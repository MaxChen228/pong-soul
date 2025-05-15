# game/states/select_skill_pva_state.py
import pygame
from game.states.base_state import BaseState
from game.theme import Style
from game.constants import DEFAULT_MENU_CONTROLS

DEBUG_MENU_STATE = True

class SelectSkillPvaState(BaseState):
    def __init__(self, game_app):
        super().__init__(game_app)
        self.skills_options = [
            ("Slow Mo", "slowmo"),
            ("Long Paddle", "long_paddle"),
            ("Soul Eater Bug", "soul_eater_bug")
        ]
        self.display_options = [opt[0] for opt in self.skills_options]
        self.selected_index = 0
        self.font_title = None
        self.font_subtitle = None
        self.font_item = None

        self.key_map = DEFAULT_MENU_CONTROLS
        self.player_identifier = "Player" 

        if DEBUG_MENU_STATE: print(f"[State:SelectSkillPva] Initialized.")

    def on_enter(self, previous_state_data=None):
        super().on_enter(previous_state_data)
        self.selected_index = 0
        scaled_title_font_size = int(Style.TITLE_FONT_SIZE * self.scale_factor)
        scaled_subtitle_font_size = int(Style.SUBTITLE_FONT_SIZE * self.scale_factor)
        scaled_item_font_size = int(Style.ITEM_FONT_SIZE * self.scale_factor)

        self.font_title = Style.get_font(scaled_title_font_size)
        self.font_subtitle = Style.get_font(scaled_subtitle_font_size)
        self.font_item = Style.get_font(scaled_item_font_size)
        if DEBUG_MENU_STATE:
            print(f"[State:SelectSkillPva] Entered. Scale: {self.scale_factor:.2f}, RenderArea: {self.render_area}")
            print(f"    Shared data: GameMode='{self.game_app.shared_game_data.get('selected_game_mode')}', Input='{self.game_app.shared_game_data.get('selected_input_mode')}'")

    def handle_event(self, event):
        if event.type == pygame.KEYDOWN:
            if event.key == self.key_map['DOWN']:
                self.selected_index = (self.selected_index + 1) % len(self.skills_options)
                self.game_app.sound_manager.play_click()
            elif event.key == self.key_map['UP']:
                self.selected_index = (self.selected_index - 1 + len(self.skills_options)) % len(self.skills_options)
                self.game_app.sound_manager.play_click()
            elif event.key == self.key_map['CONFIRM']:
                self.game_app.sound_manager.play_click()
                selected_skill_code = self.skills_options[self.selected_index][1]
                if DEBUG_MENU_STATE: print(f"[State:SelectSkillPva] Selected skill: {selected_skill_code}")

                self.game_app.shared_game_data["p1_selected_skill"] = selected_skill_code
                self.game_app.shared_game_data["p2_selected_skill"] = None 

                data_for_gameplay = {
                    "game_mode": self.game_app.shared_game_data.get("selected_game_mode"),
                    "input_mode": self.game_app.shared_game_data.get("selected_input_mode"),
                    "p1_skill": selected_skill_code,
                    "p2_skill": None
                    # GameplayState 在 on_enter 時會處理關卡選擇 (如果需要)
                }
                self.request_state_change(self.game_app.GameFlowStateName.GAMEPLAY, data_for_gameplay)

            elif event.key == self.key_map['CANCEL']: 
                self.game_app.sound_manager.play_click()
                if DEBUG_MENU_STATE: print(f"[State:SelectSkillPva] ESC pressed, returning to SelectInputPva.")
                self.request_state_change(self.game_app.GameFlowStateName.SELECT_INPUT_PVA)

    def update(self, dt):
        pass

    def render(self, surface):
        pygame.draw.rect(surface, Style.BACKGROUND_COLOR, self.render_area)
        if not self.font_title: return

        menu_title_text = f"{self.player_identifier} Select Skill"
        key_up_name = pygame.key.name(self.key_map['UP']).upper()
        key_down_name = pygame.key.name(self.key_map['DOWN']).upper()
        key_confirm_name = pygame.key.name(self.key_map['CONFIRM']).upper()
        key_cancel_name = pygame.key.name(self.key_map['CANCEL']).upper()
        menu_subtitle_text = f"({key_up_name}/{key_down_name}, {key_confirm_name} to confirm)"
        back_text_str = f"<< Back ({key_cancel_name})"

        title_x = self.render_area.left + int(Style.TITLE_POS[0] * self.scale_factor)
        title_y = self.render_area.top + int(Style.TITLE_POS[1] * self.scale_factor)
        subtitle_x = self.render_area.left + int(Style.SUBTITLE_POS[0] * self.scale_factor)
        # subtitle_y = self.render_area.top + int(Style.SUBTITLE_POS[1] * self.scale_factor) # 舊的

        scaled_line_spacing = int(Style.ITEM_LINE_SPACING * self.scale_factor)

        # 微調副標題Y，使其在主標題下方，且與第一個選項之間有空間
        subtitle_y = title_y + self.font_title.get_height() - scaled_line_spacing // 2 + int(5 * self.scale_factor)


        item_start_x_base = int(Style.ITEM_START_POS[0] * self.scale_factor)
        # item_start_y_base = int(Style.ITEM_START_POS[1] * self.scale_factor) # 舊的

        title_surf = self.font_title.render(menu_title_text, True, Style.TEXT_COLOR)
        surface.blit(title_surf, (title_x, title_y))
        subtitle_surf = self.font_subtitle.render(menu_subtitle_text, True, Style.TEXT_COLOR)
        surface.blit(subtitle_surf, (subtitle_x, subtitle_y ))


        current_item_y = subtitle_y + self.font_subtitle.get_height() + scaled_line_spacing // 2
        for i, option_display_name in enumerate(self.display_options):
            color = Style.PLAYER_COLOR if i == self.selected_index else Style.TEXT_COLOR
            item_text_surf = self.font_item.render(option_display_name, True, color)

            item_x = self.render_area.left + item_start_x_base
            surface.blit(item_text_surf, (item_x, current_item_y))
            current_item_y += scaled_line_spacing

        back_text_surf = self.font_item.render(back_text_str, True, Style.TEXT_COLOR)
        back_rect = back_text_surf.get_rect(
            bottomleft=(self.render_area.left + int(20 * self.scale_factor),
                        self.render_area.bottom - int(20 * self.scale_factor))
        )
        surface.blit(back_text_surf, back_rect)