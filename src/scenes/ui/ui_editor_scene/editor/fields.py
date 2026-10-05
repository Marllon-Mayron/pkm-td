# src/scenes/ui_editor_scene/editor/fields.py
"""Campos de entrada do editor."""
import pygame
from src.ui.theme import FontBook, Palette, parse_color
from src.ui.screen_loader import _load_ui_image


class Clipboard:
    _root = None
    _tried = False

    @classmethod
    def _get_root(cls):
        if cls._tried:
            return cls._root
        cls._tried = True
        try:
            import tkinter as tk
            r = tk.Tk()
            r.withdraw()
            cls._root = r
        except Exception as e:
            print(f"[Clipboard] indisponível: {e}")
            cls._root = None
        return cls._root

    @classmethod
    def get(cls):
        root = cls._get_root()
        if not root:
            return ""
        try:
            return root.clipboard_get()
        except Exception:
            return ""

    @classmethod
    def set(cls, text):
        root = cls._get_root()
        if not root:
            return False
        try:
            root.clipboard_clear()
            root.clipboard_append(str(text))
            root.update()
            return True
        except Exception:
            return False


class TextField:
    MAX_LEN = 512

    def __init__(self, rect, text="", placeholder="", on_change=None):
        self.rect = rect
        self.text = str(text)
        self.placeholder = placeholder
        self.focused = False
        self._t = 0.0
        self.on_change = on_change

    def _emit(self):
        if self.on_change:
            try: self.on_change(self.text)
            except Exception: pass

    def handle_event(self, event):
        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            was = self.focused
            self.focused = self.rect.collidepoint(event.pos)
            return (self.focused != was) or self.focused

        if event.type == pygame.KEYDOWN and self.focused:
            mods = pygame.key.get_mods()
            ctrl = bool(mods & pygame.KMOD_CTRL)

            if ctrl and event.key == pygame.K_c:
                Clipboard.set(self.text); return "copy"
            if ctrl and event.key == pygame.K_v:
                pasted = Clipboard.get()
                if pasted:
                    self.text = (self.text + pasted)[:self.MAX_LEN]
                    self._emit()
                return "paste"
            if ctrl and event.key == pygame.K_x:
                Clipboard.set(self.text)
                self.text = ""; self._emit()
                return "cut"
            if ctrl and event.key == pygame.K_a:
                return "select_all"

            if event.key == pygame.K_BACKSPACE:
                self.text = self.text[:-1]; self._emit()
            elif event.key in (pygame.K_RETURN, pygame.K_TAB):
                self.focused = False
            elif event.key == pygame.K_DELETE:
                self.text = self.text[:-1]; self._emit()
            elif event.unicode and event.unicode.isprintable():
                if len(self.text) < self.MAX_LEN:
                    self.text += event.unicode
                    self._emit()
            return True
        return False

    def update(self, dt):
        self._t += dt

    def render(self, screen):
        bg = (24, 28, 42) if not self.focused else (36, 46, 68)
        border = Palette.GOLD if self.focused else (72, 88, 128)
        pygame.draw.rect(screen, bg, self.rect, border_radius=6)
        pygame.draw.rect(screen, border, self.rect, 2, border_radius=6)
        font = FontBook.get(15)
        txt = self.text
        col = Palette.TEXT_LIGHT
        if not txt and self.placeholder and not self.focused:
            txt = self.placeholder; col = (110, 120, 140)
        if self.focused and int(self._t * 2) % 2 == 0:
            txt += "|"
        s = font.render(txt, True, col)
        clip = self.rect.inflate(-8, -4)
        old = screen.get_clip()
        screen.set_clip(clip)
        screen.blit(s, (self.rect.x + 6,
                        self.rect.centery - s.get_height() // 2))
        screen.set_clip(old)


class ColorField:
    def __init__(self, rect, text=""):
        self.rect = rect
        self.swatch_rect = pygame.Rect(rect.right + 6, rect.y + 2,
                                       rect.height - 4, rect.height - 4)
        self.field = TextField(rect, text, "#RRGGBB")

    def handle_event(self, event):
        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            if self.swatch_rect.collidepoint(event.pos):
                return "open_picker"
        return self.field.handle_event(event)

    def update(self, dt):
        self.field.update(dt)

    def render(self, screen):
        self.field.render(screen)
        col = parse_color(self.field.text, None)
        if col is None:
            pygame.draw.rect(screen, (60, 60, 72), self.swatch_rect,
                             border_radius=4)
            pygame.draw.rect(screen, (100, 100, 120), self.swatch_rect, 1,
                             border_radius=4)
        else:
            pygame.draw.rect(screen, col, self.swatch_rect, border_radius=4)
            pygame.draw.rect(screen, (240, 240, 250), self.swatch_rect, 2,
                             border_radius=4)

    @property
    def text(self): return self.field.text
    @text.setter
    def text(self, v): self.field.text = str(v)
    @property
    def focused(self): return self.field.focused
    @focused.setter
    def focused(self, v):
        try: self.field.focused = bool(v)
        except Exception: pass


class BoolField:
    def __init__(self, rect, value=False):
        self.rect = rect
        self.value = bool(value)
        self._hover = False

    def handle_event(self, event):
        if event.type == pygame.MOUSEMOTION:
            self._hover = self.rect.collidepoint(event.pos)
        elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            if self.rect.collidepoint(event.pos):
                self.value = not self.value
                return True
        return False

    def update(self, dt): pass

    def render(self, screen):
        s = 20
        box = pygame.Rect(self.rect.x, self.rect.centery - s // 2, s, s)
        bg = (72, 152, 88) if self.value else (48, 54, 76)
        if self._hover:
            bg = tuple(min(255, c + 20) for c in bg)
        pygame.draw.rect(screen, bg, box, border_radius=4)
        pygame.draw.rect(screen, (100, 116, 160), box, 2, border_radius=4)
        if self.value:
            pygame.draw.lines(screen, (255, 255, 255), False,
                              [(box.x + 4, box.centery),
                               (box.centerx - 1, box.bottom - 5),
                               (box.right - 4, box.y + 4)], 3)
        font = FontBook.get(13)
        lbl = font.render("true" if self.value else "false",
                          True, Palette.TEXT_LIGHT)
        screen.blit(lbl, (box.right + 10,
                          self.rect.centery - lbl.get_height() // 2))

    @property
    def text(self): return "true" if self.value else "false"
    @text.setter
    def text(self, v):
        s = str(v).strip().lower()
        self.value = s in ("1", "true", "yes", "on", "sim")
    @property
    def focused(self): return False
    @focused.setter
    def focused(self, v):
        pass  # read-only, ignora


class EditorDropdown:
    ITEM_H = 24
    MAX_VISIBLE = 10

    def __init__(self, rect, options, value, on_change=None):
        self.rect = rect
        self.options = list(options) or ["-"]
        self.value = value if value is not None else self.options[0]
        self.open = False
        self.on_change = on_change
        self.hover_idx = -1
        self._list_rect = None
        self._scroll = 0

    def handle_event(self, event):
        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            if self.open and self._list_rect and \
                    self._list_rect.collidepoint(event.pos):
                idx = self._scroll + \
                      (event.pos[1] - self._list_rect.y) // self.ITEM_H
                if 0 <= idx < len(self.options):
                    self.value = self.options[idx]
                    self.open = False
                    if self.on_change:
                        self.on_change(self.value)
                return True
            if self.rect.collidepoint(event.pos):
                self.open = not self.open
                if self.open:
                    try:
                        i = self.options.index(self.value)
                        self._scroll = max(
                            0, min(i - self.MAX_VISIBLE // 2,
                                   len(self.options) - self.MAX_VISIBLE))
                    except ValueError:
                        self._scroll = 0
                return True
            if self.open:
                self.open = False
        elif event.type == pygame.MOUSEWHEEL:
            if self.open and self._list_rect:
                mx, my = pygame.mouse.get_pos()
                if self._list_rect.collidepoint(mx, my):
                    self._scroll -= event.y
                    self._scroll = max(
                        0, min(self._scroll,
                               max(0, len(self.options) - self.MAX_VISIBLE)))
                    return True
        elif event.type == pygame.MOUSEMOTION:
            if self.open and self._list_rect and \
                    self._list_rect.collidepoint(event.pos):
                self.hover_idx = self._scroll + \
                                 (event.pos[1] - self._list_rect.y) // self.ITEM_H
            else:
                self.hover_idx = -1
        return False

    def _list_rect_now(self):
        visible = min(self.MAX_VISIBLE, len(self.options))
        h = self.ITEM_H * visible + 4
        y = self.rect.bottom + 2
        sw = pygame.display.get_surface()
        if sw and y + h > sw.get_height() - 4:
            y = max(4, self.rect.y - h - 2)
        return pygame.Rect(self.rect.x, y, self.rect.width, h)

    def render_closed(self, screen):
        pygame.draw.rect(screen, (24, 28, 42), self.rect, border_radius=6)
        border = Palette.GOLD if self.open else (72, 88, 128)
        pygame.draw.rect(screen, border, self.rect, 2, border_radius=6)
        font = FontBook.get(14)
        s = font.render(str(self.value), True, Palette.TEXT_LIGHT)
        old = screen.get_clip()
        screen.set_clip(self.rect.inflate(-4, 0))
        screen.blit(s, (self.rect.x + 6,
                        self.rect.centery - s.get_height() // 2))
        screen.set_clip(old)
        arr = font.render("v", True, (180, 190, 210))
        screen.blit(arr, (self.rect.right - 14,
                          self.rect.centery - arr.get_height() // 2))

    def render_open_overlay(self, screen):
        if not self.open:
            return
        lr = self._list_rect_now()
        self._list_rect = lr
        sh = lr.move(3, 4)
        sh_s = pygame.Surface(sh.size, pygame.SRCALPHA)
        pygame.draw.rect(sh_s, (0, 0, 0, 130), sh_s.get_rect(), border_radius=6)
        screen.blit(sh_s, sh.topleft)
        pygame.draw.rect(screen, (20, 24, 36), lr, border_radius=6)
        pygame.draw.rect(screen, Palette.GOLD, lr, 2, border_radius=6)

        font = FontBook.get(14)
        old = screen.get_clip()
        screen.set_clip(lr.inflate(-2, -2))
        visible = min(self.MAX_VISIBLE, len(self.options))
        for row in range(visible):
            idx = self._scroll + row
            if idx >= len(self.options):
                break
            opt = self.options[idx]
            ir = pygame.Rect(lr.x + 2, lr.y + 2 + row * self.ITEM_H,
                             lr.width - 4, self.ITEM_H)
            if idx == self.hover_idx:
                pygame.draw.rect(screen, (48, 60, 90), ir, border_radius=4)
            if opt == self.value:
                pygame.draw.rect(screen, (32, 48, 42), ir, border_radius=4)
            cc = Palette.GOLD if opt == self.value else Palette.TEXT_LIGHT
            s = font.render(str(opt), True, cc)
            screen.blit(s, (ir.x + 6, ir.centery - s.get_height() // 2))
        screen.set_clip(old)

        if len(self.options) > visible:
            bar_x = lr.right - 6
            bar_top = lr.y + 2
            bar_h = lr.height - 4
            thumb_h = max(20, int(bar_h * visible / len(self.options)))
            max_s = max(1, len(self.options) - visible)
            thumb_y = bar_top + int((bar_h - thumb_h) * self._scroll / max_s)
            pygame.draw.rect(screen, (60, 70, 95),
                             (bar_x, bar_top, 3, bar_h), border_radius=2)
            pygame.draw.rect(screen, (180, 200, 240),
                             (bar_x, thumb_y, 3, thumb_h), border_radius=2)


class ImageField:
    """Mostra thumbnail + nome + botão '...' que abre o picker."""
    def __init__(self, rect, name="", on_open=None):
        self.rect = rect
        self.name = str(name) if name else ""
        self.on_open = on_open
        self._hover = False

    def handle_event(self, event):
        if event.type == pygame.MOUSEMOTION:
            self._hover = self.rect.collidepoint(event.pos)
        elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            if self.rect.collidepoint(event.pos):
                if self.on_open:
                    self.on_open()
                return True
        return False

    def update(self, dt): pass

    def render(self, screen):
        pygame.draw.rect(screen, (24, 28, 42), self.rect, border_radius=6)
        border = Palette.GOLD if self._hover else (72, 88, 128)
        pygame.draw.rect(screen, border, self.rect, 2, border_radius=6)

        thumb = pygame.Rect(self.rect.x + 3, self.rect.y + 2,
                            self.rect.height - 4, self.rect.height - 4)
        pygame.draw.rect(screen, (16, 20, 30), thumb, border_radius=4)
        if self.name:
            surf = _load_ui_image(self.name)
            if surf is not None:
                try:
                    scaled = pygame.transform.smoothscale(
                        surf, (thumb.width - 4, thumb.height - 4))
                    screen.blit(scaled, (thumb.x + 2, thumb.y + 2))
                except Exception:
                    pass

        font = FontBook.get(13)
        label = self.name or "(nenhuma)"
        col = Palette.TEXT_LIGHT if self.name else (140, 150, 170)
        max_w = self.rect.width - thumb.width - 30
        while label and font.size(label)[0] > max_w:
            label = label[:-1]
        txt = font.render(label, True, col)
        tx = thumb.right + 6
        screen.blit(txt, (tx, self.rect.centery - txt.get_height() // 2))

        btn = pygame.Rect(self.rect.right - 22, self.rect.y + 2,
                          20, self.rect.height - 4)
        pygame.draw.rect(screen, (60, 76, 110), btn, border_radius=4)
        pygame.draw.rect(screen, (140, 160, 210), btn, 1, border_radius=4)
        dots = FontBook.get(14, bold=True).render("...", True, (220, 230, 250))
        screen.blit(dots, (btn.centerx - dots.get_width() // 2,
                           btn.centery - dots.get_height() // 2))

    @property
    def text(self): return self.name
    @text.setter
    def text(self, v): self.name = str(v) if v else ""
    @property
    def focused(self): return False
    @focused.setter
    def focused(self, v):
        pass  # read-only