# src/scenes/ui_editor_scene/editor/render_mixin.py
"""Mixin com todos os métodos _render_* e _paint_button do editor."""
import math
import pygame

from src.ui.theme import Palette, BUTTON_STYLES, FontBook
from src.ui.screen_loader import ScreenLoader
from src.scenes.ui.ui_editor_scene.editor import sections as S


DESIGN_W, DESIGN_H = 1280, 720
GUIDE_COLOR        = (90, 220, 255)
GUIDE_STRONG_COLOR = (255, 210, 90)


class EditorRenderMixin:

    # -----------------------------------------------------------------
    def _paint_button(self, screen, rect, label, style):
        st = BUTTON_STYLES.get(style, BUTTON_STYLES["primary"])
        hover = rect.collidepoint(pygame.mouse.get_pos())
        color = st["fill_hover"] if hover else st["fill"]
        pygame.draw.rect(screen, color, rect, border_radius=8)
        border = st["border_hover"] if hover else st["border"]
        pygame.draw.rect(screen, border, rect, 2, border_radius=8)
        txt = self._font(15, True).render(label, True, st["text"])
        screen.blit(txt, txt.get_rect(center=rect.center))

    # -----------------------------------------------------------------
    def _render_top(self, screen):
        pygame.draw.rect(screen, (24, 30, 48), self.top_rect)
        pygame.draw.rect(screen, (72, 88, 128), self.top_rect, 2)

        title = self._font(22, True).render("UI EDITOR", True, Palette.GOLD)
        screen.blit(title, (self.top_rect.x + 10,
                            self.top_rect.centery - title.get_height() // 2))

        defs = [
            ("novo",     "Novo",     "primary"),
            ("salvar",   "Salvar",   "success"),
            ("carregar", "Carregar", "gold"),
            ("preview",  "Preview",  "primary"),
            ("exportar", "Exportar", "ghost"),
            ("fechar",   "Fechar",   "danger"),
        ]
        y = self.top_rect.y + 12
        h = 32
        x = self.top_rect.x + 100
        gap = 6
        self._top_btn_rects = {}
        for key, label, style in defs:
            w = self._font(15, True).size(label)[0] + 24
            r = pygame.Rect(x, y, w, h)
            self._top_btn_rects[key] = r
            self._paint_button(screen, r, label, style)
            x += w + gap

        lbl = self._font(15).render("Nome:", True, Palette.TEXT_LIGHT)
        screen.blit(lbl, (self.name_field.rect.x - 50,
                          self.name_field.rect.centery -
                          lbl.get_height() // 2))
        self.name_field.render(screen)

        if self._tab_dd is None:
            self._rebuild_tab_dropdown()

        tab_lbl = self._font(15).render("Aba:", True, Palette.TEXT_LIGHT)
        tx = self.name_field.rect.right + 16
        screen.blit(tab_lbl, (tx,
                              self.name_field.rect.centery -
                              tab_lbl.get_height() // 2))
        tx += tab_lbl.get_width() + 6

        dd_w = 220
        self._tab_dd_rect = pygame.Rect(tx, self.name_field.rect.y,
                                        dd_w, self.name_field.rect.height)
        self._tab_dd.rect = self._tab_dd_rect
        self._tab_dd.render_closed(screen)

        if self._editing_tab:
            badge_x = self._tab_dd_rect.right + 8
            badge_w = min(260, self.top_rect.right - badge_x - 10)
            if badge_w > 120:
                badge = pygame.Rect(badge_x, self._tab_dd_rect.y + 4,
                                    badge_w, self._tab_dd_rect.height - 8)
                pygame.draw.rect(screen, (60, 80, 40), badge, border_radius=6)
                pygame.draw.rect(screen, Palette.GOLD, badge, 2,
                                 border_radius=6)
                label = f"Editando: {self._editing_tab_label()}"
                t = self._font(13, True).render(label, True, Palette.GOLD)
                max_w = badge.width - 16
                if t.get_width() > max_w:
                    while label and self._font(13, True).size(label)[0] > max_w:
                        label = label[:-1]
                    t = self._font(13, True).render(label + "...", True,
                                                    Palette.GOLD)
                screen.blit(t, (badge.x + 8,
                                badge.centery - t.get_height() // 2))

    # -----------------------------------------------------------------
    def _render_left(self, screen):
        pygame.draw.rect(screen, (24, 30, 48), self.left_rect)
        pygame.draw.rect(screen, (72, 88, 128), self.left_rect, 2)

        hdr = self._font(16, True).render("ADICIONAR", True, Palette.GOLD)
        screen.blit(hdr, (self.left_rect.x + 12, self.left_rect.y + 16))

        pad = 12
        gap = 6
        col_w = (self.left_rect.width - pad * 2 - gap) // 2
        row_h = 30
        y0 = self.left_rect.y + 44

        self._left_tool_rects = []
        for idx, (wtype, label, style) in enumerate(self.ADD_TYPES):
            row = idx // 2
            col = idx % 2
            x = self.left_rect.x + pad + col * (col_w + gap)
            yy = y0 + row * (row_h + gap)
            r = pygame.Rect(x, yy, col_w, row_h)
            self._left_tool_rects.append((r, wtype))
            self._paint_button(screen, r, f"+ {label}", style)

        tools_bottom = y0 + math.ceil(len(self.ADD_TYPES) / 2) * (row_h + gap) + 4

        # Hint do parent que vai herdar
        parent_hint = None
        if 0 <= self.selected_idx < len(self.widgets_data):
            p = self.widgets_data[self.selected_idx]
            if p.get("type") in ("panel", "tabpanel"):
                parent_hint = p.get("id")
        if parent_hint is None and self._editing_tab:
            parent_hint = self._editing_tab[0]
        if parent_hint:
            htxt = self._font(12, True).render(
                f"-> dentro de: {parent_hint[:18]}", True, Palette.GOLD)
            screen.blit(htxt, (self.left_rect.x + 12, tools_bottom - 14))

        actions_disp = [
            ("X  Remover",  "danger"),
            ("D  Duplicar", "success"),
            ("Subir (z)",   "gold"),
            ("Descer (z)",  "gold"),
            ("Desagrupar",  "ghost"),
            (f"Grid: {'ON' if self.show_grid else 'OFF'}", "ghost"),
        ]
        actions_handlers = [
            self._delete_selected,
            self._duplicate_selected,
            self._bring_forward,
            self._send_backward,
            self._unparent_selected,
            lambda: setattr(self, "show_grid", not self.show_grid),
        ]

        hdr2 = self._font(16, True).render("ACOES", True, Palette.GOLD)
        screen.blit(hdr2, (self.left_rect.x + 12, tools_bottom + 4))
        y_actions = tools_bottom + 28

        self._left_action_rects = []
        for i, (label, style) in enumerate(actions_disp):
            r = pygame.Rect(self.left_rect.x + 12,
                            y_actions + i * (row_h + gap),
                            self.left_rect.width - 24, row_h)
            self._left_action_rects.append((r, actions_handlers[i]))
            self._paint_button(screen, r, label, style)

        # Árvore
        list_y = y_actions + len(actions_disp) * (row_h + gap) + 12
        header = self._font(13, True).render("ARVORE / Z", True, Palette.GOLD)
        screen.blit(header, (self.left_rect.x + 12, list_y))
        list_y += 18

        tree = []
        self._collect_tree(self.widgets_data, None, tree, 0)
        max_rows = max(1, (self.left_rect.bottom - list_y - 130) // 18)
        for row, (i, w, depth) in enumerate(tree[:max_rows]):
            sel = (i in self.selected_indices)
            is_primary = (i == self.selected_idx)
            hidden = self._widget_hidden_by_filter(w)
            col = Palette.GOLD if is_primary else (
                (200, 220, 240) if sel else (180, 190, 210))
            prefix = ">" if is_primary else ("*" if sel else " ")
            if hidden:
                prefix = "~"
                col = (110, 120, 140)
            indent = "  " * depth
            txt = f"{prefix}{indent} z={int(w.get('z', 0)):>2}  {w.get('id', '?')[:12]}"
            s = self._font(12).render(txt, True, col)
            screen.blit(s, (self.left_rect.x + 12, list_y + row * 18))

        sel_txt = self._font(12).render(
            f"Sel: {len(self.selected_indices)}", True, (150, 190, 240))
        screen.blit(sel_txt, (self.left_rect.x + 12,
                              list_y + max_rows * 18 + 4))

        tips = [
            "Ctrl+Clique multi",
            "Marquee no canvas",
            "Del / Ctrl+D",
            "Setas movem",
            "Clique na aba = foco",
            "G grid",
            "Ctrl+S/O save/load",
            "ESC sair / limpar aba",
        ]
        ty = self.left_rect.bottom - len(tips) * 15 - 8
        for i, line in enumerate(tips):
            t = self._font(12).render(line, True, (120, 130, 150))
            screen.blit(t, (self.left_rect.x + 12, ty + i * 15))

    def _collect_tree(self, widgets, parent_id, out, depth):
        siblings = [(i, w) for i, w in enumerate(widgets)
                    if w.get("parent_id") == parent_id]
        siblings.sort(key=lambda t: int(t[1].get("z", 0)))
        for i, w in siblings:
            out.append((i, w, depth))
            self._collect_tree(widgets, w.get("id"), out, depth + 1)

    # -----------------------------------------------------------------
    def _render_canvas(self, screen):
        pygame.draw.rect(screen, (10, 14, 24), self.canvas_rect)
        pygame.draw.rect(screen, (48, 60, 90), self.canvas_rect, 2)

        dr = self._design_draw_rect
        self.design_surface.fill((28, 34, 52))

        if self.show_grid:
            step = 40
            gs = pygame.Surface((DESIGN_W, DESIGN_H), pygame.SRCALPHA)
            for x in range(0, DESIGN_W, step):
                pygame.draw.line(gs, (70, 84, 118, 120), (x, 0), (x, DESIGN_H))
            for y in range(0, DESIGN_H, step):
                pygame.draw.line(gs, (70, 84, 118, 120), (0, y), (DESIGN_W, y))
            pygame.draw.line(gs, (248, 176, 48, 160),
                             (DESIGN_W // 2, 0), (DESIGN_W // 2, DESIGN_H))
            pygame.draw.line(gs, (248, 176, 48, 160),
                             (0, DESIGN_H // 2), (DESIGN_W, DESIGN_H // 2))
            self.design_surface.blit(gs, (0, 0))

        roots = [w for w in self.widgets_data if not w.get("parent_id")]
        roots.sort(key=lambda w: int(w.get("z", 0)))
        for root in roots:
            self._render_tree(self.design_surface, root)

        scaled = pygame.transform.smoothscale(
            self.design_surface, (dr.width, dr.height))
        screen.blit(scaled, dr.topleft)

        for i in self.selected_indices:
            if not (0 <= i < len(self.widgets_data)):
                continue
            sel = self.widgets_data[i]
            if not self._widget_visible_in_canvas(sel):
                continue
            r = self._design_rect(sel)
            sr = self._design_to_screen_rect(r)
            is_primary = (i == self.selected_idx)
            color = Palette.GOLD if is_primary else (140, 200, 255)
            pygame.draw.rect(screen, color, sr, 2 if is_primary else 1)

        if len(self.selected_indices) == 1 and self.selected_idx >= 0:
            sel = self.widgets_data[self.selected_idx]
            if self._widget_visible_in_canvas(sel):
                r = self._design_rect(sel)
                sr = self._design_to_screen_rect(r)
                hs = 14
                hrect = pygame.Rect(sr.right - hs // 2, sr.bottom - hs // 2,
                                    hs, hs)
                pygame.draw.rect(screen, Palette.GOLD, hrect, border_radius=3)
                pygame.draw.rect(screen, (40, 30, 10), hrect, 2,
                                 border_radius=3)
                info = (f"z={int(sel.get('z', 0))}  "
                        f"({r.x:.0f},{r.y:.0f})  {r.w:.0f}x{r.h:.0f}")
                t = self._font(13).render(info, True, Palette.GOLD)
                screen.blit(t, (sr.x, max(dr.y, sr.y - 18)))

        if self._editing_tab:
            hint = self._font(13, True).render(
                f"Editando: {self._editing_tab_label()}  (ESC limpa o filtro)",
                True, (90, 220, 255))
            screen.blit(hint, (self.canvas_rect.x + 12,
                               self.canvas_rect.bottom - 22))

    def _render_tree(self, surface, wdata):
        if not self._widget_visible_in_canvas(wdata):
            return

        parent_content = self._get_parent_content_rect(wdata)
        widget = ScreenLoader._build_widget(wdata, parent_content, {})
        if widget is not None:
            widget._hover = False
            try:
                widget.render(surface)
            except Exception as e:
                print(f"[UI Editor] erro render {widget.id}: {e}")

        children = self._get_children_of(wdata.get("id"))
        children.sort(key=lambda w: int(w.get("z", 0)))
        for c in children:
            self._render_tree(surface, c)

    # -----------------------------------------------------------------
    def _render_guides(self, screen):
        if not (self._active_guides_v or self._active_guides_h):
            return
        dr = self._design_draw_rect
        s = self._canvas_scale

        for gx in self._active_guides_v:
            if gx in self._strong_guides_v:
                continue
            sx = dr.x + int(gx * s)
            pygame.draw.line(screen, GUIDE_COLOR,
                             (sx, dr.y), (sx, dr.bottom), 1)
            pygame.draw.circle(screen, GUIDE_COLOR, (sx, dr.y), 2)
            pygame.draw.circle(screen, GUIDE_COLOR, (sx, dr.bottom), 2)
        for gx in self._strong_guides_v:
            sx = dr.x + int(gx * s)
            pygame.draw.line(screen, GUIDE_STRONG_COLOR,
                             (sx, dr.y), (sx, dr.bottom), 2)
            pygame.draw.circle(screen, GUIDE_STRONG_COLOR, (sx, dr.y), 4)
            pygame.draw.circle(screen, GUIDE_STRONG_COLOR,
                               (sx, dr.bottom), 4)

        for gy in self._active_guides_h:
            if gy in self._strong_guides_h:
                continue
            sy = dr.y + int(gy * s)
            pygame.draw.line(screen, GUIDE_COLOR,
                             (dr.x, sy), (dr.right, sy), 1)
            pygame.draw.circle(screen, GUIDE_COLOR, (dr.x, sy), 2)
            pygame.draw.circle(screen, GUIDE_COLOR, (dr.right, sy), 2)
        for gy in self._strong_guides_h:
            sy = dr.y + int(gy * s)
            pygame.draw.line(screen, GUIDE_STRONG_COLOR,
                             (dr.x, sy), (dr.right, sy), 2)
            pygame.draw.circle(screen, GUIDE_STRONG_COLOR, (dr.x, sy), 4)
            pygame.draw.circle(screen, GUIDE_STRONG_COLOR, (dr.right, sy), 4)

    # -----------------------------------------------------------------
    def _render_marquee(self, screen):
        if self._marquee is None:
            return
        if self._marquee.width < 2 and self._marquee.height < 2:
            return
        surf = pygame.Surface(self._marquee.size, pygame.SRCALPHA)
        pygame.draw.rect(surf, (90, 220, 255, 40), surf.get_rect())
        pygame.draw.rect(surf, (90, 220, 255, 220), surf.get_rect(), 1)
        screen.blit(surf, self._marquee.topleft)

    # -----------------------------------------------------------------
    def _render_splitters(self, screen):
        for rect, which in ((self.split_l_rect, "left"),
                            (self.split_r_rect, "right")):
            if rect is None:
                continue
            is_hover = (self._hover_splitter == which or
                        self._dragging_splitter == which)
            bg = (60, 76, 110) if is_hover else (34, 42, 60)
            pygame.draw.rect(screen, bg, rect)
            cx = rect.centerx
            cy = rect.centery
            for dy in (-8, 0, 8):
                color = (200, 210, 240) if is_hover else (120, 135, 165)
                pygame.draw.line(screen, color,
                                 (cx - 1, cy + dy), (cx + 1, cy + dy), 1)

    # -----------------------------------------------------------------
    def _render_right(self, screen):
        pygame.draw.rect(screen, (24, 30, 48), self.right_rect)
        pygame.draw.rect(screen, (72, 88, 128), self.right_rect, 2)

        hdr = self._font(18, True).render("PROPRIEDADES", True, Palette.GOLD)
        screen.blit(hdr, (self.right_rect.x + 16, self.right_rect.y + 20))

        if len(self.selected_indices) > 1:
            info = f"Multi: {len(self.selected_indices)} selecionados"
            info_col = (150, 190, 240)
        elif 0 <= self.selected_idx < len(self.widgets_data):
            w = self.widgets_data[self.selected_idx]
            info = f"[{self.selected_idx + 1}/{len(self.widgets_data)}] {w['type']}"
            info_col = (160, 170, 190)
        else:
            info = "Selecione um widget"
            info_col = (160, 170, 190)
        si = self._font(13).render(info, True, info_col)
        screen.blit(si, (self.right_rect.x + 16, self.right_rect.y + 46))

        if self.right_max_scroll > 0:
            scroll_info = self._font(11).render(
                f"scroll {int(self.right_scroll)}/{int(self.right_max_scroll)}",
                True, (120, 130, 150))
            screen.blit(scroll_info,
                        (self.right_rect.right - scroll_info.get_width() - 14,
                         self.right_rect.y + 48))

        if len(self.selected_indices) != 1 or self.selected_idx < 0:
            pygame.draw.rect(screen, (18, 22, 34), self._right_footer_rect)
            pygame.draw.line(screen, (72, 88, 128),
                             self._right_footer_rect.topleft,
                             (self._right_footer_rect.right,
                              self._right_footer_rect.y), 1)
            self._paint_button(screen, self._apply_btn_rect, "Aplicar",
                               "success")
            return

        w = self.widgets_data[self.selected_idx]
        wtype = w.get("type", "button")
        sections = S.sections_for_type(wtype)

        old_clip = screen.get_clip()
        screen.set_clip(self._right_clip_rect)

        bg = pygame.Surface(self._right_clip_rect.size, pygame.SRCALPHA)
        bg.fill((18, 22, 34, 120))
        screen.blit(bg, self._right_clip_rect.topleft)

        self._section_header_rects = {}
        y = self._right_clip_rect.y - self.right_scroll

        for sid, title, keys in sections:
            open_ = self.sections_open.get(sid, True)
            hdr_r = pygame.Rect(self.right_rect.x + 8, y,
                                self.right_rect.width - 16, self.SECTION_H)
            if hdr_r.bottom > self._right_clip_rect.y and \
                    hdr_r.y < self._right_clip_rect.bottom:
                self._section_header_rects[sid] = hdr_r

            bg2 = (40, 48, 68) if open_ else (26, 32, 46)
            pygame.draw.rect(screen, bg2, hdr_r, border_radius=6)
            pygame.draw.rect(screen, (80, 96, 130), hdr_r, 1, border_radius=6)
            mk = self._font(14, True).render("-" if open_ else "+",
                                             True, Palette.GOLD)
            screen.blit(mk, (hdr_r.x + 8,
                             hdr_r.centery - mk.get_height() // 2))
            t = self._font(14, True).render(title, True, Palette.TEXT_LIGHT)
            screen.blit(t, (hdr_r.x + 24,
                            hdr_r.centery - t.get_height() // 2))
            y += self.SECTION_H

            if not open_:
                continue

            for k in keys:
                ftype = S.FIELD_TYPES.get(k, "text")
                label = S.FIELD_LABELS.get(k, k)

                if ftype == "list" and k in self.fields:
                    raw = self.fields[k].text
                    count = len([p for p in raw.split("|") if p.strip()])
                    label = f"{label} [{count}]"

                if y + self.ROW_H >= self._right_clip_rect.y and \
                        y <= self._right_clip_rect.bottom:
                    lb = self._font(13).render(label, True, (180, 190, 210))
                    screen.blit(lb, (self.right_rect.x + 12,
                                     y + 12 - lb.get_height() // 2))
                    if ftype in ("choice", "sound"):
                        d = self.dropdowns.get(k)
                        if d:
                            d.render_closed(screen)
                    else:
                        f = self.fields.get(k)
                        if f:
                            f.render(screen)
                y += self.ROW_H

        if self.right_max_scroll > 0:
            bar_x = self.right_rect.right - 12
            bar_top = self._right_clip_rect.y + 4
            bar_h = self._right_clip_rect.height - 8
            thumb_h = max(24, int(
                bar_h * self._right_clip_rect.height /
                max(1, self._right_clip_rect.height + self.right_max_scroll)))
            max_s = max(1, self.right_max_scroll)
            thumb_y = bar_top + int((bar_h - thumb_h) *
                                    self.right_scroll / max_s)
            pygame.draw.rect(screen, (35, 42, 60),
                             (bar_x, bar_top, 5, bar_h), border_radius=3)
            pygame.draw.rect(screen, (150, 170, 210),
                             (bar_x, thumb_y, 5, thumb_h), border_radius=3)

        screen.set_clip(old_clip)

        pygame.draw.rect(screen, (18, 22, 34), self._right_footer_rect)
        pygame.draw.line(screen, (72, 88, 128),
                         self._right_footer_rect.topleft,
                         (self._right_footer_rect.right,
                          self._right_footer_rect.y), 1)
        self._paint_button(screen, self._apply_btn_rect, "Aplicar", "success")

    # -----------------------------------------------------------------
    def _render_preview(self, screen):
        dr = self._design_draw_rect
        pygame.draw.rect(screen, (28, 34, 52), dr)
        for w in sorted(self._runtime_widgets,
                        key=lambda x: getattr(x, "z", 0)):
            if not self._is_widget_visible_preview(w):
                continue
            try:
                w.render(screen)
            except Exception as e:
                print(f"[Preview] erro: {e}")
        pygame.draw.rect(screen, Palette.GOLD, dr.inflate(4, 4), 3,
                         border_radius=6)

        banner = pygame.Rect(self.canvas_rect.x + 12,
                             self.canvas_rect.y + 12, 360, 34)
        pygame.draw.rect(screen, (16, 20, 32), banner, border_radius=8)
        pygame.draw.rect(screen, Palette.GOLD, banner, 2, border_radius=8)
        t = self._font(15, True).render("PREVIEW  -  ESC para sair",
                                        True, Palette.GOLD)
        screen.blit(t, (banner.x + 12,
                        banner.centery - t.get_height() // 2))

        hint = self._font(13).render(
            "Clique/hover nos widgets. Sons tocam. Abas funcionam.",
            True, (180, 190, 210))
        screen.blit(hint, (self.canvas_rect.x + 12, banner.bottom + 6))

    # -----------------------------------------------------------------
    def _render_status(self, screen):
        sm = self.screen_manager
        bar = pygame.Rect(sm.viewport_x,
                          sm.viewport_y + sm.viewport_height - self.BOT_H,
                          sm.viewport_width, self.BOT_H)
        pygame.draw.rect(screen, (14, 18, 30), bar)
        pygame.draw.line(screen, (72, 88, 128), bar.topleft,
                         (bar.right, bar.top), 1)
        txt = self._font(13).render(self.status_text, True, (180, 190, 210))
        screen.blit(txt, (bar.x + 10, bar.centery - txt.get_height() // 2))

        n = len(FontBook.available_fonts())
        ns = len(self._sound_names) - 1
        tab_hint = ""
        if self._editing_tab:
            tab_hint = f"  |  Aba: {self._editing_tab_label()}"
        info = self._font(12).render(
            f"Layouts: {len(ScreenLoader.list_layouts())}  |  "
            f"Fontes: {n}  |  Sons: {ns}  |  "
            f"Sel: {len(self.selected_indices)}{tab_hint}  |  "
            f"L:{self.left_w}px R:{self.right_w}px",
            True, (120, 130, 150))
        screen.blit(info, (bar.right - info.get_width() - 12,
                           bar.centery - info.get_height() // 2))