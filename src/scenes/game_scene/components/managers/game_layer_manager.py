# src/scenes/game_scene/components/renderer/game_layer_manager.py

"""
Gerenciador de camadas para o jogo.

IMPORTANTE — arquitetura de renderização:
  Cada camada é uma superfície TRANSPARENTE (SRCALPHA), exatamente como no
  editor. Os tiles são blitados nessa superfície e o blend natural do alpha
  faz o resultado aparecer igual ao editor, sem criar "caixas pretas" em
  cima das camadas de baixo.

  Isso significa que:
    - Um tile de chão (pixels com alpha=255) naturalmente cobre o fundo.
    - Um tile de decoração com regiões vazias deixa o chão aparecer.
    - Não importa se a camada está marcada como "ground", "decoration" ou
      "ceiling" — o resultado visual é o mesmo.
  O `layer_type` fica apenas como metadado (usado para ordenação em 3 passes
  pelo GameLayerManager: ground → decoration → ceiling).
"""
import pygame
import os
from src.core.render_context import render_context


class GameLayer:
    def __init__(self, name, layer_type, width, height, tile_size=16):
        self.name = name
        self.layer_type = layer_type
        self.width = width
        self.height = height
        self.tile_size = tile_size
        self.tiles = [[0 for _ in range(width)] for _ in range(height)]
        self.tile_offsets = {}  # {(x, y): (dx, dy)}
        self.visible = True
        self.opacity = 255
        self.tileset = []
        self.tilesets = []
        self.tileset_paths = []

        # ===== AUTOTILE METADATA =====
        self.autotile_tilesets = []

        self._cached_tiles = {}

        self._cached_surface = None
        self._cached_scale = None
        self._cached_zoom = None
        self._cached_visible_section = None
        self._last_camera_rect = None
        self._last_screen_pos = None
        self._recreate_counter = 0

    def _invalidate_surface_cache(self):
        self._cached_surface = None
        self._cached_scale = None
        self._cached_zoom = None
        self._cached_visible_section = None
        self._last_camera_rect = None
        self._last_screen_pos = None
        self._recreate_counter += 1

    def set_tile(self, x, y, tile_id, offset=None):
        if 0 <= x < self.width and 0 <= y < self.height:
            self.tiles[y][x] = int(tile_id)
            if offset and offset != (0, 0):
                self.tile_offsets[(x, y)] = (int(offset[0]), int(offset[1]))
            else:
                self.tile_offsets.pop((x, y), None)
            self._invalidate_surface_cache()
            return True
        return False

    def get_tile_offset(self, x, y):
        return self.tile_offsets.get((x, y), (0, 0))

    # ==================================================================
    # EXTRAÇÃO
    # ==================================================================
    def _extract_tiles(self, image_path, tile_width, tile_height, spacing=0):
        try:
            if not os.path.exists(image_path):
                return None, 0, 0
            sheet = pygame.image.load(image_path).convert_alpha()
            img_w, img_h = sheet.get_width(), sheet.get_height()
            step_x = tile_width + spacing
            step_y = tile_height + spacing
            cols = (img_w + spacing) // step_x
            rows = (img_h + spacing) // step_y
            if cols <= 0 or rows <= 0:
                return None, 0, 0
            print(f"[GameLayer._extract] {os.path.basename(image_path)}: "
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
            print(f"[GameLayer._extract] Erro: {e}")
            import traceback
            traceback.print_exc()
            return None, 0, 0

    def _empty_tile(self):
        size = self.tile_size
        surf = pygame.Surface((size, size), pygame.SRCALPHA)
        surf.fill((0, 0, 0, 0))
        return surf

    def load_tileset_from_image(self, image_path, tile_width, tile_height, spacing=0):
        tiles, cols, rows = self._extract_tiles(image_path, tile_width, tile_height, spacing)
        if tiles is None:
            return False

        # Reconstrói do zero: zera metadata de autotile antigo
        self.autotile_tilesets = []

        self.tileset = tiles
        self.tilesets = [{
            'path': image_path, 'tiles': tiles, 'start_id': 1, 'count': len(tiles),
            'cols': cols, 'rows': rows, 'tile_width': tile_width, 'tile_height': tile_height,
            'spacing': spacing, 'tileset_index': 0,
        }]
        self.tileset_paths = [image_path]
        self._invalidate_surface_cache()
        return True

    def add_tileset_from_image(self, image_path, tile_width, tile_height, spacing=0):
        tiles, cols, rows = self._extract_tiles(image_path, tile_width, tile_height, spacing)
        if tiles is None:
            return False

        # Adicionar tileset normal invalida o metadata de autotile
        self.autotile_tilesets = []

        next_start = len(self.tileset) + 1
        self.tilesets.append({
            'path': image_path, 'tiles': tiles, 'start_id': next_start, 'count': len(tiles),
            'cols': cols, 'rows': rows, 'tile_width': tile_width, 'tile_height': tile_height,
            'spacing': spacing, 'tileset_index': len(self.tilesets),
        })
        self.tileset.extend(tiles)
        if image_path not in self.tileset_paths:
            self.tileset_paths.append(image_path)
        self._invalidate_surface_cache()
        return True

    # ==================================================================
    # AUTOTILE — respeita start_id e count salvos no JSON
    # ==================================================================
    def add_autotile_tileset(self, local_id, sheet_path, tiles,
                             cell_size, cols=8, rows=6,
                             start_id=None, count=None):
        """
        Anexa tiles de um autotile ao tileset da layer.
        Se start_id for fornecido, ALINHA o tileset para que o primeiro
        tile do autotile fique exatamente nesse ID.
        """
        # Normaliza a lista de tiles para o 'count' salvo
        if count is not None:
            count = int(count)
            if len(tiles) > count:
                tiles = list(tiles[:count])
            elif len(tiles) < count:
                pad = [self._empty_tile() for _ in range(count - len(tiles))]
                tiles = list(tiles) + pad

        # Alinha o tileset ao start_id salvo
        if start_id is not None:
            start_id = int(start_id)
            needed_len = start_id - 1
            current_len = len(self.tileset)

            if current_len < needed_len:
                pad_count = needed_len - current_len
                print(f"[GameLayer] autotile #{local_id}: "
                      f"padding {pad_count} tiles vazios para alinhar "
                      f"start_id={start_id}")
                self.tileset.extend(
                    self._empty_tile() for _ in range(pad_count)
                )
            elif current_len > needed_len:
                print(f"[GameLayer] AVISO: autotile #{local_id} start_id="
                      f"{start_id} mas tileset já tem {current_len} tiles. "
                      f"Truncando {current_len - needed_len} tiles.")
                del self.tileset[needed_len:]

            self.tileset.extend(tiles)
            info = {
                'local_id': int(local_id),
                'start_id': start_id,
                'count': len(tiles),
                'sheet_path': sheet_path,
                'cell_size': int(cell_size),
                'cols': int(cols),
                'rows': int(rows),
            }

            for i, existing in enumerate(self.autotile_tilesets):
                if existing.get('local_id') == local_id:
                    self.autotile_tilesets[i] = info
                    break
            else:
                self.autotile_tilesets.append(info)

            self._invalidate_surface_cache()
            return info

        # Fallback: sem start_id
        existing = None
        for info in self.autotile_tilesets:
            if info.get('local_id') == local_id:
                existing = info
                break

        if existing is not None:
            expected_end = existing['start_id'] + existing['count'] - 1
            if len(self.tileset) >= expected_end:
                return existing

            current_len = len(self.tileset)
            if current_len + 1 != existing['start_id']:
                print(f"[GameLayer] Aviso: start_id do autotile #{local_id} "
                      f"não bate (salvo={existing['start_id']}, "
                      f"atual={current_len + 1}). Reajustando.")
                existing['start_id'] = current_len + 1

            self.tileset.extend(tiles)
            existing['count'] = len(tiles)
            self._invalidate_surface_cache()
            return existing

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
        self._invalidate_surface_cache()
        return info

    def find_autotile_tileset(self, local_id):
        for info in self.autotile_tilesets:
            if info.get('local_id') == local_id:
                return info
        return None

    def load_tileset(self, p, w, h):
        return self.load_tileset_from_image(p, w, h)

    def add_tileset(self, p, w, h):
        return self.add_tileset_from_image(p, w, h)

    def get_tile_image(self, tile_id):
        try:
            idx = int(tile_id) - 1
            if 0 <= idx < len(self.tileset):
                return self.tileset[idx]
            return None
        except (ValueError, TypeError):
            return None

    # ==================================================================
    # CACHE / RENDER
    # ==================================================================
    def _get_scaled_tile(self, tile_index, target_size):
        key = (tile_index, target_size)
        if key not in self._cached_tiles:
            original = self.tileset[tile_index]
            scaled = pygame.transform.scale(original, (target_size, target_size))
            if len(self._cached_tiles) > 1000:
                for k in list(self._cached_tiles.keys())[:500]:
                    del self._cached_tiles[k]
            self._cached_tiles[key] = scaled
        return self._cached_tiles[key]

    def _render_to_surface(self, scale):
        tile_size_scaled = max(1, int(self.tile_size * scale))
        total_w = self.width * tile_size_scaled
        total_h = self.height * tile_size_scaled
        if total_w <= 0 or total_h <= 0:
            return None

        surface = pygame.Surface((total_w, total_h), pygame.SRCALPHA)

        if not self.tileset:
            return surface

        # ===== PRÉ-COLETA COM OFFSETS =====
        tiles_to_render = []
        for y in range(self.height):
            for x in range(self.width):
                tile_id = self.tiles[y][x]
                if tile_id == 0:
                    continue
                try:
                    idx = int(tile_id) - 1
                except (ValueError, TypeError):
                    continue
                if 0 <= idx < len(self.tileset):
                    off = self.tile_offsets.get((x, y), (0, 0))
                    tiles_to_render.append((
                        idx,
                        x * tile_size_scaled,
                        y * tile_size_scaled,
                        off[0], off[1],
                    ))

        # Blit com offset aplicado
        for idx, sx, sy, off_x, off_y in tiles_to_render:
            surf = self._get_scaled_tile(idx, tile_size_scaled)
            if off_x != 0 or off_y != 0:
                ox = round(off_x * scale)
                oy = round(off_y * scale)
                surface.blit(surf, (sx + ox, sy + oy))
            else:
                surface.blit(surf, (sx, sy))

        return surface

    def render(self, screen, camera, screen_manager):
        if not self.visible:
            return
        if not self.tileset:
            return

        current_scale = render_context.get_scale(camera, screen_manager)
        current_zoom = camera.zoom if camera else 1.0

        if (self._cached_surface is None
                or self._cached_scale != current_scale
                or self._cached_zoom != current_zoom):
            self._cached_surface = self._render_to_surface(current_scale)
            self._cached_scale = current_scale
            self._cached_zoom = current_zoom
            self._cached_visible_section = None

        if self._cached_surface is None:
            return

        screen_x, screen_y = render_context.world_to_screen(0, 0, camera, screen_manager)

        visible_rect = camera.get_visible_rect()
        tile_size_scaled = max(1, int(self.tile_size * current_scale))

        # Aumenta margem para acomodar offsets
        margin = tile_size_scaled * 2

        vx_start = max(0, int((visible_rect.x - margin) / self.tile_size) * tile_size_scaled)
        vy_start = max(0, int((visible_rect.y - margin) / self.tile_size) * tile_size_scaled)
        vx_end = min(self._cached_surface.get_width(),
                     int((visible_rect.x + visible_rect.width + margin) / self.tile_size) * tile_size_scaled + tile_size_scaled)
        vy_end = min(self._cached_surface.get_height(),
                     int((visible_rect.y + visible_rect.height + margin) / self.tile_size) * tile_size_scaled + tile_size_scaled)

        key = (vx_start, vy_start, vx_end, vy_end, screen_x, screen_y)

        if (self._cached_visible_section is None or self._last_camera_rect != key):
            if vx_start < vx_end and vy_start < vy_end:
                try:
                    self._cached_visible_section = self._cached_surface.subsurface(
                        (vx_start, vy_start, vx_end - vx_start, vy_end - vy_start)
                    )
                    self._last_camera_rect = key
                    self._last_screen_pos = (screen_x + vx_start, screen_y + vy_start)
                except ValueError:
                    self._cached_visible_section = None
                    return

        if self._cached_visible_section and self._last_screen_pos:
            screen.blit(self._cached_visible_section,
                        (round(self._last_screen_pos[0]), round(self._last_screen_pos[1])))


# ======================================================================
# MANAGER
# ======================================================================
class GameLayerManager:
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
        print("\n=== GameLayerManager.load_from_dict ===")
        self.width = data.get("width", 100)
        self.height = data.get("height", 100)
        self.layers = []

        raw_layers = data.get("layers", [])
        print(f"Encontradas {len(raw_layers)} camadas")

        for layer_idx, layer_data in enumerate(raw_layers):
            layer_name = layer_data.get("name", "?")
            layer_type = layer_data.get("type", "ground")
            layer_width = layer_data.get("width", self.width)
            layer_height = layer_data.get("height", self.height)
            layer_tile_size = layer_data.get("tile_size", self.tile_size)

            print(f"\n--- [{layer_idx}] '{layer_name}' ({layer_type}, "
                  f"{layer_width}x{layer_height}, tile={layer_tile_size}) ---")

            layer = GameLayer(layer_name, layer_type, layer_width, layer_height, layer_tile_size)

            # Tiles
            loaded_tiles = layer_data.get("tiles", [])
            non_zero = 0
            for y in range(min(layer_height, len(loaded_tiles))):
                row = loaded_tiles[y] if y < len(loaded_tiles) else []
                for x in range(min(layer_width, len(row))):
                    try:
                        val = int(row[x])
                    except (ValueError, TypeError):
                        val = 0
                    layer.tiles[y][x] = val
                    if val != 0:
                        non_zero += 1
            print(f"    Tiles não-zero: {non_zero}")

            # ===== OFFSETS =====
            offsets_raw = layer_data.get("tile_offsets", {})
            if offsets_raw:
                for key, off in offsets_raw.items():
                    try:
                        xs, ys = key.split(",")
                        x, y = int(xs), int(ys)
                        if 0 <= x < layer_width and 0 <= y < layer_height:
                            dx, dy = int(off[0]), int(off[1])
                            if (dx, dy) != (0, 0):
                                layer.tile_offsets[(x, y)] = (dx, dy)
                    except (ValueError, IndexError, TypeError):
                        continue
                print(f"    Offsets: {len(layer.tile_offsets)} tiles deslocados")

            # ===== TILESETS NORMAIS =====
            tileset_paths = []
            if layer_data.get("tileset_paths"):
                tileset_paths = layer_data["tileset_paths"]
            elif layer_data.get("tileset_path"):
                tileset_paths = [layer_data["tileset_path"]]

            slice_size = self.tile_size
            for ts_idx, ts_path in enumerate(tileset_paths):
                if not ts_path:
                    continue
                found = self._find_tileset_path(ts_path, base_path)
                if not found:
                    print(f"    ✗ Tileset não encontrado: {ts_path}")
                    continue
                if ts_idx == 0 and not layer.tileset:
                    layer.load_tileset_from_image(found, slice_size, slice_size)
                else:
                    layer.add_tileset_from_image(found, slice_size, slice_size)

            # ===== AUTOTILES =====
            autotile_data = layer_data.get("autotile_tilesets", []) or []
            if autotile_data:
                loaded_at = 0
                for at in autotile_data:
                    sheet_path = at.get("sheet_path")
                    if not sheet_path:
                        continue

                    found = self._find_tileset_path(sheet_path, base_path, is_autotile=True)
                    if not found:
                        print(f"    ✗ Autotile sheet não encontrado: {sheet_path}")
                        continue

                    cell_size = int(at.get("cell_size", layer_tile_size))
                    cols = int(at.get("cols", 8))
                    rows = int(at.get("rows", 6))
                    local_id = int(at.get("local_id", 0))
                    saved_start = at.get("start_id")
                    saved_count = at.get("count")

                    tiles, _c, _r = layer._extract_tiles(found, cell_size, cell_size, 0)
                    if tiles is None:
                        print(f"    ✗ Falha ao extrair autotile: {found}")
                        continue

                    if saved_start is not None and saved_count is not None \
                            and len(tiles) != int(saved_count):
                        print(f"    ! autotile #{local_id}: sheet tem {len(tiles)} "
                              f"tiles, JSON esperava {saved_count}. Normalizando.")

                    layer.add_autotile_tileset(
                        local_id=local_id,
                        sheet_path=found,
                        tiles=tiles,
                        cell_size=cell_size,
                        cols=cols,
                        rows=rows,
                        start_id=saved_start,
                        count=saved_count,
                    )
                    loaded_at += 1

                print(f"    Autotiles: {loaded_at}/{len(autotile_data)} sheet(s) "
                      f"carregado(s) (total tileset: {len(layer.tileset)})")

            self.layers.append(layer)

        print(f"\n=== GameLayerManager: {len(self.layers)} camadas ===\n")
        return self

    def _find_tileset_path(self, tileset_path, base_path, is_autotile=False):
        if not tileset_path:
            return None
        if os.path.isabs(tileset_path) and os.path.exists(tileset_path):
            return tileset_path

        basename = os.path.basename(tileset_path)
        possible = []

        if base_path:
            clean = tileset_path
            if clean.startswith('pkm-td/'):
                clean = clean[len('pkm-td/'):]
            if clean.startswith('pkm-td\\'):
                clean = clean[len('pkm-td\\'):]
            possible.append(os.path.join(base_path, clean))

        if is_autotile:
            possible.append(os.path.join("res", "AllTiles", "Autotile", basename))
            if base_path:
                possible.append(os.path.join(base_path, "res", "AllTiles", "Autotile", basename))

        possible.append(os.path.join("res", "AllTiles", basename))
        if base_path:
            possible.append(os.path.join(base_path, "res", "AllTiles", basename))
        possible.append(basename)

        for p in possible:
            n = os.path.normpath(p)
            if os.path.exists(n):
                return n
        return None

    # ==================================================================
    # RENDER — 3 passes por tipo (igual ao editor)
    # ==================================================================
    def render_ground_layers(self, screen, camera, screen_manager):
        for layer in self.layers:
            if layer.layer_type == "ground":
                layer.render(screen, camera, screen_manager)

    def render_decoration_layers(self, screen, camera, screen_manager):
        for layer in self.layers:
            if layer.layer_type == "decoration":
                layer.render(screen, camera, screen_manager)

    def render_ceiling_layers(self, screen, camera, screen_manager):
        for layer in self.layers:
            if layer.layer_type == "ceiling":
                layer.render(screen, camera, screen_manager)

    def render_all(self, screen, camera, screen_manager):
        self.render_ground_layers(screen, camera, screen_manager)
        self.render_decoration_layers(screen, camera, screen_manager)
        self.render_ceiling_layers(screen, camera, screen_manager)

    def get_dimensions(self):
        return (self.width * self.tile_size, self.height * self.tile_size)

    def invalidate_cache(self):
        for layer in self.layers:
            layer._invalidate_surface_cache()
            layer._cached_tiles.clear()