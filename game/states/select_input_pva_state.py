# game/states/select_input_pva_state.py
import pygame
from game.states.base_state import BaseState
from game.theme import Style
# from main import GameFlowStateName

DEBUG_MENU_STATE = True

class SelectInputPvaState(BaseState):
    def __init__(self, game_app):
        super().__init__(game_app)
        self.options = [
            ("Keyboard", "keyboard"), 
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

                self.game_app.shared_game_data["selected_input_mode"] = selected_input_mode_value
                self.request_state_change(self.game_app.GameFlowStateName.SELECT_SKILL_PVA)

            elif event.key == pygame.K_ESCAPE: 
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