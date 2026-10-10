# src/ui/utils/rarity_bar_loader.py
"""
Loader centralizado de sprites de barra de raridade (roupas).

Caminho: res/PokemonSprites/UI/Types/types_rarity_bar/
Sprites: 70x16, um por raridade (common.png, uncommon.png, ...).
Fallback: common.png (ou placeholder).

Uso:
    from src.ui.utils.rarity_bar_loader import rarity_bar_loader

    surf = rarity_bar_loader.get_original("legendary")
    surf = rarity_bar_loader.get("epic", size=(140, 32))

    rarity_bar_loader.render(screen, "rare", x=100, y=50)
    rarity_bar_loader.render_centered(screen, "uncommon", center=(200, 100))

Ou via conveniência module-level:
    from src.ui.utils.rarity_bar_loader import (
        get_rarity_bar, render_rarity_bar,
    )
    render_rarity_bar(screen, "epic", 100, 50)
"""
from pathlib import Path
from typing import Dict, List, Optional, Tuple
import pygame

from src.config.paths import SPRITES_PATH


# Caminho base das barras de raridade
RARITY_BAR_DIR = SPRITES_PATH / "UI" / "Types" / "types_rarity_bar"

# Fallback (sem extensão — o loader adiciona .png)
FALLBACK_NAME = "common"

# Dimensões canônicas dos sprites originais
ORIGINAL_SIZE: Tuple[int, int] = (70, 16)


# Aliases: nomes que podem chegar de saves/dados antigos
_RARITY_ALIASES = {
    "common":    "common",
    "uncommon":  "uncommon",
    "rare":      "rare",
    "epic":      "epic",
    "legendary": "legendary",
    # pt-br / variações
    "comum":     "common",
    "incomum":   "uncommon",
    "raro":      "rare",
    "epico":     "epic",
    "épico":     "epic",
    "lendario":  "legendary",
    "lendário":  "legendary",
    # inglês legado
    "basic":     "common",
    "uncommon_": "uncommon",
    "legend":    "legendary",
}


def _norm(name: str) -> str:
    """Normaliza um nome de raridade: lowercase, sem espaços, aplica alias."""
    if not name:
        return ""
    s = str(name).strip().lower().replace("_", "-").replace(" ", "-")
    return _RARITY_ALIASES.get(s, s)


class RarityBarLoader:
    """Carrega e cacheia as barras de raridade (70x16)."""

    def __init__(self, base_dir: Path = RARITY_BAR_DIR):
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
                print(f"[RARITY_BAR] Erro ao carregar {target}: {e}")

        # Fallback: case-insensitive
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
                        print(f"[RARITY_BAR] Erro ao carregar {f}: {e}")
                        return None
        except Exception:
            pass

        return None

    def _build_placeholder(self) -> pygame.Surface:
        """Placeholder cinza caso nem o fallback exista."""
        surf = pygame.Surface(ORIGINAL_SIZE, pygame.SRCALPHA)
        surf.fill((60, 65, 80))
        pygame.draw.rect(surf, (120, 130, 150),
                         surf.get_rect(), 1, border_radius=2)
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
    def get(self, rarity_name: str,
            size: Optional[Tuple[int, int]] = None) -> pygame.Surface:
        """Retorna o sprite da raridade (70x16 ou escalado)."""
        key = _norm(rarity_name)

        if key in self._cache:
            surf = self._cache[key]
        else:
            loaded = self._load_file(key)
            surf = loaded if loaded is not None else self._get_fallback()
            self._cache[key] = surf

        if size and surf.get_size() != size:
            return pygame.transform.smoothscale(surf, size)
        return surf

    def get_original(self, rarity_name: str) -> pygame.Surface:
        """Retorna o sprite no tamanho original (70x16)."""
        return self.get(rarity_name, size=ORIGINAL_SIZE)

    def has(self, rarity_name: str) -> bool:
        """Verifica se o sprite da raridade existe (não é fallback)."""
        key = _norm(rarity_name)
        loaded = self._load_file(key)
        if loaded is not None:
            self._cache[key] = loaded
            return True
        return False

    def available_rarities(self) -> List[str]:
        """Lista as raridades com sprite disponível (exclui o fallback)."""
        if not self.base_dir.exists():
            return []
        names = []
        for f in self.base_dir.iterdir():
            if f.is_file() and f.suffix.lower() == ".png":
                if f.stem.lower() != FALLBACK_NAME.lower():
                    names.append(f.stem.lower())
        return sorted(names)

    def preload(self, rarity_names: Optional[List[str]] = None):
        """Pré-carrega uma lista de raridades (ou todas se None)."""
        targets = rarity_names if rarity_names else self.available_rarities()
        for r in targets:
            self.get_original(r)

    def clear_cache(self):
        self._cache.clear()
        self._fallback = None

    # ----------------------------------------------------------
    # Helpers de desenho
    # ----------------------------------------------------------
    def render(self, screen: pygame.Surface, rarity_name: str,
               x: int, y: int,
               size: Optional[Tuple[int, int]] = None) -> pygame.Rect:
        """Blita o sprite da raridade em (x, y) e retorna o Rect usado."""
        surf = self.get(rarity_name, size=size)
        rect = surf.get_rect(topleft=(int(x), int(y)))
        screen.blit(surf, rect)
        return rect

    def render_centered(self, screen: pygame.Surface, rarity_name: str,
                        center: Tuple[int, int],
                        size: Optional[Tuple[int, int]] = None) -> pygame.Rect:
        """Blita o sprite centralizado em `center`."""
        surf = self.get(rarity_name, size=size)
        rect = surf.get_rect(center=(int(center[0]), int(center[1])))
        screen.blit(surf, rect)
        return rect


# =========================================================
# Instância global
# =========================================================
rarity_bar_loader = RarityBarLoader()


# =========================================================
# Conveniências module-level
# =========================================================
def get_rarity_bar(rarity_name: str,
                   size: Optional[Tuple[int, int]] = None) -> pygame.Surface:
    """Atalho para `rarity_bar_loader.get(rarity_name, size)`."""
    return rarity_bar_loader.get(rarity_name, size=size)


def render_rarity_bar(screen: pygame.Surface, rarity_name: str,
                      x: int, y: int,
                      size: Optional[Tuple[int, int]] = None) -> pygame.Rect:
    """Atalho para `rarity_bar_loader.render(...)`."""
    return rarity_bar_loader.render(screen, rarity_name, x, y, size=size)