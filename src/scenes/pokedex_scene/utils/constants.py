# src/scenes/pokedex_scene/utils/constants.py
"""
Constantes de DOMÍNIO da Pokédex.

Tudo aqui é dado puro (tipos, faixas de ID, filtros).
Cores, tamanhos e posições vivem no layout JSON (`res/ui_layouts/pokedex.json`).
"""

# =========================================================================
# TIPOS DE POKÉMON E SUAS CORES
# =========================================================================
# Usado pelas badges de tipo no painel de detalhe (via PokedexLogic).
TYPE_COLORS = {
    "normal":   (168, 168, 120),
    "fire":     (240, 128, 48),
    "water":    (104, 144, 240),
    "electric": (248, 208, 48),
    "grass":    (120, 200, 80),
    "ice":      (152, 216, 216),
    "fighting": (192, 48, 40),
    "poison":   (160, 64, 160),
    "ground":   (224, 192, 104),
    "flying":   (168, 144, 240),
    "psychic":  (248, 88, 136),
    "bug":      (168, 184, 32),
    "rock":     (184, 160, 56),
    "ghost":    (112, 88, 152),
    "dragon":   (112, 56, 248),
    "dark":     (112, 88, 72),
    "steel":    (184, 184, 208),
    "fairy":    (238, 153, 172),
}

# =========================================================================
# FILTROS DE STATUS
# =========================================================================
# Chave interna usada pela lógica (PokedexLogic.filter_type).
FILTERS = {
    'ALL':        'all',
    'CAUGHT':     'caught',
    'SEEN':       'seen',
    'UNSEEN':     'unseen',
    'NOT_CAUGHT': 'not_caught',
}

# =========================================================================
# REGIÕES
# =========================================================================
# Chave interna usada pela lógica (PokedexLogic.region).
REGIONS = {
    'ALL':   'all',
    'KANTO': 'kanto',
    'JOHTO': 'johto',
    'HOENN': 'hoenn',
}

# Faixas de IDs por região (inclusive nos dois extremos).
REGION_RANGES = {
    'kanto': (1, 151),
    'johto': (152, 251),
    'hoenn': (252, 386),
}