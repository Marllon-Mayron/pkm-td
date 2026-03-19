# src/config/paths.py
import os

# Caminho absoluto da raiz do projeto
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
print(f"[PATHS] PROJECT_ROOT: {PROJECT_ROOT}")

# Caminhos úteis
RES_PATH = os.path.join(PROJECT_ROOT, "res")
ALL_TILES_PATH = os.path.join(RES_PATH, "AllTiles")
SPRITES_PATH = os.path.join(RES_PATH, "PokemonSprites")
ITEMS_PATH = os.path.join(SPRITES_PATH, "items")