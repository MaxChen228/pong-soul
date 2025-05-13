# game/render.py

import math
import pygame
from game.theme import Style
from game.settings import GameSettings
from game.skills.skill_config import SKILL_CONFIGS
from utils import resource_path

DEBUG_RENDERER = True # ⭐️ 除錯開關

class Renderer:
    def __init__(self, env):
        if DEBUG_RENDERER: print("[Renderer.__init__] Initializing Renderer...")
        pygame.init() 
        self.env = env
        self.render_size = env.render_size 
        self.offset_y = 100 
        
        self.window_width = self.render_size
        self.window_height = self.render_size + 2 * self.offset_y
        self.window = pygame.display.set_mode((self.window_width, self.window_height))
        pygame.display.set_caption("Pong Soul (Renderer Updated)") 

        self.clock = pygame.time.Clock()

        if DEBUG_RENDERER: print(f"[Renderer.__init__] Loading ball image. env.ball_radius_px: {env.ball_radius_px}")
        try:
            ball_diameter_px = int(env.ball_radius_px * 2)
            if ball_diameter_px <= 0:
                if DEBUG_RENDERER: print(f"[Renderer.__init__] Warning: ball_diameter_px is {ball_diameter_px}. Setting to default 20.")
                ball_diameter_px = 20 

            self.ball_image_original = pygame.image.load(resource_path("assets/sunglasses.png")).convert_alpha()
            self.ball_image = pygame.transform.smoothscale(
                self.ball_image_original,
                (ball_diameter_px, ball_diameter_px)
            )
        except Exception as e: # Catching generic exception for brevity
            if DEBUG_RENDERER: print(f"[Renderer.__init__] Error loading/scaling ball image: {e}. Creating fallback.")
            ball_diameter_px = int(env.ball_radius_px * 2) if hasattr(env, 'ball_radius_px') and env.ball_radius_px * 2 > 0 else 20
            self.ball_image = pygame.Surface((ball_diameter_px, ball_diameter_px), pygame.SRCALPHA)
            pygame.draw.circle(self.ball_image, (255, 255, 255), (ball_diameter_px // 2, ball_diameter_px // 2), ball_diameter_px // 2)
        
        self.ball_angle = 0 
        self.skill_glow_position = 0
        self.skill_glow_trail = []
        self.max_skill_glow_trail_length = 15
        if DEBUG_RENDERER: print("[Renderer.__init__] Renderer initialization complete.")


    def render(self):
        if not self.env:
            if DEBUG_RENDERER: print("[Renderer.render] Error: self.env is not set.")
            return

        freeze_active = (
            self.env.freeze_timer > 0
            and (pygame.time.get_ticks() - self.env.freeze_timer < self.env.freeze_duration)
        )
        current_bg_color = Style.BACKGROUND_COLOR
        if freeze_active:
            current_bg_color = (220, 220, 220) if (pygame.time.get_ticks() // 100) % 2 == 0 else (10, 10, 10)
        
        self.window.fill(current_bg_color)
        offset_y = self.offset_y
        ui_overlay_color = tuple(max(0, c - 20) for c in Style.BACKGROUND_COLOR) # Use base BG for UI overlay
        pygame.draw.rect(self.window, ui_overlay_color, (0, 0, self.window_width, offset_y))
        pygame.draw.rect(self.window, ui_overlay_color, (0, offset_y + self.env.render_size, self.window_width, offset_y))

        # ⭐️ 1. 調用技能的 render 方法 (在繪製球和球拍之前，讓技能效果如衝擊波畫在底層)
        # 繪製 Player 1 的技能效果
        if self.env.player1.skill_instance and (self.env.player1.skill_instance.is_active() or \
                                               (hasattr(self.env.player1.skill_instance, 'fadeout_active') and self.env.player1.skill_instance.fadeout_active) or \
                                               (hasattr(self.env.player1.skill_instance, 'fog_active') and self.env.player1.skill_instance.fog_active)): # 確保淡出等效果也能渲染
            if DEBUG_RENDERER and self.env.player1.skill_instance.is_active(): print(f"[SKILL_DEBUG][Renderer] Rendering P1 skill: {self.env.player1.skill_instance.__class__.__name__}")
            self.env.player1.skill_instance.render(self.window)

        # 繪製 Opponent 的技能效果
        if self.env.opponent.skill_instance and (self.env.opponent.skill_instance.is_active() or \
                                                 (hasattr(self.env.opponent.skill_instance, 'fadeout_active') and self.env.opponent.skill_instance.fadeout_active) or \
                                                 (hasattr(self.env.opponent.skill_instance, 'fog_active') and self.env.opponent.skill_instance.fog_active)):
            if DEBUG_RENDERER and self.env.opponent.skill_instance.is_active(): print(f"[SKILL_DEBUG][Renderer] Rendering Opponent skill: {self.env.opponent.skill_instance.__class__.__name__}")
            self.env.opponent.skill_instance.render(self.window)


        try:
            # 球的位置轉換
            cx_px = int(self.env.ball_x * self.env.render_size)
            cy_px = int(self.env.ball_y * self.env.render_size) + offset_y

            # 玩家1 球拍
            p1_paddle_color = self.env.player1.paddle_color # ⭐️ 使用 PlayerState 中的顏色
            p1_x_px = int(self.env.player1.x * self.env.render_size)
            p1_paddle_width_px = self.env.player1.paddle_width 
            p1_paddle_height_px = self.env.paddle_height_px
            pygame.draw.rect(self.window, p1_paddle_color if p1_paddle_color else Style.PLAYER_COLOR,
                (p1_x_px - p1_paddle_width_px // 2,
                 offset_y + self.env.render_size - p1_paddle_height_px,
                 p1_paddle_width_px, p1_paddle_height_px),
                border_radius=8
            )

            # 對手 球拍
            opponent_paddle_color = self.env.opponent.paddle_color # ⭐️ 使用 PlayerState 中的顏色
            opponent_x_px = int(self.env.opponent.x * self.env.render_size)
            opponent_paddle_width_px = self.env.opponent.paddle_width
            opponent_paddle_height_px = self.env.paddle_height_px
            pygame.draw.rect(self.window, opponent_paddle_color if opponent_paddle_color else Style.AI_COLOR,
                (opponent_x_px - opponent_paddle_width_px // 2,
                 offset_y, 
                 opponent_paddle_width_px, opponent_paddle_height_px),
                 border_radius=8
            )

            # 球的拖尾
            for i, (tx_norm, ty_norm) in enumerate(self.env.trail):
                # ... (拖尾繪製邏輯保持不變)
                fade = int(255 * (i + 1) / len(self.env.trail)) if len(self.env.trail) > 0 else 255
                base_ball_color_rgb = Style.BALL_COLOR[:3] if isinstance(Style.BALL_COLOR, tuple) and len(Style.BALL_COLOR) >=3 else (255,255,255)
                color = (*base_ball_color_rgb, fade) 
                trail_circle_radius_px = 4 
                temp_surf = pygame.Surface((trail_circle_radius_px * 2, trail_circle_radius_px * 2), pygame.SRCALPHA)
                pygame.draw.circle(temp_surf, color, (trail_circle_radius_px, trail_circle_radius_px), trail_circle_radius_px)
                trail_x_px = int(tx_norm * self.env.render_size)
                trail_y_px = int(ty_norm * self.env.render_size) + offset_y
                self.window.blit(temp_surf, (trail_x_px - trail_circle_radius_px, trail_y_px - trail_circle_radius_px))

            # 球的繪製和旋轉
            # ⭐️ 之後 SoulEaterBugSkill 可能會替換 self.ball_image
            # 目前 Renderer 自身的 self.ball_image 是基礎球體圖像
            # 如果技能要改變球的樣子，它應該修改 env.current_ball_display_image 之類的屬性
            # 或者 Renderer 在此處檢查是否有技能覆蓋球的圖像
            current_ball_render_image = self.ball_image # 預設使用 Renderer 的球圖像
            if hasattr(self.env, 'bug_skill_active') and self.env.bug_skill_active: # 舊的判斷方式，待改
                # 假設 SoulEaterBugSkill 會將其圖像放到 env.renderer.ball_image
                # 這不是個好設計，技能不應該直接操作 renderer 的內部圖像
                # 更好的方式是 env 有一個屬性指示當前球的視覺，Renderer 讀取那個
                pass # 暫時不處理 SoulEaterBug 的圖像替換

            if not (hasattr(self.env, 'bug_skill_active') and self.env.bug_skill_active):
                self.ball_angle += self.env.spin * 12 
            rotated_ball = pygame.transform.rotate(current_ball_render_image, self.ball_angle)
            rect = rotated_ball.get_rect(center=(cx_px, cy_px))
            self.window.blit(rotated_ball, rect)

            # 血條 (基本保持不變，已使用 PlayerState)
            bar_w_px, bar_h_px, spacing_px = 150, 20, 20
            current_time_ticks = pygame.time.get_ticks()
            # 對手 (上方) 血條
            pygame.draw.rect(self.window, Style.AI_BAR_BG, (self.window_width - bar_w_px - spacing_px, spacing_px, bar_w_px, bar_h_px))
            opp_flash = (current_time_ticks - self.env.opponent.last_hit_time < self.env.freeze_duration)
            opp_fill_color = (255,255,255) if (opp_flash and (current_time_ticks//100%2==0)) else Style.AI_BAR_FILL
            opponent_life_ratio = self.env.opponent.lives / self.env.opponent.max_lives if self.env.opponent.max_lives > 0 else 0
            pygame.draw.rect(self.window, opp_fill_color, (self.window_width - bar_w_px - spacing_px, spacing_px, bar_w_px * opponent_life_ratio, bar_h_px))
            # 玩家1 (下方) 血條
            player_bar_y_pos = self.window_height - offset_y + spacing_px 
            pygame.draw.rect(self.window, Style.PLAYER_BAR_BG, (spacing_px, player_bar_y_pos, bar_w_px, bar_h_px))
            p1_flash = (current_time_ticks - self.env.player1.last_hit_time < self.env.freeze_duration)
            p1_fill_color = (255,255,255) if (p1_flash and (current_time_ticks//100%2==0)) else Style.PLAYER_BAR_FILL
            player1_life_ratio = self.env.player1.lives / self.env.player1.max_lives if self.env.player1.max_lives > 0 else 0
            pygame.draw.rect(self.window, p1_fill_color, (spacing_px, player_bar_y_pos, bar_w_px * player1_life_ratio, bar_h_px))

        except AttributeError as e:
            if DEBUG_RENDERER: print(f"[Renderer.render] AttributeError: {e}")
            font = pygame.font.Font(None, 24); error_surf = font.render(f"Render Attr Err: {e}", True, (255,0,0)); self.window.blit(error_surf, (10, self.window_height // 2))
        except Exception as e:
            if DEBUG_RENDERER: print(f"[Renderer.render] Generic Render Error: {e}")
            font = pygame.font.Font(None, 24); error_surf = font.render(f"Unexpected Render Err", True, (255,0,0)); self.window.blit(error_surf, (10, self.window_height // 2 + 30))

        # ⭐️ 2. 繪製技能 UI (能量條、冷卻倒數) - 這部分是新增的，需要進一步完善
        self._render_skill_ui(self.env.player1, is_player1=True)
        self._render_skill_ui(self.env.opponent, is_player1=False)


        pygame.display.flip()
        self.clock.tick(60)

    def _render_skill_ui(self, player_state, is_player1):
        """輔助方法：為指定玩家繪製技能UI（能量條和冷卻）。"""
        if not player_state.skill_instance:
            return

        skill = player_state.skill_instance
        
        # 技能條尺寸和位置設定 (需要根據 P1 或 Opponent 調整位置)
        bar_width_px = 100
        bar_height_px = 10
        spacing_from_edge_px = 20
        text_offset_y_px = 15 # 文字在條下方多少像素

        if is_player1: # P1 的技能條在左下方 (示例位置)
            # bar_x_px = spacing_from_edge_px
            # bar_y_px = self.window_height - spacing_from_edge_px - bar_height_px - self.offset_y # 在下方UI區內
            # P1 血條位置: (sp, self.render_size+ offset_y+ sp, bar_w, bar_h)
            # 假設P1技能條在血條右側或下方
            p1_health_bar_x_end = spacing_from_edge_px + 150 # 假設血條寬150
            bar_x_px = p1_health_bar_x_end + spacing_from_edge_px
            bar_y_px = self.window_height - self.offset_y + spacing_from_edge_px # 與血條同高，在下方UI區
        else: # Opponent 的技能條在右上方 (示例位置)
            # bar_x_px = self.window_width - spacing_from_edge_px - bar_width_px
            # bar_y_px = spacing_from_edge_px # 在上方UI區內
            opp_health_bar_x_start = self.window_width - 150 - spacing_from_edge_px # 假設血條寬150
            bar_x_px = opp_health_bar_x_start - spacing_from_edge_px - bar_width_px
            bar_y_px = spacing_from_edge_px # 與血條同高，在上方UI區
        
        skill_to_render_ui_for = player_state.skill_instance # 清晰起見，換個名字
        
        # 獲取技能配置中的 bar_color
        # 使用 player_state.skill_code_name 來查找配置
        skill_cfg = SKILL_CONFIGS.get(player_state.skill_code_name, {})
        bar_fill_color_rgb = skill_cfg.get("bar_color", (200, 200, 200))
        bar_bg_color_rgb = (50,50,50)

        # 繪製背景條
        pygame.draw.rect(self.window, bar_bg_color_rgb, (bar_x_px, bar_y_px, bar_width_px, bar_height_px))

        # 繪製能量/冷卻進度條
        energy_ratio = skill.get_energy_ratio()
        current_bar_width = int(bar_width_px * energy_ratio)
        pygame.draw.rect(self.window, bar_fill_color_rgb, (bar_x_px, bar_y_px, current_bar_width, bar_height_px))

        # 顯示冷卻時間 (如果技能不在 active 狀態且正在冷卻)
        if not skill_to_render_ui_for.is_active(): # 使用 skill_to_render_ui_for
            cooldown_sec = skill_to_render_ui_for.get_cooldown_seconds() # 使用 skill_to_render_ui_for
            if cooldown_sec > 0:
                font = Style.get_font(14) # 使用 Style 統一獲取字體
                text_surf = font.render(f"{cooldown_sec:.1f}s", True, Style.TEXT_COLOR)
                text_rect = text_surf.get_rect(center=(bar_x_px + bar_width_px / 2, bar_y_px + bar_height_px + text_offset_y_px))
                self.window.blit(text_surf, text_rect)
                pass
        
        # TODO: 之後可以加入技能滿能量時的追跡光暈特效 (skill.has_full_energy_effect())
        # if skill.has_full_energy_effect() and energy_ratio >= 1.0 and not skill.is_active():
        #     # ... (繪製光暈效果) ...
        #     pass

    def close(self):
        if DEBUG_RENDERER: print("[Renderer.close] Closing Renderer.")
        # pygame.quit() # 已移除