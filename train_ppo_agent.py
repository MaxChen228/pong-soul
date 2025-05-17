import torch
import torch.nn as nn
import torch.optim as optim
from torch.distributions import Normal
import numpy as np
import os
import pygame # Pygame 始終導入
import yaml
import argparse
import random
import time # 新增: 用於控制渲染幀率

from envs.pong_duel_env import PongDuelEnv
from game.settings import GameSettings
from game.config_manager import ConfigManager as GameConfigManager
from utils import resource_path

# 全域變數
device = None
train_config = None
# 新增: 用於渲染的 Pygame screen 物件
render_screen = None
# 新增: 用於渲染的 Pygame clock 物件
render_clock = None

# --- 配置加載函數 (保持不變) ---
def load_config_from_yaml(config_path):
    try:
        with open(config_path, 'r', encoding='utf-8') as f:
            cfg = yaml.safe_load(f)
        print(f"成功從 {config_path} 加載訓練配置。")
        return cfg
    except FileNotFoundError:
        print(f"錯誤: 訓練配置文件 {config_path} 未找到。請確保路徑正確。")
        exit(1)
    except yaml.YAMLError as e:
        print(f"錯誤: 解析訓練配置文件 {config_path} 失敗: {e}")
        exit(1)
    except Exception as e:
        print(f"錯誤: 加載訓練配置文件 {config_path} 時發生未知錯誤: {e}")
        exit(1)

# --- Actor-Critic 網路定義 (保持不變) ---
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

    def forward(self, state):
        x = self.net(state)
        mean_before_tanh = self.mean_layer(x)
        mean_tanh = self.tanh(mean_before_tanh)
        mean_scaled_to_0_1 = (mean_tanh + 1.0) / 2.0    
        log_std = self.log_std_layer(x)
        log_std = torch.clamp(log_std, self.log_std_min, self.log_std_max) 
        return mean_scaled_to_0_1, log_std

class Critic(nn.Module):
    def __init__(self, state_dim, network_cfg):
        super(Critic, self).__init__()
        hidden_dim = network_cfg['critic_hidden_dim']
        self.net = nn.Sequential(
            nn.Linear(state_dim, hidden_dim),
            nn.ReLU(),
            nn.Linear(hidden_dim, hidden_dim),
            nn.ReLU(),
            nn.Linear(hidden_dim, 1)
        )
        self.apply(init_weights)

    def forward(self, state):
        return self.net(state)

