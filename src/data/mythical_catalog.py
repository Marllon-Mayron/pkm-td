# src/data/mythical_catalog.py
"""
Catálogo de Pokémon Míticos e suas localizações.
"""
from dataclasses import dataclass
from typing import Dict, List, Optional, Set


@dataclass(frozen=True)
class MythicalEntry:
    pokemon_id: int
    name: str
    phases: tuple

MYTHICALS: Dict[int, MythicalEntry] = {
    # ===== GEN 1 =====
    151: MythicalEntry(
        pokemon_id=151,
        name="Mew",
        phases=("4-1", "6-7", "6-4"),
    ),
    # ===== GEN 2 =====
    251: MythicalEntry(
        pokemon_id=251,
        name="Celebi",
        phases=("2-1", "2-2", "2-3", "7-1"),
    ),
}


class MythicalCatalog:
    """Catálogo central de Pokémon míticos."""

    @staticmethod
    def get_all() -> List[MythicalEntry]:
        return list(MYTHICALS.values())

    @staticmethod
    def get_all_ids() -> List[int]:
        return list(MYTHICALS.keys())

    @staticmethod
    def get_mythical(pokemon_id: int) -> Optional[MythicalEntry]:
        return MYTHICALS.get(pokemon_id)

    @staticmethod
    def get_phases_for_mythical(pokemon_id: int) -> List[str]:
        entry = MYTHICALS.get(pokemon_id)
        return list(entry.phases) if entry else []

    @staticmethod
    def get_mythicals_for_phase(phase_id: str) -> List[MythicalEntry]:
        return [m for m in MYTHICALS.values() if phase_id in m.phases]

    @staticmethod
    def is_mythical(pokemon_id: int) -> bool:
        return pokemon_id in MYTHICALS

    @staticmethod
    def get_all_phases_with_mythicals() -> Set[str]:
        phases: Set[str] = set()
        for m in MYTHICALS.values():
            phases.update(m.phases)
        return phases