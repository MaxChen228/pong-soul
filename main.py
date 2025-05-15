# main.py (修正版 - 第二階段：選單居中縮放)

import pygame
import sys
import time
import os
import random

# 專案路徑設定 (如果您的 utils.py 等在根目錄下，這個可能不需要，
# 或者您的 IDE 會自動處理。如果 main.py 在子目錄，則可能需要)
# sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from envs.pong_duel_env import PongDuelEnv
from game.ai_agent import AIAgent
from game.level import LevelManager
from game.theme import Style
from game.menu import (
    show_level_selection,
    select_input_method,
    select_skill,
    select_game_mode
)
from game.settings import GameSettings
from game.sound import SoundManager
from utils import resource_path # 確保 utils.py 和 resource_path 能被正確找到

DEBUG_MAIN = False
DEBUG_MAIN_FULLSCREEN = True

# --- 倒數與結果顯示函數 ---
def show_countdown(env):
    if not env.renderer or not env.renderer.window:
        if DEBUG_MAIN: print("[show_countdown] Error: Renderer or window not initialized.")
        return

    screen_to_draw_on = env.renderer.window
    
    # ‼️ 字體大小的縮放將由 Renderer 或 game_session 傳遞的 scale_factor 控制
    # ‼️ 目前暫時使用固定大小，但在遊戲內容縮放時需要調整
    # ‼️ 或者，Style.get_font 本身就需要能處理縮放
    font_size = 60
    # 假設 env.renderer 有一個 scale_factor 屬性 (後續階段加入)
    # if hasattr(env.renderer, 'scale_factor_for_game_elements'):
    #     font_size = int(font_size * env.renderer.scale_factor_for_game_elements)
    # else: # Fallback if renderer scaling not yet implemented
    #     # We might need a global game_scale_factor accessible here
    #     pass

    font = Style.get_font(font_size)

    countdown_seconds_to_show = GameSettings.COUNTDOWN_SECONDS
    if hasattr(env, 'common_config') and 'countdown_seconds' in env.common_config:
        countdown_seconds_to_show = env.common_config['countdown_seconds']
    elif hasattr(env, 'countdown_seconds'):
        countdown_seconds_to_show = env.countdown_seconds

    for i in range(countdown_seconds_to_show, 0, -1):
        if hasattr(env, 'sound_manager') and env.sound_manager:
            env.sound_manager.play_countdown()

        # 倒計時應該繪製在遊戲的邏輯中心，然後由 Renderer 負責縮放和定位到螢幕
        # 目前，它直接在 screen_to_draw_on (可能是整個螢幕或 Renderer 的畫布) 上繪製
        # 如果 screen_to_draw_on 是 Renderer 的已縮放畫布，則 get_width/height 是縮放後的
        screen_to_draw_on.fill(Style.BACKGROUND_COLOR) # 清屏 (Renderer 的背景)
        countdown_surface = font.render(str(i), True, Style.TEXT_COLOR)
        
        # 這裡的 center 是相對於 screen_to_draw_on 的
        # 如果 screen_to_draw_on 是整個螢幕，而遊戲區域是居中的，這裡的定位需要調整
        # 理想情況：Renderer 提供一個方法來獲取遊戲區域的中心點
        center_x = screen_to_draw_on.get_width() // 2
        center_y = screen_to_draw_on.get_height() // 2
        # if hasattr(env.renderer, 'game_render_area_center_on_window'):
        #     center_x, center_y = env.renderer.game_render_area_center_on_window

        countdown_rect = countdown_surface.get_rect(center=(center_x, center_y))
        screen_to_draw_on.blit(countdown_surface, countdown_rect)
        
        pygame.display.flip() # 這個 flip 會刷新整個應用程式視窗
        pygame.time.wait(1000)

def show_result_banner(screen_to_draw_on, text, color): # screen 應為遊戲結束時的繪圖表面
    if not screen_to_draw_on:
        if DEBUG_MAIN: print(f"[show_result_banner] Error: Screen not available for text: {text}")
        return
    
    font_size = 40
    # Similar scaling logic as show_countdown for font if needed
    font = Style.get_font(font_size)

    screen_to_draw_on.fill(Style.BACKGROUND_COLOR)
    banner = font.render(text, True, color)
    
    center_x = screen_to_draw_on.get_width() // 2
    center_y = screen_to_draw_on.get_height() // 2
    # if hasattr(env.renderer, 'game_render_area_center_on_window'): # Assuming env is accessible or passed
    #     center_x, center_y = env.renderer.game_render_area_center_on_window

    rect = banner.get_rect(center=(center_x, center_y))
    screen_to_draw_on.blit(banner, rect)
    pygame.display.flip()
    pygame.time.delay(2000)

