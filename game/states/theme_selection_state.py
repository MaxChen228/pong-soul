# game/states/theme_selection_state.py
import pygame
import math
from game.states.base_state import BaseState
from game.theme import Style, get_available_theme_names, ALL_THEMES
from game.settings import GameSettings

DEBUG_THEME_SELECT_STATE = False

class ThemeSelectionState(BaseState):
    def __init__(self, game_app):
        super().__init__(game_app)
        self.available_themes = get_available_theme_names()
        self.selected_index = 0
        self.item_rects = []
        self.hover_scale_factor = 1.1

        self.font_title = None
        self.font_item = None
        self.font_subtitle = None

        self.previous_state_name = self.game_app.GameFlowStateName.SETTINGS_MENU

        self.num_columns = 2
        
        self.swatch_size_px = 0
        self.swatch_spacing_px = 0
        self.swatches_per_theme = 5 
        # self.swatch_cols = 2 # 不再需要固定為2欄，改為單行橫向排列

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
        self.base_scaled_item_font_size = int(Style.ITEM_FONT_SIZE * self.scale_factor)
        scaled_subtitle_font_size = int(Style.SUBTITLE_FONT_SIZE * self.scale_factor)

        self.font_title = Style.get_font(scaled_title_font_size)
        self.font_item = Style.get_font(self.base_scaled_item_font_size)
        self.font_subtitle = Style.get_font(scaled_subtitle_font_size)

        self.swatch_size_px = int(15 * self.scale_factor) 
        self.swatch_spacing_px = int(5 * self.scale_factor) 

        if DEBUG_THEME_SELECT_STATE:
            print(f"[State:ThemeSelection] Entered. Scale: {self.scale_factor:.2f}, RenderArea: {self.render_area}")
            print(f"    Swatch size: {self.swatch_size_px}px, Swatch spacing: {self.swatch_spacing_px}px")
            print(f"    Current selected theme index: {self.selected_index} ('{self.available_themes[self.selected_index] if self.available_themes and 0 <= self.selected_index < len(self.available_themes) else 'N/A'}')")
            print(f"    Previous state to return to: {self.previous_state_name}")

    def handle_event(self, event):
        if not self.available_themes:
            if event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE:
                self.game_app.sound_manager.play_click()
                self.request_state_change(self.previous_state_name)
            return

        num_themes = len(self.available_themes)
        if num_themes == 0: return

        items_per_column = math.ceil(num_themes / self.num_columns)

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
                        self.request_state_change(self.previous_state_name)
                        return

        if event.type == pygame.KEYDOWN:
            current_row = self.selected_index % items_per_column
            current_col = self.selected_index // items_per_column

            if event.key == pygame.K_DOWN:
                new_row = (current_row + 1)
                if current_col * items_per_column + new_row < num_themes: 
                    if new_row < items_per_column : 
                         self.selected_index = current_col * items_per_column + new_row
                         self.game_app.sound_manager.play_click()
            elif event.key == pygame.K_UP:
                if current_row > 0:
                    self.selected_index -= 1
                    self.game_app.sound_manager.play_click()
            elif event.key == pygame.K_RIGHT:
                if current_col < self.num_columns - 1: 
                    potential_new_index = (current_col + 1) * items_per_column + current_row
                    if potential_new_index < num_themes: 
                        self.selected_index = potential_new_index
                    else: 
                        last_item_in_next_col_candidate = (current_col + 1) * items_per_column
                        if last_item_in_next_col_candidate < num_themes: 
                             self.selected_index = min(potential_new_index, num_themes - 1)
                        elif (current_col + 1) * items_per_column >= num_themes and (current_col + 1)*items_per_column - items_per_column < num_themes :
                             self.selected_index = num_themes - 1
                    self.game_app.sound_manager.play_click()
            elif event.key == pygame.K_LEFT:
                if current_col > 0:
                    self.selected_index = (current_col - 1) * items_per_column + current_row
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

    def _get_theme_key_colors(self, theme_object):
        if not theme_object:
            return []
        
        color_attributes = [
            'BACKGROUND_COLOR', 'TEXT_COLOR', 
            'PLAYER_COLOR', 'AI_COLOR', 
            'BALL_COLOR', 'PLAYER_BAR_FILL' 
        ]
        
        key_colors = []
        for attr_name in color_attributes:
            if hasattr(theme_object, attr_name):
                key_colors.append(getattr(theme_object, attr_name))
            else: 
                key_colors.append((128, 128, 128)) 
        
        return key_colors[:self.swatches_per_theme]


    def render(self, surface):
        pygame.draw.rect(surface, Style.BACKGROUND_COLOR, self.render_area)
        if not self.font_title or not self.font_item or not self.font_subtitle:
            return

        title_x = self.render_area.left + int(Style.TITLE_POS[0] * self.scale_factor)
        title_y = self.render_area.top + int(Style.TITLE_POS[1] * self.scale_factor)
        subtitle_x = self.render_area.left + int(Style.SUBTITLE_POS[0] * self.scale_factor)
        subtitle_y = title_y + self.font_title.get_height() + int(5 * self.scale_factor)

        title_surf = self.font_title.render("Select Theme", True, Style.TEXT_COLOR)
        surface.blit(title_surf, (title_x, title_y))
        
        subtitle_text = "(Arrow Keys/Mouse, ENTER/Click to apply, ESC to back)"
        subtitle_surf = self.font_subtitle.render(subtitle_text, True, Style.TEXT_COLOR)
        surface.blit(subtitle_surf, (subtitle_x, subtitle_y))

        if not self.available_themes:
            no_themes_text = self.font_item.render("No themes available.", True, Style.TEXT_COLOR)
            text_rect = no_themes_text.get_rect(center=self.render_area.center)
            surface.blit(no_themes_text, text_rect)
            return

        num_themes = len(self.available_themes)
        items_per_column = math.ceil(num_themes / self.num_columns)

        column_padding_from_render_area_edge = int(self.render_area.width * 0.08)
        total_inter_column_spacing = int(self.render_area.width * 0.05) 
        available_content_width = self.render_area.width - 2 * column_padding_from_render_area_edge - total_inter_column_spacing * (self.num_columns - 1)
        column_content_width = available_content_width / self.num_columns
        
        item_start_y_base_abs = subtitle_y + self.font_subtitle.get_height() + int(Style.ITEM_LINE_SPACING * 0.7 * self.scale_factor)
        
        # 色卡不再分多行，所以 swatches_total_height 只需考慮一行的高度
        swatches_total_height = self.swatch_size_px if self.swatches_per_theme > 0 else 0
        swatches_margin_top = self.swatch_spacing_px * 2 

        entry_total_height_estimate = self.font_item.get_height() + swatches_margin_top + swatches_total_height
        scaled_line_spacing = entry_total_height_estimate + int(Style.ITEM_LINE_SPACING * self.scale_factor * 0.5)

        self.item_rects = [None] * num_themes

        for i in range(num_themes):
            theme_name_str = self.available_themes[i]
            theme_object = ALL_THEMES.get(theme_name_str)
            
            is_selected = (i == self.selected_index)
            is_currently_active_theme = (theme_name_str == GameSettings.ACTIVE_THEME_NAME)
            
            display_name = theme_name_str
            if is_currently_active_theme:
                display_name += " (Active)"
            
            color = Style.PLAYER_COLOR if is_selected else Style.TEXT_COLOR
            
            original_text_surf = self.font_item.render(display_name, True, color)
            
            current_col_index = i // items_per_column
            current_row_index = i % items_per_column
            
            column_start_x = self.render_area.left + column_padding_from_render_area_edge + \
                             current_col_index * (column_content_width + total_inter_column_spacing)
            
            item_y_abs = item_start_y_base_abs + current_row_index * scaled_line_spacing
            
            text_surf_to_blit = original_text_surf
            text_max_width = column_content_width 
            
            if original_text_surf.get_width() > text_max_width:
                original_text = display_name
                for char_idx in range(len(original_text), 0, -1):
                    temp_text = original_text[:char_idx] + "..." if char_idx < len(original_text) else original_text[:char_idx]
                    temp_surf = self.font_item.render(temp_text, True, color)
                    if temp_surf.get_width() <= text_max_width:
                        text_surf_to_blit = temp_surf
                        break
                else: 
                    text_surf_to_blit = self.font_item.render(original_text[0] + "...", True, color)

            if is_selected:
                scaled_width = int(text_surf_to_blit.get_width() * self.hover_scale_factor)
                scaled_height = int(text_surf_to_blit.get_height() * self.hover_scale_factor)
                if text_surf_to_blit.get_width() > 0 and text_surf_to_blit.get_height() > 0:
                    final_text_surf = pygame.transform.smoothscale(text_surf_to_blit, (scaled_width, scaled_height))
                else:
                    final_text_surf = text_surf_to_blit
            else:
                final_text_surf = text_surf_to_blit
            
            item_text_x = column_start_x 
            item_text_rect = final_text_surf.get_rect(topleft=(item_text_x, item_y_abs))
            
            entry_rect_for_mouse = pygame.Rect(column_start_x, item_y_abs, column_content_width, entry_total_height_estimate)
            self.item_rects[i] = entry_rect_for_mouse
            
            surface.blit(final_text_surf, item_text_rect)

            if theme_object:
                key_colors = self._get_theme_key_colors(theme_object)
                swatch_start_y = item_text_rect.bottom + swatches_margin_top
                
                # 色卡單行橫向排列
                current_swatch_x = column_start_x 
                
                for swatch_idx, swatch_color in enumerate(key_colors):
                    # 檢查是否會超出該欄的內容寬度
                    if current_swatch_x + self.swatch_size_px <= column_start_x + column_content_width:
                        pygame.draw.rect(surface, swatch_color, (current_swatch_x, swatch_start_y, self.swatch_size_px, self.swatch_size_px))
                        # 移除色卡邊框
                        # pygame.draw.rect(surface, (50,50,50), (current_swatch_x, swatch_start_y, self.swatch_size_px, self.swatch_size_px), 1) 
                        current_swatch_x += (self.swatch_size_px + self.swatch_spacing_px)
                    else:
                        break # 如果超出寬度，則不再繪製後續的色卡