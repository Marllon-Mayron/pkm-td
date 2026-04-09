# src/battle/attack_pattern.py
from enum import Enum
from typing import List, Optional
import random


class AttackPattern(Enum):
    """Padrões de ataque para inimigos"""
    AGGRESSIVE = "aggressive"  # Pode atacar (30% dos inimigos comuns)
    VICIOUS = "vicious"  # Só ataca com um golpe específico até acabar PP
    RANDOM = "random"  # Ataca com todos os ataques disponíveis aleatoriamente
    VICIOUS_SELECTIVE = "vicious_selective"  # Só usa golpes do mesmo tipo (status, físico ou especial)
    PASSIVE = "passive"  # Não ataca (70% dos inimigos comuns)


class AttackTypeCategory(Enum):
    """Categorias de ataques para o padrão VICIOUS_SELECTIVE"""
    PHYSICAL = "physical"
    SPECIAL = "special"
    STATUS = "status"


class AttackPatternManager:
    """Gerencia os padrões de ataque dos inimigos"""

    AGGRESSIVE_CHANCE = 0.20
    BOSS_ALWAYS_AGGRESSIVE = True

    @classmethod
    def get_pattern_for_enemy(cls, is_boss: bool = False, is_shiny: bool = False) -> AttackPattern:
        """Determina o padrão de ataque para um inimigo"""
        if is_boss:
            # Boss sempre agressivo, mas pode ter padrões especiais
            return cls._get_boss_pattern()

        # Para inimigos comuns
        if random.random() < cls.AGGRESSIVE_CHANCE:
            return cls._get_aggressive_pattern()
        else:
            return AttackPattern.PASSIVE

    @classmethod
    def _get_aggressive_pattern(cls) -> AttackPattern:
        """Define padrão para inimigos agressivos"""
        patterns = [
            AttackPattern.VICIOUS,
            AttackPattern.RANDOM,
            AttackPattern.VICIOUS_SELECTIVE
        ]
        return random.choice(patterns)

    @classmethod
    def _get_boss_pattern(cls) -> AttackPattern:
        """Define padrão para bosses (mais desafiadores)"""
        # Boss pode ter padrões mais complexos
        patterns = [
            #AttackPattern.VICIOUS,
            AttackPattern.RANDOM,
            #AttackPattern.VICIOUS_SELECTIVE
        ]
        # Boss tem chance maior de ser VICIOUS_SELECTIVE
        return AttackPattern.RANDOM

    @classmethod
    def get_attack_category_for_vicious_selective(cls, pokemon) -> AttackTypeCategory:
        """Determina qual categoria de ataque o Pokémon VICIOUS_SELECTIVE vai usar"""
        if not pokemon.moves:
            return AttackTypeCategory.PHYSICAL

        # Conta quantos moves de cada categoria
        categories = {AttackTypeCategory.PHYSICAL: 0,
                      AttackTypeCategory.SPECIAL: 0,
                      AttackTypeCategory.STATUS: 0}

        for move in pokemon.moves:
            if move.category == "physical":
                categories[AttackTypeCategory.PHYSICAL] += 1
            elif move.category == "special":
                categories[AttackTypeCategory.SPECIAL] += 1
            elif move.category == "status":
                categories[AttackTypeCategory.STATUS] += 1

        # Escolhe a categoria com mais moves (se houver empate, escolhe aleatório)
        max_count = max(categories.values())
        if max_count == 0:
            return AttackTypeCategory.PHYSICAL

        available = [cat for cat, count in categories.items() if count == max_count]
        return random.choice(available)