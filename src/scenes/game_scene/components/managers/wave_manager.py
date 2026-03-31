# src/scenes/game_scene/components/managers/wave_manager.py
import random
import math
from typing import List, Dict, Optional, Tuple, Set
from enum import Enum
from dataclasses import dataclass, field

from src.battle.effects import StatusType
from src.entities.pokemon import Pokemon
from src.managers.sound_manager import sound_manager, SoundEffect


class EnemyState(Enum):
    """Estado do inimigo no path"""
    MOVING_FORWARD = "moving_forward"  # Indo do início ao fim
    MOVING_BACKWARD = "moving_backward"  # Voltando do fim ao início
    RETURNING_TO_START = "returning_to_start"  # Voltando com item (boss)


@dataclass
class PathData:
    """Dados do path"""
    index: int
    points: List[Tuple[float, float]]
    start_point: Tuple[float, float]
    end_point: Tuple[float, float]
    length: float


@dataclass
class WaveEnemy:
    """Configuração de um inimigo na wave"""
    pokemon_id: int
    percentage: int = 100
    level_min: int = 1
    level_max: int = 5


@dataclass
class WaveData:
    """Dados de uma wave"""
    path_index: int
    wave_index: int
    enemies: List[WaveEnemy]
    wave_size: int = 10
    spawn_interval: float = 3.0
    initial_delay: float = 2.0
    has_boss: bool = True
    speed_multiplier: float = 1.0
    min_level: int = 1
    max_level: int = 5
    repeat_wave: bool = False  # Se deve repetir a wave
    repeat_count: int = 1  # Número de repetições (0 = infinito)
    current_repeat: int = 0  # Contador de repetições atuais


