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
    Responsabilidade ÚNICA: movimento e rastreamento.
    """

    PROXIMITY_THRESHOLD = 15.0

    def __init__(self):
        self.paths: Dict[int, Path] = {}
        self._enemy_state: Dict[int, dict] = {}  # enemy_id -> estado

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

    def get_path_by_index(self, path_idx: int) -> Optional[Path]:
        """Obtém o path pelo índice"""
        return self.paths.get(path_idx)

    def get_path(self, enemy: 'Pokemon') -> Optional[Path]:
        """Obtém o path de um inimigo"""
        path_idx = getattr(enemy, 'path_index_origin', 0)
        return self.paths.get(path_idx)

    def assign_path(self, enemy: 'Pokemon', path_idx: int, start_at_begin: bool = True):
        """Atribui um path a um inimigo"""
        path = self.paths.get(path_idx)
        if not path:
            return False

        enemy.path = path.points.copy()
        enemy.path_index = 0
        enemy.path_index_origin = path_idx
        enemy.original_path = path.points.copy()

        if start_at_begin:
            enemy.x, enemy.y = path.start_point
        else:
            enemy.x, enemy.y = path.end_point
            enemy.path_index = len(path.points) - 1

        enemy.rect.x, enemy.rect.y = enemy.x, enemy.y

        # Inicializa estado
        self._enemy_state[id(enemy)] = {
            'distance_traveled': 0.0,
            'last_pos': (enemy.x, enemy.y),
            'is_reversed': False
        }
        return True

    def update_movement(self, enemy: 'Pokemon', dt: float) -> bool:
        """
        Atualiza movimento do inimigo.
        Retorna True se chegou ao FIM do path.
        """
        if not enemy.path or enemy.path_index >= len(enemy.path):
            return False

        # Obtém estado
        state = self._enemy_state.get(id(enemy))
        if not state:
            return False

        target_x, target_y = enemy.path[enemy.path_index]
        dx = target_x - enemy.x
        dy = target_y - enemy.y
        distance = math.hypot(dx, dy)
        move_distance = enemy.move_speed * dt * 60

        if distance <= move_distance:
            # Chegou ao ponto
            enemy.x, enemy.y = target_x, target_y
            enemy.rect.x, enemy.rect.y = enemy.x, enemy.y
            enemy.path_index += 1

            # Atualiza distância percorrida
            move_x, move_y = target_x - state['last_pos'][0], target_y - state['last_pos'][1]
            state['distance_traveled'] += math.hypot(move_x, move_y)
            state['last_pos'] = (enemy.x, enemy.y)

            # Verifica se chegou ao FIM
            if enemy.path_index >= len(enemy.path):
                path = self.get_path(enemy)
                if path and state['distance_traveled'] >= 15.0:
                    state['distance_traveled'] = 0.0
                    return True  # Chegou ao fim

        else:
            # Move em direção ao ponto
            move_x = (dx / distance) * move_distance
            move_y = (dy / distance) * move_distance
            enemy.x += move_x
            enemy.y += move_y
            enemy.rect.x, enemy.rect.y = enemy.x, enemy.y

            # Atualiza distância percorrida
            state['distance_traveled'] += move_distance
            state['last_pos'] = (enemy.x, enemy.y)

            # Atualiza direção
            self._update_direction(enemy, dx, dy)

        return False

    def reverse_direction(self, enemy: 'Pokemon'):
        """Inverte a direção do inimigo"""
        if not enemy.original_path:
            return

        state = self._enemy_state.get(id(enemy))
        if not state:
            return

        # Inverte o path
        enemy.path = list(reversed(enemy.original_path.copy()))

        # Encontra ponto mais próximo no novo path
        min_dist = float('inf')
        closest_idx = 0
        for i, point in enumerate(enemy.path):
            dist = math.hypot(enemy.x - point[0], enemy.y - point[1])
            if dist < min_dist:
                min_dist = dist
                closest_idx = i

        enemy.path_index = closest_idx

        # Se está exatamente no ponto, avança
        if min_dist < 1.0 and closest_idx < len(enemy.path) - 1:
            enemy.path_index = closest_idx + 1

        state['is_reversed'] = not state['is_reversed']
        state['distance_traveled'] = 0.0
        state['last_pos'] = (enemy.x, enemy.y)

        # Marca que acabou de inverter (para evitar loops)
        enemy._just_reversed = True
        enemy._reverse_timer = 0.5

    def _update_direction(self, enemy: 'Pokemon', dx: float, dy: float):
        """Atualiza direção baseada no movimento"""
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