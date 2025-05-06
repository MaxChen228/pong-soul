import os
import yaml
from utils import resource_path # <--- 加入這行

class LevelManager:
    def __init__(self, models_folder="models"):
        self.models_folder = models_folder
        self.model_files = sorted([
            f for f in os.listdir(models_folder) if f.endswith(".pth")
        ])
        self.current_level = 0

    def get_current_model_path(self):
        if self.current_level < len(self.model_files):
            return os.path.join(self.models_folder, self.model_files[self.current_level])
        return None

    def get_current_config(self):
        if not self.model_files or self.current_level >= len(self.model_files): # 增加邊界檢查
            print(f"Warning: No model files available or current_level out of bounds.")
            return {}

        model_filename = self.model_files[self.current_level]
        yaml_filename = model_filename.replace(".pth", ".yaml")

        # self.models_folder 已經是 resource_path("models") 的結果，是絕對路徑
        absolute_yaml_path = os.path.join(self.models_folder, yaml_filename)

        if os.path.exists(absolute_yaml_path):
            try:
                with open(absolute_yaml_path, 'r') as f:
                    return yaml.safe_load(f)
            except Exception as e:
                print(f"Error loading YAML file {absolute_yaml_path}: {e}")
                return {} # 或其他錯誤處理
        else:
            print(f"Warning: Config file not found at {absolute_yaml_path}")
        return {}

    def advance_level(self):
        self.current_level += 1
        return self.current_level < len(self.model_files)
