# src/config/raid_season.py
"""
Configuração da TEMPORADA de raid ativa.

Capítulos = gerações:
  1 = Kanto
  2 = Johto
  3 = Hoenn
  4 = Sinnoh
  5 = Unova
  6 = Kalos
  7 = Alola
  8 = Galar
"""

CURRENT_RAID_CHAPTER = 1

# Nome da temporada (usado em logs/toasts)
SEASON_NAMES = {
    1: "Kanto",
    2: "Johto",
    3: "Hoenn",
    4: "Sinnoh",
    5: "Unova",
    6: "Kalos",
    7: "Alola",
    8: "Galar",
}


def get_season_name(chapter=None):
    if chapter is None:
        chapter = CURRENT_RAID_CHAPTER
    return SEASON_NAMES.get(chapter, f"Geração {chapter}")