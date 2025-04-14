class GameSettings:
    # 音量設定（略）
    BACKGROUND_MUSIC_VOLUME = 0.2
    CLICK_SOUND_VOLUME = 0.7
    COUNTDOWN_SOUND_VOLUME = 0.7
    SLOWMO_SOUND_VOLUME = 1.0

    # 技能相關設定（略）
    SLOWMO_DURATION_MS = 3000
    SLOWMO_COOLDOWN_MS = 5000

    # 板子變長技能設定（新增這一區）
    LONG_PADDLE_DURATION_MS = 3000       # 技能持續 3 秒
    LONG_PADDLE_COOLDOWN_MS = 5000       # 技能冷卻 5 秒
    LONG_PADDLE_MULTIPLIER = 2         # 板子長度倍率
    # 技能條顏色（板子變長技能專屬）
    LONG_PADDLE_BAR_COLOR = (0, 100, 0)  # 綠色
    SLOWMO_BAR_COLOR = (0, 200, 255)
    # 技能視覺效果設定 (新增這個區塊)
    SLOWMO_TRAIL_COLOR = (0, 200, 255)  # slowmo 技能板子殘影顏色（淡藍色）

    # 技能特效設定（新增）
    SLOWMO_PADDLE_COLOR = (0, 150, 255)       # 時間暫停時的板子顏色
    SLOWMO_GLOW_COLOR = (0, 150, 255, 100)    # 板子周圍的光圈顏色 (RGBA，含透明度)
    SLOWMO_FOG_DURATION_MS = 800              # 技能結束後霧氣淡出的時間（毫秒）

    LONG_PADDLE_COLOR = (0, 255, 100)         # 板子變長時的顏色
    LONG_PADDLE_ANIMATION_MS = 300            # 板子拉伸動畫的持續時間（毫秒）

    # 技能選擇設定（一次只能一個）
    ACTIVE_SKILL = "slowmo"  # 可選值："slowmo" 或 "long_paddle"

    # 技能條滿能量拖曳線特效設定
    SKILL_BAR_TRAIL_COLOR = (255, 255, 255)  # 拖曳線顏色（白色）
    SKILL_BAR_TRAIL_LENGTH = 15  # 拖曳線的殘影數量

    # 其他參數設定（略）
    FREEZE_DURATION_MS = 500
    COUNTDOWN_SECONDS = 3
    # === Slowmo技能『時鐘特效』設定 ===
    SLOWMO_CLOCK_COLOR = (255, 255, 255, 100)  # 時鐘的顏色 (RGBA半透明白色)
    SLOWMO_CLOCK_RADIUS = 50                   # 時鐘的半徑大小
    SLOWMO_CLOCK_LINE_WIDTH = 4                # 時鐘指針的粗細


    # ⭐️ 新增主題選擇參數：
    ACTIVE_THEME_NAME = "Chinese Traditional"
