# src/scenes/pokedex_scene/pokedex_scene.py

"""
Tela da Pokédex
"""
import pygame
from src.scenes.base_scene import BaseScene
from src.data.pokedex import Pokedex
from src.scenes.pokedex_scene.utils.constants import ( COLORS, FILTERS, SIZES, REGIONS)
from src.scenes.pokedex_scene.components.search_bar import SearchBar
from src.scenes.pokedex_scene.components.pokedex_list import PokedexList
from src.scenes.pokedex_scene.components.pokemon_detail import PokemonDetail
from src.scenes.pokedex_scene.components.dropdown import Dropdown


class PokedexScene(BaseScene):
    def __init__(self, game):
        super().__init__(game)

        self.pokedex = Pokedex()
        self.player = game.player
        self.filter_type = FILTERS['ALL']
        self.region = REGIONS['ALL']

        self.search_bar = None
        self.pokedex_list = None
        self.pokemon_detail = None
        self.filter_dropdown = None
        self.region_dropdown = None

        self.layout_initialized = False
        self.last_window_size = (
            self.screen_manager.window_width,
            self.screen_manager.window_height,
        )

        self.fonts = self._create_fonts()

        self.back_button = None
        self.back_hover = False

        self.total_seen = 0
        self.total_caught = 0
        self.total_pokemon = 0

        self.current_selected_id = None

        print("[POKEDEX_SCENE] Inicializada")

    # ==========================================================
    # FONTES E RESIZE
    # ==========================================================
    def _create_fonts(self):
        base_size = max(14, self.screen_manager.window_height // 40)
        return {
            'title': pygame.font.Font(None, base_size * 2),
            'large': pygame.font.Font(None, base_size + 4),
            'medium': pygame.font.Font(None, base_size),
            'small': pygame.font.Font(None, base_size - 2),
            'tiny': pygame.font.Font(None, base_size - 4),
        }

    def _check_resize(self):
        current_size = (self.screen_manager.window_width,
                        self.screen_manager.window_height)
        if current_size != self.last_window_size:
            self.last_window_size = current_size
            self.layout_initialized = False
            self.fonts = self._create_fonts()
            return True
        return False

    # ==========================================================
    # LAYOUT
    # ==========================================================
    def _create_layout(self):
        print("[POKEDEX_SCENE] Criando layout...")
        vx = self.screen_manager.viewport_x
        vy = self.screen_manager.viewport_y
        vw = self.screen_manager.viewport_width
        vh = self.screen_manager.viewport_height

        padding = SIZES['padding']
        gap = SIZES['gap']

        # ===== HEADER =====
        header_y = vy + padding
        back_size = 40
        self.back_button = pygame.Rect(vx + padding, header_y, back_size, back_size)

        # ===== SEARCH BAR =====
        search_y = header_y + back_size + gap
        search_width = min(350, vw * 0.35)
        search_height = 34
        search_x = vx + padding
        self.search_bar = SearchBar(search_x, search_y, search_width, search_height)

        # ===== DROPDOWNS (Região + Filtro) =====
        dd_y = search_y + search_height + gap
        dd_height = 32

        region_options = [
            {'key': REGIONS['ALL'],   'label': "TODAS AS REGIÕES"},
            {'key': REGIONS['KANTO'], 'label': "KANTO (GEN 1)"},
            {'key': REGIONS['JOHTO'], 'label': "JOHTO (GEN 2)"},
        ]
        filter_options = [
            {'key': FILTERS['ALL'],        'label': "TODOS"},
            {'key': FILTERS['CAUGHT'],     'label': "CAPTURADOS"},
            {'key': FILTERS['SEEN'],       'label': "VISTOS"},
            {'key': FILTERS['NOT_CAUGHT'], 'label': "NÃO CAPTURADOS"},
            {'key': FILTERS['UNSEEN'],     'label': "NÃO VISTOS"},
        ]

        region_w = 200
        filter_w = 200

        self.region_dropdown = Dropdown(
            vx + padding, dd_y, region_w, dd_height,
            region_options, default_key=self.region
        )
        self.region_dropdown.on_change = self._on_region_change

        self.filter_dropdown = Dropdown(
            vx + padding + region_w + gap, dd_y, filter_w, dd_height,
            filter_options, default_key=self.filter_type
        )
        self.filter_dropdown.on_change = self._on_filter_change

        # ===== LISTA E DETALHE =====
        list_y = dd_y + dd_height + gap
        bottom_margin = 50
        list_height = vh - (list_y - vy) - bottom_margin - padding

        list_width = int(vw * 0.32)
        list_x = vx + padding

        detail_width = vw - list_width - padding * 3
        detail_x = list_x + list_width + padding

        self.pokedex_list = PokedexList(list_x, list_y, list_width, list_height)
        self.pokedex_list.on_item_click = self._on_list_item_click

        self.pokemon_detail = PokemonDetail(detail_x, list_y, detail_width, list_height)

        self._update_pokedex_list()
        self._update_counts()

        self.layout_initialized = True
        print("[POKEDEX_SCENE] Layout criado!")

    # ==========================================================
    # CALLBACKS
    # ==========================================================
    def _on_list_item_click(self, pokemon_id):
        self.current_selected_id = pokemon_id
        self._update_detail(pokemon_id)

    def _on_filter_change(self, new_filter):
        print(f"[POKEDEX_SCENE] Filtro -> {new_filter}")
        self.filter_type = new_filter
        self._update_pokedex_list()

    def _on_region_change(self, new_region):
        print(f"[POKEDEX_SCENE] Região -> {new_region}")
        self.region = new_region
        self._update_pokedex_list()

    # ==========================================================
    # UPDATES
    # ==========================================================
    def _update_counts(self):
        self.total_seen = len(self.player.seen_pokemon)
        self.total_caught = len(self.player.caught_pokemon)
        self.total_pokemon = len(self.pokedex.pokemon_data)

    def _update_pokedex_list(self):
        if not self.pokedex_list:
            return
        search_text = self.search_bar.get_search_text() if self.search_bar else ""
        region = self.region_dropdown.get_selected_key() if self.region_dropdown else 'all'

        self.pokedex_list.update_items(
            self.pokedex.pokemon_data,
            self.player,
            search_text,
            self.filter_type,
            region,
        )

        selected_item = self.pokedex_list.get_selected_item()
        if selected_item:
            self.current_selected_id = selected_item.pokemon_id
            self._update_detail(selected_item.pokemon_id)

    def _update_detail(self, pokemon_id):
        if not self.pokemon_detail:
            return
        is_caught = pokemon_id in self.player.caught_pokemon
        is_seen = pokemon_id in self.player.seen_pokemon
        pokemon_data = self.pokedex.get_pokemon(pokemon_id)
        self.pokemon_detail.set_pokemon(pokemon_id, pokemon_data, is_caught, is_seen)

        if self.pokedex_list:
            self.pokedex_list.selected_id = pokemon_id

    def _close_open_dropdown(self):
        closed = False
        if self.filter_dropdown and self.filter_dropdown.is_open:
            self.filter_dropdown.close()
            closed = True
        if self.region_dropdown and self.region_dropdown.is_open:
            self.region_dropdown.close()
            closed = True
        return closed

    # ==========================================================
    # EVENTOS
    # ==========================================================
    def handle_event(self, event):
        if self._check_resize():
            self._create_layout()

        if event.type == pygame.KEYDOWN:
            if event.key == pygame.K_ESCAPE:
                # Se algum dropdown estiver aberto, só fecha
                if self._close_open_dropdown():
                    return
                self._go_back()
                return
            elif event.key == pygame.K_p:
                self.toggle_pause()

        if event.type == pygame.VIDEORESIZE:
            self.layout_initialized = False
            return

        # ===== DROPDOWNS (prioridade) =====
        dropdowns = [d for d in (self.filter_dropdown, self.region_dropdown) if d]
        for dd in dropdowns:
            if dd.handle_event(event):
                # Se um abriu, fecha os outros
                for other in dropdowns:
                    if other is not dd and other.is_open:
                        other.close()
                return

        # ===== BOTÃO VOLTAR =====
        if event.type == pygame.MOUSEMOTION and self.back_button:
            self.back_hover = self.back_button.collidepoint(event.pos)

        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            if self.back_button and self.back_button.collidepoint(event.pos):
                self._go_back()
                return

        # ===== SEARCH BAR =====
        if self.search_bar:
            result = self.search_bar.handle_event(event)
            if result is not None:
                self._update_pokedex_list()

        # ===== LISTA =====
        if self.pokedex_list:
            result = self.pokedex_list.handle_event(event)
            if result and isinstance(result, int):
                self.current_selected_id = result
                self._update_detail(result)

        # ===== DETALHE =====
        if self.pokemon_detail:
            result = self.pokemon_detail.handle_event(event, self.pokedex)
            if result and result.get('action') == 'navigate':
                new_id = result['pokemon_id']
                self.current_selected_id = new_id
                self._update_detail(new_id)
                if self.pokedex_list:
                    self.pokedex_list.update(self.screen_manager.get_delta_time())

    def fixed_update(self, dt):
        if not self.layout_initialized:
            self._create_layout()
            return
        if self.search_bar:
            self.search_bar.update(dt)
        if self.pokedex_list:
            self.pokedex_list.update(dt)
        if self.pokemon_detail:
            self.pokemon_detail.update(dt)

    # ==========================================================
    # RENDER
    # ==========================================================
    def render(self, screen):
        self._draw_gradient_background(screen)

        if not self.layout_initialized:
            self._create_layout()

        vx = self.screen_manager.viewport_x
        vy = self.screen_manager.viewport_y
        vw = self.screen_manager.viewport_width

        # ===== HEADER =====
        self._render_back_button(screen)

        title = self.fonts['title'].render("POKEDEX", True, COLORS['text_accent'])
        title_x = vx + (vw - title.get_width()) // 2
        title_y = vy + SIZES['padding'] + 5
        screen.blit(title, (title_x, title_y))

        line_y = title_y + title.get_height() + 6
        line_width = 120
        line_x = vx + (vw - line_width) // 2
        pygame.draw.line(screen, COLORS['border_gold'],
                         (line_x, line_y), (line_x + line_width, line_y), 2)

        stats_text = (f"Total: {self.total_pokemon}  |  "
                      f"Vistos: {self.total_seen}  |  "
                      f"Capturados: {self.total_caught}")
        stats_font = pygame.font.Font(None, 24)
        stats_surf = stats_font.render(stats_text, True, COLORS['text_secondary'])
        stats_x = vx + vw - SIZES['padding'] - stats_surf.get_width()
        stats_y = vy + SIZES['padding'] + 8
        screen.blit(stats_surf, (stats_x, stats_y))

        # ===== SEARCH =====
        if self.search_bar:
            self.search_bar.render(screen, self.fonts['medium'])

        # ===== DROPDOWN HEADERS =====
        if self.region_dropdown:
            self.region_dropdown.render_header(screen, self.fonts['medium'])
        if self.filter_dropdown:
            self.filter_dropdown.render_header(screen, self.fonts['medium'])

        # ===== LISTA =====
        if self.pokedex_list:
            self.pokedex_list.render(
                screen, self.pokedex,
                self.fonts['medium'],
                self.fonts['small'],
            )

        # ===== DETALHE =====
        if self.pokemon_detail:
            self.pokemon_detail.render(screen, self.pokedex, self.fonts)

        # ===== CONTADOR =====
        if self.pokedex_list:
            count = self.pokedex_list.get_count()
            count_text = f"Mostrando {count} de {self.total_pokemon} Pokemon"
            count_surf = self.fonts['tiny'].render(
                count_text, True, COLORS['text_secondary'])
            count_x = vx + SIZES['padding']
            count_y = self.pokedex_list.rect.bottom + 5
            screen.blit(count_surf, (count_x, count_y))

        # ===== INSTRUÇÕES =====
        self._render_instructions(screen)

        # ===== DROPDOWN OPTIONS (por último = acima de tudo) =====
        if self.region_dropdown:
            self.region_dropdown.render_options(screen, self.fonts['medium'])
        if self.filter_dropdown:
            self.filter_dropdown.render_options(screen, self.fonts['medium'])

        if self.paused:
            self._render_pause_overlay(screen)

    # ==========================================================
    # RENDER HELPERS
    # ==========================================================
    def _render_back_button(self, screen):
        if not self.back_button:
            return
        bg_color = (50, 50, 55) if not self.back_hover else (70, 70, 80)
        border_color = (90, 90, 100) if not self.back_hover else COLORS['text_accent']
        pygame.draw.rect(screen, bg_color, self.back_button, border_radius=6)
        pygame.draw.rect(screen, border_color, self.back_button, 2, border_radius=6)
        back_text = pygame.font.Font(None, 32).render(
            "<", True, COLORS['text_primary'])
        screen.blit(back_text, back_text.get_rect(center=self.back_button.center))

    def _render_instructions(self, screen):
        inst_font = pygame.font.Font(None, 13)
        inst_text = ("ESC voltar  |  P pausar  |  "
                     "Use os dropdowns para filtrar por Região e Status")
        inst_surf = inst_font.render(inst_text, True, COLORS['text_secondary'])

        vx = self.screen_manager.viewport_x
        vy = self.screen_manager.viewport_y
        vw = self.screen_manager.viewport_width
        vh = self.screen_manager.viewport_height

        inst_x = vx + (vw - inst_surf.get_width()) // 2
        inst_y = vy + vh - 20
        screen.blit(inst_surf, (inst_x, inst_y))

    def _draw_gradient_background(self, screen):
        if (not hasattr(self, '_bg_cache')
                or self._bg_cache.get_width() != self.screen_manager.window_width
                or self._bg_cache.get_height() != self.screen_manager.window_height):
            self._bg_cache = pygame.Surface(
                (self.screen_manager.window_width,
                 self.screen_manager.window_height)
            )
            for i in range(self.screen_manager.window_height):
                t = i / self.screen_manager.window_height
                r = int(10 + t * 15)
                g = int(12 + t * 18)
                b = int(20 + t * 25)
                pygame.draw.line(self._bg_cache, (r, g, b), (0, i),
                                 (self.screen_manager.window_width, i))
        screen.blit(self._bg_cache, (0, 0))

    def _render_pause_overlay(self, screen):
        overlay = pygame.Surface(
            (self.screen_manager.window_width, self.screen_manager.window_height))
        overlay.set_alpha(180)
        overlay.fill((10, 10, 10))
        screen.blit(overlay, (0, 0))
        pause_font = pygame.font.Font(None, 60)
        pause_text = pause_font.render("PAUSADO", True, COLORS['text_primary'])
        text_x = (self.screen_manager.window_width - pause_text.get_width()) // 2
        text_y = (self.screen_manager.window_height - pause_text.get_height()) // 2
        screen.blit(pause_text, (text_x, text_y))

    def _go_back(self):
        from src.scenes.phase_selector.phase_select_scene import PhaseSelectScene
        self.game.current_scene = PhaseSelectScene(self.game)