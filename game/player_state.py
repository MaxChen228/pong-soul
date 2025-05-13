# pong-soul/game/player_state.py

# ⭐️ [SKILL_DEBUG] 引入 Style 以便 PlayerState 可以有預設顏色
from game.theme import Style # 假設 Style.PLAYER_COLOR 和 Style.AI_COLOR 已定義

class PlayerState:
    def __init__(self, initial_x=0.5, initial_paddle_width=60, initial_lives=3, is_ai=False, skill_code=None, env_render_size=400, player_identifier="player_default"): # ⭐️ player_identifier for debug
        self.identifier = player_identifier # ⭐️ 用於除錯 e.g., "player1", "opponent"
        self.x = initial_x
        self.prev_x = initial_x
        
        self.base_paddle_width = initial_paddle_width # 像素
        self.paddle_width = initial_paddle_width    # 當前像素

        self.lives = initial_lives
        self.max_lives = initial_lives
        self.last_hit_time = 0

        self.is_ai = is_ai
        self.input_action = 1 # 0: left, 1: stay, 2: right

        # 技能相關屬性
        self.skill_code_name = skill_code
        self.skill_instance = None # ⭐️ 將在此處儲存技能實例

        # 外觀相關屬性 (技能可能會修改)
        # ⭐️ 設定一個基礎顏色，技能可以臨時改變它
        self.base_paddle_color = Style.PLAYER_COLOR if self.identifier == "player1" else Style.AI_COLOR # 簡單的預設
        self.paddle_color = self.base_paddle_color # 當前球拍顏色

        self.env_render_size = env_render_size # 儲存 render_size 以便後續計算
        self.paddle_width_normalized = self.paddle_width / env_render_size if env_render_size > 0 else 0
        self.base_paddle_width_normalized = self.base_paddle_width / env_render_size if env_render_size > 0 else 0

        print(f"[SKILL_DEBUG][PlayerState] ({self.identifier}) Initialized: x={self.x}, paddle_width={self.paddle_width}, lives={self.lives}, skill_code='{self.skill_code_name}', color={self.paddle_color}")

    def update_paddle_width_normalized(self, new_width_pixels): # 移除 env_render_size 參數，使用 self.env_render_size
        self.paddle_width = new_width_pixels
        self.paddle_width_normalized = self.paddle_width / self.env_render_size if self.env_render_size > 0 else 0
        # print(f"[SKILL_DEBUG][PlayerState] ({self.identifier}) Paddle width updated to: {self.paddle_width}px")

    def reset_state(self, initial_x=0.5):
        self.x = initial_x
        self.prev_x = initial_x
        
        # 重置技能可能影響的狀態
        self.paddle_width = self.base_paddle_width
        self.paddle_width_normalized = self.base_paddle_width_normalized
        self.paddle_color = self.base_paddle_color

        if self.skill_instance and hasattr(self.skill_instance, 'deactivate') and self.skill_instance.is_active():
            print(f"[SKILL_DEBUG][PlayerState] ({self.identifier}) Deactivating skill during reset.")
            self.skill_instance.deactivate() # 確保技能被停用

        print(f"[SKILL_DEBUG][PlayerState] ({self.identifier}) State reset: x={self.x}, paddle_width={self.paddle_width}, color={self.paddle_color}")