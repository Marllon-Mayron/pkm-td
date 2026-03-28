# src/entities/pokemon.py
import pygame
import math
import uuid
import random
from typing import List, Dict, Optional

from src.data.move_data import MoveData
from src.entities.base import Entity
from src.data.pokedex import Pokedex
from src.managers.evolution_manager import evolution_manager
from src.entities.move import Move

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
        self.game_scene = None
        self.battle_system = None
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

        # ===== 8. TAMANHO DO SPRITE (antes de carregar sprites) =====
        self.map_sprite_size = self.pokedex.get_map_sprite_size(pokemon_id, shiny)
        width = self.map_sprite_size
        height = self.map_sprite_size

        # ===== 9. INICIALIZAR ATRIBUTOS DE ANIMAÇÃO (antes de _load_sprites) =====
        self.raw_animations = None
        self.inmap_animations = {}  # Dicionário para animações separadas
        self.current_animation = "idle"  # "idle" ou "walk"
        self.is_moving = False
        self.walk_frame_durations = []
        self.idle_frame_durations = []
        self.frame_durations = []

        # ===== 10. CARREGAR SPRITES =====
        self._load_sprites(pokemon_id, shiny)

        # Pega o primeiro sprite da animação idle como inicial
        sprite = None
        if self.inmap_frames and "down" in self.inmap_frames and self.inmap_frames["down"]:
            sprite = self.inmap_frames["down"][0]

        super().__init__(x, y, width, height, sprite)

        # ===== 11. ATRIBUTOS DE JOGO =====
        self.is_wild = is_wild
        self.is_in_team = False
        self.is_selected = False

        # ===== 12. MOVIMENTO =====
        self.path = []
        self.path_index = 0
        self.move_speed = 2.0
        self.original_path = None
        self.path_index_origin = 0
        self.is_returning_with_item = False
        if is_wild:
            self.base_move_speed = self._get_cached_move_speed()
            self.move_speed = self.base_move_speed
        else:
            self.base_move_speed = 2.0
            self.move_speed = 2.0

        # ===== 13. COMBATE =====
        self.can_attack = True
        self.attack_cooldown = 0
        self.attack_cooldown_max = 60
        self.target = None
        self.has_no_pp = False

        # ===== 14. EFEITOS VISUAIS =====
        self.hp_bar_width = 48
        self.hp_bar_height = 5
        self.miss_timer = 0.0

        # ===== 15. POSIÇÃO E MOVIMENTAÇÃO =====
        self.last_x = x
        self.last_y = y

        # ===== 16. ITENS =====
        self.is_carrying = None
        self.capture_range = 10
        self.is_returning_with_item = False

        # ===== 17. ATRIBUTOS DE COMBATE =====
        self.attack_range = 60
        self.combat_state = "idle"
        self.original_spot_x = x
        self.original_spot_y = y

        # ===== 18. COOLDOWNS =====
        self.charge_cooldown = 0.0
        self.charge_cooldown_max = 1.2

        # ===== 19. STATS DE COMBATE =====
        self.attack_damage = self._calculate_attack_damage()
        self.defense_value = self._calculate_defense()

        # ===== 20. RASTREAMENTO DE DANO =====
        self.damage_contributions = {}
        self.last_attacker = None

        # ===== 21. SCREEN MANAGER =====
        self.screen_manager = None

        # ===== 22. DEBUG =====
        self.show_debug = False

        # ===== 23. MOVES =====
        self.move_data = MoveData()
        self.moves: List[Move] = []
        self.current_move_index = 0
        self._initialize_moves()

    def _load_sprites(self, pokemon_id, shiny):
        """Carrega sprites com cache"""
        cache_key = f"{pokemon_id}_{shiny}"

        if cache_key in _SPRITE_CACHE:
            cached = _SPRITE_CACHE[cache_key]
            self.ui_sprite = cached["ui"]
            self.battle_sprite = cached["battle"]
            self.inmap_frames = cached["inmap"]
            self.inmap_animations = cached.get("animations", {})
        else:
            self.ui_sprite = self.pokedex.get_sprite(pokemon_id, "front", shiny)
            self.battle_sprite = self.pokedex.get_sprite(pokemon_id, "back", shiny)
            self.inmap_frames = self.pokedex.get_inmap_animation(pokemon_id, shiny)

            # Tenta carregar animações separadas
            self.inmap_animations = {}
            if hasattr(self.pokedex, 'get_raw_inmap_data'):
                try:
                    raw_data = self.pokedex.get_raw_inmap_data(pokemon_id, shiny)
                    self.inmap_animations = raw_data.get("animations", {})
                    self.raw_animations = raw_data  # Guarda os dados brutos
                except Exception as e:
                    print(f"[ERRO] Falha ao carregar dados brutos: {e}")

            _SPRITE_CACHE[cache_key] = {
                "ui": self.ui_sprite,
                "battle": self.battle_sprite,
                "inmap": self.inmap_frames,
                "animations": self.inmap_animations
            }

        self.current_direction = "down"
        self.current_frame = 0
        self.animation_timer = 0
        self.animation_speed = 0.1

        # Carrega os timings das animações
        self._load_animation_timings()

    def _load_animation_timings(self):
        """Carrega os tempos de duração dos frames do AnimData.xml"""
        # Verifica se temos os dados brutos
        if not hasattr(self, 'raw_animations') or not self.raw_animations:
            # Fallback: timings padrão
            self.walk_frame_durations = [8, 8, 8, 8]  # 4 frames com 8 ticks cada
            self.idle_frame_durations = [10, 10, 10, 10]  # 4 frames com 10 ticks cada
            self.frame_durations = self.idle_frame_durations
            return

        anim_data = self.raw_animations.get("anim_data", {})

        # Carrega timings para Walk
        walk_info = anim_data.get("Walk", {})
        if "durations" in walk_info and walk_info["durations"]:
            self.walk_frame_durations = walk_info["durations"]
        else:
            self.walk_frame_durations = [8, 8, 8, 8]

        # Carrega timings para Idle
        idle_info = anim_data.get("Idle", {})
        if "durations" in idle_info and idle_info["durations"]:
            self.idle_frame_durations = idle_info["durations"]
        else:
            self.idle_frame_durations = [10, 10, 10, 10]

        # Define duração atual baseada na animação atual
        self._update_current_durations()

    def _update_current_durations(self):
        """Atualiza as durações dos frames baseado na animação atual"""
        if hasattr(self, 'current_animation'):
            if self.current_animation == "walk" and hasattr(self, 'walk_frame_durations'):
                self.frame_durations = self.walk_frame_durations
            elif hasattr(self, 'idle_frame_durations'):
                self.frame_durations = self.idle_frame_durations
            else:
                self.frame_durations = [8, 8, 8, 8]  # Fallback

            # Reseta o frame atual se necessário
            if hasattr(self, 'current_frame') and self.current_frame >= len(self.frame_durations):
                self.current_frame = 0

    def set_animation(self, animation_name: str):
        """
        Troca a animação atual
        animation_name: "idle" ou "walk"
        """
        if not hasattr(self, 'current_animation'):
            return

        if animation_name == self.current_animation:
            return

        self.current_animation = animation_name
        self.current_frame = 0
        self.animation_timer = 0
        self._update_current_durations()

        # Atualiza o sprite imediatamente com o primeiro frame da nova animação
        self._update_sprite_from_current_animation()

    def _update_sprite_from_current_animation(self):
        """Atualiza o sprite baseado na animação atual, direção e frame"""
        # Tenta usar as animações separadas primeiro (com 8 direções)
        if hasattr(self, 'inmap_animations') and self.current_animation in self.inmap_animations:
            anim_frames = self.inmap_animations[self.current_animation]

            # Tenta pegar a direção completa
            if self.current_direction in anim_frames:
                frames = anim_frames[self.current_direction]
                if frames and hasattr(self, 'current_frame') and self.current_frame < len(frames):
                    self.sprite = frames[self.current_frame]
                    return

            # Fallback: mapeia direção de 4 para 8
            dir_mapping = {
                "down": ["down", "down-left", "down-right"],
                "left": ["left", "down-left", "up-left"],
                "right": ["right", "down-right", "up-right"],
                "up": ["up", "up-left", "up-right"]
            }

            for src_dir in dir_mapping.get(self.current_direction, [self.current_direction]):
                if src_dir in anim_frames:
                    frames = anim_frames[src_dir]
                    if frames and hasattr(self, 'current_frame') and self.current_frame < len(frames):
                        self.sprite = frames[self.current_frame]
                        return

        # Fallback: usa o sistema antigo (inmap_frames)
        if hasattr(self, 'inmap_frames') and self.current_direction in self.inmap_frames:
            frames_list = self.inmap_frames[self.current_direction]
            if frames_list and hasattr(self, 'current_frame') and self.current_frame < len(frames_list):
                self.sprite = frames_list[self.current_frame]

    def _get_current_animation_frame_count(self) -> int:
        """Retorna o número de frames da animação atual para a direção atual"""
        # Tenta pegar das animações separadas
        if hasattr(self, 'inmap_animations') and self.current_animation in self.inmap_animations:
            anim_frames = self.inmap_animations[self.current_animation]

            # Tenta pegar a direção completa
            if self.current_direction in anim_frames:
                return len(anim_frames[self.current_direction])

            # Fallback: verifica direções alternativas
            dir_mapping = {
                "down": ["down", "down-left", "down-right"],
                "left": ["left", "down-left", "up-left"],
                "right": ["right", "down-right", "up-right"],
                "up": ["up", "up-left", "up-right"]
            }

            for src_dir in dir_mapping.get(self.current_direction, [self.current_direction]):
                if src_dir in anim_frames:
                    return len(anim_frames[src_dir])

        # Fallback: usa o sistema antigo
        if hasattr(self, 'inmap_frames') and self.current_direction in self.inmap_frames:
            return len(self.inmap_frames[self.current_direction])

        return 1  # Mínimo 1 frame

    def _is_moving(self) -> bool:
        """
        Verifica se o Pokémon está em movimento
        Baseado na posição atual vs última posição
        """
        if hasattr(self, 'last_x') and hasattr(self, 'last_y'):
            dx = abs(self.x - self.last_x)
            dy = abs(self.y - self.last_y)
            # Se moveu mais que 0.5 pixels, considera que está se movendo
            return (dx + dy) > 0.5
        return False

    def _update_animation(self, dt):
        """
        Atualiza animação do sprite baseado no movimento
        """
        # Verifica se está em movimento para trocar animação
        is_moving_now = self._is_moving()

        if is_moving_now and not self.is_moving:
            # Começou a se mover
            self.is_moving = True
            self.set_animation("walk")
        elif not is_moving_now and self.is_moving:
            # Parou de se mover
            self.is_moving = False
            self.set_animation("idle")

        # Atualiza o timer da animação
        self.animation_timer += dt

        # Calcula o tempo necessário para o frame atual
        frame_time = self.animation_speed
        if hasattr(self, 'frame_durations') and self.frame_durations and hasattr(self,
                                                                                 'current_frame') and self.current_frame < len(
                self.frame_durations):
            # Converte duração (em ticks de 60fps) para segundos
            # Cada tick = 1/60 segundo
            frame_time = self.frame_durations[self.current_frame] / 60.0

        if self.animation_timer >= frame_time:
            self.animation_timer = 0

            # Avança para o próximo frame
            max_frames = self._get_current_animation_frame_count()
            if max_frames > 0:
                self.current_frame = (self.current_frame + 1) % max_frames
                self._update_sprite_from_current_animation()


    def set_battle_system(self, battle_system):
        """Define o sistema de combate para este Pokémon"""
        self.battle_system = battle_system

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

    def get_current_move(self):
        """Retorna o move atual do Pokémon"""
        if self.moves and 0 <= self.current_move_index < len(self.moves):
            return self.moves[self.current_move_index]
        return None

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
        """Realiza a evolução mantendo os moves compatíveis"""
        old_name = self.name
        old_level = self.level

        new_pokemon_data = self.pokedex.get_pokemon(new_id)
        if not new_pokemon_data:
            return

        # Atualiza dados básicos
        self.id = new_id
        self.name = new_pokemon_data["name"].capitalize()
        self.types = new_pokemon_data["types"]
        self.base_stats = new_pokemon_data["base_stats"]

        # Recalcula stats (nível mantido)
        self._calculate_stats()
        self.current_hp = self.max_hp

        # Recarrega sprites
        self._load_sprites(new_id, self.is_shiny)
        self.map_sprite_size = self.pokedex.get_map_sprite_size(new_id, self.is_shiny)

        # ===== GERENCIAMENTO DE MOVES NA EVOLUÇÃO =====

        # Obter moves que o novo Pokémon aprende até o nível atual
        new_learnset = set(self.move_data.get_moves_at_level(self.id, self.level))

        # Moves que o Pokémon já tem
        current_move_names = set(move.name.lower() for move in self.moves)

        # Novos moves que o Pokémon evolutivo aprende e o antigo não tinha
        moves_to_learn = new_learnset - current_move_names

        for move_name in moves_to_learn:
            # Aprende novos moves, mantendo os existentes (substitui o último se já tiver 4)
            self._learn_move_without_replacement(move_name)

        print(f"[EVOLUÇÃO] ✓ {old_name} (Lv.{old_level}) evoluiu para {self.name}!")
        print(f"[EVOLUÇÃO] Moves atuais: {[m.name for m in self.moves]}")

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

            # Verifica evolução - agora com overlay
            evolution = evolution_manager.check_evolution(self.id, current_level=self.level)
            if evolution and self.game_scene:
                # Se tem overlay de evolução, abre ele
                self.game_scene.open_evolution_overlay(self, evolution)
                return True  # Indica que a evolução está pendente

        return leveled_up

    def level_up(self):
        old_level = self.level
        self.xp -= self.xp_to_next
        self.level += 1
        self._calculate_stats()
        self.current_hp = self.max_hp
        self.xp_to_next = self._calculate_xp_needed()

        # Verifica novos moves
        new_moves, pending_moves = self.check_new_moves_on_level_up(old_level)
        if new_moves:
            print(f"[LEVEL UP] {self.name} subiu para Lv.{self.level} e aprendeu: {', '.join(new_moves)}")

        # Limpa cache de velocidade
        cache_key = (self.id, self.level, self.speed_stat, self.is_shiny, self.is_boss)
        self._speed_cache.pop(cache_key, None)

        # NÃO chama evolução automática aqui - será chamada no gain_xp após level_up
        return pending_moves

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
        """Encontra o inimigo mais próximo (versão original)"""
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

    def _handle_idle_state(self, dt, enemies):
        """Estado parado - procura inimigo"""
        nearest = self.find_nearest_enemy(enemies)

        if nearest and self.charge_cooldown <= 0:
            print(f"[COMBAT] {self.name}: Encontrou inimigo {nearest.name}")
            self.target = nearest
            self.combat_state = "charging"

    def _handle_charging_state(self, dt):
        """Estado indo em direção ao alvo - com suporte para ataques de status e especiais"""
        if not self.target or not self.target.is_alive():
            self.combat_state = "returning"
            self.target = None
            return

        # Verificar se o Pokémon tem PP
        current_move = self.get_current_move()
        if not current_move or current_move.current_pp <= 0:
            print(f"[COMBAT] {self.name} está sem PP para {current_move.name if current_move else 'ataque'}!")
            self.combat_state = "returning"
            self.target = None
            self.has_no_pp = True
            return

        # Verifica o tipo do move atual
        is_status_move = current_move.category == "status"
        is_special_move = current_move.category == "special"

        # Ataques de status e especiais são executados à distância
        if is_status_move or is_special_move:
            attack_type = "status" if is_status_move else "especial"
            print(f"[COMBAT] {self.name} usou {current_move.name} ({attack_type}) à distância!")

            if self.battle_system:
                self.battle_system.attempt_attack(self, self.target)
            else:
                hit_chance = current_move.accuracy / 100
                will_hit = random.random() <= hit_chance
                if will_hit:
                    self._perform_charge_attack(self.target)
                else:
                    print(f"[COMBAT] {current_move.name} errou!")
                    self._show_miss_on_self()
                current_move.current_pp -= 1

            self.combat_state = "returning"
            self.charge_cooldown = self.charge_cooldown_max
            return

        # Para ataques físicos, move em direção ao alvo
        dx = self.target.x - self.x
        dy = self.target.y - self.y
        distance = math.sqrt(dx * dx + dy * dy)

        # Se estiver perto o suficiente, ataca
        if distance < 8:  # Aumentado de 5 para 8 para dar espaço aos sprites maiores
            if self.battle_system:
                self.battle_system.attempt_attack(self, self.target)
            else:
                hit_chance = current_move.accuracy / 100
                will_hit = random.random() <= hit_chance
                if will_hit:
                    self._perform_charge_attack(self.target)
                else:
                    print(f"[COMBAT] {current_move.name} errou!")
                    self._show_miss_on_self()
                current_move.current_pp -= 1

            self.combat_state = "returning"
            self.charge_cooldown = self.charge_cooldown_max
            return

        # Move em direção ao alvo
        if distance > 0:
            move_distance = self.move_speed * dt * 60
            move_x = (dx / distance) * move_distance
            move_y = (dy / distance) * move_distance

            # Não ultrapassar o alvo
            if abs(move_x) > abs(dx):
                move_x = dx
            if abs(move_y) > abs(dy):
                move_y = dy

            self.x += move_x
            self.y += move_y
            self.rect.x, self.rect.y = self.x, self.y

            # Atualizar direção para animação (8 direções baseado no ângulo)
            angle = math.atan2(dy, dx)
            # Converte ângulo para direção (8 direções)
            if angle >= -math.pi/8 and angle < math.pi/8:
                self.current_direction = "right"
            elif angle >= math.pi/8 and angle < 3*math.pi/8:
                self.current_direction = "down-right"
            elif angle >= 3*math.pi/8 and angle < 5*math.pi/8:
                self.current_direction = "down"
            elif angle >= 5*math.pi/8 and angle < 7*math.pi/8:
                self.current_direction = "down-left"
            elif angle >= 7*math.pi/8 or angle < -7*math.pi/8:
                self.current_direction = "left"
            elif angle >= -7*math.pi/8 and angle < -5*math.pi/8:
                self.current_direction = "up-left"
            elif angle >= -5*math.pi/8 and angle < -3*math.pi/8:
                self.current_direction = "up"
            else:
                self.current_direction = "up-right"

    def _show_miss_on_self(self):
        """Mostra o texto MISS no próprio Pokémon (atacante)"""
        # Inicia o timer para mostrar o texto MISS
        self.miss_timer = 0.6  # 0.6 segundos de duração

    def _show_miss_on_target(self, target):
        """Mostra o texto MISS no alvo (mantido para compatibilidade)"""
        if not hasattr(target, 'miss_timer'):
            target.miss_timer = 0.0
        target.miss_timer = 0.6

    def _handle_returning_state(self, dt):
        """Estado voltando para posição original - atualiza direção"""
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

            # Atualizar direção para animação
            if abs(dx) > abs(dy):
                self.current_direction = "right" if dx > 0 else "left"
            else:
                self.current_direction = "down" if dy > 0 else "up"

    def _perform_attack(self, target):
        """Realiza ataque - usando battle_system se disponível"""
        print(f"[ATTACK] {self.name} atacando {target.name}!")

        if self.battle_system:
            # Tenta atacar com o sistema de moves
            success = self.battle_system.attempt_attack(self, target)
            if success:
                return

        # Fallback: ataque simples
        print(f"[ATTACK] {self.name}: Usando ataque simples (fallback)")
        self._perform_charge_attack(target)

    def _perform_charge_attack(self, target):
        """Ataque de carga - usa o sistema de moves"""
        # Verificar novamente se tem PP antes de atacar
        current_move = self.get_current_move()
        if not current_move or current_move.current_pp <= 0:
            print(f"[ATTACK] {self.name} não pode atacar - sem PP!")
            self.combat_state = "returning"
            self.target = None
            return

        if self.battle_system:
            # Usa o sistema de batalha com o move atual
            success = self.battle_system.attempt_attack(self, target)
            if success:
                print(
                    f"[ATTACK] {self.name} usou {current_move.name if current_move else 'ataque'} em {target.name}!")
                return

        # Fallback: ataque simples (caso não tenha battle_system)
        print(f"[ATTACK] {self.name}: Ataque simples em {target.name}!")
        base_damage = self.attack_damage * (self.level / 8)
        damage_multiplier = random.uniform(0.85, 1.15)
        damage = int(base_damage * damage_multiplier)

        defense_factor = max(0.4, 1.0 - (target.defense_value / 800))
        final_damage = max(2, int(damage * defense_factor))

        target.take_damage(final_damage, attacker=self)

    def _charge_towards_target(self, dt, target):
        """Move em direção ao alvo"""
        dx = target.x - self.x
        dy = target.y - self.y
        distance = math.sqrt(dx * dx + dy * dy)

        if distance < 1:
            return

        # Velocidade de movimento (ajustada)
        move_distance = self.move_speed * dt * 60

        # Se está muito perto, não precisa se mover
        if distance < self.map_sprite_size / 2 + 5:
            return

        move_x = (dx / distance) * move_distance
        move_y = (dy / distance) * move_distance

        # Não ultrapassar o alvo
        if abs(move_x) > abs(dx):
            move_x = dx
        if abs(move_y) > abs(dy):
            move_y = dy

        self.x += move_x
        self.y += move_y
        self.rect.x, self.rect.y = self.x, self.y

        # Atualizar direção para animação
        if abs(dx) > abs(dy):
            self.current_direction = "right" if dx > 0 else "left"
        else:
            self.current_direction = "down" if dy > 0 else "up"

    def _return_to_spot(self, dt):
        """Retorna ao ponto original"""
        dx = self.original_spot_x - self.x
        dy = self.original_spot_y - self.y
        distance = math.sqrt(dx * dx + dy * dy)

        if distance < 5:
            self.x, self.y = self.original_spot_x, self.original_spot_y
            self.rect.x, self.rect.y = self.x, self.y
            self.combat_state = "idle"
            self.target = None
            return

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

    def _perform_move_attack(self, target):
        """Realiza ataque com move atual"""
        if not self.battle_system:
            # Fallback para sistema antigo
            self._attack_target(target)
            return

        # Tenta atacar com o sistema de moves
        success = self.battle_system.attempt_attack(self, target)

        if success:
            # Ataque foi executado
            pass
        else:
            # Não conseguiu atacar (sem PP, etc), usa ataque padrão
            self._attack_target(target)

        self.attack_cooldown = self.attack_cooldown_max

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
        """Recebe dano"""
        old_hp = self.current_hp
        self.current_hp = max(0, self.current_hp - damage)

        # NOTA: O som de impacto já é tocado pelo BattleSystem ou Projectile
        # Aqui só fazemos o som de low_hp (opcional) e faint

        # Se o HP ficou muito baixo, toca som de aviso (opcional)
        if self.current_hp > 0 and self.current_hp <= self.max_hp * 0.2:
            from src.managers.move_sound_manager import move_sound_manager
            # Tenta tocar som de low_hp se existir
            move_sound_manager.play_attack_sound("low_hp")  # Som opcional

        if attacker and self.is_wild:
            attacker_id = id(attacker)
            actual_damage = min(damage, old_hp)
            self.damage_contributions[attacker_id] = self.damage_contributions.get(attacker_id, 0) + actual_damage
            self.last_attacker = attacker

        # Se o Pokémon morreu, toca som de faint e libera o item
        if self.current_hp <= 0:
            from src.managers.move_sound_manager import move_sound_manager
            move_sound_manager.play_attack_sound("faint")
            print(f"[BATTLE] {self.name} foi derrotado!")

            # ===== LIBERA O ITEM SE ESTAVA CARRREGANDO =====
            if self.is_carrying:
                carried_item = self.is_carrying
                # CORREÇÃO: usa item_name
                print(f"[ITEM] {carried_item.item_name} será liberado com a morte de {self.name}")
                carried_item.reset_capture()
                carried_item.is_protected = True
                carried_item.is_stolen = False
                carried_item.carried_by = None
                self.is_carrying = None

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

    def update(self, dt, player=None, enemies=None, items=None):
        """Update do Pokémon - versão compatível com WaveManager"""
        # Guarda posição anterior para detectar movimento
        self.last_x = self.x
        self.last_y = self.y

        # Atualizar timer do MISS
        if hasattr(self, 'miss_timer') and self.miss_timer > 0:
            self.miss_timer -= dt
            if self.miss_timer < 0:
                self.miss_timer = 0

        # Cooldown de ataque
        if not self.can_attack:
            self.attack_cooldown -= 1
            if self.attack_cooldown <= 0:
                self.can_attack = True

        # ===== MOVIMENTO: SÓ EXECUTA SE NÃO FOR CONTROLADO PELO WAVE MANAGER =====
        # Verifica se este Pokémon está sob controle do wave manager
        # Inimigos selvagens com path_index_origin definido são controlados pelo WaveManager
        is_wave_controlled = hasattr(self, 'path_index_origin') and self.is_wild

        # BOSS também é controlado pelo WaveManager
        if self.is_boss:
            is_wave_controlled = True

        if not is_wave_controlled:
            # Movimento para Pokémon não controlados por waves (como aliados colocados)
            self._update_movement(dt, items)

        # ===== CAPTURA DE ITENS: SÓ EXECUTA SE NÃO FOR CONTROLADO =====
        if self.is_wild and not is_wave_controlled and items is not None and not self.is_carrying:
            self._check_item_capture(items)

        # Atualização do item carregado (sempre)
        if self.is_carrying:
            self.is_carrying.update_capture(dt)

        # ===== ANIMAÇÃO (sempre) =====
        self._update_animation(dt)

    def _update_movement(self, dt, items=None):
        """Movimento via path (para aliados ou inimigos sem wave control)"""
        if not self.path or len(self.path) == 0 or self.path_index >= len(self.path):
            return

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

            # Atualiza direção baseado no movimento
            if abs(dx) > abs(dy):
                self.current_direction = "right" if dx > 0 else "left"
            else:
                self.current_direction = "down" if dy > 0 else "up"

        self.rect.x, self.rect.y = self.x, self.y

    def _check_item_capture(self, items):
        """Verifica captura de item (apenas para Pokémon sem wave control)"""
        for item in items:
            if hasattr(item, 'is_protected') and item.is_protected and not item.carried_by:
                dx = self.x - item.x
                dy = self.y - item.y
                if dx * dx + dy * dy < self.capture_range * self.capture_range:
                    item.start_capture(self)
                    break

    def update_combat(self, dt, enemies):
        """Atualiza lógica de combate - versão corrigida"""
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

    def get_distance_to(self, entity):
        dx = self.x - entity.x
        dy = self.y - entity.y
        return math.sqrt(dx * dx + dy * dy)

    def _get_font(self, size):
        """Obtém fonte do cache"""
        if size not in _FONT_CACHE:
            try:
                _FONT_CACHE[size] = pygame.font.Font(None, size)
            except:
                _FONT_CACHE[size] = pygame.font.SysFont('Arial', size)
        return _FONT_CACHE[size]

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
        """
        Renderiza o sprite com posicionamento correto.
        O ponto (screen_x, screen_y) é o centro do spot onde o Pokémon deve ficar.
        """
        current_width, current_height = sprite.get_width(), sprite.get_height()
        final_width = max(1, int(current_width * zoom_scale))
        final_height = max(1, int(current_height * zoom_scale))

        if final_width != current_width or final_height != current_height:
            scaled_sprite = pygame.transform.scale(sprite, (final_width, final_height))
        else:
            scaled_sprite = sprite

        # Ancoragem pelo CENTRO do sprite (não pela base)
        sprite_rect = scaled_sprite.get_rect()
        sprite_rect.center = (int(screen_x), int(screen_y))

        screen.blit(scaled_sprite, sprite_rect)
        return sprite_rect

    def render(self, screen, camera=None, show_hp=True):
        """Renderiza o Pokémon com todos os elementos visuais ajustados"""
        if camera and hasattr(self, 'screen_manager') and self.screen_manager:
            screen_x, screen_y = self.screen_manager.world_to_screen(self.x, self.y, camera)
            zoom_scale = camera.zoom * self.screen_manager.render_scale
        else:
            screen_x = self.x
            screen_y = self.y
            zoom_scale = 1.0

        sprite_to_render = self._prepare_sprite(zoom_scale)

        sprite_rect = None
        if sprite_to_render:
            sprite_rect = self._render_sprite(screen, sprite_to_render, screen_x, screen_y, zoom_scale)
        else:
            sprite_rect = self._render_placeholder(screen, screen_x, screen_y, zoom_scale)

        # Renderiza textos e barras acima do sprite
        if sprite_rect:
            # Ajusta a posição dos elementos visuais baseado no sprite_rect
            if self.is_wild:
                self._render_wild_text(screen, sprite_rect, zoom_scale)

            if show_hp:
                self._render_hp_bar(screen, sprite_rect, zoom_scale)

            # Renderiza texto MISS
            if hasattr(self, 'miss_timer') and self.miss_timer > 0:
                self._render_miss_text(screen, sprite_rect, zoom_scale)

        if hasattr(self, 'show_debug') and self.show_debug and sprite_rect:
            self._render_debug(screen, screen_x, screen_y, zoom_scale, sprite_rect)

    def render_hp_enemy(self, screen, camera=None):
        """Método de compatibilidade para chamar o _render_hp_bar"""
        if camera and hasattr(self, 'screen_manager') and self.screen_manager:
            screen_x, screen_y = self.screen_manager.world_to_screen(self.x, self.y, camera)
            zoom_scale = camera.zoom * self.screen_manager.render_scale

            # Prepara o sprite para obter o retângulo
            sprite_to_render = self._prepare_sprite(zoom_scale)
            if sprite_to_render:
                current_width, current_height = sprite_to_render.get_width(), sprite_to_render.get_height()
                final_width = max(1, int(current_width * zoom_scale))
                final_height = max(1, int(current_height * zoom_scale))

                if final_width != current_width or final_height != current_height:
                    scaled_sprite = pygame.transform.scale(sprite_to_render, (final_width, final_height))
                else:
                    scaled_sprite = sprite_to_render

                sprite_rect = scaled_sprite.get_rect()
                sprite_rect.center = (int(screen_x), int(screen_y))

                self._render_hp_bar(screen, sprite_rect, zoom_scale)
        else:
            # Fallback: cria um retângulo temporário
            temp_rect = pygame.Rect(0, 0, self.map_sprite_size, self.map_sprite_size)
            temp_rect.center = (int(self.x), int(self.y))
            self._render_hp_bar(screen, temp_rect, 1.0)

    def _render_hp_bar(self, screen, sprite_rect, zoom_scale):
        """Renderiza barra de HP ajustada baseada no retângulo do sprite"""
        hp_percent = self.current_hp / self.max_hp

        # Ajusta tamanho da barra baseado no tamanho do sprite
        bar_width = int(self.hp_bar_width * zoom_scale)
        bar_height = max(2, int(self.hp_bar_height * zoom_scale))
        bar_x = sprite_rect.centerx - bar_width // 2

        # Barra fica a 5 pixels ACIMA do sprite (não dentro)
        bar_y = sprite_rect.top - bar_height - 5

        # Fundo da barra
        pygame.draw.rect(screen, (60, 60, 60), (bar_x, bar_y, bar_width, bar_height))

        # Cor da barra baseado no HP
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

        # Borda da barra
        pygame.draw.rect(screen, (100, 100, 100), (bar_x, bar_y, bar_width, bar_height), 1)

    def _render_wild_text(self, screen, sprite_rect, zoom_scale):
        """Renderiza nome e nível do Pokémon selvagem acima do sprite"""
        # Aumenta o tamanho da fonte para sprites maiores
        name_font_size = max(8, int(10 * zoom_scale))
        level_font_size = max(7, int(9 * zoom_scale))

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

        # Posiciona ACIMA da barra de HP (barra está a -5 do topo)
        # Então texto fica acima da barra
        text_y = sprite_rect.top - self.hp_bar_height - 10 - name_font_size

        name_x, name_y = start_x, text_y
        level_x = start_x + name_width + 2
        level_y = text_y + (name_font_size - level_font_size)

        # Desenha contorno
        for dx, dy in [(-1, -1), (-1, 1), (1, -1), (1, 1)]:
            screen.blit(name_outline, (name_x + dx, name_y + dy))
            screen.blit(level_outline, (level_x + dx, level_y + dy))

        # Desenha texto principal
        screen.blit(name_surface, (name_x, name_y))
        screen.blit(level_surface, (level_x, level_y))

    def _render_miss_text(self, screen, sprite_rect, zoom_scale):
        """Renderiza o texto MISS acima do Pokémon (atacante)"""
        if self.miss_timer <= 0:
            return

        font_size = max(10, int(16 * zoom_scale))
        font = self._get_font(font_size)

        text = "MISS!"
        text_surface = font.render(text, True, (255, 100, 100))
        text_outline = font.render(text, True, (100, 0, 0))

        text_width = text_surface.get_width()
        text_height = text_surface.get_height()
        text_x = sprite_rect.centerx - text_width // 2
        # Fica acima da barra de HP
        text_y = sprite_rect.top - self.hp_bar_height - 25

        for dx, dy in [(-1, -1), (-1, 1), (1, -1), (1, 1)]:
            screen.blit(text_outline, (text_x + dx, text_y + dy))
        screen.blit(text_surface, (text_x, text_y))

    def _render_debug(self, screen, screen_x, screen_y, zoom_scale, sprite_rect):
        """Renderiza informações de debug"""
        # Centro do sprite (ponto de ancoragem)
        pygame.draw.circle(screen, (255, 0, 0), (sprite_rect.centerx, sprite_rect.centery), 6, 2)

        # Retângulo do sprite
        pygame.draw.rect(screen, (255, 0, 255), sprite_rect, 1)

        # Mostra animação atual e frame
        font = self._get_font(10)
        debug_text = f"{self.current_animation} f{self.current_frame} dir:{self.current_direction}"
        text_surf = font.render(debug_text, True, (255, 255, 255))
        screen.blit(text_surf, (sprite_rect.left, sprite_rect.top - 25))

        # Mostra coordenadas
        coord_text = f"({self.x:.0f}, {self.y:.0f})"
        coord_surf = font.render(coord_text, True, (200, 200, 200))
        screen.blit(coord_surf, (sprite_rect.left, sprite_rect.bottom + 5))

    def _render_placeholder(self, screen, screen_x, screen_y, zoom_scale):
        """Renderiza placeholder para quando sprite não existe"""
        size = int((64 if self.is_boss else self.map_sprite_size) * zoom_scale)

        rect = pygame.Rect(0, 0, size, size)
        rect.center = (int(screen_x), int(screen_y))

        pygame.draw.rect(screen, (255, 0, 255), rect)
        pygame.draw.rect(screen, (255, 255, 255), rect, 2)
        return rect

    def get_info_string(self):
        return (f"{self.name} Lv.{self.level}\n"
                f"HP: {self.current_hp}/{self.max_hp}\n"
                f"Tipos: {'/'.join(self.types)}\n"
                f"Natureza: {self.nature}")

    #================MOVES============================

    def restore_pp(self, percentage: float = 1.0) -> int:
        """
        Restaura PP de TODOS os moves do Pokémon.

        Args:
            percentage: Porcentagem a restaurar (0.2 = 20%, 1.0 = 100%)

        Returns:
            int: Número total de PP restaurados
        """
        restored_count = 0

        for move in self.moves:
            pp_to_restore = int(move.max_pp * percentage)
            old_pp = move.current_pp
            move.current_pp = min(move.max_pp, move.current_pp + pp_to_restore)
            restored_count += move.current_pp - old_pp

        if restored_count > 0:
            print(f"[PP_RESTORE] {self.name}: {restored_count} PP restaurados "
                  f"({int(percentage * 100)}% de cada move)")

        return restored_count

    def reset_pp(self) -> int:
        """Reseta os PP de todos os moves para o máximo (100%)"""
        return self.restore_pp(percentage=1.0)

    def _initialize_moves(self):
        """Inicializa os moves do Pokémon baseado no nível atual"""
        # Obtém moves iniciais (todos os moves até o nível atual)
        all_moves_learned = self.move_data.get_moves_at_level(self.id, self.level)

        # Pega apenas os 4 primeiros (ou menos se não tiver 4)
        initial_moves = all_moves_learned[:4]

        for move_name in initial_moves:
            move_info = self.move_data.get_move_info(move_name)
            if move_info:
                self.moves.append(Move(move_name, move_info))

        # Se não aprendeu nenhum move (fallback), adiciona um move padrão
        if not self.moves:
            fallback_move = {
                "name": "tackle",
                "type": "normal",
                "power": 40,
                "accuracy": 100,
                "pp": 35,
                "category": "physical",
                "description": "Um ataque físico com o corpo."
            }
            self.moves.append(Move("tackle", fallback_move))

        print(f"[INIT] {self.name} Lv.{self.level} aprendeu: {[m.name for m in self.moves]}")

    def learn_move(self, move_name: str) -> bool:
        """
        Tenta aprender um novo move
        Se já tem 4 moves, abre overlay para escolher
        """
        move_info = self.move_data.get_move_info(move_name)
        if not move_info:
            return False

        new_move = Move(move_name, move_info)

        # Se tem menos de 4 moves, adiciona diretamente
        if len(self.moves) < 4:
            self.moves.append(new_move)
            print(f"[MOVES] {self.name} aprendeu {move_name}!")
            return True

        # Se já tem 4 moves, abre overlay
        if self.game_scene:
            self.game_scene.open_move_learn_overlay(self, move_name)
            return True

        return False

    def forget_move(self, index: int) -> bool:
        """
        Esquece um move pelo índice (0-3)
        Retorna True se esqueceu
        """
        if 0 <= index < len(self.moves):
            forgotten = self.moves.pop(index)
            print(f"[MOVES] {self.name} esqueceu {forgotten.name}!")
            return True
        return False

    def replace_move(self, index: int, new_move_name: str) -> bool:
        """
        Substitui um move existente por um novo
        """
        if not 0 <= index < len(self.moves):
            return False

        move_info = self.move_data.get_move_info(new_move_name)
        if not move_info:
            return False

        old_name = self.moves[index].name
        self.moves[index] = Move(new_move_name, move_info)
        print(f"[MOVES] {self.name} esqueceu {old_name} e aprendeu {new_move_name}!")
        return True

    def get_available_moves(self) -> List[str]:
        """Retorna todos os moves que o Pokémon pode aprender (até o nível atual)"""
        return self.move_data.get_moves_at_level(self.id, self.level)

    def get_new_moves_at_level(self, level: int) -> List[str]:
        """
        Retorna moves que o Pokémon aprende EXATAMENTE neste nível
        e que ainda não estão na lista de moves atuais
        """
        # Obtém todos os moves do learnset do Pokémon
        learnset = self.move_data.get_pokemon_learnset(self.id)

        # Moves que o Pokémon já conhece
        known_moves = set(move.name for move in self.moves)

        # Filtra moves aprendidos exatamente neste nível
        new_moves = []
        for move_info in learnset:
            if move_info.get("level", 0) == level:
                move_name = move_info.get("move", "")
                if move_name and move_name not in known_moves:
                    new_moves.append(move_name)

        return new_moves

    def check_new_moves_on_level_up(self, old_level: int):
        """
        Verifica se o Pokémon aprende novos moves ao subir de nível
        Retorna (learned_moves, pending_moves)
        """
        # Obtém todos os moves que o Pokémon aprende
        learnset = self.move_data.get_pokemon_learnset(self.id)

        # Moves que o Pokémon já sabe
        current_moves = set(move.name for move in self.moves)

        # Filtra apenas moves que são aprendidos EXATAMENTE no nível atual
        new_moves = []
        for move_info in learnset:
            level = move_info.get("level", 0)
            move_name = move_info.get("move", "")

            # SÓ adiciona se for aprendido no nível ATUAL E o Pokémon ainda não sabe
            if level == self.level and move_name not in current_moves:
                new_moves.append(move_name)

        learned_moves = []
        pending_moves = []

        for move_name in new_moves:
            learned = self.learn_move(move_name)
            if learned:
                learned_moves.append(move_name)
            else:
                pending_moves.append(move_name)

        return learned_moves, pending_moves

    def restore_moves(self, moves_data: list):
        """
        Restaura moves a partir de dados serializados
        moves_data: lista de dicts com "name", "current_pp", "max_pp"
        """
        from src.data.move_data import MoveData
        from src.entities.move import Move

        move_data = MoveData()
        self.moves = []

        for move_dict in moves_data:
            move_info = move_data.get_move_info(move_dict["name"])
            # Se o move_info for None (move não encontrado), usa dados padrão
            if move_info is None:
                move_info = {
                    "type": "normal",
                    "power": 40,
                    "accuracy": 100,
                    "pp": move_dict.get("max_pp", 35),
                    "category": "physical",
                    "description": f"Usa {move_dict['name']}."
                }

            move = Move(move_dict["name"], move_info)
            move.current_pp = move_dict.get("current_pp", move.max_pp)
            move.max_pp = move_dict.get("max_pp", move.max_pp)
            self.moves.append(move)

        print(f"[LOAD] {self.name} restaurado com {len(self.moves)} moves")

    def _learn_move_without_replacement(self, move_name: str) -> bool:
        """
        Aprende um novo move mantendo os existentes
        Retorna:
            True: move aprendido com sucesso (ainda tem espaço)
            False: precisa de decisão do jogador (já tem 4 moves)
        """
        move_info = self.move_data.get_move_info(move_name)
        if not move_info:
            return False

        new_move = Move(move_name, move_info)

        # Se tem menos de 4 moves, adiciona diretamente
        if len(self.moves) < 4:
            self.moves.append(new_move)
            print(f"[MOVES] {self.name} aprendeu {move_name}!")
            return True

        # Se já tem 4 moves, retorna False indicando que precisa de decisão
        print(f"[MOVES] {self.name} quer aprender {move_name}, mas já tem 4 moves!")
        return False  # False = precisa de overlay para decidir

    def learn_move_with_selection(self, move_name: str, slot_index: int) -> bool:
        """
        Aprende um novo move substituindo o move no slot_index
        """
        move_info = self.move_data.get_move_info(move_name)
        if not move_info:
            return False

        if 0 <= slot_index < len(self.moves):
            old_name = self.moves[slot_index].name
            self.moves[slot_index] = Move(move_name, move_info)
            print(f"[MOVES] {self.name} esqueceu {old_name} e aprendeu {move_name}!")
            return True

        return False