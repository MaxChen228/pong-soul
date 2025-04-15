# skill_config.py
"""
用來集中管理各種技能的參數。
你可依照需求，將與技能相關的持續時間、冷卻、顏色等全部放這裡。
"""
SKILL_CONFIGS = {
    "slowmo": {
        # 時間相關
        "duration_ms": 3000,
        "cooldown_ms": 5000,
        # 顏色/特效
        "paddle_color": (0, 150, 255),  # 板子顏色
        "fog_duration_ms": 2000,        # 技能結束後霧氣淡出時間
        "trail_color": (0, 200, 255),   # slowmo技能板子殘影顏色

        # 新增 bar_color
        "bar_color": (0, 200, 255),     # 用來顯示技能條的顏色 (過去 GameSettings.SLOWMO_BAR_COLOR)

        # 新增：時鐘參數（原本放在 GameSettings）
        "clock_color": (255, 255, 255, 100),
        "clock_radius": 50,
        "clock_line_width": 4,
    },

    "long_paddle": {
        "duration_ms": 3000,
        "cooldown_ms": 5000,
        "paddle_color": (0, 255, 100),  # 板子顏色
        "paddle_multiplier": 2,
        "animation_ms": 300,

        # 新增 bar_color
        "bar_color": (0, 100, 0),       # 過去 GameSettings.LONG_PADDLE_BAR_COLOR
    },
}
