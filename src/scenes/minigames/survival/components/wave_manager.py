# src/scenes/minigames/survival/components/wave_manager.py
"""
Wave Manager para minigame Survival - Inimigos param para atacar
"""
import math
import random
from typing import List, Optional, Dict, Any, Tuple
from dataclasses import dataclass, field

from src.entities.pokemon import Pokemon
from src.data.pokedex import Pokedex
from src.battle.attack_pattern import AttackPattern


@dataclass
class WaveConfig:
    wave_number: int
    total_enemies: int
    spawn_interval: float
    initial_delay: float
    enemy_level_min: int
    enemy_level_max: int
    has_boss: bool
    boss_at_end: bool = True
    paths_available: List[int] = field(default_factory=list)
    pokemon_pool: List[int] = field(default_factory=list)


class SurvivalWaveManager:
    """
    Wave Manager para minigame Survival.
    Inimigos param para atacar (como Plants vs Zombies).
    """

    # LISTA DE POKEMON QUE PODEM APARECER COMO INIMIGOS
    ENEMY_POKEMON_POOL = [
        16, 19, 21, 23, 25, 29, 32, 39, 41, 43, 46, 48, 50, 52, 54, 56, 58, 60, 63, 66, 69, 72,
        74, 77, 79, 81, 84, 86, 88, 90, 92, 95, 96, 98, 100, 102, 104, 108, 109, 111, 114, 116,
        118, 120, 123, 129, 133
    ]

    # BOSSES (pokemon mais fortes)
    BOSS_POKEMON_POOL = [3, 6, 9, 18, 31, 34, 45, 59, 62, 65, 68, 76, 94, 106, 107, 108, 112, 130, 131, 149]

    BASE_ENEMIES_PER_WAVE = 6
    ENEMIES_INCREMENT_PER_WAVE = 1
    MAX_ENEMIES_PER_WAVE = 20

    BASE_SPAWN_INTERVAL = 3.0
    MIN_SPAWN_INTERVAL = 1.0

    BASE_LEVEL = 3
    LEVEL_INCREMENT_PER_WAVE = 1
    MAX_LEVEL = 50

    def __init__(self, game_scene, chapter_id: int = 1, phase_number: int = 1):
        self.game_scene = game_scene
        self.chapter_id = chapter_id
        self.phase_number = phase_number

        self.paths = None
        self.pokedex = Pokedex()

        # Estado
        self.active_enemies: List[Pokemon] = []
        self.paused = False

        # Configuracao das waves
        self.current_wave = 1
        self.total_waves = 0
        self.enemies_spawned_in_wave = 0
        self.enemies_to_spawn = 0
        self.wave_active = False
        self.wave_timer = 0.0
        self.spawn_timer = 0.0
        self.between_waves_timer = 0.0
        self.between_waves_duration = 3.0

        self.current_wave_config: Optional[WaveConfig] = None

        self.enemies_killed = 0
        self.enemies_escaped = 0

        self.available_paths: List[int] = []
        self.pokemon_pool = self.ENEMY_POKEMON_POOL.copy()

        self._load_minigame_config()

    def _load_minigame_config(self):
        """Carrega configuracoes especificas do minigame survival"""
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
                    if waves_list:
                        wave_config = waves_list[0]
                        self.BASE_ENEMIES_PER_WAVE = wave_config.get("wave_size", self.BASE_ENEMIES_PER_WAVE)
                        self.BASE_SPAWN_INTERVAL = wave_config.get("spawn_interval", self.BASE_SPAWN_INTERVAL)
                        self.BASE_LEVEL = wave_config.get("min_level", self.BASE_LEVEL)

                custom_pool = data.get("pokemon_pool", [])
                if custom_pool:
                    self.pokemon_pool = custom_pool
                    print(f"[SurvivalWave] Pokemon pool carregado: {len(self.pokemon_pool)} Pokemon")

            except Exception as e:
                print(f"[SurvivalWave] Erro ao carregar config: {e}")

    def set_paths(self, paths):
        self.paths = paths
        if paths:
            self.available_paths = list(range(len(paths)))
            print(f"[SurvivalWave] Paths disponiveis: {self.available_paths}")

    def set_target_items(self, items):
        pass

    def start_waves(self):
        self.current_wave = 1
        self.enemies_killed = 0
        self.enemies_escaped = 0
        self.wave_active = False
        self.between_waves_timer = 0
        self._prepare_next_wave()
        self.wave_active = True
        print(f"[SurvivalWave] Waves iniciadas! Wave 1 comecando...")

    def _prepare_next_wave(self):
        wave_number = self.current_wave

        enemies_count = min(
            self.MAX_ENEMIES_PER_WAVE,
            self.BASE_ENEMIES_PER_WAVE + (wave_number - 1) * self.ENEMIES_INCREMENT_PER_WAVE
        )

        spawn_interval = max(
            self.MIN_SPAWN_INTERVAL,
            self.BASE_SPAWN_INTERVAL - (wave_number - 1) * 0.1
        )

        initial_delay = max(0.5, 2.0 - (wave_number - 1) * 0.1)

        level_min = self.BASE_LEVEL + (wave_number - 1) * self.LEVEL_INCREMENT_PER_WAVE
        level_max = min(self.MAX_LEVEL, level_min + 2)

        # Boss a cada 5 waves
        has_boss = (wave_number % 5 == 0)

        paths_available = self.available_paths.copy()
        random.shuffle(paths_available)

        self.current_wave_config = WaveConfig(
            wave_number=wave_number,
            total_enemies=enemies_count,
            spawn_interval=spawn_interval,
            initial_delay=initial_delay,
            enemy_level_min=level_min,
            enemy_level_max=level_max,
            has_boss=has_boss,
            paths_available=paths_available,
            pokemon_pool=self.pokemon_pool.copy()
        )

        self.enemies_to_spawn = enemies_count
        self.enemies_spawned_in_wave = 0
        self.wave_timer = initial_delay
        self.spawn_timer = 0.0

        self._announce_wave()

        print(f"[SurvivalWave] WAVE {wave_number}: {enemies_count} inimigos, nivel {level_min}-{level_max}, boss={has_boss}")

    def _announce_wave(self):
        if hasattr(self.game_scene, 'survival_ui'):
            wave_text = f"ONDA {self.current_wave}"
            if self.current_wave_config and self.current_wave_config.has_boss:
                wave_text = f"ONDA {self.current_wave} - CHEFE INIMIGO"
            self.game_scene.survival_ui.show_message(wave_text, (255, 215, 0), duration=2.0)

    def _get_random_path(self) -> Optional[int]:
        if not self.current_wave_config or not self.current_wave_config.paths_available:
            return 0 if self.available_paths else None
        return random.choice(self.current_wave_config.paths_available)

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
        """Cria um inimigo - RESPEITANDO STATS E COOLDOWN DO MODO CAMPANHA"""
        if not self.current_wave_config:
            return None

        path_idx = self._get_random_path()
        if path_idx is None:
            return None

        start_point = self._get_path_start_point(path_idx)
        if not start_point:
            return None

        start_x, start_y = start_point

        is_last = (self.enemies_spawned_in_wave + 1) >= self.current_wave_config.total_enemies
        is_boss = is_last and self.current_wave_config.has_boss

        if is_boss:
            pokemon_pool = self.BOSS_POKEMON_POOL
            level = self.current_wave_config.enemy_level_max + 2
        else:
            pokemon_pool = self.current_wave_config.pokemon_pool
            level = random.randint(
                self.current_wave_config.enemy_level_min,
                self.current_wave_config.enemy_level_max
            )

        pokemon_id = random.choice(pokemon_pool)

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

        # ===== CONFIGURA O INIMIGO COMO AGRESSIVO =====
        pokemon.attack_pattern = AttackPattern.AGGRESSIVE
        pokemon.combat_state = "attacking"

        # Configura screen e camera
        if self.game_scene and hasattr(self.game_scene, 'screen_manager'):
            pokemon.screen_manager = self.game_scene.screen_manager
            pokemon.camera = self.game_scene.camera

        # Atribui o path
        path_points = self._get_path_points(path_idx)
        if path_points:
            pokemon.path = path_points.copy()
            pokemon.path_index = 0
            pokemon.original_path = path_points.copy()
        else:
            return None

        # ===== CRUCIAL: NÃO MODIFICA A VELOCIDADE MANUALMENTE! =====
        # A velocidade JÁ É CALCULADA pelo stats do Pokémon baseada em:
        # - Base speed do Pokémon
        # - Level
        # - IVs/EVs
        # - Natureza
        # - Status effects (paralisia, etc)
        # - Shiny/Boss (já aplicado no __init__)

        # OBS: O __init__ do Pokémon já calcula move_speed corretamente
        # Não sobrescreva com valor fixo!

        pokemon._just_spawned = True
        pokemon._spawn_timer = 0.5
        pokemon._escaped_counted = False

        # ===== GARANTE QUE O COOLDOWN ESTÁ CORRETO =====
        # O __init__ do Pokémon já define charge_cooldown_max:
        # - Boss: 1.2 segundos
        # - Normal: 3.0 segundos
        # Não precisa modificar!

        print(
            f"[SurvivalWave] {pokemon.name} criado - Speed: {pokemon.move_speed:.2f}, Cooldown: {pokemon.charge_cooldown_max:.1f}s")

        return pokemon

    def update(self, dt: float) -> List[Pokemon]:
        """
        Atualiza waves - APENAS MOVIMENTO.
        O COMBATE É PROCESSADO PELO GAME_SCENE.
        """
        if self.paused:
            return []

        enemies_at_end = []

        # Entre waves
        if not self.wave_active:
            if self.between_waves_timer <= 0:
                self._prepare_next_wave()
                self.wave_active = True
            else:
                self.between_waves_timer -= dt
                return []

        # Delay inicial da wave
        if self.wave_timer > 0:
            self.wave_timer -= dt
            if self.wave_timer > 0:
                return []
            self.spawn_timer = 0

        # Spawn de novos inimigos
        if self.enemies_spawned_in_wave < self.enemies_to_spawn:
            self.spawn_timer -= dt

            if self.spawn_timer <= 0:
                enemy = self._create_enemy()
                if enemy:
                    if hasattr(self.game_scene, 'battle_system'):
                        enemy.set_battle_system(self.game_scene.battle_system)

                    self.active_enemies.append(enemy)
                    self.enemies_spawned_in_wave += 1
                    print(
                        f"[SurvivalWave] Spawn #{self.enemies_spawned_in_wave}/{self.enemies_to_spawn}: {enemy.name} Lv.{enemy.level}")

                    self.spawn_timer = self.current_wave_config.spawn_interval

        # ===== APENAS MOVIMENTO - SEM COMBATE AQUI! =====
        enemies_to_remove = []

        for enemy in self.active_enemies[:]:
            try:
                if not hasattr(enemy, 'path') or not enemy.path:
                    continue

                # Verifica se o inimigo está morto
                if not enemy.is_alive() or enemy.is_defeated:
                    if not getattr(enemy, '_marked_for_removal', False):
                        self._handle_enemy_death(enemy)
                        enemies_to_remove.append(enemy)
                    continue

                # ===== VERIFICA SE DEVE PARAR (TEM ALIADO NO RANGE) =====
                # Isso é usado APENAS para decidir se move ou não
                should_stop = False
                if hasattr(self.game_scene, 'player_pokemon'):
                    for ally in self.game_scene.player_pokemon:
                        if not ally.is_alive() or ally.is_defeated:
                            continue
                        dx = ally.x - enemy.x
                        dy = ally.y - enemy.y
                        distance = math.hypot(dx, dy)
                        if distance < enemy.attack_range:
                            should_stop = True
                            break

                # Se tem aliado no range, NÃO MOVE (para de andar)
                if should_stop:
                    # Não atualiza movimento - fica parado
                    # A animação será tratada pelo game_scene
                    continue

                # ===== MOVIMENTO NORMAL (sem aliados no range) =====
                if enemy.path_index >= len(enemy.path):
                    enemies_at_end.append(enemy)
                    continue

                target_x, target_y = enemy.path[enemy.path_index]
                dx = target_x - enemy.x
                dy = target_y - enemy.y
                distance = math.hypot(dx, dy)
                move_distance = enemy.move_speed * dt * 60

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

        # Remove inimigos mortos
        for enemy in enemies_to_remove:
            if enemy in self.active_enemies:
                self.active_enemies.remove(enemy)

        # Remove inimigos que chegaram ao fim
        for enemy in enemies_at_end:
            if enemy in self.active_enemies:
                self.active_enemies.remove(enemy)

        # Verifica se a wave terminou
        if self.enemies_spawned_in_wave >= self.enemies_to_spawn and len(self.active_enemies) == 0:
            self._complete_wave()

        return enemies_at_end

    def _get_direction_from_movement(self, dx: float, dy: float) -> str:
        """Retorna a direção baseada no movimento (8 direções)"""
        if dx == 0 and dy == 0:
            return "down"

        abs_dx = abs(dx)
        abs_dy = abs(dy)
        THRESHOLD = 0.41421356

        if abs_dx >= abs_dy:
            if dx > 0:
                if dy > 0 and abs_dy > abs_dx * THRESHOLD:
                    return "down-right"
                elif dy < 0 and abs_dy > abs_dx * THRESHOLD:
                    return "up-right"
                else:
                    return "right"
            else:
                if dy > 0 and abs_dy > abs_dx * THRESHOLD:
                    return "down-left"
                elif dy < 0 and abs_dy > abs_dx * THRESHOLD:
                    return "up-left"
                else:
                    return "left"
        else:
            if dy > 0:
                if dx > 0 and abs_dx > abs_dy * THRESHOLD:
                    return "down-right"
                elif dx < 0 and abs_dx > abs_dy * THRESHOLD:
                    return "down-left"
                else:
                    return "down"
            else:
                if dx > 0 and abs_dx > abs_dy * THRESHOLD:
                    return "up-right"
                elif dx < 0 and abs_dx > abs_dy * THRESHOLD:
                    return "up-left"
                else:
                    return "up"

    def _handle_enemy_death(self, enemy: Pokemon):
        """Processa morte de um inimigo e DA ENERGIA E XP"""
        self.enemies_killed += 1

        # ===== DISTRIBUI XP E EVS (COPIADO DO WAVE_MANAGER ORIGINAL) =====
        self._distribute_xp(enemy)

        # ===== DA ENERGIA AO MATAR =====
        if hasattr(self.game_scene, 'add_energy'):
            energy_gain = 15  # Energia base
            if enemy.is_boss:
                energy_gain = 60  # Boss da mais energia
            elif enemy.is_shiny:
                energy_gain = 30  # Shiny da um bonus
            self.game_scene.add_energy(energy_gain)
            print(f"[SurvivalWave] {enemy.name} derrotado! +{energy_gain} energia")

        # ===== DA PONTOS =====
        if hasattr(self.game_scene, 'add_score'):
            score_gain = 10
            if enemy.is_boss:
                score_gain = 150
            elif enemy.is_shiny:
                score_gain = 50
            self.game_scene.add_score(score_gain)
            print(f"[SurvivalWave] +{score_gain} pontos")

        # Marca para remocao
        enemy._marked_for_removal = True
        enemy.is_defeated = True
        enemy.current_hp = 0

        # Limpa referencia de aliados
        if hasattr(self.game_scene, 'player_pokemon'):
            for ally in self.game_scene.player_pokemon:
                if hasattr(ally, 'target') and ally.target == enemy:
                    ally.target = None
                    ally.combat_state = "idle"

        # Remove do effect manager
        if hasattr(enemy, 'effect_manager') and enemy.effect_manager:
            try:
                enemy.effect_manager.unregister_pokemon(enemy)
            except:
                pass

        print(f"[SurvivalWave] {enemy.name} removido do campo!")

    def _distribute_xp(self, defeated_enemy: 'Pokemon'):
        """Distribui XP e EVs quando um inimigo é derrotado (COPIADO DO WAVE_MANAGER ORIGINAL)"""
        contributors = defeated_enemy.get_xp_contributors()
        if not contributors:
            print(f"[XP] Nenhum contribuidor para {defeated_enemy.name}")
            return

        # ===== BASE XP =====
        base_xp = 15 + (defeated_enemy.level * 5)

        # Bônus para boss
        if defeated_enemy.is_boss:
            base_xp = int(base_xp * 3)
            print(f"[XP] BOSS derrotado! XP base: {base_xp}")

        if defeated_enemy.is_shiny:
            base_xp = int(base_xp * 1.5)

        total_contribution = defeated_enemy.get_total_contribution()
        if total_contribution <= 0:
            total_contribution = len(contributors)

        # Obtém os EVs concedidos pelo inimigo derrotado
        pokedex = self.game_scene.game.player.pokedex if self.game_scene.game.player else None
        if not pokedex:
            return

        ev_yield = pokedex.get_ev_yield(defeated_enemy.id)

        # Aplica multiplicadores para boss/shiny
        ev_multiplier = 1.0
        if defeated_enemy.is_boss:
            ev_multiplier *= 3
        if defeated_enemy.is_shiny:
            ev_multiplier *= 2

        for attacker_id, contribution in contributors:
            proportion = contribution / total_contribution
            xp_gained = int(base_xp * proportion)

            # EVs são distribuídos proporcionalmente
            evs_gained = {}
            for stat, value in ev_yield.items():
                if value > 0:
                    ev_value = max(1, int(value * proportion * ev_multiplier))
                    evs_gained[stat] = ev_value

            if xp_gained < 1 and contribution > 0:
                xp_gained = 1

            # Procura o Pokémon aliado que causou o dano
            for ally in self.game_scene.player_pokemon:
                if id(ally) == attacker_id and ally.is_alive():
                    old_level = ally.level
                    ally.gain_xp(xp_gained)

                    # Ganha EVs
                    if any(evs_gained.values()):
                        if ally.stats.can_gain_evs(evs_gained):
                            ally.stats.gain_evs(evs_gained)
                            print(f"[XP] {ally.name} ganhou {xp_gained} XP e EVs: {evs_gained}")
                        else:
                            print(f"[XP] {ally.name} ganhou {xp_gained} XP (EVs bloqueados)")
                    else:
                        print(f"[XP] {ally.name} ganhou {xp_gained} XP")

                    # Verifica level up
                    if ally.level > old_level:
                        print(f"[XP] {ally.name} subiu para o nível {ally.level}!")
                    break

    def _complete_wave(self):
        """Completa a wave atual e prepara a próxima"""
        print(f"[SurvivalWave] WAVE {self.current_wave} COMPLETA!")

        # ===== NÃO PERDE VIDA AQUI! =====
        # Apenas dá bônus

        if hasattr(self.game_scene, 'add_energy'):
            bonus = 50 + (self.current_wave - 1) * 10
            self.game_scene.add_energy(bonus)

        if hasattr(self.game_scene, 'survival_ui'):
            self.game_scene.survival_ui.show_message(
                f"ONDA {self.current_wave} COMPLETA",
                (100, 255, 100),
                duration=2.0
            )

        self.current_wave += 1
        self.wave_active = False
        self.between_waves_timer = self.between_waves_duration

    def remove_enemy(self, enemy: Pokemon):
        self._handle_enemy_death(enemy)

    def get_current_wave_info(self, active_enemies_count: int = None) -> dict:
        if active_enemies_count is None:
            active_enemies_count = len(self.active_enemies)

        progress = 0
        if self.enemies_to_spawn > 0:
            progress = self.enemies_spawned_in_wave / self.enemies_to_spawn

        name = f"Onda {self.current_wave}"
        if self.current_wave_config and self.current_wave_config.has_boss:
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

    def is_wave_completely_finished(self) -> bool:
        return not self.wave_active and self.between_waves_timer <= 0

    def has_more_waves(self) -> bool:
        return True  # Survival infinito

    def has_active_waves(self) -> bool:
        return self.wave_active or self.enemies_spawned_in_wave > 0