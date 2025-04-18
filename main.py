# main.py（改良後）

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

# 倒數動畫（開始前 3,2,1）
def show_countdown(env):
    font = Style.get_font(60)
    screen = env.window
    for i in range(3, 0, -1):
        env.sound_manager.play_countdown()  # 播放倒數音效

        screen.fill(Style.BACKGROUND_COLOR)
        countdown_surface = font.render(str(i), True, Style.TEXT_COLOR)
        countdown_rect = countdown_surface.get_rect(center=(env.render_size // 2, env.render_size // 2))
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
input_mode = None

def main():
    global input_mode

    # 先選擇控制方式
    if input_mode is None:
        input_mode = select_input_method()
        if input_mode is not None:
            temp_env = PongDuelEnv(render_size=400)
            temp_env.sound_manager.play_click()
            temp_env.close()
        if input_mode is None:
            return
        
    # 取得玩家選擇的技能
    selected_skill = select_skill()
    if selected_skill is None:
        input_mode = None
        return

    # === ❶ 不再寫入 GameSettings.ACTIVE_SKILL ===
    # GameSettings.ACTIVE_SKILL = selected_skill  # 這行刪掉

    # 選擇關卡
    selected_index = show_level_selection()
    if selected_index is None:
        input_mode = None
        return

    # === ❷ 在此直接傳入環境的建構子 ===
    env = PongDuelEnv(render_size=400, active_skill_name=selected_skill)
    # ↑ 這樣 PongDuelEnv 就知道你選了什麼技能，而不必依賴 GameSettings

    # 確定選項後播放點擊音效
    env.sound_manager.play_click()

    # 載入關卡設定與 AI 模型
    levels = LevelManager()
    levels.current_level = selected_index
    model_path = levels.get_current_model_path()
    config = levels.get_current_config()

    if model_path is None:
        print("❌ No model found.")
        return

    env.set_params_from_config(config)
    ai = AIAgent(model_path)

    obs, _ = env.reset()
    env.render()

    # 背景音樂（使用關卡指定的 bg_music）
    pygame.mixer.music.load(f"assets/{env.bg_music}")
    pygame.mixer.music.set_volume(GameSettings.BACKGROUND_MUSIC_VOLUME)
    pygame.mixer.music.play(-1)

    # 倒數計時
    show_countdown(env)

    done = False
    while True:
        env.render()
        time.sleep(0.016)

        # 處理輸入
        player_action = 1
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

        # 讓 AI 做動作
        ai_obs = obs.copy()
        ai_obs[4], ai_obs[5] = ai_obs[5], ai_obs[4]
        ai_action = ai.select_action(ai_obs)

        obs, reward, done, _, _ = env.step(player_action, ai_action)

        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                env.close()
                sys.exit()

        if done:
            player_life, ai_life = env.get_lives()
            freeze_start = pygame.time.get_ticks()
            while pygame.time.get_ticks() - freeze_start < env.freeze_duration:
                env.render()
                pygame.time.delay(16)

            if player_life <= 0:
                show_result_banner(env.window, "YOU LOSE", Style.AI_COLOR)
                break
            elif ai_life <= 0:
                show_result_banner(env.window, "YOU WIN", Style.PLAYER_COLOR)
                break

            pygame.time.delay(500)
            obs, _ = env.reset()
            done = False

    env.close()


if __name__ == '__main__':
    while True:
        main()
