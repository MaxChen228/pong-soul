import pygame
import sys
import time
import os
import torch
import numpy as np

# 初始化 pygame 和字型
pygame.init()
pygame.font.init()

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from envs.pong_duel_env import PongDuelEnv
from game.ai_agent import AIAgent
from game.level import LevelManager
from game.menu import show_level_selection
from game.theme import Style

# 倒數動畫顯示
def show_countdown(screen):
    font = Style.get_font(72)
    for n in ["3", "2", "1", "START"]:
        screen.fill(Style.BACKGROUND_COLOR)
        text = font.render(n, True, Style.TEXT_COLOR)
        rect = text.get_rect(center=(screen.get_width() // 2, screen.get_height() // 2))
        screen.blit(text, rect)
        pygame.display.flip()
        pygame.time.delay(700)

# 結果畫面顯示
def show_result_banner(screen, text, color):
    font = Style.get_font(40)
    screen.fill(Style.BACKGROUND_COLOR)
    banner = font.render(text, True, color)
    rect = banner.get_rect(center=(screen.get_width() // 2, screen.get_height() // 2))
    screen.blit(banner, rect)
    pygame.display.flip()
    pygame.time.delay(1500)


def main():
    # 顯示選關卡選單
    selected_index = show_level_selection()

    # 載入選定的關卡模型與設定
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

    # 建立畫面（要先 render 才有 window 給字型用）
    obs, _ = env.reset()
    env.render()               # 👈 建立 window
    show_countdown(env.window)

    done = False
    while True:
        env.render()
        time.sleep(0.016)

        # 玩家控制
        keys = pygame.key.get_pressed()
        player_action = 1
        if keys[pygame.K_LEFT]:
            player_action = 0
        elif keys[pygame.K_RIGHT]:
            player_action = 2

        # AI 控制
        ai_obs = obs.copy()
        ai_obs[4], ai_obs[5] = ai_obs[5], ai_obs[4]
        ai_action = ai.select_action(ai_obs)

        # 執行一輪
        obs, reward, done, _, _ = env.step(player_action, ai_action)

        # 處理視窗關閉
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                env.close()
                sys.exit()

        if done:
            player_life, ai_life = env.get_lives()

            if reward > 0:
                print("🎯 AI missed!")
            elif reward < 0:
                print("😵 You missed!")

            if player_life <= 0:
                show_result_banner(env.window, "YOU LOSE", Style.AI_COLOR)
                break

            elif ai_life <= 0:
                show_result_banner(env.window, "YOU WIN", Style.PLAYER_COLOR)
                break

            time.sleep(1)
            obs, _ = env.reset()
            done = False

    env.close()

# 主迴圈：結束後回到選單
if __name__ == '__main__':
    while True:
        main()
