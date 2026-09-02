# src/scenes/game_scene/components/day_night_weather_system.py

import random
from src.battle.effects.specific.day_night.day_night_state import DayNightType, DayNightState
from src.battle.effects.specific.weather.weather_state import WeatherType


class DayNightWeatherSystem:
    """
    Sistema que gerencia o dia/noite e clima da fase.

    Suporta configurações do editor:
    - day_night_mode: "random", "day", "night"
    - base_weather: "random", "none", "sunny", "rain"
    """

    def __init__(self, game_scene):
        self.game_scene = game_scene
        self.day_night_state = None
        self._initialized = False

        # ===== CLIMAS DISPONÍVEIS PARA O MAPA =====
        self.MAP_WEATHER_TYPES = [
            None, None, None, None, None, None, None, None, None,  # 90%
            WeatherType.SUNNY,  # 5%
            WeatherType.RAIN,  # 5%
        ]

    def initialize(self):
        """Inicializa o sistema com valores baseados nas configurações da fase"""
        if self._initialized:
            return

        # ===== OBTÉM CONFIGURAÇÕES DO EDITOR =====
        day_night_mode = "random"
        base_weather = "random"

        if hasattr(self.game_scene, 'day_night_mode'):
            day_night_mode = self.game_scene.day_night_mode
        if hasattr(self.game_scene, 'base_weather'):
            base_weather = self.game_scene.base_weather

        print(f"[DAY/NIGHT] Configuração do editor: Dia/Noite={day_night_mode}, Clima={base_weather}")

        # ===== DIA/NOITE =====
        # Mapeia os modos para os tipos DayNightType
        mode_map = {
            "day": DayNightType.DAY,
            "night": DayNightType.NIGHT,
            "dusk": DayNightType.DUSK,
            "dawn": DayNightType.DAWN,
            "cave": DayNightType.CAVE,
            "deep": DayNightType.DEEP,
        }

        if day_night_mode in mode_map:
            period_type = mode_map[day_night_mode]
            print(f"[DAY/NIGHT] Forçando {period_type.value.upper()} (configuração do editor)")
        else:  # "random"
            period_type = random.choices(
                [DayNightType.DAY, DayNightType.NIGHT, DayNightType.DUSK, DayNightType.DAWN],
                weights=[0.65, 0.25, 0.050, 0.050]  # 60% dia, 25% noite, 5% cada transição
            )[0]
            print(f"[DAY/NIGHT] Período aleatório: {period_type.value}")

        duration = random.uniform(30.0, 90.0)
        self.day_night_state = DayNightState(period_type, duration)

        # ===== CLIMA BASE DA FASE =====
        weather_type = self._get_weather_from_config(base_weather)

        if weather_type:
            weather_names = {
                WeatherType.SUNNY: "Sol Forte",
                WeatherType.RAIN: "Chuva",
            }
            print(
                f"[WEATHER_BASE] Clima BASE da fase: {weather_names.get(weather_type, weather_type.value)} (PERMANENTE)")

            if hasattr(self.game_scene, 'battle_system'):
                self.game_scene.battle_system.weather_manager.set_base_weather(weather_type)
        else:
            print(f"[WEATHER_BASE] Clima BASE da fase: Normal (PERMANENTE)")

        self._initialized = True

    def _get_weather_from_config(self, base_weather):
        """Retorna o WeatherType baseado na configuração do editor."""
        if base_weather == "sunny":
            if self.day_night_state and self.day_night_state.is_night():
                print(f"[WEATHER_BASE] Sunny Day bloqueado (é noite/caverna/profundo) - usando Normal")
                return None
            return WeatherType.SUNNY
        elif base_weather == "rain":
            return WeatherType.RAIN
        elif base_weather == "none":
            return None
        else:  # "random"
            is_night = self.day_night_state and self.day_night_state.is_night()

            for _ in range(10):
                weather_type = random.choice(self.MAP_WEATHER_TYPES)
                if weather_type == WeatherType.SUNNY and is_night:
                    continue
                return weather_type

            return None

    def _get_weather_from_config(self, base_weather):
        """
        Retorna o WeatherType baseado na configuração do editor.
        """
        if base_weather == "sunny":
            # Verifica se é noite (Sunny Day não funciona à noite)
            if self.day_night_state and self.day_night_state.is_night():
                print(f"[WEATHER_BASE] Sunny Day bloqueado (é noite) - usando Normal")
                return None
            return WeatherType.SUNNY
        elif base_weather == "rain":
            return WeatherType.RAIN
        elif base_weather == "none":
            return None
        else:  # "random"
            # Escolhe aleatoriamente, mas respeitando a regra de Sunny Day à noite
            is_night = self.day_night_state and self.day_night_state.is_night()

            # Tenta até 10 vezes
            for _ in range(10):
                weather_type = random.choice(self.MAP_WEATHER_TYPES)
                if weather_type == WeatherType.SUNNY and is_night:
                    continue
                return weather_type

            return None

    def update(self, dt: float):
        """Atualiza o sistema de dia/noite"""
        if not self._initialized:
            self.initialize()
            return

        if self.day_night_state:
            self.day_night_state.update(dt)
            if not self.day_night_state.active:
                self._change_period()

    def _change_period(self):
        """Alterna entre dia e noite (respeitando a configuração do editor)"""
        if not self.day_night_state:
            return

        # Verifica se a fase é fixa (day ou night)
        day_night_mode = getattr(self.game_scene, 'day_night_mode', 'random')

        if day_night_mode == "day":
            period_type = DayNightType.DAY
        elif day_night_mode == "night":
            period_type = DayNightType.NIGHT
        else:  # "random"
            period_type = random.choices(
                [DayNightType.DAY, DayNightType.NIGHT],
                weights=[0.8, 0.2]
            )[0]

        duration = random.uniform(30.0, 90.0)
        self.day_night_state = DayNightState(period_type, duration)

        print(f"[DAY/NIGHT] Mudou para: {self.day_night_state.get_display_name()} por {duration:.1f}s")

        # ===== QUANDO MUDA PARA NOITE, VERIFICA SE O CLIMA É SUNNY =====
        if period_type == DayNightType.NIGHT:
            self._validate_weather_on_night()

    def _validate_weather_on_night(self):
        """Quando a noite começa, verifica se o clima atual é Sunny Day."""
        if not hasattr(self.game_scene, 'battle_system'):
            return

        weather_mgr = self.game_scene.battle_system.weather_manager
        current_weather = weather_mgr.current_weather

        if current_weather and current_weather.type == WeatherType.SUNNY:
            if current_weather.is_base_weather:
                print(f"[WEATHER_BASE] Sunny Day removido porque a NOITE chegou!")
                weather_mgr.base_weather = None
                weather_mgr.current_weather = None
                if weather_mgr.battle_system and weather_mgr.battle_system.effect_manager:
                    weather_mgr.battle_system.effect_manager.add_status_text(
                        None,
                        "O sol se pôs! O clima voltou ao normal.",
                        duration=2.0
                    )

    def get_day_night_type(self) -> DayNightType:
        if self.day_night_state:
            return self.day_night_state.type
        return DayNightType.DAY

    def is_night(self) -> bool:
        return self.day_night_state and self.day_night_state.is_night()

    def is_day(self) -> bool:
        return self.day_night_state and self.day_night_state.is_day()

    def get_ambient_light(self) -> float:
        if self.day_night_state:
            return self.day_night_state.get_ambient_light()
        return 1.0