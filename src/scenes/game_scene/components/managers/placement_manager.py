# src/scenes/game_scene/components/managers/placement_manager.py

class PlacementManager:
    """Gerencia os Pokémon colocados no mapa"""

    def __init__(self, game):
        self.game = game
        self.placed_pokemon = []  # Lista de Pokémon no mapa

    def add_pokemon(self, spot, pokemon):
        """Adiciona um Pokémon no spot"""
        # Verifica se já tem Pokémon neste spot
        existing = self.get_pokemon_at_spot(spot)
        if existing:
            print(f"[PLACEMENT] Spot já ocupado por {existing.name}")
            return None

        # Cria uma nova instância do Pokémon no mapa
        from src.entities.pokemon import Pokemon
        placed = Pokemon(
            spot.x,  # Usa a posição exata do spot
            spot.y,
            pokemon.id,
            level=pokemon.level,
            is_wild=False
        )

        # Copia atributos importantes
        placed.current_hp = pokemon.current_hp
        placed.max_hp = pokemon.max_hp
        placed.ivs = pokemon.ivs
        placed.evs = pokemon.evs
        placed.is_shiny = pokemon.is_shiny
        placed.screen_manager = self.game.screen_manager

        # Marca como colocado
        placed.is_placed = True
        placed.spot_id = id(spot)  # Identificador único do spot

        # Marca o spot como ocupado
        spot.occupied = True

        self.placed_pokemon.append(placed)
        print(f"[PLACEMENT] {pokemon.name} colocado no spot ({spot.x}, {spot.y})")
        return placed

    def remove_pokemon(self, pokemon):
        """Remove um Pokémon do mapa"""
        if pokemon in self.placed_pokemon:
            self.placed_pokemon.remove(pokemon)
            # Procura o spot correspondente e desocupa
            for spot in self._get_all_spots():
                if abs(spot.x - pokemon.x) < 10 and abs(spot.y - pokemon.y) < 10:
                    spot.occupied = False
                    break
            print(f"[PLACEMENT] {pokemon.name} removido do mapa")

    def get_pokemon_at_spot(self, spot):
        """Verifica se já existe um Pokémon no spot"""
        for pokemon in self.placed_pokemon:
            if abs(pokemon.x - spot.x) < 10 and abs(pokemon.y - spot.y) < 10:
                return pokemon
        return None

    def get_pokemon_at_world_pos(self, world_x, world_y, tolerance=20):
        """Retorna o Pokémon na posição do mundo (para seleção)"""
        for pokemon in self.placed_pokemon:
            distance = ((pokemon.x - world_x) ** 2 + (pokemon.y - world_y) ** 2) ** 0.5
            if distance < tolerance:
                return pokemon
        return None

    def _get_all_spots(self):
        """Método auxiliar para pegar todos os spots (será sobrescrito)"""
        return []

    def update(self, dt, enemies):
        """Atualiza todos os Pokémon colocados"""
        for pokemon in self.placed_pokemon:
            pokemon.update(dt)
            # TODO: Adicionar lógica de ataque dos Pokémon aqui
            # Por enquanto, só atualiza animação

    def render(self, screen, camera, screen_manager):
        """Renderiza todos os Pokémon colocados"""
        for pokemon in self.placed_pokemon:
            pokemon.render(screen, camera, show_hp=True)

    def clear(self):
        """Remove todos os Pokémon do mapa"""
        self.placed_pokemon.clear()