# src/scenes/minigames/survival/components/pokemon_input_handler.py

import pygame
from typing import Optional, TYPE_CHECKING

if TYPE_CHECKING:
    from src.scenes.minigames.survival.survival_minigame_scene import SurvivalMinigameScene
    from src.entities.pokemon import Pokemon


class PokemonInputHandler:
    """
    Gerencia inputs de clique nos Pokémon do campo.
    Abre o overlay de seleção de moves quando um Pokémon é clicado.
    """

    def __init__(self, game_scene: 'SurvivalMinigameScene'):
        self.game_scene = game_scene
        self.tile_size = 24
        self.click_tolerance = 20  # Tolerância em pixels para clique

    def handle_event(self, event: pygame.event.Event) -> bool:
        """
        Processa eventos de clique nos Pokémon.
        Retorna True se o evento foi consumido.
        """
        if event.type != pygame.MOUSEBUTTONDOWN or event.button != 1:
            return False

        # Não processa se o jogo está pausado ou em game over
        if self.game_scene.paused:
            return False
        if self.game_scene.game_state in ["game_over", "completed"]:
            return False

        # Não processa se tem um card selecionado (prioridade para colocar Pokémon)
        if self.game_scene.selected_card is not None:
            return False

        mouse_pos = pygame.mouse.get_pos()

        # Verifica se o mouse está dentro do viewport
        if not self.game_scene.screen_manager.is_mouse_in_viewport(mouse_pos):
            return False

        # Converte para posição do mundo
        world_pos = self.game_scene.screen_manager.get_mouse_world_position(
            mouse_pos, self.game_scene.camera
        )

        if not world_pos:
            return False

        world_x, world_y = world_pos

        # Busca o Pokémon na posição clicada
        clicked_pokemon = self._get_pokemon_at_position(world_x, world_y)

        if clicked_pokemon:
            # Abre o overlay de seleção de moves
            self._open_move_select_overlay(clicked_pokemon)
            return True

        return False

    def _get_pokemon_at_position(self, world_x: float, world_y: float) -> Optional['Pokemon']:
        """
        Retorna o Pokémon na posição do mundo (se houver)
        """
        tolerance_sq = self.click_tolerance * self.click_tolerance

        # Verifica nos Pokémon do jogador (aliados)
        for pokemon in self.game_scene.player_pokemon:
            if not pokemon.is_alive() or pokemon.is_defeated:
                continue

            dx = pokemon.x - world_x
            dy = pokemon.y - world_y
            distance_sq = dx * dx + dy * dy

            if distance_sq <= tolerance_sq:
                return pokemon

        return None

    def _open_move_select_overlay(self, pokemon: 'Pokemon'):
        """
        Abre o overlay de seleção de moves para o Pokémon clicado.
        Copiado do método game_scene.open_move_select_overlay
        """
        from src.scenes.game_scene.components.overlays.move_select_overlay import MoveSelectOverlay

        if not pokemon or not pokemon.moves:
            return

        # Fecha overlay existente
        if hasattr(self.game_scene, 'move_select_overlay') and self.game_scene.move_select_overlay:
            if hasattr(self.game_scene.move_select_overlay, 'close'):
                self.game_scene.move_select_overlay.close()

        # Cria e ativa o overlay
        self.game_scene.move_select_overlay = MoveSelectOverlay(self.game_scene, pokemon)
        self.game_scene.move_select_overlay.active = True

        # Pausa o jogo (igual ao game_scene)
        self.game_scene.paused = True
        if hasattr(self.game_scene, 'wave_manager') and self.game_scene.wave_manager:
            self.game_scene.wave_manager.paused = True

        print(f"[INPUT] Overlay de moves aberto para {pokemon.name}")