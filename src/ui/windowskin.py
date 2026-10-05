# src/ui/windowskin.py
"""
Windowskin estilo FireRed + suporte a imagem de fundo custom.
"""
import pygame
from src.ui.theme import Palette, lerp_color
from src.ui.image_draw import draw_image_in_rect


class WindowSkin:
    def __init__(self,
                 radius=10,
                 fill=Palette.PANEL_FILL,
                 fill_dark=Palette.PANEL_FILL_DARK,
                 border=Palette.BORDER_DARK,
                 border_light=Palette.BORDER_LIGHT,
                 shadow=(0, 0, 0, 130),
                 shadow_offset=(4, 4),
                 border_width=2):
        self.radius = radius
        self.fill = fill
        self.fill_dark = fill_dark
        self.border = border
        self.border_light = border_light
        self.shadow = shadow
        self.shadow_offset = shadow_offset
        self.border_width = border_width

    # -----------------------------------------------------------------
    def render(self, target, rect,
               draw_shadow=True,
               border_color=None,
               fill_override=None,
               border_width=None,
               draw_border=True,
               # NOVO — fundo com imagem
               bg_image=None,
               bg_image_mode="stretch",
               bg_tint=None,
               bg_image_alpha=255,
               # NOVO — raio custom
               radius=None):
        r = self.radius if radius is None else radius

        if draw_shadow:
            self._draw_shadow(target, rect, r)

        # 1) Fundo: imagem tem prioridade sobre gradiente
        if bg_image is not None:
            # máscara arredondada sobre a imagem
            layer = pygame.Surface((rect.width, rect.height), pygame.SRCALPHA)
            draw_image_in_rect(layer, bg_image,
                               pygame.Rect(0, 0, rect.width, rect.height),
                               mode=bg_image_mode,
                               tint=bg_tint,
                               alpha=bg_image_alpha)
            mask = pygame.Surface((rect.width, rect.height), pygame.SRCALPHA)
            pygame.draw.rect(mask, (255, 255, 255, 255),
                             mask.get_rect(), border_radius=r)
            layer.blit(mask, (0, 0), special_flags=pygame.BLEND_RGBA_MULT)
            target.blit(layer, rect.topleft)
        else:
            fill = fill_override if fill_override else self.fill
            self._draw_fill(target, rect, fill, r)

        # 2) Borda
        if draw_border:
            bw = self.border_width if border_width is None else int(border_width)
            if bw > 0:
                bc = border_color if border_color else self.border
                pygame.draw.rect(target, bc, rect, bw, border_radius=r)
                if bw >= 2:
                    pygame.draw.rect(target, self.border_light,
                                     rect.inflate(-4, -4), 1,
                                     border_radius=max(2, r - 2))

    # -----------------------------------------------------------------
    def _draw_shadow(self, target, rect, radius):
        s = pygame.Surface((rect.width, rect.height), pygame.SRCALPHA)
        pygame.draw.rect(s, self.shadow, s.get_rect(), border_radius=radius)
        target.blit(s, (rect.x + self.shadow_offset[0],
                        rect.y + self.shadow_offset[1]))

    def _draw_fill(self, target, rect, fill, radius):
        s = pygame.Surface((rect.width, rect.height), pygame.SRCALPHA)
        for y in range(rect.height):
            t = y / max(1, rect.height - 1)
            c = lerp_color(fill, self.fill_dark, t * 0.30)
            pygame.draw.line(s, c, (0, y), (rect.width, y))
        mask = pygame.Surface((rect.width, rect.height), pygame.SRCALPHA)
        pygame.draw.rect(mask, (255, 255, 255, 255),
                         mask.get_rect(), border_radius=radius)
        s.blit(mask, (0, 0), special_flags=pygame.BLEND_RGBA_MULT)
        target.blit(s, rect.topleft)


# =====================================================================
# INSTÂNCIAS PADRÃO (reutilizáveis)
# =====================================================================
panel_skin  = WindowSkin()
dialog_skin = WindowSkin(fill=(240, 240, 220), fill_dark=(208, 208, 184))
dark_skin   = WindowSkin(fill=(72, 88, 128), fill_dark=(48, 60, 96),
                         border=Palette.BORDER_LIGHT,
                         border_light=(180, 200, 232))