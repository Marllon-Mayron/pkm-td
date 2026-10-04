# src/scenes/editor/components/tile_palette.py

"""
Paleta de tiles do editor.

Recursos:
- Duas abas: TILES (tileset normal) e AUTOTILES (47-tile blob)
- Grade com número de COLUNAS configurável pelo usuário (botões [−]/[+]/[A])
- Modo single (1x1) e modo multi (seleção por arrasto, ex: árvore 3x3)
- Suporta QUALQUER tamanho de tileset (não há mais 6x8 fixo)
- Zoom com Ctrl +/−
- Scroll com roda, arraste da barra ou arraste da grade
"""

import pygame


class TilePalette:
    # Layout
    TITLE_HEIGHT = 24
    TAB_HEIGHT = 22
    CONTROLS_HEIGHT = 26
    FOOTER_HEIGHT = 40

    def __init__(self, x, y, width, height):
        self.rect = pygame.Rect(x, y, width, height)
        self.tiles = []
        self.selected_tile = 0
        self.scroll_y = 0
        self.max_scroll = 0
        self.tile_size = 16
        self.visible = True
        self.focused = False

        # ===== Colunas configuráveis =====
        self.cols = 6                 # colunas exibidas
        self.natural_cols = 6         # colunas do tileset de origem (auto)
        self.min_cols = 1
        self.max_cols = 40
        self._cols_user_customized = False  # se True, "A" não sobrescreve

        # ===== Multi-seleção =====
        self.selection_mode = "single"     # "single" | "multi"
        self.is_selecting = False
        self.selection_start = None        # (col, row)
        self.selection_end = None          # (col, row)
        self.multi_selection = None        # [{'dx','dy','tile_id'}, ...]
        self.multi_selection_bounds = None # (min_c, min_r, max_c, max_r)
        self.multi_selection_size = (0, 0) # (w, h) em tiles

        # ===== Spacing / tamanho =====
        self.tile_spacing = 2
        self.min_tile_size = 12
        self.max_tile_size = 48

        # ===== Separadores entre arquivos de tileset =====
        self.tileset_boundaries = []

        # ===== Redimensionamento / arraste =====
        self.resizing = False
        self.resize_margin = 10
        self.min_width = 220
        self.min_height = 320

        self.dragging = False
        self.drag_start_x = 0
        self.drag_start_y = 0

        self.scroll_dragging = False
        self.scroll_drag_start_y = 0
        self.scroll_drag_start_scroll = 0

        # Botões dos controles (calculados em _update_button_positions)
        self.cols_minus_rect = pygame.Rect(0, 0, 0, 0)
        self.cols_value_rect = pygame.Rect(0, 0, 0, 0)
        self.cols_plus_rect = pygame.Rect(0, 0, 0, 0)
        self.cols_auto_rect = pygame.Rect(0, 0, 0, 0)
        self.mode_single_rect = pygame.Rect(0, 0, 0, 0)
        self.mode_multi_rect = pygame.Rect(0, 0, 0, 0)
        self.clear_sel_rect = pygame.Rect(0, 0, 0, 0)
        self.cols_label_x = 0
        self.mode_label_x = 0

        self.hovered_control = None

        # Botões do rodapé
        self.left_button_rect = pygame.Rect(0, 0, 0, 0)
        self.right_button_rect = pygame.Rect(0, 0, 0, 0)

        # ===== ABAS =====
        self.active_tab = "tiles"        # "tiles" | "autotiles"
        self.tab_tiles_rect = pygame.Rect(0, 0, 0, 0)
        self.tab_auto_rect = pygame.Rect(0, 0, 0, 0)

        # ===== AUTOTILE =====
        self.autotile_manager = None
        self.selected_autotile_id = 0    # local_id
        self.autotile_scroll = 0
        self.autotile_max_scroll = 0
        self.autotile_cell_size = 32
        self.autotile_cols = 4

        self._update_button_positions()

    # =========================================================
    # LAYOUT
    # =========================================================
    def _header_height(self):
        return self.TITLE_HEIGHT + self.TAB_HEIGHT + self.CONTROLS_HEIGHT

    def _grid_rect(self):
        return pygame.Rect(
            self.rect.x + 5,
            self.rect.y + self._header_height(),
            self.rect.width - 10,
            self.rect.height - self._header_height() - self.FOOTER_HEIGHT,
        )

    def _update_button_positions(self):
        # ===== Abas =====
        tab_y = self.rect.y + self.TITLE_HEIGHT
        tab_h = self.TAB_HEIGHT - 2
        half_w = (self.rect.width - 12) // 2
        self.tab_tiles_rect = pygame.Rect(self.rect.x + 4, tab_y, half_w, tab_h)
        self.tab_auto_rect = pygame.Rect(self.rect.x + 8 + half_w, tab_y, half_w, tab_h)

        # ===== Controles (linha abaixo das abas) =====
        y = self.rect.y + self.TITLE_HEIGHT + self.TAB_HEIGHT + 2
        h = self.CONTROLS_HEIGHT - 4
        x = self.rect.x + 6

        # Colunas
        self.cols_label_x = x
        x += 34

        self.cols_minus_rect = pygame.Rect(x, y, 18, h); x += 20
        self.cols_value_rect = pygame.Rect(x, y, 26, h); x += 28
        self.cols_plus_rect  = pygame.Rect(x, y, 18, h); x += 20
        self.cols_auto_rect  = pygame.Rect(x, y, 22, h); x += 28

        # Modo
        self.mode_label_x = x
        x += 40
        self.mode_single_rect = pygame.Rect(x, y, 22, h); x += 24
        self.mode_multi_rect  = pygame.Rect(x, y, 22, h); x += 26

        # Limpar seleção
        self.clear_sel_rect = pygame.Rect(x, y, 22, h)

    # =========================================================
    # ABAS
    # =========================================================
    def get_active_tab(self):
        return self.active_tab

    def set_autotile_manager(self, mgr):
        self.autotile_manager = mgr
        self._update_autotile_scroll()

    def _update_autotile_scroll(self):
        if not self.autotile_manager:
            self.autotile_max_scroll = 0
            return
        n = len(self.autotile_manager.sheets)
        rows = (n + self.autotile_cols - 1) // self.autotile_cols
        content_h = rows * (self.autotile_cell_size + 6)
        self.autotile_max_scroll = max(0, content_h - self._grid_rect().height)
        self.autotile_scroll = max(0, min(self.autotile_scroll, self.autotile_max_scroll))

    # =========================================================
    # TILESET
    # =========================================================
    def set_tileset(self, tileset, tileset_boundaries=None, natural_cols=None):

        self.tiles = tileset
        self.tileset_boundaries = tileset_boundaries or []
        self.selected_tile = 0

        if natural_cols is not None and natural_cols > 0:
            self.natural_cols = int(natural_cols)
            # Só sobrescreve self.cols se o usuário nunca mexeu
            if not self._cols_user_customized:
                self.cols = self.natural_cols

        self._update_max_scroll()

    def set_cols(self, cols, user_customized=True):
        cols = max(self.min_cols, min(self.max_cols, int(cols)))
        if cols == self.cols:
            return
        self.cols = cols
        if user_customized:
            self._cols_user_customized = True
        self._update_max_scroll()

    def _update_max_scroll(self):
        if not self.tiles:
            self.max_scroll = 0
            self.scroll_y = 0
            return
        cols = max(1, self.cols)
        rows = (len(self.tiles) + cols - 1) // cols
        content_height = rows * (self.tile_size + self.tile_spacing)
        visible_height = self._grid_rect().height
        self.max_scroll = max(0, content_height - visible_height)
        self.scroll_y = max(0, min(self.scroll_y, self.max_scroll))

    # =========================================================
    # EVENTOS
    # =========================================================
    def handle_event(self, event):
        if not self.visible:
            return False

        mouse_x, mouse_y = pygame.mouse.get_pos()
        self.focused = self.rect.collidepoint(mouse_x, mouse_y)

        # ===== CLIQUES NAS ABAS =====
        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            # ===== LOG TEMPORÁRIO =====
            print(f"[PALETTE] click at ({mouse_x},{mouse_y}) "
                  f"tiles_rect={self.tab_tiles_rect} auto_rect={self.tab_auto_rect}")

            if self.tab_tiles_rect.collidepoint(mouse_x, mouse_y):
                print(f"[PALETTE] -> TILES")
                self.active_tab = "tiles"
                return True
            if self.tab_auto_rect.collidepoint(mouse_x, mouse_y):
                print(f"[PALETTE] -> AUTOTILES")
                self.active_tab = "autotiles"
                self._update_autotile_scroll()
                return True

        # ===== ABA AUTOTILES: scroll + seleção =====
        if self.active_tab == "autotiles":
            if event.type == pygame.MOUSEBUTTONDOWN and self.focused:
                if event.button == 4:
                    self.autotile_scroll = max(0, self.autotile_scroll - 24)
                    return True
                if event.button == 5:
                    self.autotile_scroll = min(self.autotile_max_scroll,
                                                self.autotile_scroll + 24)
                    return True

            # Clique na grade de autotiles
            if (event.type == pygame.MOUSEBUTTONDOWN and event.button == 1
                    and self._grid_rect().collidepoint(mouse_x, mouse_y)):
                grid = self._grid_rect()
                local_x = mouse_x - grid.x
                local_y = mouse_y - grid.y + self.autotile_scroll
                cell = self.autotile_cell_size + 6
                col = local_x // cell
                row = local_y // cell
                idx = row * self.autotile_cols + col
                if 0 <= col < self.autotile_cols and self.autotile_manager:
                    ids = self.autotile_manager.list_ids()
                    if 0 <= idx < len(ids):
                        self.selected_autotile_id = ids[idx]
                        return True

            # Arrastar / resize continuam válidos nas abas
            if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                # resize pelo canto
                if (self.rect.right - self.resize_margin <= mouse_x <= self.rect.right + self.resize_margin and
                        self.rect.bottom - self.resize_margin <= mouse_y <= self.rect.bottom + self.resize_margin):
                    self.resizing = True
                    return True
                # arrastar pela barra de título
                title_rect = pygame.Rect(self.rect.x, self.rect.y, self.rect.width, self.TITLE_HEIGHT)
                if title_rect.collidepoint(mouse_x, mouse_y):
                    self.dragging = True
                    self.drag_start_x = mouse_x - self.rect.x
                    self.drag_start_y = mouse_y - self.rect.y
                    return True

            if event.type == pygame.MOUSEBUTTONUP and event.button == 1:
                self.resizing = False
                self.dragging = False

            if event.type == pygame.MOUSEMOTION:
                if self.resizing:
                    self.rect.width = max(self.min_width, mouse_x - self.rect.x)
                    self.rect.height = max(self.min_height, mouse_y - self.rect.y)
                    self._update_button_positions()
                    return True
                if self.dragging:
                    self.rect.x = mouse_x - self.drag_start_x
                    self.rect.y = mouse_y - self.drag_start_y
                    self._update_button_positions()
                    return True
            return False

        # ===== ABA TILES: comportamento original =====
        self._update_control_hover(mouse_x, mouse_y)

        if event.type == pygame.MOUSEBUTTONDOWN:
            if event.button == 1:
                return self._handle_left_down(mouse_x, mouse_y)
            elif event.button == 4 and self.focused:
                self.scroll_y = max(0, self.scroll_y - 30)
                return True
            elif event.button == 5 and self.focused:
                self.scroll_y = min(self.max_scroll, self.scroll_y + 30)
                return True

        elif event.type == pygame.MOUSEBUTTONUP:
            if event.button == 1:
                self._handle_left_up(mouse_x, mouse_y)
                self.resizing = False
                self.dragging = False
                self.scroll_dragging = False

        elif event.type == pygame.MOUSEMOTION:
            return self._handle_motion(mouse_x, mouse_y)

        elif event.type == pygame.KEYDOWN and self.focused:
            return self._handle_shortcuts(event)

        return False

    def _handle_left_down(self, mouse_x, mouse_y):
        # 1) Controles
        if self._handle_control_click(mouse_x, mouse_y):
            return True

        # 2) Scrollbar
        if self._is_mouse_on_scrollbar(mouse_x, mouse_y):
            self.scroll_dragging = True
            self.scroll_drag_start_y = mouse_y
            self.scroll_drag_start_scroll = self.scroll_y
            return True

        # 3) Resize
        if (self.rect.right - self.resize_margin <= mouse_x <= self.rect.right + self.resize_margin and
                self.rect.bottom - self.resize_margin <= mouse_y <= self.rect.bottom + self.resize_margin):
            self.resizing = True
            return True

        # 4) Arraste pela barra de título
        title_rect = pygame.Rect(self.rect.x, self.rect.y, self.rect.width, self.TITLE_HEIGHT)
        if title_rect.collidepoint(mouse_x, mouse_y):
            self.dragging = True
            self.drag_start_x = mouse_x - self.rect.x
            self.drag_start_y = mouse_y - self.rect.y
            return True

        # 5) Grade de tiles
        if self._grid_rect().collidepoint(mouse_x, mouse_y):
            if self.selection_mode == "single":
                return self._handle_tile_selection(mouse_x, mouse_y)
            else:
                return self._handle_multi_select_start(mouse_x, mouse_y)

        return False

    def _handle_left_up(self, mouse_x, mouse_y):
        if self.is_selecting:
            self._handle_multi_select_end()

    def _handle_motion(self, mouse_x, mouse_y):
        if self.scroll_dragging:
            delta_y = mouse_y - self.scroll_drag_start_y
            visible_height = self._grid_rect().height
            if self.max_scroll > 0 and visible_height > 0:
                scrollbar_height = max(30, visible_height * (visible_height / (visible_height + self.max_scroll)))
                scroll_ratio = (visible_height - scrollbar_height) / self.max_scroll
                if scroll_ratio > 0:
                    scroll_delta = delta_y / scroll_ratio
                    self.scroll_y = max(0, min(self.max_scroll, self.scroll_drag_start_scroll + scroll_delta))
            return True

        if self.resizing:
            new_width = max(self.min_width, mouse_x - self.rect.x)
            new_height = max(self.min_height, mouse_y - self.rect.y)
            self.rect.width = new_width
            self.rect.height = new_height
            self._update_button_positions()
            self._update_max_scroll()
            return True

        if self.dragging:
            self.rect.x = mouse_x - self.drag_start_x
            self.rect.y = mouse_y - self.drag_start_y
            self._update_button_positions()
            return True

        if self.is_selecting:
            return self._handle_multi_select_update(mouse_x, mouse_y)

        return False

    # =========================================================
    # CONTROLES
    # =========================================================
    def _update_control_hover(self, mouse_x, mouse_y):
        self.hovered_control = None
        for rect, name in [
            (self.cols_minus_rect, "cols_minus"),
            (self.cols_plus_rect, "cols_plus"),
            (self.cols_auto_rect, "cols_auto"),
            (self.mode_single_rect, "mode_single"),
            (self.mode_multi_rect, "mode_multi"),
            (self.clear_sel_rect, "clear_sel"),
        ]:
            if rect.collidepoint(mouse_x, mouse_y):
                self.hovered_control = name
                return

    def _handle_control_click(self, mouse_x, mouse_y):
        if self.cols_minus_rect.collidepoint(mouse_x, mouse_y):
            self.set_cols(self.cols - 1); return True
        if self.cols_plus_rect.collidepoint(mouse_x, mouse_y):
            self.set_cols(self.cols + 1); return True
        if self.cols_auto_rect.collidepoint(mouse_x, mouse_y):
            self._cols_user_customized = False
            self.set_cols(self.natural_cols, user_customized=False)
            print(f"[TilePalette] Colunas resetadas para natural: {self.natural_cols}")
            return True
        if self.mode_single_rect.collidepoint(mouse_x, mouse_y):
            self.selection_mode = "single"
            return True
        if self.mode_multi_rect.collidepoint(mouse_x, mouse_y):
            self.selection_mode = "multi"
            return True
        if self.clear_sel_rect.collidepoint(mouse_x, mouse_y):
            self.clear_multi_selection()
            return True
        return False

    # =========================================================
    # GRID / SELEÇÃO
    # =========================================================
    def _mouse_to_grid(self, mouse_x, mouse_y):
        grid = self._grid_rect()
        local_x = mouse_x - grid.x
        local_y = mouse_y - grid.y + self.scroll_y

        cell = self.tile_size + self.tile_spacing
        if cell <= 0:
            return None

        col = int(local_x // cell)
        row = int(local_y // cell)

        if col < 0: col = 0
        if row < 0: row = 0
        if self.cols > 0 and col >= self.cols:
            col = self.cols - 1

        return col, row

    def _handle_tile_selection(self, mouse_x, mouse_y):
        result = self._mouse_to_grid(mouse_x, mouse_y)
        if result is None:
            return False
        col, row = result
        idx = row * self.cols + col
        if 0 <= idx < len(self.tiles):
            self.selected_tile = idx
            return True
        return False

    def _handle_multi_select_start(self, mouse_x, mouse_y):
        result = self._mouse_to_grid(mouse_x, mouse_y)
        if result is None:
            return False
        self.is_selecting = True
        self.selection_start = result
        self.selection_end = result
        return True

    def _handle_multi_select_update(self, mouse_x, mouse_y):
        if not self.is_selecting:
            return False
        result = self._mouse_to_grid(mouse_x, mouse_y)
        if result is None:
            return False
        self.selection_end = result
        return True

    def _handle_multi_select_end(self):
        if not self.is_selecting:
            return False
        if self.selection_start is None or self.selection_end is None:
            self.is_selecting = False
            return False

        c1, r1 = self.selection_start
        c2, r2 = self.selection_end
        min_c, max_c = min(c1, c2), max(c1, c2)
        min_r, max_r = min(r1, r2), max(r1, r2)

        pattern = []
        for r in range(min_r, max_r + 1):
            for c in range(min_c, max_c + 1):
                idx = r * self.cols + c
                if 0 <= idx < len(self.tiles):
                    pattern.append({
                        'dx': c - min_c,
                        'dy': r - min_r,
                        'tile_id': idx + 1,   # IDs são 1-based
                    })

        if pattern:
            self.multi_selection = pattern
            self.multi_selection_bounds = (min_c, min_r, max_c, max_r)
            self.multi_selection_size = (max_c - min_c + 1, max_r - min_r + 1)
            print(f"[TilePalette] Multi-seleção: "
                  f"{self.multi_selection_size[0]}x{self.multi_selection_size[1]} = "
                  f"{len(pattern)} tiles")
        else:
            self.clear_multi_selection()

        self.is_selecting = False
        self.selection_start = None
        self.selection_end = None
        return True

    def clear_multi_selection(self):
        self.multi_selection = None
        self.multi_selection_bounds = None
        self.multi_selection_size = (0, 0)

    # =========================================================
    # API PÚBLICA — CONSULTADA PELO MAP_HANDLER
    # =========================================================
    def get_current_brush_pattern(self):
        """
        Retorna a lista de células do pattern multi-tile
        [{dx, dy, tile_id}, ...] ou None se estiver em modo single.
        """
        if self.selection_mode == "multi" and self.multi_selection:
            return self.multi_selection
        return None

    # =========================================================
    # ATALHOS / SCROLL / HELPERS
    # =========================================================
    def _handle_shortcuts(self, event):
        mods = pygame.key.get_mods()
        if event.key in (pygame.K_PLUS, pygame.K_EQUALS) and (mods & pygame.KMOD_CTRL):
            self.tile_size = min(self.max_tile_size, self.tile_size + 4)
            self._update_max_scroll()
            return True
        if event.key == pygame.K_MINUS and (mods & pygame.KMOD_CTRL):
            self.tile_size = max(self.min_tile_size, self.tile_size - 4)
            self._update_max_scroll()
            return True
        return False

    def _is_mouse_on_scrollbar(self, mouse_x, mouse_y):
        if not self.focused or self.max_scroll <= 0:
            return False
        grid = self._grid_rect()
        sb = pygame.Rect(grid.right - 12, grid.y, 10, grid.height)
        return sb.collidepoint(mouse_x, mouse_y)

    def handle_current_tile_buttons(self, mouse_pos):
        """Setas ‹ › do rodapé (só em modo single)."""
        if not self.visible or not self.tiles:
            return False
        if self.selection_mode != "single":
            return False
        if self.left_button_rect.collidepoint(mouse_pos):
            self.selected_tile = (self.selected_tile - 1) % len(self.tiles)
            return True
        if self.right_button_rect.collidepoint(mouse_pos):
            self.selected_tile = (self.selected_tile + 1) % len(self.tiles)
            return True
        return False

    # =========================================================
    # RENDER
    # =========================================================
    def render(self, screen):
        if not self.visible:
            return
        self._render_background(screen)
        self._render_title(screen)
        self._render_tabs(screen)

        if self.active_tab == "tiles":
            self._render_controls(screen)
            self._render_tiles(screen)
            self._render_selection_overlay(screen)
            self._render_scrollbar(screen)
            self._render_footer(screen)
        else:
            self._render_autotiles(screen)

        self._render_resize_handle(screen)

    def _render_background(self, screen):
        shadow = self.rect.copy()
        shadow.x += 3
        shadow.y += 3
        pygame.draw.rect(screen, (20, 20, 30), shadow, border_radius=8)

        if self.focused:
            bg = (60, 60, 75); border = (140, 140, 160)
        else:
            bg = (45, 45, 55); border = (90, 90, 100)

        pygame.draw.rect(screen, bg, self.rect, border_radius=8)
        pygame.draw.rect(screen, border, self.rect, 2, border_radius=8)

    def _render_title(self, screen):
        font = pygame.font.Font(None, 16)
        title = font.render("TILES", True, (255, 255, 255))
        screen.blit(title, (self.rect.x + 8, self.rect.y + 4))

        num_tilesets = len(self.tileset_boundaries) if self.tileset_boundaries else (1 if self.tiles else 0)
        info = f"{self.tile_size}px  |  {num_tilesets} set(s)  |  {len(self.tiles)} tiles"
        info_surf = font.render(info, True, (200, 200, 200))
        screen.blit(info_surf, (self.rect.x + 55, self.rect.y + 4))

    def _render_tabs(self, screen):
        font = pygame.font.Font(None, 15)
        for rect, label, key in (
            (self.tab_tiles_rect, "TILES", "tiles"),
            (self.tab_auto_rect,  "AUTOTILES", "autotiles"),
        ):
            active = (self.active_tab == key)
            bg = (100, 150, 200) if active else (50, 55, 70)
            border = (200, 220, 255) if active else (90, 95, 110)
            pygame.draw.rect(screen, bg, rect, border_radius=4)
            pygame.draw.rect(screen, border, rect, 1, border_radius=4)
            t = font.render(label, True, (255, 255, 255))
            screen.blit(t, t.get_rect(center=rect.center))

    def _render_autotiles(self, screen):
        if not self.autotile_manager or not self.autotile_manager.sheets:
            font = pygame.font.Font(None, 16)
            msg = font.render("Nenhum autotile carregado", True, (200, 200, 200))
            screen.blit(msg, msg.get_rect(center=self._grid_rect().center))
            return

        grid = self._grid_rect()
        old_clip = screen.get_clip()
        screen.set_clip(grid)

        cell = self.autotile_cell_size
        gap = 6
        step = cell + gap
        ids = self.autotile_manager.list_ids()

        font = pygame.font.Font(None, 13)
        for i, local_id in enumerate(ids):
            col = i % self.autotile_cols
            row = i // self.autotile_cols
            x = grid.x + col * step + gap // 2
            y = grid.y + row * step - self.autotile_scroll + gap // 2

            if y + cell < grid.y or y > grid.bottom:
                continue
            if x + cell < grid.x or x > grid.right:
                continue

            # Preview
            preview = self.autotile_manager.preview(local_id, cell)
            pygame.draw.rect(screen, (30, 32, 42), (x - 2, y - 2, cell + 4, cell + 4))

            if local_id == self.selected_autotile_id:
                pygame.draw.rect(screen, (255, 215, 0),
                                 (x - 3, y - 3, cell + 6, cell + 6), 2)
            else:
                pygame.draw.rect(screen, (90, 95, 110),
                                 (x - 2, y - 2, cell + 4, cell + 4), 1)

            screen.blit(preview, (x, y))

            # Número do local_id
            label = str(local_id)
            t = font.render(label, True, (255, 255, 255))
            bg = pygame.Surface((t.get_width() + 4, t.get_height() + 2), pygame.SRCALPHA)
            bg.fill((0, 0, 0, 180))
            screen.blit(bg, (x + 1, y + 1))
            screen.blit(t, (x + 3, y + 2))

        screen.set_clip(old_clip)

        # Scrollbar
        if self.autotile_max_scroll > 0:
            ratio = self.autotile_scroll / self.autotile_max_scroll
            sb_h = max(20, int(grid.height * 0.4))
            sb_y = grid.y + int((grid.height - sb_h) * ratio)
            pygame.draw.rect(screen, (70, 70, 80),
                             (grid.right - 6, grid.y, 4, grid.height))
            pygame.draw.rect(screen, (150, 150, 160),
                             (grid.right - 6, sb_y, 4, sb_h))

    def _render_controls(self, screen):
        font = pygame.font.Font(None, 14)
        y = self.rect.y + self.TITLE_HEIGHT + self.TAB_HEIGHT + 2

        lbl = font.render("Cols:", True, (200, 200, 200))
        screen.blit(lbl, (self.cols_label_x, y + 4))

        self._draw_button(screen, self.cols_minus_rect, "-", "cols_minus")

        pygame.draw.rect(screen, (30, 34, 44), self.cols_value_rect)
        pygame.draw.rect(screen, (90, 95, 110), self.cols_value_rect, 1)
        v = font.render(str(self.cols), True, (255, 255, 255))
        screen.blit(v, v.get_rect(center=self.cols_value_rect.center))

        self._draw_button(screen, self.cols_plus_rect, "+", "cols_plus")
        self._draw_button(screen, self.cols_auto_rect, "A", "cols_auto",
                          tooltip="Auto (usa colunas do tileset)")

        mlbl = font.render("Mode:", True, (200, 200, 200))
        screen.blit(mlbl, (self.mode_label_x, y + 4))

        # Modo 1x1
        active = self.selection_mode == "single"
        color = (100, 150, 200) if active else ((60, 70, 90) if self.hovered_control == "mode_single" else (40, 45, 60))
        pygame.draw.rect(screen, color, self.mode_single_rect, border_radius=3)
        pygame.draw.rect(screen, (150, 150, 160), self.mode_single_rect, 1, border_radius=3)
        screen.blit(font.render("1", True, (255, 255, 255)),
                    font.render("1", True, (255, 255, 255)).get_rect(center=self.mode_single_rect.center))

        # Modo NxN
        active = self.selection_mode == "multi"
        color = (100, 150, 200) if active else ((60, 70, 90) if self.hovered_control == "mode_multi" else (40, 45, 60))
        pygame.draw.rect(screen, color, self.mode_multi_rect, border_radius=3)
        pygame.draw.rect(screen, (150, 150, 160), self.mode_multi_rect, 1, border_radius=3)
        screen.blit(font.render("N", True, (255, 255, 255)),
                    font.render("N", True, (255, 255, 255)).get_rect(center=self.mode_multi_rect.center))

        # Limpar seleção (só quando tem pattern)
        if self.multi_selection:
            color = (150, 60, 60) if self.hovered_control == "clear_sel" else (100, 40, 40)
            pygame.draw.rect(screen, color, self.clear_sel_rect, border_radius=3)
            pygame.draw.rect(screen, (180, 100, 100), self.clear_sel_rect, 1, border_radius=3)
            screen.blit(font.render("X", True, (255, 255, 255)),
                        font.render("X", True, (255, 255, 255)).get_rect(center=self.clear_sel_rect.center))

    def _draw_button(self, screen, rect, label, name, tooltip=None):
        hovered = self.hovered_control == name
        color = (70, 85, 110) if hovered else (40, 45, 60)
        pygame.draw.rect(screen, color, rect, border_radius=3)
        pygame.draw.rect(screen, (120, 125, 140), rect, 1, border_radius=3)
        font = pygame.font.Font(None, 14)
        t = font.render(label, True, (255, 255, 255))
        screen.blit(t, t.get_rect(center=rect.center))

    def _render_tiles(self, screen):
        grid = self._grid_rect()
        old_clip = screen.get_clip()
        screen.set_clip(grid)

        if not self.tiles:
            font = pygame.font.Font(None, 16)
            msg = font.render("CTRL+I para importar", True, (150, 150, 150))
            screen.blit(msg, msg.get_rect(center=grid.center))
            screen.set_clip(old_clip)
            return

        cell = self.tile_size + self.tile_spacing
        cols = max(1, self.cols)

        for i, tile in enumerate(self.tiles):
            row = i // cols
            col = i % cols

            tile_x = grid.x + col * cell
            tile_y = grid.y + row * cell - self.scroll_y

            if tile_y + self.tile_size < grid.y or tile_y > grid.bottom:
                continue
            if tile_x + self.tile_size < grid.x or tile_x > grid.right:
                continue

            # Separador entre tilesets
            if self.tileset_boundaries and i in self.tileset_boundaries and i > 0 and col == 0:
                line_y = tile_y - 2
                if line_y > grid.y:
                    pygame.draw.line(screen, (100, 150, 200),
                                     (grid.x, line_y), (grid.right, line_y), 1)
                    f = pygame.font.Font(None, 10)
                    ts_num = self.tileset_boundaries.index(i) + 1
                    screen.blit(f.render(f"Set {ts_num}", True, (100, 150, 200)),
                                (grid.x + 2, line_y - 10))

            # Highlight single
            if self.selection_mode == "single" and i == self.selected_tile:
                pygame.draw.rect(screen, (255, 255, 0),
                                 (tile_x - 2, tile_y - 2, self.tile_size + 4, self.tile_size + 4),
                                 2, border_radius=3)

            if tile.get_width() != self.tile_size or tile.get_height() != self.tile_size:
                screen.blit(pygame.transform.scale(tile, (self.tile_size, self.tile_size)), (tile_x, tile_y))
            else:
                screen.blit(tile, (tile_x, tile_y))

            if self.tile_size >= 24:
                f = pygame.font.Font(None, 10)
                screen.blit(f.render(str(i + 1), True, (255, 255, 255)), (tile_x + 2, tile_y + 2))

        screen.set_clip(old_clip)

    def _render_selection_overlay(self, screen):
        grid = self._grid_rect()
        old_clip = screen.get_clip()
        screen.set_clip(grid)

        cell = self.tile_size + self.tile_spacing

        # Durante o arrasto
        if self.is_selecting and self.selection_start and self.selection_end:
            c1, r1 = self.selection_start
            c2, r2 = self.selection_end
            min_c, max_c = min(c1, c2), max(c1, c2)
            min_r, max_r = min(r1, r2), max(r1, r2)

            x = grid.x + min_c * cell
            y = grid.y + min_r * cell - self.scroll_y
            w = (max_c - min_c + 1) * cell - self.tile_spacing
            h = (max_r - min_r + 1) * cell - self.tile_spacing

            surf = pygame.Surface((w, h), pygame.SRCALPHA)
            surf.fill((80, 160, 255, 60))
            screen.blit(surf, (x, y))
            pygame.draw.rect(screen, (100, 180, 255), (x, y, w, h), 2, border_radius=3)

        # Seleção persistente
        if self.multi_selection and self.multi_selection_bounds:
            min_c, min_r, max_c, max_r = self.multi_selection_bounds
            x = grid.x + min_c * cell
            y = grid.y + min_r * cell - self.scroll_y
            w = (max_c - min_c + 1) * cell - self.tile_spacing
            h = (max_r - min_r + 1) * cell - self.tile_spacing

            if y + h > grid.y and y < grid.bottom:
                surf = pygame.Surface((w, h), pygame.SRCALPHA)
                surf.fill((100, 180, 255, 70))
                screen.blit(surf, (x, y))
                pygame.draw.rect(screen, (255, 215, 0), (x, y, w, h), 2, border_radius=3)

        screen.set_clip(old_clip)

    def _render_scrollbar(self, screen):
        if not self.focused or self.max_scroll <= 0:
            return
        grid = self._grid_rect()
        visible_height = grid.height
        scrollbar_height = max(30, visible_height * (visible_height / (visible_height + self.max_scroll)))
        scroll_ratio = self.scroll_y / self.max_scroll if self.max_scroll > 0 else 0
        sb_y = grid.y + scroll_ratio * (visible_height - scrollbar_height)

        bg = pygame.Rect(grid.right - 12, grid.y, 10, visible_height)
        pygame.draw.rect(screen, (70, 70, 80), bg)
        pygame.draw.rect(screen, (90, 90, 100), bg, 1)

        thumb = pygame.Rect(grid.right - 12, sb_y, 10, scrollbar_height)
        color = (180, 180, 200) if self.scroll_dragging else (130, 130, 150)
        pygame.draw.rect(screen, color, thumb)
        pygame.draw.rect(screen, (200, 200, 220), thumb, 1)

    def _render_resize_handle(self, screen):
        h = pygame.Rect(self.rect.right - 15, self.rect.bottom - 15, 10, 10)
        pygame.draw.rect(screen, (150, 150, 150), h)
        pygame.draw.line(screen, (200, 200, 200),
                         (h.x + 2, h.bottom - 2), (h.right - 2, h.y + 2), 2)

    def _render_footer(self, screen):
        footer_y = self.rect.bottom - self.FOOTER_HEIGHT
        footer_rect = pygame.Rect(self.rect.x + 5, footer_y, self.rect.width - 10, self.FOOTER_HEIGHT)

        pygame.draw.rect(screen, (30, 30, 40), footer_rect, border_radius=5)

        font = pygame.font.Font(None, 12)
        title = font.render("ATUAL", True, (180, 180, 180))
        screen.blit(title, (footer_rect.x + 5, footer_rect.y + 2))

        if self.selection_mode == "multi" and self.multi_selection:
            # Preview do pattern
            preview_x = footer_rect.x + 8
            preview_y = footer_rect.y + 14

            # Escala para caber no rodapé
            w, h = self.multi_selection_size
            avail_w = footer_rect.width - 100
            avail_h = footer_rect.height - 18
            if w > 0 and h > 0:
                cell_w = min(self.tile_size, avail_w // w)
                cell_h = min(self.tile_size, avail_h // h)
                ps = max(6, min(cell_w, cell_h))

                for cell in self.multi_selection:
                    idx = cell['tile_id'] - 1
                    if 0 <= idx < len(self.tiles):
                        tile = self.tiles[idx]
                        scaled = pygame.transform.scale(tile, (ps, ps))
                        screen.blit(scaled, (preview_x + cell['dx'] * (ps + 1),
                                             preview_y + cell['dy'] * (ps + 1)))

            info = f"{w}x{h} ({len(self.multi_selection)} tiles)"
            info_surf = font.render(info, True, (255, 215, 0))
            screen.blit(info_surf, (footer_rect.right - info_surf.get_width() - 5, footer_rect.y + 2))

            # Sem setas em modo multi
            self.left_button_rect = pygame.Rect(0, 0, 0, 0)
            self.right_button_rect = pygame.Rect(0, 0, 0, 0)

        else:
            # Preview single tile
            preview_x = footer_rect.x + 8
            preview_y = footer_rect.y + 14
            ps = 24

            pygame.draw.rect(screen, (20, 20, 30), (preview_x, preview_y, ps, ps), border_radius=3)
            pygame.draw.rect(screen, (100, 100, 100), (preview_x, preview_y, ps, ps), 1, border_radius=3)

            idx = int(self.selected_tile) if not isinstance(self.selected_tile, float) else self.selected_tile
            if 0 <= idx < len(self.tiles):
                scaled = pygame.transform.scale(self.tiles[idx], (ps, ps))
                screen.blit(scaled, (preview_x, preview_y))

            row = idx // max(1, self.cols)
            col = idx % max(1, self.cols)
            info = f"#{idx + 1}  ({col + 1},{row + 1})"
            info_surf = font.render(info, True, (220, 220, 220))
            screen.blit(info_surf, (preview_x + ps + 8, preview_y + 6))

            # Setas ‹ ›
            left_btn = pygame.Rect(footer_rect.right - 50, footer_rect.y + 10, 20, 22)
            right_btn = pygame.Rect(footer_rect.right - 25, footer_rect.y + 10, 20, 22)
            pygame.draw.rect(screen, (80, 80, 90), left_btn, border_radius=3)
            pygame.draw.rect(screen, (80, 80, 90), right_btn, border_radius=3)
            screen.blit(font.render("<", True, (255, 255, 255)),
                        font.render("<", True, (255, 255, 255)).get_rect(center=left_btn.center))
            screen.blit(font.render(">", True, (255, 255, 255)),
                        font.render(">", True, (255, 255, 255)).get_rect(center=right_btn.center))

            self.left_button_rect = left_btn
            self.right_button_rect = right_btn