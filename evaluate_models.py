import torch
import torch.nn as nn
import numpy as np
import os
import pygame # 即使不渲染，PongDuelEnv 可能也需要 Pygame 初始化
import yaml
import argparse
import random

# 從專案中導入必要的類別和函數
# 假設 evaluate_models.py 與 train_ppo_agent.py 在同一層級，或者 utils, envs, game 等在 PYTHONPATH 中
from envs.pong_duel_env import PongDuelEnv
from game.settings import GameSettings # PongDuelEnv 可能間接依賴
from game.config_manager import ConfigManager as GameConfigManager # PongDuelEnv 可能需要
from utils import resource_path # 用於處理資源路徑

# --- 與 train_ppo_agent.py 中 Actor 完全一致的網路定義 ---
# 這對於正確載入模型狀態字典至關重要
def init_weights(m):
    if isinstance(m, nn.Linear):
        nn.init.orthogonal_(m.weight.data, gain=nn.init.calculate_gain('relu'))
        if m.bias is not None:
            nn.init.constant_(m.bias.data, 0)

class Actor(nn.Module):
    def __init__(self, state_dim, action_dim, network_cfg):
        super(Actor, self).__init__()
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

        self.apply(init_weights)
        init_log_std_bias = network_cfg.get('init_log_std_bias', -1.0)
        init_log_std_weights_limit = network_cfg.get('init_log_std_weights_uniform_abs_limit', 0.001)
        if init_log_std_weights_limit is not None:
             nn.init.uniform_(self.log_std_layer.weight.data, -init_log_std_weights_limit, init_log_std_weights_limit)
        if init_log_std_bias is not None:
            nn.init.constant_(self.log_std_layer.bias.data, init_log_std_bias)

    def forward(self, state, deterministic=False): # 添加 deterministic 參數
        x = self.net(state)
        mean_before_tanh = self.mean_layer(x)
        mean_tanh = self.tanh(mean_before_tanh)
        mean_scaled_to_0_1 = (mean_tanh + 1.0) / 2.0

        if deterministic:
            return mean_scaled_to_0_1, None # 在評估時，通常使用確定性動作
        else:
            log_std = self.log_std_layer(x)
            log_std = torch.clamp(log_std, self.log_std_min, self.log_std_max)
            return mean_scaled_to_0_1, log_std

# --- 與 train_ppo_agent.py 中類似的配置加載函數 ---
def load_config_from_yaml(config_path):
    try:
        with open(config_path, 'r', encoding='utf-8') as f:
            cfg = yaml.safe_load(f)
        print(f"成功從 {config_path} 加載評估用訓練配置。")
        return cfg
    except FileNotFoundError:
        print(f"錯誤: 訓練配置文件 {config_path} 未找到。")
        exit(1)
    except yaml.YAMLError as e:
        print(f"錯誤: 解析訓練配置文件 {config_path} 失敗: {e}")
        exit(1)
    except Exception as e:
        print(f"錯誤: 加載訓練配置文件 {config_path} 時發生未知錯誤: {e}")
        exit(1)

