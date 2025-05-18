# game/skills/skill_config.py
"""
從 YAML 檔案動態載入技能參數。
"""
from game.config_manager import ConfigManager # ⭐️ 導入 ConfigManager

# 創建一個 ConfigManager 實例來載入設定
# 注意：這假設 ConfigManager 的初始化不需要 Pygame 初始化等複雜依賴，
# 或者假設此模組會在 ConfigManager 正常運作後被引用。
# 另一種方法是讓主程式初始化 ConfigManager 並將其傳遞給技能系統。
# 但為了簡化，這裡我們在模組級別創建一個臨時實例來載入。
# 如果您的 ConfigManager 實例在遊戲啟動時已經創建並全局可用（例如通過 GameApp），
# 則應使用該全局實例。
#
# 根據您目前的結構，ConfigManager 在 main.py 中創建。
# game.skills.skill_config.py 通常在技能類別導入時（即遊戲早期）就會被執行。
# 為了確保一致性，我們在這裡創建一個新的 ConfigManager 實例來專門加載技能配置。
# 這可以避免依賴於 main.py 中 ConfigManager 的創建順序。

_config_loader = ConfigManager()
SKILL_CONFIGS = _config_loader.get_all_skill_configs()

# 檢查是否成功載入，如果沒有，則 SKILL_CONFIGS 會是空字典
if not SKILL_CONFIGS:
    print("[skill_config.py] WARNING: SKILL_CONFIGS is empty. Failed to load from YAML or YAML was empty.")
    print("    Skills might use their internal default parameters.")
    # 您可以在這裡選擇是否提供一個最小的硬編碼備用 SKILL_CONFIGS，
    # 但由於各技能類別內部已有備用邏輯，這裡僅打印警告。
    # SKILL_CONFIGS = {
    #     "slowmo": { "duration_ms": 1000, "cooldown_ms": 1000, "slow_time_scale": 0.1 }, # 最小備用示例
    # }
else:
    print("[skill_config.py] SKILL_CONFIGS loaded successfully from YAML.")

# 為了調試，您可以取消註解以下行來打印載入的設定：
# import pprint
# print("[skill_config.py] Loaded SKILL_CONFIGS:")
# pprint.pprint(SKILL_CONFIGS)