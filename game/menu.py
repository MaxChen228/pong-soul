# pong-soul/game/menu.py
import pygame
import os
import sys

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from game.level import LevelManager
from game.theme import Style
from game.settings import GameSettings
import pygame.mixer
from utils import resource_path
from game.sound import SoundManager # 確保 SoundManager 已引入

def show_level_selection():
    pygame.init()
    screen = pygame.display.set_mode((500, 500))
    pygame.display.set_caption("Select Level")

    font_title = Style.get_font(Style.TITLE_FONT_SIZE)
    font_subtitle = Style.get_font(Style.SUBTITLE_FONT_SIZE)
    font_item = Style.get_font(Style.ITEM_FONT_SIZE)

    clock = pygame.time.Clock()
    sound_manager = SoundManager() # 建立 SoundManager 實例以播放音效

    levels = LevelManager(models_folder=resource_path("models"))
    level_names = [os.path.basename(f).replace(".pth", "") for f in levels.model_files]
    selected = 0

    # ⭐ 播放 menu 專屬背景音樂 ⭐
    # 注意：背景音樂通常在 select_input_method 中已啟動，此處不再重複啟動，
    # 除非你有特別設計讓每個選單獨立控制背景音樂。
    # 為保持一致性，假設背景音樂已由上層選單或主程式啟動。

    while True:
        screen.fill(Style.BACKGROUND_COLOR)

        title_surf = font_title.render("Select Level", True, Style.TEXT_COLOR)
        screen.blit(title_surf, Style.TITLE_POS)

        subtitle_surf = font_subtitle.render("(UP/DOWN, ENTER to start)", True, Style.TEXT_COLOR)
        screen.blit(subtitle_surf, Style.SUBTITLE_POS)

        for i, name in enumerate(level_names):
            color = Style.TEXT_COLOR
            if i == selected:
                color = Style.PLAYER_COLOR
            item_text = font_item.render(f"{i+1}. {name}", True, color)
            x, y = Style.ITEM_START_POS
            screen.blit(item_text, (x, y + i * Style.ITEM_LINE_SPACING))

        back_text = font_item.render("<< Back (ESC)", True, Style.TEXT_COLOR)
        back_rect = back_text.get_rect()
        screen.blit(back_text, (20, 500 - back_rect.height - 20))

        pygame.display.flip()
        clock.tick(30)

        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                pygame.quit()
                sys.exit()
            elif event.type == pygame.KEYDOWN:
                if event.key == pygame.K_DOWN:
                    selected = (selected + 1) % len(level_names)
                    sound_manager.play_click() # <--- 加入音效
                elif event.key == pygame.K_UP:
                    selected = (selected - 1 + len(level_names)) % len(level_names) # 確保正數
                    sound_manager.play_click() # <--- 加入音效
                elif event.key == pygame.K_RETURN:
                    sound_manager.play_click() # <--- 加入音效
                    # pygame.mixer.music.stop() # 遊戲開始前通常會停止選單音樂，由 main.py 控制
                    # pygame.quit() # pygame.quit() 會終止整個 Pygame，不應在此處單獨呼叫
                    return selected # 只返回選擇的索引
                elif event.key == pygame.K_ESCAPE:
                    sound_manager.play_click() # <--- 加入音效
                    # pygame.mixer.music.stop() # 同上
                    # pygame.quit() # 同上
                    return None  # 返回上層


