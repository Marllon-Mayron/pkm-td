# src/scenes/team_select_scene/managers/layout_manager.py

import pygame
from src.scenes.team_select_scene.components.team_slot import TeamSlot
from src.scenes.team_select_scene.components.pokemon_grid_item import PokemonGridItem
from src.scenes.team_select_scene.components.pokemon_filters import PokemonFilters
from src.scenes.team_select_scene.utils.constants import LAYOUT


class LayoutManager:
    def __init__(self, game):
        self.game = game
        self.team_slots = []
        self.grid_items = []
        self.back_button = None
        self.start_button = None
        self.prev_page_button = None
        self.next_page_button = None
        self.filters = None

        self.current_page = 0
        self.items_per_page = LAYOUT['GRID']['COLS'] * 3
        self.rows_per_page = 3

    def create_layout(self, team, page_pokemon, page=0, current_sort="capture", current_search=""):
        screen_width = self.game.screen_manager.window_width
        screen_height = self.game.screen_manager.window_height

        self.current_page = page
        self._create_team_slots(screen_width, screen_height, team)
        self._create_filters(screen_width, screen_height, current_sort, current_search)
        self._create_grid(screen_width, screen_height, page_pokemon, page)
        self._create_buttons(screen_width, screen_height)

        return {
            'team_slots': self.team_slots,
            'grid_items': self.grid_items,
            'filters': self.filters,
            'buttons': {
                'back': self.back_button,
                'start': self.start_button,
                'prev': self.prev_page_button,
                'next': self.next_page_button
            }
        }

    def _create_filters(self, screen_width, screen_height, current_sort, current_search):
        margin = LAYOUT['MARGIN']
        top_margin = LAYOUT['TOP_MARGIN']
        slot_height = LAYOUT['SLOT']['HEIGHT']

        grid_label_y = top_margin + slot_height + 20
        filters_y = grid_label_y + 35

        # Largura máxima da área de filtros, centralizada
        max_width = LAYOUT['FILTERS']['MAX_WIDTH']
        filter_width = min(max_width, screen_width - 2 * margin)
        filter_x = (screen_width - filter_width) // 2

        self.filters = PokemonFilters(filter_x, filters_y, filter_width)
        self.filters.update_sort_state(current_sort)
        self.filters.update_search_state(current_search)
        self.filters.update_filter_state("all")

    def _create_grid(self, screen_width, screen_height, page_pokemon, page):
        margin = LAYOUT['MARGIN']
        top_margin = LAYOUT['TOP_MARGIN']
        slot_height = LAYOUT['SLOT']['HEIGHT']
        filters_height = LAYOUT['FILTERS']['HEIGHT'] + 20  # espaço extra

        grid_label_y = top_margin + slot_height + 20
        grid_y = grid_label_y + 35 + filters_height + 10

        grid_height = screen_height - grid_y - 100

        card_height = LAYOUT['GRID']['CARD_HEIGHT']
        card_spacing = LAYOUT['GRID']['SPACING']

        self.rows_per_page = max(1, grid_height // (card_height + card_spacing))
        self.items_per_page = LAYOUT['GRID']['COLS'] * self.rows_per_page

        card_width = min(LAYOUT['GRID']['CARD_WIDTH'],
                         (screen_width - 2 * margin - (LAYOUT['GRID']['COLS'] - 1) * card_spacing)
                         // LAYOUT['GRID']['COLS'])

        grid_width = (LAYOUT['GRID']['COLS'] * card_width +
                      (LAYOUT['GRID']['COLS'] - 1) * card_spacing)
        grid_start_x = (screen_width - grid_width) // 2

        self.grid_items = []
        for i, pokemon in enumerate(page_pokemon):
            row = i // LAYOUT['GRID']['COLS']
            col = i % LAYOUT['GRID']['COLS']

            card_x = grid_start_x + col * (card_width + card_spacing)
            card_y = grid_y + row * (card_height + card_spacing)

            item = PokemonGridItem(pokemon, card_x, card_y, card_width, card_height)
            self.grid_items.append(item)

    def _create_team_slots(self, screen_width, screen_height, team):
        margin = LAYOUT['MARGIN']
        top_margin = LAYOUT['TOP_MARGIN']

        slot_width = min(LAYOUT['SLOT']['WIDTH'],
                         (screen_width - 2 * margin) // 6 - LAYOUT['SLOT']['SPACING'])
        slot_height = LAYOUT['SLOT']['HEIGHT']

        slots_total_width = 6 * slot_width + 5 * LAYOUT['SLOT']['SPACING']
        slots_start_x = (screen_width - slots_total_width) // 2

        self.team_slots = []
        for i in range(6):
            slot_x = slots_start_x + i * (slot_width + LAYOUT['SLOT']['SPACING'])
            slot_y = top_margin

            slot = TeamSlot(slot_x, slot_y, slot_width, slot_height, i)
            if i < len(team):
                slot.set_pokemon(team[i])
            self.team_slots.append(slot)

    def _create_buttons(self, screen_width, screen_height):
        margin = LAYOUT['MARGIN'] + 20
        button_width = LAYOUT['BUTTON']['WIDTH']
        button_height = LAYOUT['BUTTON']['HEIGHT']
        button_y = screen_height - 60

        # Botão VOLTAR
        self.back_button = pygame.Rect(margin, button_y, button_width, button_height)

        # Botão INICIAR
        self.start_button = pygame.Rect(screen_width - button_width - margin,
                                        button_y, button_width, button_height)

        page_button_width = LAYOUT['BUTTON']['PAGE_WIDTH']
        page_gap = 60
        center_x = screen_width // 2

        self.prev_page_button = pygame.Rect(
            center_x - page_button_width - page_gap,
            button_y, page_button_width, button_height
        )
        self.next_page_button = pygame.Rect(
            center_x + page_gap,
            button_y, page_button_width, button_height
        )

    def update_modal_position(self, modal):
        modal.width = int(self.game.screen_manager.window_width * 0.7)
        modal.height = int(self.game.screen_manager.window_height * 0.7)
        modal.x = (self.game.screen_manager.window_width - modal.width) // 2
        modal.y = (self.game.screen_manager.window_height - modal.height) // 2
        modal.rect = pygame.Rect(modal.x, modal.y, modal.width, modal.height)
        modal.close_button = pygame.Rect(modal.x + modal.width - 40, modal.y + 10, 30, 30)
        modal.action_button = pygame.Rect(
            modal.x + (modal.width - 150) // 2,
            modal.y + modal.height - 70, 150, 40
        )