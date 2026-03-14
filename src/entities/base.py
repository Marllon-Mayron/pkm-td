# src/entities/base.py
import pygame
from abc import ABC, abstractmethod


class Entity(ABC):
    def __init__(self, x, y, width, height, sprite=None):
        self.x = x
        self.y = y
        self.width = width
        self.height = height
        self.sprite = sprite
        self.rect = pygame.Rect(x, y, width, height)

    def update(self, dt):
        """Atualiza a entidade"""
        pass

    def render(self, screen, camera=None):
        """Renderiza a entidade"""
        if self.sprite:
            screen_x = self.x - (camera.x if camera else 0)
            screen_y = self.y - (camera.y if camera else 0)
            screen.blit(self.sprite, (screen_x, screen_y))

    @staticmethod
    def check_collision(entity1, entity2):
        """Verifica colisão entre duas entidades"""
        return entity1.rect.colliderect(entity2.rect)