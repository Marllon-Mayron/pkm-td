# src/editor/undo_manager.py

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
        """Captura o estado atual do editor"""
        # Captura os dados das layers com informações dos tilesets
        layers_data = []
        for layer in editor_scene.layer_manager.layers:
            layer_dict = {
                'name': layer.name,
                'type': layer.layer_type.value,
                'tiles': [row[:] for row in layer.tiles],  # Cópia profunda da matriz
                'tileset_path': layer.tileset_path,  # IMPORTANTE: salva o caminho do tileset
                'width': layer.width,
                'height': layer.height
            }
            layers_data.append(layer_dict)

        return {
            'layers': layers_data,
            'path_manager': copy.deepcopy(editor_scene.path_manager.to_dict()),
            'tower_spots': copy.deepcopy(editor_scene.tower_spots.to_dict()),
            'current_tile': editor_scene.current_tile,
            'mode': editor_scene.mode,
            'timestamp': id(editor_scene)  # Para debug
        }

    def _restore_state(self, editor_scene, state):
        """Restaura um estado salvo - PRESERVANDO OS TILESETS"""
        try:
            # Restaura layers preservando os tilesets
            if 'layers' in state:
                # Primeiro, guarda os tilesets atuais
                current_tilesets = {}
                for i, layer in enumerate(editor_scene.layer_manager.layers):
                    if layer.tileset:
                        current_tilesets[i] = {
                            'tileset': layer.tileset,
                            'tileset_path': layer.tileset_path
                        }

                # Restaura os dados das layers
                for i, layer_data in enumerate(state['layers']):
                    if i < len(editor_scene.layer_manager.layers):
                        layer = editor_scene.layer_manager.layers[i]

                        # Restaura a matriz de tiles
                        for y in range(min(len(layer_data['tiles']), layer.height)):
                            for x in range(min(len(layer_data['tiles'][y]), layer.width)):
                                if y < layer.height and x < layer.width:
                                    layer.tiles[y][x] = layer_data['tiles'][y][x]

                        # PRESERVA O TILESET (não sobrescreve com None)
                        # Só atualiza o caminho se veio algo no estado E não é None
                        if 'tileset_path' in layer_data and layer_data['tileset_path']:
                            layer.tileset_path = layer_data['tileset_path']

                        # Se perdeu o tileset mas tem caminho, tenta recarregar
                        if not layer.tileset and layer.tileset_path:
                            # Tenta recarregar o tileset do caminho salvo
                            project_root = getattr(editor_scene, 'project_root', '')
                            if project_root:
                                full_path = os.path.join(project_root, layer.tileset_path)
                                if os.path.exists(full_path):
                                    layer.load_tileset(full_path, editor_scene.grid_size, editor_scene.grid_size)

            # Restaura path_manager
            if 'path_manager' in state:
                editor_scene.path_manager.from_dict(state['path_manager'])

            # Restaura tower spots
            if 'tower_spots' in state:
                editor_scene.tower_spots.from_dict(state['tower_spots'])

            # Restaura outras propriedades
            if 'current_tile' in state:
                editor_scene.current_tile = state['current_tile']

            # Atualiza UI
            current_layer = editor_scene.layer_manager.get_current_layer()
            if current_layer and current_layer.tileset:
                editor_scene.tile_palette.set_tileset(current_layer.tileset)

            print("[Undo] Estado restaurado com sucesso (tilesets preservados)")

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