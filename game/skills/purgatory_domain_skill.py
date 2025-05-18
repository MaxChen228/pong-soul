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

        self.active = False
        self.activated_time = 0
        self.cooldown_start_time = 0

        if DEBUG_PURGATORY_SKILL:
            print(f"[SKILL_DEBUG][{self.__class__.__name__}] ({self.owner.identifier}) Initialized. Duration: {self.duration_ms}ms, Cooldown: {self.cooldown_ms}ms")

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
        主要負責檢查技能是否因為持續時間結束而需要停用。
        球體的具體物理行為更新是在 PongDuelEnv.step() 中，
        當檢測到此技能 active 且 overrides_ball_physics=True 時，
        透過呼叫 self.update_ball_in_domain() 來實現的。
        """
        if not self.active:
            return

        current_time = pygame.time.get_ticks()
        if (current_time - self.activated_time) >= self.duration_ms:
            if DEBUG_PURGATORY_SKILL:
                print(f"[SKILL_DEBUG][{self.__class__.__name__}] ({self.owner.identifier}) Duration expired. Deactivating from update().")
            self.deactivate(duration_expired=True) # 傳遞一個原因以供除錯

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
        if not self.active:
            return {"type": "purgatory_domain", "active_effects": False}

        return {
            "type": "purgatory_domain",
            "active_effects": True,
            "domain_filter_color_rgba": self.domain_filter_color_rgba,
            "ball_aura_color_rgba": self.ball_aura_color_rgba,
        }

    def render(self, surface):
        pass