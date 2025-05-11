# pong-soul/game/skills/skill_config.py
"""
用來集中管理各種技能的參數。
不省略任何功能。
"""
SKILL_CONFIGS = {
    "slowmo": {
        "duration_ms": 3000,
        "cooldown_ms": 5000,
        "paddle_color": (0, 150, 255),
        "fog_duration_ms": 2000,
        "trail_color": (0, 200, 255),
        "bar_color": (0, 200, 255),
        "clock_color": (255, 255, 255, 100),
        "clock_radius": 50,
        "clock_line_width": 4,
        # SlowMo 音效由 SlowMoSkill 內部直接引用 sound_manager 的方法播放，不在此配置路徑
    },
    "long_paddle": {
        "duration_ms": 3000,
        "cooldown_ms": 5000,
        "paddle_color": (0, 255, 100),
        "paddle_multiplier": 2,
        "animation_ms": 300,
        "bar_color": (0, 100, 0),
    },
    "soul_eater_bug": {
        "duration_ms": 6000,      # 蟲形態最大持續時間
        "cooldown_ms": 12000,     # 技能冷卻時間
        "bar_color": (150, 50, 200),
        "bug_image_path": "assets/soul_eater_bug.png", # 確認你有這個圖片
        "bug_display_scale_factor": 2, # 蟲圖片相對於原始球大小的縮放因子 (1.0代表一樣大)

        # --- 新增音效路徑 (請確保 assets 資料夾有這些音效檔) ---
        "sound_activate": "assets/bug_activate.mp3",    # 啟動音效
        "sound_crawl": "assets/bug_crawl.mp3",          # (可選) 爬行時循環音效
        "sound_hit_paddle": "assets/bug_hit_paddle.mp3",# 撞到對方球拍音效
        "sound_score": "assets/bug_score.mp3",          # 成功得分音效 (可共用預設得分音效)

        # --- Movement Parameters ---
        "base_y_speed": 0.022,
        "x_amplitude": 0.18,
        "x_frequency": 0.75,
        "x_homing_factor": 0.035,
        "initial_phase_offset_range": [0, 6.28318],
        "time_scaling_for_wave": 0.05,
    }
}