# src/scenes/editor/handlers/render_handler.py

import pygame


class EditorRenderHandler:
    def __init__(self, editor_scene):
        self.editor = editor_scene
        self._cam_offset_x = 0
        self._cam_offset_y = 0
        self._tile_size_scaled = 24

    def render(self, screen):
        """Renderiza todos os elementos do editor"""
        screen.fill((30, 30, 40))

        self._update_camera_values()

        # ===== MAPA =====
        self.editor.layer_manager.render_all(screen, self.editor.camera, self.editor.screen_manager)

        # ===== ELEMENTOS DE EDIÇÃO =====
        self.editor.tower_spots.render(screen, self.editor.camera, self.editor.screen_manager)
        self.editor.path_manager.render(screen, self.editor.camera, self.editor.screen_manager)
        self.editor.target_items.render(screen, self.editor.camera, self.editor.screen_manager)

        # ===== PREVIEWS =====
        self._render_pattern_preview(screen)
        self._render_shape_preview(screen)
        self._render_eraser_preview(screen)

        # ===== PREVIEW DA ESTRUTURA CARREGADA (colar) =====
        self._render_structure_preview(screen)

        # ===== GRID =====
        if self.editor.show_grid:
            self._render_grid(screen)

        # ===== LIMITES / BORDAS =====
        self._render_map_bounds(screen)
        self._render_viewport_border(screen)

        # ===== OVERLAY DE SELEÇÃO DE ESTRUTURA =====
        self._render_structure_selection_overlay(screen)

        # ===== UI PANELS =====
        self._render_ui_panels(screen)
        self._render_top_ui(screen)

        # ===== DIÁLOGOS (ordem inversa de prioridade) =====
        if (hasattr(self.editor, 'tileset_manager_dialog')
                and self.editor.tileset_manager_dialog
                and self.editor.tileset_manager_dialog.visible):
            self.editor.tileset_manager_dialog.render(screen)

        if (self.editor.map_config_dialog
                and self.editor.map_config_dialog.visible):
            self.editor.map_config_dialog.render(screen)

        if (self.editor.wave_config_dialog
                and self.editor.wave_config_dialog.visible):
            self.editor.wave_config_dialog.render(screen)

        if (self.editor.load_phase_dialog
                and self.editor.load_phase_dialog.visible):
            self.editor.load_phase_dialog.render(screen)

        if (self.editor.target_item_dialog
                and self.editor.target_item_dialog.visible):
            self.editor.target_item_dialog.render(screen)

        if (self.editor.rewards_config_dialog
                and self.editor.rewards_config_dialog.visible):
            self.editor.rewards_config_dialog.render(screen, self.editor.font, self.editor.font_small)

        if (hasattr(self.editor, 'event_config_dialog')
                and self.editor.event_config_dialog
                and self.editor.event_config_dialog.visible):
            self.editor.event_config_dialog.render(screen)

        # ===== DIÁLOGO DE ESTRUTURAS (NOVO) =====
        if (hasattr(self.editor, 'structure_manager_dialog')
                and self.editor.structure_manager_dialog
                and self.editor.structure_manager_dialog.visible):
            self.editor.structure_manager_dialog.render(screen)

        # ===== PAUSE (sempre por último) =====
        if self.editor.paused:
            self._render_pause_overlay(screen)

    # ==================================================================
    # PREVIEW DA ESTRUTURA CARREGADA (seguir mouse ao colar)
    # ==================================================================
    def _render_structure_preview(self, screen):
        structure = getattr(self.editor, 'loaded_structure', None)
        if not structure:
            return
        if self.editor.brush_buttons.get_current_brush() != self.editor.brush_buttons.BRUSH_PENCIL:
            return

        sm = self.editor.screen_manager
        camera = self.editor.camera
        mp = pygame.mouse.get_pos()
        if not sm.is_mouse_in_viewport(mp):
            return
        if self.editor.tile_palette and self.editor.tile_palette.rect.collidepoint(mp):
            return
        if self.editor.layer_selector and self.editor.layer_selector.rect.collidepoint(mp):
            return
        if self.editor.brush_buttons.rect.collidepoint(mp):
            return

        world_pos = sm.get_mouse_world_position(mp, camera)
        if not world_pos:
            return

        grid = self.editor.grid_size
        anchor_x = int(world_pos[0] // grid)
        anchor_y = int(world_pos[1] // grid)

        width = structure.get("width", 0)
        height = structure.get("height", 0)
        if width <= 0 or height <= 0:
            return

        zoom_scale = camera.zoom * sm.render_scale
        tile_scaled = max(1, round(grid * zoom_scale))

        # Bounding box na tela
        sx = round((anchor_x * grid - camera.x) * zoom_scale
                   + (sm.render_width / 2) * sm.render_scale + sm.viewport_x)
        sy = round((anchor_y * grid - camera.y) * zoom_scale
                   + (sm.render_height / 2) * sm.render_scale + sm.viewport_y)
        bw = width * tile_scaled
        bh = height * tile_scaled

        all_layers = structure.get("layers", [])

        # Tenta desenhar os tiles reais da primeira camada (se houver tileset compatível)
        current_layer = self.editor.layer_manager.get_current_layer()
        tileset = current_layer.tileset if current_layer else None

        if tileset and all_layers:
            first = all_layers[0]
            tiles = first.get("tiles", [])
            offsets = first.get("tile_offsets", {})
            for dy, row in enumerate(tiles):
                for dx, tid in enumerate(row):
                    try:
                        idx = int(tid) - 1
                    except (ValueError, TypeError):
                        continue
                    if 0 <= idx < len(tileset):
                        img = tileset[idx]
                        if img.get_width() != tile_scaled:
                            img = pygame.transform.scale(img, (tile_scaled, tile_scaled))
                        prev = img.copy()
                        prev.set_alpha(150)
                        off = offsets.get(f"{dx},{dy}")
                        off_x = int(off[0] * zoom_scale) if off else 0
                        off_y = int(off[1] * zoom_scale) if off else 0
                        px = sx + dx * tile_scaled + off_x
                        py = sy + dy * tile_scaled + off_y
                        screen.blit(prev, (px, py))

        # Sobreposição por camada (indicador de profundidade)
        layer_colors = [
            (255, 200, 100, 55),
            (100, 255, 200, 55),
            (200, 150, 255, 55),
            (255, 150, 200, 55),
        ]
        for i in range(len(all_layers)):
            color = layer_colors[i % len(layer_colors)]
            ov = pygame.Surface((bw, bh), pygame.SRCALPHA)
            ov.fill(color)
            screen.blit(ov, (sx, sy))

        # Borda amarela
        pygame.draw.rect(screen, (255, 215, 0), (sx, sy, bw, bh), 2)

        # Label com nome + dimensões
        font = pygame.font.Font(None, 18)
        txt = f"{self.editor.loaded_structure_name} ({width}x{height}, {len(all_layers)} cam)"
        label = font.render(txt, True, (255, 240, 150))
        bg = pygame.Surface((label.get_width() + 12, label.get_height() + 6), pygame.SRCALPHA)
        bg.fill((0, 0, 0, 190))
        screen.blit(bg, (sx, sy - label.get_height() - 8))
        screen.blit(label, (sx + 6, sy - label.get_height() - 5))

        # Hint do rodapé
        hint = "PINCEL: clique para colar | Botão direito: descarregar"
        htext = font.render(hint, True, (255, 230, 120))
        hpad = 6
        hbg = pygame.Surface((htext.get_width() + hpad * 2, htext.get_height() + hpad), pygame.SRCALPHA)
        hbg.fill((0, 0, 0, 180))
        hx = sm.viewport_x + (sm.viewport_width - htext.get_width()) // 2
        hy = sm.viewport_y + sm.viewport_height - 40
        screen.blit(hbg, (hx - hpad, hy - hpad // 2))
        screen.blit(htext, (hx, hy))

    # ==================================================================
    # OVERLAY DE SELEÇÃO DE ESTRUTURA (novo fluxo)
    # ==================================================================
    def _render_structure_selection_overlay(self, screen):
        if not getattr(self.editor, 'structure_selection_active', False):
            return

        camera = self.editor.camera
        sm = self.editor.screen_manager
        grid_size = self.editor.grid_size
        zoom_scale = camera.zoom * sm.render_scale
        tile_scaled = max(1, round(grid_size * zoom_scale))

        def to_screen(tx, ty):
            sx = round((tx * grid_size - camera.x) * zoom_scale
                       + (sm.render_width / 2) * sm.render_scale + sm.viewport_x)
            sy = round((ty * grid_size - camera.y) * zoom_scale
                       + (sm.render_height / 2) * sm.render_scale + sm.viewport_y)
            return sx, sy

        # ---- Máscara acumulada ----
        mask = self.editor.structure_selection_mask
        if mask:
            mask_surf = pygame.Surface((tile_scaled, tile_scaled), pygame.SRCALPHA)
            mask_surf.fill((100, 220, 100, 90))

            for (tx, ty) in mask:
                sx, sy = to_screen(tx, ty)
                if (sx + tile_scaled < sm.viewport_x or sx > sm.viewport_x + sm.viewport_width or
                        sy + tile_scaled < sm.viewport_y or sy > sm.viewport_y + sm.viewport_height):
                    continue
                screen.blit(mask_surf, (sx, sy))
                pygame.draw.rect(screen, (60, 170, 60),
                                 (sx, sy, tile_scaled, tile_scaled), 1)

            bbox = self.editor.structure_manager.get_selection_bbox(mask)
            if bbox:
                min_x, min_y, max_x, max_y = bbox
                bx, by = to_screen(min_x, min_y)
                bw = (max_x - min_x + 1) * tile_scaled
                bh = (max_y - min_y + 1) * tile_scaled
                pygame.draw.rect(screen, (255, 215, 0), (bx - 1, by - 1, bw + 2, bh + 2), 2)

        # ---- Drag em andamento ----
        if (self.editor.structure_selection_dragging
                and self.editor.structure_selection_drag_start
                and self.editor.structure_selection_drag_end):

            x0, y0 = self.editor.structure_selection_drag_start
            x1, y1 = self.editor.structure_selection_drag_end

            panel = self.editor.structure_selection_panel
            tool = panel.tool if panel else "rect"
            op = panel.operation if panel else "add"
            filled = panel.filled if panel else True

            if tool == "rect":
                cells = self.editor.structure_manager.get_rect_cells(x0, y0, x1, y1)
            else:
                cells = self.editor.structure_manager.get_circle_cells(x0, y0, x1, y1, filled=filled)

            if op == "add":
                fill_color = (100, 220, 100, 110)
                border_color = (60, 200, 60)
            else:
                fill_color = (220, 100, 100, 110)
                border_color = (200, 60, 60)

            preview = pygame.Surface((tile_scaled, tile_scaled), pygame.SRCALPHA)
            preview.fill(fill_color)

            for (tx, ty) in cells:
                sx, sy = to_screen(tx, ty)
                if (sx + tile_scaled < sm.viewport_x or sx > sm.viewport_x + sm.viewport_width or
                        sy + tile_scaled < sm.viewport_y or sy > sm.viewport_y + sm.viewport_height):
                    continue
                screen.blit(preview, (sx, sy))
                pygame.draw.rect(screen, border_color,
                                 (sx, sy, tile_scaled, tile_scaled), 1)

        # ---- Painel flutuante ----
        if (self.editor.structure_selection_panel
                and self.editor.structure_selection_panel.visible):
            self.editor.structure_selection_panel.render(screen)

    # ==================================================================
    # PREVIEW DO SHAPE (linha / círculo) — inalterado
    # ==================================================================
    def _render_shape_preview(self, screen):
        if not hasattr(self.editor, 'map_handler'):
            return
        if not self.editor.map_handler.shape_active:
            return

        tiles = self.editor.map_handler.get_shape_tiles()
        if not tiles:
            return

        camera = self.editor.camera
        sm = self.editor.screen_manager
        grid_size = self.editor.grid_size

        tile_size_scaled = max(1, round(grid_size * camera.zoom * sm.render_scale))

        current_layer = self.editor.layer_manager.get_current_layer()
        current_tile_int = self.editor.current_tile

        tile_img = None
        if current_layer and current_layer.tileset:
            try:
                idx = int(current_tile_int) - 1
                if 0 <= idx < len(current_layer.tileset):
                    tile_img = current_layer.tileset[idx]
            except (ValueError, TypeError):
                tile_img = None

        for tx, ty in tiles:
            screen_x = round((tx * grid_size - camera.x) * camera.zoom * sm.render_scale +
                             (sm.render_width / 2) * sm.render_scale + sm.viewport_x)
            screen_y = round((ty * grid_size - camera.y) * camera.zoom * sm.render_scale +
                             (sm.render_height / 2) * sm.render_scale + sm.viewport_y)

            if tile_img is not None:
                if tile_img.get_width() != tile_size_scaled:
                    scaled = pygame.transform.scale(tile_img, (tile_size_scaled, tile_size_scaled))
                else:
                    scaled = tile_img

                preview = scaled.copy()
                preview.set_alpha(170)
                screen.blit(preview, (screen_x, screen_y))

            pygame.draw.rect(screen, (255, 215, 0),
                             (screen_x, screen_y, tile_size_scaled, tile_size_scaled), 1)

        if self.editor.map_handler.shape_start:
            sx, sy = self.editor.map_handler.shape_start
            start_screen_x = round((sx * grid_size - camera.x) * camera.zoom * sm.render_scale +
                                   (sm.render_width / 2) * sm.render_scale + sm.viewport_x)
            start_screen_y = round((sy * grid_size - camera.y) * camera.zoom * sm.render_scale +
                                   (sm.render_height / 2) * sm.render_scale + sm.viewport_y)
            center_x = start_screen_x + tile_size_scaled // 2
            center_y = start_screen_y + tile_size_scaled // 2
            pygame.draw.circle(screen, (255, 60, 60), (center_x, center_y),
                               max(3, tile_size_scaled // 4))

        tool = self.editor.map_handler.shape_tool or ""
        if tool == "line":
            hint = "LINHA: arraste para definir o fim | ESC cancela"
        elif tool == "circle":
            filled = "preenchido" if self.editor.brush_buttons.is_circle_filled() else "contorno"
            hint = f"CIRCULO ({filled}): arraste para definir o raio | ESC cancela"
        else:
            hint = ""

        if hint:
            font = pygame.font.Font(None, 18)
            text = font.render(hint, True, (255, 230, 120))
            pad = 6
            bg = pygame.Surface((text.get_width() + pad * 2, text.get_height() + pad), pygame.SRCALPHA)
            bg.fill((0, 0, 0, 180))
            hint_x = sm.viewport_x + (sm.viewport_width - text.get_width()) // 2
            hint_y = sm.viewport_y + sm.viewport_height - 40
            screen.blit(bg, (hint_x - pad, hint_y - pad // 2))
            screen.blit(text, (hint_x, hint_y))

    # ==================================================================
    # PREVIEW DO PATTERN MULTI-TILE — inalterado
    # ==================================================================
    def _render_pattern_preview(self, screen):
        if self.editor.mode != "layers":
            return
        if not hasattr(self.editor, 'brush_buttons') or not self.editor.brush_buttons:
            return
        if self.editor.brush_buttons.get_current_brush() != self.editor.brush_buttons.BRUSH_PENCIL:
            return
        if not hasattr(self.editor, 'tile_palette') or not self.editor.tile_palette:
            return

        pattern = self.editor.tile_palette.get_current_brush_pattern()
        if not pattern:
            return

        sm = self.editor.screen_manager
        camera = self.editor.camera
        mouse_pos = pygame.mouse.get_pos()

        if not sm.is_mouse_in_viewport(mouse_pos):
            return
        if self.editor.tile_palette.rect.collidepoint(mouse_pos):
            return
        if self.editor.layer_selector and self.editor.layer_selector.rect.collidepoint(mouse_pos):
            return
        if hasattr(self.editor, 'brush_buttons') and self.editor.brush_buttons.rect.collidepoint(mouse_pos):
            return

        world_pos = sm.get_mouse_world_position(mouse_pos, camera)
        if not world_pos:
            return

        grid_size = self.editor.grid_size
        tile_x = int(world_pos[0] // grid_size)
        tile_y = int(world_pos[1] // grid_size)

        current_layer = self.editor.layer_manager.get_current_layer()
        if not current_layer or not current_layer.tileset:
            return

        zoom_scale = camera.zoom * sm.render_scale
        tile_size_scaled = max(1, round(grid_size * zoom_scale))

        def to_screen(wx, wy):
            sx = round((wx - camera.x) * zoom_scale +
                       (sm.render_width / 2) * sm.render_scale + sm.viewport_x)
            sy = round((wy - camera.y) * zoom_scale +
                       (sm.render_height / 2) * sm.render_scale + sm.viewport_y)
            return sx, sy

        for cell in pattern:
            tx = tile_x + cell['dx']
            ty = tile_y + cell['dy']
            if not (0 <= tx < current_layer.width and 0 <= ty < current_layer.height):
                continue
            tile_id = cell['tile_id']
            try:
                idx = int(tile_id) - 1
            except (ValueError, TypeError):
                continue
            if not (0 <= idx < len(current_layer.tileset)):
                continue
            tile_img = current_layer.tileset[idx]
            if tile_img.get_width() != tile_size_scaled:
                scaled = pygame.transform.scale(tile_img, (tile_size_scaled, tile_size_scaled))
            else:
                scaled = tile_img
            preview = scaled.copy()
            preview.set_alpha(170)
            screen_x, screen_y = to_screen(tx * grid_size, ty * grid_size)
            if (screen_x + tile_size_scaled < sm.viewport_x or
                    screen_x > sm.viewport_x + sm.viewport_width or
                    screen_y + tile_size_scaled < sm.viewport_y or
                    screen_y > sm.viewport_y + sm.viewport_height):
                continue
            screen.blit(preview, (screen_x, screen_y))

        min_dx = min(c['dx'] for c in pattern)
        max_dx = max(c['dx'] for c in pattern)
        min_dy = min(c['dy'] for c in pattern)
        max_dy = max(c['dy'] for c in pattern)
        box_x0, box_y0 = to_screen(
            (tile_x + min_dx) * grid_size,
            (tile_y + min_dy) * grid_size
        )
        box_w = (max_dx - min_dx + 1) * tile_size_scaled
        box_h = (max_dy - min_dy + 1) * tile_size_scaled

        if (box_x0 + box_w > sm.viewport_x and box_x0 < sm.viewport_x + sm.viewport_width and
                box_y0 + box_h > sm.viewport_y and box_y0 < sm.viewport_y + sm.viewport_height):
            pygame.draw.rect(screen, (255, 215, 0),
                             (box_x0 - 1, box_y0 - 1, box_w + 2, box_h + 2), 2)

        w = max_dx - min_dx + 1
        h = max_dy - min_dy + 1
        hint = f"PATTERN {w}x{h} ({len(pattern)} tiles) | Solte para pintar"
        font = pygame.font.Font(None, 18)
        text = font.render(hint, True, (255, 230, 120))
        pad = 6
        bg = pygame.Surface((text.get_width() + pad * 2, text.get_height() + pad), pygame.SRCALPHA)
        bg.fill((0, 0, 0, 180))
        hint_x = sm.viewport_x + (sm.viewport_width - text.get_width()) // 2
        hint_y = sm.viewport_y + sm.viewport_height - 40
        screen.blit(bg, (hint_x - pad, hint_y - pad // 2))
        screen.blit(text, (hint_x, hint_y))

    # ==================================================================
    # CAMERA / GRID / MUNDO
    # ==================================================================
    def _update_camera_values(self):
        camera = self.editor.camera
        sm = self.editor.screen_manager

        self._cam_offset_x = round((-camera.x * camera.zoom * sm.render_scale +
                                    (sm.render_width / 2) * sm.render_scale +
                                    sm.viewport_x))
        self._cam_offset_y = round((-camera.y * camera.zoom * sm.render_scale +
                                    (sm.render_height / 2) * sm.render_scale +
                                    sm.viewport_y))
        self._tile_size_scaled = max(1, round(self.editor.grid_size * camera.zoom * sm.render_scale))

    def _render_grid(self, screen):
        sm = self.editor.screen_manager
        first_visible_x = (-self._cam_offset_x) // self._tile_size_scaled
        first_visible_y = (-self._cam_offset_y) // self._tile_size_scaled
        tiles_visible_x = (sm.viewport_width // self._tile_size_scaled) + 2
        tiles_visible_y = (sm.viewport_height // self._tile_size_scaled) + 2

        grid_surface = pygame.Surface(
            (sm.viewport_width, sm.viewport_height), pygame.SRCALPHA
        )

        for i in range(tiles_visible_x):
            tile_x = first_visible_x + i
            screen_x = tile_x * self._tile_size_scaled + self._cam_offset_x
            grid_x = screen_x - sm.viewport_x
            if -1 <= grid_x <= sm.viewport_width + 1:
                if tile_x == 0:
                    color = (255, 100, 100, 180); width = 2
                else:
                    color = (100, 100, 100, 100); width = 1
                grid_x_int = int(round(grid_x))
                pygame.draw.line(grid_surface, color, (grid_x_int, 0),
                                 (grid_x_int, sm.viewport_height), width)

        for i in range(tiles_visible_y):
            tile_y = first_visible_y + i
            screen_y = tile_y * self._tile_size_scaled + self._cam_offset_y
            grid_y = screen_y - sm.viewport_y
            if -1 <= grid_y <= sm.viewport_height + 1:
                if tile_y == 0:
                    color = (100, 255, 100, 180); width = 2
                else:
                    color = (100, 100, 100, 100); width = 1
                grid_y_int = int(round(grid_y))
                pygame.draw.line(grid_surface, color, (0, grid_y_int),
                                 (sm.viewport_width, grid_y_int), width)

        screen.blit(grid_surface, (sm.viewport_x, sm.viewport_y))

    def _world_to_screen(self, world_x, world_y):
        camera = self.editor.camera
        sm = self.editor.screen_manager
        screen_x = round((world_x - camera.x) * camera.zoom * sm.render_scale +
                         (sm.render_width / 2) * sm.render_scale + sm.viewport_x)
        screen_y = round((world_y - camera.y) * camera.zoom * sm.render_scale +
                         (sm.render_height / 2) * sm.render_scale + sm.viewport_y)
        return (screen_x, screen_y)

    def _render_map_bounds(self, screen):
        current_layer = self.editor.layer_manager.get_current_layer()
        if not current_layer:
            return

        map_left = self.editor.min_world_x
        map_right = self.editor.max_world_x
        map_top = self.editor.min_world_y
        map_bottom = self.editor.max_world_y

        current_left = 0
        current_right = current_layer.width * self.editor.grid_size
        current_top = 0
        current_bottom = current_layer.height * self.editor.grid_size

        corners = [
            (map_left, map_top), (map_right, map_top),
            (map_right, map_bottom), (map_left, map_bottom)
        ]
        screen_corners = [self._world_to_screen(wx, wy) for wx, wy in corners]

        if len(screen_corners) == 4:
            pygame.draw.polygon(screen, (255, 100, 100), screen_corners, 2)

        current_corners = [
            (current_left, current_top), (current_right, current_top),
            (current_right, current_bottom), (current_left, current_bottom)
        ]
        screen_current_corners = [self._world_to_screen(wx, wy) for wx, wy in current_corners]
        if len(screen_current_corners) == 4:
            pygame.draw.polygon(screen, (100, 255, 100), screen_current_corners, 2)

        for screen_x, screen_y in screen_corners:
            pygame.draw.circle(screen, (255, 100, 100), (screen_x, screen_y), 6)

        font = pygame.font.Font(None, 16)
        text = font.render(f"({map_left:.0f}, {map_top:.0f})", True, (255, 100, 100))
        screen.blit(text, (screen_corners[0][0] + 10, screen_corners[0][1] + 10))
        text = font.render(f"({map_right:.0f}, {map_top:.0f})", True, (255, 100, 100))
        screen.blit(text, (screen_corners[1][0] - 90, screen_corners[1][1] + 10))
        text = font.render(f"({map_right:.0f}, {map_bottom:.0f})", True, (255, 100, 100))
        screen.blit(text, (screen_corners[2][0] - 100, screen_corners[2][1] - 20))
        text = font.render(f"({map_left:.0f}, {map_bottom:.0f})", True, (255, 100, 100))
        screen.blit(text, (screen_corners[3][0] + 10, screen_corners[3][1] - 20))

        info_font = pygame.font.Font(None, 14)
        info_text = info_font.render(
            f"Área atual: {current_layer.width}x{current_layer.height} tiles",
            True, (100, 255, 100))
        screen.blit(info_text, (screen_corners[0][0] + 10, screen_corners[0][1] + 30))

    def _render_eraser_preview(self, screen):
        if not hasattr(self.editor, 'brush_buttons'):
            return
        brush = self.editor.brush_buttons
        if brush.get_current_brush() != brush.BRUSH_ERASER:
            return

        sm = self.editor.screen_manager
        camera = self.editor.camera
        mouse_pos = pygame.mouse.get_pos()
        if not sm.is_mouse_in_viewport(mouse_pos):
            return
        world_pos = sm.get_mouse_world_position(mouse_pos, camera)
        if not world_pos:
            return

        grid_size = self.editor.grid_size
        tile_x = int(world_pos[0] // grid_size)
        tile_y = int(world_pos[1] // grid_size)
        tiles = self.editor.map_handler.get_eraser_tiles_at(tile_x, tile_y)
        if not tiles:
            return

        tile_size_scaled = max(1, round(grid_size * camera.zoom * sm.render_scale))
        overlay = pygame.Surface((tile_size_scaled, tile_size_scaled), pygame.SRCALPHA)
        overlay.fill((255, 60, 60, 80))

        for tx, ty in tiles:
            screen_x = round((tx * grid_size - camera.x) * camera.zoom * sm.render_scale +
                             (sm.render_width / 2) * sm.render_scale + sm.viewport_x)
            screen_y = round((ty * grid_size - camera.y) * camera.zoom * sm.render_scale +
                             (sm.render_height / 2) * sm.render_scale + sm.viewport_y)
            screen.blit(overlay, (screen_x, screen_y))
            pygame.draw.rect(screen, (255, 90, 90),
                             (screen_x, screen_y, tile_size_scaled, tile_size_scaled), 1)

        shape_label = "Quadrada" if brush.get_eraser_shape() == brush.ERASER_SQUARE else "Redonda"
        size = brush.get_eraser_size() * 2 + 1
        hint = f"BORRACHA {shape_label} ({size}x{size}) | Clique ou arraste para apagar"

        font = pygame.font.Font(None, 18)
        text = font.render(hint, True, (255, 200, 200))
        pad = 6
        bg = pygame.Surface((text.get_width() + pad * 2, text.get_height() + pad), pygame.SRCALPHA)
        bg.fill((0, 0, 0, 180))
        hint_x = sm.viewport_x + (sm.viewport_width - text.get_width()) // 2
        hint_y = sm.viewport_y + sm.viewport_height - 40
        screen.blit(bg, (hint_x - pad, hint_y - pad // 2))
        screen.blit(text, (hint_x, hint_y))

    def _render_viewport_border(self, screen):
        pygame.draw.rect(screen, (100, 100, 100),
                         (self.editor.screen_manager.viewport_x,
                          self.editor.screen_manager.viewport_y,
                          self.editor.screen_manager.viewport_width,
                          self.editor.screen_manager.viewport_height), 2)

    def _render_ui_panels(self, screen):
        if self.editor.mode == "layers":
            if hasattr(self.editor, 'brush_buttons') and self.editor.brush_buttons.visible:
                structure_loaded = getattr(self.editor, 'loaded_structure', None) is not None
                self.editor.brush_buttons.render(
                    screen, self.editor.font_small,
                    structure_loaded=structure_loaded
                )

            self.editor.layer_selector.layers = self.editor.layer_manager.layers
            self.editor.layer_selector.render(screen, self.editor.layer_manager.current_layer)

            current_layer = self.editor.layer_manager.get_current_layer()
            if current_layer and current_layer.tileset:
                self.editor.tile_palette.visible = True
                self.editor.tile_palette.render(screen)
            else:
                self.editor.tile_palette.visible = False
                font = pygame.font.Font(None, 20)
                msg = font.render("CTRL+I para importar tileset", True, (200, 200, 200))
                msg_x = self.editor.screen_manager.viewport_x + self.editor.screen_manager.viewport_width - 250
                msg_y = self.editor.screen_manager.viewport_y + 180
                screen.blit(msg, (msg_x, msg_y))

    def _render_top_ui(self, screen):
        viewport_x = self.editor.screen_manager.viewport_x
        viewport_y = self.editor.screen_manager.viewport_y

        pygame.draw.rect(screen, (40, 40, 50),
                         (viewport_x, viewport_y,
                          self.editor.screen_manager.viewport_width, 60))

        current_layer = self.editor.layer_manager.get_current_layer()
        if current_layer:
            size_info = f" [{current_layer.width}x{current_layer.height}]"
        else:
            size_info = ""

        title = self.editor.font.render(
            f"EDITOR DE FASES - {self.editor.phase_name}{size_info}",
            True, (255, 215, 0))
        screen.blit(title, (viewport_x + 10, viewport_y + 10))

        inst = self.editor.font_small.render(
            "CTRL+S: Salvar | CTRL+O: Carregar | CTRL+I: Importar | CTRL+M: Map Size | "
            "CTRL+Z: Undo | CTRL+Y: Redo | G: Grid | 1-5: Modos | DEL: Remover",
            True, (200, 200, 200))
        screen.blit(inst, (viewport_x + 10, viewport_y + 35))

        # Aviso de seleção de estrutura ativa
        if getattr(self.editor, 'structure_selection_active', False):
            warn = self.editor.font_small.render(
                "★ MODO SELEÇÃO DE ESTRUTURA ATIVO — arraste no mapa | R/C: ferramenta | F: filled | ESC: cancelar",
                True, (255, 230, 100))
            screen.blit(warn, (viewport_x + 10, viewport_y + 52))

        # Aviso de estrutura carregada
        if getattr(self.editor, 'loaded_structure', None) is not None:
            warn = self.editor.font_small.render(
                f"★ ESTRUTURA CARREGADA: '{self.editor.loaded_structure_name}' — clique com pincel para colar | Botão direito cancela",
                True, (180, 255, 180))
            screen.blit(warn, (viewport_x + 10, viewport_y + 52))

        if self.editor.undo_manager.can_undo() or self.editor.undo_manager.can_redo():
            undo_text = ""
            if self.editor.undo_manager.can_undo():
                undo_desc = self.editor.undo_manager.get_undo_description()
                undo_text = f"Undo: {undo_desc[:20]}..."
            if undo_text:
                undo_surf = self.editor.font_small.render(undo_text, True, (150, 150, 200))
                screen.blit(undo_surf,
                            (viewport_x + self.editor.screen_manager.viewport_width - 300,
                             viewport_y + 35))

        self.editor.mode_buttons.render(screen, self.editor.mode, self.editor.font_small)

        mode_info = {
            "layers": "Clique nos tiles à direita | Selecione layers à esquerda",
            "path": f"Path {self.editor.path_manager.current_path_index + 1}/{len(self.editor.path_manager.paths)} | "
                    f"Esquerdo: add nó | Direito: remove | Ctrl+N: novo path | Ctrl+D: deletar | Ctrl+W: Wave configs | TAB: alternar",
            "towers": "Esquerdo: add spot | Direito: remove",
            "map_config": "Configure o mapa"
        }
        info = self.editor.font_small.render(mode_info.get(self.editor.mode, ""), True, (180, 180, 180))
        screen.blit(info, (viewport_x + 10,
                           viewport_y + self.editor.screen_manager.viewport_height - 20))

    def _render_pause_overlay(self, screen):
        overlay = pygame.Surface((self.editor.screen_manager.viewport_width,
                                  self.editor.screen_manager.viewport_height))
        overlay.set_alpha(128)
        overlay.fill((0, 0, 0))
        screen.blit(overlay, (self.editor.screen_manager.viewport_x,
                              self.editor.screen_manager.viewport_y))

        font_large = pygame.font.Font(None, 48)
        pause_text = font_large.render("PAUSADO", True, (255, 255, 255))
        text_x = self.editor.screen_manager.viewport_x + (
                self.editor.screen_manager.viewport_width - pause_text.get_width()) // 2
        text_y = self.editor.screen_manager.viewport_y + (
                self.editor.screen_manager.viewport_height - pause_text.get_height()) // 2
        screen.blit(pause_text, (text_x, text_y))