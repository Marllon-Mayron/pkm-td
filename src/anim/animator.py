"""Animator — instancia rodando de uma animacao.

Regras:
  - Camera so ativa em `category == "cutscene"`.
  - Atores renderizam com nearest neighbor (pixel art).
  - Layers seguem `anchor_actor` (ator) ou `aim_at` (direcao/alvo).
  - Filtros ignoram camera (sempre cobrem viewport).
  - `hidden_actors` permite ao editor esconder atores sem afeta-los.
  - `scale_mult` no AnimDefinition multiplica TODAS as layers (sprite+offset).
  - `anchor_mode` (center/head/feet) desloca a ancora verticalmente conforme
    o tamanho real do sprite do alvo.
  - `world_scaled` faz a animacao escalar junto com o zoom da camera de jogo,
    IGUAL aos pokemons (camera.zoom * render_scale * TILE_SCALE).
"""
import math
from pathlib import Path
import pygame

from src.anim.animation import AnimDefinition
from src.anim.layer import SpriteLayerDef, FilterLayerDef, EmitterLayerDef
from src.anim.easing import apply_easing
from src.anim.emitter import ParticleEmitter
from src.anim.actor import ActorRuntime
from src.anim.camera import CameraRuntime


# Mesmo TILE_SCALE usado em Pokemon.render
_TILE_SCALE = 16 / 24


