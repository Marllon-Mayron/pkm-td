# src/ui/utils/type_bar_loader.py
"""
Loader unificado de sprites de barra (tipos E raridades).

Caminhos:
    res/PokemonSprites/UI/Types/types_bar/         → tipos     (48x16, fallback undefined.png)
    res/PokemonSprites/UI/Types/types_rarity_bar/  → raridades (70x16, fallback common.png)

A categoria é decidida automaticamente pelo nome:
    "fire", "water", "grass", ...           → tipo
    "common", "legendary", "épico", ...     → raridade

Uso:
    from src.ui.utils.type_bar_loader import type_bar_loader

    surf = type_bar_loader.get_original("fire")        # tipo     (48x16)
    surf = type_bar_loader.get_original("legendary")   # raridade (70x16)
    surf = type_bar_loader.get("water", size=(96, 32)) # tipo escalado

    type_bar_loader.render(screen, "grass", 100, 50)
    type_bar_loader.render_centered(screen, "epic", (200, 100))

    # Forçar categoria (raro precisar):
    type_bar_loader.get_type("fire")
    type_bar_loader.get_rarity("legendary")

    # Module-level (o que o PokedexScene chama):
    from src.ui.utils import type_bar_loader
    surf = type_bar_loader.get_original(item)   # funciona para tipo e raridade
"""
from pathlib import Path
from typing import Dict, List, Optional, Tuple
import pygame

from src.config.paths import SPRITES_PATH


# =========================================================================
# Caminhos base
# =========================================================================
TYPE_BAR_DIR   = SPRITES_PATH / "UI" / "Types" / "types_bar"
RARITY_BAR_DIR = SPRITES_PATH / "UI" / "Types" / "types_rarity_bar"

# Fallbacks (sem extensão — o loader adiciona .png)
TYPE_FALLBACK   = "undefined"
RARITY_FALLBACK = "common"

# Tamanhos originais canônicos
TYPE_ORIGINAL_SIZE   = (48, 16)
RARITY_ORIGINAL_SIZE = (70, 16)


# =========================================================================
# Aliases
# =========================================================================
_TYPE_ALIASES = {
    # tipos oficiais
    "normal":     "normal",
    "fire":       "fire",
    "water":      "water",
    "electric":   "electric",
    "grass":      "grass",
    "ice":        "ice",
    "fighting":   "fighting",
    "poison":     "poison",
    "ground":     "ground",
    "flying":     "flying",
    "psychic":    "psychic",
    "bug":        "bug",
    "rock":       "rock",
    "ghost":      "ghost",
    "dragon":     "dragon",
    "dark":       "dark",
    "steel":      "steel",
    "fairy":      "fairy",
    "undefined":  "undefined",
    # aliases pt-br / erros comuns
    "eletric":    "electric",
    "plant":      "grass",
    "psico":      "psychic",
    "insect":     "bug",
    "sinistro":   "dark",
    "lutador":    "fighting",
    "venenoso":   "poison",
    "terrestre":  "ground",
    "voador":     "flying",
    "pedra":      "rock",
    "fantasma":   "ghost",
    "dragão":     "dragon",
    "dragao":     "dragon",
    "aço":        "steel",
    "aco":        "steel",
    "fada":       "fairy",
    "gelo":       "ice",
}

_RARITY_ALIASES = {
    # raridades oficiais
    "common":     "common",
    "uncommon":   "uncommon",
    "rare":       "rare",
    "epic":       "epic",
    "legendary":  "legendary",
    # pt-br
    "comum":      "common",
    "incomum":    "uncommon",
    "raro":       "rare",
    "epico":      "epic",
    "épico":      "epic",
    "lendario":   "legendary",
    "lendário":   "legendary",
    # inglês legado
    "basic":      "common",
    "legend":     "legendary",
}


def _clean(name: str) -> str:
    if not name:
        return ""
    return str(name).strip().lower().replace("_", "-").replace(" ", "-")


def _resolve(name: str) -> Tuple[str, str]:
    """
    Devolve ('type' | 'rarity', chave_canonica).

    Ordem de decisão:
      1) alias de raridade  → rarity
      2) alias de tipo      → type
      3) desconhecido       → type (comportamento padrão anterior)
    """
    raw = _clean(name)
    if raw in _RARITY_ALIASES:
        return "rarity", _RARITY_ALIASES[raw]
    if raw in _TYPE_ALIASES:
        return "type", _TYPE_ALIASES[raw]
    return "type", raw


