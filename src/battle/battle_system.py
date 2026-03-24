# src/battle/battle_system.py
from src.battle.damage_calculator import DamageCalculator
from src.battle.projectile import Projectile

from typing import List

from src.entities.pokemon import Pokemon


class BattleSystem:
    """Gerencia combate entre Pokémon usando moves"""

    def __init__(self, game_scene=None):
        self.game_scene = game_scene
        self.projectiles: List[Projectile] = []

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
            # Adicionar flag para indicar que o Pokémon está sem PP
            attacker.has_no_pp = True
            return False

        # Se tem PP, limpa a flag
        attacker.has_no_pp = False
        # ===== ATAQUES DE STATUS =====
        if move.category == "status":
            print(f"[BATTLE] {attacker.name} usou {move.name}! (Efeito de status)")
            move.current_pp -= 1
            attacker.attack_cooldown = max(0.3, 1.0 - (attacker.speed_stat / 500))
            self._apply_status(attacker, target, move)
            return True

        # ===== ATAQUES QUE CAUSAM DANO =====
        # Calcular dano
        damage_result = DamageCalculator.calculate_damage(attacker, target, move)

        if not damage_result["hit"]:
            # Move errou
            move.current_pp -= 1
            attacker.attack_cooldown = max(0.3, 1.0 - (attacker.speed_stat / 500))
            print(f"[BATTLE] {attacker.name} usou {move.name} e errou!")
            return True

        # Consome PP
        move.current_pp -= 1

        # ===== ATAQUES ESPECIAIS (criam projétil) =====
        if move.category == "special" and move.power > 0:
            print(f"[BATTLE] {attacker.name} usou {move.name}! (Ataque especial)")
            self._create_projectile(attacker, target, move, damage_result)
            attacker.attack_cooldown = max(0.3, 1.0 - (attacker.speed_stat / 500))
            return True

        # ===== ATAQUES FÍSICOS (dano imediato) =====
        elif move.category == "physical" and move.power > 0:
            print(f"[BATTLE] {attacker.name} usou {move.name}! (Ataque físico)")
            self._apply_damage(attacker, target, damage_result, move)
            attacker.attack_cooldown = max(0.3, 1.0 - (attacker.speed_stat / 500))
            return True

        # ===== FALLBACK: qualquer outro caso =====
        else:
            print(f"[BATTLE] {attacker.name} usou {move.name}!")
            attacker.attack_cooldown = max(0.3, 1.0 - (attacker.speed_stat / 500))
            return True

    def _create_projectile(self, attacker: 'Pokemon', target: 'Pokemon', move, damage_result: dict):
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
            speed=projectile_speed
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
        # Para ataques especiais: o projétil já tocou o som do atacante,
        # aqui toca só o som do impacto
        if move.category == "physical":
            # Toca som do atacante
            move_sound_manager.play_attack_sound(move.sound_name)
            print(f"[SOM] {move.name} (físico) - som do atacante: {move.sound_name}")

        # Toca som de impacto (do alvo)
        move_sound_manager.play_hit_sound(move.sound_name)
        print(f"[SOM] {move.name} - som de impacto: {move.sound_name}_target")

        # Aplica dano
        target.take_damage(damage, attacker=attacker)

        # Registrar contribuição de dano
        attacker_id = id(attacker)
        target.damage_contributions[attacker_id] = target.damage_contributions.get(attacker_id, 0) + damage

        # Mensagens de log
        if damage_result.get("stab"):
            print(f"[BATTLE] {attacker.name} usou {move.name}! (STAB)")

        if damage_result["message"]:
            print(f"[BATTLE] {damage_result['message']}")

        print(f"[BATTLE] Causou {damage} de dano a {target.name}!")

        if not target.is_alive():
            print(f"[BATTLE] {target.name} foi derrotado!")

    def _apply_status(self, attacker: 'Pokemon', target: 'Pokemon', move):
        """Aplica efeito de status ao alvo"""

        from src.managers.move_sound_manager import move_sound_manager

        print(f"[DEBUG STATUS] Move: {move.name}")
        print(f"[DEBUG STATUS] move.sound_name: {move.sound_name}")

        # Toca som do atacante
        move_sound_manager.play_attack_sound(move.sound_name)
        print(f"[SOM] {move.name} (status) - som do atacante: {move.sound_name}")

        # Tenta tocar som de impacto APENAS se existir um som específico
        # use_fallback=False impede de usar o som padrão (tackle_target)
        result = move_sound_manager.play_hit_sound(move.sound_name, use_fallback=False)
        print(f"[DEBUG STATUS] Resultado do play_hit_sound: {result}")

        print(f"[BATTLE] {attacker.name} usou {move.name}!")


    def render_projectiles(self, screen, camera, screen_manager):
        """Renderiza projéteis"""
        for projectile in self.projectiles:
            projectile.render(screen, camera, screen_manager)