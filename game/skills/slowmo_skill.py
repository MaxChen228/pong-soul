# pong-soul/game/skills/slowmo_skill.py

import math
import pygame
from game.skills.base_skill import Skill
from game.skills.skill_config import SKILL_CONFIGS

class SlowMoSkill(Skill):
    def __init__(self, env, owner_player_state): # ⭐️ 修改參數
        super().__init__(env, owner_player_state) # ⭐️ 調用父類
        cfg_key = "slowmo"
        if cfg_key not in SKILL_CONFIGS:
            raise ValueError(f"Skill configuration for '{cfg_key}' not found.")
        cfg = SKILL_CONFIGS[cfg_key]

        self.duration_ms = cfg["duration_ms"]
        self.cooldown_ms = cfg["cooldown_ms"]

        self.active = False
        self.activated_time = 0
        self.cooldown_start_time = 0

        # shockwave
        self.shockwaves = [] # 衝擊波列表，每個元素是個字典 e.g. {"cx":px, "cy":py, "radius":r}
        self.last_shockwave_frame_count = 0 # 用於控制衝擊波產生頻率 (可選)

        # fog (霧效，影響視覺和可能的 time_scale)
        self.fog_duration_ms = cfg.get("fog_duration_ms", self.duration_ms + 1000) # 霧效持續時間，可比技能長
        self.fog_active = False # 霧效是否激活 (視覺上)
        self.fog_end_time = 0   # 霧效結束時間

        # color (技能期間擁有者的球拍顏色)
        self.owner_skill_paddle_color = cfg.get("paddle_color", (0, 150, 255)) # 技能啟用時的顏色
        self.trail_color = cfg.get("trail_color", (0, 200, 255)) # 軌跡顏色
        self.max_trail_length = cfg.get("max_trail_length", 15) # 軌跡最大長度
        self.owner_trail_positions_x = [] # 只記錄X座標的軌跡 (歸一化)

        # clock (技能計時UI)
        self.clock_color = cfg.get("clock_color", (255, 255, 255, 100))
        self.clock_radius = cfg.get("clock_radius", 50)
        self.clock_line_width = cfg.get("clock_line_width", 4)

        # time_scale (技能效果)
        self.slow_time_scale_value = cfg.get("slow_time_scale", 0.2) # 技能作用時的時間尺度
        self.normal_time_scale_value = 1.0 # 正常時間尺度

        # fadeout (技能結束後的淡出效果)
        self.fadeout_active = False # 是否正在淡出
        self.fadeout_duration_ms = cfg.get("fadeout_duration_ms", 1500) # 淡出持續時間
        self.fadeout_end_time = 0

        # ⭐️ 移除 self.offset_y，Renderer 會處理Y軸偏移
        # self.env.sound_manager.stop_slowmo() # 初始化時不應停止音效，應在 deactivate 時

        print(f"[SKILL_DEBUG][SlowMoSkill] ({self.owner.identifier}) Initialized. Duration: {self.duration_ms}ms, TimeScale: {self.slow_time_scale_value}")

    def activate(self):
        cur = pygame.time.get_ticks()
        if not self.active and (self.cooldown_start_time == 0 or (cur - self.cooldown_start_time >= self.cooldown_ms)):
            self.active = True
            self.activated_time = cur
            
            # ⭐️ 設定環境的時間尺度 - 關鍵點
            # self.env.time_scale = self.slow_time_scale_value # PongDuelEnv.step 中會統一處理
            
            self.owner.paddle_color = self.owner_skill_paddle_color # 改變擁有者球拍顏色
            
            self.fog_active = True # 啟用霧效
            self.fog_end_time = cur + self.fog_duration_ms # 設定霧效結束時間

            self.shockwaves.clear() # 清除舊的衝擊波
            self.owner_trail_positions_x.clear() # 清除舊的軌跡
            self.last_shockwave_frame_count = 0 # 重置衝擊波計數器

            self.fadeout_active = False #不在淡出狀態

            if hasattr(self.env, 'sound_manager'): # 播放音效
                self.env.sound_manager.play_slowmo() # 假設 SoundManager 有此方法

            print(f"[SKILL_DEBUG][SlowMoSkill] ({self.owner.identifier}) Activated! Fog ends at {self.fog_end_time}. Paddle color: {self.owner.paddle_color}")
            return True
        print(f"[SKILL_DEBUG][SlowMoSkill] ({self.owner.identifier}) Activation failed (active: {self.active}, cooldown: {self.get_cooldown_seconds():.1f}s).")
        return False

    def update(self):
        # 注意：此 update 方法主要更新技能自身的內部狀態和觸發效果的產生（如衝擊波、軌跡）。
        # 全局 time_scale 的設定由 PongDuelEnv.step 在所有技能 update 後統一處理。
        cur = pygame.time.get_ticks()

        if self.active: # 技能效果持續中
            if (cur - self.activated_time) >= self.duration_ms:
                print(f"[SKILL_DEBUG][SlowMoSkill] ({self.owner.identifier}) Duration expired. Deactivating.")
                self.deactivate() # 持續時間到，開始淡出
            else:
                # 技能生效期間的邏輯
                self._update_shockwaves() # 更新/產生衝擊波
                self._update_trail()    # 更新軌跡

        # 處理霧效和淡出 (即使技能本身 active=False，霧效和淡出可能仍在持續)
        if self.fog_active and cur > self.fog_end_time:
            print(f"[SKILL_DEBUG][SlowMoSkill] ({self.owner.identifier}) Fog duration expired.")
            self.fog_active = False # 霧效結束

        if self.fadeout_active and cur > self.fadeout_end_time:
            print(f"[SKILL_DEBUG][SlowMoSkill] ({self.owner.identifier}) Fadeout finished.")
            self.fadeout_active = False # 淡出結束
            # 淡出結束後，確保所有視覺效果被清理 (render方法中處理alpha為0的情況)
            self.shockwaves.clear()
            self.owner_trail_positions_x.clear()
            # 顏色已在deactivate中或動畫結束時由PlayerState.reset_state處理，此處不再動

        # 如果不再 active，且不在 fadeout，且不在 fog_active (理論上此時應已清理)
        if not self.active and not self.fadeout_active and not self.fog_active:
            # 確保清理，以防萬一
            if self.owner_trail_positions_x: self.owner_trail_positions_x.clear()
            if self.shockwaves: self.shockwaves.clear()
            # paddle color 和 time_scale 由 Env 和 PlayerState 在 reset 或技能結束時處理


    def deactivate(self):
        if self.active or self.fadeout_active or self.fog_active : # 只要技能還在以任何形式影響 (active, fadeout, fog)
            was_active = self.active
            self.active = False # 技能主效果結束

            if was_active: # 只有在技能是從 active 狀態被 deactivate 時才啟動冷卻和淡出
                print(f"[SKILL_DEBUG][SlowMoSkill] ({self.owner.identifier}) Deactivating. Starting cooldown and fadeout.")
                self.cooldown_start_time = pygame.time.get_ticks()
                
                self.fadeout_active = True # 開始淡出
                self.fadeout_end_time = self.cooldown_start_time + self.fadeout_duration_ms
                
                # 霧效的結束時間可能已經設定，如果淡出比霧效先結束，以霧效為準
                # 或者讓霧效也跟隨淡出時間，取決於設計
                # self.fog_end_time = max(self.fog_end_time, self.fadeout_end_time)
            
            # 恢復擁有者球拍顏色 (PlayerState.reset_state 會處理基礎顏色，但技能停用時應立即恢復)
            self.owner.paddle_color = self.owner.base_paddle_color
            
            # 停止音效
            if hasattr(self.env, 'sound_manager'):
                self.env.sound_manager.stop_slowmo()
            
            # time_scale 的恢復由 PongDuelEnv.step 統一處理
            print(f"[SKILL_DEBUG][SlowMoSkill] ({self.owner.identifier}) Deactivated. Paddle color restored to {self.owner.paddle_color}. Fadeout ends at {self.fadeout_end_time}")


    def is_active(self):
        return self.active

    def get_cooldown_seconds(self):
        # ... (與 LongPaddleSkill 類似)
        if self.active: return 0.0
        current_time = pygame.time.get_ticks()
        if self.cooldown_start_time == 0: return 0.0 
        elapsed = current_time - self.cooldown_start_time
        remaining = self.cooldown_ms - elapsed
        return max(0.0, remaining / 1000.0)

    def get_energy_ratio(self):
        # ... (與 LongPaddleSkill 類似)
        current_time = pygame.time.get_ticks()
        if self.active:
            elapsed_duration = current_time - self.activated_time
            ratio = (self.duration_ms - elapsed_duration) / self.duration_ms if self.duration_ms > 0 else 0.0
            return max(0.0, ratio)
        else:
            if self.cooldown_start_time == 0: return 1.0
            elapsed_cooldown = current_time - self.cooldown_start_time
            if elapsed_cooldown >= self.cooldown_ms: return 1.0
            ratio = elapsed_cooldown / self.cooldown_ms if self.cooldown_ms > 0 else 1.0
            return min(1.0, ratio)

    def _get_fadeout_ratio(self):
        """計算淡出效果的alpha比例，1.0為不透明，0.0為完全透明"""
        if not self.fadeout_active: return 0.0 # 如果不在淡出，則完全透明 (或不繪製)
        cur = pygame.time.get_ticks()
        remaining_fade_time = self.fadeout_end_time - cur
        if remaining_fade_time <= 0: return 0.0
        return remaining_fade_time / float(self.fadeout_duration_ms)

    def _get_fog_alpha_ratio(self):
        """計算霧效的alpha比例"""
        if not self.fog_active: return 0.0
        cur = pygame.time.get_ticks()
        remaining_fog_time = self.fog_end_time - cur
        if remaining_fog_time <= 0: return 0.0
        # 霧效可以有一個更複雜的alpha變化，例如開始時淡入，結束時淡出
        # 簡化：線性淡出
        # 假設 fog_duration_ms 是總時長，可以基於 fog_end_time 計算剩餘比例
        # 或者，如果希望霧效在技能期間保持，在淡出時一起淡出，則這裡的alpha可以更簡單
        # 此處的 alpha 主要用於獨立的霧效時間控制
        # 為了與淡出協調，最終的 alpha 會取最小值
        return remaining_fog_time / float(self.fog_duration_ms) if self.fog_duration_ms > 0 else 0.0


    def _update_shockwaves(self):
        # 衝擊波產生邏輯
        # ⭐️ 衝擊波的中心點應該是技能擁有者的球拍中心
        # 球拍在底部的Y座標 (歸一化): 1.0 - self.env.paddle_height_normalized
        # 轉換為像素: (1.0 - self.env.paddle_height_normalized) * self.env.render_size
        # 再加上 Renderer 的 offset_y
        # 但技能 render 方法接收的是主 surface，座標應相對於遊戲區域或 owner
        
        # 簡化：衝擊波的 cx, cy 在 render 時再計算像素座標
        # 此處只決定是否產生新的衝擊波
        self.last_shockwave_frame_count +=1
        # 每隔幾幀產生一個衝_擊波 (可調整)
        if self.last_shockwave_frame_count >= 10: # 例如每10遊戲幀
            # 獲取擁有者球拍的當前中心X (歸一化) 和 底部Y (歸一化，球拍上表面)
            owner_paddle_center_x_norm = self.owner.x
            # 球拍在遊戲區域內的Y座標 (像素，相對於遊戲區頂部)
            # P1 (下方): self.env.render_size - self.env.paddle_height_px
            # P2/Opponent (上方): 0 (球拍下表面是 self.env.paddle_height_px)
            # 為了通用，我們假設衝擊波從球拍的"前緣"發出
            if self.owner.identifier == "player1": # P1 在下方
                owner_paddle_y_surface_norm = 1.0 - self.env.paddle_height_normalized
            else: # Opponent 在上方
                owner_paddle_y_surface_norm = self.env.paddle_height_normalized
            
            self.shockwaves.append({
                "cx_norm": owner_paddle_center_x_norm,
                "cy_norm": owner_paddle_y_surface_norm, # Y座標是球拍的表面
                "radius_px": 0, # 初始半徑為0像素
                "max_radius_px": 150, # 最大半徑
                "expand_speed_px": 20 # 每幀擴張速度
            })
            self.last_shockwave_frame_count = 0
            # print(f"[SKILL_DEBUG][SlowMoSkill] ({self.owner.identifier}) New shockwave. Total: {len(self.shockwaves)}")

        # 更新現有衝擊波
        active_shockwaves = []
        for wave in self.shockwaves:
            wave["radius_px"] += wave["expand_speed_px"]
            if wave["radius_px"] < wave["max_radius_px"]:
                active_shockwaves.append(wave)
        self.shockwaves = active_shockwaves

    def _update_trail(self):
        # 更新擁有者球拍的軌跡 (只記錄X座標)
        self.owner_trail_positions_x.append(self.owner.x) # 儲存歸一化的X座標
        if len(self.owner_trail_positions_x) > self.max_trail_length:
            self.owner_trail_positions_x.pop(0)

    def render(self, surface): # surface 是主 Pygame 視窗
        # 繪製此技能的視覺效果 (衝擊波、軌跡、時鐘等)
        # 所有繪製都應考慮到 Renderer 的 offset_y
        # 以及可能的淡出效果

        # 統一計算最終的 alpha 比例，用於所有視覺效果的淡化
        final_alpha_ratio = 1.0
        if self.fadeout_active:
            final_alpha_ratio = self._get_fadeout_ratio()
        
        # 如果霧效獨立於淡出且仍在活動，也考慮霧效的 alpha (取較小者)
        # 或者，如果設計是霧效隨淡出而淡出，則不需要獨立計算 fog_alpha
        # 這裡假設霧效的視覺也受 fadeout_active 控制
        # if self.fog_active and not self.fadeout_active: # 如果只剩霧效獨立持續
        #     final_alpha_ratio = min(final_alpha_ratio, self._get_fog_alpha_ratio())


        if final_alpha_ratio <= 0.01: # 如果幾乎完全透明，則不繪製
            return

        # 1) 衝擊波繪製
        if self.shockwaves:
            base_fill_alpha = 80
            base_border_alpha = 200
            fill_color_rgb = (50, 150, 255) # 衝擊波填充顏色RGB
            border_color_rgb = (255, 255, 255) # 衝擊波邊框顏色RGB

            final_fill_alpha = int(base_fill_alpha * final_alpha_ratio)
            final_border_alpha = int(base_border_alpha * final_alpha_ratio)

            if final_fill_alpha > 0 or final_border_alpha > 0:
                for wave in self.shockwaves:
                    # 將歸一化的中心點轉換為螢幕像素座標
                    cx_px = int(wave["cx_norm"] * self.env.render_size)
                    # cy_norm 是相對於遊戲區域 (0-1) 的球拍表面 Y
                    # 轉換為相對於遊戲區域頂部的像素 Y
                    cy_game_px = int(wave["cy_norm"] * self.env.render_size)
                    # 再加上 Renderer 的 offset_y 得到螢幕像素 Y
                    cy_screen_px = cy_game_px + self.env.renderer.offset_y # 假設 renderer 存在

                    # 創建一個與衝擊波半徑相符的臨時 overlay surface (優化)
                    # overlay_size = int(wave["radius_px"] * 2 + 12) # 比半徑稍大以容納邊框
                    # overlay_surf = pygame.Surface((overlay_size, overlay_size), pygame.SRCALPHA)
                    # overlay_center = (overlay_size // 2, overlay_size // 2)

                    # 直接在主 surface 上繪製 (如果衝擊波數量不多)
                    current_radius_px = int(wave["radius_px"])
                    if current_radius_px > 0:
                        # 填充 (如果需要)
                        if final_fill_alpha > 0:
                            # 為了畫出有透明度的填充圓，需要一個臨時surface
                            temp_circle_surf = pygame.Surface((current_radius_px * 2, current_radius_px * 2), pygame.SRCALPHA)
                            pygame.draw.circle(temp_circle_surf, (*fill_color_rgb, final_fill_alpha), 
                                               (current_radius_px, current_radius_px), current_radius_px)
                            surface.blit(temp_circle_surf, (cx_px - current_radius_px, cy_screen_px - current_radius_px))

                        # 邊框
                        if final_border_alpha > 0:
                             pygame.draw.circle(surface, (*border_color_rgb, final_border_alpha),
                                               (cx_px, cy_screen_px), current_radius_px, width=6)
        
        # 2) 球拍軌跡繪製 (為技能擁有者繪製)
        if self.owner_trail_positions_x:
            owner_paddle_width_px = self.owner.paddle_width # 當前像素寬度
            owner_paddle_height_px = self.env.paddle_height_px # 像素高度
            
            # 確定擁有者球拍的Y座標 (螢幕座標)
            if self.owner.identifier == "player1": # P1 在下方
                # 球拍上邊緣的Y (遊戲區) = render_size - paddle_height
                # 球拍矩形左上角的Y (螢幕) = offset_y + render_size - paddle_height
                rect_y_screen_px = self.env.renderer.offset_y + self.env.render_size - owner_paddle_height_px
            else: # Opponent 在上方
                # 球拍矩形左上角的Y (螢幕) = offset_y
                rect_y_screen_px = self.env.renderer.offset_y

            for i, trail_x_norm in enumerate(self.owner_trail_positions_x):
                trail_alpha_ratio = (i + 1) / len(self.owner_trail_positions_x) # 越舊的越透明
                base_alpha = int(150 * trail_alpha_ratio) # 最大alpha值
                final_alpha = int(base_alpha * final_alpha_ratio)

                if final_alpha > 0:
                    trail_color_rgb = self.trail_color[:3] # 取RGB
                    # 計算軌跡矩形的X座標 (螢幕座標)
                    rect_x_center_px = int(trail_x_norm * self.env.render_size)
                    rect_x_screen_px = rect_x_center_px - owner_paddle_width_px // 2
                    
                    # 創建一個小 surface 來繪製帶 alpha 的矩形
                    trail_surf = pygame.Surface((owner_paddle_width_px, owner_paddle_height_px), pygame.SRCALPHA)
                    trail_surf.fill((*trail_color_rgb, final_alpha))
                    surface.blit(trail_surf, (rect_x_screen_px, rect_y_screen_px))

        # 3) 時鐘 UI 繪製
        # (只在技能 active 或 fadeout 時顯示，或者只要 fog_active 也顯示)
        if self.active or self.fadeout_active or self.fog_active:
            clock_rgb = self.clock_color[:3]
            base_clock_alpha = self.clock_color[3] if len(self.clock_color) > 3 else 100
            final_clock_alpha = int(base_clock_alpha * final_alpha_ratio)

            if final_clock_alpha > 0:
                energy_display_ratio = self.get_energy_ratio() if self.active else 0 # 淡出時能量為0
                angle_deg = (1 - energy_display_ratio) * 360 # 能量滿是0度，能量空是360度
                angle_rad = math.radians(angle_deg)

                # 時鐘繪製在螢幕中心
                # screen_center_x = self.env.render_size // 2
                # screen_center_y = self.env.render_size // 2 + self.env.renderer.offset_y # 考慮UI偏移
                screen_center_x = surface.get_width() // 2
                screen_center_y = surface.get_height() // 2


                # 創建一個用於時鐘的臨時 surface
                clock_surface_size = self.clock_radius * 2 + 10
                clock_surf = pygame.Surface((clock_surface_size, clock_surface_size), pygame.SRCALPHA)
                
                center_on_clock_surf = (clock_surface_size // 2, clock_surface_size // 2)
                
                # 繪製時鐘背景圓
                pygame.draw.circle(clock_surf, (*clock_rgb, final_clock_alpha), 
                                   center_on_clock_surf, self.clock_radius)
                
                # 繪製時鐘指標
                needle_alpha = int(200 * final_alpha_ratio) # 指針更實一點
                needle_color = (255, 255, 255, needle_alpha) # 白色指針
                needle_length = self.clock_radius - 5
                
                # 指針從12點方向開始 (上方，-PI/2)
                nx = center_on_clock_surf[0] + needle_length * math.cos(angle_rad - math.pi / 2)
                ny = center_on_clock_surf[1] + needle_length * math.sin(angle_rad - math.pi / 2)
                pygame.draw.line(clock_surf, needle_color, center_on_clock_surf, (nx, ny), self.clock_line_width)

                # 將時鐘 surface 繪製到主視窗的中心
                clock_rect = clock_surf.get_rect(center=(screen_center_x, screen_center_y))
                surface.blit(clock_surf, clock_rect)