# pong-soul/game/skills/soul_eater_bug_skill.py
import pygame
import math
import random
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
            # 基礎大小使用 env 的 ball_radius (假設是像素)
            base_width = self.env.ball_radius * 2
            base_height = self.env.ball_radius * 2
            # 套用縮放因子
            scaled_width = int(base_width * self.bug_display_scale_factor)
            scaled_height = int(base_height * self.bug_display_scale_factor)
            self.bug_image = pygame.transform.smoothscale(self.bug_image_surface, (scaled_width, scaled_height))
        except Exception as e:
            print(f"Error loading or scaling bug image: {bug_image_path}. Error: {e}")
            self.bug_image = None

        self.base_y_speed = cfg.get("base_y_speed", 0.02)
        self.x_amplitude = cfg.get("x_amplitude", 0.15)
        self.x_frequency = cfg.get("x_frequency", 2.0)
        self.x_homing_factor = cfg.get("x_homing_factor", 0.01)
        initial_phase_range = cfg.get("initial_phase_offset_range", [0, 6.28318])
        self.initial_phase_offset = random.uniform(initial_phase_range[0], initial_phase_range[1])
        self.time_scaling_for_wave = cfg.get("time_scaling_for_wave", 0.05)
        self.time_since_activation_frames = 0

        if not hasattr(self.env, 'bug_skill_active'):
            self.env.bug_skill_active = False
            print("Warning: Dynamically added 'bug_skill_active' to env.")
        
        # --- 載入音效 ---
        self.sound_activate_sfx = self._load_sound(cfg.get("sound_activate"))
        self.sound_crawl_sfx = self._load_sound(cfg.get("sound_crawl")) # 可選的爬行音效
        self.sound_hit_paddle_sfx = self._load_sound(cfg.get("sound_hit_paddle"))
        self.sound_score_sfx = self._load_sound(cfg.get("sound_score"))
        self.crawl_channel = None # 用於控制爬行循環音效

    def _load_sound(self, sound_path):
        if sound_path:
            try:
                return pygame.mixer.Sound(resource_path(sound_path))
            except pygame.error as e:
                print(f"Error loading sound: {sound_path}. Error: {e}")
        return None

    def activate(self):
        cur_time = pygame.time.get_ticks()
        if self.active: # 如果已經啟動，直接返回 False，不印訊息
            return False
        if not (self.cooldown_start_time == 0 or (cur_time - self.cooldown_start_time >= self.cooldown_ms)):
            # 還在冷卻中，不印訊息 (或者只在除錯模式下印)
            # print(f"{self.__class__.__name__} activation failed (cooldown).")
            return False

        self.active = True
        self.activated_time = cur_time
        self.env.bug_skill_active = True

        if hasattr(self.env, 'renderer') and self.env.renderer is not None:
            self.original_ball_image = self.env.renderer.ball_image
            if self.bug_image:
                self.env.renderer.ball_image = self.bug_image
        else:
            print("Warning: env.renderer not available for bug skill image swap.")

        self.time_since_activation_frames = 0
        self.env.ball_vx = 0
        self.env.ball_vy = 0
        self.env.spin = 0
        print(f"{self.__class__.__name__} Activated!")
        
        if self.sound_activate_sfx: # 播放啟動音效
            self.sound_activate_sfx.play()
        if self.sound_crawl_sfx: # 開始播放爬行音效 (循環)
            self.crawl_channel = self.sound_crawl_sfx.play(-1) # -1 表示無限循環
        return True

    def update(self):
        if not self.active:
            return

        current_time = pygame.time.get_ticks()
        if (current_time - self.activated_time) >= self.duration_ms:
            print(f"{self.__class__.__name__} duration expired.")
            self.deactivate(hit_paddle=False, scored=False) # 新增參數以區分停用原因
            return
        self.time_since_activation_frames += 1

    def deactivate(self, hit_paddle=False, scored=False): # 新增參數
        if self.active:
            print(f"{self.__class__.__name__} Deactivating. Hit paddle: {hit_paddle}, Scored: {scored}")
            self.active = False
            self.env.bug_skill_active = False
            self.cooldown_start_time = pygame.time.get_ticks()

            if hasattr(self.env, 'renderer') and self.env.renderer is not None and self.original_ball_image is not None:
                self.env.renderer.ball_image = self.original_ball_image
            self.original_ball_image = None
            
            if self.crawl_channel: # 停止爬行音效
                self.crawl_channel.stop()
                self.crawl_channel = None

            # 根據情況播放不同音效
            if hit_paddle and self.sound_hit_paddle_sfx:
                self.sound_hit_paddle_sfx.play()
            elif scored and self.sound_score_sfx: # 如果蟲得分有特殊音效
                self.sound_score_sfx.play()
            # 如果是超時或其他原因，可能不需要特殊音效，或播放一個通用結束音效

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
            if self.cooldown_start_time == 0:
                return 1.0
            elapsed_since_cooldown_start = current_time - self.cooldown_start_time
            if elapsed_since_cooldown_start >= self.cooldown_ms or self.cooldown_ms == 0:
                return 1.0
            else:
                ratio = elapsed_since_cooldown_start / self.cooldown_ms if self.cooldown_ms > 0 else 1.0
                return min(1.0, ratio)

    def render(self, surface):
        pass # 主要視覺由 renderer 的 ball_image 處理