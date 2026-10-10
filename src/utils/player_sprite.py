# src/utils/player_sprite.py
"""
Renderiza o sprite do jogador em camadas (estilo GBA).

As camadas vêm do item_bag_catalog (categoria='clothing', campo 'slot').
Ordem de empilhamento (baixo → cima):
    skin → pants → shoes → torso → hair

Se nenhuma camada carregar, desenha um placeholder colorido.
"""
import pygame
from pathlib import Path
from typing import Optional


LAYER_ORDER = ["skin", "eyes", "pants", "torso", "hair", "hat"]

_appearance_cache = {}


def _appearance_key(appearance: dict) -> tuple:
    return tuple(str(appearance.get(s, "")) for s in LAYER_ORDER)


def _placeholder_sprite(size=(32, 32)) -> pygame.Surface:
    """Fallback visual se não houver nenhuma peça válida."""
    surf = pygame.Surface(size, pygame.SRCALPHA)
    w, h = size
    # corpo
    pygame.draw.rect(surf, (60, 80, 140),
                     (w // 4, h // 3, w // 2, h // 2),
                     border_radius=2)
    # cabeça
    pygame.draw.circle(surf, (200, 160, 130), (w // 2, h // 3), w // 5)
    # olhos
    pygame.draw.circle(surf, (0, 0, 0),
                       (w // 2 - 2, h // 3 - 1), max(1, w // 20))
    pygame.draw.circle(surf, (0, 0, 0),
                       (w // 2 + 2, h // 3 - 1), max(1, w // 20))
    return surf


def render_player_sprite(appearance: dict, size=(32, 32),
                         use_cache: bool = True) -> pygame.Surface:
    """Monta o sprite empilhando as camadas na ordem certa."""
    if not isinstance(appearance, dict):
        appearance = {}

    key = (_appearance_key(appearance), size)
    if use_cache and key in _appearance_cache:
        return _appearance_cache[key]

    try:
        from src.data.item_bag_catalog import item_bag_catalog
    except Exception as e:
        print(f"[player_sprite] import catalog falhou: {e}")
        surf = _placeholder_sprite(size)
        _appearance_cache[key] = surf
        return surf

    surf = pygame.Surface(size, pygame.SRCALPHA)
    loaded = 0

    for slot in LAYER_ORDER:
        item_id = appearance.get(slot)
        if not item_id:
            continue
        data = item_bag_catalog.items.get(item_id)
        if not data:
            continue
        path = data.get("sprite_path")
        if not path:
            continue
        p = Path(str(path))
        if not p.exists():
            continue
        try:
            layer = pygame.image.load(str(p)).convert_alpha()
        except Exception as e:
            print(f"[player_sprite] erro carregando {p}: {e}")
            continue
        if layer.get_size() != size:
            layer = pygame.transform.scale(layer, size)
        surf.blit(layer, (0, 0))
        loaded += 1

    if loaded == 0:
        surf = _placeholder_sprite(size)

    _appearance_cache[key] = surf
    return surf


def clear_cache():
    _appearance_cache.clear()