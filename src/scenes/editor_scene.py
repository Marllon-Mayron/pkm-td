"""
Cena do Editor de Fases
"""
import pygame
import os
from src.scenes.base_scene import BaseScene
from src.editor.layer_manager import LayerManager, LayerType
from src.editor.path_editor import Path
from src.editor.tower_spot_editor import TowerSpotManager
from src.editor.phase_exporter import PhaseExporter
from tkinter import filedialog, Tk

class TestEnemy:
    def __init__(self, path_nodes):
        self.path_nodes = path_nodes
        self.current_node = 0
        self.progress = 0.0
        self.speed = 0.1
        self.position = path_nodes[0] if path_nodes else (0, 0)
        self.active = len(path_nodes) > 0

    def update(self, dt):
        if not self.active or len(self.path_nodes) < 2:
            return

        self.progress += self.speed * dt * 60

        if self.progress >= 1.0:
            self.progress = 0.0
            self.current_node = (self.current_node + 1) % (len(self.path_nodes) - 1)

        start = self.path_nodes[self.current_node]
        end = self.path_nodes[self.current_node + 1]

        self.position = (
            start[0] + (end[0] - start[0]) * self.progress,
            start[1] + (end[1] - start[1]) * self.progress
        )

    def render(self, screen, camera, screen_manager):
        if not self.active:
            return

        render_x = (self.position[0] - camera.x) * camera.zoom + screen_manager.render_width / 2
        render_y = (self.position[1] - camera.y) * camera.zoom + screen_manager.render_height / 2
        screen_x, screen_y = screen_manager.get_screen_position(render_x, render_y)

        size = int(20 * camera.zoom)
        pygame.draw.circle(screen, (255, 0, 0), (int(screen_x), int(screen_y)), size)
        pygame.draw.circle(screen, (255, 255, 255), (int(screen_x), int(screen_y)), size, 2)

        eye_size = max(2, int(4 * camera.zoom))
        pygame.draw.circle(screen, (255, 255, 255),
                          (int(screen_x - size/3), int(screen_y - size/3)), eye_size)
        pygame.draw.circle(screen, (255, 255, 255),
                          (int(screen_x + size/3), int(screen_y - size/3)), eye_size)
        pygame.draw.circle(screen, (0, 0, 0),
                          (int(screen_x - size/3), int(screen_y - size/3)), max(1, eye_size//2))
        pygame.draw.circle(screen, (0, 0, 0),
                          (int(screen_x + size/3), int(screen_y - size/3)), max(1, eye_size//2))

class TestTower:
    def __init__(self, x, y):
        self.x = x
        self.y = y
        self.rotation = 0

    def update(self, dt):
        self.rotation += dt * 50

    def render(self, screen, camera, screen_manager):
        render_x = (self.x - camera.x) * camera.zoom + screen_manager.render_width / 2
        render_y = (self.y - camera.y) * camera.zoom + screen_manager.render_height / 2
        screen_x, screen_y = screen_manager.get_screen_position(render_x, render_y)

        size = int(25 * camera.zoom)

        pygame.draw.rect(screen, (0, 100, 200),
                        (screen_x - size//2, screen_y - size//2, size, size))

        cannon_length = size
        end_x = screen_x + cannon_length * 0.8 * pygame.math.Vector2(1, 0).rotate(self.rotation).x
        end_y = screen_y + cannon_length * 0.8 * pygame.math.Vector2(1, 0).rotate(self.rotation).y

        pygame.draw.line(screen, (200, 200, 100),
                        (screen_x, screen_y), (end_x, end_y), max(2, int(5 * camera.zoom)))

        pygame.draw.circle(screen, (255, 255, 0), (int(screen_x), int(screen_y)), max(3, int(8 * camera.zoom)))

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
        self.max_tile_size = 16

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

    def set_tileset(self, tileset):
        self.tiles = tileset
        self.selected_tile = 0
        self._update_max_scroll()

    def _update_max_scroll(self):
        if not self.tiles:
            self.max_scroll = 0
            return

        rows = (len(self.tiles) + self.cols - 1) // self.cols
        content_height = rows * (self.tile_size + self.tile_spacing)
        visible_height = self.rect.height - 40
        self.max_scroll = max(0, content_height - visible_height)

    def handle_event(self, event):
        if not self.visible:
            return False

        mouse_pos = pygame.mouse.get_pos()
        mouse_x, mouse_y = mouse_pos

        # Verifica se o mouse está sobre a palette
        self.focused = self.rect.collidepoint(mouse_x, mouse_y)

        if event.type == pygame.MOUSEBUTTONDOWN:
            if event.button == 1:
                # Redimensionamento
                if (self.rect.right - self.resize_margin <= mouse_x <= self.rect.right + self.resize_margin and
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

                # Seleção de tile (só se tiver foco)
                if self.focused:
                    local_x = mouse_x - self.rect.x - 5
                    local_y = mouse_y - self.rect.y - 35 + self.scroll_y

                    col = local_x // (self.tile_size + self.tile_spacing)
                    row = local_y // (self.tile_size + self.tile_spacing)

                    if 0 <= col < self.cols:
                        tile_index = row * self.cols + col
                        if 0 <= tile_index < len(self.tiles):
                            self.selected_tile = tile_index
                            return True

            elif event.button == 4:
                if self.focused:
                    self.scroll_y = max(0, self.scroll_y - 30)
                    return True
            elif event.button == 5:
                if self.focused:
                    self.scroll_y = min(self.max_scroll, self.scroll_y + 30)
                    return True

        elif event.type == pygame.MOUSEBUTTONUP:
            if event.button == 1:
                self.resizing = False
                self.dragging = False

        elif event.type == pygame.MOUSEMOTION:
            if self.resizing:
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

        elif event.type == pygame.KEYDOWN:
            if self.focused:
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
                elif event.key == pygame.K_1:
                    if pygame.key.get_mods() & pygame.KMOD_CTRL:
                        self.cols = 1
                        self._update_max_scroll()
                        return True
                elif event.key == pygame.K_2:
                    if pygame.key.get_mods() & pygame.KMOD_CTRL:
                        self.cols = 2
                        self._update_max_scroll()
                        return True
                elif event.key == pygame.K_3:
                    if pygame.key.get_mods() & pygame.KMOD_CTRL:
                        self.cols = 3
                        self._update_max_scroll()
                        return True
                elif event.key == pygame.K_4:
                    if pygame.key.get_mods() & pygame.KMOD_CTRL:
                        self.cols = 4
                        self._update_max_scroll()
                        return True
                elif event.key == pygame.K_5:
                    if pygame.key.get_mods() & pygame.KMOD_CTRL:
                        self.cols = 5
                        self._update_max_scroll()
                        return True
                elif event.key == pygame.K_6:
                    if pygame.key.get_mods() & pygame.KMOD_CTRL:
                        self.cols = 6
                        self._update_max_scroll()
                        return True

        return False

    def render(self, screen):
        if not self.visible:
            return

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

        # Título
        title_font = pygame.font.Font(None, 20)
        title = title_font.render("TILES", True, (255, 255, 255))
        screen.blit(title, (self.rect.x + 10, self.rect.y + 5))

        # Informações
        info_text = f"{self.tile_size}px | {self.cols}col"
        info = title_font.render(info_text, True, (200, 200, 200))
        screen.blit(info, (self.rect.x + self.rect.width - 70, self.rect.y + 5))

        # Instruções
        if self.focused:
            hint_font = pygame.font.Font(None, 14)
            hint = hint_font.render("Ctrl + 1-6 :cols | Ctrl + ± :size", True, (150, 150, 150))
            screen.blit(hint, (self.rect.x + 10, self.rect.y + 20))

        # Área de clipping
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

        # Barra de scroll
        if self.focused and self.max_scroll > 0:
            visible_height = self.rect.height - 35
            scrollbar_height = max(30, visible_height * (visible_height / (visible_height + self.max_scroll)))
            scrollbar_y = self.rect.y + 35 + (self.scroll_y / self.max_scroll) * (visible_height - scrollbar_height)

            scrollbar_bg = pygame.Rect(
                self.rect.x + self.rect.width - 10,
                self.rect.y + 35,
                5,
                visible_height
            )
            pygame.draw.rect(screen, (70, 70, 80), scrollbar_bg)

            scrollbar = pygame.Rect(
                self.rect.x + self.rect.width - 10,
                scrollbar_y,
                5,
                scrollbar_height
            )
            pygame.draw.rect(screen, (150, 150, 160), scrollbar)
            pygame.draw.rect(screen, (200, 200, 210), scrollbar, 1)

        # Área de redimensionamento
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

class LayerSelector:
    def __init__(self, x, y, width, height):
        self.rect = pygame.Rect(x, y, width, height)
        self.layers = []
        self.selected_layer = 0
        self.visible = True
        self.focused = False

        # Para redimensionamento
        self.resizing = False
        self.resize_margin = 10
        self.min_width = 120
        self.min_height = 150

        # Para arrastar
        self.dragging = False
        self.drag_start_x = 0
        self.drag_start_y = 0

    def set_layers(self, layers):
        self.layers = layers

    def handle_event(self, event):
        if not self.visible:
            return False

        mouse_pos = pygame.mouse.get_pos()
        mouse_x, mouse_y = mouse_pos

        # Verifica foco
        self.focused = self.rect.collidepoint(mouse_x, mouse_y)

        if event.type == pygame.MOUSEBUTTONDOWN:
            if event.button == 1:
                # Redimensionamento
                if (self.rect.right - self.resize_margin <= mouse_x <= self.rect.right + self.resize_margin and
                    self.rect.bottom - self.resize_margin <= mouse_y <= self.rect.bottom + self.resize_margin):
                    self.resizing = True
                    return True

                # Arrastar pelo título
                title_rect = pygame.Rect(self.rect.x, self.rect.y, self.rect.width, 25)
                if title_rect.collidepoint(mouse_x, mouse_y):
                    self.dragging = True
                    self.drag_start_x = mouse_x - self.rect.x
                    self.drag_start_y = mouse_y - self.rect.y
                    return True

                # Selecionar layer (só com foco)
                if self.focused:
                    local_y = mouse_y - self.rect.y - 30
                    index = local_y // 28
                    if 0 <= index < len(self.layers):
                        self.selected_layer = index
                        return True

        elif event.type == pygame.MOUSEBUTTONUP:
            if event.button == 1:
                self.resizing = False
                self.dragging = False

        elif event.type == pygame.MOUSEMOTION:
            if self.resizing:
                new_width = max(self.min_width, mouse_x - self.rect.x)
                new_height = max(self.min_height, mouse_y - self.rect.y)
                self.rect.width = new_width
                self.rect.height = new_height
                return True
            elif self.dragging:
                self.rect.x = mouse_x - self.drag_start_x
                self.rect.y = mouse_y - self.drag_start_y
                return True

        return False

    def render(self, screen, current_layer_index):
        if not self.visible:
            return

        # Sombra
        shadow_rect = self.rect.copy()
        shadow_rect.x += 3
        shadow_rect.y += 3
        pygame.draw.rect(screen, (20, 20, 30), shadow_rect, border_radius=8)

        # Fundo
        if self.focused:
            bg_color = (60, 60, 75)
            border_color = (140, 140, 160)
        else:
            bg_color = (45, 45, 55)
            border_color = (90, 90, 100)

        pygame.draw.rect(screen, bg_color, self.rect, border_radius=8)
        pygame.draw.rect(screen, border_color, self.rect, 2, border_radius=8)

        # Título
        font = pygame.font.Font(None, 20)
        title = font.render("LAYERS", True, (255, 255, 255))
        screen.blit(title, (self.rect.x + 10, self.rect.y + 5))

        # Cores para cada tipo
        type_colors = {
            LayerType.GROUND: (80, 80, 90),
            LayerType.DECORATION: (70, 100, 70),
            LayerType.CEILING: (100, 70, 70),
        }

        type_names = {
            LayerType.GROUND: "Chão",
            LayerType.DECORATION: "Decoração",
            LayerType.CEILING: "Teto",
        }

        # Área de clipping
        clip_rect = pygame.Rect(
            self.rect.x + 5,
            self.rect.y + 30,
            self.rect.width - 10,
            self.rect.height - 35
        )

        old_clip = screen.get_clip()
        screen.set_clip(clip_rect)

        # Lista layers
        y_offset = 0
        for i, layer in enumerate(self.layers):
            layer_rect = pygame.Rect(
                self.rect.x + 5,
                self.rect.y + 30 + y_offset,
                self.rect.width - 10,
                25
            )

            bg_color = type_colors.get(layer.layer_type, (80, 80, 80))

            if i == current_layer_index:
                bg_color = tuple(min(255, c + 40) for c in bg_color)
                border_color = (255, 255, 255)
            else:
                border_color = (80, 80, 90)

            pygame.draw.rect(screen, bg_color, layer_rect)
            pygame.draw.rect(screen, border_color, layer_rect, 1)

            # Nome da layer
            name_font = pygame.font.Font(None, 14)
            name_text = f"{layer.name[:8]}"
            name_surf = name_font.render(name_text, True, (255, 255, 255))
            screen.blit(name_surf, (layer_rect.x + 3, layer_rect.y + 5))

            # Tipo abreviado
            type_abbr = {
                LayerType.GROUND: "C",
                LayerType.DECORATION: "D",
                LayerType.CEILING: "T",
            }
            type_surf = name_font.render(type_abbr[layer.layer_type], True, (200, 200, 200))
            screen.blit(type_surf, (layer_rect.x + 40, layer_rect.y + 5))

            # Indicador de visibilidade
            vis_color = (0, 255, 0) if layer.visible else (100, 100, 100)
            pygame.draw.circle(screen, vis_color, (layer_rect.right - 10, layer_rect.centery), 4)

            y_offset += 28

        screen.set_clip(old_clip)

        # Área de redimensionamento
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

class EditorScene(BaseScene):
    def __init__(self, game, chapter=None, phase=None):
        super().__init__(game)

        # Dimensões do mundo
        self.world_width = 3000
        self.world_height = 3000

        # Inicializa câmera
        self.game.initialize_camera(self.world_width, self.world_height)
        self.camera = self.game.camera

        # Gerenciadores
        self.layer_manager = LayerManager()
        self.path = Path()
        self.tower_spots = TowerSpotManager()
        self.exporter = PhaseExporter()

        # Estado do editor
        self.mode = "layers"
        self.current_tile = 1
        self.show_grid = True
        self.grid_size = 16
        self.snap_to_grid = True

        # Elementos de visualização
        self.test_enemies = []
        self.test_towers = []
        self.preview_speed = 1.0

        # UI Panels
        self.tile_palette = None
        self.layer_selector = None

        # Fontes
        self.font = pygame.font.Font(None, 24)
        self.font_small = pygame.font.Font(None, 18)

        # Cria layers padrão
        self._create_default_layers()

        # Inicializa UI panels
        self._init_ui_panels()

        # Cria botões de modo
        self.mode_buttons = []
        self._create_mode_buttons()

        # Fase atual
        self.current_chapter = chapter or 1
        self.current_phase = phase or 1
        self.phase_name = f"Fase {self.current_chapter}-{self.current_phase}"

        # Tkinter para file dialog
        self.root = Tk()
        self.root.withdraw()

        print(f"Editor iniciado - {self.phase_name}")

    def _create_default_layers(self):
        """Cria layers padrão"""
        self.layer_manager.add_layer("Chão", LayerType.GROUND)
        self.layer_manager.add_layer("Decoração", LayerType.DECORATION)
        self.layer_manager.add_layer("Teto", LayerType.CEILING)

    def _init_ui_panels(self):
        """Inicializa painéis da UI"""
        viewport_x = self.screen_manager.viewport_x
        viewport_y = self.screen_manager.viewport_y
        viewport_width = self.screen_manager.viewport_width

        # Palette de tiles (lado direito)
        palette_x = viewport_x + viewport_width - 250
        palette_y = viewport_y + 200
        palette_width = 230
        palette_height = 300

        self.tile_palette = TilePalette(palette_x, palette_y, palette_width, palette_height)

        # Seletor de layers (lado esquerdo)
        selector_x = viewport_x + 10
        selector_y = viewport_y + 200
        selector_width = 180
        selector_height = 300

        self.layer_selector = LayerSelector(selector_x, selector_y, selector_width, selector_height)

    def _create_mode_buttons(self):
        """Cria botões de modo"""
        modes = [
            ("LAYERS", "layers"),
            ("PATH", "path"),
            ("TOWERS", "towers"),
            ("PREVIEW", "preview"),
        ]

        viewport_x = self.screen_manager.viewport_x
        viewport_y = self.screen_manager.viewport_y

        self.mode_buttons = []
        for i, (text, mode) in enumerate(modes):
            rect = pygame.Rect(
                viewport_x + 10,
                viewport_y + 70 + i * 40,
                90,
                30
            )
            self.mode_buttons.append((rect, text, mode))

    def _update_preview_objects(self):
        """Atualiza objetos de visualização"""
        path_points = self.path.get_path_points()
        if path_points and len(path_points) > 1:
            if self.path.is_loop and path_points[0] == path_points[-1]:
                path_points = path_points[:-1]

            self.test_enemies = []
            for i in range(3):
                enemy = TestEnemy(path_points)
                enemy.progress = i * 0.3
                enemy.current_node = int(enemy.progress)
                enemy.progress = enemy.progress - enemy.current_node
                self.test_enemies.append(enemy)

        self.test_towers = []
        for spot in self.tower_spots.spots:
            tower_x = spot.x + spot.size // 2
            tower_y = spot.y + spot.size // 2
            self.test_towers.append(TestTower(tower_x, tower_y))

    def _import_tileset(self):
        """Importa um tileset para a layer atual"""
        file_path = filedialog.askopenfilename(
            title="Selecione uma imagem de tileset",
            filetypes=[("Image files", "*.png *.jpg *.jpeg *.bmp *.gif")]
        )

        if file_path:
            current_layer = self.layer_manager.get_current_layer()
            if current_layer:
                success = current_layer.load_tileset(file_path, self.grid_size, self.grid_size)
                if success:
                    self.tile_palette.set_tileset(current_layer.tileset)
                    print(f"Tileset importado para layer: {current_layer.name}")
                else:
                    print("Erro ao importar tileset")

    def handle_event(self, event):
        """Processa eventos do editor"""
        # Primeiro, deixa os painéis da UI processarem o evento
        ui_handled = False

        if self.mode == "layers":
            if self.tile_palette and self.tile_palette.handle_event(event):
                ui_handled = True
                if self.tile_palette.selected_tile is not None:
                    self.current_tile = self.tile_palette.selected_tile + 1

            if self.layer_selector and self.layer_selector.handle_event(event):
                ui_handled = True
                self.layer_manager.current_layer = self.layer_selector.selected_layer
                current_layer = self.layer_manager.get_current_layer()
                if current_layer and current_layer.tileset:
                    self.tile_palette.set_tileset(current_layer.tileset)

        # Se a UI não processou, processa outros eventos
        if not ui_handled:
            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_p:
                    self.toggle_pause()
                elif event.key == pygame.K_ESCAPE:
                    self.game.current_scene = self.game.menu_scene
                elif event.key == pygame.K_g:
                    self.show_grid = not self.show_grid
                elif event.key == pygame.K_s:
                    if pygame.key.get_mods() & pygame.KMOD_CTRL:
                        self.save_phase()
                elif event.key == pygame.K_i:
                    if pygame.key.get_mods() & pygame.KMOD_CTRL:
                        self._import_tileset()
                elif event.key == pygame.K_1:
                    self.mode = "layers"
                    self._update_preview_objects()
                elif event.key == pygame.K_2:
                    self.mode = "path"
                    self._update_preview_objects()
                elif event.key == pygame.K_3:
                    self.mode = "towers"
                    self._update_preview_objects()
                elif event.key == pygame.K_4:
                    self.mode = "preview"
                    self._update_preview_objects()
                elif event.key == pygame.K_EQUALS or event.key == pygame.K_PLUS:
                    if not pygame.key.get_mods() & pygame.KMOD_CTRL:
                        self.preview_speed = min(3.0, self.preview_speed + 0.2)
                elif event.key == pygame.K_MINUS:
                    if not pygame.key.get_mods() & pygame.KMOD_CTRL:
                        self.preview_speed = max(0.2, self.preview_speed - 0.2)
                elif event.key == pygame.K_DELETE:
                    self._delete_selected()
                elif event.key == pygame.K_o:
                    if pygame.key.get_mods() & pygame.KMOD_CTRL:
                        # Abre diálogo para selecionar fase
                        self._open_phase_loader()
                elif event.key == pygame.K_l:
                    if pygame.key.get_mods() & pygame.KMOD_CTRL:
                        # Lista fases disponíveis no console
                        self.list_available_phases()

            elif event.type == pygame.MOUSEBUTTONDOWN:
                mouse_pos = pygame.mouse.get_pos()

                # Verifica botões de modo
                for rect, text, mode in self.mode_buttons:
                    if rect.collidepoint(mouse_pos):
                        self.mode = mode
                        self._update_preview_objects()
                        return

                # Se não clicou em botão e está no viewport, processa ações de edição
                if self.mode != "preview" and self.screen_manager.is_mouse_in_viewport(mouse_pos):
                    world_pos = self.screen_manager.get_mouse_world_position(mouse_pos, self.camera)
                    if world_pos:
                        if event.button == 1:
                            self._handle_left_click(world_pos)
                        elif event.button == 3:
                            self._handle_right_click(world_pos)

            elif event.type == pygame.MOUSEWHEEL:
                if not self.paused:
                    if not (self.tile_palette and self.tile_palette.focused):
                        self.camera.handle_zoom(event.y > 0)

    def _handle_left_click(self, world_pos):
        """Processa clique esquerdo"""
        x, y = world_pos

        if self.mode == "layers":
            # Converte posição do mundo para coordenadas de grid
            grid_x = int(x // self.grid_size)
            grid_y = int(y // self.grid_size)

            # Verifica se está dentro dos limites
            current_layer = self.layer_manager.get_current_layer()
            if current_layer:
                if 0 <= grid_x < current_layer.width and 0 <= grid_y < current_layer.height:
                    # Coloca o tile
                    success = self.layer_manager.set_tile(grid_x, grid_y, self.current_tile)
                    if success:
                        print(f"Tile {self.current_tile} colocado em ({grid_x}, {grid_y})")  # Debug
                    else:
                        print(f"Falha ao colocar tile em ({grid_x}, {grid_y})")
                else:
                    print(f"Posição ({grid_x}, {grid_y}) fora dos limites da layer")

        elif self.mode == "path":
            if self.snap_to_grid:
                x = (x // self.grid_size) * self.grid_size + self.grid_size // 2
                y = (y // self.grid_size) * self.grid_size + self.grid_size // 2

            node_idx = self.path.get_node_at(x, y)
            if node_idx >= 0:
                self.path.selected_node = node_idx
            else:
                node_type = "waypoint"
                if len(self.path.nodes) == 0:
                    node_type = "start"
                if pygame.key.get_mods() & pygame.KMOD_SHIFT:
                    node_type = "end"

                new_idx = self.path.add_node(x, y, node_type)
                self.path.selected_node = new_idx

                if self.path.selected_node >= 0 and self.path.selected_node != new_idx:
                    self.path.connect_nodes(self.path.selected_node, new_idx)

        elif self.mode == "towers":
            self.tower_spots.add_spot(x, y)

    def _handle_right_click(self, world_pos):
        """Processa clique direito"""
        x, y = world_pos

        if self.mode == "layers":
            # Converte posição do mundo para coordenadas de grid
            grid_x = int(x // self.grid_size)
            grid_y = int(y // self.grid_size)

            # Verifica se está dentro dos limites
            current_layer = self.layer_manager.get_current_layer()
            if current_layer:
                if 0 <= grid_x < current_layer.width and 0 <= grid_y < current_layer.height:
                    # Remove o tile (coloca 0)
                    success = self.layer_manager.set_tile(grid_x, grid_y, 0)
                    if success:
                        print(f"Tile removido em ({grid_x}, {grid_y})")  # Debug
                else:
                    print(f"Posição ({grid_x}, {grid_y}) fora dos limites da layer")

        elif self.mode == "path":
            node_idx = self.path.get_node_at(x, y)
            if node_idx >= 0:
                self.path.remove_node(node_idx)

        elif self.mode == "towers":
            spot_idx = self.tower_spots.get_spot_at(x, y)
            if spot_idx >= 0:
                self.tower_spots.remove_spot(spot_idx)

    def _delete_selected(self):
        """Deleta item selecionado"""
        if self.mode == "path" and self.path.selected_node >= 0:
            self.path.remove_node(self.path.selected_node)
            self.path.selected_node = -1

    def fixed_update(self, dt):
        """Update da lógica"""
        if self.paused:
            return

        mouse_pos = pygame.mouse.get_pos()
        if self.screen_manager.is_mouse_in_viewport(mouse_pos):
            mouse_render_pos = self.screen_manager.get_mouse_world_position(mouse_pos)
            if mouse_render_pos:
                self.camera.update(dt, mouse_render_pos)

        if self.mode == "preview":
            for enemy in self.test_enemies:
                enemy.update(dt * self.preview_speed)
            for tower in self.test_towers:
                tower.update(dt)

    def render(self, screen):
        """Renderiza o editor"""
        screen.fill((30, 30, 40))

        # Renderiza mapa
        self.layer_manager.render_all(screen, self.camera, self.screen_manager)

        # Elementos de edição
        if self.mode != "preview":
            self.tower_spots.render(screen, self.camera, self.screen_manager)
        self.path.render(screen, self.camera, self.screen_manager)

        # Preview
        if self.mode == "preview":
            for tower in self.test_towers:
                tower.render(screen, self.camera, self.screen_manager)
            for enemy in self.test_enemies:
                enemy.render(screen, self.camera, self.screen_manager)

        # Grid
        if self.show_grid:
            self._render_grid(screen)

        self._render_map_bounds(screen)

        # Borda do viewport
        pygame.draw.rect(screen, (100, 100, 100),
                        (self.screen_manager.viewport_x,
                         self.screen_manager.viewport_y,
                         self.screen_manager.viewport_width,
                         self.screen_manager.viewport_height), 2)

        # UI Panels
        if self.mode == "layers":
            self.layer_selector.layers = self.layer_manager.layers
            self.layer_selector.render(screen, self.layer_manager.current_layer)

            current_layer = self.layer_manager.get_current_layer()
            if current_layer and current_layer.tileset:
                self.tile_palette.visible = True
                self.tile_palette.render(screen)
            else:
                self.tile_palette.visible = False
                font = pygame.font.Font(None, 20)
                msg = font.render("CTRL+I para importar tileset", True, (200, 200, 200))
                msg_x = self.screen_manager.viewport_x + self.screen_manager.viewport_width - 250
                msg_y = self.screen_manager.viewport_y + 180
                screen.blit(msg, (msg_x, msg_y))

        # UI Superior
        self._render_ui(screen)

        # Pause
        if self.paused:
            self._render_pause_overlay(screen)

    def _render_grid(self, screen):
        """Renderiza grid"""
        visible_rect = self.camera.get_visible_rect()

        # Calcula offset da câmera
        cam_offset_x = -self.camera.x * self.camera.zoom + self.screen_manager.render_width / 2
        cam_offset_y = -self.camera.y * self.camera.zoom + self.screen_manager.render_height / 2

        start_x = int(visible_rect.left // self.grid_size) * self.grid_size
        start_y = int(visible_rect.top // self.grid_size) * self.grid_size
        end_x = int(visible_rect.right // self.grid_size) * self.grid_size + self.grid_size
        end_y = int(visible_rect.bottom // self.grid_size) * self.grid_size + self.grid_size

        # Cria superfície para a grid
        grid_surface = pygame.Surface((self.screen_manager.viewport_width,
                                       self.screen_manager.viewport_height), pygame.SRCALPHA)

        # Linhas verticais
        x = start_x
        while x <= end_x:
            render_x = x * self.camera.zoom + cam_offset_x
            render_y1 = visible_rect.top * self.camera.zoom + cam_offset_y
            render_y2 = visible_rect.bottom * self.camera.zoom + cam_offset_y

            # Converte para tela
            screen_x, _ = self.screen_manager.get_screen_position(render_x, 0)
            screen_y1, _ = self.screen_manager.get_screen_position(0, render_y1)
            screen_y2, _ = self.screen_manager.get_screen_position(0, render_y2)

            # Ajusta para coordenadas locais do viewport
            grid_x = screen_x - self.screen_manager.viewport_x
            grid_y1 = screen_y1 - self.screen_manager.viewport_y
            grid_y2 = screen_y2 - self.screen_manager.viewport_y

            pygame.draw.line(grid_surface, (80, 80, 80, 100),
                             (grid_x, grid_y1), (grid_x, grid_y2), max(1, int(1 * self.screen_manager.render_scale)))
            x += self.grid_size

        # Linhas horizontais
        y = start_y
        while y <= end_y:
            render_x1 = visible_rect.left * self.camera.zoom + cam_offset_x
            render_x2 = visible_rect.right * self.camera.zoom + cam_offset_x
            render_y = y * self.camera.zoom + cam_offset_y

            # Converte para tela
            screen_x1, _ = self.screen_manager.get_screen_position(render_x1, 0)
            screen_x2, _ = self.screen_manager.get_screen_position(render_x2, 0)
            screen_y, _ = self.screen_manager.get_screen_position(0, render_y)

            # Ajusta para coordenadas locais do viewport
            grid_x1 = screen_x1 - self.screen_manager.viewport_x
            grid_x2 = screen_x2 - self.screen_manager.viewport_x
            grid_y = screen_y - self.screen_manager.viewport_y

            pygame.draw.line(grid_surface, (80, 80, 80, 100),
                             (grid_x1, grid_y), (grid_x2, grid_y), max(1, int(1 * self.screen_manager.render_scale)))
            y += self.grid_size

        screen.blit(grid_surface, (self.screen_manager.viewport_x, self.screen_manager.viewport_y))

    def _world_to_render(self, world_x, world_y):
        """Converte mundo para render"""
        render_x = (world_x - self.camera.x) * self.camera.zoom + self.screen_manager.render_width / 2
        render_y = (world_y - self.camera.y) * self.camera.zoom + self.screen_manager.render_height / 2
        return (render_x, render_y)

    def _world_to_screen(self, world_x, world_y):
        """Método unificado para converter coordenadas do mundo para tela"""
        # Calcula posição relativa à câmera no espaço de renderização
        render_x = (world_x - self.camera.x) * self.camera.zoom + self.screen_manager.render_width / 2
        render_y = (world_y - self.camera.y) * self.camera.zoom + self.screen_manager.render_height / 2

        # Converte para coordenadas de tela
        screen_x, screen_y = self.screen_manager.get_screen_position(render_x, render_y)
        return (screen_x, screen_y)

    def _render_ui(self, screen):
        """Renderiza UI superior"""
        viewport_x = self.screen_manager.viewport_x
        viewport_y = self.screen_manager.viewport_y

        # Painel superior
        pygame.draw.rect(screen, (40, 40, 50),
                        (viewport_x, viewport_y, self.screen_manager.viewport_width, 60))

        # Título
        title = self.font.render(f"EDITOR DE FASES - {self.phase_name}", True, (255, 215, 0))
        screen.blit(title, (viewport_x + 10, viewport_y + 10))

        # Instruções
        inst = self.font_small.render(
            "CTRL+S: Salvar | CTRL+O: Carregar | CTRL+I: Importar Tileset | G: Grid | 1-5: Modos | DEL: Remover",
            True, (200, 200, 200))
        screen.blit(inst, (viewport_x + 10, viewport_y + 35))

        # Botões de modo
        for rect, text, mode in self.mode_buttons:
            if mode == self.mode:
                color = (100, 150, 200)
                border = (255, 255, 255)
            else:
                color = (60, 60, 80)
                border = (100, 100, 100)

            pygame.draw.rect(screen, color, rect)
            pygame.draw.rect(screen, border, rect, 2)
            text_surf = self.font_small.render(text, True, (255, 255, 255))
            text_rect = text_surf.get_rect(center=rect.center)
            screen.blit(text_surf, text_rect)

        # Informações do modo
        mode_info = {
            "layers": "Clique nos tiles à direita | Selecione layers à esquerda",
            "path": "Esquerdo: add nó | Shift+Click: fim | Direito: remove",
            "towers": "Esquerdo: add spot | Direito: remove",
            "preview": f"Velocidade: {self.preview_speed:.1f}x | +/ - para ajustar"
        }

        info = self.font_small.render(mode_info[self.mode], True, (180, 180, 180))
        screen.blit(info, (viewport_x + 10, viewport_y + self.screen_manager.viewport_height - 20))

    def _render_pause_overlay(self, screen):
        """Overlay de pausa"""
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

    def save_phase(self):
        """Salva a fase atual"""
        phase_data = {
            "name": self.phase_name,
            "map": self.layer_manager.to_dict(),
            "path": self.path.to_dict(),
            "tower_spots": self.tower_spots.to_dict(),
            "waves": [],
            "rewards": {
                "money": 100,
                "experience": 50
            }
        }

        self.exporter.export_phase(phase_data, self.current_chapter, self.current_phase)

    def load_phase(self, chapter, phase_number):
        """Carrega uma fase existente"""
        phase_data = self.exporter.load_phase(chapter, phase_number)

        if not phase_data:
            print(f"Fase {chapter}-{phase_number} não encontrada!")
            return False

        try:
            # Carrega o mapa
            if "map" in phase_data:
                self.layer_manager.from_dict(phase_data["map"])

            # Carrega o caminho
            if "path" in phase_data:
                self.path.from_dict(phase_data["path"])

            # Carrega os spots de torre
            if "tower_spots" in phase_data:
                self.tower_spots.from_dict(phase_data["tower_spots"])

            # Atualiza nome da fase
            self.phase_name = phase_data.get("name", f"Fase {chapter}-{phase_number}")
            self.current_chapter = chapter
            self.current_phase = phase_number

            # Atualiza a tile palette com o tileset da layer atual
            current_layer = self.layer_manager.get_current_layer()
            if current_layer and current_layer.tileset:
                self.tile_palette.set_tileset(current_layer.tileset)

            # Atualiza objetos de preview
            self._update_preview_objects()

            print(f"Fase {chapter}-{phase_number} carregada com sucesso!")
            return True

        except Exception as e:
            print(f"Erro ao carregar fase: {e}")
            return False

    def list_available_phases(self):
        """Lista todas as fases disponíveis para carregar"""
        phases = self.exporter.list_phases()

        if not phases:
            print("Nenhuma fase encontrada!")
            return

        print("\nFases disponíveis:")
        for chapter, phase in phases:
            print(f"  {chapter}-{phase}")

    def _open_phase_loader(self):
        """Abre diálogo para selecionar fase para carregar"""
        # Por enquanto, vamos usar um input simples no console
        print("\n--- CARREGAR FASE ---")
        self.list_available_phases()

        try:
            chapter = int(input("Número do capítulo: "))
            phase = int(input("Número da fase: "))
            self.load_phase(chapter, phase)
        except ValueError:
            print("Entrada inválida!")
        except KeyboardInterrupt:
            print("\nCarregamento cancelado.")

    def _render_map_bounds(self, screen):
        """Renderiza os limites do mapa"""
        # Obtém as dimensões da layer atual ou do mapa
        current_layer = self.layer_manager.get_current_layer()
        if not current_layer:
            return

        # Limites do mapa em coordenadas de mundo
        map_left = 0
        map_right = current_layer.width * self.grid_size
        map_top = 0
        map_bottom = current_layer.height * self.grid_size

        # Converte os cantos do mapa para coordenadas de tela
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

        # Desenha a borda do mapa
        # Borda externa brilhante
        pygame.draw.polygon(screen, (255, 215, 0), screen_corners, 3)

        # Cantos com marcadores
        for screen_x, screen_y in screen_corners:
            # Círculo nos cantos
            pygame.draw.circle(screen, (255, 215, 0), (int(screen_x), int(screen_y)), 8)
            pygame.draw.circle(screen, (255, 255, 255), (int(screen_x), int(screen_y)), 4)

        # Adiciona linhas de grade interna
        if self.camera.zoom > 0.5:  # Só mostra quando estiver com zoom suficiente
            # Linhas verticais da borda
            for x in [map_left, map_right]:
                screen_x, _ = self._world_to_screen(x, 0)
                screen_y1, _ = self._world_to_screen(0, map_top)
                screen_y2, _ = self._world_to_screen(0, map_bottom)
                pygame.draw.line(screen, (255, 215, 0, 100),
                                 (screen_x, screen_y1), (screen_x, screen_y2), 1)

            # Linhas horizontais da borda
            for y in [map_top, map_bottom]:
                screen_x1, _ = self._world_to_screen(map_left, 0)
                screen_x2, _ = self._world_to_screen(map_right, 0)
                screen_y, _ = self._world_to_screen(0, y)
                pygame.draw.line(screen, (255, 215, 0, 100),
                                 (screen_x1, screen_y), (screen_x2, screen_y), 1)

        # Adiciona texto informativo nos cantos
        font = pygame.font.Font(None, 16)

        # Canto superior esquerdo
        text = font.render(f"(0, 0)", True, (255, 255, 255))
        screen.blit(text, (screen_corners[0][0] + 10, screen_corners[0][1] + 10))

        # Canto superior direito
        text = font.render(f"({current_layer.width}, 0)", True, (255, 255, 255))
        screen.blit(text, (screen_corners[1][0] - 70, screen_corners[1][1] + 10))

        # Canto inferior direito
        text = font.render(f"({current_layer.width}, {current_layer.height})", True, (255, 255, 255))
        screen.blit(text, (screen_corners[2][0] - 90, screen_corners[2][1] - 20))

        # Canto inferior esquerdo
        text = font.render(f"(0, {current_layer.height})", True, (255, 255, 255))
        screen.blit(text, (screen_corners[3][0] + 10, screen_corners[3][1] - 20))
