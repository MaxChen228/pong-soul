# pong-soul/game/player_state.py

class PlayerState:
    def __init__(self, initial_x=0.5, initial_paddle_width=60, initial_lives=3, is_ai=False, skill_code=None, env_render_size=400):
        self.x = initial_x
        self.prev_x = initial_x
        self.base_paddle_width = initial_paddle_width
        self.paddle_width = initial_paddle_width
        self.lives = initial_lives
        self.max_lives = initial_lives # 確保 max_lives 被初始化
        self.skill_code_name = skill_code
        self.skill_instance = None
        self.is_ai = is_ai
        self.input_action = 1
        self.last_hit_time = 0 # ⭐️ 新增此行，用於血條閃爍等效果

        self.paddle_width_normalized = self.paddle_width / env_render_size if env_render_size > 0 else 0
        self.base_paddle_width_normalized = self.base_paddle_width / env_render_size if env_render_size > 0 else 0

        print(f"[PlayerState] Initialized: x={self.x}, paddle_width={self.paddle_width}, lives={self.lives}, max_lives={self.max_lives}, skill_code='{self.skill_code_name}', is_ai={self.is_ai}")

    def update_paddle_width_normalized(self, new_width_pixels, env_render_size):
        self.paddle_width = new_width_pixels
        self.paddle_width_normalized = self.paddle_width / env_render_size if env_render_size > 0 else 0

    def reset_state(self, initial_x=0.5):
        self.x = initial_x
        self.prev_x = initial_x
        if self.skill_instance and hasattr(self.skill_instance, 'deactivate'):
            if self.skill_instance.is_active():
                self.skill_instance.deactivate()
        
        # 重置時，將當前球拍寬度恢復為基礎寬度
        if hasattr(self, 'base_paddle_width') and hasattr(self, 'base_paddle_width_normalized'):
             self.paddle_width = self.base_paddle_width
             self.paddle_width_normalized = self.base_paddle_width_normalized
        else: # Fallback if base_paddle_width was somehow not set (should not happen)
            print("[PlayerState] Warning: base_paddle_width not found on reset, paddle width may be incorrect.")


        print(f"[PlayerState] State reset: x={self.x}, paddle_width={self.paddle_width}")