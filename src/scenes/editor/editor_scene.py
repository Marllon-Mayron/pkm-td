"""
Cena do Editor de Fases - Versão Modular
"""
import pygame
from tkinter import filedialog, Tk

from src.editor.wave_config import WaveManager
from src.scenes.base_scene import BaseScene
from src.editor.layer_manager import LayerManager, LayerType
from src.editor.path_editor import Path
from src.editor.tower_spot_editor import TowerSpotManager
from src.editor.phase_exporter import PhaseExporter
from src.scenes.editor import WaveConfigDialog
from src.scenes.editor.components.layer_selector import LayerSelector
from src.scenes.editor.components.managers.path_manager import PathManager
from src.scenes.editor.components.managers.undo_manager import UndoManager
from src.scenes.editor.components.map_config_dialog import MapConfigDialog
from src.scenes.editor.components.mode_buttons import ModeButtons
from src.scenes.editor.components.tile_palette import TilePalette
from src.scenes.editor.handlers.input_handler import EditorInputHandler
from src.scenes.editor.handlers.map_handler import MapHandler
from src.scenes.editor.handlers.render_handler import EditorRenderHandler
from src.scenes.editor.preview.test_enemy import TestEnemy
from src.scenes.editor.preview.test_tower import TestTower


class EditorScene(BaseScene):
    def __init__(self, game, chapter=None, phase=None):
        super().__init__(game)

        # Dimensões do mundo
        self.world_width = 3000
        self.world_height = 3000

        # Limites expandidos (permitem área negativa)
        self.min_world_x = -1000
        self.min_world_y = -1000
        self.max_world_x = self.world_width + 1000
        self.max_world_y = self.world_height + 1000

        # Inicializa câmera
        self.game.initialize_camera(self.world_width, self.world_height)
        self.camera = self.game.camera
        self.camera.set_limits(self.min_world_x, self.max_world_x,
                               self.min_world_y, self.max_world_y)
        self.camera.x = 0
        self.camera.y = 0

        # Gerenciadores
        self.layer_manager = LayerManager()
        self.path_manager = PathManager()
        self.tower_spots = TowerSpotManager()
        self.exporter = PhaseExporter()
        self.undo_manager = UndoManager(max_steps=10)

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

        self.wave_manager = WaveManager()
        self.path_manager.set_wave_manager(self.wave_manager)  # Associa ao path_manager
        self.wave_config_dialog = None

        # UI Panels
        self.tile_palette = None
        self.layer_selector = None
        self.mode_buttons = None

        # Fontes
        self.font = pygame.font.Font(None, 24)
        self.font_small = pygame.font.Font(None, 18)

        # Diálogos
        self.map_config_dialog = None

        # Fase atual
        self.current_chapter = chapter or 1
        self.current_phase = phase or 1
        self.phase_name = f"Fase {self.current_chapter}-{self.current_phase}"

        # Tkinter para file dialog
        self.root = Tk()
        self.root.withdraw()

        # Cria layers padrão
        self._create_default_layers()

        # Inicializa UI
        self._init_ui()

        # Handlers (devem ser inicializados após a UI)
        self.input_handler = EditorInputHandler(self)
        self.map_handler = MapHandler(self)
        self.render_handler = EditorRenderHandler(self)
        self.path_manager.add_path()

        print(f"Editor iniciado - {self.phase_name}")

    def _create_default_layers(self):
        """Cria layers padrão"""
        self.layer_manager.add_layer("Chão", LayerType.GROUND)
        self.layer_manager.add_layer("Decoração", LayerType.DECORATION)
        self.layer_manager.add_layer("Teto", LayerType.CEILING)

    def _init_ui(self):
        """Inicializa elementos da UI"""
        viewport_x = self.screen_manager.viewport_x
        viewport_y = self.screen_manager.viewport_y
        viewport_width = self.screen_manager.viewport_width

        # Palette de tiles
        palette_x = viewport_x + viewport_width - 250
        palette_y = viewport_y + 200
        self.tile_palette = TilePalette(palette_x, palette_y, 230, 300)

        # Seletor de layers
        selector_x = viewport_x + 10
        selector_y = viewport_y + 200
        self.layer_selector = LayerSelector(selector_x, selector_y, 180, 300)

        # Botões de modo
        self.mode_buttons = ModeButtons(viewport_x, viewport_y)

    def set_mode(self, mode):
        """Altera o modo do editor"""
        self.mode = mode
        if mode == "path":
            # Se entrou no modo path, cria uma wave padrão se não existir
            if not self.wave_manager.waves:
                self.wave_manager.add_wave()
        self._update_preview_objects()

    def _update_preview_objects(self):
        """Atualiza objetos de visualização"""
        print("\n=== Atualizando objetos de preview ===")

        # MODIFIQUE ESTA PARTE - usa todos os paths para criar inimigos
        all_paths = self.path_manager.get_all_paths()

        # Limpa inimigos existentes
        self.test_enemies = []

        # Cria inimigos para cada path
        for path_index, path in enumerate(all_paths):
            path_points = path.get_path_points()

            if path_points and len(path_points) > 1:
                print(f"Path {path_index+1} tem {len(path_points)} pontos, criando inimigos!")

                # Cria 2 inimigos para cada path (para teste)
                for i in range(2):
                    enemy = TestEnemy(path_points)
                    enemy.path_index = path_index  # Marca qual path este inimigo segue

                    # Posiciona um no início e outro no meio
                    if i == 1 and len(path_points) > 2:
                        enemy.current_point = 1
                        enemy.progress = 0.0
                        enemy.position = path_points[1]

                    self.test_enemies.append(enemy)

        print(f"Inimigos criados: {len(self.test_enemies)}")

        # Atualiza torres
        self.test_towers = []
        for spot in self.tower_spots.spots:
            tower_x = spot.x + spot.size // 2
            tower_y = spot.y + spot.size // 2
            self.test_towers.append(TestTower(tower_x, tower_y))

        print(f"Torres criadas: {len(self.test_towers)}")
        print("=== Fim da atualização ===\n")

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

    def _delete_selected(self):
        """Deleta item selecionado"""
        if self.mode == "path" and self.path.selected_node >= 0:
            self.path.remove_node(self.path.selected_node)
            self.path.selected_node = -1

    def _handle_left_click(self, world_pos):
        """Delega clique esquerdo para o map handler"""
        self.map_handler.handle_left_click(world_pos)

    def _handle_right_click(self, world_pos):
        """Delega clique direito para o map handler"""
        self.map_handler.handle_right_click(world_pos)

    def _open_map_config_dialog(self):
        """Abre diálogo para configurar tamanho do mapa e identificação da fase"""
        current_layer = self.layer_manager.get_current_layer()
        if current_layer:
            dialog_x = self.screen_manager.viewport_x + (self.screen_manager.viewport_width - 400) // 2
            dialog_y = self.screen_manager.viewport_y + (
                    self.screen_manager.viewport_height - 350) // 2
            self.map_config_dialog = MapConfigDialog(
                dialog_x, dialog_y, 400, 350,
                current_layer.width,
                current_layer.height,
                self.current_chapter,
                self.current_phase,
                self.phase_name
            )

    def _open_wave_config_dialog(self):
        """Abre o diálogo de configuração de waves"""
        if not self.wave_manager.waves:
            self.wave_manager.add_wave()

        dialog_x = self.screen_manager.viewport_x + (self.screen_manager.viewport_width - 600) // 2
        dialog_y = self.screen_manager.viewport_y + (self.screen_manager.viewport_height - 500) // 2

        # Passa a Pokedex como parâmetro
        from src.data.pokedex import Pokedex
        pokedex = Pokedex()

        self.wave_config_dialog = WaveConfigDialog(
            dialog_x, dialog_y, 600, 500,
            self.wave_manager,
            self.path_manager,
            pokedex  # Passa a Pokedex
        )

    def _handle_map_config_result(self, result):
        """Processa o resultado do diálogo de configuração"""
        if result:
            # Redimensiona todas as layers se necessário
            if result['width'] != self.layer_manager.width or result['height'] != self.layer_manager.height:
                self.layer_manager.resize_all_layers(result['width'], result['height'])
                print(f"Mapa redimensionado para {result['width']}x{result['height']}")

            # Atualiza capítulo, fase e nome
            chapter_changed = result['chapter'] != self.current_chapter
            phase_changed = result['phase'] != self.current_phase
            name_changed = result['name'] != self.phase_name

            self.current_chapter = result['chapter']
            self.current_phase = result['phase']
            self.phase_name = result['name']

            if chapter_changed or phase_changed or name_changed:
                print(
                    f"Fase alterada para: {self.phase_name} (Capítulo {self.current_chapter}, Fase {self.current_phase})")
                self.clear_undo_history()

    def handle_event(self, event):
        """Delega processamento de eventos para o input handler"""
        # Verifica se há um diálogo de configuração de mapa ativo
        if self.map_config_dialog and self.map_config_dialog.visible:
            result = self.map_config_dialog.handle_event(event)
            if result is not None:
                self._handle_map_config_result(result)
                self.map_config_dialog = None
            elif not self.map_config_dialog.visible:
                self.map_config_dialog = None
            return  # SEMPRE retorna se tinha diálogo

        # Verifica se há um diálogo de configuração de waves ativo
        if self.wave_config_dialog and self.wave_config_dialog.visible:
            result = self.wave_config_dialog.handle_event(event)
            if result == "saved":
                self._update_preview_objects()
                self.wave_config_dialog = None
            elif not self.wave_config_dialog.visible:
                self.wave_config_dialog = None

            # IMPORTANTE: Sempre retorna True se o diálogo estava visível
            # Isso impede que o evento propague para o editor
            return True

        # Se não houver diálogo ativo, processa normalmente
        self.input_handler.handle_event(event)

    def new_map(self):
        """Cria um novo mapa com configurações personalizadas"""
        self._open_map_config_dialog()

    def fixed_update(self, dt):
        """Update da lógica"""
        if self.paused:
            return

        if self.mode == "preview":
            # Verifica se os paths mudaram e atualiza se necessário
            current_paths = [path.get_path_points() for path in self.path_manager.get_all_paths()]
            if not hasattr(self, '_last_paths') or self._last_paths != current_paths:
                self._last_paths = [p.copy() if p else [] for p in current_paths]
                self._update_preview_objects()
                print("Paths mudaram, atualizando preview!")

            if self.test_enemies:
                # Agrupa inimigos por path para reset independente
                enemies_by_path = {}
                for enemy in self.test_enemies:
                    path_index = getattr(enemy, 'path_index', 0)
                    if path_index not in enemies_by_path:
                        enemies_by_path[path_index] = []
                    enemies_by_path[path_index].append(enemy)

                # Atualiza todos os inimigos
                for enemy in self.test_enemies:
                    enemy.update(dt * self.preview_speed)

                # Reseta inimigos de cada path independentemente
                for path_index, enemies in enemies_by_path.items():
                    all_finished = all(enemy.finished for enemy in enemies)
                    if all_finished and enemies:
                        print(f"Todos os inimigos do Path {path_index + 1} terminaram! Resetando...")
                        for enemy in enemies:
                            enemy.reset()

            # Atualiza torres
            for tower in self.test_towers:
                tower.update(dt)

    def render(self, screen):
        """Delega renderização para o render handler"""
        self.render_handler.render(screen)

    def save_phase(self):
        """Salva a fase atual"""
        phase_data = {
            "name": self.phase_name,
            "map": self.layer_manager.to_dict(),
            "paths": self.path_manager.to_dict(),
            "waves": self.wave_manager.to_dict(),  # Adiciona waves
            "tower_spots": self.tower_spots.to_dict(),
            "rewards": {
                "money": 100,
                "experience": 50
            }
        }

        self.exporter.export_phase(phase_data, self.current_chapter, self.current_phase)
        print(f"Fase salva com {len(self.wave_manager.waves)} waves!")

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

            # MODIFICADO: Carrega os paths (compatibilidade com versões antigas)
            if "paths" in phase_data:
                self.path_manager.from_dict(phase_data["paths"])
            elif "path" in phase_data:  # Compatibilidade com versão antiga
                # Converte path único para path manager
                self.path_manager = PathManager()
                path = Path()
                path.from_dict(phase_data["path"])
                self.path_manager.paths = [path]
                self.path_manager.current_path_index = 0
                # Carrega waves
            if "waves" in phase_data:
                self.wave_manager.from_dict(phase_data["waves"])
            else:
                # Cria uma wave padrão se não existir
                self.wave_manager = WaveManager()
                self.wave_manager.add_wave()

            # Carrega os spots de torre
            if "tower_spots" in phase_data:
                self.tower_spots.from_dict(phase_data["tower_spots"])

            # Atualiza nome da fase
            self.phase_name = phase_data.get("name", f"Fase {chapter}-{phase_number}")
            self.current_chapter = chapter
            self.current_phase = phase_number

            # Atualiza a tile palette
            current_layer = self.layer_manager.get_current_layer()
            if current_layer and current_layer.tileset:
                self.tile_palette.set_tileset(current_layer.tileset)

            # Atualiza objetos de preview
            self._update_preview_objects()

            # Limpa historico salvo
            self.clear_undo_history()

            print(f"Fase {chapter}-{phase_number} carregada com sucesso!")
            print(f"Paths carregados: {len(self.path_manager.paths)}")
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

    def clear_undo_history(self):
        """Limpa o histórico de undo/redo"""
        self.undo_manager.clear()
        print("Histórico de undo/redo limpo")

