# src/config/paths.py
import os
import sys
from pathlib import Path


def get_project_root():
    """Retorna o caminho raiz do projeto corretamente (desenvolvimento ou executável)"""
    if getattr(sys, 'frozen', False):
        # Rodando como executável PyInstaller
        # sys._MEIPASS já é um Path? Não, é string, mas vamos converter
        return Path(sys._MEIPASS)
    else:
        # Rodando como script Python normal
        # Vamos encontrar a raiz do projeto (onde está a pasta src/ e res/)
        current_file = Path(__file__).resolve()

        # Procura pela pasta src (este arquivo está em src/config/paths.py)
        # Subimos até encontrar a pasta que contém src/
        root = current_file.parent  # src/config
        root = root.parent  # src
        root = root.parent  # raiz do projeto (pkm-td)

        return root


# Caminho absoluto da raiz do projeto
PROJECT_ROOT = get_project_root()
print(f"[PATHS] PROJECT_ROOT: {PROJECT_ROOT}")
print(f"[PATHS] É executável: {getattr(sys, 'frozen', False)}")
if getattr(sys, 'frozen', False):
    print(f"[PATHS] sys._MEIPASS: {sys._MEIPASS}")

# Caminhos úteis - TODOS como Path objects
RES_PATH = PROJECT_ROOT / "res"
ALL_TILES_PATH = RES_PATH / "AllTiles"
SPRITES_PATH = RES_PATH / "PokemonSprites"
ITEMS_PATH = SPRITES_PATH / "items"

# Caminho para os dados JSON
DATA_PATH = PROJECT_ROOT / "src" / "data"
SCRIPTS_PATH = DATA_PATH / "scripts"
POKEMON_JSON_PATH = SCRIPTS_PATH / "pokemon_completo.json"

# Convertendo para string quando necessário (apenas para compatibilidade)
PROJECT_ROOT_STR = str(PROJECT_ROOT)
RES_PATH_STR = str(RES_PATH)
ALL_TILES_PATH_STR = str(ALL_TILES_PATH)
SPRITES_PATH_STR = str(SPRITES_PATH)
ITEMS_PATH_STR = str(ITEMS_PATH)
DATA_PATH_STR = str(DATA_PATH)
SCRIPTS_PATH_STR = str(SCRIPTS_PATH)
POKEMON_JSON_PATH_STR = str(POKEMON_JSON_PATH)


# Função auxiliar para garantir que temos Path objects
def ensure_path(path):
    """Converte string para Path se necessário"""
    return Path(path) if isinstance(path, str) else path