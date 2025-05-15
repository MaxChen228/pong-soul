# pong-soul/game/skills/long_paddle_skill.py
import pygame
from game.skills.base_skill import Skill
from game.skills.skill_config import SKILL_CONFIGS # 假設 SKILL_CONFIGS["long_paddle"] 存在且正確

class LongPaddleSkill(Skill):
    def __init__(self, env, owner_player_state): # ⭐️ 修改參數
        super().__init__(env, owner_player_state) # ⭐️ 調用父類構造函數
        cfg_key = "long_paddle"
        if cfg_key not in SKILL_CONFIGS:
             raise ValueError(f"Skill configuration for '{cfg_key}' not found.")
        cfg = SKILL_CONFIGS[cfg_key]

        self.duration_ms = cfg["duration_ms"]
        self.cooldown_ms = cfg["cooldown_ms"]
        self.paddle_multiplier = cfg["paddle_multiplier"]
        self.skill_paddle_color = cfg.get("paddle_color", (0, 255, 100)) # 技能啟用時的顏色

        self.active = False
        self.activated_time = 0
        self.cooldown_start_time = 0

        self.animation_ms = cfg["animation_ms"]
        # ⭐️ 從 owner 獲取原始和目標寬度 (像素)
        self.original_paddle_width_px = self.owner.base_paddle_width
        self.target_paddle_width_px = int(self.original_paddle_width_px * self.paddle_multiplier)

        self.is_animating = False
        self.anim_start_time = 0
        self.current_width_at_anim_start_px = self.original_paddle_width_px

        print(f"[SKILL_DEBUG][LongPaddleSkill] ({self.owner.identifier}) Initialized. OriginalWidth: {self.original_paddle_width_px}, TargetWidth: {self.target_paddle_width_px}")

    def activate(self):
        cur = pygame.time.get_ticks()
        # 檢查冷卻時間是否已過，且技能目前未啟用
        if not self.active and (self.cooldown_start_time == 0 or (cur - self.cooldown_start_time >= self.cooldown_ms)):
            self.active = True
            self.activated_time = cur
            self.is_animating = True # 開始伸長動畫
            self.anim_start_time = cur
            # ⭐️ 記錄動畫開始時的寬度 (應該是原始寬度)
            self.current_width_at_anim_start_px = self.owner.paddle_width # 或者直接用 self.original_paddle_width_px
            
            # ⭐️ 設定擁有者球拍顏色
            self.owner.paddle_color = self.skill_paddle_color
            print(f"[SKILL_DEBUG][LongPaddleSkill] ({self.owner.identifier}) Activated! Animating to {self.target_paddle_width_px}px. Color: {self.owner.paddle_color}")
            return True
        print(f"[SKILL_DEBUG][LongPaddleSkill] ({self.owner.identifier}) Activation failed (active: {self.active}, cooldown: {self.get_cooldown_seconds():.1f}s).")
        return False

    def update(self):
        if not self.active and not self.is_animating: # 如果技能未啟用且不在縮回動畫中，則不執行任何操作
            return

        cur = pygame.time.get_ticks()

        if self.active: # 技能效果持續中
            if (cur - self.activated_time) >= self.duration_ms:
                print(f"[SKILL_DEBUG][LongPaddleSkill] ({self.owner.identifier}) Duration expired. Deactivating.")
                self.deactivate() # 持續時間到，開始縮回
            else:
                # 技能生效期間的伸長動畫
                if self.is_animating:
                    elapsed_anim = cur - self.anim_start_time
                    if elapsed_anim < self.animation_ms:
                        ratio = elapsed_anim / self.animation_ms
                        # 從 current_width_at_anim_start_px 變到 target_paddle_width_px
                        new_width = int(
                            self.current_width_at_anim_start_px + 
                            (self.target_paddle_width_px - self.current_width_at_anim_start_px) * ratio
                        )
                        self.owner.update_paddle_width_normalized(new_width) # ⭐️ 更新擁有者的球拍寬度
                    else: # 動畫結束
                        self.owner.update_paddle_width_normalized(self.target_paddle_width_px)
                        self.is_animating = False # 伸長動畫結束
                        # print(f"[SKILL_DEBUG][LongPaddleSkill] ({self.owner.identifier}) Stretch animation finished. Width: {self.owner.paddle_width}")
                # 如果不在動畫中，確保寬度是目標寬度 (冗餘檢查)
                elif self.owner.paddle_width != self.target_paddle_width_px:
                     self.owner.update_paddle_width_normalized(self.target_paddle_width_px)


        elif self.is_animating: #不在 active 狀態，但在 is_animating 狀態 (即縮回動畫中)
            elapsed_anim = cur - self.anim_start_time
            if elapsed_anim < self.animation_ms:
                ratio = elapsed_anim / self.animation_ms
                # 從 current_width_at_anim_start_px (可能是 target_paddle_width_px 或中途停用時的寬度) 變到 original_paddle_width_px
                new_width = int(
                    self.current_width_at_anim_start_px - 
                    (self.current_width_at_anim_start_px - self.original_paddle_width_px) * ratio
                )
                self.owner.update_paddle_width_normalized(new_width)
            else: # 縮回動畫結束
                self.owner.update_paddle_width_normalized(self.original_paddle_width_px)
                self.is_animating = False
                self.owner.paddle_color = self.owner.base_paddle_color # ⭐️ 恢復擁有者原始顏色
                print(f"[SKILL_DEBUG][LongPaddleSkill] ({self.owner.identifier}) Shrink animation finished. Width: {self.owner.paddle_width}, Color: {self.owner.paddle_color}")


    def deactivate(self):
        if self.active: # 只有在 active 時才能觸發正常的 deactivate 流程 (開始縮回動畫)
            print(f"[SKILL_DEBUG][LongPaddleSkill] ({self.owner.identifier}) Deactivating by request. Current width: {self.owner.paddle_width}")
            self.active = False
            self.cooldown_start_time = pygame.time.get_ticks() # 開始計算冷卻
            
            # 開始縮回動畫
            self.is_animating = True
            self.anim_start_time = pygame.time.get_ticks()
            self.current_width_at_anim_start_px = self.owner.paddle_width # 從當前寬度開始縮回
            # 顏色會在縮回動畫結束後恢復
        elif self.is_animating: # 如果正在動畫中（例如伸長到一半被強制deactivate），也應該處理
            print(f"[SKILL_DEBUG][LongPaddleSkill] ({self.owner.identifier}) Deactivating during animation. Current width: {self.owner.paddle_width}")
            self.active = False # 確保 active 為 false
            # 冷卻時間應該在技能效果真正結束時開始，或者在 activate 時檢查
            if self.cooldown_start_time == 0: # 避免重複設定冷卻開始時間
                 self.cooldown_start_time = pygame.time.get_ticks()

            # 如果正在伸長，目標變為原始寬度；如果正在縮回，目標不變
            # 簡化：直接讓縮回動畫從當前寬度縮回至原始寬度
            self.is_animating = True # 確保動畫標誌為 True
            self.anim_start_time = pygame.time.get_ticks() # 重置動畫計時器
            self.current_width_at_anim_start_px = self.owner.paddle_width
            # 顏色恢復將由 update 中的縮回動畫結束邏輯處理

    def is_active(self):
        return self.active

    def get_cooldown_seconds(self):
        if self.active: return 0.0 # 技能作用期間沒有冷卻倒數
        current_time = pygame.time.get_ticks()
        if self.cooldown_start_time == 0: return 0.0 
        elapsed = current_time - self.cooldown_start_time
        remaining = self.cooldown_ms - elapsed
        return max(0.0, remaining / 1000.0)

    def get_energy_ratio(self): # 能量條顯示：啟用時計時，未啟用時計算冷卻進度
        current_time = pygame.time.get_ticks()
        if self.active:
            elapsed_duration = current_time - self.activated_time
            ratio = (self.duration_ms - elapsed_duration) / self.duration_ms if self.duration_ms > 0 else 0.0
            return max(0.0, ratio)
        else:
            if self.cooldown_start_time == 0: return 1.0 # 從未啟用過，或已冷卻完畢
            elapsed_cooldown = current_time - self.cooldown_start_time
            if elapsed_cooldown >= self.cooldown_ms: return 1.0 # 冷卻完畢
            ratio = elapsed_cooldown / self.cooldown_ms if self.cooldown_ms > 0 else 1.0
            return min(1.0, ratio)
            
    def render(self, surface):
        pass # 長板技能目前沒有額外的視覺效果需要在此渲染

    def get_visual_params(self):
        # 長板技能目前沒有除了改變球拍寬度（由 PlayerState 管理）和顏色（由 Renderer 根據 PlayerState.paddle_color 繪製）
        # 之外的特殊視覺效果需要 Renderer 額外處理。
        return {}