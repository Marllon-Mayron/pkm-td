# src/data/held_item_data.py

HELD_ITEM_TYPE_MAPPING = {
    # Inseto
    "silverpowder": "bug",
    # Fogo
    "charcoal": "fire",
    # Dragão
    "dragonfang": "dragon",
    # Pedra
    "hardstone": "rock",
    # Elétrico
    "magnet": "electric",
    # Aço
    "metalcoat": "steel",
    # Grama
    "miracleseed": "grass",
    # Água
    "mysticwater": "water",
    # Gelo
    "nevermeltice": "ice",
    # Veneno
    "poisonbarb": "poison",
    # Voador
    "sharpbeak": "flying",
    # Terrestre
    "softsand": "ground",
    # Normal
    "silkscarf": "normal",
    # Psíquico
    "twistedspoon": "psychic",
    # Lutador
    "blackbelt": "fighting",
    # Sombrio
    "blackglasses": "dark",
    # Fantasma
    "spelltag": "ghost",
}

def get_boosted_type(item_id: str) -> str:
    """Retorna o tipo boostado por um item segurável"""
    return HELD_ITEM_TYPE_MAPPING.get(item_id)

def is_type_boost_item(item_id: str) -> bool:
    """Verifica se um item é um boost de tipo"""
    return item_id in HELD_ITEM_TYPE_MAPPING