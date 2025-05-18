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
        self.flame_particles = [] # 用於存儲粒子對象或字典的列表
        self.last_particle_emission_time = 0 # <<< 新增：用於控制粒子發射頻率

        if DEBUG_PURGATORY_SKILL and self.flame_particles_enabled:
            print(f"[SKILL_DEBUG][{self.__class__.__name__}] ({self.owner.identifier}) Pixel Flame Effect enabled with config: {self.pixel_flame_config}")
        
        self.active = False

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
        self.flame_particles.clear() # <<< 新增：清除舊粒子
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
        if DEBUG_PURGATORY_SKILL: print(f"[SKILL_DEBUG][{self.__class__.__name__}] ({self.owner.identifier}) Activated!")

        if self.sound_activate:
            self.sound_activate.play()
        if self.sound_domain_loop:
            self.domain_loop_channel = self.sound_domain_loop.play(loops=-1)

        # 通知環境球體視覺可能需要改變 (如果領域本身改變球的視覺)
        # self.env.set_ball_visual_override(skill_identifier="purgatory_domain_ball", active=True, owner_identifier=self.owner.identifier)
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
        修改後：球將隨機往一個大致朝向對手的方向射出。
        返回: (new_ball_x, new_ball_y, new_ball_vx, new_ball_vy, new_spin, round_done, info)
        """
        new_ball_x, new_ball_y = current_ball_x, current_ball_y
        new_ball_vx, new_ball_vy = current_ball_vx, current_ball_vy
        new_spin = current_spin # 在此技能中，我們可能不改變 spin
        round_done = False
        info = {'scorer': None, 'reason': None}

        # === 1. 確定基礎Y軸移動方向 ===
        if owner_player_state == self.env.player1: # 技能擁有者在下方 (P1)
            target_y_direction = -1.0 # 球應主要向上移動 (Y值減小)
            # target_goal_line_y = 0.0  # 對手底線
            # owner_goal_line_y = 1.0   # 自己底線
        else: # 技能擁有者在上方 (Opponent/P2)
            target_y_direction = 1.0 # 球應主要向下移動 (Y值增大)
            # target_goal_line_y = 1.0
            # owner_goal_line_y = 0.0

        # === 2. 更新球的速度 (隨機方向) ===
        base_speed = self.ball_base_speed_in_domain

        # A. 生成一個基礎的隨機角度，使其大致朝向 target_y_direction
        #    例如，如果 target_y_direction 是 -1 (向上)，角度範圍可以是 -pi/2 +/- pi/3 (即 -150度 到 -30度)
        #    如果 target_y_direction 是  1 (向下)，角度範圍可以是  pi/2 +/- pi/3 (即  30度 到 150度)
        if target_y_direction < 0: # 向上
            base_random_angle = random.uniform(-math.pi * 5/6, -math.pi * 1/6) # -150 to -30 degrees
        else: # 向下
            base_random_angle = random.uniform(math.pi * 1/6, math.pi * 5/6)   #  30 to 150 degrees

        # B. 疊加 ball_instability_factor 帶來的額外隨機擾動
        #    擾動範圍可以小一些，例如 +/- pi/6 (30度) 乘以因子
        additional_perturbation = random.uniform(-math.pi / 6, math.pi / 6) * self.ball_instability_factor
        final_angle = base_random_angle + additional_perturbation
        
        new_ball_vx = base_speed * math.cos(final_angle)
        new_ball_vy = base_speed * math.sin(final_angle)

        if DEBUG_PURGATORY_SKILL and random.random() < 0.02: #降低打印频率
             print(f"[SKILL_DEBUG][{self.__class__.__name__}] Domain Ball Update (Randomized): Speed={base_speed:.3f}, Angle={math.degrees(final_angle):.1f}, VX={new_ball_vx:.3f}, VY={new_ball_vy:.3f}")

        # === 3. 更新球的位置 ===
        new_ball_x += new_ball_vx * dt 
        new_ball_y += new_ball_vy * dt

        # === 4. 處理邊界碰撞 (牆壁) ===
        if new_ball_x - env_ball_radius_norm <= 0:
            new_ball_x = env_ball_radius_norm
            new_ball_vx *= -0.9 
            if self.sound_ball_event: self.sound_ball_event.play()
            if DEBUG_PURGATORY_SKILL: print(f"[SKILL_DEBUG][{self.__class__.__name__}] Domain: Ball hit side wall (left).")
        elif new_ball_x + env_ball_radius_norm >= 1.0:
            new_ball_x = 1.0 - env_ball_radius_norm
            new_ball_vx *= -0.9
            if self.sound_ball_event: self.sound_ball_event.play()
            if DEBUG_PURGATORY_SKILL: print(f"[SKILL_DEBUG][{self.__class__.__name__}] Domain: Ball hit side wall (right).")
        
        new_ball_y = np.clip(new_ball_y, 0.0 + env_ball_radius_norm, 1.0 - env_ball_radius_norm)

        # === 5. 處理得分 ===
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
            if DEBUG_PURGATORY_SKILL:
                print(f"[SKILL_DEBUG][{self.__class__.__name__}] ({self.owner.identifier}) SCORED in domain against {target_player_state.identifier}!")
            if target_player_state.lives > 0 : target_player_state.lives -= 1
            round_done = True
            info['reason'] = f"{self.owner.identifier}_purgatory_scored"
            self.deactivate(scored_by_skill=True) 
            if self.sound_ball_event: self.sound_ball_event.play()

        owner_scored_this_step = False
        if not scored_this_step: 
            if owner_player_state == self.env.player1:
                if new_ball_y + env_ball_radius_norm >= 1.0:
                    owner_scored_this_step = True
            else: 
                if new_ball_y - env_ball_radius_norm <= 0.0:
                    owner_scored_this_step = True
            
            if owner_scored_this_step:
                if DEBUG_PURGATORY_SKILL:
                    print(f"[SKILL_DEBUG][{self.__class__.__name__}] ({self.owner.identifier}) Ball hit OWN GOAL LINE in domain!")
                if owner_player_state.lives > 0: owner_player_state.lives -=1 
                round_done = True
                info['scorer'] = target_player_state.identifier 
                info['reason'] = f"{target_player_state.identifier}_purgatory_own_goal"
                self.deactivate(own_goal_by_skill=True)
                if self.sound_ball_event: self.sound_ball_event.play()

        # === 6. 處理與板子的碰撞 ===
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
            # 精確的碰撞檢測，考慮球的半徑
            if is_target_top_paddle: # 目標是頂部板子 (通常是對手)
                # 球的下邊緣接觸到板子的下邊緣 (paddle_y + paddle_h)，且球的中心 Y 在板子 Y 範圍內或剛穿過
                if new_ball_y - env_ball_radius_norm <= target_paddle_y_surface_contact_max and \
                   new_ball_y + env_ball_radius_norm >= target_paddle_y_surface_contact_min: # Y軸重疊
                    if new_ball_x - env_ball_radius_norm <= target_paddle_x_max and \
                       new_ball_x + env_ball_radius_norm >= target_paddle_x_min: # X軸重疊
                        ball_hit_paddle = True
                        new_ball_y = target_paddle_y_surface_contact_max + env_ball_radius_norm # 移出板子
            else: # 目標是底部板子 (通常是玩家自己)
                if new_ball_y + env_ball_radius_norm >= target_paddle_y_surface_contact_min and \
                   new_ball_y - env_ball_radius_norm <= target_paddle_y_surface_contact_max: # Y軸重疊
                    if new_ball_x - env_ball_radius_norm <= target_paddle_x_max and \
                       new_ball_x + env_ball_radius_norm >= target_paddle_x_min: # X軸重疊
                        ball_hit_paddle = True
                        new_ball_y = target_paddle_y_surface_contact_min - env_ball_radius_norm # 移出板子
            
            if ball_hit_paddle:
                if DEBUG_PURGATORY_SKILL:
                    print(f"[SKILL_DEBUG][{self.__class__.__name__}] Domain: Ball hit TARGET PADDLE ({target_player_state.identifier}).")
                
                # 板子擊球後，球以更不可預測的方式反彈
                # Y方向基本反彈
                new_ball_vy *= -1.0 
                
                # X方向速度受擊球點影響，並增加隨機性
                hit_offset_from_paddle_center = (new_ball_x - target_player_state.x) / (paddle_actual_half_width_norm + 1e-6) # Normalize to -1 to 1
                random_vx_factor = random.uniform(0.5, 1.5) # 隨機的X速度因子
                new_ball_vx += hit_offset_from_paddle_center * base_speed * 0.7 * random_vx_factor # 0.7是可調基礎影響
                
                # 限制最大X速度，但允許一定的隨機變化
                new_ball_vx = np.clip(new_ball_vx, -base_speed * 1.8, base_speed * 1.8) 
                new_ball_vy *= (1 + self.ball_instability_factor * random.uniform(0.1, 0.3)) # Y速度也增加不穩定性

                if self.sound_ball_event: self.sound_ball_event.play()

        # === 7. 更新環境中的球體軌跡 ===
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
        if not self.active: # 並且可以加上 and not self.flame_particles 如果希望殘留粒子消失後才算完全 false
            return {
                "type": "purgatory_domain",
                "active_effects": False,
                "pixel_flames_enabled": False, # 明確告知不啟用火焰
                "pixel_flames_data": {"config": self.pixel_flame_config, "particles": []} # 提供空數據結構
            }

        visual_params = {
            "type": "purgatory_domain",
            "active_effects": True,
            "domain_filter_color_rgba": self.domain_filter_color_rgba,
            "ball_aura_color_rgba": self.ball_aura_color_rgba,
            "pixel_flames_enabled": self.flame_particles_enabled, # 告知渲染器是否啟用
            "pixel_flames_data": { # 傳遞粒子效果的靜態配置和動態粒子列表
                "config": self.pixel_flame_config, # 傳遞火焰效果的靜態配置
                "particles": self.flame_particles # 傳遞當前所有活動粒子的數據
            }
        }
        # 如果技能未激活，但仍有一些殘留效果（例如火焰熄滅過程），這裡可以調整 active_effects
        # 但對於像素火焰，通常是技能激活時才有
        if not self.active and not self.flame_particles: # 如果技能已不活動且沒有粒子了
             visual_params["active_effects"] = False # 可以考慮更精細的控制
        
        return visual_params

    def render(self, surface):
        pass