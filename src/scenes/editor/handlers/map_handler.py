# src/scenes/editor/handlers/map_handler.py

import pygame
from collections import deque


class MapHandler:
    def __init__(self, editor_scene):
        self.editor = editor_scene
        self.last_undo_tile = None
        self.last_undo_erase_tile = None
        self.last_undo_time = 0
        self.last_erase_time = 0
        self.undo_cooldown = 0.2

    def _get_current_tile_int(self):
        """Obtém o tile atual garantindo que seja inteiro"""
        try:
            return int(self.editor.current_tile)
        except (ValueError, TypeError):
            return 1  # Valor padrão se não conseguir converter

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

    def _flood_fill(self, layer, start_x, start_y, new_tile_id):
        """
        Algoritmo de preenchimento por inundação (flood fill)

        Args:
            layer: A layer a ser preenchida
            start_x, start_y: Posição inicial em tiles
            new_tile_id: ID do novo tile a ser colocado

        Returns:
            int: Número de tiles alterados
        """
        # Garante que new_tile_id seja inteiro
        try:
            new_tile_id = int(new_tile_id)
        except (ValueError, TypeError):
            print(f"DEBUG FloodFill: new_tile_id inválido: {new_tile_id}, usando 0")
            new_tile_id = 0

        # Verifica se a posição inicial é válida
        if not (0 <= start_x < layer.width and 0 <= start_y < layer.height):
            print(f"DEBUG FloodFill: Posição inválida ({start_x}, {start_y})")
            return 0

        target_tile = layer.get_tile(start_x, start_y)

        print(f"DEBUG FloodFill: Iniciando em ({start_x}, {start_y})")
        print(f"DEBUG FloodFill: target_tile = {target_tile}, new_tile_id = {new_tile_id}")

        # Se o tile de destino já é o novo tile, não faz nada
        if target_tile == new_tile_id:
            print(f"DEBUG FloodFill: target_tile já é {new_tile_id}, nada a fazer")
            return 0

        # Fila para processar os tiles (BFS - Breadth First Search)
        queue = deque()
        queue.append((start_x, start_y))

        # Conjunto para marcar tiles já processados
        processed = set()
        processed.add((start_x, start_y))

        count = 0

        while queue:
            x, y = queue.popleft()

            # Pinta o tile atual
            old_tile = layer.get_tile(x, y)
            layer.set_tile(x, y, new_tile_id)
            count += 1
            print(f"DEBUG FloodFill: Alterado ({x}, {y}) de {old_tile} para {new_tile_id}")

            # Verifica os 4 vizinhos (cima, baixo, esquerda, direita)
            neighbors = [
                (x + 1, y), (x - 1, y),
                (x, y + 1), (x, y - 1)
            ]

            for nx, ny in neighbors:
                # Verifica se está dentro dos limites
                if 0 <= nx < layer.width and 0 <= ny < layer.height:
                    # Se ainda não foi processado e é do tipo alvo
                    if (nx, ny) not in processed:
                        current_tile = layer.get_tile(nx, ny)
                        if current_tile == target_tile:
                            print(f"DEBUG FloodFill: Adicionando vizinho ({nx}, {ny}) = {current_tile}")
                            queue.append((nx, ny))
                            processed.add((nx, ny))
                        else:
                            print(f"DEBUG FloodFill: Vizinho ({nx}, {ny}) = {current_tile} != {target_tile}, ignorando")

        print(f"DEBUG FloodFill: Finalizado. Total alterado: {count} tiles")
        return count

    def handle_left_click(self, world_pos, continuous=False):
        """Processa clique esquerdo no mapa"""
        tile_x = int(world_pos[0] // self.editor.grid_size)
        tile_y = int(world_pos[1] // self.editor.grid_size)
        current_tile_pos = (tile_x, tile_y)

        current_layer = self.editor.layer_manager.get_current_layer()
        if not current_layer:
            return

        # Obtém o tile atual como inteiro
        current_tile_int = self._get_current_tile_int()

        # Modo layers - desenha tile
        if self.editor.mode == "layers":
            if 0 <= tile_x < current_layer.width and 0 <= tile_y < current_layer.height:

                # Obtém o brush atual
                current_brush = self.editor.brush_buttons.get_current_brush()

                # PINCEL (desenho normal)
                if current_brush == self.editor.brush_buttons.BRUSH_PENCIL:
                    # Verifica se o tile já é o que queremos colocar
                    current_tile_value = current_layer.get_tile(tile_x, tile_y)

                    # Só faz algo se for um tile diferente
                    if current_tile_value != current_tile_int:
                        should_save_undo = True

                        if continuous:
                            if current_tile_pos == self.last_undo_tile:
                                should_save_undo = False
                            else:
                                self.last_undo_tile = current_tile_pos

                        if should_save_undo:
                            self._save_undo_state(
                                f"Tile {current_tile_int} em ({tile_x}, {tile_y})",
                                continuous
                            )

                        self.editor.layer_manager.set_tile(tile_x, tile_y, current_tile_int)
                        print(f"Tile {current_tile_int} colocado em ({tile_x}, {tile_y})")

                # BALDE (preenchimento) - clique esquerdo
                elif current_brush == self.editor.brush_buttons.BRUSH_BUCKET and not continuous:
                    # Balde só funciona em clique único

                    # Verifica se o tile clicado já é o que queremos colocar
                    target_tile = current_layer.get_tile(tile_x, tile_y)

                    print(f"DEBUG Balde Esquerdo: Clicou em tile ({tile_x}, {tile_y}) = {target_tile}")

                    if target_tile != current_tile_int:  # Só preenche se for diferente
                        # Salva estado ANTES da modificação
                        self._save_undo_state(
                            f"Preenchimento em ({tile_x}, {tile_y}) com tile {current_tile_int}"
                        )

                        print(f"DEBUG Balde Esquerdo: Chamando flood fill para preencher com tile {current_tile_int}")

                        # Executa o flood fill
                        count = self._flood_fill(
                            current_layer,
                            tile_x, tile_y,
                            current_tile_int
                        )

                        print(f"Balde (esquerdo): {count} tiles preenchidos em ({tile_x}, {tile_y})")
                    else:
                        print(f"Balde (esquerdo): Tile já é o selecionado, nada a fazer")

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
        current_tile_pos = (tile_x, tile_y)

        # Verifica se o editor tem layer_manager
        if not hasattr(self.editor, 'layer_manager'):
            return

        current_layer = self.editor.layer_manager.get_current_layer()
        if not current_layer:
            return

        # Detecta se é contínuo baseado no estado do input_handler
        continuous = False
        if hasattr(self.editor, 'input_handler'):
            continuous = getattr(self.editor.input_handler, 'erasing', False)

        # Obtém o brush atual
        if not hasattr(self.editor, 'brush_buttons'):
            return

        current_brush = self.editor.brush_buttons.get_current_brush()

        # Modo layers - apaga tile
        if self.editor.mode == "layers":
            # BALDE - Verifica se é brush BALDE (ignora continuous para o balde)
            if current_brush == self.editor.brush_buttons.BRUSH_BUCKET:
                # Verifica se a posição clicada está dentro dos limites
                if 0 <= tile_x < current_layer.width and 0 <= tile_y < current_layer.height:

                    # Verifica se tem algo para apagar
                    target_tile = current_layer.get_tile(tile_x, tile_y)

                    if target_tile != 0:  # Só apaga se não for vazio
                        # Salva estado ANTES da modificação
                        self._save_undo_state(
                            f"Remover área de tile {target_tile} em ({tile_x}, {tile_y})"
                        )

                        # Executa flood fill com tile 0 (vazio)
                        count = self._flood_fill(
                            current_layer,
                            tile_x, tile_y,
                            0  # Tile 0 = vazio
                        )

                        print(f"Balde (direito): {count} tiles removidos em ({tile_x}, {tile_y})")

                    else:
                        print(f"Balde (direito): Tile em ({tile_x}, {tile_y}) já está vazio")
                else:
                    print(f"Balde (direito): Clique FORA dos limites do mapa em ({tile_x}, {tile_y})")

                return  # IMPORTANTE: Retorna após processar o balde

            # PINCEL - usa a lógica com continuous
            elif current_brush == self.editor.brush_buttons.BRUSH_PENCIL:

                # Verifica limites para o pincel
                if not (0 <= tile_x < current_layer.width and 0 <= tile_y < current_layer.height):
                    print("DEBUG MapHandler: Posição fora dos limites, ignorando PINCEL")
                    return

                if current_layer.get_tile(tile_x, tile_y) != 0:
                    should_save_undo = True

                    if continuous:
                        current_time = pygame.time.get_ticks() / 1000.0
                        if current_tile_pos == self.last_undo_erase_tile:
                            should_save_undo = False
                        else:
                            self.last_undo_erase_tile = current_tile_pos
                            self.last_erase_time = current_time

                    if should_save_undo:
                        self._save_undo_state(f"Remover tile em ({tile_x}, {tile_y})", continuous)

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
                self._save_undo_state(
                    f"Remover path node {node_to_remove} em ({pos_to_remove[0]:.0f}, {pos_to_remove[1]:.0f})")
                current_path.remove_node(node_to_remove)
                print(f"Nó {node_to_remove} removido do Path {self.editor.path_manager.current_path_index + 1}")

        # Modo towers - remove spot
        elif self.editor.mode == "towers":
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
                self._save_undo_state(f"Remover tower spot em ({spot_pos[0]:.0f}, {spot_pos[1]:.0f})")
                self.editor.tower_spots.remove_spot(spot_to_remove)
                print("Spot de torre removido")