import tkinter as tk
from tkinter import ttk
import sounddevice as sd
import soundfile as sf
import pyaudio
import numpy as np
import os
import shutil
from scipy.io import wavfile
import requests
import sys


# このアプリフォルダの絶対パスを取得
this_file_abspath = os.path.abspath(sys.argv[0])
last_slash_index = this_file_abspath.rfind('/')  # 最後の '/' のインデックスを取得
this_app_root_abspath = this_file_abspath[:last_slash_index]


def count_files_in_folder(folder_path):
    """  フォルダ内のファイル数を取得する関数 """
    file_count = 0
    file_list = os.listdir(folder_path)
    for file_name in file_list:
        file_path = os.path.join(folder_path, file_name)
        if os.path.isfile(file_path):
            file_count += 1
    return file_count

def choice_audio_device_ui():
    p = pyaudio.PyAudio()
    default_mic_index = p.get_default_input_device_info()['index']
    default_speaker_index = p.get_default_output_device_info()['index']
    sd.default.device = [default_mic_index, default_speaker_index]
    device_count = p.get_device_count()
    mic_device_name_list = []
    for i in range(device_count):
        device_info = p.get_device_info_by_index(i)["name"]
        mic_device_name_list.append(device_info)
    return mic_device_name_list , default_mic_index, default_speaker_index


def display_down_tk_text(
        loop_count: int, tk_canvas: tk.Canvas(), text_list: list,
        text_widget_x: int, text_widget_y_min: int
    ):
    """ ループ中に「tkinter」のウィジェットを降順に表示させる関数
    使い方 : 
        必ずループ中に使う
    引数 :
        loop_count (int) : 現時点でのループ回数
    """
    if loop_count == 0:
        tk_canvas.create_text(
            text_widget_x, text_widget_y_min , text=text_list[0],
            font=("", 14), tag="tag_text0",
        )
    for loop in range(loop_count + 1):
        # 今回のウィジェットを表示
        loop_tag_text = "tag_text" + str(loop)
        try:
            tk_canvas.delete(loop_tag_text)
        except:
            pass
        tk_canvas.create_text(
            text_widget_x, text_widget_y_min + (loop_count - loop) * 50 , text=text_list[loop],
            font=("", 14), tag = loop_tag_text
        )
    tk_canvas.update()


def insert_newlines(text, n):
    """ 文章を指定文字数ごとに改行する関数 """
    return '\n'.join(text[i:i+n] for i in range(0, len(text), n))


def delete_all_files_in_folder(folder_path):
    shutil.rmtree(folder_path)
    if not os.path.exists(folder_path):
        os.makedirs(folder_path)


def speech_to_text_api(
    wav_file_path: str ,
    api_site_url: str = "https://speech-text-api.onrender.com" ,
):
    # 音声wavファイルから音声データを読み込み
    samplerate , audio_data = wavfile.read(wav_file_path)
    # データをnumpyに変換してからリストへと変換
    audio_list = np.array(audio_data).tolist()
    params = {
        "audio_list": audio_list ,
        "wav_file_path": "recorded_audio.wav" ,
        "samplerate": samplerate ,
    }
    response = requests.post(api_site_url , json=params)
    recognized_text_json = response.json()
    recognized_text = recognized_text_json["recognized_text"]
    return recognized_text



