# pong-soul/game/skills/slowmo_skill.py

import math
import pygame
from game.skills.base_skill import Skill
from game.skills.skill_config import SKILL_CONFIGS
from game.theme import Style # 為了 Style.PLAYER_COLOR 等

DEBUG_SKILL_SLOWMO = True

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
        # surface: 主繪圖表面 (main_screen)
        # game_render_area_on_screen: pygame.Rect，技能擁有者的遊戲邏輯區域在 surface 上的實際像素矩形
        # scale_factor: 應用於遊戲內容的縮放因子
        # is_owner_bottom_perspective_in_this_area: 布林值。True表示當前渲染的這個區域是技能擁有者自己作為底部玩家的視角。
        #                                        False表示是在對手視角中渲染此技能效果（如果需要跨視角渲染）。
        #                                        在我們的分屏情況下：
        #                                        - P1用技能，在P1視口渲染 -> True
        #                                        - P2用技能，在P2視口渲染 -> True (因為P2在其視口也看自己為底部)

        if not self.active and not self.fadeout_active:
            return

        current_alpha_ratio = 1.0
        if self.fadeout_active:
            current_alpha_ratio = self._get_fadeout_ratio()
        
        if current_alpha_ratio <= 0.01 and not self.active:
            if self.shockwaves: self.shockwaves.clear()
            if self.owner_trail_positions_x_norm: self.owner_trail_positions_x_norm.clear()
            return

        ga_left = game_render_area_on_screen.left
        ga_top = game_render_area_on_screen.top
        ga_width_scaled = game_render_area_on_screen.width
        ga_height_scaled = game_render_area_on_screen.height

        # 1) 衝擊波繪製
        if self.shockwaves:
            # ... (alpha 和顏色計算不變) ...
            base_fill_alpha = 60; base_border_alpha = 180
            fill_color_rgb = (50, 150, 255); border_color_rgb = (200, 220, 255)
            final_fill_alpha = int(base_fill_alpha * current_alpha_ratio)
            final_border_alpha = int(base_border_alpha * current_alpha_ratio)

            if final_fill_alpha > 0 or final_border_alpha > 0:
                for wave in self.shockwaves:
                    # wave["cx_norm"] 是技能擁有者在場地中的正規化 X (0-1)
                    # wave["cy_norm"] 是技能擁有者在場地中的正規化 Y (0-1, 0=頂, 1=底)
                    
                    # ⭐️ 關鍵修改：根據當前視角調整 Y 座標
                    # is_owner_bottom_perspective_in_this_area 告訴我們，在這個 render_area 中，
                    # 技能擁有者是否被視為底部玩家。
                    # 如果是，那麼其原始的場地Y座標 (wave["cy_norm"]) 需要被正確映射到這個視角的底部。
                    # 然而，wave["cy_norm"] 已經是相對於整個場地的 (0頂, 1底)。
                    # 我們在 _render_player_view 中已經處理了視角的 Y 軸顛倒。
                    # 所以，這裡的 cx_norm, cy_norm 應該可以直接用來計算在 game_render_area_on_screen 內的相對位置。
                    # 問題在於衝擊波的 wave["cy_norm"] 是從誰的球拍發出的。
                    # activate() 中，cy_norm 的計算是正確的，它代表了技能擁有者球拍在場地中的Y。

                    # 衝擊波中心X (相對於 game_render_area 左上角)
                    shockwave_center_x_in_area_scaled = wave["cx_norm"] * ga_width_scaled
                    
                    # 衝擊波中心Y (相對於 game_render_area 左上角)
                    # 如果 is_owner_bottom_perspective_in_this_area 為 True，則 wave["cy_norm"] (場地Y)
                    # 應該映射到此區域的相應Y。
                    # 例如，如果 P2 (opponent, 場地Y約為0.1) 使用技能，並且 is_owner_bottom_perspective_in_this_area 為 True (P2的視口)
                    # 我們希望衝擊波從 P2 視口的底部發出。這意味著 wave["cy_norm"] 需要被 "視角轉換"。
                    
                    # 不，更簡單的邏輯是：
                    # activate 時，cy_norm 存儲的是技能擁有者球拍表面的【正規化場地Y座標】。
                    # P1的球拍表面Y (場地座標系) 在 1.0 - paddle_h_norm 附近。
                    # P2的球拍表面Y (場地座標系) 在 paddle_h_norm 附近。
                    
                    # 在 _render_player_view 中，當 is_top_player_perspective (渲染P2視角) 時，
                    # 場地Y會被 (1.0 - y) 轉換。
                    # 所以，如果技能擁有者是P2 (cy_norm 接近0)，在P2的視角中，這個Y會被畫在頂部。這是問題所在。

                    # 正確的邏輯：衝擊波應該從【當前視角中，技能擁有者的球拍位置】發出。
                    # 我們在 activate 時記錄的是技能擁有者在【場地】中的位置。
                    # 在 render 時，我們需要知道技能擁有者在【當前這個視角】的底部還是頂部。
                    
                    # 獲取技能擁有者在【當前視角下】的球拍Y位置（底部或頂部）
                    owner_paddle_y_on_current_area_norm = 0.0
                    if is_owner_bottom_perspective_in_this_area:
                        # 技能擁有者在此視角中是底部玩家
                        owner_paddle_y_on_current_area_norm = 1.0 - (self.env.paddle_height_normalized / 2) # 近似底部
                    else:
                        # 技能擁有者在此視角中是頂部玩家 (這通常不會發生，因為我們只在自己視角渲染自己技能)
                        # 但為了完整性，如果將來要畫對方技能效果，就需要這個
                        owner_paddle_y_on_current_area_norm = self.env.paddle_height_normalized / 2 # 近似頂部

                    shockwave_center_y_in_area_scaled = owner_paddle_y_on_current_area_norm * ga_height_scaled

                    # 轉換為在 surface 上的絕對像素座標
                    cx_on_surface_px = ga_left + int(shockwave_center_x_in_area_scaled)
                    cy_on_surface_px = ga_top + int(shockwave_center_y_in_area_scaled)
                    
                    current_radius_scaled_px = int(wave["current_radius_logic_px"] * scale_factor)
                    scaled_wave_border_width = max(1, int(4 * scale_factor * current_alpha_ratio))

                    if current_radius_scaled_px > 0:
                        # ... (衝擊波繪製邏輯不變, 使用 cx_on_surface_px, cy_on_surface_px)
                        if final_fill_alpha > 0:
                            temp_circle_surf_size = current_radius_scaled_px * 2
                            if temp_circle_surf_size > 0:
                                temp_circle_surf = pygame.Surface((temp_circle_surf_size, temp_circle_surf_size), pygame.SRCALPHA)
                                pygame.draw.circle(temp_circle_surf, (*fill_color_rgb, final_fill_alpha),
                                                   (current_radius_scaled_px, current_radius_scaled_px), current_radius_scaled_px)
                                surface.blit(temp_circle_surf, (cx_on_surface_px - current_radius_scaled_px, cy_on_surface_px - current_radius_scaled_px))
                        if final_border_alpha > 0 and scaled_wave_border_width > 0:
                             pygame.draw.circle(surface, (*border_color_rgb, final_border_alpha),
                                               (cx_on_surface_px, cy_on_surface_px), current_radius_scaled_px, width=scaled_wave_border_width)
        
        # 2) 球拍軌跡繪製
        if self.owner_trail_positions_x_norm:
            owner_paddle_width_scaled = int(self.owner.paddle_width * scale_factor)
            owner_paddle_height_scaled = int(self.env.paddle_height_px * scale_factor)
            
            rect_y_on_surface_px = 0
            # ⭐️ 軌跡的Y座標應該是技能擁有者在【當前視角】的球拍位置（底部）
            if is_owner_bottom_perspective_in_this_area:
                 rect_y_on_surface_px = ga_top + ga_height_scaled - owner_paddle_height_scaled
            else:
                 # 如果要在對手視角畫己方軌跡 (己方在頂部)
                 rect_y_on_surface_px = ga_top
            
            for i, trail_x_norm in enumerate(self.owner_trail_positions_x_norm):
                # ... (alpha 計算不變) ...
                trail_alpha_ratio_local = (i + 1) / len(self.owner_trail_positions_x_norm)
                base_alpha = int(120 * trail_alpha_ratio_local)
                final_trail_alpha = int(base_alpha * current_alpha_ratio)

                if final_trail_alpha > 0:
                    trail_color_rgb = self.trail_color[:3]
                    
                    trail_center_x_in_area_scaled = int(trail_x_norm * ga_width_scaled)
                    rect_center_x_on_surface_px = ga_left + trail_center_x_in_area_scaled
                    rect_left_on_surface_px = rect_center_x_on_surface_px - owner_paddle_width_scaled // 2
                    
                    trail_surf = pygame.Surface((owner_paddle_width_scaled, owner_paddle_height_scaled), pygame.SRCALPHA)
                    trail_surf.fill((*trail_color_rgb, final_trail_alpha))
                    surface.blit(trail_surf, (rect_left_on_surface_px, rect_y_on_surface_px))

        # 3) 時鐘 UI 繪製 (保持在 game_render_area_on_screen 中心)
        should_draw_clock = self.active or (self.fadeout_active and current_alpha_ratio > 0.01)
        if should_draw_clock:
            # ... (時鐘繪製邏輯基本不變，它已經是相對於 game_render_area_on_screen 中心)
            clock_rgb = self.clock_color[:3]
            base_clock_alpha = self.clock_color[3] if len(self.clock_color) > 3 else 100
            final_clock_alpha = int(base_clock_alpha * current_alpha_ratio)

            if final_clock_alpha > 0:
                clock_center_x_on_surface = game_render_area_on_screen.centerx
                clock_center_y_on_surface = game_render_area_on_screen.centery
                scaled_clock_radius = int(self.clock_radius_logic_px * scale_factor)
                scaled_clock_line_width = max(1, int(self.clock_line_width_logic_px * scale_factor))
                
                if scaled_clock_radius > 0 :
                    energy_display_ratio = self.get_energy_ratio() if self.active else 0.0
                    angle_deg_remaining = energy_display_ratio * 360.0
                    arc_rect = pygame.Rect(
                        clock_center_x_on_surface - scaled_clock_radius,
                        clock_center_y_on_surface - scaled_clock_radius,
                        scaled_clock_radius * 2,
                        scaled_clock_radius * 2
                    )
                    start_angle_rad = math.radians(-90) 
                    end_angle_rad = math.radians(-90 + angle_deg_remaining)
                    if scaled_clock_line_width > 0 and scaled_clock_radius > scaled_clock_line_width // 2 :
                        try:
                            pygame.draw.arc(surface, (*clock_rgb, final_clock_alpha), arc_rect,
                                            start_angle_rad, end_angle_rad, width=scaled_clock_line_width)
                        except TypeError: 
                             pygame.draw.arc(surface, (*clock_rgb, final_clock_alpha), arc_rect,
                                            start_angle_rad, end_angle_rad, scaled_clock_line_width)
        
        # 2) 球拍軌跡繪製
        if self.owner_trail_positions_x_norm:
            # 獲取縮放後的球拍尺寸
            owner_paddle_width_scaled = int(self.owner.paddle_width * scale_factor) # owner.paddle_width 是邏輯像素
            owner_paddle_height_scaled = int(self.env.paddle_height_px * scale_factor) # env.paddle_height_px 是邏輯像素
            
            # 確定軌跡的 Y 座標 (球拍的 Y 位置)
            # 這取決於技能擁有者是上方還是下方玩家，並且是在 game_render_area_on_screen 內
            # ⭐️⭐️⭐️ 關鍵修正：軌跡的Y座標應該總是基於 is_owner_bottom_perspective_in_this_area ⭐️⭐️⭐️
            if is_owner_bottom_perspective_in_this_area:
                 rect_y_on_surface_px = ga_top + ga_height_scaled - owner_paddle_height_scaled
            else:
                 # 這種情況目前不會發生，因為我們只在擁有者自己的視角渲染技能。
                 # 但如果將來要在對手視角畫擁有者的軌跡（此時擁有者在頂部），就需要這個：
                 rect_y_on_surface_px = ga_top

            for i, trail_x_norm in enumerate(self.owner_trail_positions_x_norm):
                # 計算軌跡 Alpha (淡化效果)
                trail_alpha_ratio_local = (i + 1) / len(self.owner_trail_positions_x_norm)
                base_alpha = int(120 * trail_alpha_ratio_local) # 軌跡的基礎 Alpha (調低一點)
                final_trail_alpha = int(base_alpha * current_alpha_ratio) # 結合技能淡出效果

                if final_trail_alpha > 0:
                    trail_color_rgb = self.trail_color[:3] # 軌跡顏色 RGB
                    
                    # 計算軌跡矩形中心X在 game_render_area_on_screen內的相對像素位置
                    trail_center_x_in_area_scaled = int(trail_x_norm * game_render_area_on_screen.width)
                    # 轉換為在 surface 上的絕對像素位置
                    rect_center_x_on_surface_px = game_render_area_on_screen.left + trail_center_x_in_area_scaled
                    
                    rect_left_on_surface_px = rect_center_x_on_surface_px - owner_paddle_width_scaled // 2
                    
                    # 創建帶 Alpha 的軌跡表面
                    trail_surf = pygame.Surface((owner_paddle_width_scaled, owner_paddle_height_scaled), pygame.SRCALPHA)
                    trail_surf.fill((*trail_color_rgb, final_trail_alpha))
                    surface.blit(trail_surf, (rect_left_on_surface_px, rect_y_on_surface_px))

        # 3) 時鐘 UI 繪製
        # 時鐘應該顯示在 game_render_area_on_screen 的中心
        should_draw_clock = self.active or (self.fadeout_active and current_alpha_ratio > 0.01)
        
        if should_draw_clock:
            clock_rgb = self.clock_color[:3]
            base_clock_alpha = self.clock_color[3] if len(self.clock_color) > 3 else 100
            final_clock_alpha = int(base_clock_alpha * current_alpha_ratio)

            if final_clock_alpha > 0:
                # 計算時鐘在 game_render_area_on_screen 的中心點
                clock_center_x_on_surface = game_render_area_on_screen.centerx
                clock_center_y_on_surface = game_render_area_on_screen.centery
                
                # 縮放後的時鐘半徑和線寬
                scaled_clock_radius = int(self.clock_radius_logic_px * scale_factor)
                scaled_clock_line_width = max(1, int(self.clock_line_width_logic_px * scale_factor))
                
                if scaled_clock_radius > 0 : # 只有當半徑大於0才繪製
                    # 繪製時鐘背景圓 (如果需要，或者直接畫指針)
                    # pygame.draw.circle(surface, (*clock_rgb, final_clock_alpha // 2), # 半透明背景
                    #                    (clock_center_x_on_surface, clock_center_y_on_surface), scaled_clock_radius)

                    # 繪製時鐘指針或進度條
                    energy_display_ratio = self.get_energy_ratio() if self.active else 0.0 # 技能剩餘時間比例 (1.0 -> 0.0)
                    angle_deg_remaining = energy_display_ratio * 360.0 # 剩餘能量對應的角度
                    
                    # 繪製圓弧表示剩餘能量
                    # Pygame 的 arc 需要一個矩形和起始/結束角度
                    arc_rect = pygame.Rect(
                        clock_center_x_on_surface - scaled_clock_radius,
                        clock_center_y_on_surface - scaled_clock_radius,
                        scaled_clock_radius * 2,
                        scaled_clock_radius * 2
                    )
                    start_angle_rad = math.radians(-90) # 從12點鐘方向開始
                    end_angle_rad = math.radians(-90 + angle_deg_remaining)

                    # 確保線寬有效
                    if scaled_clock_line_width > 0 and scaled_clock_radius > scaled_clock_line_width // 2 :
                        try:
                            pygame.draw.arc(surface, (*clock_rgb, final_clock_alpha), arc_rect,
                                            start_angle_rad, end_angle_rad, width=scaled_clock_line_width)
                        except TypeError: # Pygame < 2.0.1 draw.arc width might behave differently
                             pygame.draw.arc(surface, (*clock_rgb, final_clock_alpha), arc_rect,
                                            start_angle_rad, end_angle_rad, scaled_clock_line_width)


                    # (可選) 繪製一個小的中心點
                    # pygame.draw.circle(surface, (*clock_rgb, final_clock_alpha),
                    #                    (clock_center_x_on_surface, clock_center_y_on_surface), max(1, int(2*scale_factor)))