# src/scenes/game_scene/components/overlays/base_overlay.py

from abc import ABC, abstractmethod
import pygame


class BaseOverlay(ABC):
    """Classe base para todos os overlays do jogo"""

    def __init__(self, game_scene):
        self.game_scene = game_scene
        self.game = game_scene.game
        self.screen_manager = game_scene.screen_manager
        self.camera = game_scene.camera

        # Timer para transição automática
        self.timer = 0
        self.delay = 3.0
        self.active = False

    @abstractmethod
    def handle_event(self, event):
        """Processa eventos do overlay"""
        pass

    @abstractmethod
    def update(self, dt):
        """Atualiza lógica do overlay"""
        pass

    @abstractmethod
    def render(self, screen):
        """Renderiza o overlay"""
        pass

    def get_viewport_rect(self):
        """Retorna o retângulo do viewport"""
        return pygame.Rect(
            self.screen_manager.viewport_x,
            self.screen_manager.viewport_y,
            self.screen_manager.viewport_width,
            self.screen_manager.viewport_height
        )

    def create_overlay_surface(self, alpha=200):
        """Cria uma superfície de overlay escura"""
        viewport = self.get_viewport_rect()
        overlay = pygame.Surface((viewport.width, viewport.height))
        overlay.set_alpha(alpha)
        overlay.fill((0, 0, 0))
        return overlay, viewport