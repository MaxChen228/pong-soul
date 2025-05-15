# game/states/menu_states.py
import pygame
from game.states.base_state import BaseState
from game.theme import Style
from game.settings import GameSettings
# from main import GameFlowStateName # 避免循環導入

DEBUG_MENU_STATE = True

class SelectGameModeState(BaseState): # 這個類保持不變
    def __init__(self, game_app):
        super().__init__(game_app)
        self.options = [
            ("Player vs. AI", self.game_app.GameFlowStateName.SELECT_INPUT_PVA, {"selected_game_mode": GameSettings.GameMode.PLAYER_VS_AI}),
            ("Player vs. Player", self.game_app.GameFlowStateName.RUN_PVP_SKILL_SELECTION, {"selected_game_mode": GameSettings.GameMode.PLAYER_VS_PLAYER}),
            ("Quit Game", self.game_app.GameFlowStateName.QUIT, {})
        ]
        self.display_options = [opt[0] for opt in self.options]
        self.selected_index = 0
        self.font_title = None
        self.font_subtitle = None
        self.font_item = None
        if DEBUG_MENU_STATE: print(f"[State:SelectGameMode] Initialized.")

    def on_enter(self, previous_state_data=None):
        super().on_enter(previous_state_data)
        self.selected_index = 0
        scaled_title_font_size = int(Style.TITLE_FONT_SIZE * self.scale_factor)
        scaled_subtitle_font_size = int(Style.SUBTITLE_FONT_SIZE * self.scale_factor)
        scaled_item_font_size = int(Style.ITEM_FONT_SIZE * self.scale_factor)
        self.font_title = Style.get_font(scaled_title_font_size)
        self.font_subtitle = Style.get_font(scaled_subtitle_font_size)
        self.font_item = Style.get_font(scaled_item_font_size)
        if DEBUG_MENU_STATE: print(f"[State:SelectGameMode] Entered. Scale: {self.scale_factor:.2f}, RenderArea: {self.render_area}")

    def handle_event(self, event):
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
                action_data = self.options[self.selected_index][2].copy() # 複製以避免修改原始配置

                if DEBUG_MENU_STATE: print(f"[State:SelectGameMode] Selected: {self.options[self.selected_index][0]}")

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
        pass

    def render(self, surface):
        pygame.draw.rect(surface, Style.BACKGROUND_COLOR, self.render_area)
        if not self.font_title: return # 如果字體未初始化 (可能在極端情況下發生)

        title_x = self.render_area.left + int(Style.TITLE_POS[0] * self.scale_factor)
        title_y = self.render_area.top + int(Style.TITLE_POS[1] * self.scale_factor)
        subtitle_x = self.render_area.left + int(Style.SUBTITLE_POS[0] * self.scale_factor)
        subtitle_y = self.render_area.top + int(Style.SUBTITLE_POS[1] * self.scale_factor)
        item_start_x_base = int(Style.ITEM_START_POS[0] * self.scale_factor)
        item_start_y_base = int(Style.ITEM_START_POS[1] * self.scale_factor)
        scaled_line_spacing = int(Style.ITEM_LINE_SPACING * self.scale_factor)

        title_surf = self.font_title.render("Select Game Mode", True, Style.TEXT_COLOR)
        surface.blit(title_surf, (title_x, title_y))
        subtitle_surf = self.font_subtitle.render("(UP/DOWN, ENTER to confirm)", True, Style.TEXT_COLOR)
        surface.blit(subtitle_surf, (subtitle_x, subtitle_y))

        for i, option_text in enumerate(self.display_options):
            color = Style.PLAYER_COLOR if i == self.selected_index else Style.TEXT_COLOR
            text_surf = self.font_item.render(option_text, True, color)
            item_x = self.render_area.left + item_start_x_base
            item_y = self.render_area.top + item_start_y_base + i * scaled_line_spacing
            surface.blit(text_surf, (item_x, item_y))

