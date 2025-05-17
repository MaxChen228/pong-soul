# train_imitation.py
import torch
import torch.nn as nn
import torch.optim as optim
from torch.utils.data import DataLoader, TensorDataset
import numpy as np
import os
import pygame # Pygame 始終導入
import yaml
import argparse
import random
import time
from tqdm import tqdm # 用於顯示進度條

# --- 從你的專案中導入必要的模塊 ---
# 假設 train_ppo_agent.py 和此腳本在同一目錄，或者相關路徑已配置好
try:
    from train_ppo_agent import Actor, load_config_from_yaml, init_weights # Actor 和配置加載函數
except ImportError:
    print("錯誤：無法從 train_ppo_agent.py 導入 Actor, load_config_from_yaml, init_weights。請確保它們在正確的路徑下。")
    exit(1)

from envs.pong_duel_env import PongDuelEnv
from game.settings import GameSettings
from game.config_manager import ConfigManager as GameConfigManager
from utils import resource_path

# 全域變數
device = None
imitation_train_config = None # 將用於模仿學習的配置

def generate_expert_data(env, num_episodes, max_timesteps_per_episode, expert_player_is_opponent=True):
    """
    生成專家數據。
    :param env: PongDuelEnv 實例。
    :param num_episodes: 要運行的回合數。
    :param max_timesteps_per_episode: 每回合最大步數。
    :param expert_player_is_opponent: 專家是否是 opponent (AI 的角色)。True 表示 opponent 是專家。
    :return: (states, actions) numpy 數組。
    """
    states_data = []
    actions_data = []
    ball_x_in_obs_idx = 6  # 球的X座標在觀察向量中的索引 (根據 _get_obs)

    print(f"\n開始生成專家數據，共 {num_episodes} 回合...")
    for i_episode in tqdm(range(num_episodes), desc="生成數據回合"):
        state, _ = env.reset()
        for t in range(max_timesteps_per_episode):
            # --- 專家動作 ---
            # 專家 (AI opponent) 的動作：直接跟隨球的 X 座標
            # 假設 ball_x_in_obs_idx 是正確的球 X 座標索引
            if state.shape[0] <= ball_x_in_obs_idx:
                 print(f"警告: 觀察維度 ({state.shape[0]}) 過小，無法獲取球的X座標於索引 {ball_x_in_obs_idx}。跳過此步。")
                 # 或者可以採取其他措施，例如讓專家使用一個預設動作
                 expert_action_opponent = 0.5 # 安全回退
            else:
                ball_x_for_expert = state[ball_x_in_obs_idx]
                expert_action_opponent = np.clip(ball_x_for_expert, 0.0, 1.0)

            # --- 另一個玩家的動作 (例如，一個簡單的固定對手或隨機對手) ---
            # 為了數據多樣性，另一個玩家 (這裡假設是 player1) 的行為也應該定義。
            # 如果專家是 opponent，那麼 player1 的動作可以是：
            # 1. 與專家相同的邏輯 (兩個專家對打)
            # 2. 隨機動作
            # 3. 保持不動或簡單追球
            # 這裡我們讓 player1 也簡單追球，但可以加入一些擾動
            if state.shape[0] > ball_x_in_obs_idx:
                action_player1_target_x = np.clip(state[ball_x_in_obs_idx] + random.uniform(-0.1, 0.1), 0.0, 1.0)
            else:
                action_player1_target_x = 0.5


            # 記錄的是 "專家" (我們希望模仿的那個玩家) 的 state 和 action
            if expert_player_is_opponent:
                states_data.append(state.copy()) # 記錄 opponent 看到的 state
                actions_data.append(expert_action_opponent) # 記錄 opponent 執行的 action
            else: # 如果專家是 player1 (不常見於訓練 AI 對手的情況，但作為示例)
                # 注意：如果專家是 player1，你需要調整 _get_obs() 或傳遞 player1 的視角
                # 為了簡化，我們假設專家始終是 opponent (AI 的角色)
                pass

            next_state, _, round_done, game_over, _ = env.step(action_player1_target_x, expert_action_opponent)
            state = next_state

            if game_over:
                break
    
    print(f"專家數據生成完畢。共收集到 {len(states_data)} 個樣本。")
    return np.array(states_data, dtype=np.float32), np.array(actions_data, dtype=np.float32).reshape(-1, 1)

