import pygame
import math
from src.scenes.team_select_scene.components.team_slot import TeamSlot
from src.scenes.team_select_scene.components.pokemon_grid_item import PokemonGridItem
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

        self.current_page = 0
        self.items_per_page = LAYOUT['GRID']['COLS'] * 3  # 3 linhas padrão
        self.rows_per_page = 3

    def create_layout(self, team, page_pokemon, page=0):
        """create_layout agora recebe apenas os pokémons da página atual"""
        screen_width = self.game.screen_manager.window_width
        screen_height = self.game.screen_manager.window_height

        self.current_page = page
        self._create_team_slots(screen_width, screen_height, team)
        self._create_grid(screen_width, screen_height, page_pokemon, page)  # AGORA usa page_pokemon
        self._create_buttons(screen_width, screen_height)

        return {
            'team_slots': self.team_slots,
            'grid_items': self.grid_items,
            'buttons': {
                'back': self.back_button,
                'start': self.start_button,
                'prev': self.prev_page_button,
                'next': self.next_page_button
            }
        }

    def _create_grid(self, screen_width, screen_height, page_pokemon, page):
        """Cria grid APENAS com os pokémons da página atual"""
        margin = LAYOUT['MARGIN']
        top_margin = LAYOUT['TOP_MARGIN']
        slot_height = LAYOUT['SLOT']['HEIGHT']

        grid_y = top_margin + slot_height + 40
        grid_height = screen_height - grid_y - 100

        # Calcula linhas por página baseado na altura disponível
        card_height = LAYOUT['GRID']['CARD_HEIGHT']
        card_spacing = LAYOUT['GRID']['SPACING']

        self.rows_per_page = max(1, grid_height // (card_height + card_spacing))
        self.items_per_page = LAYOUT['GRID']['COLS'] * self.rows_per_page

        # Cálculo do grid
        card_width = min(LAYOUT['GRID']['CARD_WIDTH'],
                         (screen_width - 2 * margin - (LAYOUT['GRID']['COLS'] - 1) * card_spacing)
                         // LAYOUT['GRID']['COLS'])

        grid_width = (LAYOUT['GRID']['COLS'] * card_width +
                      (LAYOUT['GRID']['COLS'] - 1) * card_spacing)
        grid_start_x = (screen_width - grid_width) // 2

        # Cria grid items DIRETO da lista page_pokemon
        self.grid_items = []
        for i, pokemon in enumerate(page_pokemon):
            row = i // LAYOUT['GRID']['COLS']
            col = i % LAYOUT['GRID']['COLS']

            card_x = grid_start_x + col * (card_width + card_spacing)
            card_y = grid_y + row * (card_height + card_spacing)

            item = PokemonGridItem(
                pokemon,
                card_x, card_y,
                card_width, card_height
            )
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
        margin = LAYOUT['MARGIN']
        button_width = LAYOUT['BUTTON']['WIDTH']
        button_height = LAYOUT['BUTTON']['HEIGHT']
        button_y = screen_height - 60

        self.back_button = pygame.Rect(margin, button_y, button_width, button_height)
        self.start_button = pygame.Rect(screen_width - button_width - margin,
                                        button_y, button_width, button_height)

        page_button_width = LAYOUT['BUTTON']['PAGE_WIDTH']
        self.prev_page_button = pygame.Rect(
            screen_width // 2 - page_button_width - 10,
            button_y, page_button_width, button_height
        )
        self.next_page_button = pygame.Rect(
            screen_width // 2 + 10,
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