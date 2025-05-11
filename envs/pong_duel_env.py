# envs/pong_duel_env.py
import numpy as np
import pygame
import random
import math

from game.theme import Style
from game.physics import collide_sphere_with_moving_plane
from game.sound import SoundManager
from game.render import Renderer
from game.settings import GameSettings # 引入 GameSettings
from game.skills.skill_config import SKILL_CONFIGS

from game.skills.slowmo_skill import SlowMoSkill
from game.skills.long_paddle_skill import LongPaddleSkill
from game.skills.soul_eater_bug_skill import SoulEaterBugSkill


class PongDuelEnv:
    def __init__(self,
                 render_size=400,
                 paddle_width=60,
                 paddle_height=10,
                 ball_radius=10,
                 active_skill_name=None,
                 game_mode=GameSettings.GameMode.PLAYER_VS_AI): # ⭐ 新增 game_mode 參數

        self.game_mode = game_mode # ⭐ 儲存遊戲模式
        print(f"PongDuelEnv initialized with game_mode: {self.game_mode}") # ⭐ 驗證用 print

        self.sound_manager = SoundManager()
        self.renderer = None
        # ... (其他 __init__ 內容保持不變) ...
        self.trail = []
        self.max_trail_length = 20

        self.mass = 1.0
        self.radius = ball_radius / render_size
        self.e = 1.0
        self.mu = 0.4

        self.render_size = render_size
        self.paddle_width = paddle_width
        self.paddle_height = paddle_height
        self.ball_radius = ball_radius

        self.player_x = 0.5 # 未來可能改為 player1_x
        self.ai_x = 0.5     # 未來可能改為 player2_x
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

        self.player_life = 3 # 未來可能改為 player1_life
        self.ai_life = 3     # 未來可能改為 player2_life
        self.player_max_life = 3
        self.ai_max_life = 3


        self.window = None
        self.clock = None
        self.freeze_timer = 0
        self.last_player_hit_time = 0
        self.last_ai_hit_time = 0

        self.time_scale = 1.0

        self.skills = {}
        self.active_skill_name = active_skill_name
        self.bug_skill_active = False
        self.paddle_color = None

        self.freeze_duration = GameSettings.FREEZE_DURATION_MS
        self.countdown_seconds = GameSettings.COUNTDOWN_SECONDS
        
        self.round_concluded_by_skill = False


    def set_params_from_config(self, config):
        self.speed_increment = config.get('speed_increment', 0.005)
        self.speed_scale_every = config.get('speed_scale_every', 3)
        self.enable_spin = config.get('enable_spin', True)
        self.magnus_factor = config.get('magnus_factor', 0.01)
        self.initial_speed = config.get('initial_speed', 0.02)
        self.initial_angle_range = config.get('initial_angle_deg_range', None)
        self.initial_direction = config.get('initial_direction', 'down')

        self.player_life = config.get('player_life', 3)
        self.ai_life = config.get('ai_life', 3)
        self.player_max_life = config.get('player_max_life', self.player_life)
        self.ai_max_life = config.get('ai_max_life', self.ai_life)

        self.player_paddle_width = config.get('player_paddle_width', self.paddle_width)
        self.ai_paddle_width = config.get('ai_paddle_width', 60)
        self.bg_music = config.get("bg_music", "bg_music.mp3")

        if not self.active_skill_name:
            self.active_skill_name = config.get('default_skill', 'slowmo')

        available_skills = {
            'slowmo': SlowMoSkill,
            'long_paddle': LongPaddleSkill,
            'soul_eater_bug': SoulEaterBugSkill
        }
        skill_cls = available_skills.get(self.active_skill_name)
        if not skill_cls:
            print(f"Warning: Skill '{self.active_skill_name}' not found. Falling back to slowmo.")
            self.active_skill_name = 'slowmo'
            skill_cls = SlowMoSkill
        
        self.skills.clear()
        self.skills[self.active_skill_name] = skill_cls(self)
        print(f"Registered active skill: {self.active_skill_name}")


    def reset_ball_after_score(self, scored_by_player):
        self.round_concluded_by_skill = False # 重置旗標
        self.bounces = 0

        angle_deg = self.initial_angle_deg
        if self.initial_angle_range:
            angle_deg = random.uniform(*self.initial_angle_range)
        angle_rad = np.radians(angle_deg)

        paddle_h_norm = self.paddle_height / self.render_size
        ball_r_norm = self.ball_radius / self.render_size

        if self.initial_direction == "down":
            self.ball_y = paddle_h_norm + ball_r_norm + 0.05
            vy_sign = 1
        else:
            self.ball_y = 1.0 - paddle_h_norm - ball_r_norm - 0.05
            vy_sign = -1
        
        self.ball_x = 0.5
        self.ball_vx = self.initial_speed * np.sin(angle_rad)
        self.ball_vy = self.initial_speed * np.cos(angle_rad) * vy_sign
        self.spin = 0
        
        # 如果因得分重置時蟲技能是啟動的，則停用它
        if self.bug_skill_active: # bug_skill_active 會由 SoulEaterBugSkill 的 deactivate 重置
            active_skill = self.skills.get(self.active_skill_name)
            if active_skill and isinstance(active_skill, SoulEaterBugSkill) and active_skill.is_active():
                active_skill.deactivate(hit_paddle=False, scored=False) # 確保狀態正確


    def reset(self):
        self.round_concluded_by_skill = False # 重置旗標
        self.player_x = 0.5
        self.ai_x = 0.5
        self.reset_ball_after_score(scored_by_player=False) # 假設AI先發球或隨機
        
        for skill in self.skills.values():
            if hasattr(skill, 'reset_state'):
                skill.reset_state()
            elif skill.is_active():
                skill.deactivate()

        self.bug_skill_active = False # 確保這個總是被重置
        self.time_scale = 1.0
        self.paddle_color = None

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
        speed_multiplier = 1 + (self.bounces // self.speed_scale_every) * self.speed_increment
        current_speed_magnitude = math.sqrt(self.ball_vx**2 + self.ball_vy**2)
        target_speed_magnitude = self.initial_speed * speed_multiplier

        if current_speed_magnitude > 0 :
            scale_factor = target_speed_magnitude / current_speed_magnitude
            self.ball_vx *= scale_factor
            self.ball_vy *= scale_factor
        else:
            angle_rad = math.atan2(self.ball_vx, self.ball_vy) if current_speed_magnitude !=0 else random.uniform(0, 2*math.pi)
            self.ball_vx = target_speed_magnitude * math.sin(angle_rad)
            self.ball_vy = target_speed_magnitude * math.cos(angle_rad)


    def step(self, player_action, ai_action):
        cur = pygame.time.get_ticks()

        if self.freeze_timer > 0:
            if cur - self.freeze_timer < self.freeze_duration:
                return self._get_obs(), 0, False, False, {}
            else:
                self.freeze_timer = 0
                # 這裡的發球邏輯可能需要更細緻，例如判斷是誰導致的 freeze
                self.reset_ball_after_score(scored_by_player=True) # 簡化：先假設玩家區發球

        self.prev_player_x = self.player_x
        self.prev_ai_x = self.ai_x
        old_ball_y_for_collision = self.ball_y # 用於普通球碰撞檢測

        self.round_concluded_by_skill = False # 在每一步開始時重置

        keys = pygame.key.get_pressed()
        active_skill_instance = self.skills.get(self.active_skill_name)

        if keys[pygame.K_SPACE] and active_skill_instance:
            active_skill_instance.activate()

        # --- 更新當前技能 ---
        if active_skill_instance and active_skill_instance.is_active():
            active_skill_instance.update() # 技能的 update 可能會移動球、處理碰撞並設定 round_concluded_by_skill

        # --- 檢查技能是否結束了回合 ---
        if self.round_concluded_by_skill:
            return self._get_obs(), 0, True, False, {} # True 表示回合結束

        # --- 時間尺度和球拍顏色設定 (通用技能影響) ---
        self.time_scale = 1.0 # 重置為預設值
        self.paddle_color = None # 重置為預設值
        if active_skill_instance and active_skill_instance.is_active():
            if self.active_skill_name == "slowmo": # SlowMoSkill 特定邏輯
                 if hasattr(active_skill_instance, 'slow_time_scale'):
                    self.time_scale = active_skill_instance.slow_time_scale
            
            # 通用方式獲取球拍顏色 (如果技能提供)
            if hasattr(active_skill_instance, 'paddle_color') and active_skill_instance.paddle_color is not None:
                self.paddle_color = active_skill_instance.paddle_color
        
        # --- 判斷是否執行預設球體物理 ---
        run_normal_ball_physics = True
        if active_skill_instance and active_skill_instance.is_active() and active_skill_instance.overrides_ball_physics:
            run_normal_ball_physics = False

        # --- 玩家與AI移動 ---
        ts = self.time_scale
        player_move_speed = 0.03
        combo_factor = 1.0
        # Slowmo 加速因子，確保 active_skill_instance 存在且是 slowmo
        if active_skill_instance and active_skill_instance.is_active() and \
           self.active_skill_name == "slowmo" and hasattr(active_skill_instance, 'slow_time_scale') and \
           active_skill_instance.slow_time_scale < 1.0:
            combo_factor = 5.0

        if player_action == 0: self.player_x -= player_move_speed * ts * combo_factor
        elif player_action == 2: self.player_x += player_move_speed * ts * combo_factor
        # AI 移動速度是否受 slowmo 影響，是遊戲設計的選擇
        ai_move_speed = player_move_speed # 可以為 AI 設定不同的速度
        if ai_action == 0: self.ai_x -= ai_move_speed * ts
        elif ai_action == 2: self.ai_x += ai_move_speed * ts
        self.player_x = np.clip(self.player_x, 0, 1)
        self.ai_x = np.clip(self.ai_x, 0, 1)

        if run_normal_ball_physics:
            # --- 普通球物理 ---
            if self.enable_spin:
                spin_force_x = self.magnus_factor * self.spin * self.ball_vy if self.ball_vy !=0 else 0
                self.ball_vx += spin_force_x * ts
            self.ball_x += self.ball_vx * ts
            self.ball_y += self.ball_vy * ts

            # 普通球拖尾
            self.trail.append((self.ball_x, self.ball_y))
            if len(self.trail) > self.max_trail_length: self.trail.pop(0)

            # 左右牆碰撞
            ball_r_norm = self.radius # 物理半徑
            if self.ball_x - ball_r_norm <= 0:
                self.ball_x = ball_r_norm
                self.ball_vx *= -1
            elif self.ball_x + ball_r_norm >= 1:
                self.ball_x = 1 - ball_r_norm
                self.ball_vx *= -1
            
            reward = 0 # 初始化獎勵

            # --- 普通球與球拍碰撞及計分 ---
            # AI 擋板 (上方)
            ai_paddle_surface_y_norm = (self.paddle_height / self.render_size)
            ai_paddle_half_w_norm = (self.ai_paddle_width / self.render_size) / 2
            if old_ball_y_for_collision > ai_paddle_surface_y_norm + ball_r_norm and self.ball_y <= ai_paddle_surface_y_norm + ball_r_norm:
                if abs(self.ball_x - self.ai_x) < ai_paddle_half_w_norm + ball_r_norm: # 碰撞
                    self.ball_y = ai_paddle_surface_y_norm + ball_r_norm
                    vn = self.ball_vy
                    vt = self.ball_vx
                    u_paddle = (self.ai_x - self.prev_ai_x) / ts if ts != 0 else 0
                    vn_post, vt_post, omega_post = collide_sphere_with_moving_plane(
                        vn, vt, u_paddle, self.spin, self.e, self.mu, self.mass, self.radius
                    )
                    self.ball_vy = vn_post
                    self.ball_vx = vt_post
                    self.spin = omega_post
                    self.bounces += 1
                    self._scale_difficulty()
                    self.sound_manager.play_paddle_hit() # <--- 修改於此
                else: # AI漏接
                    self.ai_life -= 1
                    self.last_ai_hit_time = cur
                    self.freeze_timer = cur
                    for s_name, s_obj in self.skills.items(): # 所有技能失效
                        if s_obj.is_active(): s_obj.deactivate()
                    return self._get_obs(), reward, True, False, {}

            # 玩家擋板 (下方)
            player_paddle_surface_y_norm = 1.0 - (self.paddle_height / self.render_size)
            player_paddle_half_w_norm = (self.player_paddle_width / self.render_size) / 2
            if old_ball_y_for_collision < player_paddle_surface_y_norm - ball_r_norm and self.ball_y >= player_paddle_surface_y_norm - ball_r_norm:
                if abs(self.ball_x - self.player_x) < player_paddle_half_w_norm + ball_r_norm: # 碰撞
                    self.ball_y = player_paddle_surface_y_norm - ball_r_norm
                    vn = -self.ball_vy
                    vt = self.ball_vx
                    u_paddle = (self.player_x - self.prev_player_x) / ts if ts != 0 else 0
                    vn_post, vt_post, omega_post = collide_sphere_with_moving_plane(
                        vn, vt, u_paddle, self.spin, self.e, self.mu, self.mass, self.radius
                    )
                    self.ball_vy = -vn_post
                    self.ball_vx = vt_post
                    self.spin = omega_post
                    self.bounces += 1
                    self._scale_difficulty()
                    self.sound_manager.play_paddle_hit() # <--- 修改於此
                else: # 玩家漏接
                    self.player_life -= 1
                    self.last_player_hit_time = cur
                    self.freeze_timer = cur
                    for s_name, s_obj in self.skills.items(): # 所有技能失效
                         if s_obj.is_active(): s_obj.deactivate()
                    return self._get_obs(), reward, True, False, {}
        # else:
            # 球的移動和碰撞已由覆寫物理的技能處理
            # 拖尾也應該由該技能的 update 處理 (SoulEaterBugSkill 已加入此邏輯)

        return self._get_obs(), 0, False, False, {}


    def render(self):
        if self.renderer is None:
            self.renderer = Renderer(self)
            self.window = self.renderer.window
        self.renderer.render()

    def close(self):
        if self.window:
            pygame.quit()
            self.window = None