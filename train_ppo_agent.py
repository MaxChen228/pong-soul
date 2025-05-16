import torch
import torch.nn as nn
import torch.optim as optim
from torch.distributions import Normal # 用於連續動作的隨機抽樣
import numpy as np
import os
import pygame # PongDuelEnv 需要 pygame

# 從專案中導入必要的類別
from envs.pong_duel_env import PongDuelEnv
from game.settings import GameSettings # PongDuelEnv 可能會間接使用
from game.config_manager import ConfigManager # PongDuelEnv 可能需要
from utils import resource_path # AIAgent 和 PongDuelEnv 可能需要

# --- Actor-Critic 網路定義 ---
# 注意：這個 Actor 網路與 game/ai_agent.py 中的 QNet (現在輸出連續動作) 角色類似。
# 在 PPO 中，我們通常明確區分 Actor 和 Critic。
# 您可以選擇將 game/ai_agent.py 中的 QNet 直接用作此處的 Actor，或者重新定義。
# 為了訓練的獨立性，這裡重新定義 Actor 和 Critic。

def init_weights(m):
    if isinstance(m, nn.Linear):
        nn.init.orthogonal_(m.weight.data, gain=nn.init.calculate_gain('relu'))
        if m.bias is not None:
            nn.init.constant_(m.bias.data, 0)

class Actor(nn.Module):
    def __init__(self, state_dim, action_dim, hidden_dim=128, log_std_min=-20, log_std_max=2):
        super(Actor, self).__init__()
        self.log_std_min = log_std_min
        self.log_std_max = log_std_max
        
        self.net = nn.Sequential(
            nn.Linear(state_dim, hidden_dim),
            nn.ReLU(),
            nn.Linear(hidden_dim, hidden_dim),
            nn.ReLU()
        )
        # 輸出動作的均值
        self.mean_layer = nn.Linear(hidden_dim, action_dim)
        # 輸出動作的對數標準差 (可訓練參數)
        self.log_std_layer = nn.Linear(hidden_dim, action_dim) # 或者使用 nn.Parameter(torch.zeros(1, action_dim))

        self.apply(init_weights)

    def forward(self, state):
        x = self.net(state)
        mean = self.mean_layer(x)
        
        # 讓 log_std 也是網路的一部分，或者作為獨立的可訓練參數
        log_std = self.log_std_layer(x)
        log_std = torch.clamp(log_std, self.log_std_min, self.log_std_max)
        # std = torch.exp(log_std) # 標準差必須是正數
        
        return mean, log_std

class Critic(nn.Module):
    def __init__(self, state_dim, hidden_dim=128):
        super(Critic, self).__init__()
        self.net = nn.Sequential(
            nn.Linear(state_dim, hidden_dim),
            nn.ReLU(),
            nn.Linear(hidden_dim, hidden_dim),
            nn.ReLU(),
            nn.Linear(hidden_dim, 1) # 輸出一個狀態價值 V(s)
        )
        self.apply(init_weights)

    def forward(self, state):
        return self.net(state)

