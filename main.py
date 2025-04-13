# main.py（已整理 + 註解）

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
from game.menu import show_level_selection, select_input_method

# 倒數動畫（開始前 3,2,1）
def show_countdown(screen):
    font = Style.get_font(72)
    for n in ["3", "2", "1", "START"]:
        screen.fill(Style.BACKGROUND_COLOR)
        text = font.render(n, True, Style.TEXT_COLOR)
        rect = text.get_rect(center=(screen.get_width() // 2, screen.get_height() // 2))
        screen.blit(text, rect)
        pygame.display.flip()
        pygame.time.delay(700)

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
input_mode = None

def main():
    global input_mode

    # 選擇控制方式
    if input_mode is None:
        input_mode = select_input_method()
        if input_mode is None:
            return

    # 選擇關卡
    selected_index = show_level_selection()
    if selected_index is None:
        input_mode = None
        return

    # 載入關卡設定與 AI 模型
    levels = LevelManager()
    levels.current_level = selected_index
    model_path = levels.get_current_model_path()
    config = levels.get_current_config()

    if model_path is None:
        print("❌ No model found.")
        return

    env = PongDuelEnv(render_size=400)
    env.set_params_from_config(config)
    ai = AIAgent(model_path)

    # 初始化遊戲狀態
    obs, _ = env.reset()
    env.render()
    show_countdown(env.window)

    done = False
    while True:
        env.render()
        time.sleep(0.016)  # 60 FPS

        # 處理玩家控制輸入
        player_action = 1  # 預設保持不動
        if input_mode == "keyboard":
            keys = pygame.key.get_pressed()
            if keys[pygame.K_LEFT]:
                player_action = 0
            elif keys[pygame.K_RIGHT]:
                player_action = 2
        elif input_mode == "mouse":
            mouse_x = pygame.mouse.get_pos()[0] / env.render_size
            if mouse_x < env.player_x - 0.01:
                player_action = 0
            elif mouse_x > env.player_x + 0.01:
                player_action = 2

        # 取得 AI 控制
        ai_obs = obs.copy()
        ai_obs[4], ai_obs[5] = ai_obs[5], ai_obs[4]  # 對調玩家/AI 位置信息
        ai_action = ai.select_action(ai_obs)

        # 遊戲邏輯進行一回合
        obs, reward, done, _, _ = env.step(player_action, ai_action)

        # 處理視窗關閉
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                env.close()
                sys.exit()

        # 檢查是否結束遊戲
        if done:
            player_life, ai_life = env.get_lives()
            if reward > 0:
                print("🎯 AI missed!")
            elif reward < 0:
                print("😵 You missed!")

            freeze_start = pygame.time.get_ticks()
            while pygame.time.get_ticks() - freeze_start < env.freeze_duration:
                env.render()
                pygame.time.delay(16)  # 約60FPS的更新頻率

            if player_life <= 0:
                show_result_banner(env.window, "YOU LOSE", Style.AI_COLOR)
                break
            elif ai_life <= 0:
                show_result_banner(env.window, "YOU WIN", Style.PLAYER_COLOR)
                break

            # freeze效果後短暫暫停再重置
            pygame.time.delay(500)
            obs, _ = env.reset()
            done = False


    env.close()

# 遊戲主迴圈
if __name__ == '__main__':
    while True:
        main()
