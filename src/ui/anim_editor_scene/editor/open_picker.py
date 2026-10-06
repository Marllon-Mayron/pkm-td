"""Modal simples para abrir uma animacao salva."""
import pygame

from src.ui.theme import Palette, FontBook
from src.ui.anim_editor_scene.editor import scene_loader as SL


class OpenPicker:
    W = 520
    H = 440
    ROW_H = 26

    def __init__(self):
        self.open = False
        self.rect = pygame.Rect(0, 0, self.W, self.H)
        self.items = []            # [(category, name)]
        self.selected = 0
        self.scroll = 0
        self._row_rects = []
        self._btn_cancel = None
        self._btn_open = None
        self.on_select = None

    # ---------------------------------------------------------------
    def open_with(self, on_select, center=None):
        self.items = SL.list_all_animations() or []
        self.selected = 0
        self.scroll = 0
        self.on_select = on_select
        self.open = True
        sfc = pygame.display.get_surface()
        if sfc:
            w, h = sfc.get_size()
            cx, cy = center or (w // 2, h // 2)
            self.rect.center = (cx, cy)

    def close(self):
        self.open = False
        self.on_select = None

    # ---------------------------------------------------------------
    def _layout(self):
        r = self.rect
        pad = 14
        self._list_rect = pygame.Rect(
            r.x + pad, r.y + 48,
            r.width - pad * 2, r.height - 48 - 60)

        self._btn_cancel = pygame.Rect(
            r.right - pad - 100, r.bottom - pad - 32, 92, 30)
        self._btn_open = pygame.Rect(
            self._btn_cancel.left - 108, self._btn_cancel.y, 100, 30)

    # ---------------------------------------------------------------
    def handle_event(self, event) -> bool:
        if not self.open:
            return False
        self._layout()

        if event.type == pygame.KEYDOWN:
            if event.key == pygame.K_ESCAPE:
                self.close()
                return True
            if event.key == pygame.K_RETURN:
                self._apply_and_close()
                return True
            if event.key == pygame.K_DOWN:
                self.selected = min(len(self.items) - 1, self.selected + 1)
                return True
            if event.key == pygame.K_UP:
                self.selected = max(0, self.selected - 1)
                return True

        if event.type == pygame.MOUSEWHEEL:
            max_s = max(0, len(self.items)
                        - self._list_rect.height // self.ROW_H)
            self.scroll = max(0, min(max_s, self.scroll - event.y))
            return True

        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            pos = event.pos
            if not self.rect.collidepoint(pos):
                self.close()
                return True

            for idx, rect in self._row_rects:
                if rect.collidepoint(pos):
                    if idx == self.selected:
                        self._apply_and_close()
                    else:
                        self.selected = idx
                    return True

            if self._btn_cancel.collidepoint(pos):
                self.close()
                return True
            if self._btn_open.collidepoint(pos):
                self._apply_and_close()
                return True
            return True

        return True

    def _apply_and_close(self):
        if not (0 <= self.selected < len(self.items)):
            self.close()
            return
        cat, name = self.items[self.selected]
        cb = self.on_select
        self.close()
        if cb:
            try:
                cb(cat, name)
            except Exception as e:
                print(f"[OPEN_PICKER] erro: {e}")

    # ---------------------------------------------------------------
    def render(self, screen):
        if not self.open:
            return
        self._layout()

        # backdrop
        ov = pygame.Surface(screen.get_size(), pygame.SRCALPHA)
        ov.fill((0, 0, 0, 170))
        screen.blit(ov, (0, 0))

        # painel
        pygame.draw.rect(screen, (26, 30, 48), self.rect, border_radius=10)
        pygame.draw.rect(screen, Palette.GOLD, self.rect, 2, border_radius=10)

        title = FontBook.get(16, bold=True).render(
            "Abrir animacao", True, Palette.GOLD)
        screen.blit(title, (self.rect.x + 14, self.rect.y + 14))

        sub = FontBook.get(11).render(
            f"{len(self.items)} arquivos em res/animations/",
            True, (150, 160, 190))
        screen.blit(sub, (self.rect.x + 14, self.rect.y + 32))

        pygame.draw.line(screen, (60, 76, 110),
                         (self.rect.x + 10, self.rect.y + 46),
                         (self.rect.right - 10, self.rect.y + 46), 1)

        # lista
        pygame.draw.rect(screen, (16, 20, 32), self._list_rect, border_radius=6)
        pygame.draw.rect(screen, (60, 76, 110), self._list_rect, 1, border_radius=6)

        old = screen.get_clip()
        screen.set_clip(self._list_rect)

        self._row_rects = []
        visible = self._list_rect.height // self.ROW_H
        if self.selected < self.scroll:
            self.scroll = self.selected
        if self.selected >= self.scroll + visible:
            self.scroll = self.selected - visible + 1

        for i in range(self.scroll,
                       min(self.scroll + visible, len(self.items))):
            cat, name = self.items[i]
            ry = self._list_rect.y + (i - self.scroll) * self.ROW_H
            rr = pygame.Rect(self._list_rect.x + 2, ry,
                             self._list_rect.width - 4, self.ROW_H - 2)
            self._row_rects.append((i, rr))

            selected = (i == self.selected)
            hover = rr.collidepoint(pygame.mouse.get_pos())
            if selected:
                pygame.draw.rect(screen, (72, 108, 148), rr, border_radius=3)
                pygame.draw.rect(screen, Palette.GOLD, rr, 1, border_radius=3)
            elif hover:
                pygame.draw.rect(screen, (44, 56, 84), rr, border_radius=3)

            col = Palette.GOLD if selected else (220, 228, 240)
            cat_t = FontBook.get(11, bold=True).render(cat, True, (140, 180, 220))
            name_t = FontBook.get(13, bold=selected).render(name, True, col)

            screen.blit(cat_t, (rr.x + 8,
                                rr.centery - cat_t.get_height() // 2))
            screen.blit(name_t, (rr.x + 110,
                                 rr.centery - name_t.get_height() // 2))

        if not self.items:
            t = FontBook.get(12).render(
                "Nenhuma animacao salva em res/animations/",
                True, (170, 180, 210))
            screen.blit(t, (self._list_rect.centerx - t.get_width() // 2,
                            self._list_rect.centery - t.get_height() // 2))

        screen.set_clip(old)

        # scrollbar
        if len(self.items) > visible:
            thumb_h = max(20, int(self._list_rect.height * visible / len(self.items)))
            max_s = max(1, len(self.items) - visible)
            thumb_y = self._list_rect.y + int(
                (self._list_rect.height - thumb_h) * self.scroll / max_s)
            pygame.draw.rect(screen, (40, 48, 66),
                             (self._list_rect.right - 6, self._list_rect.y,
                              4, self._list_rect.height),
                             border_radius=2)
            pygame.draw.rect(screen, (150, 170, 210),
                             (self._list_rect.right - 6, thumb_y, 4, thumb_h),
                             border_radius=2)

        # botoes
        cancel_hover = self._btn_cancel.collidepoint(pygame.mouse.get_pos())
        bg = (120, 55, 55) if not cancel_hover else (170, 70, 70)
        pygame.draw.rect(screen, bg, self._btn_cancel, border_radius=6)
        pygame.draw.rect(screen, Palette.GOLD if cancel_hover else (160, 80, 80),
                         self._btn_cancel, 2, border_radius=6)
        ct = FontBook.get(13, bold=True).render("Cancelar", True, (240, 240, 250))
        screen.blit(ct, ct.get_rect(center=self._btn_cancel.center))

        open_hover = self._btn_open.collidepoint(pygame.mouse.get_pos())
        bg = (72, 152, 88) if not open_hover else (104, 184, 120)
        pygame.draw.rect(screen, bg, self._btn_open, border_radius=6)
        pygame.draw.rect(screen, Palette.GOLD if open_hover else (80, 96, 130),
                         self._btn_open, 2, border_radius=6)
        ot = FontBook.get(13, bold=True).render("Abrir", True, (240, 240, 250))
        screen.blit(ot, ot.get_rect(center=self._btn_open.center))