# --- 與 train_ppo_agent.py 中類似的獎勵計算函數 ---
# 為了評估，我們也需要這個函數，因為環境本身不包含獎勵計算邏輯
def calculate_reward(reward_cfg, current_state, env_info, done, prev_ball_y_obs, current_ball_y_obs, player1_lives, opponent_lives, prev_player1_lives, prev_opponent_lives):
    reward = 0.0
    # reward_components = {} # 在評估時，我們可能不太關心詳細的組成

    AI_PADDLE_X_IDX = 0
    BALL_X_IDX = 6
    BALL_Y_IDX = 7 # 假設 ball_y_current_ai_obs 是從 current_state[BALL_Y_IDX] 取得

    ai_paddle_x = current_state[AI_PADDLE_X_IDX]
    ball_x = current_state[BALL_X_IDX]
    ball_y_current_ai_obs_from_state = current_state[BALL_Y_IDX]


    hit_ball_this_step = env_info.get('ai_hit_ball', False)
    player1_scored_this_step = env_info.get('scorer') == 'player1' or opponent_lives < prev_opponent_lives
    ai_scored_this_step = env_info.get('scorer') == 'opponent' or player1_lives < prev_player1_lives

    if hit_ball_this_step:
        val = reward_cfg.get('hit_ball_reward', 0.0)
        reward += val
        # reward_components['hit_ball'] = val

    if player1_scored_this_step:
        val = reward_cfg.get('player_scored_penalty', 0.0)
        reward += val
        # reward_components['scored_upon'] = val
    elif ai_scored_this_step:
        val = reward_cfg.get('ai_scored_reward', 0.0)
        reward += val
        # reward_components['ai_scored'] = val

    if not hit_ball_this_step and not player1_scored_this_step and not ai_scored_this_step and not done:
        dist_x = abs(ai_paddle_x - ball_x)
        if reward_cfg.get('enable_x_align_penalty', False):
            penalty_val = dist_x * reward_cfg.get('x_align_penalty_factor', 0.0)
            reward -= penalty_val
            # reward_components['penalty_dist_x'] = -penalty_val

        if reward_cfg.get('enable_y_shaping', False): # 根據 train_config.yaml 這裡是 false
            effective_reach_y = reward_cfg.get('y_paddle_effective_reach', 0.3)
            prepared_reward_val = reward_cfg.get('y_prepared_to_hit_reward', 0.0)
            good_dist_x = reward_cfg.get('y_good_dist_x_for_bonus', 0.1)
            if ball_y_current_ai_obs_from_state < effective_reach_y and ball_y_current_ai_obs_from_state >= 0:
                if dist_x < good_dist_x:
                    reward += prepared_reward_val
                    # reward_components['prepared_to_hit_bonus'] = prepared_reward_val

        if reward_cfg.get('enable_edge_penalty', False): # 根據 train_config.yaml 這裡是 true 但因子為 0
            zone_width = reward_cfg.get('edge_penalty_zone_width', 0.05)
            penalty_scale = reward_cfg.get('edge_penalty_scale', 0.1)
            edge_penalty_val = 0.0
            if ai_paddle_x < zone_width:
                edge_penalty_val = (zone_width - ai_paddle_x) / zone_width * penalty_scale
            elif ai_paddle_x > (1.0 - zone_width):
                edge_penalty_val = (ai_paddle_x - (1.0 - zone_width)) / zone_width * penalty_scale
            if edge_penalty_val > 0:
                reward -= edge_penalty_val
                # reward_components['penalty_edge_zone'] = -edge_penalty_val

    if reward_cfg.get('enable_time_penalty', False): # 根據 train_config.yaml 這裡是 true 但因子為 0
        val = reward_cfg.get('time_penalty_per_step', 0.0)
        reward += val
        # reward_components['time_penalty'] = val

    return reward # 評估時只需要總獎勵


