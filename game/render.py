# game/render.py
import math
import pygame
from game.theme import Style
from game.settings import GameSettings
from utils import resource_path
from game.skills.skill_config import SKILL_CONFIGS

DEBUG_RENDERER = True

class Renderer:
    def __init__(self, env, game_mode):
        if DEBUG_RENDERER: print(f"[Renderer.__init__] Initializing Renderer for game_mode: {game_mode}...")
        pygame.init() 
        self.env = env
        self.game_mode = game_mode
        
        self.logical_render_size = env.render_size 
        
        # ⭐️ 無論何種模式，都設定一個 Renderer 實例的 offset_y 屬性
        # 沿用之前定義的 ui_offset_y_per_viewport 作為其值
        self.ui_offset_y_per_viewport = 100 
        self.offset_y = self.ui_offset_y_per_viewport # ⭐️ 確保 self.offset_y 存在

        if self.game_mode == GameSettings.GameMode.PLAYER_VS_PLAYER:
            self.main_window_width = 1000 
            self.main_window_height = 600  
            self.window = pygame.display.set_mode((self.main_window_width, self.main_window_height))
            pygame.display.set_caption("Pong Soul - PvP Mode (Horizontal Split Setup)")

            self.viewport_width = self.main_window_width // 2 
            self.viewport_height = self.main_window_height   
            self.viewport1_rect = pygame.Rect(0, 0, self.viewport_width, self.viewport_height) 
            self.viewport2_rect = pygame.Rect(self.viewport_width, 0, self.viewport_width, self.viewport_height)
            
            if DEBUG_RENDERER:
                print(f"[Renderer.__init__] PvP mode. Main window: {self.main_window_width}x{self.main_window_height}")
                print(f"[Renderer.__init__] Viewport1 (P1/Left): {self.viewport1_rect}")
                print(f"[Renderer.__init__] Viewport2 (P2/Right): {self.viewport2_rect}")
                print(f"[Renderer.__init__] self.offset_y set to: {self.offset_y}") # ⭐️ 除錯確認
        else: # PvA 或其他單一視圖模式
            self.main_window_width = self.logical_render_size
            self.main_window_height = self.logical_render_size + 2 * self.offset_y # PvA 使用2倍offset_y
            self.window = pygame.display.set_mode((self.main_window_width, self.main_window_height))
            pygame.display.set_caption("Pong Soul - PvA Mode")
            self.game_area_rect = pygame.Rect(0, self.offset_y, self.logical_render_size, self.logical_render_size)
            if DEBUG_RENDERER:
                print(f"[Renderer.__init__] PvA mode. Main window: {self.main_window_width}x{self.main_window_height}")
                print(f"[Renderer.__init__] PvA Game Area offset by Y: {self.offset_y}")
                print(f"[Renderer.__init__] self.offset_y set to: {self.offset_y}") # ⭐️ 除錯確認

        self.clock = pygame.time.Clock()
        # ... (球圖像加載邏輯保持不變) ...
        try:
            ball_diameter_px = int(env.ball_radius_px * 2); _=ball_diameter_px
            if ball_diameter_px <= 0: ball_diameter_px = 20 
            self.ball_image_original = pygame.image.load(resource_path("assets/sunglasses.png")).convert_alpha()
            self.ball_image = pygame.transform.smoothscale(self.ball_image_original, (ball_diameter_px, ball_diameter_px))
        except Exception as e: 
            if DEBUG_RENDERER: print(f"[Renderer.__init__] Error loading/scaling ball image: {e}. Creating fallback.")
            ball_diameter_px = int(env.ball_radius_px * 2) if hasattr(env, 'ball_radius_px') and env.ball_radius_px * 2 > 0 else 20
            self.ball_image = pygame.Surface((ball_diameter_px, ball_diameter_px), pygame.SRCALPHA)
            pygame.draw.circle(self.ball_image, (255, 255, 255), (ball_diameter_px // 2, ball_diameter_px // 2), ball_diameter_px // 2)
        self.ball_angle = 0 
        self.skill_glow_position = 0; self.skill_glow_trail = []; self.max_skill_glow_trail_length = 15

        if DEBUG_RENDERER: print("[Renderer.__init__] Renderer initialization complete.")


    def render(self):
        if not self.env:
            if DEBUG_RENDERER: print("[Renderer.render] Error: self.env is not set.")
            return

        current_time_ticks = pygame.time.get_ticks()
        freeze_active = (
            self.env.freeze_timer > 0
            and (current_time_ticks - self.env.freeze_timer < self.env.freeze_duration)
        )
        current_bg_color = Style.BACKGROUND_COLOR
        if freeze_active:
            current_bg_color = (220, 220, 220) if (current_time_ticks // 100) % 2 == 0 else (10, 10, 10)
        
        self.window.fill(current_bg_color)

        # ⭐️ ui_overlay_color 在此定義，對後續所有分支都可見
        ui_overlay_color = tuple(max(0, c - 20) for c in Style.BACKGROUND_COLOR)
        # ⭐️ (可以加個 print 驗證 Style.BACKGROUND_COLOR 是否有效)
        # if DEBUG_RENDERER: print(f"[Renderer.render] Style.BACKGROUND_COLOR: {Style.BACKGROUND_COLOR}, ui_overlay_color: {ui_overlay_color}")


        if self.game_mode == GameSettings.GameMode.PLAYER_VS_PLAYER:
            pygame.draw.line(self.window, (255, 0, 0), (self.viewport_width, 0), (self.viewport_width, self.main_window_height), 2)
            
            p1_viewport_surface = self.window.subsurface(self.viewport1_rect)
            p1_viewport_surface.fill(current_bg_color) 

            # ⭐️ 使用外部已定義的 ui_overlay_color
            pygame.draw.rect(p1_viewport_surface, ui_overlay_color, (0, 0, self.viewport_width, self.ui_offset_y_per_viewport))
            # 計算 p1_viewport_surface 內遊戲區域下方的剩餘部分作為底部UI條
            bottom_ui_y_start_in_p1_vp = self.ui_offset_y_per_viewport + self.logical_render_size
            bottom_ui_height_in_p1_vp = self.viewport_height - bottom_ui_y_start_in_p1_vp
            if bottom_ui_height_in_p1_vp > 0 : # 確保高度大於0才繪製
                pygame.draw.rect(p1_viewport_surface, ui_overlay_color, (0, bottom_ui_y_start_in_p1_vp, self.viewport_width, bottom_ui_height_in_p1_vp ))

            # ... (PvP P1 視口的後續渲染邏輯) ...
            # ... (技能渲染) ...
            if self.env.player1.skill_instance and (self.env.player1.skill_instance.is_active() or \
                (hasattr(self.env.player1.skill_instance, 'fadeout_active') and self.env.player1.skill_instance.fadeout_active) or \
                (hasattr(self.env.player1.skill_instance, 'fog_active') and self.env.player1.skill_instance.fog_active)):
                self.env.player1.skill_instance.render(p1_viewport_surface) # 傳遞子表面

            try: # 主要元素繪製 (球、球拍等)，座標基於 self.logical_render_size，繪製到 p1_viewport_surface
                cx_px = int(self.env.ball_x * self.logical_render_size)
                cy_px = int(self.env.ball_y * self.logical_render_size) + self.ui_offset_y_per_viewport
                p1_paddle_color = self.env.player1.paddle_color
                p1_x_px = int(self.env.player1.x * self.logical_render_size)
                p1_paddle_width_px = self.env.player1.paddle_width 
                p1_paddle_height_px = self.env.paddle_height_px
                pygame.draw.rect(p1_viewport_surface, p1_paddle_color if p1_paddle_color else Style.PLAYER_COLOR,
                    (p1_x_px - p1_paddle_width_px // 2,
                     self.ui_offset_y_per_viewport + self.logical_render_size - p1_paddle_height_px,
                     p1_paddle_width_px, p1_paddle_height_px), border_radius=8)
                opponent_paddle_color = self.env.opponent.paddle_color 
                opponent_x_px = int(self.env.opponent.x * self.logical_render_size)
                opponent_paddle_width_px = self.env.opponent.paddle_width
                opponent_paddle_height_px = self.env.paddle_height_px
                pygame.draw.rect(p1_viewport_surface, opponent_paddle_color if opponent_paddle_color else Style.AI_COLOR,
                    (opponent_x_px - opponent_paddle_width_px // 2,
                     self.ui_offset_y_per_viewport, 
                     opponent_paddle_width_px, opponent_paddle_height_px), border_radius=8)
                for i, (tx_norm, ty_norm) in enumerate(self.env.trail):
                    fade = int(255 * (i + 1) / len(self.env.trail)) if len(self.env.trail) > 0 else 255
                    base_ball_color_rgb = Style.BALL_COLOR[:3] if isinstance(Style.BALL_COLOR, tuple) and len(Style.BALL_COLOR) >=3 else (255,255,255)
                    color = (*base_ball_color_rgb, fade) 
                    trail_circle_radius_px = 4 
                    temp_surf = pygame.Surface((trail_circle_radius_px * 2, trail_circle_radius_px * 2), pygame.SRCALPHA)
                    pygame.draw.circle(temp_surf, color, (trail_circle_radius_px, trail_circle_radius_px), trail_circle_radius_px)
                    trail_x_px = int(tx_norm * self.logical_render_size)
                    trail_y_px = int(ty_norm * self.logical_render_size) + self.ui_offset_y_per_viewport
                    p1_viewport_surface.blit(temp_surf, (trail_x_px - trail_circle_radius_px, trail_y_px - trail_circle_radius_px))
                current_ball_render_image = self.ball_image 
                if not (hasattr(self.env, 'bug_skill_active') and self.env.bug_skill_active):
                    self.ball_angle += self.env.spin * 12 
                rotated_ball = pygame.transform.rotate(current_ball_render_image, self.ball_angle)
                rect = rotated_ball.get_rect(center=(cx_px, cy_px))
                p1_viewport_surface.blit(rotated_ball, rect)
            except Exception as e:
                 if DEBUG_RENDERER: print(f"[Renderer.render] PvP P1 View drawing error: {e}")


            # 右視口 (P2)
            p2_viewport_surface = self.window.subsurface(self.viewport2_rect)
            p2_viewport_surface.fill(Style.BACKGROUND_COLOR) # 可以用不同的顏色來區分，例如 Style.AI_COLOR
            font_temp = Style.get_font(30)
            p2_text = font_temp.render("Player 2 View (WIP)", True, Style.TEXT_COLOR)
            p2_text_rect = p2_text.get_rect(center=(self.viewport_width // 2, self.viewport_height // 2))
            p2_viewport_surface.blit(p2_text, p2_text_rect)

            # PvP 技能 UI (分別繪製到主視窗的正確視口區域)
            self._render_skill_ui_for_viewport(self.window, self.env.player1, self.viewport1_rect, is_player1_side=True)
            self._render_skill_ui_for_viewport(self.window, self.env.opponent, self.viewport2_rect, is_player1_side=False)


        else: # PvA 模式
            # UI 區域背景
            pygame.draw.rect(self.window, ui_overlay_color, (0, 0, self.main_window_width, self.ui_offset_y_per_viewport))
            bottom_ui_y_start_pva = self.ui_offset_y_per_viewport + self.logical_render_size
            bottom_ui_height_pva = self.main_window_height - bottom_ui_y_start_pva
            if bottom_ui_height_pva > 0:
                 pygame.draw.rect(self.window, ui_overlay_color, (0, bottom_ui_y_start_pva, self.main_window_width, bottom_ui_height_pva))

            # ... (PvA 的後續渲染邏輯，與上一版本相同) ...
            if self.env.player1.skill_instance and (self.env.player1.skill_instance.is_active() or \
                (hasattr(self.env.player1.skill_instance, 'fadeout_active') and self.env.player1.skill_instance.fadeout_active) or \
                (hasattr(self.env.player1.skill_instance, 'fog_active') and self.env.player1.skill_instance.fog_active)):
                self.env.player1.skill_instance.render(self.window)
            try: 
                cx_px = int(self.env.ball_x * self.logical_render_size)
                cy_px = int(self.env.ball_y * self.logical_render_size) + self.ui_offset_y_per_viewport
                p1_paddle_color = self.env.player1.paddle_color
                p1_x_px = int(self.env.player1.x * self.logical_render_size)
                p1_paddle_width_px = self.env.player1.paddle_width 
                p1_paddle_height_px = self.env.paddle_height_px
                pygame.draw.rect(self.window, p1_paddle_color if p1_paddle_color else Style.PLAYER_COLOR,
                    (p1_x_px - p1_paddle_width_px // 2,
                     self.ui_offset_y_per_viewport + self.logical_render_size - p1_paddle_height_px,
                     p1_paddle_width_px, p1_paddle_height_px), border_radius=8)
                opponent_paddle_color = self.env.opponent.paddle_color
                opponent_x_px = int(self.env.opponent.x * self.logical_render_size)
                opponent_paddle_width_px = self.env.opponent.paddle_width
                opponent_paddle_height_px = self.env.paddle_height_px
                pygame.draw.rect(self.window, opponent_paddle_color if opponent_paddle_color else Style.AI_COLOR,
                    (opponent_x_px - opponent_paddle_width_px // 2,
                     self.ui_offset_y_per_viewport, 
                     opponent_paddle_width_px, opponent_paddle_height_px), border_radius=8)
                for i, (tx_norm, ty_norm) in enumerate(self.env.trail):
                    fade = int(255 * (i + 1) / len(self.env.trail)) if len(self.env.trail) > 0 else 255
                    base_ball_color_rgb = Style.BALL_COLOR[:3] if isinstance(Style.BALL_COLOR, tuple) and len(Style.BALL_COLOR) >=3 else (255,255,255)
                    color = (*base_ball_color_rgb, fade) 
                    trail_circle_radius_px = 4 
                    temp_surf = pygame.Surface((trail_circle_radius_px * 2, trail_circle_radius_px * 2), pygame.SRCALPHA)
                    pygame.draw.circle(temp_surf, color, (trail_circle_radius_px, trail_circle_radius_px), trail_circle_radius_px)
                    trail_x_px = int(tx_norm * self.logical_render_size)
                    trail_y_px = int(ty_norm * self.logical_render_size) + self.ui_offset_y_per_viewport
                    self.window.blit(temp_surf, (trail_x_px - trail_circle_radius_px, trail_y_px - trail_circle_radius_px))
                current_ball_render_image = self.ball_image 
                if not (hasattr(self.env, 'bug_skill_active') and self.env.bug_skill_active):
                    self.ball_angle += self.env.spin * 12 
                rotated_ball = pygame.transform.rotate(current_ball_render_image, self.ball_angle)
                rect = rotated_ball.get_rect(center=(cx_px, cy_px))
                self.window.blit(rotated_ball, rect)
                bar_w_px, bar_h_px, spacing_px = 150, 20, 20; current_time_ticks = pygame.time.get_ticks()
                pygame.draw.rect(self.window, Style.AI_BAR_BG, (self.main_window_width - bar_w_px - spacing_px, spacing_px, bar_w_px, bar_h_px))
                opp_flash = (current_time_ticks - self.env.opponent.last_hit_time < self.env.freeze_duration)
                opp_fill_color = (255,255,255) if (opp_flash and (current_time_ticks//100%2==0)) else Style.AI_BAR_FILL
                opponent_life_ratio = self.env.opponent.lives / self.env.opponent.max_lives if self.env.opponent.max_lives > 0 else 0
                pygame.draw.rect(self.window, opp_fill_color, (self.main_window_width - bar_w_px - spacing_px, spacing_px, bar_w_px * opponent_life_ratio, bar_h_px))
                player_bar_y_pos = self.main_window_height - self.ui_offset_y_per_viewport + spacing_px 
                pygame.draw.rect(self.window, Style.PLAYER_BAR_BG, (spacing_px, player_bar_y_pos, bar_w_px, bar_h_px))
                p1_flash = (current_time_ticks - self.env.player1.last_hit_time < self.env.freeze_duration)
                p1_fill_color = (255,255,255) if (p1_flash and (current_time_ticks//100%2==0)) else Style.PLAYER_BAR_FILL
                player1_life_ratio = self.env.player1.lives / self.env.player1.max_lives if self.env.player1.max_lives > 0 else 0
                pygame.draw.rect(self.window, p1_fill_color, (spacing_px, player_bar_y_pos, bar_w_px * player1_life_ratio, bar_h_px))
            except AttributeError as e:
                if DEBUG_RENDERER: print(f"[Renderer.render] PvA AttributeError: {e}")
            except Exception as e:
                if DEBUG_RENDERER: print(f"[Renderer.render] PvA Generic Render Error: {e}")
            self._render_skill_ui_for_pva(self.env.player1)

        pygame.display.flip()
        self.clock.tick(60)

    def _render_skill_ui_for_pva(self, player_state):
        """ PvA 模式下 P1 的技能 UI """
        if not player_state.skill_instance: return
        # ... (與之前 _render_skill_ui 類似的邏輯，但位置固定為 PvA 的 P1 位置)
        skill = player_state.skill_instance
        bar_width_px = 100; bar_height_px = 10; spacing_px = 20; text_offset_y_px = 15
        p1_health_bar_x_end = spacing_px + 150 
        bar_x_px = p1_health_bar_x_end + spacing_px
        bar_y_px = self.main_window_height - self.ui_offset_y_per_viewport + spacing_px
        # ... (後續繪製邏輯與 _render_skill_ui_for_viewport 類似)
        skill_cfg = SKILL_CONFIGS.get(player_state.skill_code_name, {}); bar_fill_color_rgb = skill_cfg.get("bar_color", (200,200,200)); bar_bg_color_rgb = (50,50,50)
        pygame.draw.rect(self.window, bar_bg_color_rgb, (bar_x_px, bar_y_px, bar_width_px, bar_height_px))
        energy_ratio = skill.get_energy_ratio(); current_bar_width = int(bar_width_px * energy_ratio)
        pygame.draw.rect(self.window, bar_fill_color_rgb, (bar_x_px, bar_y_px, current_bar_width, bar_height_px))
        if not skill.is_active():
            cooldown_sec = skill.get_cooldown_seconds()
            if cooldown_sec > 0:
                font = Style.get_font(14); text_surf = font.render(f"{cooldown_sec:.1f}s", True, Style.TEXT_COLOR)
                text_rect = text_surf.get_rect(center=(bar_x_px + bar_width_px / 2, bar_y_px + bar_height_px + text_offset_y_px))
                self.window.blit(text_surf, text_rect)


    def _render_skill_ui_for_viewport(self, target_surface, player_state, viewport_rect, is_player1_side):
        """輔助方法：在指定 viewport 的相對位置繪製技能UI。"""
        if not player_state.skill_instance: return
        skill = player_state.skill_instance
        bar_width_px = 100; bar_height_px = 10; spacing_from_viewport_edge_px = 20; text_offset_y_px = 15
        health_bar_width_assumed = 150 # 假設的血條寬度，用於定位

        # UI元素在視口內的頂部，靠近血條
        # Y 座標相對於視口頂部
        ui_y_in_viewport = spacing_from_viewport_edge_px
        
        if is_player1_side: # P1 在左視口，技能條在血條右邊
            # 血條X結束位置 (相對於視口左邊緣)
            health_bar_x_end_in_viewport = spacing_from_viewport_edge_px + health_bar_width_assumed
            bar_x_in_viewport = health_bar_x_end_in_viewport + spacing_from_viewport_edge_px
        else: # P2 在右視口，技能條在血條左邊
            # 血條X開始位置 (相對於視口右邊緣)
            health_bar_x_start_from_right_edge = spacing_from_viewport_edge_px + health_bar_width_assumed
            bar_x_in_viewport = viewport_rect.width - health_bar_x_start_from_right_edge - bar_width_px 
            
        # 轉換為相對於 target_surface (通常是 self.window) 的絕對座標
        bar_x_abs = viewport_rect.left + bar_x_in_viewport
        bar_y_abs = viewport_rect.top + ui_y_in_viewport

        skill_cfg = SKILL_CONFIGS.get(player_state.skill_code_name, {})
        bar_fill_color_rgb = skill_cfg.get("bar_color", (200, 200, 200))
        bar_bg_color_rgb = (50,50,50)
        pygame.draw.rect(target_surface, bar_bg_color_rgb, (bar_x_abs, bar_y_abs, bar_width_px, bar_height_px))
        energy_ratio = skill.get_energy_ratio()
        current_bar_width = int(bar_width_px * energy_ratio)
        pygame.draw.rect(target_surface, bar_fill_color_rgb, (bar_x_abs, bar_y_abs, current_bar_width, bar_height_px))
        if not skill.is_active():
            cooldown_sec = skill.get_cooldown_seconds()
            if cooldown_sec > 0:
                font = Style.get_font(14); text_surf = font.render(f"{cooldown_sec:.1f}s", True, Style.TEXT_COLOR)
                text_rect = text_surf.get_rect(center=(bar_x_abs + bar_width_px / 2, bar_y_abs + bar_height_px + text_offset_y_px))
                target_surface.blit(text_surf, text_rect)

    def close(self):
        if DEBUG_RENDERER: print("[Renderer.close] Closing Renderer.")