class GameWaveManager:
    """
    Gerenciador de waves refatorado com lógica clara:
    - Inimigos comuns: vão do início ao fim, somem no fim
    - Inimigos comuns com item: podem voltar ao início
    - Boss: vai e volta, não some
    - Boss com item: decide direção baseado na distância
    """

    # Constantes
    PROXIMITY_THRESHOLD = 15.0  # Distância para considerar "chegou"

    def __init__(self, phase_loader):
        self.phase_loader = phase_loader

        # Dados de waves
        self.waves: Dict[int, List[WaveData]] = {}  # path_index -> lista de waves
        self.active_enemies: List[Pokemon] = []

        # Estado por path
        self.paths: Dict[int, PathData] = {}
        self.current_wave_idx: Dict[int, int] = {}  # path_index -> wave_atual
        self.wave_active: Dict[int, bool] = {}  # path_index -> wave_ativa
        self.wave_timer: Dict[int, float] = {}  # timer para início da wave
        self.spawn_timer: Dict[int, float] = {}  # timer entre spawns
        self.spawned_count: Dict[int, int] = {}  # inimigos spawnados
        self.alive_count: Dict[int, int] = {}  # inimigos vivos no path

        # Referências
        self.target_items: List = []
        self.game_scene = None
        self.paused = False

        # Cache
        self._path_points_cache: Dict[int, List[Tuple[float, float]]] = {}

        # Acumuladores
        self.total_gold_earned = 0
        self.gold_per_defeat = 10

        # Carrega dados
        self._load_waves_data()

    def _load_waves_data(self):
        """Carrega e organiza os dados das waves"""
        raw_data = self.phase_loader.get_waves_data()

        if not raw_data:
            print("[WaveManager] Nenhum dado de waves encontrado")
            return

        self.waves.clear()

        for idx, wave_dict in enumerate(raw_data):
            # Extrai dados básicos
            path_index = wave_dict.get("path_index", 0)
            wave_size = wave_dict.get("wave_size", 10)
            spawn_interval = wave_dict.get("spawn_interval", 3.0)
            initial_delay = wave_dict.get("initial_delay", 2.0)
            has_boss = wave_dict.get("has_boss", True)
            speed_multiplier = wave_dict.get("speed_multiplier", 1.0)
            min_level = wave_dict.get("min_level", 1)
            max_level = wave_dict.get("max_level", 5)
            repeat_wave = wave_dict.get("repeat_wave", False)
            repeat_count = wave_dict.get("repeat_count", 1)

            # Configura inimigos
            enemies = []
            for enemy_dict in wave_dict.get("enemies", []):
                enemies.append(WaveEnemy(
                    pokemon_id=enemy_dict.get("pokemon_id", 1),
                    percentage=enemy_dict.get("percentage", 100),
                    level_min=enemy_dict.get("level_min", min_level),
                    level_max=enemy_dict.get("level_max", max_level)
                ))

            # Se não tem inimigos configurados, usa um padrão
            if not enemies:
                enemies = [WaveEnemy(pokemon_id=1, percentage=100)]

            wave_data = WaveData(
                path_index=path_index,
                wave_index=idx,
                enemies=enemies,
                wave_size=wave_size,
                spawn_interval=spawn_interval,
                initial_delay=initial_delay,
                has_boss=has_boss,
                speed_multiplier=speed_multiplier,
                min_level=min_level,
                max_level=max_level,
                repeat_wave=repeat_wave,
                repeat_count=repeat_count,
                current_repeat=0
            )

            if path_index not in self.waves:
                self.waves[path_index] = []
            self.waves[path_index].append(wave_data)

        # Inicializa estado por path
        for path_idx in self.waves.keys():
            self.current_wave_idx[path_idx] = 0
            self.wave_active[path_idx] = False
            self.wave_timer[path_idx] = 0
            self.spawn_timer[path_idx] = 0
            self.spawned_count[path_idx] = 0
            self.alive_count[path_idx] = 0

        print(f"[WaveManager] Carregadas {len(raw_data)} waves para {len(self.waves)} paths")

    def set_paths_data(self, path_renderer):
        """Define os dados dos paths"""
        self.paths.clear()
        self._path_points_cache.clear()

        for i, path in enumerate(path_renderer.paths):
            points = path.get_path_points()
            if len(points) >= 2:
                self.paths[i] = PathData(
                    index=i,
                    points=points,
                    start_point=points[0],
                    end_point=points[-1],
                    length=self._calculate_path_length(points)
                )
                self._path_points_cache[i] = points

        print(f"[WaveManager] Carregados {len(self.paths)} paths")

    def _calculate_path_length(self, points: List[Tuple[float, float]]) -> float:
        """Calcula o comprimento total do path"""
        length = 0
        for i in range(len(points) - 1):
            dx = points[i + 1][0] - points[i][0]
            dy = points[i + 1][1] - points[i][1]
            length += math.sqrt(dx * dx + dy * dy)
        return length

    def set_target_items(self, items):
        """Vincula a lista de itens alvo"""
        self.target_items = items
        print(f"[WaveManager] Vinculados {len(items)} itens alvo")

    def start_all_waves(self):
        """Inicia todas as waves de todos os paths"""
        started = False
        for path_idx in self.paths.keys():
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

        # Se esta é a primeira vez que a wave está sendo iniciada, reseta o contador de repetição
        # (Isso acontece quando avançamos para uma nova wave)
        if wave_data.current_repeat == 0:
            # Já está no estado inicial
            pass

        self.wave_active[path_idx] = True
        self.wave_timer[path_idx] = wave_data.initial_delay
        self.spawn_timer[path_idx] = 0
        self.spawned_count[path_idx] = 0
        self.alive_count[path_idx] = 0

        print(f"[WaveManager] Path {path_idx}: Iniciando wave {wave_idx + 1}" +
              (f" (repetição {wave_data.current_repeat + 1})" if wave_data.current_repeat > 0 else ""))
        return True

    def update(self, dt: float, path_points_by_index: dict, screen_manager) -> List[Pokemon]:
        """
        Atualiza o sistema de waves
        Retorna lista de inimigos que chegaram ao fim (para processamento)
        """
        if self.paused:
            return []

        enemies_at_end = []
        enemies_to_remove = []

        # ===== 1. ATUALIZAR INIMIGOS EXISTENTES =====
        for enemy in self.active_enemies[:]:
            # IMPORTANTE: NÃO chamar enemy.update() aqui!
            # O movimento é gerenciado inteiramente pelo WaveManager

            # Atualiza posição e estado
            self._update_enemy_movement(enemy, dt)

            # Atualiza animação (não chama update completo)
            self._update_enemy_animation(enemy, dt)

            # Verifica captura de item (mas não chama enemy.update)
            self._check_item_capture(enemy)

            # Atualiza o item carregado se houver
            if enemy.is_carrying:
                enemy.is_carrying.update_capture(dt)

            # Verifica morte
            if not enemy.is_alive():
                enemies_to_remove.append(enemy)
                continue

            # Verifica se chegou ao destino
            arrived, is_end = self._check_arrival(enemy)

            if arrived:
                result = self._handle_enemy_arrival(enemy, is_end)
                if result == "remove":
                    enemies_to_remove.append(enemy)
                elif result == "return":
                    # Já está retornando, não adiciona
                    pass
                elif result == "end":
                    enemies_at_end.append(enemy)

        # ===== 2. PROCESSAR REMOÇÕES =====
        for enemy in enemies_to_remove:
            self._remove_enemy(enemy)

        # ===== 3. SPAWNAR NOVOS INIMIGOS =====
        self._process_spawning(dt)

        # ===== 4. ATUALIZAR CONTAGEM DE VIVOS =====
        self._update_alive_counts()

        return enemies_at_end

    def _update_enemy_animation(self, enemy: Pokemon, dt: float):
        """Atualiza apenas a animação do inimigo"""
        enemy.animation_timer += dt
        if enemy.animation_timer >= enemy.animation_speed:
            enemy.animation_timer = 0
            if enemy.inmap_frames and enemy.current_direction in enemy.inmap_frames:
                frames_list = enemy.inmap_frames[enemy.current_direction]
                if frames_list:
                    enemy.current_frame = (enemy.current_frame + 1) % len(frames_list)
                    enemy.sprite = frames_list[enemy.current_frame]

    def _update_enemy_movement(self, enemy: Pokemon, dt: float):
        """Atualiza o movimento do inimigo ao longo do path - com verificação de stun"""

        # ===== VERIFICA STUN DA PARALISIA =====
        if hasattr(enemy, 'effect_manager') and enemy.effect_manager:
            status = enemy.effect_manager.get_status(enemy)
            if status and status.type == StatusType.PARALYSIS:
                # Atualiza o estado de paralisia
                is_stunned = status.update_paralysis(dt)
                if is_stunned:
                    # Está atordoado - não se move neste frame
                    return  # Não move

        # ===== MOVIMENTO NORMAL =====
        if not enemy.path or len(enemy.path) == 0:
            return

        if enemy.path_index >= len(enemy.path):
            return

        target_x, target_y = enemy.path[enemy.path_index]
        dx = target_x - enemy.x
        dy = target_y - enemy.y
        distance = math.sqrt(dx * dx + dy * dy)
        move_distance = enemy.move_speed * dt * 60

        if distance <= move_distance:
            enemy.x, enemy.y = target_x, target_y
            enemy.path_index += 1
            enemy.rect.x, enemy.rect.y = enemy.x, enemy.y

            if enemy.is_boss:
                print(
                    f"[BOSS] {enemy.name} chegou ao ponto {enemy.path_index - 1}, indo para {enemy.path_index}/{len(enemy.path)}")
        else:
            move_x = (dx / distance) * move_distance
            move_y = (dy / distance) * move_distance
            enemy.x += move_x
            enemy.y += move_y
            enemy.rect.x, enemy.rect.y = enemy.x, enemy.y

            if abs(dx) > abs(dy):
                enemy.current_direction = "right" if dx > 0 else "left"
            else:
                enemy.current_direction = "down" if dy > 0 else "up"

    def _check_item_capture(self, enemy: Pokemon):
        """Verifica se o inimigo capturou um item - CORRIGIDO"""
        if enemy.is_carrying or not self.target_items:
            return

        for item in self.target_items:
            if hasattr(item, 'is_protected') and item.is_protected and not item.carried_by:
                # Calcula a posição real do item no mundo
                if item.carried_by:
                    item_x = item.current_x
                    item_y = item.current_y
                else:
                    if item.was_carried:
                        item_x = item.current_x
                        item_y = item.current_y
                    else:
                        # Centraliza a posição do item para detecção de colisão
                        item_x = item.base_x + 12  # 12 = tile_size/2
                        item_y = item.base_y + 12  # 12 = tile_size/2

                dx = enemy.x - item_x
                dy = enemy.y - item_y
                distance_sq = dx * dx + dy * dy
                capture_range_sq = enemy.capture_range * enemy.capture_range

                if distance_sq < capture_range_sq:
                    # Captura o item
                    item.start_capture(enemy)
                    enemy.is_carrying = item

                    # Decide direção após capturar
                    self._decide_direction_after_capture(enemy)
                    break

    def _decide_direction_after_capture(self, enemy: Pokemon):
        """
        Decide a direção após capturar um item:
        - Comuns: voltam ao início se estiverem mais perto do início
        - Boss: calcula distância até início e fim
        """
        if not enemy.path:
            return

        # Obtém o path data
        path_idx = getattr(enemy, 'path_index_origin', 0)
        path_data = self.paths.get(path_idx)
        if not path_data:
            return

        # Calcula distâncias até início e fim
        start_point = path_data.start_point
        end_point = path_data.end_point

        dist_to_start = math.hypot(enemy.x - start_point[0], enemy.y - start_point[1])
        dist_to_end = math.hypot(enemy.x - end_point[0], enemy.y - end_point[1])

        if enemy.is_boss:
            # Boss: decide baseado na distância
            # Se estiver mais perto do fim, continua; senão, volta
            if dist_to_end <= dist_to_start:
                # Continua para o fim
                if enemy.path_index < len(enemy.path) - 1:
                    # Mantém direção atual
                    pass
            else:
                # Volta para o início
                self._reverse_path(enemy)
        else:
            # Comum: sempre volta ao início
            self._reverse_path(enemy)

    def _reverse_path(self, enemy: Pokemon):
        """Inverte a direção do path (para boss ou Pokémon com item)"""
        if not enemy.path:
            return

        # Salva o path original se necessário
        if not hasattr(enemy, 'original_path') or enemy.original_path is None:
            enemy.original_path = enemy.path.copy()

        # Inverte o path
        enemy.path = list(reversed(enemy.original_path.copy()))

        # Encontra o ponto mais próximo no novo path
        min_dist = float('inf')
        closest_idx = 0
        for i, point in enumerate(enemy.path):
            dist = math.hypot(enemy.x - point[0], enemy.y - point[1])
            if dist < min_dist:
                min_dist = dist
                closest_idx = i

        enemy.path_index = closest_idx

        # IMPORTANTE: Se encontrou o ponto com distância 0 (está exatamente nele)
        # avança para o próximo ponto para não ficar preso
        if min_dist < 0.1 and closest_idx < len(enemy.path) - 1:
            enemy.path_index = closest_idx + 1
            print(f"[BOSS] {enemy.name} estava exatamente no ponto {closest_idx}, avançando para {enemy.path_index}")

        # Marca estado
        enemy.is_returning_with_item = True
        print(f"[BOSS] {enemy.name} invertido - novo path_index={enemy.path_index}, path_length={len(enemy.path)}")

    # Adicione esta constante
    MIN_TRAVEL_DISTANCE = 15.0  # Distância mínima para considerar que realmente andou

    def _check_arrival(self, enemy: Pokemon) -> Tuple[bool, bool]:
        """
        Verifica se o inimigo chegou ao início ou fim do path
        Retorna: (chegou, é_fim)
        """
        if not enemy.path:
            return False, False

        threshold = self.PROXIMITY_THRESHOLD
        path_idx = getattr(enemy, 'path_index_origin', 0)
        path_data = self.paths.get(path_idx)

        if not path_data:
            return False, False

        # Para BOSS: sempre verifica início E fim
        if enemy.is_boss:
            # Verifica se acabou de inverter e está no ponto exato
            # Se o path_index for 0, ele está no início do path atual
            if enemy.path_index == 0:
                # Está no início do path atual (pode ser início original ou fim original)
                return False, False

            # Verifica chegada ao FIM do path ATUAL
            if enemy.path_index >= len(enemy.path) - 1:
                # Chegou ao último ponto
                dist_to_end = math.hypot(enemy.x - enemy.path[-1][0],
                                         enemy.y - enemy.path[-1][1])
                if dist_to_end < threshold:
                    return True, True  # Chegou ao FIM do path atual

            # Verifica chegada ao INÍCIO do path ATUAL (apenas se não for o primeiro ponto)
            if enemy.path_index > 0:
                dist_to_start = math.hypot(enemy.x - enemy.path[0][0],
                                           enemy.y - enemy.path[0][1])
                if dist_to_start < threshold:
                    return True, False  # Chegou ao INÍCIO do path atual

            return False, False

        # ===== PARA INIMIGOS NORMAIS (NÃO BOSS) =====

        # Se acabou de nascer (índice 0), NÃO considera chegada
        if enemy.path_index == 0:
            return False, False

        # Calcula distância percorrida desde o nascimento
        if not hasattr(enemy, '_distance_traveled'):
            enemy._distance_traveled = 0.0
            enemy._last_pos = (enemy.x, enemy.y)
        else:
            dx = enemy.x - enemy._last_pos[0]
            dy = enemy.y - enemy._last_pos[1]
            enemy._distance_traveled += math.sqrt(dx * dx + dy * dy)
            enemy._last_pos = (enemy.x, enemy.y)

        # Só considera chegada ao fim se percorreu distância mínima
        if enemy._distance_traveled < self.MIN_TRAVEL_DISTANCE:
            return False, False

        # Verifica chegada ao FIM
        dist_to_end = math.hypot(enemy.x - path_data.end_point[0],
                                 enemy.y - path_data.end_point[1])
        if dist_to_end < threshold:
            return True, True  # Chegou ao fim, vai ser removido

        return False, False

    def _handle_enemy_arrival(self, enemy: Pokemon, is_end: bool) -> str:
        """
        Processa chegada do inimigo
        Retorna:
            "remove" - remove o inimigo
            "return" - faz retornar (boss)
            "end" - chegou ao fim (processar item)
        """
        # ===== BOSS =====
        if enemy.is_boss:
            print(f"[BOSS] {enemy.name} chegou ao {'FIM' if is_end else 'INÍCIO'} do path")

            # Se está carregando item, processa o roubo (apenas quando chega ao FIM)
            if enemy.is_carrying and is_end:
                carried_item = enemy.is_carrying
                print(f"[BOSS] {enemy.name} roubou {carried_item.item_name}!")

                # Marca item como roubado
                carried_item.is_protected = False
                carried_item.is_stolen = True
                carried_item.carried_by = None

                if hasattr(self.game_scene, 'target_item_manager'):
                    self.game_scene.target_item_manager.mark_item_as_stolen(carried_item)

                enemy.is_carrying = None

            # INVERTE A DIREÇÃO DO BOSS (continua andando)
            # Só inverte se NÃO for o primeiro ponto após inversão
            if enemy.path_index >= len(enemy.path) - 1 or enemy.path_index == 0:
                self._reverse_boss_direction(enemy)

            return "return"

        # ===== INIMIGO COMUM =====
        if enemy.is_carrying:
            # Carregando item -> item é roubado (chegou ao fim)
            carried_item = enemy.is_carrying
            print(f"[WAVE] {enemy.name} chegou ao fim com {carried_item.item_name} - item será roubado!")
            carried_item.is_protected = False
            carried_item.is_stolen = True
            carried_item.carried_by = None

            if hasattr(self.game_scene, 'target_item_manager'):
                self.game_scene.target_item_manager.mark_item_as_stolen(carried_item)

            enemy.is_carrying = None
            enemy.is_returning_with_item = False
            return "remove"

        # Inimigo comum sem item sempre some ao chegar
        return "remove"

    def _reverse_boss_direction(self, enemy: Pokemon):
        """
        Inverte a direção do boss no path
        Mantém o boss andando continuamente
        """
        if not enemy.path or len(enemy.path) < 2:
            return

        # Salva o path original se necessário
        if not hasattr(enemy, 'original_path') or enemy.original_path is None:
            enemy.original_path = enemy.path.copy()

        # Cria o novo path invertido
        enemy.path = list(reversed(enemy.original_path.copy()))

        # IMPORTANTE: Não encontrar o ponto mais próximo!
        # Em vez disso, define o índice baseado na direção

        # Se está no fim do path atual, deve começar do início do path invertido
        if enemy.is_returning_with_item:
            # Já está invertido, começa do início
            enemy.path_index = 0
            # Ajusta posição para o primeiro ponto
            if len(enemy.path) > 0:
                enemy.x, enemy.y = enemy.path[0]
                enemy.rect.x, enemy.rect.y = enemy.x, enemy.y
        else:
            # Primeira inversão (chegou ao fim)
            # Vai para o início do path invertido (que é o fim original)
            enemy.path_index = 0
            # Ajusta posição para o primeiro ponto do path invertido
            if len(enemy.path) > 0:
                enemy.x, enemy.y = enemy.path[0]
                enemy.rect.x, enemy.rect.y = enemy.x, enemy.y

        # Marca que está retornando com item (ou invertido)
        enemy.is_returning_with_item = True

        # Reseta o controle de distância percorrida
        if hasattr(enemy, '_distance_traveled'):
            enemy._distance_traveled = 0.0
        if hasattr(enemy, '_last_pos'):
            enemy._last_pos = (enemy.x, enemy.y)

        print(f"[BOSS] {enemy.name} inverteu direção - novo path_index={enemy.path_index}/{len(enemy.path)}")
        print(f"[BOSS] Nova posição: ({enemy.x:.1f}, {enemy.y:.1f})")

    def _remove_enemy(self, enemy: Pokemon):
        """Remove um inimigo da lista ativa (por morte ou captura)"""
        if enemy in self.active_enemies:
            path_idx = getattr(enemy, 'path_index_origin', 0)
            self.active_enemies.remove(enemy)

            # Atualiza contagem de vivos
            if path_idx in self.alive_count:
                self.alive_count[path_idx] = max(0, self.alive_count[path_idx] - 1)

            # ===== LIBERA O ITEM SE O POKÉMON ESTAVA CARRREGANDO E MORREU =====
            # Neste caso, o item NÃO é roubado - volta ao chão
            if enemy.is_carrying:
                carried_item = enemy.is_carrying
                # Reseta o item para voltar ao chão
                carried_item.reset_capture()
                # Garante que NÃO está roubado
                carried_item.is_stolen = False
                carried_item.is_protected = True
                carried_item.carried_by = None
                enemy.is_carrying = None
                print(f"[ITEM] {carried_item.name} foi liberado (volta ao chão) após a morte de {enemy.name}")

            enemy.clear_damage_tracking()

    def _process_spawning(self, dt: float):
        """Processa o spawn de novos inimigos"""
        for path_idx, wave_active in self.wave_active.items():
            if not wave_active:
                continue

            waves = self.waves.get(path_idx, [])
            wave_idx = self.current_wave_idx.get(path_idx, 0)

            if wave_idx >= len(waves):
                self.wave_active[path_idx] = False
                continue

            wave_data = waves[wave_idx]
            path_data = self.paths.get(path_idx)

            if not path_data:
                continue

            # Delay inicial da wave
            if self.wave_timer[path_idx] > 0:
                self.wave_timer[path_idx] -= dt
                continue

            # Spawn de inimigos
            spawned = self.spawned_count.get(path_idx, 0)

            if spawned < wave_data.wave_size:
                self.spawn_timer[path_idx] -= dt

                if self.spawn_timer[path_idx] <= 0:
                    # Cria novo inimigo
                    enemy = self._create_enemy(wave_data, path_data, path_idx)

                    if enemy:
                        self.active_enemies.append(enemy)
                        self.spawned_count[path_idx] = spawned + 1
                        self.alive_count[path_idx] = self.alive_count.get(path_idx, 0) + 1

                        self.spawn_timer[path_idx] = wave_data.spawn_interval
            else:
                # Wave terminou de spawnar TODOS os inimigos (incluindo boss)
                # Verifica se todos os inimigos NÃO-BOSS morreram E o boss NÃO está vivo
                non_boss_alive = sum(1 for e in self.active_enemies
                                     if getattr(e, 'path_index_origin', 0) == path_idx
                                     and not e.is_boss and e.is_alive())

                # Verifica se o boss está vivo
                boss_alive = any(e for e in self.active_enemies
                                 if getattr(e, 'path_index_origin', 0) == path_idx
                                 and e.is_boss and e.is_alive())

                # Se não há inimigos não-boss vivos, e (se não tem boss OU o boss morreu)
                # Então pode avançar para próxima wave
                if non_boss_alive == 0 and not boss_alive:
                    # Passa para próxima wave
                    self._advance_to_next_wave(path_idx)

    def _create_enemy(self, wave_data: WaveData, path_data: PathData, path_idx: int) -> Optional[Pokemon]:
        """Cria um novo inimigo"""
        # Escolhe inimigo baseado em porcentagem
        enemy_config = self._choose_enemy(wave_data.enemies)
        if not enemy_config:
            return None

        # Calcula nível
        level = random.randint(
            enemy_config.level_min,
            enemy_config.level_max
        )

        # Verifica se é boss (último inimigo da wave)
        spawned = self.spawned_count.get(path_idx, 0)
        is_last_enemy = (spawned + 1) >= wave_data.wave_size
        is_boss = is_last_enemy and wave_data.has_boss

        # Cria Pokémon
        pokemon = Pokemon(
            path_data.start_point[0], path_data.start_point[1],
            enemy_config.pokemon_id,
            level=level,
            is_wild=True,
            shiny=random.random() < 0.001,
            is_boss=is_boss
        )
        if pokemon.is_shiny:
            sound_manager.play_effect(SoundEffect.SHINY)

        # Configura path - IMPORTANTE: cópia completa da lista
        pokemon.path = path_data.points.copy()
        pokemon.path_index = 0
        pokemon.path_index_origin = path_idx

        # Inicializa controle de distância percorrida
        pokemon._distance_traveled = 0.0
        pokemon._last_pos = (pokemon.x, pokemon.y)

        # IMPORTANTE: Não configurar original_path aqui para comuns
        # Apenas boss precisa guardar original_path
        if is_boss:
            pokemon.original_path = path_data.points.copy()

        # Configura screen manager e batalha
        pokemon.screen_manager = self.game_scene.screen_manager if self.game_scene else None
        if self.game_scene and hasattr(self.game_scene, 'battle_system'):
            pokemon.set_battle_system(self.game_scene.battle_system)
            self.game_scene.battle_system.set_effect_manager_for_pokemon(pokemon)
            print(f"[WAVE] {pokemon.name} vinculado ao effect_manager: {pokemon.effect_manager is not None}")
        # Configura velocidade
        pokemon.move_speed = pokemon.base_move_speed * wave_data.speed_multiplier

        # Configura direção inicial
        if len(path_data.points) > 1:
            dx = path_data.points[1][0] - path_data.points[0][0]
            dy = path_data.points[1][1] - path_data.points[0][1]
            if abs(dx) > abs(dy):
                pokemon.current_direction = "right" if dx > 0 else "left"
            else:
                pokemon.current_direction = "down" if dy > 0 else "up"

        # Debug
        print(f"[WAVE] Criado {pokemon.name} Lv.{pokemon.level} {'(BOSS)' if is_boss else ''} no path {path_idx}")
        print(f"[WAVE] Path points: {len(path_data.points)} pontos")
        print(f"[WAVE] Posição inicial: ({pokemon.x:.0f}, {pokemon.y:.0f})")
        print(f"[WAVE] Velocidade: {pokemon.move_speed:.2f}")

        return pokemon

    def _choose_enemy(self, enemies: List[WaveEnemy]) -> Optional[WaveEnemy]:
        """Escolhe um inimigo baseado nas porcentagens"""
        if not enemies:
            return None

        total = sum(e.percentage for e in enemies)
        if total <= 0:
            return random.choice(enemies)

        roll = random.uniform(0, total)
        cumulative = 0

        for enemy in enemies:
            cumulative += enemy.percentage
            if roll <= cumulative:
                return enemy

        return enemies[-1]

    def _advance_to_next_wave(self, path_idx: int):
        """Avança para a próxima wave do path, com suporte a repetição"""
        current_idx = self.current_wave_idx.get(path_idx, 0)
        waves = self.waves.get(path_idx, [])

        if current_idx >= len(waves):
            return

        wave_data = waves[current_idx]

        # Verifica se a wave atual deve repetir
        if wave_data.repeat_wave:
            wave_data.current_repeat += 1

            # Verifica se ainda deve repetir (repeat_count == 0 = infinito)
            if wave_data.repeat_count == 0 or wave_data.current_repeat < wave_data.repeat_count:
                print(
                    f"[WaveManager] Path {path_idx}: repetindo wave {current_idx + 1} (repetição {wave_data.current_repeat}/{wave_data.repeat_count if wave_data.repeat_count > 0 else '∞'})")
                # Reinicia a wave atual
                self._start_wave_for_path(path_idx)
                return

        # Se não deve repetir mais, avança para a próxima wave
        if current_idx + 1 < len(waves):
            self.current_wave_idx[path_idx] = current_idx + 1
            print(f"[WaveManager] Path {path_idx}: avançando para wave {current_idx + 2}")
            self._start_wave_for_path(path_idx)
        else:
            # Todas as waves concluídas
            self.wave_active[path_idx] = False
            self.current_wave_idx[path_idx] = current_idx + 1
            print(f"[WaveManager] Path {path_idx}: todas as waves concluídas")

    def _update_alive_counts(self):
        """Atualiza contagem de inimigos vivos por path"""
        # Reset contagens
        for path_idx in self.alive_count:
            self.alive_count[path_idx] = 0

        # Conta inimigos vivos
        for enemy in self.active_enemies:
            path_idx = getattr(enemy, 'path_index_origin', 0)
            if path_idx in self.alive_count:
                self.alive_count[path_idx] += 1

    def _remove_enemy(self, enemy: Pokemon):
        """Remove um inimigo da lista ativa (por morte ou captura)"""
        if enemy in self.active_enemies:
            path_idx = getattr(enemy, 'path_index_origin', 0)
            self.active_enemies.remove(enemy)

            # Atualiza contagem de vivos
            if path_idx in self.alive_count:
                self.alive_count[path_idx] = max(0, self.alive_count[path_idx] - 1)

            # ===== DISTRIBUIR XP E OURO QUANDO O INIMIGO MORRE =====
            # Verifica se o inimigo morreu (não foi capturado) e não é boss
            if enemy.current_hp <= 0 and not enemy.is_boss:
                # Distribui XP para os atacantes
                self._distribute_xp(enemy)
                # Acumula ouro por derrota
                self.total_gold_earned += self.gold_per_defeat
                print(f"[GOLD] +{self.gold_per_defeat} ouro (total acumulado: {self.total_gold_earned})")

            # ===== LIBERA O ITEM SE O POKÉMON ESTAVA CARRREGANDO E MORREU =====
            if enemy.is_carrying:
                carried_item = enemy.is_carrying
                # Reseta o item para voltar ao chão
                carried_item.reset_capture()
                # Garante que NÃO está roubado
                carried_item.is_stolen = False
                carried_item.is_protected = True
                carried_item.carried_by = None
                enemy.is_carrying = None
                print(f"[ITEM] {carried_item.item_name} foi liberado (volta ao chão) após a morte de {enemy.name}")

            enemy.clear_damage_tracking()

    def _distribute_xp(self, defeated_enemy: Pokemon):
        """Distribui XP quando um inimigo é derrotado - com suporte para status e buffs"""
        contributors = defeated_enemy.get_xp_contributors()
        if not contributors:
            print(f"[XP] Nenhum contribuidor registrado para {defeated_enemy.name}")
            return

        # Base XP: maior para inimigos mais fortes
        base_xp = 15 + (defeated_enemy.level * 5)
        # Bônus para shiny
        if defeated_enemy.is_shiny:
            base_xp = int(base_xp * 1.5)
            print(f"[XP] Bônus shiny! +50% XP")

        total_contribution = defeated_enemy.get_total_contribution()
        if total_contribution <= 0:
            # Se não houver contribuição (algo errado), dá XP igual para todos os atacantes registrados
            total_contribution = len(contributors)

        placement_manager = None
        if self.game_scene and hasattr(self.game_scene, 'placement_manager'):
            placement_manager = self.game_scene.placement_manager

        if not placement_manager:
            return

        print(f"[XP] {defeated_enemy.name} Lv.{defeated_enemy.level} derrotado!")
        print(f"[XP] XP base: {base_xp}")
        print(f"[XP] Contribuição total: {total_contribution:.1f}")
        print(f"[XP] Contribuidores: {[(id(p), c) for p, c in contributors]}")

        for attacker_id, contribution in contributors:
            proportion = contribution / total_contribution
            xp_gained = int(base_xp * proportion)

            # Garante XP mínimo de 1 para quem contribuiu
            if xp_gained < 1 and contribution > 0:
                xp_gained = 1

            # Encontra o Pokémon pelo ID
            for pokemon in placement_manager.placed_pokemon:
                if id(pokemon) == attacker_id and pokemon.is_alive():
                    old_level = pokemon.level
                    pokemon.gain_xp(xp_gained)

                    # Log detalhado
                    contribution_type = []
                    if attacker_id in defeated_enemy.damage_contributions:
                        contribution_type.append(f"dano:{defeated_enemy.damage_contributions[attacker_id]}")
                    if attacker_id in defeated_enemy.status_contributions:
                        contribution_type.append(f"status:{defeated_enemy.status_contributions[attacker_id]:.1f}")
                    if attacker_id in defeated_enemy.buff_contributions:
                        contribution_type.append(f"buff:{defeated_enemy.buff_contributions[attacker_id]:.1f}")

                    print(f"[XP] {pokemon.name} ganhou {xp_gained} XP ({', '.join(contribution_type)})")

                    if pokemon.level > old_level:
                        print(f"[XP] {pokemon.name} subiu para Lv.{pokemon.level}!")

                    if self.game_scene and hasattr(self.game_scene, 'game'):
                        self.game_scene.game.player.auto_save()
                    break

    def get_total_gold_earned(self) -> int:
        """Retorna o total de ouro acumulado"""
        return self.total_gold_earned

    def get_current_wave_info(self) -> dict:
        """Retorna informações consolidadas das waves"""
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
                    "total": len(self.waves),
                    "enemies_remaining": len(self.active_enemies),
                    "enemies_spawned": total_spawned,
                    "enemies_total": total_enemies,
                    "progress": total_spawned / total_enemies if total_enemies > 0 else 0,
                    "active_paths": 0
                }

        return {
            "name": f"{active_paths} wave(s) ativa(s)",
            "index": "Múltiplas",
            "total": len(self.waves),
            "enemies_remaining": len(self.active_enemies),
            "enemies_spawned": total_spawned,
            "enemies_total": total_enemies,
            "progress": total_spawned / total_enemies if total_enemies > 0 else 0,
            "active_paths": active_paths
        }

    def has_more_waves(self) -> bool:
        """Verifica se ainda existem waves"""
        for path_idx in self.waves.keys():
            current = self.current_wave_idx.get(path_idx, 0)
            if current < len(self.waves[path_idx]):
                return True
        return False

    def is_wave_completely_finished(self) -> bool:
        """
        Verifica se todas as waves terminaram.
        BOSS não impede a conclusão da fase (ele continua andando).
        """
        # Verifica se há inimigos NÃO-BOSS vivos
        non_boss_enemies = [e for e in self.active_enemies if not e.is_boss]
        if non_boss_enemies:
            return False

        # Verifica se alguma wave ainda está ativa
        for path_idx in self.waves.keys():
            if self.wave_active.get(path_idx, False):
                return False

            current = self.current_wave_idx.get(path_idx, 0)
            if current < len(self.waves[path_idx]):
                return False

        return True

    def reset_gold(self):
        """Reseta o ouro acumulado para uma nova fase"""
        self.total_gold_earned = 0