# src/scenes/team_select_scene/managers/pokemon_manager.py

class PokemonManager:
    def __init__(self, player):
        self.player = player
        self.current_sort = "capture"
        self.current_filter = "all"
        self.current_search = ""

    def _apply_filters_and_sort(self, pokemon_list):
        """Aplica busca, filtro e ordenação a uma lista de dicionários."""
        filtered_list = pokemon_list

        # Filtro de shiny
        if self.current_filter == "shiny":
            filtered_list = [p for p in filtered_list if p.get("is_shiny", False)]
        elif self.current_filter == "normal":
            filtered_list = [p for p in filtered_list if not p.get("is_shiny", False)]

        # Busca por nome ou apelido
        if self.current_search:
            search_lower = self.current_search.lower()
            filtered_list = [
                p for p in filtered_list
                if search_lower in p.get("name", "").lower() or
                   (p.get("custom_name") and search_lower in p["custom_name"].lower())
            ]

        # Ordenação
        if self.current_sort == "name_asc":
            filtered_list.sort(key=lambda p: p.get("name", "").lower())
        elif self.current_sort == "name_desc":
            filtered_list.sort(key=lambda p: p.get("name", "").lower(), reverse=True)
        elif self.current_sort == "id_asc":
            filtered_list.sort(key=lambda p: p.get("id", 0))
        elif self.current_sort == "id_desc":
            filtered_list.sort(key=lambda p: p.get("id", 0), reverse=True)
        # "capture" mantém a ordem original

        return filtered_list

    def get_available_pokemon(self, page=0, items_per_page=30):
        all_pokemon = list(self.player.pc_box)  # já são dicts
        filtered_list = self._apply_filters_and_sort(all_pokemon)
        start_idx = page * items_per_page
        end_idx = start_idx + items_per_page
        return filtered_list[start_idx:end_idx]

    def get_page_count(self, items_per_page):
        all_pokemon = list(self.player.pc_box)
        filtered_list = self._apply_filters_and_sort(all_pokemon)
        if not filtered_list:
            return 1
        return max(1, (len(filtered_list) + items_per_page - 1) // items_per_page)

    def get_total_filtered_count(self):
        all_pokemon = list(self.player.pc_box)
        filtered_list = self._apply_filters_and_sort(all_pokemon)
        return len(filtered_list)

    def set_sort(self, sort_type):
        self.current_sort = sort_type

    def set_filter(self, filter_type):
        self.current_filter = filter_type

    def set_search(self, search_text):
        self.current_search = search_text

    def update_team_status(self):
        """Atualiza is_in_team nos Pokémon do time e na box."""
        team_ids = {p.unique_id for p in self.player.team}
        for pokemon in self.player.team:
            pokemon.is_in_team = True
        for data in self.player.pc_box:
            data["is_in_team"] = data.get("unique_id") in team_ids

    def add_to_team(self, pokemon_or_data):
        """
        Adiciona um Pokémon à equipe.
        Pode receber um objeto Pokemon ou um dicionário com os dados.
        """
        if len(self.player.team) >= 6:
            return False

        # Determina se é um objeto ou dict
        if hasattr(pokemon_or_data, 'unique_id'):  # é um objeto Pokemon
            pokemon = pokemon_or_data
            unique_id = pokemon.unique_id
        else:  # é um dict
            unique_id = pokemon_or_data["unique_id"]
            pokemon = self.player.get_pokemon_instance(unique_id)
            if not pokemon:
                return False

        # Remove da pc_box (se estiver lá)
        self.player.pc_box = [d for d in self.player.pc_box if d.get("unique_id") != unique_id]

        # Adiciona ao time
        self.player.team.append(pokemon)
        pokemon.is_in_team = True
        self.update_team_status()
        self.player.auto_save()
        return True

    def remove_from_team(self, pokemon):
        """Remove um Pokémon da equipe e o coloca na PC Box."""
        if pokemon not in self.player.team:
            return False

        # Remove do time
        self.player.team.remove(pokemon)
        pokemon.is_in_team = False

        # Converte para dict e adiciona à pc_box
        pokemon_dict = pokemon.to_dict()
        self.player.pc_box.append(pokemon_dict)

        # Mantém no cache (opcional)
        self.player._pokemon_cache[pokemon.unique_id] = pokemon

        self.update_team_status()
        self.player.auto_save()
        return True

    def release_pokemon(self, pokemon):
        """Liberta um Pokémon (remove do time e da box)."""
        if pokemon in self.player.team:
            self.player.team.remove(pokemon)
        # Remove da box (procurando por unique_id)
        self.player.pc_box = [d for d in self.player.pc_box if d.get("unique_id") != pokemon.unique_id]
        if pokemon.unique_id in self.player._pokemon_cache:
            del self.player._pokemon_cache[pokemon.unique_id]
        pokemon.is_in_team = False
        self.player.auto_save()
        return True