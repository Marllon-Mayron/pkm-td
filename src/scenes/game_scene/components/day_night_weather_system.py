# src/scenes/game_scene/components/day_night_weather_system.py

import random
from src.battle.effects.specific.day_night.day_night_state import DayNightType, DayNightState
from src.battle.effects.specific.weather.weather_state import WeatherType


class DayNightWeatherSystem:
    """
    Sistema que gerencia o dia/noite e clima da fase.

    Probabilidades:
    - Dia: 80%
    - Noite: 20%

    Clima BASE da fase (permanente até ser alterado por move):
    - Sem clima: 90%
    - Sunny Day: 5%
    - Chuva: 5%

    REGRA: Sunny Day NÃO pode ocorrer durante a NOITE.
    """

    def __init__(self, game_scene):
        self.game_scene = game_scene
        self.day_night_state = None
        self._initialized = False

        # ===== CLIMAS DISPONÍVEIS PARA O MAPA =====
        # 90% Sem clima, 5% Sunny, 5% Rain
        self.MAP_WEATHER_TYPES = [
            None, None, None, None, None, None, None, None, None,  # 90%
            WeatherType.SUNNY,  # 5%
            WeatherType.RAIN,   # 5%
        ]

    def initialize(self):
        """Inicializa o sistema com valores aleatórios para a fase"""
        if self._initialized:
            return

        # ===== DIA/NOITE ALEATÓRIO =====
        # 80% chance de dia, 20% de noite
        period_type = random.choices(
            [DayNightType.DAY, DayNightType.NIGHT],
            weights=[0.8, 0.2]
        )[0]

        duration = random.uniform(30.0, 90.0)
        self.day_night_state = DayNightState(period_type, duration)

        print(f"[DAY/NIGHT] Período: {self.day_night_state.get_display_name()} por {duration:.1f}s")

        # ===== CLIMA BASE DA FASE (COM VALIDAÇÃO) =====
        weather_type = self._get_valid_base_weather()

        if weather_type:
            weather_names = {
                WeatherType.SUNNY: "Sol Forte",
                WeatherType.RAIN: "Chuva",
            }
            print(f"[WEATHER_BASE] Clima BASE da fase: {weather_names.get(weather_type, weather_type.value)} (PERMANENTE)")

            if hasattr(self.game_scene, 'battle_system'):
                self.game_scene.battle_system.weather_manager.set_base_weather(weather_type)
        else:
            print(f"[WEATHER_BASE] Clima BASE da fase: Normal (PERMANENTE)")

        self._initialized = True

    def _get_valid_base_weather(self):
        """
        Retorna um clima válido para a fase, respeitando as regras:
        - Sunny Day NÃO pode ocorrer durante a NOITE
        """
        # Verifica se é noite
        is_night = self.is_night()

        # Tenta escolher um clima aleatório até encontrar um válido
        attempts = 0
        max_attempts = 10

        while attempts < max_attempts:
            weather_type = random.choice(self.MAP_WEATHER_TYPES)

            # ===== REGRA: Sunny Day NÃO funciona à noite =====
            if weather_type == WeatherType.SUNNY and is_night:
                print(f"[WEATHER_BASE] Sunny Day bloqueado (é noite) - tentando novamente...")
                attempts += 1
                continue

            # Clima válido encontrado
            return weather_type

        # Fallback: se não encontrar clima válido, retorna None (sem clima)
        print(f"[WEATHER_BASE] Nenhum clima válido encontrado após {max_attempts} tentativas - usando Normal")
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
        """Alterna entre dia e noite (mantendo as probabilidades)"""
        if not self.day_night_state:
            return

        # Escolhe novo período com as mesmas probabilidades
        # 80% dia, 20% noite
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
        """
        Quando a noite começa, verifica se o clima atual é Sunny Day.
        Se for, remove o clima (volta para Normal).
        """
        if not hasattr(self.game_scene, 'battle_system'):
            return

        weather_mgr = self.game_scene.battle_system.weather_manager
        current_weather = weather_mgr.current_weather

        # Verifica se o clima atual é Sunny Day (base ou temporário)
        if current_weather and current_weather.type == WeatherType.SUNNY:
            # Se for clima base, remove e volta para Normal
            if current_weather.is_base_weather:
                print(f"[WEATHER_BASE] Sunny Day removido porque a NOITE chegou!")
                # Remove o clima base
                weather_mgr.base_weather = None
                weather_mgr.current_weather = None
                # Mostra mensagem
                if weather_mgr.battle_system and weather_mgr.battle_system.effect_manager:
                    weather_mgr.battle_system.effect_manager.add_status_text(
                        None,
                        "O sol se pôs! O clima voltou ao normal.",
                        duration=2.0
                    )
            else:
                # Se for clima temporário de move, ele vai expirar normalmente
                print(f"[WEATHER_BASE] Sunny Day temporário ainda ativo, mas a noite chegou. Aguardando expirar...")

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