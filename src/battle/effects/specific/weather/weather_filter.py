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

        # Obtém a cor do filtro baseado no tipo de clima
        color = self._get_filter_color(weather_state)

        if color[3] <= 0:
            print(f"[WEATHER_FILTER] Opacidade zero, ignorando")
            return

        # Cria ou recria a superfície se o tamanho mudou
        current_size = (viewport_rect.width, viewport_rect.height)
        if self.last_size != current_size or self.surface is None:
            self.surface = pygame.Surface(current_size, pygame.SRCALPHA)
            self.last_size = current_size
            print(f"[WEATHER_FILTER] Superfície criada: {current_size}")

        # Limpa a superfície
        self.surface.fill((0, 0, 0, 0))

        # Desenha o filtro
        pygame.draw.rect(self.surface, color, self.surface.get_rect())

        # ===== CORREÇÃO: Para clima base, sempre usa opacidade total =====
        if weather_state.is_base_weather:
            # Clima base: opacidade total SEM fade
            final_alpha = color[3]
        else:
            # Clima temporário: com fade in/out
            progress = weather_state.get_progress()

            if progress < 0.2:
                alpha_factor = progress / 0.2
            elif progress > 0.8:
                alpha_factor = (1.0 - progress) / 0.2
            else:
                alpha_factor = 1.0

            final_alpha = int(color[3] * alpha_factor)

        self.surface.set_alpha(final_alpha)

        # Renderiza na posição da viewport
        screen.blit(self.surface, (viewport_rect.x, viewport_rect.y))

    def _get_filter_color(self, weather_state) -> tuple:
        """
        Retorna a cor do filtro com opacidade baseado no tipo de clima.
        """
        weather_type = weather_state.type.value

        if weather_type == "sandstorm":
            return (194, 178, 128, 110)  # Marrom/areia
        elif weather_type == "rain":
            return (100, 100, 200, 110)  # Azul (chuva)
        elif weather_type == "sunny":
            return (255, 200, 100, 110)  # Amarelo (sol)
        else:
            print(f"[WEATHER_FILTER] Tipo não reconhecido: {weather_type}")
            return (255, 0, 0, 110)  # Vermelho (fallback)

    def clear(self):
        """Limpa o cache"""
        self.surface = None
        self.last_size = None