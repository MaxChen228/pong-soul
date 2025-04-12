import os
import yaml

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
        model_file = self.model_files[self.current_level]
        yaml_file = model_file.replace(".pth", ".yaml")
        yaml_path = os.path.join(self.models_folder, yaml_file)
        if os.path.exists(yaml_path):
            with open(yaml_path, 'r') as f:
                return yaml.safe_load(f)
        return {}

    def advance_level(self):
        self.current_level += 1
        return self.current_level < len(self.model_files)
