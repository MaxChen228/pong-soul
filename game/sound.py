# game/sound.py
import pygame

class SoundManager:
    def __init__(self):
        pygame.mixer.init()  # 初始化音效系統
        self.slowmo_sound = pygame.mixer.Sound("assets/slowmo.mp3")  # 讀取音效文件
        self.slowmo_channel = None  # 用來控制播放/停止音效

    def play_slowmo(self):
        """ 播放慢動作音效，並設定為循環播放 """
        if self.slowmo_channel is None:  # 只有當音效未播放時才開始播放
            print("Playing slowmo sound...")
            self.slowmo_channel = self.slowmo_sound.play(-1)  # 播放並循環
            self.slowmo_channel.set_volume(1.0)  # 設置音量為最大
        else:
            print("Slowmo sound is already playing.")  # 如果音效已經在播放，則不再播放

    def stop_slowmo(self):
        """ 停止慢動作音效 """
        if self.slowmo_channel is not None:  # 只有當音效正在播放時才停止
            print("Stopping slowmo sound...")
            self.slowmo_channel.stop()  # 停止播放音效
            self.slowmo_channel = None  # 重置音效通道為 None
        else:
            print("No slowmo sound to stop.")  # 如果音效沒有播放，則不做任何動作
