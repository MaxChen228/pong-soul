import pygame
import os
import sys

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from game.level import LevelManager

def show_level_selection():
    pygame.init()
    screen = pygame.display.set_mode((500, 500))
    pygame.display.set_caption("Select Level")

    # 使用系統安全字體，避免亂碼
    font = pygame.font.SysFont("arial", 20)
    clock = pygame.time.Clock()

    levels = LevelManager()
    level_names = [os.path.basename(f).replace(".pth", "") for f in levels.model_files]
    selected = 0

    while True:
        screen.fill((20, 20, 20))

        # 標題文字
        title = font.render("Select Level (UP/DOWN, ENTER to start)", True, (255, 255, 0))
        screen.blit(title, (40, 30))

        # 列出關卡
        for i, name in enumerate(level_names):
            color = (255, 255, 255)
            if i == selected:
                color = (0, 255, 0)
            text = font.render(f"{i+1}. {name}", True, color)
            screen.blit(text, (100, 100 + i * 40))

        pygame.display.flip()
        clock.tick(30)

        # 鍵盤輸入處理
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
