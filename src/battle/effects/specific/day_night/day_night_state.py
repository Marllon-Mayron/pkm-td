# src/battle/effects/specific/day_night/day_night_state.py

from enum import Enum
import random


class DayNightType(Enum):
    """Tipos de período do dia/ambiente"""
    DAY = "day"
    NIGHT = "night"
    DUSK = "dusk"      # Entardecer
    DAWN = "dawn"      # Amanhecer
    CAVE = "cave"      # Caverna (escuro)
    DEEP = "deep"      # Fundo do mar (azul profundo)


class DayNightState:
    """
    Estado do período do dia/ambiente na batalha/fase.
    """

    def __init__(self, period_type: DayNightType = None, duration: float = 60.0):
        # Se não especificado, escolhe aleatoriamente entre DAY e NIGHT
        if period_type is None:
            period_type = random.choice([DayNightType.DAY, DayNightType.NIGHT])

        self.type = period_type
        self.duration = duration
        self.max_duration = duration
        self.active = True
        self.elapsed = 0.0
        self.transition_progress = 0.0  # 0 = início, 1 = fim

    def update(self, dt: float) -> bool:
        """Atualiza o estado do período"""
        if not self.active:
            return False

        self.elapsed += dt
        self.transition_progress = min(1.0, self.elapsed / self.duration)

        if self.elapsed >= self.duration:
            self.active = False
            return False

        return True

    def get_progress(self) -> float:
        """Retorna o progresso do período (0-1)"""
        if self.max_duration <= 0:
            return 1.0
        return min(1.0, self.elapsed / self.max_duration)

    def get_display_name(self) -> str:
        """Retorna o nome do período"""
        names = {
            DayNightType.DAY: "Dia",
            DayNightType.NIGHT: "Noite",
            DayNightType.DUSK: "Entardecer",
            DayNightType.DAWN: "Amanhecer",
            DayNightType.CAVE: "Caverna",
            DayNightType.DEEP: "Fundo do Mar",
        }
        return names.get(self.type, "Dia")

    def get_filter_color(self) -> tuple:
        """
        Retorna a cor do filtro para o período atual.
        Usa RGBA com opacidade.
        """
        if self.type == DayNightType.DAY:
            # Dia: sem filtro (transparente)
            return (0, 0, 0, 0)
        elif self.type == DayNightType.NIGHT:
            # Noite: filtro escuro com tom azulado profundo
            return (5, 10, 35, 200)
        elif self.type == DayNightType.DUSK:
            # Entardecer: tons alaranjados/quentes
            return (200, 120, 50, 100)
        elif self.type == DayNightType.DAWN:
            # Amanhecer: tons rosados/azuis claros
            return (255, 180, 150, 70)
        elif self.type == DayNightType.CAVE:
            # Caverna: escuro com tom acinzentado/verde
            return (20, 25, 30, 220)
        elif self.type == DayNightType.DEEP:
            # Fundo do Mar: azul profundo com tons verdes
            return (0, 30, 60, 200)

        return (0, 0, 0, 0)

    def get_ambient_light(self) -> float:
        """
        Retorna o fator de luz ambiente (0.0 a 1.0).
        1.0 = dia, 0.0 = noite escura.
        """
        if self.type == DayNightType.DAY:
            return 1.0
        elif self.type == DayNightType.NIGHT:
            return 0.15
        elif self.type == DayNightType.DUSK:
            return 0.5
        elif self.type == DayNightType.DAWN:
            return 0.6
        elif self.type == DayNightType.CAVE:
            return 0.1
        elif self.type == DayNightType.DEEP:
            return 0.2
        return 1.0

    def is_night(self) -> bool:
        """Verifica se é noite (inclui caverna e fundo do mar)"""
        return self.type in [DayNightType.NIGHT, DayNightType.CAVE, DayNightType.DEEP]

    def is_day(self) -> bool:
        """Verifica se é dia"""
        return self.type == DayNightType.DAY

    def is_cave(self) -> bool:
        """Verifica se é caverna"""
        return self.type == DayNightType.CAVE

    def is_deep(self) -> bool:
        """Verifica se é fundo do mar"""
        return self.type == DayNightType.DEEP

    def is_dusk(self) -> bool:
        """Verifica se é entardecer"""
        return self.type == DayNightType.DUSK

    def is_dawn(self) -> bool:
        """Verifica se é amanhecer"""
        return self.type == DayNightType.DAWN