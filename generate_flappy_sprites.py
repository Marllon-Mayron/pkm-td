"""Gera sprites pixel art para a cutscene Flappy Natu.

Rode:  python tools/generate_flappy_sprites.py
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

TWO_PI = 2 * math.pi

# ===== Paletas =====
CLOUD_WHITE   = (250, 252, 255)
CLOUD_SHADOW  = (205, 218, 235)
MTN_FAR       = (150, 180, 210)
MTN_NEAR      = (95, 125, 165)
MTN_SNOW      = (242, 246, 252)
PIPE_HILITE   = (200, 255, 200)
PIPE_LIGHT    = (130, 220, 130)
PIPE_MID      = (70, 180, 70)
PIPE_DARK     = (40, 120, 40)
PIPE_EDGE     = (28, 80, 28)
GRASS_TOP     = (120, 200, 100)
GRASS_MID     = (60, 150, 60)
GRASS_DIRT    = (140, 100, 60)
DIRT_DARK     = (90, 65, 40)


def _px(s, x, y, c):
    if 0 <= x < s.get_width() and 0 <= y < s.get_height():
        s.set_at((int(x), int(y)), c)


# =====================================================================
def build_clouds_strip():
    """480x60 - tira de nuvens tileable em X."""
    W, H = 480, 60
    s = pygame.Surface((W, H), pygame.SRCALPHA)
    rnd = random.Random(99)

    # 3 clusters de nuvem ao longo da faixa
    for base_cx in (70, 220, 370):
        # base oval (sombra)
        base_w = rnd.randint(45, 65)
        base_h = 8
        base_cy = 40 + rnd.randint(-4, 4)
        for dx in range(-base_w, base_w + 1):
            for dy in range(-base_h, base_h + 1):
                if (dx * dx) / (base_w ** 2) + (dy * dy) / (base_h ** 2) <= 1:
                    _px(s, base_cx + dx, base_cy + dy, CLOUD_SHADOW + (235,))
        # bumps de cima
        num_bumps = rnd.randint(4, 6)
        for i in range(num_bumps):
            bx = base_cx - base_w // 2 + 8 + i * (base_w - 16) // max(1, num_bumps - 1)
            br = rnd.randint(9, 14)
            by = base_cy - 6 + rnd.randint(-2, 2)
            for dx in range(-br, br + 1):
                for dy in range(-br, br + 1):
                    if dx * dx + dy * dy <= br * br:
                        _px(s, bx + dx, by + dy, CLOUD_WHITE + (255,))
    return s


def build_mountains_strip():
    """480x100 - montanhas tileable em X."""
    W, H = 480, 100
    s = pygame.Surface((W, H), pygame.SRCALPHA)

    # perfil de fundo (2 senoides com periodo divisor de 480)
    def far_h(x):
        return (32
                + 18 * math.sin(x * TWO_PI / 480)
                + 10 * math.sin(x * TWO_PI / 240 + 1.2))

    def near_h(x):
        return (60
                + 22 * math.sin(x * TWO_PI / 480 + 0.6)
                + 14 * math.sin(x * TWO_PI / 160 + 2.1))

    for x in range(W):
        h_far = int(far_h(x))
        h_near = int(near_h(x))
        # preenche faixa far
        for y in range(H - h_far, H):
            _px(s, x, y, MTN_FAR + (255,))
        # preenche faixa near
        for y in range(H - h_near, H):
            _px(s, x, y, MTN_NEAR + (255,))
        # neve no topo das near (2-3 px)
        _px(s, x, H - h_near, MTN_SNOW + (255,))
        if h_near > 70:
            _px(s, x, H - h_near + 1, MTN_SNOW + (255,))
    return s


def build_pipe_strip():
    """1440x960 - 6 pares de canos, gaps em alturas variadas.

    6 slots * 240px = 1440px. Com scroll_speed_x=120 e duration=720
    frames, o strip da exatamente 1 volta: cada cano passa pelo Natu
    em um frame previsivel (a cada 120 frames).
    """
    W, H = 1440, 960
    s = pygame.Surface((W, H), pygame.SRCALPHA)

    SLOT_W = 240
    BODY_X = 80
    BODY_W = 80
    CAP_PAD = 6
    CAP_H = 24
    GAP_H = 180

    # 6 gaps em alturas crescentemente variadas
    gap_tops = [260, 420, 300, 520, 380, 340]

    def paint_body(y0, y1, x0):
        for y in range(max(0, y0), min(H, y1)):
            for x in range(x0, x0 + BODY_W):
                dx = x - x0
                if dx < 4:             c = PIPE_HILITE
                elif dx < 10:          c = PIPE_LIGHT
                elif dx < BODY_W - 12: c = PIPE_MID
                elif dx < BODY_W - 4:  c = PIPE_DARK
                else:                  c = PIPE_EDGE
                _px(s, x, y, c + (255,))

    def paint_cap(y0, y1, x0):
        x0 = x0 - CAP_PAD
        w = BODY_W + CAP_PAD * 2
        for y in range(max(0, y0), min(H, y1)):
            for x in range(x0, x0 + w):
                dx = x - x0
                if dx < 6:             c = PIPE_HILITE
                elif dx < 14:          c = PIPE_LIGHT
                elif dx < w - 14:      c = PIPE_MID
                elif dx < w - 4:       c = PIPE_DARK
                else:                  c = PIPE_EDGE
                _px(s, x, y, c + (255,))

    for i, gap_top in enumerate(gap_tops):
        cx = i * SLOT_W + BODY_X
        paint_body(0, gap_top - CAP_H, cx)
        paint_cap(gap_top - CAP_H, gap_top, cx)
        for x in range(cx - CAP_PAD, cx + BODY_W + CAP_PAD):
            _px(s, x, gap_top - 1, (20, 60, 20, 255))

        gap_bot = gap_top + GAP_H
        paint_cap(gap_bot, gap_bot + CAP_H, cx)
        for x in range(cx - CAP_PAD, cx + BODY_W + CAP_PAD):
            _px(s, x, gap_bot, (20, 60, 20, 255))
        paint_body(gap_bot + CAP_H, H, cx)

    return s


def build_ground_strip():
    """480x40 - tira de chao (grama + terra) tileable em X."""
    W, H = 480, 40
    s = pygame.Surface((W, H), pygame.SRCALPHA)
    rnd = random.Random(7)
    for x in range(W):
        # 8px de grama
        for y in range(0, 8):
            _px(s, x, y, GRASS_TOP + (255,) if y < 3 else GRASS_MID + (255,))
        # 32px de terra
        for y in range(8, H):
            shade = rnd.choice((GRASS_DIRT, DIRT_DARK, GRASS_DIRT))
            _px(s, x, y, shade + (255,))
        # 1 pontinho de grama alta
        if x % 6 == 0:
            _px(s, x, 0, (150, 220, 120, 255))
            _px(s, x, 1, (100, 190, 90, 255))
    return s


# =====================================================================
if __name__ == "__main__":
    sprites = {
        "flappy_clouds_480.png":    build_clouds_strip(),
        "flappy_mountains_480.png": build_mountains_strip(),
        "flappy_pipes_240.png":     build_pipe_strip(),
        "flappy_ground_480.png":    build_ground_strip(),
    }
    for name, surf in sprites.items():
        pygame.image.save(surf, str(OUT / name))
        print(f"OK {name}  ({surf.get_width()}x{surf.get_height()})")
    print(f"\n{len(sprites)} sprites em {OUT.resolve()}")