"""Gera todos os JSONs de spray medicinal.

Rode:  python tools/generate_spray_jsons.py

Cada spray sai com:
  - scale_mult = 0.5      → encolhe o efeito inteiro (calibre aqui)
  - anchor_mode = "center" → spray no centro da hitbox do pokémon
  - world_scaled = True    → escala junto com o zoom do jogador
  - world_offset = (0, 0)  → sem offset vertical
"""
import json
from pathlib import Path


OUT = Path("res/animations/items")
OUT.mkdir(parents=True, exist_ok=True)


# =====================================================================
# CONFIG GLOBAL — aplicada a TODOS os sprays
# =====================================================================
DEFAULT_SCALE_MULT = 0.35         # spray compacto
DEFAULT_ANCHOR_MODE = "center"    # centro da hitbox
DEFAULT_WORLD_SCALED = True       # acompanha zoom do jogador


# =====================================================================
# TABELA DE ITENS
# =====================================================================
SPRAYS = {
    "potion": {
        "desc": "Borrifada de Potion",
        "tints": ["#FF5050", "#FF6060", "#FF8080", "#FFA0A0", "#FFC8C8"],
        "sparkle": "#FFE0E0",
        "trigger": "item.potion.use_on_ally",
    },
    "superpotion": {
        "desc": "Borrifada de Super Potion",
        "tints": ["#FF3060", "#FF4070", "#FF5080", "#FF80A0", "#FFB0C8"],
        "sparkle": "#FFC0D0",
        "trigger": "item.superpotion.use_on_ally",
    },
    "hyperpotion": {
        "desc": "Borrifada de Hyper Potion",
        "tints": ["#E00050", "#F00060", "#FF2080", "#FF60A0", "#FFA0C8"],
        "sparkle": "#FFB0D0",
        "trigger": "item.hyperpotion.use_on_ally",
    },
    "moomoo_milk": {
        "desc": "Borrifada de Moomoo Milk",
        "tints": ["#E8E0C0", "#F0E8D0", "#FFF8E0", "#FFFCF0", "#FFFFFF"],
        "sparkle": "#FFF8C0",
        "trigger": "item.moomoo_milk.use_on_ally",
    },
    "antidote": {
        "desc": "Borrifada de Antidote",
        "tints": ["#40C040", "#60D060", "#80E070", "#A0FFA0", "#C8FFC8"],
        "sparkle": "#C8FFC8",
        "trigger": "item.antidote.use_on_ally",
    },
    "paralyze_heal": {
        "desc": "Borrifada de Paralyze Heal",
        "tints": ["#D0A000", "#E0B020", "#FFD040", "#FFE070", "#FFF0A0"],
        "sparkle": "#FFE080",
        "trigger": "item.paralyze_heal.use_on_ally",
    },
    "awakening": {
        "desc": "Borrifada de Awakening",
        "tints": ["#4070D0", "#5090E0", "#80C0FF", "#A0D8FF", "#C8E8FF"],
        "sparkle": "#C0E0FF",
        "trigger": "item.awakening.use_on_ally",
    },
    "burn_heal": {
        "desc": "Borrifada de Burn Heal",
        "tints": ["#D05010", "#E07020", "#FF8040", "#FFA060", "#FFC090"],
        "sparkle": "#FFB080",
        "trigger": "item.burn_heal.use_on_ally",
    },
    "ice_heal": {
        "desc": "Borrifada de Ice Heal",
        "tints": ["#40C0D0", "#60D0E0", "#80FFFF", "#A0FFFF", "#C8FFFF"],
        "sparkle": "#C0FFFF",
        "trigger": "item.ice_heal.use_on_ally",
    },
    "full_heal": {
        "desc": "Borrifada de Full Heal (arco-íris)",
        "tints": ["#C0A0FF", "#A0D0FF", "#80FFE0", "#FFFFA0", "#FFFFFF"],
        "sparkle": "#FFFFFF",
        "trigger": "item.full_heal.use_on_ally",
    },
}


