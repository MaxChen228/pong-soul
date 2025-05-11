# pong-soul/game/skills/base_skill.py
from abc import ABC, abstractmethod

class Skill(ABC):
    def __init__(self, env):
        self.env = env

    @property
    def overrides_ball_physics(self):
        """
        指示此技能是否會完全覆寫環境中的預設球體物理邏輯。
        預設為 False，表示技能不覆寫，環境應繼續處理球的移動。
        """
        return False

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