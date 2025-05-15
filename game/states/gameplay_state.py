# game/states/gameplay_state.py
import pygame
import random # 需要隨機發球等
import os     # 需要 os.path.exists
import time   # 需要 time.sleep (雖然Renderer有clock.tick)

from game.states.base_state import BaseState
from game.theme import Style
from game.settings import GameSettings
from envs.pong_duel_env import PongDuelEnv # 遊戲環境
from game.ai_agent import AIAgent         # AI 代理
from game.level import LevelManager       # 關卡管理器
from utils import resource_path           # 資源路徑輔助函數
from game.constants import P1_GAME_CONTROLS, P2_GAME_CONTROLS


DEBUG_GAMEPLAY_STATE = True

class GameplayState(BaseState):
    def __init__(self, game_app):
        super().__init__(game_app)
        self.env = None
        self.ai_agent = None
        
        # 從 shared_game_data 獲取的遊戲參數
        self.current_game_mode = None
        self.current_input_mode = "keyboard" # 預設
        self.p1_skill_code = None
        self.p2_skill_code = None # PvP 模式下 P2 的技能

        self.game_session_result_state_name = self.game_app.GameFlowStateName.SELECT_GAME_MODE # 預設返回狀態

        # 用於倒數和結果橫幅的臨時解決方案
        self.font_countdown = None
        self.font_banner = None

        # 遊戲內的邏輯，例如 freeze timer，現在由 env 管理
        # 但像回合結束後的短暫等待，或遊戲結束後的等待，可能由狀態管理
        self.round_over_display_start_time = 0
        self.round_over_display_duration = 500 # 回合間的短暫停頓 (ms), 替代 freeze_duration
        self.is_round_over_displaying = False

        self.game_over_banner_shown = False # 避免重複顯示遊戲結束橫幅

    def on_enter(self, previous_state_data=None):
        super().on_enter(previous_state_data) # 這會將 previous_state_data 更新到 self.persistent_data
        if DEBUG_GAMEPLAY_STATE: print(f"[State:Gameplay] Entered. Data from prev state (self.persistent_data): {self.persistent_data}")

        # 1. 從 self.persistent_data (由前一狀態傳入) 獲取遊戲設定
        #    或者從 game_app.shared_game_data (作為備用，但不推薦依賴此處的關卡索引)
        self.current_game_mode = self.persistent_data.get("game_mode", 
                                                          self.game_app.shared_game_data.get("selected_game_mode", GameSettings.GameMode.PLAYER_VS_AI))
        self.current_input_mode = self.persistent_data.get("input_mode", 
                                                            self.game_app.shared_game_data.get("selected_input_mode", "keyboard"))
        self.p1_skill_code = self.persistent_data.get("p1_skill", 
                                                  self.game_app.shared_game_data.get("p1_selected_skill"))
        self.p2_skill_code = self.persistent_data.get("p2_skill", 
                                                  self.game_app.shared_game_data.get("p2_selected_skill")) # PvP 時會有 P2 技能

        # ⭐️ 新增：直接從 persistent_data 獲取選擇的關卡索引 (僅 PvA 模式需要)
        selected_level_index = None
        if self.current_game_mode == GameSettings.GameMode.PLAYER_VS_AI:
            selected_level_index = self.persistent_data.get("selected_level_index")
            if selected_level_index is None:
                if DEBUG_GAMEPLAY_STATE: 
                    print("[State:Gameplay] CRITICAL WARNING: No 'selected_level_index' received for PvA mode. Defaulting to 0 or erroring.")
                # 可以選擇一個預設關卡，或者拋出錯誤/返回選單
                # 為了讓遊戲能運行，我們暫時預設為 0，但這表示流程可能有問題
                selected_level_index = 0 
                # 或者更好地是返回上一個狀態
                # self.request_state_change(self.game_app.GameFlowStateName.SELECT_LEVEL_PVA, self.persistent_data)
                # return # 提前退出 on_enter

        if DEBUG_GAMEPLAY_STATE:
            print(f"    Mode: {self.current_game_mode}, Input: {self.current_input_mode}")
            print(f"    P1 Skill: {self.p1_skill_code}, P2 Skill: {self.p2_skill_code}")
            if self.current_game_mode == GameSettings.GameMode.PLAYER_VS_AI:
                print(f"    Selected Level Index (PvA): {selected_level_index}")


        # 2. 初始化 PongDuelEnv 
        common_game_config = {
            'mass': 1.0, 'e_ball_paddle': 1.0, 'mu_ball_paddle': 0.4, 'enable_spin': True, 
            'magnus_factor': 0.01, 'speed_increment': 0.002, 'speed_scale_every': 3, 
            'initial_ball_speed': 0.025, 'initial_angle_deg_range': [-45, 45],
            'freeze_duration_ms': GameSettings.FREEZE_DURATION_MS,
            'countdown_seconds': GameSettings.COUNTDOWN_SECONDS,
            'bg_music': "bg_music_level1.mp3" 
        }
        render_size_for_env = 400 
        paddle_height_for_env = 10
        ball_radius_for_env = 10
        player1_env_config = {}
        opponent_env_config = {}
        self.ai_agent = None

        if self.current_game_mode == GameSettings.GameMode.PLAYER_VS_AI:
            # 使用 game_app 傳過來的 config_manager 實例來初始化 LevelManager
            levels = LevelManager(config_manager=self.game_app.config_manager,
                                  models_folder=resource_path("models"))
            
            # ⭐️ 使用從 persistent_data 傳來的 selected_level_index
            if selected_level_index is not None and 0 <= selected_level_index < len(levels.model_files):
                levels.current_level = selected_level_index
            else:
                if DEBUG_GAMEPLAY_STATE: 
                    print(f"    Invalid selected_level_index ({selected_level_index}) or no levels. Defaulting to level 0.")
                levels.current_level = 0 # 安全回退
                if not levels.model_files: # 如果真的沒有模型文件
                    print("[State:Gameplay] CRITICAL: No model files found by LevelManager. Cannot start PvA game.")
                    # 應該返回到一個安全的選單狀態，例如遊戲模式選擇
                    self.request_state_change(self.game_app.GameFlowStateName.SELECT_GAME_MODE)
                    return # 提前退出 on_enter


            level_specific_config = levels.get_current_config()
            if not level_specific_config: # 如果 YAML 讀取失敗或不存在
                if DEBUG_GAMEPLAY_STATE: print(f"    Failed to load config for level {levels.current_level}. Using defaults.")
                level_specific_config = { # 提供一個最小的預設配置
                    'player_life': 3, 'ai_life': 3, 'player_paddle_width': 100, 'ai_paddle_width': 60,
                    'initial_speed': 0.02, 'bg_music': "bg_music_level1.mp3",
                    # freeze_duration_ms 應該從 common_game_config 獲取
                }
            
            common_game_config.update(level_specific_config) # 用關卡特定配置覆蓋通用配置
            
            player1_env_config = {
                'initial_x': 0.5, 
                'initial_paddle_width': level_specific_config.get('player_paddle_width', 100),
                'initial_lives': level_specific_config.get('player_life', 3), 
                'skill_code': self.p1_skill_code, 
                'is_ai': False
            }
            opponent_env_config = {
                'initial_x': 0.5, 
                'initial_paddle_width': level_specific_config.get('ai_paddle_width', 60),
                'initial_lives': level_specific_config.get('ai_life', 3), 
                'skill_code': None, # AI 通常不主動使用玩家可選技能
                'is_ai': True
            }
            relative_model_path = levels.get_current_model_path()
            if relative_model_path:
                absolute_model_path = resource_path(relative_model_path)
                if os.path.exists(absolute_model_path): 
                    self.ai_agent = AIAgent(absolute_model_path)
                    if DEBUG_GAMEPLAY_STATE: print(f"    AI Agent loaded from: {absolute_model_path}")
                else: 
                    print(f"[GameplayState] AI model not found at: {absolute_model_path}. AI will be inactive.")
            else:
                 print("[GameplayState] No AI model path found for current level. AI will be inactive.")


        elif self.current_game_mode == GameSettings.GameMode.PLAYER_VS_PLAYER:
            pvp_game_specific_config = {
                'player1_paddle_width': 100, 'player1_lives': 3,
                'player2_paddle_width': 100, 'player2_lives': 3,
                'bg_music': "bg_music_pvp.mp3",
            }
            common_game_config.update(pvp_game_specific_config)
            player1_env_config = {
                'initial_x': 0.5, 
                'initial_paddle_width': pvp_game_specific_config.get('player1_paddle_width', 100),
                'initial_lives': pvp_game_specific_config.get('player1_lives', 3), 
                'skill_code': self.p1_skill_code, 
                'is_ai': False
            }
            opponent_env_config = { # 在 PvP 中，"opponent" 是 P2
                'initial_x': 0.5, 
                'initial_paddle_width': pvp_game_specific_config.get('player2_paddle_width', 100),
                'initial_lives': pvp_game_specific_config.get('player2_lives', 3), 
                'skill_code': self.p2_skill_code, # P2 的技能
                'is_ai': False # P2 不是 AI
            }
        
        self.env = PongDuelEnv(
            game_mode=self.current_game_mode,
            player1_config=player1_env_config,
            opponent_config=opponent_env_config,
            common_config=common_game_config,
            render_size=render_size_for_env,
            paddle_height_px=paddle_height_for_env,
            ball_radius_px=ball_radius_for_env,
            initial_main_screen_surface_for_renderer=self.game_app.main_screen
        )
        self.obs, _ = self.env.reset() # reset 會初始化球的位置和速度
        
        if self.env:
            self.env.render() 
            if not self.env.renderer or not self.env.renderer.window:
                if DEBUG_GAMEPLAY_STATE: print("[GameplayState.on_enter] CRITICAL: Renderer failed to initialize.")
                self.request_state_change(self.game_app.GameFlowStateName.SELECT_GAME_MODE) 
                return 
        else:
            if DEBUG_GAMEPLAY_STATE: print("[GameplayState.on_enter] CRITICAL: self.env is None after creation attempt.")
            self.request_quit()
            return

        # 3. 播放背景音樂
        bg_music_to_play = common_game_config.get("bg_music", "bg_music_level1.mp3")
        if hasattr(self.env, 'sound_manager') and self.env.sound_manager and bg_music_to_play:
            bg_music_path = resource_path(f"assets/{bg_music_to_play}")
            if os.path.exists(bg_music_path):
                try:
                    pygame.mixer.music.load(bg_music_path)
                    pygame.mixer.music.set_volume(GameSettings.BACKGROUND_MUSIC_VOLUME)
                    self.env.sound_manager.play_bg_music() # 使用 env 的 sound_manager 播放
                except pygame.error as e:
                    if DEBUG_GAMEPLAY_STATE: print(f"[GameplayState] Error loading/playing music '{bg_music_path}': {e}")
            else:
                if DEBUG_GAMEPLAY_STATE: print(f"[GameplayState] Warning: Music file not found: {bg_music_path}")

        # 4. 遊戲開始倒數
        initial_countdown_duration = common_game_config.get('countdown_seconds', GameSettings.COUNTDOWN_SECONDS)
        if initial_countdown_duration > 0 and self.env and self.env.renderer: # 確保 env 和 renderer 已準備好
            if DEBUG_GAMEPLAY_STATE: print(f"[GameplayState] Starting initial countdown for {initial_countdown_duration} seconds.")
            self._show_countdown_internal(initial_countdown_duration) # 這個方法依賴 self.env.renderer

        self.game_over_banner_shown = False
        self.is_round_over_displaying = False
        if DEBUG_GAMEPLAY_STATE: print(f"[State:Gameplay] on_enter finished successfully.")


    def _show_countdown_internal(self, seconds):
        """內部實現的倒數計時顯示，直接在 main_screen 上繪製。"""
        # Renderer 已經初始化並設定了 self.env.renderer.window 為 main_screen
        if not self.env or not self.env.renderer or not self.env.renderer.window:
            print("[GameplayState._show_countdown_internal] Error: Env or Renderer not ready.")
            return

        screen_to_draw_on = self.env.renderer.window # 即 self.game_app.main_screen
        # 倒計時文字大小應基於遊戲內容的縮放因子
        # Renderer 應該有一個方法或屬性提供遊戲內容的縮放因子和居中渲染區域
        # 假設 Renderer 有 self.env.renderer.game_content_render_area_on_screen
        # 和 self.env.renderer.game_content_scale_factor
        
        base_font_size = 60
        scale = getattr(self.env.renderer, 'game_content_scale_factor', 1.0)
        scaled_font_size = int(base_font_size * scale)
        if not self.font_countdown or self.font_countdown.get_height() != Style.get_font(scaled_font_size).get_height(): # 避免重複創建相同字體
            self.font_countdown = Style.get_font(scaled_font_size)

        game_area_center_x, game_area_center_y = screen_to_draw_on.get_width() // 2, screen_to_draw_on.get_height() // 2
        if hasattr(self.env.renderer, 'game_content_render_area_on_screen'): # 如果Renderer提供了遊戲內容的實際渲染區域
            game_render_rect = self.env.renderer.game_content_render_area_on_screen
            game_area_center_x = game_render_rect.centerx
            game_area_center_y = game_render_rect.centery
        
        for i in range(seconds, 0, -1):
            if hasattr(self.env, 'sound_manager') and self.env.sound_manager:
                self.env.sound_manager.play_countdown()
            
            # 倒數計時的背景應該是當前遊戲畫面的樣子，所以我們先渲染遊戲
            if self.env: self.env.render() # 這會 flip
            
            countdown_surface = self.font_countdown.render(str(i), True, Style.TEXT_COLOR)
            countdown_rect = countdown_surface.get_rect(center=(game_area_center_x, game_area_center_y))
            screen_to_draw_on.blit(countdown_surface, countdown_rect) # 直接畫在 env.render() 之後的表面上
            
            pygame.display.flip() # 確保倒計時數字更新顯示
            pygame.time.wait(1000)
        
        # 倒數結束後，可能需要再渲染一次乾淨的遊戲畫面
        if self.env: self.env.render()


    def _show_result_banner_internal(self, text, color):
        """內部實現的結果橫幅顯示。"""
        if not self.env or not self.env.renderer or not self.env.renderer.window:
            print("[GameplayState._show_result_banner_internal] Error: Env or Renderer not ready.")
            return
        screen_to_draw_on = self.env.renderer.window
        base_font_size = 40
        scale = getattr(self.env.renderer, 'game_content_scale_factor', 1.0)
        scaled_font_size = int(base_font_size * scale)
        if not self.font_banner or self.font_banner.get_height() != Style.get_font(scaled_font_size).get_height():
            self.font_banner = Style.get_font(scaled_font_size)

        game_area_center_x, game_area_center_y = screen_to_draw_on.get_width() // 2, screen_to_draw_on.get_height() // 2
        if hasattr(self.env.renderer, 'game_content_render_area_on_screen'):
            game_render_rect = self.env.renderer.game_content_render_area_on_screen
            game_area_center_x = game_render_rect.centerx
            game_area_center_y = game_render_rect.centery

        # 橫幅顯示前也先渲染遊戲背景
        if self.env: self.env.render()

        banner_surface = self.font_banner.render(text, True, color)
        banner_rect = banner_surface.get_rect(center=(game_area_center_x, game_area_center_y))
        screen_to_draw_on.blit(banner_surface, banner_rect)
        pygame.display.flip()
        pygame.time.delay(2000) # 原版是 delay，不是 wait
        self.game_over_banner_shown = True


    def handle_event(self, event):
        if event.type == pygame.KEYDOWN:
            if event.key == pygame.K_ESCAPE:
                if DEBUG_GAMEPLAY_STATE: print("[State:Gameplay] ESC pressed. Requesting state change to SelectGameMode.")
                self.request_state_change(self.game_app.GameFlowStateName.SELECT_GAME_MODE)
        # 遊戲內的按鍵（移動、技能）在 update 方法中通過 pygame.key.get_pressed() 處理

    def update(self, dt): # dt 目前未使用，因為遊戲邏輯是基於幀的
        if not self.env or self.game_over_banner_shown : # 如果環境未初始化或遊戲結束橫幅已顯示，則不更新
            return
        
        if self.is_round_over_displaying: # 如果正在顯示回合結束後的短暫停頓
            if pygame.time.get_ticks() - self.round_over_display_start_time >= self.round_over_display_duration:
                self.is_round_over_displaying = False
                # 停頓結束，重置球並獲取新觀察值 (如果遊戲未結束)
                if not (self.env.player1.lives <= 0 or self.env.opponent.lives <= 0):
                    if self.last_scorer == 'player1': self.env.reset_ball_after_score(scored_by_player1=True)
                    elif self.last_scorer == 'opponent': self.env.reset_ball_after_score(scored_by_player1=False)
                    else: self.env.reset_ball_after_score(scored_by_player1=random.choice([True, False]))
                    self.obs = self.env._get_obs()
                    if DEBUG_GAMEPLAY_STATE: print("[State:Gameplay] Round over display finished. Ball reset.")
            else:
                return # 仍在回合結束停頓中，不執行遊戲邏輯


        # --- 複製自舊 game_session 的遊戲主迴圈核心邏輯 ---
        keys = pygame.key.get_pressed()
        p1_ingame_action = 1

        if self.current_input_mode == "keyboard":
            if keys[P1_GAME_CONTROLS['LEFT_KB']]: p1_ingame_action = 0
            elif keys[P1_GAME_CONTROLS['RIGHT_KB']]: p1_ingame_action = 2
        elif self.current_input_mode == "mouse" and self.current_game_mode == GameSettings.GameMode.PLAYER_VS_AI:
            mouse_x_abs, mouse_y_abs = pygame.mouse.get_pos()
            logical_mouse_x = -1
            if hasattr(self.env.renderer, 'game_area_rect_on_screen') and \
               hasattr(self.env.renderer, 'game_content_scale_factor'):
                game_rect = self.env.renderer.game_area_rect_on_screen
                scale = self.env.renderer.game_content_scale_factor
                if game_rect.collidepoint(mouse_x_abs, mouse_y_abs) and scale > 0:
                    mouse_x_in_scaled_area = mouse_x_abs - game_rect.left
                    mouse_x_logical_pixels = mouse_x_in_scaled_area / scale
                    if self.env.render_size > 0:
                        logical_mouse_x = mouse_x_logical_pixels / self.env.render_size
                        logical_mouse_x = max(0.0, min(1.0, logical_mouse_x))
            
            if logical_mouse_x != -1:
                threshold = 0.02
                if logical_mouse_x < self.env.player1.x - threshold: p1_ingame_action = 0
                elif logical_mouse_x > self.env.player1.x + threshold: p1_ingame_action = 2
        
        if keys[P1_GAME_CONTROLS['SKILL_KB']]:
            self.env.activate_skill(self.env.player1)

        opponent_ingame_action = 1
        if self.current_game_mode == GameSettings.GameMode.PLAYER_VS_AI:
            if self.ai_agent: opponent_ingame_action = self.ai_agent.select_action(self.obs.copy())
        else: # PvP
            if keys[P2_GAME_CONTROLS['LEFT']]: opponent_ingame_action = 0
            elif keys[P2_GAME_CONTROLS['RIGHT']]: opponent_ingame_action = 2
            if keys[P2_GAME_CONTROLS['SKILL']]:
                self.env.activate_skill(self.env.opponent)
        
        self.obs, reward, round_done, game_over, info = self.env.step(p1_ingame_action, opponent_ingame_action)

        if round_done:
            if DEBUG_GAMEPLAY_STATE: print(f"[State:Gameplay] Round Done. Info: {info}. P1_Lives: {self.env.player1.lives}, Opp_Lives: {self.env.opponent.lives}")
            
            self.last_scorer = info.get('scorer') # 記住得分者，以便在停頓後正確發球

            if game_over:
                if DEBUG_GAMEPLAY_STATE: print(f"[State:Gameplay] Game Over detected.")
                # 顯示勝利/失敗橫幅
                p1_wins_msg = "PLAYER 1 WINS!" if self.current_game_mode == GameSettings.GameMode.PLAYER_VS_PLAYER else "YOU WIN!"
                p1_loses_msg = "PLAYER 2 WINS!" if self.current_game_mode == GameSettings.GameMode.PLAYER_VS_PLAYER else "YOU LOSE!"
                
                if self.env.player1.lives <= 0:
                    if self.env.sound_manager: self.env.sound_manager.play_lose_sound()
                    self._show_result_banner_internal(p1_loses_msg, Style.AI_COLOR)
                elif self.env.opponent.lives <= 0:
                    if self.env.sound_manager: self.env.sound_manager.play_win_sound()
                    self._show_result_banner_internal(p1_wins_msg, Style.PLAYER_COLOR)
                
                # 遊戲結束後，請求返回遊戲模式選擇
                self.request_state_change(self.game_app.GameFlowStateName.SELECT_GAME_MODE)
                return # 避免後續的 reset_ball_after_score
            else:
                # 回合結束，但遊戲未結束，進入短暫停頓
                self.is_round_over_displaying = True
                self.round_over_display_start_time = pygame.time.get_ticks()
                # 在停頓結束後再 reset_ball_after_score
                if DEBUG_GAMEPLAY_STATE: print(f"[State:Gameplay] Round ended, not game over. Scorer: {self.last_scorer}. Displaying round over.")
        # --- 舊 game_session 核心邏輯結束 ---

    def render(self, surface): # surface 就是 self.game_app.main_screen
        if self.env and self.env.renderer:
            self.env.render() # PongDuelEnv.render() 內部會調用 Renderer.render()，Renderer 會 flip
        else:
            # 如果 env 還沒準備好，可以畫一個載入畫面或保持背景色
            # GameApp 的 run() 已經填充了背景色
            pass 
            # if DEBUG_GAMEPLAY_STATE: print("[State:Gameplay] Env or Renderer not ready for rendering.")

    def on_exit(self):
        if DEBUG_GAMEPLAY_STATE: print("[State:Gameplay] Exiting.")
        if self.env:
            if hasattr(self.env, 'sound_manager'):
                self.env.sound_manager.stop_bg_music()
            self.env.close() # 清理 PongDuelEnv 資源
            self.env = None
        return super().on_exit() # 返回 persistent_data