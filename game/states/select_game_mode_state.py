# game/states/select_game_mode_state.py
import pygame
from game.states.base_state import BaseState
from game.theme import Style
from game.settings import GameSettings
# from main import GameFlowStateName # GameApp 實例會傳遞 GameFlowStateName 枚舉

DEBUG_MENU_STATE = True # 你可以為每個狀態文件保留獨立的 DEBUG 開關

class SelectGameModeState(BaseState):
    def __init__(self, game_app):
        super().__init__(game_app)
        # game_app.GameFlowStateName 可以從 game_app 實例中獲取
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
                action_data = self.options[self.selected_index][2].copy() 

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
        if not self.font_title: return

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