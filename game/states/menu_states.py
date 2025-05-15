# game/states/menu_states.py
import pygame
from game.states.base_state import BaseState
from game.theme import Style
from game.settings import GameSettings
# from main import GameFlowStateName # 避免循環導入

DEBUG_MENU_STATE = True

class SelectGameModeState(BaseState): # 這個類保持不變
    def __init__(self, game_app):
        super().__init__(game_app)
        self.options = [
            ("Player vs. AI", self.game_app.GameFlowStateName.SELECT_INPUT_PVA, {"selected_game_mode": GameSettings.GameMode.PLAYER_VS_AI}),
            ("Player vs. Player", self.game_app.GameFlowStateName.RUN_PVP_SKILL_SELECTION, {"selected_game_mode": GameSettings.GameMode.PLAYER_VS_PLAYER}),
            ("Quit Game", self.game_app.GameFlowStateName.QUIT, {})
        ]
        self.display_options = [opt[0] for opt in self.options]
        self.selected_index = 0
        self.font_title = None
        self.font_subtitle = None
        self.font_item = None
        if DEBUG_MENU_STATE: print(f"[State:SelectGameMode] Initialized.")

    def on_enter(self, previous_state_data=None):
        super().on_enter(previous_state_data)
        self.selected_index = 0
        scaled_title_font_size = int(Style.TITLE_FONT_SIZE * self.scale_factor)
        scaled_subtitle_font_size = int(Style.SUBTITLE_FONT_SIZE * self.scale_factor)
        scaled_item_font_size = int(Style.ITEM_FONT_SIZE * self.scale_factor)
        self.font_title = Style.get_font(scaled_title_font_size)
        self.font_subtitle = Style.get_font(scaled_subtitle_font_size)
        self.font_item = Style.get_font(scaled_item_font_size)
        if DEBUG_MENU_STATE: print(f"[State:SelectGameMode] Entered. Scale: {self.scale_factor:.2f}, RenderArea: {self.render_area}")

    def handle_event(self, event):
        if event.type == pygame.KEYDOWN:
            if event.key == pygame.K_DOWN:
                self.selected_index = (self.selected_index + 1) % len(self.options)
                self.game_app.sound_manager.play_click()
            elif event.key == pygame.K_UP:
                self.selected_index = (self.selected_index - 1 + len(self.options)) % len(self.options)
                self.game_app.sound_manager.play_click()
            elif event.key == pygame.K_RETURN:
                self.game_app.sound_manager.play_click()
                selected_action_target_state = self.options[self.selected_index][1]
                action_data = self.options[self.selected_index][2].copy() # 複製以避免修改原始配置

                if DEBUG_MENU_STATE: print(f"[State:SelectGameMode] Selected: {self.options[self.selected_index][0]}")

                if selected_action_target_state == self.game_app.GameFlowStateName.QUIT:
                    self.request_quit()
                else:
                    if "selected_game_mode" in action_data:
                        self.game_app.shared_game_data["selected_game_mode"] = action_data["selected_game_mode"]
                    
                    if action_data.get("selected_game_mode") == GameSettings.GameMode.PLAYER_VS_PLAYER:
                        self.game_app.shared_game_data["selected_input_mode"] = "keyboard"
                        if DEBUG_MENU_STATE: print(f"    PvP selected, input mode forced to keyboard.")
                    
                    self.request_state_change(selected_action_target_state, action_data)
            elif event.key == pygame.K_ESCAPE:
                self.game_app.sound_manager.play_click()
                if DEBUG_MENU_STATE: print(f"[State:SelectGameMode] ESC pressed, doing nothing (use Quit option).")

    def update(self, dt):
        pass

    def render(self, surface):
        pygame.draw.rect(surface, Style.BACKGROUND_COLOR, self.render_area)
        if not self.font_title: return # 如果字體未初始化 (可能在極端情況下發生)

        title_x = self.render_area.left + int(Style.TITLE_POS[0] * self.scale_factor)
        title_y = self.render_area.top + int(Style.TITLE_POS[1] * self.scale_factor)
        subtitle_x = self.render_area.left + int(Style.SUBTITLE_POS[0] * self.scale_factor)
        subtitle_y = self.render_area.top + int(Style.SUBTITLE_POS[1] * self.scale_factor)
        item_start_x_base = int(Style.ITEM_START_POS[0] * self.scale_factor)
        item_start_y_base = int(Style.ITEM_START_POS[1] * self.scale_factor)
        scaled_line_spacing = int(Style.ITEM_LINE_SPACING * self.scale_factor)

        title_surf = self.font_title.render("Select Game Mode", True, Style.TEXT_COLOR)
        surface.blit(title_surf, (title_x, title_y))
        subtitle_surf = self.font_subtitle.render("(UP/DOWN, ENTER to confirm)", True, Style.TEXT_COLOR)
        surface.blit(subtitle_surf, (subtitle_x, subtitle_y))

        for i, option_text in enumerate(self.display_options):
            color = Style.PLAYER_COLOR if i == self.selected_index else Style.TEXT_COLOR
            text_surf = self.font_item.render(option_text, True, color)
            item_x = self.render_area.left + item_start_x_base
            item_y = self.render_area.top + item_start_y_base + i * scaled_line_spacing
            surface.blit(text_surf, (item_x, item_y))

