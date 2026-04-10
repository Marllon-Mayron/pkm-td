# src/battle/effects/move_effect.py
from enum import Enum
from typing import Optional, List, Any, Callable
from dataclasses import dataclass, field
import random

from battle.effects import StatusType
from battle.effects.residual_effect import ResidualEffect
from battle.effects.residual_effect import ResidualEffectType, ResidualEffectManager


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


class MultiHitState:
    """Estado de um ataque multi-hit em andamento"""

    def __init__(self, attacker, target, hits, move_name, battle_system):
        self.attacker = attacker
        self.target = target
        self.remaining_hits = hits
        self.total_hits = hits
        self.current_hit = 1
        self.move_name = move_name
        self.battle_system = battle_system
        self.hit_timer = 0.0
        self.hit_interval = 0.15  # 0.15 segundos entre hits (rápido!)
        self.total_damage = 0

    def update(self, dt):
        """Atualiza o multi-hit, retorna True se ainda ativo"""
        self.hit_timer += dt

        if self.hit_timer >= self.hit_interval and self.remaining_hits > 0:
            self.hit_timer = 0
            self._execute_next_hit()

        return self.remaining_hits > 0

    def _execute_next_hit(self):
        """Executa o próximo hit"""
        from src.managers.move_sound_manager import move_sound_manager

        # Pega o move atual
        move = self.attacker.get_current_move()

        # Toca o som do ataque
        move_sound_manager.play_attack_sound(move.sound_name)

        # Calcula dano para este hit
        damage_result = self.battle_system._calculate_move_damage(
            self.attacker, self.target, move
        )

        if damage_result["hit"]:
            damage = damage_result["damage"]
            self.total_damage += damage
            self.target.take_damage(damage, attacker=self.attacker)

            # Toca som de impacto
            move_sound_manager.play_hit_sound(move.sound_name)

            # Toca animação de hurt rapidamente no alvo
            if hasattr(self.target, 'play_hurt_animation'):
                self.target.play_hurt_animation()

        self.current_hit += 1
        self.remaining_hits -= 1


