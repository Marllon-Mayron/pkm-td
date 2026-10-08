"""Definicoes de layer (dados puros, parse de JSON)."""
from dataclasses import dataclass, field
from typing import Optional


# =====================================================================
# KEYFRAME (sprite)
# =====================================================================
@dataclass
class Keyframe:
    f: int = 0
    x: float = 0.0
    y: float = 0.0
    rot: float = 0.0
    scale: float = 1.0
    alpha: int = 255
    tint: tuple = (255, 255, 255)
    frame_index: int = -1   # -1 = herda layer.frame_index

    @classmethod
    def from_dict(cls, d: dict) -> "Keyframe":
        return cls(
            f=int(d.get("f", 0)),
            x=float(d.get("x", 0)),
            y=float(d.get("y", 0)),
            rot=float(d.get("rot", 0)),
            scale=float(d.get("scale", 1.0)),
            alpha=int(d.get("alpha", 255)),
            tint=_parse_hex_color(d.get("tint", "#FFFFFF")),
            frame_index=int(d.get("frame_index", -1)),
        )

    def to_dict(self) -> dict:
        out = {
            "f": self.f, "x": self.x, "y": self.y,
            "rot": self.rot, "scale": self.scale,
            "alpha": self.alpha, "tint": _to_hex_color(self.tint),
        }
        if self.frame_index >= 0:
            out["frame_index"] = self.frame_index
        return out

    def copy(self) -> "Keyframe":
        return Keyframe(self.f, self.x, self.y, self.rot,
                        self.scale, self.alpha, tuple(self.tint),
                        self.frame_index)


# =====================================================================
# LAYER BASE
# =====================================================================
@dataclass
class LayerDef:
    id: str = "layer"
    type: str = "sprite"
    z: int = 0
    blend: str = "normal"
    pivot: str = "center"
    offset_x: float = 0.0
    offset_y: float = 0.0
    visible_frames: tuple = (0, -1)
    anchor_actor: str = ""   # segue ator com esse id
    aim_at: str = ""         # "" | "up" | "down" | "left" | "right" | "actor:<id>"

    @classmethod
    def from_dict(cls, d: dict):
        lt = d.get("type", "sprite")
        offset = d.get("offset") or {}
        base = dict(
            id=str(d.get("id", "layer")),
            type=lt,
            z=int(d.get("z", 0)),
            blend=str(d.get("blend", "normal")),
            pivot=str(d.get("pivot", "center")),
            offset_x=float(offset.get("x", 0)),
            offset_y=float(offset.get("y", 0)),
            visible_frames=tuple(d.get("visible_frames", [0, -1])),
            anchor_actor=str(d.get("anchor_actor", "")),
            aim_at=str(d.get("aim_at", "")),
        )

        if lt == "message":
            return MessageLayerDef(
                **base,
                text=str(d.get("text", "")),
                text_speed=float(d.get("text_speed", 28.0)),
                start_delay=int(d.get("start_delay", 0)),
                balloon_style=str(d.get("balloon_style", "firered")),
                balloon_width=int(d.get("balloon_width", 340)),
                balloon_height=int(d.get("balloon_height", 100)),
                balloon_fill=_parse_hex_color(
                    d.get("balloon_fill", "#F8F8F8")),
                balloon_border=_parse_hex_color(
                    d.get("balloon_border", "#303060")),
                balloon_border_w=int(d.get("balloon_border_w", 3)),
                balloon_radius=int(d.get("balloon_radius", 8)),
                balloon_shadow=bool(d.get("balloon_shadow", True)),
                tail=str(d.get("tail", "down")),
                tail_x=float(d.get("tail_x", 0.5)),
                text_color=_parse_hex_color(
                    d.get("text_color", "#282828")),
                font_path=str(d.get("font_path",
                    "pokemon-firered-leafgreen-font-recreation.ttf")),
                font_size=int(d.get("font_size", 22)),
                line_spacing=int(d.get("line_spacing", 4)),
                padding=int(d.get("padding", 12)),
                text_align=str(d.get("text_align", "left")),
                show_prompt=bool(d.get("show_prompt", False)),
                prompt_char=str(d.get("prompt_char", "▼")),
                prompt_blink=bool(d.get("prompt_blink", True)),
            )

        if lt == "sprite":
            return SpriteLayerDef(
                **base,
                image_path=str(d.get("image", "")),
                keyframes=[Keyframe.from_dict(k)
                           for k in d.get("keyframes", [])],
                easing=str(d.get("easing", "linear")),
                flip_x=bool(d.get("flip_x", False)),
                flip_y=bool(d.get("flip_y", False)),
                frame_width=int(d.get("frame_width", 0)),
                frame_height=int(d.get("frame_height", 0)),
                frame_index=int(d.get("frame_index", 0)),
            )
        if lt == "emitter":
            return EmitterLayerDef(
                **base,
                image_path=str(d.get("image", "")),
                emitter_params=dict(d.get("emitter", {})),
            )
        if lt == "filter":
            return FilterLayerDef(
                **base,
                color=_parse_hex_color(d.get("color", "#000000")),
                alpha=int(d.get("alpha", 180)),
                fade_in_frames=int(d.get("fade_in_frames", 0)),
                fade_out_frames=int(d.get("fade_out_frames", 0)),
            )
        if lt == "parallax":
            return ParallaxLayerDef(
                **base,
                image_path=str(d.get("image", "")),
                scroll_speed_x=float(d.get("scroll_speed_x", 20.0)),
                scroll_speed_y=float(d.get("scroll_speed_y", 0.0)),
                repeat_x=bool(d.get("repeat_x", True)),
                repeat_y=bool(d.get("repeat_y", False)),
                alpha=int(d.get("alpha", 255)),
                tint=_parse_hex_color(d.get("tint", "#FFFFFF")),
                stop_scroll_at_frame=int(d.get("stop_scroll_at_frame", -1)),
            )

        return SpriteLayerDef(**base, image_path="", keyframes=[],
                              easing="linear")

    def base_dict(self) -> dict:
        return {
            "id": self.id, "type": self.type, "z": self.z,
            "blend": self.blend, "pivot": self.pivot,
            "offset": {"x": self.offset_x, "y": self.offset_y},
            "visible_frames": list(self.visible_frames),
            "anchor_actor": self.anchor_actor,
            "aim_at": self.aim_at,
        }

    def copy(self):
        return LayerDef.from_dict(self.to_dict())

    def to_dict(self) -> dict:
        raise NotImplementedError


