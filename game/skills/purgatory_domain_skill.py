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
            # 技能內部備用預設值 (僅在 YAML 完全沒有此技能條目時使用)
            cfg = {
                "duration_ms": 7000, "cooldown_ms": 15000, "bar_color": [70, 0, 100],
                "ball_instability_factor": 0.1, "ball_base_speed_in_domain": 0.03,
                "ball_seek_target_strength": 0.0, "opponent_paddle_slowdown_factor": 1.0,
                "domain_filter_color_rgba": [30, 0, 50, 100], "ball_aura_color_rgba": [120, 50, 150, 200],
                "sound_activate": None, "sound_domain_loop": None, "sound_ball_event": None, "sound_deactivate": None,
            }

        self.duration_ms = int(cfg.get("duration_ms", 7000))
        self.cooldown_ms = int(cfg.get("cooldown_ms", 15000))
        # 技能特有參數
        self.ball_instability_factor = float(cfg.get("ball_instability_factor", 0.1))
        self.ball_base_speed_in_domain = float(cfg.get("ball_base_speed_in_domain", 0.03))
        self.ball_seek_target_strength = float(cfg.get("ball_seek_target_strength", 0.0))
        self.opponent_paddle_slowdown_factor = float(cfg.get("opponent_paddle_slowdown_factor", 1.0))

        # 視覺和音效參數
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
        return True # 此技能將覆寫球體物理

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
            self.domain_loop_channel = self.sound_domain_loop.play(loops=-1) # 無限循環播放

        # 通知環境球體視覺可能需要改變 (如果領域本身改變球的視覺)
        # 或者由 Renderer 根據 get_visual_params() 決定
        # self.env.set_ball_visual_override(skill_identifier="purgatory_domain_ball", active=True, owner_identifier=self.owner.identifier)

        return True

    def deactivate(self, *args, **kwargs):
        if not self.active:
            # Fix: Ensure cooldown_start_time is set even if deactivated while not truly active (e.g. by game reset)
            if self.cooldown_start_time == 0 and self.activated_time != 0 : # only set if it was activated at least once and not set
                 self.cooldown_start_time = pygame.time.get_ticks()
            return

        was_truly_active = self.active
        self.active = False
        if DEBUG_PURGATORY_SKILL: print(f"[SKILL_DEBUG][{self.__class__.__name__}] ({self.owner.identifier}) Deactivated.")

        if was_truly_active: # 只有當是從 active 狀態停用時才開始冷卻
            self.cooldown_start_time = pygame.time.get_ticks()

        if self.sound_deactivate:
            self.sound_deactivate.play()
        if self.domain_loop_channel:
            self.domain_loop_channel.stop()
            self.domain_loop_channel = None

        # 恢復球體視覺
        # self.env.set_ball_visual_override(skill_identifier="purgatory_domain_ball", active=False, owner_identifier=self.owner.identifier)


    def update_ball_in_domain(self, current_ball_x, current_ball_y, current_ball_vx, current_ball_vy, current_spin,
                              dt, target_player_state, owner_player_state,
                              env_paddle_height_norm, env_ball_radius_norm, env_render_size):
        """
        在此技能啟用期間，由此方法控制球的行為。
        核心邏輯：不穩定的軌跡，帶有攻擊傾向。
        """
        new_ball_x, new_ball_y = current_ball_x, current_ball_y
        new_ball_vx, new_ball_vy = current_ball_vx, current_ball_vy # 初始繼承當前速度，但很快會被覆蓋
        new_spin = 0 # 領域內可以簡化，不處理複雜旋轉，或賦予特殊旋轉
        round_done = False
        info = {'scorer': None, 'reason': None}

        # === 1. 確定基礎Y軸移動方向和目標線 ===
        if owner_player_state == self.env.player1: # 技能擁有者在下方 (P1)
            target_y_general_direction = -1.0 # 球應向上移動 (Y值減小)
            target_goal_line_y = 0.0  # 對手底線 (球心接觸點)
            owner_goal_line_y = 1.0   # 自己底線 (球心接觸點)
        else: # 技能擁有者在上方 (Opponent/P2)
            target_y_general_direction = 1.0 # 球應向下移動 (Y值增大)
            target_goal_line_y = 1.0
            owner_goal_line_y = 0.0

        # === 2. 計算球的新速度和攻擊目標 ===
        base_speed = self.ball_base_speed_in_domain

        # A. 製造軌跡不穩定性 (隨機角度偏移)
        #    每次更新都可能輕微改變方向
        random_angle_perturbation = random.uniform(-math.pi / 6, math.pi / 6) * self.ball_instability_factor

        # B. "攻擊性" - 嘗試朝向對手板子目前的空檔或邊緣
        #    這裡的實現可以多樣化，以下是一個簡單的例子：
        #    - 隨機選擇是瞄準對手板子的左邊緣、右邊緣還是中心。
        #    - 或者更智能地，判斷對手板子移動方向，攻擊其反方向。
        
        # 簡單策略：隨機選擇一個目標點 X (可以是板子中心，或板子兩側的空檔)
        target_paddle_x = target_player_state.x
        target_paddle_half_width = target_player_state.paddle_width_normalized / 2.0
        
        # 引入 "ball_seek_target_strength" (如果 > 0)
        # 這個參數現在控制球是否會瞄準對手板子後的某個區域，而不僅僅是板子本身
        aim_offset_x = 0
        if self.ball_seek_target_strength > 0:
            # 隨機一個偏離對手板子中心的 X 偏移量，強度受 ball_seek_target_strength 影響
            # 讓球嘗試打向對手更難接到的地方
            aim_offset_x = random.uniform(-0.3, 0.3) * self.ball_seek_target_strength # 0.3 是一個可調的基礎偏移範圍

        target_ball_x_destination = np.clip(target_paddle_x + aim_offset_x, 0.0 + env_ball_radius_norm, 1.0 - env_ball_radius_norm)

        # C. 計算指向目標點 (target_ball_x_destination, target_goal_line_y) 的角度
        #    注意：這裡的 target_goal_line_y 只是 Y 軸的終點線，實際角度計算時，
        #    我們更關心 Y 方向的總體趨勢。
        #    我們使用 target_y_general_direction 來確定主要 Y 分量。
        
        vector_x_to_target = target_ball_x_destination - new_ball_x
        vector_y_to_target = (target_goal_line_y - new_ball_y) # 這是到目標底線的 Y 向量
        
        # 如果球離目標底線很近，Y向量會很小，可能導致速度主要在X軸
        # 我們需要確保Y軸有足夠的推進力
        # 可以將 Y 分量設定為一個固定比例，或者基於與 target_y_general_direction 的關係
        
        # 基礎角度指向 (target_ball_x_destination, 假想的對手Y位置)
        # 我們簡化：假設 Y 方向速度分量固定，X 方向根據目標調整
        
        desired_vy = base_speed * target_y_general_direction * 0.7 # Y方向佔基礎速度的70% (可調)
        remaining_speed_for_vx_sq = base_speed**2 - desired_vy**2
        
        desired_vx_magnitude = 0
        if remaining_speed_for_vx_sq > 0:
            desired_vx_magnitude = math.sqrt(remaining_speed_for_vx_sq)
        
        if abs(vector_x_to_target) > 1e-6: # 避免除以零
            desired_vx = math.copysign(desired_vx_magnitude, vector_x_to_target)
        else:
            desired_vx = 0

        # 疊加隨機擾動到計算出的速度向量
        current_angle = math.atan2(desired_vy, desired_vx)
        perturbed_angle = current_angle + random_angle_perturbation
        
        new_ball_vx = base_speed * math.cos(perturbed_angle)
        new_ball_vy = base_speed * math.sin(perturbed_angle)

        # 強制Y方向與 target_y_general_direction 一致，避免隨機擾動完全反向
        if (target_y_general_direction < 0 and new_ball_vy > 0) or \
           (target_y_general_direction > 0 and new_ball_vy < 0):
            new_ball_vy *= -1 # 反轉錯誤的Y方向

        if DEBUG_PURGATORY_SKILL and random.random() < 0.05: #降低打印频率
             print(f"[SKILL_DEBUG][{self.__class__.__name__}] Domain Ball Update: TargetX={target_ball_x_destination:.2f}, Speed={base_speed:.3f}, Angle={math.degrees(perturbed_angle):.1f}, VX={new_ball_vx:.3f}, VY={new_ball_vy:.3f}")

        # === 3. 更新球的位置 ===
        new_ball_x += new_ball_vx * dt
        new_ball_y += new_ball_vy * dt
        new_ball_x = np.clip(new_ball_x, env_ball_radius_norm, 1.0 - env_ball_radius_norm) # 預防穿牆
        new_ball_y = np.clip(new_ball_y, env_ball_radius_norm, 1.0 - env_ball_radius_norm) # 預防穿牆

        # === 4. 處理邊界碰撞 (牆壁) ===
        if new_ball_x == env_ball_radius_norm or new_ball_x == 1.0 - env_ball_radius_norm:
            new_ball_vx *= -0.9 # 撞牆後速度略微衰減並反彈
            if self.sound_ball_event: self.sound_ball_event.play()
            if DEBUG_PURGATORY_SKILL: print(f"[SKILL_DEBUG][{self.__class__.__name__}] Domain: Ball hit side wall.")


        # === 5. 處理得分 ===
        scored_this_step = False
        if owner_player_state == self.env.player1: # 技能擁有者 P1, 目標是上方
            if new_ball_y - env_ball_radius_norm <= target_goal_line_y:
                scored_this_step = True
                info['scorer'] = self.owner.identifier
        else: # 技能擁有者 Opponent, 目標是下方
            if new_ball_y + env_ball_radius_norm >= target_goal_line_y:
                scored_this_step = True
                info['scorer'] = self.owner.identifier

        if scored_this_step:
            if DEBUG_PURGATORY_SKILL:
                print(f"[SKILL_DEBUG][{self.__class__.__name__}] ({self.owner.identifier}) SCORED in domain against {target_player_state.identifier}!")
            if target_player_state.lives > 0 : target_player_state.lives -= 1
            round_done = True
            info['reason'] = f"{self.owner.identifier}_purgatory_scored"
            self.deactivate(scored_by_skill=True) # 技能導致得分，技能結束
            # 球體事件音效（或專用得分音效）
            if self.sound_ball_event: self.sound_ball_event.play()
            # 球體狀態在得分後通常由環境的 reset_ball_after_score 處理，此處不再特殊設定
            # 但由於是技能覆寫，我們需要確保返回的球體位置和速度是合理的“最終”狀態
            # 或者，我們讓 PongDuelEnv 在 round_done 後處理球的重置
            # 此處，我們僅標記回合結束， PongDuelEnv.step 會處理後續

        # (可選) 檢查是否打到自己底線 - 正常情況下，領域內的球應該總朝對手去
        # 但如果邏輯複雜，或有強烈隨機性，可以保留此檢查
        owner_scored_this_step = False
        if owner_player_state == self.env.player1: # P1 的底線在下方
            if new_ball_y + env_ball_radius_norm >= owner_goal_line_y:
                owner_scored_this_step = True
        else: # Opponent 的底線在上方
            if new_ball_y - env_ball_radius_norm <= owner_goal_line_y:
                owner_scored_this_step = True
        
        if owner_scored_this_step and not scored_this_step: # 確保不是同時得分 (雖然不太可能)
            if DEBUG_PURGATORY_SKILL:
                print(f"[SKILL_DEBUG][{self.__class__.__name__}] ({self.owner.identifier}) Ball hit OWN GOAL LINE in domain!")
            if owner_player_state.lives > 0: owner_player_state.lives -=1 # 自己失分
            round_done = True
            info['scorer'] = target_player_state.identifier # 對手得分
            info['reason'] = f"{target_player_state.identifier}_purgatory_own_goal"
            self.deactivate(own_goal_by_skill=True)
            if self.sound_ball_event: self.sound_ball_event.play()


        # === 6. 處理與板子的碰撞 (領域內的特殊碰撞) ===
        # 領域內的碰撞可以與常規碰撞不同，例如：
        # - 板子擊球後，球以更刁鑽的角度飛出
        # - 板子擊球的 "甜點區" 效果被放大或改變
        # - 球可能短暫黏在板子上再飛出

        # 此階段的簡化：如果球碰到了板子，就簡單地反轉Y方向速度，並給予一個基於擊球點的X方向擾動
        # 我們只檢測與 "目標對手" 板子的碰撞
        if not round_done: # 只有在回合未結束時才檢測板子碰撞
            target_paddle_y_surface_contact_min, target_paddle_y_surface_contact_max = 0, 0
            is_target_top_paddle = False

            if target_player_state == self.env.opponent: # 目標是頂部板子 (P2/AI)
                target_paddle_y_surface_contact_min = 0 # 板子上邊緣
                target_paddle_y_surface_contact_max = env_paddle_height_norm # 板子下邊緣
                is_target_top_paddle = True
            else: # 目標是底部板子 (P1)
                target_paddle_y_surface_contact_min = 1.0 - env_paddle_height_norm
                target_paddle_y_surface_contact_max = 1.0
                is_target_top_paddle = False

            paddle_actual_half_width_norm = target_player_state.paddle_width_normalized / 2.0
            target_paddle_x_min = target_player_state.x - paddle_actual_half_width_norm
            target_paddle_x_max = target_player_state.x + paddle_actual_half_width_norm

            ball_hit_paddle = False
            if is_target_top_paddle: # 目標是頂部板子
                # 球的下邊緣 <= 板子的下邊緣  AND  球的中心Y 大致在板子Y範圍或剛穿過
                if new_ball_y - env_ball_radius_norm <= target_paddle_y_surface_contact_max and \
                   new_ball_y >= target_paddle_y_surface_contact_min - env_ball_radius_norm: # 允許一點點穿透再校正
                    if target_paddle_x_min <= new_ball_x <= target_paddle_x_max:
                        ball_hit_paddle = True
                        new_ball_y = target_paddle_y_surface_contact_max + env_ball_radius_norm # 校正Y位置
            else: # 目標是底部板子
                # 球的上邊緣 >= 板子的上邊緣 AND 球的中心Y 大致在板子Y範圍或剛穿過
                if new_ball_y + env_ball_radius_norm >= target_paddle_y_surface_contact_min and \
                   new_ball_y <= target_paddle_y_surface_contact_max + env_ball_radius_norm:
                    if target_paddle_x_min <= new_ball_x <= target_paddle_x_max:
                        ball_hit_paddle = True
                        new_ball_y = target_paddle_y_surface_contact_min - env_ball_radius_norm # 校正Y位置
            
            if ball_hit_paddle:
                if DEBUG_PURGATORY_SKILL:
                    print(f"[SKILL_DEBUG][{self.__class__.__name__}] Domain: Ball hit TARGET PADDLE ({target_player_state.identifier}).")
                new_ball_vy *= -1.0 # Y方向反彈 (可以加一點隨機性或基於擊球點的變化 self.ball_instability_factor)
                
                # X方向速度受擊球點影響
                hit_offset_from_paddle_center = (new_ball_x - target_player_state.x) / paddle_actual_half_width_norm # -1 到 1
                new_ball_vx += hit_offset_from_paddle_center * base_speed * 0.5 # 0.5 是可調因子
                new_ball_vx = np.clip(new_ball_vx, -base_speed, base_speed) # 限制最大X速度

                # 領域內擊球後，可以讓球更具攻擊性
                new_ball_vy *= (1 + self.ball_instability_factor * 0.2) # 輕微加速Y

                if self.sound_ball_event: self.sound_ball_event.play()
                # 增加環境的 bounce 計數器，如果需要的話 (目前 PongDuelEnv 的 _scale_difficulty 依賴此)
                # 但領域內的球速主要由此技能控制，所以可以考慮不增加 self.env.bounces
                # 或者，如果增加了，需要確保 _scale_difficulty 不會過度干擾領域內的球速

        # === 7. 更新環境中的球體軌跡 (如果技能直接修改環境trail) ===
        # PongDuelEnv 的 step 方法在調用此函數後，如果 run_normal_ball_physics 為 False，
        # 就不會執行常規的 trail 更新。所以如果領域技能需要 trail，要自己處理。
        # 但 SoulEaterBugSkill 的 _update_trail 是直接修改 self.env.trail，我們也可以這樣做
        if hasattr(self.env, 'trail') and hasattr(self.env, 'max_trail_length'):
            self.env.trail.append((new_ball_x, new_ball_y))
            if len(self.env.trail) > self.env.max_trail_length:
                self.env.trail.pop(0)
        
        # 返回更新後的球體狀態 和 回合信息
        return new_ball_x, new_ball_y, new_ball_vx, new_ball_vy, new_spin, round_done, info

    def update_ball_in_domain(self, current_ball_x, current_ball_y, current_ball_vx, current_ball_vy, current_spin,
                              dt, target_player_state, owner_player_state,
                              env_paddle_height_norm, env_ball_radius_norm, env_render_size):
        """
        在此技能啟用期間，由此方法控制球的行為。
        返回: (new_ball_x, new_ball_y, new_ball_vx, new_ball_vy, new_spin, round_done, info)
        或者直接修改 env 的球體屬性並返回 (round_done, info)
        為了與 PongDuelEnv.step 的返回結構類似，我們返回完整的球狀態和回合信息。
        """
        new_ball_x, new_ball_y = current_ball_x, current_ball_y
        new_ball_vx, new_ball_vy = current_ball_vx, current_ball_vy
        new_spin = current_spin
        round_done = False
        info = {'scorer': None, 'reason': None}

        # === 1. 計算球的基礎目標方向 (朝向對手) ===
        # 判斷球應該朝哪個Y方向移動
        if owner_player_state == self.env.player1: # 技能擁有者在下方 (P1)
            target_y_direction = -1.0 # 球應向上移動 (Y值減小)
            target_line_y = 0.0 + env_ball_radius_norm # 對手底線
            owner_line_y = 1.0 - env_ball_radius_norm # 自己底線
        else: # 技能擁有者在上方 (Opponent/P2)
            target_y_direction = 1.0 # 球應向下移動 (Y值增大)
            target_line_y = 1.0 - env_ball_radius_norm
            owner_line_y = 0.0 + env_ball_radius_norm

        # === 2. 更新球的速度 ===
        # 簡單的例子：給予一個基礎速度，並帶有隨機擾動
        base_speed = self.ball_base_speed_in_domain
        angle_to_target_center = math.atan2(target_y_direction, target_player_state.x - new_ball_x) # 指向對手板子中心

        # 加入不穩定性/隨機性
        random_angle_offset = random.uniform(-math.pi / 4, math.pi / 4) * self.ball_instability_factor
        final_angle = angle_to_target_center + random_angle_offset

        new_ball_vx = base_speed * math.cos(final_angle)
        new_ball_vy = base_speed * math.sin(final_angle)

        # 確保Y方向大致正確 (如果隨機偏離過大，進行修正)
        if (target_y_direction < 0 and new_ball_vy > 0) or \
           (target_y_direction > 0 and new_ball_vy < 0):
            new_ball_vy *= -0.5 # 輕微反向或減弱錯誤方向的速度

        # (可選) 簡易的 "追蹤" 效果 (此階段可先簡化或禁用 ball_seek_target_strength)
        if self.ball_seek_target_strength > 0:
            dx_to_target_center = target_player_state.x - new_ball_x
            new_ball_vx += dx_to_target_center * self.ball_seek_target_strength * dt


        # === 3. 更新球的位置 ===
        new_ball_x += new_ball_vx * dt
        new_ball_y += new_ball_vy * dt

        # === 4. 處理邊界碰撞 (牆壁) ===
        if new_ball_x - env_ball_radius_norm <= 0:
            new_ball_x = env_ball_radius_norm
            new_ball_vx *= -1
            if self.sound_ball_event: self.sound_ball_event.play()
        elif new_ball_x + env_ball_radius_norm >= 1.0:
            new_ball_x = 1.0 - env_ball_radius_norm
            new_ball_vx *= -1
            if self.sound_ball_event: self.sound_ball_event.play()

        # === 5. 處理得分 ===
        # 檢查球是否超過對手的底線
        if (target_y_direction < 0 and new_ball_y - env_ball_radius_norm <= target_line_y) or \
           (target_y_direction > 0 and new_ball_y + env_ball_radius_norm >= target_line_y):
            if DEBUG_PURGATORY_SKILL:
                print(f"[SKILL_DEBUG][{self.__class__.__name__}] ({self.owner.identifier}) SCORED in domain against {target_player_state.identifier}!")
            target_player_state.lives -= 1
            # self.env.freeze_timer = pygame.time.get_ticks() # 環境的 freeze_timer 由 env.step 統一處理
            round_done = True
            info['scorer'] = self.owner.identifier
            info['reason'] = f"{self.owner.identifier}_purgatory_scored"
            self.deactivate(scored=True) # 得分後技能通常會結束
            if self.sound_ball_event: self.sound_ball_event.play() # 或專用的得分音效


        # 檢查球是否回到自己半場的底線 (不太可能發生，除非速度設置有問題)
        elif (target_y_direction < 0 and new_ball_y + env_ball_radius_norm >= owner_line_y) or \
             (target_y_direction > 0 and new_ball_y - env_ball_radius_norm <= owner_line_y):
            if DEBUG_PURGATORY_SKILL:
                print(f"[SKILL_DEBUG][{self.__class__.__name__}] ({self.owner.identifier}) Ball hit OWN GOAL LINE in domain!")
            owner_player_state.lives -=1
            round_done = True
            info['scorer'] = target_player_state.identifier # 對手得分
            info['reason'] = f"{target_player_state.identifier}_purgatory_own_goal"
            self.deactivate(hit_own_goal=True)
            if self.sound_ball_event: self.sound_ball_event.play()


        # === 6. 處理與板子的碰撞 (簡化版 - Y軸反彈，X軸忽略或簡單處理) ===
        # 注意：此階段的板子碰撞可以非常簡化，重點是建立覆寫機制。
        # 後續階段可以實現更複雜的領域內板子交互。

        # 檢查與目標板子的碰撞
        target_paddle_y_surface_norm = 0.0
        if target_player_state == self.env.opponent: # 目標在上方
            target_paddle_y_surface_norm = env_paddle_height_norm
        else: # 目標在下方
            target_paddle_y_surface_norm = 1.0 - env_paddle_height_norm

        paddle_half_width_norm = target_player_state.paddle_width_normalized / 2.0
        paddle_x_min = target_player_state.x - paddle_half_width_norm
        paddle_x_max = target_player_state.x + paddle_half_width_norm

        collision_margin = env_ball_radius_norm # 碰撞邊距

        # 球的預計碰撞點 (Y軸)
        ball_contact_y = new_ball_y
        if target_y_direction < 0: # 球向上 (向對手)
            ball_contact_y = new_ball_y - env_ball_radius_norm
            if ball_contact_y <= target_paddle_y_surface_norm and new_ball_y > target_paddle_y_surface_norm - collision_margin: # 檢查是否穿過或接近板面
                 if paddle_x_min <= new_ball_x <= paddle_x_max: # X軸在板子範圍內
                    new_ball_y = target_paddle_y_surface_norm + env_ball_radius_norm # 將球放在板子表面
                    new_ball_vy *= -1 # 簡單反彈
                    new_ball_vx += (new_ball_x - target_player_state.x) * 0.1 # 簡單的擊球點影響
                    if DEBUG_PURGATORY_SKILL: print(f"Domain: Hit target paddle (top)")
                    if self.sound_ball_event: self.sound_ball_event.play()

        elif target_y_direction > 0: # 球向下 (向對手)
            ball_contact_y = new_ball_y + env_ball_radius_norm
            if ball_contact_y >= target_paddle_y_surface_norm and new_ball_y < target_paddle_y_surface_norm + collision_margin:
                 if paddle_x_min <= new_ball_x <= paddle_x_max:
                    new_ball_y = target_paddle_y_surface_norm - env_ball_radius_norm
                    new_ball_vy *= -1
                    new_ball_vx += (new_ball_x - target_player_state.x) * 0.1
                    if DEBUG_PURGATORY_SKILL: print(f"Domain: Hit target paddle (bottom)")
                    if self.sound_ball_event: self.sound_ball_event.play()

        # (可選) 檢查與自己板子的碰撞 (如果球因為某些原因回頭了) - 邏輯類似上面，但板子是 owner_player_state

        # 更新環境中的球體軌跡 (如果技能直接修改環境trail)
        self.env.trail.append((new_ball_x, new_ball_y))
        if len(self.env.trail) > self.env.max_trail_length:
            self.env.trail.pop(0)

        return new_ball_x, new_ball_y, new_ball_vx, new_ball_vy, new_spin, round_done, info


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
        # 第一階段，先簡單返回領域是否啟用和基礎顏色
        if not self.active:
            return {"type": "purgatory_domain", "active_effects": False}

        return {
            "type": "purgatory_domain",
            "active_effects": True,
            "domain_filter_color_rgba": self.domain_filter_color_rgba,
            "ball_aura_color_rgba": self.ball_aura_color_rgba,
            # 未來可以加入更多特效參數，如煉獄幻影的位置、扭曲程度等
        }

    def render(self, surface):
        # 大部分的視覺效果將由 Renderer 根據 get_visual_params() 繪製
        # 此處可以留空，或用於繪製一些技能擁有者特有的、不便於通用 Renderer 處理的指示器
        pass