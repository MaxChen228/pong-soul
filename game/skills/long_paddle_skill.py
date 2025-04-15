# long_paddle_skill.py (改良後)

from game.skills.base_skill import Skill
from game.skills.skill_config import SKILL_CONFIGS
import pygame

class LongPaddleSkill(Skill):
    def __init__(self, env):
        super().__init__(env)
        cfg = SKILL_CONFIGS["long_paddle"]

        # 主要參數
        self.duration_ms = cfg["duration_ms"]
        self.cooldown_ms = cfg["cooldown_ms"]
        self.paddle_multiplier = cfg["paddle_multiplier"]

        self.active = False
        self.activated_time = 0
        self.cooldown_start_time = 0

        # 動畫 & 顏色參數
        self.animation_ms = cfg["animation_ms"]
        self.original_paddle_width = env.player_paddle_width
        self.target_paddle_width = int(self.original_paddle_width * self.paddle_multiplier)

        self.is_animating = False
        self.anim_start_time = 0

    def activate(self):
        current_time = pygame.time.get_ticks()
        if not self.active and (current_time - self.cooldown_start_time) >= self.cooldown_ms:
            self.active = True
            self.activated_time = current_time
            self.is_animating = True
            self.anim_start_time = current_time

    def update(self):
        """
        每次 env.step() 都會呼叫 -> 由本方法處理整個「板子伸長/縮回」動畫
        """
        current_time = pygame.time.get_ticks()

        # 如果正在 active，檢查是否超時 -> deactivate
        if self.active:
            if (current_time - self.activated_time) >= self.duration_ms:
                self.deactivate()
            else:
                # 持續的「伸長期動畫」（從 original 到 target）
                # (a) 如果剛 start 動畫, is_animating = True
                if self.is_animating:
                    elapsed = current_time - self.anim_start_time
                    if elapsed < self.animation_ms:
                        ratio = elapsed / self.animation_ms
                        new_width = int(
                            self.original_paddle_width
                            + (self.target_paddle_width - self.original_paddle_width) * ratio
                        )
                        self.env.player_paddle_width = new_width
                    else:
                        # 動畫結束 -> 到 target
                        self.env.player_paddle_width = self.target_paddle_width
                        self.is_animating = False

                # 持續設定板子顏色
                cfg = SKILL_CONFIGS["long_paddle"]
                self.env.paddle_color = cfg["paddle_color"]

        else:
            # 不在 active 狀態 -> 可能是「縮回」動畫
            # 你可以做：若 self.env.player_paddle_width != self.original_paddle_width, 就做縮回
            if self.env.player_paddle_width != self.original_paddle_width:
                if not self.is_animating:
                    # 重新啟動動畫
                    self.is_animating = True
                    self.anim_start_time = current_time
                    # 這裡注意: self.original_paddle_width 可能動態
                    # 也許需要暫存 "current_width" in a field to do reverse animate
                    self.current_width_at_anim_start = self.env.player_paddle_width

                elapsed = current_time - self.anim_start_time
                if elapsed < self.animation_ms:
                    ratio = elapsed / self.animation_ms
                    new_width = int(
                        self.current_width_at_anim_start
                        - (self.current_width_at_anim_start - self.original_paddle_width) * ratio
                    )
                    self.env.player_paddle_width = new_width
                else:
                    self.env.player_paddle_width = self.original_paddle_width
                    self.is_animating = False
                    # 動畫結束 => 恢復板子顏色
                    self.env.paddle_color = None

    def deactivate(self):
        if self.active:
            self.active = False
            self.cooldown_start_time = pygame.time.get_ticks()
            # 進入「縮回」動畫階段
            self.is_animating = True
            self.anim_start_time = pygame.time.get_ticks()

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
