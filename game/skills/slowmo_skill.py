# slowmo_skill.py

import pygame
from game.skills.base_skill import Skill
from game.skills.skill_config import SKILL_CONFIGS

class SlowMoSkill(Skill):
    """
    slowmo技能的全部功能都在這裡實作
    包含shockwave, fog, paddle_color, trail, time_scale, ...
    """
    def __init__(self, env):
        super().__init__(env)
        cfg = SKILL_CONFIGS["slowmo"]
        self.duration_ms = cfg["duration_ms"]
        self.cooldown_ms = cfg["cooldown_ms"]

        # 內部狀態
        self.active = False
        self.activated_time = 0
        self.cooldown_start_time = 0

        # shockwave
        self.shockwaves = []
        self.last_slowmo_frame = 0

        # fog
        self.fog_duration_ms = cfg["fog_duration_ms"]
        self.fog_active = False
        self.fog_end_time = 0

        # color
        self.paddle_color = cfg["paddle_color"]
        self.trail_color = cfg["trail_color"]
        self.max_trail_length = 15

        # time_scale
        self.slow_time_scale = 0.2
        self.normal_time_scale = 1.0

        # skill-specific trail for the board
        self.player_trail = []

        # 保證聲音先停
        self.env.sound_manager.stop_slowmo()

    def activate(self):
        cur = pygame.time.get_ticks()
        if (not self.active) and (cur - self.cooldown_start_time >= self.cooldown_ms):
            self.active = True
            self.activated_time = cur
            self.env.sound_manager.play_slowmo()

            self.last_slowmo_frame = 0
            self.shockwaves.clear()

    def update(self):
        cur = pygame.time.get_ticks()
        if self.active:
            # 持續時間到 => deactivate
            if (cur - self.activated_time)>= self.duration_ms:
                self.deactivate()
            else:
                # slowmo期間 => 0.2
                self.env.time_scale = self.slow_time_scale

                # fog啟動
                if not self.fog_active:
                    self.fog_active = True
                    self.fog_end_time = cur + self.fog_duration_ms

                # 塗上板子顏色
                self.env.paddle_color = self.paddle_color

                # shockwave / trail
                self._update_shockwaves()
                self._update_trail()
        else:
            # 非active => timescale =1
            self.env.time_scale = self.normal_time_scale

            # fog
            if self.fog_active:
                if cur> self.fog_end_time:
                    self.fog_active = False
                    self.env.paddle_color = None
                    self.shockwaves.clear()
                else:
                    pass

            # trail清空
            self.player_trail.clear()

    def deactivate(self):
        if self.active:
            self.active = False
            self.cooldown_start_time = pygame.time.get_ticks()
            self.env.sound_manager.stop_slowmo()
            # 保留fog機制在 update()等結束

    def is_active(self):
        return self.active

    def get_cooldown_seconds(self):
        cur = pygame.time.get_ticks()
        elapsed = cur - self.cooldown_start_time
        remain = max(0, self.cooldown_ms- elapsed)
        return remain/1000

    def get_energy_ratio(self):
        cur= pygame.time.get_ticks()
        if self.active:
            e= cur - self.activated_time
            return max(0, (self.duration_ms-e)/self.duration_ms)
        else:
            e= cur- self.cooldown_start_time
            return min(1,(e/self.cooldown_ms))

    # shockwave
    def _update_shockwaves(self):
        if self.last_slowmo_frame<=0:
            cx = int(self.env.player_x*self.env.render_size)
            cy = int((1- self.env.paddle_height/self.env.render_size)* self.env.render_size)
            self.shockwaves.append({"cx":cx, "cy":cy, "radius":0})
            self.last_slowmo_frame=1
        else:
            self.last_slowmo_frame+=1

        for wave in self.shockwaves:
            wave["radius"]+=30

    # trail
    def _update_trail(self):
        self.player_trail.append(self.env.player_x)
        if len(self.player_trail) > self.max_trail_length:
            self.player_trail.pop(0)
