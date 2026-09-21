# src/data/minigames/arena_maps/arena_catalog.py
"""
Catálogo de arenas de PvP.

Os arquivos de arena ficam em:
    src/data/minigames/arena_maps/
        index.json
        level_01_01.json   -> 1v1  (2 spots)
        level_02_01.json   -> 2v2  (4 spots)
        level_03_01.json   -> 3v3  (6 spots)

Por compatibilidade, se a pasta arena_maps não existir, cai no raid_maps.
"""
import json
import os

from src.config.paths import PROJECT_ROOT

_ARENA_DIR = os.path.join(PROJECT_ROOT, "src", "data", "minigames", "arena_maps")
_FALLBACK_DIR = os.path.join(PROJECT_ROOT, "src", "data", "minigames", "raid_maps")


def _maps_dir():
    if os.path.exists(os.path.join(_ARENA_DIR, "index.json")):
        return _ARENA_DIR
    return _FALLBACK_DIR


def _arena_path(chapter, level):
    return os.path.join(_maps_dir(), f"level_{chapter:02d}_{level:02d}.json")


def get_arena_path(chapter, level):
    return _arena_path(chapter, level)


def load_arena(chapter, level):
    path = _arena_path(chapter, level)
    if not os.path.exists(path):
        return None
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception as e:
        print(f"[ARENA_CATALOG] Erro lendo {path}: {e}")
        return None


def get_arena_name(chapter, level):
    data = load_arena(chapter, level)
    if data:
        return data.get("name", f"Arena {chapter}-{level}")
    return f"Arena {chapter}-{level}"


def get_arena_spots(chapter, level):
    """Retorna a lista bruta de spots do mapa."""
    data = load_arena(chapter, level)
    if not data:
        return []
    return data.get("tower_spots", {}).get("spots", [])


def get_arena_spot_count(chapter, level):
    return len(get_arena_spots(chapter, level))


def get_arena_format(chapter):
    """(tamanho_do_time, nome_do_formato) por capítulo."""
    return {1: (1, "1v1"), 2: (2, "2v2"), 3: (3, "3v3")}.get(chapter, (1, "1v1"))


def list_arenas(chapter=None):
    """Lista de tuplas (chapter, level) válidas."""
    index_path = os.path.join(_maps_dir(), "index.json")
    if not os.path.exists(index_path):
        return []
    try:
        with open(index_path, "r", encoding="utf-8") as f:
            data = json.load(f)
    except Exception:
        return []

    out = []
    for item in data.get("levels", []):
        ch = item.get("chapter")
        lv = item.get("level")
        if chapter is not None and ch != chapter:
            continue
        if os.path.exists(_arena_path(ch, lv)):
            out.append((ch, lv))
    return out


def split_spots_for_teams(spots):
    """
    Divide spots em (team_player, team_enemy) por Y.
    Convenção: Y maior = baixo da tela = jogador local.
    """
    sorted_spots = sorted(spots, key=lambda s: s.get("y", 0))
    half = len(sorted_spots) // 2
    enemy_spots = sorted_spots[:half]   # topo (y pequeno)
    player_spots = sorted_spots[half:]  # baixo (y grande)
    return player_spots, enemy_spots