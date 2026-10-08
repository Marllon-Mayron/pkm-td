# src/ui/widgets.py
"""
Widgets reutilizáveis.

Novidades desta versão:
  - border_style: "solid" | "dashed" | "dotted" | "none" (em Panel e Button)
  - ListView com scrollbar visual + drag + mouse wheel
  - Dropdown com drop_dir: "down" | "up"
  - Divider: linha horizontal/vertical com espessura, cor e estilo
  - Table: grid de headers + rows com colunas proporcionais
"""
import pygame
import math

from src.ui.theme import (Palette, FontBook, BUTTON_STYLES,
                          lerp_color, darken, lighten,
                          with_alpha, color_alpha)
from src.ui.windowskin import panel_skin
from src.ui.layout import draw_text_centered
from src.ui.sound_helper import play_ui_sound
from src.ui.image_draw import draw_image_in_rect
from src.ui.layout import draw_text_centered, layout_text


# =====================================================================
# HELPERS DE BORDA
# =====================================================================
def _scale_sprite(surface, size, pixel_art=True):
    try:
        if pixel_art:
            return pygame.transform.scale(surface, size)
        return pygame.transform.smoothscale(surface, size)
    except Exception:
        return pygame.transform.scale(surface, size)


def _draw_side_styled(screen, x1, y1, x2, y2, thickness, color, style):
    """Desenha UMA linha horizontal ou vertical com estilo."""
    if style == "none" or thickness <= 0:
        return
    horizontal = (y1 == y2)

    if style == "solid":
        if horizontal:
            pygame.draw.rect(screen, color, (x1, y1, x2 - x1, thickness))
        else:
            pygame.draw.rect(screen, color, (x1, y1, thickness, y2 - y1))
        return

    if style == "dotted":
        dash = max(1, thickness)
        gap = max(2, thickness * 2)
    else:  # dashed
        dash = max(4, thickness * 4)
        gap = max(3, thickness * 2)

    if horizontal:
        x = x1
        while x < x2:
            seg = min(dash, x2 - x)
            pygame.draw.rect(screen, color, (x, y1, seg, thickness))
            x += dash + gap
    else:
        y = y1
        while y < y2:
            seg = min(dash, y2 - y)
            pygame.draw.rect(screen, color, (x1, y, thickness, seg))
            y += dash + gap


def _draw_border_box(screen, rect, color, thickness, radius, style="solid",
                     sides=None, alpha=255):
    """Desenha uma borda com estilo. Cantos arredondados só quando solid completo."""
    if style == "none" or thickness <= 0:
        return
    col = with_alpha(color, alpha) if alpha < 255 else color

    if sides is None:
        sides = ["top", "bottom", "left", "right"]
    if isinstance(sides, str):
        if sides in ("all", ""):
            sides = ["top", "bottom", "left", "right"]
        elif sides == "none":
            return
        else:
            sides = [s.strip() for s in sides.split(",") if s.strip()]

    # Solid + 4 lados → nativo (com cantos arredondados bonitos)
    if style == "solid" and len(sides) >= 4:
        if alpha < 255:
            surf = pygame.Surface(rect.size, pygame.SRCALPHA)
            pygame.draw.rect(surf, col, surf.get_rect(), thickness,
                             border_radius=radius)
            screen.blit(surf, rect.topleft)
        else:
            pygame.draw.rect(screen, col, rect, thickness,
                             border_radius=radius)
        return

    # Desenho lado a lado (dashed/dotted ou lados parciais)
    if "top" in sides:
        _draw_side_styled(screen, rect.x, rect.y, rect.right, rect.y,
                          thickness, col, style)
    if "bottom" in sides:
        _draw_side_styled(screen, rect.x, rect.bottom - thickness,
                          rect.right, rect.bottom - thickness,
                          thickness, col, style)
    if "left" in sides:
        _draw_side_styled(screen, rect.x, rect.y, rect.x, rect.bottom,
                          thickness, col, style)
    if "right" in sides:
        _draw_side_styled(screen, rect.right - thickness, rect.y,
                          rect.right - thickness, rect.bottom,
                          thickness, col, style)


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
        self.fill_alpha = 255
        self.border_alpha = 255
        self.border_style = "solid"
        self.tab = None
        self.pixel_art = True

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
                 fill_alpha=255, border_alpha=255, border_style="solid",
                 bg_image=None, bg_image_mode="stretch",
                 bg_tint=None, bg_image_alpha=255,
                 border_width=2, border_radius=10, draw_border=True,
                 draw_shadow=True,
                 pixel_art=True,
                 tab=None,
                 click_sound="CLICK", hover_sound=None,
                 click_volume=None, hover_volume=None,
                 text_fit="none", min_font_size=8):
        super().__init__(wid, rect, z=z)
        self.label = label
        self.on_click = on_click
        self.style_name = style
        self.font_size = font_size or max(16, int(rect.height * 0.5))
        self.icon = icon_surface
        self.icon_size = icon_size or min(32, max(12, rect.height - 12))
        self.icon_position = icon_position
        self.icon_gap = icon_gap
        self.tooltip = tooltip
        self.font_name = font_name
        self.bold = bool(bold)
        self.text_color = text_color
        self.fill_color = fill_color
        self.border_color = border_color
        self.fill_alpha = int(fill_alpha)
        self.border_alpha = int(border_alpha)
        self.border_style = border_style
        self.tab = tab
        self.pixel_art = bool(pixel_art)
        self.click_sound = click_sound
        self.hover_sound = hover_sound
        self.click_volume = click_volume
        self.hover_volume = hover_volume

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

        self.text_fit = text_fit
        self.min_font_size = int(min_font_size)


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
            rect = rect.inflate(wo * 2, ho * 2)
            rect.center = self.rect.center

        if self.draw_shadow:
            sh = rect.move(3, 4)
            sh_s = pygame.Surface(sh.size, pygame.SRCALPHA)
            pygame.draw.rect(sh_s, (0, 0, 0, 120), sh_s.get_rect(),
                             border_radius=self.border_radius)
            screen.blit(sh_s, sh.topleft)

        if self.bg_image is not None:
            draw_image_in_rect(screen, self.bg_image, rect,
                               mode=self.bg_image_mode,
                               tint=self.bg_tint,
                               alpha=self.bg_image_alpha,
                               smooth=not self.pixel_art)
        else:
            if self._pressed:
                base = style["fill_press"]
            elif self._hover and self.enabled:
                base = style["fill_hover"]
            else:
                base = style["fill"]
            fill = self.fill_color if self.fill_color else base

            grad = pygame.Surface(rect.size, pygame.SRCALPHA)
            top = lighten(fill, 0.18)
            bot = darken(fill, 0.12)
            for y in range(rect.height):
                t = y / max(1, rect.height - 1)
                c = lerp_color(top, bot, t)
                pygame.draw.line(grad, c, (0, y), (rect.width, y))
            mask = pygame.Surface(rect.size, pygame.SRCALPHA)
            pygame.draw.rect(mask, (255, 255, 255, 255), mask.get_rect(),
                             border_radius=self.border_radius)
            grad.blit(mask, (0, 0), special_flags=pygame.BLEND_RGBA_MULT)
            if self.fill_alpha < 255:
                grad.set_alpha(self.fill_alpha)
            screen.blit(grad, rect.topleft)

        if self.draw_border and self.border_width > 0:
            border = self.border_color if self.border_color else \
                     (style["border_hover"] if (self._hover and self.enabled)
                      else style["border"])
            _draw_border_box(screen, rect, border, self.border_width,
                             self.border_radius, self.border_style,
                             sides=None, alpha=self.border_alpha)

        if self.enabled and self.draw_border and self.border_style != "none":
            hi = pygame.Rect(rect.x + 3, rect.y + 2, rect.width - 6, 2)
            hi_s = pygame.Surface(hi.size, pygame.SRCALPHA)
            hi_s.fill((255, 255, 255, 60))
            screen.blit(hi_s, hi.topleft)

        font = FontBook.get(self.font_size, bold=self.bold, name=self.font_name)
        tcol = self.text_color if self.text_color else style["text"]

        if self.icon is not None:
            self._render_with_icon(screen, rect, font, tcol)
        else:
            draw_text_centered(
                screen, self.label, font, tcol, rect,
                shadow_color=(0, 0, 0, 130),
                shadow_offset=(2, 2),
                text_fit=self.text_fit,
                font_factory=lambda s: FontBook.get(
                    s, bold=self.bold, name=self.font_name),
                start_size=self.font_size,
                min_font_size=self.min_font_size,
            )

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
        icon = _scale_sprite(self.icon, (isize, isize), self.pixel_art)

        # Helper pra reusar o mesmo "ajuste de texto" em qualquer posição
        def _draw_label(target_rect):
            draw_text_centered(
                screen, self.label, font, tcol, target_rect,
                shadow_color=(0, 0, 0, 130),
                shadow_offset=(2, 2),
                text_fit=self.text_fit,
                font_factory=lambda s: FontBook.get(
                    s, bold=self.bold, name=self.font_name),
                start_size=self.font_size,
                min_font_size=self.min_font_size,
            )

        pos = self.icon_position
        pad = 8

        # ---------- Ícone centralizado (sem texto) ----------
        if pos == "center":
            ix = rect.centerx - isize // 2
            iy = rect.centery - isize // 2
            screen.blit(icon, (ix, iy))
            return

        # ---------- Ícone em cima, texto embaixo ----------
        if pos == "top":
            total_h = isize + self.icon_gap + font.get_height()
            iy = rect.centery - total_h // 2
            ix = rect.centerx - isize // 2
            screen.blit(icon, (ix, iy))
            text_rect = pygame.Rect(rect.x, iy + isize + self.icon_gap,
                                    rect.width, font.get_height())
            _draw_label(text_rect)
            return

        # ---------- Ícone à direita, texto à esquerda ----------
        if pos == "right":
            ix = rect.right - pad - isize
            tx = rect.x + pad
            tw = rect.width - isize - self.icon_gap - pad * 2
        # ---------- Ícone à esquerda, texto à direita ----------
        else:
            ix = rect.x + pad
            tx = ix + isize + self.icon_gap
            tw = rect.right - tx - pad

        iy = rect.centery - isize // 2
        screen.blit(icon, (ix, iy))
        text_rect = pygame.Rect(tx, rect.y, tw, rect.height)
        _draw_label(text_rect)


