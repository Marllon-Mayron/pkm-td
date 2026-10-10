# src/utils/map_renderer.py
"""
Renderiza o mapa de uma fase (JSON) num pygame.Surface ou PNG.

Replica EXATAMENTE o comportamento do GameLayerManager do jogo:

  - tileset comum: carregado por `tileset_paths` (na ordem).
    Fallback pra `res/AllTiles/<basename>` se o path literal não existir.
  - tile_id 0   → vazio.
  - tile_id N   → subsurf em (N-1) % cols, (N-1) // cols (row-major).
  - autotile_tilesets NÃO são usados no runtime — são só metadados do
    editor. Aqui ignoramos também.
  - tile_offsets  aplicados em PIXELS (não em tiles).
  - ordem de render: ground → decoration → ceiling (por tipo de layer).

Uso runtime:
    surf = load_level_map("res/maps/level_01_01_01.json")

Uso CLI:
    python -m scripts.build_map_png <json> [--scale N] [--out <png>]
"""
import json
import os
import pygame
from pathlib import Path
from typing import Optional

from src.config.paths import PROJECT_ROOT


TILE_SIZE_DEFAULT = 16

# Ordem de render por tipo de layer (o game_scene chama nessa ordem)
TYPE_ORDER = {"ground": 0, "decoration": 1, "ceiling": 2}

# Cache de sheets: (path_str, tile_size) → _Sheet ou None
_SHEET_CACHE: dict = {}
# Cache de mapas renderizados: (level_path, tile_size) → Surface
_MAP_CACHE: dict = {}


