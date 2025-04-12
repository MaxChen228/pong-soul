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
            color = (255, 255, 255)
            if i == selected:
                color = Style.PLAYER_COLOR
            item_text = font_item.render(f"{i+1}. {name}", True, color)

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
                    selected = (selected + 1) % len(level_names)
                elif event.key == pygame.K_UP:
                    selected = (selected - 1) % len(level_names)
                elif event.key == pygame.K_RETURN:
                    pygame.quit()
                    return selected

