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
BORDER_STYLE_OPTIONS = ["solid", "dashed", "dotted", "none"]
DIVIDER_ORIENT_OPTIONS = ["horizontal", "vertical"]
DROP_DIR_OPTIONS = ["down", "up"]

SLOT_SHAPES = ["star", "circle", "square", "diamond", "triangle",
               "pentagon", "hexagon", "heart", "shield", "trophy",
               "medal", "none"]
SLOT_ORIENT_OPTIONS = ["horizontal", "vertical"]

TEXT_FIT_OPTIONS = ["none", "shrink", "wrap", "ellipsis", "shrink_wrap"]
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
    "tab_height": "int",
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
    # grid
    "cols": "int", "rows": "int", "cell_gap": "int",
    # list scroll
    "show_scrollbar": "bool", "scrollbar_width": "int",
    "scrollbar_color": "color", "scrollbar_bg": "color",
    "scrollbar_radius": "int",
    # divider
    "orientation": "choice", "thickness": "int",
    "radius": "int",
    # table
    "headers": "list", "rows_data": "text",
    "col_widths": "text",
    "row_height": "int", "header_height": "int",
    "cell_padding": "int",
    "header_bg": "color", "header_text_color": "color",
    "row_bg": "color", "row_bg_alt": "color",
    "grid_color": "color", "grid_width": "int",
    # dropdown
    "drop_dir": "choice",
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
    "border_style": "choice",
    "draw_border": "bool", "draw_shadow": "bool",
    "border_sides": "choice", "padding": "int",
    # ícone
    "icon": "image", "icon_size": "int",
    "icon_position": "choice", "icon_gap": "int",
    # progress
    "max_value": "float", "min_value": "float",
    "show_text": "bool", "text_format": "text",
    "color_low": "color", "color_mid": "color", "color_high": "color",
    "progress_bg": "color",
    # badge
    "badge_text_color": "color", "bg_color": "color",
    "badge_border_color": "color",
    # world sprite
    "world_x": "float", "world_y": "float", "max_size": "int",
    # slot row
    "max_slots": "int", "slot_size": "int", "shape": "choice",
    "outline_color": "color", "outline_width": "int",
    "filled_alpha": "int", "empty_alpha": "int",
    "icon_tint": "bool",

    "text_fit": "choice",
    "min_font_size": "int",
}

FIELD_LABELS = {
    "id": "ID", "z": "Z", "tab": "Aba", "parent_id": "Pai",
    "x": "X", "y": "Y", "w": "W", "h": "H", "anchor": "Ancora",
    "style": "Estilo", "font_name": "Fonte",
    "font_size": "Tam.", "align": "Alinhar", "bold": "Negrito",
    "title_font_size": "Tam. titulo",
    "tab_height": "Altura abas",
    "text_color": "Texto", "fill_color": "Fundo", "border_color": "Borda",
    "fill_alpha": "Alpha fundo", "border_alpha": "Alpha borda",
    "label": "Rotulo", "title": "Titulo", "text": "Texto",
    "checked": "Marcado",
    "value": "Valor", "min": "Min", "max": "Max",
    "options": "Opcoes (|)", "tabs": "Abas (|)", "items": "Itens (|)",
    "current_tab": "Aba inicial",
    "cols": "Colunas", "rows": "Linhas", "cell_gap": "Gap",
    "show_scrollbar": "Mostrar scrollbar", "scrollbar_width": "Largura sb",
    "scrollbar_color": "Cor sb", "scrollbar_bg": "Fundo sb",
    "scrollbar_radius": "Raio sb",
    "orientation": "Orientacao", "thickness": "Espessura",
    "headers": "Cabecalhos (|)", "rows_data": "Linhas (| com ; entre cols)",
    "col_widths": "Larguras cols (;)",
    "row_height": "Altura linha", "header_height": "Altura header",
    "cell_padding": "Padding celula",
    "header_bg": "Fundo header", "header_text_color": "Texto header",
    "row_bg": "Fundo linha par", "row_bg_alt": "Fundo linha impar",
    "grid_color": "Cor grid", "grid_width": "Largura grid",
    "drop_dir": "Direcao drop",
    "on_click": "on_click", "on_toggle": "on_toggle",
    "on_change": "on_change", "on_select": "on_select",
    "click_sound": "Som click", "hover_sound": "Som hover",
    "click_volume": "Vol click", "hover_volume": "Vol hover",
    "bg_image": "Imagem", "bg_image_mode": "Modo",
    "bg_tint": "Tint", "bg_image_alpha": "Alpha img",
    "pixel_art": "Pixel art",
    "border_width": "Espessura", "border_radius": "Raio",
    "border_style": "Estilo borda",
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
    "max_slots": "Total slots",
    "slot_size": "Tam. slot (auto)",
    "shape": "Forma",
    "outline_color": "Contorno",
    "outline_width": "Esp. contorno",
    "filled_alpha": "Alpha aceso",
    "empty_alpha": "Alpha apagado",
    "icon_tint": "Tint no icone",
    "text_fit": "Ajuste de texto",
    "min_font_size": "Tam. minimo",
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
                  ["border_width", "border_radius",
                   "border_style", "border_sides",
                   "draw_border", "draw_shadow"])
