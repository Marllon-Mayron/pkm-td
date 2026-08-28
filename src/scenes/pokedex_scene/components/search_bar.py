# src/scenes/pokedex_scene/components/search_bar.py

import pygame
from src.scenes.pokedex_scene.utils.constants import COLORS


class SearchBar:
    """Barra de pesquisa da Pokédex"""

    def __init__(self, x, y, width, height):
        self.rect = pygame.Rect(x, y, width, height)
        self.text = ""
        self.active = False
        self.hovered = False
        self.cursor_visible = True
        self.cursor_timer = 0

    def handle_event(self, event):
        if event.type == pygame.MOUSEBUTTONDOWN:
            self.active = self.rect.collidepoint(event.pos)
            return self.active

        elif event.type == pygame.MOUSEMOTION:
            self.hovered = self.rect.collidepoint(event.pos)

        if self.active and event.type == pygame.KEYDOWN:
            if event.key == pygame.K_ESCAPE:
                self.active = False
                return False
            elif event.key == pygame.K_BACKSPACE:
                self.text = self.text[:-1]
            elif event.key == pygame.K_RETURN:
                self.active = False
                return True
            else:
                char = event.unicode
                if char.isalnum() or char == " " or char == "-":
                    if len(self.text) < 30:
                        self.text += char

        return None

    def update(self, dt):
        self.cursor_timer += dt
        if self.cursor_timer > 0.5:
            self.cursor_timer = 0
            self.cursor_visible = not self.cursor_visible

    def render(self, screen, font):
        # Fundo
        if self.active:
            bg_color = (45, 48, 55)
            border_color = COLORS['text_accent']
        elif self.hovered:
            bg_color = (40, 42, 50)
            border_color = COLORS['border_light']
        else:
            bg_color = COLORS['bg_list_item']
            border_color = COLORS['border']

        pygame.draw.rect(screen, bg_color, self.rect, border_radius=6)
        pygame.draw.rect(screen, border_color, self.rect, 2, border_radius=6)

        # Texto
        display_text = self.text if self.text else "Buscar Pokemon..."
        text_color = COLORS['text_primary'] if self.text else COLORS['text_secondary']
        text_surface = font.render(display_text, True, text_color)

        max_width = self.rect.width - 50
        if text_surface.get_width() > max_width:
            while text_surface.get_width() > max_width and display_text:
                display_text = display_text[:-1]
                text_surface = font.render(display_text + "...", True, text_color)

        screen.blit(text_surface, (self.rect.x + 35, self.rect.y + (self.rect.height - text_surface.get_height()) // 2))

        # Cursor
        if self.active and self.cursor_visible:
            cursor_x = self.rect.x + 35 + text_surface.get_width()
            cursor_y = self.rect.y + 6
            cursor_height = self.rect.height - 12
            pygame.draw.line(screen, COLORS['text_accent'],
                           (cursor_x, cursor_y), (cursor_x, cursor_y + cursor_height), 2)

        # Botão limpar
        if self.text:
            clear_rect = pygame.Rect(self.rect.right - 28, self.rect.y + 6, 20, self.rect.height - 12)
            pygame.draw.circle(screen, (70, 70, 80), clear_rect.center, 10)
            clear_font = pygame.font.Font(None, 14)
            clear_text = clear_font.render("X", True, COLORS['text_secondary'])
            clear_center = clear_text.get_rect(center=clear_rect.center)
            screen.blit(clear_text, clear_center)

    def get_search_text(self):
        return self.text.lower().strip()