class PPOAgent:
    def __init__(self, state_dim, action_dim, ppo_cfg, network_cfg): # 接收配置字典
        self.gamma = ppo_cfg['gamma']
        self.eps_clip = ppo_cfg['eps_clip']
        self.K_epochs = ppo_cfg['k_epochs']
        self.gae_lambda = ppo_cfg['gae_lambda']
        self.entropy_coefficient = ppo_cfg['entropy_coefficient']

        self.actor = Actor(state_dim, action_dim, network_cfg).to(device)
        self.critic = Critic(state_dim, network_cfg).to(device)
        
        # MODIFIED: 優化器初始化移到這裡，方便在加載 IL 模型後重新初始化 actor_optimizer
        self.optimizer_actor = optim.Adam(self.actor.parameters(), lr=ppo_cfg['lr_actor'])
        self.optimizer_critic = optim.Adam(self.critic.parameters(), lr=ppo_cfg['lr_critic'])

        self.actor_old = Actor(state_dim, action_dim, network_cfg).to(device)
        self.actor_old.load_state_dict(self.actor.state_dict())
        
        self.mse_loss = nn.MSELoss()

    def select_action(self, state):
        with torch.no_grad():
            state_tensor = torch.FloatTensor(state.reshape(1, -1)).to(device)
            mean, log_std = self.actor_old(state_tensor)
            std = torch.exp(log_std)
            
            dist = Normal(mean, std)
            action = dist.sample()
            action_log_prob = dist.log_prob(action)
            action_env = torch.clamp(action, 0.0, 1.0)

        return action_env.cpu().numpy().flatten(), action_log_prob.cpu()

    def update(self, memory, logging_cfg_update): # 傳入日誌配置
        rewards_gae = []
        discounted_reward = 0
        for reward, is_terminal in zip(reversed(memory.rewards), reversed(memory.is_terminals)):
            if is_terminal:
                discounted_reward = 0
            discounted_reward = reward + (self.gamma * discounted_reward)
            rewards_gae.insert(0, discounted_reward)
            
        rewards_gae = torch.tensor(rewards_gae, dtype=torch.float32).to(device)
        rewards_gae = (rewards_gae - rewards_gae.mean()) / (rewards_gae.std() + 1e-7)

        old_states = torch.squeeze(torch.stack(memory.states, dim=0)).detach().to(device)
        old_actions = torch.squeeze(torch.stack(memory.actions, dim=0)).detach().to(device)
        old_log_probs = torch.squeeze(torch.stack(memory.log_probs, dim=0)).detach().to(device)
        
        if not hasattr(self, 'update_call_count'):
            self.update_call_count = 0
        self.update_call_count += 1

        for epoch_k in range(self.K_epochs):
            mean_new, log_std_new = self.actor(old_states)
            std_new = torch.exp(log_std_new)
            dist_new = Normal(mean_new, std_new)
            
            log_probs_new = dist_new.log_prob(old_actions)
            state_values = self.critic(old_states)
            state_values = torch.squeeze(state_values)

            ratios = torch.exp(log_probs_new - old_log_probs.detach())
            advantages = rewards_gae - state_values.detach()
            advantages_normalized = (advantages - advantages.mean()) / (advantages.std() + 1e-7)
            
            surr1 = ratios * advantages_normalized
            surr2 = torch.clamp(ratios, 1 - self.eps_clip, 1 + self.eps_clip) * advantages_normalized
            
            loss_actor_policy = -torch.min(surr1, surr2).mean()
            loss_critic = self.mse_loss(state_values, rewards_gae)
            
            dist_entropy_val = dist_new.entropy().mean()
            loss_entropy_term = self.entropy_coefficient * dist_entropy_val 
            total_actor_loss = loss_actor_policy - loss_entropy_term

            if logging_cfg_update['enable'] and \
               logging_cfg_update.get('log_every_n_updates', 1) > 0 and \
               self.update_call_count % logging_cfg_update['log_every_n_updates'] == 0 and \
               logging_cfg_update.get('log_at_k_epoch_num', 1) > 0 and \
               epoch_k == (logging_cfg_update['log_at_k_epoch_num'] -1) and \
               len(old_states) > 0:
                sample_idx_to_log = 0
                if len(old_states) > sample_idx_to_log:
                    if logging_cfg_update.get('print_full_state_vector_for_sample', False):
                        state_sample_str = str(old_states[sample_idx_to_log, :].cpu().numpy())
                    else:
                        state_sample_str = f"OppX:{old_states[sample_idx_to_log, 0].item():.2f} BallX:{old_states[sample_idx_to_log, 6].item():.2f} BallY:{old_states[sample_idx_to_log, 7].item():.2f} RelBallOppX:{old_states[sample_idx_to_log, 11].item():.2f}"
                    
                    print(f"PPO_UPDATE_LOG --- UpdateCall: {self.update_call_count}, K_Epoch: {epoch_k}, SampleIdx: {sample_idx_to_log} ---")
                    print(f"  State: {state_sample_str}")
                    print(f"  V(s_t) (Critic Value): {state_values[sample_idx_to_log].item():.4f}")
                    print(f"  R_t (GAE Target for V): {rewards_gae[sample_idx_to_log].item():.4f}")
                    print(f"  Advantage (Normalized): {advantages_normalized[sample_idx_to_log].item():.4f}")
                    print(f"  Actor New Output | Mean: {mean_new[sample_idx_to_log].item():.4f}, LogStd: {log_std_new[sample_idx_to_log].item():.4f}")
                    entropy_float = dist_entropy_val.item() if isinstance(dist_entropy_val, torch.Tensor) else float(dist_entropy_val)
                    print(f"  Losses | Policy: {loss_actor_policy.item():.4f}, Critic: {loss_critic.item():.4f}, EntropyTerm: {loss_entropy_term.item():.4f} (RawEntropy: {entropy_float:.4f})")
                    print("--------------------------------------------------------------------")

            self.optimizer_actor.zero_grad()
            total_actor_loss.backward()
            torch.nn.utils.clip_grad_norm_(self.actor.parameters(), max_norm=0.5)
            self.optimizer_actor.step()
            
            self.optimizer_critic.zero_grad()
            loss_critic.backward()
            torch.nn.utils.clip_grad_norm_(self.critic.parameters(), max_norm=0.5)
            self.optimizer_critic.step()

        self.actor_old.load_state_dict(self.actor.state_dict())
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

