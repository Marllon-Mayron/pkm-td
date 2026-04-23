# src/data/mystery_gift_data.py

"""
Dados dos códigos Mystery Gift
Cada código pode ser resgatado apenas uma vez por save
Suporte para invalidação de códigos (eventos passados)
"""

# Estrutura dos códigos disponíveis
# Formato: "CODIGO": {"pokemon_id": int, "pokemon_name": str, "description": str, "invalid": bool}
MYSTERY_GIFT_CODES = {
    "TESTE123": {
        "pokemon_id": 1,  # Bulbasaur
        "pokemon_name": "Bulbasaur",
        "description": "Pokémon Inicial Especial!",
        "is_shiny": True,
        "invalid": False,  # False = disponível, True = evento encerrado
        "event_name": "Lançamento do sistema de MYSTERY GIFT",
        "event_date": "2025-04-23"
    },
    "TESTE321": {
        "pokemon_id": 4,  # Charmander
        "pokemon_name": "Charmander",
        "description": "Lançamento do sistema de MYSTERY GIFT",
        "is_shiny": True,
        "invalid": False,
        "event_name": "Lançamento do sistema de MYSTERY GIFT",
        "event_date": "2025-04-23"
    }
}


def get_code_info(code):
    """Retorna informações do código ou None se inválido/não existe"""
    code_info = MYSTERY_GIFT_CODES.get(code.upper())

    if code_info:
        # Retorna uma cópia para não modificar o original
        return code_info.copy()
    return None


def is_valid_code(code):
    """Verifica se o código existe e NÃO está inválido"""
    code_info = MYSTERY_GIFT_CODES.get(code.upper())
    if not code_info:
        return False
    return not code_info.get("invalid", False)


def is_code_invalid(code):
    """Verifica se o código existe mas está marcado como inválido"""
    code_info = MYSTERY_GIFT_CODES.get(code.upper())
    if not code_info:
        return False
    return code_info.get("invalid", False)


def get_all_codes():
    """Retorna todos os códigos disponíveis (incluindo inválidos)"""
    return list(MYSTERY_GIFT_CODES.keys())


def get_valid_codes():
    """Retorna apenas códigos válidos (não inválidos)"""
    return [code for code, info in MYSTERY_GIFT_CODES.items() if not info.get("invalid", False)]


def get_invalid_codes():
    """Retorna códigos inválidos (eventos encerrados)"""
    return [code for code, info in MYSTERY_GIFT_CODES.items() if info.get("invalid", False)]