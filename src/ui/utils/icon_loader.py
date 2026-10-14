# src/ui/utils/icon_loader.py

"""
Loaders de ícones de UI.

- UIImageLoader      -> loader genérico com cache (raw + escalado)
- ingame_icon_loader -> instância para res/PokemonSprites/UI/Icons/InGame
- get_held_icon()    -> atalho para o ícone de item segurável
"""
import pygame
from pathlib import Path
from typing import Dict, List, Optional, Tuple

from src.config.paths import SPRITES_PATH


# =====================================================================
# GENERIC UI IMAGE LOADER
# =====================================================================
class UIImageLoader:
    """
    Carrega e cacheia PNGs de uma pasta. Busca case-insensitive pelo stem.

    Uso:
        from src.ui.utils.icon_loader import ingame_icon_loader

        surf = ingame_icon_loader.get("capturado")               # original
        surf = ingame_icon_loader.get_scaled("capturado", (12, 12))
    """

    def __init__(self, base_dir: Path, cache_scaled: bool = True):
        self.base_dir = Path(base_dir)
        self.cache_scaled = cache_scaled
        self._raw_cache: Dict[str, Optional[pygame.Surface]] = {}
        self._scaled_cache: Dict[Tuple[str, Tuple[int, int]], pygame.Surface] = {}

    # ------------------------------------------------------------------
    # Busca no disco
    # ------------------------------------------------------------------
    def _find_file(self, name: str) -> Optional[Path]:
        if not self.base_dir.exists():
            return None

        target = self.base_dir / f"{name}.png"
        if target.exists():
            return target

        # Case-insensitive
        try:
            needle = name.lower()
            for f in self.base_dir.iterdir():
                if (f.is_file()
                        and f.suffix.lower() == ".png"
                        and f.stem.lower() == needle):
                    return f
        except Exception:
            pass
        return None

    # ------------------------------------------------------------------
    # API
    # ------------------------------------------------------------------
    def get(self, name: str) -> Optional[pygame.Surface]:
        """Retorna a Surface original (ou None se não encontrar)."""
        if name in self._raw_cache:
            return self._raw_cache[name]

        path = self._find_file(name)
        if path is None:
            self._raw_cache[name] = None
            return None

        try:
            surf = pygame.image.load(str(path))
            if pygame.display.get_surface() is not None:
                surf = surf.convert_alpha()
            self._raw_cache[name] = surf
            return surf
        except Exception as e:
            print(f"[UIImageLoader] Erro ao carregar {path}: {e}")
            self._raw_cache[name] = None
            return None

    def get_scaled(self, name: str,
                   size: Tuple[int, int]) -> Optional[pygame.Surface]:
        """Retorna a Surface escalada para `size` (int). Cacheada."""
        size = (max(1, int(size[0])), max(1, int(size[1])))

        if self.cache_scaled:
            key = (name, size)
            if key in self._scaled_cache:
                return self._scaled_cache[key]

        surf = self.get(name)
        if surf is None:
            return None

        scaled = (surf if surf.get_size() == size
                  else pygame.transform.smoothscale(surf, size))

        if self.cache_scaled:
            self._scaled_cache[(name, size)] = scaled

        return scaled

    def has(self, name: str) -> bool:
        return self.get(name) is not None

    def list_all(self) -> List[str]:
        if not self.base_dir.exists():
            return []
        return sorted([
            f.stem for f in self.base_dir.iterdir()
            if f.is_file() and f.suffix.lower() == ".png"
        ])

    def clear_cache(self):
        self._raw_cache.clear()
        self._scaled_cache.clear()


# =====================================================================
# INSTÂNCIAS PRONTAS
# =====================================================================
ingame_icon_loader = UIImageLoader(
    SPRITES_PATH / "UI" / "Icons" / "InGame"
)


# =====================================================================
# HELPERS ESPECÍFICOS
# =====================================================================
# Nome do arquivo do held icon dentro da pasta InGame
_HELD_ICON_NAME = "holdIcon"

# Fallback procedural caso o arquivo não exista
_HELD_FALLBACK: Optional[pygame.Surface] = None


def _build_held_fallback() -> pygame.Surface:
    """Círculo dourado procedural — só usado se o PNG não existir."""
    icon = pygame.Surface((16, 16), pygame.SRCALPHA)
    pygame.draw.circle(icon, (255, 215, 0), (8, 8), 7)
    pygame.draw.circle(icon, (255, 200, 50), (8, 8), 5)
    return icon


def get_held_icon() -> Optional[pygame.Surface]:
    """
    Ícone de item segurável (holdIcon.png na pasta InGame).

    Prioridade:
      1. PNG em res/PokemonSprites/UI/Icons/InGame/holdIcon.png
      2. Fallback procedural (círculo dourado)

    Retorna None apenas se pygame não estiver inicializado.
    """
    global _HELD_FALLBACK

    if not pygame.get_init():
        pygame.init()

    icon = ingame_icon_loader.get(_HELD_ICON_NAME)
    if icon is not None:
        return icon

    # Fallback
    if _HELD_FALLBACK is None:
        _HELD_FALLBACK = _build_held_fallback()
    return _HELD_FALLBACK

phase_star_loader = UIImageLoader(SPRITES_PATH / "UI" / "Icons")

_STAR_FILLED_NAME = "star"
_STAR_EMPTY_NAME  = "withoutStar"


def _build_star_fallback(filled: bool, size: int = 28) -> pygame.Surface:
    """Fallback procedural caso os PNGs não existam."""
    import math
    surf = pygame.Surface((size, size), pygame.SRCALPHA)
    cx = cy = size / 2.0
    R = size * 0.46
    r = R * 0.45
    pts = []
    for i in range(10):
        ang = -math.pi / 2 + i * math.pi / 5
        rad = R if i % 2 == 0 else r
        pts.append((cx + math.cos(ang) * rad, cy + math.sin(ang) * rad))
    if filled:
        pygame.draw.polygon(surf, (255, 210, 74), pts)
        pygame.draw.polygon(surf, (140, 100, 20), pts, 2)
    else:
        pygame.draw.polygon(surf, (60, 65, 80), pts)
        pygame.draw.polygon(surf, (90, 98, 120), pts, 2)
    return surf


def get_phase_star_surfaces(size: int = 28):
    """
    Retorna (filled, empty) — duas Surfaces escaladas para `size`.
    Faz fallback procedural se os PNGs faltarem.
    """
    size_t = (int(size), int(size))
    filled = phase_star_loader.get_scaled(_STAR_FILLED_NAME, size_t)
    empty  = phase_star_loader.get_scaled(_STAR_EMPTY_NAME,  size_t)
    if filled is None:
        filled = _build_star_fallback(filled=True,  size=size)
    if empty is None:
        empty = _build_star_fallback(filled=False, size=size)
    return filled, empty