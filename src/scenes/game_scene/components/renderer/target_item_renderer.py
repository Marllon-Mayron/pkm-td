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
        """Renderiza um único item"""

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

        # Converte para tela
        screen_x, screen_y = render_context.world_to_screen(world_x, world_y, camera, screen_manager)
        scale = render_context.get_scale(camera, screen_manager)
        sprite_size = max(8, int(16 * scale))
        half_size = sprite_size // 2

        # Desenha o item
        if item.sprite:
            scaled = pygame.transform.scale(item.sprite, (sprite_size, sprite_size))
            screen.blit(scaled, (screen_x - half_size, screen_y - half_size))
        else:
            # Placeholder
            colors = [(255, 215, 0), (255, 0, 0), (0, 255, 0), (0, 0, 255)]
            color = colors[(item.item_id - 1) % len(colors)]
            pygame.draw.rect(screen, color, (screen_x - half_size, screen_y - half_size, sprite_size, sprite_size))

        # Barra de progresso
        if item.carried_by:
            bar_width = sprite_size
            bar_height = max(2, int(3 * scale))
            bar_x = screen_x - half_size
            bar_y = screen_y - half_size - bar_height - 2

            pygame.draw.rect(screen, (50, 50, 50), (bar_x, bar_y, bar_width, bar_height))
            progress_width = (item.capture_progress / 100) * bar_width
            if progress_width > 0:
                color = (255, 255, 0) if item.capture_progress < 50 else (255, 100, 0)
                pygame.draw.rect(screen, color, (bar_x, bar_y, progress_width, bar_height))