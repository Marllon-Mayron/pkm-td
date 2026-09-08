# src/ui/utils/icon_loader.py

import pygame
from pathlib import Path
from src.config.paths import PROJECT_ROOT

_ICON_CACHE = {}


def get_held_icon() -> pygame.Surface:
    """Retorna o ícone de item segurável (holdIcon.png)"""
    if "held_icon" in _ICON_CACHE:
        return _ICON_CACHE["held_icon"]

    icon_path = PROJECT_ROOT / "res" / "PokemonSprites" / "items" / "held-itens" / "holdIcon.png"

    # Garante que o pygame está inicializado
    if not pygame.get_init():
        pygame.init()

    if icon_path.exists():
        try:
            icon = pygame.image.load(str(icon_path)).convert_alpha()
            _ICON_CACHE["held_icon"] = icon
            return icon
        except Exception as e:
            print(f"[ICON_LOADER] Erro ao carregar ícone de item: {e}")

    # Fallback: cria um ícone simples
    icon = pygame.Surface((16, 16), pygame.SRCALPHA)
    pygame.draw.circle(icon, (255, 215, 0), (8, 8), 7)
    pygame.draw.circle(icon, (255, 200, 50), (8, 8), 5)
    _ICON_CACHE["held_icon"] = icon
    return icon