def evaluate_single_model(model_path, train_cfg, eval_episodes, max_timesteps_per_episode, device):
    """評估單個模型並返回平均獎勵。"""
    print(f"\n--- 正在評估模型: {model_path} ---")

    cfg_general = train_cfg['general']
    cfg_reward = train_cfg['reward_function']
    cfg_network = train_cfg['network'] # Actor 初始化需要

    obs_dim = cfg_general['obs_dim']
    action_dim = cfg_general['action_dim']

    # --- 初始化環境 (與訓練時類似，但不渲染) ---
    game_cfg_manager_eval = GameConfigManager() # 每個評估可能有獨立的實例
    GameSettings._config_manager = game_cfg_manager_eval

    # 使用 level1.yaml 作為評估的基準環境配置
    level1_yaml_path = "models/level1.yaml"
    common_game_cfg_eval = {}
    if os.path.exists(resource_path(level1_yaml_path)):
        common_game_cfg_eval = game_cfg_manager_eval.get_level_config(os.path.basename(level1_yaml_path))
        if common_game_cfg_eval is None: common_game_cfg_eval = {}
        print(f"  使用 Level 1 的 common_config 進行評估。")
    else:
        print(f"  警告: {level1_yaml_path} 未找到。評估時使用預設 common_config。")
        common_game_cfg_eval.setdefault('initial_speed', 0.02)
        common_game_cfg_eval.setdefault('player_life', 3)
        common_game_cfg_eval.setdefault('ai_life', 3)
        common_game_cfg_eval.setdefault('player_paddle_width', 100) # 確保這些值存在
        common_game_cfg_eval.setdefault('ai_paddle_width', 60)


    player1_env_config_eval = {
        'initial_x': 0.5,
        'initial_paddle_width': common_game_cfg_eval.get('player_paddle_width', 100),
        'initial_lives': common_game_cfg_eval.get('player_life', 3),
        'skill_code': None, 'is_ai': False
    }
    opponent_env_config_eval = { # 這是被評估的 AI
        'initial_x': 0.5,
        'initial_paddle_width': common_game_cfg_eval.get('ai_paddle_width', 60), # 確保與訓練時一致
        'initial_lives': common_game_cfg_eval.get('ai_life', 3),
        'skill_code': None, 'is_ai': True
    }

    env = PongDuelEnv(
        game_mode=GameSettings.GameMode.PLAYER_VS_AI,
        player1_config=player1_env_config_eval,
        opponent_config=opponent_env_config_eval,
        common_config=common_game_cfg_eval,
        render_size=400, # 與訓練時的 env 內部邏輯尺寸一致
        paddle_height_px=10,
        ball_radius_px=10,
        initial_main_screen_surface_for_renderer=None # 不渲染
    )

    # --- 載入 Actor 模型 ---
    actor_net = Actor(obs_dim, action_dim, cfg_network).to(device)
    try:
        checkpoint = torch.load(model_path, map_location=device)
        # 我們只需要 actor 的權重來進行評估
        if 'actor_state_dict' in checkpoint:
            actor_net.load_state_dict(checkpoint['actor_state_dict'])
            actor_net.eval() # 設定為評估模式
            print(f"  成功從 {model_path} 載入 Actor 網路權重。")
        else:
            print(f"  錯誤: 模型檔案 {model_path} 中未找到 'actor_state_dict'。")
            return -float('inf') # 返回一個極小值表示載入失敗
    except Exception as e:
        print(f"  錯誤: 載入模型 {model_path} 失敗: {e}")
        return -float('inf')

    total_rewards_for_model = 0
    for i_episode in range(1, eval_episodes + 1):
        state, _ = env.reset()
        current_episode_reward = 0

        # 與 train_ppo_agent 中獎勵計算相關的變數初始化
        ball_y_in_obs_idx = 7 # Ball Y 在觀察向量中的索引
        prev_ball_y_for_reward = state[ball_y_in_obs_idx]
        prev_p1_lives = env.player1.lives
        prev_opp_lives = env.opponent.lives

        for t in range(max_timesteps_per_episode):
            # AI (opponent) 選擇確定性動作
            with torch.no_grad():
                state_tensor = torch.FloatTensor(state.reshape(1, -1)).to(device)
                action_mean, _ = actor_net(state_tensor, deterministic=True) # 使用確定性動作
                action_opponent_continuous = action_mean.cpu().numpy().flatten()

            # Player 1 的動作 (簡單規則：追球X，與訓練時一致)
            ball_x_in_obs_idx = 6 # Ball X 在觀察向量中的索引
            action_player1_target_x = np.clip(state[ball_x_in_obs_idx], 0.0, 1.0)

            next_state, _, round_done, game_over, info = env.step(
                action_player1_target_x,
                action_opponent_continuous[0] # AI 的動作
            )

            # 計算獎勵 (使用與訓練時相同的獎勵函數)
            # 注意：current_ball_y_obs 應該是 next_state 中的球Y座標
            reward_val = calculate_reward(
                cfg_reward, state, info, (round_done or game_over),
                prev_ball_y_for_reward, next_state[ball_y_in_obs_idx], # 使用 next_state 的球 Y
                env.player1.lives, env.opponent.lives,
                prev_p1_lives, prev_opp_lives
            )
            current_episode_reward += reward_val

            # 更新用於下一輪獎勵計算的變數
            prev_ball_y_for_reward = next_state[ball_y_in_obs_idx]
            prev_p1_lives = env.player1.lives
            prev_opp_lives = env.opponent.lives
            state = next_state

            if game_over:
                break
        
        total_rewards_for_model += current_episode_reward
        # print(f"    回合 {i_episode}/{eval_episodes}, 獎勵: {current_episode_reward:.2f}") # 可選：打印每個回合的獎勵

    avg_reward = total_rewards_for_model / eval_episodes
    print(f"  模型 {os.path.basename(model_path)} 的平均獎勵 ({eval_episodes} 回合): {avg_reward:.2f}")
    return avg_reward


