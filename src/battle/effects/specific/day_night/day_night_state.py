# src/battle/effects/specific/day_night/day_night_state.py

from enum import Enum
import random


class DayNightType(Enum):
    """Tipos de período do dia/ambiente"""
    DAY = "day"
    NIGHT = "night"
    DUSK = "dusk"
    DAWN = "dawn"
    CAVE = "cave"
    DEEP = "deep"


class DayNightState:
    """
    Estado do período do dia/ambiente na batalha/fase.
    """

    def __init__(self, period_type: DayNightType = None, duration: float = 60.0):
        if period_type is None:
            period_type = random.choice([DayNightType.DAY, DayNightType.NIGHT])

        if isinstance(period_type, str):
            type_map = {
                "day": DayNightType.DAY,
                "night": DayNightType.NIGHT,
                "dusk": DayNightType.DUSK,
                "dawn": DayNightType.DAWN,
                "cave": DayNightType.CAVE,
                "deep": DayNightType.DEEP,
            }
            self.type = type_map.get(period_type.lower(), DayNightType.DAY)
        else:
            self.type = period_type

        self.duration = duration
        self.max_duration = duration
        self.active = True
        self.elapsed = 0.0
        self.transition_progress = 0.0

        # ===== FLASH EFFECT =====
        self.flash_state = "inactive"  # "inactive", "active", "fading"
        self.flash_timer = 0.0
        self.flash_duration = 15.0
        self.flash_fade_duration = 5.0
        self.flash_fade_progress = 0.0

    def update(self, dt: float) -> bool:
        """Atualiza o estado do período"""
        if not self.active:
            return False

        # ===== ATUALIZA FLASH =====
        if self.flash_state == "active":
            self.flash_timer += dt
            if self.flash_timer >= self.flash_duration:
                self.flash_state = "fading"
                self.flash_fade_progress = 0.0

        if self.flash_state == "fading":
            self.flash_fade_progress += dt / self.flash_fade_duration
            if self.flash_fade_progress >= 1.0:
                self.flash_state = "inactive"
                self.flash_fade_progress = 1.0

        # ===== CAVE E DEEP NUNCA TRANSICIONAM =====
        if self.type in [DayNightType.CAVE, DayNightType.DEEP]:
            self.active = True
            self.duration = 999999.0
            self.max_duration = 999999.0
            return True

        self.elapsed += dt
        self.transition_progress = min(1.0, self.elapsed / self.duration)

        if self.elapsed >= self.duration:
            self.active = False
            return False

        return True

    def get_progress(self) -> float:
        if self.max_duration <= 0:
            return 1.0
        return min(1.0, self.elapsed / self.max_duration)

    def get_display_name(self) -> str:
        names = {
            DayNightType.DAY: "Dia",
            DayNightType.NIGHT: "Noite",
            DayNightType.DUSK: "Entardecer",
            DayNightType.DAWN: "Amanhecer",
            DayNightType.CAVE: "Caverna",
            DayNightType.DEEP: "Fundo do Mar",
        }
        return names.get(self.type, "Dia")

    def activate_flash(self):
        """Ativa o efeito Flash (ilumina a caverna por 15 segundos)"""
        if self.type != DayNightType.CAVE:
            return False

        self.flash_state = "active"
        self.flash_timer = 0.0
        self.flash_fade_progress = 0.0
        return True

    def get_flash_intensity(self) -> float:
        """
        Retorna a intensidade atual do flash (0 = escuro, 1 = totalmente iluminado)
        """
        if self.type != DayNightType.CAVE:
            return 0.0

        if self.flash_state == "active":
            return 1.0
        elif self.flash_state == "fading":
            return 1.0 - self.flash_fade_progress
        else:
            return 0.0

    def get_filter_color(self) -> tuple:
        if self.type == DayNightType.DAY:
            return (0, 0, 0, 0)
        elif self.type == DayNightType.NIGHT:
            return (5, 10, 35, 200)
        elif self.type == DayNightType.DUSK:
            return (200, 120, 50, 100)
        elif self.type == DayNightType.DAWN:
            return (255, 180, 150, 70)
        elif self.type == DayNightType.CAVE:
            flash_intensity = self.get_flash_intensity()
            if flash_intensity > 0:
                base_alpha = 220
                current_alpha = int(base_alpha * (1.0 - flash_intensity))
                current_alpha = max(0, current_alpha)
                return (0, 0, 0, current_alpha)
            return (0, 0, 0, 220)
        elif self.type == DayNightType.DEEP:
            return (0, 30, 60, 200)
        return (0, 0, 0, 0)

    def get_ambient_light(self) -> float:
        if self.type == DayNightType.DAY:
            return 1.0
        elif self.type == DayNightType.NIGHT:
            return 0.15
        elif self.type == DayNightType.DUSK:
            return 0.5
        elif self.type == DayNightType.DAWN:
            return 0.6
        elif self.type == DayNightType.CAVE:
            flash_intensity = self.get_flash_intensity()
            if flash_intensity > 0:
                base_light = 0.1
                max_light = 0.9
                return base_light + (max_light - base_light) * flash_intensity
            return 0.1
        elif self.type == DayNightType.DEEP:
            return 0.2
        return 1.0

    def is_night(self) -> bool:
        return self.type in [DayNightType.NIGHT, DayNightType.CAVE, DayNightType.DEEP]

    def is_day(self) -> bool:
        return self.type == DayNightType.DAY

    def is_cave(self) -> bool:
        return self.type == DayNightType.CAVE

    def is_deep(self) -> bool:
        return self.type == DayNightType.DEEP

    def is_dusk(self) -> bool:
        return self.type == DayNightType.DUSK

    def is_dawn(self) -> bool:
        return self.type == DayNightType.DAWN

    def is_transitional(self) -> bool:
        return self.type not in [DayNightType.CAVE, DayNightType.DEEP]