# main.py (修正版)

import pygame
import sys
import time
import os
import torch # 雖然此處不直接使用torch的api，但AIAgent會用到
import numpy # 同上，AIAgent或env可能用到

# 初始化 pygame 系統 (應在最開始執行一次)
pygame.init()
pygame.font.init() # 字型模組初始化

# 專案路徑設定，確保能載入模組
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from envs.pong_duel_env import PongDuelEnv
from game.ai_agent import AIAgent
from game.level import LevelManager
from game.theme import Style
from game.menu import (
    show_level_selection,
    select_input_method,
    select_skill,  # 已改造
    select_game_mode # 未改造 (假設仍是全螢幕阻塞型)
)
from game.settings import GameSettings
from game.sound import SoundManager
from utils import resource_path

# --- 倒數與結果顯示函數 (保持不變) ---
def show_countdown(env):
    font = Style.get_font(60)
    # env.window 應該在 env.render() 第一次被呼叫時由 Renderer 初始化
    if not env.window:
        print("Warning: env.window not initialized before show_countdown. Forcing render.")
        env.render() # 確保 env.window 存在
        if not env.window: # 如果仍然不存在，則無法進行
            print("Error: env.window could not be initialized for countdown.")
            return

    screen = env.window
    for i in range(GameSettings.COUNTDOWN_SECONDS, 0, -1):
        if hasattr(env, 'sound_manager') and env.sound_manager:
            env.sound_manager.play_countdown()

        screen.fill(Style.BACKGROUND_COLOR)
        countdown_surface = font.render(str(i), True, Style.TEXT_COLOR)
        # Renderer 的 offset_y
        offset_y_val = env.renderer.offset_y if hasattr(env, 'renderer') and env.renderer else 0
        countdown_rect = countdown_surface.get_rect(
            center=(env.render_size // 2, env.render_size // 2 + offset_y_val)
        )
        screen.blit(countdown_surface, countdown_rect)
        pygame.display.flip()
        pygame.time.wait(1000)

def show_result_banner(screen, text, color):
    # screen 參數是 pygame.Surface 物件 (即 env.window)
    if not screen:
        print(f"Error: Screen not available for show_result_banner with text: {text}")
        return
    font = Style.get_font(40)
    # 背景顏色應使用當前主題的背景色
    screen.fill(Style.BACKGROUND_COLOR) # 或者直接使用 screen.fill(Style.BACKGROUND_COLOR)
    banner = font.render(text, True, color)
    rect = banner.get_rect(center=(screen.get_width() // 2, screen.get_height() // 2))
    screen.blit(banner, rect)
    pygame.display.flip()
    pygame.time.delay(1500)

# --- 按鍵映射定義 ---
P1_MENU_KEYS = { # 用於PVP選單中的玩家一
    'UP': pygame.K_w,
    'DOWN': pygame.K_s,
    'CONFIRM': pygame.K_e,
    'CANCEL': pygame.K_q
}

# 用於PVA選單（單人時）或PVP選單中的玩家二
DEFAULT_MENU_KEYS = {
    'UP': pygame.K_UP,
    'DOWN': pygame.K_DOWN,
    'CONFIRM': pygame.K_RETURN,
    'CANCEL': pygame.K_ESCAPE
}

# --- PVP 選單階段處理 ---
def run_pvp_selection_phase(main_screen, sound_manager_instance): # 傳入 sound_manager_instance
    screen_width = main_screen.get_width()
    screen_height = main_screen.get_height()

    left_rect = pygame.Rect(0, 0, screen_width // 2, screen_height)
    right_rect = pygame.Rect(screen_width // 2, 0, screen_width // 2, screen_height)
    divider_color = (100, 100, 100)

    player1_selected_skill = None
    player2_selected_skill = None

    # 玩家一選擇技能 (左側)
    main_screen.fill(Style.BACKGROUND_COLOR) # 清理螢幕
    pygame.draw.line(main_screen, divider_color, (screen_width // 2, 0), (screen_width // 2, screen_height), 2)
    # pygame.display.flip() # 由 select_skill 內部 flip

    print("Player 1, please select your skill using W, S, E (Confirm), Q (Back) keys.")
    player1_selected_skill = select_skill( # 已改造的 select_skill
        main_screen_surface=main_screen,
        render_area=left_rect,
        key_map=P1_MENU_KEYS,
        sound_manager=sound_manager_instance,
        player_identifier="Player 1"
    )

    if player1_selected_skill is None:
        print("Player 1 cancelled skill selection.")
        return None, None

    # 在左側顯示玩家一的選擇
    # (select_skill 在返回前已經 flip 了最後一幀，所以左側是 P1 選單的樣子)
    # 我們可以覆蓋繪製P1的選擇
    pygame.draw.rect(main_screen, Style.BACKGROUND_COLOR, left_rect) # 清理左側區域
    font_info = Style.get_font(Style.ITEM_FONT_SIZE)
    p1_info_text = font_info.render(f"P1 Skill: {player1_selected_skill}", True, Style.TEXT_COLOR)
    main_screen.blit(p1_info_text, (left_rect.left + 20, left_rect.centery))
    pygame.draw.line(main_screen, divider_color, (screen_width // 2, 0), (screen_width // 2, screen_height), 2) # 重繪分割線
    # pygame.display.flip() # 暫不 flip，等待 P2 選單的第一次 flip

    print(f"Player 1 selected: {player1_selected_skill}")
    print("Player 2, please select your skill using Arrow Keys, Enter (Confirm), Esc (Back).")

    # 玩家二選擇技能 (右側)
    player2_selected_skill = select_skill( # 已改造的 select_skill
        main_screen_surface=main_screen,
        render_area=right_rect,
        key_map=DEFAULT_MENU_KEYS, # P2 使用標準按鍵
        sound_manager=sound_manager_instance,
        player_identifier="Player 2"
    )

    if player2_selected_skill is None:
        print("Player 2 cancelled skill selection.")
        return None, None # 讓主流程決定如何處理 (例如回到P1重選或模式選擇)

    # 在右側顯示玩家二的選擇
    pygame.draw.rect(main_screen, Style.BACKGROUND_COLOR, right_rect) # 清理右側區域
    p2_info_text = font_info.render(f"P2 Skill: {player2_selected_skill}", True, Style.TEXT_COLOR)
    main_screen.blit(p2_info_text, (right_rect.left + 20, right_rect.centery))
    # 左側P1的選擇資訊依然存在
    # pygame.display.flip() # 再次由select_skill內部flip過了，這裡可以選擇性再flip一次確保同步

    print(f"Player 2 selected: {player2_selected_skill}")
    
    main_screen.fill(Style.BACKGROUND_COLOR) # 統一清空
    font_large = Style.get_font(Style.TITLE_FONT_SIZE)
    ready_text_str = "Players Ready! Starting..."
    if not player1_selected_skill or not player2_selected_skill: # 理論上不會到這裡，除非select_skill返回空字串等意外
        ready_text_str = "Error in skill selection!"
    ready_text = font_large.render(ready_text_str, True, Style.TEXT_COLOR)
    ready_rect = ready_text.get_rect(center=(screen_width // 2, screen_height // 2))
    main_screen.blit(ready_text, ready_rect)
    pygame.display.flip()
    pygame.time.wait(2000)

    return player1_selected_skill, player2_selected_skill

# --- 遊戲會話管理 ---
def game_session(initial_input_mode, p1_skill_code, p2_skill_code, current_game_mode_value):
    print(f"Game Session Starting. P1 Skill: {p1_skill_code}, P2 Skill: {p2_skill_code}, Mode: {current_game_mode_value}")

    active_skill_for_env_init = p1_skill_code # PongDuelEnv 初始化時需要一個 active_skill_name
                                         # 後續需要改造 PongDuelEnv 以支援雙技能
    
    levels = LevelManager(models_folder=resource_path("models"))
    config = {}
    relative_model_path = None

    if current_game_mode_value == GameSettings.GameMode.PLAYER_VS_AI:
        # PVA 模式下，p2_skill_code 應為 None
        # 需要選擇關卡來決定AI模型和參數
        # 假設 show_level_selection 未改造，在 main_loop 中處理其螢幕
        selected_index_val = show_level_selection() # 此函數內部會處理自己的螢幕和迴圈
        if selected_index_val is None:
            return "select_skill_pva" # 返回到PVA的技能選擇 (或更早的狀態)
        
        levels.current_level = selected_index_val
        relative_model_path = levels.get_current_model_path()
        config = levels.get_current_config()
        if not relative_model_path or not config:
            print(f"❌ Config or model not found for PVA level {selected_index_val}.")
            return "select_game_mode" # 嚴重錯誤，返回模式選擇
    
    elif current_game_mode_value == GameSettings.GameMode.PLAYER_VS_PLAYER:
        print("PVP mode session. Using a default or shared level configuration.")
        # PVP 可以使用一個固定的關卡設定，或者也允許選擇（但忽略AI模型）
        levels.current_level = 0 # 例如，總是使用level1的場地設定
        config = levels.get_current_config()
        if not config:
            print("Warning: PVP using fallback config as default level config not found.")
            config = {
                'initial_speed': 0.025, 'enable_spin': True, 'magnus_factor': 0.01,
                'speed_increment': 0.002, 'speed_scale_every': 3,
                'player_life': 3, 'ai_life': 3, # ai_life 在PVP中視為 P2 life
                'player_paddle_width': 100, 'ai_paddle_width': 100, # ai_paddle_width 在PVP中為 P2 paddle
                'bg_music': "bg_music_level1.mp3",
                'player_max_life': 3, 'ai_max_life': 3
            }
        # 確保PVP模式下雙方球拍寬度等參數合理 (ai_life/ai_paddle_width 會被env內部解釋為P2)
        if 'player_max_life' not in config: config['player_max_life'] = config.get('player_life',3)
        if 'ai_max_life' not in config: config['ai_max_life'] = config.get('ai_life',3)


    if not config: # 如果到這裡 config 還是空的，說明有問題
        print("Error: Game configuration is empty. Aborting session.")
        return "select_game_mode"

    env = PongDuelEnv(
        render_size=400,
        active_skill_name=active_skill_for_env_init, # PongDuelEnv 需要改造以處理雙技能
        game_mode=current_game_mode_value
        # p1_skill_name=p1_skill_code, # 未來傳遞方式
        # p2_skill_name=p2_skill_code  # 未來傳遞方式
    )
    env.set_params_from_config(config)
    # 此時 env.renderer 和 env.window 尚未被 renderer 初始化
    # 第一次 env.render() 會做初始化。

    ai = None
    if current_game_mode_value == GameSettings.GameMode.PLAYER_VS_AI:
        if relative_model_path:
            absolute_model_path = resource_path(relative_model_path)
            if not os.path.exists(absolute_model_path):
                print(f"❌ Model file not found at: {absolute_model_path}")
                env.close() # 雖然 window 可能未創建，但 env 內部可能有其他資源
                return "select_game_mode"
            ai = AIAgent(absolute_model_path)
            print(f"AI Agent loaded: {relative_model_path}")
        else:
            print("❌ Error: PVA mode but no AI model path. This shouldn't happen if level selection worked.")
            env.close()
            return "select_game_mode"
    else: # PVP mode
        print("PVP mode: AI Agent not loaded.")

    obs, _ = env.reset()
    env.render() # 第一次渲染，初始化 env.renderer 和 env.window
    if not env.window: # 再次檢查
        print("Fatal Error: env.window could not be initialized by renderer.")
        env.close()
        return "quit" # 嚴重問題，直接退出


    if hasattr(env, 'sound_manager') and env.sound_manager and hasattr(env, 'bg_music') and env.bg_music:
        bg_music_path = resource_path(f"assets/{env.bg_music}")
        if os.path.exists(bg_music_path):
            try:
                pygame.mixer.music.load(bg_music_path)
                pygame.mixer.music.set_volume(GameSettings.BACKGROUND_MUSIC_VOLUME)
                env.sound_manager.play_bg_music()
            except pygame.error as e:
                print(f"Error loading/playing background music {bg_music_path}: {e}")
        else:
            print(f"Warning: Background music file not found: {bg_music_path}")

    show_countdown(env)

    game_running = True
    while game_running:
        # 事件處理應優先，以允許退出
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                game_running = False # 會跳出 while 迴圈
                env.close()
                pygame.quit()
                sys.exit() # 確保程式終止

        if not game_running: break # 如果在事件處理中設定為False，則跳出

        keys = pygame.key.get_pressed()

        # --- 玩家一行動 (P1) ---
        p1_ingame_action = 1 # 預設不動
        if initial_input_mode == "keyboard":
            if keys[pygame.K_LEFT]: p1_ingame_action = 0
            elif keys[pygame.K_RIGHT]: p1_ingame_action = 2
        elif initial_input_mode == "mouse":
            mouse_x_abs, _ = pygame.mouse.get_pos()
            # 確保 env.render_size > 0 避免 ZeroDivisionError
            if env.render_size > 0:
                mouse_x_relative = mouse_x_abs / env.render_size
                threshold = 0.01
                if mouse_x_relative < env.player_x - threshold: p1_ingame_action = 0
                elif mouse_x_relative > env.player_x + threshold: p1_ingame_action = 2
        
        # --- 玩家一技能啟動 ---
        if keys[pygame.K_x]: # P1 遊戲中技能鍵 'x'
            # PongDuelEnv 需要知道是哪個玩家的技能，或技能本身知道自己屬於哪個玩家
            # 暫時假設 env.active_skill_name 是 P1 的技能
            p1_skill_instance = env.skills.get(p1_skill_code if p1_skill_code else env.active_skill_name)
            if p1_skill_instance:
                p1_skill_instance.activate()
            else:
                # 如果 p1_skill_code 為 None (例如 PVA 模式下跳過了技能選擇，或 PVP 未正确傳遞)
                # fallback 到 env.active_skill_name (通常是 env 初始化時的那個)
                fallback_skill = env.skills.get(env.active_skill_name)
                if fallback_skill: fallback_skill.activate()


        # --- 上方球拍行動 (AI 或 P2) ---
        top_paddle_action = 1
        if current_game_mode_value == GameSettings.GameMode.PLAYER_VS_AI:
            if ai:
                ai_obs = obs.copy()
                if len(ai_obs) >= 6: ai_obs[4], ai_obs[5] = ai_obs[5], ai_obs[4]
                top_paddle_action = ai.select_action(ai_obs)
        else: # PVP 模式
            # 玩家二遊戲中按鍵 (示例)
            if keys[pygame.K_j]: top_paddle_action = 0 # P2 左移 (J)
            elif keys[pygame.K_l]: top_paddle_action = 2 # P2 右移 (L)
            
            if keys[pygame.K_u]: # P2 遊戲中技能鍵 'u' (示例)
                 # PongDuelEnv 需要知道是哪個玩家的技能
                 p2_skill_instance = env.skills.get(p2_skill_code) # 假設 p2_skill_code 已傳入
                 if p2_skill_instance: # 這裡需要 PongDuelEnv 支持 P2 的技能實例
                     p2_skill_instance.activate() # 這需要 PongDuelEnv 內部正確設置 P2 的技能


        obs, reward, done, _, _ = env.step(p1_ingame_action, top_paddle_action)
        env.render() # 在 step 之後渲染最新狀態

        if hasattr(env, 'renderer') and env.renderer and hasattr(env.renderer, 'clock'):
            env.renderer.clock.tick(60)
        else:
            time.sleep(0.016) # ~60 FPS

        if done: # 回合結束
            player1_life, other_player_life = env.get_lives() # env.get_lives() 返回 (player_life, ai_life)
            
            freeze_start_time = pygame.time.get_ticks()
            while pygame.time.get_ticks() - freeze_start_time < env.freeze_duration:
                # 在凍結期間，也需要處理事件以允許退出
                for event_freeze in pygame.event.get():
                    if event_freeze.type == pygame.QUIT:
                        game_running = False; env.close(); pygame.quit(); sys.exit()
                env.render() # 持續渲染凍結效果
                pygame.time.delay(16) # 避免CPU滿載

            # 根據遊戲模式決定勝利/失敗訊息
            p1_wins_msg = "PLAYER 1 WINS!" if current_game_mode_value == GameSettings.GameMode.PLAYER_VS_PLAYER else "YOU WIN!"
            p1_loses_msg = "PLAYER 2 WINS!" if current_game_mode_value == GameSettings.GameMode.PLAYER_VS_PLAYER else "YOU LOSE!"
            
            # 根據遊戲模式決定獲勝者和失敗者的顏色
            # 這裡假設 Style.PLAYER_COLOR 是 P1, Style.AI_COLOR 在PVP時可以代表P2，或定義P2專屬顏色
            p1_color = Style.PLAYER_COLOR
            other_player_color = Style.AI_COLOR # 應替換為 P2 顏色 if PVP and P2 has own color

            if player1_life <= 0: # P1 輸
                if env.sound_manager: env.sound_manager.play_lose_sound()
                show_result_banner(env.window, p1_loses_msg, other_player_color)
                game_running = False
            elif other_player_life <= 0: # P1 贏 (AI 或 P2 輸)
                if env.sound_manager: env.sound_manager.play_win_sound()
                show_result_banner(env.window, p1_wins_msg, p1_color)
                game_running = False
            
            if not game_running: # 如果遊戲因勝負已分而結束
                env.close()
                return "select_game_mode" # 返回到模式選擇

            # 如果遊戲未結束，僅重置回合
            obs, _ = env.reset() # 重置球等狀態
            # show_countdown(env) # 回合間的倒數可以考慮是否需要，目前設計是失分後直接重置發球

    # game_running 正常結束 (例如 ESC 跳出遊戲會話，但目前沒有此設計)
    env.close()
    return "select_game_mode"

# --- 主應用程式迴圈 ---
def main_loop():
    current_input_mode = None
    p1_skill_code = None
    p2_skill_code = None # PVP模式下玩家二的技能
    current_game_mode_value = None
    
    # 全域的 SoundManager 實例
    sound_manager_instance = SoundManager()

    # 主螢幕 surface，由各階段設定
    # Pygame 顯示模式最好只在必要時設定，避免頻繁切換導致問題
    # 初始設定一個通用的大小，選單函數內部不應再 set_mode
    main_screen = pygame.display.set_mode((500, 500)) # 預設選單大小
    pygame.display.set_caption("Pong Soul")

    next_step_state = "select_game_mode"

    while True:
        print(f"Main loop, next_step: {next_step_state}") # 調試用
        if next_step_state == "select_game_mode":
            pygame.display.set_mode((500, 500)) # 設定為標準選單螢幕大小
            pygame.display.set_caption("Pong Soul - Select Mode")
            current_game_mode_value = select_game_mode() # 假設此函數仍是舊式全螢幕阻塞
            if current_game_mode_value is None: # 通常表示用戶在選單中退出或按了ESC
                break # 結束主迴圈
            p1_skill_code = None # 重置技能選擇
            p2_skill_code = None
            next_step_state = "select_input"

        elif next_step_state == "select_input":
            pygame.display.set_mode((500, 500))
            pygame.display.set_caption("Pong Soul - Select Controller")
            current_input_mode = select_input_method() # 舊式全螢幕阻塞
            if current_input_mode is None:
                next_step_state = "select_game_mode" # 返回模式選擇
                continue
            
            if current_game_mode_value == GameSettings.GameMode.PLAYER_VS_AI:
                next_step_state = "select_skill_pva"
            elif current_game_mode_value == GameSettings.GameMode.PLAYER_VS_PLAYER:
                pygame.display.set_mode((1000, 600)) # 為PVP技能選擇設定較寬螢幕
                pygame.display.set_caption("Pong Soul - PVP Skill Selection")
                p1_skill_code, p2_skill_code = run_pvp_selection_phase(main_screen, sound_manager_instance)
                if p1_skill_code is None or p2_skill_code is None: # 有玩家取消
                    next_step_state = "select_input" # 返回輸入選擇 (或模式選擇)
                    continue
                # 雙方選完技能，直接進入遊戲會話
                next_step_state = game_session(current_input_mode, p1_skill_code, p2_skill_code, current_game_mode_value)
            else: # 未知遊戲模式
                print(f"Unknown game mode: {current_game_mode_value}, returning to mode select.")
                next_step_state = "select_game_mode"


        elif next_step_state == "select_skill_pva":
            pygame.display.set_mode((500, 500))
            pygame.display.set_caption("Pong Soul - Select Skill (PVA)")
            # 使用改造後的 select_skill，但讓它在整個螢幕區域渲染
            pva_render_area = main_screen.get_rect()
            p1_skill_code = select_skill(
                main_screen_surface=main_screen,
                render_area=pva_render_area,
                key_map=DEFAULT_MENU_KEYS, # PVA 時 P1 用標準按鍵選單
                sound_manager=sound_manager_instance,
                player_identifier="Player"
            )
            if p1_skill_code is None:
                next_step_state = "select_input" # 返回輸入選擇
                continue
            # PVA 模式，p2_skill_code 為 None
            # PVA 模式在 game_session 內部處理關卡選擇
            next_step_state = game_session(current_input_mode, p1_skill_code, None, current_game_mode_value)
        
        elif next_step_state == "quit": # 如果 game_session 或其他地方返回 "quit"
            break
        
        else: # 如果 next_step_state 是由 game_session 返回的 (例如 "select_game_mode")
            if next_step_state not in ["select_game_mode", "select_input", "select_skill_pva"]:
                print(f"Warning: Unhandled next_step_state '{next_step_state}', defaulting to 'select_game_mode'.")
                next_step_state = "select_game_mode"


if __name__ == '__main__':
    main_loop()
    pygame.quit()
    sys.exit()