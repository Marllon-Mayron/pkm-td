# src/battle/effects/specific/day_night/day_night_filter.py

import pygame
import random
import math

from src.battle.effects.specific.day_night.day_night_state import DayNightType


class DayNightFilter:
    """
    Filtro visual para o período do dia/noite/ambiente.
    Renderizado sobre toda a tela.
    """

    def __init__(self):
        self.surface = None
        self.last_size = None
        self._star_surface = None
        self._moon_surface = None
        self._sun_surface = None
        self._bubble_surface = None
        self._star_cache = {}

    def _create_stars(self, width, height, count=150):
        """Cria uma superfície com estrelas para a noite"""
        if self._star_surface is None or self._star_surface.get_size() != (width, height):
            star_surface = pygame.Surface((width, height), pygame.SRCALPHA)
            star_surface.fill((0, 0, 0, 0))

            for _ in range(count):
                x = random.randint(0, width)
                y = random.randint(0, height)
                size = random.choice([1, 1, 1, 2, 2, 3])
                alpha = random.randint(150, 255)
                brightness = random.randint(180, 255)

                if size == 1:
                    pygame.draw.circle(star_surface, (brightness, brightness, brightness, alpha),
                                       (x, y), size)
                else:
                    alpha = random.randint(100, 200)
                    pygame.draw.circle(star_surface, (brightness, brightness, brightness, alpha),
                                       (x, y), size)

            for _ in range(5):
                x = random.randint(0, width)
                y = random.randint(0, height)
                alpha = random.randint(80, 180)
                pygame.draw.circle(star_surface, (255, 255, 200, alpha),
                                   (x, y), random.choice([1, 2]))

            self._star_surface = star_surface

        return self._star_surface

    def _create_moon(self, size=60):
        """Cria uma superfície com a lua"""
        if self._moon_surface is None:
            moon_surface = pygame.Surface((size, size), pygame.SRCALPHA)
            moon_surface.fill((0, 0, 0, 0))

            moon_color = (240, 235, 200)
            pygame.draw.circle(moon_surface, moon_color, (size // 2, size // 2), size // 2 - 4)

            for i in range(8, 0, -2):
                alpha = 40 - i * 3
                glow_color = (255, 250, 220, alpha)
                pygame.draw.circle(moon_surface, glow_color,
                                   (size // 2, size // 2), size // 2 + i)

            crater_positions = [
                (size // 3, size // 3, 5),
                (size // 2 + 10, size // 4, 4),
                (size // 4 + 5, size // 2 + 8, 6),
                (size // 2 + 15, size // 2 + 12, 3),
                (size // 3 + 20, size // 3 + 15, 4),
            ]

            crater_color = (200, 195, 170)
            for cx, cy, r in crater_positions:
                pygame.draw.circle(moon_surface, crater_color, (cx, cy), r)
                shadow_color = (180, 175, 150)
                pygame.draw.circle(moon_surface, shadow_color, (cx + 1, cy + 1), r, 1)

            self._moon_surface = moon_surface

        return self._moon_surface

    def _create_sun(self, size=50):
        """Cria uma superfície com o sol para amanhecer/entardecer"""
        if self._sun_surface is None:
            sun_surface = pygame.Surface((size, size), pygame.SRCALPHA)
            sun_surface.fill((0, 0, 0, 0))

            sun_color = (255, 200, 50)
            pygame.draw.circle(sun_surface, sun_color, (size // 2, size // 2), size // 2 - 4)

            for i in range(10, 0, -2):
                alpha = 60 - i * 4
                glow_color = (255, 220, 100, alpha)
                pygame.draw.circle(sun_surface, glow_color,
                                   (size // 2, size // 2), size // 2 + i)

            self._sun_surface = sun_surface

        return self._sun_surface

    def _create_bubbles(self, width, height, count=30):
        """Cria bolhas para o fundo do mar"""
        if self._bubble_surface is None or self._bubble_surface.get_size() != (width, height):
            bubble_surface = pygame.Surface((width, height), pygame.SRCALPHA)
            bubble_surface.fill((0, 0, 0, 0))

            for _ in range(count):
                x = random.randint(0, width)
                y = random.randint(0, height)
                size = random.randint(2, 8)
                alpha = random.randint(50, 150)
                color = (150, 200, 255, alpha)
                pygame.draw.circle(bubble_surface, color, (x, y), size, 1)
                if size > 4:
                    pygame.draw.circle(bubble_surface, (255, 255, 255, 30),
                                       (x - size // 3, y - size // 3), size // 3)

            self._bubble_surface = bubble_surface

        return self._bubble_surface

    def render(self, screen, day_night_state, viewport_rect):
        """
        Renderiza o filtro de dia/noite/ambiente sobre a tela.
        """
        if not day_night_state or not day_night_state.active:
            return

        color = day_night_state.get_filter_color()

        if color[3] <= 0:
            return

        current_size = (viewport_rect.width, viewport_rect.height)

        filter_surface = pygame.Surface(current_size)
        filter_surface.fill(color[:3])
        filter_surface.set_alpha(color[3])

        if day_night_state.type == DayNightType.NIGHT:
            stars = self._create_stars(viewport_rect.width, viewport_rect.height, 150)
            filter_surface.blit(stars, (0, 0))

            moon = self._create_moon(50)
            moon_x = viewport_rect.width - moon.get_width() - 40
            moon_y = 30
            filter_surface.blit(moon, (moon_x, moon_y))

            glow_surface = pygame.Surface((viewport_rect.width, viewport_rect.height), pygame.SRCALPHA)
            glow_center_x = moon_x + moon.get_width() // 2
            glow_center_y = moon_y + moon.get_height() // 2

            for radius in range(80, 20, -10):
                alpha = 10 - (80 - radius) // 10 * 2
                if alpha > 0:
                    glow_color = (200, 220, 255, alpha)
                    pygame.draw.circle(glow_surface, glow_color,
                                       (glow_center_x, glow_center_y), radius)

            filter_surface.blit(glow_surface, (0, 0), special_flags=pygame.BLEND_RGBA_ADD)

        elif day_night_state.type == DayNightType.DUSK:
            sun = self._create_sun(40)
            sun_x = viewport_rect.width - sun.get_width() - 60
            sun_y = viewport_rect.height - sun.get_height() - 40
            filter_surface.blit(sun, (sun_x, sun_y))

            for y in range(viewport_rect.height // 4):
                progress = y / (viewport_rect.height // 4)
                alpha = int(30 * (1 - progress))
                color_warm = (200, 120, 50, alpha)
                pygame.draw.line(filter_surface, color_warm,
                                 (0, viewport_rect.height - y),
                                 (viewport_rect.width, viewport_rect.height - y))

        elif day_night_state.type == DayNightType.DAWN:
            sun = self._create_sun(35)
            sun_x = 40
            sun_y = viewport_rect.height - sun.get_height() - 30
            filter_surface.blit(sun, (sun_x, sun_y))

            for y in range(viewport_rect.height // 3):
                progress = y / (viewport_rect.height // 3)
                alpha = int(40 * (1 - progress))
                color_dawn = (255, 180, 150, alpha)
                pygame.draw.line(filter_surface, color_dawn,
                                 (0, viewport_rect.height - y),
                                 (viewport_rect.width, viewport_rect.height - y))

        # ===== CAVERNA =====
        # Apenas o filtro escuro, sem animações extras
        # O fade é controlado pela opacidade da cor

        elif day_night_state.type == DayNightType.DEEP:
            bubbles = self._create_bubbles(viewport_rect.width, viewport_rect.height, 35)
            filter_surface.blit(bubbles, (0, 0))

            for _ in range(5):
                x = random.randint(0, viewport_rect.width)
                width = random.randint(30, 80)
                alpha = random.randint(20, 50)
                color_ray = (100, 180, 255, alpha)
                for y in range(0, viewport_rect.height, 2):
                    offset = math.sin(y / 50 + x / 30) * 20
                    pygame.draw.line(filter_surface, color_ray,
                                     (x + offset, y),
                                     (x + offset + width, y))

        screen.blit(filter_surface, (viewport_rect.x, viewport_rect.y))

    def clear(self):
        """Limpa o cache"""
        self.surface = None
        self.last_size = None
        self._star_surface = None
        self._moon_surface = None
        self._sun_surface = None
        self._bubble_surface = None
        self._star_cache.clear()