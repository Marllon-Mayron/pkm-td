# src/scenes/editor/handlers/render_handler.py

import pygame


# src/scenes/editor/handlers/render_handler.py

class EditorRenderHandler:
    def __init__(self, editor_scene):
        self.editor = editor_scene
        self._cam_offset_x = 0
        self._cam_offset_y = 0
        self._tile_size_scaled = 24  # ALTERADO: 24

    def render(self, screen):
        """Renderiza todos os elementos do editor"""
        screen.fill((30, 30, 40))

        # Atualiza valores de câmera ANTES de renderizar
        self._update_camera_values()

        # Renderiza mapa
        self.editor.layer_manager.render_all(screen, self.editor.camera, self.editor.screen_manager)

        # Elementos de edição
        self.editor.tower_spots.render(screen, self.editor.camera, self.editor.screen_manager)
        self.editor.path_manager.render(screen, self.editor.camera, self.editor.screen_manager)

        # Renderiza itens alvo
        self.editor.target_items.render(screen, self.editor.camera, self.editor.screen_manager)

        # Preview do pattern multi-tile (pincel em modo multi)
        self._render_pattern_preview(screen)

        # Preview de shapes (linha/círculo)
        self._render_shape_preview(screen)
        # Preview da borracha
        self._render_eraser_preview(screen)

        # Grid
        if self.editor.show_grid:
            self._render_grid(screen)

        # Limites do mapa
        self._render_map_bounds(screen)

        # Borda do viewport
        self._render_viewport_border(screen)

        # UI Panels
        self._render_ui_panels(screen)

        # UI Superior
        self._render_top_ui(screen)

        # Diálogos (renderizar na ordem inversa de prioridade)

        if hasattr(self.editor, 'tileset_manager_dialog') and self.editor.tileset_manager_dialog and self.editor.tileset_manager_dialog.visible:
            self.editor.tileset_manager_dialog.render(screen)

        # Diálogo de tamanho do mapa
        if self.editor.map_config_dialog and self.editor.map_config_dialog.visible:
            self.editor.map_config_dialog.render(screen)

        # Diálogo de waves
        if self.editor.wave_config_dialog and self.editor.wave_config_dialog.visible:
            self.editor.wave_config_dialog.render(screen)

        # Diálogo de carregar fase
        if self.editor.load_phase_dialog and self.editor.load_phase_dialog.visible:
            self.editor.load_phase_dialog.render(screen)

        # Diálogo de itens alvo
        if self.editor.target_item_dialog and self.editor.target_item_dialog.visible:
            self.editor.target_item_dialog.render(screen)

        if self.editor.rewards_config_dialog and self.editor.rewards_config_dialog.visible:
            self.editor.rewards_config_dialog.render(screen, self.editor.font, self.editor.font_small)

        # Diálogo de eventos
        if hasattr(self.editor, 'event_config_dialog') and self.editor.event_config_dialog and self.editor.event_config_dialog.visible:
            self.editor.event_config_dialog.render(screen)

        # Pause (sempre por último)
        if self.editor.paused:
            self._render_pause_overlay(screen)

    def _render_shape_preview(self, screen):
        """Renderiza a prévia do shape (linha / círculo) em construção."""
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

        # Tenta carregar a imagem do tile atual
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

            # Prévia do tile (semi-transparente)
            if tile_img is not None:
                if tile_img.get_width() != tile_size_scaled:
                    scaled = pygame.transform.scale(tile_img, (tile_size_scaled, tile_size_scaled))
                else:
                    scaled = tile_img

                preview = scaled.copy()
                preview.set_alpha(170)
                screen.blit(preview, (screen_x, screen_y))

            # Borda amarela
            pygame.draw.rect(screen, (255, 215, 0),
                             (screen_x, screen_y, tile_size_scaled, tile_size_scaled), 1)

        # Ponto de origem (start)
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

        # Dica no rodapé
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

            # Fundo preto semi-transparente
            pad = 6
            bg = pygame.Surface((text.get_width() + pad * 2, text.get_height() + pad), pygame.SRCALPHA)
            bg.fill((0, 0, 0, 180))
            hint_x = sm.viewport_x + (sm.viewport_width - text.get_width()) // 2
            hint_y = sm.viewport_y + sm.viewport_height - 40
            screen.blit(bg, (hint_x - pad, hint_y - pad // 2))
            screen.blit(text, (hint_x, hint_y))

    def _render_pattern_preview(self, screen):
        """
        Mostra onde o pattern multi-tile vai ser pintado.
        Só aparece quando:
          - o modo é 'layers'
          - a ferramenta é o PINCEL
          - há um pattern ativo na tile_palette
          - o mouse está no viewport
        """
        # ===== GUARDAS =====
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
            return  # modo single, nada a mostrar

        # ===== MOUSE =====
        sm = self.editor.screen_manager
        camera = self.editor.camera
        mouse_pos = pygame.mouse.get_pos()

        if not sm.is_mouse_in_viewport(mouse_pos):
            return
        # Não mostra se o mouse está sobre a palette ou o layer selector
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

        # ===== LAYER / TILESET =====
        current_layer = self.editor.layer_manager.get_current_layer()
        if not current_layer or not current_layer.tileset:
            return

        # ===== GEOMETRIA NA TELA =====
        zoom_scale = camera.zoom * sm.render_scale
        tile_size_scaled = max(1, round(grid_size * zoom_scale))

        # Helper de conversão world→screen
        def to_screen(wx, wy):
            sx = round((wx - camera.x) * zoom_scale +
                       (sm.render_width / 2) * sm.render_scale + sm.viewport_x)
            sy = round((wy - camera.y) * zoom_scale +
                       (sm.render_height / 2) * sm.render_scale + sm.viewport_y)
            return sx, sy

        # ===== DESENHA CADA TILE DO PATTERN =====
        for cell in pattern:
            tx = tile_x + cell['dx']
            ty = tile_y + cell['dy']

            # Limites do mapa
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

            # Escala
            if tile_img.get_width() != tile_size_scaled:
                scaled = pygame.transform.scale(tile_img, (tile_size_scaled, tile_size_scaled))
            else:
                scaled = tile_img

            # Copia com alpha (preview)
            preview = scaled.copy()
            preview.set_alpha(170)

            # Posição na tela
            screen_x, screen_y = to_screen(tx * grid_size, ty * grid_size)

            # Culling
            if (screen_x + tile_size_scaled < sm.viewport_x or
                    screen_x > sm.viewport_x + sm.viewport_width or
                    screen_y + tile_size_scaled < sm.viewport_y or
                    screen_y > sm.viewport_y + sm.viewport_height):
                continue

            screen.blit(preview, (screen_x, screen_y))

        # ===== BORDA AMARELA NO RETÂNGULO INTEIRO =====
        # Calcula bounding box do pattern na tela
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

        # Só desenha a borda se pelo menos parte estiver no viewport
        if (box_x0 + box_w > sm.viewport_x and box_x0 < sm.viewport_x + sm.viewport_width and
                box_y0 + box_h > sm.viewport_y and box_y0 < sm.viewport_y + sm.viewport_height):
            pygame.draw.rect(
                screen, (255, 215, 0),
                (box_x0 - 1, box_y0 - 1, box_w + 2, box_h + 2), 2
            )

        # ===== HINT NO RODAPÉ =====
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

    def _update_camera_values(self):
        """Atualiza valores de câmera"""
        camera = self.editor.camera
        sm = self.editor.screen_manager

        # mesma fórmula que o layer_manager usa
        self._cam_offset_x = round((-camera.x * camera.zoom * sm.render_scale +
                                    (sm.render_width / 2) * sm.render_scale +
                                    sm.viewport_x))
        self._cam_offset_y = round((-camera.y * camera.zoom * sm.render_scale +
                                    (sm.render_height / 2) * sm.render_scale +
                                    sm.viewport_y))

        self._tile_size_scaled = max(1, round(self.editor.grid_size * camera.zoom * sm.render_scale))

    def _render_grid(self, screen):
        """Renderiza o grid com tile_size 24"""
        sm = self.editor.screen_manager

        first_visible_x = (-self._cam_offset_x) // self._tile_size_scaled
        first_visible_y = (-self._cam_offset_y) // self._tile_size_scaled

        tiles_visible_x = (sm.viewport_width // self._tile_size_scaled) + 2
        tiles_visible_y = (sm.viewport_height // self._tile_size_scaled) + 2

        grid_surface = pygame.Surface(
            (sm.viewport_width, sm.viewport_height),
            pygame.SRCALPHA
        )

        # Linhas verticais
        for i in range(tiles_visible_x):
            tile_x = first_visible_x + i
            screen_x = tile_x * self._tile_size_scaled + self._cam_offset_x
            grid_x = screen_x - sm.viewport_x

            if -1 <= grid_x <= sm.viewport_width + 1:
                if tile_x == 0:
                    color = (255, 100, 100, 180)
                    width = 2
                else:
                    color = (100, 100, 100, 100)
                    width = 1

                grid_x_int = int(round(grid_x))
                pygame.draw.line(
                    grid_surface,
                    color,
                    (grid_x_int, 0),
                    (grid_x_int, sm.viewport_height),
                    width
                )

        # Linhas horizontais
        for i in range(tiles_visible_y):
            tile_y = first_visible_y + i
            screen_y = tile_y * self._tile_size_scaled + self._cam_offset_y
            grid_y = screen_y - sm.viewport_y

            if -1 <= grid_y <= sm.viewport_height + 1:
                if tile_y == 0:
                    color = (100, 255, 100, 180)
                    width = 2
                else:
                    color = (100, 100, 100, 100)
                    width = 1

                grid_y_int = int(round(grid_y))
                pygame.draw.line(
                    grid_surface,
                    color,
                    (0, grid_y_int),
                    (sm.viewport_width, grid_y_int),
                    width
                )

        screen.blit(grid_surface, (sm.viewport_x, sm.viewport_y))

    def _world_to_screen(self, world_x, world_y):
        """Converte coordenadas do mundo para tela"""
        camera = self.editor.camera
        sm = self.editor.screen_manager

        screen_x = round((world_x - camera.x) * camera.zoom * sm.render_scale +
                         (sm.render_width / 2) * sm.render_scale +
                         sm.viewport_x)
        screen_y = round((world_y - camera.y) * camera.zoom * sm.render_scale +
                         (sm.render_height / 2) * sm.render_scale +
                         sm.viewport_y)

        return (screen_x, screen_y)

    def _render_map_bounds(self, screen):
        """Renderiza os limites do mapa"""
        current_layer = self.editor.layer_manager.get_current_layer()
        if not current_layer:
            return

        # Limites do mapa
        map_left = self.editor.min_world_x
        map_right = self.editor.max_world_x
        map_top = self.editor.min_world_y
        map_bottom = self.editor.max_world_y

        # Área editável atual
        current_left = 0
        current_right = current_layer.width * self.editor.grid_size
        current_top = 0
        current_bottom = current_layer.height * self.editor.grid_size

        # Converte cantos para coordenadas de tela
        corners = [
            (map_left, map_top),
            (map_right, map_top),
            (map_right, map_bottom),
            (map_left, map_bottom)
        ]

        screen_corners = []
        for world_x, world_y in corners:
            screen_x, screen_y = self._world_to_screen(world_x, world_y)
            screen_corners.append((screen_x, screen_y))

        # Desenha borda do mapa
        if len(screen_corners) == 4:
            pygame.draw.polygon(screen, (255, 100, 100), screen_corners, 2)

        # Desenha área editável atual
        current_corners = [
            (current_left, current_top),
            (current_right, current_top),
            (current_right, current_bottom),
            (current_left, current_bottom)
        ]

        screen_current_corners = []
        for world_x, world_y in current_corners:
            screen_x, screen_y = self._world_to_screen(world_x, world_y)
            screen_current_corners.append((screen_x, screen_y))

        if len(screen_current_corners) == 4:
            pygame.draw.polygon(screen, (100, 255, 100), screen_current_corners, 2)

        # Cantos com marcadores
        for screen_x, screen_y in screen_corners:
            pygame.draw.circle(screen, (255, 100, 100), (screen_x, screen_y), 6)

        # Texto informativo nos cantos
        font = pygame.font.Font(None, 16)

        # Canto superior esquerdo
        text = font.render(f"({map_left:.0f}, {map_top:.0f})", True, (255, 100, 100))
        screen.blit(text, (screen_corners[0][0] + 10, screen_corners[0][1] + 10))

        # Canto superior direito
        text = font.render(f"({map_right:.0f}, {map_top:.0f})", True, (255, 100, 100))
        screen.blit(text, (screen_corners[1][0] - 90, screen_corners[1][1] + 10))

        # Canto inferior direito
        text = font.render(f"({map_right:.0f}, {map_bottom:.0f})", True, (255, 100, 100))
        screen.blit(text, (screen_corners[2][0] - 100, screen_corners[2][1] - 20))

        # Canto inferior esquerdo
        text = font.render(f"({map_left:.0f}, {map_bottom:.0f})", True, (255, 100, 100))
        screen.blit(text, (screen_corners[3][0] + 10, screen_corners[3][1] - 20))

        # Informação da área atual
        info_font = pygame.font.Font(None, 14)
        info_text = info_font.render(f"Área atual: {current_layer.width}x{current_layer.height} tiles", True,
                                     (100, 255, 100))
        screen.blit(info_text, (screen_corners[0][0] + 10, screen_corners[0][1] + 30))

    def _render_eraser_preview(self, screen):
        """Mostra onde a borracha vai apagar (segue o mouse)."""
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

        # Overlay reutilizável
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

        # Dica no rodapé
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
        """Renderiza a borda do viewport"""
        pygame.draw.rect(screen, (100, 100, 100),
                         (self.editor.screen_manager.viewport_x,
                          self.editor.screen_manager.viewport_y,
                          self.editor.screen_manager.viewport_width,
                          self.editor.screen_manager.viewport_height), 2)

    def _render_ui_panels(self, screen):
        """Renderiza os painéis da UI"""
        if self.editor.mode == "layers":
            if hasattr(self.editor, 'brush_buttons') and self.editor.brush_buttons.visible:
                self.editor.brush_buttons.render(screen, self.editor.font_small)

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
        """Renderiza a UI superior"""
        viewport_x = self.editor.screen_manager.viewport_x
        viewport_y = self.editor.screen_manager.viewport_y

        # Painel superior
        pygame.draw.rect(screen, (40, 40, 50),
                         (viewport_x, viewport_y, self.editor.screen_manager.viewport_width, 60))

        # Título
        current_layer = self.editor.layer_manager.get_current_layer()
        if current_layer:
            size_info = f" [{current_layer.width}x{current_layer.height}]"
        else:
            size_info = ""

        title = self.editor.font.render(f"EDITOR DE FASES - {self.editor.phase_name}{size_info}", True, (255, 215, 0))
        screen.blit(title, (viewport_x + 10, viewport_y + 10))

        # Instruções (modificadas para incluir Undo/Redo)
        inst = self.editor.font_small.render(
            "CTRL+S: Salvar | CTRL+O: Carregar | CTRL+I: Importar | CTRL+M: Map Size | "
            "CTRL+Z: Undo | CTRL+Y: Redo | G: Grid | 1-5: Modos | DEL: Remover",
            True, (200, 200, 200))
        screen.blit(inst, (viewport_x + 10, viewport_y + 35))

        # Indicador de Undo/Redo (opcional)
        if self.editor.undo_manager.can_undo() or self.editor.undo_manager.can_redo():
            undo_text = ""
            if self.editor.undo_manager.can_undo():
                undo_desc = self.editor.undo_manager.get_undo_description()
                undo_text = f"Undo: {undo_desc[:20]}..."

            if undo_text:
                undo_surf = self.editor.font_small.render(undo_text, True, (150, 150, 200))
                screen.blit(undo_surf, (viewport_x + self.editor.screen_manager.viewport_width - 300, viewport_y + 35))

        # Botões de modo
        self.editor.mode_buttons.render(screen, self.editor.mode, self.editor.font_small)

        # Informações do modo
        mode_info = {
            "layers": "Clique nos tiles à direita | Selecione layers à esquerda",
            "path": f"Path {self.editor.path_manager.current_path_index + 1}/{len(self.editor.path_manager.paths)} | "
                    f"Esquerdo: add nó | Direito: remove | Ctrl+N: novo path | Ctrl+D: deletar | Ctrl+W: Wave configs | TAB: alternar",
            "towers": "Esquerdo: add spot | Direito: remove",
            "map_config": "Configure o mapa"
        }

        info = self.editor.font_small.render(mode_info.get(self.editor.mode, ""), True, (180, 180, 180))
        screen.blit(info, (viewport_x + 10, viewport_y + self.editor.screen_manager.viewport_height - 20))

    def _render_pause_overlay(self, screen):
        """Renderiza overlay de pausa"""
        overlay = pygame.Surface((self.editor.screen_manager.viewport_width,
                                  self.editor.screen_manager.viewport_height))
        overlay.set_alpha(128)
        overlay.fill((0, 0, 0))
        screen.blit(overlay, (self.editor.screen_manager.viewport_x, self.editor.screen_manager.viewport_y))

        font_large = pygame.font.Font(None, 48)
        pause_text = font_large.render("PAUSADO", True, (255, 255, 255))
        text_x = self.editor.screen_manager.viewport_x + (
                self.editor.screen_manager.viewport_width - pause_text.get_width()) // 2
        text_y = self.editor.screen_manager.viewport_y + (
                self.editor.screen_manager.viewport_height - pause_text.get_height()) // 2
        screen.blit(pause_text, (text_x, text_y))