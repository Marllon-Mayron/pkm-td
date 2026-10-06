# src/scenes/ui_editor_scene/editor/sections.py
"""Definições de seções, tipos de campo e rótulos do editor."""

ANCHORS = ["tl", "tc", "tr", "cl", "c", "cr", "bl", "bc", "br"]
ALIGNS  = ["left", "center", "right"]

BG_IMAGE_MODES = ["stretch", "tile", "tile_h", "tile_v",
                  "center", "contain", "cover", "fit_w", "fit_h"]
ICON_POSITIONS = ["left", "right", "top", "center"]
BORDER_SIDE_OPTIONS = [
    "all", "none",
    "top", "bottom", "left", "right",
    "top,bottom", "left,right",
    "top,left", "top,right",
    "bottom,left", "bottom,right",
]

# =====================================================================
# Tipos e rótulos de campo
# =====================================================================
FIELD_TYPES = {
    # identidade
    "id": "text", "z": "int", "tab": "text", "parent_id": "text",
    # posição
    "x": "float", "y": "float", "w": "float", "h": "float",
    "anchor": "choice",
    # estilo
    "style": "choice", "font_name": "choice",
    "font_size": "int", "align": "choice", "bold": "bool",
    "title_font_size": "int",
    # cores
    "text_color": "color", "fill_color": "color", "border_color": "color",
    # alpha
    "fill_alpha": "int", "border_alpha": "int",
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
    "pixel_art": "bool",
    # borda
    "border_width": "int", "border_radius": "int",
    "draw_border": "bool", "draw_shadow": "bool",
    "border_sides": "choice", "padding": "int",
    # ícone
    "icon": "image", "icon_size": "int",
    "icon_position": "choice", "icon_gap": "int",
    # progress
    "max_value": "float", "min_value": "float",
    "show_text": "bool", "text_format": "text",
    "color_low": "color", "color_mid": "color", "color_high": "color",
    "progress_bg": "color", "radius": "int",
    # badge
    "badge_text_color": "color", "bg_color": "color",
    "badge_border_color": "color",
    # world sprite
    "world_x": "float", "world_y": "float", "max_size": "int",
}

FIELD_LABELS = {
    "id": "ID", "z": "Z", "tab": "Aba", "parent_id": "Pai",
    "x": "X", "y": "Y", "w": "W", "h": "H", "anchor": "Ancora",
    "style": "Estilo", "font_name": "Fonte",
    "font_size": "Tam.", "align": "Alinhar", "bold": "Negrito",
    "title_font_size": "Tam. titulo",
    "text_color": "Texto", "fill_color": "Fundo", "border_color": "Borda",
    "fill_alpha": "Alpha fundo", "border_alpha": "Alpha borda",
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
    "bg_tint": "Tint", "bg_image_alpha": "Alpha img",
    "pixel_art": "Pixel art",
    "border_width": "Espessura", "border_radius": "Raio",
    "draw_border": "Mostrar borda", "draw_shadow": "Sombra",
    "border_sides": "Lados", "padding": "Padding",
    "icon": "Icone", "icon_size": "Tam.", "icon_position": "Posicao",
    "icon_gap": "Gap",
    "max_value": "Max valor", "min_value": "Min valor",
    "show_text": "Mostrar texto", "text_format": "Formato",
    "color_low": "Cor baixa", "color_mid": "Cor media",
    "color_high": "Cor alta", "progress_bg": "Fundo", "radius": "Raio",
    "badge_text_color": "Texto badge", "bg_color": "Fundo badge",
    "badge_border_color": "Borda badge",
    "world_x": "World X", "world_y": "World Y", "max_size": "Tam. max",
}

# =====================================================================
# Seções reutilizáveis
# =====================================================================
IDENTITY = ("identity", "IDENTIDADE", ["id", "z", "tab", "parent_id"])
POSITION = ("position", "POSICAO",    ["x", "y", "w", "h", "anchor", "padding"])

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

ALPHA_SECTION = ("alpha", "ALPHA", ["fill_alpha", "border_alpha"])

SOUNDS_FULL = ("sounds", "SONS",
               ["click_sound", "click_volume",
                "hover_sound", "hover_volume"])
SOUNDS_SOFT = ("sounds", "SONS", ["click_sound", "click_volume"])

