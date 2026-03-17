# src/scenes/game_scene/components/renderer/target_item_renderer.py

import pygame


class TargetItemRenderer:
    """Renderiza os itens alvo (opcional - podemos usar o próprio manager)"""

    def __init__(self):
        pass

    def render(self, screen, camera, screen_manager, items):
        """Renderiza a lista de itens"""
        for item in items:
            # Converte coordenadas do mundo para tela
            screen_x, screen_y = screen_manager.world_to_screen(item.x, item.y, camera)

            # Renderiza o item
            item.render(screen, camera)

            # Se estiver em debug, mostra informações
            if hasattr(self, 'show_debug') and self.show_debug:
                font = pygame.font.Font(None, 14)
                text = font.render(f"{item.item_name} x{item.quantity}", True, (255, 255, 255))
                screen.blit(text, (screen_x, screen_y - 20))