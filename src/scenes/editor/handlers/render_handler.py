# src/scenes/editor/handlers/render_handler.py (versão final corrigida)

import pygame


class EditorRenderHandler:
    """Gerencia a renderização do editor"""

    def __init__(self, editor_scene):
        self.editor = editor_scene

    def render(self, screen):
        """Renderiza todos os elementos do editor"""
        screen.fill((30, 30, 40))

        # Renderiza mapa
        self.editor.layer_manager.render_all(screen, self.editor.camera, self.editor.screen_manager)

        # Elementos de edição
        if self.editor.mode != "preview":
            self.editor.tower_spots.render(screen, self.editor.camera, self.editor.screen_manager)
        self.editor.path.render(screen, self.editor.camera, self.editor.screen_manager)

        # Preview
        if self.editor.mode == "preview":
            self._render_preview(screen)

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

        # Diálogo de tamanho do mapa
        if self.editor.map_config_dialog and self.editor.map_config_dialog.visible:
            self.editor.map_config_dialog.render(screen)

        # Pause
        if self.editor.paused:
            self._render_pause_overlay(screen)

    def _render_preview(self, screen):
        """Renderiza elementos de preview"""
        for tower in self.editor.test_towers:
            tower.render(screen, self.editor.camera, self.editor.screen_manager)

        for enemy in self.editor.test_enemies:
            enemy.render(screen, self.editor.camera, self.editor.screen_manager)

    def _render_grid(self, screen):
        """Renderiza o grid alinhado perfeitamente com os tiles"""
        if not self.editor.show_grid:
            return

        # Obtém parâmetros necessários
        camera = self.editor.camera
        screen_manager = self.editor.screen_manager
        grid_size = self.editor.grid_size

        # --- CÁLCULO EXATAMENTE IGUAL AO LAYER_MANAGER.PY ---
        # PRÉ-CALCULA usando inteiros (igual ao layer_manager)
        cam_offset_x = int(-camera.x * camera.zoom * screen_manager.render_scale +
                           (screen_manager.render_width / 2) * screen_manager.render_scale +
                           screen_manager.viewport_x)
        cam_offset_y = int(-camera.y * camera.zoom * screen_manager.render_scale +
                           (screen_manager.render_height / 2) * screen_manager.render_scale +
                           screen_manager.viewport_y)

        tile_size_scaled = int(grid_size * camera.zoom * screen_manager.render_scale)

        # Calcula o primeiro tile visível
        # Em vez de usar visible_rect, calculamos a partir do offset
        # Isso garante que a grid comece no mesmo lugar que os tiles
        first_visible_x = -cam_offset_x // tile_size_scaled
        first_visible_y = -cam_offset_y // tile_size_scaled

        # Quantos tiles cabem na tela (com margem para evitar gaps)
        tiles_visible_x = (screen_manager.viewport_width // tile_size_scaled) + 2
        tiles_visible_y = (screen_manager.viewport_height // tile_size_scaled) + 2

        # Cria superfície para a grid
        grid_surface = pygame.Surface(
            (screen_manager.viewport_width, screen_manager.viewport_height),
            pygame.SRCALPHA
        )

        # Desenha linhas verticais
        for i in range(tiles_visible_x):
            tile_x = first_visible_x + i

            # Posição na tela - MESMA FÓRMULA DO LAYER_MANAGER
            screen_x = tile_x * tile_size_scaled + cam_offset_x

            # Converte para coordenadas locais do viewport
            grid_x = screen_x - screen_manager.viewport_x

            # Verifica se está dentro do viewport (com pequena margem)
            if -tile_size_scaled <= grid_x <= screen_manager.viewport_width + tile_size_scaled:
                # Cor diferente para o eixo Y (x=0)
                if tile_x == 0:
                    color = (255, 100, 100, 180)
                    width = 2
                else:
                    color = (100, 100, 100, 100)
                    width = 1

                # Desenha a linha - usa grid_x diretamente, sem arredondar
                # O Pygame já lida com floats convertendo para ints no momento do desenho
                pygame.draw.line(
                    grid_surface,
                    color,
                    (grid_x, 0),
                    (grid_x, screen_manager.viewport_height),
                    width
                )

        # Desenha linhas horizontais
        for i in range(tiles_visible_y):
            tile_y = first_visible_y + i

            # Posição na tela - MESMA FÓRMULA DO LAYER_MANAGER
            screen_y = tile_y * tile_size_scaled + cam_offset_y

            # Converte para coordenadas locais do viewport
            grid_y = screen_y - screen_manager.viewport_y

            # Verifica se está dentro do viewport (com pequena margem)
            if -tile_size_scaled <= grid_y <= screen_manager.viewport_height + tile_size_scaled:
                # Cor diferente para o eixo X (y=0)
                if tile_y == 0:
                    color = (100, 255, 100, 180)
                    width = 2
                else:
                    color = (100, 100, 100, 100)
                    width = 1

                # Desenha a linha
                pygame.draw.line(
                    grid_surface,
                    color,
                    (0, grid_y),
                    (screen_manager.viewport_width, grid_y),
                    width
                )

        # Aplica a grid na tela
        screen.blit(grid_surface, (screen_manager.viewport_x, screen_manager.viewport_y))

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
            screen_corners.append((int(screen_x), int(screen_y)))

        # Desenha borda do mapa (limites máximos)
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
            screen_current_corners.append((int(screen_x), int(screen_y)))

        if len(screen_current_corners) == 4:
            pygame.draw.polygon(screen, (100, 255, 100), screen_current_corners, 2)

        # Cantos com marcadores
        for screen_x, screen_y in screen_corners:
            pygame.draw.circle(screen, (255, 100, 100), (int(screen_x), int(screen_y)), 6)

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

    def _world_to_screen(self, world_x, world_y):
        """Converte coordenadas do mundo para coordenadas de tela"""
        camera = self.editor.camera
        screen_manager = self.editor.screen_manager

        # Usa o mesmo cálculo do layer_manager para consistência
        screen_x = int((world_x - camera.x) * camera.zoom * screen_manager.render_scale +
                       (screen_manager.render_width / 2) * screen_manager.render_scale +
                       screen_manager.viewport_x)
        screen_y = int((world_y - camera.y) * camera.zoom * screen_manager.render_scale +
                       (screen_manager.render_height / 2) * screen_manager.render_scale +
                       screen_manager.viewport_y)

        return (screen_x, screen_y)

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

        # Instruções
        inst = self.editor.font_small.render(
            "CTRL+S: Salvar | CTRL+O: Carregar | CTRL+I: Importar | CTRL+M: Map Size | G: Grid | 1-5: Modos | DEL: Remover",
            True, (200, 200, 200))
        screen.blit(inst, (viewport_x + 10, viewport_y + 35))

        # Botões de modo
        self.editor.mode_buttons.render(screen, self.editor.mode, self.editor.font_small)

        # Informações do modo
        mode_info = {
            "layers": "Clique nos tiles à direita | Selecione layers à esquerda",
            "path": "Esquerdo: add nó | Shift+Click: fim | Direito: remove",
            "towers": "Esquerdo: add spot | Direito: remove",
            "preview": f"Velocidade: {self.editor.preview_speed:.1f}x | +/ - para ajustar",
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