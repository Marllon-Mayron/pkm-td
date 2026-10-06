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