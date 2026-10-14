# src/scenes/shop_scene/shop_logic.py
"""
Estado + regras da loja. Sem render, sem som, sem pygame.draw.
Itens bloqueados NÃO são retornados — a lógica filtra.
Busca textual filtra por nome e descrição.
"""
from typing import List, Optional

from src.data.item_bag_catalog import item_bag_catalog


def _hx(rgb) -> str:
    return "#{:02X}{:02X}{:02X}".format(*rgb)


def _darken(rgb, factor=0.18):
    return tuple(max(14, int(c * factor)) for c in rgb)


class ShopLogic:
    HIDDEN_CATEGORIES = {"clothing"}

    BUY_CATEGORIES = [
        ("all",         "TODOS"),
        ("pokeball",    "POKEBOLAS"),
        ("medicine",    "MEDICINA"),
        ("battle_item", "BATALHA"),
        ("tm",          "TMs/HMs"),
        ("items",       "ITENS"),
    ]

    SELL_CATEGORIES = [
        ("all",         "TODOS"),
        ("pokeball",    "POKEBOLAS"),
        ("medicine",    "MEDICINA"),
        ("battle_item", "BATALHA"),
        ("tm",          "TMs/HMs"),
        ("items",       "ITENS"),
        ("fossil",      "FOSSEIS"),
        ("held_item",   "SEGURAVEIS"),
    ]

    CATEGORY_COLORS = {
        "pokeball":    (220,  90,  90),
        "medicine":    ( 90, 200, 110),
        "battle_item": (230, 170,  70),
        "tm":          ( 90, 140, 230),
        "items":       (220, 190,  60),
        "fossil":      (200, 180, 130),
        "held_item":   (180, 140, 210),
        "all":         (150, 165, 195),
    }

    # ================================================================
    def __init__(self, game):
        self.game = game
        self.player = game.player
        self.catalog = item_bag_catalog

        self.current_tab = "buy"
        self.buy_category = "all"
        self.sell_category = "all"
        self.search_text = ""

        self.buy_items: List[dict] = []
        self.sell_items: List[dict] = []

        self.qty_open = False
        self.qty_mode: Optional[str] = None
        self.qty_item: Optional[dict] = None
        self.qty_max = 1
        self.qty_value = 1
        self.qty_unit_price = 0

        self.feedback_text = ""
        self.feedback_kind = "info"
        self.feedback_timer = 0.0

    # ================================================================
    # SEARCH
    # ================================================================
    def set_search(self, text: str):
        self.search_text = text or ""

    def clear_search(self):
        self.search_text = ""

    def _matches_search(self, name: str, description: str) -> bool:
        q = self.search_text.strip().lower()
        if not q:
            return True
        return (q in (name or "").lower()) or (q in (description or "").lower())

    # ================================================================
    # REFRESH
    # ================================================================
    def refresh(self):
        self.refresh_buy()
        self.refresh_sell()

    def refresh_buy(self):
        out = []
        for it in self.catalog.get_all_items():
            if it.get("not_for_sale", False):
                continue
            if it.get("category") in self.HIDDEN_CATEGORIES:
                continue
            if not self._is_unlocked(it):
                continue
            if (self.buy_category != "all"
                    and it.get("category") != self.buy_category):
                continue
            if not self._matches_search(
                    it.get("name", ""), it.get("description", "")):
                continue
            out.append(self._make_buy_card(it))

        out.sort(key=lambda d: (d["category"], d["_price"]))
        self.buy_items = out

    def refresh_sell(self):
        out = []
        for entry in self.player.bag.get_all_items_for_render():
            data = entry.get("data") or {}
            if data.get("category") in self.HIDDEN_CATEGORIES:
                continue
            if (self.sell_category != "all"
                    and data.get("category") != self.sell_category):
                continue
            if not self._matches_search(
                    data.get("name", ""), data.get("description", "")):
                continue
            out.append(self._make_sell_card(data))

        out.sort(key=lambda d: (d["category"], d["name"]))
        self.sell_items = out

    # ================================================================
    # CARD DICTS — apenas sprite, título, descrição e preço.
    # ================================================================
    def _make_buy_card(self, item_data: dict) -> dict:
        item_id = item_data["id"]
        category = item_data.get("category", "")
        cat_rgb = self.CATEGORY_COLORS.get(category, (140, 160, 200))

        price = int(item_data.get("price", 0))
        affordable = self.player.money >= price

        if affordable:
            price_bg, price_fg = "#14301C", "#8AF080"
        else:
            price_bg, price_fg = "#301818", "#FF9090"

        return {
            "id": item_id,
            "name": item_data.get("name", item_id),
            "description": item_data.get("description", ""),
            "sprite_surface": self.catalog.get_sprite(item_id, scaled=True),
            "category": category,
            "bg_color": _hx(_darken(cat_rgb, 0.18)),
            "border_color": _hx(cat_rgb),
            "price_text": f"$ {price:,}".replace(",", "."),
            "price_bg": price_bg,
            "price_fg": price_fg,
            "_price": price,
            "_mode": "buy",
        }

    def _make_sell_card(self, item_data: dict) -> dict:
        item_id = item_data["id"]
        category = item_data.get("category", "")
        cat_rgb = self.CATEGORY_COLORS.get(category, (140, 160, 200))

        price = int(item_data.get("price", 0))
        sell_price = max(1, int(price * 0.5))

        return {
            "id": item_id,
            "name": item_data.get("name", item_id),
            "description": item_data.get("description", ""),
            "sprite_surface": self.catalog.get_sprite(item_id, scaled=True),
            "category": category,
            "bg_color": _hx(_darken(cat_rgb, 0.18)),
            "border_color": _hx(cat_rgb),
            "price_text": f"$ {sell_price:,}".replace(",", "."),
            "price_bg": "#2A1828",
            "price_fg": "#FFC8A0",
            "_sell_price": sell_price,
            "_quantity": int(item_data.get("quantity", 0)),
            "_mode": "sell",
        }

    # ================================================================
    def _is_unlocked(self, item_data: dict) -> bool:
        unlock = item_data.get("unlock_phase") or item_data.get("unlock_chapter")
        if not unlock:
            return True
        try:
            from src.config.progress import progress_manager
            return progress_manager.is_phase_completed(unlock)
        except Exception:
            return True

    # ================================================================
    # QUANTITY MODAL
    # ================================================================
    def open_qty(self, card: dict) -> bool:
        mode = card.get("_mode")
        if mode == "buy":
            price = card["_price"]
            if price <= 0:
                return False
            max_affordable = self.player.money // price
            if max_affordable < 1:
                self.set_feedback("Dinheiro insuficiente!", "error")
                return False
            self.qty_max = min(99, max_affordable)
            self.qty_unit_price = price
        else:
            have = card.get("_quantity", 0)
            if have < 1:
                return False
            self.qty_max = have
            self.qty_unit_price = card["_sell_price"]

        self.qty_open = True
        self.qty_mode = mode
        self.qty_item = card
        self.qty_value = 1
        return True

    def close_qty(self):
        self.qty_open = False
        self.qty_item = None
        self.qty_mode = None

    def qty_inc(self, amount: int = 1):
        self.qty_value = min(self.qty_max, self.qty_value + amount)

    def qty_dec(self, amount: int = 1):
        self.qty_value = max(1, self.qty_value - amount)

    def qty_max_out(self):
        self.qty_value = max(1, self.qty_max)

    def qty_total(self) -> int:
        return self.qty_value * self.qty_unit_price

    # ================================================================
    # TRANSAÇÃO
    # ================================================================
    def confirm_transaction(self) -> bool:
        if not self.qty_item or self.qty_value < 1:
            return False
        if self.qty_mode == "buy":
            return self._do_buy()
        if self.qty_mode == "sell":
            return self._do_sell()
        return False

    def _do_buy(self) -> bool:
        total = self.qty_total()
        if self.player.money < total:
            self.set_feedback("Dinheiro insuficiente!", "error")
            return False
        item = self.qty_item
        self.player.money -= total
        self.player.bag.add_item(item["id"], self.qty_value)
        self.set_feedback(f"Comprou {self.qty_value}x {item['name']}", "success")
        return True

    def _do_sell(self) -> bool:
        item = self.qty_item
        item_id = item["id"]
        have = self.player.bag.get_quantity(item_id)
        if have < self.qty_value:
            self.set_feedback("Quantidade insuficiente!", "error")
            return False
        total = self.qty_total()
        self.player.money += total
        self.player.bag.remove_item(item_id, self.qty_value)
        self.set_feedback(f"Vendeu {self.qty_value}x {item['name']}", "success")
        return True

    # ================================================================
    # FEEDBACK
    # ================================================================
    def set_feedback(self, text: str, kind: str = "info", duration: float = 2.2):
        self.feedback_text = text
        self.feedback_kind = kind
        self.feedback_timer = duration

    def has_feedback(self) -> bool:
        return self.feedback_timer > 0 and bool(self.feedback_text)

    def update(self, dt: float):
        if self.feedback_timer > 0:
            self.feedback_timer = max(0.0, self.feedback_timer - dt)