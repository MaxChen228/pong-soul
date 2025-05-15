# game/theme.py

import pygame
from game.settings import GameSettings # GameSettings 會在運行時被 GameApp 初始化
from utils import resource_path

# --- Theme definitions ---
# (保持 Theme 類別和所有主題定義不變)
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
        return pygame.font.Font(resource_path(self.FONT_PATH), size)

RETRO_ARCADE = Theme(
    "Retro Arcade",
    background=(26, 26, 26), ball=(255, 255, 255), player=(0, 255, 0), ai=(255, 0, 0),
    player_bar_bg=(0, 100, 0), player_bar_fill=(0, 255, 0), ai_bar_bg=(100, 0, 0), ai_bar_fill=(255, 0, 0),
    text=(255, 255, 0), font_path='assets/PressStart2P.ttf'
)
NEON_CYBERPUNK = Theme(
    "Neon Cyberpunk",
    background=(15, 15, 15), ball=(0, 255, 255), player=(255, 0, 255), ai=(255, 255, 0),
    player_bar_bg=(80, 0, 80), player_bar_fill=(255, 0, 255), ai_bar_bg=(80, 80, 0), ai_bar_fill=(255, 255, 0),
    text=(255, 255, 255), font_path='assets/PressStart2P.ttf'
)
MORANDI_ELEGANCE = Theme(
    "Morandi Elegance",
    background=(230, 228, 220), ball=(214, 199, 176), player=(168, 159, 145), ai=(140, 131, 122),
    player_bar_bg=(140, 131, 122), player_bar_fill=(168, 159, 145), ai_bar_bg=(190, 175, 160), ai_bar_fill=(214, 199, 176),
    text=(92, 92, 92), font_path='assets/PressStart2P.ttf'
)
JAPANESE_TRADITIONAL = Theme(
    "Japanese Traditional",
    background=(247, 241, 231), ball=(152, 105, 96), player=(112, 128, 144), ai=(201, 173, 167),
    player_bar_bg=(190, 183, 172), player_bar_fill=(112, 128, 144), ai_bar_bg=(210, 180, 170), ai_bar_fill=(152, 105, 96),
    text=(66, 66, 66), font_path='assets/PressStart2P.ttf'
)
CHINESE_TRADITIONAL = Theme(
    "Chinese Traditional",
    background=(248, 245, 240), ball=(190, 30, 45), player=(255, 204, 0), ai=(104, 168, 103),
    player_bar_bg=(255, 230, 150), player_bar_fill=(255, 204, 0), ai_bar_bg=(160, 190, 150), ai_bar_fill=(104, 168, 103),
    text=(33, 33, 33), font_path='assets/PressStart2P.ttf'
)
MATERIAL_FLAT = Theme(
    "Material Flat",
    background=(236, 239, 241), ball=(33, 150, 243), player=(76, 175, 80), ai=(244, 67, 54),
    player_bar_bg=(200, 230, 201), player_bar_fill=(76, 175, 80), ai_bar_bg=(239, 154, 154), ai_bar_fill=(244, 67, 54),
    text=(33, 33, 33), font_path='assets/PressStart2P.ttf'
)

# Dictionary of all available themes
ALL_THEMES = {
    "Retro Arcade": RETRO_ARCADE,
    "Neon Cyberpunk": NEON_CYBERPUNK,
    "Morandi Elegance": MORANDI_ELEGANCE,
    "Japanese Traditional": JAPANESE_TRADITIONAL,
    "Chinese Traditional": CHINESE_TRADITIONAL,
    "Material Flat": MATERIAL_FLAT
}

# --- Global variable to hold the currently active theme object ---
# This will be updated by reload_active_style()
ACTIVE_THEME = None

