# src/data/achievement_data.py

from dataclasses import dataclass, field
from typing import Dict, Optional, List
from enum import Enum
from datetime import datetime


class AchievementRarity(Enum):
    COMMON = "comum"
    UNCOMMON = "incomum"
    RARE = "raro"
    EPIC = "epico"
    LEGENDARY = "lendaria"

    @property
    def color(self) -> tuple:
        colors = {
            "comum": (150, 150, 150),
            "incomum": (100, 200, 100),
            "raro": (100, 150, 255),
            "epico": (200, 100, 255),
            "lendaria": (255, 215, 0)
        }
        return colors.get(self.value, (150, 150, 150))

    @property
    def display_name(self) -> str:
        names = {
            "comum": "Comum",
            "incomum": "Incomum",
            "raro": "Raro",
            "epico": "Epico",
            "lendaria": "Lendaria"
        }
        return names.get(self.value, "Comum")


@dataclass
class Achievement:
    """Estrutura de uma conquista"""
    id: str
    title: str
    description: str
    rarity: AchievementRarity
    rewards: Dict[str, int]  # {"gold": 100, "xp": 50}

    # Estado (não salvo, vem do jogador)
    unlocked: bool = False
    unlocked_at: Optional[str] = None  # Data/hora da conquista
    unlocked_phase: Optional[str] = None  # Fase onde foi obtida (ex: "1-3")


# ===== CATALOGO DE CONQUISTAS =====
ACHIEVEMENTS: Dict[str, Achievement] = {
    "first_capture": Achievement(
        id="first_capture",
        title="Primeiro Passo",
        description="Capture seu primeiro Pokemon",
        rarity=AchievementRarity.COMMON,
        rewards={"gold": 50, "xp": 20}
    ),
    "heal_5": Achievement(
        id="heal_5",
        title="Curandeiro Iniciante",
        description="Cure seus Pokemon 5 vezes",
        rarity=AchievementRarity.COMMON,
        rewards={"gold": 30, "xp": 15}
    ),
    "first_badge": Achievement(
        id="first_badge",
        title="Primeira Insignia",
        description="Ganhe sua primeira insignia",
        rarity=AchievementRarity.COMMON,
        rewards={"gold": 100, "xp": 50}
    ),
    "capture_10": Achievement(
        id="capture_10",
        title="Colecionador Iniciante",
        description="Capture 10 Pokemon diferentes",
        rarity=AchievementRarity.COMMON,
        rewards={"gold": 150, "xp": 75}
    ),
    "heal_100": Achievement(
        id="heal_100",
        title="Mestre Curandeiro",
        description="Cure seus Pokemon 100 vezes",
        rarity=AchievementRarity.UNCOMMON,
        rewards={"gold": 500, "xp": 200}
    ),
    "capture_50": Achievement(
        id="capture_50",
        title="Colecionador intermediário",
        description="Capture 50 Pokemon diferentes",
        rarity=AchievementRarity.RARE,
        rewards={"gold": 1000, "xp": 500}
    ),
    "perfect_phase": Achievement(
        id="perfect_phase",
        title="Fase Perfeita",
        description="Complete uma fase sem perder nenhum item",
        rarity=AchievementRarity.UNCOMMON,
        rewards={"gold": 200, "xp": 100}
    ),
    "boss_defeated": Achievement(
        id="boss_defeated",
        title="Cacador de Chefes",
        description="Derrote seu primeiro chefe",
        rarity=AchievementRarity.RARE,
        rewards={"gold": 300, "xp": 150}
    ),
}


def get_achievement(achievement_id: str) -> Optional[Achievement]:
    """Retorna uma conquista pelo ID"""
    return ACHIEVEMENTS.get(achievement_id)


def get_all_achievements() -> List[Achievement]:
    """Retorna todas as conquistas"""
    return list(ACHIEVEMENTS.values())


def get_achievements_by_rarity(rarity: AchievementRarity) -> List[Achievement]:
    """Retorna conquistas por raridade"""
    return [a for a in ACHIEVEMENTS.values() if a.rarity == rarity]