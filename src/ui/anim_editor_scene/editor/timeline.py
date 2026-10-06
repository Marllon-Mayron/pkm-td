"""Timeline — trilhas de atores e layers, playhead, keyframes."""
import pygame

from src.ui.theme import Palette, FontBook
from src.ui.anim_editor_scene.editor.scrollbar import ScrollBar


class TimelineWidget:
    HEADER_H = 30
    ROW_H = 24
    ROW_GAP = 4
    SCROLLBAR_W = 10

    def __init__(self):
        self.rect = pygame.Rect(0, 0, 0, 0)
        self.header_rect = pygame.Rect(0, 0, 0, 0)
        self.area = pygame.Rect(0, 0, 0, 0)
        self.rows = []            # [(kind, idx, rect)]
        self.scrollbar = ScrollBar(width=self.SCROLLBAR_W, wheel_step=2)
        self.controller = None

    # =================================================================
    def layout(self, rect, controller):
        self.rect = rect
        self.controller = controller
        self.header_rect = pygame.Rect(rect.x, rect.y, rect.width,
                                       self.HEADER_H)
        ay = rect.y + self.HEADER_H + 4
        aw = rect.width - self.SCROLLBAR_W - 6
        ah = rect.height - self.HEADER_H - 8
        self.area = pygame.Rect(rect.x, ay, aw, ah)

        total = self._total_rows()
        row_h = self.ROW_H + self.ROW_GAP
        visible = max(1, ah // row_h)

        track = pygame.Rect(rect.right - self.SCROLLBAR_W - 2,
                            ay, self.SCROLLBAR_W, ah)
        self.scrollbar.set(track, total=max(1, total),
                           visible=visible, wheel_area=self.area)
        self._recalc_tracks()

    def _total_rows(self):
        c = self.controller
        if c is None:
            return 0
        return (len(c.current_anim.actors) +
                len(c.current_anim.layers) + 2)  # 2 headers

    def _recalc_tracks(self):
        c = self.controller
        if c is None:
            return
        row_h = self.ROW_H + self.ROW_GAP
        visible = max(1, self.area.height // row_h)
        start = self.scrollbar.scroll

        # constrói lista unificada
        rows_def = []
        rows_def.append(("header", "ATORES"))
        for i, _ in enumerate(c.current_anim.actors):
            rows_def.append(("actor", i))
        rows_def.append(("header", "EFEITOS"))
        for i, _ in enumerate(c.current_anim.layers):
            rows_def.append(("layer", i))

        self.rows = []
        for r in range(visible):
            idx = start + r
            if idx >= len(rows_def):
                break
            y = self.area.y + r * row_h
            rect = pygame.Rect(self.area.x, y, self.area.width, self.ROW_H)
            self.rows.append((rows_def[idx], rect))

    # =================================================================
    def frame_to_x(self, frame):
        total = max(1, self.controller.current_anim.duration_frames)
        w = max(1, self.area.width - 140)
        return self.area.x + 130 + int((frame / total) * w)

    def x_to_frame(self, x):
        total = max(1, self.controller.current_anim.duration_frames)
        w = max(1, self.area.width - 140)
        rel = max(0, min(w, x - (self.area.x + 130)))
        return int((rel / w) * total)

    # =================================================================
    def handle_event(self, event) -> bool:
        c = self.controller
        if c is None:
            return False

        if self.scrollbar.handle_event(event):
            self._recalc_tracks()
            return True

        if event.type == pygame.MOUSEWHEEL:
            if self.scrollbar.handle_wheel(event.y, pygame.mouse.get_pos()):
                self._recalc_tracks()
                return True

        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            if self.header_rect.collidepoint(event.pos):
                c.current_frame = float(self.x_to_frame(event.pos[0]))
                c.dragging_playhead = True
                c._on_frame_changed()
                return True
            for row_def, rect in self.rows:
                if not rect.collidepoint(event.pos):
                    continue
                kind = row_def[0]
                if kind == "header":
                    return True
                c.current_frame = float(self.x_to_frame(event.pos[0]))
                c._on_frame_changed()

                if kind == "actor":
                    idx = row_def[1]
                    c.select_actor(idx)
                    actor = c.current_anim.actors[idx]
                    # procura keyframe perto do clique
                    for kfi, kf in enumerate(actor.keyframes):
                        kx = self.frame_to_x(kf.f)
                        if abs(event.pos[0] - kx) <= 6:
                            # começa drag de keyframe
                            c._drag_kf = (kind, idx, kfi)
                            return True
                else:
                    idx = row_def[1]
                    c.select_layer(idx)
                    layer = c.current_anim.layers[idx]
                    if getattr(layer, "type", "") == "sprite":
                        for kfi, kf in enumerate(layer.keyframes):
                            kx = self.frame_to_x(kf.f)
                            if abs(event.pos[0] - kx) <= 6:
                                c._drag_kf = (kind, idx, kfi)
                                return True
                return True
            return False

        if event.type == pygame.MOUSEBUTTONUP and event.button == 1:
            c.dragging_playhead = False
            if getattr(c, "_drag_kf", None):
                c._drag_kf = None
            return False

        if event.type == pygame.MOUSEMOTION:
            if c.dragging_playhead:
                c.current_frame = float(self.x_to_frame(event.pos[0]))
                c._on_frame_changed()
                return True
            if getattr(c, "_drag_kf", None):
                kind, idx, kfi = c._drag_kf
                new_f = self.x_to_frame(event.pos[0])
                if kind == "actor":
                    kfs = c.current_anim.actors[idx].keyframes
                    if 0 <= kfi < len(kfs):
                        kfs[kfi].f = max(0, new_f)
                        kfs.sort(key=lambda k: k.f)
                        c.mark_dirty()
                        c._on_frame_changed()
                else:
                    layer = c.current_anim.layers[idx]
                    if getattr(layer, "type", "") == "sprite":
                        kfs = layer.keyframes
                        if 0 <= kfi < len(kfs):
                            kfs[kfi].f = max(0, new_f)
                            kfs.sort(key=lambda k: k.f)
                            c.mark_dirty()
                            c._on_frame_changed()
                return True
        return False

    # =================================================================
    def render(self, screen):
        c = self.controller
        if c is None:
            return

        pygame.draw.rect(screen, (14, 18, 30), self.rect)
        pygame.draw.rect(screen, (60, 80, 120), self.rect, 2)

        # Régua
        pygame.draw.rect(screen, (24, 30, 48), self.header_rect)
        pygame.draw.line(screen, (60, 80, 120),
                         (self.header_rect.x, self.header_rect.bottom),
                         (self.header_rect.right, self.header_rect.bottom))

        total = max(1, c.current_anim.duration_frames)
        for f in range(0, total + 1, 10):
            x = self.frame_to_x(f)
            pygame.draw.line(screen, (100, 120, 160),
                             (x, self.header_rect.bottom - 6),
                             (x, self.header_rect.bottom), 1)
            if f % 30 == 0:
                t = FontBook.get(11).render(str(f), True, (150, 160, 190))
                screen.blit(t, (x + 2, self.header_rect.y + 6))

        # Área
        old = screen.get_clip()
        screen.set_clip(self.area)

        for row_def, rect in self.rows:
            kind = row_def[0]
            if kind == "header":
                pygame.draw.rect(screen, (28, 36, 54), rect, border_radius=3)
                t = FontBook.get(11, bold=True).render(
                    row_def[1], True, (150, 170, 210))
                screen.blit(t, (rect.x + 8, rect.centery - t.get_height() // 2))
                continue

            idx = row_def[1]
            obj = (c.current_anim.actors[idx] if kind == "actor"
                   else c.current_anim.layers[idx])
            selected = (c.selection == (kind, idx))

            bg = (44, 56, 82) if selected else (24, 30, 46)
            pygame.draw.rect(screen, bg, rect, border_radius=3)

            # faixa esquerda com nome
            name_w = 120
            pygame.draw.rect(screen, (18, 24, 38),
                             (rect.x, rect.y, name_w, rect.height),
                             border_radius=3)
            name = getattr(obj, "id", "?")
            col = Palette.GOLD if selected else (190, 200, 220)
            t = FontBook.get(11, bold=True).render(name[:18], True, col)
            screen.blit(t, (rect.x + 6, rect.centery - t.get_height() // 2))

            # barra de visibilidade
            vf = getattr(obj, "visible_frames", None)
            if vf:
                s = int(vf[0]) if len(vf) > 0 else 0
                e = int(vf[1]) if len(vf) > 1 and vf[1] >= 0 else total
                x1 = self.frame_to_x(s)
                x2 = self.frame_to_x(e)
                vis = pygame.Rect(x1, rect.y + 4, max(2, x2 - x1), rect.height - 8)
                col = (60, 100, 70) if selected else (40, 66, 50)
                pygame.draw.rect(screen, col, vis, border_radius=2)

            # keyframes
            if kind == "actor":
                for kfi, kf in enumerate(obj.keyframes):
                    kx = self.frame_to_x(kf.f)
                    ky = rect.centery
                    is_sel = (selected and c._drag_kf
                              and c._drag_kf[2] == kfi)
                    color = Palette.GOLD if is_sel else (140, 200, 240)
                    size = 6
                    pts = [(kx, ky - size), (kx + size, ky),
                           (kx, ky + size), (kx - size, ky)]
                    pygame.draw.polygon(screen, color, pts)
                    pygame.draw.polygon(screen, (20, 24, 36), pts, 1)
            elif getattr(obj, "type", "") == "sprite":
                for kfi, kf in enumerate(obj.keyframes):
                    kx = self.frame_to_x(kf.f)
                    ky = rect.centery
                    color = (200, 220, 250)
                    size = 5
                    pts = [(kx, ky - size), (kx + size, ky),
                           (kx, ky + size), (kx - size, ky)]
                    pygame.draw.polygon(screen, color, pts)
                    pygame.draw.polygon(screen, (20, 24, 36), pts, 1)

        # Playhead
        px = self.frame_to_x(int(c.current_frame))
        pygame.draw.line(screen, (90, 200, 255),
                         (px, self.header_rect.bottom),
                         (px, self.area.bottom), 2)

        screen.set_clip(old)

        # Playhead no header
        px = self.frame_to_x(int(c.current_frame))
        pygame.draw.line(screen, (90, 200, 255),
                         (px, self.header_rect.y),
                         (px, self.header_rect.bottom), 2)
        pygame.draw.polygon(screen, (90, 200, 255), [
            (px, self.header_rect.y),
            (px - 5, self.header_rect.y - 5),
            (px + 5, self.header_rect.y - 5),
        ])

        self.scrollbar.render(screen)