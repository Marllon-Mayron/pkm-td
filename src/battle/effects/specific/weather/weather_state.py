# src/battle/effects/specific/weather/weather_state.py

from enum import Enum


class WeatherType(Enum):
    """Tipos de clima"""
    NONE = "none"
    RAIN = "rain"
    SUNNY = "sunny"
    SNOW = "snow"
    HAIL = "hail"                 # map-only
    SANDSTORM = "sandstorm"       # map-only
    THUNDERSTORM = "thunderstorm" # map-only


# =====================================================================
# CATEGORIAS
# =====================================================================
# NATURAL = moves podem ativar (Sunny Day, Rain Dance, etc)
# MAP_ONLY = só via config de fase / debug. Moves NÃO conseguem ativar.
NATURAL_WEATHERS = {WeatherType.NONE, WeatherType.RAIN,
                    WeatherType.SUNNY, WeatherType.SNOW}

MAP_ONLY_WEATHERS = {WeatherType.HAIL, WeatherType.SANDSTORM,
                     WeatherType.THUNDERSTORM}


def is_natural_weather(wt: WeatherType) -> bool:
    return wt in NATURAL_WEATHERS


# =====================================================================
# UI
# =====================================================================
WEATHER_DISPLAY_NAMES = {
    WeatherType.NONE: "Nenhum",
    WeatherType.RAIN: "Chuva",
    WeatherType.SUNNY: "Sol Forte",
    WeatherType.SNOW: "Neve",
    WeatherType.HAIL: "Granizo",
    WeatherType.SANDSTORM: "Tempestade de Areia",
    WeatherType.THUNDERSTORM: "Tempestade",
}

WEATHER_FILTER_COLORS = {
    WeatherType.RAIN: (100, 100, 200, 110),
    WeatherType.SUNNY: (255, 200, 100, 110),
    WeatherType.SNOW: (200, 220, 255, 90),
    WeatherType.HAIL: (180, 220, 255, 130),
    WeatherType.SANDSTORM: (194, 178, 128, 110),
    WeatherType.THUNDERSTORM: (40, 40, 90, 140),
}


def get_weather_ui_options(only_natural: bool = False):
    """Lista (value, label).

    only_natural=True  → só rain/sunny/snow (+ NONE)
    only_natural=False → todos (debug)
    """
    opts = []
    for wt in WeatherType:
        if only_natural and wt not in NATURAL_WEATHERS:
            continue
        opts.append((wt.value, WEATHER_DISPLAY_NAMES.get(wt, wt.value.title())))
    return opts


def weather_from_string(s: str) -> WeatherType:
    try:
        return WeatherType(s.lower())
    except ValueError:
        return WeatherType.NONE


# =====================================================================
# STATE
# =====================================================================
class WeatherState:
    def __init__(self, weather_type: WeatherType, duration: float = 10.0,
                 source=None, is_base_weather: bool = False):
        if isinstance(weather_type, str):
            self.type = weather_from_string(weather_type)
        else:
            self.type = weather_type

        self.duration = duration
        self.max_duration = duration
        self.source = source
        self.active = True
        self.is_base_weather = is_base_weather

    # ================================================================
    # IMUNIDADE A DANO DE CLIMA
    # ================================================================
    def is_immune_to_damage(self, pokemon) -> bool:
        if self.type == WeatherType.SANDSTORM:
            immune_types = ['rock', 'ground', 'steel']
            return any(t.lower() in immune_types for t in pokemon.types)
        if self.type == WeatherType.HAIL:
            return any(t.lower() == "ice" for t in pokemon.types)
        return True

    # ================================================================
    # MULTIPLICADOR DE DANO POR TIPO DE MOVE
    # ================================================================
    def get_damage_multiplier(self, move_type: str) -> float:
        """Retorna o multiplicador de dano pra um tipo de move neste clima.

        Exemplo:
            weather = THUNDERSTORM
            weather.get_damage_multiplier("water")  → 1.20 (+20%)
            weather.get_damage_multiplier("fire")   → 1.00
        """
        if not self.active:
            return 1.0

        mt = str(move_type).lower()
        t = self.type

        # ===== SOL =====
        if t == WeatherType.SUNNY:
            if mt == "fire":
                return 1.5    # +50%
            if mt == "water":
                return 0.5    # -50%

        # ===== CHUVA =====
        elif t == WeatherType.RAIN:
            if mt == "water":
                return 1.5
            if mt == "fire":
                return 0.5

        # ===== TEMPESTADE (map-only) =====
        elif t == WeatherType.THUNDERSTORM:
            # +20% em Water (pedido) e +20% em Electric (faz sentido temático)
            if mt == "water":
                return 1.2
            if mt == "electric":
                return 1.2

        # ===== NEVE / GRANIZO =====
        # Real: Snow não altera dano de Ice, só Defesa (não implementado aqui).
        elif t == WeatherType.SNOW:
            if mt == "fire":
                return 0.7    # fogo perde força no frio
        elif t == WeatherType.HAIL:
            if mt == "fire":
                return 0.7

        # SANDSTORM: neutro pra tipos (o dano vem por turno)
        return 1.0

    # ================================================================
    # CICLO
    # ================================================================
    def update(self, dt: float) -> bool:
        if not self.active:
            return False
        if self.is_base_weather:
            return True
        self.duration -= dt
        if self.duration <= 0:
            self.active = False
            return False
        return True

    def get_progress(self) -> float:
        if self.max_duration <= 0:
            return 1.0
        return 1.0 - (self.duration / self.max_duration)

    def get_display_name(self) -> str:
        return WEATHER_DISPLAY_NAMES.get(self.type, "")

    def get_filter_color(self) -> tuple:
        return WEATHER_FILTER_COLORS.get(self.type, (255, 0, 0, 110))