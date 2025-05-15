# game/states/settings_menu_state.py
import pygame
from game.states.base_state import BaseState
from game.theme import Style, get_available_theme_names # 需要 get_available_theme_names
from game.settings import GameSettings # 需要 GameSettings 來調用 set_active_theme

DEBUG_SETTINGS_MENU_STATE = False

class SettingsMenuState(BaseState):
    def __init__(self, game_app):
        super().__init__(game_app)
        self.options = [
            ("Select Theme", self.game_app.GameFlowStateName.THEME_SELECTION, {}),
            ("Back", None, {}) # "Back" 的目標狀態將在 on_enter 中動態設定
        ]
        self.display_options = [opt[0] for opt in self.options]
        self.selected_index = 0
        self.font_title = None
        self.font_item = None
        self.previous_state_name = self.game_app.GameFlowStateName.SELECT_GAME_MODE # 預設返回到主選單

        if DEBUG_SETTINGS_MENU_STATE: print(f"[State:SettingsMenu] Initialized.")

    def on_enter(self, previous_state_data=None):
        super().on_enter(previous_state_data)
        self.selected_index = 0

        # 從 persistent_data 中獲取是從哪個狀態跳轉過來的，以便可以正確返回
        # 如果沒有提供，則預設返回到主選單
        self.previous_state_name = self.persistent_data.get(
            "previous_state_for_settings", 
            self.game_app.GameFlowStateName.SELECT_GAME_MODE
        )
        # 更新 "Back" 選項的目標狀態
        self.options[-1] = ("Back", self.previous_state_name, {}) # 最後一個選項是 "Back"


        scaled_title_font_size = int(Style.TITLE_FONT_SIZE * self.scale_factor)
        scaled_item_font_size = int(Style.ITEM_FONT_SIZE * self.scale_factor)

        self.font_title = Style.get_font(scaled_title_font_size)
        self.font_item = Style.get_font(scaled_item_font_size)

        if DEBUG_SETTINGS_MENU_STATE:
            print(f"[State:SettingsMenu] Entered. Scale: {self.scale_factor:.2f}, RenderArea: {self.render_area}")
            print(f"    Previous state to return to: {self.previous_state_name}")


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
                selected_option_target_state = self.options[self.selected_index][1]
                action_data = self.options[self.selected_index][2].copy()

                if DEBUG_SETTINGS_MENU_STATE:
                    print(f"[State:SettingsMenu] Selected: {self.options[self.selected_index][0]} -> {selected_option_target_state}")

                if selected_option_target_state:
                    # 如果是跳轉到主題選擇，傳遞當前狀態 (SettingsMenuState) 作為返回目標
                    if selected_option_target_state == self.game_app.GameFlowStateName.THEME_SELECTION:
                        action_data["previous_state_for_theme_selection"] = self.game_app.GameFlowStateName.SETTINGS_MENU
                    
                    self.request_state_change(selected_option_target_state, action_data)
                # "Back" 選項的 target_state 已經在 on_enter 中設定為 self.previous_state_name

            elif event.key == pygame.K_ESCAPE: # ESC 也作為返回
                self.game_app.sound_manager.play_click()
                if DEBUG_SETTINGS_MENU_STATE: print(f"[State:SettingsMenu] ESC pressed, returning to {self.previous_state_name}.")
                self.request_state_change(self.previous_state_name)


    def update(self, dt):
        pass

    def render(self, surface):
        pygame.draw.rect(surface, Style.BACKGROUND_COLOR, self.render_area)
        if not self.font_title or not self.font_item:
            return

        title_x = self.render_area.left + int(Style.TITLE_POS[0] * self.scale_factor)
        title_y = self.render_area.top + int(Style.TITLE_POS[1] * self.scale_factor)
        item_start_x_base = int(Style.ITEM_START_POS[0] * self.scale_factor)
        item_start_y_base = self.render_area.top + int(Style.ITEM_START_POS[1] * self.scale_factor)
        scaled_line_spacing = int(Style.ITEM_LINE_SPACING * self.scale_factor)

        title_surf = self.font_title.render("Settings", True, Style.TEXT_COLOR)
        surface.blit(title_surf, (title_x, title_y))

        current_item_y = item_start_y_base
        for i, option_text in enumerate(self.display_options):
            color = Style.PLAYER_COLOR if i == self.selected_index else Style.TEXT_COLOR
            text_surf = self.font_item.render(option_text, True, color)
            item_x = self.render_area.left + item_start_x_base
            surface.blit(text_surf, (item_x, current_item_y))
            current_item_y += scaled_line_spacing