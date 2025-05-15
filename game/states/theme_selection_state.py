# game/states/theme_selection_state.py
import pygame
from game.states.base_state import BaseState
from game.theme import Style, get_available_theme_names
from game.settings import GameSettings

DEBUG_THEME_SELECT_STATE = False

class ThemeSelectionState(BaseState):
    def __init__(self, game_app):
        super().__init__(game_app)
        self.available_themes = get_available_theme_names()
        self.selected_index = 0
        self.item_rects = []
        self.hover_scale_factor = 1.1 # <--- 新增：懸停縮放比例

        self.font_title = None
        self.font_item = None # 將在 on_enter 中創建
        self.font_subtitle = None

        self.previous_state_name = self.game_app.GameFlowStateName.SETTINGS_MENU

        try:
            current_theme_name = GameSettings.ACTIVE_THEME_NAME
            if current_theme_name in self.available_themes:
                self.selected_index = self.available_themes.index(current_theme_name)
        except Exception as e:
            if DEBUG_THEME_SELECT_STATE:
                print(f"[State:ThemeSelection] Error getting initial theme index: {e}")
            self.selected_index = 0

        if DEBUG_THEME_SELECT_STATE: print(f"[State:ThemeSelection] Initialized. Themes: {self.available_themes}")

    def on_enter(self, previous_state_data=None):
        super().on_enter(previous_state_data)
        
        self.available_themes = get_available_theme_names()
        try:
            current_theme_name = GameSettings.ACTIVE_THEME_NAME
            if current_theme_name in self.available_themes:
                self.selected_index = self.available_themes.index(current_theme_name)
            else: 
                self.selected_index = 0
                if self.available_themes: 
                     GameSettings.set_active_theme(self.available_themes[0])
        except Exception as e:
            if DEBUG_THEME_SELECT_STATE:
                print(f"[State:ThemeSelection] Error re-evaluating theme index on enter: {e}")
            self.selected_index = 0
            if self.available_themes: GameSettings.set_active_theme(self.available_themes[0])

        self.item_rects = [None] * len(self.available_themes)
        self.previous_state_name = self.persistent_data.get(
            "previous_state_for_theme_selection", 
            self.game_app.GameFlowStateName.SETTINGS_MENU 
        )

        scaled_title_font_size = int(Style.TITLE_FONT_SIZE * self.scale_factor)
        self.base_scaled_item_font_size = int(Style.ITEM_FONT_SIZE * self.scale_factor) # <--- 基礎選項字體大小
        scaled_subtitle_font_size = int(Style.SUBTITLE_FONT_SIZE * self.scale_factor)

        self.font_title = Style.get_font(scaled_title_font_size)
        self.font_item = Style.get_font(self.base_scaled_item_font_size) # <--- 標準選項字體
        self.font_subtitle = Style.get_font(scaled_subtitle_font_size)

        if DEBUG_THEME_SELECT_STATE:
            print(f"[State:ThemeSelection] Entered. Scale: {self.scale_factor:.2f}, RenderArea: {self.render_area}")
            print(f"    Current selected theme index: {self.selected_index} ('{self.available_themes[self.selected_index] if self.available_themes and 0 <= self.selected_index < len(self.available_themes) else 'N/A'}')")
            print(f"    Previous state to return to: {self.previous_state_name}")

    def handle_event(self, event):
        if not self.available_themes: 
            if event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE:
                self.game_app.sound_manager.play_click()
                self.request_state_change(self.previous_state_name)
            return

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
                        selected_theme_name = self.available_themes[self.selected_index]
                        
                        if DEBUG_THEME_SELECT_STATE:
                            print(f"[State:ThemeSelection] Mouse clicked, applying theme: {selected_theme_name}")
                        
                        GameSettings.set_active_theme(selected_theme_name)
                        # After setting theme, Style might change, so next state's on_enter will get new fonts
                        self.request_state_change(self.previous_state_name)
                        return

        if event.type == pygame.KEYDOWN:
            if event.key == pygame.K_DOWN:
                self.selected_index = (self.selected_index + 1) % len(self.available_themes)
                self.game_app.sound_manager.play_click()
            elif event.key == pygame.K_UP:
                self.selected_index = (self.selected_index - 1 + len(self.available_themes)) % len(self.available_themes)
                self.game_app.sound_manager.play_click()
            elif event.key == pygame.K_RETURN: 
                self.game_app.sound_manager.play_click()
                selected_theme_name = self.available_themes[self.selected_index]
                
                if DEBUG_THEME_SELECT_STATE:
                    print(f"[State:ThemeSelection] Enter key, applying theme: {selected_theme_name}")
                
                GameSettings.set_active_theme(selected_theme_name)
                self.request_state_change(self.previous_state_name)

            elif event.key == pygame.K_ESCAPE: 
                self.game_app.sound_manager.play_click()
                if DEBUG_THEME_SELECT_STATE: print(f"[State:ThemeSelection] ESC pressed, returning to {self.previous_state_name}.")
                self.request_state_change(self.previous_state_name)

    def update(self, dt):
        pass

    def render(self, surface):
        pygame.draw.rect(surface, Style.BACKGROUND_COLOR, self.render_area) 
        if not self.font_title or not self.font_item or not self.font_subtitle:
            return

        title_x = self.render_area.left + int(Style.TITLE_POS[0] * self.scale_factor)
        title_y = self.render_area.top + int(Style.TITLE_POS[1] * self.scale_factor)
        subtitle_x = self.render_area.left + int(Style.SUBTITLE_POS[0] * self.scale_factor)
        subtitle_y = title_y + self.font_title.get_height() + int(5 * self.scale_factor) # Position below title

        item_start_x_base_abs = self.render_area.left + int(Style.ITEM_START_POS[0] * self.scale_factor)
        # Adjust item_start_y to be below subtitle
        item_start_y_base_abs = subtitle_y + self.font_subtitle.get_height() + int(Style.ITEM_LINE_SPACING * 0.5 * self.scale_factor)
        scaled_line_spacing = int(Style.ITEM_LINE_SPACING * self.scale_factor)

        title_surf = self.font_title.render("Select Theme", True, Style.TEXT_COLOR)
        surface.blit(title_surf, (title_x, title_y))
        
        subtitle_text = "(UP/DOWN/Mouse, ENTER/Click to apply, ESC to back)"
        subtitle_surf = self.font_subtitle.render(subtitle_text, True, Style.TEXT_COLOR)
        surface.blit(subtitle_surf, (subtitle_x, subtitle_y))

        if not self.available_themes:
            no_themes_text = self.font_item.render("No themes available.", True, Style.TEXT_COLOR)
            text_rect = no_themes_text.get_rect(center=self.render_area.center)
            surface.blit(no_themes_text, text_rect)
            return

        current_item_y_abs = item_start_y_base_abs
        for i, theme_name in enumerate(self.available_themes):
            is_selected = (i == self.selected_index)
            is_currently_active_theme = (theme_name == GameSettings.ACTIVE_THEME_NAME)
            
            display_name = theme_name
            if is_currently_active_theme:
                display_name += " (Active)" 
            
            color = Style.PLAYER_COLOR if is_selected else Style.TEXT_COLOR
            
            original_text_surf = self.font_item.render(display_name, True, color)
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