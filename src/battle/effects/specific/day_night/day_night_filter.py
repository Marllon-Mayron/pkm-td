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

        # ===== CAVERNA =====
        # Apenas o filtro escuro, o fade é controlado pela opacidade da cor

        screen.blit(filter_surface, (viewport_rect.x, viewport_rect.y))

    def clear(self):
        """Limpa o cache"""
        self.surface = None
        self.last_size = None