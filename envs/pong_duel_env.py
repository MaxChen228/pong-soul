import gym
from gym import spaces
import numpy as np
import pygame
import random
from game.theme import Style 

class PongDuelEnv(gym.Env):
    def __init__(self, render_size=400, paddle_width=60, paddle_height=10, ball_radius=10):
        super().__init__()

        self.render_size = render_size
        self.paddle_width = paddle_width
        self.paddle_height = paddle_height
        self.ball_radius = ball_radius

        self.player_x = 0.5
        self.ai_x = 0.5

        self.ball_x = 0.5
        self.ball_y = 0.5
        self.ball_vx = 0.02
        self.ball_vy = -0.02

        self.enable_spin = True
        self.magnus_factor = 0.01
        self.spin = 0

        self.speed_scale_every = 3
        self.speed_increment = 0.005
        self.bounces = 0

        self.trail = []
        self.max_trail_length = 20

        self.initial_direction = "down"
        self.initial_angle_deg = 15
        self.initial_angle_range = None
        self.initial_speed = 0.02

        self.player_life = 3
        self.ai_life = 3
        self.max_life = 3

        self.observation_space = spaces.Box(
            low=np.array([0, 0, -1, -1, 0, 0], dtype=np.float32),
            high=np.array([1, 1, 1, 1, 1, 1], dtype=np.float32)
        )
        self.action_space = spaces.Discrete(3)

        self.window = None
        self.clock = None

    def set_params_from_config(self, config):
        self.speed_increment = config.get('speed_increment', 0.005)
        self.speed_scale_every = config.get('speed_scale_every', 3)
        self.enable_spin = config.get('enable_spin', True)
        self.magnus_factor = config.get('magnus_factor', 0.01)
        self.initial_speed = config.get('initial_speed', 0.02)
        self.initial_angle_deg = config.get('initial_angle_deg', 15)
        self.initial_angle_range = config.get('initial_angle_deg_range', None)
        self.initial_direction = config.get('initial_direction', 'down')

        self.player_life = config.get('player_life', 3)
        self.ai_life = config.get('ai_life', 3)
        self.player_max_life = config.get('player_max_life', self.player_life)
        self.ai_max_life = config.get('ai_max_life', self.ai_life)

        self.player_paddle_width = config.get('player_paddle_width', 60)
        self.ai_paddle_width = config.get('ai_paddle_width', 60)

    def reset(self):
        self.bounces = 0
        self.player_x = 0.5
        self.ai_x = 0.5

        # 決定角度
        if self.initial_angle_range:
            angle_deg = random.uniform(*self.initial_angle_range)
        else:
            angle_deg = self.initial_angle_deg
        angle_rad = np.radians(angle_deg)

        # 確定發球方向邏輯：y 軸朝下為正方向
        if self.initial_direction == "down":
            self.ball_y = (self.paddle_height / self.render_size) + 0.05  # 從 AI 下方開始
            vy_sign = 1  # 正的 vy = 往下（pygame y 軸正向）
            print("👾 發球方向：DOWN")
        else:
            self.ball_y = 1 - (self.paddle_height / self.render_size) - 0.05  # 從玩家上方開始
            vy_sign = -1  # 負的 vy = 往上
            print("👾 發球方向：UP")

        # 水平位置可固定在中間或稍偏
        self.ball_x = 0.5

        # 球速
        self.ball_vx = self.initial_speed * np.sin(angle_rad)
        self.ball_vy = self.initial_speed * np.cos(angle_rad) * vy_sign

        # 調試輸出
        print(f"🟡 初始位置: ({self.ball_x:.2f}, {self.ball_y:.2f})")
        print(f"🟢 初始速度: vx={self.ball_vx:.4f}, vy={self.ball_vy:.4f}")

        self.spin = 0
        return self._get_obs(), {}




    def _get_obs(self):
        return np.array([
            self.ball_x,
            self.ball_y,
            self.ball_vx,
            self.ball_vy,
            self.player_x,
            self.ai_x
        ], dtype=np.float32)

    def get_lives(self):
        return self.player_life, self.ai_life

    def _scale_difficulty(self):
        factor = 1 + (self.bounces // self.speed_scale_every) * self.speed_increment
        self.ball_vx *= factor
        self.ball_vy *= factor

    def step(self, player_action, ai_action):
        old_ball_x = self.ball_x
        old_ball_y = self.ball_y

        if player_action == 0:
            self.player_x -= 0.03
        elif player_action == 2:
            self.player_x += 0.03

        if ai_action == 0:
            self.ai_x -= 0.03
        elif ai_action == 2:
            self.ai_x += 0.03

        self.player_x = np.clip(self.player_x, 0.0, 1.0)
        self.ai_x = np.clip(self.ai_x, 0.0, 1.0)

        if self.enable_spin:
            self.ball_vx += self.magnus_factor * self.spin * self.ball_vy

        self.ball_x += self.ball_vx
        self.ball_y += self.ball_vy
        self.trail.append((self.ball_x, self.ball_y))
        if len(self.trail) > self.max_trail_length:
            self.trail.pop(0)

        if self.ball_x <= 0 or self.ball_x >= 1:
            self.ball_vx *= -1

        reward = 0

        ai_y = self.paddle_height / self.render_size
        ai_half_width = self.ai_paddle_width / self.render_size / 2

        if old_ball_y > ai_y and self.ball_y <= ai_y:
            if abs(self.ball_x - self.ai_x) < ai_half_width:
                self.ball_y = ai_y
                self.ball_vy *= -1
                self.bounces += 1
                self._scale_difficulty()
                self.spin = -1 if ai_action == 2 else (1 if ai_action == 0 else 0)
            else:
                self.ai_life -= 1
                reward = 1
                return self._get_obs(), reward, True, False, {}

        player_y = 1 - self.paddle_height / self.render_size
        player_half_width = self.player_paddle_width / self.render_size / 2

        if old_ball_y < player_y and self.ball_y >= player_y:
            if abs(self.ball_x - self.player_x) < player_half_width:
                self.ball_y = player_y
                self.ball_vy *= -1
                self.bounces += 1
                self._scale_difficulty()
                self.spin = -1 if player_action == 0 else (1 if player_action == 2 else 0)
            else:
                self.player_life -= 1
                reward = -1
                return self._get_obs(), reward, True, False, {}

        return self._get_obs(), reward, False, False, {}

    def render(self):
        if not self.window:
            pygame.init()
            self.window = pygame.display.set_mode((self.render_size, self.render_size + 200))
            self.clock = pygame.time.Clock()

        self.window.fill(Style.BACKGROUND_COLOR)
        offset_y = 100
        ui_overlay_color = tuple(max(0, c - 20) for c in Style.BACKGROUND_COLOR)

        pygame.draw.rect(self.window, ui_overlay_color, (0, 0, self.render_size, offset_y))
        pygame.draw.rect(self.window, ui_overlay_color, (0, offset_y + self.render_size, self.render_size, offset_y))

        cx = int(self.ball_x * self.render_size)
        cy = int(self.ball_y * self.render_size) + offset_y
        px = int(self.player_x * self.render_size)
        ax = int(self.ai_x * self.render_size)

        for i, (tx, ty) in enumerate(self.trail):
            fade = int(255 * (i + 1) / len(self.trail))
            trail_color = (Style.BALL_COLOR[0], Style.BALL_COLOR[1], Style.BALL_COLOR[2], fade)
            trail_surface = pygame.Surface((self.render_size, self.render_size + 200), pygame.SRCALPHA)
            pygame.draw.circle(trail_surface, trail_color, (int(tx * self.render_size), int(ty * self.render_size) + offset_y), 4)
            self.window.blit(trail_surface, (0, 0))

        ball_surface = pygame.Surface((self.ball_radius * 2, self.ball_radius * 2), pygame.SRCALPHA)
        pygame.draw.circle(ball_surface, Style.BALL_COLOR, (self.ball_radius, self.ball_radius), self.ball_radius)
        pygame.draw.line(ball_surface, (0, 0, 0), (0, self.ball_radius), (self.ball_radius * 2, self.ball_radius), 2)

        if not hasattr(self, 'ball_angle'):
            self.ball_angle = 0
        self.ball_angle += self.spin * 5

        rotated_ball = pygame.transform.rotate(ball_surface, self.ball_angle)
        rotated_rect = rotated_ball.get_rect(center=(cx, cy))
        self.window.blit(rotated_ball, rotated_rect)

        pygame.draw.rect(self.window, Style.PLAYER_COLOR, (
            px - self.player_paddle_width // 2,
            offset_y + self.render_size - self.paddle_height,
            self.player_paddle_width,
            self.paddle_height
        ))

        pygame.draw.rect(self.window, Style.AI_COLOR, (
            ax - self.ai_paddle_width // 2,
            offset_y,
            self.ai_paddle_width,
            self.paddle_height
        ))

        bar_width = 150
        bar_height = 20
        spacing = 20

        pygame.draw.rect(self.window, Style.AI_BAR_BG, (
            self.render_size - bar_width - spacing,
            spacing,
            bar_width,
            bar_height
        ))
        pygame.draw.rect(self.window, Style.AI_BAR_FILL, (
            self.render_size - bar_width - spacing,
            spacing,
            bar_width * (self.ai_life / self.ai_max_life),
            bar_height
        ))

        pygame.draw.rect(self.window, Style.PLAYER_BAR_BG, (
            spacing,
            self.render_size + offset_y + spacing,
            bar_width,
            bar_height
        ))
        pygame.draw.rect(self.window, Style.PLAYER_BAR_FILL, (
            spacing,
            self.render_size + offset_y + spacing,
            bar_width * (self.player_life / self.player_max_life),
            bar_height
        ))

        pygame.display.flip()
        self.clock.tick(60)

    def close(self):
        if self.window:
            pygame.quit()