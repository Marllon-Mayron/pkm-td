# src/battle/battle_system.py
import random

from src.battle.effects.specific.weather.weather_manager import WeatherManager
from src.battle.effects.specific.weather.weather_state import WeatherType
from src.battle.effects.residual_effect import ResidualEffectManager
from src.battle.damage_calculator import DamageCalculator
from src.battle.effects import EffectManager, EffectTiming, StatType, StatusType
from src.battle.projectile import Projectile

from typing import List, Set

from src.entities.pokemon import Pokemon


class BattleSystem:
    """Gerencia combate entre Pokémon usando moves"""

    def __init__(self, game_scene=None):
        self.game_scene = game_scene
        self.projectiles: List[Projectile] = []
        self.effect_manager = EffectManager()
        self.active_multi_hit = None  # Estado do multi-hit ativo
        self.active_charge_move = None
        self.residual_effects = ResidualEffectManager(self)
        # Weather system
        self.weather_manager = WeatherManager(self)
        self.weather_filter = None

        # ===== NOVO: RASTREAMENTO DE PARTICIPANTES DA BATALHA =====
        self.battle_participants: Set[int] = set()  # IDs dos Pokémon que participaram

    def set_effect_manager_for_pokemon(self, pokemon):
        """Vincula o effect_manager a um Pokémon e registra"""
        pokemon.effect_manager = self.effect_manager
        self.effect_manager.register_pokemon(pokemon)
        print(f"[BATTLE] EffectManager vinculado a {pokemon.name} (id={id(pokemon)})")

    def update(self, dt: float):
        """Atualiza projéteis e multi-hits ativos"""
        # Atualiza projéteis
        for projectile in self.projectiles[:]:
            projectile.update(dt)
            if projectile.is_finished:
                self.projectiles.remove(projectile)

        # ===== ATUALIZA DISABLE =====
        self._update_disable(dt)
        # Atualiza multi-hit ativo
        if self.active_multi_hit:
            still_active = self.active_multi_hit.update(dt)
            if not still_active:
                self.active_multi_hit = None
        # ===== ATUALIZA EFEITOS ESPECIFICOS =====
        if hasattr(self, 'active_triple_kick') and self.active_triple_kick:
            still_active = self.active_triple_kick.update(dt)
            if not still_active:
                self.active_triple_kick = None
                print(f"[BATTLE] Triple Kick finalizado ou interrompido!")

        self.residual_effects.update(dt)
        # ===== ATUALIZA CLIMA =====
        self.weather_manager.update(dt)

    def register_participant(self, pokemon: 'Pokemon'):
        """Registra um Pokémon como participante da batalha"""
        if pokemon and not pokemon.is_wild and pokemon.is_alive():
            self.battle_participants.add(id(pokemon))
            print(f"[XP_PARTICIPANT] {pokemon.name} registrado como participante")

    def clear_participants(self):
        """Limpa a lista de participantes (chamado quando a wave termina)"""
        self.battle_participants.clear()

    def distribute_xp_for_defeated_enemy(self, defeated_enemy: 'Pokemon'):
        """Distribui XP APENAS para os Pokémon que atacaram este inimigo específico"""

        # ===== OBTÉM OS ATACANTES QUE ATINGIRAM ESTE INIMIGO =====
        attackers = self.get_attackers_for_enemy(defeated_enemy)

        if not attackers:
            print(f"[XP] Nenhum atacante registrado para {defeated_enemy.name}")
            self.clear_enemy_attackers(defeated_enemy)
            return

        # ===== CALCULA XP BASE (exponencial pelo nível do inimigo) =====
        level = defeated_enemy.level
        base_xp = 5 + int((level ** 1.5) * 2)

        # Bônus para boss (2x)
        if defeated_enemy.is_boss:
            base_xp = int(base_xp * 1.5)
            print(f"[XP] BOSS derrotado! XP base: {base_xp}")

        # Bônus para shiny (1.5x)
        if defeated_enemy.is_shiny:
            base_xp = int(base_xp * 1.5)

        # ===== XP DIVIDIDO IGUALMENTE ENTRE OS ATACANTES =====
        xp_per_attacker = max(1, base_xp // len(attackers))

        print(f"[XP] {defeated_enemy.name} (nível {level}) foi atacado por {len(attackers)} Pokémon")
        print(f"[XP] Distribuindo {xp_per_attacker} XP para cada atacante")

        # Obtém EVs do inimigo
        ev_yield = {}
        if self.game_scene and hasattr(self.game_scene, 'player'):
            ev_yield = self.game_scene.player.pokedex.get_ev_yield(defeated_enemy.id)

        # Multiplicador de EV para boss/shiny
        ev_multiplier = 1.0
        if defeated_enemy.is_boss:
            ev_multiplier *= 3
        if defeated_enemy.is_shiny:
            ev_multiplier *= 2

        # Aplica multiplicador de Pay Day se houver
        pay_day_xp_mult = 1.0
        if hasattr(defeated_enemy, '_pay_day_hit') and defeated_enemy._pay_day_hit:
            pay_day_xp_mult = getattr(defeated_enemy, '_pay_day_xp_multiplier', 1.5)
            xp_per_attacker = int(xp_per_attacker * pay_day_xp_mult)
            ev_multiplier *= pay_day_xp_mult
            print(f"[PAY_DAY] Bônus XP! Multiplicador x{pay_day_xp_mult}")

        # Distribui XP e EVs para cada atacante
        for attacker in attackers:
            # Ganha XP
            old_level = attacker.level
            attacker.gain_xp(xp_per_attacker)

            # Ganha EVs
            if any(ev_yield.values()):
                evs_gained = {}
                for stat, value in ev_yield.items():
                    if value > 0:
                        ev_value = max(1, int(value * ev_multiplier))
                        evs_gained[stat] = ev_value

                if attacker.stats.can_gain_evs(evs_gained):
                    attacker.stats.gain_evs(evs_gained)
                    print(f"[XP] {attacker.name} ganhou {xp_per_attacker} XP e EVs: {evs_gained}")
                else:
                    print(f"[XP] {attacker.name} ganhou {xp_per_attacker} XP (EVs bloqueados)")
            else:
                print(f"[XP] {attacker.name} ganhou {xp_per_attacker} XP")

        # ===== LIMPA OS ATACANTES DO INIMIGO =====
        self.clear_enemy_attackers(defeated_enemy)

    def _give_xp_to_pokemon(self, pokemon: 'Pokemon', xp_amount: int, defeated_enemy: 'Pokemon'):
        """Dá XP a um Pokémon individual"""
        # Aplica multiplicador de Pay Day se houver
        pay_day_xp_mult = 1.0

        if hasattr(defeated_enemy, '_pay_day_hit') and defeated_enemy._pay_day_hit:
            pay_day_xp_mult = getattr(defeated_enemy, '_pay_day_xp_multiplier', 1.5)
            xp_amount = int(xp_amount * pay_day_xp_mult)
            print(f"[PAY_DAY] Bônus XP! {pokemon.name} ganhou {xp_amount} XP (x{pay_day_xp_mult})")

        old_level = pokemon.level
        pokemon.gain_xp(xp_amount)

        # Distribui EVs (agora também dividido igualmente)
        ev_yield = self.game_scene.player.pokedex.get_ev_yield(defeated_enemy.id)

        ev_multiplier = 1.0
        if defeated_enemy.is_boss:
            ev_multiplier *= 3
        if defeated_enemy.is_shiny:
            ev_multiplier *= 2
        if pay_day_xp_mult > 1.0:
            ev_multiplier *= pay_day_xp_mult

        if any(ev_yield.values()):
            evs_gained = {}
            for stat, value in ev_yield.items():
                if value > 0:
                    evs_gained[stat] = max(1, int(value * ev_multiplier))

            if pokemon.stats.can_gain_evs(evs_gained):
                pokemon.stats.gain_evs(evs_gained)
                print(f"[XP] {pokemon.name} ganhou {xp_amount} XP e EVs: {evs_gained}")
            else:
                print(f"[XP] {pokemon.name} ganhou {xp_amount} XP (EVs bloqueados)")
        else:
            print(f"[XP] {pokemon.name} ganhou {xp_amount} XP")

        # Limpa as flags de Pay Day após distribuir
        if hasattr(defeated_enemy, '_pay_day_hit'):
            defeated_enemy._pay_day_hit = False
            if hasattr(defeated_enemy, '_pay_day_hit_count'):
                delattr(defeated_enemy, '_pay_day_hit_count')
            if hasattr(defeated_enemy, '_pay_day_gold_multiplier'):
                delattr(defeated_enemy, '_pay_day_gold_multiplier')
            if hasattr(defeated_enemy, '_pay_day_xp_multiplier'):
                delattr(defeated_enemy, '_pay_day_xp_multiplier')

    def attempt_attack(self, attacker: 'Pokemon', target: 'Pokemon') -> bool:
        """Tenta realizar um ataque com o move atual do atacante"""

        # ===== REGISTRA ATACANTE COMO PARTICIPANTE (antes de qualquer verificação) =====
        # Isso garante que mesmo moves que "falham" ou são bloqueados ainda contam como participação
        if not attacker.is_wild:
            # Registra que este Pokémon está atacando (para o sistema de XP)
            # O target pode ser None para moves que não têm alvo (ex: Harden)
            if target:
                self.register_attacker_for_enemy(attacker, target)
            else:
                # Para moves sem alvo (buffs em si mesmo), registra como participação genérica
                self.register_participant(attacker)

        # ===== LIMPA RASTROS DE COUNTER DO ATACANTE ANTES DE ATACAR =====
        self.clear_counter_tracking(attacker)

        # Se já tem um multi-hit ativo, não permite novo ataque
        if self.active_multi_hit:
            print(f"[BATTLE] Aguardando término do multi-hit...")
            return False

        # ===== VERIFICAÇÃO CRÍTICA: GOLPES DE 2 TURNOS =====
        if self.active_charge_move and self.active_charge_move['attacker'] == attacker:
            move_name = self.active_charge_move['move_name']
            charged_target = self.active_charge_move['target']

            if not charged_target or charged_target.is_defeated or not charged_target.is_alive():
                print(f"[TWO_TURN] Alvo {charged_target.name if charged_target else '?'} não está mais disponível!")
                self.active_charge_move = None
                self.effect_manager.add_status_text(attacker, f"Mas falhou!", duration=1.0)
                attacker.attack_cooldown = max(0.3, 1.0 - (attacker.speed_stat / 500))
                return True

            print(f"[TWO_TURN] {attacker.name} está liberando {move_name}!")

            move = None
            for m in attacker.moves:
                if m.name.lower() == move_name.lower():
                    move = m
                    break

            if not move:
                print(f"[BATTLE] Erro: Movimento {move_name} não encontrado!")
                self.active_charge_move = None
                return False

            success = self._execute_two_turn_attack(attacker, charged_target, move)
            self.active_charge_move = None
            return success

        # ===== FLUXO NORMAL =====
        if attacker.is_defeated:
            print(f"[BATTLE] {attacker.name} está derrotado e não pode atacar!")
            return False

        if target and target.is_defeated:
            print(f"[BATTLE] {target.name} está derrotado e não pode ser atacado!")
            return False

        # ===== VERIFICA DISABLE =====
        current_move = attacker.get_current_move()
        if current_move and hasattr(attacker, '_disabled_move') and attacker._disabled_move:
            if current_move.name == attacker._disabled_move:
                self.effect_manager.add_status_text(
                    attacker,
                    f"{current_move.name} está desabilitado!",
                    duration=1.0
                )
                print(f"[DISABLE] {attacker.name} não pode usar {current_move.name}!")
                attacker.attack_cooldown = max(0.3, 1.0 - (attacker.speed_stat / 500))
                return True

        # ===== VERIFICA PP =====
        has_pp = False
        for m in attacker.moves:
            if m.current_pp > 0:
                has_pp = True
                break

        if not has_pp:
            print(f"[BATTLE] {attacker.name} está sem PP em todos os moves! Usando Struggle!")

            from src.entities.move import Move
            struggle_info = {
                "name": "Struggle",
                "type": "normal",
                "power": 50,
                "accuracy": 100,
                "pp": 1,
                "max_pp": 1,
                "category": "physical",
                "description": "Usado quando todos os PP acabam. Causa dano e dano de retorno."
            }
            move = Move("struggle", struggle_info)
            move.current_pp = 1

            if not hasattr(attacker, '_struggle_message_shown') or not attacker._struggle_message_shown:
                self.effect_manager.add_status_text(attacker, f"{attacker.name} não tem PP! Usou Struggle!",
                                                    duration=2.0)
                attacker._struggle_message_shown = True

            result = self._attempt_struggle(attacker, target, move)

            if move.name.lower() != "struggle":
                attacker._last_used_move = move.name
                print(f"[TRACK] {attacker.name} usou {move.name}")

            return result

        if hasattr(attacker, 'get_current_move_for_pattern'):
            move = attacker.get_current_move_for_pattern()
        else:
            move = attacker.get_current_move()

        if not move:
            print(f"[BATTLE] {attacker.name} não tem move selecionado!")
            return False

        from src.battle.effects import EffectFactory
        effect = EffectFactory.create_effect(move.name)

        # ===== VERIFICA SE O MOVE É DE ÁREA =====
        if effect and effect.is_area:
            print(f"[BATTLE_DEBUG] {move.name} é ataque em área (is_area=True)!")
            if move.current_pp <= 0:
                print(f"[BATTLE] {attacker.name} não tem PP para {move.name}!")
                return False

            result = effect.execute(attacker, target, self, self.effect_manager)
            attacker.attack_cooldown = max(0.3, 1.0 - (attacker.speed_stat / 500))

            from src.managers.sounds.move_sound_manager import move_sound_manager
            move_sound_manager.play_attack_sound(move.sound_name)
            print(f"[SOM] {move.name} (área) - som do atacante: {move.sound_name}")

            if move.name.lower() != "struggle":
                attacker._last_used_move = move.name
                print(f"[TRACK] {attacker.name} usou {move.name}")

            return result

        # ===== VERIFICA SE É GOLPE DE 2 TURNOS =====
        if effect and effect.effect_type == "two_turn_attack":
            if move.current_pp <= 0:
                print(f"[BATTLE] {attacker.name} não tem PP para {move.name}!")
                return False

            result = effect.execute(attacker, target, self, self.effect_manager)
            attacker.attack_cooldown = max(0.3, 1.0 - (attacker.speed_stat / 500))

            if move.name.lower() != "struggle":
                attacker._last_used_move = move.name
                print(f"[TRACK] {attacker.name} usou {move.name}")

            return result

        # ===== MOVIMENTOS NORMAIS =====
        if move.current_pp <= 0:
            print(f"[BATTLE] {attacker.name} não tem PP para {move.name}!")
            attacker.has_no_pp = True
            return False

        attacker.has_no_pp = False

        # ===== VERIFICA CONFUSÃO =====
        if self.effect_manager.is_confused(attacker):
            confusion = self.effect_manager.get_confusion(attacker)
            result = confusion.before_attack(attacker, target, self, self.effect_manager)

            if result == "self":
                self._apply_confusion_self_damage(attacker, confusion)
                attacker.attack_cooldown = max(0.3, 1.0 - (attacker.speed_stat / 500))

                if move.name.lower() != "struggle":
                    attacker._last_used_move = move.name
                    print(f"[TRACK] {attacker.name} tentou usar {move.name} mas se machucou")

                return True

            if not confusion.is_active():
                self.effect_manager.remove_confusion(attacker)

        # ===== DESCONGELAMENTO POR ATAQUES DE FOGO =====
        if target:
            target_status = self.effect_manager.get_status(target)
            if target_status and target_status.type == StatusType.FREEZE:
                if move.type.lower() == "fire":
                    target_status.thaw()
                    self.effect_manager.add_status_text(target, f"{target.name} descongelou com o calor!")
                    print(f"[FREEZE] {target.name} descongelou devido ao ataque de fogo {move.name}!")

        # ===== VERIFICA SE O ATACANTE PODE AGIR =====
        status = self.effect_manager.get_status(attacker)

        if status and status.type == StatusType.PARALYSIS:
            status.update_paralysis(0)

        if status and not status.can_attack():
            if status.type == StatusType.PARALYSIS:
                print(f"[BATTLE] {attacker.name} está paralisado e não consegue se mover!")
            elif status.type == StatusType.SLEEP:
                print(f"[BATTLE] {attacker.name} está dormindo e não pode atacar!")
            elif status.type == StatusType.FREEZE:
                print(f"[BATTLE] {attacker.name} está congelado e não pode atacar!")
            else:
                print(f"[BATTLE] {attacker.name} está {status.name.lower()} e não pode atacar!")
            attacker.attack_cooldown = max(0.3, 1.0 - (attacker.speed_stat / 500))

            if move.name.lower() != "struggle":
                attacker._last_used_move = move.name
                print(f"[TRACK] {attacker.name} tentou usar {move.name} mas falhou devido a status")

            return True

        # ===== MOVES DE STATUS (SEM DANO) =====
        if move.category == "status":
            print(f"[BATTLE] {attacker.name} usou {move.name}! (Move de status)")

            from src.managers.sounds.move_sound_manager import move_sound_manager
            move_sound_manager.play_attack_sound(move.sound_name)

            move.current_pp -= 1
            attacker.attack_cooldown = max(0.3, 1.0 - (attacker.speed_stat / 500))

            # Verifica acerto para moves de status (quando aplicam no alvo)
            will_hit = True
            if target and move.accuracy:
                hit_chance = move.accuracy / 100
                accuracy_mult = self.effect_manager.get_stat_multiplier(attacker, StatType.ACCURACY)
                evasion_mult = self.effect_manager.get_stat_multiplier(target, StatType.EVASION)
                hit_chance = hit_chance * accuracy_mult / evasion_mult
                hit_chance = max(0.01, min(1.0, hit_chance))
                will_hit = random.random() <= hit_chance

            if not will_hit and target:
                print(f"[BATTLE] {move.name} errou!")
                self._show_miss_on_attacker(attacker)
            else:
                # Aplica o efeito do move de status
                from src.battle.effects import EffectFactory
                effect = EffectFactory.create_effect(move.name)
                if effect:
                    effect.execute(attacker, target, self, self.effect_manager)
                else:
                    self.effect_manager.add_status_text(attacker, f"{attacker.name} usou {move.name}!", duration=1.0)

            if move.name.lower() != "struggle":
                attacker._last_used_move = move.name
                print(f"[TRACK] {attacker.name} usou {move.name}")

            return True

        # ===== MOVES COM POWER NULL =====
        if move.power is None or move.power == 0:
            result = self._handle_special_damage_move(attacker, target, move)

            if move.name.lower() != "struggle":
                attacker._last_used_move = move.name
                print(f"[TRACK] {attacker.name} usou {move.name}")

            return result

        # ===== MOVES QUE NUNCA ERRAM =====
        never_miss = effect and effect.effect_type == "never_miss"
        has_crash_effect = effect and effect.effect_type == "crash_damage_on_miss"

        # ===== VERIFICA EFEITOS DE ACERTO GARANTIDO =====
        is_guaranteed_hit = False
        guaranteed_hit_effects = ["lock_on", "mind_reader"]

        for effect_key in guaranteed_hit_effects:
            active_flag = f"_{effect_key}_active"
            target_flag = f"_{effect_key}_target"

            if (hasattr(attacker, active_flag) and getattr(attacker, active_flag) and
                    hasattr(attacker, target_flag) and getattr(attacker, target_flag) == target):

                is_guaranteed_hit = True

                if move.name.lower() != "struggle":
                    self.effect_manager.add_status_text(
                        attacker,
                        f"{attacker.name} acertou com certeza!",
                        duration=0.8
                    )

                effect_names = {"lock_on": "Lock-On", "mind_reader": "Mind Reader"}
                effect_display = effect_names.get(effect_key, "Foco")
                print(f"[{effect_display.upper()}] {attacker.name} tem acerto garantido em {target.name}!")

                setattr(attacker, active_flag, False)
                setattr(attacker, target_flag, None)
                break

        # ===== VERIFICA PROTEÇÃO DO ALVO =====
        if target and hasattr(target, '_protected') and target._protected:
            self.effect_manager.add_status_text(
                attacker,
                f"{target.name} está protegido! O ataque não teve efeito!",
                duration=1.5
            )

            target._protection_remaining -= 1

            print(
                f"[PROTECT] {attacker.name} atacou, mas {target.name} estava protegido! {target._protection_remaining} proteções restantes")

            if target._protection_remaining <= 0:
                target._protected = False
                self.effect_manager.add_status_text(
                    target,
                    f"A proteção de {target.name} acabou!",
                    duration=1.0
                )
                print(f"[PROTECT] Proteção de {target.name} acabou!")

            attacker.attack_cooldown = max(0.3, 1.0 - (attacker.speed_stat / 500))

            if move.name.lower() != "struggle":
                attacker._last_used_move = move.name

            return True

        # ===== CALCULAR ACERTO =====
        if never_miss or is_guaranteed_hit:
            will_hit = True
            print(f"[BATTLE] {move.name} nunca erra! (ou acerto garantido ativo)")
        else:
            hit_chance = move.accuracy / 100
            accuracy_mult = self.effect_manager.get_stat_multiplier(attacker, StatType.ACCURACY)
            evasion_mult = self.effect_manager.get_stat_multiplier(target, StatType.EVASION)
            hit_chance = hit_chance * accuracy_mult / evasion_mult
            hit_chance = max(0.01, min(1.0, hit_chance))
            will_hit = random.random() <= hit_chance

        # ===== VERIFICA SE É MOVE ESPECIAL =====
        if move.category == "special" and move.power > 0:
            print(f"[BATTLE] {attacker.name} usou {move.name}! (Ataque especial)")

            # ===== REGISTRA ATACANTE PARA O ALVO =====
            if target:
                self.register_attacker_for_enemy(attacker, target)

            move.current_pp -= 1

            if will_hit:
                damage_result = self._calculate_move_damage(attacker, target, move)
            else:
                damage_result = {
                    "damage": 0,
                    "effectiveness": 1.0,
                    "hit": False,
                    "message": f"O ataque errou!",
                    "stab": False,
                    "critical": False
                }
                if has_crash_effect:
                    self._apply_crash_damage(attacker, move, effect)

            self._create_projectile(attacker, target, move, damage_result, will_hit)
            attacker.attack_cooldown = max(0.3, 1.0 - (attacker.speed_stat / 500))

            if move.name.lower() != "struggle":
                attacker._last_used_move = move.name
                print(f"[TRACK] {attacker.name} usou {move.name}")

            return True

        # ===== ATAQUES FÍSICOS =====
        elif move.category == "physical" and move.power > 0:
            print(f"[BATTLE] {attacker.name} usou {move.name}! (Ataque físico)")

            # ===== REGISTRA ATACANTE PARA O ALVO =====
            if target:
                self.register_attacker_for_enemy(attacker, target)

            from src.managers.sounds.move_sound_manager import move_sound_manager
            move_sound_manager.play_attack_sound(move.sound_name)

            move.current_pp -= 1

            if will_hit:
                damage_result = self._calculate_move_damage(attacker, target, move)
                self._apply_damage(attacker, target, damage_result, move)
                self._apply_move_effect(attacker, target, move, damage_result["damage"])
            else:
                print(f"[BATTLE] {move.name} errou!")
                self._show_miss_on_attacker(attacker)
                if has_crash_effect:
                    self._apply_crash_damage(attacker, move, effect)

            attacker.attack_cooldown = max(0.3, 1.0 - (attacker.speed_stat / 500))

            if move.name.lower() != "struggle":
                attacker._last_used_move = move.name
                print(f"[TRACK] {attacker.name} usou {move.name}")

            return True

        # Fallback
        else:
            print(f"[BATTLE] {attacker.name} usou {move.name}!")

            # ===== REGISTRA ATACANTE PARA O ALVO =====
            if target:
                self.register_attacker_for_enemy(attacker, target)

            move.current_pp -= 1
            attacker.attack_cooldown = max(0.3, 1.0 - (attacker.speed_stat / 500))

            if move.name.lower() != "struggle":
                attacker._last_used_move = move.name
                print(f"[TRACK] {attacker.name} usou {move.name}")

            return True

    def _handle_special_damage_move(self, attacker: 'Pokemon', target: 'Pokemon', move) -> bool:
        """
        Processa movimentos especiais que causam dano de forma diferente
        (Super Fang, Seismic Toss, etc)
        """
        import random

        print(f"[BATTLE] {attacker.name} usou {move.name}!")

        # Verifica acerto
        hit_chance = move.accuracy / 100
        accuracy_mult = self.effect_manager.get_stat_multiplier(attacker, StatType.ACCURACY)
        evasion_mult = self.effect_manager.get_stat_multiplier(target, StatType.EVASION)
        hit_chance = hit_chance * accuracy_mult / evasion_mult
        hit_chance = max(0.01, min(1.0, hit_chance))

        will_hit = random.random() <= hit_chance

        if not will_hit:
            print(f"[BATTLE] {move.name} errou!")
            self._show_miss_on_attacker(attacker)
            attacker.attack_cooldown = max(0.3, 1.0 - (attacker.speed_stat / 500))

            self.miss_hit_general(attacker)

            return True

        # Toca som
        from src.managers.sounds.move_sound_manager import move_sound_manager
        move_sound_manager.play_attack_sound(move.sound_name)

        # Aplica o efeito (que vai causar o dano)
        from src.battle.effects import EffectFactory
        effect = EffectFactory.create_effect(move.name)

        if effect:
            # O dano será aplicado dentro do effect
            effect.execute(attacker, target, self, self.effect_manager)
        else:
            # Fallback: dano baseado no nível
            damage = attacker.level
            target.take_damage(damage, attacker=attacker)
            self.effect_manager.add_status_text(target, f"-{damage} HP", duration=1.0)

        # Cooldown
        attacker.attack_cooldown = max(0.3, 1.0 - (attacker.speed_stat / 500))

        return True

    def miss_hit_general (self, attacker):
        if hasattr(self, 'effect_manager') and self.effect_manager:
            buff = self.effect_manager.get_battle_item_buff(attacker)
            if buff and buff["stat"] == StatType.ACCURACY:
                # Conquista: acertar um miss com X Accuracy ativo
                if hasattr(self, 'game_scene') and self.game_scene:
                    player = self.game_scene.player
                    if hasattr(player, 'achievement_manager'):
                        phase_id = f"{self.game_scene.chapter_id}-{self.game_scene.phase_number}"
                        player.achievement_manager.increment_counter("accuracy_buff_miss_count")
                        player.achievement_manager.check_and_unlock("accuracy_buff_miss", phase_id)
                        print("[ACHIEVEMENT] Miss com X Accuracy ativo!")

    def _attempt_struggle(self, attacker: 'Pokemon', target: 'Pokemon', move) -> bool:
        """
        Executa o movimento Struggle
        - Sempre acerta (ignora accuracy/evasion)
        - Causa dano typeless (não tem resistência/imunidade)
        - Causa recoil de 1/4 do HP máximo do atacante
        """
        print(f"[STRUGGLE] {attacker.name} está sem PP e usou Struggle!")

        # Mostra mensagem
        self.effect_manager.add_status_text(attacker, f"{attacker.name} usou Struggle!", duration=1.5)

        # ===== CALCULA DANO =====
        damage_result = self._calculate_struggle_damage(attacker, target, move)

        print(f"[STRUGGLE] Dano calculado: {damage_result['damage']}")

        # ===== APLICA DANO AO ALVO =====
        if damage_result["damage"] > 0:
            target.take_damage(damage_result["damage"], attacker=attacker)
            print(f"[STRUGGLE] {attacker.name} causou {damage_result['damage']} de dano em {target.name}!")

            # Toca som de impacto
            from src.managers.sounds.move_sound_manager import move_sound_manager
            move_sound_manager.play_hit_sound("struggle")

            # Toca animação de hurt no alvo
            if hasattr(target, 'play_hurt_animation'):
                target.play_hurt_animation()
        else:
            print(f"[STRUGGLE] Nenhum dano causado!")

        # ===== APLICA RECOIL (1/4 do HP máximo) =====
        recoil_damage = max(1, int(attacker.max_hp * 0.25))
        attacker.take_damage(recoil_damage, attacker=attacker)

        self.effect_manager.add_status_text(attacker, f"Recoil: -{recoil_damage} HP", duration=1.0)
        print(f"[STRUGGLE] {attacker.name} sofreu {recoil_damage} de recoil!")

        # Toca animação de hurt no atacante
        if hasattr(attacker, 'play_hurt_animation'):
            attacker.play_hurt_animation()

        # Cooldown
        attacker.attack_cooldown = max(0.3, 1.0 - (attacker.speed_stat / 500))

        return True

    def _execute_two_turn_attack(self, attacker: 'Pokemon', target: 'Pokemon', move) -> bool:
        """
        Executa o ataque de um golpe de 2 turnos no segundo turno.
        Não gasta PP.
        """
        # Verifica se o alvo ainda é válido
        if target.is_defeated or not target.is_alive():
            print(f"[TWO_TURN] Alvo {target.name} não está mais disponível para o ataque!")
            self.effect_manager.add_status_text(attacker, f"Mas falhou!", duration=1.0)
            return False

        # Verifica se o atacante ainda pode agir
        status = self.effect_manager.get_status(attacker)
        if status and not status.can_attack():
            self.effect_manager.add_status_text(attacker, f"{attacker.name} não conseguiu executar o ataque!")
            return False

        # ===== NÃO GASTA PP =====

        # Calcula dano UMA ÚNICA VEZ
        damage_result = self._calculate_move_damage(attacker, target, move)

        if damage_result["hit"]:
            self._apply_damage(attacker, target, damage_result, move)
            self._apply_move_effect(attacker, target, move, damage_result["damage"])
        else:
            self._show_miss_on_attacker(attacker)

        # Aplica cooldown
        attacker.attack_cooldown = max(0.3, 1.0 - (attacker.speed_stat / 500))

        return True

    def _calculate_struggle_damage(self, attacker, target, move):
        """
        Calcula dano do Struggle (typeless, ignora resistências)
        """
        # Struggle é typeless - não tem super efetivo ou resistência
        # Mas ainda usa a fórmula normal de dano físico
        level = attacker.level
        power = move.power  # 50

        # ===== USA O STAT DE ATAQUE FÍSICO DO ATACANTE =====
        attack_stat = attacker.attack
        defense_stat = target.defense

        # Aplica modificadores de estágio (buff/debuff)
        if hasattr(attacker, 'effect_manager') and attacker.effect_manager:
            atk_mult = attacker.effect_manager.get_stat_multiplier(attacker, StatType.ATTACK)
            def_mult = attacker.effect_manager.get_stat_multiplier(target, StatType.DEFENSE)
            attack_stat = int(attack_stat * atk_mult)
            defense_stat = int(defense_stat * def_mult)
            print(f"[STRUGGLE] Modificadores: atk_mult={atk_mult:.2f}, def_mult={def_mult:.2f}")

        # Evita divisão por zero
        if defense_stat <= 0:
            defense_stat = 1

        # Fórmula de dano padrão Pokémon
        # damage = ((2 * level / 5 + 2) * power * attack / defense) / 50 + 2
        damage = ((2 * level / 5 + 2) * power * attack_stat / defense_stat) / 50 + 2

        # Variação aleatória (85-100%)
        damage = damage * random.uniform(0.85, 1.0)

        # Dano mínimo de 1
        damage = max(1, int(damage))

        print(
            f"[STRUGGLE] Dano calculado: {damage} (Level={level}, Power={power}, Atk={attack_stat}, Def={defense_stat})")

        return {
            "damage": damage,
            "effectiveness": 1.0,  # Sempre neutro
            "hit": True,
            "message": "",
            "stab": False,
            "critical": False
        }

    def _show_miss_on_attacker(self, attacker):
        """Mostra o texto MISS no ATACANTE (quem usou o golpe)"""
        if not hasattr(attacker, 'miss_timer'):
            attacker.miss_timer = 0.0
        attacker.miss_timer = 0.6

    def _show_miss_on_target(self, target):
        """Mostra o texto MISS no alvo (mantido para compatibilidade, mas não usado)"""
        if not hasattr(target, 'miss_timer'):
            target.miss_timer = 0.0
        target.miss_timer = 0.6

    def _create_projectile(self, attacker: 'Pokemon', target: 'Pokemon', move, damage_result: dict, will_hit: bool):
        """Cria um projétil para ataque especial"""
        # Cores baseadas no tipo
        type_colors = {
            "normal": (168, 168, 120),
            "fire": (240, 128, 48),
            "water": (104, 144, 240),
            "electric": (248, 208, 48),
            "grass": (120, 200, 80),
            "ice": (152, 216, 216),
            "fighting": (192, 48, 40),
            "poison": (160, 64, 160),
            "ground": (224, 192, 104),
            "flying": (168, 144, 240),
            "psychic": (248, 88, 136),
            "bug": (168, 184, 32),
            "rock": (184, 160, 56),
            "ghost": (112, 88, 152),
            "dragon": (112, 56, 248),
            "dark": (112, 88, 72),
            "steel": (184, 184, 208),
            "fairy": (238, 153, 238)
        }
        color = type_colors.get(move.type.lower(), (255, 255, 255))

        # Usar a velocidade de movimento do atacante para o projétil
        projectile_speed = attacker.move_speed * 60

        projectile = Projectile(
            attacker=attacker,
            target=target,
            move_name=move.name,
            damage=damage_result["damage"],
            effectiveness=damage_result["effectiveness"],
            color=color,
            speed=projectile_speed,
            will_hit=will_hit
        )
        self.projectiles.append(projectile)

        from src.managers.sounds.move_sound_manager import move_sound_manager

        move_sound_manager.play_attack_sound(move.sound_name)
        print(f"[SOM] {move.name} - som do atacante: {move.sound_name}")

    def _apply_damage(self, attacker: 'Pokemon', target: 'Pokemon', damage_result: dict, move):
        """Aplica dano a um alvo com rastreamento para Counter e Mirror Coat"""
        damage = damage_result["damage"]

        # Verifica se o movimento é inefetivo (imune)
        if damage_result["effectiveness"] == 0:
            print(f"[BATTLE] {move.name} não afeta {target.name}!")
            self.effect_manager.add_status_text(target, "Não afeta!", duration=1.0)
            return

        from src.managers.sounds.move_sound_manager import move_sound_manager

        # Toca som do ataque (físico ou especial)
        move_sound_manager.play_attack_sound(move.sound_name)
        print(f"[SOM] {move.name} - som do atacante: {move.sound_name}")

        # ===== RASTREIA DANO PARA COUNTER (FÍSICO) =====
        if move.category == "physical" and damage > 0 and target.is_alive() and not target.is_defeated:
            target._last_physical_damage_received = damage
            target._last_physical_attacker = attacker
            print(f"[COUNTER_TRACK] {target.name} registrou {damage} de dano FÍSICO de {attacker.name}")

        # ===== RASTREIA DANO PARA MIRROR COAT (ESPECIAL) =====
        if move.category == "special" and damage > 0 and target.is_alive() and not target.is_defeated:
            target._last_special_damage_received = damage
            target._last_special_attacker = attacker
            print(f"[MIRROR_COAT_TRACK] {target.name} registrou {damage} de dano ESPECIAL de {attacker.name}")

        # Toca som de impacto
        move_sound_manager.play_hit_sound(move.sound_name)
        print(f"[SOM] {move.name} - som de impacto: {move.sound_name}_target")

        # ===== EXIBE MENSAGEM DE CRÍTICO =====
        if damage_result.get("critical", False):
            self.effect_manager.add_status_text(attacker, "Acerto Crítico!", duration=1.0)
            print(f"[CRITICAL] Ataque crítico de {attacker.name} causou {damage} de dano em {target.name}!")

        # ===== EXIBE MENSAGEM DE SUPER EFETIVO =====
        if damage_result["effectiveness"] > 1.0:
            self.effect_manager.add_status_text(attacker, "Super efetivo!", duration=0.8)

        # ===== EXIBE MENSAGEM DE NÃO MUITO EFETIVO =====
        elif 0 < damage_result["effectiveness"] < 1.0:
            self.effect_manager.add_status_text(attacker, "Não é muito efetivo...", duration=0.8)

        # Aplica o dano ao alvo
        target.take_damage(damage, attacker=attacker)

        # Log do dano causado
        print(f"[DAMAGE] {attacker.name} causou {damage} de dano a {target.name} com {move.name}!")

    def _apply_crash_damage(self, attacker, move, effect):
        """
        Aplica dano de colisão para movimentos como Jump Kick
        """
        crash_percentage = effect.params.get("crash_damage_percentage", 0.5)
        crash_formula = effect.params.get("crash_damage_formula", "max_hp_percentage")

        if crash_formula == "max_hp_percentage":
            # Dano = porcentagem do HP máximo (ex: 50%)
            damage = max(1, int(attacker.max_hp * crash_percentage))
        elif crash_formula == "current_hp_percentage":
            # Dano = porcentagem do HP atual
            damage = max(1, int(attacker.current_hp * crash_percentage))
        else:
            damage = max(1, int(attacker.max_hp * 0.5))  # Fallback

        # Aplica dano ao atacante
        attacker.take_damage(damage, attacker=attacker)

        # Mostra mensagem
        self.effect_manager.add_status_text(attacker, f"{attacker.name} se machucou!", duration=1.5)
        print(f"[CRASH] {attacker.name} errou {move.name} e se machucou! Perdeu {damage} HP")

        # Toca animação de hurt
        if hasattr(attacker, 'play_hurt_animation'):
            attacker.play_hurt_animation()

        # Toca som de dano
        from src.managers.sounds.move_sound_manager import move_sound_manager
        move_sound_manager.play_attack_sound("hurt")

    def _apply_confusion_self_damage(self, attacker, confusion):
        """Aplica dano de confusão (atacante se machuca)"""
        damage = confusion.calculate_self_damage(attacker)

        # Toca som de dano
        from src.managers.sounds.move_sound_manager import move_sound_manager
        move_sound_manager.play_attack_sound("hurt")

        # Aplica dano (atacante é a fonte do dano para si mesmo)
        attacker.take_damage(damage, attacker=attacker)

        # Mostra texto de dano
        self.effect_manager.add_status_text(attacker, f"-{damage} HP (Confusão)", duration=1.0)

        print(f"[CONFUSION] {attacker.name} se machucou na confusão e causou {damage} de dano a si mesmo!")

        # Toca animação de hurt
        if hasattr(attacker, 'play_hurt_animation'):
            attacker.play_hurt_animation()

    def _calculate_move_damage(self, attacker, target, move):
        """Calcula dano do move com modificadores de stat e screens"""
        damage_result = DamageCalculator.calculate_damage(attacker, target, move)

        if not damage_result["hit"]:
            return damage_result

        # Aplica modificadores de stat
        from src.battle.effects import StatType

        if move.category == "physical":
            atk_mult = self.effect_manager.get_stat_multiplier(attacker, StatType.ATTACK)
            def_mult = self.effect_manager.get_stat_multiplier(target, StatType.DEFENSE)
            damage_result["damage"] = int(damage_result["damage"] * atk_mult / def_mult)
        else:
            sp_atk_mult = self.effect_manager.get_stat_multiplier(attacker, StatType.SP_ATTACK)
            sp_def_mult = self.effect_manager.get_stat_multiplier(target, StatType.SP_DEFENSE)
            damage_result["damage"] = int(damage_result["damage"] * sp_atk_mult / sp_def_mult)

        # ===== APLICA EFEITOS DO CLIMA =====
        move_info = {
            'type': move.type,
            'category': move.category,
            'power': move.power
        }
        weather_effects = self.apply_weather_effects(attacker, target, move_info)

        if weather_effects['damage_multiplier'] != 1.0:
            old_damage = damage_result["damage"]
            damage_result["damage"] = int(damage_result["damage"] * weather_effects['damage_multiplier'])
            if weather_effects['message']:
                self.effect_manager.add_status_text(attacker, weather_effects['message'], duration=1.0)
            print(
                f"[WEATHER] Dano ajustado: {old_damage} -> {damage_result['damage']} (x{weather_effects['damage_multiplier']})")

        # ===== APLICA REDUÇÃO DE SCREENS =====
        screen_reduction = self.get_screen_damage_reduction(target, move.category)
        if screen_reduction < 1.0:
            old_damage = damage_result["damage"]
            damage_result["damage"] = int(damage_result["damage"] * screen_reduction)
            print(f"[SCREEN] Dano reduzido de {old_damage} para {damage_result['damage']} (x{screen_reduction})")

        # Queimadura reduz ataque físico
        if move.category == "physical":
            status = self.effect_manager.get_status(attacker)
            if status and status.type == StatusType.BURN:
                damage_result["damage"] = int(damage_result["damage"] * 0.5)

        return damage_result

    def _apply_move_effect(self, attacker, target, move, damage):
        """Aplica efeitos especiais do move (multi-hit, flinch, etc)"""
        from src.battle.effects import EffectFactory

        effect = EffectFactory.create_effect(move.name)
        if effect:
            if effect.timing == EffectTiming.AFTER_DAMAGE:
                effect.execute(attacker, target, self, self.effect_manager, damage)
            elif effect.timing == EffectTiming.ON_HIT:
                effect.execute(attacker, target, self, self.effect_manager, damage)

    def _is_status_applying_move(self, move_name: str) -> bool:
        """Verifica se um move realmente aplica um status (veneno, queimadura, paralisia, sono)"""
        from src.battle.effects.effect_factory import EffectFactory

        effect = EffectFactory.create_effect(move_name)
        if not effect:
            return False

        status_moves = ["status", "status_chance"]
        stat_mod_moves = ["stat_mod"]

        if effect.effect_type in stat_mod_moves:
            return False

        if effect.effect_type in status_moves:
            return True

        return False

    def _apply_status_effect(self, attacker, target, move):
        """Aplica efeito de status do move"""
        from src.battle.effects import EffectFactory

        effect = EffectFactory.create_effect(move.name)
        if effect:
            if effect.effect_type in ["status", "status_chance"]:
                effect.execute(attacker, target, self, self.effect_manager)
                target.register_status_application(attacker, move.name)
            else:
                effect.execute(attacker, target, self, self.effect_manager)
        else:
            print(f"[BATTLE] {attacker.name} usou {move.name}! (Efeito de status)")
            self.effect_manager.add_status_text(target, f"{move.name} usado!")

    def get_screen_damage_reduction(self, defender, move_category):
        """
        Retorna a redução de dano aplicável baseada nos screens ativos do defensor
        E decrementa os turns automaticamente
        """
        # Cria um MoveEffect temporário para usar o método
        from src.battle.effects.move_effect import MoveEffect
        temp_effect = MoveEffect("temp", "temp")

        # Usa o método de decremento
        reduction = temp_effect._decrement_screen_turns(self, defender, move_category)

        return reduction

    def clear_counter_tracking(self, pokemon):
        """Limpa os rastros de Counter e Mirror Coat de um Pokémon"""
        # Counter (físico)
        if hasattr(pokemon, '_last_physical_damage_received'):
            pokemon._last_physical_damage_received = 0
        if hasattr(pokemon, '_last_physical_attacker'):
            pokemon._last_physical_attacker = None

        # Mirror Coat (especial)
        if hasattr(pokemon, '_last_special_damage_received'):
            pokemon._last_special_damage_received = 0
        if hasattr(pokemon, '_last_special_attacker'):
            pokemon._last_special_attacker = None

    def render_projectiles(self, screen, camera, screen_manager):
        """Renderiza projéteis"""
        for projectile in self.projectiles:
            projectile.render(screen, camera, screen_manager)

    def clear_all_effects(self):
        """Limpa todos os efeitos (usado quando batalha termina)"""
        self.residual_effects.clear_all()
        self.effect_manager.clear_all()
        self.effect_manager.clear_battle_item_buffs()
        self.battle_participants.clear()

        # ===== LIMPA SCREENS =====
        if hasattr(self, 'active_screens'):
            self.active_screens.clear()
            print(f"[SCREEN] Todos os screens foram limpos!")

        # ===== LIMPA MODIFICADORES DE CRÍTICO =====
        from src.battle.effects.critical_hit import CriticalHitSystem
        CriticalHitSystem.clear_all_modifiers()

    def _update_disable(self, dt: float):
        """Atualiza o contador de turnos do Disable"""
        # Método 1: varrer todos os Pokémon em campo
        if hasattr(self, 'game_scene') and self.game_scene:
            # Verifica Pokémon aliados
            if hasattr(self.game_scene, 'placement_manager'):
                for pokemon in self.game_scene.placement_manager.placed_pokemon:
                    self._update_pokemon_disable(pokemon, dt)

            # Verifica inimigos
            if hasattr(self.game_scene, 'wave_manager'):
                for pokemon in self.game_scene.wave_manager.active_enemies:
                    self._update_pokemon_disable(pokemon, dt)

    def _update_pokemon_disable(self, pokemon, dt: float):
        """Atualiza o disable de um Pokémon individual"""
        if not hasattr(pokemon, '_disabled_move') or not pokemon._disabled_move:
            return

        # Usamos um timer simples (cada turno ≈ 2 segundos)
        if not hasattr(pokemon, '_disable_timer'):
            pokemon._disable_timer = 0.0

        pokemon._disable_timer += dt

        # A cada 2 segundos, decrementa um turno
        if pokemon._disable_timer >= 2.0:
            pokemon._disable_timer = 0
            pokemon._disabled_turns -= 1

            print(
                f"[DISABLE] {pokemon.name}: {pokemon._disabled_move} desabilitado por mais {pokemon._disabled_turns} turnos")

            if pokemon._disabled_turns <= 0:
                # Remove o disable
                self._remove_disable(pokemon)

    def _remove_disable(self, pokemon):
        """Remove o efeito Disable do Pokémon"""
        if hasattr(pokemon, '_disabled_move') and pokemon._disabled_move:
            move_name = pokemon._disabled_move

            # Mostra mensagem
            if hasattr(self, 'effect_manager') and self.effect_manager:
                self.effect_manager.add_status_text(
                    pokemon,
                    f"{move_name} não está mais desabilitado!",
                    duration=1.5
                )

            print(f"[DISABLE] {move_name} de {pokemon.name} foi liberado!")

            # Limpa as flags
            delattr(pokemon, '_disabled_move')
            if hasattr(pokemon, '_disabled_turns'):
                delattr(pokemon, '_disabled_turns')
            if hasattr(pokemon, '_disabled_original_pp'):
                delattr(pokemon, '_disabled_original_pp')
            if hasattr(pokemon, '_disable_timer'):
                delattr(pokemon, '_disable_timer')

    def get_weather_type(self):
        """Retorna o tipo de clima atual"""
        if self.weather_manager and self.weather_manager.current_weather:
            return self.weather_manager.current_weather.type
        return None

    def is_weather_active(self, weather_type: WeatherType = None) -> bool:
        """Verifica se um clima está ativo"""
        if not self.weather_manager:
            return False
        return self.weather_manager.is_weather_active(weather_type)

    def apply_weather_effects(self, attacker, defender, move_info) -> dict:
        """
        Aplica os efeitos do clima no movimento.
        Retorna um dicionário com modificadores.
        """
        effects = {
            'damage_multiplier': 1.0,
            'accuracy_modifier': 1.0,
            'heal_modifier': 1.0,
            'is_immune': False,
            'message': None
        }

        if not self.weather_manager:
            return effects

        weather = self.weather_manager.current_weather
        if not weather or not weather.active:
            return effects

        move_type = move_info.get('type', '').lower()
        weather_boosted = False

        # ===== RAIN =====
        if weather.type.value == "rain":
            if move_type == 'water':
                effects['damage_multiplier'] = 1.5
                effects['message'] = "A chuva fortaleceu o ataque!"
                weather_boosted = True
            elif move_type == 'fire':
                effects['damage_multiplier'] = 0.5
                effects['message'] = "A chuva enfraqueceu o ataque!"
            elif move_type in ['solar_beam', 'solar_blade']:
                effects['damage_multiplier'] = 0.5
                effects['message'] = "A chuva enfraqueceu o ataque!"

        # ===== SUNNY =====
        elif weather.type.value == "sunny":
            if move_type == 'fire':
                effects['damage_multiplier'] = 1.5
                effects['message'] = "O sol forte fortaleceu o ataque!"
                weather_boosted = True
            elif move_type == 'water':
                effects['damage_multiplier'] = 0.5
                effects['message'] = "O sol forte enfraqueceu o ataque!"
            elif move_type in ['solar_beam', 'solar_blade']:
                effects['damage_multiplier'] = 1.5
                effects['message'] = "O sol forte carregou o ataque!"
                weather_boosted = True

        # ===== SANDSTORM =====
        elif weather.type.value == "sandstorm":
            if move_type in ['rock', 'ground', 'steel']:
                effects['damage_multiplier'] = 1.3
                effects['message'] = "A tempestade de areia fortaleceu o ataque!"
                weather_boosted = True

        # ===== CONQUISTAS: Ataque buffado pelo clima =====
        if weather_boosted and hasattr(self, 'game_scene') and self.game_scene:
            game_scene = self.game_scene
            if hasattr(game_scene, 'player') and hasattr(game_scene.player, 'achievement_manager'):
                player = game_scene.player
                phase_id = f"{game_scene.chapter_id}-{game_scene.phase_number}"

                # Incrementa contador de ataques buffados pelo clima
                player.achievement_manager.increment_counter("weather_boosted_attack_count")

                # Verifica conquista
                player.achievement_manager.check_and_unlock("first_weather_boosted_attack", phase_id)

                print(
                    f"[ACHIEVEMENT] Ataque buffado pelo clima #{player.achievement_manager.get_counter('weather_boosted_attack_count')}")

        return effects

    def register_attacker_for_enemy(self, attacker: 'Pokemon', enemy: 'Pokemon'):
        """Registra que um atacante atingiu um inimigo específico"""
        if not attacker or not enemy:
            return

        # Pula se for selvagem (inimigo atacando aliado não ganha XP)
        if attacker.is_wild:
            return

        # Pula se o inimigo já está morto
        if enemy.is_defeated or not enemy.is_alive():
            return

        # Inicializa o set de atacantes para este inimigo se não existir
        if not hasattr(enemy, '_attackers'):
            enemy._attackers = set()

        # Adiciona o ID do atacante
        enemy._attackers.add(id(attacker))
        print(f"[XP_TRACK] {attacker.name} atacou {enemy.name} - registrado")

    def get_attackers_for_enemy(self, enemy: 'Pokemon') -> list:
        """Retorna a lista de atacantes que atingiram este inimigo"""
        if not hasattr(enemy, '_attackers'):
            return []

        attackers = []
        for attacker_id in enemy._attackers:
            # Procura o Pokémon no time
            if hasattr(self, 'game_scene') and self.game_scene:
                if hasattr(self.game_scene, 'placement_manager'):
                    for ally in self.game_scene.placement_manager.placed_pokemon:
                        if id(ally) == attacker_id and ally.is_alive():
                            attackers.append(ally)
                            break

        return attackers

    def clear_enemy_attackers(self, enemy: 'Pokemon'):
        """Limpa a lista de atacantes de um inimigo"""
        if hasattr(enemy, '_attackers'):
            enemy._attackers.clear()