class SelectInputPvaState(BaseState):

    def __init__(self, game_app):
        super().__init__(game_app)
        self.options = [
            ("Keyboard", "keyboard"), # (顯示文字, 對應的 input_mode 值)
            ("Mouse", "mouse")
        ]
        self.display_options = [opt[0] for opt in self.options]
        self.selected_index = 0
        self.font_title = None
        self.font_subtitle = None
        self.font_item = None
        if DEBUG_MENU_STATE: print(f"[State:SelectInputPva] Initialized.")

    def on_enter(self, previous_state_data=None):
        super().on_enter(previous_state_data)
        self.selected_index = 0
        # 根據當前狀態的 scale_factor 初始化字體
        scaled_title_font_size = int(Style.TITLE_FONT_SIZE * self.scale_factor)
        scaled_subtitle_font_size = int(Style.SUBTITLE_FONT_SIZE * self.scale_factor)
        scaled_item_font_size = int(Style.ITEM_FONT_SIZE * self.scale_factor)

        self.font_title = Style.get_font(scaled_title_font_size)
        self.font_subtitle = Style.get_font(scaled_subtitle_font_size)
        self.font_item = Style.get_font(scaled_item_font_size)
        if DEBUG_MENU_STATE: print(f"[State:SelectInputPva] Entered. Scale: {self.scale_factor:.2f}, RenderArea: {self.render_area}")
        if DEBUG_MENU_STATE: print(f"    Game mode from previous state: {self.game_app.shared_game_data.get('selected_game_mode')}")


    def handle_event(self, event):
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
                if DEBUG_MENU_STATE: print(f"[State:SelectInputPva] Selected input: {selected_input_mode_value}")
                
                # 更新 GameApp 中的共享數據
                self.game_app.shared_game_data["selected_input_mode"] = selected_input_mode_value
                
                # 請求切換到 PvA 技能選擇狀態
                self.request_state_change(self.game_app.GameFlowStateName.SELECT_SKILL_PVA)

            elif event.key == pygame.K_ESCAPE: # 按 ESC 返回到遊戲模式選擇
                self.game_app.sound_manager.play_click()
                if DEBUG_MENU_STATE: print(f"[State:SelectInputPva] ESC pressed, returning to SelectGameMode.")
                self.request_state_change(self.game_app.GameFlowStateName.SELECT_GAME_MODE)

    def update(self, dt):
        pass

    def render(self, surface):
        pygame.draw.rect(surface, Style.BACKGROUND_COLOR, self.render_area)
        if not self.font_title: return

        title_x = self.render_area.left + int(Style.TITLE_POS[0] * self.scale_factor)
        title_y = self.render_area.top + int(Style.TITLE_POS[1] * self.scale_factor)
        subtitle_x = self.render_area.left + int(Style.SUBTITLE_POS[0] * self.scale_factor)
        subtitle_y = self.render_area.top + int(Style.SUBTITLE_POS[1] * self.scale_factor)
        item_start_x_base = int(Style.ITEM_START_POS[0] * self.scale_factor)
        item_start_y_base = int(Style.ITEM_START_POS[1] * self.scale_factor)
        scaled_line_spacing = int(Style.ITEM_LINE_SPACING * self.scale_factor)

        title_surf = self.font_title.render("Select Controller (PvA)", True, Style.TEXT_COLOR)
        surface.blit(title_surf, (title_x, title_y))
        subtitle_surf = self.font_subtitle.render("(UP/DOWN, ENTER, ESC to back)", True, Style.TEXT_COLOR)
        surface.blit(subtitle_surf, (subtitle_x, subtitle_y))

        for i, option_text in enumerate(self.display_options):
            color = Style.PLAYER_COLOR if i == self.selected_index else Style.TEXT_COLOR
            text_surf = self.font_item.render(option_text, True, color)
            item_x = self.render_area.left + item_start_x_base
            item_y = self.render_area.top + item_start_y_base + i * scaled_line_spacing
            surface.blit(text_surf, (item_x, item_y))

