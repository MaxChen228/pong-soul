# game/constants.py
import pygame

# --- Key Mappings for Menus ---
# For Player 1 in PvP skill selection, or any menu where P1 uses WASD-like keys
P1_MENU_CONTROLS = {
    'UP': pygame.K_w,
    'DOWN': pygame.K_s,
    'CONFIRM': pygame.K_e, # Or pygame.K_SPACE, pygame.K_RETURN
    'CANCEL': pygame.K_q  # Or pygame.K_ESCAPE
}

# For Player 2 in PvP skill selection, or default single-player menu controls
DEFAULT_MENU_CONTROLS = {
    'UP': pygame.K_UP,
    'DOWN': pygame.K_DOWN,
    'CONFIRM': pygame.K_RETURN,
    'CANCEL': pygame.K_ESCAPE
}

# --- Key Mappings for Gameplay ---
# Player 1 Gameplay Controls
P1_GAME_CONTROLS = {
    'LEFT_KB': pygame.K_LEFT,    # Keyboard left for P1
    'RIGHT_KB': pygame.K_RIGHT,  # Keyboard right for P1
    'SKILL_KB': pygame.K_x,      # Keyboard skill for P1 (example)
    # If mouse controls were more complex, they could also be defined here,
    # but mouse movement is usually direct input, not key mapping.
}

# Player 2 Gameplay Controls (for PvP)
P2_GAME_CONTROLS = {
    'LEFT': pygame.K_a,       # Player 2 Left
    'RIGHT': pygame.K_d,      # Player 2 Right
    'SKILL': pygame.K_s       # Player 2 Skill
}

# --- Add other game-wide constants below as needed ---
# Example:
# DEFAULT_FONT_NAME = "Arial"
# MAX_SCORE = 10

# Skill code names (already somewhat centralized in skill_config.py and state classes)
# If used very widely outside of their direct context, could be added here.
# SKILL_SLOWMO = "slowmo"
# SKILL_LONG_PADDLE = "long_paddle"
# SKILL_SOUL_EATER_BUG = "soul_eater_bug"