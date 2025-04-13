# game/settings.py

# 遊戲全域設定參數表

class GameSettings:
    # ====== 🎵 音量設定 ======
    BACKGROUND_MUSIC_VOLUME = 0.5   # 背景音樂音量 (0.0 到 1.0)
    CLICK_SOUND_VOLUME = 0.7        # 點擊音效音量 (0.0 到 1.0)
    COUNTDOWN_SOUND_VOLUME = 0.7    # 倒數音效音量 (0.0 到 1.0)
    SLOWMO_SOUND_VOLUME = 1.0       # Slowmo 技能音量 (0.0 到 1.0)

    # ====== ⏳ 技能相關設定 ======
    SLOWMO_DURATION_MS = 1200       # Slowmo 技能持續時間（毫秒）
    SLOWMO_COOLDOWN_MS = 5000       # Slowmo 技能冷卻時間（毫秒）

    # ====== 🌟 其他參數設定 ======
    FREEZE_DURATION_MS = 500        # 死球畫面凍結時間 (毫秒)
    COUNTDOWN_SECONDS = 1           # 倒數秒數
