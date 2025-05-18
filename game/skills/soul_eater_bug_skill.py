# pong-soul/game/skills/soul_eater_bug_skill.py
import pygame
import math
import random
import numpy as np
import torch

from game.skills.base_skill import Skill
from game.skills.skill_config import SKILL_CONFIGS
from utils import resource_path
import os

from game.ai_agent import AIAgent


FPS = 60
DEBUG_BUG_SKILL = True # 確保 DEBUG 開啟

class SoulEaterBugSkill(Skill):
    def __init__(self, env, owner_player_state):
        super().__init__(env, owner_player_state)
        cfg_key = "soul_eater_bug"
        cfg = SKILL_CONFIGS.get(cfg_key, {})

        if not cfg:
            print(f"[SKILL_DEBUG][SoulEaterBugSkill] ({self.owner.identifier}) CRITICAL: Config for '{cfg_key}' not found in SKILL_CONFIGS! Using internal defaults for core params.")
            internal_core_cfg = {
                "duration_ms": 8000, "cooldown_ms": 12000,
                "bug_image_path": "assets/soul_eater_bug.png",
                "bug_display_scale_factor": 1.5,
                "base_y_speed": 0.020,
                "rl_model_path": None,
                "bug_x_rl_move_speed": 0.02,
                "bug_y_rl_move_speed": 0.02,
            }
            cfg = internal_core_cfg

        self.duration_ms = int(cfg.get("duration_ms", 8000))
        self.cooldown_ms = int(cfg.get("cooldown_ms", 12000))
        self.active = False
        self.activated_time = 0
        self.cooldown_start_time = 0

        if self.owner == self.env.player1:
            self.target_player_state = self.env.opponent
        else:
            self.target_player_state = self.env.player1
        
        if DEBUG_BUG_SKILL: print(f"[SKILL_DEBUG][SoulEaterBugSkill] ({self.owner.identifier}) Initialized. Target: {self.target_player_state.identifier}")

        bug_image_path = cfg.get("bug_image_path", "assets/soul_eater_bug.png")
        self.bug_display_scale_factor = float(cfg.get("bug_display_scale_factor", 1.5))
        
        try:
            base_diameter = self.env.ball_radius_px * 2 
            scaled_width = int(base_diameter * self.bug_display_scale_factor)
            scaled_height = int(base_diameter * self.bug_display_scale_factor)
            if scaled_width <=0 or scaled_height <=0 :
                scaled_width, scaled_height = int(20 * self.bug_display_scale_factor), int(20 * self.bug_display_scale_factor)
            self.bug_image_surface_loaded = pygame.image.load(resource_path(bug_image_path)).convert_alpha()
            self.bug_image_transformed = pygame.transform.smoothscale(self.bug_image_surface_loaded, (scaled_width, scaled_height))
            if DEBUG_BUG_SKILL:
                print(f"[SKILL_DEBUG][SoulEaterBugSkill] ({self.owner.identifier}) Bug Image Details:")
                print(f"    env.ball_radius_px: {self.env.ball_radius_px}")
                print(f"    bug_display_scale_factor: {self.bug_display_scale_factor}")
                print(f"    scaled_width for image (px): {scaled_width}")
                print(f"    bug_image_transformed width (px): {self.bug_image_transformed.get_width()}")
                print(f"    env.ball_radius_normalized (standard ball collision radius): {self.env.ball_radius_normalized:.4f}")
        except Exception as e:
            print(f"[SKILL_DEBUG][SoulEaterBugSkill] ({self.owner.identifier}) Error loading or scaling bug image: {bug_image_path}. Error: {e}")
            fallback_size = int(20 * self.bug_display_scale_factor)
            self.bug_image_transformed = pygame.Surface((fallback_size, fallback_size), pygame.SRCALPHA)
            pygame.draw.circle(self.bug_image_transformed, (100, 0, 100), (fallback_size//2, fallback_size//2), fallback_size//2)
            
        self.sound_activate_sfx = self._load_sound(cfg.get("sound_activate"))
        self.sound_crawl_sfx = self._load_sound(cfg.get("sound_crawl"))
        self.sound_hit_paddle_sfx = self._load_sound(cfg.get("sound_hit_paddle"))
        self.sound_score_sfx = self._load_sound(cfg.get("sound_score"))
        self.crawl_channel = None
        self.was_crawl_sound_playing = False

        self.bug_agent = None
        rl_model_path_from_config = cfg.get("rl_model_path")
        if rl_model_path_from_config:
            absolute_model_path = resource_path(rl_model_path_from_config)
            if DEBUG_BUG_SKILL:
                print(f"[SKILL_DEBUG][SoulEaterBugSkill] ({self.owner.identifier}) Attempting to load RL model from config path: '{rl_model_path_from_config}', resolved to: '{absolute_model_path}'")

            if os.path.exists(absolute_model_path):
                try:
                    self.bug_agent = AIAgent(
                        model_path=absolute_model_path,
                        input_dim=6,
                        output_dim=5
                    )
                    if DEBUG_BUG_SKILL: print(f"[SKILL_DEBUG][SoulEaterBugSkill] ({self.owner.identifier}) RL Bug Agent (AIAgent instance) loaded successfully from: {absolute_model_path}")
                except Exception as e:
                    print(f"[SKILL_DEBUG][SoulEaterBugSkill] ({self.owner.identifier}) ERROR loading RL Bug Agent model from '{absolute_model_path}': {e}")
                    self.bug_agent = None
            else:
                print(f"[SKILL_DEBUG][SoulEaterBugSkill] ({self.owner.identifier}) WARNING: RL Bug Agent model file not found at '{absolute_model_path}'. Bug will be inactive or use fallback.")
        else:
            if DEBUG_BUG_SKILL: print(f"[SKILL_DEBUG][SoulEaterBugSkill] ({self.owner.identifier}) No 'rl_model_path' in config. Bug will be inactive or use fallback if any.")

        self.bug_x_rl_move_speed = float(cfg.get("bug_x_rl_move_speed", 0.02))
        self.bug_y_rl_move_speed = float(cfg.get("bug_y_rl_move_speed", 0.02))
        self.base_y_speed = float(cfg.get("base_y_speed", 0.0))
        self.is_resting = False
        self.rest_timer_frames = 0

    def _get_bug_observation(self):
        bug_x_norm = self.env.ball_x
        bug_y_norm = self.env.ball_y
        target_paddle_x_norm = self.target_player_state.x
        target_paddle_half_width_norm = self.target_player_state.paddle_width_normalized / 2.0

        if self.target_player_state == self.env.opponent:
            bug_y_distance_to_goal_line = bug_y_norm
        else:
            bug_y_distance_to_goal_line = 1.0 - bug_y_norm
        
        observation = [
            bug_x_norm,
            bug_y_norm,
            target_paddle_x_norm,
            target_paddle_half_width_norm,
            bug_x_norm - target_paddle_x_norm,
            bug_y_distance_to_goal_line
        ]
        return np.array(observation, dtype=np.float32)

    def _load_sound(self, sound_path):
        if sound_path:
            try: return pygame.mixer.Sound(resource_path(sound_path))
            except pygame.error as e: print(f"[SKILL_DEBUG][SoulEaterBugSkill] Error loading sound: {sound_path}. Error: {e}")
        return None

    @property
    def overrides_ball_physics(self):
        return True

    def activate(self):
        cur_time = pygame.time.get_ticks()
        if self.active: 
            if DEBUG_BUG_SKILL: print(f"[SKILL_DEBUG][SoulEaterBugSkill] ({self.owner.identifier}) Activation failed: Already active.")
            return False
        if not (self.cooldown_start_time == 0 or (cur_time - self.cooldown_start_time >= self.cooldown_ms)):
            if DEBUG_BUG_SKILL: print(f"[SKILL_DEBUG][SoulEaterBugSkill] ({self.owner.identifier}) Activation failed: On cooldown ({self.get_cooldown_seconds():.1f}s left).")
            return False
        
        self.active = True
        self.activated_time = cur_time
        
        if hasattr(self.env, 'set_ball_visual_override'):
            self.env.set_ball_visual_override(skill_identifier="soul_eater_bug", active=True, owner_identifier=self.owner.identifier)
            if DEBUG_BUG_SKILL: print(f"[SKILL_DEBUG][SoulEaterBugSkill] ({self.owner.identifier}) Notified Env to change ball visual to bug.")
        
        self.env.ball_vx = 0
        self.env.ball_vy = 0
        self.env.spin = 0
        
        current_ball_x = self.env.ball_x
        current_ball_y = self.env.ball_y
        self.env.ball_x = current_ball_x
        self.env.ball_y = current_ball_y
        if DEBUG_BUG_SKILL:
            print(f"[SKILL_DEBUG][SoulEaterBugSkill] ({self.owner.identifier}) Bug initial position set to current ball position: X={self.env.ball_x:.3f}, Y={self.env.ball_y:.3f}")

        self.is_resting = False
        self.rest_timer_frames = 0
        self.was_crawl_sound_playing = False
        
        if DEBUG_BUG_SKILL: print(f"[SKILL_DEBUG][SoulEaterBugSkill] ({self.owner.identifier}) Activated! Target: {self.target_player_state.identifier}. Duration: {self.duration_ms}ms.")
        if self.sound_activate_sfx: self.sound_activate_sfx.play()
        if self.sound_crawl_sfx:
            self.crawl_channel = self.sound_crawl_sfx.play(-1)
            self.was_crawl_sound_playing = True
        return True

    def update(self):
        if not self.active:
            return

        current_time = pygame.time.get_ticks()
        if (current_time - self.activated_time) >= self.duration_ms:
            if DEBUG_BUG_SKILL: print(f"[SKILL_DEBUG][SoulEaterBugSkill] ({self.owner.identifier}) Duration expired.")
            self.deactivate(hit_paddle=False, scored=False)
            return

        delta_x_norm, delta_y_norm = 0.0, 0.0

        if self.bug_agent:
            obs = self._get_bug_observation()
            action_index = self.bug_agent.select_action(obs)
            
            y_direction_sign_to_target = -1.0 if self.target_player_state == self.env.opponent else 1.0
            
            if action_index == 0: # 前
                delta_y_norm = y_direction_sign_to_target * self.bug_y_rl_move_speed
            elif action_index == 1: # 後
                delta_y_norm = -y_direction_sign_to_target * self.bug_y_rl_move_speed
            elif action_index == 2: # 左
                delta_x_norm = -self.bug_x_rl_move_speed
            elif action_index == 3: # 右
                delta_x_norm = self.bug_x_rl_move_speed
            elif action_index == 4: # 靜止
                delta_x_norm = 0.0
                delta_y_norm = 0.0
            else:
                if DEBUG_BUG_SKILL:
                    print(f"[SKILL_DEBUG][SoulEaterBugSkill] ({self.owner.identifier}) Unknown RL Action Index: {action_index}. Bug will be static.")
                delta_x_norm = 0.0
                delta_y_norm = 0.0

            if self.base_y_speed != 0.0 and action_index in [2, 3, 4]:
                if delta_y_norm == 0.0:
                    delta_y_norm = y_direction_sign_to_target * self.base_y_speed
        else:
            y_direction_sign_to_target = -1.0 if self.target_player_state == self.env.opponent else 1.0
            delta_y_norm = y_direction_sign_to_target * self.base_y_speed

        self._apply_movement_and_constrain_bounds(delta_x_norm, delta_y_norm)
        
        if self._check_bug_scored():
            return 
        if self._check_bug_hit_paddle():
            return
            
        self._update_trail()

    def _apply_movement_and_constrain_bounds(self, delta_x_norm, delta_y_norm):
        actual_delta_x = delta_x_norm * self.env.time_scale
        actual_delta_y = delta_y_norm * self.env.time_scale
        
        self.env.ball_x += actual_delta_x
        self.env.ball_y += actual_delta_y
        
        # ⭐️ 使用標準球體半徑進行邊界限制
        ball_std_radius_norm = self.env.ball_radius_normalized

        self.env.ball_x = np.clip(self.env.ball_x, ball_std_radius_norm, 1.0 - ball_std_radius_norm)
        self.env.ball_y = np.clip(self.env.ball_y, ball_std_radius_norm, 1.0 - ball_std_radius_norm)

    def _check_bug_scored(self):
        bug_collision_radius_norm = self.env.ball_radius_normalized # ⭐️ 使用標準球體半徑
        target_goal_line_y_norm = 0.0
        scored_condition = False

        if self.target_player_state == self.env.opponent: # 目標在上方
            target_goal_line_y_norm = self.env.paddle_height_normalized * 0.5 
            if self.env.ball_y - bug_collision_radius_norm <= target_goal_line_y_norm: # ⭐️ 修改此處
                scored_condition = True
        else: # 目標在下方 (Player1)
            target_goal_line_y_norm = 1.0 - (self.env.paddle_height_normalized * 0.5)
            if self.env.ball_y + bug_collision_radius_norm >= target_goal_line_y_norm: # ⭐️ 修改此處
                scored_condition = True
        
        if scored_condition:
            if DEBUG_BUG_SKILL:
                print(f"[SKILL_DEBUG][SoulEaterBugSkill] ({self.owner.identifier}) Bug scored against {self.target_player_state.identifier}!")
                # ⭐️ 添加更詳細的得分時的 DEBUG 訊息
                print(f"    bug_y_norm: {self.env.ball_y:.4f}, bug_collision_radius_norm: {bug_collision_radius_norm:.4f}")
                print(f"    target_goal_line_y_norm: {target_goal_line_y_norm:.4f}")
            self.target_player_state.lives -= 1 
            self.target_player_state.last_hit_time = pygame.time.get_ticks()
            self.env.freeze_timer = pygame.time.get_ticks() 
            self.env.round_concluded_by_skill = True 
            self.env.current_round_info = {'scorer': self.owner.identifier, 'reason': 'bug_scored'} 
            self.deactivate(scored=True)
            return True
        return False

    def _check_bug_hit_paddle(self):
        bug_collision_radius_norm = self.env.ball_radius_normalized # ⭐️ 使用標準球體半徑
        target_paddle = self.target_player_state
        target_paddle_x_norm = target_paddle.x
        target_paddle_half_w_norm = target_paddle.paddle_width_normalized / 2
        
        target_paddle_y_surface_contact_min_norm = 0.0
        target_paddle_y_surface_contact_max_norm = 0.0

        if target_paddle == self.env.opponent: 
            target_paddle_y_surface_contact_min_norm = 0 
            target_paddle_y_surface_contact_max_norm = self.env.paddle_height_normalized 
        else: 
            target_paddle_y_surface_contact_min_norm = 1.0 - self.env.paddle_height_normalized
            target_paddle_y_surface_contact_max_norm = 1.0
            
        bug_y_min_norm = self.env.ball_y - bug_collision_radius_norm # ⭐️ 修改此處
        bug_y_max_norm = self.env.ball_y + bug_collision_radius_norm # ⭐️ 修改此處
        bug_x_min_norm = self.env.ball_x - bug_collision_radius_norm # ⭐️ 修改此處
        bug_x_max_norm = self.env.ball_x + bug_collision_radius_norm # ⭐️ 修改此處
        target_paddle_x_min_norm = target_paddle_x_norm - target_paddle_half_w_norm
        target_paddle_x_max_norm = target_paddle_x_norm + target_paddle_half_w_norm

        y_overlap = (bug_y_max_norm >= target_paddle_y_surface_contact_min_norm and \
                     bug_y_min_norm <= target_paddle_y_surface_contact_max_norm)
        x_overlap = (bug_x_max_norm >= target_paddle_x_min_norm and \
                     bug_x_min_norm <= target_paddle_x_max_norm)

        if x_overlap and y_overlap:
            if DEBUG_BUG_SKILL:
                print(f"[SKILL_DEBUG][SoulEaterBugSkill] ({self.owner.identifier}) Bug hit {target_paddle.identifier}'s paddle!")
                # ⭐️ 添加更詳細的碰撞時的 DEBUG 訊息
                print(f"    bug_x_norm: {self.env.ball_x:.4f}, bug_y_norm: {self.env.ball_y:.4f}, bug_collision_radius_norm: {bug_collision_radius_norm:.4f}")
                print(f"    bug_x_min: {bug_x_min_norm:.4f}, bug_x_max: {bug_x_max_norm:.4f}, bug_y_min: {bug_y_min_norm:.4f}, bug_y_max: {bug_y_max_norm:.4f}")
                print(f"    paddle_x_norm: {target_paddle_x_norm:.4f}, paddle_half_w: {target_paddle_half_w_norm:.4f}")
                print(f"    paddle_x_min: {target_paddle_x_min_norm:.4f}, paddle_x_max: {target_paddle_x_max_norm:.4f}")
                print(f"    paddle_y_contact_min: {target_paddle_y_surface_contact_min_norm:.4f}, paddle_y_contact_max: {target_paddle_y_surface_contact_max_norm:.4f}")
            self.env.freeze_timer = pygame.time.get_ticks() 
            self.env.round_concluded_by_skill = True 
            self.env.current_round_info = {'scorer': None, 'reason': 'bug_hit_paddle'} 
            self.deactivate(hit_paddle=True)
            return True
        return False

    def _update_trail(self):
        self.env.trail.append((self.env.ball_x, self.env.ball_y))
        if len(self.env.trail) > self.env.max_trail_length:
             self.env.trail.pop(0)

    def deactivate(self, *args, **kwargs):
        hit_paddle = kwargs.get('hit_paddle', False)
        scored = kwargs.get('scored', False)

        if DEBUG_BUG_SKILL:
            print(f"[SKILL_DEBUG][SoulEaterBugSkill] ({self.owner.identifier}) Deactivating. HitPaddle: {hit_paddle}, Scored: {scored}, Current Active State: {self.active}")

        was_truly_active = self.active 
        self.active = False

        if was_truly_active:
            self.cooldown_start_time = pygame.time.get_ticks()
            if DEBUG_BUG_SKILL: print(f"    Cooldown started at: {self.cooldown_start_time}")

            if self.sound_hit_paddle_sfx and hit_paddle and not scored:
                if DEBUG_BUG_SKILL: print("    Playing hit paddle sound.")
                self.sound_hit_paddle_sfx.play()
            if self.sound_score_sfx and scored:
                if DEBUG_BUG_SKILL: print("    Playing score sound.")
                self.sound_score_sfx.play()
        
        if hasattr(self.env, 'set_ball_visual_override'):
            self.env.set_ball_visual_override(skill_identifier="soul_eater_bug", active=False, owner_identifier=self.owner.identifier)
            if DEBUG_BUG_SKILL: print(f"    Notified Env to restore ball visual from bug.")
        
        if self.crawl_channel:
            self.crawl_channel.stop()
            self.crawl_channel = None
            if DEBUG_BUG_SKILL: print("    Crawl sound channel stopped.")
        self.was_crawl_sound_playing = False

        self.is_resting = False
        self.rest_timer_frames = 0
        if DEBUG_BUG_SKILL: print(f"    Skill fully deactivated. New Active State: {self.active}")

    def is_active(self):
        return self.active

    def get_cooldown_seconds(self):
        if self.active: return 0.0
        current_time = pygame.time.get_ticks()
        if self.cooldown_start_time == 0: return 0.0 
        elapsed = current_time - self.cooldown_start_time
        remaining = self.cooldown_ms - elapsed
        return max(0.0, remaining / 1000.0)

    def get_energy_ratio(self):
        current_time = pygame.time.get_ticks()
        if self.active:
            elapsed_duration = current_time - self.activated_time
            ratio = (self.duration_ms - elapsed_duration) / self.duration_ms if self.duration_ms > 0 else 0.0
            return max(0.0, ratio)
        else:
            if self.cooldown_start_time == 0 or (current_time - self.cooldown_start_time >= self.cooldown_ms):
                 return 1.0 
            elapsed_cooldown = current_time - self.cooldown_start_time
            ratio = elapsed_cooldown / self.cooldown_ms if self.cooldown_ms > 0 else 1.0
            return min(1.0, ratio)
            
    def render(self, surface):
        pass
    
    def get_visual_params(self):
        return {"type": "soul_eater_bug", "active_effects": self.is_active()}