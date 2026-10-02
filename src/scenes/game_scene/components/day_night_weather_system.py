# src/scenes/game_scene/components/day_night_weather_system.py

import random
from src.battle.effects.specific.day_night.day_night_state import (
    DayNightType, DayNightState,
    CYCLE_ORDER, DEFAULT_PERIOD_DURATION, get_next_cycle_period,
)
from src.battle.effects.specific.weather.weather_state import WeatherType


class DayNightWeatherSystem:

    def __init__(self, game_scene):
        self.game_scene = game_scene
        self.day_night_state = None
        self._initialized = False

        self.MAP_WEATHER_TYPES = [
            None, None, None, None, None, None, None, None,
            WeatherType.SUNNY,
            WeatherType.RAIN,
            WeatherType.HAIL,
        ]

    def initialize(self):
        if self._initialized:
            return

        day_night_mode = getattr(self.game_scene, 'day_night_mode', 'random')
        base_weather = getattr(self.game_scene, 'base_weather', 'random')

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

            if period_type in (DayNightType.CAVE, DayNightType.DEEP):
                self.day_night_state = DayNightState(period_type, 999999.0)
                self.day_night_state.active = True
                self._initialized = True
                weather_type = self._get_weather_from_config(base_weather)
                if weather_type:
                    self._apply_base_weather(weather_type)
                return
        else:
            # Sorteio inicial ponderado (dia é mais comum)
            period_type = random.choices(
                CYCLE_ORDER,
                weights=[0.05, 0.65, 0.05, 0.25],  # DAWN, DAY, DUSK, NIGHT
            )[0]

        # ===== DURAÇÃO IGUAL PARA TODOS OS PERÍODOS =====
        self.day_night_state = DayNightState(
            period_type, DEFAULT_PERIOD_DURATION
        )

        weather_type = self._get_weather_from_config(base_weather)
        if weather_type:
            self._apply_base_weather(weather_type)

        self._initialized = True

    # ------------------------------------------------------------------
    def _apply_base_weather(self, weather_type):
        if hasattr(self.game_scene, 'battle_system'):
            self.game_scene.battle_system.weather_manager.set_base_weather(weather_type)

            from src.managers.sounds.ambient_sound_manager import ambient_sound_manager
            if weather_type.value == "rain":
                ambient_sound_manager.play_ambient("rain", loop=True)
            elif weather_type.value == "sandstorm":
                ambient_sound_manager.play_ambient("sandstorm", loop=True)
            elif weather_type.value == "hail":
                try:
                    ambient_sound_manager.play_ambient("hail", loop=True)
                except Exception:
                    ambient_sound_manager.stop_ambient()
            else:
                ambient_sound_manager.stop_ambient()

    def _get_weather_from_config(self, base_weather):
        if base_weather == "sunny":
            if self.day_night_state and self.day_night_state.is_night():
                return None
            return WeatherType.SUNNY
        if base_weather == "rain":
            return WeatherType.RAIN
        if base_weather == "none":
            return None

        is_night = self.day_night_state and self.day_night_state.is_night()
        for _ in range(10):
            weather_type = random.choice(self.MAP_WEATHER_TYPES)
            if weather_type == WeatherType.SUNNY and is_night:
                continue
            return weather_type
        return None

    # ------------------------------------------------------------------
    def update(self, dt: float):
        if not self._initialized:
            self.initialize()
            return

        if self.day_night_state:
            self.day_night_state.update(dt)

            if self.day_night_state.is_transitional() and not self.day_night_state.active:
                self._change_period()

    def _change_period(self):
        if not self.day_night_state:
            return

        day_night_mode = getattr(self.game_scene, 'day_night_mode', 'random')
        current_type = self.day_night_state.type

        # CAVE / DEEP são permanentes
        if day_night_mode in ("cave", "deep"):
            self.day_night_state.active = True
            self.day_night_state.duration = 999999.0
            return

        # ===== CICLO NATURAL: DAWN → DAY → DUSK → NIGHT → DAWN =====
        forced_map = {
            "day": DayNightType.DAY,
            "night": DayNightType.NIGHT,
            "dusk": DayNightType.DUSK,
            "dawn": DayNightType.DAWN,
        }

        if day_night_mode in forced_map:
            next_type = forced_map[day_night_mode]
        else:
            next_type = get_next_cycle_period(current_type)

        # ===== MESMA DURAÇÃO PARA TODOS OS PERÍODOS =====
        self.day_night_state = DayNightState(
            next_type,
            DEFAULT_PERIOD_DURATION,
            previous_type=current_type,
        )

        if next_type == DayNightType.NIGHT:
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
                        duration=3.0,
                    )

    # ------------------------------------------------------------------
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