def train_actor_with_imitation(actor_model, states, actions, train_cfg_il, network_cfg_from_main_config):
    """
    使用專家數據訓練 Actor 模型。
    :param actor_model: Actor 網路實例。
    :param states: 專家狀態數據。
    :param actions: 專家動作數據。
    :param train_cfg_il: 包含模仿學習超參數的配置字典 (例如 epochs, batch_size, lr)。
    :param network_cfg_from_main_config: 從主 train_config.yaml 讀取的 network 配置，Actor 初始化時已使用。
    """
    epochs = train_cfg_il.get('epochs', 50)
    batch_size = train_cfg_il.get('batch_size', 64)
    learning_rate = train_cfg_il.get('lr', 0.0005) # 模仿學習的學習率可以稍高

    print(f"\n開始模仿學習訓練...")
    print(f"  總 Epochs: {epochs}, Batch Size: {batch_size}, Learning Rate: {learning_rate}")

    optimizer = optim.Adam(actor_model.parameters(), lr=learning_rate)
    criterion = nn.MSELoss()

    dataset = TensorDataset(torch.from_numpy(states).float().to(device),
                            torch.from_numpy(actions).float().to(device))
    dataloader = DataLoader(dataset, batch_size=batch_size, shuffle=True)

    actor_model.train() # 設置為訓練模式

    for epoch in range(epochs):
        epoch_loss = 0.0
        num_batches = 0
        for batch_states, batch_actions in tqdm(dataloader, desc=f"Epoch {epoch+1}/{epochs}", leave=False):
            optimizer.zero_grad()
            # Actor 的 forward 方法返回 (mean, log_std)
            # 模仿學習時，我們只關心 mean (即預測的動作)
            predicted_actions_mean, _ = actor_model(batch_states) # Actor.forward() returns mean and log_std
            
            loss = criterion(predicted_actions_mean, batch_actions)
            loss.backward()
            optimizer.step()
            
            epoch_loss += loss.item()
            num_batches += 1
        
        avg_epoch_loss = epoch_loss / num_batches if num_batches > 0 else 0
        print(f"Epoch [{epoch+1}/{epochs}], 平均損失 (MSE): {avg_epoch_loss:.6f}")

    actor_model.eval() # 訓練結束後設置回評估模式
    print("模仿學習訓練完成。")

