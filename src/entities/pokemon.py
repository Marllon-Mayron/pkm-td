# src/entities/pokemon.py
import pygame
import math
import uuid
import random
from src.entities.base import Entity
from src.data.pokedex import Pokedex
from src.managers.evolution_manager import evolution_manager

# Cache global de sprites e fontes para reduzir recriação
_SPRITE_CACHE = {}
_FONT_CACHE = {}


class Pokemon(Entity):
    # Constantes de classe
    _MIN_MOVE_SPEED = 0.2
    _MAX_MOVE_SPEED = 4.5
    _speed_cache = {}

    def __init__(self, x, y, pokemon_id, level=5, is_wild=False, shiny=False, is_boss=False):
        # ===== 1. DADOS BÁSICOS =====
        self.pokedex = Pokedex()
        self.unique_id = str(uuid.uuid4())
        self.pokemon_data = self.pokedex.get_pokemon(pokemon_id)

        if not self.pokemon_data:
            raise ValueError(f"Pokémon ID {pokemon_id} não encontrado")

        self.id = pokemon_id
        self.name = self.pokemon_data["name"].capitalize()
        self.base_level = level
        self.level = level
        self.is_shiny = shiny
        self.is_boss = is_boss

        # ===== 2. STATUS E ATRIBUTOS BASE =====
        self.is_placed = False
        self.spot_id = None
        self.types = self.pokemon_data["types"]
        self.base_stats = self.pokemon_data["base_stats"]

        # ===== 3. IVs E EVs =====
        self.ivs = {
            "hp": random.randint(0, 31),
            "attack": random.randint(0, 31),
            "defense": random.randint(0, 31),
            "special_attack": random.randint(0, 31),
            "special_defense": random.randint(0, 31),
            "speed": random.randint(0, 31)
        }

        self.evs = {
            "hp": 0, "attack": 0, "defense": 0,
            "special_attack": 0, "special_defense": 0, "speed": 0
        }

        # ===== 4. NATUREZA =====
        self.nature_multipliers = self._generate_nature()
        self.nature = self.nature_multipliers["name"]

        # ===== 5. CALCULAR STATS =====
        self._calculate_stats()

        # ===== 6. BOSS: AUMENTA LEVEL E RECALCULA =====
        if is_boss:
            self.level = self.base_level + 3
            self._calculate_stats()
            self.max_hp = int(self.max_hp * 2)
            self.current_hp = self.max_hp
            self.defense = int(self.defense * 2)
            self.sp_defense = int(self.sp_defense * 2)
            self.defense_value = self._calculate_defense()

        # ===== 7. ESTADO ATUAL =====
        self.current_hp = self.max_hp
        self.xp = 0
        self.xp_to_next = self._calculate_xp_needed()

        # ===== 8. SPRITES (COM CACHE) =====
        self._load_sprites(pokemon_id, shiny)

        # ===== 9. TAMANHO DO SPRITE =====
        self.map_sprite_size = self.pokedex.get_map_sprite_size(pokemon_id, shiny)
        width = self.map_sprite_size
        height = self.map_sprite_size

        sprite = None
        if self.inmap_frames and "down" in self.inmap_frames and self.inmap_frames["down"]:
            sprite = self.inmap_frames["down"][0]

        super().__init__(x, y, width, height, sprite)

        # ===== 10. ATRIBUTOS DE JOGO =====
        self.is_wild = is_wild
        self.is_in_team = False
        self.is_selected = False

        # ===== 11. MOVIMENTO =====
        self.path = []
        self.path_index = 0
        self.move_speed = 2.0
        self.original_path = None  # Mantido para compatibilidade

        if is_wild:
            self.base_move_speed = self._get_cached_move_speed()
            self.move_speed = self.base_move_speed
            # Log reduzido - apenas em debug
            # print(f"[VELOCIDADE] {self.name} velocidade de movimento: {self.move_speed:.2f}")
        else:
            self.base_move_speed = 2.0
            self.move_speed = 2.0

        # ===== 12. COMBATE =====
        self.can_attack = True
        self.attack_cooldown = 0
        self.attack_cooldown_max = 60
        self.target = None

        # ===== 13. EFEITOS VISUAIS =====
        self.hp_bar_width = 32
        self.hp_bar_height = 3

        # ===== 14. POSIÇÃO E MOVIMENTAÇÃO =====
        self.last_x = x
        self.last_y = y

        # ===== 15. ITENS =====
        self.is_carrying = None
        self.capture_range = 10
        self.is_returning_with_item = False

        # ===== 16. ATRIBUTOS DE COMBATE =====
        self.attack_range = 60
        self.combat_state = "idle"
        self.original_spot_x = x
        self.original_spot_y = y

        # ===== 17. COOLDOWNS =====
        self.charge_cooldown = 0.0
        self.charge_cooldown_max = 1.2

        # ===== 18. STATS DE COMBATE =====
        self.attack_damage = self._calculate_attack_damage()
        self.defense_value = self._calculate_defense()

        # ===== 19. RASTREAMENTO DE DANO =====
        self.damage_contributions = {}
        self.last_attacker = None

        # ===== 20. SCREEN MANAGER (para renderização) =====
        self.screen_manager = None

        # ===== 21. DEBUG (desativado por padrão) =====
        self.show_debug = False

    def _load_sprites(self, pokemon_id, shiny):
        """Carrega sprites com cache"""
        cache_key = f"{pokemon_id}_{shiny}"

        if cache_key in _SPRITE_CACHE:
            cached = _SPRITE_CACHE[cache_key]
            self.ui_sprite = cached["ui"]
            self.battle_sprite = cached["battle"]
            self.inmap_frames = cached["inmap"]
        else:
            self.ui_sprite = self.pokedex.get_sprite(pokemon_id, "front", shiny)
            self.battle_sprite = self.pokedex.get_sprite(pokemon_id, "back", shiny)
            self.inmap_frames = self.pokedex.get_inmap_animation(pokemon_id, shiny)
            _SPRITE_CACHE[cache_key] = {
                "ui": self.ui_sprite,
                "battle": self.battle_sprite,
                "inmap": self.inmap_frames
            }

        self.current_direction = "down"
        self.current_frame = 0
        self.animation_timer = 0
        self.animation_speed = 0.1

    def _get_cached_move_speed(self):
        """Obtém velocidade de movimento do cache"""
        cache_key = (self.id, self.level, self.speed_stat, self.is_shiny, self.is_boss)

        if cache_key in self._speed_cache:
            return self._speed_cache[cache_key]

        speed = self._calculate_wild_move_speed()
        # Limita o tamanho do cache
        if len(self._speed_cache) > 1000:
            self._speed_cache.clear()
        self._speed_cache[cache_key] = speed
        return speed

    def _calculate_stats(self):
        """Calcula stats baseado em level, IVs e EVs"""
        stats = self.pokedex.calculate_stats(self.id, self.level, self.ivs, self.evs)

        self.max_hp = stats["hp"]
        self.attack = stats["attack"]
        self.defense = stats["defense"]
        self.sp_attack = stats["special_attack"]
        self.sp_defense = stats["special_defense"]
        self.speed_stat = stats["speed"]

        if hasattr(self, 'nature_multipliers'):
            mult = self.nature_multipliers
            if mult["attack"] != 1.0:
                self.attack = int(self.attack * mult["attack"])
            if mult["defense"] != 1.0:
                self.defense = int(self.defense * mult["defense"])
            if mult["sp_attack"] != 1.0:
                self.sp_attack = int(self.sp_attack * mult["sp_attack"])
            if mult["sp_defense"] != 1.0:
                self.sp_defense = int(self.sp_defense * mult["sp_defense"])
            if mult["speed"] != 1.0:
                self.speed_stat = int(self.speed_stat * mult["speed"])

    def _calculate_xp_needed(self):
        return int(self.level ** 3)

    def _generate_nature(self):
        natures = [
            {"name": "Hardy", "attack": 1.0, "defense": 1.0, "sp_attack": 1.0, "sp_defense": 1.0, "speed": 1.0},
            {"name": "Lonely", "attack": 1.1, "defense": 0.9, "sp_attack": 1.0, "sp_defense": 1.0, "speed": 1.0},
            {"name": "Brave", "attack": 1.1, "defense": 1.0, "sp_attack": 1.0, "sp_defense": 1.0, "speed": 0.9},
            {"name": "Adamant", "attack": 1.1, "defense": 1.0, "sp_attack": 0.9, "sp_defense": 1.0, "speed": 1.0},
            {"name": "Naughty", "attack": 1.1, "defense": 1.0, "sp_attack": 1.0, "sp_defense": 0.9, "speed": 1.0},
            {"name": "Bold", "attack": 0.9, "defense": 1.1, "sp_attack": 1.0, "sp_defense": 1.0, "speed": 1.0},
            {"name": "Relaxed", "attack": 1.0, "defense": 1.1, "sp_attack": 1.0, "sp_defense": 1.0, "speed": 0.9},
            {"name": "Impish", "attack": 1.0, "defense": 1.1, "sp_attack": 0.9, "sp_defense": 1.0, "speed": 1.0},
            {"name": "Lax", "attack": 1.0, "defense": 1.1, "sp_attack": 1.0, "sp_defense": 0.9, "speed": 1.0},
            {"name": "Timid", "attack": 0.9, "defense": 1.0, "sp_attack": 1.0, "sp_defense": 1.0, "speed": 1.1},
            {"name": "Hasty", "attack": 1.0, "defense": 0.9, "sp_attack": 1.0, "sp_defense": 1.0, "speed": 1.1},
            {"name": "Jolly", "attack": 1.0, "defense": 1.0, "sp_attack": 0.9, "sp_defense": 1.0, "speed": 1.1},
            {"name": "Naive", "attack": 1.0, "defense": 1.0, "sp_attack": 1.0, "sp_defense": 0.9, "speed": 1.1},
            {"name": "Modest", "attack": 0.9, "defense": 1.0, "sp_attack": 1.1, "sp_defense": 1.0, "speed": 1.0},
            {"name": "Mild", "attack": 1.0, "defense": 0.9, "sp_attack": 1.1, "sp_defense": 1.0, "speed": 1.0},
            {"name": "Quiet", "attack": 1.0, "defense": 1.0, "sp_attack": 1.1, "sp_defense": 1.0, "speed": 0.9},
            {"name": "Rash", "attack": 1.0, "defense": 1.0, "sp_attack": 1.1, "sp_defense": 0.9, "speed": 1.0},
            {"name": "Calm", "attack": 0.9, "defense": 1.0, "sp_attack": 1.0, "sp_defense": 1.1, "speed": 1.0},
            {"name": "Gentle", "attack": 1.0, "defense": 0.9, "sp_attack": 1.0, "sp_defense": 1.1, "speed": 1.0},
            {"name": "Sassy", "attack": 1.0, "defense": 1.0, "sp_attack": 1.0, "sp_defense": 1.1, "speed": 0.9},
            {"name": "Careful", "attack": 1.0, "defense": 1.0, "sp_attack": 0.9, "sp_defense": 1.1, "speed": 1.0},
            {"name": "Quirky", "attack": 1.0, "defense": 1.0, "sp_attack": 1.0, "sp_defense": 1.0, "speed": 1.0},
        ]
        nature = random.choice(natures)
        self.nature = nature["name"]
        return nature

    def heal(self, amount=None):
        if amount is None:
            self.current_hp = self.max_hp
        else:
            self.current_hp = min(self.max_hp, self.current_hp + amount)

    def check_and_evolve(self):
        evolution = evolution_manager.check_evolution(self.id, current_level=self.level)

        if evolution:
            evolve_to_id = evolution["evolve_to"]
            self._perform_evolution(evolve_to_id)
            return True
        return False

    def _perform_evolution(self, new_id):
        old_name = self.name
        old_level = self.level

        new_pokemon_data = self.pokedex.get_pokemon(new_id)

        if not new_pokemon_data:
            return

        self.id = new_id
        self.name = new_pokemon_data["name"].capitalize()
        self.types = new_pokemon_data["types"]
        self.base_stats = new_pokemon_data["base_stats"]

        self._calculate_stats()
        self.current_hp = self.max_hp

        self._load_sprites(new_id, self.is_shiny)
        self.map_sprite_size = self.pokedex.get_map_sprite_size(new_id, self.is_shiny)

        print(f"[EVOLUÇÃO] ✓ {old_name} (Lv.{old_level}) evoluiu para {self.name}!")

    def gain_xp(self, amount):
        old_level = self.level
        self.xp += amount

        leveled_up = False
        while self.xp >= self.xp_to_next:
            self.level_up()
            leveled_up = True

        if leveled_up:
            self.attack_damage = self._calculate_attack_damage()
            self.defense_value = self._calculate_defense()
            self.check_and_evolve()

    def level_up(self):
        self.xp -= self.xp_to_next
        self.level += 1
        self._calculate_stats()
        self.current_hp = self.max_hp
        self.xp_to_next = self._calculate_xp_needed()

        # Limpa cache de velocidade
        cache_key = (self.id, self.level, self.speed_stat, self.is_shiny, self.is_boss)
        self._speed_cache.pop(cache_key, None)

    def is_boss_type(self):
        return hasattr(self, 'is_boss') and self.is_boss

    def is_alive(self):
        return self.current_hp > 0

    def get_hp_percentage(self):
        return self.current_hp / self.max_hp

    def _calculate_attack_damage(self):
        return (self.attack + self.sp_attack) / 2

    def _calculate_wild_move_speed(self):
        MIN_MOVE_SPEED = self._MIN_MOVE_SPEED
        MAX_MOVE_SPEED = self._MAX_MOVE_SPEED

        min_base = self.pokedex.min_base_speed
        max_base = self.pokedex.max_base_speed

        base_speed = self.base_stats["speed"]

        if max_base > min_base:
            base_norm = (base_speed - min_base) / (max_base - min_base)
            base_norm = max(0.0, min(1.0, base_norm))
        else:
            base_norm = 0.5

        nature_min = 0.9
        nature_max = 1.1

        def calc_speed_stat(iv, ev, nature_mult):
            raw = ((2 * base_speed + iv + (ev // 4)) * self.level) / 100 + 5
            return int(raw * nature_mult)

        min_speed_stat = calc_speed_stat(0, 0, nature_min)
        max_speed_stat = calc_speed_stat(31, 252, nature_max)

        actual_speed = self.speed_stat

        if max_speed_stat > min_speed_stat:
            stat_norm = (actual_speed - min_speed_stat) / (max_speed_stat - min_speed_stat)
            stat_norm = max(0.0, min(1.0, stat_norm))
        else:
            stat_norm = 0.5

        combined_norm = base_norm * (0.8 + 0.2 * stat_norm)
        level_factor = 1.0 + (self.level / 100) * 0.3

        move_speed = MIN_MOVE_SPEED + (MAX_MOVE_SPEED - MIN_MOVE_SPEED) * combined_norm
        move_speed *= level_factor

        if self.is_shiny:
            move_speed *= 1.25
        if self.is_boss:
            move_speed *= 0.7

        return max(MIN_MOVE_SPEED, min(MAX_MOVE_SPEED, move_speed))

    def _calculate_defense(self):
        return (self.defense + self.sp_defense) / 2

    def find_nearest_enemy(self, enemies):
        if not enemies:
            return None

        nearest = None
        min_distance = float('inf')
        attack_range_sq = self.attack_range * self.attack_range

        for enemy in enemies:
            if enemy.is_alive() and enemy.is_wild:
                dx = self.x - enemy.x
                dy = self.y - enemy.y
                distance_sq = dx * dx + dy * dy

                if distance_sq < attack_range_sq and distance_sq < min_distance:
                    min_distance = distance_sq
                    nearest = enemy

        return nearest

    def update_combat(self, dt, enemies):
        if self.charge_cooldown > 0:
            self.charge_cooldown -= dt

        if self.target and not self.target.is_alive():
            self.target = None
            self.combat_state = "returning"
            return

        if self.combat_state == "idle":
            self._handle_idle_state(dt, enemies)
        elif self.combat_state == "charging":
            self._handle_charging_state(dt)
        elif self.combat_state == "returning":
            self._handle_returning_state(dt)

    def _handle_idle_state(self, dt, enemies):
        nearest = self.find_nearest_enemy(enemies)

        if nearest and self.charge_cooldown <= 0:
            self.target = nearest
            self.combat_state = "charging"

    def _handle_charging_state(self, dt):
        if not self.target or not self.target.is_alive():
            self.combat_state = "returning"
            self.target = None
            return

        dx = self.target.x - self.x
        dy = self.target.y - self.y
        distance = math.sqrt(dx * dx + dy * dy)

        if distance < 5:
            self._perform_charge_attack(self.target)
            self.combat_state = "returning"
            self.charge_cooldown = self.charge_cooldown_max
            return

        if distance > 0:
            move_distance = self.move_speed * dt * 60
            move_x = (dx / distance) * move_distance
            move_y = (dy / distance) * move_distance

            if abs(move_x) > abs(dx):
                move_x = dx
            if abs(move_y) > abs(dy):
                move_y = dy

            self.x += move_x
            self.y += move_y
            self.rect.x, self.rect.y = self.x, self.y

            if abs(dx) > abs(dy):
                self.current_direction = "right" if dx > 0 else "left"
            else:
                self.current_direction = "down" if dy > 0 else "up"

    def _handle_returning_state(self, dt):
        dx = self.original_spot_x - self.x
        dy = self.original_spot_y - self.y
        distance = math.sqrt(dx * dx + dy * dy)

        if distance < 5:
            self.x, self.y = self.original_spot_x, self.original_spot_y
            self.rect.x, self.rect.y = self.x, self.y
            self.combat_state = "idle"
            self.target = None
            return

        if distance > 0:
            move_distance = self.move_speed * dt * 60
            move_x = (dx / distance) * move_distance
            move_y = (dy / distance) * move_distance

            if abs(move_x) > abs(dx):
                move_x = dx
            if abs(move_y) > abs(dy):
                move_y = dy

            self.x += move_x
            self.y += move_y
            self.rect.x, self.rect.y = self.x, self.y

            if abs(dx) > abs(dy):
                self.current_direction = "right" if dx > 0 else "left"
            else:
                self.current_direction = "down" if dy > 0 else "up"

    def _perform_charge_attack(self, target):
        base_damage = self.attack_damage * (self.level / 8)
        damage_multiplier = random.uniform(0.85, 1.15)
        damage = int(base_damage * damage_multiplier)

        defense_factor = max(0.4, 1.0 - (target.defense_value / 800))
        final_damage = max(2, int(damage * defense_factor))

        target.take_damage(final_damage, attacker=self)

        if not target.is_alive():
            pass

    def _attack_target(self, target):
        base_damage = self.attack_damage * (self.level / 10)
        damage_multiplier = random.uniform(0.8, 1.2)
        damage = int(base_damage * damage_multiplier)

        defense_factor = max(0.5, 1.0 - (target.defense_value / 1000))
        final_damage = max(1, int(damage * defense_factor))

        target.take_damage(final_damage)

        if not target.is_alive():
            self.target = None
            self.combat_state = "returning"

    def take_damage(self, damage, attacker=None):
        old_hp = self.current_hp
        self.current_hp = max(0, self.current_hp - damage)

        if attacker and self.is_wild:
            attacker_id = id(attacker)
            actual_damage = min(damage, old_hp)
            self.damage_contributions[attacker_id] = self.damage_contributions.get(attacker_id, 0) + actual_damage
            self.last_attacker = attacker

        if self.current_hp <= 0:
            self.drop_item()
            self.combat_state = "idle"
            self.target = None

        return self.current_hp <= 0

    def get_xp_contributors(self):
        if not self.damage_contributions:
            if self.last_attacker:
                return [(id(self.last_attacker), 1)]
            return []

        return [(attacker_id, damage) for attacker_id, damage in self.damage_contributions.items()]

    def clear_damage_tracking(self):
        self.damage_contributions.clear()
        self.last_attacker = None

    def drop_item(self):
        if self.is_carrying:
            self.is_carrying.reset_capture()
            self.is_carrying = None

    def calculate_damage(self, target):
        damage = max(1, int((self.attack * self.level) / (target.defense * 2) + 2))
        return int(damage * random.uniform(0.85, 1.0))

    def clear_carrying(self):
        if self.is_carrying:
            self.is_carrying = None

    def recalculate_path_after_capture(self):
        if not self.path or self.path_index >= len(self.path):
            return

        current_idx = self.path_index

        start_distance = 0
        if current_idx > 0:
            start_distance += math.hypot(self.x - self.path[current_idx][0],
                                         self.y - self.path[current_idx][1])
            for i in range(current_idx, 0, -1):
                x1, y1 = self.path[i]
                x2, y2 = self.path[i - 1]
                start_distance += math.hypot(x2 - x1, y2 - y1)

        end_distance = 0
        if current_idx < len(self.path) - 1:
            end_distance += math.hypot(self.x - self.path[current_idx][0],
                                       self.y - self.path[current_idx][1])
            for i in range(current_idx, len(self.path) - 1):
                x1, y1 = self.path[i]
                x2, y2 = self.path[i + 1]
                end_distance += math.hypot(x2 - x1, y2 - y1)

        if start_distance < end_distance:
            if not hasattr(self, 'original_path') or self.original_path is None:
                self.original_path = self.path.copy()

            self.path = list(reversed(self.original_path.copy()))

            min_dist = float('inf')
            closest_idx = 0
            for i, point in enumerate(self.path):
                dist = math.hypot(self.x - point[0], self.y - point[1])
                if dist < min_dist:
                    min_dist = dist
                    closest_idx = i
            self.path_index = closest_idx
        else:
            if hasattr(self, 'original_path') and self.original_path is not None:
                self.path = self.original_path.copy()
            else:
                self.original_path = self.path.copy()

            min_dist = float('inf')
            closest_idx = self.path_index
            for i, point in enumerate(self.path):
                if i >= self.path_index:
                    dist = math.hypot(self.x - point[0], self.y - point[1])
                    if dist < min_dist:
                        min_dist = dist
                        closest_idx = i
            self.path_index = closest_idx

        self.target = None
        self.combat_state = "idle"

        if self.is_boss:
            self.is_returning_with_item = True

    def update(self, dt, player=None, enemies=None, items=None):
        self.last_x = self.x
        self.last_y = self.y

        if not self.can_attack:
            self.attack_cooldown -= 1
            if self.attack_cooldown <= 0:
                self.can_attack = True

        # Lógica de captura de itens
        if self.is_wild and items is not None and not self.is_carrying:
            for item in items:
                if hasattr(item, 'is_protected') and item.is_protected and not item.carried_by:
                    dx = self.x - item.x
                    dy = self.y - item.y
                    if dx * dx + dy * dy < self.capture_range * self.capture_range:
                        item.start_capture(self)
                        self.recalculate_path_after_capture()
                        break

        # Movimento em path
        if self.path and len(self.path) > 0 and self.path_index < len(self.path):
            target_x, target_y = self.path[self.path_index]
            dx = target_x - self.x
            dy = target_y - self.y
            distance_sq = dx * dx + dy * dy
            move_distance = self.move_speed * dt * 60

            if distance_sq <= move_distance * move_distance:
                self.x, self.y = target_x, target_y
                self.path_index += 1
                if self.path_index >= len(self.path):
                    self.rect.x, self.rect.y = self.x, self.y
                    return
            else:
                distance = math.sqrt(distance_sq)
                move_x = (dx / distance) * move_distance
                move_y = (dy / distance) * move_distance
                self.x += move_x
                self.y += move_y

                if abs(dx) > abs(dy):
                    self.current_direction = "right" if dx > 0 else "left"
                else:
                    self.current_direction = "down" if dy > 0 else "up"

            self.rect.x, self.rect.y = self.x, self.y

        if self.is_carrying:
            self.is_carrying.update_capture(dt)

        # Animação
        self.animation_timer += dt
        if self.animation_timer >= self.animation_speed:
            self.animation_timer = 0
            if self.inmap_frames and self.current_direction in self.inmap_frames:
                frames_list = self.inmap_frames[self.current_direction]
                if frames_list:
                    self.current_frame = (self.current_frame + 1) % len(frames_list)
                    self.sprite = frames_list[self.current_frame]

    def get_distance_to(self, entity):
        dx = self.x - entity.x
        dy = self.y - entity.y
        return math.sqrt(dx * dx + dy * dy)

    def render_hp(self, screen, camera=None):
        if camera and hasattr(self, 'screen_manager') and self.screen_manager:
            screen_x, screen_y = self.screen_manager.world_to_screen(self.x, self.y, camera)
            zoom_scale = camera.zoom * self.screen_manager.render_scale
        else:
            screen_x = self.x
            screen_y = self.y
            zoom_scale = 1.0

        hp_percent = self.current_hp / self.max_hp

        bar_width = int(32 * zoom_scale)
        bar_height = max(1, int(3 * zoom_scale))
        bar_x = screen_x - bar_width // 2

        sprite_height = int(self.map_sprite_size * zoom_scale)
        foot_offset = int(sprite_height * 0.2)
        sprite_top = (screen_y + foot_offset) - sprite_height
        bar_y = sprite_top + 10

        pygame.draw.rect(screen, (60, 60, 60), (bar_x, bar_y, bar_width, bar_height))

        if self.is_boss:
            color = (0, 0, 255)
        else:
            if not self.is_shiny:
                if hp_percent > 0.5:
                    color = (0, 200, 0)
                elif hp_percent > 0.25:
                    color = (255, 255, 0)
                else:
                    color = (255, 0, 0)
            else:
                color = (255, 0, 0)

        progress_width = int(bar_width * hp_percent)
        if progress_width > 0:
            pygame.draw.rect(screen, color, (bar_x, bar_y, progress_width, bar_height))

        pygame.draw.rect(screen, (100, 100, 100), (bar_x, bar_y, bar_width, bar_height), 1)

    def _get_font(self, size):
        """Obtém fonte do cache"""
        if size not in _FONT_CACHE:
            try:
                _FONT_CACHE[size] = pygame.font.Font(None, size)
            except:
                _FONT_CACHE[size] = pygame.font.SysFont('Arial', size)
        return _FONT_CACHE[size]

    def render(self, screen, camera=None, show_hp=True):
        if camera and hasattr(self, 'screen_manager') and self.screen_manager:
            screen_x, screen_y = self.screen_manager.world_to_screen(self.x, self.y, camera)
            zoom_scale = camera.zoom * self.screen_manager.render_scale
        else:
            screen_x = self.x
            screen_y = self.y
            zoom_scale = 1.0

        sprite_to_render = self._prepare_sprite(zoom_scale)

        if sprite_to_render:
            sprite_rect = self._render_sprite(screen, sprite_to_render, screen_x, screen_y, zoom_scale)
        else:
            sprite_rect = self._render_placeholder(screen, screen_x, screen_y, zoom_scale)

        if self.is_wild and sprite_rect:
            self._render_wild_text(screen, sprite_rect, zoom_scale)

        if show_hp:
            self.render_hp(screen, camera)

        if hasattr(self, 'show_debug') and self.show_debug:
            self._render_debug(screen, screen_x, screen_y, zoom_scale, sprite_rect)

    def _prepare_sprite(self, zoom_scale):
        if not self.sprite:
            return None

        if self.is_boss:
            orig_width, orig_height = self.sprite.get_width(), self.sprite.get_height()
            new_width = orig_width * 2
            new_height = orig_height * 2
            return pygame.transform.scale(self.sprite, (new_width, new_height))

        return self.sprite

    def _render_sprite(self, screen, sprite, screen_x, screen_y, zoom_scale):
        current_width, current_height = sprite.get_width(), sprite.get_height()
        final_width = max(1, int(current_width * zoom_scale))
        final_height = max(1, int(current_height * zoom_scale))

        if final_width != current_width or final_height != current_height:
            scaled_sprite = pygame.transform.scale(sprite, (final_width, final_height))
        else:
            scaled_sprite = sprite

        foot_offset = int(final_height * 0.2)
        sprite_rect = scaled_sprite.get_rect()
        sprite_rect.bottom = int(screen_y) + foot_offset
        sprite_rect.centerx = int(screen_x)

        screen.blit(scaled_sprite, sprite_rect)
        return sprite_rect

    def _render_placeholder(self, screen, screen_x, screen_y, zoom_scale):
        size = int((64 if self.is_boss else self.map_sprite_size) * zoom_scale)
        foot_offset = int(size * 0.2)

        rect = pygame.Rect(0, 0, size, size)
        rect.bottom = int(screen_y) + foot_offset
        rect.centerx = int(screen_x)

        pygame.draw.rect(screen, (255, 0, 255), rect)
        pygame.draw.rect(screen, (255, 255, 255), rect, 2)
        return rect

    def _render_wild_text(self, screen, sprite_rect, zoom_scale):
        name_font_size = max(5, int(6 * zoom_scale))
        level_font_size = max(4, int(6 * zoom_scale))

        name_font = self._get_font(name_font_size)
        level_font = self._get_font(level_font_size)

        name_text = f"{self.name} - "
        level_text = f"lv. {self.level:02d}"

        text_color = (255, 255, 255)
        outline_color = (0, 0, 0)

        if self.is_shiny:
            level_color = (255, 215, 0)
        elif self.is_boss:
            level_color = (255, 100, 100)
            text_color = (255, 100, 100)
        else:
            level_color = (255, 255, 255)

        name_surface = name_font.render(name_text, True, text_color)
        level_surface = level_font.render(level_text, True, level_color)
        name_outline = name_font.render(name_text, True, outline_color)
        level_outline = level_font.render(level_text, True, outline_color)

        name_width = name_surface.get_width()
        level_width = level_surface.get_width()
        total_width = name_width + 2 + level_width
        start_x = sprite_rect.centerx - total_width // 2

        text_y = sprite_rect.top - name_font_size
        name_x, name_y = start_x, text_y
        level_x = start_x + name_width + 2
        level_y = text_y + (name_font_size - level_font_size)

        for dx, dy in [(-1, -1), (-1, 1), (1, -1), (1, 1)]:
            screen.blit(name_outline, (name_x + dx, name_y + dy))
            screen.blit(level_outline, (level_x + dx, level_y + dy))

        screen.blit(name_surface, (name_x, name_y))
        screen.blit(level_surface, (level_x, level_y))

    def _render_debug(self, screen, screen_x, screen_y, zoom_scale, sprite_rect):
        if sprite_rect:
            foot_offset = int(sprite_rect.height * 0.2)
        else:
            size = int((64 if self.is_boss else self.map_sprite_size) * zoom_scale)
            foot_offset = int(size * 0.2)

        pygame.draw.circle(screen, (255, 0, 0), (int(screen_x), int(screen_y) + foot_offset), 6, 2)

        if sprite_rect:
            pygame.draw.circle(screen, (0, 255, 0), (sprite_rect.centerx, sprite_rect.centery), 4, 1)
            pygame.draw.line(screen, (255, 255, 0),
                           (sprite_rect.left, int(screen_y) + foot_offset),
                           (sprite_rect.right, int(screen_y) + foot_offset), 1)

    def get_info_string(self):
        return (f"{self.name} Lv.{self.level}\n"
                f"HP: {self.current_hp}/{self.max_hp}\n"
                f"Tipos: {'/'.join(self.types)}\n"
                f"Natureza: {self.nature}")