# src/ui/theme.py
"""Tema global + helpers de cor com suporte a alpha."""
from pathlib import Path
import pygame


class Palette:
    BG_DEEP     = (28, 40, 72)
    BG_MID      = (48, 68, 112)
    BG_LIGHT    = (88, 120, 176)
    PANEL_FILL       = (232, 232, 208)
    PANEL_FILL_DARK  = (192, 192, 168)
    PANEL_FILL_ALT   = (216, 216, 192)
    BORDER_DARK      = (48, 60, 96)
    BORDER_MID       = (80, 104, 152)
    BORDER_LIGHT     = (248, 248, 240)
    BORDER_HIGHLIGHT = (248, 200, 88)
    BORDER_SHADOW    = (16, 24, 48)
    GOLD   = (248, 176, 48)
    RED    = (216, 72, 64)
    BLUE   = (56, 128, 200)
    GREEN  = (88, 176, 88)
    PURPLE = (136, 88, 200)
    ORANGE = (248, 128, 48)
    TEXT_DARK  = (32, 32, 40)
    TEXT_LIGHT = (248, 248, 240)
    TEXT_MUTED = (120, 120, 128)
    TEXT_GOLD  = (248, 176, 48)


BUTTON_STYLES = {
    "primary": {"fill": (88, 136, 200), "fill_hover": (120, 168, 232),
                "fill_press": (64, 104, 160), "border": Palette.BORDER_DARK,
                "border_hover": Palette.GOLD, "text": Palette.TEXT_LIGHT},
    "danger":  {"fill": (200, 80, 72), "fill_hover": (232, 112, 104),
                "fill_press": (160, 56, 48), "border": (96, 32, 32),
                "border_hover": Palette.GOLD, "text": Palette.TEXT_LIGHT},
    "success": {"fill": (72, 152, 88), "fill_hover": (104, 184, 120),
                "fill_press": (52, 120, 64), "border": (32, 80, 48),
                "border_hover": Palette.GOLD, "text": Palette.TEXT_LIGHT},
    "gold":    {"fill": (216, 152, 48), "fill_hover": (248, 184, 80),
                "fill_press": (176, 120, 32), "border": (112, 72, 16),
                "border_hover": Palette.BORDER_LIGHT, "text": Palette.TEXT_LIGHT},
    "ghost":   {"fill": (232, 232, 208), "fill_hover": (248, 248, 232),
                "fill_press": (208, 208, 184), "border": Palette.BORDER_DARK,
                "border_hover": Palette.GOLD, "text": Palette.TEXT_DARK},
    "disabled":{"fill": (160, 160, 152), "fill_hover": (160, 160, 152),
                "fill_press": (160, 160, 152), "border": (96, 96, 96),
                "border_hover": (96, 96, 96), "text": (112, 112, 112)},
}


class FontBook:
    _cache = {}
    _font_files = {"default": None}

    @classmethod
    def register(cls, name, path):
        cls._font_files[name] = str(path)
        cls._cache = {k: v for k, v in cls._cache.items() if k[2] != name}

    @classmethod
    def scan_folder(cls, folder):
        folder = Path(folder)
        if not folder.exists():
            print(f"[FontBook] pasta não existe: {folder}")
            return 0
        n = 0
        for ext in ("*.ttf", "*.otf", "*.TTF", "*.OTF"):
            for p in folder.glob(ext):
                cls.register(p.stem, p)
                n += 1
        print(f"[FontBook] {n} fontes registradas em {folder}")
        return n

    @classmethod
    def available_fonts(cls):
        return ["default"] + sorted(k for k in cls._font_files if k != "default")

    @classmethod
    def get(cls, size, bold=False, name="default"):
        key = (int(size), bool(bold), name or "default")
        if key not in cls._cache:
            path = cls._font_files.get(name or "default")
            try:
                f = pygame.font.Font(path, int(size)) if path else pygame.font.Font(None, int(size))
            except Exception:
                f = pygame.font.Font(None, int(size))
            if bold:
                f.set_bold(True)
            cls._cache[key] = f
        return cls._cache[key]

    @classmethod
    def clear(cls):
        cls._cache.clear()


def lerp_color(a, b, t):
    t = max(0.0, min(1.0, t))
    return tuple(int(a[i] + (b[i] - a[i]) * t) for i in range(3))

def darken(color, amount=0.3):  return lerp_color(color, (0, 0, 0), amount)
def lighten(color, amount=0.3): return lerp_color(color, (255, 255, 255), amount)


# =====================================================================
# CORES — parse / serialize (com alpha)
# =====================================================================
def parse_color(value, default=None):
    """
    Aceita:
      - None                              -> default
      - (r,g,b)   / [r,g,b]               -> tuple (sem alpha)
      - (r,g,b,a) / [r,g,b,a]             -> tuple (com alpha)
      - "#RRGGBB" / "#RRGGBBAA"           -> tuple
      - int 0xRRGGBB                      -> tuple
    """
    if value is None:
        return default
    if isinstance(value, (list, tuple)):
        if len(value) >= 4:
            return (int(value[0]), int(value[1]), int(value[2]), int(value[3]))
        if len(value) >= 3:
            return (int(value[0]), int(value[1]), int(value[2]))
    if isinstance(value, int):
        return ((value >> 16) & 0xFF, (value >> 8) & 0xFF, value & 0xFF)
    s = str(value).strip().lstrip("#").upper()
    if len(s) == 8:
        try:
            return (int(s[0:2], 16), int(s[2:4], 16),
                    int(s[4:6], 16), int(s[6:8], 16))
        except ValueError:
            pass
    if len(s) == 6:
        try:
            return (int(s[0:2], 16), int(s[2:4], 16), int(s[4:6], 16))
        except ValueError:
            pass
    return default


def to_hex(c):
    """
    Normaliza para "#RRGGBB" ou "#RRGGBBAA" (quando alpha < 255).
    """
    if c is None or c == "":
        return ""
    if isinstance(c, str):
        s = c.strip().lstrip("#").upper()
        if len(s) in (6, 8):
            try:
                int(s, 16)
                return f"#{s}"
            except ValueError:
                return ""
        return ""
    if isinstance(c, (list, tuple)):
        if len(c) >= 4:
            r = int(c[0]) & 0xFF
            g = int(c[1]) & 0xFF
            b = int(c[2]) & 0xFF
            a = int(c[3]) & 0xFF
            if a == 255:
                return f"#{r:02X}{g:02X}{b:02X}"
            return f"#{r:02X}{g:02X}{b:02X}{a:02X}"
        if len(c) >= 3:
            r = int(c[0]) & 0xFF
            g = int(c[1]) & 0xFF
            b = int(c[2]) & 0xFF
            return f"#{r:02X}{g:02X}{b:02X}"
    if isinstance(c, int):
        return f"#{(c >> 16) & 0xFF:02X}{(c >> 8) & 0xFF:02X}{c & 0xFF:02X}"
    return ""


def with_alpha(color, alpha):
    """Retorna a cor como tupla RGBA com o alpha informado."""
    if color is None:
        return None
    if len(color) >= 4:
        return (color[0], color[1], color[2], int(alpha))
    return (color[0], color[1], color[2], int(alpha))


def color_alpha(color):
    """Retorna o alpha da cor (255 se não tiver)."""
    if color is None:
        return 255
    if len(color) >= 4:
        return int(color[3])
    return 255


# Auto-scan de fontes
try:
    from src.config.paths import RES_PATH
    FontBook.scan_folder(RES_PATH / "fontes")
except Exception as e:
    print(f"[theme] não foi possível escanear fontes: {e}")