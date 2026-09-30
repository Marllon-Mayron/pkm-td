# src/scenes/editor/components/structure_selection_panel.py

"""
Painel flutuante que gerencia a seleção de uma nova estrutura customizada.
"""
import pygame


class StructureSelectionPanel:
    COLORS = {
        'bg':            (40, 40, 50),
        'bg_light':      (55, 55, 68),
        'bg_dark':       (30, 30, 40),
        'border':        (255, 215, 0),
        'border_light':  (85, 85, 100),
        'text':          (240, 240, 245),
        'text_dim':      (190, 190, 200),
        'text_muted':    (140, 140, 150),
        'accent':        (80, 110, 160),
        'accent_hover':  (105, 135, 190),
        'success':       (0, 130, 0),
        'success_hover': (0, 165, 0),
        'danger':        (140, 0, 0),
        'danger_hover':  (175, 0, 0),
        'warn':          (150, 120, 0),
        'warn_hover':    (185, 150, 0),
        'input_bg':      (50, 50, 62),
        'input_active':  (100, 150, 255),
        'add':           (60, 160, 60),
        'add_hover':     (80, 200, 80),
        'remove':        (170, 60, 60),
        'remove_hover':  (210, 80, 80),
    }

    def __init__(self, x, y, editor_scene):
        self.rect = pygame.Rect(x, y, 460, 168)
        self.visible = True
        self.editor = editor_scene

        # Estado
        self.tool = "rect"          # "rect" | "circle"
        self.operation = "add"      # "add" | "remove"
        self.filled = True          # círculo preenchido
        self.name_input = ""
        self.active_input = "name"

        # Arraste
        self.dragging = False
        self.drag_off = (0, 0)

        self.hovered = None

        # Fonts
        self.font_title = pygame.font.Font(None, 22)
        self.font       = pygame.font.Font(None, 18)
        self.font_small = pygame.font.Font(None, 15)

        self._init_layout()

    # =========================================================
    # LAYOUT
    # =========================================================
    def _init_layout(self):
        x, y, w, h = self.rect

        # Título (drag)
        self.title_rect = pygame.Rect(x, y, w, 26)
        self.close_btn  = pygame.Rect(x + w - 26, y + 3, 20, 20)

        # Linha 1: nome
        lbl_y = y + 34
        self.name_label = pygame.Rect(x + 12, lbl_y, 50, 22)
        self.name_input_rect = pygame.Rect(x + 62, lbl_y, w - 74, 22)

        # Linha 2: ferramenta + modo
        lbl2_y = y + 64
        self.tool_label = pygame.Rect(x + 12, lbl2_y, 70, 24)
        self.rect_btn   = pygame.Rect(x + 82, lbl2_y, 90, 24)
        self.circle_btn = pygame.Rect(x + 176, lbl2_y, 80, 24)

        self.mode_label = pygame.Rect(x + 268, lbl2_y, 40, 24)
        self.add_btn    = pygame.Rect(x + 306, lbl2_y, 68, 24)
        self.rem_btn    = pygame.Rect(x + 378, lbl2_y, 68, 24)

        # Linha 3: filled + limpar + salvar
        lbl3_y = y + 96
        self.filled_box = pygame.Rect(x + 12, lbl3_y + 3, 16, 16)
        self.filled_lbl = pygame.Rect(x + 32, lbl3_y, 110, 22)

        self.clear_btn  = pygame.Rect(x + 150, lbl3_y, 78, 24)
        self.save_btn   = pygame.Rect(x + 236, lbl3_y, 100, 24)
        self.cancel_btn = pygame.Rect(x + 344, lbl3_y, 102, 24)

        # Info
        self.info_rect = pygame.Rect(x + 12, y + 132, w - 24, 24)

    def _update_positions(self):
        # só recalcula rects baseados em self.rect (após drag)
        self._init_layout()

    # =========================================================
    # EVENTOS
    # =========================================================
    def handle_event(self, event):
        if not self.visible:
            return None

        mp = pygame.mouse.get_pos()

        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            return self._handle_click(mp)

        if event.type == pygame.MOUSEBUTTONUP and event.button == 1:
            self.dragging = False
            return None

        if event.type == pygame.MOUSEMOTION:
            if self.dragging:
                self.rect.x = mp[0] - self.drag_off[0]
                self.rect.y = mp[1] - self.drag_off[1]
                self._update_positions()
                return None
            self._update_hover(mp)
            return None

        if event.type == pygame.KEYDOWN and self.active_input == "name":
            if event.key == pygame.K_BACKSPACE:
                self.name_input = self.name_input[:-1]
                return None
            elif event.key == pygame.K_RETURN:
                self.active_input = None
                return None
            elif event.unicode.isprintable():
                self.name_input += event.unicode
                return None

        return None

    def _update_hover(self, mp):
        self.hovered = None
        for rect, name in (
            (self.close_btn, "close"),
            (self.rect_btn, "rect"),
            (self.circle_btn, "circle"),
            (self.add_btn, "add"),
            (self.rem_btn, "remove"),
            (self.filled_box, "filled"),
            (self.clear_btn, "clear"),
            (self.save_btn, "save"),
            (self.cancel_btn, "cancel"),
        ):
            if rect.collidepoint(mp):
                self.hovered = name
                return

    def _handle_click(self, mp):
        # Arrastar pelo título
        if self.title_rect.collidepoint(mp) and not self.close_btn.collidepoint(mp):
            self.dragging = True
            self.drag_off = (mp[0] - self.rect.x, mp[1] - self.rect.y)
            return None

        if self.close_btn.collidepoint(mp):
            return "cancel"

        if self.name_input_rect.collidepoint(mp):
            self.active_input = "name"
            return None

        # Ferramenta
        if self.rect_btn.collidepoint(mp):
            self.tool = "rect"; return None
        if self.circle_btn.collidepoint(mp):
            self.tool = "circle"; return None

        # Modo
        if self.add_btn.collidepoint(mp):
            self.operation = "add"; return None
        if self.rem_btn.collidepoint(mp):
            self.operation = "remove"; return None

        # Filled
        if self.filled_box.collidepoint(mp) or self.filled_lbl.collidepoint(mp):
            self.filled = not self.filled
            return None

        # Ações
        if self.clear_btn.collidepoint(mp):
            return "clear"
        if self.save_btn.collidepoint(mp):
            return "save"
        if self.cancel_btn.collidepoint(mp):
            return "cancel"

        return None

    # =========================================================
    # RENDER
    # =========================================================
    def render(self, screen):
        if not self.visible:
            return

        # Sombra
        shadow = self.rect.copy()
        shadow.x += 3
        shadow.y += 3
        pygame.draw.rect(screen, (10, 10, 15), shadow, border_radius=10)

        pygame.draw.rect(screen, self.COLORS['bg'], self.rect, border_radius=10)
        pygame.draw.rect(screen, self.COLORS['border'], self.rect, 2, border_radius=10)

        # Título
        pygame.draw.rect(screen, self.COLORS['bg_light'], self.title_rect,
                         border_top_left_radius=10, border_top_right_radius=10)
        t = self.font_title.render("Seleção de Estrutura", True, self.COLORS['border'])
        screen.blit(t, (self.rect.x + 12, self.rect.y + 5))

        # Close
        cv = self.COLORS['danger_hover'] if self.hovered == "close" else self.COLORS['danger']
        pygame.draw.rect(screen, cv, self.close_btn, border_radius=4)
        pygame.draw.line(screen, (255, 255, 255),
                         (self.close_btn.x + 5, self.close_btn.y + 5),
                         (self.close_btn.right - 5, self.close_btn.bottom - 5), 2)
        pygame.draw.line(screen, (255, 255, 255),
                         (self.close_btn.right - 5, self.close_btn.y + 5),
                         (self.close_btn.x + 5, self.close_btn.bottom - 5), 2)

        # ===== Nome =====
        screen.blit(self.font_small.render("Nome:", True, self.COLORS['text_dim']),
                    (self.name_label.x, self.name_label.y + 4))
        border = self.COLORS['input_active'] if self.active_input == "name" else self.COLORS['border_light']
        pygame.draw.rect(screen, self.COLORS['input_bg'], self.name_input_rect, border_radius=4)
        pygame.draw.rect(screen, border, self.name_input_rect, 1, border_radius=4)
        name_display = self.name_input if self.name_input else "estrutura_nova"
        name_color = self.COLORS['text'] if self.name_input else self.COLORS['text_muted']
        screen.blit(self.font_small.render(name_display, True, name_color),
                    (self.name_input_rect.x + 5, self.name_input_rect.y + 4))

        # ===== Ferramenta =====
        screen.blit(self.font_small.render("Ferramenta:", True, self.COLORS['text_dim']),
                    (self.tool_label.x, self.tool_label.y + 4))

        self._render_toggle(screen, self.rect_btn, "Retângulo", self.tool == "rect", "rect")
        self._render_toggle(screen, self.circle_btn, "Círculo", self.tool == "circle", "circle")

        # ===== Modo =====
        screen.blit(self.font_small.render("Modo:", True, self.COLORS['text_dim']),
                    (self.mode_label.x, self.mode_label.y + 4))

        self._render_toggle(screen, self.add_btn, "+ Add", self.operation == "add", "add",
                            active_color=self.COLORS['add'])
        self._render_toggle(screen, self.rem_btn, "- Rem", self.operation == "remove", "remove",
                            active_color=self.COLORS['remove'])

        # ===== Filled =====
        box = self.filled_box
        if self.filled:
            pygame.draw.rect(screen, self.COLORS['accent'], box, border_radius=4)
            pygame.draw.line(screen, (255, 255, 255),
                             (box.x + 3, box.y + 8), (box.x + 6, box.y + 11), 2)
            pygame.draw.line(screen, (255, 255, 255),
                             (box.x + 6, box.y + 11), (box.x + 12, box.y + 4), 2)
        else:
            pygame.draw.rect(screen, self.COLORS['input_bg'], box, border_radius=4)
        pygame.draw.rect(screen, self.COLORS['border_light'], box, 1, border_radius=4)
        fill_txt = "Preenchido (só círculo)" if self.tool == "circle" else "Preenchido"
        fill_color = self.COLORS['text_dim'] if self.tool == "circle" else self.COLORS['text_muted']
        screen.blit(self.font_small.render(fill_txt, True, fill_color),
                    (self.filled_lbl.x, self.filled_lbl.y + 3))

        # ===== Botões de ação =====
        self._render_action_button(screen, self.clear_btn, "Limpar",
                                   color_key="warn", hover_key="warn_hover", name="clear")
        self._render_action_button(screen, self.save_btn, "Salvar Estrutura",
                                   color_key="success", hover_key="success_hover", name="save")
        self._render_action_button(screen, self.cancel_btn, "Cancelar",
                                   color_key="danger", hover_key="danger_hover", name="cancel")

        # ===== Info =====
        mask = getattr(self.editor, 'structure_selection_mask', set())
        n = len(mask)
        bbox = self.editor.structure_manager.get_selection_bbox(mask)
        bbox_txt = f"{bbox[2] - bbox[0] + 1}x{bbox[3] - bbox[1] + 1}" if bbox else "-"

        # Camadas visíveis que serão salvas
        vis_count = sum(1 for l in self.editor.layer_manager.layers
                        if getattr(l, 'visible', True))

        info = f"Selecionados: {n} tile(s) | BBox: {bbox_txt} | Camadas visíveis: {vis_count}"
        screen.blit(self.font_small.render(info, True, self.COLORS['text_dim']),
                    (self.info_rect.x, self.info_rect.y + 4))

        hint = "Botão direito cancela arraste | ESC cancela tudo"
        screen.blit(self.font_small.render(hint, True, self.COLORS['text_muted']),
                    (self.info_rect.x, self.info_rect.y + 18))

    def _render_toggle(self, screen, rect, label, active, name, active_color=None):
        hovered = (self.hovered == name)
        if active:
            color = active_color if active_color else self.COLORS['accent']
            border = (255, 255, 255)
        elif hovered:
            color = self.COLORS['bg_light']
            border = self.COLORS['border_light']
        else:
            color = self.COLORS['bg_dark']
            border = self.COLORS['border_light']

        pygame.draw.rect(screen, color, rect, border_radius=4)
        pygame.draw.rect(screen, border, rect, 1, border_radius=4)
        txt = self.font_small.render(label, True, self.COLORS['text'])
        screen.blit(txt, txt.get_rect(center=rect.center))

    def _render_action_button(self, screen, rect, label, color_key, hover_key, name):
        hovered = (self.hovered == name)
        color = self.COLORS[hover_key] if hovered else self.COLORS[color_key]
        pygame.draw.rect(screen, color, rect, border_radius=5)
        pygame.draw.rect(screen, (230, 230, 230), rect, 1, border_radius=5)
        txt = self.font_small.render(label, True, (255, 255, 255))
        screen.blit(txt, txt.get_rect(center=rect.center))