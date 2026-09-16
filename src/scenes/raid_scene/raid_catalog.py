# src/data/minigames/raid_maps/raid_catalog.py
import json
import os
import random

from src.config.paths import PROJECT_ROOT
from src.config.raid_season import CURRENT_RAID_CHAPTER

RAID_MAPS_DIR = os.path.join(PROJECT_ROOT, "src", "data", "minigames", "raid_maps")
INDEX_PATH = os.path.join(RAID_MAPS_DIR, "index.json")


def _load_index():
    with open(INDEX_PATH, "r", encoding="utf-8") as f:
        return json.load(f)


def _raid_path(chapter, level):
    return os.path.join(RAID_MAPS_DIR, f"level_{chapter:02d}_{level:02d}.json")


def pick_random_raid(chapter=None):
    """
    Sorteia uma raid do capítulo. Retorna (chapter, level) ou None se vazio.

    Lê o index.json toda vez — sem cache. Simples e sempre atualizado.
    """
    if chapter is None:
        chapter = CURRENT_RAID_CHAPTER

    try:
        data = _load_index()
    except Exception as e:
        print(f"[RAID_CATALOG] Erro lendo index.json: {e}")
        return None

    # Só raids do capítulo certo que têm arquivo de mapa existindo
    candidatas = [
        (item["chapter"], item["level"])
        for item in data.get("levels", [])
        if item.get("chapter") == chapter
        and os.path.exists(_raid_path(item["chapter"], item["level"]))
    ]

    if not candidatas:
        print(f"[RAID_CATALOG] Nenhuma raid válida no capítulo {chapter}")
        return None

    escolhida = random.choice(candidatas)
    print(f"[RAID_CATALOG] Capítulo {chapter} → sorteada {escolhida}")
    return escolhida  # (chapter, level)


def get_raid_name(chapter, level):
    try:
        with open(_raid_path(chapter, level), "r", encoding="utf-8") as f:
            return json.load(f).get("name", f"Raid {chapter}-{level}")
    except Exception:
        return f"Raid {chapter}-{level}"


def get_raid_boss_id(chapter, level):
    try:
        with open(_raid_path(chapter, level), "r", encoding="utf-8") as f:
            data = json.load(f)
        waves = data.get("waves", {}).get("waves", [])
        if waves and waves[0].get("enemies"):
            return waves[0]["enemies"][0].get("pokemon_id", 146)
    except Exception:
        pass
    return 146


def get_raid_path(chapter, level):
    return _raid_path(chapter, level)