# src/scenes/editor/components/brush_buttons.py

import pygame


class BrushButtons:
    """Botões para seleção do tipo de pincel/ferramenta"""

    # Constantes para os tipos de brush
    BRUSH_PENCIL = "pencil"  # Pincel normal
    BRUSH_BUCKET = "bucket"  # Balde (preenchimento)

    def __init__(self, x, y, width=180, height=110):  # AUMENTADO: largura 180, altura 110
        self.rect = pygame.Rect(x, y, width, height)
        self.visible = True
        self.focused = False

        # Brush atual
        self.current_brush = self.BRUSH_PENCIL

        # Para arrastar
        self.dragging = False
        self.drag_start_x = 0
        self.drag_start_y = 0

        # Para redimensionamento
        self.resizing = False
        self.resize_margin = 10
        self.min_width = 160  # AUMENTADO
        self.min_height = 90  # AUMENTADO

        # Botões internos
        self._init_buttons()

        # Tooltips
        self.show_tooltip = False
        self.tooltip_text = ""
        self.tooltip_timer = 0
        self.tooltip_mouse_pos = (0, 0)

    def _init_buttons(self):
        """Inicializa botões com posições relativas ao rect"""
        button_width = 70  # AUMENTADO
        button_height = 30
        spacing = 10
        start_y = 30  # TÍTULO DENTRO: espaço para o título (25px) + margem

        # Botão Pincel (esquerda)
        self.pencil_rect = pygame.Rect(
            self.rect.x + 10,
            self.rect.y + start_y,
            button_width,
            button_height
        )

        # Botão Balde (direita)
        self.bucket_rect = pygame.Rect(
            self.rect.x + 10 + button_width + spacing,
            self.rect.y + start_y,
            button_width,
            button_height
        )

    def _update_button_positions(self):
        """Mantém botões alinhados após movimento/redimensionamento"""
        button_width = 70
        button_height = 30
        spacing = 10
        start_y = 30

        self.pencil_rect.x = self.rect.x + 10
        self.pencil_rect.y = self.rect.y + start_y

        self.bucket_rect.x = self.rect.x + 10 + button_width + spacing
        self.bucket_rect.y = self.rect.y + start_y

    def handle_event(self, event):
        """Processa eventos"""
        if not self.visible:
            return False

        mouse_pos = pygame.mouse.get_pos()
        mouse_x, mouse_y = mouse_pos

        self.focused = self.rect.collidepoint(mouse_x, mouse_y)

        if event.type == pygame.MOUSEBUTTONDOWN:
            if event.button == 1:
                return self._handle_left_click(mouse_x, mouse_y)

        elif event.type == pygame.MOUSEBUTTONUP:
            if event.button == 1:
                self.dragging = False
                self.resizing = False

        elif event.type == pygame.MOUSEMOTION:
            return self._handle_mouse_motion(mouse_x, mouse_y)

        elif event.type == pygame.KEYDOWN and self.focused:
            return self._handle_keydown(event)

        return False

    def _handle_left_click(self, mouse_x, mouse_y):
        """Processa clique esquerdo"""
        # Redimensionamento
        if (self.rect.right - self.resize_margin <= mouse_x <= self.rect.right + self.resize_margin and
            self.rect.bottom - self.resize_margin <= mouse_y <= self.rect.bottom + self.resize_margin):
            self.resizing = True
            return True

        # Arrastar pelo título
        title_rect = pygame.Rect(self.rect.x, self.rect.y, self.rect.width, 25)
        if title_rect.collidepoint(mouse_x, mouse_y):
            self.dragging = True
            self.drag_start_x = mouse_x - self.rect.x
            self.drag_start_y = mouse_y - self.rect.y
            return True

        # Clique nos botões
        if self.pencil_rect.collidepoint(mouse_x, mouse_y):
            self.current_brush = self.BRUSH_PENCIL
            return True
        elif self.bucket_rect.collidepoint(mouse_x, mouse_y):
            self.current_brush = self.BRUSH_BUCKET
            return True

        return False

    def _handle_mouse_motion(self, mouse_x, mouse_y):
        """Processa movimento do mouse"""
        if self.resizing:
            new_width = max(self.min_width, mouse_x - self.rect.x)
            new_height = max(self.min_height, mouse_y - self.rect.y)
            self.rect.width = new_width
            self.rect.height = new_height
            self._update_button_positions()
            return True
        elif self.dragging:
            self.rect.x = mouse_x - self.drag_start_x
            self.rect.y = mouse_y - self.drag_start_y
            self._update_button_positions()
            return True
        return False

    def _handle_keydown(self, event):
        """Atalhos de teclado"""
        if event.key == pygame.K_b:
            self.current_brush = self.BRUSH_PENCIL
            return True
        elif event.key == pygame.K_v:
            self.current_brush = self.BRUSH_BUCKET
            return True
        return False

    def get_current_brush(self):
        """Retorna o brush atual"""
        return self.current_brush

    def render(self, screen, font_small):
        """Renderiza os botões"""
        if not self.visible:
            return

        # Sombra
        shadow_rect = self.rect.copy()
        shadow_rect.x += 3
        shadow_rect.y += 3
        pygame.draw.rect(screen, (20, 20, 30), shadow_rect, border_radius=8)

        # Fundo
        if self.focused:
            bg_color = (60, 60, 75)
            border_color = (140, 140, 160)
        else:
            bg_color = (45, 45, 55)
            border_color = (90, 90, 100)

        pygame.draw.rect(screen, bg_color, self.rect, border_radius=8)
        pygame.draw.rect(screen, border_color, self.rect, 2, border_radius=8)

        # Barra de título (agora INTEGRADA ao fundo, não separada visualmente)
        title_bar = pygame.Rect(self.rect.x, self.rect.y, self.rect.width, 25)
        pygame.draw.rect(screen, (70, 70, 85), title_bar, border_top_left_radius=8, border_top_right_radius=8)

        # Título (DENTRO da barra)
        title = font_small.render("FERRAMENTAS", True, (255, 255, 255))
        screen.blit(title, (self.rect.x + 10, self.rect.y + 5))  # Ajustado para ficar dentro

        # Alça de redimensionamento
        resize_handle = pygame.Rect(self.rect.right - 15, self.rect.bottom - 15, 10, 10)
        pygame.draw.rect(screen, (150, 150, 150), resize_handle)
        pygame.draw.line(screen, (200, 200, 200),
                        (resize_handle.x + 2, resize_handle.bottom - 2),
                        (resize_handle.right - 2, resize_handle.y + 2), 2)

        # Botão Pincel
        pencil_color = (100, 150, 200) if self.current_brush == self.BRUSH_PENCIL else (60, 60, 70)
        pygame.draw.rect(screen, pencil_color, self.pencil_rect, border_radius=3)
        pygame.draw.rect(screen, (100, 100, 100), self.pencil_rect, 1, border_radius=3)
        pencil_text = font_small.render("PINCEL", True, (255, 255, 255))
        pencil_x = self.pencil_rect.x + (self.pencil_rect.width - pencil_text.get_width()) // 2
        pencil_y = self.pencil_rect.y + (self.pencil_rect.height - pencil_text.get_height()) // 2
        screen.blit(pencil_text, (pencil_x, pencil_y))

        # Botão Balde
        bucket_color = (100, 150, 200) if self.current_brush == self.BRUSH_BUCKET else (60, 60, 70)
        pygame.draw.rect(screen, bucket_color, self.bucket_rect, border_radius=3)
        pygame.draw.rect(screen, (100, 100, 100), self.bucket_rect, 1, border_radius=3)
        bucket_text = font_small.render("BALDE", True, (255, 255, 255))
        bucket_x = self.bucket_rect.x + (self.bucket_rect.width - bucket_text.get_width()) // 2
        bucket_y = self.bucket_rect.y + (self.bucket_rect.height - bucket_text.get_height()) // 2
        screen.blit(bucket_text, (bucket_x, bucket_y))

        # Instrução (opcional) - só aparece se hover e espaço suficiente
        if self.focused and self.rect.height >= 110:
            hint = font_small.render("Clique com mouse", True, (150, 150, 150))
            hint_x = self.rect.x + (self.rect.width - hint.get_width()) // 2
            hint_y = self.rect.y + self.rect.height - 20
            screen.blit(hint, (hint_x, hint_y))