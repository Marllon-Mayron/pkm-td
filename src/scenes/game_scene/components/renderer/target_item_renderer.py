# src/scenes/game_scene/components/renderer/target_item_renderer.py

"""
Renderizador de itens alvo - COM VARIAÇÃO VISUAL DE POSIÇÃO E ROTAÇÃO
"""
import pygame
import random
import math
from src.core.render_context import render_context


class TargetItemRenderer:
    """Renderiza os itens alvo com variações visuais"""

    def __init__(self):
        self.show_debug = False

    def render(self, screen, camera, screen_manager, items):
        """Renderiza a lista de itens"""
        for item in items:
            self.render_item(screen, camera, screen_manager, item)

    def render_item(self, screen, camera, screen_manager, item):
        """Renderiza um único item com variação visual"""
        # Obtém a posição de renderização (com offset visual)
        if hasattr(item, 'get_render_position'):
            world_x, world_y = item.get_render_position()
        else:
            # Fallback para compatibilidade
            world_x, world_y = item.get_capture_position()

        # Converte para coordenadas de tela
        screen_x, screen_y = screen_manager.world_to_screen(world_x, world_y, camera)

        # Escala do sprite baseada no zoom
        scale = camera.zoom * screen_manager.render_scale if camera else screen_manager.render_scale
        sprite_size = max(8, int(16 * scale))
        half_size = sprite_size // 2

        # Renderiza o item (com rotação)
        if item.sprite:
            # Aplica rotação (usa a rotação do item)
            rotation = item.rotation if hasattr(item, 'rotation') else 0

            if rotation != 0:
                # Rotaciona o sprite
                rotated_sprite = pygame.transform.rotate(item.sprite, rotation)
                # Escala após rotação
                scaled = pygame.transform.scale(rotated_sprite, (sprite_size, sprite_size))
                rotated_rect = scaled.get_rect()
                rotated_rect.center = (screen_x, screen_y)
                screen.blit(scaled, rotated_rect)
            else:
                # Sem rotação, apenas escala
                scaled = pygame.transform.scale(item.sprite, (sprite_size, sprite_size))
                screen.blit(scaled, (screen_x - half_size, screen_y - half_size))

        # Debug: mostra hitbox real (sem offset)
        if self.show_debug:
            # Pega a posição real da hitbox
            real_x, real_y = item.get_capture_position()
            real_screen_x, real_screen_y = screen_manager.world_to_screen(real_x, real_y, camera)

            # Desenha um círculo na posição real (hitbox)
            pygame.draw.circle(screen, (255, 0, 0), (real_screen_x, real_screen_y), 5, 1)

            # Desenha um círculo na posição renderizada
            pygame.draw.circle(screen, (0, 255, 0), (screen_x, screen_y), 5, 1)

            # Desenha linha conectando hitbox à renderização
            pygame.draw.line(screen, (255, 255, 0), (real_screen_x, real_screen_y), (screen_x, screen_y), 1)

            # Desenha o range de captura
            capture_range_px = item.capture_rate * scale if hasattr(item, 'capture_rate') else 20
            pygame.draw.circle(screen, (255, 255, 0), (real_screen_x, real_screen_y), int(capture_range_px), 1)