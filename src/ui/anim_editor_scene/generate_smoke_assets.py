"""Gera sprites 16x16 pixel art: fumaça, puff, brilhos, gotas, bolhas.

Rode uma vez:  python tools/generate_smoke_assets.py
"""
import math
import random
from pathlib import Path

import pygame

pygame.init()
pygame.display.set_mode((1, 1), pygame.HIDDEN)

OUT = Path("res/animations/_shared")
OUT.mkdir(parents=True, exist_ok=True)

SIZE = 16
CX = CY = SIZE // 2


# =====================================================================
# HELPERS
# =====================================================================
def _quantize(alpha, step=32):
    """Quantiza alpha em degraus — dá cara de pixel art."""
    return max(0, min(255, (int(alpha) // step) * step))


def _pixel_smoke(radius, density, seed=0, blobs=6, gamma=1.2):
    """Vários círculos sobrepostos (blend aditivo) → forma orgânica e densa."""
    rnd = random.Random(seed)
    surf = pygame.Surface((SIZE, SIZE), pygame.SRCALPHA)

    for _ in range(blobs):
        # offset maior → silhueta mais irregular
        bx = CX + rnd.randint(-3, 3)
        by = CY + rnd.randint(-3, 3)
        # raio mais consistente e gordo
        br = radius * rnd.uniform(0.75, 1.05)
        # cada blob começa quase opaco
        ba = density * rnd.uniform(0.75, 1.0)

        for y in range(SIZE):
            for x in range(SIZE):
                dx = x - bx
                dy = y - by
                d = math.sqrt(dx * dx + dy * dy)
                if d >= br:
                    continue
                t = 1.0 - (d / br)
                a = int((t ** gamma) * ba)
                cur = surf.get_at((x, y))
                surf.set_at((x, y), (255, 255, 255,
                                     min(255, cur[3] + a)))

    # quantiza alpha
    for y in range(SIZE):
        for x in range(SIZE):
            _, _, _, a = surf.get_at((x, y))
            surf.set_at((x, y), (255, 255, 255, _quantize(a)))
    return surf


def _make_sheet(frames):
    sheet = pygame.Surface((SIZE * len(frames), SIZE), pygame.SRCALPHA)
    for i, s in enumerate(frames):
        sheet.blit(s, (i * SIZE, 0))
    return sheet


# =====================================================================
# GERADORES DE FORMA
# =====================================================================
def build_smoke_frames():
    """8 frames: fumaça gorda que cresce e se dissipa lentamente."""
    params = [
        # (raio, density, gamma)
        (3.8, 255, 1.1),
        (5.0, 255, 1.2),
        (6.0, 250, 1.3),
        (6.8, 240, 1.4),
        (7.3, 225, 1.5),
        (7.6, 200, 1.6),
        (7.6, 170, 1.8),
        (7.4, 130, 2.0),
    ]
    return [_pixel_smoke(r, d, seed=i * 7 + 3, gamma=g)
            for i, (r, d, g) in enumerate(params)]


def build_puff_frames():
    """6 frames: puff rápido e denso (impacto)."""
    params = [
        (2.8, 255, 1.1), (4.4, 255, 1.2), (5.6, 235, 1.4),
        (6.5, 195, 1.6), (6.9, 145, 1.9), (6.6,  90, 2.2),
    ]
    return [_pixel_smoke(r, d, seed=100 + i * 11,
                         blobs=4, gamma=g)
            for i, (r, d, g) in enumerate(params)]


def build_sparkle():
    """Estrelinha 16x16 com 4 pontas + halo."""
    s = pygame.Surface((SIZE, SIZE), pygame.SRCALPHA)
    c = SIZE // 2
    # 4 pontas
    for y in range(SIZE):
        s.set_at((c, y), (255, 255, 255, 255))
        s.set_at((c + 1, y), (255, 255, 255, 200))
        s.set_at((y, c), (255, 255, 255, 255))
        s.set_at((y, c + 1), (255, 255, 255, 200))
    # miolo
    for dy in (-1, 0, 1):
        for dx in (-1, 0, 1):
            s.set_at((c + dx, c + dy), (255, 255, 255, 255))
    # halo
    for y in range(SIZE):
        for x in range(SIZE):
            if s.get_at((x, y))[3] > 0:
                continue
            dx, dy = x - c, y - c
            if dx * dx + dy * dy <= 5:
                s.set_at((x, y), (255, 255, 255, _quantize(90)))
    return s


def build_bubble():
    """Bolha 16x16 — contorno claro, centro vazio."""
    s = pygame.Surface((SIZE, SIZE), pygame.SRCALPHA)
    c = (SIZE - 1) / 2.0
    for y in range(SIZE):
        for x in range(SIZE):
            dx = (x + 0.5) - (c + 0.5)
            dy = (y + 0.5) - (c + 0.5)
            d = math.sqrt(dx * dx + dy * dy)
            if d > 6.5:
                continue
            if d > 5.0:
                s.set_at((x, y), (255, 255, 255,
                                  _quantize(220 - (d - 5.0) * 90)))
            elif d > 4.0:
                s.set_at((x, y), (255, 255, 255, 96))
    # highlight
    for (x, y) in ((5, 5), (6, 5), (5, 6)):
        s.set_at((x, y), (255, 255, 255, 255))
    return s


def build_droplet():
    """Gotícula 16x16 — topo fino, base gorda."""
    s = pygame.Surface((SIZE, SIZE), pygame.SRCALPHA)
    # topo (triângulo fino)
    for y in range(1, 6):
        w = y
        for x in range(CX - w // 2, CX - w // 2 + w):
            if 0 <= x < SIZE:
                s.set_at((x, y), (255, 255, 255, 200))
    # base (círculo)
    bcx, bcy, br = CX, 9, 4
    for y in range(SIZE):
        for x in range(SIZE):
            dx, dy = x - bcx, y - bcy
            if dx * dx + dy * dy <= br * br:
                s.set_at((x, y), (255, 255, 255, 255))
    # highlight
    s.set_at((6, 8), (255, 255, 255, 255))
    s.set_at((7, 8), (255, 255, 255, 255))
    return s


def build_ring():
    """Anel fino 16x16 — pra 'impacto' de spray."""
    s = pygame.Surface((SIZE, SIZE), pygame.SRCALPHA)
    c = (SIZE - 1) / 2.0
    for y in range(SIZE):
        for x in range(SIZE):
            dx = (x + 0.5) - (c + 0.5)
            dy = (y + 0.5) - (c + 0.5)
            d = math.sqrt(dx * dx + dy * dy)
            if 6.0 <= d <= 7.0:
                s.set_at((x, y), (255, 255, 255, 220))
            elif 5.0 <= d < 6.0:
                s.set_at((x, y), (255, 255, 255, _quantize(96)))
    return s


# =====================================================================
# GERA TUDO
# =====================================================================
smoke = build_smoke_frames()
puff = build_puff_frames()

# --- spritesheets (todos os frames lado a lado) ---
pygame.image.save(_make_sheet(smoke), str(OUT / "smoke_8f.png"))
pygame.image.save(_make_sheet(puff),  str(OUT / "puff_6f.png"))

# --- frames individuais (pra compor layer por layer) ---
for i, s in enumerate(smoke):
    pygame.image.save(s, str(OUT / f"smoke_{i:02d}.png"))
for i, s in enumerate(puff):
    pygame.image.save(s, str(OUT / f"puff_{i:02d}.png"))

# --- sprites soltos ---
pygame.image.save(build_sparkle(), str(OUT / "sparkle_16.png"))
pygame.image.save(build_bubble(),  str(OUT / "bubble_16.png"))
pygame.image.save(build_droplet(), str(OUT / "droplet_16.png"))
pygame.image.save(build_ring(),    str(OUT / "ring_16.png"))

print(f"OK — sprites gerados em {OUT.resolve()}")
print("  smoke_8f.png      (128x16 — 8 frames lado a lado)")
print("  puff_6f.png       ( 96x16 — 6 frames)")
print("  smoke_00..07.png  (16x16 cada)")
print("  puff_00..05.png   (16x16 cada)")
print("  sparkle_16.png, bubble_16.png, droplet_16.png, ring_16.png")