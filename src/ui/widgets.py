# src/ui/widgets.py
"""
Widgets reutilizáveis.

Convenções:
  - Todos aceitam z, font_name, bold, text_color, fill_color,
    border_color, tab, click_sound, hover_sound, click_volume, hover_volume
  - Button e Panel aceitam imagem de fundo:
      bg_image, bg_image_mode, bg_tint, bg_image_alpha
  - Button e Panel aceitam ajuste de borda:
      border_width, draw_border, border_radius
"""
import pygame

from src.ui.theme import (Palette, FontBook, BUTTON_STYLES,
                          lerp_color, darken, lighten)
from src.ui.windowskin import panel_skin
from src.ui.layout import draw_text_centered
from src.ui.sound_helper import play_ui_sound
from src.ui.image_draw import draw_image_in_rect


# =====================================================================
# BASE
# =====================================================================
class Widget:
    def __init__(self, wid, rect, z=0):
        self.id = wid
        self.rect = rect
        self.visible = True
        self.enabled = True
        self.z = int(z)
        self.font_name = "default"
        self.bold = False
        self.text_color = None
        self.fill_color = None
        self.border_color = None
        self.tab = None

        self.click_sound = "CLICK"
        self.hover_sound = None
        self.click_volume = None
        self.hover_volume = None

        self._hover = False
        self._pressed = False

    def _play_click(self):
        play_ui_sound(self.click_sound, volume=self.click_volume)

    def _play_hover(self):
        play_ui_sound(self.hover_sound, volume=self.hover_volume)

    def handle_event(self, event): return False
    def update(self, dt): pass
    def render(self, screen): pass


