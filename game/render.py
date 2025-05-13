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


    def _render_player_view(self, target_surface, view_player_state, opponent_state_for_this_view, 
                            game_area_rect_in_target_surface, is_top_player_perspective=False):
        """
        在 target_surface 內，根據 game_area_rect_in_target_surface 定義的遊戲區域，
        從 view_player_state 的視角繪製遊戲元素。

        Args:
            target_surface: 要繪製到的 pygame Surface。
            view_player_state: 當前視角的玩家 (PlayerState 實例)。
            opponent_state_for_this_view: 在此視角中，view_player 的對手 (PlayerState 實例)。
            game_area_rect_in_target_surface: pygame.Rect，定義了在 target_surface 中，
                                             邏輯遊戲區域 (0-1正規化座標) 應該被映射到的像素區域。
                                             例如 Rect(offset_x, offset_y, logical_width_px, logical_height_px)
            is_top_player_perspective: 布林值。如果為 True，則 Y 軸和某些元素需要上下顛倒來模擬
                                       頂部玩家看到自己在本方（底部）的效果。
        """
        if DEBUG_RENDERER: 
            print(f"[Renderer._render_player_view] For {view_player_state.identifier}, TargetSurf: {target_surface.get_size()}, GameAreaRect: {game_area_rect_in_target_surface}, IsTopPerspective: {is_top_player_perspective}")

        # 從 game_area_rect_in_target_surface 獲取繪圖基準和尺寸
        ga_x = game_area_rect_in_target_surface.x
        ga_y = game_area_rect_in_target_surface.y
        ga_w = game_area_rect_in_target_surface.width  # 這是 self.logical_render_size
        ga_h = game_area_rect_in_target_surface.height # 這也是 self.logical_render_size (假設正方形邏輯區域)

        # 1. 繪製牆壁 (在此遊戲區域內)
        self._draw_walls(target_surface, ga_w, ga_h, offset_x=ga_x, offset_y=ga_y)

        # 2. 技能渲染 (先渲染底層效果)
        #    技能的 render 方法需要知道它是在哪個 surface 和 rect 內渲染
        #    這一步比較複雜，因為技能的 render 可能有自己的全螢幕假設
        #    暫時：如果技能是 view_player 的，就調用它。
        if view_player_state.skill_instance and \
           (view_player_state.skill_instance.is_active() or \
            (hasattr(view_player_state.skill_instance, 'fadeout_active') and view_player_state.skill_instance.fadeout_active) or \
            (hasattr(view_player_state.skill_instance, 'fog_active') and view_player_state.skill_instance.fog_active)):
            # 理想情況：skill.render(target_surface, game_area_rect_in_target_surface)
            # 暫時：讓技能在 target_surface 上畫，它需要自己處理座標轉換
            # 這意味著 SlowMoSkill 的 render 內部需要知道它畫的是 P1 視角還是 P2 視角，
            # 並且其衝擊波、時鐘等的位置計算要相對於 game_area_rect。
            # 為了本步驟簡化，我們先假設技能渲染暫時還按舊方式（可能只在P1視口畫對）。
            if not is_top_player_perspective: # 暫時只為 P1 (底部玩家) 渲染技能特效
                 view_player_state.skill_instance.render(target_surface)


        # 3. 繪製主要遊戲元素
        try:
            # 球的座標
            ball_norm_x, ball_norm_y = self.env.ball_x, self.env.ball_y
            if is_top_player_perspective: # 如果是頂部玩家的視角，Y 軸顛倒
                ball_norm_y = 1.0 - ball_norm_y
            
            cx_px = int(ball_norm_x * ga_w) + ga_x
            cy_px = int(ball_norm_y * ga_h) + ga_y

            # 視角玩家的球拍 (總是在此視角的底部)
            # view_player 的 X 位置是相對於整個邏輯場地的
            vp_paddle_norm_x = view_player_state.x
            # if is_top_player_perspective: # 如果 P2 在上方，其X軸可能也需要鏡像，取決於你希望的控制感
            #     vp_paddle_norm_x = 1.0 - vp_paddle_norm_x # 讓P2的左變成右，右變成左

            vp_paddle_x_px = int(vp_paddle_norm_x * ga_w) + ga_x
            vp_paddle_width_px = view_player_state.paddle_width # 已經是像素
            vp_paddle_height_px = self.env.paddle_height_px
            vp_paddle_color = view_player_state.paddle_color if view_player_state.paddle_color else Style.PLAYER_COLOR # 假設 view_player 是 "我方"顏色

            # 繪製 view_player 的球拍 (在此視角的底部)
            pygame.draw.rect(target_surface, vp_paddle_color,
                (vp_paddle_x_px - vp_paddle_width_px // 2,
                 ga_y + ga_h - vp_paddle_height_px, # 在遊戲區域底部
                 vp_paddle_width_px, vp_paddle_height_px), border_radius=8)

            # 對手玩家的球拍 (總是在此視角的頂部)
            opp_paddle_norm_x = opponent_state_for_this_view.x
            # if is_top_player_perspective: # 同理，對手的X也可能需要鏡像
            #    opp_paddle_norm_x = 1.0 - opp_paddle_norm_x

            opp_paddle_x_px = int(opp_paddle_norm_x * ga_w) + ga_x
            opp_paddle_width_px = opponent_state_for_this_view.paddle_width
            opp_paddle_height_px = self.env.paddle_height_px
            opp_paddle_color = opponent_state_for_this_view.paddle_color if opponent_state_for_this_view.paddle_color else Style.AI_COLOR # 假設對手是 "敵方"顏色

            pygame.draw.rect(target_surface, opp_paddle_color,
                (opp_paddle_x_px - opp_paddle_width_px // 2,
                 ga_y, # 在遊戲區域頂部
                 opp_paddle_width_px, opp_paddle_height_px), border_radius=8)

            # 球的拖尾
            # 拖尾座標也需要根據 is_top_player_perspective 進行 Y 軸轉換
            for i, (tx_norm, ty_norm) in enumerate(self.env.trail):
                trail_y_to_draw = ty_norm
                if is_top_player_perspective:
                    trail_y_to_draw = 1.0 - ty_norm
                
                fade = int(255 * (i + 1) / len(self.env.trail)) if len(self.env.trail) > 0 else 255
                base_ball_color_rgb = Style.BALL_COLOR[:3] if isinstance(Style.BALL_COLOR, tuple) and len(Style.BALL_COLOR) >=3 else (255,255,255)
                color = (*base_ball_color_rgb, fade) 
                trail_circle_radius_px = 4 
                temp_surf = pygame.Surface((trail_circle_radius_px * 2, trail_circle_radius_px * 2), pygame.SRCALPHA)
                pygame.draw.circle(temp_surf, color, (trail_circle_radius_px, trail_circle_radius_px), trail_circle_radius_px)
                
                trail_x_px = int(tx_norm * ga_w) + ga_x
                trail_y_px = int(trail_y_to_draw * ga_h) + ga_y
                target_surface.blit(temp_surf, (trail_x_px - trail_circle_radius_px, trail_y_px - trail_circle_radius_px))
            
            # 球圖像
            current_ball_render_image = self.ball_image # 之後由 SoulEaterBug 替換
            # 球的旋轉角度：如果視角顛倒，旋轉方向也應相反
            ball_spin_for_view = self.env.spin
            if is_top_player_perspective:
                ball_spin_for_view = -self.env.spin # 視覺上旋轉方向相反

            # self.ball_angle 是 Renderer 的一個狀態，可能需要為每個視角獨立，或傳遞
            # 暫時共用 self.ball_angle，但用 ball_spin_for_view
            # 這部分旋轉還不完美，因為 self.ball_angle 會持續累加
            # 理想情況是球有個絕對角度，然後根據視角調整
            # 為了簡單，這裡的旋轉可能在雙視圖下看起來不協調
            current_angle = self.ball_angle + ball_spin_for_view * 12 # 模擬累加
            
            rotated_ball = pygame.transform.rotate(current_ball_render_image, current_angle) # 使用 current_angle
            rect = rotated_ball.get_rect(center=(cx_px, cy_px))
            target_surface.blit(rotated_ball, rect)

        except Exception as e:
             if DEBUG_RENDERER: print(f"[Renderer._render_player_view] ({view_player_state.identifier}) drawing error: {e}")


    def render(self):
        if not self.env: return
        # ... (freeze, background fill, ui_overlay_color - 保持不變) ...
        current_time_ticks = pygame.time.get_ticks()
        freeze_active = (self.env.freeze_timer > 0 and (current_time_ticks - self.env.freeze_timer < self.env.freeze_duration))
        current_bg_color = Style.BACKGROUND_COLOR
        if freeze_active: current_bg_color = (220,220,220) if (current_time_ticks//100)%2==0 else (10,10,10)
        self.window.fill(current_bg_color)
        ui_overlay_color = tuple(max(0, c - 20) for c in Style.BACKGROUND_COLOR)


        if self.game_mode == GameSettings.GameMode.PLAYER_VS_PLAYER:
            # PvP 模式
            # 1. 定義 P1 視口的遊戲區域 (在左視口內，可能居中)
            # self.logical_render_size 是遊戲邏輯區域的邊長 (e.g., 400)
            # self.viewport_width 是左視口的寬度 (e.g., 500)
            # self.viewport_height 是左視口的高度 (e.g., 500, 因為底部有共享UI條)
            p1_game_area_offset_x = (self.viewport_width - self.logical_render_size) // 2
            p1_game_area_offset_y = 0 # 假設遊戲區在視口內垂直靠頂
            p1_game_area_rect_in_vp1 = pygame.Rect(p1_game_area_offset_x, p1_game_area_offset_y, 
                                                 self.logical_render_size, self.logical_render_size)
            
            p1_viewport_surface = self.window.subsurface(self.viewport1_rect)
            p1_viewport_surface.fill(Style.PLAYER_COLOR if hasattr(Style,'PLAYER_VIEW_BG') else (20,20,60)) # P1視口背景
            
            # 為 P1 繪製其視角 (P1是底部玩家，所以 is_top_player_perspective=False)
            self._render_player_view(p1_viewport_surface, self.env.player1, self.env.opponent, 
                                     p1_game_area_rect_in_vp1, is_top_player_perspective=False)

            # 2. 定義 P2 視口的遊戲區域 (在右視口內)
            p2_game_area_offset_x = (self.viewport_width - self.logical_render_size) // 2
            p2_game_area_offset_y = 0 
            p2_game_area_rect_in_vp2 = pygame.Rect(p2_game_area_offset_x, p2_game_area_offset_y,
                                                 self.logical_render_size, self.logical_render_size)

            p2_viewport_surface = self.window.subsurface(self.viewport2_rect)
            p2_viewport_surface.fill(Style.AI_COLOR if hasattr(Style,'OPPONENT_VIEW_BG') else (60,20,20)) # P2視口背景
            
            # ⭐️ 為 P2 繪製其視角 (P2/Opponent 在邏輯上是頂部玩家，所以 is_top_player_perspective=True)
            self._render_player_view(p2_viewport_surface, self.env.opponent, self.env.player1,
                                     p2_game_area_rect_in_vp2, is_top_player_perspective=True)

            # 3. 繪製底部共享 UI
            pygame.draw.rect(self.window, ui_overlay_color, self.pvp_shared_bottom_ui_rect)
            self._render_pvp_bottom_ui(self.window, self.env.player1, self.env.opponent, self.pvp_shared_bottom_ui_rect)
            
            # 4. 繪製中間分割線
            pygame.draw.line(self.window, (80,80,80), (self.viewport_width, 0), (self.viewport_width, self.viewport_height), 3) # 只畫到視口高度

        else: # PvA 模式 (與之前類似，但使用 _render_player_view)
            # PvA UI 條
            pygame.draw.rect(self.window, ui_overlay_color, (0, 0, self.main_window_width, self.ui_offset_y_single_view))
            bottom_ui_y_start_pva = self.ui_offset_y_single_view + self.logical_render_size
            bottom_ui_height_pva = self.main_window_height - bottom_ui_y_start_pva
            if bottom_ui_height_pva > 0:
                 pygame.draw.rect(self.window, ui_overlay_color, (0, bottom_ui_y_start_pva, self.main_window_width, bottom_ui_height_pva))

            # PvA 遊戲區域定義 (相對於 self.window)
            pva_game_area_on_window = pygame.Rect(0, self.ui_offset_y_single_view, 
                                                self.logical_render_size, self.logical_render_size)
            
            # PvA 模式下，P1 是視角玩家，Opponent (AI) 是其對手
            self._render_player_view(self.window, self.env.player1, self.env.opponent,
                                     pva_game_area_on_window, is_top_player_perspective=False)
            
            # PvA P1 技能 UI (繪製在主視窗的底部UI條)
            self._render_skill_ui_for_pva(self.env.player1)


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