def main():
    global device, imitation_train_config

    parser = argparse.ArgumentParser(description="Imitation Learning for PPO Pong Agent")
    parser.add_argument(
        "--config", type=str, default="config/train_config.yaml",
        help="Path to the main training configuration YAML file (used for env and network setup)."
    )
    parser.add_argument(
        "--il_config", type=str, default="config/imitation_config.yaml", # 新增：模仿學習專用配置文件
        help="Path to the imitation learning specific configuration YAML file."
    )
    parser.add_argument(
        "--output_model_name", type=str, default="il_actor_pretrained.pth",
        help="Filename for the saved pre-trained actor model."
    )
    args = parser.parse_args()

    # 1. 加載主訓練配置 (用於環境和網路結構)
    main_train_cfg = load_config_from_yaml(args.config)
    if main_train_cfg is None: return

    # 2. 加載模仿學習專用配置
    try:
        with open(resource_path(args.il_config), 'r', encoding='utf-8') as f:
            imitation_train_config = yaml.safe_load(f)
        print(f"成功從 {args.il_config} 加載模仿學習配置。")
    except FileNotFoundError:
        print(f"錯誤: 模仿學習配置文件 {args.il_config} 未找到。請創建一個，或使用預設值。")
        # 提供一些預設值，以防配置文件不存在
        imitation_train_config = {
            'data_generation': {'num_episodes': 100, 'max_timesteps_per_episode': 2000},
            'training': {'epochs': 30, 'batch_size': 128, 'lr': 0.001}
        }
        print(f"使用預設模仿學習配置: {imitation_train_config}")
    except yaml.YAMLError as e:
        print(f"錯誤: 解析模仿學習配置文件 {args.il_config} 失敗: {e}")
        return
    except Exception as e:
        print(f"錯誤: 加載模仿學習配置文件 {args.il_config} 時發生未知錯誤: {e}")
        return


    # 設定設備
    cfg_general_device = main_train_cfg.get('general', {}).get('device', 'auto')
    if cfg_general_device == "auto":
        device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    elif cfg_general_device == "cuda" and torch.cuda.is_available():
        device = torch.device("cuda")
    else:
        device = torch.device("cpu")
    print(f"使用設備: {device}")

    # 設定隨機種子 (與主訓練配置一致，以確保環境的可復現性)
    seed_val = main_train_cfg.get('general', {}).get('seed', None)
    if seed_val is not None:
        torch.manual_seed(seed_val)
        np.random.seed(seed_val)
        random.seed(seed_val)
        if device.type == 'cuda':
            torch.cuda.manual_seed_all(seed_val)
        print(f"已設定隨機種子 (來自 train_config.yaml): {seed_val}")

    # --- 初始化環境 (與 train_ppo_agent.py 類似) ---
    pygame.init()
    pygame.display.set_mode((1,1)) # 虛擬螢幕

    game_cfg_manager = GameConfigManager()
    GameSettings._config_manager = game_cfg_manager

    level1_yaml_path = "models/level1.yaml"
    common_game_cfg = {}
    if os.path.exists(resource_path(level1_yaml_path)):
        common_game_cfg = game_cfg_manager.get_level_config(os.path.basename(level1_yaml_path))
        if common_game_cfg is None: common_game_cfg = {}
        print(f"使用 Level 1 的 common_config 進行數據生成: {common_game_cfg}")
    else:
        print(f"警告: {level1_yaml_path} 未找到。使用預設 common_config。")
        # 確保這些預設值與 train_ppo_agent.py 中的一致
        common_game_cfg.setdefault('initial_speed', main_train_cfg.get('reward_function', {}).get('initial_ball_speed', 0.02)) # 示例，應從train_config或global_settings獲取
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
    # 對手 (我們要模仿的專家) 的配置
    opponent_env_config = {
        'initial_x': 0.5,
        'initial_paddle_width': common_game_cfg.get('ai_paddle_width', 60), # 應與 PPO 訓練時 AI 球拍寬度一致
        'initial_lives': common_game_cfg.get('ai_life', 3),
        'skill_code': None, 'is_ai': True # 標記為 AI，但其動作由我們的專家邏輯決定
    }

    env = PongDuelEnv(
        game_mode=GameSettings.GameMode.PLAYER_VS_AI,
        player1_config=player1_env_config,
        opponent_config=opponent_env_config, # opponent 即為專家角色
        common_config=common_game_cfg,
        render_size=400, # 應與 train_config.yaml 中的設定匹配
        paddle_height_px=10,
        ball_radius_px=10,
        initial_main_screen_surface_for_renderer=None # 不渲染
    )

    # 3. 生成專家數據
    cfg_data_gen = imitation_train_config.get('data_generation', {})
    expert_states, expert_actions = generate_expert_data(
        env,
        num_episodes=cfg_data_gen.get('num_episodes', 100),
        max_timesteps_per_episode=cfg_data_gen.get('max_timesteps_per_episode', 2000),
        expert_player_is_opponent=True # 因為我們在訓練 AI (opponent)
    )

    if expert_states.size == 0 or expert_actions.size == 0:
        print("錯誤：未能生成任何專家數據。請檢查數據生成邏輯和環境。")
        pygame.quit()
        return

    # 4. 初始化 Actor 模型
    # 使用從 train_config.yaml 讀取的網路配置
    cfg_general_main = main_train_cfg['general']
    cfg_network_main = main_train_cfg['network']
    
    actor_to_train = Actor(
        state_dim=cfg_general_main['obs_dim'],
        action_dim=cfg_general_main['action_dim'],
        network_cfg=cfg_network_main
    ).to(device)
    actor_to_train.apply(init_weights) # 應用權重初始化 (可選，因為之後會被訓練覆蓋)

    # 5. 使用專家數據訓練 Actor
    cfg_il_training_params = imitation_train_config.get('training', {})
    train_actor_with_imitation(actor_to_train, expert_states, expert_actions, cfg_il_training_params, cfg_network_main)

    # 6. 保存訓練好的 Actor 模型
    output_dir = main_train_cfg.get('model_io', {}).get('model_dir', 'ppo_models')
    os.makedirs(resource_path(output_dir), exist_ok=True)
    output_path = resource_path(os.path.join(output_dir, args.output_model_name))
    
    torch.save(actor_to_train.state_dict(), output_path)
    print(f"模仿學習訓練完成的 Actor 模型已保存到: {output_path}")

    env.close()
    pygame.quit()

if __name__ == '__main__':
    main()