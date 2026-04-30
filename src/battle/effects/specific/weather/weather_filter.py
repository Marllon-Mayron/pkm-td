# src/battle/effects/specific/weather/weather_filter.py

import pygame


class WeatherFilter:
    """
    Filtro visual para o clima.
    Renderizado sobre toda a tela.
    """

    def __init__(self):
        self.surface = None
        self.last_size = None

    def render(self, screen, weather_state, viewport_rect):
        """
        Renderiza o filtro de clima sobre a tela.

        Args:
            screen: Superfície da tela
            weather_state: Estado do clima atual (ou None)
            viewport_rect: Retângulo da viewport (onde o filtro deve aparecer)
        """
        if not weather_state or not weather_state.active:
            return

        # Obtém a cor do filtro
        color = weather_state.get_filter_color()
        if color[3] <= 0:
            return

        # Cria ou recria a superfície se o tamanho mudou
        current_size = (viewport_rect.width, viewport_rect.height)
        if self.last_size != current_size or self.surface is None:
            self.surface = pygame.Surface(current_size, pygame.SRCALPHA)
            self.last_size = current_size

        # Limpa a superfície
        self.surface.fill((0, 0, 0, 0))

        # Desenha o filtro
        pygame.draw.rect(self.surface, color, self.surface.get_rect())

        # Intensidade baseada no progresso (fade in/out)
        progress = weather_state.get_progress()

        # Fade in no início, fade out no final
        if progress < 0.2:
            alpha_factor = progress / 0.2
        elif progress > 0.8:
            alpha_factor = (1.0 - progress) / 0.2
        else:
            alpha_factor = 1.0

        # Aplica a opacidade final
        final_alpha = int(color[3] * alpha_factor)
        self.surface.set_alpha(final_alpha)

        # Renderiza na posição da viewport
        screen.blit(self.surface, (viewport_rect.x, viewport_rect.y))

    def clear(self):
        """Limpa o cache"""
        self.surface = None
        self.last_size = None