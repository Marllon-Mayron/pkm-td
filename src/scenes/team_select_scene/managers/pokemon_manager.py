# src/scenes/team_select_scene/managers/pokemon_manager.py

class PokemonManager:
    def __init__(self, player):
        self.player = player

    def get_available_pokemon(self, page=0, items_per_page=30):
        """Retorna os pokémons da página atual (da pc_box)"""
        start_idx = page * items_per_page
        end_idx = start_idx + items_per_page

        # Retorna um slice da pc_box
        return list(self.player.pc_box)[start_idx:end_idx]

    def get_page_count(self, items_per_page):
        """Retorna o número total de páginas baseado na pc_box"""
        return max(1, (len(self.player.pc_box) + items_per_page - 1) // items_per_page)

    def update_team_status(self):
        """Atualiza o status 'in_team' para todos os pokémons da box"""
        team_ids = [id(p) for p in self.player.team]  # Usa id() para comparação segura
        for pokemon in self.player.pc_box:
            # Verifica se está no time comparando objetos
            pokemon.is_in_team = any(p is pokemon for p in self.player.team)

    def add_to_team(self, pokemon):
        """Adiciona um pokémon ao time"""
        if len(self.player.team) < 6:
            # Verifica se o Pokémon está na box
            if pokemon in self.player.pc_box:
                success, _ = self.player.add_to_team(pokemon)
                if success:
                    pokemon.is_in_team = True
                    self.update_team_status()
                    self.player.auto_save()
                return success
            else:
                print(f"[ERRO] {pokemon.name} não está na PC Box!")
        return False

    def remove_from_team(self, pokemon):
        """Remove um pokémon do time"""
        for i, p in enumerate(self.player.team):
            if p is pokemon:  # Comparação de identidade
                removed = self.player.remove_from_team(i)
                if removed:
                    pokemon.is_in_team = False

                    # GARANTE que o Pokémon está na box
                    if pokemon not in self.player.pc_box:
                        self.player.pc_box.append(pokemon)

                    self.update_team_status()
                    self.player.auto_save()
                    return True
        return False