# =====================================================================
# LAYER: SPRITE
# =====================================================================
@dataclass
class SpriteLayerDef(LayerDef):
    image_path: str = ""
    keyframes: list = field(default_factory=list)
    easing: str = "linear"
    flip_x: bool = False
    flip_y: bool = False
    frame_width: int = 0
    frame_height: int = 0
    frame_index: int = 0

    def to_dict(self) -> dict:
        d = self.base_dict()
        d.update({
            "image": self.image_path,
            "keyframes": [k.to_dict() for k in self.keyframes],
            "easing": self.easing,
            "flip_x": self.flip_x,
            "flip_y": self.flip_y,
            "frame_width": self.frame_width,
            "frame_height": self.frame_height,
            "frame_index": self.frame_index,
        })
        return d


# =====================================================================
# LAYER: EMITTER
# =====================================================================
@dataclass
class EmitterLayerDef(LayerDef):
    image_path: str = ""
    emitter_params: dict = field(default_factory=dict)

    def to_dict(self) -> dict:
        d = self.base_dict()
        d.update({"image": self.image_path,
                  "emitter": dict(self.emitter_params)})
        return d


# =====================================================================
# LAYER: FILTER
# =====================================================================
@dataclass
class FilterLayerDef(LayerDef):
    color: tuple = (0, 0, 0)
    alpha: int = 180
    fade_in_frames: int = 0
    fade_out_frames: int = 0

    def to_dict(self) -> dict:
        d = self.base_dict()
        d.update({
            "color": _to_hex_color(self.color),
            "alpha": self.alpha,
            "fade_in_frames": self.fade_in_frames,
            "fade_out_frames": self.fade_out_frames,
        })
        return d


# =====================================================================
# HELPERS DE COR
# =====================================================================
def _parse_hex_color(s) -> tuple:
    if isinstance(s, (tuple, list)) and len(s) >= 3:
        return (int(s[0]), int(s[1]), int(s[2]))
    if not isinstance(s, str):
        return (255, 255, 255)
    s = s.strip().lstrip("#")
    if len(s) == 3:
        s = "".join(c * 2 for c in s)
    if len(s) != 6:
        return (255, 255, 255)
    try:
        return (int(s[0:2], 16), int(s[2:4], 16), int(s[4:6], 16))
    except ValueError:
        return (255, 255, 255)


