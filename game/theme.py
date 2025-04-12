# game/theme.py

import pygame

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
        return pygame.font.Font(self.FONT_PATH, size)


# === Theme definitions ===

RETRO_ARCADE = Theme(
    name="Retro Arcade",
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
    name="Neon Cyberpunk",
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

MORANDI = Theme(
    name="Morandi Elegance",
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

# === Choose your active theme here ===
ACTIVE_THEME = NEON_CYBERPUNK  # <- 只改這一行就換整個遊戲外觀

# === Proxy Style class ===
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

    @staticmethod
    def get_font(size):
        return ACTIVE_THEME.get_font(size)
