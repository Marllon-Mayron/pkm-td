# src/scenes/game_scene/components/managers/placement_manager.py
import pygame

class PlacementManager:
    """Gerencia os Pokémon colocados no mapa"""

    def __init__(self, game):
        self.game = game
        self.placed_pokemon = []  # Lista de Pokémon no mapa
        self.tile_size = 16

    def add_pokemon(self, spot, pokemon):
        """Adiciona um Pokémon no spot - USA O MESMO OBJETO"""
        # Verifica se já tem Pokémon neste spot
        existing = self.get_pokemon_at_spot(spot)
        if existing:
            print(f"[PLACEMENT] Spot já ocupado por {existing.name}")
            return None

        # Verifica se o spot já está marcado como ocupado
        if spot.occupied:
            print(f"[PLACEMENT] Spot já marcado como ocupado")
            return None

        # Verifica se o Pokémon já está no mapa
        if hasattr(pokemon, 'is_placed') and pokemon.is_placed:
            print(f"[PLACEMENT] {pokemon.name} já está no mapa!")
            return None

        # Calcula o centro do tile para posicionar o Pokémon
        tile_center_x = (spot.x // self.tile_size) * self.tile_size + self.tile_size // 2
        tile_center_y = (spot.y // self.tile_size) * self.tile_size + self.tile_size // 2

        # NÃO CRIAMOS MAIS UMA CÓPIA! Usamos o mesmo objeto
        pokemon.x = tile_center_x
        pokemon.y = tile_center_y
        pokemon.original_spot_x = tile_center_x
        pokemon.original_spot_y = tile_center_y
        pokemon.screen_manager = self.game.screen_manager

        # Marca como colocado
        pokemon.is_placed = True
        pokemon.spot_id = id(spot)
        pokemon.combat_state = "idle"

        pokemon.game_scene = self.game
        # Marca o spot como ocupado
        spot.occupied = True

        # Adiciona à lista de colocados
        self.placed_pokemon.append(pokemon)

        print(
            f"[PLACEMENT] {pokemon.name} colocado no spot ({spot.x}, {spot.y}) - "
            f"Centro ({tile_center_x}, {tile_center_y})"
        )

        if hasattr(self.game, 'battle_system'):
            pokemon.set_battle_system(self.game.battle_system)

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

                # PROCURA O SPOT CORRESPONDENTE E DESOCUPA
                pokemon_tile_x = pokemon.x // self.tile_size
                pokemon_tile_y = pokemon.y // self.tile_size

                for spot in self.game.spot_renderer.get_spots():
                    spot_tile_x = spot.x // self.tile_size
                    spot_tile_y = spot.y // self.tile_size

                    if spot_tile_x == pokemon_tile_x and spot_tile_y == pokemon_tile_y:
                        spot.occupied = False
                        print(f"[PLACEMENT] Spot ({spot.x}, {spot.y}) desocupado")
                        break

                # Marca o Pokémon como não colocado (é o mesmo objeto do time!)
                pokemon.is_placed = False

                return pokemon

        return None

    def _get_team_pokemon(self):
        """Método auxiliar para pegar Pokémon do time"""
        if hasattr(self.game, 'player') and hasattr(self.game.player, 'team'):
            return self.game.player.team
        return []

    def get_pokemon_at_spot(self, spot):
        """Verifica se já existe um Pokémon no spot baseado no tile"""
        # Converte spot para coordenadas de tile
        spot_tile_x = spot.x // self.tile_size
        spot_tile_y = spot.y // self.tile_size

        for pokemon in self.placed_pokemon:
            pokemon_tile_x = pokemon.x // self.tile_size
            pokemon_tile_y = pokemon.y // self.tile_size

            if pokemon_tile_x == spot_tile_x and pokemon_tile_y == spot_tile_y:
                return pokemon
        return None

    def get_pokemon_at_world_pos(self, world_x, world_y, tolerance=20):
        """Retorna o Pokémon na posição do mundo (para seleção)"""
        for pokemon in self.placed_pokemon:
            distance = ((pokemon.x - world_x) ** 2 + (pokemon.y - world_y) ** 2) ** 0.5
            if distance < tolerance:
                return pokemon
        return None

    def update(self, dt, enemies):
        """Atualiza todos os Pokémon colocados - SISTEMA DE INVESTIDAS"""

        defeated = []

        for pokemon in self.placed_pokemon:
            if pokemon.is_alive():
                # Sistema de combate baseado em investidas
                pokemon.update_combat(dt, enemies)

                # Atualiza animação normal
                pokemon.update(dt)
            else:
                defeated.append(pokemon)

        # Remove derrotados
        for pokemon in defeated:
            self._remove_pokemon(pokemon)

    def _remove_pokemon(self, pokemon):
        """Remove um Pokémon do mapa (por derrota)"""
        if pokemon in self.placed_pokemon:
            self.placed_pokemon.remove(pokemon)

            # Libera o spot
            if hasattr(pokemon, 'spot_id') and pokemon.spot_id:
                for spot in self.game.spot_renderer.get_spots():
                    if spot.id == pokemon.spot_id:
                        spot.occupied = False
                        print(f"[COMBATE] Spot {spot.id} liberado")
                        break

            # Marca como não colocado (é o mesmo objeto do time!)
            pokemon.is_placed = False

    def clear(self):
        """Remove todos os Pokémon do mapa"""
        for pokemon in self.placed_pokemon:
            # Libera os spots
            if hasattr(pokemon, 'spot_id') and pokemon.spot_id:
                for spot in self.game.spot_renderer.get_spots():
                    if spot.id == pokemon.spot_id:
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
        """Renderiza todos os Pokémon colocados"""
        for pokemon in self.placed_pokemon:
            pokemon.render_hp(screen, camera)

    def render(self, screen, camera, screen_manager):
        """Renderiza todos os Pokémon colocados"""
        for pokemon in self.placed_pokemon:
            pokemon.render(screen, camera, show_hp=False)

            # DEBUG: Mostra estado de combate na tela
            if hasattr(self.game, 'show_debug') and self.game.show_debug:
                font = pygame.font.Font(None, 16)
                # Mostra estado e cooldown
                state_text = f"{pokemon.combat_state}"
                if pokemon.attack_cooldown > 0:
                    state_text += f" CD:{pokemon.attack_cooldown:.1f}"

                # Posição do texto (acima do Pokémon)
                screen_x, screen_y = screen_manager.world_to_screen(
                    pokemon.x, pokemon.y - 50, camera
                )

                # Cor baseada no estado
                if pokemon.combat_state == "attacking":
                    color = (255, 0, 0)  # Vermelho
                elif pokemon.combat_state == "moving_to_target":
                    color = (255, 255, 0)  # Amarelo
                elif pokemon.combat_state == "returning":
                    color = (0, 255, 255)  # Ciano
                else:  # idle
                    color = (0, 255, 0)  # Verde

                text_surf = font.render(state_text, True, color)
                screen.blit(text_surf, (screen_x - text_surf.get_width() // 2, screen_y))