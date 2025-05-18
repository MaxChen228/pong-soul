import torch
import torch.optim as optim
import torch.nn.functional as F
import numpy as np
import random
from collections import deque, namedtuple
import os
import sys
import pygame

# 為了能 import 專案內的模組
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
sys.path.insert(0, project_root)

from envs.pong_duel_env import PongDuelEnv # 或者特製的 SoulEaterBugEnv
from game.ai_agent import QNet # 重用 QNet
from game.settings import GameSettings # 可能需要一些全域設定
from game.player_state import PlayerState
from game.skills.soul_eater_bug_skill import SoulEaterBugSkill # 用於獲取觀察空間維度等

# --- Hyperparameters ---
BUFFER_SIZE = int(1e5)  # Replay buffer size
BATCH_SIZE = 64         # Minibatch size
GAMMA = 0.99            # Discount factor
TAU = 1e-3              # For soft update of target parameters
LR = 5e-4               # Learning rate
UPDATE_EVERY = 4        # How often to update the network
TARGET_UPDATE_EVERY = 100 # How often to update the target network

# (可選) TensorBoard 記錄
# from torch.utils.tensorboard import SummaryWriter
# writer = SummaryWriter('runs/bug_rl_experiment_1')

Transition = namedtuple('Transition',
                        ('state', 'action', 'next_state', 'reward', 'done'))

class ReplayBuffer:
    def __init__(self, capacity):
        self.memory = deque([], maxlen=capacity)

    def push(self, *args):
        self.memory.append(Transition(*args))

    def sample(self, batch_size):
        return random.sample(self.memory, batch_size)

    def __len__(self):
        return len(self.memory)

class BugDQNAgent:
    def __init__(self, state_size, action_size, seed):
        self.state_size = state_size
        self.action_size = action_size
        self.seed = random.seed(seed)
        self.device = torch.device("cuda" if torch.cuda.is_available() else "cpu")

        self.qnetwork_local = QNet(state_size, action_size).to(self.device)
        self.qnetwork_target = QNet(state_size, action_size).to(self.device)
        self.optimizer = optim.Adam(self.qnetwork_local.parameters(), lr=LR)

        self.memory = ReplayBuffer(BUFFER_SIZE)
        self.t_step = 0 # For UPDATE_EVERY
        self.target_update_step = 0 # For TARGET_UPDATE_EVERY

        # 確保目標網路初始參數與本地網路一致
        self.qnetwork_target.load_state_dict(self.qnetwork_local.state_dict())
        self.qnetwork_target.eval()


    def step(self, state, action, reward, next_state, done):
        self.memory.push(state, action, next_state, reward, done)
        self.t_step = (self.t_step + 1) % UPDATE_EVERY
        if self.t_step == 0:
            if len(self.memory) > BATCH_SIZE:
                experiences = self.memory.sample(BATCH_SIZE)
                self.learn(experiences, GAMMA)

        self.target_update_step = (self.target_update_step + 1) % TARGET_UPDATE_EVERY
        if self.target_update_step == 0:
            self.soft_update(self.qnetwork_local, self.qnetwork_target, TAU)


    def act(self, state, eps=0.):
        state = torch.from_numpy(state).float().unsqueeze(0).to(self.device)
        self.qnetwork_local.eval()
        with torch.no_grad():
            action_values = self.qnetwork_local(state)
        self.qnetwork_local.train()

        if random.random() > eps:
            return np.argmax(action_values.cpu().data.numpy())
        else:
            return random.choice(np.arange(self.action_size))

    def learn(self, experiences, gamma):
        states, actions, next_states, rewards, dones = zip(*experiences)

        states = torch.from_numpy(np.vstack(states)).float().to(self.device)
        actions = torch.from_numpy(np.vstack(actions)).long().to(self.device) # long for indexing
        next_states = torch.from_numpy(np.vstack(next_states)).float().to(self.device)
        rewards = torch.from_numpy(np.vstack(rewards)).float().to(self.device)
        dones = torch.from_numpy(np.vstack(dones).astype(np.uint8)).float().to(self.device)


        # Get max predicted Q values (for next states) from target model
        Q_targets_next = self.qnetwork_target(next_states).detach().max(1)[0].unsqueeze(1)
        # Compute Q targets for current states
        Q_targets = rewards + (gamma * Q_targets_next * (1 - dones))

        # Get expected Q values from local model
        Q_expected = self.qnetwork_local(states).gather(1, actions)

        # Compute loss
        loss = F.mse_loss(Q_expected, Q_targets)
        # Minimize the loss
        self.optimizer.zero_grad()
        loss.backward()
        # torch.nn.utils.clip_grad_norm_(self.qnetwork_local.parameters(), 1) # Gradient clipping
        self.optimizer.step()

        return loss.item() # Return loss for logging

    def soft_update(self, local_model, target_model, tau):
        for target_param, local_param in zip(target_model.parameters(), local_model.parameters()):
            target_param.data.copy_(tau*local_param.data + (1.0-tau)*target_param.data)

    def save(self, filename="bug_agent_checkpoint.pth"):
        model_save_path = os.path.join(project_root, "models", filename) # 儲存到專案的 models 資料夾
        torch.save({
            'model_state_dict': self.qnetwork_local.state_dict(),
            # 'optimizer_state_dict': self.optimizer.state_dict(), # 可選
        }, model_save_path)
        print(f"Model saved to {model_save_path}")

    def load(self, filename="bug_agent_checkpoint.pth"):
        model_load_path = os.path.join(project_root, "models", filename)
        if os.path.exists(model_load_path):
            checkpoint = torch.load(model_load_path, map_location=self.device)
            self.qnetwork_local.load_state_dict(checkpoint['model_state_dict'])
            self.qnetwork_target.load_state_dict(checkpoint['model_state_dict']) # 也載入目標網路
            # if 'optimizer_state_dict' in checkpoint:
            #    self.optimizer.load_state_dict(checkpoint['optimizer_state_dict'])
            print(f"Model loaded from {model_load_path}")
            return True
        print(f"No model found at {model_load_path}")
        return False

