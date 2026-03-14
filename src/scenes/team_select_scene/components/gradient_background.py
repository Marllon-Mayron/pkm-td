import pygame
from src.scenes.team_select_scene.utils.constants import COLORS


class GradientBackground:
    def __init__(self, screen_manager):
        self.screen_manager = screen_manager

    def render(self, screen):
        for i in range(self.screen_manager.window_height):
            value = int(COLORS['BACKGROUND']['GRADIENT_START'] +
                       (i / self.screen_manager.window_height) *
                       (COLORS['BACKGROUND']['GRADIENT_END'] - COLORS['BACKGROUND']['GRADIENT_START']))
            color = (value, value, value + 3)
            pygame.draw.line(screen, color, (0, i),
                           (self.screen_manager.window_width, i))