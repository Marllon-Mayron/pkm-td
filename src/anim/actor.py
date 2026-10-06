"""Actor — objeto animavel de uma cutscene (pokemon, item, sprite, mock).

Tamanho do sprite:
  - `size_px > 0`: normaliza pelo bounding box REAL do sprite (uniao de
    todos os frames da animacao atual). Todos os pokemons com o mesmo
    `size_px` ficam visualmente do mesmo tamanho, independente do tamanho
    do frame original.
  - `size_px == 0`: usa `display_scale` (comportamento antigo).
"""
from dataclasses import dataclass, field

from src.anim.easing import apply_easing


_MISSING_LOGGED = set()


# =====================================================================
# KEYFRAME DE ATOR
# =====================================================================
@dataclass
class ActorKeyframe:
    f: int = 0
    x: float = 0.0
    y: float = 0.0
    rot: float = 0.0
    scale: float = 1.0
    alpha: int = 255
    anim: str = "idle"
    dir: str = "down"

    @classmethod
    def from_dict(cls, d):
        return cls(
            f=int(d.get("f", 0)),
            x=float(d.get("x", 0)),
            y=float(d.get("y", 0)),
            rot=float(d.get("rot", 0)),
            scale=float(d.get("scale", 1.0)),
            alpha=int(d.get("alpha", 255)),
            anim=str(d.get("anim", "idle")),
            dir=str(d.get("dir", "down")),
        )

    def to_dict(self):
        return {
            "f": self.f, "x": self.x, "y": self.y,
            "rot": self.rot, "scale": self.scale,
            "alpha": self.alpha, "anim": self.anim, "dir": self.dir,
        }

    def copy(self):
        return ActorKeyframe(self.f, self.x, self.y, self.rot,
                             self.scale, self.alpha, self.anim, self.dir)


# =====================================================================
# DEFINICAO DE ATOR
# =====================================================================
@dataclass
class ActorDef:
    id: str = "actor"
    source_type: str = "mock"
    pokemon_id: int = 25
    shiny: bool = False
    default_anim: str = "idle"
    default_dir: str = "down"
    item_id: str = "pokeball"
    sprite_path: str = ""
    mock_color: tuple = (200, 120, 120)
    mock_label: str = "MOCK"

    # ----- Tamanho -----
    # Prioridade:
    #   1. size_px > 0  -> maior lado do SPRITE VISIVEL = size_px
    #   2. display_scale -> maior lado do FRAME = TARGET_BASE * display_scale
    display_scale: float = 2.0
    size_px: int = 0

    z: int = 10
    flip_x: bool = False
    visible_frames: tuple = (0, -1)
    keyframes: list = field(default_factory=list)
    easing: str = "ease_in_out"

    @classmethod
    def from_dict(cls, d):
        mc = d.get("mock_color", [200, 120, 120])
        vf = d.get("visible_frames", [0, -1])
        return cls(
            id=str(d.get("id", "actor")),
            source_type=str(d.get("source_type", "mock")),
            pokemon_id=int(d.get("pokemon_id", 25)),
            shiny=bool(d.get("shiny", False)),
            default_anim=str(d.get("default_anim", "idle")),
            default_dir=str(d.get("default_dir", "down")),
            item_id=str(d.get("item_id", "pokeball")),
            sprite_path=str(d.get("sprite_path", "")),
            mock_color=(tuple(int(x) for x in mc[:3])
                        if mc else (200, 120, 120)),
            mock_label=str(d.get("mock_label", "MOCK")),
            display_scale=float(d.get("display_scale", 2.0)),
            size_px=int(d.get("size_px", 0)),
            z=int(d.get("z", 10)),
            flip_x=bool(d.get("flip_x", False)),
            visible_frames=(int(vf[0]), int(vf[1]))
                            if len(vf) >= 2 else (0, -1),
            keyframes=[ActorKeyframe.from_dict(k)
                       for k in d.get("keyframes", [])],
            easing=str(d.get("easing", "ease_in_out")),
        )

    def to_dict(self):
        return {
            "id": self.id,
            "source_type": self.source_type,
            "pokemon_id": self.pokemon_id,
            "shiny": self.shiny,
            "default_anim": self.default_anim,
            "default_dir": self.default_dir,
            "item_id": self.item_id,
            "sprite_path": self.sprite_path,
            "mock_color": list(self.mock_color),
            "mock_label": self.mock_label,
            "display_scale": self.display_scale,
            "size_px": self.size_px,
            "z": self.z,
            "flip_x": self.flip_x,
            "visible_frames": list(self.visible_frames),
            "keyframes": [k.to_dict() for k in self.keyframes],
            "easing": self.easing,
        }

    def copy(self):
        return ActorDef.from_dict(self.to_dict())

    def sorted_keyframes(self):
        return sorted(self.keyframes, key=lambda k: k.f)

    def keyframe_at(self, frame):
        f = int(frame)
        for kf in self.keyframes:
            if kf.f == f:
                return kf
        return None

    def ensure_keyframe_at(self, frame, defaults=None):
        f = int(frame)
        kf = self.keyframe_at(f)
        if kf is not None:
            return kf
        kf = ActorKeyframe(f=f)
        if defaults:
            for k, v in defaults.items():
                setattr(kf, k, v)
        self.keyframes.append(kf)
        self.keyframes.sort(key=lambda k: k.f)
        return kf

    def remove_keyframe_at(self, frame):
        f = int(frame)
        for i, kf in enumerate(self.keyframes):
            if kf.f == f:
                self.keyframes.pop(i)
                return True
        return False


