# pong-soul/game/skills/soul_eater_bug_skill.py
import pygame
import math
import random
import numpy as np # 確保引入 numpy
from game.skills.base_skill import Skill
from game.skills.skill_config import SKILL_CONFIGS
from utils import resource_path

class SoulEaterBugSkill(Skill):
    def __init__(self, env):
        super().__init__(env)
        cfg_key = "soul_eater_bug"
        if cfg_key not in SKILL_CONFIGS:
            raise ValueError(f"Skill configuration for '{cfg_key}' not found in SKILL_CONFIGS.")
        cfg = SKILL_CONFIGS[cfg_key]

        self.duration_ms = cfg.get("duration_ms", 6000)
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
            self.bug_image = None # Fallback to no image or default behavior

        self.base_y_speed = cfg.get("base_y_speed", 0.02)
        self.x_amplitude = cfg.get("x_amplitude", 0.15)
        self.x_frequency = cfg.get("x_frequency", 2.0)
        self.x_homing_factor = cfg.get("x_homing_factor", 0.01)
        initial_phase_range = cfg.get("initial_phase_offset_range", [0, 6.28318])
        self.initial_phase_offset = random.uniform(initial_phase_range[0], initial_phase_range[1])
        self.time_scaling_for_wave = cfg.get("time_scaling_for_wave", 0.05)
        self.time_since_activation_frames = 0

        if not hasattr(self.env, 'bug_skill_active'): # 檢查 env 是否有此屬性
            self.env.bug_skill_active = False
            # print("Warning: Dynamically added 'bug_skill_active' to env.")

        # 確保 env 有 round_concluded_by_skill 旗標 (在 init 中檢查並初始化)
        if not hasattr(self.env, 'round_concluded_by_skill'):
            self.env.round_concluded_by_skill = False
        
        self.sound_activate_sfx = self._load_sound(cfg.get("sound_activate"))
        self.sound_crawl_sfx = self._load_sound(cfg.get("sound_crawl"))
        self.sound_hit_paddle_sfx = self._load_sound(cfg.get("sound_hit_paddle"))
        self.sound_score_sfx = self._load_sound(cfg.get("sound_score"))
        self.crawl_channel = None

    def _load_sound(self, sound_path):
        if sound_path:
            try:
                return pygame.mixer.Sound(resource_path(sound_path))
            except pygame.error as e:
                print(f"Error loading sound: {sound_path}. Error: {e}")
        return None

    @property
    def overrides_ball_physics(self):
        return True

    def activate(self):
        cur_time = pygame.time.get_ticks()
        if self.active:
            return False
        if not (self.cooldown_start_time == 0 or (cur_time - self.cooldown_start_time >= self.cooldown_ms)):
            return False

        self.active = True
        self.activated_time = cur_time
        self.env.bug_skill_active = True # 環境旗標

        if hasattr(self.env, 'renderer') and self.env.renderer is not None:
            self.original_ball_image = self.env.renderer.ball_image
            if self.bug_image:
                self.env.renderer.ball_image = self.bug_image
        else:
            print("Warning: env.renderer not available for bug skill image swap.")

        self.time_since_activation_frames = 0
        self.env.ball_vx = 0 # 啟動時固定球的預設速度和旋轉
        self.env.ball_vy = 0
        self.env.spin = 0
        print(f"{self.__class__.__name__} Activated!")
        
        if self.sound_activate_sfx:
            self.sound_activate_sfx.play()
        if self.sound_crawl_sfx:
            self.crawl_channel = self.sound_crawl_sfx.play(-1)
        return True

    def update(self):
        if not self.active:
            return

        current_time = pygame.time.get_ticks()
        if (current_time - self.activated_time) >= self.duration_ms:
            print(f"{self.__class__.__name__} duration expired.")
            self.deactivate(hit_paddle=False, scored=False)
            # 技能過期不一定意味著回合結束，除非遊戲設計如此
            # 如果技能過期也算結束回合，則: self.env.round_concluded_by_skill = True
            return

        self.time_since_activation_frames += 1

        # --- 蟲球移動邏輯 ---
        delta_y = -self.base_y_speed
        homing_target_x = self.env.ai_x
        sine_oscillation = self.x_amplitude * math.sin(
            self.x_frequency * (self.time_since_activation_frames * self.time_scaling_for_wave) +
            self.initial_phase_offset
        )
        bug_aim_x = homing_target_x + sine_oscillation
        bug_aim_x = np.clip(bug_aim_x, 0.0, 1.0)
        delta_x = (bug_aim_x - self.env.ball_x) * self.x_homing_factor

        self.env.ball_y += delta_y * self.env.time_scale # 使用 env 的 time_scale
        self.env.ball_x += delta_x * self.env.time_scale
        self.env.ball_x = np.clip(self.env.ball_x, 0.0, 1.0)

        # --- 蟲球碰撞與得分邏輯 ---
        ai_goal_line_norm = (self.env.paddle_height / self.env.render_size)
        if self.env.ball_y <= ai_goal_line_norm:
            print("Bug scored against AI!")
            self.env.ai_life -= 1
            self.env.last_ai_hit_time = current_time # pygame.time.get_ticks()
            self.env.freeze_timer = current_time    # pygame.time.get_ticks()
            self.deactivate(hit_paddle=False, scored=True)
            self.env.round_concluded_by_skill = True # 設定回合結束旗標
            return

        ai_paddle_y_contact_norm = (self.env.paddle_height / self.env.render_size)
        ai_paddle_thickness_norm = (self.env.paddle_height / self.env.render_size) # 估算
        ai_paddle_x_min = self.env.ai_x - (self.env.ai_paddle_width / self.env.render_size / 2)
        ai_paddle_x_max = self.env.ai_x + (self.env.ai_paddle_width / self.env.render_size / 2)
        
        if self.bug_image: # 使用蟲圖片的寬度計算半徑
            bug_radius_norm = (self.bug_image.get_width() / 2) / self.env.render_size
        else: # Fallback
            bug_radius_norm = self.env.ball_radius / self.env.render_size


        if (self.env.ball_y - bug_radius_norm <= ai_paddle_y_contact_norm + ai_paddle_thickness_norm and \
            self.env.ball_y + bug_radius_norm >= ai_paddle_y_contact_norm): # Y軸在球拍厚度內
            if (self.env.ball_x + bug_radius_norm >= ai_paddle_x_min and \
                self.env.ball_x - bug_radius_norm <= ai_paddle_x_max): # X軸在球拍寬度內
                print("Bug hit AI paddle!")
                self.env.freeze_timer = current_time # pygame.time.get_ticks()
                self.deactivate(hit_paddle=True, scored=False)
                self.env.round_concluded_by_skill = True # 設定回合結束旗標
                return

        # --- 蟲球拖尾更新 ---
        self.env.trail.append((self.env.ball_x, self.env.ball_y))
        if len(self.env.trail) > self.env.max_trail_length:
             self.env.trail.pop(0)

    def deactivate(self, hit_paddle=False, scored=False):
        if self.active:
            print(f"{self.__class__.__name__} Deactivating. Hit paddle: {hit_paddle}, Scored: {scored}")
            self.active = False
            self.env.bug_skill_active = False # 重置環境旗標
            self.cooldown_start_time = pygame.time.get_ticks()

            if hasattr(self.env, 'renderer') and self.env.renderer is not None and self.original_ball_image is not None:
                self.env.renderer.ball_image = self.original_ball_image
            self.original_ball_image = None
            
            if self.crawl_channel:
                self.crawl_channel.stop()
                self.crawl_channel = None

            if hit_paddle and self.sound_hit_paddle_sfx:
                self.sound_hit_paddle_sfx.play()
            elif scored and self.sound_score_sfx:
                self.sound_score_sfx.play()

    def is_active(self):
        return self.active

    def get_cooldown_seconds(self):
        if self.active:
            return 0.0
        current_time = pygame.time.get_ticks()
        if self.cooldown_start_time == 0:
            return 0.0
        elapsed_since_cooldown_start = current_time - self.cooldown_start_time
        remaining_cooldown_ms = self.cooldown_ms - elapsed_since_cooldown_start
        return max(0.0, remaining_cooldown_ms / 1000.0)

    def get_energy_ratio(self):
        current_time = pygame.time.get_ticks()
        if self.active:
            elapsed_duration = current_time - self.activated_time
            ratio = max(0.0, (self.duration_ms - elapsed_duration) / self.duration_ms) if self.duration_ms > 0 else 0.0
            return ratio
        else:
            if self.cooldown_start_time == 0: # 還沒開始過冷卻
                return 1.0 # 能量滿
            elapsed_since_cooldown_start = current_time - self.cooldown_start_time
            if elapsed_since_cooldown_start >= self.cooldown_ms or self.cooldown_ms == 0:
                return 1.0 # 冷卻結束，能量滿
            else:
                ratio = elapsed_since_cooldown_start / self.cooldown_ms if self.cooldown_ms > 0 else 1.0
                return min(1.0, ratio) # 冷卻中，顯示進度

    def render(self, surface):
        pass # 主要視覺由 renderer 的 ball_image 處理