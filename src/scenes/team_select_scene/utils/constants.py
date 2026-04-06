# Constantes de cores
COLORS = {
    'BACKGROUND': {
        'BASE': (10, 10, 13),
        'GRADIENT_START': 10,
        'GRADIENT_END': 30
    },
    'SLOT': {
        'DEFAULT': (45, 45, 55),
        'HOVER': (70, 70, 90),
        'SELECTED': (100, 150, 200),
        'BORDER': (80, 80, 100),
        'BORDER_HOVER': (120, 120, 140),
        'BORDER_SELECTED': (150, 200, 250),
        'SHADOW': (20, 20, 25),
        'EMPTY_PLUS': (100, 100, 110)
    },
    'GRID': {
        'DEFAULT': (35, 35, 45),
        'HOVER': (60, 60, 80),
        'IN_TEAM': (40, 60, 40),
        'BORDER': (60, 60, 80),
        'BORDER_HOVER': (100, 100, 140),
        'BORDER_IN_TEAM': (70, 120, 70),
        'SHADOW': (15, 15, 20)
    },
    'BUTTON': {
        'DEFAULT': (50, 50, 55),
        'BORDER': (90, 90, 100),
        'ACTIVE': (60, 60, 70),
        'INACTIVE': (40, 40, 45),
        'START_ACTIVE': (70, 120, 70),
        'START_INACTIVE': (50, 50, 55),
        'MODAL_ACTION_ADD': (80, 150, 80),
        'MODAL_ACTION_REMOVE': (150, 80, 80),
        'MODAL_ACTION_DISABLED': (80, 80, 80)
    },
    'FILTERS': {
        'BACKGROUND': (25, 27, 32),
        'BORDER': (55, 58, 65),
        'SEARCH_DEFAULT': (35, 38, 45),
        'SEARCH_ACTIVE': (40, 45, 55),
        'SEARCH_BORDER': (70, 75, 85),
        'SEARCH_BORDER_ACTIVE': (100, 150, 200),
        'SORT_DEFAULT': (45, 48, 55),
        'SORT_ACTIVE': (70, 120, 70),
        'SORT_BORDER': (80, 85, 95),
    },
    'TEXT': {
        'WHITE': (255, 255, 255),
        'GRAY': (200, 200, 200),
        'DARK_GRAY': (150, 150, 160),
        'YELLOW': (255, 255, 100),
        'GREEN': (150, 255, 150),
        'HP_GREEN': (0, 200, 0),
        'HP_YELLOW': (255, 255, 0),
        'HP_RED': (255, 0, 0)
    },
    'MODAL': {
        'BACKGROUND': (30, 30, 40),
        'BORDER': (100, 100, 150),
        'CLOSE_BUTTON': (60, 60, 70),
        'CLOSE_BORDER': (150, 150, 150)
    }
}
FILTER_BUTTONS = {
    'CAPTURE': {'label': 'CAPTURA', 'sort_type': 'capture'},
    'NAME_ASC': {'label': 'A-Z', 'sort_type': 'name_asc'},
    'NAME_DESC': {'label': 'Z-A', 'sort_type': 'name_desc'},
    'ID_ASC': {'label': 'ID ↑', 'sort_type': 'id_asc'},
    'ID_DESC': {'label': 'ID ↓', 'sort_type': 'id_desc'},
}
# Configurações de layout
LAYOUT = {
    'MARGIN': 30,
    'TOP_MARGIN': 80,
    'SLOT': {
        'WIDTH': 160,
        'HEIGHT': 110,
        'SPACING': 10
    },
    'GRID': {
        'COLS': 6,
        'CARD_WIDTH': 140,
        'CARD_HEIGHT': 90,
        'SPACING': 10
    },
    'BUTTON': {
        'WIDTH': 100,
        'HEIGHT': 40,
        'PAGE_WIDTH': 80
    }
}

# Configurações de fonte
FONT_SIZES = {
    'TITLE': 48,
    'SLOT': 20,
    'GRID': 18,
    'PAGE': 24,
    'MODAL_TITLE': 28,
    'MODAL_TEXT': 22,
    'SMALL': 18
}