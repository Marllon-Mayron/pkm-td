# src/battle/effects/move_effect.py
from enum import Enum
from typing import Optional, List, Any, Callable
from dataclasses import dataclass, field
import random


class EffectTarget(Enum):
    """Alvo do efeito"""
    SELF = "self"
    TARGET = "target"
    BOTH = "both"


class EffectTiming(Enum):
    """Quando o efeito acontece"""
    BEFORE_DAMAGE = "before_damage"
    AFTER_DAMAGE = "after_damage"
    ON_HIT = "on_hit"
    ON_MISS = "on_miss"


@dataclass
class MoveEffect:
    """
    Define um efeito de movimento
    """
    # Identificação
    name: str
    effect_type: str  # status, stat_mod, multi_hit, flinch, status_chance, etc

    # Alvo e timing
    target: EffectTarget = EffectTarget.TARGET
    timing: EffectTiming = EffectTiming.AFTER_DAMAGE

    # Parâmetros do efeito
    params: dict = field(default_factory=dict)

    # Callback opcional
    callback: Optional[Callable] = None

    # Descrição para UI
    description: str = ""

    def execute(self, attacker, target, battle_system, effect_manager, damage: int = 0):
        """
        Executa o efeito do movimento

        Args:
            attacker: Pokémon atacante
            target: Pokémon alvo
            battle_system: Sistema de batalha
            effect_manager: Gerenciador de efeitos
            damage: Dano causado (se houver)
        """
        if self.callback:
            return self.callback(attacker, target, battle_system, effect_manager, damage, self.params)

        # Executa efeito padrão baseado no tipo
        if self.effect_type == "status":
            return self._apply_status(attacker, target, effect_manager)
        elif self.effect_type == "status_chance":
            return self._apply_status_with_chance(attacker, target, effect_manager)
        elif self.effect_type == "stat_mod":
            return self._apply_stat_mod(attacker, target, effect_manager)
        elif self.effect_type == "multi_hit":
            return self._apply_multi_hit(attacker, target, battle_system, effect_manager)
        elif self.effect_type == "flinch":
            return self._apply_flinch(attacker, target, effect_manager)
        elif self.effect_type == "recoil":
            return self._apply_recoil(attacker, target, damage, effect_manager)
        elif self.effect_type == "drain":
            return self._apply_drain(attacker, target, damage, effect_manager)

        return True

    def _apply_status(self, attacker, target, effect_manager):
        """Aplica efeito de status"""
        from .status_effect import StatusEffect, StatusType

        status_type_str = self.params.get('status', 'NONE').upper()

        # Mapeia para StatusType
        if status_type_str == 'POISON':
            status_type = StatusType.POISON
        elif status_type_str == 'TOXIC_POISON':
            status_type = StatusType.TOXIC_POISON
        elif status_type_str == 'BURN':
            status_type = StatusType.BURN
        elif status_type_str == 'PARALYSIS':
            status_type = StatusType.PARALYSIS
        elif status_type_str == 'SLEEP':
            status_type = StatusType.SLEEP
        elif status_type_str == 'FREEZE':
            status_type = StatusType.FREEZE
        else:
            status_type = StatusType.NONE

        duration = self.params.get('duration')

        if status_type != StatusType.NONE:
            # Remove status existente? (alguns golpes sobrescrevem)
            if self.params.get('overwrite', False):
                effect_manager.remove_status(target)

            status = StatusEffect(status_type, duration)
            effect_manager.apply_status(target, status, attacker)
            return True

        return False

    def _apply_status_with_chance(self, attacker, target, effect_manager):
        """Aplica efeito de status com chance de sucesso"""
        from .status_effect import StatusEffect, StatusType

        status_type_str = self.params.get('status', 'NONE').upper()
        chance = self.params.get('chance', 0.30)

        # Mapeia para StatusType
        if status_type_str == 'POISON':
            status_type = StatusType.POISON
        elif status_type_str == 'TOXIC_POISON':
            status_type = StatusType.TOXIC_POISON
        elif status_type_str == 'BURN':
            status_type = StatusType.BURN
        elif status_type_str == 'PARALYSIS':
            status_type = StatusType.PARALYSIS
        else:
            status_type = StatusType.NONE

        duration = self.params.get('duration')

        # Verifica se já tem status
        existing_status = effect_manager.get_status(target)
        if existing_status and existing_status.type != StatusType.NONE:
            print(f"[STATUS] {target.name} já está com {existing_status.name}, não pode aplicar novo status!")
            return False

        # Tenta aplicar com a chance
        if status_type != StatusType.NONE and random.random() < chance:
            status = StatusEffect(status_type, duration)
            effect_manager.apply_status(target, status, attacker)

            # Mensagem específica para queimadura
            if status_type == StatusType.BURN:
                print(f"[BURN] {attacker.name} queimou {target.name}!")
            elif status_type == StatusType.POISON:
                print(f"[POISON] {attacker.name} envenenou {target.name}!")

            return True

        return False

    def _apply_stat_mod(self, attacker, target, effect_manager):
        """Aplica modificador de stat - com registro de contribuição"""
        from .stat_modifier import StatType, StatModifier

        stat_name = self.params.get('stat', 'attack')
        stages = self.params.get('stages', 0)
        duration = self.params.get('duration', 8.0)

        print(f"[MOVE_EFFECT] Aplicando modificador: {stat_name} {stages:+d} em {target.name} (duração: {duration}s)")

        # Converte string para StatType
        stat_map = {
            'attack': StatType.ATTACK,
            'defense': StatType.DEFENSE,
            'sp_attack': StatType.SP_ATTACK,
            'sp_defense': StatType.SP_DEFENSE,
            'speed': StatType.SPEED,
            'accuracy': StatType.ACCURACY,
            'evasion': StatType.EVASION
        }

        stat_type = stat_map.get(stat_name.lower())
        if stat_type:
            target_entity = target if self.target == EffectTarget.TARGET else attacker

            # REGISTRA CONTRIBUIÇÃO
            if self.target == EffectTarget.TARGET:
                # É um debuff no alvo
                target_entity.register_stat_modifier(attacker, stat_name, stages)
            else:
                # É um buff em si mesmo ou aliado
                # Para buffs, registramos como contribuição positiva
                target_entity.register_buff_on_ally(attacker, target_entity, stat_name, stages)

            effect_manager.add_stat_modifier(target_entity, stat_type, stages, duration)
            return True

        return False

    def _apply_multi_hit(self, attacker, target, battle_system, effect_manager):
        """Aplica efeito de múltiplos hits"""
        min_hits = self.params.get('min_hits', 2)
        max_hits = self.params.get('max_hits', 5)

        hits = random.randint(min_hits, max_hits)
        total_damage = 0

        effect_manager.add_status_text(attacker, f"Acertou {hits} vezes!")

        for i in range(hits):
            # Calcula dano para cada hit
            damage_result = battle_system._calculate_move_damage(attacker, target, attacker.get_current_move())

            if damage_result["hit"]:
                damage = damage_result["damage"]
                total_damage += damage
                target.take_damage(damage, attacker=attacker)

                # Feedback visual
                effect_manager.add_status_text(target, f"Hit {i + 1}: -{damage} HP", duration=0.3)

        return total_damage > 0

    def _apply_flinch(self, attacker, target, effect_manager):
        """Aplica flinch (hesitação)"""
        chance = self.params.get('chance', 0.3)

        if random.random() < chance:
            # Adiciona efeito de flinch (não pode atacar no próximo turno)
            effect_manager.add_status_text(target, f"{target.name} hesitou!")

            # TODO: Implementar flinch effect
            return True

        return False

    def _apply_recoil(self, attacker, target, damage, effect_manager):
        """Aplica recoil (dano de retorno)"""
        percentage = self.params.get('percentage', 0.33)  # 33% do dano causado

        recoil_damage = max(1, int(damage * percentage))
        attacker.current_hp = max(0, attacker.current_hp - recoil_damage)

        effect_manager.add_status_text(attacker, f"Recoil: -{recoil_damage} HP")

        return True

    def _apply_drain(self, attacker, target, damage, effect_manager):
        """Aplica drain (rouba HP)"""
        percentage = self.params.get('percentage', 0.5)  # 50% do dano

        drain_amount = max(1, int(damage * percentage))
        attacker.current_hp = min(attacker.max_hp, attacker.current_hp + drain_amount)

        effect_manager.add_status_text(attacker, f"Drenou {drain_amount} HP")

        return True