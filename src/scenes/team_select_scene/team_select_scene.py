# src/scenes/team_select_scene/team_select_scene.py

import pygame

from src.scenes.base_scene import BaseScene
from src.scenes.game_scene.game_scene import GameScene
from src.scenes.team_select_scene.components.gradient_background import GradientBackground
from src.scenes.team_select_scene.components.pokemon_modal import PokemonModal
from src.scenes.team_select_scene.components.navigation_buttons import NavigationButtons
from src.scenes.team_select_scene.components.pokemon_grid_item import PokemonGridItem
from src.scenes.team_select_scene.managers.layout_manager import LayoutManager
from src.scenes.team_select_scene.managers.pokemon_manager import PokemonManager
from src.scenes.team_select_scene.handlers.event_handler import EventHandler
from src.scenes.team_select_scene.utils.constants import FONT_SIZES, LAYOUT
from src.data.pokedex import Pokedex
from src.managers.sounds.sound_manager import sound_manager, SoundEffect


class TeamSelectScene(BaseScene):
    def __init__(self, game, chapter, phase):
        super().__init__(game)

        self.pokedex = Pokedex()
        self.phase = phase
        self.chapter = chapter

        # ===== MANAGERS =====
        self.pokemon_manager = PokemonManager(game.player)
        self.layout_manager = LayoutManager(game)
        self.event_handler = EventHandler(game, self.pokemon_manager, self.layout_manager)

        # ===== COMPONENTS =====
        self.background = GradientBackground(game.screen_manager)
        self.navigation = None
        self.filters = None

        # ===== STATE =====
        self.current_page = 0
        self.total_pages = 1
        self.layout_initialized = False
        self._needs_refresh = True

        # Listas vazias (preenchidas em _initialize_layout)
        self.team_slots = []
        self.grid_items = []

        # Controle de resize
        self.last_window_size = (
            self.game.screen_manager.window_width,
            self.game.screen_manager.window_height,
        )

        # ===== FONTS =====
        self.title_font = pygame.font.Font(None, FONT_SIZES['TITLE'])
        self.slot_font = pygame.font.Font(None, FONT_SIZES['SLOT'])
        self.grid_font = pygame.font.Font(None, FONT_SIZES['GRID'])
        self.page_font = pygame.font.Font(None, FONT_SIZES['PAGE'])

        # ===== MÚSICA =====
        self._music_started = False
        self._start_team_select_music()

        # ===== DRAG & DROP =====
        self._setup_drag_drop()

    # =================================================================
    # MÚSICA
    # =================================================================
    def _start_team_select_music(self):
        if not self._music_started:
            success = sound_manager.play_team_select_music(loop=True)
            if success:
                self._music_started = True
                print("[TEAM_SELECT] Música iniciada: Come_Along")
            else:
                print("[TEAM_SELECT] Tentando música alternativa...")
                success = sound_manager.play_menu_music("Title_Theme", loop=True)
                if success:
                    self._music_started = True
                    print("[TEAM_SELECT] Música iniciada: Title_Theme (fallback)")

    # =================================================================
    # DRAG & DROP — SETUP + CALLBACKS
    # =================================================================
    def _setup_drag_drop(self):
        """Conecta os callbacks do drag_drop aos handlers da cena."""
        dd = self.event_handler.drag_drop
        dd.on_drop = self._on_drag_drop
        dd.on_cancel = self._on_drag_cancel

    def _on_drag_cancel(self):
        """Limpa estados visuais quando o drag é cancelado."""
        for s in self.team_slots:
            s.is_selected = False
            s.is_drag_hover = False
        for g in self.grid_items:
            g.is_being_dragged = False
            g.is_drag_hover = False

    def _on_drag_drop(self, op_type, data):
        """
        Executa a operação de mover Pokémon após o drop.

        op_type:
            'team_to_team' -> reordena dentro do time
            'team_to_box'  -> remove do time (vai pra box)
            'box_to_team'  -> adiciona ao time (substitui se slot ocupado)
            'box_to_box'   -> troca posições visuais na grid
            'release'      -> liberta o Pokémon
        """
        src_type = data['source_type']
        src_idx = data['source_index']
        tgt_type = data['target_type']
        tgt_idx = data['target_index']
        src_pokemon = data['source_pokemon']

        print(f"[DRAG] {op_type} | {src_type}[{src_idx}] -> {tgt_type}[{tgt_idx}]")

        # -------------------------------------------------------------
        # 1) Reordenar DENTRO DO TIME
        # -------------------------------------------------------------
        if op_type == 'team_to_team':
            team = self.game.player.team
            if 0 <= src_idx < len(team):
                if tgt_idx >= len(team):
                    tgt_idx = len(team) - 1
                if src_idx == tgt_idx:
                    self._on_drag_cancel()
                    return
                pokemon = team.pop(src_idx)
                team.insert(tgt_idx, pokemon)

                self.pokemon_manager.update_team_status()
                self._refresh_all_pokemon_status()
                self.layout_initialized = False

        # -------------------------------------------------------------
        # 2) TIME -> BOX
        # -------------------------------------------------------------
        elif op_type == 'team_to_box':
            if 0 <= src_idx < len(self.game.player.team):
                pokemon = self.game.player.team[src_idx]
                self.pokemon_manager.remove_from_team(pokemon)
                self._refresh_all_pokemon_status()
                self.layout_initialized = False

        # -------------------------------------------------------------
        # 3) BOX -> TIME
        # -------------------------------------------------------------
        elif op_type == 'box_to_team':
            if 0 <= src_idx < len(self.grid_items):
                item = self.grid_items[src_idx]
                pokemon_data = item.pokemon_data
                unique_id = pokemon_data.get("unique_id")
                pokemon = self.game.player.get_pokemon_instance(unique_id)
                if pokemon:
                    # Se o slot alvo já tem alguém, remove antes (troca)
                    if 0 <= tgt_idx < len(self.team_slots):
                        target_slot = self.team_slots[tgt_idx]
                        if target_slot.pokemon:
                            self.pokemon_manager.remove_from_team(target_slot.pokemon)

                    ok = self.pokemon_manager.add_to_team(pokemon)
                    if ok:
                        self._refresh_all_pokemon_status()
                        self.layout_initialized = False
                    else:
                        self._on_drag_cancel()

        # -------------------------------------------------------------
        # 4) Reordenar DENTRO DA BOX (swap visual na página atual)
        # -------------------------------------------------------------
        elif op_type == 'box_to_box':
            if (0 <= src_idx < len(self.grid_items) and
                    0 <= tgt_idx < len(self.grid_items)):
                a = self.grid_items[src_idx]
                b = self.grid_items[tgt_idx]
                # Troca os dados visuais dos dois cards
                a.pokemon_data, b.pokemon_data = b.pokemon_data, a.pokemon_data
                # Reseta timer de animação pra não dar "salto" visual
                a._icon_frame_timer = 0
                b._icon_frame_timer = 0

        # -------------------------------------------------------------
        # 5) RELEASE
        # -------------------------------------------------------------
        elif op_type == 'release':
            if src_pokemon:
                self.pokemon_manager.release_pokemon(src_pokemon)
                self._refresh_all_pokemon_status()
                self.layout_initialized = False

        # Garante que flags visuais sejam limpas
        self._on_drag_cancel()

    # =================================================================
    # RESIZE
    # =================================================================
    def _check_resize(self):
        current_size = (
            self.game.screen_manager.window_width,
            self.game.screen_manager.window_height,
        )
        if current_size != self.last_window_size:
            self.last_window_size = current_size
            self.layout_initialized = False
            return True
        return False

    # =================================================================
    # CICLO DE VIDA
    # =================================================================
    def on_enter(self):
        """Chamado quando a cena é ativada — força refresh dos dados."""
        self._needs_refresh = True

        if not self._music_started or not pygame.mixer.music.get_busy():
            self._start_team_select_music()

    def on_exit(self):
        """Chamado quando a cena é desativada — para a música."""
        sound_manager.stop_music(fade_ms=300)
        self._music_started = False

    # =================================================================
    # REFRESH DE DADOS
    # =================================================================
    def _refresh_all_data(self):
        """Força atualização completa dos dados do jogador."""
        print("[TEAM_SELECT] Forçando refresh de dados...")

        # 1) Atualiza cache e box
        self.pokemon_manager.refresh_all_pokemon_data()

        # 2) Atualiza slots do time (se já existirem)
        if hasattr(self, 'team_slots') and self.team_slots:
            for i, slot in enumerate(self.team_slots):
                if i < len(self.game.player.team):
                    slot.set_pokemon(self.game.player.team[i])
                else:
                    slot.set_pokemon(None)

        # 3) Marca para recriar layout
        self.layout_initialized = False

        # 4) Reseta página
        self.current_page = 0

        self._needs_refresh = False
        print("[TEAM_SELECT] Refresh de dados concluído!")

    def _refresh_all_pokemon_status(self):
        """Atualiza is_in_team em todos os Pokémon (time + box + cache)."""
        team_ids = {p.unique_id for p in self.game.player.team}

        for pokemon in self.game.player.team:
            pokemon.is_in_team = True

        for data in self.game.player.pc_box:
            unique_id = data.get("unique_id")
            if unique_id:
                data["is_in_team"] = unique_id in team_ids

        for unique_id, pokemon in self.game.player._pokemon_cache.items():
            if hasattr(pokemon, 'is_in_team'):
                pokemon.is_in_team = unique_id in team_ids

        self.layout_initialized = False

    # =================================================================
    # LAYOUT
    # =================================================================
    def _initialize_layout(self):
        """Inicializa o layout da cena (slots + filtros + grid + botões)."""
        if self._needs_refresh:
            self._refresh_all_data()
            self._needs_refresh = False

        # ★ 1) PRIMEIRO: calcular a geometria e atualizar items_per_page
        geo = self.layout_manager.refresh_items_per_page()

        # ★ 2) AGORA sim busca os Pokémon com o número correto por página
        available_pokemon = self.pokemon_manager.get_available_pokemon(
            self.current_page,
            self.layout_manager.items_per_page,
        )

        layout = self.layout_manager.create_layout(
            self.game.player.team,
            available_pokemon,
            self.current_page,
            self.pokemon_manager.current_sort,
            self.pokemon_manager.current_search,
        )

        self.team_slots = layout['team_slots']
        self.grid_items = layout['grid_items']
        self.filters = layout.get('filters')
        buttons = layout['buttons']

        self.navigation = NavigationButtons(
            buttons['back'],
            buttons['start'],
            buttons['prev'],
            buttons['next'],
        )

        self.total_pages = self.pokemon_manager.get_page_count(
            self.layout_manager.items_per_page
        )
        self.layout_initialized = True

    def _refresh_grid(self):
        """Atualiza apenas a grid (mantendo slots e filtros)."""
        if not self.layout_initialized:
            return

        if self._needs_refresh:
            self._refresh_all_data()
            self._needs_refresh = False

        geo = self.layout_manager.compute_geometry()

        # Mantém items_per_page alinhado com a geometria atual
        self.layout_manager.cols_per_page = geo['cols']
        self.layout_manager.rows_per_page = geo['rows']
        self.layout_manager.items_per_page = geo['cols'] * geo['rows']

        available_pokemon = self.pokemon_manager.get_available_pokemon(
            self.current_page,
            self.layout_manager.items_per_page,
        )

        self.layout_manager.grid_items = []
        for i, pokemon in enumerate(available_pokemon):
            row = i // geo['cols']
            col = i % geo['cols']
            x = geo['grid_x'] + col * (geo['card_w'] + geo['card_spacing'])
            y = geo['grid_y'] + row * (geo['card_h'] + geo['card_spacing'])
            item = PokemonGridItem(pokemon, x, y, geo['card_w'], geo['card_h'])
            self.layout_manager.grid_items.append(item)

        self.grid_items = self.layout_manager.grid_items
        self.total_pages = self.pokemon_manager.get_page_count(
            self.layout_manager.items_per_page
        )

    # =================================================================
    # MODAL
    # =================================================================
    def _handle_modal_action(self):
        modal = self.event_handler.modal
        if not modal:
            return

        if modal.pokemon.is_in_team:
            self.pokemon_manager.remove_from_team(modal.pokemon)
        else:
            self.pokemon_manager.add_to_team(modal.pokemon)

        for i, slot in enumerate(self.team_slots):
            if i < len(self.game.player.team):
                slot.set_pokemon(self.game.player.team[i])
            else:
                slot.set_pokemon(None)

        self._refresh_all_pokemon_status()
        self.layout_initialized = False

    # =================================================================
    # EVENTOS
    # =================================================================
    def handle_event(self, event):
        self._check_resize()

        if event.type == pygame.VIDEORESIZE:
            self.layout_initialized = False
            return

        if not self.layout_initialized:
            self._initialize_layout()

        result = self.event_handler.handle_event(
            event,
            self.team_slots,
            self.grid_items,
            self.filters,
            self.navigation.back_button if self.navigation else None,
            self.navigation.start_button if self.navigation else None,
            self.navigation.prev_page_button if self.navigation else None,
            self.navigation.next_page_button if self.navigation else None,
            self.current_page,
            self.total_pages,
        )

        if result:
            self._handle_action(result)

    def _handle_action(self, action):
        action_type = action.get('type')

        # -------------------------------------------------------------
        # FILTROS / BUSCA / ORDENAÇÃO
        # -------------------------------------------------------------
        if action_type == 'SORT_CHANGED':
            sort_type = action['sort']
            self.pokemon_manager.set_sort(sort_type)
            if self.filters:
                self.filters.update_sort_state(sort_type)
            self.current_page = 0
            self._refresh_grid()

        elif action_type == 'FILTER_CHANGED':
            filter_type = action['filter']
            self.pokemon_manager.set_filter(filter_type)
            if self.filters:
                self.filters.update_filter_state(filter_type)
            self.current_page = 0
            self._refresh_grid()

        elif action_type == 'SEARCH_CHANGED':
            search_text = action['search']
            self.pokemon_manager.set_search(search_text)
            if self.filters:
                self.filters.update_search_state(search_text)
            self.current_page = 0
            self._refresh_grid()

        # -------------------------------------------------------------
        # NAVEGAÇÃO
        # -------------------------------------------------------------
        elif action_type == 'GO_BACK':
            sound_manager.play_effect(SoundEffect.CLICK)
            sound_manager.stop_music(fade_ms=300)
            from src.scenes.phase_selector.phase_select_scene import PhaseSelectScene
            self.game.phase_select_scene = PhaseSelectScene(self.game)
            self.game.current_scene = self.game.phase_select_scene

        elif action_type == 'START_GAME':
            sound_manager.play_effect(SoundEffect.CLICK)
            sound_manager.stop_music(fade_ms=300)
            self.game.game_scene = GameScene(self.game, self.chapter, self.phase)
            self.game.current_scene = self.game.game_scene

        elif action_type == 'PREV_PAGE':
            self.current_page -= 1
            self.layout_initialized = False

        elif action_type == 'NEXT_PAGE':
            self.current_page += 1
            self.layout_initialized = False

        # -------------------------------------------------------------
        # CLIQUE EM SLOT / GRID -> ABRE MODAL
        # -------------------------------------------------------------
        elif action_type == 'SLOT_CLICK':
            slot = action['slot']
            for s in self.team_slots:
                s.is_selected = (s.slot_index == action['slot_index'])
            if slot.pokemon:
                modal = PokemonModal(self.game, slot.pokemon.unique_id)
                self.event_handler.set_modal(modal)

        elif action_type == 'GRID_CLICK':
            pokemon_data = action['pokemon']
            unique_id = pokemon_data["unique_id"]
            modal = PokemonModal(self.game, unique_id)
            self.event_handler.set_modal(modal)

        # -------------------------------------------------------------
        # MODAL
        # -------------------------------------------------------------
        elif action_type == 'MODAL_ACTION':
            self._handle_modal_action()

        elif action_type == 'CLOSE_MODAL':
            self.event_handler.set_modal(None)

        elif action_type == 'RELEASE_POKEMON':
            modal = self.event_handler.modal
            if modal and modal.pokemon:
                self.pokemon_manager.release_pokemon(modal.pokemon)
                self.event_handler.set_modal(None)
                self.layout_initialized = False

        elif action_type == 'RESIZE':
            self.layout_initialized = False

    # =================================================================
    # UPDATE
    # =================================================================
    def fixed_update(self, dt):
        self._check_resize()
        if not self.layout_initialized:
            self._initialize_layout()

    # =================================================================
    # RENDER
    # =================================================================
    def render(self, screen):
        self._check_resize()
        self.background.render(screen)

        if not self.layout_initialized:
            return

        # -------------------------------------------------------------
        # TÍTULO
        # -------------------------------------------------------------
        title = self.title_font.render("SELECIONAR TIME", True, (220, 220, 230))
        title_x = (self.game.screen_manager.window_width - title.get_width()) // 2
        screen.blit(title, (title_x, 20))

        # Linha separadora
        pygame.draw.line(
            screen, (60, 60, 70),
            (50, 70),
            (self.game.screen_manager.window_width - 50, 70),
            2,
        )

        # -------------------------------------------------------------
        # SLOTS DO TIME
        # -------------------------------------------------------------
        for slot in self.team_slots:
            slot.render(screen, self.slot_font, self.pokedex)

        # -------------------------------------------------------------
        # FILTROS (botões, sem opções abertas)
        # -------------------------------------------------------------
        if self.filters:
            self.filters.render(screen, self.slot_font)

        # -------------------------------------------------------------
        # GRID ITEMS
        # -------------------------------------------------------------
        for item in self.grid_items:
            item.render(screen, self.grid_font, self.pokedex)

        # -------------------------------------------------------------
        # OPÇÕES DOS DROPDOWNS (por cima do grid)
        # -------------------------------------------------------------
        if self.filters:
            self.filters.render_dropdowns(screen, self.slot_font)

        # -------------------------------------------------------------
        # PAGINAÇÃO
        # -------------------------------------------------------------
        if self.total_pages > 1:
            page_text = self.page_font.render(
                f"Página {self.current_page + 1} de {self.total_pages}",
                True, (150, 150, 160),
            )
            page_rect = page_text.get_rect(
                center=(
                    self.game.screen_manager.window_width // 2,
                    self.navigation.prev_page_button.centery,
                )
            )
            screen.blit(page_text, page_rect)

        # -------------------------------------------------------------
        # BOTÕES DE NAVEGAÇÃO
        # -------------------------------------------------------------
        if self.navigation:
            self.navigation.render(
                screen, self.slot_font,
                len(self.game.player.team),
                self.current_page, self.total_pages,
            )

        # -------------------------------------------------------------
        # INFO DE FILTROS ATIVOS
        # -------------------------------------------------------------
        if self.filters:
            total_filtered = self.pokemon_manager.get_total_filtered_count()
            total_pc = len(self.game.player.pc_box)
            filter_active = (
                self.pokemon_manager.current_search or
                self.pokemon_manager.current_filter != "all" or
                self.pokemon_manager.current_sort != "capture"
            )

            if filter_active:
                if total_filtered > 0:
                    filter_info = f"Mostrando {total_filtered} de {total_pc} Pokemon"
                else:
                    filter_info = "Nenhum Pokemon encontrado"

                info_font = pygame.font.Font(None, 14)
                info_text = info_font.render(filter_info, True, (150, 150, 160))
                info_y = self.filters.rect.bottom + 8
                screen.blit(info_text, (30, info_y))

                if total_filtered == 0:
                    empty_font = pygame.font.Font(None, 24)
                    empty_text = empty_font.render(
                        "Nenhum Pokemon encontrado com esses filtros",
                        True, (150, 150, 160),
                    )
                    empty_x = (self.game.screen_manager.window_width
                               - empty_text.get_width()) // 2
                    empty_y = self.filters.rect.bottom + 50
                    screen.blit(empty_text, (empty_x, empty_y))

        # -------------------------------------------------------------
        # STATUS DO TIME
        # -------------------------------------------------------------
        team_status = f"Time: {len(self.game.player.team)}/6"
        status_color = (
            (255, 255, 255) if len(self.game.player.team) > 0
            else (150, 150, 150)
        )
        status_text = self.slot_font.render(team_status, True, status_color)
        screen.blit(
            status_text,
            (20, self.game.screen_manager.window_height - 30),
        )

        # DRAG GHOST (por cima do grid, abaixo do modal)
        modal_aberto = (
            self.event_handler.modal and
            self.event_handler.modal.visible
        )
        if not modal_aberto:
            self.event_handler.drag_drop.render_drag_ghost(screen, self.pokedex)

        if modal_aberto:
            self.event_handler.modal.render(screen)