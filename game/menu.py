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

def select_skill(
    main_screen_surface, # 主螢幕 surface
    render_area,         # pygame.Rect，定義此選單的繪製區域
    key_map,             # 按鍵映射 for UP, DOWN, CONFIRM, CANCEL
    sound_manager,       # SoundManager 實例
    player_identifier="Player" # 用於標題，例如 "Player 1" 或 "Player 2"
    ):
    # pygame.init() # 不在此處初始化，由主程式負責
    # screen = pygame.display.set_mode((500, 500)) # 不再創建新螢幕

    font_title = Style.get_font(Style.TITLE_FONT_SIZE)
    font_subtitle = Style.get_font(Style.SUBTITLE_FONT_SIZE)
    font_item = Style.get_font(Style.ITEM_FONT_SIZE)

    skills_code_names = ["slowmo", "long_paddle", "soul_eater_bug"]
    selected = 0
    clock = pygame.time.Clock()
    # sound_manager = SoundManager() # 由外部傳入

    menu_title = f"{player_identifier} Select Skill"
    menu_subtitle = "(UP/DOWN, ENTER to confirm)" # 提示文字可能需要根據 key_map 動態生成，但暫時簡化

    running = True
    while running:
        # 繪製背景 (只在 render_area 內)
        # 注意：如果 render_area 不是從 (0,0) 開始，直接 fill 會填滿整個 surface 的顏色
        # 更安全的做法是繪製一個特定顏色的矩形到 render_area
        pygame.draw.rect(main_screen_surface, Style.BACKGROUND_COLOR, render_area)

        # 計算相對於 render_area 的繪製位置
        # Style.TITLE_POS 等是全域位置，需要轉換
        # 為了簡化，我們假設 Style 中的 POS 是相對於一個標準500x500選單區域的
        # 我們將其按比例縮放或直接使用，但繪製時加上 render_area.topleft
        
        # 標題和副標題的偏移，使其在 render_area 內部看起來合理
        # 這裡的偏移量可以根據 render_area 的大小動態調整，或使用固定值
        # 假設 Style.TITLE_POS 是 (40,30)，這對於一個小的 render_area 可能太大
        # 暫時使用固定的小偏移量
        title_offset_x = 20 
        title_offset_y = 20
        subtitle_offset_y_delta = 35 # 副標題在標題下方的距離
        item_start_offset_y_delta = 70 # 項目列表在副標題下方的距離
        item_start_offset_x = 40    # 項目列表的X偏移

        title_surf = font_title.render(menu_title, True, Style.TEXT_COLOR)
        main_screen_surface.blit(title_surf, (render_area.left + title_offset_x, render_area.top + title_offset_y))

        # 副標題的按鍵提示可以更通用，例如顯示 CONFIRM_KEY 的名稱
        # key_confirm_name = pygame.key.name(key_map['CONFIRM'])
        # menu_subtitle = f"(UP/DOWN, {key_confirm_name.upper()} to confirm)"
        subtitle_surf = font_subtitle.render(menu_subtitle, True, Style.TEXT_COLOR)
        main_screen_surface.blit(subtitle_surf, (render_area.left + title_offset_x, render_area.top + title_offset_y + subtitle_offset_y_delta))

        for i, skill_code in enumerate(skills_code_names):
            color = Style.PLAYER_COLOR if i == selected else Style.TEXT_COLOR
            display_name = skill_code.replace("_", " ").title()
            if skill_code == "soul_eater_bug": display_name = "Soul Eater Bug"

            item_text = font_item.render(display_name, True, color)
            # 計算項目位置
            item_x = render_area.left + item_start_offset_x
            item_y = render_area.top + title_offset_y + subtitle_offset_y_delta + item_start_offset_y_delta + i * Style.ITEM_LINE_SPACING
            main_screen_surface.blit(item_text, (item_x, item_y))

        # 返回提示 (ESC鍵)
        # key_cancel_name = pygame.key.name(key_map['CANCEL'])
        # back_text_str = f"<< Back ({key_cancel_name.upper()})"
        back_text_str = "<< Back (CANCEL_KEY)" # 簡化提示
        back_text_surf = font_item.render(back_text_str, True, Style.TEXT_COLOR)
        back_rect = back_text_surf.get_rect(bottomleft=(render_area.left + 20, render_area.bottom - 20))
        main_screen_surface.blit(back_text_surf, back_rect)

        pygame.display.flip() # ⭐ 注意：這裡 flip 了整個主螢幕。在PVP選單中，這應該在主迴圈完成兩邊繪製後進行。
                              # 為了讓此函數仍能獨立測試或用於單人模式，暫時保留。
                              # 在PVP選單主迴圈中，我們可能只調用繪製部分，然後統一flip。
                              # 但為了保持阻塞特性，這個 flip 是必須的。

        clock.tick(30)

        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                pygame.quit()
                sys.exit()
            elif event.type == pygame.KEYDOWN:
                if event.key == key_map['DOWN']:
                    selected = (selected + 1) % len(skills_code_names)
                    sound_manager.play_click()
                elif event.key == key_map['UP']:
                    selected = (selected - 1 + len(skills_code_names)) % len(skills_code_names)
                    sound_manager.play_click()
                elif event.key == key_map['CONFIRM']:
                    sound_manager.play_click()
                    return skills_code_names[selected] # 返回選擇的技能程式碼名稱
                elif event.key == key_map['CANCEL']:
                    sound_manager.play_click()
                    return None  # 允許返回 / 取消