# =====================================================================
# PAINEL
# =====================================================================
class Panel(Widget):
    def __init__(self, wid, rect, title=None, title_color=None, skin=None,
                 title_font_size=None,
                 z=0, font_name="default", bold=True,
                 text_color=None, fill_color=None, border_color=None,
                 fill_alpha=255, border_alpha=255, border_style="solid",
                 bg_image=None, bg_image_mode="stretch",
                 bg_tint=None, bg_image_alpha=255,
                 border_width=2, border_radius=10, draw_border=True,
                 draw_shadow=True,
                 padding=0, border_sides=None,
                 pixel_art=True,
                 tab=None):
        super().__init__(wid, rect, z=z)
        self.title = title
        self.title_color = title_color or Palette.TEXT_DARK
        self.title_font_size = (
            int(title_font_size) if title_font_size is not None else None)
        self.skin = skin or panel_skin
        self.font_name = font_name
        self.bold = bool(bold)
        self.text_color = text_color
        self.fill_color = fill_color
        self.border_color = border_color
        self.fill_alpha = int(fill_alpha)
        self.border_alpha = int(border_alpha)
        self.border_style = border_style
        self.bg_image = bg_image
        self.bg_image_mode = bg_image_mode
        self.bg_tint = bg_tint
        self.bg_image_alpha = bg_image_alpha
        self.border_width = int(border_width)
        self.border_radius = int(border_radius)
        self.draw_border = bool(draw_border)
        self.draw_shadow = bool(draw_shadow)
        self.padding = int(padding)
        self.border_sides = border_sides
        self.pixel_art = bool(pixel_art)
        self.tab = tab

    def render(self, screen):
        if not self.visible:
            return
        rect = self.rect

        if self.draw_shadow:
            sh = rect.move(4, 4)
            sh_s = pygame.Surface(sh.size, pygame.SRCALPHA)
            pygame.draw.rect(sh_s, (0, 0, 0, 130), sh_s.get_rect(),
                             border_radius=self.border_radius)
            screen.blit(sh_s, sh.topleft)

        if self.bg_image is not None:
            layer = pygame.Surface((rect.width, rect.height), pygame.SRCALPHA)
            draw_image_in_rect(layer, self.bg_image,
                               pygame.Rect(0, 0, rect.width, rect.height),
                               mode=self.bg_image_mode,
                               tint=self.bg_tint,
                               alpha=self.bg_image_alpha,
                               smooth=not self.pixel_art)
            mask = pygame.Surface((rect.width, rect.height), pygame.SRCALPHA)
            pygame.draw.rect(mask, (255, 255, 255, 255), mask.get_rect(),
                             border_radius=self.border_radius)
            layer.blit(mask, (0, 0), special_flags=pygame.BLEND_RGBA_MULT)
            screen.blit(layer, rect.topleft)
        else:
            fill = self.fill_color if self.fill_color else self.skin.fill
            grad = pygame.Surface(rect.size, pygame.SRCALPHA)
            for y in range(rect.height):
                t = y / max(1, rect.height - 1)
                c = lerp_color(fill, self.skin.fill_dark, t * 0.30)
                pygame.draw.line(grad, c, (0, y), (rect.width, y))
            mask = pygame.Surface(rect.size, pygame.SRCALPHA)
            pygame.draw.rect(mask, (255, 255, 255, 255), mask.get_rect(),
                             border_radius=self.border_radius)
            grad.blit(mask, (0, 0), special_flags=pygame.BLEND_RGBA_MULT)
            if self.fill_alpha < 255:
                grad.set_alpha(self.fill_alpha)
            screen.blit(grad, rect.topleft)

        if self.draw_border and self.border_width > 0 \
                and self.border_style != "none":
            bc = self.border_color if self.border_color else self.skin.border
            _draw_border_box(screen, rect, bc, self.border_width,
                             self.border_radius, self.border_style,
                             sides=self.border_sides,
                             alpha=self.border_alpha)

        if self.title:
            self._render_title(screen, rect)

    def _render_title(self, screen, rect):
        if self.title_font_size is not None:
            size = max(10, int(self.title_font_size))
        else:
            size = max(14, min(26, int(rect.height * 0.08)))

        font = FontBook.get(size, bold=self.bold, name=self.font_name)
        bar_h = font.get_height() + 8
        bar_h = min(bar_h, max(20, int(rect.height * 0.25)))
        bar = pygame.Rect(rect.x + 2, rect.y + 2, rect.width - 4, bar_h)

        bar_s = pygame.Surface(bar.size, pygame.SRCALPHA)
        pygame.draw.rect(bar_s, (72, 88, 128, 60), bar_s.get_rect(),
                         border_radius=max(2, self.border_radius - 2))
        screen.blit(bar_s, bar.topleft)

        tcol = self.text_color or self.title_color
        display = str(self.title)
        max_w = bar.width - 16
        try:
            if font.size(display)[0] > max_w:
                while display and font.size(display + "...")[0] > max_w:
                    display = display[:-1]
                display = display + "..."
        except Exception:
            pass

        draw_text_centered(screen, display, font, tcol, bar,
                           shadow_color=(255, 255, 255, 80),
                           shadow_offset=(1, 1))


# =====================================================================
# LABEL
# =====================================================================
class Label(Widget):
    def __init__(self, wid, rect, text, color=None, size=20, bold=False,
                 align="center", z=0, font_name="default",
                 text_color=None, fill_color=None, border_color=None,
                 fill_alpha=255, border_alpha=255, tab=None,
                 text_fit="none", min_font_size=8):
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
        self.fill_alpha = int(fill_alpha)
        self.border_alpha = int(border_alpha)
        self.tab = tab
        self.text_fit = text_fit
        self.min_font_size = int(min_font_size)

    def _font_factory(self):
        return lambda s: FontBook.get(s, bold=self.bold, name=self.font_name)

    def render(self, screen):
        if not self.visible:
            return
        font = FontBook.get(self.size, bold=self.bold, name=self.font_name)
        col = self.text_color or self.color

        max_w = max(4, self.rect.width - 6)
        max_h = max(4, self.rect.height)

        lines, final_font = layout_text(
            str(self.text), font, max_w, max_h,
            text_fit=self.text_fit,
            font_factory=self._font_factory(),
            start_size=self.size,
            min_size=self.min_font_size,
        )

        line_gap = 1
        line_h = final_font.get_height() + line_gap
        total_h = len(lines) * line_h - line_gap
        y0 = self.rect.centery - total_h // 2

        for i, line in enumerate(lines):
            if not line:
                continue
            surf = final_font.render(line, True, col)
            if self.align == "center":
                x = self.rect.centerx - surf.get_width() // 2
            elif self.align == "right":
                x = self.rect.right - surf.get_width()
            else:
                x = self.rect.x
            screen.blit(surf, (x, y0 + i * line_h))


