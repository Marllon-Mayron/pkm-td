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

        # NOVO: Diálogo de gerenciamento de tilesets (deve ser o primeiro para aparecer por cima)
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