class PPOAgent:
    def __init__(self, state_dim, action_dim, lr_actor=3e-4, lr_critic=1e-3, gamma=0.99, K_epochs=10, eps_clip=0.2, gae_lambda=0.95, hidden_dim=128, action_std_init=0.6):
        self.gamma = gamma
        self.eps_clip = eps_clip
        self.K_epochs = K_epochs
        self.gae_lambda = gae_lambda

        self.actor = Actor(state_dim, action_dim, hidden_dim).to(device)
        self.critic = Critic(state_dim, hidden_dim).to(device)
        
        self.optimizer_actor = optim.Adam(self.actor.parameters(), lr=lr_actor)
        self.optimizer_critic = optim.Adam(self.critic.parameters(), lr=lr_critic)

        # 用於儲存舊策略網路的參數，PPO 需要 actor_old 來計算比例
        self.actor_old = Actor(state_dim, action_dim, hidden_dim).to(device)
        self.actor_old.load_state_dict(self.actor.state_dict())
        
        self.mse_loss = nn.MSELoss()

        # 動作標準差的初始化 (對於連續動作)
        # 如果 log_std 是網路輸出，則不需要這個
        # self.action_log_std = nn.Parameter(torch.ones(1, action_dim) * np.log(action_std_init)).to(device)


    def select_action(self, state):
        with torch.no_grad():
            state_tensor = torch.FloatTensor(state.reshape(1, -1)).to(device)
            mean, log_std = self.actor_old(state_tensor) # 從舊策略中採樣
            std = torch.exp(log_std)
            
            dist = Normal(mean, std)
            action = dist.sample()
            action_log_prob = dist.log_prob(action)
            
            # 將動作限制在環境的有效範圍內，例如 Pong 球拍目標X是 [0, 1]
            # Actor 網路的輸出 mean 本身沒有 tanh，所以 dist.sample() 可能超出範圍
            # 通常 Actor 的最後一層會加 tanh 讓 mean 在 [-1, 1]
            # 然後再根據環境的 action_scale 和 action_bias 調整
            # 假設我們的 PongEnv 動作是正規化的 [0,1] 目標位置
            # 如果 Actor 的 mean_layer 後面沒有 tanh:
            action_clipped = torch.clamp(mean + std * torch.randn_like(std), 0.0, 1.0) # 一種處理方式
            # 或者，如果 Actor 的 mean_layer 後面有 tanh，輸出 action_mean in [-1,1]
            # action_env_scale = 0.5 # (upper_bound - lower_bound) / 2
            # action_env_bias = 0.5 # (upper_bound + lower_bound) / 2
            # action_final = torch.tanh(action) * action_env_scale + action_env_bias

            # 簡化：假設 Actor 的 forward 方法返回的 mean 已經是 [0,1] (例如內部有 (tanh+1)/2 )
            # 或者我們在這裡 clip
            # 如果 Actor 的 forward 返回的是 (-inf, inf) 的 mean, 和 log_std
            # 我們的 game.ai_agent.py 中的 QNet/Actor 是輸出了 [0,1] 的均值
            # 但這裡的 Actor 網路輸出 mean 和 log_std，需要從 Normal 分佈中採樣
            # 採樣後的值可能是任意的，需要 clip
            
            # 假設我們的環境動作是單一維度 [0,1]
            # PPO 的 Actor 通常輸出分佈的參數 (mean, std)，而不是直接的動作值然後加噪聲
            # 讓我們假設 Actor 輸出的 mean 是 [-inf, inf]，std 是正的
            # 採樣後的值 action 需要被 clip 到 [0,1] for Pong target X
            # 並且，為了計算 log_prob，我們通常不對 action 本身做 tanh 轉換後再給 Normal distribution
            # 而是 Normal distribution 產生動作，然後再 clip / scale 到環境範圍

            action_env = torch.clamp(action, 0.0, 1.0)

        return action_env.cpu().numpy().flatten(), action_log_prob.cpu()

    def update(self, memory):
        # Monte Carlo estimate of returns
        rewards = []
        discounted_reward = 0
        for reward, is_terminal in zip(reversed(memory.rewards), reversed(memory.is_terminals)):
            if is_terminal:
                discounted_reward = 0
            discounted_reward = reward + (self.gamma * discounted_reward)
            rewards.insert(0, discounted_reward)
            
        # Normalizing the rewards
        rewards = torch.tensor(rewards, dtype=torch.float32).to(device)
        rewards = (rewards - rewards.mean()) / (rewards.std() + 1e-7)

        # convert list to tensor
        old_states = torch.squeeze(torch.stack(memory.states, dim=0)).detach().to(device)
        old_actions = torch.squeeze(torch.stack(memory.actions, dim=0)).detach().to(device)
        old_log_probs = torch.squeeze(torch.stack(memory.log_probs, dim=0)).detach().to(device)
        
        # Optimize policy for K epochs
        for _ in range(self.K_epochs):
            # Evaluating old actions and values
            mean_new, log_std_new = self.actor(old_states)
            std_new = torch.exp(log_std_new)
            dist_new = Normal(mean_new, std_new)
            
            # Action log probabilities
            log_probs_new = dist_new.log_prob(old_actions)
            
            # State values V(s)
            state_values = self.critic(old_states)
            state_values = torch.squeeze(state_values)

            # Importance PPO Ratio: r_t(theta) = pi_theta(a_t | s_t) / pi_theta_k(a_t | s_t)
            ratios = torch.exp(log_probs_new - old_log_probs.detach())

            # Advantages A_t = R_t - V(s_t)
            advantages = rewards - state_values.detach()
            # Normalize advantages (optional but often helpful)
            advantages = (advantages - advantages.mean()) / (advantages.std() + 1e-7)
            
            # Surrogate Loss (PPO-Clip objective)
            surr1 = ratios * advantages
            surr2 = torch.clamp(ratios, 1 - self.eps_clip, 1 + self.eps_clip) * advantages
            
            # Actor loss
            loss_actor = -torch.min(surr1, surr2).mean()
            
            # Critic loss (Value function loss)
            loss_critic = self.mse_loss(state_values, rewards) # V(s) should approximate R_t
            
            # Entropy loss (optional, for exploration)
            dist_entropy = dist_new.entropy().mean()
            loss_entropy = -0.01 * dist_entropy # 0.01 is a common coefficient

            # Total loss for actor
            total_actor_loss = loss_actor + loss_entropy

            # Update actor
            self.optimizer_actor.zero_grad()
            total_actor_loss.backward()
            self.optimizer_actor.step()
            
            # Update critic
            self.optimizer_critic.zero_grad()
            loss_critic.backward()
            self.optimizer_critic.step()
            
        # Copy new weights into old policy: theta_k+1 <- theta_k
        self.actor_old.load_state_dict(self.actor.state_dict())
        
        # Clear memory
        memory.clear_memory()