ICON_SECTION   = ("icon", "ICONE",
                  ["icon", "icon_size", "icon_position", "icon_gap"])


def sections_for_type(wtype):
    base = [IDENTITY, POSITION]

    if wtype == "button":
        extra = [STYLE_FULL, COLORS_FULL, ALPHA_SECTION,
                 ("content", "CONTEUDO", ["label", "text_fit", "min_font_size"]),
                 ("action", "ACAO", ["on_click"]),
                 ICON_SECTION, IMAGE_SECTION, BORDER_SECTION,
                 SOUNDS_FULL]
    elif wtype == "panel":
        extra = [STYLE_FONT, COLORS_FULL, ALPHA_SECTION,
                 ("content", "CONTEUDO", ["title", "title_font_size"]),
                 IMAGE_SECTION, BORDER_SECTION]
    elif wtype == "label":
        extra = [STYLE_TEXT, COLOR_TEXT, ALPHA_SECTION,
                 ("content", "CONTEUDO", ["text", "text_fit", "min_font_size"])]
    elif wtype == "list":
        extra = [STYLE_MIN, COLORS_FULL, ALPHA_SECTION,
                 ("content", "ITENS", ["items"]),
                 ("content", "SCROLLBAR",
                  ["show_scrollbar", "scrollbar_width", "scrollbar_radius",
                   "scrollbar_color", "scrollbar_bg"]),
                 ("action", "ACAO", ["on_select"]),
                 IMAGE_SECTION, BORDER_SECTION,
                 SOUNDS_FULL]
    elif wtype == "grid":
        extra = [STYLE_MIN, COLORS_FULL, ALPHA_SECTION,
                 ("content", "ITENS", ["items"]),
                 ("content", "GRID", ["cols", "rows", "cell_gap"]),
                 ("action", "ACAO", ["on_select"]),
                 BORDER_SECTION,
                 SOUNDS_FULL]
    elif wtype == "divider":
        extra = [("content", "LINHA",
                  ["orientation", "thickness", "padding", "radius"]),
                 ("colors", "CORES", ["color"]),
                 ("border", "ESTILO", ["border_style"])]
    elif wtype == "table":
        extra = [STYLE_MIN,
                 ("content", "DADOS",
                  ["headers", "rows_data", "col_widths"]),
                 ("content", "DIMENSOES",
                  ["row_height", "header_height", "cell_padding"]),
                 ("colors", "CORES",
                  ["header_bg", "header_text_color",
                   "row_bg", "row_bg_alt", "text_color"]),
                 ("colors", "GRID", ["grid_color", "grid_width"]),
                 BORDER_SECTION]
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
                 ("content", "OPCOES", ["options", "value", "drop_dir"]),
                 ("action", "ACAO", ["on_change"]),
                 BORDER_SECTION,
                 SOUNDS_FULL]
    elif wtype == "tabpanel":
        extra = [STYLE_MIN, COLORS_FULL, ALPHA_SECTION,
                 ("content", "ABAS",
                  ["tabs", "current_tab", "tab_height"]),
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
    elif wtype == "slot_row":
        extra = [
            ("content", "VALORES", ["value", "max_slots"]),
            ("content", "APARENCIA",
             ["shape", "orientation", "slot_size", "gap",
              "outline_width"]),
            ("colors", "CORES",
             ["color_filled", "color_empty", "outline_color"]),
            ("colors", "ALPHA",
             ["filled_alpha", "empty_alpha"]),
            ICON_SECTION,
        ]
    else:
        extra = [STYLE_FULL, COLORS_FULL, ALPHA_SECTION,
                 ("content", "CONTEUDO", ["label", "title", "text"]),
                 ("action", "ACAO", ["on_click"]),
                 IMAGE_SECTION, BORDER_SECTION,
                 SOUNDS_FULL]

    return base + extra


def default_open_state(wtype):
    closed = {"sounds", "image", "border", "icon", "alpha", "scrollbar",
              "grid"}
    return {sid: (sid not in closed) for sid, _, _ in sections_for_type(wtype)}