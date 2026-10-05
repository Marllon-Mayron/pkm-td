# src/ui/screen_loader.py
"""
Carrega layouts JSON e instancia widgets.
Imagens: busca em res/PokemonSprites/UI/ e subpastas (com fallback res/ui/).
Cria placeholders automaticamente se referenciadas e não encontradas.
"""
import inspect
import json
import pygame
from pathlib import Path

from src.config.paths import UI_LAYOUTS_PATH, RES_PATH
from src.ui.layout import rel_rect
from src.ui.theme import parse_color
from src.ui.widgets import (Button, Panel, Label, ListView, ImageBox,
                            Checkbox, Slider, Dropdown, TabPanel)


LAYOUTS_DIR = UI_LAYOUTS_PATH
_MISSING_WARNED = set()

# =====================================================================
# IMAGENS — busca em pastas do jogo
# =====================================================================
# Ordem de prioridade (primeiras vencem):
_UI_IMAGE_DIRS = [
    RES_PATH / "PokemonSprites" / "UI",
    RES_PATH / "ui",
]
_UI_CREATE_DIR = RES_PATH / "PokemonSprites" / "UI"   # onde salvar placeholders

_IMAGE_CACHE = {}
_MISSING_IMAGES_LOGGED = set()


def _image_extensions():
    return (".png", ".jpg", ".jpeg", ".bmp", ".gif")


