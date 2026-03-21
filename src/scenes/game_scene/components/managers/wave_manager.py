# src/scenes/game_scene/components/managers/wave_manager.py

import random, math
from src.entities.pokemon import Pokemon


class GameWaveManager:
    """Gerencia as waves durante o jogo - AGORA SUPORTA MÚLTIPLOS PATHS SIMULTÂNEOS"""

    def __init__(self, phase_loader):
        self.phase_loader = phase_loader
        self.waves_data = []  # Lista de todas as waves
        self.path_waves = {}  # Dicionário: path_index -> lista de waves daquele path

        # Estado das waves (agora por path)
        self.current_wave_index_by_path = {}  # path_index -> índice da wave atual
        self.wave_in_progress_by_path = {}  # path_index -> se está em progresso
        self.wave_timer_by_path = {}  # path_index -> timer atual
        self.spawn_timer_by_path = {}  # path_index -> timer de spawn
        self.enemies_spawned_by_path = {}  # path_index -> inimigos spawnados
        self.enemies_remaining_by_path = {}  # path_index -> inimigos restantes
        self.current_wave_data_by_path = {}  # path_index -> dados da wave atual

        # Lista principal de inimigos (todos juntos)
        self.active_enemies = []

        # Referência para os itens alvo
        self.target_items = []

        self.game_scene = None

        # Carrega os dados
        self._load_waves_data()

        # Inicializa o estado para cada path
        self._initialize_path_states()

    def _load_waves_data(self):
        """Carrega os dados das waves do phase_loader e organiza por path"""
        raw_data = self.phase_loader.get_waves_data()

        if isinstance(raw_data, list):
            self.waves_data = raw_data

            # Organiza waves por path
            self.path_waves = {}
            for wave_data in self.waves_data:
                path_index = wave_data.get("path_index", 0)
                if path_index not in self.path_waves:
                    self.path_waves[path_index] = []
                self.path_waves[path_index].append(wave_data)

            print(f"[WaveManager] Waves carregadas: {len(self.waves_data)}")
            for path_idx, waves in self.path_waves.items():
                print(f"  Path {path_idx + 1}: {len(waves)} waves")
        else:
            self.waves_data = []
            self.path_waves = {}
            print("⚠️ raw_data não é uma lista, criando lista vazia")

    def _initialize_path_states(self):
        """Inicializa o estado para todos os paths que têm waves"""
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

        for path_index, waves in self.path_waves.items():
            if waves and self.current_wave_index_by_path[path_index] < len(waves):
                self._start_wave_for_path(path_index)
                started_any = True
                print(f"[WaveManager] Iniciando Wave 1 do Path {path_index + 1}")

        return started_any

    def _start_wave_for_path(self, path_index):
        """Inicia a próxima wave para um path específico"""
        if path_index not in self.path_waves:
            print(f"[WaveManager] Path {path_index} não tem waves definidas")
            return False

        waves = self.path_waves[path_index]
        current_idx = self.current_wave_index_by_path[path_index]

        if current_idx >= len(waves):
            print(f"[WaveManager] Path {path_index + 1} já concluiu todas as waves")
            return False

        wave_data = waves[current_idx]

        # Configura a wave atual para este path
        self.current_wave_data_by_path[path_index] = wave_data
        self.wave_in_progress_by_path[path_index] = True
        self.wave_timer_by_path[path_index] = wave_data.get("initial_delay", 2.0)
        self.spawn_timer_by_path[path_index] = 0
        self.enemies_spawned_by_path[path_index] = 0
        self.enemies_remaining_by_path[path_index] = 0

        print(
            f"[WaveManager] Path {path_index + 1} - Iniciando Wave {current_idx + 1}: {wave_data.get('name', 'Wave')} "
            f"(delay inicial: {self.wave_timer_by_path[path_index]:.1f}s)"
        )
        return True

    def set_target_items(self, items):
        """Define a lista de itens alvo para os inimigos"""
        self.target_items = items
        print(f"[WaveManager] Itens alvo vinculados: {len(items)} itens")

    def update(self, dt, path_points_by_index, screen_manager):
        """Atualiza o estado das waves de TODOS os paths"""
        enemies_at_end = []
        enemies_to_remove = []
        defeated_enemies = []

        # ===== 1. Atualiza todos os inimigos existentes =====
        for enemy in self.active_enemies[:]:
            # Atualiza o inimigo (movimento e captura de itens)
            enemy.update(dt, items=self.target_items)

            # Verifica se morreu
            if not enemy.is_alive():
                print(f"[WAVE] {enemy.name} foi derrotado!")
                defeated_enemies.append(enemy)

                if enemy.is_carrying:
                    enemy.drop_item()

                enemies_to_remove.append(enemy)
                continue

            # ===== VERIFICA SE CHEGOU AO FIM DO PATH =====
            if hasattr(enemy, 'path') and enemy.path and enemy.path_index >= len(enemy.path):
                # ===== BOSS: NÃO É REMOVIDO, VOLTA PARA O INÍCIO =====
                if hasattr(enemy, 'is_boss') and enemy.is_boss:
                    # BOSS: Chegou ao fim do path atual
                    print(f"[BOSS] {enemy.name} chegou ao fim do path!")

                    # ===== VERIFICA SE BOSS ESTÁ CARREGANDO ITEM =====
                    if enemy.is_carrying:
                        # Boss está carregando item e chegou ao fim (que é o início original do path)
                        print(
                            f"[BOSS] {enemy.name} está carregando {enemy.is_carrying.item_name} e completou o caminho de volta!")
                        print(f"[BOSS] {enemy.is_carrying.item_name} foi levado com sucesso e DESAPARECE!")

                        carried_item = enemy.is_carrying
                        carried_item.is_protected = False
                        carried_item.is_stolen = True
                        carried_item.carried_by = None

                        # Marca o item como roubado no target_item_manager
                        if hasattr(self.game_scene, 'target_item_manager'):
                            self.game_scene.target_item_manager.mark_item_as_stolen(carried_item)

                        enemy.clear_carrying()

                        # Resetar a flag de retorno do boss e velocidade
                        enemy.is_returning_with_item = False
                        enemy.speed = 0.6  # Volta à velocidade normal do boss
                        print(f"[BOSS] {enemy.name} perdeu o item, velocidade volta para {enemy.speed}")

                        # ===== RESTAURA O PATH ORIGINAL =====
                        if hasattr(enemy, 'original_path') and enemy.original_path:
                            enemy.path = enemy.original_path.copy()
                            print(f"[BOSS] {enemy.name} path restaurado para o original com {len(enemy.path)} pontos")

                        # Reseta para o início do path original
                        enemy.path_index = 0
                        if enemy.path and len(enemy.path) > 0:
                            enemy.x, enemy.y = enemy.path[0]
                            enemy.rect.x, enemy.rect.y = enemy.x, enemy.y
                            print(f"[BOSS] {enemy.name} resetado para o início do path original")

                        # Não adiciona à lista de remoção (boss continua vivo)
                        # IMPORTANTE: CONTINUA para não processar movimento neste frame
                        continue
                    else:
                        # Boss normal (sem item) reseta para o início sem perder item
                        print(f"[BOSS] {enemy.name} sem item, resetando para o início")

                        # Verifica se o path está invertido e precisa ser restaurado
                        if enemy.is_returning_with_item:
                            # Isso não deveria acontecer, mas por segurança
                            enemy.is_returning_with_item = False
                            enemy.speed = 0.6
                            # Restaura path original se necessário
                            if hasattr(enemy, 'original_path') and enemy.original_path:
                                enemy.path = enemy.original_path.copy()
                                print(f"[BOSS] {enemy.name} path restaurado para o original")

                        # Reseta para o início
                        enemy.path_index = 0
                        if enemy.path and len(enemy.path) > 0:
                            enemy.x, enemy.y = enemy.path[0]
                            enemy.rect.x, enemy.rect.y = enemy.x, enemy.y

                        # Não adiciona à lista de remoção
                        continue
                else:
                    # Inimigo normal: chega ao fim e é removido
                    print(f"[WAVE] {enemy.name} chegou ao FIM do path! Será removido.")

                    # ===== CORREÇÃO: Marca o item como roubado =====
                    if enemy.is_carrying:
                        carried_item = enemy.is_carrying
                        print(f"[WAVE] {enemy.name} levou {carried_item.item_name}!")

                        # Marca o item como roubado
                        carried_item.is_protected = False
                        carried_item.is_stolen = True

                        # ===== Marca o item como roubado no target_item_manager =====
                        if hasattr(self.game_scene, 'target_item_manager'):
                            self.game_scene.target_item_manager.mark_item_as_stolen(carried_item)

                    enemies_at_end.append(enemy)
                    enemies_to_remove.append(enemy)
                    continue

            # ===== VERIFICAÇÃO EXTRA: Inimigo voltando e próximo do início =====
            # Só para inimigos normais (não bosses)
            if not enemy.is_boss and enemy.is_carrying and enemy.path and len(enemy.path) > 0:
                # Verifica se está próximo do último ponto do path (que é o início original)
                last_point = enemy.path[-1]
                dist_to_start = math.hypot(enemy.x - last_point[0], enemy.y - last_point[1])

                # Se está a menos de 15 pixels do início, considera que chegou
                if dist_to_start < 15:
                    print(f"[WAVE] {enemy.name} está voltando e próximo do início! Distância: {dist_to_start:.1f}")
                    print(f"[WAVE] {enemy.name} levou {enemy.is_carrying.item_name}!")

                    # Marca o item como roubado
                    carried_item = enemy.is_carrying
                    carried_item.is_protected = False
                    carried_item.is_stolen = True

                    # ===== Marca o item como roubado no target_item_manager =====
                    if hasattr(self.game_scene, 'target_item_manager'):
                        self.game_scene.target_item_manager.mark_item_as_stolen(carried_item)

                    enemies_at_end.append(enemy)
                    enemies_to_remove.append(enemy)
                    continue

        # Processa XP dos inimigos derrotados
        for enemy in defeated_enemies:
            self._distribute_xp(enemy)

        # Remove inimigos normais (não bosses)
        for enemy in enemies_to_remove:
            if enemy in self.active_enemies:
                path_index = getattr(enemy, 'path_index_origin', 0)
                self.active_enemies.remove(enemy)
                if path_index in self.enemies_remaining_by_path:
                    self.enemies_remaining_by_path[path_index] -= 1
                enemy.clear_damage_tracking()

                # Remove o item permanentemente se estiver carregando
                if enemy.is_carrying:
                    carried_item = enemy.is_carrying
                    print(f"[WaveManager] {enemy.name} estava carregando {carried_item.item_name} e será removido!")

                    # Marca o item como roubado se ainda não foi marcado
                    if carried_item.is_protected:
                        if hasattr(self.game_scene, 'target_item_manager'):
                            self.game_scene.target_item_manager.mark_item_as_stolen(carried_item)

                    # Limpa referências
                    carried_item.carried_by = None
                    enemy.is_carrying = None

        # ===== 2. Processa waves para CADA PATH =====
        for path_index, waves in self.path_waves.items():
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
                if self.wave_timer_by_path[path_index] > 0:
                    self.wave_timer_by_path[path_index] -= dt
                    if self.wave_timer_by_path[path_index] <= 0:
                        print(f"[WaveManager] Path {path_index + 1} - Delay inicial terminado! Iniciando spawns...")
                    continue

                enemies_spawned = self.enemies_spawned_by_path[path_index]
                wave_size = wave_data.get("wave_size", 10)

                if enemies_spawned < wave_size:
                    self.spawn_timer_by_path[path_index] -= dt

                    if self.spawn_timer_by_path[path_index] <= 0:
                        path_points = path_points_by_index.get(path_index, [])

                        enemy = self._create_enemy(
                            wave_data,
                            path_points,
                            screen_manager,
                            path_index
                        )

                        if enemy:
                            enemy.path_index_origin = path_index

                            self.active_enemies.append(enemy)
                            self.enemies_spawned_by_path[path_index] += 1
                            self.enemies_remaining_by_path[path_index] += 1

                            print(
                                f"[WaveManager] Path {path_index + 1} - Spawnado {enemy.name} "
                                f"({enemies_spawned + 1}/{wave_size})"
                            )

                            self.spawn_timer_by_path[path_index] = wave_data.get("spawn_interval", 3.0)

                if self.enemies_spawned_by_path[path_index] >= wave_size:
                    if self.enemies_remaining_by_path[path_index] <= 0:
                        self._end_current_wave_for_path(path_index)

        return enemies_at_end

    def _end_current_wave_for_path(self, path_index):
        """Finaliza a wave atual de um path específico"""
        wave_data = self.current_wave_data_by_path.get(path_index)
        if not wave_data:
            return

        # Verifica se ainda tem bosses vivos neste path
        bosses_alive = sum(1 for e in self.active_enemies
                           if hasattr(e, 'is_boss') and e.is_boss
                           and getattr(e, 'path_index_origin', 0) == path_index)

        # Se ainda tem bosses vivos, não finaliza a wave
        if bosses_alive > 0:
            print(
                f"[WaveManager] Path {path_index + 1} - Ainda tem {bosses_alive} boss(es) vivo(s)! Continuando wave...")
            return

        print(
            f"\n[WaveManager] Path {path_index + 1} - Wave {self.current_wave_index_by_path[path_index] + 1} concluída!")

        # Verifica se a wave repete
        if wave_data.get("repeat_wave", False):
            repeat_count = wave_data.get("repeat_count", 1)

            if repeat_count > 1:
                # Decrementa contador e reinicia a mesma wave
                wave_data["repeat_count"] = repeat_count - 1
                self.wave_in_progress_by_path[path_index] = True
                self.enemies_spawned_by_path[path_index] = 0
                self.enemies_remaining_by_path[path_index] = 0
                self.wave_timer_by_path[path_index] = wave_data.get("initial_delay", 2.0)
                print(f"[WaveManager] Path {path_index + 1} - Repetindo wave... Restam {repeat_count - 1} repetições")
                return

        # Passa para próxima wave deste path
        self.wave_in_progress_by_path[path_index] = False
        self.current_wave_index_by_path[path_index] += 1
        self.current_wave_data_by_path[path_index] = None

        # Verifica se ainda tem mais waves para este path
        if self.current_wave_index_by_path[path_index] < len(self.path_waves.get(path_index, [])):
            print(f"[WaveManager] Path {path_index + 1} - Próxima wave disponível. Aguardando início...")
        else:
            print(f"[WaveManager] Path {path_index + 1} - TODAS AS WAVES CONCLUÍDAS!")

    def _create_enemy(self, wave_data, path_points, screen_manager, path_index):
        """Cria um inimigo baseado nos dados da wave (com suporte a boss)"""
        enemy_data = self._get_random_enemy(wave_data)

        if not enemy_data or not path_points or len(path_points) < 2:
            return None

        # Pega o ponto inicial
        start_x, start_y = path_points[0]

        # Nível aleatório
        level = random.randint(
            wave_data.get("min_level", 1),
            wave_data.get("max_level", 5)
        )

        # VERIFICA SE É O ÚLTIMO INIMIGO DA WAVE
        enemies_spawned = self.enemies_spawned_by_path.get(path_index, 0)
        wave_size = wave_data.get("wave_size", 10)
        is_last_enemy = (enemies_spawned + 1) >= wave_size

        # Se for o último inimigo, é boss!
        is_boss = is_last_enemy and wave_data.get("has_boss", True)

        # Cria o Pokémon inimigo
        pokemon = Pokemon(
            start_x, start_y,
            enemy_data["pokemon_id"],
            level=level,
            is_wild=True,
            shiny=random.random() < 0.001,
            is_boss=is_boss
        )

        pokemon.screen_manager = screen_manager

        # Configura para seguir o path
        pokemon.path = path_points
        pokemon.speed = 0.8

        # Boss é mais lento (mas mais forte)
        if is_boss:
            pokemon.speed = 0.6
            # ===== GUARDA O PATH ORIGINAL =====
            pokemon.original_path = path_points.copy()  # Cópia do path original
            print(f"[BOSS] Criado {pokemon.name} (Lv.{pokemon.level}) para Path {path_index + 1}")
            print(f"[BOSS] Path original guardado com {len(pokemon.original_path)} pontos")

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
        """Retorna um inimigo aleatório baseado nas porcentagens"""
        enemies = wave_data.get("enemies", [])
        if not enemies:
            return None

        total = sum(e.get("percentage", 0) for e in enemies)
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
        """Distribui XP para os atacantes quando um inimigo é derrotado"""
        contributors = defeated_enemy.get_xp_contributors()

        if not contributors:
            print(f"[XP] Nenhum contribuidor encontrado para {defeated_enemy.name}")
            return

        base_xp = 15 + (defeated_enemy.level * 5)
        print(f"\n[XP] ===== DISTRIBUINDO XP PARA {defeated_enemy.name.upper()} =====")
        print(f"[XP] XP base: {base_xp}")

        total_damage = sum(damage for _, damage in contributors)
        print(f"[XP] Dano total causado: {total_damage}")

        # Distribui XP proporcional ao dano
        for attacker_id, damage in contributors:
            proportion = damage / total_damage
            xp_gained = int(base_xp * proportion)

            # Encontra o Pokémon atacante
            attacker = self._find_attacker_by_id(attacker_id)

            if attacker:
                attacker.gain_xp(xp_gained)
                print(f"[XP] {attacker.name}: {damage} de dano ({proportion * 100:.1f}%) -> {xp_gained} XP")
                self.game_scene.game.player.auto_save()
            else:
                print(f"[XP] Não encontrou atacante com ID {attacker_id} no mapa")

    def _find_attacker_by_id(self, attacker_id):
        """Encontra um atacante pelo ID"""
        if not hasattr(self, 'game_scene') or not hasattr(self.game_scene, 'placement_manager'):
            return None

        for pokemon in self.game_scene.placement_manager.placed_pokemon:
            if id(pokemon) == attacker_id and pokemon.is_alive():
                return pokemon
        return None

    def remove_enemy(self, enemy):
        """Remove um inimigo da lista ativa"""
        if enemy in self.active_enemies:
            # ===== CORREÇÃO: Marca o item como roubado se estiver carregando =====
            if enemy.is_carrying:
                carried_item = enemy.is_carrying
                print(f"[WaveManager] Removendo {enemy.name} que estava carregando {carried_item.item_name}")

                # Marca o item como roubado no target_item_manager
                if carried_item.is_protected:
                    if hasattr(self.game_scene, 'target_item_manager'):
                        self.game_scene.target_item_manager.mark_item_as_stolen(carried_item)

                enemy.drop_item()

            path_index = getattr(enemy, 'path_index_origin', 0)
            self.active_enemies.remove(enemy)

            if path_index in self.enemies_remaining_by_path:
                self.enemies_remaining_by_path[path_index] -= 1

            print(f"[WaveManager] Inimigo {enemy.name} removido!")
            return True
        return False

    def get_current_wave_info(self):
        """Retorna informações consolidadas de todas as waves ativas"""
        total_active_paths = len([p for p in self.path_waves.keys()
                                  if self.wave_in_progress_by_path.get(p, False)])

        # Se não há waves ativas, mostra status de conclusão
        if total_active_paths == 0:
            # Verifica se todos os paths concluíram todas as waves
            all_completed = True
            for path_idx, waves in self.path_waves.items():
                if self.current_wave_index_by_path.get(path_idx, 0) < len(waves):
                    all_completed = False
                    break

            if all_completed:
                return {
                    "name": "Fase Completa!",
                    "index": len(self.waves_data),
                    "total": len(self.waves_data),
                    "enemies_remaining": len(self.active_enemies),
                    "enemies_spawned": sum(self.enemies_spawned_by_path.values()),
                    "enemies_total": sum(w.get("wave_size", 10) for w in self.waves_data),
                    "progress": 1.0,
                    "active_paths": 0
                }
            else:
                return {
                    "name": "Aguardando...",
                    "index": min(self.current_wave_index_by_path.values()) + 1
                    if self.current_wave_index_by_path else 1,
                    "total": len(self.waves_data),
                    "enemies_remaining": len(self.active_enemies),
                    "enemies_spawned": sum(self.enemies_spawned_by_path.values()),
                    "enemies_total": sum(w.get("wave_size", 10) for w in self.waves_data),
                    "progress": 0,
                    "active_paths": 0
                }

        # Calcula progresso consolidado
        total_spawned = sum(self.enemies_spawned_by_path.values())
        total_enemies = sum(w.get("wave_size", 10) for w in self.waves_data)

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
        """Verifica se ainda existem waves em qualquer path"""
        for path_idx, waves in self.path_waves.items():
            if self.current_wave_index_by_path.get(path_idx, 0) < len(waves):
                return True
        return False

    def is_wave_completely_finished(self):
        """
        Verifica se TODAS as waves de TODOS os paths terminaram
        """
        # Se ainda tem inimigos vivos, não terminou
        if self.active_enemies:
            return False

        # Verifica cada path
        for path_idx, waves in self.path_waves.items():
            # Se o path ainda está em progresso, não terminou
            if self.wave_in_progress_by_path.get(path_idx, False):
                return False

            # Se ainda tem waves para spawnar neste path, não terminou
            if self.current_wave_index_by_path.get(path_idx, 0) < len(waves):
                # Verifica se já spawnou todos da wave atual
                wave_data = self.current_wave_data_by_path.get(path_idx)
                if wave_data:
                    wave_size = wave_data.get("wave_size", 10)
                    if self.enemies_spawned_by_path.get(path_idx, 0) < wave_size:
                        return False
                else:
                    # Se não tem wave_data mas ainda tem índices, significa que não começou
                    return False

        return True