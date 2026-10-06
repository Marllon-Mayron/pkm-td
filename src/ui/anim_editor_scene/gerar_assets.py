"""Gera sprites de placeholder para o editor de animações.
Rode uma vez: python tools/make_anim_placeholders.py
"""
import pygame
from pathlib import Path

pygame.init()
pygame.display.set_mode((1, 1))

OUT = Path("res/animations/_shared")
OUT.mkdir(parents=True, exist_ok=True)

# ---------- SPARKLE ----------
sparkle = pygame.Surface((16, 16), pygame.SRCALPHA)
# Contorno externo suave
pygame.draw.polygon(sparkle, (255, 240, 180, 180),
                    [(8, 0), (10, 6), (16, 8), (10, 10),
                     (8, 16), (6, 10), (0, 8), (6, 6)])
# Miolo brilhante
pygame.draw.polygon(sparkle, (255, 255, 255, 255),
                    [(8, 3), (9, 7), (13, 8), (9, 9),
                     (8, 13), (7, 9), (3, 8), (7, 7)])
pygame.image.save(sparkle, str(OUT / "sparkle.png"))

# ---------- RAINDROP ----------
rain = pygame.Surface((8, 16), pygame.SRCALPHA)
pygame.draw.rect(rain, (180, 210, 255, 180), (3, 0, 2, 6))
pygame.draw.rect(rain, (150, 190, 255, 230), (2, 4, 4, 10))
pygame.draw.rect(rain, (200, 220, 255, 255), (3, 6, 2, 8))
pygame.image.save(rain, str(OUT / "raindrop.png"))

# ---------- SMOKE ----------
smoke = pygame.Surface((16, 16), pygame.SRCALPHA)
for i, (cx, cy, r, a) in enumerate([
    (6, 8, 5, 180), (10, 6, 4, 150), (8, 11, 4, 130), (11, 10, 3, 160),
]):
    pygame.draw.circle(smoke, (200, 200, 200, a), (cx, cy), r)
pygame.image.save(smoke, str(OUT / "smoke.png"))

ember = pygame.Surface((12, 12), pygame.SRCALPHA)
pygame.draw.polygon(ember, (255, 90, 30, 220),
                    [(6, 0), (10, 6), (6, 12), (2, 6)])
pygame.draw.polygon(ember, (255, 200, 90, 255),
                    [(6, 3), (9, 6), (6, 10), (3, 6)])
pygame.draw.circle(ember, (255, 255, 220, 255), (6, 6), 2)
pygame.image.save(ember, str(OUT / "ember.png"))

# ---------- BUBBLE (bolha) ----------
bubble = pygame.Surface((16, 16), pygame.SRCALPHA)
pygame.draw.circle(bubble, (160, 220, 255, 140), (8, 8), 7)
pygame.draw.circle(bubble, (220, 245, 255, 220), (8, 8), 7, 2)
pygame.draw.circle(bubble, (255, 255, 255, 240), (6, 6), 2)
pygame.image.save(bubble, str(OUT / "bubble.png"))

print(f"OK — sprites gerados em {OUT.resolve()}")