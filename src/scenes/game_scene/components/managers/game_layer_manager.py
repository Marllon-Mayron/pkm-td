# src/scenes/game_scene/components/renderer/game_layer_manager.py

"""
Gerenciador de camadas para o jogo - SEM GAPS
"""
import pygame
from src.core.render_context import render_context


class GameLayer:
    """Camada do mapa para o jogo"""

    def __init__(self, name, layer_type, width, height, tile_size=16):
        self.name = name
        self.layer_type = layer_type
        self.width = width
        self.height = height
        self.tile_size = tile_size
        self.tiles = [[0 for _ in range(width)] for _ in range(height)]
        self.visible = True
        self.opacity = 255
        self.tileset = []
        self._cached_tiles = {}
        self._last_scale = None

    def set_tile(self, x, y, tile_id):
        if 0 <= x < self.width and 0 <= y < self.height:
            self.tiles[y][x] = int(tile_id)
            return True
        return False

    def get_tile(self, x, y):
        if 0 <= x < self.width and 0 <= y < self.height:
            return self.tiles[y][x]
        return 0

    def load_tileset(self, image_path, tile_width, tile_height):
        """Carrega tileset de uma imagem"""
        try:
            sheet = pygame.image.load(image_path).convert_alpha()
            cols = sheet.get_width() // tile_width
            rows = sheet.get_height() // tile_height

            self.tileset = []
            for row in range(rows):
                for col in range(cols):
                    rect = pygame.Rect(col * tile_width, row * tile_height,
                                       tile_width, tile_height)
                    tile = sheet.subsurface(rect)
                    self.tileset.append(tile)
            return True
        except Exception as e:
            print(f"Erro ao carregar tileset: {e}")
            return False

    def _get_scaled_tile(self, tile_index, target_size):
        """Obtém tile escalado do cache"""
        cache_key = (tile_index, target_size)
        if cache_key not in self._cached_tiles:
            original = self.tileset[tile_index]
            # Adiciona 1 pixel extra para evitar gaps
            scaled = pygame.transform.scale(original, (target_size + 1, target_size + 1))
            self._cached_tiles[cache_key] = scaled
        return self._cached_tiles[cache_key]

    def render(self, screen, camera, screen_manager):
        """Renderiza a camada - SEM GAPS (com sobreposição)"""
        if not self.visible or not self.tileset:
            return

        scale = render_context.get_scale(camera, screen_manager)
        tile_size_scaled = max(1, int(self.tile_size * scale))
        # Adiciona 1 pixel extra para sobreposição e evitar gaps
        tile_size_render = tile_size_scaled + 1

        visible_rect = camera.get_visible_rect()
        start_x = max(0, int(visible_rect.x // self.tile_size) - 1)
        start_y = max(0, int(visible_rect.y // self.tile_size) - 1)
        end_x = min(self.width, int((visible_rect.x + visible_rect.width) // self.tile_size) + 2)
        end_y = min(self.height, int((visible_rect.y + visible_rect.height) // self.tile_size) + 2)

        for y in range(start_y, end_y):
            for x in range(start_x, end_x):
                tile_id = self.tiles[y][x]

                try:
                    tile_index = int(tile_id) - 1
                except (ValueError, TypeError):
                    tile_index = -1

                if 0 <= tile_index < len(self.tileset):
                    world_x = x * self.tile_size
                    world_y = y * self.tile_size

                    # Usa float para posição
                    screen_x, screen_y = render_context.world_to_screen(
                        world_x, world_y, camera, screen_manager
                    )

                    tile_img = self._get_scaled_tile(tile_index, tile_size_render)
                    screen.blit(tile_img, (int(screen_x), int(screen_y)))


class GameLayerManager:
    """Gerenciador de camadas para o jogo"""

    def __init__(self):
        self.layers = []
        self.width = 100
        self.height = 100
        self.tile_size = 16

    def add_layer(self, name, layer_type):
        layer = GameLayer(name, layer_type, self.width, self.height, self.tile_size)
        self.layers.append(layer)
        return layer

    def load_from_dict(self, data, base_path=""):
        """Carrega do dicionário"""
        print("\n=== Carregando GameLayerManager ===")

        self.width = data.get("width", 100)
        self.height = data.get("height", 100)
        self.tile_size = data.get("tile_size", 16)
        self.layers = []

        for layer_data in data.get("layers", []):
            layer_width = layer_data.get("width", self.width)
            layer_height = layer_data.get("height", self.height)

            layer = GameLayer(
                layer_data["name"],
                layer_data["type"],
                layer_width,
                layer_height,
                self.tile_size
            )

            # Carrega os tiles
            loaded_tiles = layer_data.get("tiles", [])
            for y in range(min(layer_height, len(loaded_tiles))):
                row = loaded_tiles[y] if y < len(loaded_tiles) else []
                for x in range(min(layer_width, len(row))):
                    try:
                        layer.tiles[y][x] = int(row[x])
                    except (ValueError, TypeError):
                        layer.tiles[y][x] = 0

            # Carrega tileset
            tileset_path = layer_data.get("tileset_path")
            if tileset_path:
                found_path = self._find_tileset_path(tileset_path, base_path)
                if found_path:
                    layer.load_tileset(found_path, self.tile_size, self.tile_size)
                    print(f"  ✓ Tileset carregado para {layer.name}")

            self.layers.append(layer)
            print(f"  ✓ Camada {layer.name} carregada")

        print(f"GameLayerManager carregado: {len(self.layers)} camadas")
        return self

    def _find_tileset_path(self, tileset_path, base_path):
        """Encontra o caminho correto do tileset"""
        import os

        basename = os.path.basename(tileset_path)
        possible_paths = []

        if base_path:
            clean_path = tileset_path
            if clean_path.startswith('pokemon-tower-defense/'):
                clean_path = clean_path[len('pokemon-tower-defense/'):]
            if clean_path.startswith('pokemon-tower-defense\\'):
                clean_path = clean_path[len('pokemon-tower-defense\\'):]
            possible_paths.append(os.path.join(base_path, clean_path))

        possible_paths.append(os.path.join("res", "AllTiles", basename))

        if base_path:
            possible_paths.append(os.path.join(base_path, "res", "AllTiles", basename))

        possible_paths.append(basename)

        for path in possible_paths:
            normalized = os.path.normpath(path)
            if os.path.exists(normalized):
                return normalized

        return None

    def render_all(self, screen, camera, screen_manager):
        """Renderiza todas as camadas na ordem correta"""
        # Ordem: ground, decoration, ceiling
        for layer in self.layers:
            if layer.layer_type == "ground":
                layer.render(screen, camera, screen_manager)
        for layer in self.layers:
            if layer.layer_type == "decoration":
                layer.render(screen, camera, screen_manager)
        for layer in self.layers:
            if layer.layer_type == "ceiling":
                layer.render(screen, camera, screen_manager)

    def get_dimensions(self):
        return (self.width * self.tile_size, self.height * self.tile_size)

    def invalidate_cache(self):
        for layer in self.layers:
            layer._cached_tiles.clear()