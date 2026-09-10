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


# =========================================================
# Compatibilidade: label -> chave
# =========================================================
_LABEL_TO_KEY = {v: k for k, v in CAPTURE_METHOD_LABELS.items()}


def _label_to_key(label_or_key: str) -> str:
    """
    Converte um label legível de volta para a chave interna.
    Se já for uma chave, retorna ela mesma.
    Se não reconhecer, retorna 'unknown'.
    """
    if not label_or_key:
        return "unknown"
    if label_or_key in CAPTURE_METHOD_LABELS:
        return label_or_key
    if label_or_key in _LABEL_TO_KEY:
        return _LABEL_TO_KEY[label_or_key]
    return "unknown"


# =========================================================
# Separador de histórico de troca
# =========================================================

# Marcador que separa a origem original do histórico de trocas
TRADE_HISTORY_SEPARATOR = " | "


# =========================================================
# Helpers de exibição
# =========================================================

def _extract_base(origin: str) -> str:
    """
    Extrai a parte base (origem original) de uma string de origem.
    Se for concatenada, retorna apenas o primeiro segmento.
    """
    if not origin:
        return ""
    if TRADE_HISTORY_SEPARATOR in origin:
        return origin.split(TRADE_HISTORY_SEPARATOR)[0].strip()
    return origin.strip()


def get_capture_label(method: str) -> str:
    """
    Retorna o label amigável de um capture_method.
    Suporta tanto chaves quanto labels (compatibilidade) e strings
    concatenadas (com histórico de troca).
    """
    if not method:
        return CAPTURE_METHOD_LABELS["unknown"]

    base = _extract_base(method)

    # Se for uma chave conhecida, retorna o label
    if base in CAPTURE_METHOD_LABELS:
        return CAPTURE_METHOD_LABELS[base]

    # Se já for um label conhecido, retorna ele mesmo
    if base in _LABEL_TO_KEY:
        return base

    # Desconhecido: retorna o que veio
    return base or CAPTURE_METHOD_LABELS["unknown"]


def get_capture_color(method: str) -> tuple:
    """
    Retorna a cor associada a um capture_method.
    Suporta tanto chaves quanto labels (compatibilidade) e strings
    concatenadas (com histórico de troca).
    """
    if not method:
        return CAPTURE_METHOD_COLORS["unknown"]

    base = _extract_base(method)

    # Tenta direto como chave
    if base in CAPTURE_METHOD_COLORS:
        return CAPTURE_METHOD_COLORS[base]

    # Tenta converter label -> chave
    key = _label_to_key(base)
    return CAPTURE_METHOD_COLORS.get(key, CAPTURE_METHOD_COLORS["unknown"])


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

def build_trade_origin(
    original_method: str,
    original_origin_extra: str,
    traded_at: datetime,
    other_player_name: str,
    other_player_id: str,
) -> str:
    """
    Constrói a string de origem concatenada para uma troca.

    IMPORTANTE: armazena a CHAVE interna (ex: "starter",
    "capture_pokeball"), NÃO o label. Isso preserva a informação
    para que get_capture_color() e get_capture_label() funcionem
    corretamente em qualquer ponto.

    Formato final:
        "starter | Trocado em 12/03/2025 14:30 com Ash (ID: abc12345)"
        "capture_pokeball | Trocado em ... | Trocado em ..."  (múltiplas trocas)

    Args:
        original_method: capture_method original (chave OU label, será
                         normalizado para chave se possível)
        original_origin_extra: string já concatenada (se houver trocas
                               anteriores); se preenchida, é usada como base
        traded_at: datetime da troca
        other_player_name: nome do outro jogador
        other_player_id: id único do outro jogador (curto)

    Returns:
        Nova string de origem concatenada
    """
    # Se já tem histórico, preserva a string existente como base
    if original_origin_extra:
        base = original_origin_extra
    else:
        # Normaliza para chave (aceita chave OU label como entrada)
        if original_method in CAPTURE_METHOD_LABELS:
            base = original_method  # já é chave
        elif original_method in _LABEL_TO_KEY:
            base = _LABEL_TO_KEY[original_method]  # converte label -> chave
        else:
            base = "unknown"

    date_str = traded_at.strftime("%d/%m/%Y %H:%M")
    trade_entry = (
        f"Trocado em {date_str} com {other_player_name} "
        f"(ID: {other_player_id})"
    )

    return f"{base}{TRADE_HISTORY_SEPARATOR}{trade_entry}"


def split_origin_for_display(origin: str, max_chars: int = 55) -> list:
    """
    Quebra a string de origem em linhas para exibição no modal.

    Regras:
      - Se não houver separador ' | ', retorna [label] (1 linha).
      - Se houver, divide pelo separador e agrupa em linhas que caibam
        em max_chars.
      - A primeira parte (origem original) é convertida para label.
      - As partes seguintes (trocas) já são texto descritivo e mantidas.

    Args:
        origin: string de origem (chave, label ou concatenada)
        max_chars: número máximo de caracteres por linha

    Returns:
        Lista de strings (linhas)
    """
    if not origin:
        return ["Desconhecido"]

    # Origem simples: converte chave -> label para exibição
    if TRADE_HISTORY_SEPARATOR not in origin:
        return [get_capture_label(origin)]

    parts = origin.split(TRADE_HISTORY_SEPARATOR)
    lines = []
    current = ""

    for i, part in enumerate(parts):
        part = part.strip()
        if not part:
            continue

        # A primeira parte é a origem original -> converte para label
        # As demais partes já são texto descritivo ("Trocado em ...")
        if i == 0:
            display_part = get_capture_label(part)
        else:
            display_part = part

        candidate = (
            f"{current}{TRADE_HISTORY_SEPARATOR}{display_part}"
            if current else display_part
        )
        if len(candidate) <= max_chars:
            current = candidate
        else:
            if current:
                lines.append(current)
            current = display_part

    if current:
        lines.append(current)

    return lines or [origin]


def is_traded(origin: str) -> bool:
    """Verifica se a origem contém histórico de troca."""
    return bool(origin) and TRADE_HISTORY_SEPARATOR in origin