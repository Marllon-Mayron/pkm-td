# src/battle/effects/specific/weather/weather_state.py

from enum import Enum


class WeatherType(Enum):
    """Tipos de clima"""
    NONE = "none"
    SANDSTORM = "sandstorm"
    RAIN = "rain"
    SUNNY = "sunny"
    HAIL = "hail"

# ===== METADADOS DE UI (fonte única) =====
WEATHER_DISPLAY_NAMES = {
    WeatherType.NONE: "Nenhum",
    WeatherType.SANDSTORM: "Tempestade de Areia",
    WeatherType.RAIN: "Chuva",
    WeatherType.SUNNY: "Sol Forte",
    WeatherType.HAIL: "Granizo",
}

WEATHER_FILTER_COLORS = {
    WeatherType.SANDSTORM: (194, 178, 128, 110),
    WeatherType.RAIN: (100, 100, 200, 110),
    WeatherType.SUNNY: (255, 200, 100, 110),
    WeatherType.HAIL: (180, 220, 255, 130),
}


def get_weather_ui_options():
    """Lista de (value_str, label_pt) para dropdowns."""
    return [
        (wt.value, WEATHER_DISPLAY_NAMES.get(wt, wt.value.title()))
        for wt in WeatherType
    ]


def weather_from_string(s: str) -> WeatherType:
    """Converte 'hail' → WeatherType.HAIL, com fallback para NONE."""
    try:
        return WeatherType(s.lower())
    except ValueError:
        return WeatherType.NONE


class WeatherState:
    """
    Estado do clima na batalha.
    """

    def __init__(self, weather_type: WeatherType, duration: float = 10.0, source=None, is_base_weather: bool = False):
        print(f"[WeatherState] __init__: weather_type={weather_type}, type(weather_type)={type(weather_type)}")

        # Garantir que é um WeatherType
        if isinstance(weather_type, str):
            self.type = weather_from_string(weather_type)
        else:
            self.type = weather_type

        self.duration = duration
        self.max_duration = duration
        self.source = source
        self.active = True
        self.is_base_weather = is_base_weather  # True = clima permanente da fase

        print(f"[WeatherState] Finalizado: type={self.type}, value={self.type.value}, "
              f"active={self.active}, is_base_weather={self.is_base_weather}")

    def is_immune_to_damage(self, pokemon) -> bool:
        """Verifica se um Pokémon é imune ao dano deste clima"""
        if self.type == WeatherType.SANDSTORM:
            # Rock, Ground, Steel são imunes
            immune_types = ['rock', 'ground', 'steel']
            return any(t.lower() in immune_types for t in pokemon.types)
        if self.type == WeatherType.HAIL:
            return any(t.lower() == "ice" for t in pokemon.types)

        return True  # Outros climas não causam dano

    def update(self, dt: float) -> bool:
        """
        Atualiza o clima.

        Retorna False se o clima expirou.
        Clima base (is_base_weather=True) NUNCA expira.
        """
        if not self.active:
            return False

        # ===== CLIMA BASE NUNCA EXPIRE =====
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