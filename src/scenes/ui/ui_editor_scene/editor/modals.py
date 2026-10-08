# src/scenes/ui_editor_scene/editor/modals.py
"""
Modais do editor: LoadPicker (layouts) e ImagePicker (imagens).

Ambos herdam de _BaseListPicker com:
  - modal grande e centralizado na tela
  - busca com input em tempo real + highlight de match
  - scroll (roda, click no track, drag no thumb, PgUp/PgDn)
  - navegação por teclado (↑ ↓ Home End Enter Esc)
  - fontes grandes e visual estilizado
"""
import pygame
from src.ui.theme import FontBook, Palette
from src.ui.screen_loader import _load_ui_image


# =====================================================================
# HELPERS DE DESENHO
# =====================================================================
def _make_gradient(size, c_top, c_bot, radius=0):
    """Cria uma Surface com gradiente vertical e cantos arredondados."""
    w, h = size
    if w <= 0 or h <= 0:
        return None
    surf = pygame.Surface((w, h), pygame.SRCALPHA)
    for y in range(h):
        t = y / max(1, h - 1)
        c = (int(c_top[0] + (c_bot[0] - c_top[0]) * t),
             int(c_top[1] + (c_bot[1] - c_top[1]) * t),
             int(c_top[2] + (c_bot[2] - c_top[2]) * t))
        pygame.draw.line(surf, c, (0, y), (w, y))
    if radius > 0:
        mask = pygame.Surface((w, h), pygame.SRCALPHA)
        pygame.draw.rect(mask, (255, 255, 255, 255),
                         mask.get_rect(), border_radius=radius)
        surf.blit(mask, (0, 0), special_flags=pygame.BLEND_RGBA_MULT)
    return surf


def _make_shadow(size, radius, spread, alpha):
    w, h = size
    if w <= 0 or h <= 0:
        return None
    surf = pygame.Surface((w, h), pygame.SRCALPHA)
    pygame.draw.rect(surf, (0, 0, 0, alpha), surf.get_rect(),
                     border_radius=radius + spread)
    return surf


