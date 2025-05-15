# main.py

import pygame
import sys
import time
from enum import Enum

# 遊戲內部模組
from game.theme import Style
from game.settings import GameSettings # GameSettings 也需要被 menu_states 訪問
from game.sound import SoundManager
from utils import resource_path

# 引入狀態
from game.states.base_state import BaseState
from game.states.menu_states import SelectGameModeState # ⭐️ 引入真正的狀態類

DEBUG_GAME_APP = True

class GameFlowStateName(Enum):
    QUIT = 0
    SELECT_GAME_MODE = 1
    SELECT_INPUT_PVA = 2
    SELECT_SKILL_PVA = 3
    RUN_PVP_SKILL_SELECTION = 4
    GAMEPLAY = 5

class GameApp:
    def __init__(self):
        # ... (init 中的螢幕設定等不變) ...
        pygame.init()
        pygame.font.init()

        self.sound_manager = SoundManager()
        self.clock = pygame.time.Clock()
        self.running = True

        try:
            screen_info = pygame.display.Info()
            self.ACTUAL_SCREEN_WIDTH = screen_info.current_w
            self.ACTUAL_SCREEN_HEIGHT = screen_info.current_h
            if DEBUG_GAME_APP: print(f"[GameApp] Detected screen: {self.ACTUAL_SCREEN_WIDTH}x{self.ACTUAL_SCREEN_HEIGHT}")
        except pygame.error as e:
            if DEBUG_GAME_APP: print(f"[GameApp] Pygame display error: {e}. Defaulting to 1280x720.")
            self.ACTUAL_SCREEN_WIDTH, self.ACTUAL_SCREEN_HEIGHT = 1280, 720

        try:
            self.main_screen = pygame.display.set_mode(
                (self.ACTUAL_SCREEN_WIDTH, self.ACTUAL_SCREEN_HEIGHT),
                pygame.FULLSCREEN
            )
            if DEBUG_GAME_APP: print(f"[GameApp] Fullscreen mode: {self.main_screen.get_size()}")
        except pygame.error as e:
            if DEBUG_GAME_APP: print(f"[GameApp] Fullscreen failed: {e}. Windowed fallback.")
            try:
                self.main_screen = pygame.display.set_mode(
                    (self.ACTUAL_SCREEN_WIDTH, self.ACTUAL_SCREEN_HEIGHT)
                )
                if DEBUG_GAME_APP: print(f"[GameApp] Windowed fallback: {self.main_screen.get_size()}")
            except pygame.error as e2:
                print(f"[CRITICAL_ERROR_GAME_APP] No display mode: {e2}. Exiting.")
                pygame.quit()
                sys.exit()
        
        pygame.display.set_caption("Pong Soul (State Machine)")

        self.LOGICAL_MENU_WIDTH = 800
        self.LOGICAL_MENU_HEIGHT = 600
        self.LOGICAL_PVP_SKILL_MENU_WIDTH = 1000
        self.LOGICAL_PVP_SKILL_MENU_HEIGHT = 600
        
        self.GameFlowStateName = GameFlowStateName # ⭐️ 使枚舉在 GameApp 實例中可訪問，方便狀態類使用

        self.states = {}
        self.current_state_name = None
        self.current_state_object = None
        self.current_state_debug_name = "None"

        self.shared_game_data = {
            "selected_game_mode": None,
            "selected_input_mode": "keyboard",
            "p1_selected_skill": None,
            "p2_selected_skill": None,
        }
        
        self._register_states()
        self.change_state(GameFlowStateName.SELECT_GAME_MODE)

