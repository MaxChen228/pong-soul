import gym
from gym import spaces
import numpy as np
import pygame
import random

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

        self.initial_direction = "down"
        self.initial_angle_deg = 15
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
        self.initial_direction = config.get('initial_direction', 'down')

    def reset(self):
        self.bounces = 0
        self.player_x = 0.5
        self.ai_x = 0.5

        self.ball_x = self.ai_x
        self.ball_y = self.paddle_height / self.render_size

        angle_rad = np.radians(self.initial_angle_deg)
        direction = -1 if self.initial_direction == "down" else 1
        self.ball_vx = self.initial_speed * np.sin(angle_rad)
        self.ball_vy = self.initial_speed * np.cos(angle_rad) * direction

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

        if self.ball_x <= 0 or self.ball_x >= 1:
            self.ball_vx *= -1

        reward = 0

        # AI 撞牆
        if self.ball_y <= (self.paddle_height / self.render_size):
            if abs(self.ball_x - self.ai_x) < self.paddle_width / self.render_size / 2:
                self.ball_vy *= -1
                self.bounces += 1
                self._scale_difficulty()
            else:
                self.ai_life -= 1
                reward = 1
                return self._get_obs(), reward, True, False, {}

        # 玩家撞牆
        elif self.ball_y >= 1 - (self.paddle_height / self.render_size):
            if abs(self.ball_x - self.player_x) < self.paddle_width / self.render_size / 2:
                self.ball_vy *= -1
                self.bounces += 1
                self._scale_difficulty()
            else:
                self.player_life -= 1
                reward = -1
                return self._get_obs(), reward, True, False, {}

        return self._get_obs(), reward, False, False, {}

    def render(self):
        if not self.window:
            pygame.init()
            self.window = pygame.display.set_mode((self.render_size, self.render_size))
            self.clock = pygame.time.Clock()

        self.window.fill((0, 0, 0))
        cx = int(self.ball_x * self.render_size)
        cy = int(self.ball_y * self.render_size)
        px = int(self.player_x * self.render_size)
        ax = int(self.ai_x * self.render_size)

        pygame.draw.circle(self.window, (255, 255, 255), (cx, cy), self.ball_radius)

        pygame.draw.rect(self.window, (0, 255, 0), (
            px - self.paddle_width // 2,
            self.render_size - self.paddle_height,
            self.paddle_width,
            self.paddle_height
        ))

        pygame.draw.rect(self.window, (255, 0, 0), (
            ax - self.paddle_width // 2,
            0,
            self.paddle_width,
            self.paddle_height
        ))

        # 血條
        bar_width = 100
        bar_height = 10
        spacing = 10

        pygame.draw.rect(self.window, (100, 0, 0), (
            spacing, spacing, bar_width, bar_height
        ))
        pygame.draw.rect(self.window, (255, 0, 0), (
            spacing, spacing,
            bar_width * (self.ai_life / self.max_life), bar_height
        ))

        pygame.draw.rect(self.window, (0, 100, 0), (
            self.render_size - bar_width - spacing,
            self.render_size - bar_height - spacing,
            bar_width, bar_height
        ))
        pygame.draw.rect(self.window, (0, 255, 0), (
            self.render_size - bar_width - spacing,
            self.render_size - bar_height - spacing,
            bar_width * (self.player_life / self.max_life),
            bar_height
        ))

        pygame.display.flip()
        self.clock.tick(60)

    def close(self):
        if self.window:
            pygame.quit()
