# pong-soul/game/skills/soul_eater_bug_skill.py
import pygame
import math
import random
import numpy as np
from game.skills.base_skill import Skill
from game.skills.skill_config import SKILL_CONFIGS
from utils import resource_path

FPS = 60 # 假設遊戲幀率為60FPS
DEBUG_BUG_SKILL = True # 啟用此文件內的詳細日誌

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


    def update(self): # ⭐️ 此 update 方法現在全權負責球（蟲）的移動和碰撞邏輯
        if not self.active:
            return

        current_time = pygame.time.get_ticks()
        if (current_time - self.activated_time) >= self.duration_ms:
            if DEBUG_BUG_SKILL: print(f"[SKILL_DEBUG][SoulEaterBugSkill] ({self.owner.identifier}) Duration expired.")
            self.deactivate(hit_paddle=False, scored=False) # 技能時間到
            return

        delta_x_norm, delta_y_norm = 0.0, 0.0 # 歸一化的位移量

        # --- 休息/猶豫邏輯 ---
        if self.is_resting:
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
                    except Exception as e:
                        if DEBUG_BUG_SKILL: print(f"[SKILL_DEBUG][SoulEaterBugSkill] Error unpausing crawl sound: {e}. Re-playing.")
                        self.crawl_channel = self.sound_crawl_sfx.play(-1) # 嘗試重新播放
                        self.was_crawl_sound_playing = True
                if DEBUG_BUG_SKILL: print(f"[SKILL_DEBUG][SoulEaterBugSkill] ({self.owner.identifier}) Bug finished resting.")
            else: # 仍在休息中
                base_delta_y_norm = (-self.base_y_speed if self.target_player_state == self.env.opponent else self.base_y_speed) * self.y_movement_dampening_during_rest
                random_y_offset_norm = random.uniform(-self.small_drift_during_rest_factor, self.small_drift_during_rest_factor)
                delta_y_norm = base_delta_y_norm + random_y_offset_norm
                
                target_dx_norm = (self.current_target_x_norm - self.env.ball_x) * self.goal_seeking_factor * self.x_movement_dampening_during_rest
                random_x_offset_norm = random.uniform(-self.small_drift_during_rest_factor, self.small_drift_during_rest_factor)
                delta_x_norm = target_dx_norm + random_x_offset_norm
        else: # 非休息狀態 (正常移動)
            if self.crawl_channel and not self.was_crawl_sound_playing and self.sound_crawl_sfx:
                try:
                    self.crawl_channel.unpause(); self.was_crawl_sound_playing = True
                except Exception as e:
                    if DEBUG_BUG_SKILL: print(f"[SKILL_DEBUG][SoulEaterBugSkill] Error unpausing crawl sound: {e}. Re-playing.")
                    self.crawl_channel = self.sound_crawl_sfx.play(-1); self.was_crawl_sound_playing = True

            # Y軸移動方向取決於目標是 P1 還是 Opponent
            # 如果目標是 Opponent (在上方)，蟲子 Y 軸應主要向上移動 (負的 delta_y)
            # 如果目標是 P1 (在下方)，蟲子 Y 軸應主要向下移動 (正的 delta_y)
            y_direction_sign = -1.0 if self.target_player_state == self.env.opponent else 1.0
            base_delta_y_norm = y_direction_sign * self.base_y_speed
            random_y_offset_norm = random.uniform(-self.y_random_magnitude, self.y_random_magnitude)
            delta_y_norm = base_delta_y_norm + random_y_offset_norm

            # X軸目標點更新
            self.frames_since_target_update += 1
            if self.frames_since_target_update >= self.target_update_interval_frames:
                self.frames_since_target_update = 0
                self._update_target_x_norm()
                if self.can_rest and random.random() < self.rest_chance_after_target_update:
                    self.is_resting = True
                    self.rest_timer_frames = random.randint(self.min_rest_duration_frames, self.max_rest_duration_frames)
                    if DEBUG_BUG_SKILL: print(f"[SKILL_DEBUG][SoulEaterBugSkill] ({self.owner.identifier}) Bug started resting for {self.rest_timer_frames} frames.")
            
            if not self.is_resting: # 再次檢查，因為上面可能剛進入休息
                # X軸移動 (朝向目標 + 隨機探索 + 避障)
                target_dx_norm = (self.current_target_x_norm - self.env.ball_x) * self.goal_seeking_factor
                delta_x_norm += target_dx_norm

                random_x_offset_norm = random.choice([-1, 0, 1]) * self.x_random_walk_speed * random.uniform(0.3, 1.0)
                delta_x_norm += random_x_offset_norm
                
                # 避開目標球拍的邏輯
                # 蟲子的視覺半徑 (歸一化)
                bug_visual_radius_norm = (self.bug_image_transformed.get_width() / 2) / self.env.render_size
                
                # 目標球拍的屬性
                target_paddle_x_norm = self.target_player_state.x
                target_paddle_half_w_norm = self.target_player_state.paddle_width_normalized / 2
                
                # 避障的有效球拍寬度 (稍微放大一點，給蟲子留出空間)
                effective_paddle_width_for_dodge_norm = target_paddle_half_w_norm + bug_visual_radius_norm * 0.75 
                
                distance_to_target_paddle_x_norm = self.env.ball_x - target_paddle_x_norm
                
                # 判斷蟲子是否在目標球拍的 X 軸威脅範圍內
                if abs(distance_to_target_paddle_x_norm) < effective_paddle_width_for_dodge_norm:
                    # 判斷蟲子是否在目標球拍的 Y 軸威脅區域
                    # 對於上方球拍 (Opponent): Y 座標範圍是 [0, paddle_height_norm + 一些緩衝]
                    # 對於下方球拍 (Player1): Y 座標範圍是 [1 - paddle_height_norm - 一些緩衝, 1]
                    is_near_target_paddle_y = False
                    target_paddle_surface_y_norm = 0.0
                    if self.target_player_state == self.env.opponent: # 目標在上方
                        target_paddle_surface_y_norm = self.env.paddle_height_normalized
                        # 蟲子的 Y 底部接近或超過球拍上表面，且蟲子 Y 頂部未完全超過球拍下表面 (假設蟲子從上往下看)
                        if (self.env.ball_y + bug_visual_radius_norm > target_paddle_surface_y_norm - bug_visual_radius_norm * 2) and \
                           (self.env.ball_y - bug_visual_radius_norm < target_paddle_surface_y_norm + self.env.paddle_height_normalized + bug_visual_radius_norm):
                            is_near_target_paddle_y = True
                    else: # 目標在下方 (Player1)
                        target_paddle_surface_y_norm = 1.0 - self.env.paddle_height_normalized
                        if (self.env.ball_y - bug_visual_radius_norm < target_paddle_surface_y_norm + bug_visual_radius_norm * 2) and \
                           (self.env.ball_y + bug_visual_radius_norm > target_paddle_surface_y_norm - self.env.paddle_height_normalized - bug_visual_radius_norm):
                            is_near_target_paddle_y = True
                            
                    if is_near_target_paddle_y:
                        dodge_direction = 1 if distance_to_target_paddle_x_norm >= 0 else -1 # 往遠離球拍中心的方向躲
                        if distance_to_target_paddle_x_norm == 0: dodge_direction = random.choice([-1,1]) # 正好在中間就隨機選一邊
                        delta_x_dodge_norm = dodge_direction * self.dodge_factor
                        delta_x_norm += delta_x_dodge_norm
                        if DEBUG_BUG_SKILL: print(f"[SKILL_DEBUG][SoulEaterBugSkill] ({self.owner.identifier}) Dodging target paddle. Dodge_X: {delta_x_dodge_norm:.3f}")
        
        # 應用計算出的位移 (乘以時間尺度)
        self.env.ball_y += delta_y_norm * self.env.time_scale
        self.env.ball_x += delta_x_norm * self.env.time_scale
        
        # 限制蟲子在場地內的活動範圍 (Y軸稍微留邊，避免視覺上完全貼邊)
        self.env.ball_y = np.clip(self.env.ball_y, 0.02, 0.98) 
        self.env.ball_x = np.clip(self.env.ball_x, 0.0, 1.0)

        # --- 碰撞檢測與得分邏輯 (由蟲技能自己處理) ---
        # 蟲子的視覺半徑 (歸一化)
        bug_visual_radius_norm_collision = (self.bug_image_transformed.get_width() / 2) / self.env.render_size

        # 1. 檢查蟲子是否到達目標的得分線
        target_goal_line_y_norm = 0.0
        scored_condition = False
        if self.target_player_state == self.env.opponent: # 目標在上方，得分線在 Y=0 附近
            target_goal_line_y_norm = self.env.paddle_height_normalized / 2 # 大致在球拍厚度一半的位置算得分
            if self.env.ball_y - bug_visual_radius_norm_collision <= target_goal_line_y_norm:
                scored_condition = True
        else: # 目標在下方 (Player1)，得分線在 Y=1 附近
            target_goal_line_y_norm = 1.0 - (self.env.paddle_height_normalized / 2)
            if self.env.ball_y + bug_visual_radius_norm_collision >= target_goal_line_y_norm:
                scored_condition = True
        
        if scored_condition:
            if DEBUG_BUG_SKILL: print(f"[SKILL_DEBUG][SoulEaterBugSkill] ({self.owner.identifier}) Bug scored against {self.target_player_state.identifier}!")
            self.target_player_state.lives -= 1 # 扣除目標生命值
            self.target_player_state.last_hit_time = current_time # 用於目標血條閃爍
            self.env.freeze_timer = current_time # 觸發得分後的凍結
            self.env.round_concluded_by_skill = True # ⭐️ 設定回合結束標誌
            # ⭐️ 準備 info字典，用於 Env 的 step 返回
            self.env.current_round_info = {'scorer': self.owner.identifier} # 技能擁有者得分
            self.deactivate(hit_paddle=False, scored=True) # 停用技能
            return # 得分後，本幀的後續邏輯不再執行

        # 2. 檢查蟲子是否碰到目標的球拍
        target_paddle_x_norm = self.target_player_state.x
        target_paddle_half_w_norm = self.target_player_state.paddle_width_normalized / 2
        target_paddle_y_surface_contact_min_norm = 0.0 # 球拍接觸面的Y座標範圍
        target_paddle_y_surface_contact_max_norm = 0.0

        if self.target_player_state == self.env.opponent: # 目標在上方
            # 球拍的Y軸範圍是 [0, paddle_height_normalized]
            # 蟲子Y中心接觸球拍的範圍大致是 [ball_radius, paddle_height - ball_radius]
            # 簡化：只要蟲子的Y區間與球拍的Y區間有重疊
            target_paddle_y_surface_contact_min_norm = 0 # 球拍頂部
            target_paddle_y_surface_contact_max_norm = self.env.paddle_height_normalized # 球拍底部
        else: # 目標在下方
            target_paddle_y_surface_contact_min_norm = 1.0 - self.env.paddle_height_normalized
            target_paddle_y_surface_contact_max_norm = 1.0
            
        # 蟲子的Y軸佔據範圍
        bug_y_min_norm = self.env.ball_y - bug_visual_radius_norm_collision
        bug_y_max_norm = self.env.ball_y + bug_visual_radius_norm_collision
        
        # 蟲子的X軸佔據範圍
        bug_x_min_norm = self.env.ball_x - bug_visual_radius_norm_collision
        bug_x_max_norm = self.env.ball_x + bug_visual_radius_norm_collision

        # 目標球拍的X軸佔據範圍
        target_paddle_x_min_norm = target_paddle_x_norm - target_paddle_half_w_norm
        target_paddle_x_max_norm = target_paddle_x_norm + target_paddle_half_w_norm

        # Y軸重疊判斷
        y_overlap = (bug_y_max_norm >= target_paddle_y_surface_contact_min_norm and \
                     bug_y_min_norm <= target_paddle_y_surface_contact_max_norm)
        # X軸重疊判斷
        x_overlap = (bug_x_max_norm >= target_paddle_x_min_norm and \
                     bug_x_min_norm <= target_paddle_x_max_norm)

        if x_overlap and y_overlap:
            if DEBUG_BUG_SKILL: print(f"[SKILL_DEBUG][SoulEaterBugSkill] ({self.owner.identifier}) Bug hit {self.target_player_state.identifier}'s paddle!")
            self.env.freeze_timer = current_time # 觸發短暫凍結
            self.env.round_concluded_by_skill = True # ⭐️ 設定回合結束標誌
            # ⭐️ 蟲子被拍到，沒有人得分
            self.env.current_round_info = {'scorer': None, 'reason': 'bug_hit_paddle'} 
            self.deactivate(hit_paddle=True, scored=False) # 停用技能
            return # 碰撞後，本幀的後續邏輯不再執行

        # 更新蟲子（球）的拖尾，因為它在移動
        self.env.trail.append((self.env.ball_x, self.env.ball_y))
        if len(self.env.trail) > self.env.max_trail_length:
             self.env.trail.pop(0)


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