"""Sistema de particulas generico (config-driven).

Suporta rotacao base via `set_base_rotation(angle_deg)`. Isso gira a
velocidade inicial E a rotacao do sprite de cada particula — util pra
fazer efeitos que "miram" num alvo.
"""
import math
import random
import pygame


class _Particle:
    __slots__ = ("x", "y", "vx", "vy", "life", "max_life",
                 "scale", "alpha", "rot", "rot_speed", "tint")

    def __init__(self, x, y, vx, vy, life, scale, alpha, rot,
                 rot_speed, tint):
        self.x = x
        self.y = y
        self.vx = vx
        self.vy = vy
        self.life = life
        self.max_life = life
        self.scale = scale
        self.alpha = alpha
        self.rot = rot
        self.rot_speed = rot_speed
        self.tint = tint


class ParticleEmitter:
    def __init__(self, image, params):
        self.image = image
        self.params = params or {}
        self.particles = []
        self._accumulator = 0.0
        self._base_rotation = 0.0

    # =================================================================
    def set_base_rotation(self, angle_deg):
        """Angulo em graus. 0 = comportamento original do JSON."""
        self._base_rotation = float(angle_deg)

    def clear(self):
        self.particles.clear()
        self._accumulator = 0.0

    # =================================================================
    def update(self, dt):
        rate = float(self.params.get("spawn_rate", 10.0))
        max_particles = int(self.params.get("max_particles", 50))
        if rate > 0 and self.image is not None:
            self._accumulator += dt * rate
            while (self._accumulator >= 1.0
                   and len(self.particles) < max_particles):
                self._accumulator -= 1.0
                self._spawn_particle()

        gravity = float(self.params.get("gravity", 0.0))
        gx, gy = 0.0, gravity
        if abs(self._base_rotation) > 0.01:
            rad = math.radians(self._base_rotation)
            cos_r, sin_r = math.cos(rad), math.sin(rad)
            gx, gy = (-gy * sin_r, gy * cos_r)

        for p in self.particles[:]:
            p.life -= dt
            if p.life <= 0:
                self.particles.remove(p)
                continue
            p.vx += gx * dt
            p.vy += gy * dt
            p.x += p.vx * dt
            p.y += p.vy * dt
            p.rot += p.rot_speed * dt

    def render(self, screen, offset_x, offset_y, blend_mode="normal"):
        if not self.image or not self.particles:
            return
        flags = self._blend_flags(blend_mode)
        for p in self.particles:
            self._render_particle(screen, p, offset_x, offset_y, flags)

    # =================================================================
    def _spawn_particle(self):
        pa = self.params

        area = pa.get("spawn_area") or {"x": 0, "y": 0, "w": 40, "h": 40}
        x = random.uniform(area["x"], area["x"] + area["w"])
        y = random.uniform(area["y"], area["y"] + area["h"])

        vel = pa.get("velocity") or {"x": [0, 0], "y": [0, 0]}
        vx = random.uniform(vel["x"][0], vel["x"][1])
        vy = random.uniform(vel["y"][0], vel["y"][1])

        if abs(self._base_rotation) > 0.01:
            rad = math.radians(self._base_rotation)
            cos_r, sin_r = math.cos(rad), math.sin(rad)
            vx, vy = (vx * cos_r - vy * sin_r,
                      vx * sin_r + vy * cos_r)

        life_r = pa.get("lifetime") or [0.5, 1.0]
        life = random.uniform(life_r[0], life_r[1])

        scale_r = pa.get("scale") or [1.0, 1.0]
        scale = random.uniform(scale_r[0], scale_r[1])

        alpha_r = pa.get("alpha") or [255, 255]
        alpha = random.randint(int(alpha_r[0]), int(alpha_r[1]))

        rot_r = pa.get("rotation_speed") or [0, 0]
        rot_speed = random.uniform(rot_r[0], rot_r[1])

        tints = pa.get("tint_options") or ["#FFFFFF"]
        from src.anim.layer import _parse_hex_color
        tint = _parse_hex_color(random.choice(tints))

        self.particles.append(_Particle(
            x=x, y=y, vx=vx, vy=vy, life=life, scale=scale,
            alpha=alpha,
            rot=self._base_rotation,
            rot_speed=rot_speed, tint=tint,
        ))

    # =================================================================
    def _render_particle(self, screen, p, offset_x, offset_y, flags):
        prog = 1.0 - (p.life / max(0.001, p.max_life))

        scale = p.scale
        scale_over = self.params.get("scale_over_life")
        if scale_over:
            scale = self._sample_curve(scale_over, prog)

        alpha = p.alpha
        if self.params.get("fade_out", False):
            fade_start = 0.7
            if prog > fade_start:
                alpha = int(alpha * (1.0 - (prog - fade_start)
                                     / (1.0 - fade_start)))
        alpha = max(0, min(255, alpha))
        if alpha <= 0:
            return

        img = self.image
        if p.tint != (255, 255, 255):
            from src.anim.animator import _apply_tint
            img = _apply_tint(img, p.tint)

        if abs(scale - 1.0) > 0.001:
            w = max(1, int(round(img.get_width() * scale)))
            h = max(1, int(round(img.get_height() * scale)))
            img = pygame.transform.scale(img, (w, h))

        if abs(p.rot) > 0.5:
            img = pygame.transform.rotozoom(img, -p.rot, 1.0)

        if alpha < 255:
            img = img.copy()
            img.set_alpha(alpha)

        sx = int(p.x + offset_x)
        sy = int(p.y + offset_y)
        rect = img.get_rect(center=(sx, sy))
        screen.blit(img, rect.topleft, special_flags=flags)

    # =================================================================
    @staticmethod
    def _sample_curve(points, t):
        if not points:
            return 1.0
        pts = sorted(points, key=lambda p: p["t"])
        if t <= pts[0]["t"]:
            return pts[0]["v"]
        if t >= pts[-1]["t"]:
            return pts[-1]["v"]
        for i in range(len(pts) - 1):
            a, b = pts[i], pts[i + 1]
            if a["t"] <= t <= b["t"]:
                span = max(0.0001, b["t"] - a["t"])
                u = (t - a["t"]) / span
                return a["v"] + (b["v"] - a["v"]) * u
        return pts[-1]["v"]

    @staticmethod
    def _blend_flags(blend_mode):
        from pygame import BLEND_RGBA_ADD, BLEND_RGBA_MULT, BLEND_ADD
        return {
            "add": BLEND_RGBA_ADD,
            "mult": BLEND_RGBA_MULT,
            "screen": BLEND_ADD,
        }.get(blend_mode, 0)