def select_input_method():
    pygame.init()
    screen = pygame.display.set_mode((500, 500))
    pygame.display.set_caption("Select Controller") # 修正錯字 Controller

    font_title = Style.get_font(Style.TITLE_FONT_SIZE)
    font_subtitle = Style.get_font(Style.SUBTITLE_FONT_SIZE)
    font_item = Style.get_font(Style.ITEM_FONT_SIZE)

    options = ["Keyboard", "Mouse"]
    selected = 0
    clock = pygame.time.Clock()
    sound_manager = SoundManager() # 建立 SoundManager 實例

    # ⭐ 播放 menu 專屬背景音樂 ⭐
    # pygame.mixer.init() # 最好在主程式開頭統一初始化一次
    # pygame.mixer.music.load(resource_path("assets/menu_music.mp3"))
    # pygame.mixer.music.set_volume(GameSettings.BACKGROUND_MUSIC_VOLUME)
    # pygame.mixer.music.play(-1)
    # 假設背景音樂已由 main.py 或更早的流程啟動和管理，這裡專注於點擊音效。
    # 如果這是遊戲第一個選單，可以在此處啟動背景音樂。

    while True:
        screen.fill(Style.BACKGROUND_COLOR)

        title_surf = font_title.render("Select Controller", True, Style.TEXT_COLOR) # 修正錯字
        screen.blit(title_surf, Style.TITLE_POS)

        subtitle_surf = font_subtitle.render("(UP/DOWN, ENTER to confirm)", True, Style.TEXT_COLOR)
        screen.blit(subtitle_surf, Style.SUBTITLE_POS)

        for i, option in enumerate(options):
            color = Style.PLAYER_COLOR if i == selected else Style.TEXT_COLOR
            text = font_item.render(option, True, color)
            x, y = Style.ITEM_START_POS
            screen.blit(text, (x, y + i * Style.ITEM_LINE_SPACING))

        pygame.display.flip()
        clock.tick(30)

        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                pygame.quit()
                sys.exit()
            elif event.type == pygame.KEYDOWN:
                if event.key == pygame.K_DOWN:
                    selected = (selected + 1) % len(options)
                    sound_manager.play_click() # <--- 加入音效
                elif event.key == pygame.K_UP:
                    selected = (selected - 1 + len(options)) % len(options) # 確保正數
                    sound_manager.play_click() # <--- 加入音效
                elif event.key == pygame.K_RETURN:
                    sound_manager.play_click() # <--- 加入音效
                    return options[selected].lower()
                # 此選單通常沒有 ESC 返回上層的選項，因為它是第一個主要選項


def select_skill():
    pygame.init() # 雖然 main.py 已初始化，但保留以確保獨立性
    screen = pygame.display.set_mode((500, 500))
    pygame.display.set_caption("Select Skill")

    font_title = Style.get_font(Style.TITLE_FONT_SIZE)
    font_subtitle = Style.get_font(Style.SUBTITLE_FONT_SIZE)
    font_item = Style.get_font(Style.ITEM_FONT_SIZE)

    # 技能選項 (程式碼名稱)
    skills_code_names = ["slowmo", "long_paddle", "soul_eater_bug"] # <--- 加入 "soul_eater_bug"
    selected = 0
    clock = pygame.time.Clock()
    sound_manager = SoundManager() # <--- 建立 SoundManager 實例

    while True:
        screen.fill(Style.BACKGROUND_COLOR)

        title_surf = font_title.render("Select Skill", True, Style.TEXT_COLOR)
        screen.blit(title_surf, Style.TITLE_POS)

        subtitle_surf = font_subtitle.render("(UP/DOWN, ENTER to confirm)", True, Style.TEXT_COLOR)
        screen.blit(subtitle_surf, Style.SUBTITLE_POS)

        for i, skill_code in enumerate(skills_code_names):
            color = Style.PLAYER_COLOR if i == selected else Style.TEXT_COLOR

            # 技能顯示名稱轉換
            display_name = ""
            if skill_code == "slowmo":
                display_name = "Slow Motion"
            elif skill_code == "long_paddle":
                display_name = "Long Paddle"
            elif skill_code == "soul_eater_bug":
                display_name = "Soul Eater Bug" # <--- 為新技能設定顯示名稱 (蝕魂蟲)
            else:
                display_name = skill_code.replace("_", " ").title() # 預設顯示方式

            item_text = font_item.render(display_name, True, color)
            x, y = Style.ITEM_START_POS
            screen.blit(item_text, (x, y + i * Style.ITEM_LINE_SPACING))

        # (可選) 加入返回提示
        back_text = font_item.render("<< Back (ESC)", True, Style.TEXT_COLOR)
        back_rect = back_text.get_rect()
        screen.blit(back_text, (20, 500 - back_rect.height - 20))

        pygame.display.flip()
        clock.tick(30)

        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                pygame.quit()
                sys.exit()
            elif event.type == pygame.KEYDOWN:
                if event.key == pygame.K_DOWN:
                    selected = (selected + 1) % len(skills_code_names)
                    sound_manager.play_click() # <--- 加入音效
                elif event.key == pygame.K_UP:
                    selected = (selected - 1 + len(skills_code_names)) % len(skills_code_names) # 確保正數
                    sound_manager.play_click() # <--- 加入音效
                elif event.key == pygame.K_RETURN:
                    sound_manager.play_click() # <--- 加入音效
                    return skills_code_names[selected] # 返回選擇的技能程式碼名稱
                elif event.key == pygame.K_ESCAPE:
                    sound_manager.play_click() # <--- 加入音效
                    return None  # 允許返回上一層 (通常是輸入方式選擇)