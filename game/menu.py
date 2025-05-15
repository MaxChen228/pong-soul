# pong-soul/game/menu.py
import pygame
import os
import sys

from game.level import LevelManager
from game.theme import Style
from game.settings import GameSettings
from utils import resource_path
from game.sound import SoundManager

DEBUG_MENU = True
DEBUG_MENU_FULLSCREEN = True

# ⭐️ 修改 select_input_method
def select_input_method(main_screen_surface, sound_manager_instance, scale_factor, render_area_on_screen):
    if DEBUG_MENU_FULLSCREEN:
        print(f"[DEBUG_MENU_FULLSCREEN][select_input_method] Called. Scale: {scale_factor:.2f}, RenderArea: {render_area_on_screen}")

    scaled_title_font_size = int(Style.TITLE_FONT_SIZE * scale_factor)
    scaled_subtitle_font_size = int(Style.SUBTITLE_FONT_SIZE * scale_factor)
    scaled_item_font_size = int(Style.ITEM_FONT_SIZE * scale_factor)

    font_title = Style.get_font(scaled_title_font_size)
    font_subtitle = Style.get_font(scaled_subtitle_font_size)
    font_item = Style.get_font(scaled_item_font_size)

    options = ["Keyboard", "Mouse"]
    selected = 0
    clock = pygame.time.Clock()

    running = True
    while running:
        pygame.draw.rect(main_screen_surface, Style.BACKGROUND_COLOR, render_area_on_screen)

        title_x = render_area_on_screen.left + int(Style.TITLE_POS[0] * scale_factor)
        title_y = render_area_on_screen.top + int(Style.TITLE_POS[1] * scale_factor)
        subtitle_x = render_area_on_screen.left + int(Style.SUBTITLE_POS[0] * scale_factor)
        subtitle_y = render_area_on_screen.top + int(Style.SUBTITLE_POS[1] * scale_factor)
        item_start_x_base = int(Style.ITEM_START_POS[0] * scale_factor)
        item_start_y_base = int(Style.ITEM_START_POS[1] * scale_factor)
        scaled_line_spacing = int(Style.ITEM_LINE_SPACING * scale_factor)

        title_surf = font_title.render("Select Controller", True, Style.TEXT_COLOR)
        main_screen_surface.blit(title_surf, (title_x, title_y))

        subtitle_surf = font_subtitle.render("(UP/DOWN, ENTER to confirm, ESC to back)", True, Style.TEXT_COLOR)
        main_screen_surface.blit(subtitle_surf, (subtitle_x, subtitle_y))

        for i, option in enumerate(options):
            color = Style.PLAYER_COLOR if i == selected else Style.TEXT_COLOR
            text_surf = font_item.render(option, True, color)
            item_x = render_area_on_screen.left + item_start_x_base
            item_y = render_area_on_screen.top + item_start_y_base + i * scaled_line_spacing
            main_screen_surface.blit(text_surf, (item_x, item_y))

        pygame.display.flip()
        clock.tick(30)

        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                return None
            elif event.type == pygame.KEYDOWN:
                if event.key == pygame.K_DOWN:
                    selected = (selected + 1) % len(options)
                    sound_manager_instance.play_click()
                elif event.key == pygame.K_UP:
                    selected = (selected - 1 + len(options)) % len(options)
                    sound_manager_instance.play_click()
                elif event.key == pygame.K_RETURN:
                    sound_manager_instance.play_click()
                    return options[selected].lower()
                elif event.key == pygame.K_ESCAPE:
                    sound_manager_instance.play_click()
                    return "back_to_game_mode_select"
    return None # Just in case

