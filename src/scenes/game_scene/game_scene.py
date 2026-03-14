# src/scenes/game_scene.py

"""
Cena principal do jogo - Carrega fases reais
"""
import pygame
from src.scenes.base_scene import BaseScene
from src.config.phase_catalog import phase_catalog
from src.scenes.game_scene.components.phase_loader import phase_loader
from src.scenes.game_scene.components.renderer.map_renderer import MapRenderer
from src.scenes.game_scene.components.renderer.path_renderer import PathRenderer
from src.scenes.game_scene.components.renderer.tower_spot_renderer import TowerSpotRenderer


class GameScene(BaseScene):
    def __init__(self, game, phase_number=1):
        super().__init__(game)

        self.phase_number = phase_number
        self.phase_info = None

        # Carrega informações da fase do catálogo
        self._load_phase_info()

        # Componentes da fase
        self.map_renderer = MapRenderer()
        self.path_renderer = PathRenderer()
        self.spot_renderer = TowerSpotRenderer()

        # Carrega dados da fase
        self._load_phase_data()

        # Configurações de mundo baseadas no mapa
        self._setup_world_dimensions()

        # Inicializa câmera
        self.game.initialize_camera(self.world_width, self.world_height)
        self.camera = self.game.camera
        self.camera.set_limits(
            -500, self.world_width + 500,
            -500, self.world_height + 500
        )

        # Posiciona câmera no centro do mapa
        self.camera.x = self.world_width / 2
        self.camera.y = self.world_height / 2

        # Configurações da grid
        self.show_grid = True
        self.grid_size = 16
        self.grid_color = (60, 60, 80)
        self.grid_alpha = 100

        # Debug
        self.show_debug = True

        # Controle de arrasto da câmera
        self.dragging_camera = False
        self.last_mouse_pos = None

        # Flag para sincronização de renderização
        self._last_camera_values = None

        print(f"\n=== FASE CARREGADA ===")
        print(f"Fase: {self.phase_info.get('name', 'Desconhecida')}")
        print(f"Capítulo: {self.phase_info.get('chapter', 1)}")
        print(f"Número: {self.phase_number}")
        print(f"Mundo: {self.world_width}x{self.world_height}")
        print(f"Grid ativada por padrão (tecla G para toggle)")
        print(f"Arraste com botão do meio para mover a câmera")
        print("=====================\n")

    def _load_phase_info(self):
        """Carrega informações da fase do catálogo"""
        # Precisa encontrar em qual capítulo está esta fase
        all_phases = phase_catalog.get_all_phases()
        for chapter, phases in all_phases.items():
            for phase in phases:
                if phase["number"] == self.phase_number:
                    self.phase_info = phase
                    return

        # Fallback se não encontrar
        self.phase_info = {
            "name": f"Fase {self.phase_number}",
            "number": self.phase_number,
            "chapter": 1
        }

    def _load_phase_data(self):
        """Carrega os dados da fase do disco"""
        chapter = self.phase_info.get("chapter", 1)
        data = phase_loader.load_phase(chapter, self.phase_number)

        if not data:
            print(f"ERRO: Não foi possível carregar a fase {self.phase_number}")
            return

        # Carrega mapa
        map_data = phase_loader.get_map_data()
        self.map_renderer.load_from_data(map_data, "data/phases")

        # Carrega path
        path_data = phase_loader.get_path_data()
        self.path_renderer.load_from_data(path_data)

        # Carrega spots
        spot_data = phase_loader.get_tower_spots_data()
        self.spot_renderer.load_from_data(spot_data)

    def _setup_world_dimensions(self):
        """Configura dimensões do mundo baseado no mapa"""
        map_width, map_height = self.map_renderer.get_dimensions()

        # Se o mapa foi carregado, usa suas dimensões
        if map_width > 0 and map_height > 0:
            self.world_width = map_width
            self.world_height = map_height
        else:
            # Fallback para tamanho padrão
            self.world_width = 2000
            self.world_height = 2000

    def handle_event(self, event):
        """Processa eventos do jogo"""
        if event.type == pygame.KEYDOWN:
            if event.key == pygame.K_p:
                self.toggle_pause()
            elif event.key == pygame.K_ESCAPE:
                self.game.current_scene = self.game.menu_scene
            elif event.key == pygame.K_F1:
                self.show_debug = not self.show_debug
            elif event.key == pygame.K_g:
                self.show_grid = not self.show_grid
                print(f"[DEBUG] Grid {'ativada' if self.show_grid else 'desativada'}")
            elif event.key == pygame.K_SPACE:
                mouse_pos = pygame.mouse.get_pos()
                if self.screen_manager.is_mouse_in_viewport(mouse_pos):
                    world_pos = self.screen_manager.get_mouse_world_position(mouse_pos, self.camera)
                    if world_pos:
                        print(f"[DEBUG] Posição do mouse no mundo: ({world_pos[0]:.0f}, {world_pos[1]:.0f})")

                        # Mostra informações do tile
                        tile_x = int(world_pos[0] // self.grid_size)
                        tile_y = int(world_pos[1] // self.grid_size)
                        print(f"[DEBUG] Tile: ({tile_x}, {tile_y})")

        elif event.type == pygame.MOUSEBUTTONDOWN:
            mouse_pos = pygame.mouse.get_pos()

            # Verifica se clicou no viewport
            in_viewport = self.screen_manager.is_mouse_in_viewport(mouse_pos)

            if event.button == 1:  # Clique esquerdo
                if in_viewport:
                    world_pos = self.screen_manager.get_mouse_world_position(mouse_pos, self.camera)
                    if world_pos:
                        print(f"[DEBUG] Clique no mundo: ({world_pos[0]:.0f}, {world_pos[1]:.0f})")

            elif event.button == 2:  # Botão do meio/scroll - ARRASTO DA CÂMERA
                if in_viewport:
                    self.dragging_camera = True
                    self.last_mouse_pos = mouse_pos
                    pygame.mouse.set_cursor(pygame.SYSTEM_CURSOR_SIZEALL)
                    return True

        elif event.type == pygame.MOUSEBUTTONUP:
            if event.button == 2:  # Botão do meio/scroll
                if self.dragging_camera:
                    self.dragging_camera = False
                    self.last_mouse_pos = None
                    pygame.mouse.set_cursor(pygame.SYSTEM_CURSOR_ARROW)
                    return True

        elif event.type == pygame.MOUSEMOTION:
            if self.dragging_camera and self.last_mouse_pos:
                dx = event.pos[0] - self.last_mouse_pos[0]
                dy = event.pos[1] - self.last_mouse_pos[1]

                world_dx = dx / self.camera.zoom
                world_dy = dy / self.camera.zoom

                self.camera.x -= world_dx
                self.camera.y -= world_dy
                self.camera._clamp_position()

                self.last_mouse_pos = event.pos
                return True

        elif event.type == pygame.MOUSEWHEEL:
            if not self.paused and not self.dragging_camera:
                mouse_pos = pygame.mouse.get_pos()
                if self.screen_manager.is_mouse_in_viewport(mouse_pos):
                    world_pos = self.screen_manager.get_mouse_world_position(mouse_pos, self.camera)

                    if world_pos:
                        target_world_x, target_world_y = world_pos
                        self.camera.handle_zoom(event.y > 0)

                        new_world_pos = self.screen_manager.get_mouse_world_position(mouse_pos, self.camera)
                        if new_world_pos:
                            dx = target_world_x - new_world_pos[0]
                            dy = target_world_y - new_world_pos[1]
                            self.camera.x += dx
                            self.camera.y += dy
                            self.camera._clamp_position()

    def fixed_update(self, dt):
        """Update da lógica do jogo"""
        if self.paused:
            return

    def render(self, screen):
        """Renderiza o jogo"""
        # Limpa a tela
        screen.fill((0, 0, 0))

        # Renderiza o mapa (usando o mesmo sistema do editor)
        self.map_renderer.render(screen, self.camera, self.screen_manager)

        # Renderiza o path (opcional - para debug)
        if self.show_debug:
            self.path_renderer.render(screen, self.camera, self.screen_manager, show_editing=False)

        # Desenha a grid se ativada (usando o mesmo cálculo dos tiles)
        if self.show_grid:
            self._draw_grid_aligned(screen)

        # Desenha borda do viewport
        pygame.draw.rect(screen, (80, 80, 80),
                        (self.screen_manager.viewport_x,
                         self.screen_manager.viewport_y,
                         self.screen_manager.viewport_width,
                         self.screen_manager.viewport_height), 1)

        # UI mínima
        self._render_minimal_ui(screen)

        # Overlay de pausa
        if self.paused:
            self._render_pause_overlay(screen)

        # Debug info
        if self.show_debug:
            self._render_debug_info(screen)

    def _draw_grid_aligned(self, screen):
        """
        Desenha a grid usando os MESMOS cálculos que o layer_manager
        para garantir alinhamento perfeito com os tiles
        """
        camera = self.camera
        sm = self.screen_manager

        # Calcula offset da câmera (igual ao layer_manager)
        cam_offset_x = round((-camera.x * camera.zoom * sm.render_scale +
                             (sm.render_width / 2) * sm.render_scale +
                             sm.viewport_x))
        cam_offset_y = round((-camera.y * camera.zoom * sm.render_scale +
                             (sm.render_height / 2) * sm.render_scale +
                             sm.viewport_y))

        tile_size_scaled = max(1, round(self.grid_size * camera.zoom * sm.render_scale))

        # Calcula primeiro tile visível
        first_visible_x = (-cam_offset_x) // tile_size_scaled
        first_visible_y = (-cam_offset_y) // tile_size_scaled

        # Quantos tiles cabem na tela
        tiles_visible_x = (sm.viewport_width // tile_size_scaled) + 3
        tiles_visible_y = (sm.viewport_height // tile_size_scaled) + 3

        # Cria superfície para a grid
        grid_surface = pygame.Surface(
            (sm.viewport_width, sm.viewport_height),
            pygame.SRCALPHA
        )

        # Desenha linhas verticais
        for i in range(tiles_visible_x):
            tile_x = first_visible_x + i
            screen_x = tile_x * tile_size_scaled + cam_offset_x
            grid_x = screen_x - sm.viewport_x

            if -tile_size_scaled <= grid_x <= sm.viewport_width + tile_size_scaled:
                # Linhas mais sutis no jogo
                if tile_x == 0:
                    color = (100, 100, 150, 150)  # Eixo Y
                else:
                    color = (60, 60, 80, 80)  # Grid normal

                pygame.draw.line(
                    grid_surface,
                    color,
                    (grid_x, 0),
                    (grid_x, sm.viewport_height),
                    1
                )

        # Desenha linhas horizontais
        for i in range(tiles_visible_y):
            tile_y = first_visible_y + i
            screen_y = tile_y * tile_size_scaled + cam_offset_y
            grid_y = screen_y - sm.viewport_y

            if -tile_size_scaled <= grid_y <= sm.viewport_height + tile_size_scaled:
                if tile_y == 0:
                    color = (150, 100, 100, 150)  # Eixo X
                else:
                    color = (60, 60, 80, 80)  # Grid normal

                pygame.draw.line(
                    grid_surface,
                    color,
                    (0, grid_y),
                    (sm.viewport_width, grid_y),
                    1
                )

        screen.blit(grid_surface, (sm.viewport_x, sm.viewport_y))

    def _render_minimal_ui(self, screen):
        """UI mínima com instruções"""
        font_small = pygame.font.Font(None, 20)

        grid_status = "ON" if self.show_grid else "OFF"
        grid_color = (0, 255, 0) if self.show_grid else (255, 0, 0)

        # Nome da fase
        phase_display = self.phase_info.get("name", f"Fase {self.phase_number}")
        phase_text = font_small.render(phase_display, True, (200, 200, 0))
        phase_x = self.screen_manager.viewport_x + 10
        phase_y = self.screen_manager.viewport_y + 10
        screen.blit(phase_text, (phase_x, phase_y))

        # Instruções
        inst_text = f"F1:Debug | G:Grid [{grid_status}] | P:Pause | ESC:Menu | SPACE:Log | Scroll+Arrasto: Mover"
        inst = font_small.render(inst_text, True, (150, 150, 150))
        inst_x = self.screen_manager.viewport_x + (self.screen_manager.viewport_width - inst.get_width()) // 2
        screen.blit(inst, (inst_x, self.screen_manager.viewport_y + 10))

        # Dimensões do mapa
        map_info = f"Mapa: {self.map_renderer.layer_manager.width}x{self.map_renderer.layer_manager.height} tiles"
        map_text = font_small.render(map_info, True, (100, 100, 100))
        map_x = self.screen_manager.viewport_x + self.screen_manager.viewport_width - map_text.get_width() - 10
        map_y = self.screen_manager.viewport_y + 10
        screen.blit(map_text, (map_x, map_y))

    def _render_pause_overlay(self, screen):
        """Overlay de pausa do jogo"""
        overlay = pygame.Surface((self.screen_manager.viewport_width,
                                 self.screen_manager.viewport_height))
        overlay.set_alpha(128)
        overlay.fill((0, 0, 0))
        screen.blit(overlay, (self.screen_manager.viewport_x, self.screen_manager.viewport_y))

        font_large = pygame.font.Font(None, 48)
        pause_text = font_large.render("PAUSADO", True, (255, 255, 255))
        text_x = self.screen_manager.viewport_x + (self.screen_manager.viewport_width - pause_text.get_width()) // 2
        text_y = self.screen_manager.viewport_y + (self.screen_manager.viewport_height - pause_text.get_height()) // 2
        screen.blit(pause_text, (text_x, text_y))

        # Mostra nome da fase no pause
        font_small = pygame.font.Font(None, 24)
        phase_display = self.phase_info.get("name", f"Fase {self.phase_number}")
        phase_text = font_small.render(phase_display, True, (200, 200, 200))
        phase_x = self.screen_manager.viewport_x + (self.screen_manager.viewport_width - phase_text.get_width()) // 2
        phase_y = text_y + pause_text.get_height() + 10
        screen.blit(phase_text, (phase_x, phase_y))

    def _render_debug_info(self, screen):
        """Informações de debug detalhadas"""
        mouse_pos = pygame.mouse.get_pos()
        in_viewport = self.screen_manager.is_mouse_in_viewport(mouse_pos)

        if in_viewport:
            world_pos = self.screen_manager.get_mouse_world_position(mouse_pos, self.camera)
            if world_pos:
                world_text = f"World: ({world_pos[0]:.0f}, {world_pos[1]:.0f})"
                tile_x = int(world_pos[0] // self.grid_size)
                tile_y = int(world_pos[1] // self.grid_size)
                tile_info = f"Tile: ({tile_x}, {tile_y})"

                # Pega o tile da layer atual (primeira layer ground)
                tile_id = 0
                for layer in self.map_renderer.layer_manager.layers:
                    if layer.layer_type.value == "ground":
                        tile_id = layer.get_tile(tile_x, tile_y)
                        break
                tile_value = f"Tile ID: {tile_id}"
            else:
                world_text = "World: invalid position"
                tile_info = "Tile: N/A"
                tile_value = "Tile ID: N/A"
        else:
            world_text = "World: outside viewport"
            tile_info = "Tile: outside"
            tile_value = "Tile ID: N/A"

        debug_lines = [
            "=== DEBUG INFO ===",
            f"Fase: {self.phase_info.get('name', 'Desconhecida')}",
            f"Capítulo: {self.phase_info.get('chapter', 1)} | Nº: {self.phase_number}",
            f"FPS: {self.screen_manager.get_fps():.1f}",
            f"Delta Time: {self.screen_manager.get_delta_time()*1000:.1f}ms",
            f"Grid: {'ON' if self.show_grid else 'OFF'}",
            f"Camera Drag: {'ACTIVE' if self.dragging_camera else 'inactive'}",
            "",
            "=== CAMERA ===",
            f"Position: ({self.camera.x:.0f}, {self.camera.y:.0f})",
            f"Zoom: {self.camera.zoom:.2f}",
            f"Visible: {self.screen_manager.render_width/self.camera.zoom:.0f} x {self.screen_manager.render_height/self.camera.zoom:.0f}",
            "",
            "=== SCREEN ===",
            f"Window: {self.screen_manager.window_width}x{self.screen_manager.window_height}",
            f"Viewport: {self.screen_manager.viewport_width}x{self.screen_manager.viewport_height}",
            f"Scale: {self.screen_manager.render_scale:.2f}",
            "",
            "=== MOUSE ===",
            f"Screen: ({mouse_pos[0]}, {mouse_pos[1]})",
            f"In Viewport: {in_viewport}",
            world_text,
            tile_info,
            tile_value,
            "",
            "=== MAPA ===",
            f"Tiles: {self.map_renderer.layer_manager.width}x{self.map_renderer.layer_manager.height}",
            f"Pixels: {self.world_width}x{self.world_height}",
            f"Grid size: {self.grid_size}px",
            f"Path points: {len(self.path_renderer.path.nodes)}",
            f"Tower spots: {len(self.spot_renderer.spot_manager.spots)}"
        ]

        y_offset = self.screen_manager.viewport_y + 40
        x_offset = self.screen_manager.viewport_x + 10
        font_small = pygame.font.Font(None, 18)

        line_height = 16
        bg_height = len(debug_lines) * line_height + 10
        bg_width = 400
        bg_surface = pygame.Surface((bg_width, bg_height))
        bg_surface.set_alpha(180)
        bg_surface.fill((0, 0, 0))
        screen.blit(bg_surface, (x_offset - 5, y_offset - 5))

        for line in debug_lines:
            if line.startswith("==="):
                color = (255, 255, 0)
                font_bold = pygame.font.Font(None, 20)
                text = font_bold.render(line, True, color)
            else:
                color = (0, 255, 0)
                text = font_small.render(line, True, color)

            screen.blit(text, (x_offset, y_offset))
            y_offset += line_height