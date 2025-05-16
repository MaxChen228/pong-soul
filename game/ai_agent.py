import torch
import torch.nn as nn

# 為了更清晰，我們可以將 QNet 重新命名為 ActorNet，因為它現在更像一個 Actor-Critic 架構中的 Actor
# 但為了最小化命名上的混淆，暫時保留 QNet 名稱，僅修改其內部結構以適應連續動作輸出。
# 如果將來採用 PPO/DDPG/SAC 等演算法，則應明確區分 Actor 和 Critic 網路。

class QNet(nn.Module): # 或者可以命名為 PolicyNet, ActorNet
    def __init__(self, input_dim=15, output_dim=1): # ⭐️ input_dim 改為 15, output_dim 保持為 1 (連續目標位置)
        super(QNet, self).__init__()
        self.fc = nn.Sequential(
            nn.Linear(input_dim, 64), # ⭐️ 輸入層接收 15 維的觀察值
            nn.ReLU(),
            nn.Linear(64, 64),
            nn.ReLU(),
            nn.Linear(64, output_dim), # 輸出一個連續值
            nn.Tanh()  # 將輸出限制在 [-1, 1]
        )

    def forward(self, x):
        # 網路輸出範圍是 [-1, 1]
        output_tanh = self.fc(x)
        # 將輸出從 [-1, 1] 轉換到 [0, 1] 作為正規化的目標位置
        output_scaled = (output_tanh + 1.0) / 2.0
        return output_scaled

class AIAgent:
    def __init__(self, model_path, device='cpu'):
        self.device = device
        # _load_model 使用的是已經處理好的絕對路徑
        self.model = self._load_model(model_path)
        self.model.eval()

    def _load_model(self, model_path):
        # ⭐️ 明確指定 input_dim 為 15，以匹配新的觀察空間
        model = QNet(input_dim=15, output_dim=1)
        try:
            checkpoint = torch.load(model_path, map_location=self.device)
            # 載入模型權重。由於 input_dim 和 output_dim 都可能已改變，
            # 舊模型幾乎肯定不相容。strict=False 允許只載入名稱和形狀都匹配的層。
            # 對於一個全新的觀察空間和動作空間，通常意味著需要從頭訓練或對權重做複雜遷移。
            model.load_state_dict(checkpoint['model'], strict=False)
            print(f"[AIAgent._load_model] Model weights attempted to load from: {model_path} (strict=False due to potential architecture changes).")
            if 'model' not in checkpoint:
                 print(f"[AIAgent._load_model] WARNING: 'model' key not found in checkpoint from '{model_path}'. Model will be randomly initialized.")
        except FileNotFoundError:
            print(f"[AIAgent._load_model] WARNING: Model file '{model_path}' not found. Using randomly initialized model.")
        except Exception as e:
            print(f"[AIAgent._load_model] WARNING: Could not load model weights from '{model_path}' due to: {e}. Using randomly initialized model.")
            print(f"  This is expected if the network architecture has significantly changed and you haven't retrained or provided a compatible model.")
        return model.to(self.device)

    def select_action(self, obs):
        # obs 現在應該是 15 維的
        if obs.shape[0] != 15: # 添加一個檢查，確保觀察維度正確
            print(f"[AIAgent.select_action] WARNING: Expected observation dimension 15, but got {obs.shape[0]}. Ensure _get_obs and QNet input_dim match.")
            # 可以返回一個預設動作，或者讓它出錯以便追蹤
            return 0.5 # 返回中間位置作為安全的回退

        obs_tensor = torch.tensor(obs, dtype=torch.float32).to(self.device).unsqueeze(0)
        with torch.no_grad():
            action_continuous = self.model(obs_tensor)
        return action_continuous.squeeze().item()