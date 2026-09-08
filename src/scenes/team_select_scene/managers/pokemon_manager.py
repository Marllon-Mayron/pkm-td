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
        """Retorna a lista de Pokémon disponíveis (sempre do cache atualizado)"""
        # Garante que os dados estão atualizados antes de retornar
        all_pokemon = list(self.player.pc_box)

        # Atualiza is_in_team para todos os Pokémon na box
        team_ids = {p.unique_id for p in self.player.team}
        for data in all_pokemon:
            unique_id = data.get("unique_id")
            if unique_id:
                data["is_in_team"] = unique_id in team_ids
                # Se tiver no cache, usa os dados mais recentes
                if unique_id in self.player._pokemon_cache:
                    cached = self.player._pokemon_cache[unique_id]
                    data["name"] = cached.name
                    data["id"] = cached.id
                    data["level"] = cached.level
                    data["types"] = cached.types.copy()

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

    def refresh_all_pokemon_data(self):
        """
        Força a atualização de todos os dados dos Pokémon na box.
        Deve ser chamado quando voltar do GameScene para garantir que
        evoluções, capturas e mudanças de status sejam refletidas.
        """
        # ===== 1. ATUALIZA O STATUS DE TIME =====
        team_ids = {p.unique_id for p in self.player.team}

        # Atualiza objetos no time
        for pokemon in self.player.team:
            pokemon.is_in_team = True

        # Atualiza dicionários na box
        for data in self.player.pc_box:
            unique_id = data.get("unique_id")
            if unique_id:
                data["is_in_team"] = unique_id in team_ids

        # ===== 2. ATUALIZA O CACHE DE INSTÂNCIAS =====
        # Remove instâncias que não estão mais no time nem na box
        team_ids_set = team_ids
        box_ids = {data.get("unique_id") for data in self.player.pc_box if data.get("unique_id")}
        valid_ids = team_ids_set | box_ids

        # Remove do cache os que não são mais válidos
        for unique_id in list(self.player._pokemon_cache.keys()):
            if unique_id not in valid_ids:
                del self.player._pokemon_cache[unique_id]

        # Atualiza os que estão no cache
        for unique_id, pokemon in self.player._pokemon_cache.items():
            pokemon.is_in_team = unique_id in team_ids_set

        # ===== 3. ATUALIZA OS DICIONÁRIOS DA BOX COM OS DADOS MAIS RECENTES =====
        for data in self.player.pc_box:
            unique_id = data.get("unique_id")
            if unique_id and unique_id in self.player._pokemon_cache:
                cached_pokemon = self.player._pokemon_cache[unique_id]
                # Sincroniza os dados do cache para o dict
                data["id"] = cached_pokemon.id
                data["name"] = cached_pokemon.name
                data["level"] = cached_pokemon.level
                data["xp"] = cached_pokemon.xp
                data["types"] = cached_pokemon.types.copy()
                data["base_stats"] = cached_pokemon.base_stats.copy()
                data["max_hp"] = cached_pokemon.max_hp
                data["attack"] = cached_pokemon.attack
                data["defense"] = cached_pokemon.defense
                data["sp_attack"] = cached_pokemon.sp_attack
                data["sp_defense"] = cached_pokemon.sp_defense
                data["speed"] = cached_pokemon.speed_stat
                data["happiness"] = cached_pokemon.happiness
                data["moves"] = [
                    {
                        "name": move.name,
                        "current_pp": move.current_pp,
                        "max_pp": move.max_pp,
                        "type": move.type,
                        "power": move.power,
                        "accuracy": move.accuracy,
                        "category": move.category,
                    }
                    for move in cached_pokemon.moves
                ]

        # ===== 4. ATUALIZA OS POKEMON QUE ESTÃO NO TIME MAS NÃO NO CACHE =====
        for pokemon in self.player.team:
            if pokemon.unique_id not in self.player._pokemon_cache:
                self.player._pokemon_cache[pokemon.unique_id] = pokemon

        # ===== 5. SALVA O JOGO =====
        self.player.auto_save()

        print(
            f"[REFRESH] Dados atualizados: {len(self.player.team)} no time, {len(self.player.pc_box)} na box, {len(self.player._pokemon_cache)} em cache")

    def update_team_status(self):
        """Atualiza is_in_team nos Pokémon do time e na box."""
        team_ids = {p.unique_id for p in self.player.team}

        # Atualiza os objetos no time
        for pokemon in self.player.team:
            pokemon.is_in_team = True

        # Atualiza os dicionários na box
        for data in self.player.pc_box:
            unique_id = data.get("unique_id")
            if unique_id:
                data["is_in_team"] = unique_id in team_ids

        # ===== Atualiza também o cache de instâncias =====
        for unique_id, pokemon in self.player._pokemon_cache.items():
            if hasattr(pokemon, 'is_in_team'):
                pokemon.is_in_team = unique_id in team_ids

    def add_to_team(self, pokemon_or_data):
        """Adiciona um Pokémon à equipe."""
        if len(self.player.team) >= 6:
            return False

        if hasattr(pokemon_or_data, 'unique_id'):
            pokemon = pokemon_or_data
            unique_id = pokemon.unique_id
        else:
            unique_id = pokemon_or_data["unique_id"]
            pokemon = self.player.get_pokemon_instance(unique_id)
            if not pokemon:
                return False

        # Remove da pc_box (se estiver lá)
        self.player.pc_box = [d for d in self.player.pc_box if d.get("unique_id") != unique_id]

        # Adiciona ao time
        self.player.team.append(pokemon)
        pokemon.is_in_team = True

        # ===== Atualiza o cache também =====
        self.player._pokemon_cache[unique_id] = pokemon

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

        # ===== VERIFICA SE JÁ EXISTE NA BOX (evita duplicação) =====
        already_in_box = any(d.get("unique_id") == pokemon.unique_id for d in self.player.pc_box)
        if not already_in_box:
            # Converte para dict e adiciona à pc_box
            pokemon_dict = pokemon.to_dict()
            self.player.pc_box.append(pokemon_dict)

        # Mantém no cache
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

        # Remove do cache
        if pokemon.unique_id in self.player._pokemon_cache:
            del self.player._pokemon_cache[pokemon.unique_id]

        pokemon.is_in_team = False
        self.player.auto_save()
        return True

    def sync_pokemon_in_box(self, pokemon):
        """
        Sincroniza os dados de um Pokémon na box após uma evolução.
        """
        unique_id = pokemon.unique_id

        for data in self.player.pc_box:
            if data.get("unique_id") == unique_id:
                # Atualiza todos os campos relevantes
                data["id"] = pokemon.id
                data["name"] = pokemon.name
                data["types"] = pokemon.types.copy()
                data["base_stats"] = pokemon.base_stats.copy()
                data["max_hp"] = pokemon.max_hp
                data["attack"] = pokemon.attack
                data["defense"] = pokemon.defense
                data["sp_attack"] = pokemon.sp_attack
                data["sp_defense"] = pokemon.sp_defense
                data["speed"] = pokemon.speed_stat
                data["level"] = pokemon.level
                data["xp"] = pokemon.xp
                data["moves"] = [
                    {
                        "name": move.name,
                        "current_pp": move.current_pp,
                        "max_pp": move.max_pp,
                        "type": move.type,
                        "power": move.power,
                        "accuracy": move.accuracy,
                        "category": move.category,
                    }
                    for move in pokemon.moves
                ]
                # Mantém o unique_id, is_shiny, etc
                print(f"[SYNC] Box atualizada para {pokemon.name} (ID: {pokemon.id})")
                return True
        return False

    def get_pokemon_from_box(self, unique_id):
        """Retorna o dicionário do Pokémon na box"""
        for data in self.player.pc_box:
            if data.get("unique_id") == unique_id:
                return data
        return None