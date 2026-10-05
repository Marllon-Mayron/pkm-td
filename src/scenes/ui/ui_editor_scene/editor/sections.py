# src/scenes/ui_editor_scene/editor/sections.py
"""Definições de seções, tipos de campo e rótulos do editor."""

ANCHORS = ["tl", "tc", "tr", "cl", "c", "cr", "bl", "bc", "br"]
ALIGNS  = ["left", "center", "right"]

BG_IMAGE_MODES = ["stretch", "tile", "tile_h", "tile_v",
                  "center", "contain", "cover", "fit_w", "fit_h"]
ICON_POSITIONS = ["left", "right", "top", "center"]

# =====================================================================
# Tipos e rótulos de campo
# =====================================================================
FIELD_TYPES = {
    # identidade
    "id": "text", "z": "int", "tab": "text",
    "parent_id": "text",
    # posição
    "x": "float", "y": "float", "w": "float", "h": "float",
    "anchor": "choice",
    # estilo
    "style": "choice", "font_name": "choice",
    "font_size": "int", "align": "choice", "bold": "bool",
    # cores
    "text_color": "color", "fill_color": "color", "border_color": "color",
    # conteúdo
    "label": "text", "title": "text", "text": "text",
    "checked": "bool",
    "value": "float", "min": "float", "max": "float",
    "options": "list", "tabs": "list", "items": "list",
    "current_tab": "text",
    # ações
    "on_click": "action", "on_toggle": "action",
    "on_change": "action", "on_select": "action",
    # sons
    "click_sound": "sound", "hover_sound": "sound",
    "click_volume": "float", "hover_volume": "float",
    # imagem de fundo
    "bg_image": "image", "bg_image_mode": "choice",
    "bg_tint": "color", "bg_image_alpha": "int",
    # borda
    "border_width": "int", "border_radius": "int",
    "draw_border": "bool", "draw_shadow": "bool",
    # ícone
    "icon": "image", "icon_size": "int",
    "icon_position": "choice", "icon_gap": "int",
}

FIELD_LABELS = {
    "id": "ID", "z": "Z", "tab": "Aba", "parent_id": "Pai",
    "x": "X", "y": "Y", "w": "W", "h": "H", "anchor": "Ancora",
    "style": "Estilo", "font_name": "Fonte",
    "font_size": "Tam.", "align": "Alinhar", "bold": "Negrito",
    "text_color": "Texto", "fill_color": "Fundo", "border_color": "Borda",
    "label": "Rotulo", "title": "Titulo", "text": "Texto",
    "checked": "Marcado",
    "value": "Valor", "min": "Min", "max": "Max",
    "options": "Opcoes (|)", "tabs": "Abas (|)", "items": "Itens (|)",
    "current_tab": "Aba inicial",
    "on_click": "on_click", "on_toggle": "on_toggle",
    "on_change": "on_change", "on_select": "on_select",
    "click_sound": "Som click", "hover_sound": "Som hover",
    "click_volume": "Vol click", "hover_volume": "Vol hover",
    "bg_image": "Imagem", "bg_image_mode": "Modo",
    "bg_tint": "Tint", "bg_image_alpha": "Alpha",
    "border_width": "Espessura", "border_radius": "Raio",
    "draw_border": "Mostrar borda", "draw_shadow": "Sombra",
    "icon": "Icone", "icon_size": "Tam.", "icon_position": "Posicao",
    "icon_gap": "Gap",
}

# =====================================================================
# Seções reutilizáveis
# =====================================================================
IDENTITY = ("identity", "IDENTIDADE", ["id", "z", "tab", "parent_id"])
POSITION = ("position", "POSICAO",    ["x", "y", "w", "h", "anchor"])

STYLE_FULL = ("style", "ESTILO",
              ["style", "font_name", "font_size", "bold", "align"])
STYLE_TEXT = ("style", "ESTILO",
              ["font_name", "font_size", "bold", "align"])
STYLE_MIN  = ("style", "ESTILO",
              ["font_name", "bold", "font_size"])
STYLE_FONT = ("style", "ESTILO", ["font_name"])

COLORS_FULL  = ("colors", "CORES",
                ["text_color", "fill_color", "border_color"])
COLORS_LIGHT = ("colors", "CORES", ["fill_color", "border_color"])
COLOR_TEXT   = ("colors", "CORES", ["text_color"])

SOUNDS_FULL = ("sounds", "SONS",
               ["click_sound", "click_volume",
                "hover_sound", "hover_volume"])
SOUNDS_SOFT = ("sounds", "SONS", ["click_sound", "click_volume"])

IMAGE_SECTION  = ("image", "IMAGEM",
                  ["bg_image", "bg_image_mode",
                   "bg_tint", "bg_image_alpha"])
BORDER_SECTION = ("border", "BORDA",
                  ["border_width", "border_radius",
                   "draw_border", "draw_shadow"])
ICON_SECTION   = ("icon", "ICONE",
                  ["icon", "icon_size", "icon_position", "icon_gap"])


def sections_for_type(wtype):
    base = [IDENTITY, POSITION]

    if wtype == "button":
        extra = [STYLE_FULL, COLORS_FULL,
                 ("content", "CONTEUDO", ["label"]),
                 ("action", "ACAO", ["on_click"]),
                 ICON_SECTION, IMAGE_SECTION, BORDER_SECTION,
                 SOUNDS_FULL]
    elif wtype == "panel":
        extra = [STYLE_FONT, COLORS_FULL,
                 ("content", "CONTEUDO", ["title"]),
                 IMAGE_SECTION, BORDER_SECTION]
    elif wtype == "label":
        extra = [STYLE_TEXT, COLOR_TEXT,
                 ("content", "CONTEUDO", ["text"])]
    elif wtype == "list":
        extra = [STYLE_MIN, COLORS_FULL,
                 ("content", "ITENS", ["items"]),
                 ("action", "ACAO", ["on_select"]),
                 IMAGE_SECTION, BORDER_SECTION,
                 SOUNDS_FULL]
    elif wtype == "image":
        extra = [COLORS_LIGHT, IMAGE_SECTION, BORDER_SECTION]
    elif wtype == "checkbox":
        extra = [STYLE_MIN, COLORS_FULL,
                 ("content", "CONTEUDO", ["label", "checked"]),
                 ("action", "ACAO", ["on_toggle"]),
                 SOUNDS_FULL]
    elif wtype == "slider":
        extra = [STYLE_MIN, COLORS_LIGHT,
                 ("content", "VALORES", ["value", "min", "max"]),
                 ("action", "ACAO", ["on_change"]),
                 SOUNDS_SOFT]
    elif wtype == "dropdown":
        extra = [STYLE_MIN, COLORS_FULL,
                 ("content", "OPCOES", ["options", "value"]),
                 ("action", "ACAO", ["on_change"]),
                 SOUNDS_FULL]
    elif wtype == "tabpanel":
        extra = [STYLE_MIN, COLORS_FULL,
                 ("content", "ABAS", ["tabs", "current_tab"]),
                 ("action", "ACAO", ["on_change"]),
                 SOUNDS_FULL]
    else:
        extra = [STYLE_FULL, COLORS_FULL,
                 ("content", "CONTEUDO", ["label", "title", "text"]),
                 ("action", "ACAO", ["on_click"]),
                 IMAGE_SECTION, BORDER_SECTION,
                 SOUNDS_FULL]

    return base + extra


def default_open_state(wtype):
    """Sons/imagem/borda/ícone começam fechados."""
    closed = {"sounds", "image", "border", "icon"}
    return {sid: (sid not in closed) for sid, _, _ in sections_for_type(wtype)}