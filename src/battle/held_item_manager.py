# src/battle/held_item_manager.py

from typing import Optional, Dict, Any
from src.entities.pokemon import Pokemon


class HeldItemManager:
    """Gerencia os efeitos dos itens seguráveis durante a batalha"""

    @staticmethod
    def get_held_item_effect(pokemon: Pokemon) -> Optional[Dict[str, Any]]:
        """
        Retorna o efeito do item segurável do Pokémon.
        Se não tiver item ou não for um item com efeito de batalha, retorna None.
        """
        if not pokemon.held_item or not pokemon.held_item_data:
            return None

        item_data = pokemon.held_item_data
        effect = item_data.get("effect")
        effect_value = item_data.get("effect_value", {})

        # Verifica se é um item com efeito de batalha
        if effect == "held_item_boost":
            return {
                "type": "boost",
                "effect_value": effect_value,
                "item_name": item_data.get("name", "Item"),
                "description": item_data.get("description", "")
            }

        return None

    @staticmethod
    def apply_type_boost(attacker: Pokemon, move_type: str, damage: int) -> int:
        """
        Aplica bônus de tipo se o atacante estiver segurando um item que aumenta
        o poder de um tipo específico.
        """
        effect = HeldItemManager.get_held_item_effect(attacker)

        if not effect or effect.get("type") != "boost":
            return damage

        effect_value = effect.get("effect_value", {})
        type_boost = effect_value.get("type_boost", 1.0)

        # Verifica se o item aumenta o tipo do movimento
        # Os itens são específicos por tipo (ex: Charcoal para Fogo)
        type_mapping = {
            "charcoal": "fire",
            "mysticwater": "water",
            "magnet": "electric",
            "miracleseed": "grass",
            "nevermeltice": "ice",
            "sharpbeak": "flying",
            "poisonbarb": "poison",
            "softsand": "ground",
            "hardstone": "rock",
            "silverpowder": "bug",
            "spelltag": "ghost",
            "twistedspoon": "psychic",
            "blackbelt": "fighting",
            "silkscarf": "normal",
            "blackglasses": "dark",
            "metalcoat": "steel",
            "dragonfang": "dragon",
            "charcoal": "fire",
        }

        item_id = attacker.held_item
        boosted_type = type_mapping.get(item_id)

        if boosted_type and move_type.lower() == boosted_type:
            boosted_damage = int(damage * type_boost)
            print(f"[HELD_ITEM] {attacker.name} usou {item_id} - dano aumentado! {damage} -> {boosted_damage}")
            return boosted_damage

        return damage

    @staticmethod
    def get_item_boost_message(attacker: Pokemon, move_type: str) -> Optional[str]:
        """Retorna uma mensagem se o item do atacante está boostando o movimento"""
        effect = HeldItemManager.get_held_item_effect(attacker)
        if not effect:
            return None

        type_mapping = {
            "charcoal": "fire",
            "mysticwater": "water",
            "magnet": "electric",
            "miracleseed": "grass",
            "nevermeltice": "ice",
            "sharpbeak": "flying",
            "poisonbarb": "poison",
            "softsand": "ground",
            "hardstone": "rock",
            "silverpowder": "bug",
            "spelltag": "ghost",
            "twistedspoon": "psychic",
            "blackbelt": "fighting",
            "silkscarf": "normal",
            "blackglasses": "dark",
            "metalcoat": "steel",
            "dragonfang": "dragon",
        }

        item_id = attacker.held_item
        boosted_type = type_mapping.get(item_id)

        if boosted_type and move_type.lower() == boosted_type:
            effect_value = effect.get("effect_value", {})
            boost_percent = int((effect_value.get("type_boost", 1.0) - 1) * 100)
            return f"{attacker.held_item_data['name']} aumentou o poder!"

        return None