# src/config/regions.py
"""
Definições de Regiões (Gerações) do jogo.

Formato canônico de phase_id: "region:chapter:phase"
  - Ex: "1:1:1" -> Kanto, Capítulo 1, Fase 1
  - Ex: "3:1:1" -> Hoenn, Capítulo 1, Fase 1

Fallback (retrocompatibilidade): quando não há região, assume 1 (Kanto).
"""
from dataclasses import dataclass
from typing import Dict, List, Optional


# Região padrão usada como fallback em IDs antigos (ex: "1-1" -> "1:1:1")
DEFAULT_REGION_ID = 1


@dataclass(frozen=True)
class Region:
    id: int
    name: str
    short: str
    generation: int


# ============================================================
# CATÁLOGO DE REGIÕES
# ============================================================
REGIONS: Dict[int, Region] = {
    1: Region(id=1, name="Kanto",  short="KAN", generation=1),
    2: Region(id=2, name="Johto",  short="JOH", generation=2),
    3: Region(id=3, name="Hoenn",  short="HOE", generation=3),
    4: Region(id=4, name="Sinnoh", short="SIN", generation=4),
    5: Region(id=5, name="Unova",  short="UNO", generation=5),
    6: Region(id=6, name="Kalos",  short="KAL", generation=6),
    7: Region(id=7, name="Alola",  short="ALO", generation=7),
    8: Region(id=8, name="Galar",  short="GAL", generation=8),
}


class RegionCatalog:
    """Catálogo central de regiões."""

    @staticmethod
    def get_all() -> List[Region]:
        return [REGIONS[k] for k in sorted(REGIONS.keys())]

    @staticmethod
    def get(region_id: int) -> Optional[Region]:
        return REGIONS.get(region_id)

    @staticmethod
    def exists(region_id: int) -> bool:
        return region_id in REGIONS

    @staticmethod
    def get_name(region_id: int) -> str:
        r = REGIONS.get(region_id)
        return r.name if r else f"Região {region_id}"

    @staticmethod
    def get_short(region_id: int) -> str:
        r = REGIONS.get(region_id)
        return r.short if r else f"R{region_id}"


# ============================================================
# HELPERS DE PHASE_ID
# ============================================================
def parse_phase_id(phase_id: str) -> tuple:
    """
    Converte qualquer phase_id em (region, chapter, phase).

    Formatos aceitos:
      - "1:1:1"  -> (1, 1, 1)
      - "1-1"    -> (1, 1, 1)   [legado, região 1 = Kanto]
      - inválido -> (1, 1, 1)   [fallback Kanto]
    """
    if not phase_id:
        return (DEFAULT_REGION_ID, 1, 1)

    s = str(phase_id).strip()

    # Formato novo: region:chapter:phase
    if ":" in s:
        parts = s.split(":")
        if len(parts) == 3:
            try:
                return (int(parts[0]), int(parts[1]), int(parts[2]))
            except (ValueError, TypeError):
                pass
        elif len(parts) == 2:
            # region:chapter (raro)
            try:
                return (int(parts[0]), int(parts[1]), 1)
            except (ValueError, TypeError):
                pass

    # Formato legado: chapter-phase
    if "-" in s:
        parts = s.split("-")
        if len(parts) == 2:
            try:
                return (DEFAULT_REGION_ID, int(parts[0]), int(parts[1]))
            except (ValueError, TypeError):
                pass

    return (DEFAULT_REGION_ID, 1, 1)


def make_phase_id(region_id: int, chapter: int, phase: int) -> str:
    """Constrói phase_id no formato canônico novo."""
    return f"{int(region_id)}:{int(chapter)}:{int(phase)}"


def normalize_phase_id(phase_id: str) -> str:
    """Converte qualquer phase_id para o formato canônico novo."""
    r, c, p = parse_phase_id(phase_id)
    return make_phase_id(r, c, p)