# src/battle/effects/specific/day_night/day_night_filter.py

import pygame
import random
import math

from battle.effects.specific.day_night.day_night_state import *


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
        """Cria uma superfície com estrelas para a noite/caverna"""
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

            # Estrelas cadentes
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

            # Corpo da lua
            moon_color = (240, 235, 200)
            pygame.draw.circle(moon_surface, moon_color, (size // 2, size // 2), size // 2 - 4)

            # Brilho da lua (halo)
            for i in range(8, 0, -2):
                alpha = 40 - i * 3
                glow_color = (255, 250, 220, alpha)
                pygame.draw.circle(moon_surface, glow_color,
                                   (size // 2, size // 2), size // 2 + i)

            # Crateras
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

            # Corpo do sol
            sun_color = (255, 200, 50)
            pygame.draw.circle(sun_surface, sun_color, (size // 2, size // 2), size // 2 - 4)

            # Brilho do sol
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
                # Brilho da bolha
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

        # Obtém a cor do filtro
        color = day_night_state.get_filter_color()

        # ===== DIA: sem filtro =====
        if color[3] <= 0:
            return

        current_size = (viewport_rect.width, viewport_rect.height)

        # Cria ou recria a superfície se o tamanho mudou
        if self.last_size != current_size or self.surface is None:
            self.surface = pygame.Surface(current_size, pygame.SRCALPHA)
            self.last_size = current_size

        # Limpa a superfície
        self.surface.fill((0, 0, 0, 0))

        # ===== FILTRO BASE =====
        pygame.draw.rect(self.surface, color, self.surface.get_rect())

        # ===== NOITE =====
        if day_night_state.type == DayNightType.NIGHT:
            # Estrelas
            stars = self._create_stars(viewport_rect.width, viewport_rect.height, 150)
            self.surface.blit(stars, (0, 0))

            # Lua
            moon = self._create_moon(50)
            moon_x = viewport_rect.width - moon.get_width() - 40
            moon_y = 30
            self.surface.blit(moon, (moon_x, moon_y))

            # Brilho da lua
            glow_surface = pygame.Surface((viewport_rect.width, viewport_rect.height), pygame.SRCALPHA)
            glow_center_x = moon_x + moon.get_width() // 2
            glow_center_y = moon_y + moon.get_height() // 2

            for radius in range(80, 20, -10):
                alpha = 10 - (80 - radius) // 10 * 2
                if alpha > 0:
                    glow_color = (200, 220, 255, alpha)
                    pygame.draw.circle(glow_surface, glow_color,
                                       (glow_center_x, glow_center_y), radius)

            self.surface.blit(glow_surface, (0, 0), special_flags=pygame.BLEND_RGBA_ADD)

        # ===== ENTARDECER =====
        elif day_night_state.type == DayNightType.DUSK:
            # Sol se pondo (no canto inferior direito)
            sun = self._create_sun(40)
            sun_x = viewport_rect.width - sun.get_width() - 60
            sun_y = viewport_rect.height - sun.get_height() - 40
            self.surface.blit(sun, (sun_x, sun_y))

            # Cores quentes no horizonte (faixa inferior)
            for y in range(viewport_rect.height // 4):
                progress = y / (viewport_rect.height // 4)
                alpha = int(30 * (1 - progress))
                color_warm = (200, 120, 50, alpha)
                pygame.draw.line(self.surface, color_warm,
                                 (0, viewport_rect.height - y),
                                 (viewport_rect.width, viewport_rect.height - y))

        # ===== AMANHECER =====
        elif day_night_state.type == DayNightType.DAWN:
            # Sol nascendo (no canto inferior esquerdo)
            sun = self._create_sun(35)
            sun_x = 40
            sun_y = viewport_rect.height - sun.get_height() - 30
            self.surface.blit(sun, (sun_x, sun_y))

            # Cores suaves no horizonte
            for y in range(viewport_rect.height // 3):
                progress = y / (viewport_rect.height // 3)
                alpha = int(40 * (1 - progress))
                color_dawn = (255, 180, 150, alpha)
                pygame.draw.line(self.surface, color_dawn,
                                 (0, viewport_rect.height - y),
                                 (viewport_rect.width, viewport_rect.height - y))

        # ===== CAVERNA =====
        elif day_night_state.type == DayNightType.CAVE:
            # Gotas de água (efeito de caverna)
            for _ in range(8):
                x = random.randint(0, viewport_rect.width)
                y = random.randint(0, viewport_rect.height)
                alpha = random.randint(30, 80)
                size = random.randint(1, 3)
                pygame.draw.circle(self.surface, (100, 150, 200, alpha), (x, y), size)

            # Cristais/brilhos (pequenos pontos de luz)
            for _ in range(15):
                x = random.randint(0, viewport_rect.width)
                y = random.randint(0, viewport_rect.height)
                alpha = random.randint(50, 150)
                brightness = random.randint(150, 220)
                pygame.draw.circle(self.surface, (brightness, brightness, 200, alpha),
                                   (x, y), random.choice([1, 2]))

        # ===== FUNDO DO MAR =====
        elif day_night_state.type == DayNightType.DEEP:
            # Bolhas
            bubbles = self._create_bubbles(viewport_rect.width, viewport_rect.height, 35)
            self.surface.blit(bubbles, (0, 0))

            # Raios de luz (efeito de luz vindo de cima)
            for _ in range(5):
                x = random.randint(0, viewport_rect.width)
                width = random.randint(30, 80)
                alpha = random.randint(20, 50)
                color_ray = (100, 180, 255, alpha)
                for y in range(0, viewport_rect.height, 2):
                    offset = math.sin(y / 50 + x / 30) * 20
                    pygame.draw.line(self.surface, color_ray,
                                     (x + offset, y),
                                     (x + offset + width, y))

        # ===== INTENSIDADE =====
        # Ajusta a opacidade baseada no progresso
        progress = day_night_state.get_progress()

        # Para ambientes especiais (caverna, fundo do mar), mantém opacidade constante
        if day_night_state.type in [DayNightType.CAVE, DayNightType.DEEP]:
            alpha_factor = 1.0
        else:
            # Transição suave para dia/noite/entardecer/amanhecer
            if progress < 0.1:
                alpha_factor = progress / 0.1
            elif progress > 0.9:
                alpha_factor = (1.0 - progress) / 0.1
            else:
                alpha_factor = 1.0

        final_alpha = int(color[3] * alpha_factor)
        self.surface.set_alpha(final_alpha)

        # Renderiza na posição da viewport
        screen.blit(self.surface, (viewport_rect.x, viewport_rect.y))

    def clear(self):
        """Limpa o cache"""
        self.surface = None
        self.last_size = None
        self._star_surface = None
        self._moon_surface = None
        self._sun_surface = None
        self._bubble_surface = None
        self._star_cache.clear()