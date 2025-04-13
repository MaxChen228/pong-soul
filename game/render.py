# game/render.py
import pygame
from game.theme import Style

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

    def render(self):
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
                shockwave["radius"] += 60
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
        pygame.draw.rect(self.window, Style.AI_BAR_BG, (self.render_size - bar_width - spacing, spacing, bar_width, bar_height))
        pygame.draw.rect(self.window, Style.AI_BAR_FILL, (self.render_size - bar_width - spacing, spacing, bar_width * (self.env.ai_life / self.env.ai_max_life), bar_height))
        pygame.draw.rect(self.window, Style.PLAYER_BAR_BG, (spacing, self.render_size + offset_y + spacing, bar_width, bar_height))
        pygame.draw.rect(self.window, Style.PLAYER_BAR_FILL, (spacing, self.render_size + offset_y + spacing, bar_width * (self.env.player_life / self.env.player_max_life), bar_height))

        # 技能條
        slow_bar_width, slow_bar_height, slow_bar_spacing = 100, 10, 20
        slow_bar_x = self.render_size - slow_bar_width - slow_bar_spacing
        slow_bar_y = self.render_size + offset_y + self.env.paddle_height + slow_bar_spacing
        pygame.draw.rect(self.window, (50, 50, 50), (slow_bar_x, slow_bar_y, slow_bar_width, slow_bar_height))
        pygame.draw.rect(self.window, (0, 200, 255), (slow_bar_x, slow_bar_y, slow_bar_width * self.env.time_slow_energy, slow_bar_height))

        pygame.display.flip()
        self.clock.tick(60)

    def close(self):
        pygame.quit()