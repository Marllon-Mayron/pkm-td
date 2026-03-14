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
        print(
            f"Renderizando preview: {len(self.editor.test_towers)} torres, {len(self.editor.test_enemies)} inimigos")  # Debug

        for tower in self.editor.test_towers:
            tower.render(screen, self.editor.camera, self.editor.screen_manager)

        if self.editor.test_enemies:
            for i, enemy in enumerate(self.editor.test_enemies):
                print(f"Renderizando inimigo {i}")  # Debug
                enemy.render(screen, self.editor.camera, self.editor.screen_manager)
        else:
            print("Nenhum inimigo para renderizar!")

    def _render_grid(self, screen):
        """Renderiza o grid alinhado perfeitamente com os tiles"""
        if not self.editor.show_grid:
            return

        # Calcula o retângulo visível no mundo
        visible_rect = self.editor.camera.get_visible_rect()

        # Converte para coordenadas de grid
        start_col = int(visible_rect.left // self.editor.grid_size)
        start_row = int(visible_rect.top // self.editor.grid_size)
        end_col = int(visible_rect.right // self.editor.grid_size) + 1
        end_row = int(visible_rect.bottom // self.editor.grid_size) + 1

        # Cria superfície para a grid (mesmo tamanho do viewport)
        grid_surface = pygame.Surface(
            (self.editor.screen_manager.viewport_width,
             self.editor.screen_manager.viewport_height),
            pygame.SRCALPHA
        )

        # Desenha linhas verticais
        for col in range(start_col, end_col + 1):
            # Posição mundial da linha
            world_x = col * self.editor.grid_size

            # Converte para coordenadas de tela
            screen_x, _ = self._world_to_screen(world_x, 0)

            # Ajusta para coordenadas locais do viewport
            grid_x = screen_x - self.editor.screen_manager.viewport_x

            # Só desenha se estiver dentro do viewport
            if 0 <= grid_x <= self.editor.screen_manager.viewport_width:
                # Cor diferente para o eixo 0 (origem)
                if col == 0:
                    color = (255, 100, 100, 180)  # Vermelho para eixo Y
                    width = 2
                else:
                    color = (100, 100, 100, 100)  # Cinza para as demais
                    width = 1

                pygame.draw.line(
                    grid_surface,
                    color,
                    (grid_x, 0),
                    (grid_x, self.editor.screen_manager.viewport_height),
                    width
                )

        # Desenha linhas horizontais
        for row in range(start_row, end_row + 1):
            # Posição mundial da linha
            world_y = row * self.editor.grid_size

            # Converte para coordenadas de tela
            _, screen_y = self._world_to_screen(0, world_y)

            # Ajusta para coordenadas locais do viewport
            grid_y = screen_y - self.editor.screen_manager.viewport_y

            # Só desenha se estiver dentro do viewport
            if 0 <= grid_y <= self.editor.screen_manager.viewport_height:
                # Cor diferente para o eixo 0 (origem)
                if row == 0:
                    color = (100, 255, 100, 180)  # Verde para eixo X
                    width = 2
                else:
                    color = (100, 100, 100, 100)  # Cinza para as demais
                    width = 1

                pygame.draw.line(
                    grid_surface,
                    color,
                    (0, grid_y),
                    (self.editor.screen_manager.viewport_width, grid_y),
                    width
                )

        # Desenha pontos nas interseções (opcional - para melhor visualização)
        if self.editor.camera.zoom > 1.5:  # Só mostra pontos quando muito zoom
            for col in range(start_col, end_col + 1):
                for row in range(start_row, end_row + 1):
                    world_x = col * self.editor.grid_size
                    world_y = row * self.editor.grid_size

                    screen_x, screen_y = self._world_to_screen(world_x, world_y)
                    grid_x = screen_x - self.editor.screen_manager.viewport_x
                    grid_y = screen_y - self.editor.screen_manager.viewport_y

                    if (0 <= grid_x <= self.editor.screen_manager.viewport_width and
                            0 <= grid_y <= self.editor.screen_manager.viewport_height):
                        # Ponto mais visível nas interseções
                        color = (200, 200, 0, 200) if col == 0 or row == 0 else (150, 150, 150, 150)
                        pygame.draw.circle(grid_surface, color, (int(grid_x), int(grid_y)), 2)

        # Aplica a grid na tela
        screen.blit(grid_surface, (self.editor.screen_manager.viewport_x, self.editor.screen_manager.viewport_y))

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

        # Desenha borda do mapa (limites máximos)
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
        """Converte coordenadas do mundo para coordenadas de tela (pixel perfeito)"""
        # Calcula posição na superfície de renderização
        render_x = (
                               world_x - self.editor.camera.x) * self.editor.camera.zoom + self.editor.screen_manager.render_width / 2
        render_y = (
                               world_y - self.editor.camera.y) * self.editor.camera.zoom + self.editor.screen_manager.render_height / 2

        # Converte para coordenadas de tela
        screen_x = render_x * self.editor.screen_manager.render_scale + self.editor.screen_manager.viewport_x
        screen_y = render_y * self.editor.screen_manager.render_scale + self.editor.screen_manager.viewport_y

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