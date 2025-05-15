# pong-soul/game/render.py
import math
import pygame
from game.theme import Style
from game.settings import GameSettings
from utils import resource_path
from game.skills.skill_config import SKILL_CONFIGS # 用於技能條顏色等

DEBUG_RENDERER = True
DEBUG_RENDERER_FULLSCREEN = True

class Renderer:
    def __init__(self, env, game_mode, actual_screen_surface, actual_screen_width, actual_screen_height):
        if DEBUG_RENDERER: print(f"[Renderer.__init__] Initializing Renderer for game_mode: {game_mode}")
        if DEBUG_RENDERER_FULLSCREEN:
            print(f"[DEBUG_RENDERER_FULLSCREEN][Renderer.__init__] Received actual_screen_surface: {type(actual_screen_surface)}")
            if actual_screen_surface:
                print(f"    Surface size: {actual_screen_surface.get_size()}, Expected: {actual_screen_width}x{actual_screen_height}")

        self.env = env
        self.game_mode = game_mode
        self.logical_game_area_size = env.render_size # 純遊戲區域的邏輯尺寸 (e.g., 400x400)

        if actual_screen_surface:
            self.window = actual_screen_surface
            self.actual_screen_width = actual_screen_width
            self.actual_screen_height = actual_screen_height
        else: # Fallback (不應在正常流程發生)
            if DEBUG_RENDERER_FULLSCREEN: print(f"[DEBUG_RENDERER_FULLSCREEN][Renderer.__init__] No surface! Fallback window (breaks fullscreen).")
            self.actual_screen_width, self.actual_screen_height = 1000, 700
            try:
                self.window = pygame.display.set_mode((self.actual_screen_width, self.actual_screen_height))
                pygame.display.set_caption("Pong Soul - Renderer Fallback")
            except pygame.error as e:
                raise RuntimeError(f"Renderer could not establish a drawing surface: {e}")

        # ⭐️ 步驟 1: 定義遊戲內容的整體「邏輯佈局尺寸」
        # 這些尺寸是遊戲 UI (包含遊戲區域、UI條等) 在設計時的畫布大小。
        if self.game_mode == GameSettings.GameMode.PLAYER_VS_PLAYER:
            self.logical_layout_width = 1000 # PvP 總佈局寬度 (例如: 2個400寬遊戲區+邊距 = 假設1000)
                                             # 或者更精確：(env.render_size * 2) 如果是緊密排列
                                             # 這裡我們假設 PvP 的兩個遊戲視口各佔 500 邏輯寬度
            self.logical_pvp_game_area_width_per_viewport = self.logical_game_area_size # 每個視口內的遊戲區邏輯寬
            self.logical_pvp_viewport_width = 500 # 假設每個 PvP 視口的設計寬度
            self.logical_layout_width = self.logical_pvp_viewport_width * 2

            self.logical_pvp_game_area_height = self.logical_game_area_size # 遊戲區邏輯高
            self.logical_pvp_shared_ui_height = 100 # 底部共享UI的邏輯高度
            self.logical_layout_height = self.logical_pvp_game_area_height + self.logical_pvp_shared_ui_height
        else: # PvA
            self.logical_layout_width = self.logical_game_area_size # PvA 佈局寬度等於遊戲區邏輯寬度
            self.logical_pva_ui_bar_height = 100 # PvA 上下UI條的邏輯高度
            self.logical_layout_height = self.logical_game_area_size + 2 * self.logical_pva_ui_bar_height

        if DEBUG_RENDERER_FULLSCREEN:
            print(f"[DEBUG_RENDERER_FULLSCREEN][Renderer.__init__] Game Mode: {self.game_mode}")
            print(f"    Logical Game Area Size (env.render_size): {self.logical_game_area_size}x{self.logical_game_area_size}")
            print(f"    Renderer Logical Layout: {self.logical_layout_width}x{self.logical_layout_height}")

        # ⭐️ 步驟 2: 計算遊戲內容整體的縮放因子和居中渲染區域
        scale_x = self.actual_screen_width / self.logical_layout_width
        scale_y = self.actual_screen_height / self.logical_layout_height
        self.game_content_scale_factor = min(scale_x, scale_y) # 保持寬高比

        self.scaled_layout_width = int(self.logical_layout_width * self.game_content_scale_factor)
        self.scaled_layout_height = int(self.logical_layout_height * self.game_content_scale_factor)

        self.layout_offset_x = (self.actual_screen_width - self.scaled_layout_width) // 2
        self.layout_offset_y = (self.actual_screen_height - self.scaled_layout_height) // 2

        # 這是整個遊戲內容 (PvA的完整界面或PvP的完整界面) 在螢幕上縮放並居中後的 Rect
        self.game_content_render_area_on_screen = pygame.Rect(
            self.layout_offset_x, self.layout_offset_y,
            self.scaled_layout_width, self.scaled_layout_height
        )
        # ⭐️ 這個 scale_factor 用於縮放所有遊戲內元素和UI元素
        # ⭐️ Renderer 給滑鼠座標轉換提供的 scale_factor 也應該是這個
        self.scale_factor_for_game = self.game_content_scale_factor # 給外部使用 (如 main.py 的滑鼠轉換)


        if DEBUG_RENDERER_FULLSCREEN:
            print(f"[DEBUG_RENDERER_FULLSCREEN][Renderer.__init__] Game Content Scaling:")
            print(f"    Scale Factor: {self.game_content_scale_factor:.4f}")
            print(f"    Scaled Layout Size: {self.scaled_layout_width}x{self.scaled_layout_height}")
            print(f"    Layout Offset (Centering): ({self.layout_offset_x}, {self.layout_offset_y})")
            print(f"    Game Content Render Area on Screen: {self.game_content_render_area_on_screen}")

        # ⭐️ 步驟 3: 根據縮放後的佈局，重新計算 PvP 或 PvA 的具體繪圖區域 (Rects)
        # 這些 Rect 的座標是相對於 self.window (全螢幕) 左上角的絕對像素座標。
        s = self.game_content_scale_factor # 簡寫
        area_left = self.game_content_render_area_on_screen.left
        area_top = self.game_content_render_area_on_screen.top

        if self.game_mode == GameSettings.GameMode.PLAYER_VS_PLAYER:
            scaled_pvp_viewport_width = int(self.logical_pvp_viewport_width * s)
            scaled_pvp_game_area_height = int(self.logical_pvp_game_area_height * s) # 等於 scaled_logical_game_area_size
            scaled_pvp_shared_ui_height = int(self.logical_pvp_shared_ui_height * s)

            # PvP 視口內的遊戲區域，其邏輯尺寸是 self.logical_game_area_size
            # 我們需要將這個邏輯尺寸的遊戲區域，居中繪製到 scaled_pvp_viewport_width x scaled_pvp_game_area_height 的視口內
            # 假設 self.logical_pvp_viewport_width 是為了容納 self.logical_game_area_size 並可能包含一些邊距
            # 簡化：假設遊戲區域直接填滿視口的分配寬高（需要確保 viewport_width/height 是為遊戲區設計的）
            
            # Viewport1 (左邊)
            vp1_left = area_left
            vp1_top = area_top
            self.viewport1_game_area_on_screen = pygame.Rect( # P1 遊戲區域在螢幕上的實際繪圖矩形
                vp1_left + (scaled_pvp_viewport_width - int(self.logical_game_area_size * s)) // 2, # 遊戲區在視口內X居中
                vp1_top,  # 遊戲區在視口內Y靠上
                int(self.logical_game_area_size * s),     # 縮放後的遊戲區寬
                scaled_pvp_game_area_height               # 縮放後的遊戲區高 (等於視口遊戲區高)
            )

            # Viewport2 (右邊)
            vp2_left = area_left + scaled_pvp_viewport_width
            vp2_top = area_top
            self.viewport2_game_area_on_screen = pygame.Rect( # P2 遊戲區域在螢幕上的實際繪圖矩形
                vp2_left + (scaled_pvp_viewport_width - int(self.logical_game_area_size * s)) // 2,
                vp2_top,
                int(self.logical_game_area_size * s),
                scaled_pvp_game_area_height
            )
            
            # 共享UI條
            self.pvp_shared_bottom_ui_rect_on_screen = pygame.Rect(
                area_left, # 從整體佈局的左邊開始
                area_top + scaled_pvp_game_area_height, # 在視口下方
                self.scaled_layout_width, # UI條橫跨整個縮放後的佈局寬度
                scaled_pvp_shared_ui_height
            )
            self.offset_y = 0 # PvP模式下，遊戲區域在其視口內通常從頂部開始

            if DEBUG_RENDERER_FULLSCREEN:
                print(f"    PvP Scaled Viewport Width (each): {scaled_pvp_viewport_width}")
                print(f"    PvP Scaled Game Area Height (in viewport): {scaled_pvp_game_area_height}")
                print(f"    P1 Game Area on Screen: {self.viewport1_game_area_on_screen}")
                print(f"    P2 Game Area on Screen: {self.viewport2_game_area_on_screen}")
                print(f"    PvP Scaled Shared UI Rect on Screen: {self.pvp_shared_bottom_ui_rect_on_screen}")

        else: # PvA
            scaled_pva_ui_bar_height = int(self.logical_pva_ui_bar_height * s)
            scaled_logical_game_area_size = int(self.logical_game_area_size * s)

            self.pva_top_ui_rect_on_screen = pygame.Rect(
                area_left, area_top,
                self.scaled_layout_width, scaled_pva_ui_bar_height
            )
            self.game_area_rect_on_screen = pygame.Rect( # PvA 遊戲區域在螢幕上的實際繪圖矩形
                area_left, # 遊戲區域在縮放佈局內X靠左
                area_top + scaled_pva_ui_bar_height, # 在頂部UI條下方
                scaled_logical_game_area_size, # 縮放後的遊戲區寬
                scaled_logical_game_area_size  # 縮放後的遊戲區高
            )
            self.pva_bottom_ui_rect_on_screen = pygame.Rect(
                area_left, area_top + scaled_pva_ui_bar_height + scaled_logical_game_area_size,
                self.scaled_layout_width, scaled_pva_ui_bar_height
            )
            self.offset_y = scaled_pva_ui_bar_height # PvA 模式下，遊戲區域的頂部偏移是縮放後的UI條高度
                                                     # 注意：這個 offset_y 是相對於 area_top 的

            if DEBUG_RENDERER_FULLSCREEN:
                print(f"    PvA Scaled UI Bar Height: {scaled_pva_ui_bar_height}")
                print(f"    PvA Scaled Game Area Size: {scaled_logical_game_area_size}x{scaled_logical_game_area_size}")
                print(f"    PvA Top UI Rect on Screen: {self.pva_top_ui_rect_on_screen}")
                print(f"    PvA Game Area Rect on Screen: {self.game_area_rect_on_screen}")
                print(f"    PvA Bottom UI Rect on Screen: {self.pva_bottom_ui_rect_on_screen}")
                print(f"    PvA self.offset_y (scaled top bar for skills): {self.offset_y}")


        self.clock = pygame.time.Clock()
        try:
            # ⭐️ 球的圖像尺寸基於縮放後的邏輯球半徑
            scaled_ball_diameter_px = int(env.ball_radius_px * 2 * self.game_content_scale_factor)
            if scaled_ball_diameter_px <= 0: scaled_ball_diameter_px = max(1, int(20 * self.game_content_scale_factor))
            
            # 原始圖像只加載一次
            if not hasattr(self, '_ball_image_original_loaded'): # 避免重複加載
                self._ball_image_original_loaded = pygame.image.load(resource_path("assets/sunglasses.png")).convert_alpha()

            self.ball_image = pygame.transform.smoothscale(self._ball_image_original_loaded, (scaled_ball_diameter_px, scaled_ball_diameter_px))
            # SoulEaterBugSkill 更換圖像時，也需要用 game_content_scale_factor 縮放蟲子圖像
            if DEBUG_RENDERER_FULLSCREEN:
                print(f"[DEBUG_RENDERER_FULLSCREEN][Renderer.__init__] Ball image scaled to diameter: {scaled_ball_diameter_px}px")
        except Exception as e:
            if DEBUG_RENDERER: print(f"[Renderer.__init__] Error loading/scaling ball image: {e}. Creating fallback.")
            # Fallback 球的尺寸也應縮放
            fallback_diameter = max(1, int(20 * self.game_content_scale_factor))
            self.ball_image = pygame.Surface((fallback_diameter, fallback_diameter), pygame.SRCALPHA)
            pygame.draw.circle(self.ball_image, (255, 255, 255), (fallback_diameter // 2, fallback_diameter // 2), fallback_diameter // 2)
        
        # self.ball_image_original_unscaled 已不需要，因為我們有 _ball_image_original_loaded
        # SoulEaterBugSkill 需要訪問 _ball_image_original_loaded 來恢復並正確縮放

        self.ball_angle = 0
        self.skill_glow_position = 0; self.skill_glow_trail = []; self.max_skill_glow_trail_length = 15
        if DEBUG_RENDERER: print("[Renderer.__init__] Renderer initialization complete with scaling parameters.")


    def _draw_walls(self, target_surface, game_area_on_surface_rect, color=(100,100,100)):
        """
        在 target_surface 的 game_area_on_surface_rect 區域內繪製牆壁。
        game_area_on_surface_rect 是牆壁所包圍的遊戲區域在 target_surface 上的【實際像素】Rect。
        """
        s = self.game_content_scale_factor
        scaled_thickness = max(1, int(2 * s)) # 縮放後的牆壁厚度

        left_wall_x = game_area_on_surface_rect.left + scaled_thickness // 2
        right_wall_x = game_area_on_surface_rect.right - scaled_thickness // 2
        wall_top_y = game_area_on_surface_rect.top
        wall_bottom_y = game_area_on_surface_rect.bottom

        pygame.draw.line(target_surface, color, (left_wall_x, wall_top_y), (left_wall_x, wall_bottom_y), scaled_thickness)
        pygame.draw.line(target_surface, color, (right_wall_x, wall_top_y), (right_wall_x, wall_bottom_y), scaled_thickness)

    def _render_player_view(self,
                            target_surface_for_view, # 通常是 self.window
                            view_player_state,
                            opponent_state_for_this_view,
                            game_render_area_on_target, # pygame.Rect, 遊戲邏輯區域在 target_surface_for_view 上的【實際縮放後像素】位置和大小
                            is_top_player_perspective=False):
        
        s = self.game_content_scale_factor # 使用 Renderer 統一的遊戲內容縮放因子

        # game_render_area_on_target 的 .x, .y, .width, .height 就是繪圖的像素基準
        ga_left = game_render_area_on_target.left
        ga_top = game_render_area_on_target.top
        ga_width_scaled = game_render_area_on_target.width
        ga_height_scaled = game_render_area_on_target.height

        # 1. 繪製牆壁 (在 game_render_area_on_target 內部)
        self._draw_walls(target_surface_for_view, game_render_area_on_target)

        # 2. 技能渲染
        if view_player_state.skill_instance:
            skill_should_render = view_player_state.skill_instance.is_active() or \
                                  (hasattr(view_player_state.skill_instance, 'fadeout_active') and view_player_state.skill_instance.fadeout_active) or \
                                  (hasattr(view_player_state.skill_instance, 'fog_active') and view_player_state.skill_instance.fog_active)
            if skill_should_render:
                # ⭐️ 技能渲染也需要知道縮放因子和其遊戲區域的實際繪圖位置
                # ⭐️ 理想情況：skill.render(target_surface_for_view, game_render_area_on_target, s)
                # ⭐️ SlowMoSkill 的 render 方法需要修改以接收並使用這些參數
                if hasattr(view_player_state.skill_instance, 'set_render_context'): # 如果技能有這個方法
                     view_player_state.skill_instance.set_render_context(game_render_area_on_target, s, self.offset_y) # self.offset_y 是縮放後的頂部UI高度(PvA)
                view_player_state.skill_instance.render(target_surface_for_view)


        # 3. 繪製主要遊戲元素
        try:
            ball_norm_x, ball_norm_y_raw = self.env.ball_x, self.env.ball_y
            ball_norm_y_for_view = 1.0 - ball_norm_y_raw if is_top_player_perspective else ball_norm_y_raw
            
            ball_center_x_scaled = ga_left + int(ball_norm_x * ga_width_scaled)
            ball_center_y_scaled = ga_top + int(ball_norm_y_for_view * ga_height_scaled)

            vp_paddle_norm_x = view_player_state.x
            vp_paddle_center_x_scaled = ga_left + int(vp_paddle_norm_x * ga_width_scaled)
            
            # 球拍的邏輯寬高乘以縮放因子
            vp_paddle_width_scaled = int(view_player_state.paddle_width * s) # paddle_width 是邏輯像素
            vp_paddle_height_scaled = int(self.env.paddle_height_px * s)  # paddle_height_px 是邏輯像素
            vp_paddle_color = view_player_state.paddle_color if view_player_state.paddle_color else Style.PLAYER_COLOR
            scaled_paddle_border_radius = max(1, int(3 * s))

            pygame.draw.rect(target_surface_for_view, vp_paddle_color,
                (vp_paddle_center_x_scaled - vp_paddle_width_scaled // 2,
                 ga_top + ga_height_scaled - vp_paddle_height_scaled,
                 vp_paddle_width_scaled, vp_paddle_height_scaled), border_radius=scaled_paddle_border_radius)

            opp_paddle_norm_x = opponent_state_for_this_view.x
            opp_paddle_center_x_scaled = ga_left + int(opp_paddle_norm_x * ga_width_scaled)
            opp_paddle_width_scaled = int(opponent_state_for_this_view.paddle_width * s)
            opp_paddle_height_scaled = int(self.env.paddle_height_px * s)
            opp_paddle_color = opponent_state_for_this_view.paddle_color if opponent_state_for_this_view.paddle_color else Style.AI_COLOR

            pygame.draw.rect(target_surface_for_view, opp_paddle_color,
                (opp_paddle_center_x_scaled - opp_paddle_width_scaled // 2,
                 ga_top,
                 opp_paddle_width_scaled, opp_paddle_height_scaled), border_radius=scaled_paddle_border_radius)

            if self.env.trail:
                scaled_trail_radius = max(1, int(self.env.ball_radius_px * 0.4 * s))
                for i, (tx_norm, ty_norm_raw) in enumerate(self.env.trail):
                    trail_ty_norm_for_view = 1.0 - ty_norm_raw if is_top_player_perspective else ty_norm_raw
                    fade = int(200 * (i + 1) / len(self.env.trail))
                    base_ball_color_rgb = Style.BALL_COLOR[:3] if isinstance(Style.BALL_COLOR, tuple) and len(Style.BALL_COLOR) >=3 else (255,255,255)
                    trail_color_with_alpha = (*base_ball_color_rgb, fade)
                    
                    temp_surf = pygame.Surface((scaled_trail_radius * 2, scaled_trail_radius * 2), pygame.SRCALPHA)
                    pygame.draw.circle(temp_surf, trail_color_with_alpha, (scaled_trail_radius, scaled_trail_radius), scaled_trail_radius)
                    
                    trail_x_scaled = ga_left + int(tx_norm * ga_width_scaled)
                    trail_y_scaled = ga_top + int(trail_ty_norm_for_view * ga_height_scaled)
                    target_surface_for_view.blit(temp_surf, (trail_x_scaled - scaled_trail_radius, trail_y_scaled - scaled_trail_radius))
            
            current_ball_render_image_scaled = self.ball_image # self.ball_image 已在 __init__ 中縮放
            ball_spin_for_view = -self.env.spin if is_top_player_perspective else self.env.spin
            self.ball_angle = (self.ball_angle + ball_spin_for_view * 10) % 360
            
            rotated_ball = pygame.transform.rotate(current_ball_render_image_scaled, self.ball_angle)
            ball_rect = rotated_ball.get_rect(center=(ball_center_x_scaled, ball_center_y_scaled))
            target_surface_for_view.blit(rotated_ball, ball_rect)

        except Exception as e:
             if DEBUG_RENDERER: print(f"[Renderer._render_player_view] ({view_player_state.identifier}) drawing error: {e}")
             import traceback; traceback.print_exc()


    def render(self):
        if not self.env or not self.window : return
        current_time_ticks = pygame.time.get_ticks()
        freeze_active = (self.env.freeze_timer > 0 and (current_time_ticks - self.env.freeze_timer < self.env.freeze_duration))
        
        current_bg_color = Style.BACKGROUND_COLOR
        if freeze_active:
            current_bg_color = (200,200,200) if (current_time_ticks // 150) % 2 == 0 else (50,50,50)
        self.window.fill(current_bg_color) # 填充整個全螢幕

        # UI 條的背景顏色
        bg_r, bg_g, bg_b = Style.BACKGROUND_COLOR[:3] if isinstance(Style.BACKGROUND_COLOR, tuple) and len(Style.BACKGROUND_COLOR) >=3 else (0,0,0)
        ui_overlay_color = tuple(max(0, c - 20) for c in (bg_r, bg_g, bg_b))

        if self.game_mode == GameSettings.GameMode.PLAYER_VS_PLAYER:
            # PvP 模式下，_render_player_view 使用 self.viewport1_game_area_on_screen 等
            self._render_player_view(self.window, self.env.player1, self.env.opponent,
                                     self.viewport1_game_area_on_screen, is_top_player_perspective=False)
            self._render_player_view(self.window, self.env.opponent, self.env.player1,
                                     self.viewport2_game_area_on_screen, is_top_player_perspective=True)
            
            # 繪製底部共享 UI (使用縮放後的 Rect)
            self._render_pvp_bottom_ui(self.window, self.env.player1, self.env.opponent, self.pvp_shared_bottom_ui_rect_on_screen)
            
            # 繪製中間分割線 (在縮放後的視口之間)
            scaled_divider_thickness = max(1, int(2 * self.game_content_scale_factor))
            divider_x_abs = self.viewport1_game_area_on_screen.right + (self.viewport2_game_area_on_screen.left - self.viewport1_game_area_on_screen.right) // 2 # 兩個遊戲區中間
            pygame.draw.line(self.window, (80,80,80),
                               (divider_x_abs, self.viewport1_game_area_on_screen.top),
                               (divider_x_abs, self.viewport1_game_area_on_screen.bottom),
                               scaled_divider_thickness)
        else: # PvA
            pygame.draw.rect(self.window, ui_overlay_color, self.pva_top_ui_rect_on_screen)
            pygame.draw.rect(self.window, ui_overlay_color, self.pva_bottom_ui_rect_on_screen)

            self._render_player_view(self.window, self.env.player1, self.env.opponent,
                                     self.game_area_rect_on_screen, is_top_player_perspective=False)
            
            self._render_health_bar_for_pva(self.env.player1, is_opponent=False)
            self._render_health_bar_for_pva(self.env.opponent, is_opponent=True)
            self._render_skill_ui_for_pva(self.env.player1)

        pygame.display.flip()
        self.clock.tick(60)

    def _render_pvp_bottom_ui(self, target_surface, player1_state, player2_state, scaled_ui_rect):
        s = self.game_content_scale_factor
        ui_bg_color = Style.UI_BACKGROUND_COLOR if hasattr(Style, 'UI_BACKGROUND_COLOR') else (30,30,30)
        pygame.draw.rect(target_surface, ui_bg_color, scaled_ui_rect)

        scaled_bar_w = int(150 * s) # 邏輯寬度 150
        scaled_bar_h = int(15 * s)  # 邏輯高度 15
        scaled_skill_bar_w = int(100 * s)
        scaled_skill_bar_h = int(8 * s)
        scaled_spacing = int(10 * s)
        scaled_text_font_size = int(14 * s)
        text_font = Style.get_font(scaled_text_font_size)
        scaled_border_radius = max(1, int(2*s))

        # P1 UI (在共享條的左側)
        p1_base_x = scaled_ui_rect.left + scaled_spacing * 2
        p1_ui_y_center = scaled_ui_rect.centery # P1 UI元素的垂直中心線

        p1_label_surf = text_font.render("P1", True, Style.PLAYER_COLOR)
        # 調整標籤位置使其在血條的左上方或左中方
        p1_label_rect = p1_label_surf.get_rect(
            midright=(p1_base_x - scaled_spacing / 2, p1_ui_y_center - scaled_bar_h / 2 - scaled_skill_bar_h / 2 - scaled_spacing / 2) # 嘗試更精確的定位
        )
        # 或者一個更簡單的，相對於血條的位置
        # p1_label_rect = p1_label_surf.get_rect(midright=(p1_base_x - scaled_spacing, p1_ui_y_center - scaled_bar_h)) # 示例：血條左上

        target_surface.blit(p1_label_surf, p1_label_rect)

        p1_health_bar_y = p1_ui_y_center - scaled_bar_h - scaled_spacing // 4 # 血條在中心線偏上
        pygame.draw.rect(target_surface, Style.PLAYER_BAR_BG, (p1_base_x, p1_health_bar_y, scaled_bar_w, scaled_bar_h), border_radius=scaled_border_radius)
        p1_life_ratio = player1_state.lives / player1_state.max_lives if player1_state.max_lives > 0 else 0
        pygame.draw.rect(target_surface, Style.PLAYER_BAR_FILL, (p1_base_x, p1_health_bar_y, int(scaled_bar_w * p1_life_ratio), scaled_bar_h), border_radius=scaled_border_radius)
        
        p1_skill_y = p1_ui_y_center + scaled_spacing // 4 # 技能條在中心線偏下
        if player1_state.skill_instance:
            self._render_single_skill_bar(target_surface, player1_state, text_font, p1_base_x, p1_skill_y, scaled_skill_bar_w, scaled_skill_bar_h, s)

        # P2 UI (在共享條的右側)
        p2_base_end_x = scaled_ui_rect.right - scaled_spacing * 2
        p2_ui_x_health_bar_start = p2_base_end_x - scaled_bar_w
        
        # ⭐️⭐️⭐️ 定義 p2_ui_y_center ⭐️⭐️⭐️
        p2_ui_y_center = scaled_ui_rect.centery # P2 UI元素的垂直中心線，與P1相同

        p2_label_surf = text_font.render("P2", True, Style.AI_COLOR) # 使用AI顏色或P2專用色
        # 調整P2標籤位置
        p2_label_rect = p2_label_surf.get_rect(
            midleft=(p2_base_end_x + scaled_spacing / 2, p2_ui_y_center - scaled_bar_h / 2 - scaled_skill_bar_h / 2 - scaled_spacing / 2)
        )
        # 或者一個更簡單的，相對於血條的位置
        # p2_label_rect = p2_label_surf.get_rect(midleft=(p2_ui_x_health_bar_start + scaled_bar_w + scaled_spacing, p2_ui_y_center - scaled_bar_h)) # 示例：血條右上

        target_surface.blit(p2_label_surf, p2_label_rect)
        
        # P2 血條 Y軸與P1對齊 (或者使用 p2_ui_y_center 計算)
        p2_health_bar_y = p2_ui_y_center - scaled_bar_h - scaled_spacing // 4 # 與P1的計算方式相同
        pygame.draw.rect(target_surface, Style.AI_BAR_BG, (p2_ui_x_health_bar_start, p2_health_bar_y, scaled_bar_w, scaled_bar_h), border_radius=scaled_border_radius)
        p2_life_ratio = player2_state.lives / player2_state.max_lives if player2_state.max_lives > 0 else 0
        pygame.draw.rect(target_surface, Style.AI_BAR_FILL, (p2_ui_x_health_bar_start, p2_health_bar_y, int(scaled_bar_w * p2_life_ratio), scaled_bar_h), border_radius=scaled_border_radius)
        
        # P2 技能條 Y軸與P1對齊 (或者使用 p2_ui_y_center 計算)
        p2_skill_y = p2_ui_y_center + scaled_spacing // 4 # 與P1的計算方式相同
        if player2_state.skill_instance:
            p2_skill_x = p2_ui_x_health_bar_start + (scaled_bar_w - scaled_skill_bar_w) // 2 # 技能條在血條下方居中對齊
            self._render_single_skill_bar(target_surface, player2_state, text_font, p2_skill_x, p2_skill_y, scaled_skill_bar_w, scaled_skill_bar_h, s)

    def _render_single_skill_bar(self, surface, player_state, font, x, y, width_scaled, height_scaled, scale_factor):
        skill = player_state.skill_instance
        text_offset_x_scaled = int(5 * scale_factor) # 文字在條右側的偏移
        scaled_border_radius = max(1, int(2*scale_factor))
        
        skill_cfg = SKILL_CONFIGS.get(player_state.skill_code_name, {})
        bar_fill_color_rgb = skill_cfg.get("bar_color", (200, 200, 200))
        bar_bg_color_rgb = (50,50,50)
        
        pygame.draw.rect(surface, bar_bg_color_rgb, (x, y, width_scaled, height_scaled), border_radius=scaled_border_radius)
        energy_ratio = skill.get_energy_ratio()
        current_bar_width_scaled = int(width_scaled * energy_ratio)
        pygame.draw.rect(surface, bar_fill_color_rgb, (x, y, current_bar_width_scaled, height_scaled), border_radius=scaled_border_radius)
        
        display_text = ""
        text_color = Style.TEXT_COLOR
        if skill.is_active():
            display_text = f"{player_state.skill_code_name.upper()}!"
            text_color = bar_fill_color_rgb
        elif skill.get_cooldown_seconds() > 0:
            display_text = f"{skill.get_cooldown_seconds():.1f}s"
        else:
            display_text = "RDY" # 縮短文字以適應空間
            text_color = (200, 255, 200)

        if display_text:
            text_surf = font.render(display_text, True, text_color)
            text_rect = text_surf.get_rect(midleft=(x + width_scaled + text_offset_x_scaled, y + height_scaled / 2))
            surface.blit(text_surf, text_rect)

    def _render_health_bar_for_pva(self, player_state, is_opponent):
        s = self.game_content_scale_factor
        # 使用縮放後的UI條Rect來定位
        target_ui_bar_rect = self.pva_top_ui_rect_on_screen if is_opponent else self.pva_bottom_ui_rect_on_screen

        scaled_bar_w = int(self.logical_game_area_size * 0.35 * s) # 血條寬度為遊戲區域邏輯寬的35%，再縮放
        scaled_bar_h = int(15 * s) # 邏輯高度15
        scaled_spacing = int(20 * s)
        scaled_text_font_size = int(14 * s)
        font = Style.get_font(scaled_text_font_size)
        scaled_border_radius = max(1, int(2*s))

        bar_bg_color = Style.AI_BAR_BG if is_opponent else Style.PLAYER_BAR_BG
        bar_fill_color = Style.AI_BAR_FILL if is_opponent else Style.PLAYER_BAR_FILL
        label_text = "AI" if is_opponent else "P1"
        label_color = Style.AI_COLOR if is_opponent else Style.PLAYER_COLOR
        label_surf = font.render(label_text, True, label_color)
        life_ratio = player_state.lives / player_state.max_lives if player_state.max_lives > 0 else 0

        bar_y = target_ui_bar_rect.top + (target_ui_bar_rect.height - scaled_bar_h) // 2 # 垂直居中於UI條

        if is_opponent: # AI 在頂部右側
            bar_x = target_ui_bar_rect.right - scaled_bar_w - scaled_spacing
            label_rect = label_surf.get_rect(midright=(bar_x - int(10*s), bar_y + scaled_bar_h / 2))
        else: # P1 在底部左側
            bar_x = target_ui_bar_rect.left + scaled_spacing
            label_rect = label_surf.get_rect(midleft=(bar_x + scaled_bar_w + int(10*s), bar_y + scaled_bar_h / 2))

        pygame.draw.rect(self.window, bar_bg_color, (bar_x, bar_y, scaled_bar_w, scaled_bar_h), border_radius=scaled_border_radius)
        pygame.draw.rect(self.window, bar_fill_color, (bar_x, bar_y, int(scaled_bar_w * life_ratio), scaled_bar_h), border_radius=scaled_border_radius)
        self.window.blit(label_surf, label_rect)


    def _render_skill_ui_for_pva(self, player_state):
        if not player_state.skill_instance: return
        s = self.game_content_scale_factor
        target_ui_bar_rect = self.pva_bottom_ui_rect_on_screen # 技能條在底部UI

        # 假設血條在左，技能條在其右
        scaled_health_bar_w = int(self.logical_game_area_size * 0.35 * s)
        scaled_spacing_from_edge = int(20 * s)
        scaled_spacing_between = int(15 * s)
        scaled_skill_bar_w = int(self.logical_game_area_size * 0.25 * s)
        scaled_skill_bar_h = int(10 * s)
        scaled_text_font_size = int(12 * s)
        font = Style.get_font(scaled_text_font_size)

        skill_bar_x = target_ui_bar_rect.left + scaled_spacing_from_edge + scaled_health_bar_w + scaled_spacing_between
        skill_bar_y = target_ui_bar_rect.top + (target_ui_bar_rect.height - scaled_skill_bar_h) // 2
        
        self._render_single_skill_bar(self.window, player_state, font, skill_bar_x, skill_bar_y, scaled_skill_bar_w, scaled_skill_bar_h, s)

    def close(self):
        if DEBUG_RENDERER: print("[Renderer.close] Closing Renderer.")
        # No pygame.quit() here