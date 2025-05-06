# skill_config.py
"""
用來集中管理各種技能的參數。
不省略任何功能。
"""
SKILL_CONFIGS = {
    "slowmo": {
        "duration_ms": 3000,
        "cooldown_ms": 5000,
        # 顏色/特效
        "paddle_color": (0, 150, 255),  # slowmo板子顏色
        "fog_duration_ms": 2000,
        "trail_color": (0, 200, 255),
        "bar_color": (0, 200, 255),

        # 時鐘參數（如果還需要）
        "clock_color": (255, 255, 255, 100),
        "clock_radius": 50,
        "clock_line_width": 4,
    },
    "long_paddle": {
        "duration_ms": 3000,
        "cooldown_ms": 5000,
        "paddle_color": (0, 255, 100),
        "paddle_multiplier": 2,
        "animation_ms": 300,
        "bar_color": (0, 100, 0),
    },
}
