# src/scenes/chest_scene/chest_logic.py
"""Dados da tela de baús — sem render."""
import pygame
from typing import Optional, List, Dict

from src.data.chest_data import (
    CHEST_TYPES, CHEST_ORDER, RARITY_INFO,
    get_chest_frame, remaining_seconds,
)


class ChestLogic:
    SLOT_COUNT = 3

    def __init__(self, game):
        self.game = game
        self.player = game.player
        self._sprite_cache: Dict[tuple, pygame.Surface] = {}

    # ============================================================
    # SPRITES
    # ============================================================
    def chest_sprite(self, chest_type: str, frame: int = 0,
                     size=(160, 160)) -> Optional[pygame.Surface]:
        key = (chest_type, frame, size)
        if key in self._sprite_cache:
            return self._sprite_cache[key]
        surf = get_chest_frame(chest_type, frame, scale_to=size)
        self._sprite_cache[key] = surf
        return surf

    # ============================================================
    # SLOTS
    # ============================================================
    def get_slot(self, idx: int) -> Optional[dict]:
        if 0 <= idx < len(self.player.chests):
            return self.player.chests[idx]
        return None

    def chest_type_of(self, idx: int) -> str:
        if 0 <= idx < len(CHEST_ORDER):
            return CHEST_ORDER[idx]
        return "simple"

    def time_text(self, slot: dict) -> str:
        if slot["status"] == "ready":
            return "PRONTO"
        if slot["status"] == "opened":
            return "ABRIR"
        if slot["status"] == "cooldown":
            rem = remaining_seconds(slot)
            m = int(rem // 60)
            s = int(rem % 60)
            return f"{m:02d}:{s:02d}"
        return "—"

    def status_label(self, slot: dict) -> str:
        return {
            "ready":    "PRONTO",
            "opened":   "ABRIR",
            "cooldown": "AGUARDE",
        }.get(slot.get("status"), "—")

    def progress_ratio(self, slot: dict) -> float:
        """0..1 de progresso do cooldown."""
        if slot["status"] == "ready" or slot["status"] == "opened":
            return 1.0
        if slot["status"] != "cooldown":
            return 0.0
        dur = max(1.0, float(slot.get("duration", 1.0)))
        rem = remaining_seconds(slot)
        return max(0.0, min(1.0, 1.0 - (rem / dur)))

    # ============================================================
    # RECOMPENSAS (cards)
    # ============================================================
    def reward_items(self, rewards: List[dict]) -> List[dict]:
        from src.data.item_bag_catalog import item_bag_catalog
        out = []
        for r in rewards or []:
            iid = r.get("item_id")
            qty = int(r.get("qty", 1))
            is_clothing = bool(r.get("is_clothing"))
            is_dup = bool(r.get("is_duplicate"))

            data = item_bag_catalog.items.get(iid, {})
            name = data.get("name", iid)

            sprite = None
            try:
                sprite = item_bag_catalog.get_sprite(iid, scaled=True)
            except Exception:
                pass

            rar = data.get("rarity", "common")
            rinfo = RARITY_INFO.get(rar, RARITY_INFO["common"])
            rar_name = data.get("rarity_name") or rinfo["name"]
            rar_color = data.get("rarity_color") or rinfo["color"]

            if is_clothing and not is_dup:
                # Roupa nova → badge verde "NOVO!"
                qty_text = "NOVO!"
                bg_color = "#243A28"
            elif is_clothing and is_dup:
                # Roupa repetida → mostra a qty que vai acumular
                qty_text = f"x{qty}"
                bg_color = "#12172A"
            else:
                # Item normal
                qty_text = f"x{qty}" if qty > 1 else ""
                bg_color = "#12172A"

            out.append({
                "item_id": iid,
                "name": name,
                "qty_text": qty_text,
                "sprite": sprite,
                "rarity": rar,
                "rarity_name": rar_name,
                "rarity_color": rar_color,
                "bg_color": bg_color,
                "border_color": rar_color,
                "is_clothing": is_clothing,
                "is_duplicate": is_dup,
            })
        return out