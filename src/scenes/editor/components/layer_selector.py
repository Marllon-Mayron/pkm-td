import pygame
from src.editor.layer_manager import LayerType


class LayerSelector:
    BUTTONS_HEIGHT = 54
    ITEM_HEIGHT = 26
    EYE_SIZE = 16
    TYPE_BTN_SIZE = 18
    DRAG_THRESHOLD = 5

    # Cores por tipo (brilhantes, para o botão de tipo)
    TYPE_COLORS = {
        "ground":     (120, 140, 180),
        "decoration": (100, 180, 100),
        "ceiling":    (200, 110, 110),
    }
    TYPE_ABBR = {
        "ground":     "C",
        "decoration": "D",
        "ceiling":    "T",
    }

    def __init__(self, x, y, width, height):
        self.rect = pygame.Rect(x, y, width, height)
        self.layers = []
        self.selected_layer = 0
        self.visible = True
        self.focused = False

        # Ação pendente que o editor deve processar
        # {'action': 'add'|'remove'|'toggle_visibility'|'move_layer'|'change_type', ...}
        self.pending_action = None

        # Resize
        self.resizing = False
        self.resize_margin = 10
        self.min_width = 180
        self.min_height = 240

        # Arrastar janela
        self.dragging = False
        self.drag_start_x = 0
        self.drag_start_y = 0

        # Scroll
        self.scroll_y = 0
        self.max_scroll = 0
        self.scroll_dragging = False
        self.scroll_drag_start_y = 0
        self.scroll_drag_start_scroll = 0

        # Hover
        self.hovered_button = None
        self.hovered_eye_index = -1       # índice REAL
        self.hovered_type_index = -1      # índice REAL

        # ===== REORDER (arrastar e soltar) =====
        self.reorder_potential = False     # botão pressionado numa linha
        self.reorder_dragging = False      # passou do threshold → arrastando
        self.reorder_from_display = -1
        self.reorder_from_real = -1
        self.reorder_target_display = -1   # posição-alvo (display)
        self.reorder_start_mouse_y = 0
        self.reorder_current_mouse_y = 0

        # Botões inferiores
        self.add_ground_rect = pygame.Rect(0, 0, 0, 0)
        self.add_deco_rect = pygame.Rect(0, 0, 0, 0)
        self.add_ceiling_rect = pygame.Rect(0, 0, 0, 0)
        self.remove_rect = pygame.Rect(0, 0, 0, 0)

        self._update_button_positions()

    # =========================================================
    # LAYOUT
    # =========================================================
    def _list_rect(self):
        return pygame.Rect(
            self.rect.x + 5,
            self.rect.y + 30,
            self.rect.width - 10,
            self.rect.height - 30 - self.BUTTONS_HEIGHT,
        )

    def _update_button_positions(self):
        r = self.rect
        m = 5
        btn_h = 22
        row1_y = r.bottom - self.BUTTONS_HEIGHT + 4
        row2_y = row1_y + btn_h + 4

        total_w = r.width - m * 2
        gap = 4
        bw = (total_w - gap * 2) // 3

        self.add_ground_rect = pygame.Rect(r.x + m, row1_y, bw, btn_h)
        self.add_deco_rect = pygame.Rect(r.x + m + bw + gap, row1_y, bw, btn_h)
        self.add_ceiling_rect = pygame.Rect(r.x + m + (bw + gap) * 2, row1_y, bw, btn_h)

        self.remove_rect = pygame.Rect(r.x + m, row2_y, total_w, btn_h)

        self._update_max_scroll()

    def _update_max_scroll(self):
        list_r = self._list_rect()
        total_h = len(self.layers) * self.ITEM_HEIGHT
        self.max_scroll = max(0, total_h - list_r.height)
        self.scroll_y = max(0, min(self.scroll_y, self.max_scroll))

    # =========================================================
    # API
    # =========================================================
    def set_layers(self, layers):
        self.layers = layers
        if self.selected_layer >= len(layers):
            self.selected_layer = max(0, len(layers) - 1)
        self._update_max_scroll()

    # =========================================================
    # HELPERS DE ÍNDICE (display <-> real, invertido)
    # =========================================================
    def _display_to_real(self, display_i):
        return len(self.layers) - 1 - display_i

    def _real_to_display(self, real_i):
        return len(self.layers) - 1 - real_i

    def _row_y(self, list_r, display_i):
        return list_r.y + display_i * self.ITEM_HEIGHT - self.scroll_y

    def _eye_rect_for_row(self, list_r, display_i):
        y = self._row_y(list_r, display_i)
        return pygame.Rect(list_r.right - 24, y + 4, self.EYE_SIZE, self.EYE_SIZE)

    def _type_rect_for_row(self, list_r, display_i):
        y = self._row_y(list_r, display_i)
        return pygame.Rect(list_r.right - 24 - self.TYPE_BTN_SIZE - 4,
                           y + 3, self.TYPE_BTN_SIZE, self.TYPE_BTN_SIZE)

    def _mouse_y_to_display_row(self, my):
        list_r = self._list_rect()
        local_y = my - list_r.y + self.scroll_y
        if local_y < 0:
            return 0
        row = int(local_y // self.ITEM_HEIGHT)
        if row >= len(self.layers):
            row = len(self.layers) - 1
        return max(0, row)

    # =========================================================
    # EVENTOS
    # =========================================================
    def handle_event(self, event):
        if not self.visible:
            return False

        mx, my = pygame.mouse.get_pos()
        self.focused = self.rect.collidepoint(mx, my)
        self._update_hover(mx, my)

        if event.type == pygame.MOUSEBUTTONDOWN:
            if event.button == 1:
                return self._handle_left_click(mx, my)
            elif event.button == 4 and self.rect.collidepoint(mx, my):
                self.scroll_y = max(0, self.scroll_y - 24)
                return True
            elif event.button == 5 and self.rect.collidepoint(mx, my):
                self.scroll_y = min(self.max_scroll, self.scroll_y + 24)
                return True

        elif event.type == pygame.MOUSEBUTTONUP:
            if event.button == 1:
                result = self._handle_left_up(mx, my)
                self.resizing = False
                self.dragging = False
                self.scroll_dragging = False
                return result

        elif event.type == pygame.MOUSEMOTION:
            return self._handle_motion(mx, my)

        return False

    def _update_hover(self, mx, my):
        self.hovered_button = None
        self.hovered_eye_index = -1
        self.hovered_type_index = -1

        for rect, name in (
            (self.add_ground_rect, "add_ground"),
            (self.add_deco_rect, "add_deco"),
            (self.add_ceiling_rect, "add_ceiling"),
            (self.remove_rect, "remove"),
        ):
            if rect.collidepoint(mx, my):
                self.hovered_button = name
                break

        list_r = self._list_rect()
        if list_r.collidepoint(mx, my):
            for display_i in range(len(self.layers)):
                eye = self._eye_rect_for_row(list_r, display_i)
                if eye.collidepoint(mx, my):
                    self.hovered_eye_index = self._display_to_real(display_i)
                    return
                tp = self._type_rect_for_row(list_r, display_i)
                if tp.collidepoint(mx, my):
                    self.hovered_type_index = self._display_to_real(display_i)
                    return

    # ---------------------------------------------------------
    # CLIQUE ESQUERDO
    # ---------------------------------------------------------
    def _handle_left_click(self, mx, my):
        # 1) Resize (canto inferior direito)
        if (self.rect.right - self.resize_margin <= mx <= self.rect.right + self.resize_margin and
                self.rect.bottom - self.resize_margin <= my <= self.rect.bottom + self.resize_margin):
            self.resizing = True
            return True

        # 2) Arrastar janela (título)
        title_rect = pygame.Rect(self.rect.x, self.rect.y, self.rect.width, 25)
        if title_rect.collidepoint(mx, my):
            self.dragging = True
            self.drag_start_x = mx - self.rect.x
            self.drag_start_y = my - self.rect.y
            return True

        # 3) Botões inferiores
        if self.add_ground_rect.collidepoint(mx, my):
            self.pending_action = {'action': 'add', 'type': LayerType.GROUND}
            return True
        if self.add_deco_rect.collidepoint(mx, my):
            self.pending_action = {'action': 'add', 'type': LayerType.DECORATION}
            return True
        if self.add_ceiling_rect.collidepoint(mx, my):
            self.pending_action = {'action': 'add', 'type': LayerType.CEILING}
            return True
        if self.remove_rect.collidepoint(mx, my):
            self.pending_action = {'action': 'remove', 'index': self.selected_layer}
            return True

        # 4) Linhas da lista
        list_r = self._list_rect()
        if list_r.collidepoint(mx, my):
            for display_i in range(len(self.layers)):
                # 4a) Olho → toggle visibilidade
                eye = self._eye_rect_for_row(list_r, display_i)
                if eye.collidepoint(mx, my):
                    real_i = self._display_to_real(display_i)
                    self.pending_action = {'action': 'toggle_visibility', 'index': real_i}
                    return True

                # 4b) Botão de tipo → troca o tipo (cicla C→D→T→C)
                tp = self._type_rect_for_row(list_r, display_i)
                if tp.collidepoint(mx, my):
                    real_i = self._display_to_real(display_i)
                    self.pending_action = {'action': 'change_type', 'index': real_i}
                    return True

            # 4c) Resto da linha → seleciona + inicia drag potencial
            display_i = self._mouse_y_to_display_row(my)
            if 0 <= display_i < len(self.layers):
                real_i = self._display_to_real(display_i)
                self.selected_layer = real_i
                # prepara possível drag de reordenação
                self.reorder_potential = True
                self.reorder_dragging = False
                self.reorder_from_display = display_i
                self.reorder_from_real = real_i
                self.reorder_target_display = display_i
                self.reorder_start_mouse_y = my
                self.reorder_current_mouse_y = my
                return True

        return False

    # ---------------------------------------------------------
    # SOLTAR
    # ---------------------------------------------------------
    def _handle_left_up(self, mx, my):
        # Commit do reorder, se estava arrastando
        if self.reorder_dragging:
            from_real = self.reorder_from_real
            to_real = self._display_to_real(self.reorder_target_display)
            if from_real != to_real and from_real >= 0 and to_real >= 0:
                self.pending_action = {
                    'action': 'move_layer',
                    'from': from_real,
                    'to': to_real,
                }
            self.reorder_potential = False
            self.reorder_dragging = False
            self.reorder_from_display = -1
            self.reorder_from_real = -1
            self.reorder_target_display = -1
            return True

        self.reorder_potential = False
        return False

    # ---------------------------------------------------------
    # MOVIMENTO (resize / drag janela / drag reorder)
    # ---------------------------------------------------------
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

        # Reorder: passou do threshold?
        if self.reorder_potential:
            if not self.reorder_dragging:
                if abs(my - self.reorder_start_mouse_y) >= self.DRAG_THRESHOLD:
                    self.reorder_dragging = True
            if self.reorder_dragging:
                self.reorder_current_mouse_y = my
                self.reorder_target_display = self._mouse_y_to_display_row(my)
                return True

        return False

    # =========================================================
    # RENDER
    # =========================================================
    def render(self, screen, current_layer_index):
        if not self.visible:
            return
        self._render_background(screen)
        self._render_title(screen)
        self._render_layers(screen, current_layer_index)
        self._render_reorder_overlay(screen)
        self._render_scrollbar(screen)
        self._render_buttons(screen)
        self._render_resize_handle(screen)

    def _render_background(self, screen):
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

    def _render_title(self, screen):
        font = pygame.font.Font(None, 20)
        title = font.render("LAYERS", True, (255, 255, 255))
        screen.blit(title, (self.rect.x + 10, self.rect.y + 5))

        count = font.render(f"({len(self.layers)})", True, (180, 180, 180))
        screen.blit(count, (self.rect.x + 72, self.rect.y + 5))

        hint_font = pygame.font.Font(None, 11)
        hint = hint_font.render("TOPO = frente  |  arraste p/ reordenar", True, (150, 150, 180))
        screen.blit(hint, (self.rect.right - hint.get_width() - 6, self.rect.y + 8))

    def _render_layers(self, screen, current_layer_index):
        # Cor de fundo por tipo
        type_colors = {
            "ground":     (80, 80, 90),
            "decoration": (70, 100, 70),
            "ceiling":    (100, 70, 70),
        }

        def type_str(lt):
            return lt.value if hasattr(lt, 'value') else lt

        list_r = self._list_rect()
        old_clip = screen.get_clip()
        screen.set_clip(list_r)

        font = pygame.font.Font(None, 14)
        n = len(self.layers)

        for display_i in range(n):
            real_i = self._display_to_real(display_i)
            layer = self.layers[real_i]

            y = self._row_y(list_r, display_i)
            if y + self.ITEM_HEIGHT < list_r.y or y > list_r.bottom:
                continue

            # Esconde a linha original enquanto está sendo arrastada
            if self.reorder_dragging and display_i == self.reorder_from_display:
                continue

            item_rect = pygame.Rect(list_r.x, y, list_r.width - 6, self.ITEM_HEIGHT - 2)

            ts = type_str(layer.layer_type)
            bg_color = type_colors.get(ts, (80, 80, 80))

            if not layer.visible:
                bg_color = tuple(int(c * 0.45) for c in bg_color)

            if real_i == current_layer_index:
                bg_color = tuple(min(255, c + 40) for c in bg_color)
                border_color = (255, 255, 255)
            else:
                border_color = (80, 80, 90)

            pygame.draw.rect(screen, bg_color, item_rect)
            pygame.draw.rect(screen, border_color, item_rect, 1)

            # Número da camada (index REAL, 0 = base)
            num_color = (255, 215, 0) if real_i == 0 else (220, 220, 220)
            screen.blit(font.render(str(real_i), True, num_color),
                        (item_rect.x + 4, item_rect.y + 5))

            # Nome (truncado)
            text_color = (255, 255, 255) if layer.visible else (130, 130, 130)
            name = layer.name[:8] + ("…" if len(layer.name) > 8 else "")
            screen.blit(font.render(name, True, text_color),
                        (item_rect.x + 22, item_rect.y + 5))

            # ===== BOTÃO DE TIPO (C/D/T) =====
            type_rect = self._type_rect_for_row(list_r, display_i)
            hovered_type = (self.hovered_type_index == real_i)
            base_color = self.TYPE_COLORS.get(ts, (120, 120, 120))
            if hovered_type:
                type_bg = tuple(min(255, c + 40) for c in base_color)
                type_border = (255, 255, 255)
            else:
                type_bg = base_color
                type_border = (40, 40, 50)
            pygame.draw.rect(screen, type_bg, type_rect, border_radius=3)
            pygame.draw.rect(screen, type_border, type_rect, 1, border_radius=3)
            abbr = self.TYPE_ABBR.get(ts, "?")
            abbr_surf = font.render(abbr, True, (255, 255, 255))
            screen.blit(abbr_surf, abbr_surf.get_rect(center=type_rect.center))

            # ===== OLHO =====
            eye_rect = self._eye_rect_for_row(list_r, display_i)
            hovered_eye = (self.hovered_eye_index == real_i)
            self._draw_eye(screen, eye_rect, layer.visible, hovered_eye)

        screen.set_clip(old_clip)

    def _draw_eye(self, screen, rect, visible, hovered=False):
        cx, cy = rect.center

        if hovered:
            pygame.draw.rect(screen, (80, 90, 115), rect.inflate(2, 2), border_radius=3)

        if visible:
            color = (140, 230, 140) if hovered else (110, 200, 110)
            pygame.draw.ellipse(screen, color, (cx - 7, cy - 4, 14, 8), 1)
            pygame.draw.circle(screen, color, (cx, cy), 2)
        else:
            color = (200, 110, 110) if hovered else (150, 80, 80)
            pygame.draw.ellipse(screen, color, (cx - 7, cy - 4, 14, 8), 1)
            pygame.draw.line(screen, color, (cx - 7, cy + 5), (cx + 7, cy - 5), 2)

    # ---------------------------------------------------------
    # OVERLAY DE REORDER (ghost + linha de inserção)
    # ---------------------------------------------------------
    def _render_reorder_overlay(self, screen):
        if not self.reorder_dragging:
            return

        list_r = self._list_rect()

        # === Linha de inserção ===
        target_y = list_r.y + self.reorder_target_display * self.ITEM_HEIGHT - self.scroll_y
        if self.reorder_current_mouse_y < self.reorder_start_mouse_y:
            # arrastando para CIMA → linha no topo da célula
            line_y = target_y
        else:
            # arrastando para BAIXO → linha na base da célula
            line_y = target_y + self.ITEM_HEIGHT

        line_y = max(list_r.y, min(list_r.bottom, line_y))

        old_clip = screen.get_clip()
        screen.set_clip(list_r)
        pygame.draw.line(screen, (255, 215, 0),
                         (list_r.x + 4, line_y),
                         (list_r.right - 4, line_y), 3)
        pygame.draw.circle(screen, (255, 215, 0), (list_r.x + 4, line_y), 4)
        pygame.draw.circle(screen, (255, 215, 0), (list_r.right - 4, line_y), 4)
        screen.set_clip(old_clip)

        # === Ghost da linha arrastada seguindo o mouse ===
        if 0 <= self.reorder_from_display < len(self.layers):
            layer = self.layers[self.reorder_from_real]
            ghost_y = self.reorder_current_mouse_y - self.ITEM_HEIGHT // 2
            ghost_rect = pygame.Rect(list_r.x, ghost_y,
                                     list_r.width - 6, self.ITEM_HEIGHT - 2)

            ghost = pygame.Surface((ghost_rect.width, ghost_rect.height), pygame.SRCALPHA)
            ghost.fill((100, 150, 220, 160))
            screen.blit(ghost, ghost_rect.topleft)
            pygame.draw.rect(screen, (255, 255, 255), ghost_rect, 2, border_radius=3)

            font = pygame.font.Font(None, 14)
            screen.blit(font.render(str(self.reorder_from_real), True, (255, 255, 255)),
                        (ghost_rect.x + 4, ghost_rect.y + 5))
            name = layer.name[:8] + ("…" if len(layer.name) > 8 else "")
            screen.blit(font.render(name, True, (255, 255, 255)),
                        (ghost_rect.x + 22, ghost_rect.y + 5))

    def _render_scrollbar(self, screen):
        if self.max_scroll <= 0:
            return
        list_r = self._list_rect()
        sb_h = max(20, int(list_r.height * (list_r.height / (list_r.height + self.max_scroll))))
        ratio = self.scroll_y / self.max_scroll if self.max_scroll > 0 else 0
        sb_y = list_r.y + ratio * (list_r.height - sb_h)

        pygame.draw.rect(screen, (60, 60, 70),
                         (list_r.right - 4, list_r.y, 3, list_r.height))
        pygame.draw.rect(screen, (150, 150, 160),
                         (list_r.right - 4, sb_y, 3, sb_h))

    def _render_buttons(self, screen):
        font = pygame.font.Font(None, 14)

        for rect, label, name, color in (
            (self.add_ground_rect, "+Chão", "add_ground", (60, 90, 60)),
            (self.add_deco_rect, "+Deco", "add_deco", (60, 90, 60)),
            (self.add_ceiling_rect, "+Teto", "add_ceiling", (60, 90, 60)),
        ):
            hovered = self.hovered_button == name
            bg = tuple(min(255, c + 30) for c in color) if hovered else color
            pygame.draw.rect(screen, bg, rect, border_radius=3)
            pygame.draw.rect(screen, (140, 160, 140), rect, 1, border_radius=3)
            txt = font.render(label, True, (255, 255, 255))
            screen.blit(txt, txt.get_rect(center=rect.center))

        can_remove = len(self.layers) > 1
        hovered = self.hovered_button == "remove"
        if not can_remove:
            bg, border, text_color = (50, 50, 55), (80, 80, 80), (110, 110, 110)
        elif hovered:
            bg, border, text_color = (150, 60, 60), (200, 90, 90), (255, 255, 255)
        else:
            bg, border, text_color = (110, 45, 45), (150, 70, 70), (255, 255, 255)

        pygame.draw.rect(screen, bg, self.remove_rect, border_radius=3)
        pygame.draw.rect(screen, border, self.remove_rect, 1, border_radius=3)
        label = f"- Remover ({self.selected_layer})" if can_remove else "- (mínimo 1)"
        txt = font.render(label, True, text_color)
        screen.blit(txt, txt.get_rect(center=self.remove_rect.center))

    def _render_resize_handle(self, screen):
        handle = pygame.Rect(self.rect.right - 15, self.rect.bottom - 15, 10, 10)
        pygame.draw.rect(screen, (150, 150, 150), handle)
        pygame.draw.line(screen, (200, 200, 200),
                         (handle.x + 2, handle.bottom - 2),
                         (handle.right - 2, handle.y + 2), 2)