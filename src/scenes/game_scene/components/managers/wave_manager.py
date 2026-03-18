# src/scenes/game_scene/components/managers/wave_manager.py

import random
from src.entities.pokemon import Pokemon


class GameWaveManager:
    """Gerencia as waves durante o jogo - AGORA É A ÚNICA FONTE DE VERDADE PARA INIMIGOS"""

    def __init__(self, phase_loader):
        self.phase_loader = phase_loader
        self.waves_data = []  # Lista de waves
        self.current_wave_index = 0
        self.wave_in_progress = False
        self.wave_timer = 0
        self.spawn_timer = 0
        self.enemies_spawned = 0
        self.enemies_remaining = 0
        self.current_wave_data = None

        # Lista principal de inimigos
        self.active_enemies = []

        # NOVO: Referência para os itens alvo (será setada pelo GameScene)
        self.target_items = []

        # Carrega os dados
        self._load_waves_data()

    def _load_waves_data(self):
        """Carrega os dados das waves do phase_loader"""
        raw_data = self.phase_loader.get_waves_data()

        if isinstance(raw_data, list):
            self.waves_data = raw_data
            print(f"[WaveManager] Waves carregadas: {len(self.waves_data)}")
        else:
            self.waves_data = []
            print("⚠️ raw_data não é uma lista, criando lista vazia")

    def start_next_wave(self):
        """Inicia a próxima wave"""
        if self.current_wave_index >= len(self.waves_data):
            print("[WaveManager] Todas as waves concluídas!")
            return False

        self.current_wave_data = self.waves_data[self.current_wave_index]

        # Configura a wave atual
        self.wave_in_progress = True
        self.wave_timer = self.current_wave_data.get("initial_delay", 2.0)
        self.spawn_timer = 0
        self.enemies_spawned = 0
        # IMPORTANTE: Não resetamos enemies_remaining aqui, pois ele será incrementado conforme spawnamos
        self.enemies_remaining = 0

        print(
            f"[WaveManager] Iniciando Wave {self.current_wave_index + 1}: {self.current_wave_data.get('name', 'Wave')}")
        return True

    def set_target_items(self, items):
        """Define a lista de itens alvo para os inimigos"""
        self.target_items = items
        print(f"[WaveManager] Itens alvo vinculados: {len(items)} itens")

    def update(self, dt, path_points, screen_manager):
        """
        Atualiza o estado da wave e todos os inimigos
        Retorna uma lista de inimigos que chegaram ao fim (para processamento)
        """
        enemies_at_end = []  # Inimigos que chegaram ao fim do caminho nesta atualização

        # ===== 1. Atualiza todos os inimigos ativos =====
        for enemy in self.active_enemies[:]:  # Itera sobre uma cópia para poder remover com segurança
            # MODIFICADO: Passa os itens alvo para o inimigo
            enemy.update(dt, items=self.target_items)  # Passa os itens aqui!

            # Verifica se o inimigo chegou ao fim do caminho
            if hasattr(enemy, 'path') and enemy.path and enemy.path_index >= len(enemy.path):
                enemies_at_end.append(enemy)
                # Remove da lista ativa
                self.active_enemies.remove(enemy)
                self.enemies_remaining -= 1
                print(f"[WaveManager] {enemy.name} chegou ao fim! Restam {self.enemies_remaining} inimigos")

        # ===== 2. Spawna novos inimigos (se a wave estiver em andamento) =====
        if self.wave_in_progress and self.current_wave_index < len(self.waves_data):
            wave_data = self.current_wave_data or self.waves_data[self.current_wave_index]

            # Delay inicial da wave
            if self.wave_timer > 0:
                self.wave_timer -= dt
                if self.wave_timer <= 0:
                    print(f"[WaveManager] Delay inicial terminado! Iniciando spawns...")
                return enemies_at_end  # Retorna apenas os que chegaram ao fim

            # Spawn de inimigos
            if self.enemies_spawned < wave_data.get("wave_size", 10):
                self.spawn_timer -= dt

                if self.spawn_timer <= 0:
                    # Cria um inimigo
                    enemy = self._create_enemy(wave_data, path_points, screen_manager)

                    if enemy:
                        # Adiciona à lista ativa
                        self.active_enemies.append(enemy)
                        self.enemies_spawned += 1
                        self.enemies_remaining += 1

                        print(f"[WaveManager] Spawnado {enemy.name} ({self.enemies_spawned}/{wave_data.get('wave_size', 10)})")

                        # Reseta timer de spawn
                        self.spawn_timer = wave_data.get("spawn_interval", 3.0)

            # ===== 3. Verifica se a wave terminou de spawnar =====
            if self.enemies_spawned >= wave_data.get("wave_size", 10):
                # Se já spawnou todos e não há mais inimigos vivos, a wave terminou
                if self.enemies_remaining <= 0:
                    self._end_current_wave()
                else:
                    # Ainda tem inimigos vivos, mas não spawna mais
                    if self.wave_in_progress:
                        # Só printa ocasionalmente para não floodar o console
                        if random.random() < 0.01:  # 1% de chance a cada frame
                            print(f"[WaveManager] Aguardando eliminar {self.enemies_remaining} inimigos...")

        return enemies_at_end

    def _create_enemy(self, wave_data, path_points, screen_manager):
        """Cria um inimigo baseado nos dados da wave"""
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

        # Cria o Pokémon inimigo
        pokemon = Pokemon(
            start_x, start_y,
            enemy_data["pokemon_id"],
            level=level,
            is_wild=True
        )

        pokemon.screen_manager = screen_manager

        # Configura para seguir o path
        pokemon.path = path_points
        pokemon.speed = 0.8
        pokemon.path_index = 0

        # Define direção inicial
        if len(path_points) > 1:
            dx = path_points[1][0] - path_points[0][0]
            dy = path_points[1][1] - path_points[0][1]

            if abs(dx) > abs(dy):
                pokemon.current_direction = "right" if dx > 0 else "left"
            else:
                pokemon.current_direction = "down" if dy > 0 else "up"

        return pokemon

    def remove_enemy(self, enemy):
        """
        Remove um inimigo da lista ativa (quando capturado ou morto)
        Retorna True se removeu com sucesso
        """
        if enemy in self.active_enemies:
            self.active_enemies.remove(enemy)
            self.enemies_remaining -= 1
            print(f"[WaveManager] Inimigo {enemy.name} removido! Restam {self.enemies_remaining}")
            return True
        else:
            print(f"[WaveManager] ERRO: Tentou remover {enemy.name} mas ele não está na lista!")
            return False

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

    def _end_current_wave(self):
        """Finaliza a wave atual"""
        if not self.current_wave_data:
            return

        print(f"\n[WaveManager] Wave {self.current_wave_index + 1} concluída!")

        # Verifica se a wave repete
        if self.current_wave_data.get("repeat_wave", False):
            repeat_count = self.current_wave_data.get("repeat_count", 1)

            if repeat_count > 1:
                # Decrementa contador e reinicia a mesma wave
                self.current_wave_data["repeat_count"] = repeat_count - 1
                self.wave_in_progress = True
                self.enemies_spawned = 0
                self.enemies_remaining = 0
                self.wave_timer = self.current_wave_data.get("initial_delay", 2.0)
                print(f"[WaveManager] Repetindo wave... Restam {repeat_count - 1} repetições")
                return

        # Passa para próxima wave
        self.wave_in_progress = False
        self.current_wave_index += 1
        self.current_wave_data = None

        if self.current_wave_index < len(self.waves_data):
            print(f"[WaveManager] Próxima wave disponível. Aguardando início...")
        else:
            print(f"[WaveManager] 🏆 TODAS AS WAVES CONCLUÍDAS!")

    def get_current_wave_info(self):
        """Retorna informações da wave atual para UI"""
        if self.current_wave_index >= len(self.waves_data):
            return {
                "name": "Fim",
                "index": self.current_wave_index,
                "total": len(self.waves_data),
                "enemies_remaining": 0,
                "enemies_spawned": self.enemies_spawned,
                "enemies_total": 0,
                "progress": 1.0
            }

        wave_data = self.waves_data[self.current_wave_index]
        total_enemies = wave_data.get("wave_size", 10)

        return {
            "name": wave_data.get("name", f"Wave {self.current_wave_index + 1}"),
            "index": self.current_wave_index + 1,
            "total": len(self.waves_data),
            "enemies_remaining": self.enemies_remaining,
            "enemies_spawned": self.enemies_spawned,
            "enemies_total": total_enemies,
            "progress": self.enemies_spawned / total_enemies if total_enemies > 0 else 0
        }

    def has_more_waves(self):
        """Verifica se ainda existem waves"""
        return self.current_wave_index < len(self.waves_data)

    def is_wave_completely_finished(self):
        """
        Verifica se a wave atual terminou completamente
        (não está mais em progresso E não há inimigos vivos)
        """
        return not self.wave_in_progress and self.enemies_remaining <= 0 < self.enemies_spawned