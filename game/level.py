import os
import yaml
from utils import resource_path # <--- 加入這行

class LevelManager:
    def __init__(self, config_manager, models_folder="models"): # <--- 新增 config_manager 參數
        self.config_manager = config_manager # <--- 儲存 config_manager 實例
        self.models_folder = models_folder # models_folder 仍然有用，用於列出 .pth 檔案和推斷 .yaml 檔名
        self.model_files = sorted([
            f for f in os.listdir(models_folder) if f.endswith(".pth")
        ])
        self.current_level = 0

    def get_current_model_path(self):
        if self.current_level < len(self.model_files):
            return os.path.join(self.models_folder, self.model_files[self.current_level])
        return None

    def get_current_config(self):
        if not self.model_files or self.current_level >= len(self.model_files):
            # 使用 ConfigManager 的除錯輸出風格 (如果需要)
            # print(f"[LevelManager] Warning: No model files available or current_level out of bounds.")
            return {} # 返回空字典表示沒有有效的設定

        model_filename = self.model_files[self.current_level]
        yaml_filename_only = model_filename.replace(".pth", ".yaml") # 只取檔案名稱

        # 使用 ConfigManager 獲取設定
        # ConfigManager 的 get_level_config 會處理路徑和快取
        config_data = self.config_manager.get_level_config(yaml_filename_only)

        if config_data is None: # 如果 ConfigManager 返回 None (表示讀取失敗或檔案不存在)
            # print(f"[LevelManager] Warning: ConfigManager failed to load config for {yaml_filename_only}")
            return {} # 確保返回字典
        return config_data

    def advance_level(self):
        self.current_level += 1
        return self.current_level < len(self.model_files)
