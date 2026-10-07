"""Modal para abrir uma animação salva.

Melhorias desta versão:
  - Texto MAIOR (itens 14px, headers 13px, título 18px)
  - Busca em tempo real (nome / categoria / "categoria/nome")
  - Listagem AGRUPADA por categoria (headers com contagem)
  - Scrollbar arrastável + wheel + autoscroll ao navegar
  - Navegação por teclado: ↑↓ PgUp/PgDn Home/End Enter ESC
  - Digite qualquer letra para focar a busca automaticamente
  - Duplo-clique em um item abre
  - Botão X para limpar busca
"""
import pygame

from src.ui.theme import Palette, FontBook
from src.ui.anim_editor_scene.editor import scene_loader as SL
from src.ui.anim_editor_scene.editor.scrollbar import ScrollBar


class OpenPicker:
    # ===== Tamanho da janela =====
    W = 760
    H = 580

    # ===== Layout =====
    PAD = 18
    TITLE_H = 46
    SEARCH_H = 40
    HEADER_ROW_H = 26
    ITEM_ROW_H = 30
    BTN_H = 36
    BTN_W = 120
    SCROLLBAR_W = 12

    # ===== Fontes =====
    F_TITLE = 18
    F_SUB = 12
    F_SEARCH = 14
    F_HEADER = 13
    F_ITEM = 14
    F_BTN = 14
    F_EMPTY = 14

    # ===== Duplo-clique =====
    DOUBLE_CLICK_MS = 350

    def __init__(self):
        self.open = False
        self.rect = pygame.Rect(0, 0, self.W, self.H)

        # Dados
        self.all_items = []          # [(categoria, nome), ...]
        self.filtered_items = []     # após filtro de busca
        self._visual_rows = []       # [("header", cat, n) | ("item", idx)]
        self._item_to_vrow = {}      # item_idx -> vrow
        self.selected = 0            # índice em filtered_items
        self.search_text = ""
        self.search_focused = False
        self.on_select = None

        # Áreas (recalculadas no _layout)
        self._search_rect = None
        self._list_rect = None
        self._btn_cancel = None
        self._btn_open = None
        self._btn_clear_search = None
        self._header_rects = []
        self._row_rects = []

        # Duplo-clique
        self._last_click_ms = 0
        self._last_click_idx = -1

        # Scrollbar
        self.scrollbar = ScrollBar(width=self.SCROLLBAR_W, wheel_step=3)

    # ================================================================
    # API
    # ================================================================
    def open_with(self, on_select, center=None):
        self.all_items = SL.list_all_animations() or []
        self.on_select = on_select
        self.search_text = ""
        self.search_focused = False
        self.selected = 0
        self.scrollbar.scroll = 0
        self._last_click_ms = 0
        self._last_click_idx = -1
        self.open = True
        self._apply_filter()

        sfc = pygame.display.get_surface()
        if sfc:
            w, h = sfc.get_size()
            cx, cy = center or (w // 2, h // 2)

            # Garante que o modal não estoure a tela
            target_w = min(self.W, max(360, w - 40))
            target_h = min(self.H, max(280, h - 40))
            self.rect = pygame.Rect(0, 0, target_w, target_h)
            self.rect.center = (cx, cy)

    def close(self):
        self.open = False
        self.on_select = None
        self.search_focused = False

    # ================================================================
    # FILTRO / ÍNDICES
    # ================================================================
    def _apply_filter(self):
        q = self.search_text.strip().lower()

        if not q:
            self.filtered_items = list(self.all_items)
        else:
            self.filtered_items = [
                (cat, name) for (cat, name) in self.all_items
                if q in name.lower()
                or q in cat.lower()
                or q in f"{cat}/{name}".lower()
            ]

        cat_order = {c: i for i, c in enumerate(SL.list_categories())}
        self.filtered_items.sort(
            key=lambda x: (cat_order.get(x[0], 99), x[1].lower())
        )

        if not self.filtered_items:
            self.selected = 0
        else:
            self.selected = min(self.selected, len(self.filtered_items) - 1)

        self._rebuild_visual_rows()

        # Sempre volta pro topo ao refiltrar
        try:
            self.scrollbar.scroll = 0
        except Exception:
            pass

    def _rebuild_visual_rows(self):
        self._visual_rows = []
        self._item_to_vrow = {}

        by_cat = {}
        for i, (cat, name) in enumerate(self.filtered_items):
            by_cat.setdefault(cat, []).append((i, name))

        for cat in SL.list_categories():
            if cat not in by_cat:
                continue
            entries = by_cat[cat]
            self._visual_rows.append(("header", cat, len(entries)))
            for (i, _name) in entries:
                self._item_to_vrow[i] = len(self._visual_rows)
                self._visual_rows.append(("item", i))

    # ================================================================
    # LAYOUT
    # ================================================================
    def _layout(self):
        r = self.rect
        pad = self.PAD

        y = r.y + self.TITLE_H

        # Barra de busca
        self._search_rect = pygame.Rect(
            r.x + pad, y, r.width - pad * 2, self.SEARCH_H,
        )
        y = self._search_rect.bottom + 10

        # Área de botões (embaixo)
        btn_y = r.bottom - pad - self.BTN_H
        self._btn_cancel = pygame.Rect(
            r.right - pad - self.BTN_W, btn_y, self.BTN_W, self.BTN_H,
        )
        self._btn_open = pygame.Rect(
            self._btn_cancel.left - 8 - self.BTN_W, btn_y,
            self.BTN_W, self.BTN_H,
        )

        # Lista
        list_bottom = btn_y - 12
        self._list_rect = pygame.Rect(
            r.x + pad, y,
            r.width - pad * 2 - self.SCROLLBAR_W - 4,
            max(60, list_bottom - y),
        )

        # Scrollbar
        track = pygame.Rect(
            self._list_rect.right + 4, self._list_rect.y,
            self.SCROLLBAR_W, self._list_rect.height,
        )
        visible_rows = max(1, self._list_rect.height // self.ITEM_ROW_H)
        self.scrollbar.set(
            track,
            total=max(1, len(self._visual_rows)),
            visible=visible_rows,
            wheel_area=self._list_rect,
        )

    # ================================================================
    # AUTO-SCROLL
    # ================================================================
    def _ensure_selected_visible(self):
        if not self.filtered_items or self._list_rect is None:
            return
        vrow = self._item_to_vrow.get(self.selected, 0)
        visible = max(1, self._list_rect.height // self.ITEM_ROW_H)
        cur = self.scrollbar.scroll
        if vrow < cur:
            self.scrollbar.scroll = vrow
        elif vrow >= cur + visible:
            self.scrollbar.scroll = vrow - visible + 1

    # ================================================================
    # NAVEGAÇÃO
    # ================================================================
    def _move_selection(self, delta):
        if not self.filtered_items:
            return
        n = len(self.filtered_items)
        self.selected = max(0, min(n - 1, self.selected + delta))
        self._ensure_selected_visible()

    def _goto_selection(self, idx):
        if not self.filtered_items:
            return
        self.selected = max(0, min(idx, len(self.filtered_items) - 1))
        self._ensure_selected_visible()

    def _page_delta(self):
        visible = max(1, self._list_rect.height // self.ITEM_ROW_H)
        return max(1, visible - 1)

    # ================================================================
    # EVENTOS
    # ================================================================
    def handle_event(self, event) -> bool:
        if not self.open:
            return False
        self._layout()

        # ---------- TECLADO ----------
        if event.type == pygame.KEYDOWN:
            return self._handle_keydown(event)

        # ---------- SCROLLBAR (prioridade nos cliques) ----------
        if self.scrollbar.handle_event(event):
            return True

        # ---------- MOUSE DOWN ----------
        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            return self._handle_mousedown(event)

        # ---------- WHEEL ----------
        if event.type == pygame.MOUSEWHEEL:
            if self.scrollbar.handle_wheel(event.y, pygame.mouse.get_pos()):
                return True
            return True

        # ---------- MOUSEMOTION / MOUSEUP ----------
        if event.type in (pygame.MOUSEMOTION, pygame.MOUSEBUTTONUP):
            self.scrollbar.handle_event(event)
            return True

        return True

    def _handle_keydown(self, event) -> bool:
        # ---------- BUSCA FOCADA ----------
        if self.search_focused:
            if event.key == pygame.K_ESCAPE:
                if self.search_text:
                    self.search_text = ""
                    self._apply_filter()
                else:
                    self.search_focused = False
                return True
            if event.key == pygame.K_RETURN:
                self._apply_and_close()
                return True
            if event.key == pygame.K_DOWN:
                self.search_focused = False
                self._move_selection(1)
                return True
            if event.key == pygame.K_UP:
                self.search_focused = False
                self._move_selection(-1)
                return True
            if event.key == pygame.K_TAB:
                self.search_focused = False
                return True
            if event.key == pygame.K_BACKSPACE:
                self.search_text = self.search_text[:-1]
                self._apply_filter()
                return True
            if event.unicode and event.unicode.isprintable():
                if len(self.search_text) < 60:
                    self.search_text += event.unicode
                    self._apply_filter()
                return True
            return True

        # ---------- BUSCA NÃO FOCADA ----------
        if event.key == pygame.K_ESCAPE:
            self.close()
            return True
        if event.key == pygame.K_RETURN:
            self._apply_and_close()
            return True
        if event.key == pygame.K_UP:
            self._move_selection(-1)
            return True
        if event.key == pygame.K_DOWN:
            self._move_selection(1)
            return True
        if event.key == pygame.K_PAGEUP:
            self._move_selection(-self._page_delta())
            return True
        if event.key == pygame.K_PAGEDOWN:
            self._move_selection(self._page_delta())
            return True
        if event.key == pygame.K_HOME:
            self._goto_selection(0)
            return True
        if event.key == pygame.K_END:
            self._goto_selection(len(self.filtered_items) - 1)
            return True

        # ---------- AUTOFOCUS ----------
        # Se o usuário digitar uma letra, foca a busca automaticamente.
        c = event.unicode
        if c and c.isprintable() and c not in "\t\r\n":
            mods = pygame.key.get_mods()
            if not (mods & (pygame.KMOD_CTRL
                            | pygame.KMOD_ALT
                            | pygame.KMOD_META)):
                self.search_focused = True
                if len(self.search_text) < 60:
                    self.search_text += c
                    self._apply_filter()
                return True

        return True

    def _handle_mousedown(self, event) -> bool:
        pos = event.pos

        # 1. Botões
        if self._btn_cancel and self._btn_cancel.collidepoint(pos):
            self.close()
            return True
        if self._btn_open and self._btn_open.collidepoint(pos):
            if self.filtered_items:
                self._apply_and_close()
            return True

        # 2. X de limpar busca
        if (self._btn_clear_search
                and self._btn_clear_search.collidepoint(pos)):
            self.search_text = ""
            self.search_focused = True
            self._apply_filter()
            return True

        # 3. Barra de busca
        if self._search_rect and self._search_rect.collidepoint(pos):
            self.search_focused = True
            return True

        # 4. Linhas da lista
        for rect, item_idx in self._row_rects:
            if rect.collidepoint(pos):
                now = pygame.time.get_ticks()
                is_double = (
                    item_idx == self.selected
                    and item_idx == self._last_click_idx
                    and (now - self._last_click_ms) < self.DOUBLE_CLICK_MS
                )
                if is_double:
                    self._apply_and_close()
                else:
                    self.selected = item_idx
                self._last_click_idx = item_idx
                self._last_click_ms = now
                return True

        # 5. Headers apenas desfocam a busca
        for rect, _cat, _n in self._header_rects:
            if rect.collidepoint(pos):
                self.search_focused = False
                return True

        # 6. Clique fora do modal → fecha
        if not self.rect.collidepoint(pos):
            self.close()
            return True

        self.search_focused = False
        return True

    def _apply_and_close(self):
        if not self.filtered_items:
            self.close()
            return
        if not (0 <= self.selected < len(self.filtered_items)):
            self.close()
            return

        cat, name = self.filtered_items[self.selected]
        cb = self.on_select
        self.close()
        if cb:
            try:
                cb(cat, name)
            except Exception as e:
                print(f"[OPEN_PICKER] erro ao abrir: {e}")

    # ================================================================
    # RENDER
    # ================================================================
    def render(self, screen):
        if not self.open:
            return
        self._layout()

        # Backdrop
        ov = pygame.Surface(screen.get_size(), pygame.SRCALPHA)
        ov.fill((0, 0, 0, 180))
        screen.blit(ov, (0, 0))

        # Painel com sombra
        r = self.rect
        shadow = pygame.Surface((r.width + 16, r.height + 16),
                                pygame.SRCALPHA)
        pygame.draw.rect(shadow, (0, 0, 0, 160),
                         shadow.get_rect(), border_radius=14)
        screen.blit(shadow, (r.x - 8, r.y - 8))

        pygame.draw.rect(screen, (22, 26, 40), r, border_radius=12)
        pygame.draw.rect(screen, Palette.GOLD, r, 2, border_radius=12)

        self._draw_header(screen)
        self._draw_search(screen)
        self._draw_list(screen)
        self.scrollbar.render(screen)
        self._draw_buttons(screen)

    # ----------------------------------------------------------------
    def _draw_header(self, screen):
        r = self.rect
        title = FontBook.get(self.F_TITLE, bold=True).render(
            "Abrir animação", True, Palette.GOLD,
        )
        screen.blit(title, (r.x + self.PAD, r.y + 14))

        total = len(self.all_items)
        shown = len(self.filtered_items)
        if self.search_text:
            sub_text = f"{shown} de {total} animações"
        else:
            sub_text = f"{total} animações salvas"

        sub = FontBook.get(self.F_SUB).render(
            sub_text, True, (150, 165, 200),
        )
        sub_x = r.right - self.PAD - sub.get_width()
        screen.blit(sub, (sub_x, r.y + 22))

        pygame.draw.line(
            screen, (60, 76, 110),
            (r.x + 10, r.y + self.TITLE_H - 6),
            (r.right - 10, r.y + self.TITLE_H - 6),
            1,
        )

    # ----------------------------------------------------------------
    def _draw_search(self, screen):
        r = self._search_rect

        pygame.draw.rect(screen, (16, 20, 32), r, border_radius=8)
        border = Palette.GOLD if self.search_focused else (60, 76, 110)
        bw = 2 if self.search_focused else 1
        pygame.draw.rect(screen, border, r, bw, border_radius=8)

        # Ícone de lupa
        icon_x = r.x + 18
        icon_y = r.centery
        pygame.draw.circle(screen, (140, 160, 200),
                           (icon_x, icon_y), 6, 2)
        pygame.draw.line(
            screen, (140, 160, 200),
            (icon_x + 4, icon_y + 4),
            (icon_x + 9, icon_y + 9), 2,
        )

        # Texto ou placeholder
        tx = r.x + 38
        if self.search_text:
            color = (240, 240, 250)
            text = self.search_text
        else:
            color = (110, 120, 150)
            text = "Buscar por nome ou categoria..."

        font = FontBook.get(self.F_SEARCH)
        surf = font.render(text, True, color)
        screen.blit(surf, (tx, r.centery - surf.get_height() // 2))

        # Cursor (piscante)
        if self.search_focused and (pygame.time.get_ticks() // 500) % 2 == 0:
            cx = tx + surf.get_width() + 2
            pygame.draw.line(
                screen, Palette.GOLD,
                (cx, r.y + 9), (cx, r.bottom - 9), 2,
            )

        # Botão X (limpar busca)
        if self.search_text:
            x_btn = pygame.Rect(r.right - 32, r.centery - 11, 22, 22)
            hover = x_btn.collidepoint(pygame.mouse.get_pos())
            col = (240, 200, 100) if hover else (150, 160, 190)
            pygame.draw.line(screen, col,
                             (x_btn.x + 6, x_btn.y + 6),
                             (x_btn.right - 6, x_btn.bottom - 6), 2)
            pygame.draw.line(screen, col,
                             (x_btn.right - 6, x_btn.y + 6),
                             (x_btn.x + 6, x_btn.bottom - 6), 2)
            self._btn_clear_search = x_btn
        else:
            self._btn_clear_search = None

    # ----------------------------------------------------------------
    def _draw_list(self, screen):
        lr = self._list_rect
        pygame.draw.rect(screen, (14, 18, 30), lr, border_radius=8)
        pygame.draw.rect(screen, (60, 76, 110), lr, 1, border_radius=8)

        self._header_rects = []
        self._row_rects = []

        # Estado vazio
        if not self.filtered_items:
            if not self.all_items:
                msg = "Nenhuma animação salva em res/animations/"
                col = (170, 180, 210)
            else:
                msg = f'Nada encontrado para "{self.search_text}"'
                col = (210, 160, 160)
            t = FontBook.get(self.F_EMPTY).render(msg, True, col)
            screen.blit(t, (lr.centerx - t.get_width() // 2,
                            lr.centery - t.get_height() // 2))
            return

        old_clip = screen.get_clip()
        screen.set_clip(lr)

        start = self.scrollbar.scroll
        y = lr.y + 4
        max_draw = (lr.height // self.ITEM_ROW_H) + 4

        for vrow_idx in range(start, len(self._visual_rows)):
            if y > lr.bottom + self.ITEM_ROW_H:
                break
            row = self._visual_rows[vrow_idx]

            if row[0] == "header":
                _, cat, count = row
                h_rect = pygame.Rect(
                    lr.x + 4, y, lr.width - 8, self.HEADER_ROW_H,
                )
                self._header_rects.append((h_rect, cat, count))
                self._draw_category_header(screen, h_rect, cat, count)
                y += self.HEADER_ROW_H
            else:
                _, item_idx = row
                i_rect = pygame.Rect(
                    lr.x + 4, y + 1, lr.width - 8, self.ITEM_ROW_H - 2,
                )
                self._row_rects.append((i_rect, item_idx))
                self._draw_item_row(screen, i_rect, item_idx)
                y += self.ITEM_ROW_H

        screen.set_clip(old_clip)

    def _draw_category_header(self, screen, rect, cat, count):
        pygame.draw.rect(screen, (26, 32, 48), rect, border_radius=4)
        pygame.draw.rect(screen, Palette.GOLD,
                         (rect.x, rect.y, 3, rect.height))

        font = FontBook.get(self.F_HEADER, bold=True)
        t = font.render(cat.upper(), True, (255, 210, 110))
        screen.blit(t, (rect.x + 12, rect.centery - t.get_height() // 2))

        cnt = FontBook.get(self.F_HEADER).render(
            f"({count})", True, (130, 150, 185),
        )
        screen.blit(cnt, (rect.right - cnt.get_width() - 10,
                          rect.centery - cnt.get_height() // 2))

    def _draw_item_row(self, screen, rect, item_idx):
        _, name = self.filtered_items[item_idx]
        selected = (item_idx == self.selected)
        hovered = rect.collidepoint(pygame.mouse.get_pos())

        if selected:
            pygame.draw.rect(screen, (72, 108, 148), rect, border_radius=4)
            pygame.draw.rect(screen, Palette.GOLD, rect, 2, border_radius=4)
        elif hovered:
            pygame.draw.rect(screen, (44, 56, 84), rect, border_radius=4)

        col = Palette.GOLD if selected else (220, 228, 240)
        font = FontBook.get(self.F_ITEM, bold=selected)
        t = font.render(name, True, col)
        screen.blit(t, (rect.x + 16, rect.centery - t.get_height() // 2))

    # ----------------------------------------------------------------
    def _draw_buttons(self, screen):
        self._paint_button(screen, self._btn_cancel, "Cancelar",
                           danger=True)
        disabled = not self.filtered_items
        self._paint_button(screen, self._btn_open, "Abrir",
                           success=True, disabled=disabled)

    def _paint_button(self, screen, rect, label,
                      danger=False, success=False, disabled=False):
        hovered = (rect.collidepoint(pygame.mouse.get_pos())
                   and not disabled)

        if disabled:
            bg, border, txt_col = (40, 42, 55), (70, 76, 92), (130, 130, 140)
        elif danger:
            bg = (140, 55, 55) if hovered else (110, 45, 45)
            border, txt_col = (220, 90, 90), (255, 235, 235)
        elif success:
            bg = (60, 130, 75) if hovered else (45, 105, 60)
            border, txt_col = (120, 220, 130), (240, 255, 240)
        else:
            bg = (56, 72, 106) if hovered else (40, 52, 78)
            border, txt_col = (130, 170, 240), (240, 240, 250)

        pygame.draw.rect(screen, bg, rect, border_radius=7)
        pygame.draw.rect(screen, border, rect, 2, border_radius=7)

        font = FontBook.get(self.F_BTN, bold=True)
        t = font.render(label, True, txt_col)
        screen.blit(t, t.get_rect(center=rect.center))