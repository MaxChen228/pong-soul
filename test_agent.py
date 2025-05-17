import torch
import torch.nn as nn
import numpy as np
import pygame
import os
import time # 用於控制幀率

# 從專案中導入必要的類別
from envs.pong_duel_env import PongDuelEnv
from game.settings import GameSettings
from game.config_manager import ConfigManager # PongDuelEnv 可能需要
from utils import resource_path

# --- 與 train_ppo_agent.py 中 Actor 完全一致的網路定義 ---
# 為了確保一致性，直接複製 train_ppo_agent.py 中的 Actor 定義
# 或者，更好的做法是將 Actor, Critic 移到一個共享文件中導入

def init_weights_actor_test(m): # 避免與 train_ppo_agent.py 中的函數名衝突
    if isinstance(m, nn.Linear):
        nn.init.orthogonal_(m.weight.data, gain=nn.init.calculate_gain('relu'))
        if m.bias is not None:
            nn.init.constant_(m.bias.data, 0)

class ActorPolicy(nn.Module): # 在測試時，我們只關心 Actor 的策略部分
    def __init__(self, state_dim, action_dim, hidden_dim=256, log_std_min=-20, log_std_max=-0.5, init_log_std_bias=-1.0, init_log_std_weights_uniform_abs_limit=0.001):
        super(ActorPolicy, self).__init__()
        self.log_std_min = log_std_min
        self.log_std_max = log_std_max

        self.net = nn.Sequential(
            nn.Linear(state_dim, hidden_dim),
            nn.ReLU(),
            nn.Linear(hidden_dim, hidden_dim),
            nn.ReLU()
        )
        self.mean_layer = nn.Linear(hidden_dim, action_dim)
        self.tanh = nn.Tanh() # 保持與訓練時 Actor 一致
        self.log_std_layer = nn.Linear(hidden_dim, action_dim)

        self.apply(init_weights_actor_test) # 使用獨立的 init_weights 函數名

        # 與訓練時 Actor 一致的 log_std_layer 初始化
        if init_log_std_weights_uniform_abs_limit is not None:
             nn.init.uniform_(self.log_std_layer.weight.data, -init_log_std_weights_uniform_abs_limit, init_log_std_weights_uniform_abs_limit)
        if init_log_std_bias is not None:
            nn.init.constant_(self.log_std_layer.bias.data, init_log_std_bias)


    def forward(self, state, deterministic=False): # 增加 deterministic 參數
        x = self.net(state)
        mean_before_tanh = self.mean_layer(x)
        mean_tanh = self.tanh(mean_before_tanh)
        mean_scaled_to_0_1 = (mean_tanh + 1.0) / 2.0    # 輸出範圍 [0, 1]
        
        if deterministic:
            return mean_scaled_to_0_1, None # 確定性動作，不需要 log_std
        else:
            log_std = self.log_std_layer(x)
            log_std = torch.clamp(log_std, self.log_std_min, self.log_std_max)
            return mean_scaled_to_0_1, log_std

# --- 設定與常數 ---
device = torch.device("cpu") # 測試時通常用 CPU 即可
OBS_DIM = 15  # 應與 train_config.yaml 中的 general.obs_dim 一致
ACTION_DIM = 1 # 應與 train_config.yaml 中的 general.action_dim 一致

# --- 從 train_config.yaml 加載必要的網路參數 ---
# 為了簡化 test_agent.py，我們直接在這裡複製必要的網路配置值
# 更好的做法是 test_agent.py 也讀取 train_config.yaml
# 或者將網路配置硬編碼，但要確保與訓練時一致
# 這裡我們假設直接使用訓練時的配置值：
# 來自 train_config.yaml -> network
ACTOR_HIDDEN_DIM = 256
LOG_STD_MIN = -20
LOG_STD_MAX = -0.5
INIT_LOG_STD_BIAS = -1.0
INIT_LOG_STD_WEIGHTS_UNIFORM_ABS_LIMIT = 0.001


