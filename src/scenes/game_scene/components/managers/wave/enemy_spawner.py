# src/managers/wave/enemy_spawner.py
import random
from typing import List, Dict, Optional
from dataclasses import dataclass

from src.managers.sounds.sound_manager import sound_manager, SoundEffect
from ui.toast_renderer import toast_battle


@dataclass
class WaveConfig:
    """Configuração de uma wave"""
    path_index: int
    wave_index: int
    enemies: List[dict]
    wave_size: int
    spawn_interval: float
    initial_delay: float
    has_boss: bool
    speed_multiplier: float
    min_level: int = 1
    max_level: int = 5
    repeat_wave: bool = False
    repeat_count: int = 1
    current_repeat: int = 0


class EnemySpawner:
    """
    Gerencia o spawn de inimigos em waves.
    Responsabilidade ÚNICA: criar inimigos no momento correto.
    """

    def __init__(self, phase_loader, wave_manager):
        self.wave_manager = wave_manager
        self.waves: Dict[int, List[WaveConfig]] = {}
        self.raw_waves_data = []

        # ===== ESTADO DE PAUSA =====
        self.paused = False

        # Estado por path
        self.current_wave_idx: Dict[int, int] = {}
        self.wave_active: Dict[int, bool] = {}
        self.wave_timer: Dict[int, float] = {}
        self.spawn_timer: Dict[int, float] = {}
        self.spawned_count: Dict[int, int] = {}

    def set_paused(self, paused: bool):
        """Define o estado de pausa do spawner"""
        self.paused = paused

    def initialize_waves(self, raw_data):
        """Inicializa as waves a partir dos dados brutos"""
        self.raw_waves_data = raw_data
        self._load_waves()

    def _load_waves(self):
        """Carrega configurações das waves"""
        self.waves.clear()

        for idx, wave_dict in enumerate(self.raw_waves_data):
            path_idx = wave_dict.get("path_index", 0)
            min_level = wave_dict.get("min_level", 1)
            max_level = wave_dict.get("max_level", 5)

            # Converte inimigos
            enemies = []
            for enemy_dict in wave_dict.get("enemies", []):
                enemies.append({
                    "pokemon_id": enemy_dict.get("pokemon_id", 1),
                    "percentage": enemy_dict.get("percentage", 100),
                    "level_min": enemy_dict.get("level_min", min_level),
                    "level_max": enemy_dict.get("level_max", max_level)
                })

            if not enemies:
                enemies = [{"pokemon_id": 1, "percentage": 100, "level_min": min_level, "level_max": max_level}]

            wave = WaveConfig(
                path_index=path_idx,
                wave_index=idx,
                enemies=enemies,
                wave_size=wave_dict.get("wave_size", 10),
                spawn_interval=wave_dict.get("spawn_interval", 3.0),
                initial_delay=wave_dict.get("initial_delay", 2.0),
                has_boss=wave_dict.get("has_boss", True),
                speed_multiplier=wave_dict.get("speed_multiplier", 1.0),
                min_level=min_level,
                max_level=max_level,
                repeat_wave=wave_dict.get("repeat_wave", False),
                repeat_count=wave_dict.get("repeat_count", 1)
            )

            if path_idx not in self.waves:
                self.waves[path_idx] = []
            self.waves[path_idx].append(wave)

            print(
                f"[Spawner] Carregada wave {idx} para path {path_idx}: {wave.wave_size} inimigos, boss={wave.has_boss}")

    def start_all_waves(self) -> bool:
        """Inicia todas as waves de todos os paths"""
        started = False
        for path_idx in self.waves.keys():
            if self._start_wave_for_path(path_idx):
                started = True
        return started

    def _start_wave_for_path(self, path_idx: int) -> bool:
        """Inicia a wave atual para um path"""
        waves = self.waves.get(path_idx, [])
        wave_idx = self.current_wave_idx.get(path_idx, 0)

        if wave_idx >= len(waves):
            return False

        wave_data = waves[wave_idx]

        self.wave_active[path_idx] = True
        self.wave_timer[path_idx] = wave_data.initial_delay
        self.spawn_timer[path_idx] = 0
        self.spawned_count[path_idx] = 0

        print(f"[WaveSpawner] Path {path_idx}: Iniciando wave {wave_idx + 1} com {wave_data.wave_size} inimigos")
        return True

    def has_more_waves(self) -> bool:
        """Verifica se ainda existem waves pendentes"""
        for path_idx, waves in self.waves.items():
            current = self.current_wave_idx.get(path_idx, 0)
            if current < len(waves):
                return True
        return False

    def has_active_waves(self) -> bool:
        """Verifica se alguma wave ainda está ativa (spawnando)"""
        for path_idx, active in self.wave_active.items():
            if active:
                return True
        return False

    def get_current_wave_info(self, active_enemies_count: int) -> dict:
        """Retorna informações sobre a wave atual"""
        total_spawned = sum(self.spawned_count.values())
        total_enemies = sum(w.wave_size for waves in self.waves.values() for w in waves)
        active_paths = sum(1 for active in self.wave_active.values() if active)

        if active_paths == 0:
            all_completed = all(
                self.current_wave_idx.get(p, 0) >= len(w)
                for p, w in self.waves.items()
            )
            if all_completed:
                return {
                    "name": "Fase Completa!",
                    "index": "Final",
                    "total": len(self.waves),
                    "enemies_remaining": active_enemies_count,
                    "enemies_spawned": total_spawned,
                    "enemies_total": total_enemies,
                    "progress": 1.0,
                    "active_paths": 0
                }
            else:
                return {
                    "name": "Aguardando...",
                    "index": 1,
                    "total": len(self.waves),
                    "enemies_remaining": active_enemies_count,
                    "enemies_spawned": total_spawned,
                    "enemies_total": total_enemies,
                    "progress": total_spawned / total_enemies if total_enemies > 0 else 0,
                    "active_paths": 0
                }

        return {
            "name": f"{active_paths} wave(s) ativa(s)",
            "index": "Múltiplas",
            "total": len(self.waves),
            "enemies_remaining": active_enemies_count,
            "enemies_spawned": total_spawned,
            "enemies_total": total_enemies,
            "progress": total_spawned / total_enemies if total_enemies > 0 else 0,
            "active_paths": active_paths
        }

    def update(self, dt: float) -> List['Pokemon']:
        """
        Atualiza spawn de inimigos.
        Retorna lista de novos inimigos criados.
        """
        if self.paused:
            return []

        new_enemies = []

        for path_idx, wave_active in list(self.wave_active.items()):
            if not wave_active:
                continue

            waves = self.waves.get(path_idx, [])
            wave_idx = self.current_wave_idx.get(path_idx, 0)

            if wave_idx >= len(waves):
                self.wave_active[path_idx] = False
                continue

            wave = waves[wave_idx]
            path = self.wave_manager.path_tracker.get_path_by_index(path_idx)

            if not path:
                print(f"[Spawner] ERRO: Path {path_idx} não encontrado!")
                continue

            # Delay inicial da wave
            if self.wave_timer[path_idx] > 0:
                self.wave_timer[path_idx] -= dt
                continue

            # Spawn de inimigos
            spawned = self.spawned_count.get(path_idx, 0)

            if spawned < wave.wave_size:
                self.spawn_timer[path_idx] -= dt

                if self.spawn_timer[path_idx] <= 0:
                    # Cria novo inimigo
                    is_last = (spawned + 1) >= wave.wave_size
                    is_boss = is_last and wave.has_boss

                    enemy = self._create_enemy(wave, path, path_idx, is_boss)

                    if enemy:
                        print(f"[Spawner] Spawnado {enemy.name} Lv.{enemy.level} (BOSS={is_boss}) no path {path_idx}")
                        new_enemies.append(enemy)
                        self.spawned_count[path_idx] = spawned + 1
                        self.spawn_timer[path_idx] = wave.spawn_interval
                    else:
                        print(f"[Spawner] ERRO: Falha ao criar inimigo!")
                        self.spawn_timer[path_idx] = 0.5  # Tenta novamente em 0.5s
            else:
                # Wave terminou de spawnar
                self._advance_to_next_wave(path_idx)

        return new_enemies

    def _advance_to_next_wave(self, path_idx: int):
        """Avança para a próxima wave"""
        current_idx = self.current_wave_idx.get(path_idx, 0)
        waves = self.waves.get(path_idx, [])

        if current_idx >= len(waves):
            return

        wave_data = waves[current_idx]

        # Verifica se deve repetir
        if wave_data.repeat_wave:
            wave_data.current_repeat += 1

            if wave_data.repeat_count == 0 or wave_data.current_repeat < wave_data.repeat_count:
                # Reinicia a wave atual
                print(
                    f"[WaveSpawner] Path {path_idx}: repetindo wave {current_idx + 1} (repetição {wave_data.current_repeat})")
                self._start_wave_for_path(path_idx)
                return

        # Avança para próxima wave
        if current_idx + 1 < len(waves):
            self.current_wave_idx[path_idx] = current_idx + 1
            print(f"[WaveSpawner] Path {path_idx}: avançando para wave {current_idx + 2}")
            self._start_wave_for_path(path_idx)
        else:
            self.wave_active[path_idx] = False
            self.current_wave_idx[path_idx] = current_idx + 1
            print(f"[WaveSpawner] Path {path_idx}: todas as waves concluídas")

    def _create_enemy(self, wave: WaveConfig, path, path_idx: int, is_boss: bool) -> Optional['Pokemon']:
        """Cria um novo inimigo"""
        from src.entities.pokemon import Pokemon

        # Escolhe inimigo baseado em porcentagem
        enemy_config = self._choose_enemy(wave.enemies)
        if not enemy_config:
            print(f"[Spawner] ERRO: Nenhum inimigo configurado!")
            return None

        level = random.randint(
            enemy_config.get("level_min", wave.min_level),
            enemy_config.get("level_max", wave.max_level)
        )

        # Garante que o ponto de início existe
        if not path.start_point:
            print(f"[Spawner] ERRO: Path {path_idx} não tem start_point!")
            return None

        start_x, start_y = path.start_point
        print(f"[Spawner] Criando inimigo em ({start_x}, {start_y})")

        pokemon = Pokemon(
            start_x, start_y,
            enemy_config.get("pokemon_id", 1),
            level=level,
            is_wild=True,
            shiny=random.random() < 0.001,
            is_boss=is_boss
        )

        # Configura screen_manager e camera
        if self.wave_manager.game_scene and hasattr(self.wave_manager.game_scene, 'screen_manager'):
            pokemon.screen_manager = self.wave_manager.game_scene.screen_manager
            pokemon.camera = self.wave_manager.game_scene.camera

        # Configura path
        success = self.wave_manager.path_tracker.assign_path(pokemon, path_idx, start_at_begin=True)
        if not success:
            print(f"[Spawner] ERRO: Falha ao atribuir path para {pokemon.name}")
            return None

        pokemon.move_speed = pokemon.base_move_speed * wave.speed_multiplier

        # Marca que acabou de nascer (evita detecção de chegada imediata)
        pokemon._just_spawned = True
        pokemon._spawn_timer = 0.5

        # Inicializa controle de distância percorrida
        pokemon._distance_traveled = 0.0
        pokemon._last_pos = (pokemon.x, pokemon.y)

        # Garante que o inimigo está vivo
        pokemon.current_hp = pokemon.max_hp
        if pokemon.is_shiny:
            sound_manager.play_effect(SoundEffect.SHINY)
            toast_battle(f"{pokemon.name} shiny apareceu!)", duration=4.0, pokemon=pokemon, portrait="angry")

        return pokemon

    def _choose_enemy(self, enemies: List[dict]) -> Optional[dict]:
        """Escolhe um inimigo baseado nas porcentagens"""
        if not enemies:
            return None

        total = sum(e.get("percentage", 100) for e in enemies)
        if total <= 0:
            return random.choice(enemies)

        roll = random.uniform(0, total)
        cumulative = 0

        for enemy in enemies:
            cumulative += enemy.get("percentage", 100)
            if roll <= cumulative:
                return enemy

        return enemies[-1]