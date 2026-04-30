# src/battle/effects/specific/weather/weather_manager.py

from typing import Optional
from src.battle.effects.specific.weather.weather_state import WeatherType, WeatherState


class WeatherManager:

    def __init__(self, battle_system):
        self.battle_system = battle_system
        self.current_weather: Optional[WeatherState] = None
        self._weather_damage_timer = 0.0

    def set_weather(self, weather_type: WeatherType, duration: float = 10.0, source=None):
        if self.current_weather:
            self._on_weather_end(self.current_weather)

        self.current_weather = WeatherState(weather_type, duration, source)
        self._weather_damage_timer = 0.0
        self._on_weather_start(self.current_weather)

    def clear_weather(self):
        if self.current_weather:
            self._on_weather_end(self.current_weather)
            self.current_weather = None
            self._weather_damage_timer = 0.0

    def update(self, dt: float):
        """Atualiza o clima atual"""
        if self.current_weather:
            self._apply_weather_damage(dt)

            still_active = self.current_weather.update(dt)

            if not still_active:
                self._on_weather_end(self.current_weather)
                self.current_weather = None

    def get_current_weather(self) -> Optional[WeatherState]:
        return self.current_weather

    def is_weather_active(self, weather_type: WeatherType = None) -> bool:
        if not self.current_weather:
            return False
        if weather_type is None:
            return True
        return self.current_weather.type == weather_type

    def _on_weather_start(self, weather: WeatherState):
        if self.battle_system and self.battle_system.effect_manager:
            self.battle_system.effect_manager.add_status_text(
                None,
                weather.get_display_name(),
                duration=2.0
            )

    def _on_weather_end(self, weather: WeatherState):
        if self.battle_system and self.battle_system.effect_manager:
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