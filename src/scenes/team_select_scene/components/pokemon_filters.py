# src/scenes/team_select_scene/components/pokemon_filters.py

import pygame
from src.scenes.team_select_scene.utils.constants import COLORS


class PokemonFilters:
    def __init__(self, x, y, width):
        self.rect = pygame.Rect(x, y, width, 100)
        self.search_text = ""
        self.search_active = False
        self.current_sort = "capture"
        self.button_pressed = None
        self.pressed_timer = 0

        # Campo de busca - CENTRALIZADO
        search_width = 300
        self.search_rect = pygame.Rect(
            x + (width - search_width) // 2,
            y + 12,
            search_width,
            32
        )

        # Botões de ordenação - CENTRALIZADOS
        self.sort_buttons = []
        self._create_sort_buttons()

    def _create_sort_buttons(self):
        """Cria botões de ordenação centralizados"""
        button_width = 72
        button_height = 32
        button_spacing = 12

        sort_options = [
            ("CAPTURA", "capture"),
            ("A-Z", "name_asc"),
            ("Z-A", "name_desc"),
            ("ID ↑", "id_asc"),
            ("ID ↓", "id_desc")
        ]

        # Calcula largura total dos botões
        total_buttons_width = len(sort_options) * button_width + (len(sort_options) - 1) * button_spacing

        # Centraliza os botões
        start_x = self.rect.x + (self.rect.width - total_buttons_width) // 2
        y = self.rect.y + 58

        self.sort_buttons = []
        for i, (label, sort_type) in enumerate(sort_options):
            x = start_x + i * (button_width + button_spacing)
            button_rect = pygame.Rect(x, y, button_width, button_height)
            self.sort_buttons.append({
                'rect': button_rect,
                'label': label,
                'sort_type': sort_type,
                'is_active': (self.current_sort == sort_type),
                'pressed': False
            })

    def update_sort_state(self, sort_type):
        """Atualiza o estado dos botões sem recriá-los"""
        self.current_sort = sort_type
        for button in self.sort_buttons:
            button['is_active'] = (button['sort_type'] == self.current_sort)

    def update_search_state(self, search_text):
        """Atualiza o texto de busca"""
        self.search_text = search_text

    def handle_event(self, event):
        """Processa eventos do mouse e teclado"""

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
                # Adiciona caractere
                if event.unicode and event.unicode.isprintable() and len(self.search_text) < 30:
                    self.search_text += event.unicode
                    return {'type': 'SEARCH_CHANGED', 'search': self.search_text}

            return None

        # Processa eventos do mouse
        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            # Verifica clique no campo de busca
            if self.search_rect.collidepoint(event.pos):
                self.search_active = True
                return None

            # Verifica cliques nos botões
            for button in self.sort_buttons:
                if button['rect'].collidepoint(event.pos):
                    button['pressed'] = True
                    self.button_pressed = button
                    self.pressed_timer = pygame.time.get_ticks()
                    break
            else:
                # Clicou fora de tudo
                self.search_active = False

        elif event.type == pygame.MOUSEBUTTONUP and event.button == 1:
            # Verifica se soltou o clique em algum botão
            for button in self.sort_buttons:
                if button.get('pressed', False):
                    button['pressed'] = False

                    # Se o mouse ainda está sobre o botão, executa a ação
                    if button['rect'].collidepoint(event.pos):
                        # Só muda se for diferente do atual
                        if self.current_sort != button['sort_type']:
                            self.current_sort = button['sort_type']
                            # Atualiza estado ativo dos botões
                            for btn in self.sort_buttons:
                                btn['is_active'] = (btn['sort_type'] == self.current_sort)
                            return {'type': 'SORT_CHANGED', 'sort': self.current_sort}
                    break

            self.button_pressed = None

        # Atualiza timer do botão pressionado
        if self.button_pressed and pygame.time.get_ticks() - self.pressed_timer > 100:
            for button in self.sort_buttons:
                button['pressed'] = False
            self.button_pressed = None

        return None

    def render(self, screen, font):
        """Renderiza os controles de filtro"""
        filters_colors = COLORS.get('FILTERS', {})

        # Fundo da área de filtros
        bg_color = filters_colors.get('BACKGROUND', (25, 27, 32))
        border_color = filters_colors.get('BORDER', (55, 58, 65))

        pygame.draw.rect(screen, bg_color, self.rect, border_radius=10)
        pygame.draw.rect(screen, border_color, self.rect, 2, border_radius=10)

        # ===== CAMPO DE BUSCA =====
        if self.search_active:
            search_color = filters_colors.get('SEARCH_ACTIVE', (45, 50, 60))
            search_border = filters_colors.get('SEARCH_BORDER_ACTIVE', (100, 150, 200))
        else:
            search_color = filters_colors.get('SEARCH_DEFAULT', (35, 38, 45))
            search_border = filters_colors.get('SEARCH_BORDER', (70, 75, 85))

        pygame.draw.rect(screen, search_color, self.search_rect, border_radius=6)
        pygame.draw.rect(screen, search_border, self.search_rect, 2, border_radius=6)

        # Ícone de lupa
        try:
            icon_font = pygame.font.Font(None, 18)
            icon = icon_font.render("🔍", True, COLORS['TEXT'].get('DARK_GRAY', (150, 150, 160)))
            screen.blit(icon, (self.search_rect.x + 8, self.search_rect.y + 7))
        except:
            pass

        # Texto da busca
        text_x = self.search_rect.x + 32
        text_y = self.search_rect.y + 8

        if self.search_text:
            display_text = self.search_text
            color = COLORS['TEXT'].get('WHITE', (255, 255, 255))
        else:
            display_text = "Buscar Pokémon..."
            color = COLORS['TEXT'].get('DARK_GRAY', (150, 150, 160))

        # Trunca o texto se necessário
        max_text_width = self.search_rect.width - 40
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
                cursor_color = COLORS['TEXT'].get('WHITE', (255, 255, 255))
                pygame.draw.line(screen, cursor_color,
                                 (cursor_x, text_y),
                                 (cursor_x, text_y + font.get_height()), 2)

        # ===== BOTÕES DE ORDENAÇÃO =====
        for button in self.sort_buttons:
            # Define cores baseado no estado
            if button.get('pressed', False):
                color = (90, 140, 90)
                border_color = (130, 180, 130)
                text_color = (255, 255, 255)
            elif button['is_active']:
                color = (70, 120, 70)
                border_color = (100, 170, 100)
                text_color = (255, 255, 255)
            else:
                color = (45, 48, 55)
                border_color = (80, 85, 95)
                text_color = (200, 200, 200)

            # Sombra do botão
            shadow_rect = button['rect'].copy()
            shadow_rect.x += 2
            shadow_rect.y += 2
            pygame.draw.rect(screen, (15, 17, 22), shadow_rect, border_radius=6)

            # Botão principal
            pygame.draw.rect(screen, color, button['rect'], border_radius=6)
            pygame.draw.rect(screen, border_color, button['rect'], 2, border_radius=6)

            # Texto do botão
            text = font.render(button['label'], True, text_color)
            text_rect = text.get_rect(center=button['rect'].center)
            screen.blit(text, text_rect)

            # Indicador do botão ativo
            if button['is_active'] and not button.get('pressed', False):
                indicator_x = button['rect'].centerx
                indicator_y = button['rect'].bottom - 5
                pygame.draw.circle(screen, (100, 200, 100), (indicator_x, indicator_y), 3)