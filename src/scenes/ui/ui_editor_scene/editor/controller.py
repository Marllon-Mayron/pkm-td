# src/scenes/ui_editor_scene/editor/controller.py
"""EditorController — orquestra estado, eventos e ciclo de vida."""
import copy
import json
import pygame
from pathlib import Path

from src.scenes.base_scene import BaseScene
from src.ui.theme import Palette, FontBook, BUTTON_STYLES, parse_color, to_hex
from src.ui.layout import rel_rect
from src.ui.screen_loader import ScreenLoader
from src.ui.color_picker import ColorPicker
from src.ui.sound_helper import available_sound_names
from src.config.paths import UI_LAYOUTS_PATH, SCENES_EDITOR_PATH
from src.managers.sounds.sound_manager import sound_manager, SoundEffect

from src.scenes.ui.ui_editor_scene.editor.fields import (
    TextField, ColorField, BoolField, EditorDropdown, ImageField)
from src.scenes.ui.ui_editor_scene.editor.modals import LoadPicker, ImagePicker
from src.scenes.ui.ui_editor_scene.editor.guides import compute_guides_and_snap
from src.scenes.ui.ui_editor_scene.editor import sections as S
from src.scenes.ui.ui_editor_scene.editor.render_mixin import EditorRenderMixin


DESIGN_W, DESIGN_H = 1280, 720
LAYOUTS_DIR = UI_LAYOUTS_PATH
SCENES_DIR = SCENES_EDITOR_PATH
SNAP_THRESHOLD = 6