# =====================================================================
# BOTÃO
# =====================================================================
class Button(Widget):
    def __init__(self, wid, rect, label, on_click=None,
                 style="primary", font_size=None,
                 icon_surface=None, icon_size=None,
                 icon_position="left", icon_gap=6,
                 tooltip="",
                 z=0, font_name="default", bold=True,
                 text_color=None, fill_color=None, border_color=None,
                 bg_image=None, bg_image_mode="stretch",
                 bg_tint=None, bg_image_alpha=255,
                 border_width=2, border_radius=10, draw_border=True,
                 draw_shadow=True,
                 tab=None,
                 click_sound="CLICK", hover_sound=None,
                 click_volume=None, hover_volume=None):
        super().__init__(wid, rect, z=z)
        self.label = label
        self.on_click = on_click
        self.style_name = style
        self.font_size = font_size or max(16, int(rect.height * 0.5))
        self.icon = icon_surface
        self.icon_size = icon_size or min(32, max(12, rect.height - 12))
        self.icon_position = icon_position   # left|right|top|center
        self.icon_gap = icon_gap
        self.tooltip = tooltip
        self.font_name = font_name
        self.bold = bool(bold)
        self.text_color = text_color
        self.fill_color = fill_color
        self.border_color = border_color
        self.tab = tab
        self.click_sound = click_sound
        self.hover_sound = hover_sound
        self.click_volume = click_volume
        self.hover_volume = hover_volume

        # Novos
        self.bg_image = bg_image
        self.bg_image_mode = bg_image_mode
        self.bg_tint = bg_tint
        self.bg_image_alpha = bg_image_alpha
        self.border_width = int(border_width)
        self.border_radius = int(border_radius)
        self.draw_border = bool(draw_border)
        self.draw_shadow = bool(draw_shadow)

        self._scale = 1.0
        self._target_scale = 1.0
        self._glow = 0.0

    # -----------------------------------------------------------------
    def handle_event(self, event):
        if not self.visible or not self.enabled:
            return False
        if event.type == pygame.MOUSEMOTION:
            was = self._hover
            self._hover = self.rect.collidepoint(event.pos)
            if self._hover and not was:
                self._target_scale = 1.04
                self._play_hover()
            elif not self._hover and was:
                self._target_scale = 1.0
        elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            if self._hover:
                self._pressed = True
                self._target_scale = 0.96
                return True
        elif event.type == pygame.MOUSEBUTTONUP and event.button == 1:
            if self._pressed and self._hover:
                self._pressed = False
                self._target_scale = 1.04
                self._play_click()
                if self.on_click:
                    self.on_click(self)
                return True
            self._pressed = False
            self._target_scale = 1.0
        return False

    def update(self, dt):
        self._scale += (self._target_scale - self._scale) * min(1, dt * 18)
        if self._hover and self.enabled:
            self._glow = min(1.0, self._glow + dt * 4)
        else:
            self._glow = max(0.0, self._glow - dt * 4)

    # -----------------------------------------------------------------
    def render(self, screen):
        if not self.visible:
            return
        style = BUTTON_STYLES.get(self.style_name, BUTTON_STYLES["primary"])
        if not self.enabled:
            style = BUTTON_STYLES["disabled"]

        rect = self.rect
        if abs(self._scale - 1.0) > 0.001:
            wo = int(rect.width * (self._scale - 1) / 2)
            ho = int(rect.height * (self._scale - 1) / 2)
            rect = rect.inflate(wo * 2, ho * 2); rect.center = self.rect.center

        # Sombra
        if self.draw_shadow:
            sh = rect.move(3, 4)
            sh_s = pygame.Surface(sh.size, pygame.SRCALPHA)
            pygame.draw.rect(sh_s, (0, 0, 0, 120), sh_s.get_rect(),
                             border_radius=self.border_radius)
            screen.blit(sh_s, sh.topleft)

        # Fundo
        if self.bg_image is not None:
            draw_image_in_rect(screen, self.bg_image, rect,
                               mode=self.bg_image_mode,
                               tint=self.bg_tint,
                               alpha=self.bg_image_alpha)
        else:
            if self._pressed:                     base = style["fill_press"]
            elif self._hover and self.enabled:    base = style["fill_hover"]
            else:                                 base = style["fill"]
            fill = self.fill_color if self.fill_color else base

            grad = pygame.Surface(rect.size, pygame.SRCALPHA)
            top = lighten(fill, 0.18); bot = darken(fill, 0.12)
            for y in range(rect.height):
                t = y / max(1, rect.height - 1)
                pygame.draw.line(grad, lerp_color(top, bot, t),
                                 (0, y), (rect.width, y))
            mask = pygame.Surface(rect.size, pygame.SRCALPHA)
            pygame.draw.rect(mask, (255, 255, 255, 255), mask.get_rect(),
                             border_radius=self.border_radius)
            grad.blit(mask, (0, 0), special_flags=pygame.BLEND_RGBA_MULT)
            screen.blit(grad, rect.topleft)

        # Borda
        if self.draw_border and self.border_width > 0:
            border = self.border_color if self.border_color else \
                     (style["border_hover"] if (self._hover and self.enabled)
                      else style["border"])
            pygame.draw.rect(screen, border, rect, self.border_width,
                             border_radius=self.border_radius)

        # Highlight interno
        if self.enabled and self.draw_border:
            hi = pygame.Rect(rect.x + 3, rect.y + 2, rect.width - 6, 2)
            hi_s = pygame.Surface(hi.size, pygame.SRCALPHA)
            hi_s.fill((255, 255, 255, 60))
            screen.blit(hi_s, hi.topleft)

        # Ícone + texto
        font = FontBook.get(self.font_size, bold=self.bold, name=self.font_name)
        tcol = self.text_color if self.text_color else style["text"]

        if self.icon is not None:
            self._render_with_icon(screen, rect, font, tcol)
        else:
            draw_text_centered(screen, self.label, font, tcol, rect,
                               shadow_color=(0, 0, 0, 130),
                               shadow_offset=(2, 2))

        # Glow hover
        if self._hover and self.enabled and self._glow > 0:
            a = int(60 * self._glow)
            glow = pygame.Surface(rect.size, pygame.SRCALPHA)
            pygame.draw.rect(glow, (Palette.GOLD[0], Palette.GOLD[1],
                                    Palette.GOLD[2], a),
                             glow.get_rect(), border_radius=self.border_radius)
            screen.blit(glow, rect.topleft,
                        special_flags=pygame.BLEND_RGBA_ADD)

    def _render_with_icon(self, screen, rect, font, tcol):
        isize = int(self.icon_size)
        try:
            icon = pygame.transform.smoothscale(self.icon, (isize, isize))
        except Exception:
            icon = self.icon
            isize = max(icon.get_width(), icon.get_height())

        pos = self.icon_position
        pad = 8
        if pos == "center":
            ix = rect.centerx - isize // 2
            iy = rect.centery - isize // 2
            screen.blit(icon, (ix, iy))
            return

        if pos == "top":
            total_h = isize + self.icon_gap + font.get_height()
            iy = rect.centery - total_h // 2
            ix = rect.centerx - isize // 2
            screen.blit(icon, (ix, iy))
            text_rect = pygame.Rect(rect.x, iy + isize + self.icon_gap,
                                    rect.width, font.get_height())
            draw_text_centered(screen, self.label, font, tcol, text_rect,
                               shadow_color=(0, 0, 0, 130), shadow_offset=(2, 2))
            return

        # left / right
        if pos == "right":
            ix = rect.right - pad - isize
            tx = rect.x + pad
            tw = rect.width - isize - self.icon_gap - pad * 2
        else:  # left
            ix = rect.x + pad
            tx = ix + isize + self.icon_gap
            tw = rect.right - tx - pad
        iy = rect.centery - isize // 2
        screen.blit(icon, (ix, iy))
        text_rect = pygame.Rect(tx, rect.y, tw, rect.height)
        draw_text_centered(screen, self.label, font, tcol, text_rect,
                           shadow_color=(0, 0, 0, 130), shadow_offset=(2, 2))


