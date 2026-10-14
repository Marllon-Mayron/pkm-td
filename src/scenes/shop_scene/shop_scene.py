# src/scenes/shop_scene/shop_scene.py
"""
Loja — StandardScreen + JSON + Logic.
Busca com foco: clique no input, digite, ESC/click fora blur.
"""
import pygame

from src.ui.screen_template import StandardScreen
from src.ui.screen_loader import ScreenLoader
from src.managers.sounds.sound_manager import sound_manager, SoundEffect

from .shop_logic import ShopLogic


LAYOUT_PATH = "res/ui_layouts/shop.json"


class ShopScene(StandardScreen):
    title = ""
    show_back_button = False

    # =================================================================
    def __init__(self, game, return_scene=None):
        self.return_scene = return_scene or "phase_select"
        self.logic = ShopLogic(game)

        self._search_focused = False
        self._cursor_t = 0.0

        super().__init__(game)

    # =================================================================
    # CICLO DE VIDA
    # =================================================================
    def build(self):
        ScreenLoader.load(self, LAYOUT_PATH)
        self._refresh_all()

    def enter(self):
        self._search_focused = False
        self._refresh_all()

    # =================================================================
    # ACTIONS
    # =================================================================
    def get_actions(self):
        return {
            "back":                  lambda *_: self._on_back(),
            "tab_buy":               lambda *_: self._switch_tab("buy"),
            "tab_sell":              lambda *_: self._switch_tab("sell"),
            "buy_category_changed":  lambda *_: self._on_category_changed("buy"),
            "sell_category_changed": lambda *_: self._on_category_changed("sell"),
            "buy_click":             lambda idx: self._on_card_click(idx, "buy"),
            "sell_click":            lambda idx: self._on_card_click(idx, "sell"),
            "search_clear":          lambda *_: self._on_search_clear(),
            "qty_minus":             lambda *_: self._qty_step("dec", 1),
            "qty_plus":              lambda *_: self._qty_step("inc", 1),
            "qty_minus_10":          lambda *_: self._qty_step("dec", 10),
            "qty_plus_10":           lambda *_: self._qty_step("inc", 10),
            "qty_max":               lambda *_: self._qty_step("max", 0),
            "qty_cancel":            lambda *_: self._close_qty(),
            "qty_confirm":           lambda *_: self._confirm_qty(),
        }

    # =================================================================
    # REFRESH
    # =================================================================
    def _refresh_all(self):
        self.logic.refresh()
        self._apply_tab()
        self._update_money()
        self._feed_grids()
        self._update_counts()
        self._update_empty_labels()
        self._update_search_display()
        self._update_modal_visibility()

    def _feed_grids(self):
        buy = self.get("buy_grid")
        if buy is not None:
            buy.items = list(self.logic.buy_items)
            buy.scroll = 0
        sell = self.get("sell_grid")
        if sell is not None:
            sell.items = list(self.logic.sell_items)
            sell.scroll = 0

    def _refresh_list_only(self):
        """Só re-alimenta grids/counts — usado durante digitação."""
        self._feed_grids()
        self._update_counts()
        self._update_empty_labels()

    def _update_money(self):
        lbl = self.get("lbl_money")
        if lbl is not None:
            lbl.text = f"{int(self.game.player.money):,}".replace(",", ".")

    def _update_counts(self):
        bc = self.get("buy_count")
        if bc is not None:
            bc.text = f"{len(self.logic.buy_items)} itens"
        sc = self.get("sell_count")
        if sc is not None:
            sc.text = f"{len(self.logic.sell_items)} itens"

    def _update_empty_labels(self):
        be = self.get("buy_empty")
        if be is not None:
            be.visible = (self.logic.current_tab == "buy"
                          and not self.logic.buy_items)
        se = self.get("sell_empty")
        if se is not None:
            se.visible = (self.logic.current_tab == "sell"
                          and not self.logic.sell_items)

    # =================================================================
    # SEARCH
    # =================================================================
    def _update_search_display(self):
        lbl = self.get("search_lbl")
        inp = self.get("search_input")
        clr = self.get("search_clear")

        if lbl is None:
            return

        txt = self.logic.search_text
        focused = self._search_focused

        if not txt and not focused:
            lbl.text = "Buscar..."
            lbl.text_color = (110, 125, 150)
        else:
            if focused and int(self._cursor_t * 2) % 2 == 0:
                lbl.text = (txt or "") + "|"
            else:
                lbl.text = txt or "|"
            lbl.text_color = (232, 232, 240)

        # Botão X só aparece se há texto
        if clr is not None:
            clr.visible = bool(txt)

        # Borda de foco
        if inp is not None:
            inp.border_color = (255, 210, 74) if focused else (58, 72, 112)
            inp.border_width = 2

    def _on_search_clear(self):
        self.logic.clear_search()
        self._play_click(0.25)
        self.logic.refresh()
        self._refresh_list_only()
        self._update_search_display()

    def _on_search_focus(self):
        if not self._search_focused:
            self._search_focused = True
            self._update_search_display()

    def _on_search_blur(self):
        if self._search_focused:
            self._search_focused = False
            self._update_search_display()

    def _is_click_in_search(self, pos) -> bool:
        for wid in ("search_input", "search_lbl", "search_icon"):
            w = self.get(wid)
            if w is not None and getattr(w, "rect", None) is not None:
                if w.rect.collidepoint(pos):
                    return True
        return False

    # =================================================================
    # ABAS
    # =================================================================
    def _switch_tab(self, tab: str):
        if self.logic.current_tab == tab:
            return
        self.logic.current_tab = tab
        self._search_focused = False
        self._play_click(0.3)
        self._apply_tab()
        self._update_empty_labels()
        self._update_search_display()
        self._update_modal_visibility()

    def _apply_tab(self):
        is_buy = self.logic.current_tab == "buy"

        for wid in ("buy_filter_lbl", "buy_dd_category",
                    "buy_count", "buy_grid"):
            self._set_visible(wid, is_buy)
        for wid in ("sell_filter_lbl", "sell_dd_category",
                    "sell_count", "sell_grid"):
            self._set_visible(wid, not is_buy)

        tab_buy = self.get("tab_buy")
        if tab_buy is not None:
            tab_buy.fill_color = (42, 110, 62) if is_buy else (58, 58, 80)
            tab_buy.border_color = (90, 216, 112) if is_buy else (122, 122, 144)
        tab_sell = self.get("tab_sell")
        if tab_sell is not None:
            tab_sell.fill_color = (110, 62, 42) if not is_buy else (58, 58, 80)
            tab_sell.border_color = (216, 140, 90) if not is_buy else (122, 122, 144)

    def _set_visible(self, wid: str, v: bool):
        w = self.get(wid)
        if w is not None:
            w.visible = v

    # =================================================================
    # CATEGORIA
    # =================================================================
    def _on_category_changed(self, mode: str):
        if mode == "buy":
            dd = self.get("buy_dd_category")
            if dd is None:
                return
            cat_id = self._label_to_category(dd.value, self.logic.BUY_CATEGORIES)
            if cat_id is None:
                return
            self.logic.buy_category = cat_id
            self.logic.refresh_buy()
        else:
            dd = self.get("sell_dd_category")
            if dd is None:
                return
            cat_id = self._label_to_category(dd.value, self.logic.SELL_CATEGORIES)
            if cat_id is None:
                return
            self.logic.sell_category = cat_id
            self.logic.refresh_sell()

        self._feed_grids()
        self._update_counts()
        self._update_empty_labels()

    @staticmethod
    def _label_to_category(label: str, table):
        for cid, lbl in table:
            if lbl == label:
                return cid
        return None

    # =================================================================
    # CLIQUE EM CARD
    # =================================================================
    def _on_card_click(self, idx: int, mode: str):
        if idx < 0:
            return
        items = self.logic.buy_items if mode == "buy" else self.logic.sell_items
        if idx >= len(items):
            return
        card = items[idx]

        if not self.logic.open_qty(card):
            self._update_feedback()
            return

        self._play_click(0.3)
        self._refresh_qty_modal()
        self._update_modal_visibility()

    # =================================================================
    # QUANTITY MODAL
    # =================================================================
    def _refresh_qty_modal(self):
        item = self.logic.qty_item
        if item is None:
            return

        is_buy = self.logic.qty_mode == "buy"
        self._set_text("qty_title", "COMPRAR" if is_buy else "VENDER")
        self._set_text("qty_name", item["name"])
        self._set_text(
            "qty_unit",
            f"Preco unitario: $ {self.logic.qty_unit_price:,}".replace(",", "."))

        spr_w = self.get("qty_sprite")
        if spr_w is not None:
            spr_w.surface = item.get("sprite_surface")

        self._refresh_qty_value()

    def _refresh_qty_value(self):
        self._set_text("qty_value", str(self.logic.qty_value))
        total = self.logic.qty_total()
        self._set_text("qty_total_value", f"$ {total:,}".replace(",", "."))

        tv = self.get("qty_total_value")
        if tv is not None:
            if (self.logic.qty_mode == "buy"
                    and total > self.game.player.money):
                tv.text_color = (255, 130, 130)
            else:
                tv.text_color = (138, 240, 128)

    def _qty_step(self, action: str, amount: int):
        if not self.logic.qty_open:
            return
        if action == "inc":
            self.logic.qty_inc(amount)
        elif action == "dec":
            self.logic.qty_dec(amount)
        elif action == "max":
            self.logic.qty_max_out()
        self._play_click(0.2)
        self._refresh_qty_value()

    def _confirm_qty(self):
        if not self.logic.qty_open:
            return
        ok = self.logic.confirm_transaction()
        if ok:
            self._play_click(0.4)
            self._close_qty()
            self._refresh_all()
            try:
                self.game.player.auto_save()
            except Exception:
                pass
        else:
            self._update_feedback()
            self._refresh_qty_modal()

    def _close_qty(self):
        self.logic.close_qty()
        self._update_modal_visibility()

    def _update_modal_visibility(self):
        v = self.logic.qty_open
        for wid in (
            "qty_backdrop", "qty_panel",
            "qty_title", "qty_sprite_wrap", "qty_sprite",
            "qty_name", "qty_unit",
            "qty_value_box", "qty_minus", "qty_value", "qty_plus",
            "qty_minus_10", "qty_max", "qty_plus_10",
            "qty_total_panel", "qty_total_label", "qty_total_value",
            "qty_cancel", "qty_confirm",
        ):
            self._set_visible(wid, v)

    # =================================================================
    # HELPERS
    # =================================================================
    def _set_text(self, wid: str, text: str):
        w = self.get(wid)
        if w is not None and hasattr(w, "text"):
            w.text = text

    def _play_click(self, v=0.3):
        try:
            sound_manager.play_effect(SoundEffect.CLICK, volume=v)
        except Exception:
            pass

    # =================================================================
    # FEEDBACK
    # =================================================================
    def _update_feedback(self):
        lbl = self.get("feedback_lbl")
        if lbl is None:
            return
        if self.logic.has_feedback():
            lbl.visible = True
            lbl.text = self.logic.feedback_text
            kind = self.logic.feedback_kind
            if kind == "error":
                lbl.text_color = (255, 130, 130)
            elif kind == "success":
                lbl.text_color = (138, 240, 128)
            else:
                lbl.text_color = (200, 210, 240)
        else:
            lbl.visible = False

    # =================================================================
    # NAV
    # =================================================================
    def _on_back(self):
        self._play_click()
        if self.return_scene == "menu":
            from src.scenes.menu_scene import MenuScene
            self.game.current_scene = MenuScene(self.game)
        else:
            from src.scenes.phase_selector.phase_select_scene import PhaseSelectScene
            self.game.current_scene = PhaseSelectScene(self.game)

    # =================================================================
    # EVENTOS
    # =================================================================
    def handle_event(self, event):
        # ===== MODAL DE QUANTIDADE =====
        if self.logic.qty_open:
            super().handle_event(event)
            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_ESCAPE:
                    self._close_qty()
                elif event.key == pygame.K_RETURN:
                    self._confirm_qty()
            return

        # ===== BUSCA ATIVA =====
        if self._search_focused and event.type == pygame.KEYDOWN:
            if event.key == pygame.K_ESCAPE:
                self._on_search_blur()
                return
            if event.key == pygame.K_RETURN:
                self._on_search_blur()
                return
            if event.key == pygame.K_BACKSPACE:
                self.logic.set_search(self.logic.search_text[:-1])
                self.logic.refresh()
                self._refresh_list_only()
                self._update_search_display()
                return
            if event.key == pygame.K_DELETE:
                self.logic.clear_search()
                self.logic.refresh()
                self._refresh_list_only()
                self._update_search_display()
                return
            if event.unicode and event.unicode.isprintable():
                if len(self.logic.search_text) < 32:
                    self.logic.set_search(self.logic.search_text + event.unicode)
                    self.logic.refresh()
                    self._refresh_list_only()
                    self._update_search_display()
                return
            # Bloqueia teclas de navegação durante foco
            return

        # ===== CLICK: foco da busca =====
        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            if self._is_click_in_search(event.pos):
                self._on_search_focus()
                return
            else:
                self._on_search_blur()
                # continua processando normalmente para os outros widgets

        # ===== ATALHO: "/" foca a busca =====
        if event.type == pygame.KEYDOWN and event.key == pygame.K_SLASH:
            self._on_search_focus()
            return

        # ===== ESC global =====
        if event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE:
            self._on_back()
            return

        super().handle_event(event)

    # =================================================================
    # UPDATE
    # =================================================================
    def fixed_update(self, dt):
        self.logic.update(dt)
        self._update_feedback()

        # Cursor piscante
        if self._search_focused:
            self._cursor_t += dt
            self._update_search_display()

        super().fixed_update(dt)