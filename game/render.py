# pong-soul/game/render.py
import math
import pygame
from game.theme import Style
from game.settings import GameSettings
from utils import resource_path
from game.skills.skill_config import SKILL_CONFIGS

# pong-soul/game/render.py
# ... (imports) ...
DEBUG_RENDERER = True

class Renderer:
    def __init__(self, env, game_mode):
        if DEBUG_RENDERER: print(f"[Renderer.__init__] Initializing Renderer for game_mode: {game_mode}...")
        pygame.init() 
        self.env = env
        self.game_mode = game_mode
        self.logical_render_size = env.render_size 
        
        self.pvp_shared_bottom_ui_height = 100 
        self.ui_offset_y_per_viewport = 0 # ⭐️ PvP 視口內遊戲區域頂部的偏移，設為0，因為遊戲內容直接從視口頂部開始
                                         # 或者如果 PvP 視口內也有一個頂部UI條，則設為該UI條高度

        if self.game_mode == GameSettings.GameMode.PLAYER_VS_PLAYER:
            self.main_window_width = 1000 
            self.viewport_height = self.logical_render_size # 假設視口高度就是邏輯遊戲區的高度
            self.main_window_height = self.viewport_height + self.pvp_shared_bottom_ui_height
            
            self.window = pygame.display.set_mode((self.main_window_width, self.main_window_height))
            pygame.display.set_caption("Pong Soul - PvP Mode (Horizontal Split)")

            self.viewport_width = self.main_window_width // 2 
            self.viewport1_rect = pygame.Rect(0, 0, self.viewport_width, self.viewport_height) 
            self.viewport2_rect = pygame.Rect(self.viewport_width, 0, self.viewport_width, self.viewport_height)
            self.pvp_shared_bottom_ui_rect = pygame.Rect(0, self.viewport_height, self.main_window_width, self.pvp_shared_bottom_ui_height)
            
            self.offset_y = self.ui_offset_y_per_viewport # ⭐️ PvP 模式下，offset_y 指的是視口內的頂部偏移 (目前設為0)
                                                         # 這樣 SlowMoSkill 計算 cy_screen_px 時，如果 cy_game_px 是視口內相對座標，則結果正確。
            if DEBUG_RENDERER:
                print(f"[Renderer.__init__] PvP mode. Main window: {self.main_window_width}x{self.main_window_height}")
                print(f"[Renderer.__init__] Viewport Height: {self.viewport_height}, Shared UI Height: {self.pvp_shared_bottom_ui_height}")
                print(f"[Renderer.__init__] Viewport1 (P1/Left): {self.viewport1_rect}")
                print(f"[Renderer.__init__] Viewport2 (P2/Right): {self.viewport2_rect}")
                print(f"[Renderer.__init__] PvP Shared Bottom UI Rect: {self.pvp_shared_bottom_ui_rect}")
                print(f"[Renderer.__init__] self.offset_y (for PvP viewport context) set to: {self.offset_y}")
        else: # PvA
            self.ui_offset_y_single_view = 100 
            self.offset_y = self.ui_offset_y_single_view # ⭐️ PvA 模式下，offset_y 是頂部UI條高度
            self.main_window_width = self.logical_render_size
            self.main_window_height = self.logical_render_size + 2 * self.offset_y 
            self.window = pygame.display.set_mode((self.main_window_width, self.main_window_height))
            pygame.display.set_caption("Pong Soul - PvA Mode")
            self.game_area_rect = pygame.Rect(0, self.offset_y, self.logical_render_size, self.logical_render_size)
            if DEBUG_RENDERER: 
                print(f"[Renderer.__init__] PvA mode. Main window: {self.main_window_width}x{self.main_window_height}, Game Area: {self.game_area_rect}")
                print(f"[Renderer.__init__] self.offset_y (for PvA top UI) set to: {self.offset_y}")

        self.clock = pygame.time.Clock()
        # ... (球圖像加載等保持不變) ...
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
    
    # ... (render 方法和其他輔助方法) ...


    def _draw_walls(self, target_surface, game_area_width, game_area_height, offset_x=0, offset_y=0, color=(100,100,100), thickness=2):
        """在指定的 surface 內繪製遊戲區域的左右牆壁線。"""
        # 左牆: x=0 (或 thickness/2), 從 y=0 到 y=game_area_height
        # 右牆: x=game_area_width (或 game_area_width - thickness/2), 從 y=0 到 y=game_area_height
        # 這些座標是相對於 target_surface 的，但需要加上 offset_x, offset_y (如果 target_surface 是 self.window)
        
        # 牆壁畫在遊戲邏輯區域的邊緣
        left_wall_x = offset_x + thickness // 2
        right_wall_x = offset_x + game_area_width - thickness // 2
        wall_top_y = offset_y
        wall_bottom_y = offset_y + game_area_height

        pygame.draw.line(target_surface, color, (left_wall_x, wall_top_y), (left_wall_x, wall_bottom_y), thickness)
        pygame.draw.line(target_surface, color, (right_wall_x, wall_top_y), (right_wall_x, wall_bottom_y), thickness)
        if DEBUG_RENDERER: print(f"[Renderer._draw_walls] Walls drawn on surface at L:{left_wall_x}, R:{right_wall_x}, T:{wall_top_y}, B:{wall_bottom_y}")


    def render(self):
        if not self.env: return
        current_time_ticks = pygame.time.get_ticks()
        freeze_active = (self.env.freeze_timer > 0 and (current_time_ticks - self.env.freeze_timer < self.env.freeze_duration))
        current_bg_color = Style.BACKGROUND_COLOR
        if freeze_active: current_bg_color = (220,220,220) if (current_time_ticks//100)%2==0 else (10,10,10)
        self.window.fill(current_bg_color)
        ui_overlay_color = tuple(max(0, c - 20) for c in Style.BACKGROUND_COLOR)

        if self.game_mode == GameSettings.GameMode.PLAYER_VS_PLAYER:
            # PvP 模式
            # 1. 繪製 P1 視口 (左)
            p1_viewport_surface = self.window.subsurface(self.viewport1_rect)
            p1_viewport_surface.fill(current_bg_color) # 可以為P1視口用不同背景以區分
            
            # ⭐️ 在 P1 視口內繪製牆壁 (相對於 p1_viewport_surface)
            # 假設 P1 視口的遊戲區域大小是 self.logical_render_size x self.logical_render_size
            # 並且這個遊戲區域在 p1_viewport_surface 中是居中或從 (0,0) 開始
            # 如果 P1 的視口高度 (self.viewport_height) 就是 self.logical_render_size, 則牆高是 self.logical_render_size
            # 牆寬是 self.logical_render_size (因為球拍左右移動範圍是這個寬度)
            # 但我們的 PvP 視口寬度是 self.viewport_width (e.g. 500)，高度是 self.viewport_height (e.g. 500)
            # 乒乓球的邏輯區域是 self.logical_render_size x self.logical_render_size (e.g. 400x400)
            # 我們需要將這個 400x400 的區域畫在 500x500 的視口內，可以居中或靠邊。
            # 為了簡化，先假設遊戲內容直接畫在視口左上角，大小為 logical_render_size
            game_area_offset_x_in_vp = (self.viewport_width - self.logical_render_size) // 2 # 遊戲區在視口內水平居中
            game_area_offset_y_in_vp = 0 # 遊戲區在視口內垂直靠上 (PVP底部是共享UI)
            
            self._draw_walls(p1_viewport_surface, self.logical_render_size, self.logical_render_size,
                             offset_x=game_area_offset_x_in_vp, offset_y=game_area_offset_y_in_vp)

            # ... (P1 視口的技能渲染、元素繪製邏輯，所有座標都要加上 game_area_offset_x_in_vp 和 game_area_offset_y_in_vp)
            # 例如，球的繪製：
            # cx_px_vp = int(self.env.ball_x * self.logical_render_size) + game_area_offset_x_in_vp
            # cy_px_vp = int(self.env.ball_y * self.logical_render_size) + game_area_offset_y_in_vp
            # p1_viewport_surface.blit(rotated_ball, rect) # rect 要用 _vp 座標
            # 這一大塊繪製邏輯與 PvA 的繪製邏輯非常相似，只是目標 surface 和偏移不同，後續應提取成通用函數。
            # 為了推進，我將複製並修改 PvA 的繪製邏輯到此處。
            if self.env.player1.skill_instance and (self.env.player1.skill_instance.is_active() or \
                (hasattr(self.env.player1.skill_instance, 'fadeout_active') and self.env.player1.skill_instance.fadeout_active) or \
                (hasattr(self.env.player1.skill_instance, 'fog_active') and self.env.player1.skill_instance.fog_active)):
                # 技能渲染也需要知道 viewport 的偏移
                # 暫時假設技能 render 內部會處理，或傳遞 game_area_offset_x/y_in_vp
                self.env.player1.skill_instance.render(p1_viewport_surface) 
            try: 
                cx_px = int(self.env.ball_x * self.logical_render_size) + game_area_offset_x_in_vp
                cy_px = int(self.env.ball_y * self.logical_render_size) + game_area_offset_y_in_vp
                p1_paddle_color = self.env.player1.paddle_color
                p1_x_px = int(self.env.player1.x * self.logical_render_size) + game_area_offset_x_in_vp
                p1_paddle_width_px = self.env.player1.paddle_width 
                p1_paddle_height_px = self.env.paddle_height_px
                pygame.draw.rect(p1_viewport_surface, p1_paddle_color if p1_paddle_color else Style.PLAYER_COLOR,
                    (p1_x_px - p1_paddle_width_px // 2,
                     game_area_offset_y_in_vp + self.logical_render_size - p1_paddle_height_px, # P1球拍在遊戲區底部
                     p1_paddle_width_px, p1_paddle_height_px), border_radius=8)
                opponent_paddle_color = self.env.opponent.paddle_color 
                opponent_x_px = int(self.env.opponent.x * self.logical_render_size) + game_area_offset_x_in_vp
                opponent_paddle_width_px = self.env.opponent.paddle_width
                opponent_paddle_height_px = self.env.paddle_height_px
                pygame.draw.rect(p1_viewport_surface, opponent_paddle_color if opponent_paddle_color else Style.AI_COLOR,
                    (opponent_x_px - opponent_paddle_width_px // 2,
                     game_area_offset_y_in_vp, # 對手球拍在遊戲區頂部
                     opponent_paddle_width_px, opponent_paddle_height_px), border_radius=8)
                for i, (tx_norm, ty_norm) in enumerate(self.env.trail):
                    fade = int(255 * (i + 1) / len(self.env.trail)) if len(self.env.trail) > 0 else 255
                    base_ball_color_rgb = Style.BALL_COLOR[:3] if isinstance(Style.BALL_COLOR, tuple) and len(Style.BALL_COLOR) >=3 else (255,255,255)
                    color = (*base_ball_color_rgb, fade) 
                    trail_circle_radius_px = 4 
                    temp_surf = pygame.Surface((trail_circle_radius_px * 2, trail_circle_radius_px * 2), pygame.SRCALPHA)
                    pygame.draw.circle(temp_surf, color, (trail_circle_radius_px, trail_circle_radius_px), trail_circle_radius_px)
                    trail_x_px = int(tx_norm * self.logical_render_size) + game_area_offset_x_in_vp
                    trail_y_px = int(ty_norm * self.logical_render_size) + game_area_offset_y_in_vp
                    p1_viewport_surface.blit(temp_surf, (trail_x_px - trail_circle_radius_px, trail_y_px - trail_circle_radius_px))
                current_ball_render_image = self.ball_image 
                if not (hasattr(self.env, 'bug_skill_active') and self.env.bug_skill_active):
                    self.ball_angle += self.env.spin * 12 
                rotated_ball = pygame.transform.rotate(current_ball_render_image, self.ball_angle)
                rect = rotated_ball.get_rect(center=(cx_px, cy_px))
                p1_viewport_surface.blit(rotated_ball, rect)
            except Exception as e:
                 if DEBUG_RENDERER: print(f"[Renderer.render] PvP P1 View drawing error: {e}")


            # 2. 繪製 P2 視口 (右) - 暫時還是 WIP
            p2_viewport_surface = self.window.subsurface(self.viewport2_rect)
            p2_viewport_surface.fill(Style.AI_COLOR) # 用不同背景色區分
            # ⭐️ 在 P2 視口內繪製牆壁 (示意，之後 P2 會有自己的旋轉視角)
            self._draw_walls(p2_viewport_surface, self.logical_render_size, self.logical_render_size,
                             offset_x=game_area_offset_x_in_vp, offset_y=game_area_offset_y_in_vp, color=(0,200,0)) # 用綠色牆壁示意
            font_temp = Style.get_font(30)
            p2_text = font_temp.render("Player 2 View (WIP)", True, Style.TEXT_COLOR)
            p2_text_rect = p2_text.get_rect(center=(self.viewport_width // 2, self.viewport_height // 2))
            p2_viewport_surface.blit(p2_text, p2_text_rect)

            # 3. 繪製底部共享 UI 區域背景
            pygame.draw.rect(self.window, ui_overlay_color, self.pvp_shared_bottom_ui_rect)
            
            # 4. 在底部共享 UI 區域繪製 P1 和 P2 的技能條和血條
            self._render_pvp_bottom_ui(self.window, self.env.player1, self.env.opponent, self.pvp_shared_bottom_ui_rect)

            # 5. 繪製中間的分割線 (如果需要，且在所有視口繪製完之後)
            pygame.draw.line(self.window, (80, 80, 80), (self.viewport_width, 0), (self.viewport_width, self.viewport_height), 3)


        else: # PvA 模式
            # PvA UI 條
            pygame.draw.rect(self.window, ui_overlay_color, (0, 0, self.main_window_width, self.ui_offset_y_single_view))
            bottom_ui_y_start_pva = self.ui_offset_y_single_view + self.logical_render_size
            bottom_ui_height_pva = self.main_window_height - bottom_ui_y_start_pva
            if bottom_ui_height_pva > 0:
                 pygame.draw.rect(self.window, ui_overlay_color, (0, bottom_ui_y_start_pva, self.main_window_width, bottom_ui_height_pva))

            # ⭐️ 在 PvA 遊戲區域繪製牆壁
            self._draw_walls(self.window, self.logical_render_size, self.logical_render_size,
                             offset_x=0, offset_y=self.ui_offset_y_single_view) # PvA 遊戲區 Y 偏移

            # ... (PvA 的技能渲染、元素繪製、血條繪製邏輯與上一版本相似，但要確保座標基於 game_area_rect 或 ui_offset_y_single_view)
            # 為了簡潔，我將複製並調整PvA的繪製邏輯
            current_drawing_offset_y = self.ui_offset_y_single_view # PvA 繪圖的Y軸基準點
            if self.env.player1.skill_instance and (self.env.player1.skill_instance.is_active() or \
                (hasattr(self.env.player1.skill_instance, 'fadeout_active') and self.env.player1.skill_instance.fadeout_active) or \
                (hasattr(self.env.player1.skill_instance, 'fog_active') and self.env.player1.skill_instance.fog_active)):
                self.env.player1.skill_instance.render(self.window) # PvA 技能直接畫在主視窗
            try: 
                cx_px = int(self.env.ball_x * self.logical_render_size)
                cy_px = int(self.env.ball_y * self.logical_render_size) + current_drawing_offset_y
                # P1 球拍
                p1_paddle_color = self.env.player1.paddle_color
                p1_x_px = int(self.env.player1.x * self.logical_render_size)
                p1_paddle_width_px = self.env.player1.paddle_width 
                p1_paddle_height_px = self.env.paddle_height_px
                pygame.draw.rect(self.window, p1_paddle_color if p1_paddle_color else Style.PLAYER_COLOR,
                    (p1_x_px - p1_paddle_width_px // 2,
                     current_drawing_offset_y + self.logical_render_size - p1_paddle_height_px,
                     p1_paddle_width_px, p1_paddle_height_px), border_radius=8)
                # Opponent 球拍
                opponent_paddle_color = self.env.opponent.paddle_color
                opponent_x_px = int(self.env.opponent.x * self.logical_render_size)
                opponent_paddle_width_px = self.env.opponent.paddle_width
                opponent_paddle_height_px = self.env.paddle_height_px
                pygame.draw.rect(self.window, opponent_paddle_color if opponent_paddle_color else Style.AI_COLOR,
                    (opponent_x_px - opponent_paddle_width_px // 2,
                     current_drawing_offset_y, 
                     opponent_paddle_width_px, opponent_paddle_height_px), border_radius=8)
                # 拖尾
                for i, (tx_norm, ty_norm) in enumerate(self.env.trail):
                    fade = int(255 * (i + 1) / len(self.env.trail)) if len(self.env.trail) > 0 else 255
                    base_ball_color_rgb = Style.BALL_COLOR[:3] if isinstance(Style.BALL_COLOR, tuple) and len(Style.BALL_COLOR) >=3 else (255,255,255)
                    color = (*base_ball_color_rgb, fade) 
                    trail_circle_radius_px = 4 
                    temp_surf = pygame.Surface((trail_circle_radius_px * 2, trail_circle_radius_px * 2), pygame.SRCALPHA)
                    pygame.draw.circle(temp_surf, color, (trail_circle_radius_px, trail_circle_radius_px), trail_circle_radius_px)
                    trail_x_px = int(tx_norm * self.logical_render_size)
                    trail_y_px = int(ty_norm * self.logical_render_size) + current_drawing_offset_y
                    self.window.blit(temp_surf, (trail_x_px - trail_circle_radius_px, trail_y_px - trail_circle_radius_px))
                # 球圖像
                current_ball_render_image = self.ball_image 
                if not (hasattr(self.env, 'bug_skill_active') and self.env.bug_skill_active):
                    self.ball_angle += self.env.spin * 12 
                rotated_ball = pygame.transform.rotate(current_ball_render_image, self.ball_angle)
                rect = rotated_ball.get_rect(center=(cx_px, cy_px))
                self.window.blit(rotated_ball, rect)
                # 血條
                bar_w_px, bar_h_px, spacing_px = 150, 20, 20;
                # Opponent (AI) 血條 - 位於上方 UI 條
                pygame.draw.rect(self.window, Style.AI_BAR_BG, (self.main_window_width - bar_w_px - spacing_px, spacing_px, bar_w_px, bar_h_px))
                opp_flash = (current_time_ticks - self.env.opponent.last_hit_time < self.env.freeze_duration)
                opp_fill_color = (255,255,255) if (opp_flash and (current_time_ticks//100%2==0)) else Style.AI_BAR_FILL
                opponent_life_ratio = self.env.opponent.lives / self.env.opponent.max_lives if self.env.opponent.max_lives > 0 else 0
                pygame.draw.rect(self.window, opp_fill_color, (self.main_window_width - bar_w_px - spacing_px, spacing_px, bar_w_px * opponent_life_ratio, bar_h_px))
                # P1 血條 - 位於下方 UI 條
                player_bar_y_pos = self.main_window_height - self.ui_offset_y_single_view + spacing_px 
                pygame.draw.rect(self.window, Style.PLAYER_BAR_BG, (spacing_px, player_bar_y_pos, bar_w_px, bar_h_px))
                p1_flash = (current_time_ticks - self.env.player1.last_hit_time < self.env.freeze_duration)
                p1_fill_color = (255,255,255) if (p1_flash and (current_time_ticks//100%2==0)) else Style.PLAYER_BAR_FILL
                player1_life_ratio = self.env.player1.lives / self.env.player1.max_lives if self.env.player1.max_lives > 0 else 0
                pygame.draw.rect(self.window, p1_fill_color, (spacing_px, player_bar_y_pos, bar_w_px * player1_life_ratio, bar_h_px))
            except AttributeError as e:
                if DEBUG_RENDERER: print(f"[Renderer.render] PvA AttributeError: {e}")
            except Exception as e:
                if DEBUG_RENDERER: print(f"[Renderer.render] PvA Generic Render Error: {e}")
            
            self._render_skill_ui_for_pva(self.env.player1) # PvA P1 技能 UI

        pygame.display.flip()
        self.clock.tick(60)

    def _render_pvp_bottom_ui(self, target_surface, player1_state, player2_state, ui_rect):
        """在 PvP 模式的底部共享 UI 區域繪製雙方的血條和技能條。"""
        if DEBUG_RENDERER: print(f"[Renderer._render_pvp_bottom_ui] Drawing shared UI in rect: {ui_rect}")
        target_surface.fill(Style.UI_BACKGROUND_COLOR if hasattr(Style, 'UI_BACKGROUND_COLOR') else (30,30,30) , ui_rect) # 填充UI條背景

        bar_w_px, bar_h_px, spacing_px = 150, 20, 15 # UI元素的基本尺寸和間距
        skill_bar_w_px, skill_bar_h_px = 100, 10
        
        # P1 UI (在共享條的左側)
        p1_start_x = ui_rect.left + spacing_px
        p1_ui_y = ui_rect.top + (ui_rect.height - bar_h_px - skill_bar_h_px - spacing_px) // 2 # 垂直居中排列血條和技能條
        
        # P1 血條
        pygame.draw.rect(target_surface, Style.PLAYER_BAR_BG, (p1_start_x, p1_ui_y, bar_w_px, bar_h_px))
        p1_life_ratio = player1_state.lives / player1_state.max_lives if player1_state.max_lives > 0 else 0
        pygame.draw.rect(target_surface, Style.PLAYER_BAR_FILL, (p1_start_x, p1_ui_y, bar_w_px * p1_life_ratio, bar_h_px))
        
        # P1 技能條 (在血條下方)
        p1_skill_y = p1_ui_y + bar_h_px + spacing_px // 2
        if player1_state.skill_instance:
            self._render_single_skill_bar(target_surface, player1_state, p1_start_x, p1_skill_y, skill_bar_w_px, skill_bar_h_px)

        # P2 UI (在共享條的右側)
        p2_start_x_from_right = spacing_px + bar_w_px # 從右邊緣向左計算血條起始點
        p2_ui_x_base = ui_rect.right - p2_start_x_from_right # 血條的X座標
        p2_ui_y = ui_rect.top + (ui_rect.height - bar_h_px - skill_bar_h_px - spacing_px) // 2

        # P2 血條
        pygame.draw.rect(target_surface, Style.AI_BAR_BG, (p2_ui_x_base, p2_ui_y, bar_w_px, bar_h_px)) # P2 用 AI 的顏色風格
        p2_life_ratio = player2_state.lives / player2_state.max_lives if player2_state.max_lives > 0 else 0
        pygame.draw.rect(target_surface, Style.AI_BAR_FILL, (p2_ui_x_base, p2_ui_y, bar_w_px * p2_life_ratio, bar_h_px))
        
        # P2 技能條 (在血條下方)
        p2_skill_y = p2_ui_y + bar_h_px + spacing_px // 2
        if player2_state.skill_instance:
             # 技能條的X座標也需要從右邊計算對齊或居中在血條下方
            p2_skill_x = p2_ui_x_base + (bar_w_px - skill_bar_w_px) // 2 # 技能條在血條下方居中
            self._render_single_skill_bar(target_surface, player2_state, p2_skill_x, p2_skill_y, skill_bar_w_px, skill_bar_h_px)


    def _render_single_skill_bar(self, surface, player_state, x, y, width, height):
        """輔助方法：繪製單個技能條及其冷卻文字。"""
        skill = player_state.skill_instance
        text_offset_y_px = 15 # 文字在條下方多少像素
        
        skill_cfg = SKILL_CONFIGS.get(player_state.skill_code_name, {})
        bar_fill_color_rgb = skill_cfg.get("bar_color", (200, 200, 200))
        bar_bg_color_rgb = (50,50,50)
        
        pygame.draw.rect(surface, bar_bg_color_rgb, (x, y, width, height))
        energy_ratio = skill.get_energy_ratio()
        current_bar_width = int(width * energy_ratio)
        pygame.draw.rect(surface, bar_fill_color_rgb, (x, y, current_bar_width, height))
        
        if not skill.is_active():
            cooldown_sec = skill.get_cooldown_seconds()
            if cooldown_sec > 0:
                font = Style.get_font(12) # 可以用小一點的字體
                text_surf = font.render(f"{cooldown_sec:.1f}s", True, Style.TEXT_COLOR)
                text_rect = text_surf.get_rect(center=(x + width / 2, y + height + text_offset_y_px))
                surface.blit(text_surf, text_rect)
    
    # _render_skill_ui_for_pva 和 _render_skill_ui_for_viewport 可以移除或保留作為參考
    # 但 _render_pvp_bottom_ui 和 _render_single_skill_bar 是新的核心

    def _render_skill_ui_for_pva(self, player_state): # PvA 模式 P1 技能 UI (在下方UI條)
        if not player_state.skill_instance: return
        bar_w_px = 150; bar_h_px = 20; spacing_px = 20 # PvA 血條尺寸
        skill_bar_w_px = 100; skill_bar_h_px = 10 # PvA 技能條尺寸
        
        # PvA 的 P1 技能條通常在血條右側
        p1_health_bar_x_end = spacing_px + bar_w_px 
        bar_x_px = p1_health_bar_x_end + spacing_px 
        # 和血條同一 Y 基準線 (在主視窗的下方 UI 條內)
        bar_y_px = self.main_window_height - self.ui_offset_y_single_view + spacing_px + (bar_h_px - skill_bar_h_px)//2 # 垂直居中對齊血條
        
        self._render_single_skill_bar(self.window, player_state, bar_x_px, bar_y_px, skill_bar_w_px, skill_bar_h_px)


    def close(self):
        if DEBUG_RENDERER: print("[Renderer.close] Closing Renderer.")