class Recorder:
    def __init__(self, wav_file_path: str = "audio/record.wav", tk_canvas = tk.Canvas()):
        self.wav_file_path: str = wav_file_path
        self.samplerate: int = 0
        self.recorded_audio_list = []
        self.record_number: int = 0
        self.tk_canvas = tk_canvas
        self.is_running = True

    def callback(self, indata: np.ndarray, frames: int , time, status):
        recorded_audio = indata.copy()
        self.recorded_audio_list.append(recorded_audio)
        # 最新の音声データのみをファイルに追加
        dot_index = dot_index = self.wav_file_path.rfind(".")
        sequential_wav_file_path = self.wav_file_path[:dot_index] + str(self.record_number) + self.wav_file_path[dot_index:]
        sf.write(sequential_wav_file_path, recorded_audio, samplerate=int(self.samplerate))
        self.record_number += 1

    def on_button_click(self):
        self.is_running = False

    def record_audio(self):
        """ 音声をマイク入力する関数 """
        stream = sd.InputStream(
            channels=1,
            dtype='float32',
            callback=self.callback
        )
        with stream:
            self.samplerate = int(stream.samplerate)
            self.tk_canvas.create_text(200, 160, text="録音＆文字起こし中", font=("", 18))
            button = tk.Button(self.tk_canvas, text="更新")
            button.place(x=170, y=180)
            self.tk_canvas.update()
            button["command"] = self.on_button_click

            input_sec = 0.05
            recognized_text_list: list = []
            recognition_count = 0
            while self.is_running:
                while self.is_running:
                    sd.sleep(int(input_sec * 1000))
                    self.tk_canvas.update()
                
                all_recorded_audio = np.concatenate(self.recorded_audio_list)
                sf.write(self.wav_file_path, all_recorded_audio, samplerate = self.samplerate)
                recognized_text = speech_to_text_api(self.wav_file_path)
                recognized_text = insert_newlines(recognized_text, 22)
                # self.tk_canvas.create_text(200, 200 , text=recognized_text, font=("", 14))
                recognized_text_list.append(recognized_text)
                display_down_tk_text(
                    recognition_count , self.tk_canvas ,
                    recognized_text_list , 200 , 240
                )
                recognition_count += 1
                self.is_running = True
                self.recorded_audio_list = []


def start_mic_input(canvas, form_mic_device, mic_device_name_list, default_speaker_index):
    # 外部ファイルとの通信用ファイル
    async_np_file = os.path.join(this_app_root_abspath, "media/async/recognition.npz")
    wav_file_path = os.path.join(this_app_root_abspath, "media/audio/recorded_audio.wav")
    # 選択されたマイクに設定
    selected_mic_device = form_mic_device.get()
    selected_mic_index = mic_device_name_list.index(selected_mic_device)
    sd.default.device = [selected_mic_index , default_speaker_index]
    # 音声入力と録音
    recorder = Recorder(wav_file_path, canvas)
    recorder.record_audio()
    # スクロールバーウィジェット
    canvas.create_window((0, 0), window=tk.Frame(canvas), anchor=tk.NW)


def main(root):
    root.title("リアルタイム音声文字起こし")
    root.geometry("420x2000")
    
    # スクロールバーオブジェクトを生成
    ybar = tk.Scrollbar(root, orient=tk.VERTICAL)

    canvas = tk.Canvas(
        root, width=400, height=1800,
        scrollregion=(0, 0, 400, 10000),
        yscrollcommand=ybar.set
    )
    canvas.place(x=100, y=10)
    canvas.grid(row=0, column=0)

    ybar.grid(
        row=0, column=1,  # キャンバスの右の位置を指定
        sticky=tk.N + tk.S  # 上下いっぱいに引き伸ばす
    )
    ybar.config(
        command=canvas.yview
    )
    canvas.config(
        yscrollcommand=ybar.set
    )

    # マイクの選択
    canvas.create_text(200, 40, text="マイクを選択してください", font=("", 14))
    mic_device_name_list, default_mic_index, default_speaker_index = choice_audio_device_ui()
    print(mic_device_name_list)
    form_mic_device = ttk.Combobox(root, values = mic_device_name_list, textvariable = tk.StringVar())
    canvas.create_window(200, 70 , window=form_mic_device)
    decide_mic = tk.Button(root, text="マイクを決定", command=lambda: start_mic_input(canvas, form_mic_device, mic_device_name_list, default_speaker_index))
    canvas.create_window(200, 100 , window=decide_mic)


root = tk.Tk()
main(root)
root.mainloop()