# ⭐️ 修改 select_skill (注意它已經有 render_area 參數，現在再加 scale_factor)
def select_skill(
    main_screen_surface,
    render_area, # 這個 render_area 是由 main.py 計算好的，代表在螢幕上的實際繪圖區域
    key_map,
    sound_manager,
    player_identifier="Player",
    scale_factor=1.0 # ⭐️ 新增 scale_factor，預設為1以便向後兼容（如果直接調用）
    ):
    if DEBUG_MENU_FULLSCREEN:
        print(f"[DEBUG_MENU_FULLSCREEN][select_skill] Called for {player_identifier}. Scale: {scale_factor:.2f}, RenderArea: {render_area}")

    scaled_title_font_size = int(Style.TITLE_FONT_SIZE * scale_factor)
    scaled_subtitle_font_size = int(Style.SUBTITLE_FONT_SIZE * scale_factor)
    scaled_item_font_size = int(Style.ITEM_FONT_SIZE * scale_factor)

    font_title = Style.get_font(scaled_title_font_size)
    font_subtitle = Style.get_font(scaled_subtitle_font_size)
    font_item = Style.get_font(scaled_item_font_size)

    skills_code_names = ["slowmo", "long_paddle", "soul_eater_bug"]
    selected = 0
    clock = pygame.time.Clock()

    menu_title = f"{player_identifier} Select Skill"
    key_up_name = pygame.key.name(key_map['UP']).upper()
    key_down_name = pygame.key.name(key_map['DOWN']).upper()
    key_confirm_name = pygame.key.name(key_map['CONFIRM']).upper()
    key_cancel_name = pygame.key.name(key_map['CANCEL']).upper()
    menu_subtitle = f"({key_up_name}/{key_down_name}, {key_confirm_name})" # 簡化副標題
    back_text_str = f"<< Back ({key_cancel_name})"

    running = True
    while running:
        pygame.draw.rect(main_screen_surface, Style.BACKGROUND_COLOR, render_area)

        # 繪製位置基於 render_area.topleft，並且邏輯偏移經過縮放
        # 假設 Style 中的 POS 是小的邏輯偏移值
        title_x = render_area.left + int(20 * scale_factor) # 簡化偏移計算
        title_y = render_area.top + int(20 * scale_factor)

        scaled_title_font_height = font_title.get_height() # 獲取縮放後字體的高度
        scaled_subtitle_font_height = font_subtitle.get_height()
        
        subtitle_y = title_y + scaled_title_font_height + int(5 * scale_factor)
        
        item_start_y_base = subtitle_y + scaled_subtitle_font_height + int(20 * scale_factor)
        item_start_x_base = render_area.left + int(40 * scale_factor)
        scaled_line_spacing = int(Style.ITEM_LINE_SPACING * scale_factor)


        title_surf = font_title.render(menu_title, True, Style.TEXT_COLOR)
        main_screen_surface.blit(title_surf, (title_x, title_y))

        subtitle_surf = font_subtitle.render(menu_subtitle, True, Style.TEXT_COLOR)
        main_screen_surface.blit(subtitle_surf, (title_x, subtitle_y))

        for i, skill_code in enumerate(skills_code_names):
            color = Style.PLAYER_COLOR if i == selected else Style.TEXT_COLOR
            display_name = skill_code.replace("_", " ").title()
            if skill_code == "soul_eater_bug": display_name = "Soul Eater Bug"

            item_text_surf = font_item.render(display_name, True, color)
            item_y = item_start_y_base + i * scaled_line_spacing
            main_screen_surface.blit(item_text_surf, (item_start_x_base, item_y))

        back_text_surf = font_item.render(back_text_str, True, Style.TEXT_COLOR)
        back_rect = back_text_surf.get_rect(
            bottomleft=(render_area.left + int(20 * scale_factor),
                        render_area.bottom - int(20 * scale_factor))
        )
        main_screen_surface.blit(back_text_surf, back_rect)

        pygame.display.flip()
        clock.tick(30)

        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                return None
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
    return None # Just in case

# ⭐️ 修改 select_game_mode
def select_game_mode(main_screen_surface, sound_manager_instance, scale_factor, render_area_on_screen):
    if DEBUG_MENU_FULLSCREEN:
        print(f"[DEBUG_MENU_FULLSCREEN][select_game_mode] Called. Scale: {scale_factor:.2f}, RenderArea: {render_area_on_screen}")

    scaled_title_font_size = int(Style.TITLE_FONT_SIZE * scale_factor)
    scaled_subtitle_font_size = int(Style.SUBTITLE_FONT_SIZE * scale_factor)
    scaled_item_font_size = int(Style.ITEM_FONT_SIZE * scale_factor)

    font_title = Style.get_font(scaled_title_font_size)
    font_subtitle = Style.get_font(scaled_subtitle_font_size)
    font_item = Style.get_font(scaled_item_font_size)

    options = [
        ("Player vs. AI", GameSettings.GameMode.PLAYER_VS_AI),
        ("Player vs. Player", GameSettings.GameMode.PLAYER_VS_PLAYER),
        ("Quit Game", "quit_game_action")
    ]
    display_options = [opt[0] for opt in options]
    selected = 0
    clock = pygame.time.Clock()

    running = True
    while running:
        pygame.draw.rect(main_screen_surface, Style.BACKGROUND_COLOR, render_area_on_screen)

        title_x = render_area_on_screen.left + int(Style.TITLE_POS[0] * scale_factor)
        title_y = render_area_on_screen.top + int(Style.TITLE_POS[1] * scale_factor)
        subtitle_x = render_area_on_screen.left + int(Style.SUBTITLE_POS[0] * scale_factor)
        subtitle_y = render_area_on_screen.top + int(Style.SUBTITLE_POS[1] * scale_factor)
        item_start_x_base = int(Style.ITEM_START_POS[0] * scale_factor)
        item_start_y_base = int(Style.ITEM_START_POS[1] * scale_factor)
        scaled_line_spacing = int(Style.ITEM_LINE_SPACING * scale_factor)

        title_surf = font_title.render("Select Game Mode", True, Style.TEXT_COLOR)
        main_screen_surface.blit(title_surf, (title_x, title_y))

        subtitle_surf = font_subtitle.render("(UP/DOWN, ENTER to confirm)", True, Style.TEXT_COLOR)
        main_screen_surface.blit(subtitle_surf, (subtitle_x, subtitle_y))

        for i, option_text in enumerate(display_options):
            color = Style.PLAYER_COLOR if i == selected else Style.TEXT_COLOR
            text_surf = font_item.render(option_text, True, color)
            item_x = render_area_on_screen.left + item_start_x_base
            item_y = render_area_on_screen.top + item_start_y_base + i * scaled_line_spacing
            main_screen_surface.blit(text_surf, (item_x, item_y))

        pygame.display.flip()
        clock.tick(30)

        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                return None
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
                        return None
                    else:
                        return selected_action
    return None # Just in case