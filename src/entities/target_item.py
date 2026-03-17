# src/entities/target_item.py

import pygame
import os
from src.entities.base import Entity
from src.data.item_catalog import item_catalog


class TargetItem(Entity):
    """Item que precisa ser protegido durante a wave"""

    def __init__(self, x, y, item_id):
        super().__init__(x, y, 16, 16, None)  # Hitbox continua 16x16

        self.item_id = item_id

        # Carrega informações do catálogo
        item_info = item_catalog.get_item(item_id)
        self.item_name = item_info["name"]
        self.sprite_path = item_info["sprite"]

        self.is_protected = True
        self.carried_by = None
        self.capture_progress = 0
        self.capture_rate = 10

        # Carrega sprite (mantém tamanho original)
        self.sprite = None
        self.original_sprite_size = 32  # Tamanho original do sprite
        self.load_sprite()

        # Referência ao screen_manager (será setado pelo jogo)
        self.screen_manager = None

    def load_sprite(self):
        """Carrega o sprite do item mantendo tamanho original"""
        if self.sprite_path and os.path.exists(self.sprite_path):
            try:
                # Carrega o sprite no tamanho original
                self.sprite = pygame.image.load(self.sprite_path).convert_alpha()
                print(
                    f"✓ Sprite do item {self.item_name} carregado ({self.sprite.get_width()}x{self.sprite.get_height()})")
            except Exception as e:
                print(f"✗ Erro ao carregar sprite do item {self.sprite_path}: {e}")
                self.sprite = None
        else:
            print(f"✗ Sprite do item {self.item_name} não encontrado: {self.sprite_path}")
            self.sprite = None

    def update(self, dt):
        """Atualiza lógica do item"""
        if self.carried_by:
            # Item sendo carregado - segue o Pokémon
            self.x = self.carried_by.x
            self.y = self.carried_by.y
            self.rect.x = self.x
            self.rect.y = self.y

    def start_capture(self, pokemon):
        """Inicia o processo de captura por um Pokémon"""
        if not self.carried_by and self.is_protected:
            self.carried_by = pokemon
            pokemon.is_carrying = self
            print(f"{pokemon.name} começou a carregar {self.item_name}")

    def update_capture(self, dt):
        """Atualiza o progresso de captura"""
        if self.carried_by:
            self.capture_progress += self.capture_rate * dt
            if self.capture_progress >= 100:
                self.complete_capture()

    def complete_capture(self):
        """Completa a captura do item"""
        if self.carried_by:
            self.is_protected = False
            self.carried_by.is_carrying = None
            self.carried_by = None
            print(f"{self.item_name} foi levado!")

    def render(self, screen, camera=None):
        """Renderiza o item com sprite em tamanho reduzido (16x16)"""
        # Determina posição na tela
        if camera and self.screen_manager:
            # Usa a posição do tile (canto superior esquerdo)
            screen_x, screen_y = self.screen_manager.world_to_screen(self.x, self.y, camera)
            zoom_scale = camera.zoom * self.screen_manager.render_scale

            # Tamanho do sprite na tela - AGORA METADE (16 em vez de 32)
            sprite_size = max(1, int(16 * zoom_scale))  # 16 é metade de 32
        else:
            screen_x = self.x
            screen_y = self.y
            sprite_size = 16  # Tamanho fixo 16x16 sem zoom

        # Se tem sprite, usa ele
        if self.sprite:
            sprite_to_draw = pygame.transform.scale(self.sprite, (sprite_size, sprite_size))

            screen.blit(sprite_to_draw, (screen_x, screen_y))
        else:
            # Fallback: desenha placeholder no tamanho do grid
            colors = [(255, 215, 0), (255, 0, 0), (0, 255, 0), (0, 0, 255)]
            color = colors[(self.item_id - 1) % len(colors)]

            pygame.draw.rect(screen, color, (screen_x, screen_y, sprite_size, sprite_size))
            font = pygame.font.Font(None, sprite_size // 2)
            text = font.render(str(self.item_id), True, (255, 255, 255))
            text_rect = text.get_rect(center=(screen_x + sprite_size // 2, screen_y + sprite_size // 2))
            screen.blit(text, text_rect)

        # Barra de progresso se está sendo carregado
        if self.carried_by:
            bar_width = sprite_size  # Barra do tamanho do sprite
            bar_height = 4
            bar_x = screen_x
            bar_y = screen_y - 10

            pygame.draw.rect(screen, (50, 50, 50),
                             (bar_x, bar_y, bar_width, bar_height))

            progress_width = (self.capture_progress / 100) * bar_width
            if self.capture_progress < 50:
                color = (255, 255, 0)
            else:
                color = (255, 100, 0)

            pygame.draw.rect(screen, color,
                             (bar_x, bar_y, progress_width, bar_height))