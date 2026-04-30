# src/battle/damage_calculator.py
"""
Calculadora de dano baseada nos jogos Pokémon originais
"""
from typing import Dict
import random

from src.battle.effects.specific.weather.weather_state import WeatherType
from src.battle.effects import StatusType
from src.battle.effects.critical_hit import CriticalHitSystem


class DamageCalculator:
    """Calcula dano com base em tipos, stats e moves"""

    # Tabela de eficácia de tipos COMPLETA (Gen 1-6)
    # Formato: (move_type, defender_type) -> multiplier
    TYPE_CHART = {
        # NORMAL
        ("normal", "rock"): 0.5,
        ("normal", "ghost"): 0,
        ("normal", "steel"): 0.5,

        # FIRE
        ("fire", "fire"): 0.5,
        ("fire", "water"): 0.5,
        ("fire", "grass"): 2.0,
        ("fire", "ice"): 2.0,
        ("fire", "bug"): 2.0,
        ("fire", "rock"): 0.5,
        ("fire", "dragon"): 0.5,
        ("fire", "steel"): 2.0,
        ("fire", "fairy"): 0.5,

        # WATER
        ("water", "fire"): 2.0,
        ("water", "water"): 0.5,
        ("water", "grass"): 0.5,
        ("water", "ground"): 2.0,
        ("water", "rock"): 2.0,
        ("water", "dragon"): 0.5,

        # ELECTRIC
        ("electric", "water"): 2.0,
        ("electric", "electric"): 0.5,
        ("electric", "grass"): 0.5,
        ("electric", "ground"): 0,
        ("electric", "flying"): 2.0,
        ("electric", "dragon"): 0.5,
        ("electric", "rock"): 0.5,

        # GRASS
        ("grass", "fire"): 0.5,
        ("grass", "water"): 2.0,
        ("grass", "grass"): 0.5,
        ("grass", "poison"): 0.5,
        ("grass", "ground"): 2.0,
        ("grass", "flying"): 0.5,
        ("grass", "bug"): 0.5,
        ("grass", "rock"): 2.0,
        ("grass", "dragon"): 0.5,
        ("grass", "steel"): 0.5,

        # ICE
        ("ice", "fire"): 0.5,
        ("ice", "water"): 0.5,
        ("ice", "grass"): 2.0,
        ("ice", "ice"): 0.5,
        ("ice", "ground"): 2.0,
        ("ice", "flying"): 2.0,
        ("ice", "dragon"): 2.0,
        ("ice", "steel"): 0.5,

        # FIGHTING
        ("fighting", "normal"): 2.0,
        ("fighting", "ice"): 2.0,
        ("fighting", "poison"): 0.5,
        ("fighting", "flying"): 0.5,
        ("fighting", "psychic"): 0.5,
        ("fighting", "bug"): 0.5,
        ("fighting", "rock"): 2.0,
        ("fighting", "ghost"): 0,
        ("fighting", "dark"): 2.0,
        ("fighting", "steel"): 2.0,

        # POISON
        ("poison", "grass"): 2.0,
        ("poison", "poison"): 0.5,
        ("poison", "ground"): 0.5,
        ("poison", "rock"): 0.5,
        ("poison", "ghost"): 0.5,
        ("poison", "steel"): 0,
        ("poison", "fairy"): 2.0,

        # GROUND
        ("ground", "fire"): 2.0,
        ("ground", "electric"): 2.0,
        ("ground", "grass"): 0.5,
        ("ground", "poison"): 2.0,
        ("ground", "flying"): 0,
        ("ground", "bug"): 0.5,
        ("ground", "rock"): 2.0,
        ("ground", "steel"): 2.0,

        # FLYING
        ("flying", "grass"): 2.0,
        ("flying", "fighting"): 2.0,
        ("flying", "bug"): 2.0,
        ("flying", "rock"): 0.5,
        ("flying", "steel"): 0.5,
        ("flying", "electric"): 0.5,

        # PSYCHIC
        ("psychic", "fighting"): 2.0,
        ("psychic", "poison"): 2.0,
        ("psychic", "psychic"): 0.5,
        ("psychic", "dark"): 0,
        ("psychic", "steel"): 0.5,

        # BUG
        ("bug", "grass"): 2.0,
        ("bug", "fighting"): 0.5,
        ("bug", "poison"): 0.5,
        ("bug", "flying"): 0.5,
        ("bug", "psychic"): 2.0,
        ("bug", "ghost"): 0.5,
        ("bug", "dark"): 2.0,
        ("bug", "steel"): 0.5,

        # ROCK
        ("rock", "fire"): 2.0,
        ("rock", "ice"): 2.0,
        ("rock", "fighting"): 0.5,
        ("rock", "ground"): 0.5,
        ("rock", "flying"): 2.0,
        ("rock", "bug"): 2.0,
        ("rock", "steel"): 0.5,

        # GHOST
        ("ghost", "normal"): 0,
        ("ghost", "psychic"): 2.0,
        ("ghost", "ghost"): 2.0,
        ("ghost", "dark"): 0.5,

        # DRAGON
        ("dragon", "dragon"): 2.0,
        ("dragon", "steel"): 0.5,

        # DARK
        ("dark", "psychic"): 2.0,
        ("dark", "dark"): 0.5,
        ("dark", "fighting"): 0.5,

        # STEEL
        ("steel", "ice"): 2.0,
        ("steel", "rock"): 2.0,
        ("steel", "steel"): 0.5,
        ("steel", "fire"): 0.5,
        ("steel", "water"): 0.5,
        ("steel", "electric"): 0.5,
        ("steel", "fairy"): 2.0,

        # FAIRY
        ("fairy", "fighting"): 2.0,
        ("fairy", "dragon"): 2.0,
        ("fairy", "dark"): 2.0,
        ("fairy", "fire"): 0.5,
        ("fairy", "poison"): 0.5,
        ("fairy", "steel"): 0.5,
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
        - stab: True se teve STAB
        - critical: True se foi acerto crítico
        """
        # 1. Verificar acerto (accuracy)
        hit_chance = move.accuracy / 100
        if random.random() > hit_chance:
            return {
                "damage": 0,
                "effectiveness": 1.0,
                "hit": False,
                "message": f"O ataque errou!",
                "stab": False,
                "critical": False
            }

        # 2. Moves de status não causam dano
        if move.category == "status":
            return {
                "damage": 0,
                "effectiveness": 1.0,
                "hit": True,
                "message": f"Usou {move.name}! (Efeito de status)",
                "stab": False,
                "critical": False
            }

        # 3. Power 0 = não causa dano
        if move.power == 0:
            return {
                "damage": 0,
                "effectiveness": 1.0,
                "hit": True,
                "message": f"Usou {move.name}!",
                "stab": False,
                "critical": False
            }

        # 4. Calcular multiplicador de tipo (inclui 4x e 0.25x)
        effectiveness = cls._get_type_effectiveness(move.type, defender.types)

        # Se for imune (effectiveness = 0), retorna sem dano
        if effectiveness == 0:
            return {
                "damage": 0,
                "effectiveness": 0,
                "hit": True,
                "message": f"Não afeta {defender.name}!",
                "stab": False,
                "critical": False
            }

        # 5. STAB (Same Type Attack Bonus)
        stab = 1.5 if move.type in attacker.types else 1.0

        # ===== NOVO: MODIFICADORES DE CLIMA =====
        weather_multiplier = 1.0
        weather = None

        # Verifica se o atacante tem battle_system com clima
        if hasattr(attacker, 'battle_system') and attacker.battle_system:
            weather = attacker.battle_system.get_weather_type()

            if weather == WeatherType.SUNNY:
                if move.type.lower() == "fire":
                    weather_multiplier = 1.5  # +50% para Fire
                    print(f"[WEATHER] Sol forte: {move.name} +50% de dano!")
                elif move.type.lower() == "water":
                    weather_multiplier = 0.5  # -50% para Water
                    print(f"[WEATHER] Sol forte: {move.name} -50% de dano!")

            elif weather == WeatherType.RAIN:
                if move.type.lower() == "water":
                    weather_multiplier = 1.5  # +50% para Water
                    print(f"[WEATHER] Chuva: {move.name} +50% de dano!")
                elif move.type.lower() == "fire":
                    weather_multiplier = 0.5  # -50% para Fire
                    print(f"[WEATHER] Chuva: {move.name} -50% de dano!")

        # 6. Calcular stats de ataque/defesa
        if move.category == "physical":
            attack_stat = attacker.attack
            defense_stat = defender.defense

            # ===== APLICA EFEITO DA QUEIMADURA NO ATACANTE =====
            # Se o atacante está queimado, reduz o dano físico pela metade
            if hasattr(attacker, 'effect_manager') and attacker.effect_manager:
                status = attacker.effect_manager.get_status(attacker)
                if status and status.type == StatusType.BURN:
                    attack_stat = attack_stat * 0.5
                    print(f"[BURN] Ataque de {attacker.name} reduzido pela metade devido à queimadura!")
        else:  # special
            attack_stat = attacker.sp_attack
            defense_stat = defender.sp_defense

        # ===== VERIFICA MINIMIZE PARA STOMP =====
        if move.name.lower() == "stomp":
            if hasattr(defender, '_minimize_active') and defender._minimize_active:
                power = move.power * 2  # Dobra o poder
                print(f"[STOMP] Dano dobrado contra {defender.name} (Minimize)!")
            else:
                power = move.power
        else:
            power = move.power

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
        damage = damage * stab * effectiveness * weather_multiplier

        # ===== VERIFICAÇÃO DE CRÍTICO =====
        is_critical = False
        if move.category != "status" and move.power > 0:
            is_critical = CriticalHitSystem.is_critical(attacker, move.name)
            if is_critical:
                old_damage = damage
                damage = CriticalHitSystem.calculate_critical_damage(damage, move.category)
                print(f"[CRITICAL] {move.name} causou um acerto crítico! {old_damage:.0f} -> {damage:.0f} de dano!")

        # Random entre 0.85 e 1.0
        damage = damage * random.uniform(0.85, 1.0)

        # Dano mínimo de 1
        damage = max(1, int(damage))

        # Mensagem baseada na eficácia
        message = cls._get_effectiveness_message(effectiveness)

        # Adiciona mensagem de crítico se aplicável
        if is_critical:
            if message:
                message = f"Acerto crítico! {message}"
            else:
                message = "Acerto crítico!"

        return {
            "damage": damage,
            "effectiveness": effectiveness,
            "hit": True,
            "message": message,
            "stab": stab > 1.0,
            "critical": is_critical
        }

    @classmethod
    def _get_type_effectiveness(cls, move_type: str, defender_types: list) -> float:
        """
        Calcula multiplicador de eficácia baseado nos tipos
        Suporta multiplicadores combinados (ex: 2x * 2x = 4x)
        """
        multiplier = 1.0
        move_type_lower = move_type.lower()

        for def_type in defender_types:
            def_type_lower = def_type.lower()
            key = (move_type_lower, def_type_lower)

            # Verifica na tabela
            if key in cls.TYPE_CHART:
                mult = cls.TYPE_CHART[key]
                multiplier *= mult
            # Se não tem entrada, é neutro (1.0)
            # else: multiplier *= 1.0

        return multiplier

    @classmethod
    def _get_effectiveness_message(cls, effectiveness: float) -> str:
        """Retorna mensagem baseada na eficácia"""
        if effectiveness == 0:
            return "Não afeta..."
        elif effectiveness >= 4.0:
            return "É super efetivo! (4x)"
        elif effectiveness > 1.0:
            if effectiveness >= 2.0:
                return "É super efetivo!"
            return "É um pouco efetivo..."
        elif effectiveness < 1.0:
            if effectiveness <= 0.25:
                return "Não é muito efetivo... (1/4x)"
            return "Não é muito efetivo..."
        return ""

    @classmethod
    def get_type_interaction(cls, move_type: str, defender_type: str) -> float:
        """
        Método auxiliar para debug - retorna o multiplicador entre um tipo de ataque e um tipo de defesa
        """
        key = (move_type.lower(), defender_type.lower())
        return cls.TYPE_CHART.get(key, 1.0)