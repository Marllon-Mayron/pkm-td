# src/ui/utils/type_bar_loader.py
"""
Loader centralizado de sprites de barra de tipo.

Caminho: res/PokemonSprites/UI/Types/types_bar/
Sprites: 48x16 por padrão, um por tipo (fire.png, water.png, ...).
Fallback: undefined.png

Uso:
    from src.ui.utils.type_bar_loader import type_bar_loader

    # Direto (retorna Surface)
    surf = type_bar_loader.get_original("fire")
    surf = type_bar_loader.get("water", size=(96, 32))

    # Desenho
    type_bar_loader.render(screen, "grass", x=100, y=50)
    type_bar_loader.render_centered(screen, "ice", center=(200, 100))

    # Ou via conveniência module-level:
    from src.ui.utils.type_bar_loader import get_type_bar, render_type_bar
    render_type_bar(screen, "fire", 100, 50)
"""
from pathlib import Path
from typing import Dict, List, Optional, Tuple
import pygame

from src.config.paths import SPRITES_PATH


# Caminho base das barras de tipo
TYPE_BAR_DIR = SPRITES_PATH / "UI" / "Types" / "types_bar"

# Arquivo de fallback (sem extensão, o loader adiciona .png)
FALLBACK_NAME = "undefined"

# Dimensões canônicas dos sprites originais
ORIGINAL_SIZE: Tuple[int, int] = (48, 16)


# Aliases: nomes alternativos que podem chegar de saves antigos
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
    # aliases comuns
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


class TypeBarLoader:
    """Carrega e cacheia as barras de tipo (48x16)."""

    def __init__(self, base_dir: Path = TYPE_BAR_DIR):
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

        # 1ª tentativa: nome direto (case-sensitive no stem, mas o FS pode ser insensível)
        if target.exists():
            try:
                surf = pygame.image.load(str(target))
                if pygame.display.get_surface() is not None:
                    surf = surf.convert_alpha()
                return surf
            except Exception as e:
                print(f"[TYPE_BAR] Erro ao carregar {target}: {e}")

        # 2ª tentativa: case-insensitive
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
                        print(f"[TYPE_BAR] Erro ao carregar {f}: {e}")
                        return None
        except Exception:
            pass

        return None

    def _build_placeholder(self) -> pygame.Surface:
        """Cria um placeholder cinza caso nem o fallback exista."""
        surf = pygame.Surface(ORIGINAL_SIZE, pygame.SRCALPHA)
        surf.fill((60, 65, 80))
        pygame.draw.rect(surf, (120, 130, 150), surf.get_rect(), 1, border_radius=2)
        try:
            font = pygame.font.Font(None, 12)
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
        """Retorna o sprite do tipo (48x16 ou escalado)."""
        key = _norm(type_name)

        if key in self._cache:
            surf = self._cache[key]
        else:
            loaded = self._load_file(key)
            if loaded is None:
                surf = self._get_fallback()
            else:
                surf = loaded
            self._cache[key] = surf

        if size and surf.get_size() != size:
            return pygame.transform.smoothscale(surf, size)
        return surf

    def get_original(self, type_name: str) -> pygame.Surface:
        """Retorna o sprite no tamanho original (48x16)."""
        return self.get(type_name, size=ORIGINAL_SIZE)

    def has(self, type_name: str) -> bool:
        """Verifica se o sprite do tipo existe (não é fallback)."""
        key = _norm(type_name)
        loaded = self._load_file(key)
        if loaded is not None:
            self._cache[key] = loaded
            return True
        return False

    def available_types(self) -> List[str]:
        """Lista os tipos com sprite disponível (exclui o fallback)."""
        if not self.base_dir.exists():
            return []
        names = []
        for f in self.base_dir.iterdir():
            if f.is_file() and f.suffix.lower() == ".png":
                if f.stem.lower() != FALLBACK_NAME.lower():
                    names.append(f.stem.lower())
        return sorted(names)

    def preload(self, type_names: Optional[List[str]] = None):
        """Pré-carrega uma lista de tipos (ou todos se None)."""
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
        """Blita o sprite do tipo em (x, y) e retorna o Rect usado."""
        surf = self.get(type_name, size=size)
        rect = surf.get_rect(topleft=(int(x), int(y)))
        screen.blit(surf, rect)
        return rect

    def render_centered(self, screen: pygame.Surface, type_name: str,
                        center: Tuple[int, int],
                        size: Optional[Tuple[int, int]] = None) -> pygame.Rect:
        """Blita o sprite centralizado em `center`."""
        surf = self.get(type_name, size=size)
        rect = surf.get_rect(center=(int(center[0]), int(center[1])))
        screen.blit(surf, rect)
        return rect

    def render_row(self, screen: pygame.Surface, type_names: List[str],
                   x: int, y: int, gap: int = 4,
                   size: Optional[Tuple[int, int]] = None) -> int:
        """
        Desenha várias barras lado a lado.
        Retorna o X final (útil para encadear outros elementos).
        """
        cx = int(x)
        for name in type_names:
            rect = self.render(screen, name, cx, y, size=size)
            cx = rect.right + gap
        return cx


# =========================================================
# Instância global
# =========================================================
type_bar_loader = TypeBarLoader()


# =========================================================
# Conveniências module-level
# =========================================================
def get_type_bar(type_name: str,
                 size: Optional[Tuple[int, int]] = None) -> pygame.Surface:
    """Atalho para `type_bar_loader.get(type_name, size)`."""
    return type_bar_loader.get(type_name, size=size)


def render_type_bar(screen: pygame.Surface, type_name: str,
                    x: int, y: int,
                    size: Optional[Tuple[int, int]] = None) -> pygame.Rect:
    """Atalho para `type_bar_loader.render(...)`."""
    return type_bar_loader.render(screen, type_name, x, y, size=size)