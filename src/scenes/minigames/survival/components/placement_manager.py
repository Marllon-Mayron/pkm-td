# src/scenes/minigames/survival/components/placement_manager.py
"""
Gerenciador de colocação de Pokémon para o minigame survival
"""
from typing import List, Optional, Any


class SurvivalPlacementManager:
    """Gerencia os Pokémon colocados no mapa durante o minigame"""

    def __init__(self, game_scene):
        self.game_scene = game_scene
        self.placed_pokemon: List[Any] = []
        self.tile_size = 24

    def add_pokemon(self, pokemon, spot):
        """Adiciona um Pokémon ao mapa e associa ao path correto"""
        if pokemon not in self.placed_pokemon:
            self.placed_pokemon.append(pokemon)

            # ===== ASSOCIA AO PATH BASEADO NO SPOT =====
            if hasattr(self.game_scene, 'path_assignment'):
                path_idx = self.game_scene.path_assignment.get_path_for_spot(spot.x, spot.y, self.tile_size)
                if path_idx is not None:
                    pokemon.assigned_path_index = path_idx
                    print(f"[Placement] {pokemon.name} associado ao path {path_idx}")

            print(f"[Placement] {pokemon.name} adicionado à lista")

    def remove_pokemon(self, pokemon):
        """Remove um Pokémon do mapa"""
        if pokemon in self.placed_pokemon:
            self.placed_pokemon.remove(pokemon)
            print(f"[Placement] {pokemon.name} removido da lista")

            # ===== CORREÇÃO: DESOCUPA O SPOT =====
            if hasattr(pokemon, 'placed_tile_x') and hasattr(pokemon, 'placed_tile_y'):
                pokemon_tile_x = pokemon.placed_tile_x
                pokemon_tile_y = pokemon.placed_tile_y
            else:
                pokemon_tile_x = pokemon.x // self.tile_size
                pokemon_tile_y = pokemon.y // self.tile_size

            # Procura e desocupa o spot correspondente
            if hasattr(self.game_scene, 'spot_renderer'):
                for spot in self.game_scene.spot_renderer.get_spots():
                    spot_tile_x = spot.x // self.tile_size
                    spot_tile_y = spot.y // self.tile_size

                    if spot_tile_x == pokemon_tile_x and spot_tile_y == pokemon_tile_y:
                        spot.occupied = False
                        print(f"[Placement] Spot ({spot.x}, {spot.y}) desocupado")
                        break

    def get_pokemon_at_world_pos(self, world_x: float, world_y: float, tolerance: int = 20):
        """Retorna o Pokémon na posição do mundo"""
        tolerance_sq = tolerance * tolerance
        for pokemon in self.placed_pokemon:
            dx = pokemon.x - world_x
            dy = pokemon.y - world_y
            if dx * dx + dy * dy < tolerance_sq:
                return pokemon
        return None

    def clear(self):
        """Remove todos os Pokémon"""
        self.placed_pokemon.clear()

    def update(self, dt: float, enemies: List):
        """Atualiza todos os Pokémon colocados"""
        for pokemon in self.placed_pokemon[:]:
            # Atualiza o Pokémon
            pokemon.update(dt, enemies=enemies)

            # Atualiza combate se vivo
            if pokemon.is_alive():
                pokemon.update_combat(dt, enemies)

    def render(self, screen, camera, screen_manager):
        """Renderiza todos os Pokémon"""
        for pokemon in self.placed_pokemon:
            pokemon.render(screen, camera, show_hp=True)