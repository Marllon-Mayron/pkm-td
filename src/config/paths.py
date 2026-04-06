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
        # main.py está em src/, então precisamos subir 1 nível
        current_file = Path(__file__).resolve()
        # Vamos subir até encontrar a pasta raiz (que contém src/ e res/)
        root = current_file.parent.parent.parent
        return root

# Caminho absoluto da raiz do projeto
PROJECT_ROOT = get_project_root()
print(f"[PATHS] PROJECT_ROOT: {PROJECT_ROOT}")

# Caminhos úteis
RES_PATH = PROJECT_ROOT / "res"
ALL_TILES_PATH = RES_PATH / "AllTiles"
SPRITES_PATH = RES_PATH / "PokemonSprites"
ITEMS_PATH = SPRITES_PATH / "items"

# Convertendo para string quando necessário
PROJECT_ROOT_STR = str(PROJECT_ROOT)
RES_PATH_STR = str(RES_PATH)
ALL_TILES_PATH_STR = str(ALL_TILES_PATH)
SPRITES_PATH_STR = str(SPRITES_PATH)
ITEMS_PATH_STR = str(ITEMS_PATH)