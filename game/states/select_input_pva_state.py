# game/states/select_input_pva_state.py
import pygame
from game.states.base_state import BaseState
from game.theme import Style

DEBUG_MENU_STATE = False

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
        self.item_rects = []
        self.hover_scale_factor = 1.1 # <--- 新增：懸停縮放比例
        if DEBUG_MENU_STATE: print(f"[State:SelectInputPva] Initialized.")

    def on_enter(self, previous_state_data=None):
        super().on_enter(previous_state_data)
        self.selected_index = 0
        self.item_rects = [None] * len(self.options)

        scaled_title_font_size = int(Style.TITLE_FONT_SIZE * self.scale_factor)
        scaled_subtitle_font_size = int(Style.SUBTITLE_FONT_SIZE * self.scale_factor)
        # Item font size will be scaled per item for hover effect, so get base scaled size here
        self.base_scaled_item_font_size = int(Style.ITEM_FONT_SIZE * self.scale_factor)


        self.font_title = Style.get_font(scaled_title_font_size)
        self.font_subtitle = Style.get_font(scaled_subtitle_font_size)
        # self.font_item is now created on-the-fly in render if needed, or use a base one
        self.font_item = Style.get_font(self.base_scaled_item_font_size)


        if DEBUG_MENU_STATE: print(f"[State:SelectInputPva] Entered. Scale: {self.scale_factor:.2f}, RenderArea: {self.render_area}")
        if DEBUG_MENU_STATE: print(f"    Game mode from previous state: {self.game_app.shared_game_data.get('selected_game_mode')}")

    def handle_event(self, event):
        if event.type == pygame.MOUSEMOTION:
            for i, rect in enumerate(self.item_rects):
                if rect and rect.collidepoint(event.pos):
                    if self.selected_index != i:
                        self.selected_index = i
                    break
        elif event.type == pygame.MOUSEBUTTONDOWN:
            if event.button == 1: # 左鍵點擊
                for i, rect in enumerate(self.item_rects):
                    if rect and rect.collidepoint(event.pos):
                        self.selected_index = i
                        self.game_app.sound_manager.play_click()
                        selected_input_mode_value = self.options[self.selected_index][1]
                        if DEBUG_MENU_STATE: print(f"[State:SelectInputPva] Mouse selected input: {selected_input_mode_value}")

                        self.game_app.shared_game_data["selected_input_mode"] = selected_input_mode_value
                        self.request_state_change(self.game_app.GameFlowStateName.SELECT_SKILL_PVA)
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
                selected_input_mode_value = self.options[self.selected_index][1]
                if DEBUG_MENU_STATE: print(f"[State:SelectInputPva] Keyboard selected input: {selected_input_mode_value}")

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
        if not self.font_title or not self.font_item or not self.font_subtitle:
            return

        title_x = self.render_area.left + int(Style.TITLE_POS[0] * self.scale_factor)
        title_y = self.render_area.top + int(Style.TITLE_POS[1] * self.scale_factor)
        subtitle_x = self.render_area.left + int(Style.SUBTITLE_POS[0] * self.scale_factor)
        subtitle_y = self.render_area.top + int(Style.SUBTITLE_POS[1] * self.scale_factor)
        item_start_x_base_abs = self.render_area.left + int(Style.ITEM_START_POS[0] * self.scale_factor)
        item_start_y_base_abs = self.render_area.top + int(Style.ITEM_START_POS[1] * self.scale_factor)
        scaled_line_spacing = int(Style.ITEM_LINE_SPACING * self.scale_factor)

        title_surf = self.font_title.render("Select Controller (PvA)", True, Style.TEXT_COLOR)
        surface.blit(title_surf, (title_x, title_y))

        subtitle_text_new = "(UP/DOWN/Mouse, ENTER/Click to confirm, ESC to back)"
        subtitle_surf = self.font_subtitle.render(subtitle_text_new, True, Style.TEXT_COLOR)
        surface.blit(subtitle_surf, (subtitle_x, subtitle_y))

        current_item_y = item_start_y_base_abs
        for i, option_text in enumerate(self.display_options):
            is_selected = (i == self.selected_index)
            color = Style.PLAYER_COLOR if is_selected else Style.TEXT_COLOR
            
            # Render original text surface for rect calculation and non-hovered state
            original_text_surf = self.font_item.render(option_text, True, color)
            original_rect = original_text_surf.get_rect(topleft=(item_start_x_base_abs, current_item_y))
            
            # Store the original rect for mouse collision
            if i < len(self.item_rects):
                self.item_rects[i] = original_rect

            if is_selected:
                # Calculate scaled dimensions
                scaled_width = int(original_rect.width * self.hover_scale_factor)
                scaled_height = int(original_rect.height * self.hover_scale_factor)
                
                # Scale the surface (which already has the correct color)
                # Ensure the surface to scale isn't zero-width or zero-height
                if original_rect.width > 0 and original_rect.height > 0 :
                    scaled_text_surf = pygame.transform.smoothscale(original_text_surf, (scaled_width, scaled_height))
                    scaled_rect = scaled_text_surf.get_rect(center=original_rect.center)
                    surface.blit(scaled_text_surf, scaled_rect)
                else: # Fallback if original surface is invalid for scaling
                    surface.blit(original_text_surf, original_rect)
            else:
                surface.blit(original_text_surf, original_rect)
            
            current_item_y += scaled_line_spacing