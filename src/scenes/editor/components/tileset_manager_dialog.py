# src/scenes/editor/components/tileset_manager_dialog.py

import pygame
import os
from tkinter import filedialog, Tk


class TilesetManagerDialog:
    """Diálogo para gerenciar múltiplos tilesets na layer atual"""

    COLORS = {
        'bg': (40, 40, 50),
        'bg_light': (50, 50, 60),
        'bg_dark': (30, 30, 40),
        'border': (255, 215, 0),
        'border_light': (80, 80, 90),
        'text': (255, 255, 255),
        'text_dim': (200, 200, 200),
        'text_dark': (150, 150, 150),
        'accent': (80, 100, 120),
        'accent_hover': (100, 120, 140),
        'success': (0, 120, 0),
        'danger': (120, 0, 0),
        'warning': (120, 120, 0),
    }

    def __init__(self, x, y, width, height, layer, editor_scene):
        self.rect = pygame.Rect(x, y, width, height)
        self.visible = True
        self.layer = layer
        self.editor = editor_scene

        # UI State
        self.dragging = False
        self.drag_offset_x = 0
        self.drag_offset_y = 0
        self.hovered_button = None
        self.scroll_offset = 0
        self.selected_tileset_index = -1

        # Fontes
        self.font_title = pygame.font.Font(None, 24)
        self.font = pygame.font.Font(None, 20)
        self.font_small = pygame.font.Font(None, 16)

        # Tkinter para file dialog
        self.root = Tk()
        self.root.withdraw()

        # Botões
        self._init_buttons()

    def _init_buttons(self):
        x, y, w, h = self.rect

        # Botões superiores
        self.add_button = pygame.Rect(x + 20, y + 50, 100, 30)
        self.remove_button = pygame.Rect(x + 130, y + 50, 100, 30)
        self.clear_button = pygame.Rect(x + 240, y + 50, 100, 30)

        # Botões de ação
        self.close_button = pygame.Rect(x + w - 30, y + 5, 25, 25)
        self.apply_button = pygame.Rect(x + w - 150, y + h - 45, 80, 30)
        self.cancel_button = pygame.Rect(x + w - 65, y + h - 45, 80, 30)

        # Área da lista
        self.list_area = pygame.Rect(x + 10, y + 100, w - 20, h - 150)

        # Altura de cada item na lista
        self.item_height = 70

    def _update_button_positions(self):
        x, y, w, h = self.rect

        self.add_button.x = x + 20
        self.add_button.y = y + 50
        self.remove_button.x = x + 130
        self.remove_button.y = y + 50
        self.clear_button.x = x + 240
        self.clear_button.y = y + 50

        self.close_button.x = x + w - 30
        self.close_button.y = y + 5

        self.apply_button.x = x + w - 150
        self.apply_button.y = y + h - 45
        self.cancel_button.x = x + w - 65
        self.cancel_button.y = y + h - 45

        self.list_area.x = x + 10
        self.list_area.y = y + 100
        self.list_area.width = w - 20
        self.list_area.height = h - 150

    def handle_event(self, event):
        if not self.visible:
            return False

        mouse_pos = pygame.mouse.get_pos()
        mouse_x, mouse_y = mouse_pos
        self.hovered_button = None

        # Atualiza hover
        self._update_hover(mouse_x, mouse_y)

        if event.type == pygame.MOUSEBUTTONDOWN:
            if event.button == 1:
                return self._handle_left_click(mouse_x, mouse_y)
            elif event.button == 4:  # Scroll up
                self.scroll_offset = max(0, self.scroll_offset - 1)
                return True
            elif event.button == 5:  # Scroll down
                max_scroll = max(0, len(self.layer.tilesets) - self._get_visible_items())
                self.scroll_offset = min(max_scroll, self.scroll_offset + 1)
                return True

        elif event.type == pygame.MOUSEBUTTONUP:
            if event.button == 1:
                self.dragging = False

        elif event.type == pygame.MOUSEMOTION:
            if self.dragging:
                self.rect.x = mouse_x - self.drag_offset_x
                self.rect.y = mouse_y - self.drag_offset_y
                self._update_button_positions()
                return True

        return True

    def _update_hover(self, mouse_x, mouse_y):
        buttons = [
            (self.add_button, "add"),
            (self.remove_button, "remove"),
            (self.clear_button, "clear"),
            (self.apply_button, "apply"),
            (self.cancel_button, "cancel"),
        ]

        for button, name in buttons:
            if button.collidepoint(mouse_x, mouse_y):
                self.hovered_button = name
                return

    def _handle_left_click(self, mouse_x, mouse_y):
        # Título para arrastar
        title_rect = pygame.Rect(self.rect.x, self.rect.y, self.rect.width, 30)
        if title_rect.collidepoint(mouse_x, mouse_y):
            self.dragging = True
            self.drag_offset_x = mouse_x - self.rect.x
            self.drag_offset_y = mouse_y - self.rect.y
            return True

        # Botão fechar
        if self.close_button.collidepoint(mouse_x, mouse_y):
            self.visible = False
            return True

        # Botões de ação
        if self.add_button.collidepoint(mouse_x, mouse_y):
            self._add_tileset()
            return True

        if self.remove_button.collidepoint(mouse_x, mouse_y):
            self._remove_selected_tileset()
            return True

        if self.clear_button.collidepoint(mouse_x, mouse_y):
            self._clear_all_tilesets()
            return True

        if self.apply_button.collidepoint(mouse_x, mouse_y):
            self._apply_changes()
            return True

        if self.cancel_button.collidepoint(mouse_x, mouse_y):
            self.visible = False
            return True

        # Selecionar tileset na lista
        if self.list_area.collidepoint(mouse_x, mouse_y):
            relative_y = mouse_y - self.list_area.y
            item_index = (relative_y // self.item_height) + self.scroll_offset

            if 0 <= item_index < len(self.layer.tilesets):
                self.selected_tileset_index = item_index
                return True

        return True

    def _get_visible_items(self):
        return self.list_area.height // self.item_height

    def _add_tileset(self):
        """Adiciona um novo arquivo de tileset"""
        file_path = filedialog.askopenfilename(
            title="Selecione uma imagem de tileset (pode conter múltiplos tilesets)",
            filetypes=[("Image files", "*.png *.jpg *.jpeg *.bmp *.gif")]
        )

        if file_path:
            print(f"\n[TS Manager] Adicionando tileset: {file_path}")
            success = self.layer.add_tileset_6x8(file_path, self.editor.grid_size, self.editor.grid_size)

            if success:
                print(f"[TS Manager] Tileset adicionado! Total tilesets: {len(self.layer.tilesets)}")
                self.scroll_offset = max(0, len(self.layer.tilesets) - self._get_visible_items())
                self.selected_tileset_index = len(self.layer.tilesets) - 1
            else:
                print(f"[TS Manager] Erro ao adicionar tileset")

    def _remove_selected_tileset(self):
        """Remove o tileset selecionado"""
        if 0 <= self.selected_tileset_index < len(self.layer.tilesets):
            removed = self.layer.tilesets.pop(self.selected_tileset_index)
            print(f"[TS Manager] Removendo tileset: {removed.get('path', 'Unknown')}")

            # Reconstrói a lista principal de tiles
            self.layer.tileset = []
            for ts in self.layer.tilesets:
                self.layer.tileset.extend(ts['tiles'])

            # Atualiza os start_ids
            current_id = 1
            for ts in self.layer.tilesets:
                ts['start_id'] = current_id
                current_id += ts['count']

            # Atualiza paths
            self.layer.tileset_paths = [ts['path'] for ts in self.layer.tilesets]

            if self.selected_tileset_index >= len(self.layer.tilesets):
                self.selected_tileset_index = len(self.layer.tilesets) - 1

            print(
                f"[TS Manager] Tilesets restantes: {len(self.layer.tilesets)}, Total tiles: {len(self.layer.tileset)}")

    def _clear_all_tilesets(self):
        """Remove todos os tilesets"""
        self.layer.tilesets = []
        self.layer.tileset = []
        self.layer.tileset_paths = []
        self.selected_tileset_index = -1
        print(f"[TS Manager] Todos os tilesets removidos")

    def _apply_changes(self):
        """Aplica as mudanças e fecha o diálogo"""
        # Atualiza a tile palette
        all_tiles, boundaries = self.layer.get_all_tiles_with_boundaries()
        self.editor.tile_palette.set_tileset(all_tiles, boundaries)
        self.editor.tile_palette._update_max_scroll()

        self.visible = False
        print(
            f"[TS Manager] Alterações aplicadas: {len(self.layer.tilesets)} tilesets, {len(self.layer.tileset)} tiles")

    def render(self, screen):
        if not self.visible:
            return

        # Overlay
        overlay = pygame.Surface((screen.get_width(), screen.get_height()))
        overlay.set_alpha(180)
        overlay.fill((0, 0, 0))
        screen.blit(overlay, (0, 0))

        # Fundo
        pygame.draw.rect(screen, self.COLORS['bg'], self.rect, border_radius=10)
        pygame.draw.rect(screen, self.COLORS['border'], self.rect, 2, border_radius=10)

        # Título
        title_bar = pygame.Rect(self.rect.x, self.rect.y, self.rect.width, 30)
        pygame.draw.rect(screen, self.COLORS['bg_light'], title_bar,
                         border_top_left_radius=10, border_top_right_radius=10)

        title = self.font_title.render("Gerenciador de Tilesets", True, self.COLORS['text'])
        screen.blit(title, (self.rect.x + 10, self.rect.y + 8))

        # Botão fechar
        pygame.draw.rect(screen, (80, 80, 90), self.close_button)
        pygame.draw.line(screen, (255, 255, 255),
                         (self.close_button.x + 5, self.close_button.y + 5),
                         (self.close_button.right - 5, self.close_button.bottom - 5), 2)
        pygame.draw.line(screen, (255, 255, 255),
                         (self.close_button.right - 5, self.close_button.y + 5),
                         (self.close_button.x + 5, self.close_button.bottom - 5), 2)

        # Botões superiores
        self._render_top_buttons(screen)

        # Lista de tilesets
        self._render_tileset_list(screen)

        # Botões inferiores
        self._render_bottom_buttons(screen)

        # Info
        info_text = self.font_small.render(
            f"Total: {len(self.layer.tilesets)} tilesets | {len(self.layer.tileset)} tiles",
            True, self.COLORS['text_dim']
        )
        screen.blit(info_text, (self.rect.x + 10, self.rect.bottom - 35))

    def _render_top_buttons(self, screen):
        # Botão Adicionar
        add_color = self.COLORS['success'] if self.hovered_button == "add" else (0, 80, 0)
        pygame.draw.rect(screen, add_color, self.add_button, border_radius=5)
        add_text = self.font_small.render("+ Adicionar", True, self.COLORS['text'])
        add_x = self.add_button.x + (self.add_button.width - add_text.get_width()) // 2
        add_y = self.add_button.y + (self.add_button.height - add_text.get_height()) // 2
        screen.blit(add_text, (add_x, add_y))

        # Botão Remover
        remove_color = self.COLORS['danger'] if self.hovered_button == "remove" else (80, 0, 0)
        pygame.draw.rect(screen, remove_color, self.remove_button, border_radius=5)
        remove_text = self.font_small.render("- Remover", True, self.COLORS['text'])
        remove_x = self.remove_button.x + (self.remove_button.width - remove_text.get_width()) // 2
        remove_y = self.remove_button.y + (self.remove_button.height - remove_text.get_height()) // 2
        screen.blit(remove_text, (remove_x, remove_y))

        # Botão Limpar Tudo
        clear_color = self.COLORS['warning'] if self.hovered_button == "clear" else (80, 80, 0)
        pygame.draw.rect(screen, clear_color, self.clear_button, border_radius=5)
        clear_text = self.font_small.render("Limpar Tudo", True, self.COLORS['text'])
        clear_x = self.clear_button.x + (self.clear_button.width - clear_text.get_width()) // 2
        clear_y = self.clear_button.y + (self.clear_button.height - clear_text.get_height()) // 2
        screen.blit(clear_text, (clear_x, clear_y))

    def _render_tileset_list(self, screen):
        # Fundo da lista
        pygame.draw.rect(screen, self.COLORS['bg_dark'], self.list_area, border_radius=5)

        # Clipping
        old_clip = screen.get_clip()
        screen.set_clip(self.list_area)

        list_x = self.list_area.x + 5
        list_start_y = self.list_area.y + 2 - self.scroll_offset * self.item_height

        for i, ts in enumerate(self.layer.tilesets):
            item_y = list_start_y + i * self.item_height

            if item_y + self.item_height < self.list_area.y or item_y > self.list_area.y + self.list_area.height:
                continue

            item_rect = pygame.Rect(list_x, item_y, self.list_area.width - 10, self.item_height - 4)

            # Fundo do item
            is_selected = (i == self.selected_tileset_index)
            if is_selected:
                bg_color = self.COLORS['accent']
                border_color = self.COLORS['border']
            else:
                bg_color = self.COLORS['bg_light'] if i % 2 == 0 else self.COLORS['bg']
                border_color = self.COLORS['border_light']

            pygame.draw.rect(screen, bg_color, item_rect, border_radius=5)
            pygame.draw.rect(screen, border_color, item_rect, 1, border_radius=5)

            # Número do tileset
            ts_num = self.font.render(f"Tileset #{i + 1}", True, self.COLORS['text'])
            screen.blit(ts_num, (item_rect.x + 10, item_rect.y + 8))

            # IDs
            id_text = self.font_small.render(
                f"IDs: {ts['start_id']} a {ts['start_id'] + ts['count'] - 1}",
                True, self.COLORS['text_dim']
            )
            screen.blit(id_text, (item_rect.x + 10, item_rect.y + 32))

            # Caminho do arquivo (truncado)
            path = ts.get('path', 'Unknown')
            path_short = path.split('/')[-1] if '/' in path else path.split('\\')[-1] if '\\' in path else path
            path_text = self.font_small.render(path_short, True, self.COLORS['text_dark'])
            screen.blit(path_text, (item_rect.x + 10, item_rect.y + 50))

            # Preview dos primeiros tiles
            preview_x = item_rect.right - 100
            preview_y = item_rect.y + 10
            preview_size = 24

            for p in range(min(3, ts['count'])):
                if p < len(ts['tiles']):
                    tile = ts['tiles'][p]
                    scaled = pygame.transform.scale(tile, (preview_size, preview_size))
                    screen.blit(scaled, (preview_x + p * (preview_size + 2), preview_y))

        screen.set_clip(old_clip)

        # Indicador de scroll
        visible_items = self._get_visible_items()
        if len(self.layer.tilesets) > visible_items:
            scroll_text = self.font_small.render(
                f"{self.scroll_offset + 1}-{min(self.scroll_offset + visible_items, len(self.layer.tilesets))} de {len(self.layer.tilesets)}",
                True, self.COLORS['text_dark']
            )
            screen.blit(scroll_text, (self.list_area.x + 5, self.list_area.bottom + 5))

    def _render_bottom_buttons(self, screen):
        # Botão Aplicar
        apply_color = self.COLORS['success'] if self.hovered_button == "apply" else (0, 80, 0)
        pygame.draw.rect(screen, apply_color, self.apply_button, border_radius=5)
        apply_text = self.font.render("Aplicar", True, self.COLORS['text'])
        apply_x = self.apply_button.x + (self.apply_button.width - apply_text.get_width()) // 2
        apply_y = self.apply_button.y + (self.apply_button.height - apply_text.get_height()) // 2
        screen.blit(apply_text, (apply_x, apply_y))

        # Botão Cancelar
        cancel_color = self.COLORS['danger'] if self.hovered_button == "cancel" else (80, 0, 0)
        pygame.draw.rect(screen, cancel_color, self.cancel_button, border_radius=5)
        cancel_text = self.font.render("Cancelar", True, self.COLORS['text'])
        cancel_x = self.cancel_button.x + (self.cancel_button.width - cancel_text.get_width()) // 2
        cancel_y = self.cancel_button.y + (self.cancel_button.height - cancel_text.get_height()) // 2
        screen.blit(cancel_text, (cancel_x, cancel_y))