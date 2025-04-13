from game.skills.base_skill import Skill
import pygame

class SlowMoSkill(Skill):
    def __init__(self, env):
        super().__init__(env)
        self.duration_ms = 1500   # 技能持續時間：1500毫秒（1.5秒）
        self.cooldown_ms = 2000   # 冷卻時間：2000毫秒（2秒）
        self.active = False
        self.activated_time = 0
        self.cooldown_start_time = 0


    def activate(self):
        current_time = pygame.time.get_ticks()
        if not self.active and (current_time - self.cooldown_start_time) >= self.cooldown_ms:
            self.active = True
            self.activated_time = current_time
            self.env.sound_manager.play_slowmo()


    def update(self):
        current_time = pygame.time.get_ticks()
        if self.active:
            if current_time - self.activated_time >= self.duration_ms:
                self.deactivate()
        else:
            # 什麼都不用做，因為冷卻是靠時間差來計算的
            pass

    def deactivate(self):
        if self.active:
            self.active = False
            self.cooldown_start_time = pygame.time.get_ticks()
            self.env.sound_manager.stop_slowmo()

    def get_cooldown_seconds(self):
        current_time = pygame.time.get_ticks()
        elapsed = current_time - self.cooldown_start_time
        remaining = max(0, self.cooldown_ms - elapsed)
        return remaining / 1000  # 返回秒數


    def is_active(self):
        return self.active

    # ⭐ 新增此方法
    def get_energy_ratio(self):
        current_time = pygame.time.get_ticks()
        if self.active:
            elapsed = current_time - self.activated_time
            return max(0, (self.duration_ms - elapsed) / self.duration_ms)
        else:
            elapsed = current_time - self.cooldown_start_time
            return min(1.0, elapsed / self.cooldown_ms)

