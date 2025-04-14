import gym
from gym import spaces
import numpy as np
import pygame
import random
from game.theme import Style
from game.physics import collide_sphere_with_moving_plane
from game.sound import SoundManager  # 引入 SoundManager 類
from game.render import Renderer
from game.settings import GameSettings
from game.skills.slowmo_skill import SlowMoSkill
from game.skills.long_paddle_skill import LongPaddleSkill

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

        # 初始化技能
        self.skills = {}
        self.active_skill_name = None

        # 球圖像（圖片載入延後到 render）
        self.ball_image = None

        # 死球時的特效設定參數
        self.freeze_timer = 0
        self.freeze_duration = 500  # 毫秒 (0.5秒)
        self.last_player_hit_time = 0
        self.last_ai_hit_time = 0

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
        # ⭐️ 載入背景音樂
        self.bg_music = config.get("bg_music", "bg_music.mp3")  # 預設值防止出錯

        # 🔥 移到這裡！確保上面參數都已初始化再註冊技能
        available_skills = {
            'slowmo': SlowMoSkill,
            'long_paddle': LongPaddleSkill
        }

        active_skill_name = GameSettings.ACTIVE_SKILL
        active_skill_class = available_skills.get(active_skill_name)

        if active_skill_class is None:
            raise ValueError(f"Skill '{active_skill_name}' not found!")

        # 清空技能並重新註冊，避免重複
        self.skills.clear()
        self.register_skill(active_skill_name, active_skill_class(self))

        # 設定目前啟動的技能名稱
        self.active_skill_name = active_skill_name
        
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

    def register_skill(self, skill_name, skill_obj):
        self.skills[skill_name] = skill_obj

    def _scale_difficulty(self):
        factor = 1 + (self.bounces // self.speed_scale_every) * self.speed_increment
        self.ball_vx *= factor
        self.ball_vy *= factor

    def step(self, player_action, ai_action):

        current_time = pygame.time.get_ticks()
        if self.freeze_timer > 0:
            if current_time - self.freeze_timer < self.freeze_duration:
                # freeze期間，什麼都不更新
                return self._get_obs(), 0, False, False, {}
            else:
                self.freeze_timer = 0  # 解除freeze狀態

        # 儲存上幀資料
        self.prev_player_x = self.player_x
        self.prev_ai_x = self.ai_x
        old_ball_x = self.ball_x
        old_ball_y = self.ball_y

        # === 技能觸發與更新（新系統）===
        keys = pygame.key.get_pressed()

        # 按下空白鍵觸發slowmo技能
        if keys[pygame.K_SPACE]:
            self.skills[self.active_skill_name].activate()


        # 更新所有技能狀態
        for skill in self.skills.values():
            skill.update()

        # 判斷技能效果（使用動態名稱）
        active_skill = self.skills[self.active_skill_name]

        # 根據不同技能設定不同效果 (可彈性新增)
        if self.active_skill_name == "slowmo":
            self.time_slow_active = active_skill.is_active()
            self.time_slow_energy = active_skill.get_energy_ratio()
        else:
            self.time_slow_active = False
            self.time_slow_energy = 0

        time_scale = 0.3 if self.time_slow_active else 1.0

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
                self.last_ai_hit_time = pygame.time.get_ticks()
                self.freeze_timer = pygame.time.get_ticks()
                for skill in self.skills.values():
                    skill.deactivate()
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
                self.last_player_hit_time = pygame.time.get_ticks()
                self.freeze_timer = pygame.time.get_ticks()
                for skill in self.skills.values():
                    skill.deactivate()
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
