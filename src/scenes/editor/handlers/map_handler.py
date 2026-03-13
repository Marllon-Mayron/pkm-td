import pygame


class MapHandler:
    """Gerencia operações relacionadas ao mapa"""

    def __init__(self, editor_scene):
        self.editor = editor_scene

    def handle_left_click(self, world_pos):
        """Processa clique esquerdo no mapa"""
        x, y = world_pos

        if self.editor.mode == "layers":
            self._handle_layer_click(x, y)
        elif self.editor.mode == "path":
            # SNAP TO GRID: alinha a posição ao grid de 16x16
            grid_x = round(x / self.editor.grid_size) * self.editor.grid_size
            grid_y = round(y / self.editor.grid_size) * self.editor.grid_size
            self.editor.path.add_node(grid_x, grid_y)
            print(f"Nó do path adicionado em ({grid_x}, {grid_y})")
        elif self.editor.mode == "towers":
            # Torres também podem ser alinhadas ao grid? Se sim, descomente as linhas abaixo
            # grid_x = round(x / self.editor.grid_size) * self.editor.grid_size
            # grid_y = round(y / self.editor.grid_size) * self.editor.grid_size
            # self.editor.tower_spots.add_spot(grid_x, grid_y)
            self.editor.tower_spots.add_spot(x, y)

    def handle_right_click(self, world_pos):
        """Processa clique direito no mapa"""
        x, y = world_pos

        if self.editor.mode == "layers":
            self._handle_layer_right_click(x, y)
        elif self.editor.mode == "path":
            # Para remoção, também precisamos buscar o nó mais próximo considerando o grid
            node_idx = self.editor.path.get_node_at(x, y)
            if node_idx >= 0:
                self.editor.path.remove_node(node_idx)
                print(f"Nó {node_idx} removido")
        elif self.editor.mode == "towers":
            spot_idx = self.editor.tower_spots.get_spot_at(x, y)
            if spot_idx >= 0:
                self.editor.tower_spots.remove_spot(spot_idx)
                print(f"Spot {spot_idx} removido")

    def _handle_layer_click(self, x, y):
        """Processa clique em modo layers"""
        grid_x = int(x // self.editor.grid_size)
        grid_y = int(y // self.editor.grid_size)

        current_layer = self.editor.layer_manager.get_current_layer()
        if not current_layer:
            return

        # Verifica limites
        if (
                self.editor.min_world_x // self.editor.grid_size <= grid_x < self.editor.max_world_x // self.editor.grid_size and
                self.editor.min_world_y // self.editor.grid_size <= grid_y < self.editor.max_world_y // self.editor.grid_size):

            # Expande layer se necessário
            if grid_x < 0 or grid_x >= current_layer.width or grid_y < 0 or grid_y >= current_layer.height:
                self._expand_layer_to_include(grid_x, grid_y)
                # Após expandir, atualiza a referência da layer
                current_layer = self.editor.layer_manager.get_current_layer()

            # Coloca o tile
            if 0 <= grid_x < current_layer.width and 0 <= grid_y < current_layer.height:
                success = self.editor.layer_manager.set_tile(grid_x, grid_y, self.editor.current_tile)
                if success:
                    print(f"Tile {self.editor.current_tile} colocado em ({grid_x}, {grid_y})")

    def _handle_layer_right_click(self, x, y):
        """Processa clique direito em modo layers"""
        grid_x = int(x // self.editor.grid_size)
        grid_y = int(y // self.editor.grid_size)

        current_layer = self.editor.layer_manager.get_current_layer()
        if current_layer and 0 <= grid_x < current_layer.width and 0 <= grid_y < current_layer.height:
            self.editor.layer_manager.set_tile(grid_x, grid_y, 0)
            print(f"Tile removido em ({grid_x}, {grid_y})")

    def _expand_layer_to_include(self, grid_x, grid_y):
        """Expande a layer para incluir coordenadas negativas ou além dos limites"""
        current_layer = self.editor.layer_manager.get_current_layer()
        if not current_layer:
            return

        # Calcula novos limites
        new_min_x = min(0, grid_x)
        new_min_y = min(0, grid_y)
        new_max_x = max(current_layer.width - 1, grid_x)
        new_max_y = max(current_layer.height - 1, grid_y)

        new_width = new_max_x - new_min_x + 1
        new_height = new_max_y - new_min_y + 1

        # Cria nova matriz com offset
        new_tiles = [[0 for _ in range(new_width)] for _ in range(new_height)]

        # Copia tiles existentes para a nova posição com offset
        offset_x = -new_min_x
        offset_y = -new_min_y

        for y in range(current_layer.height):
            for x in range(current_layer.width):
                new_x = x + offset_x
                new_y = y + offset_y
                if 0 <= new_x < new_width and 0 <= new_y < new_height:
                    new_tiles[new_y][new_x] = current_layer.tiles[y][x]

        # Atualiza a layer
        current_layer.tiles = new_tiles
        current_layer.width = new_width
        current_layer.height = new_height

        # Atualiza os limites do mundo
        self.editor.min_world_x = min(self.editor.min_world_x, new_min_x * self.editor.grid_size)
        self.editor.min_world_y = min(self.editor.min_world_y, new_min_y * self.editor.grid_size)
        self.editor.max_world_x = max(self.editor.max_world_x,
                                      new_max_x * self.editor.grid_size + self.editor.grid_size)
        self.editor.max_world_y = max(self.editor.max_world_y,
                                      new_max_y * self.editor.grid_size + self.editor.grid_size)

        # Atualiza limites da câmera
        self.editor.camera.set_limits(self.editor.min_world_x, self.editor.max_world_x,
                                      self.editor.min_world_y, self.editor.max_world_y)

        print(f"Layer expandida: novo tamanho {new_width}x{new_height}, offset ({offset_x}, {offset_y})")

    def resize_map(self, new_width, new_height):
        """Redimensiona todas as layers do mapa"""
        print(f"Redimensionando mapa para {new_width}x{new_height} tiles")

        for layer in self.editor.layer_manager.layers:
            # Cria nova matriz de tiles
            new_tiles = [[0 for _ in range(new_width)] for _ in range(new_height)]

            # Copia tiles existentes para a nova matriz
            for y in range(min(layer.height, new_height)):
                for x in range(min(layer.width, new_width)):
                    if y < len(layer.tiles) and x < len(layer.tiles[y]):
                        new_tiles[y][x] = layer.tiles[y][x]

            # Atualiza a layer
            layer.tiles = new_tiles
            layer.width = new_width
            layer.height = new_height

        # Atualiza as dimensões do mundo
        self.editor.world_width = new_width * self.editor.grid_size
        self.editor.world_height = new_height * self.editor.grid_size

        # Atualiza a câmera
        self.editor.game.initialize_camera(self.editor.world_width, self.editor.world_height)
        self.editor.camera = self.editor.game.camera

        # Atualiza limites da câmera
        self.editor.camera.set_limits(self.editor.min_world_x, self.editor.max_world_x,
                                      self.editor.min_world_y, self.editor.max_world_y)

        print(f"Mapa redimensionado para {new_width}x{new_height} tiles")