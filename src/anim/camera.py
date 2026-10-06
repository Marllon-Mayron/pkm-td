"""Camera — offset + zoom + shake animaveis por keyframes.

FERRAMENTA EXCLUSIVA DE CUTSCENE.

O Animator so instancia um CameraRuntime se `AnimDefinition.category
== "cutscene"` E `camera.enabled == True`. Em qualquer outra categoria,
o campo e ignorado por completo — efeitos, moves, itens e weather
continuam ancorados no mundo como sempre.
"""
from dataclasses import dataclass, field

from src.anim.easing import apply_easing


# =====================================================================
# KEYFRAME DA CAMERA
# =====================================================================
@dataclass
class CameraKeyframe:
    f: int = 0
    x: float = 0.0
    y: float = 0.0
    zoom: float = 1.0

    @classmethod
    def from_dict(cls, d):
        return cls(
            f=int(d.get("f", 0)),
            x=float(d.get("x", 0)),
            y=float(d.get("y", 0)),
            zoom=float(d.get("zoom", 1.0)),
        )

    def to_dict(self):
        return {"f": self.f, "x": self.x, "y": self.y, "zoom": self.zoom}

    def copy(self):
        return CameraKeyframe(self.f, self.x, self.y, self.zoom)


# =====================================================================
# SHAKE DA CAMERA
# =====================================================================
@dataclass
class CameraShake:
    """Tremor aplicado entre f_start e f_end (frames inclusos).

    O envelope sobe nos primeiros 15% e cai nos ultimos 15% — sem
    entrada/saida abruptas. Ambas as ondas (x e y) rodam em frequencias
    levemente diferentes pra nao ficar com padrao visual.
    """
    f_start: int = 0
    f_end: int = 0
    amplitude: float = 6.0
    frequency: float = 25.0

    @classmethod
    def from_dict(cls, d):
        return cls(
            f_start=int(d.get("f_start", d.get("f", 0))),
            f_end=int(d.get("f_end", d.get("f", 0))),
            amplitude=float(d.get("amplitude", 6.0)),
            frequency=float(d.get("frequency", 25.0)),
        )

    def to_dict(self):
        return {
            "f_start": self.f_start,
            "f_end": self.f_end,
            "amplitude": self.amplitude,
            "frequency": self.frequency,
        }

    def copy(self):
        return CameraShake(self.f_start, self.f_end,
                           self.amplitude, self.frequency)


# =====================================================================
# DEFINICAO
# =====================================================================
@dataclass
class CameraDef:
    enabled: bool = False
    x: float = 0.0
    y: float = 0.0
    zoom: float = 1.0
    easing: str = "ease_in_out"
    follow: str = ""            # id de ator (reservado p/ uso futuro)
    keyframes: list = field(default_factory=list)
    shakes: list = field(default_factory=list)

    @classmethod
    def from_dict(cls, d):
        return cls(
            enabled=bool(d.get("enabled", False)),
            x=float(d.get("x", 0.0)),
            y=float(d.get("y", 0.0)),
            zoom=float(d.get("zoom", 1.0)),
            easing=str(d.get("easing", "ease_in_out")),
            follow=str(d.get("follow", "")),
            keyframes=[CameraKeyframe.from_dict(k)
                       for k in d.get("keyframes", [])],
            shakes=[CameraShake.from_dict(k)
                    for k in d.get("shakes", [])],
        )

    def to_dict(self):
        return {
            "enabled": self.enabled,
            "x": self.x,
            "y": self.y,
            "zoom": self.zoom,
            "easing": self.easing,
            "follow": self.follow,
            "keyframes": [k.to_dict() for k in self.keyframes],
            "shakes": [k.to_dict() for k in self.shakes],
        }

    def copy(self):
        return CameraDef.from_dict(self.to_dict())

    # -----------------------------------------------------------------
    def sorted_keyframes(self):
        return sorted(self.keyframes, key=lambda k: k.f)

    def keyframe_at(self, frame: int):
        f = int(frame)
        for kf in self.keyframes:
            if kf.f == f:
                return kf
        return None

    def ensure_keyframe_at(self, frame: int, defaults=None) -> CameraKeyframe:
        f = int(frame)
        kf = self.keyframe_at(f)
        if kf is not None:
            return kf
        kf = CameraKeyframe(f=f)
        if defaults:
            for k, v in defaults.items():
                setattr(kf, k, v)
        self.keyframes.append(kf)
        self.keyframes.sort(key=lambda k: k.f)
        return kf

    def remove_keyframe_at(self, frame: int) -> bool:
        f = int(frame)
        for i, kf in enumerate(self.keyframes):
            if kf.f == f:
                self.keyframes.pop(i)
                return True
        return False


# =====================================================================
# RUNTIME
# =====================================================================
class CameraRuntime:
    """Avalia a camera em qualquer frame. Nao tem estado mutavel —
    e uma funcao pura (frame -> estado). Isso permite reavaliar em
    qualquer momento sem sincronizacao.
    """

    def __init__(self, defn: CameraDef):
        self.defn = defn

    def eval_at(self, frame: float) -> dict:
        base = self._interp_base(frame)
        sx, sy = self._eval_shake(frame)
        return {
            "x": base["x"] + sx,
            "y": base["y"] + sy,
            "zoom": max(0.05, base["zoom"]),
        }

    # -----------------------------------------------------------------
    def _interp_base(self, frame: float) -> dict:
        kfs = self.defn.sorted_keyframes()
        if not kfs:
            return {
                "x": self.defn.x,
                "y": self.defn.y,
                "zoom": self.defn.zoom,
            }
        if frame <= kfs[0].f:
            k = kfs[0]
            return {"x": k.x, "y": k.y, "zoom": k.zoom}
        if frame >= kfs[-1].f:
            k = kfs[-1]
            return {"x": k.x, "y": k.y, "zoom": k.zoom}

        for i in range(len(kfs) - 1):
            a, b = kfs[i], kfs[i + 1]
            if a.f <= frame <= b.f:
                span = max(1, b.f - a.f)
                t = apply_easing(self.defn.easing, (frame - a.f) / span)
                return {
                    "x": a.x + (b.x - a.x) * t,
                    "y": a.y + (b.y - a.y) * t,
                    "zoom": a.zoom + (b.zoom - a.zoom) * t,
                }
        k = kfs[-1]
        return {"x": k.x, "y": k.y, "zoom": k.zoom}

    # -----------------------------------------------------------------
    def _eval_shake(self, frame: float) -> tuple:
        import math
        sx, sy = 0.0, 0.0
        for sh in self.defn.shakes:
            if not (sh.f_start <= frame <= sh.f_end):
                continue
            total = max(1, sh.f_end - sh.f_start)
            prog = (frame - sh.f_start) / total
            if prog < 0.15:
                env = prog / 0.15
            elif prog > 0.85:
                env = (1.0 - prog) / 0.15
            else:
                env = 1.0
            env = max(0.0, min(1.0, env))
            t = frame / 60.0
            amp = sh.amplitude * env
            sx += math.sin(t * sh.frequency * math.tau) * amp
            sy += math.cos(t * sh.frequency * math.tau * 0.8) * amp * 0.7
        return sx, sy