class Memory:
    def __init__(self):
        self.actions = []
        self.states = []
        self.log_probs = []
        self.rewards = []
        self.is_terminals = []

    def clear_memory(self):
        del self.actions[:]
        del self.states[:]
        del self.log_probs[:]
        del self.rewards[:]
        del self.is_terminals[:]

# --- 設定與常數 ---
device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
OBS_DIM = 15  # 根據我們最新的 _get_obs()
ACTION_DIM = 1 # 連續目標X座標
MAX_EPISODES = 10000
MAX_TIMESTEPS_PER_EPISODE = 1000 # 每回合最大步數
UPDATE_TIMESTEPS = 4096  # 每收集這麼多步數後更新一次網路
SAVE_MODEL_FREQ = 500000 # 每多少步儲存一次模型 (或者按 episode)
MODEL_DIR = "ppo_models" # 模型儲存目錄
os.makedirs(MODEL_DIR, exist_ok=True)
MODEL_NAME_PREFIX = "ppo_pong_strategic_ai"

# PPO 超參數 (可以調整)
LR_ACTOR = 0.0003
LR_CRITIC = 0.001
GAMMA = 0.99           # 折扣因子
K_EPOCHS = 10          # 每次更新時，用同一批數據訓練的次數
EPS_CLIP = 0.2         # PPO 裁剪參數
GAE_LAMBDA = 0.95      # GAE lambda 參數
ACTION_STD_INIT = 0.5  # 初始動作標準差 (如果 log_std 不是網路輸出)
HIDDEN_DIM_NETS = 256  # 網路隱藏層大小

