# src/ui/notification.py
import pygame
from enum import Enum
from dataclasses import dataclass, field
from typing import Optional

class NotificationType(Enum):
    INFO = (100, 150, 255)
    SUCCESS = (100, 200, 100)
    WARNING = (255, 200, 100)
    ERROR = (255, 100, 100)
    ACHIEVEMENT = (255, 215, 0)
    BATTLE = (255, 150, 100)

@dataclass
class Notification:
    message: str
    type: NotificationType
    duration: float = 3.0
    data: Optional[dict] = None

    # Pokémon object
    pokemon = None  # Referência ao objeto Pokémon
    pokemon_id: Optional[int] = None
    pokemon_name: Optional[str] = None
    is_shiny: bool = False
    portrait: Optional[pygame.Surface] = None

    _created_at: float = field(default_factory=lambda: pygame.time.get_ticks() / 1000.0)
    _life: float = 0.0
    _fade_out: bool = False
    _fade_alpha: int = 255

    def __post_init__(self):
        self._life = self.duration

    def update(self, current_time: float) -> bool:
        elapsed = current_time - self._created_at

        if elapsed >= self.duration:
            return False

        self._life = self.duration - elapsed

        if elapsed > self.duration - 0.5:
            fade_progress = (elapsed - (self.duration - 0.5)) / 0.5
            self._fade_alpha = int(255 * (1 - fade_progress))
            self._fade_out = True
        else:
            self._fade_alpha = 255
            self._fade_out = False

        return True

    @property
    def alpha(self) -> int:
        return self._fade_alpha

    @property
    def is_fading(self) -> bool:
        return self._fade_out