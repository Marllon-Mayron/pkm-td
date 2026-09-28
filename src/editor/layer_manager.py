# src/editor/layer_manager.py

"""
Gerenciador de layers do mapa com suporte a múltiplos tilesets de QUALQUER tamanho.

Suporta:
- Auto-detecção da grade do tileset (sem limite 6x8)
- Offsets em pixels por tile (posicionamento livre sem snap no pincel normal)
"""
import pygame
import os
from enum import Enum

try:
    from src.config.paths import PROJECT_ROOT, RES_PATH
except ImportError:
    PROJECT_ROOT = ""
    RES_PATH = ""


class LayerType(Enum):
    GROUND = "ground"
    DECORATION = "decoration"
    CEILING = "ceiling"


class Layer:
    def __init__(self, name, layer_type, width, height, tile_size=16):
        self.name = name
        self.layer_type = layer_type
        self.width = width
        self.height = height
        self.tile_size = tile_size
        self.tiles = [[0 for _ in range(width)] for _ in range(height)]

        # ===== OFFSETS POR TILE (pintura livre) =====
        # {(x, y): (dx, dy)} — chave = célula, valor = pixels de deslocamento
        # Só células com offset != (0, 0) aparecem aqui. Retrocompatível com JSON antigo.
        self.tile_offsets = {}

        self.visible = True
        self.opacity = 255
        self.tileset_path = None
        self.tileset = []

        # Múltiplos tilesets
        self.tilesets = []
        self.tileset_paths = []

    # ==================================================================
    # TILES
    # ==================================================================
    def set_tile(self, x, y, tile_id, offset=None):
        """
        Define um tile na posição.

        offset: tupla (dx, dy) em pixels ou None. Se (0, 0) ou None, remove offset.
        """
        if 0 <= x < self.width and 0 <= y < self.height:
            try:
                self.tiles[y][x] = int(tile_id)
            except (ValueError, TypeError):
                self.tiles[y][x] = 0

            key = (x, y)
            if offset and offset != (0, 0):
                self.tile_offsets[key] = (int(offset[0]), int(offset[1]))
            else:
                self.tile_offsets.pop(key, None)
            return True
        return False

    def get_tile(self, x, y):
        if 0 <= x < self.width and 0 <= y < self.height:
            return self.tiles[y][x]
        return 0

    def get_tile_offset(self, x, y):
        """Retorna (dx, dy) ou (0, 0)."""
        return self.tile_offsets.get((x, y), (0, 0))

    def get_all_tiles_with_boundaries(self):
        all_tiles = []
        boundaries = []
        for ts_info in self.tilesets:
            boundaries.append(len(all_tiles))
            all_tiles.extend(ts_info['tiles'])
        return all_tiles, boundaries

    # ==================================================================
    # EXTRAÇÃO DE TILES (AUTO-DETECÇÃO)
    # ==================================================================
    def _extract_tiles(self, image_path, tile_width, tile_height, spacing=0):
        try:
            if not os.path.exists(image_path):
                print(f"[TileExtract] ERRO: arquivo não encontrado: {image_path}")
                return None, 0, 0

            sheet = pygame.image.load(image_path).convert_alpha()
            img_w = sheet.get_width()
            img_h = sheet.get_height()

            step_x = tile_width + spacing
            step_y = tile_height + spacing

            cols = (img_w + spacing) // step_x
            rows = (img_h + spacing) // step_y

            if cols <= 0 or rows <= 0:
                return None, 0, 0

            print(f"[TileExtract] {os.path.basename(image_path)}: "
                  f"{img_w}x{img_h} -> {cols}x{rows} = {cols * rows} tiles")

            tiles = []
            for r in range(rows):
                for c in range(cols):
                    rect = pygame.Rect(c * step_x, r * step_y, tile_width, tile_height)
                    if rect.right > img_w or rect.bottom > img_h:
                        empty = pygame.Surface((tile_width, tile_height), pygame.SRCALPHA)
                        empty.fill((0, 0, 0, 0))
                        tiles.append(empty)
                    else:
                        tiles.append(sheet.subsurface(rect))
            return tiles, cols, rows

        except Exception as e:
            print(f"[TileExtract] Erro: {e}")
            import traceback
            traceback.print_exc()
            return None, 0, 0

    def _make_relative_path(self, image_path):
        if not os.path.isabs(image_path):
            return image_path.replace('\\', '/')
        root = self._get_project_root()
        if root:
            try:
                rel = os.path.relpath(image_path, root)
                return rel.replace('\\', '/')
            except (ValueError, Exception):
                pass
        return os.path.basename(image_path)

    def load_tileset_from_image(self, image_path, tile_width, tile_height, spacing=0):
        tiles, cols, rows = self._extract_tiles(image_path, tile_width, tile_height, spacing)
        if tiles is None:
            return False

        self.tileset = tiles
        self.tilesets = [{
            'path': image_path,
            'tiles': tiles,
            'start_id': 1,
            'count': len(tiles),
            'cols': cols,
            'rows': rows,
            'tile_width': tile_width,
            'tile_height': tile_height,
            'spacing': spacing,
            'tileset_index': 0,
        }]
        self.tileset_paths = [self._make_relative_path(image_path)]
        self.tileset_path = self.tileset_paths[0]
        print(f"[Layer] ✓ Tileset carregado: {len(tiles)} tiles ({cols}x{rows})")
        return True

    def add_tileset_from_image(self, image_path, tile_width, tile_height, spacing=0):
        tiles, cols, rows = self._extract_tiles(image_path, tile_width, tile_height, spacing)
        if tiles is None:
            return False

        next_start_id = len(self.tileset) + 1
        self.tilesets.append({
            'path': image_path,
            'tiles': tiles,
            'start_id': next_start_id,
            'count': len(tiles),
            'cols': cols,
            'rows': rows,
            'tile_width': tile_width,
            'tile_height': tile_height,
            'spacing': spacing,
            'tileset_index': len(self.tilesets),
        })
        self.tileset.extend(tiles)

        rel_path = self._make_relative_path(image_path)
        if rel_path not in self.tileset_paths:
            self.tileset_paths.append(rel_path)

        print(f"[Layer] ✓ Tileset adicionado: +{len(tiles)} tiles. "
              f"Total: {len(self.tileset)} em {len(self.tilesets)} sets")
        return True

    # Aliases de compatibilidade
    def load_tileset(self, image_path, tile_width, tile_height):
        return self.load_tileset_from_image(image_path, tile_width, tile_height)

    def add_tileset_6x8(self, image_path, tile_width, tile_height):
        return self.add_tileset_from_image(image_path, tile_width, tile_height)

    # ==================================================================
    # LOOKUP
    # ==================================================================
    def get_tileset_info(self, tile_id):
        try:
            tile_index = int(tile_id) - 1
            if tile_index < 0:
                return None
            current_start = 0
            for i, ts_info in enumerate(self.tilesets):
                count = ts_info['count']
                if tile_index < current_start + count:
                    local_index = tile_index - current_start
                    cols = ts_info.get('cols', 1) or 1
                    row = local_index // cols
                    col = local_index % cols
                    return (i, local_index, ts_info, row, col)
                current_start += count
            return None
        except (ValueError, TypeError):
            return None

    def get_tile_image(self, tile_id):
        try:
            tile_index = int(tile_id) - 1
            if 0 <= tile_index < len(self.tileset):
                return self.tileset[tile_index]
            return None
        except (ValueError, TypeError):
            return None

    # ==================================================================
    # RESIZE
    # ==================================================================
    def resize(self, new_width, new_height, default_tile=0):
        if new_width == self.width and new_height == self.height:
            return True

        try:
            default_tile = int(default_tile)
        except (ValueError, TypeError):
            default_tile = 0

        new_tiles = [[default_tile for _ in range(new_width)] for _ in range(new_height)]
        for y in range(min(self.height, new_height)):
            for x in range(min(self.width, new_width)):
                new_tiles[y][x] = self.tiles[y][x]

        # Filtra offsets válidos
        new_offsets = {}
        for (x, y), off in self.tile_offsets.items():
            if 0 <= x < new_width and 0 <= y < new_height:
                new_offsets[(x, y)] = off

        self.tiles = new_tiles
        self.tile_offsets = new_offsets
        self.width = new_width
        self.height = new_height
        return True

    # ==================================================================
    # RENDER
    # ==================================================================
    def render(self, screen, camera, screen_manager):
        if not self.visible or not self.tileset:
            return

        cam_offset_x = round((-camera.x * camera.zoom * screen_manager.render_scale +
                              (screen_manager.render_width / 2) * screen_manager.render_scale +
                              screen_manager.viewport_x))
        cam_offset_y = round((-camera.y * camera.zoom * screen_manager.render_scale +
                              (screen_manager.render_height / 2) * screen_manager.render_scale +
                              screen_manager.viewport_y))

        tile_size_scaled = max(1, round(self.tile_size * camera.zoom * screen_manager.render_scale))

        start_x = max(0, (-cam_offset_x) // tile_size_scaled - 2)
        start_y = max(0, (-cam_offset_y) // tile_size_scaled - 2)
        end_x = min(self.width, start_x + (screen_manager.viewport_width // tile_size_scaled) + 6)
        end_y = min(self.height, start_y + (screen_manager.viewport_height // tile_size_scaled) + 6)

        zoom_scale = camera.zoom * screen_manager.render_scale

        for y in range(start_y, end_y):
            for x in range(start_x, end_x):
                tile_id = self.tiles[y][x]
                try:
                    tile_index = int(tile_id) - 1
                except (ValueError, TypeError):
                    tile_index = -1

                if 0 <= tile_index < len(self.tileset):
                    base_screen_x = x * tile_size_scaled + cam_offset_x
                    base_screen_y = y * tile_size_scaled + cam_offset_y

                    # ===== OFFSET POR TILE (pintura livre) =====
                    off = self.tile_offsets.get((x, y))
                    if off and off != (0, 0):
                        base_screen_x += round(off[0] * zoom_scale)
                        base_screen_y += round(off[1] * zoom_scale)

                    # Culling
                    if (base_screen_x + tile_size_scaled < screen_manager.viewport_x or
                            base_screen_x > screen_manager.viewport_x + screen_manager.viewport_width or
                            base_screen_y + tile_size_scaled < screen_manager.viewport_y or
                            base_screen_y > screen_manager.viewport_y + screen_manager.viewport_height):
                        continue

                    tile_img = self.tileset[tile_index]
                    if (tile_img.get_width() != tile_size_scaled or
                            tile_img.get_height() != tile_size_scaled):
                        scaled_tile = pygame.transform.scale(
                            tile_img, (tile_size_scaled, tile_size_scaled)
                        )
                        scaled_tile.set_alpha(self.opacity)
                        screen.blit(scaled_tile, (base_screen_x, base_screen_y))
                    else:
                        tile_img.set_alpha(self.opacity)
                        screen.blit(tile_img, (base_screen_x, base_screen_y))

    # ==================================================================
    # HELPERS
    # ==================================================================
    def _get_project_root(self):
        try:
            from src.config.paths import PROJECT_ROOT
            return PROJECT_ROOT
        except ImportError:
            current = os.path.dirname(os.path.abspath(__file__))
            for _ in range(5):
                if os.path.exists(os.path.join(current, "src", "main.py")):
                    return current
                current = os.path.dirname(current)
            return ""


# ======================================================================
# LAYER MANAGER
# ======================================================================
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
        self.current_layer = len(self.layers) - 1
        return layer

    def remove_layer(self, index):
        if 0 <= index < len(self.layers):
            del self.layers[index]
            if self.current_layer >= len(self.layers):
                self.current_layer = max(0, len(self.layers) - 1)

    def resize_all_layers(self, new_width, new_height, default_tile=0):
        if new_width == self.width and new_height == self.height:
            return True
        try:
            default_tile = int(default_tile)
        except (ValueError, TypeError):
            default_tile = 0

        for layer in self.layers:
            layer.resize(new_width, new_height, default_tile)
        self.width = new_width
        self.height = new_height
        return True

    def get_current_layer(self):
        if 0 <= self.current_layer < len(self.layers):
            return self.layers[self.current_layer]
        return None

    def set_tile(self, x, y, tile_id, offset=None):
        layer = self.get_current_layer()
        if layer:
            return layer.set_tile(x, y, tile_id, offset)
        return False

    def get_tile(self, x, y, layer_index=None):
        if layer_index is None:
            layer_index = self.current_layer
        if 0 <= layer_index < len(self.layers):
            return self.layers[layer_index].get_tile(x, y)
        return 0

    def render_all(self, screen, camera, screen_manager):
        for layer in self.layers:
            if layer.layer_type == LayerType.GROUND:
                layer.render(screen, camera, screen_manager)
        for layer in self.layers:
            if layer.layer_type == LayerType.DECORATION:
                layer.render(screen, camera, screen_manager)
        for layer in self.layers:
            if layer.layer_type == LayerType.CEILING:
                layer.render(screen, camera, screen_manager)

    # ==================================================================
    # SERIALIZAÇÃO
    # ==================================================================
    def to_dict(self):
        max_width = 0
        max_height = 0
        for layer in self.layers:
            max_width = max(max_width, layer.width)
            max_height = max(max_height, layer.height)

        layers_data = []
        for layer in self.layers:
            layer_dict = {
                "name": layer.name,
                "type": layer.layer_type.value,
                "tiles": layer.tiles,
                "width": layer.width,
                "height": layer.height,
                "tile_size": layer.tile_size,
            }

            # ===== OFFSETS (só salva se houver) =====
            if layer.tile_offsets:
                # Salva como {"x,y": [dx, dy]} para ficar legível
                layer_dict["tile_offsets"] = {
                    f"{x},{y}": [off[0], off[1]]
                    for (x, y), off in layer.tile_offsets.items()
                }

            if getattr(layer, 'tileset_paths', None):
                layer_dict["tileset_paths"] = layer.tileset_paths
            elif layer.tileset_path:
                layer_dict["tileset_path"] = layer.tileset_path

            layers_data.append(layer_dict)

        return {
            "width": max_width,
            "height": max_height,
            "tile_size": self.tile_size,
            "layers": layers_data,
        }

    def from_dict(self, data, base_path=""):
        print("\n=== LayerManager.from_dict ===")

        self.width = data.get("width", 100)
        self.height = data.get("height", 100)
        self.layers = []
        self.current_layer = 0

        for layer_idx, layer_data in enumerate(data["layers"]):
            layer_width = layer_data.get("width", self.width)
            layer_height = layer_data.get("height", self.height)
            layer_tile_size = layer_data.get("tile_size", self.tile_size)

            print(f"\n--- Layer {layer_idx}: {layer_data['name']} "
                  f"({layer_width}x{layer_height}, tile={layer_tile_size}) ---")

            loaded_tiles = layer_data["tiles"]

            layer = Layer(
                layer_data["name"],
                LayerType(layer_data["type"]),
                layer_width,
                layer_height,
                layer_tile_size,
            )

            # Tiles
            for y in range(layer_height):
                for x in range(layer_width):
                    if y < len(loaded_tiles) and x < len(loaded_tiles[y]):
                        try:
                            layer.tiles[y][x] = int(loaded_tiles[y][x])
                        except (ValueError, TypeError):
                            layer.tiles[y][x] = 0
                    else:
                        layer.tiles[y][x] = 0

            # ===== OFFSETS (retrocompatível — se não houver, fica vazio) =====
            offsets_raw = layer_data.get("tile_offsets", {})
            if offsets_raw:
                for key, off in offsets_raw.items():
                    try:
                        x_str, y_str = key.split(",")
                        x = int(x_str)
                        y = int(y_str)
                        if 0 <= x < layer_width and 0 <= y < layer_height:
                            dx = int(off[0])
                            dy = int(off[1])
                            if (dx, dy) != (0, 0):
                                layer.tile_offsets[(x, y)] = (dx, dy)
                    except (ValueError, IndexError, TypeError):
                        continue
                print(f"    Offsets: {len(layer.tile_offsets)} tiles com deslocamento")

            # Tilesets
            tileset_paths = []
            if layer_data.get("tileset_paths"):
                tileset_paths = layer_data["tileset_paths"]
            elif layer_data.get("tileset_path"):
                tileset_paths = [layer_data["tileset_path"]]

            slice_size = self.tile_size

            for ts_idx, ts_path in enumerate(tileset_paths):
                if not ts_path:
                    continue

                possible_paths = []
                basename = os.path.basename(ts_path)

                project_root = self._get_project_root()
                if project_root:
                    clean = ts_path
                    if clean.startswith('pkm-td/'):
                        clean = clean[len('pkm-td/'):]
                    if clean.startswith('pkm-td\\'):
                        clean = clean[len('pkm-td\\'):]
                    possible_paths.append(os.path.join(project_root, clean))

                if base_path:
                    possible_paths.append(os.path.join(base_path, ts_path))

                possible_paths.append(os.path.join(RES_PATH, "AllTiles", basename))
                possible_paths.append(basename)

                for path in possible_paths:
                    normalized = os.path.normpath(path)
                    if os.path.exists(normalized):
                        if ts_idx == 0 and not layer.tileset:
                            layer.load_tileset_from_image(normalized, slice_size, slice_size)
                        else:
                            layer.add_tileset_from_image(normalized, slice_size, slice_size)
                        break

            self.layers.append(layer)

        print("\n=== FIM from_dict ===\n")
        return self

    def _get_project_root(self):
        try:
            from src.config.paths import PROJECT_ROOT
            return PROJECT_ROOT
        except ImportError:
            current = os.path.dirname(os.path.abspath(__file__))
            for _ in range(5):
                if os.path.exists(os.path.join(current, "src", "main.py")):
                    return current
                current = os.path.dirname(current)
            return ""