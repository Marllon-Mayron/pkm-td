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

    def set_weather_from_move(self, weather_type: WeatherType,
                              duration: float = 10.0, source=None):
        """Igual a set_weather(), mas SÓ aceita climas NATURAIS.

        Moves (Sunny Day, Rain Dance, etc) usam este método — nunca vão
        conseguir ativar Sandstorm/Hail/Thunderstorm (map-only).
        """
        from src.battle.effects.specific.weather.weather_state import (
            is_natural_weather,
        )

        if not is_natural_weather(weather_type):
            print(f"[WEATHER_MANAGER] '{weather_type.value}' é MAP-ONLY — "
                  f"move ignorado")
            return False

        self.set_weather(weather_type, duration, source)
        return True

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
        from src.managers.sounds.ambient_sound_manager import ambient_sound_manager

        if self.battle_system and self.battle_system.effect_manager:
            if weather.is_base_weather:
                self.battle_system.effect_manager.add_status_text(
                    None,
                    f"{weather.get_display_name()} (clima da fase)",
                    duration=2.0
                )
            else:
                self.battle_system.effect_manager.add_status_text(
                    None,
                    weather.get_display_name(),
                    duration=2.0
                )

        # ===== TOCA SOM AMBIENTE =====
        if weather.type.value == "rain":
            ambient_sound_manager.play_ambient("rain", loop=True)
        elif weather.type.value == "sandstorm":
            ambient_sound_manager.play_ambient("sandstorm", loop=True)
        elif weather.type.value == "sunny":
            # Para sons de chuva/tempestade se estiver sol
            ambient_sound_manager.stop_ambient()

    def _on_weather_end(self, weather: WeatherState):
        from src.managers.sounds.ambient_sound_manager import ambient_sound_manager

        if self.battle_system and self.battle_system.effect_manager:
            if not weather.is_base_weather:
                self.battle_system.effect_manager.add_status_text(
                    None,
                    f"{weather.get_display_name()} acabou!",
                    duration=2.0
                )

        # ===== PARA O SOM AMBIENTE =====
        ambient_sound_manager.stop_ambient(fade_ms=500)

    def _apply_weather_damage(self, dt: float):
        """Aplica dano de clima a cada tick (a cada ~2 segundos)"""
        if not self.current_weather or not self.current_weather.active:
            return

        # Só Sandstorm e Hail causa dano
        if self.current_weather.type.value not in ("sandstorm", "hail"):
            return

        self._weather_damage_timer += dt

        # Tick a cada 2 segundos (simula um "turno")
        if self._weather_damage_timer >= 2.0:
            self._weather_damage_timer = 0
            self._apply_weather_tick_damage()

    def _apply_weather_tick_damage(self):
        """Aplica dano de Sandstorm ou Hail (1/16 do HP máximo) a cada tick."""
        if not self.battle_system or not self.battle_system.game_scene:
            return

        weather_type = self.current_weather.type.value
        game_scene = self.battle_system.game_scene
        all_pokemon = []

        if hasattr(game_scene, 'placement_manager'):
            all_pokemon.extend(game_scene.placement_manager.placed_pokemon)
        if hasattr(game_scene, 'wave_manager'):
            all_pokemon.extend(game_scene.wave_manager.active_enemies)

        # ===== Tipos imunes por clima =====
        if weather_type == "sandstorm":
            immune_types = {'rock', 'ground', 'steel'}
            immune_msg = "não foi afetado pela tempestade!"
        elif weather_type == "hail":
            immune_types = {'ice'}
            immune_msg = "não foi afetado pelo granizo!"
        else:
            return

        for pokemon in all_pokemon:
            if not pokemon.is_alive() or pokemon.is_defeated:
                continue

            if any(t.lower() in immune_types for t in pokemon.types):
                if self.battle_system.effect_manager:
                    self.battle_system.effect_manager.add_status_text(
                        pokemon, f"{pokemon.name} {immune_msg}", duration=1.0
                    )
                continue

            damage = max(1, pokemon.max_hp // 16)
            old_hp = pokemon.current_hp
            pokemon.take_damage(damage, attacker=None)
            actual_damage = old_hp - pokemon.current_hp

            if actual_damage > 0 and self.battle_system.effect_manager:
                label = "Tempestade de Areia" if weather_type == "sandstorm" else "Granizo"
                self.battle_system.effect_manager.add_status_text(
                    pokemon, f"{label}: -{actual_damage} HP", duration=1.5
                )
                if hasattr(pokemon, 'play_hurt_animation'):
                    pokemon.play_hurt_animation()