# game/states/base_state.py
from abc import ABC, abstractmethod
import pygame

class BaseState(ABC):
    def __init__(self, game_app):
        self.game_app = game_app # 對主 GameApp 實例的引用
        self.next_state_name = None # 用於指示下一個狀態的名稱 (字串或枚舉)
        self.quit_requested = False # 標記是否請求退出整個遊戲
        self.persistent_data = {} # 用於在狀態之間傳遞數據 (可選)

        # 每個狀態可以有自己的縮放因子和渲染區域，由 GameApp 計算並傳遞
        self.scale_factor = 1.0
        self.render_area = pygame.Rect(0, 0, self.game_app.ACTUAL_SCREEN_WIDTH, self.game_app.ACTUAL_SCREEN_HEIGHT)


    @abstractmethod
    def handle_event(self, event):
        """處理單個 Pygame 事件。"""
        pass

    @abstractmethod
    def update(self, dt): # dt (delta time) 如果遊戲邏輯是基於時間的，目前我們主要是基於幀
        """更新狀態邏輯。"""
        pass

    @abstractmethod
    def render(self, surface):
        """將當前狀態渲染到指定的 surface 上。
        surface 通常是 self.game_app.main_screen。
        縮放和定位應在此方法內部，使用 self.scale_factor 和 self.render_area。
        """
        pass

    def on_enter(self, previous_state_data=None):
        """當進入此狀態時調用。可以接收來自前一個狀態的數據。"""
        if previous_state_data:
            self.persistent_data.update(previous_state_data)
        if hasattr(self.game_app, 'current_state_debug_name'): # 用於排錯
            print(f"[STATE_MACHINE] Entering State: {self.game_app.current_state_debug_name}")


    def on_exit(self):
        """當離開此狀態時調用。可以返回數據給下一個狀態。"""
        if hasattr(self.game_app, 'current_state_debug_name'): # 用於排錯
            print(f"[STATE_MACHINE] Exiting State: {self.game_app.current_state_debug_name}")
        return self.persistent_data # 默認傳遞所有 persistent_data

    def request_quit(self):
        """請求退出遊戲。"""
        self.quit_requested = True

    def request_state_change(self, next_state_name, data_to_pass=None):
        """請求切換到另一個狀態。"""
        self.next_state_name = next_state_name
        if data_to_pass:
            self.persistent_data.update(data_to_pass) # 更新要傳遞的數據