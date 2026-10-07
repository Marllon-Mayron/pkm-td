"""Gera sprites pixel art para efeitos de clima.

Rode:  python tools/generate_weather_sprites.py
Salva em res/animations/_shared/
"""
import math
import random
from pathlib import Path

import pygame

pygame.init()
pygame.display.set_mode((1, 1), pygame.HIDDEN)

OUT = Path("res/animations/_shared")
OUT.mkdir(parents=True, exist_ok=True)


def _q(a, step=32):
    return max(0, min(255, (int(a) // step) * step))


# =====================================================================
# CHUVA
# =====================================================================
def build_raindrop():
    """16x16 traço diagonal de chuva."""
    s = pygame.Surface((16, 16), pygame.SRCALPHA)
    pts = [(3, 1), (4, 2), (4, 3), (5, 4), (5, 5), (6, 6), (6, 7), (7, 8),
           (7, 9), (8, 10), (8, 11), (9, 12), (9, 13)]
    for (x, y) in pts:
        s.set_at((x, y), (200, 230, 255, 220))
        s.set_at((x + 1, y), (140, 180, 255, 120))
    s.set_at((3, 1), (255, 255, 255, 255))
    s.set_at((4, 2), (255, 255, 255, 255))
    return s


def build_splash():
    """16x16 respingo de água."""
    s = pygame.Surface((16, 16), pygame.SRCALPHA)
    for (x, y) in [(2, 12), (4, 10), (6, 8), (9, 8), (11, 10), (13, 12),
                   (3, 14), (7, 13), (9, 13), (13, 14)]:
        s.set_at((x, y), (200, 240, 255, 220))
        s.set_at((x, y - 1), (255, 255, 255, 180))
    return s


# =====================================================================
# NEVE / GRANIZO
# =====================================================================
def build_snowflake():
    """16x16 floco de neve 6 pontas."""
    s = pygame.Surface((16, 16), pygame.SRCALPHA)
    c = 8
    for angle_deg in (0, 60, 120):
        angle = math.radians(angle_deg)
        for r in range(-6, 7):
            x = c + int(round(math.cos(angle) * r))
            y = c + int(round(math.sin(angle) * r))
            if 0 <= x < 16 and 0 <= y < 16:
                a = max(60, 255 - abs(r) * 20)
                s.set_at((x, y), (255, 255, 255, a))
    s.set_at((c, c), (255, 255, 255, 255))
    return s


def build_hailstone():
    """16x16 pedra de granizo arredondada."""
    s = pygame.Surface((16, 16), pygame.SRCALPHA)
    c = 8
    for y in range(16):
        for x in range(16):
            dx, dy = x - c, y - c
            d = math.sqrt(dx * dx + dy * dy)
            if d <= 4:
                s.set_at((x, y), (240, 250, 255, 255))
            elif d <= 5:
                s.set_at((x, y), (200, 230, 250, 200))
    s.set_at((6, 6), (255, 255, 255, 255))
    s.set_at((7, 6), (255, 255, 255, 255))
    s.set_at((6, 7), (255, 255, 255, 255))
    return s


# =====================================================================
# AREIA
# =====================================================================
def build_sand_grain():
    """8x8 grão de areia oval."""
    s = pygame.Surface((8, 8), pygame.SRCALPHA)
    for y in range(8):
        for x in range(8):
            dx = x - 3.5
            dy = y - 3.5
            if (dx * dx) / 6 + (dy * dy) / 2.5 <= 1:
                s.set_at((x, y), (220, 190, 120, 230))
    s.set_at((3, 3), (250, 230, 180, 255))
    return s


def build_dust_puff():
    """32x32 nuvem suave de poeira."""
    s = pygame.Surface((32, 32), pygame.SRCALPHA)
    rnd = random.Random(7)
    for _ in range(8):
        cx = 16 + rnd.randint(-6, 6)
        cy = 16 + rnd.randint(-6, 6)
        r = rnd.randint(6, 11)
        for y in range(32):
            for x in range(32):
                d = math.sqrt((x - cx) ** 2 + (y - cy) ** 2)
                if d >= r:
                    continue
                t = 1.0 - (d / r)
                a = int((t ** 1.5) * 110)
                cur = s.get_at((x, y))
                s.set_at((x, y), (200, 170, 110,
                                   min(255, cur[3] + a)))
    for y in range(32):
        for x in range(32):
            _, _, _, a = s.get_at((x, y))
            s.set_at((x, y), (200, 170, 110, _q(a)))
    return s


# =====================================================================
# SOL
# =====================================================================
def build_sun_ray():
    """64x64 raio de sol (feixe + pontas)."""
    s = pygame.Surface((64, 64), pygame.SRCALPHA)
    c = 32
    for angle_deg in range(0, 360, 45):
        angle = math.radians(angle_deg)
        for i in range(24):
            w = int(10 * (1 - i / 24))
            for offset in range(-w, w + 1):
                x = c + int(math.cos(angle) * i) + int(offset * math.sin(angle))
                y = c + int(math.sin(angle) * i) - int(offset * math.cos(angle))
                if 0 <= x < 64 and 0 <= y < 64:
                    a = int(180 * (1 - i / 24))
                    s.set_at((x, y), (255, 240, 180, _q(a)))
    return s


def build_sun_disc():
    """64x64 disco solar com glow."""
    s = pygame.Surface((64, 64), pygame.SRCALPHA)
    c = 32
    for y in range(64):
        for x in range(64):
            d = math.sqrt((x - c) ** 2 + (y - c) ** 2)
            if d <= 28:
                t = 1.0 - (d / 28)
                s.set_at((x, y), (255, 220, 120, _q((t ** 2) * 200)))
            if d <= 12:
                s.set_at((x, y), (255, 250, 200, int(255 - (d / 12) * 40)))
    return s


# =====================================================================
# RAIO
# =====================================================================
def build_lightning():
    """32x64 raio em zigzag."""
    s = pygame.Surface((32, 64), pygame.SRCALPHA)
    path = [(16, 0), (14, 8), (18, 8), (12, 24), (17, 24),
            (10, 44), (14, 44), (8, 64)]
    for i in range(len(path) - 1):
        x1, y1 = path[i]
        x2, y2 = path[i + 1]
        steps = max(abs(x2 - x1), abs(y2 - y1)) * 2
        for si in range(steps + 1):
            t = si / max(1, steps)
            x = int(x1 + (x2 - x1) * t)
            y = int(y1 + (y2 - y1) * t)
            for dx in (-1, 0, 1):
                for dy in (-1, 0, 1):
                    nx, ny = x + dx, y + dy
                    if 0 <= nx < 32 and 0 <= ny < 64:
                        s.set_at((nx, ny), (255, 255, 220, 240))
    for (x, y) in path:
        for dx in (-2, -1, 0, 1, 2):
            for dy in (-2, -1, 0, 1, 2):
                nx, ny = x + dx, y + dy
                if 0 <= nx < 32 and 0 <= ny < 64:
                    a = s.get_at((nx, ny))[3]
                    s.set_at((nx, ny), (255, 255, 255, min(255, a + 100)))
    return s


# =====================================================================
# DEEP SEA
# =====================================================================
def build_bubble_32():
    """32x32 bolha estilizada."""
    s = pygame.Surface((32, 32), pygame.SRCALPHA)
    c = 16
    for y in range(32):
        for x in range(32):
            d = math.sqrt((x - c + 0.5) ** 2 + (y - c + 0.5) ** 2)
            if d > 14:
                continue
            if d > 12:
                s.set_at((x, y), (200, 240, 255, 180))
            elif d > 11:
                s.set_at((x, y), (150, 220, 255, 100))
    for (x, y) in ((10, 10), (11, 10), (10, 11), (11, 11), (12, 10)):
        s.set_at((x, y), (255, 255, 255, 230))
    return s


def build_god_ray():
    """128x128 feixe diagonal (deep sea)."""
    s = pygame.Surface((128, 128), pygame.SRCALPHA)
    for y in range(128):
        for x in range(128):
            d = abs(x - y) / math.sqrt(2)
            if d > 40:
                continue
            if x + y < 30 or x + y > 220:
                continue
            t = 1.0 - (d / 40)
            s.set_at((x, y), (180, 240, 255, _q((t ** 2) * 70, 16)))
    return s


# =====================================================================
# GERAR
# =====================================================================
if __name__ == "__main__":
    sprites = {
        "raindrop_16.png": build_raindrop(),
        "splash_16.png": build_splash(),
        "snowflake_16.png": build_snowflake(),
        "hailstone_16.png": build_hailstone(),
        "sand_grain_8.png": build_sand_grain(),
        "dust_puff_32.png": build_dust_puff(),
        "sun_ray_64.png": build_sun_ray(),
        "sun_disc_64.png": build_sun_disc(),
        "lightning_32.png": build_lightning(),
        "bubble_32.png": build_bubble_32(),
        "god_ray_128.png": build_god_ray(),
    }
    for name, surf in sprites.items():
        path = OUT / name
        pygame.image.save(surf, str(path))
        print(f"✓ {path.name} ({surf.get_width()}x{surf.get_height()})")
    print(f"\n{len(sprites)} sprites em {OUT.resolve()}")