# envs/pong_duel_env.py
import numpy as np
import pygame
import random
import math

from game.theme import Style # 假設 Style 仍然可用
from game.physics import collide_sphere_with_moving_plane
from game.sound import SoundManager
from game.render import Renderer # Renderer 之後也需要修改
from game.settings import GameSettings
# from game.skills.skill_config import SKILL_CONFIGS # 技能相關的暫時註解或後續處理

# 技能類的引入暫時註解，因為 PlayerState 還未完整整合技能實例的創建
# from game.skills.slowmo_skill import SlowMoSkill
# from game.skills.long_paddle_skill import LongPaddleSkill
# from game.skills.soul_eater_bug_skill import SoulEaterBugSkill

from game.player_state import PlayerState # ⭐️ 引入 PlayerState

DEBUG_ENV = True # ⭐️ 除錯開關

class PongDuelEnv:
    def __init__(self,
                 game_mode=GameSettings.GameMode.PLAYER_VS_AI,
                 player1_config=None, # ⭐️ 新增: 包含技能、初始球拍寬度、生命等
                 opponent_config=None, # ⭐️ 新增: 同上，對手可以是P2或AI
                 common_config=None, # ⭐️ 新增: 球速、物理等共享參數
                 render_size=400, # 暫時保留，之後可以移到 common_config
                 paddle_height_px=10, # 球拍厚度 (像素)
                 ball_radius_px=10): # 球半徑 (像素)

        if DEBUG_ENV: print(f"[PongDuelEnv.__init__] Initializing with game_mode: {game_mode}")
        if DEBUG_ENV: print(f"[PongDuelEnv.__init__] Player1 Config: {player1_config}")
        if DEBUG_ENV: print(f"[PongDuelEnv.__init__] Opponent Config: {opponent_config}")
        if DEBUG_ENV: print(f"[PongDuelEnv.__init__] Common Config: {common_config}")

        self.game_mode = game_mode
        self.sound_manager = SoundManager() # SoundManager 應該在更上層初始化並傳入，暫時保留
        self.renderer = None # Renderer 會在第一次 render() 時初始化

        # 基礎尺寸設定
        self.render_size = render_size # 遊戲區域的邏輯大小 (通常是寬度)
        self.paddle_height_px = paddle_height_px
        self.ball_radius_px = ball_radius_px
        self.paddle_height_normalized = self.paddle_height_px / self.render_size
        self.ball_radius_normalized = self.ball_radius_px / self.render_size

        # 初始化玩家和對手狀態
        # 預設配置，以防外部未提供 (更好的做法是強制外部提供)
        default_p_config = {'initial_x': 0.5, 'initial_paddle_width': 60, 'initial_lives': 3, 'skill_code': None, 'is_ai': False}
        p1_conf = player1_config if player1_config else default_p_config
        opp_conf = opponent_config if opponent_config else {**default_p_config, 'is_ai': True if game_mode == GameSettings.GameMode.PLAYER_VS_AI else False}

        self.player1 = PlayerState(
            initial_x=p1_conf.get('initial_x', 0.5),
            initial_paddle_width=p1_conf.get('initial_paddle_width', 60),
            initial_lives=p1_conf.get('initial_lives', 3),
            skill_code=p1_conf.get('skill_code'),
            is_ai=p1_conf.get('is_ai', False), # Player1 通常不是 AI
            env_render_size=self.render_size
        )
        self.opponent = PlayerState(
            initial_x=opp_conf.get('initial_x', 0.5),
            initial_paddle_width=opp_conf.get('initial_paddle_width', 60), # AI/P2 的球拍寬度
            initial_lives=opp_conf.get('initial_lives', 3), # AI/P2 的生命值
            skill_code=opp_conf.get('skill_code'), # P2 的技能
            is_ai=opp_conf.get('is_ai', game_mode == GameSettings.GameMode.PLAYER_VS_AI),
            env_render_size=self.render_size
        )

        # 球的狀態 (歸一化)
        self.ball_x = 0.5
        self.ball_y = 0.5
        self.ball_vx = 0.0 # 將在 reset_ball_after_score 中設定
        self.ball_vy = 0.0 # 將在 reset_ball_after_score 中設定
        self.spin = 0

        # 遊戲邏輯相關
        self.bounces = 0 # 用於計算球速增加
        self.freeze_timer = 0 # 得分後的凍結計時器
        self.time_scale = 1.0 # 用於慢動作等技能

        # 通用配置應用 (來自 common_config)
        # 物理參數 (使用預設值或從 common_config 讀取)
        cfg = common_config if common_config else {}
        self.mass = cfg.get('mass', 1.0)
        self.e_ball_paddle = cfg.get('e_ball_paddle', 1.0) # 球與球拍的恢復係數
        self.mu_ball_paddle = cfg.get('mu_ball_paddle', 0.4) # 球與球拍的摩擦係數
        self.enable_spin = cfg.get('enable_spin', True)
        self.magnus_factor = cfg.get('magnus_factor', 0.01)
        self.speed_increment = cfg.get('speed_increment', 0.002) # 每次加速的增量
        self.speed_scale_every = cfg.get('speed_scale_every', 3) # 每 N 次反彈加速一次
        self.initial_ball_speed = cfg.get('initial_ball_speed', 0.02) # 球的初始歸一化速度
        self.initial_angle_range_deg = cfg.get('initial_angle_deg_range', [-60, 60]) # 發球角度範圍
        self.initial_direction_serves_down = cfg.get('initial_direction_serves_down', True) # True: P1區域發球向下, False: Opponent區域發球向上

        self.freeze_duration = cfg.get('freeze_duration_ms', GameSettings.FREEZE_DURATION_MS)
        self.countdown_seconds = cfg.get('countdown_seconds', GameSettings.COUNTDOWN_SECONDS)
        self.bg_music = cfg.get("bg_music", "bg_music.mp3") # 背景音樂文件名

        self.trail = [] # 球的拖尾效果
        self.max_trail_length = 20 # 拖尾最大長度

        # 技能相關 - 這一階段暫不完全處理技能實例化和管理
        self.skills = {} # 之後會是 {'player1': p1_skill_instance, 'opponent': opponent_skill_instance}
        self.bug_skill_active = False # 舊的標誌，之後會由技能系統管理
        self.paddle_color = None # 舊的，之後由 PlayerState 或 Renderer 管理

        self.round_concluded_by_skill = False # 標記回合是否由技能結束的

        if DEBUG_ENV: print("[PongDuelEnv.__init__] Initialization complete.")
        self.reset() # 初始化完成後立即重置一次遊戲狀態

    # 移除 set_params_from_config，因為參數在 __init__ 中處理
    # def set_params_from_config(self, config):
    #     ...

    def reset_ball_after_score(self, scored_by_player1):
        if DEBUG_ENV: print(f"[PongDuelEnv.reset_ball_after_score] Ball reset. Scored by player1: {scored_by_player1}")
        self.round_concluded_by_skill = False
        self.bounces = 0
        self.spin = 0
        self.trail.clear()

        angle_deg = random.uniform(*self.initial_angle_range_deg)
        angle_rad = np.radians(angle_deg)

        # 根據是誰得分，決定發球方和方向
        # 假設失分方發球
        serve_from_player1_area = not scored_by_player1 # 如果P1得分，則對手發球 (從上方)
                                                     # 如果對手得分，則P1發球 (從下方)

        if serve_from_player1_area:
            # 從 P1 (下方) 區域發球，球向上移動
            self.ball_y = 1.0 - self.paddle_height_normalized - self.ball_radius_normalized - 0.05 # 略高於 P1 球拍
            vy_sign = -1 # 向上
            if DEBUG_ENV: print(f"[PongDuelEnv.reset_ball_after_score] Serving from Player 1 area (bottom), ball moving UP.")
        else:
            # 從 Opponent (上方) 區域發球，球向下移動
            self.ball_y = self.paddle_height_normalized + self.ball_radius_normalized + 0.05 # 略低於 Opponent 球拍
            vy_sign = 1 # 向下
            if DEBUG_ENV: print(f"[PongDuelEnv.reset_ball_after_score] Serving from Opponent area (top), ball moving DOWN.")

        self.ball_x = 0.5 # 中央發球
        self.ball_vx = self.initial_ball_speed * np.sin(angle_rad)
        self.ball_vy = self.initial_ball_speed * np.cos(angle_rad) * vy_sign

        # 重置時停用技能 (之後技能系統完善後處理)
        # if self.player1.skill_instance and self.player1.skill_instance.is_active():
        #     self.player1.skill_instance.deactivate()
        # if self.opponent.skill_instance and self.opponent.skill_instance.is_active():
        #     self.opponent.skill_instance.deactivate()
        self.bug_skill_active = False # 臨時

    def reset(self):
        if DEBUG_ENV: print("[PongDuelEnv.reset] Full reset triggered.")
        self.player1.reset_state()
        # self.player1.paddle_width = self.player1.base_paddle_width # 確保球拍寬度重置
        self.player1.update_paddle_width_normalized(self.player1.base_paddle_width, self.render_size)


        self.opponent.reset_state()
        # self.opponent.paddle_width = self.opponent.base_paddle_width
        self.opponent.update_paddle_width_normalized(self.opponent.base_paddle_width, self.render_size)

        # 生命值在 reset 時不重置，除非是新遊戲開始。此 reset 主要用於回合結束。
        # 若要實現新遊戲的生命重置，應在 main.py 中調用 env.player1.lives = env.player1.max_lives

        self.reset_ball_after_score(scored_by_player1=random.choice([True, False])) # 隨機一方先發球
        self.time_scale = 1.0
        self.paddle_color = None # 臨時

        # 技能相關重置 (稍後階段處理)
        # for skill in self.skills.values():
        #     if hasattr(skill, 'reset_state'): skill.reset_state()
        #     elif skill and skill.is_active(): skill.deactivate()

        return self._get_obs(), {}

    def _get_obs(self):
        # 觀測值需要定義清楚，特別是對於AI
        # [ball_x, ball_y, ball_vx, ball_vy, player1_x, opponent_x, player1_paddle_width_norm, opponent_paddle_width_norm, ball_spin (可選)]
        # 如果是 AI 控制 opponent，觀測值可能需要翻轉 Y 軸相關量
        obs_array = [
            self.ball_x, self.ball_y,
            self.ball_vx, self.ball_vy,
            self.player1.x, self.opponent.x,
            # self.player1.paddle_width_normalized, # 暫不加入觀測，簡化AI模型
            # self.opponent.paddle_width_normalized
        ]
        # if self.opponent.is_ai: # 如果AI在上方，Y軸對它來說是反的
        #     obs_array[1] = 1.0 - obs_array[1] # ball_y
        #     obs_array[3] = -obs_array[3]      # ball_vy
            # paddle positions (player1_x, opponent_x)不需要翻轉，因為它們是相對於整個場地的X軸

        return np.array(obs_array, dtype=np.float32)

    def get_lives(self):
        return self.player1.lives, self.opponent.lives

    def _scale_difficulty(self):
        # 根據反彈次數增加球速
        speed_multiplier = 1 + (self.bounces // self.speed_scale_every) * self.speed_increment
        current_speed_magnitude = math.sqrt(self.ball_vx**2 + self.ball_vy**2)
        target_speed_magnitude = self.initial_ball_speed * speed_multiplier

        if current_speed_magnitude > 0 :
            scale_factor = target_speed_magnitude / current_speed_magnitude
            self.ball_vx *= scale_factor
            self.ball_vy *= scale_factor
        else: # 球靜止時 (理論上不應發生在遊戲中，除非是初始情況)
            angle_rad = math.atan2(self.ball_vx, self.ball_vy) if current_speed_magnitude !=0 else random.uniform(0, 2*math.pi)
            self.ball_vx = target_speed_magnitude * math.sin(angle_rad)
            self.ball_vy = target_speed_magnitude * math.cos(angle_rad)
        if DEBUG_ENV: print(f"[PongDuelEnv._scale_difficulty] Bounces: {self.bounces}, New speed multiplier: {speed_multiplier:.3f}, Current V: ({self.ball_vx:.3f}, {self.ball_vy:.3f})")

    def step(self, player1_action_input, opponent_action_input):
        current_time_ticks = pygame.time.get_ticks()

        if self.freeze_timer > 0:
            if current_time_ticks - self.freeze_timer < self.freeze_duration:
                return self._get_obs(), 0, False, False, {}
            else:
                self.freeze_timer = 0
                # 凍結結束後的發球邏輯，由 main.py 在 round_done 後調用 reset_ball_after_score 處理

        self.player1.prev_x = self.player1.x
        self.opponent.prev_x = self.opponent.x
        old_ball_y_for_collision = self.ball_y

        player_move_speed = 0.03
        ts = self.time_scale

        if player1_action_input == 0: self.player1.x -= player_move_speed * ts
        elif player1_action_input == 2: self.player1.x += player_move_speed * ts

        if opponent_action_input == 0: self.opponent.x -= player_move_speed * ts
        elif opponent_action_input == 2: self.opponent.x += player_move_speed * ts

        self.player1.x = np.clip(self.player1.x, 0.0, 1.0)
        self.opponent.x = np.clip(self.opponent.x, 0.0, 1.0)

        run_normal_ball_physics = True
        if run_normal_ball_physics:
            if self.enable_spin:
                spin_force_x = self.magnus_factor * self.spin * self.ball_vy if self.ball_vy !=0 else 0
                self.ball_vx += spin_force_x * ts
            self.ball_x += self.ball_vx * ts
            self.ball_y += self.ball_vy * ts

            self.trail.append((self.ball_x, self.ball_y))
            if len(self.trail) > self.max_trail_length: self.trail.pop(0)

            if self.ball_x - self.ball_radius_normalized <= 0:
                self.ball_x = self.ball_radius_normalized
                self.ball_vx *= -1
            elif self.ball_x + self.ball_radius_normalized >= 1:
                self.ball_x = 1 - self.ball_radius_normalized
                self.ball_vx *= -1

            collided_with_paddle_this_step = False
            reward = 0
            done = False # 回合是否結束

            # 對手球拍 (上方)
            opponent_paddle_surface_y = self.paddle_height_normalized
            opponent_paddle_contact_y = opponent_paddle_surface_y + self.ball_radius_normalized
            opponent_paddle_half_w = self.opponent.paddle_width_normalized / 2

            if old_ball_y_for_collision > opponent_paddle_contact_y and self.ball_y <= opponent_paddle_contact_y:
                if abs(self.ball_x - self.opponent.x) < opponent_paddle_half_w + self.ball_radius_normalized * 0.5:
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
                    collided_with_paddle_this_step = True
                else: # 對手漏接 (P1 得分)
                    if DEBUG_ENV: print(f"[PongDuelEnv.step] Opponent MISS. Player 1 scores.")
                    self.opponent.lives -= 1 # ⭐️ 對手生命值減少
                    self.player1.last_hit_time = current_time_ticks # 用於P1的慶祝或對手的血條效果
                    self.freeze_timer = current_time_ticks
                    done = True
            elif self.ball_y < 0: # 球出上界 (P1 得分)
                 if not collided_with_paddle_this_step:
                    if DEBUG_ENV: print(f"[PongDuelEnv.step] Ball out of TOP bound. Player 1 scores.")
                    self.opponent.lives -= 1 # ⭐️ 對手生命值減少
                    self.player1.last_hit_time = current_time_ticks
                    self.freeze_timer = current_time_ticks
                    done = True

            # 玩家1球拍 (下方)
            if not done:
                player1_paddle_surface_y = 1.0 - self.paddle_height_normalized
                player1_paddle_contact_y = player1_paddle_surface_y - self.ball_radius_normalized
                player1_paddle_half_w = self.player1.paddle_width_normalized / 2

                if old_ball_y_for_collision < player1_paddle_contact_y and self.ball_y >= player1_paddle_contact_y:
                    if abs(self.ball_x - self.player1.x) < player1_paddle_half_w + self.ball_radius_normalized * 0.5:
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
                        collided_with_paddle_this_step = True
                    else: # 玩家1漏接 (對手得分)
                        if DEBUG_ENV: print(f"[PongDuelEnv.step] Player 1 MISS. Opponent scores.")
                        self.player1.lives -= 1 # ⭐️ 玩家1生命值減少
                        self.opponent.last_hit_time = current_time_ticks # 用於對手的慶祝或P1的血條效果
                        self.freeze_timer = current_time_ticks
                        done = True
                elif self.ball_y > 1.0: # 球出下界 (對手得分)
                    if not collided_with_paddle_this_step:
                        if DEBUG_ENV: print(f"[PongDuelEnv.step] Ball out of BOTTOM bound. Opponent scores.")
                        self.player1.lives -= 1 # ⭐️ 玩家1生命值減少
                        self.opponent.last_hit_time = current_time_ticks
                        self.freeze_timer = current_time_ticks
                        done = True
            
            if done and DEBUG_ENV:
                 print(f"[PongDuelEnv.step] Round ended. P1 Lives: {self.player1.lives}, Opponent Lives: {self.opponent.lives}")

        game_over = self.player1.lives <= 0 or self.opponent.lives <= 0
        if game_over and done and DEBUG_ENV:
            print(f"[PongDuelEnv.step] GAME OVER. P1 Lives: {self.player1.lives}, Opponent Lives: {self.opponent.lives}")
        
        return self._get_obs(), reward, done, game_over, {}


    def render(self):
        if self.renderer is None:
            if DEBUG_ENV: print("[PongDuelEnv.render] Renderer not initialized. Creating one.")
            self.renderer = Renderer(self) # Renderer 初始化時會創建 window
            # self.window = self.renderer.window # 移除，Renderer 內部管理 window
        self.renderer.render() # Renderer 的 render 方法負責繪製所有內容

    def close(self):
        if DEBUG_ENV: print("[PongDuelEnv.close] Closing environment.")
        if self.renderer:
            self.renderer.close() # Renderer 負責 pygame.quit()
            self.renderer = None