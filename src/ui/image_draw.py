# src/ui/image_draw.py
"""
Utilitário central de desenho de imagens.

Modos:
  "stretch"   estica pra preencher (ignora aspect)
  "tile"      repete em 2D no tamanho original
  "tile_h"    repete na horizontal, altura esticada
  "tile_v"    repete na vertical, largura esticada
  "center"    tamanho original, centralizado
  "contain"   mantém aspect, cabe dentro
  "cover"     mantém aspect, cobre tudo (corta sobras)
  "fit_w"     largura total, altura proporcional
  "fit_h"     altura total, largura proporcional

Escala:
  smooth=False (padrão) → pygame.transform.scale (nearest, pixel perfect)
  smooth=True           → pygame.transform.smoothscale (bilinear)
"""
import pygame

MODES = ("stretch", "tile", "tile_h", "tile_v", "center",
         "contain", "cover", "fit_w", "fit_h")


def _apply_tint(img, tint):
    if not tint:
        return img
    out = img.copy()
    overlay = pygame.Surface(out.get_size(), pygame.SRCALPHA)
    overlay.fill((int(tint[0]), int(tint[1]), int(tint[2]), 255))
    out.blit(overlay, (0, 0), special_flags=pygame.BLEND_RGBA_MULT)
    return out


def _apply_alpha(img, alpha):
    if alpha >= 255:
        return img
    alpha = max(0, min(255, int(alpha)))
    out = img.copy()
    out.set_alpha(alpha)
    return out


def _scaled_size(img, rect, mode):
    iw, ih = img.get_size()
    if iw <= 0 or ih <= 0:
        return (1, 1)
    rw, rh = max(1, rect.width), max(1, rect.height)
    if mode == "stretch":
        return (rw, rh)
    if mode == "center":
        return (iw, ih)
    if mode == "fit_w":
        return (rw, max(1, int(ih * rw / iw)))
    if mode == "fit_h":
        return (max(1, int(iw * rh / ih)), rh)
    ratio_img = iw / ih
    ratio_rect = rw / rh
    if mode == "contain":
        if ratio_img > ratio_rect:
            nw = rw; nh = int(rw / ratio_img)
        else:
            nh = rh; nw = int(rh * ratio_img)
    else:  # cover
        if ratio_img > ratio_rect:
            nh = rh; nw = int(rh * ratio_img)
        else:
            nw = rw; nh = int(rw / ratio_img)
    return (max(1, nw), max(1, nh))


def _scale(img, size, smooth):
    """Escolhe entre scale (nearest) e smoothscale (bilinear)."""
    try:
        if smooth:
            return pygame.transform.smoothscale(img, size)
        return pygame.transform.scale(img, size)
    except Exception:
        return pygame.transform.scale(img, size)


def draw_image_in_rect(target, image, rect, mode="stretch",
                       tint=None, alpha=255, smooth=False):
    """
    Desenha `image` dentro de `rect`.
    `smooth=False` → nearest neighbor (pixel art).
    """
    if image is None or rect.width <= 0 or rect.height <= 0:
        return rect

    if mode not in MODES:
        mode = "stretch"

    img = image
    if tint:
        img = _apply_tint(img, tint)
    if alpha < 255:
        img = _apply_alpha(img, alpha)

    rw, rh = max(1, rect.width), max(1, rect.height)

    # Modos de repetição
    if mode in ("tile", "tile_h", "tile_v"):
        iw, ih = img.get_size()
        if mode == "tile_h":
            tile = _scale(img, (iw, rh), smooth)
            tile_w, tile_h = iw, rh
        elif mode == "tile_v":
            tile = _scale(img, (rw, ih), smooth)
            tile_w, tile_h = rw, ih
        else:
            tile = img
            tile_w, tile_h = iw, ih
        if tile_w <= 0 or tile_h <= 0:
            return rect
        old = target.get_clip()
        target.set_clip(rect.clip(old))
        y = rect.y
        while y < rect.bottom:
            x = rect.x
            while x < rect.right:
                target.blit(tile, (x, y))
                x += tile_w
            y += tile_h
        target.set_clip(old)
        return rect

    # Modos de escala única
    nw, nh = _scaled_size(img, rect, mode)
    if (nw, nh) != img.get_size():
        surf = _scale(img, (nw, nh), smooth)
    else:
        surf = img

    old = target.get_clip()
    target.set_clip(rect.clip(old))

    x = rect.x + (rw - nw) // 2
    y = rect.y + (rh - nh) // 2
    target.blit(surf, (x, y))

    target.set_clip(old)
    return pygame.Rect(x, y, nw, nh)