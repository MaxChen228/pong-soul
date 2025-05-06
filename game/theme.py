# game/theme.py

import pygame
from game.settings import GameSettings
from utils import resource_path # <--- 加入這行

class Theme:
    def __init__(self, name, background, ball, player, ai, player_bar_bg, player_bar_fill, ai_bar_bg, ai_bar_fill, text, font_path):
        self.name = name
        self.BACKGROUND_COLOR = background
        self.BALL_COLOR = ball
        self.PLAYER_COLOR = player
        self.AI_COLOR = ai
        self.PLAYER_BAR_BG = player_bar_bg
        self.PLAYER_BAR_FILL = player_bar_fill
        self.AI_BAR_BG = ai_bar_bg
        self.AI_BAR_FILL = ai_bar_fill
        self.TEXT_COLOR = text
        self.FONT_PATH = font_path

    def get_font(self, size):
        # 確保 self.FONT_PATH 是相對路徑 "assets/PressStart2P.ttf"
        return pygame.font.Font(resource_path(self.FONT_PATH), size) # <--- 修改這裡

# === Theme definitions ===

RETRO_ARCADE = Theme(
    "Retro Arcade",
    background=(26, 26, 26),
    ball=(255, 255, 255),
    player=(0, 255, 0),
    ai=(255, 0, 0),
    player_bar_bg=(0, 100, 0),
    player_bar_fill=(0, 255, 0),
    ai_bar_bg=(100, 0, 0),
    ai_bar_fill=(255, 0, 0),
    text=(255, 255, 0),
    font_path='assets/PressStart2P.ttf'
)

NEON_CYBERPUNK = Theme(
    "Neon Cyberpunk",
    background=(15, 15, 15),
    ball=(0, 255, 255),
    player=(255, 0, 255),
    ai=(255, 255, 0),
    player_bar_bg=(80, 0, 80),
    player_bar_fill=(255, 0, 255),
    ai_bar_bg=(80, 80, 0),
    ai_bar_fill=(255, 255, 0),
    text=(255, 255, 255),
    font_path='assets/PressStart2P.ttf'
)

MORANDI_ELEGANCE = Theme(
    "Morandi Elegance",
    background=(230, 228, 220),
    ball=(214, 199, 176),
    player=(168, 159, 145),
    ai=(140, 131, 122),
    player_bar_bg=(140, 131, 122),
    player_bar_fill=(168, 159, 145),
    ai_bar_bg=(190, 175, 160),
    ai_bar_fill=(214, 199, 176),
    text=(92, 92, 92),
    font_path='assets/PressStart2P.ttf'
)

JAPANESE_TRADITIONAL = Theme(
    "Japanese Traditional",
    background=(247, 241, 231),  # 薄墨色
    ball=(152, 105, 96),         # 紅緋
    player=(112, 128, 144),      # 錫色
    ai=(201, 173, 167),          # 鳩羽鼠
    player_bar_bg=(190, 183, 172),
    player_bar_fill=(112, 128, 144),
    ai_bar_bg=(210, 180, 170),
    ai_bar_fill=(152, 105, 96),
    text=(66, 66, 66),
    font_path='assets/PressStart2P.ttf'
)

CHINESE_TRADITIONAL = Theme(
    "Chinese Traditional",
    background=(248, 245, 240),  # 米色
    ball=(190, 30, 45),          # 中國紅
    player=(255, 204, 0),        # 明黃
    ai=(104, 168, 103),          # 青綠
    player_bar_bg=(255, 230, 150),
    player_bar_fill=(255, 204, 0),
    ai_bar_bg=(160, 190, 150),
    ai_bar_fill=(104, 168, 103),
    text=(33, 33, 33),
    font_path='assets/PressStart2P.ttf'
)

MATERIAL_FLAT = Theme(
    "Material Flat",
    background=(236, 239, 241),
    ball=(33, 150, 243),
    player=(76, 175, 80),
    ai=(244, 67, 54),
    player_bar_bg=(200, 230, 201),
    player_bar_fill=(76, 175, 80),
    ai_bar_bg=(239, 154, 154),
    ai_bar_fill=(244, 67, 54),
    text=(33, 33, 33),
    font_path='assets/PressStart2P.ttf'
)


# === Choose your active theme dynamically ===
ACTIVE_THEME = {
    "Retro Arcade": RETRO_ARCADE,
    "Neon Cyberpunk": NEON_CYBERPUNK,
    "Morandi Elegance": MORANDI_ELEGANCE,
    "Japanese Traditional": JAPANESE_TRADITIONAL,
    "Chinese Traditional": CHINESE_TRADITIONAL,
    "Material Flat": MATERIAL_FLAT
}[GameSettings.ACTIVE_THEME_NAME]

class Style:
    BACKGROUND_COLOR = ACTIVE_THEME.BACKGROUND_COLOR
    BALL_COLOR = ACTIVE_THEME.BALL_COLOR
    PLAYER_COLOR = ACTIVE_THEME.PLAYER_COLOR
    AI_COLOR = ACTIVE_THEME.AI_COLOR
    PLAYER_BAR_BG = ACTIVE_THEME.PLAYER_BAR_BG
    PLAYER_BAR_FILL = ACTIVE_THEME.PLAYER_BAR_FILL
    AI_BAR_BG = ACTIVE_THEME.AI_BAR_BG
    AI_BAR_FILL = ACTIVE_THEME.AI_BAR_FILL
    TEXT_COLOR = ACTIVE_THEME.TEXT_COLOR
    FONT_PATH = ACTIVE_THEME.FONT_PATH

    TITLE_FONT_SIZE = 28
    SUBTITLE_FONT_SIZE = 16
    ITEM_FONT_SIZE = 20

    TITLE_POS = (40, 30)
    SUBTITLE_POS = (40, 65)
    ITEM_START_POS = (100, 120)
    ITEM_LINE_SPACING = 40

    @staticmethod
    def get_font(size):
        return ACTIVE_THEME.get_font(size)

