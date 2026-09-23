# src/data/pvp_catalog.py
"""
Catálogo de arenas PvP entre jogadores.

Mapas em: src/data/minigames/pvp_maps/
    level_01_01.json  → 1v1  (1 spot por lado, 6 pokémon de time)
    level_02_01.json  → 2v2  (2 spots por lado, 3 pokémon por jogador)
    level_03_01.json  → 3v3  (6 spots por lado, 2 pokémon por jogador)
"""
import json
import os

from src.config.paths import PROJECT_ROOT

PVP_DIR = os.path.join(PROJECT_ROOT, "src", "data", "minigames", "pvp_maps")


def _pvp_path(chapter, level):
    return os.path.join(PVP_DIR, f"level_{chapter:02d}_{level:02d}.json")


def get_pvp_path(chapter, level):
    return _pvp_path(chapter, level)


def load_pvp(chapter, level):
    path = _pvp_path(chapter, level)
    if not os.path.exists(path):
        return None
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception as e:
        print(f"[PVP_CATALOG] Erro lendo {path}: {e}")
        return None


def get_pvp_name(chapter, level):
    data = load_pvp(chapter, level)
    return data.get("name", f"PvP {chapter}-{level}") if data else f"PvP {chapter}-{level}"


def get_pvp_spots(chapter, level):
    data = load_pvp(chapter, level)
    if not data:
        return []
    return data.get("tower_spots", {}).get("spots", [])


def get_pvp_spot_count(chapter, level):
    return len(get_pvp_spots(chapter, level))


# =====================================================================
# FORMATOS
# =====================================================================
def get_pvp_format(chapter):
    """
    Retorna (players_per_team, team_size, spots_per_player, label).

    Regras:
      1v1 → 1 jogador/time · time de 6 · 1 spot por jogador (1 vs 1)
      2v2 → 2 jogadores/time · time de 3 · 1 spot por jogador (2 vs 2)
      3v3 → 3 jogadores/time · time de 2 · 2 spots por jogador (6 vs 6)
    """
    return {
        1: (1, 6, 1, "1v1"),
        2: (2, 3, 1, "2v2"),
        3: (3, 2, 2, "3v3"),
    }.get(chapter, (1, 6, 1, "1v1"))


def get_pvp_team_size(chapter):
    """Quantos pokémon cada jogador seleciona na tela de seleção."""
    _, team_size, _, _ = get_pvp_format(chapter)
    return team_size


def get_pvp_spots_per_player(chapter):
    """Quantos spots cada jogador preenche no mapa."""
    _, _, spots, _ = get_pvp_format(chapter)
    return spots


def get_pvp_total_players(chapter):
    """Total de jogadores na partida (ambos os times)."""
    players, _, _, _ = get_pvp_format(chapter)
    return players * 2


def get_pvp_total_on_field(chapter):
    """Total de pokémon em campo POR TIME (players * spots)."""
    players, _, spots, _ = get_pvp_format(chapter)
    return players * spots


def list_pvps(chapter=None):
    index_path = os.path.join(PVP_DIR, "index.json")
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
        if os.path.exists(_pvp_path(ch, lv)):
            out.append((ch, lv))
    return out


# =====================================================================
# DIVISÃO DE SPOTS
# =====================================================================
def split_spots_for_teams(spots):
    """
    Divide spots em (team_a, team_b) por Y.
    Y maior = baixo = time A (jogador local).
    Y menor = topo  = time B.
    """
    sorted_spots = sorted(spots, key=lambda s: s.get("y", 0))
    half = len(sorted_spots) // 2
    team_b = sorted_spots[:half]   # topo
    team_a = sorted_spots[half:]   # baixo
    return team_a, team_b


def split_team_spots_among_players(team_spots, num_players):
    """
    Divide os spots de um time entre seus jogadores (ordem por X).

    Exemplos:
      1v1: 1 spot  + 1 player  → [[spot]]
      2v2: 2 spots + 2 players → [[sA], [sB]]
      3v3: 6 spots + 3 players → [[s1,s2], [s3,s4], [s5,s6]]
    """
    sorted_spots = sorted(team_spots, key=lambda s: s.get("x", 0))

    if num_players <= 1:
        return [sorted_spots]

    per_player = len(sorted_spots) // num_players
    result = []
    for i in range(num_players):
        start = i * per_player
        end = start + per_player if i < num_players - 1 else len(sorted_spots)
        result.append(sorted_spots[start:end])
    return result