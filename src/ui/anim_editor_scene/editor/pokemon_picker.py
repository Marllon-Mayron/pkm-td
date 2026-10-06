"""
PokemonPicker — modal para escolher um frame específico de um pokémon.

Layout:
  ┌──────────────────────────────────────────────┐
  │ Escolher frame de Pokémon  [X]               │
  ├────────────────┬─────────────────────────────┤
  │  ANIMAÇÕES     │  Direções: [⬇][↘][➡]...     │
  │  ▸ idle        │                              │
  │  ▸ walk        │  ┌───┬───┬───┬───┐          │
  │  ▸ attack      │  │ f │ f │ f │ f │  frames  │
  │  ▸ hurt        │  └───┴───┴───┴───┘          │
  │  ...           │  Preview grande              │
  ├────────────────┴─────────────────────────────┤
  │              [Cancelar]  [Usar este frame]    │
  └──────────────────────────────────────────────┘
"""
import pygame

from src.ui.theme import Palette, FontBook
from src.ui.anim_editor_scene.editor import scene_loader as SL


class PokemonPicker:
    FRAME_CELL = 52
    FRAME_PAD = 8
    ANIM_ROW_H = 28
    DIR_BTN_W = 52
    DIR_BTN_H = 30

    def __init__(self):
        self.open = False
        self.rect = pygame.Rect(0, 0, 820, 560)

        self.pid = None
        self.pname = ""
        self.shiny = False

        self.animations = []
        self.selected_anim = None

        self.directions = []
        self.selected_dir = None

        self.frames = []
        self.selected_frame = 0

        # Scrolling da lista de animações
        self.anim_scroll = 0

        # Callback
        self.on_select = None

        # Cache de frames em miniatura
        self._thumb_cache = {}

        # Rects internos (recalculados no layout)
        self._anim_rects = []
        self._dir_rects = []
        self._frame_rects = []
        self._btn_cancel = None
        self._btn_use = None
        self._clip_anims = None
        self._clip_frames = None

    # =================================================================
    def open_with(self, pid: int, pname: str, on_select,
                  center=None, shiny: bool = False):
        self.pid = int(pid)
        self.pname = str(pname)
        self.shiny = bool(shiny)
        self.on_select = on_select
        self.open = True
        self.anim_scroll = 0

        self.animations = SL.list_pokemon_animations(self.pid, self.shiny)
        self.selected_anim = self.animations[0] if self.animations else None

        self._reload_directions()
        self._reload_frames()
        self.selected_frame = 0

        # Centraliza
        sfc = pygame.display.get_surface()
        if sfc:
            w, h = sfc.get_size()
            cx, cy = center or (w // 2, h // 2)
            self.rect.center = (cx, cy)

        print(f"[POKEMON_PICKER] aberto para {pname} (#{pid}) "
              f"- {len(self.animations)} animações")

    def close(self):
        self.open = False
        self.on_select = None

    # =================================================================
    def _reload_directions(self):
        if not self.selected_anim:
            self.directions = []
            self.selected_dir = None
            return
        self.directions = SL.list_pokemon_directions(
            self.pid, self.selected_anim, self.shiny)
        if not self.directions:
            self.directions = ["down"]
        if self.selected_dir not in self.directions:
            # Prefere "down"
            self.selected_dir = "down" if "down" in self.directions else self.directions[0]

    def _reload_frames(self):
        if not (self.selected_anim and self.selected_dir):
            self.frames = []
            return
        self.frames = SL.get_pokemon_frames(
            self.pid, self.selected_anim, self.selected_dir, self.shiny)
        self.selected_frame = 0
        self._thumb_cache.clear()

    # =================================================================
    def _layout(self):
        r = self.rect
        pad = 16

        # Área esquerda: animações (180px)
        self._anim_area = pygame.Rect(r.x + pad, r.y + 56, 180, r.height - 130)
        self._clip_anims = self._anim_area.copy()

        # Área direita: direções + frames
        right_x = self._anim_area.right + 16
        right_w = r.right - pad - right_x
        self._dir_area = pygame.Rect(right_x, r.y + 56, right_w, 34)
        self._frames_area = pygame.Rect(right_x, self._dir_area.bottom + 12,
                                        right_w, r.bottom - 100 - self._dir_area.bottom - 12)
        self._clip_frames = self._frames_area.copy()

        # Botões
        self._btn_cancel = pygame.Rect(r.right - pad - 110,
                                       r.bottom - pad - 34, 100, 34)
        self._btn_use = pygame.Rect(self._btn_cancel.left - 130,
                                    self._btn_cancel.y, 120, 34)

    # =================================================================
    def handle_event(self, event):
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

        if event.type == pygame.MOUSEWHEEL:
            mx, my = pygame.mouse.get_pos()
            if self._anim_area.collidepoint((mx, my)):
                total = len(self.animations)
                visible = self._anim_area.height // self.ANIM_ROW_H
                max_s = max(0, total - visible)
                self.anim_scroll = max(0, min(max_s, self.anim_scroll - event.y))
                return True
            return True  # bloqueia scroll global

        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            pos = event.pos

            # Fora do modal → fecha
            if not self.rect.collidepoint(pos):
                self.close()
                return True

            # Animações
            for anim_name, r in self._anim_rects:
                if r.collidepoint(pos):
                    if anim_name != self.selected_anim:
                        self.selected_anim = anim_name
                        self._reload_directions()
                        self._reload_frames()
                    return True

            # Direções
            for dir_name, r in self._dir_rects:
                if r.collidepoint(pos):
                    if dir_name != self.selected_dir:
                        self.selected_dir = dir_name
                        self._reload_frames()
                    return True

            # Frames
            for i, r in self._frame_rects:
                if r.collidepoint(pos):
                    self.selected_frame = i
                    return True

            # Botões
            if self._btn_cancel and self._btn_cancel.collidepoint(pos):
                self.close()
                return True
            if self._btn_use and self._btn_use.collidepoint(pos):
                self._apply_and_close()
                return True

            return True

        return True

    # =================================================================
    def _apply_and_close(self):
        if self.on_select and self.selected_anim and self.selected_dir:
            uri = SL.make_pokemon_uri(
                self.pid, self.selected_anim,
                self.selected_dir, self.selected_frame, self.shiny
            )
            try:
                self.on_select(uri)
            except Exception as e:
                print(f"[POKEMON_PICKER] erro on_select: {e}")
        self.close()

    # =================================================================
    def _get_thumb(self, idx, size):
        key = (self.selected_anim, self.selected_dir, idx, size)
        if key in self._thumb_cache:
            return self._thumb_cache[key]
        if 0 <= idx < len(self.frames):
            surf = self.frames[idx]
            try:
                thumb = pygame.transform.smoothscale(surf, (size, size))
            except Exception:
                thumb = pygame.transform.scale(surf, (size, size))
            self._thumb_cache[key] = thumb
            return thumb
        return None

    # =================================================================
    def render(self, screen):
        if not self.open:
            return

        self._layout()

        # Backdrop
        ov = pygame.Surface(screen.get_size(), pygame.SRCALPHA)
        ov.fill((0, 0, 0, 170))
        screen.blit(ov, (0, 0))

        # Painel
        pygame.draw.rect(screen, (26, 30, 48), self.rect, border_radius=12)
        pygame.draw.rect(screen, Palette.GOLD, self.rect, 2, border_radius=12)

        # Header
        title_font = FontBook.get(18, bold=True)
        t = title_font.render(
            f"Escolher frame de {self.pname}  (#{self.pid})",
            True, Palette.GOLD)
        screen.blit(t, (self.rect.x + 16, self.rect.y + 14))

        sub_font = FontBook.get(12)
        sub = sub_font.render(
            f"{len(self.frames)} frames  |  anim={self.selected_anim}  |  dir={self.selected_dir}  |  shiny={self.shiny}",
            True, (150, 160, 190))
        screen.blit(sub, (self.rect.x + 16, self.rect.y + 36))

        # Separador
        pygame.draw.line(screen, (60, 76, 110),
                         (self.rect.x + 12, self.rect.y + 52),
                         (self.rect.right - 12, self.rect.y + 52), 1)

        # --------- ANIMAÇÕES ---------
        pygame.draw.rect(screen, (18, 22, 34), self._anim_area, border_radius=6)
        pygame.draw.rect(screen, (60, 76, 110), self._anim_area, 1, border_radius=6)

        old_clip = screen.get_clip()
        screen.set_clip(self._anim_area)

        self._anim_rects = []
        row_h = self.ANIM_ROW_H
        for i in range(self.anim_scroll,
                       min(self.anim_scroll + self._anim_area.height // row_h,
                           len(self.animations))):
            anim_name = self.animations[i]
            ry = self._anim_area.y + (i - self.anim_scroll) * row_h
            rr = pygame.Rect(self._anim_area.x + 2, ry,
                             self._anim_area.width - 4, row_h - 2)
            self._anim_rects.append((anim_name, rr))

            selected = (anim_name == self.selected_anim)
            hover = rr.collidepoint(pygame.mouse.get_pos())

            if selected:
                pygame.draw.rect(screen, (60, 80, 130), rr, border_radius=4)
                pygame.draw.rect(screen, Palette.GOLD, rr, 1, border_radius=4)
            elif hover:
                pygame.draw.rect(screen, (40, 50, 74), rr, border_radius=4)

            col = Palette.GOLD if selected else (210, 220, 240)
            txt = FontBook.get(13, bold=selected).render(
                anim_name.capitalize(), True, col)
            screen.blit(txt, (rr.x + 8, rr.centery - txt.get_height() // 2))

        screen.set_clip(old_clip)

        # Scrollbar das animações
        total = len(self.animations)
        visible = self._anim_area.height // row_h
        if total > visible:
            bar_x = self._anim_area.right - 6
            thumb_h = max(20, int(self._anim_area.height * visible / total))
            max_s = max(1, total - visible)
            thumb_y = self._anim_area.y + int((self._anim_area.height - thumb_h)
                                              * self.anim_scroll / max_s)
            pygame.draw.rect(screen, (40, 48, 66),
                             (bar_x, self._anim_area.y, 4, self._anim_area.height),
                             border_radius=2)
            pygame.draw.rect(screen, (150, 170, 210),
                             (bar_x, thumb_y, 4, thumb_h), border_radius=2)

        # --------- DIREÇÕES ---------
        self._dir_rects = []
        dx = self._dir_area.x
        for d in self.directions:
            label = {"down": "⬇", "up": "⬆", "left": "⬅", "right": "➡",
                     "down-left": "↙", "down-right": "↘",
                     "up-left": "↖", "up-right": "↗"}.get(d, d[:2])
            rr = pygame.Rect(dx, self._dir_area.y, self.DIR_BTN_W, self.DIR_BTN_H)
            self._dir_rects.append((d, rr))

            selected = (d == self.selected_dir)
            hover = rr.collidepoint(pygame.mouse.get_pos())

            if selected:
                pygame.draw.rect(screen, (72, 108, 148), rr, border_radius=4)
                pygame.draw.rect(screen, Palette.GOLD, rr, 2, border_radius=4)
            elif hover:
                pygame.draw.rect(screen, (48, 60, 90), rr, border_radius=4)
                pygame.draw.rect(screen, (140, 170, 220), rr, 1, border_radius=4)
            else:
                pygame.draw.rect(screen, (30, 36, 52), rr, border_radius=4)
                pygame.draw.rect(screen, (60, 76, 110), rr, 1, border_radius=4)

            col = Palette.GOLD if selected else (220, 230, 240)
            txt = FontBook.get(14, bold=True).render(label, True, col)
            screen.blit(txt, txt.get_rect(center=rr.center))

            dx += self.DIR_BTN_W + 4

        # --------- FRAMES ---------
        pygame.draw.rect(screen, (18, 22, 34), self._frames_area, border_radius=6)
        pygame.draw.rect(screen, (60, 76, 110), self._frames_area, 1, border_radius=6)

        old_clip = screen.get_clip()
        screen.set_clip(self._frames_area)

        self._frame_rects = []
        cell = self.FRAME_CELL
        pad = self.FRAME_PAD
        cols = max(1, (self._frames_area.width - pad) // (cell + pad))
        for i, frame_surf in enumerate(self.frames):
            col = i % cols
            row = i // cols
            fx = self._frames_area.x + pad + col * (cell + pad)
            fy = self._frames_area.y + pad + row * (cell + pad)

            rr = pygame.Rect(fx, fy, cell, cell)
            self._frame_rects.append((i, rr))

            selected = (i == self.selected_frame)
            hover = rr.collidepoint(pygame.mouse.get_pos())

            pygame.draw.rect(screen, (24, 28, 42), rr, border_radius=4)
            if selected:
                pygame.draw.rect(screen, Palette.GOLD, rr, 2, border_radius=4)
            elif hover:
                pygame.draw.rect(screen, (100, 130, 190), rr, 1, border_radius=4)
            else:
                pygame.draw.rect(screen, (60, 76, 110), rr, 1, border_radius=4)

            thumb = self._get_thumb(i, cell - 4)
            if thumb:
                tr = thumb.get_rect(center=rr.center)
                screen.blit(thumb, tr.topleft)

            # Index no canto
            idx_t = FontBook.get(10).render(str(i), True, (140, 150, 180))
            screen.blit(idx_t, (rr.x + 3, rr.y + 2))

        screen.set_clip(old_clip)

        # Preview grande do frame atual
        preview_size = 90
        preview_rect = pygame.Rect(
            self._frames_area.right - preview_size - 10,
            self.rect.bottom - 100 - preview_size - 8,
            preview_size, preview_size)
        pygame.draw.rect(screen, (18, 22, 34), preview_rect, border_radius=6)
        pygame.draw.rect(screen, (80, 96, 130), preview_rect, 1, border_radius=6)

        if 0 <= self.selected_frame < len(self.frames):
            big = self._get_thumb(self.selected_frame, preview_size - 8)
            if big:
                screen.blit(big, big.get_rect(center=preview_rect.center))

        # --------- BOTÕES ---------
        cancel_hover = self._btn_cancel.collidepoint(pygame.mouse.get_pos())
        base = (120, 55, 55) if not cancel_hover else (170, 70, 70)
        pygame.draw.rect(screen, base, self._btn_cancel, border_radius=6)
        pygame.draw.rect(screen, Palette.GOLD if cancel_hover else (160, 80, 80),
                         self._btn_cancel, 2, border_radius=6)
        ct = FontBook.get(14, bold=True).render("Cancelar", True, (240, 240, 250))
        screen.blit(ct, ct.get_rect(center=self._btn_cancel.center))

        use_hover = self._btn_use.collidepoint(pygame.mouse.get_pos())
        base = (72, 152, 88) if not use_hover else (104, 184, 120)
        pygame.draw.rect(screen, base, self._btn_use, border_radius=6)
        pygame.draw.rect(screen, Palette.GOLD if use_hover else (80, 96, 130),
                         self._btn_use, 2, border_radius=6)
        ut = FontBook.get(14, bold=True).render("Usar este frame", True, (240, 240, 250))
        screen.blit(ut, ut.get_rect(center=self._btn_use.center))