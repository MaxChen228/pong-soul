# envs/pong_duel_env.py
import numpy as np
import pygame
import random
import math

from game.theme import Style
from game.physics import collide_sphere_with_moving_plane
from game.sound import SoundManager
from game.render import Renderer
from game.settings import GameSettings
from game.player_state import PlayerState

# ⭐️ 引入所有可用的技能類
from game.skills.long_paddle_skill import LongPaddleSkill
from game.skills.slowmo_skill import SlowMoSkill
from game.skills.soul_eater_bug_skill import SoulEaterBugSkill # 之後階段再詳細適配此技能

DEBUG_ENV = True

class PongDuelEnv:
    def __init__(self,
                 game_mode=GameSettings.GameMode.PLAYER_VS_AI,
                 player1_config=None,
                 opponent_config=None,
                 common_config=None,
                 render_size=400,
                 paddle_height_px=10,
                 ball_radius_px=10):

        if DEBUG_ENV: print(f"[SKILL_DEBUG][PongDuelEnv.__init__] Initializing with game_mode: {game_mode}")
        # ... (之前的 __init__ 内容保持不变，直到 PlayerState 初始化之后) ...
        self.game_mode = game_mode
        self.sound_manager = SoundManager()
        self.renderer = None
        self.render_size = render_size
        self.paddle_height_px = paddle_height_px
        self.ball_radius_px = ball_radius_px
        self.paddle_height_normalized = self.paddle_height_px / self.render_size
        self.ball_radius_normalized = self.ball_radius_px / self.render_size

        default_p_config = {'initial_x': 0.5, 'initial_paddle_width': 60, 'initial_lives': 3, 'skill_code': None, 'is_ai': False}
        p1_conf = player1_config if player1_config else default_p_config
        opp_conf = opponent_config if opponent_config else {**default_p_config, 'is_ai': True if game_mode == GameSettings.GameMode.PLAYER_VS_AI else False}

        self.player1 = PlayerState(
            initial_x=p1_conf.get('initial_x', 0.5),
            initial_paddle_width=p1_conf.get('initial_paddle_width', 60),
            initial_lives=p1_conf.get('initial_lives', 3),
            skill_code=p1_conf.get('skill_code'),
            is_ai=p1_conf.get('is_ai', False),
            env_render_size=self.render_size,
            player_identifier="player1" # ⭐️ 傳遞 identifier
        )
        self.opponent = PlayerState(
            initial_x=opp_conf.get('initial_x', 0.5),
            initial_paddle_width=opp_conf.get('initial_paddle_width', 60),
            initial_lives=opp_conf.get('initial_lives', 3),
            skill_code=opp_conf.get('skill_code'),
            is_ai=opp_conf.get('is_ai', game_mode == GameSettings.GameMode.PLAYER_VS_AI),
            env_render_size=self.render_size,
            player_identifier="opponent" # ⭐️ 傳遞 identifier
        )
        
        # ⭐️ 技能實例化
        self.player1.skill_instance = self._create_skill(self.player1.skill_code_name, self.player1)
        self.opponent.skill_instance = self._create_skill(self.opponent.skill_code_name, self.opponent)

        # ... (球狀態、遊戲邏輯、通用配置應用等保持不變) ...
        self.ball_x = 0.5
        self.ball_y = 0.5
        self.ball_vx = 0.0 
        self.ball_vy = 0.0 
        self.spin = 0
        self.bounces = 0 
        self.freeze_timer = 0 
        self.time_scale = 1.0 

        cfg = common_config if common_config else {}
        self.mass = cfg.get('mass', 1.0)
        self.e_ball_paddle = cfg.get('e_ball_paddle', 1.0) 
        self.mu_ball_paddle = cfg.get('mu_ball_paddle', 0.4) 
        self.enable_spin = cfg.get('enable_spin', True)
        self.magnus_factor = cfg.get('magnus_factor', 0.01)
        self.speed_increment = cfg.get('speed_increment', 0.002) 
        self.speed_scale_every = cfg.get('speed_scale_every', 3) 
        self.initial_ball_speed = cfg.get('initial_ball_speed', 0.02) 
        self.initial_angle_range_deg = cfg.get('initial_angle_deg_range', [-60, 60])
        self.initial_direction_serves_down = cfg.get('initial_direction_serves_down', True)

        self.freeze_duration = cfg.get('freeze_duration_ms', GameSettings.FREEZE_DURATION_MS)
        self.countdown_seconds = cfg.get('countdown_seconds', GameSettings.COUNTDOWN_SECONDS)
        self.bg_music = cfg.get("bg_music", "bg_music.mp3")

        self.trail = [] 
        self.max_trail_length = 20

        # 移除舊的技能相關屬性，因為 PlayerState 現在管理技能實例
        # self.skills = {} 
        # self.bug_skill_active = False
        # self.paddle_color = None

        self.round_concluded_by_skill = False

        if DEBUG_ENV: print("[SKILL_DEBUG][PongDuelEnv.__init__] Env Initialization complete (skills linked).")
        self.reset()

    def _create_skill(self, skill_code, owner_player_state):
        """根據技能代碼創建並返回技能實例，或在無效時返回 None。"""
        if not skill_code or skill_code.lower() == 'none':
            if DEBUG_ENV: print(f"[SKILL_DEBUG][PongDuelEnv._create_skill] No skill_code provided for {owner_player_state.identifier}.")
            return None

        # ⭐️ 技能類映射表
        available_skills = {
            "long_paddle": LongPaddleSkill,
            "slowmo": SlowMoSkill,
            "soul_eater_bug": SoulEaterBugSkill, # SoulEaterBugSkill 適配較複雜，暫時先列出
        }
        skill_class = available_skills.get(skill_code)

        if skill_class:
            try:
                skill_instance = skill_class(self, owner_player_state) # 傳遞 env 和 owner
                if DEBUG_ENV: print(f"[SKILL_DEBUG][PongDuelEnv._create_skill] Created skill '{skill_code}' for {owner_player_state.identifier}.")
                return skill_instance
            except Exception as e:
                print(f"[SKILL_DEBUG][PongDuelEnv._create_skill] Error creating skill '{skill_code}' for {owner_player_state.identifier}: {e}")
                return None
        else:
            print(f"[SKILL_DEBUG][PongDuelEnv._create_skill] Unknown skill_code '{skill_code}' for {owner_player_state.identifier}.")
            return None

    def activate_skill(self, player_state_object):
        """啟用指定 PlayerState 對象的技能。"""
        if player_state_object and player_state_object.skill_instance:
            if DEBUG_ENV: print(f"[SKILL_DEBUG][PongDuelEnv.activate_skill] Attempting to activate skill for {player_state_object.identifier}.")
            activated = player_state_object.skill_instance.activate()
            if activated:
                 if DEBUG_ENV: print(f"[SKILL_DEBUG][PongDuelEnv.activate_skill] Skill for {player_state_object.identifier} ACTIVATED successfully.")
            else:
                 if DEBUG_ENV: print(f"[SKILL_DEBUG][PongDuelEnv.activate_skill] Skill for {player_state_object.identifier} FAILED to activate (e.g., on cooldown or already active).")
        elif DEBUG_ENV:
            owner_id = player_state_object.identifier if player_state_object else "UNKNOWN_PLAYER_OBJECT"
            has_skill_instance = "YES" if player_state_object and player_state_object.skill_instance else "NO"
            print(f"[SKILL_DEBUG][PongDuelEnv.activate_skill] Cannot activate skill for {owner_id}, skill_instance present: {has_skill_instance}.")


    def reset_ball_after_score(self, scored_by_player1):
        # ... (此方法內容保持不變) ...
        if DEBUG_ENV: print(f"[PongDuelEnv.reset_ball_after_score] Ball reset. Scored by player1: {scored_by_player1}")
        self.round_concluded_by_skill = False
        self.bounces = 0
        self.spin = 0
        self.trail.clear()

        angle_deg = random.uniform(*self.initial_angle_range_deg)
        angle_rad = np.radians(angle_deg)
        serve_from_player1_area = not scored_by_player1 
        if serve_from_player1_area:
            self.ball_y = 1.0 - self.paddle_height_normalized - self.ball_radius_normalized - 0.05 
            vy_sign = -1 
        else:
            self.ball_y = self.paddle_height_normalized + self.ball_radius_normalized + 0.05 
            vy_sign = 1 
        self.ball_x = 0.5 
        self.ball_vx = self.initial_ball_speed * np.sin(angle_rad)
        self.ball_vy = self.initial_ball_speed * np.cos(angle_rad) * vy_sign
        
        # ⭐️ 重置時停用雙方技能 (PlayerState.reset_state 內部已處理)
        # 但為確保，這裡可以再次檢查並停用
        if self.player1.skill_instance and self.player1.skill_instance.is_active():
            if DEBUG_ENV: print(f"[SKILL_DEBUG][PongDuelEnv.reset_ball_after_score] Deactivating P1 skill: {self.player1.skill_instance.__class__.__name__}")
            self.player1.skill_instance.deactivate()
        if self.opponent.skill_instance and self.opponent.skill_instance.is_active():
            if DEBUG_ENV: print(f"[SKILL_DEBUG][PongDuelEnv.reset_ball_after_score] Deactivating Opponent skill: {self.opponent.skill_instance.__class__.__name__}")
            self.opponent.skill_instance.deactivate()


    def reset(self):
        if DEBUG_ENV: print("[SKILL_DEBUG][PongDuelEnv.reset] Full reset triggered.")
        # PlayerState.reset_state 會處理其自身屬性的重置，包括球拍寬度、顏色和停用技能
        self.player1.reset_state()
        self.opponent.reset_state()

        # 重新發球
        self.reset_ball_after_score(scored_by_player1=random.choice([True, False]))
        self.time_scale = 1.0 # ⭐️ 全局時間尺度重置

        # 確保 Env 層面的技能相關狀態也正確
        # 例如，如果技能會修改 env.time_scale，這裡要重置。
        # SoulEaterBugSkill 修改的 env.bug_skill_active 等也需要考慮。
        # 目前 LongPaddleSkill 不直接修改 env 全局狀態 (除了間接通過 owner)。
        
        return self._get_obs(), {}

    def _get_obs(self):
        # ... (此方法內容保持不變) ...
        obs_array = [
            self.ball_x, self.ball_y,
            self.ball_vx, self.ball_vy,
            self.player1.x, self.opponent.x,
        ]
        return np.array(obs_array, dtype=np.float32)

    def get_lives(self):
        # ... (此方法內容保持不變) ...
        return self.player1.lives, self.opponent.lives

    def _scale_difficulty(self):
        # ... (此方法內容保持不變) ...
        speed_multiplier = 1 + (self.bounces // self.speed_scale_every) * self.speed_increment
        current_speed_magnitude = math.sqrt(self.ball_vx**2 + self.ball_vy**2)
        target_speed_magnitude = self.initial_ball_speed * speed_multiplier
        if current_speed_magnitude > 0 :
            scale_factor = target_speed_magnitude / current_speed_magnitude
            self.ball_vx *= scale_factor
            self.ball_vy *= scale_factor
        else: 
            angle_rad = math.atan2(self.ball_vx, self.ball_vy) if current_speed_magnitude !=0 else random.uniform(0, 2*math.pi)
            self.ball_vx = target_speed_magnitude * math.sin(angle_rad)
            self.ball_vy = target_speed_magnitude * math.cos(angle_rad)

    def step(self, player1_action_input, opponent_action_input):
        current_time_ticks = pygame.time.get_ticks()

        if self.freeze_timer > 0:
            if current_time_ticks - self.freeze_timer < self.freeze_duration:
                return self._get_obs(), 0, False, False, {}
            else:
                self.freeze_timer = 0

        self.player1.prev_x = self.player1.x
        self.opponent.prev_x = self.opponent.x
        old_ball_y_for_collision = self.ball_y

        # ⭐️ 更新技能狀態 (P1)
        if self.player1.skill_instance and self.player1.skill_instance.is_active():
            # print(f"[TEMP_DEBUG] Updating P1 skill: {self.player1.skill_instance.__class__.__name__}")
            self.player1.skill_instance.update()
        
        # ⭐️ 更新技能狀態 (Opponent)
        if self.opponent.skill_instance and self.opponent.skill_instance.is_active():
            # print(f"[TEMP_DEBUG] Updating Opponent skill: {self.opponent.skill_instance.__class__.__name__}")
            self.opponent.skill_instance.update()
            
        # ⭐️ 全局時間尺度 (如果有多個技能影響時間，需要決策邏輯)
        # 暫時簡化：如果 P1 的 slowmo 啟用，則使用 P1 的時間尺度。
        # 如果 P2 的 slowmo 也啟用，且更慢，則使用 P2 的。 (或取最小值)
        # 這個邏輯需要根據 SlowMoSkill 的具體實現來調整。
        # 目前 SlowMoSkill 修改的是 env.time_scale，這會導致後者覆蓋前者。
        # 更好的做法是技能返回其期望的 time_scale，然後 env 取最小值。
        # 為了簡單起見，我們暫時假設技能 update 會直接修改 self.time_scale。
        # 在技能 update 後，重置 self.time_scale，然後由技能決定是否再次修改。
        self.time_scale = 1.0 # 預設為正常速度
        if self.player1.skill_instance and isinstance(self.player1.skill_instance, SlowMoSkill) and self.player1.skill_instance.is_active():
             self.time_scale = self.player1.skill_instance.slow_time_scale # 假設 SlowMoSkill 有此屬性
        if self.opponent.skill_instance and isinstance(self.opponent.skill_instance, SlowMoSkill) and self.opponent.skill_instance.is_active():
             # 如果兩者都啟用慢動作，取更慢的那個 (或者其他合併邏輯)
             opponent_slowmo_scale = self.opponent.skill_instance.slow_time_scale
             if opponent_slowmo_scale < self.time_scale : self.time_scale = opponent_slowmo_scale


        # 移動處理 (與之前相同)
        player_move_speed = 0.03
        ts = self.time_scale
        if player1_action_input == 0: self.player1.x -= player_move_speed * ts
        elif player1_action_input == 2: self.player1.x += player_move_speed * ts
        if opponent_action_input == 0: self.opponent.x -= player_move_speed * ts
        elif opponent_action_input == 2: self.opponent.x += player_move_speed * ts
        self.player1.x = np.clip(self.player1.x, 0.0, 1.0)
        self.opponent.x = np.clip(self.opponent.x, 0.0, 1.0)

        # ⭐️ 判斷是否執行預設球體物理
        run_normal_ball_physics = True
        # 如果 P1 的技能覆蓋物理
        if self.player1.skill_instance and self.player1.skill_instance.is_active() and self.player1.skill_instance.overrides_ball_physics:
            run_normal_ball_physics = False
            if DEBUG_ENV: print(f"[SKILL_DEBUG][PongDuelEnv.step] P1 skill '{self.player1.skill_instance.__class__.__name__}' overrides ball physics.")
        # 如果 Opponent 的技能覆蓋物理 (如果 P1 未覆蓋)
        elif self.opponent.skill_instance and self.opponent.skill_instance.is_active() and self.opponent.skill_instance.overrides_ball_physics:
            run_normal_ball_physics = False
            if DEBUG_ENV: print(f"[SKILL_DEBUG][PongDuelEnv.step] Opponent skill '{self.opponent.skill_instance.__class__.__name__}' overrides ball physics.")


        # 球物理更新、碰撞及計分邏輯 (與之前相同，但現在 run_normal_ball_physics 控制是否執行)
        info = {} # 用於返回額外信息，例如得分者
        reward = 0
        done = False
        game_over = False

        if run_normal_ball_physics:
            if self.enable_spin: # ... (spin logic)
                spin_force_x = self.magnus_factor * self.spin * self.ball_vy if self.ball_vy !=0 else 0
                self.ball_vx += spin_force_x * ts
            self.ball_x += self.ball_vx * ts # ... (ball movement)
            self.ball_y += self.ball_vy * ts

            self.trail.append((self.ball_x, self.ball_y)) # ... (trail logic)
            if len(self.trail) > self.max_trail_length: self.trail.pop(0)

            if self.ball_x - self.ball_radius_normalized <= 0: # ... (wall collision)
                self.ball_x = self.ball_radius_normalized
                self.ball_vx *= -1
            elif self.ball_x + self.ball_radius_normalized >= 1:
                self.ball_x = 1 - self.ball_radius_normalized
                self.ball_vx *= -1
            
            collided_with_paddle_this_step = False # 重置此標誌

            # 對手球拍 (上方)
            opponent_paddle_surface_y = self.paddle_height_normalized
            opponent_paddle_contact_y = opponent_paddle_surface_y + self.ball_radius_normalized
            opponent_paddle_half_w = self.opponent.paddle_width_normalized / 2
            if old_ball_y_for_collision > opponent_paddle_contact_y and self.ball_y <= opponent_paddle_contact_y:
                if abs(self.ball_x - self.opponent.x) < opponent_paddle_half_w + self.ball_radius_normalized * 0.5:
                    # ... (collision physics with opponent paddle) ...
                    self.ball_y = opponent_paddle_contact_y; vn = self.ball_vy; vt = self.ball_vx
                    u_paddle = (self.opponent.x - self.opponent.prev_x) / ts if ts != 0 else 0
                    vn_post, vt_post, omega_post = collide_sphere_with_moving_plane(vn, vt, u_paddle, self.spin, self.e_ball_paddle, self.mu_ball_paddle, self.mass, self.ball_radius_normalized)
                    self.ball_vy = vn_post; self.ball_vx = vt_post; self.spin = omega_post
                    self.bounces += 1; self._scale_difficulty(); self.sound_manager.play_paddle_hit()
                    collided_with_paddle_this_step = True
                else: 
                    self.opponent.lives -= 1; self.player1.last_hit_time = current_time_ticks
                    self.freeze_timer = current_time_ticks; done = True; info['scorer'] = 'player1'
            elif self.ball_y < 0: 
                 if not collided_with_paddle_this_step:
                    self.opponent.lives -= 1; self.player1.last_hit_time = current_time_ticks
                    self.freeze_timer = current_time_ticks; done = True; info['scorer'] = 'player1'
            
            # 玩家1球拍 (下方)
            if not done:
                player1_paddle_surface_y = 1.0 - self.paddle_height_normalized
                player1_paddle_contact_y = player1_paddle_surface_y - self.ball_radius_normalized
                player1_paddle_half_w = self.player1.paddle_width_normalized / 2
                if old_ball_y_for_collision < player1_paddle_contact_y and self.ball_y >= player1_paddle_contact_y:
                    if abs(self.ball_x - self.player1.x) < player1_paddle_half_w + self.ball_radius_normalized * 0.5:
                        # ... (collision physics with player1 paddle) ...
                        self.ball_y = player1_paddle_contact_y; vn = -self.ball_vy; vt = self.ball_vx
                        u_paddle = (self.player1.x - self.player1.prev_x) / ts if ts != 0 else 0
                        vn_post, vt_post, omega_post = collide_sphere_with_moving_plane(vn, vt, u_paddle, self.spin, self.e_ball_paddle, self.mu_ball_paddle, self.mass, self.ball_radius_normalized)
                        self.ball_vy = -vn_post; self.ball_vx = vt_post; self.spin = omega_post
                        self.bounces += 1; self._scale_difficulty(); self.sound_manager.play_paddle_hit()
                        collided_with_paddle_this_step = True
                    else: 
                        self.player1.lives -= 1; self.opponent.last_hit_time = current_time_ticks
                        self.freeze_timer = current_time_ticks; done = True; info['scorer'] = 'opponent'
                elif self.ball_y > 1.0: 
                    if not collided_with_paddle_this_step:
                        self.player1.lives -= 1; self.opponent.last_hit_time = current_time_ticks
                        self.freeze_timer = current_time_ticks; done = True; info['scorer'] = 'opponent'
        # else: 球的移動和碰撞已由技能處理
        # 如果技能覆蓋物理，技能的 update 方法需要負責檢測碰撞和得分，並設定 done=True, info['scorer']
        # 以及更新 self.player1.lives 或 self.opponent.lives。
        # SoulEaterBugSkill 就需要這樣的邏輯。

        if done and DEBUG_ENV:
            print(f"[SKILL_DEBUG][PongDuelEnv.step] Round ended. Scorer: {info.get('scorer')}. P1 Lives: {self.player1.lives}, Opponent Lives: {self.opponent.lives}")

        game_over = self.player1.lives <= 0 or self.opponent.lives <= 0
        if game_over and done and DEBUG_ENV: # 確保 done 為 True 時才判斷 game_over
            print(f"[SKILL_DEBUG][PongDuelEnv.step] GAME OVER detected.")
        
        return self._get_obs(), reward, done, game_over, info


    def render(self):
        # ... (此方法內容保持不變) ...
        if self.renderer is None:
            if DEBUG_ENV: print("[PongDuelEnv.render] Renderer not initialized. Creating one.")
            self.renderer = Renderer(self) 
        self.renderer.render() 

    def close(self):
        # ... (此方法內容保持不變) ...
        if DEBUG_ENV: print("[PongDuelEnv.close] Closing environment.")
        if self.renderer:
            self.renderer.close() 
            self.renderer = None