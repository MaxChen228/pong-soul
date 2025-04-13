import gym
from gym import spaces
import numpy as np
import pygame
import random
from game.theme import Style
from game.physics import collide_sphere_with_moving_plane
from game.sound import SoundManager  # 引入 SoundManager 類
from game.render import Renderer

class PongDuelEnv(gym.Env):
    def __init__(self, render_size=400, paddle_width=60, paddle_height=10, ball_radius=10):
        super().__init__()

        # ========== 音效管理 ==========
        self.sound_manager = SoundManager()  # 初始化音效管理器

        # ========== 渲染管理 ==========
        self.renderer = None  # ⭐ 新增這一行解決錯誤

        # ========== 物理參數 ==========
        self.mass = 1.0       # kg
        self.radius = 0.02    # m
        self.e = 1.0          # 恢復係數
        self.mu = 0.4         # 摩擦係數

        # ========== 畫面與遊戲參數 ==========
        self.render_size = render_size
        self.paddle_width = paddle_width
        self.paddle_height = paddle_height
        self.ball_radius = ball_radius

        # 玩家 & AI 初始位置
        self.player_x = 0.5
        self.ai_x = 0.5
        self.prev_player_x = self.player_x
        self.prev_ai_x = self.ai_x

        # 球初始狀態
        self.ball_x = 0.5
        self.ball_y = 0.5
        self.ball_vx = 0.02
        self.ball_vy = -0.02

        # 自轉
        self.spin = 0
        self.enable_spin = True
        self.magnus_factor = 0.01

        # 難度調整參數
        self.speed_scale_every = 3
        self.speed_increment = 0.005
        self.bounces = 0

        # 拖尾特效
        self.trail = []
        self.max_trail_length = 20

        # 初始方向與角度
        self.initial_direction = "down"
        self.initial_angle_deg = 15
        self.initial_angle_range = None
        self.initial_speed = 0.02

        # 血量相關
        self.player_life = 3
        self.ai_life = 3
        self.max_life = 3

        # Gym API
        self.observation_space = spaces.Box(
            low=np.array([0, 0, -1, -1, 0, 0], dtype=np.float32),
            high=np.array([1, 1, 1, 1, 1, 1], dtype=np.float32)
        )
        self.action_space = spaces.Discrete(3)

        # 視窗與時脈
        self.window = None
        self.clock = None

        # 時間減速機制
        self.time_slow_active = False
        self.time_slow_energy = 1.0
        self.time_slow_decay = 0.005
        self.time_slow_recover = 0.002

        # 球圖像（圖片載入延後到 render）
        self.ball_image = None

    def set_params_from_config(self, config):
        # 設定參數由關卡設定讀入
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
        # 重置狀態（球位置、板子位置、速度）
        self.bounces = 0
        self.player_x = 0.5
        self.ai_x = 0.5

        # 隨機或固定角度
        angle_deg = random.uniform(*self.initial_angle_range) if self.initial_angle_range else self.initial_angle_deg
        angle_rad = np.radians(angle_deg)

        # 根據方向決定初始 y
        if self.initial_direction == "down":
            self.ball_y = (self.paddle_height / self.render_size) + 0.05
            vy_sign = 1
        else:
            self.ball_y = 1 - (self.paddle_height / self.render_size) - 0.05
            vy_sign = -1

        self.ball_x = 0.5
        self.ball_vx = self.initial_speed * np.sin(angle_rad)
        self.ball_vy = self.initial_speed * np.cos(angle_rad) * vy_sign
        self.spin = 0
        return self._get_obs(), {}

    def _get_obs(self):
        return np.array([self.ball_x, self.ball_y, self.ball_vx, self.ball_vy, self.player_x, self.ai_x], dtype=np.float32)

    def get_lives(self):
        return self.player_life, self.ai_life

    def _scale_difficulty(self):
        factor = 1 + (self.bounces // self.speed_scale_every) * self.speed_increment
        self.ball_vx *= factor
        self.ball_vy *= factor

    def step(self, player_action, ai_action):
        # 儲存上幀資料
        self.prev_player_x = self.player_x
        self.prev_ai_x = self.ai_x
        old_ball_x = self.ball_x
        old_ball_y = self.ball_y

        # === 技能觸發狀態管理 ===
        keys = pygame.key.get_pressed()
        if not hasattr(self, 'slowmo_timer'):
            self.slowmo_timer = 0
        if not hasattr(self, 'slowmo_cooldown'):
            self.slowmo_cooldown = 0
        if not hasattr(self, 'slowmo_just_pressed'):
            self.slowmo_just_pressed = False

        # 技能觸發檢查，按下空白鍵且冷卻結束
        if keys[pygame.K_SPACE]:
            if not self.slowmo_just_pressed and self.slowmo_timer <= 0 and self.slowmo_cooldown <= 0:
                self.slowmo_timer = 90  # 技能持續 90 幀（大約 1.5 秒）
                self.slowmo_cooldown = 120  # 冷卻時間 120 幀（2 秒）

                # 播放慢動作音效
                self.sound_manager.play_slowmo()

            self.slowmo_just_pressed = True
        else:
            self.slowmo_just_pressed = False

        # 進行時間減速或冷卻的邏輯
        if self.slowmo_timer > 0:
            self.slowmo_timer -= 1
            self.time_slow_active = True
            time_scale = 0.3
        else:
            self.time_slow_active = False
            time_scale = 1.0
            if self.slowmo_cooldown > 0:
                self.slowmo_cooldown -= 1

        # 停止慢動作音效，並確保音效只停止一次
        if self.slowmo_timer <= 0:
            if self.sound_manager.slowmo_channel is not None:  # 確保音效正在播放
                self.sound_manager.stop_slowmo()  # 停止播放音效

        # === 更新技能計時與狀態 ===
        if self.slowmo_timer > 0:
            self.slowmo_timer -= 1
            self.time_slow_active = True
            time_scale = 0.3
        else:
            self.time_slow_active = False
            time_scale = 1.0
            if self.slowmo_cooldown > 0:
                self.slowmo_cooldown -= 1

        # === 技能條可視化比例（render 用） ===
        self.time_slow_energy = self.slowmo_timer / 90 if self.slowmo_timer > 0 else 0

        # === 玩家 / AI 控制 ===
        # Combo 強化：時間變慢時玩家移動更快
        combo_boost = 1.0
        if self.time_slow_active:
            combo_boost = 2.0  # 2 倍移動速度
        if player_action == 0:
            self.player_x -= 0.03 * time_scale * combo_boost
        elif player_action == 2:
            self.player_x += 0.03 * time_scale * combo_boost

        if ai_action == 0:
            self.ai_x -= 0.03 * time_scale
        elif ai_action == 2:
            self.ai_x += 0.03 * time_scale
        self.player_x = np.clip(self.player_x, 0.0, 1.0)
        self.ai_x = np.clip(self.ai_x, 0.0, 1.0)

        # Magnus effect 簡化模型（可升級）
        if self.enable_spin:
            self.ball_vx += self.magnus_factor * self.spin * self.ball_vy
        self.spin *= 0.99

        # 更新球位置
        self.ball_x += self.ball_vx * time_scale
        self.ball_y += self.ball_vy * time_scale

        # 拖尾
        self.trail.append((self.ball_x, self.ball_y))
        if len(self.trail) > self.max_trail_length:
            self.trail.pop(0)

        # 撞牆反彈
        if self.ball_x <= 0 or self.ball_x >= 1:
            self.ball_vx *= -1

        reward = 0

        # AI 擋板
        ai_y = self.paddle_height / self.render_size
        ai_half_width = self.ai_paddle_width / self.render_size / 2
        if old_ball_y > ai_y and self.ball_y <= ai_y:
            if abs(self.ball_x - self.ai_x) < ai_half_width + self.radius:
                self.ball_y = ai_y
                self.ball_vy *= -1
                self.bounces += 1
                self._scale_difficulty()
                paddle_velocity = self.ai_x - self.prev_ai_x
                self.spin = np.clip(paddle_velocity * 100, -3, 3)
            else:
                self.ai_life -= 1
                reward = 1
                return self._get_obs(), reward, True, False, {}

        # 玩家擋板
        player_y = 1 - self.paddle_height / self.render_size
        player_half_width = self.player_paddle_width / self.render_size / 2
        if old_ball_y < player_y and self.ball_y >= player_y:
            if abs(self.ball_x - self.player_x) < player_half_width + self.radius:
                self.ball_y = player_y
                self.bounces += 1
                self._scale_difficulty()

                # ⚡ 套用真實碰撞物理
                vn = -self.ball_vy
                vt = self.ball_vx
                u = (self.player_x - self.prev_player_x) / time_scale
                omega = self.spin

                vn_post, vt_post, omega_post = collide_sphere_with_moving_plane(
                    vn, vt, u, omega,
                    self.e, self.mu, self.mass, self.radius
                )

                self.ball_vy = -vn_post
                self.ball_vx = vt_post
                self.spin = omega_post
            else:
                self.player_life -= 1
                reward = -1
                return self._get_obs(), reward, True, False, {}

        return self._get_obs(), reward, False, False, {}

    def render(self):
        if self.renderer is None:
            self.renderer = Renderer(self)
            self.window = self.renderer.window
        self.renderer.render()

    def close(self):
        if self.window:
            pygame.quit()