# ⭐️ 新增 SelectSkillPvaState 類 ⭐️
class SelectSkillPvaState(BaseState):
    def __init__(self, game_app):
        super().__init__(game_app)
        # 技能的內部代碼名稱和顯示名稱的映射
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

        # 按鍵映射 (PvA模式下通常使用預設按鍵)
        self.key_map = {
            'UP': pygame.K_UP,
            'DOWN': pygame.K_DOWN,
            'CONFIRM': pygame.K_RETURN,
            'CANCEL': pygame.K_ESCAPE # ESC 用於返回
        }
        self.player_identifier = "Player" # PvA 模式下是單一玩家

        if DEBUG_MENU_STATE: print(f"[State:SelectSkillPva] Initialized.")

    def on_enter(self, previous_state_data=None):
        super().on_enter(previous_state_data)
        self.selected_index = 0
        # 根據當前狀態的 scale_factor 初始化字體
        scaled_title_font_size = int(Style.TITLE_FONT_SIZE * self.scale_factor)
        scaled_subtitle_font_size = int(Style.SUBTITLE_FONT_SIZE * self.scale_factor)
        scaled_item_font_size = int(Style.ITEM_FONT_SIZE * self.scale_factor)

        self.font_title = Style.get_font(scaled_title_font_size)
        self.font_subtitle = Style.get_font(scaled_subtitle_font_size)
        self.font_item = Style.get_font(scaled_item_font_size)
        if DEBUG_MENU_STATE:
            print(f"[State:SelectSkillPva] Entered. Scale: {self.scale_factor:.2f}, RenderArea: {self.render_area}")
            print(f"    Shared data: GameMode='{self.game_app.shared_game_data.get('selected_game_mode')}', Input='{self.game_app.shared_game_data.get('selected_input_mode')}'")

    def handle_event(self, event):
        if event.type == pygame.KEYDOWN:
            if event.key == self.key_map['DOWN']:
                self.selected_index = (self.selected_index + 1) % len(self.skills_options)
                self.game_app.sound_manager.play_click()
            elif event.key == self.key_map['UP']:
                self.selected_index = (self.selected_index - 1 + len(self.skills_options)) % len(self.skills_options)
                self.game_app.sound_manager.play_click()
            elif event.key == self.key_map['CONFIRM']:
                self.game_app.sound_manager.play_click()
                selected_skill_code = self.skills_options[self.selected_index][1]
                if DEBUG_MENU_STATE: print(f"[State:SelectSkillPva] Selected skill: {selected_skill_code}")
                
                # 更新 GameApp 中的共享數據
                self.game_app.shared_game_data["p1_selected_skill"] = selected_skill_code
                self.game_app.shared_game_data["p2_selected_skill"] = None # PvA 模式 P2 無技能
                
                # 請求切換到 Gameplay 狀態
                # 將所有需要的數據一起傳遞
                data_for_gameplay = {
                    "game_mode": self.game_app.shared_game_data.get("selected_game_mode"),
                    "input_mode": self.game_app.shared_game_data.get("selected_input_mode"),
                    "p1_skill": selected_skill_code,
                    "p2_skill": None
                }
                self.request_state_change(self.game_app.GameFlowStateName.GAMEPLAY, data_for_gameplay)

            elif event.key == self.key_map['CANCEL']: # 按 ESC 返回到輸入選擇
                self.game_app.sound_manager.play_click()
                if DEBUG_MENU_STATE: print(f"[State:SelectSkillPva] ESC pressed, returning to SelectInputPva.")
                self.request_state_change(self.game_app.GameFlowStateName.SELECT_INPUT_PVA)

    def update(self, dt):
        pass

    def render(self, surface):
        # render_area 和 scale_factor 由 GameApp 設定
        pygame.draw.rect(surface, Style.BACKGROUND_COLOR, self.render_area)
        if not self.font_title: return

        # 繪製邏輯類似於 menu.select_skill，但整合到狀態中
        menu_title_text = f"{self.player_identifier} Select Skill"
        key_up_name = pygame.key.name(self.key_map['UP']).upper()
        key_down_name = pygame.key.name(self.key_map['DOWN']).upper()
        key_confirm_name = pygame.key.name(self.key_map['CONFIRM']).upper()
        key_cancel_name = pygame.key.name(self.key_map['CANCEL']).upper()
        menu_subtitle_text = f"({key_up_name}/{key_down_name}, {key_confirm_name} to confirm)"
        back_text_str = f"<< Back ({key_cancel_name})"

        # 位置計算基於 render_area 和 scale_factor
        # 我們可以複製 menu.select_skill 中的定位邏輯，並應用縮放
        # 為了簡化，使用與 SelectGameModeState 類似的定位邏輯
        title_x = self.render_area.left + int(Style.TITLE_POS[0] * self.scale_factor)
        title_y = self.render_area.top + int(Style.TITLE_POS[1] * self.scale_factor)
        subtitle_x = self.render_area.left + int(Style.SUBTITLE_POS[0] * self.scale_factor)
        subtitle_y = self.render_area.top + int(Style.SUBTITLE_POS[1] * self.scale_factor)
        item_start_x_base = int(Style.ITEM_START_POS[0] * self.scale_factor)
        item_start_y_base = int(Style.ITEM_START_POS[1] * self.scale_factor)
        scaled_line_spacing = int(Style.ITEM_LINE_SPACING * self.scale_factor)

        # 渲染標題和副標題
        title_surf = self.font_title.render(menu_title_text, True, Style.TEXT_COLOR)
        surface.blit(title_surf, (title_x, title_y))
        subtitle_surf = self.font_subtitle.render(menu_subtitle_text, True, Style.TEXT_COLOR)
        surface.blit(subtitle_surf, (subtitle_x, subtitle_y + self.font_title.get_height() - scaled_line_spacing //2)) # 調整副標題Y


        # 渲染技能選項
        current_item_y = self.render_area.top + item_start_y_base # 重設 item_y 的起始點
        for i, option_display_name in enumerate(self.display_options):
            color = Style.PLAYER_COLOR if i == self.selected_index else Style.TEXT_COLOR
            item_text_surf = self.font_item.render(option_display_name, True, color)
            
            item_x = self.render_area.left + item_start_x_base
            # 確保 current_item_y 是在 subtitle 下方開始
            if i == 0: # 第一個項目 Y 軸基於副標題
                 current_item_y = subtitle_y + self.font_subtitle.get_height() + scaled_line_spacing // 2
            
            surface.blit(item_text_surf, (item_x, current_item_y))
            current_item_y += scaled_line_spacing


        # 渲染返回提示
        back_text_surf = self.font_item.render(back_text_str, True, Style.TEXT_COLOR)
        back_rect = back_text_surf.get_rect(
            bottomleft=(self.render_area.left + int(20 * self.scale_factor),
                        self.render_area.bottom - int(20 * self.scale_factor))
        )
        surface.blit(back_text_surf, back_rect)



# game/states/menu_states.py
# ... (之前的 import 和 SelectGameModeState, SelectInputPvaState, SelectSkillPvaState 類) ...

# 為了在 RunPvpSkillSelectionState 中使用按鍵映射，我們從 main.py 複製過來
# 理想情況下，這些按鍵映射可以放在一個共享的 constants.py 或 settings.py 中
P1_MENU_KEYS = {
    'UP': pygame.K_w, 'DOWN': pygame.K_s, 'CONFIRM': pygame.K_e, 'CANCEL': pygame.K_q
}
DEFAULT_MENU_KEYS = { # P2 使用預設按鍵
    'UP': pygame.K_UP, 'DOWN': pygame.K_DOWN, 'CONFIRM': pygame.K_RETURN, 'CANCEL': pygame.K_ESCAPE
}

class RunPvpSkillSelectionState(BaseState):
    def __init__(self, game_app):
        super().__init__(game_app)
        self.skills_options = [ # 與 SelectSkillPvaState 共用相同的技能列表
            ("Slow Mo", "slowmo"),
            ("Long Paddle", "long_paddle"),
            ("Soul Eater Bug", "soul_eater_bug")
        ]
        self.display_options = [opt[0] for opt in self.skills_options]

        self.p1_selected_index = 0
        self.p2_selected_index = 0
        self.p1_skill_code = None
        self.p2_skill_code = None

        self.current_selecting_player = 1 # 1 for P1, 2 for P2, 0 for done/showing ready
        self.selection_confirmed_p1 = False
        self.selection_confirmed_p2 = False
        
        self.ready_message_timer_start = 0
        self.ready_message_duration = 2000 # 2秒 "Players Ready" 顯示時間

        self.font_title = None
        self.font_item = None
        self.font_info = None # 用於顯示 "P1 Skill: XXX"
        self.font_large_ready = None # 用於 "Players Ready"

        if DEBUG_MENU_STATE: print(f"[State:RunPvpSkillSelection] Initialized.")

    def on_enter(self, previous_state_data=None):
        super().on_enter(previous_state_data)
        self.p1_selected_index = 0
        self.p2_selected_index = 0
        self.p1_skill_code = None
        self.p2_skill_code = None
        self.current_selecting_player = 1 # P1 先選
        self.selection_confirmed_p1 = False
        self.selection_confirmed_p2 = False
        self.ready_message_timer_start = 0
        
        # 初始化字體 (基於 GameApp 傳遞的 scale_factor)
        scaled_title_font_size = int(Style.TITLE_FONT_SIZE * self.scale_factor) # 用於 "Player X Select Skill"
        scaled_item_font_size = int(Style.ITEM_FONT_SIZE * self.scale_factor)   # 用於技能選項和選擇後的提示
        scaled_large_font_size = int(Style.TITLE_FONT_SIZE * 1.2 * self.scale_factor) # 用於 "Players Ready" (稍大)

        self.font_title = Style.get_font(scaled_title_font_size)
        self.font_item = Style.get_font(scaled_item_font_size)
        self.font_info = Style.get_font(scaled_item_font_size) 
        self.font_large_ready = Style.get_font(scaled_large_font_size)

        if DEBUG_MENU_STATE:
            print(f"[State:RunPvpSkillSelection] Entered. Scale: {self.scale_factor:.2f}, RenderArea: {self.render_area}")
            print(f"    Shared data: GameMode='{self.game_app.shared_game_data.get('selected_game_mode')}'")
            # PvP 模式強制鍵盤，已在 SelectGameModeState 中設定 shared_game_data["selected_input_mode"]

    def _get_current_key_map(self):
        return P1_MENU_KEYS if self.current_selecting_player == 1 else DEFAULT_MENU_KEYS

    def handle_event(self, event):
        if self.current_selecting_player == 0: # 如果正在顯示 "Players Ready"
            return # 不處理按鍵

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
                    self.current_selecting_player = 2 # 切換到 P2 選擇
                    if DEBUG_MENU_STATE: print(f"[State:RunPvpSkillSelection] P1 selected: {self.p1_skill_code}. Now P2 selecting.")
                elif self.current_selecting_player == 2:
                    self.p2_skill_code = selected_skill_code
                    self.selection_confirmed_p2 = True
                    self.current_selecting_player = 0 # 兩人都選擇完畢
                    self.ready_message_timer_start = pygame.time.get_ticks() # 開始計時顯示 "Ready"
                    if DEBUG_MENU_STATE: print(f"[State:RunPvpSkillSelection] P2 selected: {self.p2_skill_code}. Both selected.")
            
            elif event.key == key_map['CANCEL']: # 任一玩家按取消
                self.game_app.sound_manager.play_click()
                if DEBUG_MENU_STATE: print(f"[State:RunPvpSkillSelection] Player {self.current_selecting_player} cancelled. Returning to SelectGameMode.")
                # PvP 技能選擇取消，通常返回到遊戲模式選擇
                self.request_state_change(self.game_app.GameFlowStateName.SELECT_GAME_MODE)
                return # 立即返回，避免後續的 selected_index 更新

            if self.current_selecting_player == 1:
                self.p1_selected_index = current_player_index
            elif self.current_selecting_player == 2:
                self.p2_selected_index = current_player_index

    def update(self, dt):
        if self.current_selecting_player == 0 and self.p1_skill_code and self.p2_skill_code:
            if pygame.time.get_ticks() - self.ready_message_timer_start >= self.ready_message_duration:
                # "Players Ready" 顯示時間到，準備進入遊戲
                self.game_app.shared_game_data["p1_selected_skill"] = self.p1_skill_code
                self.game_app.shared_game_data["p2_selected_skill"] = self.p2_skill_code
                # PvP 模式的 input_mode 已在 SelectGameModeState 中設定為 keyboard
                
                data_for_gameplay = {
                    "game_mode": self.game_app.shared_game_data.get("selected_game_mode"), # 應該是 PvP
                    "input_mode": self.game_app.shared_game_data.get("selected_input_mode"), # 應該是 keyboard
                    "p1_skill": self.p1_skill_code,
                    "p2_skill": self.p2_skill_code
                }
                if DEBUG_MENU_STATE: print(f"[State:RunPvpSkillSelection] Ready message done. Requesting Gameplay state with data: {data_for_gameplay}")
                self.request_state_change(self.game_app.GameFlowStateName.GAMEPLAY, data_for_gameplay)

    def _draw_skill_list(self, surface, player_id_text, area_rect, selected_idx, key_map_for_player):
        # 輔助函數，在指定區域繪製技能列表
        menu_title_text = f"{player_id_text} Select Skill"
        key_up_name = pygame.key.name(key_map_for_player['UP']).upper()
        key_down_name = pygame.key.name(key_map_for_player['DOWN']).upper()
        key_confirm_name = pygame.key.name(key_map_for_player['CONFIRM']).upper()
        menu_subtitle_text = f"({key_up_name}/{key_down_name}, {key_confirm_name})"

        # 位置計算基於 area_rect 和 self.scale_factor
        title_x = area_rect.left + int(20 * self.scale_factor)
        title_y = area_rect.top + int(20 * self.scale_factor)
        
        scaled_title_font_height = self.font_title.get_height()
        subtitle_y = title_y + scaled_title_font_height + int(5 * self.scale_factor)
        scaled_subtitle_font_height = self.font_item.get_height() # 用 item font 近似 subtitle 高度
        
        item_start_y_base = subtitle_y + scaled_subtitle_font_height + int(20 * self.scale_factor)
        item_start_x_base = area_rect.left + int(40 * self.scale_factor)
        scaled_line_spacing = int(Style.ITEM_LINE_SPACING * self.scale_factor)

        title_surf = self.font_title.render(menu_title_text, True, Style.TEXT_COLOR)
        surface.blit(title_surf, (title_x, title_y))
        subtitle_surf = self.font_item.render(menu_subtitle_text, True, Style.TEXT_COLOR) # 副標題用 item font
        surface.blit(subtitle_surf, (title_x, subtitle_y))

        current_item_y = item_start_y_base
        for i, option_display_name in enumerate(self.display_options):
            color = Style.PLAYER_COLOR if i == selected_idx else Style.TEXT_COLOR
            item_text_surf = self.font_item.render(option_display_name, True, color)
            surface.blit(item_text_surf, (item_start_x_base, current_item_y))
            current_item_y += scaled_line_spacing
        
        # (可選) 返回按鈕的提示，但事件已在主 handle_event 中處理
        # key_cancel_name = pygame.key.name(key_map_for_player['CANCEL']).upper()
        # back_text_str = f"<< Back ({key_cancel_name})"
        # back_text_surf = self.font_item.render(back_text_str, True, Style.TEXT_COLOR)
        # back_rect = back_text_surf.get_rect(
        #     bottomleft=(area_rect.left + int(20 * self.scale_factor),
        #                 area_rect.bottom - int(20 * self.scale_factor))
        # )
        # surface.blit(back_text_surf, back_rect)


    def render(self, surface):
        # self.render_area 是 GameApp 為此狀態計算的整個 PvP 技能選擇界面的繪圖區域
        pygame.draw.rect(surface, Style.BACKGROUND_COLOR, self.render_area)
        if not self.font_title or not self.font_item: return

        # 獲取整個 PvP 技能選擇區域的尺寸和偏移
        area_width = self.render_area.width
        area_height = self.render_area.height
        area_left = self.render_area.left
        area_top = self.render_area.top

        # 計算 P1 和 P2 各自的技能選擇子區域 (在螢幕上的絕對像素 Rect)
        p1_skill_select_sub_area = pygame.Rect(
            area_left, area_top,
            area_width // 2, area_height
        )
        p2_skill_select_sub_area = pygame.Rect(
            area_left + area_width // 2, area_top,
            area_width // 2, area_height
        )
        
        # 繪製中間的分割線
        divider_color = (100, 100, 100)
        scaled_divider_thickness = max(1, int(2 * self.scale_factor))
        divider_x_abs = area_left + area_width // 2
        pygame.draw.line(surface, divider_color,
                         (divider_x_abs, area_top),
                         (divider_x_abs, area_top + area_height),
                         scaled_divider_thickness)

        if self.current_selecting_player == 1: # P1 正在選擇
            self._draw_skill_list(surface, "Player 1", p1_skill_select_sub_area, self.p1_selected_index, P1_MENU_KEYS)
            # P2 區域可以顯示等待訊息或保持空白
            pygame.draw.rect(surface, Style.BACKGROUND_COLOR, p2_skill_select_sub_area) # 清理P2區域
            if self.font_info:
                wait_text = self.font_info.render("Player 2 Waiting...", True, Style.TEXT_COLOR)
                wait_rect = wait_text.get_rect(center=p2_skill_select_sub_area.center)
                surface.blit(wait_text, wait_rect)

        elif self.current_selecting_player == 2: # P2 正在選擇
            # P1 區域顯示已選技能
            pygame.draw.rect(surface, Style.BACKGROUND_COLOR, p1_skill_select_sub_area) # 清理P1區域
            if self.p1_skill_code and self.font_info:
                p1_skill_display = self.skills_options[self.p1_selected_index][0] # 獲取顯示名稱
                p1_confirm_text = self.font_info.render(f"P1: {p1_skill_display}", True, Style.PLAYER_COLOR)
                p1_confirm_rect = p1_confirm_text.get_rect(center=p1_skill_select_sub_area.center)
                surface.blit(p1_confirm_text, p1_confirm_rect)
            
            self._draw_skill_list(surface, "Player 2", p2_skill_select_sub_area, self.p2_selected_index, DEFAULT_MENU_KEYS)

        elif self.current_selecting_player == 0: # 兩人都已選擇，顯示 "Players Ready"
            if self.p1_skill_code and self.p2_skill_code and self.font_large_ready:
                # 清理左右區域，然後在整個 render_area 中央顯示 Ready
                pygame.draw.rect(surface, Style.BACKGROUND_COLOR, self.render_area)
                ready_text_str = "Players Ready! Starting..."
                ready_text_render = self.font_large_ready.render(ready_text_str, True, Style.TEXT_COLOR)
                ready_rect = ready_text_render.get_rect(center=self.render_area.center)
                surface.blit(ready_text_render, ready_rect)