IMAGE_SECTION  = ("image", "IMAGEM",
                  ["bg_image", "bg_image_mode",
                   "bg_tint", "bg_image_alpha", "pixel_art"])
BORDER_SECTION = ("border", "BORDA",
                  ["border_width", "border_radius", "border_sides",
                   "draw_border", "draw_shadow"])
ICON_SECTION   = ("icon", "ICONE",
                  ["icon", "icon_size", "icon_position", "icon_gap"])


def sections_for_type(wtype):
    base = [IDENTITY, POSITION]

    if wtype == "button":
        extra = [STYLE_FULL, COLORS_FULL, ALPHA_SECTION,
                 ("content", "CONTEUDO", ["label"]),
                 ("action", "ACAO", ["on_click"]),
                 ICON_SECTION, IMAGE_SECTION, BORDER_SECTION,
                 SOUNDS_FULL]
    elif wtype == "panel":
        extra = [STYLE_FONT, COLORS_FULL, ALPHA_SECTION,
                 ("content", "CONTEUDO", ["title", "title_font_size"]),
                 IMAGE_SECTION, BORDER_SECTION]
    elif wtype == "label":
        extra = [STYLE_TEXT, COLOR_TEXT, ALPHA_SECTION,
                 ("content", "CONTEUDO", ["text"])]
    elif wtype == "list":
        extra = [STYLE_MIN, COLORS_FULL, ALPHA_SECTION,
                 ("content", "ITENS", ["items"]),
                 ("action", "ACAO", ["on_select"]),
                 IMAGE_SECTION, BORDER_SECTION,
                 SOUNDS_FULL]
    elif wtype == "image":
        extra = [COLORS_LIGHT, ALPHA_SECTION,
                 IMAGE_SECTION, BORDER_SECTION]
    elif wtype == "world_sprite":
        extra = [ICON_SECTION,
                 ("image", "IMAGEM", ["pixel_art"]),
                 ("content", "POSICAO MUNDO", ["world_x", "world_y"]),
                 ("content", "TAMANHO", ["max_size"])]
    elif wtype == "checkbox":
        extra = [STYLE_MIN, COLORS_FULL, ALPHA_SECTION,
                 ("content", "CONTEUDO", ["label", "checked"]),
                 ("action", "ACAO", ["on_toggle"]),
                 SOUNDS_FULL]
    elif wtype == "slider":
        extra = [STYLE_MIN, COLORS_LIGHT, ALPHA_SECTION,
                 ("content", "VALORES", ["value", "min", "max"]),
                 ("action", "ACAO", ["on_change"]),
                 SOUNDS_SOFT]
    elif wtype == "dropdown":
        extra = [STYLE_MIN, COLORS_FULL, ALPHA_SECTION,
                 ("content", "OPCOES", ["options", "value"]),
                 ("action", "ACAO", ["on_change"]),
                 SOUNDS_FULL]
    elif wtype == "tabpanel":
        extra = [STYLE_MIN, COLORS_FULL, ALPHA_SECTION,
                 ("content", "ABAS", ["tabs", "current_tab"]),
                 ("action", "ACAO", ["on_change"]),
                 SOUNDS_FULL]
    elif wtype == "progress":
        extra = [("content", "VALORES",
                  ["value", "max_value", "min_value",
                   "show_text", "text_format"]),
                 ("colors", "CORES",
                  ["progress_bg", "color_low", "color_mid", "color_high",
                   "border_color"]),
                 ("border", "BORDA",
                  ["border_width", "border_radius", "radius",
                   "draw_border", "draw_shadow"]),
                 STYLE_MIN]
    elif wtype == "badge":
        extra = [("content", "CONTEUDO",
                  ["text", "badge_text_color", "bg_color",
                   "badge_border_color"]),
                 STYLE_MIN]
    else:
        extra = [STYLE_FULL, COLORS_FULL, ALPHA_SECTION,
                 ("content", "CONTEUDO", ["label", "title", "text"]),
                 ("action", "ACAO", ["on_click"]),
                 IMAGE_SECTION, BORDER_SECTION,
                 SOUNDS_FULL]

    return base + extra


def default_open_state(wtype):
    """Sons/imagem/borda/ícone/alpha começam fechados."""
    closed = {"sounds", "image", "border", "icon", "alpha"}
    return {sid: (sid not in closed) for sid, _, _ in sections_for_type(wtype)}