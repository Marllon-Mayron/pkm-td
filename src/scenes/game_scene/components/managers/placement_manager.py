# src/scenes/game_scene/components/managers/placement_manager.py
import pygame

class PlacementManager:
    """Gerencia os Pokémon colocados no mapa"""

    def __init__(self, game):
        self.game = game
        self.placed_pokemon = []  # Lista de Pokémon no mapa
        self.tile_size = 24

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
        # ARMAZENA A POSIÇÃO DO TILE PARA REFERÊNCIA FUTURA
        pokemon.placed_tile_x = tile_center_x // self.tile_size
        pokemon.placed_tile_y = tile_center_y // self.tile_size
        pokemon.combat_state = "idle"

        pokemon.game_scene = self.game
        # Marca o spot como ocupado
        spot.occupied = True

        # Adiciona à lista de colocados
        self.placed_pokemon.append(pokemon)

        print(
            f"[PLACEMENT] {pokemon.name} colocado no spot ({spot.x}, {spot.y}) - "
            f"Centro ({tile_center_x}, {tile_center_y}) - "
            f"Tile ({pokemon.placed_tile_x}, {pokemon.placed_tile_y})"
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
        """Atualiza todos os Pokémon colocados - COM ANIMAÇÕES DE STATUS"""

        defeated = []

        for pokemon in self.placed_pokemon:
            if pokemon.is_alive():
                # ===== ATUALIZA ANIMAÇÃO BASEADA EM STATUS =====
                if hasattr(pokemon, 'effect_manager') and pokemon.effect_manager:
                    status = pokemon.effect_manager.get_status(pokemon)
                    if status and status.type.value != "none":
                        # Tem status - verifica se precisa trocar animação
                        current_anim = getattr(pokemon, 'current_animation', 'idle')
                        status_anim = self._get_status_animation_name(status.type.value)
                        if status_anim and current_anim != status_anim:
                            pokemon.set_animation_direct(status_anim)
                    else:
                        # Sem status - atualiza animação normal
                        self._update_normal_pokemon_animation(pokemon, dt)
                else:
                    self._update_normal_pokemon_animation(pokemon, dt)

                # Sistema de combate baseado em investidas
                pokemon.update_combat(dt, enemies)

                # Atualiza animação normal
                pokemon.update(dt)
            else:
                pass
                #defeated.append(pokemon)

        # Remove derrotados
        for pokemon in defeated:
            self._remove_pokemon(pokemon)

    def _get_status_animation_name(self, status_type: str) -> str:
        """Retorna o nome da animação para um status"""
        status_map = {
            "sleep": "sleep",
            "paralysis": "charge",
            "freeze": "charge",
        }
        return status_map.get(status_type)

    def _update_normal_pokemon_animation(self, pokemon, dt):
        """Atualiza animação normal do Pokémon"""
        if hasattr(pokemon, '_update_animation'):
            pokemon._update_animation(dt)

    def _remove_pokemon(self, pokemon):
        """Remove um Pokémon do mapa (por derrota) - CORRIGIDO"""
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