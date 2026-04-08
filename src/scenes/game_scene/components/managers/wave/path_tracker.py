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
        """
        state = self._enemy_state.get(id(enemy))
        if not state:
            return False, False

        # ===== VERIFICA SE O INIMIGO DEVE PARAR DE SEGUIR O ALVO =====
        should_abandon_target = False

        if hasattr(enemy, 'target') and enemy.target:
            # Caso 1: Alvo morreu
            if not enemy.target.is_alive() or enemy.target.is_defeated:
                should_abandon_target = True
                print(f"[PathTracker] {enemy.name}: alvo {enemy.target.name} morreu! Abandonando perseguição.")

            # Caso 2: Alvo está muito longe (fora do range de ataque * 2)
            else:
                dx = enemy.target.x - enemy.x
                dy = enemy.target.y - enemy.y
                distance_to_target = math.hypot(dx, dy)

                # Se o alvo está muito longe (mais que 2x o range de ataque)
                if distance_to_target > enemy.attack_range * 2:
                    should_abandon_target = True
                    print(
                        f"[PathTracker] {enemy.name}: alvo {enemy.target.name} muito longe ({distance_to_target:.0f} > {enemy.attack_range * 2:.0f})! Abandonando perseguição.")

            # Caso 3: Inimigo está tentando atacar há muito tempo sem sucesso
            if hasattr(enemy, '_attack_attempts') and enemy._attack_attempts > 5:
                should_abandon_target = True
                print(f"[PathTracker] {enemy.name}: muitas tentativas de ataque sem sucesso! Abandonando perseguição.")
                enemy._attack_attempts = 0

        # Se deve abandonar o alvo, limpa o target e reseta o timer de ignorar path
        if should_abandon_target:
            enemy.target = None
            state['ignore_path_timer'] = 0.0
            state['combat_target'] = None
            # Reseta estado de combate
            enemy.combat_state = "idle"
            if hasattr(enemy, '_attack_attempts'):
                enemy._attack_attempts = 0
            # Força voltar a seguir o path
            print(f"[PathTracker] {enemy.name}: voltando ao path normal!")
            return False, False

        # ===== VERIFICA SE DEVE IGNORAR O PATH (EM COMBATE ATIVO) =====
        is_in_combat = False

        # Verifica se o inimigo tem um alvo de combate válido
        if hasattr(enemy, 'target') and enemy.target and enemy.target.is_alive():
            is_in_combat = True

            # Calcula distância até o alvo
            dx = enemy.target.x - enemy.x
            dy = enemy.target.y - enemy.y
            distance_to_target = math.hypot(dx, dy)

            # Obtém o move atual para saber o range necessário
            current_move = None
            if hasattr(enemy, 'get_current_move_for_pattern'):
                current_move = enemy.get_current_move_for_pattern()
            elif hasattr(enemy, 'get_current_move'):
                current_move = enemy.get_current_move()

            # Define o range de ataque baseado no tipo de move
            if current_move and current_move.category == "physical":
                required_range = 25  # Distância para ataque físico
            else:
                required_range = enemy.attack_range

            # Se está perto do alvo (dentro do range) ou em animação de ataque, ignora o path
            is_attacking = hasattr(enemy, '_attack_animation_active') and enemy._attack_animation_active

            if distance_to_target < required_range or is_attacking:
                # Mantém ou aumenta o tempo de ignorar path
                state['ignore_path_timer'] = max(state['ignore_path_timer'], 0.5)
                state['combat_target'] = enemy.target
            else:
                # Alvo está longe, não vale a pena perseguir
                # Reseta o timer e limpa o target
                state['ignore_path_timer'] = 0.0
                target_name = enemy.target.name if enemy.target else "None"
                print(
                    f"[PathTracker] {enemy.name}: alvo {target_name} está longe ({distance_to_target:.0f}), voltando ao path.")
                enemy.target = None
                is_in_combat = False

        # Atualiza o timer de ignorar path
        if state['ignore_path_timer'] > 0:
            state['ignore_path_timer'] -= dt

            # Se ainda está ignorando path, NÃO processa movimento do path
            if state['ignore_path_timer'] > 0:
                return False, False

        # Se chegou aqui, NÃO está ignorando path
        # Limpa o alvo se ainda existir (pois não estamos mais em combate)
        if enemy.target:
            print(f"[PathTracker] {enemy.name}: saindo do modo combate, limpando alvo {enemy.target.name}")
            enemy.target = None
            enemy.combat_state = "idle"

        state['combat_target'] = None

        # Cooldown de spawn
        if state['spawn_cooldown'] > 0:
            state['spawn_cooldown'] -= dt

        # Verifica status que impedem movimento (paralisia, sono, congelamento)
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

        # CORREÇÃO: Verifica se está no primeiro ponto (INÍCIO)
        if enemy.path_index == 0:
            target_x, target_y = enemy.path[enemy.path_index]
            dx = target_x - enemy.x
            dy = target_y - enemy.y
            dist_to_start = math.hypot(dx, dy)

            if dist_to_start < self.ARRIVAL_THRESHOLD:
                if state['spawn_cooldown'] <= 0 and state['just_reversed_cooldown'] <= 0:
                    if not state['has_reached_start'] and state['arrival_cooldown'] <= 0:
                        state['has_reached_start'] = True
                        state['arrival_cooldown'] = 0.1
                        print(f"[PathTracker] {enemy.name} chegou ao INÍCIO!")
                        return False, True

        # CORREÇÃO: Verifica se está no último ponto (FIM)
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

            # CORREÇÃO: Verifica chegada ao INÍCIO (depois de passar do primeiro ponto para trás)
            elif enemy.path_index < 0:
                if state['spawn_cooldown'] <= 0 and state['just_reversed_cooldown'] <= 0:
                    if not state['has_reached_start'] and state['arrival_cooldown'] <= 0:
                        state['has_reached_start'] = True
                        state['arrival_cooldown'] = 0.1
                        print(f"[PathTracker] {enemy.name} chegou ao INÍCIO!")
                        return False, True

        else:
            # Move em direção ao ponto
            move_x = (dx / distance) * move_distance
            move_y = (dy / distance) * move_distance
            enemy.x += move_x
            enemy.y += move_y
            enemy.rect.x, enemy.rect.y = enemy.x, enemy.y

            state['distance_traveled'] += move_distance
            state['last_pos'] = (enemy.x, enemy.y)

            # Atualiza direção baseada no movimento (8 direções)
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
        O inimigo deve andar de volta pelo MESMO caminho.
        """
        if not enemy.original_path:
            print(f"[PathTracker] {enemy.name} não tem original_path!")
            return

        state = self._enemy_state.get(id(enemy))
        if not state:
            return

        original = enemy.original_path.copy()
        enemy.path = list(reversed(original))

        if len(enemy.path) > 1:
            enemy.path_index = 1
        else:
            enemy.path_index = 0

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

        reversed_points = list(reversed(enemy.original_path.copy()))
        enemy.path = reversed_points

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
        print(f"[PathTracker] {enemy.name} (BOSS={enemy.is_boss}) REVERTEU PATH. Agora: {direction}. "
              f"Pos: ({enemy.x:.0f}, {enemy.y:.0f}), path_index: {enemy.path_index}/{len(enemy.path)}")

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