@dataclass
class MoveEffect:
    """
    Define um efeito de movimento
    """
    # Identificação
    name: str
    effect_type: str  # status, stat_mod, multi_hit, flinch, status_chance, residual, confusion, etc

    # Alvo e timing
    target: EffectTarget = EffectTarget.TARGET
    timing: EffectTiming = EffectTiming.AFTER_DAMAGE

    # Parâmetros do efeito
    params: dict = field(default_factory=dict)

    # ===== ATRIBUTOS PARA ANIMAÇÃO =====
    attacker_animation: Optional[str] = None  # Nome da animação que o atacante deve fazer
    min_distance: float = 0  # Distância mínima para usar a animação (0 = sempre usa)

    # Callback opcional
    callback: Optional[Callable] = None

    # Descrição para UI
    description: str = ""

    @classmethod
    def from_config(cls, name: str, config: dict) -> 'MoveEffect':
        """Cria um MoveEffect a partir de configuração"""
        # Converte target para enum se for string
        target = config.get("target", EffectTarget.TARGET)
        if isinstance(target, str):
            target = EffectTarget[target.upper()]

        timing = config.get("timing", EffectTiming.AFTER_DAMAGE)
        if isinstance(timing, str):
            timing = EffectTiming[timing.upper()]

        return cls(
            name=name,
            effect_type=config["effect_type"],
            target=target,
            timing=timing,
            params=config.get("params", {}),
            attacker_animation=config.get("attacker_animation"),
            min_distance=config.get("min_distance", 0),
            description=config.get("description", "")
        )

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
        elif self.effect_type == "high_crit":
            # Já tratado pelo CriticalHitSystem
            return True
        elif self.effect_type == "residual":
            return self._apply_residual(attacker, target, battle_system, effect_manager)
        elif self.effect_type == "remove_residual":
            return self._apply_remove_residual(attacker, target, battle_system, effect_manager)
        elif self.effect_type == "confusion":
            return self._apply_confusion(attacker, target, effect_manager)
        elif self.effect_type == "damage_with_confusion_chance":
            return self._apply_damage_with_confusion_chance(attacker, target, effect_manager, damage)
        elif self.effect_type == "self_confusion_after":
            return self._apply_self_confusion_after(attacker, target, effect_manager)
        elif self.effect_type == "cure_confusion":
            return self._apply_cure_confusion(attacker, target, effect_manager)
        elif self.effect_type == "force_switch":
            return self._apply_force_switch(attacker, target, battle_system, effect_manager)
        elif self.effect_type == "level_damage":
            return self._apply_level_damage(attacker, target, battle_system, effect_manager)
        elif self.effect_type == "ohko":
            return self._apply_ohko(attacker, target, battle_system, effect_manager)
        elif self.effect_type == "fixed_damage":
            return self._apply_fixed_damage(attacker, target, battle_system, effect_manager)
        elif self.effect_type == "heal":
            return self._apply_heal(attacker, target, battle_system, effect_manager)
        elif self.effect_type == "critical_stage_mod":
            return self._apply_critical_stage_mod(attacker, target, battle_system, effect_manager)
        elif self.effect_type == "struggle":
            return self._apply_struggle(attacker, target, battle_system, effect_manager, damage)
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
        elif status_type_str == 'FREEZE':
            status_type = StatusType.FREEZE
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
        """
        Aplica modificador de stat - SUPORTA MÚLTIPLOS STATS
        """
        from .stat_modifier import StatType

        # Verifica se é formato antigo (stat único) ou novo (stats lista)
        if "stats" in self.params:
            # Formato novo: lista de stats
            stats_list = self.params.get("stats", [])
            duration = self.params.get("duration", 8.0)

            # Verifica condições climáticas (Sunny Day para Growth)
            #sun_boost = self.params.get("sun_boost", False)
            #if sun_boost:
                # Verifica se está com Sunny Day ativo
                #is_sunny = self._is_sunny_day_active(attacker, effect_manager)


            # Aplica cada modificador
            success_count = 0
            for stat_config in stats_list:
                stat_name = stat_config.get("stat", "attack")
                stages = stat_config.get("stages", 0)

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
                        target_entity.register_stat_modifier(attacker, stat_name, stages)
                    else:
                        target_entity.register_buff_on_ally(attacker, target_entity, stat_name, stages)

                    effect_manager.add_stat_modifier(target_entity, stat_type, stages, duration)
                    success_count += 1

                    # Mensagem para cada stat (opcional, pode ser simplificado)
                    stat_display = {
                        StatType.ATTACK: "Ataque",
                        StatType.DEFENSE: "Defesa",
                        StatType.SP_ATTACK: "Ataque Especial",
                        StatType.SP_DEFENSE: "Defesa Especial",
                        StatType.SPEED: "Velocidade",
                    }
                    stat_name_pt = stat_display.get(stat_type, stat_name)
                    if stages > 0:
                        effect_manager.add_status_text(target_entity, f"{stat_name_pt} aumentou!", duration=0.8)
                    else:
                        effect_manager.add_status_text(target_entity, f"{stat_name_pt} diminuiu!", duration=0.8)

            # Mensagem consolidada
            if success_count > 0:
                target_name = target.name if self.target == EffectTarget.TARGET else attacker.name
                effect = "aumentaram" if any(s["stages"] > 0 for s in stats_list) else "diminuíram"
                print(f"[MOVE_EFFECT] {success_count} stats de {target_name} {effect}!")
                return True

            return False

        else:
            # ===== FORMATO ANTIGO (UM ÚNICO STAT) - MANTIDO PARA COMPATIBILIDADE =====
            stat_name = self.params.get('stat', 'attack')
            stages = self.params.get('stages', 0)
            duration = self.params.get('duration', 8.0)
            chance = self.params.get('chance', 1.0)

            # Verifica chance
            import random
            if random.random() > chance:
                if chance < 1.0:
                    effect_manager.add_status_text(attacker, f"Mas falhou!", duration=0.8)
                    print(f"[STAT_MOD] {self.name} falhou em reduzir {stat_name} de {target.name}!")
                return False

            print(
                f"[MOVE_EFFECT] Aplicando modificador: {stat_name} {stages:+d} em {target.name} (duração: {duration}s)")

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
                    target_entity.register_stat_modifier(attacker, stat_name, stages)
                else:
                    target_entity.register_buff_on_ally(attacker, target_entity, stat_name, stages)

                effect_manager.add_stat_modifier(target_entity, stat_type, stages, duration)

                # Mensagem
                stat_display = {
                    StatType.ATTACK: "Ataque",
                    StatType.DEFENSE: "Defesa",
                    StatType.SP_ATTACK: "Ataque Especial",
                    StatType.SP_DEFENSE: "Defesa Especial",
                    StatType.SPEED: "Velocidade",
                }
                stat_name_pt = stat_display.get(stat_type, stat_name)
                if stages > 0:
                    effect_manager.add_status_text(target_entity, f"{stat_name_pt} aumentou!", duration=0.8)
                else:
                    effect_manager.add_status_text(target_entity, f"{stat_name_pt} diminuiu!", duration=0.8)

                return True

            return False

    def _apply_multi_hit(self, attacker, target, battle_system, effect_manager):
        """Inicia um ataque multi-hit (será processado ao longo do tempo)"""
        min_hits = self.params.get('min_hits', 2)
        max_hits = self.params.get('max_hits', 5)

        hits = random.randint(min_hits, max_hits)

        # Cria o estado do multi-hit
        multi_hit_state = MultiHitState(attacker, target, hits, self.name, battle_system)

        # Armazena no battle_system para processamento contínuo
        battle_system.active_multi_hit = multi_hit_state

        return True

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

        return True

    def _apply_heal(self, attacker, target, battle_system, effect_manager):
        """
        Aplica efeito de cura (Recover)
        """
        heal_percentage = self.params.get("heal_percentage", 0.5)
        heal_formula = self.params.get("heal_formula", "max_hp_percentage")

        # Determina o alvo (SELF para Recover)
        target_entity = target if self.target == EffectTarget.TARGET else attacker

        # Verifica se o alvo já está com HP cheio
        if target_entity.current_hp >= target_entity.max_hp:
            effect_manager.add_status_text(target_entity, f"O HP de {target_entity.name} já está no máximo!",
                                           duration=1.0)
            print(f"[HEAL] {target_entity.name} já está com HP cheio!")
            return False

        # Calcula quantidade de cura
        if heal_formula == "max_hp_percentage":
            heal_amount = int(target_entity.max_hp * heal_percentage)
        else:
            heal_amount = int(target_entity.max_hp * 0.5)  # Fallback

        # Garante cura mínima de 1 HP
        heal_amount = max(1, heal_amount)

        # Calcula cura real (não pode ultrapassar o máximo)
        old_hp = target_entity.current_hp
        new_hp = min(target_entity.max_hp, target_entity.current_hp + heal_amount)
        actual_heal = new_hp - old_hp

        if actual_heal <= 0:
            effect_manager.add_status_text(target_entity, f"Mas falhou!", duration=0.8)
            return False

        # Aplica a cura
        target_entity.current_hp = new_hp

        # Mostra mensagem
        effect_manager.add_status_text(target_entity, f"{target_entity.name} recuperou {actual_heal} HP!", duration=1.5)
        print(f"[HEAL] {target_entity.name} recuperou {actual_heal} HP com {self.name}!")

        # Toca som de cura (opcional - pode usar um som existente)
        from src.managers.move_sound_manager import move_sound_manager
        move_sound_manager.play_attack_sound("heal")  # Se não tiver, pode remover ou usar outro

        return True

    def _apply_struggle(self, attacker, target, battle_system, effect_manager, damage):
        """
        Aplica efeitos do Struggle (recoil)
        O dano já foi aplicado pelo battle_system
        """
        recoil_percentage = self.params.get("recoil_percentage", 0.25)

        recoil_damage = max(1, int(attacker.max_hp * recoil_percentage))
        attacker.take_damage(recoil_damage, attacker=attacker)

        effect_manager.add_status_text(attacker, f"Recoil: -{recoil_damage} HP", duration=1.0)
        print(f"[STRUGGLE] {attacker.name} sofreu {recoil_damage} de recoil!")

        return True

    def _apply_residual(self, attacker, target, battle_system, effect_manager):
        """Aplica efeito residual (Leech Seed, Wrap, etc)"""

        residual_type_str = self.params.get('residual_type', 'leech_seed')
        duration = self.params.get('duration', 5)
        tick_interval = self.params.get('tick_interval', 2.0)
        drain_percentage = self.params.get('drain_percentage', 0.125)

        # Mapeia string para enum
        residual_type_map = {
            'leech_seed': ResidualEffectType.LEECH_SEED,
            'wrap': ResidualEffectType.WRAP,
            'bind': ResidualEffectType.BIND,
            'fire_spin': ResidualEffectType.FIRE_SPIN,
            'whirlpool': ResidualEffectType.WHIRLPOOL,
            'clamp': ResidualEffectType.CLAMP,
            'sand_tomb': ResidualEffectType.SAND_TOMB,
            'infestation': ResidualEffectType.INFESTATION,
            'magma_storm': ResidualEffectType.MAGMA_STORM,
            'salt_cure': ResidualEffectType.SALT_CURE,
        }
        residual_type = residual_type_map.get(residual_type_str, ResidualEffectType.LEECH_SEED)

        # Verifica imunidade: Grass Pokémon são imunes a Leech Seed
        if residual_type == ResidualEffectType.LEECH_SEED:
            if any(t.lower() == "grass" for t in target.types):
                effect_manager.add_status_text(target, f"Não afeta {target.name}!")
                print(f"[LEECH_SEED] {target.name} é tipo Grass, imune a Leech Seed!")
                return False

        # Cria callbacks
        def on_tick(effect):
            """Executado a cada tick do efeito"""
            if effect.effect_type == ResidualEffectType.LEECH_SEED:
                self._apply_leech_seed_tick(effect, battle_system, effect_manager)
            else:
                # Para outros efeitos (Wrap, etc) - dano puro
                self._apply_trapping_tick(effect, battle_system, effect_manager, drain_percentage)

        def on_remove(effect):
            """Quando o efeito é removido"""
            effect_manager.add_status_text(target, f"{target.name} se libertou!", duration=1.0)

        # Cria o efeito residual
        effect = ResidualEffect(
            effect_type=residual_type,
            source=attacker,
            target=target,
            duration=duration,
            tick_interval=tick_interval,
            on_tick_callback=on_tick,
            on_remove_callback=on_remove
        )

        # Adiciona ao gerenciador de efeitos residuais do battle_system
        if not hasattr(battle_system, 'residual_effects'):
            battle_system.residual_effects = ResidualEffectManager(battle_system)

        battle_system.residual_effects.add_effect(effect)
        effect_manager.add_status_text(target, f"{target.name} foi plantado com sementes!")

        return True

    def _apply_leech_seed_tick(self, effect, battle_system, effect_manager):
        """Aplica o tick do Leech Seed (drena HP)"""
        target = effect.target
        source = effect.source

        # Verifica se o alvo ainda está vivo
        if target.is_defeated or not target.is_alive():
            effect.remove()
            return

        # Verifica se a fonte ainda está viva
        if source.is_defeated or not source.is_alive():
            effect.remove()
            return

        # Calcula dano: 1/8 do HP máximo
        drain_amount = max(1, target.max_hp // 8)

        # Aplica dano ao alvo
        old_hp = target.current_hp
        target.take_damage(drain_amount, attacker=source)
        actual_damage = old_hp - target.current_hp

        if actual_damage > 0:
            # Cura a fonte
            heal_amount = actual_damage
            source.current_hp = min(source.max_hp, source.current_hp + heal_amount)

            print(f"[LEECH_SEED] {target.name} perdeu {actual_damage} HP, {source.name} recuperou {heal_amount} HP")

            # Toca som de dreno
            from src.managers.move_sound_manager import move_sound_manager
            move_sound_manager.play_attack_sound("drain")
        else:
            print(f"[LEECH_SEED] {target.name} não sofreu dano (imune?)")

    def _apply_trapping_tick(self, effect, battle_system, effect_manager, damage_percentage):
        """Aplica tick de dano para efeitos de trapping (Wrap, Bind, etc)"""
        target = effect.target

        if target.is_defeated or not target.is_alive():
            effect.remove()
            return

        # Dano: 1/8 do HP máximo por turno (padrão)
        damage = max(1, int(target.max_hp * damage_percentage))
        target.take_damage(damage, attacker=effect.source)

        effect_manager.add_status_text(target, f"-{damage} HP ({effect.effect_type.value})")
        print(f"[TRAPPING] {target.name} sofreu {damage} HP de {effect.effect_type.value}")

    def _apply_remove_residual(self, attacker, target, battle_system, effect_manager):
        """Remove efeitos residuais (Rapid Spin, etc)"""
        removes = self.params.get('removes', [])

        # Mapeia strings para enum
        residual_type_map = {
            'leech_seed': ResidualEffectType.LEECH_SEED,
            'wrap': ResidualEffectType.WRAP,
            'bind': ResidualEffectType.BIND,
            'fire_spin': ResidualEffectType.FIRE_SPIN,
            'whirlpool': ResidualEffectType.WHIRLPOOL,
            'clamp': ResidualEffectType.CLAMP,
            'sand_tomb': ResidualEffectType.SAND_TOMB,
            'infestation': ResidualEffectType.INFESTATION,
            'magma_storm': ResidualEffectType.MAGMA_STORM,
            'salt_cure': ResidualEffectType.SALT_CURE,
        }

        removed_count = 0

        for residual_type_str in removes:
            residual_type = residual_type_map.get(residual_type_str)

            if residual_type and hasattr(battle_system, 'residual_effects'):
                if battle_system.residual_effects.has_effect_on_target(attacker, residual_type):
                    battle_system.residual_effects.remove_effect_on_target(attacker, residual_type)
                    removed_count += 1

        if removed_count > 0:
            effect_manager.add_status_text(attacker, f"{attacker.name} se libertou!")
            print(f"[REMOVE_RESIDUAL] {attacker.name} removeu {removed_count} efeitos residuais")

        return True

    def _apply_level_damage(self, attacker, target, battle_system, effect_manager):
        """
        Aplica dano baseado no nível do atacante (Seismic Toss, Night Shade)
        Dano = level do atacante
        """
        damage = attacker.level

        # Verifica imunidade por tipo (Ghost é imune a Fighting)
        ignore_type = self.params.get("ignore_type_effectiveness", True)

        if not ignore_type:
            # Calcula eficácia normal de tipo
            from src.battle.damage_calculator import DamageCalculator
            effectiveness = DamageCalculator._get_type_effectiveness(
                self.name, target.types
            )
            if effectiveness == 0:
                effect_manager.add_status_text(target, "Não afeta!", duration=1.0)
                print(f"[LEVEL_DAMAGE] {target.name} é imune!")
                return False

        # Aplica dano
        target.take_damage(damage, attacker=attacker)

        effect_manager.add_status_text(target, f"-{damage} HP", duration=1.0)
        print(f"[LEVEL_DAMAGE] {attacker.name} causou {damage} de dano (nível) em {target.name}!")

        return True

    def _apply_ohko(self, attacker, target, battle_system, effect_manager):
        """
        Aplica One-Hit KO (Horn Drill, Fissure, Guillotine)

        Regras:
        - Só funciona se atacante level >= target level
        - Accuracy = 30% + (atacante level - target level) * 1%
        - Máximo 100%
        - Imunidade: Ghost é imune a Horn Drill, etc
        """

        # ===== VERIFICA IMUNIDADE DE TIPO =====
        move_name = self.name.lower()

        # Horn Drill (Normal) não afeta Ghost
        if move_name == "horn-drill":
            if any(t.lower() == "ghost" for t in target.types):
                effect_manager.add_status_text(target, "Não afeta!", duration=1.0)
                print(f"[OHKO] {target.name} é tipo Fantasma, imune a {self.name}!")
                return False

        # Fissure (Ground) não afeta Flying ou Levitate
        if move_name == "fissure":
            if any(t.lower() == "flying" for t in target.types):
                effect_manager.add_status_text(target, "Não afeta!", duration=1.0)
                print(f"[OHKO] {target.name} é tipo Voador, imune a {self.name}!")
                return False
            # TODO: Verificar habilidade Levitate

        # ===== VERIFICA NÍVEL =====
        if attacker.level < target.level:
            effect_manager.add_status_text(attacker, f"{attacker.name} é muito fraco!", duration=1.0)
            print(f"[OHKO] {attacker.name} (Lv.{attacker.level}) é mais fraco que {target.name} (Lv.{target.level})!")
            return False

        # ===== CALCULA ACERTO =====
        base_accuracy = self.params.get("base_accuracy", 30)
        level_bonus = self.params.get("level_difference_bonus", 1)
        max_accuracy = self.params.get("max_accuracy", 100)

        level_diff = attacker.level - target.level
        accuracy = base_accuracy + (level_diff * level_bonus)
        accuracy = min(max_accuracy, accuracy)

        # Verifica acerto
        import random
        if random.random() * 100 > accuracy:
            effect_manager.add_status_text(attacker, "Errou!", duration=0.8)
            print(f"[OHKO] {self.name} errou! (Acerto: {accuracy}%)")
            return False

        # ===== APLICA OHKO =====
        # Causa dano igual ao HP máximo do alvo
        damage = target.current_hp

        target.take_damage(damage, attacker=attacker)

        effect_manager.add_status_text(target, f"{target.name} foi derrubado!", duration=1.5)
        print(f"[OHKO] {attacker.name} usou {self.name} e derrubou {target.name}!")

        return True

    def _apply_critical_stage_mod(self, attacker, target, battle_system, effect_manager):
        """
        Aplica modificador de estágio de crítico (Focus Energy)
        """
        from src.battle.critical_hit import CriticalHitSystem

        stage_increase = self.params.get("stage_increase", 2)
        max_stage = self.params.get("max_stage", 4)
        stackable = self.params.get("stackable", False)

        # Determina o alvo (geralmente SELF)
        target_entity = target if self.target == EffectTarget.TARGET else attacker

        # Verifica se já tem Focus Energy ativo
        pokemon_id = id(target_entity)
        current_stage = CriticalHitSystem._crit_stage_modifiers.get(pokemon_id, 0)

        if not stackable and current_stage > 0:
            effect_manager.add_status_text(target_entity, f"{target_entity.name} já está com foco energético!",
                                           duration=1.5)
            print(f"[CRIT] {target_entity.name} já está com Focus Energy ativo!")
            return False

        # Verifica se não vai exceder o máximo
        if current_stage + stage_increase > max_stage:
            effect_manager.add_status_text(target_entity, f"Mas o efeito não aumentou mais!", duration=1.0)
            print(f"[CRIT] {target_entity.name} já atingiu o máximo de estágio de crítico!")
            return False

        # Aplica o modificador
        success = CriticalHitSystem.add_crit_stage_modifier(target_entity, stage_increase)

        if success:
            # Mostra mensagem
            effect_manager.add_status_text(target_entity, f"{target_entity.name} concentrou sua energia!", duration=1.5)
            print(
                f"[FOCUS_ENERGY] {target_entity.name} aumentou sua taxa de acerto crítico em {stage_increase} estágios!")

            # Mensagem adicional sobre a taxa
            from src.battle.critical_hit import CriticalHitSystem
            new_chance = CriticalHitSystem.calculate_critical_chance(target_entity)
            effect_manager.add_status_text(target_entity, f"Taxa de crítico aumentada!", duration=1.0)

            return True

        return False

    def _apply_fixed_damage(self, attacker, target, battle_system, effect_manager):
        """
        Aplica dano fixo (Sonic Boom, Dragon Rage, etc)
        """
        fixed_damage = self.params.get("fixed_damage", 20)

        # Verifica imunidade de tipo (se aplicável)
        if self.name.lower() == "sonic-boom":
            # Sonic Boom é Normal, não afeta Ghost
            if any(t.lower() == "ghost" for t in target.types):
                effect_manager.add_status_text(target, "Não afeta!", duration=1.0)
                print(f"[FIXED_DAMAGE] {target.name} é tipo Fantasma, imune a {self.name}!")
                return False

        # Aplica dano fixo
        target.take_damage(fixed_damage, attacker=attacker)

        print(f"[FIXED_DAMAGE] {attacker.name} causou {fixed_damage} de dano fixo em {target.name}!")

        return True
    # ===== MÉTODOS DE CONFUSÃO =====

    def _apply_confusion(self, attacker, target, effect_manager):
        """Aplica confusão diretamente no alvo"""
        duration = self.params.get('duration')  # None = aleatório 1-4 turnos

        # Verifica se o alvo já está com algum status que impede ação
        status = effect_manager.get_status(target)
        if status and status.type in [StatusType.SLEEP, StatusType.FREEZE]:
            effect_manager.add_status_text(target,
                                           f"{target.name} está {status.name.lower()} e não pode ficar confuso!")
            print(f"[CONFUSION] {target.name} está {status.name.lower()}, não pode aplicar confusão!")
            return False

        success = effect_manager.apply_confusion(target, source=attacker, duration=duration)
        return success

    def _apply_damage_with_confusion_chance(self, attacker, target, effect_manager, damage):
        """Dano + chance de causar confusão (ex: Psybeam, Confusion)"""
        chance = self.params.get('chance', 0.10)

        if random.random() < chance:
            # Verifica se o alvo já está com algum status que impede ação
            status = effect_manager.get_status(target)
            if not (status and status.type in [StatusType.SLEEP, StatusType.FREEZE]):
                effect_manager.apply_confusion(target, source=attacker)
                effect_manager.add_status_text(target, f"{target.name} ficou confuso!")
                print(f"[CONFUSION] {attacker.name} causou confusão em {target.name}!")

        return True

    def _apply_self_confusion_after(self, attacker, target, effect_manager):
        """
        Para movimentos como Petal Dance, Thrash.
        Ataca por X turnos, depois causa confusão no usuário.
        """
        duration = self.params.get('duration', 3)

        # TODO: Implementar lógica de multi-turn attack
        # Por enquanto, aplica confusão após o ataque

        # Não aplica confusão se o atacante já está com sono ou congelado
        status = effect_manager.get_status(attacker)
        if status and status.type in [StatusType.SLEEP, StatusType.FREEZE]:
            return True

        effect_manager.apply_confusion(attacker, source=attacker, duration=duration)
        effect_manager.add_status_text(attacker, f"{attacker.name} ficou confuso devido ao esforço!")
        print(f"[CONFUSION] {attacker.name} se confundiu após usar {self.name}!")

        return True

    def _apply_cure_confusion(self, attacker, target, effect_manager):
        """Cura confusão (ex: Persim Berry)"""
        target_entity = target if self.target == EffectTarget.TARGET else attacker

        if effect_manager.is_confused(target_entity):
            effect_manager.remove_confusion(target_entity)
            effect_manager.add_status_text(target_entity, f"{target_entity.name} se recuperou da confusão!")
            print(f"[CONFUSION] Confusão de {target_entity.name} foi curada!")
            return True

        return False

    # ===== MÉTODOS DE MOVIMENTAÇÕES =====

    def _apply_force_switch(self, attacker, target, battle_system, effect_manager):
        """
        Aplica efeito de Roar/Whirlwind - força troca/fuga

        - Se target é selvagem (is_wild=True): faz fugir (remove do wave_manager)
        - Se target é aliado (is_wild=False): volta para o time (is_placed=False)
        """

        # Verifica se o alvo está vivo
        if target.is_defeated or not target.is_alive():
            effect_manager.add_status_text(attacker, "Mas falhou!", duration=1.0)
            print(f"[FORCE_SWITCH] {target.name} já está derrotado!")
            return False

        # Verifica imunidade (Ghost types são imunes? Nos jogos originais sim)
        # Ghost types são imunes a Roar/Whirlwind
        if any(t.lower() == "ghost" for t in target.types):
            effect_manager.add_status_text(target, f"Não afeta {target.name}!", duration=1.0)
            print(f"[FORCE_SWITCH] {target.name} é tipo Fantasma, imune!")
            return False

        # Verifica habilidade Suction Cups (ventosas) - impede troca
        if hasattr(target, 'has_ability') and target.has_ability("Suction Cups"):
            effect_manager.add_status_text(target, f"{target.name} não pode ser forçado a trocar!", duration=1.0)
            print(f"[FORCE_SWITCH] {target.name} tem Ventosas, imune!")
            return False

        # ===== CASO 1: POKÉMON SELVAGEM (INIMIGO) - FAZ FUGIR =====
        if target.is_wild:
            return self._force_wild_flee(target, attacker, battle_system, effect_manager)

        # ===== CASO 2: POKÉMON ALIADO - VOLTA PARA O TIME =====
        else:
            return self._force_ally_return(target, attacker, battle_system, effect_manager)

    def _force_wild_flee(self, target, attacker, battle_system, effect_manager):
        """
        Força um Pokémon selvagem a FUGIR - inverte o path e o torna passivo.

        Args:
            target: Pokémon selvagem que vai fugir
            attacker: Pokémon que usou o golpe
            battle_system: Sistema de batalha
            effect_manager: Gerenciador de efeitos
        """

        # Verifica se o wave_manager existe
        if not battle_system.game_scene or not hasattr(battle_system.game_scene, 'wave_manager'):
            effect_manager.add_status_text(target, "Mas falhou!", duration=1.0)
            print(f"[FORCE_SWITCH] Não foi possível fazer {target.name} fugir!")
            return False

        wave_manager = battle_system.game_scene.wave_manager

        # Verifica se o target está na lista de inimigos ativos
        if target not in wave_manager.active_enemies:
            effect_manager.add_status_text(target, "Mas falhou!", duration=1.0)
            print(f"[FORCE_SWITCH] {target.name} não está na lista de inimigos ativos!")
            return False

        # ===== BOSS NÃO É ACOVARDADO =====
        if target.is_boss:
            effect_manager.add_status_text(target, f"{target.name} não se abalou!", duration=1.5)
            print(f"[FORCE_SWITCH] {target.name} é um BOSS e não pode ser acovardado!")
            return False

        # Verifica se o target tem um path para inverter
        if not hasattr(target, 'path') or not target.path:
            effect_manager.add_status_text(target, "Mas falhou!", duration=1.0)
            print(f"[FORCE_SWITCH] {target.name} não tem path para inverter!")
            return False

        # ===== 1. MUDA O PADRÃO DE ATAQUE PARA PASSIVO =====
        from src.battle.attack_pattern import AttackPattern

        old_pattern = target.attack_pattern
        target.attack_pattern = AttackPattern.PASSIVE
        print(f"[FORCE_SWITCH] {target.name} mudou de {old_pattern} para PASSIVO (acovardado)!")

        # ===== 2. LIMPA O ALVO ATUAL =====
        if hasattr(target, 'target') and target.target:
            print(f"[FORCE_SWITCH] {target.name} abandonou o alvo {target.target.name}")
            target.target = None

        # ===== 3. RESETA ESTADO DE COMBATE =====
        target.combat_state = "idle"
        if hasattr(target, '_attack_attempts'):
            target._attack_attempts = 0

        # ===== 4. INTERROMPE QUALQUER ANIMAÇÃO DE ATAQUE =====
        if hasattr(target, '_attack_animation_active'):
            target._attack_animation_active = False
        if hasattr(target, '_damage_applied'):
            target._damage_applied = False

        # ===== 5. INVERTE O PATH =====
        effect_manager.add_status_text(target, f"{target.name} fugiu assustado!", duration=2.0)
        print(f"[FORCE_SWITCH] {target.name} fugiu e está voltando pelo path devido a {attacker.name}!")

        # Usa o PathTracker para inverter a direção
        if hasattr(wave_manager, 'path_tracker'):
            path_tracker = wave_manager.path_tracker

            # Inverte o path do inimigo (faz ele voltar)
            path_tracker.reverse_path(target)

            # Reseta flags de chegada para evitar detecção imediata
            state = path_tracker._enemy_state.get(id(target))
            if state:
                state['has_reached_start'] = False
                state['has_reached_end'] = False
                state['arrival_cooldown'] = 0.0
                state['just_reversed_cooldown'] = 0.5  # Cooldown para evitar reverse duplo
                # Limpa ignore_path_timer para garantir que ele volte pelo path
                state['ignore_path_timer'] = 0.0
                print(f"[FORCE_SWITCH] Path de {target.name} invertido! Agora voltando passivamente.")

            # ===== 6. FORÇA ANIMAÇÃO DE WALK =====
            if hasattr(target, 'set_animation') and target.has_animation("walk"):
                target.set_animation("walk")

            # ===== 7. TOCA ANIMAÇÃO DE HURT (ASSUSTADO) =====
            if hasattr(target, 'play_hurt_animation'):
                target.play_hurt_animation()

            return True

        return False

    def _force_ally_return(self, target, attacker, battle_system, effect_manager):
        """
        Força um Pokémon aliado a retornar para o time (is_placed = False)

        Args:
            target: Pokémon aliado que vai retornar
            attacker: Pokémon que usou o golpe (pode ser aliado ou inimigo)
            battle_system: Sistema de batalha
            effect_manager: Gerenciador de efeitos
        """

        # Verifica se o placement_manager existe
        if not battle_system.game_scene or not hasattr(battle_system.game_scene, 'placement_manager'):
            effect_manager.add_status_text(target, "Mas falhou!", duration=1.0)
            print(f"[FORCE_SWITCH] Não foi possível fazer {target.name} retornar!")
            return False

        placement_manager = battle_system.game_scene.placement_manager

        # Verifica se o target está no mapa
        if not target.is_placed or target not in placement_manager.placed_pokemon:
            effect_manager.add_status_text(target, "Mas falhou!", duration=1.0)
            print(f"[FORCE_SWITCH] {target.name} não está no mapa!")
            return False

        # Mostra mensagem de retorno
        effect_manager.add_status_text(target, f"{target.name} foi forçado a retornar!", duration=2.0)
        print(f"[FORCE_SWITCH] {target.name} foi forçado a retornar ao time por {attacker.name}!")

        # ===== LIMPA REFERÊNCIAS =====
        # Limpa target de outros Pokémon que possam estar mirando nele
        for ally in placement_manager.placed_pokemon:
            if ally != target and hasattr(ally, 'target') and ally.target == target:
                ally.target = None
                if hasattr(ally, '_attack_attempts'):
                    ally._attack_attempts = 0
                ally.combat_state = "idle"

        # Limpa target do próprio Pokémon
        if hasattr(target, 'target'):
            target.target = None

        # Reseta estado de combate
        target.combat_state = "idle"
        target.charge_cooldown = 0

        # Remove efeitos residuais
        if hasattr(battle_system, 'residual_effects'):
            battle_system.residual_effects.remove_effect_on_target(target)

        # Remove do placement_manager (volta para o time)
        placement_manager.remove_pokemon(target)

        # Opcional: toca som de retorno
        from src.managers.move_sound_manager import move_sound_manager
        move_sound_manager.play_attack_sound("return")

        print(f"[FORCE_SWITCH] {target.name} retornou ao time com sucesso!")
        return True