# pong-soul/game/render.py
import math
import pygame
from game.theme import Style
from game.settings import GameSettings # GameSettings 用於 game_mode
from utils import resource_path
from game.skills.skill_config import SKILL_CONFIGS # 用於技能條顏色等

DEBUG_RENDERER = True
DEBUG_RENDERER_FULLSCREEN = True # ⭐️ 新增排錯開關

class Renderer:
    # ⭐️ 修改構造函數簽名
    def __init__(self, env, game_mode, actual_screen_surface, actual_screen_width, actual_screen_height):
        if DEBUG_RENDERER: print(f"[Renderer.__init__] Initializing Renderer for game_mode: {game_mode}")
        if DEBUG_RENDERER_FULLSCREEN:
            print(f"[DEBUG_RENDERER_FULLSCREEN][Renderer.__init__] Received actual_screen_surface: {type(actual_screen_surface)}")
            if actual_screen_surface:
                print(f"[DEBUG_RENDERER_FULLSCREEN][Renderer.__init__] Surface size: {actual_screen_surface.get_size()}, Expected: {actual_screen_width}x{actual_screen_height}")
            else:
                print(f"[DEBUG_RENDERER_FULLSCREEN][Renderer.__init__] CRITICAL WARNING: actual_screen_surface is None!")

        # pygame.init() # Pygame 已在 main.py 中初始化

        self.env = env
        self.game_mode = game_mode
        self.logical_render_size = env.render_size # 遊戲內容的邏輯尺寸 (例如 400)

        # ⭐️ 使用傳入的 surface 和尺寸
        if actual_screen_surface:
            self.window = actual_screen_surface
            self.actual_main_window_width = actual_screen_width
            self.actual_main_window_height = actual_screen_height
        else:
            # Fallback: 如果沒有提供 surface (理論上在正常流程中不應發生)
            # 則 Renderer 會嘗試創建一個預設大小的視窗，這會脫離全螢幕控制
            if DEBUG_RENDERER_FULLSCREEN:
                print(f"[DEBUG_RENDERER_FULLSCREEN][Renderer.__init__] No actual_screen_surface provided! Falling back to creating a default window (1000x700). This breaks fullscreen.")
            self.actual_main_window_width = 1000 # Fallback width
            self.actual_main_window_height = 700 # Fallback height (to accommodate PvP layout potentially)
            # REMOVED: self.window = pygame.display.set_mode(...) and related caption
            # ‼️ 如果真的執行到這裡，需要一個 pygame surface 實例，否則後續繪圖會失敗
            # ‼️ 這是一個重要的排錯點：確保 PongDuelEnv 總能傳遞一個有效的 surface
            try:
                self.window = pygame.display.set_mode((self.actual_main_window_width, self.actual_main_window_height))
                pygame.display.set_caption("Pong Soul - Renderer Fallback Window")
            except pygame.error as e:
                print(f"[CRITICAL_ERROR_RENDERER] Failed to create fallback window: {e}. Renderer cannot operate.")
                # 在這種情況下，後續的 self.window.fill 等操作會失敗。
                # 一個更健壯的處理方式可能是拋出異常或設定一個標誌使 render() 方法不執行。
                # 為了簡單，我們先假設 self.window 總是被賦值。
                raise RuntimeError(f"Renderer could not establish a drawing surface: {e}")


        # ⭐️ 根據遊戲模式和【實際螢幕尺寸】以及【邏輯尺寸】來定義佈局
        # ⭐️ 現階段（第一階段全螢幕）我們還不進行縮放。
        # ⭐️ 尺寸計算會直接使用邏輯尺寸作為像素尺寸，繪製在實際螢幕的左上角區域。
        # ⭐️ PvP 和 PvA 的 UI 元素偏移和尺寸也暫時使用固定的像素值。

        self.pvp_shared_bottom_ui_height = 100 # 底部共享UI的邏輯/像素高度 (暫不縮放)
        # self.ui_offset_y_per_viewport = 0 # PvP 視口內遊戲區域頂部的偏移 (暫不使用)

        if self.game_mode == GameSettings.GameMode.PLAYER_VS_PLAYER:
            # PvP 模式佈局 (繪製在實際螢幕的左上部分)
            # 假設 PvP 總佈局寬度為 1000px (兩個500px視口)，高度為 遊戲邏輯高度 + 底部UI高度
            # 這些是"目標"繪製區域的尺寸和位置，相對於 self.window (即全螢幕) 的左上角
            
            # 視口寬度暫時固定為 PvP 佈局的一半 (例如 1000px / 2 = 500px)
            # 在縮放階段，這會基於實際螢幕寬度和列數計算
            self.viewport_width = 500 # 每個 PvP 視口的【像素】寬度 (暫不縮放)
            
            # 視口高度是遊戲邏輯渲染區域的高度
            self.viewport_height = self.logical_render_size # 例如 400px (暫不縮放)

            # PvP 模式下，主 "視窗" 的概念是整個螢幕，但我們在這裡定義的是 PvP 內容將要繪製的區域
            # 這不是重新 set_mode，而是定義 Rect 相對於 self.window (全螢幕)
            self.pvp_content_total_width = self.viewport_width * 2 # PvP內容總寬度
            self.pvp_content_total_height = self.viewport_height + self.pvp_shared_bottom_ui_height

            # 定義視口 Rect (相對於 self.window 左上角)
            self.viewport1_rect = pygame.Rect(0, 0, self.viewport_width, self.viewport_height)
            self.viewport2_rect = pygame.Rect(self.viewport_width, 0, self.viewport_width, self.viewport_height)
            self.pvp_shared_bottom_ui_rect = pygame.Rect(0, self.viewport_height, self.pvp_content_total_width, self.pvp_shared_bottom_ui_height)
            
            self.offset_y = 0 # PvP模式下，遊戲區域直接在視口頂部開始，所以視口內的頂部偏移為0

            if DEBUG_RENDERER_FULLSCREEN:
                print(f"[DEBUG_RENDERER_FULLSCREEN][Renderer.__init__] PvP mode layout (unscaled, on actual_screen_surface {self.actual_main_window_width}x{self.actual_main_window_height}):")
                print(f"    Viewport logical game size: {self.logical_render_size}x{self.logical_render_size}")
                print(f"    Viewport pixel size (unscaled): {self.viewport_width}x{self.viewport_height}")
                print(f"    Shared UI pixel height (unscaled): {self.pvp_shared_bottom_ui_height}")
                print(f"    Viewport1 Rect: {self.viewport1_rect}")
                print(f"    Viewport2 Rect: {self.viewport2_rect}")
                print(f"    Shared Bottom UI Rect: {self.pvp_shared_bottom_ui_rect}")
        else: # PvA 模式佈局 (繪製在實際螢幕的左上部分)
            self.ui_offset_y_single_view = 100 # 頂部和底部UI條的邏輯/像素高度 (暫不縮放)
            self.offset_y = self.ui_offset_y_single_view # PvA 模式下，遊戲區域的頂部偏移

            # PvA 內容將要繪製的區域尺寸和位置，相對於 self.window (全螢幕) 的左上角
            self.pva_content_width = self.logical_render_size # 例如 400px
            self.pva_content_height = self.logical_render_size + 2 * self.ui_offset_y_single_view # 例如 400 + 2*100 = 600px

            # PvA 模式的遊戲區域 Rect (相對於 self.window 左上角)
            self.game_area_rect = pygame.Rect(0, self.offset_y, self.logical_render_size, self.logical_render_size)
            
            if DEBUG_RENDERER_FULLSCREEN:
                print(f"[DEBUG_RENDERER_FULLSCREEN][Renderer.__init__] PvA mode layout (unscaled, on actual_screen_surface {self.actual_main_window_width}x{self.actual_main_window_height}):")
                print(f"    Logical game size: {self.logical_render_size}x{self.logical_render_size}")
                print(f"    Top/Bottom UI bar height (unscaled): {self.ui_offset_y_single_view}")
                print(f"    Game Area Rect (on surface): {self.game_area_rect}")


        self.clock = pygame.time.Clock()
        try:
            # 球的直徑基於 env 的邏輯球半徑 (ball_radius_px)
            # 這些是未縮放的像素值
            ball_diameter_px = int(env.ball_radius_px * 2)
            if ball_diameter_px <= 0:
                if DEBUG_RENDERER: print(f"[Renderer.__init__] Warning: env.ball_radius_px resulted in non-positive diameter ({ball_diameter_px}). Defaulting to 20px.")
                ball_diameter_px = 20
            
            # self.ball_image_original 用於 SoulEaterBugSkill 恢復圖像時的備份
            self.ball_image_original_unscaled = pygame.image.load(resource_path("assets/sunglasses.png")).convert_alpha()
            # self.ball_image 是當前要繪製的球圖像，初始時是原始圖像按邏輯尺寸縮放
            self.ball_image = pygame.transform.smoothscale(self.ball_image_original_unscaled, (ball_diameter_px, ball_diameter_px))
            if DEBUG_RENDERER_FULLSCREEN:
                print(f"[DEBUG_RENDERER_FULLSCREEN][Renderer.__init__] Ball image loaded and scaled to logical diameter: {ball_diameter_px}px")

        except Exception as e:
            if DEBUG_RENDERER: print(f"[Renderer.__init__] Error loading/scaling ball image: {e}. Creating fallback.")
            ball_diameter_px = int(env.ball_radius_px * 2) if hasattr(env, 'ball_radius_px') and env.ball_radius_px * 2 > 0 else 20
            self.ball_image = pygame.Surface((ball_diameter_px, ball_diameter_px), pygame.SRCALPHA)
            pygame.draw.circle(self.ball_image, (255, 255, 255), (ball_diameter_px // 2, ball_diameter_px // 2), ball_diameter_px // 2)
            self.ball_image_original_unscaled = self.ball_image.copy() # 備份fallback圖像

        self.ball_angle = 0
        # 技能相關視覺效果的參數 (暫時不變)
        self.skill_glow_position = 0; self.skill_glow_trail = []; self.max_skill_glow_trail_length = 15
        if DEBUG_RENDERER: print("[Renderer.__init__] Renderer initialization complete.")


    def _draw_walls(self, target_surface, game_area_width_px, game_area_height_px, offset_x_on_target=0, offset_y_on_target=0, color=(100,100,100), thickness=2):
        """
        在指定的 target_surface 內的指定偏移處，繪製具有指定像素寬高的遊戲區域的左右牆壁線。
        game_area_width_px, game_area_height_px 是牆壁所包圍的遊戲區域的【像素】尺寸。
        offset_x_on_target, offset_y_on_target 是遊戲區域左上角在 target_surface 上的【像素】偏移。
        """
        # 牆壁畫在遊戲邏輯區域的邊緣
        left_wall_x = offset_x_on_target + thickness // 2
        right_wall_x = offset_x_on_target + game_area_width_px - thickness // 2 # 應為 game_area_width_px - thickness // 2
        wall_top_y = offset_y_on_target
        wall_bottom_y = offset_y_on_target + game_area_height_px

        pygame.draw.line(target_surface, color, (left_wall_x, wall_top_y), (left_wall_x, wall_bottom_y), thickness)
        pygame.draw.line(target_surface, color, (right_wall_x, wall_top_y), (right_wall_x, wall_bottom_y), thickness)
        # if DEBUG_RENDERER: print(f"[Renderer._draw_walls] Walls drawn on surface at L:{left_wall_x}, R:{right_wall_x}, T:{wall_top_y}, B:{wall_bottom_y}")


    def _render_player_view(self,
                            target_surface_for_view, # 通常是 self.window 的一個 subsurface (用於 PvP) 或 self.window 本身 (用於 PvA)
                            view_player_state,
                            opponent_state_for_this_view,
                            game_area_rect_on_target, # pygame.Rect, 定義遊戲內容在 target_surface_for_view 上的【像素】位置和大小
                            is_top_player_perspective=False):
        """
        在 target_surface_for_view 內的 game_area_rect_on_target 區域繪製遊戲元素。
        所有座標和尺寸轉換應在此函數內部處理，將 env 中的正規化座標 (0-1) 轉換為
        相對於 game_area_rect_on_target 的像素座標。
        """
        if DEBUG_RENDERER_FULLSCREEN:
            pass
            # print(f"[DEBUG_RENDERER_FULLSCREEN][Renderer._render_player_view] For {view_player_state.identifier}, "
            #       f"TargetSurfForView: {target_surface_for_view.get_size()}, "
            #       f"GameAreaRectOnTarget: {game_area_rect_on_target}, "
            #       f"IsTopPerspective: {is_top_player_perspective}")

        ga_x_on_target = game_area_rect_on_target.x # 遊戲區域在 target_surface_for_view 上的左上角 X
        ga_y_on_target = game_area_rect_on_target.y # 遊戲區域在 target_surface_for_view 上的左上角 Y
        ga_w_px = game_area_rect_on_target.width    # 遊戲區域的【像素】寬度 (等於 self.logical_render_size，因為未縮放)
        ga_h_px = game_area_rect_on_target.height   # 遊戲區域的【像素】高度 (等於 self.logical_render_size，因為未縮放)

        # 1. 繪製遊戲區域背景 (可選, 如果 target_surface_for_view 已填充則可能不需要)
        # pygame.draw.rect(target_surface_for_view, Style.BACKGROUND_COLOR, game_area_rect_on_target)

        # 2. 繪製牆壁 (在遊戲區域內部)
        # _draw_walls 的 offset_x/y 是相對於 target_surface_for_view 的，所以直接用 ga_x_on_target, ga_y_on_target
        self._draw_walls(target_surface_for_view, ga_w_px, ga_h_px,
                         offset_x_on_target=ga_x_on_target, offset_y_on_target=ga_y_on_target)

        # 3. 技能渲染 (先渲染底層效果，如 SlowMo 的衝擊波)
        # 技能的 render 方法需要知道它是在哪個 surface 和 rect 內渲染
        # ⭐️ 技能渲染的座標轉換是一個複雜點，需要確保技能特效相對於正確的遊戲區域繪製
        # ⭐️ 暫時假設技能 render 方法能處理好在其 owner 的視角下，相對於整個 target_surface_for_view 繪製
        # ⭐️ 後續階段，我們需要將 game_area_rect_on_target 和縮放因子傳遞給技能的 render 方法
        if view_player_state.skill_instance:
            # 判斷是否需要渲染技能 (active, fading, fogging etc.)
            skill_should_render = view_player_state.skill_instance.is_active() or \
                                  (hasattr(view_player_state.skill_instance, 'fadeout_active') and view_player_state.skill_instance.fadeout_active) or \
                                  (hasattr(view_player_state.skill_instance, 'fog_active') and view_player_state.skill_instance.fog_active)
            if skill_should_render:
                # 理想情況: skill.render(target_surface_for_view, game_area_rect_on_target, scale_factor)
                # 目前: skill.render(target_surface_for_view) - 技能需要自己處理好座標問題
                # SlowMoSkill 的 render 內部有 self.env.renderer.offset_y，這在全螢幕下需要調整
                # 暫時，我們假設 SlowMoSkill 的特效是相對於整個 target_surface_for_view 的中心，
                # 或者如果它是為 PvA 設計的，它會使用 self.env.renderer.offset_y (現在是self.offset_y)
                # 這部分在 PvP 分屏時可能不完全準確，需要在縮放階段詳細調整技能渲染。
                if DEBUG_RENDERER_FULLSCREEN and isinstance(view_player_state.skill_instance, __import__('game.skills.slowmo_skill', fromlist=['SlowMoSkill']).SlowMoSkill):
                     pass
                    # print(f"    Rendering SlowMoSkill for {view_player_state.identifier}. "
                    #       f"Renderer's self.offset_y = {self.offset_y} (used by skill for PvA clock). "
                    #       f"Game area top on target: {ga_y_on_target}")
                view_player_state.skill_instance.render(target_surface_for_view)


        # 4. 繪製主要遊戲元素 (球、球拍、拖尾)
        try:
            # 球的正規化座標 (0-1)
            ball_norm_x, ball_norm_y_raw = self.env.ball_x, self.env.ball_y
            
            # 如果是頂部玩家視角，Y軸顛倒 (0在頂，1在底)
            ball_norm_y_for_view = 1.0 - ball_norm_y_raw if is_top_player_perspective else ball_norm_y_raw
            
            # 將正規化座標轉換為相對於 game_area_rect_on_target 左上角的像素座標
            ball_center_x_px = ga_x_on_target + int(ball_norm_x * ga_w_px)
            ball_center_y_px = ga_y_on_target + int(ball_norm_y_for_view * ga_h_px)

            # 視角玩家的球拍 (總是在此視角的底部)
            vp_paddle_norm_x = view_player_state.x
            # PvP 模式下，如果 is_top_player_perspective (即 P2)，其 X 軸控制是否需要鏡像？
            # 假設不需要鏡像，P2 在右邊視口，其 'left' 鍵仍然是向其視口的左邊移動。
            
            vp_paddle_center_x_px = ga_x_on_target + int(vp_paddle_norm_x * ga_w_px)
            # 球拍寬高使用 env 中定義的邏輯像素值 (因為目前未縮放)
            vp_paddle_width_px = int(view_player_state.paddle_width) # paddle_width 來自 PlayerState，是邏輯像素
            vp_paddle_height_px = int(self.env.paddle_height_px)   # 來自 env，是邏輯像素
            vp_paddle_color = view_player_state.paddle_color if view_player_state.paddle_color else Style.PLAYER_COLOR

            # 繪製視角玩家的球拍 (在此視角的底部)
            pygame.draw.rect(target_surface_for_view, vp_paddle_color,
                (vp_paddle_center_x_px - vp_paddle_width_px // 2,
                 ga_y_on_target + ga_h_px - vp_paddle_height_px, # 在遊戲區域底部
                 vp_paddle_width_px, vp_paddle_height_px), border_radius=3) # 圓角稍微小一點

            # 對手玩家的球拍 (總是在此視角的頂部)
            opp_paddle_norm_x = opponent_state_for_this_view.x
            opp_paddle_center_x_px = ga_x_on_target + int(opp_paddle_norm_x * ga_w_px)
            opp_paddle_width_px = int(opponent_state_for_this_view.paddle_width)
            opp_paddle_height_px = int(self.env.paddle_height_px)
            opp_paddle_color = opponent_state_for_this_view.paddle_color if opponent_state_for_this_view.paddle_color else Style.AI_COLOR

            pygame.draw.rect(target_surface_for_view, opp_paddle_color,
                (opp_paddle_center_x_px - opp_paddle_width_px // 2,
                 ga_y_on_target, # 在遊戲區域頂部
                 opp_paddle_width_px, opp_paddle_height_px), border_radius=3)

            # 球的拖尾
            # 拖尾座標也需要根據 is_top_player_perspective 進行 Y 軸轉換並映射到像素
            if self.env.trail: # 僅當有拖尾數據時繪製
                for i, (tx_norm, ty_norm_raw) in enumerate(self.env.trail):
                    trail_ty_norm_for_view = 1.0 - ty_norm_raw if is_top_player_perspective else ty_norm_raw
                    
                    fade = int(200 * (i + 1) / len(self.env.trail)) # 拖尾透明度 (最大200，避免完全不透明)
                    base_ball_color_rgb = Style.BALL_COLOR[:3] if isinstance(Style.BALL_COLOR, tuple) and len(Style.BALL_COLOR) >=3 else (255,255,255)
                    trail_color_with_alpha = (*base_ball_color_rgb, fade)
                    
                    # 拖尾圓點的半徑 (像素，暫時固定，可隨球縮放)
                    trail_circle_radius_px = int(self.env.ball_radius_px * 0.4) # 例如球半徑的40%
                    if trail_circle_radius_px < 1: trail_circle_radius_px = 1
                    
                    temp_surf = pygame.Surface((trail_circle_radius_px * 2, trail_circle_radius_px * 2), pygame.SRCALPHA)
                    pygame.draw.circle(temp_surf, trail_color_with_alpha,
                                       (trail_circle_radius_px, trail_circle_radius_px), trail_circle_radius_px)
                    
                    trail_x_px = ga_x_on_target + int(tx_norm * ga_w_px)
                    trail_y_px = ga_y_on_target + int(trail_ty_norm_for_view * ga_h_px)
                    target_surface_for_view.blit(temp_surf, (trail_x_px - trail_circle_radius_px, trail_y_px - trail_circle_radius_px))
            
            # 球圖像 (self.ball_image 已經是按邏輯尺寸縮放好的)
            # 球的旋轉角度
            ball_spin_for_view = self.env.spin
            if is_top_player_perspective: # 如果視角顛倒，視覺上旋轉方向也應相反
                ball_spin_for_view = -self.env.spin

            # self.ball_angle 是 Renderer 的一個狀態，用於累加旋轉
            # 乘以一個因子使旋轉更明顯，這個因子可能需要調整
            # 這個旋轉的視覺效果在 PvP 雙視圖下是否完全協調需要測試
            self.ball_angle += ball_spin_for_view * 10 # 調整旋轉速度因子
            self.ball_angle %= 360 # 保持在0-359度

            # 確保 self.ball_image 是最新的 (例如被技能替換後)
            current_ball_render_image = self.ball_image # Renderer.ball_image 可能被 SoulEaterBugSkill 修改
            
            rotated_ball = pygame.transform.rotate(current_ball_render_image, self.ball_angle)
            ball_rect = rotated_ball.get_rect(center=(ball_center_x_px, ball_center_y_px))
            target_surface_for_view.blit(rotated_ball, ball_rect)

        except Exception as e:
             if DEBUG_RENDERER: print(f"[Renderer._render_player_view] ({view_player_state.identifier}) drawing error: {e}")
             import traceback
             traceback.print_exc() # 打印詳細的錯誤堆棧


    def render(self):
        if not self.env or not self.window : # 確保 env 和 self.window (主表面) 都存在
            if DEBUG_RENDERER: print("[Renderer.render] Error: Env or self.window not available. Skipping render.")
            return

        current_time_ticks = pygame.time.get_ticks()
        freeze_active = (self.env.freeze_timer > 0 and (current_time_ticks - self.env.freeze_timer < self.env.freeze_duration))
        
        # ⭐️ 背景填充作用於整個 self.window (即全螢幕表面)
        current_bg_color = Style.BACKGROUND_COLOR
        if freeze_active:
            # 閃爍效果
            current_bg_color = (200,200,200) if (current_time_ticks // 150) % 2 == 0 else (50,50,50) # 調整閃爍顏色和頻率
        self.window.fill(current_bg_color)

        # UI 覆蓋顏色 (用於 UI 條背景)
        # 確保 Style.BACKGROUND_COLOR 是 RGB 元組
        bg_r, bg_g, bg_b = Style.BACKGROUND_COLOR[:3] if isinstance(Style.BACKGROUND_COLOR, tuple) and len(Style.BACKGROUND_COLOR) >=3 else (0,0,0)
        ui_overlay_color = tuple(max(0, c - 20) for c in (bg_r, bg_g, bg_b))


        if self.game_mode == GameSettings.GameMode.PLAYER_VS_PLAYER:
            # --- PvP 模式渲染 ---
            # 1. P1 視口 (左側)
            #    P1 視口的繪圖目標是 self.window 的一個子區域 (subsurface)
            #    或者直接在 self.window 上根據 viewport1_rect 的偏移繪圖。
            #    使用 subsurface 可以隔離繪圖，但座標是相對於 subsurface 左上角的。
            #    直接在 self.window 上繪圖，座標需要加上 viewport1_rect.topleft。
            #    為了與 _render_player_view 的 game_area_rect_on_target 概念一致，
            #    我們在 self.window 上繪製，game_area_rect_on_target 就是 self.viewport1_rect。
            
            # P1 視口背景 (可選，如果整個 self.window 已填色)
            # pygame.draw.rect(self.window, Style.PLAYER_COLOR if hasattr(Style,'PLAYER_VIEW_BG') else (20,20,60), self.viewport1_rect)

            # P1 遊戲區域在 P1 視口內的邏輯定義 (目前是整個視口)
            # game_area_rect_in_vp1 就是 self.viewport1_rect，因為遊戲內容填滿視口
            self._render_player_view(self.window, self.env.player1, self.env.opponent,
                                     self.viewport1_rect, # P1 的遊戲區域就是其視口區域
                                     is_top_player_perspective=False)

            # 2. P2 視口 (右側)
            # pygame.draw.rect(self.window, Style.AI_COLOR if hasattr(Style,'OPPONENT_VIEW_BG') else (60,20,20), self.viewport2_rect)
            self._render_player_view(self.window, self.env.opponent, self.env.player1,
                                     self.viewport2_rect, # P2 的遊戲區域就是其視口區域
                                     is_top_player_perspective=True)

            # 3. 繪製底部共享 UI (在 self.window 上的 self.pvp_shared_bottom_ui_rect 區域)
            # pygame.draw.rect(self.window, ui_overlay_color, self.pvp_shared_bottom_ui_rect) # 用統一的UI覆蓋色
            self._render_pvp_bottom_ui(self.window, self.env.player1, self.env.opponent, self.pvp_shared_bottom_ui_rect)
            
            # 4. 繪製中間分割線 (在視口之間，直到視口底部)
            divider_x = self.viewport_width # 分割線在P1視口右邊緣
            pygame.draw.line(self.window, (80,80,80),
                               (divider_x, 0),
                               (divider_x, self.viewport_height), 3) # 線只畫到視口的高度

        else: # --- PvA 模式渲染 ---
            # PvA UI 條 (頂部和底部)
            # 頂部 UI 條背景
            pygame.draw.rect(self.window, ui_overlay_color, (0, 0, self.pva_content_width, self.ui_offset_y_single_view))
            # 底部 UI 條背景
            bottom_ui_y_start_pva = self.ui_offset_y_single_view + self.logical_render_size
            bottom_ui_height_pva = self.pva_content_height - bottom_ui_y_start_pva # (self.actual_main_window_height - bottom_ui_y_start_pva) 應基於 pva_content_height
            if bottom_ui_height_pva > 0:
                 pygame.draw.rect(self.window, ui_overlay_color, (0, bottom_ui_y_start_pva, self.pva_content_width, bottom_ui_height_pva))

            # PvA 遊戲區域 (在 self.window 上的 self.game_area_rect 區域)
            self._render_player_view(self.window, self.env.player1, self.env.opponent,
                                     self.game_area_rect, # PvA 的遊戲區域定義
                                     is_top_player_perspective=False)
            
            # PvA P1 血條和技能 UI (繪製在 self.window 的底部 UI 條區域)
            # 這些UI元素的位置計算需要相對於 self.window 的左上角
            self._render_health_bar_for_pva(self.env.player1, is_opponent=False)
            self._render_health_bar_for_pva(self.env.opponent, is_opponent=True)
            self._render_skill_ui_for_pva(self.env.player1)


        pygame.display.flip() # 最終刷新整個螢幕
        self.clock.tick(60) # 控制幀率

    def _render_pvp_bottom_ui(self, target_surface, player1_state, player2_state, ui_rect):
        """在 PvP 模式的底部共享 UI 區域繪製雙方的血條和技能條。"""
        # if DEBUG_RENDERER: print(f"[Renderer._render_pvp_bottom_ui] Drawing shared UI in rect: {ui_rect}")
        
        # 填充UI條背景 (可選，如果 target_surface 的這部分已被填充)
        # 確保 Style.UI_BACKGROUND_COLOR 存在或有備用
        ui_bg_color = Style.UI_BACKGROUND_COLOR if hasattr(Style, 'UI_BACKGROUND_COLOR') else (30,30,30)
        pygame.draw.rect(target_surface, ui_bg_color, ui_rect)

        # UI元素的基本尺寸和間距 (這些是邏輯/像素值，目前未縮放)
        bar_w_px, bar_h_px = 150, 15 # 血條尺寸略微調整
        skill_bar_w_px, skill_bar_h_px = 100, 8 # 技能條尺寸略微調整
        spacing_px = 10 # 間距
        text_font_size = 14 # 用於玩家標識和技能文字的字體大小
        text_font = Style.get_font(text_font_size)
        
        # P1 UI (在共享條的左側)
        p1_base_x = ui_rect.left + spacing_px * 2 # P1 UI區域的起始X
        p1_ui_y_center = ui_rect.centery # P1 UI元素的垂直中心線

        # P1 玩家標籤
        p1_label_surf = text_font.render("P1", True, Style.PLAYER_COLOR)
        p1_label_rect = p1_label_surf.get_rect(midright=(p1_base_x - spacing_px, p1_ui_y_center - bar_h_px // 2 - spacing_px //2 )) # 血條左上方
        target_surface.blit(p1_label_surf, p1_label_rect)

        # P1 血條 (垂直居中)
        p1_health_bar_y = p1_ui_y_center - bar_h_px - spacing_px // 4 # 血條在中心線偏上
        pygame.draw.rect(target_surface, Style.PLAYER_BAR_BG, (p1_base_x, p1_health_bar_y, bar_w_px, bar_h_px), border_radius=2)
        p1_life_ratio = player1_state.lives / player1_state.max_lives if player1_state.max_lives > 0 else 0
        pygame.draw.rect(target_surface, Style.PLAYER_BAR_FILL, (p1_base_x, p1_health_bar_y, bar_w_px * p1_life_ratio, bar_h_px), border_radius=2)
        
        # P1 技能條 (在血條下方)
        p1_skill_y = p1_ui_y_center + spacing_px // 4 # 技能條在中心線偏下
        if player1_state.skill_instance:
            self._render_single_skill_bar(target_surface, player1_state, text_font, p1_base_x, p1_skill_y, skill_bar_w_px, skill_bar_h_px)

        # P2 UI (在共享條的右側)
        p2_base_end_x = ui_rect.right - spacing_px * 2 # P2 UI區域的結束X (從右邊緣算起)
        p2_ui_x_health_bar_start = p2_base_end_x - bar_w_px # P2血條的起始X
        p2_ui_x_skill_bar_start = p2_base_end_x - skill_bar_w_px # P2技能條的起始X (如果與血條右對齊)
                                                               # 或者 p2_base_end_x - (bar_w_px + skill_bar_w_px + spacing_px) // 2 ... 複雜
                                                               # 簡化：技能條也在血條同樣的X範圍內，但寬度不同
        p2_ui_y_center = ui_rect.centery

        # P2 玩家標籤
        p2_label_surf = text_font.render("P2", True, Style.AI_COLOR) # 使用AI顏色或P2專用色
        p2_label_rect = p2_label_surf.get_rect(midleft=(p2_base_end_x + spacing_px, p2_ui_y_center - bar_h_px // 2 - spacing_px //2)) # 血條右上方
        target_surface.blit(p2_label_surf, p2_label_rect)
        
        # P2 血條
        p2_health_bar_y = p2_ui_y_center - bar_h_px - spacing_px // 4
        pygame.draw.rect(target_surface, Style.AI_BAR_BG, (p2_ui_x_health_bar_start, p2_health_bar_y, bar_w_px, bar_h_px), border_radius=2)
        p2_life_ratio = player2_state.lives / player2_state.max_lives if player2_state.max_lives > 0 else 0
        pygame.draw.rect(target_surface, Style.AI_BAR_FILL, (p2_ui_x_health_bar_start, p2_health_bar_y, bar_w_px * p2_life_ratio, bar_h_px), border_radius=2)
        
        # P2 技能條
        p2_skill_y = p2_ui_y_center + spacing_px // 4
        if player2_state.skill_instance:
            # 技能條在血條下方居中對齊
            p2_skill_x = p2_ui_x_health_bar_start + (bar_w_px - skill_bar_w_px) // 2
            self._render_single_skill_bar(target_surface, player2_state, text_font, p2_skill_x, p2_skill_y, skill_bar_w_px, skill_bar_h_px)


    def _render_single_skill_bar(self, surface, player_state, font, x, y, width, height):
        """輔助方法：繪製單個技能條及其冷卻文字。接收 font 參數。"""
        skill = player_state.skill_instance
        # 文字顯示在技能條右側或下方
        text_offset_x_px = width + 5 # 文字在條右側5px
        
        skill_cfg = SKILL_CONFIGS.get(player_state.skill_code_name, {})
        bar_fill_color_rgb = skill_cfg.get("bar_color", (200, 200, 200))
        bar_bg_color_rgb = (50,50,50) # 技能條背景色
        
        pygame.draw.rect(surface, bar_bg_color_rgb, (x, y, width, height), border_radius=2)
        energy_ratio = skill.get_energy_ratio()
        current_bar_width = int(width * energy_ratio)
        pygame.draw.rect(surface, bar_fill_color_rgb, (x, y, current_bar_width, height), border_radius=2)
        
        # 顯示技能名稱或冷卻時間
        display_text = ""
        text_color = Style.TEXT_COLOR
        if skill.is_active():
            display_text = f"{player_state.skill_code_name.upper()}!" # 技能激活時顯示名稱
            text_color = bar_fill_color_rgb # 用技能顏色
        elif skill.get_cooldown_seconds() > 0:
            display_text = f"{skill.get_cooldown_seconds():.1f}s"
        else: # 可用
            display_text = "READY"
            text_color = (200, 255, 200) # 亮一點的綠色表示可用

        if display_text:
            text_surf = font.render(display_text, True, text_color)
            # 將文字放在技能條右側垂直居中
            text_rect = text_surf.get_rect(midleft=(x + text_offset_x_px, y + height / 2))
            surface.blit(text_surf, text_rect)

    def _render_health_bar_for_pva(self, player_state, is_opponent):
        """PvA 模式下繪製單個玩家的血條 (在頂部或底部UI條)"""
        bar_w_px = int(self.logical_render_size * 0.35) # 血條寬度為遊戲區域的35%
        bar_h_px = 15
        spacing_from_edge = 20 # 離螢幕邊緣/中心的距離
        
        # 確定血條顏色
        bar_bg_color = Style.AI_BAR_BG if is_opponent else Style.PLAYER_BAR_BG
        bar_fill_color = Style.AI_BAR_FILL if is_opponent else Style.PLAYER_BAR_FILL
        label_text = "AI" if is_opponent else "P1"
        label_color = Style.AI_COLOR if is_opponent else Style.PLAYER_COLOR

        font = Style.get_font(14)
        label_surf = font.render(label_text, True, label_color)

        life_ratio = player_state.lives / player_state.max_lives if player_state.max_lives > 0 else 0

        if is_opponent: # 對手 (AI) 在頂部UI條的右側
            bar_x = self.pva_content_width - bar_w_px - spacing_from_edge # pva_content_width 是繪圖區域的寬
            bar_y = (self.ui_offset_y_single_view - bar_h_px) // 2 # 垂直居中於頂部UI條
            label_rect = label_surf.get_rect(midright=(bar_x - 10, bar_y + bar_h_px / 2))
        else: # 玩家在底部UI條的左側
            bar_x = spacing_from_edge
            # 底部UI條的Y起始點是 self.ui_offset_y_single_view + self.logical_render_size
            bottom_ui_top_y = self.ui_offset_y_single_view + self.logical_render_size
            bottom_ui_height = self.pva_content_height - bottom_ui_top_y
            bar_y = bottom_ui_top_y + (bottom_ui_height - bar_h_px) // 2 # 垂直居中於底部UI條
            label_rect = label_surf.get_rect(midleft=(bar_x + bar_w_px + 10, bar_y + bar_h_px / 2))

        pygame.draw.rect(self.window, bar_bg_color, (bar_x, bar_y, bar_w_px, bar_h_px), border_radius=2)
        pygame.draw.rect(self.window, bar_fill_color, (bar_x, bar_y, bar_w_px * life_ratio, bar_h_px), border_radius=2)
        self.window.blit(label_surf, label_rect)


    def _render_skill_ui_for_pva(self, player_state):
        """PvA 模式下 P1 技能 UI (在底部UI條，血條右側)"""
        if not player_state.skill_instance: return

        # 技能條尺寸和位置的邏輯計算 (相對於 pva_content_width 和底部UI條)
        # 假設血條在底部UI條左側，技能條在其右側
        p1_health_bar_logical_width = int(self.logical_render_size * 0.35)
        spacing_from_edge = 20
        spacing_between_elements = 15

        skill_bar_w_px = int(self.logical_render_size * 0.25) # 技能條寬度
        skill_bar_h_px = 10 # 技能條高度
        
        # 技能條X位置：在血條右邊
        skill_bar_x = spacing_from_edge + p1_health_bar_logical_width + spacing_between_elements
        
        # 技能條Y位置 (與血條垂直對齊)
        bottom_ui_top_y = self.ui_offset_y_single_view + self.logical_render_size
        bottom_ui_height = self.pva_content_height - bottom_ui_top_y
        skill_bar_y = bottom_ui_top_y + (bottom_ui_height - skill_bar_h_px) // 2

        font = Style.get_font(12) # 用於技能文字的字體
        self._render_single_skill_bar(self.window, player_state, font, skill_bar_x, skill_bar_y, skill_bar_w_px, skill_bar_h_px)


    def close(self):
        if DEBUG_RENDERER: print("[Renderer.close] Closing Renderer.")
        # Renderer 不再管理 Pygame 的退出，只做自身清理 (如果有的話)
        # pygame.quit() 應在 main.py 中調用