# --- 按鍵映射定義 ---
P1_MENU_KEYS = {
    'UP': pygame.K_w, 'DOWN': pygame.K_s, 'CONFIRM': pygame.K_e, 'CANCEL': pygame.K_q
}
DEFAULT_MENU_KEYS = {
    'UP': pygame.K_UP, 'DOWN': pygame.K_DOWN, 'CONFIRM': pygame.K_RETURN, 'CANCEL': pygame.K_ESCAPE
}
P2_GAME_KEYS = {
    'LEFT': pygame.K_j, 'RIGHT': pygame.K_l, 'SKILL': pygame.K_u
}
P1_GAME_KEYS = {
    'LEFT_KB': pygame.K_LEFT, 'RIGHT_KB': pygame.K_RIGHT, 'SKILL_KB': pygame.K_x,
}

# --- PVP 選單階段處理 ---
def run_pvp_selection_phase(main_screen_surface_param,
                            sound_manager_instance,
                            scale_factor,
                            render_area_on_screen
                           ):
    # (此函數的程式碼已在上一回答中提供並修改，此處省略以保持簡潔)
    # 確保其內部調用 select_skill 時，也傳遞了 scale_factor 和計算好的子 render_area
    # 繪圖都將在 render_area_on_screen 內部進行

    area_width = render_area_on_screen.width
    area_height = render_area_on_screen.height
    area_left = render_area_on_screen.left
    area_top = render_area_on_screen.top

    p1_skill_select_area = pygame.Rect(
        area_left, area_top,
        area_width // 2, area_height
    )
    p2_skill_select_area = pygame.Rect(
        area_left + area_width // 2, area_top,
        area_width // 2, area_height
    )
    divider_color = (100, 100, 100)
    scaled_divider_thickness = max(1, int(2 * scale_factor))
    player1_selected_skill = None
    player2_selected_skill = None

    pygame.draw.rect(main_screen_surface_param, Style.BACKGROUND_COLOR, render_area_on_screen)
    divider_x_abs = area_left + area_width // 2
    pygame.draw.line(main_screen_surface_param, divider_color,
                     (divider_x_abs, area_top),
                     (divider_x_abs, area_top + area_height),
                     scaled_divider_thickness)
    # pygame.display.flip() # 由 main_loop 控制 flip

    if DEBUG_MAIN: print("[run_pvp_selection_phase] Player 1 selecting skill...")
    player1_selected_skill = select_skill(
        main_screen_surface=main_screen_surface_param,
        render_area=p1_skill_select_area,
        key_map=P1_MENU_KEYS,
        sound_manager=sound_manager_instance,
        player_identifier="Player 1",
        scale_factor=scale_factor
    )
    if player1_selected_skill is None:
        if DEBUG_MAIN: print("[run_pvp_selection_phase] Player 1 cancelled.")
        return None, None

    pygame.draw.rect(main_screen_surface_param, Style.BACKGROUND_COLOR, p1_skill_select_area)
    scaled_item_font_size = int(Style.ITEM_FONT_SIZE * scale_factor)
    font_info = Style.get_font(scaled_item_font_size)
    p1_info_text_render = font_info.render(f"P1: {player1_selected_skill.replace('_',' ').title()}", True, Style.PLAYER_COLOR)
    p1_info_rect = p1_info_text_render.get_rect(center=p1_skill_select_area.center)
    main_screen_surface_param.blit(p1_info_text_render, p1_info_rect)
    pygame.draw.line(main_screen_surface_param, divider_color,
                     (divider_x_abs, area_top),
                     (divider_x_abs, area_top + area_height),
                     scaled_divider_thickness)
    # pygame.display.flip()

    if DEBUG_MAIN: print(f"[run_pvp_selection_phase] Player 1 selected: {player1_selected_skill}. Player 2 selecting...")
    player2_selected_skill = select_skill(
        main_screen_surface=main_screen_surface_param,
        render_area=p2_skill_select_area,
        key_map=DEFAULT_MENU_KEYS,
        sound_manager=sound_manager_instance,
        player_identifier="Player 2",
        scale_factor=scale_factor
    )
    if player2_selected_skill is None:
        if DEBUG_MAIN: print("[run_pvp_selection_phase] Player 2 cancelled.")
        return player1_selected_skill, None

    pygame.draw.rect(main_screen_surface_param, Style.BACKGROUND_COLOR, p2_skill_select_area)
    p2_info_text_render = font_info.render(f"P2: {player2_selected_skill.replace('_',' ').title()}", True, Style.AI_COLOR)
    p2_info_rect = p2_info_text_render.get_rect(center=p2_skill_select_area.center)
    main_screen_surface_param.blit(p2_info_text_render, p2_info_rect)
    # pygame.display.flip()

    if DEBUG_MAIN: print(f"[run_pvp_selection_phase] Player 2 selected: {player2_selected_skill}.")
    pygame.draw.rect(main_screen_surface_param, Style.BACKGROUND_COLOR, render_area_on_screen)
    scaled_title_font_size = int(Style.TITLE_FONT_SIZE * scale_factor)
    font_large = Style.get_font(scaled_title_font_size)
    ready_text_str = "Players Ready! Starting..."
    if not player1_selected_skill or not player2_selected_skill:
         ready_text_str = "Skill selection incomplete!"
    ready_text_render = font_large.render(ready_text_str, True, Style.TEXT_COLOR)
    ready_rect = ready_text_render.get_rect(center=render_area_on_screen.center)
    main_screen_surface_param.blit(ready_text_render, ready_rect)
    
    # 此處的 flip 是此函數的最後一次視覺更新，之後控制權交回 main_loop
    pygame.display.flip() 
    pygame.time.wait(2000)
    return player1_selected_skill, player2_selected_skill


