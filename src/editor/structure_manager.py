# src/editor/structure_manager.py

"""
Gerenciador de Estruturas Customizadas (blocos prontos multi-camada).

Recursos:
  - Captura por máscara (retângulo/círculo, add/remove)
  - Salva metadados completos dos tilesets (tilesets_info) — permite
    remapear IDs ao colar em mapas com tilesets diferentes
  - Cache de tilesets em memória — usado para preview sem alterar o mapa
  - Ao colar: carrega tilesets ausentes do disco e remapeia IDs
  - Ao colar: IGNORA tiles vazios (tile_id == 0), preservando o
    conteúdo existente no destino (colagem aditiva)
"""
import json
import os
from pathlib import Path

import pygame

try:
    from src.config.paths import PROJECT_ROOT, RES_PATH
except ImportError:
    PROJECT_ROOT = ""
    RES_PATH = ""


class StructureManager:
    def __init__(self):
        if PROJECT_ROOT:
            self.base_path = Path(PROJECT_ROOT) / "res" / "AllTiles" / "Tilesets" / "CustomStructures"
        else:
            self.base_path = Path("res") / "AllTiles" / "Tilesets" / "CustomStructures"

        try:
            self.base_path.mkdir(parents=True, exist_ok=True)
        except Exception as e:
            print(f"[StructureManager] Erro ao criar pasta: {e}")

        self.structures = {}

        # ===== CACHES =====
        # (path, tile_size) -> pygame.Surface (sheet inteira)
        self._sheet_cache = {}
        # (path, tile_idx_0based, tile_size, cols, spacing) -> pygame.Surface
        self._tile_cache = {}

        self.reload()

        print(f"[StructureManager] Pasta: {self.base_path}")
        print(f"[StructureManager] {len(self.structures)} estrutura(s) carregada(s)")

    # ==================================================================
    # PERSISTÊNCIA
    # ==================================================================
    def reload(self):
        self.structures = {}
        if not self.base_path.exists():
            return
        for filepath in sorted(self.base_path.glob("*.json")):
            try:
                with open(filepath, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                name = data.get("name", filepath.stem)
                self.structures[name] = data
            except Exception as e:
                print(f"[StructureManager] Erro ao carregar {filepath.name}: {e}")

    def list_names(self):
        return sorted(self.structures.keys())

    def get(self, name):
        return self.structures.get(name)

    def has(self, name):
        return name in self.structures

    def save(self, name, structure_data):
        if not name:
            return False
        safe_name = "".join(c for c in name if c.isalnum() or c in "_- ").strip()
        if not safe_name:
            return False

        structure_data["name"] = safe_name
        filepath = self.base_path / f"{safe_name}.json"

        try:
            with open(filepath, 'w', encoding='utf-8') as f:
                json.dump(structure_data, f, indent=2, ensure_ascii=False)
            self.structures[safe_name] = structure_data
            print(f"[StructureManager] ✓ Estrutura '{safe_name}' salva")
            return True
        except Exception as e:
            print(f"[StructureManager] Erro ao salvar '{name}': {e}")
            return False

    def delete(self, name):
        if name not in self.structures:
            return False
        filepath = self.base_path / f"{name}.json"
        try:
            if filepath.exists():
                filepath.unlink()
            self.structures.pop(name, None)
            print(f"[StructureManager] Estrutura '{name}' removida")
            return True
        except Exception as e:
            print(f"[StructureManager] Erro ao remover '{name}': {e}")
            return False

    # ==================================================================
    # SHAPE HELPERS
    # ==================================================================
    @staticmethod
    def get_rect_cells(x0, y0, x1, y1):
        min_x, max_x = min(x0, x1), max(x0, x1)
        min_y, max_y = min(y0, y1), max(y0, y1)
        cells = set()
        for y in range(min_y, max_y + 1):
            for x in range(min_x, max_x + 1):
                cells.add((x, y))
        return cells

    @staticmethod
    def get_circle_cells(cx, cy, x1, y1, filled=True):
        dx = x1 - cx
        dy = y1 - cy
        radius = int(round((dx * dx + dy * dy) ** 0.5))

        if radius < 0:
            return set()
        if radius == 0:
            return {(cx, cy)}

        tiles = set()
        x, y = radius, 0
        err = 1 - radius
        while x >= y:
            for px, py in (
                (cx + x, cy + y), (cx - x, cy + y),
                (cx + x, cy - y), (cx - x, cy - y),
                (cx + y, cy + x), (cx - y, cy + x),
                (cx + y, cy - x), (cx - y, cy - x),
            ):
                tiles.add((px, py))
            y += 1
            if err < 0:
                err += 2 * y + 1
            else:
                x -= 1
                err += 2 * (y - x) + 1

        if filled:
            rows = {}
            for px, py in tiles:
                rows.setdefault(py, []).append(px)
            for py, xs in rows.items():
                for fx in range(min(xs), max(xs) + 1):
                    tiles.add((fx, py))

        return tiles

    @staticmethod
    def get_selection_bbox(mask):
        if not mask:
            return None
        xs = [p[0] for p in mask]
        ys = [p[1] for p in mask]
        return min(xs), min(ys), max(xs), max(ys)

    # ==================================================================
    # RESOLUÇÃO DE CAMINHOS
    # ==================================================================
    def _resolve_path(self, path):
        """Tenta resolver um caminho de tileset vindo do JSON."""
        if not path:
            return None

        if os.path.isabs(path):
            return path if os.path.exists(path) else None

        if PROJECT_ROOT:
            full = os.path.join(str(PROJECT_ROOT), path.replace('/', os.sep))
            if os.path.exists(full):
                return full

        if os.path.exists(path):
            return path

        basename = os.path.basename(path)
        if RES_PATH:
            try:
                candidate = Path(RES_PATH) / "AllTiles" / basename
                if candidate.exists():
                    return str(candidate)
            except Exception:
                pass

        if PROJECT_ROOT:
            candidate = os.path.join(str(PROJECT_ROOT), "res", "AllTiles", basename)
            if os.path.exists(candidate):
                return candidate

        return None

    @staticmethod
    def _normalize_tileset_key(path):
        if not path:
            return ''
        return os.path.basename(path).lower()

    # ==================================================================
    # TILESET CACHE (para preview)
    # ==================================================================
    def get_tileset_image(self, path, tile_size, spacing=0):
        key = (path, tile_size)
        if key in self._sheet_cache:
            return self._sheet_cache[key]

        full = self._resolve_path(path)
        if not full or not os.path.exists(full):
            self._sheet_cache[key] = None
            return None

        try:
            img = pygame.image.load(full).convert_alpha()
        except Exception as e:
            print(f"[StructureManager] Erro ao carregar sheet '{path}': {e}")
            self._sheet_cache[key] = None
            return None

        self._sheet_cache[key] = img
        return img

    def get_tile_surface(self, path, tile_idx_0based, tile_size, cols, spacing=0):
        key = (path, tile_idx_0based, tile_size, cols, spacing)
        if key in self._tile_cache:
            return self._tile_cache[key]

        sheet = self.get_tileset_image(path, tile_size, spacing)
        if sheet is None or cols <= 0:
            self._tile_cache[key] = None
            return None

        step = tile_size + spacing
        r = tile_idx_0based // cols
        c = tile_idx_0based % cols

        rect = pygame.Rect(c * step, r * step, tile_size, tile_size)
        if rect.right > sheet.get_width() or rect.bottom > sheet.get_height():
            self._tile_cache[key] = None
            return None

        try:
            surf = sheet.subsurface(rect).copy()
        except Exception:
            self._tile_cache[key] = None
            return None

        self._tile_cache[key] = surf
        return surf

    @staticmethod
    def _find_tileset_for_tile(tilesets_info, tile_id_1based):
        cumulative = 0
        for ts in tilesets_info:
            count = int(ts.get('count', 0))
            if tile_id_1based <= cumulative + count:
                return ts, tile_id_1based - 1 - cumulative
            cumulative += count
        return None, None

    def get_tile_surface_for_structure(self, tilesets_info, tile_id_1based, target_size):
        if not tilesets_info or tile_id_1based <= 0:
            return None

        ts_info, local_idx = self._find_tileset_for_tile(tilesets_info, tile_id_1based)
        if ts_info is None:
            return None

        path = ts_info.get('path')
        cols = ts_info.get('cols', 1) or 1
        spacing = int(ts_info.get('spacing', 0) or 0)
        native = int(ts_info.get('tile_width')
                     or ts_info.get('tile_height')
                     or ts_info.get('tile_size')
                     or 16)

        surf = self.get_tile_surface(path, local_idx, native, cols, spacing)
        if surf is None:
            return None

        if surf.get_width() != target_size or surf.get_height() != target_size:
            return pygame.transform.scale(surf, (target_size, target_size))
        return surf

    def clear_cache(self):
        self._sheet_cache.clear()
        self._tile_cache.clear()

    # ==================================================================
    # CAPTURA POR MÁSCARA
    # ==================================================================
    def capture_from_mask(self, layer_manager, mask, only_visible=True):
        if not mask:
            return None

        bbox = self.get_selection_bbox(mask)
        if bbox is None:
            return None
        min_x, min_y, max_x, max_y = bbox
        w = max_x - min_x + 1
        h = max_y - min_y + 1

        structure = {
            "width": int(w),
            "height": int(h),
            "tile_size": layer_manager.tile_size,
            "layers": [],
        }

        # ===== MÁSCARA (shape exato) =====
        # mask_grid[dy][dx] = 1 se célula pertence à seleção
        mask_grid = []
        for dy in range(h):
            row = []
            for dx in range(w):
                row.append(1 if (min_x + dx, min_y + dy) in mask else 0)
            mask_grid.append(row)
        structure["mask"] = mask_grid

        # ===== CAMADAS =====
        for layer in layer_manager.layers:
            if only_visible and not getattr(layer, 'visible', True):
                continue

            layer_type_val = (layer.layer_type.value
                              if hasattr(layer.layer_type, 'value')
                              else str(layer.layer_type))

            layer_data = {
                "name": layer.name,
                "type": layer_type_val,
                "tiles": [],
                "tile_offsets": {},
                "tileset_paths": list(getattr(layer, 'tileset_paths', []) or []),
                "tilesets_info": [],
                "visible": True,
                "opacity": getattr(layer, 'opacity', 255),
            }

            # ===== METADADOS COMPLETOS DOS TILESETS =====
            for ts in getattr(layer, 'tilesets', []) or []:
                try:
                    layer_data["tilesets_info"].append({
                        "path": ts.get('path', ''),
                        "count": int(ts.get('count', 0)),
                        "cols": int(ts.get('cols', 1) or 1),
                        "rows": int(ts.get('rows', 1) or 1),
                        "tile_width": int(ts.get('tile_width', layer.tile_size)),
                        "tile_height": int(ts.get('tile_height', layer.tile_size)),
                        "spacing": int(ts.get('spacing', 0) or 0),
                    })
                except Exception:
                    continue

            # ===== TILES =====
            for dy in range(h):
                row = []
                for dx in range(w):
                    sx = min_x + dx
                    sy = min_y + dy
                    if (sx, sy) in mask and 0 <= sx < layer.width and 0 <= sy < layer.height:
                        tile_id = layer.get_tile(sx, sy)
                        row.append(int(tile_id))
                        off = layer.get_tile_offset(sx, sy)
                        if off and off != (0, 0):
                            layer_data["tile_offsets"][f"{dx},{dy}"] = [int(off[0]), int(off[1])]
                    else:
                        row.append(0)
                layer_data["tiles"].append(row)

            structure["layers"].append(layer_data)

        return structure

    # ==================================================================
    # COLAGEM — compatibilidade
    # ==================================================================
    def check_can_paste(self, layer_manager, structure, start_layer_index=None):
        """
        Verifica se dá pra colar a estrutura a partir da camada
        `start_layer_index` (default = layer_manager.current_layer).
        """
        if not structure:
            return False, "Nenhuma estrutura carregada"

        need = len(structure.get("layers", []))
        have = len(layer_manager.layers)

        if start_layer_index is None:
            start_layer_index = getattr(layer_manager, 'current_layer', 0)

        start_layer_index = max(0, int(start_layer_index))

        if start_layer_index + need > have:
            disponiveis = have - start_layer_index
            return False, (
                f"Precisa de {need} camada(s) a partir do index {start_layer_index}, "
                f"mas só há {disponiveis} disponível(is) (total: {have}). "
                f"Selecione uma camada mais baixa ou adicione mais camadas."
            )
        return True, "OK"

    # ==================================================================
    # COLAGEM — carregar tilesets faltantes + remapear IDs
    # ==================================================================
    def _add_tileset_to_layer(self, target_layer, struct_ts):
        path = struct_ts.get('path')
        full = self._resolve_path(path)
        if not full:
            print(f"[StructureManager] Tileset não encontrado: {path}")
            return None

        tile_w = int(struct_ts.get('tile_width') or target_layer.tile_size or 16)
        tile_h = int(struct_ts.get('tile_height') or target_layer.tile_size or 16)
        spacing = int(struct_ts.get('spacing', 0) or 0)

        ok = target_layer.add_tileset_from_image(full, tile_w, tile_h, spacing)
        if not ok or not target_layer.tilesets:
            print(f"[StructureManager] Falha ao adicionar tileset: {path}")
            return None

        return target_layer.tilesets[-1]

    def _ensure_tilesets_and_build_id_map(self, target_layer, struct_layer):
        struct_infos = struct_layer.get('tilesets_info', []) or []

        if not struct_infos:
            return {}

        existing_by_key = {}
        for ts in target_layer.tilesets:
            key = self._normalize_tileset_key(ts.get('path', ''))
            if key:
                existing_by_key[key] = ts

        id_map = {}
        struct_cursor = 0

        for struct_ts in struct_infos:
            count = int(struct_ts.get('count', 0))
            if count <= 0:
                continue

            struct_start = struct_cursor + 1
            path = struct_ts.get('path')
            key = self._normalize_tileset_key(path)

            target_ts = existing_by_key.get(key) if key else None

            if target_ts is None:
                target_ts = self._add_tileset_to_layer(target_layer, struct_ts)
                if target_ts:
                    existing_by_key[key] = target_ts

            if target_ts:
                target_start = int(target_ts.get('start_id', 1))
                target_count = int(target_ts.get('count', 0))
                mapped = min(count, target_count)
                for i in range(mapped):
                    id_map[struct_start + i] = target_start + i

            struct_cursor += count

        return id_map

    # ==================================================================
    # APLICAR AO MAPA — com colagem ADITIVA (ignora tiles vazios)
    # ==================================================================
    def apply_to_map(self, layer_manager, structure, anchor_x, anchor_y,
                     start_layer_index=None):
        """
        Cola a estrutura a partir da camada `start_layer_index`
        (default = camada atualmente selecionada no editor).
        A camada 0 da estrutura vai para `start_layer_index`,
        a camada 1 para `start_layer_index + 1`, e assim por diante.

        Tiles vazios são IGNORADOS (colagem aditiva), preservando o
        conteúdo existente no destino.
        """
        if not structure:
            return False, "Estrutura inválida"

        struct_layers = structure.get("layers", [])
        width = int(structure.get("width", 0))
        height = int(structure.get("height", 0))
        mask_grid = structure.get("mask")  # opcional

        if width <= 0 or height <= 0:
            return False, "Dimensões inválidas"

        if start_layer_index is None:
            start_layer_index = getattr(layer_manager, 'current_layer', 0)

        start_layer_index = max(0, int(start_layer_index))
        have = len(layer_manager.layers)
        need = len(struct_layers)

        # ===== Bounds considerando o offset =====
        if start_layer_index + need > have:
            disponiveis = have - start_layer_index
            return False, (
                f"Precisa de {need} camada(s) a partir do index {start_layer_index}, "
                f"mas só há {disponiveis} disponível(is) (total: {have})"
            )

        total_added_tilesets = 0
        total_pasted = 0
        total_skipped_empty = 0

        for local_idx, struct_layer in enumerate(struct_layers):
            target_layer_idx = start_layer_index + local_idx
            target_layer = layer_manager.layers[target_layer_idx]

            before = len(target_layer.tilesets)
            id_map = self._ensure_tilesets_and_build_id_map(target_layer, struct_layer)
            added = len(target_layer.tilesets) - before
            if added > 0:
                total_added_tilesets += added
                print(f"[StructureManager] Camada '{target_layer.name}' "
                      f"(index {target_layer_idx}): +{added} tileset(s)")

            tiles = struct_layer.get("tiles", []) or []
            offsets = struct_layer.get("tile_offsets", {}) or {}

            tw = target_layer.width
            th = target_layer.height
            set_tile = target_layer.set_tile

            for dy in range(height):
                row = tiles[dy] if dy < len(tiles) else []

                for dx in range(width):
                    in_mask = True
                    if mask_grid and dy < len(mask_grid) and dx < len(mask_grid[dy]):
                        in_mask = bool(mask_grid[dy][dx])
                    if not in_mask:
                        continue

                    tid = row[dx] if dx < len(row) else 0
                    try:
                        tid_int = int(tid)
                    except (ValueError, TypeError):
                        continue

                    # ===== Colagem aditiva: ignora vazios =====
                    if tid_int == 0:
                        total_skipped_empty += 1
                        continue

                    new_id = id_map.get(tid_int, tid_int)

                    tx = anchor_x + dx
                    ty = anchor_y + dy
                    if 0 <= tx < tw and 0 <= ty < th:
                        off = offsets.get(f"{dx},{dy}")
                        offset_tuple = (int(off[0]), int(off[1])) if off else None
                        set_tile(tx, ty, new_id, offset=offset_tuple)
                        total_pasted += 1

        msg = (f"Estrutura colada ({width}x{height}, {need} camadas "
               f"em {start_layer_index}..{start_layer_index + need - 1}, "
               f"{total_pasted} tiles")
        if total_skipped_empty:
            msg += f", {total_skipped_empty} vazios ignorados"
        if total_added_tilesets:
            msg += f", +{total_added_tilesets} tileset(s)"
        msg += ")"
        return True, msg