# src/ui/color_picker.py
"""Seletor de cor RGB modal — sliders + paleta + OK/Cancel."""
import pygame
from src.ui.theme import FontBook, Palette, parse_color, to_hex


class ColorPicker:
    PRESETS = [
        "#FFFFFF", "#F8F8F0", "#C8C8C8", "#888888", "#404040", "#101010",
        "#F8B030", "#F88030", "#D84840", "#C83878", "#8840C8", "#4060C8",
        "#3090C8", "#30B890", "#48B858", "#80B840", "#A09840", "#F8C8A0",
    ]

    def __init__(self):
        self.open = False
        self.rect = pygame.Rect(0, 0, 400, 320)
        self.hex_str = "#FFFFFF"
        self.r = self.g = self.b = 255

        self._dragging = None
        self._on_confirm = None
        self._preset_rects = []
        self._ok_rect = pygame.Rect(0, 0, 0, 0)
        self._cancel_rect = pygame.Rect(0, 0, 0, 0)

        # Rects de sliders (recalculados em _layout)
        self.slider_r = pygame.Rect(0, 0, 0, 0)
        self.slider_g = pygame.Rect(0, 0, 0, 0)
        self.slider_b = pygame.Rect(0, 0, 0, 0)
        self.preview_rect = pygame.Rect(0, 0, 0, 0)
        self.hex_rect = pygame.Rect(0, 0, 0, 0)

    # =================================================================
    def open_with(self, hex_color, on_confirm=None, center=None):
        c = parse_color(hex_color, (255, 255, 255))
        self.r, self.g, self.b = c
        self.hex_str = to_hex(c) or "#FFFFFF"
        self.open = True
        self._on_confirm = on_confirm
        sfc = pygame.display.get_surface()
        if sfc:
            w, h = sfc.get_size()
            self.rect.center = center or (w // 2, h // 2)

    def close(self):
        self.open = False
        self._dragging = None

    def _sync_hex(self):
        self.hex_str = f"#{self.r:02X}{self.g:02X}{self.b:02X}"

    def _set_from_slider(self, which, mouse_x, bar):
        ratio = (mouse_x - bar.x) / max(1, bar.width)
        ratio = max(0.0, min(1.0, ratio))
        val = int(round(ratio * 255))
        if which == "r":   self.r = val
        elif which == "g": self.g = val
        else:              self.b = val
        self._sync_hex()

    # =================================================================
    def _layout(self):
        pad = 14
        x = self.rect.x + pad
        w = self.rect.width - pad * 2

        self.preview_rect = pygame.Rect(x, self.rect.y + pad, 60, 60)
        self.hex_rect = pygame.Rect(self.preview_rect.right + 10,
                                    self.rect.y + pad, w - 70, 60)

        sy = self.rect.y + pad + 76
        sl_h = 26
        gap = 12
        self.slider_r = pygame.Rect(x + 18, sy, w - 44, sl_h)
        self.slider_g = pygame.Rect(x + 18, sy + sl_h + gap, w - 44, sl_h)
        self.slider_b = pygame.Rect(x + 18, sy + (sl_h + gap) * 2, w - 44, sl_h)

        py = sy + (sl_h + gap) * 3 + 4
        cols = 9
        size = 26
        spacing = 6
        self._preset_rects = []
        for i, hv in enumerate(self.PRESETS):
            row = i // cols
            col = i % cols
            r = pygame.Rect(x + col * (size + spacing),
                            py + row * (size + spacing), size, size)
            self._preset_rects.append((hv, r))

        by = self.rect.bottom - pad - 34
        bw = 100
        self._cancel_rect = pygame.Rect(self.rect.right - pad - bw * 2 - 10, by, bw, 34)
        self._ok_rect = pygame.Rect(self.rect.right - pad - bw, by, bw, 34)

    # =================================================================
    def handle_event(self, event):
        if not self.open:
            return False
        self._layout()

        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            pos = event.pos
            for name, bar in (("r", self.slider_r),
                              ("g", self.slider_g),
                              ("b", self.slider_b)):
                if bar.collidepoint(pos):
                    self._dragging = name
                    self._set_from_slider(name, pos[0], bar)
                    return True
            for hv, r in self._preset_rects:
                if r.collidepoint(pos):
                    self.r, self.g, self.b = parse_color(hv, (255, 255, 255))
                    self._sync_hex()
                    return True
            if self._ok_rect.collidepoint(pos):
                if self._on_confirm:
                    self._on_confirm(self.hex_str)
                self.close()
                return True
            if self._cancel_rect.collidepoint(pos):
                self.close()
                return True
            if not self.rect.collidepoint(pos):
                self.close()
                return True
            return True

        if event.type == pygame.MOUSEBUTTONUP and event.button == 1:
            if self._dragging:
                self._dragging = None
                return True

        if event.type == pygame.MOUSEMOTION and self._dragging:
            for name, bar in (("r", self.slider_r),
                              ("g", self.slider_g),
                              ("b", self.slider_b)):
                if name == self._dragging:
                    self._set_from_slider(name, event.pos[0], bar)
                    return True

        if event.type == pygame.KEYDOWN:
            if event.key == pygame.K_ESCAPE:
                self.close(); return True
            if event.key == pygame.K_RETURN:
                if self._on_confirm:
                    self._on_confirm(self.hex_str)
                self.close(); return True
        return False

    # =================================================================
    def render(self, screen):
        if not self.open:
            return
        self._layout()

        ov = pygame.Surface(screen.get_size(), pygame.SRCALPHA)
        ov.fill((0, 0, 0, 140))
        screen.blit(ov, (0, 0))

        pygame.draw.rect(screen, (32, 36, 52), self.rect, border_radius=12)
        pygame.draw.rect(screen, Palette.GOLD, self.rect, 2, border_radius=12)

        t = FontBook.get(18, bold=True).render("ESCOLHER COR", True, Palette.GOLD)
        screen.blit(t, (self.rect.x + 14, self.rect.y + 8))

        # Preview
        pygame.draw.rect(screen, (self.r, self.g, self.b), self.preview_rect,
                         border_radius=6)
        pygame.draw.rect(screen, (220, 220, 240), self.preview_rect, 2,
                         border_radius=6)

        # Hex box
        pygame.draw.rect(screen, (20, 24, 36), self.hex_rect, border_radius=6)
        pygame.draw.rect(screen, (72, 88, 128), self.hex_rect, 2, border_radius=6)
        ht = FontBook.get(20, bold=True).render(self.hex_str, True, Palette.TEXT_LIGHT)
        screen.blit(ht, ht.get_rect(center=self.hex_rect.center))

        # Sliders
        for label, bar, val, col in (
            ("R", self.slider_r, self.r, (220, 90, 90)),
            ("G", self.slider_g, self.g, (90, 200, 90)),
            ("B", self.slider_b, self.b, (90, 130, 220)),
        ):
            lt = FontBook.get(15, bold=True).render(label, True, col)
            screen.blit(lt, (bar.x - 18, bar.centery - lt.get_height() // 2))
            pygame.draw.rect(screen, (20, 24, 36), bar, border_radius=6)
            fill_w = int(bar.width * (val / 255))
            if fill_w > 0:
                pygame.draw.rect(screen, col,
                                 (bar.x, bar.y, fill_w, bar.height),
                                 border_radius=6)
            pygame.draw.rect(screen, (80, 96, 130), bar, 2, border_radius=6)
            vt = FontBook.get(14, bold=True).render(str(val), True, Palette.TEXT_LIGHT)
            screen.blit(vt, (bar.right + 6, bar.centery - vt.get_height() // 2))

        # Presets
        for hv, r in self._preset_rects:
            c = parse_color(hv, (0, 0, 0))
            pygame.draw.rect(screen, c, r, border_radius=4)
            pygame.draw.rect(screen, (220, 220, 240), r, 1, border_radius=4)

        # Botões
        for r, txt, base, hov in (
            (self._cancel_rect, "Cancelar", (110, 55, 55), (150, 75, 75)),
            (self._ok_rect,     "OK",       (72, 152, 88), (104, 184, 120)),
        ):
            h = r.collidepoint(pygame.mouse.get_pos())
            pygame.draw.rect(screen, hov if h else base, r, border_radius=8)
            pygame.draw.rect(screen, Palette.GOLD if h else (80, 96, 130),
                             r, 2, border_radius=8)
            bt = FontBook.get(15, bold=True).render(txt, True, (255, 255, 255))
            screen.blit(bt, bt.get_rect(center=r.center))