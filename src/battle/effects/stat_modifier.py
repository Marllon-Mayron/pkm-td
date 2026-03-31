# src/battle/effects/stat_modifier.py
from enum import Enum
from typing import Dict, Optional


class StatType(Enum):
    """Tipos de stats que podem ser modificados"""
    ATTACK = "attack"
    DEFENSE = "defense"
    SP_ATTACK = "sp_attack"
    SP_DEFENSE = "sp_defense"
    SPEED = "speed"
    ACCURACY = "accuracy"
    EVASION = "evasion"


class StatStage:
    """Gerencia estágios de modificação de stats (Pokémon style: -6 a +6)"""

    # Multiplicadores para cada estágio (baseado nos jogos Pokémon)
    STAGE_MULTIPLIERS = {
        -6: 2 / 8,  # 0.25
        -5: 2 / 7,  # ~0.2857
        -4: 2 / 6,  # 0.3333
        -3: 2 / 5,  # 0.4
        -2: 2 / 4,  # 0.5
        -1: 2 / 3,  # 0.6667
        0: 1.0,
        1: 3 / 2,  # 1.5
        2: 4 / 2,  # 2.0
        3: 5 / 2,  # 2.5
        4: 6 / 2,  # 3.0
        5: 7 / 2,  # 3.5
        6: 8 / 2  # 4.0
    }

    # ORDEM DE EXIBIÇÃO (prioridade visual)
    STAT_DISPLAY_ORDER = [
        "Atk",
        "Def",
        "SpAtk",
        "SpDef",
        "Spd",
        "Prec",
        "Evas"
    ]

    # Nomes dos stats em português (VERSÃO CURTA para UI)
    STAT_NAMES_SHORT = {
        StatType.ATTACK: "Atk",
        StatType.DEFENSE: "Def",
        StatType.SP_ATTACK: "SpAtk",
        StatType.SP_DEFENSE: "SpDef",
        StatType.SPEED: "Spd",
        StatType.ACCURACY: "Prec",
        StatType.EVASION: "Evas"
    }

    # Nomes completos (para logs)
    STAT_NAMES_FULL = {
        StatType.ATTACK: "Ataque",
        StatType.DEFENSE: "Defesa",
        StatType.SP_ATTACK: "Ataque Especial",
        StatType.SP_DEFENSE: "Defesa Especial",
        StatType.SPEED: "Velocidade",
        StatType.ACCURACY: "Precisão",
        StatType.EVASION: "Evasão"
    }

    def __init__(self):
        self.stages: Dict[StatType, int] = {
            stat_type: 0 for stat_type in StatType
        }

    def modify(self, stat_type: StatType, stages: int):
        """Modifica um stat em x estágios"""
        old_stage = self.stages[stat_type]
        new_stage = old_stage + stages
        self.stages[stat_type] = max(-6, min(6, new_stage))
        return self.stages[stat_type]

    def get_multiplier(self, stat_type: StatType) -> float:
        """Retorna o multiplicador para um stat"""
        stage = self.stages[stat_type]
        return self.STAGE_MULTIPLIERS[stage]

    def get_stage(self, stat_type: StatType) -> int:
        """Retorna o estágio atual"""
        return self.stages[stat_type]

    def reset(self):
        """Reseta todos os estágios"""
        for stat_type in StatType:
            self.stages[stat_type] = 0

    def get_all_active_modifiers(self) -> Dict[str, int]:
        """Retorna todos os modificadores ativos com nomes curtos, ordenados"""
        result = {}
        for stat_type, stage in self.stages.items():
            if stage != 0:
                result[self.STAT_NAMES_SHORT[stat_type]] = stage
        return result

    def get_ordered_modifiers(self) -> list:
        """Retorna lista ordenada de modificadores (nome, estágio)"""
        modifiers = self.get_all_active_modifiers()
        ordered = []

        # Primeiro adiciona na ordem definida
        for stat_name in self.STAT_DISPLAY_ORDER:
            if stat_name in modifiers:
                ordered.append((stat_name, modifiers[stat_name]))

        # Depois adiciona os que não estão na ordem (fallback)
        for stat_name, stage in modifiers.items():
            if stat_name not in self.STAT_DISPLAY_ORDER:
                ordered.append((stat_name, stage))

        return ordered


class StatModifier:
    """Modificador temporário de stats (para efeitos com duração limitada)"""

    def __init__(self, stat_type: StatType, stages: int, duration: float = None):
        """
        Args:
            stat_type: Stat a ser modificado
            stages: Quantidade de estágios (-6 a +6)
            duration: Duração em SEGUNDOS (None = permanente)
        """
        self.stat_type = stat_type
        self.stages = stages
        self.duration = duration
        self.time_left = duration if duration is not None else None
        self.is_permanent = duration is None

    def update(self, dt: float) -> bool:
        """
        Atualiza o modificador, retorna False se acabou
        dt: tempo decorrido desde o último update (em segundos)
        """
        # Modificadores permanentes nunca expiram
        if self.is_permanent:
            return True

        if self.time_left is not None:
            self.time_left -= dt
            return self.time_left > 0

        return True