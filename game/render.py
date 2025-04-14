# game/render.py
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
        if self.env.time_slow_active:
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
            if hasattr(self.env, 'shockwaves'):
                del self.env.shockwaves

        # 畫衝擊波
        if hasattr(self.env, 'shockwaves'):
            for shockwave in self.env.shockwaves:
                shockwave["radius"] += 30
                overlay = pygame.Surface((self.render_size, self.render_size + 200), pygame.SRCALPHA)
                pygame.draw.circle(overlay, (50, 150, 255, 80), (shockwave["cx"], shockwave["cy"]), shockwave["radius"])
                pygame.draw.circle(overlay, (255, 255, 255, 200), (shockwave["cx"], shockwave["cy"]), shockwave["radius"], width=6)
                self.window.blit(overlay, (0, 0))

        # UI區塊背景
        ui_overlay_color = (20, 20, 100) if self.env.time_slow_active else tuple(max(0, c - 20) for c in Style.BACKGROUND_COLOR)
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

        # 畫板子
        pygame.draw.rect(self.window, Style.PLAYER_COLOR, (
            px - self.env.player_paddle_width // 2,
            offset_y + self.render_size - self.env.paddle_height,
            self.env.player_paddle_width,
            self.env.paddle_height
        ))
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
        if self.env.time_slow_energy >= 1.0:
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

        pygame.display.flip()
        self.clock.tick(60)

    def close(self):
        pygame.quit()