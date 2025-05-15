# game/states/select_game_mode_state.py
import pygame
from game.states.base_state import BaseState
from game.theme import Style # Style 包含 SETTINGS_ICON_FONT_SIZE, SETTINGS_ICON_POS_LOGICAL
from game.settings import GameSettings

DEBUG_MENU_STATE = True

class SelectGameModeState(BaseState):
    def __init__(self, game_app):
        super().__init__(game_app)
        self.options = [
            ("Player vs. AI", self.game_app.GameFlowStateName.SELECT_INPUT_PVA, {"selected_game_mode": GameSettings.GameMode.PLAYER_VS_AI}),
            ("Player vs. Player", self.game_app.GameFlowStateName.RUN_PVP_SKILL_SELECTION, {"selected_game_mode": GameSettings.GameMode.PLAYER_VS_PLAYER}),
            ("Quit Game", self.game_app.GameFlowStateName.QUIT, {})
        ]
        self.display_options = [opt[0] for opt in self.options]
        self.selected_index = 0
        self.item_rects = [] # <--- 新增：用於儲存主要選單選項的 Rect

        self.font_title = None
        self.font_subtitle = None
        self.font_item = None
        
        # 設定按鈕相關
        self.font_settings_icon = None
        self.settings_icon_text = "SET" 
        self.settings_icon_rect_on_surface = None 
        self.settings_icon_color = Style.TEXT_COLOR 
        self.settings_icon_hover_color = Style.PLAYER_COLOR

        if DEBUG_MENU_STATE: print(f"[State:SelectGameMode] Initialized.")

    def on_enter(self, previous_state_data=None):
        if DEBUG_MENU_STATE:
            print(f"[State:SelectGameMode:on_enter] persistent_data BEFORE super: {self.persistent_data}")
            print(f"[State:SelectGameMode:on_enter] previous_state_data received: {previous_state_data}")

        super().on_enter(previous_state_data) 

        if DEBUG_MENU_STATE:
            print(f"[State:SelectGameMode:on_enter] persistent_data AFTER super: {self.persistent_data}")

        self.selected_index = 0 
        if DEBUG_MENU_STATE:
            print(f"[State:SelectGameMode:on_enter] selected_index set to 0. Current persistent_data: {self.persistent_data}")
        
        # <--- 新增：根據選項數量初始化 item_rects 列表
        self.item_rects = [None] * len(self.options)
        
        scaled_title_font_size = int(Style.TITLE_FONT_SIZE * self.scale_factor)
        scaled_subtitle_font_size = int(Style.SUBTITLE_FONT_SIZE * self.scale_factor)
        scaled_item_font_size = int(Style.ITEM_FONT_SIZE * self.scale_factor)
        scaled_settings_font_size = int(Style.SETTINGS_ICON_FONT_SIZE * self.scale_factor)

        self.font_title = Style.get_font(scaled_title_font_size)
        self.font_subtitle = Style.get_font(scaled_subtitle_font_size)
        self.font_item = Style.get_font(scaled_item_font_size)
        self.font_settings_icon = Style.get_font(scaled_settings_font_size)

        if self.font_settings_icon:
            settings_surf = self.font_settings_icon.render(self.settings_icon_text, True, self.settings_icon_color)
            padding_x = int(20 * self.scale_factor) 
            padding_y = int(20 * self.scale_factor) 
            self.settings_icon_rect_on_surface = settings_surf.get_rect(
                topright=(self.render_area.right - padding_x, self.render_area.top + padding_y)
            )

        if DEBUG_MENU_STATE:
            print(f"[State:SelectGameMode] Entered. Scale: {self.scale_factor:.2f}, RenderArea: {self.render_area}")
            if self.settings_icon_rect_on_surface:
                 print(f"    Settings icon rect: {self.settings_icon_rect_on_surface}")

    def handle_event(self, event):
        # --- 滑鼠事件處理 ---
        if event.type == pygame.MOUSEMOTION:
            # 檢查主要選單項目的懸停
            mouse_over_main_item = False
            for i, rect in enumerate(self.item_rects):
                if rect and rect.collidepoint(event.pos):
                    if self.selected_index != i:
                        self.selected_index = i
                    mouse_over_main_item = True
                    break
            # 設定圖示的懸停顏色變化在 update 方法中處理

        elif event.type == pygame.MOUSEBUTTONDOWN:
            if event.button == 1: # 左鍵點擊
                # 優先檢查設定圖示點擊
                if self.settings_icon_rect_on_surface and self.settings_icon_rect_on_surface.collidepoint(event.pos):
                    self.game_app.sound_manager.play_click()
                    if DEBUG_MENU_STATE: print(f"[State:SelectGameMode] Settings icon clicked by mouse.")
                    data_to_pass = {"previous_state_for_settings": self.game_app.GameFlowStateName.SELECT_GAME_MODE}
                    self.request_state_change(self.game_app.GameFlowStateName.SETTINGS_MENU, data_to_pass)
                    return # 事件已處理

                # 檢查主要選單項目點擊
                for i, rect in enumerate(self.item_rects):
                    if rect and rect.collidepoint(event.pos):
                        self.selected_index = i
                        self.game_app.sound_manager.play_click()
                        selected_action_target_state = self.options[self.selected_index][1]
                        action_data = self.options[self.selected_index][2].copy()

                        if DEBUG_MENU_STATE: print(f"[State:SelectGameMode] Mouse clicked: {self.options[self.selected_index][0]}")

                        if selected_action_target_state == self.game_app.GameFlowStateName.QUIT:
                            self.request_quit()
                        else:
                            if "selected_game_mode" in action_data:
                                self.game_app.shared_game_data["selected_game_mode"] = action_data["selected_game_mode"]
                            if action_data.get("selected_game_mode") == GameSettings.GameMode.PLAYER_VS_PLAYER:
                                self.game_app.shared_game_data["selected_input_mode"] = "keyboard"
                            self.request_state_change(selected_action_target_state, action_data)
                        return # 事件已處理
        
        # --- 鍵盤事件處理 ---
        if event.type == pygame.KEYDOWN:
            # ... (原有的鍵盤事件處理邏輯不變) ...
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

                if DEBUG_MENU_STATE: print(f"[State:SelectGameMode] Enter key: {self.options[self.selected_index][0]}")

                if selected_action_target_state == self.game_app.GameFlowStateName.QUIT:
                    self.request_quit()
                else:
                    if "selected_game_mode" in action_data:
                        self.game_app.shared_game_data["selected_game_mode"] = action_data["selected_game_mode"]

                    if action_data.get("selected_game_mode") == GameSettings.GameMode.PLAYER_VS_PLAYER:
                        self.game_app.shared_game_data["selected_input_mode"] = "keyboard"
                        if DEBUG_MENU_STATE: print(f"    PvP selected, input mode forced to keyboard.")
                    
                    if selected_action_target_state == self.game_app.GameFlowStateName.SETTINGS_MENU: # 理論上這段不會被鍵盤觸發了，因為設定是圖示
                        action_data["previous_state_for_settings"] = self.game_app.GameFlowStateName.SELECT_GAME_MODE
                    
                    self.request_state_change(selected_action_target_state, action_data)
            elif event.key == pygame.K_ESCAPE:
                self.game_app.sound_manager.play_click()
                if DEBUG_MENU_STATE: print(f"[State:SelectGameMode] ESC pressed, doing nothing (use Quit option).")


    def update(self, dt):
        if self.settings_icon_rect_on_surface:
            mouse_pos = pygame.mouse.get_pos()
            if self.settings_icon_rect_on_surface.collidepoint(mouse_pos):
                self.settings_icon_color = self.settings_icon_hover_color
            else:
                self.settings_icon_color = Style.TEXT_COLOR


    def render(self, surface):
        pygame.draw.rect(surface, Style.BACKGROUND_COLOR, self.render_area)
        
        if not self.font_title or not self.font_item or not self.font_subtitle or not self.font_settings_icon:
             return

        title_x = self.render_area.left + int(Style.TITLE_POS[0] * self.scale_factor)
        title_y = self.render_area.top + int(Style.TITLE_POS[1] * self.scale_factor)
        subtitle_x = self.render_area.left + int(Style.SUBTITLE_POS[0] * self.scale_factor)
        subtitle_y = self.render_area.top + int(Style.SUBTITLE_POS[1] * self.scale_factor)
        item_start_x_base = int(Style.ITEM_START_POS[0] * self.scale_factor)
        item_start_y_base = self.render_area.top + int(Style.ITEM_START_POS[1] * self.scale_factor)
        scaled_line_spacing = int(Style.ITEM_LINE_SPACING * self.scale_factor)

        title_surf = self.font_title.render("Select Game Mode", True, Style.TEXT_COLOR)
        surface.blit(title_surf, (title_x, title_y))
        
        # <--- 更新副標題提示 ---
        subtitle_text = "(UP/DOWN/Mouse, ENTER/Click to confirm)"
        subtitle_surf = self.font_subtitle.render(subtitle_text, True, Style.TEXT_COLOR)
        surface.blit(subtitle_surf, (subtitle_x, subtitle_y))

        current_item_y = item_start_y_base
        for i, option_text in enumerate(self.display_options):
            color = Style.PLAYER_COLOR if i == self.selected_index else Style.TEXT_COLOR
            text_surf = self.font_item.render(option_text, True, color)
            item_x = self.render_area.left + item_start_x_base
            item_y = item_start_y_base + i * scaled_line_spacing 

            # <--- 新增：計算並儲存每個主要選單選項的 Rect ---
            if i < len(self.item_rects):
                item_rect = text_surf.get_rect(topleft=(item_x, item_y))
                self.item_rects[i] = item_rect
            # <--- Rect 計算結束 ---

            surface.blit(text_surf, (item_x, item_y))
            current_item_y += scaled_line_spacing

        if self.settings_icon_rect_on_surface:
            settings_text_surf = self.font_settings_icon.render(self.settings_icon_text, True, self.settings_icon_color)
            surface.blit(settings_text_surf, self.settings_icon_rect_on_surface)