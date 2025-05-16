# pong-soul/game/skills/soul_eater_bug_skill.py
import pygame
import math
import random
import numpy as np
from game.skills.base_skill import Skill
from game.skills.skill_config import SKILL_CONFIGS
from utils import resource_path

FPS = 60 # 假設遊戲幀率為60FPS
DEBUG_BUG_SKILL = False

class SoulEaterBugSkill(Skill):
    def __init__(self, env, owner_player_state): # ⭐️ 修改參數
        super().__init__(env, owner_player_state) # ⭐️ 調用父類
        cfg_key = "soul_eater_bug"
        if cfg_key not in SKILL_CONFIGS:
            print(f"[SKILL_DEBUG][SoulEaterBugSkill] ({self.owner.identifier}) CRITICAL: Config for '{cfg_key}' not found! Using defaults.")
            cfg = { # 提供最小預設值
                "duration_ms": 8000, "cooldown_ms": 12000,
                "bug_image_path": "assets/soul_eater_bug.png", # 確保此路徑有效
                "bug_display_scale_factor": 1.5, # 調整蟲子視覺大小
                "base_y_speed": 0.020, "y_random_magnitude": 0.008,
                "x_random_walk_speed": 0.025, "target_update_interval_frames": 20,
                "goal_seeking_factor": 0.07, "dodge_factor": 0.06,
                "can_rest": True, "rest_chance_after_target_update": 0.20,
                "min_rest_duration_seconds": 0.8, "max_rest_duration_seconds": 1.5,
                "y_movement_dampening_during_rest": 0.05, "x_movement_dampening_during_rest": 0.0,
                "small_drift_during_rest_factor": 0.003
            }
        else:
            cfg = SKILL_CONFIGS[cfg_key]

        self.duration_ms = int(cfg.get("duration_ms", 8000))
        self.cooldown_ms = int(cfg.get("cooldown_ms", 12000))
        self.active = False
        self.activated_time = 0
        self.cooldown_start_time = 0

        # ⭐️ 決定攻擊目標
        if self.owner == self.env.player1:
            self.target_player_state = self.env.opponent
        elif self.owner == self.env.opponent:
            self.target_player_state = self.env.player1
        else:
            # 理論上不應發生，但作為防禦性程式設計
            print(f"[SKILL_DEBUG][SoulEaterBugSkill] ({self.owner.identifier}) ERROR: Owner is neither player1 nor opponent! Defaulting target to opponent.")
            self.target_player_state = self.env.opponent 
        
        if DEBUG_BUG_SKILL: print(f"[SKILL_DEBUG][SoulEaterBugSkill] ({self.owner.identifier}) Initialized. Target: {self.target_player_state.identifier}")

        bug_image_path = cfg.get("bug_image_path", "assets/soul_eater_bug.png") # 確保有預設路徑
        self.bug_display_scale_factor = float(cfg.get("bug_display_scale_factor", 1.5))
        
        try:
            # 球的視覺半徑，用於縮放蟲子圖片
            # 假設 env.ball_radius_px 是球的實際半徑（用於物理），我們用它來基準化蟲子大小
            base_diameter = self.env.ball_radius_px * 2 
            scaled_width = int(base_diameter * self.bug_display_scale_factor)
            scaled_height = int(base_diameter * self.bug_display_scale_factor)
            if scaled_width <=0 or scaled_height <=0 : # 防禦
                scaled_width, scaled_height = int(20 * self.bug_display_scale_factor), int(20 * self.bug_display_scale_factor)
                if DEBUG_BUG_SKILL: print(f"[SKILL_DEBUG][SoulEaterBugSkill] Warning: Invalid base_diameter for bug image scaling. Using default.")

            self.bug_image_surface_loaded = pygame.image.load(resource_path(bug_image_path)).convert_alpha()
            self.bug_image_transformed = pygame.transform.smoothscale(self.bug_image_surface_loaded, (scaled_width, scaled_height))
            if DEBUG_BUG_SKILL: print(f"[SKILL_DEBUG][SoulEaterBugSkill] Bug image '{bug_image_path}' loaded and scaled to ({scaled_width}x{scaled_height}).")
        except Exception as e:
            print(f"[SKILL_DEBUG][SoulEaterBugSkill] ({self.owner.identifier}) Error loading or scaling bug image: {bug_image_path}. Error: {e}")
            # 創建一個簡單的備用圖像
            fallback_size = int(20 * self.bug_display_scale_factor)
            self.bug_image_transformed = pygame.Surface((fallback_size, fallback_size), pygame.SRCALPHA)
            pygame.draw.circle(self.bug_image_transformed, (100, 0, 100), (fallback_size//2, fallback_size//2), fallback_size//2) # 紫色蟲
            if DEBUG_BUG_SKILL: print(f"[SKILL_DEBUG][SoulEaterBugSkill] Using fallback bug image.")
            
        # 移除 env.bug_skill_active 和 env.round_concluded_by_skill 的直接賦值
        # 這些狀態應由技能內部管理或透過 PongDuelEnv 的機制設定

        self.sound_activate_sfx = self._load_sound(cfg.get("sound_activate"))
        self.sound_crawl_sfx = self._load_sound(cfg.get("sound_crawl"))
        self.sound_hit_paddle_sfx = self._load_sound(cfg.get("sound_hit_paddle"))
        self.sound_score_sfx = self._load_sound(cfg.get("sound_score"))
        self.crawl_channel = None
        self.was_crawl_sound_playing = False

        # 移動參數
        self.base_y_speed = float(cfg.get("base_y_speed", 0.020))
        self.y_random_magnitude = float(cfg.get("y_random_magnitude", 0.008))
        self.x_random_walk_speed = float(cfg.get("x_random_walk_speed", 0.025))
        self.target_update_interval_frames = int(cfg.get("target_update_interval_frames", 20))
        self.goal_seeking_factor = float(cfg.get("goal_seeking_factor", 0.07)) # 追向目標點的強度
        self.dodge_factor = float(cfg.get("dodge_factor", 0.06)) # 避開目標球拍的強度
        self.current_target_x_norm = 0.5 # 蟲子在X軸上的短期目標點 (歸一化)
        self.frames_since_target_update = 0

        # 休息行為參數
        self.can_rest = bool(cfg.get("can_rest", True))
        self.rest_chance_after_target_update = float(cfg.get("rest_chance_after_target_update", 0.20))
        min_rest_sec = float(cfg.get("min_rest_duration_seconds", 0.8))
        max_rest_sec = float(cfg.get("max_rest_duration_seconds", 1.5))
        self.min_rest_duration_frames = int(min_rest_sec * FPS)
        self.max_rest_duration_frames = int(max_rest_sec * FPS)
        self.y_movement_dampening_during_rest = float(cfg.get("y_movement_dampening_during_rest", 0.05))
        self.x_movement_dampening_during_rest = float(cfg.get("x_movement_dampening_during_rest", 0.0))
        self.small_drift_during_rest_factor = float(cfg.get("small_drift_during_rest_factor", 0.003))
        self.is_resting = False
        self.rest_timer_frames = 0

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
            self.deactivate(hit_paddle=False, scored=False) # 技能時間到，未得分也未擊中
            return

        delta_x_norm, delta_y_norm = 0.0, 0.0

        # 1. 處理休息狀態
        if self._handle_rest_state(): # 如果正在休息
            delta_x_norm, delta_y_norm = self._calculate_movement_deltas_during_rest()
        else: # 非休息狀態 (正常移動)
            # 確保爬行音效播放 (如果之前因休息暫停)
            if self.crawl_channel and not self.was_crawl_sound_playing and self.sound_crawl_sfx:
                try:
                    self.crawl_channel.unpause()
                    self.was_crawl_sound_playing = True
                except Exception as e:
                    if DEBUG_BUG_SKILL: print(f"[SKILL_DEBUG][SoulEaterBugSkill] Error unpausing crawl sound: {e}. Re-playing.")
                    self.crawl_channel = self.sound_crawl_sfx.play(-1)
                    self.was_crawl_sound_playing = True
            
            # 2. 更新 X 軸目標點並可能決定進入休息
            self._decide_to_rest_or_update_x_target()

            if self.is_resting: # 如果剛好在上面進入了休息狀態
                delta_x_norm, delta_y_norm = self._calculate_movement_deltas_during_rest()
            else: # 仍然是非休息狀態，計算主要移動
                delta_x_norm, delta_y_norm = self._calculate_movement_deltas_active()
                # 3. 應用躲避邏輯
                delta_x_norm = self._apply_dodge_and_avoidance(delta_x_norm)
        
        # 4. 應用計算出的位移並限制邊界
        self._apply_movement_and_constrain_bounds(delta_x_norm, delta_y_norm)
        
        # 5. 碰撞檢測與得分邏輯
        if self._check_bug_scored(): # 如果得分，技能已在內部停用，回合結束
            return 
        if self._check_bug_hit_paddle(): # 如果擊中球拍，技能已在內部停用，回合結束
            return
            
        # 6. 更新拖尾 (如果回合未因碰撞或得分而結束)
        self._update_trail()


    def deactivate(self, hit_paddle=False, scored=False):
        if not self.active: return # 如果本來就不是 active，直接返回

        if DEBUG_BUG_SKILL: print(f"[SKILL_DEBUG][SoulEaterBugSkill] ({self.owner.identifier}) Deactivating. Hit paddle: {hit_paddle}, Scored: {scored}")
        self.active = False
        self.is_resting = False # 確保休息狀態也重置
        self.cooldown_start_time = pygame.time.get_ticks()

        # 通知 Env 取消球的視覺效果覆蓋
        if hasattr(self.env, 'set_ball_visual_override'):
            self.env.set_ball_visual_override(skill_identifier="soul_eater_bug", active=False, owner_identifier=self.owner.identifier)
            if DEBUG_BUG_SKILL: print(f"[SKILL_DEBUG][SoulEaterBugSkill] ({self.owner.identifier}) Notified Env to restore default ball visual.")
        else:
            if DEBUG_BUG_SKILL: print(f"[SKILL_DEBUG][SoulEaterBugSkill] ({self.owner.identifier}) WARNING: env.set_ball_visual_override method not found on deactivate!")
        
        # 停止音效
        if self.crawl_channel:
            self.crawl_channel.stop()
            self.crawl_channel = None
        self.was_crawl_sound_playing = False
        
        if hit_paddle and self.sound_hit_paddle_sfx: self.sound_hit_paddle_sfx.play()
        elif scored and self.sound_score_sfx: self.sound_score_sfx.play()
        
        # 技能結束後，球的狀態應該由 PongDuelEnv 的 reset_ball_after_score 或類似機制處理
        # 不在此處直接重置球的位置和速度，因為 env.round_concluded_by_skill = True 後，
        # PongDuelEnv.step 會返回，然後 main.py 的邏輯會處理回合結束和球的重置。

    def is_active(self):
        return self.active

    def get_cooldown_seconds(self):
        # ... (與 LongPaddleSkill/SlowMoSkill 類似) ...
        if self.active: return 0.0
        current_time = pygame.time.get_ticks()
        if self.cooldown_start_time == 0: return 0.0 
        elapsed = current_time - self.cooldown_start_time
        remaining = self.cooldown_ms - elapsed
        return max(0.0, remaining / 1000.0)

    def get_energy_ratio(self):
        # ... (與 LongPaddleSkill/SlowMoSkill 類似) ...
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
        # SoulEaterBugSkill 主要的視覺效果是替換球的圖像，這在 activate/deactivate 中處理。
        # 如果蟲子有額外的視覺效果（例如特定的光暈、粒子），可以在這裡繪製。
        # 目前，我們讓 Renderer 負責繪製被替換後的球（蟲）圖像。
        pass
    
    def get_visual_params(self):
        """
        SoulEaterBugSkill 主要通過改變 Env 中的球視覺類型來影響渲染。
        如果蟲子本身有額外的、獨立於球的視覺效果（例如光環），可以在這裡返回參數。
        目前，我們假設它只改變球的基礎外觀，該改變由 PongDuelEnv.get_render_data() 中的
        ball["image_key"] 處理。
        """
        # 如果將來蟲子有例如移動時的粒子效果、特殊光暈等，可以在這裡返回參數。
        # 例如:
        # if self.is_active():
        #     return {
        #         "type": "soul_eater_bug",
        #         "active_effects": True,
        #         "aura_color_rgba": (128, 0, 128, 100) if self.is_resting else (200, 0, 200, 150),
        #         # 其他參數...
        #     }
        return {"type": "soul_eater_bug", "active_effects": self.is_active()} # 基本標識