def select_game_mode(): # ⭐ 新增此函數
    pygame.init() # 確保pygame已初始化
    screen = pygame.display.set_mode((500, 500))
    pygame.display.set_caption("Select Game Mode")

    font_title = Style.get_font(Style.TITLE_FONT_SIZE)
    font_subtitle = Style.get_font(Style.SUBTITLE_FONT_SIZE)
    font_item = Style.get_font(Style.ITEM_FONT_SIZE)

    options = [
        ("Player vs. AI", GameSettings.GameMode.PLAYER_VS_AI),
        ("Player vs. Player", GameSettings.GameMode.PLAYER_VS_PLAYER)
    ]
    display_options = [opt[0] for opt in options]
    selected = 0
    clock = pygame.time.Clock()
    sound_manager = SoundManager()

    # 假設背景音樂已由 main.py 或更早的流程啟動和管理
    # 如果這是遊戲第一個選單，可以在此處啟動背景音樂。

    while True:
        screen.fill(Style.BACKGROUND_COLOR)

        title_surf = font_title.render("Select Game Mode", True, Style.TEXT_COLOR)
        screen.blit(title_surf, Style.TITLE_POS)

        subtitle_surf = font_subtitle.render("(UP/DOWN, ENTER to confirm)", True, Style.TEXT_COLOR)
        screen.blit(subtitle_surf, Style.SUBTITLE_POS)

        for i, option_text in enumerate(display_options):
            color = Style.PLAYER_COLOR if i == selected else Style.TEXT_COLOR
            text_surf = font_item.render(option_text, True, color)
            x, y = Style.ITEM_START_POS
            screen.blit(text_surf, (x, y + i * Style.ITEM_LINE_SPACING))

        pygame.display.flip()
        clock.tick(30)

        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                pygame.quit()
                sys.exit()
            elif event.type == pygame.KEYDOWN:
                if event.key == pygame.K_DOWN:
                    selected = (selected + 1) % len(options)
                    sound_manager.play_click()
                elif event.key == pygame.K_UP:
                    selected = (selected - 1 + len(options)) % len(options)
                    sound_manager.play_click()
                elif event.key == pygame.K_RETURN:
                    sound_manager.play_click()
                    return options[selected][1] # 返回選擇的模式值 (e.g., "PVA" or "PVP")
                # 此選單暫不提供 ESC 返回，因為它通常是流程的早期步驟
                # 如果需要返回，可以像 select_skill 那樣返回 None