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
        "duration_ms": 8000, # 可略增，因休息會佔用時間
        "cooldown_ms": 1000,
        "bar_color": (150, 50, 200),
        "bug_image_path": "assets/soul_eater_bug.png",
        "bug_display_scale_factor": 2,

        "sound_activate": "assets/bug_activate.mp3",
        "sound_crawl": "assets/bug_crawl.mp3", # 休息時可以考慮暫停此音效
        "sound_hit_paddle": "assets/bug_hit_paddle.mp3",
        "sound_score": "assets/bug_score.mp3",

        # --- Movement Parameters ---
        "base_y_speed": 0.025,
        "y_random_magnitude": 0.008,
        "x_random_walk_speed": 0.025, # 非休息狀態下的X隨機探索
        "target_update_interval_frames": 10, # 非休息狀態下，重新評估目標的頻率
        "goal_seeking_factor": 0.12,
        "dodge_factor": 0.12,

        # --- 策略性休息/猶豫行為參數 ---
        "can_rest": True,
        "rest_chance_after_target_update": 0.6, # 更新目標後，有多大概率進入休息 (可略增)
                                                 # 或者可以設定一個固定的 "移動->休息" 循環計時器
        "min_rest_duration_seconds": 0.1,        # 最小休息持續秒數
        "max_rest_duration_seconds": 0.2,        # 最大休息持續秒數
        "y_movement_dampening_during_rest": 0.0, # 休息時Y軸移動的抑制因子 (接近0表示幾乎不動)
        "x_movement_dampening_during_rest": 0.0,  # 休息時X軸主要意圖移動的抑制因子 (0表示完全停止意圖移動)
                                                 # 即使X軸意圖停止，可能仍保留極小的隨機漂移
        "small_drift_during_rest_factor": 0.007, # 休息時的微小漂移因子 (X和Y)
    }
}