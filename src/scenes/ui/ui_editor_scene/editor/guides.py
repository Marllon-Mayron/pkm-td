# src/scenes/ui_editor_scene/editor/guides.py
"""Cálculo de snap e linhas de alinhamento."""
import pygame


def compute_guides_and_snap(dragged_rect, dragged_indices,
                             widgets_data, design_rect_fn,
                             design_w, design_h,
                             snap_threshold=6):
    """
    Retorna (dx, dy, guides_v, guides_h, strong_v, strong_h).
      - dx, dy: ajuste de snap
      - guides_v/h: conjuntos de x/y (design) que devem renderizar linhas
      - strong_*: subset com 2+ fontes reais (3+ no total) — cor mais forte
    """
    th = snap_threshold

    counts_x, counts_y = {}, {}
    for i, wd in enumerate(widgets_data):
        if i in dragged_indices:
            continue
        r = design_rect_fn(wd)
        for val in (r.left, r.centerx, r.right):
            counts_x.setdefault(val, set()).add(i)
        for val in (r.top, r.centery, r.bottom):
            counts_y.setdefault(val, set()).add(i)

    for val in (0, design_w // 2, design_w):
        counts_x.setdefault(val, set()).add(-1)
    for val in (0, design_h // 2, design_h):
        counts_y.setdefault(val, set()).add(-1)

    moved_x = (dragged_rect.left, dragged_rect.centerx, dragged_rect.right)
    moved_y = (dragged_rect.top, dragged_rect.centery, dragged_rect.bottom)

    best_dx, best_dist_x = 0, th + 1
    for v in moved_x:
        for t in counts_x:
            d = t - v; ad = abs(d)
            if ad < best_dist_x and ad <= th:
                best_dist_x, best_dx = ad, d

    best_dy, best_dist_y = 0, th + 1
    for v in moved_y:
        for t in counts_y:
            d = t - v; ad = abs(d)
            if ad < best_dist_y and ad <= th:
                best_dist_y, best_dy = ad, d

    final = pygame.Rect(int(dragged_rect.x + best_dx),
                        int(dragged_rect.y + best_dy),
                        dragged_rect.w, dragged_rect.h)
    final_x = (final.left, final.centerx, final.right)
    final_y = (final.top, final.centery, final.bottom)

    guides_v, guides_h = set(), set()
    strong_v, strong_h = set(), set()

    for v in final_x:
        for t, srcs in counts_x.items():
            if abs(t - v) <= 1:
                guides_v.add(t)
                real = len([s for s in srcs if s != -1])
                if real >= 2:
                    strong_v.add(t)
    for v in final_y:
        for t, srcs in counts_y.items():
            if abs(t - v) <= 1:
                guides_h.add(t)
                real = len([s for s in srcs if s != -1])
                if real >= 2:
                    strong_h.add(t)

    return best_dx, best_dy, guides_v, guides_h, strong_v, strong_h