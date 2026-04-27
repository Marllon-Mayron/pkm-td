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
        """Adiciona um Pokémon ao mapa"""
        if pokemon not in self.placed_pokemon:
            self.placed_pokemon.append(pokemon)
            print(f"[Placement] {pokemon.name} adicionado à lista")

    def remove_pokemon(self, pokemon):
        """Remove um Pokémon do mapa"""
        if pokemon in self.placed_pokemon:
            self.placed_pokemon.remove(pokemon)
            print(f"[Placement] {pokemon.name} removido da lista")

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