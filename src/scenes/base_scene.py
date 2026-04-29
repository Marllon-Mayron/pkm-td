"""
Classe base para todas as cenas
"""
from abc import ABC, abstractmethod
import pygame

class BaseScene(ABC):
    def __init__(self, game):
        self.game = game
        self.screen_manager = game.screen_manager
        self.camera = game.camera if hasattr(game, 'camera') else None

        # Estado da cena
        self.paused = False

        # Fontes básicas (podem ser sobrescritas nas subclasses)
        self.font_large = pygame.font.Font(None, 48)
        self.font_medium = pygame.font.Font(None, 32)
        self.font_small = pygame.font.Font(None, 24)

    @abstractmethod
    def handle_event(self, event):
        """Processa eventos específicos da cena"""
        pass

    @abstractmethod
    def fixed_update(self, dt):
        """Update fixo para lógica"""
        pass

    def on_resize(self):
        pass

    @abstractmethod
    def render(self, screen):
        """Renderiza a cena diretamente na tela"""
        pass

    def enter(self):
        """Chamado quando a cena é ativada"""
        pass

    def exit(self):
        """Chamado quando a cena é desativada"""
        pass

    def toggle_pause(self):
        """Alterna pausa da cena"""
        self.paused = not self.paused
        if self.paused:
            print("Jogo pausado")
        else:
            print("Jogo continuando")