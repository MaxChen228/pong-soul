# envs/pong_duel_env.py
import numpy as np
import pygame
import random
import math

from game.theme import Style
from game.physics import collide_sphere_with_moving_plane # 雖然可能不會直接用到，但保留以防萬一
from game.sound import SoundManager
from game.render import Renderer # Renderer 將被修改
from game.settings import GameSettings
from game.player_state import PlayerState

from game.skills.long_paddle_skill import LongPaddleSkill
from game.skills.slowmo_skill import SlowMoSkill
from game.skills.soul_eater_bug_skill import SoulEaterBugSkill

DEBUG_ENV = True
DEBUG_ENV_FULLSCREEN = True # ⭐️ 新增排錯開關

class PongDuelEnv:
    def __init__(self,
                 game_mode=GameSettings.GameMode.PLAYER_VS_AI,
                 player1_config=None,
                 opponent_config=None,
                 common_config=None,
                 render_size=400, # ⭐️ 這將是邏輯渲染尺寸
                 paddle_height_px=10, # ⭐️ 邏輯球拍高度
                 ball_radius_px=10,   # ⭐️ 邏輯球半徑
                 initial_main_screen_surface_for_renderer=None # ⭐️ 新增參數
                ):

        if DEBUG_ENV: print(f"[SKILL_DEBUG][PongDuelEnv.__init__] Initializing with game_mode: {game_mode}")
        if DEBUG_ENV_FULLSCREEN:
            print(f"[DEBUG_ENV_FULLSCREEN][PongDuelEnv.__init__] Received initial_main_screen_surface: {type(initial_main_screen_surface_for_renderer)}")

        self.game_mode = game_mode
        self.sound_manager = SoundManager()
        self.renderer = None # Renderer 將在第一次調用 render() 時創建
        self.render_size = render_size # 儲存邏輯渲染尺寸
        self.paddle_height_px = paddle_height_px
        self.ball_radius_px = ball_radius_px
        
        # ⭐️ 將提供的 main_screen surface 儲存起來，以便傳遞給 Renderer
        self.provided_main_screen_surface = initial_main_screen_surface_for_renderer

        # 正規化尺寸是基於邏輯 render_size
        self.paddle_height_normalized = self.paddle_height_px / self.render_size if self.render_size > 0 else 0
        self.ball_radius_normalized = self.ball_radius_px / self.render_size if self.render_size > 0 else 0


        default_p_config = {'initial_x': 0.5, 'initial_paddle_width': 60, 'initial_lives': 3, 'skill_code': None, 'is_ai': False}
        p1_conf = player1_config if player1_config else default_p_config.copy()
        opp_conf = opponent_config if opponent_config else {**default_p_config.copy(), 'is_ai': (game_mode == GameSettings.GameMode.PLAYER_VS_AI)}

        self.player1 = PlayerState(
            initial_x=p1_conf.get('initial_x', 0.5),
            initial_paddle_width=p1_conf.get('initial_paddle_width', 60), # 這是邏輯寬度
            initial_lives=p1_conf.get('initial_lives', 3),
            skill_code=p1_conf.get('skill_code'),
            is_ai=p1_conf.get('is_ai', False),
            env_render_size=self.render_size, # PlayerState 也需要邏輯 render_size
            player_identifier="player1"
        )
        self.opponent = PlayerState(
            initial_x=opp_conf.get('initial_x', 0.5),
            initial_paddle_width=opp_conf.get('initial_paddle_width', 60), # 這是邏輯寬度
            initial_lives=opp_conf.get('initial_lives', 3),
            skill_code=opp_conf.get('skill_code'),
            is_ai=opp_conf.get('is_ai', game_mode == GameSettings.GameMode.PLAYER_VS_AI),
            env_render_size=self.render_size, # PlayerState 也需要邏輯 render_size
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

        cfg = common_config if common_config else {}
        self.mass = cfg.get('mass', 1.0)
        self.e_ball_paddle = cfg.get('e_ball_paddle', 1.0)
        self.mu_ball_paddle = cfg.get('mu_ball_paddle', 0.4)
        self.enable_spin = cfg.get('enable_spin', True)
        self.magnus_factor = cfg.get('magnus_factor', 0.01)
        self.speed_increment = cfg.get('speed_increment', 0.002)
        self.speed_scale_every = cfg.get('speed_scale_every', 3)
        self.initial_ball_speed = cfg.get('initial_ball_speed', 0.02)
        self.initial_angle_range_deg = cfg.get('initial_angle_deg_range', [-60, 60]) # 保持原樣，之前是 initial_angle_deg_range
        self.initial_direction_serves_down = cfg.get('initial_direction_serves_down', True) # 假設P1在下，AI/P2在上

        self.freeze_duration = cfg.get('freeze_duration_ms', GameSettings.FREEZE_DURATION_MS)
        self.countdown_seconds = cfg.get('countdown_seconds', GameSettings.COUNTDOWN_SECONDS)
        self.bg_music = cfg.get("bg_music", "bg_music_level1.mp3") # 從 common_config 中獲取

        self.trail = []
        self.ball_visual_key = "default" # 球的當前視覺類型鍵名 ("default", "soul_eater_bug", etc.)
        self.active_ball_visual_skill_owner = None # 記錄是哪個玩家的技能正在覆蓋球的視覺
        self.max_trail_length = 20 # 拖尾長度

        self.round_concluded_by_skill = False
        self.current_round_info = {} # 用於技能回傳的回合信息

        if DEBUG_ENV: print("[SKILL_DEBUG][PongDuelEnv.__init__] Env Initialization complete (skills linked).")
        self.reset() # 調用 reset 以初始化球的狀態等

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
        """
        由技能調用，以請求改變球的視覺外觀。
        owner_identifier 用於處理多個技能可能嘗試同時影響球視覺的情況 (雖然目前不太可能)。
        """
        if DEBUG_ENV: 
            print(f"[SKILL_DEBUG][PongDuelEnv.set_ball_visual_override] Called by skill '{skill_identifier}', active: {active}, owner: {owner_identifier}")

        if active:
            # 如果目前沒有其他技能覆蓋，或者請求的技能與當前覆蓋的技能擁有者相同
            if self.active_ball_visual_skill_owner is None or self.active_ball_visual_skill_owner == owner_identifier:
                self.ball_visual_key = skill_identifier # 例如 "soul_eater_bug"
                self.active_ball_visual_skill_owner = owner_identifier
                if DEBUG_ENV: print(f"    Ball visual set to '{self.ball_visual_key}' by {owner_identifier}.")
            else: # 其他玩家的技能正在覆蓋
                if DEBUG_ENV: print(f"    Ball visual override IGNORED. Currently overridden by {self.active_ball_visual_skill_owner}'s skill.")
        else:
            # 只有當取消請求來自當前正在覆蓋視覺的技能擁有者時，才恢復預設
            if self.active_ball_visual_skill_owner == owner_identifier or self.ball_visual_key == skill_identifier: # 後一個條件是為了處理擁有者未正確傳遞的情況
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

        angle_deg = random.uniform(*self.initial_angle_range_deg)
        angle_rad = np.radians(angle_deg)
        
        # 根據誰得分決定發球方向和位置
        # 如果 P1 得分 (scored_by_player1=True)，則球從 P2 (上方) 區域發出，向下運動
        # 如果 P2/AI 得分 (scored_by_player1=False)，則球從 P1 (下方) 區域發出，向上運動
        serve_from_top_area = scored_by_player1 # P1得分，對手從頂部發球
        
        if serve_from_top_area: # 從頂部 (P2/AI) 區域發球
            self.ball_y = self.paddle_height_normalized + self.ball_radius_normalized + 0.05
            vy_sign = 1 # 向下為正 (如果 Y 軸 0 在頂部，1 在底部)
        else: # 從底部 (P1) 區域發球
            self.ball_y = 1.0 - self.paddle_height_normalized - self.ball_radius_normalized - 0.05
            vy_sign = -1 # 向上為負

        # 球的初始速度方向也需要根據發球區域調整
        # 如果是從 P1 (下方) 發球向上，且 initial_direction_serves_down = True (預設球向下發)，則 vy_sign 需反轉。
        # 簡化：vy_sign 已經決定了球的垂直運動方向。cos(angle_rad) 通常為正。
        
        self.ball_x = 0.5
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
        self.reset_ball_after_score(scored_by_player1=random.choice([True, False]))
        self.time_scale = 1.0
        return self._get_obs(), {}

    def _get_obs(self):
        obs_array = [
            self.ball_x, self.ball_y,
            self.ball_vx, self.ball_vy,
            self.player1.x, self.opponent.x,
            # 可以考慮加入更多狀態，如技能冷卻時間、球拍寬度等，如果AI需要這些信息
            # self.player1.paddle_width_normalized, self.opponent.paddle_width_normalized,
            # self.player1.skill_instance.get_energy_ratio() if self.player1.skill_instance else 0.0,
        ]
        return np.array(obs_array, dtype=np.float32)
    def get_render_data(self):
        """
        收集並返回所有渲染所需的遊戲狀態數據。
        """
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
                "visual_params": player1_skill_visual_params # 包含技能的視覺參數
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
                "visual_params": opponent_skill_visual_params # 包含技能的視覺參數
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
                "image_key": self.ball_visual_key # <-- 新增，例如 "default" 或 "soul_eater_bug"
            },
            "player1": {
                "x_norm": self.player1.x,
                "paddle_width_norm": self.player1.paddle_width_normalized, 
                "paddle_color": self.player1.paddle_color,
                "lives": self.player1.lives,
                "max_lives": self.player1.max_lives,
                "skill_data": player1_skill_data_for_ui, # UI條和技能視覺效果都會用到
                "is_ai": self.player1.is_ai, 
                "identifier": self.player1.identifier, 
            },
            "opponent": {
                "x_norm": self.opponent.x,
                "paddle_width_norm": self.opponent.paddle_width_normalized,
                "paddle_color": self.opponent.paddle_color,
                "lives": self.opponent.lives,
                "max_lives": self.opponent.max_lives,
                "skill_data": opponent_skill_data_for_ui, # UI條和技能視覺效果都會用到
                "is_ai": self.opponent.is_ai,
                "identifier": self.opponent.identifier,
            },
            "trail": list(self.trail), 
            "paddle_height_norm": self.paddle_height_normalized, 
            "freeze_active": freeze_active,
            # PongDuelEnv 現在還需要傳遞技能自身的邏輯像素尺寸給 Renderer，以便 Renderer 可以正確縮放
            # 例如 SlowMoSkill 的 clock_radius_logic_px, paddle_trail 的 paddle_width_logic_px 等
            # 這些可以包含在 playerX.skill_data.visual_params 中，由技能的 get_visual_params 提供
            "logical_paddle_height_px": self.paddle_height_px, # Renderer 可能需要這個來畫軌跡
            # self.logical_ball_radius_px 已經在 Renderer init 時傳遞
        }
        return render_data
    def get_lives(self):
        return self.player1.lives, self.opponent.lives

    def _scale_difficulty(self):
        # 根據 bounces 增加球速
        # 確保不會在初始幾次碰撞就變得太快
        if self.bounces > 0 and self.speed_scale_every > 0:
            speed_multiplier = 1 + (self.bounces // self.speed_scale_every) * self.speed_increment
            current_speed_magnitude = math.sqrt(self.ball_vx**2 + self.ball_vy**2)
            
            # 避免除以零，並確保只在速度大於一個非常小的值時才進行縮放
            if current_speed_magnitude > 1e-6: #一個很小的值，避免浮點數問題
                # 新的目標速度不應低於初始速度
                target_speed_magnitude = max(self.initial_ball_speed, self.initial_ball_speed * speed_multiplier)
                
                scale_factor = target_speed_magnitude / current_speed_magnitude
                self.ball_vx *= scale_factor
                self.ball_vy *= scale_factor
                if DEBUG_ENV:
                    print(f"[PongDuelEnv._scale_difficulty] Bounces: {self.bounces}, Multiplier: {speed_multiplier:.3f}, New Speed Mag: {target_speed_magnitude:.4f}")
            # else: # 如果球速幾乎為零，則不進行縮放，等待下一次有效碰撞
            #    if DEBUG_ENV: print(f"[PongDuelEnv._scale_difficulty] Ball speed too low to scale ({current_speed_magnitude:.4e})")


    def step(self, player1_action_input, opponent_action_input):
        current_time_ticks = pygame.time.get_ticks()
        info = {'scorer': None} # 初始化 info，確保 scorer 鍵存在

        if self.freeze_timer > 0:
            if current_time_ticks - self.freeze_timer < self.freeze_duration:
                return self._get_obs(), 0, False, False, info
            else:
                self.freeze_timer = 0

        self.player1.prev_x = self.player1.x
        self.opponent.prev_x = self.opponent.x
        old_ball_y_for_collision = self.ball_y # 用於判斷是否穿過球拍平面

        self.round_concluded_by_skill = False
        self.current_round_info = {} # 重置技能回合信息

        if self.player1.skill_instance and self.player1.skill_instance.is_active():
            self.player1.skill_instance.update()
        if self.opponent.skill_instance and self.opponent.skill_instance.is_active():
            self.opponent.skill_instance.update()

        if self.round_concluded_by_skill: # 如果技能更新導致回合結束
            if DEBUG_ENV: print(f"[SKILL_DEBUG][PongDuelEnv.step] Round concluded by skill. Info: {self.current_round_info}")
            game_over = self.player1.lives <= 0 or self.opponent.lives <= 0
            # 確保 info 字典從 self.current_round_info 更新
            info.update(self.current_round_info)
            return self._get_obs(), 0, True, game_over, info

        self.time_scale = 1.0
        active_slowmo_skill = None
        if self.player1.skill_instance and isinstance(self.player1.skill_instance, SlowMoSkill) and self.player1.skill_instance.is_active():
             active_slowmo_skill = self.player1.skill_instance
        if self.opponent.skill_instance and isinstance(self.opponent.skill_instance, SlowMoSkill) and self.opponent.skill_instance.is_active():
            if active_slowmo_skill is None or self.opponent.skill_instance.slow_time_scale_value < active_slowmo_skill.slow_time_scale_value:
                 active_slowmo_skill = self.opponent.skill_instance
        if active_slowmo_skill:
            self.time_scale = active_slowmo_skill.slow_time_scale_value

        player_move_speed = 0.03 # 正規化移動速度
        ts = self.time_scale     # 當前幀的時間尺度

        if player1_action_input == 0: self.player1.x -= player_move_speed * ts
        elif player1_action_input == 2: self.player1.x += player_move_speed * ts
        if opponent_action_input == 0: self.opponent.x -= player_move_speed * ts
        elif opponent_action_input == 2: self.opponent.x += player_move_speed * ts

        self.player1.x = np.clip(self.player1.x, 0.0, 1.0)
        self.opponent.x = np.clip(self.opponent.x, 0.0, 1.0)

        run_normal_ball_physics = True
        # 檢查是否有技能覆蓋了球的物理邏輯 (例如 SoulEaterBugSkill)
        if self.player1.skill_instance and self.player1.skill_instance.is_active() and self.player1.skill_instance.overrides_ball_physics:
            run_normal_ball_physics = False
        elif self.opponent.skill_instance and self.opponent.skill_instance.is_active() and self.opponent.skill_instance.overrides_ball_physics:
            run_normal_ball_physics = False
        
        reward = 0; done = False; game_over = False

        if run_normal_ball_physics:
            if self.enable_spin:
                spin_force_x = self.magnus_factor * self.spin * self.ball_vy if self.ball_vy != 0 else 0
                self.ball_vx += spin_force_x * ts
            
            self.ball_x += self.ball_vx * ts
            self.ball_y += self.ball_vy * ts

            self.trail.append((self.ball_x, self.ball_y))
            if len(self.trail) > self.max_trail_length: self.trail.pop(0)

            # 牆壁碰撞
            if self.ball_x - self.ball_radius_normalized <= 0:
                self.ball_x = self.ball_radius_normalized
                self.ball_vx *= -1
                # 可以加入撞牆音效 self.sound_manager.play_wall_hit()
            elif self.ball_x + self.ball_radius_normalized >= 1:
                self.ball_x = 1 - self.ball_radius_normalized
                self.ball_vx *= -1
                # 可以加入撞牆音效

            collided_with_paddle_this_step = False # 用於避免球穿過球拍後仍然判得分

            # 對手球拍 (上方) 碰撞檢測
            opponent_paddle_surface_y = self.paddle_height_normalized # 球拍底部邊緣的Y座標
            opponent_paddle_contact_y = opponent_paddle_surface_y + self.ball_radius_normalized # 球心接觸此邊緣時的Y座標
            opponent_paddle_half_w = self.opponent.paddle_width_normalized / 2

            if old_ball_y_for_collision > opponent_paddle_contact_y and self.ball_y <= opponent_paddle_contact_y: # 球從上方穿過接觸線
                if abs(self.ball_x - self.opponent.x) < opponent_paddle_half_w + self.ball_radius_normalized * 0.75: # X軸在球拍範圍內 (略微放寬)
                    self.ball_y = opponent_paddle_contact_y # 校正球的位置，防止穿透
                    vn = self.ball_vy # 法向速度 (向下為正)
                    vt = self.ball_vx # 切向速度
                    u_paddle = (self.opponent.x - self.opponent.prev_x) / ts if ts != 0 else 0 # 球拍切向速度
                    
                    vn_post, vt_post, omega_post = collide_sphere_with_moving_plane(
                        vn, vt, u_paddle, self.spin, self.e_ball_paddle, self.mu_ball_paddle, self.mass, self.ball_radius_normalized
                    )
                    self.ball_vy = vn_post
                    self.ball_vx = vt_post
                    self.spin = omega_post
                    self.bounces += 1
                    self._scale_difficulty()
                    self.sound_manager.play_paddle_hit()
                    collided_with_paddle_this_step = True
                # else: # X軸未在球拍範圍內，但球已越過對手球拍的Y基準線，應視為玩家得分（如果球繼續向下）
                      # 這部分邏輯在下方 ball_y < 0 處理更佳
            
            # 玩家 (下方) 球拍碰撞檢測
            if not done: # 如果尚未結束回合
                player1_paddle_surface_y = 1.0 - self.paddle_height_normalized # 球拍頂部邊緣的Y座標
                player1_paddle_contact_y = player1_paddle_surface_y - self.ball_radius_normalized # 球心接觸此邊緣時的Y座標
                player1_paddle_half_w = self.player1.paddle_width_normalized / 2

                if old_ball_y_for_collision < player1_paddle_contact_y and self.ball_y >= player1_paddle_contact_y: # 球從下方穿過接觸線
                    if abs(self.ball_x - self.player1.x) < player1_paddle_half_w + self.ball_radius_normalized * 0.75: # X軸在球拍範圍內
                        self.ball_y = player1_paddle_contact_y # 校正位置
                        vn = -self.ball_vy # 法向速度 (向上為正，故取反)
                        vt = self.ball_vx
                        u_paddle = (self.player1.x - self.player1.prev_x) / ts if ts != 0 else 0
                        
                        vn_post, vt_post, omega_post = collide_sphere_with_moving_plane(
                            vn, vt, u_paddle, self.spin, self.e_ball_paddle, self.mu_ball_paddle, self.mass, self.ball_radius_normalized
                        )
                        self.ball_vy = -vn_post # 反彈後速度方向改變
                        self.ball_vx = vt_post
                        self.spin = omega_post
                        self.bounces += 1
                        self._scale_difficulty()
                        self.sound_manager.play_paddle_hit()
                        collided_with_paddle_this_step = True
                    # else: # X軸未在球拍範圍內，但球已越過玩家球拍的Y基準線，應視為對手得分（如果球繼續向上）
                          # 這部分邏輯在下方 ball_y > 1.0 處理更佳

            # 得分判斷
            if not collided_with_paddle_this_step: # 只有在本幀沒有發生球拍碰撞時才判斷得分
                if self.ball_y - self.ball_radius_normalized < 0: # 球觸及或越過頂部邊界 (玩家得分)
                    self.player1.lives += 0 # 這裡之前是 self.opponent.lives -=1，P1得分，對手生命減少
                                            # 假設P1在下，其對手 (opponent) 在上。球到頂部是P1得分。
                    if self.opponent.lives > 0 : self.opponent.lives -=1 # 確保生命值不為負
                    self.player1.last_hit_time = current_time_ticks # 用於UI閃爍
                    self.freeze_timer = current_time_ticks
                    done = True
                    info['scorer'] = 'player1'
                    if DEBUG_ENV: print(f"[PongDuelEnv.step] Player 1 scored! Opponent lives: {self.opponent.lives}")
                elif self.ball_y + self.ball_radius_normalized > 1.0: # 球觸及或越過底部邊界 (對手得分)
                    if self.player1.lives > 0: self.player1.lives -= 1
                    self.opponent.last_hit_time = current_time_ticks # 用於UI閃爍
                    self.freeze_timer = current_time_ticks
                    done = True
                    info['scorer'] = 'opponent'
                    if DEBUG_ENV: print(f"[PongDuelEnv.step] Opponent scored! Player 1 lives: {self.player1.lives}")
        
        if done and DEBUG_ENV:
            print(f"[SKILL_DEBUG][PongDuelEnv.step] Round ended by NORMAL physics. Scorer: {info.get('scorer')}. P1 Lives: {self.player1.lives}, Opponent Lives: {self.opponent.lives}")

        game_over = self.player1.lives <= 0 or self.opponent.lives <= 0
        if game_over and done and DEBUG_ENV: # 只有在回合結束時才判斷遊戲是否結束
            print(f"[SKILL_DEBUG][PongDuelEnv.step] GAME OVER by NORMAL physics detected.")
        
        return self._get_obs(), reward, done, game_over, info

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
                # env=self, # Renderer 不再直接持有 env 的引用
                game_mode=self.game_mode, # Renderer 仍需知道遊戲模式以進行佈局
                logical_game_area_size=self.render_size, # Renderer 需要知道遊戲區的邏輯大小
                logical_ball_radius_px=self.ball_radius_px, # Renderer 初始化球圖像時需要
                logical_paddle_height_px=self.paddle_height_px, # Renderer 繪製球拍時需要
                actual_screen_surface=self.provided_main_screen_surface,
                actual_screen_width=actual_width,
                actual_screen_height=actual_height
            )

        # 收集渲染數據並傳遞給 Renderer
        render_data_packet = self.get_render_data()
        self.renderer.render(render_data_packet)

    def close(self):
        if DEBUG_ENV: print("[PongDuelEnv.close] Closing environment.")
        if self.renderer:
            self.renderer.close()
            self.renderer = None
        # 可以加入 pygame.mixer.music.stop() 等清理
        if self.sound_manager:
            self.sound_manager.stop_bg_music() # 確保背景音樂停止