# src/scenes/editor/components/load_phase_dialog.py

import pygame
import os
from pathlib import Path


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

        # Dados das fases disponíveis
        self.available_phases = []  # Lista de (chapter, phase)
        self.selected_chapter = 1
        self.selected_phase = 1
        self.filtered_phases = []

        # Scroll
        self.phases_scroll = 0
        self.max_scroll = 0

        # Input fields
        self.active_input = None
        self.temp_chapter = "1"
        self.temp_phase = "1"

        # Fontes
        self.font = pygame.font.Font(None, 20)
        self.font_small = pygame.font.Font(None, 16)
        self.font_title = pygame.font.Font(None, 24)

        # Carrega fases disponíveis
        self._load_available_phases()

        # Inicializa botões
        self._init_buttons()

    def _init_buttons(self):
        """Inicializa botões"""
        x, y, w, h = self.rect

        # Botão fechar
        self.close_button = pygame.Rect(x + w - 30, y + 5, 25, 25)

        # Botões de ação
        self.load_button = pygame.Rect(x + (w - 170) // 2, y + h - 50, 80, 30)
        self.cancel_button = pygame.Rect(x + (w - 170) // 2 + 90, y + h - 50, 80, 30)

        # Botões para navegação na lista
        self.refresh_button = pygame.Rect(x + w - 100, y + 70, 80, 25)

        # Input boxes
        self.chapter_input = pygame.Rect(x + 150, y + 110, 80, 30)
        self.phase_input = pygame.Rect(x + 150, y + 150, 80, 30)

    def _load_available_phases(self):
        """Carrega lista de fases disponíveis"""
        self.available_phases = self.exporter.list_phases()
        self.filtered_phases = self.available_phases.copy()

        # Seleciona a primeira fase disponível, se houver
        if self.filtered_phases:
            self.selected_chapter, self.selected_phase = self.filtered_phases[0]
            self.temp_chapter = str(self.selected_chapter)
            self.temp_phase = str(self.selected_phase)

        # Atualiza scroll máximo
        self._update_max_scroll()

    def _update_max_scroll(self):
        """Atualiza o limite máximo de scroll"""
        visible_items = 8  # Número de itens visíveis
        self.max_scroll = max(0, len(self.filtered_phases) - visible_items)

    def handle_event(self, event):
        """Processa eventos do diálogo - Retorna None ou dicionário com resultado"""
        if not self.visible:
            return None

        mouse_pos = pygame.mouse.get_pos()
        mouse_x, mouse_y = mouse_pos

        # Se clicou fora do diálogo, fecha
        if event.type == pygame.MOUSEBUTTONDOWN:
            if not self.rect.collidepoint(mouse_x, mouse_y):
                self.visible = False
                return None

        if event.type == pygame.MOUSEBUTTONDOWN:
            if event.button == 1:
                return self._handle_left_click(mouse_x, mouse_y)
            elif event.button == 4:  # Scroll up
                self.phases_scroll = max(0, self.phases_scroll - 1)
                return None  # Não retorna resultado
            elif event.button == 5:  # Scroll down
                self.phases_scroll = min(self.max_scroll, self.phases_scroll + 1)
                return None  # Não retorna resultado

        elif event.type == pygame.MOUSEBUTTONUP:
            if event.button == 1:
                self.dragging = False
                return None

        elif event.type == pygame.MOUSEMOTION:
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

        self.close_button.x = x + w - 30
        self.close_button.y = y + 5

        self.load_button.x = x + (w - 170) // 2
        self.load_button.y = y + h - 50

        self.cancel_button.x = x + (w - 170) // 2 + 90
        self.cancel_button.y = y + h - 50

        self.refresh_button.x = x + w - 100
        self.refresh_button.y = y + 70

        self.chapter_input.x = x + 150
        self.chapter_input.y = y + 110

        self.phase_input.x = x + 150
        self.phase_input.y = y + 150

    def _handle_left_click(self, mouse_x, mouse_y):
        """Processa clique esquerdo - Retorna None ou dicionário"""
        # Título para arrastar
        title_rect = pygame.Rect(self.rect.x, self.rect.y, self.rect.width, 30)
        if title_rect.collidepoint(mouse_x, mouse_y):
            self.dragging = True
            self.drag_offset_x = mouse_x - self.rect.x
            self.drag_offset_y = mouse_y - self.rect.y
            return None

        # Botão fechar
        if self.close_button.collidepoint(mouse_x, mouse_y):
            self.visible = False
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
            self.active_input = "chapter"
            return None
        elif self.phase_input.collidepoint(mouse_x, mouse_y):
            self.active_input = "phase"
            return None

        # Lista de fases
        list_x = self.rect.x + 20
        list_y = self.rect.y + 200 - self.phases_scroll * 30

        for i, (chapter, phase) in enumerate(self.filtered_phases):
            item_rect = pygame.Rect(list_x, list_y + i * 30, 300, 25)
            if item_rect.collidepoint(mouse_x, mouse_y):
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
                # Fase não encontrada
                print(f"Fase {chapter}-{phase} não encontrada!")
                return None
        except ValueError:
            return None

    def render(self, screen):
        """Renderiza o diálogo"""
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

        # Título
        title = self.font_title.render("Carregar Fase", True, (255, 255, 255))
        screen.blit(title, (self.rect.x + 10, self.rect.y + 10))

        # Botão fechar
        pygame.draw.rect(screen, (80, 80, 90), self.close_button)
        pygame.draw.line(screen, (255, 255, 255),
                         (self.close_button.x + 5, self.close_button.y + 5),
                         (self.close_button.right - 5, self.close_button.bottom - 5), 2)
        pygame.draw.line(screen, (255, 255, 255),
                         (self.close_button.right - 5, self.close_button.y + 5),
                         (self.close_button.x + 5, self.close_button.bottom - 5), 2)

        # Botão atualizar
        pygame.draw.rect(screen, (60, 60, 80), self.refresh_button, border_radius=5)
        refresh_text = self.font_small.render("Atualizar", True, (255, 255, 255))
        screen.blit(refresh_text, (self.refresh_button.x + 5, self.refresh_button.y + 5))

        # Input fields
        label_x = self.rect.x + 20

        # Capítulo
        chapter_label = self.font.render("Capítulo:", True, (200, 200, 200))
        screen.blit(chapter_label, (label_x, self.rect.y + 115))

        color = (100, 150, 255) if self.active_input == "chapter" else (80, 80, 90)
        pygame.draw.rect(screen, color, self.chapter_input, 2)
        chapter_surf = self.font.render(self.temp_chapter, True, (255, 255, 255))
        screen.blit(chapter_surf, (self.chapter_input.x + 5, self.chapter_input.y + 5))

        # Fase
        phase_label = self.font.render("Fase:", True, (200, 200, 200))
        screen.blit(phase_label, (label_x, self.rect.y + 155))

        color = (100, 150, 255) if self.active_input == "phase" else (80, 80, 90)
        pygame.draw.rect(screen, color, self.phase_input, 2)
        phase_surf = self.font.render(self.temp_phase, True, (255, 255, 255))
        screen.blit(phase_surf, (self.phase_input.x + 5, self.phase_input.y + 5))

        # Lista de fases disponíveis
        list_title = self.font.render("Fases Disponíveis:", True, (255, 255, 255))
        screen.blit(list_title, (label_x, self.rect.y + 190))

        # Área de clipping para a lista
        clip_rect = pygame.Rect(
            self.rect.x + 15,
            self.rect.y + 215,
            self.rect.width - 30,
            150
        )
        old_clip = screen.get_clip()
        screen.set_clip(clip_rect)

        list_x = self.rect.x + 20
        list_y = self.rect.y + 215 - self.phases_scroll * 30

        for i, (chapter, phase) in enumerate(self.filtered_phases):
            item_rect = pygame.Rect(list_x, list_y + i * 30, clip_rect.width - 10, 25)

            # Verifica se está visível
            if item_rect.bottom < clip_rect.top or item_rect.top > clip_rect.bottom:
                continue

            # Fundo do item
            if chapter == self.selected_chapter and phase == self.selected_phase:
                bg_color = (80, 100, 120)
                border_color = (255, 215, 0)
            else:
                bg_color = (55, 55, 65) if i % 2 == 0 else (50, 50, 60)
                border_color = None

            pygame.draw.rect(screen, bg_color, item_rect)
            if border_color:
                pygame.draw.rect(screen, border_color, item_rect, 1)

            # Texto da fase
            phase_text = f"Capítulo {chapter:02d} - Fase {phase:02d}"
            text_surf = self.font_small.render(phase_text, True, (255, 255, 255))
            screen.blit(text_surf, (item_rect.x + 5, item_rect.y + 5))

        screen.set_clip(old_clip)

        # Indicador de scroll
        if self.max_scroll > 0:
            scroll_text = self.font_small.render(
                f"{self.phases_scroll + 1}/{self.max_scroll + 1}",
                True, (150, 150, 150)
            )
            screen.blit(scroll_text, (self.rect.right - 60, self.rect.y + 340))

        # Botões de ação
        pygame.draw.rect(screen, (0, 150, 0), self.load_button, border_radius=5)
        pygame.draw.rect(screen, (255, 255, 255), self.load_button, 1, border_radius=5)
        load_text = self.font.render("Carregar", True, (255, 255, 255))
        load_x = self.load_button.x + (self.load_button.width - load_text.get_width()) // 2
        load_y = self.load_button.y + (self.load_button.height - load_text.get_height()) // 2
        screen.blit(load_text, (load_x, load_y))

        pygame.draw.rect(screen, (150, 0, 0), self.cancel_button, border_radius=5)
        pygame.draw.rect(screen, (255, 255, 255), self.cancel_button, 1, border_radius=5)
        cancel_text = self.font.render("Cancelar", True, (255, 255, 255))
        cancel_x = self.cancel_button.x + (self.cancel_button.width - cancel_text.get_width()) // 2
        cancel_y = self.cancel_button.y + (self.cancel_button.height - cancel_text.get_height()) // 2
        screen.blit(cancel_text, (cancel_x, cancel_y))

        # Informação
        info_text = self.font_small.render(
            f"Total: {len(self.filtered_phases)} fases disponíveis",
            True, (150, 150, 150)
        )
        screen.blit(info_text, (self.rect.x + 20, self.rect.y + 370))