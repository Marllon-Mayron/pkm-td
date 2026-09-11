# src/battle/held_item_effects.py
"""
Sistema de efeitos automáticos de itens segurados em batalha.

Arquitetura pensada para escalar:
- BaseBerry: interface comum (should_trigger / apply)
- Subclasses por berry: OranBerry, LeppaBerry, (futuro: CheriBerry, SitrusBerry, ...)
- BERRY_REGISTRY: item_id -> classe
- HeldItemEffectProcessor: chamado pelo BattleSystem a cada frame

Para adicionar uma nova berry:
1. Crie uma subclasse de BaseBerry
2. Registre em BERRY_REGISTRY
3. Pronto. O resto do sistema já processa automaticamente.
"""


# =====================================================================
# CLASSE BASE
# =====================================================================
class BaseBerry:
    """Interface comum para todas as berries consumíveis."""

    def __init__(self, item_id: str, item_data: dict):
        self.item_id = item_id
        self.item_data = item_data or {}

    @property
    def display_name(self) -> str:
        return self.item_data.get("name", self.item_id)

    def should_trigger(self, pokemon) -> bool:
        """Retorna True se a berry deve ser consumida agora."""
        return False

    def apply(self, pokemon, effect_manager, battle_system=None) -> bool:
        """Aplica o efeito. Retorna True se consumiu a berry."""
        return False


# =====================================================================
# BERRIES IMPLEMENTADAS
# =====================================================================
class OranBerry(BaseBerry):
    """
    Oran Berry: restaura 10 HP quando o Pokémon cai abaixo de 50% do HP máximo.
    """

    HEAL_AMOUNT = 10
    TRIGGER_THRESHOLD = 0.5  # 50%

    def should_trigger(self, pokemon) -> bool:
        if pokemon.max_hp <= 0:
            return False
        if pokemon.current_hp >= pokemon.max_hp:
            return False
        return pokemon.current_hp <= pokemon.max_hp * self.TRIGGER_THRESHOLD

    def apply(self, pokemon, effect_manager, battle_system=None) -> bool:
        if pokemon.current_hp >= pokemon.max_hp:
            return False

        heal = min(self.HEAL_AMOUNT, pokemon.max_hp - pokemon.current_hp)
        if heal <= 0:
            return False

        old_hp = pokemon.current_hp
        pokemon.current_hp += heal

        if effect_manager:
            effect_manager.add_status_text(
                pokemon,
                f"+{heal} HP ({self.display_name})",
                duration=1.5
            )

        print(f"[BERRY] {pokemon.name} comeu {self.display_name}! "
              f"HP: {old_hp} -> {pokemon.current_hp}")
        return True


class LeppaBerry(BaseBerry):
    """
    Leppa Berry: restaura 10 PP do move com menos PP quando algum dos
    4 moves cai abaixo de 50% do PP máximo.
    """

    RESTORE_AMOUNT = 10
    TRIGGER_THRESHOLD = 0.5  # 50%

    def _get_lowest_pp_move(self, pokemon):
        """Retorna o move com o menor ratio de PP (ignora moves cheios)."""
        best_move = None
        best_ratio = 1.0

        for move in pokemon.moves:
            if move.max_pp <= 0:
                continue
            if move.current_pp >= move.max_pp:
                continue

            ratio = move.current_pp / move.max_pp
            if ratio < best_ratio:
                best_ratio = ratio
                best_move = move

        return best_move

    def should_trigger(self, pokemon) -> bool:
        for move in pokemon.moves:
            if move.max_pp <= 0:
                continue
            if move.current_pp <= move.max_pp * self.TRIGGER_THRESHOLD:
                return True
        return False

    def apply(self, pokemon, effect_manager, battle_system=None) -> bool:
        target_move = self._get_lowest_pp_move(pokemon)
        if not target_move:
            return False

        restore = min(self.RESTORE_AMOUNT, target_move.max_pp - target_move.current_pp)
        if restore <= 0:
            return False

        old_pp = target_move.current_pp
        target_move.current_pp += restore

        if effect_manager:
            effect_manager.add_status_text(
                pokemon,
                f"{target_move.name}: +{restore} PP ({self.display_name})",
                duration=1.5
            )

        print(f"[BERRY] {pokemon.name} comeu {self.display_name}! "
              f"{target_move.name}: {old_pp} -> {target_move.current_pp} PP")
        return True


# =====================================================================
# REGISTRY — adicinar novas berries aqui
# =====================================================================
BERRY_REGISTRY = {
    "oranberry": OranBerry,
    "leppaberry": LeppaBerry,

    # ===== FUTURO =====
    # "cheri_berry":  CheriBerry,   # cura paralisia
    # "chesto_berry": ChestoBerry,  # cura sono
    # "pecha_berry":  PechaBerry,   # cura veneno
    # "rawst_berry":  RawstBerry,   # cura queimadura
    # "aspear_berry": AspearBerry,  # cura congelamento
    # "sitrus_berry": SitrusBerry,  # cura 25% HP
    # "lum_berry":    LumBerry,     # cura qualquer status
}


# =====================================================================
# PROCESSADOR
# =====================================================================
class HeldItemEffectProcessor:
    """
    Processa efeitos automáticos de itens segurados em todos os Pokémon
    em campo. Deve ser chamado 1x por frame pelo BattleSystem.
    """

    @classmethod
    def process_battle(cls, battle_system) -> None:
        """Itera aliados + selvagens e processa cada um."""
        if not battle_system or not battle_system.game_scene:
            return

        game_scene = battle_system.game_scene
        effect_manager = battle_system.effect_manager

        all_pokemon = []

        # Aliados em campo
        if hasattr(game_scene, 'placement_manager'):
            all_pokemon.extend(game_scene.placement_manager.placed_pokemon)

        # Inimigos selvagens
        if hasattr(game_scene, 'wave_manager'):
            all_pokemon.extend(game_scene.wave_manager.active_enemies)

        for pokemon in all_pokemon:
            cls.process_pokemon(pokemon, effect_manager, battle_system)

    @classmethod
    def process_pokemon(cls, pokemon, effect_manager, battle_system=None) -> None:
        """Processa o item segurado de um Pokémon individual."""
        if not pokemon:
            return

        # Não processa Pokémon derrotado/morto
        if getattr(pokemon, 'is_defeated', False):
            return
        if not pokemon.is_alive():
            return

        # Obtém o item segurado
        item_id = getattr(pokemon, 'held_item', None)
        if not item_id:
            return

        # Verifica se é uma berry registrada
        berry_class = BERRY_REGISTRY.get(item_id)
        if not berry_class:
            return  # Não é berry, ignora (outros sistemas tratam)

        berry = berry_class(item_id, pokemon.held_item_data)

        # Verifica condição de trigger
        if not berry.should_trigger(pokemon):
            return

        # Aplica o efeito
        if berry.apply(pokemon, effect_manager, battle_system):
            cls._consume_item(pokemon)

    @classmethod
    def _consume_item(cls, pokemon) -> None:
        """Remove o item segurado permanentemente após o consumo."""
        item_name = "Item"
        if pokemon.held_item_data:
            item_name = pokemon.held_item_data.get("name", pokemon.held_item)

        pokemon.held_item = None
        pokemon.held_item_data = None

        print(f"[BERRY] {pokemon.name} consumiu {item_name} permanentemente!")