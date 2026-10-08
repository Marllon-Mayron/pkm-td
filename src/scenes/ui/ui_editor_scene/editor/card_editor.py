# src/scenes/ui_editor_scene/editor/card_editor.py
"""
Modal para editar visualmente o `card_layout` de um widget CardGrid.

Features:
  - Canvas com drag/resize dos widgets
  - Lista de widgets + botões para adicionar
  - Painel de propriedades (texto/int/float/color/bool/choice)
  - ColorPicker modal (clique no swatch)
  - Binding picker (botão {} → dropdown de {item.xxx})
  - Preview com dados reais (callable cycling)
"""
import copy
import pygame

from src.ui.theme import FontBook, parse_color, to_hex
from src.ui.screen_loader import ScreenLoader
from src.ui.bindings import resolve_wdata, resolve_value
from src.ui.layout import rel_rect
from src.ui.color_picker import ColorPicker
from src.scenes.ui.ui_editor_scene.editor.fields import (
    TextField, ColorField, BoolField, EditorDropdown,
)


DESIGN_CARD_W = 240
DESIGN_CARD_H = 280


def _looks_like_binding(s):
    return isinstance(s, str) and "{item." in s


# =====================================================================
# CardLayoutField — botão que abre o modal (usado pelo controller)
# =====================================================================
class CardLayoutField:
    def __init__(self, rect, on_open=None):
        self.rect = rect
        self.on_open = on_open
        self._hover = False
        self._count = 0
        self.focused = False

    def set_count(self, n): self._count = int(n)

    def handle_event(self, event):
        if event.type == pygame.MOUSEMOTION:
            self._hover = self.rect.collidepoint(event.pos)
        elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            if self.rect.collidepoint(event.pos):
                if self.on_open:
                    self.on_open()
                return True
        return False

    def update(self, dt): pass

    def render(self, screen):
        bg = (72, 88, 128) if self._hover else (36, 44, 64)
        bd = (248, 176, 48) if self._hover else (80, 104, 152)
        pygame.draw.rect(screen, bg, self.rect, border_radius=6)
        pygame.draw.rect(screen, bd, self.rect, 2, border_radius=6)
        txt = f"Editar layout do card ({self._count} widgets) ..."
        f = FontBook.get(13, True)
        s = f.render(txt, True, (232, 232, 208))
        screen.blit(s, (self.rect.x + 8,
                        self.rect.centery - s.get_height() // 2))

    @property
    def text(self): return ""
    @text.setter
    def text(self, v): pass


# =====================================================================
# BindingPopup — dropdown de {item.xxx} ao lado de um campo
# =====================================================================
class BindingPopup:
    ROW_H = 22
    W = 220
    MAX_VISIBLE = 10
    FONT_SIZE = 12

    def __init__(self):
        self.open = False
        self.rect = pygame.Rect(0, 0, 0, 0)
        self.options = []
        self.hover_idx = -1
        self.target_key = None
        self.on_select = None
        self._scroll = 0
        self._hover = -1

    def open_at(self, anchor_rect, options, target_key, on_select):
        visible = min(self.MAX_VISIBLE, len(options))
        h = visible * self.ROW_H + 4
        x = anchor_rect.x
        y = anchor_rect.bottom + 2
        sfc = pygame.display.get_surface()
        if sfc and y + h > sfc.get_height() - 4:
            y = max(4, anchor_rect.y - h - 2)
        if x + self.W > (sfc.get_width() - 4 if sfc else 9999):
            x = max(4, (sfc.get_width() - self.W - 4) if sfc else 0)
        self.rect = pygame.Rect(x, y, self.W, h)
        self.options = list(options)
        self.target_key = target_key
        self.on_select = on_select
        self.hover_idx = -1
        self._scroll = 0
        self.open = True

    def close(self):
        self.open = False
        self.hover_idx = -1
        self.target_key = None

    def handle_event(self, event):
        if not self.open:
            return False
        if event.type == pygame.MOUSEMOTION:
            if self.rect.collidepoint(event.pos):
                rel = event.pos[1] - self.rect.y - 2
                idx = self._scroll + rel // self.ROW_H
                self.hover_idx = idx if 0 <= idx < len(self.options) else -1
            else:
                self.hover_idx = -1
            return True
        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            if self.rect.collidepoint(event.pos):
                idx = self._scroll + (event.pos[1] - self.rect.y - 2) // self.ROW_H
                if 0 <= idx < len(self.options):
                    if self.on_select:
                        self.on_select(self.target_key, self.options[idx])
                self.close()
                return True
            self.close()
            return True
        if event.type == pygame.MOUSEWHEEL:
            if self.rect.collidepoint(pygame.mouse.get_pos()):
                self._scroll -= event.y
                max_s = max(0, len(self.options) - self.MAX_VISIBLE)
                self._scroll = max(0, min(max_s, self._scroll))
                return True
        if event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE:
            self.close()
            return True
        return True

    def render(self, screen):
        if not self.open:
            return
        sh = self.rect.move(3, 3)
        sh_s = pygame.Surface(sh.size, pygame.SRCALPHA)
        pygame.draw.rect(sh_s, (0, 0, 0, 150), sh_s.get_rect(),
                         border_radius=6)
        screen.blit(sh_s, sh.topleft)
        pygame.draw.rect(screen, (20, 24, 36), self.rect, border_radius=6)
        pygame.draw.rect(screen, (248, 176, 48), self.rect, 2, border_radius=6)

        visible = min(self.MAX_VISIBLE, len(self.options))
        f = FontBook.get(self.FONT_SIZE, False)
        old = screen.get_clip()
        screen.set_clip(self.rect.inflate(-4, -4))
        for row in range(visible):
            idx = self._scroll + row
            if idx >= len(self.options):
                break
            opt = self.options[idx]
            r = pygame.Rect(
                self.rect.x + 2, self.rect.y + 2 + row * self.ROW_H,
                self.rect.width - 4, self.ROW_H)
            if idx == self.hover_idx:
                pygame.draw.rect(screen, (48, 60, 90), r, border_radius=3)
            col = (248, 200, 88) if opt.startswith("(limpar") else (232, 232, 208)
            txt = f.render(opt, True, col)
            screen.blit(txt, (r.x + 6, r.centery - txt.get_height() // 2))
        screen.set_clip(old)


# =====================================================================
# Modal principal
# =====================================================================
class CardLayoutEditor:
    PAD     = 16
    TITLE_H = 40
    FOOT_H  = 52
    LEFT_W  = 220
    RIGHT_W = 300
    ROW_H   = 24
    BTN_W   = 22

    ADD_TYPES = [
        ("panel",    "Painel",   "gold"),
        ("label",    "Texto",    "ghost"),
        ("image",    "Imagem",   "success"),
        ("badge",    "Badge",    "gold"),
        ("button",   "Botão",    "primary"),
        ("progress", "Barra",    "success"),
        ("divider",  "Divisor",  "ghost"),
    ]

    FIELD_DEFS = [
        ("id",           "text",   "ID"),
        ("z",            "int",    "Z"),
        ("x",            "float",  "X (0-1)"),
        ("y",            "float",  "Y (0-1)"),
        ("w",            "float",  "W (0-1)"),
        ("h",            "float",  "H (0-1)"),
        ("anchor",       "choice", "Ancora"),
        ("text",         "text",   "Texto"),
        ("label",        "text",   "Label"),
        ("title",        "text",   "Titulo"),
        ("icon",         "text",   "Icone"),
        ("font_size",    "int",    "Tam. fonte"),
        ("bold",         "bool",   "Negrito"),
        ("text_fit",     "choice", "Ajuste texto"),
        ("text_color",   "color",  "Cor texto"),
        ("fill_color",   "color",  "Fundo"),
        ("border_color", "color",  "Borda"),
        ("bg_color",     "color",  "Cor badge"),
        ("fill_alpha",   "int",    "Alpha fundo"),
        ("border_alpha", "int",    "Alpha borda"),
        ("border_width", "int",    "Esp. borda"),
        ("border_radius","int",    "Raio"),
        ("draw_border",  "bool",   "Mostrar borda"),
        ("draw_shadow",  "bool",   "Sombra"),
        ("visible",      "text",   "Visivel"),
    ]
    ANCHORS  = ["tl", "tc", "tr", "cl", "c", "cr", "bl", "bc", "br"]
    TEXT_FIT = ["none", "shrink", "wrap", "ellipsis", "shrink_wrap"]

    def __init__(self):
        self.open = False
        self.card_layout = []
        self.sample_item = {}
        self._sample_provider = None
        self._on_save = None
        self._selected_idx = -1
        self._scroll = 0
        self._max_scroll = 0
        self._dragging = False
        self._resizing = False
        self._drag_offset = (0.0, 0.0)
        self._drag_start_rect = None
        self._fields = {}
        self._dropdowns = {}
        self._field_order = []
        self._fonts = {}
        self._binding_btns = {}

        self.color_picker = ColorPicker()
        self._color_target_key = None
        self.binding_popup = BindingPopup()

        self.rect = pygame.Rect(0, 0, 1080, 680)
        self._canvas_rect   = pygame.Rect(0, 0, 0, 0)
        self._left_rect     = pygame.Rect(0, 0, 0, 0)
        self._right_rect    = pygame.Rect(0, 0, 0, 0)
        self._right_clip    = pygame.Rect(0, 0, 0, 0)
        self._ok_rect       = pygame.Rect(0, 0, 0, 0)
        self._cancel_rect   = pygame.Rect(0, 0, 0, 0)
        self._refresh_btn   = pygame.Rect(0, 0, 0, 0)
        self._left_item_rects = []
        self._left_add_rects  = []
        self._design_rect     = pygame.Rect(0, 0, 1, 1)
        self._scale = 1.0

    # -----------------------------------------------------------------
    def _font(self, size, bold=False):
        key = (int(size), bool(bold))
        if key not in self._fonts:
            self._fonts[key] = FontBook.get(size, bold)
        return self._fonts[key]

    # -----------------------------------------------------------------
    def open_with(self, card_layout, sample_item, on_save):
        """
        sample_item: dict OU callable sem args que retorna dict.
        Se callable, o botão "Trocar preview" chama de novo.
        """
        self.card_layout = copy.deepcopy(card_layout or [])
        self._on_save = on_save
        self.open = True
        self._selected_idx = -1
        self._scroll = 0
        self._dragging = False
        self._resizing = False
        self.color_picker.close()
        self.binding_popup.close()
        self._color_target_key = None
        self._resolve_sample(sample_item)
        self._layout()
        self._rebuild_fields()

    def close(self):
        self.open = False
        self.color_picker.close()
        self.binding_popup.close()

    def _resolve_sample(self, sample_item):
        if callable(sample_item):
            self._sample_provider = sample_item
            try:
                self.sample_item = dict(sample_item() or {})
            except Exception as e:
                print(f"[CardEditor] sample provider falhou: {e}")
                self.sample_item = {}
        else:
            self._sample_provider = None
            self.sample_item = dict(sample_item or {})

    def _refresh_sample(self):
        if self._sample_provider is None:
            return
        try:
            self.sample_item = dict(self._sample_provider() or {})
        except Exception as e:
            print(f"[CardEditor] refresh sample falhou: {e}")

    # -----------------------------------------------------------------
    def _layout(self):
        sfc = pygame.display.get_surface()
        sw, sh = sfc.get_size() if sfc else (1280, 720)
        w = min(sw - 40, 1100)
        h = min(sh - 40, 700)
        self.rect = pygame.Rect(0, 0, w, h)
        self.rect.center = (sw // 2, sh // 2)

        r = self.rect
        p = self.PAD
        body_y = r.y + self.TITLE_H
        body_h = r.height - self.TITLE_H - self.FOOT_H

        self._left_rect = pygame.Rect(r.x + p, body_y, self.LEFT_W, body_h)
        self._right_rect = pygame.Rect(
            r.right - p - self.RIGHT_W, body_y, self.RIGHT_W, body_h)
        self._canvas_rect = pygame.Rect(
            self._left_rect.right + p, body_y,
            self._right_rect.x - self._left_rect.right - p * 2, body_h)

        cw = min(self._canvas_rect.width - 40, 260)
        ch = min(self._canvas_rect.height - 40, 320)
        if cw / ch > 0.85:
            cw = int(ch * 0.85)
        else:
            ch = int(cw / 0.85)
        self._design_rect = pygame.Rect(0, 0, cw, ch)
        self._design_rect.center = self._canvas_rect.center
        self._scale = cw / DESIGN_CARD_W

        bw, bh = 110, 32
        self._cancel_rect = pygame.Rect(
            r.right - p - bw * 2 - 10, r.bottom - self.FOOT_H + 10, bw, bh)
        self._ok_rect = pygame.Rect(
            r.right - p - bw, r.bottom - self.FOOT_H + 10, bw, bh)

        # Botão "Trocar preview" no canto direito do título
        self._refresh_btn = pygame.Rect(
            r.right - p - 140, r.y + 8, 140, 26)

        self._right_clip = pygame.Rect(
            self._right_rect.x + 6, self._right_rect.y + 30,
            self._right_rect.width - 12, self._right_rect.height - 36)

    # -----------------------------------------------------------------
    # Bindings disponíveis (auto-geradas do sample)
    # -----------------------------------------------------------------
    def _available_bindings(self):
        opts = ["(limpar campo)"]
        if self.sample_item:
            for k in sorted(self.sample_item.keys()):
                opts.append("{{item.{}}}".format(k))
        return opts

    # -----------------------------------------------------------------
    def _rebuild_fields(self):
        self._fields = {}
        self._dropdowns = {}
        self._binding_btns = {}
        self._field_order = []
        if not (0 <= self._selected_idx < len(self.card_layout)):
            self._max_scroll = 0
            return

        wdata = self.card_layout[self._selected_idx]
        props = wdata.get("props", {}) or {}

        def _pick(key, default=None):
            if key in wdata and wdata[key] not in (None, ""):
                return wdata[key]
            if key in props and props[key] not in (None, ""):
                return props[key]
            return default

        x0 = self._right_rect.x + 12
        w_ = self._right_rect.width - 100
        field_w = w_ - self.BTN_W - 4
        y = self._right_clip.y - self._scroll

        for key, ftype, label in self.FIELD_DEFS:
            f_rect = pygame.Rect(x0 + 82, y, field_w, 22)
            b_rect = pygame.Rect(f_rect.right + 4, y, self.BTN_W, 22)
            self._binding_btns[key] = b_rect

            if ftype == "choice":
                opts = self.ANCHORS if key == "anchor" else self.TEXT_FIT
                cur = str(_pick(key, opts[0]))
                if cur not in opts:
                    opts = list(opts) + [cur]
                self._dropdowns[key] = EditorDropdown(
                    f_rect, opts, cur,
                    on_change=lambda _v: self._apply_fields())
            elif ftype == "color":
                cur = _pick(key, "")
                if _looks_like_binding(cur):
                    cur_str = str(cur)
                else:
                    cur_str = to_hex(parse_color(cur)) if cur else ""
                self._fields[key] = ColorField(f_rect, cur_str)
            elif ftype == "bool":
                self._fields[key] = BoolField(
                    f_rect, bool(_pick(key, False)))
            elif ftype in ("int", "float"):
                cur = _pick(key, "")
                if cur not in (None, ""):
                    try:
                        txt = str(int(cur) if ftype == "int" else float(cur))
                    except (TypeError, ValueError):
                        txt = str(cur)
                else:
                    txt = ""
                self._fields[key] = TextField(f_rect, txt)
            else:
                cur = _pick(key, "")
                self._fields[key] = TextField(
                    f_rect, str(cur) if cur not in (None, "") else "")

            self._field_order.append((key, ftype, label))
            y += 26

        content_h = len(self._field_order) * 26
        self._max_scroll = max(0, content_h - self._right_clip.height)
        self._scroll = max(0, min(self._scroll, self._max_scroll))
        y = self._right_clip.y - self._scroll
        for key, ftype, _ in self._field_order:
            if key in self._fields:
                self._fields[key].rect.y = y
            if key in self._dropdowns:
                self._dropdowns[key].rect.y = y
            if key in self._binding_btns:
                self._binding_btns[key].y = y
            y += 26

    # -----------------------------------------------------------------
    def _apply_fields(self):
        if not (0 <= self._selected_idx < len(self.card_layout)):
            return
        wdata = self.card_layout[self._selected_idx]
        props = wdata.setdefault("props", {})

        for key, ftype, _ in self._field_order:
            if ftype == "choice":
                dd = self._dropdowns.get(key)
                if dd:
                    if key == "anchor":
                        wdata["anchor"] = dd.value
                    else:
                        props[key] = dd.value
                continue
            f = self._fields.get(key)
            if f is None:
                continue
            raw = f.text.strip()

            if ftype == "color":
                if raw:
                    if _looks_like_binding(raw):
                        wdata[key] = raw           # preserva binding
                    else:
                        c = parse_color(raw, None)
                        if c:
                            wdata[key] = to_hex(c)
                        else:
                            wdata.pop(key, None)
                else:
                    wdata.pop(key, None)
            elif ftype == "bool":
                wdata[key] = bool(f.value)
            elif ftype == "int":
                if raw:
                    try: wdata[key] = int(float(raw))
                    except ValueError: pass
                else:
                    wdata.pop(key, None)
            elif ftype == "float":
                if raw:
                    try: wdata[key] = float(raw)
                    except ValueError: pass
                else:
                    wdata.pop(key, None)
            else:
                if raw: wdata[key] = raw
                else:   wdata.pop(key, None)

    # -----------------------------------------------------------------
    # ColorPicker / BindingPopup
    # -----------------------------------------------------------------
    def _open_color_picker(self, key):
        f = self._fields.get(key)
        if f is None:
            return
        cur = ""
        try:
            cur = str(f.text or "").strip()
        except Exception:
            pass
        if not cur or _looks_like_binding(cur):
            cur = "#FFFFFF"
        self._color_target_key = key
        self.color_picker.open_with(
            cur,
            on_confirm=lambda h, k=key: self._on_color_confirmed(k, h),
            center=self.rect.center)

    def _on_color_confirmed(self, key, hexv):
        f = self._fields.get(key)
        if f is not None:
            try:
                f.text = hexv
            except Exception:
                pass
        self._apply_fields()

    def _open_binding_popup(self, key, anchor_rect):
        self.binding_popup.open_at(
            anchor_rect,
            self._available_bindings(),
            key,
            on_select=self._on_binding_selected)

    def _on_binding_selected(self, key, opt):
        if key is None:
            return
        if opt.startswith("(limpar"):
            new_val = ""
        else:
            new_val = opt
        f = self._fields.get(key)
        if f is not None:
            try:
                f.text = new_val
            except Exception:
                pass
        self._apply_fields()

    # -----------------------------------------------------------------
    # CRUD
    # -----------------------------------------------------------------
    def _add_widget(self, wtype):
        wid = f"{wtype}_{len(self.card_layout) + 1}"
        base = {
            "id": wid, "type": wtype, "z": len(self.card_layout),
            "x": 0.2, "y": 0.2, "w": 0.6, "h": 0.15, "anchor": "tl",
            "props": {},
        }
        if wtype == "panel":
            base.update({
                "fill_color": "#3A4560", "border_color": "#F8B030",
                "border_width": 2, "border_radius": 6,
                "w": 0.8, "h": 0.3,
            })
        elif wtype == "label":
            base.update({
                "font_size": 12, "bold": True, "text_color": "#E8E8D0",
                "props": {"text": "Texto", "align": "center"},
            })
        elif wtype == "image":
            base.update({"w": 0.6, "h": 0.5})
        elif wtype == "badge":
            base.update({
                "font_size": 9, "bold": True,
                "props": {
                    "text": "BADGE",
                    "bg_color": "#F8B030",
                    "badge_text_color": "#1A1A2E",
                    "badge_border_color": "#0A0A14",
                },
            })
        elif wtype == "button":
            base.update({
                "bold": True, "font_size": 11,
                "props": {"label": "OK", "style": "primary"},
            })
        elif wtype == "progress":
            base.update({
                "h": 0.06,
                "props": {
                    "value": 0.5, "max_value": 1, "min_value": 0,
                    "show_text": False,
                    "progress_bg": "#0F0F1E",
                    "color_low": "#E65A5A",
                    "color_mid": "#F8B030",
                    "color_high": "#69DC82",
                },
            })
        elif wtype == "divider":
            base.update({
                "w": 0.8, "h": 0.01,
                "color": "#F8B030", "thickness": 2,
            })
        self.card_layout.append(base)
        self._selected_idx = len(self.card_layout) - 1
        self._rebuild_fields()

    def _delete_selected(self):
        if 0 <= self._selected_idx < len(self.card_layout):
            self.card_layout.pop(self._selected_idx)
            self._selected_idx = min(self._selected_idx,
                                     len(self.card_layout) - 1)
            self._rebuild_fields()

    def _move_selected(self, direction):
        i = self._selected_idx
        j = i + direction
        if not (0 <= i < len(self.card_layout)):
            return
        if not (0 <= j < len(self.card_layout)):
            return
        self.card_layout[i], self.card_layout[j] = \
            self.card_layout[j], self.card_layout[i]
        self._selected_idx = j
        self._rebuild_fields()

    # -----------------------------------------------------------------
    # Coordenadas
    # -----------------------------------------------------------------
    def _cell_to_design(self, wdata):
        return rel_rect(
            pygame.Rect(0, 0, DESIGN_CARD_W, DESIGN_CARD_H),
            wdata.get("x", 0.1), wdata.get("y", 0.1),
            wdata.get("w", 0.2), wdata.get("h", 0.08),
            wdata.get("anchor", "tl"))

    def _design_to_screen(self, r):
        dr = self._design_rect
        s = self._scale
        return pygame.Rect(
            dr.x + int(r.x * s), dr.y + int(r.y * s),
            max(2, int(r.w * s)), max(2, int(r.h * s)))

    def _screen_to_design(self, pos):
        dr = self._design_rect
        s = self._scale
        return ((pos[0] - dr.x) / s, (pos[1] - dr.y) / s)

    def _hit_test(self, design_pos):
        hits = []
        for i, wdata in enumerate(self.card_layout):
            r = self._cell_to_design(wdata)
            if r.collidepoint(design_pos):
                hits.append((int(wdata.get("z", 0)), i))
        if not hits:
            return -1
        hits.sort(reverse=True)
        return hits[0][1]

    def _write_rect(self, idx, new_rect):
        wdata = self.card_layout[idx]
        wdata["x"] = new_rect.x / DESIGN_CARD_W
        wdata["y"] = new_rect.y / DESIGN_CARD_H
        wdata["w"] = new_rect.w / DESIGN_CARD_W
        wdata["h"] = new_rect.h / DESIGN_CARD_H
        wdata["anchor"] = "tl"

    # -----------------------------------------------------------------
    # Eventos
    # -----------------------------------------------------------------
    def handle_event(self, event):
        if not self.open:
            return False

        # ColorPicker tem prioridade máxima
        if self.color_picker.open:
            if self.color_picker.handle_event(event):
                return True

        # BindingPopup em seguida
        if self.binding_popup.open:
            if self.binding_popup.handle_event(event):
                return True

        # Dropdowns abertos
        for d in self._dropdowns.values():
            if d.open:
                if d.handle_event(event):
                    return True

        # Teclado
        if event.type == pygame.KEYDOWN:
            if event.key == pygame.K_ESCAPE:
                self.close(); return True
            if event.key == pygame.K_DELETE:
                self._delete_selected(); return True
            if event.key in (pygame.K_UP, pygame.K_DOWN):
                for f in self._fields.values():
                    if getattr(f, "focused", False):
                        if f.handle_event(event):
                            return True
                self._move_selected(-1 if event.key == pygame.K_UP else 1)
                return True
            for f in self._fields.values():
                if f.handle_event(event):
                    return True
            return True

        # Mouse
        if event.type == pygame.MOUSEMOTION:
            if self._dragging or self._resizing:
                self._on_drag(event.pos)
                return True
            for f in self._fields.values():
                f.handle_event(event)
            for d in self._dropdowns.values():
                d.handle_event(event)
            return True

        if event.type == pygame.MOUSEBUTTONUP and event.button == 1:
            if self._dragging or self._resizing:
                self._dragging = False
                self._resizing = False
                return True
            for f in self._fields.values():
                f.handle_event(event)
            return True

        if event.type == pygame.MOUSEWHEEL:
            mx, my = pygame.mouse.get_pos()
            if self._right_clip.collidepoint(mx, my):
                self._scroll -= event.y * 24
                self._scroll = max(0, min(self._max_scroll, self._scroll))
                self._rebuild_fields()
                return True

        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            pos = event.pos

            if self._refresh_btn.collidepoint(pos):
                self._refresh_sample()
                return True

            if self._ok_rect.collidepoint(pos):
                self._apply_fields()
                if self._on_save:
                    self._on_save(self.card_layout)
                self.close()
                return True
            if self._cancel_rect.collidepoint(pos):
                self.close()
                return True

            if not self.rect.collidepoint(pos):
                self.close()
                return True

            for r, wtype in self._left_add_rects:
                if r.collidepoint(pos):
                    self._apply_fields()
                    self._add_widget(wtype)
                    return True

            for i, r in self._left_item_rects:
                if r.collidepoint(pos):
                    self._apply_fields()
                    self._selected_idx = i
                    self._scroll = 0
                    self._rebuild_fields()
                    return True

            if self._canvas_rect.collidepoint(pos):
                if 0 <= self._selected_idx < len(self.card_layout):
                    sel = self.card_layout[self._selected_idx]
                    sr = self._design_to_screen(self._cell_to_design(sel))
                    handle = pygame.Rect(sr.right - 8, sr.bottom - 8, 14, 14)
                    if handle.collidepoint(pos):
                        self._resizing = True
                        self._drag_start_rect = self._cell_to_design(sel).copy()
                        self._drag_offset = self._screen_to_design(pos)
                        return True

                design = self._screen_to_design(pos)
                idx = self._hit_test(design)
                self._apply_fields()
                self._selected_idx = idx
                self._scroll = 0
                self._rebuild_fields()
                if idx >= 0:
                    self._dragging = True
                    self._drag_start_rect = self._cell_to_design(
                        self.card_layout[idx]).copy()
                    self._drag_offset = design
                return True

            if self._right_clip.collidepoint(pos):
                # 1) Binding button?
                for key, br in self._binding_btns.items():
                    if br.collidepoint(pos):
                        for other in self._fields.values():
                            try: other.focused = False
                            except Exception: pass
                        self._open_binding_popup(key, br)
                        return True

                # 2) Field / dropdown
                for key, ftype, _ in self._field_order:
                    if key in self._fields:
                        f = self._fields[key]
                        r = f.rect
                        sw_r = getattr(f, "swatch_rect", None)
                        if r.collidepoint(pos) or (sw_r and sw_r.collidepoint(pos)):
                            for other in self._fields.values():
                                try: other.focused = False
                                except Exception: pass
                            res = f.handle_event(event)
                            if res == "open_picker":
                                self._open_color_picker(key)
                            return True
                    if key in self._dropdowns:
                        d = self._dropdowns[key]
                        if d.rect.collidepoint(pos):
                            for other in self._fields.values():
                                try: other.focused = False
                                except Exception: pass
                            if d.handle_event(event):
                                self._apply_fields()
                                return True
                return True

        return True

    def _on_drag(self, pos):
        if not (0 <= self._selected_idx < len(self.card_layout)):
            return
        design = self._screen_to_design(pos)
        if self._resizing:
            r = self._drag_start_rect
            new = pygame.Rect(r.x, r.y,
                              max(8, int(design[0] - r.x)),
                              max(6, int(design[1] - r.y)))
            self._write_rect(self._selected_idx, new)
        elif self._dragging:
            dx = design[0] - self._drag_offset[0]
            dy = design[1] - self._drag_offset[1]
            r = self._drag_start_rect
            new = pygame.Rect(int(r.x + dx), int(r.y + dy), r.w, r.h)
            self._write_rect(self._selected_idx, new)
        self._rebuild_fields()

    def fixed_update(self, dt):
        for f in self._fields.values():
            f.update(dt)
        self.color_picker.handle_event  # noqa
        # ColorPicker não tem update()

    # -----------------------------------------------------------------
    # Render
    # -----------------------------------------------------------------
    def render(self, screen):
        if not self.open:
            return
        self._layout()

        ov = pygame.Surface(screen.get_size(), pygame.SRCALPHA)
        ov.fill((0, 0, 0, 180))
        screen.blit(ov, (0, 0))

        pygame.draw.rect(screen, (26, 26, 46), self.rect, border_radius=12)
        pygame.draw.rect(screen, (248, 176, 48), self.rect, 2, border_radius=12)

        t = self._font(18, True).render(
            "EDITOR DE CARD LAYOUT", True, (248, 176, 48))
        screen.blit(t, (self.rect.x + 16, self.rect.y + 12))

        # Botão "Trocar preview"
        hov = self._refresh_btn.collidepoint(pygame.mouse.get_pos())
        bg = (72, 88, 128) if hov else (48, 60, 96)
        pygame.draw.rect(screen, bg, self._refresh_btn, border_radius=6)
        pygame.draw.rect(screen, (80, 104, 152), self._refresh_btn, 1,
                         border_radius=6)
        s = self._font(12, True).render("Trocar preview", True, (232, 232, 208))
        screen.blit(s, s.get_rect(center=self._refresh_btn.center))

        # LEFT
        pygame.draw.rect(screen, (20, 22, 38), self._left_rect, border_radius=8)
        pygame.draw.rect(screen, (80, 104, 152), self._left_rect, 1,
                         border_radius=8)
        lbl = self._font(13, True).render("WIDGETS", True, (248, 200, 88))
        screen.blit(lbl, (self._left_rect.x + 10, self._left_rect.y + 8))

        y = self._left_rect.y + 30
        self._left_item_rects = []
        for i, wdata in enumerate(self.card_layout):
            r = pygame.Rect(self._left_rect.x + 6, y,
                            self._left_rect.width - 12, 22)
            sel = (i == self._selected_idx)
            bg = (72, 88, 128) if sel else (36, 40, 58)
            bd = (248, 176, 48) if sel else (60, 76, 108)
            pygame.draw.rect(screen, bg, r, border_radius=4)
            pygame.draw.rect(screen, bd, r, 1, border_radius=4)
            txt = (f"{i:>2}. z={int(wdata.get('z', 0)):>2}  "
                   f"{wdata.get('id', '?')[:14]}")
            s = self._font(11).render(txt, True, (232, 232, 208))
            screen.blit(s, (r.x + 6, r.centery - s.get_height() // 2))
            self._left_item_rects.append((i, r))
            y += 24

        y_add = max(y + 8, self._left_rect.bottom - 200)
        hdr = self._font(12, True).render("ADICIONAR", True, (248, 200, 88))
        screen.blit(hdr, (self._left_rect.x + 10, y_add - 18))

        self._left_add_rects = []
        pad = 6
        col_w = (self._left_rect.width - pad * 3) // 2
        row_h = 22
        for k, (wtype, label, _) in enumerate(self.ADD_TYPES):
            row = k // 2
            col = k % 2
            r = pygame.Rect(
                self._left_rect.x + pad + col * (col_w + pad),
                y_add + row * (row_h + 4),
                col_w, row_h)
            hover = r.collidepoint(pygame.mouse.get_pos())
            bg = (72, 88, 128) if hover else (40, 48, 68)
            pygame.draw.rect(screen, bg, r, border_radius=4)
            pygame.draw.rect(screen, (80, 104, 152), r, 1, border_radius=4)
            s = self._font(11, True).render(f"+ {label}", True, (232, 232, 208))
            screen.blit(s, (r.centerx - s.get_width() // 2,
                            r.centery - s.get_height() // 2))
            self._left_add_rects.append((r, wtype))

        # CANVAS
        pygame.draw.rect(screen, (12, 14, 24), self._canvas_rect,
                         border_radius=8)
        pygame.draw.rect(screen, (80, 104, 152), self._canvas_rect, 1,
                         border_radius=8)

        # Info do sample no topo do canvas
        sample_name = str(self.sample_item.get("title", "—"))
        sample_rarity = str(self.sample_item.get("rarity_name", ""))
        info = f"Preview: {sample_name}"
        if sample_rarity:
            info += f"  [{sample_rarity}]"
        inf = self._font(11, True).render(info, True, (248, 200, 88))
        screen.blit(inf, (self._canvas_rect.x + 10, self._canvas_rect.y + 6))

        dr = self._design_rect
        pygame.draw.rect(screen, (26, 26, 46), dr)
        for gx in range(1, 4):
            x = dr.x + dr.width * gx // 4
            pygame.draw.line(screen, (60, 76, 108), (x, dr.y), (x, dr.bottom))
        for gy in range(1, 4):
            y = dr.y + dr.height * gy // 4
            pygame.draw.line(screen, (60, 76, 108), (dr.x, y), (dr.right, y))
        pygame.draw.rect(screen, (248, 176, 48), dr, 2)

        for wdata in self.card_layout:
            widget = self._build_preview_widget(wdata)
            if widget is None:
                continue
            try:
                widget.render(screen)
            except Exception as e:
                print(f"[CardEditor] render {wdata.get('id')}: {e}")

        if 0 <= self._selected_idx < len(self.card_layout):
            sel = self.card_layout[self._selected_idx]
            r = self._design_to_screen(self._cell_to_design(sel))
            pygame.draw.rect(screen, (255, 215, 0), r, 2)
            handle = pygame.Rect(r.right - 8, r.bottom - 8, 14, 14)
            pygame.draw.rect(screen, (255, 215, 0), handle, border_radius=2)
            pygame.draw.rect(screen, (60, 40, 10), handle, 1, border_radius=2)

        # RIGHT
        pygame.draw.rect(screen, (20, 22, 38), self._right_rect, border_radius=8)
        pygame.draw.rect(screen, (80, 104, 152), self._right_rect, 1,
                         border_radius=8)
        hdr = self._font(13, True).render("PROPRIEDADES", True, (248, 200, 88))
        screen.blit(hdr, (self._right_rect.x + 10, self._right_rect.y + 8))

        old = screen.get_clip()
        screen.set_clip(self._right_clip)

        if not (0 <= self._selected_idx < len(self.card_layout)):
            s = self._font(12).render("Selecione um widget", True, (150, 160, 180))
            screen.blit(s, (self._right_clip.x + 10, self._right_clip.y + 10))
        else:
            for key, ftype, label in self._field_order:
                lbl_s = self._font(11).render(label, True, (180, 190, 210))
                # label
                if key in self._fields:
                    f = self._fields[key]
                    screen.blit(lbl_s, (self._right_rect.x + 10,
                                        f.rect.centery - lbl_s.get_height() // 2))
                    f.render(screen)
                if key in self._dropdowns:
                    d = self._dropdowns[key]
                    screen.blit(lbl_s, (self._right_rect.x + 10,
                                        d.rect.centery - lbl_s.get_height() // 2))
                    d.render_closed(screen)
                # binding button
                br = self._binding_btns.get(key)
                if br:
                    hov = br.collidepoint(pygame.mouse.get_pos())
                    bg = (72, 88, 128) if hov else (40, 48, 68)
                    bd = (248, 176, 48) if hov else (80, 104, 152)
                    pygame.draw.rect(screen, bg, br, border_radius=4)
                    pygame.draw.rect(screen, bd, br, 1, border_radius=4)
                    bs = self._font(11, True).render("{}", True, (248, 200, 88))
                    screen.blit(bs, (br.centerx - bs.get_width() // 2,
                                     br.centery - bs.get_height() // 2))

        screen.set_clip(old)

        # Botões bottom
        for r, label, base, hovc in (
            (self._cancel_rect, "Cancelar", (110, 55, 55), (150, 75, 75)),
            (self._ok_rect,     "Salvar",   (72, 152, 88), (104, 184, 120)),
        ):
            h = r.collidepoint(pygame.mouse.get_pos())
            pygame.draw.rect(screen, hovc if h else base, r, border_radius=6)
            pygame.draw.rect(screen, (248, 176, 48) if h else (80, 96, 130),
                             r, 2, border_radius=6)
            s = self._font(13, True).render(label, True, (255, 255, 255))
            screen.blit(s, s.get_rect(center=r.center))

        # Dropdowns abertos
        for d in self._dropdowns.values():
            d.render_open_overlay(screen)

        # Binding popup
        self.binding_popup.render(screen)

        # ColorPicker por último (topo)
        self.color_picker.render(screen)

    # -----------------------------------------------------------------
    def _build_preview_widget(self, wdata):
        resolved = resolve_wdata(wdata, self.sample_item or {})
        cell = pygame.Rect(0, 0, DESIGN_CARD_W, DESIGN_CARD_H)
        w = ScreenLoader._build_widget(resolved, cell, {}, None)
        if w is None:
            return None
        w.rect = self._design_to_screen(w.rect)
        vis = wdata.get("visible", True)
        if isinstance(vis, str) and "{item." in vis:
            try:
                vis = resolve_value(vis, self.sample_item or {})
            except Exception:
                vis = True
        w.visible = bool(vis)
        return w