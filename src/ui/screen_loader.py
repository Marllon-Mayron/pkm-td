# src/ui/screen_loader.py
"""
Carrega layouts JSON e instancia widgets.
Suporta: parent-child (content rect), padding, alpha, border_sides,
         ProgressBar, Badge, WorldSprite, ListView com render_callback,
         pixel_art (nearest vs bilinear).

Leitura de props: prioriza o WIDGET (top-level), com fallback para props{}.
Isso mantém compatibilidade com o editor visual que salva no widget.
"""
import inspect
import json
import pygame
from pathlib import Path

from src.config.paths import UI_LAYOUTS_PATH, RES_PATH
from src.ui.layout import rel_rect
from src.ui.theme import parse_color, with_alpha, color_alpha
from src.ui.widgets import (
    Button, Panel, Label, ListView, ImageBox, Checkbox, Slider,
    Dropdown, TabPanel, ProgressBar, Badge, WorldSprite, GridSelect,
)


LAYOUTS_DIR = UI_LAYOUTS_PATH
_MISSING_WARNED = set()

# =====================================================================
# IMAGENS
# =====================================================================
_UI_IMAGE_DIRS = [
    RES_PATH / "PokemonSprites" / "UI",
    RES_PATH / "ui",
]
_UI_CREATE_DIR = RES_PATH / "PokemonSprites" / "UI"
_IMAGE_CACHE = {}
_MISSING_IMAGES_LOGGED = set()


def _image_extensions():
    return (".png", ".jpg", ".jpeg", ".bmp", ".gif")


def _find_image_file(name):
    name = str(name).strip().replace("\\", "/")
    if not name:
        return None
    p = Path(name)
    has_ext = p.suffix.lower() in _image_extensions()
    for base in _UI_IMAGE_DIRS:
        if not base.exists():
            continue
        candidate = base / name
        if candidate.is_file():
            return candidate
        if not has_ext:
            for ext in _image_extensions():
                candidate = base / f"{name}{ext}"
                if candidate.is_file():
                    return candidate
        target = p.name if has_ext else None
        if target:
            for found in base.rglob(target):
                if found.is_file():
                    return found
        else:
            for ext in _image_extensions():
                for found in base.rglob(f"{p.name}{ext}"):
                    if found.is_file():
                        return found
    return None


def _create_placeholder_image(name):
    try:
        _UI_CREATE_DIR.mkdir(parents=True, exist_ok=True)
        rel = str(name).strip().replace("\\", "/")
        p = Path(rel)
        if p.suffix.lower() not in _image_extensions():
            p = p.with_suffix(".png")
        out_path = _UI_CREATE_DIR / p
        surf = pygame.Surface((128, 128), pygame.SRCALPHA)
        surf.fill((230, 90, 160, 220))
        pygame.draw.rect(surf, (255, 255, 255, 255), surf.get_rect(), 3)
        pygame.draw.line(surf, (255, 255, 255, 255), (0, 0), (128, 128), 2)
        pygame.draw.line(surf, (255, 255, 255, 255), (128, 0), (0, 128), 2)
        try:
            font = pygame.font.Font(None, 16)
            label = p.stem[:18]
            txt = font.render(label, True, (255, 255, 255))
            surf.blit(txt, (6, 6))
            txt2 = font.render("(placeholder)", True, (255, 255, 255))
            surf.blit(txt2, (6, 108))
        except Exception:
            pass
        out_path.parent.mkdir(parents=True, exist_ok=True)
        pygame.image.save(surf, str(out_path))
        print(f"[UI] placeholder criado: {out_path}")
        return surf
    except Exception as e:
        print(f"[UI] erro ao criar placeholder {name!r}: {e}")
        return None


