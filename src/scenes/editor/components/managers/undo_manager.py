# src/scenes/editor/components/managers/undo_manager.py

"""
Gerenciador de Undo/Redo para o Editor
"""
from collections import deque
import copy, os


class UndoManager:
    """Gerencia o histórico de ações para desfazer/refazer"""

    def __init__(self, max_steps=10):
        self.undo_stack = deque(maxlen=max_steps)  # Histórico para desfazer
        self.redo_stack = deque(maxlen=max_steps)  # Histórico para refazer
        self.max_steps = max_steps
        self.current_state = None  # Estado atual (cache)
        self.last_action = None  # Última ação para debug

    def save_state(self, editor_scene, action_description=""):
        """
        Salva o estado atual do editor
        Deve ser chamado ANTES de fazer uma modificação
        """
        # Captura o estado atual
        state = self._capture_state(editor_scene)

        # Se for diferente do último estado salvo, adiciona ao histórico
        if state != self.current_state:
            self.undo_stack.append({
                'state': state,
                'description': action_description
            })
            self.current_state = state
            # Limpa a pilha de redo quando uma nova ação é feita
            self.redo_stack.clear()
            print(f"[Undo] Estado salvo: {action_description}")
            return True
        return False

    def undo(self, editor_scene):
        """Desfaz a última ação"""
        if not self.undo_stack:
            print("[Undo] Nada para desfazer")
            return False

        # Salva o estado atual para possível redo
        current = self._capture_state(editor_scene)

        # Pega o último estado salvo
        last_state = self.undo_stack.pop()

        # Adiciona o estado atual à pilha de redo
        self.redo_stack.append({
            'state': current,
            'description': f"Redo: {last_state['description']}"
        })

        # Restaura o estado
        self._restore_state(editor_scene, last_state['state'])
        self.current_state = last_state['state']

        print(f"[Undo] Desfeito: {last_state['description']}")
        return True

    def redo(self, editor_scene):
        """Refaz a última ação desfeita"""
        if not self.redo_stack:
            print("[Undo] Nada para refazer")
            return False

        # Salva o estado atual para possível undo
        current = self._capture_state(editor_scene)

        # Pega o próximo estado
        next_state = self.redo_stack.pop()

        # Adiciona o estado atual à pilha de undo
        self.undo_stack.append({
            'state': current,
            'description': f"Undo: {next_state['description']}"
        })

        # Restaura o estado
        self._restore_state(editor_scene, next_state['state'])
        self.current_state = next_state['state']

        print(f"[Undo] Refado: {next_state['description']}")
        return True

    def _capture_state(self, editor_scene):
        """Captura o estado atual do editor com suporte a múltiplos tilesets"""
        # Captura os dados das layers com informações dos tilesets
        layers_data = []
        for layer in editor_scene.layer_manager.layers:
            layer_dict = {
                'name': layer.name,
                'type': layer.layer_type.value,
                'tiles': [row[:] for row in layer.tiles],
                'tile_offsets': dict(layer.tile_offsets),
                # ===== AUTOTILE =====
                'autotile_ids': [row[:] for row in getattr(layer, 'autotile_ids', [])],
                'autotile_tilesets': list(getattr(layer, 'autotile_tilesets', [])),
                'tileset_paths': layer.tileset_paths.copy() if hasattr(layer, 'tileset_paths') else [],
                'tileset_path': layer.tileset_path,
                'width': layer.width,
                'height': layer.height,
                'tile_size': layer.tile_size
            }

            # Salva informações completas dos tilesets
            if hasattr(layer, 'tilesets') and layer.tilesets:
                layer_dict['tilesets'] = []
                for ts_info in layer.tilesets:
                    layer_dict['tilesets'].append({
                        'path': ts_info['path'],
                        'count': ts_info['count'],
                        'start_id': ts_info['start_id'],
                        'cols': ts_info.get('cols', 6),
                        'rows': ts_info.get('rows', 8)
                    })

            layers_data.append(layer_dict)

        state = {
            'layers': layers_data,
            'path_manager': copy.deepcopy(editor_scene.path_manager.to_dict()),
            'tower_spots': copy.deepcopy(editor_scene.tower_spots.to_dict()),
            'wave_manager': copy.deepcopy(editor_scene.wave_manager.to_dict()),
            'target_items': copy.deepcopy(editor_scene.target_items.to_dict()),
            'events': copy.deepcopy(editor_scene.event_manager.to_dict()),
            'current_tile': editor_scene.current_tile,
            'mode': editor_scene.mode,
            'timestamp': id(editor_scene)  # Para debug
        }

        return state

    def _restore_state(self, editor_scene, state):
        """Restaura um estado salvo - PRESERVANDO OS TILESETS MÚLTIPLOS, OFFSETS E AUTOTILES."""
        try:
            print("\n[Undo] Iniciando restauração de estado...")

            # =========================================================
            # RESTAURA LAYERS (tiles + offsets + tilesets + autotiles)
            # =========================================================
            if 'layers' in state:
                # Primeiro, guarda os tilesets atuais de cada layer (para não recarregar)
                current_tilesets = {}
                for i, layer in enumerate(editor_scene.layer_manager.layers):
                    if layer.tileset:
                        current_tilesets[i] = {
                            'tilesets': layer.tilesets.copy() if hasattr(layer, 'tilesets') else [],
                            'tileset_paths': layer.tileset_paths.copy() if hasattr(layer, 'tileset_paths') else [],
                            'tileset': layer.tileset.copy() if layer.tileset else [],
                            'tileset_path': layer.tileset_path
                        }

                # Ajusta a quantidade de layers do editor para bater com o estado
                # (importante quando o usuário adiciona/remove camadas entre undos)
                target_layer_count = len(state['layers'])
                current_layer_count = len(editor_scene.layer_manager.layers)

                if target_layer_count != current_layer_count:
                    print(f"[Undo] Ajustando camadas: {current_layer_count} -> {target_layer_count}")
                    from src.editor.layer_manager import Layer, LayerType

                    if target_layer_count < current_layer_count:
                        # Remove camadas extras do fim
                        del editor_scene.layer_manager.layers[target_layer_count:]
                    else:
                        # Adiciona camadas vazias
                        for j in range(current_layer_count, target_layer_count):
                            ld = state['layers'][j]
                            try:
                                ltype = LayerType(ld.get('type', 'ground'))
                            except Exception:
                                ltype = LayerType.GROUND
                            new_layer = Layer(
                                ld.get('name', f'Layer {j}'),
                                ltype,
                                ld.get('width', editor_scene.layer_manager.width),
                                ld.get('height', editor_scene.layer_manager.height),
                                ld.get('tile_size', editor_scene.layer_manager.tile_size),
                            )
                            editor_scene.layer_manager.layers.append(new_layer)

                # Restaura os dados de cada layer
                for i, layer_data in enumerate(state['layers']):
                    if i >= len(editor_scene.layer_manager.layers):
                        break

                    layer = editor_scene.layer_manager.layers[i]

                    # Atualiza metadados básicos
                    layer.name = layer_data.get('name', layer.name)
                    layer.width = layer_data.get('width', layer.width)
                    layer.height = layer_data.get('height', layer.height)
                    layer.tile_size = layer_data.get('tile_size', layer.tile_size)

                    # ===== MATRIZ DE TILES =====
                    tiles_to_restore = layer_data.get('tiles', [])
                    for y in range(min(len(tiles_to_restore), layer.height)):
                        row = tiles_to_restore[y]
                        for x in range(min(len(row), layer.width)):
                            if y < layer.height and x < layer.width:
                                try:
                                    layer.tiles[y][x] = int(row[x])
                                except (ValueError, TypeError):
                                    layer.tiles[y][x] = 0

                    # ===== OFFSETS =====
                    if 'tile_offsets' in layer_data:
                        restored_offsets = {}
                        raw = layer_data['tile_offsets'] or {}
                        for key, off in raw.items():
                            try:
                                # Aceita tanto tupla (x,y) quanto string "x,y"
                                if isinstance(key, tuple):
                                    x, y = int(key[0]), int(key[1])
                                elif isinstance(key, str) and ',' in key:
                                    xs, ys = key.split(",")
                                    x, y = int(xs), int(ys)
                                else:
                                    continue

                                dx, dy = int(off[0]), int(off[1])
                                if (dx, dy) != (0, 0):
                                    restored_offsets[(x, y)] = (dx, dy)
                            except (ValueError, IndexError, TypeError):
                                continue

                        layer.tile_offsets = restored_offsets
                        print(f"[Undo] Layer {i}: {len(layer.tile_offsets)} offsets restaurados")
                    else:
                        layer.tile_offsets = {}

                    # ===== AUTOTILE =====
                    if 'autotile_ids' in layer_data:
                        try:
                            saved = layer_data['autotile_ids']
                            # Se a layer redimensionou, ajusta
                            for y in range(min(len(saved), layer.height)):
                                row = saved[y]
                                for x in range(min(len(row), layer.width)):
                                    try:
                                        layer.autotile_ids[y][x] = int(row[x])
                                    except (ValueError, TypeError):
                                        layer.autotile_ids[y][x] = 0
                            count = sum(1 for row in layer.autotile_ids for c in row if c != 0)
                            print(f"[Undo] Layer {i}: {count} autotiles restaurados")
                        except Exception as e:
                            print(f"[Undo] Layer {i}: erro ao restaurar autotiles: {e}")

                    layer.autotile_tilesets = list(layer_data.get('autotile_tilesets', []))

                    # ===== TILESETS =====
                    # Preserva os tilesets atuais se existirem
                    if i in current_tilesets and current_tilesets[i]['tilesets']:
                        layer.tilesets = current_tilesets[i]['tilesets'].copy()
                        layer.tileset_paths = current_tilesets[i]['tileset_paths'].copy()

                        # Reconstrói a lista principal de tiles a partir dos tilesets
                        layer.tileset = []
                        for ts_info in layer.tilesets:
                            layer.tileset.extend(ts_info['tiles'])

                        if layer.tileset_paths:
                            layer.tileset_path = layer.tileset_paths[0]

                        print(f"[Undo] Layer {i}: {len(layer.tilesets)} tilesets preservados")
                    else:
                        # Fallback: tenta recarregar do caminho salvo
                        tileset_paths = []
                        if 'tileset_paths' in layer_data and layer_data['tileset_paths']:
                            tileset_paths = layer_data['tileset_paths']
                        elif 'tileset_path' in layer_data and layer_data['tileset_path']:
                            tileset_paths = [layer_data['tileset_path']]

                        if tileset_paths:
                            print(f"[Undo] Layer {i}: recarregando {len(tileset_paths)} tilesets...")

                            layer.tilesets = []
                            layer.tileset = []
                            layer.tileset_paths = []

                            for ts_idx, ts_path in enumerate(tileset_paths):
                                if not ts_path:
                                    continue

                                project_root = getattr(editor_scene, 'project_root', '')
                                base_path = project_root or getattr(editor_scene, 'base_path', '')

                                possible_paths = []
                                basename = os.path.basename(ts_path)

                                if base_path:
                                    clean_path = ts_path
                                    if clean_path.startswith('pokemon-tower-defense/'):
                                        clean_path = clean_path[len('pokemon-tower-defense/'):]
                                    if clean_path.startswith('pokemon-tower-defense\\'):
                                        clean_path = clean_path[len('pokemon-tower-defense\\'):]
                                    full_path = os.path.join(base_path, clean_path)
                                    possible_paths.append(full_path)

                                possible_paths.append(os.path.join("res", "AllTiles", basename))

                                if base_path:
                                    res_path = os.path.join(base_path, "res", "AllTiles", basename)
                                    possible_paths.append(res_path)

                                possible_paths.append(basename)

                                loaded = False
                                for path in possible_paths:
                                    normalized = os.path.normpath(path)
                                    if os.path.exists(normalized):
                                        print(f"[Undo]   Carregando tileset {ts_idx + 1}: {normalized}")
                                        if ts_idx == 0 and not layer.tilesets:
                                            success = layer.load_tileset_from_image(
                                                normalized,
                                                editor_scene.grid_size,
                                                editor_scene.grid_size,
                                            )
                                        else:
                                            success = layer.add_tileset_from_image(
                                                normalized,
                                                editor_scene.grid_size,
                                                editor_scene.grid_size,
                                            )
                                        if success:
                                            loaded = True
                                            break

                                if not loaded:
                                    print(f"[Undo]   ERRO: Não foi possível carregar tileset {ts_idx + 1}: {ts_path}")

                            print(f"[Undo] Layer {i}: {len(layer.tileset)} tiles recarregados")

            # =========================================================
            # PATH MANAGER
            # =========================================================
            if 'path_manager' in state:
                try:
                    editor_scene.path_manager.from_dict(state['path_manager'])
                    print("[Undo] Path manager restaurado")
                except Exception as e:
                    print(f"[Undo] Erro ao restaurar path_manager: {e}")

            # =========================================================
            # TOWER SPOTS
            # =========================================================
            if 'tower_spots' in state:
                try:
                    editor_scene.tower_spots.from_dict(state['tower_spots'])
                    print("[Undo] Tower spots restaurados")
                except Exception as e:
                    print(f"[Undo] Erro ao restaurar tower_spots: {e}")

            # =========================================================
            # WAVE MANAGER
            # =========================================================
            if 'wave_manager' in state:
                try:
                    editor_scene.wave_manager.from_dict(state['wave_manager'])
                    print("[Undo] Wave manager restaurado")
                except Exception as e:
                    print(f"[Undo] Erro ao restaurar wave_manager: {e}")

            # =========================================================
            # TARGET ITEMS
            # =========================================================
            if 'target_items' in state:
                try:
                    editor_scene.target_items.from_dict(state['target_items'])
                    print("[Undo] Target items restaurados")
                except Exception as e:
                    print(f"[Undo] Erro ao restaurar target_items: {e}")

            # =========================================================
            # EVENT MANAGER
            # =========================================================
            if 'events' in state:
                try:
                    editor_scene.event_manager.from_dict(state['events'])
                    print("[Undo] Event manager restaurado")
                except Exception as e:
                    print(f"[Undo] Erro ao restaurar event_manager: {e}")

            # =========================================================
            # OUTRAS PROPRIEDADES
            # =========================================================
            if 'current_tile' in state:
                editor_scene.current_tile = state['current_tile']

            if 'mode' in state:
                editor_scene.mode = state['mode']

            # =========================================================
            # SINCRONIZA UI (palette + layer selector)
            # =========================================================
            current_layer = editor_scene.layer_manager.get_current_layer()
            if current_layer and current_layer.tileset:
                try:
                    if hasattr(current_layer, 'get_all_tiles_with_boundaries'):
                        all_tiles, boundaries = current_layer.get_all_tiles_with_boundaries()

                        natural_cols = None
                        if hasattr(current_layer, 'tilesets') and current_layer.tilesets:
                            natural_cols = current_layer.tilesets[0].get('cols', 6)

                        if hasattr(editor_scene, 'tile_palette') and editor_scene.tile_palette:
                            # set_tileset agora aceita natural_cols=
                            try:
                                editor_scene.tile_palette.set_tileset(
                                    all_tiles, boundaries, natural_cols=natural_cols
                                )
                            except TypeError:
                                # Fallback para assinatura antiga
                                editor_scene.tile_palette.set_tileset(all_tiles, boundaries)

                            print(f"[Undo] Tile palette atualizada: {len(all_tiles)} tiles, "
                                  f"{len(boundaries)} tilesets")
                    else:
                        if hasattr(editor_scene, 'tile_palette') and editor_scene.tile_palette:
                            editor_scene.tile_palette.set_tileset(current_layer.tileset)
                            print(f"[Undo] Tile palette atualizada (fallback): "
                                  f"{len(current_layer.tileset)} tiles")
                except Exception as e:
                    print(f"[Undo] Erro ao atualizar tile palette: {e}")

            # Atualiza o layer selector
            if hasattr(editor_scene, 'layer_selector') and editor_scene.layer_selector:
                editor_scene.layer_selector.set_layers(editor_scene.layer_manager.layers)

                # Garante que o índice está dentro do range
                max_idx = max(0, len(editor_scene.layer_manager.layers) - 1)
                if editor_scene.layer_selector.selected_layer > max_idx:
                    editor_scene.layer_selector.selected_layer = max_idx
                if editor_scene.layer_manager.current_layer > max_idx:
                    editor_scene.layer_manager.current_layer = max_idx

            print("[Undo] Estado restaurado com sucesso")

        except Exception as e:
            print(f"[Undo] Erro ao restaurar estado: {e}")
            import traceback
            traceback.print_exc()

    def can_undo(self):
        """Verifica se é possível desfazer"""
        return len(self.undo_stack) > 0

    def can_redo(self):
        """Verifica se é possível refazer"""
        return len(self.redo_stack) > 0

    def get_undo_description(self):
        """Retorna descrição da próxima ação a ser desfeita"""
        if self.undo_stack:
            return self.undo_stack[-1]['description']
        return ""

    def get_redo_description(self):
        """Retorna descrição da próxima ação a ser refeita"""
        if self.redo_stack:
            return self.redo_stack[-1]['description']
        return ""

    def clear(self):
        """Limpa todo o histórico"""
        self.undo_stack.clear()
        self.redo_stack.clear()
        self.current_state = None
        print("[Undo] Histórico limpo")