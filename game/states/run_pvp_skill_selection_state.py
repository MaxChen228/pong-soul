# game/states/run_pvp_skill_selection_state.py
import pygame
from game.states.base_state import BaseState
from game.theme import Style
from game.constants import P1_MENU_CONTROLS, DEFAULT_MENU_CONTROLS

DEBUG_MENU_STATE = False

class RunPvpSkillSelectionState(BaseState):
    def __init__(self, game_app):
        super().__init__(game_app)
        self.skills_options = [
            ("Platinum Star: The World", "slowmo"),
            ("Infinite Aegis: Requiem", "long_paddle"),
            ("Nether Bug: Soul Eater", "soul_eater_bug"),
            ("Final Purgatory: Pure Land", "purgatory_domain")
        ]
        self.display_options = [opt[0] for opt in self.skills_options]

        self.p1_selected_index = 0
        self.p2_selected_index = 0
        self.p1_skill_code = None
        self.p2_skill_code = None

        self.p1_item_rects = []
        self.p2_item_rects = []
        self.hover_scale_factor = 1.1 # <--- 新增：懸停縮放比例

        self.current_selecting_player = 1
        self.selection_confirmed_p1 = False
        self.selection_confirmed_p2 = False

        self.ready_message_timer_start = 0
        self.ready_message_duration = 2000

        self.font_title = None
        self.font_item = None # 將在 on_enter 中創建
        self.font_info = None
        self.font_large_ready = None

        if DEBUG_MENU_STATE: print(f"[State:RunPvpSkillSelection] Initialized.")

    def on_enter(self, previous_state_data=None):
        super().on_enter(previous_state_data)
        self.p1_selected_index = 0
        self.p2_selected_index = 0
        self.p1_skill_code = None
        self.p2_skill_code = None
        self.current_selecting_player = 1
        self.selection_confirmed_p1 = False
        self.selection_confirmed_p2 = False
        self.ready_message_timer_start = 0

        num_options = len(self.skills_options)
        self.p1_item_rects = [None] * num_options
        self.p2_item_rects = [None] * num_options

        scaled_title_font_size = int(Style.TITLE_FONT_SIZE * self.scale_factor)
        self.base_scaled_item_font_size = int(Style.ITEM_FONT_SIZE * self.scale_factor) # <--- 基礎選項字體大小
        # For font_info, if it's same style as item, use base_scaled_item_font_size
        # For font_large_ready, it has its own scaling logic based on TITLE_FONT_SIZE
        scaled_large_font_size = int(Style.TITLE_FONT_SIZE * 1.2 * self.scale_factor)

        self.font_title = Style.get_font(scaled_title_font_size)
        self.font_item = Style.get_font(self.base_scaled_item_font_size) # <--- 標準選項字體
        self.font_info = Style.get_font(self.base_scaled_item_font_size) # Assuming info font is same as item
        self.font_large_ready = Style.get_font(scaled_large_font_size)

        if DEBUG_MENU_STATE:
            print(f"[State:RunPvpSkillSelection] Entered. Scale: {self.scale_factor:.2f}, RenderArea: {self.render_area}")
            print(f"    Shared data: GameMode='{self.game_app.shared_game_data.get('selected_game_mode')}'")

    def _get_current_key_map(self):
        return P1_MENU_CONTROLS if self.current_selecting_player == 1 else DEFAULT_MENU_CONTROLS

    def _confirm_current_player_selection(self):
        self.game_app.sound_manager.play_click()
        current_player_index = self.p1_selected_index if self.current_selecting_player == 1 else self.p2_selected_index
        selected_skill_code = self.skills_options[current_player_index][1]

        if self.current_selecting_player == 1:
            self.p1_skill_code = selected_skill_code
            self.selection_confirmed_p1 = True
            self.current_selecting_player = 2
            if DEBUG_MENU_STATE: print(f"[State:RunPvpSkillSelection] P1 confirmed: {self.p1_skill_code}. Now P2 selecting.")
        elif self.current_selecting_player == 2:
            self.p2_skill_code = selected_skill_code
            self.selection_confirmed_p2 = True
            self.current_selecting_player = 0
            self.ready_message_timer_start = pygame.time.get_ticks()
            if DEBUG_MENU_STATE: print(f"[State:RunPvpSkillSelection] P2 confirmed: {self.p2_skill_code}. Both selected.")

    def handle_event(self, event):
        if self.current_selecting_player == 0:
            return

        if event.type == pygame.MOUSEMOTION:
            mouse_pos = event.pos
            active_area = None
            item_rects_to_check = None
            current_player_original_index = -1
            updated_player_index = -1

            if self.current_selecting_player == 1:
                active_area = getattr(self, 'p1_skill_select_sub_area_on_surface', None) # getattr for safety before render
                item_rects_to_check = self.p1_item_rects
                current_player_original_index = self.p1_selected_index
            elif self.current_selecting_player == 2:
                active_area = getattr(self, 'p2_skill_select_sub_area_on_surface', None)
                item_rects_to_check = self.p2_item_rects
                current_player_original_index = self.p2_selected_index

            if active_area and active_area.collidepoint(mouse_pos) and item_rects_to_check:
                for i, rect in enumerate(item_rects_to_check):
                    if rect and rect.collidepoint(mouse_pos):
                        if current_player_original_index != i:
                            updated_player_index = i
                        break
                if updated_player_index != -1:
                    if self.current_selecting_player == 1:
                        self.p1_selected_index = updated_player_index
                    elif self.current_selecting_player == 2:
                        self.p2_selected_index = updated_player_index

        elif event.type == pygame.MOUSEBUTTONDOWN:
            if event.button == 1:
                mouse_pos = event.pos
                active_area = None
                item_rects_to_check = None
                clicked_valid_item = False

                if self.current_selecting_player == 1:
                    active_area = getattr(self, 'p1_skill_select_sub_area_on_surface', None)
                    item_rects_to_check = self.p1_item_rects
                elif self.current_selecting_player == 2:
                    active_area = getattr(self, 'p2_skill_select_sub_area_on_surface', None)
                    item_rects_to_check = self.p2_item_rects
                
                if active_area and active_area.collidepoint(mouse_pos) and item_rects_to_check:
                    for i, rect in enumerate(item_rects_to_check):
                        if rect and rect.collidepoint(mouse_pos):
                            if self.current_selecting_player == 1:
                                self.p1_selected_index = i
                            elif self.current_selecting_player == 2:
                                self.p2_selected_index = i
                            clicked_valid_item = True
                            break
                    if clicked_valid_item:
                        self._confirm_current_player_selection()
                        return

        if event.type == pygame.KEYDOWN:
            key_map = self._get_current_key_map()
            current_player_index_ref = self.p1_selected_index if self.current_selecting_player == 1 else self.p2_selected_index
            new_index = current_player_index_ref

            if event.key == key_map['DOWN']:
                new_index = (current_player_index_ref + 1) % len(self.skills_options)
                self.game_app.sound_manager.play_click()
            elif event.key == key_map['UP']:
                new_index = (current_player_index_ref - 1 + len(self.skills_options)) % len(self.skills_options)
                self.game_app.sound_manager.play_click()
            elif event.key == key_map['CONFIRM']:
                self._confirm_current_player_selection()
            elif event.key == key_map['CANCEL']:
                self.game_app.sound_manager.play_click()
                if DEBUG_MENU_STATE: print(f"[State:RunPvpSkillSelection] Player {self.current_selecting_player} cancelled. Returning to SelectGameMode.")
                self.request_state_change(self.game_app.GameFlowStateName.SELECT_GAME_MODE)
                return

            if self.current_selecting_player == 1:
                self.p1_selected_index = new_index
            elif self.current_selecting_player == 2:
                self.p2_selected_index = new_index

    def update(self, dt):
        if self.current_selecting_player == 0 and self.p1_skill_code and self.p2_skill_code:
            if pygame.time.get_ticks() - self.ready_message_timer_start >= self.ready_message_duration:
                self.game_app.shared_game_data["p1_selected_skill"] = self.p1_skill_code
                self.game_app.shared_game_data["p2_selected_skill"] = self.p2_skill_code
                data_for_gameplay = {
                    "game_mode": self.game_app.shared_game_data.get("selected_game_mode"),
                    "input_mode": "keyboard", # PvP is always keyboard for gameplay
                    "p1_skill": self.p1_skill_code,
                    "p2_skill": self.p2_skill_code
                }
                if DEBUG_MENU_STATE: print(f"[State:RunPvpSkillSelection] Ready message done. Requesting Gameplay state with data: {data_for_gameplay}")
                self.request_state_change(self.game_app.GameFlowStateName.GAMEPLAY, data_for_gameplay)

    def _draw_skill_list(self, surface, player_id_text, area_rect_on_surface, selected_idx, key_map_for_player, item_rects_list_to_update):
        # Ensure fonts are loaded, especially self.font_item used for options
        if not self.font_title or not self.font_item: # self.font_info may not be used here directly
            return

        menu_title_text = f"{player_id_text} Select Skill"
        key_up_name = pygame.key.name(key_map_for_player['UP']).upper()
        key_down_name = pygame.key.name(key_map_for_player['DOWN']).upper()
        key_confirm_name = pygame.key.name(key_map_for_player['CONFIRM']).upper()
        menu_subtitle_text = f"({key_up_name}/{key_down_name}/Mouse, {key_confirm_name}/Click)"

        title_x_abs = area_rect_on_surface.left + int(20 * self.scale_factor)
        title_y_abs = area_rect_on_surface.top + int(20 * self.scale_factor)

        scaled_title_font_height = self.font_title.get_height()
        subtitle_y_abs = title_y_abs + scaled_title_font_height + int(5 * self.scale_factor)
        # Subtitle uses font_item here, so get its height
        scaled_subtitle_font_height = self.font_item.get_height()

        item_start_y_base_abs = subtitle_y_abs + scaled_subtitle_font_height + int(20 * self.scale_factor)
        item_start_x_base_abs = area_rect_on_surface.left + int(40 * self.scale_factor)
        scaled_line_spacing = int(Style.ITEM_LINE_SPACING * self.scale_factor)

        title_surf = self.font_title.render(menu_title_text, True, Style.TEXT_COLOR)
        surface.blit(title_surf, (title_x_abs, title_y_abs))
        subtitle_surf = self.font_item.render(menu_subtitle_text, True, Style.TEXT_COLOR)
        surface.blit(subtitle_surf, (title_x_abs, subtitle_y_abs))

        current_item_y_abs = item_start_y_base_abs
        for i in range(len(item_rects_list_to_update)): # Clear previous rects
            item_rects_list_to_update[i] = None

        for i, option_display_name in enumerate(self.display_options):
            is_option_selected = (i == selected_idx)
            color = Style.PLAYER_COLOR if is_option_selected else Style.TEXT_COLOR
            
            original_text_surf = self.font_item.render(option_display_name, True, color)
            original_rect = original_text_surf.get_rect(topleft=(item_start_x_base_abs, current_item_y_abs))
            
            if i < len(item_rects_list_to_update):
                item_rects_list_to_update[i] = original_rect

            if is_option_selected:
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

        key_cancel_name = pygame.key.name(key_map_for_player['CANCEL']).upper()
        back_text_str = f"<< Back ({key_cancel_name})"
        back_text_surf = self.font_item.render(back_text_str, True, Style.TEXT_COLOR)
        back_rect_abs = back_text_surf.get_rect(
            bottomleft=(area_rect_on_surface.left + int(20 * self.scale_factor),
                        area_rect_on_surface.bottom - int(20 * self.scale_factor))
        )
        surface.blit(back_text_surf, back_rect_abs)

    def render(self, surface):
        pygame.draw.rect(surface, Style.BACKGROUND_COLOR, self.render_area)
        if not self.font_title or not self.font_item or not self.font_info or not self.font_large_ready:
            return

        area_width_on_surface = self.render_area.width
        area_height_on_surface = self.render_area.height
        area_left_on_surface = self.render_area.left
        area_top_on_surface = self.render_area.top

        self.p1_skill_select_sub_area_on_surface = pygame.Rect(
            area_left_on_surface, area_top_on_surface,
            area_width_on_surface // 2, area_height_on_surface
        )
        self.p2_skill_select_sub_area_on_surface = pygame.Rect(
            area_left_on_surface + area_width_on_surface // 2, area_top_on_surface,
            area_width_on_surface // 2, area_height_on_surface
        )

        divider_color = (100, 100, 100)
        scaled_divider_thickness = max(1, int(2 * self.scale_factor))
        divider_x_abs = area_left_on_surface + area_width_on_surface // 2
        pygame.draw.line(surface, divider_color,
                         (divider_x_abs, area_top_on_surface),
                         (divider_x_abs, area_top_on_surface + area_height_on_surface),
                         scaled_divider_thickness)

        if self.current_selecting_player == 1:
            self._draw_skill_list(surface, "Player 1", self.p1_skill_select_sub_area_on_surface, self.p1_selected_index, P1_MENU_CONTROLS, self.p1_item_rects)
            pygame.draw.rect(surface, Style.BACKGROUND_COLOR, self.p2_skill_select_sub_area_on_surface)
            if self.font_info:
                wait_text = self.font_info.render("Player 2 Waiting...", True, Style.TEXT_COLOR)
                wait_rect = wait_text.get_rect(center=self.p2_skill_select_sub_area_on_surface.center)
                surface.blit(wait_text, wait_rect)

        elif self.current_selecting_player == 2:
            pygame.draw.rect(surface, Style.BACKGROUND_COLOR, self.p1_skill_select_sub_area_on_surface)
            if self.p1_skill_code and self.font_info:
                p1_skill_display_name = "Unknown"
                for name, code in self.skills_options:
                    if code == self.p1_skill_code:
                        p1_skill_display_name = name
                        break
                p1_confirm_text = self.font_info.render(f"P1: {p1_skill_display_name}", True, Style.PLAYER_COLOR)
                p1_confirm_rect = p1_confirm_text.get_rect(center=self.p1_skill_select_sub_area_on_surface.center)
                surface.blit(p1_confirm_text, p1_confirm_rect)
            self._draw_skill_list(surface, "Player 2", self.p2_skill_select_sub_area_on_surface, self.p2_selected_index, DEFAULT_MENU_CONTROLS, self.p2_item_rects)

        elif self.current_selecting_player == 0:
            if self.p1_skill_code and self.p2_skill_code and self.font_large_ready:
                pygame.draw.rect(surface, Style.BACKGROUND_COLOR, self.render_area)
                ready_text_str = "Players Ready! Starting..."
                ready_text_render = self.font_large_ready.render(ready_text_str, True, Style.TEXT_COLOR)
                ready_rect = ready_text_render.get_rect(center=self.render_area.center)
                surface.blit(ready_text_render, ready_rect)