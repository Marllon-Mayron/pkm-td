# src/battle/effects/specific/day_night/day_night_filter.py

import pygame
import random
import math


class DayNightFilter:
    """
    Filtro visual para o período do dia/noite.
    Renderizado sobre toda a tela.
    """

    def __init__(self):
        self.surface = None
        self.last_size = None
        self._star_surface = None
        self._moon_surface = None
        self._star_cache = {}

    def _create_stars(self, width, height, count=150):
        """
        Cria uma superfície com estrelas para a noite.
        Aumentei o número de estrelas e adicionei variação de tamanho/brilho.
        """
        if self._star_surface is None or self._star_surface.get_size() != (width, height):
            star_surface = pygame.Surface((width, height), pygame.SRCALPHA)
            star_surface.fill((0, 0, 0, 0))

            # Estrelas pequenas (maioria)
            for _ in range(count):
                x = random.randint(0, width)
                y = random.randint(0, height)
                size = random.choice([1, 1, 1, 2, 2, 3])  # Maioria pequenas
                alpha = random.randint(150, 255)
                brightness = random.randint(180, 255)

                # Estrelas com brilho variável
                if size == 1:
                    pygame.draw.circle(star_surface, (brightness, brightness, brightness, alpha),
                                       (x, y), size)
                else:
                    # Estrelas maiores têm brilho mais suave
                    alpha = random.randint(100, 200)
                    pygame.draw.circle(star_surface, (brightness, brightness, brightness, alpha),
                                       (x, y), size)

            # ===== ESTRELAS CADENTES (algumas com brilho extra) =====
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

            # Corpo da lua (amarelo claro)
            moon_color = (240, 235, 200)
            pygame.draw.circle(moon_surface, moon_color, (size // 2, size // 2), size // 2 - 4)

            # Brilho da lua (halo)
            for i in range(8, 0, -2):
                alpha = 40 - i * 3
                glow_color = (255, 250, 220, alpha)
                pygame.draw.circle(moon_surface, glow_color,
                                   (size // 2, size // 2), size // 2 + i)

            # Crateras (detalhes na lua)
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
                # Sombra da cratera
                shadow_color = (180, 175, 150)
                pygame.draw.circle(moon_surface, shadow_color, (cx + 1, cy + 1), r, 1)

            self._moon_surface = moon_surface

        return self._moon_surface

    def render(self, screen, day_night_state, viewport_rect):
        """
        Renderiza o filtro de dia/noite sobre a tela.

        Args:
            screen: Superfície da tela
            day_night_state: Estado do período atual
            viewport_rect: Retângulo da viewport
        """
        if not day_night_state or not day_night_state.active:
            return

        # Obtém a cor do filtro
        color = day_night_state.get_filter_color()

        # ===== DIA: sem filtro =====
        if color[3] <= 0:
            return

        # ===== NOITE: filtro escuro com estrelas e lua =====
        if day_night_state.is_night():
            # Cria ou recria a superfície se o tamanho mudou
            current_size = (viewport_rect.width, viewport_rect.height)
            if self.last_size != current_size or self.surface is None:
                self.surface = pygame.Surface(current_size, pygame.SRCALPHA)
                self.last_size = current_size

            # Limpa a superfície
            self.surface.fill((0, 0, 0, 0))

            # ===== FILTRO ESCURO =====
            pygame.draw.rect(self.surface, color, self.surface.get_rect())

            # ===== ESTRELAS =====
            stars = self._create_stars(viewport_rect.width, viewport_rect.height, 150)
            self.surface.blit(stars, (0, 0))

            # ===== LUA =====
            moon = self._create_moon(50)
            # Posiciona a lua no canto superior direito
            moon_x = viewport_rect.width - moon.get_width() - 40
            moon_y = 30
            self.surface.blit(moon, (moon_x, moon_y))

            # ===== BRILHO DA LUA (reflexo suave) =====
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

            # ===== INTENSIDADE DA NOITE =====
            # Noite mais escura no início e no fim (efeito de transição)
            progress = day_night_state.get_progress()

            # No início da noite: mais claro (pôr do sol)
            if progress < 0.1:
                alpha_factor = progress / 0.1
            # No meio da noite: mais escuro
            elif progress < 0.9:
                alpha_factor = 1.0
            # No final da noite: mais claro (amanhecer)
            else:
                alpha_factor = (1.0 - progress) / 0.1

            # Aplica a opacidade final
            final_alpha = int(color[3] * alpha_factor)
            self.surface.set_alpha(final_alpha)

            # Renderiza na posição da viewport
            screen.blit(self.surface, (viewport_rect.x, viewport_rect.y))

        else:
            # ===== OUTROS PERÍODOS (DUSK, DAWN) =====
            current_size = (viewport_rect.width, viewport_rect.height)
            if self.last_size != current_size or self.surface is None:
                self.surface = pygame.Surface(current_size, pygame.SRCALPHA)
                self.last_size = current_size

            self.surface.fill((0, 0, 0, 0))
            pygame.draw.rect(self.surface, color, self.surface.get_rect())

            # Intensidade baseada no progresso
            progress = day_night_state.get_progress()

            if progress < 0.2:
                alpha_factor = progress / 0.2
            elif progress > 0.8:
                alpha_factor = (1.0 - progress) / 0.2
            else:
                alpha_factor = 1.0

            final_alpha = int(color[3] * alpha_factor)
            self.surface.set_alpha(final_alpha)

            screen.blit(self.surface, (viewport_rect.x, viewport_rect.y))

    def clear(self):
        """Limpa o cache"""
        self.surface = None
        self.last_size = None
        self._star_surface = None
        self._moon_surface = None
        self._star_cache.clear()