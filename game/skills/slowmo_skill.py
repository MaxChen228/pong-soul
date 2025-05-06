# slowmo_skill.py

import math
import pygame
from game.skills.base_skill import Skill
from game.skills.skill_config import SKILL_CONFIGS

class SlowMoSkill(Skill):
    """
    技能時間到 -> deactivate() -> fadeout_active = True
    外部不強制中斷 => 持續 step() / render() => shockwave / trail / clock 漸淡
    """

    def __init__(self, env):
        super().__init__(env)
        cfg = SKILL_CONFIGS["slowmo"]
        self.duration_ms = cfg["duration_ms"]
        self.cooldown_ms = cfg["cooldown_ms"]

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
        self.player_trail = []

        # clock
        self.clock_color = cfg["clock_color"]
        self.clock_radius = cfg["clock_radius"]
        self.clock_line_width = cfg["clock_line_width"]

        # time_scale
        self.slow_time_scale = 0.2
        self.normal_time_scale = 1.0

        # fadeout
        self.fadeout_active = False
        self.fadeout_duration_ms = 1500
        self.fadeout_end_time = 0

        # offset
        self.offset_y = 100
        self.env.sound_manager.stop_slowmo()

    def activate(self):
        cur = pygame.time.get_ticks()
        if (not self.active) and (cur - self.cooldown_start_time >= self.cooldown_ms):
            self.active = True
            self.activated_time = cur
            self.env.sound_manager.play_slowmo()
            self.last_slowmo_frame = 0
            self.shockwaves.clear()
            self.fadeout_active = False

    def update(self):
        cur = pygame.time.get_ticks()
        if self.active:
            if (cur - self.activated_time) >= self.duration_ms:
                # 時間到 => 進入fadeout
                self.deactivate()
            else:
                self.env.time_scale = self.slow_time_scale
                if not self.fog_active:
                    self.fog_active = True
                    # 讓 fog 比 fadeout 多 1000ms
                    self.fog_end_time = self.fadeout_end_time + 1000

                self.env.paddle_color = self.paddle_color
                self._update_shockwaves()
                self._update_trail()
        else:
            # 不再 active => 可能 fadeout or just ended
            if self.fadeout_active:
                ratio = self._get_fadeout_ratio()
                if ratio <= 0.0:
                    self.fadeout_active = False
                    self.fog_active = False
                    self.env.paddle_color = None
                    self.shockwaves.clear()
                    self.player_trail.clear()
                else:
                    # 繼續讓shockwave/trail顯示
                    pass
            else:
                # 真的結束 => time_scale=1
                self.env.time_scale = self.normal_time_scale
                if self.fog_active:
                    # 如果還有fog => 也順便檢查
                    if cur > self.fog_end_time:
                        self.fog_active = False
                        self.env.paddle_color = None
                        self.shockwaves.clear()
                self.player_trail.clear()

    def deactivate(self):
        if self.active:
            self.active = False
            cur = pygame.time.get_ticks()
            self.cooldown_start_time = cur
            self.env.sound_manager.stop_slowmo()
            # 進入fadeout
            self.fadeout_active = True
            self.fadeout_end_time = cur + self.fadeout_duration_ms
            if not self.fog_active:
                self.fog_active = True
                self.fog_end_time = self.fadeout_end_time

    def is_active(self):
        return self.active

    def get_cooldown_seconds(self):
        cur = pygame.time.get_ticks()
        elapsed = cur - self.cooldown_start_time
        remain = max(0, self.cooldown_ms - elapsed)
        return remain/1000

    def get_energy_ratio(self):
        cur = pygame.time.get_ticks()
        if self.active:
            e= cur - self.activated_time
            return max(0, (self.duration_ms- e)/ self.duration_ms)
        else:
            e= cur- self.cooldown_start_time
            return min(1.0, e/ self.cooldown_ms)

    def _get_fadeout_ratio(self):
        cur = pygame.time.get_ticks()
        left = self.fadeout_end_time - cur
        return left / float(self.fadeout_duration_ms)

    def _update_shockwaves(self):
        if self.last_slowmo_frame <=0:
            cx = int(self.env.player_x * self.env.render_size)
            cy = int((1 - self.env.paddle_height/self.env.render_size) * self.env.render_size)
            self.shockwaves.append({"cx":cx,"cy":cy,"radius":0})
            self.last_slowmo_frame=1
        else:
            self.last_slowmo_frame+=1

        for w in self.shockwaves:
            w["radius"] +=30

    def _update_trail(self):
        self.player_trail.append(self.env.player_x)
        if len(self.player_trail)> self.max_trail_length:
            self.player_trail.pop(0)

    def render(self, surface):
        cur = pygame.time.get_ticks()

        # fog or fadeout 的 alpha計算
        alpha_ratio = 1.0
        # fog
        if (not self.active) and self.fog_active and (not self.fadeout_active):
            ratio = max(0.0, (self.fog_end_time - cur)/ self.fog_duration_ms)
            alpha_ratio = ratio

        # 若正處於 fadeout -> 也要用 fadeout ratio
        if self.fadeout_active:
            ratio = self._get_fadeout_ratio()
            if self.fog_active:
                ratio_fog = max(0.0, (self.fog_end_time - cur)/ self.fog_duration_ms)
                ratio = min(ratio, ratio_fog)
            alpha_ratio = max(0, ratio)

        # 1) shockwave 繪製
        if self.shockwaves:
            base_fill_alpha = 80
            base_border_alpha = 200
            final_fill_alpha = int(base_fill_alpha * alpha_ratio)
            final_border_alpha = int(base_border_alpha * alpha_ratio)
            if final_fill_alpha>0 or final_border_alpha>0:
                keep_list= []
                for wave in self.shockwaves:
                    overlay= pygame.Surface((self.env.render_size, self.env.render_size+200), pygame.SRCALPHA)
                    fill_color= (50,150,255, final_fill_alpha)
                    border_color= (255,255,255, final_border_alpha)
                    pygame.draw.circle(overlay, fill_color, (wave["cx"], wave["cy"]), wave["radius"])
                    pygame.draw.circle(overlay, border_color, (wave["cx"], wave["cy"]), wave["radius"], width=6)
                    surface.blit(overlay,(0,0))
                    if final_fill_alpha>0 or final_border_alpha>0:
                        keep_list.append(wave)
                self.shockwaves= keep_list
            else:
                self.shockwaves.clear()

        # 2) 板子殘影 (畫在板子後面)
        for i, trail_x in enumerate(self.player_trail):
            # i越大 => 越舊 => alpha越大
            fade_idx_ratio = (i+1)/ len(self.player_trail)
            base_alpha = int(200* fade_idx_ratio)
            final_alpha = int(base_alpha * alpha_ratio)
            w= self.env.player_paddle_width
            h= self.env.paddle_height

            sur= pygame.Surface((w,h), pygame.SRCALPHA)
            color= (*self.trail_color, final_alpha)
            sur.fill(color)

            # 修正: offset_y + render_size - h
            real_y = self.offset_y + self.env.render_size - h
            real_x = trail_x*self.env.render_size - (w/2)
            surface.blit(sur, (int(real_x), int(real_y)))

        # 3) 時鐘 (clock)
        if self.active or self.fog_active or self.fadeout_active:
            base_clock_color_rgb= self.clock_color[:3]
            base_clock_alpha= self.clock_color[3]
            final_clock_alpha= int(base_clock_alpha* alpha_ratio)
            if final_clock_alpha>0:
                e_ratio= self.get_energy_ratio() if self.active else 0
                angle_deg= (1- e_ratio)*360
                angle_rad= math.radians(angle_deg)

                clock_surf= pygame.Surface((self.clock_radius*2+10, self.clock_radius*2+10), pygame.SRCALPHA)
                fillcol= (*base_clock_color_rgb, final_clock_alpha)
                center= (self.clock_radius+5, self.clock_radius+5)
                pygame.draw.circle(clock_surf, fillcol, center, self.clock_radius)

                final_needle_alpha= int(255* alpha_ratio)
                final_needle_color= (255,255,255, final_needle_alpha)

                needle_length= self.clock_radius-5
                nx= center[0]+ needle_length* math.cos(angle_rad- math.pi/2)
                ny= center[1]+ needle_length* math.sin(angle_rad- math.pi/2)
                pygame.draw.line(clock_surf, final_needle_color, center, (nx, ny), self.clock_line_width)

                scr_center= (self.env.render_size//2, self.env.render_size//2)
                rect= clock_surf.get_rect(center= scr_center)
                surface.blit(clock_surf, rect)
