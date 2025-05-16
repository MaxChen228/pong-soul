import torch
import numpy as np
import pygame
import os
import time # 用於控制幀率

# 從專案中導入必要的類別
from envs.pong_duel_env import PongDuelEnv
from game.settings import GameSettings
from game.config_manager import ConfigManager
from utils import resource_path

# 從 train_ppo_agent.py 複製 Actor 網路定義
# 或者，您可以將 Actor, Critic, PPOAgent 等移到一個共享的 agent_ppo.py 檔案中
# 然後從該檔案導入。為了簡潔，這裡直接複製 Actor 定義。
import torch.nn as nn

def init_weights_test(m): # 避免與 train_ppo_agent.py 中的函數名衝突 (如果它們在同一進程中被導入)
    if isinstance(m, nn.Linear):
        nn.init.orthogonal_(m.weight.data, gain=nn.init.calculate_gain('relu'))
        if m.bias is not None:
            nn.init.constant_(m.bias.data, 0)

class ActorPolicy(nn.Module): # 重新命名以避免與訓練腳本中的 Actor 衝突
    def __init__(self, state_dim, action_dim, hidden_dim=128, log_std_min=-20, log_std_max=2):
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
        self.log_std_layer = nn.Linear(hidden_dim, action_dim)
        self.apply(init_weights_test)

    def forward(self, state):
        x = self.net(state)
        mean = self.mean_layer(x)
        log_std = self.log_std_layer(x)
        log_std = torch.clamp(log_std, self.log_std_min, self.log_std_max)
        return mean, log_std

# --- 設定與常數 ---
device = torch.device("cpu") # 測試時通常用 CPU 即可
OBS_DIM = 15
ACTION_DIM = 1
MODEL_DIR = "ppo_models"
MODEL_FILENAME = "ppo_pong_strategic_ai_latest.pth" # 或指定特定 episode 的模型檔案
MODEL_PATH = os.path.join(MODEL_DIR, MODEL_FILENAME)

# 遊戲畫面設定
SCREEN_WIDTH = 1000 # 測試時的視窗寬度
SCREEN_HEIGHT = 700 # 測試時的視窗高度
FPS = 60

