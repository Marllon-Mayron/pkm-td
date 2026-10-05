# src/scenes/ui_editor_scene/editor/modals.py
"""Modais: LoadPicker (carregar layout) e ImagePicker (escolher imagem)."""
import pygame
from src.ui.theme import FontBook, Palette
from src.ui.screen_loader import _load_ui_image


class _BaseListPicker:
    ITEM_H = 28
    TITLE = "PICKER"

    def __init__(self):
        self.open = False
        self.rect = pygame.Rect(0, 0, 340, 400)
        self.items = []
        self.hover_idx = -1
        self.on_select = None
        self.scroll = 0

    def open_with(self, items, on_select, center=None):
        self.items = sorted(list(items))
        self.on_select = on_select
        self.open = True
        self.hover_idx = -1
        self.scroll = 0
        sfc = pygame.display.get_surface()
        if sfc:
            w, h = sfc.get_size()
            cx, cy = center or (w // 2, h // 2)
        else:
            cx, cy = 400, 300
        needed = 90 + max(1, len(self.items)) * self.ITEM_H
        self.rect.height = min(460, max(140, needed))
        self.rect.center = (cx, cy)

    def close(self):
        self.open = False

    def _list_top(self):
        return self.rect.y + 52

    def _hit_index(self, pos):
        top = self._list_top()
        for i in range(len(self.items)):
            r = pygame.Rect(self.rect.x + 8,
                            top + i * self.ITEM_H - self.scroll,
                            self.rect.width - 16, self.ITEM_H - 2)
            if r.collidepoint(pos):
                return i
        return -1

    def handle_event(self, event):
        if not self.open:
            return False

        if event.type == pygame.KEYDOWN:
            if event.key == pygame.K_ESCAPE:
                self.close(); return True

        if event.type == pygame.MOUSEMOTION:
            self.hover_idx = self._hit_index(event.pos)
            return True

        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            idx = self._hit_index(event.pos)
            if idx >= 0:
                if self.on_select:
                    self.on_select(self.items[idx])
                self.close()
                return True
            if not self.rect.collidepoint(event.pos):
                self.close()
            return True

        if event.type == pygame.MOUSEWHEEL:
            mx, my = pygame.mouse.get_pos()
            if self.rect.collidepoint(mx, my):
                total = len(self.items) * self.ITEM_H
                list_h = self.rect.height - 60
                max_s = max(0, total - list_h)
                self.scroll = max(0, min(max_s, self.scroll - event.y * 20))
                return True
        return True

    def render(self, screen, extra_draw=None):
        if not self.open:
            return
        ov = pygame.Surface(screen.get_size(), pygame.SRCALPHA)
        ov.fill((0, 0, 0, 140))
        screen.blit(ov, (0, 0))

        sh = self.rect.move(4, 6)
        sh_s = pygame.Surface(sh.size, pygame.SRCALPHA)
        pygame.draw.rect(sh_s, (0, 0, 0, 130), sh_s.get_rect(), border_radius=12)
        screen.blit(sh_s, sh.topleft)

        pygame.draw.rect(screen, (28, 34, 52), self.rect, border_radius=12)
        pygame.draw.rect(screen, Palette.GOLD, self.rect, 2, border_radius=12)

        t = FontBook.get(16, True).render(self.TITLE, True, Palette.GOLD)
        screen.blit(t, (self.rect.x + 14, self.rect.y + 10))
        sub = FontBook.get(12).render(self._subtitle(), True, (150, 160, 180))
        screen.blit(sub, (self.rect.x + 14, self.rect.y + 30))

        if not self.items:
            msg = FontBook.get(14).render("(vazio)", True, (140, 150, 170))
            screen.blit(msg, msg.get_rect(center=self.rect.center))
            return

        top = self._list_top()
        list_bottom = self.rect.bottom - 8
        clip = pygame.Rect(self.rect.x + 6, top,
                           self.rect.width - 12, list_bottom - top)
        old = screen.get_clip()
        screen.set_clip(clip)

        for i, name in enumerate(self.items):
            r = pygame.Rect(self.rect.x + 8,
                            top + i * self.ITEM_H - self.scroll,
                            self.rect.width - 16, self.ITEM_H - 2)
            if r.bottom < clip.top or r.y > clip.bottom:
                continue
            if i == self.hover_idx:
                pygame.draw.rect(screen, (60, 80, 120), r, border_radius=6)
                pygame.draw.rect(screen, Palette.GOLD, r, 1, border_radius=6)
            else:
                pygame.draw.rect(screen, (36, 44, 62), r, border_radius=6)

            text_x = r.x + 10
            if extra_draw is not None:
                extra_draw(screen, name, r, clip)
                text_x = r.x + 10 + 34

            nt = FontBook.get(14).render(name, True, Palette.TEXT_LIGHT)
            screen.blit(nt, (text_x, r.centery - nt.get_height() // 2))

        screen.set_clip(old)

        total = len(self.items) * self.ITEM_H
        list_h = clip.height
        if total > list_h:
            bar_x = self.rect.right - 10
            thumb_h = max(20, int(list_h * list_h / total))
            max_s = max(1, total - list_h)
            thumb_y = clip.y + int((list_h - thumb_h) * self.scroll / max_s)
            pygame.draw.rect(screen, (35, 42, 60),
                             (bar_x, clip.y, 3, list_h), border_radius=2)
            pygame.draw.rect(screen, (150, 170, 210),
                             (bar_x, thumb_y, 3, thumb_h), border_radius=2)

    def _subtitle(self):
        return f"{len(self.items)} item(s)"


class LoadPicker(_BaseListPicker):
    TITLE = "CARREGAR LAYOUT"

    def _subtitle(self):
        return f"{len(self.items)} layout(s) em res/ui_layouts/"


class ImagePicker(_BaseListPicker):
    TITLE = "ESCOLHER IMAGEM"

    def open_with(self, items, on_select, center=None):
        items = ["(nenhuma)"] + list(items)
        super().open_with(items, on_select, center)

    def _subtitle(self):
        return f"{max(0, len(self.items) - 1)} imagem(ns) em res/ui/"

    def render(self, screen):
        def draw_thumb(target, name, rect, clip):
            thumb = pygame.Rect(rect.x + 4, rect.y + 2,
                                rect.height - 4, rect.height - 4)
            pygame.draw.rect(target, (16, 20, 30), thumb, border_radius=4)
            if name == "(nenhuma)":
                f = FontBook.get(11).render("—", True, (150, 160, 180))
                target.blit(f, (thumb.centerx - f.get_width() // 2,
                                thumb.centery - f.get_height() // 2))
                return
            surf = _load_ui_image(name)
            if surf is not None:
                try:
                    scaled = pygame.transform.smoothscale(
                        surf, (thumb.width - 4, thumb.height - 4))
                    target.blit(scaled, (thumb.x + 2, thumb.y + 2))
                except Exception:
                    pass

        super().render(screen, extra_draw=draw_thumb)