# =====================================================================
# BASE LIST PICKER
# =====================================================================
class _BaseListPicker:
    # ---- Layout ----
    ITEM_H = 44
    SEARCH_H = 44
    TITLE_H = 56
    HINT_H = 30
    PADDING = 22
    RADIUS = 16

    # ---- Tamanho relativo da tela ----
    MODAL_W_RATIO = 0.72
    MODAL_H_RATIO = 0.82
    MODAL_W_MIN = 720
    MODAL_W_MAX = 1100
    MODAL_H_MIN = 520
    MODAL_H_MAX = 760
    SCREEN_MARGIN = 30

    # ---- Cores ----
    C_BG_TOP        = (36, 44, 66)
    C_BG_BOT        = (18, 24, 38)
    C_BORDER_OUT    = (248, 176, 48)
    C_BORDER_IN     = (90, 106, 150)

    C_TITLE_BAR_TOP = (56, 66, 96)
    C_TITLE_BAR_BOT = (32, 40, 62)
    C_TITLE         = (255, 220, 120)
    C_TITLE_SHADOW  = (20, 10, 0)
    C_TITLE_LINE    = (248, 176, 48)

    C_COUNTER_BG    = (26, 34, 54)
    C_COUNTER_TEXT  = (210, 220, 240)

    C_SEARCH_BG     = (16, 20, 32)
    C_SEARCH_BG_F   = (24, 32, 52)
    C_SEARCH_BORDER = (72, 88, 128)
    C_SEARCH_BOR_F  = (248, 176, 48)
    C_SEARCH_ICON   = (160, 180, 220)
    C_SEARCH_TEXT   = (242, 244, 252)
    C_SEARCH_PHOLD  = (110, 122, 145)

    C_LIST_BG       = (12, 16, 26)
    C_LIST_BORDER   = (50, 62, 90)
    C_ITEM_ODD      = (30, 36, 54)
    C_ITEM_EVEN     = (24, 30, 46)
    C_ITEM_HOVER    = (52, 72, 116)
    C_ITEM_KB       = (58, 88, 62)
    C_ITEM_BORDER   = (60, 76, 108)
    C_ITEM_HOVER_B  = (248, 176, 48)
    C_ITEM_KB_B     = (140, 220, 140)

    C_TEXT          = (242, 244, 252)
    C_TEXT_MUTED    = (120, 130, 150)
    C_MATCH_BG      = (255, 210, 90, 140)
    C_MATCH_TEXT    = (255, 244, 190)

    C_SCROLL_BG     = (30, 36, 52)
    C_SCROLL_THUMB  = (140, 160, 210)
    C_SCROLL_THU_H  = (210, 230, 255)

    C_HINT_BAR      = (14, 18, 28)
    C_HINT_TEXT     = (140, 150, 170)

    C_X_BG          = (100, 50, 50)
    C_X_BG_H        = (180, 70, 70)
    C_X_BD          = (180, 100, 100)
    C_X_BD_H        = (240, 140, 140)
    C_X_TEXT        = (255, 230, 230)

    TITLE = "PICKER"

    # -----------------------------------------------------------------
    def __init__(self):
        self.open = False
        self.rect = pygame.Rect(0, 0, 900, 600)

        self.items = []
        self.filtered = []
        self.hover_idx = -1
        self.on_select = None
        self.scroll = 0

        # Busca
        self.search_text = ""
        self.search_active = True
        self.search_cursor_t = 0.0

        # Teclado
        self.kb_index = -1

        # Rects internos (calculados em _recalc_layout)
        self._title_rect = pygame.Rect(0, 0, 0, 0)
        self._counter_rect = pygame.Rect(0, 0, 0, 0)
        self._search_rect = pygame.Rect(0, 0, 0, 0)
        self._list_rect_cache = pygame.Rect(0, 0, 0, 0)
        self._hint_rect = pygame.Rect(0, 0, 0, 0)

        # Scrollbar drag
        self._dragging_scroll = False
        self._scroll_drag_offset = 0

        # Surfaces cacheadas
        self._bg_surface = None
        self._title_bar_surface = None
        self._shadow_surface = None

    # -----------------------------------------------------------------
    # ABERTURA / FECHAMENTO
    # -----------------------------------------------------------------
    def open_with(self, items, on_select, center=None):
        self.items = sorted(list(items))
        self.on_select = on_select
        self.open = True

        self.hover_idx = -1
        self.kb_index = -1
        self.scroll = 0
        self.search_text = ""
        self.search_active = True
        self._dragging_scroll = False

        self._apply_filter()
        self._layout_modal()

    def close(self):
        self.open = False

    def _layout_modal(self):
        """Tamanho grande + sempre centralizado na tela."""
        sfc = pygame.display.get_surface()
        if sfc:
            sw, sh = sfc.get_size()
        else:
            sw, sh = 1280, 720

        w = int(sw * self.MODAL_W_RATIO)
        h = int(sh * self.MODAL_H_RATIO)
        w = max(self.MODAL_W_MIN, min(self.MODAL_W_MAX, w))
        h = max(self.MODAL_H_MIN, min(self.MODAL_H_MAX, h))

        # Nunca maior que a tela
        w = min(w, sw - self.SCREEN_MARGIN * 2)
        h = min(h, sh - self.SCREEN_MARGIN * 2)

        self.rect = pygame.Rect(0, 0, w, h)
        self.rect.center = (sw // 2, sh // 2)

        self._recalc_layout()

    def _recalc_layout(self):
        """Recalcula rects internos e caches de superfície."""
        r = self.rect
        p = self.PADDING

        # Título
        self._title_rect = pygame.Rect(
            r.x + p, r.y + 10,
            r.width - p * 2, self.TITLE_H
        )

        # Contador (badge à direita do título)
        cw, ch = 120, 32
        self._counter_rect = pygame.Rect(
            r.right - p - cw,
            self._title_rect.centery - ch // 2,
            cw, ch
        )

        # Busca
        self._search_rect = pygame.Rect(
            r.x + p,
            self._title_rect.bottom + 8,
            r.width - p * 2,
            self.SEARCH_H
        )

        # Hint (rodapé colado nas bordas)
        self._hint_rect = pygame.Rect(
            r.x + 1,
            r.bottom - self.HINT_H - 1,
            r.width - 2,
            self.HINT_H
        )

        # Lista
        self._list_rect_cache = pygame.Rect(
            r.x + p,
            self._search_rect.bottom + 12,
            r.width - p * 2,
            self._hint_rect.y - self._search_rect.bottom - 16
        )

        # ---- Cache de superfícies ----
        self._bg_surface = _make_gradient(
            (r.width, r.height),
            self.C_BG_TOP, self.C_BG_BOT, self.RADIUS
        )
        self._title_bar_surface = _make_gradient(
            (r.width - 8, self.TITLE_H),
            self.C_TITLE_BAR_TOP, self.C_TITLE_BAR_BOT, 10
        )
        self._shadow_surface = _make_shadow(
            (r.width + 24, r.height + 24),
            self.RADIUS, 8, 170
        )

    # -----------------------------------------------------------------
    # FILTRO
    # -----------------------------------------------------------------
    def _apply_filter(self):
        q = self.search_text.strip().lower()
        if not q:
            self.filtered = list(self.items)
        else:
            def score(name):
                n = name.lower()
                i = n.find(q)
                if i < 0:
                    return (2, 0, name)
                if i == 0:
                    return (0, i, name)
                return (1, i, name)

            matches = [n for n in self.items if q in n.lower()]
            matches.sort(key=score)
            self.filtered = matches

        self.scroll = 0
        self.hover_idx = -1
        if self.kb_index >= len(self.filtered):
            self.kb_index = -1

    # -----------------------------------------------------------------
    # GEOMETRIA
    # -----------------------------------------------------------------
    def _list_rect(self):
        return self._list_rect_cache

    def _max_scroll(self):
        lr = self._list_rect()
        total = len(self.filtered) * self.ITEM_H
        # +2 para o último item não ficar colado na borda inferior
        return max(0, total + 2 - lr.height)

    def _hit_index(self, pos):
        lr = self._list_rect()
        if not lr.collidepoint(pos):
            return -1
        rel_y = pos[1] - lr.y - 4 + self.scroll
        if rel_y < 0:
            return -1
        idx = rel_y // self.ITEM_H
        return int(idx) if 0 <= idx < len(self.filtered) else -1

    def _ensure_visible(self, idx):
        lr = self._list_rect()
        item_top = idx * self.ITEM_H
        item_bot = item_top + self.ITEM_H
        if item_top < self.scroll:
            self.scroll = item_top
        elif item_bot > self.scroll + lr.height - 8:
            self.scroll = item_bot - lr.height + 8
        self.scroll = max(0, min(self._max_scroll(), self.scroll))

    def _scrollbar_rects(self):
        """Retorna (track, thumb) ou (None, None)."""
        if self._max_scroll() <= 0:
            return None, None
        lr = self._list_rect()
        w = 10
        track = pygame.Rect(lr.right - w - 3, lr.y + 4, w, lr.height - 8)
        visible = lr.height
        total = visible + self._max_scroll()
        thumb_h = max(40, int(track.height * visible / max(1, total)))
        max_s = max(1, self._max_scroll())
        thumb_y = track.y + int((track.height - thumb_h) *
                                self.scroll / max_s)
        thumb = pygame.Rect(track.x, thumb_y, w, thumb_h)
        return track, thumb

    def _update_scroll_from_mouse(self, mouse_y):
        track, thumb = self._scrollbar_rects()
        if not track or not thumb:
            return
        thumb_range = track.height - thumb.height
        if thumb_range <= 0:
            return
        rel = mouse_y - self._scroll_drag_offset - track.y
        rel = max(0, min(thumb_range, rel))
        self.scroll = int(self._max_scroll() * rel / thumb_range)

    # -----------------------------------------------------------------
    # EVENTOS
    # -----------------------------------------------------------------
    def handle_event(self, event):
        if not self.open:
            return False

        # =============================================================
        # TECLADO
        # =============================================================
        if event.type == pygame.KEYDOWN:
            if event.key == pygame.K_ESCAPE:
                if self.search_text:
                    self.search_text = ""
                    self._apply_filter()
                else:
                    self.close()
                return True

            if event.key == pygame.K_RETURN:
                idx = self.kb_index
                if idx < 0 and self.filtered:
                    idx = 0
                if 0 <= idx < len(self.filtered):
                    self._select(self.filtered[idx])
                return True

            if event.key == pygame.K_UP:
                if not self.filtered:
                    return True
                if self.kb_index <= 0:
                    self.kb_index = 0
                else:
                    self.kb_index -= 1
                self._ensure_visible(self.kb_index)
                return True

            if event.key == pygame.K_DOWN:
                if not self.filtered:
                    return True
                if self.kb_index < 0:
                    self.kb_index = 0
                elif self.kb_index < len(self.filtered) - 1:
                    self.kb_index += 1
                self._ensure_visible(self.kb_index)
                return True

            if event.key == pygame.K_PAGEUP:
                lr = self._list_rect()
                self.scroll = max(0, self.scroll - lr.height)
                return True

            if event.key == pygame.K_PAGEDOWN:
                lr = self._list_rect()
                self.scroll = min(self._max_scroll(),
                                  self.scroll + lr.height)
                return True

            if event.key == pygame.K_HOME:
                self.kb_index = 0 if self.filtered else -1
                self.scroll = 0
                return True

            if event.key == pygame.K_END:
                if self.filtered:
                    self.kb_index = len(self.filtered) - 1
                    self._ensure_visible(self.kb_index)
                return True

            if event.key == pygame.K_BACKSPACE:
                if self.search_text:
                    self.search_text = self.search_text[:-1]
                    self._apply_filter()
                return True

            if event.key == pygame.K_DELETE:
                self.search_text = ""
                self._apply_filter()
                return True

            mods = pygame.key.get_mods()
            ctrl = bool(mods & pygame.KMOD_CTRL)

            if ctrl and event.key == pygame.K_v:
                try:
                    from src.scenes.ui.ui_editor_scene.editor.fields import Clipboard
                    pasted = Clipboard.get() or ""
                    if pasted:
                        pasted = pasted.splitlines()[0]
                        self.search_text += pasted
                        self._apply_filter()
                except Exception:
                    pass
                return True

            if ctrl and event.key == pygame.K_c:
                try:
                    from src.scenes.ui.ui_editor_scene.editor.fields import Clipboard
                    Clipboard.set(self.search_text)
                except Exception:
                    pass
                return True

            if event.unicode and event.unicode.isprintable():
                self.search_text += event.unicode
                self.search_active = True
                self._apply_filter()
                return True

            return True

        # =============================================================
        # MOUSE — movimento
        # =============================================================
        if event.type == pygame.MOUSEMOTION:
            if self._dragging_scroll:
                self._update_scroll_from_mouse(event.pos[1])
                return True
            self.hover_idx = self._hit_index(event.pos)
            if self._search_rect.collidepoint(event.pos):
                self.search_active = True
            return True

        # =============================================================
        # MOUSE — clique esquerdo
        # =============================================================
        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            # Scrollbar drag / click no track
            track, thumb = self._scrollbar_rects()
            if track and thumb and track.collidepoint(event.pos):
                if thumb.collidepoint(event.pos):
                    self._dragging_scroll = True
                    self._scroll_drag_offset = event.pos[1] - thumb.y
                else:
                    self._scroll_drag_offset = thumb.height // 2
                    self._update_scroll_from_mouse(event.pos[1])
                    self._dragging_scroll = True
                return True

            # Busca / botão X
            if self._search_rect.collidepoint(event.pos):
                btn_x = pygame.Rect(self._search_rect.right - 40,
                                    self._search_rect.y + 10,
                                    28,
                                    self._search_rect.height - 20)
                if btn_x.collidepoint(event.pos) and self.search_text:
                    self.search_text = ""
                    self._apply_filter()
                    self.search_active = True
                    return True
                self.search_active = True
                return True

            # Lista
            idx = self._hit_index(event.pos)
            if idx >= 0:
                self._select(self.filtered[idx])
                return True

            # Fora do modal → fecha
            if not self.rect.collidepoint(event.pos):
                self.close()
            return True

        if event.type == pygame.MOUSEBUTTONUP and event.button == 1:
            if self._dragging_scroll:
                self._dragging_scroll = False
                return True

        # =============================================================
        # RODA DO MOUSE
        # =============================================================
        if event.type == pygame.MOUSEWHEEL:
            mx, my = pygame.mouse.get_pos()
            if self.rect.collidepoint(mx, my):
                self.scroll -= event.y * (self.ITEM_H * 2)
                self.scroll = max(0, min(self._max_scroll(), self.scroll))
                return True

        return True

    def _select(self, name):
        if self.on_select:
            self.on_select(name)
        self.close()

    def fixed_update(self, dt):
        self.search_cursor_t += dt

    # -----------------------------------------------------------------
    # RENDER
    # -----------------------------------------------------------------
    def render(self, screen, extra_draw=None):
        if not self.open:
            return

        # Overlay
        ov = pygame.Surface(screen.get_size(), pygame.SRCALPHA)
        ov.fill((0, 0, 0, 175))
        screen.blit(ov, (0, 0))

        # Sombra
        if self._shadow_surface:
            screen.blit(self._shadow_surface,
                        (self.rect.x - 12, self.rect.y - 12))

        # Fundo (gradiente cacheado)
        if self._bg_surface:
            screen.blit(self._bg_surface, self.rect.topleft)
        else:
            pygame.draw.rect(screen, self.C_BG_BOT, self.rect,
                             border_radius=self.RADIUS)

        # Borda dupla
        pygame.draw.rect(screen, self.C_BORDER_OUT, self.rect, 3,
                         border_radius=self.RADIUS)
        inner = self.rect.inflate(-8, -8)
        pygame.draw.rect(screen, self.C_BORDER_IN, inner, 1,
                         border_radius=self.RADIUS - 4)

        # Título + contador
        self._render_title(screen)

        # Busca
        self._render_search(screen)

        # Lista
        self._render_list(screen, extra_draw)

        # Rodapé com dicas
        self._render_hint(screen)

    # -----------------------------------------------------------------
    def _render_title(self, screen):
        tr = self._title_rect

        # Barra de título (cacheada)
        if self._title_bar_surface:
            screen.blit(self._title_bar_surface,
                        (tr.x - 4, tr.y))

        # Linha dourada embaixo
        bar_right = tr.x - 4 + (self.rect.width - 8)
        pygame.draw.line(screen, self.C_TITLE_LINE,
                         (tr.x + 10, tr.bottom - 3),
                         (bar_right - 10, tr.bottom - 3), 2)

        # Texto do título
        font = FontBook.get(26, bold=True)
        shadow = font.render(self.TITLE, True, self.C_TITLE_SHADOW)
        text = font.render(self.TITLE, True, self.C_TITLE)
        tx = tr.x + 12
        ty = tr.centery - text.get_height() // 2
        screen.blit(shadow, (tx + 2, ty + 2))
        screen.blit(text, (tx, ty))

        # Contador (badge)
        self._render_counter(screen)

    def _render_counter(self, screen):
        cr = self._counter_rect
        pygame.draw.rect(screen, self.C_COUNTER_BG, cr,
                         border_radius=cr.height // 2)
        pygame.draw.rect(screen, self.C_BORDER_OUT, cr, 2,
                         border_radius=cr.height // 2)

        text = f"{len(self.filtered)} / {len(self.items)}"
        font = FontBook.get(15, bold=True)
        t = font.render(text, True, self.C_COUNTER_TEXT)
        screen.blit(t, (cr.centerx - t.get_width() // 2,
                        cr.centery - t.get_height() // 2))

    # -----------------------------------------------------------------
    def _render_search(self, screen):
        r = self._search_rect
        focused = self.search_active

        bg = self.C_SEARCH_BG_F if focused else self.C_SEARCH_BG
        border = self.C_SEARCH_BOR_F if focused else self.C_SEARCH_BORDER

        pygame.draw.rect(screen, bg, r, border_radius=10)
        pygame.draw.rect(screen, border, r, 3 if focused else 2,
                         border_radius=10)

        # Ícone de lupa
        cx, cy = r.x + 24, r.centery
        pygame.draw.circle(screen, self.C_SEARCH_ICON, (cx, cy - 2), 7, 2)
        pygame.draw.line(screen, self.C_SEARCH_ICON,
                         (cx + 5, cy + 3), (cx + 11, cy + 9), 3)

        # Texto / placeholder
        font = FontBook.get(18)
        if self.search_text:
            disp = self.search_text
            col = self.C_SEARCH_TEXT
        else:
            disp = "Digite para buscar..."
            col = self.C_SEARCH_PHOLD

        if focused and int(self.search_cursor_t * 2) % 2 == 0:
            disp = disp + "|"

        max_w = r.width - 40 - 44
        # Se não couber, mostra o fim (o começo é cortado)
        while disp and font.size(disp)[0] > max_w:
            disp = disp[1:]

        txt = font.render(disp, True, col)
        screen.blit(txt, (r.x + 44, r.centery - txt.get_height() // 2))

        # Botão X
        if self.search_text:
            btn = pygame.Rect(r.right - 40, r.y + 10, 28, r.height - 20)
            hover = btn.collidepoint(pygame.mouse.get_pos())
            bg_x = self.C_X_BG_H if hover else self.C_X_BG
            bd_x = self.C_X_BD_H if hover else self.C_X_BD
            pygame.draw.rect(screen, bg_x, btn, border_radius=6)
            pygame.draw.rect(screen, bd_x, btn, 2, border_radius=6)
            xfont = FontBook.get(18, bold=True)
            xs = xfont.render("X", True, self.C_X_TEXT)
            screen.blit(xs, (btn.centerx - xs.get_width() // 2,
                             btn.centery - xs.get_height() // 2))

    # -----------------------------------------------------------------
    def _render_list(self, screen, extra_draw):
        lr = self._list_rect()

        # Fundo
        pygame.draw.rect(screen, self.C_LIST_BG, lr, border_radius=10)
        pygame.draw.rect(screen, self.C_LIST_BORDER, lr, 2,
                         border_radius=10)

        if not self.filtered:
            msg = ("Nada corresponde a \"" + self.search_text + "\""
                   if self.search_text else "(vazio)")
            font = FontBook.get(18)
            t = font.render(msg, True, self.C_TEXT_MUTED)
            screen.blit(t, t.get_rect(center=lr.center))
            return

        # Área visível com um inset
        clip = lr.inflate(-6, -6)
        old = screen.get_clip()
        screen.set_clip(clip)

        total = len(self.filtered)
        first = max(0, self.scroll // self.ITEM_H - 1)
        last = min(total, first + (lr.height // self.ITEM_H) + 3)

        for i in range(first, last):
            name = self.filtered[i]
            y = lr.y + 4 + i * self.ITEM_H - self.scroll
            r = pygame.Rect(lr.x + 6, y,
                            lr.width - 12 - 14, self.ITEM_H - 2)
            if r.bottom < clip.y - 4 or r.y > clip.bottom + 4:
                continue

            is_hover = (i == self.hover_idx)
            is_kb = (i == self.kb_index)

            if is_kb:
                bg = self.C_ITEM_KB
                bd = self.C_ITEM_KB_B
                bw = 3
            elif is_hover:
                bg = self.C_ITEM_HOVER
                bd = self.C_ITEM_HOVER_B
                bw = 2
            else:
                bg = self.C_ITEM_ODD if (i % 2 == 0) else self.C_ITEM_EVEN
                bd = self.C_ITEM_BORDER
                bw = 1

            pygame.draw.rect(screen, bg, r, border_radius=8)
            pygame.draw.rect(screen, bd, r, bw, border_radius=8)

            text_x = r.x + 18
            if extra_draw is not None:
                extra_draw(screen, name, r, clip)
                text_x = r.x + 60

            self._render_item_text(screen, name, text_x, r)

        screen.set_clip(old)

        # Scrollbar
        track, thumb = self._scrollbar_rects()
        if track and thumb:
            pygame.draw.rect(screen, self.C_SCROLL_BG, track,
                             border_radius=track.width // 2)
            col = self.C_SCROLL_THU_H if self._dragging_scroll \
                else self.C_SCROLL_THUMB
            pygame.draw.rect(screen, col, thumb,
                             border_radius=thumb.width // 2)

    # -----------------------------------------------------------------
    def _render_item_text(self, screen, name, x, r):
        """Nome com destaque dos caracteres que casaram com a busca."""
        font = FontBook.get(18)
        col = self.C_TEXT
        q = self.search_text.strip().lower()

        if not q:
            s = font.render(name, True, col)
            screen.blit(s, (x, r.centery - s.get_height() // 2))
            return

        i = name.lower().find(q)
        if i < 0:
            s = font.render(name, True, col)
            screen.blit(s, (x, r.centery - s.get_height() // 2))
            return

        before = name[:i]
        match = name[i:i + len(q)]
        after = name[i + len(q):]

        w_before = font.size(before)[0]
        w_match = font.size(match)[0]

        y = r.centery - font.get_height() // 2

        if before:
            s = font.render(before, True, col)
            screen.blit(s, (x, y))

        mx = x + w_before
        hl_rect = pygame.Rect(mx - 3, y - 2,
                              w_match + 6, font.get_height() + 2)
        hl = pygame.Surface(hl_rect.size, pygame.SRCALPHA)
        pygame.draw.rect(hl, self.C_MATCH_BG, hl.get_rect(),
                         border_radius=4)
        screen.blit(hl, hl_rect.topleft)

        s = font.render(match, True, self.C_MATCH_TEXT)
        screen.blit(s, (mx, y))

        if after:
            s = font.render(after, True, col)
            screen.blit(s, (mx + w_match, y))

    # -----------------------------------------------------------------
    def _render_hint(self, screen):
        r = self._hint_rect
        pygame.draw.rect(
            screen, self.C_HINT_BAR, r,
            border_bottom_left_radius=self.RADIUS - 2,
            border_bottom_right_radius=self.RADIUS - 2,
        )
        # Linha dourada superior
        pygame.draw.line(screen, self.C_BORDER_OUT,
                         (r.x + 12, r.y), (r.right - 12, r.y), 1)

        font = FontBook.get(13)
        text = ("↑ ↓  navegar      Enter  abrir      "
                "Esc  limpar / fechar      digite para buscar")
        t = font.render(text, True, self.C_HINT_TEXT)
        screen.blit(t, (r.centerx - t.get_width() // 2,
                        r.centery - t.get_height() // 2))


# =====================================================================
# LOAD PICKER
# =====================================================================
class LoadPicker(_BaseListPicker):
    TITLE = "CARREGAR LAYOUT"


# =====================================================================
# IMAGE PICKER
# =====================================================================
class ImagePicker(_BaseListPicker):
    TITLE = "ESCOLHER IMAGEM"

    def open_with(self, items, on_select, center=None):
        items = ["(nenhuma)"] + list(items)
        super().open_with(items, on_select, center)

    def render(self, screen):
        def draw_thumb(target, name, rect, clip):
            size = min(rect.height - 12, 36)
            thumb = pygame.Rect(
                rect.x + 12,
                rect.centery - size // 2,
                size, size
            )
            pygame.draw.rect(target, (16, 20, 30), thumb, border_radius=6)
            pygame.draw.rect(target, (60, 76, 108), thumb, 1,
                             border_radius=6)

            if name == "(nenhuma)":
                f = FontBook.get(14, True).render(
                    "—", True, (150, 160, 180))
                target.blit(f, (thumb.centerx - f.get_width() // 2,
                                thumb.centery - f.get_height() // 2))
                return

            surf = _load_ui_image(name)
            if surf is not None:
                try:
                    scaled = pygame.transform.smoothscale(
                        surf, (thumb.width - 6, thumb.height - 6))
                    target.blit(scaled, (thumb.x + 3, thumb.y + 3))
                except Exception:
                    pass

        super().render(screen, extra_draw=draw_thumb)