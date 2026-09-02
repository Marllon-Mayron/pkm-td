# src/scenes/pokedex_scene/pokedex_scene.py

"""
Tela da Pokédex - LAYOUT ORGANIZADO COM LOGS
"""
import pygame
from src.scenes.base_scene import BaseScene
from src.data.pokedex import Pokedex
from src.scenes.pokedex_scene.utils.constants import COLORS, FILTERS, SIZES
from src.scenes.pokedex_scene.components.search_bar import SearchBar
from src.scenes.pokedex_scene.components.pokedex_list import PokedexList
from src.scenes.pokedex_scene.components.pokemon_detail import PokemonDetail


class PokedexScene(BaseScene):
    def __init__(self, game):
        super().__init__(game)

        self.pokedex = Pokedex()
        self.player = game.player
        self.filter_type = FILTERS['ALL']

        self.search_bar = None
        self.pokedex_list = None
        self.pokemon_detail = None
        self.filter_buttons = []

        self.layout_initialized = False
        self.last_window_size = (self.screen_manager.window_width, self.screen_manager.window_height)

        self.fonts = self._create_fonts()

        self.back_button = None
        self.back_hover = False

        self.total_seen = 0
        self.total_caught = 0
        self.total_pokemon = 0

        self.current_selected_id = None

        print("[POKEDEX_SCENE] Inicializada")

    def _create_fonts(self):
        base_size = max(14, self.screen_manager.window_height // 40)
        return {
            'title': pygame.font.Font(None, base_size * 2),
            'large': pygame.font.Font(None, base_size + 4),
            'medium': pygame.font.Font(None, base_size),
            'small': pygame.font.Font(None, base_size - 2),
            'tiny': pygame.font.Font(None, base_size - 4)
        }

    def _check_resize(self):
        current_size = (self.screen_manager.window_width, self.screen_manager.window_height)
        if current_size != self.last_window_size:
            self.last_window_size = current_size
            self.layout_initialized = False
            self.fonts = self._create_fonts()
            return True
        return False

    def _create_layout(self):
        print("[POKEDEX_SCENE] Criando layout...")
        vx = self.screen_manager.viewport_x
        vy = self.screen_manager.viewport_y
        vw = self.screen_manager.viewport_width
        vh = self.screen_manager.viewport_height

        padding = SIZES['padding']
        header_height = SIZES['header_height']
        filter_height = SIZES['filter_height']
        gap = SIZES['gap']

        # ===== HEADER =====
        header_y = vy + padding

        # Botão voltar
        back_size = 40
        self.back_button = pygame.Rect(vx + padding, header_y, back_size, back_size)

        # ===== SEARCH BAR =====
        search_y = header_y + back_size + gap
        search_width = min(350, vw * 0.28)
        search_height = 34
        search_x = vx + padding
        self.search_bar = SearchBar(search_x, search_y, search_width, search_height)
        print(f"[POKEDEX_SCENE] Search bar: {search_x}, {search_y}, {search_width}x{search_height}")

        # ===== FILTERS =====
        filter_y = search_y + search_height + gap
        filter_spacing = 12
        filter_width = 150
        filter_height = 30
        filter_start_x = vx + padding

        self.filter_buttons = []
        filter_keys = [
            (FILTERS['ALL'], "TODOS"),
            (FILTERS['CAUGHT'], "CAPTURADOS"),
            (FILTERS['SEEN'], "VISTOS"),
            (FILTERS['NOT_CAUGHT'], "NÃO CAPTURADOS"),
            (FILTERS['UNSEEN'], "NÃO VISTOS")
        ]

        for i, (filter_key, filter_name) in enumerate(filter_keys):
            btn_x = filter_start_x + i * (filter_width + filter_spacing)
            btn_rect = pygame.Rect(btn_x, filter_y, filter_width, filter_height)
            self.filter_buttons.append({
                'key': filter_key,
                'name': filter_name,
                'rect': btn_rect,
                'active': filter_key == self.filter_type,
                'hover': False
            })
            print(f"[POKEDEX_SCENE] Filtro {filter_name}: {btn_rect}")

        # ===== LISTA E DETALHE =====
        list_y = filter_y + filter_height + gap
        bottom_margin = 50
        list_height = vh - (list_y - vy) - bottom_margin - padding

        list_width = int(vw * 0.32)
        list_x = vx + padding

        detail_width = vw - list_width - padding * 3
        detail_x = list_x + list_width + padding

        print(f"[POKEDEX_SCENE] Lista: {list_x}, {list_y}, {list_width}x{list_height}")
        print(f"[POKEDEX_SCENE] Detalhe: {detail_x}, {list_y}, {detail_width}x{list_height}")

        self.pokedex_list = PokedexList(list_x, list_y, list_width, list_height)
        self.pokedex_list.on_item_click = self._on_list_item_click

        self.pokemon_detail = PokemonDetail(detail_x, list_y, detail_width, list_height)

        self._update_pokedex_list()
        self._update_counts()

        self.layout_initialized = True
        print("[POKEDEX_SCENE] Layout criado com sucesso!")

    def _on_list_item_click(self, pokemon_id):
        """Callback quando um item da lista é clicado"""
        print(f"[POKEDEX_SCENE] === CALLBACK RECEBIDO: {pokemon_id} ===")
        self.current_selected_id = pokemon_id
        self._update_detail(pokemon_id)
        print(f"[POKEDEX_SCENE] Callback finalizado")

    def _update_counts(self):
        self.total_seen = len(self.player.seen_pokemon)
        self.total_caught = len(self.player.caught_pokemon)
        self.total_pokemon = len(self.pokedex.pokemon_data)

    def _update_pokedex_list(self):
        if self.pokedex_list:
            search_text = self.search_bar.get_search_text() if self.search_bar else ""
            self.pokedex_list.update_items(
                self.pokedex.pokemon_data,
                self.player,
                search_text,
                self.filter_type
            )

            selected_item = self.pokedex_list.get_selected_item()
            if selected_item:
                pokemon_id = selected_item.pokemon_id
                self.current_selected_id = pokemon_id
                self._update_detail(pokemon_id)

    def _update_detail(self, pokemon_id):
        """Atualiza o painel de detalhes com o Pokémon selecionado"""
        print(f"[POKEDEX_SCENE] _update_detail: {pokemon_id}")
        if not self.pokemon_detail:
            print(f"[POKEDEX_SCENE] pokemon_detail é None!")
            return

        is_caught = pokemon_id in self.player.caught_pokemon
        is_seen = pokemon_id in self.player.seen_pokemon
        print(f"[POKEDEX_SCENE] is_caught: {is_caught}, is_seen: {is_seen}")

        pokemon_data = self.pokedex.get_pokemon(pokemon_id)
        self.pokemon_detail.set_pokemon(pokemon_id, pokemon_data, is_caught, is_seen)

        if self.pokedex_list:
            self.pokedex_list.selected_id = pokemon_id
            print(f"[POKEDEX_SCENE] selected_id atualizado para {pokemon_id}")

    def handle_event(self, event):
        if self._check_resize():
            self._create_layout()

        if event.type == pygame.KEYDOWN:
            if event.key == pygame.K_ESCAPE:
                self._go_back()
                return
            elif event.key == pygame.K_p:
                self.toggle_pause()

        if event.type == pygame.VIDEORESIZE:
            self.layout_initialized = False
            return

        # ===== BARRA DE PESQUISA =====
        if self.search_bar:
            result = self.search_bar.handle_event(event)
            if result is not None:
                print(f"[POKEDEX_SCENE] Busca atualizada: '{self.search_bar.text}'")
                self._update_pokedex_list()

        # ===== FILTROS =====
        if event.type == pygame.MOUSEMOTION:
            for btn in self.filter_buttons:
                btn['hover'] = btn['rect'].collidepoint(event.pos)

            if self.back_button:
                self.back_hover = self.back_button.collidepoint(event.pos)

        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            mouse_pos = event.pos
            print(f"[POKEDEX_SCENE] Clique em: {mouse_pos}")

            # Verifica filtros
            for btn in self.filter_buttons:
                if btn['rect'].collidepoint(mouse_pos):
                    print(f"[POKEDEX_SCENE] Clique no filtro: {btn['name']}")
                    self.filter_type = btn['key']
                    for b in self.filter_buttons:
                        b['active'] = (b['key'] == self.filter_type)
                    self._update_pokedex_list()
                    return

            # Verifica botão voltar
            if self.back_button and self.back_button.collidepoint(mouse_pos):
                print(f"[POKEDEX_SCENE] Clique no botão voltar")
                self._go_back()
                return

        # ===== LISTA =====
        if self.pokedex_list:
            result = self.pokedex_list.handle_event(event)
            if result and isinstance(result, int):
                print(f"[POKEDEX_SCENE] RESULTADO DA LISTA: {result}")
                self.current_selected_id = result
                self._update_detail(result)

        # ===== DETALHE =====
        if self.pokemon_detail:
            result = self.pokemon_detail.handle_event(event, self.pokedex)
            if result:
                if result.get('action') == 'navigate':
                    new_id = result['pokemon_id']
                    print(f"[POKEDEX_SCENE] Navegação para: {new_id}")
                    self.current_selected_id = new_id
                    self._update_detail(new_id)
                    if self.pokedex_list:
                        self.pokedex_list.update(
                            self.screen_manager.get_delta_time()
                        )

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

    def render(self, screen):
        self._draw_gradient_background(screen)

        if not self.layout_initialized:
            self._create_layout()

        vx = self.screen_manager.viewport_x
        vy = self.screen_manager.viewport_y
        vw = self.screen_manager.viewport_width

        # ===== HEADER =====
        self._render_back_button(screen)

        # Título
        title = self.fonts['title'].render("POKEDEX", True, COLORS['text_accent'])
        title_x = vx + (vw - title.get_width()) // 2
        title_y = vy + SIZES['padding'] + 5
        screen.blit(title, (title_x, title_y))

        # Linha decorativa
        line_y = title_y + title.get_height() + 6
        line_width = 120
        line_x = vx + (vw - line_width) // 2
        pygame.draw.line(screen, COLORS['border_gold'], (line_x, line_y), (line_x + line_width, line_y), 2)

        # Estatísticas
        stats_text = f"Total: {self.total_pokemon}  |  Vistos: {self.total_seen}  |  Capturados: {self.total_caught}"
        stats_font = pygame.font.Font(None, 24)
        stats_surf = stats_font.render(stats_text, True, COLORS['text_secondary'])
        stats_x = vx + vw - SIZES['padding'] - stats_surf.get_width()
        stats_y = vy + SIZES['padding'] + 8
        screen.blit(stats_surf, (stats_x, stats_y))

        # ===== SEARCH =====
        if self.search_bar:
            self.search_bar.render(screen, self.fonts['medium'])

        # ===== FILTERS =====
        self._render_filters(screen)

        # ===== LISTA =====
        if self.pokedex_list:
            self.pokedex_list.render(
                screen, self.pokedex,
                self.fonts['medium'],
                self.fonts['small']
            )

        # ===== DETALHE =====
        if self.pokemon_detail:
            self.pokemon_detail.render(screen, self.pokedex, self.fonts)

        # ===== CONTADOR DA LISTA =====
        if self.pokedex_list:
            count = self.pokedex_list.get_count()
            count_text = f"Mostrando {count} de {self.total_pokemon} Pokemon"
            count_surf = self.fonts['tiny'].render(count_text, True, COLORS['text_secondary'])
            count_x = vx + SIZES['padding']
            count_y = self.pokedex_list.rect.bottom + 5
            screen.blit(count_surf, (count_x, count_y))

        # ===== INSTRUÇÕES =====
        self._render_instructions(screen)

        if self.paused:
            self._render_pause_overlay(screen)

    def _render_back_button(self, screen):
        if not self.back_button:
            return

        bg_color = (50, 50, 55) if not self.back_hover else (70, 70, 80)
        border_color = (90, 90, 100) if not self.back_hover else COLORS['text_accent']

        pygame.draw.rect(screen, bg_color, self.back_button, border_radius=6)
        pygame.draw.rect(screen, border_color, self.back_button, 2, border_radius=6)

        back_text = pygame.font.Font(None, 32).render("<", True, COLORS['text_primary'])
        text_rect = back_text.get_rect(center=self.back_button.center)
        screen.blit(back_text, text_rect)

    def _render_filters(self, screen):
        for btn in self.filter_buttons:
            if btn['active']:
                bg_color = COLORS['bg_list_item_selected']
                border_color = COLORS['text_accent']
                text_color = COLORS['text_primary']
            elif btn['hover']:
                bg_color = COLORS['bg_list_item_hover']
                border_color = COLORS['border_light']
                text_color = COLORS['text_primary']
            else:
                bg_color = COLORS['bg_list_item']
                border_color = COLORS['border']
                text_color = COLORS['text_secondary']

            pygame.draw.rect(screen, bg_color, btn['rect'], border_radius=4)
            pygame.draw.rect(screen, border_color, btn['rect'], 2, border_radius=4)

            text = self.fonts['small'].render(btn['name'], True, text_color)
            text_rect = text.get_rect(center=btn['rect'].center)
            screen.blit(text, text_rect)

    def _render_instructions(self, screen):
        inst_font = pygame.font.Font(None, 13)
        inst_text = "ESC voltar  |  P pausar  |  Clique no Pokemon para ver detalhes"
        inst_surf = inst_font.render(inst_text, True, COLORS['text_secondary'])

        vx = self.screen_manager.viewport_x
        vy = self.screen_manager.viewport_y
        vw = self.screen_manager.viewport_width
        vh = self.screen_manager.viewport_height

        inst_x = vx + (vw - inst_surf.get_width()) // 2
        inst_y = vy + vh - 20
        screen.blit(inst_surf, (inst_x, inst_y))

    def _draw_gradient_background(self, screen):
        if (not hasattr(self, '_bg_cache') or
                self._bg_cache.get_width() != self.screen_manager.window_width or
                self._bg_cache.get_height() != self.screen_manager.window_height):

            self._bg_cache = pygame.Surface(
                (self.screen_manager.window_width, self.screen_manager.window_height)
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
            (self.screen_manager.window_width, self.screen_manager.window_height)
        )
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