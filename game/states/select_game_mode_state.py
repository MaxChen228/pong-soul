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
            # ("Settings", self.game_app.GameFlowStateName.SETTINGS_MENU, {}), # 可以選擇也加入到選項列表
            ("Quit Game", self.game_app.GameFlowStateName.QUIT, {})
        ]
        self.display_options = [opt[0] for opt in self.options]
        self.selected_index = 0
        self.font_title = None
        self.font_subtitle = None
        self.font_item = None
        
        # 設定按鈕相關
        self.font_settings_icon = None
        self.settings_icon_text = "SET" # 或使用 Unicode 齒輪: "⚙" (需確保字型支援)
        self.settings_icon_rect_on_surface = None # 實際渲染到螢幕上的 Rect
        self.settings_icon_color = Style.TEXT_COLOR # 預設顏色
        self.settings_icon_hover_color = Style.PLAYER_COLOR # 滑鼠懸停顏色

        if DEBUG_MENU_STATE: print(f"[State:SelectGameMode] Initialized.")

    def on_enter(self, previous_state_data=None):
        if DEBUG_MENU_STATE:
            print(f"[State:SelectGameMode:on_enter] persistent_data BEFORE super: {self.persistent_data}")
            print(f"[State:SelectGameMode:on_enter] previous_state_data received: {previous_state_data}")

        super().on_enter(previous_state_data) # 這會更新 self.persistent_data

        if DEBUG_MENU_STATE:
            print(f"[State:SelectGameMode:on_enter] persistent_data AFTER super: {self.persistent_data}")

        self.selected_index = 0 # 每次進入重置選項
        if DEBUG_MENU_STATE:
            print(f"[State:SelectGameMode:on_enter] selected_index set to 0. Current persistent_data: {self.persistent_data}")
        
        
        # 重新加載字型，因為主題可能已更改
        scaled_title_font_size = int(Style.TITLE_FONT_SIZE * self.scale_factor)
        scaled_subtitle_font_size = int(Style.SUBTITLE_FONT_SIZE * self.scale_factor)
        scaled_item_font_size = int(Style.ITEM_FONT_SIZE * self.scale_factor)
        scaled_settings_font_size = int(Style.SETTINGS_ICON_FONT_SIZE * self.scale_factor)

        self.font_title = Style.get_font(scaled_title_font_size)
        self.font_subtitle = Style.get_font(scaled_subtitle_font_size)
        self.font_item = Style.get_font(scaled_item_font_size)
        self.font_settings_icon = Style.get_font(scaled_settings_font_size)

        # 計算設定圖示的實際位置和大小
        # Style.SETTINGS_ICON_POS_LOGICAL 是相對於邏輯選單區域的
        # self.render_area 是主 GameApp 計算出的此狀態在螢幕上的實際渲染區域
        # self.scale_factor 是邏輯尺寸到 render_area 尺寸的縮放因子

        if self.font_settings_icon:
            settings_surf = self.font_settings_icon.render(self.settings_icon_text, True, self.settings_icon_color)
            
            # SETTINGS_ICON_POS_LOGICAL 的 x,y 是相對於邏輯選單的右邊和頂邊的偏移（假設）
            # 或是直接指定邏輯座標。我們在 Style 中定義的是 (760, 20) 在 800x600 邏輯菜單中。
            # 所以是從邏輯區域的左上角算起。
            logical_x = Style.SETTINGS_ICON_POS_LOGICAL[0]
            logical_y = Style.SETTINGS_ICON_POS_LOGICAL[1]

            # 將邏輯座標轉換為在 self.render_area 內的座標
            icon_x_on_render_area = int(logical_x * self.scale_factor)
            icon_y_on_render_area = int(logical_y * self.scale_factor)

            # 最終在螢幕上的位置
            icon_abs_x = self.render_area.left + icon_x_on_render_area
            icon_abs_y = self.render_area.top + icon_y_on_render_area
            
            # 讓 Rect 的 topright 對齊計算出的點，或者 center，取決於想要的對齊方式
            # 這裡我們讓 topright 對齊 (render_area.right - padding, render_area.top + padding)
            padding_x = int(20 * self.scale_factor) # 離 render_area 右邊界的距離
            padding_y = int(20 * self.scale_factor) # 離 render_area 上邊界的距離
            
            self.settings_icon_rect_on_surface = settings_surf.get_rect(
                topright=(self.render_area.right - padding_x, self.render_area.top + padding_y)
            )

        if DEBUG_MENU_STATE:
            print(f"[State:SelectGameMode] Entered. Scale: {self.scale_factor:.2f}, RenderArea: {self.render_area}")
            if self.settings_icon_rect_on_surface:
                 print(f"    Settings icon rect: {self.settings_icon_rect_on_surface}")

    def handle_event(self, event):
        if DEBUG_MENU_STATE: # 使用已有的 DEBUG_MENU_STATE 開關
            print(f"[State:SelectGameMode:handle_event] Received event: {pygame.event.event_name(event.type)}")
            if event.type == pygame.KEYDOWN:
                print(f"    Key pressed: {pygame.key.name(event.key)}")

        # 先處理滑鼠點擊設定圖示的事件
        if event.type == pygame.MOUSEBUTTONDOWN:
            # ... (後續代碼不變)
            if event.button == 1 and self.settings_icon_rect_on_surface: # 左鍵點擊
                if self.settings_icon_rect_on_surface.collidepoint(event.pos):
                    self.game_app.sound_manager.play_click()
                    if DEBUG_MENU_STATE: print(f"[State:SelectGameMode] Settings icon clicked.")
                    # 傳遞當前狀態名，以便設定選單可以返回
                    data_to_pass = {"previous_state_for_settings": self.game_app.GameFlowStateName.SELECT_GAME_MODE}
                    self.request_state_change(self.game_app.GameFlowStateName.SETTINGS_MENU, data_to_pass)
                    return # 事件已處理

        # 然後處理鍵盤事件
        if event.type == pygame.KEYDOWN:
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

                if DEBUG_MENU_STATE: print(f"[State:SelectGameMode] Selected: {self.options[self.selected_index][0]}")

                if selected_action_target_state == self.game_app.GameFlowStateName.QUIT:
                    self.request_quit()
                else:
                    if "selected_game_mode" in action_data:
                        self.game_app.shared_game_data["selected_game_mode"] = action_data["selected_game_mode"]

                    if action_data.get("selected_game_mode") == GameSettings.GameMode.PLAYER_VS_PLAYER:
                        self.game_app.shared_game_data["selected_input_mode"] = "keyboard"
                        if DEBUG_MENU_STATE: print(f"    PvP selected, input mode forced to keyboard.")
                    
                    # 如果選的是 SETTINGS_MENU (雖然目前設定圖示是滑鼠點擊，但保留鍵盤導航的可能)
                    if selected_action_target_state == self.game_app.GameFlowStateName.SETTINGS_MENU:
                        action_data["previous_state_for_settings"] = self.game_app.GameFlowStateName.SELECT_GAME_MODE
                    
                    self.request_state_change(selected_action_target_state, action_data)
            elif event.key == pygame.K_ESCAPE:
                self.game_app.sound_manager.play_click()
                if DEBUG_MENU_STATE: print(f"[State:SelectGameMode] ESC pressed, doing nothing (use Quit option).")

    def update(self, dt):
        # 檢查滑鼠是否懸停在設定圖示上，以改變顏色
        if self.settings_icon_rect_on_surface:
            mouse_pos = pygame.mouse.get_pos()
            if self.settings_icon_rect_on_surface.collidepoint(mouse_pos):
                self.settings_icon_color = self.settings_icon_hover_color
            else:
                self.settings_icon_color = Style.TEXT_COLOR


    def render(self, surface):
        # 背景色應該已經由 Style 更新，因為 reload_active_style 會在主題更改時被調用
        pygame.draw.rect(surface, Style.BACKGROUND_COLOR, self.render_area)
        
        if not self.font_title or not self.font_item or not self.font_subtitle or not self.font_settings_icon: # 確保字型已載入
             return

        if DEBUG_MENU_STATE: # 使用已有的 DEBUG_MENU_STATE 開關
            print(f"[State:SelectGameMode:render] Cycle Start. Rendering with selected_index: {self.selected_index}, Frame Time: {pygame.time.get_ticks()}")

        title_x = self.render_area.left + int(Style.TITLE_POS[0] * self.scale_factor)
        title_y = self.render_area.top + int(Style.TITLE_POS[1] * self.scale_factor)
        subtitle_x = self.render_area.left + int(Style.SUBTITLE_POS[0] * self.scale_factor)
        subtitle_y = self.render_area.top + int(Style.SUBTITLE_POS[1] * self.scale_factor)
        item_start_x_base = int(Style.ITEM_START_POS[0] * self.scale_factor)
        item_start_y_base = self.render_area.top + int(Style.ITEM_START_POS[1] * self.scale_factor)
        scaled_line_spacing = int(Style.ITEM_LINE_SPACING * self.scale_factor)

        title_surf = self.font_title.render("Select Game Mode", True, Style.TEXT_COLOR)
        surface.blit(title_surf, (title_x, title_y))
        subtitle_surf = self.font_subtitle.render("(UP/DOWN, ENTER to confirm)", True, Style.TEXT_COLOR)
        surface.blit(subtitle_surf, (subtitle_x, subtitle_y))
        if DEBUG_MENU_STATE:
            print(f"[State:SelectGameMode:render] Before item loop. selected_index: {self.selected_index}")
        for i, option_text in enumerate(self.display_options):
            color = Style.PLAYER_COLOR if i == self.selected_index else Style.TEXT_COLOR
            text_surf = self.font_item.render(option_text, True, color)
            item_x = self.render_area.left + item_start_x_base
            item_y = item_start_y_base + i * scaled_line_spacing # 相對於 render_area.top 計算
            surface.blit(text_surf, (item_x, item_y))

        # 繪製設定圖示
        if self.settings_icon_rect_on_surface:
            settings_text_surf = self.font_settings_icon.render(self.settings_icon_text, True, self.settings_icon_color)
            # settings_icon_rect_on_surface 的位置已經是絕對螢幕座標了
            surface.blit(settings_text_surf, self.settings_icon_rect_on_surface)