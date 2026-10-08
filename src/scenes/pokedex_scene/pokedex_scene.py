# src/scenes/pokedex_scene/pokedex_scene.py
"""
Pokédex — Scene orquestradora.

Todo o layout está em `res/ui_layouts/pokedex.json`.
Toda a lógica de dados está em `PokedexLogic`.
Aqui só: ligar widgets <-> dados e reagir a eventos.
"""
import pygame

from src.ui.screen_template import StandardScreen
from src.ui.screen_loader import ScreenLoader
from src.ui.theme import FontBook

from src.scenes.pokedex_scene.pokedex_logic import PokedexLogic
from src.ui.utils.type_bar_loader import type_bar_loader
from src.ui.utils.type_icon_loader import type_icon_loader

LAYOUT_PATH = "res/ui_layouts/pokedex.json"


class PokedexScene(StandardScreen):
    title = ""
    show_back_button = False

    def __init__(self, game):
        self.logic = PokedexLogic(game)
        self.search_active = False
        self.search_cursor_t = 0.0
        super().__init__(game)

    # =================================================================
    def build(self):
        ScreenLoader.load(self, LAYOUT_PATH)
        self._populate_static()

    def get_actions(self):
        return {
            "back":             self._on_back,
            "region_changed":   self._on_region_changed,
            "status_changed":   self._on_status_changed,
            "pokemon_selected": self._on_pokemon_selected,
            "prev_pokemon":     self._on_prev,
            "next_pokemon":     self._on_next,
            "toggle_view":      self._on_toggle_view,
        }

    # =================================================================
    # População inicial
    # =================================================================
    def _populate_static(self):
        dd = self.get("dd_region")
        if dd is not None:
            dd.options = self.logic.get_region_labels()
            dd.value   = self.logic.get_region_label()

        dd = self.get("dd_status")
        if dd is not None:
            dd.options = self.logic.get_status_labels()
            dd.value   = self.logic.get_status_label()

        grid = self.get("stats_grid")
        if grid is not None:
            grid.items = [0, 1, 2, 3, 4, 5]
            grid.render_callback = self._render_stat_cell

        self._refresh_search_label()
        self._update_stats()
        self._feed_grid()
        self._update_detail()

    # =================================================================
    # Feed da grid de Pokémon
    # =================================================================
    def _feed_grid(self):
        grid = self.get("pokemon_grid")
        if grid is None:
            return

        items = []
        for e in self.logic.filtered:
            d = self.logic.item_dict(e)
            # Tipo 1 (sempre existe — cai em undefined)
            d["type_icon"] = type_icon_loader.get_original(d["type_key"])
            # Tipo 2 (None para monotype)
            tk2 = d.get("type_key_2")
            d["type_icon_2"] = type_icon_loader.get_original(tk2) if tk2 else None
            items.append(d)

        grid.items = items

    # =================================================================
    # Stats gerais
    # =================================================================
    def _update_stats(self):
        lbl = self.get("lbl_stat_total")
        if lbl is not None:
            lbl.text = f"Total: {self.logic.total_pokemon}"
        lbl = self.get("lbl_stat_seen")
        if lbl is not None:
            lbl.text = f"Vistos: {self.logic.total_seen}"
        lbl = self.get("lbl_stat_caught")
        if lbl is not None:
            lbl.text = f"Capturados: {self.logic.total_caught}"

    # =================================================================
    # Painel de detalhe
    # =================================================================
    def _update_detail(self):
        state = self.logic.get_detail_state()

        # sprite
        img = self.get("detail_sprite")
        if img is not None:
            img.surface = state["sprite"]

        # info do sprite (inmap)
        lbl = self.get("lbl_sprite_info")
        if lbl is not None:
            lbl.text = state["sprite_info"]

        # botão toggle
        btn = self.get("btn_toggle")
        if btn is not None:
            btn.label = "SPRITE" if state["show_inmap"] else "INMAP"

        # nome
        lbl = self.get("detail_name")
        if lbl is not None:
            lbl.text = state["name"]

        # status
        badge = self.get("detail_status")
        if badge is not None:
            badge.text = state["status_text"]
            badge.bg_color = state["status_color"]

        # ===== TYPES — barras carregadas do type_bar_loader =====
        b1 = self.get("detail_type_1")
        b2 = self.get("detail_type_2")
        types = state["types"]

        show_1 = len(types) >= 1
        show_2 = len(types) >= 2

        if b1 is not None:
            b1.visible = show_1
            if show_1:
                b1.surface = type_bar_loader.get_original(types[0]["key"])
        if b2 is not None:
            b2.visible = show_2
            if show_2:
                b2.surface = type_bar_loader.get_original(types[1]["key"])

        self._center_type_bars(b1, b2, show_1, show_2)

        # stats (só capturados)
        lbl = self.get("lbl_stats_header")
        if lbl is not None:
            lbl.visible = state["caught"]

        grid = self.get("stats_grid")
        if grid is not None:
            grid.visible = state["caught"]

        # contador
        lbl = self.get("lbl_nav_counter")
        if lbl is not None:
            lbl.text = state["counter"]

        # widgets da animação InMap
        self._update_inmap_widgets(state)

    def _update_inmap_widgets(self, state):
        show = state.get("show_inmap", False)

        lbl = self.get("lbl_inmap_dir")
        if lbl is not None:
            lbl.visible = show
            lbl.text = state.get("direction_label", "") if show else ""

        lbl = self.get("lbl_inmap_frame")
        if lbl is not None:
            lbl.visible = show
            lbl.text = state.get("frame_label", "") if show else ""

        prog = self.get("inmap_progress")
        if prog is not None:
            prog.visible = show
            if show:
                prog.value = state.get("direction_progress", 0.0)

    def _center_type_bars(self, b1, b2, show_1, show_2):
        """
        Reposiciona slots + imagens centralizados no detail_panel.

        - 1 tipo:  [X]         (centralizado)
        - 2 tipos: [X][Y]      (par colado, centralizado)
        - 0 tipos: nada visível
        """
        parent = self.get("detail_panel")
        s1 = self.get("type_slot_1")
        s2 = self.get("type_slot_2")

        if parent is None or b1 is None or b2 is None:
            return

        cx = parent.rect.centerx
        w = b1.rect.width
        gap = 6
        y = b1.rect.y  # vem do JSON

        if show_1 and show_2:
            total = w + gap + w
            x1 = cx - total // 2
            x2 = x1 + w + gap

            if s1 is not None:
                s1.visible = True
                s1.rect.x, s1.rect.y = x1, y
            if s2 is not None:
                s2.visible = True
                s2.rect.x, s2.rect.y = x2, y

            b1.rect.x, b1.rect.y = x1, y
            b2.rect.x, b2.rect.y = x2, y

        elif show_1:
            x1 = cx - w // 2

            if s1 is not None:
                s1.visible = True
                s1.rect.x, s1.rect.y = x1, y
            if s2 is not None:
                s2.visible = False

            b1.rect.x, b1.rect.y = x1, y

        else:
            if s1 is not None:
                s1.visible = False
            if s2 is not None:
                s2.visible = False

    def _render_stat_cell(self, idx, item, screen, rect):
        """Renderiza uma linha de stat (nome + barra + valor)."""
        state = self.logic.get_detail_state()
        stats = state.get("stats", [])
        if idx >= len(stats):
            return True

        stat = stats[idx]
        label = stat["label"]
        value = stat["value"]
        vmax = max(1, stat["max"])
        pct = max(0.0, min(1.0, value / vmax))

        inner = rect.inflate(-2, -2)

        # nome
        f_name = FontBook.get(11, bold=True,
                              name="pokemon-firered-leafgreen-font-recreation")
        n_surf = f_name.render(label, True, (160, 165, 180))
        screen.blit(n_surf, (inner.x, inner.centery - n_surf.get_height() // 2))

        # barra
        bar_x = inner.x + 34
        bar_w = inner.width - 34 - 34
        bar_h = 10
        bar_y = inner.centery - bar_h // 2
        bar_rect = pygame.Rect(bar_x, bar_y, max(10, bar_w), bar_h)
        pygame.draw.rect(screen, (26, 32, 48), bar_rect, border_radius=3)

        if pct > 0:
            if pct > 0.7:
                col = (100, 200, 100)
            elif pct > 0.4:
                col = (248, 176, 48)
            else:
                col = (200, 80, 80)
            fill_w = max(3, int(bar_rect.width * pct))
            fill_rect = pygame.Rect(bar_rect.x, bar_rect.y, fill_w, bar_h)
            pygame.draw.rect(screen, col, fill_rect, border_radius=3)

        # valor
        f_val = FontBook.get(11, bold=True,
                             name="pokemon-firered-leafgreen-font-recreation")
        v_surf = f_val.render(str(int(value)), True, (240, 242, 248))
        screen.blit(v_surf, (inner.right - v_surf.get_width(),
                             inner.centery - v_surf.get_height() // 2))
        return True

    # =================================================================
    # Callbacks
    # =================================================================
    def _on_back(self, *_):
        from src.scenes.phase_selector.phase_select_scene import PhaseSelectScene
        self.game.phase_select_scene = PhaseSelectScene(self.game)
        self.game.current_scene = self.game.phase_select_scene

    def _on_region_changed(self, *_):
        dd = self.get("dd_region")
        if dd is None:
            return
        self.logic.set_region_label(dd.value)
        self._feed_grid()
        self._update_stats()
        self._update_detail()

    def _on_status_changed(self, *_):
        dd = self.get("dd_status")
        if dd is None:
            return
        self.logic.set_status_label(dd.value)
        self._feed_grid()
        self._update_detail()

    def _on_pokemon_selected(self, idx):
        if 0 <= idx < len(self.logic.filtered):
            self.logic.select(self.logic.filtered[idx]["id"])
            self._feed_grid()
            self._update_detail()

    def _on_prev(self, *_):
        self.logic.prev_pokemon()
        self._feed_grid()
        self._update_detail()

    def _on_next(self, *_):
        self.logic.next_pokemon()
        self._feed_grid()
        self._update_detail()

    def _on_toggle_view(self, *_):
        self.logic.toggle_view()
        self._update_detail()

    # =================================================================
    # Busca
    # =================================================================
    def _refresh_search_label(self):
        lbl = self.get("lbl_search_text")
        if lbl is None:
            return

        txt = self.logic.search_text
        if not txt and not self.search_active:
            lbl.text = "Buscar..."
            lbl.text_color = (90, 96, 112)
            return

        lbl.text_color = (240, 242, 248)

        if self.search_active and int(self.search_cursor_t * 2) % 2 == 0:
            lbl.text = (txt or "") + "|"
        else:
            lbl.text = txt or "|"

    # =================================================================
    # Eventos
    # =================================================================
    def handle_event(self, event):
        # ===== INPUT DE BUSCA =====
        if self.search_active and event.type == pygame.KEYDOWN:
            if event.key == pygame.K_ESCAPE:
                self.search_active = False
                self.logic.set_search("")
                self._refresh_search_label()
                self._feed_grid()
                self._update_detail()
                return True
            if event.key == pygame.K_RETURN:
                self.search_active = False
                self._refresh_search_label()
                return True
            if event.key == pygame.K_BACKSPACE:
                self.logic.set_search(self.logic.search_text[:-1])
                self._refresh_search_label()
                self._feed_grid()
                self._update_detail()
                return True
            if event.unicode and event.unicode.isprintable():
                self.logic.set_search(self.logic.search_text + event.unicode)
                self._refresh_search_label()
                self._feed_grid()
                self._update_detail()
                return True
            return True

        # ===== CLIQUE FORA DA BUSCA =====
        if (self.search_active
                and event.type == pygame.MOUSEBUTTONDOWN
                and event.button == 1):
            sp = self.get("search_panel")
            if sp is None or not sp.rect.collidepoint(event.pos):
                self.search_active = False
                self._refresh_search_label()

        # ===== CLIQUE NA BUSCA =====
        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            sp = self.get("search_panel")
            if sp is not None and sp.rect.collidepoint(event.pos):
                self.search_active = True
                self._refresh_search_label()
                return True

        # ===== ATALHOS =====
        if event.type == pygame.KEYDOWN:
            if event.key == pygame.K_ESCAPE:
                self._on_back()
                return
            if event.key == pygame.K_p:
                self.toggle_pause()
                return
            if event.key == pygame.K_f:
                self.search_active = True
                self._refresh_search_label()
                return True

        super().handle_event(event)

    # =================================================================
    # Update
    # =================================================================
    def fixed_update(self, dt):
        self.search_cursor_t += dt
        if self.search_active:
            self._refresh_search_label()

        self.logic.update_animation(dt)

        if self.logic.show_inmap:
            state = self.logic.get_detail_state()

            img = self.get("detail_sprite")
            if img is not None:
                img.surface = state["sprite"]

            lbl = self.get("lbl_inmap_dir")
            if lbl is not None:
                lbl.text = state.get("direction_label", "")

            lbl = self.get("lbl_inmap_frame")
            if lbl is not None:
                lbl.text = state.get("frame_label", "")

            prog = self.get("inmap_progress")
            if prog is not None:
                prog.value = state.get("direction_progress", 0.0)

        super().fixed_update(dt)

    def on_back(self):
        self._on_back()