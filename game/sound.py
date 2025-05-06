import pygame
pygame.mixer.init()
from game.settings import GameSettings  # ⭐️ 引用設定
from utils import resource_path # <--- 加入這行

class SoundManager:
    def __init__(self):
        pygame.mixer.init()
        self.slowmo_sound = pygame.mixer.Sound(resource_path("assets/slowmo.mp3")) # <--- 修改這裡
        self.click_sound = pygame.mixer.Sound(resource_path("assets/click.mp3"))    # <--- 修改這裡
        self.countdown_sound = pygame.mixer.Sound(resource_path("assets/countdown.mp3")) # <--- 修改這裡
        self.slowmo_sound.set_volume(GameSettings.SLOWMO_SOUND_VOLUME)  # ⭐️ 使用設定音量
        self.slowmo_channel = None
        self.click_sound.set_volume(GameSettings.CLICK_SOUND_VOLUME)    # ⭐️ 使用設定音量
        self.countdown_sound.set_volume(GameSettings.COUNTDOWN_SOUND_VOLUME)  # ⭐️ 使用設定音量
        pygame.mixer.music.set_volume(GameSettings.BACKGROUND_MUSIC_VOLUME)   # ⭐️ 使用設定音量


    # === 原有 slowmo 音效 ===
    def play_slowmo(self):
        if self.slowmo_channel is None:
            self.slowmo_channel = self.slowmo_sound.play(-1)
            self.slowmo_channel.set_volume(1.0)

    def stop_slowmo(self):
        if self.slowmo_channel is not None:
            self.slowmo_channel.stop()
            self.slowmo_channel = None

    # === ⭐ 新增以下三個方法 ===
    
    # 播放點擊音效
    def play_click(self):
        self.click_sound.play()

    # 播放倒數音效
    def play_countdown(self):
        self.countdown_sound.play()

    # 控制背景音樂
    def play_bg_music(self, loop=True):
        pygame.mixer.music.play(-1 if loop else 0)

    def stop_bg_music(self):
        pygame.mixer.music.stop()
