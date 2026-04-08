# src/entities/pokemon/combat.py
import math
import random
from typing import List, Optional

from src.battle.effects import StatusType
from src.battle.effects.animation_mapper import AnimationMapper


class PokemonCombat:
    """Gerencia combate do Pokémon - UNIFICADO para aliados e inimigos"""

    def __init__(self, pokemon):
        self.pokemon = pokemon

    # ===== MÉTODOS DE STATUS =====
    def is_stunned(self) -> bool:
        if hasattr(self.pokemon, 'effect_manager') and self.pokemon.effect_manager:
            status = self.pokemon.effect_manager.get_status(self.pokemon)
            if status and status.type == StatusType.PARALYSIS:
                return status.is_stunned()
        return False

    def update_stun(self, dt: float) -> bool:
        if hasattr(self.pokemon, 'effect_manager') and self.pokemon.effect_manager:
            status = self.pokemon.effect_manager.get_status(self.pokemon)
            if status and status.type == StatusType.PARALYSIS:
                return status.update_paralysis(dt, self.pokemon)
        return False

    def is_asleep(self) -> bool:
        if hasattr(self.pokemon, 'effect_manager') and self.pokemon.effect_manager:
            status = self.pokemon.effect_manager.get_status(self.pokemon)
            if status and status.type == StatusType.SLEEP:
                return status.is_asleep()
        return False

    def update_sleep(self, dt: float) -> bool:
        if hasattr(self.pokemon, 'effect_manager') and self.pokemon.effect_manager:
            status = self.pokemon.effect_manager.get_status(self.pokemon)
            if status and status.type == StatusType.SLEEP:
                return status.update_sleep(dt)
        return False

    def is_frozen(self) -> bool:
        if hasattr(self.pokemon, 'effect_manager') and self.pokemon.effect_manager:
            status = self.pokemon.effect_manager.get_status(self.pokemon)
            if status and status.type == StatusType.FREEZE:
                return status.is_frozen()
        return False

    def update_freeze(self, dt: float) -> bool:
        if hasattr(self.pokemon, 'effect_manager') and self.pokemon.effect_manager:
            status = self.pokemon.effect_manager.get_status(self.pokemon)
            if status and status.type == StatusType.FREEZE:
                return status.update_freeze(dt)
        return False

    def thaw(self):
        if hasattr(self.pokemon, 'effect_manager') and self.pokemon.effect_manager:
            status = self.pokemon.effect_manager.get_status(self.pokemon)
            if status and status.type == StatusType.FREEZE:
                return status.thaw()
        return False

    # ===== MÉTODOS DE BUSCA DE ALVO =====
    def find_nearest_enemy(self, all_entities: List) -> Optional['Pokemon']:
        """
        Encontra o inimigo mais próximo.
        - Se for wild (inimigo): alvos são NOT wild (aliados)
        - Se for NOT wild (aliado): alvos são wild (inimigos)
        """
        if not all_entities:
            return None

        nearest = None
        min_distance = float('inf')
        attack_range_sq = self.pokemon.attack_range * self.pokemon.attack_range

        for entity in all_entities:
            # Verifica se é alvo válido
            is_valid_target = False
            if self.pokemon.is_wild:
                # Inimigo ataca aliados
                is_valid_target = not entity.is_wild and entity.is_alive() and not entity.is_defeated
            else:
                # Aliado ataca inimigos
                is_valid_target = entity.is_wild and entity.is_alive() and not entity.is_defeated

            if is_valid_target:
                dx = self.pokemon.x - entity.x
                dy = self.pokemon.y - entity.y
                distance_sq = dx * dx + dy * dy

                if distance_sq < attack_range_sq and distance_sq < min_distance:
                    min_distance = distance_sq
                    nearest = entity

        return nearest

    # ===== MÉTODO PRINCIPAL DE COMBATE =====
    def update_combat(self, dt: float, all_entities: List):
        """
        Atualiza a lógica de combate - UNIFICADA.
        A única diferença entre wild e not wild é se movem durante ataque.
        """
        # Verificações de status que impedem ação
        if not self._can_act(dt):
            return

        # Atualiza cooldown
        if self.pokemon.charge_cooldown > 0:
            self.pokemon.charge_cooldown -= dt

        # Se já tem alvo, verifica se ainda é válido
        if self.pokemon.target:
            if not self.pokemon.target.is_alive() or self.pokemon.target.is_defeated:
                self.pokemon.target = None
                self.pokemon.combat_state = "idle"

        # Se não tem alvo, procura um
        if not self.pokemon.target:
            self.pokemon.target = self.find_nearest_enemy(all_entities)
            if self.pokemon.target:
                print(f"[COMBAT] {self.pokemon.name} encontrou alvo: {self.pokemon.target.name}")
                self.pokemon.combat_state = "attacking"

        # Se tem alvo e pode atacar
        if self.pokemon.target and self.pokemon.charge_cooldown <= 0:
            self._try_attack(self.pokemon.target, dt)

    def _can_act(self, dt: float) -> bool:
        """Verifica se o Pokémon pode agir (não está atordoado, dormindo ou congelado)"""
        # Stun (paralisia)
        if self.update_stun(dt):
            return False

        # Sono
        if self.update_sleep(dt):
            return False

        # Congelamento
        if self.is_frozen():
            if self.update_freeze(dt):
                return False

        return True

    def _try_attack(self, target: 'Pokemon', dt: float):
        """Tenta atacar o alvo - UNIFICADO para aliados e inimigos"""
        # Verifica se está em animação de ataque
        is_attacking = hasattr(self.pokemon, '_attack_animation_active') and self.pokemon._attack_animation_active
        if is_attacking:
            return

        # Verifica se tem move disponível
        current_move = self._get_current_move()
        if not current_move or current_move.current_pp <= 0:
            self.pokemon.has_no_pp = True
            return

        # Calcula distância até o alvo
        dx = target.x - self.pokemon.x
        dy = target.y - self.pokemon.y
        distance = math.sqrt(dx * dx + dy * dy)

        # Atualiza direção para olhar para o alvo
        self._update_direction_to_target(dx, dy)

        # ===== INIMIGOS (WILD): Atacam em movimento, sem verificar distância =====
        if self.pokemon.is_wild:
            # Inimigos atacam independente da distância (continuam andando)
            self._start_attack_animation(target, current_move)
            return

        # ===== ALIADOS (NOT WILD): Precisam estar perto para atacar =====
        attack_distance = 12  # Distância corpo a corpo para físicos
        is_status_move = current_move.category == "status"
        is_special_move = current_move.category == "special"

        # Ataques à distância (status e especiais) podem atacar de qualquer lugar
        if is_status_move or is_special_move:
            self._start_attack_animation(target, current_move)
            return

        # Ataques físicos precisam se aproximar
        if distance > attack_distance:
            # Move em direção ao alvo
            self._move_towards_target(target, dx, dy, distance, dt)
        else:
            # Está perto o suficiente para atacar
            self._start_attack_animation(target, current_move)

    def _get_current_move(self):
        """Obtém o move atual baseado no padrão de ataque (para inimigos) ou move normal (para aliados)"""
        if hasattr(self.pokemon, 'get_current_move_for_pattern'):
            return self.pokemon.get_current_move_for_pattern()
        return self.pokemon.get_current_move()

    def _move_towards_target(self, target: 'Pokemon', dx: float, dy: float, distance: float, dt: float):
        """Move em direção ao alvo (apenas para aliados)"""
        # Garante animação de walk
        if self.pokemon.current_animation != "walk":
            is_attacking = hasattr(self.pokemon, '_attack_animation_active') and self.pokemon._attack_animation_active
            if not is_attacking:
                self.pokemon.set_animation("walk")

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

    def _start_attack_animation(self, target: 'Pokemon', move):
        """Inicia a animação de ataque"""
        from src.battle.effects.animation_mapper import AnimationMapper

        animation_to_use = AnimationMapper.get_animation_for_move(move.name, move.category)

        # Verifica se o Pokémon tem a animação
        if not self.pokemon.has_animation(animation_to_use):
            if animation_to_use == "attack" and self.pokemon.has_animation("strike"):
                animation_to_use = "strike"
            elif animation_to_use == "shoot" and self.pokemon.has_animation("attack"):
                animation_to_use = "attack"
            elif not self.pokemon.has_animation(animation_to_use):
                if self.pokemon.has_animation("attack"):
                    animation_to_use = "attack"
                elif self.pokemon._available_animations:
                    animation_to_use = self.pokemon._available_animations[0]
                else:
                    # Sem animação, ataca diretamente
                    self._execute_attack(target, move)
                    return

        # Salva animação anterior
        self.pokemon._saved_animation_before_attack = self.pokemon.current_animation
        self.pokemon.set_animation_direct(animation_to_use)
        self.pokemon.current_frame = 0
        self.pokemon.animation_timer = 0
        self.pokemon._attack_animation_active = True
        self.pokemon._pending_attack_move = move.name  # Salva o nome do move
        self.pokemon._pending_attack_target = target  # Salva o alvo
        self.pokemon._damage_frame_percent = 0.5
        self.pokemon._damage_applied = False

        print(f"[ANIM] {self.pokemon.name} usou animação '{animation_to_use}' para {move.name}")

    def _execute_attack(self, target: 'Pokemon', move):
        """Executa o ataque real (chamado pela animação ou diretamente)"""
        if not target or not target.is_alive() or target.is_defeated:
            self.pokemon.target = None
            self.pokemon.combat_state = "idle"
            return

        if not move or move.current_pp <= 0:
            print(f"[COMBAT] {self.pokemon.name} está sem PP para {move.name if move else 'ataque'}!")
            self.pokemon.has_no_pp = True
            self.pokemon.target = None
            self.pokemon.combat_state = "idle"
            return

        # Executa o ataque via battle_system
        if self.pokemon.battle_system:
            success = self.pokemon.battle_system.attempt_attack(self.pokemon, target)
            if success:
                print(f"[ATTACK] {self.pokemon.name} usou {move.name} em {target.name}!")
        else:
            # Fallback: cálculo simples
            hit_chance = move.accuracy / 100
            will_hit = random.random() <= hit_chance
            if will_hit:
                self._simple_attack(target, move)
            else:
                print(f"[COMBAT] {move.name} errou!")
                self.show_miss_on_self()
            move.current_pp -= 1

        # Reseta estado após ataque
        self.pokemon.charge_cooldown = self.pokemon.charge_cooldown_max

        # Para aliados: volta para posição original
        if not self.pokemon.is_wild:
            self.pokemon.combat_state = "returning"
            self.pokemon.target = None
        else:
            # Para inimigos: mantém o alvo (pode atacar de novo)
            self.pokemon.combat_state = "attacking"
            # Não reseta o target para continuar atacando

    def _simple_attack(self, target: 'Pokemon', move):
        """Ataque simples (fallback sem battle_system)"""
        # Determina se é físico ou especial
        if move.category == "physical":
            atk = self.pokemon.attack
            defense = target.defense_value
        else:
            atk = self.pokemon.sp_attack
            defense = target.sp_defense

        base_damage = ((2 * self.pokemon.level / 5 + 2) * move.power * atk / defense) / 50 + 2
        damage_multiplier = random.uniform(0.85, 1.15)
        damage = max(1, int(base_damage * damage_multiplier))

        target.take_damage(damage, attacker=self.pokemon)

    def show_miss_on_self(self):
        """Mostra o texto MISS no próprio Pokémon"""
        self.pokemon.miss_timer = 0.6

    def _update_direction_to_target(self, dx: float, dy: float):
        """Atualiza direção baseada no alvo (8 direções)"""
        if dx == 0 and dy == 0:
            return

        abs_dx = abs(dx)
        abs_dy = abs(dy)
        THRESHOLD = 0.41421356

        if abs_dx >= abs_dy:
            if dx > 0:
                if dy > 0 and abs_dy > abs_dx * THRESHOLD:
                    self.pokemon.current_direction = "down-right"
                elif dy < 0 and abs_dy > abs_dx * THRESHOLD:
                    self.pokemon.current_direction = "up-right"
                else:
                    self.pokemon.current_direction = "right"
            else:
                if dy > 0 and abs_dy > abs_dx * THRESHOLD:
                    self.pokemon.current_direction = "down-left"
                elif dy < 0 and abs_dy > abs_dx * THRESHOLD:
                    self.pokemon.current_direction = "up-left"
                else:
                    self.pokemon.current_direction = "left"
        else:
            if dy > 0:
                if dx > 0 and abs_dx > abs_dy * THRESHOLD:
                    self.pokemon.current_direction = "down-right"
                elif dx < 0 and abs_dx > abs_dy * THRESHOLD:
                    self.pokemon.current_direction = "down-left"
                else:
                    self.pokemon.current_direction = "down"
            else:
                if dx > 0 and abs_dx > abs_dy * THRESHOLD:
                    self.pokemon.current_direction = "up-right"
                elif dx < 0 and abs_dx > abs_dy * THRESHOLD:
                    self.pokemon.current_direction = "up-left"
                else:
                    self.pokemon.current_direction = "up"

    # ===== MÉTODOS DE DANO =====
    def take_damage(self, damage, attacker=None):
        """Recebe dano"""
        if self.pokemon.is_defeated:
            return self.pokemon.current_hp <= 0

        old_hp = self.pokemon.current_hp
        self.pokemon.current_hp = max(0, self.pokemon.current_hp - damage)

        if damage > 0 and self.pokemon.current_hp > 0:
            self.pokemon.play_hurt_animation()

        if self.pokemon.current_hp <= 0:
            from src.managers.move_sound_manager import move_sound_manager
            move_sound_manager.play_attack_sound("faint")
            print(f"[BATTLE] {self.pokemon.name} foi derrotado!")

            self.pokemon.set_defeated(True)

            # Se estava carregando item (apenas para inimigos selvagens)
            if self.pokemon.is_wild and self.pokemon.is_carrying:
                carried_item = self.pokemon.is_carrying
                print(f"[ITEM] {carried_item.item_name} será liberado com a morte de {self.pokemon.name}")
                carried_item.reset_capture()
                carried_item.is_protected = True
                carried_item.is_stolen = False
                carried_item.carried_by = None
                self.pokemon.is_carrying = None

        return self.pokemon.current_hp <= 0

    # ===== MÉTODOS LEGADOS (para compatibilidade) =====
    def handle_idle_state(self, dt, enemies):
        """Legado - mantido para compatibilidade"""
        if self.pokemon.target:
            return
        self.pokemon.target = self.find_nearest_enemy(enemies)
        if self.pokemon.target:
            self.pokemon.combat_state = "charging"

    def handle_charging_state(self, dt):
        """Legado - mantido para compatibilidade"""
        if self.pokemon.is_wild:
            if self.pokemon.target and self.pokemon.target.is_alive():
                self._try_attack(self.pokemon.target, dt)
            else:
                self.pokemon.combat_state = "idle"
                self.pokemon.target = None

    def handle_returning_state(self, dt):
        """Legado - apenas para aliados"""
        if self.pokemon.is_wild:
            self.pokemon.combat_state = "idle"
            return

        dx = self.pokemon.original_spot_x - self.pokemon.x
        dy = self.pokemon.original_spot_y - self.pokemon.y
        distance = math.sqrt(dx * dx + dy * dy)

        if distance < 5:
            self.pokemon.x, self.pokemon.y = self.pokemon.original_spot_x, self.pokemon.original_spot_y
            self.pokemon.rect.x, self.pokemon.rect.y = self.pokemon.x, self.pokemon.y
            self.pokemon.combat_state = "idle"
            self.pokemon.target = None
            if self.pokemon.has_animation("idle"):
                self.pokemon.set_animation("idle")
            return

        if distance > 0:
            is_attacking = hasattr(self.pokemon, '_attack_animation_active') and self.pokemon._attack_animation_active
            if self.pokemon.current_animation != "walk" and not is_attacking:
                self.pokemon.set_animation("walk")

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

    def find_nearest_enemy_legacy(self, enemies: List) -> Optional['Pokemon']:
        """Legado - usa o novo método unificado"""
        return self.find_nearest_enemy(enemies)

    def perform_charge_attack(self, target):
        """Legado - delega para o novo sistema"""
        current_move = self._get_current_move()
        if current_move and current_move.current_pp > 0:
            self._execute_attack(target, current_move)