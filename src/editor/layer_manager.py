# src/editor/layer_manager.py

"""
Gerenciador de layers do mapa com suporte a múltiplos tilesets de QUALQUER tamanho.

Suporta:
- Auto-detecção da grade do tileset (sem limite 6x8)
- Offsets em pixels por tile (posicionamento livre sem snap no pincel normal)
- Autotiles 47-tile (blob) com recálculo dinâmico de bordas
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
        self.tile_offsets = {}

        # ===== AUTOTILE =====
        # grid paralelo: 0 = célula normal; >0 = local_id do autotile
        self.autotile_ids = [[0 for _ in range(width)] for _ in range(height)]
        # metadados dos tilesets de autotile que foram adicionados a ESTA layer
        # [{local_id, start_id, count, sheet_path, cell_size, cols, rows}]
        self.autotile_tilesets = []

        self.visible = True
        self.opacity = 255
        self.tileset_path = None
        self.tileset = []

        # Múltiplos tilesets
        self.tilesets = []
        self.tileset_paths = []

        # ===== CACHE DE TILES ESCALADOS =====
        # Chave: (tile_size_scaled, opacity) -> lista de Surfaces prontas.
        # Pequeno LRU (máx 3) para não explodir memória durante zoom.
        # Evita chamar pygame.transform.scale() por tile por frame.
        self._scaled_cache = {}
        self._scaled_cache_order = []  # lista de chaves (LRU)
        self._SCALED_CACHE_MAX = 3

    # ------------------------------------------------------------------
    # CACHE
    # ------------------------------------------------------------------
    def _invalidate_scaled_cache(self):
        self._scaled_cache.clear()
        self._scaled_cache_order.clear()

    def _get_scaled_tiles(self, tile_size_scaled, opacity):
        """
        Retorna lista de Surfaces já escaladas para (tile_size_scaled, opacity).
        Reconstrói apenas quando a chave muda; reusa nas demais chamadas.
        """
        key = (tile_size_scaled, opacity)
        cached = self._scaled_cache.get(key)
        if cached is not None:
            # LRU touch
            try:
                self._scaled_cache_order.remove(key)
            except ValueError:
                pass
            self._scaled_cache_order.append(key)
            return cached

        needs_alpha = opacity < 255
        out = []
        for tile in self.tileset:
            if (tile.get_width() != tile_size_scaled
                    or tile.get_height() != tile_size_scaled):
                s = pygame.transform.scale(
                    tile, (tile_size_scaled, tile_size_scaled)
                )
            else:
                s = tile
            if needs_alpha:
                s = s.copy()
                s.set_alpha(opacity)
            out.append(s)

        # LRU evict
        if len(self._scaled_cache_order) >= self._SCALED_CACHE_MAX:
            oldest = self._scaled_cache_order.pop(0)
            self._scaled_cache.pop(oldest, None)

        self._scaled_cache[key] = out
        self._scaled_cache_order.append(key)
        return out

    # ==================================================================
    # TILES
    # ==================================================================
    def set_tile(self, x, y, tile_id, offset=None):
        if 0 <= x < self.width and 0 <= y < self.height:
            # Se um tile normal está sendo colocado, limpa o autotile da célula
            if self.autotile_ids[y][x] != 0:
                self.erase_autotile_at(x, y)

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
        return self.tile_offsets.get((x, y), (0, 0))

    def get_all_tiles_with_boundaries(self):
        all_tiles = []
        boundaries = []
        for ts_info in self.tilesets:
            boundaries.append(len(all_tiles))
            all_tiles.extend(ts_info['tiles'])
        return all_tiles, boundaries

    # ==================================================================
    # AUTOTILE
    # ==================================================================
    def add_autotile_tileset(self, local_id, sheet_path, tiles,
                             cell_size, cols=8, rows=6):
        """
        Adiciona os tiles do sheet de autotile ao tileset da layer.
        IDEMPOTENTE: se o metadata já existe mas os tiles NÃO estão no
        `tileset` (caso comum após load do JSON), re-adiciona mantendo o
        `start_id` para não quebrar tiles já pintados.
        """
        existing = None
        for info in self.autotile_tilesets:
            if info['local_id'] == local_id:
                existing = info
                break

        if existing is not None:
            # Metadata existe — checa se os tiles reais estão no tileset
            expected_end = existing['start_id'] + existing['count'] - 1
            if len(self.tileset) >= expected_end:
                # Tudo OK, nada a fazer
                return existing

            # Faltam tiles — re-adiciona mantendo o mesmo start_id (se possível)
            current_len = len(self.tileset)
            if current_len + 1 != existing['start_id']:
                print(f"[Layer] Aviso: start_id do autotile #{local_id} "
                      f"não bate (salvo={existing['start_id']}, "
                      f"atual={current_len + 1}). Reajustando.")
                existing['start_id'] = current_len + 1

            self.tileset.extend(tiles)
            existing['count'] = len(tiles)
            self._invalidate_scaled_cache()
            return existing

        # Nova entrada
        start_id = len(self.tileset) + 1
        self.tileset.extend(tiles)
        info = {
            'local_id': local_id,
            'start_id': start_id,
            'count': len(tiles),
            'sheet_path': sheet_path,
            'cell_size': cell_size,
            'cols': cols,
            'rows': rows,
        }
        self.autotile_tilesets.append(info)
        self._invalidate_scaled_cache()
        return info

    def find_autotile_tileset(self, local_id):
        for info in self.autotile_tilesets:
            if info['local_id'] == local_id:
                return info
        return None

    def get_autotile(self, x, y):
        if 0 <= x < self.width and 0 <= y < self.height:
            return self.autotile_ids[y][x]
        return 0

    def _compute_mask(self, x, y, local_id):
        """Máscara 8-bit considerando só vizinhos do MESMO autotile."""
        def same(nx, ny):
            if 0 <= nx < self.width and 0 <= ny < self.height:
                return self.autotile_ids[ny][nx] == local_id
            return False

        from src.editor.autotile_system import DIRS, canonical
        m = 0
        for dx, dy, bit in DIRS:
            if same(x + dx, y + dy):
                m |= bit
        return canonical(m)

    def _refresh_autotile_tile(self, x, y):
        """Recalcula o tile_id da célula baseado no autotile atual."""
        aid = self.autotile_ids[y][x]
        if aid == 0:
            return
        info = self.find_autotile_tileset(aid)
        if info is None:
            return

        from src.editor.autotile_system import MASK_TO_POS
        mask = self._compute_mask(x, y, aid)
        pos = MASK_TO_POS.get(mask)
        if pos is None:
            return
        col, row = pos
        local_idx = row * info['cols'] + col
        if local_idx < 0 or local_idx >= info['count']:
            return
        self.tiles[y][x] = info['start_id'] + local_idx

    def paint_autotile(self, x, y, local_id):
        """Marca (x, y) e recalcula ele + 8 vizinhos."""
        if not (0 <= x < self.width and 0 <= y < self.height):
            return False
        if self.find_autotile_tileset(local_id) is None:
            return False

        self.autotile_ids[y][x] = local_id
        self._refresh_autotile_tile(x, y)

        from src.editor.autotile_system import DIRS
        for dx, dy, _ in DIRS:
            nx, ny = x + dx, y + dy
            if 0 <= nx < self.width and 0 <= ny < self.height:
                if self.autotile_ids[ny][nx] == local_id:
                    self._refresh_autotile_tile(nx, ny)
        return True

    def erase_autotile_at(self, x, y):
        """Remove o autotile desta célula e reajusta os vizinhos do mesmo id."""
        if not (0 <= x < self.width and 0 <= y < self.height):
            return False
        aid = self.autotile_ids[y][x]
        if aid == 0:
            return False

        self.autotile_ids[y][x] = 0
        self.tiles[y][x] = 0

        from src.editor.autotile_system import DIRS
        for dx, dy, _ in DIRS:
            nx, ny = x + dx, y + dy
            if 0 <= nx < self.width and 0 <= ny < self.height:
                if self.autotile_ids[ny][nx] == aid:
                    self._refresh_autotile_tile(nx, ny)
        return True

    def clear_autotile_if_any(self, x, y):
        """Chamado quando um tile NORMAL é pintado em cima de um autotile."""
        if not (0 <= x < self.width and 0 <= y < self.height):
            return
        if self.autotile_ids[y][x] != 0:
            self.erase_autotile_at(x, y)

    # ==================================================================
    # EXTRAÇÃO DE TILES (auto-detecção)
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
        self._invalidate_scaled_cache()
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

        self._invalidate_scaled_cache()
        print(f"[Layer] ✓ Tileset adicionado: +{len(tiles)} tiles. "
              f"Total: {len(self.tileset)} em {len(self.tilesets)} sets")
        return True

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

        new_offsets = {}
        for (x, y), off in self.tile_offsets.items():
            if 0 <= x < new_width and 0 <= y < new_height:
                new_offsets[(x, y)] = off

        # ===== AUTOTILE: preserva o que cai no novo range =====
        new_autotile_ids = [[0 for _ in range(new_width)] for _ in range(new_height)]
        for y in range(min(self.height, new_height)):
            for x in range(min(self.width, new_width)):
                new_autotile_ids[y][x] = self.autotile_ids[y][x]

        self.tiles = new_tiles
        self.tile_offsets = new_offsets
        self.autotile_ids = new_autotile_ids
        self.width = new_width
        self.height = new_height
        return True

    # ==================================================================
    # RENDER — OTIMIZADO (usa cache de tiles escalados)
    # ==================================================================
    def render(self, screen, camera, screen_manager):
        if not self.visible or not self.tileset:
            return

        sm = screen_manager
        cam_offset_x = round((-camera.x * camera.zoom * sm.render_scale +
                              (sm.render_width / 2) * sm.render_scale +
                              sm.viewport_x))
        cam_offset_y = round((-camera.y * camera.zoom * sm.render_scale +
                              (sm.render_height / 2) * sm.render_scale +
                              sm.viewport_y))

        tile_size_scaled = max(1, round(self.tile_size * camera.zoom * sm.render_scale))

        start_x = max(0, (-cam_offset_x) // tile_size_scaled - 2)
        start_y = max(0, (-cam_offset_y) // tile_size_scaled - 2)
        end_x = min(self.width, start_x + (sm.viewport_width // tile_size_scaled) + 6)
        end_y = min(self.height, start_y + (sm.viewport_height // tile_size_scaled) + 6)

        zoom_scale = camera.zoom * sm.render_scale

        # ===== USA CACHE (evita pygame.transform.scale por tile/frame) =====
        scaled_tiles = self._get_scaled_tiles(tile_size_scaled, self.opacity)
        num_scaled = len(scaled_tiles)

        # Local vars para acelerar o loop
        screen_blit = screen.blit
        tiles_matrix = self.tiles
        offsets_map = self.tile_offsets
        vx = sm.viewport_x
        vy = sm.viewport_y
        vw = sm.viewport_width
        vh = sm.viewport_height

        for y in range(start_y, end_y):
            row = tiles_matrix[y]
            base_y = y * tile_size_scaled + cam_offset_y
            for x in range(start_x, end_x):
                tile_id = row[x]
                try:
                    tile_index = tile_id - 1 if isinstance(tile_id, int) else int(tile_id) - 1
                except (ValueError, TypeError):
                    continue

                if 0 <= tile_index < num_scaled:
                    base_screen_x = x * tile_size_scaled + cam_offset_x
                    base_screen_y = base_y

                    # Offset por tile
                    off = offsets_map.get((x, y))
                    if off is not None:
                        base_screen_x += round(off[0] * zoom_scale)
                        base_screen_y += round(off[1] * zoom_scale)

                    # Culling
                    if (base_screen_x + tile_size_scaled < vx or
                            base_screen_x > vx + vw or
                            base_screen_y + tile_size_scaled < vy or
                            base_screen_y > vy + vh):
                        continue

                    screen_blit(scaled_tiles[tile_index], (base_screen_x, base_screen_y))

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

    def move_layer(self, from_index, to_index):
        """
        Reordena uma camada. Alterar a posição na lista muda a prioridade
        de renderização (dentro do mesmo tipo: index maior = mais na frente).
        """
        n = len(self.layers)
        if not (0 <= from_index < n) or not (0 <= to_index < n):
            return False
        if from_index == to_index:
            return False
        layer = self.layers.pop(from_index)
        self.layers.insert(to_index, layer)
        return True

    def set_layer_type(self, index, new_type):
        """Troca o tipo de uma camada (GROUND / DECORATION / CEILING)."""
        if 0 <= index < len(self.layers):
            self.layers[index].layer_type = new_type
            return True
        return False

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

            # ===== AUTOTILE (só salva se houver) =====
            has_auto = any(any(c != 0 for c in row) for row in layer.autotile_ids)
            if has_auto:
                layer_dict["autotile_ids"] = layer.autotile_ids
            if layer.autotile_tilesets:
                layer_dict["autotile_tilesets"] = layer.autotile_tilesets

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

            # ===== AUTOTILE (retrocompatível) =====
            auto_raw = layer_data.get("autotile_ids", None)
            if auto_raw:
                for y in range(min(layer_height, len(auto_raw))):
                    for x in range(min(layer_width, len(auto_raw[y]))):
                        try:
                            layer.autotile_ids[y][x] = int(auto_raw[y][x])
                        except (ValueError, TypeError, IndexError):
                            layer.autotile_ids[y][x] = 0
                count = sum(1 for row in layer.autotile_ids for c in row if c != 0)
                print(f"    Autotiles: {count} células")
            layer.autotile_tilesets = layer_data.get("autotile_tilesets", []) or []
            if layer.autotile_tilesets:
                print(f"    Autotile tilesets: {len(layer.autotile_tilesets)}")

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