# src/editor/undo_manager.py

"""
Gerenciador de Undo/Redo para o Editor
"""
from collections import deque
import copy


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
        # CORRIGIDO: Agora usa path_manager em vez de path
        return {
            'layers': copy.deepcopy(editor_scene.layer_manager.to_dict()),
            'path_manager': copy.deepcopy(editor_scene.path_manager.to_dict()),  # Mudou aqui
            'tower_spots': copy.deepcopy(editor_scene.tower_spots.to_dict()),
            'current_tile': editor_scene.current_tile,
            'mode': editor_scene.mode,
            'timestamp': id(editor_scene)  # Para debug
        }

    def _restore_state(self, editor_scene, state):
        """Restaura um estado salvo"""
        try:
            # Restaura layers
            if 'layers' in state:
                editor_scene.layer_manager.from_dict(state['layers'])

            # CORRIGIDO: Restaura path_manager (compatibilidade com versões antigas)
            if 'path_manager' in state:
                editor_scene.path_manager.from_dict(state['path_manager'])
            elif 'path' in state:  # Compatibilidade com saves antigos
                # Converte path antigo para path_manager
                from src.scenes.editor.components.managers.path_manager import PathManager
                from src.editor.path_editor import Path

                new_path_manager = PathManager()
                path = Path()
                path.from_dict(state['path'])
                new_path_manager.paths = [path]
                new_path_manager.current_path_index = 0
                editor_scene.path_manager = new_path_manager

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

            print("[Undo] Estado restaurado com sucesso")

        except Exception as e:
            print(f"[Undo] Erro ao restaurar estado: {e}")

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