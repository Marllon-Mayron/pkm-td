# src/battle/effects/specific/weather/weather_filter.py

import pygame
from src.battle.effects.specific.weather.rain_particle_system import RainParticleSystem


class WeatherFilter:
    """
    Filtro visual para o clima + sistema de partículas (chuva).
    """

    def __init__(self):
        self.surface = None
        self.last_size = None
        self._rain = None  # RainParticleSystem (criado on-demand)

    # ------------------------------------------------------------------ #
    def _ensure_rain(self, viewport_rect):
        if self._rain is None:
            self._rain = RainParticleSystem(viewport_rect, drop_count=45, scale=1.0)
        else:
            self._rain.set_viewport(viewport_rect)
        return self._rain

    # ------------------------------------------------------------------ #
    def render(self, screen, weather_state, viewport_rect, dt: float = 0.0):
        """Renderiza o filtro de clima e, se for chuva, as partículas."""

        # ===== Clima inativo =====
        if not weather_state or not weather_state.active:
            if self._rain and self._rain.active:
                self._rain.stop()
            return

        # ===== Filtro de cor (comportamento atual) =====
        color = self._get_filter_color(weather_state)

        if color[3] > 0:
            current_size = (viewport_rect.width, viewport_rect.height)
            if self.last_size != current_size or self.surface is None:
                self.surface = pygame.Surface(current_size, pygame.SRCALPHA)
                self.last_size = current_size

            self.surface.fill((0, 0, 0, 0))
            pygame.draw.rect(self.surface, color, self.surface.get_rect())

            if weather_state.is_base_weather:
                final_alpha = color[3]
            else:
                progress = weather_state.get_progress()
                if progress < 0.2:
                    alpha_factor = progress / 0.2
                elif progress > 0.8:
                    alpha_factor = (1.0 - progress) / 0.2
                else:
                    alpha_factor = 1.0
                final_alpha = int(color[3] * alpha_factor)

            self.surface.set_alpha(final_alpha)
            screen.blit(self.surface, (viewport_rect.x, viewport_rect.y))

        # ===== PARTÍCULAS DE CHUVA =====
        weather_type = weather_state.type.value
        is_raining = (weather_type == "rain")

        if is_raining:
            rain = self._ensure_rain(viewport_rect)
            if not rain.active:
                rain.start()

            # Só atualiza/renderiza se houver dt (evita travar em chamadas antigas)
            if dt > 0:
                rain.update(dt)

            # Recorta ao viewport para não vazar pra HUD
            prev_clip = screen.get_clip()
            screen.set_clip(pygame.Rect(
                viewport_rect.x, viewport_rect.y,
                viewport_rect.width, viewport_rect.height,
            ))
            rain.render(screen)
            screen.set_clip(prev_clip)
        else:
            if self._rain and self._rain.active:
                self._rain.stop()

    # ------------------------------------------------------------------ #
    def _get_filter_color(self, weather_state) -> tuple:
        weather_type = weather_state.type.value
        if weather_type == "sandstorm":
            return (194, 178, 128, 110)
        elif weather_type == "rain":
            return (100, 100, 200, 110)
        elif weather_type == "sunny":
            return (255, 200, 100, 110)
        return (255, 0, 0, 110)

    # ------------------------------------------------------------------ #
    def clear(self):
        self.surface = None
        self.last_size = None
        if self._rain:
            self._rain.stop()
            self._rain = None