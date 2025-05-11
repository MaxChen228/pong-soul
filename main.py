# main.py
import pygame
import sys
import time
import os
import torch
import numpy as np

pygame.init()
pygame.font.init()

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from envs.pong_duel_env import PongDuelEnv
from game.ai_agent import AIAgent
from game.level import LevelManager
from game.theme import Style
# ⭐ 引入 select_game_mode
from game.menu import show_level_selection, select_input_method, select_skill, select_game_mode
from game.settings import GameSettings # ⭐ 引入 GameSettings
from utils import resource_path

# 倒數動畫（開始前 3,2,1）
def show_countdown(env):
    font = Style.get_font(60)
    screen = env.window
    for i in range(3, 0, -1):
        if hasattr(env, 'sound_manager') and env.sound_manager:
            env.sound_manager.play_countdown()
        else:
            print("Warning: sound_manager not found in env for countdown.")

        screen.fill(Style.BACKGROUND_COLOR)
        countdown_surface = font.render(str(i), True, Style.TEXT_COLOR)
        offset_y_val = env.renderer.offset_y if hasattr(env, 'renderer') and hasattr(env.renderer, 'offset_y') else 0
        countdown_rect = countdown_surface.get_rect(center=(env.render_size // 2, env.render_size // 2 + offset_y_val))
        screen.blit(countdown_surface, countdown_rect)
        pygame.display.flip()
        pygame.time.wait(1000)

# 顯示遊戲結果橫幅（YOU WIN / LOSE）
def show_result_banner(screen, text, color):
    font = Style.get_font(40)
    screen.fill(Style.BACKGROUND_COLOR)
    banner = font.render(text, True, color)
    rect = banner.get_rect(center=(screen.get_width() // 2, screen.get_height() // 2))
    screen.blit(banner, rect)
    pygame.display.flip()
    pygame.time.delay(1500)

# 全域控制輸入方式（Keyboard / Mouse）
# input_mode = None # 改為在 main_loop 中管理

def game_session(initial_input_mode, initial_skill, current_game_mode): # ⭐ 新增 current_game_mode 參數
    """管理一整局遊戲的邏輯，從選擇關卡到遊戲結束"""
    input_mode = initial_input_mode
    selected_skill = initial_skill

    # 關卡選擇邏輯調整：PVP模式可能跳過或有不同處理
    selected_index = 0 # 預設值
    config = {}
    relative_model_path = None # AI模型路徑
    levels = LevelManager(models_folder=resource_path("models"))

    if current_game_mode == GameSettings.GameMode.PLAYER_VS_AI:
        selected_index_result = show_level_selection()
        if selected_index_result is None:
            return "select_skill"
        selected_index = selected_index_result
        levels.current_level = selected_index
        relative_model_path = levels.get_current_model_path() # 只有PVA需要模型
        config = levels.get_current_config()
        if relative_model_path is None:
            print("❌ No model found for PVA mode.")
            # env is not created yet, so no env.close()
            return "select_skill"
    elif current_game_mode == GameSettings.GameMode.PLAYER_VS_PLAYER:
        print("PVP mode selected. Using default configuration or a specific PVP config if available.")
        # ⭐ PVP模式的配置：
        # 方案A: 使用第一個關卡的設定 (不含AI模型)
        levels.current_level = 0 # 或者一個指定的PVP關卡索引
        config = levels.get_current_config() # 獲取球速、場地等設定
        # 方案B: 或者載入一個PVP專用的config.yaml
        # config = load_pvp_config() # 假設有此函數
        if not config: # 如果沒有PVP設定，可以使用一個通用預設
            print("Warning: No specific PVP config found, using fallback.")
            config = { # 一些基本預設值
                'initial_speed': 0.025, 'enable_spin': True, 'magnus_factor': 0.01,
                'speed_increment': 0.002, 'speed_scale_every': 3,
                'player_life': 3, 'ai_life': 3, # 在PVP中 ai_life 會是 player2_life
                'player_paddle_width': 100, 'ai_paddle_width': 100, # PVP雙方球拍寬度
                'bg_music': "bg_music_level1.mp3" # 預設背景音樂
            }
            # 手動設定PVP的玩家生命 (此處ai_life會被視為P2的生命)
            config['player_max_life'] = config['player_life']
            config['ai_max_life'] = config['ai_life']


    # ⭐ 傳遞 game_mode 給 PongDuelEnv
    env = PongDuelEnv(render_size=400, active_skill_name=selected_skill, game_mode=current_game_mode)
    env.set_params_from_config(config) # 使用獲取的config設定環境

    # ⭐ AI Agent 的條件式載入
    ai = None
    if current_game_mode == GameSettings.GameMode.PLAYER_VS_AI:
        if relative_model_path: # 確保PVA模式有模型路徑
            absolute_model_path = resource_path(relative_model_path)
            if not os.path.exists(absolute_model_path):
                print(f"❌ Model file not found at: {absolute_model_path}")
                env.close()
                return "select_skill"
            ai = AIAgent(absolute_model_path)
            print(f"AI Agent loaded for PVA mode: {relative_model_path}")
        else:
            print("❌ Error: PVA mode selected but no model path available.")
            env.close()
            return "select_skill" # 或者 "quit"
    else: # PVP mode
        print("PVP mode: AI Agent will not be loaded.")


    obs, _ = env.reset()
    env.render() # 確保在倒數前至少渲染一次以建立env.window

    if hasattr(env, 'sound_manager') and env.sound_manager and hasattr(env, 'bg_music'):
        # ... (背景音樂播放邏輯不變) ...
        bg_music_relative_path = f"assets/{env.bg_music}"
        try:
            pygame.mixer.music.load(resource_path(bg_music_relative_path))
            pygame.mixer.music.set_volume(GameSettings.BACKGROUND_MUSIC_VOLUME)
            env.sound_manager.play_bg_music()
        except pygame.error as e:
            print(f"Error loading or playing background music {bg_music_relative_path}: {e}")

    show_countdown(env)

    done = False
    game_running = True
    while game_running:
        env.render()
        
        if hasattr(env, 'renderer') and env.renderer and hasattr(env.renderer, 'clock'):
            env.renderer.clock.tick(60)
        else:
            time.sleep(0.016)

        player_action = 1 # 玩家一的行動
        # ... (玩家一輸入捕捉邏輯不變) ...
        if input_mode == "keyboard":
            keys = pygame.key.get_pressed()
            if keys[pygame.K_LEFT]:
                player_action = 0
            elif keys[pygame.K_RIGHT]:
                player_action = 2
        elif input_mode == "mouse":
            mouse_x_abs, _ = pygame.mouse.get_pos()
            mouse_x_relative = mouse_x_abs / env.render_size
            threshold = 0.01
            if mouse_x_relative < env.player_x - threshold:
                player_action = 0
            elif mouse_x_relative > env.player_x + threshold:
                player_action = 2
        
        # ⭐ 動作決策：AI 或 玩家二
        action_for_top_paddle = 1 # 預設不動
        if current_game_mode == GameSettings.GameMode.PLAYER_VS_AI:
            if ai: # 確保ai物件存在
                ai_obs = obs.copy()
                if len(ai_obs) >= 6:
                    ai_obs[4], ai_obs[5] = ai_obs[5], ai_obs[4] # AI觀察的是對手在前的狀態
                action_for_top_paddle = ai.select_action(ai_obs)
            else: # AI不存在，這不應該發生在PVA模式，但作為保護
                print("Error: AI is None in PVA mode during step.")
                action_for_top_paddle = 1 # AI故障，不動
        else: # PVP 模式 (下一階段實現玩家二輸入)
            # 目前PVP模式下，上方球拍暫時不動或由簡單邏輯控制
            # print("PVP mode: Top paddle action pending P2 input implementation.")
            action_for_top_paddle = 1 # 暫時讓上方球拍不動

        obs, reward, done, _, _ = env.step(player_action, action_for_top_paddle)

        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                game_running = False
                env.close()
                pygame.quit()
                sys.exit()

        if done:
            player_life, ai_or_p2_life = env.get_lives() # ai_life 此時可能是 p2_life
            
            freeze_start = pygame.time.get_ticks()
            while pygame.time.get_ticks() - freeze_start < env.freeze_duration:
                env.render()
                pygame.event.pump()
                pygame.time.delay(16)

            game_over_message_p1_wins = "PLAYER 1 WINS!" if current_game_mode == GameSettings.GameMode.PLAYER_VS_PLAYER else "YOU WIN!"
            game_over_message_p1_loses = "PLAYER 2 WINS!" if current_game_mode == GameSettings.GameMode.PLAYER_VS_PLAYER else "YOU LOSE!"
            
            if player_life <= 0:
                if hasattr(env, 'sound_manager') and env.sound_manager:
                    env.sound_manager.play_lose_sound()
                show_result_banner(env.window, game_over_message_p1_loses, Style.AI_COLOR) # PVP時AI_COLOR可能代表P2
                game_running = False
            elif ai_or_p2_life <= 0:
                if hasattr(env, 'sound_manager') and env.sound_manager:
                    env.sound_manager.play_win_sound()
                show_result_banner(env.window, game_over_message_p1_wins, Style.PLAYER_COLOR)
                game_running = False
            
            if not game_running:
                env.close()
                # 返回到遊戲模式選擇，或技能選擇，取決於流程設計
                return "select_game_mode" # 或者 "select_skill"

            pygame.time.delay(500)
            obs, _ = env.reset()
            done = False

    env.close()
    return "select_game_mode" # 預設返回到遊戲模式選擇


def main_loop():
    """管理主要的應用程式流程，包括選單和遊戲會話之間的轉換"""
    current_input_mode = None
    current_skill = None
    current_game_mode = None # ⭐ 新增遊戲模式狀態
    
    next_step = "select_game_mode" # ⭐ 應用程式啟動時的第一步

    while True:
        if next_step == "select_game_mode":
            current_game_mode = select_game_mode()
            if current_game_mode is None: # 通常意味著退出
                break
            next_step = "select_input" # 選擇完模式後去選擇輸入方式

        elif next_step == "select_input":
            current_input_mode = select_input_method()
            if current_input_mode is None:
                next_step = "select_game_mode" # 返回上一層選單
                continue
            next_step = "select_skill"

        elif next_step == "select_skill":
            current_skill = select_skill()
            if current_skill is None:
                next_step = "select_input" # 返回上一層選單
                continue
            # 選擇完技能後，進入遊戲會話
            next_step = game_session(current_input_mode, current_skill, current_game_mode) # ⭐ 傳遞模式

        elif next_step == "quit":
            break
        
        # 如果 game_session 返回 "select_game_mode", "select_input", "select_skill"
        # 會在下一次迴圈開始時直接跳轉到對應的 if 分支

if __name__ == '__main__':
    main_loop()
    pygame.quit()
    sys.exit()