# --- 主測試函數 ---
def test_model():
    print(f"開始測試模型，使用設備: {device}")
    print(f"載入模型: {MODEL_PATH}")

    # 初始化 Pygame
    pygame.init()
    pygame.font.init() # GameSettings 或 Theme 可能需要
    screen = pygame.display.set_mode((SCREEN_WIDTH, SCREEN_HEIGHT))
    pygame.display.set_caption("Pong Soul - PPO Agent Test")
    clock = pygame.time.Clock()

    # 初始化 ConfigManager 和 GameSettings
    config_manager = ConfigManager()
    GameSettings._config_manager = config_manager
    # 手動觸發一次主題載入，因為 PongDuelEnv 的 Renderer 會用到 Style
    try:
        import game.theme
        game.theme.reload_active_style()
        print(f"使用主題: {GameSettings.ACTIVE_THEME_NAME}")
    except Exception as e:
        print(f"載入主題時發生錯誤: {e}")


    # 初始化 AI 代理 (只需要 Actor)
    # 注意：PPOAgent 類包含訓練邏輯，測試時我們只需要 Actor 網路來選擇動作。
    # 我們可以直接載入 Actor 網路的 state_dict。
    actor_policy_net = ActorPolicy(OBS_DIM, ACTION_DIM, hidden_dim=256).to(device) # hidden_dim 與訓練時一致

    if os.path.exists(MODEL_PATH):
        checkpoint = torch.load(MODEL_PATH, map_location=device)
        actor_policy_net.load_state_dict(checkpoint['actor_state_dict'])
        print(f"成功載入 Actor 網路權重從: {MODEL_PATH}")
        print(f"  模型來自 episode: {checkpoint.get('episode_count', '未知')}, total_timesteps: {checkpoint.get('time_step_counter', '未知')}")
    else:
        print(f"錯誤: 找不到模型檔案 {MODEL_PATH}。請先訓練模型。")
        pygame.quit()
        return
    actor_policy_net.eval() # 設定為評估模式

    # 初始化環境 (與訓練時的設定盡可能一致)
    level1_yaml_path = "models/level1.yaml"
    common_game_cfg = {}
    if os.path.exists(resource_path(level1_yaml_path)):
        common_game_cfg = config_manager.get_level_config("level1.yaml")
        if common_game_cfg is None: common_game_cfg = {}
    else:
        common_game_cfg.setdefault('initial_speed', 0.02)
        common_game_cfg.setdefault('initial_angle_deg_range', [-60, 60])
        # ... 其他必要的預設值 ...
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
        initial_main_screen_surface_for_renderer=screen # ⭐️ 傳遞實際的螢幕物件
    )

    num_test_episodes = 10
    for i_episode in range(1, num_test_episodes + 1):
        state, _ = env.reset()
        episode_reward = 0
        print(f"\n--- 開始測試回合 {i_episode}/{num_test_episodes} ---")

        for t in range(2000): # 每回合最多執行 2000 步進行觀察
            # AI (opponent) 選擇動作
            with torch.no_grad():
                state_tensor = torch.FloatTensor(state.reshape(1, -1)).to(device)
                action_mean, action_log_std = actor_policy_net(state_tensor)
                # 在測試時，通常直接使用 mean 作為確定性動作，或從均值加微小噪聲採樣
                # action_continuous_opponent = torch.tanh(action_mean).cpu().numpy().flatten() # 如果 mean 本身是 raw logits
                # 如果 ActorPolicy 的 forward 輸出 mean 已經是 logits，而 PPO 的 action_env = torch.clamp(action, 0.0, 1.0)
                # 這裡我們直接取 mean，然後 clip。
                # 我們的 ActorPolicy 輸出 mean 和 log_std, mean 是 (-inf, inf)
                # QNet/Actor 在 game/ai_agent.py 是 (tanh+1)/2 輸出 [0,1]
                # 為保持一致，如果用 ActorPolicy，我們也應該這樣處理
                # 修正：讓 ActorPolicy 也輸出 [0,1] 的確定性動作均值，或在 test 裡處理
                
                # 簡化：直接使用 ActorPolicy 的 mean，然後應用 (tanh+1)/2 轉換 (如果 mean 本身沒有 tanh)
                # 或者，如果 ActorPolicy 的 mean_layer 後面期望有 tanh:
                # action_mean_activated = torch.tanh(action_mean) # -> [-1, 1]
                # action_scaled = (action_mean_activated + 1.0) / 2.0 # -> [0, 1]
                # action_opponent_target_x = action_scaled.cpu().numpy().flatten()[0]
                
                # 根據我們 train_ppo_agent.py 中 ActorPolicy 的定義，mean_layer 後沒有 tanh
                # 所以 action_mean 是原始 logits。
                # 通常測試時，從 Normal(mean, exp(log_std)) 中取 mean
                # 然後 clip 到 [0,1]
                action_opponent_target_x = torch.clamp(action_mean, 0.0, 1.0).cpu().numpy().flatten()[0]


            # Player 1 的動作 (規則型)
            ball_x_in_obs_idx = 6 # Ball X
            action_player1_target_x = np.clip(state[ball_x_in_obs_idx], 0.0, 1.0)

            next_state, reward_from_env, round_done, game_over, info = env.step(
                action_player1_target_x,
                action_opponent_target_x
            )
            
            # 測試時，我們通常不太關心獎勵函數，而是觀察行為
            # episode_reward += reward_from_env # env.step 目前 reward 是 0

            env.render() # ⭐️ 渲染遊戲畫面

            state = next_state

            # 處理 Pygame 事件 (例如關閉視窗)
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
            
            clock.tick(FPS) # 控制幀率

            if game_over:
                print(f"回合 {i_episode} 結束 (遊戲結束).")
                if info.get('scorer') == 'player1':
                    print("  AI (Opponent) 失利!")
                elif info.get('scorer') == 'opponent':
                    print("  AI (Opponent) 獲勝!")
                else:
                    print("  回合結束，原因未知或平局。")
                time.sleep(1) # 短暫停留觀看結果
                break
            elif round_done: # 僅回合結束，遊戲繼續
                print(f"  回合 {i_episode} - {t+1} 步: 一分結束 (Scorer: {info.get('scorer', 'N/A')}). 生命 P1: {env.player1.lives}, Opp: {env.opponent.lives}")
                time.sleep(0.5)


    print("測試完成。")
    env.close()
    pygame.quit()

if __name__ == '__main__':
    test_model()