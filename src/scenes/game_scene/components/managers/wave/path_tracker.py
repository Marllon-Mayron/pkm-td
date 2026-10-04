# src/managers/wave/path_tracker.py

import math
from typing import List, Tuple, Optional, Dict
from dataclasses import dataclass


@dataclass
class Path:
    """Representa um caminho"""
    index: int
    points: List[Tuple[float, float]]
    start_point: Tuple[float, float]
    end_point: Tuple[float, float]
    length: float


class PathTracker:
    """
    Gerencia o movimento de inimigos ao longo de um path.
    """
    ARRIVAL_THRESHOLD = 8.0

    def __init__(self):
        self.paths: Dict[int, Path] = {}
        self._enemy_state: Dict[int, dict] = {}

    def set_paths(self, paths_data: list):
        """Carrega os paths"""
        self.paths.clear()
        for i, path in enumerate(paths_data):
            points = path.get_path_points()
            if len(points) >= 2:
                self.paths[i] = Path(
                    index=i,
                    points=points,
                    start_point=points[0],
                    end_point=points[-1],
                    length=self._calculate_length(points)
                )
                print(f"[PathTracker] Path {i} carregado: inicio={points[0]}, fim={points[-1]}")

    def get_path_by_index(self, path_idx: int) -> Optional[Path]:
        return self.paths.get(path_idx)

    def get_path(self, enemy: 'Pokemon') -> Optional[Path]:
        path_idx = getattr(enemy, 'path_index_origin', 0)
        return self.paths.get(path_idx)

    def assign_path(self, enemy: 'Pokemon', path_idx: int, start_at_begin: bool = True):
        """Atribui um path a um inimigo"""
        path = self.paths.get(path_idx)
        if not path:
            print(f"[PathTracker] ERRO: Path {path_idx} não encontrado!")
            return False

        enemy.path = path.points.copy()
        enemy.path_index = 0
        enemy.path_index_origin = path_idx
        enemy.original_path = path.points.copy()

        if start_at_begin:
            enemy.x, enemy.y = path.start_point
            print(f"[PathTracker] Iniciando {enemy.name} no INÍCIO: ({enemy.x}, {enemy.y})")
        else:
            enemy.x, enemy.y = path.end_point
            enemy.path_index = len(path.points) - 1
            print(f"[PathTracker] Iniciando {enemy.name} no FIM: ({enemy.x}, {enemy.y})")

        enemy.rect.x, enemy.rect.y = enemy.x, enemy.y

        self._enemy_state[id(enemy)] = {
            'distance_traveled': 0.0,
            'last_pos': (enemy.x, enemy.y),
            'is_reversed': False,
            'has_reached_start': False,
            'has_reached_end': False,
            'arrival_cooldown': 0.0,
            'just_reversed_cooldown': 0.0,
            'spawn_cooldown': 0.5,
            'ignore_path_timer': 0.0,
            'combat_target': None,
        }
        return True

    def set_ignore_path(self, enemy: 'Pokemon', duration: float = 1.0):
        """
        Faz o inimigo ignorar o path por um período (para combate).
        Durante esse tempo, ele pode se mover livremente.
        """
        state = self._enemy_state.get(id(enemy))
        if state:
            state['ignore_path_timer'] = duration
            print(f"[PathTracker] {enemy.name} ignorando path por {duration}s")

    def should_ignore_path(self, enemy: 'Pokemon') -> bool:
        """Verifica se o inimigo deve ignorar o path temporariamente"""
        state = self._enemy_state.get(id(enemy))
        if state:
            return state['ignore_path_timer'] > 0
        return False

    def update_movement(self, enemy: 'Pokemon', dt: float) -> Tuple[bool, bool]:
        """
        Atualiza movimento do inimigo.
        Retorna (arrived_at_end, arrived_at_start)

        BOSSES:
          - NUNCA ignoram o path.
          - NUNCA abandonam alvo.
          - NUNCA param em combate.
          - Sempre seguem o path até o fim/início, capturando itens no caminho.
          O combate do boss é tratado separadamente em WaveManager._update_boss_combat.
        """
        state = self._enemy_state.get(id(enemy))
        if not state:
            return False, False

        is_boss = getattr(enemy, 'is_boss', False)

        # ===== BOSS: PULA LÓGICA DE COMBATE =====
        if not is_boss:
            if hasattr(enemy, 'target') and enemy.target:
                if not enemy.target.is_alive() or enemy.target.is_defeated:
                    enemy.target = None
                    state['ignore_path_timer'] = 0.0
                    state['combat_target'] = None
                    enemy.combat_state = "idle"
                    return False, False

                if not hasattr(enemy.target, 'is_placed') or not enemy.target.is_placed:
                    enemy.target = None
                    state['ignore_path_timer'] = 0.0
                    state['combat_target'] = None
                    return False, False

                if hasattr(enemy.target, '_marked_for_removal') and enemy.target._marked_for_removal:
                    enemy.target = None
                    state['ignore_path_timer'] = 0.0
                    state['combat_target'] = None
                    return False, False

            should_abandon_target = False

            if hasattr(enemy, 'target') and enemy.target:
                dx = enemy.target.x - enemy.x
                dy = enemy.target.y - enemy.y
                distance_to_target = math.hypot(dx, dy)

                current_move = None
                if hasattr(enemy, 'get_current_move_for_pattern'):
                    current_move = enemy.get_current_move_for_pattern()
                elif hasattr(enemy, 'get_current_move'):
                    current_move = enemy.get_current_move()

                if current_move and current_move.category == "physical":
                    max_range = 50
                else:
                    max_range = enemy.attack_range * 2

                if distance_to_target > max_range:
                    should_abandon_target = True
                    print(f"[PathTracker] {enemy.name}: alvo {enemy.target.name} muito longe "
                          f"({distance_to_target:.0f} > {max_range:.0f})! Abandonando perseguição.")

                if hasattr(enemy, '_attack_attempts') and enemy._attack_attempts > 5:
                    should_abandon_target = True
                    print(f"[PathTracker] {enemy.name}: muitas tentativas de ataque sem sucesso! Abandonando.")
                    enemy._attack_attempts = 0

            if should_abandon_target:
                enemy.target = None
                state['ignore_path_timer'] = 0.0
                state['combat_target'] = None
                enemy.combat_state = "idle"
                if hasattr(enemy, '_attack_attempts'):
                    enemy._attack_attempts = 0
                return False, False

            is_in_combat = False

            if hasattr(enemy, 'target') and enemy.target and enemy.target.is_alive():
                is_in_combat = True

                dx = enemy.target.x - enemy.x
                dy = enemy.target.y - enemy.y
                distance_to_target = math.hypot(dx, dy)

                current_move = None
                if hasattr(enemy, 'get_current_move_for_pattern'):
                    current_move = enemy.get_current_move_for_pattern()
                elif hasattr(enemy, 'get_current_move'):
                    current_move = enemy.get_current_move()

                if current_move and current_move.category == "physical":
                    required_range = 25
                else:
                    required_range = enemy.attack_range

                is_attacking = hasattr(enemy, '_attack_animation_active') and enemy._attack_animation_active

                if distance_to_target < required_range or is_attacking:
                    state['ignore_path_timer'] = max(state['ignore_path_timer'], 0.5)
                    state['combat_target'] = enemy.target
                else:
                    state['ignore_path_timer'] = 0.0
                    enemy.target = None
                    is_in_combat = False

            if state['ignore_path_timer'] > 0:
                state['ignore_path_timer'] -= dt
                if state['ignore_path_timer'] > 0:
                    return False, False

            if enemy.target:
                enemy.target = None
                enemy.combat_state = "idle"

            state['combat_target'] = None

        # ==================================================================
        # MOVIMENTO PELO PATH
        # ==================================================================
        if state['spawn_cooldown'] > 0:
            state['spawn_cooldown'] -= dt

        if hasattr(enemy, 'combat') and enemy.combat.is_frozen():
            if enemy.combat.update_freeze(dt):
                return False, False

        if hasattr(enemy, 'combat') and enemy.combat.is_asleep():
            if enemy.combat.update_sleep(dt):
                return False, False

        if hasattr(enemy, 'combat') and enemy.combat.is_stunned():
            if enemy.combat.update_stun(dt):
                return False, False

        if not enemy.path or len(enemy.path) == 0:
            return False, False

        if state['arrival_cooldown'] > 0:
            state['arrival_cooldown'] -= dt

        if state['just_reversed_cooldown'] > 0:
            state['just_reversed_cooldown'] -= dt

        if enemy.path_index < 0:
            enemy.path_index = 0
        if enemy.path_index >= len(enemy.path):
            enemy.path_index = len(enemy.path) - 1

        # ===== THRESHOLD ADAPTATIVO (PATCH B) =====
        step_size = enemy.move_speed * dt * 60
        arrival_threshold = max(self.ARRIVAL_THRESHOLD, step_size * 1.5)

        # ===== CHEGOU AO INÍCIO (index 0) =====
        if enemy.path_index == 0:
            target_x, target_y = enemy.path[enemy.path_index]
            dx = target_x - enemy.x
            dy = target_y - enemy.y
            dist_to_start = math.hypot(dx, dy)

            if dist_to_start < arrival_threshold:  # <-- PATCH
                if state['spawn_cooldown'] <= 0 and state['just_reversed_cooldown'] <= 0:
                    if not state['has_reached_start'] and state['arrival_cooldown'] <= 0:
                        state['has_reached_start'] = True
                        state['arrival_cooldown'] = 0.1
                        print(f"[PathTracker] {enemy.name} chegou ao INÍCIO!")
                        return False, True

        # ===== CHEGOU AO FIM (último index) =====
        if enemy.path_index == len(enemy.path) - 1:
            target_x, target_y = enemy.path[enemy.path_index]
            dx = target_x - enemy.x
            dy = target_y - enemy.y
            dist_to_end = math.hypot(dx, dy)

            if dist_to_end < arrival_threshold:  # <-- PATCH
                if state['spawn_cooldown'] <= 0 and state['just_reversed_cooldown'] <= 0:
                    if not state['has_reached_end'] and state['arrival_cooldown'] <= 0:
                        state['has_reached_end'] = True
                        state['arrival_cooldown'] = 0.1
                        print(f"[PathTracker] {enemy.name} chegou ao FIM!")
                        return True, False

        # ===== MOVIMENTO PADRÃO =====
        target_x, target_y = enemy.path[enemy.path_index]
        dx = target_x - enemy.x
        dy = target_y - enemy.y
        distance = math.hypot(dx, dy)
        move_distance = enemy.move_speed * dt * 60

        if distance <= move_distance:
            enemy.x, enemy.y = target_x, target_y
            enemy.rect.x, enemy.rect.y = enemy.x, enemy.y

            enemy.path_index += 1

            move_x = target_x - state['last_pos'][0]
            move_y = target_y - state['last_pos'][1]
            state['distance_traveled'] += math.hypot(move_x, move_y)
            state['last_pos'] = (enemy.x, enemy.y)

            # Passou do último nó
            if enemy.path_index >= len(enemy.path):
                if state['spawn_cooldown'] <= 0 and state['just_reversed_cooldown'] <= 0:
                    if not state['has_reached_end'] and state['arrival_cooldown'] <= 0:
                        state['has_reached_end'] = True
                        state['arrival_cooldown'] = 0.1
                        print(f"[PathTracker] {enemy.name} chegou ao FIM!")
                        return True, False

            # Passou do primeiro nó pra trás
            elif enemy.path_index < 0:
                if state['spawn_cooldown'] <= 0 and state['just_reversed_cooldown'] <= 0:
                    if not state['has_reached_start'] and state['arrival_cooldown'] <= 0:
                        state['has_reached_start'] = True
                        state['arrival_cooldown'] = 0.1
                        print(f"[PathTracker] {enemy.name} chegou ao INÍCIO!")
                        return False, True

        else:
            move_x = (dx / distance) * move_distance
            move_y = (dy / distance) * move_distance
            enemy.x += move_x
            enemy.y += move_y
            enemy.rect.x, enemy.rect.y = enemy.x, enemy.y

            state['distance_traveled'] += move_distance
            state['last_pos'] = (enemy.x, enemy.y)

            self._update_direction_from_movement(enemy, dx, dy)

        return False, False

    _DIRECTION_THRESHOLD = 0.414

    def _update_direction_from_movement(self, enemy: 'Pokemon', dx: float, dy: float):
        """Atualiza direção baseada no movimento (8 direções)"""
        if dx == 0 and dy == 0:
            return

        abs_dx = abs(dx)
        abs_dy = abs(dy)

        h_sign = 1 if dx > 0 else -1
        v_sign = 1 if dy > 0 else -1

        ratio = abs_dy / abs_dx if abs_dx > abs_dy else abs_dx / abs_dy
        is_diagonal = ratio > self._DIRECTION_THRESHOLD

        if not is_diagonal:
            if abs_dx >= abs_dy:
                enemy.current_direction = "right" if dx > 0 else "left"
            else:
                enemy.current_direction = "down" if dy > 0 else "up"
        else:
            if dx > 0 and dy > 0:
                enemy.current_direction = "down-right"
            elif dx > 0 and dy < 0:
                enemy.current_direction = "up-right"
            elif dx < 0 and dy > 0:
                enemy.current_direction = "down-left"
            else:
                enemy.current_direction = "up-left"

    def reverse_direction_simple(self, enemy: 'Pokemon'):
        """
        Inverte a direção do inimigo para paths lineares.
        O inimigo anda de volta pelo MESMO caminho.

        CORREÇÃO:
          Inverte `enemy.path` (path ATUAL), não `enemy.original_path`.
          Antes, cada chamada partia sempre do original e dava o mesmo
          resultado após a 1ª inversão — o boss "pulava" de nó na 2ª
          chegada (bug de sair da rota).

          Além disso, encontra o nó mais próximo da posição REAL do boss
          no novo path, evitando teleportes visuais se ele não estiver
          exatamente em um nó.
        """
        if not enemy.path:
            print(f"[PathTracker] {enemy.name} não tem path para reverter!")
            return

        state = self._enemy_state.get(id(enemy))
        if not state:
            return

        # ===== INVERTE O PATH ATUAL =====
        current = list(enemy.path)
        enemy.path = list(reversed(current))

        # ===== ENCONTRA O NÓ MAIS PRÓXIMO DA POSIÇÃO ATUAL =====
        current_x, current_y = enemy.x, enemy.y
        min_dist = float('inf')
        closest_idx = 0
        for i, point in enumerate(enemy.path):
            dist = math.hypot(current_x - point[0], current_y - point[1])
            if dist < min_dist:
                min_dist = dist
                closest_idx = i

        # Avança um passo para não ficar preso no nó atual
        if closest_idx + 1 < len(enemy.path):
            enemy.path_index = closest_idx + 1
        else:
            enemy.path_index = closest_idx

        state['has_reached_start'] = False
        state['has_reached_end'] = False
        state['arrival_cooldown'] = 0.0
        state['just_reversed_cooldown'] = 0.0
        state['last_pos'] = (enemy.x, enemy.y)
        state['is_reversed'] = not state.get('is_reversed', False)

        enemy.is_returning_with_item = False
        enemy._just_reversed = True
        enemy._reverse_timer = 0.0

        direction = "FIM → INÍCIO" if not state['is_reversed'] else "INÍCIO → FIM"
        print(f"[PathTracker] {enemy.name} inverteu direção. Agora: {direction} "
              f"(index {enemy.path_index}/{len(enemy.path) - 1})")

    def reverse_path(self, enemy: 'Pokemon'):
        """
        Inverte o path do inimigo (para andar de volta pelo mesmo caminho).
        SEM TELEPORTE — mantém a posição atual e apenas inverte a direção.

        CORREÇÃO: usa `enemy.path` (path atual), para funcionar corretamente
        quando o boss já inverteu uma vez (ex: chegou ao fim e capturou item
        no caminho de volta).
        """
        if not enemy.path:
            print(f"[PathTracker] {enemy.name} não tem path para reverter!")
            return

        state = self._enemy_state.get(id(enemy))
        if not state:
            print(f"[PathTracker] {enemy.name} não tem estado para reverter!")
            return

        # ===== INVERTE O PATH ATUAL =====
        enemy.path = list(reversed(enemy.path.copy()))

        # Encontra o nó mais próximo da posição atual
        current_x, current_y = enemy.x, enemy.y
        min_dist = float('inf')
        closest_idx = 0

        for i, point in enumerate(enemy.path):
            dist = math.hypot(current_x - point[0], current_y - point[1])
            if dist < min_dist:
                min_dist = dist
                closest_idx = i

        enemy.path_index = closest_idx

        state['has_reached_start'] = False
        state['has_reached_end'] = False
        state['arrival_cooldown'] = 0.0
        state['just_reversed_cooldown'] = 0.0
        state['distance_traveled'] = 0.0
        state['last_pos'] = (enemy.x, enemy.y)
        state['is_reversed'] = not state['is_reversed']

        enemy._just_reversed = True
        enemy._reverse_timer = 0.0
        enemy.is_returning_with_item = False

        if enemy.path_index >= len(enemy.path):
            enemy.path_index = len(enemy.path) - 1
        if enemy.path_index < 0:
            enemy.path_index = 0

        direction = "FIM → INÍCIO" if not state['is_reversed'] else "INÍCIO → FIM"
        print(f"[PathTracker] {enemy.name} (BOSS={enemy.is_boss}) REVERTEU PATH. "
              f"Agora: {direction}. Pos: ({enemy.x:.0f}, {enemy.y:.0f}), "
              f"index: {enemy.path_index}/{len(enemy.path)}")

    def _calculate_length(self, points: List[Tuple[float, float]]) -> float:
        length = 0.0
        for i in range(len(points) - 1):
            dx = points[i + 1][0] - points[i][0]
            dy = points[i + 1][1] - points[i][1]
            length += math.hypot(dx, dy)
        return length

    def reset_enemy_state(self, enemy: 'Pokemon'):
        """Reseta o estado de um inimigo"""
        enemy_id = id(enemy)
        if enemy_id in self._enemy_state:
            self._enemy_state[enemy_id].update({
                'has_reached_start': False,
                'has_reached_end': False,
                'arrival_cooldown': 0.0,
                'just_reversed_cooldown': 0.0,
                'distance_traveled': 0.0,
                'last_pos': (enemy.x, enemy.y)
            })