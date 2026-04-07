# src/scenes/editor/editor_scene.py

"""
Cena do Editor de Fases

"""
import pygame, os
from tkinter import filedialog, Tk

from src.editor.target_item_editor import TargetItemManager
from src.editor.event_system import EventManager
from src.editor.wave_config import WaveManager
from src.editor.layer_manager import LayerManager, LayerType
from src.editor.path_editor import Path
from src.editor.tower_spot_editor import TowerSpotManager
from src.editor.phase_exporter import PhaseExporter
from src.scenes.base_scene import BaseScene
from src.scenes.editor import WaveConfigDialog
from src.scenes.editor.components.event_config_dialog import EventConfigDialog
from src.scenes.editor.components.tileset_manager_dialog import TilesetManagerDialog
from src.scenes.editor.components.brush_buttons import BrushButtons
from src.scenes.editor.components.layer_selector import LayerSelector
from src.scenes.editor.components.managers.path_manager import PathManager
from src.scenes.editor.components.managers.undo_manager import UndoManager
from src.scenes.editor.components.map_config_dialog import MapConfigDialog
from src.scenes.editor.components.mode_buttons import ModeButtons
from src.scenes.editor.components.target_item_dialog import TargetItemDialog
from src.scenes.editor.components.tile_palette import TilePalette
from src.scenes.editor.components.load_phase_dialog import LoadPhaseDialog
from src.scenes.editor.components.rewards_config_dialog import RewardsConfigDialog  # NOVO
from src.scenes.editor.handlers.input_handler import EditorInputHandler
from src.scenes.editor.handlers.map_handler import MapHandler
from src.scenes.editor.handlers.render_handler import EditorRenderHandler


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
        self.target_items = TargetItemManager()
        self.event_manager = EventManager()

        # Estado do editor - NOVO TAMANHO 24
        self.mode = "layers"  # layers, path, towers
        self.current_tile = 1
        self.show_grid = True
        self.grid_size = 24  # ALTERADO: 24x24 pixels por tile
        self.snap_to_grid = True

        # Waves
        self.wave_manager = WaveManager()
        self.path_manager.set_wave_manager(self.wave_manager)

        # Recompensas da fase (NOVO)
        self.phase_rewards = {
            "money": 100,
            "experience": 50
        }

        # UI Panels
        self.tile_palette = None
        self.layer_selector = None
        self.mode_buttons = None

        # Fontes
        self.font = pygame.font.Font(None, 24)
        self.font_small = pygame.font.Font(None, 18)

        # Diálogos
        self.map_config_dialog = None
        self.load_phase_dialog = None
        self.wave_config_dialog = None
        self.target_item_dialog = None
        self.event_config_dialog = None
        self.tileset_manager_dialog = None
        self.rewards_config_dialog = None

        self.selected_item_id = None

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

        # Handlers
        self.input_handler = EditorInputHandler(self)
        self.map_handler = MapHandler(self)
        self.render_handler = EditorRenderHandler(self)
        self.path_manager.add_path()

        print(f"Editor iniciado - {self.phase_name} - Grid size: {self.grid_size}px")

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

        # Palette de tiles - ajustada para 6 colunas (mais larga)
        palette_x = viewport_x + viewport_width - 280  # Aumentado para 280
        palette_y = viewport_y + 200
        self.tile_palette = TilePalette(palette_x, palette_y, 260, 350)  # Largura 260, altura 350

        # Seletor de layers
        selector_x = viewport_x + 10
        selector_y = viewport_y + 200
        self.layer_selector = LayerSelector(selector_x, selector_y, 180, 300)

        # Botões de modo
        self.mode_buttons = ModeButtons(viewport_x, viewport_y)

        brush_x = viewport_x + 100
        brush_y = viewport_y + 300
        self.brush_buttons = BrushButtons(brush_x, brush_y)

    def set_mode(self, mode):
        """Altera o modo do editor"""
        print(f"DEBUG: set_mode({mode})")

        self.mode = mode

        if mode == "path":
            if not self.wave_manager.waves:
                self.wave_manager.add_wave()

        elif mode == "load_phase":
            self._open_load_phase_dialog()

        elif mode == "items":
            print("DEBUG: Abrindo diálogo de seleção de item")
            self._open_target_item_dialog()

        elif mode == "layers":
            if self.target_item_dialog:
                self.target_item_dialog.visible = False

        elif mode == "towers":
            if self.target_item_dialog:
                self.target_item_dialog.visible = False

        elif mode == "events":
            print("DEBUG: Abrindo diálogo de configuração de eventos")
            self._open_event_config_dialog()

        elif mode == "tilesets":
            print("DEBUG: Abrindo gerenciador de tilesets")
            self._open_tileset_manager_dialog()

        elif mode == "rewards":  # NOVO
            print("DEBUG: Abrindo configuração de recompensas")
            self._open_rewards_config_dialog()

    def _open_rewards_config_dialog(self):
        """Abre o diálogo de configuração de recompensas (gold e XP)"""
        dialog_x = self.screen_manager.viewport_x + (self.screen_manager.viewport_width - 400) // 2
        dialog_y = self.screen_manager.viewport_y + (self.screen_manager.viewport_height - 300) // 2

        self.rewards_config_dialog = RewardsConfigDialog(
            dialog_x, dialog_y, 400, 300,
            self.phase_rewards.get("money", 100),
            self.phase_rewards.get("experience", 50)
        )

    def _import_tileset(self):
        """Importa um tileset (suporta múltiplos tilesets na mesma imagem)"""
        file_path = filedialog.askopenfilename(
            title="Selecione uma imagem de tileset (pode conter múltiplos tilesets lado a lado)",
            filetypes=[("Image files", "*.png *.jpg *.jpeg *.bmp *.gif")]
        )

        if file_path:
            current_layer = self.layer_manager.get_current_layer()
            if current_layer:
                print(f"\n=== IMPORTANDO TILESET ===")
                print(f"Layer: {current_layer.name}")
                print(f"Arquivo: {file_path}")

                # Tenta detectar quantos tilesets tem na imagem
                try:
                    import pygame
                    test_img = pygame.image.load(file_path)
                    img_width = test_img.get_width()
                    expected_width_per_set = 6 * self.grid_size  # 144px
                    estimated_sets = img_width // expected_width_per_set
                    print(f"Imagem detectada: {img_width}x{test_img.get_height()}px")
                    print(f"Estimativa: {estimated_sets} tilesets de {6}x{8} tiles")
                except:
                    pass

                if not current_layer.tileset:
                    success = current_layer.load_tileset(file_path, self.grid_size, self.grid_size)
                else:
                    success = current_layer.add_tileset_6x8(file_path, self.grid_size, self.grid_size)

                if success:
                    # Atualiza a tile palette
                    all_tiles, boundaries = current_layer.get_all_tiles_with_boundaries()
                    self.tile_palette.set_tileset(all_tiles, boundaries)
                    self.tile_palette._update_max_scroll()

                    print(f"\n✓ IMPORTADO COM SUCESSO!")
                    print(f"  Total de tiles: {len(current_layer.tileset)}")
                    print(f"  Total de tilesets: {len(current_layer.tilesets)}")
                else:
                    print("Erro ao importar tileset")

    def _update_tile_palette_from_layer(self):
        """Atualiza a tile palette a partir da layer atual"""
        current_layer = self.layer_manager.get_current_layer()
        if current_layer and current_layer.tileset:
            all_tiles, boundaries = current_layer.get_all_tiles_with_boundaries()
            self.tile_palette.set_tileset(all_tiles, boundaries)

    def _delete_selected(self):
        """Deleta item selecionado"""
        if self.mode == "path" and hasattr(self.path_manager.get_current_path(), 'selected_node'):
            current_path = self.path_manager.get_current_path()
            if current_path.selected_node >= 0:
                current_path.remove_node(current_path.selected_node)
                current_path.selected_node = -1
        elif self.mode == "towers" and self.tower_spots.selected_spot >= 0:
            self.tower_spots.remove_spot_by_index(self.tower_spots.selected_spot)

    def _handle_left_click(self, world_pos, continuous=False):
        """Delega clique esquerdo para o map handler ou trata items"""

        if self.mode == "items" and not continuous:
            # Verifica se temos um item selecionado (do diálogo)
            if not hasattr(self, 'selected_item_id') or self.selected_item_id is None:
                print("Nenhum item selecionado! Use o modo Items para selecionar um item primeiro.")
                return True

            # Converte para coordenadas de tile
            tile_x = int(world_pos[0] // self.grid_size)
            tile_y = int(world_pos[1] // self.grid_size)

            # Ajusta para grid
            grid_x = tile_x * self.grid_size
            grid_y = tile_y * self.grid_size

            # Adiciona o item
            item_id = self.selected_item_id
            print(f"Adicionando item ID {item_id} em ({grid_x}, {grid_y})")

            self.undo_manager.save_state(self, f"Criar item {item_id} em ({grid_x}, {grid_y})")
            self.target_items.add_item(grid_x, grid_y, item_id)

            return True

        # Para outros modos, delega para o map handler
        self.map_handler.handle_left_click(world_pos, continuous)

    def _handle_right_click(self, world_pos):
        """Delega clique direito para o map handler ou trata items"""

        # Modo items - remove item
        if self.mode == "items":
            # Converte para coordenadas de tile
            tile_x = int(world_pos[0] // self.grid_size)
            tile_y = int(world_pos[1] // self.grid_size)

            # Ajusta para grid
            grid_x = tile_x * self.grid_size
            grid_y = tile_y * self.grid_size

            # MODIFICADO: Pega TODOS os itens na posição
            items_at_pos = self.target_items.get_items_at(grid_x + 8, grid_y + 8)

            if items_at_pos:
                # Se houver um item selecionado no diálogo, remove ele primeiro
                if self.target_item_dialog and self.target_item_dialog.selected_item_index >= 0:
                    selected_idx = self.target_item_dialog.selected_item_index
                    if selected_idx < len(self.target_items.items):
                        item = self.target_items.items[selected_idx]
                        if item in items_at_pos:
                            # Remove o item selecionado
                            self.undo_manager.save_state(self, f"Remover item selecionado em ({grid_x}, {grid_y})")
                            self.target_items.remove_item(item)
                            self.target_item_dialog.selected_item_index = -1
                            print(f"Item selecionado removido de ({grid_x}, {grid_y})")
                            return True

                # Se não removeu um específico, remove o primeiro da lista
                self.undo_manager.save_state(self, f"Remover item em ({grid_x}, {grid_y})")
                self.target_items.remove_item(items_at_pos[0])

                # Se o item removido era o selecionado, desseleciona
                if self.target_item_dialog:
                    selected = self.target_item_dialog.selected_item_index
                    if selected >= 0 and selected < len(self.target_items.items):
                        if self.target_items.items[selected] == items_at_pos[0]:
                            self.target_item_dialog.selected_item_index = -1

                print(f"Item removido de ({grid_x}, {grid_y})")
            else:
                print("Nenhum item nesta posição")

            return True

        # Para outros modos, delega para o map handler
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

    def _open_load_phase_dialog(self):
        """Abre diálogo para carregar uma fase existente"""
        dialog_x = self.screen_manager.viewport_x + (self.screen_manager.viewport_width - 400) // 2
        dialog_y = self.screen_manager.viewport_y + (self.screen_manager.viewport_height - 450) // 2
        self.load_phase_dialog = LoadPhaseDialog(
            dialog_x, dialog_y, 400, 450,
            self.exporter
        )

    def _open_target_item_dialog(self):
        """Abre diálogo para selecionar qual item adicionar"""
        dialog_x = self.screen_manager.viewport_x + (self.screen_manager.viewport_width - 400) // 2
        dialog_y = self.screen_manager.viewport_y + (self.screen_manager.viewport_height - 400) // 2
        self.target_item_dialog = TargetItemDialog(
            dialog_x, dialog_y, 400, 350,
            self.target_items
        )

    def _open_event_config_dialog(self):
        """Abre o diálogo de configuração de eventos."""
        if not self.event_manager.triggers:
            self.event_manager.add_trigger()  # Cria um gatilho padrão se não houver nenhum

        dialog_x = self.screen_manager.viewport_x + (self.screen_manager.viewport_width - 700) // 2
        dialog_y = self.screen_manager.viewport_y + (self.screen_manager.viewport_height - 500) // 2

        self.event_config_dialog = EventConfigDialog(
            dialog_x, dialog_y, 700, 500,
            self.event_manager,
            self.wave_manager  # Passa o wave_manager para saber o número de waves
        )

    def _handle_load_phase_result(self, result):
        """Processa o resultado do diálogo de carregamento"""
        if result and result.get('action') == 'load':
            chapter = result['chapter']
            phase = result['phase']
            success = self.load_phase(chapter, phase)
            if success:
                print(f"Fase {chapter}-{phase} carregada com sucesso!")
            else:
                print(f"Falha ao carregar fase {chapter}-{phase}")

    def _open_wave_config_dialog(self):
        """Abre o diálogo de configuração de waves"""
        if not self.wave_manager.waves:
            self.wave_manager.add_wave()

        dialog_x = self.screen_manager.viewport_x + (self.screen_manager.viewport_width - 600) // 2
        dialog_y = self.screen_manager.viewport_y + (self.screen_manager.viewport_height - 500) // 2

        from src.data.pokedex import Pokedex
        pokedex = Pokedex()

        self.wave_config_dialog = WaveConfigDialog(
            dialog_x, dialog_y, 600, 500,
            self.wave_manager,
            self.path_manager,
            pokedex
        )

    def _open_tileset_manager_dialog(self):
        """Abre o diálogo de gerenciamento de tilesets"""
        current_layer = self.layer_manager.get_current_layer()
        if not current_layer:
            print("Nenhuma layer selecionada!")
            return

        dialog_x = self.screen_manager.viewport_x + (self.screen_manager.viewport_width - 600) // 2
        dialog_y = self.screen_manager.viewport_y + (self.screen_manager.viewport_height - 500) // 2

        self.tileset_manager_dialog = TilesetManagerDialog(
            dialog_x, dialog_y, 600, 500,
            current_layer, self
        )

    def _handle_map_config_result(self, result):
        """Processa o resultado do diálogo de configuração"""
        if result:
            if result['width'] != self.layer_manager.width or result['height'] != self.layer_manager.height:
                self.layer_manager.resize_all_layers(result['width'], result['height'])
                print(f"Mapa redimensionado para {result['width']}x{result['height']}")

            chapter_changed = result['chapter'] != self.current_chapter
            phase_changed = result['phase'] != self.current_phase
            name_changed = result['name'] != self.phase_name

            self.current_chapter = result['chapter']
            self.current_phase = result['phase']
            self.phase_name = result['name']

            if chapter_changed or phase_changed or name_changed:
                print(f"Fase alterada para: {self.phase_name} (Capítulo {self.current_chapter}, Fase {self.current_phase})")
                self.clear_undo_history()

    def _handle_target_item_selected(self, item_id):
        """Guarda o ID do item selecionado"""
        self.selected_item_id = item_id
        print(f"Item {item_id} selecionado para adicionar")

    def handle_event(self, event):
        """Delega processamento de eventos para o input handler"""

        if self.tileset_manager_dialog and self.tileset_manager_dialog.visible:
            self.tileset_manager_dialog.handle_event(event)
            if not self.tileset_manager_dialog.visible:
                self.tileset_manager_dialog = None
            return True

        # Diálogo de recompensas (NOVO)
        if self.rewards_config_dialog and self.rewards_config_dialog.visible:
            result = self.rewards_config_dialog.handle_event(event)
            if result is not None:
                # Atualiza as recompensas
                self.phase_rewards.update(result)
                print(f"Recompensas atualizadas: Gold={self.phase_rewards['money']}, XP={self.phase_rewards['experience']}")
                self.rewards_config_dialog = None
            elif not self.rewards_config_dialog.visible:
                self.rewards_config_dialog = None
            return True

        # Diálogo de Items - processa e pode retornar "selected"
        if self.target_item_dialog and self.target_item_dialog.visible:
            result = self.target_item_dialog.handle_event(event)
            if result == "selected":
                # Usuário selecionou um item e fechou o diálogo
                item_id = self.target_item_dialog.selected_item_id
                print(f"Item selecionado: ID {item_id}")
                # CHAMA O MÉTODO PARA GUARDAR O ID
                self._handle_target_item_selected(item_id)
                # Fecha o diálogo
                self.target_item_dialog = None
            elif result is None and not self.target_item_dialog.visible:
                # Diálogo foi fechado sem selecionar
                self.target_item_dialog = None
            return True  # Sempre consome o evento enquanto diálogo visível

        # Diálogo de configuração de mapa
        if self.map_config_dialog and self.map_config_dialog.visible:
            result = self.map_config_dialog.handle_event(event)
            if result is not None:
                self._handle_map_config_result(result)
                self.map_config_dialog = None
            elif not self.map_config_dialog.visible:
                self.map_config_dialog = None
            return

        # Diálogo de configuração de waves
        if self.wave_config_dialog and self.wave_config_dialog.visible:
            result = self.wave_config_dialog.handle_event(event)
            if result == "saved":
                self.wave_config_dialog = None
            elif not self.wave_config_dialog.visible:
                self.wave_config_dialog = None
            return True

        # Diálogo de carregar fase
        if self.load_phase_dialog and self.load_phase_dialog.visible:
            result = self.load_phase_dialog.handle_event(event)
            if result is not None:
                self._handle_load_phase_result(result)
                self.load_phase_dialog = None
            elif not self.load_phase_dialog.visible:
                self.load_phase_dialog = None
            return

        if self.event_config_dialog and self.event_config_dialog.visible:
            result = self.event_config_dialog.handle_event(event)
            if result == "saved":
                self.event_config_dialog = None
            elif not self.event_config_dialog.visible:
                self.event_config_dialog = None
            return True

        if self.brush_buttons.handle_event(event):
            return True

        # Processa normalmente (sem diálogos ativos)
        self.input_handler.handle_event(event)

    def new_map(self):
        """Cria um novo mapa com configurações personalizadas"""
        self._open_map_config_dialog()

    def fixed_update(self, dt):
        """Update da lógica"""
        if self.paused:
            return

    def render(self, screen):
        """Delega renderização para o render handler"""
        self.render_handler.render(screen)

    def save_phase(self):
        """Salva a fase atual - INCLUINDO RECOMPENSAS"""
        phase_data = {
            "name": self.phase_name,
            "map": self.layer_manager.to_dict(),
            "paths": self.path_manager.to_dict(),
            "waves": self.wave_manager.to_dict(),
            "tower_spots": self.tower_spots.to_dict(),
            "target_items": self.target_items.to_dict(),
            "events": self.event_manager.to_dict(),
            "rewards": self.phase_rewards  # INCLUI AS RECOMPENSAS
        }

        self.exporter.export_phase(phase_data, self.current_chapter, self.current_phase)
        print(f"Fase salva com {len(self.wave_manager.waves)} waves, "
              f"{len(self.tower_spots.spots)} spots, "
              f"{len(self.target_items.items)} itens alvo, "
              f"{len(self.event_manager.triggers)} gatilhos de evento, e "
              f"recompensas: {self.phase_rewards['money']} gold, {self.phase_rewards['experience']} XP!")

    def load_phase(self, chapter, phase_number):
        """Carrega uma fase existente - INCLUINDO RECOMPENSAS"""
        print(f"\n=== CARREGANDO FASE {chapter}-{phase_number} ===")

        phase_data = self.exporter.load_phase(chapter, phase_number)

        if not phase_data:
            print(f"Fase {chapter}-{phase_number} não encontrada!")
            return False

        try:
            # Mostra estrutura do JSON
            print(f"Keys do phase_data: {phase_data.keys()}")

            # Pega o diretório raiz do projeto
            # Caminho atual: .../pokemon-tower-defense/src/scenes/editor/editor_scene.py
            current_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(__file__))))
            # Sobe 4 níveis para chegar na raiz
            project_root = os.path.abspath(os.path.join(current_dir))

            # Se ainda não estiver certo, tenta com caminho fixo para teste
            if not os.path.exists(os.path.join(project_root, "res")):
                # Tenta caminho alternativo
                project_root = os.path.dirname(
                    os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(__file__)))))

            print(f"Project root calculado: {project_root}")
            print(f"Pasta res existe? {os.path.exists(os.path.join(project_root, 'res'))}")

            # Carrega o mapa
            if "map" in phase_data:
                print(f"Mapa encontrado com {len(phase_data['map'].get('layers', []))} layers")
                self.layer_manager.from_dict(phase_data["map"], project_root)

            # Carrega os paths
            if "paths" in phase_data:
                self.path_manager.from_dict(phase_data["paths"])
                print(f"Paths carregados: {len(self.path_manager.paths)}")
            elif "path" in phase_data:
                # Compatibilidade com versão antiga
                self.path_manager = PathManager()
                path = Path()
                path.from_dict(phase_data["path"])
                self.path_manager.paths = [path]
                self.path_manager.current_path_index = 0
                print("Path carregado (formato antigo)")

            # Carrega waves
            if "waves" in phase_data:
                self.wave_manager.from_dict(phase_data["waves"])
                print(f"Waves carregadas: {len(self.wave_manager.waves)}")
            else:
                self.wave_manager = WaveManager()
                self.wave_manager.add_wave()
                print("Nenhuma wave encontrada, criada wave padrão")

            # Carrega os spots
            if "tower_spots" in phase_data:
                self.tower_spots.from_dict(phase_data["tower_spots"])
                print(f"Spots carregados: {len(self.tower_spots.spots)}")

            # Carrega os items
            if "target_items" in phase_data:
                self.target_items.from_dict(phase_data["target_items"])
                print(f"Itens alvo carregados: {len(self.target_items.items)}")

            if "events" in phase_data:
                self.event_manager.from_dict(phase_data["events"])
                print(f"Gatilhos de eventos carregados: {len(self.event_manager.triggers)}")
            else:
                self.event_manager = EventManager()
                print("Nenhum evento encontrado, criado gerenciador vazio")

            # Carrega as recompensas (NOVO)
            if "rewards" in phase_data:
                self.phase_rewards = phase_data["rewards"]
                print(f"Recompensas carregadas: Gold={self.phase_rewards.get('money', 100)}, XP={self.phase_rewards.get('experience', 50)}")
            else:
                # Valores padrão para fases antigas
                self.phase_rewards = {"money": 100, "experience": 50}
                print("Nenhuma recompensa encontrada, usando valores padrão (100 gold, 50 XP)")

            # Atualiza nome da fase
            self.phase_name = phase_data.get("name", f"Fase {chapter}-{phase_number}")
            self.current_chapter = chapter
            self.current_phase = phase_number

            # Atualiza a tile palette
            current_layer = self.layer_manager.get_current_layer()
            if current_layer and current_layer.tileset:
                self.tile_palette.set_tileset(current_layer.tileset)
                print("Tile palette atualizada")

            # Limpa historico
            self.clear_undo_history()

            print(f"\n✓ Fase {chapter}-{phase_number} carregada com sucesso!")
            print(f"  Layers: {len(self.layer_manager.layers)}")
            print(f"  Paths: {len(self.path_manager.paths)}")
            print(f"  Spots: {len(self.tower_spots.spots)}")
            print(f"  Itens: {len(self.target_items.items)}")
            print(f"  Recompensas: {self.phase_rewards['money']} gold, {self.phase_rewards['experience']} XP")
            return True

        except Exception as e:
            print(f"Erro ao carregar fase: {e}")
            import traceback
            traceback.print_exc()
            return False

    def list_available_phases(self):
        """Lista todas as fases disponíveis para carregar"""
        phases = self.exporter.list_phases()

        if not phases:
            print("Nenhuma fase encontrada!")
            return

        print("\nFases disponíveis:")
        for chapter, phase in phases:
            print(f"  Capítulo {chapter}, Fase {phase}")

    def clear_undo_history(self):
        """Limpa o histórico de undo/redo"""
        self.undo_manager.clear()
        print("Histórico de undo/redo limpo")