# game/config_manager.py
import yaml
import os
from utils import resource_path # 從您專案的 utils 導入

DEBUG_CONFIG_MANAGER = True

class ConfigManager:
    def __init__(self):
        self._cache = {}
        self._global_settings = {} # <--- 新增用於存放全域設定的字典
        if DEBUG_CONFIG_MANAGER:
            print("[ConfigManager] Initializing...")
        self._preload_global_settings() # <--- 呼叫新的預載入方法
        if DEBUG_CONFIG_MANAGER:
            print("[ConfigManager] Initialization complete (global settings preloaded).")
    def _preload_global_settings(self):
        # 注意：路徑相對於專案根目錄，resource_path 會處理
        global_settings_path = "config/global_settings.yaml"
        data = self._load_yaml_file(global_settings_path) # 使用現有的 _load_yaml_file
        if data:
            self._global_settings = data
            if DEBUG_CONFIG_MANAGER:
                print(f"[ConfigManager] Global settings loaded from: {global_settings_path}")
        else:
            if DEBUG_CONFIG_MANAGER:
                print(f"[ConfigManager] WARNING: Global settings file not found or failed to load at '{global_settings_path}'. Using empty defaults.")
            self._global_settings = {} # 確保 self._global_settings 至少是一個空字典

    def get_global_setting(self, key_string, default=None):
        """
        獲取全域設定值。支援使用點分隔的巢狀鍵。
        例如: "audio.background_music_volume"
        """
        keys = key_string.split('.')
        value = self._global_settings
        try:
            for key in keys:
                if isinstance(value, dict): # 確保目前層級是字典
                    value = value[key]
                else: # 如果路徑中的某一層不是字典，則無法繼續深入
                    if DEBUG_CONFIG_MANAGER:
                        print(f"[ConfigManager] Warning: Key '{key}' in '{key_string}' does not lead to a dictionary.")
                    return default
            return value
        except KeyError:
            if DEBUG_CONFIG_MANAGER:
                print(f"[ConfigManager] Global setting key '{key_string}' not found. Returning default: {default}")
            return default
        except Exception as e:
            if DEBUG_CONFIG_MANAGER:
                print(f"[ConfigManager] Error accessing global setting '{key_string}': {e}. Returning default: {default}")
            return default

    def _load_yaml_file(self, file_path_relative_to_assets_or_models):
        """
        從相對於專案根目錄的 'assets' 或 'models' 等已知基礎資料夾載入 YAML 檔案。
        實際路徑將通過 resource_path 處理。
        """
        # 注意：這裡的 file_path_relative_to_assets_or_models 應該是
        # 像 "models/level1.yaml" 這樣的路徑，resource_path 會處理打包後的情況。
        # 或者，如果傳入的是已經由 resource_path 處理過的絕對路徑，則直接使用。
        # 為了與 LevelManager 現有邏輯（models_folder 已是絕對路徑）配合，
        # 此方法暫時假設傳入的 file_path 可能是相對於 models 資料夾的，
        # 或者是一個可以直接使用的路徑。 LevelManager 會負責構造正確的路徑。

        # 簡化：假設傳入的是 resource_path 可以處理的相對路徑，或者已經是絕對路徑
        absolute_path = resource_path(file_path_relative_to_assets_or_models)

        if absolute_path in self._cache:
            if DEBUG_CONFIG_MANAGER:
                print(f"[ConfigManager] Returning cached data for: {absolute_path}")
            return self._cache[absolute_path]

        if not os.path.exists(absolute_path):
            if DEBUG_CONFIG_MANAGER:
                print(f"[ConfigManager] YAML file not found at: {absolute_path}")
            return None # 或拋出錯誤

        try:
            with open(absolute_path, 'r', encoding='utf-8') as f:
                data = yaml.safe_load(f)
            self._cache[absolute_path] = data
            if DEBUG_CONFIG_MANAGER:
                print(f"[ConfigManager] Loaded and cached YAML file: {absolute_path}")
            return data
        except yaml.YAMLError as e:
            if DEBUG_CONFIG_MANAGER:
                print(f"[ConfigManager] Error parsing YAML file {absolute_path}: {e}")
            # 發生錯誤時，可以選擇快取一個錯誤標記或 None，避免重複嘗試解析錯誤檔案
            self._cache[absolute_path] = None # 快取 None 表示讀取失敗
            return None
        except Exception as e:
            if DEBUG_CONFIG_MANAGER:
                print(f"[ConfigManager] Unexpected error loading YAML file {absolute_path}: {e}")
            self._cache[absolute_path] = None
            return None

    def get_level_config(self, level_yaml_filename_only):
        """
        獲取指定關卡的設定。
        level_yaml_filename_only: 例如 "level1.yaml"
        """
        # 假設關卡 YAML 檔案都存放在 "models" 資料夾下
        # LevelManager 在呼叫時會提供 models 資料夾下的 YAML 檔案名
        file_path = os.path.join("models", level_yaml_filename_only)
        return self._load_yaml_file(file_path)

    # 未來可以添加更多 get_xxx_config 方法，例如 get_skill_config, get_global_settings 等

# 全域 ConfigManager 實例 (可選，但方便在專案中各處使用同一個實例)
# 如果選擇使用全域實例，需要在 main.py 或 GameApp 初始化時創建它
# config_manager_instance = ConfigManager()