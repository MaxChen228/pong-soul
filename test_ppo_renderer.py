# test_ppo_renderer.py
import torch
import torch.nn as nn
import numpy as np
import pygame
import os
import time
import yaml
import argparse
import random

# 從專案中導入必要的類別
from envs.pong_duel_env import PongDuelEnv
from game.settings import GameSettings
from game.config_manager import ConfigManager as GameConfigManager # PongDuelEnv 可能需要
from utils import resource_path

# --- 與 train_ppo_agent.py 中 Actor 完全一致的網路定義 ---
def init_weights_actor_test(m):
    if isinstance(m, nn.Linear):
        nn.init.orthogonal_(m.weight.data, gain=nn.init.calculate_gain('relu'))
        if m.bias is not None:
            nn.init.constant_(m.bias.data, 0)

class ActorPolicy(nn.Module):
    def __init__(self, state_dim, action_dim, network_cfg): # 與 train_ppo_agent.py 中的 Actor 一致
        super(ActorPolicy, self).__init__()
        self.log_std_min = network_cfg['log_std_min']
        self.log_std_max = network_cfg['log_std_max']
        hidden_dim = network_cfg['actor_hidden_dim']

        self.net = nn.Sequential(
            nn.Linear(state_dim, hidden_dim),
            nn.ReLU(),
            nn.Linear(hidden_dim, hidden_dim),
            nn.ReLU()
        )
        self.mean_layer = nn.Linear(hidden_dim, action_dim)
        self.tanh = nn.Tanh()
        self.log_std_layer = nn.Linear(hidden_dim, action_dim)

        self.apply(init_weights_actor_test)
        init_log_std_bias = network_cfg.get('init_log_std_bias', -1.0)
        init_log_std_weights_limit = network_cfg.get('init_log_std_weights_uniform_abs_limit', 0.001)
        if init_log_std_weights_limit is not None:
             nn.init.uniform_(self.log_std_layer.weight.data, -init_log_std_weights_limit, init_log_std_weights_limit)
        if init_log_std_bias is not None:
            nn.init.constant_(self.log_std_layer.bias.data, init_log_std_bias)

    def forward(self, state, deterministic=False):
        x = self.net(state)
        mean_before_tanh = self.mean_layer(x)
        mean_tanh = self.tanh(mean_before_tanh)
        mean_scaled_to_0_1 = (mean_tanh + 1.0) / 2.0
        
        if deterministic:
            return mean_scaled_to_0_1, None
        else:
            log_std = self.log_std_layer(x)
            log_std = torch.clamp(log_std, self.log_std_min, self.log_std_max)
            return mean_scaled_to_0_1, log_std

# --- 配置加載函數 ---
def load_train_config(config_path="config/train_config.yaml"):
    try:
        with open(resource_path(config_path), 'r', encoding='utf-8') as f:
            cfg = yaml.safe_load(f)
        print(f"成功從 {config_path} 加載訓練配置。")
        return cfg
    except FileNotFoundError:
        print(f"錯誤: 訓練配置文件 {config_path} 未找到。將使用預設渲染設置。")
        return None
    except yaml.YAMLError as e:
        print(f"錯誤: 解析訓練配置文件 {config_path} 失敗: {e}")
        return None
    except Exception as e:
        print(f"錯誤: 加載訓練配置文件 {config_path} 時發生未知錯誤: {e}")
        return None

