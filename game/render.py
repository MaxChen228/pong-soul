# pong-soul/game/render.py
import math
import pygame
from game.theme import Style
from game.settings import GameSettings
from utils import resource_path
from game.skills.skill_config import SKILL_CONFIGS # 用於技能條顏色等

DEBUG_RENDERER = False
DEBUG_RENDERER_FULLSCREEN = False

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
            if not hasattr(Renderer, '_original_ball_visuals'):
                Renderer._original_ball_visuals = {}
                try:
                    Renderer._original_ball_visuals["default"] = pygame.image.load(resource_path("assets/sunglasses.png")).convert_alpha()
                    if DEBUG_RENDERER: print(f"[Renderer.__init__] Loaded 'default' ball image.")
                except Exception as e_default:
                    if DEBUG_RENDERER: print(f"[Renderer.__init__] Error loading 'default' ball image: {e_default}. Creating fallback.")
                    fb_surf_def = pygame.Surface((40, 40), pygame.SRCALPHA) # 假設基礎邏輯尺寸
                    pygame.draw.circle(fb_surf_def, (255, 255, 255), (20, 20), 20)
                    Renderer._original_ball_visuals["default"] = fb_surf_def

                try:
                    # 假設蟲子圖像的邏輯尺寸與預設球類似，或者 SoulEaterBugSkill 的配置中有其基礎尺寸
                    # 為了簡化，我們這裡假設蟲子圖像的原始檔案適合直接縮放
                    # SoulEaterBugSkill 的 config 中有 bug_image_path 和 bug_display_scale_factor
                    # Renderer 不應該知道 skill_config，所以這裡我們先用一個固定的 bug 圖像
                    # 或者，更好的方法是技能在 get_visual_params 時提供其圖像的 surface
                    # 但這又回到了傳遞 surface 的問題。
                    # 折衷：Renderer 知道 "soul_eater_bug" 這個 key，並嘗試載入對應資源。
                    bug_cfg = SKILL_CONFIGS.get("soul_eater_bug", {})
                    bug_img_path = bug_cfg.get("bug_image_path", "assets/soul_eater_bug.png") # 從 skill_config 取路徑
                    Renderer._original_ball_visuals["soul_eater_bug"] = pygame.image.load(resource_path(bug_img_path)).convert_alpha()
                    if DEBUG_RENDERER: print(f"[Renderer.__init__] Loaded 'soul_eater_bug' ball image from {bug_img_path}.")
                except Exception as e_bug:
                    if DEBUG_RENDERER: print(f"[Renderer.__init__] Error loading 'soul_eater_bug' image: {e_bug}. Creating fallback.")
                    fb_surf_bug = pygame.Surface((50, 50), pygame.SRCALPHA) # 假設蟲子稍大
                    pygame.draw.ellipse(fb_surf_bug, (100, 0, 100), fb_surf_bug.get_rect()) # 紫色蟲
                    Renderer._original_ball_visuals["soul_eater_bug"] = fb_surf_bug

            # self.ball_image 將在 render 時根據 image_key 動態選擇和縮放，不再是固定的單一圖像
            # 但是，Renderer 需要一個預設的 self.ball_image 以防萬一，或者在 render 時處理 image_key 不存在的情況
            # 我們將在 render 時處理圖像的選擇和縮放。
            # scaled_ball_diameter_px 仍然有用，用於計算縮放後的尺寸。
            self.scaled_ball_diameter_px = int(self.logical_ball_radius_px * 2 * self.game_content_scale_factor)
            if self.scaled_ball_diameter_px <= 0: self.scaled_ball_diameter_px = max(1, int(20 * self.game_content_scale_factor))

            if DEBUG_RENDERER_FULLSCREEN:
                print(f"[DEBUG_RENDERER_FULLSCREEN][Renderer.__init__] Expected scaled ball diameter: {self.scaled_ball_diameter_px}px")

        except Exception as e: # 這個 try-except 塊是外層的，處理上面所有圖像載入的通用錯誤
            if DEBUG_RENDERER: print(f"[Renderer.__init__] General error during ball image preparation: {e}")
            # 確保 self.scaled_ball_diameter_px 有值
            if not hasattr(self, 'scaled_ball_diameter_px') or self.scaled_ball_diameter_px <= 0:
                self.scaled_ball_diameter_px = max(1, int(20 * self.game_content_scale_factor))
            # 確保 _original_ball_visuals["default"] 至少有一個備用圖像
            if not hasattr(Renderer, '_original_ball_visuals') or "default" not in Renderer._original_ball_visuals:
                if not hasattr(Renderer, '_original_ball_visuals'): Renderer._original_ball_visuals = {}
                fb_surf_def = pygame.Surface((40, 40), pygame.SRCALPHA)
                pygame.draw.circle(fb_surf_def, (255, 255, 255), (20, 20), 20)
                Renderer._original_ball_visuals["default"] = fb_surf_def

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

    def _draw_slowmo_visuals(self, target_surface, skill_visual_params, game_render_area_on_target, view_player_paddle_data):
        """
        繪製 SlowMo 技能的視覺效果（衝擊波、軌跡、時鐘）。
        skill_visual_params: 從 player_data["skill_data"]["visual_params"] 獲取的字典。
        game_render_area_on_target: 當前視角的遊戲區域在螢幕上的 Rect。
        view_player_paddle_data: 視角擁有者的球拍數據，用於軌跡繪製。
        """
        s = self.game_content_scale_factor
        ga_left = game_render_area_on_target.left
        ga_top = game_render_area_on_target.top
        ga_width_scaled = game_render_area_on_target.width
        ga_height_scaled = game_render_area_on_target.height

        # 1. 衝擊波繪製
        shockwave_list = skill_visual_params.get("shockwaves", [])
        for wave_param in shockwave_list:
            # wave_param["cx_norm"] 和 wave_param["cy_norm"] 是場地正規化座標
            # SlowMo 衝擊波通常從技能擁有者的球拍位置發出。
            # Renderer._render_player_view 繪製的是特定玩家的視角，該玩家總是在底部。
            # 因此，如果衝擊波屬於此視角玩家，其 Y 座標應映射到此視角的底部。
            # skill_visual_params 已經由 SlowMoSkill.get_visual_params() 生成，
            # 其中 cx_norm, cy_norm 是技能擁有者球拍在場地中的 Y。
            # 我們需要將這個場地Y轉換為當前視角的Y。

            # 簡化：假設衝擊波參數中的 cx_norm, cy_norm 已經是相對於技能發起者球拍表面
            # 而技能發起者在自己的視角中總是在底部。
            owner_paddle_y_on_current_area_norm = 1.0 - (self.logical_paddle_height_px / self.logical_game_area_size) / 2 # 近似底部球拍中心Y

            shockwave_center_x_in_area_scaled = wave_param["cx_norm"] * ga_width_scaled
            # 使用技能擁有者在自己視角中的 Y 位置 (底部)
            shockwave_center_y_in_area_scaled = owner_paddle_y_on_current_area_norm * ga_height_scaled

            cx_on_surface_px = ga_left + int(shockwave_center_x_in_area_scaled)
            cy_on_surface_px = ga_top + int(shockwave_center_y_in_area_scaled)

            current_radius_scaled_px = int(wave_param["current_radius_logic_px"] * s)

            # 舊版 SlowMoSkill.render 中 border_width 是根據 alpha 變的，現在 get_visual_params 傳固定邏輯寬度
            scaled_wave_border_width = max(1, int(wave_param.get("border_width_logic_px", 4) * s * (wave_param["border_color_rgba"][3]/255.0)))


            if current_radius_scaled_px > 0:
                fill_color = wave_param["fill_color_rgba"]
                border_color = wave_param["border_color_rgba"]
                if fill_color[3] > 0: # Alpha > 0
                    temp_circle_surf_size = current_radius_scaled_px * 2
                    if temp_circle_surf_size > 0:
                        temp_circle_surf = pygame.Surface((temp_circle_surf_size, temp_circle_surf_size), pygame.SRCALPHA)
                        pygame.draw.circle(temp_circle_surf, fill_color,
                                        (current_radius_scaled_px, current_radius_scaled_px), current_radius_scaled_px)
                        target_surface.blit(temp_circle_surf, (cx_on_surface_px - current_radius_scaled_px, cy_on_surface_px - current_radius_scaled_px))
                if border_color[3] > 0 and scaled_wave_border_width > 0:
                    pygame.draw.circle(target_surface, border_color,
                                    (cx_on_surface_px, cy_on_surface_px), current_radius_scaled_px, width=scaled_wave_border_width)

        # 2. 球拍軌跡繪製
        paddle_trail_list = skill_visual_params.get("paddle_trails", [])
        owner_paddle_width_logic_px = skill_visual_params.get("owner_paddle_width_logic_px", self.logical_game_area_size * 0.15) # 備用值
        owner_paddle_height_logic_px = skill_visual_params.get("owner_paddle_height_logic_px", self.logical_paddle_height_px)

        owner_paddle_width_scaled = int(owner_paddle_width_logic_px * s)
        owner_paddle_height_scaled = int(owner_paddle_height_logic_px * s)

        # 軌跡的 Y 座標（視角擁有者的球拍Y，總是在底部）
        rect_y_on_surface_px = ga_top + ga_height_scaled - owner_paddle_height_scaled

        for trail_param in paddle_trail_list:
            trail_color_rgba = trail_param["color_rgba"]
            if trail_color_rgba[3] > 0: # Alpha > 0
                trail_center_x_in_area_scaled = int(trail_param["x_norm"] * ga_width_scaled)
                rect_center_x_on_surface_px = ga_left + trail_center_x_in_area_scaled
                rect_left_on_surface_px = rect_center_x_on_surface_px - owner_paddle_width_scaled // 2

                trail_surf = pygame.Surface((owner_paddle_width_scaled, owner_paddle_height_scaled), pygame.SRCALPHA)
                trail_surf.fill(trail_color_rgba)
                target_surface.blit(trail_surf, (rect_left_on_surface_px, rect_y_on_surface_px))

        # 3. 時鐘 UI 繪製 (在 game_render_area_on_target 中心)
        clock_param = skill_visual_params.get("clock")
        if clock_param and clock_param.get("is_visible"):
            clock_color_rgba = clock_param["color_rgba"]
            if clock_color_rgba[3] > 0: # Alpha > 0
                clock_center_x_on_surface = game_render_area_on_target.centerx
                clock_center_y_on_surface = game_render_area_on_target.centery
                scaled_clock_radius = int(clock_param["radius_logic_px"] * s)
                scaled_clock_line_width = max(1, int(clock_param["line_width_logic_px"] * s))

                if scaled_clock_radius > 0 :
                    progress_ratio = clock_param["progress_ratio"]
                    angle_deg_remaining = progress_ratio * 360.0
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
                            pygame.draw.arc(target_surface, clock_color_rgba, arc_rect,
                                            start_angle_rad, end_angle_rad, width=scaled_clock_line_width)
                        except TypeError: 
                            pygame.draw.arc(target_surface, clock_color_rgba, arc_rect,
                                            start_angle_rad, end_angle_rad, scaled_clock_line_width)
    def _render_player_view(self,
                            target_surface_for_view, 
                            view_player_data, 
                            opponent_data_for_this_view, 
                            ball_data, 
                            trail_data, 
                            paddle_height_norm, # 正規化球拍高度 (來自 env.get_render_data)
                            # ball_spin, # spin 已經在 ball_data 中
                            game_render_area_on_target, 
                            is_top_player_perspective=False):

        s = self.game_content_scale_factor 
        ga_left = game_render_area_on_target.left
        ga_top = game_render_area_on_target.top
        ga_width_scaled = game_render_area_on_target.width
        ga_height_scaled = game_render_area_on_target.height

        self._draw_walls(target_surface_for_view, game_render_area_on_target)

        # --- 技能視覺效果渲染 ---
        skill_data = view_player_data.get("skill_data")
        if skill_data:
            skill_visual_params = skill_data.get("visual_params")
            if skill_visual_params and skill_visual_params.get("active_effects", False):
                skill_type = skill_visual_params.get("type")
                if skill_type == "slowmo":
                    self._draw_slowmo_visuals(target_surface_for_view, skill_visual_params, game_render_area_on_target, view_player_data)
                # elif skill_type == "soul_eater_bug":
                    # 如果 SoulEaterBug 有除了改變球以外的特效，在這裡處理
                    # pass 
                # ... 可以添加其他技能類型的繪製邏輯 ...
        # --- 技能視覺效果渲染結束 ---

        try:
            ball_norm_x = ball_data["x_norm"]
            ball_norm_y_raw = ball_data["y_norm"]
            ball_spin = ball_data["spin"] # 從 ball_data 獲取 spin
            ball_image_key = ball_data.get("image_key", "default") # 從 ball_data 獲取 image_key

            ball_norm_y_for_view = 1.0 - ball_norm_y_raw if is_top_player_perspective else ball_norm_y_raw

            ball_center_x_scaled = ga_left + int(ball_norm_x * ga_width_scaled)
            ball_center_y_scaled = ga_top + int(ball_norm_y_for_view * ga_height_scaled)

            vp_paddle_norm_x = view_player_data["x_norm"]
            vp_paddle_center_x_scaled = ga_left + int(vp_paddle_norm_x * ga_width_scaled)
            # 球拍寬度 paddle_width_norm 是相對於 logical_game_area_size 的
            vp_paddle_width_scaled = int(view_player_data["paddle_width_norm"] * self.logical_game_area_size * s) 
            vp_paddle_height_scaled = int(self.logical_paddle_height_px * s) 
            vp_paddle_color = view_player_data.get("paddle_color", Style.PLAYER_COLOR) 
            scaled_paddle_border_radius = max(1, int(3 * s))

            pygame.draw.rect(target_surface_for_view, vp_paddle_color,
                (vp_paddle_center_x_scaled - vp_paddle_width_scaled // 2,
                ga_top + ga_height_scaled - vp_paddle_height_scaled, 
                vp_paddle_width_scaled, vp_paddle_height_scaled), border_radius=scaled_paddle_border_radius)

            opp_paddle_norm_x = opponent_data_for_this_view["x_norm"]
            opp_paddle_center_x_scaled = ga_left + int(opp_paddle_norm_x * ga_width_scaled)
            opp_paddle_width_scaled = int(opponent_data_for_this_view["paddle_width_norm"] * self.logical_game_area_size * s)
            opp_paddle_height_scaled = int(self.logical_paddle_height_px * s)
            opp_paddle_color = opponent_data_for_this_view.get("paddle_color", Style.AI_COLOR)

            pygame.draw.rect(target_surface_for_view, opp_paddle_color,
                (opp_paddle_center_x_scaled - opp_paddle_width_scaled // 2,
                ga_top, 
                opp_paddle_width_scaled, opp_paddle_height_scaled), border_radius=scaled_paddle_border_radius)

            if trail_data:
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

            # --- 選擇並縮放球的圖像 ---
            original_ball_surf = Renderer._original_ball_visuals.get(ball_image_key, Renderer._original_ball_visuals["default"])

            # 根據 image_key，球的邏輯直徑可能不同。
            # 例如，蟲子圖像的 "bug_display_scale_factor" 可能使其邏輯上比普通球大。
            # self.scaled_ball_diameter_px 是基於 self.logical_ball_radius_px 計算的。
            # 如果蟲子有不同的基礎尺寸，這裡需要調整。
            # 暫時假設所有球視覺的目標縮放直徑都是 self.scaled_ball_diameter_px
            current_ball_render_image_scaled = pygame.transform.smoothscale(original_ball_surf, (self.scaled_ball_diameter_px, self.scaled_ball_diameter_px))
            # --- 球圖像選擇結束 ---

            spin_for_this_view = -ball_spin if is_top_player_perspective else ball_spin
            self.ball_angle = (self.ball_angle + spin_for_this_view * 10) % 360 

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