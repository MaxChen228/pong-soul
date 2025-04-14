import pygame
from game.skills.base_skill import Skill
from game.settings import GameSettings

class LongPaddleSkill(Skill):
    def __init__(self, env):
        super().__init__(env)
        self.duration_ms = GameSettings.LONG_PADDLE_DURATION_MS
        self.cooldown_ms = GameSettings.LONG_PADDLE_COOLDOWN_MS
        self.active = False
        self.activated_time = 0
        self.cooldown_start_time = 0
        self.original_paddle_width = env.player_paddle_width

    def activate(self):
        current_time = pygame.time.get_ticks()
        if not self.active and (current_time - self.cooldown_start_time) >= self.cooldown_ms:
            self.active = True
            self.activated_time = current_time
            # 板子變長
            self.env.player_paddle_width = int(self.original_paddle_width * GameSettings.LONG_PADDLE_MULTIPLIER)

    def update(self):
        current_time = pygame.time.get_ticks()
        if self.active:
            if current_time - self.activated_time >= self.duration_ms:
                self.deactivate()

    def deactivate(self):
        if self.active:
            self.active = False
            self.cooldown_start_time = pygame.time.get_ticks()
            # 回復原本的板子長度
            self.env.player_paddle_width = self.original_paddle_width

    def is_active(self):
        return self.active

    def get_cooldown_seconds(self):
        current_time = pygame.time.get_ticks()
        elapsed = current_time - self.cooldown_start_time
        remaining = max(0, self.cooldown_ms - elapsed)
        return remaining / 1000

    def get_energy_ratio(self):
        current_time = pygame.time.get_ticks()
        if self.active:
            elapsed = current_time - self.activated_time
            return max(0, (self.duration_ms - elapsed) / self.duration_ms)
        else:
            elapsed = current_time - self.cooldown_start_time
            return min(1.0, elapsed / self.cooldown_ms)
