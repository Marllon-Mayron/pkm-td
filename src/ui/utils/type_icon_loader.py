# src/ui/utils/type_icon_loader.py
"""
Loader centralizado de ícones de tipo (38x38).

Caminho: res/PokemonSprites/UI/Types/types_icon/
Fallback: undefined.png

Uso:
    from src.ui.utils.type_icon_loader import type_icon_loader
    surf = type_icon_loader.get_original("fire")
    type_icon_loader.render(screen, "water", x=10, y=10)
"""
from pathlib import Path
from typing import Dict, List, Optional, Tuple
import pygame

from src.config.paths import SPRITES_PATH


# Caminho base dos ícones de tipo
TYPE_ICON_DIR = SPRITES_PATH / "UI" / "Types" / "types_icon"

# Arquivo de fallback (sem extensão — o loader adiciona .png)
FALLBACK_NAME = "undefined"

# Dimensões canônicas dos sprites originais
ORIGINAL_SIZE: Tuple[int, int] = (38, 38)


# Aliases: nomes alternativos / typos comuns que podem chegar
_TYPE_ALIASES = {
    "normal":       "normal",
    "fire":         "fire",
    "water":        "water",
    "electric":     "electric",
    "grass":        "grass",
    "ice":          "ice",
    "fighting":     "fighting",
    "poison":       "poison",
    "ground":       "ground",
    "flying":       "flying",
    "psychic":      "psychic",
    "bug":          "bug",
    "rock":         "rock",
    "ghost":        "ghost",
    "dragon":       "dragon",
    "dark":         "dark",
    "steel":        "steel",
    "fairy":        "fairy",
    # aliases / typos
    "stell":        "steel",     # <-- typo conhecido
    "eletric":      "electric",
    "plant":        "grass",
    "psico":        "psychic",
    "insect":       "bug",
    "sinistro":     "dark",
    "lutador":      "fighting",
    "venenoso":     "poison",
    "terrestre":    "ground",
    "voador":       "flying",
    "pedra":        "rock",
    "fantasma":     "ghost",
    "dragão":       "dragon",
    "dragao":       "dragon",
    "aço":          "steel",
    "aco":          "steel",
    "fada":         "fairy",
    "gelo":         "ice",
}


def _norm(name: str) -> str:
    """Normaliza um nome de tipo: lowercase, sem espaços extras, aplica alias."""
    if not name:
        return ""
    s = str(name).strip().lower().replace("_", "-").replace(" ", "-")
    return _TYPE_ALIASES.get(s, s)


class TypeIconLoader:
    """Carrega e cacheia os ícones de tipo (38x38)."""

    def __init__(self, base_dir: Path = TYPE_ICON_DIR):
        self.base_dir = Path(base_dir)
        self._cache: Dict[str, pygame.Surface] = {}
        self._fallback: Optional[pygame.Surface] = None

    # ----------------------------------------------------------
    # Carregamento interno
    # ----------------------------------------------------------
    def _load_file(self, name: str) -> Optional[pygame.Surface]:
        """Tenta carregar `name.png` de forma case-insensitive."""
        if not self.base_dir.exists():
            return None

        target = self.base_dir / f"{name}.png"
        if target.exists():
            try:
                surf = pygame.image.load(str(target))
                if pygame.display.get_surface() is not None:
                    surf = surf.convert_alpha()
                return surf
            except Exception as e:
                print(f"[TYPE_ICON] Erro ao carregar {target}: {e}")

        # case-insensitive
        try:
            for f in self.base_dir.iterdir():
                if (f.is_file()
                        and f.suffix.lower() == ".png"
                        and f.stem.lower() == name.lower()):
                    try:
                        surf = pygame.image.load(str(f))
                        if pygame.display.get_surface() is not None:
                            surf = surf.convert_alpha()
                        return surf
                    except Exception as e:
                        print(f"[TYPE_ICON] Erro ao carregar {f}: {e}")
                        return None
        except Exception:
            pass

        return None

    def _build_placeholder(self) -> pygame.Surface:
        """Placeholder cinza caso nem o fallback exista."""
        surf = pygame.Surface(ORIGINAL_SIZE, pygame.SRCALPHA)
        surf.fill((60, 65, 80))
        pygame.draw.rect(surf, (120, 130, 150), surf.get_rect(),
                         1, border_radius=4)
        try:
            font = pygame.font.Font(None, 18)
            txt = font.render("?", True, (200, 205, 220))
            surf.blit(txt, txt.get_rect(center=(ORIGINAL_SIZE[0] // 2,
                                                 ORIGINAL_SIZE[1] // 2)))
        except Exception:
            pass
        return surf

    def _get_fallback(self) -> pygame.Surface:
        if self._fallback is not None:
            return self._fallback
        fb = self._load_file(FALLBACK_NAME)
        if fb is None:
            fb = self._build_placeholder()
        self._fallback = fb
        return fb

    # ----------------------------------------------------------
    # API pública
    # ----------------------------------------------------------
    def get(self, type_name: str,
            size: Optional[Tuple[int, int]] = None) -> pygame.Surface:
        key = _norm(type_name)

        if key in self._cache:
            surf = self._cache[key]
        else:
            loaded = self._load_file(key)
            surf = loaded if loaded is not None else self._get_fallback()
            self._cache[key] = surf

        if size and surf.get_size() != size:
            return pygame.transform.smoothscale(surf, size)
        return surf

    def get_original(self, type_name: str) -> pygame.Surface:
        return self.get(type_name, size=ORIGINAL_SIZE)

    def has(self, type_name: str) -> bool:
        key = _norm(type_name)
        loaded = self._load_file(key)
        if loaded is not None:
            self._cache[key] = loaded
            return True
        return False

    def available_types(self) -> List[str]:
        if not self.base_dir.exists():
            return []
        names = []
        for f in self.base_dir.iterdir():
            if f.is_file() and f.suffix.lower() == ".png":
                if f.stem.lower() != FALLBACK_NAME.lower():
                    names.append(f.stem.lower())
        return sorted(names)

    def preload(self, type_names: Optional[List[str]] = None):
        targets = type_names if type_names else self.available_types()
        for t in targets:
            self.get_original(t)

    def clear_cache(self):
        self._cache.clear()
        self._fallback = None

    # ----------------------------------------------------------
    # Helpers de desenho
    # ----------------------------------------------------------
    def render(self, screen: pygame.Surface, type_name: str,
               x: int, y: int,
               size: Optional[Tuple[int, int]] = None) -> pygame.Rect:
        surf = self.get(type_name, size=size)
        rect = surf.get_rect(topleft=(int(x), int(y)))
        screen.blit(surf, rect)
        return rect

    def render_centered(self, screen: pygame.Surface, type_name: str,
                        center: Tuple[int, int],
                        size: Optional[Tuple[int, int]] = None) -> pygame.Rect:
        surf = self.get(type_name, size=size)
        rect = surf.get_rect(center=(int(center[0]), int(center[1])))
        screen.blit(surf, rect)
        return rect


# =========================================================
# Instância global
# =========================================================
type_icon_loader = TypeIconLoader()


# =========================================================
# Conveniências module-level
# =========================================================
def get_type_icon(type_name: str,
                  size: Optional[Tuple[int, int]] = None) -> pygame.Surface:
    return type_icon_loader.get(type_name, size=size)


def render_type_icon(screen: pygame.Surface, type_name: str,
                     x: int, y: int,
                     size: Optional[Tuple[int, int]] = None) -> pygame.Rect:
    return type_icon_loader.render(screen, type_name, x, y, size=size)