# pong-soul/game/skills/slowmo_skill.py

import math
import pygame
from game.skills.base_skill import Skill
from game.skills.skill_config import SKILL_CONFIGS

DEBUG_SKILL_SLOWMO = True # 啟用此文件內的詳細日誌

class SlowMoSkill(Skill):
    def __init__(self, env, owner_player_state):
        super().__init__(env, owner_player_state)
        cfg_key = "slowmo"
        if cfg_key not in SKILL_CONFIGS:
            print(f"[SKILL_DEBUG][SlowMoSkill] ({self.owner.identifier}) CRITICAL: Config for '{cfg_key}' not found! Using defaults.")
            cfg = {
                "duration_ms": 3000, "cooldown_ms": 5000, "fog_duration_ms": 4000,
                "paddle_color": (0, 150, 255), "trail_color": (0, 200, 255), "max_trail_length": 15,
                "clock_color": (255, 255, 255, 100), "clock_radius": 50, "clock_line_width": 4,
                "slow_time_scale": 0.2, "fadeout_duration_ms": 1500,
                "shockwave_max_radius_px": 10000, # ⭐️ 將預設最大半徑設得非常大，確保它能持續擴散
                "shockwave_expand_speed_px": 15
            }
        else:
            cfg = SKILL_CONFIGS[cfg_key]

        self.duration_ms = int(cfg["duration_ms"])
        self.cooldown_ms = int(cfg["cooldown_ms"])
        self.active = False
        self.activated_time = 0
        self.cooldown_start_time = 0
        self.shockwaves = []
        self.fog_duration_ms = int(cfg.get("fog_duration_ms", self.duration_ms + 1000))
        self.fog_active = False
        self.fog_end_time = 0
        self.owner_skill_paddle_color = cfg.get("paddle_color", (0, 150, 255))
        self.trail_color = cfg.get("trail_color", (0, 200, 255))
        self.max_trail_length = int(cfg.get("max_trail_length", 15))
        self.owner_trail_positions_x = []
        self.clock_color = cfg.get("clock_color", (255, 255, 255, 100))
        self.clock_radius = int(cfg.get("clock_radius", 50))
        self.clock_line_width = int(cfg.get("clock_line_width", 4))
        self.slow_time_scale_value = float(cfg.get("slow_time_scale", 0.2))
        self.normal_time_scale_value = 1.0
        self.fadeout_active = False
        self.fadeout_duration_ms = int(cfg.get("fadeout_duration_ms", 1500))
        self.fadeout_end_time = 0
        
        # ⭐️ shockwave_max_radius_px 仍然可以從配置讀取，但 update 邏輯改變
        self.shockwave_max_radius_config = int(cfg.get("shockwave_max_radius_px", 10000)) # 用於潛在的未來限制
        self.shockwave_expand_speed_px = int(cfg.get("shockwave_expand_speed_px", 15))

        if DEBUG_SKILL_SLOWMO:
            print(f"[SKILL_DEBUG][SlowMoSkill] ({self.owner.identifier}) Initialized. Duration: {self.duration_ms}ms, TimeScale: {self.slow_time_scale_value}, ShockwaveMaxRadiusConfig: {self.shockwave_max_radius_config}px")

    def activate(self):
        cur = pygame.time.get_ticks()
        if not self.active and (self.cooldown_start_time == 0 or (cur - self.cooldown_start_time >= self.cooldown_ms)):
            self.active = True
            self.activated_time = cur
            self.owner.paddle_color = self.owner_skill_paddle_color
            self.fog_active = True
            self.fog_end_time = cur + self.fog_duration_ms
            self.shockwaves.clear() 
            self.owner_trail_positions_x.clear()
            self.fadeout_active = False

            owner_paddle_center_x_norm = self.owner.x
            if self.owner.identifier == "player1":
                owner_paddle_y_surface_norm = 1.0 - self.env.paddle_height_normalized
            else: 
                owner_paddle_y_surface_norm = self.env.paddle_height_normalized
            
            self.shockwaves.append({
                "cx_norm": owner_paddle_center_x_norm,
                "cy_norm": owner_paddle_y_surface_norm,
                "radius_px": 0,
                # "max_radius_px" : self.shockwave_max_radius_config, # 儲存配置的最大半徑，但不在 update 中強制使用
                "expand_speed_px": self.shockwave_expand_speed_px 
            })
            if DEBUG_SKILL_SLOWMO: print(f"[SKILL_DEBUG][SlowMoSkill] ({self.owner.identifier}) Shockwave created at activate.")

            if hasattr(self.env, 'sound_manager'): self.env.sound_manager.play_slowmo()
            if DEBUG_SKILL_SLOWMO: print(f"[SKILL_DEBUG][SlowMoSkill] ({self.owner.identifier}) Activated! Fog ends at {self.fog_end_time}. Paddle color: {self.owner.paddle_color}")
            return True
        
        if DEBUG_SKILL_SLOWMO: print(f"[SKILL_DEBUG][SlowMoSkill] ({self.owner.identifier}) Activation failed (active: {self.active}, cooldown: {self.get_cooldown_seconds():.1f}s).")
        return False

    def update(self):
        cur = pygame.time.get_ticks()

        # 技能效果更新 (衝擊波和軌跡)
        # 這些效果即使在 fadeout 期間也可能需要更新其狀態 (例如半徑、位置)
        if self.active or self.fadeout_active:
            self._update_shockwaves() 
        if self.active: # 軌跡只在技能活躍時更新
            self._update_trail()

        # 技能狀態轉換
        if self.active:
            if (cur - self.activated_time) >= self.duration_ms:
                if DEBUG_SKILL_SLOWMO: print(f"[SKILL_DEBUG][SlowMoSkill] ({self.owner.identifier}) Duration expired. Deactivating.")
                self.deactivate()

        if self.fog_active and cur > self.fog_end_time:
            if DEBUG_SKILL_SLOWMO: print(f"[SKILL_DEBUG][SlowMoSkill] ({self.owner.identifier}) Fog duration expired.")
            self.fog_active = False

        if self.fadeout_active: 
            if cur > self.fadeout_end_time:
                if DEBUG_SKILL_SLOWMO: print(f"[SKILL_DEBUG][SlowMoSkill] ({self.owner.identifier}) Fadeout finished. Clearing visuals.")
                self.fadeout_active = False
                if self.shockwaves: self.shockwaves.clear()
                if self.owner_trail_positions_x: self.owner_trail_positions_x.clear()
        
        # 如果技能已完全結束（非 active 且非 fadeout），確保清理
        if not self.active and not self.fadeout_active:
            if self.shockwaves:
                if DEBUG_SKILL_SLOWMO: print(f"[SKILL_DEBUG][SlowMoSkill] ({self.owner.identifier}) Clearing shockwaves as skill fully ended.")
                self.shockwaves.clear()
            if self.owner_trail_positions_x: self.owner_trail_positions_x.clear()


    def _update_shockwaves(self):
        # ⭐️ 衝擊波持續擴大，不因達到某個內部 max_radius 而移除
        # 它的生命週期由技能的 active 和 fadeout 狀態決定
        for wave in self.shockwaves:
            wave["radius_px"] += wave["expand_speed_px"]
            # 可以選擇性地在這裡加一個非常非常大的上限防止溢位，但通常不需要
            # if wave["radius_px"] > 2000: wave["radius_px"] = 2000 
        # 此處不再有 active_shockwaves 列表和移除邏輯

    # --- deactivate, is_active, get_cooldown_seconds, get_energy_ratio, _get_fadeout_ratio, _update_trail, render ---
    # --- 這些方法的實現與上一版本保持一致，所以省略以節省篇幅 ---
    # --- 確保 render 方法能夠正確處理 self.shockwaves 中可能存在的單個、持續擴大的衝擊波 ---

    def deactivate(self):
        was_truly_active_or_fading = self.active or self.fadeout_active
        if self.active: 
            self.cooldown_start_time = pygame.time.get_ticks() 
            self.fadeout_active = True 
            self.fadeout_end_time = self.cooldown_start_time + self.fadeout_duration_ms
            if DEBUG_SKILL_SLOWMO: print(f"[SKILL_DEBUG][SlowMoSkill] ({self.owner.identifier}) Deactivating from ACTIVE. Cooldown & Fadeout start. Fadeout ends: {self.fadeout_end_time}")
        self.active = False 
        if was_truly_active_or_fading : 
            self.owner.paddle_color = self.owner.base_paddle_color
            if hasattr(self.env, 'sound_manager'): self.env.sound_manager.stop_slowmo()
            if DEBUG_SKILL_SLOWMO: print(f"[SKILL_DEBUG][SlowMoSkill] ({self.owner.identifier}) Deactivated. Paddle color restored.")

    def is_active(self):
        return self.active

    def get_cooldown_seconds(self):
        if self.active: return 0.0
        current_time = pygame.time.get_ticks()
        if self.cooldown_start_time == 0: return 0.0 
        elapsed = current_time - self.cooldown_start_time
        remaining = self.cooldown_ms - elapsed
        return max(0.0, remaining / 1000.0)

    def get_energy_ratio(self):
        current_time = pygame.time.get_ticks()
        if self.active:
            elapsed_duration = current_time - self.activated_time
            ratio = (self.duration_ms - elapsed_duration) / self.duration_ms if self.duration_ms > 0 else 0.0
            return max(0.0, ratio)
        else:
            if self.cooldown_start_time == 0 or (current_time - self.cooldown_start_time >= self.cooldown_ms):
                 return 1.0 
            elapsed_cooldown = current_time - self.cooldown_start_time
            ratio = elapsed_cooldown / self.cooldown_ms if self.cooldown_ms > 0 else 1.0
            return min(1.0, ratio)

    def _get_fadeout_ratio(self):
        if not self.fadeout_active: return 0.0 
        cur = pygame.time.get_ticks()
        remaining_fade_time = self.fadeout_end_time - cur
        if remaining_fade_time <= 0: return 0.0
        return remaining_fade_time / float(self.fadeout_duration_ms)
    
    def _update_trail(self):
        self.owner_trail_positions_x.append(self.owner.x)
        if len(self.owner_trail_positions_x) > self.max_trail_length:
            self.owner_trail_positions_x.pop(0)

    def render(self, surface):
        if not hasattr(self.env, 'renderer') or self.env.renderer is None:
            if DEBUG_SKILL_SLOWMO: print(f"[SKILL_DEBUG][SlowMoSkill.render] ({self.owner.identifier}) Renderer not available. Skipping render.")
            return

        final_alpha_ratio = 1.0
        if self.fadeout_active:
            final_alpha_ratio = self._get_fadeout_ratio()
        
        if final_alpha_ratio <= 0.01 and not self.active : 
            if self.shockwaves: self.shockwaves.clear()
            if self.owner_trail_positions_x: self.owner_trail_positions_x.clear()
            return

        # 1) 衝擊波繪製
        if self.shockwaves: # 現在 self.shockwaves 應該只包含一個持續擴大的衝擊波
            base_fill_alpha = 80; base_border_alpha = 200
            fill_color_rgb = (50, 150, 255); border_color_rgb = (255, 255, 255)
            final_fill_alpha = int(base_fill_alpha * final_alpha_ratio)
            final_border_alpha = int(base_border_alpha * final_alpha_ratio)

            # 即使衝擊波列表為空，alpha > 0 也可能讓這裡執行，所以再次檢查 self.shockwaves
            if (final_fill_alpha > 0 or final_border_alpha > 0) and self.shockwaves:
                for wave in self.shockwaves: # 理論上只有一個 wave
                    cx_px = int(wave["cx_norm"] * self.env.render_size)
                    cy_game_px = int(wave["cy_norm"] * self.env.render_size)
                    cy_screen_px = cy_game_px + self.env.renderer.offset_y 
                    current_radius_px = int(wave["radius_px"])

                    if current_radius_px > 0:
                        if final_fill_alpha > 0:
                            # 畫填充圓時，可以考慮不使用臨時surface以簡化，但透明度混合可能略有不同
                            # pygame.draw.circle(surface, (*fill_color_rgb, final_fill_alpha), 
                            #                    (cx_px, cy_screen_px), current_radius_px) # 這種畫法 pygame 可能不支持帶 alpha 的直接繪製
                            # 使用臨時 surface 處理 alpha 仍然是比較可靠的方式
                            temp_circle_surf = pygame.Surface((current_radius_px * 2, current_radius_px * 2), pygame.SRCALPHA)
                            pygame.draw.circle(temp_circle_surf, (*fill_color_rgb, final_fill_alpha), 
                                               (current_radius_px, current_radius_px), current_radius_px)
                            surface.blit(temp_circle_surf, (cx_px - current_radius_px, cy_screen_px - current_radius_px))
                        
                        if final_border_alpha > 0:
                             pygame.draw.circle(surface, (*border_color_rgb, final_border_alpha),
                                               (cx_px, cy_screen_px), current_radius_px, width=max(1, int(6 * final_alpha_ratio)))
        
        # 2) 球拍軌跡繪製 (保持不變)
        if self.owner_trail_positions_x:
            owner_paddle_width_px = self.owner.paddle_width 
            owner_paddle_height_px = self.env.paddle_height_px 
            if self.owner.identifier == "player1":
                rect_y_screen_px = self.env.renderer.offset_y + self.env.render_size - owner_paddle_height_px
            else: 
                rect_y_screen_px = self.env.renderer.offset_y
            for i, trail_x_norm in enumerate(self.owner_trail_positions_x):
                trail_alpha_ratio_local = (i + 1) / len(self.owner_trail_positions_x) 
                base_alpha = int(150 * trail_alpha_ratio_local) 
                final_alpha = int(base_alpha * final_alpha_ratio)
                if final_alpha > 0:
                    trail_color_rgb = self.trail_color[:3] 
                    rect_x_center_px = int(trail_x_norm * self.env.render_size)
                    rect_x_screen_px = rect_x_center_px - owner_paddle_width_px // 2
                    trail_surf = pygame.Surface((owner_paddle_width_px, owner_paddle_height_px), pygame.SRCALPHA)
                    trail_surf.fill((*trail_color_rgb, final_alpha))
                    surface.blit(trail_surf, (rect_x_screen_px, rect_y_screen_px))

        # 3) 時鐘 UI 繪製 (保持不變)
        should_draw_clock = self.active or (self.fadeout_active and final_alpha_ratio > 0.01) or \
                            (self.fog_active and final_alpha_ratio > 0.01) 
        if should_draw_clock:
            if DEBUG_SKILL_SLOWMO: print(f"[SKILL_DEBUG][SlowMoSkill.render] ({self.owner.identifier}) Conditions met for clock. Active: {self.active}, Fadeout: {self.fadeout_active}, Fog: {self.fog_active}, final_alpha_ratio: {final_alpha_ratio:.2f}")
            clock_rgb = self.clock_color[:3]
            base_clock_alpha = self.clock_color[3] if len(self.clock_color) > 3 else 100
            final_clock_alpha = int(base_clock_alpha * final_alpha_ratio)
            if DEBUG_SKILL_SLOWMO: print(f"[SKILL_DEBUG][SlowMoSkill.render] ({self.owner.identifier}) Clock final_clock_alpha: {final_clock_alpha}")
            if final_clock_alpha > 0:
                energy_display_ratio = self.get_energy_ratio() if self.active else 0.0 
                angle_deg = (1.0 - energy_display_ratio) * 360.0
                angle_rad = math.radians(angle_deg)
                if DEBUG_SKILL_SLOWMO: print(f"[SKILL_DEBUG][SlowMoSkill.render] ({self.owner.identifier}) Clock energy_ratio: {energy_display_ratio:.2f}, angle_deg: {angle_deg:.1f}")
                screen_center_x = surface.get_width() // 2
                screen_center_y = surface.get_height() // 2
                if DEBUG_SKILL_SLOWMO: print(f"[SKILL_DEBUG][SlowMoSkill.render] ({self.owner.identifier}) Clock target screen center: ({screen_center_x}, {screen_center_y})")
                clock_surface_size = self.clock_radius * 2 + self.clock_line_width * 2 
                clock_surf = pygame.Surface((clock_surface_size, clock_surface_size), pygame.SRCALPHA)
                center_on_clock_surf = (clock_surface_size // 2, clock_surface_size // 2)
                pygame.draw.circle(clock_surf, (*clock_rgb, final_clock_alpha), center_on_clock_surf, self.clock_radius)
                needle_base_alpha = 255 
                final_needle_alpha = int(needle_base_alpha * final_alpha_ratio)
                if final_needle_alpha > 0: 
                    needle_color = (255, 255, 255, final_needle_alpha) 
                    needle_length = self.clock_radius - (self.clock_line_width // 2) 
                    start_angle_rad = -math.pi / 2 
                    current_angle_rad = start_angle_rad + angle_rad
                    nx = center_on_clock_surf[0] + needle_length * math.cos(current_angle_rad)
                    ny = center_on_clock_surf[1] + needle_length * math.sin(current_angle_rad)
                    pygame.draw.line(clock_surf, needle_color, center_on_clock_surf, (nx, ny), self.clock_line_width)
                clock_rect = clock_surf.get_rect(center=(screen_center_x, screen_center_y))
                surface.blit(clock_surf, clock_rect)
                if DEBUG_SKILL_SLOWMO: print(f"[SKILL_DEBUG][SlowMoSkill.render] ({self.owner.identifier}) Clock blitted at {clock_rect.topleft}, center {clock_rect.center}")