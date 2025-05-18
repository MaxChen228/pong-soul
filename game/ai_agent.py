import torch
import torch.nn as nn
import torch.nn.functional as F # <--- 確保導入
import math # <--- 確保導入

# vvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvv #
# START OF COPIED NoisyLinear and QNet FROM YOUR qnet.py
# (這部分保持不變，因為 dqn_definitions.py 中的定義與此處相同)
class NoisyLinear(nn.Module):
    def __init__(self, in_features, out_features, sigma_init=0.017):
        super().__init__()
        self.in_features  = in_features
        self.out_features = out_features
        self.sigma_init   = sigma_init

        # 可训练参数 μ 和 σ
        self.weight_mu    = nn.Parameter(torch.empty(out_features, in_features))
        self.bias_mu      = nn.Parameter(torch.empty(out_features))
        self.weight_sigma = nn.Parameter(torch.empty(out_features, in_features))
        self.bias_sigma   = nn.Parameter(torch.empty(out_features))

        # 噪声缓存
        self.register_buffer('weight_epsilon', torch.empty(out_features, in_features))
        self.register_buffer('bias_epsilon',   torch.empty(out_features))

        self.reset_parameters()
        self.reset_noise()

    def reset_parameters(self):
        mu_range = 1.0 / math.sqrt(self.in_features)
        self.weight_mu.data.uniform_(-mu_range, mu_range)
        self.bias_mu.data.uniform_(-mu_range, mu_range)
        self.weight_sigma.data.fill_(self.sigma_init)
        self.bias_sigma.data.fill_(self.sigma_init)

    def reset_noise(self):
        # factorised Gaussian noise
        def scale_noise(size):
            x = torch.randn(size, device=self.weight_mu.device) # <--- 注意: device
            return x.sign().mul_(x.abs().sqrt_())
        eps_in  = scale_noise(self.in_features)
        eps_out = scale_noise(self.out_features)
        self.weight_epsilon.copy_(eps_out.ger(eps_in))
        self.bias_epsilon.copy_(eps_out)

    def forward(self, x):
        if self.training:
            weight = self.weight_mu + self.weight_sigma * self.weight_epsilon
            bias   = self.bias_mu   + self.bias_sigma   * self.bias_epsilon
        else:
            weight = self.weight_mu
            bias   = self.bias_mu
        return F.linear(x, weight, bias)

class QNet(nn.Module):
    def __init__(self, input_dim=7, output_dim=3): # <--- 確認參數
        super().__init__()
        # 特征提取层不含噪声
        self.features = nn.Sequential(
            nn.Linear(input_dim, 64),
            nn.ReLU(),
            nn.Linear(64, 64),
            nn.ReLU(),
        )
        # 使用 NoisyLinear 构建 dueling head
        self.fc_V = NoisyLinear(64, 1)
        self.fc_A = NoisyLinear(64, output_dim)

    def reset_noise(self):
        for m in self.modules():
            if isinstance(m, NoisyLinear):
                m.reset_noise()

    def forward(self, x):
        h = self.features(x)
        V = self.fc_V(h)  # [B,1]
        A = self.fc_A(h)  # [B,output_dim]
        return V + (A - A.mean(dim=1, keepdim=True))

# END OF COPIED NoisyLinear and QNet
# ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^ #

