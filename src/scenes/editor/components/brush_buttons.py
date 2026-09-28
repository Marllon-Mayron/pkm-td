# src/scenes/editor/components/brush_buttons.py

"""
Botões de ferramentas do editor.

Ferramentas:
    PINCEL   (B) — pinta 1 tile por clique (com SNAP opcional)
    BALDE    (V) — flood fill
    LINHA    (L) — clique/arraste (Bresenham)
    CÍRCULO  (O) — clique/arraste define centro+raio
    BORRACHA (E) — apaga com formato e tamanho ajustáveis
"""
import pygame


class BrushButtons:
    BRUSH_PENCIL = "pencil"
    BRUSH_BUCKET = "bucket"
    BRUSH_LINE = "line"
    BRUSH_CIRCLE = "circle"
    BRUSH_ERASER = "eraser"

    ERASER_SQUARE = "square"
    ERASER_CIRCLE = "circle"

    def __init__(self, x, y, width=200, height=240):
        self.rect = pygame.Rect(x, y, width, height)
        self.visible = True
        self.focused = False

        self.current_brush = self.BRUSH_PENCIL
        self.circle_filled = False

        # ===== SNAP (só afeta o pincel normal) =====
        self.snap_enabled = True

        # Borracha
        self.eraser_shape = self.ERASER_SQUARE
        self.eraser_size = 0
        self.eraser_max_size = 6

        # Arrastar / resize
        self.dragging = False
        self.drag_start_x = 0
        self.drag_start_y = 0
        self.resizing = False
        self.resize_margin = 10
        self.min_width = 190
        self.min_height = 220

        # Hover
        self.hovered_control = None

        # Tooltip
        self.show_tooltip = False
        self.tooltip_text = ""
        self.tooltip_timer = 0
        self.tooltip_mouse_pos = (0, 0)

        self._init_buttons()

    # =========================================================
    # LAYOUT
    # =========================================================
    def _init_buttons(self):
        bw = 80
        bh = 26
        gap = 8
        m = 10

        row1_y = 30
        self.pencil_rect = pygame.Rect(self.rect.x + m, self.rect.y + row1_y, bw, bh)
        self.bucket_rect = pygame.Rect(self.rect.x + m + bw + gap, self.rect.y + row1_y, bw, bh)

        row2_y = row1_y + bh + 6
        self.line_rect = pygame.Rect(self.rect.x + m, self.rect.y + row2_y, bw, bh)
        self.circle_rect = pygame.Rect(self.rect.x + m + bw + gap, self.rect.y + row2_y, bw, bh)

        row3_y = row2_y + bh + 6
        full_w = bw * 2 + gap
        self.eraser_rect = pygame.Rect(self.rect.x + m, self.rect.y + row3_y, full_w, bh)

        row4_y = row3_y + bh + 10
        self._init_dynamic_row(row4_y, m)

    def _init_dynamic_row(self, row4_y, m):
        # Preenchimento do círculo
        self.fill_checkbox = pygame.Rect(self.rect.x + m, self.rect.y + row4_y, 18, 18)
        self.fill_label_rect = pygame.Rect(self.rect.x + m + 24, self.rect.y + row4_y, 130, 18)

        # SNAP (pincel)
        self.snap_checkbox = pygame.Rect(self.rect.x + m, self.rect.y + row4_y, 18, 18)
        self.snap_label_rect = pygame.Rect(self.rect.x + m + 24, self.rect.y + row4_y, 150, 18)

        # Forma da borracha
        self.eraser_square_rect = pygame.Rect(self.rect.x + m, self.rect.y + row4_y, 24, 22)
        self.eraser_circle_rect = pygame.Rect(self.rect.x + m + 28, self.rect.y + row4_y, 24, 22)

        size_start_x = self.rect.x + m + 62
        self.eraser_size_label_x = size_start_x
        self.eraser_minus_rect = pygame.Rect(size_start_x + 34, self.rect.y + row4_y, 18, 22)
        self.eraser_value_rect = pygame.Rect(size_start_x + 54, self.rect.y + row4_y, 22, 22)
        self.eraser_plus_rect  = pygame.Rect(size_start_x + 78, self.rect.y + row4_y, 18, 22)

    def _update_button_positions(self):
        bw = 80
        bh = 26
        gap = 8
        m = 10

        row1_y = 30
        self.pencil_rect.topleft = (self.rect.x + m, self.rect.y + row1_y)
        self.bucket_rect.topleft = (self.rect.x + m + bw + gap, self.rect.y + row1_y)

        row2_y = row1_y + bh + 6
        self.line_rect.topleft = (self.rect.x + m, self.rect.y + row2_y)
        self.circle_rect.topleft = (self.rect.x + m + bw + gap, self.rect.y + row2_y)

        row3_y = row2_y + bh + 6
        self.eraser_rect.topleft = (self.rect.x + m, self.rect.y + row3_y)
        self.eraser_rect.width = bw * 2 + gap

        row4_y = row3_y + bh + 10
        self._init_dynamic_row(row4_y, m)

    # =========================================================
    # EVENTOS
    # =========================================================
    def handle_event(self, event):
        if not self.visible:
            return False
        mx, my = pygame.mouse.get_pos()
        self.focused = self.rect.collidepoint(mx, my)
        self._update_hover(mx, my)

        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            return self._handle_left_click(mx, my)
        elif event.type == pygame.MOUSEBUTTONUP and event.button == 1:
            self.dragging = False
            self.resizing = False
        elif event.type == pygame.MOUSEMOTION:
            return self._handle_motion(mx, my)
        elif event.type == pygame.KEYDOWN and self.focused:
            return self._handle_keydown(event)
        return False

    def _update_hover(self, mx, my):
        self.hovered_control = None
        rects = [
            (self.pencil_rect, "pencil"),
            (self.bucket_rect, "bucket"),
            (self.line_rect, "line"),
            (self.circle_rect, "circle"),
            (self.eraser_rect, "eraser"),
        ]
        if self.current_brush == self.BRUSH_CIRCLE:
            rects.append((self.fill_checkbox, "fill"))
        if self.current_brush == self.BRUSH_PENCIL:
            rects.append((self.snap_checkbox, "snap"))
        if self.current_brush == self.BRUSH_ERASER:
            rects += [
                (self.eraser_square_rect, "eraser_square"),
                (self.eraser_circle_rect, "eraser_circle"),
                (self.eraser_minus_rect, "eraser_minus"),
                (self.eraser_plus_rect, "eraser_plus"),
            ]
        for rect, name in rects:
            if rect.collidepoint(mx, my):
                self.hovered_control = name
                return

    def _handle_left_click(self, mx, my):
        if (self.rect.right - self.resize_margin <= mx <= self.rect.right + self.resize_margin and
                self.rect.bottom - self.resize_margin <= my <= self.rect.bottom + self.resize_margin):
            self.resizing = True
            return True

        title_rect = pygame.Rect(self.rect.x, self.rect.y, self.rect.width, 25)
        if title_rect.collidepoint(mx, my):
            self.dragging = True
            self.drag_start_x = mx - self.rect.x
            self.drag_start_y = my - self.rect.y
            return True

        if self.pencil_rect.collidepoint(mx, my):
            self.current_brush = self.BRUSH_PENCIL; return True
        if self.bucket_rect.collidepoint(mx, my):
            self.current_brush = self.BRUSH_BUCKET; return True
        if self.line_rect.collidepoint(mx, my):
            self.current_brush = self.BRUSH_LINE; return True
        if self.circle_rect.collidepoint(mx, my):
            self.current_brush = self.BRUSH_CIRCLE; return True
        if self.eraser_rect.collidepoint(mx, my):
            self.current_brush = self.BRUSH_ERASER; return True

        # Círculo fill
        if self.current_brush == self.BRUSH_CIRCLE:
            if self.fill_checkbox.collidepoint(mx, my):
                self.circle_filled = not self.circle_filled
                return True

        # Pincel — SNAP
        if self.current_brush == self.BRUSH_PENCIL:
            if self.snap_checkbox.collidepoint(mx, my):
                self.snap_enabled = not self.snap_enabled
                print(f"[BrushButtons] Snap {'ON' if self.snap_enabled else 'OFF'}")
                return True

        # Borracha
        if self.current_brush == self.BRUSH_ERASER:
            if self.eraser_square_rect.collidepoint(mx, my):
                self.eraser_shape = self.ERASER_SQUARE; return True
            if self.eraser_circle_rect.collidepoint(mx, my):
                self.eraser_shape = self.ERASER_CIRCLE; return True
            if self.eraser_minus_rect.collidepoint(mx, my):
                self.eraser_size = max(0, self.eraser_size - 1); return True
            if self.eraser_plus_rect.collidepoint(mx, my):
                self.eraser_size = min(self.eraser_max_size, self.eraser_size + 1); return True

        return False

    def _handle_motion(self, mx, my):
        if self.resizing:
            self.rect.width = max(self.min_width, mx - self.rect.x)
            self.rect.height = max(self.min_height, my - self.rect.y)
            self._update_button_positions()
            return True
        if self.dragging:
            self.rect.x = mx - self.drag_start_x
            self.rect.y = my - self.drag_start_y
            self._update_button_positions()
            return True
        return False

    def _handle_keydown(self, event):
        # Atalhos de ferramenta
        if event.key == pygame.K_b:
            self.current_brush = self.BRUSH_PENCIL; return True
        if event.key == pygame.K_v:
            self.current_brush = self.BRUSH_BUCKET; return True
        if event.key == pygame.K_l:
            self.current_brush = self.BRUSH_LINE; return True
        if event.key == pygame.K_o:
            self.current_brush = self.BRUSH_CIRCLE; return True
        if event.key == pygame.K_e:
            self.current_brush = self.BRUSH_ERASER; return True

        # Shift = toggle snap temporário
        if event.key == pygame.K_LSHIFT or event.key == pygame.K_RSHIFT:
            self.snap_enabled = not self.snap_enabled
            print(f"[BrushButtons] Snap (Shift) {'ON' if self.snap_enabled else 'OFF'}")
            return True
        return False

    # =========================================================
    # API
    # =========================================================
    def get_current_brush(self):
        return self.current_brush

    def is_circle_filled(self):
        return self.circle_filled

    def is_snap_enabled(self):
        return self.snap_enabled

    def is_shape_tool(self):
        return self.current_brush in (self.BRUSH_LINE, self.BRUSH_CIRCLE)

    def is_eraser(self):
        return self.current_brush == self.BRUSH_ERASER

    def get_eraser_shape(self):
        return self.eraser_shape

    def get_eraser_size(self):
        return self.eraser_size

    # =========================================================
    # RENDER
    # =========================================================
    def render(self, screen, font_small):
        if not self.visible:
            return

        shadow = self.rect.copy()
        shadow.x += 3
        shadow.y += 3
        pygame.draw.rect(screen, (20, 20, 30), shadow, border_radius=8)

        if self.focused:
            bg, border = (60, 60, 75), (140, 140, 160)
        else:
            bg, border = (45, 45, 55), (90, 90, 100)
        pygame.draw.rect(screen, bg, self.rect, border_radius=8)
        pygame.draw.rect(screen, border, self.rect, 2, border_radius=8)

        title_bar = pygame.Rect(self.rect.x, self.rect.y, self.rect.width, 25)
        pygame.draw.rect(screen, (70, 70, 85), title_bar,
                         border_top_left_radius=8, border_top_right_radius=8)
        screen.blit(font_small.render("FERRAMENTAS", True, (255, 255, 255)),
                    (self.rect.x + 10, self.rect.y + 5))

        handle = pygame.Rect(self.rect.right - 15, self.rect.bottom - 15, 10, 10)
        pygame.draw.rect(screen, (150, 150, 150), handle)
        pygame.draw.line(screen, (200, 200, 200),
                         (handle.x + 2, handle.bottom - 2),
                         (handle.right - 2, handle.y + 2), 2)

        # Ferramentas
        self._render_tool_button(screen, font_small, self.pencil_rect, "PINCEL",
                                 self.BRUSH_PENCIL, "pencil")
        self._render_tool_button(screen, font_small, self.bucket_rect, "BALDE",
                                 self.BRUSH_BUCKET, "bucket")
        self._render_tool_button(screen, font_small, self.line_rect, "LINHA",
                                 self.BRUSH_LINE, "line")
        self._render_tool_button(screen, font_small, self.circle_rect, "CIRCULO",
                                 self.BRUSH_CIRCLE, "circle")
        self._render_tool_button(screen, font_small, self.eraser_rect, "BORRACHA",
                                 self.BRUSH_ERASER, "eraser")

        # Linha dinâmica
        if self.current_brush == self.BRUSH_PENCIL:
            self._render_snap_control(screen, font_small)
        elif self.current_brush == self.BRUSH_CIRCLE:
            self._render_fill_checkbox(screen, font_small)
        elif self.current_brush == self.BRUSH_ERASER:
            self._render_eraser_controls(screen, font_small)

    def _render_tool_button(self, screen, font, rect, label, brush_id, hover_name):
        active = self.current_brush == brush_id
        hovered = self.hovered_control == hover_name
        if active:
            color, border_color = (100, 150, 200), (180, 210, 255)
        elif hovered:
            color, border_color = (70, 80, 100), (120, 130, 150)
        else:
            color, border_color = (60, 60, 70), (100, 100, 110)
        pygame.draw.rect(screen, color, rect, border_radius=3)
        pygame.draw.rect(screen, border_color, rect, 1, border_radius=3)
        txt = font.render(label, True, (255, 255, 255))
        screen.blit(txt, txt.get_rect(center=rect.center))

    def _render_snap_control(self, screen, font_small):
        box = self.snap_checkbox
        if self.snap_enabled:
            pygame.draw.rect(screen, (70, 120, 190), box, border_radius=4)
            pygame.draw.rect(screen, (150, 200, 255), box, 1, border_radius=4)
            pygame.draw.line(screen, (255, 255, 255),
                             (box.x + 4, box.y + 9), (box.x + 7, box.y + 13), 2)
            pygame.draw.line(screen, (255, 255, 255),
                             (box.x + 7, box.y + 13), (box.x + 13, box.y + 5), 2)
        else:
            pygame.draw.rect(screen, (60, 50, 40), box, border_radius=4)
            pygame.draw.rect(screen, (180, 140, 90), box, 1, border_radius=4)

        label_color = (220, 220, 220) if self.snap_enabled else (255, 200, 120)
        screen.blit(font_small.render("Snap na grade", True, label_color),
                    (self.snap_label_rect.x, self.snap_label_rect.y))

        # Dica extra quando snap OFF
        if not self.snap_enabled:
            tip = font_small.render("(posicionamento livre)", True, (180, 180, 200))
            screen.blit(tip, (self.snap_label_rect.x, self.snap_label_rect.y + 14))

    def _render_fill_checkbox(self, screen, font_small):
        box = self.fill_checkbox
        if self.circle_filled:
            pygame.draw.rect(screen, (70, 120, 190), box, border_radius=4)
            pygame.draw.rect(screen, (150, 200, 255), box, 1, border_radius=4)
            pygame.draw.line(screen, (255, 255, 255),
                             (box.x + 4, box.y + 9), (box.x + 7, box.y + 13), 2)
            pygame.draw.line(screen, (255, 255, 255),
                             (box.x + 7, box.y + 13), (box.x + 13, box.y + 5), 2)
        else:
            pygame.draw.rect(screen, (40, 45, 60), box, border_radius=4)
            pygame.draw.rect(screen, (120, 120, 130), box, 1, border_radius=4)
        label = font_small.render("Fill (preencher)", True, (220, 220, 220))
        screen.blit(label, (self.fill_label_rect.x, self.fill_label_rect.y))

    def _render_eraser_controls(self, screen, font_small):
        sq, ci = self.eraser_square_rect, self.eraser_circle_rect

        active = self.eraser_shape == self.ERASER_SQUARE
        hovered = self.hovered_control == "eraser_square"
        color = (100, 150, 200) if active else ((70, 80, 100) if hovered else (50, 55, 70))
        pygame.draw.rect(screen, color, sq, border_radius=3)
        pygame.draw.rect(screen, (150, 160, 180), sq, 1, border_radius=3)
        pygame.draw.rect(screen, (255, 255, 255), (sq.x + 6, sq.y + 6, 12, 12), 2)

        active = self.eraser_shape == self.ERASER_CIRCLE
        hovered = self.hovered_control == "eraser_circle"
        color = (100, 150, 200) if active else ((70, 80, 100) if hovered else (50, 55, 70))
        pygame.draw.rect(screen, color, ci, border_radius=3)
        pygame.draw.rect(screen, (150, 160, 180), ci, 1, border_radius=3)
        pygame.draw.circle(screen, (255, 255, 255), (ci.x + 12, ci.y + 11), 7, 2)

        lbl = font_small.render("Size:", True, (200, 200, 200))
        screen.blit(lbl, (self.eraser_size_label_x, self.eraser_minus_rect.y + 3))

        minus = self.eraser_minus_rect
        hovered = self.hovered_control == "eraser_minus"
        color = (70, 85, 110) if hovered else (40, 45, 60)
        pygame.draw.rect(screen, color, minus, border_radius=3)
        pygame.draw.rect(screen, (120, 125, 140), minus, 1, border_radius=3)
        t = font_small.render("-", True, (255, 255, 255))
        screen.blit(t, t.get_rect(center=minus.center))

        val = self.eraser_value_rect
        pygame.draw.rect(screen, (30, 34, 44), val, border_radius=3)
        pygame.draw.rect(screen, (90, 95, 110), val, 1, border_radius=3)
        t = font_small.render(str(self.eraser_size * 2 + 1), True, (255, 255, 255))
        screen.blit(t, t.get_rect(center=val.center))

        plus = self.eraser_plus_rect
        hovered = self.hovered_control == "eraser_plus"
        color = (70, 85, 110) if hovered else (40, 45, 60)
        pygame.draw.rect(screen, color, plus, border_radius=3)
        pygame.draw.rect(screen, (120, 125, 140), plus, 1, border_radius=3)
        t = font_small.render("+", True, (255, 255, 255))
        screen.blit(t, t.get_rect(center=plus.center))