# --- 從 train_config.yaml 加載模型路徑相關配置 ---
# 這裡我們直接複製模型路徑相關配置值
# 更好的做法是 test_agent.py 也讀取 train_config.yaml 的 model_io 部分
# 來自 train_config.yaml -> model_io
MODEL_DIR_FROM_CONFIG = "ppo_models"
MODEL_NAME_PREFIX_FROM_CONFIG = "ppo_pong_configurable_ai" # 確保這個與您訓練時使用的前綴一致
# MODEL_FILENAME = f"{MODEL_NAME_PREFIX_FROM_CONFIG}_latest.pth"
# 或者測試特定 episode 的模型
MODEL_FILENAME = f"{MODEL_NAME_PREFIX_FROM_CONFIG}_episode_400.pth" # 假設測試 episode 1000
MODEL_PATH = os.path.join(MODEL_DIR_FROM_CONFIG, MODEL_FILENAME)


# 遊戲畫面設定
SCREEN_WIDTH = 1000
SCREEN_HEIGHT = 700
FPS = 60

# --- 主測試函數 ---
def test_model():
    print(f"開始測試模型，使用設備: {device}")
    print(f"載入模型: {MODEL_PATH}")

    pygame.init()
    pygame.font.init()
    screen = pygame.display.set_mode((SCREEN_WIDTH, SCREEN_HEIGHT))
    pygame.display.set_caption("Pong Soul - PPO Agent Test")
    clock = pygame.time.Clock()

    game_config_manager = ConfigManager()
    GameSettings._config_manager = game_config_manager
    try:
        import game.theme
        game.theme.reload_active_style()
        print(f"使用主題: {GameSettings.ACTIVE_THEME_NAME}")
    except Exception as e:
        print(f"載入主題時發生錯誤: {e}")

    actor_policy_net = ActorPolicy(
        OBS_DIM,
        ACTION_DIM,
        hidden_dim=ACTOR_HIDDEN_DIM,
        log_std_min=LOG_STD_MIN,
        log_std_max=LOG_STD_MAX,
        init_log_std_bias=INIT_LOG_STD_BIAS,
        init_log_std_weights_uniform_abs_limit=INIT_LOG_STD_WEIGHTS_UNIFORM_ABS_LIMIT
    ).to(device)

    if os.path.exists(MODEL_PATH):
        try:
            checkpoint = torch.load(MODEL_PATH, map_location=device)
            # 加載 actor 的 state_dict (PPOAgent 保存的是 actor，而不是 actor_old)
            actor_policy_net.load_state_dict(checkpoint['actor_state_dict'])
            print(f"成功載入 Actor 網路權重從: {MODEL_PATH}")
            print(f"  模型來自 episode: {checkpoint.get('episode_count', '未知')}, total_timesteps: {checkpoint.get('time_step_counter', '未知')}")
            if 'train_config_snapshot' in checkpoint:
                print(f"  模型訓練時使用的配置快照 (部分網絡參數):")
                loaded_net_cfg = checkpoint['train_config_snapshot'].get('network', {})
                print(f"    Actor Hidden Dim: {loaded_net_cfg.get('actor_hidden_dim')}")
                print(f"    LogStd Min/Max: {loaded_net_cfg.get('log_std_min')}, {loaded_net_cfg.get('log_std_max')}")
                print(f"    Init LogStd Bias: {loaded_net_cfg.get('init_log_std_bias')}")

        except Exception as e:
            print(f"載入模型權重時發生錯誤: {e}。請確保模型檔案與 ActorPolicy 結構兼容。")
            pygame.quit()
            return
    else:
        print(f"錯誤: 找不到模型檔案 {MODEL_PATH}。請先訓練模型。")
        pygame.quit()
        return
    actor_policy_net.eval()

    # 初始化環境 (與訓練時的設定盡可能一致)
    level1_yaml_path = "models/level1.yaml" # 假設測試也用 level1 的配置
    common_game_cfg = {}
    if os.path.exists(resource_path(level1_yaml_path)):
        common_game_cfg = game_config_manager.get_level_config("level1.yaml")
        if common_game_cfg is None: common_game_cfg = {}
    else:
        # 提供一些基礎預設值
        common_game_cfg.setdefault('initial_speed', 0.02)
        common_game_cfg.setdefault('initial_angle_deg_range', [-60, 60])
        common_game_cfg.setdefault('player_life', 3)
        common_game_cfg.setdefault('ai_life', 3)
        common_game_cfg.setdefault('player_paddle_width', 100)
        common_game_cfg.setdefault('ai_paddle_width', 60) # 與訓練時的 AI 球拍寬度一致

    player1_env_config = {
        'initial_x': 0.5,
        'initial_paddle_width': common_game_cfg.get('player_paddle_width', 100),
        'initial_lives': common_game_cfg.get('player_life', 3),
        'skill_code': None, 'is_ai': False
    }
    opponent_env_config = { # 這是我們的 PPO AI
        'initial_x': 0.5,
        'initial_paddle_width': common_game_cfg.get('ai_paddle_width', 60),
        'initial_lives': common_game_cfg.get('ai_life', 3),
        'skill_code': None, 'is_ai': True
    }

    env = PongDuelEnv(
        game_mode=GameSettings.GameMode.PLAYER_VS_AI,
        player1_config=player1_env_config,
        opponent_config=opponent_env_config,
        common_config=common_game_cfg,
        render_size=400,
        paddle_height_px=10,
        ball_radius_px=10,
        initial_main_screen_surface_for_renderer=screen
    )

    num_test_episodes = 10
    for i_episode in range(1, num_test_episodes + 1):
        state, _ = env.reset()
        print(f"\n--- 開始測試回合 {i_episode}/{num_test_episodes} ---")

        for t in range(2000): # 每回合最多執行 2000 步進行觀察
            # AI (opponent) 選擇動作
            with torch.no_grad():
                state_tensor = torch.FloatTensor(state.reshape(1, -1)).to(device)
                
                # 測試時，我們通常使用確定性動作 (即直接取 mean)
                # 或者，如果想觀察帶一點隨機性的策略，可以從 Normal(mean, std) 採樣
                # 這裡我們選擇確定性動作：
                action_mean_scaled, _ = actor_policy_net(state_tensor, deterministic=True) # mean_scaled 已經是 [0,1]
                
                # 如果想加入少量固定的隨機性進行測試（不推薦，除非特定目的）：
                # action_mean_scaled, action_log_std = actor_policy_net(state_tensor, deterministic=False)
                # test_std = 0.05 # 一個非常小的固定標準差
                # dist = Normal(action_mean_scaled, test_std)
                # sampled_action = dist.sample()
                # action_opponent_target_x = torch.clamp(sampled_action, 0.0, 1.0).cpu().numpy().flatten()[0]
                
                # 直接使用確定性的 mean (已經是 [0,1] 範圍)
                action_opponent_target_x = action_mean_scaled.cpu().numpy().flatten()[0]

            # Player 1 的動作 (簡單規則：追球X)
            ball_x_in_obs_idx = 6 # Ball X 在觀察向量中的索引
            action_player1_target_x = np.clip(state[ball_x_in_obs_idx], 0.0, 1.0)

            next_state, _, round_done, game_over, info = env.step(
                action_player1_target_x,
                action_opponent_target_x
            )
            
            # 打印 AI 的目標 X 和實際 X，方便觀察
            if t % 50 == 0: # 每50幀打印一次
                print(f"  TestStep {t}: AI TargetX: {action_opponent_target_x:.4f}, AI ActualX: {env.opponent.x:.4f}, BallX: {env.ball_x:.4f}")

            env.render() # 渲染遊戲畫面
            state = next_state

            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    print("用戶請求退出。")
                    env.close()
                    pygame.quit()
                    return
                if event.type == pygame.KEYDOWN:
                    if event.key == pygame.K_ESCAPE:
                        print("用戶按下 ESC 退出。")
                        env.close()
                        pygame.quit()
                        return
            
            clock.tick(FPS)

            if game_over:
                print(f"回合 {i_episode} 結束 (遊戲結束). Scorer: {info.get('scorer', 'N/A')}")
                time.sleep(1)
                break
            elif round_done:
                print(f"  回合 {i_episode} - {t+1} 步: 一分結束 (Scorer: {info.get('scorer', 'N/A')}). 生命 P1: {env.player1.lives}, Opp: {env.opponent.lives}")
                # time.sleep(0.5) # 回合間的短暫停頓可以不要，以便更快看到下一回合

    print("測試完成。")
    env.close()
    pygame.quit()

if __name__ == '__main__':
    test_model()