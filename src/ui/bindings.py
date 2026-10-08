# src/ui/bindings.py
"""
Sistema de bindings {item.xxx} para templates de CardGrid.

Dentro de um `card_layout` (JSON), qualquer valor string pode conter
placeholders `{item.campo}` que são resolvidos em runtime pelo item.

Ex.:
    "text": "{item.title}"
    "fill_color": "{item.rarity_color}"
    "icon": "{item.card_surface}"       ← retorna Surface direto
"""
import re

_TOKEN = re.compile(r"\{item\.([a-zA-Z_][a-zA-Z0-9_]*)\}")


def resolve_value(value, item):
    """
    - Se `value` for EXATAMENTE 1 binding → retorna o valor cru
      (permite passar Surface, int, bool sem stringificar).
    - Se contiver bindings no meio → substitui como str.
    - Caso contrário retorna o valor original.
    """
    if not isinstance(value, str) or "{item." not in value:
        return value

    m_full = _TOKEN.fullmatch(value.strip())
    if m_full:
        return item.get(m_full.group(1))

    def _sub(m):
        v = item.get(m.group(1))
        return "" if v is None else str(v)

    return _TOKEN.sub(_sub, value)


def resolve_wdata(wdata, item):
    """
    Retorna uma CÓPIA rasa do wdata com todos os campos resolvidos.
    Não desce em listas (ex: card_layout) — só 1 nível.
    """
    out = {}
    for k, v in wdata.items():
        if isinstance(v, str):
            out[k] = resolve_value(v, item)
        elif isinstance(v, dict):
            out[k] = {kk: resolve_value(vv, item) for kk, vv in v.items()}
        else:
            out[k] = v
    return out