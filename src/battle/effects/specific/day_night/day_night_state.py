# src/battle/effects/specific/day_night/day_night_state.py

from enum import Enum
import random


class DayNightType(Enum):
    DAY = "day"
    NIGHT = "night"
    DUSK = "dusk"
    DAWN = "dawn"
    CAVE = "cave"
    DEEP = "deep"


DAY_NIGHT_DISPLAY_NAMES = {
    DayNightType.DAY: "Dia",
    DayNightType.NIGHT: "Noite",
    DayNightType.DUSK: "Entardecer",
    DayNightType.DAWN: "Amanhecer",
    DayNightType.CAVE: "Caverna",
    DayNightType.DEEP: "Fundo do Mar",
}

# ===== CICLO NATURAL DOS PERÍODOS =====
# Ordem: Amanhecer → Dia → Entardecer → Noite → (volta pra Amanhecer)
# CAVE e DEEP ficam FORA do ciclo (são permanentes).
CYCLE_ORDER = [
    DayNightType.DAWN,
    DayNightType.DAY,
    DayNightType.DUSK,
    DayNightType.NIGHT,
]

# Duração PADRÃO de cada período (segundos).
# TODOS os períodos têm exatamente a MESMA duração → ciclo de 4 × 60s = 4 min.
DEFAULT_PERIOD_DURATION = 60.0

# Duração da transição suave entre períodos (segundos)
TRANSITION_DURATION = 3.0


def get_next_cycle_period(current: DayNightType) -> DayNightType:
    """Retorna o próximo período no ciclo natural (CAVE/DEEP ficam parados)."""
    if current in (DayNightType.CAVE, DayNightType.DEEP):
        return current
    try:
        idx = CYCLE_ORDER.index(current)
    except ValueError:
        return DayNightType.DAY
    return CYCLE_ORDER[(idx + 1) % len(CYCLE_ORDER)]


def get_day_night_ui_options():
    return [
        (dt.value, DAY_NIGHT_DISPLAY_NAMES.get(dt, dt.value.title()))
        for dt in DayNightType
    ]


def day_night_from_string(s: str) -> DayNightType:
    try:
        return DayNightType(s.lower())
    except ValueError:
        return DayNightType.DAY


# ===== CORES "CHEIAS" PARA UI (relógio do debug) =====
PERIOD_DISPLAY_COLORS = {
    DayNightType.DAWN:  (255, 175, 200),   # rosa/peach — amanhecer
    DayNightType.DAY:   (255, 215,  70),   # amarelo-ouro — dia
    DayNightType.DUSK:  (255, 120,  40),   # laranja profundo — entardecer
    DayNightType.NIGHT: ( 95,  60, 155),   # roxo — noite
    DayNightType.CAVE:  ( 70,  70,  70),
    DayNightType.DEEP:  ( 30, 100, 160),
}


