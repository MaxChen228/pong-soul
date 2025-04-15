# pong_duel_env.py

import gym
from gym import spaces
import numpy as np
import pygame
import random

from game.theme import Style
from game.physics import collide_sphere_with_moving_plane
from game.sound import SoundManager  # 音效管理
from game.render import Renderer
from game.settings import GameSettings  # 保留全域設定 (非技能相關)
# 這裡多匯入 skill_config (若需在 env 用到某些技能參數):
from game.skills.skill_config import SKILL_CONFIGS

# 技能類別
from game.skills.slowmo_skill import SlowMoSkill
from game.skills.long_paddle_skill import LongPaddleSkill


class PongDuelEnv(gym.Env):
    def __init__(
        self,
        render_size=400,
        paddle_width=60,
        paddle_height=10,
        ball_radius=10,
        active_skill_name=None,  # 新增參數：若外部(如 main.py)想直接指定技能名稱
    ):
        super().__init__()

        # === 音效管理 ===
        self.sound_manager = SoundManager()

        # === 渲染管理 ===
        self.renderer = None  # 用於 render()

        self.player_trail = []            # slowmo技能下的玩家板子殘影
        self.max_player_trail_length = 15

        # === 物理參數 ===
        self.mass = 1.0
        self.radius = 0.02
        self.e = 1.0
        self.mu = 0.4

        # === 基礎畫面參數 ===
        self.render_size = render_size
        self.paddle_width = paddle_width
        self.paddle_height = paddle_height
        self.ball_radius = ball_radius

        # 玩家 & AI 的位置 (0~1)
        self.player_x = 0.5
        self.ai_x = 0.5
        self.prev_player_x = self.player_x
        self.prev_ai_x = self.ai_x

        # 球的狀態
        self.ball_x = 0.5
        self.ball_y = 0.5
        self.ball_vx = 0.02
        self.ball_vy = -0.02

        # 自轉
        self.spin = 0
        self.enable_spin = True
        self.magnus_factor = 0.01

        # 難度/加速
        self.speed_scale_every = 3
        self.speed_increment = 0.005
        self.bounces = 0

        # 拖尾特效
        self.trail = []
        self.max_trail_length = 20

        # 初始方向 & 角度
        self.initial_direction = "down"
        self.initial_angle_deg = 15
        self.initial_angle_range = None
        self.initial_speed = 0.02

        # 血量
        self.player_life = 3
        self.ai_life = 3
        self.max_life = 3

        # Gym API
        self.observation_space = spaces.Box(
            low=np.array([0, 0, -1, -1, 0, 0], dtype=np.float32),
            high=np.array([1, 1, 1, 1, 1, 1], dtype=np.float32)
        )
        self.action_space = spaces.Discrete(3)

        # 視窗 & 時脈
        self.window = None
        self.clock = None

        # 死球時的 freeze 特效
        self.freeze_timer = 0
        self.freeze_duration = 500
        self.last_player_hit_time = 0
        self.last_ai_hit_time = 0

        # 遊戲速度 (slowmo 時會變)
        self.time_scale = 1.0

        # === 技能系統 ===
        self.skills = {}                 # 依據 active_skill_name 實例化
        self.active_skill_name = active_skill_name  # 先暫存
        self.ball_image = None           # 之後在render()載入

        # 技能特效相關
        self.slowmo_fog_active = False
        self.slowmo_fog_end_time = 0
        self.long_paddle_animating = False
        self.long_paddle_animation_start_time = 0
        self.long_paddle_target_width = None
        self.paddle_color = None  # 若技能改變板子顏色

    def set_params_from_config(self, config):
        """
        從關卡設定 (yaml) 讀取參數，並進一步覆蓋 env 初始值。
        另外若外部沒給 active_skill_name，就從 config 取 default。
        """
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
        self.long_paddle_original_width = self.player_paddle_width
        self.ai_paddle_width = config.get('ai_paddle_width', 60)

        # 關卡可能指定背景音樂
        self.bg_music = config.get("bg_music", "bg_music.mp3")

        # 如果外部沒有指定 active_skill_name，就用 config (若有)
        if not self.active_skill_name:
            self.active_skill_name = config.get('default_skill', 'slowmo')

        # 註冊對應的技能類別
        available_skills = {
            'slowmo': SlowMoSkill,
            'long_paddle': LongPaddleSkill
        }

        active_skill_class = available_skills.get(self.active_skill_name)
        if active_skill_class is None:
            raise ValueError(f"Skill '{self.active_skill_name}' not found!")

        self.skills.clear()
        self.register_skill(self.active_skill_name, active_skill_class(self))

    def register_skill(self, skill_name, skill_obj):
        self.skills[skill_name] = skill_obj

    def reset(self):
        """重置遊戲環境（球與板子）"""
        self.bounces = 0
        self.player_x = 0.5
        self.ai_x = 0.5

        # 隨機 or 固定角度
        if self.initial_angle_range:
            angle_deg = random.uniform(*self.initial_angle_range)
        else:
            angle_deg = self.initial_angle_deg

        angle_rad = np.radians(angle_deg)

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
        return np.array([
            self.ball_x, self.ball_y,
            self.ball_vx, self.ball_vy,
            self.player_x, self.ai_x
        ], dtype=np.float32)

    def get_lives(self):
        return self.player_life, self.ai_life

    def _scale_difficulty(self):
        factor = 1 + (self.bounces // self.speed_scale_every) * self.speed_increment
        self.ball_vx *= factor
        self.ball_vy *= factor

    def step(self, player_action, ai_action):
        current_time = pygame.time.get_ticks()

        # freeze機制：死球暫停
        if self.freeze_timer > 0:
            if current_time - self.freeze_timer < self.freeze_duration:
                return self._get_obs(), 0, False, False, {}
            else:
                self.freeze_timer = 0

        # 儲存前一幀資料
        self.prev_player_x = self.player_x
        self.prev_ai_x = self.ai_x
        old_ball_x = self.ball_x
        old_ball_y = self.ball_y

        # === 技能觸發 & 更新 ===
        keys = pygame.key.get_pressed()
        if keys[pygame.K_SPACE]:
            # 取得當前技能物件呼叫 activate()
            self.skills[self.active_skill_name].activate()

        for skill in self.skills.values():
            skill.update()

        # 根據技能啟動狀態，調整 time_scale
        active_skill = self.skills[self.active_skill_name]
        if self.active_skill_name == "slowmo" and active_skill.is_active():
            self.time_scale = 0.2
        else:
            self.time_scale = 1.0

        time_scale = self.time_scale

        # === 玩家 & AI 控制移動 ===
        combo_boost = 5.0 if time_scale < 1.0 else 1.0
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

        # Magnus effect (簡化)
        if self.enable_spin:
            self.ball_vx += self.magnus_factor * self.spin * self.ball_vy
        self.spin *= 1.0

        # 更新球位置
        self.ball_x += self.ball_vx * time_scale
        self.ball_y += self.ball_vy * time_scale

        # 拖尾
        self.trail.append((self.ball_x, self.ball_y))
        if len(self.trail) > self.max_trail_length:
            self.trail.pop(0)

        # 左右牆簡易反彈
        if self.ball_x <= 0:
            self.ball_x = 0
            self.ball_vx *= -1
        elif self.ball_x >= 1:
            self.ball_x = 1
            self.ball_vx *= -1

        reward = 0

        # === AI 擋板 (上方) 真實碰撞 ===
        ai_y = self.paddle_height / self.render_size
        ai_half_width = self.ai_paddle_width / self.render_size / 2

        if old_ball_y > ai_y and self.ball_y <= ai_y:
            if abs(self.ball_x - self.ai_x) < ai_half_width + self.radius:
                self.ball_y = ai_y
                vn = self.ball_vy
                vt = self.ball_vx
                u = (self.ai_x - self.prev_ai_x) / time_scale
                omega = self.spin

                vn_post, vt_post, omega_post = collide_sphere_with_moving_plane(
                    vn, vt, u, omega, self.e, self.mu, self.mass, self.radius
                )

                self.ball_vy = vn_post
                self.ball_vx = vt_post
                self.spin = omega_post

                self.bounces += 1
                self._scale_difficulty()
            else:
                # AI沒接到 => AI扣血
                self.ai_life -= 1
                self.last_ai_hit_time = current_time
                self.freeze_timer = current_time
                for s in self.skills.values():
                    s.deactivate()
                return self._get_obs(), reward, True, False, {}

        # === 玩家擋板 (下方) 真實碰撞 ===
        player_y = 1 - self.paddle_height / self.render_size
        player_half_width = self.player_paddle_width / self.render_size / 2

        if old_ball_y < player_y and self.ball_y >= player_y:
            if abs(self.ball_x - self.player_x) < player_half_width + self.radius:
                self.ball_y = player_y
                self.bounces += 1
                self._scale_difficulty()

                vn = -self.ball_vy
                vt = self.ball_vx
                u = (self.player_x - self.prev_player_x) / time_scale
                omega = self.spin

                vn_post, vt_post, omega_post = collide_sphere_with_moving_plane(
                    vn, vt, u, omega, self.e, self.mu, self.mass, self.radius
                )

                self.ball_vy = -vn_post
                self.ball_vx = vt_post
                self.spin = omega_post
            else:
                # 玩家沒接到 => 扣血
                self.player_life -= 1
                self.last_player_hit_time = current_time
                self.freeze_timer = current_time
                for s in self.skills.values():
                    s.deactivate()
                return self._get_obs(), reward, True, False, {}

        # === slowmo 技能霧氣 & 殘影特效 ===
        # 若 slowmo 啟動，就產生玩家板子殘影
        if active_skill.is_active() and self.active_skill_name == "slowmo":
            self.player_trail.append(self.player_x)
            if len(self.player_trail) > self.max_player_trail_length:
                self.player_trail.pop(0)
        else:
            self.player_trail.clear()

        # 檢查 slowmo 是否結束，若結束則處理 fog
        slowmo_skill = self.skills.get('slowmo')
        if slowmo_skill:
            if slowmo_skill.is_active():
                # 從 config 讀取霧氣時間 & paddle顏色
                slowmo_cfg = SKILL_CONFIGS["slowmo"]
                self.paddle_color = slowmo_cfg["paddle_color"]
                self.slowmo_fog_active = True
                self.slowmo_fog_end_time = current_time + slowmo_cfg["fog_duration_ms"]
            elif self.slowmo_fog_active and current_time > self.slowmo_fog_end_time:
                self.slowmo_fog_active = False
                self.paddle_color = None
                # 若有 shockwaves 亦清空
                if hasattr(self, 'shockwaves') and isinstance(self.shockwaves, list):
                    self.shockwaves.clear()

        # === long paddle 技能動畫處理 ===
        long_paddle_skill = self.skills.get('long_paddle')
        if long_paddle_skill:
            lp_cfg = SKILL_CONFIGS["long_paddle"]
            animation_ms = lp_cfg["animation_ms"]

            if long_paddle_skill.is_active():
                if not self.long_paddle_animating:
                    self.long_paddle_animating = True
                    self.long_paddle_animation_start_time = current_time
                    self.long_paddle_original_width = (
                        self.long_paddle_original_width or self.player_paddle_width
                    )
                    # 透過 config 取 multiplier
                    self.long_paddle_target_width = int(
                        self.long_paddle_original_width * lp_cfg["paddle_multiplier"]
                    )

                elapsed = current_time - self.long_paddle_animation_start_time
                if elapsed < animation_ms:
                    ratio = elapsed / animation_ms
                    self.player_paddle_width = int(
                        self.long_paddle_original_width
                        + (self.long_paddle_target_width - self.long_paddle_original_width) * ratio
                    )
                else:
                    self.player_paddle_width = self.long_paddle_target_width

                # 設定板子顏色
                self.paddle_color = lp_cfg["paddle_color"]

            else:
                # 技能結束 => 做縮回動畫
                if self.long_paddle_animating or (self.player_paddle_width != self.long_paddle_original_width):
                    if self.long_paddle_animating:
                        self.long_paddle_animating = False
                        self.long_paddle_animation_start_time = current_time

                    elapsed = current_time - self.long_paddle_animation_start_time
                    if elapsed < animation_ms:
                        ratio = elapsed / animation_ms
                        self.player_paddle_width = int(
                            self.long_paddle_target_width
                            - (self.long_paddle_target_width - self.long_paddle_original_width) * ratio
                        )
                    else:
                        self.player_paddle_width = self.long_paddle_original_width

                    # 若動畫結束，顏色恢復
                    if elapsed >= animation_ms or (self.player_paddle_width == self.long_paddle_original_width):
                        self.paddle_color = None

        return self._get_obs(), reward, False, False, {}

    def render(self):
        if self.renderer is None:
            self.renderer = Renderer(self)
            self.window = self.renderer.window
        self.renderer.render()

    def close(self):
        if self.window:
            pygame.quit()