# --- 獎勵函數設計 (根據新的 reward_cfg 進行修改) ---
def calculate_reward(reward_cfg, current_state, env_info, done, prev_ball_y_obs, current_ball_y_obs, player1_lives, opponent_lives, prev_player1_lives, prev_opponent_lives):
    reward = 0.0
    reward_components = {}

    hit_ball_this_step = env_info.get('ai_hit_ball', False)
    player1_scored_this_step = env_info.get('scorer') == 'player1' or opponent_lives < prev_opponent_lives
    ai_scored_this_step = env_info.get('scorer') == 'opponent' or player1_lives < prev_player1_lives

    if hit_ball_this_step:
        val = reward_cfg.get('hit_ball_reward', 0.0)
        reward += val
        reward_components['hit_ball'] = val

    if player1_scored_this_step: 
        val = reward_cfg.get('player_scored_penalty', 0.0)
        reward += val
        reward_components['scored_upon'] = val
    elif ai_scored_this_step: 
        val = reward_cfg.get('ai_scored_reward', 0.0)
        reward += val
        reward_components['ai_scored'] = val

    if not hit_ball_this_step and not player1_scored_this_step and not ai_scored_this_step and not done:
        if reward_cfg.get('enable_x_align_reward', False):
            pass 
        if reward_cfg.get('enable_y_proximity_reward', False):
            pass
        if reward_cfg.get('enable_paddle_movement_penalty', False):
            pass
        if reward_cfg.get('enable_x_align_penalty', False) and reward_cfg.get('x_align_penalty_factor', 0.0) != 0:
            pass
        if reward_cfg.get('enable_y_shaping', False):
            pass
        if reward_cfg.get('enable_edge_penalty', False):
            pass

    if reward_cfg.get('enable_survival_reward', False):
        val = reward_cfg.get('survival_reward_per_step', 0.0) 
        if not done and not player1_scored_this_step: 
            reward += val
            reward_components['survival_reward'] = val
    
    return reward, reward_components