class DayNightState:
    """
    Estado do período do dia/ambiente.

    Ciclo normal (CAVE/DEEP não fazem parte):
        DAWN → DAY → DUSK → NIGHT → DAWN → …

    Ao trocar de período, guardamos `previous_type` e interpolamos
    a cor do filtro suavemente durante `TRANSITION_DURATION` segundos.
    """

    def __init__(self,
                 period_type: DayNightType = None,
                 duration: float = DEFAULT_PERIOD_DURATION,
                 previous_type: DayNightType = None):
        if period_type is None:
            period_type = random.choice(CYCLE_ORDER)

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

        # ===== TRANSIÇÃO SUAVE =====
        self.previous_type = previous_type
        self.transition_elapsed = (
            TRANSITION_DURATION if previous_type is None else 0.0
        )

        # ===== FLASH =====
        self.flash_state = "inactive"   # "inactive", "active", "fading"
        self.flash_timer = 0.0
        self.flash_duration = 15.0
        self.flash_fade_duration = 5.0
        self.flash_fade_progress = 0.0

    # ------------------------------------------------------------------
    def update(self, dt: float) -> bool:
        if not self.active:
            return False

        # Progresso da transição suave
        if self.transition_elapsed < TRANSITION_DURATION:
            self.transition_elapsed = min(
                TRANSITION_DURATION, self.transition_elapsed + dt
            )

        # Flash
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

        # CAVE / DEEP são permanentes
        if self.type in (DayNightType.CAVE, DayNightType.DEEP):
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

    # ------------------------------------------------------------------
    def get_progress(self) -> float:
        """Progresso DENTRO do período atual (0..1)."""
        if self.max_duration <= 0:
            return 1.0
        return min(1.0, self.elapsed / self.max_duration)

    def get_transition_factor(self) -> float:
        """0 = período anterior, 1 = período atual."""
        if self.previous_type is None or TRANSITION_DURATION <= 0:
            return 1.0
        return min(1.0, self.transition_elapsed / TRANSITION_DURATION)

    def get_display_name(self) -> str:
        return DAY_NIGHT_DISPLAY_NAMES.get(self.type, "Dia")

    # ------------------------------------------------------------------
    def activate_flash(self):
        if self.type != DayNightType.CAVE:
            return False
        self.flash_state = "active"
        self.flash_timer = 0.0
        self.flash_fade_progress = 0.0
        return True

    def get_flash_intensity(self) -> float:
        if self.type != DayNightType.CAVE:
            return 0.0
        if self.flash_state == "active":
            return 1.0
        if self.flash_state == "fading":
            return 1.0 - self.flash_fade_progress
        return 0.0

    # ------------------------------------------------------------------
    # CORES / LUZ
    # ------------------------------------------------------------------
    def _base_filter_color(self, period_type: DayNightType) -> tuple:
        if period_type == DayNightType.DAY:
            return (0, 0, 0, 0)
        if period_type == DayNightType.NIGHT:
            return (5, 10, 35, 200)
        if period_type == DayNightType.DUSK:
            return (200, 120, 50, 100)
        if period_type == DayNightType.DAWN:
            return (255, 180, 150, 70)
        if period_type == DayNightType.CAVE:
            flash = self.get_flash_intensity()
            if flash > 0:
                alpha = max(0, int(220 * (1.0 - flash)))
                return (0, 0, 0, alpha)
            return (0, 0, 0, 220)
        if period_type == DayNightType.DEEP:
            return (0, 30, 60, 200)
        return (0, 0, 0, 0)

    def get_filter_color(self) -> tuple:
        """Cor final, já com blend suave aplicado."""
        current = self._base_filter_color(self.type)

        if self.previous_type is None or self.previous_type == self.type:
            return current

        prev = self._base_filter_color(self.previous_type)
        t = self.get_transition_factor()

        return tuple(
            int(prev[i] + (current[i] - prev[i]) * t)
            for i in range(4)
        )

    def _base_ambient_light(self, period_type: DayNightType) -> float:
        if period_type == DayNightType.DAY:
            return 1.0
        if period_type == DayNightType.NIGHT:
            return 0.15
        if period_type == DayNightType.DUSK:
            return 0.5
        if period_type == DayNightType.DAWN:
            return 0.6
        if period_type == DayNightType.CAVE:
            flash = self.get_flash_intensity()
            if flash > 0:
                return 0.1 + (0.9 - 0.1) * flash
            return 0.1
        if period_type == DayNightType.DEEP:
            return 0.2
        return 1.0

    def get_ambient_light(self) -> float:
        curr = self._base_ambient_light(self.type)
        if self.previous_type is None or self.previous_type == self.type:
            return curr
        prev = self._base_ambient_light(self.previous_type)
        t = self.get_transition_factor()
        return prev + (curr - prev) * t

    # ------------------------------------------------------------------
    # PREDICADOS
    # ------------------------------------------------------------------
    def is_night(self) -> bool:
        return self.type in (DayNightType.NIGHT, DayNightType.CAVE, DayNightType.DEEP)

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
        return self.type not in (DayNightType.CAVE, DayNightType.DEEP)