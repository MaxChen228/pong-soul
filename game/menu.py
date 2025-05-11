import pygame
import os
import sys

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from game.level import LevelManager
from game.theme import Style  # 新增 if not already
from game.settings import GameSettings
import pygame.mixer
from utils import resource_path # 現在它可以找到咒語了！
from game.sound import SoundManager # <--- 新增這一行

def show_level_selection():
    pygame.init()
    screen = pygame.display.set_mode((500, 500))
    pygame.display.set_caption("Select Level")

    # 三種字體
    font_title = Style.get_font(Style.TITLE_FONT_SIZE)
    font_subtitle = Style.get_font(Style.SUBTITLE_FONT_SIZE)
    font_item = Style.get_font(Style.ITEM_FONT_SIZE)

    clock = pygame.time.Clock()

     # ⭐ 播放 menu 專屬背景音樂 ⭐ 新增這裡

     # pygame.mixer.music.set_volume(GameSettings.BACKGROUND_MUSIC_VOLUME)

    levels = LevelManager(models_folder=resource_path("models"))
    level_names = [os.path.basename(f).replace(".pth", "") for f in levels.model_files]
    selected = 0

    while True:
        screen.fill(Style.BACKGROUND_COLOR)

        # 主標題
        title_surf = font_title.render("Select Level", True, Style.TEXT_COLOR)
        screen.blit(title_surf, Style.TITLE_POS)

        # 副標題
        subtitle_surf = font_subtitle.render("(UP/DOWN, ENTER to start)", True, Style.TEXT_COLOR)
        screen.blit(subtitle_surf, Style.SUBTITLE_POS)

        # 關卡選項
        for i, name in enumerate(level_names):
            color = Style.TEXT_COLOR
            if i == selected:
                color = Style.PLAYER_COLOR
            item_text = font_item.render(f"{i+1}. {name}", True, color)

            x, y = Style.ITEM_START_POS
            screen.blit(item_text, (x, y + i * Style.ITEM_LINE_SPACING))
        # 畫左下角 BACK 提示
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
                elif event.key == pygame.K_UP:
                    selected = (selected - 1) % len(level_names)
                elif event.key == pygame.K_RETURN:
                    pygame.mixer.music.stop()  # ⭐ 停止音樂（新增）
                    pygame.quit()
                    return selected
                elif event.key == pygame.K_ESCAPE:
                    pygame.mixer.music.stop()  # ⭐ 停止音樂（新增）
                    pygame.quit()
                    return None  # 回上層



                
def select_input_method():
    pygame.init()
    screen = pygame.display.set_mode((500, 500))
    pygame.display.set_caption("Select Controler")

    font_title = Style.get_font(Style.TITLE_FONT_SIZE)
    font_subtitle = Style.get_font(Style.SUBTITLE_FONT_SIZE)
    font_item = Style.get_font(Style.ITEM_FONT_SIZE)

    options = ["Keyboard", "Mouse"]
    selected = 0
    clock = pygame.time.Clock()

    # ⭐ 播放 menu 專屬背景音樂 ⭐ 新增這裡
    pygame.mixer.init()
    pygame.mixer.music.load(resource_path("assets/menu_music.mp3")) # 新的
    pygame.mixer.music.set_volume(GameSettings.BACKGROUND_MUSIC_VOLUME)
    pygame.mixer.music.play(-1)
    

    while True:
        screen.fill(Style.BACKGROUND_COLOR)

        # 標題
        title_surf = font_title.render("Select Controler", True, Style.TEXT_COLOR)
        screen.blit(title_surf, Style.TITLE_POS)

        # 可選：加一個副標題提示操作
        subtitle_surf = font_subtitle.render("(UP/DOWN, ENTER to confirm)", True, Style.TEXT_COLOR)
        screen.blit(subtitle_surf, Style.SUBTITLE_POS)

        # 選項
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
                elif event.key == pygame.K_UP:
                    selected = (selected - 1) % len(options)
                elif event.key == pygame.K_RETURN:
                    return options[selected].lower()

def select_skill():
    pygame.init()
    screen = pygame.display.set_mode((500, 500))
    pygame.display.set_caption("Select Skill")

    font_title = Style.get_font(Style.TITLE_FONT_SIZE)
    font_subtitle = Style.get_font(Style.SUBTITLE_FONT_SIZE)
    font_item = Style.get_font(Style.ITEM_FONT_SIZE)

    # 技能選項
    skills = ["slowmo", "long_paddle"]
    selected = 0
    clock = pygame.time.Clock()

    sound_manager = SoundManager()

    while True:
        screen.fill(Style.BACKGROUND_COLOR)

        # 主標題
        title_surf = font_title.render("Select Skill", True, Style.TEXT_COLOR)
        screen.blit(title_surf, Style.TITLE_POS)

        # 副標題
        subtitle_surf = font_subtitle.render("(UP/DOWN, ENTER to confirm)", True, Style.TEXT_COLOR)
        screen.blit(subtitle_surf, Style.SUBTITLE_POS)

        # 技能列表
        for i, skill in enumerate(skills):
            color = Style.PLAYER_COLOR if i == selected else Style.TEXT_COLOR
            skill_name = "Slow Motion" if skill == "slowmo" else "Long Paddle"
            item_text = font_item.render(skill_name, True, color)
            x, y = Style.ITEM_START_POS
            screen.blit(item_text, (x, y + i * Style.ITEM_LINE_SPACING))

        pygame.display.flip()
        clock.tick(30)

        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                pygame.quit()
                sys.exit()
            elif event.type == pygame.KEYDOWN:
                if event.key == pygame.K_DOWN:
                    selected = (selected + 1) % len(skills)
                    sound_manager.play_click() # <--- 新增：播放點擊音效
                elif event.key == pygame.K_UP:
                    selected = (selected - 1) % len(skills)
                    sound_manager.play_click() # <--- 新增：播放點擊音效
                elif event.key == pygame.K_RETURN:
                    sound_manager.play_click() # <--- 新增：播放點擊音效
                    return skills[selected]
                elif event.key == pygame.K_ESCAPE:
                    sound_manager.play_click() # <--- 新增：播放點擊音效
                    return None  # 允許返回上一層
