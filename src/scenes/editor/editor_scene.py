# src/scenes/editor/editor_scene.py

"""
Cena do Editor de Fases — com suporte a REGIÕES e ESTRUTURAS CUSTOMIZADAS.
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
from src.editor.structure_manager import StructureManager
from src.editor.autotile_system import AutotileManager
from src.config.paths import ALL_TILES_PATH
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
from src.scenes.editor.components.rewards_config_dialog import RewardsConfigDialog
from src.scenes.editor.components.structure_manager_dialog import StructureManagerDialog
from src.scenes.editor.components.structure_selection_panel import StructureSelectionPanel
from src.scenes.editor.handlers.input_handler import EditorInputHandler
from src.scenes.editor.handlers.map_handler import MapHandler
from src.scenes.editor.handlers.render_handler import EditorRenderHandler

from src.config.regions import (
    RegionCatalog, DEFAULT_REGION_ID,
    make_phase_id, normalize_phase_id,
)


class EditorScene(BaseScene):
    def __init__(self, game, chapter=None, phase=None, region=None):
        super().__init__(game)

        self.world_width = 3000
        self.world_height = 3000
        self.min_world_x = -1000
        self.min_world_y = -1000
        self.max_world_x = self.world_width + 1000
        self.max_world_y = self.world_height + 1000

        self.game.initialize_camera(self.world_width, self.world_height)
        self.camera = self.game.camera
        self.camera.set_limits(self.min_world_x, self.max_world_x,
                               self.min_world_y, self.max_world_y)
        self.camera.x = 0
        self.camera.y = 0

        self.day_night_mode = "random"
        self.base_weather = "random"

        self.current_region = int(region) if region is not None else DEFAULT_REGION_ID
        self.unlock_region = DEFAULT_REGION_ID

        # Gerenciadores
        self.layer_manager = LayerManager()
        self.path_manager = PathManager()
        self.tower_spots = TowerSpotManager()
        self.exporter = PhaseExporter()
        self.undo_manager = UndoManager(max_steps=10)
        self.target_items = TargetItemManager()
        self.event_manager = EventManager()
        self.structure_manager = StructureManager()

        # ===== AUTOTILE =====
        self.autotile_manager = AutotileManager(ALL_TILES_PATH)
        self.autotile_manager.load_all()

        # Estado do editor
        self.mode = "layers"
        self.current_tile = 1
        self.show_grid = True
        self.grid_size = 16
        self.snap_to_grid = True

        self.wave_manager = WaveManager()
        self.path_manager.set_wave_manager(self.wave_manager)

        self.phase_rewards = {
            "money": 100, "experience": 50, "item_rewards": [],
            "drop_chance": 0.0, "max_items": 3, "template_name": None,
        }

        self.tile_palette = None
        self.layer_selector = None
        self.mode_buttons = None

        self.font = pygame.font.Font(None, 24)
        self.font_small = pygame.font.Font(None, 18)

        self.map_config_dialog = None
        self.load_phase_dialog = None
        self.wave_config_dialog = None
        self.target_item_dialog = None
        self.event_config_dialog = None
        self.tileset_manager_dialog = None
        self.rewards_config_dialog = None
        self.structure_manager_dialog = None

        self.selected_item_id = None

        self.current_chapter = chapter or 1
        self.current_phase = phase or 1
        self.phase_name = f"Fase {self.current_chapter}-{self.current_phase}"

        self.root = Tk()
        self.root.withdraw()

        # ===== COLAR (preview) =====
        self.loaded_structure = None
        self.loaded_structure_name = None

        # ===== SELEÇÃO (novo fluxo) =====
        self.structure_selection_active = False
        self.structure_selection_mask = set()          # {(tx, ty)}
        self.structure_selection_dragging = False
        self.structure_selection_drag_start = None     # (tx, ty)
        self.structure_selection_drag_end = None       # (tx, ty)
        self.structure_selection_panel = None

        self._create_default_layers()
        self._init_ui()

        self.input_handler = EditorInputHandler(self)
        self.map_handler = MapHandler(self)
        self.render_handler = EditorRenderHandler(self)
        self.path_manager.add_path()

        self.localization_type = "default"
        self.custom_folder = ""
        self.unlock_chapter = 1
        self.unlock_phase = 1

        print(f"Editor iniciado - {self.phase_name} (Regiao {self.current_region})")

    # ==================================================================
    # INIT
    # ==================================================================
    def _create_default_layers(self):
        self.layer_manager.add_layer("Chão", LayerType.GROUND)
        self.layer_manager.add_layer("Decoração", LayerType.DECORATION)
        self.layer_manager.add_layer("Teto", LayerType.CEILING)

    def _init_ui(self):
        vx = self.screen_manager.viewport_x
        vy = self.screen_manager.viewport_y
        vw = self.screen_manager.viewport_width

        self.tile_palette = TilePalette(vx + vw - 280, vy + 200, 260, 380)
        self.tile_palette.set_autotile_manager(self.autotile_manager)

        self.layer_selector = LayerSelector(vx + 10, vy + 200, 180, 300)
        self.mode_buttons = ModeButtons(vx, vy)
        self.brush_buttons = BrushButtons(vx + 100, vy + 300)

        self._ensure_all_layers_have_autotiles()
        self._update_tile_palette_from_layer()

    def _add_layer_of_type(self, layer_type):
        if layer_type == LayerType.GROUND:
            base = "Chão"
        elif layer_type == LayerType.DECORATION:
            base = "Decoração"
        else:
            base = "Teto"

        existing = [l.name for l in self.layer_manager.layers]
        if base not in existing:
            name = base
        else:
            counter = 2
            while f"{base} {counter}" in existing:
                counter += 1
            name = f"{base} {counter}"

        self.undo_manager.save_state(self, f"Adicionar camada '{name}'")
        self.layer_manager.add_layer(name, layer_type)

        self.layer_manager.current_layer = len(self.layer_manager.layers) - 1
        self.layer_selector.set_layers(self.layer_manager.layers)
        self.layer_selector.selected_layer = self.layer_manager.current_layer
        self._ensure_layer_has_all_autotiles(self.layer_manager.get_current_layer())
        self._update_tile_palette_from_layer()

    def _remove_layer_at(self, index):
        if len(self.layer_manager.layers) <= 1:
            return
        if not (0 <= index < len(self.layer_manager.layers)):
            return

        removed = self.layer_manager.layers[index].name
        self.undo_manager.save_state(self, f"Remover camada '{removed}'")
        self.layer_manager.remove_layer(index)

        if self.layer_manager.current_layer >= len(self.layer_manager.layers):
            self.layer_manager.current_layer = len(self.layer_manager.layers) - 1
        self.layer_selector.set_layers(self.layer_manager.layers)
        self.layer_selector.selected_layer = self.layer_manager.current_layer
        self._update_tile_palette_from_layer()

    def _move_layer(self, from_index, to_index):
        """Reordena uma camada; ajusta índices de seleção."""
        n = len(self.layer_manager.layers)
        if not (0 <= from_index < n) or not (0 <= to_index < n) or from_index == to_index:
            return

        # Preserva a camada selecionada
        sel = self.layer_selector.selected_layer
        current = self.layer_manager.current_layer

        self.undo_manager.save_state(self, f"Mover camada {from_index} → {to_index}")
        self.layer_manager.move_layer(from_index, to_index)

        def _adjust(idx):
            if idx == from_index:
                return to_index
            if from_index < idx <= to_index:
                return idx - 1
            if to_index <= idx < from_index:
                return idx + 1
            return idx

        new_sel = _adjust(sel)
        new_cur = _adjust(current)
        self.layer_selector.selected_layer = max(0, min(n - 1, new_sel))
        self.layer_manager.current_layer = max(0, min(n - 1, new_cur))

        self.layer_selector.set_layers(self.layer_manager.layers)
        self._update_tile_palette_from_layer()

    def _cycle_layer_type(self, index):
        """Cicla o tipo: GROUND → DECORATION → CEILING → GROUND."""
        n = len(self.layer_manager.layers)
        if not (0 <= index < n):
            return

        layer = self.layer_manager.layers[index]
        cycle = [LayerType.GROUND, LayerType.DECORATION, LayerType.CEILING]
        try:
            cur = cycle.index(layer.layer_type)
        except ValueError:
            cur = 0
        new_type = cycle[(cur + 1) % len(cycle)]

        self.undo_manager.save_state(
            self, f"Camada {index} ('{layer.name}') → {new_type.value}"
        )
        layer.layer_type = new_type
        print(f"[EDITOR] Camada {index} ('{layer.name}') agora é '{new_type.value}'")

    # ==================================================================
    # MODO
    # ==================================================================
    def set_mode(self, mode):
        self.mode = mode

        if mode == "path":
            if not self.wave_manager.waves:
                self.wave_manager.add_wave()
        elif mode == "load_phase":
            self._open_load_phase_dialog()
        elif mode == "items":
            self._open_target_item_dialog()
        elif mode in ("layers", "towers"):
            if self.target_item_dialog:
                self.target_item_dialog.visible = False
        elif mode == "events":
            self._open_event_config_dialog()
        elif mode == "tilesets":
            self._open_tileset_manager_dialog()
        elif mode == "rewards":
            self._open_rewards_config_dialog()

    # ==================================================================
    # ESTRUTURAS — COLAR (preview)
    # ==================================================================
    def _open_structure_dialog(self):
        dialog_w, dialog_h = 640, 540
        dx = self.screen_manager.viewport_x + (self.screen_manager.viewport_width - dialog_w) // 2
        dy = self.screen_manager.viewport_y + (self.screen_manager.viewport_height - dialog_h) // 2
        self.structure_manager_dialog = StructureManagerDialog(dx, dy, dialog_w, dialog_h, self)

    def clear_loaded_structure(self):
        self.loaded_structure = None
        self.loaded_structure_name = None

    # ==================================================================
    # ESTRUTURAS — SELEÇÃO (novo fluxo de captura)
    # ==================================================================
    def start_structure_selection(self):
        """Ativa o modo de seleção para criar uma nova estrutura."""
        self.structure_selection_active = True
        self.structure_selection_mask = set()
        self.structure_selection_dragging = False
        self.structure_selection_drag_start = None
        self.structure_selection_drag_end = None

        vx = self.screen_manager.viewport_x
        vy = self.screen_manager.viewport_y
        self.structure_selection_panel = StructureSelectionPanel(vx + 20, vy + 80, self)

        print("[Editor] Modo de seleção de estrutura ativo")
        print("       [R]etângulo / [C]írculo | Add/Rem | Botão direito cancela arraste")

    def cancel_structure_selection(self):
        self.structure_selection_active = False
        self.structure_selection_mask = set()
        self.structure_selection_dragging = False
        self.structure_selection_drag_start = None
        self.structure_selection_drag_end = None
        self.structure_selection_panel = None
        print("[Editor] Seleção de estrutura cancelada")

    def save_structure_selection(self):
        """Salva a estrutura selecionada (só camadas visíveis)."""
        if not self.structure_selection_mask:
            print("[Editor] Nada selecionado — abortando")
            return

        name = ""
        if self.structure_selection_panel:
            name = self.structure_selection_panel.name_input.strip()
        if not name:
            name = "estrutura_nova"

        structure = self.structure_manager.capture_from_mask(
            self.layer_manager, self.structure_selection_mask, only_visible=True
        )
        if not structure:
            print("[Editor] Falha ao capturar estrutura")
            return

        ok = self.structure_manager.save(name, structure)
        if ok:
            w = structure.get("width")
            h = structure.get("height")
            n = len(structure.get("layers", []))
            print(f"[Editor] ✓ Estrutura '{name}' salva ({w}x{h}, {n} camadas visíveis)")
        self.cancel_structure_selection()

    def _commit_selection_drag(self):
        if not self.structure_selection_drag_start or not self.structure_selection_drag_end:
            return
        x0, y0 = self.structure_selection_drag_start
        x1, y1 = self.structure_selection_drag_end

        panel = self.structure_selection_panel
        tool = panel.tool if panel else "rect"
        op = panel.operation if panel else "add"
        filled = panel.filled if panel else True

        if tool == "rect":
            cells = self.structure_manager.get_rect_cells(x0, y0, x1, y1)
        else:
            cells = self.structure_manager.get_circle_cells(x0, y0, x1, y1, filled=filled)

        if op == "add":
            self.structure_selection_mask.update(cells)
        else:
            self.structure_selection_mask.difference_update(cells)

        self.structure_selection_drag_start = None
        self.structure_selection_drag_end = None

    # ==================================================================
    # DIÁLOGOS
    # ==================================================================
    def _open_rewards_config_dialog(self):
        dx = self.screen_manager.viewport_x + (self.screen_manager.viewport_width - 500) // 2
        dy = self.screen_manager.viewport_y + (self.screen_manager.viewport_height - 500) // 2
        self.rewards_config_dialog = RewardsConfigDialog(
            dx, dy, 500, 480,
            current_money=self.phase_rewards.get("money", 100),
            current_xp=self.phase_rewards.get("experience", 50),
            item_rewards=self.phase_rewards.get("item_rewards", []),
            drop_chance=self.phase_rewards.get("drop_chance", 0.0),
            max_items=self.phase_rewards.get("max_items", 3),
            template_name=self.phase_rewards.get("template_name"),
        )

    def _open_map_config_dialog(self):
        current_layer = self.layer_manager.get_current_layer()
        if not current_layer:
            return
        dialog_w, dialog_h = 520, 560
        dx = self.screen_manager.viewport_x + (self.screen_manager.viewport_width - dialog_w) // 2
        dy = self.screen_manager.viewport_y + (self.screen_manager.viewport_height - dialog_h) // 2
        self.map_config_dialog = MapConfigDialog(
            dx, dy, dialog_w, dialog_h,
            current_layer.width, current_layer.height,
            self.current_chapter, self.current_phase, self.phase_name,
            self.localization_type, self.custom_folder,
            getattr(self, 'unlock_chapter', 1),
            getattr(self, 'unlock_phase', 1),
            self.day_night_mode, self.base_weather,
            current_region=self.current_region,
            current_unlock_region=getattr(self, 'unlock_region', DEFAULT_REGION_ID),
        )

    def _open_load_phase_dialog(self):
        dialog_w, dialog_h = 560, 520
        dx = self.screen_manager.viewport_x + (self.screen_manager.viewport_width - dialog_w) // 2
        dy = self.screen_manager.viewport_y + (self.screen_manager.viewport_height - dialog_h) // 2
        self.load_phase_dialog = LoadPhaseDialog(dx, dy, dialog_w, dialog_h, self.exporter)

    def _open_target_item_dialog(self):
        dx = self.screen_manager.viewport_x + (self.screen_manager.viewport_width - 400) // 2
        dy = self.screen_manager.viewport_y + (self.screen_manager.viewport_height - 400) // 2
        self.target_item_dialog = TargetItemDialog(dx, dy, 400, 350, self.target_items)

    def _open_event_config_dialog(self):
        if not self.event_manager.triggers:
            self.event_manager.add_trigger()
        dx = self.screen_manager.viewport_x + (self.screen_manager.viewport_width - 700) // 2
        dy = self.screen_manager.viewport_y + (self.screen_manager.viewport_height - 500) // 2
        self.event_config_dialog = EventConfigDialog(dx, dy, 700, 500,
                                                      self.event_manager, self.wave_manager)

    def _open_wave_config_dialog(self):
        if not self.wave_manager.waves:
            self.wave_manager.add_wave()
        dx = self.screen_manager.viewport_x + (self.screen_manager.viewport_width - 600) // 2
        dy = self.screen_manager.viewport_y + (self.screen_manager.viewport_height - 500) // 2
        from src.data.pokedex import Pokedex
        self.wave_config_dialog = WaveConfigDialog(
            dx, dy, 600, 500, self.wave_manager, self.path_manager, Pokedex()
        )

    def _open_tileset_manager_dialog(self):
        current_layer = self.layer_manager.get_current_layer()
        if not current_layer:
            return
        dx = self.screen_manager.viewport_x + (self.screen_manager.viewport_width - 600) // 2
        dy = self.screen_manager.viewport_y + (self.screen_manager.viewport_height - 500) // 2
        self.tileset_manager_dialog = TilesetManagerDialog(dx, dy, 600, 500,
                                                            current_layer, self)

    # ==================================================================
    # RESULTADO DE DIÁLOGOS
    # ==================================================================
    def _handle_load_phase_result(self, result):
        if result and result.get('action') == 'load':
            region = int(result.get('region', DEFAULT_REGION_ID))
            chapter = result['chapter']
            phase = result['phase']
            loc = result.get('localization_type', 'default')
            folder = result.get('custom_folder', '')

            self.current_region = region
            self.localization_type = loc
            self.custom_folder = folder

            if self.load_phase(chapter, phase):
                print(f"{'Minigame' if loc == 'custom' else 'Fase'} "
                      f"{region}:{chapter}-{phase} carregado!")
            else:
                print(f"Falha ao carregar {region}:{chapter}-{phase}")

    def _handle_map_config_result(self, result):
        if not result:
            return
        if result['width'] != self.layer_manager.width or result['height'] != self.layer_manager.height:
            self.layer_manager.resize_all_layers(result['width'], result['height'])
            print(f"Mapa redimensionado para {result['width']}x{result['height']}")

        old_key = (self.current_region, self.current_chapter, self.current_phase)
        new_key = (int(result.get('region', DEFAULT_REGION_ID)),
                   result['chapter'], result['phase'])

        self.current_region = new_key[0]
        self.current_chapter = result['chapter']
        self.current_phase = result['phase']
        self.phase_name = result['name']
        self.localization_type = result.get('localization_type', 'default')
        self.custom_folder = result.get('custom_folder', '')
        self.day_night_mode = result.get('day_night_mode', 'random')
        self.base_weather = result.get('base_weather', 'random')

        if self.localization_type == "custom":
            self.unlock_region = int(result.get('unlock_region', DEFAULT_REGION_ID))
            self.unlock_chapter = int(result.get('unlock_chapter', 1))
            self.unlock_phase = int(result.get('unlock_phase', 1))
        else:
            self.unlock_region = DEFAULT_REGION_ID
            self.unlock_chapter = 1
            self.unlock_phase = 1

        if old_key != new_key:
            print(f"Fase alterada para: {self.phase_name}")
            self.clear_undo_history()

    def _handle_target_item_selected(self, item_id):
        self.selected_item_id = item_id

    # ==================================================================
    # HANDLE EVENT
    # ==================================================================
    def handle_event(self, event):
        # ===== SELEÇÃO DE ESTRUTURA ATIVA — intercepta tudo =====
        if self.structure_selection_active:
            self._handle_structure_selection_event(event)
            return True

        # Diálogos têm prioridade máxima
        if self.tileset_manager_dialog and self.tileset_manager_dialog.visible:
            self.tileset_manager_dialog.handle_event(event)
            if not self.tileset_manager_dialog.visible:
                self.tileset_manager_dialog = None
            return True

        if self.rewards_config_dialog and self.rewards_config_dialog.visible:
            result = self.rewards_config_dialog.handle_event(event)
            if isinstance(result, dict):
                self.phase_rewards.update(result)
                self.rewards_config_dialog = None
            elif not self.rewards_config_dialog.visible:
                self.rewards_config_dialog = None
            return True

        if self.target_item_dialog and self.target_item_dialog.visible:
            result = self.target_item_dialog.handle_event(event)
            if result == "selected":
                item_id = self.target_item_dialog.selected_item_id
                self._handle_target_item_selected(item_id)
                self.target_item_dialog = None
            elif result is None and not self.target_item_dialog.visible:
                self.target_item_dialog = None
            return True

        if self.map_config_dialog and self.map_config_dialog.visible:
            result = self.map_config_dialog.handle_event(event)
            if result is not None:
                self._handle_map_config_result(result)
                self.map_config_dialog = None
            elif not self.map_config_dialog.visible:
                self.map_config_dialog = None
            return True

        if self.wave_config_dialog and self.wave_config_dialog.visible:
            result = self.wave_config_dialog.handle_event(event)
            if result == "saved":
                self.wave_config_dialog = None
            elif not self.wave_config_dialog.visible:
                self.wave_config_dialog = None
            return True

        if self.load_phase_dialog and self.load_phase_dialog.visible:
            result = self.load_phase_dialog.handle_event(event)
            if result is not None:
                self._handle_load_phase_result(result)
                self.load_phase_dialog = None
            elif not self.load_phase_dialog.visible:
                self.load_phase_dialog = None
            return True

        if self.event_config_dialog and self.event_config_dialog.visible:
            result = self.event_config_dialog.handle_event(event)
            if result == "saved":
                self.event_config_dialog = None
            elif not self.event_config_dialog.visible:
                self.event_config_dialog = None
            return True

        # Diálogo de estruturas
        if self.structure_manager_dialog and self.structure_manager_dialog.visible:
            result = self.structure_manager_dialog.handle_event(event)
            if result == "loaded":
                self.structure_manager_dialog = None
            elif not self.structure_manager_dialog.visible:
                self.structure_manager_dialog = None
            return True

        # Botões de ferramenta
        handled_by_brush = self.brush_buttons.handle_event(event)

        if self.brush_buttons.pending_action:
            action = self.brush_buttons.pending_action
            self.brush_buttons.pending_action = None
            if action.get('action') == 'open_structure_dialog':
                self._open_structure_dialog()

        if handled_by_brush:
            return True

        self.input_handler.handle_event(event)

    # ==================================================================
    # HANDLE EVENT — MODO SELEÇÃO DE ESTRUTURA
    # ==================================================================
    def _handle_structure_selection_event(self, event):
        # ===== 1) PAINEL DE SELEÇÃO (prioridade máxima) =====
        if self.structure_selection_panel and self.structure_selection_panel.visible:
            result = self.structure_selection_panel.handle_event(event)
            if result == "save":
                self.save_structure_selection();
                return
            if result == "cancel":
                self.cancel_structure_selection();
                return
            if result == "clear":
                self.structure_selection_mask.clear();
                return

            # Consome se o mouse está sobre o painel
            if event.type in (pygame.MOUSEBUTTONDOWN, pygame.MOUSEBUTTONUP, pygame.MOUSEMOTION):
                if self.structure_selection_panel.rect.collidepoint(pygame.mouse.get_pos()):
                    return
            if event.type == pygame.KEYDOWN and self.structure_selection_panel.active_input:
                return

        # ===== 2) LAYER SELECTOR (para ocultar/mostrar camadas) =====
        if self.layer_selector and self.layer_selector.handle_event(event):
            pending = self.layer_selector.pending_action
            if pending:
                self.layer_selector.pending_action = None
                action = pending['action']

                if action == 'add':
                    self._add_layer_of_type(pending['type'])
                elif action == 'remove':
                    self._remove_layer_at(pending['index'])
                elif action == 'toggle_visibility':
                    idx = pending['index']
                    if 0 <= idx < len(self.layer_manager.layers):
                        layer = self.layer_manager.layers[idx]
                        layer.visible = not layer.visible
                        state = "visível" if layer.visible else "oculta"
                        print(f"[EDITOR] Camada {idx} ('{layer.name}') {state}")
                elif action == 'move_layer':
                    self._move_layer(pending['from'], pending['to'])
                elif action == 'change_type':
                    self._cycle_layer_type(pending['index'])

            self.layer_manager.current_layer = self.layer_selector.selected_layer

            current_layer = self.layer_manager.get_current_layer()
            if current_layer and current_layer.tileset:
                all_tiles, boundaries = current_layer.get_all_tiles_with_boundaries()
                natural_cols = None
                if current_layer.tilesets:
                    natural_cols = current_layer.tilesets[0].get('cols', 6)
                self.tile_palette.set_tileset(all_tiles, boundaries, natural_cols=natural_cols)

            return

        # ===== 3) ATALHOS =====
        if event.type == pygame.KEYDOWN:
            if event.key == pygame.K_ESCAPE:
                if self.structure_selection_dragging:
                    self.structure_selection_dragging = False
                    self.structure_selection_drag_start = None
                    self.structure_selection_drag_end = None
                else:
                    self.cancel_structure_selection()
                return
            if event.key == pygame.K_r and self.structure_selection_panel:
                self.structure_selection_panel.tool = "rect";
                return
            if event.key == pygame.K_c and self.structure_selection_panel:
                self.structure_selection_panel.tool = "circle";
                return
            if event.key == pygame.K_f and self.structure_selection_panel:
                self.structure_selection_panel.filled = not self.structure_selection_panel.filled;
                return

        # ===== 4) CÂMERA (botão do meio) =====
        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 2:
            self.input_handler.handle_event(event);
            return
        if event.type == pygame.MOUSEBUTTONUP and event.button == 2:
            self.input_handler.handle_event(event);
            return
        if event.type == pygame.MOUSEMOTION and self.input_handler.dragging_camera:
            self.input_handler.handle_event(event);
            return

        # ===== 5) BOTÃO DIREITO — cancela arraste =====
        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 3:
            self.structure_selection_dragging = False
            self.structure_selection_drag_start = None
            self.structure_selection_drag_end = None
            return

        # ===== 6) BOTÃO ESQUERDO — inicia arraste (só no viewport, fora de UIs) =====
        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            mp = pygame.mouse.get_pos()
            # Ignora se o mouse está sobre qualquer UI flutuante
            if (self.structure_selection_panel and
                    self.structure_selection_panel.rect.collidepoint(mp)):
                return
            if self.layer_selector and self.layer_selector.rect.collidepoint(mp):
                return
            if self.brush_buttons and self.brush_buttons.rect.collidepoint(mp):
                return
            if self.tile_palette and self.tile_palette.rect.collidepoint(mp):
                return

            if self.screen_manager.is_mouse_in_viewport(mp):
                world_pos = self.screen_manager.get_mouse_world_position(mp, self.camera)
                if world_pos:
                    tx = int(world_pos[0] // self.grid_size)
                    ty = int(world_pos[1] // self.grid_size)
                    self.structure_selection_dragging = True
                    self.structure_selection_drag_start = (tx, ty)
                    self.structure_selection_drag_end = (tx, ty)
            return

        # ===== 7) MOVIMENTO — atualiza ponta =====
        if event.type == pygame.MOUSEMOTION and self.structure_selection_dragging:
            mp = pygame.mouse.get_pos()
            if self.screen_manager.is_mouse_in_viewport(mp):
                world_pos = self.screen_manager.get_mouse_world_position(mp, self.camera)
                if world_pos:
                    tx = int(world_pos[0] // self.grid_size)
                    ty = int(world_pos[1] // self.grid_size)
                    self.structure_selection_drag_end = (tx, ty)
            return

        # ===== 8) SOLTA — commita =====
        if event.type == pygame.MOUSEBUTTONUP and event.button == 1:
            if self.structure_selection_dragging:
                self._commit_selection_drag()
                self.structure_selection_dragging = False
            return

    # ==================================================================
    # CLICKS NO MAPA (fluxo normal)
    # ==================================================================
    def _handle_left_click(self, world_pos, continuous=False):
        if self.mode == "items" and not continuous:
            if getattr(self, 'selected_item_id', None) is None:
                print("Nenhum item selecionado! Use o modo Items.")
                return True
            tile_x = int(world_pos[0] // self.grid_size)
            tile_y = int(world_pos[1] // self.grid_size)
            gx, gy = tile_x * self.grid_size, tile_y * self.grid_size
            self.undo_manager.save_state(self, f"Criar item {self.selected_item_id} em ({gx}, {gy})")
            self.target_items.add_item(gx, gy, self.selected_item_id)
            return True
        self.map_handler.handle_left_click(world_pos, continuous)

    def _handle_right_click(self, world_pos):
        if self.loaded_structure is not None:
            self.clear_loaded_structure()
            print("[Editor] Estrutura descarregada")
            return True

        if self.mode == "items":
            tile_x = int(world_pos[0] // self.grid_size)
            tile_y = int(world_pos[1] // self.grid_size)
            gx, gy = tile_x * self.grid_size, tile_y * self.grid_size
            items_at = self.target_items.get_items_at(gx + 8, gy + 8)
            if items_at:
                self.undo_manager.save_state(self, f"Remover item em ({gx}, {gy})")
                self.target_items.remove_item(items_at[0])
            return True

        self.map_handler.handle_right_click(world_pos)

    # ==================================================================
    # TILESET / PALETTE
    # ==================================================================
    def _import_tileset(self):
        file_path = filedialog.askopenfilename(
            title="Selecione uma imagem de tileset",
            filetypes=[("Image files", "*.png *.jpg *.jpeg *.bmp *.gif")],
        )
        if not file_path:
            return
        current_layer = self.layer_manager.get_current_layer()
        if not current_layer:
            return
        if not current_layer.tileset:
            ok = current_layer.load_tileset_from_image(file_path, self.grid_size, self.grid_size)
        else:
            ok = current_layer.add_tileset_from_image(file_path, self.grid_size, self.grid_size)
        if not ok:
            return
        all_tiles, boundaries = current_layer.get_all_tiles_with_boundaries()
        natural_cols = current_layer.tilesets[0].get('cols', 6) if current_layer.tilesets else None
        self.tile_palette.set_tileset(all_tiles, boundaries, natural_cols=natural_cols)
        self.tile_palette._update_max_scroll()

    def _ensure_layer_has_all_autotiles(self, layer):
        """Garante que a layer tem os tiles de autotile tanto em metadata quanto no tileset real."""
        if not layer or not self.autotile_manager:
            return False
        changed = False
        for local_id, sheet in self.autotile_manager.by_local_id.items():
            info = layer.find_autotile_tileset(local_id)

            # Verifica se precisa adicionar
            needs = False
            if info is None:
                needs = True
            else:
                expected_end = info['start_id'] + info['count'] - 1
                if len(layer.tileset) < expected_end:
                    needs = True

            if needs:
                layer.add_autotile_tileset(
                    local_id=local_id,
                    sheet_path=sheet.path,
                    tiles=sheet.tiles,
                    cell_size=sheet.cell_size,
                    cols=sheet.cols,
                    rows=sheet.rows,
                )
                changed = True

        if changed:
            print(f"[Editor] Layer '{layer.name}': "
                  f"tilesets de autotile sincronizados "
                  f"(tileset agora tem {len(layer.tileset)} tiles)")
        return changed

    def _ensure_all_layers_have_autotiles(self):
        """Garante que TODAS as layers têm os tilesets de autotile registrados."""
        if not self.autotile_manager:
            return
        for lyr in self.layer_manager.layers:
            self._ensure_layer_has_all_autotiles(lyr)

    def _update_tile_palette_from_layer(self):
        current_layer = self.layer_manager.get_current_layer()
        if not current_layer:
            return
        # Garante que todos os autotiles estão no tileset da layer
        self._ensure_layer_has_all_autotiles(current_layer)
        if not current_layer.tileset:
            return
        all_tiles, boundaries = current_layer.get_all_tiles_with_boundaries()
        natural_cols = current_layer.tilesets[0].get('cols', 6) if current_layer.tilesets else None
        self.tile_palette.set_tileset(all_tiles, boundaries, natural_cols=natural_cols)

    def _delete_selected(self):
        if self.mode == "path":
            cp = self.path_manager.get_current_path()
            if cp and cp.selected_node >= 0:
                cp.remove_node(cp.selected_node)
                cp.selected_node = -1
        elif self.mode == "towers" and self.tower_spots.selected_spot >= 0:
            self.tower_spots.remove_spot_by_index(self.tower_spots.selected_spot)

    # ==================================================================
    # SAVE / LOAD
    # ==================================================================
    def save_phase(self):
        phase_data = {
            "name": self.phase_name,
            "map": self.layer_manager.to_dict(),
            "paths": self.path_manager.to_dict(),
            "waves": self.wave_manager.to_dict(),
            "tower_spots": self.tower_spots.to_dict(),
            "target_items": self.target_items.to_dict(),
            "events": self.event_manager.to_dict(),
            "rewards": self.phase_rewards,
            "day_night_mode": self.day_night_mode,
            "base_weather": self.base_weather,
        }
        self.exporter.export_phase(
            phase_data,
            self.current_chapter, self.current_phase,
            self.localization_type, self.custom_folder,
            getattr(self, 'unlock_chapter', 1),
            getattr(self, 'unlock_phase', 1),
            region=self.current_region,
            unlock_region=getattr(self, 'unlock_region', DEFAULT_REGION_ID),
        )
        tipo = "Minigame" if self.localization_type == "custom" else "Fase"
        print(f"{tipo} salva em Regiao {self.current_region}")

    def load_phase(self, chapter, phase_number):
        phase_data = self.exporter.load_phase(
            chapter, phase_number,
            self.localization_type, self.custom_folder,
            region=self.current_region,
        )
        if not phase_data:
            print(f"Fase {self.current_region}:{chapter}-{phase_number} nao encontrada!")
            return False

        try:
            current_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(__file__))))
            project_root = os.path.abspath(current_dir)
            if not os.path.exists(os.path.join(project_root, "res")):
                project_root = os.path.dirname(
                    os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(__file__)))))

            if "map" in phase_data:
                self.layer_manager.from_dict(phase_data["map"], project_root)
                self.layer_manager.current_layer = 0
                if hasattr(self, 'layer_selector') and self.layer_selector:
                    self.layer_selector.set_layers(self.layer_manager.layers)
                    self.layer_selector.selected_layer = 0
                cur = self.layer_manager.get_current_layer()
                if cur and getattr(cur, 'tile_size', None):
                    self.grid_size = cur.tile_size

            if "paths" in phase_data:
                self.path_manager.from_dict(phase_data["paths"])
            elif "path" in phase_data:
                self.path_manager = PathManager()
                path = Path()
                path.from_dict(phase_data["path"])
                self.path_manager.paths = [path]
                self.path_manager.current_path_index = 0

            if "waves" in phase_data:
                self.wave_manager.from_dict(phase_data["waves"])
            else:
                self.wave_manager = WaveManager()
                self.wave_manager.add_wave()

            if "tower_spots" in phase_data:
                self.tower_spots.from_dict(phase_data["tower_spots"])
            if "target_items" in phase_data:
                self.target_items.from_dict(phase_data["target_items"])
            if "events" in phase_data:
                self.event_manager.from_dict(phase_data["events"])
            else:
                self.event_manager = EventManager()
            if "rewards" in phase_data:
                self.phase_rewards = phase_data["rewards"]

            self.current_region = int(phase_data.get("region", self.current_region))
            self.day_night_mode = phase_data.get("day_night_mode", "random")
            self.base_weather = phase_data.get("base_weather", "random")

            if "localization_type" in phase_data:
                self.localization_type = phase_data["localization_type"]
                self.custom_folder = phase_data.get("custom_folder", "")

            if self.localization_type == "custom" and "unlock_requirement" in phase_data:
                ur = phase_data["unlock_requirement"]
                self.unlock_region = int(ur.get("region", DEFAULT_REGION_ID))
                self.unlock_chapter = int(ur.get("chapter", 1))
                self.unlock_phase = int(ur.get("phase", 1))
            else:
                self.unlock_region = DEFAULT_REGION_ID
                self.unlock_chapter = 1
                self.unlock_phase = 1

            self.phase_name = phase_data.get("name", f"Fase {chapter}-{phase_number}")
            self.current_chapter = chapter
            self.current_phase = phase_number

            # ===== AUTOTILE: sincroniza em todas as layers carregadas =====
            for lyr in self.layer_manager.layers:
                self._ensure_layer_has_all_autotiles(lyr)

            cur = self.layer_manager.get_current_layer()
            if cur and cur.tileset:
                all_tiles, boundaries = cur.get_all_tiles_with_boundaries()
                natural_cols = cur.tilesets[0].get('cols', 6) if cur.tilesets else None
                self.tile_palette.set_tileset(all_tiles, boundaries, natural_cols=natural_cols)

            if hasattr(self, 'wave_manager') and hasattr(self, 'path_manager'):
                self.path_manager.set_wave_manager(self.wave_manager)

            # limpeza
            self.clear_loaded_structure()
            if self.structure_selection_active:
                self.cancel_structure_selection()

            self.clear_undo_history()

            if cur:
                map_w = cur.width * self.grid_size
                map_h = cur.height * self.grid_size
                self.min_world_x = -1000
                self.min_world_y = -1000
                self.max_world_x = map_w + 1000
                self.max_world_y = map_h + 1000
                if hasattr(self, 'camera'):
                    self.camera.set_limits(self.min_world_x, self.max_world_x,
                                            self.min_world_y, self.max_world_y)
            return True
        except Exception as e:
            print(f"Erro ao carregar fase: {e}")
            import traceback
            traceback.print_exc()
            return False

    def list_available_phases(self):
        phases = self.exporter.list_phases()
        if not phases:
            print("Nenhuma fase encontrada!")
            return
        print("\nFases disponíveis:")
        for entry in phases:
            if len(entry) == 3:
                r, c, p = entry
                print(f"  Regiao {r} - Cap {c} - Fase {p}")

    def clear_undo_history(self):
        self.undo_manager.clear()

    def new_map(self):
        self._open_map_config_dialog()

    def fixed_update(self, dt):
        if self.paused:
            return

    def render(self, screen):
        self.render_handler.render(screen)