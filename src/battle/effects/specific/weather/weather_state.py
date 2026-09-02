# src/battle/effects/specific/weather/weather_state.py

from enum import Enum


class WeatherType(Enum):
    """Tipos de clima"""
    NONE = "none"
    SANDSTORM = "sandstorm"
    RAIN = "rain"
    SUNNY = "sunny"


class WeatherState:
    """
    Estado do clima na batalha.
    """

    def __init__(self, weather_type: WeatherType, duration: float = 10.0, source=None, is_base_weather: bool = False):
        print(f"[WeatherState] __init__: weather_type={weather_type}, type(weather_type)={type(weather_type)}")

        # Garantir que é um WeatherType
        if isinstance(weather_type, str):
            # Se veio como string, converte
            if weather_type.lower() == "sandstorm":
                self.type = WeatherType.SANDSTORM
            elif weather_type.lower() == "rain":
                self.type = WeatherType.RAIN
            elif weather_type.lower() == "sunny":
                self.type = WeatherType.SUNNY
            else:
                self.type = WeatherType.NONE
            print(f"[WeatherState] Convertido de string para {self.type}")
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
        if self.type == WeatherType.SANDSTORM:
            return "Tempestade de Areia"
        elif self.type == WeatherType.RAIN:
            return "Chuva"
        elif self.type == WeatherType.SUNNY:
            return "Sol Forte"
        return ""

    def get_filter_color(self) -> tuple:
        """Retorna a cor do filtro com opacidade"""
        if self.type.value == "sandstorm":
            return (194, 178, 128, 110)
        elif self.type.value == "rain":
            return (100, 100, 200, 110)
        elif self.type.value == "sunny":
            return (255, 200, 100, 110)
        else:
            print(f"[WeatherState] WARNING: tipo não reconhecido! {self.type}")
            return (255, 0, 0, 110)