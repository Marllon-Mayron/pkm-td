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

    PROXIMITY_THRESHOLD = 15.0
    ARRIVAL_THRESHOLD = 10.0

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
        }
        return True

    def update_movement(self, enemy: 'Pokemon', dt: float) -> Tuple[bool, bool]:
        """
        Atualiza movimento do inimigo.
        Retorna (arrived_at_end, arrived_at_start)
        """
        state = self._enemy_state.get(id(enemy))
        if not state:
            return False, False

        # Cooldown de spawn
        if state['spawn_cooldown'] > 0:
            state['spawn_cooldown'] -= dt

        # Verifica status que impedem movimento
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

        # Cooldowns
        if state['arrival_cooldown'] > 0:
            state['arrival_cooldown'] -= dt

        if state['just_reversed_cooldown'] > 0:
            state['just_reversed_cooldown'] -= dt

        # Garante que o path_index está dentro dos limites
        if enemy.path_index < 0:
            enemy.path_index = 0
        if enemy.path_index >= len(enemy.path):
            enemy.path_index = len(enemy.path) - 1

        # CORREÇÃO: Se estiver no último ponto, verifica se já chegou ao fim
        if enemy.path_index == len(enemy.path) - 1:
            target_x, target_y = enemy.path[enemy.path_index]
            dx = target_x - enemy.x
            dy = target_y - enemy.y
            dist_to_end = math.hypot(dx, dy)

            if dist_to_end < self.ARRIVAL_THRESHOLD:
                if state['spawn_cooldown'] <= 0 and state['just_reversed_cooldown'] <= 0:
                    if not state['has_reached_end'] and state['arrival_cooldown'] <= 0:
                        state['has_reached_end'] = True
                        state['arrival_cooldown'] = 0.1
                        print(f"[PathTracker] {enemy.name} chegou ao FIM!")
                        return True, False

        target_x, target_y = enemy.path[enemy.path_index]
        dx = target_x - enemy.x
        dy = target_y - enemy.y
        distance = math.hypot(dx, dy)
        move_distance = enemy.move_speed * dt * 60

        if distance <= move_distance:
            # Chegou ao ponto
            enemy.x, enemy.y = target_x, target_y
            enemy.rect.x, enemy.rect.y = enemy.x, enemy.y

            # Avança para o próximo ponto
            enemy.path_index += 1

            move_x, move_y = target_x - state['last_pos'][0], target_y - state['last_pos'][1]
            state['distance_traveled'] += math.hypot(move_x, move_y)
            state['last_pos'] = (enemy.x, enemy.y)

            # Verifica chegada ao FIM (depois de passar do último ponto)
            if enemy.path_index >= len(enemy.path):
                if state['spawn_cooldown'] <= 0 and state['just_reversed_cooldown'] <= 0:
                    if not state['has_reached_end'] and state['arrival_cooldown'] <= 0:
                        state['has_reached_end'] = True
                        state['arrival_cooldown'] = 0.1
                        print(f"[PathTracker] {enemy.name} chegou ao FIM!")
                        return True, False

        else:
            # Move em direção ao ponto
            move_x = (dx / distance) * move_distance
            move_y = (dy / distance) * move_distance
            enemy.x += move_x
            enemy.y += move_y
            enemy.rect.x, enemy.rect.y = enemy.x, enemy.y

            state['distance_traveled'] += move_distance
            state['last_pos'] = (enemy.x, enemy.y)
            self._update_direction(enemy, dx, dy)

        return False, False

    def reverse_direction_simple(self, enemy: 'Pokemon'):
        """
        Inverte a direção do inimigo para paths lineares.
        O inimigo deve andar de volta pelo MESMO caminho.
        """
        if not enemy.original_path:
            print(f"[PathTracker] {enemy.name} não tem original_path!")
            return

        state = self._enemy_state.get(id(enemy))
        if not state:
            return

        # Guarda o path original
        original = enemy.original_path.copy()

        # INVERTE O PATH (fim → início)
        enemy.path = list(reversed(original))

        # O inimigo acabou de chegar ao fim, então ele está no último ponto do path original
        # No path invertido, esse é o PRIMEIRO ponto (índice 0)
        # Ele deve começar a andar para o PRÓXIMO ponto (índice 1)

        if len(enemy.path) > 1:
            enemy.path_index = 1  # Começa do segundo ponto do path invertido
        else:
            enemy.path_index = 0

        # NÃO mexe na posição x,y - mantém onde está (no ponto 3/fim)

        # Reseta flags
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
        print(f"[PathTracker] {enemy.name} inverteu direção. Agora: {direction}")
        print(f"[PathTracker] Path original: {original}")
        print(f"[PathTracker] Path invertido: {enemy.path}")
        print(
            f"[PathTracker] Pos atual: ({enemy.x:.0f}, {enemy.y:.0f}), path_index: {enemy.path_index}/{len(enemy.path)}")
        print(f"[PathTracker] Próximo ponto: {enemy.path[enemy.path_index]}")

    def reverse_path(self, enemy: 'Pokemon'):
        """
        Inverte o path do inimigo (para andar de volta pelo mesmo caminho).
        SEM TELEPORTE - mantém a posição atual e apenas inverte a direção.
        """
        if not enemy.original_path:
            print(f"[PathTracker] {enemy.name} não tem original_path para reverter!")
            return

        state = self._enemy_state.get(id(enemy))
        if not state:
            print(f"[PathTracker] {enemy.name} não tem estado para reverter!")
            return

        # INVERTE O PATH (fim → início vira início → fim)
        reversed_points = list(reversed(enemy.original_path.copy()))
        enemy.path = reversed_points

        # ENCONTRA O PONTO MAIS PRÓXIMO no NOVO path (baseado na posição atual)
        current_x, current_y = enemy.x, enemy.y
        min_dist = float('inf')
        closest_idx = 0

        for i, point in enumerate(enemy.path):
            dist = math.hypot(current_x - point[0], current_y - point[1])
            if dist < min_dist:
                min_dist = dist
                closest_idx = i

        # DEFINE O ÍNDICE para o ponto MAIS PRÓXIMO (NÃO avança para o próximo)
        # Isso evita o teleporte - o inimigo continua de onde está
        enemy.path_index = closest_idx

        # NÃO altera a posição do inimigo - mantém onde ele está
        # Apenas reseta os flags

        # RESETA OS FLAGS (ZERA COOLDOWNS para não travar)
        state['has_reached_start'] = False
        state['has_reached_end'] = False
        state['arrival_cooldown'] = 0.0
        state['just_reversed_cooldown'] = 0.0
        state['distance_traveled'] = 0.0
        state['last_pos'] = (enemy.x, enemy.y)
        state['is_reversed'] = not state['is_reversed']

        # Flags para controle
        enemy._just_reversed = True
        enemy._reverse_timer = 0.0
        enemy.is_returning_with_item = False

        # Força path_index válido
        if enemy.path_index >= len(enemy.path):
            enemy.path_index = len(enemy.path) - 1
        if enemy.path_index < 0:
            enemy.path_index = 0

        direction = "FIM → INÍCIO" if not state['is_reversed'] else "INÍCIO → FIM"
        print(f"[PathTracker] {enemy.name} (BOSS={enemy.is_boss}) REVERTEU PATH. Agora: {direction}. "
              f"Pos: ({enemy.x:.0f}, {enemy.y:.0f}), path_index: {enemy.path_index}/{len(enemy.path)}")

    def _update_direction(self, enemy: 'Pokemon', dx: float, dy: float):
        if abs(dx) > abs(dy):
            enemy.current_direction = "right" if dx > 0 else "left"
        else:
            enemy.current_direction = "down" if dy > 0 else "up"

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