class EditorController(EditorRenderMixin, BaseScene):
    TOP_H, BOT_H = 56, 26
    ROW_H = 30
    SECTION_H = 26
    SPLITTER_W = 6
    MIN_LEFT = 180
    MIN_RIGHT = 280
    MIN_CANVAS = 260

    ADD_TYPES = [
        ("button",       "Botão",    "primary"),
        ("panel",        "Painel",   "gold"),
        ("label",        "Texto",    "ghost"),
        ("list",         "Lista",    "primary"),
        ("image",        "Imagem",   "success"),
        ("checkbox",     "Checkbox", "success"),
        ("slider",       "Slider",   "gold"),
        ("dropdown",     "Dropdown", "primary"),
        ("tabpanel",     "Abas",     "ghost"),
        ("progress",     "Barra",    "success"),
        ("badge",        "Badge",    "gold"),
        ("world_sprite", "Sprite3D", "primary"),
    ]

    # =================================================================
    def __init__(self, game):
        super().__init__(game)
        self.layout_name = "novo_layout"
        self.widgets_data = []
        self.selected_indices = set()
        self.selected_idx = -1
        self._selected_type = None

        self.dragging = False
        self.resizing = False
        self.drag_offset = (0, 0)
        self.drag_start_rect = None
        self._drag_rects = {}

        self._active_guides_v = []
        self._active_guides_h = []
        self._strong_guides_v = set()
        self._strong_guides_h = set()

        self._marquee = None
        self._marquee_start_screen = None

        self.show_grid = True
        self.status_text = "Pronto."

        self.preview_mode = False
        self._runtime_widgets = []
        self._runtime_dirty = True
        self.preview_active_tab = None

        self.left_w = 240
        self.right_w = 360
        self._dragging_splitter = None
        self._split_drag_start_x = 0
        self._split_start_w = 0
        self._hover_splitter = None

        self.right_scroll = 0
        self.right_max_scroll = 0

        self._last_size = (0, 0)
        self.design_surface = pygame.Surface((DESIGN_W, DESIGN_H))
        self._fonts = {}

        self.top_rect = None
        self.left_rect = None
        self.right_rect = None
        self.canvas_rect = None
        self.split_l_rect = None
        self.split_r_rect = None
        self._right_clip_rect = pygame.Rect(0, 0, 0, 0)
        self._right_header_rect = pygame.Rect(0, 0, 0, 0)
        self._right_footer_rect = pygame.Rect(0, 0, 0, 0)
        self._apply_btn_rect = pygame.Rect(0, 0, 0, 0)
        self._design_draw_rect = pygame.Rect(0, 0, 1, 1)
        self._canvas_scale = 1.0

        self.name_field = None
        self.fields = {}
        self.dropdowns = {}
        self.sections_open = {}

        self._top_btn_rects = {}
        self._section_header_rects = {}
        self._left_tool_rects = []
        self._left_action_rects = []

        self.color_picker = ColorPicker()
        self.load_picker = LoadPicker()
        self.image_picker = ImagePicker()
        self._color_target_key = None
        self._image_target_key = None

        self._editing_tab = None
        self._tab_dd = None
        self._tab_dd_rect = pygame.Rect(0, 0, 0, 0)
        self._tab_map = {}

        try:
            self._sound_names = available_sound_names()
        except Exception:
            self._sound_names = ["(nenhum)", "CLICK", "SHINY"]

        self._bg_image_modes = S.BG_IMAGE_MODES
        self._icon_positions = S.ICON_POSITIONS
        self._border_sides_choices = S.BORDER_SIDE_OPTIONS

        self._layout()
        self._new_layout()

    # =================================================================
    def _font(self, size, bold=False):
        key = (int(size), bool(bold))
        if key not in self._fonts:
            self._fonts[key] = FontBook.get(size, bold)
        return self._fonts[key]

    def _mark_dirty(self):
        self._runtime_dirty = True

    def _any_field_focused(self):
        if self.name_field and self.name_field.focused:
            return True
        for f in self.fields.values():
            if getattr(f, "focused", False):
                return True
        return False

    def _focused_field(self):
        for k, f in self.fields.items():
            if getattr(f, "focused", False):
                return "field", k, f
        if self.name_field and self.name_field.focused:
            return "name", None, self.name_field
        return None, None, None

    def _set_field_focus(self, f, focused):
        focused = bool(focused)
        inner = getattr(f, "field", None)
        if inner is not None and hasattr(inner, "focused"):
            try:
                inner.focused = focused
            except Exception:
                pass
            return
        try:
            f.focused = focused
        except Exception:
            pass

    def _clear_field_focus(self):
        if self.name_field:
            try:
                self.name_field.focused = False
            except Exception:
                pass
        for f in self.fields.values():
            self._set_field_focus(f, False)

    def _flush_current_edits(self):
        if 0 <= self.selected_idx < len(self.widgets_data):
            try:
                self._apply_fields()
            except Exception as e:
                print(f"[UI Editor] flush: {e}")

    # =================================================================
    # ÁRVORE
    # =================================================================
    def _get_widget_by_id(self, wid):
        if not wid:
            return None
        for w in self.widgets_data:
            if w.get("id") == wid:
                return w
        return None

    def _index_of_id(self, wid):
        if not wid:
            return -1
        for i, w in enumerate(self.widgets_data):
            if w.get("id") == wid:
                return i
        return -1

    def _get_children_of(self, wid):
        if not wid:
            return []
        return [w for w in self.widgets_data if w.get("parent_id") == wid]

    def _get_descendants_of(self, wid):
        out = []
        stack = list(self._get_children_of(wid))
        while stack:
            c = stack.pop()
            out.append(c)
            stack.extend(self._get_children_of(c.get("id")))
        return out

    def _get_depth(self, wdata):
        d = 0
        p = wdata.get("parent_id")
        while p:
            d += 1
            parent = self._get_widget_by_id(p)
            if not parent:
                break
            p = parent.get("parent_id")
        return d

    def _is_descendant_of(self, wdata, ancestor_id):
        if not ancestor_id:
            return False
        p = wdata.get("parent_id")
        seen = 0
        while p and seen < 64:
            if p == ancestor_id:
                return True
            parent = self._get_widget_by_id(p)
            if not parent:
                return False
            p = parent.get("parent_id")
            seen += 1
        return False

    def _get_parent_content_rect(self, wdata):
        parent_id = wdata.get("parent_id")
        if not parent_id:
            return self._design_vp()
        parent = self._get_widget_by_id(parent_id)
        if not parent:
            return self._design_vp()
        return self._get_content_rect(parent)

    def _get_content_rect(self, wdata):
        r = self._design_rect(wdata)
        wtype = wdata.get("type")
        props = wdata.get("props", {}) or {}

        if wtype == "tabpanel":
            tabs = props.get("tabs", [])
            if tabs:
                tab_h = max(28, int(r.height * 0.12))
                base = pygame.Rect(r.x, r.y + tab_h,
                                   r.width, r.height - tab_h)
            else:
                base = r
        else:
            base = r

        # Aplica padding
        try:
            pad = int(float(wdata.get("padding", props.get("padding", 0)) or 0))
        except (TypeError, ValueError):
            pad = 0
        if pad > 0:
            base = base.inflate(-pad * 2, -pad * 2)
        return base

    def _has_selected_ancestor(self, idx):
        if not (0 <= idx < len(self.widgets_data)):
            return False
        w = self.widgets_data[idx]
        p = w.get("parent_id")
        seen = 0
        while p and seen < 64:
            pidx = self._index_of_id(p)
            if pidx in self.selected_indices:
                return True
            parent = self.widgets_data[pidx] if pidx >= 0 else None
            p = parent.get("parent_id") if parent else None
            seen += 1
        return False

    def _top_level_selection(self):
        return {i for i in self.selected_indices
                if not self._has_selected_ancestor(i)}

    # =================================================================
    # SELEÇÃO
    # =================================================================
    def _select_only(self, idx):
        self.selected_indices = {idx} if idx >= 0 else set()
        self.selected_idx = idx
        self._selected_type = None
        self.right_scroll = 0

    def _select_toggle(self, idx):
        if idx < 0:
            return
        if idx in self.selected_indices:
            self.selected_indices.discard(idx)
            if self.selected_idx == idx:
                self.selected_idx = next(iter(self.selected_indices), -1)
        else:
            self.selected_indices.add(idx)
            self.selected_idx = idx
        self._selected_type = None

    def _select_clear(self):
        self.selected_indices.clear()
        self.selected_idx = -1
        self._selected_type = None
        self.right_scroll = 0

    # =================================================================
    # ABAS
    # =================================================================
    def _get_all_tabs(self):
        out = []
        for w in self.widgets_data:
            if w.get("type") != "tabpanel":
                continue
            tp_id = w.get("id")
            if not tp_id:
                continue
            props = w.get("props", {}) or {}
            tabs = props.get("tabs", []) or []
            for t in tabs:
                t = str(t)
                if not t:
                    continue
                short = tp_id if len(tp_id) <= 14 else tp_id[:11] + "..."
                out.append({
                    "tp_id": tp_id,
                    "tab": t,
                    "label": f"{t}  [{short}]",
                })
        return out

    def _editing_tab_label(self):
        if not self._editing_tab:
            return ""
        tp_id, tab_name = self._editing_tab
        short = tp_id if len(tp_id) <= 14 else tp_id[:11] + "..."
        return f"{tab_name}  [{short}]"

    def _editing_tab_name(self):
        return self._editing_tab[1] if self._editing_tab else ""

    def _set_editing_tab(self, value):
        if value is None or value == "(todas)":
            self._editing_tab = None
        elif isinstance(value, tuple) and len(value) == 2:
            self._editing_tab = (str(value[0]), str(value[1]))
        elif isinstance(value, str):
            self._editing_tab = self._tab_map.get(value)

        self._mark_dirty()
        self._rebuild_tab_dropdown()
        if self._editing_tab:
            self.status_text = f"Editando: {self._editing_tab_label()}"
        else:
            self.status_text = "Editando todas as abas"

    def _rebuild_tab_dropdown(self):
        all_tabs = self._get_all_tabs()
        options = ["(todas)"] + [t["label"] for t in all_tabs]
        self._tab_map = {t["label"]: (t["tp_id"], t["tab"]) for t in all_tabs}
        current = self._editing_tab_label() or "(todas)"

        if self._tab_dd is None:
            self._tab_dd = EditorDropdown(
                pygame.Rect(0, 0, 10, 10),
                options, current,
                on_change=self._set_editing_tab)
        else:
            self._tab_dd.options = options
            self._tab_dd.value = current

    def _widget_hidden_by_filter(self, wdata):
        if not self._editing_tab:
            return False
        tp_id, tab_name = self._editing_tab
        if wdata.get("type") == "tabpanel":
            return False
        wtab = wdata.get("tab")
        if not wtab:
            return False
        if wtab != tab_name:
            return True
        return not self._is_descendant_of(wdata, tp_id)

    def _widget_visible_in_canvas(self, wdata):
        return not self._widget_hidden_by_filter(wdata)

    # =================================================================
    # LAYOUT
    # =================================================================
    def _layout(self):
        sm = self.screen_manager
        vx, vy = sm.viewport_x, sm.viewport_y
        vw, vh = sm.viewport_width, sm.viewport_height

        max_side = max(60, (vw - self.MIN_CANVAS) // 2)
        self.left_w = max(self.MIN_LEFT, min(self.left_w, max_side))
        self.right_w = max(self.MIN_RIGHT, min(self.right_w, max_side))

        total = self.left_w + self.right_w + self.SPLITTER_W * 2 + self.MIN_CANVAS
        if total > vw:
            excess = total - vw
            if self.left_w + self.right_w > 0:
                self.left_w = max(self.MIN_LEFT, self.left_w - excess // 2)
                self.right_w = max(self.MIN_RIGHT, self.right_w - excess // 2)

        self.top_rect = pygame.Rect(vx, vy, vw, self.TOP_H)
        body_y = vy + self.TOP_H
        body_h = vh - self.TOP_H - self.BOT_H

        self.left_rect = pygame.Rect(vx, body_y, self.left_w, body_h)
        self.split_l_rect = pygame.Rect(vx + self.left_w, body_y,
                                        self.SPLITTER_W, body_h)
        canvas_x = vx + self.left_w + self.SPLITTER_W
        canvas_w = vw - self.left_w - self.right_w - self.SPLITTER_W * 2
        self.canvas_rect = pygame.Rect(canvas_x, body_y, canvas_w, body_h)
        self.split_r_rect = pygame.Rect(canvas_x + canvas_w, body_y,
                                        self.SPLITTER_W, body_h)
        self.right_rect = pygame.Rect(vx + vw - self.right_w, body_y,
                                      self.right_w, body_h)

        self._right_header_rect = pygame.Rect(
            self.right_rect.x, self.right_rect.y,
            self.right_rect.width, 82)
        self._right_footer_rect = pygame.Rect(
            self.right_rect.x, self.right_rect.bottom - 52,
            self.right_rect.width, 52)
        self._right_clip_rect = pygame.Rect(
            self.right_rect.x + 6,
            self._right_header_rect.bottom,
            self.right_rect.width - 12,
            self._right_footer_rect.y - self._right_header_rect.bottom)
        self._apply_btn_rect = pygame.Rect(
            self.right_rect.x + 16,
            self._right_footer_rect.y + 9,
            self.right_rect.width - 32, 34)

        pad = 16
        aw = max(50, self.canvas_rect.width - pad * 2)
        ah = max(50, self.canvas_rect.height - pad * 2)
        self._canvas_scale = max(0.05, min(aw / DESIGN_W, ah / DESIGN_H))
        dw = int(DESIGN_W * self._canvas_scale)
        dh = int(DESIGN_H * self._canvas_scale)
        self._design_draw_rect = pygame.Rect(
            self.canvas_rect.centerx - dw // 2,
            self.canvas_rect.centery - dh // 2, dw, dh)

        self._rebuild_fields()
        self._mark_dirty()

    # =================================================================
    # CAMPOS
    # =================================================================
    @staticmethod
    def _pick(wdata, props, key, default=None):
        if key in wdata:
            v = wdata[key]
            if v is not None and v != "":
                return v
        if key in props:
            v = props[key]
            if v is not None and v != "":
                return v
        return default

    def _rebuild_fields(self):
        if self.name_field is None:
            self.name_field = TextField(
                pygame.Rect(0, 0, 10, 10), self.layout_name)
        nw = max(120, min(240, int(self.top_rect.width * 0.18)))
        self.name_field.rect = pygame.Rect(
            self.top_rect.x + int(self.top_rect.width * 0.36),
            self.top_rect.y + 12, nw, 32)

        if not (0 <= self.selected_idx < len(self.widgets_data)):
            self.fields = {}
            self.dropdowns = {}
            self.right_max_scroll = 0
            self.right_scroll = 0
            return

        w = self.widgets_data[self.selected_idx]
        props = w.get("props", {}) or {}
        wtype = w.get("type", "button")
        sections = S.sections_for_type(wtype)

        if self._selected_type != wtype:
            self.sections_open = S.default_open_state(wtype)
            self._selected_type = wtype
        else:
            for sid, _, _ in sections:
                if sid not in self.sections_open:
                    self.sections_open[sid] = (sid not in
                                               {"sounds", "image",
                                                "border", "icon", "alpha"})

        old_focus = {k: getattr(f, "focused", False)
                     for k, f in self.fields.items()}

        content_h = 0
        for sid, _, keys in sections:
            content_h += self.SECTION_H
            if self.sections_open.get(sid, True):
                content_h += self.ROW_H * len(keys)

        clip_h = self._right_clip_rect.height
        self.right_max_scroll = max(0, content_h - clip_h)
        self.right_scroll = max(0, min(self.right_scroll,
                                       self.right_max_scroll))

        self.fields = {}
        self.dropdowns = {}

        x0 = self.right_rect.x + 92
        w_ = self.right_rect.width - 110
        y = self._right_clip_rect.y - self.right_scroll

        options = {
            "anchor": S.ANCHORS,
            "style": list(BUTTON_STYLES.keys()),
            "font_name": FontBook.available_fonts(),
            "align": S.ALIGNS,
            "click_sound": self._sound_names,
            "hover_sound": self._sound_names,
            "bg_image_mode": self._bg_image_modes,
            "icon_position": self._icon_positions,
            "border_sides": self._border_sides_choices,
        }

        placeholders = {
            "options": "A | B | C",
            "tabs": "Audio | Atalhos",
            "items": "Item 1 | Item 2 | Item 3",
            "on_click": "nome_acao",
            "on_toggle": "nome_acao",
            "on_change": "nome_acao",
            "on_select": "nome_acao",
            "click_volume": "0.0 - 1.0",
            "hover_volume": "0.0 - 1.0",
            "parent_id": "id do painel pai",
            "text_format": "{value}/{max}",
            "world_x": "ex: 500.0",
            "world_y": "ex: 300.0",
        }

        for sid, _, keys in sections:
            if self.sections_open.get(sid, True):
                y += self.SECTION_H
                for k in keys:
                    ftype = S.FIELD_TYPES.get(k, "text")
                    rect = pygame.Rect(x0, y, w_, 24)

                    if ftype in ("choice", "sound"):
                        opt_list = options.get(k, ["-"])
                        if k in ("click_sound", "hover_sound"):
                            cur = self._pick(w, props, k, None)
                            cur_s = cur if cur else "(nenhum)"
                        elif k == "anchor":
                            cur_s = str(w.get("anchor", "tl"))
                        elif k == "style":
                            cur_s = str(props.get("style", "primary"))
                        elif k == "font_name":
                            cur_s = str(self._pick(w, props, "font_name",
                                                   "default"))
                        elif k == "align":
                            cur_s = str(props.get("align", "center"))
                        elif k == "bg_image_mode":
                            cur_s = str(self._pick(w, props,
                                                   "bg_image_mode",
                                                   "stretch"))
                        elif k == "icon_position":
                            cur_s = str(self._pick(w, props,
                                                   "icon_position",
                                                   "left"))
                        elif k == "border_sides":
                            cur_s = str(self._pick(w, props,
                                                   "border_sides", "all"))
                        else:
                            cur_s = str(self._pick(w, props, k, "-"))

                        d = EditorDropdown(
                            rect, opt_list, cur_s,
                            on_change=lambda _v: self._apply_fields())
                        self.dropdowns[k] = d

                    elif ftype == "color":
                        cur = self._pick(w, props, k, None)
                        f = ColorField(rect, to_hex(cur) or "")
                        f.field.focused = old_focus.get(k, False)
                        self.fields[k] = f

                    elif ftype == "bool":
                        cur = self._pick(w, props, k, False)
                        self.fields[k] = BoolField(rect, bool(cur))

                    elif ftype == "image":
                        cur = self._pick(w, props, k, "")
                        def _mk_open(key=k):
                            return lambda: self._open_image_picker(key)
                        f = ImageField(rect, str(cur) if cur else "",
                                       on_open=_mk_open())
                        self.fields[k] = f

                    else:
                        cur = self._pick(w, props, k, "")
                        if ftype == "list":
                            if isinstance(cur, list):
                                cur = " | ".join(str(x) for x in cur)
                            else:
                                cur = str(cur) if cur else ""
                        elif cur is None:
                            cur = ""
                        else:
                            cur = str(cur)
                        f = TextField(rect, cur,
                                      placeholder=placeholders.get(k, ""))
                        f.focused = old_focus.get(k, False)
                        self.fields[k] = f

                    y += self.ROW_H
            else:
                y += self.SECTION_H

    def _sync_fields(self):
        self._rebuild_fields()
        self._rebuild_tab_dropdown()

    # =================================================================
    # CRUD
    # =================================================================
    def _new_layout(self):
        self.layout_name = "novo_layout"
        if self.name_field:
            self.name_field.text = self.layout_name
        self.widgets_data = [
            {"id": "titulo", "type": "label", "z": 0,
             "x": 0.5, "y": 0.10, "w": 0.6, "h": 0.08, "anchor": "c",
             "font_size": 42, "bold": True,
             "props": {"text": "MINHA TELA", "align": "center"}},
            {"id": "btn_ok", "type": "button", "z": 1,
             "x": 0.5, "y": 0.5, "w": 0.22, "h": 0.09, "anchor": "c",
             "bold": True,
             "props": {"label": "OK", "style": "primary"}},
        ]
        self._select_clear()
        self._editing_tab = None
        self._mark_dirty()
        self._rebuild_tab_dropdown()
        self.status_text = "Novo layout."

    def _next_z(self):
        if not self.widgets_data:
            return 0
        return max(int(w.get("z", 0)) for w in self.widgets_data) + 1

    def _add_widget(self, wtype):
        wid = f"{wtype}_{len(self.widgets_data) + 1}"
        base = {"id": wid, "type": wtype, "z": self._next_z(),
                "x": 0.5, "y": 0.5, "w": 0.22, "h": 0.09,
                "anchor": "c", "font_name": "default", "props": {}}

        # Herda aba em edição
        if self._editing_tab:
            base["tab"] = self._editing_tab[1]

        # Herda parent se algo tiver selecionado
        parent_id = None
        sel = None
        if 0 <= self.selected_idx < len(self.widgets_data):
            sel = self.widgets_data[self.selected_idx]
            stype = sel.get("type")
            if stype in ("panel", "tabpanel"):
                parent_id = sel.get("id")
            else:
                parent_id = sel.get("parent_id")

        if parent_id is None and self._editing_tab:
            parent_id = self._editing_tab[0]
        if parent_id:
            base["parent_id"] = parent_id

        # Defaults por tipo
        if wtype == "button":
            base["bold"] = True
            base["props"] = {"label": "Botão", "style": "primary"}
        elif wtype == "panel":
            base["bold"] = True
            base["props"] = {"title": "Painel"}
            base["w"], base["h"] = 0.4, 0.4
        elif wtype == "label":
            base["bold"] = False
            base["props"] = {"text": "Texto", "align": "center"}
            base["font_size"] = 24
        elif wtype == "list":
            base["bold"] = False
            base["props"] = {"items": ["Item 1", "Item 2", "Item 3"]}
            base["w"], base["h"] = 0.3, 0.4
        elif wtype == "image":
            base["w"], base["h"] = 0.3, 0.3
        elif wtype == "checkbox":
            base["bold"] = True
            base["props"] = {"label": "Opção", "checked": False}
            base["w"], base["h"] = 0.2, 0.05
        elif wtype == "slider":
            base["props"] = {"value": 0.5, "min": 0.0, "max": 1.0}
            base["w"], base["h"] = 0.3, 0.04
        elif wtype == "dropdown":
            base["bold"] = False
            base["props"] = {"options": ["A", "B", "C"], "value": "A"}
            base["w"], base["h"] = 0.2, 0.05
        elif wtype == "tabpanel":
            base["bold"] = True
            base["props"] = {"tabs": ["Aba 1", "Aba 2"],
                             "current_tab": "Aba 1"}
            base["w"], base["h"] = 0.8, 0.5
            base.pop("tab", None)
        elif wtype == "progress":
            base["props"] = {
                "value": 50, "max_value": 100, "min_value": 0,
                "show_text": True, "text_format": "{value}/{max}",
                "progress_bg": "#282D3C",
                "color_low": "#E65A5A",
                "color_mid": "#F8B030",
                "color_high": "#69DC82",
            }
            base["w"], base["h"] = 0.35, 0.04
        elif wtype == "badge":
            base["bold"] = True
            base["props"] = {
                "text": "BADGE",
                "bg_color": "#4A80E8",
                "badge_text_color": "#FFFFFF",
            }
            base["w"], base["h"] = 0.10, 0.04
        elif wtype == "world_sprite":
            base["props"] = {
                "world_x": 0.0, "world_y": 0.0, "max_size": 130,
            }
            base["w"], base["h"] = 0.12, 0.15

        self.widgets_data.append(base)
        self._select_only(len(self.widgets_data) - 1)
        self._mark_dirty()
        self._rebuild_fields()
        self._rebuild_tab_dropdown()
        self.status_text = f"Adicionado: {wid}"
        sound_manager.play_effect(SoundEffect.CLICK, volume=0.2)

    def _duplicate_selected(self):
        if not self.selected_indices:
            return
        src_indices = list(self.selected_indices)
        new_indices = set()
        id_map = {}
        for i in src_indices:
            if not (0 <= i < len(self.widgets_data)):
                continue
            src = self.widgets_data[i]
            old_id = src.get("id")
            new_id = f"{old_id}_copy" if old_id else None
            if old_id and new_id:
                id_map[old_id] = new_id

        for i in src_indices:
            if not (0 <= i < len(self.widgets_data)):
                continue
            src = self.widgets_data[i]
            dup = copy.deepcopy(src)
            old_id = src.get("id")
            if old_id:
                dup["id"] = id_map.get(old_id, f"{old_id}_copy")
            pid = dup.get("parent_id")
            if pid and pid in id_map:
                dup["parent_id"] = id_map[pid]
            dup["z"] = self._next_z()
            if not dup.get("parent_id"):
                dup["x"] = min(0.95, float(dup.get("x", 0.5)) + 0.02)
                dup["y"] = min(0.95, float(dup.get("y", 0.5)) + 0.02)
            self.widgets_data.append(dup)
            new_indices.add(len(self.widgets_data) - 1)

        if new_indices:
            self.selected_indices = new_indices
            self.selected_idx = next(iter(new_indices))
            self._selected_type = None
            self._mark_dirty()
            self._rebuild_fields()
            self._rebuild_tab_dropdown()
            self.status_text = f"Duplicados: {len(new_indices)}"

    def _delete_selected(self):
        if not self.selected_indices:
            return
        to_delete = set(self.selected_indices)
        for i in list(self.selected_indices):
            if 0 <= i < len(self.widgets_data):
                wid = self.widgets_data[i].get("id")
                if wid:
                    for d in self._get_descendants_of(wid):
                        didx = self._index_of_id(d.get("id"))
                        if didx >= 0:
                            to_delete.add(didx)

        for i in sorted(to_delete, reverse=True):
            if 0 <= i < len(self.widgets_data):
                self.widgets_data.pop(i)
        count = len(to_delete)
        self._select_clear()
        self._mark_dirty()
        self._rebuild_fields()
        self._rebuild_tab_dropdown()
        self.status_text = f"Removidos: {count}"

    def _unparent_selected(self):
        if not self.selected_indices:
            return
        for i in self.selected_indices:
            if 0 <= i < len(self.widgets_data):
                w = self.widgets_data[i]
                abs_rect = self._design_rect(w)
                w.pop("parent_id", None)
                w["x"] = abs_rect.x / DESIGN_W
                w["y"] = abs_rect.y / DESIGN_H
                w["w"] = abs_rect.w / DESIGN_W
                w["h"] = abs_rect.h / DESIGN_H
                w["anchor"] = "tl"
        self._mark_dirty()
        self._rebuild_fields()
        self.status_text = "Desagrupados"

    def _bring_forward(self):
        if not self.selected_indices:
            return
        for i in self.selected_indices:
            if 0 <= i < len(self.widgets_data):
                self.widgets_data[i]["z"] = self._next_z()
        self._mark_dirty()
        self.status_text = f"{len(self.selected_indices)} -> frente"

    def _send_backward(self):
        if not self.selected_indices:
            return
        mn = min(int(x.get("z", 0)) for x in self.widgets_data)
        for j, i in enumerate(sorted(self.selected_indices)):
            if 0 <= i < len(self.widgets_data):
                self.widgets_data[i]["z"] = mn - 1 - j
        self._mark_dirty()
        self.status_text = f"{len(self.selected_indices)} -> trás"

    # =================================================================
    # GEOMETRIA
    # =================================================================
    def _design_vp(self):
        return pygame.Rect(0, 0, DESIGN_W, DESIGN_H)

    def _design_rect(self, wdata):
        parent_content = self._get_parent_content_rect(wdata)
        return rel_rect(parent_content,
                        wdata.get("x", 0.1), wdata.get("y", 0.1),
                        wdata.get("w", 0.2), wdata.get("h", 0.08),
                        wdata.get("anchor", "tl"))

    def _screen_to_design(self, sxy):
        return ((sxy[0] - self._design_draw_rect.x) / self._canvas_scale,
                (sxy[1] - self._design_draw_rect.y) / self._canvas_scale)

    def _design_to_screen_rect(self, d_rect):
        dr = self._design_draw_rect
        return pygame.Rect(
            dr.x + int(d_rect.x * self._canvas_scale),
            dr.y + int(d_rect.y * self._canvas_scale),
            max(2, int(d_rect.w * self._canvas_scale)),
            max(2, int(d_rect.h * self._canvas_scale)))

    def _hit_test(self, design_pos):
        candidates = []
        for i, wd in enumerate(self.widgets_data):
            if not self._widget_visible_in_canvas(wd):
                continue
            r = self._design_rect(wd)
            if r.collidepoint(design_pos):
                depth = self._get_depth(wd)
                z = int(wd.get("z", 0))
                candidates.append((depth, z, i))
        if not candidates:
            return -1
        candidates.sort(key=lambda t: (t[0], t[1]), reverse=True)
        return candidates[0][2]

    def _hit_test_tab_header(self, design_pos):
        ordered = sorted(self.widgets_data,
                         key=lambda w: self._get_depth(w))
        for wdata in ordered:
            if wdata.get("type") != "tabpanel":
                continue
            rect = self._design_rect(wdata)
            tabs = (wdata.get("props", {}) or {}).get("tabs", [])
            if not tabs:
                continue
            tab_h = max(28, int(rect.height * 0.12))
            header = pygame.Rect(rect.x, rect.y, rect.width, tab_h)
            if not header.collidepoint(design_pos):
                continue
            n = len(tabs)
            tab_w = max(1, rect.width // n)
            idx = (design_pos[0] - rect.x) // tab_w
            idx = max(0, min(n - 1, int(idx)))
            return wdata, str(tabs[idx])
        return None

    def _resize_handle_rect(self, wdata):
        r = self._design_rect(wdata)
        return pygame.Rect(r.right - 10, r.bottom - 10, 20, 20)

    def _write_rect(self, idx, abs_rect):
        w = self.widgets_data[idx]
        parent_content = self._get_parent_content_rect(w)
        pcw = max(1, parent_content.width)
        pch = max(1, parent_content.height)
        w["x"] = (abs_rect.x - parent_content.x) / pcw
        w["y"] = (abs_rect.y - parent_content.y) / pch
        w["w"] = abs_rect.w / pcw
        w["h"] = abs_rect.h / pch
        w["anchor"] = "tl"

    def _compute_guides_and_snap(self, dragged_rect, dragged_indices):
        return compute_guides_and_snap(
            dragged_rect, dragged_indices,
            self.widgets_data, self._design_rect,
            DESIGN_W, DESIGN_H, SNAP_THRESHOLD)

    # =================================================================
    # CAMPOS → DADOS
    # =================================================================
    def _apply_fields(self):
        if not (0 <= self.selected_idx < len(self.widgets_data)):
            return
        w = self.widgets_data[self.selected_idx]
        props = w.setdefault("props", {})
        try:
            if "id" in self.fields:
                v = self.fields["id"].text.strip()
                if v:
                    w["id"] = v

            if "parent_id" in self.fields:
                v = self.fields["parent_id"].text.strip()
                if v:
                    w["parent_id"] = v
                else:
                    w.pop("parent_id", None)

            for k in ("x", "y", "w", "h"):
                if k in self.fields:
                    s = self.fields[k].text.strip()
                    if s:
                        try:
                            w[k] = float(s)
                        except ValueError:
                            pass

            if "z" in self.fields:
                s = self.fields["z"].text.strip()
                if s:
                    try:
                        w["z"] = int(float(s))
                    except ValueError:
                        pass

            if "tab" in self.fields:
                w["tab"] = self.fields["tab"].text.strip() or None

            if "padding" in self.fields:
                s = self.fields["padding"].text.strip()
                if s:
                    try:
                        w["padding"] = int(float(s))
                    except ValueError:
                        pass
                else:
                    w.pop("padding", None)

            if "font_size" in self.fields:
                s = self.fields["font_size"].text.strip()
                if s:
                    try:
                        w["font_size"] = int(float(s))
                    except ValueError:
                        pass
                else:
                    w.pop("font_size", None)

            if "bold" in self.fields:
                w["bold"] = bool(self.fields["bold"].value)

            for k in ("text_color", "fill_color", "border_color", "bg_tint",
                      "color_low", "color_mid", "color_high", "progress_bg",
                      "bg_color", "badge_text_color", "badge_border_color"):
                if k in self.fields:
                    s = self.fields[k].text.strip()
                    if s:
                        c = parse_color(s, None)
                        if c:
                            w[k] = to_hex(c)
                        else:
                            w.pop(k, None)
                    else:
                        w.pop(k, None)

            for k in ("bg_image", "icon"):
                if k in self.fields:
                    v = self.fields[k].text.strip()
                    if v:
                        w[k] = v
                    else:
                        w.pop(k, None)

            for k in ("bg_image_alpha", "border_width", "border_radius",
                      "icon_size", "icon_gap",
                      "fill_alpha", "border_alpha", "max_size", "radius"):
                if k in self.fields:
                    s = self.fields[k].text.strip()
                    if s:
                        try:
                            w[k] = int(float(s))
                        except ValueError:
                            pass
                    else:
                        w.pop(k, None)

            for k in ("draw_border", "draw_shadow", "show_text"):
                if k in self.fields:
                    w[k] = bool(self.fields[k].value)

            for k in ("click_volume", "hover_volume",
                      "world_x", "world_y"):
                if k in self.fields:
                    s = self.fields[k].text.strip()
                    if s:
                        try:
                            w[k] = float(s)
                        except ValueError:
                            pass
                    else:
                        w.pop(k, None)

            for k in ("click_sound", "hover_sound"):
                if k in self.dropdowns:
                    v = self.dropdowns[k].value
                    if v and v != "(nenhum)":
                        w[k] = v
                    else:
                        w.pop(k, None)

            if "anchor" in self.dropdowns:
                w["anchor"] = self.dropdowns["anchor"].value
            if "font_name" in self.dropdowns:
                w["font_name"] = self.dropdowns["font_name"].value
            if "bg_image_mode" in self.dropdowns:
                w["bg_image_mode"] = self.dropdowns["bg_image_mode"].value
            if "icon_position" in self.dropdowns:
                w["icon_position"] = self.dropdowns["icon_position"].value
            if "border_sides" in self.dropdowns:
                v = self.dropdowns["border_sides"].value
                if v and v != "all":
                    w["border_sides"] = v
                else:
                    w.pop("border_sides", None)

            # ---- props ----
            for k in ("label", "title", "text", "current_tab",
                      "text_format"):
                if k in self.fields:
                    props[k] = self.fields[k].text

            if "checked" in self.fields:
                props["checked"] = bool(self.fields["checked"].value)

            for k in ("value", "min", "max",
                      "max_value", "min_value"):
                if k in self.fields:
                    s = self.fields[k].text.strip()
                    if s:
                        try:
                            props[k] = float(s)
                        except ValueError:
                            pass

            for k in ("options", "tabs", "items"):
                if k in self.fields:
                    raw = self.fields[k].text
                    props[k] = [p.strip() for p in raw.split("|") if p.strip()]

            if "style" in self.dropdowns:
                props["style"] = self.dropdowns["style"].value
            if "align" in self.dropdowns:
                props["align"] = self.dropdowns["align"].value

            for k in ("on_click", "on_toggle", "on_change", "on_select"):
                if k in self.fields:
                    v = self.fields[k].text.strip()
                    if v:
                        props[k] = v
                    else:
                        props.pop(k, None)

            # Filtro pode ter ficado inválido (tabs mudaram)
            if w.get("type") == "tabpanel" and self._editing_tab:
                tp_id, tab_name = self._editing_tab
                if tp_id == w.get("id"):
                    tabs_atual = props.get("tabs", [])
                    if tab_name not in tabs_atual:
                        self._editing_tab = None
                        self._rebuild_tab_dropdown()

            self._mark_dirty()
            self.status_text = "Aplicado."
        except Exception as e:
            self.status_text = f"Erro: {e}"

    # =================================================================
    # SAVE / LOAD / EXPORT
    # =================================================================
    def _current_dict(self):
        return {"name": self.name_field.text.strip() or "layout",
                "design_size": [DESIGN_W, DESIGN_H],
                "widgets": self.widgets_data}

    def _save_layout(self):
        self._flush_current_edits()
        name = self.name_field.text.strip() or "layout"
        LAYOUTS_DIR.mkdir(parents=True, exist_ok=True)
        path = LAYOUTS_DIR / f"{name}.json"
        try:
            with open(path, "w", encoding="utf-8") as f:
                json.dump(self._current_dict(), f, indent=2,
                          ensure_ascii=False)
            self.status_text = f"Salvo: {path}"
            print(f"[UI Editor] Layout salvo em: {path}")
            sound_manager.play_effect(SoundEffect.CLICK, volume=0.3)
        except Exception as e:
            self.status_text = f"Erro ao salvar: {e}"

    def _open_load_picker(self):
        try:
            items = ScreenLoader.list_layouts()
        except Exception:
            items = []
        self.load_picker.open_with(
            items,
            on_select=self._on_load_selected,
            center=(self.top_rect.centerx, self.top_rect.centery))

    def _on_load_selected(self, name):
        path = LAYOUTS_DIR / f"{name}.json"
        if not path.exists():
            self.status_text = f"Não existe: {path}"
            return
        try:
            with open(path, "r", encoding="utf-8") as f:
                data = json.load(f)
            self.widgets_data = data.get("widgets", [])
            self.layout_name = data.get("name", name)
            self.name_field.text = self.layout_name
            self._select_clear()

            first_tp = next((w for w in self.widgets_data
                             if w.get("type") == "tabpanel"), None)
            if first_tp:
                tabs = (first_tp.get("props", {}) or {}).get("tabs", []) or []
                if tabs:
                    self._editing_tab = (first_tp.get("id"), str(tabs[0]))
                else:
                    self._editing_tab = None
            else:
                self._editing_tab = None

            self._mark_dirty()
            self._rebuild_fields()
            self._rebuild_tab_dropdown()
            self.status_text = f"Carregado: {path}"
            sound_manager.play_effect(SoundEffect.CLICK, volume=0.3)
        except Exception as e:
            self.status_text = f"Erro ao carregar: {e}"

    def _open_image_picker(self, field_key):
        self._image_target_key = field_key
        try:
            items = ScreenLoader.list_images()
        except Exception:
            items = []
        self.image_picker.open_with(
            items,
            on_select=lambda name: self._on_image_selected(field_key, name),
            center=(self.top_rect.centerx, self.top_rect.centery))

    def _on_image_selected(self, field_key, name):
        if name == "(nenhuma)":
            name = ""
        if not (0 <= self.selected_idx < len(self.widgets_data)):
            return
        w = self.widgets_data[self.selected_idx]
        if name:
            w[field_key] = name
        else:
            w.pop(field_key, None)
        f = self.fields.get(field_key)
        if f is not None:
            f.text = name
        self._mark_dirty()
        self.status_text = f"Imagem: {name or '(nenhuma)'}"

    def _on_color_picked(self, key, hexv):
        if not (0 <= self.selected_idx < len(self.widgets_data)):
            return
        w = self.widgets_data[self.selected_idx]
        c = parse_color(hexv, None)
        if c:
            w[key] = to_hex(c)
        else:
            w.pop(key, None)
        f = self.fields.get(key)
        if f is not None:
            try:
                f.text = to_hex(c) if c else ""
            except Exception:
                pass
        self._mark_dirty()
        self.status_text = f"Cor: {hexv}"

    def _collect_actions_used(self):
        used = set()
        for w in self.widgets_data:
            props = w.get("props", {}) or {}
            for akey in ("on_click", "on_toggle", "on_change", "on_select"):
                a = props.get(akey)
                if a and isinstance(a, str) and a.strip():
                    used.add(a.strip())
        return sorted(used)

    def _export_python(self):
        name = self.name_field.text.strip() or "layout"
        cls = "".join(p.capitalize() for p in name.split("_")) + "Scene"

        actions_used = self._collect_actions_used()
        builtin_map = {"set_tab": "self.set_active_tab"}

        action_lines, stub_names = [], []
        for a in actions_used:
            if a in builtin_map:
                action_lines.append(f'            "{a}": {builtin_map[a]},')
            else:
                method = f"_action_{a}"
                action_lines.append(f'            "{a}": {method},')
                stub_names.append((a, method))

        if not action_lines:
            action_lines.append('            # Nenhuma ação declarada.')

        stubs = ""
        for a, method in stub_names:
            stubs += (
                f"\n    def {method}(self, *args):\n"
                f'        """Ação: {a}."""\n'
                f'        print("[{cls}] {a}", args)\n'
            )

        actions_repr = ", ".join(actions_used) if actions_used else "(nenhuma)"
        layout_rel = f"res/ui_layouts/{name}.json"

        code = f'''# src/scenes_editor/{name}_scene/{name}_scene.py
"""Cena gerada pelo editor visual.
Ações declaradas nos widgets: {actions_repr}
"""
from src.ui.screen_template import StandardScreen
from src.ui.screen_loader import ScreenLoader


class {cls}(StandardScreen):
    title = ""
    show_back_button = False

    def build(self):
        ScreenLoader.load(self, "{layout_rel}")
        self._sync_widgets()

    def get_actions(self):
        return {{
{chr(10).join(action_lines)}
        }}

    def _sync_widgets(self):
        """Sincronize o estado inicial dos widgets com o estado do jogo."""
        pass

    def on_back(self):
        self.game.current_scene = self.game.menu_scene
{stubs}'''

        out_dir = SCENES_DIR / f"{name}_scene"
        out_dir.mkdir(parents=True, exist_ok=True)
        (out_dir / "__init__.py").touch(exist_ok=True)
        out_path = out_dir / f"{name}_scene.py"
        try:
            with open(out_path, "w", encoding="utf-8") as f:
                f.write(code)
            self.status_text = f"Exportado: {out_path}"
            print(f"[UI Editor] Cena exportada em: {out_path}")
            print(f"[UI Editor] Ações: {actions_used}")
        except Exception as e:
            self.status_text = f"Erro ao exportar: {e}"

    # =================================================================
    # PREVIEW
    # =================================================================
    def _ensure_runtime(self):
        if not self._runtime_dirty:
            return
        self._runtime_widgets = []

        roots = [w for w in self.widgets_data if not w.get("parent_id")]
        roots.sort(key=lambda w: int(w.get("z", 0)))
        for root in roots:
            self._flatten_runtime(root)

        self.preview_active_tab = None
        for w in self._runtime_widgets:
            if w.__class__.__name__ == "TabPanel":
                self.preview_active_tab = w.current_tab
                orig = w.on_change

                def make_cb(tp, orig_cb):
                    def cb(name):
                        self.preview_active_tab = name
                        if orig_cb:
                            orig_cb(name)
                    return cb

                w.on_change = make_cb(w, orig)
                break
        self._runtime_dirty = False

    def _flatten_runtime(self, wdata):
        parent_content = self._get_parent_content_rect(wdata)
        widget = ScreenLoader._build_widget(wdata, parent_content, {}, self)
        if widget is not None:
            widget.rect = self._design_to_screen_rect(widget.rect)
            self._runtime_widgets.append(widget)

        children = self._get_children_of(wdata.get("id"))
        children.sort(key=lambda w: int(w.get("z", 0)))
        for c in children:
            self._flatten_runtime(c)

    def _is_widget_visible_preview(self, w):
        if self.preview_active_tab is None:
            return True
        wtab = getattr(w, "tab", None)
        return wtab is None or wtab == self.preview_active_tab

    def _splitter_at(self, pos):
        if self.split_l_rect and self.split_l_rect.inflate(6, 0).collidepoint(pos):
            return "left"
        if self.split_r_rect and self.split_r_rect.inflate(6, 0).collidepoint(pos):
            return "right"
        return None

    # =================================================================
    # EVENTOS
    # =================================================================
    def handle_event(self, event):
        if self._tab_dd is not None and self._tab_dd.open:
            if self._tab_dd.handle_event(event):
                return

        if self.color_picker.open:
            if self.color_picker.handle_event(event):
                return
        if self.load_picker.open:
            if self.load_picker.handle_event(event):
                return
        if self.image_picker.open:
            if self.image_picker.handle_event(event):
                return

        if self.preview_mode:
            if event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE:
                self.preview_mode = False
                self._mark_dirty()
                self.status_text = "Preview desligado."
                return
            if event.type == pygame.VIDEORESIZE:
                self._layout()
                return
            ordered = sorted(self._runtime_widgets,
                             key=lambda x: getattr(x, "z", 0), reverse=True)
            for w in ordered:
                if not self._is_widget_visible_preview(w):
                    continue
                if w.handle_event(event):
                    return
            for w in self._runtime_widgets:
                if self._is_widget_visible_preview(w):
                    w.handle_event(event)
            return

        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            which = self._splitter_at(event.pos)
            if which:
                self._dragging_splitter = which
                self._split_drag_start_x = event.pos[0]
                self._split_start_w = self.left_w if which == "left" \
                    else self.right_w
                return
        if event.type == pygame.MOUSEBUTTONUP and event.button == 1:
            if self._dragging_splitter:
                self._dragging_splitter = None
                return
        if event.type == pygame.MOUSEMOTION:
            if self._dragging_splitter == "left":
                dx = event.pos[0] - self._split_drag_start_x
                self.left_w = self._split_start_w + dx
                self._layout()
                return
            if self._dragging_splitter == "right":
                dx = event.pos[0] - self._split_drag_start_x
                self.right_w = self._split_start_w - dx
                self._layout()
                return
            self._hover_splitter = self._splitter_at(event.pos)

        if event.type == pygame.MOUSEWHEEL:
            mx, my = pygame.mouse.get_pos()
            for d in self.dropdowns.values():
                if d.open and d._list_rect and d._list_rect.collidepoint(mx, my):
                    if d.handle_event(event):
                        return
            if self._right_clip_rect.collidepoint(mx, my):
                self.right_scroll -= event.y * 24
                self.right_scroll = max(0, min(self.right_max_scroll,
                                               self.right_scroll))
                self._rebuild_fields()
                return
            return

        for d in self.dropdowns.values():
            if d.handle_event(event):
                return

        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            if self._right_clip_rect.collidepoint(event.pos):
                for sid, r in self._section_header_rects.items():
                    if r.collidepoint(event.pos):
                        self._clear_field_focus()
                        self.sections_open[sid] = not self.sections_open[sid]
                        self._rebuild_fields()
                        return

                if self._apply_btn_rect.collidepoint(event.pos):
                    self._clear_field_focus()
                    self._apply_fields()
                    return

                clicked = None
                for k, f in self.fields.items():
                    r = getattr(f, "rect", None)
                    sw = getattr(f, "swatch_rect", None)
                    if (r and r.collidepoint(event.pos)) or \
                       (sw and sw.collidepoint(event.pos)):
                        clicked = k
                        break

                for k, f in self.fields.items():
                    self._set_field_focus(f, (k == clicked))
                if self.name_field:
                    try:
                        self.name_field.focused = False
                    except Exception:
                        pass

                if clicked is not None:
                    f = self.fields[clicked]
                    sw = getattr(f, "swatch_rect", None)
                    if sw and sw.collidepoint(event.pos):
                        self._color_target_key = clicked
                        initial = getattr(f, "text", "") or "#FFFFFF"
                        self.color_picker.open_with(
                            initial,
                            on_confirm=lambda hexv, key=clicked:
                                self._on_color_picked(key, hexv),
                            center=(self.right_rect.centerx,
                                    self.right_rect.centery))
                        return

                    res = f.handle_event(event)
                    if res is True or res == "open_picker":
                        self._apply_fields()
                    return
                return

        if event.type == pygame.MOUSEMOTION:
            if self.name_field:
                self.name_field.handle_event(event)
            for f in self.fields.values():
                f.handle_event(event)

        if event.type == pygame.MOUSEBUTTONUP and event.button == 1:
            for f in self.fields.values():
                f.handle_event(event)

        if self.name_field:
            res = self.name_field.handle_event(event)
            if res:
                return

        if event.type == pygame.KEYDOWN:
            kind, key, obj = self._focused_field()
            if kind == "field":
                res = obj.handle_event(event)
                if res == "copy":
                    self.status_text = "Copiado."
                elif res == "paste":
                    self.status_text = "Colado."
                elif res == "cut":
                    self.status_text = "Cortado."
                if res in ("copy", "paste", "cut") or res is True:
                    self._apply_fields()
                return
            if kind == "name":
                obj.handle_event(event)
                return

            mods = pygame.key.get_mods()
            ctrl = bool(mods & pygame.KMOD_CTRL)

            if event.key == pygame.K_ESCAPE and self._editing_tab:
                self._set_editing_tab(None)
                return

            if event.key == pygame.K_ESCAPE:
                self._save_layout()
                self.game.current_scene = self.game.menu_scene
                return
            if ctrl and event.key == pygame.K_d:
                self._duplicate_selected()
                return
            if ctrl and event.key == pygame.K_s:
                self._save_layout()
                return
            if ctrl and event.key == pygame.K_o:
                self._flush_current_edits()
                self._open_load_picker()
                return
            if event.key == pygame.K_DELETE:
                self._delete_selected()
                return
            if event.key == pygame.K_g:
                self.show_grid = not self.show_grid
                return
            if event.key == pygame.K_PAGEUP:
                self._bring_forward()
                return
            if event.key == pygame.K_PAGEDOWN:
                self._send_backward()
                return
            if self.selected_indices and event.key in (
                    pygame.K_LEFT, pygame.K_RIGHT,
                    pygame.K_UP, pygame.K_DOWN):
                step = 10 if (mods & pygame.KMOD_SHIFT) else 1
                dx = (-step if event.key == pygame.K_LEFT else
                      step if event.key == pygame.K_RIGHT else 0)
                dy = (-step if event.key == pygame.K_UP else
                      step if event.key == pygame.K_DOWN else 0)
                for i in self._top_level_selection():
                    if 0 <= i < len(self.widgets_data):
                        w = self.widgets_data[i]
                        parent_content = self._get_parent_content_rect(w)
                        pcw = max(1, parent_content.width)
                        pch = max(1, parent_content.height)
                        w["x"] = float(w.get("x", 0.0)) + dx / pcw
                        w["y"] = float(w.get("y", 0.0)) + dy / pch
                self._mark_dirty()
                self._rebuild_fields()
                return

        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            if self._handle_ui_click(event.pos):
                return
            if self.canvas_rect.collidepoint(event.pos):
                self._handle_canvas_click(event.pos, event)

        if event.type == pygame.MOUSEMOTION:
            self._handle_drag(event.pos)

        if event.type == pygame.MOUSEBUTTONUP and event.button == 1:
            if self._marquee is not None:
                self._apply_marquee()
                self._marquee = None
                self._marquee_start_screen = None
                self.dragging = False
                self.resizing = False
                self._drag_rects = {}
                self._active_guides_v = []
                self._active_guides_h = []
                self._strong_guides_v = set()
                self._strong_guides_h = set()
                return
            self.dragging = False
            self.resizing = False
            self._drag_rects = {}
            self._active_guides_v = []
            self._active_guides_h = []
            self._strong_guides_v = set()
            self._strong_guides_h = set()

    # =================================================================
    # HANDLERS INTERNOS
    # =================================================================
    def _handle_ui_click(self, pos):
        for key, r in self._top_btn_rects.items():
            if r.collidepoint(pos):
                if key == "novo":
                    self._flush_current_edits()
                    self._new_layout()
                elif key == "salvar":
                    self._save_layout()
                elif key == "carregar":
                    self._flush_current_edits()
                    self._open_load_picker()
                elif key == "exportar":
                    self._flush_current_edits()
                    self._export_python()
                elif key == "preview":
                    self._flush_current_edits()
                    self.preview_mode = True
                    self._select_clear()
                    self._clear_field_focus()
                    self._mark_dirty()
                    self.status_text = "PREVIEW — ESC para sair"
                elif key == "fechar":
                    self._save_layout()
                    self.game.current_scene = self.game.menu_scene
                return True

        for r, wtype in self._left_tool_rects:
            if r.collidepoint(pos):
                self._flush_current_edits()
                self._clear_field_focus()
                self._add_widget(wtype)
                return True

        for rect, cb in self._left_action_rects:
            if rect.collidepoint(pos):
                self._clear_field_focus()
                cb()
                return True

        return False

    def _handle_canvas_click(self, pos, event):
        design = self._screen_to_design(pos)
        ctrl = bool(pygame.key.get_mods() & pygame.KMOD_CTRL)

        tab_hit = self._hit_test_tab_header(design)
        if tab_hit is not None:
            wdata, tab_name = tab_hit
            tp_id = wdata.get("id")
            if self._editing_tab == (tp_id, tab_name):
                self._set_editing_tab(None)
            else:
                self._set_editing_tab((tp_id, tab_name))
            return

        if len(self.selected_indices) == 1 and self.selected_idx >= 0:
            sel = self.widgets_data[self.selected_idx]
            if self._resize_handle_rect(sel).collidepoint(design):
                self.resizing = True
                self.drag_start_rect = self._design_rect(sel).copy()
                self.drag_offset = design
                return

        idx = self._hit_test(design)

        if idx < 0:
            self._flush_current_edits()
            if not ctrl:
                self._select_clear()
                self._rebuild_fields()
            self._marquee_start_screen = pos
            self._marquee = pygame.Rect(pos[0], pos[1], 0, 0)
            return

        if idx != self.selected_idx:
            self._flush_current_edits()

        if ctrl:
            self._select_toggle(idx)
        else:
            if idx not in self.selected_indices:
                self._select_only(idx)
            else:
                self.selected_idx = idx

        self._rebuild_fields()

        if self.selected_indices and idx in self.selected_indices:
            self.dragging = True
            drag_set = self._top_level_selection()
            self._drag_rects = {
                i: self._design_rect(self.widgets_data[i]).copy()
                for i in drag_set
                if 0 <= i < len(self.widgets_data)
            }
            self.drag_offset = design
            self._active_guides_v = []
            self._active_guides_h = []
            self._strong_guides_v = set()
            self._strong_guides_h = set()

    def _apply_marquee(self):
        if self._marquee is None or self._marquee.width < 3 or \
                self._marquee.height < 3:
            return
        dr = self._design_draw_rect
        s = self._canvas_scale
        d_x0 = (self._marquee.left - dr.x) / s
        d_y0 = (self._marquee.top - dr.y) / s
        d_x1 = (self._marquee.right - dr.x) / s
        d_y1 = (self._marquee.bottom - dr.y) / s
        sel_rect = pygame.Rect(int(min(d_x0, d_x1)), int(min(d_y0, d_y1)),
                               abs(int(d_x1 - d_x0)), abs(int(d_y1 - d_y0)))
        picked = set()
        for i, wd in enumerate(self.widgets_data):
            if not self._widget_visible_in_canvas(wd):
                continue
            if sel_rect.colliderect(self._design_rect(wd)):
                picked.add(i)
        self.selected_indices = picked
        self.selected_idx = next(iter(picked), -1)
        self._selected_type = None
        self._rebuild_fields()
        self.status_text = f"Selecionados: {len(picked)}"

    def _handle_drag(self, pos):
        if self._marquee is not None and self._marquee_start_screen is not None:
            sx, sy = self._marquee_start_screen
            w = pos[0] - sx
            h = pos[1] - sy
            self._marquee = pygame.Rect(min(sx, pos[0]), min(sy, pos[1]),
                                        abs(w), abs(h))
            return

        if not (self.dragging or self.resizing):
            return

        design = self._screen_to_design(pos)

        if self.resizing:
            if self.selected_idx < 0:
                return
            r = self.drag_start_rect
            new_rect = pygame.Rect(r.x, r.y,
                                   max(20, int(design[0] - r.x)),
                                   max(16, int(design[1] - r.y)))
            self._write_rect(self.selected_idx, new_rect)
            self._mark_dirty()
            self._rebuild_fields()
            return

        if not self._drag_rects:
            return

        dx = design[0] - self.drag_offset[0]
        dy = design[1] - self.drag_offset[1]

        if self.selected_idx in self._drag_rects:
            ref = self._drag_rects[self.selected_idx]
            moved = pygame.Rect(int(ref.x + dx), int(ref.y + dy),
                                ref.w, ref.h)
            sdx, sdy, gv, gh, sv, sh = self._compute_guides_and_snap(
                moved, set(self._drag_rects.keys()))
            dx += sdx
            dy += sdy
            self._active_guides_v = list(gv)
            self._active_guides_h = list(gh)
            self._strong_guides_v = sv
            self._strong_guides_h = sh
        else:
            self._active_guides_v = []
            self._active_guides_h = []
            self._strong_guides_v = set()
            self._strong_guides_h = set()

        for i, r0 in self._drag_rects.items():
            new_rect = pygame.Rect(int(r0.x + dx), int(r0.y + dy),
                                   r0.w, r0.h)
            self._write_rect(i, new_rect)

        self._mark_dirty()
        self._rebuild_fields()

    # =================================================================
    # UPDATE
    # =================================================================
    def fixed_update(self, dt):
        for f in self.fields.values():
            f.update(dt)
        if self.name_field:
            self.name_field.update(dt)
        cur = (self.screen_manager.window_width,
               self.screen_manager.window_height)
        if cur != self._last_size:
            self._last_size = cur
            self._layout()
        if self.preview_mode:
            self._ensure_runtime()
            for w in self._runtime_widgets:
                w.update(dt)

    # =================================================================
    # RENDER
    # =================================================================
    def render(self, screen):
        screen.fill((18, 22, 36))

        if self.preview_mode:
            self._render_preview(screen)
            self._render_status(screen)
            self.color_picker.render(screen)
            self.load_picker.render(screen)
            self.image_picker.render(screen)
            return

        self._render_top(screen)
        self._render_left(screen)
        self._render_canvas(screen)
        self._render_guides(screen)
        self._render_marquee(screen)
        self._render_right(screen)
        self._render_splitters(screen)
        self._render_status(screen)

        if self._tab_dd is not None:
            self._tab_dd.render_open_overlay(screen)
        for d in self.dropdowns.values():
            d.render_open_overlay(screen)

        self.color_picker.render(screen)
        self.load_picker.render(screen)
        self.image_picker.render(screen)