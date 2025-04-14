from abc import ABC, abstractmethod

class Skill(ABC):
    def __init__(self, env):
        self.env = env
        self.effect_active = False  # 新增：技能特效是否啟用

    @abstractmethod
    def activate(self):
        pass

    @abstractmethod
    def update(self):
        pass

    @abstractmethod
    def deactivate(self):
        pass

    @abstractmethod
    def is_active(self):
        pass

    @abstractmethod
    def get_cooldown_seconds(self):
        pass

    @abstractmethod
    def get_energy_ratio(self):
        pass

    # ⭐️ 明確新增技能條特效共通判斷方法
    def has_full_energy_effect(self):
        return self.get_energy_ratio() >= 1.0