# --- 主測試函數 ---
def test_model_with_config_render(config_file_path="config/train_config.yaml", model_episode_num=200):
    train_cfg = load_train_config(config_file_path)

    if train_cfg is None:
        print("無法加載訓練配置，測試終止。")
        return

    cfg_general = train_cfg['general']
    cfg_model_io = train_cfg['model_io']
    cfg_network = train_cfg['network']
    cfg_viz = train_cfg.get('visualization', {})

    # 設定設備
    device_name = cfg_general.get('device', 'auto')
    if device_name == "auto":
        device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    elif device_name == "cuda" and torch.cuda.is_available():
        device = torch.device("cuda")
    else:
        device = torch.device("cpu")
    print(f"開始測試模型，使用設備: {device}")

    # 從訓練配置中獲取模型和觀察/動作維度
    obs_dim = cfg_general['obs_dim']
    action_dim = cfg_general['action_dim']
    model_dir = cfg_model_io['model_dir']
    model_name_prefix = cfg_model_io['model_name_prefix']

    if model_episode_num is None:
        model_filename = f"{model_name_prefix}_latest.pth"
    else:
        model_filename = f"{model_name_prefix}_episode_{model_episode_num}.pth"
    
    model_path = resource_path(os.path.join(model_dir, model_filename))
    print(f"載入模型: {model_path}")

    # 初始化 Pygame 和渲染視窗 (與 train_ppo_agent.py 相同的方式)
    pygame.init()
    pygame.font.init() # 確保字體系統已初始化，供 Style 使用

    render_screen_width = cfg_viz.get('render_screen_width', 800) # 從 train_config 讀取或預設
    render_screen_height = cfg_viz.get('render_screen_height', 600)
    render_fps = cfg_viz.get('render_fps', 60)

    screen = pygame.display.set_mode((render_screen_width, render_screen_height))
    pygame.display.set_caption(f"Pong Soul - PPO Agent Test ({model_filename})")
    clock = pygame.time.Clock()

    # 初始化遊戲相關的 ConfigManager 和 GameSettings (主要為了主題)
    game_config_manager = GameConfigManager()
    GameSettings._config_manager = game_config_manager # 將實例賦值給 GameSettings
    try:
        import game.theme # 確保主題模組被加載
        game.theme.reload_active_style() # 根據 global_settings.yaml 加載主題
        print(f"測試時使用主題: {GameSettings.ACTIVE_THEME_NAME}")
    except Exception as e:
        print(f"測試時載入主題發生錯誤: {e}")


    # 初始化 Actor 網路
    actor_policy_net = ActorPolicy(
        obs_dim,
        action_dim,
        cfg_network # 從 train_config.yaml 讀取的網路配置
    ).to(device)

    if os.path.exists(model_path):
        try:
            checkpoint = torch.load(model_path, map_location=device)
            actor_policy_net.load_state_dict(checkpoint['actor_state_dict'])
            print(f"成功載入 Actor 網路權重從: {model_path}")
            loaded_episode = checkpoint.get('episode_count', '未知')
            print(f"  模型來自 episode: {loaded_episode}")
        except Exception as e:
            print(f"載入模型權重時發生錯誤: {e}。")
            pygame.quit()
            return
    else:
        print(f"錯誤: 找不到模型檔案 {model_path}。")
        pygame.quit()
        return
    actor_policy_net.eval()

    # 初始化環境 (使用 level1.yaml 作為基礎配置，與訓練時相似)
    level1_yaml_path = resource_path("models/level1.yaml")
    common_game_cfg = {}
    if os.path.exists(level1_yaml_path):
        common_game_cfg = game_config_manager.get_level_config(os.path.basename(level1_yaml_path)) # 傳遞檔案名
        if common_game_cfg is None: common_game_cfg = {}
    else:
        # 提供一些基礎預設值 (如果 level1.yaml 缺失)
        common_game_cfg.setdefault('initial_speed', 0.02)
        common_game_cfg.setdefault('player_life', 3)
        common_game_cfg.setdefault('ai_life', 3)
        common_game_cfg.setdefault('player_paddle_width', 100)
        common_game_cfg.setdefault('ai_paddle_width', 60)

    player1_env_config = {
        'initial_x': 0.5,
        'initial_paddle_width': common_game_cfg.get('player_paddle_width', 100),
        'initial_lives': common_game_cfg.get('player_life', 3),
        'skill_code': None, 'is_ai': False
    }
    opponent_env_config = { # 這是我們的 PPO AI
        'initial_x': 0.5,
        'initial_paddle_width': common_game_cfg.get('ai_paddle_width', 60), # AI 球拍寬度應與訓練時觀察空間對應的AI球拍寬度一致
        'initial_lives': common_game_cfg.get('ai_life', 3),
        'skill_code': None, 'is_ai': True
    }

    env = PongDuelEnv(
        game_mode=GameSettings.GameMode.PLAYER_VS_AI,
        player1_config=player1_env_config,
        opponent_config=opponent_env_config,
        common_config=common_game_cfg,
        render_size=400, # 與訓練時的 env 內部邏輯尺寸一致
        paddle_height_px=10,
        ball_radius_px=10,
        initial_main_screen_surface_for_renderer=screen # 將創建的 Pygame screen 傳給 Env
    )

    num_test_episodes = cfg_viz.get('render_every_n_episodes', 5) # 可以用訓練配置中的渲染頻率，或自訂
    if num_test_episodes == 0: num_test_episodes = 5 # 如果訓練配置不渲染，則預設測試5回合

    for i_episode in range(1, num_test_episodes + 1):
        state, _ = env.reset()
        print(f"\n--- 開始測試回合 {i_episode}/{num_test_episodes} ---")
        
        # 遊戲開始倒數 (可選，如果 GameplayState 中有此邏輯，這裡可省略)
        # 為了與 train_ppo_agent.py 的渲染行為一致，我們不在此處手動加載倒數
        # 而是依賴 env 本身的邏輯 (如果有的話) 或直接開始遊戲

        for t in range(cfg_viz.get('render_frames_per_episode', 3000)): # 與訓練時每回合最大步數類似
            # AI (opponent) 選擇動作
            with torch.no_grad():
                state_tensor = torch.FloatTensor(state.reshape(1, -1)).to(device)
                action_mean_scaled, _ = actor_policy_net(state_tensor, deterministic=True) # 確定性動作
                action_opponent_target_x = action_mean_scaled.cpu().numpy().flatten()[0]

            # Player 1 的動作 (簡單規則：追球X)
            # 觀察向量中 Ball X 的索引，需要根據 PongDuelEnv._get_obs() 的定義
            # 根據 envs/pong_duel_env.py _get_obs() 中 ball_x 的索引是 6
            ball_x_in_obs_idx = 6
            if state.shape[0] > ball_x_in_obs_idx:
                action_player1_target_x = np.clip(state[ball_x_in_obs_idx], 0.0, 1.0)
            else: # 防禦性程式碼，如果觀察空間不對
                action_player1_target_x = 0.5


            next_state, _, round_done, game_over, info = env.step(
                action_player1_target_x,
                action_opponent_target_x
            )
            
            # 打印 AI 的目標 X 和實際 X (可選)
            if t % 60 == 0: # 每秒打印一次 (假設 FPS=60)
                print(f"  TestStep {t}: AI TargetX: {action_opponent_target_x:.3f}, AI ActualX: {env.opponent.x:.3f}, BallX: {env.ball_x:.3f}, BallY: {env.ball_y:.3f}")

            env.render() # 渲染遊戲畫面
            state = next_state

            # 處理 Pygame 事件，允許關閉視窗
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    print("用戶請求退出。")
                    if env: env.close()
                    pygame.quit()
                    return
                if event.type == pygame.KEYDOWN:
                    if event.key == pygame.K_ESCAPE:
                        print("用戶按下 ESC 退出。")
                        if env: env.close()
                        pygame.quit()
                        return
            
            clock.tick(render_fps) # 控制幀率，使用 train_config 中的設定

            if game_over:
                print(f"回合 {i_episode} 結束 (遊戲結束). Scorer: {info.get('scorer', 'N/A')}, P1 Lives: {env.player1.lives}, AI Lives: {env.opponent.lives}")
                time.sleep(1) # 遊戲結束後暫停一下
                break
            elif round_done:
                print(f"  回合 {i_episode} - {t+1} 步: 一分結束 (Scorer: {info.get('scorer', 'N/A')}). 生命 P1: {env.player1.lives}, AI: {env.opponent.lives}")
                # 回合結束後的短暫停頓由 env.freeze_timer 控制，此處不需額外 time.sleep

    print("測試完成。")
    if env: env.close()
    pygame.quit()

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description="PPO Pong Agent Testing Script with Configurable Rendering")
    parser.add_argument(
        "--config", type=str, default="config/train_config.yaml",
        help="Path to the training configuration YAML file (used for rendering settings and model path)."
    )
    parser.add_argument(
        "--episode", type=int, default=None,
        help="Specify the episode number of the model to test (e.g., 1000). If None, loads '_latest.pth'."
    )
    args = parser.parse_args()

    test_model_with_config_render(config_file_path=args.config, model_episode_num=args.episode)