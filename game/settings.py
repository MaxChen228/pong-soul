class GameSettings:
    # 音量設定（略）
    BACKGROUND_MUSIC_VOLUME = 0.5
    CLICK_SOUND_VOLUME = 0.7
    COUNTDOWN_SOUND_VOLUME = 0.7
    SLOWMO_SOUND_VOLUME = 1.0

    # 技能相關設定（略）
    SLOWMO_DURATION_MS = 2000
    SLOWMO_COOLDOWN_MS = 7000

    # 板子變長技能設定（新增這一區）
    LONG_PADDLE_DURATION_MS = 3000       # 技能持續 3 秒
    LONG_PADDLE_COOLDOWN_MS = 5000       # 技能冷卻 5 秒
    LONG_PADDLE_MULTIPLIER = 1.5         # 板子長度倍率
    # 技能條顏色（板子變長技能專屬）
    LONG_PADDLE_BAR_COLOR = (0, 100, 0)  # 綠色
    SLOWMO_BAR_COLOR = (0, 200, 255)
    # 技能視覺效果設定 (新增這個區塊)
    SLOWMO_TRAIL_COLOR = (0, 200, 255)  # slowmo 技能板子殘影顏色（淡藍色）

    # 技能選擇設定（一次只能一個）
    ACTIVE_SKILL = "slowmo"  # 可選值："slowmo" 或 "long_paddle"

    # 其他參數設定（略）
    FREEZE_DURATION_MS = 500
    COUNTDOWN_SECONDS = 3

    # ⭐️ 新增主題選擇參數：
    ACTIVE_THEME_NAME = "Chinese Traditional"
