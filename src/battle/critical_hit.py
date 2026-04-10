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
        self._crit_stage_modifiers: Dict[int, int] = {}  # pokemon_id -> extra_stages

    @classmethod
    def get_critical_stage(cls, move_name: str = None, attacker=None) -> int:
        """
        Retorna o estágio de crítico base do movimento + modificadores do atacante
        0 = normal, 1 = high crit rate
        """
        base_stage = 0

        if move_name:
            move_key = move_name.lower().replace(" ", "-")
            if move_key in cls.HIGH_CRIT_MOVES:
                base_stage = 1

        # Adiciona modificadores do atacante (Focus Energy, etc)
        if attacker and hasattr(attacker, 'effect_manager') and attacker.effect_manager:
            # Verifica se tem modificador de crítico ativo
            pokemon_id = id(attacker)
            if pokemon_id in cls._crit_stage_modifiers:
                base_stage += cls._crit_stage_modifiers[pokemon_id]

        # Limita a +4 (50% de chance)
        return min(4, base_stage)

    @classmethod
    def calculate_critical_chance(cls, attacker, move_name: str = None) -> float:
        """
        Calcula a chance real de acerto crítico
        """
        # Estágio base do movimento + modificadores
        total_stage = cls.get_critical_stage(move_name, attacker)

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

    @classmethod
    def add_crit_stage_modifier(cls, pokemon, stages: int, duration: float = None):
        """
        Adiciona um modificador de estágio de crítico (Focus Energy)

        Args:
            pokemon: Pokémon que recebe o modificador
            stages: Quantidade de estágios a adicionar (+2 para Focus Energy)
            duration: Duração em segundos (None = permanente até o fim da batalha)
        """
        pokemon_id = id(pokemon)

        # Verifica se já tem Focus Energy ativo
        if pokemon_id in cls._crit_stage_modifiers and stages > 0:
            print(f"[CRIT] {pokemon.name} já está com Focus Energy ativo!")
            return False

        # Armazena o modificador
        cls._crit_stage_modifiers[pokemon_id] = min(4, cls._crit_stage_modifiers.get(pokemon_id, 0) + stages)

        # Se tiver duração, agenda remoção
        if duration:
            # TODO: Implementar sistema de remoção por tempo
            pass

        print(f"[CRIT] {pokemon.name} agora tem +{cls._crit_stage_modifiers[pokemon_id]} estágio(s) de crítico!")
        return True

    @classmethod
    def remove_crit_stage_modifier(cls, pokemon):
        """Remove o modificador de estágio de crítico (quando o Pokémon sai de campo)"""
        pokemon_id = id(pokemon)
        if pokemon_id in cls._crit_stage_modifiers:
            del cls._crit_stage_modifiers[pokemon_id]
            print(f"[CRIT] Modificador de crítico removido de {pokemon.name}")

    @classmethod
    def clear_all_modifiers(cls):
        """Limpa todos os modificadores (usado quando a batalha termina)"""
        cls._crit_stage_modifiers.clear()