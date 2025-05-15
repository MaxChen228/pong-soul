# envs/pong_duel_env.py
import numpy as np
import pygame
import random
import math

from game.theme import Style
from game.physics import collide_sphere_with_moving_plane
from game.sound import SoundManager
from game.render import Renderer # Renderer 將被修改
from game.settings import GameSettings # <--- 確保 GameSettings 已導入
from game.player_state import PlayerState

from game.skills.long_paddle_skill import LongPaddleSkill
from game.skills.slowmo_skill import SlowMoSkill
from game.skills.soul_eater_bug_skill import SoulEaterBugSkill

DEBUG_ENV = True
DEBUG_ENV_FULLSCREEN = True

class PongDuelEnv:
    def __init__(self,
                 game_mode=GameSettings.GameMode.PLAYER_VS_AI,
                 player1_config=None,
                 opponent_config=None,
                 common_config=None, # common_config 仍然可以由 GameplayState 傳入，但我們會優先使用它的值，然後才是 GameSettings 的預設
                 render_size=400,
                 paddle_height_px=10,
                 ball_radius_px=10,
                 initial_main_screen_surface_for_renderer=None
                ):

        if DEBUG_ENV: print(f"[SKILL_DEBUG][PongDuelEnv.__init__] Initializing with game_mode: {game_mode}")
        if DEBUG_ENV_FULLSCREEN:
            print(f"[DEBUG_ENV_FULLSCREEN][PongDuelEnv.__init__] Received initial_main_screen_surface: {type(initial_main_screen_surface_for_renderer)}")

        self.game_mode = game_mode
        self.sound_manager = SoundManager()
        self.renderer = None
        self.render_size = render_size
        self.paddle_height_px = paddle_height_px
        self.ball_radius_px = ball_radius_px
        
        self.provided_main_screen_surface = initial_main_screen_surface_for_renderer

        self.paddle_height_normalized = self.paddle_height_px / self.render_size if self.render_size > 0 else 0
        self.ball_radius_normalized = self.ball_radius_px / self.render_size if self.render_size > 0 else 0

        default_p_config = {'initial_x': 0.5, 'initial_paddle_width': 60, 'initial_lives': 3, 'skill_code': None, 'is_ai': False}
        p1_conf = player1_config if player1_config else default_p_config.copy()
        opp_conf = opponent_config if opponent_config else {**default_p_config.copy(), 'is_ai': (game_mode == GameSettings.GameMode.PLAYER_VS_AI)}

        self.player1 = PlayerState(
            initial_x=p1_conf.get('initial_x', 0.5),
            initial_paddle_width=p1_conf.get('initial_paddle_width', 60),
            initial_lives=p1_conf.get('initial_lives', 3),
            skill_code=p1_conf.get('skill_code'),
            is_ai=p1_conf.get('is_ai', False),
            env_render_size=self.render_size,
            player_identifier="player1"
        )
        self.opponent = PlayerState(
            initial_x=opp_conf.get('initial_x', 0.5),
            initial_paddle_width=opp_conf.get('initial_paddle_width', 60),
            initial_lives=opp_conf.get('initial_lives', 3),
            skill_code=opp_conf.get('skill_code'),
            is_ai=opp_conf.get('is_ai', game_mode == GameSettings.GameMode.PLAYER_VS_AI),
            env_render_size=self.render_size,
            player_identifier="opponent"
        )

        self.player1.skill_instance = self._create_skill(self.player1.skill_code_name, self.player1)
        self.opponent.skill_instance = self._create_skill(self.opponent.skill_code_name, self.opponent)

        self.ball_x = 0.5
        self.ball_y = 0.5
        self.ball_vx = 0.0
        self.ball_vy = 0.0
        self.spin = 0
        self.bounces = 0
        self.freeze_timer = 0
        self.time_scale = 1.0

        # 如果 GameplayState 沒有傳遞 common_config，則 cfg 為空字典
        cfg = common_config if common_config else {}

        # 現在從 common_config (如果提供) 或 GameSettings 的預設值獲取參數
        # GameSettings 的值作為最終的備用
        self.mass = cfg.get('mass', GameSettings.ENV_DEFAULT_MASS)
        self.e_ball_paddle = cfg.get('e_ball_paddle', GameSettings.ENV_DEFAULT_E_BALL_PADDLE)
        self.mu_ball_paddle = cfg.get('mu_ball_paddle', GameSettings.ENV_DEFAULT_MU_BALL_PADDLE)
        self.enable_spin = cfg.get('enable_spin', GameSettings.ENV_DEFAULT_ENABLE_SPIN)
        self.magnus_factor = cfg.get('magnus_factor', GameSettings.PHYSICS_MAGNUS_FACTOR) # 移至 physics 組
        self.speed_increment = cfg.get('speed_increment', GameSettings.ENV_DEFAULT_SPEED_INCREMENT)
        self.speed_scale_every = cfg.get('speed_scale_every', GameSettings.ENV_DEFAULT_SPEED_SCALE_EVERY)
        
        # 球的初始行為參數，優先使用關卡 YAML 中的，然後是 common_config，最後是 GameSettings
        self.initial_ball_speed = cfg.get('initial_speed', GameSettings.BALL_INITIAL_SPEED)
        self.initial_angle_range_deg = cfg.get('initial_angle_deg_range', GameSettings.BALL_INITIAL_ANGLE_DEG_RANGE)
        # initial_direction_serves_down 在 reset_ball_after_score 中使用，但其預設值也應來自 GameSettings
        # GameplayState 中的 GameplayState.on_enter() 會從關卡 YAML 讀取 level_specific_config 並更新 common_game_config
        # 所以這裡的 GameSettings.BALL_INITIAL_DIRECTION_SERVES_DOWN 主要是作為一個絕對備用
        # self.initial_direction_serves_down = cfg.get('initial_direction', GameSettings.BALL_INITIAL_DIRECTION_SERVES_DOWN)
        # ^^^ 這個屬性主要在 reset_ball_after_score 中用於邏輯判斷，不在這裡直接賦值給 self。
        # 它的值應在 GameplayState 構建 common_config 時就已確定。

        self.freeze_duration = cfg.get('freeze_duration_ms', GameSettings.FREEZE_DURATION_MS)
        self.countdown_seconds = cfg.get('countdown_seconds', GameSettings.COUNTDOWN_SECONDS)
        self.bg_music = cfg.get("bg_music", "bg_music_level1.mp3")

        self.trail = []
        self.ball_visual_key = "default"
        self.active_ball_visual_skill_owner = None
        self.max_trail_length = GameSettings.MAX_TRAIL_LENGTH # <--- 從 GameSettings 讀取

        self.round_concluded_by_skill = False
        self.current_round_info = {}

        if DEBUG_ENV: print("[SKILL_DEBUG][PongDuelEnv.__init__] Env Initialization complete (skills linked).")
        self.reset()

    def _create_skill(self, skill_code, owner_player_state):
        if not skill_code or skill_code.lower() == 'none':
            if DEBUG_ENV: print(f"[SKILL_DEBUG][PongDuelEnv._create_skill] No skill_code provided for {owner_player_state.identifier}.")
            return None
        available_skills = {
            "long_paddle": LongPaddleSkill,
            "slowmo": SlowMoSkill,
            "soul_eater_bug": SoulEaterBugSkill,
        }
        skill_class = available_skills.get(skill_code)
        if skill_class:
            try:
                skill_instance = skill_class(self, owner_player_state)
                if DEBUG_ENV: print(f"[SKILL_DEBUG][PongDuelEnv._create_skill] Created skill '{skill_code}' for {owner_player_state.identifier}.")
                return skill_instance
            except Exception as e:
                print(f"[SKILL_DEBUG][PongDuelEnv._create_skill] Error creating skill '{skill_code}' for {owner_player_state.identifier}: {e}")
                return None
        else:
            print(f"[SKILL_DEBUG][PongDuelEnv._create_skill] Unknown skill_code '{skill_code}' for {owner_player_state.identifier}.")
            return None
        
    def set_ball_visual_override(self, skill_identifier: str, active: bool, owner_identifier: str = None):
        if DEBUG_ENV: 
            print(f"[SKILL_DEBUG][PongDuelEnv.set_ball_visual_override] Called by skill '{skill_identifier}', active: {active}, owner: {owner_identifier}")

        if active:
            if self.active_ball_visual_skill_owner is None or self.active_ball_visual_skill_owner == owner_identifier:
                self.ball_visual_key = skill_identifier
                self.active_ball_visual_skill_owner = owner_identifier
                if DEBUG_ENV: print(f"    Ball visual set to '{self.ball_visual_key}' by {owner_identifier}.")
            else:
                if DEBUG_ENV: print(f"    Ball visual override IGNORED. Currently overridden by {self.active_ball_visual_skill_owner}'s skill.")
        else:
            if self.active_ball_visual_skill_owner == owner_identifier or self.ball_visual_key == skill_identifier:
                self.ball_visual_key = "default"
                self.active_ball_visual_skill_owner = None
                if DEBUG_ENV: print(f"    Ball visual restored to 'default'. Previous owner: {owner_identifier}")
            else:
                if DEBUG_ENV: print(f"    Ball visual restore IGNORED. Not current overrider or key mismatch. Current owner: {self.active_ball_visual_skill_owner}, current key: {self.ball_visual_key}")

    def activate_skill(self, player_state_object):
        if player_state_object and player_state_object.skill_instance:
            if DEBUG_ENV: print(f"[SKILL_DEBUG][PongDuelEnv.activate_skill] Attempting to activate skill for {player_state_object.identifier}.")
            activated = player_state_object.skill_instance.activate()
            if activated:
                 if DEBUG_ENV: print(f"[SKILL_DEBUG][PongDuelEnv.activate_skill] Skill for {player_state_object.identifier} ACTIVATED successfully.")
            else:
                 if DEBUG_ENV: print(f"[SKILL_DEBUG][PongDuelEnv.activate_skill] Skill for {player_state_object.identifier} FAILED to activate.")
        elif DEBUG_ENV:
            owner_id = player_state_object.identifier if player_state_object else "UNKNOWN_PLAYER_OBJECT"
            has_skill_instance = "YES" if player_state_object and player_state_object.skill_instance else "NO"
            print(f"[SKILL_DEBUG][PongDuelEnv.activate_skill] Cannot activate skill for {owner_id}, skill_instance present: {has_skill_instance}.")

    def reset_ball_after_score(self, scored_by_player1):
        if DEBUG_ENV: print(f"[PongDuelEnv.reset_ball_after_score] Ball reset. Scored by player1: {scored_by_player1}")
        self.round_concluded_by_skill = False
        self.bounces = 0
        self.spin = 0
        self.trail.clear()
        self.ball_visual_key = "default"
        self.active_ball_visual_skill_owner = None

        # initial_angle_range_deg 應從 self 獲取 (已在 __init__ 中設定)
        angle_deg = random.uniform(*self.initial_angle_range_deg)
        angle_rad = np.radians(angle_deg)
        
        serve_from_top_area = scored_by_player1
        
        if serve_from_top_area:
            self.ball_y = self.paddle_height_normalized + self.ball_radius_normalized + 0.05
            vy_sign = 1
        else:
            self.ball_y = 1.0 - self.paddle_height_normalized - self.ball_radius_normalized - 0.05
            vy_sign = -1

        self.ball_x = 0.5
        # initial_ball_speed 應從 self 獲取 (已在 __init__ 中設定)
        self.ball_vx = self.initial_ball_speed * np.sin(angle_rad)
        self.ball_vy = self.initial_ball_speed * np.cos(angle_rad) * vy_sign

        if self.player1.skill_instance and self.player1.skill_instance.is_active():
            if DEBUG_ENV: print(f"[SKILL_DEBUG][PongDuelEnv.reset_ball_after_score] Deactivating P1 skill: {self.player1.skill_instance.__class__.__name__}")
            self.player1.skill_instance.deactivate()
        if self.opponent.skill_instance and self.opponent.skill_instance.is_active():
            if DEBUG_ENV: print(f"[SKILL_DEBUG][PongDuelEnv.reset_ball_after_score] Deactivating Opponent skill: {self.opponent.skill_instance.__class__.__name__}")
            self.opponent.skill_instance.deactivate()

    def reset(self):
        if DEBUG_ENV: print("[SKILL_DEBUG][PongDuelEnv.reset] Full reset triggered.")
        self.player1.reset_state()
        self.opponent.reset_state()
        self.ball_visual_key = "default"
        self.active_ball_visual_skill_owner = None
        
        # 決定發球方時，考慮 GameSettings 中的 initial_direction_serves_down
        # 但 GameplayState 在準備 common_config 時，如果關卡 YAML 有 initial_direction，會覆蓋它。
        # 如果 GameplayState 傳入的 common_config 中有 initial_direction，則優先使用它。
        # 否則，使用 GameSettings.BALL_INITIAL_DIRECTION_SERVES_DOWN。
        # 這裡的 initial_direction_serves_down 決定了第一次 reset 時球是向上還是向下發。
        # (此處的實現保持原樣：隨機發球)
        serves_down_first = GameSettings.BALL_INITIAL_DIRECTION_SERVES_DOWN # 從設定讀取預設
        # 如果 common_config (即 self.initial_direction_serves_down，如果存在) 中有指定，會覆蓋
        # 這裡我們簡化為，reset() 時的發球方向不由 scored_by_player1 決定，而是由一個配置決定
        self.reset_ball_after_score(scored_by_player1=not serves_down_first if serves_down_first else random.choice([True,False]))


        self.time_scale = 1.0
        return self._get_obs(), {}

    def _get_obs(self):
        obs_array = [
            self.ball_x, self.ball_y,
            self.ball_vx, self.ball_vy,
            self.player1.x, self.opponent.x,
        ]
        return np.array(obs_array, dtype=np.float32)
    
    def _determine_time_scale(self):
        current_time_scale = 1.0
        active_slowmo_skill = None
        if self.player1.skill_instance and isinstance(self.player1.skill_instance, SlowMoSkill) and self.player1.skill_instance.is_active():
             active_slowmo_skill = self.player1.skill_instance
        if self.opponent.skill_instance and isinstance(self.opponent.skill_instance, SlowMoSkill) and self.opponent.skill_instance.is_active():
            if active_slowmo_skill is None or \
               self.opponent.skill_instance.slow_time_scale_value < active_slowmo_skill.slow_time_scale_value:
                 active_slowmo_skill = self.opponent.skill_instance
        
        if active_slowmo_skill:
            current_time_scale = active_slowmo_skill.slow_time_scale_value
        return current_time_scale

    def _update_player_positions(self, player1_action_input, opponent_action_input, time_scale):
        self.player1.prev_x = self.player1.x
        self.opponent.prev_x = self.opponent.x
        
        player_move_speed = GameSettings.PLAYER_MOVE_SPEED # <--- 從 GameSettings 讀取
        
        if player1_action_input == 0: self.player1.x -= player_move_speed * time_scale
        elif player1_action_input == 2: self.player1.x += player_move_speed * time_scale
        
        if opponent_action_input == 0: self.opponent.x -= player_move_speed * time_scale
        elif opponent_action_input == 2: self.opponent.x += player_move_speed * time_scale

        self.player1.x = np.clip(self.player1.x, 0.0, 1.0)
        self.opponent.x = np.clip(self.opponent.x, 0.0, 1.0)

    def _update_active_skills(self):
        if self.player1.skill_instance and self.player1.skill_instance.is_active():
            self.player1.skill_instance.update()
        if self.opponent.skill_instance and self.opponent.skill_instance.is_active():
            self.opponent.skill_instance.update()

    def _apply_ball_movement_and_physics(self, time_scale):
        if self.enable_spin:
            spin_force_x = self.magnus_factor * self.spin * self.ball_vy if self.ball_vy != 0 else 0
            self.ball_vx += spin_force_x * time_scale
        
        self.ball_x += self.ball_vx * time_scale
        self.ball_y += self.ball_vy * time_scale

        self.trail.append((self.ball_x, self.ball_y))
        if len(self.trail) > self.max_trail_length: 
            self.trail.pop(0)

    def _handle_wall_collisions(self):
        collided_with_wall = False
        if self.ball_x - self.ball_radius_normalized <= 0:
            self.ball_x = self.ball_radius_normalized
            self.ball_vx *= -1
            collided_with_wall = True
        elif self.ball_x + self.ball_radius_normalized >= 1.0:
            self.ball_x = 1.0 - self.ball_radius_normalized
            self.ball_vx *= -1
            collided_with_wall = True
        
        if collided_with_wall and hasattr(self.sound_manager, 'play_wall_hit'):
            pass

    def _handle_paddle_collisions(self, old_ball_y, time_scale):
        collided_this_step = False
        ts = time_scale

        opponent_paddle_surface_y = self.paddle_height_normalized 
        opponent_paddle_contact_y = opponent_paddle_surface_y + self.ball_radius_normalized
        opponent_paddle_half_w = self.opponent.paddle_width_normalized / 2

        if old_ball_y > opponent_paddle_contact_y and self.ball_y <= opponent_paddle_contact_y:
            if abs(self.ball_x - self.opponent.x) < opponent_paddle_half_w + self.ball_radius_normalized * 0.75:
                self.ball_y = opponent_paddle_contact_y 
                vn = self.ball_vy 
                vt = self.ball_vx 
                u_paddle = (self.opponent.x - self.opponent.prev_x) / ts if ts != 0 else 0 
                
                vn_post, vt_post, omega_post = collide_sphere_with_moving_plane(
                    vn, vt, u_paddle, self.spin, self.e_ball_paddle, self.mu_ball_paddle, self.mass, self.ball_radius_normalized
                )
                self.ball_vy = vn_post
                self.ball_vx = vt_post
                self.spin = omega_post
                self.bounces += 1
                self._scale_difficulty()
                self.sound_manager.play_paddle_hit()
                collided_this_step = True
        
        if not collided_this_step:
            player1_paddle_surface_y = 1.0 - self.paddle_height_normalized 
            player1_paddle_contact_y = player1_paddle_surface_y - self.ball_radius_normalized 
            player1_paddle_half_w = self.player1.paddle_width_normalized / 2

            if old_ball_y < player1_paddle_contact_y and self.ball_y >= player1_paddle_contact_y: 
                if abs(self.ball_x - self.player1.x) < player1_paddle_half_w + self.ball_radius_normalized * 0.75:
                    self.ball_y = player1_paddle_contact_y 
                    vn = -self.ball_vy 
                    vt = self.ball_vx
                    u_paddle = (self.player1.x - self.player1.prev_x) / ts if ts != 0 else 0
                    
                    vn_post, vt_post, omega_post = collide_sphere_with_moving_plane(
                        vn, vt, u_paddle, self.spin, self.e_ball_paddle, self.mu_ball_paddle, self.mass, self.ball_radius_normalized
                    )
                    self.ball_vy = -vn_post 
                    self.ball_vx = vt_post
                    self.spin = omega_post
                    self.bounces += 1
                    self._scale_difficulty()
                    self.sound_manager.play_paddle_hit()
                    collided_this_step = True
        
        return collided_this_step

    def _check_scoring_and_resolve_round(self, collided_with_paddle_this_step):
        round_done = False
        info = {'scorer': None}
        current_time_ticks = pygame.time.get_ticks()

        if not collided_with_paddle_this_step:
            if self.ball_y - self.ball_radius_normalized < 0:
                if self.opponent.lives > 0: self.opponent.lives -=1 
                self.player1.last_hit_time = current_time_ticks 
                self.freeze_timer = current_time_ticks
                round_done = True
                info['scorer'] = 'player1'
                if DEBUG_ENV: print(f"[PongDuelEnv._check_scoring] Player 1 scored! Opponent lives: {self.opponent.lives}")
            elif self.ball_y + self.ball_radius_normalized > 1.0:
                if self.player1.lives > 0: self.player1.lives -= 1
                self.opponent.last_hit_time = current_time_ticks 
                self.freeze_timer = current_time_ticks
                round_done = True
                info['scorer'] = 'opponent'
                if DEBUG_ENV: print(f"[PongDuelEnv._check_scoring] Opponent scored! Player 1 lives: {self.player1.lives}")
        
        return round_done, info

    def get_render_data(self):
        player1_skill_visual_params = {}
        if self.player1.skill_instance and hasattr(self.player1.skill_instance, 'get_visual_params'):
            player1_skill_visual_params = self.player1.skill_instance.get_visual_params()

        player1_skill_data_for_ui = None
        if self.player1.skill_instance:
            player1_skill_data_for_ui = {
                "code_name": self.player1.skill_code_name,
                "is_active": self.player1.skill_instance.is_active(),
                "energy_ratio": self.player1.skill_instance.get_energy_ratio(),
                "cooldown_seconds": self.player1.skill_instance.get_cooldown_seconds(),
                "visual_params": player1_skill_visual_params
            }

        opponent_skill_visual_params = {}
        if self.opponent.skill_instance and hasattr(self.opponent.skill_instance, 'get_visual_params'):
            opponent_skill_visual_params = self.opponent.skill_instance.get_visual_params()

        opponent_skill_data_for_ui = None
        if self.opponent.skill_instance:
            opponent_skill_data_for_ui = {
                "code_name": self.opponent.skill_code_name,
                "is_active": self.opponent.skill_instance.is_active(),
                "energy_ratio": self.opponent.skill_instance.get_energy_ratio(),
                "cooldown_seconds": self.opponent.skill_instance.get_cooldown_seconds(),
                "visual_params": opponent_skill_visual_params
            }

        freeze_active = (self.freeze_timer > 0 and 
                        (pygame.time.get_ticks() - self.freeze_timer < self.freeze_duration))

        render_data = {
            "game_mode": self.game_mode,
            "ball": {
                "x_norm": self.ball_x,
                "y_norm": self.ball_y,
                "spin": self.spin, 
                "radius_norm": self.ball_radius_normalized,
                "image_key": self.ball_visual_key
            },
            "player1": {
                "x_norm": self.player1.x,
                "paddle_width_norm": self.player1.paddle_width_normalized, 
                "paddle_color": self.player1.paddle_color,
                "lives": self.player1.lives,
                "max_lives": self.player1.max_lives,
                "skill_data": player1_skill_data_for_ui,
                "is_ai": self.player1.is_ai, 
                "identifier": self.player1.identifier, 
            },
            "opponent": {
                "x_norm": self.opponent.x,
                "paddle_width_norm": self.opponent.paddle_width_normalized,
                "paddle_color": self.opponent.paddle_color,
                "lives": self.opponent.lives,
                "max_lives": self.opponent.max_lives,
                "skill_data": opponent_skill_data_for_ui,
                "is_ai": self.opponent.is_ai,
                "identifier": self.opponent.identifier,
            },
            "trail": list(self.trail), 
            "paddle_height_norm": self.paddle_height_normalized, 
            "freeze_active": freeze_active,
            "logical_paddle_height_px": self.paddle_height_px,
        }
        return render_data

    def get_lives(self):
        return self.player1.lives, self.opponent.lives

    def _scale_difficulty(self):
        if self.bounces > 0 and self.speed_scale_every > 0:
            # speed_increment 應從 self 獲取
            speed_multiplier = 1 + (self.bounces // self.speed_scale_every) * self.speed_increment
            current_speed_magnitude = math.sqrt(self.ball_vx**2 + self.ball_vy**2)
            
            if current_speed_magnitude > 1e-6:
                # initial_ball_speed 應從 self 獲取
                target_speed_magnitude = max(self.initial_ball_speed, self.initial_ball_speed * speed_multiplier)
                
                scale_factor = target_speed_magnitude / current_speed_magnitude
                self.ball_vx *= scale_factor
                self.ball_vy *= scale_factor
                if DEBUG_ENV:
                    print(f"[PongDuelEnv._scale_difficulty] Bounces: {self.bounces}, Multiplier: {speed_multiplier:.3f}, New Speed Mag: {target_speed_magnitude:.4f}")

    def step(self, player1_action_input, opponent_action_input):
        current_time_ticks = pygame.time.get_ticks()
        
        if self.freeze_timer > 0:
            if current_time_ticks - self.freeze_timer < self.freeze_duration:
                return self._get_obs(), 0, False, False, {'scorer': None}
            else:
                self.freeze_timer = 0

        current_time_scale = self._determine_time_scale()
        self.time_scale = current_time_scale

        self._update_player_positions(player1_action_input, opponent_action_input, current_time_scale)

        old_ball_y_for_collision = self.ball_y 

        self.round_concluded_by_skill = False
        self.current_round_info = {}
        self._update_active_skills()

        if self.round_concluded_by_skill:
            if DEBUG_ENV: print(f"[SKILL_DEBUG][PongDuelEnv.step] Round concluded by SKILL. Info: {self.current_round_info}")
            game_over_after_skill = self.player1.lives <= 0 or self.opponent.lives <= 0
            final_info = {'scorer': None}
            final_info.update(self.current_round_info)
            return self._get_obs(), 0, True, game_over_after_skill, final_info

        run_normal_ball_physics = True
        if (self.player1.skill_instance and self.player1.skill_instance.is_active() and 
            getattr(self.player1.skill_instance, 'overrides_ball_physics', False)):
            run_normal_ball_physics = False
        elif (self.opponent.skill_instance and self.opponent.skill_instance.is_active() and
              getattr(self.opponent.skill_instance, 'overrides_ball_physics', False)):
            run_normal_ball_physics = False

        reward = 0
        round_done_by_normal_physics = False
        game_over_by_normal_physics = False
        info_from_normal_physics = {'scorer': None}

        if run_normal_ball_physics:
            self._apply_ball_movement_and_physics(current_time_scale)
            self._handle_wall_collisions()
            collided_with_paddle_this_step = self._handle_paddle_collisions(old_ball_y_for_collision, current_time_scale)
            round_done_by_normal_physics, info_from_normal_physics = self._check_scoring_and_resolve_round(collided_with_paddle_this_step)
            
            if round_done_by_normal_physics and DEBUG_ENV:
                print(f"[NORMAL_PHYSICS][PongDuelEnv.step] Round ended by NORMAL physics. Scorer: {info_from_normal_physics.get('scorer')}. P1 Lives: {self.player1.lives}, Opponent Lives: {self.opponent.lives}")
        
        if round_done_by_normal_physics or self.round_concluded_by_skill :
            game_over_by_normal_physics = self.player1.lives <= 0 or self.opponent.lives <= 0
            if game_over_by_normal_physics and DEBUG_ENV:
                print(f"[NORMAL_PHYSICS][PongDuelEnv.step] GAME OVER by NORMAL physics detected.")

        final_round_done = round_done_by_normal_physics or self.round_concluded_by_skill
        final_game_over = game_over_by_normal_physics
        
        final_info_to_return = {'scorer': None}
        if self.round_concluded_by_skill:
            final_info_to_return.update(self.current_round_info)
        elif round_done_by_normal_physics:
            final_info_to_return.update(info_from_normal_physics)
            
        return self._get_obs(), reward, final_round_done, final_game_over, final_info_to_return

    def render(self):
        if self.renderer is None:
            if DEBUG_ENV: print("[PongDuelEnv.render] Renderer not initialized. Creating one.")
            if self.provided_main_screen_surface is None and DEBUG_ENV_FULLSCREEN:
                print("[DEBUG_ENV_FULLSCREEN][PongDuelEnv.render] CRITICAL WARNING: provided_main_screen_surface is None when creating Renderer!")

            actual_width, actual_height = (0,0)
            if self.provided_main_screen_surface:
                actual_width, actual_height = self.provided_main_screen_surface.get_size()
                if DEBUG_ENV_FULLSCREEN: print(f"[DEBUG_ENV_FULLSCREEN][PongDuelEnv.render] Passing surface of size {actual_width}x{actual_height} to Renderer.")
            else: 
                if DEBUG_ENV_FULLSCREEN: print(f"[DEBUG_ENV_FULLSCREEN][PongDuelEnv.render] No surface provided, Renderer might create its own default window.")

            self.renderer = Renderer(
                game_mode=self.game_mode,
                logical_game_area_size=self.render_size,
                logical_ball_radius_px=self.ball_radius_px,
                logical_paddle_height_px=self.paddle_height_px,
                actual_screen_surface=self.provided_main_screen_surface,
                actual_screen_width=actual_width,
                actual_screen_height=actual_height
            )

        render_data_packet = self.get_render_data()
        self.renderer.render(render_data_packet)

    def close(self):
        if DEBUG_ENV: print("[PongDuelEnv.close] Closing environment.")
        if self.renderer:
            self.renderer.close()
            self.renderer = None
        if self.sound_manager:
            self.sound_manager.stop_bg_music()