# =====================================================================
# RUNTIME
# =====================================================================
class ActorRuntime:
    """Instancia viva. Pixel art: escala com nearest neighbor.
    Sem sombra.
    """

    TARGET_BASE = 48

    FALLBACK_ANIMS = ("walk", "idle")
    FALLBACK_DIRS = ("down", "left", "right", "up",
                     "down-left", "down-right", "up-left", "up-right")

    def __init__(self, defn):
        self.defn = defn
        self._frames_cache = {}
        self._durations_cache = {}
        self._bbox_cache = {}

    def invalidate(self):
        self._frames_cache.clear()
        self._durations_cache.clear()
        self._bbox_cache.clear()

    # =================================================================
    # AVALIACAO DE KEYFRAMES
    # =================================================================
    def eval_at(self, frame):
        kfs = self.defn.sorted_keyframes()
        if not kfs:
            return {
                "x": 0.0, "y": 0.0, "rot": 0.0, "scale": 1.0,
                "alpha": 255,
                "anim": self.defn.default_anim,
                "dir": self.defn.default_dir,
            }
        if frame <= kfs[0].f:
            return self._from_kf(kfs[0])
        if frame >= kfs[-1].f:
            return self._from_kf(kfs[-1])
        for i in range(len(kfs) - 1):
            a, b = kfs[i], kfs[i + 1]
            if a.f <= frame <= b.f:
                span = max(1, b.f - a.f)
                t = apply_easing(self.defn.easing, (frame - a.f) / span)
                anim = b.anim if t >= 0.5 else a.anim
                dir_ = b.dir if t >= 0.5 else a.dir
                return {
                    "x": a.x + (b.x - a.x) * t,
                    "y": a.y + (b.y - a.y) * t,
                    "rot": a.rot + (b.rot - a.rot) * t,
                    "scale": a.scale + (b.scale - a.scale) * t,
                    "alpha": int(a.alpha + (b.alpha - a.alpha) * t),
                    "anim": anim,
                    "dir": dir_,
                }
        return self._from_kf(kfs[-1])

    @staticmethod
    def _from_kf(kf):
        return {
            "x": kf.x, "y": kf.y, "rot": kf.rot, "scale": kf.scale,
            "alpha": kf.alpha, "anim": kf.anim, "dir": kf.dir,
        }

    # =================================================================
    # CARREGAMENTO DE FRAMES
    # =================================================================
    def _get_pokemon_frames(self, anim, dir_):
        key = (anim, dir_)
        if key in self._frames_cache:
            return self._frames_cache[key]
        frames = []
        try:
            from src.data.pokedex import Pokedex
            pokedex = Pokedex()
            frames = pokedex.get_animation_frames(
                self.defn.pokemon_id, anim, dir_, self.defn.shiny
            ) or []
        except Exception as e:
            print(f"[ACTOR] frames pokemon #{self.defn.pokemon_id}: {e}")
        self._frames_cache[key] = frames
        return frames

    def _get_pokemon_durations(self, anim):
        if anim in self._durations_cache:
            return self._durations_cache[anim]
        durs = None
        try:
            from src.data.pokedex import Pokedex
            pokedex = Pokedex()
            durs = pokedex.get_animation_durations(
                self.defn.pokemon_id, anim, self.defn.shiny
            )
        except Exception:
            durs = None
        self._durations_cache[anim] = durs
        return durs

    # =================================================================
    # FALLBACK
    # =================================================================
    def _resolve_frames_with_fallback(self, anim, dir_):
        frames = self._get_pokemon_frames(anim, dir_)
        if frames:
            return frames, anim, dir_

        for d in self.FALLBACK_DIRS:
            if d == dir_:
                continue
            frames = self._get_pokemon_frames(anim, d)
            if frames:
                return frames, anim, d

        for alt in self.FALLBACK_ANIMS:
            if alt == anim:
                continue
            frames = self._get_pokemon_frames(alt, dir_)
            if frames:
                return frames, alt, dir_
            for d in self.FALLBACK_DIRS:
                if d == dir_:
                    continue
                frames = self._get_pokemon_frames(alt, d)
                if frames:
                    return frames, alt, d

        return None, anim, dir_

    # =================================================================
    # BOUNDING BOX DO SPRITE
    # =================================================================
    def _get_union_bbox(self, anim, dir_):
        """Retorna (x, y, w, h) da uniao dos bounding boxes de TODOS os
        frames da animacao/direcao. Cacheado.

        Se o sprite for opaco (sem alpha), retorna o frame inteiro.
        """
        key = ("bbox", anim, dir_)
        if key in self._bbox_cache:
            return self._bbox_cache[key]

        import pygame

        frames = self._get_pokemon_frames(anim, dir_)
        if not frames:
            self._bbox_cache[key] = None
            return None

        min_x = 10 ** 9
        min_y = 10 ** 9
        max_x = -1
        max_y = -1

        for surf in frames:
            if surf is None:
                continue
            try:
                mask = pygame.mask.from_surface(surf)
                rects = mask.get_bounding_rects()
            except Exception:
                rects = []
            if not rects:
                # fallback: frame inteiro
                w, h = surf.get_size()
                min_x = min(min_x, 0)
                min_y = min(min_y, 0)
                max_x = max(max_x, w)
                max_y = max(max_y, h)
                continue
            for r in rects:
                min_x = min(min_x, r.x)
                min_y = min(min_y, r.y)
                max_x = max(max_x, r.x + r.w)
                max_y = max(max_y, r.y + r.h)

        if max_x < 0 or max_y < 0:
            self._bbox_cache[key] = None
            return None

        bbox = (min_x, min_y, max_x - min_x, max_y - min_y)
        self._bbox_cache[key] = bbox
        return bbox

    # =================================================================
    # SURFACE
    # =================================================================
    def get_surface(self, anim, dir_, time_seconds):
        src = self.defn.source_type

        if src == "mock":
            return None

        if src == "item":
            try:
                from src.data.item_bag_catalog import item_bag_catalog
                return item_bag_catalog.get_sprite(self.defn.item_id,
                                                   scaled=False)
            except Exception as e:
                print(f"[ACTOR] item '{self.defn.item_id}': {e}")
                return None

        if src == "sprite":
            if not self.defn.sprite_path:
                return None
            try:
                import pygame
                from src.config.paths import RES_PATH
                p = RES_PATH / "animations" / self.defn.sprite_path
                if not p.exists():
                    return None
                img = pygame.image.load(str(p))
                try:
                    img = img.convert_alpha()
                except pygame.error:
                    pass
                return img
            except Exception as e:
                print(f"[ACTOR] sprite '{self.defn.sprite_path}': {e}")
                return None

        if src == "pokemon":
            frames, used_anim, used_dir = self._resolve_frames_with_fallback(
                anim, dir_)

            if not frames:
                key = (self.defn.pokemon_id, anim, dir_)
                if key not in _MISSING_LOGGED:
                    _MISSING_LOGGED.add(key)
                    print(f"[ACTOR] SEM SPRITE: pokemon "
                          f"#{self.defn.pokemon_id} anim='{anim}' "
                          f"dir='{dir_}' — sem fallback disponivel")
                return None

            durs = self._get_pokemon_durations(used_anim)
            if not durs or len(durs) != len(frames):
                durs = [10] * len(frames)

            total = sum(durs)
            if total <= 0:
                return frames[0]

            tick = int(time_seconds * 60.0) % total
            acc = 0
            for i, d in enumerate(durs):
                acc += d
                if tick < acc:
                    return frames[i]
            return frames[-1]

        return None

    # =================================================================
    # RENDER
    # =================================================================
    def render(self, screen, origin_x, origin_y, frame, time_seconds,
               global_zoom=1.0, alpha_mult=1.0):
        import pygame

        props = self.eval_at(frame)
        alpha = int(props["alpha"] * alpha_mult)
        if alpha <= 0:
            return

        x = origin_x + props["x"] * global_zoom
        y = origin_y + props["y"] * global_zoom

        if self.defn.source_type == "mock":
            self._render_mock(screen, x, y, props, alpha, global_zoom)
            return

        surf = self.get_surface(props["anim"], props["dir"], time_seconds)
        if surf is None:
            self._render_missing(screen, x, y, props, alpha, global_zoom)
            return

        w, h = surf.get_size()
        if w <= 0 or h <= 0:
            return

        # ------------------------------------------------------------------
        # Calcula escala base e offset do bbox.
        #
        # size_px > 0  -> normaliza pelo bbox real do sprite.
        # size_px == 0 -> normaliza pelo frame (comportamento antigo).
        # ------------------------------------------------------------------
        size_px = int(getattr(self.defn, "size_px", 0))
        offset_px = (0.0, 0.0)   # deslocamento do bbox em relacao ao centro
                                  # do frame (em coords do frame original)

        if size_px > 0:
            bbox = self._get_union_bbox(props["anim"], props["dir"])
            if bbox is not None and bbox[2] > 0 and bbox[3] > 0:
                bx, by, bw, bh = bbox
                base_scale = size_px / max(bw, bh)

                # Centro do bbox em coords do frame
                bbox_cx = bx + bw / 2.0
                bbox_cy = by + bh / 2.0
                frame_cx = w / 2.0
                frame_cy = h / 2.0
                offset_px = (bbox_cx - frame_cx, bbox_cy - frame_cy)
            else:
                # fallback: frame-based
                base_scale = (self.TARGET_BASE * self.defn.display_scale
                              / max(w, h))
        else:
            base_scale = (self.TARGET_BASE * self.defn.display_scale
                          / max(w, h))

        total = base_scale * props["scale"] * global_zoom

        nw = max(1, int(round(w * total)))
        nh = max(1, int(round(h * total)))

        # Nearest neighbor — pixel art nitida
        img = pygame.transform.scale(surf, (nw, nh))

        if self.defn.flip_x:
            img = pygame.transform.flip(img, True, False)
        if abs(props["rot"]) > 0.1:
            img = pygame.transform.rotozoom(img, -props["rot"], 1.0)
        if alpha < 255:
            img = img.copy()
            img.set_alpha(alpha)

        # Ajusta posicao pra que o centro do bbox caia no centro do ator.
        # (isso tambem compensa o padding do sprite, entao o pokemon
        # fica sempre "de pe" no mesmo ponto, mesmo com frames diferentes)
        ox = offset_px[0] * total * global_zoom if False else offset_px[0] * total
        oy = offset_px[1] * total

        # Se houve rotacao, gira o offset junto
        if abs(props["rot"]) > 0.1:
            import math
            rad = math.radians(props["rot"])
            cos_r, sin_r = math.cos(rad), math.sin(rad)
            ox, oy = (ox * cos_r - oy * sin_r,
                      ox * sin_r + oy * cos_r)

        px = int(round(x - ox))
        py = int(round(y - oy))

        rect = img.get_rect(center=(px, py))
        screen.blit(img, rect.topleft)

    # -----------------------------------------------------------------
    def _render_mock(self, screen, x, y, props, alpha, zoom):
        import pygame
        r = max(8, int(self.TARGET_BASE * self.defn.display_scale
                       * props["scale"] * zoom)) // 2
        col = self.defn.mock_color
        surf = pygame.Surface((r * 2, r * 2), pygame.SRCALPHA)
        pygame.draw.circle(surf, (col[0], col[1], col[2], alpha),
                           (r, r), r, 3)
        pygame.draw.line(surf, (col[0], col[1], col[2], alpha),
                         (r, r - r // 2), (r, r + r // 2), 2)
        pygame.draw.line(surf, (col[0], col[1], col[2], alpha),
                         (r - r // 2, r), (r + r // 2, r), 2)
        screen.blit(surf, (int(x) - r, int(y) - r))

    def _render_missing(self, screen, x, y, props, alpha, zoom):
        import pygame
        from src.ui.theme import FontBook

        w, h = 78, 84
        rect = pygame.Rect(int(x - w // 2), int(y - h // 2), w, h)
        surf = pygame.Surface((w, h), pygame.SRCALPHA)
        surf.fill((80, 20, 80, int(200 * (alpha / 255))))
        pygame.draw.rect(surf, (255, 100, 255, alpha),
                         surf.get_rect(), 2)
        screen.blit(surf, rect.topleft)

        try:
            font = FontBook.get(10, bold=True)
            lines = [
                "MISSING",
                f"pk {self.defn.pokemon_id}",
                props["anim"][:12],
                props["dir"][:12],
            ]
            for i, line in enumerate(lines):
                t = font.render(line, True, (255, 200, 255))
                screen.blit(t, (rect.x + 4, rect.y + 5 + i * 17))
        except Exception:
            pass