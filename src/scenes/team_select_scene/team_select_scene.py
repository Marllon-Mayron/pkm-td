import pygame
import math
from src.scenes.base_scene import BaseScene
from src.scenes.game_scene.game_scene import GameScene
from src.scenes.phase_selector.phase_select_scene import PhaseSelectScene
from src.scenes.team_select_scene.components.gradient_background import GradientBackground
from src.scenes.team_select_scene.components.pokemon_modal import PokemonModal
from src.scenes.team_select_scene.components.navigation_buttons import NavigationButtons
from src.scenes.team_select_scene.managers.layout_manager import LayoutManager
from src.scenes.team_select_scene.managers.pokemon_manager import PokemonManager
from src.scenes.team_select_scene.handlers.event_handler import EventHandler
from src.scenes.team_select_scene.utils.constants import FONT_SIZES
from src.data.pokedex import Pokedex


class TeamSelectScene(BaseScene):
    def __init__(self, game, chapter ,phase):
        super().__init__(game)

        self.pokedex = Pokedex()
        self.phase = phase
        self.chapter = chapter
        # Managers
        self.pokemon_manager = PokemonManager(game.player)
        self.layout_manager = LayoutManager(game)
        self.event_handler = EventHandler(game, self.pokemon_manager, self.layout_manager)

        # Components
        self.background = GradientBackground(game.screen_manager)
        self.navigation = None

        # State
        self.current_page = 0
        self.total_pages = 1
        self.layout_initialized = False

        # Fonts
        self.title_font = pygame.font.Font(None, FONT_SIZES['TITLE'])
        self.slot_font = pygame.font.Font(None, FONT_SIZES['SLOT'])
        self.grid_font = pygame.font.Font(None, FONT_SIZES['GRID'])
        self.page_font = pygame.font.Font(None, FONT_SIZES['PAGE'])

        # Load data
        #Adiciona pokemons na box
        #self.pokemon_manager.load_available_pokemon()

    def _initialize_layout(self):
        """Inicializa o layout da cena"""
        layout = self.layout_manager.create_layout(
            self.game.player.team,
            self.pokemon_manager.available_pokemon,
            self.current_page
        )

        self.team_slots = layout['team_slots']
        self.grid_items = layout['grid_items']
        buttons = layout['buttons']

        self.navigation = NavigationButtons(
            buttons['back'],
            buttons['start'],
            buttons['prev'],
            buttons['next']
        )

        self.total_pages = self.pokemon_manager.get_page_count(
            self.layout_manager.items_per_page
        )
        self.layout_initialized = True

    def handle_event(self, event):
        # Verifica se precisa recriar layout
        if not self.layout_initialized:
            self._initialize_layout()

        result = self.event_handler.handle_event(
            event, self.team_slots, self.grid_items,
            self.navigation.back_button if self.navigation else None,
            self.navigation.start_button if self.navigation else None,
            self.navigation.prev_page_button if self.navigation else None,
            self.navigation.next_page_button if self.navigation else None,
            self.current_page, self.total_pages
        )

        if result:
            self._handle_action(result)

    def _handle_action(self, action):
        action_type = action.get('type')

        if action_type == 'GO_BACK':
            from src.scenes.phase_selector.phase_select_scene import PhaseSelectScene
            self.game.phase_select_scene = PhaseSelectScene(self.game)
            self.game.current_scene = self.game.phase_select_scene

        elif action_type == 'START_GAME':
            print("Iniciando batalha com time:",
                  [p.name for p in self.game.player.team])

            self.game.game_scene = GameScene(self.game, self.chapter,self.phase)
            self.game.current_scene = self.game.game_scene

        elif action_type == 'PREV_PAGE':
            self.current_page -= 1
            self.layout_initialized = False

        elif action_type == 'NEXT_PAGE':
            self.current_page += 1
            self.layout_initialized = False

        elif action_type == 'SLOT_CLICK':
            slot = action['slot']
            # Atualiza seleção dos slots
            for s in self.team_slots:
                s.is_selected = (s.slot_index == action['slot_index'])
            # Abre modal se tiver Pokémon
            if slot.pokemon:
                print(f"Abrindo modal do Pokémon: {slot.pokemon.name}")  # Debug
                modal = PokemonModal(self.game, slot.pokemon)
                self.event_handler.set_modal(modal)

        elif action_type == 'GRID_CLICK':
            pokemon = action['pokemon']
            print(f"Abrindo modal do Pokémon: {pokemon.name}")  # Debug
            modal = PokemonModal(self.game, pokemon)
            self.event_handler.set_modal(modal)

        elif action_type == 'MODAL_ACTION':
            self._handle_modal_action()

        elif action_type == 'CLOSE_MODAL':
            self.event_handler.set_modal(None)

        elif action_type == 'RESIZE':
            pass  # Layout será recriado no próximo frame

    def _handle_modal_action(self):
        modal = self.event_handler.modal
        if not modal:
            return

        if modal.pokemon.is_in_team:
            self.pokemon_manager.remove_from_team(modal.pokemon)
        else:
            self.pokemon_manager.add_to_team(modal.pokemon)

        # Atualiza slots
        for i, slot in enumerate(self.team_slots):
            if i < len(self.game.player.team):
                slot.set_pokemon(self.game.player.team[i])
            else:
                slot.set_pokemon(None)

        # Recria layout
        self.layout_initialized = False

    def fixed_update(self, dt):
        if not self.layout_initialized:
            self._initialize_layout()

    def render(self, screen):
        # Fundo
        self.background.render(screen)

        if not self.layout_initialized:
            return

        # Título
        title = self.title_font.render("SELECIONAR TIME", True, (220, 220, 230))
        title_x = (self.game.screen_manager.window_width - title.get_width()) // 2
        screen.blit(title, (title_x, 20))

        # Linha separadora
        pygame.draw.line(screen, (60, 60, 70),
                         (50, 70), (self.game.screen_manager.window_width - 50, 70), 2)

        # Slots do time
        for slot in self.team_slots:
            slot.render(screen, self.slot_font, self.pokedex)

        # Label do grid
        grid_label = self.slot_font.render("POKÉMONS DISPONÍVEIS", True, (180, 180, 190))
        label_x = (self.game.screen_manager.window_width - grid_label.get_width()) // 2
        label_y = self.team_slots[0].rect.bottom + 20
        screen.blit(grid_label, (label_x, label_y))

        # Grid items
        for item in self.grid_items:
            item.render(screen, self.grid_font, self.pokedex)

        # Informação de página
        if self.total_pages > 1:
            page_text = self.page_font.render(
                f"Página {self.current_page + 1} de {self.total_pages}",
                True, (150, 150, 160)
            )
            page_rect = page_text.get_rect(
                center=(self.game.screen_manager.window_width // 2,
                        self.navigation.prev_page_button.centery)
            )
            screen.blit(page_text, page_rect)

        # Botões de navegação
        if self.navigation:
            self.navigation.render(
                screen, self.slot_font,
                len(self.game.player.team),
                self.current_page, self.total_pages
            )

        # Status do time
        team_status = f"Time: {len(self.game.player.team)}/6"
        status_color = (255, 255, 255) if len(self.game.player.team) > 0 else (150, 150, 150)
        status_text = self.slot_font.render(team_status, True, status_color)
        screen.blit(status_text, (20, self.game.screen_manager.window_height - 30))

        # Modal
        if self.event_handler.modal and self.event_handler.modal.visible:
            self.event_handler.modal.render(screen)