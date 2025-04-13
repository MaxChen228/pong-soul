# game/skills/base_skill.py
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
