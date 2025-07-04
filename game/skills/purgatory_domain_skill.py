# game/skills/purgatory_domain_skill.py
import pygame
import random
import math
import numpy as np

from game.skills.base_skill import Skill
from game.skills.skill_config import SKILL_CONFIGS # 用於讀取設定
from utils import resource_path # 用於載入音效等資源

DEBUG_PURGATORY_SKILL = True # 技能專用除錯開關

class PurgatoryDomainSkill(Skill):
    def __init__(self, env, owner_player_state):
        super().__init__(env, owner_player_state)
        skill_key = "purgatory_domain"
        cfg = SKILL_CONFIGS.get(skill_key, {})

        if not cfg:
            if DEBUG_PURGATORY_SKILL:
                print(f"[SKILL_DEBUG][{self.__class__.__name__}] ({self.owner.identifier}) CRITICAL: Config for '{skill_key}' not found! Using internal defaults.")
            cfg = {
                "duration_ms": 7000, "cooldown_ms": 15000, "bar_color": [70, 0, 100],
                "ball_instability_factor": 0.1, "ball_base_speed_in_domain": 0.03,
                "ball_seek_target_strength": 0.0, "opponent_paddle_slowdown_factor": 1.0,
                "domain_filter_color_rgba": [30, 0, 50, 100], "ball_aura_color_rgba": [120, 50, 150, 200],
                "sound_activate": None, "sound_domain_loop": None, "sound_ball_event": None, "sound_deactivate": None,
                "pixel_flame_effect": {"enabled": False},
                "activation_animation": { # 基本的 activation_animation 預設
                    "enabled": False, 
                    "duration_ms": 0,
                    "ball_effect": { # 新增 ball_effect 的預設
                        "enabled": False,
                        "vibration_intensity_norm": 0.005,
                        "jump_intensity_norm": 0.01,
                        "jump_frequency_hz": 2.0,
                        "spin_speed_dps": 720,
                        "hold_ball_at_center": True,
                        "center_x_norm": 0.5,
                        "center_y_norm": 0.5
                    }
                }
            }

        self.duration_ms = int(cfg.get("duration_ms", 7000))
        self.cooldown_ms = int(cfg.get("cooldown_ms", 15000))
        self.ball_instability_factor = float(cfg.get("ball_instability_factor", 0.1))
        self.ball_base_speed_in_domain = float(cfg.get("ball_base_speed_in_domain", 0.03))
        self.ball_seek_target_strength = float(cfg.get("ball_seek_target_strength", 0.0))
        self.opponent_paddle_slowdown_factor = float(cfg.get("opponent_paddle_slowdown_factor", 1.0))

        self.domain_filter_color_rgba = tuple(cfg.get("domain_filter_color_rgba", [30, 0, 50, 100]))
        self.ball_aura_color_rgba = tuple(cfg.get("ball_aura_color_rgba", [120, 50, 150, 200]))

        self.sound_activate = self._load_sound(cfg.get("sound_activate"))
        self.sound_domain_loop = self._load_sound(cfg.get("sound_domain_loop"))
        self.sound_ball_event = self._load_sound(cfg.get("sound_ball_event"))
        self.sound_deactivate = self._load_sound(cfg.get("sound_deactivate"))
        self.domain_loop_channel = None

        self.pixel_flame_config = cfg.get("pixel_flame_effect", {})
        self.flame_particles_enabled = self.pixel_flame_config.get("enabled", False)
        self.flame_particles = []
        self.last_particle_emission_time = 0

        self.activation_animation_config = cfg.get("activation_animation", {})
        self.activation_animation_enabled = self.activation_animation_config.get("enabled", False)
        self.activation_animation_duration_ms = self.activation_animation_config.get("duration_ms", 0)
        self.is_in_activation_animation = False
        self.activation_animation_start_time = 0
        
        # --- 新增：讀取入場動畫時球體的特殊效果參數 ---
        self.ball_anim_effect_config = self.activation_animation_config.get("ball_effect", {})
        self.ball_anim_effect_enabled = self.ball_anim_effect_config.get("enabled", False)
        self.ball_anim_vibration_intensity = self.ball_anim_effect_config.get("vibration_intensity_norm", 0.005)
        self.ball_anim_jump_intensity = self.ball_anim_effect_config.get("jump_intensity_norm", 0.01)
        self.ball_anim_jump_frequency = self.ball_anim_effect_config.get("jump_frequency_hz", 2.0)
        self.ball_anim_spin_speed_dps = self.ball_anim_effect_config.get("spin_speed_dps", 720) # dps = degrees per second
        self.ball_anim_hold_at_center = self.ball_anim_effect_config.get("hold_ball_at_center", True)
        self.ball_anim_center_x = self.ball_anim_effect_config.get("center_x_norm", 0.5)
        self.ball_anim_center_y = self.ball_anim_effect_config.get("center_y_norm", 0.5)
        self.current_ball_animation_spin_angle = 0 # 用於累積球在動畫期間的視覺旋轉角度
        # --- 新增結束 ---

        if DEBUG_PURGATORY_SKILL and self.flame_particles_enabled:
            print(f"[SKILL_DEBUG][{self.__class__.__name__}] ({self.owner.identifier}) Pixel Flame Effect enabled with config: {self.pixel_flame_config}")
        
        if DEBUG_PURGATORY_SKILL and self.activation_animation_enabled:
            print(f"[SKILL_DEBUG][{self.__class__.__name__}] ({self.owner.identifier}) Activation Animation enabled. Duration: {self.activation_animation_duration_ms}ms, Config: {self.activation_animation_config}")
            if self.ball_anim_effect_enabled:
                 print(f"    Ball Anim Effect enabled with config: {self.ball_anim_effect_config}")


        self.active = False
        self.activated_time = 0
        self.cooldown_start_time = 0

        if DEBUG_PURGATORY_SKILL:
            print(f"[SKILL_DEBUG][{self.__class__.__name__}] ({self.owner.identifier}) Initialized. Duration: {self.duration_ms}ms, Cooldown: {self.cooldown_ms}ms")
    
    
    def _create_flame_particle(self):
        """創建一個新的火焰粒子並返回其屬性字典。"""
        if not self.flame_particles_enabled:
            return None

        # 從環境中獲取當前球的位置和速度 (正規化座標)
        # 確保 self.env.ball_x, self.env.ball_y, self.env.ball_vx, self.env.ball_vy 是最新的
        # 這些值通常在 PongDuelEnv.step 的物理更新之後才是最新的
        # 粒子生成應該基於球的當前幀位置
        ball_x_norm = self.env.ball_x
        ball_y_norm = self.env.ball_y
        ball_vx_norm = self.env.ball_vx
        ball_vy_norm = self.env.ball_vy

        # 從配置讀取粒子參數
        base_size_px = self.pixel_flame_config.get("particle_base_size_px", 3)
        lifetime_ms = self.pixel_flame_config.get("particle_lifetime_ms", 500)
        color_start = self.pixel_flame_config.get("color_start_rgba", [255, 200, 0, 220])
        
        # 粒子初始位置略微偏離球心，更像從球體表面發出
        # 這裡的 self.env.ball_radius_normalized 是指標準球的碰撞半徑
        # 火焰粒子可以從這個半徑附近發出
        angle_offset = random.uniform(0, 2 * math.pi)
        pos_offset_factor = self.env.ball_radius_normalized * random.uniform(0.5, 1.0)
        particle_x = ball_x_norm + pos_offset_factor * math.cos(angle_offset)
        particle_y = ball_y_norm + pos_offset_factor * math.sin(angle_offset)

        # 粒子初始速度：大致與球運動方向相反，並帶有擴散
        # 計算球速度的反方向
        ball_speed_magnitude = math.sqrt(ball_vx_norm**2 + ball_vy_norm**2)
        if ball_speed_magnitude > 1e-6: # 避免除以零
            base_vx = -ball_vx_norm / ball_speed_magnitude
            base_vy = -ball_vy_norm / ball_speed_magnitude
        else: # 球靜止時，隨機一個基礎方向
            random_base_angle = random.uniform(0, 2 * math.pi)
            base_vx = math.cos(random_base_angle)
            base_vy = math.sin(random_base_angle)

        # 粒子發射速度大小
        emission_speed_min = self.pixel_flame_config.get("emission_speed_min_factor", 0.005)
        emission_speed_max = self.pixel_flame_config.get("emission_speed_max_factor", 0.015)
        particle_speed_magnitude = random.uniform(emission_speed_min, emission_speed_max)

        # 擴散角度
        spread_angle_rad = math.radians(self.pixel_flame_config.get("spread_angle_deg", 45))
        angle_perturbation = random.uniform(-spread_angle_rad, spread_angle_rad)
        
        # 將基礎速度向量旋轉一個擾動角度
        final_vx = base_vx * math.cos(angle_perturbation) - base_vy * math.sin(angle_perturbation)
        final_vy = base_vx * math.sin(angle_perturbation) + base_vy * math.cos(angle_perturbation)
        
        # 應用粒子速度大小
        final_vx *= particle_speed_magnitude
        final_vy *= particle_speed_magnitude
        
        particle = {
            'x_norm': particle_x,
            'y_norm': particle_y,
            'vx_norm': final_vx,
            'vy_norm': final_vy,
            'lifetime_ms_remaining': lifetime_ms + random.uniform(-lifetime_ms * 0.2, lifetime_ms * 0.2), # 生命週期帶一點隨機
            'initial_lifetime_ms': lifetime_ms, # 用於計算顏色漸變的比例
            'current_color_rgba': list(color_start), # 確保是可變列表
            'current_size_px': base_size_px, # 初始大小
        }
        return particle
    
    def _load_sound(self, sound_path_str):
        if sound_path_str:
            try:
                return pygame.mixer.Sound(resource_path(sound_path_str))
            except pygame.error as e:
                if DEBUG_PURGATORY_SKILL:
                    print(f"[SKILL_DEBUG][{self.__class__.__name__}] Error loading sound '{sound_path_str}': {e}")
        return None

    @property
    def overrides_ball_physics(self):
        return True

    def activate(self):
        self.flame_particles.clear()
        self.last_particle_emission_time = pygame.time.get_ticks()
        current_time = pygame.time.get_ticks()

        if self.active:
            if DEBUG_PURGATORY_SKILL: print(f"[SKILL_DEBUG][{self.__class__.__name__}] ({self.owner.identifier}) Activation failed: Already active.")
            return False
        if not (self.cooldown_start_time == 0 or (current_time - self.cooldown_start_time >= self.cooldown_ms)):
            if DEBUG_PURGATORY_SKILL: print(f"[SKILL_DEBUG][{self.__class__.__name__}] ({self.owner.identifier}) Activation failed: On cooldown ({self.get_cooldown_seconds():.1f}s left).")
            return False

        self.active = True
        self.activated_time = current_time

        if self.activation_animation_enabled:
            self.is_in_activation_animation = True
            self.activation_animation_start_time = current_time
            self.current_ball_animation_spin_angle = 0 # 重置動畫旋轉角度
            if DEBUG_PURGATORY_SKILL:
                print(f"[SKILL_DEBUG][{self.__class__.__name__}] ({self.owner.identifier}) Activation Animation sequence started at {current_time}.")
            
            # --- 新增：如果設定了入場動畫時固定球位置 ---
            if self.ball_anim_effect_enabled and self.ball_anim_hold_at_center:
                self.env.ball_x = self.ball_anim_center_x
                self.env.ball_y = self.ball_anim_center_y
                self.env.ball_vx = 0
                self.env.ball_vy = 0
                self.env.spin = 0 # 物理自旋也歸零，視覺自旋由 current_ball_animation_spin_angle 控制
                self.env.trail.clear() # 清除舊的軌跡
                if DEBUG_PURGATORY_SKILL:
                    print(f"    Ball position set for animation: ({self.env.ball_x:.2f}, {self.env.ball_y:.2f}), Vel: (0,0)")
            # --- 新增結束 ---
        else:
            self.is_in_activation_animation = False
        
        if DEBUG_PURGATORY_SKILL: print(f"[SKILL_DEBUG][{self.__class__.__name__}] ({self.owner.identifier}) Activated!")

        if self.sound_activate:
            self.sound_activate.play()
        if self.sound_domain_loop:
            self.domain_loop_channel = self.sound_domain_loop.play(loops=-1)
        return True
    # <<< 新增的 update 方法 >>>
    def update(self):
        """
        此方法由 PongDuelEnv._update_active_skills() 每幀呼叫。
        負責檢查技能持續時間、生成和更新火焰粒子。
        """
        current_time_ms = pygame.time.get_ticks()

        if self.active:
            # 檢查技能持續時間
            if (current_time_ms - self.activated_time) >= self.duration_ms:
                if DEBUG_PURGATORY_SKILL:
                    print(f"[SKILL_DEBUG][{self.__class__.__name__}] ({self.owner.identifier}) Duration expired. Deactivating from update().")
                self.deactivate(duration_expired=True)
                # 技能已停用，但粒子可能還需要最後一次更新（如果deactivate不清除它們）
                # 或者在這裡直接返回，讓deactivate處理粒子
                # return # 視 deactivate 的實現而定

            # --- 像素火焰粒子生成 ---
            if self.flame_particles_enabled:
                max_particles = self.pixel_flame_config.get("particle_count", 30)
                # 根據粒子總數和生命週期估算一個合適的生成間隔，嘗試維持最大粒子數
                # 例如，如果生命週期是500ms，想維持30個粒子，大約每 500/30 = 16ms 生成一個
                particle_lifetime_ms = self.pixel_flame_config.get("particle_lifetime_ms", 500)
                emission_interval_ms = (particle_lifetime_ms / max_particles) if max_particles > 0 else 100 # 避免除零
                
                if len(self.flame_particles) < max_particles and \
                    (current_time_ms - self.last_particle_emission_time) > emission_interval_ms:
                    new_particle = self._create_flame_particle()
                    if new_particle:
                        self.flame_particles.append(new_particle)
                        self.last_particle_emission_time = current_time_ms
        
        # --- 像素火焰粒子更新 (無論技能是否 active，只要有粒子就需要更新，直到它們消失) ---
        if self.flame_particles_enabled and self.flame_particles:
            # 注意：PongDuelEnv.step 中的 dt 是 time_scale，這裡的粒子更新應該基於真實時間差
            # 但由於技能的 update 是每幀調用，我們可以假設 dt 約等於 16ms (60FPS)
            # 如果需要更精確的基於時間的粒子運動，需要從外部傳入真實的 dt_ms
            # 為了簡化，這裡粒子的速度 vx_norm, vy_norm 可以理解為每幀的偏移量
            
            dt_frame_simulated_norm = self.env.time_scale # 使用環境的 time_scale 來調整粒子速度的應用

            particles_to_remove = []
            for particle in self.flame_particles:
                particle['lifetime_ms_remaining'] -= (1000/60) # 假設60FPS，每幀約16.67ms

                if particle['lifetime_ms_remaining'] <= 0:
                    particles_to_remove.append(particle)
                else:
                    # 更新位置
                    particle['x_norm'] += particle['vx_norm'] * dt_frame_simulated_norm
                    particle['y_norm'] += particle['vy_norm'] * dt_frame_simulated_norm

                    # 更新顏色和大小 (生命週期比例：1 -> 0)
                    life_ratio = particle['lifetime_ms_remaining'] / particle['initial_lifetime_ms']
                    life_ratio = max(0, min(1, life_ratio)) # 確保在 0-1 之間

                    # 簡單的兩段顏色插值 (從 start 到 mid，再從 mid 到 end)
                    color_start = self.pixel_flame_config.get("color_start_rgba", [255, 200, 0, 220])
                    color_mid = self.pixel_flame_config.get("color_mid_rgba", [255, 100, 0, 180])
                    color_end = self.pixel_flame_config.get("color_end_rgba", [139, 0, 0, 50])

                    current_rgba = [0,0,0,0]
                    if life_ratio > 0.5: # 從 start 到 mid
                        # 0.5 到 1.0 的 life_ratio 映射到 0 到 1 的插值因子 (interp_ratio)
                        interp_ratio = (life_ratio - 0.5) * 2 
                        for i in range(4):
                            current_rgba[i] = int(color_mid[i] + (color_start[i] - color_mid[i]) * interp_ratio)
                    else: # 從 mid 到 end
                        # 0 到 0.5 的 life_ratio 映射到 0 到 1 的插值因子 (interp_ratio)
                        interp_ratio = life_ratio * 2
                        for i in range(4):
                            current_rgba[i] = int(color_end[i] + (color_mid[i] - color_end[i]) * interp_ratio)
                    
                    particle['current_color_rgba'] = current_rgba

                    # 大小也可以隨生命週期變化 (例如，逐漸變小)
                    base_size = self.pixel_flame_config.get("particle_base_size_px", 3)
                    particle['current_size_px'] = max(1, int(base_size * (life_ratio * 0.5 + 0.5))) # 從 base_size 到 base_size*0.5

            for p_remove in particles_to_remove:
                self.flame_particles.remove(p_remove)
        elif not self.active and not self.flame_particles:
            # 如果技能未激活，且沒有粒子了，可以考慮停止頻繁的update檢查（如果有的話）
            pass

    # <<< 保留唯一的 update_ball_in_domain 方法 (第二個定義) >>>
    def update_ball_in_domain(self, current_ball_x, current_ball_y, current_ball_vx, current_ball_vy, current_spin,
                              dt, target_player_state, owner_player_state,
                              env_paddle_height_norm, env_ball_radius_norm, env_render_size):
        """
        在此技能啟用期間，由此方法控制球的行為。
        在入場動畫期間，球會震動、跳動和旋轉。動畫結束後，球會發射。
        返回: (new_ball_x, new_ball_y, new_ball_vx, new_ball_vy, new_spin, round_done, info)
        """
        new_ball_x, new_ball_y = current_ball_x, current_ball_y
        new_ball_vx, new_ball_vy = 0, 0 # 預設速度為0，除非是常規發射階段
        new_spin = current_spin
        round_done = False
        info = {'scorer': None, 'reason': None}

        time_now_ms = pygame.time.get_ticks()
        is_in_intro_anim = False
        anim_elapsed_time_ms = 0

        if self.is_in_activation_animation and self.activation_animation_enabled:
            anim_elapsed_time_ms = time_now_ms - self.activation_animation_start_time
            if anim_elapsed_time_ms < self.activation_animation_duration_ms:
                is_in_intro_anim = True
            else: # 動畫時間到，標記 is_in_activation_animation 為 False，以便下次不再進入此邏輯
                self.is_in_activation_animation = False
                if DEBUG_PURGATORY_SKILL:
                    print(f"[SKILL_DEBUG][{self.__class__.__name__}] ({self.owner.identifier}) Ball intro animation finished. Proceeding to launch.")


        if is_in_intro_anim and self.ball_anim_effect_enabled:
            # --- 入場動畫期間的球體特殊效果 ---
            base_x = self.ball_anim_center_x if self.ball_anim_hold_at_center else current_ball_x
            base_y = self.ball_anim_center_y if self.ball_anim_hold_at_center else current_ball_y

            # 1. 震動效果
            vib_x = random.uniform(-self.ball_anim_vibration_intensity, self.ball_anim_vibration_intensity)
            vib_y = random.uniform(-self.ball_anim_vibration_intensity, self.ball_anim_vibration_intensity)
            
            # 2. 跳動效果 (Y軸)
            # anim_elapsed_time_ms 已經是從動畫開始的時間
            jump_phase = (anim_elapsed_time_ms / 1000.0) * self.ball_anim_jump_frequency * 2 * math.pi
            jump_offset = math.sin(jump_phase) * self.ball_anim_jump_intensity
            
            new_ball_x = base_x + vib_x
            new_ball_y = base_y + vib_y + jump_offset
            
            # 限制在邊界內 (考慮球半徑)
            new_ball_x = np.clip(new_ball_x, env_ball_radius_norm, 1.0 - env_ball_radius_norm)
            new_ball_y = np.clip(new_ball_y, env_ball_radius_norm, 1.0 - env_ball_radius_norm)

            # 3. 旋轉效果 (視覺上的，不影響物理)
            # dt 是 time_scale，但旋轉速度應該基於真實時間。FPS約為60。
            # 每秒旋轉_dps度，所以每幀旋轉 _dps / 60 度。
            # 注意：這裡的 current_spin 是物理自旋，我們可能需要一個獨立的視覺自旋變數
            # 或者直接修改物理自旋值，但這可能會在動畫結束後影響球的飛行。
            # 為了簡化，我們假設 self.env.spin 是視覺和物理共用的，但動畫期間不應用馬格努斯力。
            # 或者，我們可以更新一個只用於渲染的自旋角度，
            # 但 PurgatoryDomainSkill 目前沒有直接的 render 方法來畫球。
            # Renderer.py 的 render 方法中 self.ball_angle 是累積的。
            # 這裡的 new_spin 可以是物理自旋，也可以是傳給 Renderer 的視覺參考。
            # 假設 current_spin 是從 env 來的，我們更新它。
            spin_increment_per_frame = (self.ball_anim_spin_speed_dps / 60.0) # 假設60FPS
            self.current_ball_animation_spin_angle = (self.current_ball_animation_spin_angle + spin_increment_per_frame) % 360
            new_spin = math.radians(self.current_ball_animation_spin_angle) # 如果 spin 是弧度
            # 或者如果 env.spin 就是角度: new_spin = self.current_ball_animation_spin_angle

            if DEBUG_PURGATORY_SKILL and random.random() < 0.1: # 降低打印頻率
                print(f"    Ball Anim: t={anim_elapsed_time_ms:.0f}ms, pos=({new_ball_x:.3f},{new_ball_y:.3f}), spin_angle_deg={self.current_ball_animation_spin_angle:.1f}")

            # 動畫期間不進行得分、碰撞等常規物理判斷
            # 更新軌跡，即使是原地抖動
            if hasattr(self.env, 'trail') and hasattr(self.env, 'max_trail_length'):
                self.env.trail.append((new_ball_x, new_ball_y))
                if len(self.env.trail) > self.env.max_trail_length:
                    self.env.trail.pop(0)
            
            return new_ball_x, new_ball_y, 0, 0, new_spin, False, info # 速度設為0，不結束回合

        else:
            # --- 入場動畫結束 或 未啟用球體動畫效果，執行常規的領域內球體運動 ---
            if owner_player_state == self.env.player1:
                target_y_direction = -1.0
            else:
                target_y_direction = 1.0

            base_speed = self.ball_base_speed_in_domain
            if target_y_direction < 0:
                base_random_angle = random.uniform(-math.pi * 5/6, -math.pi * 1/6)
            else:
                base_random_angle = random.uniform(math.pi * 1/6, math.pi * 5/6)
            
            additional_perturbation = random.uniform(-math.pi / 6, math.pi / 6) * self.ball_instability_factor
            final_angle = base_random_angle + additional_perturbation
            
            new_ball_vx_launch = base_speed * math.cos(final_angle)
            new_ball_vy_launch = base_speed * math.sin(final_angle)

            # 如果是剛從動畫結束轉到發射，使用計算出的發射速度
            # 否則，球應繼續之前的速度（如果已經在飛行中）
            # 這裡的邏輯假設每次調用 update_ball_in_domain 且不在動畫中時，都是重新計算一個隨機方向和速度
            # 這意味著一旦發射，球會持續以隨機方式改變方向和速度，直到撞擊或得分
            new_ball_vx = new_ball_vx_launch
            new_ball_vy = new_ball_vy_launch


            if DEBUG_PURGATORY_SKILL and random.random() < 0.02:
                 print(f"[SKILL_DEBUG][{self.__class__.__name__}] Domain Ball Launch/Update: Speed={base_speed:.3f}, Angle={math.degrees(final_angle):.1f}, VX={new_ball_vx:.3f}, VY={new_ball_vy:.3f}")

            new_ball_x += new_ball_vx * dt 
            new_ball_y += new_ball_vy * dt

            # 牆壁碰撞
            if new_ball_x - env_ball_radius_norm <= 0:
                new_ball_x = env_ball_radius_norm
                new_ball_vx *= -0.9 
                if self.sound_ball_event: self.sound_ball_event.play()
            elif new_ball_x + env_ball_radius_norm >= 1.0:
                new_ball_x = 1.0 - env_ball_radius_norm
                new_ball_vx *= -0.9
                if self.sound_ball_event: self.sound_ball_event.play()
            
            new_ball_y = np.clip(new_ball_y, env_ball_radius_norm, 1.0 - env_ball_radius_norm)

            # 得分判斷
            scored_this_step = False
            if owner_player_state == self.env.player1: 
                if new_ball_y - env_ball_radius_norm <= 0.0: 
                    scored_this_step = True
                    info['scorer'] = self.owner.identifier
            else: 
                if new_ball_y + env_ball_radius_norm >= 1.0: 
                    scored_this_step = True
                    info['scorer'] = self.owner.identifier

            if scored_this_step:
                if target_player_state.lives > 0 : target_player_state.lives -= 1
                round_done = True
                info['reason'] = f"{self.owner.identifier}_purgatory_scored"
                self.deactivate(scored_by_skill=True) 
                if self.sound_ball_event: self.sound_ball_event.play()

            owner_scored_this_step = False # 判斷是否打到自己龍門
            if not scored_this_step: 
                if owner_player_state == self.env.player1:
                    if new_ball_y + env_ball_radius_norm >= 1.0:
                        owner_scored_this_step = True
                else: 
                    if new_ball_y - env_ball_radius_norm <= 0.0:
                        owner_scored_this_step = True
                
                if owner_scored_this_step:
                    if owner_player_state.lives > 0: owner_player_state.lives -=1 
                    round_done = True
                    info['scorer'] = target_player_state.identifier 
                    info['reason'] = f"{target_player_state.identifier}_purgatory_own_goal"
                    self.deactivate(own_goal_by_skill=True)
                    if self.sound_ball_event: self.sound_ball_event.play()

            # 板子碰撞 (常規階段)
            if not round_done:
                target_paddle_y_surface_contact_min, target_paddle_y_surface_contact_max = 0, 0
                is_target_top_paddle = False

                if target_player_state == self.env.opponent:
                    target_paddle_y_surface_contact_min = 0
                    target_paddle_y_surface_contact_max = env_paddle_height_norm
                    is_target_top_paddle = True
                else:
                    target_paddle_y_surface_contact_min = 1.0 - env_paddle_height_norm
                    target_paddle_y_surface_contact_max = 1.0

                paddle_actual_half_width_norm = target_player_state.paddle_width_normalized / 2.0
                target_paddle_x_min = target_player_state.x - paddle_actual_half_width_norm
                target_paddle_x_max = target_player_state.x + paddle_actual_half_width_norm

                ball_hit_paddle = False
                if is_target_top_paddle:
                    if new_ball_y - env_ball_radius_norm <= target_paddle_y_surface_contact_max and \
                       new_ball_y + env_ball_radius_norm >= target_paddle_y_surface_contact_min:
                        if new_ball_x - env_ball_radius_norm <= target_paddle_x_max and \
                           new_ball_x + env_ball_radius_norm >= target_paddle_x_min:
                            ball_hit_paddle = True
                            new_ball_y = target_paddle_y_surface_contact_max + env_ball_radius_norm
                else:
                    if new_ball_y + env_ball_radius_norm >= target_paddle_y_surface_contact_min and \
                       new_ball_y - env_ball_radius_norm <= target_paddle_y_surface_contact_max:
                        if new_ball_x - env_ball_radius_norm <= target_paddle_x_max and \
                           new_ball_x + env_ball_radius_norm >= target_paddle_x_min:
                            ball_hit_paddle = True
                            new_ball_y = target_paddle_y_surface_contact_min - env_ball_radius_norm
                
                if ball_hit_paddle:
                    new_ball_vy *= -1.0 
                    hit_offset_from_paddle_center = (new_ball_x - target_player_state.x) / (paddle_actual_half_width_norm + 1e-6)
                    random_vx_factor = random.uniform(0.5, 1.5)
                    new_ball_vx += hit_offset_from_paddle_center * base_speed * 0.7 * random_vx_factor
                    new_ball_vx = np.clip(new_ball_vx, -base_speed * 1.8, base_speed * 1.8) 
                    new_ball_vy *= (1 + self.ball_instability_factor * random.uniform(0.1, 0.3))
                    if self.sound_ball_event: self.sound_ball_event.play()

            if hasattr(self.env, 'trail') and hasattr(self.env, 'max_trail_length'):
                self.env.trail.append((new_ball_x, new_ball_y))
                if len(self.env.trail) > self.env.max_trail_length:
                    self.env.trail.pop(0)
            
            return new_ball_x, new_ball_y, new_ball_vx, new_ball_vy, new_spin, round_done, info
        
    def deactivate(self, *args, **kwargs):
        # 檢查是否有額外的參數指示停用原因
        # reason = kwargs.get('reason', 'normal_deactivation') 
        # if DEBUG_PURGATORY_SKILL:
        #     print(f"[SKILL_DEBUG][{self.__class__.__name__}] ({self.owner.identifier}) Deactivating. Reason: {reason}, Args: {args}")

        if not self.active: # 如果本來就不是 active，提早返回，避免重複設定冷卻
            # 確保如果技能曾經啟用過但現在不是active，冷卻時間也被正確設定
            if self.activated_time != 0 and self.cooldown_start_time == 0 :
                 self.cooldown_start_time = pygame.time.get_ticks()
            return

        was_truly_active = self.active # 記錄是否是從 active 狀態停用
        self.active = False
        
        if DEBUG_PURGATORY_SKILL:
            print(f"[SKILL_DEBUG][{self.__class__.__name__}] ({self.owner.identifier}) Deactivated. Was truly active: {was_truly_active}")

        if was_truly_active:
            self.cooldown_start_time = pygame.time.get_ticks()
            if DEBUG_PURGATORY_SKILL:
                print(f"    Cooldown started at: {self.cooldown_start_time}")

        if self.sound_deactivate:
            self.sound_deactivate.play()

        if self.domain_loop_channel:
            self.domain_loop_channel.stop()
            self.domain_loop_channel = None
            if DEBUG_PURGATORY_SKILL:
                print("    Domain loop sound channel stopped.")
        
        # <<< 新增開始：清除火焰粒子 >>>
        if self.flame_particles_enabled:
            self.flame_particles.clear()
            if DEBUG_PURGATORY_SKILL:
                print(f"    [SKILL_DEBUG][{self.__class__.__name__}] ({self.owner.identifier}) Cleared flame particles on deactivate.")
        # <<< 新增結束：清除火焰粒子 >>>
        
        # 恢復球體視覺 (如果技能改變了它)
        # self.env.set_ball_visual_override(skill_identifier="purgatory_domain_ball", active=False, owner_identifier=self.owner.identifier)
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

    def get_visual_params(self):
        """
        返回一個包含此技能當前視覺效果所需參數的字典。
        如果技能沒有額外的視覺效果，則返回空字典。
        這些參數將由 Renderer 用來繪製效果。
        """
        # 基本參數，包含技能類型和基礎效果是否啟用
        visual_params = {
            "type": "purgatory_domain",
            "active_effects": self.active or bool(self.flame_particles), # 如果技能本身啟用或還有火焰粒子，則認為有效果
            "domain_filter_color_rgba": self.domain_filter_color_rgba,
            "ball_aura_color_rgba": self.ball_aura_color_rgba,
            "pixel_flames_enabled": self.flame_particles_enabled,
            "pixel_flames_data": {
                "config": self.pixel_flame_config, # 傳遞火焰效果的靜態配置
                "particles": list(self.flame_particles) # 傳遞當前所有活動粒子的數據副本
            },
            "activation_animation_props": { # 預先準備好動畫屬性字典
                "is_playing": False,
                "elapsed_ms": 0,
                "duration_ms": 0,
                "filter_pulse": None,
                "vignette_effect": None
            }
        }

        # 處理入場動畫
        if self.activation_animation_enabled and self.is_in_activation_animation:
            current_time_ms = pygame.time.get_ticks()
            elapsed_anim_time = current_time_ms - self.activation_animation_start_time
            is_still_playing_anim = elapsed_anim_time < self.activation_animation_duration_ms

            activation_props = visual_params["activation_animation_props"] # 獲取預備好的字典引用
            activation_props["is_playing"] = is_still_playing_anim
            activation_props["elapsed_ms"] = elapsed_anim_time
            activation_props["duration_ms"] = self.activation_animation_duration_ms

            if is_still_playing_anim:
                # --- 計算濾鏡脈衝效果 ---
                pulse_config = self.activation_animation_config.get("filter_pulse", {})
                if pulse_config.get("enabled", False):
                    base_filter_color_cfg = self.domain_filter_color_rgba # 基礎顏色從技能主設定取
                    base_alpha = base_filter_color_cfg[3] if len(base_filter_color_cfg) == 4 else 70
                    
                    frequency_hz = pulse_config.get("frequency_hz", 2.0)
                    alpha_min_factor = pulse_config.get("alpha_min_factor", 0.5)
                    alpha_max_factor = pulse_config.get("alpha_max_factor", 1.0)

                    # 正弦波計算 alpha
                    # (elapsed_anim_time / 1000.0) 是秒
                    # sin_wave = math.sin(2 * math.pi * frequency_hz * (elapsed_anim_time / 1000.0))
                    # 為了從0開始並達到峰值，可以使用 (sin(t-pi/2)+1)/2 這樣的形式，或者直接調整相位
                    # 這裡使用一個簡單的循環往復 sin，範圍從 -1 到 1
                    oscillation = math.sin(elapsed_anim_time / (1000.0 / frequency_hz / (2 * math.pi)))
                    # 將 -1 到 1 映射到 0 到 1
                    normalized_oscillation = (oscillation + 1) / 2.0
                    # 再將 0 到 1 映射到 alpha_min_factor 到 alpha_max_factor
                    current_alpha_factor = alpha_min_factor + (alpha_max_factor - alpha_min_factor) * normalized_oscillation
                    current_alpha = int(base_alpha * current_alpha_factor)
                    current_alpha = max(0, min(255, current_alpha)) # 確保在有效範圍

                    activation_props["filter_pulse"] = {
                        "enabled": True,
                        "current_alpha": current_alpha,
                        "base_color_rgb": base_filter_color_cfg[:3] # 傳遞基礎 RGB 給渲染器
                    }
                else:
                    activation_props["filter_pulse"] = {"enabled": False}

                # --- 計算邊緣暈影效果 ---
                vignette_config = self.activation_animation_config.get("vignette_effect", {})
                if vignette_config.get("enabled", False):
                    anim_progress_ratio = min(1.0, elapsed_anim_time / self.activation_animation_duration_ms if self.activation_animation_duration_ms > 0 else 1.0)
                    
                    color_start_rgba = tuple(vignette_config.get("color_start_rgba", [0,0,0,0]))
                    color_end_rgba = tuple(vignette_config.get("color_end_rgba", [0,0,0,0]))
                    
                    thickness_start_factor = vignette_config.get("thickness_start_factor", 0.0)
                    thickness_peak_factor = vignette_config.get("thickness_peak_factor", 0.1)
                    thickness_end_factor = vignette_config.get("thickness_end_factor", 0.05)
                    peak_time_ratio = vignette_config.get("peak_time_ratio", 0.5) # 在動畫總時長的哪個比例達到峰值

                    current_vignette_color_rgba = list(color_start_rgba)
                    current_vignette_thickness_factor = 0.0

                    if anim_progress_ratio <= peak_time_ratio:
                        # 從 start 到 peak
                        ratio_to_peak = anim_progress_ratio / peak_time_ratio if peak_time_ratio > 0 else 1.0
                        for i in range(4):
                            current_vignette_color_rgba[i] = int(color_start_rgba[i] + (color_end_rgba[i] - color_start_rgba[i]) * ratio_to_peak) # 線性插值到最終顏色的一部分
                        current_vignette_thickness_factor = thickness_start_factor + (thickness_peak_factor - thickness_start_factor) * ratio_to_peak
                    else:
                        # 從 peak 到 end
                        ratio_from_peak_to_end = (anim_progress_ratio - peak_time_ratio) / (1.0 - peak_time_ratio) if (1.0 - peak_time_ratio) > 0 else 1.0
                        # 顏色保持在 peak_time_ratio 時計算出的顏色，或者繼續插值到 color_end_rgba
                        # 為了簡化，假設顏色在 peak_time_ratio 後就固定為 color_end_rgba (或者可以再插值)
                        # 這裡我們讓顏色從 start -> end 線性變化，厚度是 start -> peak -> end
                        for i in range(4): # 顏色全程線性插值
                            current_vignette_color_rgba[i] = int(color_start_rgba[i] + (color_end_rgba[i] - color_start_rgba[i]) * anim_progress_ratio)

                        current_vignette_thickness_factor = thickness_peak_factor + (thickness_end_factor - thickness_peak_factor) * ratio_from_peak_to_end
                    
                    current_vignette_color_rgba = tuple(max(0, min(255, int(c))) for c in current_vignette_color_rgba)


                    activation_props["vignette_effect"] = {
                        "enabled": True,
                        "current_color_rgba": current_vignette_color_rgba,
                        "current_thickness_factor": current_vignette_thickness_factor
                    }
                else:
                    activation_props["vignette_effect"] = {"enabled": False}
            else: # 動畫時間已過，但 is_in_activation_animation 仍然為 True (直到技能停用)
                activation_props["filter_pulse"] = {"enabled": False, "current_alpha": 0} # 確保沒有殘留
                activation_props["vignette_effect"] = {"enabled": False, "current_thickness_factor": 0}

        # 如果技能已不活躍且沒有火焰粒子了 (這個判斷其實和 visual_params["active_effects"] 重複，可以簡化)
        if not self.active and not self.flame_particles:
             visual_params["active_effects"] = False

        if DEBUG_PURGATORY_SKILL and visual_params["activation_animation_props"]["is_playing"]:
            print(f"[SKILL_DEBUG][Purgatory.get_visual_params] Anim Playing: Yes, Elapsed: {visual_params['activation_animation_props']['elapsed_ms']:.0f}ms")
            print(f"    Filter Pulse: {visual_params['activation_animation_props'].get('filter_pulse')}")
            print(f"    Vignette: {visual_params['activation_animation_props'].get('vignette_effect')}")
            # pass

        return visual_params

    def render(self, surface):
        pass