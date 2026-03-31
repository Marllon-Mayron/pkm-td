# src/entities/pokemon/combat.py
import math
import random
from typing import List, Optional


class PokemonCombat:
    """Gerencia combate do Pokémon"""

    def __init__(self, pokemon):
        self.pokemon = pokemon

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
        nearest = self.find_nearest_enemy(enemies)

        if nearest and self.pokemon.charge_cooldown <= 0:
            print(f"[COMBAT] {self.pokemon.name}: Encontrou inimigo {nearest.name}")
            self.pokemon.target = nearest
            self.pokemon.combat_state = "charging"

    def handle_charging_state(self, dt):
        """Estado indo em direção ao alvo - com suporte para ataques de status e especiais"""
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
        """Recebe dano e processa efeitos - SEM registrar contribuição (já registrado no pokemon.py)"""
        old_hp = self.pokemon.current_hp
        self.pokemon.current_hp = max(0, self.pokemon.current_hp - damage)

        if self.pokemon.current_hp > 0 and self.pokemon.current_hp <= self.pokemon.max_hp * 0.2:
            from src.managers.move_sound_manager import move_sound_manager
            move_sound_manager.play_attack_sound("low_hp")

        # REMOVIDO: registro de contribuição (já feito no pokemon.py)

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