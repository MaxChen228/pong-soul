# game/states/settings_menu_state.py
import pygame
from game.states.base_state import BaseState
from game.theme import Style
from game.settings import GameSettings

DEBUG_SETTINGS_MENU_STATE = False

class SettingsMenuState(BaseState):
    def __init__(self, game_app):
        super().__init__(game_app)
        self.options = [
            ("Select Theme", self.game_app.GameFlowStateName.THEME_SELECTION, {}),
            ("Back", None, {}) # "Back" 的目標狀態將在 on_enter 中動態設定
        ]
        # self.display_options is generated in on_enter now after options are finalized
        self.selected_index = 0
        self.item_rects = []
        self.hover_scale_factor = 1.1 # <--- 新增：懸停縮放比例

        self.font_title = None
        self.font_item = None # 將在 on_enter 中創建
        self.previous_state_name = self.game_app.GameFlowStateName.SELECT_GAME_MODE

        if DEBUG_SETTINGS_MENU_STATE: print(f"[State:SettingsMenu] Initialized.")

    def on_enter(self, previous_state_data=None):
        super().on_enter(previous_state_data)
        self.selected_index = 0

        self.previous_state_name = self.persistent_data.get(
            "previous_state_for_settings",
            self.game_app.GameFlowStateName.SELECT_GAME_MODE
        )
        # 更新 "Back" 選項的目標狀態
        self.options[-1] = ("Back", self.previous_state_name, {})
        # 在選項最終確定後生成 display_options
        self.display_options = [opt[0] for opt in self.options]


        self.item_rects = [None] * len(self.options)

        scaled_title_font_size = int(Style.TITLE_FONT_SIZE * self.scale_factor)
        self.base_scaled_item_font_size = int(Style.ITEM_FONT_SIZE * self.scale_factor) # <--- 基礎選項字體大小

        self.font_title = Style.get_font(scaled_title_font_size)
        self.font_item = Style.get_font(self.base_scaled_item_font_size) # <--- 標準選項字體

        if DEBUG_SETTINGS_MENU_STATE:
            print(f"[State:SettingsMenu] Entered. Scale: {self.scale_factor:.2f}, RenderArea: {self.render_area}")
            print(f"    Previous state to return to: {self.previous_state_name}")
            print(f"    Current options: {self.options}")


    def handle_event(self, event):
        if event.type == pygame.MOUSEMOTION:
            for i, rect in enumerate(self.item_rects):
                if rect and rect.collidepoint(event.pos):
                    if self.selected_index != i:
                        self.selected_index = i
                    break
        elif event.type == pygame.MOUSEBUTTONDOWN:
            if event.button == 1:
                for i, rect in enumerate(self.item_rects):
                    if rect and rect.collidepoint(event.pos):
                        self.selected_index = i
                        self.game_app.sound_manager.play_click()
                        selected_option_target_state = self.options[self.selected_index][1]
                        action_data = self.options[self.selected_index][2].copy()

                        if DEBUG_SETTINGS_MENU_STATE:
                            print(f"[State:SettingsMenu] Mouse clicked: {self.options[self.selected_index][0]} -> {selected_option_target_state}")

                        if selected_option_target_state:
                            if selected_option_target_state == self.game_app.GameFlowStateName.THEME_SELECTION:
                                action_data["previous_state_for_theme_selection"] = self.game_app.GameFlowStateName.SETTINGS_MENU
                            self.request_state_change(selected_option_target_state, action_data)
                        return

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
                    print(f"[State:SettingsMenu] Enter key: {self.options[self.selected_index][0]} -> {selected_option_target_state}")

                if selected_option_target_state:
                    if selected_option_target_state == self.game_app.GameFlowStateName.THEME_SELECTION:
                        action_data["previous_state_for_theme_selection"] = self.game_app.GameFlowStateName.SETTINGS_MENU
                    self.request_state_change(selected_option_target_state, action_data)

            elif event.key == pygame.K_ESCAPE:
                self.game_app.sound_manager.play_click()
                # "Back" 選項的目標狀態 (self.options[-1][1]) 就是 ESC 應該返回的狀態
                back_target_state = self.options[-1][1]
                if DEBUG_SETTINGS_MENU_STATE: print(f"[State:SettingsMenu] ESC pressed, returning to {back_target_state}.")
                self.request_state_change(back_target_state)


    def update(self, dt):
        pass

    def render(self, surface):
        pygame.draw.rect(surface, Style.BACKGROUND_COLOR, self.render_area)
        if not self.font_title or not self.font_item:
            return

        title_x = self.render_area.left + int(Style.TITLE_POS[0] * self.scale_factor)
        title_y = self.render_area.top + int(Style.TITLE_POS[1] * self.scale_factor)
        item_start_x_base_abs = self.render_area.left + int(Style.ITEM_START_POS[0] * self.scale_factor)
        item_start_y_base_abs = self.render_area.top + int(Style.ITEM_START_POS[1] * self.scale_factor)
        scaled_line_spacing = int(Style.ITEM_LINE_SPACING * self.scale_factor)

        title_surf = self.font_title.render("Settings", True, Style.TEXT_COLOR)
        surface.blit(title_surf, (title_x, title_y))

        current_item_y_abs = item_start_y_base_abs
        for i, option_text in enumerate(self.display_options): # Use self.display_options
            is_selected = (i == self.selected_index)
            color = Style.PLAYER_COLOR if is_selected else Style.TEXT_COLOR
            
            original_text_surf = self.font_item.render(option_text, True, color)
            original_rect = original_text_surf.get_rect(topleft=(item_start_x_base_abs, current_item_y_abs))
            
            if i < len(self.item_rects):
                self.item_rects[i] = original_rect

            if is_selected:
                scaled_width = int(original_rect.width * self.hover_scale_factor)
                scaled_height = int(original_rect.height * self.hover_scale_factor)
                if original_rect.width > 0 and original_rect.height > 0:
                    scaled_text_surf = pygame.transform.smoothscale(original_text_surf, (scaled_width, scaled_height))
                    scaled_rect = scaled_text_surf.get_rect(center=original_rect.center)
                    surface.blit(scaled_text_surf, scaled_rect)
                else:
                    surface.blit(original_text_surf, original_rect)
            else:
                surface.blit(original_text_surf, original_rect)
            
            current_item_y_abs += scaled_line_spacing