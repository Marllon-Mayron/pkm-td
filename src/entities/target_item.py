# src/entities/target_item.py

import pygame
from src.entities.base import Entity


class TargetItem(Entity):
    """Item que precisa ser protegido durante a wave"""

    def __init__(self, x, y, item_id, name="Item", sprite=None, quantity=1):
        super().__init__(x, y, 16, 16, sprite)  # Tamanho fixo 16x16

        self.item_id = item_id
        self.item_name = name
        self.quantity = quantity
        self.is_protected = True  # Se ainda está protegido
        self.carried_by = None  # Pokémon que está carregando
        self.capture_progress = 0  # Progresso de captura (0-100)
        self.capture_rate = 10  # Quanto aumenta por frame

        # Referência ao screen_manager (será setado pelo jogo)
        self.screen_manager = None

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
        """Atualiza o progresso de captura (chamado pelo Pokémon)"""
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
        """Renderiza o item com indicadores visuais"""
        if not self.sprite:
            return

        # CONVERSÃO CORRETA para coordenadas de tela
        if camera and self.screen_manager:
            # Usa o mesmo sistema que o Pokémon
            screen_x, screen_y = self.screen_manager.world_to_screen(self.x, self.y, camera)

            # Calcula escala baseada no zoom
            zoom_scale = camera.zoom * self.screen_manager.render_scale
            size = max(1, int(16 * zoom_scale))

            # Redimensiona sprite se necessário
            if self.sprite.get_width() != size:
                sprite_to_draw = pygame.transform.scale(self.sprite, (size, size))
            else:
                sprite_to_draw = self.sprite
        else:
            # Fallback para coordenadas diretas (sem câmera)
            screen_x = self.x
            screen_y = self.y
            sprite_to_draw = self.sprite
            size = 16

        # Desenha o sprite base
        screen.blit(sprite_to_draw, (screen_x, screen_y))

        # Se está sendo carregado, mostra barra de progresso
        if self.carried_by:
            # Fundo da barra
            bar_width = 20
            bar_height = 3
            bar_x = screen_x - 2
            bar_y = screen_y - 8

            pygame.draw.rect(screen, (50, 50, 50),
                             (bar_x, bar_y, bar_width, bar_height))

            # Progresso
            progress_width = (self.capture_progress / 100) * bar_width
            if self.capture_progress < 50:
                color = (255, 255, 0)  # Amarelo
            else:
                color = (255, 100, 0)  # Laranja -> Vermelho

            pygame.draw.rect(screen, color,
                             (bar_x, bar_y, progress_width, bar_height))

        # Se está protegido, mostra um brilho/contorno
        if self.is_protected and not self.carried_by:
            # Círculo pulsante
            pulse = abs(pygame.time.get_ticks() % 1000 - 500) / 500
            alpha = int(100 + 100 * pulse)
            glow_surf = pygame.Surface((size + 4, size + 4), pygame.SRCALPHA)
            pygame.draw.circle(glow_surf, (0, 255, 0, alpha),
                               (size // 2 + 2, size // 2 + 2), size // 2 + 4)
            screen.blit(glow_surf, (screen_x - 2, screen_y - 2))

        # Quantidade (se maior que 1)
        if self.quantity > 1:
            font = pygame.font.Font(None, max(12, size // 2))
            text = font.render(f"x{self.quantity}", True, (255, 255, 255))
            text_x = screen_x + size - text.get_width() - 2
            text_y = screen_y - text.get_height() - 2
            screen.blit(text, (text_x, text_y))