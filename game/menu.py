import pygame
import os
import sys

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from game.level import LevelManager
from game.theme import Style  # ✅ NEW

def show_level_selection():
    pygame.init()
    screen = pygame.display.set_mode((500, 500))
    pygame.display.set_caption("Select Level")

    font = Style.get_font(20)  # ✅ 使用 Style 字體
    clock = pygame.time.Clock()

    levels = LevelManager()
    level_names = [os.path.basename(f).replace(".pth", "") for f in levels.model_files]
    selected = 0

    while True:
        screen.fill(Style.BACKGROUND_COLOR)

        title = font.render("Select Level(UP/DOWN, ENTER to start)", True, Style.TEXT_COLOR)
        screen.blit(title, (40, 30))

        for i, name in enumerate(level_names):
            color = (255, 255, 255)
            if i == selected:
                color = Style.PLAYER_COLOR  # ✅ 高亮選項用 Style 顏色
            text = font.render(f"{i+1}. {name}", True, color)
            screen.blit(text, (100, 100 + i * 40))

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
