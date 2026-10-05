# src/ui/layout.py
"""
Helpers de layout — centralizar, âncoras e grid.
Todos aceitam coords RELATIVAS (0.0 - 1.0) do viewport.
"""
import pygame


class Anchor:
    TOP_LEFT      = "tl"
    TOP_CENTER    = "tc"
    TOP_RIGHT     = "tr"
    CENTER_LEFT   = "cl"
    CENTER        = "c"
    CENTER_RIGHT  = "cr"
    BOTTOM_LEFT   = "bl"
    BOTTOM_CENTER = "bc"
    BOTTOM_RIGHT  = "br"


def viewport(screen_manager):
    """Retorna o viewport como Rect (a 'área útil' do jogo)."""
    return pygame.Rect(
        screen_manager.viewport_x,
        screen_manager.viewport_y,
        screen_manager.viewport_width,
        screen_manager.viewport_height,
    )


def rel_rect(vp, x, y, w, h, anchor=Anchor.TOP_LEFT):
    """
    Constrói um Rect a partir de coords relativas (0..1) do viewport.
    Anchor inválido (None, "-", string vazia) cai em TOP_LEFT.
    """
    if anchor not in (
        Anchor.TOP_LEFT, Anchor.TOP_CENTER, Anchor.TOP_RIGHT,
        Anchor.CENTER_LEFT, Anchor.CENTER, Anchor.CENTER_RIGHT,
        Anchor.BOTTOM_LEFT, Anchor.BOTTOM_CENTER, Anchor.BOTTOM_RIGHT,
    ):
        anchor = Anchor.TOP_LEFT

    rw = int(w * vp.width)
    rh = int(h * vp.height)
    ax = vp.x + int(x * vp.width)
    ay = vp.y + int(y * vp.height)

    if anchor == Anchor.TOP_LEFT:      return pygame.Rect(ax, ay, rw, rh)
    if anchor == Anchor.TOP_CENTER:    return pygame.Rect(ax - rw // 2, ay, rw, rh)
    if anchor == Anchor.TOP_RIGHT:     return pygame.Rect(ax - rw, ay, rw, rh)
    if anchor == Anchor.CENTER_LEFT:   return pygame.Rect(ax, ay - rh // 2, rw, rh)
    if anchor == Anchor.CENTER:        return pygame.Rect(ax - rw // 2, ay - rh // 2, rw, rh)
    if anchor == Anchor.CENTER_RIGHT:  return pygame.Rect(ax - rw, ay - rh // 2, rw, rh)
    if anchor == Anchor.BOTTOM_LEFT:   return pygame.Rect(ax, ay - rh, rw, rh)
    if anchor == Anchor.BOTTOM_CENTER: return pygame.Rect(ax - rw // 2, ay - rh, rw, rh)
    if anchor == Anchor.BOTTOM_RIGHT:  return pygame.Rect(ax - rw, ay - rh, rw, rh)
    return pygame.Rect(ax, ay, rw, rh)


def stack_vertical(vp, x, y, w, h,
                   count, gap=0.012,
                   anchor=Anchor.TOP_LEFT):
    """Empilha N Rects verticalmente. Retorna lista de Rects."""
    rects = []
    for i in range(count):
        ry = y + i * (h + gap)
        rects.append(rel_rect(vp, x, ry, w, h, anchor))
    return rects


def grid(vp, cols, rows,
         area_rect=None,
         padding=16, gap=8):
    """
    Gera `cols x rows` Rects dentro de `area_rect` (ou viewport inteiro).
    Útil para listas de cards.
    """
    base = area_rect if area_rect else viewport(vp)
    inner = base.inflate(-padding * 2, -padding * 2)
    cell_w = (inner.width - gap * (cols - 1)) // cols
    cell_h = (inner.height - gap * (rows - 1)) // rows

    out = []
    for r in range(rows):
        for c in range(cols):
            x = inner.x + c * (cell_w + gap)
            y = inner.y + r * (cell_h + gap)
            out.append(pygame.Rect(x, y, cell_w, cell_h))
    return out


def font_size_for(vp, factor, minimum=14, maximum=72):
    """Tamanho de fonte proporcional à altura do viewport."""
    return max(minimum, min(maximum, int(vp.height * factor)))


def draw_text_centered(target, text, font, color, rect,
                        shadow_color=None, shadow_offset=(2, 2)):
    """Renderiza texto centralizado em `rect`, com sombra opcional."""
    surf = font.render(text, True, color)
    x = rect.centerx - surf.get_width() // 2
    y = rect.centery - surf.get_height() // 2
    if shadow_color:
        sh = font.render(text, True, shadow_color)
        target.blit(sh, (x + shadow_offset[0], y + shadow_offset[1]))
    target.blit(surf, (x, y))