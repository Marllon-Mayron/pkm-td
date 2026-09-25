# src/data/wild_held_items.py

"""
Itens segurados por Pokémon selvagens.

DUAS ROLAGENS:
  1) Rolagem A (global): 5% → segura algo | 95% → nada
  2) Rolagem B (só se passou na A): sorteio ponderado entre os itens
     - Antes da B, verifica se a ESPÉCIE tem item exclusivo
       (ex: Meowth tem 20% de chance de Amulet Coin).
"""

import random

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

# ============================================================
# REGRAS ESPECIAIS POR ESPÉCIE
# ============================================================
# Estrutura: pokemon_id (int) -> lista de regras
#
# Cada regra é um dict:
#   {
#       "item_id": "amulet_coin",   # item a ser sorteado
#       "chance": 0.10,             # chance (sobre a rolagem A já aprovada)
#       "priority": 0,              # (opcional) ordem de teste; menor = testado antes
#       "shiny_only": False,        # (opcional) só vale se for shiny
#       "level_min": 0,             # (opcional) só vale a partir desse nível
#   }
#
# Como funciona:
#   - Se o Pokémon passou na Rolagem A (5%):
#       1. Percorre as regras da espécie em ordem de prioridade.
#       2. Rola a chance de cada regra.
#       3. A PRIMEIRA que passar define o item.
#       4. Se nenhuma passar, cai na Rolagem B normal.
# ============================================================
SPECIES_HELD_ITEM_RULES = {
    # ----------------------------------------------------------
    # MEOWTH (52) — caça ao Amulet Coin
    # ----------------------------------------------------------
    52: [
        {"item_id": "amulet_coin", "chance": 0.20, "priority": 0},
    ],

    # ----------------------------------------------------------
    # SHELLDER (90) — pérolas
    # ----------------------------------------------------------
    90: [
        {"item_id": "big_pearl", "chance": 0.60, "priority": 0},
        {"item_id": "pearl",     "chance": 0.40, "priority": 1},
    ],

    # ----------------------------------------------------------
    # FARFETCH'D (83) — Stick
    # ----------------------------------------------------------
    83: [
        {"item_id": "stick", "chance": 0.30, "priority": 0},
    ],

    # ----------------------------------------------------------
    # CUBONE (104) — Thick Club
    # ----------------------------------------------------------
    104: [
        {"item_id": "thick_club", "chance": 0.10, "priority": 0},
    ],
    # ----------------------------------------------------------
    # PICHU (172) — Light Ball
    # ----------------------------------------------------------
    172: [
        {"item_id": "light_ball", "chance": 0.30, "priority": 0},
    ],

    # ----------------------------------------------------------
    # CHANSEY (113) — Lucky Punch
    # ----------------------------------------------------------
    113: [
        {"item_id": "lucky_punch", "chance": 0.30, "priority": 0},
    ],
    # ----------------------------------------------------------
    # PARAS (46) — cogumelos
    # 10% Big Mushroom, 20% Tiny Mushroom, resto cai na comum.
    # ----------------------------------------------------------
    46: [
        {"item_id": "big_mushroom",  "chance": 0.10, "priority": 0},
        {"item_id": "tiny_mushroom", "chance": 0.20, "priority": 1},
    ],
}


def _roll_species_rule(pokemon_id, is_shiny=False, level=1, rng=random):
    """
    Rola as regras especiais de uma espécie.
    Retorna o item_id se alguma regra passar, senão None.
    """
    if pokemon_id is None:
        return None

    rules = SPECIES_HELD_ITEM_RULES.get(pokemon_id)
    if not rules:
        return None

    ordered = sorted(rules, key=lambda r: r.get("priority", 0))

    for rule in ordered:
        if rule.get("shiny_only") and not is_shiny:
            continue
        if level < rule.get("level_min", 0):
            continue

        chance = float(rule.get("chance", 0.0))
        if chance <= 0:
            continue

        if rng.random() < chance:
            return rule["item_id"]

    return None


def roll_wild_held_item(pokemon_id=None, is_shiny=False, level=1, rng=None):
    """
    Rola as DUAS etapas:
      - Rolagem A: 5% de chance de segurar algo.
      - Rolagem B: item exclusivo da espécie (se houver) OU sorteio ponderado.

    Retorna o item_id (str) ou None.
    """
    if rng is None:
        rng = random

    # ===== ROLAGEM A (5%) =====
    if rng.random() >= WILD_HELD_ITEM_CHANCE:
        return None

    # ===== ROLAGEM ESPECIAL (item exclusivo da espécie) =====
    special = _roll_species_rule(pokemon_id, is_shiny=is_shiny,
                                  level=level, rng=rng)
    if special:
        return special

    # ===== ROLAGEM B (sorteio ponderado normal) =====
    ids = list(WILD_HELD_ITEM_WEIGHTS.keys())
    weights = [WILD_HELD_ITEM_WEIGHTS[i] for i in ids]

    if not ids or sum(weights) <= 0:
        return None

    return rng.choices(ids, weights=weights, k=1)[0]