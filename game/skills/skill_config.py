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
    "soul_eater_bug": {
        "duration_ms": 5000,
        "cooldown_ms": 10000,
        # "bug_speed": 0.015, # We'll replace this with base_y_speed
        "bar_color": (150, 50, 200),
        "bug_image_path": "assets/soul_eater_bug.png",
        "activation_sound_path": "assets/bug_activate.mp3",
        "crawl_sound_path": "assets/bug_crawl.mp3",
        "hit_sound_path": "assets/bug_hit_paddle.mp3",
        "score_sound_path": "assets/bug_score.mp3",

        # --- New Movement Parameters ---
        "base_y_speed": 0.025,         # Base speed towards opponent (units per frame, before time_scale)
        "x_amplitude": 0.2,           # Max horizontal deviation for sine wave (0.0 to 0.5 of screen width)
        "x_frequency": 0.7,           # How many sine wave cycles over a certain time/distance
        "x_homing_factor": 0.03,      # How strongly it steers towards opponent paddle's X (0 to 1, responsiveness)
        "initial_phase_offset_range": [0, 6.28318], # Random initial phase for sine wave [min_rad, max_rad (0 to 2*PI)]
        "time_scaling_for_wave": 0.05 # Adjusts how quickly the sine wave evolves over time
    }
}
