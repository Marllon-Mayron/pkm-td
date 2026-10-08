# src/scenes/achievement_scene/achievement_scene.py
"""
Tela de conquistas — a Scene só orquestra.

TODO o visual dos cards está no JSON (`card_layout` do widget `card_grid`).
Aqui só:
  - transformar Achievement -> dict com campos de binding
  - reagir a mudanças de filtro / busca
  - reagir ao clique num card (seleção)
"""
import pygame

from src.ui.screen_template import StandardScreen
from src.ui.screen_loader import ScreenLoader
from src.ui.theme import FontBook

from src.data.item_bag_catalog import item_bag_catalog
from src.data.pokedex import Pokedex
from .achievement_logic import AchievementLogic


LAYOUT_PATH = "res/ui_layouts/achievement_sidebar.json"


def _hex(c):
    if c is None:
        return "#000000"
    return f"#{c[0]:02X}{c[1]:02X}{c[2]:02X}"


class AchievementScene(StandardScreen):
    title = ""
    show_back_button = False

    def __init__(self, game):
        self.player = game.player
        self.logic = AchievementLogic(game)
        self.pokedex = Pokedex()
        self.item_catalog = item_bag_catalog

        self.search_active = False
        self.search_cursor_t = 0.0

        super().__init__(game)

    # =================================================================
    def build(self):
        ScreenLoader.load(self, LAYOUT_PATH)
        self._populate_static()

    def get_actions(self):
        return {
            "back":           self._on_back,
            "rarity_changed": self._on_rarity_changed,
            "region_changed": self._on_region_changed,
            "card_clicked":   self._on_card_clicked,
        }

    # =================================================================
    # População
    # =================================================================
    def _populate_static(self):
        self._update_stats()

        dd_r = self.get("dd_rarity")
        if dd_r is not None:
            dd_r.options = self.logic.get_rarity_labels()
            dd_r.value   = dd_r.options[self.logic.rarity_index]

        dd_reg = self.get("dd_region")
        if dd_reg is not None:
            dd_reg.options = self.logic.get_region_labels()
            dd_reg.value   = dd_reg.options[self.logic.region_index]

        self._refresh_search_label()
        self._feed_grid()
        self._populate_detail()

    # =================================================================
    # Adapter: Achievement -> dict de bindings
    # =================================================================
    def _item_dict(self, ach):
        sel = self.logic.selected
        is_sel = (sel is not None and sel.id == ach.id and
                  getattr(sel, "region_id", 1) ==
                  getattr(ach, "region_id", 1))

        rarity = self.logic.RARITY_COLORS.get(ach.rarity, (150, 150, 150))
        dark   = tuple(max(15, c // 5) for c in rarity)

        prog = (0, 0)
        if not ach.unlocked:
            try:
                prog = self.player.achievement_manager.get_progress(ach.id)
            except Exception:
                prog = (0, 0)

        return {
            "id":                 ach.id,
            "title":              ach.title,
            "description":        ach.description,
            "rarity_name":        self.logic.RARITY_NAMES.get(ach.rarity, ""),
            "rarity_color":       _hex(rarity),
            "rarity_color_dark":  _hex(dark),
            "card_surface":       self.logic.get_card_surface(ach),
            "unlocked":           bool(ach.unlocked),
            "locked":             not bool(ach.unlocked),
            "is_selected":        is_sel,
            "progress":           prog[0],
            "progress_max":       prog[1],
        }

    def _feed_grid(self):
        # CORRIGIDO: o ID real no JSON é "cards_list" (o antigo "cards_grid"
        # nunca existiu no layout, então o get() sempre retornava None e a
        # lista nunca populava).
        grid = self.get("cards_list")
        if grid is None:
            return
        grid.items = [self._item_dict(a) for a in self.logic.filtered]

    def _update_stats(self):
        lbl = self.get("lbl_stats")
        if lbl is None:
            return
        unlocked = self.player.achievement_manager.get_unlocked_count()
        total    = self.player.achievement_manager.get_total_count()
        lbl.text = f"{unlocked} / {total}"

    # =================================================================
    # Clique / detalhe
    # =================================================================
    def _on_card_clicked(self, idx):
        if 0 <= idx < len(self.logic.filtered):
            self.logic.select(self.logic.filtered[idx])
            self._feed_grid()          # re-resolve is_selected
            self._populate_detail()

    def _populate_detail(self):
        ach = self.logic.selected

        img = self.get("detail_card_image")
        if img is not None:
            img.surface = self.logic.get_card_surface(ach) if ach else None

        t = self.get("lbl_detail_title")
        if t is not None:
            t.text = ach.title if ach else "Selecione uma conquista"

        b = self.get("lbl_detail_rarity")
        if b is not None:
            if ach is not None:
                b.visible  = True
                b.text     = self.logic.RARITY_NAMES.get(ach.rarity, "")
                b.bg_color = self.logic.RARITY_COLORS.get(
                    ach.rarity, (150, 150, 150))
            else:
                b.visible = False

        d = self.get("lbl_detail_desc")
        if d is not None:
            if ach is not None:
                txt = str(ach.description or "").strip()
                d.text = f"\u201C{txt}\u201D" if txt else ""
            else:
                d.text = "Selecione uma conquista ao lado para ver os detalhes."

        pr = self.get("detail_progress")
        if pr is not None:
            if ach is not None and not ach.unlocked:
                prog = self.player.achievement_manager.get_progress(ach.id)
                if prog[1] > 1:
                    pr.visible   = True
                    pr.max_value = prog[1]
                    pr.min_value = 0
                    pr.value     = min(prog[0], prog[1])
                else:
                    pr.visible = False
            else:
                pr.visible = False

        grid = self.get("grid_rewards")
        rt = self.get("lbl_rewards_title")
        if grid is not None:
            rewards = self.logic.get_reward_list(ach) if ach else []
            n = len(rewards)
            if n == 0:
                grid.items = []
                grid.visible = False
                if rt: rt.visible = False
            else:
                grid.items = list(range(n))
                grid.cols  = min(4, n)
                grid.rows  = max(1, (n + 3) // 4)
                grid.render_callback = self._render_reward_cell
                grid.visible = True
                if rt: rt.visible = True

        meta = self.get("lbl_detail_meta")
        if meta is not None:
            meta.text = self.logic.build_meta_text(ach) if ach else ""

    # =================================================================
    # Recompensas (ainda é callback — ver observação no fim)
    # =================================================================
    def _render_reward_cell(self, idx, item, screen, rect):
        ach = self.logic.selected
        if ach is None:
            return True
        rewards = self.logic.get_reward_list(ach)
        if idx >= len(rewards):
            return True
        kind, value = rewards[idx]
        inner = rect.inflate(-4, -4)

        # CORRIGIDO: cores alinhadas com a paleta nova
        # (verde-claro de fundo + borda dourada fina sobre painel bege).
        pygame.draw.rect(screen, (221, 232, 192), inner, border_radius=6)   # #DDE8C0
        pygame.draw.rect(screen, (138, 106, 42), inner, 1, border_radius=6)  # #8A6A2A

        f_big = FontBook.get(14, bold=True,
                             name="pokemon-firered-leafgreen-font-recreation")
        f_small = FontBook.get(10, bold=True,
                               name="pokemon-firered-leafgreen-font-recreation")

        if kind == "gold":
            t = f_big.render(f"$ {value}", True, (122, 90, 26))   # #7A5A1A
            screen.blit(t, t.get_rect(center=inner.center))
        elif kind == "xp":
            t = f_big.render(f"XP +{value}", True, (58, 106, 26))  # #3A6A1A
            screen.blit(t, t.get_rect(center=inner.center))
        elif kind == "item":
            iid, qty = value
            sprite = self.item_catalog.get_sprite(iid, scaled=True)
            if sprite:
                sz = max(14, min(inner.width, inner.height) - 20)
                sc = pygame.transform.scale(sprite, (sz, sz))
                screen.blit(sc, sc.get_rect(
                    center=(inner.centerx, inner.centery - 6)))
            t = f_small.render(f"x{qty}", True, (58, 34, 16))      # #3A2210
            screen.blit(t, t.get_rect(
                center=(inner.centerx, inner.bottom - 8)))
        elif kind == "pokemon":
            portrait = self.pokedex.get_portrait(value, "normal", shiny=False)
            if portrait:
                sz = max(14, min(inner.width, inner.height) - 20)
                sc = pygame.transform.scale(portrait, (sz, sz))
                screen.blit(sc, sc.get_rect(
                    center=(inner.centerx, inner.centery - 6)))
            nm = self.pokedex.get_name(value)
            t = f_small.render(nm, True, (58, 34, 16))             # #3A2210
            screen.blit(t, t.get_rect(
                center=(inner.centerx, inner.bottom - 8)))
        return True

    # =================================================================
    # Filtros / busca
    # =================================================================
    def _on_rarity_changed(self, *a, **k):
        dd = self.get("dd_rarity")
        if dd is None: return
        try:
            idx = self.logic.get_rarity_labels().index(dd.value)
        except ValueError:
            idx = 0
        self.logic.set_rarity_index(idx)
        self._refresh_list()

    def _on_region_changed(self, *a, **k):
        dd = self.get("dd_region")
        if dd is None: return
        try:
            idx = self.logic.get_region_labels().index(dd.value)
        except ValueError:
            idx = 0
        self.logic.set_region_index(idx)
        self._refresh_list()

    def _refresh_list(self):
        # CORRIGIDO: mesmo ID do _feed_grid
        grid = self.get("cards_list")
        if grid is not None:
            grid.scroll = 0
        self._feed_grid()
        self._update_stats()
        self._populate_detail()

    def _refresh_search_label(self):
        lbl = self.get("lbl_search_text")
        if lbl is None: return
        txt = self.logic.search_text

        # CORRIGIDO: cores alinhadas com o JSON (texto #3A2210 sobre #FBF6E0)
        if not txt and not self.search_active:
            lbl.text = "Buscar..."
            lbl.text_color = (90, 58, 16)      # #5A3A10 (placeholder)
            return

        lbl.text_color = (58, 34, 16)          # #3A2210 (texto digitado)

        if self.search_active and int(self.search_cursor_t * 2) % 2 == 0:
            lbl.text = (txt or "") + "|"
        else:
            lbl.text = txt or "|"

    # =================================================================
    def _on_back(self, btn=None):
        from src.scenes.phase_selector.phase_select_scene import PhaseSelectScene
        self.game.phase_select_scene = PhaseSelectScene(self.game)
        self.game.current_scene = self.game.phase_select_scene

    # =================================================================
    # Eventos
    # =================================================================
    def handle_event(self, event):
        if self.search_active and event.type == pygame.KEYDOWN:
            if event.key == pygame.K_ESCAPE:
                self.search_active = False
                self.logic.set_search("")
                self._refresh_search_label()
                self._refresh_list()
                return True
            if event.key == pygame.K_RETURN:
                self.search_active = False
                self._refresh_search_label()
                return True
            if event.key == pygame.K_BACKSPACE:
                self.logic.set_search(self.logic.search_text[:-1])
                self._refresh_search_label()
                self._refresh_list()
                return True
            if event.unicode and event.unicode.isprintable():
                self.logic.set_search(self.logic.search_text + event.unicode)
                self._refresh_search_label()
                self._refresh_list()
                return True
            return True

        if (self.search_active and
                event.type == pygame.MOUSEBUTTONDOWN and event.button == 1):
            sp = self.get("search_panel")
            if sp is None or not sp.rect.collidepoint(event.pos):
                self.search_active = False
                self._refresh_search_label()

        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            sp = self.get("search_panel")
            if sp is not None and sp.rect.collidepoint(event.pos):
                self.search_active = True
                self._refresh_search_label()
                return True

        if event.type == pygame.KEYDOWN and event.key == pygame.K_f:
            self.search_active = True
            self._refresh_search_label()
            return True

        super().handle_event(event)

    def fixed_update(self, dt):
        self.search_cursor_t += dt
        if self.search_active:
            self._refresh_search_label()
        super().fixed_update(dt)

    def on_back(self):
        self._on_back()