# =========================================================================
# Bucket interno: um conjunto de sprites com pasta/cache/fallback próprios
# =========================================================================
class _BarBucket:
    """Cache + carregamento de uma categoria (tipos ou raridades)."""

    def __init__(self, base_dir: Path, fallback_name: str,
                 original_size: Tuple[int, int], log_tag: str):
        self.base_dir       = Path(base_dir)
        self.fallback_name  = fallback_name
        self.original_size  = tuple(original_size)
        self.log_tag        = log_tag
        self._cache: Dict[str, pygame.Surface] = {}
        self._fallback: Optional[pygame.Surface] = None

    # ---------------- carregamento ----------------
    def _load_file(self, name: str) -> Optional[pygame.Surface]:
        if not self.base_dir.exists():
            return None

        target = self.base_dir / f"{name}.png"

        # 1ª tentativa: caminho direto
        if target.exists():
            try:
                surf = pygame.image.load(str(target))
                if pygame.display.get_surface() is not None:
                    surf = surf.convert_alpha()
                return surf
            except Exception as e:
                print(f"[{self.log_tag}] Erro ao carregar {target}: {e}")

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
                        print(f"[{self.log_tag}] Erro ao carregar {f}: {e}")
                        return None
        except Exception:
            pass

        return None

    def _build_placeholder(self) -> pygame.Surface:
        surf = pygame.Surface(self.original_size, pygame.SRCALPHA)
        surf.fill((60, 65, 80))
        pygame.draw.rect(surf, (120, 130, 150),
                         surf.get_rect(), 1, border_radius=2)
        try:
            font = pygame.font.Font(None, 12)
            txt = font.render("?", True, (200, 205, 220))
            surf.blit(txt, txt.get_rect(center=(self.original_size[0] // 2,
                                                 self.original_size[1] // 2)))
        except Exception:
            pass
        return surf

    def _get_fallback(self) -> pygame.Surface:
        if self._fallback is not None:
            return self._fallback
        fb = self._load_file(self.fallback_name)
        if fb is None:
            fb = self._build_placeholder()
        self._fallback = fb
        return fb

    # ---------------- API ----------------
    def get(self, key: str,
            size: Optional[Tuple[int, int]] = None) -> pygame.Surface:
        surf = self._cache.get(key)
        if surf is None:
            loaded = self._load_file(key)
            if loaded is not None:
                self._cache[key] = loaded
                surf = loaded
            else:
                # NÃO cacheia o fallback sob a chave (evita envenenamento)
                surf = self._get_fallback()

        if size and surf.get_size() != size:
            return pygame.transform.smoothscale(surf, size)
        return surf

    def get_original(self, key: str) -> pygame.Surface:
        return self.get(key, size=self.original_size)

    def has(self, key: str) -> bool:
        if key in self._cache:
            return True
        loaded = self._load_file(key)
        if loaded is not None:
            self._cache[key] = loaded
            return True
        return False

    def available(self) -> List[str]:
        if not self.base_dir.exists():
            return []
        names = []
        for f in self.base_dir.iterdir():
            if f.is_file() and f.suffix.lower() == ".png":
                if f.stem.lower() != self.fallback_name.lower():
                    names.append(f.stem.lower())
        return sorted(names)

    def clear_cache(self):
        self._cache.clear()
        self._fallback = None


# =========================================================================
# Loader principal (agrega os dois buckets)
# =========================================================================
class TypeBarLoader:
    """Loader unificado de barras de tipo E raridade."""

    def __init__(self,
                 type_dir: Path = TYPE_BAR_DIR,
                 rarity_dir: Path = RARITY_BAR_DIR):
        self._type   = _BarBucket(type_dir,   TYPE_FALLBACK,
                                  TYPE_ORIGINAL_SIZE,   "TYPE_BAR")
        self._rarity = _BarBucket(rarity_dir, RARITY_FALLBACK,
                                  RARITY_ORIGINAL_SIZE, "RARITY_BAR")

    # ---------------- internos ----------------
    def _bucket_for(self, name: str) -> Tuple[_BarBucket, str]:
        category, key = _resolve(name)
        return (self._rarity if category == "rarity" else self._type), key

    # ---------------- API unificada ----------------
    def get(self, name: str,
            size: Optional[Tuple[int, int]] = None) -> pygame.Surface:
        bucket, key = self._bucket_for(name)
        return bucket.get(key, size=size)

    def get_original(self, name: str) -> pygame.Surface:
        bucket, key = self._bucket_for(name)
        return bucket.get_original(key)

    def has(self, name: str) -> bool:
        bucket, key = self._bucket_for(name)
        return bucket.has(key)

    # ---------------- API forçada por categoria ----------------
    def get_type(self, type_name: str,
                 size: Optional[Tuple[int, int]] = None) -> pygame.Surface:
        key = _TYPE_ALIASES.get(_clean(type_name), _clean(type_name))
        return self._type.get(key, size=size)

    def get_type_original(self, type_name: str) -> pygame.Surface:
        key = _TYPE_ALIASES.get(_clean(type_name), _clean(type_name))
        return self._type.get_original(key)

    def get_rarity(self, rarity_name: str,
                   size: Optional[Tuple[int, int]] = None) -> pygame.Surface:
        key = _RARITY_ALIASES.get(_clean(rarity_name), _clean(rarity_name))
        return self._rarity.get(key, size=size)

    def get_rarity_original(self, rarity_name: str) -> pygame.Surface:
        key = _RARITY_ALIASES.get(_clean(rarity_name), _clean(rarity_name))
        return self._rarity.get_original(key)

    # ---------------- inventário ----------------
    def available_types(self) -> List[str]:
        return self._type.available()

    def available_rarities(self) -> List[str]:
        return self._rarity.available()

    def available(self) -> List[str]:
        """Lista combinada (sem distinguir categoria)."""
        return sorted(set(self.available_types()) | set(self.available_rarities()))

    def preload(self, names: Optional[List[str]] = None):
        """Pré-carrega uma lista (ou tudo) — resolve categoria por nome."""
        if names:
            for n in names:
                self.get_original(n)
        else:
            for n in self.available_types():
                self._type.get_original(n)
            for n in self.available_rarities():
                self._rarity.get_original(n)

    def clear_cache(self):
        self._type.clear_cache()
        self._rarity.clear_cache()

    # ---------------- desenho ----------------
    def render(self, screen: pygame.Surface, name: str,
               x: int, y: int,
               size: Optional[Tuple[int, int]] = None) -> pygame.Rect:
        surf = self.get(name, size=size)
        rect = surf.get_rect(topleft=(int(x), int(y)))
        screen.blit(surf, rect)
        return rect

    def render_centered(self, screen: pygame.Surface, name: str,
                        center: Tuple[int, int],
                        size: Optional[Tuple[int, int]] = None) -> pygame.Rect:
        surf = self.get(name, size=size)
        rect = surf.get_rect(center=(int(center[0]), int(center[1])))
        screen.blit(surf, rect)
        return rect

    def render_row(self, screen: pygame.Surface, names: List[str],
                   x: int, y: int, gap: int = 4,
                   size: Optional[Tuple[int, int]] = None) -> int:
        """Desenha várias barras lado a lado. Retorna o X final."""
        cx = int(x)
        for n in names:
            rect = self.render(screen, n, cx, y, size=size)
            cx = rect.right + gap
        return cx


# =========================================================================
# Instância global
# =========================================================================
type_bar_loader = TypeBarLoader()

# Compat: nome antigo
rarity_bar_loader = type_bar_loader


# =========================================================================
# Conveniências module-level
# (o PokedexScene importa o MÓDULO e chama type_bar_loader.get_original)
# =========================================================================
def get_original(name: str) -> pygame.Surface:
    """Sprite no tamanho original da categoria (tipo 48x16 / raridade 70x16)."""
    return type_bar_loader.get_original(name)


def get(name: str,
        size: Optional[Tuple[int, int]] = None) -> pygame.Surface:
    """Sprite (escalado se `size` for dado). Resolve categoria pelo nome."""
    return type_bar_loader.get(name, size=size)


def has(name: str) -> bool:
    return type_bar_loader.has(name)


def render(screen: pygame.Surface, name: str,
           x: int, y: int,
           size: Optional[Tuple[int, int]] = None) -> pygame.Rect:
    return type_bar_loader.render(screen, name, x, y, size=size)


def render_centered(screen: pygame.Surface, name: str,
                    center: Tuple[int, int],
                    size: Optional[Tuple[int, int]] = None) -> pygame.Rect:
    return type_bar_loader.render_centered(screen, name, center, size=size)


def render_row(screen: pygame.Surface, names: List[str],
               x: int, y: int, gap: int = 4,
               size: Optional[Tuple[int, int]] = None) -> int:
    return type_bar_loader.render_row(screen, names, x, y, gap=gap, size=size)


def available_types() -> List[str]:
    return type_bar_loader.available_types()


def available_rarities() -> List[str]:
    return type_bar_loader.available_rarities()


# -------- Compatibilidade com nomes antigos --------
get_type_bar       = get       # assinatura compatível
render_type_bar    = render
get_rarity_bar     = get
render_rarity_bar  = render