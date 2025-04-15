# pong_duel_env.py

import gym
from gym import spaces
import numpy as np
import pygame
import random

from game.theme import Style
from game.physics import collide_sphere_with_moving_plane
from game.sound import SoundManager
from game.render import Renderer
from game.settings import GameSettings
from game.skills.skill_config import SKILL_CONFIGS

# 示例：我們有 slowmo_skill / long_paddle_skill
from game.skills.slowmo_skill import SlowMoSkill
from game.skills.long_paddle_skill import LongPaddleSkill

class PongDuelEnv(gym.Env):
    def __init__(
        self,
        render_size=400,
        paddle_width=60,
        paddle_height=10,
        ball_radius=10,
        active_skill_name=None,
    ):
        super().__init__()

        # 音效管理
        self.sound_manager = SoundManager()

        # 渲染
        self.renderer = None
        # (可選) 如果你要加全局拖尾
        self.trail = []
        self.max_trail_length = 20

        # 物理 / 初始參數
        self.mass = 1.0
        self.radius = 0.02
        self.e = 1.0
        self.mu = 0.4

        self.render_size = render_size
        self.paddle_width = paddle_width
        self.paddle_height = paddle_height
        self.ball_radius = ball_radius

        self.player_x = 0.5
        self.ai_x = 0.5
        self.prev_player_x = self.player_x
        self.prev_ai_x = self.ai_x

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

        # 初始方向 & 角度
        self.initial_direction = "down"
        self.initial_angle_deg = 15
        self.initial_angle_range = None
        self.initial_speed = 0.02

        # 血量
        self.player_life = 3
        self.ai_life = 3
        self.max_life = 3

        # Gym
        self.observation_space = spaces.Box(
            low=np.array([0,0,-1,-1,0,0], dtype=np.float32),
            high=np.array([1,1,1,1,1,1], dtype=np.float32)
        )
        self.action_space = spaces.Discrete(3)

        # freeze特效
        self.window = None
        self.clock = None
        self.freeze_timer = 0
        self.freeze_duration = 500
        self.last_player_hit_time = 0
        self.last_ai_hit_time = 0

        # 全局時間倍率
        self.time_scale = 1.0

        # === 技能系統 ===
        self.skills = {}
        self.active_skill_name = active_skill_name
        self.ball_image = None

        # 顏色 / fog / shockwave 都不在這裡
        self.paddle_color = None

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
        self.bg_music = config.get("bg_music", "bg_music.mp3")

        if not self.active_skill_name:
            self.active_skill_name = config.get('default_skill', 'slowmo')

        available_skills = {
            'slowmo': SlowMoSkill,
            'long_paddle': LongPaddleSkill
            # 你可以再加其他 skill
        }
        skill_cls = available_skills.get(self.active_skill_name)
        if not skill_cls:
            raise ValueError(f"Skill '{self.active_skill_name}' not found!")

        self.skills.clear()
        self.register_skill(self.active_skill_name, skill_cls(self))

    def register_skill(self, skill_name, skill_obj):
        self.skills[skill_name] = skill_obj

    def reset(self):
        self.bounces = 0
        self.player_x = 0.5
        self.ai_x = 0.5
        angle_deg = self.initial_angle_deg
        if self.initial_angle_range:
            angle_deg = random.uniform(*self.initial_angle_range)
        angle_rad = np.radians(angle_deg)

        if self.initial_direction == "down":
            self.ball_y = (self.paddle_height/self.render_size) + 0.05
            vy_sign = 1
        else:
            self.ball_y = 1 - (self.paddle_height/self.render_size) - 0.05
            vy_sign = -1

        self.ball_x = 0.5
        self.ball_vx = self.initial_speed * np.sin(angle_rad)
        self.ball_vy = self.initial_speed * np.cos(angle_rad) * vy_sign
        self.spin = 0
        return self._get_obs(), {}

    def _get_obs(self):
        return np.array([self.ball_x, self.ball_y,
                         self.ball_vx, self.ball_vy,
                         self.player_x, self.ai_x], dtype=np.float32)

    def get_lives(self):
        return self.player_life, self.ai_life

    def _scale_difficulty(self):
        factor = 1 + (self.bounces // self.speed_scale_every)*self.speed_increment
        self.ball_vx *= factor
        self.ball_vy *= factor

    def step(self, player_action, ai_action):
        current_time = pygame.time.get_ticks()

        # 冰凍機制
        if self.freeze_timer > 0:
            if current_time - self.freeze_timer < self.freeze_duration:
                return self._get_obs(), 0, False, False, {}
            else:
                self.freeze_timer = 0

        # 儲存舊位置
        self.prev_player_x = self.player_x
        self.prev_ai_x = self.ai_x
        old_ball_x = self.ball_x
        old_ball_y = self.ball_y

        # 技能觸發
        keys = pygame.key.get_pressed()
        if keys[pygame.K_SPACE]:
            self.skills[self.active_skill_name].activate()

        # 技能更新
        for skill in self.skills.values():
            skill.update()

        # 在 env 只做最簡單 time_scale
        active_skill = self.skills[self.active_skill_name]
        if self.active_skill_name == "slowmo" and active_skill.is_active():
            self.time_scale = 0.2
        else:
            self.time_scale = 1.0

        ts = self.time_scale

        # 玩家 / AI 移動
        combo_boost = 5.0 if ts < 1.0 else 1.0
        if player_action == 0:
            self.player_x -= 0.03 * ts * combo_boost
        elif player_action == 2:
            self.player_x += 0.03 * ts * combo_boost

        if ai_action == 0:
            self.ai_x -= 0.03 * ts
        elif ai_action == 2:
            self.ai_x += 0.03 * ts

        self.player_x = np.clip(self.player_x, 0, 1)
        self.ai_x = np.clip(self.ai_x, 0, 1)

        # Spin
        if self.enable_spin:
            self.ball_vx += self.magnus_factor * self.spin * self.ball_vy
        self.spin *= 1.0

        # 球更新
        self.ball_x += self.ball_vx * ts
        self.ball_y += self.ball_vy * ts

        # 拖尾 (全局)
        self.trail.append((self.ball_x, self.ball_y))
        if len(self.trail) > self.max_trail_length:
            self.trail.pop(0)

        # 左右牆
        if self.ball_x <= 0:
            self.ball_x = 0
            self.ball_vx *= -1
        elif self.ball_x >= 1:
            self.ball_x = 1
            self.ball_vx *= -1

        reward = 0

        # AI 擋板
        ai_y = self.paddle_height/self.render_size
        ai_hw = self.ai_paddle_width/self.render_size / 2
        if old_ball_y > ai_y and self.ball_y <= ai_y:
            if abs(self.ball_x - self.ai_x) < ai_hw + self.radius:
                # 撞到 AI 擋板
                self.ball_y = ai_y
                vn = self.ball_vy
                vt = self.ball_vx
                u = (self.ai_x - self.prev_ai_x)/ts
                omega = self.spin
                vn_post,vt_post,omega_post=collide_sphere_with_moving_plane(
                    vn,vt,u,omega,self.e,self.mu,self.mass,self.radius
                )
                self.ball_vy = vn_post
                self.ball_vx = vt_post
                self.spin = omega_post
                self.bounces += 1
                self._scale_difficulty()
            else:
                # AI沒接到 => AI扣血
                self.ai_life-=1
                self.last_ai_hit_time=current_time
                self.freeze_timer=current_time
                for s in self.skills.values():
                    s.deactivate()
                return self._get_obs(),reward,True,False,{}

        # 玩家擋板
        player_y = 1 - self.paddle_height/self.render_size
        player_hw = self.player_paddle_width/self.render_size / 2
        if old_ball_y < player_y and self.ball_y>=player_y:
            if abs(self.ball_x - self.player_x)< player_hw + self.radius:
                self.ball_y=player_y
                self.bounces+=1
                self._scale_difficulty()
                vn= -self.ball_vy
                vt= self.ball_vx
                u=(self.player_x - self.prev_player_x)/ts
                omega=self.spin
                vn_post,vt_post,omega_post= collide_sphere_with_moving_plane(
                    vn, vt, u, omega,self.e,self.mu,self.mass,self.radius
                )
                self.ball_vy= -vn_post
                self.ball_vx= vt_post
                self.spin= omega_post
            else:
                self.player_life-=1
                self.last_player_hit_time=current_time
                self.freeze_timer=current_time
                for s in self.skills.values():
                    s.deactivate()
                return self._get_obs(),reward,True,False,{}

        return self._get_obs(),reward,False,False,{}

    def render(self):
        if self.renderer is None:
            self.renderer=Renderer(self)
            self.window=self.renderer.window
        self.renderer.render()

    def close(self):
        if self.window:
            pygame.quit()
