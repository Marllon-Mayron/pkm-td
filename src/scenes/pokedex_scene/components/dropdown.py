# src/scenes/pokedex_scene/components/dropdown.py

import pygame
from src.scenes.pokedex_scene.utils.constants import COLORS


class Dropdown:
    """Dropdown reutilizável para filtros da Pokédex"""

    def __init__(self, x, y, width, height, options, default_key=None):
        self.rect = pygame.Rect(x, y, width, height)
        self.options = options  # lista de dicts {'key': ..., 'label': ...}
        self.selected_key = (
            default_key if default_key is not None
            else (options[0]['key'] if options else None)
        )
        self.is_open = False
        self.hovered = False
        self.hovered_option_index = -1
        self.option_rects = []
        self.on_change = None  # callback(key)

    # ===== GETTERS =====
    def get_selected_key(self):
        return self.selected_key

    def get_selected_label(self):
        for opt in self.options:
            if opt['key'] == self.selected_key:
                return opt['label']
        return ""

    def set_selected(self, key):
        if key != self.selected_key:
            self.selected_key = key
            if self.on_change:
                self.on_change(key)

    # ===== CONTROLE =====
    def close(self):
        self.is_open = False
        self.hovered_option_index = -1

    def _update_option_rects(self):
        self.option_rects = []
        for i in range(len(self.options)):
            opt_rect = pygame.Rect(
                self.rect.x,
                self.rect.bottom + i * self.rect.height,
                self.rect.width,
                self.rect.height,
            )
            self.option_rects.append(opt_rect)

    def handle_event(self, event):
        """
        Retorna True se consumiu o evento.
        Quando aberto e clique fora: fecha e NÃO consome (deixa propagar).
        """
        if event.type == pygame.MOUSEMOTION:
            self.hovered = self.rect.collidepoint(event.pos)
            if self.is_open:
                self.hovered_option_index = -1
                for i, r in enumerate(self.option_rects):
                    if r.collidepoint(event.pos):
                        self.hovered_option_index = i
                        break
            return False

        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            if self.is_open:
                self._update_option_rects()

                # Clique em uma opção
                for i, r in enumerate(self.option_rects):
                    if r.collidepoint(event.pos):
                        new_key = self.options[i]['key']
                        self.close()
                        if new_key != self.selected_key:
                            self.selected_key = new_key
                            if self.on_change:
                                self.on_change(new_key)
                        return True

                # Clique no header (aberto) -> só fecha
                if self.rect.collidepoint(event.pos):
                    self.close()
                    return True

                # Clique fora -> fecha e deixa propagar
                self.close()
                return False
            else:
                # Abrir
                if self.rect.collidepoint(event.pos):
                    self.is_open = True
                    self._update_option_rects()
                    return True

        return False

    # ===== RENDER =====
    def render_header(self, screen, font):
        if self.is_open:
            bg_color = COLORS['bg_list_item_hover']
            border_color = COLORS['text_accent']
        elif self.hovered:
            bg_color = COLORS['bg_list_item_hover']
            border_color = COLORS['border_light']
        else:
            bg_color = COLORS['bg_list_item']
            border_color = COLORS['border']

        pygame.draw.rect(screen, bg_color, self.rect, border_radius=6)
        pygame.draw.rect(screen, border_color, self.rect, 2, border_radius=6)

        label = self.get_selected_label()
        text_surf = font.render(label, True, COLORS['text_primary'])
        text_y = self.rect.y + (self.rect.height - text_surf.get_height()) // 2
        screen.blit(text_surf, (self.rect.x + 12, text_y))

        # Seta
        arrow_x = self.rect.right - 16
        arrow_y = self.rect.centery
        if self.is_open:
            points = [(arrow_x - 5, arrow_y + 3),
                      (arrow_x + 5, arrow_y + 3),
                      (arrow_x, arrow_y - 4)]
        else:
            points = [(arrow_x - 5, arrow_y - 3),
                      (arrow_x + 5, arrow_y - 3),
                      (arrow_x, arrow_y + 4)]
        pygame.draw.polygon(screen, COLORS['text_secondary'], points)

    def render_options(self, screen, font):
        """Deve ser chamado por último para ficar acima de tudo."""
        if not self.is_open:
            return

        self._update_option_rects()
        total_height = len(self.options) * self.rect.height

        # Sombra
        shadow = pygame.Surface(
            (self.rect.width + 6, total_height + 6), pygame.SRCALPHA
        )
        shadow.fill((0, 0, 0, 130))
        screen.blit(shadow, (self.rect.x + 3, self.rect.bottom + 3))

        for i, opt_rect in enumerate(self.option_rects):
            opt = self.options[i]

            if i == self.hovered_option_index:
                bg = COLORS['bg_list_item_hover']
            elif opt['key'] == self.selected_key:
                bg = COLORS['bg_list_item_selected']
            else:
                bg = COLORS['bg_secondary']

            pygame.draw.rect(screen, bg, opt_rect)
            pygame.draw.rect(screen, COLORS['border'], opt_rect, 1)

            color = (COLORS['text_primary']
                     if opt['key'] == self.selected_key
                     else COLORS['text_secondary'])
            text_surf = font.render(opt['label'], True, color)
            text_y = opt_rect.y + (opt_rect.height - text_surf.get_height()) // 2
            screen.blit(text_surf, (opt_rect.x + 12, text_y))