# ⭐️ 新增 SelectInputPvaState 類 ⭐️
class SelectInputPvaState(BaseState):
    def __init__(self, game_app):
        super().__init__(game_app)
        self.options = [
            ("Keyboard", "keyboard"), # (顯示文字, 對應的 input_mode 值)
            ("Mouse", "mouse")
        ]
        self.display_options = [opt[0] for opt in self.options]
        self.selected_index = 0
        self.font_title = None
        self.font_subtitle = None
        self.font_item = None
        if DEBUG_MENU_STATE: print(f"[State:SelectInputPva] Initialized.")

    def on_enter(self, previous_state_data=None):
        super().on_enter(previous_state_data)
        self.selected_index = 0
        # 根據當前狀態的 scale_factor 初始化字體
        scaled_title_font_size = int(Style.TITLE_FONT_SIZE * self.scale_factor)
        scaled_subtitle_font_size = int(Style.SUBTITLE_FONT_SIZE * self.scale_factor)
        scaled_item_font_size = int(Style.ITEM_FONT_SIZE * self.scale_factor)

        self.font_title = Style.get_font(scaled_title_font_size)
        self.font_subtitle = Style.get_font(scaled_subtitle_font_size)
        self.font_item = Style.get_font(scaled_item_font_size)
        if DEBUG_MENU_STATE: print(f"[State:SelectInputPva] Entered. Scale: {self.scale_factor:.2f}, RenderArea: {self.render_area}")
        if DEBUG_MENU_STATE: print(f"    Game mode from previous state: {self.game_app.shared_game_data.get('selected_game_mode')}")


    def handle_event(self, event):
        if event.type == pygame.KEYDOWN:
            if event.key == pygame.K_DOWN:
                self.selected_index = (self.selected_index + 1) % len(self.options)
                self.game_app.sound_manager.play_click()
            elif event.key == pygame.K_UP:
                self.selected_index = (self.selected_index - 1 + len(self.options)) % len(self.options)
                self.game_app.sound_manager.play_click()
            elif event.key == pygame.K_RETURN:
                self.game_app.sound_manager.play_click()
                selected_input_mode_value = self.options[self.selected_index][1]
                if DEBUG_MENU_STATE: print(f"[State:SelectInputPva] Selected input: {selected_input_mode_value}")
                
                # 更新 GameApp 中的共享數據
                self.game_app.shared_game_data["selected_input_mode"] = selected_input_mode_value
                
                # 請求切換到 PvA 技能選擇狀態
                self.request_state_change(self.game_app.GameFlowStateName.SELECT_SKILL_PVA)

            elif event.key == pygame.K_ESCAPE: # 按 ESC 返回到遊戲模式選擇
                self.game_app.sound_manager.play_click()
                if DEBUG_MENU_STATE: print(f"[State:SelectInputPva] ESC pressed, returning to SelectGameMode.")
                self.request_state_change(self.game_app.GameFlowStateName.SELECT_GAME_MODE)

    def update(self, dt):
        pass

    def render(self, surface):
        pygame.draw.rect(surface, Style.BACKGROUND_COLOR, self.render_area)
        if not self.font_title: return

        title_x = self.render_area.left + int(Style.TITLE_POS[0] * self.scale_factor)
        title_y = self.render_area.top + int(Style.TITLE_POS[1] * self.scale_factor)
        subtitle_x = self.render_area.left + int(Style.SUBTITLE_POS[0] * self.scale_factor)
        subtitle_y = self.render_area.top + int(Style.SUBTITLE_POS[1] * self.scale_factor)
        item_start_x_base = int(Style.ITEM_START_POS[0] * self.scale_factor)
        item_start_y_base = int(Style.ITEM_START_POS[1] * self.scale_factor)
        scaled_line_spacing = int(Style.ITEM_LINE_SPACING * self.scale_factor)

        title_surf = self.font_title.render("Select Controller (PvA)", True, Style.TEXT_COLOR)
        surface.blit(title_surf, (title_x, title_y))
        subtitle_surf = self.font_subtitle.render("(UP/DOWN, ENTER, ESC to back)", True, Style.TEXT_COLOR)
        surface.blit(subtitle_surf, (subtitle_x, subtitle_y))

        for i, option_text in enumerate(self.display_options):
            color = Style.PLAYER_COLOR if i == self.selected_index else Style.TEXT_COLOR
            text_surf = self.font_item.render(option_text, True, color)
            item_x = self.render_area.left + item_start_x_base
            item_y = self.render_area.top + item_start_y_base + i * scaled_line_spacing
            surface.blit(text_surf, (item_x, item_y))