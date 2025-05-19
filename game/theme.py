# game/theme.py

import pygame
from game.settings import GameSettings # GameSettings 會在運行時被 GameApp 初始化
from utils import resource_path

# --- Theme definitions ---
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
        self.FONT_PATH = font_path # 這個 FONT_PATH 將被修改

    def get_font(self, size):
        return pygame.font.Font(resource_path(self.FONT_PATH), size)

NEW_FONT_PATH = 'assets/unifont-16.0.03.otf' # 定義新的字體路徑

RETRO_ARCADE = Theme(
    "Retro Arcade",
    background=(26, 26, 26), ball=(255, 255, 255), player=(0, 255, 0), ai=(255, 0, 0),
    player_bar_bg=(0, 100, 0), player_bar_fill=(0, 255, 0), ai_bar_bg=(100, 0, 0), ai_bar_fill=(255, 0, 0),
    text=(255, 255, 0), font_path=NEW_FONT_PATH # <--- 修改
)
NEON_CYBERPUNK = Theme(
    "Neon Cyberpunk",
    background=(15, 15, 15), ball=(0, 255, 255), player=(255, 0, 255), ai=(255, 255, 0),
    player_bar_bg=(80, 0, 80), player_bar_fill=(255, 0, 255), ai_bar_bg=(80, 80, 0), ai_bar_fill=(255, 255, 0),
    text=(255, 255, 255), font_path=NEW_FONT_PATH # <--- 修改
)
MORANDI_ELEGANCE = Theme(
    "Morandi Elegance",
    background=(230, 228, 220), ball=(214, 199, 176), player=(168, 159, 145), ai=(140, 131, 122),
    player_bar_bg=(140, 131, 122), player_bar_fill=(168, 159, 145), ai_bar_bg=(190, 175, 160), ai_bar_fill=(214, 199, 176),
    text=(92, 92, 92), font_path=NEW_FONT_PATH # <--- 修改
)
JAPANESE_TRADITIONAL = Theme(
    "Japanese Traditional",
    background=(247, 241, 231), ball=(152, 105, 96), player=(112, 128, 144), ai=(201, 173, 167),
    player_bar_bg=(190, 183, 172), player_bar_fill=(112, 128, 144), ai_bar_bg=(210, 180, 170), ai_bar_fill=(152, 105, 96),
    text=(66, 66, 66), font_path=NEW_FONT_PATH # <--- 修改
)
CHINESE_TRADITIONAL = Theme(
    "Chinese Traditional",
    background=(248, 245, 240), ball=(190, 30, 45), player=(255, 204, 0), ai=(104, 168, 103),
    player_bar_bg=(255, 230, 150), player_bar_fill=(255, 204, 0), ai_bar_bg=(160, 190, 150), ai_bar_fill=(104, 168, 103),
    text=(33, 33, 33), font_path=NEW_FONT_PATH # <--- 修改
)
MATERIAL_FLAT = Theme(
    "Material Flat",
    background=(236, 239, 241), ball=(33, 150, 243), player=(76, 175, 80), ai=(244, 67, 54),
    player_bar_bg=(200, 230, 201), player_bar_fill=(76, 175, 80), ai_bar_bg=(239, 154, 154), ai_bar_fill=(244, 67, 54),
    text=(33, 33, 33), font_path=NEW_FONT_PATH # <--- 修改
)

ALL_THEMES = {
    "Retro Arcade": RETRO_ARCADE,
    "Neon Cyberpunk": NEON_CYBERPUNK,
    "Morandi Elegance": MORANDI_ELEGANCE,
    "Japanese Traditional": JAPANESE_TRADITIONAL,
    "Chinese Traditional": CHINESE_TRADITIONAL,
    "Material Flat": MATERIAL_FLAT
}

ACTIVE_THEME = None

class Style:
    BACKGROUND_COLOR = None
    BALL_COLOR = None
    PLAYER_COLOR = None
    AI_COLOR = None
    PLAYER_BAR_BG = None
    PLAYER_BAR_FILL = None
    AI_BAR_BG = None
    AI_BAR_FILL = None
    TEXT_COLOR = None
    FONT_PATH = None

    TITLE_FONT_SIZE = 28
    SUBTITLE_FONT_SIZE = 16
    ITEM_FONT_SIZE = 20
    SETTINGS_ICON_FONT_SIZE = 20

    TITLE_POS = (40, 30)
    SUBTITLE_POS = (40, 65)
    ITEM_START_POS = (100, 120)
    ITEM_LINE_SPACING = 40
    SETTINGS_ICON_POS_LOGICAL = (760, 20)

    @staticmethod
    def get_font(size):
        if ACTIVE_THEME and ACTIVE_THEME.FONT_PATH:
            return ACTIVE_THEME.get_font(size)
        else:
            print("[Style.get_font] WARNING: ACTIVE_THEME not set or FONT_PATH missing. Using default Pygame font.")
            return pygame.font.Font(None, size)

def reload_active_style():
    global ACTIVE_THEME
    active_theme_name_from_settings = GameSettings.ACTIVE_THEME_NAME
    if active_theme_name_from_settings not in ALL_THEMES:
        print(f"[theme.py] WARNING: Theme '{active_theme_name_from_settings}' not found in ALL_THEMES. Defaulting to 'Retro Arcade'.")
        active_theme_name_from_settings = "Retro Arcade"
    ACTIVE_THEME = ALL_THEMES[active_theme_name_from_settings]

    Style.BACKGROUND_COLOR = ACTIVE_THEME.BACKGROUND_COLOR
    Style.BALL_COLOR = ACTIVE_THEME.BALL_COLOR
    Style.PLAYER_COLOR = ACTIVE_THEME.PLAYER_COLOR
    Style.AI_COLOR = ACTIVE_THEME.AI_COLOR
    Style.PLAYER_BAR_BG = ACTIVE_THEME.PLAYER_BAR_BG
    Style.PLAYER_BAR_FILL = ACTIVE_THEME.PLAYER_BAR_FILL
    Style.AI_BAR_BG = ACTIVE_THEME.AI_BAR_BG
    Style.AI_BAR_FILL = ACTIVE_THEME.AI_BAR_FILL
    Style.TEXT_COLOR = ACTIVE_THEME.TEXT_COLOR
    Style.FONT_PATH = ACTIVE_THEME.FONT_PATH # This will now point to NEW_FONT_PATH for the active theme

def get_available_theme_names():
    return list(ALL_THEMES.keys())

if __name__ != '__main__':
    try:
        pygame.font.init()
        reload_active_style()
    except Exception as e:
        print(f"[theme.py] ERROR during initial style load: {e}. Some styles might be incorrect.")
        if ACTIVE_THEME is None:
            ACTIVE_THEME = RETRO_ARCADE
            print("[theme.py] Critical fallback: ACTIVE_THEME set to RETRO_ARCADE directly.")
            Style.BACKGROUND_COLOR = ACTIVE_THEME.BACKGROUND_COLOR
            Style.TEXT_COLOR = ACTIVE_THEME.TEXT_COLOR
            Style.FONT_PATH = ACTIVE_THEME.FONT_PATH