# src/scenes/editor/handlers/map_handler.py

import pygame


class MapHandler:
    """Gerencia as operações de edição do mapa"""

    def __init__(self, editor_scene):
        self.editor = editor_scene

    def handle_left_click(self, world_pos):
        """Processa clique esquerdo no mapa"""
        # Converte posição mundial para coordenadas de tile
        tile_x = int(world_pos[0] // self.editor.grid_size)
        tile_y = int(world_pos[1] // self.editor.grid_size)

        current_layer = self.editor.layer_manager.get_current_layer()
        if not current_layer:
            return

        # Modo layers - desenha tile
        if self.editor.mode == "layers":
            if 0 <= tile_x < current_layer.width and 0 <= tile_y < current_layer.height:
                self.editor.layer_manager.set_tile(tile_x, tile_y, self.editor.current_tile)
                print(f"Tile {self.editor.current_tile} colocado em ({tile_x}, {tile_y})")

        # Modo path - adiciona nó
        elif self.editor.mode == "path":
            # Ajusta para grid se necessário
            if self.editor.snap_to_grid:
                x = tile_x * self.editor.grid_size + self.editor.grid_size // 2
                y = tile_y * self.editor.grid_size + self.editor.grid_size // 2
            else:
                x, y = world_pos

            self.editor.path.add_node((x, y))
            print(f"Nó do path adicionado em ({x}, {y})")
            self.editor._update_preview_objects()

        # Modo towers - adiciona spot
        elif self.editor.mode == "towers":
            # Ajusta para grid se necessário
            if self.editor.snap_to_grid:
                x = tile_x * self.editor.grid_size
                y = tile_y * self.editor.grid_size
            else:
                x = world_pos[0] - 16  # Centraliza no clique
                y = world_pos[1] - 16

            # Verifica se já existe spot nesta posição
            existing_spot = self.editor.tower_spots.get_spot_at(x + 8, y + 8)  # +8 para pegar o centro
            if existing_spot:
                print(f"Já existe um spot em ({x}, {y})")
            else:
                self.editor.tower_spots.add_spot(x, y)
                self.editor._update_preview_objects()

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
                self.editor.layer_manager.set_tile(tile_x, tile_y, 0)
                print(f"Tile removido em ({tile_x}, {tile_y})")

        # Modo path - remove nó (se clicar perto)
        elif self.editor.mode == "path":
            # Encontra nó mais próximo para remover
            min_dist = float('inf')
            node_to_remove = -1

            for i, node in enumerate(self.editor.path.nodes):
                dist = ((node[0] - world_pos[0]) ** 2 + (node[1] - world_pos[1]) ** 2) ** 0.5
                if dist < 20 and dist < min_dist:  # 20 pixels de tolerância
                    min_dist = dist
                    node_to_remove = i

            if node_to_remove >= 0:
                self.editor.path.remove_node(node_to_remove)
                print(f"Nó {node_to_remove} removido")
                self.editor._update_preview_objects()

        # Modo towers - remove spot
        elif self.editor.mode == "towers":
            # Encontra spot mais próximo para remover
            spot_to_remove = None
            min_dist = float('inf')

            for spot in self.editor.tower_spots.spots:
                # Calcula centro do spot
                center_x = spot.x + spot.size // 2
                center_y = spot.y + spot.size // 2
                dist = ((center_x - world_pos[0]) ** 2 + (center_y - world_pos[1]) ** 2) ** 0.5

                if dist < spot.size and dist < min_dist:
                    min_dist = dist
                    spot_to_remove = spot

            if spot_to_remove:
                # CORREÇÃO: Agora passa o objeto spot, não o índice
                self.editor.tower_spots.remove_spot(spot_to_remove)
                print("Spot de torre removido")
                self.editor._update_preview_objects()