# src/battle/critical_hit.py
"""
Sistema de acertos críticos para batalhas Pokémon
Baseado nas mecânicas originais (Gen 1-6)
"""

import random
from typing import Optional, Dict


class CriticalHitSystem:
    """
    Gerencia acertos críticos com suporte a:
    - Taxa base de crítico (6.25% = 1/16)
    - Modificadores de estágio (ex: Karate Chop, Slash)
    - Itens que aumentam crítico (Scope Lens, etc)
    - Habilidades (Super Luck, etc)
    """

    # Taxa base de crítico (1/16 = 6.25%)
    BASE_CRIT_RATE = 1 / 16

    # Multiplicadores por estágio (Gen 6+)
    # Estágio 0: 1/16 (6.25%)
    # Estágio 1: 1/8 (12.5%)
    # Estágio 2: 1/4 (25%)
    # Estágio 3: 1/3 (33.3%)
    # Estágio 4: 1/2 (50%)
    STAGE_MULTIPLIERS = {
        0: 1.0,  # 1/16
        1: 2.0,  # 1/8
        2: 4.0,  # 1/4
        3: 5.33,  # ~1/3
        4: 8.0,  # 1/2
    }

    # Movimentos que aumentam estágio de crítico
    HIGH_CRIT_MOVES = {
        "karate-chop", "slash", "razor-leaf", "crabhammer",
        "air-cutter", "night-slash", "cross-poison",
        "shadow-claw", "stone-edge", "leaf-blade"
    }

    def __init__(self):
        # Modificadores temporários para ataques específicos
        self._temp_stage_modifiers: Dict[int, int] = {}  # pokemon_id -> stage_bonus

    @classmethod
    def get_critical_stage(cls, move_name: str = None) -> int:
        """
        Retorna o estágio de crítico base do movimento
        0 = normal, 1 = high crit rate
        """
        if move_name:
            move_key = move_name.lower().replace(" ", "-")
            if move_key in cls.HIGH_CRIT_MOVES:
                return 1  # Estágio +1
        return 0

    @classmethod
    def calculate_critical_chance(cls, attacker, move_name: str = None) -> float:
        """
        Calcula a chance real de acerto crítico

        Args:
            attacker: Pokémon atacante
            move_name: Nome do movimento (para high-crit moves)

        Returns:
            Chance de crítico (0.0 a 1.0)
        """
        # Estágio base do movimento
        base_stage = cls.get_critical_stage(move_name)

        # TODO: Adicionar efeitos de habilidades (Super Luck)
        # TODO: Adicionar efeitos de itens (Scope Lens, Razor Claw)
        # TODO: Adicionar efeitos de movimentos (Focus Energy)

        # Stage total
        total_stage = base_stage

        # Calcula taxa baseada no estágio (Gen 6+ formula)
        if total_stage >= 4:
            return 0.50  # 50%
        elif total_stage >= 3:
            return 1 / 3  # ~33.3%
        elif total_stage >= 2:
            return 0.25  # 25%
        elif total_stage >= 1:
            return 1 / 8  # 12.5%
        else:
            return cls.BASE_CRIT_RATE  # 6.25%

    @classmethod
    def is_critical(cls, attacker, move_name: str = None) -> bool:
        """
        Verifica se um ataque será crítico

        Returns:
            True se for crítico, False caso contrário
        """
        chance = cls.calculate_critical_chance(attacker, move_name)
        return random.random() < chance

    @classmethod
    def calculate_critical_damage(cls, damage: int, move_category: str = "physical") -> int:
        """
        Calcula o dano com modificador de crítico

        Nos jogos Pokémon:
        - Crítico ignora modificadores negativos do atacante
        - Crítico ignora modificadores positivos do defensor
        - Dano base é multiplicado por 1.5 (Gen 6+)

        Args:
            damage: Dano base calculado
            move_category: Categoria do movimento (physical/special)

        Returns:
            Dano com crítico aplicado
        """
        # Multiplicador base de crítico (1.5x em Gen 6+)
        CRIT_MULTIPLIER = 1.5

        # Crítico ignora:
        # - Reduções de ataque do atacante (como queimadura)
        # - Aumentos de defesa do defensor

        return int(damage * CRIT_MULTIPLIER)