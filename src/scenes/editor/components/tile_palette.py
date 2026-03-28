# src/scenes/editor/components/tile_palette.py

import pygame


class TilePalette:
    def __init__(self, x, y, width, height):
        self.rect = pygame.Rect(x, y, width, height)
        self.tiles = []
        self.selected_tile = 0  # Garantir que é inteiro
        self.scroll_y = 0
        self.max_scroll = 0
        self.tile_size = 24
        self.visible = True
        self.focused = False

        # Configuração para 6 colunas
        self.cols = 6
        self.tile_spacing = 2
        self.min_tile_size = 16
        self.max_tile_size = 64

        # Informações sobre os tilesets
        self.tileset_boundaries = []

        # Para redimensionamento
        self.resizing = False
        self.resize_margin = 10
        self.min_width = 180
        self.min_height = 250

        # Para arrastar
        self.dragging = False
        self.drag_start_x = 0
        self.drag_start_y = 0
        self.original_x = x
        self.original_y = y

        # Para arrastar a barra de scroll
        self.scroll_dragging = False
        self.scroll_drag_start_y = 0
        self.scroll_drag_start_scroll = 0

    def set_tileset(self, tileset, tileset_boundaries=None):
        """
        Define o tileset e atualiza a palette
        """
        print(f"\n[TilePalette.set_tileset]")
        print(f"  Recebendo {len(tileset)} tiles")
        print(f"  Boundaries: {tileset_boundaries}")

        self.tiles = tileset
        self.tileset_boundaries = tileset_boundaries or []

        # Garante que selected_tile é inteiro
        self.selected_tile = 0

        # Se não temos boundaries, cria boundaries automáticos
        if not self.tileset_boundaries and self.tiles:
            TILES_PER_SET = 48
            for i in range(0, len(self.tiles), TILES_PER_SET):
                self.tileset_boundaries.append(i)
            print(f"  Boundaries automáticos: {self.tileset_boundaries}")

        self._update_max_scroll()
        print(f"  Após update: {len(self.tiles)} tiles, {len(self.tileset_boundaries)} boundaries")

    def _update_max_scroll(self):
        """Atualiza o limite máximo de scroll"""
        if not self.tiles:
            self.max_scroll = 0
            return

        rows = (len(self.tiles) + self.cols - 1) // self.cols
        content_height = rows * (self.tile_size + self.tile_spacing)
        visible_height = self.rect.height - 40
        self.max_scroll = max(0, content_height - visible_height)
        self.scroll_y = max(0, min(self.scroll_y, self.max_scroll))

    def handle_event(self, event):
        """Processa eventos da palette"""
        if not self.visible:
            return False

        mouse_pos = pygame.mouse.get_pos()
        mouse_x, mouse_y = mouse_pos

        self.focused = self.rect.collidepoint(mouse_x, mouse_y)

        if event.type == pygame.MOUSEBUTTONDOWN:
            if event.button == 1:
                if self._is_mouse_on_scrollbar(mouse_x, mouse_y):
                    self.scroll_dragging = True
                    self.scroll_drag_start_y = mouse_y
                    self.scroll_drag_start_scroll = self.scroll_y
                    return True

                elif (self.rect.right - self.resize_margin <= mouse_x <= self.rect.right + self.resize_margin and
                      self.rect.bottom - self.resize_margin <= mouse_y <= self.rect.bottom + self.resize_margin):
                    self.resizing = True
                    return True

                title_rect = pygame.Rect(self.rect.x, self.rect.y, self.rect.width, 30)
                if title_rect.collidepoint(mouse_x, mouse_y):
                    self.dragging = True
                    self.drag_start_x = mouse_x - self.rect.x
                    self.drag_start_y = mouse_y - self.rect.y
                    return True

                if self.focused:
                    return self._handle_tile_selection(mouse_x, mouse_y)

            elif event.button == 4 and self.focused:
                self.scroll_y = max(0, self.scroll_y - 30)
                return True
            elif event.button == 5 and self.focused:
                self.scroll_y = min(self.max_scroll, self.scroll_y + 30)
                return True

        elif event.type == pygame.MOUSEBUTTONUP:
            if event.button == 1:
                self.resizing = False
                self.dragging = False
                self.scroll_dragging = False

        elif event.type == pygame.MOUSEMOTION:
            if self.scroll_dragging:
                delta_y = mouse_y - self.scroll_drag_start_y
                visible_height = self.rect.height - 35
                scrollbar_height = max(30, visible_height * (visible_height / (visible_height + self.max_scroll)))
                scroll_ratio = (visible_height - scrollbar_height) / self.max_scroll if self.max_scroll > 0 else 1
                scroll_delta = delta_y / scroll_ratio if scroll_ratio > 0 else 0
                self.scroll_y = max(0, min(self.max_scroll, self.scroll_drag_start_scroll + scroll_delta))
                return True
            elif self.resizing:
                new_width = max(self.min_width, mouse_x - self.rect.x)
                new_height = max(self.min_height, mouse_y - self.rect.y)
                self.rect.width = new_width
                self.rect.height = new_height
                self._update_max_scroll()
                return True
            elif self.dragging:
                self.rect.x = mouse_x - self.drag_start_x
                self.rect.y = mouse_y - self.drag_start_y
                return True

        elif event.type == pygame.KEYDOWN and self.focused:
            return self._handle_shortcuts(event)

        return False

    def _is_mouse_on_scrollbar(self, mouse_x, mouse_y):
        if not self.focused or self.max_scroll <= 0:
            return False

        scrollbar_rect = pygame.Rect(
            self.rect.x + self.rect.width - 15,
            self.rect.y + 35,
            10,
            self.rect.height - 35
        )
        return scrollbar_rect.collidepoint(mouse_x, mouse_y)

    def _handle_tile_selection(self, mouse_x, mouse_y):
        """Processa a seleção de um tile - garante índice inteiro"""
        local_x = mouse_x - self.rect.x - 5
        local_y = mouse_y - self.rect.y - 35 + self.scroll_y

        col = int(local_x // (self.tile_size + self.tile_spacing))
        row = int(local_y // (self.tile_size + self.tile_spacing))

        if 0 <= col < self.cols:
            tile_index = int(row * self.cols + col)
            if 0 <= tile_index < len(self.tiles):
                self.selected_tile = tile_index
                return True
        return False

    def _handle_shortcuts(self, event):
        if event.key == pygame.K_PLUS or event.key == pygame.K_EQUALS:
            if pygame.key.get_mods() & pygame.KMOD_CTRL:
                self.tile_size = min(self.max_tile_size, self.tile_size + 8)
                self._update_max_scroll()
                return True
        elif event.key == pygame.K_MINUS:
            if pygame.key.get_mods() & pygame.KMOD_CTRL:
                self.tile_size = max(self.min_tile_size, self.tile_size - 8)
                self._update_max_scroll()
                return True
        return False

    def render(self, screen):
        if not self.visible:
            return

        self._render_background(screen)
        self._render_title(screen)
        self._render_tiles(screen)
        self._render_scrollbar(screen)
        self._render_resize_handle(screen)
        self._render_current_tile_selector(screen)

    def _render_background(self, screen):
        shadow_rect = self.rect.copy()
        shadow_rect.x += 3
        shadow_rect.y += 3
        pygame.draw.rect(screen, (20, 20, 30), shadow_rect, border_radius=8)

        if self.focused:
            bg_color = (60, 60, 75)
            border_color = (140, 140, 160)
        else:
            bg_color = (45, 45, 55)
            border_color = (90, 90, 100)

        pygame.draw.rect(screen, bg_color, self.rect, border_radius=8)
        pygame.draw.rect(screen, border_color, self.rect, 2, border_radius=8)

    def _render_title(self, screen):
        title_font = pygame.font.Font(None, 20)
        title = title_font.render("TILES (6x8)", True, (255, 255, 255))
        screen.blit(title, (self.rect.x + 10, self.rect.y + 5))

        num_tilesets = len(self.tileset_boundaries) if self.tileset_boundaries else (1 if self.tiles else 0)
        info_text = f"{self.tile_size}px | {num_tilesets} sets | {len(self.tiles)} tiles"
        info = title_font.render(info_text, True, (200, 200, 200))
        screen.blit(info, (self.rect.x + self.rect.width - 140, self.rect.y + 5))

        if self.focused:
            hint_font = pygame.font.Font(None, 14)
            hint = hint_font.render("Ctrl + ± :size | Scroll: navegar", True, (150, 150, 150))
            screen.blit(hint, (self.rect.x + 10, self.rect.y + 20))

    def _render_tiles(self, screen):
        clip_rect = pygame.Rect(
            self.rect.x + 5,
            self.rect.y + 35,
            self.rect.width - 10,
            self.rect.height - 40
        )

        old_clip = screen.get_clip()
        screen.set_clip(clip_rect)

        if self.tiles:
            for i, tile in enumerate(self.tiles):
                row = i // self.cols
                col = i % self.cols

                tile_x = self.rect.x + 5 + col * (self.tile_size + self.tile_spacing)
                tile_y = self.rect.y + 35 + row * (self.tile_size + self.tile_spacing) - self.scroll_y

                if tile_y + self.tile_size > self.rect.y + 35 and tile_y < self.rect.y + self.rect.height:

                    # Linha separadora entre tilesets
                    if self.tileset_boundaries and i in self.tileset_boundaries and i > 0:
                        line_y = tile_y - 3
                        if line_y > self.rect.y + 35:
                            line_rect = pygame.Rect(self.rect.x + 5, line_y, self.rect.width - 10, 2)
                            pygame.draw.rect(screen, (100, 150, 200), line_rect)

                            ts_num = self.tileset_boundaries.index(i) + 1
                            font = pygame.font.Font(None, 10)
                            ts_text = font.render(f"Set {ts_num}", True, (100, 150, 200))
                            screen.blit(ts_text, (self.rect.x + 10, line_y - 8))

                    if i == self.selected_tile:
                        highlight_rect = pygame.Rect(
                            tile_x - 2,
                            tile_y - 2,
                            self.tile_size + 4,
                            self.tile_size + 4
                        )
                        pygame.draw.rect(screen, (255, 255, 0), highlight_rect, 2, border_radius=4)

                    if tile.get_width() != self.tile_size or tile.get_height() != self.tile_size:
                        scaled_tile = pygame.transform.scale(tile, (self.tile_size, self.tile_size))
                        screen.blit(scaled_tile, (tile_x, tile_y))
                    else:
                        screen.blit(tile, (tile_x, tile_y))

                    if self.tile_size >= 24:
                        font = pygame.font.Font(None, 10)
                        num_text = font.render(str(i + 1), True, (255, 255, 255, 128))
                        screen.blit(num_text, (tile_x + 2, tile_y + 2))
        else:
            no_tiles_font = pygame.font.Font(None, 16)
            msg = no_tiles_font.render("CTRL+I para importar", True, (150, 150, 150))
            msg_x = self.rect.x + (self.rect.width - msg.get_width()) // 2
            msg_y = self.rect.y + (self.rect.height - msg.get_height()) // 2
            screen.blit(msg, (msg_x, msg_y))

        screen.set_clip(old_clip)

    def _render_current_tile_selector(self, screen):
        """Renderiza o seletor do tile atual com setas"""
        if not self.tiles:
            return

        selector_y = self.rect.y + self.rect.height - 35
        selector_height = 30

        pygame.draw.rect(screen, (30, 30, 40),
                         (self.rect.x + 5, selector_y, self.rect.width - 10, selector_height),
                         border_radius=5)

        font = pygame.font.Font(None, 12)
        title = font.render("TILE ATUAL", True, (180, 180, 180))
        screen.blit(title, (self.rect.x + 10, selector_y + 3))

        left_btn = pygame.Rect(self.rect.x + self.rect.width - 55, selector_y + 4, 20, 22)
        right_btn = pygame.Rect(self.rect.x + self.rect.width - 30, selector_y + 4, 20, 22)

        left_color = (80, 80, 90) if self.focused else (60, 60, 70)
        right_color = (80, 80, 90) if self.focused else (60, 60, 70)

        pygame.draw.rect(screen, left_color, left_btn, border_radius=3)
        pygame.draw.rect(screen, right_color, right_btn, border_radius=3)

        left_text = font.render("<", True, (255, 255, 255))
        right_text = font.render(">", True, (255, 255, 255))

        screen.blit(left_text, (left_btn.x + 6, left_btn.y + 4))
        screen.blit(right_text, (right_btn.x + 6, right_btn.y + 4))

        preview_x = self.rect.x + self.rect.width - 90
        preview_y = selector_y + 3
        preview_size = 24

        pygame.draw.rect(screen, (20, 20, 30),
                         (preview_x, preview_y, preview_size, preview_size), border_radius=3)
        pygame.draw.rect(screen, (100, 100, 100),
                         (preview_x, preview_y, preview_size, preview_size), 1, border_radius=3)

        # GARANTE QUE selected_tile É INTEIRO
        selected_idx = int(self.selected_tile) if isinstance(self.selected_tile, float) else self.selected_tile

        if 0 <= selected_idx < len(self.tiles):
            tile = self.tiles[selected_idx]
            scaled_tile = pygame.transform.scale(tile, (preview_size, preview_size))
            screen.blit(scaled_tile, (preview_x, preview_y))

        # Mostra posição na grade
        row = selected_idx // self.cols
        col = selected_idx % self.cols
        pos_text = font.render(f"({col + 1},{row + 1})", True, (200, 200, 200))
        screen.blit(pos_text, (preview_x - 45, preview_y + 6))

        # Mostra qual tileset pertence
        if self.tileset_boundaries:
            ts_index = 0
            for i, boundary in enumerate(self.tileset_boundaries):
                if selected_idx >= boundary:
                    ts_index = i + 1
            ts_text = font.render(f"S{ts_index}", True, (100, 150, 200))
            screen.blit(ts_text, (preview_x - 25, preview_y + 6))

        num_text = font.render(f"#{selected_idx + 1}", True, (200, 200, 200))
        screen.blit(num_text, (preview_x - 35, preview_y + 6))

        self.left_button_rect = left_btn
        self.right_button_rect = right_btn

    def handle_current_tile_buttons(self, mouse_pos):
        """Processa cliques nos botões de seleção do tile atual"""
        if not self.visible or not self.tiles:
            return False

        if hasattr(self, 'left_button_rect') and self.left_button_rect.collidepoint(mouse_pos):
            self.selected_tile = (self.selected_tile - 1) % len(self.tiles)
            return True

        if hasattr(self, 'right_button_rect') and self.right_button_rect.collidepoint(mouse_pos):
            self.selected_tile = (self.selected_tile + 1) % len(self.tiles)
            return True

        return False

    def _render_scrollbar(self, screen):
        if not self.focused or self.max_scroll <= 0:
            return

        visible_height = self.rect.height - 35
        scrollbar_height = max(30, visible_height * (visible_height / (visible_height + self.max_scroll)))
        scroll_ratio = self.scroll_y / self.max_scroll if self.max_scroll > 0 else 0
        scrollbar_y = self.rect.y + 35 + scroll_ratio * (visible_height - scrollbar_height)

        scrollbar_bg = pygame.Rect(
            self.rect.x + self.rect.width - 15,
            self.rect.y + 35,
            10,
            visible_height
        )
        pygame.draw.rect(screen, (70, 70, 80), scrollbar_bg)
        pygame.draw.rect(screen, (90, 90, 100), scrollbar_bg, 1)

        scrollbar = pygame.Rect(
            self.rect.x + self.rect.width - 15,
            scrollbar_y,
            10,
            scrollbar_height
        )
        bar_color = (180, 180, 200) if self.scroll_dragging else (130, 130, 150)
        pygame.draw.rect(screen, bar_color, scrollbar)
        pygame.draw.rect(screen, (200, 200, 220), scrollbar, 1)

    def _render_resize_handle(self, screen):
        resize_handle = pygame.Rect(
            self.rect.right - 15,
            self.rect.bottom - 15,
            10,
            10
        )
        pygame.draw.rect(screen, (150, 150, 150), resize_handle)
        pygame.draw.line(screen, (200, 200, 200),
                         (resize_handle.x + 2, resize_handle.bottom - 2),
                         (resize_handle.right - 2, resize_handle.y + 2), 2)