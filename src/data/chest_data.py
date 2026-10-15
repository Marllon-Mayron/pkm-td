# src/data/chest_data.py
"""Definições dos baús — tipos, tempos, loot (itens + roupas) e sprite sheet."""
import random
import time
from typing import Optional, List, Dict


CHEST_TYPES = {
    "simple": {
        "id": "simple",
        "name": "BAU SIMPLES",
        "tagline": "Recompensas básicas",
        "duration_seconds": 20 * 60,
        "sprite_col": 0,
        "accent_color": "#C89050",
        "accent_dark":  "#3A2410",
        "rolls": 1,
        "clothing_rolls": [
            (0.45, ["common"]),
            (0.15, ["uncommon"]),
        ],
    },
    "rare": {
        "id": "rare",
        "name": "BAU RARO",
        "tagline": "Recompensas melhores",
        "duration_seconds": 40 * 60,
        "sprite_col": 1,
        "accent_color": "#5096FF",
        "accent_dark":  "#101C3A",
        "rolls": 2,
        "clothing_rolls": [
            (0.70, ["common", "uncommon"]),
            (0.40, ["uncommon", "rare"]),
            (0.12, ["rare"]),
        ],
    },
    "epic": {
        "id": "epic",
        "name": "BAU EPICO",
        "tagline": "As melhores recompensas",
        "duration_seconds": 60 * 60,
        "sprite_col": 2,
        "accent_color": "#C864F0",
        "accent_dark":  "#2A1040",
        "rolls": 3,
        "clothing_rolls": [
            (0.85, ["uncommon", "rare"]),
            (0.55, ["rare", "epic"]),
            (0.18, ["epic", "legendary"]),
        ],
    },
}

CHEST_ORDER = ["simple", "rare", "epic"]

RARITY_INFO = {
    "common":    {"name": "COMUM",    "color": "#C8C8C8"},
    "uncommon":  {"name": "INCOMUM",  "color": "#64DC78"},
    "rare":      {"name": "RARO",     "color": "#5096FF"},
    "epic":      {"name": "EPICO",    "color": "#C864F0"},
    "legendary": {"name": "LENDARIO", "color": "#FFC83C"},
}


# ============================================================
# LOOT — ITENS
# ============================================================
LOOT_SIMPLE = [
    ("potion",          30, 1, 3),
    ("pokeball",        30, 1, 5),
    ("antidote",        12, 1, 2),
    ("paralyze_heal",   12, 1, 2),
    ("awakening",       10, 1, 2),
    ("burn_heal",        8, 1, 2),
    ("ice_heal",         8, 1, 2),
    ("superpotion",      6, 1, 1),
    ("greatball",        4, 1, 1),
    ("firestone",        1, 1, 1),
    ("thunderstone",     1, 1, 1),
    ("waterstone",       1, 1, 1),
    ("leafstone",        1, 1, 1),
]

LOOT_RARE = [
    ("superpotion",     18, 1, 3),
    ("greatball",       18, 2, 3),
    ("hyperpotion",     14, 1, 2),
    ("revive",          12, 1, 2),
    ("ultraball",        8, 1, 2),
    ("full_heal",        8, 1, 2),
    ("moomoo_milk",      4, 1, 1),
    ("firestone",        4, 1, 1),
    ("thunderstone",     4, 1, 1),
    ("waterstone",       4, 1, 1),
    ("leafstone",        4, 1, 1),
    ("moonstone",        3, 1, 1),
    ("rare_candy",       6, 1, 1),
    ("pp_up",            4, 1, 1),
]

LOOT_EPIC = [
    ("hyperpotion",     14, 2, 3),
    ("ultraball",       14, 2, 4),
    ("revive",          12, 1, 3),
    ("full_heal",       10, 1, 3),
    ("max_revive",       8, 1, 2),
    ("moonstone",        7, 1, 1),
    ("sunstone",         5, 1, 1),
    ("shinystone",       5, 1, 1),
    ("dawnstone",        5, 1, 1),
    ("rare_candy",      10, 1, 2),
    ("pp_up",            7, 1, 1),
    ("pp_max",           4, 1, 1),
    ("nugget",           5, 1, 1),
    ("big_pearl",        5, 1, 1),
    ("masterball",       1, 1, 1),
]

CHEST_LOOT = {
    "simple": LOOT_SIMPLE,
    "rare":   LOOT_RARE,
    "epic":   LOOT_EPIC,
}


# ============================================================
# LOOT — ROUPAS
# ============================================================
CLOTHING_POOLS = {
    "common": [
        "skin_1", "skin_2",
        "eyes_1", "eyes_2", "eyes_3", "eyes_4", "eyes_6",
        "hair_1", "hair_2", "hair_3", "hair_5",
        "torso_2",
        "pants_1", "pants_4",
        "hat_2", "hat_3",
    ],
    "uncommon": [
        "eyes_7",
        "hair_6", "hair_7", "hair_8",
        "torso_1", "torso_4",
        "pants_2", "pants_3",
        "hat_1", "hat_4",
    ],
    "rare": [
        "hair_4",
        "torso_3", "torso_5",
        "pants_5",
        "hat_5",
    ],
    "epic": [
        "eyes_5",
    ],
    "legendary": [
        "eyes_8",
    ],
}


