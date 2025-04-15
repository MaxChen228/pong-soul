# long_paddle_skill.py
import pygame
from game.skills.base_skill import Skill
from game.skills.skill_config import SKILL_CONFIGS

class LongPaddleSkill(Skill):
    def __init__(self, env):
        super().__init__(env)
        cfg = SKILL_CONFIGS["long_paddle"]

        self.duration_ms = cfg["duration_ms"]
        self.cooldown_ms = cfg["cooldown_ms"]
        self.paddle_multiplier = cfg["paddle_multiplier"]

        self.active = False
        self.activated_time = 0
        self.cooldown_start_time = 0

        # 動畫 & 顏色
        self.animation_ms = cfg["animation_ms"]
        self.original_paddle_width = env.player_paddle_width
        self.target_paddle_width = int(self.original_paddle_width * self.paddle_multiplier)

        self.is_animating = False
        self.anim_start_time = 0
        # 讓縮回動畫知道當前寬度
        self.current_width_at_anim_start = self.original_paddle_width

    def activate(self):
        cur = pygame.time.get_ticks()
        if not self.active and (cur - self.cooldown_start_time >= self.cooldown_ms):
            self.active = True
            self.activated_time = cur
            self.is_animating = True
            self.anim_start_time = cur

    def update(self):
        cur = pygame.time.get_ticks()

        if self.active:
            if (cur - self.activated_time) >= self.duration_ms:
                self.deactivate()
            else:
                # 伸長動畫
                if self.is_animating:
                    elapsed = cur - self.anim_start_time
                    if elapsed < self.animation_ms:
                        ratio = elapsed / self.animation_ms
                        new_width = int(
                            self.original_paddle_width
                            + (self.target_paddle_width - self.original_paddle_width)*ratio
                        )
                        self.env.player_paddle_width = new_width
                    else:
                        self.env.player_paddle_width = self.target_paddle_width
                        self.is_animating = False

                # 設定板子顏色
                cfg = SKILL_CONFIGS["long_paddle"]
                self.env.paddle_color = cfg["paddle_color"]
        else:
            # 縮回動畫
            if self.env.player_paddle_width != self.original_paddle_width:
                if not self.is_animating:
                    self.is_animating = True
                    self.anim_start_time = cur
                    self.current_width_at_anim_start = self.env.player_paddle_width

                elapsed = cur - self.anim_start_time
                if elapsed < self.animation_ms:
                    ratio = elapsed / self.animation_ms
                    new_width = int(
                        self.current_width_at_anim_start
                        - (self.current_width_at_anim_start - self.original_paddle_width)* ratio
                    )
                    self.env.player_paddle_width = new_width
                else:
                    self.env.player_paddle_width = self.original_paddle_width
                    self.is_animating = False
                    self.env.paddle_color = None

    def deactivate(self):
        if self.active:
            self.active = False
            self.cooldown_start_time = pygame.time.get_ticks()
            self.is_animating = True
            self.anim_start_time = pygame.time.get_ticks()
            # 清除板子顏色(或可留縮回動畫做)
            self.env.paddle_color = None

    def is_active(self):
        return self.active

    def get_cooldown_seconds(self):
        cur = pygame.time.get_ticks()
        elapsed = cur - self.cooldown_start_time
        remaining = max(0, self.cooldown_ms - elapsed)
        return remaining/1000

    def get_energy_ratio(self):
        cur= pygame.time.get_ticks()
        if self.active:
            e= cur - self.activated_time
            return max(0, (self.duration_ms - e)/self.duration_ms)
        else:
            e= cur - self.cooldown_start_time
            return min(1.0, e/self.cooldown_ms)

    def render(self, surface):
        """
        如果longpaddle也需要繪圖特效(例如板子變形動畫、殘影…)，可在此實作。
        目前省略，保留後續擴充可能。
        """
        pass
