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

    def _perform_evolution(self, new_id, is_normal_game = True):
        """Realiza a evolução mantendo os moves compatíveis"""
        old_name = self.pokemon.name
        custom_name = self.pokemon.custom_name
        old_level = self.pokemon.level
        unique_id = self.pokemon.unique_id
        is_in_team = self.pokemon.is_in_team

        new_pokemon_data = self.pokemon.pokedex.get_pokemon(new_id)
        if not new_pokemon_data:
            return

        if is_normal_game:
            # ===== REGISTRA NA POKEDEX ANTES DE ALTERAR O ID =====
            if hasattr(self.pokemon, 'game_scene') and self.pokemon.game_scene:
                game_scene = self.pokemon.game_scene
                if hasattr(game_scene, 'player'):
                    player = game_scene.player
                    player.register_seen(new_id)
                    player.caught_pokemon.add(new_id)
                    print(f"[POKEDEX] {new_pokemon_data['name']} (ID: {new_id}) registrado como visto e capturado!")

        # ===== ATUALIZA O POKEMON =====
        self.pokemon.id = new_id
        self.pokemon.name = new_pokemon_data["name"].capitalize()
        self.pokemon.types = new_pokemon_data["types"]
        self.pokemon.base_stats = new_pokemon_data["base_stats"]

        self.pokemon._calculate_stats()
        self.pokemon.current_hp = self.pokemon.max_hp

        self.pokemon._load_sprites(new_id, self.pokemon.is_shiny)
        self.pokemon.map_sprite_size = self.pokemon.pokedex.get_map_sprite_size(new_id, self.pokemon.is_shiny)

        # Atualiza moves
        new_learnset = set(self.pokemon.move_data.get_moves_at_level(self.pokemon.id, self.pokemon.level))
        current_move_names = set(move.name.lower() for move in self.pokemon.moves)
        moves_to_learn = new_learnset - current_move_names

        for move_name in moves_to_learn:
            self.pokemon._learn_move_without_replacement(move_name)

        self.pokemon.custom_name = custom_name

        # ===== SINCRONIZA A BOX SE O POKEMON ESTIVER NA BOX =====
        if hasattr(self.pokemon, 'game_scene') and self.pokemon.game_scene and is_normal_game:
            game_scene = self.pokemon.game_scene
            player = game_scene.player

            # Se o Pokémon NÃO está no time (está na box), atualiza o dict
            if not is_in_team:
                self._sync_box_data(player, unique_id)

            # ===== ATUALIZA O CACHE DO JOGADOR =====
            if unique_id in player._pokemon_cache:
                player._pokemon_cache[unique_id] = self.pokemon

        print(f"[EVOLUÇÃO] ✓ {old_name} (Lv.{old_level}) evoluiu para {self.pokemon.name}!")
        print(f"[EVOLUÇÃO] Moves atuais: {[m.name for m in self.pokemon.moves]}")

        # ===== REGISTRA CONQUISTAS =====
        self._register_evolution_achievements()

    def _sync_box_data(self, player, unique_id):
        """
        Sincroniza os dados do Pokémon na PC Box após evolução.
        """
        for data in player.pc_box:
            if data.get("unique_id") == unique_id:
                # Atualiza todos os campos relevantes
                data["id"] = self.pokemon.id
                data["name"] = self.pokemon.name
                data["types"] = self.pokemon.types.copy()
                data["base_stats"] = self.pokemon.base_stats.copy()
                data["max_hp"] = self.pokemon.max_hp
                data["attack"] = self.pokemon.attack
                data["defense"] = self.pokemon.defense
                data["sp_attack"] = self.pokemon.sp_attack
                data["sp_defense"] = self.pokemon.sp_defense
                data["speed"] = self.pokemon.speed_stat
                data["level"] = self.pokemon.level
                data["xp"] = self.pokemon.xp
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
                    for move in self.pokemon.moves
                ]
                print(f"[EVOLUTION] Box atualizada para {self.pokemon.name} (ID: {self.pokemon.id})")
                return True
        return False

    def _register_evolution_achievements(self):
        """
        Registra todas as conquistas relacionadas à evolução.
        """
        if not hasattr(self.pokemon, 'game_scene') or not self.pokemon.game_scene:
            return

        game_scene = self.pokemon.game_scene
        phase_id = f"{game_scene.chapter_id}-{game_scene.phase_number}"

        if not hasattr(game_scene, 'player') or not hasattr(game_scene.player, 'achievement_manager'):
            return

        ach_mgr = game_scene.player.achievement_manager

        # ===== 1. CONTADOR GERAL DE EVOLUÇÕES =====
        ach_mgr.increment_counter("evolution_count")
        ach_mgr.check_and_unlock("first_evolution", phase_id)
        ach_mgr.check_and_unlock("evolution_10", phase_id)
        ach_mgr.check_and_unlock("evolution_50", phase_id)

        # ===== 2. IDENTIFICA O TIPO DE EVOLUÇÃO =====
        method = getattr(self, '_pending_evolution_method', None)

        # Se não tem método definido, tenta inferir
        if not method:
            if hasattr(self.pokemon, '_last_evolution_data'):
                evo_data = self.pokemon._last_evolution_data
                method = evo_data.get("method", "level")

        # ===== 3. CONTADORES POR TIPO DE EVOLUÇÃO =====
        if method == "happiness":
            ach_mgr.increment_counter("happiness_evolution_count")
            ach_mgr.check_and_unlock("first_happiness_evolution", phase_id)
            ach_mgr.check_and_unlock("happiness_evolution_3", phase_id)
            ach_mgr.check_and_unlock("happiness_evolution_10", phase_id)

            # Verifica se foi por clima (dia/noite) - Espeon/Umbreon
            if hasattr(self.pokemon, '_last_evolution_time_of_day'):
                ach_mgr.increment_counter("weather_evolution_count")
                ach_mgr.check_and_unlock("first_weather_evolution", phase_id)
                ach_mgr.check_and_unlock("weather_evolution_5", phase_id)

        elif method == "stone":
            ach_mgr.increment_counter("stone_evolution_count")
            ach_mgr.check_and_unlock("first_stone_evolution", phase_id)
            ach_mgr.check_and_unlock("stone_evolution_5", phase_id)
            ach_mgr.check_and_unlock("stone_evolution_20", phase_id)

        elif method == "level":
            ach_mgr.increment_counter("level_evolution_count")
            ach_mgr.check_and_unlock("first_level_evolution", phase_id)
            ach_mgr.check_and_unlock("level_evolution_50", phase_id)

        elif method == "combination":
            ach_mgr.increment_counter("combination_evolution_count")
            ach_mgr.check_and_unlock("first_combination_evolution", phase_id)

        # ===== 4. LIMPA AS FLAGS TEMPORÁRIAS =====
        if hasattr(self, '_pending_evolution_method'):
            delattr(self, '_pending_evolution_method')
        if hasattr(self.pokemon, '_last_evolution_time_of_day'):
            delattr(self.pokemon, '_last_evolution_time_of_day')
        if hasattr(self.pokemon, '_last_evolution_data'):
            delattr(self.pokemon, '_last_evolution_data')

        print(
            f"[ACHIEVEMENT] Evolução contada! Método: {method}, "
            f"Total: {ach_mgr.get_counter('evolution_count')}"
        )

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
                "remove_partner": remove_partner
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
            partner_unique_id = partner.unique_id

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
                # Verifica se está na box (como dict)
                for data in player.pc_box[:]:
                    if data.get("unique_id") == partner_unique_id:
                        player.pc_box.remove(data)
                        print(f"[COMBINATION] {partner_name} removido da Box do jogador!")

                # ===== REMOVE DO CACHE =====
                if partner_unique_id in player._pokemon_cache:
                    del player._pokemon_cache[partner_unique_id]

                toast_battle(f"{partner_name} foi consumido na evolução!",
                             duration=2.0, pokemon=partner, portrait="sad")

            # Marca como não colocado
            partner.is_placed = False

        # ===== SE O PARCEIRO TAMBÉM DEVE EVOLUIR (não removido) =====
        elif partner_new_id and partner and partner.is_wild == self.pokemon.is_wild:
            partner_name = partner.name
            # Guarda o método de evolução para o parceiro
            if hasattr(partner, 'evolution'):
                partner.evolution._pending_evolution_method = "combination"
            partner._perform_evolution(partner_new_id)
            print(f"[COMBINATION] {partner_name} também evoluiu para {partner.name}!")

        if hasattr(self.pokemon, 'game_scene') and self.pokemon.game_scene:
            if hasattr(self.pokemon.game_scene, 'game') and self.pokemon.game_scene.game:
                self.pokemon.game_scene.game.player.auto_save()

        # Atualiza a UI se necessário
        self._refresh_ui_after_evolution()

        return self.pokemon

    def _refresh_ui_after_evolution(self):
        """Atualiza a UI após uma evolução"""
        if not hasattr(self.pokemon, 'game_scene') or not self.pokemon.game_scene:
            return

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
                game_scene.game.current_scene.layout_initialized = False
                print(f"[COMBINATION] TeamSelectScene marcado para recriar layout!")

    # ==================================================================
    # FILA DE MOVES PENDENTES (aprendidos ao subir de nível)
    # ==================================================================
    # IMPORTANTE:
    # Quando o Pokémon sobe de nível, coletamos os moves que ele
    # aprenderia neste nível em `pokemon._pending_moves_to_learn`.
    # NÃO abrimos overlay imediatamente — damos prioridade à evolução.
    # O processamento da fila acontece depois, quando o overlay de
    # evolução fechar (ou imediatamente, se não houver evolução).
    # ==================================================================
    def _queue_new_moves_for_level(self, new_level: int):
        """
        Coleta os moves que o Pokémon aprenderia neste nível e os coloca
        em uma fila. NÃO abre overlays — o processamento é feito depois,
        respeitando a prioridade de evolução.
        """
        if not hasattr(self.pokemon, '_pending_moves_to_learn'):
            self.pokemon._pending_moves_to_learn = []

        learnset = self.pokemon.move_data.get_pokemon_learnset(self.pokemon.id)
        current_moves = {m.name.lower() for m in self.pokemon.moves}

        for move_info in learnset:
            if move_info.get("level", 0) == new_level:
                move_name = move_info.get("move", "")
                if (move_name
                        and move_name.lower() not in current_moves
                        and move_name not in self.pokemon._pending_moves_to_learn):
                    self.pokemon._pending_moves_to_learn.append(move_name)
                    print(f"[LEVEL_UP] {self.pokemon.name}: '{move_name}' "
                          f"adicionado à fila (nível {new_level})")

    def _process_pending_moves(self):
        """
        Processa a fila de moves pendentes.
        Chamado quando NÃO há evolução a resolver, ou após o overlay de
        evolução fechar.
        Retorna True se algum move foi aprendido (ou pediu overlay).
        """
        if not hasattr(self.pokemon, '_pending_moves_to_learn'):
            return False

        pending = list(self.pokemon._pending_moves_to_learn)
        if not pending:
            return False

        # Pega apenas o PRIMEIRO move para processar.
        # Se abrir overlay, os demais ficam na fila e serão processados
        # quando a fila for retomada.
        next_move = pending[0]
        self.pokemon._pending_moves_to_learn = pending[1:]

        # Verifica se o Pokémon já tem esse move
        current = {m.name.lower() for m in self.pokemon.moves}
        if next_move.lower() in current:
            # Já tem, pula para o próximo
            return self._process_pending_moves()

        # Se tem menos de 4 moves, aprende direto
        if len(self.pokemon.moves) < 4:
            from src.entities.move import Move
            move_info = self.pokemon.move_data.get_move_info(next_move)
            if move_info:
                new_move = Move(next_move, move_info)
                self.pokemon.moves.append(new_move)
                print(f"[LEVEL_UP] {self.pokemon.name} aprendeu {next_move}!")

                # Toast informativo
                try:
                    toast_battle(
                        f"{self.pokemon.name} aprendeu: {next_move}!",
                        duration=4.0,
                        pokemon=self.pokemon,
                        portrait="inspired"
                    )
                except Exception:
                    pass

                # Continua processando o próximo
                return self._process_pending_moves() or True
            return self._process_pending_moves()

        # Tem 4 moves: precisa do overlay
        if self.pokemon.game_scene:
            self.pokemon.game_scene.open_move_learn_overlay(self.pokemon, next_move)
            return True

        return False

    def has_pending_moves(self) -> bool:
        """Retorna True se há moves na fila."""
        return bool(getattr(self.pokemon, '_pending_moves_to_learn', []))

    # ==================================================================
    # LEVEL UP (modificado — NÃO abre mais overlay de moves)
    # ==================================================================
    def level_up(self):
        """Sobe de nível. Bloqueado no nível 100. NÃO abre overlays de move."""
        MAX_LEVEL = 100

        # ===== TRAVA DE SEGURANÇA =====
        if self.pokemon.level >= MAX_LEVEL:
            self.pokemon.level = MAX_LEVEL
            self.pokemon.xp = 0
            return []

        old_level = self.pokemon.level
        self.pokemon.xp -= self.pokemon.xp_to_next
        self.pokemon.level += 1

        # ===== GARANTE QUE NUNCA PASSA DE 100 =====
        if self.pokemon.level > MAX_LEVEL:
            self.pokemon.level = MAX_LEVEL
            self.pokemon.xp = 0

        self.pokemon._calculate_stats()
        self.pokemon.current_hp = self.pokemon.max_hp
        self.pokemon.xp_to_next = self.pokemon._calculate_xp_needed()
        self.pokemon.add_happiness(10, "Subiu de nivel")

        toast_battle(
            f"{self.pokemon.name} subiu de nivel!!!",
            duration=4.0,
            pokemon=self.pokemon,
            portrait="joyous"
        )

        # ===== NOVO: apenas ENFILEIRA os moves, NÃO abre overlay =====
        self._queue_new_moves_for_level(self.pokemon.level)

        cache_key = (self.pokemon.id, self.pokemon.level, self.pokemon.speed_stat,
                     self.pokemon.is_shiny, self.pokemon.is_boss)
        self.pokemon._speed_cache.pop(cache_key, None)

        from src.managers.sounds.sound_manager import sound_manager
        from src.managers.sounds.sound_manager import SoundEffect

        sound_manager.play_effect(SoundEffect.LEVELUP)
        return []

    # ==================================================================
    # GAIN XP (modificado — evolução tem PRIORIDADE sobre moves)
    # ==================================================================
    def gain_xp(self, amount):
        """Ganha XP. Evolução SEMPRE tem prioridade sobre aprendizado de moves."""
        MAX_LEVEL = 100

        # ===== SE JÁ ESTÁ NO NÍVEL MÁXIMO, IGNORA XP =====
        if self.pokemon.level >= MAX_LEVEL:
            self.pokemon.xp = 0
            self.pokemon.xp_to_next = self.pokemon._calculate_xp_needed()
            return False

        old_level = self.pokemon.level
        self.pokemon.xp += amount

        leveled_up = False

        # Garante que a fila existe
        if not hasattr(self.pokemon, '_pending_moves_to_learn'):
            self.pokemon._pending_moves_to_learn = []

        # ===== SOBE DE NÍVEL, MAS NUNCA PASSA DE 100 =====
        while (self.pokemon.xp >= self.pokemon.xp_to_next
               and self.pokemon.level < MAX_LEVEL):
            self.level_up()
            leveled_up = True

        # ===== SE BATEU NO TETO, ZERA O XP E TRAVA =====
        if self.pokemon.level >= MAX_LEVEL:
            self.pokemon.level = MAX_LEVEL
            self.pokemon.xp = 0
            self.pokemon.xp_to_next = self.pokemon._calculate_xp_needed()

            # ===== CONQUISTA: NÍVEL MÁXIMO =====
            if leveled_up and hasattr(self.pokemon, 'game_scene') and self.pokemon.game_scene:
                game_scene = self.pokemon.game_scene
                phase_id = f"{game_scene.chapter_id}-{game_scene.phase_number}"
                if hasattr(game_scene, 'player') and hasattr(game_scene.player, 'achievement_manager'):
                    game_scene.player.achievement_manager.check_and_unlock("max_level_reached", phase_id)

        if not leveled_up:
            return False

        self.pokemon.attack_damage = self.pokemon._calculate_attack_damage()
        self.pokemon.defense_value = self.pokemon._calculate_defense()

        # ==================================================================
        # PRIORIDADE 1: EVOLUÇÃO
        # ==================================================================
        # Se o Pokémon pode evoluir (por nível ou felicidade), abre o
        # overlay de evolução. Os moves aprendidos ficam na fila e só
        # serão processados quando o overlay de evolução fechar.
        # ==================================================================
        evolution = None
        if self.pokemon.level < MAX_LEVEL:
            evolution = evolution_manager.check_evolution(
                self.pokemon.id, current_level=self.pokemon.level
            )
            if not evolution:
                evolution = evolution_manager.check_happiness_evolution(self.pokemon)

        if evolution and self.pokemon.game_scene:
            print(f"[LEVEL_UP] {self.pokemon.name}: evolução pendente — "
                  f"adiando {len(self.pokemon._pending_moves_to_learn)} move(s) "
                  f"para depois do overlay de evolução")
            self.pokemon.game_scene.open_evolution_overlay(self.pokemon, evolution)
            return True

        # ==================================================================
        # PRIORIDADE 2: APRENDIZADO DE MOVES (só se não houver evolução)
        # ==================================================================
        if self.has_pending_moves():
            self._process_pending_moves()

        return True