# src/battle/effects/specific/day_night/day_night_state.py

from enum import Enum
import random


class DayNightType(Enum):
    """Tipos de período do dia"""
    DAY = "day"
    NIGHT = "night"
    DUSK = "dusk"  # Opcional: pôr do sol
    DAWN = "dawn"  # Opcional: amanhecer


class DayNightState:
    """
    Estado do período do dia na batalha/fase.
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
            DayNightType.DUSK: "Crepúsculo",
            DayNightType.DAWN: "Amanhecer"
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
            # ===== NOITE: Filtro mais escuro com tom azulado profundo =====
            # Aumentei a opacidade e deixei mais azul/escuro
            return (5, 10, 35, 200)  # Azul escuro profundo com alta opacidade
        elif self.type == DayNightType.DUSK:
            # Crepúsculo: tons alaranjados
            return (200, 120, 50, 80)
        elif self.type == DayNightType.DAWN:
            # Amanhecer: tons rosados
            return (255, 180, 150, 60)

        return (0, 0, 0, 0)

    def get_ambient_light(self) -> float:
        """
        Retorna o fator de luz ambiente (0.0 a 1.0).
        1.0 = dia, 0.0 = noite escura.
        """
        if self.type == DayNightType.DAY:
            return 1.0
        elif self.type == DayNightType.NIGHT:
            return 0.15  # Mais escuro (antes era 0.2)
        elif self.type == DayNightType.DUSK:
            return 0.5
        elif self.type == DayNightType.DAWN:
            return 0.6
        return 1.0

    def is_night(self) -> bool:
        """Verifica se é noite"""
        return self.type == DayNightType.NIGHT

    def is_day(self) -> bool:
        """Verifica se é dia"""
        return self.type == DayNightType.DAY