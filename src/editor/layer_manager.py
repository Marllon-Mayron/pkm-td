"""
Gerenciador de layers do mapa
"""
import pygame
import json
import os
from enum import Enum
from pathlib import Path

class LayerType(Enum):
    GROUND = "ground"        # Chão (fundo)
    DECORATION = "decoration" # Decorações (em cima do chão)
    CEILING = "ceiling"       # Teto/coisas para passar por baixo

class Layer:
    def __init__(self, name, layer_type, width, height, tile_size=16):
        self.name = name
        self.layer_type = layer_type
        self.width = width
        self.height = height
        self.tile_size = tile_size
        self.tiles = [[0 for _ in range(width)] for _ in range(height)]
        self.visible = True
        self.opacity = 255
        self.tileset_path = None
        self.tileset = []

    def set_tile(self, x, y, tile_id):
        if 0 <= x < self.width and 0 <= y < self.height:
            self.tiles[y][x] = tile_id
            return True
        return False

    def get_tile(self, x, y):
        if 0 <= x < self.width and 0 <= y < self.height:
            return self.tiles[y][x]
        return 0

    def load_tileset(self, image_path, tile_width, tile_height):
        """Carrega um tileset de uma imagem"""
        try:
            print(f"\n--- load_tileset ---")
            print(f"Tentando carregar: {image_path}")
            print(f"Arquivo existe? {os.path.exists(image_path)}")

            if not os.path.exists(image_path):
                print(f"ERRO: Arquivo não encontrado!")
                return False

            sheet = pygame.image.load(image_path).convert_alpha()
            print(f"Imagem carregada: {sheet.get_width()}x{sheet.get_height()}")

            sheet_width = sheet.get_width()
            sheet_height = sheet.get_height()

            cols = sheet_width // tile_width
            rows = sheet_height // tile_height
            print(f"Tilesheet dividida em {cols}x{rows} tiles")

            self.tileset = []
            for row in range(rows):
                for col in range(cols):
                    rect = pygame.Rect(col * tile_width, row * tile_height, tile_width, tile_height)
                    tile = sheet.subsurface(rect)
                    self.tileset.append(tile)

            print(f"Tileset carregado: {len(self.tileset)} tiles")

            # Converte para caminho relativo se for absoluto
            if os.path.isabs(image_path):
                try:
                    project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(__file__))))
                    relative_path = os.path.relpath(image_path, project_root)
                    self.tileset_path = relative_path.replace('\\', '/')
                    print(f"Caminho convertido para relativo: {self.tileset_path}")
                except:
                    self.tileset_path = os.path.basename(image_path)
            else:
                self.tileset_path = image_path

            return True

        except Exception as e:
            print(f"Erro ao carregar tileset: {e}")
            import traceback
            traceback.print_exc()
            return False


    def resize(self, new_width, new_height, default_tile=0):
        """
        Redimensiona a layer para novas dimensões

        """
        if new_width == self.width and new_height == self.height:
            return True

        print(f"Redimensionando layer '{self.name}' de {self.width}x{self.height} para {new_width}x{new_height}")

        # Cria nova matriz de tiles
        new_tiles = [[default_tile for _ in range(new_width)] for _ in range(new_height)]

        # Copia tiles existentes para a nova matriz
        for y in range(min(self.height, new_height)):
            for x in range(min(self.width, new_width)):
                new_tiles[y][x] = self.tiles[y][x]

        # Substitui a matriz antiga pela nova
        self.tiles = new_tiles
        self.width = new_width
        self.height = new_height

        return True

    def render(self, screen, camera, screen_manager):
        """Renderiza a layer com cálculos consistentes"""
        if not self.visible or not self.tileset:
            return

        # USA EXATAMENTE OS MESMOS CÁLCULOS QUE A GRID
        # Calcula offset da câmera (usando round para consistência)
        cam_offset_x = round((-camera.x * camera.zoom * screen_manager.render_scale +
                              (screen_manager.render_width / 2) * screen_manager.render_scale +
                              screen_manager.viewport_x))
        cam_offset_y = round((-camera.y * camera.zoom * screen_manager.render_scale +
                              (screen_manager.render_height / 2) * screen_manager.render_scale +
                              screen_manager.viewport_y))

        # Tamanho do tile escalado (usando round)
        tile_size_scaled = max(1, round(self.tile_size * camera.zoom * screen_manager.render_scale))

        # Calcula tiles visíveis baseado no offset (usando divisão inteira)
        start_x = max(0, (-cam_offset_x) // tile_size_scaled)
        start_y = max(0, (-cam_offset_y) // tile_size_scaled)
        end_x = min(self.width, start_x + (screen_manager.viewport_width // tile_size_scaled) + 2)
        end_y = min(self.height, start_y + (screen_manager.viewport_height // tile_size_scaled) + 2)

        # Renderiza tiles
        for y in range(start_y, end_y):
            for x in range(start_x, end_x):
                tile_id = self.tiles[y][x]
                if tile_id > 0 and tile_id - 1 < len(self.tileset):
                    # Posição na tela usando os mesmos valores cacheados
                    screen_x = x * tile_size_scaled + cam_offset_x
                    screen_y = y * tile_size_scaled + cam_offset_y

                    # Só renderiza se estiver dentro do viewport (otimização)
                    if (screen_x + tile_size_scaled > screen_manager.viewport_x and
                            screen_x < screen_manager.viewport_x + screen_manager.viewport_width and
                            screen_y + tile_size_scaled > screen_manager.viewport_y and
                            screen_y < screen_manager.viewport_y + screen_manager.viewport_height):

                        tile_img = self.tileset[tile_id - 1]

                        # Redimensiona se necessário
                        if (tile_img.get_width() != tile_size_scaled or
                                tile_img.get_height() != tile_size_scaled):
                            scaled_tile = pygame.transform.scale(
                                tile_img,
                                (tile_size_scaled, tile_size_scaled)
                            )
                            scaled_tile.set_alpha(self.opacity)
                            screen.blit(scaled_tile, (screen_x, screen_y))
                        else:
                            tile_img.set_alpha(self.opacity)
                            screen.blit(tile_img, (screen_x, screen_y))

class LayerManager:
    def __init__(self):
        self.layers = []
        self.current_layer = 0
        self.width = 100
        self.height = 100
        self.tile_size = 16

    def add_layer(self, name, layer_type):
        layer = Layer(name, layer_type, self.width, self.height, self.tile_size)
        self.layers.append(layer)
        return layer

    def remove_layer(self, index):
        if 0 <= index < len(self.layers):
            del self.layers[index]
            if self.current_layer >= len(self.layers):
                self.current_layer = max(0, len(self.layers) - 1)

    def resize_all_layers(self, new_width, new_height, default_tile=0):
        """
        Redimensiona todas as layers para as novas dimensões

        Args:
            new_width: nova largura em tiles
            new_height: nova altura em tiles
            default_tile: tile padrão para preencher novas áreas
        """
        if new_width == self.width and new_height == self.height:
            return True

        print(f"Redimensionando todas as layers de {self.width}x{self.height} para {new_width}x{new_height}")

        for layer in self.layers:
            layer.resize(new_width, new_height, default_tile)

        # Atualiza as dimensões do gerenciador
        self.width = new_width
        self.height = new_height

        print(f"Todas as layers redimensionadas com sucesso")
        return True

    def get_current_layer(self):
        if 0 <= self.current_layer < len(self.layers):
            return self.layers[self.current_layer]
        return None

    def set_tile(self, x, y, tile_id):
        layer = self.get_current_layer()
        if layer:
            return layer.set_tile(x, y, tile_id)
        return False

    def get_tile(self, x, y, layer_index=None):
        if layer_index is None:
            layer_index = self.current_layer
        if 0 <= layer_index < len(self.layers):
            return self.layers[layer_index].get_tile(x, y)
        return 0

    def render_all(self, screen, camera, screen_manager):
        """Renderiza todas as layers passando o screen_manager"""
        # Renderiza na ordem correta
        for layer in self.layers:
            if layer.layer_type == LayerType.GROUND:
                layer.render(screen, camera, screen_manager)

        for layer in self.layers:
            if layer.layer_type == LayerType.DECORATION:
                layer.render(screen, camera, screen_manager)

        for layer in self.layers:
            if layer.layer_type == LayerType.CEILING:
                layer.render(screen, camera, screen_manager)

    def to_dict(self):
        """Converte para dicionário para salvar em JSON"""
        # Calcula o tamanho máximo entre todas as layers
        max_width = 0
        max_height = 0

        for layer in self.layers:
            max_width = max(max_width, layer.width)
            max_height = max(max_height, layer.height)

        return {
            "width": max_width,  # Salva o tamanho máximo real
            "height": max_height,
            "tile_size": self.tile_size,
            "layers": [
                {
                    "name": layer.name,
                    "type": layer.layer_type.value,
                    "tiles": layer.tiles,
                    "tileset_path": layer.tileset_path,
                    "width": layer.width,  # Salva o tamanho individual de cada layer
                    "height": layer.height
                }
                for layer in self.layers
            ]
        }

    def from_dict(self, data, base_path=""):
        """Carrega do dicionário"""
        print("\n=== INÍCIO do from_dict ===")
        print(f"Base path recebido: {base_path}")
        print(f"Data keys: {data.keys()}")

        self.width = data.get("width", 100)
        self.height = data.get("height", 100)
        self.tile_size = data.get("tile_size", 16)
        self.layers = []

        for layer_idx, layer_data in enumerate(data["layers"]):
            print(f"\n--- Processando layer {layer_idx}: {layer_data['name']} ---")

            layer_width = layer_data.get("width", self.width)
            layer_height = layer_data.get("height", self.height)
            print(f"Dimensões: {layer_width}x{layer_height}")

            # Obtém os tiles
            loaded_tiles = layer_data["tiles"]
            print(f"Tiles recebidos: {len(loaded_tiles)} linhas")
            if loaded_tiles:
                print(f"Primeira linha tem {len(loaded_tiles[0])} colunas")

            # Cria a layer
            layer = Layer(
                layer_data["name"],
                LayerType(layer_data["type"]),
                layer_width,
                layer_height,
                self.tile_size
            )

            # COPIA OS TILES
            for y in range(layer_height):
                for x in range(layer_width):
                    if y < len(loaded_tiles) and x < len(loaded_tiles[y]):
                        layer.tiles[y][x] = loaded_tiles[y][x]
                    else:
                        layer.tiles[y][x] = 0

            # Carrega tileset se existir
            if layer_data.get("tileset_path"):
                layer.tileset_path = layer_data["tileset_path"]
                print(f"Tileset path do JSON: {layer.tileset_path}")

                # Lista de possíveis caminhos para procurar
                possible_paths = []
                basename = os.path.basename(layer.tileset_path)

                # 1. Se base_path foi fornecido, tenta com ele
                if base_path:
                    # Remove qualquer "pokemon-tower-defense" duplicado
                    clean_path = layer.tileset_path
                    if clean_path.startswith('pokemon-tower-defense/'):
                        clean_path = clean_path[len('pokemon-tower-defense/'):]
                    if clean_path.startswith('pokemon-tower-defense\\'):
                        clean_path = clean_path[len('pokemon-tower-defense\\'):]

                    full_path = os.path.join(base_path, clean_path)
                    possible_paths.append(full_path)
                    print(f"Path com base_path: {full_path}")

                # 2. Caminho direto na raiz do projeto
                root_path = os.path.join("res", "AllTiles", basename)
                possible_paths.append(root_path)
                print(f"Path res/AllTiles: {root_path}")

                # 3. Caminho com base_path + res/AllTiles
                if base_path:
                    res_path = os.path.join(base_path, "res", "AllTiles", basename)
                    possible_paths.append(res_path)
                    print(f"Path base_path + res/AllTiles: {res_path}")

                # 4. Apenas o nome do arquivo no diretório atual
                possible_paths.append(basename)
                print(f"Path apenas nome: {basename}")

                # Tenta cada caminho
                loaded = False
                for path in possible_paths:
                    normalized = os.path.normpath(path)
                    print(f"  Verificando: {normalized}")
                    print(f"    Existe? {os.path.exists(normalized)}")

                    if os.path.exists(normalized):
                        print(f"  ✓ ENCONTRADO: {normalized}")
                        success = layer.load_tileset(normalized, self.tile_size, self.tile_size)
                        if success:
                            print(f"  ✓ Tileset carregado com {len(layer.tileset)} tiles")
                            loaded = True
                            break
                        else:
                            print(f"  ✗ Falha ao carregar tileset")

                if not loaded:
                    print(f"  ✗ NENHUM CAMINHO FUNCIONOU para {layer.tileset_path}")
                    print("  Usando tileset vazio")
            else:
                print("  Sem tileset_path")

            self.layers.append(layer)
            print(f"Layer adicionada. Total layers: {len(self.layers)}")

        print("\n=== FIM do from_dict ===")
        return self