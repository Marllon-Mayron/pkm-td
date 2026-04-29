# src/scenes/minigames/survival/components/path_assignment.py
"""
Gerencia associação de paths (linhas) para Pokémon no minigame Survival
Estilo Plants vs Zombies - cada Pokémon ataca apenas inimigos na sua linha
"""
from typing import List, Optional, Tuple, Dict, Any, TYPE_CHECKING

if TYPE_CHECKING:
    from src.entities.pokemon import Pokemon


class PathAssignmentManager:
    """
    Gerencia a associação entre Pokémon e paths (linhas).

    Cada path tem uma coordenada Y característica (ex: 60, 108, 156, ...)
    Cada spot é associado ao path mais próximo verticalmente.
    Cada inimigo sabe qual path está percorrendo.

    Assim, aliados atacam apenas inimigos no mesmo path.
    """

    def __init__(self, game_scene):
        self.game_scene = game_scene
        self.path_y_coords: List[float] = []  # Y central de cada path
        self.path_index_by_y: Dict[float, int] = {}  # Y -> index do path
        self.spot_path_map: Dict[tuple, int] = {}  # (tile_x, tile_y) -> path_index

    def load_paths(self, paths) -> None:
        """
        Carrega os paths do level e extrai suas coordenadas Y características.

        Args:
            paths: Lista de paths do level_XX_XX.json
        """
        self.path_y_coords = []
        self.path_index_by_y = {}

        for idx, path in enumerate(paths):
            if hasattr(path, 'nodes') and path.nodes:
                # Pega o Y do primeiro nodo (ponto de entrada)
                first_node = path.nodes[0]
                y_coord = first_node[1] if isinstance(first_node, (list, tuple)) else first_node.y
                self.path_y_coords.append(float(y_coord))
                self.path_index_by_y[float(y_coord)] = idx
            elif isinstance(path, dict) and 'nodes' in path:
                first_node = path['nodes'][0]
                y_coord = first_node[1] if isinstance(first_node, (list, tuple)) else first_node['y']
                self.path_y_coords.append(float(y_coord))
                self.path_index_by_y[float(y_coord)] = idx
            elif hasattr(path, 'start_point') and path.start_point:
                y_coord = path.start_point[1] if isinstance(path.start_point, (list, tuple)) else path.start_point.y
                self.path_y_coords.append(float(y_coord))
                self.path_index_by_y[float(y_coord)] = idx

        print(f"[PathAssignment] Carregados {len(self.path_y_coords)} paths com Ys: {self.path_y_coords}")

    def register_spot(self, spot_x: float, spot_y: float, tile_size: int = 24) -> Optional[int]:
        """
        Registra um spot de torre e associa ao path mais próximo.

        Args:
            spot_x: Posição X do spot
            spot_y: Posição Y do spot
            tile_size: Tamanho do tile (para obter coordenada central)

        Returns:
            path_index se encontrado, None caso contrário
        """
        # Calcula o tile Y
        tile_y = spot_y // tile_size

        # Encontra o path mais próximo verticalmente
        best_path_idx = None
        best_distance = float('inf')

        for path_idx, path_y in enumerate(self.path_y_coords):
            distance = abs(spot_y - path_y)
            if distance < best_distance:
                best_distance = distance
                best_path_idx = path_idx

        if best_path_idx is not None:
            # Guarda mapeamento por coordenada do tile
            self.spot_path_map[(spot_x // tile_size, tile_y)] = best_path_idx
            print(
                f"[PathAssignment] Spot ({spot_x}, {spot_y}) associado ao path {best_path_idx} (Y={self.path_y_coords[best_path_idx]}, dist={best_distance:.0f})")
            return best_path_idx

        return None

    def get_path_for_spot(self, spot_x: float, spot_y: float, tile_size: int = 24) -> Optional[int]:
        """Retorna o path index para um spot baseado em sua posição"""
        tile_x = spot_x // tile_size
        tile_y = spot_y // tile_size
        return self.spot_path_map.get((tile_x, tile_y))

    def get_path_for_pokemon(self, pokemon) -> Optional[int]:
        """Retorna o path index para um Pokémon aliado baseado em seu spot de origem"""
        if not pokemon or not hasattr(pokemon, 'is_placed') or not pokemon.is_placed:
            return None

        if hasattr(pokemon, 'assigned_path_index'):
            return pokemon.assigned_path_index

        # Fallback: tenta obter pela posição do spot
        if hasattr(pokemon, 'placed_tile_x') and hasattr(pokemon, 'placed_tile_y'):
            return self.spot_path_map.get((pokemon.placed_tile_x, pokemon.placed_tile_y))

        return None

    def get_path_for_enemy(self, enemy) -> Optional[int]:
        """Retorna o path index para um inimigo"""
        if not enemy:
            return None

        if hasattr(enemy, '_assigned_path_index'):
            return enemy._assigned_path_index

        # Tenta determinar pelo path que está seguindo
        if hasattr(enemy, 'path') and enemy.path:
            # Pega o Y do primeiro ponto do path
            if enemy.path and len(enemy.path) > 0:
                first_y = enemy.path[0][1] if isinstance(enemy.path[0], (list, tuple)) else enemy.path[0].y

                # Encontra qual path tem esse Y
                for path_idx, path_y in enumerate(self.path_y_coords):
                    if abs(first_y - path_y) < 10:  # Tolerância de 10 pixels
                        enemy._assigned_path_index = path_idx
                        return path_idx

        return None

    def assign_path_to_enemy(self, enemy, path_idx: int) -> None:
        """Atribui um path a um inimigo"""
        enemy._assigned_path_index = path_idx

    def get_enemies_in_same_path(self, pokemon, all_enemies: List) -> List:
        """
        Retorna apenas os inimigos que estão no mesmo path que o Pokémon.
        """
        pokemon_path = self.get_path_for_pokemon(pokemon)
        if pokemon_path is None:
            # Se não tem path associado, retorna todos (fallback)
            return [e for e in all_enemies if e.is_alive() and not e.is_defeated]

        enemies_in_path = []
        for enemy in all_enemies:
            if not enemy.is_alive() or enemy.is_defeated:
                continue
            enemy_path = self.get_path_for_enemy(enemy)
            if enemy_path == pokemon_path:
                enemies_in_path.append(enemy)

        return enemies_in_path

    def get_closest_enemy_in_path(self, pokemon, all_enemies: List) -> Optional['Pokemon']:
        """Retorna o inimigo mais próximo no mesmo path"""
        pokemon_path = self.get_path_for_pokemon(pokemon)
        if pokemon_path is None:
            return None

        closest = None
        min_distance = float('inf')

        for enemy in all_enemies:
            if not enemy.is_alive() or enemy.is_defeated:
                continue
            enemy_path = self.get_path_for_enemy(enemy)
            if enemy_path == pokemon_path:
                dx = enemy.x - pokemon.x
                dy = enemy.y - pokemon.y
                distance = dx * dx + dy * dy
                if distance < min_distance:
                    min_distance = distance
                    closest = enemy

        return closest

    def is_enemy_in_range_and_path(self, pokemon, enemy) -> bool:
        """Verifica se o inimigo está no range E no mesmo path"""
        if not enemy.is_alive() or enemy.is_defeated:
            return False

        pokemon_path = self.get_path_for_pokemon(pokemon)
        if pokemon_path is None:
            # Fallback: comportamento original
            dx = enemy.x - pokemon.x
            dy = enemy.y - pokemon.y
            return dx * dx + dy * dy <= pokemon.attack_range * pokemon.attack_range

        enemy_path = self.get_path_for_enemy(enemy)
        if enemy_path != pokemon_path:
            return False

        dx = enemy.x - pokemon.x
        dy = enemy.y - pokemon.y
        return dx * dx + dy * dy <= pokemon.attack_range * pokemon.attack_range