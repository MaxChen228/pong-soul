# game/render.py

import math
import pygame
from game.theme import Style
from game.settings import GameSettings
# from game.skills.skill_config import SKILL_CONFIGS # 暫時不用
from utils import resource_path

DEBUG_RENDERER = True # ⭐️ 除錯開關

class Renderer:
    def __init__(self, env): # env 是 PongDuelEnv 的實例
        if DEBUG_RENDERER: print("[Renderer.__init__] Initializing Renderer...")
        pygame.init() # 確保 Pygame 在此處也初始化，儘管 main.py 已做
        self.env = env
        self.render_size = env.render_size # 遊戲區域的邏輯大小
        self.offset_y = 100 # 上下UI區域的高度，可考慮移到 Style 或 GameSettings
        
        # 創建視窗
        # 注意：視窗的總高度是 render_size (遊戲區) + 2 * offset_y (上下UI區)
        # PongDuelEnv 中的 render_size 主要指遊戲核心區域的寬度和高度基準
        # 而 Renderer 創建的視窗是包含UI的總視窗
        self.window_width = self.render_size
        self.window_height = self.render_size + 2 * self.offset_y
        self.window = pygame.display.set_mode((self.window_width, self.window_height))
        pygame.display.set_caption("Pong Soul (Renderer Initialized)") # 更改標題以確認

        self.clock = pygame.time.Clock()

        # 球的圖片資源加載
        # ⭐️ 使用 env.ball_radius_px 替換 env.ball_radius
        if DEBUG_RENDERER: print(f"[Renderer.__init__] Loading ball image. env.ball_radius_px: {env.ball_radius_px}")
        try:
            ball_diameter_px = int(env.ball_radius_px * 2)
            if ball_diameter_px <= 0:
                if DEBUG_RENDERER: print(f"[Renderer.__init__] Warning: ball_diameter_px is {ball_diameter_px}. Setting to default 20.")
                ball_diameter_px = 20 # 提供一個預設值以避免 transform 錯誤

            self.ball_image_original = pygame.image.load(resource_path("assets/sunglasses.png")).convert_alpha()
            self.ball_image = pygame.transform.smoothscale(
                self.ball_image_original,
                (ball_diameter_px, ball_diameter_px)
            )
        except pygame.error as e:
            if DEBUG_RENDERER: print(f"[Renderer.__init__] Pygame error loading or scaling ball image: {e}")
            # 創建一個預設的圓形 surface 作為備用球體圖像
            ball_diameter_px = int(env.ball_radius_px * 2) if env.ball_radius_px * 2 > 0 else 20
            self.ball_image = pygame.Surface((ball_diameter_px, ball_diameter_px), pygame.SRCALPHA)
            pygame.draw.circle(self.ball_image, (255, 255, 255), (ball_diameter_px // 2, ball_diameter_px // 2), ball_diameter_px // 2)
            if DEBUG_RENDERER: print(f"[Renderer.__init__] Created fallback ball image.")
        except Exception as e:
            if DEBUG_RENDERER: print(f"[Renderer.__init__] Generic error loading or scaling ball image: {e}")
            # 通用錯誤處理
            ball_diameter_px = 20 # Default size
            self.ball_image = pygame.Surface((ball_diameter_px, ball_diameter_px), pygame.SRCALPHA)
            pygame.draw.circle(self.ball_image, (255, 0, 0), (ball_diameter_px // 2, ball_diameter_px // 2), ball_diameter_px // 2) # 紅色表示錯誤
            if DEBUG_RENDERER: print(f"[Renderer.__init__] Created ERROR ball image.")


        self.ball_angle = 0 # 用於球體旋轉動畫

        # 共用的 技能條特效 (暫時保留，後續階段處理與 PlayerState 的技能綁定)
        self.skill_glow_position = 0
        self.skill_glow_trail = []
        self.max_skill_glow_trail_length = 15

        if DEBUG_RENDERER: print("[Renderer.__init__] Renderer initialization complete.")

    def render(self):
        # ⭐️⭐️⭐️ 重要提示：此 render 方法尚未更新以使用 env.player1 和 env.opponent ⭐️⭐️⭐️
        # ⭐️⭐️⭐️ 它仍然依賴舊的 env.player_x, env.ai_x 等屬性，這將在下一階段修正 ⭐️⭐️⭐️
        # ⭐️⭐️⭐️ 目前的目標是先解決 __init__ 的錯誤讓遊戲能啟動並看到畫面 ⭐️⭐️⭐️
        if not self.env: # 基本檢查
            if DEBUG_RENDERER: print("[Renderer.render] Error: self.env is not set.")
            return

        freeze_active = (
            self.env.freeze_timer > 0
            and (pygame.time.get_ticks() - self.env.freeze_timer < self.env.freeze_duration)
        )
        if freeze_active:
            if (pygame.time.get_ticks() // 100) % 2 == 0:
                self.window.fill((220, 220, 220))
            else:
                self.window.fill((10, 10, 10))
        else:
            self.window.fill(Style.BACKGROUND_COLOR)

        offset_y = self.offset_y

        # UI 區域背景 (暫時保留簡單繪製)
        ui_overlay_color = tuple(max(0, c - 20) for c in Style.BACKGROUND_COLOR)
        pygame.draw.rect(self.window, ui_overlay_color, (0, 0, self.window_width, offset_y))
        pygame.draw.rect(self.window, ui_overlay_color, (0, offset_y + self.env.render_size, self.window_width, offset_y))

        # === 球與板子位置 (使用舊的屬性訪問方式，待修正) ===
        # 這些 env 的直接屬性訪問會在下一階段修正為 env.player1.x, env.opponent.x 等
        try:
            # 球的位置轉換 (歸一化 -> 像素)
            cx_px = int(self.env.ball_x * self.env.render_size)
            cy_px = int(self.env.ball_y * self.env.render_size) + offset_y # 加上上方UI區域的偏移

            # 玩家1 球拍位置 (下方)
            # 舊: self.env.player_x (歸一化), self.env.player_paddle_width (像素)
            # 新: self.env.player1.x (歸一化), self.env.player1.paddle_width (像素)
            p1_x_px = int(self.env.player1.x * self.env.render_size) # ⭐️嘗試使用新的
            p1_paddle_width_px = self.env.player1.paddle_width       # ⭐️嘗試使用新的
            p1_paddle_height_px = self.env.paddle_height_px

            pygame.draw.rect(self.window, Style.PLAYER_COLOR, # 顏色之後也可能來自 PlayerState
                (p1_x_px - p1_paddle_width_px // 2,
                 offset_y + self.env.render_size - p1_paddle_height_px, # Y 座標在遊戲區底部
                 p1_paddle_width_px, p1_paddle_height_px),
                border_radius=8
            )

            # 對手 球拍位置 (上方)
            # 舊: self.env.ai_x (歸一化), self.env.ai_paddle_width (像素)
            # 新: self.env.opponent.x (歸一化), self.env.opponent.paddle_width (像素)
            opponent_x_px = int(self.env.opponent.x * self.env.render_size) # ⭐️嘗試使用新的
            opponent_paddle_width_px = self.env.opponent.paddle_width       # ⭐️嘗試使用新的
            opponent_paddle_height_px = self.env.paddle_height_px

            pygame.draw.rect(self.window, Style.AI_COLOR, # 顏色之後也可能來自 PlayerState
                (opponent_x_px - opponent_paddle_width_px // 2,
                 offset_y, # Y 座標在遊戲區頂部 (UI之下)
                 opponent_paddle_width_px, opponent_paddle_height_px),
                 border_radius=8 # 假設對手也有圓角
            )


            # 球的拖尾 (使用歸一化座標繪製，然後轉換)
            for i, (tx_norm, ty_norm) in enumerate(self.env.trail):
                fade = int(255 * (i + 1) / len(self.env.trail)) if len(self.env.trail) > 0 else 255
                color = (*Style.BALL_COLOR[:3], fade) # 確保 BALL_COLOR 是 RGB 或 RGBA
                
                # 創建一個臨時的透明表面來繪製帶 alpha 的圓形
                # 尺寸可以優化，不需要每次都創建全螢幕大小的 surface
                trail_circle_radius_px = 4 # 拖尾點的半徑
                temp_surf = pygame.Surface((trail_circle_radius_px * 2, trail_circle_radius_px * 2), pygame.SRCALPHA)
                pygame.draw.circle(temp_surf, color, (trail_circle_radius_px, trail_circle_radius_px), trail_circle_radius_px)
                
                # 計算繪製位置
                trail_x_px = int(tx_norm * self.env.render_size)
                trail_y_px = int(ty_norm * self.env.render_size) + offset_y
                self.window.blit(temp_surf, (trail_x_px - trail_circle_radius_px, trail_y_px - trail_circle_radius_px))


            # 球的繪製和旋轉
            current_display_image = self.ball_image # 之後技能系統可能會改變這個圖像
            if not (hasattr(self.env, 'bug_skill_active') and self.env.bug_skill_active): # 假設 bug_skill_active 還是舊的判斷方式
                self.ball_angle += self.env.spin * 12 # 根據 spin 值計算旋轉角度
            rotated_ball_or_bug = pygame.transform.rotate(current_display_image, self.ball_angle)
            rect = rotated_ball_or_bug.get_rect(center=(cx_px, cy_px))
            self.window.blit(rotated_ball_or_bug, rect)


            # 血條 (嘗試使用新的 PlayerState 結構)
            bar_w_px, bar_h_px, spacing_px = 150, 20, 20 # 像素單位
            current_time_ticks = pygame.time.get_ticks()

            # 對手 (上方) 血條
            pygame.draw.rect(self.window, Style.AI_BAR_BG, # 背景顏色
                (self.window_width - bar_w_px - spacing_px, spacing_px, # X, Y 位置 (在上方UI區)
                 bar_w_px, bar_h_px)
            )
            opp_flash = (current_time_ticks - self.env.opponent.last_hit_time < self.env.freeze_duration) # 假設 PlayerState 有 last_hit_time
            opp_fill_color = (255,255,255) if (opp_flash and (current_time_ticks//100%2==0)) else Style.AI_BAR_FILL
            opponent_life_ratio = self.env.opponent.lives / self.env.opponent.max_lives if self.env.opponent.max_lives > 0 else 0
            pygame.draw.rect(self.window, opp_fill_color, (
                self.window_width - bar_w_px - spacing_px, spacing_px,
                bar_w_px * opponent_life_ratio, bar_h_px
            ))

            # 玩家1 (下方) 血條
            player_bar_y_pos = self.window_height - offset_y + spacing_px # 在下方UI區的Y位置
            pygame.draw.rect(self.window, Style.PLAYER_BAR_BG,
                (spacing_px, player_bar_y_pos, bar_w_px, bar_h_px)
            )
            p1_flash = (current_time_ticks - self.env.player1.last_hit_time < self.env.freeze_duration)
            p1_fill_color = (255,255,255) if (p1_flash and (current_time_ticks//100%2==0)) else Style.PLAYER_BAR_FILL
            player1_life_ratio = self.env.player1.lives / self.env.player1.max_lives if self.env.player1.max_lives > 0 else 0
            pygame.draw.rect(self.window, p1_fill_color, (
                spacing_px, player_bar_y_pos,
                bar_w_px * player1_life_ratio, bar_h_px
            ))

        except AttributeError as e:
            if DEBUG_RENDERER: print(f"[Renderer.render] AttributeError during rendering: {e}. This likely means PongDuelEnv attributes need updating in Renderer.")
            # 可以在這裡畫一個錯誤提示到螢幕上
            font = pygame.font.Font(None, 24) # 使用 Pygame 預設字體
            error_surf = font.render(f"Render Error: {e}", True, (255,0,0))
            self.window.blit(error_surf, (10, self.window_height // 2))
        except Exception as e:
            if DEBUG_RENDERER: print(f"[Renderer.render] Generic error during rendering: {e}")
            font = pygame.font.Font(None, 24)
            error_surf = font.render(f"Unexpected Render Error", True, (255,0,0))
            self.window.blit(error_surf, (10, self.window_height // 2))


        # 技能相關的渲染 (階段二處理)
        # ...

        pygame.display.flip()
        self.clock.tick(60) # 控制幀率

    def close(self):
        if DEBUG_RENDERER: print("[Renderer.close] Closing Renderer and Pygame.")