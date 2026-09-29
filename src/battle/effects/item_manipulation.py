# src/battle/effects/item_manipulation.py
"""
Utilitários para manipulação de itens segurados em batalha.

Usado por: Trick, Knock Off, Covet, Recycle.

Regras gerais (Gen 3+):
- Sticky Hold / Multitype bloqueiam manipulação
- Itens removidos/roubados/trocados NÃO podem ser recuperados com Recycle
- Recycle só recupera o último item CONSUMIDO (não o perdido)
"""
from typing import Optional, Tuple


class ItemManipulation:
    """Helper para trocar/remover/roubar itens segurados."""

    # ===== CHECAGENS =====

    @staticmethod
    def can_manipulate_item(pokemon) -> bool:
        """
        Verifica se o item deste Pokémon pode ser manipulado.
        Retorna False para derrotados, Sticky Hold, Multitype.
        """
        if pokemon is None:
            return False
        if getattr(pokemon, 'is_defeated', False):
            return False
        if not pokemon.is_alive():
            return False

        # Habilidades que bloqueiam manipulação
        if hasattr(pokemon, 'has_ability'):
            try:
                if pokemon.has_ability("Sticky Hold"):
                    return False
                if pokemon.has_ability("Multitype"):
                    return False
            except Exception:
                # Sistema de habilidade pode não estar implementado ainda
                pass

        return True

    # ===== ACESSO =====

    @staticmethod
    def get_item(pokemon) -> Optional[Tuple[str, dict]]:
        """Retorna (item_id, item_data) ou None se não tiver item."""
        if pokemon is None:
            return None
        item_id = getattr(pokemon, 'held_item', None)
        if not item_id:
            return None
        item_data = getattr(pokemon, 'held_item_data', None)
        return (item_id, item_data)

    # ===== MUTAÇÕES =====

    @staticmethod
    def give_item(pokemon, item_id, item_data):
        """Dá um item ao Pokémon (invalida Recycle — item veio de fora)."""
        pokemon.held_item = item_id
        pokemon.held_item_data = item_data
        ItemManipulation.invalidate_recycle(pokemon)

    @staticmethod
    def remove_item(pokemon) -> Optional[Tuple[str, dict]]:
        """
        Remove o item do Pokémon.
        Retorna (item_id, item_data) se havia algo, senão None.
        """
        if pokemon is None:
            return None

        item = ItemManipulation.get_item(pokemon)
        pokemon.held_item = None
        pokemon.held_item_data = None
        ItemManipulation.invalidate_recycle(pokemon)
        return item

    @staticmethod
    def swap_items(a, b) -> bool:
        """
        Troca os itens entre dois Pokémon.
        Retorna True se a troca foi possível (mesmo se um dos dois não tinha item).
        """
        if not ItemManipulation.can_manipulate_item(a):
            return False
        if not ItemManipulation.can_manipulate_item(b):
            return False

        a_item = ItemManipulation.get_item(a)
        b_item = ItemManipulation.get_item(b)

        # Aplica item de B em A
        if b_item:
            a.held_item = b_item[0]
            a.held_item_data = b_item[1]
        else:
            a.held_item = None
            a.held_item_data = None

        # Aplica item de A em B
        if a_item:
            b.held_item = a_item[0]
            b.held_item_data = a_item[1]
        else:
            b.held_item = None
            b.held_item_data = None

        # Invalida Recycle em ambos (não podem recuperar o que deram)
        ItemManipulation.invalidate_recycle(a)
        ItemManipulation.invalidate_recycle(b)
        return True

    @staticmethod
    def invalidate_recycle(pokemon):
        """
        Bloqueia o Recycle deste Pokémon.
        Chamado quando o item é perdido/trocado/roubado.
        """
        if pokemon is None:
            return
        pokemon._last_consumed_item = None

    # ===== RECYCLE (registro de consumo) =====

    @staticmethod
    def register_consumed_item(pokemon):
        """
        Registra o item ATUAL do Pokémon como o último consumido.
        Deve ser chamado ANTES de zerar held_item (ex: berries).
        """
        if pokemon is None:
            return
        item_id = getattr(pokemon, 'held_item', None)
        if not item_id:
            pokemon._last_consumed_item = None
            return

        item_data = getattr(pokemon, 'held_item_data', None)
        # Cópia defensiva para não ser afetada por mutações posteriores
        pokemon._last_consumed_item = (
            item_id,
            dict(item_data) if item_data else None
        )