# =====================================================================
# LIST VIEW (com scrollbar visual + drag)
# =====================================================================
class ListView(Widget):
    ROW_H = 34

    def __init__(self, wid, rect, items=None, on_select=None,
                 render_callback=None,
                 show_scrollbar=True,
                 scrollbar_width=8,
                 scrollbar_color=None,
                 scrollbar_bg=None,
                 scrollbar_radius=4,
                 z=0, font_name="default", bold=False,
                 text_color=None, fill_color=None, border_color=None,
                 fill_alpha=255, border_alpha=255, border_style="solid",
                 tab=None,
                 click_sound="CLICK", hover_sound=None,
                 click_volume=None, hover_volume=None):
        super().__init__(wid, rect, z=z)
        self.items = items or []
        self.on_select = on_select
        self.render_callback = render_callback
        self.scroll = 0
        self._hover_index = -1
        self.font_name = font_name
        self.bold = bool(bold)
        self.text_color = text_color
        self.fill_color = fill_color
        self.border_color = border_color
        self.fill_alpha = int(fill_alpha)
        self.border_alpha = int(border_alpha)
        self.border_style = border_style
        self.tab = tab
        self.click_sound = click_sound
        self.hover_sound = hover_sound
        self.click_volume = click_volume
        self.hover_volume = hover_volume

        # ---- Scrollbar ----
        self.show_scrollbar = bool(show_scrollbar)
        self.scrollbar_width = int(scrollbar_width)
        self.scrollbar_color = scrollbar_color or (150, 170, 210)
        self.scrollbar_bg = scrollbar_bg or (35, 42, 60)
        self.scrollbar_radius = int(scrollbar_radius)
        self._dragging_scroll = False
        self._scroll_drag_offset = 0

    # -----------------------------------------------------------------
    def _visible_rows(self):
        return max(1, (self.rect.height - 16) // self.ROW_H)

    def _max_scroll(self):
        return max(0, len(self.items) - self._visible_rows())

    def _scrollbar_rects(self):
        """Retorna (track, thumb) ou (None, None)."""
        if not self.show_scrollbar:
            return None, None
        if self._max_scroll() <= 0:
            return None, None

        w = self.scrollbar_width
        pad = 4
        track = pygame.Rect(
            self.rect.right - w - pad,
            self.rect.y + pad,
            w,
            self.rect.height - pad * 2,
        )
        total = len(self.items)
        visible = self._visible_rows()
        ratio = visible / total if total > 0 else 1
        thumb_h = max(24, int(track.height * ratio))
        max_s = self._max_scroll()
        thumb_y = track.y + int((track.height - thumb_h) *
                                (self.scroll / max_s)) if max_s > 0 else track.y
        thumb = pygame.Rect(track.x, thumb_y, w, thumb_h)
        return track, thumb

    # -----------------------------------------------------------------
    def handle_event(self, event):
        if not self.visible or not self.enabled:
            return False

        # ---- Scrollbar drag ----
        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            track, thumb = self._scrollbar_rects()
            if track and thumb and track.collidepoint(event.pos):
                if thumb.collidepoint(event.pos):
                    self._scroll_drag_offset = event.pos[1] - thumb.y
                else:
                    # Clicou no track → salta e começa a arrastar
                    self._scroll_drag_offset = thumb.height // 2
                    self._update_scroll_from_mouse(event.pos[1])
                self._dragging_scroll = True
                return True

        if event.type == pygame.MOUSEMOTION and self._dragging_scroll:
            self._update_scroll_from_mouse(event.pos[1])
            return True

        if event.type == pygame.MOUSEBUTTONUP and event.button == 1:
            if self._dragging_scroll:
                self._dragging_scroll = False
                return True

        # ---- Mouse wheel ----
        if event.type == pygame.MOUSEWHEEL:
            mx, my = pygame.mouse.get_pos()
            if self.rect.collidepoint(mx, my):
                self.scroll -= event.y
                self.scroll = max(0, min(self._max_scroll(), self.scroll))
                return True

        # ---- Hover ----
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

        # ---- Click ----
        elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            track, _ = self._scrollbar_rects()
            if track and track.collidepoint(event.pos):
                return True
            if 0 <= self._hover_index < len(self.items) and self.on_select:
                self._play_click()
                self.on_select(self._hover_index)
                return True
        return False

    def _update_scroll_from_mouse(self, mouse_y):
        track, thumb = self._scrollbar_rects()
        if not track or not thumb:
            return
        max_s = self._max_scroll()
        thumb_range = track.height - thumb.height
        if thumb_range <= 0 or max_s <= 0:
            return
        rel_y = mouse_y - self._scroll_drag_offset - track.y
        rel_y = max(0, min(thumb_range, rel_y))
        self.scroll = int(max_s * (rel_y / thumb_range))

    # -----------------------------------------------------------------
    def render(self, screen):
        if not self.visible:
            return

        if self.fill_alpha < 255:
            surf = pygame.Surface(self.rect.size, pygame.SRCALPHA)
            pygame.draw.rect(surf, with_alpha(
                self.fill_color or Palette.PANEL_FILL, self.fill_alpha),
                surf.get_rect(), border_radius=8)
            screen.blit(surf, self.rect.topleft)
        else:
            panel_skin.render(screen, self.rect,
                              border_color=self.border_color,
                              fill_override=self.fill_color)

        # Borda com estilo
        if self.border_style != "solid":
            _draw_border_box(screen, self.rect,
                             self.border_color or Palette.BORDER_DARK,
                             1, 8, self.border_style)

        clip = self.rect.inflate(-12, -12)
        # Se scrollbar visível, ajusta clip à esquerda
        if self.show_scrollbar and self._max_scroll() > 0:
            clip.width -= self.scrollbar_width + 6

        old = screen.get_clip()
        screen.set_clip(clip)
        y = clip.y
        vis = self._visible_rows()
        for i in range(self.scroll, min(len(self.items), self.scroll + vis)):
            row = pygame.Rect(clip.x, y, clip.width, self.ROW_H - 2)
            item = self.items[i]

            if i == self._hover_index:
                hl = pygame.Surface(row.size, pygame.SRCALPHA)
                pygame.draw.rect(hl, (72, 88, 128, 80), hl.get_rect(),
                                 border_radius=6)
                screen.blit(hl, row.topleft)
                pygame.draw.rect(screen, Palette.GOLD, row, 1, border_radius=6)

            if self.render_callback is not None:
                try:
                    handled = self.render_callback(i, item, screen, row)
                except Exception as e:
                    handled = False
                    print(f"[ListView] render_callback erro idx={i}: {e}")
                if handled:
                    y += self.ROW_H
                    continue

            font = FontBook.get(20, bold=self.bold, name=self.font_name)
            col = self.text_color or Palette.TEXT_DARK
            txt = font.render(str(item), True, col)
            screen.blit(txt, (row.x + 12, row.centery - txt.get_height() // 2))
            y += self.ROW_H
        screen.set_clip(old)

        # ---- Scrollbar ----
        track, thumb = self._scrollbar_rects()
        if track and thumb:
            pygame.draw.rect(screen, self.scrollbar_bg, track,
                             border_radius=self.scrollbar_radius)
            col = self.scrollbar_color
            if self._dragging_scroll:
                col = lighten(col, 0.25)
            pygame.draw.rect(screen, col, thumb,
                             border_radius=self.scrollbar_radius)


# =====================================================================
# GRID SELECT
# =====================================================================
class GridSelect(Widget):
    def __init__(self, wid, rect, items=None, cols=2, rows=2,
                 cell_gap=8,
                 on_select=None, render_callback=None,
                 z=0, font_name="default", bold=False,
                 text_color=None, fill_color=None, border_color=None,
                 fill_alpha=255, border_alpha=255, tab=None,
                 click_sound="CLICK", hover_sound=None,
                 click_volume=None, hover_volume=None):
        super().__init__(wid, rect, z=z)
        self.items = items or []
        self.cols = max(1, int(cols))
        self.rows = max(1, int(rows))
        self.cell_gap = int(cell_gap)
        self.on_select = on_select
        self.render_callback = render_callback
        self._hover_index = -1
        self.font_name = font_name
        self.bold = bool(bold)
        self.text_color = text_color
        self.fill_color = fill_color
        self.border_color = border_color
        self.fill_alpha = int(fill_alpha)
        self.border_alpha = int(border_alpha)
        self.tab = tab
        self.click_sound = click_sound
        self.hover_sound = hover_sound
        self.click_volume = click_volume
        self.hover_volume = hover_volume

    def _cell_rects(self):
        cw = (self.rect.width - self.cell_gap * (self.cols - 1)) // self.cols
        ch = (self.rect.height - self.cell_gap * (self.rows - 1)) // self.rows
        out = []
        for r in range(self.rows):
            for c in range(self.cols):
                x = self.rect.x + c * (cw + self.cell_gap)
                y = self.rect.y + r * (ch + self.cell_gap)
                out.append(pygame.Rect(x, y, cw, ch))
        return out

    def handle_event(self, event):
        if not self.visible or not self.enabled:
            return False
        if event.type == pygame.MOUSEMOTION:
            old = self._hover_index
            self._hover_index = -1
            for i, r in enumerate(self._cell_rects()):
                if i >= len(self.items):
                    break
                if r.collidepoint(event.pos):
                    self._hover_index = i
                    break
            if self._hover_index != old and self._hover_index >= 0:
                self._play_hover()
        elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            if 0 <= self._hover_index < len(self.items):
                if self.on_select:
                    self._play_click()
                    self.on_select(self._hover_index)
                    return True
        return False

    def render(self, screen):
        if not self.visible:
            return

        if self.fill_alpha < 255 and self.fill_color:
            surf = pygame.Surface(self.rect.size, pygame.SRCALPHA)
            pygame.draw.rect(surf, with_alpha(self.fill_color, self.fill_alpha),
                             surf.get_rect(), border_radius=8)
            screen.blit(surf, self.rect.topleft)
        elif self.fill_color or self.border_color:
            panel_skin.render(screen, self.rect,
                              border_color=self.border_color,
                              fill_override=self.fill_color)

        for i, cell in enumerate(self._cell_rects()):
            if i >= len(self.items):
                break
            if i == self._hover_index:
                hl = pygame.Surface(cell.size, pygame.SRCALPHA)
                pygame.draw.rect(hl, (72, 88, 128, 60), hl.get_rect(),
                                 border_radius=6)
                screen.blit(hl, cell.topleft)

            if self.render_callback is not None:
                try:
                    handled = self.render_callback(i, self.items[i],
                                                   screen, cell)
                except Exception as e:
                    handled = False
                    print(f"[GridSelect] render_callback erro idx={i}: {e}")
                if handled:
                    continue

            font = FontBook.get(20, bold=self.bold, name=self.font_name)
            col = self.text_color or Palette.TEXT_DARK
            txt = font.render(str(self.items[i]), True, col)
            screen.blit(txt, txt.get_rect(center=cell.center))


# =====================================================================
# IMAGE BOX
# =====================================================================
class ImageBox(Widget):
    def __init__(self, wid, rect, surface=None, skin=None, z=0,
                 font_name="default", text_color=None,
                 fill_color=None, border_color=None,
                 fill_alpha=255, border_alpha=255, tab=None,
                 bg_image_mode="contain",
                 pixel_art=True):
        super().__init__(wid, rect, z=z)
        self.surface = surface
        self.skin = skin
        self.font_name = font_name
        self.text_color = text_color
        self.fill_color = fill_color
        self.border_color = border_color
        self.fill_alpha = int(fill_alpha)
        self.border_alpha = int(border_alpha)
        self.tab = tab
        self.bg_image_mode = bg_image_mode
        self.pixel_art = bool(pixel_art)

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
                           mode=self.bg_image_mode,
                           smooth=not self.pixel_art)


# =====================================================================
# WORLD SPRITE
# =====================================================================
class WorldSprite(Widget):
    def __init__(self, wid, rect, surface=None,
                 world_x=0.0, world_y=0.0,
                 max_size=130, z=0, tab=None,
                 screen_manager=None, game=None,
                 pixel_art=True):
        super().__init__(wid, rect, z=z)
        self.surface = surface
        self.world_x = float(world_x)
        self.world_y = float(world_y)
        self.max_size = int(max_size)
        self.tab = tab
        self.screen_manager = screen_manager
        self.game = game
        self.pixel_art = bool(pixel_art)

    def render(self, screen):
        if not self.visible or self.surface is None:
            return
        if self.screen_manager is not None:
            camera = getattr(self.game, "camera", None) if self.game else None
            try:
                sx, sy = self.screen_manager.world_to_screen(
                    self.world_x, self.world_y, camera)
            except Exception:
                sx, sy = self.rect.center
        else:
            sx, sy = self.rect.center

        orig_w, orig_h = self.surface.get_size()
        if orig_w <= 0 or orig_h <= 0:
            return
        scale = min(self.max_size / orig_w, self.max_size / orig_h)
        nw = max(1, int(orig_w * scale))
        nh = max(1, int(orig_h * scale))
        scaled = _scale_sprite(self.surface, (nw, nh), self.pixel_art)
        screen.blit(scaled, (int(sx - nw // 2), int(sy - nh // 2)))


# =====================================================================
# CHECKBOX
# =====================================================================
class Checkbox(Widget):
    def __init__(self, wid, rect, label="", checked=False, on_toggle=None,
                 z=0, font_name="default", bold=True,
                 text_color=None, fill_color=None, border_color=None,
                 fill_alpha=255, border_alpha=255, tab=None,
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
        self.fill_alpha = int(fill_alpha)
        self.border_alpha = int(border_alpha)
        self.tab = tab
        self.click_sound = click_sound
        self.hover_sound = hover_sound
        self.click_volume = click_volume
        self.hover_volume = hover_volume

    def _box_rect(self):
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
                 fill_color=None, border_color=None,
                 fill_alpha=255, border_alpha=255, tab=None,
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
        self.fill_alpha = int(fill_alpha)
        self.border_alpha = int(border_alpha)
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
        track_h = min(self.rect.height, 16)
        track = pygame.Rect(self.rect.x,
                            self.rect.centery - track_h // 2,
                            self.rect.width, track_h)

        bg = self.fill_color or (48, 54, 76)
        border = self.border_color or Palette.BORDER_DARK

        if self.fill_alpha < 255:
            surf = pygame.Surface(track.size, pygame.SRCALPHA)
            pygame.draw.rect(surf, with_alpha(bg, self.fill_alpha),
                             surf.get_rect(), border_radius=6)
            screen.blit(surf, track.topleft)
        else:
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
# DROPDOWN
# =====================================================================
class Dropdown(Widget):
    ITEM_H = 28

    def __init__(self, wid, rect, options=None, value=None,
                 on_change=None, z=0, font_name="default", bold=False,
                 text_color=None, fill_color=None, border_color=None,
                 fill_alpha=255, border_alpha=255, border_style="solid",
                 drop_dir="down",
                 tab=None,
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
        self.fill_alpha = int(fill_alpha)
        self.border_alpha = int(border_alpha)
        self.border_style = border_style
        self.drop_dir = drop_dir if drop_dir in ("down", "up") else "down"
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

        if self.drop_dir == "up":
            y = self.rect.y - h - 2
            if y < 4:
                y = self.rect.bottom + 2  # fallback pra baixo se não caber
        else:
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

        # Fundo
        if self.fill_alpha < 255:
            surf = pygame.Surface(self.rect.size, pygame.SRCALPHA)
            pygame.draw.rect(surf, with_alpha(bg, self.fill_alpha),
                             surf.get_rect(), border_radius=6)
            screen.blit(surf, self.rect.topleft)
        else:
            pygame.draw.rect(screen, bg, self.rect, border_radius=6)

        # Borda
        _draw_border_box(screen, self.rect, border, 2, 6,
                         self.border_style)

        font = FontBook.get(max(14, int(self.rect.height * 0.55)),
                            bold=self.bold, name=self.font_name)
        col = self.text_color or Palette.TEXT_LIGHT
        s = font.render(str(self.value), True, col)
        screen.blit(s, (self.rect.x + 8,
                        self.rect.centery - s.get_height() // 2))

        # Seta (muda conforme drop_dir)
        arrow_char = "^" if self.drop_dir == "up" else "v"
        arrow = font.render(arrow_char, True, (180, 190, 210))
        screen.blit(arrow, (self.rect.right - 16,
                            self.rect.centery - arrow.get_height() // 2))

        if not self.open:
            return
        lr = self._compute_list_rect()
        self._list_rect = lr

        bg2 = darken(bg, 0.05)
        if self.fill_alpha < 255:
            surf = pygame.Surface(lr.size, pygame.SRCALPHA)
            pygame.draw.rect(surf, with_alpha(bg2, max(200, self.fill_alpha)),
                             surf.get_rect(), border_radius=6)
            screen.blit(surf, lr.topleft)
        else:
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
# PROGRESS BAR
# =====================================================================
class ProgressBar(Widget):
    def __init__(self, wid, rect, value=0.5, max_value=1.0,
                 min_value=0.0,
                 bg_color=None,
                 color_low=None, color_mid=None, color_high=None,
                 border_color=None,
                 show_text=True, text_format="{value}/{max}",
                 z=0, font_name="default",
                 text_color=None, tab=None,
                 radius=None):
        super().__init__(wid, rect, z=z)
        self.value = float(value)
        self.max_value = float(max_value)
        self.min_value = float(min_value)
        self.bg_color = bg_color or (40, 45, 60)
        self.color_low = color_low or (230, 90, 90)
        self.color_mid = color_mid or (248, 176, 48)
        self.color_high = color_high or (105, 220, 130)
        self.border_color = border_color or (100, 100, 120)
        self.show_text = bool(show_text)
        self.text_format = text_format
        self.font_name = font_name
        self.text_color = text_color or (255, 255, 255)
        self.tab = tab
        self.radius = radius if radius is not None else max(2, rect.height // 2 - 2)

    def _ratio(self):
        rng = max(1e-6, self.max_value - self.min_value)
        return max(0.0, min(1.0, (self.value - self.min_value) / rng))

    def _fill_color(self):
        r = self._ratio()
        if r > 0.6:
            return self.color_high
        elif r > 0.3:
            return self.color_mid
        return self.color_low

    def handle_event(self, event):
        return False

    def render(self, screen):
        if not self.visible:
            return
        r = self._ratio()
        rect = self.rect
        rad = self.radius

        pygame.draw.rect(screen, self.bg_color, rect, border_radius=rad)

        if r > 0:
            fill_w = max(4, int(rect.width * r))
            fill_rect = pygame.Rect(rect.x, rect.y, fill_w, rect.height)
            col = self._fill_color()
            pygame.draw.rect(screen, col, fill_rect, border_radius=rad)

        pygame.draw.rect(screen, self.border_color, rect, 1, border_radius=rad)

        if self.show_text:
            try:
                text = self.text_format.format(
                    value=int(self.value),
                    max=int(self.max_value),
                    percent=int(r * 100))
            except Exception:
                text = f"{self.value}/{self.max_value}"
            font = FontBook.get(max(12, int(rect.height * 0.75)),
                                bold=True, name=self.font_name)
            surf = font.render(text, True, self.text_color)
            x = rect.centerx - surf.get_width() // 2
            y = rect.centery - surf.get_height() // 2
            sh = font.render(text, True, (0, 0, 0, 180))
            screen.blit(sh, (x + 1, y + 1))
            screen.blit(surf, (x, y))


# =====================================================================
# BADGE
# =====================================================================
class Badge(Widget):
    def __init__(self, wid, rect, text="",
                 bg_color=None, text_color=None,
                 border_color=None,
                 z=0, font_name="default", bold=True,
                 font_size=None, tab=None):
        super().__init__(wid, rect, z=z)
        self.text = text
        self.bg_color = bg_color or Palette.BLUE
        self.text_color = text_color or (255, 255, 255)
        self.border_color = border_color
        self.font_name = font_name
        self.bold = bool(bold)
        self.font_size = font_size or max(12, int(rect.height * 0.55))
        self.tab = tab

    def render(self, screen):
        if not self.visible:
            return
        pygame.draw.rect(screen, self.bg_color, self.rect,
                         border_radius=self.rect.height // 2)
        if self.border_color:
            pygame.draw.rect(screen, self.border_color, self.rect, 1,
                             border_radius=self.rect.height // 2)
        else:
            surf = pygame.Surface(self.rect.size, pygame.SRCALPHA)
            pygame.draw.rect(surf, (255, 255, 255, 100), surf.get_rect(), 1,
                             border_radius=self.rect.height // 2)
            screen.blit(surf, self.rect.topleft)

        if self.text:
            font = FontBook.get(self.font_size, bold=self.bold,
                                name=self.font_name)
            surf = font.render(str(self.text), True, self.text_color)
            x = self.rect.centerx - surf.get_width() // 2
            y = self.rect.centery - surf.get_height() // 2
            screen.blit(surf, (x, y))

    @property
    def text_value(self): return self.text
    @text_value.setter
    def text_value(self, v): self.text = str(v)


# =====================================================================
# DIVIDER — linha divisória horizontal/vertical com estilo
# =====================================================================
class Divider(Widget):
    """
    Linha reta horizontal ou vertical.
    Pode ser solid, dashed, dotted ou none.
    """
    def __init__(self, wid, rect, orientation="horizontal",
                 color=None, thickness=2, style="solid",
                 padding=0, radius=0,
                 z=0, tab=None):
        super().__init__(wid, rect, z=z)
        self.orientation = orientation if orientation in ("horizontal", "vertical") else "horizontal"
        self.color = color or Palette.BORDER_DARK
        self.thickness = int(thickness)
        self.style = style
        self.padding = int(padding)
        self.radius = int(radius)
        self.tab = tab

    def render(self, screen):
        if not self.visible or self.thickness <= 0 or self.style == "none":
            return
        rect = self.rect

        if self.orientation == "vertical":
            x = rect.centerx - self.thickness // 2
            y1 = rect.y + self.padding
            y2 = rect.bottom - self.padding
            if self.style == "solid" and self.radius > 0:
                r = pygame.Rect(x, y1, self.thickness, max(1, y2 - y1))
                pygame.draw.rect(screen, self.color, r,
                                 border_radius=self.radius)
            else:
                _draw_side_styled(screen, x, y1, x, y2,
                                  self.thickness, self.color, self.style)
        else:
            y = rect.centery - self.thickness // 2
            x1 = rect.x + self.padding
            x2 = rect.right - self.padding
            if self.style == "solid" and self.radius > 0:
                r = pygame.Rect(x1, y, max(1, x2 - x1), self.thickness)
                pygame.draw.rect(screen, self.color, r,
                                 border_radius=self.radius)
            else:
                _draw_side_styled(screen, x1, y, x2, y,
                                  self.thickness, self.color, self.style)


# =====================================================================
# TABLE
# =====================================================================
class Table(Widget):
    """
    Tabela com headers + rows.
    - headers: list[str]
    - rows: list[list[str]]
    - col_widths: list[float] (relativo) ou None (igual)
    """
    def __init__(self, wid, rect,
                 headers=None, rows=None, col_widths=None,
                 row_height=30, header_height=34,
                 font_size=14, header_font_size=15,
                 cell_padding=6,
                 header_bg=None, header_text_color=None,
                 row_bg=None, row_bg_alt=None,
                 text_color=None, grid_color=None, grid_width=1,
                 z=0, font_name="default", bold=False, tab=None):
        super().__init__(wid, rect, z=z)
        self.headers = list(headers or [])
        self.rows = list(rows or [])
        self.col_widths = col_widths
        self.row_height = int(row_height)
        self.header_height = int(header_height)
        self.font_size = int(font_size)
        self.header_font_size = int(header_font_size)
        self.cell_padding = int(cell_padding)
        self.header_bg = header_bg or (60, 48, 24)
        self.header_text_color = header_text_color or (245, 230, 180)
        self.row_bg = row_bg or (240, 226, 184)
        self.row_bg_alt = row_bg_alt or (224, 208, 162)
        self.text_color = text_color or (58, 34, 16)
        self.grid_color = grid_color or (138, 106, 42)
        self.grid_width = int(grid_width)
        self.font_name = font_name
        self.bold = bool(bold)
        self.tab = tab

    def _n_cols(self):
        if self.headers:
            return len(self.headers)
        if self.rows:
            return len(self.rows[0])
        return 0

    def _col_xs(self):
        n = self._n_cols()
        if n <= 0:
            return []
        widths = self.col_widths
        if not widths or len(widths) != n:
            cw = self.rect.width / n
            return [self.rect.x + int(i * cw) for i in range(n + 1)]

        total = sum(widths) or 1
        xs = [self.rect.x]
        acc = 0.0
        for w in widths:
            acc += (w / total) * self.rect.width
            xs.append(self.rect.x + int(acc))
        xs[-1] = self.rect.right
        return xs

    def handle_event(self, event):
        return False

    def render(self, screen):
        if not self.visible:
            return
        n = self._n_cols()
        if n <= 0:
            return

        xs = self._col_xs()

        # ----- Cabeçalho -----
        head_rect = pygame.Rect(self.rect.x, self.rect.y,
                                self.rect.width, self.header_height)
        pygame.draw.rect(screen, self.header_bg, head_rect)

        hf = FontBook.get(self.header_font_size, bold=True,
                          name=self.font_name)
        for i, title in enumerate(self.headers):
            if i >= len(xs) - 1:
                break
            cell = pygame.Rect(xs[i], self.rect.y,
                               xs[i + 1] - xs[i], self.header_height)
            txt = hf.render(str(title), True, self.header_text_color)
            clip = cell.inflate(-self.cell_padding * 2, 0)
            old = screen.get_clip()
            screen.set_clip(clip)
            screen.blit(txt, (cell.x + self.cell_padding,
                              cell.centery - txt.get_height() // 2))
            screen.set_clip(old)

        # ----- Linhas -----
        y = self.rect.y + self.header_height
        rf = FontBook.get(self.font_size, bold=self.bold,
                          name=self.font_name)

        for r, row in enumerate(self.rows):
            row_rect = pygame.Rect(self.rect.x, y, self.rect.width,
                                   self.row_height)
            bg = self.row_bg if (r % 2 == 0) else self.row_bg_alt
            pygame.draw.rect(screen, bg, row_rect)

            for i in range(n):
                if i >= len(xs) - 1:
                    break
                value = row[i] if i < len(row) else ""
                cell = pygame.Rect(xs[i], y,
                                   xs[i + 1] - xs[i], self.row_height)
                txt = rf.render(str(value), True, self.text_color)
                clip = cell.inflate(-self.cell_padding * 2, 0)
                old = screen.get_clip()
                screen.set_clip(clip)
                screen.blit(txt, (cell.x + self.cell_padding,
                                  cell.centery - txt.get_height() // 2))
                screen.set_clip(old)
            y += self.row_height

        # ----- Grid (linhas verticais + horizontais + borda) -----
        if self.grid_width > 0:
            # Verticais
            for i in range(1, n):
                if i < len(xs):
                    pygame.draw.line(screen, self.grid_color,
                                     (xs[i], self.rect.y),
                                     (xs[i], min(y, self.rect.bottom)),
                                     self.grid_width)
            # Horizontais
            hy = self.rect.y + self.header_height
            pygame.draw.line(screen, self.grid_color,
                             (self.rect.x, hy), (self.rect.right, hy),
                             self.grid_width)
            for r in range(1, len(self.rows)):
                ly = self.rect.y + self.header_height + r * self.row_height
                if ly < self.rect.bottom:
                    pygame.draw.line(screen, self.grid_color,
                                     (self.rect.x, ly),
                                     (self.rect.right, ly),
                                     self.grid_width)

            # Borda externa
            _draw_border_box(screen, self.rect, self.grid_color,
                             self.grid_width, 6, "solid")


# =====================================================================
# TAB PANEL
# =====================================================================
class TabPanel(Widget):
    def __init__(self, wid, rect, tabs=None, current_tab=None,
                 on_change=None, z=0, font_name="default", bold=True,
                 font_size=None,                      # ← NOVO
                 tab_font_size=None,                  # ← alias
                 tab_height=None,                     # ← NOVO
                 text_color=None, fill_color=None, border_color=None,
                 fill_alpha=255, border_alpha=255, tab=None,
                 click_sound="CLICK", hover_sound=None,
                 click_volume=None, hover_volume=None):
        super().__init__(wid, rect, z=z)
        self.tabs = list(tabs or ["Tab 1"])
        self.current_tab = current_tab or (self.tabs[0] if self.tabs else None)
        self.on_change = on_change
        self.font_name = font_name
        self.bold = bool(bold)

        fs = tab_font_size if tab_font_size is not None else font_size
        if fs is None or fs == "":
            self.font_size = None
        else:
            try:
                self.font_size = int(float(fs))
            except (TypeError, ValueError):
                self.font_size = None

        self.tab_height = None
        if tab_height is not None and tab_height != "":
            try:
                self.tab_height = int(float(tab_height))
            except (TypeError, ValueError):
                self.tab_height = None

        self.text_color = text_color
        self.fill_color = fill_color
        self.border_color = border_color
        self.fill_alpha = int(fill_alpha)
        self.border_alpha = int(border_alpha)
        self.tab = tab
        self.click_sound = click_sound
        self.hover_sound = hover_sound
        self.click_volume = click_volume
        self.hover_volume = hover_volume
        self._hover_idx = -1

    def _effective_font_size(self):
        if self.font_size is not None:
            return max(6, int(self.font_size))
        return max(10, int(self.rect.height * 0.07))

    def _tab_h(self):
        if self.tab_height is not None:
            return max(16, int(self.tab_height))
        fs = self._effective_font_size()
        return max(max(20, fs + 8), int(self.rect.height * 0.12))

    def _tab_rects(self):
        n = max(1, len(self.tabs))
        w = self.rect.width // n
        h = self._tab_h()
        return [(name, pygame.Rect(self.rect.x + i * w, self.rect.y, w, h))
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

        if self.fill_alpha < 255:
            surf = pygame.Surface(content.size, pygame.SRCALPHA)
            pygame.draw.rect(surf, with_alpha(
                self.fill_color or Palette.PANEL_FILL, self.fill_alpha),
                surf.get_rect(), border_radius=8)
            screen.blit(surf, content.topleft)
        else:
            panel_skin.render(screen, content,
                              border_color=self.border_color,
                              fill_override=self.fill_color)

        if not self.tabs:
            return

        # ← usa font_size explícito se setado
        font = FontBook.get(self._effective_font_size(),
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

# =====================================================================
# HELPERS DE FORMA — usados por SlotRow
# =====================================================================
def _poly_regular(cx, cy, r, n, start=-math.pi / 2):
    return [
        (cx + math.cos(start + i * 2 * math.pi / n) * r,
         cy + math.sin(start + i * 2 * math.pi / n) * r)
        for i in range(n)
    ]


def _poly_star(cx, cy, r, spikes=5, inner=0.45):
    pts = []
    for i in range(spikes * 2):
        ang = -math.pi / 2 + i * math.pi / spikes
        rad = r if (i % 2 == 0) else r * inner
        pts.append((cx + math.cos(ang) * rad, cy + math.sin(ang) * rad))
    return pts


def _poly_heart(cx, cy, r, samples=48):
    pts = []
    for i in range(samples):
        t = i / samples * 2 * math.pi
        x = 16 * math.sin(t) ** 3
        y = (13 * math.cos(t) - 5 * math.cos(2 * t)
             - 2 * math.cos(3 * t) - math.cos(4 * t))
        pts.append((cx + (x / 16) * r, cy - (y / 16) * r))
    return pts


def _poly_shield(cx, cy, r):
    return [
        (cx - r, cy - r * 0.95),
        (cx + r, cy - r * 0.95),
        (cx + r, cy + r * 0.10),
        (cx,     cy + r),
        (cx - r, cy + r * 0.10),
    ]


def _tint_surface(surf, color):
    if not color or surf is None:
        return surf
    out = surf.copy()
    overlay = pygame.Surface(out.get_size(), pygame.SRCALPHA)
    overlay.fill((int(color[0]), int(color[1]), int(color[2]), 255))
    out.blit(overlay, (0, 0), special_flags=pygame.BLEND_RGBA_MULT)
    return out


# =====================================================================
# SLOT ROW — fileira de N slots iguais (aceso/apagado)
# =====================================================================
class SlotRow(Widget):
    """
    Fileira (ou coluna) de N slots iguais. Cada slot é "aceso" ou "apagado".

    Ideal para: estrelas de fase, medalhas, insígnias de ginásio,
    vidas, slots de inventário, checks de progresso, etc.

    shape: desenha a forma proceduralmente
      ("star" | "circle" | "square" | "diamond" | "triangle" |
       "pentagon" | "hexagon" | "heart" | "shield" | "trophy" |
       "medal" | "none")

    icon: se fornecido, desenha a imagem no lugar do shape
          (com tint opcional via `icon_tint`)
    """
    SHAPES = (
        "star", "circle", "square", "diamond", "triangle",
        "pentagon", "hexagon", "heart", "shield", "trophy",
        "medal", "none",
    )
    ORIENTATIONS = ("horizontal", "vertical")

    def __init__(self, wid, rect,
                 value=0, max_slots=3,
                 shape="star",
                 orientation="horizontal",
                 slot_size=None,
                 gap=8,
                 color_filled=None,
                 color_empty=None,
                 outline_color=None,
                 outline_width=2,
                 filled_alpha=255,
                 empty_alpha=110,
                 icon=None,
                 icon_tint=True,
                 pixel_art=True,
                 z=0, tab=None):
        super().__init__(wid, rect, z=z)

        self.max_slots = max(1, int(max_slots))
        self.value = max(0, min(self.max_slots, int(value)))

        self.shape = shape if shape in self.SHAPES else "star"
        self.orientation = (orientation
                            if orientation in self.ORIENTATIONS
                            else "horizontal")

        self.slot_size = int(slot_size) if slot_size else None
        self.gap = max(0, int(gap))

        self.color_filled = color_filled or Palette.GOLD
        self.color_empty = color_empty or (55, 60, 76)
        self.outline_color = outline_color or (30, 30, 40)
        self.outline_width = max(0, int(outline_width))

        self.filled_alpha = max(0, min(255, int(filled_alpha)))
        self.empty_alpha = max(0, min(255, int(empty_alpha)))

        self.icon = icon
        self.icon_tint = bool(icon_tint)
        self.pixel_art = bool(pixel_art)
        self.tab = tab

    # -----------------------------------------------------------------
    def set_value(self, v):
        self.value = max(0, min(self.max_slots, int(v)))

    def set_max(self, n):
        self.max_slots = max(1, int(n))
        self.value = max(0, min(self.max_slots, self.value))

    # -----------------------------------------------------------------
    def _compute_slot_size(self):
        if self.slot_size:
            return max(6, int(self.slot_size))
        n = self.max_slots
        if self.orientation == "vertical":
            avail = self.rect.height - self.gap * (n - 1)
        else:
            avail = self.rect.width - self.gap * (n - 1)
        return max(6, avail // max(1, n))

    def _slot_centers(self):
        n = self.max_slots
        s = self._compute_slot_size()
        if self.orientation == "vertical":
            total = n * s + (n - 1) * self.gap
            x = self.rect.centerx
            y0 = self.rect.centery - total // 2 + s // 2
            return [(x, y0 + i * (s + self.gap), s) for i in range(n)]
        total = n * s + (n - 1) * self.gap
        y = self.rect.centery
        x0 = self.rect.centerx - total // 2 + s // 2
        return [(x0 + i * (s + self.gap), y, s) for i in range(n)]

    # -----------------------------------------------------------------
    def render(self, screen):
        if not self.visible:
            return
        for i, (cx, cy, size) in enumerate(self._slot_centers()):
            self._draw_slot(screen, cx, cy, size, filled=(i < self.value))

    def _draw_slot(self, screen, cx, cy, size, filled):
        color = self.color_filled if filled else self.color_empty
        alpha = self.filled_alpha if filled else self.empty_alpha

        # ---- Ícone custom (imagem) ----
        if self.icon is not None:
            iw, ih = self.icon.get_size()
            if iw > 0 and ih > 0:
                scale = min(size / iw, size / ih)
                nw = max(1, int(iw * scale))
                nh = max(1, int(ih * scale))
                scaled = _scale_sprite(self.icon, (nw, nh), self.pixel_art)
                if self.icon_tint:
                    scaled = _tint_surface(scaled, color)
                if alpha < 255:
                    scaled = scaled.copy()
                    scaled.set_alpha(alpha)
                screen.blit(scaled, (cx - nw // 2, cy - nh // 2))
            return

        if self.shape == "none":
            return

        r = size // 2
        fill_rgba = with_alpha(color, alpha)
        outline_rgba = with_alpha(self.outline_color, alpha)

        pts = self._shape_points(self.shape, cx, cy, r)
        if isinstance(pts, list) and len(pts) >= 3:
            pygame.draw.polygon(screen, fill_rgba, pts)
            if self.outline_width > 0:
                pygame.draw.polygon(screen, outline_rgba, pts,
                                    self.outline_width)
        elif self.shape == "medal":
            self._draw_medal(screen, cx, cy, r, fill_rgba, outline_rgba, alpha)
        elif self.shape == "trophy":
            self._draw_trophy(screen, cx, cy, r, fill_rgba, outline_rgba)

    @staticmethod
    def _shape_points(shape, cx, cy, r):
        if shape == "circle":
            return [
                (cx + math.cos(i * math.pi / 24) * r,
                 cy + math.sin(i * math.pi / 24) * r)
                for i in range(48)
            ]
        if shape == "square":
            k = r * 0.82
            return [(cx - k, cy - k), (cx + k, cy - k),
                    (cx + k, cy + k), (cx - k, cy + k)]
        if shape == "diamond":
            return [(cx, cy - r), (cx + r, cy),
                    (cx, cy + r), (cx - r, cy)]
        if shape == "triangle":
            return _poly_regular(cx, cy, r, 3)
        if shape == "pentagon":
            return _poly_regular(cx, cy, r, 5)
        if shape == "hexagon":
            return _poly_regular(cx, cy, r, 6)
        if shape == "star":
            return _poly_star(cx, cy, r, spikes=5, inner=0.45)
        if shape == "heart":
            return _poly_heart(cx, cy, r)
        if shape == "shield":
            return _poly_shield(cx, cy, r)
        return None

    @staticmethod
    def _draw_medal(screen, cx, cy, r, fill, outline, alpha):
        pygame.draw.circle(screen, fill, (cx, cy + int(r * 0.15)),
                           int(r * 0.85))
        pygame.draw.circle(screen, outline, (cx, cy + int(r * 0.15)),
                           int(r * 0.85), 2)
        top = cy - int(r * 0.85)
        ribbon = [
            (cx - r * 0.55, top),
            (cx - r * 0.10, top),
            (cx, cy + int(r * 0.05)),
        ]
        ribbon2 = [
            (cx + r * 0.55, top),
            (cx + r * 0.10, top),
            (cx, cy + int(r * 0.05)),
        ]
        pygame.draw.polygon(screen, with_alpha((200, 60, 60), alpha), ribbon)
        pygame.draw.polygon(screen, with_alpha((60, 90, 200), alpha), ribbon2)

    @staticmethod
    def _draw_trophy(screen, cx, cy, r, fill, outline):
        body_top = cy - r * 0.55
        body_bot = cy + r * 0.35
        top_w = r * 0.85
        bot_w = r * 0.5
        body_pts = [
            (cx - top_w, body_top),
            (cx + top_w, body_top),
            (cx + bot_w, body_bot),
            (cx - bot_w, body_bot),
        ]
        pygame.draw.polygon(screen, fill, body_pts)
        pygame.draw.polygon(screen, outline, body_pts, 2)
        try:
            pygame.draw.arc(screen, outline,
                            (cx - top_w - r * 0.4, body_top - r * 0.05,
                             r * 0.55, r * 0.75),
                            math.pi / 2, math.pi * 1.5, 2)
            pygame.draw.arc(screen, outline,
                            (cx + top_w - r * 0.15, body_top - r * 0.05,
                             r * 0.55, r * 0.75),
                            -math.pi / 2, math.pi / 2, 2)
        except Exception:
            pass
        base_w = r * 0.75
        base_h = max(2, int(r * 0.18))
        pygame.draw.rect(screen, fill,
                         (cx - base_w, body_bot, base_w * 2, base_h))
        pygame.draw.rect(screen, outline,
                         (cx - base_w, body_bot, base_w * 2, base_h), 2)
        stem_w = max(2, int(r * 0.18))
        stem_h = max(2, int(r * 0.12))
        pygame.draw.rect(screen, fill,
                         (cx - stem_w / 2, body_bot - stem_h,
                          stem_w, stem_h))

# =====================================================================
# CARD GRID — replica um template (card_layout) em N células
# =====================================================================
from src.ui.bindings import resolve_wdata


class CardGrid(Widget):
    """
    Grid de cards cujo visual vem 100% do JSON (`card_layout`).

    Cada widget do `card_layout` é posicionado em coordenadas RELATIVAS
    à célula (0..1), não ao pai. O widget replica pra cada item da lista.

    Suporta:
      - scroll vertical (roda do mouse)
      - hover/click por célula (on_select(idx))
      - bindings {item.xxx} resolvidos em runtime
      - cache dos sub-widgets por slot (não recria a cada frame)
    """
    def __init__(self, wid, rect,
                 items=None,
                 cols=4,
                 rows=3,
                 cell_gap=8,
                 padding=0,
                 card_layout=None,
                 on_select=None,
                 show_scrollbar=True,
                 scrollbar_width=12,
                 scrollbar_color=(212, 168, 80),
                 scrollbar_bg=(26, 26, 46),
                 scrollbar_radius=6,
                 z=0, tab=None,
                 click_sound="CLICK", hover_sound=None,
                 click_volume=None, hover_volume=None,
                 screen_loader=None):
        super().__init__(wid, rect, z=z)
        self.items = items or []
        self.cols = max(1, int(cols))
        self.rows = max(1, int(rows))
        self.cell_gap = int(cell_gap)
        self.padding = int(padding)
        self.card_layout = list(card_layout or [])
        self.on_select = on_select
        self.tab = tab
        self.click_sound = click_sound
        self.hover_sound = hover_sound
        self.click_volume = click_volume
        self.hover_volume = hover_volume
        self._loader = screen_loader

        # Scrollbar
        self.show_scrollbar = bool(show_scrollbar)
        self.scrollbar_width = int(scrollbar_width)
        self.scrollbar_color = scrollbar_color
        self.scrollbar_bg = scrollbar_bg
        self.scrollbar_radius = int(scrollbar_radius)

        # Estado
        self.scroll = 0
        self._hover_idx = -1
        self._dragging_scroll = False
        self._scroll_drag_offset = 0

        # Cache dos sub-widgets por slot (0..cols*rows-1)
        self._slot_widgets = {}

    # -----------------------------------------------------------------
    # Cálculos
    # -----------------------------------------------------------------
    def _inner_rect(self):
        r = self.rect.inflate(-self.padding * 2, -self.padding * 2)
        return r

    def _cell_rect(self, col, row):
        inner = self._inner_rect()
        gap = self.cell_gap
        cw = (inner.width - gap * (self.cols - 1)) // self.cols
        ch = (inner.height - gap * (self.rows - 1)) // self.rows
        x = inner.x + col * (cw + gap)
        y = inner.y + row * (ch + gap)
        return pygame.Rect(x, y, cw, ch)

    def _total_rows(self):
        if not self.items:
            return 0
        return (len(self.items) + self.cols - 1) // self.cols

    def _max_scroll(self):
        return max(0, self._total_rows() - self.rows)

    # -----------------------------------------------------------------
    # Construção (lazy) dos sub-widgets por slot
    # -----------------------------------------------------------------
    def _ensure_loader(self):
        if self._loader is None:
            from src.ui.screen_loader import ScreenLoader
            self._loader = ScreenLoader

    def _build_slot(self, slot_idx):
        self._ensure_loader()
        col = slot_idx % self.cols
        row = slot_idx // self.cols
        cell = self._cell_rect(col, row)

        widgets = []
        for wdata in self.card_layout:
            # Cria com valores crus; serão re-resolvidos a cada render
            w = self._loader._build_widget(wdata, cell, {}, None)
            if w is not None:
                w.z = int(wdata.get("z", 0))
                widgets.append((wdata, w))
        widgets.sort(key=lambda t: t[1].z)
        return widgets

    def _get_slot(self, slot_idx):
        if slot_idx not in self._slot_widgets:
            self._slot_widgets[slot_idx] = self._build_slot(slot_idx)
        return self._slot_widgets[slot_idx]

    # -----------------------------------------------------------------
    # Aplicar bindings em runtime
    # -----------------------------------------------------------------
    _FIELD_MAP = {
        "text": "text",
        "label": "label",
        "fill_color": "fill_color",
        "border_color": "border_color",
        "text_color": "text_color",
        "bg_color": "bg_color",
        "badge_text_color": "text_color",       # badge usa text_color
        "icon": "surface",                       # ImageBox / Button
        "surface": "surface",
        "value": "value",
        "max_value": "max_value",
        "visible": "visible",
    }

    def _apply_bindings(self, widget, wdata, item):
        from src.ui.theme import parse_color
        resolved = resolve_wdata(wdata, item)

        # Mescla top-level + props (props não sobrescreve top-level)
        merged = dict(resolved)
        for k, v in (resolved.get("props", {}) or {}).items():
            if k not in merged:
                merged[k] = v

        for key, attr in self._FIELD_MAP.items():
            if key not in merged:
                continue
            val = merged[key]
            if key.endswith("color") or key.endswith("_color"):
                if isinstance(val, str) and val.startswith("#"):
                    c = parse_color(val, None)
                    if c:
                        val = c
            try:
                setattr(widget, attr, val)
            except Exception:
                pass

        # Surface / icon resolvidos como objeto direto
        if "surface" in merged and hasattr(widget, "surface"):
            try: widget.surface = merged["surface"]
            except Exception: pass
        if "icon" in merged and hasattr(widget, "icon"):
            try: widget.icon = merged["icon"]
            except Exception: pass

    # -----------------------------------------------------------------
    # Eventos
    # -----------------------------------------------------------------
    def _hit_index(self, pos):
        inner = self._inner_rect()
        if not inner.collidepoint(pos):
            return -1
        gap = self.cell_gap
        cw = (inner.width - gap * (self.cols - 1)) // self.cols
        ch = (inner.height - gap * (self.rows - 1)) // self.rows
        rel_x = pos[0] - inner.x
        rel_y = pos[1] - inner.y
        col = rel_x // (cw + gap)
        row = rel_y // (ch + gap)
        if col >= self.cols or row >= self.rows:
            return -1
        idx = (self.scroll + row) * self.cols + int(col)
        return int(idx) if 0 <= idx < len(self.items) else -1

    def _scrollbar_rects(self):
        if not self.show_scrollbar or self._max_scroll() <= 0:
            return None, None
        w = self.scrollbar_width
        pad = 4
        track = pygame.Rect(
            self.rect.right - w - pad, self.rect.y + pad,
            w, self.rect.height - pad * 2,
        )
        total = self._total_rows()
        visible = self.rows
        ratio = visible / total if total else 1
        thumb_h = max(24, int(track.height * ratio))
        max_s = self._max_scroll()
        thumb_y = (track.y + int((track.height - thumb_h) *
                                 (self.scroll / max_s))
                   if max_s > 0 else track.y)
        return track, pygame.Rect(track.x, thumb_y, w, thumb_h)

    def handle_event(self, event):
        if not self.visible or not self.enabled:
            return False

        # Scrollbar drag
        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            track, thumb = self._scrollbar_rects()
            if track and thumb and track.collidepoint(event.pos):
                if thumb.collidepoint(event.pos):
                    self._scroll_drag_offset = event.pos[1] - thumb.y
                else:
                    self._scroll_drag_offset = thumb.height // 2
                self._dragging_scroll = True
                return True

        if event.type == pygame.MOUSEMOTION and self._dragging_scroll:
            track, thumb = self._scrollbar_rects()
            if track and thumb and self._max_scroll() > 0:
                range_ = track.height - thumb.height
                rel = event.pos[1] - self._scroll_drag_offset - track.y
                rel = max(0, min(range_, rel))
                if range_ > 0:
                    self.scroll = int(self._max_scroll() * rel / range_)
            return True

        if event.type == pygame.MOUSEBUTTONUP and event.button == 1:
            if self._dragging_scroll:
                self._dragging_scroll = False
                return True

        # Wheel
        if event.type == pygame.MOUSEWHEEL:
            mx, my = pygame.mouse.get_pos()
            if self.rect.collidepoint(mx, my):
                self.scroll -= event.y
                self.scroll = max(0, min(self._max_scroll(), self.scroll))
                return True

        # Hover / click
        if event.type == pygame.MOUSEMOTION:
            old = self._hover_idx
            self._hover_idx = self._hit_index(event.pos)
            if self._hover_idx >= 0 and self._hover_idx != old:
                self._play_hover()

        elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            idx = self._hit_index(event.pos)
            if idx >= 0 and self.on_select:
                self._play_click()
                self.on_select(idx)
                return True
        return False

    # -----------------------------------------------------------------
    # Render
    # -----------------------------------------------------------------
    def render(self, screen):
        if not self.visible:
            return

        # Fundo
        if self.fill_alpha < 255 and self.fill_color:
            surf = pygame.Surface(self.rect.size, pygame.SRCALPHA)
            pygame.draw.rect(surf,
                             with_alpha(self.fill_color, self.fill_alpha),
                             surf.get_rect(), border_radius=8)
            screen.blit(surf, self.rect.topleft)
        elif self.fill_color:
            pygame.draw.rect(screen, self.fill_color, self.rect,
                             border_radius=8)

        if self.border_color and self.border_width > 0:
            pygame.draw.rect(screen, self.border_color, self.rect,
                             self.border_width, border_radius=8)

        # Clip
        old = screen.get_clip()
        clip = self._inner_rect()
        if self.show_scrollbar and self._max_scroll() > 0:
            clip.width -= self.scrollbar_width + 6
        screen.set_clip(clip)

        # Células
        for slot_idx in range(self.cols * self.rows):
            col = slot_idx % self.cols
            row = slot_idx // self.cols
            item_idx = (self.scroll + row) * self.cols + col
            if item_idx < 0 or item_idx >= len(self.items):
                continue
            item = self.items[item_idx]

            # Garante que a célula está dentro do clip
            cell = self._cell_rect(col, row)
            if not cell.colliderect(clip):
                continue

            # Injetar flag de seleção (se a scene setar selected_id)
            for wdata, widget in self._get_slot(slot_idx):
                self._apply_bindings(widget, wdata, item)
                try:
                    widget.render(screen)
                except Exception as e:
                    print(f"[CardGrid] erro render slot={slot_idx} "
                          f"item={item_idx}: {e}")

        screen.set_clip(old)

        # Scrollbar
        track, thumb = self._scrollbar_rects()
        if track and thumb:
            pygame.draw.rect(screen, self.scrollbar_bg, track,
                             border_radius=self.scrollbar_radius)
            col = self.scrollbar_color
            if self._dragging_scroll:
                col = lighten(col, 0.25)
            pygame.draw.rect(screen, col, thumb,
                             border_radius=self.scrollbar_radius)

    def update(self, dt):
        for slot in self._slot_widgets.values():
            for _, w in slot:
                w.update(dt)