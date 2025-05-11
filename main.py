# main.py（修正版）

import pygame
import sys
import time
import os
import torch
import numpy as np

# 初始化 pygame 系統
pygame.init()
pygame.font.init()

# 載入模組
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from envs.pong_duel_env import PongDuelEnv
from game.ai_agent import AIAgent
from game.level import LevelManager
from game.theme import Style
from game.menu import show_level_selection, select_input_method, select_skill
from game.settings import GameSettings
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

def game_session(initial_input_mode, initial_skill):
    """管理一整局遊戲的邏輯，從選擇關卡到遊戲結束"""
    input_mode = initial_input_mode
    selected_skill = initial_skill

    # 選擇關卡
    selected_index = show_level_selection()
    if selected_index is None: # 如果在關卡選擇時按 ESC
        return "select_skill" # 返回到技能選擇標記

    env = PongDuelEnv(render_size=400, active_skill_name=selected_skill)
    
    levels = LevelManager(models_folder=resource_path("models"))
    levels.current_level = selected_index
    relative_model_path = levels.get_current_model_path()
    config = levels.get_current_config()

    if relative_model_path is None:
        print("❌ No model found.")
        env.close()
        return "select_skill" # 或者 "quit"

    env.set_params_from_config(config)

    absolute_model_path = resource_path(relative_model_path)
    if not os.path.exists(absolute_model_path):
         print(f"❌ Model file not found at: {absolute_model_path}")
         try: print(f"Searching in base path: {sys._MEIPASS}")
         except AttributeError: pass
         env.close()
         return "select_skill" # 或者 "quit"
    ai = AIAgent(absolute_model_path)

    obs, _ = env.reset()
    env.render()

    if hasattr(env, 'sound_manager') and env.sound_manager and hasattr(env, 'bg_music'):
        bg_music_relative_path = f"assets/{env.bg_music}"
        try:
            pygame.mixer.music.load(resource_path(bg_music_relative_path))
            pygame.mixer.music.set_volume(GameSettings.BACKGROUND_MUSIC_VOLUME)
            env.sound_manager.play_bg_music()
        except pygame.error as e:
            print(f"Error loading or playing background music {bg_music_relative_path}: {e}")
    else:
        print("Warning: SoundManager or bg_music not available in env for background music.")

    # ⭐ 第二個問題修正：開場倒數只在遊戲會話開始時執行一次 ⭐
    show_countdown(env)

    done = False
    game_running = True
    while game_running:
        env.render()
        
        if hasattr(env, 'renderer') and env.renderer and hasattr(env.renderer, 'clock'):
            env.renderer.clock.tick(60)
        else:
            time.sleep(0.016)

        player_action = 1
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
        
        ai_obs = obs.copy()
        if len(ai_obs) >= 6:
             ai_obs[4], ai_obs[5] = ai_obs[5], ai_obs[4]
        ai_action = ai.select_action(ai_obs)

        obs, reward, done, _, _ = env.step(player_action, ai_action)

        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                game_running = False
                env.close() # 確保關閉環境
                pygame.quit() # 退出pygame
                sys.exit() # 終止程式

        if done: # 僅表示回合結束 (有玩家失分)
            player_life, ai_life = env.get_lives()
            
            freeze_start = pygame.time.get_ticks()
            while pygame.time.get_ticks() - freeze_start < env.freeze_duration:
                env.render()
                pygame.event.pump()
                pygame.time.delay(16)

            if player_life <= 0: # 遊戲真正結束
                if hasattr(env, 'sound_manager') and env.sound_manager:
                    env.sound_manager.play_lose_sound()
                show_result_banner(env.window, "YOU LOSE", Style.AI_COLOR)
                game_running = False # 標記遊戲會話結束
            elif ai_life <= 0: # 遊戲真正結束
                if hasattr(env, 'sound_manager') and env.sound_manager:
                    env.sound_manager.play_win_sound()
                show_result_banner(env.window, "YOU WIN", Style.PLAYER_COLOR)
                game_running = False # 標記遊戲會話結束
            
            if not game_running: # 如果因為勝負已分而需要結束
                env.close() # 關閉當前遊戲環境
                return "select_skill" # ⭐ 第一個問題修正：返回到技能選擇菜單的信號 ⭐

            # 如果遊戲未因勝負結束，僅是回合重置
            pygame.time.delay(500)
            obs, _ = env.reset() # 重置球等回合狀態
            # ⭐ 第二個問題修正：移除這裡的 show_countdown ⭐
            done = False # 為下一回合準備

    # 如果 game_running 因為其他原因（例如非正常退出）變為 False
    env.close()
    return "select_skill" # 預設返回到技能選擇

def main_loop():
    """管理主要的應用程式流程，包括選單和遊戲會話之間的轉換"""
    current_input_mode = None
    current_skill = None
    
    while True:
        if current_input_mode is None:
            current_input_mode = select_input_method()
            if current_input_mode is None: # 用戶在選擇控制器時退出 (例如按視窗關閉)
                break # 結束主迴圈

        if current_skill is None or next_step == "select_skill": # 初始或從遊戲返回到技能選擇
            current_skill = select_skill()
            if current_skill is None: # 用戶在技能選擇時按 ESC
                current_input_mode = None # 重置，回到控制器選擇
                current_skill = None # 也重置技能
                next_step = "select_input" # 標記下次從頭開始
                continue # 回到 while True 開頭
        
        # 進入遊戲會話
        next_step = game_session(current_input_mode, current_skill)

        if next_step == "quit": # 如果 game_session 返回退出信號
            break
        elif next_step == "select_skill":
            # current_skill 會在下一次迴圈開始時重新選擇
            # input_mode 保持不變，直接進入技能選擇
            current_skill = None # 清空當前技能，以便下次重新選擇
            continue
        elif next_step == "select_input": #極端情況，例如從關卡選擇直接返回
            current_input_mode = None
            current_skill = None
            continue


if __name__ == '__main__':
    main_loop()
    pygame.quit()
    sys.exit()