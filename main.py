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
    if not env.renderer or not env.renderer.window:
        if DEBUG_MAIN: print("[show_countdown] Error: Renderer or window not initialized.")
        return

    screen = env.renderer.window # ⭐️ 使用 Renderer 的主視窗 surface
    font = Style.get_font(60) # 或者一個更大的字體，例如 Style.get_font(80)
    
    # 倒數秒數從 GameSettings 或 env 的 common_config 獲取
    countdown_seconds_to_show = GameSettings.COUNTDOWN_SECONDS
    if hasattr(env, 'common_config') and 'countdown_seconds' in env.common_config: # PongDuelEnv 應保存 common_config
        countdown_seconds_to_show = env.common_config['countdown_seconds']
    elif hasattr(env, 'countdown_seconds'): # 如果 env 直接有此屬性
        countdown_seconds_to_show = env.countdown_seconds


    for i in range(countdown_seconds_to_show, 0, -1):
        if hasattr(env, 'sound_manager') and env.sound_manager:
            env.sound_manager.play_countdown()

        screen.fill(Style.BACKGROUND_COLOR) # 用背景色清屏
        
        countdown_surface = font.render(str(i), True, Style.TEXT_COLOR)
        
        # ⭐️ 將倒數文字置於整個 screen 的中央
        countdown_rect = countdown_surface.get_rect(
            center=(screen.get_width() // 2, screen.get_height() // 2)
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
    # ... (配置加載和 Env 初始化部分保持不變) ...
    levels = LevelManager(models_folder=resource_path("models"))
    common_game_config = {
        'mass': 1.0, 'e_ball_paddle': 1.0, 'mu_ball_paddle': 0.4, 'enable_spin': True, 'magnus_factor': 0.01,
        'speed_increment': 0.002, 'speed_scale_every': 3, 'initial_ball_speed': 0.025, 
        'initial_angle_deg_range': [-45, 45], 
        'freeze_duration_ms': GameSettings.FREEZE_DURATION_MS, # 例如 500ms 或 700ms
        'countdown_seconds': GameSettings.COUNTDOWN_SECONDS, # 遊戲開始前的倒數秒數
        'bg_music': "bg_music_level1.mp3" 
    }
    render_size_for_env = 400; paddle_height_for_env = 10; ball_radius_for_env = 10
    # ... (根據 game_mode 填充 player1_env_config, opponent_env_config, common_game_config['bg_music'] 等) ...
    # ... (例如，從 level_specific_config 或 pvp_game_specific_config 更新 common_game_config['freeze_duration_ms']) ...
    # (為確保您擁有完整的上下文，我將複製這部分配置邏輯)
    player1_env_config = {}; opponent_env_config = {}; ai_agent = None
    if current_game_mode_value == GameSettings.GameMode.PLAYER_VS_AI:
        selected_level_index = show_level_selection() 
        if selected_level_index is None: return "select_game_mode" 
        levels.current_level = selected_level_index
        level_specific_config = levels.get_current_config() 
        if not level_specific_config:
            level_specific_config = { 
                'player_life': 3, 'ai_life': 3, 'player_paddle_width': 100, 'ai_paddle_width': 60,
                'initial_speed': 0.02, 'bg_music': "bg_music_level1.mp3",
                'freeze_duration_ms': common_game_config['freeze_duration_ms'] # 使用通用配置或關卡特定
            }
        common_game_config['initial_ball_speed'] = level_specific_config.get('initial_speed', common_game_config['initial_ball_speed'])
        common_game_config['bg_music'] = level_specific_config.get('bg_music', common_game_config['bg_music'])
        common_game_config['freeze_duration_ms'] = level_specific_config.get('freeze_duration_ms', common_game_config['freeze_duration_ms'])
        player1_env_config = {
            'initial_x': 0.5, 'initial_paddle_width': level_specific_config.get('player_paddle_width', 100),
            'initial_lives': level_specific_config.get('player_life', 3), 'skill_code': p1_skill_code_from_menu, 'is_ai': False
        }
        opponent_env_config = {
            'initial_x': 0.5, 'initial_paddle_width': level_specific_config.get('ai_paddle_width', 60),
            'initial_lives': level_specific_config.get('ai_life', 3), 'skill_code': None, 'is_ai': True
        }
        relative_model_path = levels.get_current_model_path()
        if relative_model_path:
            absolute_model_path = resource_path(relative_model_path)
            if os.path.exists(absolute_model_path): ai_agent = AIAgent(absolute_model_path)
    elif current_game_mode_value == GameSettings.GameMode.PLAYER_VS_PLAYER:
        pvp_game_specific_config = { 
            'player1_paddle_width': 100, 'player1_lives': 3, 'player2_paddle_width': 100, 'player2_lives': 3,
            'bg_music': "bg_music_pvp.mp3", 'freeze_duration_ms': common_game_config.get('freeze_duration_ms', 500) 
        }
        common_game_config['bg_music'] = pvp_game_specific_config.get('bg_music', common_game_config['bg_music'])
        common_game_config['freeze_duration_ms'] = pvp_game_specific_config.get('freeze_duration_ms', common_game_config['freeze_duration_ms'])
        player1_env_config = {
            'initial_x': 0.5, 'initial_paddle_width': pvp_game_specific_config.get('player1_paddle_width', 100),
            'initial_lives': pvp_game_specific_config.get('player1_lives', 3), 'skill_code': p1_skill_code_from_menu, 'is_ai': False
        }
        opponent_env_config = { 
            'initial_x': 0.5, 'initial_paddle_width': pvp_game_specific_config.get('player2_paddle_width', 100),
            'initial_lives': pvp_game_specific_config.get('player2_lives', 3), 'skill_code': p2_skill_code_from_menu, 'is_ai': False
        }
    else: return "select_game_mode"

    env = PongDuelEnv(
        game_mode=current_game_mode_value, player1_config=player1_env_config,
        opponent_config=opponent_env_config, common_config=common_game_config,
        render_size=render_size_for_env, paddle_height_px=paddle_height_for_env,
        ball_radius_px=ball_radius_for_env
    )
    obs, _ = env.reset() 
    env.render() 
    if not env.renderer or not env.renderer.window: return "quit"
    
    # 背景音樂播放
    if hasattr(env, 'sound_manager') and env.sound_manager and hasattr(env, 'bg_music') and env.bg_music:
        bg_music_path = resource_path(f"assets/{env.bg_music}") 
        if os.path.exists(bg_music_path):
            try: 
                pygame.mixer.music.load(bg_music_path)
                pygame.mixer.music.set_volume(GameSettings.BACKGROUND_MUSIC_VOLUME) 
                env.sound_manager.play_bg_music()
            except pygame.error as e:
                if DEBUG_MAIN: print(f"[DEBUG][game_session] Error loading/playing music {bg_music_path}: {e}")
        else:
            if DEBUG_MAIN: print(f"[DEBUG][game_session] Warning: Music file not found: {bg_music_path}")
    
    # --- 遊戲開始前的倒數 (這個倒數保留) ---
    initial_countdown_duration = common_game_config.get('countdown_seconds', GameSettings.COUNTDOWN_SECONDS)
    if initial_countdown_duration > 0 : 
        if DEBUG_MAIN: print(f"[DEBUG][game_session] Starting initial countdown for {initial_countdown_duration} seconds.")
        show_countdown(env) 
    # --- 遊戲主迴圈 ---
    game_running = True
    game_session_result_state = "select_game_mode" 

    while game_running:
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                game_running = False
                game_session_result_state = "quit" 
            elif event.type == pygame.KEYDOWN: 
                if event.key == pygame.K_ESCAPE:
                    if DEBUG_MAIN: print("[DEBUG][game_session] ESC pressed during gameplay. Ending session.")
                    game_running = False
                    game_session_result_state = "select_game_mode" 
        if not game_running: break

        keys = pygame.key.get_pressed()
        p1_ingame_action = 1 # 預設不動
        # ... (P1 和 Opponent/P2 的行動和技能啟用邏輯與上一版本相同) ...
        if current_input_mode == "keyboard":
            if keys[P1_GAME_KEYS['LEFT_KB']]: p1_ingame_action = 0
            elif keys[P1_GAME_KEYS['RIGHT_KB']]: p1_ingame_action = 2
        elif current_input_mode == "mouse":
            mouse_x_abs, _ = pygame.mouse.get_pos(); game_area_x_start = 0 
            mouse_x_in_game_area = mouse_x_abs - game_area_x_start
            mouse_x_relative = mouse_x_in_game_area / env.render_size if env.render_size > 0 else 0
            threshold = 0.02 
            if mouse_x_relative < env.player1.x - threshold: p1_ingame_action = 0
            elif mouse_x_relative > env.player1.x + threshold: p1_ingame_action = 2
        if keys[P1_GAME_KEYS['SKILL_KB']]:
            if DEBUG_MAIN: print(f"[DEBUG][game_session] P1 skill key '{pygame.key.name(P1_GAME_KEYS['SKILL_KB'])}' pressed.")
            env.activate_skill(env.player1)
        opponent_ingame_action = 1
        if current_game_mode_value == GameSettings.GameMode.PLAYER_VS_AI:
            if ai_agent: opponent_ingame_action = ai_agent.select_action(obs.copy())
        else: 
            if keys[P2_GAME_KEYS['LEFT']]: opponent_ingame_action = 0
            elif keys[P2_GAME_KEYS['RIGHT']]: opponent_ingame_action = 2
            if keys[P2_GAME_KEYS['SKILL']]:
                if DEBUG_MAIN: print(f"[DEBUG][game_session] P2 skill key '{pygame.key.name(P2_GAME_KEYS['SKILL'])}' pressed.")
                env.activate_skill(env.opponent)
        
        obs, reward, round_done, game_over, info = env.step(p1_ingame_action, opponent_ingame_action)
        env.render() # ⭐️ 每幀主要渲染

        if hasattr(env, 'renderer') and env.renderer and hasattr(env.renderer, 'clock'):
            env.renderer.clock.tick(60)
        else: 
            time.sleep(0.016) # 保持大約60FPS

        if round_done: # 處理回合結束
            if DEBUG_MAIN: print(f"[DEBUG][game_session] Round Done. Info: {info}. P1 Lives: {env.player1.lives}, Opponent Lives: {env.opponent.lives}")
            
            # ⭐️ 步驟 2.1: 確保在凍結期間持續渲染以顯示閃爍效果
            freeze_start_time = pygame.time.get_ticks()
            # 使用 env 內部設定的 freeze_duration，這個值可能已由 common_config 或 level_config 設定
            current_freeze_duration = env.freeze_duration 
            
            if DEBUG_MAIN: print(f"[DEBUG][game_session] Starting freeze effect (flashing) for {current_freeze_duration}ms.")

            while pygame.time.get_ticks() - freeze_start_time < current_freeze_duration:
                # 在凍結期間仍然需要處理事件，以便能按 ESC 退出或關閉視窗
                for event_freeze in pygame.event.get():
                    if event_freeze.type == pygame.QUIT:
                        game_running = False
                        game_session_result_state = "quit"
                        break
                    elif event_freeze.type == pygame.KEYDOWN: 
                        if event_freeze.key == pygame.K_ESCAPE:
                            if DEBUG_MAIN: print("[DEBUG][game_session] ESC pressed during freeze. Ending session.")
                            game_running = False
                            game_session_result_state = "select_game_mode"
                            break 
                if not game_running: break # 如果在內部事件處理中已停止，則跳出凍結迴圈
                
                env.render() # ⭐️⭐️⭐️ 關鍵：在凍結期間持續調用 render() ⭐️⭐️⭐️
                
                pygame.time.delay(16) # 短暫延遲，大約60FPS的間隔，避免CPU過度使用
                                      # 並允許閃爍效果有足夠的幀數來呈現

            if not game_running: break # 如果因QUIT或ESC退出，則跳出主遊戲迴圈

            if DEBUG_MAIN: print(f"[DEBUG][game_session] Freeze effect finished. Game over: {game_over}")

            if game_over: # 遊戲徹底結束
                # ... (遊戲結束橫幅顯示邏輯，與之前相同) ...
                p1_wins_msg = "PLAYER 1 WINS!" if current_game_mode_value == GameSettings.GameMode.PLAYER_VS_PLAYER else "YOU WIN!"
                p1_loses_msg = "PLAYER 2 WINS!" if current_game_mode_value == GameSettings.GameMode.PLAYER_VS_PLAYER else "YOU LOSE!"
                p1_color = Style.PLAYER_COLOR; opponent_color = Style.AI_COLOR # PvP 時可為 P2 設定不同顏色
                if env.player1.lives <= 0:
                    if env.sound_manager: env.sound_manager.play_lose_sound()
                    show_result_banner(env.renderer.window, p1_loses_msg, opponent_color)
                elif env.opponent.lives <= 0:
                    if env.sound_manager: env.sound_manager.play_win_sound()
                    show_result_banner(env.renderer.window, p1_wins_msg, p1_color)
                game_running = False # 結束遊戲會話
                game_session_result_state = "select_game_mode" # 返回模式選擇
            else: # 回合結束，但遊戲未結束
                scorer = info.get('scorer') # 從 env.step 返回的 info 中獲取得分者
                if DEBUG_MAIN: print(f"[DEBUG][game_session] Round ended, scorer: {scorer}. Resetting ball for next round (NO COUNTDOWN).")
                
                # 根據得分者決定下一球由誰的區域發出
                # env.reset_ball_after_score(scored_by_player1=True) 表示 P1 得分，球從對手區發
                if scorer == 'player1': 
                    env.reset_ball_after_score(scored_by_player1=True) 
                elif scorer == 'opponent': 
                    env.reset_ball_after_score(scored_by_player1=False)
                else: 
                    if DEBUG_MAIN: print(f"[DEBUG][game_session] Scorer info ('{scorer}') not definitive for serve, randomizing.")
                    env.reset_ball_after_score(scored_by_player1=random.choice([True, False]))
                
                obs = env._get_obs() # 獲取新回合的觀測值
                
                # ⭐️⭐️⭐️ 步驟 2.2: 移除回合間的倒數 ⭐️⭐️⭐️
                # show_countdown(env) # 已移除或註解掉!
                
                if DEBUG_MAIN: print("[DEBUG][game_session] Ball to be served immediately after freeze.")
    
    # 遊戲會話結束後的清理
    if hasattr(env, 'sound_manager'): env.sound_manager.stop_bg_music()
    env.close() # 關閉環境資源 (Renderer 等)
    return game_session_result_state

# ... (main_loop 和 if __name__ == '__main__': 部分保持不變) ...

# ... (main_loop 和 if __name__ == '__main__': 部分保持不變) ...
# main.py (修正版 - 階段 1.3 - 全螢幕第一階段)

import pygame
import sys
import time
import os
# import torch # 暫時不需要直接在此處使用
# import numpy # 暫時不需要直接在此處使用

# ‼️ pygame.init() 和 pygame.font.init() 將移至 main_loop() 開頭
import random
# 專案路徑設定
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from envs.pong_duel_env import PongDuelEnv
from game.ai_agent import AIAgent
from game.level import LevelManager
from game.theme import Style
from game.menu import (
    show_level_selection,
    select_input_method,
    select_skill,
    select_game_mode
)
from game.settings import GameSettings
from game.sound import SoundManager
from utils import resource_path

DEBUG_MAIN = True
DEBUG_MAIN_FULLSCREEN = True # ⭐️ 新增全螢幕排錯開關

# --- 倒數與結果顯示函數 ---
def show_countdown(env):
    # 這個函數依賴 env.renderer.window，需要確保 env.renderer.window 是正確的主螢幕表面
    if not env.renderer or not env.renderer.window:
        if DEBUG_MAIN: print("[show_countdown] Error: Renderer or window not initialized.")
        return

    screen = env.renderer.window
    font = Style.get_font(60) # 假設 Style.get_font 此時能正常工作 (後續會處理縮放)

    countdown_seconds_to_show = GameSettings.COUNTDOWN_SECONDS
    if hasattr(env, 'common_config') and 'countdown_seconds' in env.common_config:
        countdown_seconds_to_show = env.common_config['countdown_seconds']
    elif hasattr(env, 'countdown_seconds'):
        countdown_seconds_to_show = env.countdown_seconds

    for i in range(countdown_seconds_to_show, 0, -1):
        if hasattr(env, 'sound_manager') and env.sound_manager:
            env.sound_manager.play_countdown()

        screen.fill(Style.BACKGROUND_COLOR) # 用背景色清屏
        countdown_surface = font.render(str(i), True, Style.TEXT_COLOR)
        countdown_rect = countdown_surface.get_rect(
            center=(screen.get_width() // 2, screen.get_height() // 2) # 這裡的 get_width/height 是指 env.renderer.window 的
        )
        screen.blit(countdown_surface, countdown_rect)
        pygame.display.flip() # ‼️ 注意: 此處的 flip 是針對 env.renderer.window
        pygame.time.wait(1000)

def show_result_banner(screen, text, color):
    # 這個函數接收 screen 參數，需要確保是正確的主螢幕表面
    if not screen:
        if DEBUG_MAIN: print(f"[show_result_banner] Error: Screen not available for text: {text}")
        return
    font = Style.get_font(40) # 假設 Style.get_font 此時能正常工作
    screen.fill(Style.BACKGROUND_COLOR)
    banner = font.render(text, True, color)
    rect = banner.get_rect(center=(screen.get_width() // 2, screen.get_height() // 2)) # 這裡的 get_width/height 是指傳入的 screen
    screen.blit(banner, rect)
    pygame.display.flip() # ‼️ 注意: 此處的 flip 是針對傳入的 screen
    pygame.time.delay(2000)

# --- 按鍵映射定義 ---
P1_MENU_KEYS = {
    'UP': pygame.K_w, 'DOWN': pygame.K_s, 'CONFIRM': pygame.K_e, 'CANCEL': pygame.K_q
}
DEFAULT_MENU_KEYS = {
    'UP': pygame.K_UP, 'DOWN': pygame.K_DOWN, 'CONFIRM': pygame.K_RETURN, 'CANCEL': pygame.K_ESCAPE
}
P2_GAME_KEYS = {
    'LEFT': pygame.K_j, 'RIGHT': pygame.K_l, 'SKILL': pygame.K_u
}
P1_GAME_KEYS = {
    'LEFT_KB': pygame.K_LEFT, 'RIGHT_KB': pygame.K_RIGHT, 'SKILL_KB': pygame.K_x,
}

# --- PVP 選單階段處理 ---
def run_pvp_selection_phase(main_screen_surface_param, sound_manager_instance):
    # 此函數需要接收 main_screen_surface_param 並在其上繪圖
    # 內部調用的 select_skill 也需要使用 main_screen_surface_param
    if DEBUG_MAIN_FULLSCREEN:
        print(f"[DEBUG_MAIN_FULLSCREEN][run_pvp_selection_phase] Called. Drawing on surface: {type(main_screen_surface_param)}")

    # ⭐️ 假設 PvP 技能選擇的邏輯尺寸和佈局
    # ⭐️ 在後續縮放階段，這些尺寸會是"邏輯"尺寸，然後進行縮放繪製
    # ⭐️ 目前，我們直接使用像素值，它們將繪製在 main_screen_surface_param 的左上角區域
    # ⭐️ 或者，如果 main_screen_surface_param 夠大，它們會按原始像素繪製
    screen_width_for_pvp_layout = 1000 # 假設的佈局寬度
    screen_height_for_pvp_layout = 600 # 假設的佈局高度

    # 這些 Rect 是相對於繪圖區域的邏輯劃分
    # 在縮放階段，它們的實際繪製位置和大小會基於 main_screen_surface_param 和縮放因子計算
    # 目前，它們是相對於 (0,0) 的。
    left_rect = pygame.Rect(0, 0, screen_width_for_pvp_layout // 2, screen_height_for_pvp_layout)
    right_rect = pygame.Rect(screen_width_for_pvp_layout // 2, 0, screen_width_for_pvp_layout // 2, screen_height_for_pvp_layout)
    divider_color = (100, 100, 100)
    player1_selected_skill = None
    player2_selected_skill = None

    # 填充整個 main_screen_surface_param 的背景 (或者只填充將要繪製的區域)
    # 為簡單起見，先填充整個主螢幕，後續縮放時再精細控制繪製區域。
    main_screen_surface_param.fill(Style.BACKGROUND_COLOR)
    
    # 繪製分割線 (基於假設的佈局尺寸)
    # 這些座標在縮放階段也需要調整
    divider_x = screen_width_for_pvp_layout // 2
    pygame.draw.line(main_screen_surface_param, divider_color, (divider_x, 0), (divider_x, screen_height_for_pvp_layout), 2)
    
    # 刷新一次，顯示背景和分割線
    pygame.display.flip() # ‼️ PVP 選單中 flip 應由 main_loop 控制，此處 flip 僅為分步顯示

    if DEBUG_MAIN: print("[run_pvp_selection_phase] Player 1 selecting skill...")
    # ⭐️ select_skill 需要接收 main_screen_surface_param 和一個定義其繪製區域的 render_area
    # ⭐️ 目前，left_rect 是相對於 (0,0) 的邏輯區域
    player1_selected_skill = select_skill(
        main_screen_surface=main_screen_surface_param, # 傳遞主螢幕
        render_area=left_rect, # 告訴 select_skill 在主螢幕的哪個區域繪製
        key_map=P1_MENU_KEYS,
        sound_manager=sound_manager_instance,
        player_identifier="Player 1"
    )
    if player1_selected_skill is None:
        if DEBUG_MAIN: print("[run_pvp_selection_phase] Player 1 cancelled.")
        return None, None # P1 取消，則整個階段取消

    # P1 選擇完後，在左側區域顯示P1的選擇 (暫時性顯示)
    # 這部分UI可以做得更精緻
    pygame.draw.rect(main_screen_surface_param, Style.BACKGROUND_COLOR, left_rect) # 清理左側
    font_info = Style.get_font(Style.ITEM_FONT_SIZE)
    p1_info_text_render = font_info.render(f"P1 Skill: {player1_selected_skill}", True, Style.TEXT_COLOR)
    # 繪製位置需要基於 left_rect
    main_screen_surface_param.blit(p1_info_text_render, (left_rect.left + 20, left_rect.centery))
    # 重新繪製分割線，因為左側可能被p1_info_text_render覆蓋了一部分背景
    pygame.draw.line(main_screen_surface_param, divider_color, (divider_x, 0), (divider_x, screen_height_for_pvp_layout), 2)
    pygame.display.flip() # ‼️ 僅為分步顯示

    if DEBUG_MAIN: print(f"[run_pvp_selection_phase] Player 1 selected: {player1_selected_skill}. Player 2 selecting...")
    player2_selected_skill = select_skill(
        main_screen_surface=main_screen_surface_param, # 傳遞主螢幕
        render_area=right_rect, # 告訴 select_skill 在主螢幕的哪個區域繪製
        key_map=DEFAULT_MENU_KEYS,
        sound_manager=sound_manager_instance,
        player_identifier="Player 2"
    )
    if player2_selected_skill is None:
        if DEBUG_MAIN: print("[run_pvp_selection_phase] Player 2 cancelled.")
        # 即使P2取消，也可能需要返回P1的選擇，由主循環決定如何處理
        return player1_selected_skill, None

    # P2 選擇完後，在右側區域顯示P2的選擇
    pygame.draw.rect(main_screen_surface_param, Style.BACKGROUND_COLOR, right_rect) # 清理右側
    p2_info_text_render = font_info.render(f"P2 Skill: {player2_selected_skill}", True, Style.TEXT_COLOR)
    main_screen_surface_param.blit(p2_info_text_render, (right_rect.left + 20, right_rect.centery))
    # 分割線通常不需要重繪，除非P2的選擇顯示也影響了它
    pygame.display.flip() # ‼️ 僅為分步顯示

    if DEBUG_MAIN: print(f"[run_pvp_selection_phase] Player 2 selected: {player2_selected_skill}.")
    
    # 最終確認畫面
    main_screen_surface_param.fill(Style.BACKGROUND_COLOR) # 清理整個用於PVP選單的區域
    font_large = Style.get_font(Style.TITLE_FONT_SIZE) # 使用大字體
    ready_text_str = "Players Ready! Starting..."
    if not player1_selected_skill or not player2_selected_skill: # 確保都選了
         ready_text_str = "Skill selection incomplete!"
    ready_text_render = font_large.render(ready_text_str, True, Style.TEXT_COLOR)
    # 讓 "Ready" 文字顯示在假設的佈局中央
    ready_rect = ready_text_render.get_rect(center=(screen_width_for_pvp_layout // 2, screen_height_for_pvp_layout // 2))
    main_screen_surface_param.blit(ready_text_render, ready_rect)
    pygame.display.flip() # ‼️ 這是此函數最後的 flip
    pygame.time.wait(2000) # 等待玩家觀看

    return player1_selected_skill, player2_selected_skill


# --- 遊戲會話管理 ---
# ⭐️ 修改 game_session 以接收 main_screen_surface_param
def game_session(main_screen_surface_param, current_input_mode, p1_skill_code_from_menu, p2_skill_code_from_menu, current_game_mode_value):
    if DEBUG_MAIN_FULLSCREEN:
        print(f"[DEBUG_MAIN_FULLSCREEN][game_session] Called. Main screen surface: {type(main_screen_surface_param)}")

    levels = LevelManager(models_folder=resource_path("models"))
    common_game_config = {
        'mass': 1.0, 'e_ball_paddle': 1.0, 'mu_ball_paddle': 0.4, 'enable_spin': True, 'magnus_factor': 0.01,
        'speed_increment': 0.002, 'speed_scale_every': 3, 'initial_ball_speed': 0.025,
        'initial_angle_deg_range': [-45, 45],
        'freeze_duration_ms': GameSettings.FREEZE_DURATION_MS,
        'countdown_seconds': GameSettings.COUNTDOWN_SECONDS,
        'bg_music': "bg_music_level1.mp3"
    }
    # ⭐️ render_size_for_env 是邏輯尺寸，Renderer 會用它來計算縮放
    render_size_for_env = 400
    paddle_height_for_env = 10
    ball_radius_for_env = 10
    player1_env_config = {}
    opponent_env_config = {}
    ai_agent = None

    if current_game_mode_value == GameSettings.GameMode.PLAYER_VS_AI:
        # ⭐️ show_level_selection 需要 main_screen_surface_param
        # ⭐️ 在這個階段，sound_manager 需要從 game_session 傳遞，或者 show_level_selection 內部創建（暫定內部創建）
        # ⭐️ 我們將在 menu.py 修改時決定 sound_manager 的傳遞方式
        # ⭐️ 假設 show_level_selection 已修改為接收 main_screen
        temp_sound_manager_for_menu = SoundManager() # 臨時方案
        selected_level_index = show_level_selection(main_screen_surface_param, temp_sound_manager_for_menu)
        if selected_level_index is None: return "select_game_mode" # 返回到模式選擇
        
        levels.current_level = selected_level_index
        level_specific_config = levels.get_current_config()
        if not level_specific_config: # Fallback config
            level_specific_config = {
                'player_life': 3, 'ai_life': 3, 'player_paddle_width': 100, 'ai_paddle_width': 60,
                'initial_speed': 0.02, 'bg_music': "bg_music_level1.mp3",
                'freeze_duration_ms': common_game_config['freeze_duration_ms']
            }
        common_game_config.update(level_specific_config) # 更新通用配置
        player1_env_config = {
            'initial_x': 0.5, 'initial_paddle_width': level_specific_config.get('player_paddle_width', 100),
            'initial_lives': level_specific_config.get('player_life', 3), 'skill_code': p1_skill_code_from_menu, 'is_ai': False
        }
        opponent_env_config = {
            'initial_x': 0.5, 'initial_paddle_width': level_specific_config.get('ai_paddle_width', 60),
            'initial_lives': level_specific_config.get('ai_life', 3), 'skill_code': None, 'is_ai': True
        }
        relative_model_path = levels.get_current_model_path()
        if relative_model_path:
            absolute_model_path = resource_path(relative_model_path)
            if os.path.exists(absolute_model_path): ai_agent = AIAgent(absolute_model_path)
            else: print(f"AI model not found at: {absolute_model_path}")

    elif current_game_mode_value == GameSettings.GameMode.PLAYER_VS_PLAYER:
        pvp_game_specific_config = {
            'player1_paddle_width': 100, 'player1_lives': 3,
            'player2_paddle_width': 100, 'player2_lives': 3,
            'bg_music': "bg_music_pvp.mp3",
            'freeze_duration_ms': common_game_config.get('freeze_duration_ms', 500)
        }
        common_game_config.update(pvp_game_specific_config)
        player1_env_config = {
            'initial_x': 0.5, 'initial_paddle_width': pvp_game_specific_config.get('player1_paddle_width', 100),
            'initial_lives': pvp_game_specific_config.get('player1_lives', 3), 'skill_code': p1_skill_code_from_menu, 'is_ai': False
        }
        opponent_env_config = {
            'initial_x': 0.5, 'initial_paddle_width': pvp_game_specific_config.get('player2_paddle_width', 100),
            'initial_lives': pvp_game_specific_config.get('player2_lives', 3), 'skill_code': p2_skill_code_from_menu, 'is_ai': False
        }
    else:
        if DEBUG_MAIN: print(f"[game_session] Unknown game mode: {current_game_mode_value}. Returning to select_game_mode.")
        return "select_game_mode"

    env = PongDuelEnv(
        game_mode=current_game_mode_value,
        player1_config=player1_env_config,
        opponent_config=opponent_env_config,
        common_config=common_game_config,
        render_size=render_size_for_env, # 這是邏輯渲染尺寸
        paddle_height_px=paddle_height_for_env,
        ball_radius_px=ball_radius_for_env,
        # ⭐️ 將 main_screen_surface_param 傳遞給 PongDuelEnv，以便它傳遞給 Renderer
        initial_main_screen_surface_for_renderer=main_screen_surface_param
    )
    obs, _ = env.reset()
    env.render() # 第一次渲染，Renderer 會被初始化

    # 檢查 Renderer 是否成功使用了傳入的 surface
    if not env.renderer or not env.renderer.window or env.renderer.window is not main_screen_surface_param:
        if DEBUG_MAIN_FULLSCREEN:
            print("[DEBUG_MAIN_FULLSCREEN][game_session] CRITICAL: Renderer did not use the provided main_screen_surface_param.")
            if env.renderer and env.renderer.window:
                 print(f"    Renderer window is: {type(env.renderer.window)}, main_screen was: {type(main_screen_surface_param)}")
            elif not env.renderer:
                 print("    env.renderer is None.")
            else:
                 print("    env.renderer.window is None.")
        # 根據實際情況，這裡可能需要更強制的錯誤處理或退出
        # return "quit" # 如果 Renderer 沒有正確設定，遊戲無法繼續

    # 背景音樂播放
    if hasattr(env, 'sound_manager') and env.sound_manager and hasattr(env, 'bg_music') and env.bg_music:
        bg_music_filename = env.bg_music # 從 common_config 或 level_config 獲取
        bg_music_path = resource_path(f"assets/{bg_music_filename}")
        if os.path.exists(bg_music_path):
            try:
                pygame.mixer.music.load(bg_music_path)
                pygame.mixer.music.set_volume(GameSettings.BACKGROUND_MUSIC_VOLUME)
                env.sound_manager.play_bg_music() # 假設 play_bg_music() 處理循環
            except pygame.error as e:
                if DEBUG_MAIN: print(f"[DEBUG][game_session] Error loading/playing music '{bg_music_path}': {e}")
        else:
            if DEBUG_MAIN: print(f"[DEBUG][game_session] Warning: Music file not found: {bg_music_path}")

    # --- 遊戲開始前的倒數 ---
    initial_countdown_duration = common_game_config.get('countdown_seconds', GameSettings.COUNTDOWN_SECONDS)
    if initial_countdown_duration > 0 :
        if DEBUG_MAIN: print(f"[DEBUG][game_session] Starting initial countdown for {initial_countdown_duration} seconds.")
        # show_countdown 使用 env.renderer.window，該 window 應該是 main_screen_surface_param
        show_countdown(env)

    # --- 遊戲主迴圈 ---
    game_running = True
    game_session_result_state = "select_game_mode" # 預設返回到模式選擇

    while game_running:
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                game_running = False
                game_session_result_state = "quit"
            elif event.type == pygame.KEYDOWN:
                if event.key == pygame.K_ESCAPE:
                    if DEBUG_MAIN: print("[DEBUG][game_session] ESC pressed during gameplay. Ending session.")
                    game_running = False
                    game_session_result_state = "select_game_mode" # 按 ESC 返回選單
        if not game_running: break # 如果事件導致 game_running 為 False，跳出迴圈

        keys = pygame.key.get_pressed()
        p1_ingame_action = 1 # 預設不動 (0: left, 1: stay, 2: right)

        # 玩家一輸入 (鍵盤或滑鼠)
        if current_input_mode == "keyboard":
            if keys[P1_GAME_KEYS['LEFT_KB']]: p1_ingame_action = 0
            elif keys[P1_GAME_KEYS['RIGHT_KB']]: p1_ingame_action = 2
        elif current_input_mode == "mouse":
            mouse_x_abs, _ = pygame.mouse.get_pos() # 獲取的是實際螢幕座標
            
            # ‼️ 滑鼠座標轉換的簡化處理 (假設遊戲區域在螢幕左上角且未縮放)
            # ‼️ 這部分在後續實現自適應縮放時【極其重要】，需要精確轉換
            # ‼️ 目前，如果 Renderer 繪製的遊戲區域不在 (0,0) 或者有縮放，滑鼠控制會不準確
            game_area_x_start_on_screen = 0 # 假設遊戲區域在螢幕上的X軸起始點 (未縮放時為0)
                                        # 如果 Renderer 將遊戲區域繪製在螢幕中央，這裡需要是該區域的 screen_x
            game_area_width_on_screen = env.render_size # 假設遊戲區域在螢幕上的寬度 (未縮放時等於邏輯寬度)
                                                    # 如果有縮放，這裡需要是縮放後的寬度
            
            mouse_x_in_game_area = mouse_x_abs - game_area_x_start_on_screen
            # 將遊戲區域內的滑鼠X座標轉換為0-1的相對值
            mouse_x_relative = mouse_x_in_game_area / game_area_width_on_screen if game_area_width_on_screen > 0 else 0.5
            
            threshold = 0.02 # 移動閾值
            if mouse_x_relative < env.player1.x - threshold: p1_ingame_action = 0
            elif mouse_x_relative > env.player1.x + threshold: p1_ingame_action = 2

        # 玩家一技能
        if keys[P1_GAME_KEYS['SKILL_KB']]:
            if DEBUG_MAIN: print(f"[DEBUG][game_session] P1 skill key '{pygame.key.name(P1_GAME_KEYS['SKILL_KB'])}' pressed.")
            env.activate_skill(env.player1)

        # 對手/玩家二輸入
        opponent_ingame_action = 1 # 預設不動
        if current_game_mode_value == GameSettings.GameMode.PLAYER_VS_AI:
            if ai_agent:
                opponent_ingame_action = ai_agent.select_action(obs.copy()) # AI根據觀察選擇動作
        else: # PLAYER_VS_PLAYER
            if keys[P2_GAME_KEYS['LEFT']]: opponent_ingame_action = 0
            elif keys[P2_GAME_KEYS['RIGHT']]: opponent_ingame_action = 2
            # 玩家二技能
            if keys[P2_GAME_KEYS['SKILL']]:
                if DEBUG_MAIN: print(f"[DEBUG][game_session] P2 skill key '{pygame.key.name(P2_GAME_KEYS['SKILL'])}' pressed.")
                env.activate_skill(env.opponent)

        # 環境步進
        obs, reward, round_done, game_over, info = env.step(p1_ingame_action, opponent_ingame_action)
        env.render() # 渲染遊戲畫面 (應使用 main_screen_surface_param)

        # 控制幀率
        if hasattr(env, 'renderer') and env.renderer and hasattr(env.renderer, 'clock'):
            env.renderer.clock.tick(60) # 使用 Renderer 內部時鐘
        else:
            if DEBUG_MAIN: print("[DEBUG][game_session] Warning: env.renderer.clock not found, using pygame.time.delay for FPS control.")
            pygame.time.delay(16) # 約 60 FPS

        # 回合結束處理
        if round_done:
            if DEBUG_MAIN: print(f"[DEBUG][game_session] Round Done. Info: {info}. P1 Lives: {env.player1.lives}, Opponent Lives: {env.opponent.lives}")

            freeze_start_time = pygame.time.get_ticks()
            current_freeze_duration = env.freeze_duration # 從env獲取凍結時間
            if DEBUG_MAIN: print(f"[DEBUG][game_session] Starting freeze effect (flashing) for {current_freeze_duration}ms.")

            while pygame.time.get_ticks() - freeze_start_time < current_freeze_duration:
                for event_freeze in pygame.event.get(): # 在凍結時仍需處理事件以允許退出
                    if event_freeze.type == pygame.QUIT:
                        game_running = False; game_session_result_state = "quit"; break
                    elif event_freeze.type == pygame.KEYDOWN:
                        if event_freeze.key == pygame.K_ESCAPE:
                            if DEBUG_MAIN: print("[DEBUG][game_session] ESC pressed during freeze. Ending session.")
                            game_running = False; game_session_result_state = "select_game_mode"; break
                if not game_running: break
                env.render() # 持續渲染以顯示閃爍效果
                pygame.time.delay(16) # 短暫延遲
            if not game_running: break # 如果在凍結時退出，則跳出主遊戲迴圈

            if DEBUG_MAIN: print(f"[DEBUG][game_session] Freeze effect finished. Game over: {game_over}")

            if game_over: # 遊戲徹底結束
                p1_wins_msg = "PLAYER 1 WINS!" if current_game_mode_value == GameSettings.GameMode.PLAYER_VS_PLAYER else "YOU WIN!"
                p1_loses_msg = "PLAYER 2 WINS!" if current_game_mode_value == GameSettings.GameMode.PLAYER_VS_PLAYER else "YOU LOSE!"
                p1_color = Style.PLAYER_COLOR
                opponent_color = Style.AI_COLOR # PvP 時 P2 也可視為 opponent_color 或定義 P2_COLOR

                # show_result_banner 使用 env.renderer.window，該 window 應該是 main_screen_surface_param
                if env.player1.lives <= 0:
                    if env.sound_manager: env.sound_manager.play_lose_sound()
                    show_result_banner(env.renderer.window, p1_loses_msg, opponent_color)
                elif env.opponent.lives <= 0:
                    if env.sound_manager: env.sound_manager.play_win_sound()
                    show_result_banner(env.renderer.window, p1_wins_msg, p1_color)
                
                game_running = False # 遊戲結束，停止會話迴圈
                game_session_result_state = "select_game_mode" # 返回模式選擇
            else: # 回合結束，但遊戲未結束
                scorer = info.get('scorer') # 從 env.step 返回的 info 中獲取得分者
                if DEBUG_MAIN: print(f"[DEBUG][game_session] Round ended, scorer: {scorer}. Resetting ball for next round (NO COUNTDOWN).")
                
                if scorer == 'player1':
                    env.reset_ball_after_score(scored_by_player1=True)
                elif scorer == 'opponent':
                    env.reset_ball_after_score(scored_by_player1=False)
                else: # 如果 scorer 未明確 (例如蟲子技能被拍掉，無人得分)
                    if DEBUG_MAIN: print(f"[DEBUG][game_session] Scorer info ('{scorer}') not definitive for serve, randomizing.")
                    env.reset_ball_after_score(scored_by_player1=random.choice([True, False])) # 隨機發球
                
                obs = env._get_obs() # 獲取新回合的觀測值
                if DEBUG_MAIN: print("[DEBUG][game_session] Ball to be served immediately after freeze.")
    
    # 遊戲會話結束後的清理
    if hasattr(env, 'sound_manager'): env.sound_manager.stop_bg_music()
    env.close() # 關閉環境資源 (Renderer 等)
    return game_session_result_state


def main_loop():
    pygame.init()
    pygame.font.init()

    try:
        screen_info = pygame.display.Info()
        ACTUAL_SCREEN_WIDTH = screen_info.current_w
        ACTUAL_SCREEN_HEIGHT = screen_info.current_h
        if DEBUG_MAIN_FULLSCREEN:
            print(f"[DEBUG_MAIN_FULLSCREEN][main_loop] Detected screen resolution: {ACTUAL_SCREEN_WIDTH}x{ACTUAL_SCREEN_HEIGHT}")
    except pygame.error as e:
        if DEBUG_MAIN_FULLSCREEN:
            print(f"[DEBUG_MAIN_FULLSCREEN][main_loop] Pygame display error: {e}. Defaulting to 1280x720.")
        ACTUAL_SCREEN_WIDTH = 1280
        ACTUAL_SCREEN_HEIGHT = 720

    try:
        main_screen = pygame.display.set_mode((ACTUAL_SCREEN_WIDTH, ACTUAL_SCREEN_HEIGHT), pygame.FULLSCREEN)
        if DEBUG_MAIN_FULLSCREEN:
            print(f"[DEBUG_MAIN_FULLSCREEN][main_loop] Fullscreen mode attempted. Resulting screen size: {main_screen.get_size()}")
    except pygame.error as e:
        if DEBUG_MAIN_FULLSCREEN:
            print(f"[DEBUG_MAIN_FULLSCREEN][main_loop] Failed to set fullscreen: {e}. Falling back to windowed {ACTUAL_SCREEN_WIDTH}x{ACTUAL_SCREEN_HEIGHT}.")
        try:
            main_screen = pygame.display.set_mode((ACTUAL_SCREEN_WIDTH, ACTUAL_SCREEN_HEIGHT))
            if DEBUG_MAIN_FULLSCREEN:
                print(f"[DEBUG_MAIN_FULLSCREEN][main_loop] Windowed fallback. Screen size: {main_screen.get_size()}")
        except pygame.error as e2:
            print(f"[CRITICAL_ERROR_MAIN][main_loop] Could not set any display mode: {e2}. Exiting.")
            pygame.quit()
            sys.exit()

    pygame.display.set_caption("Pong Soul")

    current_input_mode = "keyboard"
    p1_selected_skill_code = None
    p2_selected_skill_code = None
    current_game_mode = None
    sound_manager = SoundManager() # 主循環的 SoundManager，主要用於傳遞給選單

    next_game_flow_step = "select_game_mode"
    running = True

    while running:
        if DEBUG_MAIN:
            print(f"[main_loop] Current step: {next_game_flow_step}")

        # 絕大部分的 pygame.display.flip() 應該集中在此處，在所有繪製完成後調用一次。
        # 選單函數和 game_session 內部理論上不應自行 flip()，除非是特殊效果如倒數。
        # 但為了第一階段的簡化和逐步遷移，它們內部可能仍有 flip。

        if next_game_flow_step == "select_game_mode":
            # ⭐️ 調用 select_game_mode，傳遞 main_screen 和 sound_manager
            # ⭐️ select_game_mode 函數內部會繪製到 main_screen 並處理自己的事件循環和 flip (暫時)
            current_game_mode = select_game_mode(main_screen, sound_manager)
            if current_game_mode is None: # 表示從選單返回 (例如按ESC或選了退出) 或發生錯誤
                if DEBUG_MAIN_FULLSCREEN:
                    print(f"[DEBUG_MAIN_FULLSCREEN][main_loop] select_game_mode returned None. Setting flow to 'quit'.")
                next_game_flow_step = "quit"
                continue # 立即進入下一次循環檢查 "quit"
            
            p1_selected_skill_code = None # 重置技能選擇
            p2_selected_skill_code = None
            next_game_flow_step = "select_input"

        elif next_game_flow_step == "select_input":
            # ⭐️ 調用 select_input_method
            selection_result = select_input_method(main_screen, sound_manager)
            if selection_result == "back_to_game_mode_select":
                next_game_flow_step = "select_game_mode"
                continue
            elif selection_result is None: # 如果返回 None (可能 ESC)
                if DEBUG_MAIN_FULLSCREEN:
                    print(f"[DEBUG_MAIN_FULLSCREEN][main_loop] select_input_method returned None. Going to 'select_game_mode'.")
                next_game_flow_step = "select_game_mode" # 返回到上一個選單
                continue
            current_input_mode = selection_result # "keyboard" or "mouse"
            
            if current_game_mode == GameSettings.GameMode.PLAYER_VS_AI:
                next_game_flow_step = "select_skill_pva"
            elif current_game_mode == GameSettings.GameMode.PLAYER_VS_PLAYER:
                # ⭐️ run_pvp_selection_phase 繪製在 main_screen 上
                p1_selected_skill_code, p2_selected_skill_code = run_pvp_selection_phase(main_screen, sound_manager)
                if p1_selected_skill_code is None or p2_selected_skill_code is None: # 有人取消
                    next_game_flow_step = "select_input" # 返回輸入選擇 (或遊戲模式選擇)
                    continue
                # 成功選擇技能後，進入遊戲會話
                next_game_flow_step = game_session(main_screen, current_input_mode, p1_selected_skill_code, p2_selected_skill_code, current_game_mode)
            else:
                if DEBUG_MAIN: print(f"[main_loop] Invalid current_game_mode after input select: {current_game_mode}")
                next_game_flow_step = "select_game_mode" # 安全回退

        elif next_game_flow_step == "select_skill_pva":
            # ⭐️ 假設的 PvA 技能選單邏輯區域 (目前未縮放，直接使用像素)
            # ⭐️ 在後續縮放階段，這個 render_area 會根據 main_screen 和邏輯尺寸計算
            # ⭐️ 目前，這個 Rect 的座標是相對於 main_screen 左上角的
            # ⭐️ 如果 main_screen 比 500x500 大，選單會出現在左上角。
            # ⭐️ 選單函數需要能夠在指定的 render_area 內繪製。
            menu_logical_width = 500 # PvA技能選單的邏輯寬度
            menu_logical_height = 500 # PvA技能選單的邏輯高度
            
            # Phase 1: 簡單地將選單放在螢幕左上角（如果螢幕夠大）
            # Phase 2: 計算偏移使其居中並縮放
            # render_area_for_pva_skill_select = pygame.Rect(
            #     (ACTUAL_SCREEN_WIDTH - menu_logical_width) // 2,  # 居中X (未縮放)
            #     (ACTUAL_SCREEN_HEIGHT - menu_logical_height) // 2, # 居中Y (未縮放)
            #     menu_logical_width,
            #     menu_logical_height
            # )
            # 簡化版：假設 select_skill 繪製在 main_screen 的 (0,0) 開始的 500x500 區域
            render_area_for_pva_skill_select = pygame.Rect(0,0, menu_logical_width, menu_logical_height)


            p1_selected_skill_code = select_skill(
                main_screen_surface=main_screen,
                render_area=render_area_for_pva_skill_select, # 傳遞繪製區域
                key_map=DEFAULT_MENU_KEYS, # PvA 使用預設按鍵
                sound_manager=sound_manager,
                player_identifier="Player"
            )
            if p1_selected_skill_code is None: # 玩家取消選擇
                next_game_flow_step = "select_input" # 返回輸入選擇
                continue
            
            # 技能選擇完成，進入遊戲會話
            next_game_flow_step = game_session(main_screen, current_input_mode, p1_selected_skill_code, None, current_game_mode)
        
        elif next_game_flow_step == "quit":
            running = False # 設定 running 為 False 以退出主迴圈
        
        else: # 從 game_session 返回的狀態，通常是 "select_game_mode" 或 "quit"
            if DEBUG_MAIN_FULLSCREEN:
                print(f"[DEBUG_MAIN_FULLSCREEN][main_loop] Game session or other flow returned: '{next_game_flow_step}'. Resetting to 'select_game_mode' if not 'quit'.")
            # 如果 next_game_flow_step 不是已知的流程控制狀態，則重置為選擇遊戲模式
            if next_game_flow_step not in ["select_game_mode", "select_input", "select_skill_pva", "quit"]:
                if DEBUG_MAIN: print(f"[main_loop] Unknown next_game_flow_step: '{next_game_flow_step}'. Defaulting to 'select_game_mode'.")
                next_game_flow_step = "select_game_mode"

        # ‼️ 主循環的 flip() 應該在這裡，但在我們完全控制選單和遊戲的 flip 之前，
        # ‼️ 暫時依賴它們內部的 flip。一旦所有繪圖都彙總到 main_loop，
        # ‼️ 我們可以在這裡統一 flip。
        # pygame.display.flip() # <--- 最終目標是將主要的 flip 放在這裡

    # 主迴圈結束
    if DEBUG_MAIN_FULLSCREEN: print("[DEBUG_MAIN_FULLSCREEN][main_loop] Exiting application main_loop.")
    pygame.quit()
    sys.exit()

if __name__ == '__main__':
    main_loop()