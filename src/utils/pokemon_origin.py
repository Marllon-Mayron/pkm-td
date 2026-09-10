# src/utils/pokemon_origin.py

"""
Helper centralizado para origem de Pokémon.

Padroniza:
  - Labels de capture_method (exibição)
  - Cores por método
  - Concatenação de origem em trocas (histórico preservado)
"""

from datetime import datetime


# =========================================================
# Labels e cores por método de captura
# =========================================================
CAPTURE_METHOD_LABELS = {
    "starter":                "Inicial",
    "capture":                "Captura",
    "capture_pokeball":       "Pokébola",
    "capture_greatball":      "Great Ball",
    "capture_ultraball":      "Ultra Ball",
    "capture_masterball":     "Master Ball",
    "capture_friendball":     "Friend Ball",
    "gift":                   "Presente",
    "trade":                  "Troca",
    "fossil":                 "Fóssil",
    "evolution":              "Evolução",
    "egg":                    "Ovo",
    "event":                  "Mystery Gift",
    "migration":              "Migração",
    "unknown":                "Desconhecido",
}

CAPTURE_METHOD_COLORS = {
    "starter":            (255, 215, 0),
    "capture":            (100, 255, 100),
    "capture_pokeball":   (200, 200, 200),
    "capture_greatball":  (100, 150, 255),
    "capture_ultraball":  (255, 200, 100),
    "capture_masterball": (255, 100, 100),
    "capture_friendball": (255, 150, 255),
    "gift":               (255, 200, 0),
    "trade":              (100, 200, 255),
    "fossil":             (200, 180, 100),
    "evolution":          (100, 200, 255),
    "egg":                (255, 180, 200),
    "event":              (255, 100, 200),
    "migration":          (150, 150, 150),
    "unknown":            (150, 150, 150),
}


def get_capture_label(method: str) -> str:
    """Retorna o label amigável de um capture_method."""
    if not method:
        return CAPTURE_METHOD_LABELS["unknown"]
    # Se for um método concatenado (contém " | "), trata separadamente
    return CAPTURE_METHOD_LABELS.get(method, method)


def get_capture_color(method: str) -> tuple:
    """Retorna a cor associada a um capture_method."""
    if not method:
        return CAPTURE_METHOD_COLORS["unknown"]
    return CAPTURE_METHOD_COLORS.get(method, CAPTURE_METHOD_COLORS["unknown"])


def format_capture_date(capture_date: str) -> str:
    """Formata a data de captura (ISO) para exibição."""
    if not capture_date:
        return "Data desconhecida"
    try:
        dt = datetime.fromisoformat(capture_date)
        return dt.strftime("%d/%m/%Y %H:%M")
    except Exception:
        return capture_date[:16] if len(capture_date) > 16 else capture_date


# =========================================================
# Concatenação de origem (para Trade)
# =========================================================

# Marcador que separa a origem original do histórico de trocas
TRADE_HISTORY_SEPARATOR = " | "


def build_trade_origin(
    original_method: str,
    original_origin_extra: str,
    traded_at: datetime,
    other_player_name: str,
    other_player_id: str,
) -> str:
    """
    Constrói a string de origem concatenada para uma troca.

    Formato final:
        "capture_pokeball | Trocado em 12/03/2025 14:30 com Ash (ID: abc123)"

    Args:
        original_method: capture_method original do Pokémon
        original_origin_extra: texto extra já concatenado (se houver trocas anteriores)
        traded_at: datetime da troca
        other_player_name: nome do outro jogador
        other_player_id: id único do outro jogador

    Returns:
        Nova string de origem concatenada
    """
    # Pega o label legível do método original
    original_label = get_capture_label(original_method)

    # Base: se já tem histórico, preserva; senão, começa com o label
    if original_origin_extra:
        # Já tem histórico — só concatena a nova troca
        base = original_origin_extra
    else:
        base = original_label

    date_str = traded_at.strftime("%d/%m/%Y %H:%M")
    trade_entry = f"Trocado em {date_str} com {other_player_name} (ID: {other_player_id})"

    return f"{base}{TRADE_HISTORY_SEPARATOR}{trade_entry}"


def split_origin_for_display(origin: str, max_chars: int = 55) -> list:
    """
    Quebra a string de origem em linhas para exibição no modal.

    Regras:
      - Se não houver separador ' | ', retorna [origem] (1 linha).
      - Se houver, divide pelo separador e agrupa em linhas que caibam em max_chars.

    Args:
        origin: string de origem (capture_method ou concatenada)
        max_chars: número máximo de caracteres por linha

    Returns:
        Lista de strings (linhas)
    """
    if not origin:
        return ["Desconhecido"]

    if TRADE_HISTORY_SEPARATOR not in origin:
        return [origin]

    parts = origin.split(TRADE_HISTORY_SEPARATOR)
    lines = []
    current = ""

    for part in parts:
        part = part.strip()
        if not part:
            continue

        # Se o current + part couber, junta
        candidate = f"{current}{TRADE_HISTORY_SEPARATOR}{part}" if current else part
        if len(candidate) <= max_chars:
            current = candidate
        else:
            if current:
                lines.append(current)
            current = part

    if current:
        lines.append(current)

    return lines or [origin]


def is_traded(origin: str) -> bool:
    """Verifica se a origem contém histórico de troca."""
    return bool(origin) and TRADE_HISTORY_SEPARATOR in origin