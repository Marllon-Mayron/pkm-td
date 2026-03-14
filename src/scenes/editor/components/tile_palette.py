# src/scenes/editor/components/tile_palette.py

import pygame


class TilePalette:
    def __init__(self, x, y, width, height):
        self.rect = pygame.Rect(x, y, width, height)
        self.tiles = []
        self.selected_tile = 0
        self.scroll_y = 0
        self.max_scroll = 0
        self.tile_size = 16
        self.visible = True
        self.focused = False

        # Configurações de visualização
        self.cols = 4
        self.tile_spacing = 4
        self.min_tile_size = 16
        self.max_tile_size = 64

        # Para redimensionamento
        self.resizing = False
        self.resize_margin = 10
        self.min_width = 100
        self.min_height = 150

        # Para arrastar
        self.dragging = False
        self.drag_start_x = 0
        self.drag_start_y = 0
        self.original_x = x
        self.original_y = y

        # NOVO: Para arrastar a barra de scroll
        self.scroll_dragging = False
        self.scroll_drag_start_y = 0
        self.scroll_drag_start_scroll = 0

    def set_tileset(self, tileset):
        """Define o tileset e atualiza a palette"""
        self.tiles = tileset
        self.selected_tile = 0
        self._update_max_scroll()

    def _update_max_scroll(self):
        """Atualiza o limite máximo de scroll"""
        if not self.tiles:
            self.max_scroll = 0
            return

        rows = (len(self.tiles) + self.cols - 1) // self.cols
        content_height = rows * (self.tile_size + self.tile_spacing)
        visible_height = self.rect.height - 40
        self.max_scroll = max(0, content_height - visible_height)
        # Garante que scroll não ultrapasse o limite
        self.scroll_y = max(0, min(self.scroll_y, self.max_scroll))

    def handle_event(self, event):
        """Processa eventos da palette"""
        if not self.visible:
            return False

        mouse_pos = pygame.mouse.get_pos()
        mouse_x, mouse_y = mouse_pos

        # Verifica se o mouse está sobre a palette
        self.focused = self.rect.collidepoint(mouse_x, mouse_y)

        if event.type == pygame.MOUSEBUTTONDOWN:
            if event.button == 1:
                # Verifica se clicou na barra de scroll
                if self._is_mouse_on_scrollbar(mouse_x, mouse_y):
                    self.scroll_dragging = True
                    self.scroll_drag_start_y = mouse_y
                    self.scroll_drag_start_scroll = self.scroll_y
                    return True

                # Redimensionamento
                elif (self.rect.right - self.resize_margin <= mouse_x <= self.rect.right + self.resize_margin and
                      self.rect.bottom - self.resize_margin <= mouse_y <= self.rect.bottom + self.resize_margin):
                    self.resizing = True
                    return True

                # Arrastar pelo título
                title_rect = pygame.Rect(self.rect.x, self.rect.y, self.rect.width, 30)
                if title_rect.collidepoint(mouse_x, mouse_y):
                    self.dragging = True
                    self.drag_start_x = mouse_x - self.rect.x
                    self.drag_start_y = mouse_y - self.rect.y
                    return True

                # Seleção de tile
                if self.focused:
                    return self._handle_tile_selection(mouse_x, mouse_y)

            elif event.button == 4 and self.focused:  # Scroll up
                self.scroll_y = max(0, self.scroll_y - 30)
                return True
            elif event.button == 5 and self.focused:  # Scroll down
                self.scroll_y = min(self.max_scroll, self.scroll_y + 30)
                return True

        elif event.type == pygame.MOUSEBUTTONUP:
            if event.button == 1:
                self.resizing = False
                self.dragging = False
                self.scroll_dragging = False  # Para de arrastar scroll

        elif event.type == pygame.MOUSEMOTION:
            if self.scroll_dragging:
                # Arrasta a barra de scroll
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
        """Verifica se o mouse está sobre a barra de scroll"""
        if not self.focused or self.max_scroll <= 0:
            return False

        # Área da barra de scroll
        scrollbar_rect = pygame.Rect(
            self.rect.x + self.rect.width - 15,
            self.rect.y + 35,
            10,
            self.rect.height - 35
        )

        return scrollbar_rect.collidepoint(mouse_x, mouse_y)

    def _handle_tile_selection(self, mouse_x, mouse_y):
        """Processa a seleção de um tile"""
        local_x = mouse_x - self.rect.x - 5
        local_y = mouse_y - self.rect.y - 35 + self.scroll_y

        col = local_x // (self.tile_size + self.tile_spacing)
        row = local_y // (self.tile_size + self.tile_spacing)

        if 0 <= col < self.cols:
            tile_index = row * self.cols + col
            if 0 <= tile_index < len(self.tiles):
                self.selected_tile = tile_index
                return True
        return False

    def _handle_shortcuts(self, event):
        """Processa atalhos de teclado"""
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
        elif event.key in [pygame.K_1, pygame.K_2, pygame.K_3, pygame.K_4, pygame.K_5, pygame.K_6]:
            if pygame.key.get_mods() & pygame.KMOD_CTRL:
                self.cols = event.key - pygame.K_0
                self._update_max_scroll()
                return True
        return False

    def render(self, screen):
        """Renderiza a palette"""
        if not self.visible:
            return

        self._render_background(screen)
        self._render_title(screen)
        self._render_tiles(screen)
        self._render_scrollbar(screen)
        self._render_resize_handle(screen)

    def _render_background(self, screen):
        """Renderiza o fundo da palette"""
        # Sombra
        shadow_rect = self.rect.copy()
        shadow_rect.x += 3
        shadow_rect.y += 3
        pygame.draw.rect(screen, (20, 20, 30), shadow_rect, border_radius=8)

        # Fundo principal
        if self.focused:
            bg_color = (60, 60, 75)
            border_color = (140, 140, 160)
        else:
            bg_color = (45, 45, 55)
            border_color = (90, 90, 100)

        pygame.draw.rect(screen, bg_color, self.rect, border_radius=8)
        pygame.draw.rect(screen, border_color, self.rect, 2, border_radius=8)

    def _render_title(self, screen):
        """Renderiza o título e informações"""
        title_font = pygame.font.Font(None, 20)
        title = title_font.render("TILES", True, (255, 255, 255))
        screen.blit(title, (self.rect.x + 10, self.rect.y + 5))

        info_text = f"{self.tile_size}px | {self.cols}col"
        info = title_font.render(info_text, True, (200, 200, 200))
        screen.blit(info, (self.rect.x + self.rect.width - 70, self.rect.y + 5))

        if self.focused:
            hint_font = pygame.font.Font(None, 14)
            hint = hint_font.render("Ctrl + 1-6 :cols | Ctrl + ± :size", True, (150, 150, 150))
            screen.blit(hint, (self.rect.x + 10, self.rect.y + 20))

    def _render_tiles(self, screen):
        """Renderiza os tiles"""
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
        else:
            no_tiles_font = pygame.font.Font(None, 16)
            msg = no_tiles_font.render("CTRL+I para importar", True, (150, 150, 150))
            msg_x = self.rect.x + (self.rect.width - msg.get_width()) // 2
            msg_y = self.rect.y + (self.rect.height - msg.get_height()) // 2
            screen.blit(msg, (msg_x, msg_y))

        screen.set_clip(old_clip)

    def _render_scrollbar(self, screen):
        """Renderiza a barra de scroll"""
        if not self.focused or self.max_scroll <= 0:
            return

        visible_height = self.rect.height - 35
        scrollbar_height = max(30, visible_height * (visible_height / (visible_height + self.max_scroll)))

        # Calcula posição Y da barra baseada no scroll atual
        scroll_ratio = self.scroll_y / self.max_scroll if self.max_scroll > 0 else 0
        scrollbar_y = self.rect.y + 35 + scroll_ratio * (visible_height - scrollbar_height)

        # Fundo da scrollbar
        scrollbar_bg = pygame.Rect(
            self.rect.x + self.rect.width - 15,
            self.rect.y + 35,
            10,
            visible_height
        )
        pygame.draw.rect(screen, (70, 70, 80), scrollbar_bg)
        pygame.draw.rect(screen, (90, 90, 100), scrollbar_bg, 1)

        # Barra de scroll propriamente dita
        scrollbar = pygame.Rect(
            self.rect.x + self.rect.width - 15,
            scrollbar_y,
            10,
            scrollbar_height
        )

        # Cor diferente se estiver arrastando
        if self.scroll_dragging:
            bar_color = (180, 180, 200)
        else:
            bar_color = (130, 130, 150)

        pygame.draw.rect(screen, bar_color, scrollbar)
        pygame.draw.rect(screen, (200, 200, 220), scrollbar, 1)

    def _render_resize_handle(self, screen):
        """Renderiza a alça de redimensionamento"""
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