# --- 遊戲會話管理 ---
def game_session(main_screen_surface_param, current_input_mode, p1_skill_code_from_menu, p2_skill_code_from_menu, current_game_mode_value):
    if DEBUG_MAIN_FULLSCREEN:
        print(f"[DEBUG_MAIN_FULLSCREEN][game_session] Called. Main screen surface: {type(main_screen_surface_param)}")

    levels = LevelManager(models_folder=resource_path("models"))
    common_game_config = {
        'mass': 1.0, 'e_ball_paddle': 1.0, 'mu_ball_paddle': 0.4, 'enable_spin': True, 'magnus_factor': 0.01,
        'speed_increment': 0.002, 'speed_scale_every': 3, 'initial_ball_speed': 0.025,
        'initial_angle_deg_range': [-45, 45],
        'freeze_duration_ms': GameSettings.FREEZE_DURATION_MS,
        'countdown_seconds': GameSettings.COUNTDOWN_SECONDS,
        'bg_music': "bg_music_level1.mp3"
    }
    render_size_for_env = 400 # 遊戲的邏輯渲染尺寸
    paddle_height_for_env = 10
    ball_radius_for_env = 10
    player1_env_config = {}
    opponent_env_config = {}
    ai_agent = None
    temp_sound_manager_for_menu = SoundManager() # 僅用於臨時傳遞給選單

    # 遊戲會話中的選單（如關卡選擇）也需要縮放和定位
    # 我們需要 game_session 知道標準選單的邏輯尺寸，以便計算傳遞給 show_level_selection 的 render_area
    # 這部分與 main_loop 中的選單縮放邏輯類似
    gs_logical_menu_width = 800  # 與 main_loop 中定義的選單邏輯尺寸一致
    gs_logical_menu_height = 600
    gs_actual_screen_width, gs_actual_screen_height = main_screen_surface_param.get_size()

    gs_scale_x = gs_actual_screen_width / gs_logical_menu_width
    gs_scale_y = gs_actual_screen_height / gs_logical_menu_height
    gs_menu_scale_factor = min(gs_scale_x, gs_scale_y)
    gs_scaled_menu_width = int(gs_logical_menu_width * gs_menu_scale_factor)
    gs_scaled_menu_height = int(gs_logical_menu_height * gs_menu_scale_factor)
    gs_menu_offset_x = (gs_actual_screen_width - gs_scaled_menu_width) // 2
    gs_menu_offset_y = (gs_actual_screen_height - gs_scaled_menu_height) // 2
    gs_level_select_render_area = pygame.Rect(gs_menu_offset_x, gs_menu_offset_y, gs_scaled_menu_width, gs_scaled_menu_height)


    if current_game_mode_value == GameSettings.GameMode.PLAYER_VS_AI:
        # 在調用 show_level_selection 前，填充主螢幕背景
        main_screen_surface_param.fill(Style.BACKGROUND_COLOR)
        selected_level_index = show_level_selection(
            main_screen_surface_param,
            temp_sound_manager_for_menu, # 傳遞 sound_manager
            gs_menu_scale_factor,        # 傳遞計算好的縮放因子
            gs_level_select_render_area  # 傳遞計算好的渲染區域
        )
        if selected_level_index is None: return "select_game_mode"
        
        levels.current_level = selected_level_index
        level_specific_config = levels.get_current_config()
        if not level_specific_config:
            level_specific_config = {
                'player_life': 3, 'ai_life': 3, 'player_paddle_width': 100, 'ai_paddle_width': 60,
                'initial_speed': 0.02, 'bg_music': "bg_music_level1.mp3", # 確保有bg_music
                'freeze_duration_ms': common_game_config['freeze_duration_ms']
            }
        # common_game_config['initial_ball_speed'] = level_specific_config.get('initial_speed', common_game_config['initial_ball_speed'])
        # common_game_config['bg_music'] = level_specific_config.get('bg_music', common_game_config['bg_music'])
        # common_game_config['freeze_duration_ms'] = level_specific_config.get('freeze_duration_ms', common_game_config['freeze_duration_ms'])
        common_game_config.update(level_specific_config) # 更簡潔地更新
        player1_env_config = {
            'initial_x': 0.5, 'initial_paddle_width': level_specific_config.get('player_paddle_width', 100),
            'initial_lives': level_specific_config.get('player_life', 3), 'skill_code': p1_skill_code_from_menu, 'is_ai': False
        }
        opponent_env_config = {
            'initial_x': 0.5, 'initial_paddle_width': level_specific_config.get('ai_paddle_width', 60),
            'initial_lives': level_specific_config.get('ai_life', 3), 'skill_code': None, 'is_ai': True
        }
        relative_model_path = levels.get_current_model_path()
        if relative_model_path:
            absolute_model_path = resource_path(relative_model_path)
            if os.path.exists(absolute_model_path): ai_agent = AIAgent(absolute_model_path)
            else: print(f"AI model not found at: {absolute_model_path}")

    elif current_game_mode_value == GameSettings.GameMode.PLAYER_VS_PLAYER:
        pvp_game_specific_config = {
            'player1_paddle_width': 100, 'player1_lives': 3,
            'player2_paddle_width': 100, 'player2_lives': 3,
            'bg_music': "bg_music_pvp.mp3",
            'freeze_duration_ms': common_game_config.get('freeze_duration_ms', 500)
        }
        common_game_config.update(pvp_game_specific_config)
        player1_env_config = {
            'initial_x': 0.5, 'initial_paddle_width': pvp_game_specific_config.get('player1_paddle_width', 100),
            'initial_lives': pvp_game_specific_config.get('player1_lives', 3), 'skill_code': p1_skill_code_from_menu, 'is_ai': False
        }
        opponent_env_config = {
            'initial_x': 0.5, 'initial_paddle_width': pvp_game_specific_config.get('player2_paddle_width', 100),
            'initial_lives': pvp_game_specific_config.get('player2_lives', 3), 'skill_code': p2_skill_code_from_menu, 'is_ai': False
        }
    else:
        if DEBUG_MAIN: print(f"[game_session] Unknown game mode: {current_game_mode_value}. Returning to select_game_mode.")
        return "select_game_mode"

    env = PongDuelEnv(
        game_mode=current_game_mode_value,
        player1_config=player1_env_config,
        opponent_config=opponent_env_config,
        common_config=common_game_config,
        render_size=render_size_for_env,
        paddle_height_px=paddle_height_for_env,
        ball_radius_px=ball_radius_for_env,
        initial_main_screen_surface_for_renderer=main_screen_surface_param
    )
    obs, _ = env.reset()
    # Renderer 將在第一次 env.render() 時初始化，並使用 main_screen_surface_param
    # Renderer 內部將負責遊戲內容的縮放和定位
    env.render() 

    if not env.renderer or not env.renderer.window or env.renderer.window is not main_screen_surface_param:
        if DEBUG_MAIN_FULLSCREEN:
            print("[DEBUG_MAIN_FULLSCREEN][game_session] CRITICAL: Renderer did not use the provided main_screen_surface_param.")
        return "quit" # 如果 Renderer 沒有正確設定，遊戲無法繼續

    # 背景音樂播放
    bg_music_to_play = common_game_config.get("bg_music", "bg_music_level1.mp3") # 從最終的 common_config 獲取
    if hasattr(env, 'sound_manager') and env.sound_manager and bg_music_to_play:
        bg_music_path = resource_path(f"assets/{bg_music_to_play}")
        if os.path.exists(bg_music_path):
            try:
                pygame.mixer.music.load(bg_music_path)
                pygame.mixer.music.set_volume(GameSettings.BACKGROUND_MUSIC_VOLUME)
                env.sound_manager.play_bg_music()
            except pygame.error as e:
                if DEBUG_MAIN: print(f"[DEBUG][game_session] Error loading/playing music '{bg_music_path}': {e}")
        else:
            if DEBUG_MAIN: print(f"[DEBUG][game_session] Warning: Music file not found: {bg_music_path}")

    initial_countdown_duration = common_game_config.get('countdown_seconds', GameSettings.COUNTDOWN_SECONDS)
    if initial_countdown_duration > 0 :
        if DEBUG_MAIN: print(f"[DEBUG][game_session] Starting initial countdown for {initial_countdown_duration} seconds.")
        show_countdown(env) # show_countdown 使用 env.renderer.window

    game_running = True
    game_session_result_state = "select_game_mode"

    while game_running:
        for event in pygame.event.get():
            # ... (事件處理不變) ...
            if event.type == pygame.QUIT:
                game_running = False
                game_session_result_state = "quit"
            elif event.type == pygame.KEYDOWN:
                if event.key == pygame.K_ESCAPE:
                    if DEBUG_MAIN: print("[DEBUG][game_session] ESC pressed during gameplay. Ending session.")
                    game_running = False
                    game_session_result_state = "select_game_mode"
        if not game_running: break

        keys = pygame.key.get_pressed()
        p1_ingame_action = 1 # 預設不動 (0: left, 1: stay, 2: right)

        if current_input_mode == "keyboard":
            if keys[P1_GAME_KEYS['LEFT_KB']]: p1_ingame_action = 0
            elif keys[P1_GAME_KEYS['RIGHT_KB']]: p1_ingame_action = 2
        elif current_input_mode == "mouse" and current_game_mode_value == GameSettings.GameMode.PLAYER_VS_AI: # 只在PVA模式下處理滑鼠
            mouse_x_abs, mouse_y_abs = pygame.mouse.get_pos() # 獲取的是實際螢幕座標
            
            logical_mouse_x = -1 # 預設為無效值，表示滑鼠不在有效區域或未成功轉換

            if hasattr(env, 'renderer') and env.renderer:
                # 獲取 PvA 遊戲區域在螢幕上的實際 Rect 和縮放因子
                # 我們期望 Renderer 中有 game_area_rect_on_screen (for PvA) 和 game_content_scale_factor
                
                actual_game_area_rect = None
                game_scale = 1.0

                if hasattr(env.renderer, 'game_area_rect_on_screen'): # PvA 模式下的遊戲區域
                    actual_game_area_rect = env.renderer.game_area_rect_on_screen
                else:
                    if DEBUG_MAIN_FULLSCREEN: print("[DEBUG_MOUSE_CTRL] Renderer missing 'game_area_rect_on_screen' for PvA mouse control.")
                
                if hasattr(env.renderer, 'game_content_scale_factor'):
                    game_scale = env.renderer.game_content_scale_factor
                elif hasattr(env.renderer, 'scale_factor_for_game'): # 備用名稱
                    game_scale = env.renderer.scale_factor_for_game
                else:
                    if DEBUG_MAIN_FULLSCREEN: print("[DEBUG_MOUSE_CTRL] Renderer missing scale factor for mouse control.")


                if actual_game_area_rect and game_scale > 0:
                    if DEBUG_MAIN_FULLSCREEN and pygame.time.get_ticks() % 300 == 0: # 每 5 秒左右打印一次，避免刷屏
                        print(f"[DEBUG_MOUSE_CTRL] Mouse_Abs: ({mouse_x_abs},{mouse_y_abs}), GameAreaRect: {actual_game_area_rect}, Scale: {game_scale:.2f}")

                    # 1. 檢查滑鼠是否在縮放後的遊戲區域內 (只關心X軸也可以，但Y軸檢查更嚴格)
                    if actual_game_area_rect.collidepoint(mouse_x_abs, mouse_y_abs):
                        # 2. 計算滑鼠相對於縮放後遊戲區域左邊界的 X 座標 (像素)
                        mouse_x_in_scaled_game_area = mouse_x_abs - actual_game_area_rect.left
                        
                        # 3. 將此座標轉換回未縮放的邏輯遊戲區域的 X 座標
                        #    縮放後的遊戲區域寬度是 actual_game_area_rect.width
                        #    它等於 env.render_size * game_scale
                        #    所以，mouse_x_in_logical_game_area = mouse_x_in_scaled_game_area / game_scale
                        mouse_x_in_logical_game_pixels = mouse_x_in_scaled_game_area / game_scale
                        
                        # 4. 將邏輯遊戲區域內的像素 X 座標正規化到 0-1
                        #    env.render_size 是遊戲的邏輯寬度 (例如 400)
                        if env.render_size > 0:
                            logical_mouse_x = mouse_x_in_logical_game_pixels / env.render_size
                        else:
                            logical_mouse_x = 0.5 # Fallback

                        # 5. 邊界限制
                        logical_mouse_x = max(0.0, min(1.0, logical_mouse_x))

                        if DEBUG_MAIN_FULLSCREEN and pygame.time.get_ticks() % 300 == 0:
                             print(f"    MouseInScaledGameAreaX: {mouse_x_in_scaled_game_area}, MouseInLogicalPixelsX: {mouse_x_in_logical_game_pixels:.2f}, LogicalMouseX_0-1: {logical_mouse_x:.3f}")
                    # else:
                        # if DEBUG_MAIN_FULLSCREEN and pygame.time.get_ticks() % 300 == 0:
                        #     print(f"    Mouse ({mouse_x_abs},{mouse_y_abs}) is OUTSIDE GameAreaRect {actual_game_area_rect}")

                else: # Renderer 缺少必要屬性時的 fallback
                    if DEBUG_MAIN_FULLSCREEN and pygame.time.get_ticks() % 300 == 0:
                        print("[DEBUG_MOUSE_CTRL] Fallback: Renderer attributes for precise mouse scaling not found. Using potentially inaccurate method.")
                    # 舊的、可能不準確的計算方式 (只適用於左上角未縮放的特定情況)
                    # 這裡的 game_area_x_start_on_screen 和 game_area_width_on_screen 需要是實際繪製的區域
                    # 如果 Renderer 已經居中和縮放了，這些固定值就是錯的
                    game_area_x_start_on_screen_fallback = 0 # 錯誤的假設
                    game_area_width_on_screen_fallback = env.render_size # 錯誤的假設
                    mouse_x_in_game_area_fallback = mouse_x_abs - game_area_x_start_on_screen_fallback
                    if game_area_width_on_screen_fallback > 0:
                        logical_mouse_x = mouse_x_in_game_area_fallback / game_area_width_on_screen_fallback
                        logical_mouse_x = max(0.0, min(1.0, logical_mouse_x))
                    else:
                        logical_mouse_x = 0.5


            if logical_mouse_x != -1: # 如果成功轉換了座標
                threshold = 0.02 # 移動閾值 (正規化座標)
                # 更新球拍動作 (0: left, 1: stay, 2: right)
                if logical_mouse_x < env.player1.x - threshold:
                    p1_ingame_action = 0
                elif logical_mouse_x > env.player1.x + threshold:
                    p1_ingame_action = 2
                # else: p1_ingame_action remains 1 (stay)
        
        if keys[P1_GAME_KEYS['SKILL_KB']]:
            if DEBUG_MAIN: print(f"[DEBUG][game_session] P1 skill key '{pygame.key.name(P1_GAME_KEYS['SKILL_KB'])}' pressed.")
            env.activate_skill(env.player1)

        opponent_ingame_action = 1
        if current_game_mode_value == GameSettings.GameMode.PLAYER_VS_AI:
            if ai_agent: opponent_ingame_action = ai_agent.select_action(obs.copy())
        else:
            if keys[P2_GAME_KEYS['LEFT']]: opponent_ingame_action = 0
            elif keys[P2_GAME_KEYS['RIGHT']]: opponent_ingame_action = 2
            if keys[P2_GAME_KEYS['SKILL']]:
                if DEBUG_MAIN: print(f"[DEBUG][game_session] P2 skill key '{pygame.key.name(P2_GAME_KEYS['SKILL'])}' pressed.")
                env.activate_skill(env.opponent)
        
        obs, reward, round_done, game_over, info = env.step(p1_ingame_action, opponent_ingame_action)
        env.render() # Renderer 內部會處理縮放和 flip

        if hasattr(env, 'renderer') and env.renderer and hasattr(env.renderer, 'clock'):
            env.renderer.clock.tick(60)
        else:
            pygame.time.delay(16)

        if round_done:
            if DEBUG_MAIN: print(f"[DEBUG][game_session] Round Done. Info: {info}. P1 Lives: {env.player1.lives}, Opponent Lives: {env.opponent.lives}")
            freeze_start_time = pygame.time.get_ticks()
            current_freeze_duration = env.freeze_duration
            if DEBUG_MAIN: print(f"[DEBUG][game_session] Starting freeze effect for {current_freeze_duration}ms.")

            while pygame.time.get_ticks() - freeze_start_time < current_freeze_duration:
                for event_freeze in pygame.event.get():
                    if event_freeze.type == pygame.QUIT:
                        game_running = False; game_session_result_state = "quit"; break
                    elif event_freeze.type == pygame.KEYDOWN:
                        if event_freeze.key == pygame.K_ESCAPE:
                            game_running = False; game_session_result_state = "select_game_mode"; break
                if not game_running: break
                env.render() # 持續渲染以顯示閃爍效果 (Renderer 內部 flip)
                pygame.time.delay(16) 
            if not game_running: break
            if DEBUG_MAIN: print(f"[DEBUG][game_session] Freeze effect finished. Game over: {game_over}")

            if game_over:
                p1_wins_msg = "PLAYER 1 WINS!" if current_game_mode_value == GameSettings.GameMode.PLAYER_VS_PLAYER else "YOU WIN!"
                p1_loses_msg = "PLAYER 2 WINS!" if current_game_mode_value == GameSettings.GameMode.PLAYER_VS_PLAYER else "YOU LOSE!"
                p1_color = Style.PLAYER_COLOR; opponent_color = Style.AI_COLOR
                
                # show_result_banner 使用 env.renderer.window (即 main_screen)
                if env.player1.lives <= 0:
                    if env.sound_manager: env.sound_manager.play_lose_sound()
                    show_result_banner(env.renderer.window, p1_loses_msg, opponent_color)
                elif env.opponent.lives <= 0:
                    if env.sound_manager: env.sound_manager.play_win_sound()
                    show_result_banner(env.renderer.window, p1_wins_msg, p1_color)
                game_running = False
                game_session_result_state = "select_game_mode"
            else:
                scorer = info.get('scorer')
                if DEBUG_MAIN: print(f"[DEBUG][game_session] Round ended, scorer: {scorer}. Resetting ball.")
                if scorer == 'player1': env.reset_ball_after_score(scored_by_player1=True)
                elif scorer == 'opponent': env.reset_ball_after_score(scored_by_player1=False)
                else: env.reset_ball_after_score(scored_by_player1=random.choice([True, False]))
                obs = env._get_obs()
                if DEBUG_MAIN: print("[DEBUG][game_session] Ball to be served immediately after freeze.")
    
    if hasattr(env, 'sound_manager'): env.sound_manager.stop_bg_music()
    env.close()
    return game_session_result_state