def _find_image_file(name):
    """
    Procura uma imagem por nome em todas as pastas registradas (recursivo).
    Retorna Path ou None.
    """
    name = str(name).strip().replace("\\", "/")
    if not name:
        return None

    p = Path(name)
    has_ext = p.suffix.lower() in _image_extensions()

    for base in _UI_IMAGE_DIRS:
        if not base.exists():
            continue

        # 1) tentativa exata (respeita subpastas: "Background/foo.png")
        candidate = base / name
        if candidate.is_file():
            return candidate

        # 2) com extensões
        if not has_ext:
            for ext in _image_extensions():
                candidate = base / f"{name}{ext}"
                if candidate.is_file():
                    return candidate

        # 3) busca recursiva só pelo nome do arquivo
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
    """
    Cria um PNG placeholder visível na pasta do jogo.
    Retorna a Surface do placeholder ou None.
    """
    try:
        _UI_CREATE_DIR.mkdir(parents=True, exist_ok=True)
        rel = str(name).strip().replace("\\", "/")
        p = Path(rel)
        # Só garante extensão
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
    """Carrega (com cache) uma imagem. Cria placeholder se pedido."""
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
# CALLBACK HELPERS
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

        # ---- Mapa id -> wdata para resolver parent_id ----
        id_to_wdata = {w.get("id"): w for w in widgets_data if w.get("id")}

        def _depth(w):
            d, p, guard = 0, w.get("parent_id"), 0
            while p and guard < 64:
                d += 1
                guard += 1
                parent = id_to_wdata.get(p)
                if not parent:
                    break
                p = parent.get("parent_id")
            return d

        # ---- Constrói pais antes dos filhos ----
        ordered = sorted(widgets_data, key=_depth)

        # ---- Guarda o content rect de cada widget (para seus filhos) ----
        content_rect_by_id = {}

        for wdata in ordered:
            parent_id = wdata.get("parent_id")
            parent_vp = vp
            if parent_id:
                parent_vp = content_rect_by_id.get(parent_id, vp)

            widget = cls._build_widget(wdata, parent_vp, actions)
            if widget is None:
                continue

            # Calcula o "content rect" para eventuais filhos
            wid = wdata.get("id")
            if wid:
                if wdata.get("type") == "tabpanel":
                    tabs = (wdata.get("props", {}) or {}).get("tabs", [])
                    if tabs:
                        tab_h = max(28, int(widget.rect.height * 0.12))
                        content_rect_by_id[wid] = pygame.Rect(
                            widget.rect.x, widget.rect.y + tab_h,
                            widget.rect.width, widget.rect.height - tab_h)
                    else:
                        content_rect_by_id[wid] = widget.rect
                else:
                    content_rect_by_id[wid] = widget.rect

            scene.add(widget)

    @classmethod
    def _build_widget(cls, wdata, vp, actions):
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

        def pick(key, default=None):
            """Lê de wdata (root) primeiro; se não existir, tenta props."""
            if key in wdata:
                v = wdata[key]
                if v is not None and v != "":
                    return v
            if key in props:
                v = props[key]
                if v is not None and v != "":
                    return v
            return default

        z = int(pick("z", 0))
        fname = pick("font_name", "default")
        fsize = pick("font_size", None)
        bold = bool(pick("bold", False))
        tcol = parse_color(pick("text_color"), None)
        fcol = parse_color(pick("fill_color"), None)
        bcol = parse_color(pick("border_color"), None)
        tabname = pick("tab", None)

        click_snd = _sound_or_none(pick("click_sound"))
        hover_snd = _sound_or_none(pick("hover_sound"))
        click_vol = pick("click_volume", None)
        hover_vol = pick("hover_volume", None)

        # Imagem de fundo
        bg_image_name = pick("bg_image", None)
        bg_image_surf = _load_ui_image(bg_image_name, create_if_missing=True)

        # Ícone
        icon_name = pick("icon", None) or pick("icon_surface", None)
        icon_surf = _load_ui_image(icon_name, create_if_missing=True)

        # Tint
        bg_tint = parse_color(pick("bg_tint"), None)

        # Borda / sombra / modo de imagem / ícone (com fallback)
        bg_image_mode   = pick("bg_image_mode", "stretch")
        bg_image_alpha  = _int_or(pick("bg_image_alpha"), 255)
        border_width    = _int_or(pick("border_width"), 2)
        border_radius   = _int_or(pick("border_radius"), 10)
        draw_border     = _bool_or(pick("draw_border"), True)
        draw_shadow     = _bool_or(pick("draw_shadow"), True)
        icon_position   = pick("icon_position", "left")
        icon_size       = pick("icon_size", None)
        icon_gap        = _int_or(pick("icon_gap"), 6)

        common = dict(
            z=z, font_name=fname, tab=tabname,
            text_color=tcol, fill_color=fcol, border_color=bcol,
            click_sound=click_snd, hover_sound=hover_snd,
            click_volume=click_vol, hover_volume=hover_vol,
        )

        bg_common = dict(
            bg_image=bg_image_surf,
            bg_image_mode=bg_image_mode,
            bg_tint=bg_tint,
            bg_image_alpha=bg_image_alpha,
            border_width=border_width,
            border_radius=border_radius,
            draw_border=draw_border,
            draw_shadow=draw_shadow,
        )

        try:
            if wtype == "button":
                kw = _filter_kwargs(Button, dict(
                    label=props.get("label", "Botão"),
                    style=props.get("style", "primary"),
                    font_size=fsize, bold=bold,
                    icon_surface=icon_surf,
                    icon_size=icon_size,
                    icon_position=icon_position,
                    icon_gap=icon_gap,
                    **bg_common, **common))
                w = Button(wid, rect, **kw)
                cls._bind_action(w, props.get("on_click"), actions, kind="click")

            elif wtype == "panel":
                kw = _filter_kwargs(Panel, dict(
                    title=props.get("title"), bold=bold,
                    **bg_common, **common))
                w = Panel(wid, rect, **kw)

            elif wtype == "label":
                kw = _filter_kwargs(Label, dict(
                    text=props.get("text", "Texto"),
                    size=fsize or props.get("size", 20),
                    bold=bold, align=props.get("align", "center"),
                    **common))
                w = Label(wid, rect, **kw)

            elif wtype == "list":
                kw = _filter_kwargs(ListView, dict(
                    items=props.get("items", []), bold=bold, **common))
                w = ListView(wid, rect, **kw)
                cls._bind_action(w, props.get("on_select"), actions,
                                 kind="select")

            elif wtype == "image":
                kw = _filter_kwargs(ImageBox, dict(
                    surface=icon_surf,
                    bg_image_mode=bg_image_mode,
                    **common))
                w = ImageBox(wid, rect, **kw)

            elif wtype == "checkbox":
                kw = _filter_kwargs(Checkbox, dict(
                    label=props.get("label", ""),
                    checked=props.get("checked", False),
                    bold=bold, **common))
                w = Checkbox(wid, rect, **kw)
                cls._bind_action(w, props.get("on_toggle"), actions,
                                 kind="toggle")

            elif wtype == "slider":
                kw = _filter_kwargs(Slider, dict(
                    value=props.get("value", 0.5),
                    min_val=props.get("min", 0.0),
                    max_val=props.get("max", 1.0), **common))
                w = Slider(wid, rect, **kw)
                cls._bind_action(w, props.get("on_change"), actions,
                                 kind="change")

            elif wtype == "dropdown":
                kw = _filter_kwargs(Dropdown, dict(
                    options=props.get("options", ["-"]),
                    value=props.get("value"), bold=bold, **common))
                w = Dropdown(wid, rect, **kw)
                cls._bind_action(w, props.get("on_change"), actions,
                                 kind="change")

            elif wtype == "tabpanel":
                kw = _filter_kwargs(TabPanel, dict(
                    tabs=props.get("tabs", ["Tab 1"]),
                    current_tab=props.get("current_tab"),
                    bold=bold, **common))
                w = TabPanel(wid, rect, **kw)
                cls._bind_action(w, props.get("on_change"), actions,
                                 kind="change")

            else:
                print(f"[UI] tipo desconhecido: {wtype}")
                return None
        except Exception as e:
            print(f"[UI] erro criando {wid}: {e}")
            return None

        if click_snd is None and hasattr(w, "click_sound"):
            raw = pick("click_sound")
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
        """Lista imagens (nome relativo) em todas as pastas de UI."""
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
        """Cria placeholder e retorna o nome salvo (relativo)."""
        surf = _create_placeholder_image(name)
        return str(name) if surf is not None else None