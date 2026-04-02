# src/managers/wave/item_decision.py

import math
from typing import Optional, List, Tuple
from enum import Enum


class DirectionDecision(Enum):
    """Decisão de direção após capturar item"""
    CONTINUE = "continue"  # Continua na mesma direção
    REVERSE = "reverse"    # Volta para o início


class ItemDecision:
    """
    Responsável por decidir a direção que um Pokémon deve tomar
    após capturar um item.
    """

    def __init__(self):
        self.threshold = 30.0  # Distância para considerar "próximo"

    def decide_direction(self, enemy: 'Pokemon', path) -> DirectionDecision:
        """
        Decide se o Pokémon deve continuar ou voltar após capturar o item.

        Regras:
        - TODOS os inimigos calculam o caminho mais curto
        - A diferença é que o boss nunca para - ele sempre continua andando
          mesmo após decidir voltar, ele vai até o início e depois volta para o fim
        """
        if not path:
            return DirectionDecision.CONTINUE

        # Encontra o ponto mais próximo no path
        current_point_idx = self._find_closest_path_point(enemy, path)

        # Calcula distância até o fim e início
        dist_to_end = self._calculate_distance_along_path(path, current_point_idx, len(path.points) - 1)
        dist_to_start = self._calculate_distance_along_path(path, current_point_idx, 0)

        # Margem para evitar decisões instáveis
        margin = 5.0

        if dist_to_end + margin < dist_to_start:
            print(
                f"[ItemDecision] {enemy.name}: dist_fim={dist_to_end:.1f} < dist_inicio={dist_to_start:.1f} -> CONTINUE")
            return DirectionDecision.CONTINUE
        elif dist_to_start + margin < dist_to_end:
            print(
                f"[ItemDecision] {enemy.name}: dist_inicio={dist_to_start:.1f} < dist_fim={dist_to_end:.1f} -> REVERSE")
            return DirectionDecision.REVERSE
        else:
            # Empate - mantém a direção atual
            current_direction = getattr(enemy, 'current_direction', 'right')
            print(
                f"[ItemDecision] {enemy.name}: empate, mantendo direção atual -> {'CONTINUE' if not getattr(enemy, 'is_returning_with_item', False) else 'REVERSE'}")
            if getattr(enemy, 'is_returning_with_item', False):
                return DirectionDecision.REVERSE
            else:
                return DirectionDecision.CONTINUE

    def _find_closest_path_point(self, enemy: 'Pokemon', path) -> int:
        """Encontra o índice do ponto do path mais próximo do Pokémon."""
        min_dist = float('inf')
        closest_idx = 0

        for i, point in enumerate(path.points):
            dist = math.hypot(enemy.x - point[0], enemy.y - point[1])
            if dist < min_dist:
                min_dist = dist
                closest_idx = i

        return closest_idx

    def _calculate_distance_along_path(self, path, from_idx: int, to_idx: int) -> float:
        """Calcula a distância percorrida ao longo do path do índice from_idx até to_idx."""
        if from_idx == to_idx:
            return 0.0

        step = 1 if to_idx > from_idx else -1

        distance = 0.0
        current_idx = from_idx

        while current_idx != to_idx:
            next_idx = current_idx + step
            if 0 <= next_idx < len(path.points):
                dx = path.points[next_idx][0] - path.points[current_idx][0]
                dy = path.points[next_idx][1] - path.points[current_idx][1]
                distance += math.hypot(dx, dy)
                current_idx = next_idx
            else:
                break

        return distance

    def is_close_to_start(self, enemy: 'Pokemon', path, threshold: float = None) -> bool:
        """Verifica se o Pokémon está perto do início do path"""
        if not path:
            return False

        t = threshold if threshold is not None else self.threshold
        closest_idx = self._find_closest_path_point(enemy, path)
        dist = self._calculate_distance_along_path(path, closest_idx, 0)
        return dist < t

    def is_close_to_end(self, enemy: 'Pokemon', path, threshold: float = None) -> bool:
        """Verifica se o Pokémon está perto do fim do path"""
        if not path:
            return False

        t = threshold if threshold is not None else self.threshold
        closest_idx = self._find_closest_path_point(enemy, path)
        dist = self._calculate_distance_along_path(path, closest_idx, len(path.points) - 1)
        return dist < t