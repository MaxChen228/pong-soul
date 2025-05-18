# pong-soul/game/skills/soul_eater_bug_skill.py
import pygame
import math # 保留 math
import random # 保留 random
import numpy as np # 保留 numpy
from game.skills.base_skill import Skill
from game.skills.skill_config import SKILL_CONFIGS
from utils import resource_path
import os # ⭐️ 新增：用於檢查模型檔案是否存在

# ⭐️ 新增：導入 AIAgent
from game.ai_agent import AIAgent


FPS = 60
DEBUG_BUG_SKILL = False # 您原有的 DEBUG 開關

class SoulEaterBugSkill(Skill):
    def __init__(self, env, owner_player_state):
        super().__init__(env, owner_player_state)
        cfg_key = "soul_eater_bug"
        cfg = SKILL_CONFIGS.get(cfg_key, {}) # 從 SKILL_CONFIGS 獲取設定

        if not cfg:
            print(f"[SKILL_DEBUG][SoulEaterBugSkill] ({self.owner.identifier}) CRITICAL: Config for '{cfg_key}' not found in SKILL_CONFIGS! Using internal defaults for core params.")
            # 技能核心參數的內部預設值
            internal_core_cfg = {
                "duration_ms": 8000, "cooldown_ms": 12000,
                "bug_image_path": "assets/soul_eater_bug.png",
                "bug_display_scale_factor": 1.5,
                "base_y_speed": 0.020, # 舊的 Y 速度，RL 可能會覆蓋或調整
                # RL 相關參數的預設值
                "rl_model_path": None, # 沒有預設模型
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
        except Exception as e:
            print(f"[SKILL_DEBUG][SoulEaterBugSkill] ({self.owner.identifier}) Error loading or scaling bug image: {bug_image_path}. Error: {e}")
            fallback_size = int(20 * self.bug_display_scale_factor)
            self.bug_image_transformed = pygame.Surface((fallback_size, fallback_size), pygame.SRCALPHA)
            pygame.draw.circle(self.bug_image_transformed, (100, 0, 100), (fallback_size//2, fallback_size//2), fallback_size//2)
            
        self.sound_activate_sfx = self._load_sound(cfg.get("sound_activate"))
        self.sound_crawl_sfx = self._load_sound(cfg.get("sound_crawl")) # RL 控制後，爬行聲可能需要調整
        self.sound_hit_paddle_sfx = self._load_sound(cfg.get("sound_hit_paddle"))
        self.sound_score_sfx = self._load_sound(cfg.get("sound_score"))
        self.crawl_channel = None
        self.was_crawl_sound_playing = False

        # --- RL Agent Initialization ---
        self.bug_agent = None
        rl_model_path_from_config = cfg.get("rl_model_path")
        if rl_model_path_from_config:
            absolute_model_path = resource_path(rl_model_path_from_config)
            if os.path.exists(absolute_model_path):
                try:
                    self.bug_agent = AIAgent(model_path=absolute_model_path) # 使用絕對路徑
                    if DEBUG_BUG_SKILL: print(f"[SKILL_DEBUG][SoulEaterBugSkill] ({self.owner.identifier}) RL Bug Agent loaded from: {absolute_model_path}")
                except Exception as e:
                    print(f"[SKILL_DEBUG][SoulEaterBugSkill] ({self.owner.identifier}) ERROR loading RL Bug Agent model from '{absolute_model_path}': {e}")
                    self.bug_agent = None # 載入失敗則不使用代理
            else:
                print(f"[SKILL_DEBUG][SoulEaterBugSkill] ({self.owner.identifier}) WARNING: RL Bug Agent model file not found at '{absolute_model_path}'. Bug will be inactive or use fallback.")
        else:
            if DEBUG_BUG_SKILL: print(f"[SKILL_DEBUG][SoulEaterBugSkill] ({self.owner.identifier}) No 'rl_model_path' in config. Bug will be inactive or use fallback if any.")

        # RL 控制的移動參數 (如果動作是離散的)
        self.bug_x_rl_move_speed = float(cfg.get("bug_x_rl_move_speed", 0.02))
        self.bug_y_rl_move_speed = float(cfg.get("bug_y_rl_move_speed", 0.02))

        # 基礎Y軸趨向性 (RL可以在此基礎上調整，或者完全由RL控制Y軸)
        self.base_y_speed = float(cfg.get("base_y_speed", 0.0)) # 如果RL完全控制Y，這裡可以設為0

        # --- 移除或調整舊的硬編碼移動參數初始化 ---
        # self.y_random_magnitude = float(cfg.get("y_random_magnitude", 0.008)) # 由RL決定
        # self.x_random_walk_speed = float(cfg.get("x_random_walk_speed", 0.025)) # 由RL決定
        # self.target_update_interval_frames = int(cfg.get("target_update_interval_frames", 20)) # RL可能不需要
        # self.goal_seeking_factor = float(cfg.get("goal_seeking_factor", 0.07)) # 由RL決定
        # self.dodge_factor = float(cfg.get("dodge_factor", 0.06)) # 由RL決定
        # self.current_target_x_norm = 0.5 # RL 會動態決定目標或移動方向
        # self.frames_since_target_update = 0 # RL 可能不需要

        # 休息行為參數 (這些也將由RL策略隱含決定，或明確設計為一個動作)
        # self.can_rest = bool(cfg.get("can_rest", True))
        # self.rest_chance_after_target_update = float(cfg.get("rest_chance_after_target_update", 0.20))
        # min_rest_sec = float(cfg.get("min_rest_duration_seconds", 0.8))
        # max_rest_sec = float(cfg.get("max_rest_duration_seconds", 1.5))
        # self.min_rest_duration_frames = int(min_rest_sec * FPS)
        # self.max_rest_duration_frames = int(max_rest_sec * FPS)
        # self.y_movement_dampening_during_rest = float(cfg.get("y_movement_dampening_during_rest", 0.05))
        # self.x_movement_dampening_during_rest = float(cfg.get("x_movement_dampening_during_rest", 0.0))
        # self.small_drift_during_rest_factor = float(cfg.get("small_drift_during_rest_factor", 0.003))
        self.is_resting = False # 這個狀態可能會被移除，或由 RL 的一個特殊動作觸發
        self.rest_timer_frames = 0

    def _get_bug_observation(self):
        """
        收集並返回噬魂蟲 RL 代理所需的觀察數據 (正規化)。
        """
        # 蟲的當前狀態 (在 env 中以 ball 代表)
        bug_x_norm = self.env.ball_x
        bug_y_norm = self.env.ball_y

        # 目標玩家的狀態
        target_paddle_x_norm = self.target_player_state.x
        target_paddle_half_width_norm = self.target_player_state.paddle_width_normalized / 2.0

        # 計算目標板子的 Y 座標 (中心)
        # 假設目標板子厚度為 self.env.paddle_height_normalized
        # 技能擁有者是 player1 (下方)，則目標是 opponent (上方)，其板子 Y 座標在 self.env.paddle_height_normalized / 2.0
        # 技能擁有者是 opponent (上方)，則目標是 player1 (下方)，其板子 Y 座標在 1.0 - (self.env.paddle_height_normalized / 2.0)
        if self.target_player_state == self.env.opponent: # 目標在上方
            target_paddle_center_y_norm = self.env.paddle_height_normalized / 2.0
            # 蟲到目標得分線的 Y 距離 (越小越好，得分線在 y=0 附近)
            # bug_y_distance_to_goal_line = bug_y_norm - self.env.ball_radius_normalized # (更精確的話是蟲的前端)
            # 簡單版本：蟲中心到 Y=0 的距離
            bug_y_distance_to_goal_line = bug_y_norm
        else: # 目標在下方 (self.target_player_state == self.env.player1)
            target_paddle_center_y_norm = 1.0 - (self.env.paddle_height_normalized / 2.0)
            # 蟲到目標得分線的 Y 距離 (越大越好，得分線在 y=1 附近)
            # bug_y_distance_to_goal_line = (1.0 - bug_y_norm) - self.env.ball_radius_normalized
            # 簡單版本：蟲中心到 Y=1 的距離的負值 (使其目標是讓此值變小)
            bug_y_distance_to_goal_line = 1.0 - bug_y_norm


        # 蟲相對於目標板子中心的 X, Y 偏移量
        relative_x_to_target_paddle = bug_x_norm - target_paddle_x_norm
        relative_y_to_target_paddle = bug_y_norm - target_paddle_center_y_norm

        # 觀察向量 - 您可以根據 RL 模型的輸入需求調整這個向量的內容和順序
        # 範例觀察向量 (6個特徵):
        observation = [
            bug_x_norm,                         # 1. 蟲的 X
            bug_y_norm,                         # 2. 蟲的 Y
            target_paddle_x_norm,               # 3. 目標板子的 X
            target_paddle_half_width_norm,      # 4. 目標板子半寬
            relative_x_to_target_paddle,        # 5. 蟲相對目標板子的 X 偏移
            bug_y_distance_to_goal_line         # 6. 蟲到目標得分線的 Y 距離 (越小越好)
            # (可選) self.env.ball_vx,          # 蟲的 X 速度
            # (可選) self.env.ball_vy,          # 蟲的 Y 速度
            # (可選) 1.0 - bug_x_norm,           # 蟲到右牆距離
            # (可選) target_paddle_center_y_norm # 目標板子中心Y (如果Y偏移不夠)
        ]
        
        if DEBUG_BUG_SKILL and random.random() < 0.05: # 降低打印頻率
            # print(f"[SKILL_DEBUG][SoulEaterBugSkill] Bug Obs: {np.array(observation).round(3)}")
            pass

        return np.array(observation, dtype=np.float32)
    def _load_sound(self, sound_path):
        if sound_path:
            try: return pygame.mixer.Sound(resource_path(sound_path))
            except pygame.error as e: print(f"[SKILL_DEBUG][SoulEaterBugSkill] Error loading sound: {sound_path}. Error: {e}")
        return None

    @property
    def overrides_ball_physics(self):
        return True # 此技能將完全控制球（蟲）的移動

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
        
        # 通知 Env 球的視覺效果已被此技能覆蓋
        if hasattr(self.env, 'set_ball_visual_override'):
            self.env.set_ball_visual_override(skill_identifier="soul_eater_bug", active=True, owner_identifier=self.owner.identifier)
            if DEBUG_BUG_SKILL: print(f"[SKILL_DEBUG][SoulEaterBugSkill] ({self.owner.identifier}) Notified Env to change ball visual to bug.")
        else:
            if DEBUG_BUG_SKILL: print(f"[SKILL_DEBUG][SoulEaterBugSkill] ({self.owner.identifier}) WARNING: env.set_ball_visual_override method not found!")
        
        # 重置球（蟲）的初始速度和旋轉（因為蟲有自己的移動邏輯）
        self.env.ball_vx = 0
        self.env.ball_vy = 0
        self.env.spin = 0 # 蟲子不受馬格努斯效應影響

        # 蟲子初始位置：可以設定在啟用者附近，或者場地特定位置
        # 為了簡單，暫時讓它在球的當前位置出現，或者中央出現
        # self.env.ball_x = self.owner.x # 出現在擁有者前方
        # if self.owner == self.env.player1: # P1 在下方
        #     self.env.ball_y = 1.0 - self.env.paddle_height_normalized - self.env.ball_radius_normalized - 0.1 # P1球拍前上方一點
        # else: # Opponent 在上方
        #     self.env.ball_y = self.env.paddle_height_normalized + self.env.ball_radius_normalized + 0.1 # Opponent球拍前下方一點
        # 或者固定從屏幕中心上方出現，向下移動
        self.env.ball_x = 0.5
        self.env.ball_y = 0.3 # 從偏上方開始

        self.is_resting = False
        self.rest_timer_frames = 0
        self.was_crawl_sound_playing = False
        
        if DEBUG_BUG_SKILL: print(f"[SKILL_DEBUG][SoulEaterBugSkill] ({self.owner.identifier}) Activated! Target: {self.target_player_state.identifier}. Duration: {self.duration_ms}ms.")
        if self.sound_activate_sfx: self.sound_activate_sfx.play()
        if self.sound_crawl_sfx:
            self.crawl_channel = self.sound_crawl_sfx.play(-1) # 循環播放爬行聲
            self.was_crawl_sound_playing = True
        return True

    def _update_target_x_norm(self):
        """更新蟲子在X軸上的短期遊走目標點 (歸一化座標)。蟲子會試圖繞過目標球拍。"""
        target_paddle_x_norm = self.target_player_state.x
        target_paddle_half_w_norm = self.target_player_state.paddle_width_normalized / 2
        
        # 嘗試在目標球拍的左側或右側找空間
        gap_to_wall_threshold_norm = 0.1 # 蟲子與牆壁的最小期望間隔
        gap_to_paddle_threshold_norm = self.env.ball_radius_normalized * 2 # 蟲子與球拍邊緣的最小期望間隔

        possible_targets = []
        # 檢查球拍左邊緣到左牆是否有足夠空間
        left_space_end_norm = target_paddle_x_norm - target_paddle_half_w_norm - gap_to_paddle_threshold_norm
        if left_space_end_norm > gap_to_wall_threshold_norm:
            possible_targets.append(random.uniform(gap_to_wall_threshold_norm, left_space_end_norm))
            
        # 檢查球拍右邊緣到右牆是否有足夠空間
        right_space_start_norm = target_paddle_x_norm + target_paddle_half_w_norm + gap_to_paddle_threshold_norm
        if right_space_start_norm < (1.0 - gap_to_wall_threshold_norm):
            possible_targets.append(random.uniform(right_space_start_norm, 1.0 - gap_to_wall_threshold_norm))

        if not possible_targets: # 如果兩邊都沒空間（例如球拍很寬或在角落）
            # 隨機選一邊嘗試突破，或者直接選場地中心
            # 這裡簡化：如果沒有明顯的繞行空間，就在一個較大的隨機範圍內選取目標
            # 目標是讓蟲子看起來不會被完全卡死
            if DEBUG_BUG_SKILL: print(f"[SKILL_DEBUG][SoulEaterBugSkill] ({self.owner.identifier}) No clear path around target paddle. Choosing wider random target.")
            self.current_target_x_norm = random.uniform(0.1, 0.9) # 在大部分場地內隨機
        else:
            self.current_target_x_norm = random.choice(possible_targets)
        
        if DEBUG_BUG_SKILL: print(f"[SKILL_DEBUG][SoulEaterBugSkill] ({self.owner.identifier}) New bug X target: {self.current_target_x_norm:.2f}")

    def _handle_rest_state(self):
        """
        管理蟲子的休息狀態，包括計時器和音效。
        返回 True 如果蟲子當前正在休息，否則 False。
        """
        if not self.is_resting:
            return False

        self.rest_timer_frames -= 1
        if self.crawl_channel and self.was_crawl_sound_playing:
            self.crawl_channel.pause()
            self.was_crawl_sound_playing = False 

        if self.rest_timer_frames <= 0:
            self.is_resting = False
            self._update_target_x_norm() # 休息結束，強制選擇新方向
            if self.crawl_channel and not self.was_crawl_sound_playing and self.sound_crawl_sfx:
                try:
                    self.crawl_channel.unpause()
                    self.was_crawl_sound_playing = True
                except Exception as e: # Pygame sound unpause might fail if channel was stopped
                    if DEBUG_BUG_SKILL: print(f"[SKILL_DEBUG][SoulEaterBugSkill] Error unpausing crawl sound: {e}. Re-playing.")
                    self.crawl_channel = self.sound_crawl_sfx.play(-1) 
                    self.was_crawl_sound_playing = True
            if DEBUG_BUG_SKILL: print(f"[SKILL_DEBUG][SoulEaterBugSkill] ({self.owner.identifier}) Bug finished resting.")
            return False # 休息結束
        
        return True # 仍在休息

    def _calculate_movement_deltas_during_rest(self):
        """計算蟲子在休息時的微小漂移。"""
        base_delta_y_norm = (-self.base_y_speed if self.target_player_state == self.env.opponent else self.base_y_speed) * self.y_movement_dampening_during_rest
        random_y_offset_norm = random.uniform(-self.small_drift_during_rest_factor, self.small_drift_during_rest_factor)
        delta_y_norm = base_delta_y_norm + random_y_offset_norm
        
        target_dx_norm = (self.current_target_x_norm - self.env.ball_x) * self.goal_seeking_factor * self.x_movement_dampening_during_rest
        random_x_offset_norm = random.uniform(-self.small_drift_during_rest_factor, self.small_drift_during_rest_factor)
        delta_x_norm = target_dx_norm + random_x_offset_norm
        return delta_x_norm, delta_y_norm

    def _decide_to_rest_or_update_x_target(self):
        """更新X軸目標點，並根據機率決定是否進入休息狀態。"""
        self.frames_since_target_update += 1
        if self.frames_since_target_update >= self.target_update_interval_frames:
            self.frames_since_target_update = 0
            self._update_target_x_norm() # 更新 X 軸目標
            if self.can_rest and random.random() < self.rest_chance_after_target_update:
                self.is_resting = True
                self.rest_timer_frames = random.randint(self.min_rest_duration_frames, self.max_rest_duration_frames)
                if DEBUG_BUG_SKILL: print(f"[SKILL_DEBUG][SoulEaterBugSkill] ({self.owner.identifier}) Bug started resting for {self.rest_timer_frames} frames.")

    def _calculate_movement_deltas_active(self):
        """計算蟲子在非休息狀態下的主要移動增量 (X 和 Y)。"""
        # Y軸移動
        y_direction_sign = -1.0 if self.target_player_state == self.env.opponent else 1.0
        base_delta_y_norm = y_direction_sign * self.base_y_speed
        random_y_offset_norm = random.uniform(-self.y_random_magnitude, self.y_random_magnitude)
        delta_y_norm = base_delta_y_norm + random_y_offset_norm

        # X軸移動 (朝向目標 + 隨機探索)
        delta_x_norm = (self.current_target_x_norm - self.env.ball_x) * self.goal_seeking_factor
        random_x_offset_norm = random.choice([-1, 0, 1]) * self.x_random_walk_speed * random.uniform(0.3, 1.0)
        delta_x_norm += random_x_offset_norm
        
        return delta_x_norm, delta_y_norm

    def _apply_dodge_and_avoidance(self, delta_x_norm):
        """應用躲避目標球拍的邏輯，調整 delta_x_norm。"""
        bug_visual_radius_norm = (self.bug_image_transformed.get_width() / 2) / self.env.render_size
        target_paddle = self.target_player_state
        target_paddle_x_norm = target_paddle.x
        target_paddle_half_w_norm = target_paddle.paddle_width_normalized / 2
        effective_paddle_width_for_dodge_norm = target_paddle_half_w_norm + bug_visual_radius_norm * 0.75 
        distance_to_target_paddle_x_norm = self.env.ball_x - target_paddle_x_norm
        
        is_near_target_paddle_y = False
        if target_paddle == self.env.opponent: # 目標在上方
            target_paddle_surface_y_norm = self.env.paddle_height_normalized
            if (self.env.ball_y + bug_visual_radius_norm > target_paddle_surface_y_norm - bug_visual_radius_norm * 2) and \
               (self.env.ball_y - bug_visual_radius_norm < target_paddle_surface_y_norm + self.env.paddle_height_normalized + bug_visual_radius_norm):
                is_near_target_paddle_y = True
        else: # 目標在下方 (Player1)
            target_paddle_surface_y_norm = 1.0 - self.env.paddle_height_normalized
            if (self.env.ball_y - bug_visual_radius_norm < target_paddle_surface_y_norm + bug_visual_radius_norm * 2) and \
               (self.env.ball_y + bug_visual_radius_norm > target_paddle_surface_y_norm - self.env.paddle_height_normalized - bug_visual_radius_norm):
                is_near_target_paddle_y = True
        
        if abs(distance_to_target_paddle_x_norm) < effective_paddle_width_for_dodge_norm and is_near_target_paddle_y:
            dodge_direction = 1 if distance_to_target_paddle_x_norm >= 0 else -1 
            if distance_to_target_paddle_x_norm == 0: dodge_direction = random.choice([-1,1])
            delta_x_dodge_norm = dodge_direction * self.dodge_factor
            delta_x_norm += delta_x_dodge_norm
            if DEBUG_BUG_SKILL: print(f"[SKILL_DEBUG][SoulEaterBugSkill] ({self.owner.identifier}) Dodging target paddle. Dodge_X: {delta_x_dodge_norm:.3f}")
        
        return delta_x_norm

    def _apply_movement_and_constrain_bounds(self, delta_x_norm, delta_y_norm):
        """應用計算出的位移並限制蟲子在場地內的活動範圍。"""
        self.env.ball_y += delta_y_norm * self.env.time_scale # 蟲子也受 time_scale 影響
        self.env.ball_x += delta_x_norm * self.env.time_scale
        
        self.env.ball_y = np.clip(self.env.ball_y, 0.02, 0.98) 
        self.env.ball_x = np.clip(self.env.ball_x, 0.0, 1.0) # X軸可以貼邊

    def _check_bug_scored(self):
        """檢查蟲子是否到達目標的得分線。如果是，處理得分並返回 True。"""
        bug_visual_radius_norm_collision = (self.bug_image_transformed.get_width() / 2) / self.env.render_size
        target_goal_line_y_norm = 0.0
        scored_condition = False

        if self.target_player_state == self.env.opponent: # 目標在上方
            target_goal_line_y_norm = self.env.paddle_height_normalized / 2 
            if self.env.ball_y - bug_visual_radius_norm_collision <= target_goal_line_y_norm:
                scored_condition = True
        else: # 目標在下方 (Player1)
            target_goal_line_y_norm = 1.0 - (self.env.paddle_height_normalized / 2)
            if self.env.ball_y + bug_visual_radius_norm_collision >= target_goal_line_y_norm:
                scored_condition = True
        
        if scored_condition:
            if DEBUG_BUG_SKILL: print(f"[SKILL_DEBUG][SoulEaterBugSkill] ({self.owner.identifier}) Bug scored against {self.target_player_state.identifier}!")
            self.target_player_state.lives -= 1 
            self.target_player_state.last_hit_time = pygame.time.get_ticks()
            self.env.freeze_timer = pygame.time.get_ticks() 
            self.env.round_concluded_by_skill = True 
            self.env.current_round_info = {'scorer': self.owner.identifier, 'reason': 'bug_scored'} 
            self.deactivate(hit_paddle=False, scored=True) 
            return True # 得分，回合結束
        return False

    def _check_bug_hit_paddle(self):
        """檢查蟲子是否碰到目標的球拍。如果是，處理碰撞並返回 True。"""
        bug_visual_radius_norm_collision = (self.bug_image_transformed.get_width() / 2) / self.env.render_size
        target_paddle = self.target_player_state
        target_paddle_x_norm = target_paddle.x
        target_paddle_half_w_norm = target_paddle.paddle_width_normalized / 2
        
        target_paddle_y_surface_contact_min_norm = 0.0
        target_paddle_y_surface_contact_max_norm = 0.0

        if target_paddle == self.env.opponent: # 目標在上方
            target_paddle_y_surface_contact_min_norm = 0 
            target_paddle_y_surface_contact_max_norm = self.env.paddle_height_normalized 
        else: # 目標在下方
            target_paddle_y_surface_contact_min_norm = 1.0 - self.env.paddle_height_normalized
            target_paddle_y_surface_contact_max_norm = 1.0
            
        bug_y_min_norm = self.env.ball_y - bug_visual_radius_norm_collision
        bug_y_max_norm = self.env.ball_y + bug_visual_radius_norm_collision
        bug_x_min_norm = self.env.ball_x - bug_visual_radius_norm_collision
        bug_x_max_norm = self.env.ball_x + bug_visual_radius_norm_collision
        target_paddle_x_min_norm = target_paddle_x_norm - target_paddle_half_w_norm
        target_paddle_x_max_norm = target_paddle_x_norm + target_paddle_half_w_norm

        y_overlap = (bug_y_max_norm >= target_paddle_y_surface_contact_min_norm and \
                     bug_y_min_norm <= target_paddle_y_surface_contact_max_norm)
        x_overlap = (bug_x_max_norm >= target_paddle_x_min_norm and \
                     bug_x_min_norm <= target_paddle_x_max_norm)

        if x_overlap and y_overlap:
            if DEBUG_BUG_SKILL: print(f"[SKILL_DEBUG][SoulEaterBugSkill] ({self.owner.identifier}) Bug hit {target_paddle.identifier}'s paddle!")
            self.env.freeze_timer = pygame.time.get_ticks() 
            self.env.round_concluded_by_skill = True 
            self.env.current_round_info = {'scorer': None, 'reason': 'bug_hit_paddle'} 
            self.deactivate(hit_paddle=True, scored=False) 
            return True # 碰撞，回合結束
        return False

    def _update_trail(self):
        """更新蟲子（球）的拖尾。"""
        self.env.trail.append((self.env.ball_x, self.env.ball_y))
        if len(self.env.trail) > self.env.max_trail_length: # self.env.max_trail_length 來自 PongDuelEnv
             self.env.trail.pop(0)


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
            # 1. 獲取觀察狀態
            obs = self._get_bug_observation()
            
            # 2. 從 RL Agent 獲取動作
            #    注意：AIAgent.select_action(obs) 返回的是一個整數動作索引
            action_index = self.bug_agent.select_action(obs)
            
            # 3. 解釋動作 ("前、後、左、右、靜止") 並轉換為 delta_x_norm, delta_y_norm
            
            # 先決定基礎的 Y 軸趨向性 (如果有的話)
            y_direction_sign_to_target = -1.0 if self.target_player_state == self.env.opponent else 1.0
            
            # 根據 action_index 設定 delta_x_norm 和 delta_y_norm
            if action_index == 0: # 前 (Y 軸朝向目標)
                delta_y_norm = y_direction_sign_to_target * self.bug_y_rl_move_speed
                # X 軸可以保持為0，或者如果「前」也帶有 X 軸的微小調整，可以在此加入
            elif action_index == 1: # 後 (Y 軸遠離目標)
                delta_y_norm = -y_direction_sign_to_target * self.bug_y_rl_move_speed
            elif action_index == 2: # 左
                delta_x_norm = -self.bug_x_rl_move_speed
                # Y 軸可以保持為0，或者如果「左」也帶有 Y 軸的基礎趨向性
                # delta_y_norm = y_direction_sign_to_target * self.base_y_speed # 例如，側移時仍緩慢趨近
            elif action_index == 3: # 右
                delta_x_norm = self.bug_x_rl_move_speed
                # delta_y_norm = y_direction_sign_to_target * self.base_y_speed # 例如，側移時仍緩慢趨近
            elif action_index == 4: # 靜止
                delta_x_norm = 0.0
                delta_y_norm = 0.0 # 完全由RL控制的靜止
                # 或者如果靜止時仍希望有 base_y_speed 的影響:
                # delta_y_norm = y_direction_sign_to_target * self.base_y_speed * 0.1 # 例如非常緩慢的趨近
            else: # 未知動作索引，可以預設為靜止或打印警告
                if DEBUG_BUG_SKILL:
                    print(f"[SKILL_DEBUG][SoulEaterBugSkill] ({self.owner.identifier}) Unknown RL Action Index: {action_index}. Bug will be static.")
                delta_x_norm = 0.0
                delta_y_norm = 0.0

            # 如果 base_y_speed 不為零，並且希望 RL 的 Y 軸動作是在 base_y_speed 基礎上的疊加或替代：
            # 例如，如果動作 0/1 直接設定了 delta_y_norm，它們就已經包含了方向和 RL 控制的幅度。
            # 如果動作 2/3/4 (左/右/靜止) 時，你希望 Y 軸仍有一個基礎的趨向性，可以這樣處理：
            if self.base_y_speed != 0.0 and action_index in [2, 3, 4]: # 左、右、靜止時
                 # 讓蟲子在執行左右或靜止動作時，依然受到基礎 Y 軸引力影響
                 # 如果 action_index 0 或 1 已經設定了 delta_y_norm，這裡就不會執行
                if delta_y_norm == 0.0: # 僅當 RL 動作本身不指定 Y 移動時，才應用 base_y_speed
                    delta_y_norm = y_direction_sign_to_target * self.base_y_speed

            if DEBUG_BUG_SKILL and random.random() < 0.1:
                print(f"[SKILL_DEBUG][SoulEaterBugSkill] ({self.owner.identifier}) RL Action: {action_index}, Raw_dx: {delta_x_norm:.3f}, Raw_dy: {delta_y_norm:.3f}")

        else: # 沒有 bug_agent (模型未載入或失敗)
            if DEBUG_BUG_SKILL:
                # print(f"[SKILL_DEBUG][SoulEaterBugSkill] ({self.owner.identifier}) No bug_agent, bug using basic y-movement.")
                pass
            y_direction_sign_to_target = -1.0 if self.target_player_state == self.env.opponent else 1.0
            delta_y_norm = y_direction_sign_to_target * self.base_y_speed # 只進行基礎的 Y 軸移動


        # 4. 應用計算出的位移並限制邊界
        self._apply_movement_and_constrain_bounds(delta_x_norm, delta_y_norm)
        
        # 5. 碰撞檢測與得分邏輯
        if self._check_bug_scored():
            return 
        if self._check_bug_hit_paddle():
            return
            
        # 6. 更新拖尾 (此方法需要保留)
        self._update_trail()

    # ⭐️ 以下輔助方法需要保留，因為它們與碰撞、得分、邊界限制和拖尾相關，
    #    而不是與硬編碼的移動決策邏輯直接相關。
    #    _apply_movement_and_constrain_bounds 的內容可能需要微調以適應 RL 的輸出。

    def _apply_movement_and_constrain_bounds(self, delta_x_norm, delta_y_norm):
        """應用計算出的位移並限制蟲子在場地內的活動範圍。"""
        # 蟲子的移動也應該受到遊戲時間尺度的影響
        # (env.time_scale 通常由 SlowMoSkill 控制)
        actual_delta_x = delta_x_norm * self.env.time_scale
        actual_delta_y = delta_y_norm * self.env.time_scale
        
        self.env.ball_x += actual_delta_x
        self.env.ball_y += actual_delta_y
        
        # 邊界限制 (讓蟲子稍微能超出邊界一點點再拉回，或者嚴格限制)
        # 視覺半徑用於更精確的邊界判斷，避免圖像部分穿透
        bug_visual_radius_norm_x = (self.bug_image_transformed.get_width() / 2) / self.env.render_size
        bug_visual_radius_norm_y = (self.bug_image_transformed.get_height() / 2) / self.env.render_size

        self.env.ball_x = np.clip(self.env.ball_x, bug_visual_radius_norm_x, 1.0 - bug_visual_radius_norm_x)
        self.env.ball_y = np.clip(self.env.ball_y, bug_visual_radius_norm_y, 1.0 - bug_visual_radius_norm_y)


    def _check_bug_scored(self):
    # ... (此方法內容不變，它基於 self.env.ball_y 判斷得分) ...
        bug_visual_radius_norm_collision = (self.bug_image_transformed.get_width() / 2) / self.env.render_size # 可以用高度或寬度，取決於形狀
        target_goal_line_y_norm = 0.0
        scored_condition = False

        if self.target_player_state == self.env.opponent: # 目標在上方
            target_goal_line_y_norm = self.env.paddle_height_normalized * 0.5 # 球拍厚度中心作為得分線
            if self.env.ball_y - bug_visual_radius_norm_collision <= target_goal_line_y_norm:
                scored_condition = True
        else: # 目標在下方 (Player1)
            target_goal_line_y_norm = 1.0 - (self.env.paddle_height_normalized * 0.5)
            if self.env.ball_y + bug_visual_radius_norm_collision >= target_goal_line_y_norm:
                scored_condition = True
        
        if scored_condition:
            if DEBUG_BUG_SKILL: print(f"[SKILL_DEBUG][SoulEaterBugSkill] ({self.owner.identifier}) Bug scored against {self.target_player_state.identifier}!")
            self.target_player_state.lives -= 1 
            self.target_player_state.last_hit_time = pygame.time.get_ticks()
            self.env.freeze_timer = pygame.time.get_ticks() 
            self.env.round_concluded_by_skill = True 
            self.env.current_round_info = {'scorer': self.owner.identifier, 'reason': 'bug_scored'} 
            self.deactivate(hit_paddle=False, scored=True) 
            return True
        return False

    def _check_bug_hit_paddle(self):
    # ... (此方法內容不變，它基於蟲和板子的碰撞檢測) ...
        bug_visual_radius_norm_collision = (self.bug_image_transformed.get_width() / 2) / self.env.render_size
        target_paddle = self.target_player_state
        target_paddle_x_norm = target_paddle.x
        target_paddle_half_w_norm = target_paddle.paddle_width_normalized / 2
        
        target_paddle_y_surface_contact_min_norm = 0.0
        target_paddle_y_surface_contact_max_norm = 0.0

        if target_paddle == self.env.opponent: # 目標在上方
            target_paddle_y_surface_contact_min_norm = 0 
            target_paddle_y_surface_contact_max_norm = self.env.paddle_height_normalized 
        else: # 目標在下方
            target_paddle_y_surface_contact_min_norm = 1.0 - self.env.paddle_height_normalized
            target_paddle_y_surface_contact_max_norm = 1.0
            
        bug_y_min_norm = self.env.ball_y - bug_visual_radius_norm_collision
        bug_y_max_norm = self.env.ball_y + bug_visual_radius_norm_collision
        bug_x_min_norm = self.env.ball_x - bug_visual_radius_norm_collision
        bug_x_max_norm = self.env.ball_x + bug_visual_radius_norm_collision
        target_paddle_x_min_norm = target_paddle_x_norm - target_paddle_half_w_norm
        target_paddle_x_max_norm = target_paddle_x_norm + target_paddle_half_w_norm

        y_overlap = (bug_y_max_norm >= target_paddle_y_surface_contact_min_norm and \
                     bug_y_min_norm <= target_paddle_y_surface_contact_max_norm)
        x_overlap = (bug_x_max_norm >= target_paddle_x_min_norm and \
                     bug_x_min_norm <= target_paddle_x_max_norm)

        if x_overlap and y_overlap:
            if DEBUG_BUG_SKILL: print(f"[SKILL_DEBUG][SoulEaterBugSkill] ({self.owner.identifier}) Bug hit {target_paddle.identifier}'s paddle!")
            self.env.freeze_timer = pygame.time.get_ticks() 
            self.env.round_concluded_by_skill = True 
            self.env.current_round_info = {'scorer': None, 'reason': 'bug_hit_paddle'} 
            self.deactivate(hit_paddle=True, scored=False) 
            return True
        return False

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