# src/scenes/editor/handlers/map_handler.py

import pygame


class MapHandler:
    """Gerencia as operações de edição do mapa"""

    def __init__(self, editor_scene):
        self.editor = editor_scene
        # Cache para evitar múltiplos saves de undo no mesmo tile durante arrasto
        self.last_undo_tile = None
        self.last_undo_time = 0
        self.undo_cooldown = 0.2  # Cooldown para salvar undo durante arrasto

    def _save_undo_state(self, action_description, continuous=False):
        """Método auxiliar para salvar estado antes de ações

        Args:
            action_description: Descrição da ação
            continuous: Se True, é uma ação contínua (arrasto) - aplica cooldown
        """
        if continuous:
            # Durante arrasto, aplica cooldown para não salvar undo a cada frame
            current_time = pygame.time.get_ticks() / 1000.0  # segundos
            if current_time - self.last_undo_time < self.undo_cooldown:
                # Ainda está dentro do cooldown, não salva undo
                return False
            self.last_undo_time = current_time

        # Salva o estado
        self.editor.undo_manager.save_state(self.editor, action_description)
        return True

    def handle_left_click(self, world_pos, continuous=False):
        """Processa clique esquerdo no mapa

        Args:
            world_pos: Posição mundial do clique
            continuous: Se True, é um clique durante arrasto (pintura contínua)
        """
        # Converte posição mundial para coordenadas de tile
        tile_x = int(world_pos[0] // self.editor.grid_size)
        tile_y = int(world_pos[1] // self.editor.grid_size)
        current_tile_pos = (tile_x, tile_y)

        current_layer = self.editor.layer_manager.get_current_layer()
        if not current_layer:
            return

        # Modo layers - desenha tile
        if self.editor.mode == "layers":
            if 0 <= tile_x < current_layer.width and 0 <= tile_y < current_layer.height:
                # Verifica se o tile já é o que queremos colocar
                current_tile_value = current_layer.get_tile(tile_x, tile_y)

                # Só faz algo se for um tile diferente
                if current_tile_value != self.editor.current_tile:
                    # Durante arrasto, só salva undo se for um tile diferente do último
                    should_save_undo = True

                    if continuous:
                        # Durante arrasto, verifica se mudou de tile desde o último undo
                        if current_tile_pos == self.last_undo_tile:
                            should_save_undo = False
                        else:
                            self.last_undo_tile = current_tile_pos

                    if should_save_undo:
                        self._save_undo_state(
                            f"Tile {self.editor.current_tile} em ({tile_x}, {tile_y})",
                            continuous
                        )

                    self.editor.layer_manager.set_tile(tile_x, tile_y, self.editor.current_tile)
                    print(f"Tile {self.editor.current_tile} colocado em ({tile_x}, {tile_y})")

        # Modo path - adiciona nó (NÃO deve ser contínuo)
        elif self.editor.mode == "path" and not continuous:
            current_path = self.editor.path_manager.get_current_path()
            if not current_path:
                # Se não há path atual, tenta criar um
                if self.editor.path_manager.add_path():
                    current_path = self.editor.path_manager.get_current_path()
                else:
                    print("Não foi possível criar novo path")
                    return

            # Ajusta para grid se necessário
            if self.editor.snap_to_grid:
                x = tile_x * self.editor.grid_size + self.editor.grid_size // 2
                y = tile_y * self.editor.grid_size + self.editor.grid_size // 2
            else:
                x, y = world_pos

            # Salva estado ANTES da modificação
            self._save_undo_state(f"Path node em ({x:.0f}, {y:.0f})", continuous=False)

            current_path.add_node((x, y))
            print(f"Nó do Path {self.editor.path_manager.current_path_index + 1} adicionado em ({x}, {y})")

        # Modo towers - adiciona spot (NÃO deve ser contínuo)
        elif self.editor.mode == "towers" and not continuous:
            # Ajusta para grid se necessário
            if self.editor.snap_to_grid:
                x = tile_x * self.editor.grid_size
                y = tile_y * self.editor.grid_size
            else:
                x = world_pos[0] - 16
                y = world_pos[1] - 16

            # Verifica se já existe spot nesta posição
            existing_spot = self.editor.tower_spots.get_spot_at(x + 8, y + 8)
            if existing_spot:
                print(f"Já existe um spot em ({x}, {y})")
            else:
                # Salva estado ANTES da modificação
                self._save_undo_state(f"Tower spot em ({x:.0f}, {y:.0f})", continuous=False)

                self.editor.tower_spots.add_spot(x, y)

    def handle_right_click(self, world_pos):
        """Processa clique direito no mapa (apagar)"""
        # Converte posição mundial para coordenadas de tile
        tile_x = int(world_pos[0] // self.editor.grid_size)
        tile_y = int(world_pos[1] // self.editor.grid_size)

        current_layer = self.editor.layer_manager.get_current_layer()
        if not current_layer:
            return

        # Modo layers - apaga tile (coloca 0)
        if self.editor.mode == "layers":
            if 0 <= tile_x < current_layer.width and 0 <= tile_y < current_layer.height:
                # Verifica se realmente tem um tile para apagar
                if current_layer.get_tile(tile_x, tile_y) != 0:
                    # Salva estado ANTES da modificação
                    self._save_undo_state(f"Remover tile em ({tile_x}, {tile_y})")

                    self.editor.layer_manager.set_tile(tile_x, tile_y, 0)
                    print(f"Tile removido em ({tile_x}, {tile_y})")

        # Modo path - remove nó
        elif self.editor.mode == "path":
            current_path = self.editor.path_manager.get_current_path()
            if not current_path:
                return

            # Encontra nó mais próximo para remover
            min_dist = float('inf')
            node_to_remove = -1
            pos_to_remove = None

            for i, node in enumerate(current_path.nodes):
                dist = ((node[0] - world_pos[0]) ** 2 + (node[1] - world_pos[1]) ** 2) ** 0.5
                if dist < 20 and dist < min_dist:
                    min_dist = dist
                    node_to_remove = i
                    pos_to_remove = node

            if node_to_remove >= 0:
                # Salva estado ANTES da modificação
                self._save_undo_state(
                    f"Remover path node {node_to_remove} em ({pos_to_remove[0]:.0f}, {pos_to_remove[1]:.0f})")

                current_path.remove_node(node_to_remove)
                print(f"Nó {node_to_remove} removido do Path {self.editor.path_manager.current_path_index + 1}")

        # Modo towers - remove spot
        elif self.editor.mode == "towers":
            # Encontra spot mais próximo para remover
            spot_to_remove = None
            min_dist = float('inf')
            spot_pos = None

            for spot in self.editor.tower_spots.spots:
                center_x = spot.x + spot.size // 2
                center_y = spot.y + spot.size // 2
                dist = ((center_x - world_pos[0]) ** 2 + (center_y - world_pos[1]) ** 2) ** 0.5

                if dist < spot.size and dist < min_dist:
                    min_dist = dist
                    spot_to_remove = spot
                    spot_pos = (spot.x, spot.y)

            if spot_to_remove:
                # Salva estado ANTES da modificação
                self._save_undo_state(f"Remover tower spot em ({spot_pos[0]:.0f}, {spot_pos[1]:.0f})")

                self.editor.tower_spots.remove_spot(spot_to_remove)
                print("Spot de torre removido")