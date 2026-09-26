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
        self.items_per_page = 0
        self.rows_per_page = 0
        self.cols_per_page = 0

    # =================================================================
    # API PÚBLICA
    # =================================================================
    def compute_geometry(self):
        sw = self.game.screen_manager.window_width
        sh = self.game.screen_manager.window_height

        margin = LAYOUT['MARGIN']
        top_margin = LAYOUT['TOP_MARGIN']
        slot_spacing = LAYOUT['SLOT']['SPACING']
        grid_spacing = LAYOUT['GRID']['SPACING']

        # =================================================================
        # SLOTS DO TIME — SEMPRE 6 NA LINHA, NUNCA SAEM DA TELA
        # =================================================================
        # Largura máxima que cada slot pode ter para caber 6 + espaços
        max_slot_w_for_screen = (sw - 2 * margin - 5 * slot_spacing) // 6
        slot_w = max(
            LAYOUT['SLOT']['MIN_W'],
            min(LAYOUT['SLOT']['MAX_W'], max_slot_w_for_screen),
        )
        # Se mesmo o MIN_W não couber, encolhe para o que couber
        if slot_w > max_slot_w_for_screen:
            slot_w = max(80, max_slot_w_for_screen)

        slot_h = max(LAYOUT['SLOT']['MIN_H'],
                     min(LAYOUT['SLOT']['MAX_H'], int(slot_w * 0.80)))

        slots_total_w = 6 * slot_w + 5 * slot_spacing
        slots_x = (sw - slots_total_w) // 2
        slots_y = top_margin

        # =================================================================
        # FILTROS
        # =================================================================
        filters_max_w = min(LAYOUT['FILTERS']['MAX_WIDTH'],
                            slots_total_w)  # não mais largo que o time
        filters_w = min(filters_max_w, sw - 2 * margin)
        filters_x = (sw - filters_w) // 2
        filters_y = slots_y + slot_h + 24
        filters_h = LAYOUT['FILTERS']['HEIGHT']

        # =================================================================
        # ÁREA DO GRID — LIMITADA À LARGURA DO TIME
        # =================================================================
        footer_h = LAYOUT['BUTTON']['HEIGHT'] + 30
        grid_y = filters_y + filters_h + 12
        grid_bottom = sh - footer_h
        grid_area_h = max(100, grid_bottom - grid_y)

        # ★ LARGURA: nunca maior que slots_total_w
        grid_area_w = min(slots_total_w, sw - 2 * margin)

        # =================================================================
        # ALGORITMO AUTO-FIT
        # =================================================================
        card_min_w = LAYOUT['GRID']['CARD_MIN_W']
        card_max_w = LAYOUT['GRID']['CARD_MAX_W']
        card_min_h = LAYOUT['GRID']['CARD_MIN_H']
        card_max_h = LAYOUT['GRID']['CARD_MAX_H']
        aspect = LAYOUT['GRID']['ASPECT']

        cols = max(1, (grid_area_w + grid_spacing) // (card_min_w + grid_spacing))
        rows = max(1, (grid_area_h + grid_spacing) // (card_min_h + grid_spacing))

        card_w = (grid_area_w - (cols - 1) * grid_spacing) // cols
        card_h = (grid_area_h - (rows - 1) * grid_spacing) // rows

        if card_w / card_h > aspect:
            card_w = int(card_h * aspect)
        else:
            card_h = int(card_w / aspect)

        card_w = max(card_min_w, min(card_max_w, card_w))
        card_h = max(card_min_h, min(card_max_h, card_h))

        # Se com cols atuais o card ficar < mínimo, reduz colunas
        while cols > 1 and (card_w < card_min_w or card_h < card_min_h):
            cols -= 1
            card_w = (grid_area_w - (cols - 1) * grid_spacing) // cols
            card_h = (grid_area_h - (rows - 1) * grid_spacing) // rows
            if card_w / card_h > aspect:
                card_w = int(card_h * aspect)
            else:
                card_h = int(card_w / aspect)

        card_w = max(card_min_w, min(card_max_w, card_w))
        card_h = max(card_min_h, min(card_max_h, card_h))

        # Centraliza grid dentro da área limitada
        grid_total_w = cols * card_w + (cols - 1) * grid_spacing
        grid_x = (sw - grid_total_w) // 2

        # Se estourar altura, remove linhas
        grid_total_h = rows * card_h + (rows - 1) * grid_spacing
        while rows > 1 and grid_total_h > grid_area_h:
            rows -= 1
            card_h = (grid_area_h - (rows - 1) * grid_spacing) // rows
            if card_w / card_h > aspect:
                card_w = int(card_h * aspect)
            else:
                card_h = int(card_w / aspect)
            card_h = max(card_min_h, min(card_max_h, card_h))
            card_w = max(card_min_w, min(card_max_w, card_w))
            grid_total_w = cols * card_w + (cols - 1) * grid_spacing
            grid_x = (sw - grid_total_w) // 2
            grid_total_h = rows * card_h + (rows - 1) * grid_spacing

        # =================================================================
        # BOTÕES
        # =================================================================
        btn_y = sh - LAYOUT['BUTTON']['HEIGHT'] - 20
        btn_w = LAYOUT['BUTTON']['WIDTH']
        btn_h = LAYOUT['BUTTON']['HEIGHT']
        page_btn_w = LAYOUT['BUTTON']['PAGE_WIDTH']

        back_rect = pygame.Rect(margin + 10, btn_y, btn_w, btn_h)
        start_rect = pygame.Rect(sw - btn_w - margin - 10, btn_y, btn_w, btn_h)
        center_x = sw // 2
        page_gap = 60
        prev_rect = pygame.Rect(center_x - page_btn_w - page_gap, btn_y, page_btn_w, btn_h)
        next_rect = pygame.Rect(center_x + page_gap, btn_y, page_btn_w, btn_h)

        return {
            'slot_w': slot_w, 'slot_h': slot_h, 'slot_spacing': slot_spacing,
            'slots_x': slots_x, 'slots_y': slots_y, 'slots_total_w': slots_total_w,
            'filters_x': filters_x, 'filters_y': filters_y,
            'filters_w': filters_w, 'filters_h': filters_h,
            'grid_x': grid_x, 'grid_y': grid_y,
            'grid_w': grid_total_w, 'grid_h': grid_total_h,
            'card_w': card_w, 'card_h': card_h,
            'card_spacing': grid_spacing,
            'cols': cols, 'rows': rows,
            'back_rect': back_rect, 'start_rect': start_rect,
            'prev_rect': prev_rect, 'next_rect': next_rect,
        }
    # =================================================================
    # LAYOUT PRINCIPAL
    # =================================================================
    def create_layout(self, team, page_pokemon, page=0,
                      current_sort="capture", current_search=""):
        self.current_page = page

        # ★ 1) Calcula geometria E atualiza items_per_page
        geo = self.refresh_items_per_page()

        self._create_team_slots(team, geo)
        self._create_filters(current_sort, current_search, geo)
        self._create_grid(page_pokemon, geo)
        self._create_buttons(geo)

        return {
            'team_slots': self.team_slots,
            'grid_items': self.grid_items,
            'filters': self.filters,
            'buttons': {
                'back': self.back_button,
                'start': self.start_button,
                'prev': self.prev_page_button,
                'next': self.next_page_button,
            },
            'geometry': geo,
        }

    # =================================================================
    # SLOTS
    # =================================================================
    def _create_team_slots(self, team, geo):
        self.team_slots = []
        for i in range(6):
            x = geo['slots_x'] + i * (geo['slot_w'] + geo['slot_spacing'])
            y = geo['slots_y']
            slot = TeamSlot(x, y, geo['slot_w'], geo['slot_h'], i)
            if i < len(team):
                slot.set_pokemon(team[i])
            self.team_slots.append(slot)

    # =================================================================
    # FILTROS
    # =================================================================
    def _create_filters(self, current_sort, current_search, geo):
        self.filters = PokemonFilters(
            geo['filters_x'], geo['filters_y'], geo['filters_w']
        )
        self.filters.update_sort_state(current_sort)
        self.filters.update_search_state(current_search)
        self.filters.update_filter_state("all")

    # =================================================================
    # GRID
    # =================================================================
    def _create_grid(self, page_pokemon, geo):
        self.grid_items = []
        cols = geo['cols']
        for i, pokemon in enumerate(page_pokemon):
            row = i // cols
            col = i % cols
            x = geo['grid_x'] + col * (geo['card_w'] + geo['card_spacing'])
            y = geo['grid_y'] + row * (geo['card_h'] + geo['card_spacing'])
            item = PokemonGridItem(pokemon, x, y, geo['card_w'], geo['card_h'])
            self.grid_items.append(item)

    # =================================================================
    # BOTÕES
    # =================================================================
    def _create_buttons(self, geo):
        self.back_button = geo['back_rect']
        self.start_button = geo['start_rect']
        self.prev_page_button = geo['prev_rect']
        self.next_page_button = geo['next_rect']

    def refresh_items_per_page(self):
        """
        Recalcula `cols_per_page`, `rows_per_page` e `items_per_page`
        com base na geometria atual. DEVE ser chamado antes de qualquer
        consulta ao PokemonManager (get_available_pokemon / get_page_count).
        """
        geo = self.compute_geometry()
        self.cols_per_page = geo['cols']
        self.rows_per_page = geo['rows']
        self.items_per_page = geo['cols'] * geo['rows']
        return geo

    # =================================================================
    # MODAL
    # =================================================================
    def update_modal_position(self, modal):
        sw = self.game.screen_manager.window_width
        sh = self.game.screen_manager.window_height
        modal.width = int(sw * 0.94)
        modal.height = int(sh * 0.94)
        modal.x = (sw - modal.width) // 2
        modal.y = (sh - modal.height) // 2
        modal.rect = pygame.Rect(modal.x, modal.y, modal.width, modal.height)

        cs = max(32, int(sh * 0.046))
        pad = max(14, int(modal.width * 0.016))
        modal.close_button = pygame.Rect(
            modal.rect.right - cs - pad, modal.rect.y + pad, cs, cs
        )

        footer_h = max(40, int(modal.height * 0.06))
        footer_y = modal.rect.bottom - pad - footer_h
        bw = max(150, int(modal.width * 0.16))
        gap_b = max(10, int(modal.width * 0.012))
        total = bw * 2 + gap_b
        bx = modal.rect.centerx - total // 2

        modal.action_button = pygame.Rect(bx, footer_y, bw, footer_h)
        modal.release_button = pygame.Rect(bx + bw + gap_b, footer_y, bw, footer_h)