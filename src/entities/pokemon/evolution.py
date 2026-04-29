# src/entities/pokemon/evolution.py

from src.managers.evolution_manager import evolution_manager
from src.ui.toast_renderer import toast_battle


class PokemonEvolution:
    """Gerencia evolução do Pokémon"""

    def __init__(self, pokemon):
        self.pokemon = pokemon

    def check_and_evolve(self):

        evolution = evolution_manager.check_evolution(self.pokemon.id, current_level=self.pokemon.level)

        if evolution:
            evolve_to_id = evolution["evolve_to"]
            self._perform_evolution(evolve_to_id)
            self.pokemon.game_scene.game.player.auto_save()
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

    def check_combination_evolution(self, nearby_pokemon):
        """
        Verifica se há evolução por combinação com outro Pokémon próximo.
        Retorna o novo ID se evoluir, None caso contrário.
        """
        combination_rules = {
            # (meu_id, outro_id) -> (novo_id_meu, novo_id_outro, mensagem, remover_parceiro)
            # Shellder (90) + Slowpoke (79) = Slowbro (80), Shellder some
            (90, 79): (80, None, "Shellder se juntou a Slowpoke e evoluiu para Slowbro!", True),
            (79, 90): (80, None, "Shellder mordeu Slowpoke e evoluiu para Slowbro!", True),
        }

        key = (self.pokemon.id, nearby_pokemon.id)
        if key in combination_rules:
            my_new_id, other_new_id, message, remove_partner = combination_rules[key]
            return {
                "evolve_to": my_new_id,
                "method": "combination",
                "partner": nearby_pokemon,
                "partner_new_id": other_new_id,
                "message": message,
                "remove_partner": remove_partner  # NOVO: flag para remover o parceiro
            }

        return None

    def perform_combination_evolution(self, evolution_data):
        """
        Realiza evolução por combinação com outro Pokémon.
        Retorna o Pokémon que evoluiu (ou None se não evoluiu).
        """
        partner = evolution_data["partner"]
        my_new_id = evolution_data["evolve_to"]
        partner_new_id = evolution_data.get("partner_new_id")
        message = evolution_data.get("message", f"{self.pokemon.name} evoluiu!")
        remove_partner = evolution_data.get("remove_partner", False)

        # Mostra mensagem visual
        toast_battle(message, duration=4.0, pokemon=self.pokemon, portrait="joyous")

        # Evolui este Pokémon
        old_name = self.pokemon.name
        self._perform_evolution(my_new_id)
        print(f"[COMBINATION] ✓ {old_name} evoluiu para {self.pokemon.name}!")

        # ===== SE DEVE REMOVER O PARCEIRO =====
        if remove_partner and partner:
            print(f"[COMBINATION] {partner.name} será consumido na combinação!")
            partner_name = partner.name

            # Remove do placement_manager se existir
            if hasattr(self.pokemon, 'game_scene') and self.pokemon.game_scene:
                game_scene = self.pokemon.game_scene

                # Remove da lista de Pokémon colocados
                if hasattr(game_scene, 'placement_manager'):
                    placement_manager = game_scene.placement_manager
                    if partner in placement_manager.placed_pokemon:
                        placement_manager.placed_pokemon.remove(partner)
                        print(f"[COMBINATION] {partner_name} removido do placement_manager")

                # Libera o spot do parceiro
                if hasattr(game_scene, 'spot_renderer'):
                    tile_size = 24
                    if hasattr(partner, 'x') and hasattr(partner, 'y'):
                        partner_tile_x = int(partner.x // tile_size)
                        partner_tile_y = int(partner.y // tile_size)

                        for spot in game_scene.spot_renderer.get_spots():
                            spot_tile_x = spot.x // tile_size
                            spot_tile_y = spot.y // tile_size
                            if spot_tile_x == partner_tile_x and spot_tile_y == partner_tile_y:
                                spot.occupied = False
                                print(f"[COMBINATION] Spot do {partner_name} liberado")
                                break

                # ===== REMOVE DO TIME DO JOGADOR =====
                player = game_scene.player
                if partner in player.team:
                    player.team.remove(partner)
                    print(f"[COMBINATION] {partner_name} removido do time do jogador!")

                # ===== REMOVE DA BOX (PC) DO JOGADOR =====
                if partner in player.pc_box:
                    player.pc_box.remove(partner)
                    print(f"[COMBINATION] {partner_name} removido da Box do jogador!")

                toast_battle(f"{partner_name} foi consumido na evolução!",
                             duration=2.0, pokemon=partner, portrait="sad")

            # Marca como não colocado
            partner.is_placed = False

        # ===== SE O PARCEIRO TAMBÉM DEVE EVOLUIR (não removido) =====
        elif partner_new_id and partner and partner.is_wild == self.pokemon.is_wild:
            partner_name = partner.name
            partner._perform_evolution(partner_new_id)
            print(f"[COMBINATION] {partner_name} também evoluiu para {partner.name}!")

        if hasattr(self.pokemon, 'game_scene') and self.pokemon.game_scene:
            if hasattr(self.pokemon.game_scene, 'game') and self.pokemon.game_scene.game:
                self.pokemon.game_scene.game.player.auto_save()

        # Atualiza a UI se necessário
        if hasattr(self.pokemon, 'game_scene') and self.pokemon.game_scene:
            game_scene = self.pokemon.game_scene

            # Atualiza o team_manager
            if hasattr(game_scene, 'team_manager'):
                for slot in game_scene.team_manager.team_slots:
                    if slot.pokemon == self.pokemon:
                        slot._cached_sprite = None
                        slot._cached_bg = None
                        break

            # Força recriação do layout do team_select se estiver ativo
            if hasattr(game_scene.game, 'current_scene'):
                from src.scenes.team_select_scene.team_select_scene import TeamSelectScene
                if isinstance(game_scene.game.current_scene, TeamSelectScene):
                    # Marca para recriar o layout na tela de seleção de time
                    game_scene.game.current_scene.layout_initialized = False
                    print(f"[COMBINATION] TeamSelectScene marcado para recriar layout!")

        return self.pokemon

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

        toast_battle(f"{self.pokemon.name} subiu de nivel!!!", duration=4.0, pokemon=self.pokemon, portrait="joyous")
        new_moves, pending_moves = self.pokemon.check_new_moves_on_level_up(old_level)
        if new_moves:
            toast_battle(f"{self.pokemon.name} aprendeu: {', '.join(new_moves)} ", duration=5.0, pokemon=self.pokemon,
                         portrait="inspired")

        cache_key = (self.pokemon.id, self.pokemon.level, self.pokemon.speed_stat,
                     self.pokemon.is_shiny, self.pokemon.is_boss)
        self.pokemon._speed_cache.pop(cache_key, None)

        from src.managers.sounds.sound_manager import sound_manager
        from src.managers.sounds.sound_manager import SoundEffect

        sound_manager.play_effect(SoundEffect.LEVELUP)
        return pending_moves