def _load_ui_image(name, create_if_missing=False):
    if not name:
        return None
    key = str(name).strip()
    if key in _IMAGE_CACHE:
        return _IMAGE_CACHE[key]
    found = _find_image_file(key)
    if found is not None:
        try:
            surf = pygame.image.load(str(found)).convert_alpha()
            _IMAGE_CACHE[key] = surf
            return surf
        except Exception as e:
            print(f"[UI] erro ao carregar {found}: {e}")
    if create_if_missing:
        surf = _create_placeholder_image(key)
        _IMAGE_CACHE[key] = surf
        return surf
    if key not in _MISSING_IMAGES_LOGGED:
        _MISSING_IMAGES_LOGGED.add(key)
        print(f"[UI] imagem não encontrada: {key!r}")
    _IMAGE_CACHE[key] = None
    return None


def clear_image_cache():
    _IMAGE_CACHE.clear()


# =====================================================================
# HELPERS
# =====================================================================
def _wrap_callback(fn):
    try:
        sig = inspect.signature(fn)
        npos = len([p for p in sig.parameters.values()
                    if p.kind in (p.POSITIONAL_ONLY, p.POSITIONAL_OR_KEYWORD)])
        if npos == 0:
            return lambda *a, **k: fn()
        return fn
    except (ValueError, TypeError):
        return fn


def _filter_kwargs(cls, kwargs):
    try:
        sig = inspect.signature(cls.__init__)
    except (ValueError, TypeError):
        return kwargs
    ok = {p.name for p in sig.parameters.values()
          if p.kind in (p.POSITIONAL_OR_KEYWORD, p.KEYWORD_ONLY)}
    return {k: v for k, v in kwargs.items() if k in ok}


def _make_missing_stub(action_name):
    def stub(*args, **kwargs):
        if action_name not in _MISSING_WARNED:
            _MISSING_WARNED.add(action_name)
            print(f"[UI] ação não encontrada (stub): {action_name!r}")
    return stub


def _sound_or_none(v):
    if not v:
        return None
    s = str(v).strip()
    if s.upper() in ("NONE", "(NENHUM)", "(NONE)", "-", ""):
        return None
    return s


def _int_or(v, default):
    try:
        return int(float(v))
    except (TypeError, ValueError):
        return default


def _float_or(v, default):
    try:
        return float(v)
    except (TypeError, ValueError):
        return default


def _bool_or(v, default):
    if v is None:
        return default
    if isinstance(v, bool):
        return v
    s = str(v).strip().lower()
    if s in ("1", "true", "yes", "on", "sim"):
        return True
    if s in ("0", "false", "no", "off", "nao", "não"):
        return False
    return default