# --- 訓練主函數 ---
def train(config_data):
    global device, train_config, render_screen, render_clock # 引用全域變數
    train_config = config_data
    
    cfg_general = train_config['general']
    cfg_model_io = train_config['model_io'] # MODIFIED: 確保 cfg_model_io 在作用域內
    cfg_train_loop = train_config['training_loop']
    cfg_ppo_agent = train_config['ppo_agent']
    cfg_network = train_config['network']
    cfg_reward = train_config['reward_function']
    cfg_logging = train_config['logging']
    cfg_viz = train_config.get('visualization', {})

    print(f"開始訓練，使用設備: {device}")
    obs_dim = cfg_general['obs_dim']
    action_dim = cfg_general['action_dim']
    print(f"觀察空間維度: {obs_dim}, 動作空間維度: {action_dim}")

    # --- 初始化 Pygame (與之前相同) ---
    pygame.init()
    if cfg_viz.get('enable_render', False) and cfg_viz.get('render_every_n_episodes', 0) > 0:
        render_screen_width = cfg_viz.get('render_screen_width', 600)
        render_screen_height = cfg_viz.get('render_screen_height', 450)
        render_screen = pygame.display.set_mode((render_screen_width, render_screen_height))
        pygame.display.set_caption("PPO Training Render")
        render_clock = pygame.time.Clock()
        print(f"訓練過程中將啟用渲染，每 {cfg_viz['render_every_n_episodes']} 回合。")
    else:
        pygame.display.set_mode((1,1)) 
        print("訓練過程中禁用渲染。")

    game_cfg_manager = GameConfigManager()
    GameSettings._config_manager = game_cfg_manager

    level1_yaml_path = "models/level1.yaml"
    common_game_cfg = {}
    if os.path.exists(resource_path(level1_yaml_path)):
        common_game_cfg = game_cfg_manager.get_level_config("level1.yaml")
        if common_game_cfg is None: common_game_cfg = {}
        print(f"使用 Level 1 的 common_config: {common_game_cfg}")
    else:
        print(f"警告: {level1_yaml_path} 未找到。使用預設 common_config。")
        common_game_cfg.setdefault('initial_speed', 0.02)
        common_game_cfg.setdefault('player_life', 3)
        common_game_cfg.setdefault('ai_life', 3)
        common_game_cfg.setdefault('player_paddle_width', 100) # 確保這些值存在
        common_game_cfg.setdefault('ai_paddle_width', 60)


    player1_env_config = {
        'initial_x': 0.5,
        'initial_paddle_width': common_game_cfg.get('player_paddle_width', 100),
        'initial_lives': common_game_cfg.get('player_life', 3),
        'skill_code': None, 'is_ai': False
    }
    opponent_env_config = {
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
        render_size=400, paddle_height_px=10, ball_radius_px=10,
        initial_main_screen_surface_for_renderer=None
    )

    ppo_agent = PPOAgent(
        state_dim=obs_dim, action_dim=action_dim,
        ppo_cfg=cfg_ppo_agent, network_cfg=cfg_network
    )
    memory = Memory()

    time_step_counter = 0
    episode_count = 0
    
    model_dir = cfg_model_io['model_dir']
    model_name_prefix = cfg_model_io['model_name_prefix']
    os.makedirs(resource_path(model_dir), exist_ok=True) # MODIFIED: 使用 resource_path

    # --- NEW: 加載模仿學習 (IL) 預訓練的 Actor 模型 ---
    il_actor_loaded_successfully = False
    if cfg_model_io.get('load_il_actor_model', False):
        il_actor_path_str = cfg_model_io.get('il_actor_model_path', "ppo_models/il_actor_pretrained.pth")
        il_actor_full_path = resource_path(il_actor_path_str)
        if os.path.exists(il_actor_full_path):
            print(f"準備從模仿學習加載預訓練的 Actor 權重: {il_actor_full_path}")
            try:
                # 假設 .pth 文件直接是 state_dict
                actor_weights = torch.load(il_actor_full_path, map_location=device)
                
                ppo_agent.actor.load_state_dict(actor_weights)
                ppo_agent.actor_old.load_state_dict(actor_weights) # PPO 的 actor_old 也需要同步
                
                # 重新初始化 Actor 的優化器，因為之前的優化器狀態是針對 IL 任務的
                ppo_agent.optimizer_actor = optim.Adam(ppo_agent.actor.parameters(), lr=cfg_ppo_agent['lr_actor'])
                print(f"成功將模仿學習預訓練的 Actor 權重加載到 PPO Agent。Actor 優化器已重置。")
                il_actor_loaded_successfully = True
            except Exception as e:
                print(f"加載模仿學習預訓練的 Actor 權重失敗: {e}。")
        else:
            print(f"未找到模仿學習預訓練的 Actor 模型: {il_actor_full_path}。")
    
    if not il_actor_loaded_successfully and cfg_model_io['load_existing_model']:
        # 只有當沒有成功加載 IL Actor，並且配置了加載 PPO 檢查點時，才執行以下邏輯
        checkpoint_path = resource_path(os.path.join(model_dir, f"{model_name_prefix}_latest.pth")) # MODIFIED
        if os.path.exists(checkpoint_path):
            print(f"載入先前儲存的完整 PPO 檢查點: {checkpoint_path}")
            try:
                checkpoint = torch.load(checkpoint_path, map_location=device)
                ppo_agent.actor_old.load_state_dict(checkpoint['actor_state_dict'])
                ppo_agent.actor.load_state_dict(checkpoint['actor_state_dict'])
                ppo_agent.critic.load_state_dict(checkpoint['critic_state_dict'])
                
                if 'optimizer_actor_state_dict' in checkpoint:
                    ppo_agent.optimizer_actor.load_state_dict(checkpoint['optimizer_actor_state_dict'])
                if 'optimizer_critic_state_dict' in checkpoint:
                    ppo_agent.optimizer_critic.load_state_dict(checkpoint['optimizer_critic_state_dict'])
                
                time_step_counter = checkpoint.get('time_step_counter', 0)
                episode_count = checkpoint.get('episode_count', 0)
                print(f"從 PPO 檢查點 episode {episode_count}, time_step {time_step_counter} 繼續訓練。")
            except Exception as e:
                print(f"載入 PPO 模型檢查點失敗: {e}。將從頭開始訓練（或使用已加載的IL Actor）。")
                if not il_actor_loaded_successfully: # 只有當 IL 也沒加載時，才重置計數器
                    time_step_counter = 0; episode_count = 0
        else:
            print(f"找不到已儲存的 PPO 模型 {checkpoint_path}。")
            if not il_actor_loaded_successfully:
                 print("將從頭開始訓練。")

    elif not il_actor_loaded_successfully: # 如果兩種加載都沒啟用或失敗
        print("設定為不載入任何已儲存的模型，將從頭開始訓練。")


    recent_rewards = []
    cfg_log_ep_prog = cfg_logging['episode_progress_log']
    cfg_log_ep_sum = cfg_logging['episode_summary_log']
    cfg_log_ppo_upd = cfg_logging['ppo_update_log']

    updates_call_counter_for_log = 0

    for i_episode in range(episode_count + 1, cfg_train_loop['max_episodes'] + 1):
        state, _ = env.reset() 
        current_ep_reward = 0
        
        ball_y_in_obs_idx = 7 
        if state.shape[0] <= ball_y_in_obs_idx:
            print(f"錯誤：觀察維度 ({state.shape[0]}) 過小。")
            pygame.quit() # MODIFIED: 退出 Pygame
            return

        prev_ball_y_for_reward = state[ball_y_in_obs_idx] 
        prev_p1_lives = env.player1.lives
        prev_opp_lives = env.opponent.lives
        
        should_render_this_episode = False
        if cfg_viz.get('enable_render', False) and \
           cfg_viz.get('render_every_n_episodes', 0) > 0 and \
           (i_episode == 1 or i_episode % cfg_viz['render_every_n_episodes'] == 0):
            should_render_this_episode = True
            if render_screen is None: 
                render_screen_width = cfg_viz.get('render_screen_width', 600)
                render_screen_height = cfg_viz.get('render_screen_height', 450)
                render_screen = pygame.display.set_mode((render_screen_width, render_screen_height))
                pygame.display.set_caption(f"PPO Training Render - Episode {i_episode}")
                render_clock = pygame.time.Clock()
            if env.renderer:
                env.renderer.window = render_screen
            elif hasattr(env, 'provided_main_screen_surface'):
                 env.provided_main_screen_surface = render_screen


        frames_rendered_this_episode = 0
        max_frames_to_render = cfg_viz.get('render_frames_per_episode', 200) if not cfg_viz.get('render_whole_episode', False) else float('inf')

        for t in range(cfg_train_loop['max_timesteps_per_episode']):
            time_step_counter += 1
            action_opponent_continuous, action_log_prob = ppo_agent.select_action(state)
            
            log_this_timestep_detail = False
            if cfg_log_ep_prog['enable'] and \
               cfg_log_ep_prog.get('log_every_n_episodes', 0) > 0 and \
               i_episode % cfg_log_ep_prog['log_every_n_episodes'] == 0:
                if cfg_log_ep_prog.get('log_at_timestep_interval', 0) > 0 and \
                   t % cfg_log_ep_prog['log_at_timestep_interval'] == 0:
                    log_this_timestep_detail = True
            
            if log_this_timestep_detail:
                with torch.no_grad():
                    current_state_tensor = torch.FloatTensor(state.reshape(1, -1)).to(device)
                    raw_mean, raw_log_std = ppo_agent.actor_old(current_state_tensor)
                print(f"EPISODE_PROGRESS_LOG --- Episode: {i_episode}, Timestep: {t} (Total: {time_step_counter}) ---")
                if cfg_log_ep_prog.get('print_full_state_vector', False):
                    state_str = str(state)
                else:
                    state_str = f"OppX:{state[0]:.2f} BallX:{state[6]:.2f} BallY:{state[7]:.2f} RelBallOppX:{state[11]:.2f}"
                print(f"  State: {state_str}")
                print(f"  PPO Raw Output | Mean (actor_old): {raw_mean.item():.4f}, LogStd (actor_old): {raw_log_std.item():.4f}")
                print(f"  PPO Action   | LogProb: {action_log_prob.item():.4f}, Final Target X: {action_opponent_continuous[0]:.4f}")

            ball_x_in_obs_idx = 6
            action_player1_target_x = 0.5 # 預設值，如果 state 維度不夠
            if state.shape[0] > ball_x_in_obs_idx:
                 ball_x_in_obs = state[ball_x_in_obs_idx]
                 action_player1_target_x = np.clip(ball_x_in_obs, 0.0, 1.0)
            else:
                 print(f"警告: Timestep {t} 的 state 維度不足以獲取 ball_x_in_obs_idx。Player1 將使用預設動作。")


            next_state, _, round_done, game_over, info = env.step(action_player1_target_x, action_opponent_continuous[0])

            reward_val, reward_components_dict = calculate_reward(
                cfg_reward, state, info, (round_done or game_over),
                prev_ball_y_for_reward, next_state[ball_y_in_obs_idx],
                env.player1.lives, env.opponent.lives,
                prev_p1_lives, prev_opp_lives
            )
            current_ep_reward += reward_val
            
            if log_this_timestep_detail:
                if cfg_log_ep_prog.get('print_reward_components', False) and reward_components_dict:
                    print(f"  Reward Detail  | Total: {reward_val:.4f}")
                    for r_key, r_val_comp in reward_components_dict.items():
                        print(f"    {r_key}: {r_val_comp:.4f}")
                    if info: print(f"  Env Info: {info}")
                print(f"--------------------------------------------------------------------")

            memory.states.append(torch.FloatTensor(state).to(device))
            memory.actions.append(torch.FloatTensor(action_opponent_continuous).to(device))
            memory.log_probs.append(action_log_prob)
            memory.rewards.append(reward_val)
            memory.is_terminals.append(round_done or game_over)

            if time_step_counter % cfg_train_loop['update_timesteps'] == 0 and len(memory.states) > 0:
                updates_call_counter_for_log +=1 
                if cfg_log_ppo_upd['enable']:
                     print(f"  總步數 {time_step_counter}: 更新 PPO 網路 (第 {updates_call_counter_for_log} 次)...")
                ppo_agent.update(memory, cfg_log_ppo_upd) 
            
            prev_ball_y_for_reward = next_state[ball_y_in_obs_idx]
            prev_p1_lives = env.player1.lives
            prev_opp_lives = env.opponent.lives
            state = next_state
            
            if should_render_this_episode and frames_rendered_this_episode < max_frames_to_render:
                if render_screen: 
                    for event in pygame.event.get(): 
                        if event.type == pygame.QUIT:
                            print("用戶在渲染過程中關閉視窗，停止訓練。")
                            if env: env.close() # MODIFIED
                            pygame.quit()
                            return
                    if env.renderer:
                        env.renderer.window = render_screen
                    else: 
                        env.provided_main_screen_surface = render_screen

                    env.render() 
                    render_clock.tick(cfg_viz.get('render_fps', 30))
                    frames_rendered_this_episode += 1
                else: 
                    should_render_this_episode = False


            if game_over:
                break
        
        if cfg_log_ep_sum['enable'] and \
           cfg_log_ep_sum.get('log_every_n_episodes', 0) > 0 and \
           i_episode % cfg_log_ep_sum['log_every_n_episodes'] == 0:
            recent_rewards.append(current_ep_reward)
            window_size = cfg_log_ep_sum.get('recent_rewards_window_size', 50)
            if len(recent_rewards) > window_size:
                 recent_rewards.pop(0)
            avg_reward_recent = np.mean(recent_rewards) if recent_rewards else 0.0
            print(f"EPISODE_SUMMARY --- 回合: {i_episode}, 總步數: {time_step_counter}, 本回合獎勵: {current_ep_reward:.2f}, 最近 {len(recent_rewards)} 回平均獎勵: {avg_reward_recent:.2f}")

        if cfg_model_io['save_model_every_n_episodes'] > 0 and \
           (i_episode % cfg_model_io['save_model_every_n_episodes'] == 0 or i_episode == cfg_train_loop['max_episodes']):
            
            # MODIFIED: 使用 resource_path 處理模型保存路徑
            path = resource_path(os.path.join(model_dir, f"{model_name_prefix}_episode_{i_episode}.pth"))
            latest_path = resource_path(os.path.join(model_dir, f"{model_name_prefix}_latest.pth"))
            
            print(f"儲存模型到 {path}")
            torch.save({
                'episode_count': i_episode,
                'time_step_counter': time_step_counter,
                'actor_state_dict': ppo_agent.actor.state_dict(),
                'critic_state_dict': ppo_agent.critic.state_dict(),
                'optimizer_actor_state_dict': ppo_agent.optimizer_actor.state_dict(),
                'optimizer_critic_state_dict': ppo_agent.optimizer_critic.state_dict(),
                'train_config_snapshot': train_config 
            }, path)
            torch.save({
                'episode_count': i_episode,
                'time_step_counter': time_step_counter,
                'actor_state_dict': ppo_agent.actor.state_dict(),
                'critic_state_dict': ppo_agent.critic.state_dict(),
                'optimizer_actor_state_dict': ppo_agent.optimizer_actor.state_dict(),
                'optimizer_critic_state_dict': ppo_agent.optimizer_critic.state_dict(),
                'train_config_snapshot': train_config
            }, latest_path)


    print("訓練完成。")
    if env: env.close() # MODIFIED
    pygame.quit()

def main():
    global device, train_config, render_screen, render_clock 

    parser = argparse.ArgumentParser(description="PPO Pong Agent Configurable Training Script")
    parser.add_argument(
        "--config", type=str, default="config/train_config.yaml",
        help="Path to the training configuration YAML file."
    )
    args = parser.parse_args()

    config_data = load_config_from_yaml(resource_path(args.config)) # MODIFIED
    if config_data is None: return

    cfg_general_device = config_data.get('general', {}).get('device', 'auto')
    if cfg_general_device == "auto":
        device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    elif cfg_general_device == "cuda" and torch.cuda.is_available():
        device = torch.device("cuda")
    else:
        device = torch.device("cpu")

    seed_val = config_data.get('general', {}).get('seed', None)
    if seed_val is not None:
        torch.manual_seed(seed_val)
        np.random.seed(seed_val)
        random.seed(seed_val)
        if device.type == 'cuda':
            torch.cuda.manual_seed_all(seed_val)
        print(f"已設定隨機種子: {seed_val}")
    
    train(config_data)

if __name__ == '__main__':
    main()