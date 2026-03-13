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

    def render(self, screen, camera, screen_manager, offset_x=0, offset_y=0):
        if not self.visible or not self.tileset:
            return

        visible_rect = camera.get_visible_rect()
        start_x = max(0, int(visible_rect.left // self.tile_size))
        start_y = max(0, int(visible_rect.top // self.tile_size))
        end_x = min(self.width, int(visible_rect.right // self.tile_size) + 1)
        end_y = min(self.height, int(visible_rect.bottom // self.tile_size) + 1)

        # Calcula offset da câmera
        cam_offset_x = -camera.x * camera.zoom + screen_manager.render_width / 2
        cam_offset_y = -camera.y * camera.zoom + screen_manager.render_height / 2

        for y in range(start_y, end_y):
            for x in range(start_x, end_x):
                tile_id = self.tiles[y][x]
                if tile_id > 0 and tile_id - 1 < len(self.tileset):
                    # Calcula posição no mundo
                    world_x = x * self.tile_size + offset_x
                    world_y = y * self.tile_size + offset_y

                    # Calcula posição na superfície de renderização
                    render_x = world_x * camera.zoom + cam_offset_x
                    render_y = world_y * camera.zoom + cam_offset_y

                    # IMPORTANTE: Converte para tela usando o ScreenManager
                    screen_x, screen_y = screen_manager.get_screen_position(render_x, render_y)

                    # Tamanho do tile na tela (considerando zoom E escala da tela)
                    tile_size_scaled = int(self.tile_size * camera.zoom * screen_manager.render_scale)

                    # Renderiza o tile
                    tile_img = self.tileset[tile_id - 1]

                    # Só escala se necessário
                    if tile_img.get_width() != tile_size_scaled:
                        scaled_tile = pygame.transform.scale(tile_img, (tile_size_scaled, tile_size_scaled))
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
        return {
            "width": self.width,
            "height": self.height,
            "tile_size": self.tile_size,
            "layers": [
                {
                    "name": layer.name,
                    "type": layer.layer_type.value,
                    "tiles": layer.tiles,
                    "tileset_path": layer.tileset_path
                }
                for layer in self.layers
            ]
        }

    def from_dict(self, data, base_path=""):
        """Carrega do dicionário"""
        self.width = data["width"]
        self.height = data["height"]
        self.tile_size = data["tile_size"]
        self.layers = []

        for layer_data in data["layers"]:
            layer = Layer(
                layer_data["name"],
                LayerType(layer_data["type"]),
                self.width,
                self.height,
                self.tile_size
            )
            layer.tiles = layer_data["tiles"]

            if layer_data.get("tileset_path"):
                tileset_path = os.path.join(base_path, layer_data["tileset_path"])
                if os.path.exists(tileset_path):
                    layer.load_tileset(tileset_path, self.tile_size, self.tile_size)

            self.layers.append(layer)