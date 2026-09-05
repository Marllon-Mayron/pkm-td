# src/scenes/team_select_scene/components/pokemon_filters.py

import pygame
from src.scenes.team_select_scene.utils.constants import COLORS, LAYOUT


class Dropdown:
    """Componente de dropdown reutilizável"""

    def __init__(self, x, y, width, height, options, default_index=0, label=""):
        self.rect = pygame.Rect(x, y, width, height)
        self.options = options
        self.selected_index = default_index
        self.is_open = False
        self.label = label
        self.hovered_option = -1

    def get_selected(self):
        return self.options[self.selected_index] if self.options else None

    def get_selected_value(self):
        if not self.options:
            return None
        return self.options[self.selected_index].get('value')

    def get_selected_label(self):
        if not self.options:
            return ""
        return self.options[self.selected_index].get('label', "")

    def set_selected_by_value(self, value):
        for i, opt in enumerate(self.options):
            if opt.get('value') == value:
                self.selected_index = i
                return True
        return False

    def handle_event(self, event):
        # Descomente para depuração:
        # if event.type == pygame.MOUSEBUTTONDOWN:
        #     print(f"[Dropdown] MOUSEBUTTONDOWN at {event.pos}, rect={self.rect}, collide={self.rect.collidepoint(event.pos)}")

        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            # Clique no botão principal
            if self.rect.collidepoint(event.pos):
                self.is_open = not self.is_open
                return 'toggle'

            # Clique em uma opção (se aberto)
            if self.is_open:
                for i, opt in enumerate(self.options):
                    opt_rect = self._get_option_rect(i)
                    if opt_rect.collidepoint(event.pos):
                        self.selected_index = i
                        self.is_open = False
                        return 'select'

                # Clicou fora do dropdown, fecha
                self.is_open = False

        elif event.type == pygame.MOUSEMOTION:
            if self.is_open:
                self.hovered_option = -1
                for i in range(len(self.options)):
                    opt_rect = self._get_option_rect(i)
                    if opt_rect.collidepoint(event.pos):
                        self.hovered_option = i
                        break
            else:
                self.hovered_option = -1

        return None

    def _get_option_rect(self, index):
        option_height = 30
        return pygame.Rect(
            self.rect.x,
            self.rect.bottom + index * option_height,
            self.rect.width,
            option_height
        )

    def render(self, screen, font):
        """Renderiza o botão principal (sem as opções)"""
        colors = COLORS['FILTERS']
        text_colors = COLORS['TEXT']

        # Sombra do botão
        shadow_rect = self.rect.copy()
        shadow_rect.x += 2
        shadow_rect.y += 2
        pygame.draw.rect(screen, colors['DROPDOWN_SHADOW'], shadow_rect, border_radius=6)

        # Fundo do botão principal
        bg_color = colors['DROPDOWN_BG'] if not self.is_open else colors['SEARCH_ACTIVE']
        pygame.draw.rect(screen, bg_color, self.rect, border_radius=6)
        pygame.draw.rect(screen, colors['DROPDOWN_BORDER'], self.rect, 2, border_radius=6)

        # Label
        label_font = pygame.font.Font(None, 14)
        if self.label:
            label_surf = label_font.render(self.label, True, text_colors['DARK_GRAY'])
            screen.blit(label_surf, (self.rect.x + 8, self.rect.y + (self.rect.height - label_surf.get_height()) // 2))

            selected_label = self.get_selected_label()
            value_font = pygame.font.Font(None, 16)
            value_surf = value_font.render(selected_label, True, text_colors['WHITE'])

            label_width = label_surf.get_width()
            value_x = self.rect.x + 12 + label_width + 6
            screen.blit(value_surf, (value_x, self.rect.y + (self.rect.height - value_surf.get_height()) // 2))

            arrow_x = self.rect.right - 18
            arrow_y = self.rect.centery
            if self.is_open:
                points = [(arrow_x - 5, arrow_y + 2), (arrow_x + 5, arrow_y + 2), (arrow_x, arrow_y - 4)]
            else:
                points = [(arrow_x - 5, arrow_y - 2), (arrow_x + 5, arrow_y - 2), (arrow_x, arrow_y + 4)]
            pygame.draw.polygon(screen, text_colors['DARK_GRAY'], points)

        else:
            selected_label = self.get_selected_label()
            value_font = pygame.font.Font(None, 16)
            value_surf = value_font.render(selected_label, True, text_colors['WHITE'])
            value_rect = value_surf.get_rect(center=self.rect.center)
            screen.blit(value_surf, value_rect)

            arrow_x = self.rect.right - 18
            arrow_y = self.rect.centery
            if self.is_open:
                points = [(arrow_x - 5, arrow_y + 2), (arrow_x + 5, arrow_y + 2), (arrow_x, arrow_y - 4)]
            else:
                points = [(arrow_x - 5, arrow_y - 2), (arrow_x + 5, arrow_y - 2), (arrow_x, arrow_y + 4)]
            pygame.draw.polygon(screen, text_colors['DARK_GRAY'], points)

    def render_dropdown_options(self, screen, font):
        """Renderiza apenas as opções abertas (para desenhar por cima de tudo)"""
        if not self.is_open:
            return

        colors = COLORS['FILTERS']
        text_colors = COLORS['TEXT']

        option_height = 30
        total_height = len(self.options) * option_height

        list_rect = pygame.Rect(
            self.rect.x,
            self.rect.bottom,
            self.rect.width,
            total_height
        )
        pygame.draw.rect(screen, colors['DROPDOWN_OPTION_BG'], list_rect, border_radius=6)
        pygame.draw.rect(screen, colors['DROPDOWN_BORDER'], list_rect, 2, border_radius=6)

        for i, opt in enumerate(self.options):
            opt_rect = self._get_option_rect(i)

            if i == self.hovered_option:
                pygame.draw.rect(screen, colors['DROPDOWN_OPTION_HOVER'], opt_rect)
            elif i == self.selected_index:
                pygame.draw.rect(screen, colors['DROPDOWN_OPTION_SELECTED'], opt_rect)

            opt_font = pygame.font.Font(None, 15)
            color = text_colors['WHITE'] if i == self.selected_index else text_colors['GRAY']
            opt_surf = opt_font.render(opt.get('label', ''), True, color)
            screen.blit(opt_surf, (opt_rect.x + 10, opt_rect.y + (opt_rect.height - opt_surf.get_height()) // 2))

            if i < len(self.options) - 1:
                pygame.draw.line(screen, colors['DROPDOWN_BORDER'],
                                 (opt_rect.x + 8, opt_rect.bottom),
                                 (opt_rect.x + opt_rect.width - 8, opt_rect.bottom), 1)


class PokemonFilters:
    """Controles de filtro com dropdowns e busca integrada - centralizado"""

    def __init__(self, x, y, width):
        self.rect = pygame.Rect(x, y, width, LAYOUT['FILTERS']['HEIGHT'])

        padding = LAYOUT['FILTERS']['PADDING']
        search_width = LAYOUT['FILTERS']['SEARCH_WIDTH']
        dropdown_width = LAYOUT['FILTERS']['DROPDOWN_WIDTH']
        spacing = LAYOUT['FILTERS']['SPACING']

        total_width = search_width + spacing + dropdown_width + spacing + dropdown_width
        start_x = self.rect.x + (self.rect.width - total_width) // 2

        self.search_rect = pygame.Rect(start_x, y + 12, search_width, 32)
        current_x = start_x + search_width + spacing

        filter_options = [
            {'label': 'Todos', 'value': 'all'},
            {'label': 'Shiny', 'value': 'shiny'},
            {'label': 'Normal', 'value': 'normal'},
        ]
        sort_options = [
            {'label': 'Captura', 'value': 'capture'},
            {'label': 'A-Z', 'value': 'name_asc'},
            {'label': 'Z-A', 'value': 'name_desc'},
            {'label': 'ID crescente', 'value': 'id_asc'},
            {'label': 'ID decrescente', 'value': 'id_desc'},
        ]

        self.filter_dropdown = Dropdown(
            current_x, y + 12, dropdown_width, 32,
            filter_options, default_index=0, label="Filtrar:"
        )
        current_x += dropdown_width + spacing

        self.sort_dropdown = Dropdown(
            current_x, y + 12, dropdown_width, 32,
            sort_options, default_index=0, label="Ordenar:"
        )

        self.search_text = ""
        self.search_active = False
        self.current_filter = "all"
        self.current_sort = "capture"

    def update_search_state(self, search_text):
        self.search_text = search_text

    def update_filter_state(self, filter_value):
        self.current_filter = filter_value
        self.filter_dropdown.set_selected_by_value(filter_value)

    def update_sort_state(self, sort_type):
        self.current_sort = sort_type
        self.sort_dropdown.set_selected_by_value(sort_type)

    def handle_event(self, event):
        # Processa eventos de teclado para a busca
        if event.type == pygame.KEYDOWN and self.search_active:
            if event.key == pygame.K_RETURN:
                self.search_active = False
                return {'type': 'SEARCH_CHANGED', 'search': self.search_text}
            elif event.key == pygame.K_BACKSPACE:
                self.search_text = self.search_text[:-1]
                return {'type': 'SEARCH_CHANGED', 'search': self.search_text}
            elif event.key == pygame.K_ESCAPE:
                self.search_active = False
                self.search_text = ""
                return {'type': 'SEARCH_CHANGED', 'search': self.search_text}
            else:
                if event.unicode and event.unicode.isprintable() and len(self.search_text) < 30:
                    self.search_text += event.unicode
                    return {'type': 'SEARCH_CHANGED', 'search': self.search_text}
            return None

        # Processa eventos do mouse
        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            # Clique no campo de busca
            if self.search_rect.collidepoint(event.pos):
                self.search_active = True
                return None

            # Se clicou fora da busca e fora dos dropdowns, desativa a busca
            # mas não impede o clique nos dropdowns
            clicked_filter = self.filter_dropdown.rect.collidepoint(event.pos)
            clicked_sort = self.sort_dropdown.rect.collidepoint(event.pos)
            if not clicked_filter and not clicked_sort:
                self.search_active = False

        # Processa dropdowns
        filter_result = self.filter_dropdown.handle_event(event)
        if filter_result == 'select':
            selected = self.filter_dropdown.get_selected_value()
            if selected and selected != self.current_filter:
                self.current_filter = selected
                return {'type': 'FILTER_CHANGED', 'filter': self.current_filter}
            return None
        elif filter_result == 'toggle':
            # Fecha o outro dropdown
            self.sort_dropdown.is_open = False
            return None

        sort_result = self.sort_dropdown.handle_event(event)
        if sort_result == 'select':
            selected = self.sort_dropdown.get_selected_value()
            if selected and selected != self.current_sort:
                self.current_sort = selected
                return {'type': 'SORT_CHANGED', 'sort': self.current_sort}
            return None
        elif sort_result == 'toggle':
            self.filter_dropdown.is_open = False
            return None

        return None

    def render(self, screen, font):
        """Renderiza fundo, busca e botões dos dropdowns (sem opções)"""
        colors = COLORS['FILTERS']
        text_colors = COLORS['TEXT']

        # Fundo da área de filtros
        pygame.draw.rect(screen, colors['BACKGROUND'], self.rect, border_radius=10)
        pygame.draw.rect(screen, colors['BORDER'], self.rect, 2, border_radius=10)

        # ===== CAMPO DE BUSCA =====
        if self.search_active:
            search_color = colors['SEARCH_ACTIVE']
            search_border = colors['SEARCH_BORDER_ACTIVE']
        else:
            search_color = colors['SEARCH_DEFAULT']
            search_border = colors['SEARCH_BORDER']

        pygame.draw.rect(screen, search_color, self.search_rect, border_radius=6)
        pygame.draw.rect(screen, search_border, self.search_rect, 2, border_radius=6)

        # Ícone de busca
        icon_font = pygame.font.Font(None, 14)
        icon_text = icon_font.render("Buscar", True, text_colors['DARK_GRAY'])
        screen.blit(icon_text, (self.search_rect.x + 10, self.search_rect.y + 9))

        # Texto da busca
        text_x = self.search_rect.x + 62
        text_y = self.search_rect.y + 8

        if self.search_text:
            display_text = self.search_text
            color = text_colors['WHITE']
        else:
            display_text = "nome ou apelido..."
            color = text_colors['DARK_GRAY']

        max_text_width = self.search_rect.width - 75
        temp_text = display_text
        while font.size(temp_text)[0] > max_text_width and len(temp_text) > 0:
            temp_text = temp_text[:-1]
        if temp_text != display_text and self.search_text:
            temp_text = temp_text[:-3] + "..."

        search_surf = font.render(temp_text, True, color)
        screen.blit(search_surf, (text_x, text_y))

        # Cursor piscando
        if self.search_active and (pygame.time.get_ticks() // 500) % 2:
            cursor_text = self.search_text
            cursor_width = font.size(cursor_text)[0]
            cursor_x = text_x + cursor_width
            if cursor_x < self.search_rect.right - 10:
                cursor_color = text_colors['WHITE']
                pygame.draw.line(screen, cursor_color,
                                 (cursor_x, text_y),
                                 (cursor_x, text_y + font.get_height()), 2)

        # ===== DROPDOWNS (apenas botões, sem opções) =====
        self.filter_dropdown.render(screen, font)
        self.sort_dropdown.render(screen, font)

    def render_dropdowns(self, screen, font):
        """Desenha as opções abertas dos dropdowns (por cima do grid)"""
        self.filter_dropdown.render_dropdown_options(screen, font)
        self.sort_dropdown.render_dropdown_options(screen, font)