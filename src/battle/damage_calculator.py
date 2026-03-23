# src/battle/damage_calculator.py
"""
Calculadora de dano baseada nos jogos Pokémon originais
"""
from typing import Dict, Tuple, Optional
import random


class DamageCalculator:
    """Calcula dano com base em tipos, stats e moves"""

    # Tabela de eficácia de tipos (Gen 1)
    TYPE_CHART = {
        ("normal", "rock"): 0.5, ("normal", "ghost"): 0, ("normal", "steel"): 0.5,
        ("fire", "fire"): 0.5, ("fire", "water"): 0.5, ("fire", "grass"): 2.0,
        ("fire", "ice"): 2.0, ("fire", "bug"): 2.0, ("fire", "rock"): 0.5,
        ("fire", "dragon"): 0.5, ("fire", "steel"): 2.0,
        ("water", "fire"): 2.0, ("water", "water"): 0.5, ("water", "grass"): 0.5,
        ("water", "ground"): 2.0, ("water", "rock"): 2.0, ("water", "dragon"): 0.5,
        ("electric", "water"): 2.0, ("electric", "electric"): 0.5, ("electric", "grass"): 0.5,
        ("electric", "ground"): 0, ("electric", "flying"): 2.0, ("electric", "dragon"): 0.5,
        ("grass", "fire"): 0.5, ("grass", "water"): 2.0, ("grass", "grass"): 0.5,
        ("grass", "poison"): 0.5, ("grass", "ground"): 2.0, ("grass", "flying"): 0.5,
        ("grass", "bug"): 0.5, ("grass", "rock"): 2.0, ("grass", "dragon"): 0.5,
        ("grass", "steel"): 0.5,
        ("ice", "fire"): 0.5, ("ice", "water"): 0.5, ("ice", "grass"): 2.0,
        ("ice", "ice"): 0.5, ("ice", "ground"): 2.0, ("ice", "flying"): 2.0,
        ("ice", "dragon"): 2.0, ("ice", "steel"): 0.5,
        ("fighting", "normal"): 2.0, ("fighting", "ice"): 2.0, ("fighting", "poison"): 0.5,
        ("fighting", "flying"): 0.5, ("fighting", "psychic"): 0.5, ("fighting", "bug"): 0.5,
        ("fighting", "rock"): 2.0, ("fighting", "ghost"): 0, ("fighting", "dark"): 2.0,
        ("fighting", "steel"): 2.0,
        ("poison", "grass"): 2.0, ("poison", "poison"): 0.5, ("poison", "ground"): 0.5,
        ("poison", "rock"): 0.5, ("poison", "ghost"): 0.5, ("poison", "steel"): 0,
        ("ground", "fire"): 2.0, ("ground", "electric"): 2.0, ("ground", "grass"): 0.5,
        ("ground", "poison"): 2.0, ("ground", "flying"): 0, ("ground", "bug"): 0.5,
        ("ground", "rock"): 2.0, ("ground", "steel"): 2.0,
        ("flying", "grass"): 2.0, ("flying", "fighting"): 2.0, ("flying", "bug"): 2.0,
        ("flying", "rock"): 0.5, ("flying", "steel"): 0.5, ("flying", "electric"): 0.5,
        ("psychic", "fighting"): 2.0, ("psychic", "poison"): 2.0, ("psychic", "psychic"): 0.5,
        ("psychic", "dark"): 0, ("psychic", "steel"): 0.5,
        ("bug", "grass"): 2.0, ("bug", "fighting"): 0.5, ("bug", "poison"): 0.5,
        ("bug", "flying"): 0.5, ("bug", "psychic"): 2.0, ("bug", "ghost"): 0.5,
        ("bug", "dark"): 2.0, ("bug", "steel"): 0.5,
        ("rock", "fire"): 2.0, ("rock", "ice"): 2.0, ("rock", "fighting"): 0.5,
        ("rock", "ground"): 0.5, ("rock", "flying"): 2.0, ("rock", "bug"): 2.0,
        ("rock", "steel"): 0.5,
        ("ghost", "normal"): 0, ("ghost", "psychic"): 2.0, ("ghost", "ghost"): 2.0,
        ("ghost", "dark"): 0.5,
        ("dragon", "dragon"): 2.0, ("dragon", "steel"): 0.5,
        ("dark", "psychic"): 2.0, ("dark", "dark"): 0.5, ("dark", "fighting"): 0.5,
        ("steel", "ice"): 2.0, ("steel", "rock"): 2.0, ("steel", "steel"): 0.5,
    }

    @classmethod
    def calculate_damage(cls, attacker, defender, move) -> Dict:
        """
        Calcula o dano de um move

        Retorna dicionário com:
        - damage: dano calculado
        - effectiveness: multiplicador de tipo (0, 0.25, 0.5, 1, 2, 4)
        - hit: True se acertou, False se errou
        - message: mensagem para exibir
        """
        # 1. Verificar acerto (accuracy)
        hit_chance = move.accuracy / 100
        if random.random() > hit_chance:
            return {
                "damage": 0,
                "effectiveness": 1.0,
                "hit": False,
                "message": f"O ataque errou!"
            }

        # 2. Moves de status não causam dano
        if move.category == "status":
            return {
                "damage": 0,
                "effectiveness": 1.0,
                "hit": True,
                "message": f"Usou {move.name}! (Efeito de status)"
            }

        # 3. Power 0 = não causa dano
        if move.power == 0:
            return {
                "damage": 0,
                "effectiveness": 1.0,
                "hit": True,
                "message": f"Usou {move.name}!"
            }

        # 4. Calcular multiplicador de tipo
        effectiveness = cls._get_type_effectiveness(move.type, defender.types)

        # 5. STAB (Same Type Attack Bonus)
        stab = 1.5 if move.type in attacker.types else 1.0

        # 6. Calcular stats de ataque/defesa
        if move.category == "physical":
            attack_stat = attacker.attack
            defense_stat = defender.defense
        else:  # special
            attack_stat = attacker.sp_attack
            defense_stat = defender.sp_defense

        # 7. Fórmula de dano (adaptada dos jogos Pokémon)
        # Dano = ((((2 * Level / 5 + 2) * Power * Attack/Defense) / 50) + 2) * STAB * Eficácia * Random
        level = attacker.level
        power = move.power

        # Evitar divisão por zero
        if defense_stat <= 0:
            defense_stat = 1

        # Cálculo base
        damage = ((2 * level / 5 + 2) * power * attack_stat / defense_stat) / 50 + 2

        # Aplicar STAB e eficácia
        damage = damage * stab * effectiveness

        # Random entre 0.85 e 1.0
        damage = damage * random.uniform(0.85, 1.0)

        # Dano mínimo de 1
        damage = max(1, int(damage))

        # Mensagem baseada na eficácia
        message = cls._get_effectiveness_message(effectiveness)

        return {
            "damage": damage,
            "effectiveness": effectiveness,
            "hit": True,
            "message": message,
            "stab": stab > 1.0
        }

    @classmethod
    def _get_type_effectiveness(cls, move_type: str, defender_types: list) -> float:
        """Calcula multiplicador de eficácia baseado nos tipos"""
        multiplier = 1.0

        for def_type in defender_types:
            # Verifica super efetivo
            key = (move_type.lower(), def_type.lower())
            if key in cls.TYPE_CHART:
                multiplier *= cls.TYPE_CHART[key]

            # Verifica imune (0x)
            if cls.TYPE_CHART.get(key) == 0:
                return 0.0

        return multiplier

    @classmethod
    def _get_effectiveness_message(cls, effectiveness: float) -> str:
        """Retorna mensagem baseada na eficácia"""
        if effectiveness == 0:
            return "Não afeta..."
        elif effectiveness > 1.0:
            if effectiveness >= 4.0:
                return "É super efetivo! (4x)"
            return "É super efetivo!"
        elif effectiveness < 1.0:
            if effectiveness <= 0.25:
                return "Não é muito efetivo... (1/4x)"
            return "Não é muito efetivo..."
        return ""