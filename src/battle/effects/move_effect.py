# src/battle/effects/move_effect.py
from enum import Enum
from typing import Optional, Callable
from dataclasses import dataclass, field
import random, math

from src.battle.effects import StatusType
from src.battle.effects.residual_effect import ResidualEffect
from src.battle.effects.residual_effect import ResidualEffectType, ResidualEffectManager


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
    is_area: bool = False

    # ===== ATRIBUTOS PARA ANIMAÇÃO =====
    attacker_animation: Optional[str] = None  # Nome da animação que o atacante deve fazer
    min_distance: float = 0  # Distância mínima para usar a animação (0 = sempre usa)

    # ===== MENSAGEM PERSONALIZADA PARA GOLPES DE 2 TURNOS =====
    charge_message: Optional[str] = None

    # Callback opcional
    callback: Optional[Callable] = None

    # Descrição para UI
    description: str = ""

    @classmethod
    def from_config(cls, name: str, config: dict) -> 'MoveEffect':
        """Cria um MoveEffect a partir de configuração"""
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
            charge_message=config.get("charge_message"),
            description=config.get("description", ""),
            is_area=config.get("is_area", False)
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
        # ===== SE FOR ATAQUE EM ÁREA, PROCESSA MÚLTIPLOS ALVOS =====
        if self.is_area:
            return self._execute_area_effect(attacker, target, battle_system, effect_manager, damage)

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
        elif self.effect_type == "variable_level_damage":
            return self._apply_variable_level_damage(attacker, target, battle_system, effect_manager)
        elif self.effect_type == "ohko":
            return self._apply_ohko(attacker, target, battle_system, effect_manager)
        elif self.effect_type == "fixed_damage":
            return self._apply_fixed_damage(attacker, target, battle_system, effect_manager)
        elif self.effect_type == "percent_damage":
            return self._apply_percent_damage(attacker, target, battle_system, effect_manager)
        elif self.effect_type == "heal":
            return self._apply_heal(attacker, target, battle_system, effect_manager)
        elif self.effect_type == "remove_all_stat_mods":
            return self._apply_remove_all_stat_mods(attacker, target, battle_system, effect_manager)
        elif self.effect_type == "critical_stage_mod":
            return self._apply_critical_stage_mod(attacker, target, battle_system, effect_manager)
        elif self.effect_type == "self_faint":
            return self._apply_self_faint(attacker, target, battle_system, effect_manager, damage)
        elif self.effect_type == "dream_eater":
            return self._apply_dream_eater(attacker, target, battle_system, effect_manager, damage)
        elif self.effect_type == "stat_mod_with_visual":
            return self._apply_stat_mod_with_visual(attacker, target, battle_system, effect_manager)
        elif self.effect_type == "rage_mode":
            return self._apply_rage_mode(attacker, target, effect_manager)
        elif self.effect_type == "teleport_swap":
            return self._apply_teleport_swap(attacker, target, battle_system, effect_manager)
        elif self.effect_type == "random_status_chance":
            return self._apply_random_status_chance(attacker, target, effect_manager)
        elif self.effect_type == "two_turn_attack":
            return self._apply_two_turn_attack(attacker, target, battle_system, effect_manager)
        elif self.effect_type == "light_screen":
            return self._apply_light_screen(attacker, target, battle_system, effect_manager)
        elif self.effect_type == "reflect":
            return self._apply_reflect(attacker, target, battle_system, effect_manager)
        elif self.effect_type == "counter":
            return self._apply_counter(attacker, target, battle_system, effect_manager)
        elif self.effect_type == "self_confusion_after_uses":
            return self._apply_self_confusion_after_uses(attacker, target, battle_system, effect_manager, damage)
        elif self.effect_type == "pay_day":
            return self._apply_pay_day(attacker, target, battle_system, effect_manager, damage)
        elif self.effect_type == "mist":
            return self._apply_mist(attacker, target, battle_system, effect_manager, damage)
        elif self.effect_type == "disable":
            return self._apply_disable(attacker, target, battle_system, effect_manager, damage)
        elif self.effect_type == "struggle":
            return self._apply_struggle(attacker, target, battle_system, effect_manager, damage)
        elif self.effect_type == "metronome":
            return self._apply_metronome(attacker, target, battle_system, effect_manager)
        elif self.effect_type == "mimic":
            return self._apply_mimic(attacker, target, battle_system, effect_manager)
        elif self.effect_type == "transform":
            return self._apply_transform(attacker, target, battle_system, effect_manager)
        return True

    def _apply_status(self, attacker, target, effect_manager):
        """Aplica efeito de status"""
        from src.battle.effects.status_effect import StatusEffect, StatusType

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
        from src.battle.effects.stat_modifier import StatType

        # Verifica se é formato antigo (stat único) ou novo (stats lista)
        if "stats" in self.params:
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

    def _apply_self_faint(self, attacker, target, battle_system, effect_manager, damage):
        """
        Aplica efeito de auto-destruição (Explosion, Self-Destruct)
        O usuário desmaia após causar dano
        """
        # Verifica se o atacante já não está derrotado
        if attacker.is_defeated:
            print(f"[SELF_FAINT] {attacker.name} já está derrotado!")
            return False

        # Causa dano ao atacante igual ao HP atual (desmaia)
        attacker.take_damage(attacker.current_hp, attacker=attacker)

        # Força a derrota
        attacker.set_defeated(True)

        # Mensagem
        effect_manager.add_status_text(attacker, f"{attacker.name} desmaiou!", duration=1.5)
        print(f"[SELF_FAINT] {attacker.name} desmaiou após usar {self.name}!")

        # Toca som de faint
        from src.managers.move_sound_manager import move_sound_manager
        move_sound_manager.play_attack_sound("faint")

        return True

    def _apply_self_faint_area(self, attacker, target, battle_system, effect_manager, damage):
        """
        Aplica Explosion em área (causa dano ao alvo)
        O desmaio do atacante acontece APÓS todos os alvos serem atingidos
        """
        from src.battle.damage_calculator import DamageCalculator

        current_move = attacker.get_current_move()
        if not current_move:
            return

        # Calcula dano para este alvo
        damage_result = DamageCalculator.calculate_damage(attacker, target, current_move)

        if damage_result["hit"]:
            old_hp = target.current_hp
            target.take_damage(damage_result["damage"], attacker=attacker)
            actual_damage = old_hp - target.current_hp

            effect_manager.add_status_text(target, f"-{actual_damage} HP", duration=0.8)

            if damage_result["effectiveness"] > 1.0:
                effect_manager.add_status_text(target, "Super efetivo!", duration=0.8)
            elif 0 < damage_result["effectiveness"] < 1.0:
                effect_manager.add_status_text(target, "Não é muito efetivo...", duration=0.8)

            print(f"[AREA_EXPLOSION] {attacker.name} causou {actual_damage} de dano em {target.name}!")

    def _apply_remove_all_stat_mods(self, attacker, target, battle_system, effect_manager):
        """
        Aplica efeito de Haze - remove todos os modificadores de stat de todos os Pokémon em campo
        """
        print(f"[HAZE] {attacker.name} usou {self.name}!")

        # Lista para armazenar todos os Pokémon em campo
        all_pokemon_in_field = []

        # Adiciona o atacante
        all_pokemon_in_field.append(attacker)

        # Adiciona o alvo
        if target and target != attacker:
            all_pokemon_in_field.append(target)

        # Adiciona todos os aliados do atacante (se houver placement_manager)
        if battle_system.game_scene and hasattr(battle_system.game_scene, 'placement_manager'):
            placement_manager = battle_system.game_scene.placement_manager
            for pokemon in placement_manager.placed_pokemon:
                if pokemon not in all_pokemon_in_field and pokemon.is_alive():
                    all_pokemon_in_field.append(pokemon)

        # Adiciona todos os inimigos selvagens ativos (se houver wave_manager)
        if battle_system.game_scene and hasattr(battle_system.game_scene, 'wave_manager'):
            wave_manager = battle_system.game_scene.wave_manager
            for enemy in wave_manager.active_enemies:
                if enemy not in all_pokemon_in_field and enemy.is_alive():
                    all_pokemon_in_field.append(enemy)

        # Remove modificadores de stat de cada Pokémon
        removed_count = 0
        for pokemon in all_pokemon_in_field:
            pokemon_id = id(pokemon)

            # Remove todos os estágios de stat
            if pokemon_id in effect_manager.stat_stages:
                # Reseta todos os estágios para 0
                for stat_type in list(effect_manager.stat_stages[pokemon_id].stages.keys()):
                    current_stage = effect_manager.stat_stages[pokemon_id].get_stage(stat_type)
                    if current_stage != 0:
                        # Aplica modificação inversa para resetar
                        effect_manager.stat_stages[pokemon_id].modify(stat_type, -current_stage)
                        removed_count += 1

                # Se todos os estágios estão 0, remove o StatStage
                if all(stage == 0 for stage in effect_manager.stat_stages[pokemon_id].stages.values()):
                    del effect_manager.stat_stages[pokemon_id]

            # Remove modificadores temporários (com duração)
            if pokemon_id in effect_manager.stat_modifiers:
                effect_manager.stat_modifiers[pokemon_id].clear()

            # Força atualização da velocidade
            if hasattr(pokemon, 'update_move_speed_from_effects'):
                pokemon.update_move_speed_from_effects()

            # Mostra mensagem para cada Pokémon afetado
            effect_manager.add_status_text(pokemon, f"Os stats de {pokemon.name} voltaram ao normal!", duration=1.5)

        # Mensagem global
        effect_manager.add_status_text(attacker, "Todos os modificadores de stat foram removidos!", duration=2.0)
        print(
            f"[HAZE] {self.name} removeu {removed_count} modificadores de stat de {len(all_pokemon_in_field)} Pokémon!")

        # Toca som (opcional)
        from src.managers.move_sound_manager import move_sound_manager
        move_sound_manager.play_attack_sound("haze")

        return True

    def _apply_dream_eater(self, attacker, target, battle_system, effect_manager, damage):
        """
        Aplica efeito de Dream Eater
        - Só funciona se o alvo estiver dormindo
        - Cura metade do dano causado
        """
        from src.battle.effects import StatusType

        # ===== VERIFICA SE O ALVO ESTÁ DORMINDO =====
        target_status = effect_manager.get_status(target)

        if not target_status or target_status.type != StatusType.SLEEP:
            # Falhou - alvo não está dormindo
            effect_manager.add_status_text(attacker, f"Mas falhou! {target.name} não está dormindo!", duration=1.5)
            print(f"[DREAM_EATER] {attacker.name} tentou usar {self.name}, mas {target.name} não está dormindo!")
            return False

        # ===== APLICA DRENAGEM (cura metade do dano) =====
        drain_percentage = self.params.get("drain_percentage", 0.5)
        drain_amount = int(damage * drain_percentage)

        if drain_amount > 0:
            old_hp = attacker.current_hp
            attacker.current_hp = min(attacker.max_hp, attacker.current_hp + drain_amount)
            actual_heal = attacker.current_hp - old_hp

            effect_manager.add_status_text(attacker, f"{attacker.name} drenou {actual_heal} HP!", duration=1.5)
            print(f"[DREAM_EATER] {attacker.name} recuperou {actual_heal} HP de {target.name}!")

            # Toca som de dreno
            from src.managers.move_sound_manager import move_sound_manager
            move_sound_manager.play_attack_sound("drain")

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

    def _apply_variable_level_damage(self, attacker, target, battle_system, effect_manager):
        """
        Aplica dano variável baseado no nível (Psywave)
        Dano = nível * (50% a 150%, em incrementos de 10%)
        """

        # Obtém os parâmetros
        min_percentage = self.params.get("min_percentage", 0.5)
        max_percentage = self.params.get("max_percentage", 1.5)
        increment = self.params.get("increment", 0.1)
        ignore_type_immunity = self.params.get("ignore_type_immunity", True)
        is_typeless = self.params.get("is_typeless", True)

        # ===== VERIFICA IMUNIDADE DE TIPO (se não for typeless) =====
        if not ignore_type_immunity:
            from src.battle.damage_calculator import DamageCalculator
            effectiveness = DamageCalculator._get_type_effectiveness(
                self.name, target.types
            )
            if effectiveness == 0:
                effect_manager.add_status_text(target, "Não afeta!", duration=1.0)
                print(f"[PSYWAVE] {target.name} é imune!")
                return False

        # ===== CALCULA O DANO =====
        # Número de incrementos possíveis
        # Ex: 0.5 a 1.5 com incremento 0.1 = 11 valores possíveis (50, 60, 70... 150)
        num_increments = int((max_percentage - min_percentage) / increment) + 1

        # Escolhe um índice aleatório
        random_index = random.randint(0, num_increments - 1)

        # Calcula a porcentagem
        percentage = min_percentage + (random_index * increment)

        # Calcula o dano baseado no nível
        damage = int(attacker.level * percentage)

        # Garante dano mínimo de 1
        damage = max(1, damage)

        # ===== MOSTRA A PORCENTAGEM (opcional, para debug) =====
        percentage_display = int(percentage * 100)
        effect_manager.add_status_text(
            attacker,
            f"Poder: {percentage_display}% do nível!",
            duration=0.8
        )

        # ===== APLICA O DANO =====
        target.take_damage(damage, attacker=attacker)

        # Mostra mensagem
        effect_manager.add_status_text(target, f"-{damage} HP", duration=1.0)
        print(f"[PSYWAVE] {attacker.name} causou {damage} de dano ({percentage_display}% do nível) em {target.name}!")

        # Toca som (reutiliza som de psychic)
        from src.managers.move_sound_manager import move_sound_manager
        move_sound_manager.play_attack_sound("psywave")

        return True

    def _apply_percent_damage(self, attacker, target, battle_system, effect_manager):
        """
        Aplica dano baseado em porcentagem do HP (Super Fang)
        """
        damage_percentage = self.params.get("damage_percentage", 0.5)
        damage_formula = self.params.get("damage_formula", "current_hp_percentage")
        min_damage = self.params.get("min_damage", 1)
        ignore_type_immunity = self.params.get("ignore_type_immunity", True)
        ignore_effectiveness = self.params.get("ignore_effectiveness", True)

        # Verifica imunidade de tipo (se não ignorar)
        if not ignore_type_immunity:
            from src.battle.damage_calculator import DamageCalculator
            effectiveness = DamageCalculator._get_type_effectiveness(
                self.name, target.types
            )
            if effectiveness == 0:
                effect_manager.add_status_text(target, "Não afeta!", duration=1.0)
                print(f"[PERCENT_DAMAGE] {target.name} é imune!")
                return False

        # Calcula dano baseado na fórmula
        if damage_formula == "current_hp_percentage":
            damage = int(target.current_hp * damage_percentage)
        elif damage_formula == "max_hp_percentage":
            damage = int(target.max_hp * damage_percentage)
        else:
            damage = int(target.current_hp * 0.5)  # Fallback

        # Garante dano mínimo
        damage = max(min_damage, damage)

        # Aplica dano
        target.take_damage(damage, attacker=attacker)

        # Mostra mensagem
        effect_manager.add_status_text(target, f"-{damage} HP", duration=1.0)
        print(f"[PERCENT_DAMAGE] {attacker.name} cortou {damage} HP de {target.name} com {self.name}!")

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

    def _apply_random_status_chance(self, attacker, target, effect_manager):
        """
        Aplica um status aleatório com uma chance (Tri Attack, Secret Power, etc)
        """
        from .status_effect import StatusEffect, StatusType

        chance = self.params.get("chance", 0.20)
        possible_status = self.params.get("possible_status", [])
        weights = self.params.get("weights", [1] * len(possible_status))
        overwrite = self.params.get("overwrite", False)

        # Verifica se já tem status (se não permitir overwrite)
        existing_status = effect_manager.get_status(target)
        if existing_status and existing_status.type != StatusType.NONE and not overwrite:
            print(f"[RANDOM_STATUS] {target.name} já está com {existing_status.name}, não aplica novo status!")
            return False

        # Tenta aplicar com a chance
        if random.random() >= chance:
            print(f"[RANDOM_STATUS] {self.name} falhou em aplicar status ({chance * 100}% de chance)")
            return False

        # Se não há status possíveis, falha
        if not possible_status:
            return False

        # Escolhe um status aleatório baseado nos pesos
        chosen_status_str = random.choices(possible_status, weights=weights, k=1)[0]

        # Mapeia para StatusType
        status_map = {
            "poison": StatusType.POISON,
            "toxic_poison": StatusType.TOXIC_POISON,
            "burn": StatusType.BURN,
            "paralysis": StatusType.PARALYSIS,
            "sleep": StatusType.SLEEP,
            "freeze": StatusType.FREEZE,
        }

        status_type = status_map.get(chosen_status_str.lower())
        if not status_type:
            return False

        # Mensagem específica para o Tri Attack
        status_names = {
            StatusType.BURN: "queimadura",
            StatusType.FREEZE: "congelamento",
            StatusType.PARALYSIS: "paralisia",
        }
        status_name_pt = status_names.get(status_type, chosen_status_str)

        effect_manager.add_status_text(
            attacker,
            f"{attacker.name} causou {status_name_pt} com {self.name}!",
            duration=1.0
        )

        # Aplica o status
        status = StatusEffect(status_type, duration=None)
        effect_manager.apply_status(target, status, attacker)

        # Registra contribuição
        target.register_status_application(attacker, self.name)

        print(f"[RANDOM_STATUS] {attacker.name} aplicou {status_type.value} em {target.name} com {self.name}!")

        return True

    def _apply_stat_mod_with_visual(self, attacker, target, battle_system, effect_manager):
        """
        Aplica modificador de stat com efeito visual (Minimize)
        """
        from .stat_modifier import StatType

        stats_list = self.params.get("stats", [])
        duration = self.params.get("duration", 8.0)
        visual_effect = self.params.get("visual_effect", None)
        sprite_scale = self.params.get("sprite_scale", 1.0)

        target_entity = target if self.target == EffectTarget.TARGET else attacker

        # Aplica os modificadores de stat
        success_count = 0
        for stat_config in stats_list:
            stat_name = stat_config.get("stat", "attack")
            stages = stat_config.get("stages", 0)

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
                effect_manager.add_stat_modifier(target_entity, stat_type, stages, duration)
                success_count += 1

        # ===== APLICA EFEITO VISUAL =====
        if visual_effect == "minimize" and sprite_scale != 1.0:
            # Armazena o scale original e aplica o novo
            if not hasattr(target_entity, '_original_sprite_scale'):
                target_entity._original_sprite_scale = 1.0
            target_entity._current_sprite_scale = sprite_scale
            target_entity._minimize_active = True
            target_entity._minimize_timer = duration

            # Força atualização do sprite
            if hasattr(target_entity, '_update_sprite_size'):
                target_entity._update_sprite_size()

            effect_manager.add_status_text(target_entity, f"{target_entity.name} ficou minúsculo!", duration=1.5)
            print(f"[MINIMIZE] {target_entity.name} diminuiu de tamanho! (scale: {sprite_scale})")

        if success_count > 0:
            effect_manager.add_status_text(target_entity, f"A Evasão de {target_entity.name} aumentou muito!",
                                           duration=1.5)
            return True

        return False

    def _apply_critical_stage_mod(self, attacker, target, battle_system, effect_manager):
        """
        Aplica modificador de estágio de crítico (Focus Energy)
        """
        from battle.effects.critical_hit import CriticalHitSystem

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
            from battle.effects.critical_hit import CriticalHitSystem
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
        # ===== MÉTODO PARA GOLPES DE 2 TURNOS =====

    def _apply_two_turn_attack(self, attacker, target, battle_system, effect_manager):
        """
        Gerencia o ciclo de golpes de 2 turnos.
        Retorna True se o efeito foi aplicado com sucesso.
        """
        # ===== SEGUNDO TURNO =====
        if (battle_system.active_charge_move and
                battle_system.active_charge_move['attacker'] == attacker and
                battle_system.active_charge_move['move_name'] == self.name):
            print(f"[TWO_TURN] {attacker.name} liberando {self.name}!")
            return True

        # ===== PRIMEIRO TURNO: INICIA A CARGA =====
        # Verifica se o atacante já está carregando outro movimento
        if battle_system.active_charge_move:
            effect_manager.add_status_text(attacker, f"{attacker.name} já está preparando um golpe!", duration=1.0)
            return False

        # Verifica se tem PP
        current_move = attacker.get_current_move()
        if not current_move or current_move.current_pp <= 0:
            return False

        # Gasta PP UMA VEZ
        current_move.current_pp -= 1
        print(
            f"[TWO_TURN] {attacker.name} gastou 1 PP para carregar {self.name} (PP restante: {current_move.current_pp})")

        # Inicia o estado de carga
        battle_system.active_charge_move = {
            'attacker': attacker,
            'move_name': self.name,
            'target': target
        }

        # ===== CONSUME A MENSAGEM DE CARGA DO FACTORY =====
        charge_message = getattr(self, 'charge_message', None)
        if charge_message:
            # Substitui {pokemon} pelo nome do atacante
            formatted_message = charge_message.format(pokemon=attacker.name)
            effect_manager.add_status_text(attacker, formatted_message, duration=1.5)
        else:
            # Mensagem padrão caso não tenha definido
            effect_manager.add_status_text(attacker, f"{attacker.name} está carregando {self.name}!", duration=1.5)

        print(f"[TWO_TURN] {attacker.name} começou a carregar {self.name}")

        # ===== APLICA EFEITOS ADICIONAIS DO PRIMEIRO TURNO =====
        if self.name.lower() == "skull-bash":
            from .stat_modifier import StatType
            effect_manager.add_stat_modifier(attacker, StatType.DEFENSE, 1, duration=6.0)
            effect_manager.add_status_text(attacker, f"Defesa de {attacker.name} aumentou!", duration=1.0)

        return True

    def _execute_area_effect(self, attacker, target, battle_system, effect_manager, damage: int = 0):
        """
        Executa um efeito em área (afeta todos os inimigos no range)
        """
        # ===== PREVINE RECURSÃO =====
        if hasattr(attacker, '_processing_area_effect') and attacker._processing_area_effect:
            print(f"[AREA_EFFECT] {attacker.name} já está processando área, ignorando")
            return False

        attacker._processing_area_effect = True

        try:
            # ===== APLICA COOLDOWN IMEDIATAMENTE =====
            attacker.charge_cooldown = attacker.charge_cooldown_max

            print(f"[AREA_EFFECT] {attacker.name} usou {self.name} em área! (tipo: {self.effect_type})")

            all_targets = []

            if attacker.is_wild:
                # Atacante é selvagem: procura aliados do player (placed_pokemon)
                if hasattr(battle_system.game_scene, 'placement_manager'):
                    placement_manager = battle_system.game_scene.placement_manager
                    all_targets = placement_manager.placed_pokemon.copy()
                    print(f"[AREA_EFFECT] Atacante selvagem: procurando em {len(all_targets)} aliados")
                else:
                    print(f"[AREA_EFFECT] placement_manager não encontrado!")
            else:
                # Atacante é aliado: procura inimigos selvagens (active_enemies)
                if hasattr(battle_system.game_scene, 'wave_manager'):
                    wave_manager = battle_system.game_scene.wave_manager
                    all_targets = wave_manager.active_enemies.copy()
                    print(f"[AREA_EFFECT] Atacante aliado: procurando em {len(all_targets)} inimigos")
                else:
                    print(f"[AREA_EFFECT] wave_manager não encontrado!")

            if not all_targets:
                print(f"[AREA_EFFECT] Nenhum alvo encontrado!")
                effect_manager.add_status_text(attacker, "Mas não há inimigos!", duration=1.0)
                return False

            # Obtém alvos no range
            targets_in_range = attacker.get_enemies_in_range(all_targets)

            print(f"[AREA_EFFECT] Alvos totais: {len(all_targets)}, no range: {len(targets_in_range)}")

            if not targets_in_range:
                effect_manager.add_status_text(attacker, "Mas não há inimigos no alcance!", duration=1.0)
                print(f"[AREA_EFFECT] Nenhum alvo no range de {attacker.name}!")
                return False

            # Obtém o move atual
            current_move = attacker.get_current_move()
            if not current_move:
                print(f"[AREA_EFFECT] {attacker.name} não tem move selecionado!")
                return False

            # Consome PP uma única vez
            if current_move.current_pp > 0:
                current_move.current_pp -= 1
                print(
                    f"[AREA_EFFECT] {attacker.name} gastou 1 PP para {self.name} (atingiu {len(targets_in_range)} alvos)")
            else:
                print(f"[AREA_EFFECT] {attacker.name} não tem PP para {self.name}!")
                return False

            # Toca som do ataque uma vez
            from src.managers.move_sound_manager import move_sound_manager
            move_sound_manager.play_attack_sound(current_move.sound_name)

            # Animação do atacante
            from src.battle.effects.animation_mapper import AnimationMapper
            animation_to_use = AnimationMapper.get_animation_for_move(self.name, current_move.category)
            if attacker.has_animation(animation_to_use):
                attacker.set_animation_direct(animation_to_use)
                attacker.current_frame = 0
                attacker.animation_timer = 0

            # ===== APLICA O EFEITO A CADA ALVO NO RANGE =====
            hit_count = 0

            for target_entity in targets_in_range:
                if not target_entity.is_alive() or target_entity.is_defeated:
                    continue

                print(f"[AREA_EFFECT] Aplicando {self.effect_type} em {target_entity.name}...")

                # ===== DIFERENCIA O TIPO DE EFEITO =====
                if self.effect_type == "self_faint":
                    self._apply_self_faint_area(attacker, target_entity, battle_system, effect_manager, damage)
                    hit_count += 1

                elif self.effect_type == "status" or self.effect_type == "status_chance":
                    success = self._apply_status(attacker, target_entity, effect_manager)
                    if success:
                        hit_count += 1

                elif self.effect_type == "stat_mod":
                    # Para golpes como Sand Attack em área
                    success = self._apply_stat_mod(attacker, target_entity, effect_manager)
                    if success:
                        hit_count += 1
                        print(f"[AREA_EFFECT] stat_mod aplicado com sucesso em {target_entity.name}")

                elif self.effect_type == "drain":
                    success = self._apply_drain(attacker, target_entity, damage, effect_manager)
                    if success:
                        hit_count += 1

                elif self.effect_type == "recoil":
                    success = self._apply_recoil(attacker, target_entity, damage, effect_manager)
                    if success:
                        hit_count += 1

                elif self.effect_type == "percent_damage":
                    success = self._apply_percent_damage(attacker, target_entity, battle_system, effect_manager)
                    if success:
                        hit_count += 1

                elif self.effect_type == "fixed_damage":
                    success = self._apply_fixed_damage(attacker, target_entity, battle_system, effect_manager)
                    if success:
                        hit_count += 1

                elif self.effect_type == "level_damage":
                    success = self._apply_level_damage(attacker, target_entity, battle_system, effect_manager)
                    if success:
                        hit_count += 1

                elif self.effect_type == "area_damage" or self.params.get("use_normal_damage", False):
                    from src.battle.damage_calculator import DamageCalculator

                    damage_result = DamageCalculator.calculate_damage(attacker, target_entity, current_move)

                    if damage_result["hit"]:
                        old_hp = target_entity.current_hp
                        target_entity.take_damage(damage_result["damage"], attacker=attacker)
                        actual_damage = old_hp - target_entity.current_hp

                        effect_manager.add_status_text(target_entity, f"-{actual_damage} HP", duration=0.8)

                        if damage_result["effectiveness"] > 1.0:
                            effect_manager.add_status_text(target_entity, "Super efetivo!", duration=0.8)
                        elif 0 < damage_result["effectiveness"] < 1.0:
                            effect_manager.add_status_text(target_entity, "Não é muito efetivo...", duration=0.8)

                        # ===== CORREÇÃO CRÍTICA: NÃO CHAMA _apply_move_effect PARA ATAQUES EM ÁREA =====
                        # Isso evita recursão e duplicação de PP
                        # battle_system._apply_move_effect(attacker, target_entity, current_move, damage_result["damage"])

                        move_sound_manager.play_hit_sound(current_move.sound_name)

                        hit_count += 1
                        print(f"[AREA_DAMAGE] {self.name} causou {actual_damage} de dano em {target_entity.name}!")

            # Reseta estado de combate (cooldown já foi aplicado no início)
            if not attacker.is_wild:
                attacker.combat_state = "returning"
                if attacker.has_animation("walk"):
                    attacker.set_animation("walk")
            else:
                attacker.combat_state = "attacking"

            return hit_count > 0

        finally:
            # ===== LIMPA A FLAG =====
            attacker._processing_area_effect = False

    def _apply_self_confusion_after_uses(self, attacker, target, battle_system, effect_manager, damage):
        """
        Aplica confusão no usuário após usar o golpe X vezes.
        Simplificado: conta usos no próprio Pokémon.
        """
        required_uses = self.params.get("required_uses", 3)
        reset_on_switch = self.params.get("reset_on_switch", True)

        # Inicializa contador se não existir
        if not hasattr(attacker, '_move_use_counter'):
            attacker._move_use_counter = {}

        move_name = self.name.lower()

        # Incrementa contador para este move
        current_uses = attacker._move_use_counter.get(move_name, 0) + 1
        attacker._move_use_counter[move_name] = current_uses

        print(f"[{self.name.upper()}] {attacker.name} usou {current_uses}/{required_uses} vezes")

        # Verifica se atingiu o limite
        if current_uses >= required_uses:
            # Reseta contador
            attacker._move_use_counter[move_name] = 0

            # Verifica se o Pokémon já não está com algum status que impede
            status = effect_manager.get_status(attacker)
            from src.battle.effects import StatusType
            if status and status.type in [StatusType.SLEEP, StatusType.FREEZE]:
                effect_manager.add_status_text(
                    attacker,
                    f"{attacker.name} está {status.name.lower()} e não ficou confuso!",
                    duration=1.0
                )
                return True

            # Aplica confusão
            effect_manager.apply_confusion(attacker, source=attacker)
            effect_manager.add_status_text(
                attacker,
                f"{attacker.name} ficou confuso devido ao esforço!",
                duration=1.5
            )
            print(f"[{self.name.upper()}] {attacker.name} ficou confuso após {required_uses} usos!")

        return True

    def _apply_light_screen(self, attacker, target, battle_system, effect_manager):
        """Aplica Light Screen - reduz dano de ataques especiais por X golpes"""
        return self._apply_screen(attacker, battle_system, effect_manager, "light_screen")

    def _apply_reflect(self, attacker, target, battle_system, effect_manager):
        """Aplica Reflect - reduz dano de ataques físicos por X golpes"""
        return self._apply_screen(attacker, battle_system, effect_manager, "reflect")

    def _apply_screen(self, attacker, battle_system, effect_manager, screen_type):
        """Aplica screen baseado em contagem de golpes"""

        # Verifica se já tem screen ativo
        if hasattr(battle_system, 'active_screens'):
            team_key = f"{'wild' if attacker.is_wild else 'ally'}_{screen_type}"
            if team_key in battle_system.active_screens:
                effect_manager.add_status_text(attacker, f"Mas já está ativo!", duration=1.0)
                print(f"[SCREEN] {attacker.name} já tem {screen_type} ativo!")
                return False

        # Obtém parâmetros
        turns = self.params.get("turns", 5)
        damage_reduction = self.params.get("damage_reduction", 0.5)
        affected_attacks = self.params.get("affected_attacks", ["special"])

        # Inicializa sistema de screens se não existir
        if not hasattr(battle_system, 'active_screens'):
            battle_system.active_screens = {}

        # Ativa o screen
        team_key = f"{'wild' if attacker.is_wild else 'ally'}_{screen_type}"
        battle_system.active_screens[team_key] = {
            'turns_remaining': turns,
            'max_turns': turns,
            'reduction': damage_reduction,
            'affected_attacks': affected_attacks,
            'pokemon': attacker,
            'screen_type': screen_type
        }

        # Mostra mensagem
        screen_names = {
            "light_screen": "Light Screen",
            "reflect": "Reflect"
        }
        screen_display = screen_names.get(screen_type, screen_type)

        effect_manager.add_status_text(
            attacker,
            f"{attacker.name} usou {screen_display}!",
            duration=1.5
        )
        effect_manager.add_status_text(
            attacker,
            f"Proteção por {turns} golpes!",
            duration=1.5
        )

        print(f"[SCREEN] {attacker.name} ativou {screen_display} por {turns} turns!")

        return True

    def _decrement_screen_turns(self, battle_system, defending_pokemon, move_category):
        """
        Decrementa os turns dos screens quando o Pokémon defensor é atingido
        Retorna a redução de dano aplicável
        """
        if not hasattr(battle_system, 'active_screens'):
            return 1.0

        reduction = 1.0
        screens_to_remove = []

        for key, screen in battle_system.active_screens.items():
            # Verifica se este screen afeta o Pokémon defensor
            # (screen do mesmo lado que o defensor)
            is_ally_screen = (not defending_pokemon.is_wild and key.startswith("ally_"))
            is_wild_screen = (defending_pokemon.is_wild and key.startswith("wild_"))

            if (is_ally_screen or is_wild_screen) and move_category in screen['affected_attacks']:
                # Aplica redução de dano
                reduction = min(reduction, screen['reduction'])

                # Decrementa os turns restantes
                screen['turns_remaining'] -= 1

                print(f"[SCREEN] {screen['screen_type']} ativo! Turns restantes: {screen['turns_remaining']}")

                # Marca para remover se acabou
                if screen['turns_remaining'] <= 0:
                    screens_to_remove.append(key)
                    pokemon = screen.get('pokemon')
                    if pokemon and pokemon.is_alive():
                        screen_name = "Light Screen" if "light_screen" in key else "Reflect"
                        battle_system.effect_manager.add_status_text(
                            pokemon,
                            f"{screen_name} de {pokemon.name} acabou!",
                            duration=1.5
                        )
                    print(f"[SCREEN] {key} expirou!")

        # Remove screens expirados
        for key in screens_to_remove:
            del battle_system.active_screens[key]

        return reduction

    def _apply_counter(self, attacker, target, battle_system, effect_manager):
        """
        Aplica Counter - retorna o dobro do dano físico recebido no último golpe
        """
        # Verifica se o atacante foi atingido por um ataque físico
        if not hasattr(attacker, '_last_physical_damage_received') or attacker._last_physical_damage_received <= 0:
            effect_manager.add_status_text(attacker, f"Mas falhou!", duration=1.0)
            print(f"[COUNTER] {attacker.name} não foi atingido por um ataque físico!")
            return False

        # Verifica se tem registro de quem atacou
        if not hasattr(attacker, '_last_physical_attacker') or not attacker._last_physical_attacker:
            effect_manager.add_status_text(attacker, f"Mas falhou!", duration=1.0)
            return False

        counter_target = attacker._last_physical_attacker

        # Verifica se o alvo ainda está vivo
        if not counter_target.is_alive() or counter_target.is_defeated:
            effect_manager.add_status_text(attacker, f"Mas o alvo já foi derrotado!", duration=1.0)
            return False

        # Calcula dano de retorno (dobro)
        multiplier = self.params.get("multiplier", 2.0)
        counter_damage = int(attacker._last_physical_damage_received * multiplier)

        # Garante dano mínimo de 1
        counter_damage = max(1, counter_damage)

        # Aplica dano ao alvo
        old_hp = counter_target.current_hp
        counter_target.take_damage(counter_damage, attacker=attacker)
        actual_damage = old_hp - counter_target.current_hp

        # Mostra mensagens
        effect_manager.add_status_text(
            attacker,
            f"{attacker.name} revidou com Counter!",
            duration=1.5
        )
        effect_manager.add_status_text(
            counter_target,
            f"-{actual_damage} HP",
            duration=1.0
        )

        print(f"[COUNTER] {attacker.name} causou {actual_damage} de dano de retorno a {counter_target.name}!")

        # Toca som
        from src.managers.move_sound_manager import move_sound_manager
        move_sound_manager.play_attack_sound("counter")

        # Limpa o registro após usar
        attacker._last_physical_damage_received = 0
        attacker._last_physical_attacker = None

        return True

    def _apply_disable(self, attacker, target, battle_system, effect_manager, damage):
        """
        Aplica efeito Disable - desabilita o último movimento usado pelo alvo

        Funcionamento:
        - Rastreia o último movimento usado pelo alvo
        - Impede o uso desse movimento por X turnos
        - Se o alvo não usou nenhum movimento, falha
        """
        duration = self.params.get("duration", 4)

        # ===== VERIFICA SE O ALVO JÁ ESTÁ COM MOVE DESABILITADO =====
        if hasattr(target, '_disabled_move') and target._disabled_move:
            effect_manager.add_status_text(
                target,
                f"Mas já está desabilitado!",
                duration=1.0
            )
            print(f"[DISABLE] {target.name} já tem um move desabilitado!")
            return False

        # ===== VERIFICA SE O ALVO USOU ALGUM MOVE =====
        if not hasattr(target, '_last_used_move') or not target._last_used_move:
            effect_manager.add_status_text(
                attacker,
                f"Mas falhou!",
                duration=1.0
            )
            print(f"[DISABLE] {target.name} não usou nenhum movimento ainda!")
            return False

        last_move_name = target._last_used_move

        # ===== VERIFICA SE O MOVE AINDA TEM PP =====
        last_move = None
        for move in target.moves:
            if move.name == last_move_name:
                last_move = move
                break

        if last_move and last_move.current_pp <= 0:
            effect_manager.add_status_text(
                attacker,
                f"Mas falhou!",
                duration=1.0
            )
            print(f"[DISABLE] {last_move_name} de {target.name} já está sem PP!")
            return False

        # ===== APLICA DISABLE =====
        target._disabled_move = last_move_name
        target._disabled_turns = duration
        target._disabled_original_pp = last_move.current_pp if last_move else 0

        # Mostra mensagem
        effect_manager.add_status_text(
            attacker,
            f"{target.name} não pode mais usar {last_move_name}!",
            duration=1.5
        )
        effect_manager.add_status_text(
            target,
            f"{last_move_name} foi desabilitado!",
            duration=1.5
        )

        print(f"[DISABLE] {attacker.name} desabilitou {last_move_name} de {target.name} por {duration} turnos!")

        return True

    def _apply_pay_day(self, attacker, target, battle_system, effect_manager, damage):
        """
        Aplica efeito Pay Day - marca o alvo para dar mais recompensas quando derrotado

        Só funciona se:
        - Atacante é aliado (not wild)
        - Alvo é inimigo (wild)
        """
        # ===== VERIFICA SE É ALIADO USANDO O GOLPE =====
        if attacker.is_wild:
            # Inimigos não ganham bônus
            print(f"[PAY_DAY] Inimigos não podem usar Pay Day para bônus!")
            return True

        # Verifica se o alvo é inimigo
        if not target.is_wild:
            print(f"[PAY_DAY] Pay Day só funciona contra inimigos!")
            return True

        gold_multiplier = self.params.get("gold_multiplier", 2.0)
        xp_multiplier = self.params.get("xp_multiplier", 1.5)

        # Verifica se o alvo já está morto
        if target.is_defeated or not target.is_alive():
            print(f"[PAY_DAY] {target.name} já está derrotado, Pay Day não teve efeito!")
            return False

        # Marca o alvo (acumula multiplicador a cada hit)
        if not hasattr(target, '_pay_day_hit_count'):
            target._pay_day_hit_count = 0
            target._pay_day_gold_multiplier = 1.0
            target._pay_day_xp_multiplier = 1.0

        # Incrementa contador
        target._pay_day_hit_count += 1

        # Calcula multiplicadores (diminishing returns)
        # 1 hit: 2.0x gold, 1.5x XP
        # 2 hits: 2.5x gold, 1.8x XP
        # 3 hits: 2.8x gold, 2.0x XP
        # Máximo: 3.0x gold, 2.5x XP
        gold_mult = min(3.0, 1.0 + (gold_multiplier - 1.0) * (1 - 0.5 ** target._pay_day_hit_count))
        xp_mult = min(2.5, 1.0 + (xp_multiplier - 1.0) * (1 - 0.5 ** target._pay_day_hit_count))

        target._pay_day_gold_multiplier = gold_mult
        target._pay_day_xp_multiplier = xp_mult
        target._pay_day_hit = True

        # Mostra mensagem visual
        effect_manager.add_status_text(
            attacker,
            f"💰 Moedas! (x{gold_mult:.1f})",
            duration=0.8
        )

        effect_manager.add_status_text(
            target,
            f"💰 Marcado!",
            duration=1.0
        )

        print(
            f"[PAY_DAY] {attacker.name} usou Pay Day em {target.name}! Multiplicadores: Gold x{gold_mult:.1f}, XP x{xp_mult:.1f} (hit #{target._pay_day_hit_count})")

        return True

    def _apply_metronome(self, attacker, target, battle_system, effect_manager):
        """
        Metronome - Usa um movimento aleatório.
        Simplificado para Gen 1: escolhe qualquer move aleatório da lista de moves disponíveis.
        """
        from src.data.move_data import MoveData
        from src.entities.move import Move
        import random

        move_data = MoveData()

        # Lista de todos os moves disponíveis (excluindo alguns problemáticos)
        all_moves = move_data.get_all_move_names()

        # Moves que NÃO devem ser escolhidos pelo Metronome (Gen 1)
        excluded_moves = self.params.get("exclude_moves", [
            "metronome", "mimic", "struggle", "transform",
            "counter", "mirror-coat", "protect", "detect", "endure"
        ])

        # Filtra moves válidos
        valid_moves = [m for m in all_moves if m not in excluded_moves]

        if not valid_moves:
            effect_manager.add_status_text(attacker, f"Mas falhou!", duration=1.0)
            return False

        # Escolhe um move aleatório
        chosen_move_name = random.choice(valid_moves)
        move_info = move_data.get_move_info(chosen_move_name)

        if not move_info:
            effect_manager.add_status_text(attacker, f"Mas falhou!", duration=1.0)
            return False

        # Cria o move temporário
        temp_move = Move(chosen_move_name, move_info)
        temp_move.current_pp = 1  # PP temporário

        # Mostra a mensagem
        effect_manager.add_status_text(
            attacker,
            f"Metronome: {chosen_move_name.upper()}!",
            duration=1.5
        )

        print(f"[METRONOME] {attacker.name} usou {chosen_move_name}!")

        # Determina se o move acerta ou não (accuracy padrão)
        hit_chance = temp_move.accuracy / 100 if temp_move.accuracy else 1.0
        import random
        will_hit = random.random() <= hit_chance

        # Executa o move de acordo com sua categoria
        if temp_move.category == "status":
            # Move de status - aplica efeito
            from .effect_factory import EffectFactory
            effect = EffectFactory.create_effect(temp_move.name)
            if effect:
                effect.execute(attacker, target, battle_system, effect_manager)
            else:
                effect_manager.add_status_text(target, f"{attacker.name} usou {temp_move.name}!", duration=1.0)

        elif temp_move.power and temp_move.power > 0:
            # Move de dano
            if will_hit:
                from src.battle.damage_calculator import DamageCalculator
                damage_result = DamageCalculator.calculate_damage(attacker, target, temp_move)

                if damage_result["hit"]:
                    # Aplica dano
                    target.take_damage(damage_result["damage"], attacker=attacker)
                    effect_manager.add_status_text(target, f"-{damage_result['damage']} HP", duration=0.8)

                    if damage_result["effectiveness"] > 1.0:
                        effect_manager.add_status_text(target, "Super efetivo!", duration=0.8)
                    elif 0 < damage_result["effectiveness"] < 1.0:
                        effect_manager.add_status_text(target, "Não é muito efetivo...", duration=0.8)

                    # Aplica efeitos do move (se houver)
                    from .effect_factory import EffectFactory
                    effect = EffectFactory.create_effect(temp_move.name)
                    if effect and effect.timing in [EffectTiming.AFTER_DAMAGE, EffectTiming.ON_HIT]:
                        effect.execute(attacker, target, battle_system, effect_manager, damage_result["damage"])

                    # Toca som
                    from src.managers.move_sound_manager import move_sound_manager
                    move_sound_manager.play_attack_sound(temp_move.sound_name)
                    move_sound_manager.play_hit_sound(temp_move.sound_name)
                else:
                    effect_manager.add_status_text(attacker, f"{temp_move.name} errou!", duration=0.8)
            else:
                effect_manager.add_status_text(attacker, f"{temp_move.name} errou!", duration=0.8)

        # Cooldown do ataque
        attacker.attack_cooldown = max(0.3, 1.0 - (attacker.speed_stat / 500))

        return True

    def _apply_mimic(self, attacker, target, battle_system, effect_manager):
        """
        Mimic - Copia o último movimento usado pelo alvo.
        Simplificado para Gen 1: substitui o move Mimic pelo move copiado.
        """
        from src.entities.move import Move

        # Verifica se o alvo usou algum movimento
        if not hasattr(target, '_last_used_move') or not target._last_used_move:
            effect_manager.add_status_text(attacker, f"Mas falhou! {target.name} não usou nenhum movimento!",
                                           duration=1.5)
            print(f"[MIMIC] {attacker.name} tentou copiar, mas {target.name} não usou nenhum movimento!")
            return False

        move_to_copy = target._last_used_move

        # Verifica se é um movimento que não pode ser copiado
        cannot_copy = ["metronome", "mimic", "struggle", "transform", "counter"]
        if move_to_copy.lower() in cannot_copy:
            effect_manager.add_status_text(attacker, f"Mas não conseguiu copiar {move_to_copy}!", duration=1.5)
            print(f"[MIMIC] {attacker.name} não pode copiar {move_to_copy}!")
            return False

        # Obtém as informações do move
        from src.data.move_data import MoveData
        move_data = MoveData()
        move_info = move_data.get_move_info(move_to_copy)

        if not move_info:
            effect_manager.add_status_text(attacker, f"Mas falhou!", duration=1.0)
            return False

        # Encontra o move Mimic no moveset do atacante
        mimic_index = None
        for i, move in enumerate(attacker.moves):
            if move.name.lower() == "mimic":
                mimic_index = i
                break

        if mimic_index is None:
            print(f"[MIMIC] {attacker.name} não tem Mimic no moveset!")
            return False

        # Substitui o Mimic pelo move copiado
        new_move = Move(move_to_copy, move_info)
        new_move.current_pp = self.params.get("pp_on_copy", 5)  # PP padrão ao copiar
        new_move.max_pp = move_info.get("pp", 5)

        old_move_name = attacker.moves[mimic_index].name
        attacker.moves[mimic_index] = new_move

        # Mostra mensagem
        effect_manager.add_status_text(
            attacker,
            f"{attacker.name} aprendeu {move_to_copy.upper()}!",
            duration=2.0
        )

        print(f"[MIMIC] {attacker.name} copiou {move_to_copy} de {target.name}!")
        print(f"[MIMIC] {old_move_name} foi substituído por {move_to_copy}!")

        return True

    # ===== MÉTODOS DE TRANSFORM (DITTO) =====

    def _apply_transform(self, attacker, target, battle_system, effect_manager):
        """
        Aplica o efeito Transform do Ditto.
        Copia aparência, moves e stats base do oponente, mas mantém IVs/EVs próprios.
        """
        from src.entities.move import Move

        # ===== VERIFICA SE O ALVO É VÁLIDO =====
        if not target or target.is_defeated or not target.is_alive():
            effect_manager.add_status_text(attacker, f"Mas falhou!", duration=1.0)
            print(f"[TRANSFORM] {attacker.name} tentou se transformar, mas falhou!")
            return False

        # Verifica se o Ditto já está transformado
        if hasattr(attacker, '_is_transformed') and attacker._is_transformed:
            effect_manager.add_status_text(attacker, f"{attacker.name} já está transformado!", duration=1.0)
            return False

        # ===== SALVA O ESTADO ORIGINAL DO DITTO =====

        attacker._original_id = attacker.id
        attacker._original_name = attacker.name
        attacker._original_types = attacker.types.copy()
        attacker._original_moves = [move for move in attacker.moves]  # Cópia profunda
        attacker._original_base_stats = attacker.base_stats.copy()

        # ===== SALVA OS STATS ORIGINAIS DO DITTO =====
        attacker._original_max_hp = attacker.max_hp
        attacker._original_attack = attacker.attack
        attacker._original_defense = attacker.defense
        attacker._original_sp_attack = attacker.sp_attack
        attacker._original_sp_defense = attacker.sp_defense
        attacker._original_speed = attacker.speed_stat

        # Salva os sprites originais
        attacker._original_sprite_data = {
            "ui_sprite": attacker.ui_sprite,
            "battle_sprite": attacker.battle_sprite,
            "inmap_frames": attacker.inmap_frames,
            "inmap_animations": attacker.inmap_animations.copy() if attacker.inmap_animations else {},
            "available_animations": attacker.animation.get_available_animations().copy()
        }

        # Guarda também os IVs e EVs (não mudam, mas salvamos para debug)
        attacker._original_ivs = attacker.ivs.copy()
        attacker._original_evs = attacker.evs.copy()

        # ===== COPIA OS DADOS DO OPONENTE =====
        # 1. ID (apenas para referência, o id real continua o mesmo)
        attacker._transformed_id = target.id
        attacker._transformed_name = target.name

        # 2. Tipos
        if self.params.get("copy_types", True):
            attacker.types = target.types.copy()

        # 3. Stats base (para cálculos futuros)
        if self.params.get("copy_stats", True):
            attacker.base_stats = target.base_stats.copy()

        # 4. Moves
        if self.params.get("copy_moves", True):
            # Salva os moves originais
            attacker._original_moves_list = attacker.moves.copy()

            # Cria cópias dos moves do oponente
            new_moves = []
            for move in target.moves:
                new_move = Move(move.name, {
                    "type": move.type,
                    "power": move.power,
                    "accuracy": move.accuracy,
                    "pp": move.max_pp,
                    "max_pp": move.max_pp,
                    "category": move.category,
                    "description": move.description
                })
                new_move.current_pp = move.max_pp
                new_moves.append(new_move)

            attacker.moves = new_moves

            # Garante que Transform ainda está disponível (como primeiro move)
            transform_exists = any(m.name.lower() == "transform" for m in attacker.moves)
            if not transform_exists:
                from src.data.move_data import MoveData
                move_data = MoveData()
                transform_info = move_data.get_move_info("transform")
                if transform_info:
                    transform_move = Move("transform", transform_info)
                    transform_move.current_pp = transform_move.max_pp
                    attacker.moves.insert(0, transform_move)

        # 5. Sprite e animações (usa o sistema da Pokedex)
        if self.params.get("copy_sprite", True):
            self._copy_sprites_via_pokedex(attacker, target, battle_system)

        # 6. Recalcula stats com os novos base_stats mas usando IVs/EVs do Ditto
        attacker._is_transformed = True
        attacker._transformed_target = target

        # Força recálculo dos stats usando o stats manager
        attacker.stats.calculate_stats()

        # ===== AJUSTE ESPECIAL: HP NÃO É COPIADO! =====
        if attacker.current_hp > attacker.max_hp:
            attacker.current_hp = attacker.max_hp

        # ===== ATUALIZA ANIMAÇÃO =====
        if hasattr(attacker, 'animation'):
            # Recarrega os sprites para a nova forma
            attacker.animation.load_sprites(target.id, target.is_shiny)

        # ===== MENSAGEM E FEEDBACK =====
        effect_manager.add_status_text(attacker, f"{attacker.name} se transformou em {target.name}!", duration=2.0)
        print(f"[TRANSFORM] {attacker.name} (Ditto) se transformou em {target.name}!")
        print(f"[TRANSFORM] Stats recalculados: HP={attacker.max_hp}, ATK={attacker.attack}, DEF={attacker.defense}")
        print(f"[TRANSFORM] Moves copiados: {[m.name for m in attacker.moves]}")

        # Registra contribuição para XP
        if hasattr(target, 'register_status_application'):
            target.register_status_application(attacker, "Transform")

        # Toca som
        from src.managers.move_sound_manager import move_sound_manager
        move_sound_manager.play_attack_sound("transform")

        return True

    def _copy_sprites_via_pokedex(self, attacker, target, battle_system):
        """
        Copia os sprites do alvo usando o sistema da Pokedex.
        Isso garante compatibilidade com seu sistema de animações.
        """
        pokedex = target.pokedex

        # Copia os sprites principais
        attacker.ui_sprite = target.ui_sprite
        attacker.battle_sprite = target.battle_sprite

        # Usa o sistema da Pokedex para carregar as animações InMap do alvo
        # Mas com os parâmetros do atacante (shiny, etc)
        attacker.inmap_frames = pokedex.get_inmap_animation(target.id, attacker.is_shiny)

        # Copia as informações de animações
        anim_info = pokedex.get_pokemon_animations_info(target.id, attacker.is_shiny)
        attacker._transformed_available_animations = anim_info.get("available_animations", []).copy()

        # Copia os dados brutos de animação
        if hasattr(pokedex, 'get_raw_inmap_data'):
            attacker.raw_animations = pokedex.get_raw_inmap_data(target.id, attacker.is_shiny)
            attacker.inmap_animations = attacker.raw_animations.get("animations", {})

        # Força atualização do sprite atual
        if attacker.inmap_frames and attacker.current_direction in attacker.inmap_frames:
            frames = attacker.inmap_frames[attacker.current_direction]
            if frames:
                attacker.sprite = frames[0]

        # Atualiza o tamanho do sprite
        attacker.map_sprite_size = pokedex.get_map_sprite_size(target.id, attacker.is_shiny)

    # ===== MÉTODOS DE MIST =====
    def _apply_mist(self, attacker, target, battle_system, effect_manager, damage):
        """
        Aplica efeito Mist - limpa todos os debuffs dos aliados em área

        Funcionamento:
        - Remove TODOS os debuffs (modificadores negativos) dos aliados próximos
        - Afeta em área (todos aliados no range)
        - Não tem duração, é efeito instantâneo
        """

        # Obtém todos os aliados no range
        allies_in_range = self._get_allies_in_area(attacker, battle_system)

        if not allies_in_range:
            effect_manager.add_status_text(attacker, f"Mas não há aliados por perto!", duration=1.0)
            return False

        # Limpa debuffs de cada aliado
        cleared_count = 0

        for ally in allies_in_range:
            cleared = self._clear_all_negative_stats(ally, effect_manager)
            if cleared > 0:
                cleared_count += cleared
                effect_manager.add_status_text(
                    ally,
                    f"Névoa purificadora limpou os debuffs de {ally.name}!",
                    duration=1.0
                )

        if cleared_count > 0:
            effect_manager.add_status_text(
                attacker,
                f"A névoa purificou {cleared_count} debuff(s) dos aliados!",
                duration=1.5
            )
            print(
                f"[MIST] {attacker.name} usou Mist e limpou {cleared_count} debuffs de {len(allies_in_range)} aliados!")
        else:
            effect_manager.add_status_text(
                attacker,
                f"Mas nada aconteceu!",
                duration=1.0
            )
            print(f"[MIST] {attacker.name} usou Mist, mas ninguém tinha debuffs!")

        return True

    def _get_allies_in_area(self, attacker, battle_system):
        """
        Retorna todos os aliados (incluindo o atacante) dentro do range da névoa
        """
        allies = []

        if not battle_system.game_scene:
            return [attacker]

        if not hasattr(battle_system.game_scene, 'placement_manager'):
            return [attacker]

        placement_manager = battle_system.game_scene.placement_manager
        mist_range = 150  # Raio da névoa (ajustável)

        for pokemon in placement_manager.placed_pokemon:
            # Verifica se é aliado (não selvagem) e está vivo
            if pokemon.is_wild:
                continue
            if not pokemon.is_alive() or pokemon.is_defeated:
                continue

            # Calcula distância
            dx = pokemon.x - attacker.x
            dy = pokemon.y - attacker.y
            distance = math.sqrt(dx * dx + dy * dy)

            if distance <= mist_range:
                allies.append(pokemon)

        # Sempre inclui o próprio atacante se não estiver na lista e estiver vivo
        if attacker not in allies and attacker.is_alive() and not attacker.is_wild:
            allies.append(attacker)

        return allies

    def _clear_all_negative_stats(self, pokemon, effect_manager):
        """
        Remove todos os debuffs (modificadores negativos de stat) do Pokémon
        Retorna a quantidade de debuffs removidos
        """
        from src.battle.effects.stat_modifier import StatType

        pokemon_id = id(pokemon)

        if pokemon_id not in effect_manager.stat_stages:
            return 0

        cleared_count = 0

        # Lista de stats que podem ser afetados
        for stat_type in [StatType.ATTACK, StatType.DEFENSE, StatType.SP_ATTACK,
                          StatType.SP_DEFENSE, StatType.SPEED, StatType.ACCURACY,
                          StatType.EVASION]:

            current_stage = effect_manager.stat_stages[pokemon_id].get_stage(stat_type)

            # Se tem debuff (estágio negativo), remove
            if current_stage < 0:
                # Aplica modificação positiva para cancelar o debuff
                effect_manager.stat_stages[pokemon_id].modify(stat_type, -current_stage)
                cleared_count += 1
                print(f"[MIST] {pokemon.name}: {stat_type.value} {current_stage:+d} -> 0")

        # Se todos os estágios estão 0, remove o StatStage
        if cleared_count > 0:
            all_zero = all(stage == 0 for stage in effect_manager.stat_stages[pokemon_id].stages.values())
            if all_zero:
                del effect_manager.stat_stages[pokemon_id]

        return cleared_count

    # ===== MÉTODOS DE RAGE =====
    def _apply_rage_mode(self, attacker, target, effect_manager):
        """Aplica o efeito Rage - aumenta Attack quando atingido"""

        # Verifica se já está em modo Rage
        if hasattr(attacker, '_rage_active') and attacker._rage_active:
            effect_manager.add_status_text(attacker, f"{attacker.name} já está em fúria!", duration=1.0)
            return False

        # Ativa o modo Rage
        attacker._rage_active = True
        attacker._rage_stage_increase = self.params.get("stages_per_hit", 1)
        attacker._rage_max_stages = self.params.get("max_stages", 6)

        # Registra o callback para ser chamado quando o Pokémon for atingido
        attacker._rage_callback = lambda pokemon, damage: self._on_rage_hit(
            pokemon, damage, effect_manager
        )

        effect_manager.add_status_text(attacker, f"{attacker.name} entrou em fúria!", duration=1.5)
        print(f"[RAGE] {attacker.name} agora aumenta Ataque quando atingido!")

        return True

    def _on_rage_hit(self, pokemon, damage, effect_manager):
        """Callback chamado quando o Pokémon em Rage é atingido"""
        from .stat_modifier import StatType

        # Verifica se ainda está em Rage
        if not hasattr(pokemon, '_rage_active') or not pokemon._rage_active:
            return

        # Obtém estágio atual
        current_stage = 0
        if hasattr(pokemon, 'effect_manager') and pokemon.effect_manager:
            pokemon_id = id(pokemon)
            if pokemon_id in pokemon.effect_manager.stat_stages:
                current_stage = pokemon.effect_manager.stat_stages[pokemon_id].get_stage(StatType.ATTACK)

        # Verifica se já atingiu o máximo
        if current_stage >= pokemon._rage_max_stages:
            print(f"[RAGE] {pokemon.name} já atingiu o máximo de Ataque!")
            return

        # Aumenta o Attack
        stages = pokemon._rage_stage_increase
        pokemon.effect_manager.add_stat_modifier(pokemon, StatType.ATTACK, stages, duration=6.0)

        effect_manager.add_status_text(pokemon, f"Ataque de {pokemon.name} aumentou pela fúria!", duration=1.0)
        print(f"[RAGE] {pokemon.name} foi atingido! Ataque +{stages}!")

    def _clear_rage_mode(self, pokemon):
        """Limpa o modo Rage (quando o Pokémon ataca ou a batalha termina)"""
        if hasattr(pokemon, '_rage_active'):
            pokemon._rage_active = False
            pokemon._rage_callback = None
            print(f"[RAGE] Modo fúria de {pokemon.name} terminou!")

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

    def _apply_teleport_swap(self, attacker, target, battle_system, effect_manager):
        """
        Aplica o efeito do Teleport:
        - Teleporta para um spot livre aleatório
        - 20% de chance de trocar de lugar com um aliado se houver
        """

        # Verifica se o atacante está colocado no mapa
        if not hasattr(attacker, 'is_placed') or not attacker.is_placed:
            effect_manager.add_status_text(attacker, f"Mas falhou!", duration=1.0)
            print(f"[TELEPORT] {attacker.name} não está no mapa!")
            return False

        # Obtém o placement_manager
        if not battle_system.game_scene or not hasattr(battle_system.game_scene, 'placement_manager'):
            effect_manager.add_status_text(attacker, f"Mas falhou!", duration=1.0)
            print(f"[TELEPORT] PlacementManager não encontrado!")
            return False

        placement_manager = battle_system.game_scene.placement_manager
        spot_renderer = battle_system.game_scene.spot_renderer

        # Obtém todos os spots
        all_spots = spot_renderer.get_spots()
        if not all_spots:
            effect_manager.add_status_text(attacker, f"Mas falhou!", duration=1.0)
            return False

        # ===== VERIFICA A CHANCE DE TROCA COM ALIADO (20%) =====
        swap_chance = self.params.get("swap_chance", 0.20)
        will_swap = random.random() < swap_chance

        if will_swap:
            # Tenta trocar com um aliado
            swapped = self._try_swap_with_ally(attacker, placement_manager, effect_manager)
            if swapped:
                return True

        # ===== TELEPORT NORMAL: Encontra um spot livre aleatório =====
        # Filtra spots livres (não ocupados)
        free_spots = [spot for spot in all_spots if not spot.occupied]

        if not free_spots:
            # Não tem spot livre - TELEPORT ERRA
            effect_manager.add_status_text(attacker,
                                           f"{attacker.name} usou Teleport, mas não encontrou um local seguro!",
                                           duration=1.5)
            print(f"[TELEPORT] {attacker.name} falhou! Nenhum spot livre disponível!")
            return False

        # Escolhe um spot livre aleatório
        target_spot = random.choice(free_spots)

        # Realiza o teleport
        return self._perform_teleport(attacker, target_spot, placement_manager, effect_manager)

    def _try_swap_with_ally(self, attacker, placement_manager, effect_manager):
        """
        Tenta trocar de lugar com um Pokémon aliado
        Retorna True se conseguiu trocar, False caso contrário
        """
        # Filtra aliados colocados (exclui o próprio atacante)
        allies = [p for p in placement_manager.placed_pokemon if p != attacker and p.is_alive()]

        if not allies:
            print(f"[TELEPORT] {attacker.name} tentou trocar, mas não há aliados!")
            return False

        # Escolhe um aliado aleatório
        target_ally = random.choice(allies)

        # Guarda as posições atuais
        attacker_old_x = attacker.x
        attacker_old_y = attacker.y
        attacker_old_spot_tile = (attacker.placed_tile_x, attacker.placed_tile_y) if hasattr(attacker,
                                                                                             'placed_tile_x') else None

        ally_old_x = target_ally.x
        ally_old_y = target_ally.y
        ally_old_spot_tile = (target_ally.placed_tile_x, target_ally.placed_tile_y) if hasattr(target_ally,
                                                                                               'placed_tile_x') else None

        # Troca as posições
        attacker.x = ally_old_x
        attacker.y = ally_old_y
        if hasattr(attacker, 'placed_tile_x'):
            attacker.placed_tile_x = target_ally.placed_tile_x
            attacker.placed_tile_y = target_ally.placed_tile_y
        attacker.original_spot_x = attacker.x
        attacker.original_spot_y = attacker.y

        target_ally.x = attacker_old_x
        target_ally.y = attacker_old_y
        if hasattr(target_ally, 'placed_tile_x'):
            target_ally.placed_tile_x = attacker_old_spot_tile[0] if attacker_old_spot_tile else None
            target_ally.placed_tile_y = attacker_old_spot_tile[1] if attacker_old_spot_tile else None
        target_ally.original_spot_x = target_ally.x
        target_ally.original_spot_y = target_ally.y

        # Atualiza os rects
        attacker.rect.x, attacker.rect.y = attacker.x, attacker.y
        target_ally.rect.x, target_ally.rect.y = target_ally.x, target_ally.y

        # Reseta estados de combate
        attacker.combat_state = "idle"
        attacker.target = None
        target_ally.combat_state = "idle"
        target_ally.target = None

        # Mostra mensagem
        effect_manager.add_status_text(attacker, f"{attacker.name} trocou de lugar com {target_ally.name}!",
                                       duration=1.5)
        print(f"[TELEPORT] {attacker.name} trocou de lugar com {target_ally.name}!")

        # Toca som (opcional)
        from src.managers.move_sound_manager import move_sound_manager
        move_sound_manager.play_attack_sound("teleport")

        return True

    def _perform_teleport(self, attacker, target_spot, placement_manager, effect_manager):
        """
        Executa o teleport para um spot específico
        """
        tile_size = placement_manager.tile_size

        # Calcula o centro do spot destino
        new_x = (target_spot.x // tile_size) * tile_size + tile_size // 2
        new_y = (target_spot.y // tile_size) * tile_size + tile_size // 2

        # Salva a posição antiga para debug
        old_x = attacker.x
        old_y = attacker.y
        old_tile = (attacker.placed_tile_x, attacker.placed_tile_y) if hasattr(attacker, 'placed_tile_x') else None

        # Move o Pokémon
        attacker.x = new_x
        attacker.y = new_y
        attacker.original_spot_x = new_x
        attacker.original_spot_y = new_y

        # Atualiza as coordenadas de tile
        attacker.placed_tile_x = new_x // tile_size
        attacker.placed_tile_y = new_y // tile_size

        # Atualiza o rect
        attacker.rect.x, attacker.rect.y = attacker.x, attacker.y

        # Marca o novo spot como ocupado
        target_spot.occupied = True

        # Desocupa o spot antigo
        if old_tile:
            for spot in placement_manager.game.spot_renderer.get_spots():
                spot_tile_x = spot.x // tile_size
                spot_tile_y = spot.y // tile_size
                if spot_tile_x == old_tile[0] and spot_tile_y == old_tile[1]:
                    spot.occupied = False
                    print(f"[TELEPORT] Spot antigo ({spot.x}, {spot.y}) desocupado")
                    break

        # Reseta estado de combate
        attacker.combat_state = "idle"
        attacker.target = None
        attacker.charge_cooldown = 0

        # Mostra mensagem
        effect_manager.add_status_text(attacker, f"{attacker.name} usou Teleport!", duration=1.0)
        print(f"[TELEPORT] {attacker.name} teleportou de ({old_x}, {old_y}) para ({new_x}, {new_y})!")

        # Toca som
        from src.managers.move_sound_manager import move_sound_manager
        move_sound_manager.play_attack_sound("teleport")

        # Toca animação de teleporte (se tiver)
        if hasattr(attacker, 'play_teleport_animation'):
            attacker.play_teleport_animation()

        return True

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
        placement_manager._remove_pokemon(target)

        # Opcional: toca som de retorno
        from src.managers.move_sound_manager import move_sound_manager
        move_sound_manager.play_attack_sound("return")

        print(f"[FORCE_SWITCH] {target.name} retornou ao time com sucesso!")
        return True