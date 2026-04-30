# src/data/mystery_gift_data.py

"""
Dados dos códigos Mystery Gift
Cada código pode ser resgatado apenas uma vez por save
Suporte para invalidação de códigos (eventos passados)
"""

# Estrutura dos códigos disponíveis
MYSTERY_GIFT_CODES = {
    "IJOHUFFZ": {
        "pokemon_id": 133,
        "pokemon_name": "Eevee",
        "description": "Eevee Especial Brilhante!",
        "is_shiny": True,
        "invalid": True,
        "event_name": "Lançamento do sistema de MYSTERY GIFT",
        "event_date": "2026-04-23"
    },
    "T2V8JUSX": {
        "pokemon_id": 137,
        "pokemon_name": "Porygon",
        "description": "Porygon, o pokémon artificial",
        "is_shiny": False,
        "invalid": False,
        "event_name": "Pokémon Secreto",
        "event_date": "2026-04-30"
    }
}


def get_code_info(code):
    """Retorna informações do código ou None se inválido/não existe"""
    code_info = MYSTERY_GIFT_CODES.get(code.upper())
    if code_info:
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