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

        # Shapes
        self.shape_active = False
        self.shape_tool = None
        self.shape_start = None
        self.shape_end = None

    # ==================================================================
    # HELPERS
    # ==================================================================
    def _get_current_tile_int(self):
        try:
            return int(self.editor.current_tile)
        except (ValueError, TypeError):
            return 1

    def _save_undo_state(self, action_description, continuous=False):
        if continuous:
            current_time = pygame.time.get_ticks() / 1000.0
            if current_time - self.last_undo_time < self.undo_cooldown:
                return False
            self.last_undo_time = current_time
        self.editor.undo_manager.save_state(self.editor, action_description)
        return True

    def _compute_tile_offset(self, world_pos, tile_x, tile_y):
        grid_size = self.editor.grid_size
        world_x, world_y = world_pos

        cell_center_x = tile_x * grid_size + grid_size // 2
        cell_center_y = tile_y * grid_size + grid_size // 2

        dx = int(round(world_x - cell_center_x))
        dy = int(round(world_y - cell_center_y))

        half = grid_size // 2
        dx = max(-half, min(half, dx))
        dy = max(-half, min(half, dy))

        dead_zone = max(1, grid_size // 8)
        if abs(dx) < dead_zone:
            dx = 0
        if abs(dy) < dead_zone:
            dy = 0

        return (dx, dy)

    # ==================================================================
    # ESTRUTURAS (NOVO)
    # ==================================================================
    def handle_structure_paste(self, world_pos, continuous=False):
        """
        Cola a estrutura carregada (self.editor.loaded_structure) na posição
        do mouse. Só executa em clique único (continuous=False) e com pincel.
        """
        if continuous:
            return  # só cola em clique único

        structure = getattr(self.editor, 'loaded_structure', None)
        if not structure:
            return

        tile_x = int(world_pos[0] // self.editor.grid_size)
        tile_y = int(world_pos[1] // self.editor.grid_size)

        # Verifica compatibilidade de camadas
        ok, msg = self.editor.structure_manager.check_can_paste(
            self.editor.layer_manager, structure
        )
        if not ok:
            print(f"[MapHandler] {msg}")
            return

        # Salva undo
        self._save_undo_state(
            f"Colar estrutura '{self.editor.loaded_structure_name}' em ({tile_x},{tile_y})"
        )

        # Aplica
        ok, msg = self.editor.structure_manager.apply_to_map(
            self.editor.layer_manager, structure, tile_x, tile_y
        )
        print(f"[MapHandler] {msg}")

    # ==================================================================
    # FLOOD FILL
    # ==================================================================
    def _flood_fill(self, layer, start_x, start_y, new_tile_id):
        try:
            new_tile_id = int(new_tile_id)
        except (ValueError, TypeError):
            new_tile_id = 0

        if not (0 <= start_x < layer.width and 0 <= start_y < layer.height):
            return 0

        target_tile = layer.get_tile(start_x, start_y)
        if target_tile == new_tile_id:
            return 0

        queue = deque()
        queue.append((start_x, start_y))
        processed = {(start_x, start_y)}
        count = 0

        while queue:
            x, y = queue.popleft()
            layer.set_tile(x, y, new_tile_id, offset=None)
            count += 1
            for nx, ny in ((x + 1, y), (x - 1, y), (x, y + 1), (x, y - 1)):
                if 0 <= nx < layer.width and 0 <= ny < layer.height:
                    if (nx, ny) not in processed and layer.get_tile(nx, ny) == target_tile:
                        queue.append((nx, ny))
                        processed.add((nx, ny))
        return count

    # ==================================================================
    # PATTERN MULTI-TILE
    # ==================================================================
    def _paint_pattern(self, pattern, anchor_x, anchor_y, layer, continuous=False):
        has_change = False
        for cell in pattern:
            tx = anchor_x + cell['dx']
            ty = anchor_y + cell['dy']
            if 0 <= tx < layer.width and 0 <= ty < layer.height:
                if layer.get_tile(tx, ty) != cell['tile_id']:
                    has_change = True
                    break
        if not has_change:
            return

        if continuous:
            if (anchor_x, anchor_y) == self.last_undo_tile:
                should_save = False
            else:
                self.last_undo_tile = (anchor_x, anchor_y)
                should_save = True
        else:
            should_save = True

        if should_save:
            self._save_undo_state(
                f"Pattern {len(pattern)} tiles em ({anchor_x}, {anchor_y})",
                continuous,
            )

        for cell in pattern:
            tx = anchor_x + cell['dx']
            ty = anchor_y + cell['dy']
            if 0 <= tx < layer.width and 0 <= ty < layer.height:
                self.editor.layer_manager.set_tile(tx, ty, cell['tile_id'], offset=None)

    # ==================================================================
    # SHAPES
    # ==================================================================
    def start_shape(self, tile_x, tile_y):
        brush = self.editor.brush_buttons.get_current_brush()
        if brush not in (self.editor.brush_buttons.BRUSH_LINE,
                         self.editor.brush_buttons.BRUSH_CIRCLE):
            return False
        self.shape_active = True
        self.shape_tool = brush
        self.shape_start = (tile_x, tile_y)
        self.shape_end = (tile_x, tile_y)
        return True

    def update_shape(self, tile_x, tile_y):
        if not self.shape_active:
            return False
        self.shape_end = (tile_x, tile_y)
        return True

    def cancel_shape(self):
        self.shape_active = False
        self.shape_tool = None
        self.shape_start = None
        self.shape_end = None

    def commit_shape(self):
        if not self.shape_active:
            return False
        current_layer = self.editor.layer_manager.get_current_layer()
        if not current_layer:
            self.cancel_shape(); return False

        tiles = self.get_shape_tiles()
        if not tiles:
            self.cancel_shape(); return False

        current_tile_int = self._get_current_tile_int()
        self._save_undo_state(
            f"Shape {self.shape_tool} ({len(tiles)} tiles)", continuous=False
        )

        for tx, ty in tiles:
            if 0 <= tx < current_layer.width and 0 <= ty < current_layer.height:
                self.editor.layer_manager.set_tile(tx, ty, current_tile_int, offset=None)

        self.cancel_shape()
        return True

    def get_shape_tiles(self):
        if not self.shape_active or not self.shape_start or not self.shape_end:
            return []
        x0, y0 = self.shape_start
        x1, y1 = self.shape_end
        if self.shape_tool == self.editor.brush_buttons.BRUSH_LINE:
            return self._get_line_tiles(x0, y0, x1, y1)
        if self.shape_tool == self.editor.brush_buttons.BRUSH_CIRCLE:
            dx, dy = x1 - x0, y1 - y0
            radius = int(round((dx * dx + dy * dy) ** 0.5))
            filled = self.editor.brush_buttons.is_circle_filled()
            return self._get_circle_tiles(x0, y0, radius, filled)
        return []

    def _get_line_tiles(self, x0, y0, x1, y1):
        tiles = []
        dx, dy = abs(x1 - x0), abs(y1 - y0)
        sx = 1 if x0 < x1 else -1
        sy = 1 if y0 < y1 else -1
        err = dx - dy
        x, y = x0, y0
        guard, mg = 0, dx + dy + 10
        while guard < mg:
            guard += 1
            tiles.append((x, y))
            if x == x1 and y == y1: break
            e2 = 2 * err
            if e2 > -dy:
                err -= dy; x += sx
            if e2 < dx:
                err += dx; y += sy
        return tiles

    def _get_circle_tiles(self, cx, cy, radius, filled=False):
        if radius < 0: return []
        if radius == 0: return [(cx, cy)]
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
        return list(tiles)

    # ==================================================================
    # BORRACHA
    # ==================================================================
    def get_eraser_tiles_at(self, tile_x, tile_y):
        brush = self.editor.brush_buttons
        shape = brush.get_eraser_shape()
        size = brush.get_eraser_size()
        tiles = []
        if shape == brush.ERASER_SQUARE:
            for dy in range(-size, size + 1):
                for dx in range(-size, size + 1):
                    tiles.append((tile_x + dx, tile_y + dy))
        else:
            for dy in range(-size, size + 1):
                for dx in range(-size, size + 1):
                    if dx * dx + dy * dy <= size * size:
                        tiles.append((tile_x + dx, tile_y + dy))
        return tiles

    def handle_erase(self, world_pos, continuous=False):
        tile_x = int(world_pos[0] // self.editor.grid_size)
        tile_y = int(world_pos[1] // self.editor.grid_size)
        current_layer = self.editor.layer_manager.get_current_layer()
        if not current_layer:
            return

        tiles = self.get_eraser_tiles_at(tile_x, tile_y)
        has_content = False
        for tx, ty in tiles:
            if 0 <= tx < current_layer.width and 0 <= ty < current_layer.height:
                if current_layer.get_tile(tx, ty) != 0:
                    has_content = True
                    break
        if not has_content:
            return

        should_save_undo = True
        if continuous:
            current_time = pygame.time.get_ticks() / 1000.0
            if current_time - self.last_undo_time < self.undo_cooldown:
                should_save_undo = False
            else:
                self.last_undo_time = current_time

        if should_save_undo:
            self._save_undo_state(
                f"Borracha ({len(tiles)} tiles) em ({tile_x}, {tile_y})",
                continuous=False,
            )

        for tx, ty in tiles:
            if 0 <= tx < current_layer.width and 0 <= ty < current_layer.height:
                if current_layer.get_tile(tx, ty) != 0:
                    self.editor.layer_manager.set_tile(tx, ty, 0, offset=None)

    # ==================================================================
    # LEFT CLICK
    # ==================================================================
    def handle_left_click(self, world_pos, continuous=False):
        if self.shape_active:
            return

        tile_x = int(world_pos[0] // self.editor.grid_size)
        tile_y = int(world_pos[1] // self.editor.grid_size)
        current_tile_pos = (tile_x, tile_y)

        current_layer = self.editor.layer_manager.get_current_layer()
        if not current_layer:
            return

        brush = self.editor.brush_buttons.get_current_brush()

        if brush in (self.editor.brush_buttons.BRUSH_LINE,
                     self.editor.brush_buttons.BRUSH_CIRCLE):
            return
        if brush == self.editor.brush_buttons.BRUSH_ERASER:
            return

        if self.editor.mode == "layers":
            # ===== PINCEL + ESTRUTURA CARREGADA → COLA =====
            if (brush == self.editor.brush_buttons.BRUSH_PENCIL
                    and getattr(self.editor, 'loaded_structure', None) is not None):
                self.handle_structure_paste(world_pos, continuous=False)
                return

            if 0 <= tile_x < current_layer.width and 0 <= tile_y < current_layer.height:

                if brush == self.editor.brush_buttons.BRUSH_PENCIL:
                    pattern = None
                    if hasattr(self.editor, 'tile_palette') and self.editor.tile_palette:
                        pattern = self.editor.tile_palette.get_current_brush_pattern()

                    if pattern:
                        self._paint_pattern(pattern, tile_x, tile_y, current_layer, continuous)
                    else:
                        current_tile_int = self._get_current_tile_int()

                        offset = (0, 0)
                        if not self.editor.brush_buttons.is_snap_enabled():
                            offset = self._compute_tile_offset(world_pos, tile_x, tile_y)

                        cur_tile = current_layer.get_tile(tile_x, tile_y)
                        cur_offset = current_layer.get_tile_offset(tile_x, tile_y)

                        if cur_tile != current_tile_int or cur_offset != offset:
                            should_save_undo = True
                            if continuous:
                                if current_tile_pos == self.last_undo_tile:
                                    should_save_undo = False
                                else:
                                    self.last_undo_tile = current_tile_pos
                            if should_save_undo:
                                self._save_undo_state(
                                    f"Tile {current_tile_int} em ({tile_x}, {tile_y})"
                                    + (f" offset={offset}" if offset != (0, 0) else ""),
                                    continuous,
                                )
                            self.editor.layer_manager.set_tile(
                                tile_x, tile_y, current_tile_int, offset
                            )

                elif brush == self.editor.brush_buttons.BRUSH_BUCKET and not continuous:
                    target_tile = current_layer.get_tile(tile_x, tile_y)
                    current_tile_int = self._get_current_tile_int()
                    if target_tile != current_tile_int:
                        self._save_undo_state(
                            f"Preenchimento em ({tile_x}, {tile_y}) com tile {current_tile_int}"
                        )
                        self._flood_fill(current_layer, tile_x, tile_y, current_tile_int)

        elif self.editor.mode == "path" and not continuous:
            current_path = self.editor.path_manager.get_current_path()
            if not current_path:
                if self.editor.path_manager.add_path():
                    current_path = self.editor.path_manager.get_current_path()
                else:
                    return
            if self.editor.snap_to_grid:
                x = tile_x * self.editor.grid_size + self.editor.grid_size // 2
                y = tile_y * self.editor.grid_size + self.editor.grid_size // 2
            else:
                x, y = world_pos
            self._save_undo_state(f"Path node em ({x:.0f}, {y:.0f})", continuous=False)
            current_path.add_node((x, y))

        elif self.editor.mode == "towers" and not continuous:
            if self.editor.snap_to_grid:
                x = tile_x * self.editor.grid_size
                y = tile_y * self.editor.grid_size
            else:
                x = world_pos[0] - 16
                y = world_pos[1] - 16
            existing_spot = self.editor.tower_spots.get_spot_at(x + 8, y + 8)
            if not existing_spot:
                self._save_undo_state(f"Tower spot em ({x:.0f}, {y:.0f})", continuous=False)
                self.editor.tower_spots.add_spot(x, y)

    # ==================================================================
    # RIGHT CLICK
    # ==================================================================
    def handle_right_click(self, world_pos):
        if self.shape_active:
            self.cancel_shape()
            return

        # Cancelar estrutura carregada com botão direito
        if getattr(self.editor, 'loaded_structure', None) is not None:
            self.editor.loaded_structure = None
            self.editor.loaded_structure_name = None
            print("[MapHandler] Estrutura descarregada")
            return

        tile_x = int(world_pos[0] // self.editor.grid_size)
        tile_y = int(world_pos[1] // self.editor.grid_size)
        current_tile_pos = (tile_x, tile_y)

        if not hasattr(self.editor, 'layer_manager'):
            return
        current_layer = self.editor.layer_manager.get_current_layer()
        if not current_layer:
            return

        continuous = False
        if hasattr(self.editor, 'input_handler'):
            continuous = getattr(self.editor.input_handler, 'erasing', False)

        if not hasattr(self.editor, 'brush_buttons'):
            return
        brush = self.editor.brush_buttons.get_current_brush()

        if self.editor.mode == "layers":
            if brush == self.editor.brush_buttons.BRUSH_BUCKET:
                if 0 <= tile_x < current_layer.width and 0 <= tile_y < current_layer.height:
                    target_tile = current_layer.get_tile(tile_x, tile_y)
                    if target_tile != 0:
                        self._save_undo_state(
                            f"Remover área de tile {target_tile} em ({tile_x}, {tile_y})"
                        )
                        self._flood_fill(current_layer, tile_x, tile_y, 0)
                return

            if brush == self.editor.brush_buttons.BRUSH_ERASER:
                self.handle_erase(world_pos, continuous=continuous)
                return

            if brush in (self.editor.brush_buttons.BRUSH_PENCIL,
                         self.editor.brush_buttons.BRUSH_LINE,
                         self.editor.brush_buttons.BRUSH_CIRCLE):
                if not (0 <= tile_x < current_layer.width and 0 <= tile_y < current_layer.height):
                    return
                if (current_layer.get_tile(tile_x, tile_y) != 0
                        or current_layer.get_tile_offset(tile_x, tile_y) != (0, 0)):
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
                    self.editor.layer_manager.set_tile(tile_x, tile_y, 0, offset=None)

        elif self.editor.mode == "path":
            current_path = self.editor.path_manager.get_current_path()
            if not current_path: return
            min_dist = float('inf'); node_to_remove = -1; pos_to_remove = None
            for i, node in enumerate(current_path.nodes):
                dist = ((node[0] - world_pos[0]) ** 2 + (node[1] - world_pos[1]) ** 2) ** 0.5
                if dist < 20 and dist < min_dist:
                    min_dist = dist; node_to_remove = i; pos_to_remove = node
            if node_to_remove >= 0:
                self._save_undo_state(
                    f"Remover path node {node_to_remove} em ({pos_to_remove[0]:.0f}, {pos_to_remove[1]:.0f})"
                )
                current_path.remove_node(node_to_remove)

        elif self.editor.mode == "towers":
            spot_to_remove = None; min_dist = float('inf'); spot_pos = None
            for spot in self.editor.tower_spots.spots:
                cx = spot.x + spot.size // 2; cy = spot.y + spot.size // 2
                dist = ((cx - world_pos[0]) ** 2 + (cy - world_pos[1]) ** 2) ** 0.5
                if dist < spot.size and dist < min_dist:
                    min_dist = dist; spot_to_remove = spot; spot_pos = (spot.x, spot.y)
            if spot_to_remove:
                self._save_undo_state(f"Remover tower spot em ({spot_pos[0]:.0f}, {spot_pos[1]:.0f})")
                self.editor.tower_spots.remove_spot(spot_to_remove)