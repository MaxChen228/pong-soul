import torch
import torch.nn as nn

class QNet(nn.Module):
    def __init__(self, input_dim=6, output_dim=3):
        super(QNet, self).__init__()
        self.fc = nn.Sequential(
            nn.Linear(input_dim, 64),
            nn.ReLU(),
            nn.Linear(64, 64),
            nn.ReLU(),
            nn.Linear(64, output_dim)
        )

    def forward(self, x):
        return self.fc(x)

class AIAgent:
    def __init__(self, model_path, device='cpu'):
        self.device = device
        self.model = self._load_model(model_path)
        self.model.eval()

    def _load_model(self, model_path):
        model = QNet()
        checkpoint = torch.load(model_path, map_location=self.device)
        model.load_state_dict(checkpoint['model'])  # ✅ 這次名稱對得上了
        return model.to(self.device)

    def select_action(self, obs):
        obs_tensor = torch.tensor(obs, dtype=torch.float32).to(self.device)
        with torch.no_grad():
            q_values = self.model(obs_tensor)
            action = torch.argmax(q_values).item()
        return action
