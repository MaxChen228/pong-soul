import torch
import torch.nn as nn
import torch.nn.functional as F # <--- 新增導入
import math # <--- 新增導入

# vvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvv #
# START OF COPIED NoisyLinear and QNet FROM YOUR qnet.py
# 請將您 qnet.py 中的 NoisyLinear 和 QNet 類別定義完整複製到此處
# 例如：
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
    def __init__(self, model_path, device='cpu'): # model_path 是從 main.py 傳來的絕對路徑
        self.device = device
        # _load_model 使用的是已經處理好的絕對路徑
        print(f"[DEBUG_AI_AGENT] Attempting to load model using QNet definition: {QNet}") # 排錯訊息
        self.model = self._load_model(model_path)
        self.model.eval()

    def _load_model(self, model_path): # model_path is absolute
        # QNet is the Dueling Noisy QNet from your qnet.py,
        # already integrated in Step 1.
        model = QNet(input_dim=7, output_dim=3)
        print(f"[DEBUG_AI_AGENT] Initialized QNet (Dueling Noisy) with input_dim=7, output_dim=3 in _load_model")

        checkpoint = torch.load(model_path, map_location=self.device)

        original_state_dict = None
        if 'modelB' in checkpoint:
            original_state_dict = checkpoint['modelB']
            print("[DEBUG_AI_AGENT] Found state_dict under 'modelB' key.")
        elif 'model' in checkpoint:
            original_state_dict = checkpoint['model']
            print("[DEBUG_AI_AGENT] Found state_dict under 'model' key.")
        else:
            # Fallback: if the checkpoint IS the state_dict itself (less likely given train_iterative.py)
            # Or if keys are different, this will likely fail later or here.
            # For robustness, if 'modelB' or 'model' not found, assume checkpoint might be the state_dict itself.
            # However, based on train_iterative.py, this path should ideally not be taken.
            # A more robust check for your specific saving format is better.
            # The current RuntimeError from your traceback suggests original_state_dict IS found.
            # The issue is the content of original_state_dict.
            print(f"[ERROR_AI_AGENT] CRITICAL: state_dict not found in checkpoint under 'modelB' or 'model' keys. Checkpoint keys: {list(checkpoint.keys())}")
            raise KeyError("Model state_dict not found in checkpoint under 'modelB' or 'model' keys.")

        # Check if the state_dict matches the new Dueling Noisy QNet architecture
        # or if it's from the old simpler "fc.X" architecture.
        is_new_architecture = any(k.startswith(("features.", "fc_V.", "fc_A.")) for k in original_state_dict.keys())

        if is_new_architecture:
            print("[DEBUG_AI_AGENT] Detected NEW QNet architecture (features, fc_V, fc_A). Loading directly (strict=True).")
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
                # Map the last linear layer (fc.4) to the new Dueling heads (fc_A and fc_V)
                # This is an approximation, as the Dueling architecture splits value and advantage.
                # We will assign fc.4 to fc_A (advantage) and a modified version to fc_V (value).

                # features.0.weight, features.0.bias (mapped from fc.0)
                # features.2.weight, features.2.bias (mapped from fc.2)

                # For fc_A (Advantage stream)
                # The NoisyLinear layers in the new QNet expect 'weight_mu' and 'bias_mu' for the mean weights.
                mapped_state_dict["fc_A.weight_mu"] = original_state_dict["fc.4.weight"]
                mapped_state_dict["fc_A.bias_mu"] = original_state_dict["fc.4.bias"]
                print("[DEBUG_AI_AGENT] Mapped fc.4 to fc_A.weight_mu and fc_A.bias_mu.")

                # For fc_V (Value stream)
                # A common practice for splitting a single output layer into V and A
                # is to initialize V in a way that doesn't drastically alter the initial combined output.
                # Here, we use a simple approach like your test scripts:
                # fc_V.weight_mu will be the mean of fc.4.weight across the output dimension.
                # fc_V.bias_mu will be the mean of fc.4.bias.
                # This is a heuristic. The NoisyLinear's sigma and epsilon will be initialized by NoisyLinear itself.
                mapped_state_dict["fc_V.weight_mu"] = original_state_dict["fc.4.weight"].mean(dim=0, keepdim=True)
                mapped_state_dict["fc_V.bias_mu"] = original_state_dict["fc.4.bias"].mean().unsqueeze(0)
                print("[DEBUG_AI_AGENT] Mapped mean of fc.4 to fc_V.weight_mu and fc_V.bias_mu.")
            else:
                print("[ERROR_AI_AGENT] CRITICAL: Old architecture state_dict is missing 'fc.4.weight' or 'fc.4.bias'. Cannot map to Dueling heads.")
                # Handle this error appropriately, maybe raise an exception or try to load what's available if that makes sense.
                # For now, we'll proceed and load_state_dict will likely complain about missing fc_V and fc_A keys.

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
        # 在將 obs 傳遞給模型前，確保 NoisyLinear 的噪聲被重置 (如果 QNet 有 reset_noise 方法)
        if hasattr(self.model, 'reset_noise'): # <--- 新增檢查
            self.model.reset_noise() # <--- 為 NoisyNet 新增

        obs_tensor = torch.tensor(obs, dtype=torch.float32).to(self.device)
        # NoisyNet 在推斷時不需要額外的隨機性，epsilon-greedy 策略通常在訓練時使用
        # select_action 應該總是利用學到的 Q 值
        with torch.no_grad():
            q_values = self.model(obs_tensor.unsqueeze(0)) # <--- 注意: 模型通常期望批次維度
            action = torch.argmax(q_values).item()
        return action