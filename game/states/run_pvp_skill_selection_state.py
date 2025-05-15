# game/states/run_pvp_skill_selection_state.py
import pygame
from game.states.base_state import BaseState
from game.theme import Style
# from main import GameFlowStateName # GameApp 實例會傳遞 GameFlowStateName 枚舉

DEBUG_MENU_STATE = True

# 這些常數特定於 PvP 技能選擇，所以暫時放在這裡
# 後續可以考慮移到 game/constants.py
P1_MENU_KEYS = {
    'UP': pygame.K_w, 'DOWN': pygame.K_s, 'CONFIRM': pygame.K_e, 'CANCEL': pygame.K_q
}
DEFAULT_MENU_KEYS = { # P2 使用預設按鍵
    'UP': pygame.K_UP, 'DOWN': pygame.K_DOWN, 'CONFIRM': pygame.K_RETURN, 'CANCEL': pygame.K_ESCAPE
}

class RunPvpSkillSelectionState(BaseState):
    def __init__(self, game_app):
        super().__init__(game_app)
        self.skills_options = [ 
            ("Slow Mo", "slowmo"),
            ("Long Paddle", "long_paddle"),
            ("Soul Eater Bug", "soul_eater_bug")
        ]
        self.display_options = [opt[0] for opt in self.skills_options]

        self.p1_selected_index = 0
        self.p2_selected_index = 0
        self.p1_skill_code = None
        self.p2_skill_code = None

        self.current_selecting_player = 1 
        self.selection_confirmed_p1 = False
        self.selection_confirmed_p2 = False

        self.ready_message_timer_start = 0
        self.ready_message_duration = 2000 

        self.font_title = None
        self.font_item = None
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

        scaled_title_font_size = int(Style.TITLE_FONT_SIZE * self.scale_factor) 
        scaled_item_font_size = int(Style.ITEM_FONT_SIZE * self.scale_factor)   
        scaled_large_font_size = int(Style.TITLE_FONT_SIZE * 1.2 * self.scale_factor) 

        self.font_title = Style.get_font(scaled_title_font_size)
        self.font_item = Style.get_font(scaled_item_font_size)
        self.font_info = Style.get_font(scaled_item_font_size) 
        self.font_large_ready = Style.get_font(scaled_large_font_size)

        if DEBUG_MENU_STATE:
            print(f"[State:RunPvpSkillSelection] Entered. Scale: {self.scale_factor:.2f}, RenderArea: {self.render_area}")
            print(f"    Shared data: GameMode='{self.game_app.shared_game_data.get('selected_game_mode')}'")

    def _get_current_key_map(self):
        return P1_MENU_KEYS if self.current_selecting_player == 1 else DEFAULT_MENU_KEYS

    def handle_event(self, event):
        if self.current_selecting_player == 0: 
            return 

        if event.type == pygame.KEYDOWN:
            key_map = self._get_current_key_map()
            current_player_index = self.p1_selected_index if self.current_selecting_player == 1 else self.p2_selected_index

            if event.key == key_map['DOWN']:
                current_player_index = (current_player_index + 1) % len(self.skills_options)
                self.game_app.sound_manager.play_click()
            elif event.key == key_map['UP']:
                current_player_index = (current_player_index - 1 + len(self.skills_options)) % len(self.skills_options)
                self.game_app.sound_manager.play_click()
            elif event.key == key_map['CONFIRM']:
                self.game_app.sound_manager.play_click()
                selected_skill_code = self.skills_options[current_player_index][1]
                if self.current_selecting_player == 1:
                    self.p1_skill_code = selected_skill_code
                    self.selection_confirmed_p1 = True
                    self.current_selecting_player = 2 
                    if DEBUG_MENU_STATE: print(f"[State:RunPvpSkillSelection] P1 selected: {self.p1_skill_code}. Now P2 selecting.")
                elif self.current_selecting_player == 2:
                    self.p2_skill_code = selected_skill_code
                    self.selection_confirmed_p2 = True
                    self.current_selecting_player = 0 
                    self.ready_message_timer_start = pygame.time.get_ticks() 
                    if DEBUG_MENU_STATE: print(f"[State:RunPvpSkillSelection] P2 selected: {self.p2_skill_code}. Both selected.")

            elif event.key == key_map['CANCEL']: 
                self.game_app.sound_manager.play_click()
                if DEBUG_MENU_STATE: print(f"[State:RunPvpSkillSelection] Player {self.current_selecting_player} cancelled. Returning to SelectGameMode.")
                self.request_state_change(self.game_app.GameFlowStateName.SELECT_GAME_MODE)
                return 

            if self.current_selecting_player == 1:
                self.p1_selected_index = current_player_index
            elif self.current_selecting_player == 2: # current_selecting_player could have changed to 0
                if self.selection_confirmed_p1 and not self.selection_confirmed_p2 : # Ensure P2 is still selecting
                     self.p2_selected_index = current_player_index


    def update(self, dt):
        if self.current_selecting_player == 0 and self.p1_skill_code and self.p2_skill_code:
            if pygame.time.get_ticks() - self.ready_message_timer_start >= self.ready_message_duration:
                self.game_app.shared_game_data["p1_selected_skill"] = self.p1_skill_code
                self.game_app.shared_game_data["p2_selected_skill"] = self.p2_skill_code

                data_for_gameplay = {
                    "game_mode": self.game_app.shared_game_data.get("selected_game_mode"), 
                    "input_mode": self.game_app.shared_game_data.get("selected_input_mode"), 
                    "p1_skill": self.p1_skill_code,
                    "p2_skill": self.p2_skill_code
                }
                if DEBUG_MENU_STATE: print(f"[State:RunPvpSkillSelection] Ready message done. Requesting Gameplay state with data: {data_for_gameplay}")
                self.request_state_change(self.game_app.GameFlowStateName.GAMEPLAY, data_for_gameplay)

    def _draw_skill_list(self, surface, player_id_text, area_rect, selected_idx, key_map_for_player):
        menu_title_text = f"{player_id_text} Select Skill"
        key_up_name = pygame.key.name(key_map_for_player['UP']).upper()
        key_down_name = pygame.key.name(key_map_for_player['DOWN']).upper()
        key_confirm_name = pygame.key.name(key_map_for_player['CONFIRM']).upper()
        menu_subtitle_text = f"({key_up_name}/{key_down_name}, {key_confirm_name})"

        title_x = area_rect.left + int(20 * self.scale_factor)
        title_y = area_rect.top + int(20 * self.scale_factor)

        scaled_title_font_height = self.font_title.get_height()
        subtitle_y = title_y + scaled_title_font_height + int(5 * self.scale_factor)
        scaled_subtitle_font_height = self.font_item.get_height() 

        item_start_y_base = subtitle_y + scaled_subtitle_font_height + int(20 * self.scale_factor)
        item_start_x_base = area_rect.left + int(40 * self.scale_factor)
        scaled_line_spacing = int(Style.ITEM_LINE_SPACING * self.scale_factor)

        title_surf = self.font_title.render(menu_title_text, True, Style.TEXT_COLOR)
        surface.blit(title_surf, (title_x, title_y))
        subtitle_surf = self.font_item.render(menu_subtitle_text, True, Style.TEXT_COLOR) 
        surface.blit(subtitle_surf, (title_x, subtitle_y))

        current_item_y = item_start_y_base
        for i, option_display_name in enumerate(self.display_options):
            color = Style.PLAYER_COLOR if i == selected_idx else Style.TEXT_COLOR
            item_text_surf = self.font_item.render(option_display_name, True, color)
            surface.blit(item_text_surf, (item_start_x_base, current_item_y))
            current_item_y += scaled_line_spacing

        key_cancel_name = pygame.key.name(key_map_for_player['CANCEL']).upper()
        back_text_str = f"<< Back ({key_cancel_name})" # Added cancel key display
        back_text_surf = self.font_item.render(back_text_str, True, Style.TEXT_COLOR)
        back_rect = back_text_surf.get_rect(
            bottomleft=(area_rect.left + int(20 * self.scale_factor),
                        area_rect.bottom - int(20 * self.scale_factor))
        )
        surface.blit(back_text_surf, back_rect)


    def render(self, surface):
        pygame.draw.rect(surface, Style.BACKGROUND_COLOR, self.render_area)
        if not self.font_title or not self.font_item: return

        area_width = self.render_area.width
        area_height = self.render_area.height
        area_left = self.render_area.left
        area_top = self.render_area.top

        p1_skill_select_sub_area = pygame.Rect(
            area_left, area_top,
            area_width // 2, area_height
        )
        p2_skill_select_sub_area = pygame.Rect(
            area_left + area_width // 2, area_top,
            area_width // 2, area_height
        )

        divider_color = (100, 100, 100)
        scaled_divider_thickness = max(1, int(2 * self.scale_factor))
        divider_x_abs = area_left + area_width // 2
        pygame.draw.line(surface, divider_color,
                         (divider_x_abs, area_top),
                         (divider_x_abs, area_top + area_height),
                         scaled_divider_thickness)

        if self.current_selecting_player == 1: 
            self._draw_skill_list(surface, "Player 1", p1_skill_select_sub_area, self.p1_selected_index, P1_MENU_KEYS)
            pygame.draw.rect(surface, Style.BACKGROUND_COLOR, p2_skill_select_sub_area) 
            if self.font_info:
                wait_text = self.font_info.render("Player 2 Waiting...", True, Style.TEXT_COLOR)
                wait_rect = wait_text.get_rect(center=p2_skill_select_sub_area.center)
                surface.blit(wait_text, wait_rect)

        elif self.current_selecting_player == 2: 
            pygame.draw.rect(surface, Style.BACKGROUND_COLOR, p1_skill_select_sub_area) 
            if self.p1_skill_code and self.font_info:
                p1_skill_display_name = "Unknown"
                for name, code in self.skills_options: # Find display name for p1_skill_code
                    if code == self.p1_skill_code:
                        p1_skill_display_name = name
                        break
                p1_confirm_text = self.font_info.render(f"P1: {p1_skill_display_name}", True, Style.PLAYER_COLOR)
                p1_confirm_rect = p1_confirm_text.get_rect(center=p1_skill_select_sub_area.center)
                surface.blit(p1_confirm_text, p1_confirm_rect)

            self._draw_skill_list(surface, "Player 2", p2_skill_select_sub_area, self.p2_selected_index, DEFAULT_MENU_KEYS)

        elif self.current_selecting_player == 0: 
            if self.p1_skill_code and self.p2_skill_code and self.font_large_ready:
                pygame.draw.rect(surface, Style.BACKGROUND_COLOR, self.render_area)
                ready_text_str = "Players Ready! Starting..."
                ready_text_render = self.font_large_ready.render(ready_text_str, True, Style.TEXT_COLOR)
                ready_rect = ready_text_render.get_rect(center=self.render_area.center)
                surface.blit(ready_text_render, ready_rect)