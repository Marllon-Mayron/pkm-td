# src/scenes/minigames/survival/components/wave_manager.py

"""
Wave Manager para minigame Survival - Waves finitas configuradas via JSON
"""
import math
import random
from typing import List, Optional, Tuple, Dict, Any
from dataclasses import dataclass

from src.entities.pokemon import Pokemon
from src.data.pokedex import Pokedex
from src.battle.attack_pattern import AttackPattern
from src.ui.toast_renderer import toast_battle, toast_success, toast_warning


class SurvivalWaveManager:
    """Gerencia waves finitas do minigame Survival"""

    def __init__(self, game_scene, chapter_id: int = 1, phase_number: int = 1, survival_data: dict = None):
        self.game_scene = game_scene
        self.chapter_id = chapter_id
        self.phase_number = phase_number
        self.survival_data = survival_data

        self.paths = None
        self.pokedex = Pokedex()

        # Estado
        self.active_enemies: List[Pokemon] = []
        self.paused = False

        # Configuração das waves
        self.current_wave = 1
        self.total_waves = 0
        self.waves_config = []
        self.enemies_spawned_in_wave = 0
        self.enemies_to_spawn = 0
        self.wave_active = False
        self.wave_timer = 0.0
        self.spawn_timer = 0.0
        self.between_waves_timer = 0.0
        self.between_waves_duration = 3.0

        self.current_wave_config = None
        self.current_wave_enemies = []
        self.current_wave_is_boss = False

        self.enemies_killed = 0
        self.enemies_escaped = 0

        self.available_paths: List[int] = []
        self._wave_completed_announced = False

        self._load_waves_from_data()
        self._load_minigame_config()

    def _load_waves_from_data(self):
        """Carrega as waves do survival_data"""
        if self.survival_data and "waves" in self.survival_data:
            self.waves_config = self.survival_data["waves"]
            self.total_waves = len(self.waves_config)
            print(f"[SurvivalWave] Carregadas {self.total_waves} waves")
        else:
            self.waves_config = [
                {"wave": 1, "enemies": [10, 13], "count": 3, "min_level": 3, "max_level": 5, "spawn_interval": 3.0}]
            self.total_waves = 1
            print(f"[SurvivalWave] Usando wave fallback")

    def _load_minigame_config(self):
        """Carrega configurações adicionais"""
        import json
        import os
        from src.config.paths import PROJECT_ROOT

        minigame_path = os.path.join(PROJECT_ROOT, "src", "data", "minigames", "survival")
        level_file = os.path.join(minigame_path, f"level_{self.chapter_id:02d}_{self.phase_number:02d}.json")

        if os.path.exists(level_file):
            try:
                with open(level_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)

                waves_data = data.get("waves", {})
                if isinstance(waves_data, dict):
                    waves_list = waves_data.get("waves", [])
                    if waves_list and self.waves_config:
                        wave_config = waves_list[0]
                        self.between_waves_duration = wave_config.get("initial_delay", 3.0)

            except Exception as e:
                print(f"[SurvivalWave] Erro ao carregar config: {e}")

    def set_paths(self, paths):
        self.paths = paths
        if paths:
            self.available_paths = list(range(len(paths)))
            print(f"[SurvivalWave] Paths disponíveis: {self.available_paths}")

    def start_waves(self):
        self.current_wave = 1
        self.enemies_killed = 0
        self.enemies_escaped = 0
        self.wave_active = False
        self.between_waves_timer = 0
        self._wave_completed_announced = False
        self._prepare_next_wave()
        self.wave_active = True
        print(f"[SurvivalWave] Iniciando waves... Total: {self.total_waves}")

    def register_attacker_for_enemy(self, attacker: Pokemon, enemy: Pokemon):
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

    def _prepare_next_wave(self):
        """Prepara a próxima wave baseada na configuração"""
        if self.current_wave > self.total_waves:
            print(f"[SurvivalWave] Todas as waves completas! Fim do jogo.")
            self.wave_active = False
            if hasattr(self.game_scene, 'complete_game'):
                self.game_scene.complete_game()
            return

        wave_config = self.waves_config[self.current_wave - 1]

        self.current_wave_is_boss = wave_config.get("is_boss", False)
        self.current_wave_enemies = wave_config.get("enemies", [10, 13])
        enemies_count = wave_config.get("count", 5)
        spawn_interval = wave_config.get("spawn_interval", 3.0)
        initial_delay = wave_config.get("initial_delay", 2.0)
        min_level = wave_config.get("min_level", 3)
        max_level = wave_config.get("max_level", 5)

        self.enemies_to_spawn = enemies_count
        self.enemies_spawned_in_wave = 0
        self.wave_timer = initial_delay
        self.spawn_timer = 0.0
        self._wave_completed_announced = False

        paths_available = self.available_paths.copy()
        random.shuffle(paths_available)

        self.current_wave_config = {
            "wave_number": self.current_wave,
            "total_enemies": enemies_count,
            "spawn_interval": spawn_interval,
            "initial_delay": initial_delay,
            "enemy_level_min": min_level,
            "enemy_level_max": max_level,
            "has_boss": self.current_wave_is_boss,
            "paths_available": paths_available,
            "enemy_ids": self.current_wave_enemies
        }

        self._announce_wave()

        print(
            f"[SurvivalWave] WAVE {self.current_wave}/{self.total_waves}: {enemies_count} inimigos, boss={self.current_wave_is_boss}")

    def _announce_wave(self):
        wave_text = f"ONDA {self.current_wave}"
        if self.current_wave_is_boss:
            wave_text = f"ONDA {self.current_wave} - CHEFE"

        toast_battle(wave_text, duration=2.0)

        if hasattr(self.game_scene, 'survival_ui'):
            self.game_scene.survival_ui.show_message(wave_text, (255, 215, 0), duration=2.0)

    def _get_random_path(self) -> Optional[int]:
        """Retorna um índice de path aleatório dos disponíveis na wave atual"""
        if not self.current_wave_config or not self.current_wave_config["paths_available"]:
            if self.available_paths:
                return random.choice(self.available_paths)
            return 0
        return random.choice(self.current_wave_config["paths_available"])

    def _get_path_start_point(self, path_idx: int) -> Optional[Tuple[float, float]]:
        if not self.paths or path_idx >= len(self.paths):
            return None

        path = self.paths[path_idx]

        if hasattr(path, 'start_point') and path.start_point:
            return path.start_point
        elif hasattr(path, 'nodes') and path.nodes:
            return path.nodes[0]
        elif hasattr(path, 'points') and path.points:
            return path.points[0]
        elif isinstance(path, list) and len(path) > 0:
            return path[0]

        return None

    def _get_path_points(self, path_idx: int) -> Optional[List[Tuple[float, float]]]:
        if not self.paths or path_idx >= len(self.paths):
            return None

        path = self.paths[path_idx]

        if hasattr(path, 'points'):
            return path.points
        elif hasattr(path, 'nodes'):
            return path.nodes
        elif isinstance(path, list):
            return path

        return None

    def _create_enemy(self) -> Optional[Pokemon]:
        """Cria um inimigo baseado na configuração da wave"""
        if not self.current_wave_config:
            return None

        path_idx = self._get_random_path()
        if path_idx is None:
            return None

        if hasattr(self.game_scene, 'path_assignment'):
            path_y = self.game_scene.path_assignment.path_y_coords[path_idx] if path_idx < len(
                self.game_scene.path_assignment.path_y_coords) else None
            print(f"[SurvivalWave] Criando inimigo para path {path_idx} (Y={path_y})")

        start_point = self._get_path_start_point(path_idx)
        if not start_point:
            return None

        start_x, start_y = start_point

        is_last = (self.enemies_spawned_in_wave + 1) >= self.current_wave_config["total_enemies"]

        enemies_list = self.current_wave_config["enemy_ids"]
        pokemon_id = random.choice(enemies_list) if len(enemies_list) > 1 else enemies_list[0]

        if is_last and self.current_wave_config["has_boss"]:
            level = self.current_wave_config["enemy_level_max"] + 2
            is_boss = True
        else:
            level = random.randint(
                self.current_wave_config["enemy_level_min"],
                self.current_wave_config["enemy_level_max"]
            )
            is_boss = False

        try:
            pokemon = Pokemon(
                start_x, start_y,
                pokemon_id,
                level=level,
                is_wild=True,
                shiny=random.random() < 0.001,
                is_boss=is_boss
            )
        except Exception as e:
            print(f"[SurvivalWave] Erro ao criar Pokemon {pokemon_id}: {e}")
            return None

        pokemon.attack_pattern = AttackPattern.AGGRESSIVE
        pokemon.combat_state = "attacking"

        pokemon._assigned_path_index = path_idx
        print(f"[SurvivalWave] {pokemon.name} associado ao path {path_idx}")

        if self.game_scene and hasattr(self.game_scene, 'screen_manager'):
            pokemon.screen_manager = self.game_scene.screen_manager
            pokemon.camera = self.game_scene.camera

        path_points = self._get_path_points(path_idx)
        if path_points:
            pokemon.path = path_points.copy()
            pokemon.path_index = 0
            pokemon.original_path = path_points.copy()
        else:
            return None

        pokemon._just_spawned = True
        pokemon._spawn_timer = 0.5
        pokemon._escaped_counted = False

        if len(path_points) >= 2:
            dx = path_points[1][0] - path_points[0][0]
            dy = path_points[1][1] - path_points[0][1]
            self._update_direction_from_movement(pokemon, dx, dy)

        print(f"[SurvivalWave] {pokemon.name} criado - Level {pokemon.level}, Path {path_idx}")
        return pokemon

    def _update_direction_from_movement(self, enemy: Pokemon, dx: float, dy: float):
        """Atualiza a direção baseada no movimento (8 direções)"""
        if dx == 0 and dy == 0:
            return

        abs_dx = abs(dx)
        abs_dy = abs(dy)
        THRESHOLD = 0.41421356

        if abs_dx >= abs_dy:
            if dx > 0:
                if dy > 0 and abs_dy > abs_dx * THRESHOLD:
                    enemy.current_direction = "down-right"
                elif dy < 0 and abs_dy > abs_dx * THRESHOLD:
                    enemy.current_direction = "up-right"
                else:
                    enemy.current_direction = "right"
            else:
                if dy > 0 and abs_dy > abs_dx * THRESHOLD:
                    enemy.current_direction = "down-left"
                elif dy < 0 and abs_dy > abs_dx * THRESHOLD:
                    enemy.current_direction = "up-left"
                else:
                    enemy.current_direction = "left"
        else:
            if dy > 0:
                if dx > 0 and abs_dx > abs_dy * THRESHOLD:
                    enemy.current_direction = "down-right"
                elif dx < 0 and abs_dx > abs_dy * THRESHOLD:
                    enemy.current_direction = "down-left"
                else:
                    enemy.current_direction = "down"
            else:
                if dx > 0 and abs_dx > abs_dy * THRESHOLD:
                    enemy.current_direction = "up-right"
                elif dx < 0 and abs_dx > abs_dy * THRESHOLD:
                    enemy.current_direction = "up-left"
                else:
                    enemy.current_direction = "up"

    def update(self, dt: float) -> List[Pokemon]:
        """Atualiza waves - APENAS MOVIMENTO"""
        if self.paused:
            return []

        enemies_at_end = []

        if not self.wave_active:
            if self.between_waves_timer > 0:
                self.between_waves_timer -= dt
                return []

            if self.current_wave <= self.total_waves:
                self._prepare_next_wave()
                self.wave_active = True
                return []
            else:
                return []

        if self.wave_timer > 0:
            self.wave_timer -= dt
            if self.wave_timer > 0:
                return []
            self.spawn_timer = 0

        if self.enemies_spawned_in_wave < self.enemies_to_spawn:
            self.spawn_timer -= dt

            if self.spawn_timer <= 0:
                enemy = self._create_enemy()
                if enemy:
                    if hasattr(self.game_scene, 'battle_system'):
                        enemy.set_battle_system(self.game_scene.battle_system)
                        # Conecta o wave_manager ao battle_system para registro de ataques
                        if hasattr(self.game_scene.battle_system, 'set_wave_manager'):
                            self.game_scene.battle_system.set_wave_manager(self)

                    self.active_enemies.append(enemy)
                    self.enemies_spawned_in_wave += 1
                    print(
                        f"[SurvivalWave] Spawn #{self.enemies_spawned_in_wave}/{self.enemies_to_spawn}: {enemy.name} Lv.{enemy.level}")

                    self.spawn_timer = self.current_wave_config["spawn_interval"]

        enemies_to_remove = []

        for enemy in self.active_enemies[:]:
            try:
                if not enemy.is_alive() or enemy.is_defeated:
                    if not getattr(enemy, '_marked_for_removal', False):
                        print(f"[SurvivalWave] {enemy.name} está morto, removendo...")
                        self._handle_enemy_death(enemy)
                        enemies_to_remove.append(enemy)
                    continue

                if not hasattr(enemy, 'path') or not enemy.path:
                    continue

                should_stop = False
                if hasattr(self.game_scene, 'player_pokemon') and hasattr(self.game_scene, 'path_assignment'):
                    enemy_path = self.game_scene.path_assignment.get_path_for_enemy(enemy)

                    for ally in self.game_scene.player_pokemon:
                        if not ally.is_alive() or ally.is_defeated:
                            continue

                        ally_path = self.game_scene.path_assignment.get_path_for_pokemon(ally)
                        if ally_path != enemy_path:
                            continue

                        dx = ally.x - enemy.x
                        dy = ally.y - enemy.y
                        distance = math.hypot(dx, dy)
                        if distance < enemy.attack_range:
                            should_stop = True
                            break

                if should_stop:
                    closest_ally = None
                    min_dist = float('inf')
                    enemy_path = self.game_scene.path_assignment.get_path_for_enemy(enemy)

                    for ally in self.game_scene.player_pokemon:
                        if not ally.is_alive() or ally.is_defeated:
                            continue
                        ally_path = self.game_scene.path_assignment.get_path_for_pokemon(ally)
                        if ally_path != enemy_path:
                            continue
                        dx = ally.x - enemy.x
                        dy = ally.y - enemy.y
                        dist = math.hypot(dx, dy)
                        if dist < min_dist:
                            min_dist = dist
                            closest_ally = ally

                    if closest_ally:
                        dx = closest_ally.x - enemy.x
                        dy = closest_ally.y - enemy.y
                        self._update_direction_from_movement(enemy, dx, dy)

                    continue

                if enemy.path_index >= len(enemy.path):
                    enemies_at_end.append(enemy)
                    continue

                target_x, target_y = enemy.path[enemy.path_index]
                dx = target_x - enemy.x
                dy = target_y - enemy.y
                distance = math.hypot(dx, dy)
                move_distance = enemy.move_speed * dt * 60

                if distance > 0:
                    self._update_direction_from_movement(enemy, dx, dy)

                if distance <= move_distance:
                    enemy.x, enemy.y = target_x, target_y
                    enemy.path_index += 1

                    if enemy.path_index >= len(enemy.path):
                        enemies_at_end.append(enemy)
                        continue
                else:
                    move_x = (dx / distance) * move_distance
                    move_y = (dy / distance) * move_distance
                    enemy.x += move_x
                    enemy.y += move_y

                if hasattr(enemy, 'rect'):
                    enemy.rect.x, enemy.rect.y = enemy.x, enemy.y

            except Exception as e:
                print(f"[SurvivalWave] Erro ao processar inimigo: {e}")
                continue

        for enemy in enemies_to_remove:
            if enemy in self.active_enemies:
                self.active_enemies.remove(enemy)

        for enemy in enemies_at_end:
            if enemy in self.active_enemies:
                self.active_enemies.remove(enemy)

        wave_finished = (self.enemies_spawned_in_wave >= self.enemies_to_spawn and
                         len(self.active_enemies) == 0)

        if wave_finished and not self._wave_completed_announced:
            self._wave_completed_announced = True
            self._complete_wave()

        return enemies_at_end

    def _handle_enemy_death(self, enemy: Pokemon):
        """Processa morte de um inimigo"""
        self.enemies_killed += 1

        # ===== DISTRIBUI XP APENAS PARA QUEM ATACOU ESTE INIMIGO =====
        self._distribute_xp_to_attackers(enemy)

        if hasattr(self.game_scene, 'add_energy'):
            energy_gain = 15
            if enemy.is_boss:
                energy_gain = 60
            elif enemy.is_shiny:
                energy_gain = 30
            self.game_scene.add_energy(energy_gain)

        if hasattr(self.game_scene, 'add_score'):
            score_gain = 10
            if enemy.is_boss:
                score_gain = 150
            elif enemy.is_shiny:
                score_gain = 50
            self.game_scene.add_score(score_gain)

        enemy._marked_for_removal = True
        enemy.is_defeated = True
        enemy.current_hp = 0

        if hasattr(self.game_scene, 'player_pokemon'):
            for ally in self.game_scene.player_pokemon:
                if hasattr(ally, 'target') and ally.target == enemy:
                    ally.target = None
                    ally.combat_state = "idle"

        if hasattr(enemy, 'effect_manager') and enemy.effect_manager:
            try:
                enemy.effect_manager.unregister_pokemon(enemy)
            except:
                pass

        self._cleanup_enemy_attackers(enemy)

    def _distribute_xp_to_attackers(self, defeated_enemy: Pokemon):
        """Distribui XP APENAS para os Pokémon que atacaram este inimigo específico"""

        if not hasattr(defeated_enemy, '_attackers'):
            print(f"[XP] Nenhum atacante registrado para {defeated_enemy.name}")
            return

        attackers = []
        for attacker_id in defeated_enemy._attackers:
            for ally in self.game_scene.player_pokemon:
                if id(ally) == attacker_id and ally.is_alive() and not ally.is_defeated:
                    attackers.append(ally)
                    break

        if not attackers:
            print(f"[XP] Nenhum atacante encontrado vivo para {defeated_enemy.name}")
            return

        # ===== CALCULA XP BASE (exponencial pelo nível do inimigo) =====
        level = defeated_enemy.level
        base_xp = 20 + int((level ** 1.5) * 2)

        if defeated_enemy.is_boss:
            base_xp = int(base_xp * 3)
            print(f"[XP] BOSS derrotado! XP base: {base_xp}")

        if defeated_enemy.is_shiny:
            base_xp = int(base_xp * 1.5)

        xp_per_attacker = max(1, base_xp // len(attackers))

        print(f"[XP] {defeated_enemy.name} (nível {level}) foi atacado por {len(attackers)} Pokémon")
        print(f"[XP] Distribuindo {xp_per_attacker} XP para cada atacante")

        pokedex = self.game_scene.game.player.pokedex if self.game_scene.game.player else None
        ev_yield = {}
        if pokedex:
            ev_yield = pokedex.get_ev_yield(defeated_enemy.id)

        ev_multiplier = 1.0
        if defeated_enemy.is_boss:
            ev_multiplier *= 3
        if defeated_enemy.is_shiny:
            ev_multiplier *= 2

        for ally in attackers:
            ally.gain_xp(xp_per_attacker)

            if any(ev_yield.values()):
                evs_gained = {}
                for stat, value in ev_yield.items():
                    if value > 0:
                        ev_value = max(1, int(value * ev_multiplier))
                        evs_gained[stat] = ev_value

                if ally.stats.can_gain_evs(evs_gained):
                    ally.stats.gain_evs(evs_gained)
                    print(f"[XP] {ally.name} ganhou {xp_per_attacker} XP e EVs: {evs_gained}")
                else:
                    print(f"[XP] {ally.name} ganhou {xp_per_attacker} XP (EVs bloqueados)")
            else:
                print(f"[XP] {ally.name} ganhou {xp_per_attacker} XP")

    def _cleanup_enemy_attackers(self, enemy: Pokemon):
        """Limpa a lista de atacantes do inimigo"""
        if hasattr(enemy, '_attackers'):
            enemy._attackers.clear()

    def _complete_wave(self):
        """Completa a wave atual e prepara a próxima"""
        print(f"[SurvivalWave] WAVE {self.current_wave} COMPLETA!")

        wave_complete_text = f"ONDA {self.current_wave} COMPLETA!"
        toast_success(wave_complete_text, duration=2.0)

        if hasattr(self.game_scene, 'survival_ui'):
            self.game_scene.survival_ui.show_message(
                f"ONDA {self.current_wave} COMPLETA",
                (100, 255, 100),
                duration=2.0
            )

        if hasattr(self.game_scene, 'force_allies_return_to_spots'):
            self.game_scene.force_allies_return_to_spots()

        if hasattr(self.game_scene, 'add_energy'):
            bonus = 30
            self.game_scene.add_energy(bonus)

        self.current_wave += 1
        self.wave_active = False
        self.between_waves_timer = self.between_waves_duration

        self.current_wave_config = None
        self.enemies_to_spawn = 0
        self.enemies_spawned_in_wave = 0

        print(f"[SurvivalWave] Próxima wave: {self.current_wave}/{self.total_waves}")

    def remove_enemy(self, enemy: Pokemon):
        self._handle_enemy_death(enemy)

    def get_current_wave_info(self, active_enemies_count: int = None) -> dict:
        if active_enemies_count is None:
            active_enemies_count = len(self.active_enemies)

        progress = 0
        if self.enemies_to_spawn > 0:
            progress = self.enemies_spawned_in_wave / self.enemies_to_spawn

        name = f"Onda {self.current_wave}"
        if self.current_wave_is_boss:
            name += " (Chefe)"

        return {
            "name": name,
            "index": self.current_wave,
            "total": self.total_waves if self.total_waves > 0 else "infinito",
            "enemies_remaining": active_enemies_count,
            "enemies_spawned": self.enemies_spawned_in_wave,
            "enemies_total": self.enemies_to_spawn,
            "progress": min(1.0, progress),
            "active_paths": len(self.available_paths)
        }

    def has_more_waves(self) -> bool:
        return self.current_wave <= self.total_waves

    def has_active_waves(self) -> bool:
        return self.wave_active or self.enemies_spawned_in_wave > 0