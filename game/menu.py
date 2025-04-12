import pygame
import os
import sys

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from game.level import LevelManager
from game.theme import Style  # 新增 if not already

def show_level_selection():
    pygame.init()
    screen = pygame.display.set_mode((500, 500))
    pygame.display.set_caption("Select Level")

    # 三種字體
    font_title = Style.get_font(Style.TITLE_FONT_SIZE)
    font_subtitle = Style.get_font(Style.SUBTITLE_FONT_SIZE)
    font_item = Style.get_font(Style.ITEM_FONT_SIZE)

    clock = pygame.time.Clock()

    levels = LevelManager()
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
                    pygame.quit()
                    return selected
                elif event.key == pygame.K_ESCAPE:
                    pygame.quit()
                    return None  # 回上層



                
def select_input_method():
    pygame.init()
    screen = pygame.display.set_mode((500, 500))  # 🆗 對齊關卡選單
    pygame.display.set_caption("Select Controler")

    font_title = Style.get_font(Style.TITLE_FONT_SIZE)
    font_subtitle = Style.get_font(Style.SUBTITLE_FONT_SIZE)
    font_item = Style.get_font(Style.ITEM_FONT_SIZE)

    options = ["Keyboard", "Mouse"]
    selected = 0
    clock = pygame.time.Clock()

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
                    pygame.quit()
                    return options[selected].lower()