def main_loop():
    pygame.init()
    pygame.font.init()

    try:
        screen_info = pygame.display.Info()
        ACTUAL_SCREEN_WIDTH = screen_info.current_w
        ACTUAL_SCREEN_HEIGHT = screen_info.current_h
        if DEBUG_MAIN_FULLSCREEN:
            print(f"[DEBUG_MAIN_FULLSCREEN][main_loop] Detected screen: {ACTUAL_SCREEN_WIDTH}x{ACTUAL_SCREEN_HEIGHT}")
    except pygame.error as e:
        if DEBUG_MAIN_FULLSCREEN: print(f"[DEBUG_MAIN_FULLSCREEN][main_loop] Display error: {e}. Defaulting.")
        ACTUAL_SCREEN_WIDTH, ACTUAL_SCREEN_HEIGHT = 1280, 720

    try:
        main_screen = pygame.display.set_mode((ACTUAL_SCREEN_WIDTH, ACTUAL_SCREEN_HEIGHT), pygame.FULLSCREEN)
        if DEBUG_MAIN_FULLSCREEN: print(f"[DEBUG_MAIN_FULLSCREEN][main_loop] Fullscreen: {main_screen.get_size()}")
    except pygame.error as e:
        if DEBUG_MAIN_FULLSCREEN: print(f"[DEBUG_MAIN_FULLSCREEN][main_loop] Fullscreen failed: {e}. Windowed fallback.")
        try:
            main_screen = pygame.display.set_mode((ACTUAL_SCREEN_WIDTH, ACTUAL_SCREEN_HEIGHT))
            if DEBUG_MAIN_FULLSCREEN: print(f"[DEBUG_MAIN_FULLSCREEN][main_loop] Windowed: {main_screen.get_size()}")
        except pygame.error as e2:
            print(f"[CRITICAL_ERROR_MAIN][main_loop] No display mode: {e2}. Exit."); pygame.quit(); sys.exit()

    pygame.display.set_caption("Pong Soul")
    
    LOGICAL_MENU_WIDTH = 800
    LOGICAL_MENU_HEIGHT = 600
    LOGICAL_PVP_SKILL_MENU_WIDTH = 1000 
    LOGICAL_PVP_SKILL_MENU_HEIGHT = 600

    if DEBUG_MAIN_FULLSCREEN:
        print(f"[DEBUG_MAIN_FULLSCREEN][main_loop] Logical Menu Design: {LOGICAL_MENU_WIDTH}x{LOGICAL_MENU_HEIGHT}")
        print(f"[DEBUG_MAIN_FULLSCREEN][main_loop] Logical PvP Skill Menu Design: {LOGICAL_PVP_SKILL_MENU_WIDTH}x{LOGICAL_PVP_SKILL_MENU_HEIGHT}")
        
    current_input_mode = "keyboard" # 預設鍵盤
    p1_selected_skill_code, p2_selected_skill_code = None, None
    current_game_mode = None
    sound_manager = SoundManager()
    next_game_flow_step = "select_game_mode"
    running = True

    while running:
        if DEBUG_MAIN: print(f"[main_loop] Current step: {next_game_flow_step}")

        current_content_logical_width = 0
        current_content_logical_height = 0
        
        # 根據流程步驟設定當前內容的邏輯尺寸
        if next_game_flow_step == "select_game_mode":
            current_content_logical_width = LOGICAL_MENU_WIDTH
            current_content_logical_height = LOGICAL_MENU_HEIGHT
        elif next_game_flow_step == "select_input": # 只有 PvA 模式會進入此步驟
            current_content_logical_width = LOGICAL_MENU_WIDTH
            current_content_logical_height = LOGICAL_MENU_HEIGHT
        elif next_game_flow_step == "select_skill_pva":
             current_content_logical_width = LOGICAL_MENU_WIDTH
             current_content_logical_height = LOGICAL_MENU_HEIGHT
        elif next_game_flow_step == "run_pvp_skill_selection":
            current_content_logical_width = LOGICAL_PVP_SKILL_MENU_WIDTH
            current_content_logical_height = LOGICAL_PVP_SKILL_MENU_HEIGHT
        
        scale_factor = 1.0
        render_area_on_screen = pygame.Rect(0, 0, ACTUAL_SCREEN_WIDTH, ACTUAL_SCREEN_HEIGHT)

        if current_content_logical_width > 0 and current_content_logical_height > 0: # 計算選單的縮放和定位
            scale_x = ACTUAL_SCREEN_WIDTH / current_content_logical_width
            scale_y = ACTUAL_SCREEN_HEIGHT / current_content_logical_height
            scale_factor = min(scale_x, scale_y)
            scaled_content_width = int(current_content_logical_width * scale_factor)
            scaled_content_height = int(current_content_logical_height * scale_factor)
            offset_x = (ACTUAL_SCREEN_WIDTH - scaled_content_width) // 2
            offset_y = (ACTUAL_SCREEN_HEIGHT - scaled_content_height) // 2
            render_area_on_screen = pygame.Rect(offset_x, offset_y, scaled_content_width, scaled_content_height)
            
            if DEBUG_MAIN_FULLSCREEN and next_game_flow_step not in ["game_session_active_state"]:
                print(f"[DEBUG_MAIN_FULLSCREEN][main_loop] Content Scaling for '{next_game_flow_step}':")
                print(f"    Logical: {current_content_logical_width}x{current_content_logical_height}, Scale: {scale_factor:.2f}")
                print(f"    Render Area on Screen: {render_area_on_screen}")
        
        if next_game_flow_step not in ["game_session_active_state"]:
             main_screen.fill(Style.BACKGROUND_COLOR)

        if next_game_flow_step == "select_game_mode":
            current_game_mode = select_game_mode(main_screen, sound_manager, scale_factor, render_area_on_screen)
            if current_game_mode is None: # 通常意味著選擇了 "Quit Game" 或關閉
                next_game_flow_step = "quit"
                continue # flip 會在迴圈末尾處理
            
            p1_selected_skill_code, p2_selected_skill_code = None, None # 重置技能選擇

            # ⭐️ 根據遊戲模式決定下一步流程
            if current_game_mode == GameSettings.GameMode.PLAYER_VS_AI:
                next_game_flow_step = "select_input" # PvA 模式，進入輸入選擇
            elif current_game_mode == GameSettings.GameMode.PLAYER_VS_PLAYER:
                current_input_mode = "keyboard" # PvP 模式強制鍵盤
                if DEBUG_MAIN: print(f"[main_loop] PvP mode selected. Input mode forced to 'keyboard'.")
                next_game_flow_step = "run_pvp_skill_selection" # PvP 模式，直接進入技能選擇
            else:
                if DEBUG_MAIN: print(f"[main_loop] Unknown game mode from select_game_mode: {current_game_mode}. Defaulting to quit.")
                next_game_flow_step = "quit" # 未知模式，退出

        elif next_game_flow_step == "select_input": # 只有 PvA 模式會到這裡
            if current_game_mode != GameSettings.GameMode.PLAYER_VS_AI:
                if DEBUG_MAIN: print(f"[main_loop] Error: select_input step reached for non-PvA mode ({current_game_mode}). Returning to mode select.")
                next_game_flow_step = "select_game_mode"
                continue

            selection_result = select_input_method(main_screen, sound_manager, scale_factor, render_area_on_screen)
            if selection_result == "back_to_game_mode_select":
                next_game_flow_step = "select_game_mode"
                continue
            elif selection_result is None: # 如果 select_input_method 內部按了 ESC 或關閉
                next_game_flow_step = "select_game_mode" # 返回到模式選擇
                continue
            current_input_mode = selection_result # "keyboard" or "mouse"
            next_game_flow_step = "select_skill_pva"


        elif next_game_flow_step == "run_pvp_skill_selection": # 只有 PvP 模式到這裡
            if current_game_mode != GameSettings.GameMode.PLAYER_VS_PLAYER:
                if DEBUG_MAIN: print(f"[main_loop] Error: run_pvp_skill_selection step reached for non-PvP mode ({current_game_mode}). Returning to mode select.")
                next_game_flow_step = "select_game_mode"
                continue
            # 此時的 scale_factor 和 render_area_on_screen 是為 PvP 技能選單計算的
            p1_selected_skill_code, p2_selected_skill_code = run_pvp_selection_phase(
                main_screen, sound_manager, scale_factor, render_area_on_screen
            )
            if p1_selected_skill_code is None or p2_selected_skill_code is None: # 有人取消
                next_game_flow_step = "select_game_mode" # 如果PvP技能選擇取消，返回遊戲模式選擇
                continue
            # PvP 技能選擇完成，進入遊戲會話
            current_input_mode = "keyboard" # 再次確認 PvP 是鍵盤
            next_game_flow_step = game_session(main_screen, current_input_mode, p1_selected_skill_code, p2_selected_skill_code, current_game_mode)


        elif next_game_flow_step == "select_skill_pva": # 只有 PvA 模式到這裡
            if current_game_mode != GameSettings.GameMode.PLAYER_VS_AI:
                if DEBUG_MAIN: print(f"[main_loop] Error: select_skill_pva step reached for non-PvA mode ({current_game_mode}). Returning to mode select.")
                next_game_flow_step = "select_game_mode"
                continue
            # 此時的 scale_factor 和 render_area_on_screen 是為標準選單計算的
            p1_selected_skill_code = select_skill(
                main_screen_surface=main_screen,
                render_area=render_area_on_screen,
                key_map=DEFAULT_MENU_KEYS,
                sound_manager=sound_manager,
                player_identifier="Player",
                scale_factor=scale_factor
            )
            if p1_selected_skill_code is None: # 玩家取消選擇
                next_game_flow_step = "select_input" # 返回輸入選擇
                continue
            # PvA 技能選擇完成，進入遊戲會話
            next_game_flow_step = game_session(main_screen, current_input_mode, p1_selected_skill_code, None, current_game_mode)
        
        elif next_game_flow_step == "quit":
            running = False
        
        else: # 通常是從 game_session 返回
            # next_game_flow_step 可能是 "select_game_mode" 或 "quit"
            if next_game_flow_step not in ["select_game_mode", "select_input", "select_skill_pva", "quit", "run_pvp_skill_selection"]:
                if DEBUG_MAIN: print(f"[main_loop] Unknown next_game_flow_step: '{next_game_flow_step}'. Defaulting to 'select_game_mode'.")
                next_game_flow_step = "select_game_mode"

        if running:
             pygame.display.flip()

    if DEBUG_MAIN_FULLSCREEN: print("[DEBUG_MAIN_FULLSCREEN][main_loop] Exiting application.")
    pygame.quit()
    sys.exit()

if __name__ == '__main__':
    main_loop()