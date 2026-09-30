# src/battle/effects/specific/weather/snow_particle_system.py
"""
Sistema de partículas de neve/granizo.

Mais lento que a chuva, com deriva lateral senoidal (flocos balançando).
Se não houver sprite, desenha círculos brancos como fallback.
"""
import os
import random
import math

import pygame


class SnowFlake:
    """Um floco individual. Cai devagar, oscilando lateralmente."""

    def __init__(self, sprite_sheet, x, y, scale, fall_duration,
                 ground_y, min_x, max_x, size_variant):
        self.sprite_sheet = sprite_sheet
        self.base_x = float(x)
        self.x = float(x)
        self.y = float(y)
        self.scale = scale
        self.ground_y = ground_y
        self.min_x = min_x
        self.max_x = max_x
        self.size_variant = size_variant  # 0.6 .. 1.4

        # Velocidade vertical
        vertical_distance = max(1.0, ground_y - y)
        self.vy = vertical_distance / fall_duration if fall_duration > 0 else 60.0

        # ===== DERIVA LATERAL (oscilação) =====
        self.drift_amplitude = random.uniform(6.0, 18.0)
        self.drift_frequency = random.uniform(1.2, 2.2)
        self.drift_phase = random.uniform(0.0, math.tau)
        self.elapsed = 0.0

    @property
    def alive(self) -> bool:
        return self.y < self.ground_y and self.min_x <= self.x <= self.max_x

    def update(self, dt: float):
        self.elapsed += dt
        self.y += self.vy * dt
        # x oscila em torno de base_x
        self.x = self.base_x + self.drift_amplitude * math.sin(
            self.drift_phase + self.elapsed * self.drift_frequency
        )
        if self.y >= self.ground_y:
            self.y = self.ground_y

    def draw(self, surface: pygame.Surface):
        if not self.alive:
            return

        # ===== FALLBACK: círculo branco se não tiver sprite =====
        if self.sprite_sheet is None:
            radius = max(1, int(2 * self.scale * self.size_variant))
            surf = pygame.Surface((radius * 2 + 2, radius * 2 + 2), pygame.SRCALPHA)
            pygame.draw.circle(
                surf, (245, 250, 255, 220),
                (radius + 1, radius + 1), radius
            )
            rect = surf.get_rect(center=(int(self.x), int(self.y)))
            surface.blit(surf, rect)
            return

        # ===== SPRITE =====
        fw = self.sprite_sheet.get_width()
        fh = self.sprite_sheet.get_height()
        w = max(1, int(fw * self.scale * self.size_variant))
        h = max(1, int(fh * self.scale * self.size_variant))

        frame_surf = self.sprite_sheet
        if (w, h) != frame_surf.get_size():
            frame_surf = pygame.transform.smoothscale(frame_surf, (w, h))

        rect = frame_surf.get_rect(center=(int(self.x), int(self.y)))
        surface.blit(frame_surf, rect)


class SnowParticleSystem:
    """
    Sistema de partículas de neve/granizo.
    Mais lento e gentil que a chuva.
    """

    FALL_DURATION = 3.5   # bem mais lento que a chuva (1.2)

    def __init__(self, viewport_rect: pygame.Rect,
                 flake_count: int = 60, scale: float = 1.0):
        self.viewport_rect = pygame.Rect(viewport_rect)
        self.scale = scale
        self.flake_count = max(1, int(flake_count))
        self.flakes = []
        self.sprite_sheet = None
        self.active = False

        self._spawn_accumulator = 0.0
        self._spawn_every = 0.06

        self._load_sprite()

    def _load_sprite(self):
        try:
            from src.config.paths import PROJECT_ROOT, SPRITES_PATH
        except Exception as e:
            print(f"[SNOW] Não foi possível importar paths: {e}")
            self.sprite_sheet = None
            return

        candidates = [
            os.path.join(str(SPRITES_PATH), "Particle", "Snow.None.png"),
            os.path.join(str(SPRITES_PATH), "Particle", "Snow.png"),
            os.path.join(str(SPRITES_PATH), "Particle", "snow.png"),
            os.path.join(str(SPRITES_PATH), "Particle", "Hail.None.png"),
            os.path.join(str(SPRITES_PATH), "Particle", "Hail.png"),
        ]

        for path in candidates:
            if not os.path.isfile(path):
                continue
            try:
                img = pygame.image.load(path)
                try:
                    img = img.convert_alpha()
                except pygame.error:
                    pass
                self.sprite_sheet = img
                print(f"[SNOW] Sprite carregado: {path}")
                return
            except Exception as e:
                print(f"[SNOW] Falha ao carregar '{path}': {e}")

        print("[SNOW] Sprite não encontrado — usando círculos brancos (fallback).")
        self.sprite_sheet = None

    def set_viewport(self, viewport_rect: pygame.Rect):
        self.viewport_rect = pygame.Rect(viewport_rect)

    def start(self):
        if self.active:
            return
        self.active = True
        self.flakes.clear()
        print("[SNOW] Granizo iniciado")
        for _ in range(self.flake_count):
            self._spawn(initial=True)

    def stop(self):
        self.active = False
        self.flakes.clear()
        self._spawn_accumulator = 0.0

    def _spawn(self, initial: bool = False):
        vp = self.viewport_rect

        x = random.uniform(vp.x - 100, vp.right + 100)

        if initial:
            y = random.uniform(vp.y, vp.bottom - 30)
        else:
            y = vp.y - random.uniform(20, 100)

        min_x = vp.x - vp.width
        max_x = vp.right + vp.width

        self.flakes.append(SnowFlake(
            sprite_sheet=self.sprite_sheet,
            x=x, y=y,
            scale=self.scale,
            fall_duration=SnowParticleSystem.FALL_DURATION,
            ground_y=vp.bottom - 2,
            min_x=min_x,
            max_x=max_x,
            size_variant=random.uniform(0.6, 1.4),
        ))

    def update(self, dt: float):
        if not self.active:
            return

        for f in self.flakes:
            f.update(dt)

        self.flakes = [f for f in self.flakes if f.alive]

        self._spawn_accumulator += dt
        while self._spawn_accumulator >= self._spawn_every:
            self._spawn_accumulator -= self._spawn_every
            if len(self.flakes) < self.flake_count * 4:
                self._spawn(initial=False)

    def render(self, surface: pygame.Surface):
        if not self.active:
            return
        for f in self.flakes:
            f.draw(surface)