# main.py (GameApp._register_states() 方法)

    def _register_states(self):
        # ⭐️ 引入新的狀態類
        from game.states.menu_states import SelectGameModeState, SelectInputPvaState 
        # from game.states.menu_states import SelectSkillPvaState, RunPvpSkillSelectionState # 稍後實現
        # from game.states.gameplay_state import GameplayState # 稍後實現
        
        self.states[GameFlowStateName.SELECT_GAME_MODE] = SelectGameModeState(self)
        # ⭐️ 使用真正的 SelectInputPvaState 替換 PlaceholderState
        self.states[GameFlowStateName.SELECT_INPUT_PVA] = SelectInputPvaState(self)
        
        # 其他狀態暫時仍然使用 PlaceholderState
        class PlaceholderState(BaseState):
            def __init__(self, game_app, name="Placeholder"):
                super().__init__(game_app)
                self.name = name
                self.font = None
                if DEBUG_GAME_APP: print(f"[PlaceholderState:{self.name}] Initialized.")
            def on_enter(self, previous_state_data=None):
                super().on_enter(previous_state_data)
                font_size = 30
                actual_font_size = int(font_size * self.scale_factor)
                self.font = Style.get_font(actual_font_size if actual_font_size > 0 else 30 )
            def handle_event(self, event):
                if event.type == pygame.KEYDOWN:
                    if event.key == pygame.K_ESCAPE:
                        print(f"[PlaceholderState:{self.name}] ESC pressed, requesting quit.")
                        self.request_quit()
                    elif event.key == pygame.K_SPACE:
                        print(f"[PlaceholderState:{self.name}] SPACE pressed, placeholder to QUIT.")
                        self.request_state_change(self.game_app.GameFlowStateName.QUIT)
            def update(self, dt): pass
            def render(self, surface):
                pygame.draw.rect(surface, Style.BACKGROUND_COLOR, self.render_area)
                if self.font:
                    text_surface = self.font.render(f"State: {self.name}", True, Style.TEXT_COLOR)
                    text_rect = text_surface.get_rect(center=self.render_area.center)
                    surface.blit(text_surface, text_rect)
        
        self.states[GameFlowStateName.SELECT_SKILL_PVA] = PlaceholderState(self, "Select Skill (PvA)")
        self.states[GameFlowStateName.RUN_PVP_SKILL_SELECTION] = PlaceholderState(self, "PvP Skill Selection")
        self.states[GameFlowStateName.GAMEPLAY] = PlaceholderState(self, "Gameplay")

    def _calculate_and_set_render_context(self, state_object, state_name_enum):
        """為指定的狀態物件計算並設定 scale_factor 和 render_area。"""
        logical_w, logical_h = 0, 0
        is_gameplay_state = (state_name_enum == GameFlowStateName.GAMEPLAY)

        if state_name_enum in [GameFlowStateName.SELECT_GAME_MODE,
                                      GameFlowStateName.SELECT_INPUT_PVA,
                                      GameFlowStateName.SELECT_SKILL_PVA]:
            logical_w, logical_h = self.LOGICAL_MENU_WIDTH, self.LOGICAL_MENU_HEIGHT
        elif state_name_enum == GameFlowStateName.RUN_PVP_SKILL_SELECTION:
            logical_w, logical_h = self.LOGICAL_PVP_SKILL_MENU_WIDTH, self.LOGICAL_PVP_SKILL_MENU_HEIGHT
        elif is_gameplay_state:
            # GameplayState 的 render_area 是整個螢幕，scale_factor 由 Renderer 內部處理遊戲元素
            logical_w, logical_h = self.ACTUAL_SCREEN_WIDTH, self.ACTUAL_SCREEN_HEIGHT
        
        current_scale_factor = 1.0
        current_render_area = pygame.Rect(0, 0, self.ACTUAL_SCREEN_WIDTH, self.ACTUAL_SCREEN_HEIGHT)

        if logical_w > 0 and logical_h > 0 and not is_gameplay_state:
            scale_x = self.ACTUAL_SCREEN_WIDTH / logical_w
            scale_y = self.ACTUAL_SCREEN_HEIGHT / logical_h
            current_scale_factor = min(scale_x, scale_y)
            scaled_w = int(logical_w * current_scale_factor)
            scaled_h = int(logical_h * current_scale_factor)
            offset_x = (self.ACTUAL_SCREEN_WIDTH - scaled_w) // 2
            offset_y = (self.ACTUAL_SCREEN_HEIGHT - scaled_h) // 2
            current_render_area = pygame.Rect(offset_x, offset_y, scaled_w, scaled_h)
        
        state_object.scale_factor = current_scale_factor
        state_object.render_area = current_render_area
        if DEBUG_GAME_APP:
            print(f"[GameApp._calculate_render_context] For State '{state_name_enum.name}':")
            print(f"    Logical: {logical_w}x{logical_h}, Scale: {current_scale_factor:.2f}")
            print(f"    Render Area on Screen: {current_render_area}")


    def change_state(self, next_state_name_enum, data_to_pass=None):
        if self.current_state_object:
            exit_data = self.current_state_object.on_exit()
            # ... (數據合併邏輯不變) ...
            merged_data = exit_data.copy() if exit_data else {}
            if data_to_pass:
                merged_data.update(data_to_pass)
            data_to_pass = merged_data


        if next_state_name_enum == GameFlowStateName.QUIT:
            self.running = False
            self.current_state_debug_name = "QUIT"
            if DEBUG_GAME_APP: print(f"[GameApp] Changing state to: QUIT")
            return

        if next_state_name_enum in self.states:
            self.current_state_name = next_state_name_enum
            next_state_object = self.states[next_state_name_enum] # 先獲取下一個狀態物件
            self.current_state_debug_name = next_state_name_enum.name
            
            # ⭐️ 在調用 on_enter 之前，為新狀態計算並設定其渲染上下文
            self._calculate_and_set_render_context(next_state_object, next_state_name_enum)
            
            next_state_object.on_enter(data_to_pass) # 現在 on_enter 可以安全使用 self.scale_factor
            self.current_state_object = next_state_object # 正式切換
            if DEBUG_GAME_APP: print(f"[GameApp] Changed state to: {self.current_state_debug_name}")
        else:
            if DEBUG_GAME_APP: print(f"[GameApp] Error: Unknown state name enum '{next_state_name_enum}' requested.")
            self.running = False

    def run(self):
        while self.running:
            dt = self.clock.tick(60) / 1000.0 

            events = pygame.event.get()
            for event in events:
                if event.type == pygame.QUIT:
                    self.running = False
                if self.current_state_object:
                    self.current_state_object.handle_event(event)

            if not self.running: break 

            if self.current_state_object:
                self.current_state_object.update(dt)

                if self.current_state_object.quit_requested:
                    self.running = False
                    break
                if self.current_state_object.next_state_name is not None:
                    next_s_name = self.current_state_object.next_state_name
                    data_from_exit = self.current_state_object.on_exit()
                    self.current_state_object.next_state_name = None 
                    self.change_state(next_s_name, data_from_exit) 
                    if not self.running: break
                    # 當狀態切換後，立即 continue，新的 scale_factor 和 render_area 會在下一次迴圈開始時
                    # 由 _calculate_and_set_render_context 函數在 change_state 內部為新狀態設定，
                    # 然後新狀態的 on_enter 會使用它。
                    # 所以這裡不需要再手動計算。
                    continue 

                # ‼️‼️ 渲染上下文的計算和設定已移至 change_state 和 _calculate_and_set_render_context ‼️‼️
                # ‼️‼️ 在這裡，我們只需要確保 current_state_object 的 scale_factor 和 render_area 是最新的 ‼️‼️
                # ‼️‼️ 事實上，由於 on_enter 在 change_state 中被調用（在計算之後），
                # ‼️‼️ 且 render 依賴 on_enter 初始化的字體，所以這裡不需要再為當前狀態重新賦值 self.scale_factor/render_area
                # ‼️‼️ 除非狀態的邏輯尺寸可以在運行時改變（目前我們的選單不會）。

                self.main_screen.fill(Style.BACKGROUND_COLOR) 
                self.current_state_object.render(self.main_screen) 
            
            pygame.display.flip()

        if DEBUG_GAME_APP: print("[GameApp] Exiting game loop.")
        pygame.quit()
        sys.exit()


if __name__ == '__main__':
    # 確保 GameApp 可以訪問 GameFlowStateName 枚舉
    # 可以通過將 GameFlowStateName 定義在 GameApp 外部或作為 GameApp 的類屬性來實現
    # 在這裡，GameApp 內部創建了一個實例屬性 self.GameFlowStateName
    game = GameApp()
    game.run()