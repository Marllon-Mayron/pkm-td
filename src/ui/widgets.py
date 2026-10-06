# src/ui/widgets.py
"""
Widgets reutilizáveis.
pixel_art=True (padrão) → escala nearest neighbor (sprite nítido)
pixel_art=False         → escala bilinear (para imagens/fotos)
"""
import pygame

from src.ui.theme import (Palette, FontBook, BUTTON_STYLES,
                          lerp_color, darken, lighten,
                          with_alpha, color_alpha)
from src.ui.windowskin import panel_skin
from src.ui.layout import draw_text_centered
from src.ui.sound_helper import play_ui_sound
from src.ui.image_draw import draw_image_in_rect


def _scale_sprite(surface, size, pixel_art=True):
    """Escala uma surface respeitando pixel_art."""
    try:
        if pixel_art:
            return pygame.transform.scale(surface, size)
        return pygame.transform.smoothscale(surface, size)
    except Exception:
        return pygame.transform.scale(surface, size)


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
                 fill_alpha=255, border_alpha=255,
                 bg_image=None, bg_image_mode="stretch",
                 bg_tint=None, bg_image_alpha=255,
                 border_width=2, border_radius=10, draw_border=True,
                 draw_shadow=True,
                 pixel_art=True,
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
            rect = rect.inflate(wo * 2, ho * 2); rect.center = self.rect.center

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
            if self._pressed:                     base = style["fill_press"]
            elif self._hover and self.enabled:    base = style["fill_hover"]
            else:                                 base = style["fill"]
            fill = self.fill_color if self.fill_color else base

            grad = pygame.Surface(rect.size, pygame.SRCALPHA)
            top = lighten(fill, 0.18); bot = darken(fill, 0.12)
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
            if self.border_alpha < 255:
                bw_surface = pygame.Surface(rect.size, pygame.SRCALPHA)
                pygame.draw.rect(bw_surface,
                                 with_alpha(border, self.border_alpha),
                                 bw_surface.get_rect(),
                                 self.border_width,
                                 border_radius=self.border_radius)
                screen.blit(bw_surface, rect.topleft)
            else:
                pygame.draw.rect(screen, border, rect, self.border_width,
                                 border_radius=self.border_radius)

        if self.enabled and self.draw_border:
            hi = pygame.Rect(rect.x + 3, rect.y + 2, rect.width - 6, 2)
            hi_s = pygame.Surface(hi.size, pygame.SRCALPHA)
            hi_s.fill((255, 255, 255, 60))
            screen.blit(hi_s, hi.topleft)

        font = FontBook.get(self.font_size, bold=self.bold, name=self.font_name)
        tcol = self.text_color if self.text_color else style["text"]

        if self.icon is not None:
            self._render_with_icon(screen, rect, font, tcol)
        else:
            draw_text_centered(screen, self.label, font, tcol, rect,
                               shadow_color=(0, 0, 0, 130),
                               shadow_offset=(2, 2))

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

        if pos == "right":
            ix = rect.right - pad - isize
            tx = rect.x + pad
            tw = rect.width - isize - self.icon_gap - pad * 2
        else:
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
                 title_font_size=None,
                 z=0, font_name="default", bold=True,
                 text_color=None, fill_color=None, border_color=None,
                 fill_alpha=255, border_alpha=255,
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

        if self.draw_border and self.border_width > 0:
            bc = self.border_color if self.border_color else self.skin.border
            self._draw_border(screen, rect, bc)

        if self.title:
            self._render_title(screen, rect)

    def _draw_border(self, screen, rect, color):
        sides = self.border_sides
        alpha = self.border_alpha
        w = self.border_width
        r = self.border_radius

        def _draw_full():
            if alpha < 255:
                surf = pygame.Surface(rect.size, pygame.SRCALPHA)
                pygame.draw.rect(surf, with_alpha(color, alpha),
                                 surf.get_rect(), w, border_radius=r)
                screen.blit(surf, rect.topleft)
            else:
                pygame.draw.rect(screen, color, rect, w, border_radius=r)

        if sides is None:
            _draw_full()
            return
        if isinstance(sides, str):
            sides = [s.strip() for s in sides.split(",") if s.strip()]
        if not sides:
            return
        if "all" in sides or len(sides) >= 4:
            _draw_full()
            return

        col = with_alpha(color, alpha) if alpha < 255 else color
        if alpha < 255:
            surf = pygame.Surface(rect.size, pygame.SRCALPHA)
            if "top" in sides:
                pygame.draw.rect(surf, col, (0, 0, rect.width, w))
            if "bottom" in sides:
                pygame.draw.rect(surf, col, (0, rect.height - w, rect.width, w))
            if "left" in sides:
                pygame.draw.rect(surf, col, (0, 0, w, rect.height))
            if "right" in sides:
                pygame.draw.rect(surf, col, (rect.width - w, 0, w, rect.height))
            screen.blit(surf, rect.topleft)
        else:
            if "top" in sides:
                pygame.draw.rect(screen, col, (rect.x, rect.y, rect.width, w))
            if "bottom" in sides:
                pygame.draw.rect(screen, col,
                                 (rect.x, rect.bottom - w, rect.width, w))
            if "left" in sides:
                pygame.draw.rect(screen, col, (rect.x, rect.y, w, rect.height))
            if "right" in sides:
                pygame.draw.rect(screen, col,
                                 (rect.right - w, rect.y, w, rect.height))

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
                 fill_alpha=255, border_alpha=255, tab=None):
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
                 render_callback=None,
                 z=0, font_name="default", bold=False,
                 text_color=None, fill_color=None, border_color=None,
                 fill_alpha=255, border_alpha=255, tab=None,
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

        clip = self.rect.inflate(-12, -12)
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
                 fill_alpha=255, border_alpha=255, tab=None,
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
# GRID SELECT — como ListView, mas em grid (cols × rows)
# =====================================================================
class GridSelect(Widget):
    """
    Grid clicável. Cada célula é uma "linha" do ListView.
    Mesma API: items, on_select(idx), render_callback(idx, item, screen, rect).
    """
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

        # Fundo (opcional)
        if self.fill_alpha < 255:
            surf = pygame.Surface(self.rect.size, pygame.SRCALPHA)
            pygame.draw.rect(surf, with_alpha(
                self.fill_color or Palette.PANEL_FILL, self.fill_alpha),
                surf.get_rect(), border_radius=8)
            screen.blit(surf, self.rect.topleft)
        elif self.fill_color or self.border_color:
            panel_skin.render(screen, self.rect,
                              border_color=self.border_color,
                              fill_override=self.fill_color)

        for i, cell in enumerate(self._cell_rects()):
            if i >= len(self.items):
                break

            # Hover highlight (atrás do cell)
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

            # Default: string centralizada
            font = FontBook.get(20, bold=self.bold, name=self.font_name)
            col = self.text_color or Palette.TEXT_DARK
            txt = font.render(str(self.items[i]), True, col)
            screen.blit(txt, txt.get_rect(center=cell.center))

# =====================================================================
# TAB PANEL
# =====================================================================
class TabPanel(Widget):
    def __init__(self, wid, rect, tabs=None, current_tab=None,
                 on_change=None, z=0, font_name="default", bold=True,
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

    def _tab_rects(self):
        n = max(1, len(self.tabs))
        w = self.rect.width // n
        h = max(28, int(self.rect.height * 0.12))
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