# =====================================================================
# SMOKE — converge no centro do pokémon
# =====================================================================
# (id, z, ox, oy, T_idx, vis_s, vis_e, [(f, x, y, scale, alpha, fi), ...])
SMOKE_LAYERS = [
    ("smoke_far_back", 2, 0, 0, 0, 8, 96, [
        (8,  -35, 4, 1.5,   0, 0), (20, -22, 0, 3.5, 200, 2),
        (34,  -8,-4, 5.0, 220, 3), (50,   0,-10, 6.5, 200, 5),
        (68,   0,-20, 7.5, 140, 6), (84,  0,-32, 8.2,  70, 7),
        (96,   0,-46, 8.6,   0, 7),
    ]),
    ("smoke_far", 3, 0, 0, 1, 6, 94, [
        (6,  -38, 4, 1.6,   0, 0), (16, -24, 0, 3.8, 220, 1),
        (28, -10,-4, 5.4, 240, 2), (42,   0,-10, 6.8, 220, 4),
        (58,   0,-18, 7.7, 160, 5), (76,  0,-28, 8.2,  90, 6),
        (94,   0,-42, 8.6,   0, 7),
    ]),
    ("smoke_main", 4, 0, 0, 2, 4, 92, [
        (4,  -40, 2, 1.8,   0, 0), (12, -26, 0, 4.2, 255, 0),
        (22, -12,-2, 5.8, 255, 1), (34,  -2,-6, 7.2, 255, 2),
        (46,   0,-10, 8.2, 240, 3), (60,  0,-18, 9.0, 200, 4),
        (74,   0,-28, 9.6, 140, 5), (84,  0,-38,10.0,  70, 6),
        (92,   0,-50,10.4,   0, 7),
    ]),
    ("smoke_near", 5, 0, 0, 3, 8, 90, [
        (8,  -38, 0, 1.4,   0, 0), (18, -24,-2, 3.6, 240, 1),
        (30, -10,-4, 5.2, 255, 2), (44,   0,-8, 6.5, 220, 4),
        (58,   0,-14, 7.4, 160, 5), (74,  0,-22, 8.2,  90, 6),
        (90,   0,-32, 8.6,   0, 7),
    ]),
    ("smoke_front", 6, 0, 0, 4, 12, 96, [
        (12, -36, 0, 1.2,   0, 0), (22, -22,-2, 3.0, 220, 1),
        (34,  -8,-4, 4.5, 240, 2), (48,   0,-6, 5.8, 200, 3),
        (62,   0,-12, 6.8, 150, 5), (78,  0,-20, 7.6,  80, 6),
        (96,   0,-30, 8.0,   0, 7),
    ]),
]

BOTTLE_KEYFRAMES = [
    (0,  -12, -22, 15, 2.2,   0),
    (8,    0,   0, 32, 2.2, 255),
    (16,   3,  -2, 36, 2.2, 255),
    (26,  -2,  -1, 30, 2.2, 255),
    (36,   3,  -2, 35, 2.2, 255),
    (46,  -2,  -1, 31, 2.2, 255),
    (56,   0,  -4, 33, 2.2, 255),
    (68,   0, -14, 22, 2.0,   0),
]

SPARKLE_KFS_A = [
    (22,  0,  4, 0.4,   0), (28,  2,   0, 1.0, 255),
    (42,  4,-10, 1.2, 255), (58,  5, -22, 1.3, 200),
    (78,  4,-34, 1.0, 100), (98,  2, -44, 0.6,   0),
]
SPARKLE_KFS_B = [
    (32, -6,  4, 0.4,   0), (38, -8,   0, 0.9, 255),
    (50,-10,-12, 1.1, 255), (66,-10, -26, 1.2, 180),
    (82, -8,-38, 0.9,  80), (98, -5, -48, 0.5,   0),
]