# =====================================================================
# SHEET
# =====================================================================
class _Sheet:
    """
    Tileset comum: PNG fatiado em cols×rows de tile_size.

    Como o game_layer_manager, `cols = img_w // tile_size` e
    `rows = img_h // tile_size`, e os tiles são ordenados em row-major:
      índice 0 → (col 0, row 0)
      índice 1 → (col 1, row 0)
      ...
      índice cols → (col 0, row 1)
    """
    __slots__ = ("surface", "cols", "rows", "tile_size", "path_str")

    def __init__(self, surface, tile_size, path_str):
        self.surface = surface
        self.tile_size = int(tile_size)
        w, h = surface.get_size()
        self.cols = max(1, w // self.tile_size)
        self.rows = max(1, h // self.tile_size)
        self.path_str = path_str

    @property
    def total(self):
        return self.cols * self.rows

    def blit_tile(self, target, tile_id_one_based, x, y):
        """
        Blit tile (1-indexed, como o runtime) em (x, y) do target.
        Retorna True se desenhou.
        """
        idx = int(tile_id_one_based) - 1
        if idx < 0 or idx >= self.total:
            return False
        c = idx % self.cols
        r = idx // self.cols
        rect = pygame.Rect(
            c * self.tile_size,
            r * self.tile_size,
            self.tile_size,
            self.tile_size,
        )
        # Não estoura a sheet
        if (rect.right > self.surface.get_width()
                or rect.bottom > self.surface.get_height()):
            return False
        target.blit(self.surface, (x, y), rect)
        return True


# =====================================================================
# RESOLUÇÃO DE PATHS
# =====================================================================
def _resolve_json_path(p) -> Optional[Path]:
    """Aceita absoluto, relativo a PROJECT_ROOT, ou só o nome."""
    if p is None:
        return None
    raw = str(p).strip().strip('"').strip("'")
    if not raw:
        return None
    if not raw.lower().endswith(".json"):
        raw_ext = raw + ".json"
    else:
        raw_ext = raw

    pth = Path(raw_ext)
    if pth.is_absolute() and pth.exists():
        return pth

    # relativo a PROJECT_ROOT
    for rel in (raw_ext, raw):
        cand = PROJECT_ROOT / rel
        if cand.exists():
            return cand

    # procura em src/data/minigames/general_maps/
    for base_rel in ("src/data/minigames/general_maps",
                     "res/maps", "res/json"):
        for rel in (raw_ext, raw):
            cand = PROJECT_ROOT / base_rel / rel
            if cand.exists():
                return cand

    # busca recursiva pelo nome
    name = Path(raw_ext).name
    for base_rel in ("src/data/minigames",
                     "src/data", "res"):
        base = PROJECT_ROOT / base_rel
        if not base.exists():
            continue
        found = list(base.rglob(name))
        if found:
            return found[0]
    return None


def _find_tileset_path(tileset_path: str, base_path: Path) -> Optional[Path]:
    """
    Replica GameLayerManager._find_tileset_path:
      1) base_path + clean  (com "pkm-td/" removido do começo)
      2) res/AllTiles/<basename>
      3) base_path + res/AllTiles/<basename>
      4) <basename>
    """
    if not tileset_path:
        return None

    basename = os.path.basename(tileset_path)
    candidates = []

    clean = tileset_path
    if clean.startswith("pkm-td/"):
        clean = clean[len("pkm-td/"):]
    if clean.startswith("pkm-td\\"):
        clean = clean[len("pkm-td\\"):]

    candidates.append(base_path / clean)
    candidates.append(Path("res") / "AllTiles" / basename)
    candidates.append(base_path / "res" / "AllTiles" / basename)
    candidates.append(Path(basename))

    for c in candidates:
        try:
            n = Path(os.path.normpath(str(c)))
        except Exception:
            continue
        if n.exists():
            return n
    return None


# =====================================================================
# CARREGAR SHEET
# =====================================================================
def _load_sheet(path_str: str,
                tile_size: int,
                base_path: Path = PROJECT_ROOT) -> Optional[_Sheet]:
    key = (path_str, tile_size)
    if key in _SHEET_CACHE:
        return _SHEET_CACHE[key]

    found = _find_tileset_path(path_str, base_path)
    if found is None or not found.exists():
        print(f"[MAP_RENDER] tileset não encontrado: {path_str}")
        _SHEET_CACHE[key] = None
        return None

    try:
        surf = pygame.image.load(str(found)).convert_alpha()
    except Exception as e:
        print(f"[MAP_RENDER] erro tileset {found}: {e}")
        _SHEET_CACHE[key] = None
        return None

    sheet = _Sheet(surf, tile_size, path_str)
    print(f"[MAP_RENDER] sheet '{found.name}': "
          f"{surf.get_width()}x{surf.get_height()} → "
          f"{sheet.cols}x{sheet.rows} = {sheet.total} tiles")
    _SHEET_CACHE[key] = sheet
    return sheet


# =====================================================================
# RENDER DE UMA LAYER
# =====================================================================
def _render_layer(canvas: pygame.Surface,
                  layer_data: dict,
                  tile_size: int,
                  base_path: Path):
    # ---- Sheets (tileset_paths plural, com fallback singular) ----
    paths = []
    if layer_data.get("tileset_paths"):
        paths = list(layer_data["tileset_paths"])
    elif layer_data.get("tileset_path"):
        paths = [layer_data["tileset_path"]]

    sheets = []
    for p in paths:
        s = _load_sheet(p, tile_size, base_path)
        if s is not None:
            sheets.append(s)

    if not sheets:
        return

    # ---- Range de IDs por sheet (1-indexed) ----
    # O runtime empilha os tilesets: `next_start = len(tileset) + 1`.
    # Ex.: 1 sheetset de 512 tiles → ids válidos 1..512.
    #      2 sheetsets de 512 e 200   → 1..512 e 513..712.
    ranges = []          # (lo, hi, sheet)
    running = 1
    for s in sheets:
        ranges.append((running, running + s.total - 1, s))
        running += s.total

    # ---- Tiles ----
    layer_tiles = layer_data.get("tiles") or []
    w = int(layer_data.get("width", len(layer_tiles[0]) if layer_tiles else 0))
    h = int(layer_data.get("height", len(layer_tiles)))

    # ---- Offsets (chave "x,y" → [dx, dy] em PIXELS) ----
    offsets = {}
    for k, off in (layer_data.get("tile_offsets") or {}).items():
        try:
            xs, ys = str(k).split(",")
            offsets[(int(xs), int(ys))] = (int(off[0]), int(off[1]))
        except (ValueError, IndexError, TypeError):
            continue

    # ---- Blit ----
    for y in range(min(h, len(layer_tiles))):
        row = layer_tiles[y] if y < len(layer_tiles) else []
        for x in range(min(w, len(row))):
            try:
                tid = int(row[x])
            except (ValueError, TypeError):
                tid = 0
            if tid == 0:
                continue

            # Acha o sheet pra esse tile_id
            target = None
            for lo, hi, s in ranges:
                if lo <= tid <= hi:
                    target = (s, tid - lo + 1)   # id LOCAL no sheetset
                    break
            if target is None:
                continue

            s, local_id = target
            dx, dy = offsets.get((x, y), (0, 0))
            s.blit_tile(canvas, local_id,
                        x * tile_size + dx,
                        y * tile_size + dy)


# =====================================================================
# API PRINCIPAL
# =====================================================================
def load_level_map(level_path,
                   tile_size: int = TILE_SIZE_DEFAULT,
                   background_color=(0, 0, 0, 0),
                   use_cache: bool = True) -> Optional[pygame.Surface]:
    """
    Lê o JSON da fase, monta o mapa num Surface e devolve.
    Respeita a ordem de render do runtime: ground → decoration → ceiling.
    """
    p = _resolve_json_path(level_path)
    if p is None or not p.exists():
        print(f"[MAP_RENDER] fase não encontrada: {level_path}")
        return None

    if use_cache:
        key = (str(p), tile_size, tuple(background_color))
        if key in _MAP_CACHE:
            return _MAP_CACHE[key]

    with open(p, "r", encoding="utf-8") as f:
        data = json.load(f)

    map_data = data.get("map", {})
    raw_layers = map_data.get("layers", []) or []
    if not raw_layers:
        print(f"[MAP_RENDER] sem layers em {p}")
        return None

    # Dimensões do canvas
    first = raw_layers[0]
    w_tiles = int(first.get("width", 10))
    h_tiles = int(first.get("height", 9))
    tile_size = int(first.get("tile_size", tile_size))

    canvas = pygame.Surface(
        (w_tiles * tile_size, h_tiles * tile_size),
        pygame.SRCALPHA,
    )
    canvas.fill(background_color)

    # Ordena por TIPO (ground → decoration → ceiling), estável
    layers_sorted = sorted(
        raw_layers,
        key=lambda L: TYPE_ORDER.get(L.get("type", "ground"), 99),
    )

    for layer in layers_sorted:
        _render_layer(canvas, layer, tile_size, PROJECT_ROOT)

    if use_cache:
        _MAP_CACHE[(str(p), tile_size, tuple(background_color))] = canvas
    return canvas


def save_map_png(level_path,
                 output_path,
                 tile_size: int = TILE_SIZE_DEFAULT,
                 scale: int = 1) -> bool:
    """Renderiza o mapa e salva como PNG. Retorna True se deu certo."""
    surf = load_level_map(level_path, tile_size)
    if surf is None:
        return False

    # Fator inteiro pra preservar pixel perfect
    if scale != 1:
        w, h = surf.get_size()
        surf = pygame.transform.scale(surf, (w * scale, h * scale))

    out = Path(output_path)
    if not out.is_absolute():
        out = PROJECT_ROOT / str(output_path)
    out.parent.mkdir(parents=True, exist_ok=True)

    try:
        pygame.image.save(surf, str(out))
    except Exception as e:
        print(f"[MAP_RENDER] erro ao salvar {out}: {e}")
        return False

    print(f"[MAP_RENDER] {out}  ({surf.get_width()}x{surf.get_height()})")
    return True


def invalidate_cache():
    _SHEET_CACHE.clear()
    _MAP_CACHE.clear()