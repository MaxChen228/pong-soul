# game/states/level_selection_pva_state.py
import pygame
import os
from game.states.base_state import BaseState
from game.theme import Style
from game.level import LevelManager # 需要 LevelManager
from utils import resource_path     # 需要 resource_path

DEBUG_LEVEL_SELECT_STATE = True

class LevelSelectionPvaState(BaseState):
    def __init__(self, game_app):
        super().__init__(game_app)
        # 使用 game_app 傳過來的 config_manager 實例來初始化 LevelManager
        self.level_manager = LevelManager(config_manager=self.game_app.config_manager,
                                          models_folder=resource_path("models"))
        self.level_names = [] # 將在 on_enter 中填充
        self.display_level_names = [] # 包含索引的顯示名稱
        self.selected_index = 0

        self.font_title = None
        self.font_subtitle = None
        self.font_item = None

        # 用於儲存從 SelectSkillPvaState 傳來的資料
        self.game_mode_data = None
        self.input_mode_data = None
        self.p1_skill_data = None

        if DEBUG_LEVEL_SELECT_STATE: print(f"[State:LevelSelectionPva] Initialized.")

    def on_enter(self, previous_state_data=None):
        super().on_enter(previous_state_data)

        # 保存從上一狀態傳來的數據
        if previous_state_data:
            self.game_mode_data = previous_state_data.get("game_mode")
            self.input_mode_data = previous_state_data.get("input_mode")
            self.p1_skill_data = previous_state_data.get("p1_skill")
            if DEBUG_LEVEL_SELECT_STATE:
                print(f"  Received data: mode={self.game_mode_data}, input={self.input_mode_data}, p1_skill={self.p1_skill_data}")

        self.level_names = [os.path.basename(f).replace(".pth", "").replace("level","Level ") for f in self.level_manager.model_files]
        self.display_level_names = [f"{i+1}. {name}" for i, name in enumerate(self.level_names)]

        self.selected_index = 0 # 每次進入都重置選擇

        scaled_title_font_size = int(Style.TITLE_FONT_SIZE * self.scale_factor)
        scaled_subtitle_font_size = int(Style.SUBTITLE_FONT_SIZE * self.scale_factor)
        scaled_item_font_size = int(Style.ITEM_FONT_SIZE * self.scale_factor)

        self.font_title = Style.get_font(scaled_title_font_size)
        self.font_subtitle = Style.get_font(scaled_subtitle_font_size)
        self.font_item = Style.get_font(scaled_item_font_size)

        if DEBUG_LEVEL_SELECT_STATE: 
            print(f"[State:LevelSelectionPva] Entered. Scale: {self.scale_factor:.2f}, RenderArea: {self.render_area}")
            print(f"  Levels found: {self.level_names}")

        if not self.level_names: # 如果沒有關卡文件
            if DEBUG_LEVEL_SELECT_STATE: print("  No levels found! Will attempt to go back.")
            # 這裡可以選擇是顯示錯誤訊息然後返回，還是直接返回
            # 為了簡單，我們先嘗試直接返回到技能選擇狀態
            self.request_state_change(self.game_app.GameFlowStateName.SELECT_SKILL_PVA, self.persistent_data)


    def handle_event(self, event):
        if not self.level_names: # 如果沒有關卡，不處理輸入
            if event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE: # 允許用ESC退出此空狀態
                self.game_app.sound_manager.play_click()
                self.request_state_change(self.game_app.GameFlowStateName.SELECT_SKILL_PVA, self.persistent_data)
            return

        if event.type == pygame.KEYDOWN:
            if event.key == pygame.K_DOWN:
                self.selected_index = (self.selected_index + 1) % len(self.level_names)
                self.game_app.sound_manager.play_click()
            elif event.key == pygame.K_UP:
                self.selected_index = (self.selected_index - 1 + len(self.level_names)) % len(self.level_names)
                self.game_app.sound_manager.play_click()
            elif event.key == pygame.K_RETURN:
                self.game_app.sound_manager.play_click()
                if DEBUG_LEVEL_SELECT_STATE: print(f"[State:LevelSelectionPva] Selected level index: {self.selected_index} ({self.level_names[self.selected_index]})")

                data_for_gameplay = {
                    "game_mode": self.game_mode_data,
                    "input_mode": self.input_mode_data,
                    "p1_skill": self.p1_skill_data,
                    "p2_skill": None, # PvA 模式 P2 無技能
                    "selected_level_index": self.selected_index # 傳遞選擇的關卡索引
                }
                self.request_state_change(self.game_app.GameFlowStateName.GAMEPLAY, data_for_gameplay)

            elif event.key == pygame.K_ESCAPE: # 按 ESC 返回到 PvA 技能選擇
                self.game_app.sound_manager.play_click()
                if DEBUG_LEVEL_SELECT_STATE: print(f"[State:LevelSelectionPva] ESC pressed, returning to SelectSkillPva.")
                # 將之前從 SelectSkillPvaState 傳來的數據再傳回去，以便它能正確恢復
                data_to_pass_back = {
                    "game_mode": self.game_mode_data,
                    "input_mode": self.input_mode_data
                    # p1_skill 不必傳回，因為技能選擇狀態會重新選擇
                }
                self.request_state_change(self.game_app.GameFlowStateName.SELECT_SKILL_PVA, data_to_pass_back)

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

        title_surf = self.font_title.render("Select Level (PvA)", True, Style.TEXT_COLOR)
        surface.blit(title_surf, (title_x, title_y))
        subtitle_surf = self.font_subtitle.render("(UP/DOWN, ENTER to start, ESC to back)", True, Style.TEXT_COLOR)
        surface.blit(subtitle_surf, (subtitle_x, subtitle_y))

        if not self.level_names:
            error_surf = self.font_item.render("No levels found!", True, Style.TEXT_COLOR)
            error_rect = error_surf.get_rect(center=self.render_area.center)
            surface.blit(error_surf, error_rect)
            # (可選) 添加返回提示
            back_text_surf = self.font_item.render("Press ESC to go back", True, Style.TEXT_COLOR)
            back_rect = back_text_surf.get_rect(midbottom=(self.render_area.centerx, self.render_area.bottom - int(20 * self.scale_factor)))
            surface.blit(back_text_surf, back_rect)
            return

        for i, name_to_display in enumerate(self.display_level_names):
            color = Style.PLAYER_COLOR if i == self.selected_index else Style.TEXT_COLOR
            text_surf = self.font_item.render(name_to_display, True, color)
            item_x = self.render_area.left + item_start_x_base
            item_y = self.render_area.top + item_start_y_base + i * scaled_line_spacing
            surface.blit(text_surf, (item_x, item_y))

        # 返回按鈕的繪製（如果需要明確的返回按鈕文字的話，目前 ESC 鍵提示在副標題中）
        # back_text_str = f"<< Back (ESC)"
        # back_text_surf = self.font_item.render(back_text_str, True, Style.TEXT_COLOR)
        # back_rect = back_text_surf.get_rect(
        #     bottomleft=(self.render_area.left + int(20 * self.scale_factor),
        #                 self.render_area.bottom - int(20 * self.scale_factor))
        # )
        # surface.blit(back_text_surf, back_rect)