def main():
    parser = argparse.ArgumentParser(description="PPO Pong Agent Evaluation Script")
    parser.add_argument(
        "--config", type=str, default="config/train_config.yaml",
        help="Path to the training configuration YAML file (used for model and env parameters)."
    )
    parser.add_argument(
        "--model_dir", type=str, default="ppo_models", # 預設掃描 ppo_models 資料夾
        help="Directory containing the PPO model files (.pth) to evaluate."
    )
    parser.add_argument(
        "--eval_episodes", type=int, default=20, # 每個模型評估20回合
        help="Number of episodes to run for each model evaluation."
    )
    parser.add_argument(
        "--max_steps", type=int, default=3000, # 每回合最大步數
        help="Maximum number of timesteps per evaluation episode."
    )
    args = parser.parse_args()

    # --- Pygame 最小化初始化 (即使不渲染，環境內部可能也需要) ---
    pygame.init()
    # 創建一個虛擬螢幕，有些 Pygame 功能（如字體）可能需要一個已設定的顯示模式
    # PongDuelEnv 的 renderer 在未提供 surface 時會自己創建，但最好我們控制
    try:
        pygame.display.set_mode((1, 1), pygame.NOFRAME) # 最小化，無框
    except pygame.error as e:
        print(f"警告: 無法設定 Pygame 虛擬顯示模式: {e}。PongDuelEnv 初始化可能會受影響。")


    train_cfg = load_config_from_yaml(args.config)
    if train_cfg is None:
        print("無法載入訓練配置文件，評估終止。")
        pygame.quit()
        return

    # 設定設備
    cfg_general_device = train_cfg.get('general', {}).get('device', 'auto')
    if cfg_general_device == "auto":
        device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    elif cfg_general_device == "cuda" and torch.cuda.is_available():
        device = torch.device("cuda")
    else:
        device = torch.device("cpu")
    print(f"使用設備進行評估: {device}")

    # 設定隨機種子 (如果訓練配置中有)
    seed_val = train_cfg.get('general', {}).get('seed', None)
    if seed_val is not None:
        # 為了評估時的環境一致性，也可以設定種子
        # 但如果想評估模型的泛化能力，可以考慮不設定或使用不同的種子
        torch.manual_seed(seed_val + 1) # 使用與訓練不同的種子以測試泛化 (可選)
        np.random.seed(seed_val + 1)
        random.seed(seed_val + 1)
        print(f"評估時設定了隨機種子 (與訓練種子不同，如果訓練時有設定)。")


    model_folder_path = resource_path(args.model_dir)
    if not os.path.isdir(model_folder_path):
        print(f"錯誤: 模型資料夾 '{model_folder_path}' 不存在。")
        pygame.quit()
        return

    model_files = [f for f in os.listdir(model_folder_path) if f.endswith(".pth")]
    if not model_files:
        print(f"在資料夾 '{model_folder_path}' 中沒有找到 .pth 模型檔案。")
        pygame.quit()
        return

    print(f"\n將在資料夾 '{model_folder_path}' 中評估以下模型:")
    for mf in model_files:
        print(f"  - {mf}")

    results = {}
    for model_file in sorted(model_files): # 排序以確保一致的評估順序
        full_model_path = os.path.join(model_folder_path, model_file)
        avg_reward = evaluate_single_model(
            full_model_path,
            train_cfg,
            args.eval_episodes,
            args.max_steps,
            device
        )
        results[model_file] = avg_reward

    print("\n--- 所有模型評估結果 ---")
    # 按平均獎勵降序排序
    sorted_results = sorted(results.items(), key=lambda item: item[1], reverse=True)
    for model_name, avg_rew in sorted_results:
        print(f"模型: {model_name:<40} | 平均獎勵: {avg_rew:>8.2f}")

    pygame.quit() # 確保 Pygame 被正確關閉

if __name__ == '__main__':
    main()