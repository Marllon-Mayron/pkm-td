# src/managers/wave/item_decision.py

import math
from typing import Optional, List, Tuple
from enum import Enum


class DirectionDecision(Enum):
    """Decisão de direção após capturar item"""
    CONTINUE = "continue"  # Continua na mesma direção
    REVERSE = "reverse"  # Volta para o início


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
        - Boss: sempre continua (vai até o fim e depois volta)
        - Comum: calcula qual direção é mais vantajosa baseado na posição atual
        """
        if not path:
            return DirectionDecision.CONTINUE

        if enemy.is_boss:
            return DirectionDecision.CONTINUE

        # ===== CORREÇÃO: Calcula distâncias considerando o path =====
        # Encontra o ponto mais próximo no path
        current_point_idx = self._find_closest_path_point(enemy, path)

        # Calcula distância percorrida até o fim (seguindo o path)
        dist_to_end = self._calculate_distance_along_path(path, current_point_idx, len(path.points) - 1)

        # Calcula distância percorrida até o início (seguindo o path)
        dist_to_start = self._calculate_distance_along_path(path, current_point_idx, 0)

        # Se está mais perto do fim, continua; senão, volta
        if dist_to_end <= dist_to_start:
            print(
                f"[ItemDecision] {enemy.name}: dist_to_end={dist_to_end:.1f}, dist_to_start={dist_to_start:.1f} -> CONTINUE")
            return DirectionDecision.CONTINUE
        else:
            print(
                f"[ItemDecision] {enemy.name}: dist_to_end={dist_to_end:.1f}, dist_to_start={dist_to_start:.1f} -> REVERSE")
            return DirectionDecision.REVERSE

    def _find_closest_path_point(self, enemy: 'Pokemon', path) -> int:
        """
        Encontra o índice do ponto do path mais próximo do Pokémon.
        """
        min_dist = float('inf')
        closest_idx = 0

        for i, point in enumerate(path.points):
            dist = math.hypot(enemy.x - point[0], enemy.y - point[1])
            if dist < min_dist:
                min_dist = dist
                closest_idx = i

        return closest_idx

    def _calculate_distance_along_path(self, path, from_idx: int, to_idx: int) -> float:
        """
        Calcula a distância percorrida ao longo do path do índice from_idx até to_idx.
        """
        if from_idx == to_idx:
            return 0.0

        # Determina direção do percurso
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

        # Encontra o ponto mais próximo
        closest_idx = self._find_closest_path_point(enemy, path)

        # Calcula distância até o início seguindo o path
        dist = self._calculate_distance_along_path(path, closest_idx, 0)

        return dist < t

    def is_close_to_end(self, enemy: 'Pokemon', path, threshold: float = None) -> bool:
        """Verifica se o Pokémon está perto do fim do path"""
        if not path:
            return False

        t = threshold if threshold is not None else self.threshold

        # Encontra o ponto mais próximo
        closest_idx = self._find_closest_path_point(enemy, path)

        # Calcula distância até o fim seguindo o path
        dist = self._calculate_distance_along_path(path, closest_idx, len(path.points) - 1)

        return dist < t