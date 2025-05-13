# main.py (修正版 - 階段 1.3)

import pygame
import sys
import time
import os
# import torch # 暫時不需要直接在此處使用
# import numpy # 暫時不需要直接在此處使用

# 初始化 pygame 系統 (應在最開始執行一次)
pygame.init()
pygame.font.init() # 字型模組初始化
import random
# 專案路徑設定
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from envs.pong_duel_env import PongDuelEnv
from game.ai_agent import AIAgent
from game.level import LevelManager
from game.theme import Style # 假設 Style 和 Theme 正常運作
from game.menu import (
    show_level_selection,
    select_input_method,
    select_skill,
    select_game_mode
)
from game.settings import GameSettings
from game.sound import SoundManager
from utils import resource_path

DEBUG_MAIN = True # ⭐️ 除錯開關

# --- 倒數與結果顯示函數 (保持不變) ---
def show_countdown(env):
    font = Style.get_font(60)
    if not env.renderer or not env.renderer.window: # 檢查 renderer 和 window 是否存在
        if DEBUG_MAIN: print("[show_countdown] Warning: env.renderer.window not initialized. Forcing render.")
        env.render()
        if not env.renderer or not env.renderer.window:
            if DEBUG_MAIN: print("[show_countdown] Error: env.renderer.window could not be initialized.")
            return

    screen = env.renderer.window
    for i in range(GameSettings.COUNTDOWN_SECONDS, 0, -1):
        if hasattr(env, 'sound_manager') and env.sound_manager:
            env.sound_manager.play_countdown()

        screen.fill(Style.BACKGROUND_COLOR)
        countdown_surface = font.render(str(i), True, Style.TEXT_COLOR)
        offset_y_val = env.renderer.offset_y if hasattr(env, 'renderer') and env.renderer else 0
        countdown_rect = countdown_surface.get_rect(
            center=(env.render_size // 2, env.render_size // 2 + offset_y_val)
        )
        screen.blit(countdown_surface, countdown_rect)
        pygame.display.flip()
        pygame.time.wait(1000)

def show_result_banner(screen, text, color):
    if not screen:
        if DEBUG_MAIN: print(f"[show_result_banner] Error: Screen not available for text: {text}")
        return
    font = Style.get_font(40)
    screen.fill(Style.BACKGROUND_COLOR)
    banner = font.render(text, True, color)
    rect = banner.get_rect(center=(screen.get_width() // 2, screen.get_height() // 2))
    screen.blit(banner, rect)
    pygame.display.flip()
    pygame.time.delay(2000) # 延長顯示時間以便觀察

# --- 按鍵映射定義 (保持不變) ---
P1_MENU_KEYS = {
    'UP': pygame.K_w, 'DOWN': pygame.K_s, 'CONFIRM': pygame.K_e, 'CANCEL': pygame.K_q
}
DEFAULT_MENU_KEYS = {
    'UP': pygame.K_UP, 'DOWN': pygame.K_DOWN, 'CONFIRM': pygame.K_RETURN, 'CANCEL': pygame.K_ESCAPE
}

# ⭐️ 新增: PvP 模式下玩家二的遊戲內按鍵 (稍後會移到 GameSettings)
P2_GAME_KEYS = {
    'LEFT': pygame.K_j,
    'RIGHT': pygame.K_l,
    'SKILL': pygame.K_u # 技能鍵暫時保留，階段二處理
}
# ⭐️ 新增: 玩家一的遊戲內按鍵
P1_GAME_KEYS = {
    'LEFT_KB': pygame.K_LEFT, #鍵盤左
    'RIGHT_KB': pygame.K_RIGHT, #鍵盤右
    'SKILL_KB': pygame.K_x, #鍵盤技能
    # 滑鼠控制會在遊戲迴圈中特別處理
}


# --- PVP 選單階段處理 (保持不變) ---
def run_pvp_selection_phase(main_screen, sound_manager_instance):
    screen_width = main_screen.get_width()
    screen_height = main_screen.get_height()
    left_rect = pygame.Rect(0, 0, screen_width // 2, screen_height)
    right_rect = pygame.Rect(screen_width // 2, 0, screen_width // 2, screen_height)
    divider_color = (100, 100, 100)
    player1_selected_skill = None
    player2_selected_skill = None

    main_screen.fill(Style.BACKGROUND_COLOR)
    pygame.draw.line(main_screen, divider_color, (screen_width // 2, 0), (screen_width // 2, screen_height), 2)

    if DEBUG_MAIN: print("[run_pvp_selection_phase] Player 1 selecting skill...")
    player1_selected_skill = select_skill(
        main_screen_surface=main_screen, render_area=left_rect, key_map=P1_MENU_KEYS,
        sound_manager=sound_manager_instance, player_identifier="Player 1"
    )
    if player1_selected_skill is None:
        if DEBUG_MAIN: print("[run_pvp_selection_phase] Player 1 cancelled.")
        return None, None

    pygame.draw.rect(main_screen, Style.BACKGROUND_COLOR, left_rect)
    font_info = Style.get_font(Style.ITEM_FONT_SIZE)
    p1_info_text = font_info.render(f"P1 Skill: {player1_selected_skill}", True, Style.TEXT_COLOR)
    main_screen.blit(p1_info_text, (left_rect.left + 20, left_rect.centery))
    pygame.draw.line(main_screen, divider_color, (screen_width // 2, 0), (screen_width // 2, screen_height), 2)

    if DEBUG_MAIN: print(f"[run_pvp_selection_phase] Player 1 selected: {player1_selected_skill}. Player 2 selecting...")
    player2_selected_skill = select_skill(
        main_screen_surface=main_screen, render_area=right_rect, key_map=DEFAULT_MENU_KEYS,
        sound_manager=sound_manager_instance, player_identifier="Player 2"
    )
    if player2_selected_skill is None:
        if DEBUG_MAIN: print("[run_pvp_selection_phase] Player 2 cancelled.")
        return player1_selected_skill, None # 即使P2取消，也可能需要返回P1的選擇

    pygame.draw.rect(main_screen, Style.BACKGROUND_COLOR, right_rect)
    p2_info_text = font_info.render(f"P2 Skill: {player2_selected_skill}", True, Style.TEXT_COLOR)
    main_screen.blit(p2_info_text, (right_rect.left + 20, right_rect.centery))
    
    if DEBUG_MAIN: print(f"[run_pvp_selection_phase] Player 2 selected: {player2_selected_skill}.")
    main_screen.fill(Style.BACKGROUND_COLOR)
    font_large = Style.get_font(Style.TITLE_FONT_SIZE)
    ready_text_str = "Players Ready! Starting..."
    if not player1_selected_skill or not player2_selected_skill:
         ready_text_str = "Skill selection incomplete!" # 如果有人取消
    ready_text = font_large.render(ready_text_str, True, Style.TEXT_COLOR)
    ready_rect = ready_text.get_rect(center=(screen_width // 2, screen_height // 2))
    main_screen.blit(ready_text, ready_rect)
    pygame.display.flip()
    pygame.time.wait(2000)
    return player1_selected_skill, player2_selected_skill

# --- 遊戲會話管理 (核心修改) ---
def game_session(current_input_mode, p1_skill_code_from_menu, p2_skill_code_from_menu, current_game_mode_value):
    if DEBUG_MAIN: print(f"[game_session] Starting. Mode: {current_game_mode_value}, P1 Skill: {p1_skill_code_from_menu}, P2 Skill: {p2_skill_code_from_menu}, P1 Input: {current_input_mode}")

    levels = LevelManager(models_folder=resource_path("models"))
    common_game_config = {} # 存放球速、物理等
    player1_env_config = {}
    opponent_env_config = {}
    ai_agent = None # AI實例

    # 預設通用遊戲參數 (可從 common_settings.yaml 讀取)
    common_game_config = {
        'mass': 1.0, 'e_ball_paddle': 1.0, 'mu_ball_paddle': 0.4,
        'enable_spin': True, 'magnus_factor': 0.01,
        'speed_increment': 0.002, 'speed_scale_every': 3,
        'initial_ball_speed': 0.025, # 稍微提高一點初始速度
        'initial_angle_deg_range': [-45, 45],
        'freeze_duration_ms': GameSettings.FREEZE_DURATION_MS, # 從全域設定讀取
        'countdown_seconds': GameSettings.COUNTDOWN_SECONDS, # 從全域設定讀取
        'bg_music': "bg_music_level1.mp3" # 預設背景音樂
    }

    render_size_for_env = 400 # 遊戲區域的渲染寬度
    paddle_height_for_env = 10
    ball_radius_for_env = 10


    if current_game_mode_value == GameSettings.GameMode.PLAYER_VS_AI:
        selected_level_index = show_level_selection() # 此函數管理自己的螢幕
        if selected_level_index is None:
            if DEBUG_MAIN: print("[game_session] PVA: Level selection cancelled.")
            return "select_game_mode" # 返回到模式選擇
        levels.current_level = selected_level_index
        
        level_specific_config = levels.get_current_config() # PvA關卡配置
        if not level_specific_config:
            if DEBUG_MAIN: print(f"[game_session] PVA: Failed to load config for level {selected_level_index}. Using defaults.")
            level_specific_config = { # 提供一個最小的後備配置
                'player_life': 3, 'ai_life': 3, 'player_paddle_width': 100, 'ai_paddle_width': 60,
                'initial_speed': 0.02, 'bg_music': "bg_music_level1.mp3"
            }

        # 更新通用配置 (關卡配置可以覆蓋通用配置中的某些項)
        common_game_config['initial_ball_speed'] = level_specific_config.get('initial_speed', common_game_config['initial_ball_speed'])
        common_game_config['bg_music'] = level_specific_config.get('bg_music', common_game_config['bg_music'])
        # ... 其他可以被關卡覆蓋的通用參數

        player1_env_config = {
            'initial_x': 0.5,
            'initial_paddle_width': level_specific_config.get('player_paddle_width', 100),
            'initial_lives': level_specific_config.get('player_life', 3),
            'skill_code': p1_skill_code_from_menu,
            'is_ai': False
        }
        opponent_env_config = {
            'initial_x': 0.5,
            'initial_paddle_width': level_specific_config.get('ai_paddle_width', 60),
            'initial_lives': level_specific_config.get('ai_life', 3),
            'skill_code': None, # AI 目前不使用選單選擇的技能
            'is_ai': True
        }
        
        relative_model_path = levels.get_current_model_path()
        if relative_model_path:
            absolute_model_path = resource_path(relative_model_path)
            if os.path.exists(absolute_model_path):
                ai_agent = AIAgent(absolute_model_path)
                if DEBUG_MAIN: print(f"[game_session] PVA: AI Agent loaded from {absolute_model_path}")
            else:
                if DEBUG_MAIN: print(f"[game_session] PVA: AI model file not found at {absolute_model_path}. AI will not function.")
        else:
            if DEBUG_MAIN: print("[game_session] PVA: No AI model path specified for this level. AI will not function.")

    elif current_game_mode_value == GameSettings.GameMode.PLAYER_VS_PLAYER:
        # PvP 模式使用另一套配置，或預設值
        # 假設有 pvp_settings.yaml 或使用硬編碼預設值
        pvp_game_specific_config = { # 之後可以從 pvp_config.yaml 讀取
            'player1_paddle_width': 100, 'player1_lives': 3,
            'player2_paddle_width': 100, 'player2_lives': 3,
            'bg_music': "bg_music_pvp.mp3" # PvP 專用背景音樂 (假設存在)
        }
        common_game_config['bg_music'] = pvp_game_specific_config.get('bg_music', common_game_config['bg_music'])

        player1_env_config = {
            'initial_x': 0.5,
            'initial_paddle_width': pvp_game_specific_config.get('player1_paddle_width', 100),
            'initial_lives': pvp_game_specific_config.get('player1_lives', 3),
            'skill_code': p1_skill_code_from_menu,
            'is_ai': False
        }
        opponent_env_config = { # 對手即 Player 2
            'initial_x': 0.5,
            'initial_paddle_width': pvp_game_specific_config.get('player2_paddle_width', 100),
            'initial_lives': pvp_game_specific_config.get('player2_lives', 3),
            'skill_code': p2_skill_code_from_menu,
            'is_ai': False
        }
        if DEBUG_MAIN: print("[game_session] PVP: Configured for Player vs Player.")
    else:
        if DEBUG_MAIN: print(f"[game_session] Error: Unknown game mode value: {current_game_mode_value}")
        return "select_game_mode"


    env = PongDuelEnv(
        game_mode=current_game_mode_value,
        player1_config=player1_env_config,
        opponent_config=opponent_env_config,
        common_config=common_game_config,
        render_size=render_size_for_env, # 傳遞渲染尺寸
        paddle_height_px=paddle_height_for_env,
        ball_radius_px=ball_radius_for_env
    )
    # env.set_params_from_config(common_game_config) # 已移至 __init__

    # env.reset() 已在 __init__ 最後調用，obs 已獲取
    obs, _ = env.reset() # 確保獲取最新的 obs

    # 遊戲開始前的渲染和倒數
    env.render() # 第一次渲染，初始化 env.renderer 和 env.window
    if not env.renderer or not env.renderer.window:
        if DEBUG_MAIN: print("[game_session] Fatal Error: env.renderer.window could not be initialized by renderer.")
        env.close()
        return "quit"

    # 播放背景音樂
    if hasattr(env, 'sound_manager') and env.sound_manager and hasattr(env, 'bg_music') and env.bg_music:
        bg_music_path = resource_path(f"assets/{env.bg_music}") # assets 目錄是假設的
        if os.path.exists(bg_music_path):
            try:
                pygame.mixer.music.load(bg_music_path)
                pygame.mixer.music.set_volume(GameSettings.BACKGROUND_MUSIC_VOLUME) # 從全域設定讀取音量
                env.sound_manager.play_bg_music()
                if DEBUG_MAIN: print(f"[game_session] Playing background music: {bg_music_path}")
            except pygame.error as e:
                if DEBUG_MAIN: print(f"[game_session] Error loading/playing background music {bg_music_path}: {e}")
        else:
            if DEBUG_MAIN: print(f"[game_session] Warning: Background music file not found: {bg_music_path}")

    show_countdown(env)

    game_running = True
    game_session_result_state = "select_game_mode" # 預設遊戲結束後返回模式選擇

    last_round_winner_is_p1 = None # 用於判斷下一回合誰發球, True: P1贏(對手發球), False: 對手贏(P1發球)

    while game_running:
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                game_running = False
                game_session_result_state = "quit" # 設定為退出遊戲

        if not game_running: break

        keys = pygame.key.get_pressed()

        # --- 玩家一行動 (P1) ---
        p1_ingame_action = 1 # 預設不動 (0:左, 1:不動, 2:右)
        if current_input_mode == "keyboard":
            if keys[P1_GAME_KEYS['LEFT_KB']]: p1_ingame_action = 0
            elif keys[P1_GAME_KEYS['RIGHT_KB']]: p1_ingame_action = 2
        elif current_input_mode == "mouse":
            mouse_x_abs, _ = pygame.mouse.get_pos()
            if env.render_size > 0: #避免 ZeroDivisionError
                # 滑鼠X座標是相對於整個視窗的，需要轉換到遊戲區域內
                # 假設遊戲區域在視窗內是水平居中的，或者從 (0, offset_y) 開始
                # 這裡簡化：假設滑鼠X直接對應遊戲區域的X
                # 注意：Renderer 的 offset_y 只影響垂直繪圖，不影響滑鼠座標轉換
                game_area_x_start = 0 # 假設遊戲區域從視窗左邊緣開始
                mouse_x_in_game_area = mouse_x_abs - game_area_x_start
                mouse_x_relative = mouse_x_in_game_area / env.render_size

                threshold = 0.02 # 避免抖動的閾值
                if mouse_x_relative < env.player1.x - threshold: p1_ingame_action = 0
                elif mouse_x_relative > env.player1.x + threshold: p1_ingame_action = 2
        
        # --- 玩家一技能啟動 (階段二處理) ---
        # if keys[P1_GAME_KEYS['SKILL_KB']]:
        #     if env.player1.skill_instance: env.player1.skill_instance.activate()


        # --- 上方球拍行動 (AI 或 P2) ---
        opponent_ingame_action = 1 # 預設不動
        if current_game_mode_value == GameSettings.GameMode.PLAYER_VS_AI:
            if ai_agent:
                # AI 的觀測值需要從 AI 的視角（上方球拍）
                # 目前 _get_obs 返回的是通用視角，如果 AI 模型訓練時有特定視角，這裡需要轉換
                ai_obs_for_agent = obs.copy()
                # 示例：如果AI在上方，它看到的 player1 是對手，自己是 player
                # 這取決於 AI 模型的訓練數據。此處暫不轉換，假設 AI 能處理。
                opponent_ingame_action = ai_agent.select_action(ai_obs_for_agent)
            else: # 沒有 AI agent
                opponent_ingame_action = 1 # 不動
        else: # PVP 模式，玩家二行動
            if keys[P2_GAME_KEYS['LEFT']]: opponent_ingame_action = 0
            elif keys[P2_GAME_KEYS['RIGHT']]: opponent_ingame_action = 2
            # --- 玩家二技能啟動 (階段二處理) ---
            # if keys[P2_GAME_KEYS['SKILL']]:
            #    if env.opponent.skill_instance: env.opponent.skill_instance.activate()


        obs, reward, round_done, game_over, _ = env.step(p1_ingame_action, opponent_ingame_action)
        env.render()

        if hasattr(env, 'renderer') and env.renderer and hasattr(env.renderer, 'clock'):
            env.renderer.clock.tick(60)
        else:
            time.sleep(0.016)

        if round_done:
            if DEBUG_MAIN: print(f"[game_session] Round Done. P1 Lives: {env.player1.lives}, Opponent Lives: {env.opponent.lives}")
            
            # 判斷是誰贏了這一回合，以便決定下一球由誰發
            # 假設 env.step 中已經正確更新了 lives
            # 如果 env.player1.lives 沒變且 env.opponent.lives 減少了 -> P1 贏了此回合
            # 如果 env.opponent.lives 沒變且 env.player1.lives 減少了 -> Opponent 贏了此回合
            # 這個邏輯可以在 env.step 返回的 info 中包含，或者在這裡比較前後 lives
            # 暫時簡化：在 freeze 之後，通過比較誰的生命值低來決定誰發球
            # (更好的方式是 step 返回誰得分了)

            # 等待凍結時間結束
            freeze_start_time = pygame.time.get_ticks()
            while pygame.time.get_ticks() - freeze_start_time < env.freeze_duration:
                for event_freeze in pygame.event.get(): # 允許在凍結時退出
                    if event_freeze.type == pygame.QUIT:
                        game_running = False; game_session_result_state = "quit"; break
                if not game_running: break
                # env.render() # 持續渲染凍結效果 (PongDuelEnv 的 freeze_timer 機制會處理)
                pygame.time.delay(16) # 避免CPU滿載
            if not game_running: break

            if game_over: # 遊戲徹底結束
                if DEBUG_MAIN: print("[game_session] Game Over detected after round.")
                p1_wins_msg = "PLAYER 1 WINS!" if current_game_mode_value == GameSettings.GameMode.PLAYER_VS_PLAYER else "YOU WIN!"
                p1_loses_msg = "PLAYER 2 WINS!" if current_game_mode_value == GameSettings.GameMode.PLAYER_VS_PLAYER else "YOU LOSE!"
                p1_color = Style.PLAYER_COLOR
                opponent_color = Style.AI_COLOR # PVP時應為P2顏色

                if env.player1.lives <= 0: # P1 輸
                    if env.sound_manager: env.sound_manager.play_lose_sound()
                    show_result_banner(env.renderer.window, p1_loses_msg, opponent_color)
                elif env.opponent.lives <= 0: # Opponent 輸 (P1 贏)
                    if env.sound_manager: env.sound_manager.play_win_sound()
                    show_result_banner(env.renderer.window, p1_wins_msg, p1_color)
                
                game_running = False # 結束遊戲會話
                game_session_result_state = "select_game_mode" # 返回模式選擇
            else: # 回合結束，但遊戲未結束
                if DEBUG_MAIN: print("[game_session] Round ended, game continues. Resetting ball.")
                # 決定下一球由誰發
                # 假設：失分方發球。
                # 如果 P1 的 lives 剛才被扣了，那麼 scored_by_player1 應為 False (即 P1 失分，對手得分)
                # 如果 Opponent 的 lives 剛才被扣了，那麼 scored_by_player1 應為 True (即 Opponent 失分，P1 得分)
                # 這裡需要一種方式從 env.step 中知道誰剛才失分，或者比較前後生命值
                # 暫時簡化：隨機或輪流發球，或基於上次誰贏
                # 假設 env.reset_ball_after_score 會處理發球權
                if last_round_winner_is_p1 is None: # 第一次回合結束
                    env.reset_ball_after_score(scored_by_player1=random.choice([True, False]))
                else:
                    env.reset_ball_after_score(scored_by_player1=last_round_winner_is_p1)

                # 更新 last_round_winner_is_p1 for next round
                # 這部分邏輯還是不夠完美，理想情況是 env.step 返回得分方
                # 臨時：如果 P1 生命多，則 P1 贏了這局，下一局對手發
                if env.player1.lives > env.opponent.lives: # 這不對，應該是比較變化
                     # last_round_winner_is_p1 = True # P1贏了這局，對手發
                     pass
                elif env.opponent.lives > env.player1.lives:
                     # last_round_winner_is_p1 = False # 對手贏了這局，P1發
                     pass


                obs, _ = env.reset() # 重置球等狀態，但不重置生命值
                show_countdown(env) # 回合間倒數
        # --- end of round_done ---
    # --- end of game_running loop ---

    if DEBUG_MAIN: print(f"[game_session] Exiting. Result state: {game_session_result_state}")
    if hasattr(env, 'sound_manager'): env.sound_manager.stop_bg_music() # 停止背景音樂
    env.close()
    return game_session_result_state


# --- 主應用程式迴圈 (部分修改以適應新的 game_session 參數) ---
def main_loop():
    current_input_mode = "keyboard" # 預設 P1 輸入方式
    p1_selected_skill_code = None
    p2_selected_skill_code = None # PVP模式下玩家二的技能
    current_game_mode = None
    
    sound_manager = SoundManager() # 全域音效管理器

    # 主螢幕在不同階段大小可能變化
    # 初始設定為選單大小
    main_screen_width, main_screen_height = 500, 500
    main_screen = pygame.display.set_mode((main_screen_width, main_screen_height))
    pygame.display.set_caption("Pong Soul")

    next_game_flow_step = "select_game_mode"

    running = True
    while running:
        if DEBUG_MAIN: print(f"[main_loop] Current step: {next_game_flow_step}")

        if next_game_flow_step == "select_game_mode":
            if main_screen.get_size() != (500,500): #確保選單時螢幕是500x500
                 main_screen = pygame.display.set_mode((500,500))
                 pygame.display.set_caption("Pong Soul - Select Mode")

            current_game_mode = select_game_mode() # 返回 "PVA" or "PVP"
            if current_game_mode is None: # 用戶可能在選單中按ESC或關閉
                next_game_flow_step = "quit"
                continue
            p1_selected_skill_code = None # 重置技能選擇
            p2_selected_skill_code = None
            next_game_flow_step = "select_input"

        elif next_game_flow_step == "select_input":
            if main_screen.get_size() != (500,500):
                 main_screen = pygame.display.set_mode((500,500))
                 pygame.display.set_caption("Pong Soul - Select Controller")

            current_input_mode = select_input_method() # 返回 "keyboard" or "mouse"
            if current_input_mode is None:
                next_game_flow_step = "select_game_mode"
                continue
            
            if current_game_mode == GameSettings.GameMode.PLAYER_VS_AI:
                next_game_flow_step = "select_skill_pva"
            elif current_game_mode == GameSettings.GameMode.PLAYER_VS_PLAYER:
                # 為PVP技能選擇設定螢幕
                pvp_menu_width, pvp_menu_height = 1000, 600 # PvP 選單的螢幕尺寸
                if main_screen.get_size() != (pvp_menu_width, pvp_menu_height):
                    main_screen = pygame.display.set_mode((pvp_menu_width, pvp_menu_height))
                pygame.display.set_caption("Pong Soul - PVP Skill Selection")
                
                p1_selected_skill_code, p2_selected_skill_code = run_pvp_selection_phase(main_screen, sound_manager)
                if p1_selected_skill_code is None or p2_selected_skill_code is None: # 有玩家取消
                    next_game_flow_step = "select_input" # 返回輸入選擇 (或模式選擇)
                    continue
                # 雙方選完技能，直接進入遊戲會話
                next_game_flow_step = game_session(current_input_mode, p1_selected_skill_code, p2_selected_skill_code, current_game_mode)
            else:
                if DEBUG_MAIN: print(f"[main_loop] Unknown game mode: {current_game_mode}, returning to mode select.")
                next_game_flow_step = "select_game_mode"

        elif next_game_flow_step == "select_skill_pva":
            if main_screen.get_size() != (500,500):
                 main_screen = pygame.display.set_mode((500,500))
            pygame.display.set_caption("Pong Soul - Select Skill (PVA)")
            
            pva_render_area = main_screen.get_rect()
            p1_selected_skill_code = select_skill(
                main_screen_surface=main_screen, render_area=pva_render_area,
                key_map=DEFAULT_MENU_KEYS, sound_manager=sound_manager, player_identifier="Player"
            )
            if p1_selected_skill_code is None:
                next_game_flow_step = "select_input"
                continue
            next_game_flow_step = game_session(current_input_mode, p1_selected_skill_code, None, current_game_mode)
        
        elif next_game_flow_step == "quit":
            running = False # 跳出主迴圈
        
        else: # game_session 返回的結果 (通常是 "select_game_mode" 或 "quit")
            if next_game_flow_step not in ["select_game_mode", "select_input", "select_skill_pva", "quit"]:
                if DEBUG_MAIN: print(f"[main_loop] Warning: Unhandled next_step_state '{next_game_flow_step}', defaulting to 'select_game_mode'.")
                next_game_flow_step = "select_game_mode" # 避免無限迴圈或錯誤狀態
            # 如果是 "select_game_mode" 等，迴圈會自然處理

    if DEBUG_MAIN: print("[main_loop] Exiting application.")
    pygame.quit()
    sys.exit()

if __name__ == '__main__':
    main_loop()