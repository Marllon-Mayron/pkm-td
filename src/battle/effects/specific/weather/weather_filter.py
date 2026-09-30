# src/battle/effects/specific/weather/weather_filter.py

import pygame

from src.battle.effects.specific.weather.snow_particle_system import SnowParticleSystem
from src.battle.effects.specific.weather.rain_particle_system import RainParticleSystem


class WeatherFilter:
    """
    Filtro visual para o clima + sistema de partículas (chuva).
    """

    def __init__(self):
        self.surface = None
        self.last_size = None
        self._rain = None
        self._snow = None

    # ------------------------------------------------------------------ #
    def _ensure_rain(self, viewport_rect):
        if self._rain is None:
            self._rain = RainParticleSystem(viewport_rect, drop_count=45, scale=1.0)
        else:
            self._rain.set_viewport(viewport_rect)
        return self._rain

    def _ensure_snow(self, viewport_rect):
        if self._snow is None:
            self._snow = SnowParticleSystem(viewport_rect, flake_count=45, scale=1.0)
        else:
            self._snow.set_viewport(viewport_rect)
        return self._snow

    # ------------------------------------------------------------------ #
    def render(self, screen, weather_state, viewport_rect, dt: float = 0.0):
        """Renderiza o filtro de clima e, se for chuva, as partículas."""

        # ===== Clima inativo =====
        if not weather_state or not weather_state.active:
            if self._rain and self._rain.active:
                self._rain.stop()
            if self._snow and self._snow.active:
                self._snow.stop()
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
                # ===== JANELA DE FADE FIXA (em segundos) =====
                FADE_WINDOW = 2.0  # 2s de fade-in e 2s de fade-out

                elapsed = weather_state.max_duration - weather_state.duration
                remaining = weather_state.duration

                if elapsed < FADE_WINDOW:
                    # Fade-in pelos primeiros 2s
                    alpha_factor = elapsed / FADE_WINDOW
                elif remaining < FADE_WINDOW:
                    # Fade-out pelos últimos 2s
                    alpha_factor = remaining / FADE_WINDOW
                else:
                    alpha_factor = 1.0

                alpha_factor = max(0.0, min(1.0, alpha_factor))
                final_alpha = int(color[3] * alpha_factor)

            self.surface.set_alpha(final_alpha)
            screen.blit(self.surface, (viewport_rect.x, viewport_rect.y))

        # ===== PARTÍCULAS =====
        weather_type = weather_state.type.value
        is_raining = (weather_type == "rain")
        is_hailing = (weather_type == "hail")

        # --- CHUVA ---
        if is_raining:
            rain = self._ensure_rain(viewport_rect)
            if not rain.active:
                rain.start()
            if dt > 0:
                rain.update(dt)
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

        # --- GRANIZO ---
        if is_hailing:
            snow = self._ensure_snow(viewport_rect)
            if not snow.active:
                snow.start()
            if dt > 0:
                snow.update(dt)
            prev_clip = screen.get_clip()
            screen.set_clip(pygame.Rect(
                viewport_rect.x, viewport_rect.y,
                viewport_rect.width, viewport_rect.height,
            ))
            snow.render(screen)
            screen.set_clip(prev_clip)
        else:
            if self._snow and self._snow.active:
                self._snow.stop()

    # ------------------------------------------------------------------ #
    def _get_filter_color(self, weather_state) -> tuple:
        weather_type = weather_state.type.value
        if weather_type == "sandstorm":
            return (194, 178, 128, 110)
        elif weather_type == "rain":
            return (100, 100, 200, 110)
        elif weather_type == "sunny":
            return (255, 200, 100, 110)
        elif weather_type == "hail":
            return (180, 220, 255, 130)
        return (255, 0, 0, 110)

    # ------------------------------------------------------------------ #
    def clear(self):
        self.surface = None
        self.last_size = None
        if self._rain:
            self._rain.stop()
            self._rain = None
        if self._snow:
            self._snow.stop()
            self._snow = None