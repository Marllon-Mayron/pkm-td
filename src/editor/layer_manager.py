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
            sheet = pygame.image.load(image_path).convert_alpha()
            sheet_width = sheet.get_width()
            sheet_height = sheet.get_height()

            cols = sheet_width // tile_width
            rows = sheet_height // tile_height

            self.tileset = []
            for row in range(rows):
                for col in range(cols):
                    rect = pygame.Rect(col * tile_width, row * tile_height, tile_width, tile_height)
                    tile = sheet.subsurface(rect)
                    self.tileset.append(tile)

            self.tileset_path = image_path
            print(f"Tileset carregado: {len(self.tileset)} tiles de {tile_width}x{tile_height}")
            return True
        except Exception as e:
            print(f"Erro ao carregar tileset: {e}")
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
        """Renderiza a layer com cálculos inteiros para evitar gaps"""
        if not self.visible or not self.tileset:
            return

        visible_rect = camera.get_visible_rect()

        start_x = max(0, int(visible_rect.left // self.tile_size))
        start_y = max(0, int(visible_rect.top // self.tile_size))
        end_x = min(self.width, int(visible_rect.right // self.tile_size) + 1)
        end_y = min(self.height, int(visible_rect.bottom // self.tile_size) + 1)

        # PRÉ-CALCULA usando inteiros
        cam_offset_x = int(-camera.x * camera.zoom * screen_manager.render_scale +
                           (screen_manager.render_width / 2) * screen_manager.render_scale +
                           screen_manager.viewport_x)
        cam_offset_y = int(-camera.y * camera.zoom * screen_manager.render_scale +
                           (screen_manager.render_height / 2) * screen_manager.render_scale +
                           screen_manager.viewport_y)

        tile_size_scaled = int(self.tile_size * camera.zoom * screen_manager.render_scale)

        for y in range(start_y, end_y):
            for x in range(start_x, end_x):
                tile_id = self.tiles[y][x]
                if tile_id > 0 and tile_id - 1 < len(self.tileset):
                    # Posição na tela com INT para evitar gaps
                    screen_x = x * tile_size_scaled + cam_offset_x
                    screen_y = y * tile_size_scaled + cam_offset_y

                    tile_img = self.tileset[tile_id - 1]

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
        # Usa o tamanho máximo salvo
        self.width = data.get("width", 100)  # fallback para 100 se não existir
        self.height = data.get("height", 100)
        self.tile_size = data.get("tile_size", 16)
        self.layers = []

        for layer_data in data["layers"]:
            # Verifica se a layer tem tamanho próprio salvo, senão usa o global
            layer_width = layer_data.get("width", self.width)
            layer_height = layer_data.get("height", self.height)

            # Obtém os tiles
            loaded_tiles = layer_data["tiles"]

            # Cria a layer com as dimensões corretas
            layer = Layer(
                layer_data["name"],
                LayerType(layer_data["type"]),
                layer_width,
                layer_height,
                self.tile_size
            )

            # Copia os tiles, garantindo que as dimensões correspondam
            for y in range(min(len(loaded_tiles), layer_height)):
                for x in range(min(len(loaded_tiles[y]), layer_width)):
                    if y < layer_height and x < layer_width:
                        layer.tiles[y][x] = loaded_tiles[y][x]

            if layer_data.get("tileset_path"):
                tileset_path = os.path.join(base_path, layer_data["tileset_path"])
                if os.path.exists(tileset_path):
                    layer.load_tileset(tileset_path, self.tile_size, self.tile_size)

            self.layers.append(layer)