# --- 訓練環境的簡化版 (需要進一步完善) ---
class BugSkillTrainingEnv:
    def __init__(self, render_training=False):
        # 模擬 PongDuelEnv 的一些核心設定
        # 注意：這裡的 player1 和 opponent 是相對於「蟲技能的擁有者」而言的
        # 假設技能擁有者是 player1，目標是 opponent
        self.skill_owner_is_player1 = True # 可以配置

        self.player1 = PlayerState(player_identifier="p1_skill_owner", skill_code="soul_eater_bug")
        self.opponent = PlayerState(player_identifier="p2_target") # 目標玩家

        # 環境設定 (需要與 PongDuelEnv 中的設定類似)
        self.render_size = 400
        self.paddle_height_normalized = 10 / self.render_size
        self.ball_radius_normalized = 10 / self.render_size
        self.time_scale = 1.0 # 訓練時通常不需要 slowmo
        self.max_trail_length = 20 # From GameSettings

        # 創建一個「模擬的」env 物件傳給 SoulEaterBugSkill
        # 這部分需要小心，確保 SoulEaterBugSkill 需要的 env 屬性都存在
        self.mock_env_for_skill = self._create_mock_env_for_skill()

        self.bug_skill = SoulEaterBugSkill(self.mock_env_for_skill, self.player1 if self.skill_owner_is_player1 else self.opponent)
        
        # 如果訓練時需要渲染 (調試用)
        self.render_training = render_training
        if self.render_training:
            pygame.init()
            self.screen = pygame.display.set_mode((self.render_size, self.render_size + 100)) # 簡化渲染區域
            pygame.display.set_caption("Bug Skill Training")
            self.clock = pygame.time.Clock()
            self.font = pygame.font.Font(None, 24)


    def _create_mock_env_for_skill(self):
        """
        創建一個最小化的模擬 env 物件，包含 SoulEaterBugSkill 執行所需的屬性。
        """
        mock_env = type('MockEnv', (object,), {})() # 創建一個空物件
        mock_env.player1 = self.player1
        mock_env.opponent = self.opponent
        mock_env.render_size = self.render_size
        mock_env.paddle_height_normalized = self.paddle_height_normalized
        mock_env.ball_radius_normalized = self.ball_radius_normalized
        mock_env.time_scale = self.time_scale # 蟲的移動會受 time_scale 影響
        mock_env.max_trail_length = self.max_trail_length

        # SoulEaterBugSkill 在 update 和碰撞檢測時會直接修改這些：
        mock_env.ball_x = 0.5
        mock_env.ball_y = 0.5
        mock_env.ball_vx = 0.0 # 蟲技能會覆寫
        mock_env.ball_vy = 0.0 # 蟲技能會覆寫
        mock_env.spin = 0      # 蟲技能會覆寫
        mock_env.trail = []    # 蟲技能會管理

        # SoulEaterBugSkill 在得分或碰撞時會設定這些：
        mock_env.freeze_timer = 0
        mock_env.round_concluded_by_skill = False
        mock_env.current_round_info = {}
        
        # SoulEaterBugSkill 在 activate/deactivate 時會呼叫這個
        def mock_set_ball_visual_override(skill_identifier, active, owner_identifier):
            # print(f"MockEnv: Ball visual override: {skill_identifier}, active: {active}, owner: {owner_identifier}")
            pass
        mock_env.set_ball_visual_override = mock_set_ball_visual_override
        
        return mock_env

    def reset(self):
        # 重置蟲（球）的狀態、目標板子狀態等
        self.opponent.x = 0.5 # 目標板子可以固定或隨機
        self.opponent.lives = 1 # 每次重置，目標只有1條命（用於該回合）

        # 技能擁有者的狀態也可能需要重置，但蟲技能主要關心蟲本身
        self.player1.x = 0.5

        # 啟動蟲技能 (這會設定蟲的初始位置等)
        self.bug_skill.activate() # activate 會設定 mock_env.ball_x/y

        # 返回初始觀察
        return self.bug_skill._get_bug_observation()

    def step(self, action_index):
        # 1. 讓蟲技能根據 RL action 更新蟲的狀態 (delta_x, delta_y)
        #    在 bug_skill.update() 內部，它會解釋 action_index 並計算移動
        #    然後 bug_skill.update() 會調用 _apply_movement_and_constrain_bounds,
        #    _check_bug_scored, _check_bug_hit_paddle
        
        # 為了讓 bug_skill.update() 能使用 action_index，我們需要一種方式傳遞它
        # 目前 bug_skill.update() 沒有參數。
        # 方案 A: 修改 bug_skill.update(action_index=None)，在訓練時傳入
        # 方案 B: 在 agent.act() 後，直接在訓練迴圈中計算 delta_x, delta_y，
        #         然後只調用 bug_skill 的一部分更新（例如只應用移動和碰撞檢測）
        # 這裡我們先假設 bug_skill.update() 內部已經有邏輯從 self.bug_agent 獲取動作，
        # 這意味著我們在訓練迴圈中，在調用 env.step() 之前，需要先讓 bug_skill 的 bug_agent 執行 act()
        # 並將結果（動作）儲存起來，讓 bug_skill.update() 能讀取到。
        #
        # 為了簡化訓練環境的 step，我們假設 BugDQNAgent.act() 決定了動作，
        # 然後我們直接在 bug_skill 內部模擬這個動作的效果。
        # SoulEaterBugSkill.update() 需要能接收一個 action_index (如果 bug_agent 不存在，則用內部邏輯)
        
        # 這裡我們模擬 SoulEaterBugSkill.update() 的核心邏輯，但由訓練腳本控制動作
        delta_x_norm, delta_y_norm = 0.0, 0.0
        y_direction_sign_to_target = -1.0 if self.bug_skill.target_player_state == self.mock_env_for_skill.opponent else 1.0

        if action_index == 0: # 前
            delta_y_norm = y_direction_sign_to_target * self.bug_skill.bug_y_rl_move_speed
        elif action_index == 1: # 後
            delta_y_norm = -y_direction_sign_to_target * self.bug_skill.bug_y_rl_move_speed
        elif action_index == 2: # 左
            delta_x_norm = -self.bug_skill.bug_x_rl_move_speed
        elif action_index == 3: # 右
            delta_x_norm = self.bug_skill.bug_x_rl_move_speed
        # action_index == 4 (靜止) -> dx, dy = 0,0

        if self.bug_skill.base_y_speed != 0.0 and action_index in [2, 3, 4]:
            if delta_y_norm == 0.0:
                delta_y_norm = y_direction_sign_to_target * self.bug_skill.base_y_speed

        # 應用移動
        self.bug_skill._apply_movement_and_constrain_bounds(delta_x_norm, delta_y_norm)
        self.bug_skill._update_trail() # 更新拖尾

        # 檢查結果
        reward = 0.0
        done = False
        info = {} # 可以放一些額外資訊，例如是否得分、是否撞牆等

        # 時間懲罰 (每一步都給一點小的負獎勵，鼓勵快點結束)
        reward -= 0.01

        if self.bug_skill._check_bug_scored():
            reward += 10.0  # 得分獎勵
            done = True
            info['result'] = 'scored'
            # self.bug_skill.deactivate() # 在技能內部已經處理
        elif self.bug_skill._check_bug_hit_paddle():
            reward -= 5.0  # 撞到板子懲罰
            done = True
            info['result'] = 'hit_paddle'
            # self.bug_skill.deactivate() # 在技能內部已經處理
        
        # 檢查技能持續時間是否結束 (如果 done 尚未為 True)
        if not done and (pygame.time.get_ticks() - self.bug_skill.activated_time) >= self.bug_skill.duration_ms:
            reward -= 1.0 # 持續時間到但未得分/撞板，可能給予少量懲罰
            done = True
            info['result'] = 'duration_expired'
            self.bug_skill.deactivate(hit_paddle=False, scored=False) # 確保停用

        # 如果還沒結束，獲取下一個觀察
        next_observation = self.bug_skill._get_bug_observation() if not done else np.zeros_like(self.bug_skill._get_bug_observation())
        
        return next_observation, reward, done, info

    def render(self, agent_action=None): # agent_action 用於顯示 RL 正在採取的動作
        if not self.render_training:
            return

        self.screen.fill((0,0,0)) # 背景色

        # 繪製目標板子 (簡化)
        target_paddle = self.bug_skill.target_player_state
        tp_x = int(target_paddle.x * self.render_size)
        tp_w = int(target_paddle.paddle_width_normalized * self.render_size)
        tp_h = int(self.paddle_height_normalized * self.render_size)
        tp_y = 0 if target_paddle == self.mock_env_for_skill.opponent else self.render_size - tp_h
        pygame.draw.rect(self.screen, (200,0,0), (tp_x - tp_w//2, tp_y, tp_w, tp_h))

        # 繪製蟲 (球)
        bug_surf = self.bug_skill.bug_image_transformed
        # SoulEaterBugSkill 在 activate 時會設定 mock_env.ball_x/y
        bug_render_x = int(self.mock_env_for_skill.ball_x * self.render_size)
        bug_render_y = int(self.mock_env_for_skill.ball_y * self.render_size)
        bug_rect = bug_surf.get_rect(center=(bug_render_x, bug_render_y))
        self.screen.blit(bug_surf, bug_rect)
        
        # 顯示一些訓練資訊
        if agent_action is not None:
            action_text = f"Action: {agent_action}"
            text_surface = self.font.render(action_text, True, (255,255,255))
            self.screen.blit(text_surface, (10, self.render_size + 10))
        
        score_text = f"Target Lives: {self.opponent.lives}" # 這裡的 opponent 是蟲的目標
        text_surface_score = self.font.render(score_text, True, (255,255,255))
        self.screen.blit(text_surface_score, (10, self.render_size + 40))


        pygame.display.flip()
        self.clock.tick(30) # 訓練時可以跑快一點，或者不 tick

# --- 主訓練迴圈 ---
def train(n_episodes=2000, max_t_per_episode=1000, eps_start=1.0, eps_end=0.01, eps_decay=0.995, load_checkpoint=False):
    # 獲取觀察空間和動作空間大小
    # 這裡我們創建一個臨時的 BugSkillTrainingEnv 和 SoulEaterBugSkill 來獲取觀察維度
    # 這不是很優雅，但可以工作。更好的方法是將這些維度作為常數或配置傳入。
    temp_env = BugSkillTrainingEnv(render_training=True)
    state_size = temp_env.reset().shape[0]
    action_size = 5 # 前、後、左、右、靜止
    temp_env = None # 釋放
    print(f"State size: {state_size}, Action size: {action_size}")

    agent = BugDQNAgent(state_size=state_size, action_size=action_size, seed=0)
    
    if load_checkpoint:
        agent.load("soul_eater_bug_agent.pth") # 嘗試載入模型

    scores = []                     # list containing scores from each episode
    scores_window = deque(maxlen=100) # last 100 scores
    eps = eps_start                   # initialize epsilon

    # 實際的訓練環境
    env = BugSkillTrainingEnv(render_training=False) # 設定為 True 可以看到訓練過程 (會很慢)

    for i_episode in range(1, n_episodes + 1):
        state = env.reset()
        score = 0
        for t in range(max_t_per_episode):
            action = agent.act(state, eps)
            next_state, reward, done, info = env.step(action)
            agent.step(state, action, reward, next_state, done)
            state = next_state
            score += reward
            if env.render_training: # 如果啟用了訓練渲染
                env.render(agent_action=action)
            if done:
                break
        
        scores_window.append(score)
        scores.append(score)
        eps = max(eps_end, eps_decay * eps) # decrease epsilon

        print(f'\rEpisode {i_episode}\tAverage Score: {np.mean(scores_window):.2f}\tEpsilon: {eps:.3f}', end="")
        if i_episode % 100 == 0:
            print(f'\rEpisode {i_episode}\tAverage Score: {np.mean(scores_window):.2f}')
            agent.save("soul_eater_bug_agent.pth") # 每100輪儲存一次

        # if writer: # TensorBoard 記錄
        #     writer.add_scalar('training_reward', score, i_episode)
        #     writer.add_scalar('average_reward_100_episodes', np.mean(scores_window), i_episode)
        #     writer.add_scalar('epsilon', eps, i_episode)

    agent.save("soul_eater_bug_agent_final.pth") # 訓練結束後最終儲存
    print("Training complete.")
    # if writer:
    #     writer.close()
    return scores


if __name__ == '__main__':
    # 確保 Pygame Display 可以初始化 (如果 BugSkillTrainingEnv 的渲染被啟用)
    # pygame.init() # 如果 render_training=True，BugSkillTrainingEnv 的 __init__ 會處理
    
    # 開始訓練，可以調整參數
    # load_checkpoint=True 可以從上次儲存的地方繼續訓練
    trained_scores = train(n_episodes=10000, max_t_per_episode=700, eps_decay=0.999, load_checkpoint=False)
    
    # pygame.quit() # 如果 render_training=True
    
    # (可選) 繪製訓練結果圖
    # import matplotlib.pyplot as plt
    # fig = plt.figure()
    # ax = fig.add_subplot(111)
    # plt.plot(np.arange(len(trained_scores)), trained_scores)
    # plt.ylabel('Score')
    # plt.xlabel('Episode #')
    # plt.show()