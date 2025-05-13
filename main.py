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
def main_loop():
    # ... (current_input_mode, p1_selected_skill_code, etc. 保持不變) ...
    current_input_mode = "keyboard" 
    p1_selected_skill_code = None
    p2_selected_skill_code = None 
    current_game_mode = None
    sound_manager = SoundManager() 
    main_screen_width, main_screen_height = 500, 500
    main_screen = pygame.display.set_mode((main_screen_width, main_screen_height))
    pygame.display.set_caption("Pong Soul")
    next_game_flow_step = "select_game_mode"
    running = True

    while running:
        if DEBUG_MAIN: print(f"[main_loop] Current step: {next_game_flow_step}")

        if next_game_flow_step == "select_game_mode":
            # ... (與之前相同)
            if main_screen.get_width() != 500 or main_screen.get_height() != 500: 
                 main_screen = pygame.display.set_mode((500,500))
            pygame.display.set_caption("Pong Soul - Select Mode")
            current_game_mode = select_game_mode() 
            if current_game_mode is None: next_game_flow_step = "quit"; continue
            p1_selected_skill_code = None; p2_selected_skill_code = None
            next_game_flow_step = "select_input"

        elif next_game_flow_step == "select_input":
            if main_screen.get_width() != 500 or main_screen.get_height() != 500:
                 main_screen = pygame.display.set_mode((500,500))
            pygame.display.set_caption("Pong Soul - Select Controller")
            
            selection_result = select_input_method() # ⭐️ 接收返回值
            
            if selection_result == "back_to_game_mode_select": # ⭐️ 檢查是否返回 "back"
                next_game_flow_step = "select_game_mode"
                continue
            elif selection_result is None: # 可能的意外退出或未處理的返回
                if DEBUG_MAIN: print("[main_loop] select_input_method returned None unexpectedly, going to game mode select.")
                next_game_flow_step = "select_game_mode" # 作為安全回退
                continue
            
            current_input_mode = selection_result # "keyboard" or "mouse"
            
            if current_game_mode == GameSettings.GameMode.PLAYER_VS_AI:
                next_game_flow_step = "select_skill_pva"
            # ... (後續 PvP 邏輯與之前相同) ...
            elif current_game_mode == GameSettings.GameMode.PLAYER_VS_PLAYER:
                pvp_menu_width, pvp_menu_height = 1000, 600 
                if main_screen.get_width() != pvp_menu_width or main_screen.get_height() != pvp_menu_height:
                    main_screen = pygame.display.set_mode((pvp_menu_width, pvp_menu_height))
                pygame.display.set_caption("Pong Soul - PVP Skill Selection")
                p1_selected_skill_code, p2_selected_skill_code = run_pvp_selection_phase(main_screen, sound_manager)
                if p1_selected_skill_code is None or p2_selected_skill_code is None: 
                    next_game_flow_step = "select_input"; continue
                next_game_flow_step = game_session(current_input_mode, p1_selected_skill_code, p2_selected_skill_code, current_game_mode)
            else: next_game_flow_step = "select_game_mode"


        # ... (select_skill_pva, quit, else 邏輯與之前相同) ...
        elif next_game_flow_step == "select_skill_pva":
            if main_screen.get_width() != 500 or main_screen.get_height() != 500:
                 main_screen = pygame.display.set_mode((500,500))
            pygame.display.set_caption("Pong Soul - Select Skill (PVA)")
            pva_render_area = main_screen.get_rect()
            p1_selected_skill_code = select_skill(
                main_screen_surface=main_screen, render_area=pva_render_area,
                key_map=DEFAULT_MENU_KEYS, sound_manager=sound_manager, player_identifier="Player"
            )
            if p1_selected_skill_code is None: next_game_flow_step = "select_input"; continue # 如果技能選擇也允許ESC返回到輸入選擇
            next_game_flow_step = game_session(current_input_mode, p1_selected_skill_code, None, current_game_mode)
        elif next_game_flow_step == "quit": running = False
        else: 
            if next_game_flow_step not in ["select_game_mode", "select_input", "select_skill_pva", "quit"]:
                next_game_flow_step = "select_game_mode" 
    
    if DEBUG_MAIN: print("[main_loop] Exiting application.")
    pygame.quit()
    sys.exit()

if __name__ == '__main__':
    main_loop()