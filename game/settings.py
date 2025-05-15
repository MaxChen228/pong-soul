# game/settings.py

# GameApp 的 config_manager 實例需要在 GameSettings 類別屬性被實際存取之前被賦值。
# 我們將在 GameApp 初始化時設定 GameSettings._config_manager

class _GameSettingsSingleton:
    _instance = None
    _config_manager = None # 將由 GameApp 初始化
    _initialized_settings = {} # 用於快取已載入的設定值

    # 硬編碼的備用預設值，以防 YAML 讀取失敗或鍵不存在
    _fallback_settings = {
        "audio.background_music_volume": 0.1,
        "audio.click_sound_volume": 0.5,
        "audio.countdown_sound_volume": 0.5,
        "audio.slowmo_sound_volume": 0.8,
        "gameplay.freeze_duration_ms": 500,
        "gameplay.countdown_seconds": 3,
        "theme.active_theme_name": "Retro Arcade", # 重要的備用值
    }

    # 屬性名稱到 YAML 鍵的映射
    _key_map = {
        "BACKGROUND_MUSIC_VOLUME": "audio.background_music_volume",
        "CLICK_SOUND_VOLUME": "audio.click_sound_volume",
        "COUNTDOWN_SOUND_VOLUME": "audio.countdown_sound_volume",
        "SLOWMO_SOUND_VOLUME": "audio.slowmo_sound_volume",
        "FREEZE_DURATION_MS": "gameplay.freeze_duration_ms",
        "COUNTDOWN_SECONDS": "gameplay.countdown_seconds",
        "ACTIVE_THEME_NAME": "theme.active_theme_name",
    }

    # 內部類別，保持 GameMode 的存取方式
    class GameMode:
        PLAYER_VS_AI = "PVA"
        PLAYER_VS_PLAYER = "PVP"

    def __new__(cls, *args, **kwargs):
        # 實現單例模式，確保 GameSettings 只有一個共享狀態的 "實例" 感知
        # 但我們實際上會透過 GameSettings 這個名稱來直接訪問它的 "類別" 屬性
        # 這裡的 __new__ 和 _instance 更多是為了結構化
        if not cls._instance:
            cls._instance = super().__new__(cls, *args, **kwargs)
        return cls._instance

    @classmethod
    def _get_setting_value(cls, name):
        if name in cls._initialized_settings:
            return cls._initialized_settings[name]

        yaml_key = cls._key_map.get(name)
        value = None

        if yaml_key:
            default_fallback_value = cls._fallback_settings.get(yaml_key)
            if cls._config_manager is None:
                print(f"[GameSettings] WARNING: ConfigManager not set when accessing '{name}'. Returning hardcoded fallback: {default_fallback_value}")
                value = default_fallback_value
            else:
                value = cls._config_manager.get_global_setting(yaml_key, default_fallback_value)
                # 如果 ConfigManager 返回了 None (表示 YAML 中也沒有，且 get_global_setting 的 default 也是 None)
                # 並且我們有一個硬編碼的備用值，則使用它。
                if value is None and default_fallback_value is not None:
                    value = default_fallback_value
            
            cls._initialized_settings[name] = value # 快取結果
            return value
        else:
            # 如果 name 不是已知的設定鍵，嘗試看它是否是 GameMode 或其他直接定義的屬性
            if hasattr(cls, name): #例如 GameMode
                 return getattr(cls, name)
            raise AttributeError(f"'{cls.__name__}' has no attribute '{name}' or mapping for it.")

    # 我們將使用 __dict__ 和 __getattr__ 的組合來使 GameSettings.XXX 工作
    # 或者更簡單，我們將 GameSettings 的實例賦值給模組級別的變數
    # 讓我們創建一個 "代理" 類別，其實例將被賦值給 GameSettings 這個名稱

class _SettingsProxy:
    # GameMode 仍然可以直接作為 GameSettings.GameMode 訪問
    GameMode = _GameSettingsSingleton.GameMode

    def __init__(self):
        # 這個 __init__ 實際上不會被多次調用，因為我們將其實例賦值給 GameSettings
        pass

    def __getattr__(self, name):
        # 當 GameSettings.XXX 被訪問時，此方法被調用
        # if name == "_config_manager": # 避免無限遞歸
        #     # 如果有人試圖 GameSettings._config_manager, 讓他直接訪問單例的
        #     return _GameSettingsSingleton._config_manager
        return _GameSettingsSingleton._get_setting_value(name)

    def __setattr__(self, name, value):
        # 允許 GameSettings._config_manager = self.config_manager
        if name == "_config_manager":
            _GameSettingsSingleton._config_manager = value
            # 清空已初始化的設定，以便下次訪問時重新從 ConfigManager 讀取
            _GameSettingsSingleton._initialized_settings.clear()
            if _GameSettingsSingleton._config_manager and hasattr(_GameSettingsSingleton._config_manager, '_preload_global_settings') and not _GameSettingsSingleton._config_manager._global_settings :
                 print("[GameSettings] ConfigManager assigned, attempting to ensure global settings are loaded if not already.")
                 # _GameSettingsSingleton._config_manager._preload_global_settings() # 確保此時全域設定被載入
        else:
            super().__setattr__(name, value)


# 在模組級別，我們用 _SettingsProxy 的一個實例替換掉 GameSettings 這個名稱
# 這樣，GameSettings.XXX 就會調用 _SettingsProxy 的 __getattr__
# 而 GameSettings._config_manager = xxx 會調用 _SettingsProxy 的 __setattr__
GameSettings = _SettingsProxy()