# --- 獎勵函數設計 ---
def calculate_reward(env_info, done, prev_ball_y, current_ball_y, player1_lives, opponent_lives, prev_player1_lives, prev_opponent_lives):
    reward = 0.0

    # 1. 基本得分/失分獎勵
    if done:
        if env_info.get('scorer') == 'player1': # AI (opponent) 失分
            reward -= 15.0
            # print(f"Train: AI lost a point. Reward: -15") # <--- 註解或刪除
        elif env_info.get('scorer') == 'opponent': # AI (opponent) 得分
            reward += 15.0
            # print(f"Train: AI scored a point! Reward: +15") # <--- 註解或刪除
        elif opponent_lives < prev_opponent_lives:
            reward -= 15.0 # AI 失分
            # print(f"Train: AI lost a point (lives decreased). Reward: -15") # <--- 註解或刪除
        elif player1_lives < prev_player1_lives:
            reward += 15.0 # AI 得分
            # print(f"Train: AI scored a point (P1 lives decreased)! Reward: +15") # <--- 註解或刪除

    ball_progress_to_opponent = current_ball_y - prev_ball_y
    if ball_progress_to_opponent > 0:
        reward += ball_progress_to_opponent * 2.0
    else:
        reward += ball_progress_to_opponent * 1.0

    if env_info.get('last_hit_by') == 'opponent':
        reward += 0.5
        # print(f"Train: AI hit the ball. Reward: +0.5") # <--- 註解或刪除
        ball_x_after_hit = env_info.get('ball_x_after_hit_by_opponent', 0.5)
        if ball_x_after_hit < 0.2 or ball_x_after_hit > 0.8:
            reward += 1.0
            # print(f"Train: AI hit to corner! x={ball_x_after_hit:.2f}. Reward: +1.0") # <--- 註解或刪除
    
    return reward