class Style:
    # These will be class attributes, updated by reload_active_style()
    BACKGROUND_COLOR = None
    BALL_COLOR = None
    PLAYER_COLOR = None
    AI_COLOR = None
    PLAYER_BAR_BG = None
    PLAYER_BAR_FILL = None
    AI_BAR_BG = None
    AI_BAR_FILL = None
    TEXT_COLOR = None
    FONT_PATH = None # Though FONT_PATH is often the same, keep it for consistency

    # UI layout constants (can remain as they are, or also be moved to theme if needed)
    TITLE_FONT_SIZE = 28
    SUBTITLE_FONT_SIZE = 16
    ITEM_FONT_SIZE = 20
    # New: Font size for settings icon/button
    SETTINGS_ICON_FONT_SIZE = 20


    TITLE_POS = (40, 30)
    SUBTITLE_POS = (40, 65)
    ITEM_START_POS = (100, 120)
    ITEM_LINE_SPACING = 40
    # New: Position for settings icon (e.g., top right corner)
    # These are logical positions; scaling will be applied by states.
    # (Example: 800x600 logical menu size)
    SETTINGS_ICON_POS_LOGICAL = (760, 20) # (x, y) from top-left of logical menu area

    @staticmethod
    def get_font(size):
        # Ensure ACTIVE_THEME is loaded before calling this
        if ACTIVE_THEME and ACTIVE_THEME.FONT_PATH:
            return ACTIVE_THEME.get_font(size)
        else:
            # Fallback if ACTIVE_THEME is somehow not set (should not happen after reload)
            print("[Style.get_font] WARNING: ACTIVE_THEME not set or FONT_PATH missing. Using default Pygame font.")
            return pygame.font.Font(None, size)

def reload_active_style():
    """
    Reloads the ACTIVE_THEME based on GameSettings and updates Style class attributes.
    This function should be called when the active theme name changes.
    """
    global ACTIVE_THEME # Declare that we are modifying the global ACTIVE_THEME variable

    active_theme_name_from_settings = GameSettings.ACTIVE_THEME_NAME
    
    # Fallback if the name from settings is not in our ALL_THEMES
    # (e.g., typo in global_settings.yaml or a theme was removed)
    if active_theme_name_from_settings not in ALL_THEMES:
        print(f"[theme.py] WARNING: Theme '{active_theme_name_from_settings}' not found in ALL_THEMES. Defaulting to 'Retro Arcade'.")
        active_theme_name_from_settings = "Retro Arcade" # A safe default

    ACTIVE_THEME = ALL_THEMES[active_theme_name_from_settings]

    # Update Style class attributes directly
    Style.BACKGROUND_COLOR = ACTIVE_THEME.BACKGROUND_COLOR
    Style.BALL_COLOR = ACTIVE_THEME.BALL_COLOR
    Style.PLAYER_COLOR = ACTIVE_THEME.PLAYER_COLOR
    Style.AI_COLOR = ACTIVE_THEME.AI_COLOR
    Style.PLAYER_BAR_BG = ACTIVE_THEME.PLAYER_BAR_BG
    Style.PLAYER_BAR_FILL = ACTIVE_THEME.PLAYER_BAR_FILL
    Style.AI_BAR_BG = ACTIVE_THEME.AI_BAR_BG
    Style.AI_BAR_FILL = ACTIVE_THEME.AI_BAR_FILL
    Style.TEXT_COLOR = ACTIVE_THEME.TEXT_COLOR
    Style.FONT_PATH = ACTIVE_THEME.FONT_PATH
    
    # print(f"[DEBUG_THEME] Style reloaded. Active theme: {ACTIVE_THEME.name}") # Optional debug

def get_available_theme_names():
    """Returns a list of names of all available themes."""
    return list(ALL_THEMES.keys())

# --- Initial load of the style based on GameSettings ---
# This ensures that when the module is first imported, Style is populated.
# GameSettings might give a warning here if ConfigManager is not yet set,
# but it will use its fallback, which is fine for the initial load.
# reload_active_style() will be called again if the theme is changed at runtime.
#
# Note: This line will cause the GameSettings warning: "[GameSettings] WARNING: ConfigManager not set..."
# This is acceptable as GameSettings provides a fallback.
# When GameApp is initialized, GameSettings gets the proper ConfigManager,
# and if we implement theme switching, reload_active_style will be called again.
if __name__ != '__main__': # Avoid running this if theme.py is run directly for testing
    try:
        pygame.font.init() # Ensure font system is initialized if not already
        reload_active_style()
    except Exception as e:
        print(f"[theme.py] ERROR during initial style load: {e}. Some styles might be incorrect.")
        # Attempt a very basic fallback for ACTIVE_THEME if all else fails
        if ACTIVE_THEME is None:
            ACTIVE_THEME = RETRO_ARCADE # Absolute fallback
            print("[theme.py] Critical fallback: ACTIVE_THEME set to RETRO_ARCADE directly.")
            # Manually set Style attributes if reload_active_style failed badly
            Style.BACKGROUND_COLOR = ACTIVE_THEME.BACKGROUND_COLOR
            Style.TEXT_COLOR = ACTIVE_THEME.TEXT_COLOR
            Style.FONT_PATH = ACTIVE_THEME.FONT_PATH