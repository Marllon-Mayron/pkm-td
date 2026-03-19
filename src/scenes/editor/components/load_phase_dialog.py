# src/scenes/editor/components/load_phase_dialog.py

import pygame


class LoadPhaseDialog:
    """Diálogo para carregar uma fase existente"""

    def __init__(self, x, y, width, height, exporter):
        self.rect = pygame.Rect(x, y, width, height)
        self.visible = True
        self.exporter = exporter

        # Estado da UI
        self.dragging = False
        self.drag_offset_x = 0
        self.drag_offset_y = 0
        self.hovered_button = None
        self.hovered_item_index = -1

        # Dados das fases disponíveis
        self.available_phases = []  # Lista de (chapter, phase)
        self.selected_chapter = 1
        self.selected_phase = 1
        self.filtered_phases = []

        # Scroll
        self.phases_scroll = 0
        self.max_scroll = 0
        self.items_per_page = 8
        self.item_height = 32

        # Input fields
        self.active_input = None
        self.temp_chapter = "1"
        self.temp_phase = "1"

        # Fontes
        self.font_title = pygame.font.Font(None, 24)
        self.font = pygame.font.Font(None, 20)
        self.font_small = pygame.font.Font(None, 16)

        # Carrega fases disponíveis
        self._load_available_phases()

        # Inicializa botões
        self._init_buttons()

        # Área da lista
        self.list_area = pygame.Rect(
            self.rect.x + 15,
            self.rect.y + 190,
            self.rect.width - 30,
            self.items_per_page * self.item_height + 5
        )

    def _init_buttons(self):
        """Inicializa botões"""
        x, y, w, h = self.rect

        # Botões de ação
        button_width = 80
        button_height = 30
        button_spacing = 15
        total_width = button_width * 2 + button_spacing

        self.load_button = pygame.Rect(
            x + (w - total_width) // 2,
            y + h - 45,
            button_width,
            button_height
        )

        self.cancel_button = pygame.Rect(
            self.load_button.right + button_spacing,
            y + h - 45,
            button_width,
            button_height
        )

        # Botão atualizar
        self.refresh_button = pygame.Rect(
            x + w - 95,
            y + 70,
            80,
            25
        )

        # Input boxes
        input_width = 80
        input_x = x + 150

        self.chapter_input = pygame.Rect(input_x, y + 110, input_width, 25)
        self.phase_input = pygame.Rect(input_x, y + 145, input_width, 25)

    def _load_available_phases(self):
        """Carrega lista de fases disponíveis"""
        self.available_phases = self.exporter.list_phases()
        self.filtered_phases = self.available_phases.copy()
        self.filtered_phases.sort(key=lambda x: (x[0], x[1]))

        # Seleciona a primeira fase disponível, se houver
        if self.filtered_phases:
            self.selected_chapter, self.selected_phase = self.filtered_phases[0]
            self.temp_chapter = str(self.selected_chapter)
            self.temp_phase = str(self.selected_phase)

        # Atualiza scroll máximo
        self._update_max_scroll()

    def _update_max_scroll(self):
        """Atualiza o limite máximo de scroll"""
        self.max_scroll = max(0, len(self.filtered_phases) - self.items_per_page)

    def handle_event(self, event):
        """Processa eventos do diálogo - Retorna None ou dicionário com resultado"""
        if not self.visible:
            return None

        mouse_pos = pygame.mouse.get_pos()
        mouse_x, mouse_y = mouse_pos

        # Atualiza hover
        self.hovered_button = None
        self.hovered_item_index = -1

        # Se clicou fora do diálogo, fecha
        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            if not self.rect.collidepoint(mouse_x, mouse_y):
                self.visible = False
                return None

        if event.type == pygame.MOUSEBUTTONDOWN:
            if event.button == 1:
                return self._handle_left_click(mouse_x, mouse_y)
            elif event.button == 4:  # Scroll up
                self.phases_scroll = max(0, self.phases_scroll - 1)
                return None
            elif event.button == 5:  # Scroll down
                self.phases_scroll = min(self.max_scroll, self.phases_scroll + 1)
                return None

        elif event.type == pygame.MOUSEBUTTONUP:
            if event.button == 1:
                self.dragging = False
                return None

        elif event.type == pygame.MOUSEMOTION:
            # Atualiza hover dos botões
            if self.load_button.collidepoint(mouse_x, mouse_y):
                self.hovered_button = "load"
            elif self.cancel_button.collidepoint(mouse_x, mouse_y):
                self.hovered_button = "cancel"
            elif self.refresh_button.collidepoint(mouse_x, mouse_y):
                self.hovered_button = "refresh"

            # Atualiza hover da lista
            if self.list_area.collidepoint(mouse_x, mouse_y):
                relative_y = mouse_y - self.list_area.y
                item_index = (relative_y // self.item_height) + self.phases_scroll
                if 0 <= item_index < len(self.filtered_phases):
                    self.hovered_item_index = item_index

            if self.dragging:
                self.rect.x = mouse_x - self.drag_offset_x
                self.rect.y = mouse_y - self.drag_offset_y
                self._update_button_positions()
                return None

        elif event.type == pygame.KEYDOWN:
            return self._handle_keydown(event)

        return None

    def _update_button_positions(self):
        """Atualiza posições dos botões após arrastar"""
        x, y, w, h = self.rect

        # Botões de ação
        button_width = 80
        button_height = 30
        button_spacing = 15
        total_width = button_width * 2 + button_spacing

        self.load_button.x = x + (w - total_width) // 2
        self.load_button.y = y + h - 45

        self.cancel_button.x = self.load_button.right + button_spacing
        self.cancel_button.y = y + h - 45

        # Botão atualizar
        self.refresh_button.x = x + w - 95
        self.refresh_button.y = y + 70

        # Input boxes
        self.chapter_input.x = x + 150
        self.chapter_input.y = y + 110
        self.phase_input.x = x + 150
        self.phase_input.y = y + 145

        # Área da lista
        self.list_area.x = x + 15
        self.list_area.y = y + 190

    def _handle_left_click(self, mouse_x, mouse_y):
        """Processa clique esquerdo - Retorna None ou dicionário"""
        # Título para arrastar
        title_rect = pygame.Rect(self.rect.x, self.rect.y, self.rect.width, 30)
        if title_rect.collidepoint(mouse_x, mouse_y):
            self.dragging = True
            self.drag_offset_x = mouse_x - self.rect.x
            self.drag_offset_y = mouse_y - self.rect.y
            return None

        # Botão carregar
        if self.load_button.collidepoint(mouse_x, mouse_y):
            return self._confirm_load()

        # Botão cancelar
        if self.cancel_button.collidepoint(mouse_x, mouse_y):
            self.visible = False
            return None

        # Botão atualizar lista
        if self.refresh_button.collidepoint(mouse_x, mouse_y):
            self._load_available_phases()
            self.phases_scroll = 0
            return None

        # Input boxes
        if self.chapter_input.collidepoint(mouse_x, mouse_y):
            self.active_input = "chapter" if self.active_input != "chapter" else None
            return None
        elif self.phase_input.collidepoint(mouse_x, mouse_y):
            self.active_input = "phase" if self.active_input != "phase" else None
            return None
        else:
            self.active_input = None

        # Lista de fases
        if self.list_area.collidepoint(mouse_x, mouse_y):
            # Calcula qual item foi clicado
            relative_y = mouse_y - self.list_area.y
            item_index = (relative_y // self.item_height) + self.phases_scroll

            if 0 <= item_index < len(self.filtered_phases):
                chapter, phase = self.filtered_phases[item_index]
                self.selected_chapter = chapter
                self.selected_phase = phase
                self.temp_chapter = str(chapter)
                self.temp_phase = str(phase)
                return None

        return None

    def _handle_keydown(self, event):
        """Processa teclas pressionadas - Retorna None ou dicionário"""
        if not self.active_input:
            if event.key == pygame.K_ESCAPE:
                self.visible = False
                return None
            elif event.key == pygame.K_RETURN:
                return self._confirm_load()
            return None

        if event.key == pygame.K_RETURN:
            return self._apply_input()
        elif event.key == pygame.K_ESCAPE:
            self.active_input = None
            return None
        elif event.key == pygame.K_BACKSPACE:
            if self.active_input == "chapter":
                self.temp_chapter = self.temp_chapter[:-1]
            elif self.active_input == "phase":
                self.temp_phase = self.temp_phase[:-1]
            return None
        elif event.unicode.isdigit():
            if self.active_input == "chapter":
                self.temp_chapter += event.unicode
            elif self.active_input == "phase":
                self.temp_phase += event.unicode
            return None

        return None

    def _apply_input(self):
        """Aplica o valor do input atual"""
        try:
            if self.active_input == "chapter":
                chapter = int(self.temp_chapter) if self.temp_chapter else 1
                chapter = max(1, min(99, chapter))
                self.selected_chapter = chapter
                self.temp_chapter = str(chapter)
            elif self.active_input == "phase":
                phase = int(self.temp_phase) if self.temp_phase else 1
                phase = max(1, min(99, phase))
                self.selected_phase = phase
                self.temp_phase = str(phase)

            self.active_input = None
            return None
        except ValueError:
            self.active_input = None
            return None

    def _confirm_load(self):
        """Confirma o carregamento da fase"""
        try:
            chapter = int(self.temp_chapter) if self.temp_chapter else 1
            phase = int(self.temp_phase) if self.temp_phase else 1

            # Verifica se a fase existe
            if (chapter, phase) in self.available_phases:
                self.visible = False
                return {
                    'action': 'load',
                    'chapter': chapter,
                    'phase': phase
                }
            else:
                print(f"Fase {chapter}-{phase} não encontrada!")
                return None
        except ValueError:
            return None

    def render(self, screen):
        """Renderiza o diálogo com estilo clean"""
        if not self.visible:
            return

        # Overlay escuro
        overlay = pygame.Surface((screen.get_width(), screen.get_height()))
        overlay.set_alpha(180)
        overlay.fill((0, 0, 0))
        screen.blit(overlay, (0, 0))

        # Fundo da janela
        pygame.draw.rect(screen, (40, 40, 50), self.rect, border_radius=10)
        pygame.draw.rect(screen, (255, 215, 0), self.rect, 2, border_radius=10)

        # Barra de título (para arrastar)
        title_bar = pygame.Rect(self.rect.x, self.rect.y, self.rect.width, 30)
        pygame.draw.rect(screen, (50, 50, 60), title_bar, border_top_left_radius=10, border_top_right_radius=10)

        # Título
        title = self.font_title.render("Carregar Fase", True, (255, 255, 255))
        screen.blit(title, (self.rect.x + 10, self.rect.y + 8))

        # Conteúdo
        content_y = self.rect.y + 45

        # Seção de busca
        search_label = self.font.render("Localizar Fase", True, (255, 215, 0))
        screen.blit(search_label, (self.rect.x + 20, content_y))

        # Input fields
        # Capítulo
        chapter_label = self.font_small.render("Capítulo:", True, (200, 200, 200))
        screen.blit(chapter_label, (self.rect.x + 20, self.rect.y + 115))

        # Input Capítulo
        input_color = (100, 150, 255) if self.active_input == "chapter" else (60, 60, 70)
        pygame.draw.rect(screen, (50, 50, 60), self.chapter_input, border_radius=5)
        pygame.draw.rect(screen, input_color, self.chapter_input, 2, border_radius=5)

        chapter_surf = self.font.render(self.temp_chapter, True, (255, 255, 255))
        screen.blit(chapter_surf, (self.chapter_input.x + 5, self.chapter_input.y + 2))

        # Fase
        phase_label = self.font_small.render("Fase:", True, (200, 200, 200))
        screen.blit(phase_label, (self.rect.x + 20, self.rect.y + 150))

        # Input Fase
        input_color = (100, 150, 255) if self.active_input == "phase" else (60, 60, 70)
        pygame.draw.rect(screen, (50, 50, 60), self.phase_input, border_radius=5)
        pygame.draw.rect(screen, input_color, self.phase_input, 2, border_radius=5)

        phase_surf = self.font.render(self.temp_phase, True, (255, 255, 255))
        screen.blit(phase_surf, (self.phase_input.x + 5, self.phase_input.y + 2))

        # Botão atualizar
        refresh_color = (80, 100, 120) if self.hovered_button == "refresh" else (60, 60, 80)
        pygame.draw.rect(screen, refresh_color, self.refresh_button, border_radius=5)
        pygame.draw.rect(screen, (255, 215, 0), self.refresh_button, 1, border_radius=5)

        refresh_text = self.font_small.render("Atualizar", True, (255, 255, 255))
        refresh_text_rect = refresh_text.get_rect(center=self.refresh_button.center)
        screen.blit(refresh_text, refresh_text_rect)

        # Lista de fases
        list_title = self.font.render("Fases Disponíveis", True, (255, 215, 0))
        screen.blit(list_title, (self.rect.x + 20, self.rect.y + 190))

        # Área da lista com fundo
        pygame.draw.rect(screen, (30, 30, 40), self.list_area, border_radius=5)

        # Clipping para a lista
        old_clip = screen.get_clip()
        screen.set_clip(self.list_area)

        list_x = self.list_area.x + 5
        list_start_y = self.list_area.y + 2 - self.phases_scroll * self.item_height

        for i, (chapter, phase) in enumerate(self.filtered_phases):
            item_y = list_start_y + i * self.item_height

            # Pula itens fora da área visível
            if item_y + self.item_height < self.list_area.y or item_y > self.list_area.y + self.list_area.height:
                continue

            item_rect = pygame.Rect(list_x, item_y, self.list_area.width - 10, self.item_height - 4)

            # Determina cor de fundo
            is_selected = (chapter == self.selected_chapter and phase == self.selected_phase)
            is_hovered = (i == self.hovered_item_index)

            if is_selected:
                bg_color = (80, 100, 120)
            elif is_hovered:
                bg_color = (60, 70, 90)
            else:
                bg_color = (45, 45, 55) if i % 2 == 0 else (40, 40, 50)

            # Desenha item
            pygame.draw.rect(screen, bg_color, item_rect)

            if is_selected:
                pygame.draw.rect(screen, (255, 215, 0), item_rect, 1)

            # Texto da fase
            phase_text = f"Capítulo {chapter:02d} - Fase {phase:02d}"
            text_color = (255, 255, 255) if is_selected else (220, 220, 220)
            text_surf = self.font_small.render(phase_text, True, text_color)
            screen.blit(text_surf, (item_rect.x + 5, item_rect.y + 5))

        screen.set_clip(old_clip)

        # Indicador de scroll
        if self.max_scroll > 0:
            scroll_y = self.phases_scroll / self.max_scroll if self.max_scroll > 0 else 0
            scroll_bar_height = self.list_area.height * (self.items_per_page / len(self.filtered_phases))
            scroll_bar_y = self.list_area.y + 5 + (self.list_area.height - 10 - scroll_bar_height) * scroll_y

            # Barra de scroll
            pygame.draw.rect(screen, (60, 60, 70),
                             (self.list_area.right - 5, self.list_area.y + 2, 3, self.list_area.height - 4),
                             border_radius=2)
            pygame.draw.rect(screen, (150, 150, 150),
                             (self.list_area.right - 5, scroll_bar_y, 3, scroll_bar_height),
                             border_radius=2)

            # Contador
            count_text = self.font_small.render(
                f"{self.phases_scroll + 1}-{min(self.phases_scroll + self.items_per_page, len(self.filtered_phases))} de {len(self.filtered_phases)}",
                True, (150, 150, 150)
            )
            screen.blit(count_text, (self.list_area.x + 10, self.list_area.bottom + 5))

        # Botões de ação
        # Botão Carregar
        load_color = (0, 150, 0) if self.hovered_button == "load" else (0, 120, 0)
        pygame.draw.rect(screen, load_color, self.load_button, border_radius=5)
        pygame.draw.rect(screen, (255, 255, 255), self.load_button, 1, border_radius=5)

        load_text = self.font.render("Carregar", True, (255, 255, 255))
        load_text_rect = load_text.get_rect(center=self.load_button.center)
        screen.blit(load_text, load_text_rect)

        # Botão Cancelar
        cancel_color = (150, 0, 0) if self.hovered_button == "cancel" else (120, 0, 0)
        pygame.draw.rect(screen, cancel_color, self.cancel_button, border_radius=5)
        pygame.draw.rect(screen, (255, 255, 255), self.cancel_button, 1, border_radius=5)

        cancel_text = self.font.render("Cancelar", True, (255, 255, 255))
        cancel_text_rect = cancel_text.get_rect(center=self.cancel_button.center)
        screen.blit(cancel_text, cancel_text_rect)

        # Total de fases
        total_text = self.font_small.render(
            f"Total: {len(self.filtered_phases)} fases disponíveis",
            True, (150, 150, 150)
        )
        screen.blit(total_text, (self.rect.x + 20, self.rect.bottom - 25))