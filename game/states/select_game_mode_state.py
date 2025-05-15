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
        self.item_rects = []
        self.hover_scale_factor = 1.1 # <--- 新增：懸停縮放比例

        self.font_title = None
        self.font_subtitle = None
        self.font_item = None # 將在 on_enter 中創建
        
        self.font_settings_icon = None
        self.settings_icon_text = "SET"
        self.settings_icon_rect_on_surface = None
        self.settings_icon_color = Style.TEXT_COLOR
        self.settings_icon_hover_color = Style.PLAYER_COLOR

        if DEBUG_MENU_STATE: print(f"[State:SelectGameMode] Initialized.")

    def on_enter(self, previous_state_data=None):
        super().on_enter(previous_state_data)
        self.selected_index = 0
        self.item_rects = [None] * len(self.options)
        
        scaled_title_font_size = int(Style.TITLE_FONT_SIZE * self.scale_factor)
        scaled_subtitle_font_size = int(Style.SUBTITLE_FONT_SIZE * self.scale_factor)
        self.base_scaled_item_font_size = int(Style.ITEM_FONT_SIZE * self.scale_factor) # <--- 基礎選項字體大小
        scaled_settings_font_size = int(Style.SETTINGS_ICON_FONT_SIZE * self.scale_factor)

        self.font_title = Style.get_font(scaled_title_font_size)
        self.font_subtitle = Style.get_font(scaled_subtitle_font_size)
        self.font_item = Style.get_font(self.base_scaled_item_font_size) # <--- 標準選項字體
        self.font_settings_icon = Style.get_font(scaled_settings_font_size)

        if self.font_settings_icon: # 設定圖示的位置計算保持不變
            settings_surf = self.font_settings_icon.render(self.settings_icon_text, True, self.settings_icon_color)
            padding_x = int(20 * self.scale_factor)
            padding_y = int(20 * self.scale_factor)
            # 確保 settings_icon_rect_on_surface 是相對於 self.render_area 計算的
            # Style.SETTINGS_ICON_POS_LOGICAL 可能是 (logical_width - offset, offset_from_top)
            # 或者直接使用 render_area 的右上角
            logical_settings_x = Style.SETTINGS_ICON_POS_LOGICAL[0] # 假設這是相對於邏輯選單寬度的位置
            logical_settings_y = Style.SETTINGS_ICON_POS_LOGICAL[1] # 假設這是相對於邏輯選單頂部的位置

            # 將邏輯位置轉換為 render_area 內的絕對位置
            # 這假設 LOGICAL_MENU_WIDTH (800) 與 render_area 的邏輯基礎一致
            # 如果 render_area 的 offset 和 scale 已經應用於整個選單，
            # 那麼 settings_icon_rect_on_surface 的計算應該使用 self.render_area.right 和 self.render_area.top
            
            # 簡化：我們假設 SETTINGS_ICON_POS_LOGICAL 是指在 800x600 邏輯畫布上的位置
            # 而 self.render_area 是這個 800x600 畫布在實際螢幕上的映射區域
            # 所以，我們需要將邏輯座標轉換到 self.render_area 的座標系下
            
            # 計算 settings icon 在 scaled render_area 中的位置
            # position_in_render_area_x = int(logical_settings_x * self.scale_factor)
            # position_in_render_area_y = int(logical_settings_y * self.scale_factor)
            # icon_topleft_x_on_surface = self.render_area.left + position_in_render_area_x
            # icon_topleft_y_on_surface = self.render_area.top + position_in_render_area_y
            # self.settings_icon_rect_on_surface = settings_surf.get_rect(topleft=(icon_topleft_x_on_surface, icon_topleft_y_on_surface))
            # 上述計算比較複雜，原有的右對齊方式可能更簡單直接：
            self.settings_icon_rect_on_surface = settings_surf.get_rect(
                topright=(self.render_area.right - padding_x, self.render_area.top + padding_y)
            )


        if DEBUG_MENU_STATE:
            print(f"[State:SelectGameMode] Entered. Scale: {self.scale_factor:.2f}, RenderArea: {self.render_area}")
            if self.settings_icon_rect_on_surface:
                 print(f"    Settings icon rect: {self.settings_icon_rect_on_surface}")

    def handle_event(self, event):
        if event.type == pygame.MOUSEMOTION:
            mouse_over_main_item = False
            for i, rect in enumerate(self.item_rects):
                if rect and rect.collidepoint(event.pos):
                    if self.selected_index != i:
                        self.selected_index = i
                    mouse_over_main_item = True
                    break
            # Settings icon hover color is handled in update

        elif event.type == pygame.MOUSEBUTTONDOWN:
            if event.button == 1:
                if self.settings_icon_rect_on_surface and self.settings_icon_rect_on_surface.collidepoint(event.pos):
                    self.game_app.sound_manager.play_click()
                    if DEBUG_MENU_STATE: print(f"[State:SelectGameMode] Settings icon clicked by mouse.")
                    data_to_pass = {"previous_state_for_settings": self.game_app.GameFlowStateName.SELECT_GAME_MODE}
                    self.request_state_change(self.game_app.GameFlowStateName.SETTINGS_MENU, data_to_pass)
                    return

                for i, rect in enumerate(self.item_rects): # 檢查主選項的點擊
                    if rect and rect.collidepoint(event.pos):
                        self.selected_index = i # 確保選中的是點擊的項目
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
        item_start_x_base_abs = self.render_area.left + int(Style.ITEM_START_POS[0] * self.scale_factor)
        item_start_y_base_abs = self.render_area.top + int(Style.ITEM_START_POS[1] * self.scale_factor)
        scaled_line_spacing = int(Style.ITEM_LINE_SPACING * self.scale_factor)

        title_surf = self.font_title.render("Select Game Mode", True, Style.TEXT_COLOR)
        surface.blit(title_surf, (title_x, title_y))
        
        subtitle_text = "(UP/DOWN/Mouse, ENTER/Click to confirm)"
        subtitle_surf = self.font_subtitle.render(subtitle_text, True, Style.TEXT_COLOR)
        surface.blit(subtitle_surf, (subtitle_x, subtitle_y))

        current_item_y_abs = item_start_y_base_abs
        for i, option_text in enumerate(self.display_options):
            is_selected = (i == self.selected_index)
            color = Style.PLAYER_COLOR if is_selected else Style.TEXT_COLOR
            
            original_text_surf = self.font_item.render(option_text, True, color)
            # The y-coordinate for topleft needs to be current_item_y_abs, not item_start_y_base_abs + i * scaled_line_spacing
            # if we are manually incrementing current_item_y_abs.
            # Let's use the direct y for original_rect.
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
            
            current_item_y_abs += scaled_line_spacing # Increment y for the next item

        if self.settings_icon_rect_on_surface and self.font_settings_icon: # Ensure font is also ready
            settings_text_surf = self.font_settings_icon.render(self.settings_icon_text, True, self.settings_icon_color)
            # The self.settings_icon_rect_on_surface already contains the correct topleft for blitting
            surface.blit(settings_text_surf, self.settings_icon_rect_on_surface)