# src/editor/autotile_system.py

"""
Sistema de autotile 47-tile (blob tileset) para o editor.

- Carrega automaticamente todos os `autotile_*.png` de res/AllTiles/Autotile/
- Cada sheet é 8x6 células (16x16 nativas, com auto-detecção de 32/48/64)
- Converte máscaras de 8 bits em posições no sheet
- Aplica a regra "diagonal só vale se ambos os lados existirem"
"""

import os
import glob
import pygame

from src.editor.autotile_layout import ORDER, is_normal, is_variant

SHEET_COLS = 8
SHEET_ROWS = 6

# Bits do vizinho (N, NE, E, SE, S, SW, W, NW)
DIRS = [
    ( 0, -1,   1),  # N
    ( 1, -1,   2),  # NE
    ( 1,  0,   4),  # E
    ( 1,  1,   8),  # SE
    ( 0,  1,  16),  # S
    (-1,  1,  32),  # SW
    (-1,  0,  64),  # W
    (-1, -1, 128),  # NW
]


def canonical(mask):
    """Remove diagonais inválidas, retornando uma das 47 máscaras canônicas."""
    n  = mask & 1;  ne = (mask >> 1) & 1
    e  = (mask >> 2) & 1;  se = (mask >> 3) & 1
    s  = (mask >> 4) & 1;  sw = (mask >> 5) & 1
    w  = (mask >> 6) & 1;  nw = (mask >> 7) & 1
    if ne and not (n and e): ne = 0
    if se and not (s and e): se = 0
    if sw and not (s and w): sw = 0
    if nw and not (n and w): nw = 0
    return n | (ne << 1) | (e << 2) | (se << 3) | (s << 4) | (sw << 5) | (w << 6) | (nw << 7)


def build_mask_to_pos():
    """mask -> (col, row). Só entradas normais (as 47 canônicas)."""
    pos = {}
    for idx, entry in enumerate(ORDER):
        if not is_normal(entry):
            continue
        col = idx % SHEET_COLS
        row = idx // SHEET_COLS
        pos[entry] = (col, row)
    return pos


MASK_TO_POS = build_mask_to_pos()


class AutotileSheet:
    """Representa um único arquivo autotile_*.png (8x6 células)."""

    def __init__(self, path, name=None):
        self.path = path
        self.name = name or os.path.splitext(os.path.basename(path))[0]
        self.sheet = None
        self.cell_size = 16
        self.cols = SHEET_COLS
        self.rows = SHEET_ROWS
        self.tiles = []  # 48 surfaces (linha x coluna, na ordem do ORDER)

    def load(self):
        if not os.path.exists(self.path):
            print(f"[AutotileSheet] não encontrado: {self.path}")
            return False
        try:
            self.sheet = pygame.image.load(self.path).convert_alpha()
        except Exception as e:
            print(f"[AutotileSheet] erro ao carregar {self.path}: {e}")
            return False

        w, h = self.sheet.get_size()
        # auto-detecção do tamanho da célula
        for cs in (16, 32, 48, 64):
            if w >= SHEET_COLS * cs and h >= SHEET_ROWS * cs:
                self.cell_size = cs
                break

        self.tiles = []
        for r in range(self.rows):
            for c in range(self.cols):
                rect = pygame.Rect(c * self.cell_size, r * self.cell_size,
                                   self.cell_size, self.cell_size)
                if rect.right > w or rect.bottom > h:
                    empty = pygame.Surface((self.cell_size, self.cell_size),
                                           pygame.SRCALPHA)
                    self.tiles.append(empty)
                else:
                    self.tiles.append(self.sheet.subsurface(rect).copy())
        return True

    def index_for_mask(self, mask):
        """Retorna o índice (0..47) do tile correspondente à máscara."""
        cm = canonical(mask)
        pos = MASK_TO_POS.get(cm)
        if pos is None:
            return None
        col, row = pos
        return row * self.cols + col

    def surface_for_mask(self, mask):
        idx = self.index_for_mask(mask)
        if idx is None or idx >= len(self.tiles):
            return None
        return self.tiles[idx]


class AutotileManager:
    """
    Carrega todos os `autotile_*.png` de `res/AllTiles/Autotile/`.
    Cada sheet recebe um `local_id` (1-based) único.
    """
    FOLDER = "Autotile"
    PREFIX = "autotile_"

    def __init__(self, all_tiles_path):
        self.all_tiles_path = str(all_tiles_path)
        self.folder_path = os.path.join(self.all_tiles_path, self.FOLDER)
        self.sheets = []
        self.by_local_id = {}
        self._cache_preview = {}

    def load_all(self):
        """Varre a pasta e carrega todos os sheets válidos."""
        self.sheets = []
        self.by_local_id = {}
        self._cache_preview.clear()

        if not os.path.isdir(self.folder_path):
            print(f"[AutotileManager] pasta inexistente: {self.folder_path}")
            return 0

        files = sorted(glob.glob(os.path.join(self.folder_path,
                                              f"{self.PREFIX}*.png")))
        # ignora templates de referência
        files = [f for f in files
                 if "template" not in os.path.basename(f).lower()]

        for i, path in enumerate(files, start=1):
            sh = AutotileSheet(path)
            if sh.load():
                self.sheets.append(sh)
                self.by_local_id[i] = sh
                print(f"[AutotileManager] #{i}: {sh.name} (cell={sh.cell_size}px)")

        print(f"[AutotileManager] {len(self.sheets)} autotile(s) carregado(s)")
        return len(self.sheets)

    def get(self, local_id):
        return self.by_local_id.get(local_id)

    def list_ids(self):
        return sorted(self.by_local_id.keys())

    def preview(self, local_id, size=32):
        """Retorna uma Surface de preview (interior mask 255) escalada."""
        key = (local_id, size)
        if key in self._cache_preview:
            return self._cache_preview[key]

        sh = self.by_local_id.get(local_id)
        if sh is None:
            surf = pygame.Surface((size, size), pygame.SRCALPHA)
            surf.fill((255, 0, 255))
        else:
            interior = sh.surface_for_mask(255)
            if interior is None:
                surf = pygame.Surface((size, size), pygame.SRCALPHA)
                surf.fill((255, 0, 255))
            else:
                surf = pygame.transform.scale(interior, (size, size))

        self._cache_preview[key] = surf
        return surf