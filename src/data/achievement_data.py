# src/data/achievement_data.py

from dataclasses import dataclass, field
from typing import Dict, Optional, List, Any
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
    id: str
    title: str
    description: str
    rarity: AchievementRarity
    rewards: Dict[str, Any]

    # Estado (não salvo, vem do jogador)
    unlocked: bool = False
    unlocked_at: Optional[str] = None  # Data/hora da conquista
    unlocked_phase: Optional[str] = None  # Fase onde foi obtida (ex: "1-3")


# ===== CATALOGO DE CONQUISTAS =====
ACHIEVEMENTS: Dict[str, Achievement] = {
    # ===== CONQUISTAS EXISTENTES (VALORES AJUSTADOS) =====
    "first_capture": Achievement(
        id="first_capture",
        title="Primeiro Passo",
        description="Capture seu primeiro Pokemon",
        rarity=AchievementRarity.COMMON,
        rewards={"gold": 100, "xp": 50}
    ),
    "heal_5": Achievement(
        id="heal_5",
        title="Curandeiro Iniciante",
        description="Cure seus Pokemon 5 vezes",
        rarity=AchievementRarity.COMMON,
        rewards={"gold": 200, "xp": 50}
    ),
    "first_badge": Achievement(
        id="first_badge",
        title="Primeira Insignia",
        description="Ganhe sua primeira insignia",
        rarity=AchievementRarity.COMMON,
        rewards={"gold": 200, "xp": 100}
    ),
    "capture_10": Achievement(
        id="capture_10",
        title="Colecionador Iniciante",
        description="Capture 10 Pokemon diferentes",
        rarity=AchievementRarity.COMMON,
        rewards={"gold": 300, "xp": 150, "items": {"ultraball": 3}}
    ),
    "heal_100": Achievement(
        id="heal_100",
        title="Mestre Curandeiro",
        description="Cure seus Pokemon 100 vezes",
        rarity=AchievementRarity.UNCOMMON,
        rewards={"gold": 1000, "xp": 500, "pokemon": 113}
    ),
    "capture_50": Achievement(
        id="capture_50",
        title="Colecionador Intermediario",
        description="Capture 50 Pokemon diferentes",
        rarity=AchievementRarity.RARE,
        rewards={"gold": 2000, "xp": 1000}
    ),
    "perfect_phase": Achievement(
        id="perfect_phase",
        title="Fase Perfeita",
        description="Complete uma fase sem perder nenhum item",
        rarity=AchievementRarity.UNCOMMON,
        rewards={"gold": 400, "xp": 200}
    ),
    "boss_defeated": Achievement(
        id="boss_defeated",
        title="Cacador de Chefes",
        description="Derrote seu primeiro chefe",
        rarity=AchievementRarity.RARE,
        rewards={"gold": 600, "xp": 300}
    ),

    # ===== CONQUISTAS DE CLIMA =====
    "first_weather_change": Achievement(
        id="first_weather_change",
        title="Mestre do Clima Iniciante",
        description="Mude o clima pela primeira vez usando um movimento",
        rarity=AchievementRarity.COMMON,
        rewards={"gold": 100, "xp": 50}
    ),
    "weather_change_50": Achievement(
        id="weather_change_50",
        title="Mestre do Clima Intermediario",
        description="Mude o clima 50 vezes usando movimentos",
        rarity=AchievementRarity.UNCOMMON,
        rewards={"gold": 600, "xp": 300}
    ),
    "weather_change_100": Achievement(
        id="weather_change_100",
        title="Mestre do Clima Absoluto",
        description="Mude o clima 100 vezes usando movimentos",
        rarity=AchievementRarity.EPIC,
        rewards={"gold": 1500, "xp": 750}
    ),
    "first_weather_boosted_attack": Achievement(
        id="first_weather_boosted_attack",
        title="Poder do Clima",
        description="Tenha seu primeiro ataque fortalecido pelo clima",
        rarity=AchievementRarity.COMMON,
        rewards={"gold": 100, "xp": 50}
    ),

    # ===== CONQUISTAS DE EVOLUÇÃO (GERAL) =====
    "first_evolution": Achievement(
        id="first_evolution",
        title="A Nova Forma!",
        description="Evolua um Pokemon pela primeira vez",
        rarity=AchievementRarity.COMMON,
        rewards={"gold": 150, "xp": 75}
    ),
    "evolution_10": Achievement(
        id="evolution_10",
        title="Mestre das Transformações",
        description="Evolua Pokemon 10 vezes",
        rarity=AchievementRarity.UNCOMMON,
        rewards={"gold": 600, "xp": 300}
    ),
    "evolution_50": Achievement(
        id="evolution_50",
        title="Arquiteto da Evolução",
        description="Evolua Pokemon 50 vezes",
        rarity=AchievementRarity.EPIC,
        rewards={"gold": 2000, "xp": 1000}
    ),

    # ===== CONQUISTAS DE EVOLUÇÃO POR NÍVEL =====
    "first_level_evolution": Achievement(
        id="first_level_evolution",
        title="Nova Etapa",
        description="Evolua seu primeiro Pokemon por nivel",
        rarity=AchievementRarity.COMMON,
        rewards={"gold": 120, "xp": 60}
    ),
    "level_evolution_50": Achievement(
        id="level_evolution_50",
        title="Mestre da Evolução",
        description="Evolua 50 Pokemon por nivel",
        rarity=AchievementRarity.LEGENDARY,
        rewards={"gold": 3000, "xp": 1500}
    ),

    # ===== CONQUISTAS DE EVOLUÇÃO POR PEDRA =====
    "first_stone_evolution": Achievement(
        id="first_stone_evolution",
        title="Pedra Fundamental",
        description="Evolua seu primeiro Pokemon com uma pedra de evolucao",
        rarity=AchievementRarity.COMMON,
        rewards={"gold": 150, "xp": 75}
    ),
    "stone_evolution_5": Achievement(
        id="stone_evolution_5",
        title="Mestre Lapidador",
        description="Evolua 5 Pokemon com pedras de evolucao",
        rarity=AchievementRarity.UNCOMMON,
        rewards={"gold": 600, "xp": 300}
    ),
    "stone_evolution_20": Achievement(
        id="stone_evolution_20",
        title="Colecionador de Pedras",
        description="Evolua 20 Pokemon com pedras de evolucao",
        rarity=AchievementRarity.EPIC,
        rewards={"gold": 2000, "xp": 1000}
    ),

    # ===== CONQUISTAS DE EVOLUÇÃO POR FELICIDADE =====
    "max_happiness": Achievement(
        id="max_happiness",
        title="Amor Incondicional",
        description="Alcance a felicidade máxima com um Pokemon (255)",
        rarity=AchievementRarity.UNCOMMON,
        rewards={"gold": 500, "xp": 500}
    ),
    "full_team_max_happiness": Achievement(
        id="full_team_max_happiness",
        title="Familia Feliz",
        description="Tenha toda sua equipe com felicidade máxima (255)",
        rarity=AchievementRarity.EPIC,
        rewards={"gold": 5000, "xp": 7500}
    ),
    "first_happiness_evolution": Achievement(
        id="first_happiness_evolution",
        title="Laco de Amizade",
        description="Evolua seu primeiro Pokemon por felicidade",
        rarity=AchievementRarity.UNCOMMON,
        rewards={"gold": 500, "xp": 300}
    ),
    "happiness_evolution_3": Achievement(
        id="happiness_evolution_3",
        title="Coracao de Ouro",
        description="Evolua 3 Pokemon por felicidade",
        rarity=AchievementRarity.RARE,
        rewards={"gold": 1000, "xp": 500}
    ),
    "happiness_evolution_10": Achievement(
        id="happiness_evolution_10",
        title="Mestre da Amizade",
        description="Evolua 10 Pokemon por felicidade",
        rarity=AchievementRarity.EPIC,
        rewards={"gold": 3000, "xp": 1500}
    ),

    # ===== CONQUISTAS DE EVOLUÇÃO POR CLIMA =====
    "first_weather_evolution": Achievement(
        id="first_weather_evolution",
        title="Clima Favoravel",
        description="Evolua um Pokemon baseado no clima (dia/noite)",
        rarity=AchievementRarity.UNCOMMON,
        rewards={"gold": 400, "xp": 250}
    ),
    "weather_evolution_5": Achievement(
        id="weather_evolution_5",
        title="Mestre das Estacoes",
        description="Evolua 5 Pokemon baseados no clima",
        rarity=AchievementRarity.RARE,
        rewards={"gold": 1000, "xp": 500}
    ),

    # ===== CONQUISTAS DE BLOQUEIO DE EVOLUÇÃO =====
    "first_evolution_blocked": Achievement(
        id="first_evolution_blocked",
        title="Pare! Nao Agora!",
        description="Interrompa a evolucao de um Pokemon pela primeira vez",
        rarity=AchievementRarity.COMMON,
        rewards={"gold": 100, "xp": 50}
    ),
    "evolution_blocked_10": Achievement(
        id="evolution_blocked_10",
        title="O Dominador",
        description="Interrompa a evolucao de Pokemon 10 vezes",
        rarity=AchievementRarity.UNCOMMON,
        rewards={"gold": 1200, "xp": 600}
    ),

    # ===== CONQUISTAS DE CURA DE STATUS =====
    # Poison
    "first_antidote": Achievement(
        id="first_antidote",
        title="Antidoto Eficaz",
        description="Cure veneno com Antidoto pela primeira vez",
        rarity=AchievementRarity.COMMON,
        rewards={"gold": 100, "xp": 50}
    ),
    "antidote_100": Achievement(
        id="antidote_100",
        title="Mestre Antiveneno",
        description="Cure veneno com Antidoto 100 vezes",
        rarity=AchievementRarity.EPIC,
        rewards={"gold": 1500, "xp": 750}
    ),

    # Sleep
    "first_awake": Achievement(
        id="first_awake",
        title="Despertador",
        description="Acorde um Pokemon com Awake pela primeira vez",
        rarity=AchievementRarity.COMMON,
        rewards={"gold": 100, "xp": 50}
    ),
    "awake_100": Achievement(
        id="awake_100",
        title="Mestre dos Sonhos",
        description="Acorde Pokemon com Awake 100 vezes",
        rarity=AchievementRarity.EPIC,
        rewards={"gold": 1500, "xp": 750}
    ),

    # Paralysis
    "first_paralyze_heal": Achievement(
        id="first_paralyze_heal",
        title="Paralisia Curada!",
        description="Cure paralisia pela primeira vez",
        rarity=AchievementRarity.COMMON,
        rewards={"gold": 100, "xp": 50}
    ),
    "paralyze_heal_100": Achievement(
        id="paralyze_heal_100",
        title="Mestre da Mobilidade",
        description="Cure paralisia 100 vezes",
        rarity=AchievementRarity.EPIC,
        rewards={"gold": 5000, "xp": 7500}
    ),

    # Revive
    "first_revive": Achievement(
        id="first_revive",
        title="Renascer",
        description="Reviva um Pokemon pela primeira vez",
        rarity=AchievementRarity.COMMON,
        rewards={"gold": 200, "xp": 200}
    ),
    "revive_25": Achievement(
        id="revive_25",
        title="Mestre da Ressurreicao",
        description="Reviva Pokemon 25 vezes",
        rarity=AchievementRarity.RARE,
        rewards={"gold": 2000, "xp": 1000}
    ),

    # ===== CONQUISTAS DE ENSINO DE MOVES =====
    "first_move_taught": Achievement(
        id="first_move_taught",
        title="Primeira Licao",
        description="Ensine um movimento a um Pokemon pela primeira vez",
        rarity=AchievementRarity.COMMON,
        rewards={"gold": 100, "xp": 50}
    ),
    "move_taught_10": Achievement(
        id="move_taught_10",
        title="Mestre Professor",
        description="Ensine 10 movimentos a Pokemon",
        rarity=AchievementRarity.UNCOMMON,
        rewards={"gold": 600, "xp": 350}
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