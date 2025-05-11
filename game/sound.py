# game/sound.py
import pygame
pygame.mixer.init()
from game.settings import GameSettings  # ⭐️ 引用設定
from utils import resource_path # <--- 加入這行

class SoundManager:
    def __init__(self):
        pygame.mixer.init()
        self.slowmo_sound = pygame.mixer.Sound(resource_path("assets/slowmo.mp3"))
        self.click_sound = pygame.mixer.Sound(resource_path("assets/click.mp3")) # 保留給UI等其他點擊音效
        self.countdown_sound = pygame.mixer.Sound(resource_path("assets/countdown.mp3"))
        
        # ⭐ 新增載入球拍碰撞音效 ⭐
        try:
            self.paddle_hit_sound = pygame.mixer.Sound(resource_path("assets/paddle_hit.mp3"))
            # 您可以為此音效設定獨立的音量，或使用現有的設定
            self.paddle_hit_sound.set_volume(GameSettings.CLICK_SOUND_VOLUME) # 暫時使用CLICK_SOUND_VOLUME，可後續調整
        except pygame.error as e:
            print(f"Warning: Could not load paddle_hit sound: {e}")
            self.paddle_hit_sound = None

        # ⭐ 新增載入勝利和失敗音效 ⭐
        try:
            self.win_sound = pygame.mixer.Sound(resource_path("assets/win.mp3"))
            self.lose_sound = pygame.mixer.Sound(resource_path("assets/lose.mp3"))
            # 設定音量，這裡我們暫定一個值，或者您可以根據需求在 GameSettings 中添加新設定
            # 為了最小化改動，我們可以使用一個現有的音量設定，例如 CLICK_SOUND_VOLUME
            self.win_sound.set_volume(GameSettings.CLICK_SOUND_VOLUME) 
            self.lose_sound.set_volume(GameSettings.CLICK_SOUND_VOLUME)
        except pygame.error as e:
            print(f"Warning: Could not load win/lose sound: {e}")
            self.win_sound = None
            self.lose_sound = None

        self.slowmo_sound.set_volume(GameSettings.SLOWMO_SOUND_VOLUME)
        self.slowmo_channel = None
        self.click_sound.set_volume(GameSettings.CLICK_SOUND_VOLUME)
        self.countdown_sound.set_volume(GameSettings.COUNTDOWN_SOUND_VOLUME)
        pygame.mixer.music.set_volume(GameSettings.BACKGROUND_MUSIC_VOLUME)


    # === 原有 slowmo 音效 ===
    def play_slowmo(self):
        if self.slowmo_channel is None:
            self.slowmo_channel = self.slowmo_sound.play(-1)
            # 確保 channel 存在才設定音量
            if self.slowmo_channel:
                 self.slowmo_channel.set_volume(GameSettings.SLOWMO_SOUND_VOLUME) # 使用 GameSettings 中的音量

    def stop_slowmo(self):
        if self.slowmo_channel is not None:
            self.slowmo_channel.stop()
            self.slowmo_channel = None
    
    # 播放點擊音效 (用於UI等)
    def play_click(self):
        self.click_sound.play()

    # ⭐ 新增播放球拍碰撞音效的方法 ⭐
    def play_paddle_hit(self):
        if self.paddle_hit_sound:
            self.paddle_hit_sound.play()
        else:
            # 如果 paddle_hit.mp3 載入失敗，可以選擇播放預設的 click 音效或不播放
            self.click_sound.play() # Fallback to click sound if paddle_hit_sound is not available

    # 播放倒數音效
    def play_countdown(self):
        self.countdown_sound.play()

    # 控制背景音樂
    def play_bg_music(self, loop=True):
        pygame.mixer.music.play(-1 if loop else 0)

    def stop_bg_music(self):
        pygame.mixer.music.stop()

    # ⭐ 新增播放勝利音效的方法 ⭐
    def play_win_sound(self):
        if self.win_sound:
            self.win_sound.play()

    # ⭐ 新增播放失敗音效的方法 ⭐
    def play_lose_sound(self):
        if self.lose_sound:
            self.lose_sound.play()