class Animator:
    def __init__(self, definition: AnimDefinition,
                 anchor_target=None, anchor_attacker=None,
                 anchor_projectile=None, world_pos=None, screen_pos=None,
                 loop_override=None, zoom: float = 1.0):
        self.defn = definition
        self.anchor_target = anchor_target
        self.anchor_attacker = anchor_attacker
        self.anchor_projectile = anchor_projectile
        self.world_pos = world_pos or (0, 0)
        self.screen_pos = screen_pos or (0, 0)

        self.loop = (loop_override if loop_override is not None
                     else definition.loop)
        self._loop_count_left = definition.loop_count
        self.zoom = float(zoom)

        self.current_frame: float = 0.0
        self.finished: bool = False
        self._sound_played = False
        self._sprite_cache: dict = {}
        self._emitter_runners: dict = {}
        self._emitter_runner_scales: dict = {}  # rastreia ws do emitter
        self._actor_runtimes: dict = {}

        self.camera_runtime = None
        if definition.category == "cutscene":
            cam_def = getattr(definition, "camera", None)
            if cam_def is not None and getattr(cam_def, "enabled", False):
                self.camera_runtime = CameraRuntime(cam_def)

    # =================================================================
    # UPDATE
    # =================================================================
    def update(self, dt):
        if self.finished:
            return
        fps = max(1, self.defn.fps)
        self.current_frame += dt * fps
        total = max(1, self.defn.duration_frames)

        self._maybe_play_sound()
        self._update_emitters(dt)

        if self.current_frame >= total:
            if self.loop:
                if self._loop_count_left > 0:
                    self._loop_count_left -= 1
                    if self._loop_count_left == 0:
                        self.finished = True
                        return
                self.current_frame = self.current_frame % total
                self._sound_played = False
            else:
                self.current_frame = total
                self.finished = True

    def update_emitters_only(self, dt):
        self._update_emitters(dt)

    def _update_emitters(self, dt):
        for layer in self.defn.layers:
            if not isinstance(layer, EmitterLayerDef):
                continue
            if not self._layer_visible_now(layer):
                continue
            runner = self._emitter_runners.get(layer.id)
            if runner is not None:
                angle = self._compute_aim_angle(layer)
                if angle is not None:
                    runner.set_base_rotation(angle)
                runner.update(dt)

    def set_zoom(self, zoom):
        z = max(0.1, min(4.0, float(zoom)))
        if abs(z - self.zoom) < 0.001:
            return
        self.zoom = z
        for r in self._emitter_runners.values():
            r.clear()
        self._emitter_runners.clear()
        self._emitter_runner_scales.clear()

    def set_camera_runtime(self, cam_def):
        if (self.defn.category == "cutscene"
                and cam_def is not None
                and getattr(cam_def, "enabled", False)):
            self.camera_runtime = CameraRuntime(cam_def)
        else:
            self.camera_runtime = None

    # =================================================================
    # SOM
    # =================================================================
    def _maybe_play_sound(self):
        if self._sound_played or not self.defn.sound:
            return
        snd = self.defn.sound
        start = int(snd.get("start_frame", 0))
        if self.current_frame < start:
            return
        self._sound_played = True
        self._play_sound(snd)

    @staticmethod
    def _play_sound(snd):
        name = str(snd.get("name", "")).strip()
        if not name:
            return
        src = str(snd.get("source", "sfx")).lower()
        vol = snd.get("volume")
        loop = bool(snd.get("loop", False))
        try:
            if src == "move":
                from src.managers.sounds.move_sound_manager import move_sound_manager
                move_sound_manager.play_attack_sound(name, volume=vol)
            elif src == "ambient":
                from src.managers.sounds.ambient_sound_manager import ambient_sound_manager
                ambient_sound_manager.play_ambient(name, loop=loop)
            else:
                from src.managers.sounds.sound_manager import sound_manager
                sound_manager.play_sound(name, volume=vol)
        except Exception as e:
            print(f"[ANIM] erro som '{name}': {e}")

    def stop(self):
        self.finished = True
        for runner in self._emitter_runners.values():
            runner.clear()
        self._actor_runtimes.clear()

    def is_finished(self):
        return self.finished

    # =================================================================
    # CAMERA
    # =================================================================
    def _get_camera_state(self):
        if self.camera_runtime is None:
            return (0.0, 0.0, 1.0)
        c = self.camera_runtime.eval_at(self.current_frame)
        return (c["x"], c["y"], c["zoom"])

    def _viewport_center(self, screen, screen_manager):
        if screen_manager is not None:
            return (screen_manager.viewport_x + screen_manager.viewport_width // 2,
                    screen_manager.viewport_y + screen_manager.viewport_height // 2)
        return (screen.get_width() // 2, screen.get_height() // 2)

    def _actor_origin(self, screen, screen_manager):
        cx, cy = self._viewport_center(screen, screen_manager)
        cam_x, cam_y, cam_zoom = self._get_camera_state()
        eff = self.zoom * cam_zoom
        return (cx - cam_x * eff, cy - cam_y * eff)

    # =================================================================
    # ESCALA DE JOGO (mesma do Pokemon.render)
    # =================================================================
    def _game_scale(self, camera, screen_manager):
        """Fator total aplicado ao sprite do pokemon no jogo.

        Pokemon.render usa:
            zoom_scale = camera.zoom * screen_manager.render_scale * TILE_SCALE

        Retorna 1.0 se world_scaled=False ou se faltar camera/screen_manager.
        """
        if not getattr(self.defn, 'world_scaled', True):
            return 1.0
        if camera is None or screen_manager is None:
            return 1.0
        return camera.zoom * screen_manager.render_scale * _TILE_SCALE

    # =================================================================
    # ATORES
    # =================================================================
    def get_actor_runtime(self, actor_id):
        return self._actor_runtimes.get(actor_id)

    def invalidate_actor(self, actor_id=None):
        if actor_id:
            self._actor_runtimes.pop(actor_id, None)
        else:
            self._actor_runtimes.clear()

    def _ensure_actor_runtime(self, actor_def):
        rt = self._actor_runtimes.get(actor_def.id)
        if rt is None or rt.defn is not actor_def:
            rt = ActorRuntime(actor_def)
            self._actor_runtimes[actor_def.id] = rt
        return rt

    def _render_actors(self, screen, screen_manager, hidden_actors=None):
        actors = getattr(self.defn, "actors", None) or []
        if not actors:
            return

        for actor_def in actors:
            self._ensure_actor_runtime(actor_def)

        ox, oy = self._actor_origin(screen, screen_manager)
        _, _, cam_zoom = self._get_camera_state()
        eff_zoom = self.zoom * cam_zoom
        time_seconds = self.current_frame / max(1, self.defn.fps)
        f = self.current_frame

        for actor_def in sorted(actors, key=lambda a: getattr(a, "z", 0)):
            if hidden_actors and actor_def.id in hidden_actors:
                continue
            vf = getattr(actor_def, "visible_frames", None)
            if vf:
                start = int(vf[0]) if len(vf) > 0 else 0
                end = int(vf[1]) if len(vf) > 1 else -1
                if f < start:
                    continue
                if end >= 0 and f > end:
                    continue
            rt = self._ensure_actor_runtime(actor_def)
            try:
                rt.render(screen, ox, oy, f, time_seconds, eff_zoom)
            except Exception as e:
                print(f"[ANIM] erro ator '{actor_def.id}': {e}")

    # =================================================================
    # ANCORAS
    # =================================================================
    def _anchor_object(self):
        a = self.defn.anchor
        if a == "target":
            return self.anchor_target
        if a == "attacker":
            return self.anchor_attacker
        if a == "projectile":
            return self.anchor_projectile
        return None

    def _resolve_anchor_screen_pos(self, camera, screen_manager,
                                   screen=None, layer=None):
        cam_x, cam_y, cam_zoom = self._get_camera_state()
        eff_zoom = self.zoom * cam_zoom

        if layer is not None and getattr(layer, "anchor_actor", ""):
            actor_id = layer.anchor_actor
            rt = self._actor_runtimes.get(actor_id)
            if rt is not None and screen is not None:
                ox, oy = self._actor_origin(screen, screen_manager)
                props = rt.eval_at(self.current_frame)
                return (ox + props["x"] * eff_zoom,
                        oy + props["y"] * eff_zoom)

        anchor = self.defn.anchor
        if anchor.startswith("actor:"):
            actor_id = anchor[len("actor:"):]
            rt = self._actor_runtimes.get(actor_id)
            if rt is not None and screen is not None:
                ox, oy = self._actor_origin(screen, screen_manager)
                props = rt.eval_at(self.current_frame)
                return (ox + props["x"] * eff_zoom,
                        oy + props["y"] * eff_zoom)

        if self.defn.space == "screen" or screen_manager is None:
            ox, oy = self.defn.screen_offset
            anchor_obj = self._anchor_object()
            if anchor_obj is not None:
                bx = getattr(anchor_obj, "x", 0)
                by = getattr(anchor_obj, "y", 0)
            else:
                bx, by = self.screen_pos
            return (bx + ox, by + oy)

        anchor_obj = self._anchor_object()
        if anchor_obj is not None:
            wx = getattr(anchor_obj, "x", 0)
            wy = getattr(anchor_obj, "y", 0)
        else:
            wx, wy = self.world_pos
        wx += self.defn.world_offset[0]
        wy += self.defn.world_offset[1]

        try:
            from src.core.render_context import render_context
            sx, sy = render_context.world_to_screen(wx, wy, camera,
                                                    screen_manager)

            # ===== ÂNCORA DINÂMICA (head/feet) =====
            # Desloca o anchor em pixels de TELA conforme o tamanho real
            # do sprite do alvo. Usa a MESMA fórmula do Pokemon.render.
            if anchor_obj is not None and self.defn.anchor_mode != "center":
                sprite = getattr(anchor_obj, 'sprite', None)
                if sprite is not None and camera is not None and screen_manager is not None:
                    screen_h = (sprite.get_height()
                                * camera.zoom
                                * screen_manager.render_scale
                                * _TILE_SCALE)
                    if self.defn.anchor_mode == "head":
                        sy -= screen_h / 2.0
                    elif self.defn.anchor_mode == "feet":
                        sy += screen_h / 2.0

            if self.camera_runtime is None:
                return (sx, sy)
            cx, cy = self._viewport_center(screen, screen_manager)
            return (sx + (cx - cam_x * eff_zoom - cx),
                    sy + (cy - cam_y * eff_zoom - cy))
        except Exception:
            return (wx, wy)

    # =================================================================
    # AIM
    # =================================================================
    def _actor_screen_pos(self, actor_id, screen, screen_manager):
        rt = self._actor_runtimes.get(actor_id)
        if rt is None or screen is None:
            return None
        ox, oy = self._actor_origin(screen, screen_manager)
        _, _, cam_zoom = self._get_camera_state()
        eff_zoom = self.zoom * cam_zoom
        props = rt.eval_at(self.current_frame)
        return (ox + props["x"] * eff_zoom,
                oy + props["y"] * eff_zoom)

    def _compute_aim_angle(self, layer, anchor_pos=None,
                           screen=None, screen_manager=None):
        aim = getattr(layer, "aim_at", "") or ""
        if not aim:
            return None

        fixed = {"up": 0.0, "down": 180.0, "left": -90.0, "right": 90.0}
        if aim in fixed:
            return fixed[aim]

        if aim.startswith("actor:") and anchor_pos is not None:
            actor_id = aim[len("actor:"):]
            tpos = self._actor_screen_pos(actor_id, screen, screen_manager)
            if tpos:
                dx = tpos[0] - anchor_pos[0]
                dy = tpos[1] - anchor_pos[1]
                return math.degrees(math.atan2(dy, dx)) + 90.0
            return 0.0

        return None

    # =================================================================
    # RENDER
    # =================================================================
    def render(self, screen, camera=None, screen_manager=None,
               hidden_actors=None):
        if self.finished:
            return

        self._render_actors(screen, screen_manager,
                            hidden_actors=hidden_actors)

        layers_sorted = sorted(enumerate(self.defn.layers),
                               key=lambda t: (t[1].z, t[0]))
        for _, layer in layers_sorted:
            if not self._layer_visible_now(layer):
                continue
            anchor_pos = self._resolve_anchor_screen_pos(
                camera, screen_manager, screen=screen, layer=layer)
            try:
                if isinstance(layer, SpriteLayerDef):
                    self._render_sprite_layer(screen, layer, anchor_pos,
                                              screen, screen_manager, camera)
                elif isinstance(layer, FilterLayerDef):
                    self._render_filter_layer(screen, layer, screen_manager)
                elif isinstance(layer, EmitterLayerDef):
                    self._render_emitter_layer(screen, layer, anchor_pos,
                                               screen, screen_manager, camera)
            except Exception as e:
                print(f"[ANIM] erro layer '{layer.id}': {e}")

    def _layer_visible_now(self, layer):
        vf = layer.visible_frames
        if not vf:
            return True
        start = int(vf[0]) if len(vf) > 0 else 0
        end = int(vf[1]) if len(vf) > 1 else -1
        f = self.current_frame
        if f < start:
            return False
        if end >= 0 and f > end:
            return False
        return True

    # -----------------------------------------------------------------
    # SPRITE
    # -----------------------------------------------------------------
    def _interp_keyframe(self, layer):
        kfs = layer.keyframes
        if not kfs:
            return {"x": 0, "y": 0, "rot": 0, "scale": 1.0,
                    "alpha": 255, "tint": (255, 255, 255),
                    "frame_index": -1}

        f = self.current_frame
        if f <= kfs[0].f:
            k = kfs[0]
            return {"x": k.x, "y": k.y, "rot": k.rot, "scale": k.scale,
                    "alpha": k.alpha, "tint": k.tint,
                    "frame_index": getattr(k, "frame_index", -1)}
        if f >= kfs[-1].f:
            k = kfs[-1]
            return {"x": k.x, "y": k.y, "rot": k.rot, "scale": k.scale,
                    "alpha": k.alpha, "tint": k.tint,
                    "frame_index": getattr(k, "frame_index", -1)}

        for i in range(len(kfs) - 1):
            a, b = kfs[i], kfs[i + 1]
            if a.f <= f <= b.f:
                span = max(1, b.f - a.f)
                t = apply_easing(layer.easing, (f - a.f) / span)

                # frame_index: interpolação LINEAR (frames discretos)
                raw = (f - a.f) / span
                a_fi = getattr(a, "frame_index", -1)
                b_fi = getattr(b, "frame_index", -1)
                if a_fi >= 0 and b_fi >= 0:
                    fi = int(round(a_fi + (b_fi - a_fi) * raw))
                elif a_fi >= 0:
                    fi = a_fi
                elif b_fi >= 0:
                    fi = b_fi
                else:
                    fi = -1

                return {
                    "x": a.x + (b.x - a.x) * t,
                    "y": a.y + (b.y - a.y) * t,
                    "rot": a.rot + (b.rot - a.rot) * t,
                    "scale": a.scale + (b.scale - a.scale) * t,
                    "alpha": int(a.alpha + (b.alpha - a.alpha) * t),
                    "tint": _lerp_color(a.tint, b.tint, t),
                    "frame_index": fi,
                }
        return {"x": 0, "y": 0, "rot": 0, "scale": 1.0,
                "alpha": 255, "tint": (255, 255, 255),
                "frame_index": -1}

    def _render_sprite_layer(self, screen, layer, anchor_pos,
                             screen_obj=None, screen_manager=None,
                             camera=None):
        img = self._get_sprite_image(layer.image_path)
        if img is None:
            self._draw_missing_sprite(screen, anchor_pos, layer)
            return

        props = self._interp_keyframe(layer)
        if props["alpha"] <= 0:
            return

        # ===== FATIA DO SPRITESHEET =====
        base = img
        if layer.frame_width > 0 and layer.frame_height > 0:
            fw, fh = int(layer.frame_width), int(layer.frame_height)
            cols = max(1, img.get_width() // fw)
            kf_fi = props.get("frame_index", -1)
            idx = int(kf_fi) if kf_fi >= 0 else max(0, int(layer.frame_index))
            col = idx % cols
            row = idx // cols
            rect = pygame.Rect(col * fw, row * fh, fw, fh)
            if (rect.right <= img.get_width()
                    and rect.bottom <= img.get_height()):
                try:
                    base = img.subsurface(rect).copy()
                except Exception:
                    base = img

        if layer.flip_x or layer.flip_y:
            base = pygame.transform.flip(base, layer.flip_x, layer.flip_y)
        if props["tint"] != (255, 255, 255):
            base = _apply_tint(base, props["tint"])

        # ===== ESCALA =====
        # eff_zoom: zoom interno do Animator (editor usa, jogo = 1.0)
        _, _, cam_zoom = self._get_camera_state()
        eff_zoom = self.zoom * cam_zoom

        # ws: escala "world" (mesma do pokemon) quando world_scaled=True
        ws = self._game_scale(camera, screen_manager)

        # Total: keyframe.scale * eff_zoom * scale_mult * ws
        scale_mult = getattr(self.defn, "scale_mult", 1.0)
        total_scale = (max(0.01, props["scale"])
                       * eff_zoom * scale_mult * ws)

        if abs(total_scale - 1.0) > 0.001:
            w = max(1, int(round(base.get_width() * total_scale)))
            h = max(1, int(round(base.get_height() * total_scale)))
            base = pygame.transform.scale(base, (w, h))

        aim_angle = self._compute_aim_angle(
            layer, anchor_pos, screen_obj, screen_manager)
        total_rot = props["rot"] + (aim_angle if aim_angle is not None else 0.0)

        if abs(total_rot) > 0.1:
            base = pygame.transform.rotozoom(base, -total_rot, 1.0)

        if props["alpha"] < 255:
            base = base.copy()
            base.set_alpha(int(props["alpha"]))

        # ===== POSIÇÃO =====
        # Offsets e keyframes x/y escalam com scale_mult e ws (uniforme)
        offset_scale = eff_zoom * scale_mult * ws
        px = anchor_pos[0] + (layer.offset_x + props["x"]) * offset_scale
        py = anchor_pos[1] + (layer.offset_y + props["y"]) * offset_scale

        rect = base.get_rect()
        pivot = layer.pivot
        if pivot == "top_left":
            rect.topleft = (int(px), int(py))
        elif pivot == "top_center":
            rect.midtop = (int(px), int(py))
        elif pivot == "top_right":
            rect.topright = (int(px), int(py))
        elif pivot == "bottom_left":
            rect.bottomleft = (int(px), int(py))
        elif pivot == "bottom_center":
            rect.midbottom = (int(px), int(py))
        elif pivot == "bottom_right":
            rect.bottomright = (int(px), int(py))
        else:
            rect.center = (int(px), int(py))

        screen.blit(base, rect.topleft)

    def _draw_missing_sprite(self, screen, anchor_pos, layer):
        w = h = 40
        x = int(anchor_pos[0] + layer.offset_x * self.zoom)
        y = int(anchor_pos[1] + layer.offset_y * self.zoom)
        rect = pygame.Rect(x - w // 2, y - h // 2, w, h)
        surf = pygame.Surface((w, h), pygame.SRCALPHA)
        surf.fill((90, 20, 90, 150))
        pygame.draw.rect(surf, (255, 100, 255), surf.get_rect(), 2)
        screen.blit(surf, rect.topleft)

    # -----------------------------------------------------------------
    # EMITTER
    # -----------------------------------------------------------------
    def _scaled_emitter_params(self, params, extra_scale=1.0):
        p = dict(params or {})
        scale_mult = getattr(self.defn, "scale_mult", 1.0)
        # z combina zoom interno + scale_mult + world_scale do momento
        z = self.zoom * scale_mult * extra_scale

        area = dict(p.get("spawn_area")
                    or {"x": -20, "y": -20, "w": 40, "h": 40})
        area["x"] *= z
        area["y"] *= z
        area["w"] *= z
        area["h"] *= z
        p["spawn_area"] = area

        vel = dict(p.get("velocity") or {"x": [0, 0], "y": [0, 0]})
        vel["x"] = [v * z for v in vel["x"]]
        vel["y"] = [v * z for v in vel["y"]]
        p["velocity"] = vel

        p["scale"] = [v * z for v in (p.get("scale") or [1.0, 1.0])]
        p["spawn_rate"] = float(p.get("spawn_rate", 10.0)) * (z ** 1.5)
        return p

    def _render_emitter_layer(self, screen, layer, anchor_pos,
                              screen_obj=None, screen_manager=None,
                              camera=None):
        ws = self._game_scale(camera, screen_manager)

        runner = self._emitter_runners.get(layer.id)
        cached_ws = self._emitter_runner_scales.get(layer.id)

        # Se o ws mudou (jogador deu zoom), recria o emitter com o novo tamanho
        if runner is not None and cached_ws is not None and abs(cached_ws - ws) > 0.001:
            runner.clear()
            runner = None

        if runner is None:
            img = self._get_sprite_image(layer.image_path)
            if img is None:
                return
            params = self._scaled_emitter_params(layer.emitter_params,
                                                 extra_scale=ws)
            runner = ParticleEmitter(img, params)
            self._emitter_runners[layer.id] = runner
            self._emitter_runner_scales[layer.id] = ws

        angle = self._compute_aim_angle(
            layer, anchor_pos, screen_obj, screen_manager)
        runner.set_base_rotation(angle if angle is not None else 0.0)

        _, _, cam_zoom = self._get_camera_state()
        eff_zoom = self.zoom * cam_zoom
        scale_mult = getattr(self.defn, "scale_mult", 1.0)
        offset_scale = eff_zoom * scale_mult * ws
        ox = anchor_pos[0] + layer.offset_x * offset_scale
        oy = anchor_pos[1] + layer.offset_y * offset_scale
        runner.render(screen, ox, oy, blend_mode=layer.blend)

    # -----------------------------------------------------------------
    # FILTER
    # -----------------------------------------------------------------
    def _render_filter_layer(self, screen, layer, screen_manager):
        if screen_manager is not None:
            vp = pygame.Rect(
                screen_manager.viewport_x, screen_manager.viewport_y,
                screen_manager.viewport_width,
                screen_manager.viewport_height)
        else:
            vp = screen.get_rect()

        alpha = layer.alpha
        f = self.current_frame
        if layer.fade_in_frames > 0 and f < layer.fade_in_frames:
            alpha = int(alpha * (f / layer.fade_in_frames))
        total = self.defn.duration_frames
        fade_out_start = total - layer.fade_out_frames
        if layer.fade_out_frames > 0 and f > fade_out_start:
            t = (f - fade_out_start) / layer.fade_out_frames
            alpha = int(alpha * (1.0 - t))
        alpha = max(0, min(255, alpha))
        if alpha == 0:
            return

        surf = pygame.Surface((vp.width, vp.height), pygame.SRCALPHA)
        surf.fill((*layer.color, alpha))
        screen.blit(surf, vp.topleft)

    # -----------------------------------------------------------------
    # IMAGEM
    # -----------------------------------------------------------------
    def _get_sprite_image(self, image_path):
        if not image_path:
            return None
        if image_path in self._sprite_cache:
            return self._sprite_cache[image_path]
        result = None
        try:
            if image_path.startswith("item://"):
                iid = image_path[len("item://"):].strip()
                from src.data.item_bag_catalog import item_bag_catalog
                result = item_bag_catalog.get_sprite(iid, scaled=False)
                if result is None:
                    print(f"[ANIM] item sprite nao encontrado: {iid}")
            elif image_path.startswith("pokemon://"):
                parts = image_path[len("pokemon://"):].split("/")
                if len(parts) >= 4:
                    pid = int(parts[0])
                    anim = parts[1]
                    direction = parts[2]
                    frame_idx = int(parts[3])
                    shiny = (len(parts) > 4
                             and parts[4].lower() == "true")
                    from src.data.pokedex import Pokedex
                    pokedex = Pokedex()
                    frames = pokedex.get_animation_frames(
                        pid, anim, direction, shiny)
                    if frames and 0 <= frame_idx < len(frames):
                        result = frames[frame_idx]
            else:
                from src.config.paths import RES_PATH
                base = RES_PATH / "animations"
                p = (Path(image_path)
                     if Path(image_path).is_absolute()
                     else (base / image_path))
                if p.exists():
                    img = pygame.image.load(str(p))
                    try:
                        img = img.convert_alpha()
                    except pygame.error:
                        pass
                    result = img
        except Exception as e:
            print(f"[ANIM] erro imagem '{image_path}': {e}")
        self._sprite_cache[image_path] = result
        return result


# =====================================================================
# HELPERS
# =====================================================================
def _apply_tint(sprite, tint):
    out = sprite.copy()
    overlay = pygame.Surface(out.get_size(), pygame.SRCALPHA)
    overlay.fill((int(tint[0]), int(tint[1]), int(tint[2]), 255))
    out.blit(overlay, (0, 0), special_flags=pygame.BLEND_RGBA_MULT)
    return out


def _lerp_color(a, b, t):
    return (int(a[0] + (b[0] - a[0]) * t),
            int(a[1] + (b[1] - a[1]) * t),
            int(a[2] + (b[2] - a[2]) * t))