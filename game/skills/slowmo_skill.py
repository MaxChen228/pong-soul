# pong-soul/game/skills/slowmo_skill.py

import math
import pygame
from game.skills.base_skill import Skill
from game.skills.skill_config import SKILL_CONFIGS
from game.theme import Style # 為了 Style.PLAYER_COLOR 等

DEBUG_SKILL_SLOWMO = False # 您原有的 DEBUG 開關

class SlowMoSkill(Skill):
    def __init__(self, env, owner_player_state):
        super().__init__(env, owner_player_state)
        cfg_key = "slowmo"
        # ⭐️ 從 SKILL_CONFIGS 獲取設定，如果 key 不存在，cfg 會是空字典或 None (取決於 get 实现)
        #    我們的 skill_config.py 在載入失敗時 SKILL_CONFIGS 會是 {}
        cfg = SKILL_CONFIGS.get(cfg_key, {}) # 使用 .get() 避免 KeyError，並提供預設空字典

        if not cfg: # 如果 SKILL_CONFIGS 中沒有 "slowmo" 或載入失敗
            print(f"[SKILL_DEBUG][SlowMoSkill] ({self.owner.identifier}) CRITICAL: Config for '{cfg_key}' not found in SKILL_CONFIGS! Using internal defaults.")
            # 技能內部預設值 (如果 SKILL_CONFIGS 中完全沒有 "slowmo")
            internal_default_cfg = {
                "duration_ms": 3000, "cooldown_ms": 5000, "fog_duration_ms": 4000,
                "paddle_color": (0, 150, 255), "trail_color": (0, 200, 255), "max_trail_length": 15,
                "clock_color": (255, 255, 255, 100), "clock_radius_logic_px": 50,
                "clock_line_width_logic_px": 4,
                "slow_time_scale": 0.2, "fadeout_duration_ms": 1500,
                "shockwave_max_radius_logic_px": 10000,
                "shockwave_expand_speed_logic_px": 15,
                "owner_paddle_speed_multiplier": 1.0 # ⭐️ 內部預設的板子速度倍率為 1.0 (無效果)
            }
            cfg = internal_default_cfg

        self.duration_ms = int(cfg.get("duration_ms", 3000))
        self.cooldown_ms = int(cfg.get("cooldown_ms", 5000))
        self.active = False
        self.activated_time = 0
        self.cooldown_start_time = 0
        
        self.shockwaves = []
        
        self.fog_duration_ms = int(cfg.get("fog_duration_ms", self.duration_ms + 1000))
        self.fog_active = False
        self.fog_end_time = 0
        
        self.owner_skill_paddle_color = tuple(cfg.get("paddle_color", (0, 150, 255)))
        self.trail_color = tuple(cfg.get("trail_color", (0, 200, 255)))
        self.max_trail_length = int(cfg.get("max_trail_length", 15))
        self.owner_trail_positions_x_norm = []

        self.clock_color = tuple(cfg.get("clock_color", (255, 255, 255, 100)))
        self.clock_radius_logic_px = int(cfg.get("clock_radius_logic_px", cfg.get("clock_radius", 50))) # 兼容舊的 clock_radius
        self.clock_line_width_logic_px = int(cfg.get("clock_line_width_logic_px", cfg.get("clock_line_width", 4))) # 兼容舊的 clock_line_width
        
        self.slow_time_scale_value = float(cfg.get("slow_time_scale", 0.2))
        self.normal_time_scale_value = 1.0
        
        self.fadeout_active = False
        self.fadeout_duration_ms = int(cfg.get("fadeout_duration_ms", 1500))
        self.fadeout_end_time = 0
        
        self.shockwave_expand_speed_logic_px = int(cfg.get("shockwave_expand_speed_logic_px", 15))
        
        # ⭐️ 讀取使用者板子速度倍率，如果 YAML 中沒有則預設為 1.0 (無加速效果)
        self.owner_paddle_speed_multiplier = float(cfg.get("owner_paddle_speed_multiplier", 1.0))

        if DEBUG_SKILL_SLOWMO:
            print(f"[SKILL_DEBUG][SlowMoSkill] ({self.owner.identifier}) Initialized. Duration: {self.duration_ms}ms, TimeScale: {self.slow_time_scale_value}, OwnerPaddleSpeedMult: {self.owner_paddle_speed_multiplier}")
            # ... (其他 debug 輸出)

    def activate(self):
        cur = pygame.time.get_ticks()
        if not self.active and (self.cooldown_start_time == 0 or (cur - self.cooldown_start_time >= self.cooldown_ms)):
            self.active = True
            self.activated_time = cur
            self.owner.paddle_color = self.owner_skill_paddle_color
            
            # ⭐️ 設定擁有者的板子速度倍率
            if hasattr(self.owner, 'current_paddle_speed_multiplier'):
                self.owner.current_paddle_speed_multiplier = self.owner_paddle_speed_multiplier
                if DEBUG_SKILL_SLOWMO:
                    print(f"[SKILL_DEBUG][SlowMoSkill] ({self.owner.identifier}) Set owner paddle speed multiplier to: {self.owner_paddle_speed_multiplier}")
            else:
                if DEBUG_SKILL_SLOWMO:
                    print(f"[SKILL_DEBUG][SlowMoSkill] ({self.owner.identifier}) WARNING: Owner has no attribute 'current_paddle_speed_multiplier'.")

            self.fog_active = True
            self.fog_end_time = cur + self.fog_duration_ms
            
            self.shockwaves.clear()
            self.owner_trail_positions_x_norm.clear()
            self.fadeout_active = False

            owner_paddle_center_x_norm = self.owner.x
            paddle_surface_offset_norm = self.env.paddle_height_normalized / 2

            if self.owner == self.env.player1:
                owner_paddle_y_surface_norm = 1.0 - self.env.paddle_height_normalized
            else:
                owner_paddle_y_surface_norm = self.env.paddle_height_normalized
            
            self.shockwaves.append({
                "cx_norm": owner_paddle_center_x_norm,
                "cy_norm": owner_paddle_y_surface_norm,
                "current_radius_logic_px": 0,
                "expand_speed_logic_px": self.shockwave_expand_speed_logic_px
            })
            
            if hasattr(self.env, 'sound_manager'): self.env.sound_manager.play_slowmo()
            if DEBUG_SKILL_SLOWMO:
                print(f"[SKILL_DEBUG][SlowMoSkill] ({self.owner.identifier}) Activated! Fog ends at {self.fog_end_time}. Paddle color: {self.owner.paddle_color}")
            return True
        
        if DEBUG_SKILL_SLOWMO:
            print(f"[SKILL_DEBUG][SlowMoSkill] ({self.owner.identifier}) Activation failed (active: {self.active}, cooldown: {self.get_cooldown_seconds():.1f}s).")
        return False

    def update(self): # 此 update 主要管理技能的持續時間和狀態轉換
        # ... (原有的 update 內容不變，主要是時間和視覺效果的更新) ...
        cur = pygame.time.get_ticks()

        if self.active:
            for wave in self.shockwaves:
                wave["current_radius_logic_px"] += wave["expand_speed_logic_px"]

            self.owner_trail_positions_x_norm.append(self.owner.x)
            if len(self.owner_trail_positions_x_norm) > self.max_trail_length:
                self.owner_trail_positions_x_norm.pop(0)

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
                self.shockwaves.clear()
                self.owner_trail_positions_x_norm.clear()

        if not self.active and not self.fadeout_active:
            if self.shockwaves: self.shockwaves.clear()
            if self.owner_trail_positions_x_norm: self.owner_trail_positions_x_norm.clear()


    def deactivate(self):
        was_truly_active_or_fading = self.active or self.fadeout_active
        
        # ⭐️ 重置擁有者的板子速度倍率，無論如何都應執行（只要技能曾 active 過）
        if self.active or self.fadeout_active: # 確保只有當技能真正作用過才重置
            if hasattr(self.owner, 'current_paddle_speed_multiplier'):
                self.owner.current_paddle_speed_multiplier = 1.0 # 恢復正常速度倍率
                if DEBUG_SKILL_SLOWMO:
                    print(f"[SKILL_DEBUG][SlowMoSkill] ({self.owner.identifier}) Reset owner paddle speed multiplier to 1.0.")
        
        if self.active:
            self.cooldown_start_time = pygame.time.get_ticks()
            self.fadeout_active = True
            self.fadeout_end_time = self.cooldown_start_time + self.fadeout_duration_ms
            if DEBUG_SKILL_SLOWMO: print(f"[SKILL_DEBUG][SlowMoSkill] ({self.owner.identifier}) Deactivating from ACTIVE. Cooldown & Fadeout start. Fadeout ends: {self.fadeout_end_time}")
        
        self.active = False
        
        if was_truly_active_or_fading:
            self.owner.paddle_color = self.owner.base_paddle_color
            if hasattr(self.env, 'sound_manager'): self.env.sound_manager.stop_slowmo()
            if DEBUG_SKILL_SLOWMO: print(f"[SKILL_DEBUG][SlowMoSkill] ({self.owner.identifier}) Deactivated. Paddle color restored.")

    # ... (is_active, get_cooldown_seconds, get_energy_ratio, _get_fadeout_ratio, render, get_visual_params 方法不變) ...
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

    def _get_fadeout_ratio(self): # 計算淡出進度 (1.0 -> 0.0)
        if not self.fadeout_active: return 0.0
        cur = pygame.time.get_ticks()
        remaining_fade_time = self.fadeout_end_time - cur
        if remaining_fade_time <= 0: return 0.0
        return remaining_fade_time / float(self.fadeout_duration_ms)


    def render(self, surface, game_render_area_on_screen, scale_factor, is_owner_bottom_perspective_in_this_area):
        pass

    def get_visual_params(self):
        if not self.active and not self.fadeout_active:
            return {"type": "slowmo", "active_effects": False}

        current_alpha_ratio = 1.0
        if self.fadeout_active:
            current_alpha_ratio = self._get_fadeout_ratio()

        if current_alpha_ratio <= 0.01 and not self.active:
            return {"type": "slowmo", "active_effects": False}

        shockwave_params_list = []
        if self.shockwaves:
            base_fill_alpha = 60
            base_border_alpha = 180
            fill_color_rgb = (50, 150, 255)
            border_color_rgb = (200, 220, 255)
            final_fill_alpha = int(base_fill_alpha * current_alpha_ratio)
            final_border_alpha = int(base_border_alpha * current_alpha_ratio)

            for wave in self.shockwaves:
                shockwave_params_list.append({
                    "cx_norm": wave["cx_norm"],
                    "cy_norm": wave["cy_norm"],
                    "current_radius_logic_px": wave["current_radius_logic_px"],
                    "fill_color_rgba": (*fill_color_rgb, final_fill_alpha),
                    "border_color_rgba": (*border_color_rgb, final_border_alpha),
                    "border_width_logic_px": 4
                })

        paddle_trail_params_list = []
        if self.owner_trail_positions_x_norm:
            for i, trail_x_norm in enumerate(self.owner_trail_positions_x_norm):
                trail_alpha_ratio_local = (i + 1) / len(self.owner_trail_positions_x_norm)
                base_alpha = int(120 * trail_alpha_ratio_local)
                final_trail_alpha = int(base_alpha * current_alpha_ratio)
                trail_color_rgb = self.trail_color[:3]

                if final_trail_alpha > 0:
                    paddle_trail_params_list.append({
                        "x_norm": trail_x_norm,
                        "color_rgba": (*trail_color_rgb, final_trail_alpha)
                    })

        clock_param = None
        should_draw_clock = self.active or (self.fadeout_active and current_alpha_ratio > 0.01)
        if should_draw_clock:
            clock_rgb = self.clock_color[:3]
            base_clock_alpha = self.clock_color[3] if len(self.clock_color) > 3 else 100
            final_clock_alpha = int(base_clock_alpha * current_alpha_ratio)

            if final_clock_alpha > 0:
                energy_display_ratio = self.get_energy_ratio() if self.active else 0.0
                clock_param = {
                    "is_visible": True,
                    "radius_logic_px": self.clock_radius_logic_px,
                    "line_width_logic_px": self.clock_line_width_logic_px,
                    "color_rgba": (*clock_rgb, final_clock_alpha),
                    "progress_ratio": energy_display_ratio
                }

        return {
            "type": "slowmo",
            "active_effects": True,
            "shockwaves": shockwave_params_list,
            "paddle_trails": paddle_trail_params_list,
            "clock": clock_param,
            "owner_paddle_width_logic_px": self.owner.base_paddle_width,
            "owner_paddle_height_logic_px": self.env.paddle_height_px
        }