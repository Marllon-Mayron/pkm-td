# src/scenes/editor/components/structure_manager_dialog.py

import pygame


class StructureManagerDialog:
    COLORS = {
        'bg':            (40, 40, 50),
        'bg_light':      (50, 50, 60),
        'bg_dark':       (30, 30, 40),
        'bg_preview':    (22, 25, 32),
        'border':        (255, 215, 0),
        'border_light':  (80, 80, 90),
        'text':          (255, 255, 255),
        'text_dim':      (200, 200, 200),
        'text_muted':    (140, 140, 150),
        'accent':        (80, 100, 140),
        'accent_hover':  (100, 120, 160),
        'success':       (0, 120, 0),
        'success_hover': (0, 155, 0),
        'danger':        (120, 0, 0),
        'danger_hover':  (155, 0, 0),
    }

    LAYER_TINTS = [
        (200, 180, 140),
        (140, 200, 140),
        (140, 170, 220),
        (220, 160, 200),
        (200, 200, 100),
    ]

    def __init__(self, x, y, width, height, editor_scene):
        self.rect = pygame.Rect(x, y, width, height)
        self.visible = True
        self.editor = editor_scene
        self.structure_manager = editor_scene.structure_manager

        self.dragging = False
        self.drag_offset_x = 0
        self.drag_offset_y = 0

        self.hovered_button = None
        self.hovered_item_index = -1
        self.selected_index = -1

        self.scroll = 0
        self.max_scroll = 0

        self.show_preview = True
        self.preview_zoom = 1.0
        self.preview_zoom_min = 0.25
        self.preview_zoom_max = 4.0

        # cache do último tile_size usado na preview (evita recomputar)
        self._last_preview_key = None

        self.font_title = pygame.font.Font(None, 24)
        self.font = pygame.font.Font(None, 20)
        self.font_small = pygame.font.Font(None, 16)
        self.font_tiny = pygame.font.Font(None, 13)

        self.names = []
        self.item_height = 30

        self._init_buttons()
        self._refresh_list()

    # =========================================================
    # LAYOUT
    # =========================================================
    def _init_buttons(self):
        x, y, w, h = self.rect

        self.preview_toggle_rect = pygame.Rect(x + w - 158, y + 34, 148, 22)

        list_top = y + 62
        list_bottom = y + h - 55
        list_height = list_bottom - list_top

        if self.show_preview:
            half = (w - 30) // 2
            self.list_area = pygame.Rect(x + 10, list_top, half, list_height)
            self.preview_area = pygame.Rect(x + 10 + half + 10, list_top,
                                            w - 20 - half - 10, list_height)
        else:
            self.list_area = pygame.Rect(x + 10, list_top, w - 20, list_height)
            self.preview_area = None

        btn_w, btn_h, gap = 110, 32, 10
        total = btn_w * 3 + gap * 2
        bx = x + (w - total) // 2
        by = y + h - 42

        self.paste_button  = pygame.Rect(bx, by, btn_w, btn_h)
        self.new_button    = pygame.Rect(bx + btn_w + gap, by, btn_w, btn_h)
        self.delete_button = pygame.Rect(bx + (btn_w + gap) * 2, by, btn_w, btn_h)

        self._update_max_scroll()

    def _refresh_list(self):
        self.names = self.structure_manager.list_names()
        if self.selected_index >= len(self.names):
            self.selected_index = len(self.names) - 1
        self._update_max_scroll()

    def _update_max_scroll(self):
        if not hasattr(self, 'list_area'):
            self.max_scroll = 0
            return
        visible = max(1, self.list_area.height // self.item_height)
        self.max_scroll = max(0, len(self.names) - visible)
        self.scroll = max(0, min(self.scroll, self.max_scroll))

    # =========================================================
    # EVENTOS
    # =========================================================
    def handle_event(self, event):
        if not self.visible:
            return None

        mp = pygame.mouse.get_pos()

        # ---- Roda do mouse: zoom na preview / scroll na lista ----
        if event.type == pygame.MOUSEWHEEL:
            # Zoom no preview
            if self.show_preview and self.preview_area and self.preview_area.collidepoint(mp):
                step = 0.15 * event.y
                self.preview_zoom = max(self.preview_zoom_min,
                                        min(self.preview_zoom_max,
                                            self.preview_zoom + step))
                return None
            # Scroll na lista
            if self.list_area.collidepoint(mp):
                self.scroll = max(0, min(self.max_scroll, self.scroll - event.y))
                return None
            return None

        # ---- Compatibilidade com pygame antigo (button 4/5) ----
        if event.type == pygame.MOUSEBUTTONDOWN and event.button in (4, 5):
            direction = 1 if event.button == 5 else -1
            if self.show_preview and self.preview_area and self.preview_area.collidepoint(mp):
                step = 0.15 * direction
                self.preview_zoom = max(self.preview_zoom_min,
                                        min(self.preview_zoom_max,
                                            self.preview_zoom + step))
                return None
            if self.list_area.collidepoint(mp):
                self.scroll = max(0, min(self.max_scroll, self.scroll + direction))
                return None
            return None

        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            return self._handle_click(mp)

        if event.type == pygame.MOUSEBUTTONUP and event.button == 1:
            self.dragging = False

        if event.type == pygame.MOUSEMOTION:
            if self.dragging:
                self.rect.x = mp[0] - self.drag_offset_x
                self.rect.y = mp[1] - self.drag_offset_y
                self._init_buttons()
                self._refresh_list()
            else:
                self._update_hover(mp)

        if event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE:
            self.visible = False
            return None

        return None

    def _update_hover(self, mp):
        self.hovered_button = None
        self.hovered_item_index = -1

        for rect, name in (
            (self.preview_toggle_rect, "preview"),
            (self.paste_button, "paste"),
            (self.new_button, "new"),
            (self.delete_button, "delete"),
        ):
            if rect.collidepoint(mp):
                self.hovered_button = name
                return

        if self.list_area.collidepoint(mp):
            rel_y = mp[1] - self.list_area.y
            idx = (rel_y // self.item_height) + self.scroll
            if 0 <= idx < len(self.names):
                self.hovered_item_index = idx

    def _handle_click(self, mp):
        title_rect = pygame.Rect(self.rect.x, self.rect.y, self.rect.width, 30)
        if title_rect.collidepoint(mp):
            self.dragging = True
            self.drag_offset_x = mp[0] - self.rect.x
            self.drag_offset_y = mp[1] - self.rect.y
            return None

        if self.preview_toggle_rect.collidepoint(mp):
            self.show_preview = not self.show_preview
            self._init_buttons()
            return None

        if self.paste_button.collidepoint(mp):
            if 0 <= self.selected_index < len(self.names):
                name = self.names[self.selected_index]
                structure = self.structure_manager.get(name)
                if structure:
                    ok, msg = self.structure_manager.check_can_paste(
                        self.editor.layer_manager, structure
                    )
                    if not ok:
                        print(f"[Structures] {msg}")
                        return None
                    self.editor.loaded_structure = structure
                    self.editor.loaded_structure_name = name
                    print(f"[Structures] '{name}' carregada — pincel cola no mapa")
                    self.visible = False
                    return "loaded"
            return None

        if self.new_button.collidepoint(mp):
            self.visible = False
            self.editor.start_structure_selection()
            return "selection_started"

        if self.delete_button.collidepoint(mp):
            if 0 <= self.selected_index < len(self.names):
                name = self.names[self.selected_index]
                self.structure_manager.delete(name)
                self._refresh_list()
            return None

        if self.list_area.collidepoint(mp):
            rel_y = mp[1] - self.list_area.y
            idx = (rel_y // self.item_height) + self.scroll
            if 0 <= idx < len(self.names):
                self.selected_index = idx
            return None

        if not self.rect.collidepoint(mp):
            self.visible = False

        return None

    # =========================================================
    # RENDER
    # =========================================================
    def render(self, screen):
        if not self.visible:
            return

        ov = pygame.Surface((screen.get_width(), screen.get_height()))
        ov.set_alpha(180)
        ov.fill((0, 0, 0))
        screen.blit(ov, (0, 0))

        pygame.draw.rect(screen, self.COLORS['bg'], self.rect, border_radius=10)
        pygame.draw.rect(screen, self.COLORS['border'], self.rect, 2, border_radius=10)

        title_bar = pygame.Rect(self.rect.x, self.rect.y, self.rect.width, 30)
        pygame.draw.rect(screen, self.COLORS['bg_light'], title_bar,
                         border_top_left_radius=10, border_top_right_radius=10)
        title = self.font_title.render("Estruturas Customizadas", True, self.COLORS['text'])
        screen.blit(title, (self.rect.x + 12, self.rect.y + 6))

        self._render_preview_toggle(screen)
        self._render_list(screen)

        if self.show_preview and self.preview_area:
            self._render_preview(screen)

        self._render_button(screen, self.paste_button, "paste", "Colar",
                            enabled=(0 <= self.selected_index < len(self.names)))
        self._render_button(screen, self.new_button, "new", "Nova Estrutura")
        self._render_button(screen, self.delete_button, "delete", "Excluir",
                            enabled=(0 <= self.selected_index < len(self.names)))

    def _render_preview_toggle(self, screen):
        r = self.preview_toggle_rect
        hovered = (self.hovered_button == "preview")

        bg = (60, 70, 90) if hovered else (45, 50, 65)
        pygame.draw.rect(screen, bg, r, border_radius=4)
        pygame.draw.rect(screen, self.COLORS['border_light'], r, 1, border_radius=4)

        box = pygame.Rect(r.x + 6, r.y + 3, 16, 16)
        if self.show_preview:
            pygame.draw.rect(screen, self.COLORS['accent'], box, border_radius=3)
            pygame.draw.line(screen, (255, 255, 255),
                             (box.x + 3, box.y + 8), (box.x + 6, box.y + 11), 2)
            pygame.draw.line(screen, (255, 255, 255),
                             (box.x + 6, box.y + 11), (box.x + 12, box.y + 3), 2)
        else:
            pygame.draw.rect(screen, (40, 45, 60), box, border_radius=3)
        pygame.draw.rect(screen, self.COLORS['border_light'], box, 1, border_radius=3)

        label = self.font_small.render("Preview", True, self.COLORS['text'])
        screen.blit(label, (box.right + 6, r.y + 3))

    def _render_list(self, screen):
        pygame.draw.rect(screen, self.COLORS['bg_dark'], self.list_area, border_radius=6)

        old_clip = screen.get_clip()
        screen.set_clip(self.list_area)

        if not self.names:
            msg = self.font.render("Nenhuma estrutura salva ainda", True,
                                   self.COLORS['text_muted'])
            screen.blit(msg, msg.get_rect(center=self.list_area.center))
        else:
            list_y = self.list_area.y + 2 - self.scroll * self.item_height
            for i, name in enumerate(self.names):
                item_y = list_y + i * self.item_height
                if item_y + self.item_height < self.list_area.y or item_y > self.list_area.bottom:
                    continue

                item_rect = pygame.Rect(self.list_area.x + 4, item_y,
                                        self.list_area.width - 8, self.item_height - 2)
                is_sel = (i == self.selected_index)
                is_hov = (i == self.hovered_item_index)

                bg = (self.COLORS['accent'] if is_sel else
                      (self.COLORS['accent_hover'] if is_hov else
                       (self.COLORS['bg_light'] if i % 2 == 0 else self.COLORS['bg'])))

                pygame.draw.rect(screen, bg, item_rect, border_radius=4)

                structure = self.structure_manager.get(name)
                info = ""
                if structure:
                    w = structure.get("width", 0)
                    h = structure.get("height", 0)
                    n = len(structure.get("layers", []))
                    info = f"   {w}x{h} | {n} cam"

                text = self.font_small.render(f"{name}{info}", True, self.COLORS['text'])
                screen.blit(text, (item_rect.x + 8,
                                   item_rect.y + (item_rect.height - text.get_height()) // 2))

        screen.set_clip(old_clip)

        if self.max_scroll > 0:
            visible = max(1, self.list_area.height // self.item_height)
            ratio = self.scroll / self.max_scroll if self.max_scroll > 0 else 0
            sh = max(20, int(self.list_area.height * (visible / max(1, len(self.names)))))
            sy = self.list_area.y + int((self.list_area.height - sh) * ratio)
            pygame.draw.rect(screen, (80, 80, 90),
                             (self.list_area.right - 6, self.list_area.y + 2,
                              4, self.list_area.height - 4))
            pygame.draw.rect(screen, (150, 150, 160),
                             (self.list_area.right - 6, sy, 4, sh))

    # =========================================================
    # PREVIEW — respeita tile_offsets escalados
    # =========================================================
    def _render_preview(self, screen):
        area = self.preview_area

        pygame.draw.rect(screen, self.COLORS['bg_preview'], area, border_radius=6)
        pygame.draw.rect(screen, self.COLORS['border_light'], area, 1, border_radius=6)

        if self.selected_index < 0 or self.selected_index >= len(self.names):
            msg = self.font_small.render("Selecione uma estrutura", True,
                                         self.COLORS['text_muted'])
            screen.blit(msg, msg.get_rect(center=area.center))
            return

        name = self.names[self.selected_index]
        structure = self.structure_manager.get(name)
        if not structure:
            return

        w = int(structure.get("width", 1))
        h = int(structure.get("height", 1))
        layers = structure.get("layers", [])
        native_ts = int(structure.get("tile_size", 16) or 16)

        if w <= 0 or h <= 0:
            return

        pad = 8
        avail_w = area.width - pad * 2
        avail_h = area.height - pad * 2 - 24

        base_fit = max(1, min(avail_w // w, avail_h // h))
        cell = max(1, int(base_fit * self.preview_zoom))

        # ===== Fator de escala: pixel nativo → pixel da preview =====
        scale_factor = cell / max(1, native_ts)

        # Área desenhada em pixels nativos (para centralizar com offsets)
        draw_w_native = w * native_ts
        draw_h_native = h * native_ts
        # Convertendo para pixels da preview
        draw_w = int(draw_w_native * scale_factor)
        draw_h = int(draw_h_native * scale_factor)

        draw_area = pygame.Rect(area.x + pad, area.y + pad,
                                area.width - pad * 2, area.height - pad * 2 - 20)

        old_clip = screen.get_clip()
        screen.set_clip(draw_area)

        # Centraliza (usa dimensões nativas convertidas)
        if draw_w <= draw_area.width:
            ox = draw_area.x + (draw_area.width - draw_w) // 2
        else:
            ox = draw_area.x
        if draw_h <= draw_area.height:
            oy = draw_area.y + (draw_area.height - draw_h) // 2
        else:
            oy = draw_area.y

        # Fundo xadrez
        bg_tile = 8
        for by in range(0, max(1, draw_h), bg_tile):
            for bx in range(0, max(1, draw_w), bg_tile):
                c = (35, 38, 46) if ((bx // bg_tile) + (by // bg_tile)) % 2 == 0 else (28, 30, 36)
                pygame.draw.rect(screen, c, (ox + bx, oy + by, bg_tile, bg_tile))

        # ===== TILES DE CADA CAMADA =====
        for li, layer_data in enumerate(layers):
            tiles = layer_data.get("tiles", []) or []
            tilesets_info = layer_data.get("tilesets_info", []) or []
            offsets = layer_data.get("tile_offsets", {}) or {}
            has_meta = bool(tilesets_info)
            tint = self.LAYER_TINTS[li % len(self.LAYER_TINTS)]

            for dy in range(min(h, len(tiles))):
                row = tiles[dy]
                for dx in range(min(w, len(row))):
                    try:
                        tid = int(row[dx])
                    except (ValueError, TypeError):
                        continue
                    if tid == 0:
                        continue

                    # ===== OFFSET (em pixels nativos) escalado =====
                    off = offsets.get(f"{dx},{dy}")
                    off_x = int(off[0] * scale_factor) if off else 0
                    off_y = int(off[1] * scale_factor) if off else 0

                    px = ox + dx * cell + off_x
                    py = oy + dy * cell + off_y

                    drawn = False
                    if has_meta:
                        surf = self.structure_manager.get_tile_surface_for_structure(
                            tilesets_info, tid, cell
                        )
                        if surf is not None:
                            screen.blit(surf, (px, py))
                            drawn = True

                    if not drawn:
                        block = pygame.Surface((cell, cell), pygame.SRCALPHA)
                        block.fill((*tint, 200))
                        screen.blit(block, (px, py))

        # Borda
        pygame.draw.rect(screen, (255, 215, 0), (ox, oy, draw_w, draw_h), 1)

        screen.set_clip(old_clip)

        info = f"{w}x{h} | {len(layers)} cam | zoom {int(self.preview_zoom * 100)}%"
        legend = self.font_tiny.render(info, True, self.COLORS['text_dim'])
        screen.blit(legend, (area.x + 6, area.bottom - 18))

        hint = "Roda: zoom"
        hint_surf = self.font_tiny.render(hint, True, self.COLORS['text_muted'])
        screen.blit(hint_surf, (area.right - hint_surf.get_width() - 6, area.bottom - 18))

    def _render_button(self, screen, rect, name, label, enabled=True):
        hovered = (self.hovered_button == name)

        if not enabled:
            bg, fg = (50, 50, 60), self.COLORS['text_muted']
        elif name == "paste":
            bg, fg = (self.COLORS['success_hover'] if hovered else self.COLORS['success'],
                      self.COLORS['text'])
        elif name == "new":
            bg, fg = (self.COLORS['accent_hover'] if hovered else self.COLORS['accent'],
                      self.COLORS['text'])
        elif name == "delete":
            bg, fg = (self.COLORS['danger_hover'] if hovered else self.COLORS['danger'],
                      self.COLORS['text'])
        else:
            bg, fg = (60, 60, 70), self.COLORS['text']

        pygame.draw.rect(screen, bg, rect, border_radius=6)
        pygame.draw.rect(screen, (200, 200, 200), rect, 1, border_radius=6)
        txt = self.font.render(label, True, fg)
        screen.blit(txt, txt.get_rect(center=rect.center))