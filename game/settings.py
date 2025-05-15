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
        "gameplay.player_move_speed": 0.03, # 新增備用值
        "gameplay.max_trail_length": 20,    # 新增備用值
        "gameplay.defaults.mass": 1.0,
        "gameplay.defaults.e_ball_paddle": 1.0,
        "gameplay.defaults.mu_ball_paddle": 0.4,
        "gameplay.defaults.enable_spin": True,
        "gameplay.defaults.speed_increment": 0.002,
        "gameplay.defaults.speed_scale_every": 3,
        "physics.magnus_factor": 0.01,
        "ball_behavior.initial_speed": 0.02,
        "ball_behavior.initial_angle_deg_range": [-60, 60],
        "ball_behavior.initial_direction_serves_down": True,
        "theme.active_theme_name": "Retro Arcade",
    }

    # 屬性名稱到 YAML 鍵的映射
    _key_map = {
        "BACKGROUND_MUSIC_VOLUME": "audio.background_music_volume",
        "CLICK_SOUND_VOLUME": "audio.click_sound_volume",
        "COUNTDOWN_SOUND_VOLUME": "audio.countdown_sound_volume",
        "SLOWMO_SOUND_VOLUME": "audio.slowmo_sound_volume",
        "FREEZE_DURATION_MS": "gameplay.freeze_duration_ms",
        "COUNTDOWN_SECONDS": "gameplay.countdown_seconds",
        "PLAYER_MOVE_SPEED": "gameplay.player_move_speed", # 新增映射
        "MAX_TRAIL_LENGTH": "gameplay.max_trail_length",    # 新增映射
        "ENV_DEFAULT_MASS": "gameplay.defaults.mass",
        "ENV_DEFAULT_E_BALL_PADDLE": "gameplay.defaults.e_ball_paddle",
        "ENV_DEFAULT_MU_BALL_PADDLE": "gameplay.defaults.mu_ball_paddle",
        "ENV_DEFAULT_ENABLE_SPIN": "gameplay.defaults.enable_spin",
        "ENV_DEFAULT_SPEED_INCREMENT": "gameplay.defaults.speed_increment",
        "ENV_DEFAULT_SPEED_SCALE_EVERY": "gameplay.defaults.speed_scale_every",
        "PHYSICS_MAGNUS_FACTOR": "physics.magnus_factor",
        "BALL_INITIAL_SPEED": "ball_behavior.initial_speed",
        "BALL_INITIAL_ANGLE_DEG_RANGE": "ball_behavior.initial_angle_deg_range",
        "BALL_INITIAL_DIRECTION_SERVES_DOWN": "ball_behavior.initial_direction_serves_down",
        "ACTIVE_THEME_NAME": "theme.active_theme_name",
    }

    # 內部類別，保持 GameMode 的存取方式
    class GameMode:
        PLAYER_VS_AI = "PVA"
        PLAYER_VS_PLAYER = "PVP"

    def __new__(cls, *args, **kwargs):
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
                if value is None and default_fallback_value is not None:
                    value = default_fallback_value
            
            cls._initialized_settings[name] = value
            return value
        else:
            if hasattr(cls, name):
                 return getattr(cls, name)
            raise AttributeError(f"'{cls.__name__}' has no attribute '{name}' or mapping for it.")

class _SettingsProxy:
    GameMode = _GameSettingsSingleton.GameMode

    def __init__(self):
        pass

    def __getattr__(self, name):
        return _GameSettingsSingleton._get_setting_value(name)

    def __setattr__(self, name, value):
        if name == "_config_manager":
            _GameSettingsSingleton._config_manager = value
            _GameSettingsSingleton._initialized_settings.clear()
            if _GameSettingsSingleton._config_manager and hasattr(_GameSettingsSingleton._config_manager, '_preload_global_settings') and not _GameSettingsSingleton._config_manager._global_settings :
                 print("[GameSettings] ConfigManager assigned, attempting to ensure global settings are loaded if not already.")
        else:
            super().__setattr__(name, value)

GameSettings = _SettingsProxy()