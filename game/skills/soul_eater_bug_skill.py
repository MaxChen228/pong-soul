# pong-soul/game/skills/soul_eater_bug_skill.py
import pygame
import math
import random
from game.skills.base_skill import Skill # 確保 base_skill.Skill 被正確引入
from game.skills.skill_config import SKILL_CONFIGS
from utils import resource_path

class SoulEaterBugSkill(Skill): # 確認繼承自 Skill
    def __init__(self, env):
        super().__init__(env) # 初始化父類別
        cfg_key = "soul_eater_bug" # 使用變數方便更改技能代碼
        if cfg_key not in SKILL_CONFIGS:
            raise ValueError(f"Skill configuration for '{cfg_key}' not found in SKILL_CONFIGS.")
        cfg = SKILL_CONFIGS[cfg_key]

        self.duration_ms = cfg.get("duration_ms", 5000) # 使用 .get 提供預設值以增加穩健性
        self.cooldown_ms = cfg.get("cooldown_ms", 10000)

        self.active = False
        self.activated_time = 0
        self.cooldown_start_time = 0 # 初始化為0，表示一開始即可用 (或根據邏輯調整)

        self.original_ball_image = None
        bug_image_path = cfg.get("bug_image_path", "assets/default_bug.png") # 提供預設圖片路徑
        try:
            self.bug_image = pygame.image.load(resource_path(bug_image_path)).convert_alpha()
            # 確保 ball_radius 存在於 env，如果 env 的 ball_radius 是 pixel 值
            # 如果 env.ball_radius 是邏輯單位，則需要轉換
            # 假設 env.ball_radius 是 pixel 值
            ball_pixel_radius = self.env.ball_radius
            self.bug_image = pygame.transform.smoothscale(self.bug_image, (ball_pixel_radius * 2, ball_pixel_radius * 2))
        except pygame.error as e:
            print(f"Error loading bug image: {bug_image_path}. Error: {e}")
            self.bug_image = None # 錯誤處理
        except Exception as e:
            print(f"An unexpected error occurred while loading bug image: {e}")
            self.bug_image = None


        # 讀取移動參數，提供預設值
        self.base_y_speed = cfg.get("base_y_speed", 0.02)
        self.x_amplitude = cfg.get("x_amplitude", 0.15)
        self.x_frequency = cfg.get("x_frequency", 2.0)
        self.x_homing_factor = cfg.get("x_homing_factor", 0.01)
        initial_phase_range = cfg.get("initial_phase_offset_range", [0, 6.28318]) # 0 to 2*PI
        self.initial_phase_offset = random.uniform(initial_phase_range[0], initial_phase_range[1])
        self.time_scaling_for_wave = cfg.get("time_scaling_for_wave", 0.05)
        self.time_since_activation_frames = 0

        # 在env中設定一個標誌，確保env實例有此屬性
        # 最好在 PongDuelEnv 的 __init__ 中也初始化 self.bug_skill_active = False
        if not hasattr(self.env, 'bug_skill_active'):
            print("Dynamically adding 'bug_skill_active' to env. Consider initializing it in PongDuelEnv.__init__.")
            self.env.bug_skill_active = False


    def activate(self):
        """嘗試啟動技能"""
        cur_time = pygame.time.get_ticks()
        if not self.active and (self.cooldown_start_time == 0 or (cur_time - self.cooldown_start_time >= self.cooldown_ms)):
            self.active = True
            self.activated_time = cur_time
            self.env.bug_skill_active = True # 通知環境蟲技能已啟動

            if hasattr(self.env, 'renderer') and self.env.renderer is not None:
                self.original_ball_image = self.env.renderer.ball_image
                if self.bug_image:
                    self.env.renderer.ball_image = self.bug_image
                else:
                    print("Warning: Bug image not loaded, cannot change ball appearance.")
            else:
                print("Warning: env.renderer not available for bug skill image swap during activation.")


            self.time_since_activation_frames = 0
            # 技能啟動時，球的運動將由 env.step 中的蟲技能邏輯完全控制
            # 因此將速度和旋轉設為0是合理的，避免干擾
            self.env.ball_vx = 0
            self.env.ball_vy = 0
            self.env.spin = 0
            print(f"{self.__class__.__name__} Activated!") # 使用類名以方便識別
            # (可選) 在此處播放啟動音效
            return True
        print(f"{self.__class__.__name__} activation failed (cooldown or already active).")
        return False

    def update(self):
        """每幀更新技能狀態 (例如檢查持續時間、更新內部計時器)"""
        if not self.active:
            return

        current_time = pygame.time.get_ticks()
        if (current_time - self.activated_time) >= self.duration_ms:
            print(f"{self.__class__.__name__} duration expired.")
            self.deactivate() # 持續時間到，自動停用
            return

        self.time_since_activation_frames += 1

    # --- 實作 Skill 抽象基礎類別要求的方法 ---

    def deactivate(self):
        """實作停用技能的邏輯"""
        if self.active: # 確保只在啟動時執行停用
            print(f"{self.__class__.__name__} Deactivating.")
            self.active = False
            self.env.bug_skill_active = False # 通知環境蟲技能已結束
            self.cooldown_start_time = pygame.time.get_ticks() # 技能結束後，立刻開始計算冷卻時間

            # 恢復原始球圖片
            if hasattr(self.env, 'renderer') and self.env.renderer is not None and self.original_ball_image is not None:
                self.env.renderer.ball_image = self.original_ball_image
            else:
                print("Warning: env.renderer not available or original_ball_image is None during deactivation.")
            self.original_ball_image = None # 清除儲存的圖片
            # (可選) 在此處停止相關音效

    def is_active(self):
        """回傳技能是否正在作用中"""
        return self.active

    def get_cooldown_seconds(self):
        """回傳剩餘的冷卻時間 (秒)"""
        if self.active:
            # 如果技能正在作用，冷卻尚未開始，可以回傳總冷卻時長或0
            # 這裡選擇回傳0，因為能量條此時應顯示持續時間
            return 0.0

        current_time = pygame.time.get_ticks()
        if self.cooldown_start_time == 0: # 若技能從未啟動過 (因此也未進入過冷卻)
            return 0.0 # 沒有冷卻時間

        elapsed_since_cooldown_start = current_time - self.cooldown_start_time
        remaining_cooldown_ms = self.cooldown_ms - elapsed_since_cooldown_start
        
        return max(0.0, remaining_cooldown_ms / 1000.0)

    def get_energy_ratio(self):
        """
        回傳能量比例 (0.0 到 1.0)。
        如果技能正在作用，顯示剩餘持續時間的比例。
        如果技能不在作用（冷卻中或可使用），顯示充能比例。
        """
        current_time = pygame.time.get_ticks()
        if self.active:
            # 技能作用中：顯示剩餘持續時間的比例
            elapsed_duration = current_time - self.activated_time
            # 避免 duration_ms 為0導致除零錯誤
            ratio = max(0.0, (self.duration_ms - elapsed_duration) / self.duration_ms) if self.duration_ms > 0 else 0.0
            return ratio
        else:
            # 技能不在作用中：顯示冷卻完成度（即充能比例）
            if self.cooldown_start_time == 0: # 遊戲開始，技能尚未使用
                return 1.0 # 能量滿
            
            elapsed_since_cooldown_start = current_time - self.cooldown_start_time
            if elapsed_since_cooldown_start >= self.cooldown_ms or self.cooldown_ms == 0 : # 冷卻完畢或無冷卻
                return 1.0 # 能量滿
            else:
                # 避免 cooldown_ms 為0導致除零錯誤
                ratio = elapsed_since_cooldown_start / self.cooldown_ms if self.cooldown_ms > 0 else 1.0
                return min(1.0, ratio) # 確保比例不超過1.0

    def render(self, surface):
        """
        繪製技能專屬的視覺特效。
        SoulEaterBugSkill 主要視覺是球圖片的替換，由 activate/deactivate 控制。
        此處可留空，或添加額外的粒子、光暈等效果。
        """
        # 範例：如果想在蟲的周圍畫一個微弱的光暈 (確保 self.env.renderer 存在)
        if self.active and hasattr(self.env, 'renderer') and self.env.renderer is not None:
            # 計算蟲在螢幕上的實際像素位置
            # bug_cx_render = int(self.env.ball_x * self.env.render_size)
            # bug_cy_render = int(self.env.ball_y * self.env.render_size) + self.env.renderer.offset_y
            # aura_color = (180, 50, 220, 30) # 淡紫色光暈 (R, G, B, Alpha)，Alpha調低更透明
            # ball_pixel_radius = self.env.ball_radius # 假設這是像素單位
            # aura_radius = ball_pixel_radius + 4 # 光暈比蟲大一點

            # # 創建一個帶 Alpha 通道的 Surface 來繪製半透明圓形
            # # 確保 aura_surface 的尺寸足夠大
            # aura_surface_size = aura_radius * 2
            # aura_surface = pygame.Surface((aura_surface_size, aura_surface_size), pygame.SRCALPHA)
            # pygame.draw.circle(aura_surface, aura_color, (aura_radius, aura_radius), aura_radius) # 在aura_surface的中心畫圓
            # surface.blit(aura_surface, (bug_cx_render - aura_radius, bug_cy_render - aura_radius))
            pass
        pass

    # 如果 base_skill.py 中的 has_full_energy_effect 不是抽象方法，則不需要在此覆寫，
    # 除非你想為這個特定技能改變其行為。
    # def has_full_energy_effect(self):
    #     """預設判斷能量是否滿，如技能條追跡線特效可用"""
    #     # 只有在技能不在作用中且能量為1（冷卻完畢）時，才顯示滿能量特效
    #     return not self.active and self.get_energy_ratio() >= 1.0