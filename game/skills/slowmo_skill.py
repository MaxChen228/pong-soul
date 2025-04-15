# slowmo_skill.py (示範融合shockwave + fog + trail + time_scale)

import pygame
from game.skills.base_skill import Skill
from game.skills.skill_config import SKILL_CONFIGS
import math

class SlowMoSkill(Skill):
    def __init__(self, env):
        super().__init__(env)
        cfg = SKILL_CONFIGS["slowmo"]

        self.duration_ms = cfg["duration_ms"]
        self.cooldown_ms = cfg["cooldown_ms"]
        self.active = False
        self.activated_time = 0
        self.cooldown_start_time = 0

        # 新增：霧氣, 板子顏色, 殘影trail顏色, shockwave資料
        self.fog_duration_ms = cfg["fog_duration_ms"]
        self.paddle_color = cfg["paddle_color"]
        self.trail_color = cfg["trail_color"]
        self.max_trail_length = 15
        # 讓skill自己擁有殘影列表
        self.player_trail = []

        # shockwave 列表 (若你想讓 skill 自己管理shockwave，而不是 env)
        self.shockwaves = []
        self.last_slowmo_frame = 0

        # 是否處在 fog 狀態, fog_end_time
        self.fog_active = False
        self.fog_end_time = 0

        # 是否影響 time_scale
        self.slow_time_scale = 0.2  # 你想要的慢動作倍數
        self.normal_time_scale = 1.0

    def activate(self):
        current_time = pygame.time.get_ticks()
        if (not self.active) and ((current_time - self.cooldown_start_time) >= self.cooldown_ms):
            self.active = True
            self.activated_time = current_time
            self.env.sound_manager.play_slowmo()

            # 剛啟動 -> 重置shockwave
            self.last_slowmo_frame = 0
            self.shockwaves.clear()
            # 霧氣先不處理，要在 update() 中處理

    def update(self):
        current_time = pygame.time.get_ticks()

        if self.active:
            # 1) 設定 time_scale = 0.2
            self.env.time_scale = self.slow_time_scale

            # 2) 持續時間檢查
            if (current_time - self.activated_time) >= self.duration_ms:
                # 時間到了 => deactivate
                self.deactivate()
            else:
                # 技能持續中 => 產生shockwave, update shockwave, 紀錄玩家 trail
                # a) shockwave
                self._update_shockwave(current_time)

                # b) 產生殘影
                self._update_trail()
                
                # c) 設定板子顏色
                self.env.paddle_color = self.paddle_color

                # d) 開啟fog_active
                if not self.fog_active:
                    self.fog_active = True
                    # fog在技能結束後才開始倒數 => 你可以設計要等技能結束or現在開始計時
                    self.fog_end_time = current_time + self.fog_duration_ms

        else:
            # 不在 active => time_scale恢復 normal
            self.env.time_scale = self.normal_time_scale

            # shockwave or trail 是否要繼續渲染？
            # 典型做法：shockwave繼續淡出, trail清除 or 要個淡出？

            # 3) fog 淡出 (技能結束後)
            if self.fog_active:
                # if 現在 > fog_end_time => fog結束, paddle_color = None
                if current_time > self.fog_end_time:
                    self.fog_active = False
                    self.env.paddle_color = None
                    # shockwaves清掉
                    self.shockwaves.clear()
                else:
                    # 霧氣還在 => 你可以設定不同顏色or漸變
                    pass

            # trail => 若你想在技能結束後也暫留一會，可做漸漸清空
            self.player_trail.clear()

    def _update_shockwave(self, current_time):
        """示範shockwave做法(移植自 render.py or env)"""
        # 如果 last_slowmo_frame <= 0 => 產生shockwave
        if self.last_slowmo_frame <= 0:
            cx = int(self.env.player_x * self.env.render_size)
            cy = int(
                (1 - self.env.paddle_height / self.env.render_size) * self.env.render_size
            )
            self.shockwaves.append({"cx": cx, "cy": cy, "radius": 0})
            self.last_slowmo_frame = 1
        else:
            self.last_slowmo_frame += 1

        # 同時shockwaves半徑擴大 or do nothing, 讓render負責繪製
        for wave in self.shockwaves:
            wave["radius"] += 30

    def _update_trail(self):
        """紀錄玩家殘影位置"""
        self.player_trail.append(self.env.player_x)
        if len(self.player_trail) > self.max_trail_length:
            self.player_trail.pop(0)

    def deactivate(self):
        if self.active:
            self.active = False
            self.cooldown_start_time = pygame.time.get_ticks()
            self.env.sound_manager.stop_slowmo()
            # 你也可以在這裡直接 self.env.paddle_color = None

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
