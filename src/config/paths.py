# src/config/paths.py
import os
import sys
from pathlib import Path


def get_project_root():
    """Retorna o caminho raiz do projeto corretamente (desenvolvimento ou executável)"""
    if getattr(sys, 'frozen', False):
        # Rodando como executável PyInstaller
        return Path(sys._MEIPASS)
    else:
        # Rodando como script Python normal
        # Este arquivo está em src/config/paths.py → subir 3 níveis
        current_file = Path(__file__).resolve()
        root = current_file.parent      # src/config
        root = root.parent              # src
        root = root.parent              # raiz do projeto
        return root


# Caminho absoluto da raiz do projeto
PROJECT_ROOT = get_project_root()
print(f"[PATHS] PROJECT_ROOT: {PROJECT_ROOT}")
print(f"[PATHS] É executável: {getattr(sys, 'frozen', False)}")
if getattr(sys, 'frozen', False):
    print(f"[PATHS] sys._MEIPASS: {sys._MEIPASS}")

# ===== RES / ASSETS =====
RES_PATH        = PROJECT_ROOT / "res"
ALL_TILES_PATH  = RES_PATH / "AllTiles"
SPRITES_PATH    = RES_PATH / "PokemonSprites"
ITEMS_PATH      = SPRITES_PATH / "items"
FONTS_PATH      = RES_PATH / "fontes"

# ===== DADOS JSON DO JOGO =====
DATA_PATH         = PROJECT_ROOT / "src" / "data"
SCRIPTS_PATH      = DATA_PATH / "scripts"
POKEMON_JSON_PATH = SCRIPTS_PATH / "pokemon_completo.json"

# ===== UI EDITOR =====
# Layouts salvos pelo editor visual
UI_LAYOUTS_PATH = RES_PATH / "ui_layouts"
# Cenas .py geradas pelo editor (separadas das cenas "oficiais")
SCENES_EDITOR_PATH = PROJECT_ROOT / "src" / "scenes_editor"

# Garante que existem
UI_LAYOUTS_PATH.mkdir(parents=True, exist_ok=True)
SCENES_EDITOR_PATH.mkdir(parents=True, exist_ok=True)

# ===== VERSÕES STRING =====
PROJECT_ROOT_STR        = str(PROJECT_ROOT)
RES_PATH_STR            = str(RES_PATH)
ALL_TILES_PATH_STR      = str(ALL_TILES_PATH)
SPRITES_PATH_STR        = str(SPRITES_PATH)
ITEMS_PATH_STR          = str(ITEMS_PATH)
FONTS_PATH_STR          = str(FONTS_PATH)
DATA_PATH_STR           = str(DATA_PATH)
SCRIPTS_PATH_STR        = str(SCRIPTS_PATH)
POKEMON_JSON_PATH_STR   = str(POKEMON_JSON_PATH)
UI_LAYOUTS_PATH_STR     = str(UI_LAYOUTS_PATH)
SCENES_EDITOR_PATH_STR  = str(SCENES_EDITOR_PATH)


def ensure_path(path):
    """Converte string para Path se necessário"""
    return Path(path) if isinstance(path, str) else path