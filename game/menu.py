# pong-soul/game/menu.py
import pygame
import os
import sys

# 移除 sys.path.append，因為我們假設 main.py 已經處理了路徑
# sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from game.level import LevelManager # LevelManager 依然需要
from game.theme import Style
from game.settings import GameSettings
# import pygame.mixer # SoundManager 會處理 mixer
from utils import resource_path
from game.sound import SoundManager # 確保 SoundManager 已引入

DEBUG_MENU = True
DEBUG_MENU_FULLSCREEN = True # ⭐️ 新增排錯開關

# ⭐️ 修改 show_level_selection
def show_level_selection(main_screen_surface, sound_manager_instance): # 接收主表面和聲音管理器
    if DEBUG_MENU_FULLSCREEN:
        print(f"[DEBUG_MENU_FULLSCREEN][show_level_selection] Called. Drawing on surface: {type(main_screen_surface)}")

    # REMOVED: pygame.init()
    # REMOVED: screen = pygame.display.set_mode((500, 500))
    # REMOVED: pygame.display.set_caption("Select Level")

    font_title = Style.get_font(Style.TITLE_FONT_SIZE)
    font_subtitle = Style.get_font(Style.SUBTITLE_FONT_SIZE)
    font_item = Style.get_font(Style.ITEM_FONT_SIZE)

    clock = pygame.time.Clock()
    # REMOVED: sound_manager = SoundManager() # 使用傳入的 sound_manager_instance

    levels = LevelManager(models_folder=resource_path("models"))
    level_names = [os.path.basename(f).replace(".pth", "") for f in levels.model_files]
    if not level_names: # 如果沒有關卡文件
        if DEBUG_MENU: print("[DEBUG_MENU][show_level_selection] No level files found.")
        # 可以在螢幕上顯示提示信息
        error_font = Style.get_font(Style.ITEM_FONT_SIZE)
        error_surf = error_font.render("No levels found!", True, Style.TEXT_COLOR)
        error_rect = error_surf.get_rect(center=(main_screen_surface.get_width() // 2, main_screen_surface.get_height() // 2))
        
        # 繪製背景和錯誤訊息
        main_screen_surface.fill(Style.BACKGROUND_COLOR)
        main_screen_surface.blit(error_surf, error_rect)
        pygame.display.flip()
        pygame.time.wait(2000) # 短暫顯示錯誤後返回
        return None # 表示沒有選擇


    selected = 0
    running = True
    while running:
        # ⭐️ 繪圖目標是 main_screen_surface
        # ⭐️ 目前繪製位置是基於 Style 的絕對座標，會畫在 main_screen_surface 的左上角區域
        # ⭐️ 後續縮放階段，這裡的繪製需要考慮 render_area 和 scale_factor
        main_screen_surface.fill(Style.BACKGROUND_COLOR)

        title_surf = font_title.render("Select Level", True, Style.TEXT_COLOR)
        main_screen_surface.blit(title_surf, Style.TITLE_POS) # Style.TITLE_POS 是 (x,y)

        subtitle_surf = font_subtitle.render("(UP/DOWN, ENTER to start)", True, Style.TEXT_COLOR)
        main_screen_surface.blit(subtitle_surf, Style.SUBTITLE_POS)

        for i, name in enumerate(level_names):
            color = Style.TEXT_COLOR
            if i == selected:
                color = Style.PLAYER_COLOR
            item_text = font_item.render(f"{i+1}. {name}", True, color)
            x, y = Style.ITEM_START_POS # Style.ITEM_START_POS 是 (x,y)
            main_screen_surface.blit(item_text, (x, y + i * Style.ITEM_LINE_SPACING))

        back_text = font_item.render("<< Back (ESC)", True, Style.TEXT_COLOR)
        # ⭐️ back_rect 的位置需要考慮 main_screen_surface 的尺寸，或設定為相對 Style.POS
        # ⭐️ 暫時，如果 main_screen_surface 夠大，它會基於 (0,0) 和原始 500x500 的設計定位
        # ⭐️ 一個簡單的處理是假設其繪製在一個邏輯的 500x500 區域的左下角
        logical_menu_height = 500 # 假設的邏輯選單高度
        back_rect = back_text.get_rect(bottomleft=(20, logical_menu_height - 20))
        main_screen_surface.blit(back_text, back_rect)

        pygame.display.flip() # 暫時保留 flip
        clock.tick(30)

        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                if DEBUG_MENU_FULLSCREEN: print("[DEBUG_MENU_FULLSCREEN][show_level_selection] QUIT event. Returning None to main_loop for handling.")
                # REMOVED: pygame.quit()
                # REMOVED: sys.exit()
                return None # 返回 None，由 main_loop 決定是否退出
            elif event.type == pygame.KEYDOWN:
                if event.key == pygame.K_DOWN:
                    selected = (selected + 1) % len(level_names)
                    sound_manager_instance.play_click()
                elif event.key == pygame.K_UP:
                    selected = (selected - 1 + len(level_names)) % len(level_names)
                    sound_manager_instance.play_click()
                elif event.key == pygame.K_RETURN:
                    sound_manager_instance.play_click()
                    return selected # 只返回選擇的索引
                elif event.key == pygame.K_ESCAPE:
                    sound_manager_instance.play_click()
                    return None  # 返回 None 表示取消或返回上一層

# ⭐️ 修改 select_input_method
def select_input_method(main_screen_surface, sound_manager_instance): # 接收主表面和聲音管理器
    if DEBUG_MENU_FULLSCREEN:
        print(f"[DEBUG_MENU_FULLSCREEN][select_input_method] Called. Drawing on surface: {type(main_screen_surface)}")

    # REMOVED: pygame.init()
    # REMOVED: screen = pygame.display.set_mode((500, 500))
    # REMOVED: pygame.display.set_caption("Select Controller")

    font_title = Style.get_font(Style.TITLE_FONT_SIZE)
    font_subtitle = Style.get_font(Style.SUBTITLE_FONT_SIZE)
    font_item = Style.get_font(Style.ITEM_FONT_SIZE)

    options = ["Keyboard", "Mouse"]
    selected = 0
    clock = pygame.time.Clock()
    # REMOVED: sound_manager = SoundManager() # 使用傳入的 sound_manager_instance

    if DEBUG_MENU: print("[Menu] select_input_method started")

    running = True
    while running:
        main_screen_surface.fill(Style.BACKGROUND_COLOR)

        title_surf = font_title.render("Select Controller", True, Style.TEXT_COLOR)
        main_screen_surface.blit(title_surf, Style.TITLE_POS)

        subtitle_surf = font_subtitle.render("(UP/DOWN, ENTER to confirm, ESC to back)", True, Style.TEXT_COLOR)
        main_screen_surface.blit(subtitle_surf, Style.SUBTITLE_POS)

        for i, option in enumerate(options):
            color = Style.PLAYER_COLOR if i == selected else Style.TEXT_COLOR
            text = font_item.render(option, True, color)
            x, y = Style.ITEM_START_POS
            main_screen_surface.blit(text, (x, y + i * Style.ITEM_LINE_SPACING))

        pygame.display.flip() # 暫時保留 flip
        clock.tick(30)

        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                if DEBUG_MENU: print("[Menu][select_input_method] QUIT event. Returning None to main_loop.")
                # REMOVED: pygame.quit()
                # REMOVED: sys.exit()
                return None # 由 main_loop 處理退出
            elif event.type == pygame.KEYDOWN:
                if event.key == pygame.K_DOWN:
                    selected = (selected + 1) % len(options)
                    sound_manager_instance.play_click()
                elif event.key == pygame.K_UP:
                    selected = (selected - 1 + len(options)) % len(options)
                    sound_manager_instance.play_click()
                elif event.key == pygame.K_RETURN:
                    sound_manager_instance.play_click()
                    if DEBUG_MENU: print(f"[Menu][select_input_method] Selected '{options[selected].lower()}'. Returning.")
                    return options[selected].lower()
                elif event.key == pygame.K_ESCAPE:
                    sound_manager_instance.play_click()
                    if DEBUG_MENU: print("[Menu][select_input_method] ESC pressed. Returning 'back_to_game_mode_select'.")
                    return "back_to_game_mode_select"

    if DEBUG_MENU: print("[Menu][select_input_method] Loop exited unexpectedly. Returning None.")
    return None # 理論上不應執行到

# ⭐️ select_skill 函數的簽名已經符合要求，但要注意其 render_area 的使用
# ⭐️ 它會在其指定的 render_area (一個 Rect 物件) 內繪圖
def select_skill(
    main_screen_surface, # 主螢幕 surface
    render_area,         # pygame.Rect，定義此選單在 main_screen_surface 上的繪製區域
    key_map,             # 按鍵映射
    sound_manager,       # SoundManager 實例
    player_identifier="Player"
    ):
    if DEBUG_MENU_FULLSCREEN:
        print(f"[DEBUG_MENU_FULLSCREEN][select_skill] Called for {player_identifier}. Drawing on surface: {type(main_screen_surface)} within render_area: {render_area}")

    font_title = Style.get_font(Style.TITLE_FONT_SIZE)
    font_subtitle = Style.get_font(Style.SUBTITLE_FONT_SIZE)
    font_item = Style.get_font(Style.ITEM_FONT_SIZE)

    skills_code_names = ["slowmo", "long_paddle", "soul_eater_bug"]
    selected = 0
    clock = pygame.time.Clock()

    menu_title = f"{player_identifier} Select Skill"
    
    # 動態生成按鍵提示
    key_up_name = pygame.key.name(key_map['UP']).upper()
    key_down_name = pygame.key.name(key_map['DOWN']).upper()
    key_confirm_name = pygame.key.name(key_map['CONFIRM']).upper()
    key_cancel_name = pygame.key.name(key_map['CANCEL']).upper()
    menu_subtitle = f"({key_up_name}/{key_down_name}, {key_confirm_name} to confirm)"
    back_text_str = f"<< Back ({key_cancel_name})"


    running = True
    while running:
        # ⭐️ 在指定的 render_area 內繪製背景
        pygame.draw.rect(main_screen_surface, Style.BACKGROUND_COLOR, render_area)

        # 繪製位置基於 render_area.topleft
        # 這些 Style.POS 應該被視為相對於 render_area 左上角的偏移，或者需要重新設計
        # 暫時，我們假設 Style.POS 仍然是小的絕對值，我們將它們加到 render_area.left/top
        # 在縮放階段，這裡的 Style.POS 和字體大小都需要乘以 scale_factor
        
        # 為了使文字在 render_area 內合理定位，我們需要調整偏移
        # 例如，標題可以設定在 render_area 的頂部附近
        title_draw_x = render_area.left + 20 # 離 render_area 左邊界 20px
        title_draw_y = render_area.top + 20  # 離 render_area 上邊界 20px

        title_surf = font_title.render(menu_title, True, Style.TEXT_COLOR)
        main_screen_surface.blit(title_surf, (title_draw_x, title_draw_y))

        subtitle_surf = font_subtitle.render(menu_subtitle, True, Style.TEXT_COLOR)
        main_screen_surface.blit(subtitle_surf, (title_draw_x, title_draw_y + Style.TITLE_FONT_SIZE + 5)) # 標題下方一點

        item_start_y_offset = title_draw_y + Style.TITLE_FONT_SIZE + 5 + Style.SUBTITLE_FONT_SIZE + 20 # 副標題下方一點
        item_start_x_offset = render_area.left + 40 # 項目X偏移

        for i, skill_code in enumerate(skills_code_names):
            color = Style.PLAYER_COLOR if i == selected else Style.TEXT_COLOR
            display_name = skill_code.replace("_", " ").title()
            if skill_code == "soul_eater_bug": display_name = "Soul Eater Bug"

            item_text = font_item.render(display_name, True, color)
            item_y = item_start_y_offset + i * Style.ITEM_LINE_SPACING
            main_screen_surface.blit(item_text, (item_start_x_offset, item_y))

        back_text_surf = font_item.render(back_text_str, True, Style.TEXT_COLOR)
        # 返回按鈕放在 render_area 的左下角
        back_rect = back_text_surf.get_rect(bottomleft=(render_area.left + 20, render_area.bottom - 20))
        main_screen_surface.blit(back_text_surf, back_rect)

        pygame.display.flip() # 暫時保留 flip
        clock.tick(30)

        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                if DEBUG_MENU_FULLSCREEN: print(f"[DEBUG_MENU_FULLSCREEN][select_skill] QUIT event for {player_identifier}. Returning None.")
                # REMOVED: pygame.quit()
                # REMOVED: sys.exit()
                return None # 由 main_loop 處理
            elif event.type == pygame.KEYDOWN:
                if event.key == key_map['DOWN']:
                    selected = (selected + 1) % len(skills_code_names)
                    sound_manager.play_click()
                elif event.key == key_map['UP']:
                    selected = (selected - 1 + len(skills_code_names)) % len(skills_code_names)
                    sound_manager.play_click()
                elif event.key == key_map['CONFIRM']:
                    sound_manager.play_click()
                    return skills_code_names[selected]
                elif event.key == key_map['CANCEL']:
                    sound_manager.play_click()
                    return None

    if DEBUG_MENU_FULLSCREEN: print(f"[DEBUG_MENU_FULLSCREEN][select_skill] Loop for {player_identifier} exited unexpectedly. Returning None.")
    return None # 理論上不應執行到

# ⭐️ 修改 select_game_mode
def select_game_mode(main_screen_surface, sound_manager_instance): # 接收主表面和聲音管理器
    if DEBUG_MENU_FULLSCREEN:
        print(f"[DEBUG_MENU_FULLSCREEN][select_game_mode] Called. Drawing on surface: {type(main_screen_surface)}")

    # REMOVED: pygame.init()
    # REMOVED: screen = pygame.display.set_mode((500, 500))
    # REMOVED: pygame.display.set_caption("Select Game Mode")

    font_title = Style.get_font(Style.TITLE_FONT_SIZE)
    font_subtitle = Style.get_font(Style.SUBTITLE_FONT_SIZE)
    font_item = Style.get_font(Style.ITEM_FONT_SIZE)

    options = [
        ("Player vs. AI", GameSettings.GameMode.PLAYER_VS_AI),
        ("Player vs. Player", GameSettings.GameMode.PLAYER_VS_PLAYER),
        ("Quit Game", "quit_game_action") # ⭐️ 新增退出遊戲選項
    ]
    display_options = [opt[0] for opt in options]
    selected = 0
    clock = pygame.time.Clock()
    # REMOVED: sound_manager = SoundManager() # 使用傳入的 sound_manager_instance

    running = True
    while running:
        main_screen_surface.fill(Style.BACKGROUND_COLOR)

        title_surf = font_title.render("Select Game Mode", True, Style.TEXT_COLOR)
        main_screen_surface.blit(title_surf, Style.TITLE_POS)

        subtitle_surf = font_subtitle.render("(UP/DOWN, ENTER to confirm)", True, Style.TEXT_COLOR)
        main_screen_surface.blit(subtitle_surf, Style.SUBTITLE_POS)

        for i, option_text in enumerate(display_options):
            color = Style.PLAYER_COLOR if i == selected else Style.TEXT_COLOR
            text_surf = font_item.render(option_text, True, color)
            x, y = Style.ITEM_START_POS
            main_screen_surface.blit(text_surf, (x, y + i * Style.ITEM_LINE_SPACING))

        pygame.display.flip() # 暫時保留 flip
        clock.tick(30)

        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                if DEBUG_MENU_FULLSCREEN: print("[DEBUG_MENU_FULLSCREEN][select_game_mode] QUIT event. Returning None (interpreted as quit by main_loop).")
                # REMOVED: pygame.quit()
                # REMOVED: sys.exit()
                return None # 由 main_loop 處理退出
            elif event.type == pygame.KEYDOWN:
                if event.key == pygame.K_DOWN:
                    selected = (selected + 1) % len(options)
                    sound_manager_instance.play_click()
                elif event.key == pygame.K_UP:
                    selected = (selected - 1 + len(options)) % len(options)
                    sound_manager_instance.play_click()
                elif event.key == pygame.K_RETURN:
                    sound_manager_instance.play_click()
                    selected_action = options[selected][1]
                    if selected_action == "quit_game_action":
                        if DEBUG_MENU_FULLSCREEN: print("[DEBUG_MENU_FULLSCREEN][select_game_mode] 'Quit Game' selected. Returning None.")
                        return None # 返回 None，main_loop 會將其解釋为 "quit"
                    else:
                        return selected_action # 返回模式值 (e.g., "PVA" or "PVP")
                # ⭐️ 此主選單不設 ESC 返回，因為它是頂層選單之一。選擇 "Quit Game" 是退出方式。

    if DEBUG_MENU_FULLSCREEN: print("[DEBUG_MENU_FULLSCREEN][select_game_mode] Loop exited unexpectedly. Returning None.")
    return None # 理論上不應執行到