class AIAgent:
    # ⭐️ 修改 __init__ 方法以接受維度參數
    def __init__(self, model_path, device='cpu', input_dim=7, output_dim=3):
        self.device = device
        self.input_dim = input_dim   # ⭐️ 儲存維度
        self.output_dim = output_dim # ⭐️ 儲存維度
        # ⭐️ 更新 DEBUG 訊息
        print(f"[DEBUG_AI_AGENT] AIAgent.__init__: Attempting to load model using QNet definition: <class 'game.ai_agent.QNet'> with input_dim={self.input_dim}, output_dim={self.output_dim}")
        self.model = self._load_model(model_path)
        self.model.eval()

    def _load_model(self, model_path): # model_path is absolute
        # ⭐️ 使用儲存的維度來初始化 QNet
        model = QNet(input_dim=self.input_dim, output_dim=self.output_dim)
        # ⭐️ 更新 DEBUG 訊息
        print(f"[DEBUG_AI_AGENT] AIAgent._load_model: Initialized QNet (Dueling Noisy) with input_dim={self.input_dim}, output_dim={self.output_dim}")

        checkpoint = torch.load(model_path, map_location=self.device)

        original_state_dict = None
        # ⭐️ 修改 state_dict 的獲取順序
        if 'model_state_dict' in checkpoint: # 優先檢查這個鍵
            original_state_dict = checkpoint['model_state_dict']
            print("[DEBUG_AI_AGENT] Found state_dict under 'model_state_dict' key.")
        elif 'modelB' in checkpoint:
            original_state_dict = checkpoint['modelB']
            print("[DEBUG_AI_AGENT] Found state_dict under 'modelB' key.")
        elif 'model' in checkpoint:
            original_state_dict = checkpoint['model']
            print("[DEBUG_AI_AGENT] Found state_dict under 'model' key.")
        else:
            print(f"[ERROR_AI_AGENT] CRITICAL: state_dict not found in checkpoint under 'model_state_dict', 'modelB', or 'model' keys. Checkpoint keys: {list(checkpoint.keys())}")
            raise KeyError("Model state_dict not found in checkpoint under 'model_state_dict', 'modelB', or 'model' keys.")

        # --- 後續的架構檢測和鍵名映射邏輯保持不變 ---
        # 重要的是，這裡的 QNet 實例 (model) 是用正確的 input_dim 和 output_dim 創建的。
        # 如果 original_state_dict 中的層的維度與之不匹配，load_state_dict 時仍會報錯。
        is_new_architecture = any(k.startswith(("features.", "fc_V.", "fc_A.")) for k in original_state_dict.keys())

        if is_new_architecture:
            print("[DEBUG_AI_AGENT] Detected NEW QNet architecture (features, fc_V, fc_A). Loading directly (strict=True).")
            # ⭐️ 確保這裡的 original_state_dict 中的層維度與 self.input_dim, self.output_dim 匹配
            model.load_state_dict(original_state_dict, strict=True)
        else:
            print("[DEBUG_AI_AGENT] Detected OLD QNet architecture (fc.0, fc.2, fc.4). Performing key mapping (strict=False).")
            mapped_state_dict = {}
            has_fc4 = "fc.4.weight" in original_state_dict and "fc.4.bias" in original_state_dict

            for k, v in original_state_dict.items():
                if k.startswith("fc.0."):
                    mapped_state_dict[k.replace("fc.0.", "features.0.")] = v
                elif k.startswith("fc.2."):
                    mapped_state_dict[k.replace("fc.2.", "features.2.")] = v
                elif not k.startswith("fc.4."): # Catch other unexpected keys if any
                    print(f"[DEBUG_AI_AGENT] Warning: Unexpected key '{k}' in old architecture state_dict. Skipping.")


            if has_fc4:
                # ⭐️ 這裡的映射假設 fc.4 的輸出維度與 self.output_dim 一致
                # ⭐️ 並且 fc.4 的輸入維度與 features 層的輸出維度 (64) 一致
                mapped_state_dict["fc_A.weight_mu"] = original_state_dict["fc.4.weight"]
                mapped_state_dict["fc_A.bias_mu"] = original_state_dict["fc.4.bias"]
                print("[DEBUG_AI_AGENT] Mapped fc.4 to fc_A.weight_mu and fc_A.bias_mu.")

                mapped_state_dict["fc_V.weight_mu"] = original_state_dict["fc.4.weight"].mean(dim=0, keepdim=True)
                mapped_state_dict["fc_V.bias_mu"] = original_state_dict["fc.4.bias"].mean().unsqueeze(0)
                print("[DEBUG_AI_AGENT] Mapped mean of fc.4 to fc_V.weight_mu and fc_V.bias_mu.")
            else:
                print("[ERROR_AI_AGENT] CRITICAL: Old architecture state_dict is missing 'fc.4.weight' or 'fc.4.bias'. Cannot map to Dueling heads.")

            try:
                model.load_state_dict(mapped_state_dict, strict=False)
                print("[DEBUG_AI_AGENT] Successfully loaded mapped state_dict with strict=False.")
            except RuntimeError as e:
                print(f"[ERROR_AI_AGENT] RuntimeError during model.load_state_dict with mapped_state_dict (strict=False): {e}")
                print(f"Mapped state_dict keys: {list(mapped_state_dict.keys())}")
                print("Model's expected (mu) keys for Dueling Noisy heads are like: 'fc_V.weight_mu', 'fc_A.bias_mu', etc.")
                print("Model's feature keys are like: 'features.0.weight', etc.")
                raise e

        return model.to(self.device)

    def select_action(self, obs):
        if hasattr(self.model, 'reset_noise'):
            self.model.reset_noise()

        obs_tensor = torch.tensor(obs, dtype=torch.float32).to(self.device)
        with torch.no_grad():
            q_values = self.model(obs_tensor.unsqueeze(0))
            action = torch.argmax(q_values).item()
        return action