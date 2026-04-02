# src/scenes/game_scene/components/renderer/target_item_renderer.py

"""
Renderizador de itens alvo - COM VARIAÇÃO VISUAL
"""
import pygame
from src.core.render_context import render_context


class TargetItemRenderer:
    """Renderiza os itens alvo"""

    def __init__(self):
        self.show_debug = False

    def render(self, screen, camera, screen_manager, items):
        """Renderiza a lista de itens"""
        for item in items:
            self.render_item(screen, camera, screen_manager, item)

    def render_item(self, screen, camera, screen_manager, item):
        """Renderiza um único item"""
        # ===== CORREÇÃO: Usa get_capture_position para obter a posição correta =====
        world_x, world_y = item.get_capture_position()

        # Converte para coordenadas de tela
        screen_x, screen_y = screen_manager.world_to_screen(world_x, world_y, camera)

        # Escala do sprite baseada no zoom
        scale = camera.zoom * screen_manager.render_scale if camera else screen_manager.render_scale
        sprite_size = max(8, int(16 * scale))
        half_size = sprite_size // 2

        # Renderiza o item (com rotação se tiver)
        if item.sprite:
            scaled = pygame.transform.scale(item.sprite, (sprite_size, sprite_size))

            # Aplica rotação se houver
            if hasattr(item, 'rotation') and item.rotation != 0:
                scaled = pygame.transform.rotate(scaled, item.rotation)
                rotated_rect = scaled.get_rect()
                rotated_rect.center = (screen_x, screen_y)
                screen.blit(scaled, rotated_rect)
            else:
                screen.blit(scaled, (screen_x - half_size, screen_y - half_size))

        # Debug: mostra hitbox
        if self.show_debug:
            # Desenha um círculo no centro do item
            pygame.draw.circle(screen, (255, 0, 0), (screen_x, screen_y), 5, 1)
            # Desenha o range de captura
            capture_range_px = item.capture_rate * scale if hasattr(item, 'capture_rate') else 20
            pygame.draw.circle(screen, (255, 255, 0), (screen_x, screen_y), int(capture_range_px), 1)