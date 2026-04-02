# src/entities/pokemon/movement.py
import math
from typing import Tuple, List, Optional

from src.battle.effects import StatusType  # Adicione esta importação


class PokemonMovement:
    """Gerencia movimento e path do Pokémon"""

    def __init__(self, pokemon):
        self.pokemon = pokemon

    def update_move_speed_from_effects(self):
        """Atualiza a velocidade de movimento baseada nos efeitos atuais"""
        if not self.pokemon.is_wild:
            return

        new_speed = self.pokemon.stats.calculate_wild_move_speed()
        self.pokemon.move_speed = new_speed
        print(f"[SPEED] {self.pokemon.name} velocidade atualizada: {self.pokemon.move_speed:.2f}")

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
                return status.update_paralysis(dt)
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

    def update_movement(self, dt, items=None):
        """Movimento via path (para aliados ou inimigos sem wave control)"""

        # ===== VERIFICA CONGELAMENTO (MAIS PRIORITÁRIO) =====
        if self.is_frozen():
            is_still_frozen = self.update_freeze(dt)
            if is_still_frozen:
                return
            # Se descongelou, continua

        # ===== VERIFICA SONO =====
        if self.is_asleep():
            is_still_asleep = self.update_sleep(dt)
            if is_still_asleep:
                return
            # Se acordou, continua

        # ===== VERIFICA STUN DA PARALISIA =====
        if self.is_stunned():
            is_still_stunned = self.update_stun(dt)
            if is_still_stunned:
                return
            # Se recuperou, continua

        if not self.pokemon.path or len(self.pokemon.path) == 0 or self.pokemon.path_index >= len(self.pokemon.path):
            return

        target_x, target_y = self.pokemon.path[self.pokemon.path_index]
        dx = target_x - self.pokemon.x
        dy = target_y - self.pokemon.y
        distance_sq = dx * dx + dy * dy
        move_distance = self.pokemon.move_speed * dt * 60

        if distance_sq <= move_distance * move_distance:
            self.pokemon.x, self.pokemon.y = target_x, target_y
            self.pokemon.path_index += 1
            if self.pokemon.path_index >= len(self.pokemon.path):
                self.pokemon.rect.x, self.pokemon.rect.y = self.pokemon.x, self.pokemon.y
                return
        else:
            distance = math.sqrt(distance_sq)
            move_x = (dx / distance) * move_distance
            move_y = (dy / distance) * move_distance
            self.pokemon.x += move_x
            self.pokemon.y += move_y

            # Atualiza direção baseado no movimento
            if abs(dx) > abs(dy):
                self.pokemon.current_direction = "right" if dx > 0 else "left"
            else:
                self.pokemon.current_direction = "down" if dy > 0 else "up"

        self.pokemon.rect.x, self.pokemon.rect.y = self.pokemon.x, self.pokemon.y

    def check_item_capture(self, items):
        """Verifica captura de item (apenas para Pokémon sem wave control)"""
        for item in items:
            if hasattr(item, 'is_protected') and item.is_protected and not item.carried_by:
                dx = self.pokemon.x - item.x
                dy = self.pokemon.y - item.y
                if dx * dx + dy * dy < self.pokemon.capture_range * self.pokemon.capture_range:
                    item.start_capture(self.pokemon)
                    break

    def get_distance_to(self, entity) -> float:
        dx = self.pokemon.x - entity.x
        dy = self.pokemon.y - entity.y
        return math.sqrt(dx * dx + dy * dy)