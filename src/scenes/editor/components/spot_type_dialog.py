# src/scenes/editor/components/spot_type_dialog.py
"""
Diálogo para editar os tipos permitidos de um spot (ATÉ 4).
Vazio = qualquer tipo.
"""
import pygame

from src.editor.tower_spot_editor import (
    TYPE_COLORS, draw_typed_rect, get_type_colors, MAX_TYPES_PER_SPOT,
)


ALL_TYPES = [
    "normal", "fire", "water", "electric", "grass", "ice",
    "fighting", "poison", "ground", "flying", "psychic", "bug",
    "rock", "ghost", "dragon", "dark", "steel", "fairy",
]

TYPE_NAMES_PT = {
    "normal": "Normal", "fire": "Fogo", "water": "Água", "electric": "Elétrico",
    "grass": "Planta", "ice": "Gelo", "fighting": "Lutador", "poison": "Veneno",
    "ground": "Terra", "flying": "Voador", "psychic": "Psíquico", "bug": "Inseto",
    "rock": "Pedra", "ghost": "Fantasma", "dragon": "Dragão", "dark": "Sombrio",
    "steel": "Aço", "fairy": "Fada",
}


class SpotTypeDialog:
    COLORS = {
        'bg':           (40, 40, 50),
        'bg_light':     (55, 55, 68),
        'border':       (255, 215, 0),
        'text':         (240, 240, 245),
        'text_dim':     (180, 180, 200),
        'text_warn':    (255, 180, 80),
    }

    def __init__(self, x, y, spot):
        self.rect = pygame.Rect(x, y, 600, 420)
        self.visible = True
        self.spot = spot

        # Lista ordenada preservando ordem de seleção
        # (a cor de cada posição 0-3 importa para o desenho)
        self.temp_types = list(spot.allowed_types or [])[:MAX_TYPES_PER_SPOT]

        self.font_title = pygame.font.Font(None, 24)
        self.font       = pygame.font.Font(None, 18)
        self.font_small = pygame.font.Font(None, 15)
        self.font_warn  = pygame.font.Font(None, 15)

        self.dragging = False
        self.drag_off = (0, 0)
        self._warning_msg = ""
        self._warning_timer = 0.0

        self._init_layout()

    def _init_layout(self):
        x, y, w, h = self.rect
        self.title_rect = pygame.Rect(x, y, w, 30)

        # ===== Grade 6×3 de checkboxes =====
        self.checkbox_rects = {}
        grid_x = x + 20
        grid_y = y + 55
        col_w = (w - 40) // 6
        row_h = 65

        for idx, t in enumerate(ALL_TYPES):
            col = idx % 6
            row = idx // 6
            cx = grid_x + col * col_w
            cy = grid_y + row * row_h
            box = pygame.Rect(cx + 6, cy + 2, 22, 22)
            label = pygame.Rect(cx, cy + 26, col_w, 20)
            self.checkbox_rects[t] = (box, label)

        # ===== Preview abaixo da grade, centralizado =====
        prev_size = 80
        prev_y = grid_y + 3 * row_h + 8  # logo após a 3ª linha
        self.preview_rect = pygame.Rect(
            x + (w - prev_size) // 2, prev_y, prev_size, prev_size
        )
        self.preview_label_rect = pygame.Rect(
            x, self.preview_rect.bottom + 4, w, 18
        )

        # ===== Botões =====
        btn_y = y + h - 50
        self.btn_all = pygame.Rect(x + 20, btn_y, 110, 30)
        self.btn_none = pygame.Rect(x + 140, btn_y, 110, 30)
        self.btn_save = pygame.Rect(x + w - 230, btn_y, 100, 30)
        self.btn_cancel = pygame.Rect(x + w - 120, btn_y, 100, 30)

    # ---------------------------------------------------------
    def _toggle(self, t):
        if t in self.temp_types:
            self.temp_types.remove(t)
        else:
            if len(self.temp_types) >= MAX_TYPES_PER_SPOT:
                self._warning_msg = f"Máximo de {MAX_TYPES_PER_SPOT} tipos por spot!"
                self._warning_timer = 2.0
                return
            self.temp_types.append(t)

    # ---------------------------------------------------------
    def handle_event(self, event):
        if not self.visible:
            return None
        mp = pygame.mouse.get_pos()

        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            if self.title_rect.collidepoint(mp):
                self.dragging = True
                self.drag_off = (mp[0] - self.rect.x, mp[1] - self.rect.y)
                return None

            if self.btn_save.collidepoint(mp):
                # Ordem importa (define qual cor vai em qual lado do quadrado)
                self.spot.allowed_types = list(self.temp_types)[:MAX_TYPES_PER_SPOT]
                self.visible = False
                print(f"[SpotTypeDialog] Tipos definidos: {self.spot.allowed_types}")
                return "saved"

            if self.btn_cancel.collidepoint(mp):
                self.visible = False
                return "cancel"

            if self.btn_all.collidepoint(mp):
                self.temp_types = list(ALL_TYPES[:MAX_TYPES_PER_SPOT])
                self._warning_msg = f"Só cabem {MAX_TYPES_PER_SPOT} tipos — os 4 primeiros foram aplicados."
                self._warning_timer = 2.5
                return None

            if self.btn_none.collidepoint(mp):
                self.temp_types = []
                return None

            for t, (box, lbl) in self.checkbox_rects.items():
                if box.collidepoint(mp) or lbl.collidepoint(mp):
                    self._toggle(t)
                    return None

            if not self.rect.collidepoint(mp):
                self.visible = False
                return "cancel"

        elif event.type == pygame.MOUSEBUTTONUP and event.button == 1:
            self.dragging = False

        elif event.type == pygame.MOUSEMOTION and self.dragging:
            self.rect.x = mp[0] - self.drag_off[0]
            self.rect.y = mp[1] - self.drag_off[1]
            self._init_layout()

        elif event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE:
            self.visible = False
            return "cancel"

        return None

    # ---------------------------------------------------------
    def update(self, dt):
        if self._warning_timer > 0:
            self._warning_timer -= dt
            if self._warning_timer <= 0:
                self._warning_msg = ""

    # ---------------------------------------------------------
    def render(self, screen):
        if not self.visible:
            return

        ov = pygame.Surface((screen.get_width(), screen.get_height()))
        ov.set_alpha(160);
        ov.fill((0, 0, 0))
        screen.blit(ov, (0, 0))

        pygame.draw.rect(screen, self.COLORS['bg'], self.rect, border_radius=10)
        pygame.draw.rect(screen, self.COLORS['border'], self.rect, 2, border_radius=10)

        pygame.draw.rect(screen, self.COLORS['bg_light'], self.title_rect,
                         border_top_left_radius=10, border_top_right_radius=10)
        screen.blit(
            self.font_title.render("Tipos permitidos no spot", True, (255, 255, 255)),
            (self.rect.x + 12, self.rect.y + 6),
        )

        # Contador (canto superior direito — não colide mais com nada)
        count = len(self.temp_types)
        counter = self.font.render(
            f"{count}/{MAX_TYPES_PER_SPOT}",
            True, (255, 215, 0) if count else self.COLORS['text_dim'],
        )
        screen.blit(counter, (self.rect.right - 60, self.rect.y + 8))

        hint = self.font_small.render(
            "Vazio = qualquer tipo | Ordem define as cores (1º = canto superior esquerdo)",
            True, self.COLORS['text_dim'],
        )
        screen.blit(hint, (self.rect.x + 12, self.rect.y + 33))

        # ===== Checkboxes =====
        mp = pygame.mouse.get_pos()
        for t, (box, lbl) in self.checkbox_rects.items():
            checked = t in self.temp_types
            hovered = box.collidepoint(mp) or lbl.collidepoint(mp)
            color = TYPE_COLORS.get(t, (120, 120, 120))

            if checked:
                pygame.draw.rect(screen, color, box, border_radius=4)
                pygame.draw.rect(screen, (255, 255, 255), box, 2, border_radius=4)
                pygame.draw.line(screen, (0, 0, 0),
                                 (box.x + 4, box.y + 11), (box.x + 9, box.y + 16), 3)
                pygame.draw.line(screen, (0, 0, 0),
                                 (box.x + 9, box.y + 16), (box.x + 18, box.y + 5), 3)
                idx = self.temp_types.index(t)
                idx_surf = self.font_small.render(str(idx + 1), True, (0, 0, 0))
                screen.blit(idx_surf, (box.x + 22, box.y + 4))
            else:
                bg = (80, 80, 100) if hovered else (60, 60, 75)
                pygame.draw.rect(screen, bg, box, border_radius=4)
                pygame.draw.rect(screen, color, box, 2, border_radius=4)

            label_text = TYPE_NAMES_PT.get(t, t.capitalize())
            label_color = (255, 255, 255) if checked else self.COLORS['text_dim']
            screen.blit(
                self.font_small.render(label_text, True, label_color),
                (lbl.x + 4, lbl.y + 2),
            )

        # ===== Preview abaixo da grade =====
        prev = self.preview_rect
        pygame.draw.rect(screen, (25, 25, 32), prev, border_radius=6)
        pygame.draw.rect(screen, (100, 100, 120), prev, 1, border_radius=6)

        colors = get_type_colors(self.temp_types)
        draw_typed_rect(screen, prev.x + 10, prev.y + 10,
                        prev.width - 20, prev.height - 20,
                        colors, fill_alpha=180, border_width=4)

        prev_label = self.font_small.render("Preview do slot", True, self.COLORS['text_dim'])
        screen.blit(prev_label, prev_label.get_rect(center=self.preview_label_rect.center))

        # ===== Aviso =====
        if self._warning_msg:
            warn = self.font_warn.render(self._warning_msg, True, self.COLORS['text_warn'])
            screen.blit(warn, (self.rect.x + 12, self.preview_label_rect.bottom + 4))

        # ===== Botões =====
        def draw_btn(rect, label, color, hover_color):
            hovered = rect.collidepoint(mp)
            c = hover_color if hovered else color
            pygame.draw.rect(screen, c, rect, border_radius=5)
            pygame.draw.rect(screen, (230, 230, 230), rect, 1, border_radius=5)
            txt = self.font.render(label, True, (255, 255, 255))
            screen.blit(txt, txt.get_rect(center=rect.center))

        draw_btn(self.btn_all, "Tudo (4)", (60, 100, 60), (80, 140, 80))
        draw_btn(self.btn_none, "Limpar", (100, 80, 60), (140, 110, 80))
        draw_btn(self.btn_save, "Salvar", (0, 140, 0), (0, 180, 0))
        draw_btn(self.btn_cancel, "Cancelar", (150, 0, 0), (190, 0, 0))