# --- 訓練主函數 ---
def train():
    print(f"開始訓練，使用設備: {device}")
    print(f"觀察空間維度: {OBS_DIM}, 動作空間維度: {ACTION_DIM}")

    # 初始化 Pygame （PongDuelEnv 可能需要）
    pygame.init()
    pygame.display.set_mode((1,1)) # 創建一個虛擬螢幕，避免 "No video mode has been set"

    # 初始化 ConfigManager (PongDuelEnv 初始化時需要)
    config_manager = ConfigManager()
    GameSettings._config_manager = config_manager # 關鍵步驟

    # 初始化環境
    # PongDuelEnv 的初始化需要 player1_config, opponent_config, common_config
    # 我們訓練的是 AI (opponent)，所以 P1 可以是一個簡單的固定策略對手或也由AI控制 (self-play)
    # 為了簡化，讓P1使用固定的簡單策略，例如總是嘗試跟隨球的X座標
    # 或者，我們可以讓 P1 也由一個簡單的 agent 控制，或者在這個訓練腳本中不控制P1的輸入，
    # 而是讓 P1 的 action 總是 "stay" 或基於簡單規則。
    # PongDuelEnv.step() 需要 player1_target_x_norm_input

    # 環境配置
    # 這裡我們選擇 PvA 模式，AI 是 opponent
    # common_config 可以從一個預設的 level YAML 讀取，或手動定義
    # 假設使用 Level 1 的設定作為基礎
    # 確保 'models' 資料夾和 'level1.yaml' 存在，或者提供一個預設的 common_config
    level1_yaml_path = "models/level1.yaml" # resource_path 會處理
    common_game_cfg = {}
    if os.path.exists(resource_path(level1_yaml_path)):
        common_game_cfg = config_manager.get_level_config("level1.yaml")
        if common_game_cfg is None: common_game_cfg = {}
        print(f"使用 Level 1 的 common_config: {common_game_cfg}")
    else:
        print(f"警告: {level1_yaml_path} 未找到，使用空的 common_config。")
        # 提供一些基礎預設值，以防 level1.yaml 不存在或內容不全
        common_game_cfg.setdefault('initial_speed', 0.02)
        common_game_cfg.setdefault('initial_angle_deg_range', [-60, 60])
        common_game_cfg.setdefault('player_life', 3)
        common_game_cfg.setdefault('ai_life', 3)
        common_game_cfg.setdefault('player_paddle_width', 100)
        common_game_cfg.setdefault('ai_paddle_width', 60)


    player1_env_config = {
        'initial_x': 0.5,
        'initial_paddle_width': common_game_cfg.get('player_paddle_width', 100),
        'initial_lives': common_game_cfg.get('player_life', 3),
        'skill_code': None, # 訓練時 P1 無技能
        'is_ai': False # P1 是人類（或由簡單規則控制）
    }
    # AI (opponent) 的設定
    opponent_env_config = {
        'initial_x': 0.5,
        'initial_paddle_width': common_game_cfg.get('ai_paddle_width', 60),
        'initial_lives': common_game_cfg.get('ai_life', 3),
        'skill_code': None, # 訓練時 AI 無技能
        'is_ai': True # 表明這是 AI 控制的球拍
    }

    env = PongDuelEnv(
        game_mode=GameSettings.GameMode.PLAYER_VS_AI,
        player1_config=player1_env_config,
        opponent_config=opponent_env_config,
        common_config=common_game_cfg,
        render_size=400, # 與遊戲中 GameplayState 初始化 Env 時一致
        paddle_height_px=10,
        ball_radius_px=10,
        initial_main_screen_surface_for_renderer=None # 訓練時不渲染到主螢幕
    )
    # PongDuelEnv 的 renderer 在訓練時不需要實際的螢幕 surface，
    # 它會在首次調用 env.render() 時嘗試創建一個（如果我們調用它）。
    # 為了訓練，我們通常不調用 env.render() 以加速。

    ppo_agent = PPOAgent(OBS_DIM, ACTION_DIM, LR_ACTOR, LR_CRITIC, GAMMA, K_EPOCHS, EPS_CLIP, GAE_LAMBDA, HIDDEN_DIM_NETS)
    memory = Memory()

    time_step_counter = 0
    episode_count = 0
    
    # 載入之前的模型 (如果存在)
    start_episode = 0
    checkpoint_path = os.path.join(MODEL_DIR, f"{MODEL_NAME_PREFIX}_latest.pth")
    if os.path.exists(checkpoint_path):
        print(f"載入先前儲存的模型: {checkpoint_path}")
        checkpoint = torch.load(checkpoint_path, map_location=device)
        ppo_agent.actor_old.load_state_dict(checkpoint['actor_state_dict'])
        ppo_agent.actor.load_state_dict(checkpoint['actor_state_dict'])
        ppo_agent.critic.load_state_dict(checkpoint['critic_state_dict'])
        ppo_agent.optimizer_actor.load_state_dict(checkpoint['optimizer_actor_state_dict'])
        ppo_agent.optimizer_critic.load_state_dict(checkpoint['optimizer_critic_state_dict'])
        time_step_counter = checkpoint.get('time_step_counter', 0)
        start_episode = checkpoint.get('episode_count', 0)
        print(f"從 episode {start_episode}, time_step {time_step_counter} 繼續訓練。")

    recent_rewards = []
    # --- 訓練迴圈 ---
    for i_episode in range(start_episode + 1, MAX_EPISODES + 1):
        episode_count = i_episode
        state, _ = env.reset() 
        current_ep_reward = 0
        
        # ⭐️ 確保 ball_y_in_obs_idx 與您的 _get_obs() 匹配 (我們上次確認是7)
        ball_y_in_obs_idx = 7 # 假設 Ball Y 在觀察向量中的索引是 7
        if state.shape[0] <= ball_y_in_obs_idx:
            print(f"錯誤：觀察維度 ({state.shape[0]}) 過小，無法獲取索引 {ball_y_in_obs_idx} 的 ball_y。請檢查 OBS_DIM 和 _get_obs()。")
            return # 或者拋出錯誤

        prev_ball_y_for_reward = state[ball_y_in_obs_idx] 

        prev_p1_lives = env.player1.lives
        prev_opp_lives = env.opponent.lives

        for t in range(MAX_TIMESTEPS_PER_EPISODE):
            time_step_counter += 1
            
            action_opponent_continuous, action_log_prob = ppo_agent.select_action(state)
            
            ball_x_in_obs_idx = 6 # 假設 Ball X 在觀察向量中的索引是 6
            if state.shape[0] <= ball_x_in_obs_idx:
                 print(f"錯誤：觀察維度 ({state.shape[0]}) 過小，無法獲取索引 {ball_x_in_obs_idx} 的 ball_x。")
                 return
            ball_x_in_obs = state[ball_x_in_obs_idx]
            action_player1_target_x = np.clip(ball_x_in_obs, 0.0, 1.0)

            next_state, _, round_done, game_over, info = env.step(action_player1_target_x, action_opponent_continuous[0])
            
            reward = calculate_reward(info, (round_done or game_over), 
                                      prev_ball_y_for_reward, next_state[ball_y_in_obs_idx],
                                      env.player1.lives, env.opponent.lives,
                                      prev_p1_lives, prev_opp_lives)
            current_ep_reward += reward

            memory.states.append(torch.FloatTensor(state).to(device))
            memory.actions.append(torch.FloatTensor(action_opponent_continuous).to(device))
            memory.log_probs.append(action_log_prob)
            memory.rewards.append(reward)
            memory.is_terminals.append(round_done or game_over)

            if time_step_counter % UPDATE_TIMESTEPS == 0:
                # print(f"  總步數 {time_step_counter}: 更新 PPO 網路...") # 保留這個，比較重要
                ppo_agent.update(memory)
            
            prev_ball_y_for_reward = next_state[ball_y_in_obs_idx]
            prev_p1_lives = env.player1.lives
            prev_opp_lives = env.opponent.lives
            state = next_state
            
            if game_over: # 只有在遊戲真正結束時才跳出內層迴圈
                break 
        n = 50
        # 累計最近獎勵
        recent_rewards.append(current_ep_reward)
        if len(recent_rewards) > n: # 只保留最近10個
            recent_rewards.pop(0)

        # 每 10 個回合打印一次該回合的獎勵和最近10回合的平均獎勵
        if i_episode % n == 0:
            avg_reward_last_10 = np.mean(recent_rewards) if recent_rewards else 0.0
            print(f"回合: {i_episode}, 總步數: {time_step_counter}, 本回合獎勵: {current_ep_reward:.2f}, 最近10回平均獎勵: {avg_reward_last_10:.2f}")

        # 定期儲存模型 (保持不變)
        if i_episode % (SAVE_MODEL_FREQ // MAX_TIMESTEPS_PER_EPISODE if MAX_TIMESTEPS_PER_EPISODE > 0 else SAVE_MODEL_FREQ) == 0 or i_episode == MAX_EPISODES:
            # ... (儲存模型的邏輯不變) ...
            path = os.path.join(MODEL_DIR, f"{MODEL_NAME_PREFIX}_episode_{i_episode}.pth")
            latest_path = os.path.join(MODEL_DIR, f"{MODEL_NAME_PREFIX}_latest.pth")
            
            print(f"儲存模型到 {path}") # 保留儲存模型的打印
            torch.save({
                'episode_count': i_episode,
                'time_step_counter': time_step_counter,
                'actor_state_dict': ppo_agent.actor.state_dict(),
                'critic_state_dict': ppo_agent.critic.state_dict(),
                'optimizer_actor_state_dict': ppo_agent.optimizer_actor.state_dict(),
                'optimizer_critic_state_dict': ppo_agent.optimizer_critic.state_dict(),
            }, path)
            torch.save({ # 也更新 latest
                'episode_count': i_episode,
                'time_step_counter': time_step_counter,
                'actor_state_dict': ppo_agent.actor.state_dict(),
                'critic_state_dict': ppo_agent.critic.state_dict(),
                'optimizer_actor_state_dict': ppo_agent.optimizer_actor.state_dict(),
                'optimizer_critic_state_dict': ppo_agent.optimizer_critic.state_dict(),
            }, latest_path)


    print("訓練完成。")
    env.close()
    pygame.quit()


if __name__ == '__main__':
    # 為了讓 utils.resource_path 能正確工作，可能需要確保當前工作目錄是專案根目錄
    # 或者在 utils.py 中處理好相對路徑的解析
    # 通常，如果 train_ppo_agent.py 在專案根目錄下執行，resource_path(".") 會是根目錄
    
    # 設置Pygame環境變數以在無頭伺服器上運行（如果需要）
    # os.environ["SDL_VIDEODRIVER"] = "dummy"
    
    train()