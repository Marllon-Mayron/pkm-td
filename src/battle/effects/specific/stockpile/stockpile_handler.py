# src/battle/effects/specific/stockpile_handler.py
"""
Gerenciador do estado de Stockpile.
Compartilhado entre Stockpile, Spit Up e Swallow.

Estado armazenado no Pokémon: pokemon._stockpile_count (0 a 3)
"""


class StockpileHandler:
    """Gerencia as cargas de Stockpile."""

    MAX_STACKS = 3

    # ===== ESTADO =====

    @classmethod
    def get_stacks(cls, pokemon) -> int:
        """Retorna quantas cargas o Pokémon tem (0-3)."""
        return getattr(pokemon, '_stockpile_count', 0)

    @classmethod
    def add_stack(cls, pokemon) -> int:
        """
        Adiciona uma carga (cap no MAX_STACKS).
        Retorna o novo número de cargas.
        """
        current = cls.get_stacks(pokemon)
        if current >= cls.MAX_STACKS:
            return current
        pokemon._stockpile_count = current + 1
        return pokemon._stockpile_count

    @classmethod
    def clear(cls, pokemon):
        """Zera as cargas (sem tocar em Def/SpDef)."""
        pokemon._stockpile_count = 0

    # ===== CÁLCULOS =====

    @classmethod
    def get_spit_up_power(cls, pokemon) -> int:
        """Poder do Spit Up: 100 × cargas."""
        return 100 * cls.get_stacks(pokemon)

    @classmethod
    def get_swallow_heal_fraction(cls, pokemon) -> float:
        """
        Fração de HP curada pelo Swallow:
          1 carga  -> 25%
          2 cargas -> 50%
          3 cargas -> 100%
        """
        stacks = cls.get_stacks(pokemon)
        if stacks <= 0:
            return 0.0
        if stacks == 1:
            return 0.25
        if stacks == 2:
            return 0.50
        return 1.0