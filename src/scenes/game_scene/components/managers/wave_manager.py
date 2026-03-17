# src/scenes/game_scene/components/managers/wave_manager.py

import random
from src.entities.pokemon import Pokemon


class GameWaveManager:
    """Gerencia as waves durante o jogo"""

    def __init__(self, phase_loader):
        self.phase_loader = phase_loader
        self.waves_data = []  # Lista de waves
        self.current_wave_index = 0
        self.wave_in_progress = False
        self.wave_timer = 0
        self.spawn_timer = 0
        self.enemies_spawned = 0
        self.enemies_remaining = 0
        self.current_wave_enemies = []  # Inimigos vivos da wave atual

        # Carrega os dados
        self._load_waves_data()

        # DEBUG: Mostra o que foi carregado
        print(f"[WaveManager] Dados carregados: {self.waves_data}")
        if self.waves_data:
            print(f"[WaveManager] Primeira wave: {self.waves_data[0] if len(self.waves_data) > 0 else 'None'}")

    def _load_waves_data(self):
        """Carrega os dados das waves do phase_loader"""
        raw_data = self.phase_loader.get_waves_data()

        print(f"\n=== WAVE MANAGER DEBUG ===")
        print(f"raw_data recebido: {raw_data}")
        print(f"Tipo: {type(raw_data)}")
        print(f"É lista? {isinstance(raw_data, list)}")

        if isinstance(raw_data, list):
            self.waves_data = raw_data
            print(f"Waves carregadas: {len(self.waves_data)}")
            if len(self.waves_data) > 0:
                print(f"Primeira wave: {self.waves_data[0]}")
        else:
            self.waves_data = []
            print("⚠️ raw_data não é uma lista, criando lista vazia")

        print("==========================\n")

    def start_next_wave(self):
        """Inicia a próxima wave"""
        if self.current_wave_index >= len(self.waves_data):
            print("Todas as waves concluídas!")
            return False

        wave_data = self.waves_data[self.current_wave_index]

        # DEBUG
        print(f"[WaveManager] Iniciando wave {self.current_wave_index + 1}")
        print(f"[WaveManager] Dados da wave: {wave_data}")

        # Configura a wave atual
        self.wave_in_progress = True
        self.wave_timer = wave_data.get("initial_delay", 2.0)
        self.spawn_timer = 0
        self.enemies_spawned = 0
        self.enemies_remaining = wave_data.get("wave_size", 10)

        print(f"Iniciando Wave {self.current_wave_index + 1}: {wave_data.get('name', 'Wave')}")
        return True

    def update(self, dt, path_points, on_enemy_spawn, screen_manager):
        """
        Atualiza o estado da wave
        dt: delta time
        path_points: lista de pontos do path para posicionar inimigos
        on_enemy_spawn: callback para criar inimigo no jogo
        """
        if not self.wave_in_progress or self.current_wave_index >= len(self.waves_data):
            return

        wave_data = self.waves_data[self.current_wave_index]

        # Delay inicial da wave
        if self.wave_timer > 0:
            self.wave_timer -= dt
            if self.wave_timer <= 0:
                print(f"[WAVE] Delay inicial terminado! Iniciando spawns...")
            return

        # Spawn de inimigos
        if self.enemies_spawned < wave_data.get("wave_size", 10):
            self.spawn_timer -= dt

            if self.spawn_timer <= 0:
                print(f"\n[WAVE] Spawnando inimigo {self.enemies_spawned + 1}/{wave_data.get('wave_size', 10)}")

                # Cria um inimigo
                enemy_data = self._get_random_enemy(wave_data)
                print(f"  - Enemy data: {enemy_data}")

                if enemy_data and path_points:
                    print(f"  - Path points disponíveis: {len(path_points)}")
                    print(f"  - Primeiro ponto: {path_points[0]}")
                    print(f"  - Último ponto: {path_points[-1]}")

                    # Valida se path_points tem pelo menos 2 pontos
                    if len(path_points) < 2:
                        print(f"  - ERRO: Path precisa ter pelo menos 2 pontos!")
                        self.spawn_timer = wave_data.get("spawn_interval", 3.0)
                        return

                    # USA OS PONTOS EXATOS DO PATH - sem conversão adicional
                    start_x, start_y = path_points[0]

                    # Nível aleatório entre min e max
                    level = random.randint(
                        wave_data.get("min_level", 1),
                        wave_data.get("max_level", 5)
                    )



                    # Cria o Pokémon inimigo
                    pokemon = Pokemon(
                        start_x,  # X inicial (exatamente como está no path)
                        start_y,  # Y inicial (exatamente como está no path)
                        enemy_data["pokemon_id"],
                        level=level,
                        is_wild=True
                    )

                    pokemon.screen_manager = screen_manager

                    # Configura para seguir o path
                    pokemon.path = path_points  # Usa os pontos exatos
                    pokemon.speed = 0.8
                    pokemon.path_index = 0

                    # Define a direção inicial baseada no próximo ponto
                    if len(path_points) > 1:
                        dx = path_points[1][0] - path_points[0][0]
                        dy = path_points[1][1] - path_points[0][1]

                        if abs(dx) > abs(dy):
                            pokemon.current_direction = "right" if dx > 0 else "left"
                        else:
                            pokemon.current_direction = "down" if dy > 0 else "up"

                        print(f"  - Direção inicial: {pokemon.current_direction}")

                    print(f"  - Pokémon criado: {pokemon.name} Lv.{pokemon.level}")
                    print(f"  - Posição inicial: ({pokemon.x:.1f}, {pokemon.y:.1f})")
                    print(f"  - Path points: {len(pokemon.path)}")
                    print(f"  - Primeiro ponto do path: {pokemon.path[0]}")
                    print(f"  - Último ponto do path: {pokemon.path[-1]}")

                    # Callback para adicionar ao jogo
                    on_enemy_spawn(pokemon)

                    self.enemies_spawned += 1
                    self.enemies_remaining += 1
                    self.spawn_timer = wave_data.get("spawn_interval", 3.0)
                else:
                    print(f"  - ERRO: enemy_data ou path_points inválido!")

        # Verifica se a wave terminou
        if self.enemies_spawned >= wave_data.get("wave_size", 10) and self.enemies_remaining <= 0:
            self._end_current_wave()

    def enemy_destroyed(self):
        """Chamado quando um inimigo é destruído"""
        self.enemies_remaining -= 1
        print(f"[WAVE] Inimigo destruído! Restam {self.enemies_remaining} inimigos vivos")

    def _get_random_enemy(self, wave_data):
        """Retorna um inimigo aleatório baseado nas porcentagens"""
        enemies = wave_data.get("enemies", [])
        if not enemies:
            return None

        # Normaliza porcentagens
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
        wave_data = self.waves_data[self.current_wave_index]
        print(f"\n[WAVE] Wave {self.current_wave_index + 1} concluída!")

        # Verifica se a wave repete
        if wave_data.get("repeat_wave", False):
            repeat_count = wave_data.get("repeat_count", 1)

            if repeat_count > 1:
                # Decrementa contador e reinicia a mesma wave
                wave_data["repeat_count"] = repeat_count - 1
                self.enemies_spawned = 0
                self.enemies_remaining = 0
                self.wave_timer = wave_data.get("initial_delay", 2.0)
                print(f"[WAVE] Repetindo wave... Restam {repeat_count - 1} repetições")
                return

        # Passa para próxima wave
        self.wave_in_progress = False
        self.current_wave_index += 1

        # Se ainda tem waves, prepara próxima
        if self.current_wave_index < len(self.waves_data):
            next_wave = self.waves_data[self.current_wave_index]
            print(f"[WAVE] Próxima wave: {next_wave.get('name', 'Wave')}")
            print(f"[WAVE] Aguardando início...")
        else:
            print(f"[WAVE] TODAS AS WAVES CONCLUÍDAS!")

    def get_current_wave_info(self):
        """Retorna informações da wave atual para UI"""
        if self.current_wave_index >= len(self.waves_data):
            return {
                "name": "Fim",
                "index": self.current_wave_index,
                "total": len(self.waves_data),
                "enemies_remaining": 0,
                "enemies_total": 0,
                "progress": 1.0
            }

        wave_data = self.waves_data[self.current_wave_index]
        return {
            "name": wave_data.get("name", f"Wave {self.current_wave_index + 1}"),
            "index": self.current_wave_index + 1,
            "total": len(self.waves_data),
            "enemies_remaining": self.enemies_remaining,
            "enemies_spawned": self.enemies_spawned,
            "enemies_total": wave_data.get("wave_size", 10),
            "progress": self.enemies_spawned / wave_data.get("wave_size", 10) if wave_data.get("wave_size",
                                                                                               10) > 0 else 0
        }

    def has_more_waves(self):
        """Verifica se ainda existem waves"""
        return self.current_wave_index < len(self.waves_data)