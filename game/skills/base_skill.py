# pong-soul/game/skills/base_skill.py
from abc import ABC, abstractmethod

class Skill(ABC):
    def __init__(self, env, owner_player_state): # ⭐️ 修改參數
        self.env = env # 環境的引用仍然有用，用於訪問球體、全局狀態等
        self.owner = owner_player_state # ⭐️ 技能的擁有者 (PlayerState 實例)
        print(f"[SKILL_DEBUG][BaseSkill] Skill '{self.__class__.__name__}' initialized for owner '{self.owner.identifier}'.")

    @property
    def overrides_ball_physics(self):
        return False

    @abstractmethod
    def activate(self):
        pass

    @abstractmethod
    def update(self):
        pass

    @abstractmethod
    def deactivate(self, *args, **kwargs): # ⭐️ 修改這裡
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
        pass

    @abstractmethod
    def get_visual_params(self):
        """
        返回一個包含此技能當前視覺效果所需參數的字典。
        如果技能沒有額外的視覺效果，則返回空字典。
        這些參數將由 Renderer 用來繪製效果。
        """
        pass

    def has_full_energy_effect(self):
        return self.get_energy_ratio() >= 1.0