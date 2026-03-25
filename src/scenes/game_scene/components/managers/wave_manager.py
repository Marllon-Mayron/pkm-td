# src/scenes/game_scene/components/managers/wave_manager.py
import random
import math
from src.entities.pokemon import Pokemon


class GameWaveManager:
    """Gerencia as waves durante o jogo - OTIMIZADO"""
    # Constantes
    DEFAULT_WAVE_SIZE = 10
    DEFAULT_SPAWN_INTERVAL = 3.0
    DEFAULT_INITIAL_DELAY = 2.0
    PROXIMITY_THRESHOLD = 15  # Distância para considerar "próximo" do início/fim

    def __init__(self, phase_loader):
        self.phase_loader = phase_loader
        self.waves_data = []
        self.path_waves = {}

        self.paused = False

        # Estado das waves (por path) - usando listas para acesso mais rápido
        self.path_indexes = []  # Lista de todos os path indexes
        self.current_wave_index_by_path = {}
        self.wave_in_progress_by_path = {}
        self.wave_timer_by_path = {}
        self.spawn_timer_by_path = {}
        self.enemies_spawned_by_path = {}
        self.enemies_remaining_by_path = {}
        self.current_wave_data_by_path = {}

        # Lista principal de inimigos
        self.active_enemies = []

        # Referências
        self.target_items = []
        self.game_scene = None

        # Cache para evitar acessos repetidos
        self._path_points_cache = {}
        self._wave_completion_cache = {}
        self._boss_check_cache = {}

        # Carrega os dados
        self._load_waves_data()
        self._initialize_path_states()

        self.total_gold_earned = 0  # Total de ouro acumulado nesta fase
        self.gold_per_defeat = 10  # Ouro base por Pokémon derrotado

    def _load_waves_data(self):
        """Carrega os dados das waves do phase_loader e organiza por path"""
        raw_data = self.phase_loader.get_waves_data()

        if isinstance(raw_data, list):
            self.waves_data = raw_data
            self.path_waves = {}

            for wave_data in self.waves_data:
                path_index = wave_data.get("path_index", 0)
                if path_index not in self.path_waves:
                    self.path_waves[path_index] = []
                self.path_waves[path_index].append(wave_data)

            self.path_indexes = list(self.path_waves.keys())
            print(f"[WaveManager] Waves carregadas: {len(self.waves_data)}")
        else:
            self.waves_data = []
            self.path_waves = {}
            self.path_indexes = []
            print("⚠️ raw_data não é uma lista, criando lista vazia")

    def _initialize_path_states(self):
        """Inicializa o estado para todos os paths"""
        for path_index in self.path_waves.keys():
            self.current_wave_index_by_path[path_index] = 0
            self.wave_in_progress_by_path[path_index] = False
            self.wave_timer_by_path[path_index] = 0
            self.spawn_timer_by_path[path_index] = 0
            self.enemies_spawned_by_path[path_index] = 0
            self.enemies_remaining_by_path[path_index] = 0
            self.current_wave_data_by_path[path_index] = None

    def start_all_waves(self):
        """Inicia todas as primeiras waves de todos os paths simultaneamente"""
        started_any = False

        for path_index in self.path_indexes:
            waves = self.path_waves[path_index]
            if waves and self.current_wave_index_by_path[path_index] < len(waves):
                self._start_wave_for_path(path_index)
                started_any = True
                print(f"[WaveManager] Iniciando Wave 1 do Path {path_index + 1}")

        return started_any

    def _start_wave_for_path(self, path_index):
        """Inicia a próxima wave para um path específico"""
        waves = self.path_waves.get(path_index)
        if not waves:
            return False

        current_idx = self.current_wave_index_by_path.get(path_index, 0)
        if current_idx >= len(waves):
            return False

        wave_data = waves[current_idx]

        self.current_wave_data_by_path[path_index] = wave_data
        self.wave_in_progress_by_path[path_index] = True
        self.wave_timer_by_path[path_index] = wave_data.get("initial_delay", self.DEFAULT_INITIAL_DELAY)
        self.spawn_timer_by_path[path_index] = 0
        self.enemies_spawned_by_path[path_index] = 0
        self.enemies_remaining_by_path[path_index] = 0

        # Log reduzido
        # print(f"[WaveManager] Path {path_index + 1} - Iniciando Wave {current_idx + 1}")
        return True

    def set_target_items(self, items):
        """Define a lista de itens alvo para os inimigos"""
        self.target_items = items
        print(f"[WaveManager] Itens alvo vinculados: {len(items)} itens")

    def update(self, dt, path_points_by_index, screen_manager):
        """Atualiza o estado das waves de TODOS os paths - OTIMIZADO"""
        if self.paused:
            return []

        enemies_at_end = []
        enemies_to_remove = []
        defeated_enemies = []

        # Cache local para acesso rápido
        active_enemies = self.active_enemies
        target_items = self.target_items
        game_scene = self.game_scene
        proximity_threshold = self.PROXIMITY_THRESHOLD
        proximity_threshold_sq = proximity_threshold * proximity_threshold

        # ===== 1. Atualiza todos os inimigos existentes =====
        for enemy in active_enemies[:]:
            # Atualiza o inimigo
            enemy.update(dt, items=target_items)

            # Verifica se morreu
            if not enemy.is_alive():
                defeated_enemies.append(enemy)
                if enemy.is_carrying:
                    enemy.drop_item()
                enemies_to_remove.append(enemy)
                continue

            # Verifica chegada ao início/fim do path
            if hasattr(enemy, 'path') and enemy.path:
                path_len = len(enemy.path)
                path_index_val = enemy.path_index

                # Verifica se chegou ao início OU fim
                at_start = (path_index_val <= 0)
                at_end = (path_index_val >= path_len)

                if at_start or at_end:
                    # Processa inimigo que chegou ao fim/início
                    self._handle_enemy_at_boundary(enemy, at_start, at_end, enemies_at_end, enemies_to_remove)
                    continue

                # Verifica proximidade (apenas para inimigos não-boss carregando item)
                if not enemy.is_boss and enemy.is_carrying and enemy.path:
                    is_returning = hasattr(enemy, 'is_returning_with_item') and enemy.is_returning_with_item

                    if not is_returning:
                        # Verifica proximidade usando distância quadrática para performance
                        start_point = enemy.path[0]
                        end_point = enemy.path[-1]

                        dx_start = enemy.x - start_point[0]
                        dy_start = enemy.y - start_point[1]
                        dist_start_sq = dx_start * dx_start + dy_start * dy_start

                        dx_end = enemy.x - end_point[0]
                        dy_end = enemy.y - end_point[1]
                        dist_end_sq = dx_end * dx_end + dy_end * dy_end

                        if dist_start_sq < proximity_threshold_sq or dist_end_sq < proximity_threshold_sq:
                            carried_item = enemy.is_carrying
                            carried_item.is_protected = False
                            carried_item.is_stolen = True

                            if game_scene and hasattr(game_scene, 'target_item_manager'):
                                game_scene.target_item_manager.mark_item_as_stolen(carried_item)

                            enemies_at_end.append(enemy)
                            enemies_to_remove.append(enemy)
                            continue

        # Processa XP dos inimigos derrotados
        if defeated_enemies:
            for enemy in defeated_enemies:
                self._distribute_xp(enemy)

        # Remove inimigos
        if enemies_to_remove:
            self._remove_enemies_batch(enemies_to_remove)

        # ===== 2. Processa waves para CADA PATH =====
        self._process_all_waves(dt, path_points_by_index, screen_manager)

        return enemies_at_end

    def _handle_enemy_at_boundary(self, enemy, at_start, at_end, enemies_at_end, enemies_to_remove):
        """Processa inimigo que chegou ao início ou fim do path"""
        if enemy.is_carrying:
            carried_item = enemy.is_carrying
            # Marca item como roubado
            carried_item.is_protected = False
            carried_item.is_stolen = True
            carried_item.carried_by = None

            if hasattr(self.game_scene, 'target_item_manager'):
                self.game_scene.target_item_manager.mark_item_as_stolen(carried_item)

            enemy.clear_carrying()

            if enemy.is_boss:
                # Boss: reseta e continua
                if hasattr(enemy, 'original_path') and enemy.original_path:
                    enemy.path = enemy.original_path.copy()
                    enemy.path_index = 0
                    if enemy.path and len(enemy.path) > 0:
                        enemy.x, enemy.y = enemy.path[0]
                        enemy.rect.x, enemy.rect.y = enemy.x, enemy.y

                enemy.is_returning_with_item = False
                enemy.move_speed = enemy.base_move_speed
                return  # Boss continua vivo
            else:
                enemies_at_end.append(enemy)
                enemies_to_remove.append(enemy)
        else:
            # Sem item
            if enemy.is_boss:
                # Boss sem item: reseta
                if hasattr(enemy, 'original_path') and enemy.original_path:
                    enemy.path = enemy.original_path.copy()
                    enemy.path_index = 0
                    if enemy.path and len(enemy.path) > 0:
                        enemy.x, enemy.y = enemy.path[0]
                        enemy.rect.x, enemy.rect.y = enemy.x, enemy.y
                return
            else:
                enemies_at_end.append(enemy)
                enemies_to_remove.append(enemy)

    def _remove_enemies_batch(self, enemies_to_remove):
        """Remove múltiplos inimigos em lote"""
        for enemy in enemies_to_remove:
            if enemy in self.active_enemies:
                path_index = getattr(enemy, 'path_index_origin', 0)
                self.active_enemies.remove(enemy)

                if path_index in self.enemies_remaining_by_path:
                    self.enemies_remaining_by_path[path_index] -= 1

                enemy.clear_damage_tracking()

                if enemy.is_carrying:
                    carried_item = enemy.is_carrying
                    if carried_item.is_protected and hasattr(self.game_scene, 'target_item_manager'):
                        self.game_scene.target_item_manager.mark_item_as_stolen(carried_item)
                    carried_item.carried_by = None
                    enemy.is_carrying = None

    def _process_all_waves(self, dt, path_points_by_index, screen_manager):
        """Processa todas as waves de todos os paths - OTIMIZADO"""
        for path_index in self.path_indexes:
            waves = self.path_waves.get(path_index)
            if not waves:
                continue

            wave_in_progress = self.wave_in_progress_by_path.get(path_index, False)
            current_idx = self.current_wave_index_by_path.get(path_index, 0)

            if current_idx >= len(waves):
                continue

            wave_data = self.current_wave_data_by_path.get(path_index)
            if not wave_data and wave_in_progress:
                self.wave_in_progress_by_path[path_index] = False
                continue

            if wave_in_progress and wave_data:
                self._process_single_wave(dt, path_index, wave_data, path_points_by_index, screen_manager)

    def _process_single_wave(self, dt, path_index, wave_data, path_points_by_index, screen_manager):
        """Processa uma wave individual - OTIMIZADO"""
        # Delay inicial
        if self.wave_timer_by_path[path_index] > 0:
            self.wave_timer_by_path[path_index] -= dt
            return

        enemies_spawned = self.enemies_spawned_by_path[path_index]
        wave_size = wave_data.get("wave_size", self.DEFAULT_WAVE_SIZE)

        if enemies_spawned < wave_size:
            self.spawn_timer_by_path[path_index] -= dt

            if self.spawn_timer_by_path[path_index] <= 0:
                path_points = path_points_by_index.get(path_index, [])
                enemy = self._create_enemy(wave_data, path_points, screen_manager, path_index)

                if enemy:
                    enemy.path_index_origin = path_index
                    self.active_enemies.append(enemy)
                    self.enemies_spawned_by_path[path_index] += 1
                    self.enemies_remaining_by_path[path_index] += 1

                    self.spawn_timer_by_path[path_index] = wave_data.get("spawn_interval", self.DEFAULT_SPAWN_INTERVAL)

        # Verifica se a wave terminou
        if self.enemies_spawned_by_path[path_index] >= wave_size:
            if self.enemies_remaining_by_path[path_index] <= 0:
                self._end_current_wave_for_path(path_index)

    def _end_current_wave_for_path(self, path_index):
        """Finaliza a wave atual de um path específico - OTIMIZADO"""
        wave_data = self.current_wave_data_by_path.get(path_index)
        if not wave_data:
            return

        # Verifica se ainda tem bosses vivos (otimizado com cache)
        bosses_alive = 0
        for e in self.active_enemies:
            if hasattr(e, 'is_boss') and e.is_boss and getattr(e, 'path_index_origin', 0) == path_index:
                bosses_alive += 1

        if bosses_alive > 0:
            return

        # Verifica repetição
        if wave_data.get("repeat_wave", False):
            repeat_count = wave_data.get("repeat_count", 1)
            if repeat_count > 1:
                wave_data["repeat_count"] = repeat_count - 1
                self.wave_in_progress_by_path[path_index] = True
                self.enemies_spawned_by_path[path_index] = 0
                self.enemies_remaining_by_path[path_index] = 0
                self.wave_timer_by_path[path_index] = wave_data.get("initial_delay", self.DEFAULT_INITIAL_DELAY)
                return

        # Passa para próxima wave
        self.wave_in_progress_by_path[path_index] = False
        self.current_wave_index_by_path[path_index] += 1
        self.current_wave_data_by_path[path_index] = None

    def _create_enemy(self, wave_data, path_points, screen_manager, path_index):
        """Cria um inimigo - OTIMIZADO"""
        enemy_data = self._get_random_enemy(wave_data)

        if not enemy_data or not path_points or len(path_points) < 2:
            return None

        start_x, start_y = path_points[0]

        level = random.randint(
            wave_data.get("min_level", 1),
            wave_data.get("max_level", 5)
        )

        enemies_spawned = self.enemies_spawned_by_path.get(path_index, 0)
        wave_size = wave_data.get("wave_size", self.DEFAULT_WAVE_SIZE)
        is_last_enemy = (enemies_spawned + 1) >= wave_size
        is_boss = is_last_enemy and wave_data.get("has_boss", True)

        pokemon = Pokemon(
            start_x, start_y,
            enemy_data["pokemon_id"],
            level=level,
            is_wild=True,
            shiny=random.random() < 0.001,
            is_boss=is_boss
        )


        pokemon.screen_manager = screen_manager
        pokemon.path = path_points

        if hasattr(self.game_scene, 'battle_system'):
            pokemon.set_battle_system(self.game_scene.battle_system)

        # Aplica multiplicador de velocidade
        wave_speed_multiplier = wave_data.get("speed_multiplier", 1.0)
        if wave_speed_multiplier != 1.0:
            pokemon.move_speed = pokemon.base_move_speed * wave_speed_multiplier

        if is_boss:
            pokemon.original_path = path_points.copy()
            # Log reduzido
            # print(f"[BOSS] Criado {pokemon.name} Lv.{pokemon.level}")

        pokemon.path_index = 0
        pokemon.path_index_origin = path_index

        # Define direção inicial
        if len(path_points) > 1:
            dx = path_points[1][0] - path_points[0][0]
            dy = path_points[1][1] - path_points[0][1]

            if abs(dx) > abs(dy):
                pokemon.current_direction = "right" if dx > 0 else "left"
            else:
                pokemon.current_direction = "down" if dy > 0 else "up"

        return pokemon

    def _get_random_enemy(self, wave_data):
        """Retorna um inimigo aleatório - OTIMIZADO"""
        enemies = wave_data.get("enemies", [])
        if not enemies:
            return None

        total = 0
        for e in enemies:
            total += e.get("percentage", 0)

        if total <= 0:
            return random.choice(enemies)

        roll = random.uniform(0, total)
        cumulative = 0

        for enemy in enemies:
            cumulative += enemy.get("percentage", 0)
            if roll <= cumulative:
                return enemy

        return enemies[-1]

    def _distribute_xp(self, defeated_enemy):
        """Distribui XP e Ouro - OTIMIZADO"""
        contributors = defeated_enemy.get_xp_contributors()

        if not contributors:
            return

        # ===== ADICIONAR OURO =====
        gold_gained = self.gold_per_defeat
        self.total_gold_earned += gold_gained

        # Atualiza o gold do jogador em tempo real
        if hasattr(self.game_scene, 'game') and self.game_scene.game:
            self.game_scene.game.player.money += gold_gained
            print(f"[GOLD] +{gold_gained} ouro por derrotar {defeated_enemy.name}")

        # Distribui XP normalmente
        base_xp = 15 + (defeated_enemy.level * 5)
        total_damage = sum(damage for _, damage in contributors)

        if total_damage <= 0:
            return

        placement_manager = None
        if hasattr(self.game_scene, 'placement_manager'):
            placement_manager = self.game_scene.placement_manager

        if not placement_manager:
            return

        for attacker_id, damage in contributors:
            proportion = damage / total_damage
            xp_gained = int(base_xp * proportion)

            for pokemon in placement_manager.placed_pokemon:
                if id(pokemon) == attacker_id and pokemon.is_alive():
                    pokemon.gain_xp(xp_gained)
                    if hasattr(self.game_scene, 'game') and self.game_scene.game:
                        self.game_scene.game.player.auto_save()
                    break

    def get_total_gold_earned(self):
        """Retorna o total de ouro ganho nesta fase"""
        return self.total_gold_earned

    def remove_enemy(self, enemy):
        """Remove um inimigo da lista ativa"""
        if enemy in self.active_enemies:
            if enemy.is_carrying:
                carried_item = enemy.is_carrying
                if carried_item.is_protected and hasattr(self.game_scene, 'target_item_manager'):
                    self.game_scene.target_item_manager.mark_item_as_stolen(carried_item)
                enemy.drop_item()

            path_index = getattr(enemy, 'path_index_origin', 0)
            self.active_enemies.remove(enemy)

            if path_index in self.enemies_remaining_by_path:
                self.enemies_remaining_by_path[path_index] -= 1

            return True
        return False

    def get_current_wave_info(self):
        """Retorna informações consolidadas - OTIMIZADO"""
        total_active_paths = 0
        for path_index in self.path_indexes:
            if self.wave_in_progress_by_path.get(path_index, False):
                total_active_paths += 1

        # Calcula totais
        total_spawned = sum(self.enemies_spawned_by_path.values())
        total_enemies = 0
        for w in self.waves_data:
            total_enemies += w.get("wave_size", self.DEFAULT_WAVE_SIZE)

        if total_active_paths == 0:
            # Verifica se todos os paths concluíram
            all_completed = True
            for path_idx in self.path_indexes:
                if self.current_wave_index_by_path.get(path_idx, 0) < len(self.path_waves.get(path_idx, [])):
                    all_completed = False
                    break

            if all_completed:
                return {
                    "name": "Fase Completa!",
                    "index": len(self.waves_data),
                    "total": len(self.waves_data),
                    "enemies_remaining": len(self.active_enemies),
                    "enemies_spawned": total_spawned,
                    "enemies_total": total_enemies,
                    "progress": 1.0,
                    "active_paths": 0
                }
            else:
                return {
                    "name": "Aguardando...",
                    "index": 1,
                    "total": len(self.waves_data),
                    "enemies_remaining": len(self.active_enemies),
                    "enemies_spawned": total_spawned,
                    "enemies_total": total_enemies,
                    "progress": 0,
                    "active_paths": 0
                }

        return {
            "name": f"{total_active_paths} wave(s) ativa(s)",
            "index": "Múltiplas",
            "total": len(self.waves_data),
            "enemies_remaining": len(self.active_enemies),
            "enemies_spawned": total_spawned,
            "enemies_total": total_enemies,
            "progress": total_spawned / total_enemies if total_enemies > 0 else 0,
            "active_paths": total_active_paths
        }

    def has_more_waves(self):
        """Verifica se ainda existem waves"""
        for path_idx in self.path_indexes:
            if self.current_wave_index_by_path.get(path_idx, 0) < len(self.path_waves.get(path_idx, [])):
                return True
        return False

    def is_wave_completely_finished(self):
        """Verifica se TODAS as waves terminaram - OTIMIZADO"""
        if self.active_enemies:
            return False

        for path_idx in self.path_indexes:
            if self.wave_in_progress_by_path.get(path_idx, False):
                return False

            if self.current_wave_index_by_path.get(path_idx, 0) < len(self.path_waves.get(path_idx, [])):
                wave_data = self.current_wave_data_by_path.get(path_idx)
                if wave_data:
                    wave_size = wave_data.get("wave_size", self.DEFAULT_WAVE_SIZE)
                    if self.enemies_spawned_by_path.get(path_idx, 0) < wave_size:
                        return False
                else:
                    return False

        return True