# src/entities/pokemon/evolution.py


class PokemonEvolution:
    """Gerencia evolução do Pokémon"""

    def __init__(self, pokemon):
        self.pokemon = pokemon

    def check_and_evolve(self):
        from src.managers.evolution_manager import evolution_manager

        evolution = evolution_manager.check_evolution(self.pokemon.id, current_level=self.pokemon.level)

        if evolution:
            evolve_to_id = evolution["evolve_to"]
            self._perform_evolution(evolve_to_id)
            return True
        return False

    def _perform_evolution(self, new_id):
        """Realiza a evolução mantendo os moves compatíveis"""
        old_name = self.pokemon.name
        old_level = self.pokemon.level

        new_pokemon_data = self.pokemon.pokedex.get_pokemon(new_id)
        if not new_pokemon_data:
            return

        self.pokemon.id = new_id
        self.pokemon.name = new_pokemon_data["name"].capitalize()
        self.pokemon.types = new_pokemon_data["types"]
        self.pokemon.base_stats = new_pokemon_data["base_stats"]

        self.pokemon._calculate_stats()
        self.pokemon.current_hp = self.pokemon.max_hp

        self.pokemon._load_sprites(new_id, self.pokemon.is_shiny)
        self.pokemon.map_sprite_size = self.pokemon.pokedex.get_map_sprite_size(new_id, self.pokemon.is_shiny)

        new_learnset = set(self.pokemon.move_data.get_moves_at_level(self.pokemon.id, self.pokemon.level))
        current_move_names = set(move.name.lower() for move in self.pokemon.moves)
        moves_to_learn = new_learnset - current_move_names

        for move_name in moves_to_learn:
            self.pokemon._learn_move_without_replacement(move_name)

        print(f"[EVOLUÇÃO] ✓ {old_name} (Lv.{old_level}) evoluiu para {self.pokemon.name}!")
        print(f"[EVOLUÇÃO] Moves atuais: {[m.name for m in self.pokemon.moves]}")

    def gain_xp(self, amount):
        """Ganha XP e verifica level up/evolução"""
        old_level = self.pokemon.level
        self.pokemon.xp += amount

        leveled_up = False
        while self.pokemon.xp >= self.pokemon.xp_to_next:
            self.level_up()
            leveled_up = True

        if leveled_up:
            self.pokemon.attack_damage = self.pokemon._calculate_attack_damage()
            self.pokemon.defense_value = self.pokemon._calculate_defense()

            from src.managers.evolution_manager import evolution_manager
            evolution = evolution_manager.check_evolution(self.pokemon.id, current_level=self.pokemon.level)
            if evolution and self.pokemon.game_scene:
                self.pokemon.game_scene.open_evolution_overlay(self.pokemon, evolution)
                return True

        return leveled_up

    def level_up(self):
        """Sobe de nível"""
        old_level = self.pokemon.level
        self.pokemon.xp -= self.pokemon.xp_to_next
        self.pokemon.level += 1
        self.pokemon._calculate_stats()
        self.pokemon.current_hp = self.pokemon.max_hp
        self.pokemon.xp_to_next = self.pokemon._calculate_xp_needed()

        new_moves, pending_moves = self.pokemon.check_new_moves_on_level_up(old_level)
        if new_moves:
            print(
                f"[LEVEL UP] {self.pokemon.name} subiu para Lv.{self.pokemon.level} e aprendeu: {', '.join(new_moves)}")

        cache_key = (self.pokemon.id, self.pokemon.level, self.pokemon.speed_stat,
                     self.pokemon.is_shiny, self.pokemon.is_boss)
        self.pokemon._speed_cache.pop(cache_key, None)

        return pending_moves