# ============================================================
# ROLAGEM
# ============================================================
def _roll_items(chest_type: str, rng) -> Dict[str, int]:
    cfg = CHEST_TYPES.get(chest_type)
    loot = CHEST_LOOT.get(chest_type, [])
    if not cfg or not loot:
        return {}

    rolls = cfg.get("rolls", 1)
    ids = [e[0] for e in loot]
    weights = [e[1] for e in loot]

    totals: Dict[str, int] = {}
    for _ in range(rolls):
        chosen = rng.choices(ids, weights=weights, k=1)[0]
        for iid, _w, mn, mx in loot:
            if iid == chosen:
                totals[iid] = totals.get(iid, 0) + rng.randint(mn, mx)
                break
    return totals


def _roll_clothing(chest_type: str, owned_ids: set, rng):
    """Retorna (item_id, is_duplicate) ou (None, False)."""
    cfg = CHEST_TYPES.get(chest_type) or {}
    rolls = cfg.get("clothing_rolls", [])
    if not rolls:
        return None, False

    for chance, rarities in rolls:
        if rng.random() >= chance:
            continue

        rarity = rng.choice(rarities)
        pool = CLOTHING_POOLS.get(rarity, [])
        if not pool:
            continue

        chosen = rng.choice(pool)
        is_dup = chosen in owned_ids
        print(f"[CHEST] Rola roupa: {chosen} (raridade={rarity}, dup={is_dup})")
        return chosen, is_dup

    return None, False


def roll_chest_rewards(
    chest_type: str,
    player=None,
    rng: Optional[random.Random] = None,
) -> List[Dict]:
    """Rola as recompensas de um baú (itens + 1 roupa opcional)."""
    if rng is None:
        rng = random

    totals = _roll_items(chest_type, rng)

    clothing_id = None
    clothing_dup = False
    if player is not None:
        owned_ids = set(getattr(player.bag, "items", {}).keys())
        clothing_id, clothing_dup = _roll_clothing(chest_type, owned_ids, rng)

    out: List[Dict] = []
    for iid, qty in totals.items():
        out.append({
            "item_id": iid,
            "qty": qty,
            "is_clothing": False,
            "is_duplicate": False,
        })
    if clothing_id:
        out.append({
            "item_id": clothing_id,
            "qty": 1,
            "is_clothing": True,
            "is_duplicate": clothing_dup,
        })

    rng.shuffle(out)
    return out


# ============================================================
# HELPERS DE TEMPO
# ============================================================
def make_chest_slot(slot_idx: int) -> Dict:
    ct = CHEST_ORDER[slot_idx]
    cfg = CHEST_TYPES[ct]
    return {
        "id": slot_idx,
        "status": "ready",
        "start_time": time.time(),
        "duration": float(cfg["duration_seconds"]),
        "rewards": [],
    }


def remaining_seconds(slot: Dict) -> float:
    if slot.get("status") != "cooldown":
        return 0.0
    elapsed = time.time() - float(slot.get("start_time", 0.0))
    return max(0.0, float(slot.get("duration", 0.0)) - elapsed)


def refresh_slot_status(slot: Dict) -> bool:
    if slot.get("status") == "cooldown":
        if remaining_seconds(slot) <= 0.0:
            slot["status"] = "ready"
            return True
    return False


# ============================================================
# SPRITE SHEET
# ============================================================
FRAME_SIZE = 32
FRAME_COUNT = 4

_sheet_cache = {"surface": None, "path": None}


def get_chest_sheet():
    import pygame
    from src.config.paths import SPRITES_PATH

    path = SPRITES_PATH / "UI" / "Icons" / "chests.png"
    if _sheet_cache["surface"] is not None and _sheet_cache["path"] == path:
        return _sheet_cache["surface"]

    _sheet_cache["path"] = path

    if not path.exists():
        print(f"[chest] Sheet não encontrado: {path}")
        _sheet_cache["surface"] = None
        return None

    if not pygame.get_init():
        pygame.init()

    try:
        surf = pygame.image.load(str(path))
        try:
            surf = surf.convert_alpha()
        except pygame.error:
            pass
        _sheet_cache["surface"] = surf
        return surf
    except Exception as e:
        print(f"[chest] Erro ao carregar sheet: {e}")
        _sheet_cache["surface"] = None
        return None


def get_chest_frame(chest_type: str, frame_idx: int = 0, scale_to=None):
    import pygame
    sheet = get_chest_sheet()
    if sheet is None:
        return _fallback_chest(chest_type, scale_to)

    cfg = CHEST_TYPES.get(chest_type)
    if not cfg:
        return None

    x = cfg["sprite_col"] * FRAME_SIZE
    y = (frame_idx % FRAME_COUNT) * FRAME_SIZE

    try:
        frame = sheet.subsurface((x, y, FRAME_SIZE, FRAME_SIZE)).copy()
    except Exception as e:
        print(f"[chest] Erro ao recortar {chest_type}/{frame_idx}: {e}")
        return _fallback_chest(chest_type, scale_to)

    if scale_to:
        frame = pygame.transform.scale(frame, scale_to)
    return frame


def _fallback_chest(chest_type, scale_to):
    import pygame
    size = scale_to or (FRAME_SIZE, FRAME_SIZE)
    color = (200, 144, 80)
    if chest_type == "rare":  color = (80, 150, 255)
    if chest_type == "epic":  color = (200, 100, 240)

    s = pygame.Surface(size, pygame.SRCALPHA)
    w, h = size
    pygame.draw.rect(s, color, (w // 8, h // 3, 3 * w // 4, h // 2),
                     border_radius=max(2, w // 16))
    pygame.draw.rect(s, (255, 220, 120), (w // 2 - 2, h // 2 - 4, 4, 10))
    return s


def clear_chest_sheet_cache():
    _sheet_cache["surface"] = None
    _sheet_cache["path"] = None