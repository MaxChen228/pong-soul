# base_skill.py
from abc import ABC, abstractmethod

class Skill(ABC):
    def __init__(self, env):
        self.env = env

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

    @abstractmethod
    def render(self, surface):
        """
        每個技能自行繪圖，與render.py對接。
        例如shockwave、板子殘影、技能專屬動畫…都寫在這裡。
        surface 是 pygame.display.set_mode(...) 取得的視窗。
        """
        pass

    def has_full_energy_effect(self):
        """
        預設判斷能量是否滿，如技能條追跡線特效可用
        """
        return self.get_energy_ratio() >= 1.0
