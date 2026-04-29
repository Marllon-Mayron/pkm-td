# src/scenes/game_scene/components/managers/placement_manager.py
import pygame

class PlacementManager:
    """Gerencia os Pokémon colocados no mapa"""

    def __init__(self, game):
        self.game = game
        self.placed_pokemon = []  # Lista de Pokémon no mapa
        self.tile_size = 24

    def _check_combination_evolution_on_placement(self, pokemon, spot):
        """
        Verifica se o Pokémon que está sendo colocado pode evoluir
        em combinação com algum Pokémon já existente no mapa.
        Retorna True se evoluiu, False caso contrário.
        """
        if pokemon.is_wild:
            return False

        tile_center_x = (spot.x // self.tile_size) * self.tile_size + self.tile_size // 2
        tile_center_y = (spot.y // self.tile_size) * self.tile_size + self.tile_size // 2

        # Verifica TODOS os Pokémon já colocados
        for placed in self.placed_pokemon:
            if placed == pokemon:
                continue
            if not placed.is_alive() or placed.is_defeated:
                continue

            # Calcula distância entre os Pokémon
            dx = abs(placed.x - tile_center_x)
            dy = abs(placed.y - tile_center_y)
            distance = (dx * dx + dy * dy) ** 0.5

            # Se estiverem no mesmo tile ou muito próximos (menos de 30 pixels)
            if distance < 30:
                # Verifica se o novo Pokémon evolui com o existente
                evolution_data = pokemon.evolution.check_combination_evolution(placed)

                # Se não, verifica se o existente evolui com o novo
                if not evolution_data:
                    evolution_data = placed.evolution.check_combination_evolution(pokemon)

                if evolution_data:
                    print(f"[COMBINATION] Evolução detectada entre {pokemon.name} e {placed.name}!")

                    # Determina qual vai evoluir (ambos podem evoluir em casos especiais)
                    if evolution_data["evolve_to"] is not None:
                        # Executa a evolução
                        result = pokemon.evolution.perform_combination_evolution(evolution_data)
                        return True

                    # Se chegou aqui, não houve evolução
                    return False

        return False

    def add_pokemon(self, spot, pokemon):
        """Adiciona um Pokémon no spot"""
        # Verificações básicas
        existing = self.get_pokemon_at_spot(spot)
        if existing:
            print(f"[PLACEMENT] Spot já ocupado por {existing.name}")
            return None

        if spot.occupied:
            print(f"[PLACEMENT] Spot já marcado como ocupado")
            return None

        if hasattr(pokemon, 'is_placed') and pokemon.is_placed:
            print(f"[PLACEMENT] {pokemon.name} já está no mapa!")
            return None

        # ===== VERIFICA EVOLUÇÃO POR COMBINAÇÃO ANTES DE COLOCAR =====
        if self._check_combination_evolution_on_placement(pokemon, spot):
            # Se evoluiu, o Pokémon original foi transformado/removido
            # Não adiciona o Pokémon original ao spot (pois ele já evoluiu)
            print(f"[COMBINATION] {pokemon.name} evoluiu durante o placement!")

            # Procura o Pokémon evoluído (agora está no placed_pokemon)
            for placed in self.placed_pokemon:
                if placed.id == pokemon.id and placed != pokemon:
                    # Atualiza a posição do Pokémon evoluído para o spot correto
                    tile_center_x = (spot.x // self.tile_size) * self.tile_size + self.tile_size // 2
                    tile_center_y = (spot.y // self.tile_size) * self.tile_size + self.tile_size // 2
                    placed.x = tile_center_x
                    placed.y = tile_center_y
                    placed.original_spot_x = tile_center_x
                    placed.original_spot_y = tile_center_y
                    placed.placed_tile_x = tile_center_x // self.tile_size
                    placed.placed_tile_y = tile_center_y // self.tile_size
                    placed.is_placed = True
                    spot.occupied = True
                    return placed

            return None

        # Se não evoluiu, coloca normalmente
        return self._add_pokemon_to_spot(spot, pokemon)

    def _add_pokemon_to_spot(self, spot, pokemon):
        """Adiciona o Pokémon ao spot (lógica interna)"""
        tile_size = self.tile_size

        # Calcula o centro do tile
        tile_center_x = (spot.x // tile_size) * tile_size + tile_size // 2
        tile_center_y = (spot.y // tile_size) * tile_size + tile_size // 2

        pokemon.x = tile_center_x
        pokemon.y = tile_center_y
        pokemon.original_spot_x = tile_center_x
        pokemon.original_spot_y = tile_center_y
        pokemon.screen_manager = self.game.screen_manager

        pokemon.is_placed = True
        pokemon.placed_tile_x = tile_center_x // tile_size
        pokemon.placed_tile_y = tile_center_y // tile_size
        pokemon.combat_state = "idle"
        pokemon.game_scene = self.game

        spot.occupied = True
        self.placed_pokemon.append(pokemon)

        if hasattr(self.game, 'battle_system'):
            pokemon.set_battle_system(self.game.battle_system)

        print(f"[PLACEMENT] {pokemon.name} colocado no spot ({spot.x}, {spot.y})")
        return pokemon

    def get_pokemon_at_world_pos(self, world_x, world_y, tolerance=20):
        """Retorna o Pokémon na posição do mundo (para seleção)"""
        tolerance_sq = tolerance * tolerance
        for pokemon in self.placed_pokemon:
            dx = pokemon.x - world_x
            dy = pokemon.y - world_y
            if dx * dx + dy * dy < tolerance_sq:
                return pokemon
        return None

    def remove_pokemon_by_right_click(self, world_x, world_y, tolerance=20):
        """Remove o Pokémon na posição do mundo (para clique direito)"""
        pokemon = self.get_pokemon_at_world_pos(world_x, world_y, tolerance)

        if pokemon:
            print(f"[PLACEMENT] Recolhendo {pokemon.name} com clique direito")

            # Remove da lista de colocados
            if pokemon in self.placed_pokemon:
                self.placed_pokemon.remove(pokemon)

                # ===== CORREÇÃO: DESOCUPA O SPOT USANDO COORDENADAS DE TILE =====
                # Usa as coordenadas de tile armazenadas no Pokémon
                pokemon_tile_x = pokemon.placed_tile_x
                pokemon_tile_y = pokemon.placed_tile_y

                # Procura e desocupa o spot correspondente
                spot_found = False
                for spot in self.game.spot_renderer.get_spots():
                    spot_tile_x = spot.x // self.tile_size
                    spot_tile_y = spot.y // self.tile_size

                    if spot_tile_x == pokemon_tile_x and spot_tile_y == pokemon_tile_y:
                        spot.occupied = False
                        spot_found = True
                        print(f"[PLACEMENT] Spot ({spot.x}, {spot.y}) desocupado")
                        break

                if not spot_found:
                    print(f"[PLACEMENT] ERRO: Spot não encontrado para tile ({pokemon_tile_x}, {pokemon_tile_y})")

                # Marca o Pokémon como não colocado (é o mesmo objeto do time!)
                pokemon.is_placed = False

                return pokemon

        return None

    def get_free_spots(self):
        """Retorna lista de spots livres"""
        spots = self.game.spot_renderer.get_spots()
        return [spot for spot in spots if not spot.occupied]

    def get_ally_at_spot(self, spot):
        """Retorna o aliado em um spot específico"""
        spot_tile_x = spot.x // self.tile_size
        spot_tile_y = spot.y // self.tile_size

        for pokemon in self.placed_pokemon:
            if hasattr(pokemon, 'placed_tile_x'):
                if pokemon.placed_tile_x == spot_tile_x and pokemon.placed_tile_y == spot_tile_y:
                    return pokemon
        return None

    def get_pokemon_at_spot(self, spot):
        """Verifica se já existe um Pokémon no spot baseado no tile"""
        # Converte spot para coordenadas de tile
        spot_tile_x = spot.x // self.tile_size
        spot_tile_y = spot.y // self.tile_size

        for pokemon in self.placed_pokemon:
            # Usa as coordenadas armazenadas ou calcula
            if hasattr(pokemon, 'placed_tile_x'):
                pokemon_tile_x = pokemon.placed_tile_x
                pokemon_tile_y = pokemon.placed_tile_y
            else:
                pokemon_tile_x = pokemon.x // self.tile_size
                pokemon_tile_y = pokemon.y // self.tile_size

            if pokemon_tile_x == spot_tile_x and pokemon_tile_y == spot_tile_y:
                return pokemon
        return None

    def update(self, dt, enemies):
        """Atualiza todos os Pokémon colocados"""
        for pokemon in self.placed_pokemon:
            # SEMPRE atualiza o Pokémon (animação continua mesmo se morto)
            pokemon.update(dt, enemies=enemies)

            # SISTEMA DE COMBATE SÓ PARA VIVOS
            if pokemon.is_alive():
                pokemon.update_combat(dt, enemies)

    def _remove_pokemon(self, pokemon):
        """Remove um Pokémon do mapa """
        if pokemon in self.placed_pokemon:
            self.placed_pokemon.remove(pokemon)

            # ===== CORREÇÃO: LIBERA O SPOT USANDO COORDENADAS DE TILE =====
            # Usa as coordenadas de tile armazenadas
            if hasattr(pokemon, 'placed_tile_x') and hasattr(pokemon, 'placed_tile_y'):
                pokemon_tile_x = pokemon.placed_tile_x
                pokemon_tile_y = pokemon.placed_tile_y
            else:
                # Fallback: calcula da posição atual
                pokemon_tile_x = pokemon.x // self.tile_size
                pokemon_tile_y = pokemon.y // self.tile_size

            spot_found = False
            for spot in self.game.spot_renderer.get_spots():
                spot_tile_x = spot.x // self.tile_size
                spot_tile_y = spot.y // self.tile_size

                if spot_tile_x == pokemon_tile_x and spot_tile_y == pokemon_tile_y:
                    spot.occupied = False
                    spot_found = True
                    print(f"[COMBATE] Spot ({spot.x}, {spot.y}) liberado")
                    break

            if not spot_found:
                print(f"[COMBATE] ERRO: Spot não encontrado para tile ({pokemon_tile_x}, {pokemon_tile_y})")

            # Marca como não colocado (é o mesmo objeto do time!)
            pokemon.is_placed = False

    def clear(self):
        """Remove todos os Pokémon do mapa"""
        for pokemon in self.placed_pokemon:
            # Libera os spots usando coordenadas de tile
            if hasattr(pokemon, 'placed_tile_x') and hasattr(pokemon, 'placed_tile_y'):
                pokemon_tile_x = pokemon.placed_tile_x
                pokemon_tile_y = pokemon.placed_tile_y
            else:
                pokemon_tile_x = pokemon.x // self.tile_size
                pokemon_tile_y = pokemon.y // self.tile_size

            for spot in self.game.spot_renderer.get_spots():
                spot_tile_x = spot.x // self.tile_size
                spot_tile_y = spot.y // self.tile_size

                if spot_tile_x == pokemon_tile_x and spot_tile_y == pokemon_tile_y:
                    spot.occupied = False
                    break

            # Reseta is_placed no time
            for team_pokemon in self.game.player.team:
                if (team_pokemon.id == pokemon.id and
                        team_pokemon.level == pokemon.level):
                    team_pokemon.is_placed = False
                    break

        self.placed_pokemon.clear()

    def render_hp(self, screen, camera):
        """Renderiza as barras de HP de todos os Pokémon colocados"""
        for pokemon in self.placed_pokemon:
            # Agora usamos o método interno _render_hp_bar
            # Mas precisamos passar os parâmetros corretos
            if camera and hasattr(pokemon, 'screen_manager') and pokemon.screen_manager:
                screen_x, screen_y = pokemon.screen_manager.world_to_screen(pokemon.x, pokemon.y, camera)
                zoom_scale = camera.zoom * pokemon.screen_manager.render_scale

                # Calcula o sprite_rect para posicionar a barra
                sprite_to_render = pokemon._prepare_sprite(zoom_scale)
                if sprite_to_render:
                    current_width, current_height = sprite_to_render.get_width(), sprite_to_render.get_height()
                    final_width = max(1, int(current_width * zoom_scale))
                    final_height = max(1, int(current_height * zoom_scale))

                    if final_width != current_width or final_height != current_height:
                        scaled_sprite = pygame.transform.scale(sprite_to_render, (final_width, final_height))
                    else:
                        scaled_sprite = sprite_to_render

                    sprite_rect = scaled_sprite.get_rect()
                    sprite_rect.center = (int(screen_x), int(screen_y))

                    # Renderiza a barra de HP
                    pokemon._render_hp_bar(screen, sprite_rect, zoom_scale)

    def render(self, screen, camera, screen_manager):
        """Renderiza todos os Pokémon colocados"""
        for pokemon in self.placed_pokemon:
            pokemon.render(screen, camera, show_hp=False)