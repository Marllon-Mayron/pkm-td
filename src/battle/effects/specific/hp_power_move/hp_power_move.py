# src/battle/effects/specific/hp_power_move.py
"""
Classe base para movimentos que aumentam poder com base no HP restante.
Ex: Flail, Reversal, Trump Card, Wring Out, Crush Grip, etc.
"""
from typing import Dict, List, Tuple, Optional
import random

from src.battle.damage_calculator import DamageCalculator
from src.managers.sounds.move_sound_manager import move_sound_manager
from src.battle.effects.stat_modifier import StatType


class HPPowerMove:
    """
    Gerencia movimentos cujo poder depende do HP restante do usuário.

    Tabelas de poder predefinidas:
    - STANDARD: Usada por Flail e Reversal (Gen 2-6)
    - TRUMP_CARD: Poder aumenta com PP restante (Gen 4)
    - WRING_OUT: Poder = 120 * (HP% atual do alvo)
    """

    # Tabela padrão (Flail/Reversal)
    STANDARD_TABLE = [
        (1, 200),  # 0-1% HP
        (5, 150),  # 2-5% HP
        (12, 100),  # 6-12% HP
        (21, 80),  # 13-21% HP
        (42, 40),  # 22-42% HP
        (100, 20)  # 43-100% HP
    ]

    # Tabela mais agressiva (alguns jogos fan-made)
    AGGRESSIVE_TABLE = [
        (1, 250),
        (5, 200),
        (12, 150),
        (21, 100),
        (42, 60),
        (100, 30)
    ]

    # Mensagens de feedback por nível de poder
    POWER_MESSAGES = {
        200: "{pokemon} usou todo seu desespero! Poder {power}!",
        150: "{pokemon} está em apuros! Poder {power}!",
        100: "{pokemon} está enfraquecido! Poder {power}!",
        "default": "Poder {power}!"
    }

    def __init__(self, move_name: str, power_table: Optional[List[Tuple[int, int]]] = None):
        """
        Args:
            move_name: Nome do movimento (flail, reversal, etc)
            power_table: Lista de tuplas (max_hp_percent, power)
                         Ordenada do menor percentual para o maior
        """
        self.move_name = move_name.lower()
        self.power_table = power_table or self.STANDARD_TABLE

    @classmethod
    def for_flail(cls) -> 'HPPowerMove':
        """Factory para Flail"""
        return cls("flail", cls.STANDARD_TABLE)

    @classmethod
    def for_reversal(cls) -> 'HPPowerMove':
        """Factory para Reversal"""
        return cls("reversal", cls.STANDARD_TABLE)

    @classmethod
    def for_trump_card(cls) -> 'HPPowerMove':
        """
        Trump Card: poder baseado no PP restante
        Quanto menos PP, mais forte
        """
        table = [
            (1, 200),  # 1 PP = 200
            (2, 80),  # 2 PP = 80
            (3, 60),  # 3 PP = 60
            (4, 50),  # 4 PP = 50
            (5, 40),  # 5+ PP = 40
        ]
        return cls("trump-card", table)

    @classmethod
    def for_wring_out(cls) -> 'HPPowerMove':
        """
        Wring Out / Crush Grip:
        Poder baseado no HP % do ALVO (não do usuário)
        """
        return cls("wring-out", None)  # Caso especial

    def calculate_power(self, attacker, target=None) -> int:
        """
        Calcula o poder baseado no estado atual.

        Para Flail/Reversal: baseado no HP do atacante
        Para Wring Out: baseado no HP do alvo
        """
        if self.move_name in ["wring-out", "crush-grip"]:
            # Poder baseado no HP do alvo
            if target and target.max_hp > 0:
                hp_percentage = (target.current_hp / target.max_hp) * 100
                # Fórmula: power = 120 * (HP% atual)
                power = int(120 * (hp_percentage / 100))
                return max(1, min(120, power))
            return 60

        elif self.move_name == "trump-card":
            # Poder baseado no PP restante do move
            current_move = attacker.get_current_move()
            if current_move:
                pp_remaining = current_move.current_pp
                for max_pp, power in self.power_table:
                    if pp_remaining <= max_pp:
                        return power
            return 40

        else:
            # Flail/Reversal: baseado no HP do atacante
            if attacker.max_hp <= 0:
                return 20

            hp_percentage = (attacker.current_hp / attacker.max_hp) * 100

            for max_percent, power in self.power_table:
                if hp_percentage <= max_percent:
                    return power

            return 20

    def get_power_message(self, power: int, pokemon_name: str) -> str:
        """Retorna a mensagem apropriada para o nível de poder"""
        # Procura mensagem específica para este poder
        for threshold, template in self.POWER_MESSAGES.items():
            if isinstance(threshold, int) and power >= threshold:
                return template.format(pokemon=pokemon_name, power=power)

        # Mensagem padrão
        return self.POWER_MESSAGES["default"].format(pokemon=pokemon_name, power=power)

    def execute(self, attacker, target, battle_system, effect_manager) -> bool:
        """
        Executa o movimento com poder baseado em HP.
        """
        # ===== OBTÉM O MOVE ATUAL =====
        current_move = attacker.get_current_move()
        if not current_move:
            print(f"[{self.move_name.upper()}] {attacker.name} não tem move selecionado!")
            return False

        # Verifica PP
        if current_move.current_pp <= 0:
            effect_manager.add_status_text(attacker, f"Não há PP para {current_move.name}!", duration=1.0)
            return False

        # Gasta PP
        current_move.current_pp -= 1

        # ===== CALCULA O PODER =====
        original_power = current_move.power
        hp_power = self.calculate_power(attacker, target)

        # Substitui o poder temporariamente
        current_move.power = hp_power

        # Mostra mensagem de poder
        power_message = self.get_power_message(hp_power, attacker.name)
        effect_manager.add_status_text(attacker, power_message, duration=1.2)

        print(f"[{self.move_name.upper()}] HP: {attacker.current_hp}/{attacker.max_hp} "
              f"({attacker.current_hp / attacker.max_hp * 100:.1f}%) -> Poder: {hp_power}")

        # ===== TOCA SOM =====
        move_sound_manager.play_attack_sound(current_move.sound_name)

        # ===== CALCULA ACERTO =====
        hit_chance = current_move.accuracy / 100
        accuracy_mult = effect_manager.get_stat_multiplier(attacker, StatType.ACCURACY)
        evasion_mult = effect_manager.get_stat_multiplier(target, StatType.EVASION)
        final_hit_chance = hit_chance * accuracy_mult / evasion_mult
        final_hit_chance = max(0.01, min(1.0, final_hit_chance))

        will_hit = random.random() <= final_hit_chance

        if not will_hit:
            # Errou
            effect_manager.add_status_text(attacker, f"{attacker.name} errou!", duration=1.0)
            move_sound_manager.play_attack_sound("miss")

            # Restaura poder original
            current_move.power = original_power
            attacker.attack_cooldown = attacker.attack_cooldown_max
            return True

        # ===== CALCULA DANO =====
        damage_result = DamageCalculator.calculate_damage(attacker, target, current_move)

        # Restaura poder original
        current_move.power = original_power

        if not damage_result["hit"]:
            if damage_result.get("effectiveness", 1.0) == 0:
                effect_manager.add_status_text(target, "Não afeta!", duration=1.0)
            attacker.attack_cooldown = attacker.attack_cooldown_max
            return True

        # ===== APLICA DANO =====
        damage = damage_result["damage"]

        if damage > 0:
            target.take_damage(damage, attacker=attacker)
            effect_manager.add_status_text(target, f"-{damage} HP", duration=0.8)

            if damage_result.get("critical", False):
                effect_manager.add_status_text(attacker, "Acerto Crítico!", duration=1.0)

            effectiveness = damage_result.get("effectiveness", 1.0)
            if effectiveness > 1.0:
                effect_manager.add_status_text(attacker, "Super efetivo!", duration=0.8)
            elif 0 < effectiveness < 1.0:
                effect_manager.add_status_text(attacker, "Não é muito efetivo...", duration=0.8)

            move_sound_manager.play_hit_sound(current_move.sound_name)

            if hasattr(target, 'play_hurt_animation'):
                target.play_hurt_animation()

            print(
                f"[{self.move_name.upper()}] {attacker.name} causou {damage} de dano em {target.name} (poder: {hp_power})!")

        # Cooldown
        attacker.attack_cooldown = attacker.attack_cooldown_max

        return True