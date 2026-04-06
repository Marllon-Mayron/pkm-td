# src/scenes/team_select_scene/managers/pokemon_manager.py

class PokemonManager:
    def __init__(self, player):
        self.player = player
        self.current_sort = "capture"  # capture, name_asc, name_desc, id_asc, id_desc
        self.current_search = ""

    def _apply_filters_and_sort(self, pokemon_list):
        """Aplica busca e ordenação à lista de Pokémon"""
        # Aplica busca por nome
        filtered_list = pokemon_list
        if self.current_search:
            search_lower = self.current_search.lower()
            filtered_list = [
                p for p in filtered_list
                if search_lower in p.name.lower()
            ]

        # Aplica ordenação
        if self.current_sort == "name_asc":
            filtered_list.sort(key=lambda p: p.name.lower())
        elif self.current_sort == "name_desc":
            filtered_list.sort(key=lambda p: p.name.lower(), reverse=True)
        elif self.current_sort == "id_asc":
            filtered_list.sort(key=lambda p: p.id)
        elif self.current_sort == "id_desc":
            filtered_list.sort(key=lambda p: p.id, reverse=True)
        # "capture" mantém a ordem original

        return filtered_list

    def get_available_pokemon(self, page=0, items_per_page=30):
        """Retorna os pokémons da página atual com filtros aplicados"""
        all_pokemon = list(self.player.pc_box)
        filtered_list = self._apply_filters_and_sort(all_pokemon)

        start_idx = page * items_per_page
        end_idx = start_idx + items_per_page

        return filtered_list[start_idx:end_idx]

    def get_page_count(self, items_per_page):
        """Retorna o número total de páginas baseado na lista filtrada"""
        all_pokemon = list(self.player.pc_box)
        filtered_list = self._apply_filters_and_sort(all_pokemon)
        return max(1, (len(filtered_list) + items_per_page - 1) // items_per_page)

    def get_total_filtered_count(self):
        """Retorna o total de Pokémon após filtros"""
        all_pokemon = list(self.player.pc_box)
        filtered_list = self._apply_filters_and_sort(all_pokemon)
        return len(filtered_list)

    def set_sort(self, sort_type):
        """Define o tipo de ordenação"""
        print(f"PokemonManager.set_sort: {sort_type}")  # Debug
        self.current_sort = sort_type

    def set_search(self, search_text):
        """Define o texto de busca"""
        print(f"PokemonManager.set_search: '{search_text}'")  # Debug
        self.current_search = search_text

    def update_team_status(self):
        """Atualiza o status 'in_team' para todos os pokémons da box"""
        for pokemon in self.player.pc_box:
            pokemon.is_in_team = any(p is pokemon for p in self.player.team)

    def add_to_team(self, pokemon):
        """Adiciona um pokémon ao time"""
        if len(self.player.team) < 6:
            if pokemon in self.player.pc_box:
                success, _ = self.player.add_to_team(pokemon)
                if success:
                    pokemon.is_in_team = True
                    self.update_team_status()
                    self.player.auto_save()
                return success
        return False

    def remove_from_team(self, pokemon):
        """Remove um pokémon do time"""
        for i, p in enumerate(self.player.team):
            if p is pokemon:
                removed = self.player.remove_from_team(i)
                if removed:
                    pokemon.is_in_team = False
                    if pokemon not in self.player.pc_box:
                        self.player.pc_box.append(pokemon)
                    self.update_team_status()
                    self.player.auto_save()
                    return True
        return False