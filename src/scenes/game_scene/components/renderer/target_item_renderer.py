# src/scenes/game_scene/components/renderer/target_item_renderer.py

import pygame
import math


class TargetItemRenderer:
    """Renderiza os itens alvo com variação visual"""

    def __init__(self):
        self.show_debug = False

    def render(self, screen, camera, screen_manager, items):
        """Renderiza a lista de itens"""
        for item in items:
            self.render_item(screen, camera, screen_manager, item)

    def render_item(self, screen, camera, screen_manager, item):
        """Renderiza um único item com sprite em tamanho reduzido (16x16) com variação visual"""

        # Determina posição na tela com offset visual
        if camera and screen_manager:
            if item.carried_by:
                # Se está sendo carregado, usa posição atual
                world_x = item.x
                world_y = item.y
            else:
                # Se está no chão, usa posição base com offset visual
                world_x = item.base_x + item.visual_offset_x
                world_y = item.base_y + item.visual_offset_y

            screen_x, screen_y = screen_manager.world_to_screen(world_x, world_y, camera)
            zoom_scale = camera.zoom * screen_manager.render_scale

            # Tamanho do sprite na tela
            sprite_size = max(1, int(16 * zoom_scale))
        else:
            # Sem câmera, usa posição base com offset
            if item.carried_by:
                screen_x = item.x
                screen_y = item.y
            else:
                screen_x = item.base_x + item.visual_offset_x
                screen_y = item.base_y + item.visual_offset_y
            sprite_size = 16

        # Se tem sprite, usa ele
        if item.sprite:
            # Escala o sprite
            sprite_scaled = pygame.transform.scale(item.sprite, (sprite_size, sprite_size))

            # Aplica rotação
            if item.rotation != 0:
                sprite_to_draw = pygame.transform.rotate(sprite_scaled, item.rotation)
                # Ajusta posição para centralizar após rotação
                screen_x -= (sprite_to_draw.get_width() - sprite_scaled.get_width()) / 2
                screen_y -= (sprite_to_draw.get_height() - sprite_scaled.get_height()) / 2
            else:
                sprite_to_draw = sprite_scaled

            screen.blit(sprite_to_draw, (screen_x, screen_y))
        else:
            # Fallback: desenha placeholder no tamanho do grid
            colors = [(255, 215, 0), (255, 0, 0), (0, 255, 0), (0, 0, 255)]
            color = colors[(item.item_id - 1) % len(colors)]

            # Cria uma superfície para rotação
            if item.rotation != 0:
                placeholder = pygame.Surface((sprite_size, sprite_size), pygame.SRCALPHA)
                pygame.draw.rect(placeholder, color, (0, 0, sprite_size, sprite_size))
                rotated = pygame.transform.rotate(placeholder, item.rotation)
                screen.blit(rotated, (screen_x - (rotated.get_width() - sprite_size) / 2,
                                      screen_y - (rotated.get_height() - sprite_size) / 2))

                # Desenha o texto no placeholder original (será rotacionado junto)
                font = pygame.font.Font(None, sprite_size // 2)
                text = font.render(str(item.item_id), True, (255, 255, 255))
                text_surf = pygame.Surface((sprite_size, sprite_size), pygame.SRCALPHA)
                text_rect = text.get_rect(center=(sprite_size // 2, sprite_size // 2))
                text_surf.blit(text, text_rect)
                text_rotated = pygame.transform.rotate(text_surf, item.rotation)
                screen.blit(text_rotated, (screen_x - (text_rotated.get_width() - sprite_size) / 2,
                                           screen_y - (text_rotated.get_height() - sprite_size) / 2))
            else:
                pygame.draw.rect(screen, color, (screen_x, screen_y, sprite_size, sprite_size))
                font = pygame.font.Font(None, sprite_size // 2)
                text = font.render(str(item.item_id), True, (255, 255, 255))
                text_rect = text.get_rect(center=(screen_x + sprite_size // 2, screen_y + sprite_size // 2))
                screen.blit(text, text_rect)

        # Barra de progresso se está sendo carregado
        if item.carried_by:
            bar_width = sprite_size  # Barra do tamanho do sprite
            bar_height = 4
            bar_x = screen_x
            bar_y = screen_y - 10

            pygame.draw.rect(screen, (50, 50, 50),
                             (bar_x, bar_y, bar_width, bar_height))

            progress_width = (item.capture_progress / 100) * bar_width
            if item.capture_progress < 50:
                color = (255, 255, 0)
            else:
                color = (255, 100, 0)

            pygame.draw.rect(screen, color,
                             (bar_x, bar_y, progress_width, bar_height))

        # Se estiver em debug, mostra informações
        if self.show_debug:
            font = pygame.font.Font(None, 14)
            # Para debug, usa a posição real (hitbox)
            debug_x, debug_y = screen_manager.world_to_screen(item.base_x, item.base_y, camera)
            text = font.render(f"{item.item_name}", True, (255, 255, 255))
            screen.blit(text, (debug_x, debug_y - 20))

            # Desenha um ponto vermelho na posição da hitbox
            pygame.draw.circle(screen, (255, 0, 0), (int(debug_x + 8), int(debug_y + 8)), 3)