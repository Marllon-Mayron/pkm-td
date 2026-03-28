# src/scenes/game_scene/components/renderer/target_item_renderer.py

"""
Renderizador de itens alvo - SIMPLIFICADO
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
        """Renderiza um único item - USANDO MESMO CÁLCULO"""
        # Determina posição no mundo
        if item.carried_by:
            world_x = item.current_x
            world_y = item.current_y
        else:
            if item.was_carried:
                world_x = item.current_x
                world_y = item.current_y
            else:
                world_x = item.base_x + item.visual_offset_x
                world_y = item.base_y + item.visual_offset_y

        # Usa o mesmo método world_to_screen
        screen_x, screen_y = render_context.world_to_screen(world_x, world_y, camera, screen_manager)
        scale = render_context.get_scale(camera, screen_manager)
        sprite_size = max(8, int(16 * scale))
        half_size = sprite_size // 2

        # Renderiza o item
        if item.sprite:
            scaled = pygame.transform.scale(item.sprite, (sprite_size, sprite_size))
            screen.blit(scaled, (screen_x - half_size, screen_y - half_size))