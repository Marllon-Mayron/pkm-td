# src/battle/battle_system.py
import random

from src.battle.effects.residual_effect import ResidualEffectManager
from src.battle.damage_calculator import DamageCalculator
from src.battle.effects import EffectManager, EffectTiming, StatType, StatusType
from src.battle.projectile import Projectile

from typing import List

from src.entities.pokemon import Pokemon


class BattleSystem:
    """Gerencia combate entre Pokémon usando moves"""

    def __init__(self, game_scene=None):
        self.game_scene = game_scene
        self.projectiles: List[Projectile] = []
        self.effect_manager = EffectManager()
        self.active_multi_hit = None  # Estado do multi-hit ativo
        self.residual_effects = ResidualEffectManager(self)

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

        # Atualiza multi-hit ativo
        if self.active_multi_hit:
            still_active = self.active_multi_hit.update(dt)
            if not still_active:
                self.active_multi_hit = None

        self.residual_effects.update(dt)

    def attempt_attack(self, attacker: 'Pokemon', target: 'Pokemon') -> bool:
        """Tenta realizar um ataque com o move atual do atacante"""
        # Se já tem um multi-hit ativo, não permite novo ataque
        if self.active_multi_hit:
            print(f"[BATTLE] Aguardando término do multi-hit...")
            return False

        # Se o atacante está derrotado, não ataca
        if attacker.is_defeated:
            print(f"[BATTLE] {attacker.name} está derrotado e não pode atacar!")
            return False

        # Se o alvo está derrotado, não pode ser atacado
        if target.is_defeated:
            print(f"[BATTLE] {target.name} está derrotado e não pode ser atacado!")
            return False

        # Usa o padrão de ataque do Pokémon (se existir)
        if hasattr(attacker, 'get_current_move_for_pattern'):
            move = attacker.get_current_move_for_pattern()
        else:
            move = attacker.get_current_move()

        if not move:
            print(f"[BATTLE] {attacker.name} não tem move selecionado!")
            return False

        # Verificar PP
        if move.current_pp <= 0:
            print(f"[BATTLE] {attacker.name} não tem PP para {move.name}!")
            attacker.has_no_pp = True
            return False

        attacker.has_no_pp = False

        # ===== VERIFICA CONFUSÃO ANTES DE ATACAR =====
        # A confusão é verificada ANTES de qualquer outra condição
        if self.effect_manager.is_confused(attacker):
            confusion = self.effect_manager.get_confusion(attacker)
            result = confusion.before_attack(attacker, target, self, self.effect_manager)

            if result == "self":
                # Ataca a si mesmo
                self._apply_confusion_self_damage(attacker, confusion)
                attacker.attack_cooldown = max(0.3, 1.0 - (attacker.speed_stat / 500))
                return True

            # Se confusão acabou durante before_attack, remove automaticamente
            if not confusion.is_active():
                self.effect_manager.remove_confusion(attacker)

        # ===== DESCONGELAMENTO POR ATAQUES DE FOGO =====
        target_status = self.effect_manager.get_status(target)
        if target_status and target_status.type == StatusType.FREEZE:
            if move.type.lower() == "fire":
                # Ataque de fogo descongela o alvo
                target_status.thaw()
                self.effect_manager.add_status_text(target, f"{target.name} descongelou com o calor!")
                print(f"[FREEZE] {target.name} descongelou devido ao ataque de fogo {move.name}!")

        # ===== VERIFICA SE O ATACANTE PODE AGIR =====
        status = self.effect_manager.get_status(attacker)

        # Atualiza o estado de paralisia antes de verificar
        if status and status.type == StatusType.PARALYSIS:
            status.update_paralysis(0)

        # Verifica se o atacante está impossibilitado de agir
        if status and not status.can_attack():
            if status.type == StatusType.PARALYSIS:
                self.effect_manager.add_status_text(attacker,
                                                    f"{attacker.name} está paralisado e não consegue se mover!")
                print(f"[BATTLE] {attacker.name} está paralisado e não consegue se mover!")
            elif status.type == StatusType.SLEEP:
                self.effect_manager.add_status_text(attacker, f"{attacker.name} está dormindo!")
                print(f"[BATTLE] {attacker.name} está dormindo e não pode atacar!")
            elif status.type == StatusType.FREEZE:
                self.effect_manager.add_status_text(attacker, f"{attacker.name} está congelado!")
                print(f"[BATTLE] {attacker.name} está congelado e não pode atacar!")
            else:
                self.effect_manager.add_status_text(attacker, f"{attacker.name} não pode atacar!")
                print(f"[BATTLE] {attacker.name} está {status.name.lower()} e não pode atacar!")
            attacker.attack_cooldown = max(0.3, 1.0 - (attacker.speed_stat / 500))
            return True

        # ===== VERIFICAÇÃO ESPECÍFICA PARA STATUS MOVES =====
        if move.category == "status":
            target_status = self.effect_manager.get_status(target)

            is_status_applying_move = self._is_status_applying_move(move.name)

            if is_status_applying_move and target_status and target_status.type != StatusType.NONE:
                move.current_pp -= 1
                attacker.attack_cooldown = max(0.3, 1.0 - (attacker.speed_stat / 500))
                self._show_miss_on_attacker(attacker)
                return True

        # Calcular acerto
        hit_chance = move.accuracy / 100
        accuracy_mult = self.effect_manager.get_stat_multiplier(attacker, StatType.ACCURACY)
        evasion_mult = self.effect_manager.get_stat_multiplier(target, StatType.EVASION)
        hit_chance = hit_chance * accuracy_mult / evasion_mult
        hit_chance = max(0.01, min(1.0, hit_chance))

        will_hit = random.random() <= hit_chance

        # Ataques de status (que aplicam efeitos como veneno, queimadura, etc)
        if move.category == "status":
            print(f"[BATTLE] {attacker.name} usou {move.name}! (Efeito de status)")

            from src.managers.move_sound_manager import move_sound_manager
            move_sound_manager.play_attack_sound(move.sound_name)

            move.current_pp -= 1
            attacker.attack_cooldown = max(0.3, 1.0 - (attacker.speed_stat / 500))

            if will_hit:
                self._apply_status_effect(attacker, target, move)
            else:
                print(f"[BATTLE] {move.name} errou!")
                self._show_miss_on_attacker(attacker)
            return True

        # Calcular dano
        if will_hit:
            damage_result = self._calculate_move_damage(attacker, target, move)
        else:
            damage_result = {
                "damage": 0,
                "effectiveness": 1.0,
                "hit": False,
                "message": f"O ataque errou!",
                "stab": False
            }

        # Ataques especiais (usam projétil)
        if move.category == "special" and move.power > 0:
            print(f"[BATTLE] {attacker.name} usou {move.name}! (Ataque especial)")
            move.current_pp -= 1

            # Cria o projétil e passa o efeito para ser aplicado no impacto
            self._create_projectile(attacker, target, move, damage_result, will_hit)
            attacker.attack_cooldown = max(0.3, 1.0 - (attacker.speed_stat / 500))

            return True

        # Ataques físicos
        elif move.category == "physical" and move.power > 0:
            print(f"[BATTLE] {attacker.name} usou {move.name}! (Ataque físico)")

            from src.managers.move_sound_manager import move_sound_manager
            move_sound_manager.play_attack_sound(move.sound_name)

            move.current_pp -= 1
            if will_hit:
                self._apply_damage(attacker, target, damage_result, move)
                # Aplica efeitos do move APÓS o dano
                self._apply_move_effect(attacker, target, move, damage_result["damage"])
            else:
                print(f"[BATTLE] {move.name} errou!")
                self._show_miss_on_attacker(attacker)
            attacker.attack_cooldown = max(0.3, 1.0 - (attacker.speed_stat / 500))
            return True

        # Fallback
        else:
            print(f"[BATTLE] {attacker.name} usou {move.name}!")
            move.current_pp -= 1
            attacker.attack_cooldown = max(0.3, 1.0 - (attacker.speed_stat / 500))
            return True

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

        from src.managers.move_sound_manager import move_sound_manager

        move_sound_manager.play_attack_sound(move.sound_name)
        print(f"[SOM] {move.name} - som do atacante: {move.sound_name}")

    def _apply_damage(self, attacker: 'Pokemon', target: 'Pokemon', damage_result: dict, move):
        """
        Aplica dano a um alvo

        Args:
            attacker: Pokémon atacante
            target: Pokémon alvo
            damage_result: Resultado do cálculo de dano (contém damage, effectiveness, critical, etc)
            move: Movimento usado
        """
        damage = damage_result["damage"]

        # Verifica se o movimento é inefetivo (imune)
        if damage_result["effectiveness"] == 0:
            print(f"[BATTLE] {move.name} não afeta {target.name}!")
            self.effect_manager.add_status_text(target, "Não afeta!", duration=1.0)
            return

        from src.managers.move_sound_manager import move_sound_manager

        # Toca som do ataque (físico)
        if move.category == "physical":
            move_sound_manager.play_attack_sound(move.sound_name)
            print(f"[SOM] {move.name} (físico) - som do atacante: {move.sound_name}")

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

    def _apply_confusion_self_damage(self, attacker, confusion):
        """Aplica dano de confusão (atacante se machuca)"""
        damage = confusion.calculate_self_damage(attacker)

        # Toca som de dano
        from src.managers.move_sound_manager import move_sound_manager
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
        """Calcula dano do move com modificadores de stat"""
        damage_result = DamageCalculator.calculate_damage(attacker, target, move)

        if not damage_result["hit"]:
            return damage_result

        from src.battle.effects import StatType

        if move.category == "physical":
            atk_mult = self.effect_manager.get_stat_multiplier(attacker, StatType.ATTACK)
            def_mult = self.effect_manager.get_stat_multiplier(target, StatType.DEFENSE)
            print(f"[DAMAGE] {attacker.name} atk_mult={atk_mult:.2f}, {target.name} def_mult={def_mult:.2f}")
            damage_result["damage"] = int(damage_result["damage"] * atk_mult / def_mult)
        else:
            sp_atk_mult = self.effect_manager.get_stat_multiplier(attacker, StatType.SP_ATTACK)
            sp_def_mult = self.effect_manager.get_stat_multiplier(target, StatType.SP_DEFENSE)
            print(
                f"[DAMAGE] {attacker.name} sp_atk_mult={sp_atk_mult:.2f}, {target.name} sp_def_mult={sp_def_mult:.2f}")
            damage_result["damage"] = int(damage_result["damage"] * sp_atk_mult / sp_def_mult)

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

    def render_projectiles(self, screen, camera, screen_manager):
        """Renderiza projéteis"""
        for projectile in self.projectiles:
            projectile.render(screen, camera, screen_manager)

    def clear_all_effects(self):
        """Limpa todos os efeitos (usado quando batalha termina)"""
        self.residual_effects.clear_all()
        self.effect_manager.clear_all()