# src/battle/battle_system.py
import random
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

    def set_effect_manager_for_pokemon(self, pokemon):
        """Vincula o effect_manager a um Pokémon e registra"""
        pokemon.effect_manager = self.effect_manager
        self.effect_manager.register_pokemon(pokemon)  # Adicione esta linha
        print(f"[BATTLE] EffectManager vinculado a {pokemon.name} (id={id(pokemon)})")

    def update(self, dt: float):
        """Atualiza projéteis ativos"""
        for projectile in self.projectiles[:]:
            projectile.update(dt)
            if projectile.is_finished:
                self.projectiles.remove(projectile)

    def attempt_attack(self, attacker: 'Pokemon', target: 'Pokemon') -> bool:
        """Tenta realizar um ataque com o move atual do atacante"""
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

        # Verifica status do atacante
        status = self.effect_manager.get_status(attacker)

        # Atualiza o estado de paralisia antes de verificar
        if status and status.type == StatusType.PARALYSIS:
            status.update_paralysis(0)

        # Verifica se pode atacar (stun da paralisia)
        if status and not status.can_attack():
            if status.type == StatusType.PARALYSIS:
                self.effect_manager.add_status_text(attacker,
                                                    f"{attacker.name} está paralisado e não consegue se mover!")
                print(f"[BATTLE] {attacker.name} está paralisado e não consegue se mover!")
            else:
                self.effect_manager.add_status_text(attacker, f"{attacker.name} não pode atacar!")
                print(f"[BATTLE] {attacker.name} está {status.name.lower()} e não pode atacar!")
            attacker.attack_cooldown = max(0.3, 1.0 - (attacker.speed_stat / 500))
            return True

        # ===== VERIFICAÇÃO PARA ATAQUES DE STATUS =====
        # Se for um ataque de status, verifica se o alvo já tem um status
        if move.category == "status":
            target_status = self.effect_manager.get_status(target)

            # Se o alvo já tem algum status (exceto NONE), o ataque sempre erra
            if target_status and target_status.type != StatusType.NONE:
                # Consome PP mesmo errando
                move.current_pp -= 1
                attacker.attack_cooldown = max(0.3, 1.0 - (attacker.speed_stat / 500))

                # MOSTRA MISS NO ATACANTE (quem usou o golpe)
                self._show_miss_on_attacker(attacker)
                return True

        # ===== CALCULAR ACERTO PRIMEIRO =====
        hit_chance = move.accuracy / 100

        # Modificadores de acerto (evasão, etc)
        accuracy_mult = self.effect_manager.get_stat_multiplier(attacker, StatType.ACCURACY)
        evasion_mult = self.effect_manager.get_stat_multiplier(target, StatType.EVASION)
        hit_chance = hit_chance * accuracy_mult / evasion_mult
        hit_chance = max(0.01, min(1.0, hit_chance))

        will_hit = random.random() <= hit_chance

        # ===== ATAQUES DE STATUS =====
        if move.category == "status":
            print(f"[BATTLE] {attacker.name} usou {move.name}! (Efeito de status)")

            # Toca o som do atacante
            from src.managers.move_sound_manager import move_sound_manager
            move_sound_manager.play_attack_sound(move.sound_name)

            # Consome PP
            move.current_pp -= 1
            attacker.attack_cooldown = max(0.3, 1.0 - (attacker.speed_stat / 500))

            if will_hit:
                self._apply_status_effect(attacker, target, move)
            else:
                print(f"[BATTLE] {move.name} errou!")
                self._show_miss_on_attacker(attacker)  # MISS no atacante
            return True

        # ===== ATAQUES QUE CAUSAM DANO =====
        # Calcular dano base (já com modificadores de stat)
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

        # ===== ATAQUES ESPECIAIS =====
        if move.category == "special" and move.power > 0:
            print(f"[BATTLE] {attacker.name} usou {move.name}! (Ataque especial)")
            move.current_pp -= 1
            self._create_projectile(attacker, target, move, damage_result, will_hit)
            attacker.attack_cooldown = max(0.3, 1.0 - (attacker.speed_stat / 500))

            # Aplica efeitos do move (se houver)
            if will_hit and damage_result["damage"] > 0:
                self._apply_move_effect(attacker, target, move, damage_result["damage"])

            return True

        # ===== ATAQUES FÍSICOS =====
        elif move.category == "physical" and move.power > 0:
            print(f"[BATTLE] {attacker.name} usou {move.name}! (Ataque físico)")

            from src.managers.move_sound_manager import move_sound_manager
            move_sound_manager.play_attack_sound(move.sound_name)

            move.current_pp -= 1
            if will_hit:
                self._apply_damage(attacker, target, damage_result, move)
                # Aplica efeitos do move
                self._apply_move_effect(attacker, target, move, damage_result["damage"])
            else:
                print(f"[BATTLE] {move.name} errou!")
                self._show_miss_on_attacker(attacker)  # MISS no atacante
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
        # Inicia o timer para mostrar o texto MISS
        if not hasattr(attacker, 'miss_timer'):
            attacker.miss_timer = 0.0
        attacker.miss_timer = 0.6  # 0.6 segundos de duração

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
            will_hit=will_hit  # Passa se o ataque acertou ou não
        )
        self.projectiles.append(projectile)

        from src.managers.move_sound_manager import move_sound_manager

        # Toca os sons do move (atacante e alvo)
        # Para ataques especiais, o som do impacto será quando o projétil atingir
        # Então aqui só tocamos o som do atacante
        move_sound_manager.play_attack_sound(move.sound_name)
        print(f"[SOM] {move.name} - som do atacante: {move.sound_name}")

    def _apply_damage(self, attacker: 'Pokemon', target: 'Pokemon', damage_result: dict, move):
        """Aplica dano a um alvo"""
        damage = damage_result["damage"]

        if damage_result["effectiveness"] == 0:
            print(f"[BATTLE] {move.name} não afeta {target.name}!")
            return

        from src.managers.move_sound_manager import move_sound_manager

        # Para ataques físicos: toca som do atacante E do impacto
        if move.category == "physical":
            move_sound_manager.play_attack_sound(move.sound_name)
            print(f"[SOM] {move.name} (físico) - som do atacante: {move.sound_name}")

        # Toca som de impacto (do alvo)
        move_sound_manager.play_hit_sound(move.sound_name)
        print(f"[SOM] {move.name} - som de impacto: {move.sound_name}_target")

        # Aplica dano
        target.take_damage(damage, attacker=attacker)

    def _calculate_move_damage(self, attacker, target, move):
        """Calcula dano do move com modificadores de stat - VERSÃO COM LOGS"""
        # Calcula dano base
        damage_result = DamageCalculator.calculate_damage(attacker, target, move)

        if not damage_result["hit"]:
            return damage_result

        # Aplica modificadores de stat
        from src.battle.effects import StatType

        if move.category == "physical":
            atk_mult = self.effect_manager.get_stat_multiplier(attacker, StatType.ATTACK)
            def_mult = self.effect_manager.get_stat_multiplier(target, StatType.DEFENSE)
            print(f"[DAMAGE] {attacker.name} atk_mult={atk_mult:.2f}, {target.name} def_mult={def_mult:.2f}")
            damage_result["damage"] = int(damage_result["damage"] * atk_mult / def_mult)
        else:  # special
            sp_atk_mult = self.effect_manager.get_stat_multiplier(attacker, StatType.SP_ATTACK)
            sp_def_mult = self.effect_manager.get_stat_multiplier(target, StatType.SP_DEFENSE)
            print(
                f"[DAMAGE] {attacker.name} sp_atk_mult={sp_atk_mult:.2f}, {target.name} sp_def_mult={sp_def_mult:.2f}")
            damage_result["damage"] = int(damage_result["damage"] * sp_atk_mult / sp_def_mult)

        # Aplica efeito de queimadura (reduz ataque físico)
        if move.category == "physical":
            status = self.effect_manager.get_status(attacker)
            if status and status.type == StatusType.BURN:
                damage_result["damage"] = int(damage_result["damage"] * 0.5)
                self.effect_manager.add_status_text(attacker, "Ataque reduzido pela queimadura!")

        return damage_result

    def _apply_status_effect(self, attacker, target, move):
        """Aplica efeito de status do move"""
        from src.battle.effects import EffectFactory

        effect = EffectFactory.create_effect(move.name)
        if effect:
            effect.execute(attacker, target, self, self.effect_manager)
            # REGISTRA CONTRIBUIÇÃO DE STATUS
            target.register_status_application(attacker, move.name)
        else:
            print(f"[BATTLE] {attacker.name} usou {move.name}! (Efeito de status)")
            self.effect_manager.add_status_text(target, f"{move.name} usado!")

    def _apply_move_effect(self, attacker, target, move, damage):
        """Aplica efeitos especiais do move (multi-hit, flinch, etc)"""
        from src.battle.effects import EffectFactory

        effect = EffectFactory.create_effect(move.name)
        if effect:
            # Executa o efeito no timing apropriado
            if effect.timing == EffectTiming.AFTER_DAMAGE:
                effect.execute(attacker, target, self, self.effect_manager, damage)
            elif effect.timing == EffectTiming.ON_HIT:
                effect.execute(attacker, target, self, self.effect_manager, damage)


    def render_projectiles(self, screen, camera, screen_manager):
        """Renderiza projéteis"""
        for projectile in self.projectiles:
            projectile.render(screen, camera, screen_manager)