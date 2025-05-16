# game/states/level_selection_pva_state.py
import pygame
import os
from game.states.base_state import BaseState
from game.theme import Style
from game.level import LevelManager # 需要 LevelManager
from utils import resource_path     # 需要 resource_path

DEBUG_LEVEL_SELECT_STATE = False

class LevelSelectionPvaState(BaseState):
    def __init__(self, game_app):
        super().__init__(game_app)
        self.level_manager = LevelManager(config_manager=self.game_app.config_manager,
                                          models_folder=resource_path("models"))
        self.level_names = []
        self.display_level_names = []
        self.selected_index = 0
        self.item_rects = []
        self.hover_scale_factor = 1.1 # <--- 新增：懸停縮放比例

        self.font_title = None
        self.font_subtitle = None
        self.font_item = None # 將在 on_enter 中基於 base_scaled_item_font_size 創建

        self.game_mode_data = None
        self.input_mode_data = None
        self.p1_skill_data = None

        if DEBUG_LEVEL_SELECT_STATE: print(f"[State:LevelSelectionPva] Initialized.")

    def on_enter(self, previous_state_data=None):
        super().on_enter(previous_state_data)

        if previous_state_data:
            self.game_mode_data = previous_state_data.get("game_mode")
            self.input_mode_data = previous_state_data.get("input_mode")
            self.p1_skill_data = previous_state_data.get("p1_skill")
            if DEBUG_LEVEL_SELECT_STATE:
                print(f"  Received data: mode={self.game_mode_data}, input={self.input_mode_data}, p1_skill={self.p1_skill_data}")

        self.level_names = [os.path.basename(f).replace(".pth", "").replace("level","Level ") for f in self.level_manager.model_files]
        self.display_level_names = [f"{i+1}. {name}" for i, name in enumerate(self.level_names)]
        
        self.item_rects = [None] * len(self.level_names)
        self.selected_index = 0

        scaled_title_font_size = int(Style.TITLE_FONT_SIZE * self.scale_factor)
        scaled_subtitle_font_size = int(Style.SUBTITLE_FONT_SIZE * self.scale_factor)
        self.base_scaled_item_font_size = int(Style.ITEM_FONT_SIZE * self.scale_factor) # <--- 基礎選項字體大小

        self.font_title = Style.get_font(scaled_title_font_size)
        self.font_subtitle = Style.get_font(scaled_subtitle_font_size)
        self.font_item = Style.get_font(self.base_scaled_item_font_size) # <--- 標準選項字體

        if DEBUG_LEVEL_SELECT_STATE:
            print(f"[State:LevelSelectionPva] Entered. Scale: {self.scale_factor:.2f}, RenderArea: {self.render_area}")
            print(f"  Levels found: {self.level_names}")

        if not self.level_names:
            if DEBUG_LEVEL_SELECT_STATE: print("  No levels found! Will attempt to go back.")
            self.request_state_change(self.game_app.GameFlowStateName.SELECT_SKILL_PVA, self.persistent_data)

    def _confirm_selection(self):
        if not self.level_names: return

        self.game_app.sound_manager.play_click()
        if DEBUG_LEVEL_SELECT_STATE: print(f"[State:LevelSelectionPva] Confirmed level index: {self.selected_index} ({self.level_names[self.selected_index]})")

        data_for_gameplay = {
            "game_mode": self.game_mode_data,
            "input_mode": self.input_mode_data,
            "p1_skill": self.p1_skill_data,
            "p2_skill": None,
            "selected_level_index": self.selected_index
        }
        self.request_state_change(self.game_app.GameFlowStateName.GAMEPLAY, data_for_gameplay)

    def handle_event(self, event):
        if not self.level_names:
            if event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE:
                self.game_app.sound_manager.play_click()
                self.request_state_change(self.game_app.GameFlowStateName.SELECT_SKILL_PVA, self.persistent_data)
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
                        self._confirm_selection()
                        return

        if event.type == pygame.KEYDOWN:
            if event.key == pygame.K_DOWN:
                self.selected_index = (self.selected_index + 1) % len(self.level_names)
                self.game_app.sound_manager.play_click()
            elif event.key == pygame.K_UP:
                self.selected_index = (self.selected_index - 1 + len(self.level_names)) % len(self.level_names)
                self.game_app.sound_manager.play_click()
            elif event.key == pygame.K_RETURN:
                self._confirm_selection()
            elif event.key == pygame.K_ESCAPE:
                self.game_app.sound_manager.play_click()
                if DEBUG_LEVEL_SELECT_STATE: print(f"[State:LevelSelectionPva] ESC pressed, returning to SelectSkillPva.")
                data_to_pass_back = {
                    "game_mode": self.game_mode_data,
                    "input_mode": self.input_mode_data
                }
                self.request_state_change(self.game_app.GameFlowStateName.SELECT_SKILL_PVA, data_to_pass_back)

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

        title_surf = self.font_title.render("Select Level (PvA)", True, Style.TEXT_COLOR)
        surface.blit(title_surf, (title_x, title_y))
        
        subtitle_text_new = "(UP/DOWN/Mouse, ENTER/Click to start, ESC to back)"
        subtitle_surf = self.font_subtitle.render(subtitle_text_new, True, Style.TEXT_COLOR)
        surface.blit(subtitle_surf, (subtitle_x, subtitle_y))

        if not self.level_names:
            error_surf = self.font_item.render("No levels found!", True, Style.TEXT_COLOR)
            error_rect = error_surf.get_rect(center=self.render_area.center)
            surface.blit(error_surf, error_rect)
            back_text_surf = self.font_item.render("Press ESC to go back", True, Style.TEXT_COLOR)
            back_rect = back_text_surf.get_rect(midbottom=(self.render_area.centerx, self.render_area.bottom - int(20 * self.scale_factor)))
            surface.blit(back_text_surf, back_rect)
            return

        current_item_y_abs = item_start_y_base_abs
        for i, name_to_display in enumerate(self.display_level_names):
            is_selected = (i == self.selected_index)
            color = Style.PLAYER_COLOR if is_selected else Style.TEXT_COLOR
            
            original_text_surf = self.font_item.render(name_to_display, True, color)
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