def _to_hex_color(rgb) -> str:
    r, g, b = int(rgb[0]) & 0xFF, int(rgb[1]) & 0xFF, int(rgb[2]) & 0xFF
    return f"#{r:02X}{g:02X}{b:02X}"

# =====================================================================
# LAYER: MESSAGE (balão de diálogo estilo Pokémon)
# =====================================================================
@dataclass
class MessageLayerDef(LayerDef):
    # ----- Texto -----
    text: str = ""
    text_speed: float = 28.0          # chars por segundo
    start_delay: int = 0              # frames antes de começar a digitar

    # ----- Balão -----
    balloon_style: str = "firered"    # firered | ruby | plain | none
    balloon_width: int = 340
    balloon_height: int = 100
    balloon_fill: tuple = (248, 248, 248)
    balloon_border: tuple = (48, 48, 96)
    balloon_border_w: int = 3
    balloon_radius: int = 8
    balloon_shadow: bool = True

    # ----- Seta (tail) -----
    tail: str = "down"                # none | down | up | left | right
    tail_x: float = 0.5               # 0..1 ao longo da borda

    # ----- Texto -----
    text_color: tuple = (40, 40, 40)
    font_path: str = "pokemon-firered-leafgreen-font-recreation.ttf"
    font_size: int = 22
    line_spacing: int = 4
    padding: int = 12
    text_align: str = "left"          # left | center | right

    # ----- Prompt (▼ piscante) -----
    show_prompt: bool = False
    prompt_char: str = "▼"
    prompt_blink: bool = True

    def __post_init__(self):
        # Normaliza: qualquer "\n" literal vira newline real.
        if self.text:
            self.text = (self.text
                         .replace("\\\\n", "\n")
                         .replace("\\n", "\n"))

    def to_dict(self) -> dict:
        d = self.base_dict()
        d.update({
            "text": self.text,
            "text_speed": self.text_speed,
            "start_delay": self.start_delay,
            "balloon_style": self.balloon_style,
            "balloon_width": self.balloon_width,
            "balloon_height": self.balloon_height,
            "balloon_fill": _to_hex_color(self.balloon_fill),
            "balloon_border": _to_hex_color(self.balloon_border),
            "balloon_border_w": self.balloon_border_w,
            "balloon_radius": self.balloon_radius,
            "balloon_shadow": self.balloon_shadow,
            "tail": self.tail,
            "tail_x": self.tail_x,
            "text_color": _to_hex_color(self.text_color),
            "font_path": self.font_path,
            "font_size": self.font_size,
            "line_spacing": self.line_spacing,
            "padding": self.padding,
            "text_align": self.text_align,
            "show_prompt": self.show_prompt,
            "prompt_char": self.prompt_char,
            "prompt_blink": self.prompt_blink,
        })
        return d

# =====================================================================
# LAYER: PARALLAX
# =====================================================================
@dataclass
class ParallaxLayerDef(LayerDef):
    """Fundo com scroll infinito (parallax).

    A imagem e tiled horizontalmente (e/ou verticalmente) e desloca
    continuamente em `scroll_speed_x` / `scroll_speed_y` pixels por
    segundo. Perfeito para ceu, nuvens, montanhas e canos (Flappy).
    """
    image_path: str = ""
    scroll_speed_x: float = 20.0
    scroll_speed_y: float = 0.0
    repeat_x: bool = True
    repeat_y: bool = False
    alpha: int = 255
    tint: tuple = (255, 255, 255)
    stop_scroll_at_frame: int = -1  # -1 = nunca para

    def to_dict(self) -> dict:
        d = self.base_dict()
        d.update({
            "image": self.image_path,
            "scroll_speed_x": self.scroll_speed_x,
            "scroll_speed_y": self.scroll_speed_y,
            "repeat_x": self.repeat_x,
            "repeat_y": self.repeat_y,
            "alpha": self.alpha,
            "tint": _to_hex_color(self.tint),
            "stop_scroll_at_frame": self.stop_scroll_at_frame,
        })
        return d