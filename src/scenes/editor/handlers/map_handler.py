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
    # AUTOTILE — helpers
    # ==================================================================
    def _is_autotile_mode(self):
        """
        True apenas se:
          - estamos no modo layers
          - a paleta está visível
          - a aba AUTOTILES está ativa
          - há um autotile selecionado (selected_autotile_id > 0)
        """
        if self.editor.mode != "layers":
            return False
        pal = getattr(self.editor, 'tile_palette', None)
        if not pal or not pal.visible:
            return False

        tab = pal.get_active_tab()
        sel = pal.selected_autotile_id

        # Sync forçado
        self.editor.paint_mode = "autotile" if tab == "autotiles" else "tile"

        if tab != "autotiles":
            return False
        if sel <= 0:
            return False
        return True

    def _get_current_autotile_id(self):
        pal = getattr(self.editor, 'tile_palette', None)
        return pal.selected_autotile_id if pal else 0

    def _paint_autotile_at(self, tile_x, tile_y, continuous=False):
        """Pinta um autotile numa célula (com undo controlado por célula)."""
        layer = self.editor.layer_manager.get_current_layer()
        if not layer:
            return
        if not (0 <= tile_x < layer.width and 0 <= tile_y < layer.height):
            return

        local_id = self._get_current_autotile_id()
        if local_id <= 0:
            return

        # ===== AUTOTILE: garante que a layer tem o tileset registrado =====
        if self.editor._ensure_layer_has_all_autotiles(layer):
            self.editor._update_tile_palette_from_layer()

        # Se já tem o mesmo autotile aqui, nada muda
        if layer.autotile_ids[tile_y][tile_x] == local_id:
            return

        # Undo
        if continuous:
            if (tile_x, tile_y) == self.last_undo_tile:
                should = False
            else:
                self.last_undo_tile = (tile_x, tile_y)
                should = True
        else:
            should = True
        if should:
            self._save_undo_state(
                f"Autotile #{local_id} em ({tile_x},{tile_y})", continuous
            )

        layer.paint_autotile(tile_x, tile_y, local_id)

    def _flood_fill_autotile(self, layer, start_x, start_y, local_id):
        """Preenche a região conexa com o autotile."""
        if not (0 <= start_x < layer.width and 0 <= start_y < layer.height):
            print(f"[BALDE] fora do range ({start_x},{start_y})")
            return 0

        # ===== AUTOTILE: garante que a layer tem o tileset registrado =====
        if self.editor._ensure_layer_has_all_autotiles(layer):
            self.editor._update_tile_palette_from_layer()

        target = layer.autotile_ids[start_y][start_x]
        print(f"[BALDE] target={target} local_id={local_id}")

        if target == local_id:
            print(f"[BALDE] target == local_id — nada a fazer")
            return 0

        queue = deque()
        queue.append((start_x, start_y))
        processed = {(start_x, start_y)}
        count = 0

        while queue:
            x, y = queue.popleft()
            layer.paint_autotile(x, y, local_id)
            count += 1
            for nx, ny in ((x + 1, y), (x - 1, y), (x, y + 1), (x, y - 1)):
                if 0 <= nx < layer.width and 0 <= ny < layer.height:
                    if (nx, ny) not in processed and layer.autotile_ids[ny][nx] == target:
                        queue.append((nx, ny))
                        processed.add((nx, ny))

        print(f"[BALDE] terminou: {count} células")
        return count

    # ==================================================================
    # STAMP ATIVO (estrutura > pattern > single)
    # ==================================================================
    def _get_active_stamp(self):
        """
        Retorna (tipo, dados) do stamp ativo:
            ('structure', dict)   -> estrutura customizada carregada
            ('pattern',   list)   -> pattern composto do tile_palette
            (None,        None)   -> nenhum (fallback: tile único)
        Prioridade: estrutura > pattern > single.
        """
        if getattr(self.editor, 'loaded_structure', None) is not None:
            return ('structure', self.editor.loaded_structure)

        if getattr(self.editor, 'tile_palette', None) is not None:
            palette = self.editor.tile_palette
            if getattr(palette, 'selection_mode', 'single') == 'multi':
                pattern = palette.get_current_brush_pattern()
                if pattern:
                    return ('pattern', pattern)

        return (None, None)

    def _has_stamp(self):
        t, _ = self._get_active_stamp()
        return t is not None

    def _get_pattern_anchor_tile(self):
        """Retorna o tile_id 'âncora' do pattern (dx=0, dy=0) ou o primeiro."""
        if not getattr(self.editor, 'tile_palette', None):
            return None
        pattern = self.editor.tile_palette.get_current_brush_pattern()
        if not pattern:
            return None
        for cell in pattern:
            if cell['dx'] == 0 and cell['dy'] == 0:
                return cell['tile_id']
        return pattern[0]['tile_id']

    # ==================================================================
    # TAMANHO DO STAMP + PLANEJAMENTO DE ANCHORS
    # ==================================================================
    def _compute_stamp_size(self, stamp_type, stamp_data):
        """
        Retorna (pw, ph) — tamanho do stamp em tiles.
        Usado para espaçar anchors em linha/círculo.
        """
        if stamp_type == 'pattern':
            min_dx = min(c['dx'] for c in stamp_data)
            max_dx = max(c['dx'] for c in stamp_data)
            min_dy = min(c['dy'] for c in stamp_data)
            max_dy = max(c['dy'] for c in stamp_data)
            return (max_dx - min_dx + 1, max_dy - min_dy + 1)
        if stamp_type == 'structure':
            return (max(1, int(stamp_data.get('width', 1))),
                    max(1, int(stamp_data.get('height', 1))))
        return (1, 1)

    def _plan_stamp_placements(self, anchor_tiles, stamp_type, stamp_data):
        """
        Filtra anchors espaçando-os pelo tamanho do stamp.
        Um anchor é aceito somente se NÃO cair dentro do bbox de um
        stamp já planejado. Isso evita a sobreposição em linha/círculo
        (o bug do 'mosaico' de patterns).
        """
        if not anchor_tiles or stamp_type is None:
            return []

        pw, ph = self._compute_stamp_size(stamp_type, stamp_data)
        if pw <= 0 or ph <= 0:
            return []

        covered = set()
        placements = []

        for (tx, ty) in anchor_tiles:
            if (tx, ty) in covered:
                continue
            placements.append((tx, ty))
            for dy in range(ph):
                base = ty + dy
                for dx in range(pw):
                    covered.add((tx + dx, base))

        return placements

    # ==================================================================
    # APLICAÇÃO
    # ==================================================================
    def _apply_pattern_at(self, tx, ty, layer):
        """Aplica o pattern atual na posição (tx, ty). Sem undo (caller salva)."""
        if not getattr(self.editor, 'tile_palette', None):
            return
        pattern = self.editor.tile_palette.get_current_brush_pattern()
        if not pattern:
            return

        w, h = layer.width, layer.height
        set_tile = layer.set_tile
        for cell in pattern:
            cx = tx + cell['dx']
            cy = ty + cell['dy']
            if 0 <= cx < w and 0 <= cy < h:
                set_tile(cx, cy, cell['tile_id'], offset=None)

    def _apply_structure_at(self, tx, ty, structure):
        """Aplica a estrutura começando da camada selecionada."""
        start_layer_index = self.editor.layer_manager.current_layer
        self.editor.structure_manager.apply_to_map(
            self.editor.layer_manager, structure, tx, ty,
            start_layer_index=start_layer_index,
        )

    def _apply_single_tile_at(self, tx, ty, layer, offset=None):
        if 0 <= tx < layer.width and 0 <= ty < layer.height:
            self.editor.layer_manager.set_tile(tx, ty, self._get_current_tile_int(), offset)

    # ==================================================================
    # ESTRUTURAS (colar com pincel)
    # ==================================================================
    def handle_structure_paste(self, world_pos, continuous=False):
        if continuous:
            return
        structure = getattr(self.editor, 'loaded_structure', None)
        if not structure:
            return

        tile_x = int(world_pos[0] // self.editor.grid_size)
        tile_y = int(world_pos[1] // self.editor.grid_size)

        # ★ Camada inicial = a selecionada atualmente
        start_layer_index = self.editor.layer_manager.current_layer

        ok, msg = self.editor.structure_manager.check_can_paste(
            self.editor.layer_manager, structure,
            start_layer_index=start_layer_index,
        )
        if not ok:
            print(f"[MapHandler] {msg}")
            return

        self._save_undo_state(
            f"Colar '{self.editor.loaded_structure_name}' em "
            f"({tile_x},{tile_y}) a partir da camada {start_layer_index}"
        )
        ok, msg = self.editor.structure_manager.apply_to_map(
            self.editor.layer_manager, structure, tile_x, tile_y,
            start_layer_index=start_layer_index,
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
    # PATTERN MULTI-TILE (usado pelo pincel)
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
    def _get_rectangle_tiles(self, x0, y0, x1, y1, filled=True):
        """
        Retorna as células do retângulo definido por (x0,y0)-(x1,y1).
        Se filled=False, retorna apenas o contorno (perímetro).
        """
        min_x, max_x = min(x0, x1), max(x0, x1)
        min_y, max_y = min(y0, y1), max(y0, y1)

        tiles = []
        if filled:
            for y in range(min_y, max_y + 1):
                for x in range(min_x, max_x + 1):
                    tiles.append((x, y))
        else:
            # Borda superior e inferior
            for x in range(min_x, max_x + 1):
                tiles.append((x, min_y))
                if max_y != min_y:
                    tiles.append((x, max_y))
            # Laterais (sem repetir cantos)
            for y in range(min_y + 1, max_y):
                tiles.append((min_x, y))
                if max_x != min_x:
                    tiles.append((max_x, y))
        return tiles

    def start_shape(self, tile_x, tile_y):
        brush = self.editor.brush_buttons.get_current_brush()
        if brush not in (self.editor.brush_buttons.BRUSH_LINE,
                         self.editor.brush_buttons.BRUSH_CIRCLE,
                         self.editor.brush_buttons.BRUSH_RECTANGLE):
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

    # ------------------------------------------------------------------
    # COMMIT — com espaçamento de anchors por tamanho do stamp
    # ------------------------------------------------------------------
    def commit_shape(self):
        if not self.shape_active:
            return False

        current_layer = self.editor.layer_manager.get_current_layer()
        if not current_layer:
            self.cancel_shape()
            return False

        raw_tiles = self.get_shape_tiles()
        if not raw_tiles:
            self.cancel_shape()
            return False

        # ===== SHAPE COM AUTOTILE =====
        if self._is_autotile_mode():
            local_id = self._get_current_autotile_id()
            if local_id > 0:
                # ===== AUTOTILE: garante que a layer tem o tileset registrado =====
                if self.editor._ensure_layer_has_all_autotiles(current_layer):
                    self.editor._update_tile_palette_from_layer()

                self._save_undo_state(
                    f"Shape {self.shape_tool} autotile #{local_id} "
                    f"({len(raw_tiles)} células)"
                )
                for tx, ty in raw_tiles:
                    if 0 <= tx < current_layer.width and 0 <= ty < current_layer.height:
                        current_layer.paint_autotile(tx, ty, local_id)
                self.cancel_shape()
                return True

        stamp_type, stamp_data = self._get_active_stamp()

        # ===== Planejamento: anchors efetivamente usados (sem sobreposição) =====
        if stamp_type is not None:
            placements = self._plan_stamp_placements(
                raw_tiles, stamp_type, stamp_data
            )
        else:
            placements = raw_tiles

        if not placements:
            self.cancel_shape()
            return False

        # ===== Descrição de undo =====
        if stamp_type == 'pattern':
            desc = (f"Shape {self.shape_tool} com pattern "
                    f"({len(placements)} stamps de {len(raw_tiles)} anchors)")
        elif stamp_type == 'structure':
            name = getattr(self.editor, 'loaded_structure_name', '?')
            desc = (f"Shape {self.shape_tool} com '{name}' "
                    f"({len(placements)} stamps)")
        else:
            desc = f"Shape {self.shape_tool} ({len(placements)} tiles)"

        self._save_undo_state(desc, continuous=False)

        # ===== Aplicação =====
        if stamp_type == 'pattern':
            for tx, ty in placements:
                self._apply_pattern_at(tx, ty, current_layer)
        elif stamp_type == 'structure':
            for tx, ty in placements:
                self._apply_structure_at(tx, ty, stamp_data)
        else:
            for tx, ty in placements:
                if 0 <= tx < current_layer.width and 0 <= ty < current_layer.height:
                    self.editor.layer_manager.set_tile(
                        tx, ty, self._get_current_tile_int(), offset=None
                    )

        self.cancel_shape()
        return True

    def get_shape_tiles(self):
        """Anchors brutos da forma (Bresenham / círculo / retângulo)."""
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

        if self.shape_tool == self.editor.brush_buttons.BRUSH_RECTANGLE:
            filled = self.editor.brush_buttons.is_rectangle_filled()
            return self._get_rectangle_tiles(x0, y0, x1, y1, filled=filled)

        return []

    def get_shape_placement_tiles(self):
        """
        Anchors APÓS o espaçamento (o que será de fato aplicado no commit).
        Usado pela preview para mostrar o resultado real.
        """
        raw = self.get_shape_tiles()
        if not raw:
            return []
        stamp_type, stamp_data = self._get_active_stamp()
        if stamp_type is None:
            return raw
        return self._plan_stamp_placements(raw, stamp_type, stamp_data)

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
            if x == x1 and y == y1:
                break
            e2 = 2 * err
            if e2 > -dy:
                err -= dy
                x += sx
            if e2 < dx:
                err += dx
                y += sy
        return tiles

    def _get_circle_tiles(self, cx, cy, radius, filled=False):
        if radius < 0:
            return []
        if radius == 0:
            return [(cx, cy)]
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
        # Ordena por (y, x) para determinismo do espaçamento em círculos
        return sorted(tiles, key=lambda p: (p[1], p[0]))

    def _get_rectangle_tiles(self, x0, y0, x1, y1, filled=True):
        """
        Retorna as células do retângulo definido por (x0,y0)-(x1,y1).
        Se filled=False, retorna apenas o contorno (perímetro).
        """
        min_x, max_x = min(x0, x1), max(x0, x1)
        min_y, max_y = min(y0, y1), max(y0, y1)

        tiles = []
        if filled:
            for y in range(min_y, max_y + 1):
                for x in range(min_x, max_x + 1):
                    tiles.append((x, y))
        else:
            # Borda superior e inferior
            for x in range(min_x, max_x + 1):
                tiles.append((x, min_y))
                if max_y != min_y:
                    tiles.append((x, max_y))
            # Laterais (sem repetir cantos)
            for y in range(min_y + 1, max_y):
                tiles.append((min_x, y))
                if max_x != min_x:
                    tiles.append((max_x, y))
        return tiles

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
                if (current_layer.get_tile(tx, ty) != 0
                        or current_layer.autotile_ids[ty][tx] != 0):
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
                # Se é autotile, apaga como autotile
                if current_layer.autotile_ids[ty][tx] != 0:
                    current_layer.erase_autotile_at(tx, ty)
                elif current_layer.get_tile(tx, ty) != 0:
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

        # ===== DEBUG TEMPORÁRIO =====
        print(f"[CLICK] brush={brush} tile=({tile_x},{tile_y}) "
              f"cont={continuous} mode={self.editor.mode} "
              f"auto_mode={self._is_autotile_mode()} "
              f"local_id={self._get_current_autotile_id()}")

        if brush in (self.editor.brush_buttons.BRUSH_LINE,
                     self.editor.brush_buttons.BRUSH_CIRCLE):
            return
        if brush == self.editor.brush_buttons.BRUSH_ERASER:
            return

        if self.editor.mode == "layers":
            # ===== PINCEL =====
            if brush == self.editor.brush_buttons.BRUSH_PENCIL:
                # ===== AUTOTILE =====
                if self._is_autotile_mode():
                    self._paint_autotile_at(tile_x, tile_y, continuous)
                    return

                if getattr(self.editor, 'loaded_structure', None) is not None:
                    self.handle_structure_paste(world_pos, continuous=False)
                    return

                if not (0 <= tile_x < current_layer.width
                        and 0 <= tile_y < current_layer.height):
                    return

                pattern = None
                if getattr(self.editor, 'tile_palette', None):
                    pattern = self.editor.tile_palette.get_current_brush_pattern()

                if pattern:
                    self._paint_pattern(pattern, tile_x, tile_y,
                                        current_layer, continuous)
                    return

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

            # ===== BALDE =====
            elif brush == self.editor.brush_buttons.BRUSH_BUCKET and not continuous:
                print(f"[CLICK] >>> BALDE acionado")

                # ===== AUTOTILE: preenche área com o mesmo autotile =====
                if self._is_autotile_mode():
                    local_id = self._get_current_autotile_id()
                    print(f"[CLICK] >>> BALDE AUTOTILE #{local_id}")
                    if local_id > 0:
                        self._save_undo_state(
                            f"Balde autotile #{local_id} em ({tile_x},{tile_y})"
                        )
                        count = self._flood_fill_autotile(
                            current_layer, tile_x, tile_y, local_id
                        )
                        print(f"[CLICK] >>> BALDE pintou {count} células")
                    return

                # ===== BALDE DE TILE NORMAL =====
                stamp_type, _ = self._get_active_stamp()

                if stamp_type == 'pattern':
                    anchor = self._get_pattern_anchor_tile()
                    if anchor is None:
                        return
                    target_tile = current_layer.get_tile(tile_x, tile_y)
                    if target_tile != anchor:
                        self._save_undo_state(
                            f"Preencher com pattern (âncora {anchor}) em "
                            f"({tile_x}, {tile_y})"
                        )
                        self._flood_fill(current_layer, tile_x, tile_y, anchor)
                    return

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
            # Já existe um spot aqui?
            existing_idx = self.editor.tower_spots.get_spot_index_at(x + 8, y + 8)
            if existing_idx >= 0:
                # Seleciona (para editar tipagem, mover etc.)
                self.editor.tower_spots.selected_spot = existing_idx
                print(f"[Editor] Spot {existing_idx} selecionado. " f"Pressione T para editar tipos permitidos.")
            else:
                self._save_undo_state(f"Tower spot em ({x:.0f}, {y:.0f})", continuous=False)
                new_idx = self.editor.tower_spots.add_spot(x, y)
                self.editor.tower_spots.selected_spot = new_idx

    # ==================================================================
    # RIGHT CLICK
    # ==================================================================
    def handle_right_click(self, world_pos):
        if self.shape_active:
            self.cancel_shape()
            return

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
                # ===== AUTOTILE: remove área conexa =====
                if self._is_autotile_mode():
                    if 0 <= tile_x < current_layer.width and 0 <= tile_y < current_layer.height:
                        target_aid = current_layer.autotile_ids[tile_y][tile_x]
                        if target_aid != 0:
                            self._save_undo_state(
                                f"Remover área de autotile #{target_aid} em ({tile_x}, {tile_y})"
                            )
                            # flood fill "vazio" apaga autotile
                            queue = deque()
                            queue.append((tile_x, tile_y))
                            seen = {(tile_x, tile_y)}
                            while queue:
                                x, y = queue.popleft()
                                current_layer.erase_autotile_at(x, y)
                                for nx, ny in ((x+1, y), (x-1, y), (x, y+1), (x, y-1)):
                                    if 0 <= nx < current_layer.width and 0 <= ny < current_layer.height:
                                        if (nx, ny) not in seen and current_layer.autotile_ids[ny][nx] == target_aid:
                                            queue.append((nx, ny))
                                            seen.add((nx, ny))
                    return

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
                if not (0 <= tile_x < current_layer.width
                        and 0 <= tile_y < current_layer.height):
                    return
                # ===== AUTOTILE =====
                if current_layer.autotile_ids[tile_y][tile_x] != 0:
                    self._save_undo_state(
                        f"Remover autotile em ({tile_x}, {tile_y})", continuous
                    )
                    current_layer.erase_autotile_at(tile_x, tile_y)
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
                        self._save_undo_state(
                            f"Remover tile em ({tile_x}, {tile_y})", continuous
                        )
                    self.editor.layer_manager.set_tile(tile_x, tile_y, 0, offset=None)

        elif self.editor.mode == "path":
            current_path = self.editor.path_manager.get_current_path()
            if not current_path:
                return
            min_dist = float('inf')
            node_to_remove = -1
            pos_to_remove = None
            for i, node in enumerate(current_path.nodes):
                dist = ((node[0] - world_pos[0]) ** 2
                        + (node[1] - world_pos[1]) ** 2) ** 0.5
                if dist < 20 and dist < min_dist:
                    min_dist = dist
                    node_to_remove = i
                    pos_to_remove = node
            if node_to_remove >= 0:
                self._save_undo_state(
                    f"Remover path node {node_to_remove} em "
                    f"({pos_to_remove[0]:.0f}, {pos_to_remove[1]:.0f})"
                )
                current_path.remove_node(node_to_remove)

        elif self.editor.mode == "towers":
            spot_to_remove = None
            min_dist = float('inf')
            spot_pos = None
            for spot in self.editor.tower_spots.spots:
                cx = spot.x + spot.size // 2
                cy = spot.y + spot.size // 2
                dist = ((cx - world_pos[0]) ** 2 + (cy - world_pos[1]) ** 2) ** 0.5
                if dist < spot.size and dist < min_dist:
                    min_dist = dist
                    spot_to_remove = spot
                    spot_pos = (spot.x, spot.y)
            if spot_to_remove:
                self._save_undo_state(
                    f"Remover tower spot em ({spot_pos[0]:.0f}, {spot_pos[1]:.0f})"
                )
                self.editor.tower_spots.remove_spot(spot_to_remove)