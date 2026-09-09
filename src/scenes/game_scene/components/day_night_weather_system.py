# src/scenes/game_scene/components/day_night_weather_system.py

import random
from src.battle.effects.specific.day_night.day_night_state import DayNightType, DayNightState
from src.battle.effects.specific.weather.weather_state import WeatherType


class DayNightWeatherSystem:

    def __init__(self, game_scene):
        self.game_scene = game_scene
        self.day_night_state = None
        self._initialized = False

        self.MAP_WEATHER_TYPES = [
            None, None, None, None, None, None, None, None, None,
            WeatherType.SUNNY,
            WeatherType.RAIN,
        ]

    def initialize(self):
        if self._initialized:
            return

        day_night_mode = "random"
        base_weather = "random"

        if hasattr(self.game_scene, 'day_night_mode'):
            day_night_mode = self.game_scene.day_night_mode
        if hasattr(self.game_scene, 'base_weather'):
            base_weather = self.game_scene.base_weather

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

            if period_type in [DayNightType.CAVE, DayNightType.DEEP]:
                duration = 999999.0
                self.day_night_state = DayNightState(period_type, duration)
                self.day_night_state.active = True
                self._initialized = True

                weather_type = self._get_weather_from_config(base_weather)
                if weather_type:
                    self._apply_base_weather(weather_type)
                return
        else:
            period_type = random.choices(
                [DayNightType.DAY, DayNightType.NIGHT, DayNightType.DUSK, DayNightType.DAWN],
                weights=[0.65, 0.25, 0.050, 0.050]
            )[0]

        duration = random.uniform(30.0, 90.0)
        self.day_night_state = DayNightState(period_type, duration)

        weather_type = self._get_weather_from_config(base_weather)
        if weather_type:
            self._apply_base_weather(weather_type)

        self._initialized = True

    def _apply_base_weather(self, weather_type):
        if hasattr(self.game_scene, 'battle_system'):
            self.game_scene.battle_system.weather_manager.set_base_weather(weather_type)

    def _get_weather_from_config(self, base_weather):
        if base_weather == "sunny":
            if self.day_night_state and self.day_night_state.is_night():
                return None
            return WeatherType.SUNNY
        elif base_weather == "rain":
            return WeatherType.RAIN
        elif base_weather == "none":
            return None
        else:
            is_night = self.day_night_state and self.day_night_state.is_night()
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
            # ===== SEMPRE ATUALIZA O ESTADO, MESMO PARA CAVE =====
            # Isso garante que o flash seja atualizado
            self.day_night_state.update(dt)

            # Se for transicional e acabou, muda o período
            if self.day_night_state.is_transitional() and not self.day_night_state.active:
                self._change_period()

    def _change_period(self):
        if not self.day_night_state:
            return

        day_night_mode = getattr(self.game_scene, 'day_night_mode', 'random')

        if day_night_mode in ["cave", "deep"]:
            self.day_night_state.active = True
            self.day_night_state.duration = 999999.0
            return

        if day_night_mode == "day":
            period_type = DayNightType.DAY
        elif day_night_mode == "night":
            period_type = DayNightType.NIGHT
        else:
            period_type = random.choices(
                [DayNightType.DAY, DayNightType.NIGHT],
                weights=[0.8, 0.2]
            )[0]

        duration = random.uniform(30.0, 90.0)
        self.day_night_state = DayNightState(period_type, duration)

        if period_type == DayNightType.NIGHT:
            self._validate_weather_on_night()

    def _validate_weather_on_night(self):
        if not hasattr(self.game_scene, 'battle_system'):
            return

        weather_mgr = self.game_scene.battle_system.weather_manager
        current_weather = weather_mgr.current_weather

        if current_weather and current_weather.type == WeatherType.SUNNY:
            if current_weather.is_base_weather:
                weather_mgr.base_weather = None
                weather_mgr.current_weather = None
                if weather_mgr.battle_system and weather_mgr.battle_system.effect_manager:
                    weather_mgr.battle_system.effect_manager.add_status_text(
                        None,
                        "O sol se pôs! O clima voltou ao normal.",
                        duration=3.0
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