# =====================================================================
# LOADER
# =====================================================================
class ScreenLoader:
    @classmethod
    def load(cls, scene, path):
        p = Path(path)
        if not p.is_absolute():
            p2 = LAYOUTS_DIR / (p.name if p.suffix == ".json"
                                else f"{p.name}.json")
            if p2.exists():
                p = p2
            else:
                from src.config.paths import PROJECT_ROOT
                p = PROJECT_ROOT / path
        if not p.exists():
            print(f"[UI] layout não encontrado: {p}")
            return None
        with open(p, "r", encoding="utf-8") as f:
            data = json.load(f)
        cls.apply(scene, data)
        return data

    @classmethod
    def apply(cls, scene, data):
        vp = getattr(scene, "vp", None)
        if vp is None:
            print("[UI] cena sem `.vp` — use StandardScreen")
            return
        actions = {}
        if hasattr(scene, "get_actions"):
            try:
                actions = scene.get_actions() or {}
            except Exception as e:
                print(f"[UI] erro em get_actions(): {e}")

        widgets_data = data.get("widgets", [])
        if not widgets_data:
            return

        id_to_wdata = {w.get("id"): w for w in widgets_data if w.get("id")}

        def _depth(w):
            d, p, guard = 0, w.get("parent_id"), 0
            while p and guard < 64:
                d += 1; guard += 1
                parent = id_to_wdata.get(p)
                if not parent:
                    break
                p = parent.get("parent_id")
            return d

        ordered = sorted(widgets_data, key=_depth)
        content_rect_by_id = {}

        for wdata in ordered:
            parent_id = wdata.get("parent_id")
            parent_vp = vp
            if parent_id:
                parent_vp = content_rect_by_id.get(parent_id, vp)

            widget = cls._build_widget(wdata, parent_vp, actions, scene)
            if widget is None:
                continue

            wid = wdata.get("id")
            if wid:
                props = wdata.get("props", {}) or {}

                def _pick(key, default=None):
                    if key in wdata:
                        v = wdata[key]
                        if v is not None and v != "":
                            return v
                    if key in props:
                        v = props[key]
                        if v is not None and v != "":
                            return v
                    return default

                pad = _int_or(_pick("padding"), 0)
                if wdata.get("type") == "tabpanel":
                    tabs = props.get("tabs", []) or []
                    if tabs:
                        tab_h = max(28, int(widget.rect.height * 0.12))
                        base = pygame.Rect(widget.rect.x,
                                           widget.rect.y + tab_h,
                                           widget.rect.width,
                                           widget.rect.height - tab_h)
                    else:
                        base = widget.rect
                else:
                    base = widget.rect
                if pad > 0:
                    base = base.inflate(-pad * 2, -pad * 2)
                content_rect_by_id[wid] = base

            scene.add(widget)

    # -----------------------------------------------------------------
    @classmethod
    def _build_widget(cls, wdata, vp, actions, scene=None):
        wtype = str(wdata.get("type", "button")).lower()
        wid = wdata.get("id") or f"{wtype}_{id(wdata)}"
        rect = rel_rect(
            vp,
            float(wdata.get("x", 0.1)),
            float(wdata.get("y", 0.1)),
            float(wdata.get("w", 0.2)),
            float(wdata.get("h", 0.08)),
            wdata.get("anchor", "tl"),
        )
        props = dict(wdata.get("props", {}))

        def _get(key, default=None):
            if key in wdata:
                v = wdata[key]
                if v is not None and v != "":
                    return v
            if key in props:
                v = props[key]
                if v is not None and v != "":
                    return v
            return default

        # --- comuns ---
        z = int(wdata.get("z", 0))
        fname = _get("font_name", "default")
        fsize = _get("font_size")
        bold = bool(_get("bold", False))
        tcol = parse_color(_get("text_color"))
        fcol = parse_color(_get("fill_color"))
        bcol = parse_color(_get("border_color"))
        tabname = _get("tab")

        f_alpha = _int_or(_get("fill_alpha"), 255)
        b_alpha = _int_or(_get("border_alpha"), 255)
        pixel_art = _bool_or(_get("pixel_art"), True)

        click_snd = _sound_or_none(_get("click_sound"))
        hover_snd = _sound_or_none(_get("hover_sound"))
        click_vol = _get("click_volume")
        hover_vol = _get("hover_volume")

        # --- imagens ---
        bg_image_name = _get("bg_image")
        bg_image_surf = _load_ui_image(bg_image_name, create_if_missing=True)

        icon_name = _get("icon") or _get("icon_surface")
        icon_surf = _load_ui_image(icon_name, create_if_missing=True)

        bg_tint = parse_color(_get("bg_tint"), None)

        common = dict(
            z=z, font_name=fname, tab=tabname,
            text_color=tcol, fill_color=fcol, border_color=bcol,
            fill_alpha=f_alpha, border_alpha=b_alpha,
            click_sound=click_snd, hover_sound=hover_snd,
            click_volume=click_vol, hover_volume=hover_vol,
        )

        bg_common = dict(
            bg_image=bg_image_surf,
            bg_image_mode=_get("bg_image_mode", "stretch"),
            bg_tint=bg_tint,
            bg_image_alpha=_int_or(_get("bg_image_alpha"), 255),
            border_width=_int_or(_get("border_width"), 2),
            border_radius=_int_or(_get("border_radius"), 10),
            draw_border=_bool_or(_get("draw_border"), True),
            draw_shadow=_bool_or(_get("draw_shadow"), True),
            pixel_art=pixel_art,
        )

        try:
            if wtype == "button":
                kw = _filter_kwargs(Button, dict(
                    label=_get("label", "Botão"),
                    style=_get("style", "primary"),
                    font_size=fsize, bold=bold,
                    icon_surface=icon_surf,
                    icon_size=_get("icon_size"),
                    icon_position=_get("icon_position", "left"),
                    icon_gap=_int_or(_get("icon_gap"), 6),
                    **bg_common, **common))
                w = Button(wid, rect, **kw)
                cls._bind_action(w, props.get("on_click"), actions,
                                 kind="click")

            elif wtype == "panel":
                kw = _filter_kwargs(Panel, dict(
                    title=_get("title"),
                    title_font_size=_int_or(_get("title_font_size"), None),
                    bold=bold,
                    padding=_int_or(_get("padding"), 0),
                    border_sides=_get("border_sides"),
                    **bg_common, **common))
                w = Panel(wid, rect, **kw)

            elif wtype == "label":
                kw = _filter_kwargs(Label, dict(
                    text=_get("text", "Texto"),
                    size=fsize or _get("size", 20),
                    bold=bold,
                    align=_get("align", "center"),
                    **common))
                w = Label(wid, rect, **kw)

            elif wtype == "list":
                kw = _filter_kwargs(ListView, dict(
                    items=_get("items", []),
                    bold=bold,
                    **common))
                w = ListView(wid, rect, **kw)
                cls._bind_action(w, props.get("on_select"), actions,
                                 kind="select")

            elif wtype == "image":
                kw = _filter_kwargs(ImageBox, dict(
                    surface=icon_surf,
                    bg_image_mode=_get("bg_image_mode", "contain"),
                    pixel_art=pixel_art,
                    **common))
                w = ImageBox(wid, rect, **kw)

            elif wtype == "world_sprite":
                kw = _filter_kwargs(WorldSprite, dict(
                    surface=icon_surf,
                    world_x=_float_or(_get("world_x"), 0.0),
                    world_y=_float_or(_get("world_y"), 0.0),
                    max_size=_int_or(_get("max_size"), 130),
                    pixel_art=pixel_art,
                    screen_manager=scene.screen_manager if scene else None,
                    game=getattr(scene, "game", None) if scene else None,
                    z=z, tab=tabname,
                ))
                w = WorldSprite(wid, rect, **kw)

            elif wtype == "checkbox":
                kw = _filter_kwargs(Checkbox, dict(
                    label=_get("label", ""),
                    checked=_get("checked", False),
                    bold=bold,
                    **common))
                w = Checkbox(wid, rect, **kw)
                cls._bind_action(w, props.get("on_toggle"), actions,
                                 kind="toggle")

            elif wtype == "slider":
                kw = _filter_kwargs(Slider, dict(
                    value=_float_or(_get("value"), 0.5),
                    min_val=_float_or(_get("min"), 0.0),
                    max_val=_float_or(_get("max"), 1.0),
                    **common))
                w = Slider(wid, rect, **kw)
                cls._bind_action(w, props.get("on_change"), actions,
                                 kind="change")

            elif wtype == "dropdown":
                kw = _filter_kwargs(Dropdown, dict(
                    options=_get("options", ["-"]),
                    value=_get("value"),
                    bold=bold,
                    **common))
                w = Dropdown(wid, rect, **kw)
                cls._bind_action(w, props.get("on_change"), actions,
                                 kind="change")

            elif wtype == "tabpanel":
                kw = _filter_kwargs(TabPanel, dict(
                    tabs=_get("tabs", ["Tab 1"]),
                    current_tab=_get("current_tab"),
                    bold=bold,
                    **common))
                w = TabPanel(wid, rect, **kw)
                cls._bind_action(w, props.get("on_change"), actions,
                                 kind="change")

            elif wtype == "grid":
                kw = _filter_kwargs(GridSelect, dict(
                    items=_get("items", []),
                    cols=_int_or(_get("cols"), 2),
                    rows=_int_or(_get("rows"), 2),
                    cell_gap=_int_or(_get("cell_gap"), 8),
                    bold=bold,
                    **common))
                w = GridSelect(wid, rect, **kw)
                cls._bind_action(w, props.get("on_select"), actions,
                                 kind="select")
                
            elif wtype == "progress":
                radius_v = _get("radius")
                kw = _filter_kwargs(ProgressBar, dict(
                    value=_float_or(_get("value"), 0.5),
                    max_value=_float_or(_get("max_value"), 1.0),
                    min_value=_float_or(_get("min_value"), 0.0),
                    bg_color=parse_color(_get("progress_bg"), None),
                    color_low=parse_color(_get("color_low"), None),
                    color_mid=parse_color(_get("color_mid"), None),
                    color_high=parse_color(_get("color_high"), None),
                    border_color=bcol,
                    show_text=_bool_or(_get("show_text"), True),
                    text_format=_get("text_format", "{value}/{max}"),
                    font_name=fname, text_color=tcol, tab=tabname,
                    radius=_int_or(radius_v, None) if radius_v is not None else None,
                    z=z,
                ))
                w = ProgressBar(wid, rect, **kw)

            elif wtype == "badge":
                kw = _filter_kwargs(Badge, dict(
                    text=_get("text", ""),
                    bg_color=parse_color(_get("bg_color"), None),
                    text_color=parse_color(_get("badge_text_color"), None) or tcol,
                    border_color=parse_color(_get("badge_border_color"), None),
                    font_name=fname, bold=bold,
                    font_size=fsize,
                    tab=tabname, z=z,
                ))
                w = Badge(wid, rect, **kw)

            else:
                print(f"[UI] tipo desconhecido: {wtype}")
                return None
        except Exception as e:
            print(f"[UI] erro criando {wid}: {e}")
            return None

        if click_snd is None and hasattr(w, "click_sound"):
            raw = _get("click_sound")
            if raw is not None and _sound_or_none(raw) is None:
                w.click_sound = None

        w.visible = wdata.get("visible", True)
        w.enabled = wdata.get("enabled", True)
        return w

    @classmethod
    def _bind_action(cls, widget, action_name, actions, kind="click"):
        attr = {"click": "on_click", "toggle": "on_toggle",
                "change": "on_change", "select": "on_select"}[kind]
        if not action_name:
            return
        fn = actions.get(action_name)
        if fn is None:
            setattr(widget, attr, _make_missing_stub(action_name))
            return
        setattr(widget, attr, _wrap_callback(fn))

    @classmethod
    def save(cls, data, path):
        p = Path(path)
        if not p.is_absolute():
            p = LAYOUTS_DIR / (p.name if p.suffix == ".json"
                               else f"{p.name}.json")
        p.parent.mkdir(parents=True, exist_ok=True)
        with open(p, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
        print(f"[UI] layout salvo: {p}")

    @classmethod
    def list_layouts(cls):
        if not LAYOUTS_DIR.exists():
            return []
        return sorted(p.stem for p in LAYOUTS_DIR.glob("*.json"))

    @classmethod
    def list_images(cls):
        out = set()
        for base in _UI_IMAGE_DIRS:
            if not base.exists():
                continue
            for ext in _image_extensions():
                for p in base.rglob(f"*{ext}"):
                    if p.is_file():
                        try:
                            rel = p.relative_to(base)
                            out.add(str(rel).replace("\\", "/"))
                        except Exception:
                            out.add(p.name)
        return sorted(out)

    @classmethod
    def create_image_placeholder(cls, name):
        surf = _create_placeholder_image(name)
        return str(name) if surf is not None else None