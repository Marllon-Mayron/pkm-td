# src/ui/layout.py
"""
Helpers de layout — centralizar, âncoras e grid.
Todos aceitam coords RELATIVAS (0.0 - 1.0) do viewport.
"""
import pygame

def _text_size(text, font):
    try:
        return font.size(text)
    except Exception:
        return (0, 0)


def text_fits(text, font, max_w, max_h):
    w, h = _text_size(text, font)
    return w <= max_w and h <= max_h


def split_wrap(text, font, max_w):
    """Quebra `text` em linhas que caibam em max_w."""
    words = str(text or "").split(" ")
    lines = []
    cur = ""
    for w in words:
        test = (cur + " " + w).strip()
        if _text_size(test, font)[0] <= max_w:
            cur = test
        else:
            if cur:
                lines.append(cur)
            cur = w
    if cur:
        lines.append(cur)
    return lines or [""]


def add_ellipsis(text, font, max_w, ellipsis="..."):
    """Corta `text` até caber em max_w, adicionando '...'."""
    text = str(text or "")
    if _text_size(text, font)[0] <= max_w:
        return text
    ell_w = _text_size(ellipsis, font)[0]
    if ell_w > max_w:
        return ""
    lo, hi = 0, len(text)
    while lo < hi:
        mid = (lo + hi + 1) // 2
        if _text_size(text[:mid], font)[0] + ell_w <= max_w:
            lo = mid
        else:
            hi = mid - 1
    return text[:lo] + ellipsis


def fit_font(text, font_factory, start_size, max_w, max_h, min_size=8,
             max_steps=64):
    """
    Diminui a fonte até o texto caber.
    `font_factory(size) -> pygame.Font`
    """
    size = max(min_size, int(start_size))
    font = font_factory(size)
    steps = 0
    while size > min_size and not text_fits(text, font, max_w, max_h):
        size -= 1
        font = font_factory(size)
        steps += 1
        if steps >= max_steps:
            break
    return font, size


def layout_text(text, font, max_w, max_h, text_fit="none",
                font_factory=None, start_size=None, min_size=8):
    """
    Retorna (lines: list[str], font: pygame.Font).

    text_fit:
      "none"        → 1 linha (sem processar)
      "shrink"      → encolhe até caber em 1 linha
      "wrap"        → quebra em várias linhas
      "ellipsis"    → 1 linha cortada com "..."
      "shrink_wrap" → encolhe E quebra se ainda não couber
    """
    text = str(text or "")

    if text_fit == "shrink" and font_factory is not None and start_size:
        font, _ = fit_font(text, font_factory, start_size,
                           max_w, max_h, min_size)
        return [text], font

    if text_fit == "ellipsis":
        return [add_ellipsis(text, font, max_w)], font

    if text_fit == "wrap":
        return split_wrap(text, font, max_w), font

    if text_fit == "shrink_wrap":
        # 1) tenta encolher até caber na largura
        work_font = font
        if font_factory is not None and start_size:
            work_font, _ = fit_font(text, font_factory, start_size,
                                    max_w, max_h, min_size)
        # 2) se ainda assim não couber em 1 linha, quebra
        if _text_size(text, work_font)[0] <= max_w:
            return [text], work_font
        return split_wrap(text, work_font, max_w), work_font

    # "none"
    return [text], font

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
                       shadow_color=None, shadow_offset=(2, 2),
                       text_fit="none", font_factory=None,
                       start_size=None, min_font_size=8,
                       line_gap=2):
    """
    Renderiza texto (com opcional ajuste automático) centralizado em `rect`.
    """
    max_w = max(4, rect.width - 8)
    max_h = max(4, rect.height)

    lines, final_font = layout_text(
        text, font, max_w, max_h,
        text_fit=text_fit,
        font_factory=font_factory,
        start_size=start_size,
        min_size=min_font_size,
    )

    line_h = final_font.get_height() + line_gap
    total_h = len(lines) * line_h - line_gap
    y0 = rect.centery - total_h // 2

    for i, line in enumerate(lines):
        if not line:
            continue
        surf = final_font.render(line, True, color)
        x = rect.centerx - surf.get_width() // 2
        y = y0 + i * line_h

        if shadow_color:
            sh = final_font.render(line, True, shadow_color)
            target.blit(sh, (x + shadow_offset[0], y + shadow_offset[1]))
        target.blit(surf, (x, y))