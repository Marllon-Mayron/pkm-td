# src/battle/effects/specific/weather/weather_manager.py

from typing import Optional
from src.battle.effects.specific.weather.weather_state import WeatherType, WeatherState


class WeatherManager:

    def __init__(self, battle_system):
        self.battle_system = battle_system
        self.current_weather: Optional[WeatherState] = None
        self.base_weather: Optional[WeatherState] = None  # Clima permanente da fase
        self._weather_damage_timer = 0.0

    def set_base_weather(self, weather_type: WeatherType, duration: float = None):
        """
        Define o clima BASE da fase (permanente).
        """
        if self.base_weather:
            self.base_weather.active = False
            self.base_weather = None

        self.base_weather = WeatherState(weather_type, duration or 999999.0, source=None, is_base_weather=True)
        self.base_weather.active = True

        if self.current_weather is None or not self.current_weather.active:
            self.current_weather = self.base_weather

        print(f"[WEATHER_MANAGER] Clima BASE definido: {weather_type.value} (permanente)")

    def set_weather(self, weather_type: WeatherType, duration: float = 10.0, source=None):
        """
        Define um clima TEMPORÁRIO (de move).
        Quando expirar, restaura o clima base.
        """
        # Se já tem clima temporário, remove
        if self.current_weather and not self.current_weather.is_base_weather:
            self._on_weather_end(self.current_weather)

        # Cria o clima temporário
        self.current_weather = WeatherState(weather_type, duration, source, is_base_weather=False)
        self._weather_damage_timer = 0.0
        self._on_weather_start(self.current_weather)

        print(f"[WEATHER_MANAGER] Clima TEMPORÁRIO: {weather_type.value} por {duration:.1f}s (fonte: {source.name if source else '?'})")

    def clear_weather(self):
        """Remove o clima temporário e restaura o base"""
        if self.current_weather and not self.current_weather.is_base_weather:
            self._on_weather_end(self.current_weather)
            self.current_weather = None
            self._weather_damage_timer = 0.0

            # ===== RESTAURA O CLIMA BASE =====
            if self.base_weather and self.base_weather.active:
                self.current_weather = self.base_weather
                print(f"[WEATHER_MANAGER] Clima BASE restaurado: {self.base_weather.type.value}")
                self._on_weather_start(self.current_weather)

    def update(self, dt: float):
        """Atualiza o clima atual"""
        if not self.current_weather:
            return

        # ===== ATUALIZA O CLIMA ATUAL =====
        self._apply_weather_damage(dt)

        still_active = self.current_weather.update(dt)

        if not still_active:
            # Se o clima expirou, limpa e restaura o base
            self._on_weather_end(self.current_weather)
            self.current_weather = None

            # ===== RESTAURA O CLIMA BASE =====
            if self.base_weather and self.base_weather.active:
                self.current_weather = self.base_weather
                print(f"[WEATHER_MANAGER] Clima BASE restaurado: {self.base_weather.type.value}")
                self._on_weather_start(self.current_weather)

    def get_current_weather(self) -> Optional[WeatherState]:
        return self.current_weather

    def is_weather_active(self, weather_type: WeatherType = None) -> bool:
        if not self.current_weather:
            return False
        if weather_type is None:
            return True
        return self.current_weather.type == weather_type

    def is_base_weather_active(self) -> bool:
        """Verifica se o clima ativo é o base (não temporário)"""
        return self.current_weather and self.current_weather.is_base_weather

    def is_weather_from_move(self) -> bool:
        """Verifica se o clima atual foi causado por um move"""
        return self.current_weather and not self.current_weather.is_base_weather and self.current_weather.source is not None

    def _on_weather_start(self, weather: WeatherState):
        if self.battle_system and self.battle_system.effect_manager:
            if weather.is_base_weather:
                # Clima base: mensagem mais sutil
                self.battle_system.effect_manager.add_status_text(
                    None,
                    f"{weather.get_display_name()} (clima da fase)",
                    duration=2.0
                )
            else:
                # Clima temporário: mensagem normal
                self.battle_system.effect_manager.add_status_text(
                    None,
                    weather.get_display_name(),
                    duration=2.0
                )

    def _on_weather_end(self, weather: WeatherState):
        if self.battle_system and self.battle_system.effect_manager:
            # Só mostra mensagem se não for clima base (que nunca acaba)
            if not weather.is_base_weather:
                self.battle_system.effect_manager.add_status_text(
                    None,
                    f"{weather.get_display_name()} acabou!",
                    duration=2.0
                )

    def _apply_weather_damage(self, dt: float):
        """Aplica dano de clima a cada tick (a cada ~2 segundos)"""
        if not self.current_weather or not self.current_weather.active:
            return

        # Só Sandstorm causa dano
        if self.current_weather.type.value != "sandstorm":
            return

        self._weather_damage_timer += dt

        # Tick a cada 2 segundos (simula um "turno")
        if self._weather_damage_timer >= 2.0:
            self._weather_damage_timer = 0
            self._apply_sandstorm_damage()

    def _apply_sandstorm_damage(self):
        """Aplica dano de 1/16 do HP máximo para todos os Pokémon não-imunes"""
        if not self.battle_system or not self.battle_system.game_scene:
            return

        game_scene = self.battle_system.game_scene
        all_pokemon = []

        # Aliados
        if hasattr(game_scene, 'placement_manager'):
            all_pokemon.extend(game_scene.placement_manager.placed_pokemon)

        # Inimigos
        if hasattr(game_scene, 'wave_manager'):
            all_pokemon.extend(game_scene.wave_manager.active_enemies)

        for pokemon in all_pokemon:
            if not pokemon.is_alive() or pokemon.is_defeated:
                continue

            # Tipos imunes a Sandstorm: Rock, Ground, Steel
            is_immune = any(t.lower() in ['rock', 'ground', 'steel'] for t in pokemon.types)

            if is_immune:
                if self.battle_system.effect_manager:
                    self.battle_system.effect_manager.add_status_text(
                        pokemon,
                        f"{pokemon.name} não foi afetado pela tempestade!",
                        duration=1.0
                    )
                continue

            # Calcula dano: 1/16 do HP máximo
            damage = max(1, pokemon.max_hp // 16)

            old_hp = pokemon.current_hp
            pokemon.take_damage(damage, attacker=None)
            actual_damage = old_hp - pokemon.current_hp

            if actual_damage > 0 and self.battle_system.effect_manager:
                self.battle_system.effect_manager.add_status_text(
                    pokemon,
                    f"Tempestade de Areia: -{actual_damage} HP",
                    duration=1.5
                )

                if hasattr(pokemon, 'play_hurt_animation'):
                    pokemon.play_hurt_animation()