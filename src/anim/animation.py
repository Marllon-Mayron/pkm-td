"""AnimDefinition — a 'planta baixa' de uma animacao."""
import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional

from src.anim.layer import LayerDef
from src.anim.actor import ActorDef
from src.anim.camera import CameraDef


SCHEMA_VERSION = 1
VALID_ANCHORS = ("target", "attacker", "projectile", "world", "screen", "mouse")
VALID_SPACES = ("world", "screen")
VALID_CATEGORIES = ("items", "effects", "moves", "weather", "ui", "cutscene")


@dataclass
class AnimDefinition:
    name: str = "nova_animacao"
    category: str = "effects"
    description: str = ""
    fps: int = 60
    duration_frames: int = 90
    loop: bool = False
    loop_count: int = 0
    anchor: str = "target"
    space: str = "world"
    world_offset: tuple = (0, 0)
    screen_offset: tuple = (0, 0)
    sound: Optional[dict] = None
    layers: list = field(default_factory=list)
    actors: list = field(default_factory=list)
    camera: Optional[CameraDef] = None
    default_binding: Optional[dict] = None
    background: Optional[dict] = None

    @property
    def duration_seconds(self) -> float:
        return self.duration_frames / max(1, self.fps)

    # =================================================================
    @classmethod
    def from_json(cls, path) -> "AnimDefinition":
        with open(Path(path), "r", encoding="utf-8") as f:
            return cls.from_dict(json.load(f))

    @classmethod
    def from_dict(cls, data: dict) -> "AnimDefinition":
        wo = data.get("world_offset") or {}
        so = data.get("screen_offset") or {}

        layers = []
        for ld in data.get("layers", []):
            try:
                layers.append(LayerDef.from_dict(ld))
            except Exception as e:
                print(f"[ANIM] erro lendo layer: {e}")

        actors = []
        for ad in data.get("actors", []):
            try:
                actors.append(ActorDef.from_dict(ad))
            except Exception as e:
                print(f"[ANIM] erro lendo actor: {e}")

        cam_raw = data.get("camera")
        camera = CameraDef.from_dict(cam_raw) if cam_raw else None

        return cls(
            name=str(data.get("name", "nova_animacao")),
            category=str(data.get("category", "effects")),
            description=str(data.get("description", "")),
            fps=int(data.get("fps", 60)),
            duration_frames=int(data.get("duration_frames", 90)),
            loop=bool(data.get("loop", False)),
            loop_count=int(data.get("loop_count", 0)),
            anchor=str(data.get("anchor", "target")),
            space=str(data.get("space", "world")),
            world_offset=(int(wo.get("x", 0)), int(wo.get("y", 0))),
            screen_offset=(int(so.get("x", 0)), int(so.get("y", 0))),
            sound=dict(data["sound"]) if data.get("sound") else None,
            layers=layers,
            actors=actors,
            camera=camera,
            default_binding=(dict(data["default_binding"])
                             if data.get("default_binding") else None),
            background=(dict(data["background"])
                        if data.get("background") else None),
        )

    def to_dict(self) -> dict:
        return {
            "schema_version": SCHEMA_VERSION,
            "name": self.name,
            "category": self.category,
            "description": self.description,
            "fps": self.fps,
            "duration_frames": self.duration_frames,
            "loop": self.loop,
            "loop_count": self.loop_count,
            "anchor": self.anchor,
            "space": self.space,
            "world_offset": {"x": self.world_offset[0], "y": self.world_offset[1]},
            "screen_offset": {"x": self.screen_offset[0], "y": self.screen_offset[1]},
            "sound": self.sound,
            "actors": [a.to_dict() for a in self.actors],
            "layers": [l.to_dict() for l in self.layers],
            "camera": self.camera.to_dict() if self.camera else None,
            "default_binding": self.default_binding,
            "background": self.background,
        }

    def save(self, path):
        path = Path(path)
        path.parent.mkdir(parents=True, exist_ok=True)
        with open(path, "w", encoding="utf-8") as f:
            json.dump(self.to_dict(), f, indent=2, ensure_ascii=False)
        print(f"[ANIM] salvo: {path}")

    def copy(self) -> "AnimDefinition":
        return AnimDefinition.from_dict(self.to_dict())

    # =================================================================
    def get_actor(self, actor_id: str):
        for a in self.actors:
            if a.id == actor_id:
                return a
        return None

    def camera_enabled_for_category(self) -> bool:
        """Camera so vale em cutscene e se estiver ligada."""
        if self.category != "cutscene":
            return False
        if self.camera is None or not self.camera.enabled:
            return False
        return True