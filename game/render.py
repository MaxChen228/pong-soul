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
    def __init__(self, 
                game_mode, 
                logical_game_area_size,
                logical_ball_radius_px,
                logical_paddle_height_px, # 新增：Renderer 需要知道球拍的邏輯高度
                actual_screen_surface, 
                actual_screen_width, 
                actual_screen_height):
        if DEBUG_RENDERER: print(f"[Renderer.__init__] Initializing Renderer for game_mode: {game_mode}")
        if DEBUG_RENDERER_FULLSCREEN:
            print(f"[DEBUG_RENDERER_FULLSCREEN][Renderer.__init__] Received actual_screen_surface: {type(actual_screen_surface)}")
            if actual_screen_surface:
                print(f"    Surface size: {actual_screen_surface.get_size()}, Expected: {actual_screen_width}x{actual_screen_height}")

        # self.env = env # 不再儲存 env 的引用
        self.game_mode = game_mode
        self.logical_game_area_size = logical_game_area_size # 純遊戲區域的邏輯尺寸 (e.g., 400x400)

        # 儲存球和球拍的邏輯像素尺寸，用於繪圖計算
        self.logical_ball_radius_px = logical_ball_radius_px
        self.logical_paddle_height_px = logical_paddle_height_px


        if actual_screen_surface:
            self.window = actual_screen_surface
            self.actual_screen_width = actual_screen_width
            self.actual_screen_height = actual_screen_height
        else: 
            if DEBUG_RENDERER_FULLSCREEN: print(f"[DEBUG_RENDERER_FULLSCREEN][Renderer.__init__] No surface! Fallback window (breaks fullscreen).")
            self.actual_screen_width, self.actual_screen_height = 1000, 700
            try:
                self.window = pygame.display.set_mode((self.actual_screen_width, self.actual_screen_height))
                pygame.display.set_caption("Pong Soul - Renderer Fallback")
            except pygame.error as e:
                raise RuntimeError(f"Renderer could not establish a drawing surface: {e}")

        if self.game_mode == GameSettings.GameMode.PLAYER_VS_PLAYER:
            self.logical_pvp_game_area_width_per_viewport = self.logical_game_area_size 
            self.logical_pvp_viewport_width = 500 
            self.logical_layout_width = self.logical_pvp_viewport_width * 2
            self.logical_pvp_game_area_height = self.logical_game_area_size 
            self.logical_pvp_shared_ui_height = 100 
            self.logical_layout_height = self.logical_pvp_game_area_height + self.logical_pvp_shared_ui_height
        else: # PvA
            self.logical_layout_width = self.logical_game_area_size 
            self.logical_pva_ui_bar_height = 100 
            self.logical_layout_height = self.logical_game_area_size + 2 * self.logical_pva_ui_bar_height

        if DEBUG_RENDERER_FULLSCREEN:
            print(f"[DEBUG_RENDERER_FULLSCREEN][Renderer.__init__] Game Mode: {self.game_mode}")
            print(f"    Logical Game Area Size (env.render_size): {self.logical_game_area_size}x{self.logical_game_area_size}")
            print(f"    Renderer Logical Layout: {self.logical_layout_width}x{self.logical_layout_height}")

        scale_x = self.actual_screen_width / self.logical_layout_width
        scale_y = self.actual_screen_height / self.logical_layout_height
        self.game_content_scale_factor = min(scale_x, scale_y) 
        self.scaled_layout_width = int(self.logical_layout_width * self.game_content_scale_factor)
        self.scaled_layout_height = int(self.logical_layout_height * self.game_content_scale_factor)
        self.layout_offset_x = (self.actual_screen_width - self.scaled_layout_width) // 2
        self.layout_offset_y = (self.actual_screen_height - self.scaled_layout_height) // 2
        self.game_content_render_area_on_screen = pygame.Rect(
            self.layout_offset_x, self.layout_offset_y,
            self.scaled_layout_width, self.scaled_layout_height
        )
        self.scale_factor_for_game = self.game_content_scale_factor 

        if DEBUG_RENDERER_FULLSCREEN:
            print(f"[DEBUG_RENDERER_FULLSCREEN][Renderer.__init__] Game Content Scaling:")
            print(f"    Scale Factor: {self.game_content_scale_factor:.4f}")
            print(f"    Scaled Layout Size: {self.scaled_layout_width}x{self.scaled_layout_height}")
            print(f"    Layout Offset (Centering): ({self.layout_offset_x}, {self.layout_offset_y})")
            print(f"    Game Content Render Area on Screen: {self.game_content_render_area_on_screen}")

        s = self.game_content_scale_factor 
        area_left = self.game_content_render_area_on_screen.left
        area_top = self.game_content_render_area_on_screen.top

        if self.game_mode == GameSettings.GameMode.PLAYER_VS_PLAYER:
            scaled_pvp_viewport_width = int(self.logical_pvp_viewport_width * s)
            scaled_pvp_game_area_height = int(self.logical_pvp_game_area_height * s) 
            scaled_pvp_shared_ui_height = int(self.logical_pvp_shared_ui_height * s)
            vp1_left = area_left
            vp1_top = area_top
            self.viewport1_game_area_on_screen = pygame.Rect( 
                vp1_left + (scaled_pvp_viewport_width - int(self.logical_game_area_size * s)) // 2, 
                vp1_top,  
                int(self.logical_game_area_size * s),     
                scaled_pvp_game_area_height               
            )
            vp2_left = area_left + scaled_pvp_viewport_width
            vp2_top = area_top
            self.viewport2_game_area_on_screen = pygame.Rect( 
                vp2_left + (scaled_pvp_viewport_width - int(self.logical_game_area_size * s)) // 2,
                vp2_top,
                int(self.logical_game_area_size * s),
                scaled_pvp_game_area_height
            )
            self.pvp_shared_bottom_ui_rect_on_screen = pygame.Rect(
                area_left, 
                area_top + scaled_pvp_game_area_height, 
                self.scaled_layout_width, 
                scaled_pvp_shared_ui_height
            )
            self.offset_y = 0 

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
            self.game_area_rect_on_screen = pygame.Rect( 
                area_left, 
                area_top + scaled_pva_ui_bar_height, 
                scaled_logical_game_area_size, 
                scaled_logical_game_area_size  
            )
            self.pva_bottom_ui_rect_on_screen = pygame.Rect(
                area_left, area_top + scaled_pva_ui_bar_height + scaled_logical_game_area_size,
                self.scaled_layout_width, scaled_pva_ui_bar_height
            )
            self.offset_y = scaled_pva_ui_bar_height 

            if DEBUG_RENDERER_FULLSCREEN:
                print(f"    PvA Scaled UI Bar Height: {scaled_pva_ui_bar_height}")
                print(f"    PvA Scaled Game Area Size: {scaled_logical_game_area_size}x{scaled_logical_game_area_size}")
                print(f"    PvA Top UI Rect on Screen: {self.pva_top_ui_rect_on_screen}")
                print(f"    PvA Game Area Rect on Screen: {self.game_area_rect_on_screen}")
                print(f"    PvA Bottom UI Rect on Screen: {self.pva_bottom_ui_rect_on_screen}")
                print(f"    PvA self.offset_y (scaled top bar for skills): {self.offset_y}")

        self.clock = pygame.time.Clock()
        try:
            # 球的圖像尺寸基於縮放後的邏輯球半徑
            # self.logical_ball_radius_px 是在 __init__ 中從 PongDuelEnv 獲取的
            scaled_ball_diameter_px = int(self.logical_ball_radius_px * 2 * self.game_content_scale_factor)
            if scaled_ball_diameter_px <= 0: scaled_ball_diameter_px = max(1, int(20 * self.game_content_scale_factor))

            if not hasattr(Renderer, '_ball_image_original_loaded'): # 靜態變數，確保只加載一次
                Renderer._ball_image_original_loaded = pygame.image.load(resource_path("assets/sunglasses.png")).convert_alpha()

            self.ball_image = pygame.transform.smoothscale(Renderer._ball_image_original_loaded, (scaled_ball_diameter_px, scaled_ball_diameter_px))
            # ⭐️ SoulEaterBugSkill 更換圖像時，也需要用 game_content_scale_factor 縮放蟲子圖像
            #    它會直接修改 self.ball_image，所以其內部也需要知道這個縮放因子，或者 Renderer 提供一個方法來設定球的圖像（並處理縮放）
            if DEBUG_RENDERER_FULLSCREEN:
                print(f"[DEBUG_RENDERER_FULLSCREEN][Renderer.__init__] Ball image scaled to diameter: {scaled_ball_diameter_px}px")
        except Exception as e:
            if DEBUG_RENDERER: print(f"[Renderer.__init__] Error loading/scaling ball image: {e}. Creating fallback.")
            fallback_diameter = max(1, int(20 * self.game_content_scale_factor))
            self.ball_image = pygame.Surface((fallback_diameter, fallback_diameter), pygame.SRCALPHA)
            pygame.draw.circle(self.ball_image, (255, 255, 255), (fallback_diameter // 2, fallback_diameter // 2), fallback_diameter // 2)

        self.ball_angle = 0 # 球的旋轉角度由 Renderer 維護
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
                            target_surface_for_view, 
                            view_player_data, # 數據包，例如 render_data["player1"]
                            opponent_data_for_this_view, # 數據包
                            ball_data, # 數據包
                            trail_data, # 列表
                            paddle_height_norm, # 浮點數
                            ball_spin, # 浮點數 (來自 ball_data["spin"])
                            game_render_area_on_target, 
                            is_top_player_perspective=False):

        s = self.game_content_scale_factor 
        ga_left = game_render_area_on_target.left
        ga_top = game_render_area_on_target.top
        ga_width_scaled = game_render_area_on_target.width
        ga_height_scaled = game_render_area_on_target.height

        self._draw_walls(target_surface_for_view, game_render_area_on_target)

        # 技能渲染 (從傳入的 view_player_data 中獲取技能實例)
        # 假設：PongDuelEnv.get_render_data() 在 player1_skill_data/opponent_skill_data 中
        # 仍然會包含一個 'instance': self.player1.skill_instance 的鍵值對，
        # 或者 Renderer 不再直接調用 skill_instance.render()，而是根據 skill_data 中的參數繪製。
        # 為了最小化此階段的改動，我們假設 skill_instance 仍然需要被傳遞，
        # 並且其 render 方法仍在此處調用。
        # 這意味著 PongDuelEnv.get_render_data() 需要傳遞 skill_instance。

        # --- 技能渲染的調整 ---
        # 我們需要從 view_player_data 中獲取 skill_instance
        # 這需要在 PongDuelEnv.get_render_data() 中做出相應修改：
        # playerX_skill_data 字典中應該有一個 'instance': player_state.skill_instance
        skill_instance_to_render = None
        if view_player_data and view_player_data.get("skill_data") and view_player_data["skill_data"].get("instance"):
            skill_instance_to_render = view_player_data["skill_data"]["instance"]

        if skill_instance_to_render:
            skill_should_render = skill_instance_to_render.is_active() or \
                                (hasattr(skill_instance_to_render, 'fadeout_active') and skill_instance_to_render.fadeout_active) or \
                                (hasattr(skill_instance_to_render, 'fog_active') and skill_instance_to_render.fog_active)

            if skill_should_render:
                # view_player_data.identifier 是視角擁有者的標識符
                # skill_instance_to_render.owner.identifier 是技能實際擁有者的標識符
                # 只有當視角擁有者就是技能擁有者時才渲染
                if view_player_data.get("identifier") == skill_instance_to_render.owner.identifier:
                    try:
                        skill_instance_to_render.render(
                            target_surface_for_view,      
                            game_render_area_on_target,   
                            s,                            
                            True # 在擁有者的視角中，擁有者總是在底部                         
                        )
                    except TypeError as e:
                        if "render() takes" in str(e) and ("but 5 were given" in str(e) or "missing 1 required positional argument: 'is_owner_bottom_perspective_in_this_area'" in str(e)):
                            if DEBUG_RENDERER:
                                print(f"[DEBUG_RENDERER] Skill '{skill_instance_to_render.__class__.__name__}' for {view_player_data.get('identifier', 'UnknownPlayer')} "
                                    f"does not have an updated render(surface, game_area, scale, is_bottom_persp) method yet. Skipping.")
                        else:
                            if DEBUG_RENDERER: print(f"[DEBUG_RENDERER] Error calling skill.render for {view_player_data.get('identifier', 'UnknownPlayer')}: {e}")
                            import traceback; traceback.print_exc()
                    except Exception as e:
                        if DEBUG_RENDERER: print(f"[DEBUG_RENDERER] Unexpected error calling skill.render for {view_player_data.get('identifier', 'UnknownPlayer')}: {e}")
                        import traceback; traceback.print_exc()
        # --- 技能渲染調整結束 ---

        try:
            ball_norm_x = ball_data["x_norm"]
            ball_norm_y_raw = ball_data["y_norm"]
            ball_norm_y_for_view = 1.0 - ball_norm_y_raw if is_top_player_perspective else ball_norm_y_raw

            ball_center_x_scaled = ga_left + int(ball_norm_x * ga_width_scaled)
            ball_center_y_scaled = ga_top + int(ball_norm_y_for_view * ga_height_scaled)

            # 視角主角的球拍 (總是在底部)
            vp_paddle_norm_x = view_player_data["x_norm"]
            vp_paddle_center_x_scaled = ga_left + int(vp_paddle_norm_x * ga_width_scaled)
            vp_paddle_width_scaled = int(view_player_data["paddle_width_norm"] * self.logical_game_area_size * s) # 從 norm 轉換回邏輯再縮放
            vp_paddle_height_scaled = int(self.logical_paddle_height_px * s) 
            vp_paddle_color = view_player_data.get("paddle_color", Style.PLAYER_COLOR) 
            scaled_paddle_border_radius = max(1, int(3 * s))

            pygame.draw.rect(target_surface_for_view, vp_paddle_color,
                (vp_paddle_center_x_scaled - vp_paddle_width_scaled // 2,
                ga_top + ga_height_scaled - vp_paddle_height_scaled, # 底部
                vp_paddle_width_scaled, vp_paddle_height_scaled), border_radius=scaled_paddle_border_radius)

            # 此視角的對手球拍 (總是在頂部)
            opp_paddle_norm_x = opponent_data_for_this_view["x_norm"]
            opp_paddle_center_x_scaled = ga_left + int(opp_paddle_norm_x * ga_width_scaled)
            opp_paddle_width_scaled = int(opponent_data_for_this_view["paddle_width_norm"] * self.logical_game_area_size * s)
            opp_paddle_height_scaled = int(self.logical_paddle_height_px * s)
            opp_paddle_color = opponent_data_for_this_view.get("paddle_color", Style.AI_COLOR)

            pygame.draw.rect(target_surface_for_view, opp_paddle_color,
                (opp_paddle_center_x_scaled - opp_paddle_width_scaled // 2,
                ga_top, # 頂部
                opp_paddle_width_scaled, opp_paddle_height_scaled), border_radius=scaled_paddle_border_radius)

            # 拖尾效果
            if trail_data:
                # self.logical_ball_radius_px 是在 __init__ 中從 Env 獲取的球的邏輯半徑
                scaled_trail_radius = max(1, int(self.logical_ball_radius_px * 0.4 * s)) 
                for i, (tx_norm, ty_norm_raw) in enumerate(trail_data):
                    trail_ty_norm_for_view = 1.0 - ty_norm_raw if is_top_player_perspective else ty_norm_raw
                    fade = int(200 * (i + 1) / len(trail_data))
                    base_ball_color_rgb = Style.BALL_COLOR[:3] if isinstance(Style.BALL_COLOR, tuple) and len(Style.BALL_COLOR) >=3 else (255,255,255)
                    trail_color_with_alpha = (*base_ball_color_rgb, fade)

                    temp_surf = pygame.Surface((scaled_trail_radius * 2, scaled_trail_radius * 2), pygame.SRCALPHA)
                    pygame.draw.circle(temp_surf, trail_color_with_alpha, (scaled_trail_radius, scaled_trail_radius), scaled_trail_radius)

                    trail_x_scaled = ga_left + int(tx_norm * ga_width_scaled)
                    trail_y_scaled = ga_top + int(trail_ty_norm_for_view * ga_height_scaled)
                    target_surface_for_view.blit(temp_surf, (trail_x_scaled - scaled_trail_radius, trail_y_scaled - scaled_trail_radius))

            current_ball_render_image_scaled = self.ball_image 

            # 使用傳入的 ball_spin 更新 Renderer 內部的 ball_angle
            # PvP 模式下，對手的視角 (is_top_player_perspective=True)，球的旋轉方向看起來是相反的
            spin_for_this_view = -ball_spin if is_top_player_perspective else ball_spin
            self.ball_angle = (self.ball_angle + spin_for_this_view * 10) % 360 # 10 是旋轉速度因子

            rotated_ball = pygame.transform.rotate(current_ball_render_image_scaled, self.ball_angle)
            ball_rect = rotated_ball.get_rect(center=(ball_center_x_scaled, ball_center_y_scaled))
            target_surface_for_view.blit(rotated_ball, ball_rect)

        except Exception as e:
            player_id_for_debug = view_player_data.get("identifier", "UnknownPlayer")
            if DEBUG_RENDERER: print(f"[Renderer._render_player_view] ({player_id_for_debug}) drawing error: {e}")
            import traceback; traceback.print_exc()


    def render(self, render_data): # 接收 render_data
        if not self.window: return # 如果沒有繪圖表面，則不執行任何操作

        # 從 render_data 中獲取 freeze_active 狀態
        freeze_active = render_data.get("freeze_active", False)

        current_bg_color = Style.BACKGROUND_COLOR
        if freeze_active:
            # 背景閃爍效果
            current_time_ticks = pygame.time.get_ticks() # 需要 pygame.time.get_ticks()
            current_bg_color = (200,200,200) if (current_time_ticks // 150) % 2 == 0 else (50,50,50)
        self.window.fill(current_bg_color) 

        bg_r, bg_g, bg_b = Style.BACKGROUND_COLOR[:3] if isinstance(Style.BACKGROUND_COLOR, tuple) and len(Style.BACKGROUND_COLOR) >=3 else (0,0,0)
        ui_overlay_color = tuple(max(0, c - 20) for c in (bg_r, bg_g, bg_b))

        player1_data = render_data["player1"]
        opponent_data = render_data["opponent"]

        if self.game_mode == GameSettings.GameMode.PLAYER_VS_PLAYER:
            self._render_player_view(
                self.window, 
                player1_data, # 傳遞 player1 的數據包
                opponent_data, # 傳遞 opponent 的數據包
                render_data["ball"], # 傳遞球的數據包
                render_data["trail"], # 傳遞拖尾數據
                render_data["paddle_height_norm"], # 傳遞正規化球拍高度
                render_data["ball"]["spin"], # 傳遞球的自旋
                self.viewport1_game_area_on_screen, 
                is_top_player_perspective=False
            )
            self._render_player_view(
                self.window, 
                opponent_data, # 現在 opponent 是視角主角
                player1_data,  # player1 是這個視角的對手
                render_data["ball"],
                render_data["trail"],
                render_data["paddle_height_norm"],
                render_data["ball"]["spin"],
                self.viewport2_game_area_on_screen, 
                is_top_player_perspective=True # 對手 P2 在其視角是底部，但其世界座標是上方，所以球的Y需要反轉
            )

            self._render_pvp_bottom_ui(self.window, player1_data, opponent_data, self.pvp_shared_bottom_ui_rect_on_screen)

            scaled_divider_thickness = max(1, int(2 * self.game_content_scale_factor))
            divider_x_abs = self.viewport1_game_area_on_screen.right + (self.viewport2_game_area_on_screen.left - self.viewport1_game_area_on_screen.right) // 2
            pygame.draw.line(self.window, (80,80,80),
                            (divider_x_abs, self.viewport1_game_area_on_screen.top),
                            (divider_x_abs, self.viewport1_game_area_on_screen.bottom),
                            scaled_divider_thickness)
        else: # PvA
            pygame.draw.rect(self.window, ui_overlay_color, self.pva_top_ui_rect_on_screen)
            pygame.draw.rect(self.window, ui_overlay_color, self.pva_bottom_ui_rect_on_screen)

            self._render_player_view(
                self.window, 
                player1_data, 
                opponent_data, 
                render_data["ball"],
                render_data["trail"],
                render_data["paddle_height_norm"],
                render_data["ball"]["spin"],
                self.game_area_rect_on_screen, 
                is_top_player_perspective=False
            )

            self._render_health_bar_for_pva(player1_data, is_opponent=False)
            self._render_health_bar_for_pva(opponent_data, is_opponent=True)
            # 技能UI現在依賴 player_data 中的 skill_data
            self._render_skill_ui_for_pva(player1_data)

        # 技能的自訂渲染 (例如 SlowMoSkill 的衝擊波、時鐘等)
        # 這部分仍然需要 Renderer 能夠訪問技能實例，或者技能的視覺參數被包含在 render_data 中
        # 目前我們的 render_data 包含了 skill_data (code_name, is_active, energy_ratio, cooldown_seconds)
        # 但還沒有包含像 SlowMoSkill 這樣的技能的詳細視覺參數 (shockwaves, trail_positions)。
        # 我們需要決定這些參數是由 skill_instance.render() 自己畫，還是由 Env 收集後交給 Renderer 畫。
        # 暫時保留技能的 render 方法在 _render_player_view 中被調用，但它需要從 playerX_data 中獲取 skill_instance。
        # 這意味著 PlayerState 的 skill_instance 需要被正確傳遞。
        # 在 PongDuelEnv.get_render_data 中，我們已經將 skill_instance 包含在 playerX_skill_data 中 (雖然被註解掉了)
        # 為了讓技能的 render 繼續工作，PongDuelEnv.get_render_data 需要傳遞 skill_instance，
        # 或者 Renderer._render_player_view 中不再調用 skill_instance.render()，而是從 render_data 提取技能視覺參數。

        # 為了簡化此步驟，我們假設技能的 .render() 方法暫時仍由 _render_player_view 內部處理，
        # _render_player_view 會從傳入的 player_state_data 中獲取 skill_instance (如果存在)。
        # 所以，PongDuelEnv.get_render_data() 中的 player1_skill_data 和 opponent_skill_data 應該包含 skill_instance 本身。
        # (回顧 PongDuelEnv.get_render_data，它目前沒有傳遞 skill_instance，這需要修正)

        pygame.display.flip()
        self.clock.tick(60)

    def _render_pvp_bottom_ui(self, target_surface, player1_data, player2_data, scaled_ui_rect):
        s = self.game_content_scale_factor
        ui_bg_color = Style.UI_BACKGROUND_COLOR if hasattr(Style, 'UI_BACKGROUND_COLOR') else (30,30,30)
        pygame.draw.rect(target_surface, ui_bg_color, scaled_ui_rect)

        scaled_bar_w = int(150 * s) 
        scaled_bar_h = int(15 * s)  
        scaled_skill_bar_w = int(100 * s)
        scaled_skill_bar_h = int(8 * s)
        scaled_spacing = int(10 * s)
        scaled_text_font_size = int(14 * s)
        text_font = Style.get_font(scaled_text_font_size)
        scaled_border_radius = max(1, int(2*s))

        # P1 UI (在共享條的左側)
        p1_base_x = scaled_ui_rect.left + scaled_spacing * 2
        p1_ui_y_center = scaled_ui_rect.centery 

        p1_label_surf = text_font.render(player1_data.get("identifier", "P1").upper(), True, Style.PLAYER_COLOR)
        p1_label_rect = p1_label_surf.get_rect(
            midright=(p1_base_x - scaled_spacing / 2, p1_ui_y_center - scaled_bar_h / 2 - scaled_skill_bar_h / 2 - scaled_spacing / 2) 
        )
        target_surface.blit(p1_label_surf, p1_label_rect)

        p1_health_bar_y = p1_ui_y_center - scaled_bar_h - scaled_spacing // 4 
        pygame.draw.rect(target_surface, Style.PLAYER_BAR_BG, (p1_base_x, p1_health_bar_y, scaled_bar_w, scaled_bar_h), border_radius=scaled_border_radius)
        p1_max_lives = player1_data.get("max_lives", 1)
        p1_life_ratio = player1_data.get("lives", 0) / p1_max_lives if p1_max_lives > 0 else 0
        pygame.draw.rect(target_surface, Style.PLAYER_BAR_FILL, (p1_base_x, p1_health_bar_y, int(scaled_bar_w * p1_life_ratio), scaled_bar_h), border_radius=scaled_border_radius)

        p1_skill_y = p1_ui_y_center + scaled_spacing // 4 
        if player1_data.get("skill_data"):
            self._render_single_skill_bar(target_surface, player1_data["skill_data"], text_font, p1_base_x, p1_skill_y, scaled_skill_bar_w, scaled_skill_bar_h, s)

        # P2 UI (在共享條的右側)
        p2_base_end_x = scaled_ui_rect.right - scaled_spacing * 2
        p2_ui_x_health_bar_start = p2_base_end_x - scaled_bar_w
        p2_ui_y_center = scaled_ui_rect.centery 

        p2_label_surf = text_font.render(player2_data.get("identifier", "P2").upper(), True, Style.AI_COLOR) 
        p2_label_rect = p2_label_surf.get_rect(
            midleft=(p2_base_end_x + scaled_spacing / 2, p2_ui_y_center - scaled_bar_h / 2 - scaled_skill_bar_h / 2 - scaled_spacing / 2)
        )
        target_surface.blit(p2_label_surf, p2_label_rect)

        p2_health_bar_y = p2_ui_y_center - scaled_bar_h - scaled_spacing // 4 
        pygame.draw.rect(target_surface, Style.AI_BAR_BG, (p2_ui_x_health_bar_start, p2_health_bar_y, scaled_bar_w, scaled_bar_h), border_radius=scaled_border_radius)
        p2_max_lives = player2_data.get("max_lives", 1)
        p2_life_ratio = player2_data.get("lives", 0) / p2_max_lives if p2_max_lives > 0 else 0
        pygame.draw.rect(target_surface, Style.AI_BAR_FILL, (p2_ui_x_health_bar_start, p2_health_bar_y, int(scaled_bar_w * p2_life_ratio), scaled_bar_h), border_radius=scaled_border_radius)

        p2_skill_y = p2_ui_y_center + scaled_spacing // 4 
        if player2_data.get("skill_data"):
            p2_skill_x = p2_ui_x_health_bar_start + (scaled_bar_w - scaled_skill_bar_w) // 2 
            self._render_single_skill_bar(target_surface, player2_data["skill_data"], text_font, p2_skill_x, p2_skill_y, scaled_skill_bar_w, scaled_skill_bar_h, s)

    def _render_single_skill_bar(self, surface, skill_data, font, x, y, width_scaled, height_scaled, scale_factor):
        # skill_data is expected to be a dictionary like:
        # { "code_name": "slowmo", "is_active": False, "energy_ratio": 1.0, "cooldown_seconds": 0.0 }

        text_offset_x_scaled = int(5 * scale_factor) 
        scaled_border_radius = max(1, int(2*scale_factor))

        skill_code_name = skill_data.get("code_name", "unknown_skill")
        skill_cfg = SKILL_CONFIGS.get(skill_code_name, {})
        bar_fill_color_rgb = skill_cfg.get("bar_color", (200, 200, 200))
        bar_bg_color_rgb = (50,50,50)

        pygame.draw.rect(surface, bar_bg_color_rgb, (x, y, width_scaled, height_scaled), border_radius=scaled_border_radius)

        energy_ratio = skill_data.get("energy_ratio", 0.0)
        current_bar_width_scaled = int(width_scaled * energy_ratio)
        pygame.draw.rect(surface, bar_fill_color_rgb, (x, y, current_bar_width_scaled, height_scaled), border_radius=scaled_border_radius)

        display_text = ""
        text_color = Style.TEXT_COLOR
        is_active = skill_data.get("is_active", False)
        cooldown_seconds = skill_data.get("cooldown_seconds", 0.0)

        if is_active:
            display_text = f"{skill_code_name.upper()}!"
            text_color = bar_fill_color_rgb
        elif cooldown_seconds > 0:
            display_text = f"{cooldown_seconds:.1f}s"
        else:
            display_text = "RDY" 
            text_color = (200, 255, 200)

        if display_text:
            text_surf = font.render(display_text, True, text_color)
            text_rect = text_surf.get_rect(midleft=(x + width_scaled + text_offset_x_scaled, y + height_scaled / 2))
            surface.blit(text_surf, text_rect)

    def _render_health_bar_for_pva(self, player_data, is_opponent):
        # player_data is expected to be a dictionary like:
        # { "lives": 3, "max_lives": 3, "identifier": "P1" or "AI" }
        s = self.game_content_scale_factor
        target_ui_bar_rect = self.pva_top_ui_rect_on_screen if is_opponent else self.pva_bottom_ui_rect_on_screen

        scaled_bar_w = int(self.logical_game_area_size * 0.35 * s) 
        scaled_bar_h = int(15 * s) 
        scaled_spacing = int(20 * s)
        scaled_text_font_size = int(14 * s)
        font = Style.get_font(scaled_text_font_size)
        scaled_border_radius = max(1, int(2*s))

        bar_bg_color = Style.AI_BAR_BG if is_opponent else Style.PLAYER_BAR_BG
        bar_fill_color = Style.AI_BAR_FILL if is_opponent else Style.PLAYER_BAR_FILL

        default_label = "AI" if is_opponent else "P1"
        label_text = player_data.get("identifier", default_label).upper()
        label_color = Style.AI_COLOR if is_opponent else Style.PLAYER_COLOR
        label_surf = font.render(label_text, True, label_color)

        max_lives = player_data.get("max_lives", 1)
        life_ratio = player_data.get("lives", 0) / max_lives if max_lives > 0 else 0

        bar_y = target_ui_bar_rect.top + (target_ui_bar_rect.height - scaled_bar_h) // 2 

        if is_opponent: 
            bar_x = target_ui_bar_rect.right - scaled_bar_w - scaled_spacing
            label_rect = label_surf.get_rect(midright=(bar_x - int(10*s), bar_y + scaled_bar_h / 2))
        else: 
            bar_x = target_ui_bar_rect.left + scaled_spacing
            label_rect = label_surf.get_rect(midleft=(bar_x + scaled_bar_w + int(10*s), bar_y + scaled_bar_h / 2))

        pygame.draw.rect(self.window, bar_bg_color, (bar_x, bar_y, scaled_bar_w, scaled_bar_h), border_radius=scaled_border_radius)
        pygame.draw.rect(self.window, bar_fill_color, (bar_x, bar_y, int(scaled_bar_w * life_ratio), scaled_bar_h), border_radius=scaled_border_radius)
        self.window.blit(label_surf, label_rect)


    def _render_skill_ui_for_pva(self, player_data):
        # player_data is expected to contain a "skill_data" dictionary
        skill_data = player_data.get("skill_data")
        if not skill_data: return

        s = self.game_content_scale_factor
        target_ui_bar_rect = self.pva_bottom_ui_rect_on_screen 

        scaled_health_bar_w = int(self.logical_game_area_size * 0.35 * s)
        scaled_spacing_from_edge = int(20 * s)
        scaled_spacing_between = int(15 * s)
        scaled_skill_bar_w = int(self.logical_game_area_size * 0.25 * s)
        scaled_skill_bar_h = int(10 * s)
        scaled_text_font_size = int(12 * s)
        font = Style.get_font(scaled_text_font_size)

        skill_bar_x = target_ui_bar_rect.left + scaled_spacing_from_edge + scaled_health_bar_w + scaled_spacing_between
        skill_bar_y = target_ui_bar_rect.top + (target_ui_bar_rect.height - scaled_skill_bar_h) // 2

        self._render_single_skill_bar(self.window, skill_data, font, skill_bar_x, skill_bar_y, scaled_skill_bar_w, scaled_skill_bar_h, s)

    def close(self):
        if DEBUG_RENDERER: print("[Renderer.close] Closing Renderer.")
        # No pygame.quit() here