# =====================================================================
# PAINEL
# =====================================================================
class Panel(Widget):
    def __init__(self, wid, rect, title=None, title_color=None, skin=None,
                 z=0, font_name="default", bold=True,
                 text_color=None, fill_color=None, border_color=None,
                 bg_image=None, bg_image_mode="stretch",
                 bg_tint=None, bg_image_alpha=255,
                 border_width=2, border_radius=10, draw_border=True,
                 draw_shadow=True,
                 tab=None):
        super().__init__(wid, rect, z=z)
        self.title = title
        self.title_color = title_color or Palette.TEXT_DARK
        self.skin = skin or panel_skin
        self.font_name = font_name
        self.bold = bool(bold)
        self.text_color = text_color
        self.fill_color = fill_color
        self.border_color = border_color
        self.tab = tab

        self.bg_image = bg_image
        self.bg_image_mode = bg_image_mode
        self.bg_tint = bg_tint
        self.bg_image_alpha = bg_image_alpha
        self.border_width = int(border_width)
        self.border_radius = int(border_radius)
        self.draw_border = bool(draw_border)
        self.draw_shadow = bool(draw_shadow)

    def render(self, screen):
        if not self.visible:
            return
        self.skin.render(
            screen, self.rect,
            draw_shadow=self.draw_shadow,
            border_color=self.border_color,
            fill_override=self.fill_color,
            border_width=self.border_width,
            draw_border=self.draw_border,
            bg_image=self.bg_image,
            bg_image_mode=self.bg_image_mode,
            bg_tint=self.bg_tint,
            bg_image_alpha=self.bg_image_alpha,
            radius=self.border_radius,
        )
        if self.title:
            font = FontBook.get(max(16, int(self.rect.height * 0.08)),
                                bold=self.bold, name=self.font_name)
            bar_h = font.get_height() + 10
            bar = pygame.Rect(self.rect.x + 2, self.rect.y + 2,
                              self.rect.width - 4, bar_h)
            bar_s = pygame.Surface(bar.size, pygame.SRCALPHA)
            pygame.draw.rect(bar_s, (72, 88, 128, 60), bar_s.get_rect(),
                             border_radius=max(2, self.border_radius - 2))
            screen.blit(bar_s, bar.topleft)
            tcol = self.text_color or self.title_color
            draw_text_centered(screen, self.title, font, tcol, bar,
                               shadow_color=(255, 255, 255, 80),
                               shadow_offset=(1, 1))


