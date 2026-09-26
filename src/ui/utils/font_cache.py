# src/ui/utils/font_cache.py

import pygame
from typing import Dict, Tuple

_FONT_CACHE: Dict[Tuple[str, int, bool], pygame.font.Font] = {}


def get_font(size: int, bold: bool = False) -> pygame.font.Font:
    """Retorna uma fonte em cache. Nunca cria duas vezes o mesmo tamanho."""
    key = ("default", size, bold)
    f = _FONT_CACHE.get(key)
    if f is None:
        f = pygame.font.Font(None, size)
        if bold:
            f.set_bold(True)
        _FONT_CACHE[key] = f
    return f


def clear_font_cache():
    _FONT_CACHE.clear()