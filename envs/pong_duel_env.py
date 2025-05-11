# pong-soul/envs/pong_duel_env.py
import numpy as np
import pygame
import random
import math

from game.theme import Style
from game.physics import collide_sphere_with_moving_plane # handle_paddle_collision 可能不再直接用於蟲
from game.sound import SoundManager
from game.render import Renderer
from game.settings import GameSettings # GameSettings.FREEZE_DURATION_MS
from game.skills.skill_config import SKILL_CONFIGS

from game.skills.slowmo_skill import SlowMoSkill
from game.skills.long_paddle_skill import LongPaddleSkill
from game.skills.soul_eater_bug_skill import SoulEaterBugSkill


class PongDuelEnv:
    def __init__(self,
                 render_size=400,
                 paddle_width=60, # 這是像素單位還是邏輯單位？假設是像素
                 paddle_height=10,
                 ball_radius=10,  # 假設這是像素單位，用於蟲的圖片縮放基準
                 active_skill_name=None):

        self.sound_manager = SoundManager() # 通用音效管理器
        self.renderer = None

        self.trail = []
        self.max_trail_length = 20

        # 物理參數 (可能對蟲不適用)
        self.mass = 1.0
        self.radius = ball_radius / render_size # 將球半徑轉換為邏輯單位 (0-1) 給物理引擎用
        self.e = 1.0
        self.mu = 0.4

        self.render_size = render_size
        self.paddle_width = paddle_width # 玩家預設球拍寬度 (像素)
        self.paddle_height = paddle_height # 球拍高度 (像素)
        self.ball_radius = ball_radius # 球的視覺半徑 (像素)

        self.player_x = 0.5 # 邏輯單位
        self.ai_x = 0.5     # 邏輯單位
        self.prev_player_x = self.player_x
        self.prev_ai_x = self.ai_x

        self.ball_x = 0.5 # 邏輯單位
        self.ball_y = 0.5 # 邏輯單位
        self.ball_vx = 0.02 # 邏輯單位/幀
        self.ball_vy = -0.02# 邏輯單位/幀

        self.spin = 0
        self.enable_spin = True
        self.magnus_factor = 0.01

        self.speed_scale_every = 3
        self.speed_increment = 0.005
        self.bounces = 0

        self.initial_direction = "down"
        self.initial_angle_deg = 15
        self.initial_angle_range = None
        self.initial_speed = 0.02 # 邏輯單位/幀

        self.player_life = 3
        self.ai_life = 3
        # self.max_life = 3 # 改用 player_max_life, ai_max_life

        self.window = None
        self.clock = None
        self.freeze_timer = 0
        # self.freeze_duration = 500 # 從 GameSettings 讀取
        self.last_player_hit_time = 0
        self.last_ai_hit_time = 0

        self.time_scale = 1.0

        self.skills = {}
        self.active_skill_name = active_skill_name
        self.bug_skill_active = False # 初始化蟲技能狀態
        self.paddle_color = None # 當前玩家球拍顏色 (受技能影響)
        # self.ball_image = None # ball_image 由 Renderer 管理和技能修改

        # GameSettings 的引用
        self.freeze_duration = GameSettings.FREEZE_DURATION_MS
        self.countdown_seconds = GameSettings.COUNTDOWN_SECONDS


    def set_params_from_config(self, config):
        self.speed_increment = config.get('speed_increment', 0.005)
        self.speed_scale_every = config.get('speed_scale_every', 3)
        self.enable_spin = config.get('enable_spin', True)
        self.magnus_factor = config.get('magnus_factor', 0.01)
        self.initial_speed = config.get('initial_speed', 0.02) # 邏輯單位/幀
        # self.initial_angle_deg = config.get('initial_angle_deg', 15) # 已在 init 中有預設
        self.initial_angle_range = config.get('initial_angle_deg_range', None)
        self.initial_direction = config.get('initial_direction', 'down')

        self.player_life = config.get('player_life', 3)
        self.ai_life = config.get('ai_life', 3)
        self.player_max_life = config.get('player_max_life', self.player_life) # 確保max_life被設定
        self.ai_max_life = config.get('ai_max_life', self.ai_life)       # 確保max_life被設定

        # 球拍寬度從關卡設定讀取的是像素單位
        self.player_paddle_width = config.get('player_paddle_width', self.paddle_width)
        self.ai_paddle_width = config.get('ai_paddle_width', 60) # AI球拍寬度也可配置
        self.bg_music = config.get("bg_music", "bg_music.mp3")

        if not self.active_skill_name: # 如果 main.py 沒有傳遞 active_skill_name
            self.active_skill_name = config.get('default_skill', 'slowmo') # 從關卡設定檔讀取預設技能

        available_skills = {
            'slowmo': SlowMoSkill,
            'long_paddle': LongPaddleSkill,
            'soul_eater_bug': SoulEaterBugSkill
        }
        skill_cls = available_skills.get(self.active_skill_name)
        if not skill_cls:
            # 如果 active_skill_name 仍然無效，則嘗試使用一個絕對預設值或報錯
            print(f"Warning: Skill '{self.active_skill_name}' not found in available_skills. Falling back to slowmo.")
            self.active_skill_name = 'slowmo' # 絕對預設
            skill_cls = SlowMoSkill
            # raise ValueError(f"Skill '{self.active_skill_name}' not found!")

        self.skills.clear() # 清除舊技能實例（如果有的話）
        # 為所有可用技能創建實例，而不僅僅是 active_skill_name
        # 這樣可以預先載入，但目前設計是只處理一個 active_skill
        # 如果要允許多個技能同時存在 (例如被動技能)，這裡需要修改
        self.skills[self.active_skill_name] = skill_cls(self) # 只註冊當前選擇的技能
        print(f"Registered active skill: {self.active_skill_name}")


    def register_skill(self, skill_name, skill_obj): # 這個方法目前在 set_params_from_config 中被間接使用
        self.skills[skill_name] = skill_obj

    def reset_ball_after_score(self, scored_by_player):
        """重置球的位置和速度，通常在得分後或回合開始時呼叫"""
        self.bounces = 0 # 重置彈跳次數以重置難度縮放

        # 根據是誰得分，決定發球方向 (可選邏輯)
        # if scored_by_player:
        #     self.initial_direction = "up" # AI 發球
        # else:
        #     self.initial_direction = "down" # 玩家發球
        # 或者總是從中間固定方向發球

        angle_deg = self.initial_angle_deg
        if self.initial_angle_range:
            angle_deg = random.uniform(*self.initial_angle_range)
        angle_rad = np.radians(angle_deg)

        # 球拍高度和球半徑都用邏輯單位計算初始Y位置
        paddle_h_norm = self.paddle_height / self.render_size
        ball_r_norm = self.ball_radius / self.render_size # 使用視覺半徑轉換的邏輯單位

        if self.initial_direction == "down": # 球從AI方落下 (玩家發球區)
            self.ball_y = paddle_h_norm + ball_r_norm + 0.05 # 略高於AI球拍
            vy_sign = 1
        else: # 球從玩家方上升 (AI發球區)
            self.ball_y = 1.0 - paddle_h_norm - ball_r_norm - 0.05 # 略低於玩家球拍
            vy_sign = -1
        
        self.ball_x = 0.5 # 中心發球
        self.ball_vx = self.initial_speed * np.sin(angle_rad)
        self.ball_vy = self.initial_speed * np.cos(angle_rad) * vy_sign
        self.spin = 0
        
        # 如果有蟲技能正在作用，但球被重置了，應該停用它
        if self.bug_skill_active:
            active_skill = self.skills.get(self.active_skill_name)
            if active_skill and isinstance(active_skill, SoulEaterBugSkill):
                active_skill.deactivate(hit_paddle=False, scored=False) # 確保蟲技能狀態正確


    def reset(self): # 完整重置遊戲狀態 (例如一局結束，或遊戲開始)
        self.player_x = 0.5
        self.ai_x = 0.5
        self.reset_ball_after_score(scored_by_player=False) # 假設AI先發球或隨機
        
        # 重置所有技能的狀態 (如果它們有需要重置的內部狀態)
        for skill in self.skills.values():
            if hasattr(skill, 'reset_state'): # 如果技能有自己的reset_state方法
                skill.reset_state()
            elif skill.is_active(): # 至少要停用它
                skill.deactivate()

        # 確保 bug_skill_active 旗標也被重置
        self.bug_skill_active = False
        self.time_scale = 1.0 # 恢復正常時間流速
        self.paddle_color = None # 恢復預設球拍顏色

        return self._get_obs(), {}


    def _get_obs(self):
        return np.array([
            self.ball_x, self.ball_y,
            self.ball_vx, self.ball_vy,
            self.player_x, self.ai_x
        ], dtype=np.float32)

    def get_lives(self):
        return self.player_life, self.ai_life

    def _scale_difficulty(self): # 普通球的難度調整
        # 速度增加的基準應該是 initial_speed
        speed_multiplier = 1 + (self.bounces // self.speed_scale_every) * self.speed_increment
        current_speed_magnitude = math.sqrt(self.ball_vx**2 + self.ball_vy**2)
        target_speed_magnitude = self.initial_speed * speed_multiplier

        if current_speed_magnitude > 0 : #避免除以零
            scale_factor = target_speed_magnitude / current_speed_magnitude
            self.ball_vx *= scale_factor
            self.ball_vy *= scale_factor
        else: # 如果速度為零，則以初始速度為基礎重新設定一個方向
            angle_rad = math.atan2(self.ball_vx, self.ball_vy) # 保持當前方向（如果是0則隨機）
            if current_speed_magnitude == 0: angle_rad = random.uniform(0, 2*math.pi)
            self.ball_vx = target_speed_magnitude * math.sin(angle_rad)
            self.ball_vy = target_speed_magnitude * math.cos(angle_rad)


    def step(self, player_action, ai_action):
        cur = pygame.time.get_ticks()

        if self.freeze_timer > 0:
            if cur - self.freeze_timer < self.freeze_duration:
                return self._get_obs(), 0, False, False, {}
            else: # Freeze結束，重置球并发球
                self.freeze_timer = 0
                # 根據是誰丟分來決定由誰發球 (或者固定發球)
                # last_hit_is_player = self.last_player_hit_time > self.last_ai_hit_time
                # self.reset_ball_after_score(scored_by_player=not last_hit_is_player) # 如果是玩家丟分，AI得分，玩家發球
                self.reset_ball_after_score(scored_by_player=True) # 簡單處理：總是玩家發球區開始

        self.prev_player_x = self.player_x
        self.prev_ai_x = self.ai_x
        old_ball_y = self.ball_y
        old_ball_x = self.ball_x # 記錄舊的X座標

        # --- 技能相關 ---
        # 技能啟動 (從 main.py 移到這裡，使用 get_pressed 更適合連續按住)
        # 但對於一次性觸發的技能，事件驅動更好。這裡暫時保留 get_pressed
        keys = pygame.key.get_pressed()
        active_skill_instance = self.skills.get(self.active_skill_name)
        if keys[pygame.K_SPACE] and active_skill_instance:
            active_skill_instance.activate() # activate 內部會檢查冷卻和是否已啟動

        # 更新當前技能 (或其他所有技能，如果設計允許多技能)
        if active_skill_instance:
            active_skill_instance.update()

        # 時間尺度 (主要由 SlowMoSkill 控制)
        # 預設為1.0，如果SlowMo啟動，它會修改 self.time_scale
        self.time_scale = 1.0 
        if self.active_skill_name == "slowmo" and active_skill_instance and active_skill_instance.is_active():
             if hasattr(active_skill_instance, 'slow_time_scale'):
                self.time_scale = active_skill_instance.slow_time_scale
        
        # 球拍顏色 (由技能控制)
        self.paddle_color = None # 每幀重置，由技能設定
        if active_skill_instance and active_skill_instance.is_active() and hasattr(active_skill_instance, 'paddle_color'):
            self.paddle_color = active_skill_instance.paddle_color


        # --- 蟲技能特殊移動和碰撞邏輯 ---
        if self.bug_skill_active and active_skill_instance and isinstance(active_skill_instance, SoulEaterBugSkill):
            # 1. Y-axis movement
            delta_y = -active_skill_instance.base_y_speed
            # 2. X-axis movement
            homing_target_x = self.ai_x
            sine_oscillation = active_skill_instance.x_amplitude * math.sin(
                active_skill_instance.x_frequency * (active_skill_instance.time_since_activation_frames * active_skill_instance.time_scaling_for_wave) +
                active_skill_instance.initial_phase_offset
            )
            bug_aim_x = homing_target_x + sine_oscillation
            bug_aim_x = np.clip(bug_aim_x, 0.0, 1.0)
            delta_x = (bug_aim_x - self.ball_x) * active_skill_instance.x_homing_factor

            self.ball_y += delta_y * self.time_scale
            self.ball_x += delta_x * self.time_scale
            self.ball_x = np.clip(self.ball_x, 0.0, 1.0)

            # 檢查蟲是否到達AI底線 (AI失分)
            ai_goal_line_norm = (self.paddle_height / self.render_size) # AI球拍的內側邊緣 (邏輯單位)
            if self.ball_y <= ai_goal_line_norm:
                print("Bug scored against AI!")
                self.ai_life -= 1
                self.last_ai_hit_time = cur # 記錄AI被擊中時間
                self.freeze_timer = cur   # 觸發凍結
                active_skill_instance.deactivate(hit_paddle=False, scored=True) # 蟲技能結束，標記為得分
                # self.sound_manager.play_countdown() # 或者一個通用的得分音效，蟲技能內部也會嘗試播放
                return self._get_obs(), 0, True, False, {} # True 表示回合結束

            # 檢查蟲是否撞到AI球拍
            ai_paddle_y_contact_norm = (self.paddle_height / self.render_size) # 球拍上表面
            ai_paddle_thickness_norm = (self.paddle_height / self.render_size) # 球拍厚度估算碰撞範圍
            ai_paddle_x_min = self.ai_x - (self.ai_paddle_width / self.render_size / 2)
            ai_paddle_x_max = self.ai_x + (self.ai_paddle_width / self.render_size / 2)
            bug_radius_norm = (active_skill_instance.bug_image.get_width() / 2) / self.render_size # 蟲的視覺半徑 (邏輯單位)


            # 簡化碰撞: Y在球拍厚度內，X在球拍寬度內
            # 蟲的Y中心是否進入AI球拍的Y範圍 (從球拍上表面到下表面)
            if (self.ball_y - bug_radius_norm <= ai_paddle_y_contact_norm + ai_paddle_thickness_norm and \
                self.ball_y + bug_radius_norm >= ai_paddle_y_contact_norm):
                 # 蟲的X中心是否在AI球拍的X範圍內
                if (self.ball_x + bug_radius_norm >= ai_paddle_x_min and \
                    self.ball_x - bug_radius_norm <= ai_paddle_x_max):
                    print("Bug hit AI paddle!")
                    self.freeze_timer = cur # 觸發凍結（停頓）
                    active_skill_instance.deactivate(hit_paddle=True, scored=False) # 蟲技能結束，標記為撞板
                    # 球會在本輪 freeze 結束後通過 reset_ball_after_score 重新發球
                    return self._get_obs(), 0, True, False, {} # True 表示回合結束 (即使沒得分)


            self.trail.append((self.ball_x, self.ball_y))
            if len(self.trail) > self.max_trail_length: self.trail.pop(0)
            return self._get_obs(), 0, False, False, {}
        # --- 蟲技能邏輯結束 ---


        # --- 普通球 & 其他技能控制下的玩家與AI移動 ---
        ts = self.time_scale # 獲取當前時間尺度
        player_move_speed = 0.03 # 基礎移動速度 (邏輯單位/幀)
        combo_factor = 5.0 if ts < 1.0 and self.active_skill_name == "slowmo" else 1.0 # Slowmo下的加速

        if player_action == 0: self.player_x -= player_move_speed * ts * combo_factor
        elif player_action == 2: self.player_x += player_move_speed * ts * combo_factor
        if ai_action == 0: self.ai_x -= player_move_speed * ts # AI不受Slowmo加速影響
        elif ai_action == 2: self.ai_x += player_move_speed * ts

        self.player_x = np.clip(self.player_x, 0, 1)
        self.ai_x = np.clip(self.ai_x, 0, 1)

        # --- 普通球物理 ---
        if self.enable_spin:
            # 確保 self.ball_vy 不為零，或者在 magnus_factor 中處理
            spin_force_x = self.magnus_factor * self.spin * self.ball_vy if self.ball_vy !=0 else 0
            self.ball_vx += spin_force_x * ts #馬格努斯力也應受時間尺度影響
        # self.spin *= 0.99 # 旋轉衰減 (可選)

        self.ball_x += self.ball_vx * ts
        self.ball_y += self.ball_vy * ts

        self.trail.append((self.ball_x, self.ball_y))
        if len(self.trail) > self.max_trail_length: self.trail.pop(0)

        # 左右牆碰撞 (普通球)
        ball_r_norm = self.radius # 使用物理半徑
        if self.ball_x - ball_r_norm <= 0:
            self.ball_x = ball_r_norm
            self.ball_vx *= -1
        elif self.ball_x + ball_r_norm >= 1:
            self.ball_x = 1 - ball_r_norm
            self.ball_vx *= -1
        
        reward = 0

        # --- 普通球與球拍碰撞及計分 ---
        # AI 擋板 (上方)
        ai_paddle_surface_y_norm = (self.paddle_height / self.render_size) # 球拍上表面 (最接近球場中心的一面)
        ai_paddle_half_w_norm = (self.ai_paddle_width / self.render_size) / 2

        # 球從下方接近AI球拍，且舊Y比球拍面遠，新Y比球拍面近或穿過
        if old_ball_y > ai_paddle_surface_y_norm + ball_r_norm and self.ball_y <= ai_paddle_surface_y_norm + ball_r_norm:
            # 檢查X方向是否在球拍範圍內
            if abs(self.ball_x - self.ai_x) < ai_paddle_half_w_norm + ball_r_norm:
                self.ball_y = ai_paddle_surface_y_norm + ball_r_norm # 校正Y避免穿透
                vn = self.ball_vy   # 法向速度 (對上方球拍，球的vy即法向速度vn)
                vt = self.ball_vx   # 切向速度
                u_paddle = (self.ai_x - self.prev_ai_x) / ts if ts != 0 else 0 # 球拍速度
                omega = self.spin
                vn_post, vt_post, omega_post = collide_sphere_with_moving_plane(
                    vn, vt, u_paddle, omega, self.e, self.mu, self.mass, self.radius
                )
                self.ball_vy = vn_post
                self.ball_vx = vt_post
                self.spin = omega_post
                self.bounces += 1
                self._scale_difficulty()
                self.sound_manager.play_click() # 播放通用擊球音效
            else: # AI漏接
                self.ai_life -= 1
                self.last_ai_hit_time = cur
                self.freeze_timer = cur
                for s_name, s_obj in self.skills.items(): s_obj.deactivate() # 所有技能失效
                # self.sound_manager.play_countdown() # 播放失分/回合結束音效
                return self._get_obs(), reward, True, False, {}

        # 玩家擋板 (下方)
        player_paddle_surface_y_norm = 1.0 - (self.paddle_height / self.render_size) # 球拍上表面
        player_paddle_half_w_norm = (self.player_paddle_width / self.render_size) / 2

        if old_ball_y < player_paddle_surface_y_norm - ball_r_norm and self.ball_y >= player_paddle_surface_y_norm - ball_r_norm:
            if abs(self.ball_x - self.player_x) < player_paddle_half_w_norm + ball_r_norm:
                self.ball_y = player_paddle_surface_y_norm - ball_r_norm
                self.bounces += 1
                self._scale_difficulty()
                vn = -self.ball_vy  # 法向速度 (對下方球拍，法線向上，與vy反向)
                vt = self.ball_vx
                u_paddle = (self.player_x - self.prev_player_x) / ts if ts != 0 else 0
                omega = self.spin
                vn_post, vt_post, omega_post = collide_sphere_with_moving_plane(
                    vn, vt, u_paddle, omega, self.e, self.mu, self.mass, self.radius
                )
                self.ball_vy = -vn_post # 反彈後vy方向相反
                self.ball_vx = vt_post
                self.spin = omega_post
                self.sound_manager.play_click() # 播放通用擊球音效
            else: # 玩家漏接
                self.player_life -= 1
                self.last_player_hit_time = cur
                self.freeze_timer = cur
                for s_name, s_obj in self.skills.items(): s_obj.deactivate()
                # self.sound_manager.play_countdown() # 播放失分/回合結束音效
                return self._get_obs(), reward, True, False, {}

        return self._get_obs(), reward, False, False, {}

    def render(self):
        if self.renderer is None:
            self.renderer = Renderer(self) # Renderer 初始化時會設定 pygame.init()
            self.window = self.renderer.window # 讓 env 也可以存取 window
        self.renderer.render()

    def close(self):
        if self.window: # 檢查 self.window 是否已創建 (即 render 是否被呼叫過)
            pygame.quit()
            self.window = None # 避免重複關閉