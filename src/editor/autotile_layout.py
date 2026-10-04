# src/editor/autotile_layout.py

"""
Layout visual dos 47 autotiles no formato 8x6 (com 1 slot variante).
Mesma ordem usada pelo template gerado em autotile_template_16.png.
"""

VARIANT = "variant"

ORDER = [
    # ---- Linha 0: Fundamentos ----
    0,    # isolado
    1,    # endcap N   (topo)
    4,    # endcap E   (direita)
    16,   # endcap S   (baixo)
    64,   # endcap W   (esquerda)
    17,   # corredor vertical  (N + S)
    68,   # corredor horizontal (E + W)
    255,  # interior

    # ---- Linha 1: Cantos externos (L-shapes) ----
    5,    # canto NE sem diagonal
    7,    # canto NE com diagonal
    20,   # canto SE sem diagonal
    28,   # canto SE com diagonal
    80,   # canto SW sem diagonal
    112,  # canto SW com diagonal
    65,   # canto NW sem diagonal
    193,  # canto NW com diagonal

    # ---- Linha 2: T-shapes (sem diagonal + primeiras com 1 diagonal) ----
    21, 84, 81, 69, 23, 29, 92, 116,

    # ---- Linha 3: T-shapes com 1 e 2 diagonais ----
    113, 209, 197, 71, 31, 124, 241, 199,

    # ---- Linha 4: Cantos internos ----
    253, 247, 223, 127, 245, 125, 95, 215,

    # ---- Linha 5: Internos complexos + slot variante ----
    221, 119, 213, 117, 93, 87, 85,
    (VARIANT, 255, 0.20),  # slot 47: 20% de chance de substituir o interior (mask 255)
]

assert len(ORDER) == 48, f"ORDER deve ter 48 entradas, tem {len(ORDER)}"


def is_variant(entry):
    return isinstance(entry, tuple) and len(entry) == 3 and entry[0] == VARIANT


def is_normal(entry):
    return isinstance(entry, int)


def is_empty(entry):
    return entry is None