# =====================================================================
# LABEL — inalterado, mas com text_color que já existia
# =====================================================================
class Label(Widget):
    def __init__(self, wid, rect, text, color=None, size=20, bold=False,
                 align="center", z=0, font_name="default",
                 text_color=None, fill_color=None, border_color=None, tab=None):
        super().__init__(wid, rect, z=z)
        self.text = text
        self.color = color or Palette.TEXT_DARK
        self.size = size
        self.bold = bool(bold)
        self.align = align
        self.font_name = font_name
        self.text_color = text_color
        self.fill_color = fill_color
        self.border_color = border_color
        self.tab = tab

    def render(self, screen):
        if not self.visible:
            return
        font = FontBook.get(self.size, bold=self.bold, name=self.font_name)
        col = self.text_color or self.color
        surf = font.render(str(self.text), True, col)
        if self.align == "center":  x = self.rect.centerx - surf.get_width() // 2
        elif self.align == "right": x = self.rect.right - surf.get_width()
        else:                       x = self.rect.x
        y = self.rect.centery - surf.get_height() // 2
        screen.blit(surf, (x, y))


# =====================================================================
# LIST VIEW
# =====================================================================
class ListView(Widget):
    ROW_H = 34

    def __init__(self, wid, rect, items=None, on_select=None,
                 z=0, font_name="default", bold=False,
                 text_color=None, fill_color=None, border_color=None, tab=None,
                 click_sound="CLICK", hover_sound=None,
                 click_volume=None, hover_volume=None):
        super().__init__(wid, rect, z=z)
        self.items = items or []
        self.on_select = on_select
        self.scroll = 0
        self._hover_index = -1
        self.font_name = font_name
        self.bold = bool(bold)
        self.text_color = text_color
        self.fill_color = fill_color
        self.border_color = border_color
        self.tab = tab
        self.click_sound = click_sound
        self.hover_sound = hover_sound
        self.click_volume = click_volume
        self.hover_volume = hover_volume

    def _visible_rows(self):
        return max(1, (self.rect.height - 16) // self.ROW_H)

    def _max_scroll(self):
        return max(0, len(self.items) - self._visible_rows())

    def handle_event(self, event):
        if not self.visible or not self.enabled:
            return False
        if event.type == pygame.MOUSEWHEEL:
            mx, my = pygame.mouse.get_pos()
            if self.rect.collidepoint(mx, my):
                self.scroll -= event.y
                self.scroll = max(0, min(self._max_scroll(), self.scroll))
                return True
        if event.type == pygame.MOUSEMOTION:
            old = self._hover_index
            self._hover_index = -1
            if self.rect.collidepoint(event.pos):
                rel = event.pos[1] - self.rect.y - 8
                idx = self.scroll + rel // self.ROW_H
                if 0 <= idx < len(self.items):
                    self._hover_index = idx
            if self._hover_index != old and self._hover_index >= 0:
                self._play_hover()
        elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            if 0 <= self._hover_index < len(self.items) and self.on_select:
                self._play_click()
                self.on_select(self._hover_index)
                return True
        return False

    def render(self, screen):
        if not self.visible:
            return
        panel_skin.render(screen, self.rect,
                          border_color=self.border_color,
                          fill_override=self.fill_color)
        clip = self.rect.inflate(-12, -12)
        old = screen.get_clip()
        screen.set_clip(clip)
        y = clip.y
        vis = self._visible_rows()
        for i in range(self.scroll, min(len(self.items), self.scroll + vis)):
            row = pygame.Rect(clip.x, y, clip.width, self.ROW_H - 2)
            if i == self._hover_index:
                hl = pygame.Surface(row.size, pygame.SRCALPHA)
                pygame.draw.rect(hl, (72, 88, 128, 80), hl.get_rect(),
                                 border_radius=6)
                screen.blit(hl, row.topleft)
                pygame.draw.rect(screen, Palette.GOLD, row, 1, border_radius=6)
            font = FontBook.get(20, bold=self.bold, name=self.font_name)
            col = self.text_color or Palette.TEXT_DARK
            txt = font.render(str(self.items[i]), True, col)
            screen.blit(txt, (row.x + 12, row.centery - txt.get_height() // 2))
            y += self.ROW_H
        screen.set_clip(old)


# =====================================================================
# IMAGE BOX
# =====================================================================
class ImageBox(Widget):
    def __init__(self, wid, rect, surface=None, skin=None, z=0,
                 font_name="default", text_color=None,
                 fill_color=None, border_color=None, tab=None,
                 bg_image_mode="contain"):
        super().__init__(wid, rect, z=z)
        self.surface = surface
        self.skin = skin
        self.font_name = font_name
        self.text_color = text_color
        self.fill_color = fill_color
        self.border_color = border_color
        self.tab = tab
        self.bg_image_mode = bg_image_mode

    def render(self, screen):
        if not self.visible:
            return
        if self.skin:
            self.skin.render(screen, self.rect,
                             border_color=self.border_color,
                             fill_override=self.fill_color)
        if self.surface is None:
            return
        inner = self.rect.inflate(-12, -12)
        draw_image_in_rect(screen, self.surface, inner,
                           mode=self.bg_image_mode)


# =====================================================================
# CHECKBOX
# =====================================================================
class Checkbox(Widget):
    def __init__(self, wid, rect, label="", checked=False, on_toggle=None,
                 z=0, font_name="default", bold=True,
                 text_color=None, fill_color=None, border_color=None, tab=None,
                 click_sound="CLICK", hover_sound=None,
                 click_volume=None, hover_volume=None):
        super().__init__(wid, rect, z=z)
        self.label = label
        self.checked = bool(checked)
        self.on_toggle = on_toggle
        self.font_name = font_name
        self.bold = bool(bold)
        self.text_color = text_color
        self.fill_color = fill_color
        self.border_color = border_color
        self.tab = tab
        self.click_sound = click_sound
        self.hover_sound = hover_sound
        self.click_volume = click_volume
        self.hover_volume = hover_volume

    def _box_rect(self):
        # Caixa pequena, limitada a 22px, mesmo se o widget for alto.
        size = min(22, max(12, self.rect.height // 2))
        if size > self.rect.width - 4:
            size = max(10, self.rect.width - 4)
        y = self.rect.centery - size // 2
        return pygame.Rect(self.rect.x, y, size, size)

    def handle_event(self, event):
        if not self.visible or not self.enabled:
            return False
        if event.type == pygame.MOUSEMOTION:
            was = self._hover
            self._hover = self.rect.collidepoint(event.pos)
            if self._hover and not was:
                self._play_hover()
        elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            if self.rect.collidepoint(event.pos):
                self.checked = not self.checked
                self._play_click()
                if self.on_toggle:
                    self.on_toggle(self.checked)
                return True
        return False

    def render(self, screen):
        if not self.visible:
            return
        box = self._box_rect()
        border_col = self.border_color or Palette.BORDER_DARK
        fill_off   = self.fill_color or (60, 60, 72)
        fill_on    = self.fill_color or (72, 152, 88)
        fill = fill_on if self.checked else fill_off
        if self._hover:
            fill = lighten(fill, 0.12)
        pygame.draw.rect(screen, fill, box, border_radius=4)
        pygame.draw.rect(screen, border_col, box, 2, border_radius=4)
        if self.checked:
            pygame.draw.lines(screen, (255, 255, 255), False,
                              [(box.x + 4, box.centery),
                               (box.centerx - 1, box.bottom - 5),
                               (box.right - 4, box.y + 4)], 3)
        if self.label:
            font = FontBook.get(max(14, int(box.height * 0.7)),
                                bold=self.bold, name=self.font_name)
            col = self.text_color or Palette.TEXT_LIGHT
            txt = font.render(self.label, True, col)
            screen.blit(txt, (box.right + 10,
                              self.rect.centery - txt.get_height() // 2))


# =====================================================================
# SLIDER
# =====================================================================
class Slider(Widget):
    def __init__(self, wid, rect, value=0.5, min_val=0.0, max_val=1.0,
                 on_change=None, z=0,
                 font_name="default", text_color=None,
                 fill_color=None, border_color=None, tab=None,
                 click_sound=None, hover_sound=None,
                 click_volume=None, hover_volume=None):
        super().__init__(wid, rect, z=z)
        self.value = float(value)
        self.min_val = float(min_val)
        self.max_val = float(max_val)
        self.on_change = on_change
        self.dragging = False
        self.font_name = font_name
        self.text_color = text_color
        self.fill_color = fill_color
        self.border_color = border_color
        self.tab = tab
        self.click_sound = click_sound
        self.hover_sound = hover_sound
        self.click_volume = click_volume
        self.hover_volume = hover_volume

    def _ratio(self):
        rng = max(1e-6, self.max_val - self.min_val)
        return max(0.0, min(1.0, (self.value - self.min_val) / rng))

    def _set_from_x(self, x):
        r = (x - self.rect.x) / max(1, self.rect.width)
        r = max(0.0, min(1.0, r))
        self.value = self.min_val + r * (self.max_val - self.min_val)
        if self.on_change:
            self.on_change(self.value)

    def handle_event(self, event):
        if not self.visible or not self.enabled:
            return False
        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            if self.rect.collidepoint(event.pos):
                self.dragging = True
                self._set_from_x(event.pos[0])
                self._play_click()
                return True
        elif event.type == pygame.MOUSEBUTTONUP and event.button == 1:
            if self.dragging:
                self.dragging = False; return True
        elif event.type == pygame.MOUSEMOTION:
            if self.dragging:
                self._set_from_x(event.pos[0]); return True
            was = self._hover
            self._hover = self.rect.collidepoint(event.pos)
            if self._hover and not was:
                self._play_hover()
        return False

    def render(self, screen):
        if not self.visible:
            return

        # Track com altura limitada, centralizado verticalmente.
        # O widget pode ser mais alto (área de clique maior), mas o
        # visual fica contido.
        track_h = min(self.rect.height, 16)
        track = pygame.Rect(
            self.rect.x,
            self.rect.centery - track_h // 2,
            self.rect.width,
            track_h,
        )

        bg = self.fill_color or (48, 54, 76)
        border = self.border_color or Palette.BORDER_DARK
        pygame.draw.rect(screen, bg, track, border_radius=6)

        r = self._ratio()
        fill_w = int(track.width * r)
        if fill_w > 0:
            fill_rect = pygame.Rect(track.x, track.y, fill_w, track_h)
            top = lighten(Palette.GOLD, 0.10)
            bot = darken(Palette.GOLD, 0.15)
            grad = pygame.Surface(fill_rect.size, pygame.SRCALPHA)
            for y in range(fill_rect.height):
                t = y / max(1, fill_rect.height - 1)
                pygame.draw.line(grad, lerp_color(top, bot, t),
                                 (0, y), (fill_rect.width, y))
            mask = pygame.Surface(fill_rect.size, pygame.SRCALPHA)
            pygame.draw.rect(mask, (255, 255, 255, 255), mask.get_rect(),
                             border_radius=6)
            grad.blit(mask, (0, 0), special_flags=pygame.BLEND_RGBA_MULT)
            screen.blit(grad, fill_rect.topleft)

        pygame.draw.rect(screen, border, track, 2, border_radius=6)

        thumb_w = 12
        thumb_h = track_h + 8
        thumb_x = track.x + fill_w - thumb_w // 2
        thumb = pygame.Rect(thumb_x, track.centery - thumb_h // 2,
                            thumb_w, thumb_h)
        tc = (240, 240, 250) if self.dragging else (200, 210, 230)
        pygame.draw.rect(screen, tc, thumb, border_radius=4)
        pygame.draw.rect(screen, (60, 70, 90), thumb, 1, border_radius=4)


# =====================================================================
# DROPDOWN (runtime)
# =====================================================================
class Dropdown(Widget):
    ITEM_H = 28

    def __init__(self, wid, rect, options=None, value=None,
                 on_change=None, z=0, font_name="default", bold=False,
                 text_color=None, fill_color=None, border_color=None, tab=None,
                 click_sound="CLICK", hover_sound=None,
                 click_volume=None, hover_volume=None):
        super().__init__(wid, rect, z=z)
        self.options = list(options or ["-"])
        self.value = value if value is not None else (
            self.options[0] if self.options else None)
        self.on_change = on_change
        self.open = False
        self._hover_idx = -1
        self._list_rect = None
        self._saved_z = z
        self.font_name = font_name
        self.bold = bool(bold)
        self.text_color = text_color
        self.fill_color = fill_color
        self.border_color = border_color
        self.tab = tab
        self.click_sound = click_sound
        self.hover_sound = hover_sound
        self.click_volume = click_volume
        self.hover_volume = hover_volume

    def _open(self):
        self._saved_z = self.z; self.z = 99999; self.open = True

    def _close(self):
        self.z = self._saved_z; self.open = False; self._list_rect = None

    def handle_event(self, event):
        if not self.visible or not self.enabled:
            return False
        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            if self.open and self._list_rect and self._list_rect.collidepoint(event.pos):
                idx = (event.pos[1] - self._list_rect.y) // self.ITEM_H
                if 0 <= idx < len(self.options):
                    self.value = self.options[idx]
                    self._close()
                    self._play_click()
                    if self.on_change:
                        self.on_change(self.value)
                return True
            if self.rect.collidepoint(event.pos):
                if self.open: self._close()
                else:
                    self._open(); self._play_click()
                return True
            if self.open:
                self._close()
        elif event.type == pygame.MOUSEMOTION:
            was_hover = self._hover
            self._hover = self.rect.collidepoint(event.pos)
            if self._hover and not was_hover:
                self._play_hover()
            if self.open and self._list_rect and self._list_rect.collidepoint(event.pos):
                self._hover_idx = (event.pos[1] - self._list_rect.y) // self.ITEM_H
            else:
                self._hover_idx = -1
        return False

    def _compute_list_rect(self):
        h = self.ITEM_H * len(self.options) + 4
        y = self.rect.bottom + 2
        sfc = pygame.display.get_surface()
        if sfc and y + h > sfc.get_height() - 4:
            y = max(4, self.rect.y - h - 2)
        return pygame.Rect(self.rect.x, y, self.rect.width, h)

    def render(self, screen):
        if not self.visible:
            return
        bg = self.fill_color or (24, 28, 42)
        border = self.border_color or (Palette.GOLD if self.open
                                       else Palette.BORDER_DARK)
        pygame.draw.rect(screen, bg, self.rect, border_radius=6)
        pygame.draw.rect(screen, border, self.rect, 2, border_radius=6)
        font = FontBook.get(max(14, int(self.rect.height * 0.55)),
                            bold=self.bold, name=self.font_name)
        col = self.text_color or Palette.TEXT_LIGHT
        s = font.render(str(self.value), True, col)
        screen.blit(s, (self.rect.x + 8,
                        self.rect.centery - s.get_height() // 2))
        arrow = font.render("v", True, (180, 190, 210))
        screen.blit(arrow, (self.rect.right - 16,
                            self.rect.centery - arrow.get_height() // 2))
        if not self.open:
            return
        lr = self._compute_list_rect()
        self._list_rect = lr
        bg2 = darken(bg, 0.05)
        pygame.draw.rect(screen, bg2, lr, border_radius=6)
        pygame.draw.rect(screen, Palette.GOLD, lr, 2, border_radius=6)
        for i, opt in enumerate(self.options):
            ir = pygame.Rect(lr.x + 2, lr.y + 2 + i * self.ITEM_H,
                             lr.width - 4, self.ITEM_H)
            if i == self._hover_idx:
                pygame.draw.rect(screen, (48, 60, 90), ir, border_radius=4)
            if opt == self.value:
                pygame.draw.rect(screen, (32, 48, 42), ir, border_radius=4)
            cc = Palette.GOLD if opt == self.value else (self.text_color or
                                                         Palette.TEXT_LIGHT)
            t = font.render(str(opt), True, cc)
            screen.blit(t, (ir.x + 8, ir.centery - t.get_height() // 2))


# =====================================================================
# TAB PANEL
# =====================================================================
class TabPanel(Widget):
    def __init__(self, wid, rect, tabs=None, current_tab=None,
                 on_change=None, z=0, font_name="default", bold=True,
                 text_color=None, fill_color=None, border_color=None, tab=None,
                 click_sound="CLICK", hover_sound=None,
                 click_volume=None, hover_volume=None):
        super().__init__(wid, rect, z=z)
        self.tabs = list(tabs or ["Tab 1"])
        self.current_tab = current_tab or (self.tabs[0] if self.tabs else None)
        self.on_change = on_change
        self.font_name = font_name
        self.bold = bool(bold)
        self.text_color = text_color
        self.fill_color = fill_color
        self.border_color = border_color
        self.tab = tab
        self.click_sound = click_sound
        self.hover_sound = hover_sound
        self.click_volume = click_volume
        self.hover_volume = hover_volume
        self._hover_idx = -1

    def _tab_rects(self):
        n = max(1, len(self.tabs))
        w = self.rect.width // n
        h = max(28, int(self.rect.height * 0.12))
        return [(name,
                 pygame.Rect(self.rect.x + i * w, self.rect.y, w, h))
                for i, name in enumerate(self.tabs)]

    def _content_rect(self):
        if not self.tabs:
            return self.rect
        _, r0 = self._tab_rects()[0]
        return pygame.Rect(self.rect.x, self.rect.y + r0.height,
                           self.rect.width, self.rect.height - r0.height)

    def handle_event(self, event):
        if not self.visible or not self.enabled:
            return False
        if event.type == pygame.MOUSEMOTION:
            old = self._hover_idx
            self._hover_idx = -1
            for i, (_, r) in enumerate(self._tab_rects()):
                if r.collidepoint(event.pos):
                    self._hover_idx = i
                    break
            if self._hover_idx != old and self._hover_idx >= 0:
                self._play_hover()
        elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            for name, r in self._tab_rects():
                if r.collidepoint(event.pos):
                    if name != self.current_tab:
                        self.current_tab = name
                        self._play_click()
                        if self.on_change:
                            self.on_change(name)
                    return True
        return False

    def render(self, screen):
        if not self.visible:
            return
        content = self._content_rect()
        panel_skin.render(screen, content,
                          border_color=self.border_color,
                          fill_override=self.fill_color)
        if not self.tabs:
            return
        font = FontBook.get(max(14, int(self.rect.height * 0.07)),
                            bold=self.bold, name=self.font_name)
        for i, (name, r) in enumerate(self._tab_rects()):
            is_active = (name == self.current_tab)
            is_hover = (i == self._hover_idx)
            if is_active:
                bg = self.fill_color or (72, 88, 128)
                bd = Palette.GOLD
                tc = self.text_color or Palette.TEXT_LIGHT
            elif is_hover:
                bg = (self.fill_color or (48, 60, 96))
                bd = Palette.BORDER_MID
                tc = self.text_color or Palette.TEXT_LIGHT
            else:
                bg = (32, 40, 58)
                bd = Palette.BORDER_DARK
                tc = self.text_color or (170, 180, 200)
            pygame.draw.rect(screen, bg, r,
                             border_top_left_radius=8,
                             border_top_right_radius=8)
            pygame.draw.rect(screen, bd, r, 2,
                             border_top_left_radius=8,
                             border_top_right_radius=8)
            t = font.render(str(name), True, tc)
            screen.blit(t, t.get_rect(center=r.center))
            if is_active:
                pygame.draw.line(screen, Palette.GOLD,
                                 (r.x + 8, r.bottom - 2),
                                 (r.right - 8, r.bottom - 2), 2)