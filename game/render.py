# game/render.py
import math
import pygame
from game.theme import Style
from game.settings import GameSettings

class Renderer:
    def __init__(self, env):
        pygame.init()
        self.env = env
        self.render_size = env.render_size
        self.offset_y = 100
        self.window = pygame.display.set_mode((self.render_size, self.render_size + 2 * self.offset_y))
        self.clock = pygame.time.Clock()
        self.ball_image = pygame.transform.smoothscale(
            pygame.image.load("assets/sunglasses.png").convert_alpha(),
            (env.ball_radius * 2, env.ball_radius * 2)
        )
        self.ball_angle = 0
        # 技能條追跡效果參數
        # 技能條追跡殘影效果參數
        self.skill_glow_position = 0
        self.skill_glow_trail = []  # 新增：殘影位置列表
        self.max_skill_glow_trail_length = 15  # 新增：殘影數量



    def render(self):
        freeze_active = self.env.freeze_timer > 0 and pygame.time.get_ticks() - self.env.freeze_timer < self.env.freeze_duration
        if freeze_active:
            if (pygame.time.get_ticks() // 100) % 2 == 0:  # 調慢頻率為100毫秒閃爍一次
                flash_color = (220, 220, 220)  # 略灰一點的白色，避免過亮
                self.window.fill(flash_color)
            else:
                self.window.fill((10, 10, 10))  # 黑色對比強烈的顏色
        else:
            self.window.fill(Style.BACKGROUND_COLOR)

        offset_y = self.offset_y

        # === 衝擊波觸發 ===
        active_skill = self.env.skills.get(self.env.active_skill_name)
        if active_skill and active_skill.is_active() and self.env.active_skill_name == "slowmo":

            if not hasattr(self.env, 'shockwaves'):
                self.env.shockwaves = []
            if not hasattr(self.env, 'last_slowmo_frame'):
                self.env.last_slowmo_frame = 0

            if self.env.last_slowmo_frame <= 0:
                cx = int(self.env.player_x * self.render_size)
                cy = int((1 - self.env.paddle_height / self.render_size) * self.render_size + offset_y)
                self.env.shockwaves.append({"cx": cx, "cy": cy, "radius": 0})
                self.env.last_slowmo_frame = 1
            else:
                self.env.last_slowmo_frame += 1
        else:
            self.env.last_slowmo_frame = 0
            # if hasattr(self.env, 'shockwaves'):
            #   del self.env.shockwaves

        # --- 修正後的衝擊波繪製與淡出 ---
        if hasattr(self.env, 'shockwaves') and self.env.shockwaves: # 檢查列表存在且非空
            # (確保這些變數在當前作用域可用)
            current_time = pygame.time.get_ticks()
            active_skill = self.env.skills.get(self.env.active_skill_name) # 獲取技能狀態

            # 計算淡出比例 (技能期間為 1.0，結束後逐漸變 0.0)
            remaining_ratio = 1.0
            # 檢查是否處於技能結束後的淡出階段
            if self.env.slowmo_fog_active and active_skill and not active_skill.is_active():
                 remaining_ratio = max(0.0, (self.env.slowmo_fog_end_time - current_time) / GameSettings.SLOWMO_FOG_DURATION_MS)

            # --- 主要邏輯：只有在比例 > 0 時才處理 ---
            if remaining_ratio > 0:
                # 原本衝擊波的基礎 Alpha 值
                base_fill_alpha = 80
                base_border_alpha = 200

                # 根據 remaining_ratio 計算最終的 Alpha 值
                final_fill_alpha = int(base_fill_alpha * remaining_ratio)
                final_border_alpha = int(base_border_alpha * remaining_ratio)

                # --- 次要邏輯：只有計算出的 alpha > 0 時才繪製和更新列表 ---
                if final_fill_alpha > 0 or final_border_alpha > 0:
                    next_shockwaves = []
                    for shockwave in self.env.shockwaves:
                        shockwave["radius"] += 30 # 半徑繼續擴大

                        # --- 繪製單個衝擊波 ---
                        # (確保 self.render_size 和 self.offset_y 可用)
                        overlay = pygame.Surface((self.render_size, self.render_size + 200), pygame.SRCALPHA)
                        fill_color = (50, 150, 255, final_fill_alpha)      # 使用計算後的 alpha
                        border_color = (255, 255, 255, final_border_alpha) # 使用計算後的 alpha
                        # (確保 shockwave["cx"], shockwave["cy"] 可用)
                        pygame.draw.circle(overlay, fill_color, (shockwave["cx"], shockwave["cy"]), shockwave["radius"])
                        pygame.draw.circle(overlay, border_color, (shockwave["cx"], shockwave["cy"]), shockwave["radius"], width=6)
                        self.window.blit(overlay, (0, 0))
                        # --- 繪製結束 ---

                        # 如果衝擊波還沒完全透明，就保留到下一幀
                        # 這個條件確保 alpha 為 0 的不會進入 next_shockwaves
                        if final_fill_alpha > 0 or final_border_alpha > 0:
                             next_shockwaves.append(shockwave)

                    self.env.shockwaves = next_shockwaves # 更新衝擊波列表
                else:
                    # 如果計算出的 alpha 為 0 (即使 ratio > 0，例如 ratio 極小導致 int 結果為 0)
                    # 立刻清空列表，確保不繪製透明的衝擊波
                    if hasattr(self.env, 'shockwaves'):
                         self.env.shockwaves.clear()
            else:
                 # 如果淡出比例 <= 0，清空列表
                 if hasattr(self.env, 'shockwaves'):
                      self.env.shockwaves.clear()
        # --- 衝擊波繪製區塊結束 ---

        # UI區塊背景
        active_skill = self.env.skills.get(self.env.active_skill_name)
        if active_skill and active_skill.is_active() and self.env.active_skill_name == "slowmo":
            ui_overlay_color = (20, 20, 100)
        else:
            ui_overlay_color = tuple(max(0, c - 20) for c in Style.BACKGROUND_COLOR)

        pygame.draw.rect(self.window, ui_overlay_color, (0, 0, self.render_size, offset_y))
        pygame.draw.rect(self.window, ui_overlay_color, (0, offset_y + self.render_size, self.render_size, offset_y))

        # 球與板子位置
        cx = int(self.env.ball_x * self.render_size)
        cy = int(self.env.ball_y * self.render_size) + offset_y
        px = int(self.env.player_x * self.render_size)
        ax = int(self.env.ai_x * self.render_size)

        # 拖尾渲染
        for i, (tx, ty) in enumerate(self.env.trail):
            fade = int(255 * (i + 1) / len(self.env.trail))
            trail_color = (*Style.BALL_COLOR, fade)
            trail_surface = pygame.Surface((self.render_size, self.render_size + 200), pygame.SRCALPHA)
            pygame.draw.circle(trail_surface, trail_color, (int(tx * self.render_size), int(ty * self.render_size) + offset_y), 4)
            self.window.blit(trail_surface, (0, 0))

        # 球的旋轉與顯示
        self.ball_angle += self.env.spin * 12
        rotated_ball = pygame.transform.rotate(self.ball_image, self.ball_angle)
        rotated_rect = rotated_ball.get_rect(center=(cx, cy))
        self.window.blit(rotated_ball, rotated_rect)
        
        # Slowmo 技能板子殘影效果（完整且清晰新增這整段）
        active_skill = self.env.skills.get(self.env.active_skill_name, None)

        if active_skill and active_skill.is_active() and self.env.active_skill_name == "slowmo":
            for i, trail_x in enumerate(self.env.player_trail):
                fade_ratio = (i + 1) / len(self.env.player_trail)
                trail_alpha = int(200 * fade_ratio)  # 透明度逐漸加深

                # 創建透明Surface繪製殘影
                trail_surface = pygame.Surface(
                    (self.env.player_paddle_width, self.env.paddle_height), 
                    pygame.SRCALPHA
                )
                # 使用settings中的顏色
                trail_color = (*GameSettings.SLOWMO_TRAIL_COLOR, trail_alpha)
                trail_surface.fill(trail_color)

                trail_rect = trail_surface.get_rect(center=(
                    int(trail_x * self.render_size),
                    offset_y + self.render_size - self.env.paddle_height // 2
                ))

                self.window.blit(trail_surface, trail_rect)

        # ---⭐ Slowmo板子特效 (修改後) ⭐---
        paddle_color = self.env.paddle_color or Style.PLAYER_COLOR # 保留板子顏色設定

        # 獲取 slowmo 技能狀態
        slowmo_skill = self.env.skills.get('slowmo')
        current_time = pygame.time.get_ticks() # 獲取當前時間

        # 效果 2: 光圈淡出 (原霧氣的位置，技能結束後顯示)
        # 條件：需要環境中的計時器 (slowmo_fog_active) 且技能已結束
        if self.env.slowmo_fog_active and slowmo_skill and not slowmo_skill.is_active(): # <--- 條件：技能剛結束且計時器作用中
            remaining_ratio = max(0.0, (self.env.slowmo_fog_end_time - current_time) / GameSettings.SLOWMO_FOG_DURATION_MS)

        # --- (特效區塊修改完畢) ---

        # 板子本體繪製 (帶顏色變化)
        pygame.draw.rect(self.window, paddle_color, (
            px - self.env.player_paddle_width // 2,
            offset_y + self.render_size - self.env.paddle_height,
            self.env.player_paddle_width,
            self.env.paddle_height
        ), border_radius=8)

        pygame.draw.rect(self.window, Style.AI_COLOR, (
            ax - self.env.ai_paddle_width // 2,
            offset_y,
            self.env.ai_paddle_width,
            self.env.paddle_height
        ))

        # 血條顯示
        bar_width, bar_height, spacing = 150, 20, 20
        current_time = pygame.time.get_ticks()

        # === AI 血條 ===
        # 背景 (底色)
        pygame.draw.rect(self.window, Style.AI_BAR_BG, (
            self.render_size - bar_width - spacing,
            spacing,
            bar_width,
            bar_height
        ))

        # 閃爍效果 (扣血時，使用時間判斷)
        ai_flash = current_time - self.env.last_ai_hit_time < self.env.freeze_duration
        ai_bar_color = (255, 255, 255) if ai_flash and (current_time // 100 % 2 == 0) else Style.AI_BAR_FILL

        # 前景 (血量)
        pygame.draw.rect(self.window, ai_bar_color, (
            self.render_size - bar_width - spacing,
            spacing,
            bar_width * (self.env.ai_life / self.env.ai_max_life),
            bar_height
        ))

        # === 玩家 血條 ===
        # 背景 (底色)
        pygame.draw.rect(self.window, Style.PLAYER_BAR_BG, (
            spacing,
            self.render_size + offset_y + spacing,
            bar_width,
            bar_height
        ))

        # 閃爍效果 (扣血時，使用時間判斷)
        player_flash = current_time - self.env.last_player_hit_time < self.env.freeze_duration
        player_bar_color = (255, 255, 255) if player_flash and (current_time // 100 % 2 == 0) else Style.PLAYER_BAR_FILL

        # 前景 (血量)
        pygame.draw.rect(self.window, player_bar_color, (
            spacing,
            self.render_size + offset_y + spacing,
            bar_width * (self.env.player_life / self.env.player_max_life),
            bar_height
        ))



        # 技能條
        slow_bar_width, slow_bar_height, slow_bar_spacing = 100, 10, 20
        slow_bar_x = self.render_size - slow_bar_width - slow_bar_spacing
        slow_bar_y = self.render_size + offset_y + self.env.paddle_height + slow_bar_spacing
        pygame.draw.rect(self.window, (50, 50, 50), (slow_bar_x, slow_bar_y, slow_bar_width, slow_bar_height))
        
        active_skill = self.env.skills[self.env.active_skill_name]

        # 根據技能名稱調整顏色
        skill_colors = {
            'slowmo': GameSettings.SLOWMO_BAR_COLOR,
            'long_paddle': GameSettings.LONG_PADDLE_BAR_COLOR,
        }

        bar_color = skill_colors.get(self.env.active_skill_name, (255, 255, 255))  # 預設白色避免錯誤

        pygame.draw.rect(
            self.window,
            bar_color,
            (slow_bar_x, slow_bar_y, slow_bar_width * active_skill.get_energy_ratio(), slow_bar_height)
        )

        # 顯示冷卻時間
        cooldown_seconds = active_skill.get_cooldown_seconds()

        if not active_skill.is_active() and cooldown_seconds > 0:
            cooldown_text = f"{cooldown_seconds:.1f}"

            cooldown_font = Style.get_font(14)
            cooldown_surface = cooldown_font.render(cooldown_text, True, Style.TEXT_COLOR)

            cooldown_rect = cooldown_surface.get_rect(center=(
                slow_bar_x + slow_bar_width / 2,
                slow_bar_y + slow_bar_height + 15
            ))

            self.window.blit(cooldown_surface, cooldown_rect)



        # 技能滿能量時的追跡線效果（加入殘影）
        active_skill = self.env.skills[self.env.active_skill_name]
        if active_skill.has_full_energy_effect():

            glow_rect = pygame.Rect(slow_bar_x - 2, slow_bar_y - 2, slow_bar_width + 4, slow_bar_height + 4)

            # 更新追跡線位置
            self.skill_glow_position = (self.skill_glow_position + 8) % ((glow_rect.width + glow_rect.height) * 2)

            pos = self.skill_glow_position

            # 計算光點位置
            if pos <= glow_rect.width:
                glow_pos = (glow_rect.x + pos, glow_rect.y)
            elif pos <= glow_rect.width + glow_rect.height:
                glow_pos = (glow_rect.x + glow_rect.width, glow_rect.y + (pos - glow_rect.width))
            elif pos <= glow_rect.width * 2 + glow_rect.height:
                glow_pos = (glow_rect.x + glow_rect.width - (pos - glow_rect.width - glow_rect.height), glow_rect.y + glow_rect.height)
            else:
                glow_pos = (glow_rect.x, glow_rect.y + glow_rect.height - (pos - 2 * glow_rect.width - glow_rect.height))

            # 加入殘影座標列表
            self.skill_glow_trail.append(glow_pos)
            if len(self.skill_glow_trail) > self.max_skill_glow_trail_length:
                self.skill_glow_trail.pop(0)

            # 畫外框
            active_skill = self.env.skills[self.env.active_skill_name]

            # 根據技能名稱調整顏色
            skill_colors = {
                'slowmo': GameSettings.SLOWMO_BAR_COLOR,
                'long_paddle': GameSettings.LONG_PADDLE_BAR_COLOR,
            }

            bar_color = skill_colors.get(self.env.active_skill_name, (255, 255, 255))  # 預設白色避免錯誤

            pygame.draw.rect(
                self.window,
                bar_color,
                (slow_bar_x, slow_bar_y, slow_bar_width * active_skill.get_energy_ratio(), slow_bar_height)
            )

            # 顯示冷卻時間
            cooldown_seconds = active_skill.get_cooldown_seconds()

            if not active_skill.is_active() and cooldown_seconds > 0:
                cooldown_text = f"{cooldown_seconds:.1f}"

                cooldown_font = Style.get_font(14)
                cooldown_surface = cooldown_font.render(cooldown_text, True, Style.TEXT_COLOR)

                cooldown_rect = cooldown_surface.get_rect(center=(
                    slow_bar_x + slow_bar_width / 2,
                    slow_bar_y + slow_bar_height + 15
                ))

                self.window.blit(cooldown_surface, cooldown_rect)


            # 畫拖曳殘影效果
            for i, pos in enumerate(self.skill_glow_trail):
                alpha = int(255 * (i + 1) / len(self.skill_glow_trail))  # 透明度漸增
                trail_color = (255, 255, 255, alpha)
                trail_surface = pygame.Surface((self.render_size, self.render_size + 200), pygame.SRCALPHA)
                pygame.draw.circle(trail_surface, trail_color, pos, 4)
                self.window.blit(trail_surface, (0, 0))
        else:
            self.skill_glow_position = 0  # 重置光點位置
            self.skill_glow_trail.clear()  # 清除殘影

            
        # === Slowmo技能時鐘特效 (修改後，加入淡出) ===
        active_skill = self.env.skills.get(self.env.active_skill_name) # 獲取技能狀態
        current_time = pygame.time.get_ticks() # 獲取當前時間

        # --- 修改條件：技能期間 或 技能結束後的淡出期間 都可能需要繪製 ---
        should_draw_clock = False
        if active_skill and self.env.active_skill_name == "slowmo":
             if active_skill.is_active():
                 should_draw_clock = True # 技能期間要畫
             elif self.env.slowmo_fog_active: # 檢查是否在淡出計時器期間
                 should_draw_clock = True # 技能剛結束、淡出期間也要畫

        if should_draw_clock:
            # --- 計算時鐘的 Alpha 和角度 ---
            clock_alpha_ratio = 1.0 # 預設完全不透明

            # 如果不在技能期間，但在淡出期間，計算淡出比例
            if not active_skill.is_active() and self.env.slowmo_fog_active:
                clock_alpha_ratio = max(0.0, (self.env.slowmo_fog_end_time - current_time) / GameSettings.SLOWMO_FOG_DURATION_MS)

            # 獲取時鐘基礎顏色和 Alpha
            base_clock_color_rgb = GameSettings.SLOWMO_CLOCK_COLOR[:3]
            base_clock_alpha = GameSettings.SLOWMO_CLOCK_COLOR[3] # 原設定值 (100)

            # 計算最終 Alpha
            final_clock_alpha = int(base_clock_alpha * clock_alpha_ratio)

            # --- 只有 Alpha > 0 時才繪製 ---
            if final_clock_alpha > 0:
                # 計算能量比例和角度 (如果技能已結束，energy_ratio 會是 0)
                # 讓指針停在結束位置或 0 的位置
                energy_ratio = active_skill.get_energy_ratio() if active_skill.is_active() else 0
                angle_deg = (1 - energy_ratio) * 360
                angle_rad = math.radians(angle_deg)

                # 時鐘位置
                clock_center = (self.render_size // 2, self.render_size // 2)

                # --- 繪製時鐘背景圓圈 (使用計算後的 Alpha) ---
                clock_surface = pygame.Surface((GameSettings.SLOWMO_CLOCK_RADIUS * 2 + 10,
                                                GameSettings.SLOWMO_CLOCK_RADIUS * 2 + 10), pygame.SRCALPHA)
                final_clock_color = (*base_clock_color_rgb, final_clock_alpha)
                pygame.draw.circle(
                    clock_surface,
                    final_clock_color, # 使用帶 Alpha 的顏色
                    (GameSettings.SLOWMO_CLOCK_RADIUS + 5, GameSettings.SLOWMO_CLOCK_RADIUS + 5),
                    GameSettings.SLOWMO_CLOCK_RADIUS
                )

                # --- 繪製時鐘指針 (使用計算後的 Alpha) ---
                # 讓指針也一起淡出 (從 255 開始淡出)
                final_needle_alpha = int(255 * clock_alpha_ratio)
                final_needle_color = (255, 255, 255, final_needle_alpha)

                needle_length = GameSettings.SLOWMO_CLOCK_RADIUS - 5
                needle_end_pos = (
                    (GameSettings.SLOWMO_CLOCK_RADIUS + 5) + needle_length * math.cos(angle_rad - math.pi/2),
                    (GameSettings.SLOWMO_CLOCK_RADIUS + 5) + needle_length * math.sin(angle_rad - math.pi/2)
                )
                pygame.draw.line(
                    clock_surface,
                    final_needle_color, # 使用帶 Alpha 的指針顏色
                    (GameSettings.SLOWMO_CLOCK_RADIUS + 5, GameSettings.SLOWMO_CLOCK_RADIUS + 5),
                    needle_end_pos,
                    GameSettings.SLOWMO_CLOCK_LINE_WIDTH
                )

                # --- 將時鐘渲染到主畫面 ---
                clock_rect = clock_surface.get_rect(center=clock_center)
                self.window.blit(clock_surface, clock_rect)
        # === 時鐘特效區塊結束 ===

        pygame.display.flip()
        self.clock.tick(60)

    def close(self):
        pygame.quit()