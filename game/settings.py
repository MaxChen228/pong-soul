# game/settings.py
import pygame # Required for pygame.font.init() in theme.py's initial load if not handled before

# GameApp 的 config_manager 實例需要在 GameSettings 類別屬性被實際存取之前被賦值。
# 我們將在 GameApp 初始化時設定 GameSettings._config_manager

# Forward declaration for type hinting if game.theme is imported here,
# but it's better if game.theme imports GameSettings and GameSettings doesn't directly import game.theme
# to avoid circular dependencies at module level. We'll call theme.reload_active_style via a string path or lambda.
# For simplicity now, we'll rely on game.theme being imported elsewhere and its functions available.

class _GameSettingsSingleton:
    _instance = None
    _config_manager = None
    _initialized_settings = {}

    _fallback_settings = {
        "audio.background_music_volume": 0.1,
        "audio.click_sound_volume": 0.5,
        "audio.countdown_sound_volume": 0.5,
        "audio.slowmo_sound_volume": 0.8,
        "gameplay.freeze_duration_ms": 500,
        "gameplay.countdown_seconds": 3,
        "gameplay.player_move_speed": 0.03,
        "gameplay.max_trail_length": 20,
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
        "theme.active_theme_name": "Retro Arcade", # This is the key for the active theme
    }

    _key_map = {
        "BACKGROUND_MUSIC_VOLUME": "audio.background_music_volume",
        "CLICK_SOUND_VOLUME": "audio.click_sound_volume",
        "COUNTDOWN_SOUND_VOLUME": "audio.countdown_sound_volume",
        "SLOWMO_SOUND_VOLUME": "audio.slowmo_sound_volume",
        "FREEZE_DURATION_MS": "gameplay.freeze_duration_ms",
        "COUNTDOWN_SECONDS": "gameplay.countdown_seconds",
        "PLAYER_MOVE_SPEED": "gameplay.player_move_speed",
        "MAX_TRAIL_LENGTH": "gameplay.max_trail_length",
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
        "ACTIVE_THEME_NAME": "theme.active_theme_name", # Maps to the YAML key
    }

    class GameMode:
        PLAYER_VS_AI = "PVA"
        PLAYER_VS_PLAYER = "PVP"

    def __new__(cls, *args, **kwargs):
        if not cls._instance:
            cls._instance = super().__new__(cls, *args, **kwargs)
        return cls._instance

    @classmethod
    def _get_setting_value(cls, name):
        if name in cls._initialized_settings and name != "ACTIVE_THEME_NAME": # Don't cache ACTIVE_THEME_NAME if we want it to be always fresh from _global_settings
            return cls._initialized_settings[name]

        yaml_key = cls._key_map.get(name)
        value = None

        if yaml_key:
            default_fallback_value = cls._fallback_settings.get(yaml_key)
            # For ACTIVE_THEME_NAME, always try to get it from _global_settings if ConfigManager is present,
            # as it might have been changed at runtime.
            if name == "ACTIVE_THEME_NAME" and cls._config_manager and cls._config_manager._global_settings:
                 # Try to get from runtime _global_settings first
                 current_theme_name = cls._config_manager.get_global_setting(yaml_key, None)
                 if current_theme_name is not None:
                     value = current_theme_name
                 else: # Fallback to initialized or hardcoded if not in runtime _global_settings (shouldn't happen if set_active_theme works)
                     value = default_fallback_value
                 # We don't cache ACTIVE_THEME_NAME in _initialized_settings here to ensure it's re-read
                 # if set_active_theme modifies _global_settings directly.
                 # However, for simplicity, current _get_setting_value caches all.
                 # Let's ensure set_active_theme clears the cache for ACTIVE_THEME_NAME.

            elif cls._config_manager is None:
                if name != "ACTIVE_THEME_NAME": # Avoid redundant warning if already warned by theme.py
                    print(f"[GameSettings] WARNING: ConfigManager not set when accessing '{name}'. Returning hardcoded fallback: {default_fallback_value}")
                value = default_fallback_value
            else:
                value = cls._config_manager.get_global_setting(yaml_key, default_fallback_value)
                if value is None and default_fallback_value is not None:
                    value = default_fallback_value
            
            if name != "ACTIVE_THEME_NAME": # Only cache non-theme name values this way
                 cls._initialized_settings[name] = value
            elif name == "ACTIVE_THEME_NAME" and value is not None: # Specifically handle caching for theme name after first successful read
                 cls._initialized_settings[name] = value


            return value
        else:
            if hasattr(cls, name):
                 return getattr(cls, name)
            raise AttributeError(f"'{cls.__name__}' has no attribute '{name}' or mapping for it.")

    @classmethod
    def _update_runtime_active_theme_name(cls, theme_name):
        """Internal method to update the theme name in runtime settings."""
        yaml_key = cls._key_map.get("ACTIVE_THEME_NAME")
        if not yaml_key:
            print("[GameSettings] ERROR: ACTIVE_THEME_NAME key not found in _key_map.")
            return

        # Update in-memory _global_settings if ConfigManager is available
        if cls._config_manager and hasattr(cls._config_manager, '_global_settings'):
            # Need to navigate the dict structure for "theme.active_theme_name"
            keys = yaml_key.split('.')
            current_level = cls._config_manager._global_settings
            try:
                for i, key_part in enumerate(keys[:-1]):
                    if key_part not in current_level or not isinstance(current_level[key_part], dict):
                        current_level[key_part] = {} # Create intermediate dict if not exists
                    current_level = current_level[key_part]
                current_level[keys[-1]] = theme_name
            except Exception as e:
                print(f"[GameSettings] Error updating _global_settings for theme: {e}")


        # Update the specific cache for ACTIVE_THEME_NAME
        cls._initialized_settings["ACTIVE_THEME_NAME"] = theme_name
        if cls._config_manager: # Also clear the general cache in ConfigManager if it's more complex
            pass # ConfigManager's main cache is for file content, not individual parsed keys from GameSettings.

        print(f"[GameSettings] Runtime ACTIVE_THEME_NAME set to: {theme_name}")


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
            if _GameSettingsSingleton._config_manager and \
               hasattr(_GameSettingsSingleton._config_manager, '_preload_global_settings') and \
               not _GameSettingsSingleton._config_manager._global_settings :
                 print("[GameSettings] ConfigManager assigned, attempting to ensure global settings are loaded if not already.")
        else:
            super().__setattr__(name, value)

    def set_active_theme(self, theme_name: str):
        """
        Sets the active theme name at runtime and triggers a style reload.
        """
        print(f"[GameSettings.set_active_theme] Attempting to set theme to: {theme_name}")
        # 1. Update the internal setting value
        _GameSettingsSingleton._update_runtime_active_theme_name(theme_name)

        # 2. Trigger a reload of styles in game.theme
        # This is a common way to handle cross-module updates without direct imports
        # by relying on the module being loaded and its functions accessible.
        try:
            import game.theme
            if hasattr(game.theme, 'reload_active_style'):
                game.theme.reload_active_style()
                print(f"[GameSettings.set_active_theme] Called game.theme.reload_active_style() for '{theme_name}'.")
            else:
                print("[GameSettings.set_active_theme] ERROR: game.theme.reload_active_style function not found!")
        except ImportError:
            print("[GameSettings.set_active_theme] ERROR: Could not import game.theme to reload style.")
        except Exception as e:
            print(f"[GameSettings.set_active_theme] ERROR during style reload: {e}")

GameSettings = _SettingsProxy()