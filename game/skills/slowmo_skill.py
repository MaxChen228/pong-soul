# pong-soul/game/skills/slowmo_skill.py

import math
import pygame
from game.skills.base_skill import Skill
from game.skills.skill_config import SKILL_CONFIGS
from game.theme import Style # 為了 Style.PLAYER_COLOR 等

DEBUG_SKILL_SLOWMO = False

class SlowMoSkill(Skill):
    def __init__(self, env, owner_player_state):
        super().__init__(env, owner_player_state)
        cfg_key = "slowmo"
        if cfg_key not in SKILL_CONFIGS:
            print(f"[SKILL_DEBUG][SlowMoSkill] ({self.owner.identifier}) CRITICAL: Config for '{cfg_key}' not found! Using defaults.")
            cfg = { # 提供最小預設值
                "duration_ms": 3000, "cooldown_ms": 5000, "fog_duration_ms": 4000,
                "paddle_color": (0, 150, 255), "trail_color": (0, 200, 255), "max_trail_length": 15,
                "clock_color": (255, 255, 255, 100), "clock_radius_logic_px": 50, # 改為邏輯像素
                "clock_line_width_logic_px": 4, # 改為邏輯像素
                "slow_time_scale": 0.2, "fadeout_duration_ms": 1500,
                "shockwave_max_radius_logic_px": 10000, # 改為邏輯像素
                "shockwave_expand_speed_logic_px": 15   # 改為邏輯像素
            }
        else:
            cfg = SKILL_CONFIGS[cfg_key]

        self.duration_ms = int(cfg["duration_ms"])
        self.cooldown_ms = int(cfg["cooldown_ms"])
        self.active = False
        self.activated_time = 0
        self.cooldown_start_time = 0
        
        self.shockwaves = [] # 衝擊波列表
        
        self.fog_duration_ms = int(cfg.get("fog_duration_ms", self.duration_ms + 1000))
        self.fog_active = False # 霧效果 (如果有的話，目前主要視覺是衝擊波和時鐘)
        self.fog_end_time = 0
        
        self.owner_skill_paddle_color = cfg.get("paddle_color", (0, 150, 255))
        self.trail_color = cfg.get("trail_color", (0, 200, 255)) # 軌跡顏色
        self.max_trail_length = int(cfg.get("max_trail_length", 15)) # 軌跡最大長度
        self.owner_trail_positions_x_norm = [] # 儲存球拍的正規化 X 座標軌跡

        # 時鐘 UI 參數 (使用邏輯像素)
        self.clock_color = cfg.get("clock_color", (255, 255, 255, 100)) # 時鐘顏色 (RGBA)
        self.clock_radius_logic_px = int(cfg.get("clock_radius_logic_px", 50)) # 時鐘半徑 (邏輯像素)
        self.clock_line_width_logic_px = int(cfg.get("clock_line_width_logic_px", 4)) # 時鐘線條寬度 (邏輯像素)
        
        self.slow_time_scale_value = float(cfg.get("slow_time_scale", 0.2)) # 慢動作的時間尺度
        self.normal_time_scale_value = 1.0 # 正常時間尺度
        
        self.fadeout_active = False # 是否正在淡出
        self.fadeout_duration_ms = int(cfg.get("fadeout_duration_ms", 1500)) # 淡出持續時間
        self.fadeout_end_time = 0
        
        # 衝擊波參數 (使用邏輯像素)
        self.shockwave_expand_speed_logic_px = int(cfg.get("shockwave_expand_speed_logic_px", 15)) # 衝擊波擴展速度 (邏輯像素/幀)
        # self.shockwave_max_radius_config_logic_px = int(cfg.get("shockwave_max_radius_logic_px", 10000)) # 最大半徑 (邏輯像素) - 可選

        if DEBUG_SKILL_SLOWMO:
            print(f"[SKILL_DEBUG][SlowMoSkill] ({self.owner.identifier}) Initialized. Duration: {self.duration_ms}ms, TimeScale: {self.slow_time_scale_value}")
            print(f"    Clock Logic Radius: {self.clock_radius_logic_px}px, Shockwave Logic Speed: {self.shockwave_expand_speed_logic_px}px/frame")

    def activate(self):
        cur = pygame.time.get_ticks()
        if not self.active and (self.cooldown_start_time == 0 or (cur - self.cooldown_start_time >= self.cooldown_ms)):
            self.active = True
            self.activated_time = cur
            self.owner.paddle_color = self.owner_skill_paddle_color # 改變擁有者球拍顏色
            
            self.fog_active = True # 假設霧效果與技能同時啟動
            self.fog_end_time = cur + self.fog_duration_ms
            
            self.shockwaves.clear()
            self.owner_trail_positions_x_norm.clear() # 清除舊軌跡
            self.fadeout_active = False

            # ⭐️ 計算衝擊波初始位置 (正規化座標)
            owner_paddle_center_x_norm = self.owner.x # 技能擁有者的正規化 X 座標
            
            # 判斷擁有者是上方還是下方玩家，以確定球拍表面的 Y 正規化座標
            # 假設 P1 在下方 (Y接近1.0)，Opponent/P2 在上方 (Y接近0.0)
            # 球拍厚度 paddle_height_normalized
            paddle_surface_offset_norm = self.env.paddle_height_normalized / 2 # 從球拍中心到表面的偏移 (近似)

            if self.owner == self.env.player1: # 玩家1在下方，衝擊波從其球拍上表面發出
                owner_paddle_y_surface_norm = 1.0 - self.env.paddle_height_normalized # 球拍頂面Y
            else: # 對手/玩家2在上方，衝擊波從其球拍下表面發出
                owner_paddle_y_surface_norm = self.env.paddle_height_normalized # 球拍底面Y
            
            self.shockwaves.append({
                "cx_norm": owner_paddle_center_x_norm,    # X 中心 (正規化)
                "cy_norm": owner_paddle_y_surface_norm,    # Y 中心 (正規化，球拍表面)
                "current_radius_logic_px": 0,             # 當前半徑 (邏輯像素), 從0開始擴大
                # "max_radius_logic_px": self.shockwave_max_radius_config_logic_px, # 可選的最大半徑
                "expand_speed_logic_px": self.shockwave_expand_speed_logic_px # 擴展速度 (邏輯像素/幀)
            })
            if DEBUG_SKILL_SLOWMO:
                print(f"[SKILL_DEBUG][SlowMoSkill] ({self.owner.identifier}) Shockwave created at activate. Norm Pos: ({owner_paddle_center_x_norm:.2f}, {owner_paddle_y_surface_norm:.2f})")

            if hasattr(self.env, 'sound_manager'): self.env.sound_manager.play_slowmo()
            if DEBUG_SKILL_SLOWMO:
                print(f"[SKILL_DEBUG][SlowMoSkill] ({self.owner.identifier}) Activated! Fog ends at {self.fog_end_time}. Paddle color: {self.owner.paddle_color}")
            return True
        
        if DEBUG_SKILL_SLOWMO:
            print(f"[SKILL_DEBUG][SlowMoSkill] ({self.owner.identifier}) Activation failed (active: {self.active}, cooldown: {self.get_cooldown_seconds():.1f}s).")
        return False

    def update(self): # 此 update 主要管理技能的持續時間和狀態轉換
        cur = pygame.time.get_ticks()

        if self.active: # 如果技能正在生效
            # 更新衝擊波半徑 (邏輯像素)
            for wave in self.shockwaves:
                wave["current_radius_logic_px"] += wave["expand_speed_logic_px"]
                # 可以選擇性地限制最大半徑
                # if wave["current_radius_logic_px"] > wave["max_radius_logic_px"]:
                #     wave["current_radius_logic_px"] = wave["max_radius_logic_px"] # 或者移除此衝擊波

            # 更新軌跡 (記錄正規化X座標)
            self.owner_trail_positions_x_norm.append(self.owner.x)
            if len(self.owner_trail_positions_x_norm) > self.max_trail_length:
                self.owner_trail_positions_x_norm.pop(0)

            # 檢查技能持續時間是否結束
            if (cur - self.activated_time) >= self.duration_ms:
                if DEBUG_SKILL_SLOWMO: print(f"[SKILL_DEBUG][SlowMoSkill] ({self.owner.identifier}) Duration expired. Deactivating.")
                self.deactivate() # 開始冷卻和淡出

        # 霧效果的持續時間管理 (如果有的話)
        if self.fog_active and cur > self.fog_end_time:
            if DEBUG_SKILL_SLOWMO: print(f"[SKILL_DEBUG][SlowMoSkill] ({self.owner.identifier}) Fog duration expired.")
            self.fog_active = False

        # 淡出效果的管理
        if self.fadeout_active:
            if cur > self.fadeout_end_time:
                if DEBUG_SKILL_SLOWMO: print(f"[SKILL_DEBUG][SlowMoSkill] ({self.owner.identifier}) Fadeout finished. Clearing visuals.")
                self.fadeout_active = False
                self.shockwaves.clear() # 清除所有衝擊波
                self.owner_trail_positions_x_norm.clear() # 清除軌跡

        # 如果技能已完全結束（非 active 且非 fadeout），確保清理視覺元素
        if not self.active and not self.fadeout_active:
            if self.shockwaves: self.shockwaves.clear()
            if self.owner_trail_positions_x_norm: self.owner_trail_positions_x_norm.clear()


    def deactivate(self):
        was_truly_active_or_fading = self.active or self.fadeout_active
        if self.active: # 只有當技能是 active 時，停用它才會啟動冷卻和淡出
            self.cooldown_start_time = pygame.time.get_ticks()
            self.fadeout_active = True # 開始淡出
            self.fadeout_end_time = self.cooldown_start_time + self.fadeout_duration_ms
            if DEBUG_SKILL_SLOWMO: print(f"[SKILL_DEBUG][SlowMoSkill] ({self.owner.identifier}) Deactivating from ACTIVE. Cooldown & Fadeout start. Fadeout ends: {self.fadeout_end_time}")
        
        self.active = False # 技能不再生效 (時間尺度恢復等)
        
        if was_truly_active_or_fading: # 只有之前是 active 或正在 fading 時才執行清理
            self.owner.paddle_color = self.owner.base_paddle_color # 恢復球拍顏色
            if hasattr(self.env, 'sound_manager'): self.env.sound_manager.stop_slowmo() # 停止音效
            if DEBUG_SKILL_SLOWMO: print(f"[SKILL_DEBUG][SlowMoSkill] ({self.owner.identifier}) Deactivated. Paddle color restored.")
            # 淡出期間視覺效果的清除在 update 中處理

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
        # Pygame 繪圖邏輯已移至 get_visual_params() 和 Renderer
        pass

    def get_visual_params(self):
        """
        收集 SlowMo 技能的視覺參數，供 Renderer 使用。
        """
        if not self.active and not self.fadeout_active:
            return {"type": "slowmo", "active_effects": False}

        current_alpha_ratio = 1.0
        if self.fadeout_active:
            current_alpha_ratio = self._get_fadeout_ratio()

        if current_alpha_ratio <= 0.01 and not self.active:
            return {"type": "slowmo", "active_effects": False}

        # 衝擊波參數
        shockwave_params_list = []
        if self.shockwaves:
            base_fill_alpha = 60
            base_border_alpha = 180
            fill_color_rgb = (50, 150, 255) # 來自舊 render
            border_color_rgb = (200, 220, 255) # 來自舊 render
            final_fill_alpha = int(base_fill_alpha * current_alpha_ratio)
            final_border_alpha = int(base_border_alpha * current_alpha_ratio)

            for wave in self.shockwaves:
                # 衝擊波的 cx_norm 和 cy_norm 是技能擁有者球拍在 *場地* 中的正規化座標。
                # Renderer 在繪製時需要根據 *當前視角* 來決定這個正規化座標如何映射。
                # 我們在這裡直接傳遞場地座標，Renderer 的 _render_player_view 或其輔助函數
                # 會處理視角轉換（如果需要的話，但 SlowMo 的衝擊波和時鐘通常是畫在視角中心或固定位置）。
                # 對於 SlowMo，衝擊波是從技能擁有者的球拍發出的，所以 cx_norm, cy_norm 是關鍵。
                shockwave_params_list.append({
                    "cx_norm": wave["cx_norm"],
                    "cy_norm": wave["cy_norm"], # 正規化的場地 Y 座標
                    "current_radius_logic_px": wave["current_radius_logic_px"],
                    "fill_color_rgba": (*fill_color_rgb, final_fill_alpha),
                    "border_color_rgba": (*border_color_rgb, final_border_alpha),
                    "border_width_logic_px": 4 # 假設固定的邏輯寬度，Renderer 會縮放它
                })

        # 球拍軌跡參數
        paddle_trail_params_list = []
        if self.owner_trail_positions_x_norm:
            # 軌跡的 Y 位置是固定的（在球拍的 Y 層），X 位置是變化的
            # Renderer 需要知道擁有者的 paddle_width (邏輯) 和 paddle_height (邏輯) 來畫軌跡塊
            for i, trail_x_norm in enumerate(self.owner_trail_positions_x_norm):
                trail_alpha_ratio_local = (i + 1) / len(self.owner_trail_positions_x_norm)
                base_alpha = int(120 * trail_alpha_ratio_local)
                final_trail_alpha = int(base_alpha * current_alpha_ratio)
                trail_color_rgb = self.trail_color[:3] # 來自 cfg

                if final_trail_alpha > 0:
                    paddle_trail_params_list.append({
                        "x_norm": trail_x_norm, # 軌跡塊的中心 X (正規化)
                        "color_rgba": (*trail_color_rgb, final_trail_alpha)
                        # Renderer 還需要知道擁有者的 paddle_width_norm 和 paddle_height_norm
                        # 這個可以從 player_data 中獲取，或者在這裡也包含
                    })

        # 時鐘 UI 參數 (通常在遊戲區域中心)
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
                    "progress_ratio": energy_display_ratio # 0.0 到 1.0
                }

        return {
            "type": "slowmo",
            "active_effects": True,
            "shockwaves": shockwave_params_list,
            "paddle_trails": paddle_trail_params_list,
            "clock": clock_param,
            # 為了讓 Renderer 畫軌跡時知道球拍的邏輯寬高
            # 雖然 Renderer 也可以從 player_data 獲取，但為清晰起見，可在此處提供
            "owner_paddle_width_logic_px": self.owner.base_paddle_width, # 或者 self.owner.paddle_width (當前)
            "owner_paddle_height_logic_px": self.env.paddle_height_px # 從 env 獲取標準邏輯高度
        }