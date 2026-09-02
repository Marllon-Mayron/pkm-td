# src/scenes/pokedex_scene/utils/constants.py

"""
Constantes para a Pokédex
"""

# Cores da Pokédex
COLORS = {
    'bg_primary': (20, 22, 27),
    'bg_secondary': (28, 30, 36),
    'bg_tertiary': (35, 38, 45),
    'bg_card': (40, 42, 50),
    'bg_list_item': (32, 34, 40),
    'bg_list_item_hover': (50, 52, 60),
    'bg_list_item_selected': (60, 80, 120),
    'bg_list_item_unseen': (25, 27, 32),
    'border': (60, 65, 80),
    'border_light': (80, 85, 105),
    'border_gold': (200, 180, 100),
    'text_primary': (240, 242, 245),
    'text_secondary': (160, 165, 180),
    'text_accent': (255, 215, 0),
    'text_good': (100, 200, 100),
    'text_caught': (100, 220, 100),
    'text_not_caught': (200, 100, 100),
    'text_unknown': (80, 80, 90),
    'text_unseen': (60, 60, 70),
    'hp_green': (0, 200, 0),
    'hp_yellow': (255, 200, 0),
    'hp_red': (255, 50, 50),
    'stat_bar': (80, 140, 200),
    'icon_bg': (45, 48, 55),
    'shiny_glow': (255, 215, 0, 80),
}

# Tipos de Pokémon e suas cores
TYPE_COLORS = {
    "normal": (168, 168, 120),
    "fire": (240, 128, 48),
    "water": (104, 144, 240),
    "electric": (248, 208, 48),
    "grass": (120, 200, 80),
    "ice": (152, 216, 216),
    "fighting": (192, 48, 40),
    "poison": (160, 64, 160),
    "ground": (224, 192, 104),
    "flying": (168, 144, 240),
    "psychic": (248, 88, 136),
    "bug": (168, 184, 32),
    "rock": (184, 160, 56),
    "ghost": (112, 88, 152),
    "dragon": (112, 56, 248),
    "dark": (112, 88, 72),
    "steel": (184, 184, 208),
    "fairy": (238, 153, 172),
}

# Filtros da Pokédex
FILTERS = {
    'ALL': 'all',
    'CAUGHT': 'caught',
    'SEEN': 'seen',
    'UNSEEN': 'unseen',
    'NOT_CAUGHT': 'not_caught',
}

# Tamanhos
SIZES = {
    'list_item_height': 90,
    'detail_padding': 20,
    'sprite_size': 180,
    'inmap_sprite_size': 96,
    'header_height': 80,
    'filter_height': 40,
    'padding': 15,
    'gap': 10,
}