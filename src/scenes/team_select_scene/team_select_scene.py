# src/scenes/team_select_scene/team_select_scene.py

import pygame
from src.scenes.base_scene import BaseScene
from src.scenes.game_scene.game_scene import GameScene
from src.scenes.team_select_scene.components.gradient_background import GradientBackground
from src.scenes.team_select_scene.components.pokemon_modal import PokemonModal
from src.scenes.team_select_scene.components.navigation_buttons import NavigationButtons
from src.scenes.team_select_scene.managers.layout_manager import LayoutManager
from src.scenes.team_select_scene.managers.pokemon_manager import PokemonManager
from src.scenes.team_select_scene.handlers.event_handler import EventHandler
from src.scenes.team_select_scene.utils.constants import FONT_SIZES
from src.data.pokedex import Pokedex


class TeamSelectScene(BaseScene):
    def __init__(self, game, chapter, phase):
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
        self.filters = None

        # State
        self.current_page = 0
        self.total_pages = 1
        self.layout_initialized = False

        # Fonts
        self.title_font = pygame.font.Font(None, FONT_SIZES['TITLE'])
        self.slot_font = pygame.font.Font(None, FONT_SIZES['SLOT'])
        self.grid_font = pygame.font.Font(None, FONT_SIZES['GRID'])
        self.page_font = pygame.font.Font(None, FONT_SIZES['PAGE'])

    def _initialize_layout(self):
        """Inicializa o layout da cena"""
        # PEGA OS POKÉMONS DA PÁGINA ATUAL COM FILTROS APLICADOS
        available_pokemon = self.pokemon_manager.get_available_pokemon(
            self.current_page,
            self.layout_manager.items_per_page
        )

        layout = self.layout_manager.create_layout(
            self.game.player.team,
            available_pokemon,
            self.current_page,
            self.pokemon_manager.current_sort,
            self.pokemon_manager.current_search
        )

        self.team_slots = layout['team_slots']
        self.grid_items = layout['grid_items']
        self.filters = layout.get('filters')
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

    def _refresh_grid(self):
        """Atualiza apenas o grid sem recriar todo o layout"""
        if not self.layout_initialized:
            return

        # Pega os pokémons atualizados com os filtros
        available_pokemon = self.pokemon_manager.get_available_pokemon(
            self.current_page,
            self.layout_manager.items_per_page
        )

        # Recria apenas os grid items
        screen_width = self.game.screen_manager.window_width
        screen_height = self.game.screen_manager.window_height

        margin = 30
        top_margin = 80
        slot_height = 110

        grid_label_y = top_margin + slot_height + 20
        filters_height = 100
        grid_y = grid_label_y + 35 + filters_height + 10

        card_height = 90
        card_spacing = 10

        card_width = min(140,
                         (screen_width - 2 * margin - (6 - 1) * card_spacing) // 6)

        grid_width = (6 * card_width + (6 - 1) * card_spacing)
        grid_start_x = (screen_width - grid_width) // 2

        # Recria os grid items
        self.layout_manager.grid_items = []
        for i, pokemon in enumerate(available_pokemon):
            row = i // 6
            col = i % 6

            card_x = grid_start_x + col * (card_width + card_spacing)
            card_y = grid_y + row * (card_height + card_spacing)

            from src.scenes.team_select_scene.components.pokemon_grid_item import PokemonGridItem
            item = PokemonGridItem(pokemon, card_x, card_y, card_width, card_height)
            self.layout_manager.grid_items.append(item)

        self.grid_items = self.layout_manager.grid_items
        self.total_pages = self.pokemon_manager.get_page_count(self.layout_manager.items_per_page)

    def handle_event(self, event):
        # Verifica se precisa recriar layout
        if not self.layout_initialized:
            self._initialize_layout()

        result = self.event_handler.handle_event(
            event, self.team_slots, self.grid_items, self.filters,
            self.navigation.back_button if self.navigation else None,
            self.navigation.start_button if self.navigation else None,
            self.navigation.prev_page_button if self.navigation else None,
            self.navigation.next_page_button if self.navigation else None,
            self.current_page, self.total_pages
        )

        if result:
            self._handle_action(result)

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

    def _handle_action(self, action):
        action_type = action.get('type')

        if action_type == 'SORT_CHANGED':
            sort_type = action['sort']
            self.pokemon_manager.set_sort(sort_type)
            if self.filters:
                self.filters.update_sort_state(sort_type)
            self.current_page = 0
            self.layout_initialized = False

        elif action_type == 'SEARCH_CHANGED':
            search_text = action['search']
            self.pokemon_manager.set_search(search_text)
            if self.filters:
                self.filters.update_search_state(search_text)
            self.current_page = 0
            # Não recria o layout, apenas atualiza o grid
            self._refresh_grid()

        elif action_type == 'GO_BACK':
            from src.scenes.phase_selector.phase_select_scene import PhaseSelectScene
            self.game.phase_select_scene = PhaseSelectScene(self.game)
            self.game.current_scene = self.game.phase_select_scene

        elif action_type == 'START_GAME':
            print("Iniciando batalha com time:",
                  [p.name for p in self.game.player.team])
            self.game.game_scene = GameScene(self.game, self.chapter, self.phase)
            self.game.current_scene = self.game.game_scene

        elif action_type == 'PREV_PAGE':
            self.current_page -= 1
            self.layout_initialized = False

        elif action_type == 'NEXT_PAGE':
            self.current_page += 1
            self.layout_initialized = False

        elif action_type == 'SLOT_CLICK':
            slot = action['slot']
            for s in self.team_slots:
                s.is_selected = (s.slot_index == action['slot_index'])
            if slot.pokemon:
                modal = PokemonModal(self.game, slot.pokemon)
                self.event_handler.set_modal(modal)

        elif action_type == 'GRID_CLICK':
            pokemon = action['pokemon']
            modal = PokemonModal(self.game, pokemon)
            self.event_handler.set_modal(modal)

        elif action_type == 'MODAL_ACTION':
            self._handle_modal_action()

        elif action_type == 'CLOSE_MODAL':
            self.event_handler.set_modal(None)

        elif action_type == 'RESIZE':
            pass

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

        # Renderiza filtros
        if self.filters:
            self.filters.render(screen, self.slot_font)

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

        # Mostra contagem de resultados dos filtros
        if self.filters and (self.pokemon_manager.current_search or self.pokemon_manager.current_sort != "capture"):
            total_filtered = self.pokemon_manager.get_total_filtered_count()
            total_pc = len(self.game.player.pc_box)

            if total_filtered > 0:
                filter_info = f"Mostrando {total_filtered} de {total_pc} Pokémon"
            else:
                filter_info = "Nenhum Pokémon encontrado"

            info_font = pygame.font.Font(None, 14)
            info_text = info_font.render(filter_info, True, (150, 150, 160))

            if self.filters:
                info_y = self.filters.rect.bottom + 5
            else:
                info_y = label_y + 35

            screen.blit(info_text, (20, info_y))

            if total_filtered == 0:
                empty_font = pygame.font.Font(None, 24)
                empty_text = empty_font.render("Nenhum Pokémon encontrado com esses filtros", True, (150, 150, 160))
                empty_x = (self.game.screen_manager.window_width - empty_text.get_width()) // 2
                empty_y = label_y + 100
                screen.blit(empty_text, (empty_x, empty_y))

        # Status do time
        team_status = f"Time: {len(self.game.player.team)}/6"
        status_color = (255, 255, 255) if len(self.game.player.team) > 0 else (150, 150, 150)
        status_text = self.slot_font.render(team_status, True, status_color)
        screen.blit(status_text, (20, self.game.screen_manager.window_height - 30))

        # Modal
        if self.event_handler.modal and self.event_handler.modal.visible:
            self.event_handler.modal.render(screen)