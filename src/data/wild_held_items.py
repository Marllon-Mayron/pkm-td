# src/data/wild_held_items.py

"""
Itens segurados por Pokémon selvagens.

DUAS ROLAGENS:
  1) Rolagem A (global): 5% → segura algo | 95% → nada
  2) Rolagem B (só se passou na A): sorteio ponderado entre os itens
"""

# ============================================================
# ROLAGEM A — chance global de segurar QUALQUER item
# ============================================================
WILD_HELD_ITEM_CHANCE = 0.05  # 5%

# ============================================================
# ROLAGEM B — pesos relativos (random.choices normaliza)
# ============================================================
WILD_HELD_ITEM_WEIGHTS = {
    "nugget":     1.0,    # muito raro
    "pearl":      0.5,    # extremamente raro
    "oranberry":  44.0,   # comum
    "leppaberry": 44.5,   # comum
}


def roll_wild_held_item(rng=None):
    """
    Rola as DUAS etapas:
      - Rolagem A: 5% de chance de segurar algo.
      - Rolagem B: escolhe qual item via sorteio ponderado.

    Retorna o item_id (str) ou None.
    """
    import random
    if rng is None:
        rng = random

    # ===== ROLAGEM A (5%) =====
    if rng.random() >= WILD_HELD_ITEM_CHANCE:
        return None

    # ===== ROLAGEM B (só chegamos aqui se passou na A) =====
    ids = list(WILD_HELD_ITEM_WEIGHTS.keys())
    weights = [WILD_HELD_ITEM_WEIGHTS[i] for i in ids]

    if not ids or sum(weights) <= 0:
        return None

    return rng.choices(ids, weights=weights, k=1)[0]