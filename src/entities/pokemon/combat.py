# src/entities/pokemon/combat.py
import math
import random
from typing import List, Optional

from src.battle.effects import StatusType  # Adicione esta importação


class PokemonCombat:
    """Gerencia combate do Pokémon"""

    def __init__(self, pokemon):
        self.pokemon = pokemon

    def is_stunned(self) -> bool:
        """Verifica se o Pokémon está atordoado pela paralisia"""
        if hasattr(self.pokemon, 'effect_manager') and self.pokemon.effect_manager:
            status = self.pokemon.effect_manager.get_status(self.pokemon)
            if status and status.type == StatusType.PARALYSIS:
                return status.is_stunned()
        return False

    def update_stun(self, dt: float) -> bool:
        """Atualiza o estado de stun e retorna True se está atordoado"""
        if hasattr(self.pokemon, 'effect_manager') and self.pokemon.effect_manager:
            status = self.pokemon.effect_manager.get_status(self.pokemon)
            if status and status.type == StatusType.PARALYSIS:
                # Chama o update passando o pokemon
                result = status.update_paralysis(dt, self.pokemon)
                return result
        return False

    def is_asleep(self) -> bool:
        """Verifica se o Pokémon está dormindo"""
        if hasattr(self.pokemon, 'effect_manager') and self.pokemon.effect_manager:
            status = self.pokemon.effect_manager.get_status(self.pokemon)
            if status and status.type == StatusType.SLEEP:
                return status.is_asleep()
        return False

    def update_sleep(self, dt: float) -> bool:
        """Atualiza o estado de sono e retorna True se ainda está dormindo"""
        if hasattr(self.pokemon, 'effect_manager') and self.pokemon.effect_manager:
            status = self.pokemon.effect_manager.get_status(self.pokemon)
            if status and status.type == StatusType.SLEEP:
                # O update já gerencia o timer e retorno
                return status.update_sleep(dt)
        return False

    def is_frozen(self) -> bool:
        """Verifica se o Pokémon está congelado"""
        if hasattr(self.pokemon, 'effect_manager') and self.pokemon.effect_manager:
            status = self.pokemon.effect_manager.get_status(self.pokemon)
            if status and status.type == StatusType.FREEZE:
                return status.is_frozen()
        return False

    def update_freeze(self, dt: float) -> bool:
        """Atualiza o estado de congelamento e retorna True se ainda está congelado"""
        if hasattr(self.pokemon, 'effect_manager') and self.pokemon.effect_manager:
            status = self.pokemon.effect_manager.get_status(self.pokemon)
            if status and status.type == StatusType.FREEZE:
                return status.update_freeze(dt)
        return False

    def thaw(self):
        """Descongela o Pokémon (usado por ataques de fogo)"""
        if hasattr(self.pokemon, 'effect_manager') and self.pokemon.effect_manager:
            status = self.pokemon.effect_manager.get_status(self.pokemon)
            if status and status.type == StatusType.FREEZE:
                return status.thaw()
        return False

    def find_nearest_enemy(self, enemies: List) -> Optional['Pokemon']:
        """Encontra o inimigo mais próximo"""
        if not enemies:
            return None

        nearest = None
        min_distance = float('inf')
        attack_range_sq = self.pokemon.attack_range * self.pokemon.attack_range

        for enemy in enemies:
            if enemy.is_alive() and enemy.is_wild:
                dx = self.pokemon.x - enemy.x
                dy = self.pokemon.y - enemy.y
                distance_sq = dx * dx + dy * dy

                if distance_sq < attack_range_sq and distance_sq < min_distance:
                    min_distance = distance_sq
                    nearest = enemy

        return nearest

    def handle_idle_state(self, dt, enemies):
        """Estado parado - procura inimigo"""

        # ===== VERIFICA STUN =====
        if self.update_stun(dt):
            return

        # ===== VERIFICA SONO =====
        if self.update_sleep(dt):
            # Está dormindo - não faz nada
            return

        # ===== VERIFICA CONGELAMENTO =====
        if self.is_frozen():
            if self.update_freeze(dt):
                # Congelado - não procura inimigo
                return

        nearest = self.find_nearest_enemy(enemies)

        if nearest and self.pokemon.charge_cooldown <= 0:
            print(f"[COMBAT] {self.pokemon.name}: Encontrou inimigo {nearest.name}")
            self.pokemon.target = nearest
            self.pokemon.combat_state = "charging"

    def handle_charging_state(self, dt):
        """Estado indo em direção ao alvo - com suporte para ataques de status e especiais"""

        # ===== VERIFICA STUN =====
        if self.update_stun(dt):
            # Se estava carregando e foi atordoado, volta para idle
            self.pokemon.combat_state = "idle"
            self.pokemon.target = None
            return

        # ===== VERIFICA SONO =====
        if self.update_sleep(dt):
            self.pokemon.combat_state = "idle"
            self.pokemon.target = None
            return

        # ===== VERIFICA CONGELAMENTO =====
        if self.is_frozen():
            if self.update_freeze(dt):
                return

        if not self.pokemon.target or not self.pokemon.target.is_alive():
            self.pokemon.combat_state = "returning"
            self.pokemon.target = None
            return

        current_move = self.pokemon.get_current_move()
        if not current_move or current_move.current_pp <= 0:
            print(f"[COMBAT] {self.pokemon.name} está sem PP!")
            self.pokemon.combat_state = "returning"
            self.pokemon.target = None
            self.pokemon.has_no_pp = True
            return

        is_status_move = current_move.category == "status"
        is_special_move = current_move.category == "special"

        if is_status_move or is_special_move:
            attack_type = "status" if is_status_move else "especial"
            print(f"[COMBAT] {self.pokemon.name} usou {current_move.name} ({attack_type}) à distância!")

            # ===== TOCAR ANIMAÇÃO DE ATAQUE =====
            self._play_attack_animation(current_move.name)

            if self.pokemon.battle_system:
                self.pokemon.battle_system.attempt_attack(self.pokemon, self.pokemon.target)
            else:
                hit_chance = current_move.accuracy / 100
                will_hit = random.random() <= hit_chance
                if will_hit:
                    self.perform_charge_attack(self.pokemon.target)
                else:
                    print(f"[COMBAT] {current_move.name} errou!")
                    self.show_miss_on_self()
                current_move.current_pp -= 1

            self.pokemon.combat_state = "returning"
            self.pokemon.charge_cooldown = self.pokemon.charge_cooldown_max
            return

        # Para ataques físicos, move em direção ao alvo
        dx = self.pokemon.target.x - self.pokemon.x
        dy = self.pokemon.target.y - self.pokemon.y
        distance = math.sqrt(dx * dx + dy * dy)

        if distance < 8:
            # ===== TOCAR ANIMAÇÃO DE ATAQUE FÍSICO =====
            self._play_attack_animation(current_move.name)

            if self.pokemon.battle_system:
                self.pokemon.battle_system.attempt_attack(self.pokemon, self.pokemon.target)
            else:
                hit_chance = current_move.accuracy / 100
                will_hit = random.random() <= hit_chance
                if will_hit:
                    self.perform_charge_attack(self.pokemon.target)
                else:
                    print(f"[COMBAT] {current_move.name} errou!")
                    self.show_miss_on_self()
                current_move.current_pp -= 1

            self.pokemon.combat_state = "returning"
            self.pokemon.charge_cooldown = self.pokemon.charge_cooldown_max
            return

        if distance > 0:
            move_distance = self.pokemon.move_speed * dt * 60
            move_x = (dx / distance) * move_distance
            move_y = (dy / distance) * move_distance

            if abs(move_x) > abs(dx):
                move_x = dx
            if abs(move_y) > abs(dy):
                move_y = dy

            self.pokemon.x += move_x
            self.pokemon.y += move_y
            self.pokemon.rect.x, self.pokemon.rect.y = self.pokemon.x, self.pokemon.y

            self._update_direction_for_angle(dx, dy)

    def _play_attack_animation(self, move_name: str):
        """Toca a animação de ataque uma única vez"""
        from src.battle.effects.effect_factory import EffectFactory

        effect = EffectFactory.create_effect(move_name)
        if effect and effect.attacker_animation:
            # Verifica distância mínima
            if effect.min_distance > 0:
                if self.pokemon.target:
                    dx = self.pokemon.target.x - self.pokemon.x
                    dy = self.pokemon.target.y - self.pokemon.y
                    distance = math.sqrt(dx * dx + dy * dy)
                    if distance > effect.min_distance:
                        return

            if self.pokemon.has_animation(effect.attacker_animation):
                # Salva animação atual
                self.pokemon._saved_animation_before_attack = self.pokemon.current_animation
                # Toca animação de ataque
                self.pokemon.set_animation_direct(effect.attacker_animation)
                # Reseta para o início
                self.pokemon.current_frame = 0
                self.pokemon.animation_timer = 0
                # Marca que está em animação de ataque
                self.pokemon._attack_animation_active = True
                print(f"[ANIM] {self.pokemon.name} usou animação {effect.attacker_animation} para {move_name}")

    def _update_direction_for_angle(self, dx, dy):
        """Atualiza direção baseada no ângulo (8 direções)"""
        angle = math.atan2(dy, dx)
        if angle >= -math.pi / 8 and angle < math.pi / 8:
            self.pokemon.current_direction = "right"
        elif angle >= math.pi / 8 and angle < 3 * math.pi / 8:
            self.pokemon.current_direction = "down-right"
        elif angle >= 3 * math.pi / 8 and angle < 5 * math.pi / 8:
            self.pokemon.current_direction = "down"
        elif angle >= 5 * math.pi / 8 and angle < 7 * math.pi / 8:
            self.pokemon.current_direction = "down-left"
        elif angle >= 7 * math.pi / 8 or angle < -7 * math.pi / 8:
            self.pokemon.current_direction = "left"
        elif angle >= -7 * math.pi / 8 and angle < -5 * math.pi / 8:
            self.pokemon.current_direction = "up-left"
        elif angle >= -5 * math.pi / 8 and angle < -3 * math.pi / 8:
            self.pokemon.current_direction = "up"
        else:
            self.pokemon.current_direction = "up-right"

    def handle_returning_state(self, dt):
        """Estado voltando para posição original"""

        # ===== VERIFICA STUN =====
        if self.update_stun(dt):
            return  # Atordoado, não se move

        # ===== VERIFICA SONO =====
        if self.update_sleep(dt):
            return

        dx = self.pokemon.original_spot_x - self.pokemon.x
        dy = self.pokemon.original_spot_y - self.pokemon.y
        distance = math.sqrt(dx * dx + dy * dy)

        if distance < 5:
            self.pokemon.x, self.pokemon.y = self.pokemon.original_spot_x, self.pokemon.original_spot_y
            self.pokemon.rect.x, self.pokemon.rect.y = self.pokemon.x, self.pokemon.y
            self.pokemon.combat_state = "idle"
            self.pokemon.target = None
            return

        if distance > 0:
            move_distance = self.pokemon.move_speed * dt * 60
            move_x = (dx / distance) * move_distance
            move_y = (dy / distance) * move_distance

            if abs(move_x) > abs(dx):
                move_x = dx
            if abs(move_y) > abs(dy):
                move_y = dy

            self.pokemon.x += move_x
            self.pokemon.y += move_y
            self.pokemon.rect.x, self.pokemon.rect.y = self.pokemon.x, self.pokemon.y

            if abs(dx) > abs(dy):
                self.pokemon.current_direction = "right" if dx > 0 else "left"
            else:
                self.pokemon.current_direction = "down" if dy > 0 else "up"

    def perform_charge_attack(self, target):
        """Ataque de carga - usa o sistema de moves"""
        current_move = self.pokemon.get_current_move()
        if not current_move or current_move.current_pp <= 0:
            print(f"[ATTACK] {self.pokemon.name} não pode atacar - sem PP!")
            self.pokemon.combat_state = "returning"
            self.pokemon.target = None
            return

        if self.pokemon.battle_system:
            success = self.pokemon.battle_system.attempt_attack(self.pokemon, target)
            if success:
                print(
                    f"[ATTACK] {self.pokemon.name} usou {current_move.name if current_move else 'ataque'} em {target.name}!")
                return

        # Fallback: ataque simples
        print(f"[ATTACK] {self.pokemon.name}: Ataque simples em {target.name}!")
        base_damage = self.pokemon.attack_damage * (self.pokemon.level / 8)
        damage_multiplier = random.uniform(0.85, 1.15)
        damage = int(base_damage * damage_multiplier)

        defense_factor = max(0.4, 1.0 - (target.defense_value / 800))
        final_damage = max(2, int(damage * defense_factor))

        target.take_damage(final_damage, attacker=self.pokemon)

    def show_miss_on_self(self):
        """Mostra o texto MISS no próprio Pokémon (atacante)"""
        self.pokemon.miss_timer = 0.6

    def take_damage(self, damage, attacker=None):
        """Recebe dano"""
        old_hp = self.pokemon.current_hp
        self.pokemon.current_hp = max(0, self.pokemon.current_hp - damage)

        if self.pokemon.current_hp > 0 and self.pokemon.current_hp <= self.pokemon.max_hp * 0.2:
            from src.managers.move_sound_manager import move_sound_manager
            move_sound_manager.play_attack_sound("low_hp")

        if self.pokemon.current_hp <= 0:
            from src.managers.move_sound_manager import move_sound_manager
            move_sound_manager.play_attack_sound("faint")
            print(f"[BATTLE] {self.pokemon.name} foi derrotado!")

            if self.pokemon.is_carrying:
                carried_item = self.pokemon.is_carrying
                print(f"[ITEM] {carried_item.item_name} será liberado com a morte de {self.pokemon.name}")
                carried_item.reset_capture()
                carried_item.is_protected = True
                carried_item.is_stolen = False
                carried_item.carried_by = None
                self.pokemon.is_carrying = None

        return self.pokemon.current_hp <= 0