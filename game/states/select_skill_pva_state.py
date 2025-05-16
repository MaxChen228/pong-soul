# game/states/select_skill_pva_state.py
import pygame
from game.states.base_state import BaseState
from game.theme import Style
from game.constants import DEFAULT_MENU_CONTROLS

DEBUG_MENU_STATE = False

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
        self.item_rects = []
        self.hover_scale_factor = 1.1 # <--- 新增：懸停縮放比例

        self.key_map = DEFAULT_MENU_CONTROLS
        self.player_identifier = "Player"

        if DEBUG_MENU_STATE: print(f"[State:SelectSkillPva] Initialized.")

    def on_enter(self, previous_state_data=None):
        super().on_enter(previous_state_data)
        self.selected_index = 0
        self.item_rects = [None] * len(self.skills_options)

        scaled_title_font_size = int(Style.TITLE_FONT_SIZE * self.scale_factor)
        scaled_subtitle_font_size = int(Style.SUBTITLE_FONT_SIZE * self.scale_factor)
        self.base_scaled_item_font_size = int(Style.ITEM_FONT_SIZE * self.scale_factor) # <--- 基礎選項字體大小

        self.font_title = Style.get_font(scaled_title_font_size)
        self.font_subtitle = Style.get_font(scaled_subtitle_font_size)
        self.font_item = Style.get_font(self.base_scaled_item_font_size) # <--- 標準選項字體

        if DEBUG_MENU_STATE:
            print(f"[State:SelectSkillPva] Entered. Scale: {self.scale_factor:.2f}, RenderArea: {self.render_area}")
            print(f"    Shared data: GameMode='{self.game_app.shared_game_data.get('selected_game_mode')}', Input='{self.game_app.shared_game_data.get('selected_input_mode')}'")

    def _confirm_selection(self):
        self.game_app.sound_manager.play_click()
        selected_skill_code = self.skills_options[self.selected_index][1]
        if DEBUG_MENU_STATE: print(f"[State:SelectSkillPva] Confirmed skill: {selected_skill_code}")

        self.game_app.shared_game_data["p1_selected_skill"] = selected_skill_code
        self.game_app.shared_game_data["p2_selected_skill"] = None

        data_for_level_selection = {
            "game_mode": self.game_app.shared_game_data.get("selected_game_mode"),
            "input_mode": self.game_app.shared_game_data.get("selected_input_mode"),
            "p1_skill": selected_skill_code
        }
        if DEBUG_MENU_STATE: print(f"  Transitioning to LevelSelectionPva with data: {data_for_level_selection}")
        self.request_state_change(self.game_app.GameFlowStateName.SELECT_LEVEL_PVA, data_for_level_selection)

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
                        self._confirm_selection()
                        return

        if event.type == pygame.KEYDOWN:
            if event.key == self.key_map['DOWN']:
                self.selected_index = (self.selected_index + 1) % len(self.skills_options)
                self.game_app.sound_manager.play_click()
            elif event.key == self.key_map['UP']:
                self.selected_index = (self.selected_index - 1 + len(self.skills_options)) % len(self.skills_options)
                self.game_app.sound_manager.play_click()
            elif event.key == self.key_map['CONFIRM']:
                self._confirm_selection()
            elif event.key == self.key_map['CANCEL']:
                self.game_app.sound_manager.play_click()
                if DEBUG_MENU_STATE: print(f"[State:SelectSkillPva] ESC pressed, returning to SelectInputPva.")
                self.request_state_change(self.game_app.GameFlowStateName.SELECT_INPUT_PVA)

    def update(self, dt):
        pass

    def render(self, surface):
        pygame.draw.rect(surface, Style.BACKGROUND_COLOR, self.render_area)
        if not self.font_title or not self.font_subtitle or not self.font_item:
            return

        menu_title_text = f"{self.player_identifier} Select Skill"
        key_up_name = pygame.key.name(self.key_map['UP']).upper()
        key_down_name = pygame.key.name(self.key_map['DOWN']).upper()
        key_confirm_name = pygame.key.name(self.key_map['CONFIRM']).upper()
        key_cancel_name = pygame.key.name(self.key_map['CANCEL']).upper()
        
        menu_subtitle_text = f"({key_up_name}/{key_down_name}/Mouse, {key_confirm_name}/Click to confirm)"
        back_text_str = f"<< Back ({key_cancel_name})"

        title_x = self.render_area.left + int(Style.TITLE_POS[0] * self.scale_factor)
        title_y = self.render_area.top + int(Style.TITLE_POS[1] * self.scale_factor)
        subtitle_x = self.render_area.left + int(Style.SUBTITLE_POS[0] * self.scale_factor)
        
        scaled_line_spacing = int(Style.ITEM_LINE_SPACING * self.scale_factor)
        subtitle_y = title_y + self.font_title.get_height() - scaled_line_spacing // 2 + int(5 * self.scale_factor)

        title_surf = self.font_title.render(menu_title_text, True, Style.TEXT_COLOR)
        surface.blit(title_surf, (title_x, title_y))
        subtitle_surf = self.font_subtitle.render(menu_subtitle_text, True, Style.TEXT_COLOR)
        surface.blit(subtitle_surf, (subtitle_x, subtitle_y ))

        current_item_y_abs = subtitle_y + self.font_subtitle.get_height() + scaled_line_spacing // 2
        item_start_x_base_abs = self.render_area.left + int(Style.ITEM_START_POS[0] * self.scale_factor)

        for i, option_display_name in enumerate(self.display_options):
            is_selected = (i == self.selected_index)
            color = Style.PLAYER_COLOR if is_selected else Style.TEXT_COLOR
            
            original_text_surf = self.font_item.render(option_display_name, True, color)
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

        back_text_surf = self.font_item.render(back_text_str, True, Style.TEXT_COLOR)
        back_rect = back_text_surf.get_rect(
            bottomleft=(self.render_area.left + int(20 * self.scale_factor),
                        self.render_area.bottom - int(20 * self.scale_factor))
        )
        surface.blit(back_text_surf, back_rect)