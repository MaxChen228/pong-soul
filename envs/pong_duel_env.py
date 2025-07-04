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
from game.skills.purgatory_domain_skill import PurgatoryDomainSkill
from game.skills.skill_config import SKILL_CONFIGS # 確保導入 (activate_skill 會用到)


DEBUG_ENV = False # 你可以將此設為 True 以便調試
DEBUG_ENV_FULLSCREEN = False

class PongDuelEnv:
    def __init__(self,
                 game_mode=GameSettings.GameMode.PLAYER_VS_AI,
                 player1_config=None,
                 opponent_config=None,
                 common_config=None,
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
        self.renderer = None # Renderer 會在第一次 render() 時創建
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
        self.freeze_timer = 0 # 用於回合結束後的短暫停頓
        self.time_scale = 1.0 # 當前遊戲速度的時間縮放因子

        cfg = common_config if common_config else {}

        self.mass = cfg.get('mass', GameSettings.ENV_DEFAULT_MASS)
        self.e_ball_paddle = cfg.get('e_ball_paddle', GameSettings.ENV_DEFAULT_E_BALL_PADDLE)
        self.mu_ball_paddle = cfg.get('mu_ball_paddle', GameSettings.ENV_DEFAULT_MU_BALL_PADDLE)
        self.enable_spin = cfg.get('enable_spin', GameSettings.ENV_DEFAULT_ENABLE_SPIN)
        self.magnus_factor = cfg.get('magnus_factor', GameSettings.PHYSICS_MAGNUS_FACTOR)
        self.speed_increment = cfg.get('speed_increment', GameSettings.ENV_DEFAULT_SPEED_INCREMENT)
        self.speed_scale_every = cfg.get('speed_scale_every', GameSettings.ENV_DEFAULT_SPEED_SCALE_EVERY)
        
        self.initial_ball_speed = cfg.get('initial_speed', GameSettings.BALL_INITIAL_SPEED)
        self.initial_angle_range_deg = cfg.get('initial_angle_deg_range', GameSettings.BALL_INITIAL_ANGLE_DEG_RANGE)
        
        self.freeze_duration = cfg.get('freeze_duration_ms', GameSettings.FREEZE_DURATION_MS) # 回合結束停頓時長
        self.countdown_seconds = cfg.get('countdown_seconds', GameSettings.COUNTDOWN_SECONDS) # 遊戲開始倒數
        self.bg_music = cfg.get("bg_music", "bg_music_level1.mp3") # 背景音樂

        self.trail = [] # 球的拖尾數據
        self.max_trail_length = GameSettings.MAX_TRAIL_LENGTH
        self.ball_visual_key = "default" # 當前球體視覺外觀的鍵名 (例如 "default", "soul_eater_bug")
        self.active_ball_visual_skill_owner = None # 記錄是哪個玩家的技能改變了球體視覺

        self.round_concluded_by_skill = False # 標記當前回合是否由技能（而非常規得分）結束
        self.current_round_info = {} # 儲存當前回合結束的資訊 (得分者，原因等)

        # --- 新增：螢幕中央技能名顯示相關屬性 ---
        self.skill_name_to_display_on_screen = None
        self.skill_name_display_start_time_ms = 0
        # 技能名顯示的總時長 (毫秒)，可以考慮之後移到 Style 或 global_settings.yaml
        self.skill_name_display_duration_ms = 2000 # 例如 2 秒
        self.skill_name_fade_duration_ms = 500   # 最後 0.5 秒用於淡出
        # --- 新增結束 ---

        if DEBUG_ENV: print("[SKILL_DEBUG][PongDuelEnv.__init__] Env Initialization complete (skills linked).")
        self.reset() # 初始化環境狀態，包括球的位置和第一次發球

    def _create_skill(self, skill_code, owner_player_state):
        if not skill_code or skill_code.lower() == 'none':
            if DEBUG_ENV: print(f"[SKILL_DEBUG][PongDuelEnv._create_skill] No skill_code provided for {owner_player_state.identifier}.")
            return None
        available_skills = {
            "long_paddle": LongPaddleSkill,
            "slowmo": SlowMoSkill,
            "soul_eater_bug": SoulEaterBugSkill,
            "purgatory_domain": PurgatoryDomainSkill, # <-- 新增這行
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
                
                # --- 新增：觸發螢幕中央技能名顯示 ---
                skill_code = player_state_object.skill_code_name
                if skill_code:
                    skill_config_for_name = SKILL_CONFIGS.get(skill_code, {})
                    name_to_show = skill_config_for_name.get("display_name_zh_full", skill_code.upper()) # 預設回退到大寫技能代碼
                    
                    self.skill_name_to_display_on_screen = name_to_show
                    self.skill_name_display_start_time_ms = pygame.time.get_ticks()
                    if DEBUG_ENV:
                        print(f"    Central Skill Name Triggered: '{name_to_show}', StartTime: {self.skill_name_display_start_time_ms}")
                # --- 新增結束 ---

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
        # AI (self.opponent) is the top paddle in pong-soul's PvA mode.
        # This observation needs to match the perspective of Player A (top paddle)
        # in your training environment (my_pong_env_2p.py).

        # Ball position and velocity from pong-soul's perspective
        ball_x_ps = self.ball_x
        ball_y_ps = self.ball_y
        ball_vx_ps = self.ball_vx
        ball_vy_ps = self.ball_vy

        # Paddle positions from pong-soul's perspective
        ai_paddle_x_ps = self.opponent.x  # This is "my_paddle_x" for the AI
        player_paddle_x_ps = self.player1.x # This is "other_paddle_x" for the AI

        # Spin
        current_spin = self.spin

        # --- Apply transformations to match training environment's Player A ---
        # 1. Ball Y coordinate: Inverted (1.0 - original_y) for top paddle perspective
        obs_ball_y = 1.0 - ball_y_ps

        # 2. Ball Y velocity: Inverted (-original_vy) for top paddle perspective
        obs_ball_vy = -ball_vy_ps

        # 3. My (AI's) paddle X: Directly use ai_paddle_x_ps
        obs_my_paddle_x = ai_paddle_x_ps

        # 4. Other (Player's) paddle X: Directly use player_paddle_x_ps
        obs_other_paddle_x = player_paddle_x_ps

        # 5. Ball X, Ball VX, Spin: No change in perspective needed for these relative to the field
        obs_ball_x = ball_x_ps
        obs_ball_vx = ball_vx_ps
        obs_spin = current_spin

        obs_for_ai_agent = [
            obs_ball_x,
            obs_ball_y,
            obs_ball_vx,
            obs_ball_vy,
            obs_my_paddle_x,
            obs_other_paddle_x,
            obs_spin
        ]
        
        # DEBUG_ENV is a flag you might have at the top of this file
        if DEBUG_ENV: # Or replace with a more specific debug flag if you prefer
            print(f"[DEBUG_PONG_DUEL_ENV_GET_OBS] Raw (pong-soul): ball_y={ball_y_ps:.3f}, ball_vy={ball_vy_ps:.3f}, opp_x={ai_paddle_x_ps:.3f}, p1_x={player_paddle_x_ps:.3f}, spin={current_spin:.3f}")
            print(f"[DEBUG_PONG_DUEL_ENV_GET_OBS] Observation for AI: ball_x={obs_ball_x:.3f}, ball_y={obs_ball_y:.3f}, ball_vx={obs_ball_vx:.3f}, ball_vy={obs_ball_vy:.3f}, my_paddle_x={obs_my_paddle_x:.3f}, other_paddle_x={obs_other_paddle_x:.3f}, spin={obs_spin:.3f}")

        return np.array(obs_for_ai_agent, dtype=np.float32)
    
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
        
        player_base_move_speed = GameSettings.PLAYER_MOVE_SPEED
        
        # --- Player 1 移動計算 ---
        p1_current_speed_multiplier = 1.0 # 預設
        if self.player1.skill_instance and hasattr(self.player1.skill_instance, 'owner_paddle_speed_multiplier'):
             # 例如 SlowMoSkill 可能會改變自己的板子速度
            p1_current_speed_multiplier = self.player1.skill_instance.owner_paddle_speed_multiplier \
                if self.player1.skill_instance.is_active() and hasattr(self.player1.skill_instance, 'active') \
                else self.player1.current_paddle_speed_multiplier # 如果技能沒有active屬性或未啟用，則使用PlayerState的
        else:
            p1_current_speed_multiplier = self.player1.current_paddle_speed_multiplier


        p1_effective_move_speed = player_base_move_speed * p1_current_speed_multiplier
        if player1_action_input == 0: 
            self.player1.x -= p1_effective_move_speed * time_scale
        elif player1_action_input == 2: 
            self.player1.x += p1_effective_move_speed * time_scale
        
        # --- Opponent 移動計算 ---
        opp_current_speed_multiplier = 1.0 # 預設
        # 檢查是否 Player1 的 PurgatoryDomainSkill 啟用並影響對手
        purgatory_active_by_p1 = False
        purgatory_slowdown_factor_from_p1 = 1.0
        if self.player1.skill_instance and \
           isinstance(self.player1.skill_instance, PurgatoryDomainSkill) and \
           self.player1.skill_instance.is_active():
            purgatory_active_by_p1 = True
            purgatory_slowdown_factor_from_p1 = self.player1.skill_instance.opponent_paddle_slowdown_factor
            if DEBUG_ENV: print(f"[SKILL_DEBUG][PongDuelEnv] P1's Purgatory affecting Opponent paddle speed with factor: {purgatory_slowdown_factor_from_p1}")

        # 檢查是否 Opponent 自己的 SlowMoSkill 等技能啟用並影響自己
        opp_self_skill_multiplier = 1.0
        if self.opponent.skill_instance and hasattr(self.opponent.skill_instance, 'owner_paddle_speed_multiplier'):
            opp_self_skill_multiplier = self.opponent.skill_instance.owner_paddle_speed_multiplier \
                if self.opponent.skill_instance.is_active() and hasattr(self.opponent.skill_instance, 'active') \
                else self.opponent.current_paddle_speed_multiplier
        else:
            opp_self_skill_multiplier = self.opponent.current_paddle_speed_multiplier
            
        # 最終對手速度倍率：取 Purgatory 的影響 和 對手自身技能影響 的最小值（如果 Purgatory 是減速）
        # 或者更合理的：Purgatory 的減速應該優先於對手自身的加速（如果有的話）
        if purgatory_active_by_p1:
            # 如果 Purgatory 啟動，對手的速度受到其 slowdown_factor 影響
            # 同時，如果對手自己有加速技能，這個加速效果也應該被 Purgatory 的減速所調和
            # 例如：基礎速度 * Purgatory減速 * 對手自身技能加速 (如果 Purgatory減速是0.8, 對手加速是1.2, 則 0.8*1.2)
            # 或者，如果 Purgatory 是主導的負面效果，可以直接使用其因子，或取更嚴格的那個
            opp_current_speed_multiplier = opp_self_skill_multiplier * purgatory_slowdown_factor_from_p1
            if DEBUG_ENV and purgatory_slowdown_factor_from_p1 != 1.0 : print(f"Opponent speed affected by P1 Purgatory: final_mult={opp_current_speed_multiplier}")
        else:
            opp_current_speed_multiplier = opp_self_skill_multiplier


        opp_effective_move_speed = player_base_move_speed * opp_current_speed_multiplier
        if opponent_action_input == 0: 
            self.opponent.x -= opp_effective_move_speed * time_scale
        elif opponent_action_input == 2: 
            self.opponent.x += opp_effective_move_speed * time_scale

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
        # --- 新增：檢查螢幕中央技能名顯示是否結束 ---
        if self.skill_name_to_display_on_screen is not None:
            if current_time_ticks - self.skill_name_display_start_time_ms >= self.skill_name_display_duration_ms:
                self.skill_name_to_display_on_screen = None # 顯示時間到，清除
                if DEBUG_ENV:
                    print(f"    Central Skill Name Display timed out. Cleared.")
        # --- 新增結束 ---

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
            # --- 新增傳遞給 Renderer 的技能名顯示資訊 ---
            "central_skill_name_text": self.skill_name_to_display_on_screen,
            "central_skill_name_start_time_ms": self.skill_name_display_start_time_ms,
            "central_skill_name_duration_ms": self.skill_name_display_duration_ms,
            "central_skill_name_fade_duration_ms": self.skill_name_fade_duration_ms,
            # --- 新增結束 ---
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
        current_time_ticks = pygame.time.get_ticks() # 獲取當前時間，用於計時器等

        # 1. 處理凍結時間 (如果有的話)
        if self.freeze_timer > 0:
            if current_time_ticks - self.freeze_timer < self.freeze_duration:
                # 仍在凍結時間內，不執行任何遊戲邏輯更新，直接返回當前觀察值
                return self._get_obs(), 0, False, False, {'scorer': None, 'reason': None}
            else:
                self.freeze_timer = 0 # 凍結時間結束

        # 2. 決定當前的時間縮放 (例如，受 SlowMoSkill 影響)
        current_time_scale = self._determine_time_scale()
        self.time_scale = current_time_scale # 更新環境的時間縮放因子

        # 3. 更新玩家板子的位置
        self._update_player_positions(player1_action_input, opponent_action_input, current_time_scale)

        # 4. 記錄球體在物理更新前的位置 (用於碰撞檢測)
        old_ball_y_for_collision = self.ball_y

        # 5. 重置回合結束標誌 (這些標誌可能被技能或常規物理設定)
        self.round_concluded_by_skill = False
        self.current_round_info = {'scorer': None, 'reason': None} # 提供預設鍵

        # 6. 更新啟用技能的內部狀態 (例如，檢查持續時間)
        self._update_active_skills() # 這個方法只更新技能的計時器等，不處理球體物理

        # 7. 檢查是否有技能覆寫了球體物理
        active_physics_override_skill_owner = None
        active_skill_instance = None

        if self.player1.skill_instance and \
           self.player1.skill_instance.is_active() and \
           getattr(self.player1.skill_instance, 'overrides_ball_physics', False):
            active_physics_override_skill_owner = self.player1
            active_skill_instance = self.player1.skill_instance
        elif self.opponent.skill_instance and \
             self.opponent.skill_instance.is_active() and \
             getattr(self.opponent.skill_instance, 'overrides_ball_physics', False):
            active_physics_override_skill_owner = self.opponent
            active_skill_instance = self.opponent.skill_instance

        run_normal_ball_physics = True # 預設執行常規物理
        round_done_by_skill_override = False
        info_from_skill_override = {'scorer': None, 'reason': None}


        if active_physics_override_skill_owner and active_skill_instance:
            if DEBUG_ENV: # 使用您環境的全域 DEBUG_ENV 旗標
                print(f"[SKILL_DEBUG][PongDuelEnv.step] Physics overridden by {active_physics_override_skill_owner.identifier}'s skill: {active_skill_instance.__class__.__name__}")

            # 檢查是否是 PurgatoryDomainSkill，並調用其專用方法
            if isinstance(active_skill_instance, PurgatoryDomainSkill):
                run_normal_ball_physics = False # 技能將處理球體
                target_player = self.opponent if active_physics_override_skill_owner == self.player1 else self.player1
                
                # 調用技能的球體更新方法
                new_ball_x, new_ball_y, new_ball_vx, new_ball_vy, new_spin, \
                round_done_by_skill_override, info_from_skill_override = active_skill_instance.update_ball_in_domain(
                    current_ball_x=self.ball_x, current_ball_y=self.ball_y,
                    current_ball_vx=self.ball_vx, current_ball_vy=self.ball_vy,
                    current_spin=self.spin,
                    dt=current_time_scale, # 傳遞 dt
                    target_player_state=target_player,
                    owner_player_state=active_physics_override_skill_owner,
                    env_paddle_height_norm=self.paddle_height_normalized,
                    env_ball_radius_norm=self.ball_radius_normalized,
                    env_render_size=self.render_size
                )
                # 更新環境中的球體狀態
                self.ball_x, self.ball_y = new_ball_x, new_ball_y
                self.ball_vx, self.ball_vy = new_ball_vx, new_ball_vy
                self.spin = new_spin

                if round_done_by_skill_override:
                    self.round_concluded_by_skill = True # 標記回合由技能結束
                    self.current_round_info = info_from_skill_override
                    # 如果技能導致得分，也應該觸發凍結
                    if info_from_skill_override.get('scorer') is not None:
                        self.freeze_timer = pygame.time.get_ticks()
                    if DEBUG_ENV:
                        print(f"[SKILL_DEBUG][PongDuelEnv.step] Round concluded by PurgatoryDomainSkill. Info: {self.current_round_info}")
            
            # (未來可以為其他覆寫物理的技能添加 elif isinstance(...) 判斷)

        # 8. 根據 run_normal_ball_physics 決定是否執行常規球體物理
        reward = 0 # 獎勵值 (主要用於強化學習，此處可保持為0)
        round_done_by_normal_physics = False
        info_from_normal_physics = {'scorer': None, 'reason': None}

        if run_normal_ball_physics:
            self._apply_ball_movement_and_physics(current_time_scale)
            self._handle_wall_collisions()
            collided_with_paddle_this_step = self._handle_paddle_collisions(old_ball_y_for_collision, current_time_scale)
            round_done_by_normal_physics, info_from_normal_physics = self._check_scoring_and_resolve_round(collided_with_paddle_this_step)
            
            if round_done_by_normal_physics and DEBUG_ENV:
                print(f"[NORMAL_PHYSICS][PongDuelEnv.step] Round ended by NORMAL physics. Scorer: {info_from_normal_physics.get('scorer')}. P1 Lives: {self.player1.lives}, Opponent Lives: {self.opponent.lives}")
        
        # 9. 整合回合結束狀態和遊戲結束狀態
        final_round_done = self.round_concluded_by_skill or round_done_by_normal_physics
        final_game_over = False # 預設遊戲未結束
        final_info_to_return = {'scorer': None, 'reason': None} # 確保有預設鍵

        if self.round_concluded_by_skill: # 如果是技能導致回合結束
            final_info_to_return.update(self.current_round_info)
        elif round_done_by_normal_physics: # 如果是常規物理導致回合結束
            final_info_to_return.update(info_from_normal_physics)
        
        if final_round_done:
            # 檢查任一方生命值是否耗盡
            final_game_over = self.player1.lives <= 0 or self.opponent.lives <= 0
            if final_game_over and DEBUG_ENV:
                winner = "Opponent" if self.player1.lives <= 0 else "Player1"
                if self.round_concluded_by_skill and self.current_round_info.get('scorer'):
                    winner_identifier = self.current_round_info['scorer']
                    if winner_identifier == self.player1.identifier: winner = "Player1 (Skill)"
                    elif winner_identifier == self.opponent.identifier: winner = "Opponent (Skill)"
                elif round_done_by_normal_physics and info_from_normal_physics.get('scorer'):
                    winner_identifier = info_from_normal_physics['scorer']
                    if winner_identifier == 'player1': winner = "Player1 (Normal)"
                    elif winner_identifier == 'opponent': winner = "Opponent (Normal)"

                print(f"[PongDuelEnv.step] GAME OVER detected. Winner: {winner} (P1 Lives: {self.player1.lives}, Opp Lives: {self.opponent.lives})")
            
        # 10. 返回觀察值、獎勵、回合結束標誌、遊戲結束標誌、以及回合信息
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