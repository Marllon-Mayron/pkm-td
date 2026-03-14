import random
from src.entities.pokemon import Pokemon


class PokemonManager:
    def __init__(self, player):
        self.player = player
        self.available_pokemon = []

    def load_available_pokemon(self, limit=30):
        """Carrega a lista de pokémons disponíveis"""
        self.available_pokemon = []

        # Pokémons de teste (1-151)
        for poke_id in range(1, min(limit + 1, 152)):
            self._add_test_pokemon(poke_id)

        # Adiciona da box do jogador
        for pokemon in self.player.pc_box:
            self.available_pokemon.append(pokemon)

        return self.available_pokemon

    def _add_test_pokemon(self, poke_id):
        """Adiciona um pokémon de teste"""
        already_in_team = any(p.id == poke_id for p in self.player.team)

        pokemon = Pokemon(
            x=0, y=0,
            pokemon_id=poke_id,
            level=random.randint(5, 20),
            is_wild=False,
            shiny=random.random() < 0.05
        )

        if already_in_team:
            pokemon.is_in_team = True

        self.available_pokemon.append(pokemon)

    def update_team_status(self):
        """Atualiza o status 'in_team' para todos os pokémons"""
        team_ids = [p.id for p in self.player.team]
        for pokemon in self.available_pokemon:
            pokemon.is_in_team = pokemon.id in team_ids

    def get_page_count(self, items_per_page):
        """Retorna o número total de páginas"""
        return max(1, (len(self.available_pokemon) + items_per_page - 1) // items_per_page)

    def add_to_team(self, pokemon):
        """Adiciona um pokémon ao time"""
        if len(self.player.team) < 6:
            success, _ = self.player.add_to_team(pokemon)
            if success:
                pokemon.is_in_team = True
            return success
        return False

    def remove_from_team(self, pokemon):
        """Remove um pokémon do time"""
        for i, p in enumerate(self.player.team):
            if p == pokemon:
                self.player.remove_from_team(i)
                pokemon.is_in_team = False
                return True
        return False