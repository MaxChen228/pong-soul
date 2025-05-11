# pong-soul/game/skills/soul_eater_bug_skill.py
import pygame
import math
import random
import numpy as np
from game.skills.base_skill import Skill
from game.skills.skill_config import SKILL_CONFIGS
from utils import resource_path

FPS = 60 # 假設遊戲幀率為60FPS，用於將秒轉換為幀

class SoulEaterBugSkill(Skill):
    def __init__(self, env):
        super().__init__(env)
        cfg_key = "soul_eater_bug"
        if cfg_key not in SKILL_CONFIGS:
            raise ValueError(f"Skill configuration for '{cfg_key}' not found in SKILL_CONFIGS.")
        cfg = SKILL_CONFIGS[cfg_key]

        self.duration_ms = cfg.get("duration_ms", 8000)
        self.cooldown_ms = cfg.get("cooldown_ms", 12000)
        self.active = False
        self.activated_time = 0
        self.cooldown_start_time = 0
        self.original_ball_image = None
        bug_image_path = cfg.get("bug_image_path", "assets/default_bug.png")
        self.bug_display_scale_factor = cfg.get("bug_display_scale_factor", 1.0)
        try:
            self.bug_image_surface = pygame.image.load(resource_path(bug_image_path)).convert_alpha()
            base_width = self.env.ball_radius * 2
            base_height = self.env.ball_radius * 2
            scaled_width = int(base_width * self.bug_display_scale_factor)
            scaled_height = int(base_height * self.bug_display_scale_factor)
            self.bug_image = pygame.transform.smoothscale(self.bug_image_surface, (scaled_width, scaled_height))
        except Exception as e:
            print(f"Error loading or scaling bug image: {bug_image_path}. Error: {e}")
            self.bug_image = None
        self.time_since_activation_frames = 0
        if not hasattr(self.env, 'bug_skill_active'): self.env.bug_skill_active = False
        if not hasattr(self.env, 'round_concluded_by_skill'): self.env.round_concluded_by_skill = False
        
        self.sound_activate_sfx = self._load_sound(cfg.get("sound_activate"))
        self.sound_crawl_sfx = self._load_sound(cfg.get("sound_crawl"))
        self.sound_hit_paddle_sfx = self._load_sound(cfg.get("sound_hit_paddle"))
        self.sound_score_sfx = self._load_sound(cfg.get("sound_score"))
        self.crawl_channel = None
        self.was_crawl_sound_playing = False # 用於休息時暫停/恢復爬行音效

        self.base_y_speed = cfg.get("base_y_speed", 0.020)
        self.y_random_magnitude = cfg.get("y_random_magnitude", 0.008)
        self.x_random_walk_speed = cfg.get("x_random_walk_speed", 0.025)
        self.target_update_interval_frames = cfg.get("target_update_interval_frames", 20)
        self.goal_seeking_factor = cfg.get("goal_seeking_factor", 0.07)
        self.dodge_factor = cfg.get("dodge_factor", 0.06)
        self.current_target_x = 0.5
        self.frames_since_target_update = 0

        self.can_rest = cfg.get("can_rest", True)
        self.rest_chance_after_target_update = cfg.get("rest_chance_after_target_update", 0.20)
        min_rest_sec = cfg.get("min_rest_duration_seconds", 0.8)
        max_rest_sec = cfg.get("max_rest_duration_seconds", 1.5)
        self.min_rest_duration_frames = int(min_rest_sec * FPS)
        self.max_rest_duration_frames = int(max_rest_sec * FPS)
        self.y_movement_dampening_during_rest = cfg.get("y_movement_dampening_during_rest", 0.05)
        self.x_movement_dampening_during_rest = cfg.get("x_movement_dampening_during_rest", 0.0)
        self.small_drift_during_rest_factor = cfg.get("small_drift_during_rest_factor", 0.003)
        
        self.is_resting = False
        self.rest_timer_frames = 0

    def _load_sound(self, sound_path):
        if sound_path:
            try: return pygame.mixer.Sound(resource_path(sound_path))
            except pygame.error as e: print(f"Error loading sound: {sound_path}. Error: {e}")
        return None

    @property
    def overrides_ball_physics(self): return True

    def activate(self):
        # ... (activate 邏輯與之前相同, 確保 is_resting 和 rest_timer_frames 被重置) ...
        cur_time = pygame.time.get_ticks()
        if self.active: return False
        if not (self.cooldown_start_time == 0 or (cur_time - self.cooldown_start_time >= self.cooldown_ms)): return False
        self.active = True
        self.activated_time = cur_time
        self.env.bug_skill_active = True
        if hasattr(self.env, 'renderer') and self.env.renderer is not None:
            self.original_ball_image = self.env.renderer.ball_image
            if self.bug_image: self.env.renderer.ball_image = self.bug_image
        self.time_since_activation_frames = 0
        self.env.ball_vx = 0; self.env.ball_vy = 0; self.env.spin = 0
        self.is_resting = False
        self.rest_timer_frames = 0
        self.was_crawl_sound_playing = False
        print(f"{self.__class__.__name__} Activated!")
        if self.sound_activate_sfx: self.sound_activate_sfx.play()
        if self.sound_crawl_sfx:
            self.crawl_channel = self.sound_crawl_sfx.play(-1)
            self.was_crawl_sound_playing = True
        return True

    def _update_target_x(self):
        """獨立出更新目標X的邏輯，在非休息或休息結束後調用"""
        ai_paddle_center_x = self.env.ai_x
        ai_paddle_half_w_norm = (self.env.ai_paddle_width / self.env.render_size) / 2
        ai_paddle_left_edge = ai_paddle_center_x - ai_paddle_half_w_norm
        ai_paddle_right_edge = ai_paddle_center_x + ai_paddle_half_w_norm
        possible_targets = []
        if ai_paddle_left_edge > 0.1: # 左邊有空間
            possible_targets.append(random.uniform(0.05, max(0.05, ai_paddle_left_edge - 0.05)))
        if ai_paddle_right_edge < 0.9: # 右邊有空間
            possible_targets.append(random.uniform(min(0.95, ai_paddle_right_edge + 0.05), 0.95))
        if not possible_targets: # 都沒空間，選一個方向硬闖或隨機
            if self.env.ball_x < ai_paddle_center_x: # 蟲在板左
                 if ai_paddle_right_edge < 0.95 : possible_targets.append(random.uniform(ai_paddle_right_edge + 0.02, 0.95))
                 else: possible_targets.append(0.9)
            else: # 蟲在板右
                 if ai_paddle_left_edge > 0.05 : possible_targets.append(random.uniform(0.05, ai_paddle_left_edge - 0.02))
                 else: possible_targets.append(0.1)
            if not possible_targets: possible_targets.append(random.uniform(0.1, 0.9))
        self.current_target_x = random.choice(possible_targets)
        # print(f"Bug new target X: {self.current_target_x:.2f}")

    def update(self):
        if not self.active: return

        current_time = pygame.time.get_ticks()
        if (current_time - self.activated_time) >= self.duration_ms:
            print(f"{self.__class__.__name__} duration expired.")
            self.deactivate(hit_paddle=False, scored=False)
            return

        self.time_since_activation_frames += 1
        delta_x, delta_y = 0.0, 0.0

        # --- 休息/猶豫邏輯 ---
        if self.is_resting:
            self.rest_timer_frames -= 1
            if self.crawl_channel and self.was_crawl_sound_playing: # 休息時暫停爬行音
                self.crawl_channel.pause()
                self.was_crawl_sound_playing = False # 避免重複pause

            if self.rest_timer_frames <= 0:
                self.is_resting = False
                self._update_target_x() # 休息結束，強制選擇新方向
                if self.crawl_channel and not self.was_crawl_sound_playing: # 恢復爬行音
                     if self.sound_crawl_sfx: # 確保音效物件存在
                        try:
                            # 重新播放可能導致從頭開始，如果支援 resume 更好，否則就 unpause
                            # self.crawl_channel = self.sound_crawl_sfx.play(-1)
                            self.crawl_channel.unpause() # pygame.mixer.Channel.unpause()
                            self.was_crawl_sound_playing = True
                        except Exception as e:
                            print(f"Error resuming crawl sound: {e}")
                            if self.sound_crawl_sfx: # 嘗試重新播放
                                self.crawl_channel = self.sound_crawl_sfx.play(-1)
                                self.was_crawl_sound_playing = True


            else: # 仍在休息中
                # Y軸移動 (大幅減緩或微小漂移)
                base_delta_y = -self.base_y_speed * self.y_movement_dampening_during_rest
                random_y_offset = random.uniform(-self.small_drift_during_rest_factor, self.small_drift_during_rest_factor)
                delta_y = base_delta_y + random_y_offset
                
                # X軸移動 (幾乎不動或微小漂移)
                target_dx = (self.current_target_x - self.env.ball_x) * self.goal_seeking_factor * self.x_movement_dampening_during_rest
                random_x_offset = random.uniform(-self.small_drift_during_rest_factor, self.small_drift_during_rest_factor)
                delta_x = target_dx + random_x_offset
        else: # 非休息狀態 (正常移動)
            if self.crawl_channel and not self.was_crawl_sound_playing: # 確保非休息時爬行音效播放
                if self.sound_crawl_sfx:
                    try:
                        self.crawl_channel.unpause()
                        self.was_crawl_sound_playing = True
                    except Exception as e:
                         print(f"Error unpausing crawl sound: {e}")
                         if self.sound_crawl_sfx:
                            self.crawl_channel = self.sound_crawl_sfx.play(-1)
                            self.was_crawl_sound_playing = True


            # Y軸移動
            base_delta_y = -self.base_y_speed
            random_y_offset = random.uniform(-self.y_random_magnitude, self.y_random_magnitude)
            delta_y = base_delta_y + random_y_offset

            # X軸目標點更新
            self.frames_since_target_update += 1
            if self.frames_since_target_update >= self.target_update_interval_frames:
                self.frames_since_target_update = 0
                self._update_target_x() # 更新目標X
                # 在更新目標後，有機率進入休息
                if self.can_rest and random.random() < self.rest_chance_after_target_update:
                    self.is_resting = True
                    self.rest_timer_frames = random.randint(self.min_rest_duration_frames, self.max_rest_duration_frames)
                    # print(f"Bug started resting for {self.rest_timer_frames} frames.")
                    # 當進入休息時，當前的delta_x, delta_y計算會被下一輪的is_resting分支覆蓋

            if not self.is_resting: # 再次檢查，因為上面可能剛進入休息
                # X軸移動邏輯 (目標導向 + 隨機探索 + 避障)
                # 1. 朝向短期目標點移動
                target_dx = (self.current_target_x - self.env.ball_x) * self.goal_seeking_factor
                delta_x += target_dx

                # 2. 隨機擾動/探索
                random_x_offset_direction = random.choice([-1, 0, 1])
                random_x_offset = random_x_offset_direction * self.x_random_walk_speed * random.uniform(0.3, 1.0)
                delta_x += random_x_offset

                # 3. 避開AI球拍的直接威脅 (避障應總是有效)
                bug_radius_norm = (self.bug_image.get_width() / 2) / self.env.render_size if self.bug_image else self.env.ball_radius / self.env.render_size
                ai_paddle_half_w_norm = (self.env.ai_paddle_width / self.env.render_size) / 2
                effective_paddle_width_for_dodge = ai_paddle_half_w_norm + bug_radius_norm * 0.5 # 給一點緩衝
                distance_to_ai_paddle_x = self.env.ball_x - self.env.ai_x
                
                if abs(distance_to_ai_paddle_x) < effective_paddle_width_for_dodge:
                    ai_paddle_y_surface = self.env.paddle_height / self.env.render_size
                    threat_y_start = ai_paddle_y_surface - bug_radius_norm * 2 
                    threat_y_end = ai_paddle_y_surface + (self.env.paddle_height / self.env.render_size) + bug_radius_norm
                    if self.env.ball_y > threat_y_start and self.env.ball_y < threat_y_end:
                        dodge_direction = 1 if distance_to_ai_paddle_x >= 0 else -1
                        if distance_to_ai_paddle_x == 0: dodge_direction = random.choice([-1,1])
                        delta_x_dodge = dodge_direction * self.dodge_factor
                        delta_x += delta_x_dodge
        
        # 應用計算出的位移
        self.env.ball_y += delta_y * self.env.time_scale
        self.env.ball_x += delta_x * self.env.time_scale
        self.env.ball_y = np.clip(self.env.ball_y, 0.0, 0.95) # Y軸裁切
        self.env.ball_x = np.clip(self.env.ball_x, 0.0, 1.0) # X軸裁切

        # --- 碰撞檢測與得分邏輯 ---
        # (這部分與之前的版本相同，檢查 self.env.ball_y 和 self.env.ball_x)
        ai_goal_line_norm = (self.env.paddle_height / self.env.render_size)
        if self.env.ball_y <= ai_goal_line_norm:
            print("Bug scored against AI!")
            self.env.ai_life -= 1
            self.env.last_ai_hit_time = current_time
            self.env.freeze_timer = current_time
            self.deactivate(hit_paddle=False, scored=True)
            self.env.round_concluded_by_skill = True
            return

        bug_radius_norm = (self.bug_image.get_width() / 2) / self.env.render_size if self.bug_image else self.env.ball_radius / self.env.render_size
        ai_paddle_half_w_norm = (self.env.ai_paddle_width / self.env.render_size) / 2
        ai_paddle_y_contact_norm = (self.env.paddle_height / self.env.render_size)
        ai_paddle_thickness_norm = (self.env.paddle_height / self.env.render_size)
        ai_paddle_x_min = self.env.ai_x - ai_paddle_half_w_norm
        ai_paddle_x_max = self.env.ai_x + ai_paddle_half_w_norm
        
        if (self.env.ball_y - bug_radius_norm <= ai_paddle_y_contact_norm + ai_paddle_thickness_norm and \
            self.env.ball_y + bug_radius_norm >= ai_paddle_y_contact_norm):
            if (self.env.ball_x + bug_radius_norm >= ai_paddle_x_min and \
                self.env.ball_x - bug_radius_norm <= ai_paddle_x_max):
                print("Bug hit AI paddle!")
                self.env.freeze_timer = current_time
                self.deactivate(hit_paddle=True, scored=False)
                self.env.round_concluded_by_skill = True
                return

        # --- 拖尾更新 ---
        self.env.trail.append((self.env.ball_x, self.env.ball_y))
        if len(self.env.trail) > self.env.max_trail_length:
             self.env.trail.pop(0)

    def deactivate(self, hit_paddle=False, scored=False):
        if self.active:
            # ... (deactivate 邏輯與之前相同, 確保 is_resting 和 crawl_channel 被處理) ...
            print(f"{self.__class__.__name__} Deactivating. Hit paddle: {hit_paddle}, Scored: {scored}")
            self.active = False
            self.is_resting = False 
            self.env.bug_skill_active = False
            self.cooldown_start_time = pygame.time.get_ticks()
            if hasattr(self.env, 'renderer') and self.env.renderer is not None and self.original_ball_image is not None:
                self.env.renderer.ball_image = self.original_ball_image
            self.original_ball_image = None
            if self.crawl_channel: # 確保先停止再清除
                self.crawl_channel.stop()
                self.crawl_channel = None
            self.was_crawl_sound_playing = False # 重置
            if hit_paddle and self.sound_hit_paddle_sfx: self.sound_hit_paddle_sfx.play()
            elif scored and self.sound_score_sfx: self.sound_score_sfx.play()

    # ... (is_active, get_cooldown_seconds, get_energy_ratio, render 方法與之前相同) ...
    def is_active(self):
        return self.active

    def get_cooldown_seconds(self):
        if self.active: return 0.0
        current_time = pygame.time.get_ticks()
        if self.cooldown_start_time == 0: return 0.0 # 如果技能從未啟動或冷卻完成
        elapsed = current_time - self.cooldown_start_time
        remaining = self.cooldown_ms - elapsed
        return max(0.0, remaining / 1000.0)

    def get_energy_ratio(self):
        current_time = pygame.time.get_ticks()
        if self.active:
            elapsed = current_time - self.activated_time
            return max(0.0, (self.duration_ms - elapsed) / self.duration_ms) if self.duration_ms > 0 else 0.0
        else: # 計算冷卻進度作為能量條
            if self.cooldown_start_time == 0: return 1.0 # 還沒開始過第一次冷卻，能量滿
            elapsed_cooldown = current_time - self.cooldown_start_time
            if elapsed_cooldown >= self.cooldown_ms: return 1.0 # 冷卻結束
            return min(1.0, elapsed_cooldown / self.cooldown_ms) if self.cooldown_ms > 0 else 1.0
            
    def render(self, surface):
        pass # 主要視覺由 renderer 的 ball_image 處理