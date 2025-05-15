# game/states/theme_selection_state.py
import pygame
from game.states.base_state import BaseState
from game.theme import Style, get_available_theme_names # 需要 get_available_theme_names
from game.settings import GameSettings # 需要 GameSettings 來調用 set_active_theme

DEBUG_THEME_SELECT_STATE = False

class ThemeSelectionState(BaseState):
    def __init__(self, game_app):
        super().__init__(game_app)
        self.available_themes = get_available_theme_names()
        self.selected_index = 0
        try:
            # 嘗試將當前主題設為預選中項
            current_theme_name = GameSettings.ACTIVE_THEME_NAME
            if current_theme_name in self.available_themes:
                self.selected_index = self.available_themes.index(current_theme_name)
        except Exception as e:
            if DEBUG_THEME_SELECT_STATE:
                print(f"[State:ThemeSelection] Error getting initial theme index: {e}")
            self.selected_index = 0


        self.font_title = None
        self.font_item = None
        self.font_subtitle = None # For instructions

        # 用於儲存是從哪個狀態跳轉過來的，以便可以正確返回
        self.previous_state_name = self.game_app.GameFlowStateName.SETTINGS_MENU


        if DEBUG_THEME_SELECT_STATE: print(f"[State:ThemeSelection] Initialized. Themes: {self.available_themes}")

    def on_enter(self, previous_state_data=None):
        super().on_enter(previous_state_data)
        
        # 更新可用主題列表和當前選中項 (以防主題列表在運行時被修改，雖然目前不會)
        self.available_themes = get_available_theme_names()
        try:
            current_theme_name = GameSettings.ACTIVE_THEME_NAME
            if current_theme_name in self.available_themes:
                self.selected_index = self.available_themes.index(current_theme_name)
            else: # 如果當前設定的主題名不在可用列表中，預設選第一個
                self.selected_index = 0
                if self.available_themes: # 避免列表為空
                     GameSettings.set_active_theme(self.available_themes[0])

        except Exception as e:
            if DEBUG_THEME_SELECT_STATE:
                print(f"[State:ThemeSelection] Error re-evaluating theme index on enter: {e}")
            self.selected_index = 0
            if self.available_themes: GameSettings.set_active_theme(self.available_themes[0])


        # 從 persistent_data 中獲取是從哪個狀態跳轉過來的
        self.previous_state_name = self.persistent_data.get(
            "previous_state_for_theme_selection", 
            self.game_app.GameFlowStateName.SETTINGS_MENU # 預設返回到設定選單
        )

        scaled_title_font_size = int(Style.TITLE_FONT_SIZE * self.scale_factor)
        scaled_item_font_size = int(Style.ITEM_FONT_SIZE * self.scale_factor)
        scaled_subtitle_font_size = int(Style.SUBTITLE_FONT_SIZE * self.scale_factor)


        self.font_title = Style.get_font(scaled_title_font_size)
        self.font_item = Style.get_font(scaled_item_font_size)
        self.font_subtitle = Style.get_font(scaled_subtitle_font_size)


        if DEBUG_THEME_SELECT_STATE:
            print(f"[State:ThemeSelection] Entered. Scale: {self.scale_factor:.2f}, RenderArea: {self.render_area}")
            print(f"    Current selected theme index: {self.selected_index} ('{self.available_themes[self.selected_index] if self.available_themes else 'N/A'}')")
            print(f"    Previous state to return to: {self.previous_state_name}")


    def handle_event(self, event):
        if not self.available_themes: # 如果沒有主題可選
            if event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE:
                self.game_app.sound_manager.play_click()
                self.request_state_change(self.previous_state_name)
            return

        if event.type == pygame.KEYDOWN:
            if event.key == pygame.K_DOWN:
                self.selected_index = (self.selected_index + 1) % len(self.available_themes)
                self.game_app.sound_manager.play_click()
            elif event.key == pygame.K_UP:
                self.selected_index = (self.selected_index - 1 + len(self.available_themes)) % len(self.available_themes)
                self.game_app.sound_manager.play_click()
            elif event.key == pygame.K_RETURN: # 確認選擇
                self.game_app.sound_manager.play_click()
                selected_theme_name = self.available_themes[self.selected_index]
                
                if DEBUG_THEME_SELECT_STATE:
                    print(f"[State:ThemeSelection] Applying theme: {selected_theme_name}")
                
                GameSettings.set_active_theme(selected_theme_name)
                # 主題已應用，字型等會自動重載。
                # 不需要做其他事情，可以直接返回或停留在當前選單讓玩家看到效果。
                # 為了更好的用戶體驗，我們在應用後短暫停留或直接返回。
                # 這裡我們選擇直接返回到上一個狀態 (SettingsMenuState)。
                self.request_state_change(self.previous_state_name)

            elif event.key == pygame.K_ESCAPE: # 取消並返回
                self.game_app.sound_manager.play_click()
                if DEBUG_THEME_SELECT_STATE: print(f"[State:ThemeSelection] ESC pressed, returning to {self.previous_state_name}.")
                self.request_state_change(self.previous_state_name)

    def update(self, dt):
        pass

    def render(self, surface):
        pygame.draw.rect(surface, Style.BACKGROUND_COLOR, self.render_area) # 使用當前主題背景色
        if not self.font_title or not self.font_item or not self.font_subtitle:
            return

        title_x = self.render_area.left + int(Style.TITLE_POS[0] * self.scale_factor)
        title_y = self.render_area.top + int(Style.TITLE_POS[1] * self.scale_factor)
        subtitle_x = self.render_area.left + int(Style.SUBTITLE_POS[0] * self.scale_factor)
        subtitle_y = title_y + self.font_title.get_height() + int(5 * self.scale_factor) # 副標題在主標題下方

        item_start_x_base = int(Style.ITEM_START_POS[0] * self.scale_factor)
        item_start_y_base = subtitle_y + self.font_subtitle.get_height() + int(Style.ITEM_LINE_SPACING * 0.5 * self.scale_factor)
        scaled_line_spacing = int(Style.ITEM_LINE_SPACING * self.scale_factor)

        title_surf = self.font_title.render("Select Theme", True, Style.TEXT_COLOR)
        surface.blit(title_surf, (title_x, title_y))
        
        subtitle_text = "(UP/DOWN, ENTER to apply, ESC to back)"
        subtitle_surf = self.font_subtitle.render(subtitle_text, True, Style.TEXT_COLOR)
        surface.blit(subtitle_surf, (subtitle_x, subtitle_y))


        if not self.available_themes:
            no_themes_text = self.font_item.render("No themes available.", True, Style.TEXT_COLOR)
            text_rect = no_themes_text.get_rect(center=self.render_area.center)
            surface.blit(no_themes_text, text_rect)
            return

        current_item_y = item_start_y_base
        for i, theme_name in enumerate(self.available_themes):
            is_currently_active = (theme_name == GameSettings.ACTIVE_THEME_NAME) # 檢查是否為當前全局生效的主題
            
            display_name = theme_name
            if is_currently_active:
                display_name += " (Active)" # 標記當前生效的主題
            
            color = Style.PLAYER_COLOR if i == self.selected_index else Style.TEXT_COLOR
            text_surf = self.font_item.render(display_name, True, color)
            
            item_x = self.render_area.left + item_start_x_base
            surface.blit(text_surf, (item_x, current_item_y))
            current_item_y += scaled_line_spacing