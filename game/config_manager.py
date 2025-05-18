# game/config_manager.py
import yaml
import os
from utils import resource_path # 從您專案的 utils 導入

DEBUG_CONFIG_MANAGER = False # 保持您原有的 DEBUG 開關

class ConfigManager:
    def __init__(self):
        self._cache = {}
        self._global_settings = {} # 用於存放全域設定的字典
        if DEBUG_CONFIG_MANAGER:
            print("[ConfigManager] Initializing...")
        self._preload_global_settings() # 呼叫預載入方法
        # ⭐️ 新增：預載入技能設定
        self._preload_skill_configs()
        if DEBUG_CONFIG_MANAGER:
            print("[ConfigManager] Initialization complete (global and skill settings preloaded).")

    def _preload_global_settings(self):
        # ... (您原有的 _preload_global_settings 方法內容不變) ...
        global_settings_path = "config/global_settings.yaml"
        data = self._load_yaml_file(global_settings_path)
        if data:
            self._global_settings = data
            if DEBUG_CONFIG_MANAGER:
                print(f"[ConfigManager] Global settings loaded from: {global_settings_path}")
        else:
            if DEBUG_CONFIG_MANAGER:
                print(f"[ConfigManager] WARNING: Global settings file not found or failed to load at '{global_settings_path}'. Using empty defaults.")
            self._global_settings = {}

    # ⭐️ 新增：預載入技能設定的方法
    def _preload_skill_configs(self):
        skills_config_path = "config/skills_config.yaml"
        data = self._load_yaml_file(skills_config_path)
        if data:
            # 我們可以將其存在 _cache 中，或者如果 ConfigManager 需要直接提供它，
            # 則可以像 _global_settings 一樣存儲。
            # 為了讓 get_all_skill_configs 保持簡單，這裡確保它被 _load_yaml_file 快取。
            if DEBUG_CONFIG_MANAGER:
                print(f"[ConfigManager] Skill configs preloaded (cached) from: {skills_config_path}")
        else:
            if DEBUG_CONFIG_MANAGER:
                print(f"[ConfigManager] WARNING: Skill configs file not found or failed to load at '{skills_config_path}'.")

    def get_global_setting(self, key_string, default=None):
        # ... (您原有的 get_global_setting 方法內容不變) ...
        keys = key_string.split('.')
        value = self._global_settings
        try:
            for key in keys:
                if isinstance(value, dict):
                    value = value[key]
                else:
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


    def _load_yaml_file(self, file_path_relative_to_config_or_models): # 稍微修改了參數名以更清晰
        """
        從相對於專案根目錄的 'config' 或 'models' 等已知基礎資料夾載入 YAML 檔案。
        實際路徑將通過 resource_path 處理。
        """
        # ⭐️ 注意: resource_path 通常用於打包後的資源路徑，
        #    如果 'config' 目錄與執行的 main.py 在同一層級或 python PATH 可找到，
        #    直接使用相對路徑可能更適合開發。
        #    但為了與您現有的 utils.resource_path 保持一致，我們繼續使用它。
        #    確保 skills_config.yaml 位於 resource_path 可以解析的路徑下（例如，與 main.py 同級的 config/ 目錄）。
        absolute_path = resource_path(file_path_relative_to_config_or_models)

        if absolute_path in self._cache:
            if DEBUG_CONFIG_MANAGER:
                print(f"[ConfigManager] Returning cached data for: {absolute_path}")
            return self._cache[absolute_path]

        if not os.path.exists(absolute_path):
            if DEBUG_CONFIG_MANAGER:
                print(f"[ConfigManager] YAML file not found at: {absolute_path}")
            return None # 保持返回 None，讓調用者處理

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
            self._cache[absolute_path] = None # 標記為載入失敗
            return None
        except Exception as e:
            if DEBUG_CONFIG_MANAGER:
                print(f"[ConfigManager] Unexpected error loading YAML file {absolute_path}: {e}")
            self._cache[absolute_path] = None # 標記為載入失敗
            return None

    def get_level_config(self, level_yaml_filename_only):
        # ... (您原有的 get_level_config 方法內容不變) ...
        file_path = os.path.join("models", level_yaml_filename_only) # models 資料夾內的
        return self._load_yaml_file(file_path)

    # ⭐️ 新增的方法
    def get_all_skill_configs(self):
        """
        獲取所有技能的設定，從 'config/skills_config.yaml' 載入。
        """
        file_path = "config/skills_config.yaml" # 相對於專案根目錄或 resource_path 的基礎路徑
        # _load_yaml_file 會處理快取和檔案讀取
        configs = self._load_yaml_file(file_path)
        if configs is None:
            if DEBUG_CONFIG_MANAGER:
                print(f"[ConfigManager] get_all_skill_configs: Failed to load skill configs from '{file_path}'. Returning empty dict.")
            return {} # 如果檔案不存在或讀取失敗，返回空字典
        return configs