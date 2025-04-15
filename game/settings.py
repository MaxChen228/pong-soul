# settings.py（改良後）

class GameSettings:
    """
    此類僅存放「全域遊戲設定」，不再包含任何技能參數。
    例如：音量、FPS、Theme選擇、freeze時間等。
    """

    # === 音量設定 ===
    BACKGROUND_MUSIC_VOLUME = 0.2
    CLICK_SOUND_VOLUME = 0.7
    COUNTDOWN_SOUND_VOLUME = 0.7
    SLOWMO_SOUND_VOLUME = 1.0  # （可自行斟酌是否放 skill_config）

    # === 其他全域參數 ===
    FREEZE_DURATION_MS = 500
    COUNTDOWN_SECONDS = 3

    # === 主題設定 ===
    ACTIVE_THEME_NAME = "Chinese Traditional"
    # 若要管理其它可用主題之類，也可在這裡

    # 你可以再補充其他「真正通用」的參數…
    # 例如螢幕尺寸、FPS上限…等