# =====================================================================
# BUILDERS
# =====================================================================
def build_smoke_layer(entry, tints):
    lid, z, ox, oy, t_idx, vis_s, vis_e, kfs = entry
    return {
        "id": lid, "type": "sprite",
        "image": "_shared/smoke_8f.png",
        "z": z, "blend": "normal", "pivot": "center",
        "offset": {"x": ox, "y": oy},
        "visible_frames": [vis_s, vis_e],
        "flip_x": False, "flip_y": False,
        "keyframes": [
            {"f": f, "x": x, "y": y, "scale": s, "alpha": a,
             "tint": tints[t_idx], "frame_index": fi}
            for (f, x, y, s, a, fi) in kfs
        ],
        "easing": "linear",
        "frame_width": 16, "frame_height": 16, "frame_index": 0,
    }


def build_bottle(item_id):
    return {
        "id": "bottle", "type": "sprite",
        "image": f"item://{item_id}",
        "z": 10, "blend": "normal", "pivot": "bottom_center",
        "offset": {"x": -52, "y": -6},
        "visible_frames": [0, 68],
        "flip_x": True, "flip_y": False,
        "keyframes": [
            {"f": f, "x": x, "y": y, "rot": r, "scale": s,
             "alpha": a, "tint": "#FFFFFF"}
            for (f, x, y, r, s, a) in BOTTLE_KEYFRAMES
        ],
        "easing": "ease_out",
        "frame_width": 0, "frame_height": 0, "frame_index": 0,
    }


def build_sparkle(lid, offset_x, vis_s, vis_e, kfs, tint):
    keyframes = []
    for (f, x, y, s, a) in kfs:
        t = tint if a > 0 else "#FFFFFF"
        keyframes.append({
            "f": f, "x": x, "y": y, "scale": s,
            "alpha": a, "tint": t,
        })
    return {
        "id": lid, "type": "sprite",
        "image": "_shared/sparkle_16.png",
        "z": 8, "blend": "add", "pivot": "center",
        "offset": {"x": offset_x, "y": 0},   # sparkles no centro
        "visible_frames": [vis_s, vis_e],
        "flip_x": False, "flip_y": False,
        "keyframes": keyframes,
        "easing": "linear",
        "frame_width": 0, "frame_height": 0, "frame_index": 0,
    }


def build_spray(item_id, cfg):
    tints = cfg["tints"]
    return {
        "schema_version": 1,
        "name": f"{item_id}_spray",
        "category": "items",
        "description": cfg["desc"],

        # ===== INTEGRAÇÃO COM O JOGO =====
        "scale_mult": float(cfg.get("scale_mult", DEFAULT_SCALE_MULT)),
        "anchor_mode": cfg.get("anchor_mode", DEFAULT_ANCHOR_MODE),
        "world_scaled": bool(cfg.get("world_scaled", DEFAULT_WORLD_SCALED)),

        "fps": 60,
        "duration_frames": 100,
        "loop": False,
        "loop_count": 0,
        "anchor": "target",
        "space": "world",
        "world_offset": {"x": 0, "y": 0},    # âncora no centro, sem offset
        "screen_offset": {"x": 0, "y": 0},
        "sound": {"name": "CLICK", "source": "sfx",
                  "start_frame": 3, "loop": False, "volume": 0.6},
        "layers": [
            *[build_smoke_layer(e, tints) for e in SMOKE_LAYERS],
            build_bottle(item_id),
            build_sparkle("sparkle_a", 0, 22, 98, SPARKLE_KFS_A, cfg["sparkle"]),
            build_sparkle("sparkle_b", 0, 32, 98, SPARKLE_KFS_B, cfg["sparkle"]),
        ],
        "default_binding": {"trigger": cfg["trigger"]},
    }


# =====================================================================
# GERA
# =====================================================================
if __name__ == "__main__":
    print(f"[GEN] scale_mult    = {DEFAULT_SCALE_MULT}")
    print(f"[GEN] anchor_mode   = {DEFAULT_ANCHOR_MODE}")
    print(f"[GEN] world_scaled  = {DEFAULT_WORLD_SCALED}")
    print()
    for item_id, cfg in SPRAYS.items():
        path = OUT / f"{item_id}_spray.json"
        data = build_spray(item_id, cfg)
        with open(path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
        print(f"✓ {path}")
    print(f"\n{len(SPRAYS)} sprays gerados em {OUT.resolve()}")