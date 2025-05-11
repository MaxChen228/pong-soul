# pong_duel_env.py

import numpy as np
import pygame
import random
import math

from game.theme import Style
from game.physics import collide_sphere_with_moving_plane, handle_paddle_collision
from game.sound import SoundManager
from game.render import Renderer
from game.settings import GameSettings
from game.skills.skill_config import SKILL_CONFIGS

# 示例：這裡掛好我們有 slowmo / long_paddle
from game.skills.slowmo_skill import SlowMoSkill
from game.skills.long_paddle_skill import LongPaddleSkill
from game.skills.soul_eater_bug_skill import SoulEaterBugSkill

class PongDuelEnv:
    def __init__(self,
                 render_size=400,
                 paddle_width=60,
                 paddle_height=10,
                 ball_radius=10,
                 active_skill_name=None):

        self.bug_skill_active = False
        self.sound_manager = SoundManager()
        self.renderer = None

        self.trail = []
        self.max_trail_length = 20

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

        self.spin = 0
        self.enable_spin = True
        self.magnus_factor = 0.01

        self.speed_scale_every = 3
        self.speed_increment = 0.005
        self.bounces = 0

        self.initial_direction = "down"
        self.initial_angle_deg = 15
        self.initial_angle_range = None
        self.initial_speed = 0.02

        self.player_life = 3
        self.ai_life = 3
        self.max_life = 3

        self.window = None
        self.clock = None
        self.freeze_timer = 0
        self.freeze_duration = 500
        self.last_player_hit_time = 0
        self.last_ai_hit_time = 0

        self.time_scale = 1.0

        # 技能系統
        self.skills = {}
        self.active_skill_name = active_skill_name
        self.ball_image = None
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

        # 這裡手動掛。若想自動掃描 plugin,可改成動態匯入
        available_skills = {
            'soul_eater_bug': SoulEaterBugSkill,
            'slowmo': SlowMoSkill,
            'long_paddle': LongPaddleSkill
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
            self.ball_y = (self.paddle_height/self.render_size)+0.05
            vy_sign=1
        else:
            self.ball_y = 1 - (self.paddle_height/self.render_size)-0.05
            vy_sign=-1

        self.ball_x=0.5
        self.ball_vx= self.initial_speed * np.sin(angle_rad)
        self.ball_vy= self.initial_speed * np.cos(angle_rad)* vy_sign
        self.spin=0
        return self._get_obs(),{}

    def _get_obs(self):
        return np.array([
            self.ball_x, self.ball_y,
            self.ball_vx, self.ball_vy,
            self.player_x, self.ai_x
        ], dtype=np.float32)

    def get_lives(self):
        return self.player_life, self.ai_life

    def _scale_difficulty(self):
        factor = 1 + (self.bounces// self.speed_scale_every)* self.speed_increment
        self.ball_vx *= factor
        self.ball_vy *= factor

    def step(self, player_action, ai_action):
        cur = pygame.time.get_ticks()

        if self.freeze_timer > 0:
            if cur - self.freeze_timer < self.freeze_duration:
                return self._get_obs(), 0, False, False, {}
            else:
                self.freeze_timer = 0

        self.prev_player_x = self.player_x
        self.prev_ai_x = self.ai_x
        old_ball_y = self.ball_y # old_ball_x is also available if needed

        # Skill activation and update calls
        keys = pygame.key.get_pressed()
        if keys[pygame.K_SPACE]:
            skill_instance = self.skills.get(self.active_skill_name)
            if skill_instance:
                skill_instance.activate()

        for skill_name, skill in self.skills.items(): # Iterate through all skills for their update
            if skill.is_active() or skill_name == self.active_skill_name : # Update active skill or if it has a passive component
                 skill.update()


        # --- Complex Bug Movement Logic ---
        if self.bug_skill_active:
            active_bug_skill = self.skills.get(self.active_skill_name)
            if not active_bug_skill or not active_bug_skill.is_active():
                self.bug_skill_active = False # Sync state if skill deactivated itself
            else:
                # 1. Y-axis movement (primary thrust towards opponent)
                #    Bug moves "up" the screen, so its Y value decreases.
                #    base_y_speed is per-frame, global time_scale will apply to the final position update.
                delta_y = -active_bug_skill.base_y_speed

                # 2. X-axis movement (sine wave oscillation around a homing target)
                homing_target_x = self.ai_x # Target the center of AI's paddle

                # Calculate the sine wave offset.
                # Phase depends on time_since_activation_frames.
                sine_oscillation = active_bug_skill.x_amplitude * math.sin(
                    active_bug_skill.x_frequency * (active_bug_skill.time_since_activation_frames * active_bug_skill.time_scaling_for_wave) +
                    active_bug_skill.initial_phase_offset
                )

                # The bug's desired X position is the homing target offset by the sine wave.
                bug_aim_x = homing_target_x + sine_oscillation
                bug_aim_x = np.clip(bug_aim_x, 0.0, 1.0) # Keep aim within screen bounds

                # Calculate the change in X needed to move towards bug_aim_x.
                # The x_homing_factor determines how quickly it tries to reach this bug_aim_x.
                delta_x = (bug_aim_x - self.ball_x) * active_bug_skill.x_homing_factor

                # --- Apply Movement (scaled by self.time_scale) ---
                self.ball_y += delta_y * self.time_scale
                self.ball_x += delta_x * self.time_scale

                # Clip ball_x to stay within [0, 1] bounds after movement
                self.ball_x = np.clip(self.ball_x, 0.0, 1.0)

                # --- Bug Collision & Goal Logic ---
                # Check if bug reached AI goal line
                ai_goal_line = self.paddle_height / self.render_size # AI paddle inner edge
                if self.ball_y <= ai_goal_line:
                    print("Bug reached AI goal!")
                    self.ai_life -= 1
                    self.last_ai_hit_time = cur
                    self.freeze_timer = cur
                    # (Optional) Play score sound via active_bug_skill if it stores sounds
                    active_bug_skill.deactivate() # Skill ends
                    self.bug_skill_active = False
                    return self._get_obs(), 0, True, False, {} # Round over

                # (Optional) Check bug collision with AI paddle (if blockable)
                # This part would need careful implementation if you want bugs to be blockable.
                # For now, we'll assume it passes through or the goal check is primary.
                # if cfg_can_be_blocked:
                #    ... collision logic ...

                # Update ball trail
                self.trail.append((self.ball_x, self.ball_y))
                if len(self.trail) > self.max_trail_length:
                    self.trail.pop(0)

                return self._get_obs(), 0, False, False, {} # Bug skill handled this frame

        # --- End of Bug Skill Logic ---


        # --- Normal Game Logic (if bug_skill_active is False) ---
        # (Existing code for player/AI movement, normal ball physics, collisions, scoring)
        # Ensure this section is only run if bug_skill_active is False.
        # The `return` statement within the `if self.bug_skill_active:` block handles this.

        # Player & AI paddle movement (applies regardless of bug skill)
        combo = 5.0 if self.time_scale < 1.0 else 1.0 # Slowmo combo effect
        if player_action == 0: # Left
            self.player_x -= 0.03 * self.time_scale * combo
        elif player_action == 2: # Right
            self.player_x += 0.03 * self.time_scale * combo

        if ai_action == 0: # AI Left
            self.ai_x -= 0.03 * self.time_scale
        elif ai_action == 2: # AI Right
            self.ai_x += 0.03 * self.time_scale

        self.player_x = np.clip(self.player_x, 0, 1)
        self.ai_x = np.clip(self.ai_x, 0, 1)

        # Normal Ball Physics
        if self.enable_spin: # Magnus effect
            self.ball_vx += self.magnus_factor * self.spin * self.ball_vy * self.time_scale # Apply time_scale to force
        # self.spin *= 1.0 # Spin decay (can be adjusted)

        self.ball_x += self.ball_vx * self.time_scale
        self.ball_y += self.ball_vy * self.time_scale

        self.trail.append((self.ball_x, self.ball_y))
        if len(self.trail) > self.max_trail_length:
            self.trail.pop(0)

        # Wall collisions
        if self.ball_x <= 0:
            self.ball_x = 0
            self.ball_vx *= -1
        elif self.ball_x >= 1:
            self.ball_x = 1
            self.ball_vx *= -1

        reward = 0 # Default reward

        # Paddle Collisions & Scoring (Normal Ball)
        # AI Paddle (Top)
        ai_paddle_contact_y = self.paddle_height / self.render_size
        ai_paddle_half_w_norm = (self.ai_paddle_width / self.render_size) / 2
        ball_radius_norm = self.ball_radius / self.render_size

        if old_ball_y > ai_paddle_contact_y and self.ball_y <= ai_paddle_contact_y: # Ball crossed plane from below
            if abs(self.ball_x - self.ai_x) < ai_paddle_half_w_norm + ball_radius_norm: # Hit
                self.ball_y = ai_paddle_contact_y # Correct position
                vn = self.ball_vy
                vt = self.ball_vx
                u = (self.ai_x - self.prev_ai_x) / self.time_scale if self.time_scale else 0 # Paddle speed
                omega = self.spin
                vn_post, vt_post, omega_post = collide_sphere_with_moving_plane(
                    vn, vt, u, omega, self.e, self.mu, self.mass, self.radius
                )
                self.ball_vy = vn_post
                self.ball_vx = vt_post
                self.spin = omega_post
                self.bounces += 1
                self._scale_difficulty()
            else: # Missed by AI
                self.ai_life -= 1
                self.last_ai_hit_time = cur
                self.freeze_timer = cur
                for s in self.skills.values(): s.deactivate()
                return self._get_obs(), reward, True, False, {} # Round over

        # Player Paddle (Bottom)
        player_paddle_contact_y = 1.0 - (self.paddle_height / self.render_size)
        player_paddle_half_w_norm = (self.player_paddle_width / self.render_size) / 2

        if old_ball_y < player_paddle_contact_y and self.ball_y >= player_paddle_contact_y: # Ball crossed plane from above
            if abs(self.ball_x - self.player_x) < player_paddle_half_w_norm + ball_radius_norm: # Hit
                self.ball_y = player_paddle_contact_y # Correct position
                self.bounces += 1
                self._scale_difficulty()
                vn = -self.ball_vy # Normal is upward
                vt = self.ball_vx
                u = (self.player_x - self.prev_player_x) / self.time_scale if self.time_scale else 0 # Paddle speed
                omega = self.spin
                vn_post, vt_post, omega_post = collide_sphere_with_moving_plane(
                    vn, vt, u, omega, self.e, self.mu, self.mass, self.radius
                )
                self.ball_vy = -vn_post # Reflect Y velocity
                self.ball_vx = vt_post
                self.spin = omega_post
            else: # Missed by Player
                self.player_life -= 1
                self.last_player_hit_time = cur
                self.freeze_timer = cur
                for s in self.skills.values(): s.deactivate()
                return self._get_obs(), reward, True, False, {} # Round over

        return self._get_obs(), reward, False, False, {}

    def render(self):
        if self.renderer is None:
            self.renderer= Renderer(self)
            self.window= self.renderer.window
        self.renderer.render()

    def close(self):
        if self.window:
            pygame.quit()
