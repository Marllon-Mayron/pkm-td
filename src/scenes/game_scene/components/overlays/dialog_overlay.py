import pygame


class DialogOverlay:
    """Overlay de diálogo com layout vertical, sprite metade fora, texto grande com rolagem e responsivo."""

    COLORS = {
        'overlay_bg': (0, 0, 0, 180),
        'dialog_bg': (45, 45, 60),
        'dialog_border': (120, 130, 160),
        'speaker_frame': (70, 80, 110),
        'speaker_bg': (30, 30, 45),
        'text_primary': (255, 255, 255),
        'text_secondary': (200, 210, 230),
        'text_speaker': (180, 210, 255),
        'button_bg': (80, 140, 220),
        'button_hover': (100, 170, 255),
        'button_text': (255, 255, 255),
        'button_border': (200, 220, 255),
        'shadow': (0, 0, 0, 80),
        'text_panel_bg': (35, 35, 50),
        'text_panel_border': (100, 110, 140),
        'scrollbar_bg': (60, 60, 80),
        'scrollbar_thumb': (140, 150, 190),
        'scrollbar_thumb_hover': (170, 180, 220),
    }

    def __init__(self, game_scene, text, speaker="", sprite_path="", action_label="OK", action_callback=None):
        self.game_scene = game_scene
        self.text = text
        self.speaker = speaker
        self.sprite = None
        if sprite_path:
            try:
                self.sprite = pygame.image.load(sprite_path).convert_alpha()
            except Exception:
                pass
        self.action_label = action_label
        self.action_callback = action_callback
        self.active = True

        # Referências
        sm = self.game_scene.screen_manager
        self.viewport = pygame.Rect(sm.viewport_x, sm.viewport_y,
                                    sm.viewport_width, sm.viewport_height)

        # Dimensões - responsivas
        self.margin = 20
        self.sprite_size = min(120, self.viewport.width // 5)
        self.sprite_radius = 20
        self.button_height = max(36, min(44, self.viewport.height // 20))
        self.button_width = min(160, self.viewport.width // 5)
        self.dialog_width = min(720, self.viewport.width - 60)

        # Fontes
        font_size = max(20, min(24, self.viewport.width // 55))
        self.font_speaker = pygame.font.Font(None, font_size)
        self.font_text = pygame.font.Font(None, font_size - 2 if font_size > 20 else font_size)
        self.font_button = pygame.font.Font(None, font_size + 2 if font_size < 24 else font_size)

        # Parâmetros de texto
        self.line_height = max(26, min(32, self.viewport.height // 30))
        self._cached_lines = []

        # Calcula altura e posiciona
        self.dialog_height = self._calculate_height()
        self.dialog_x = self.viewport.x + (self.viewport.width - self.dialog_width) // 2
        self.dialog_y = self.viewport.y + (self.viewport.height - self.dialog_height) // 2
        self.rect = pygame.Rect(self.dialog_x, self.dialog_y,
                                self.dialog_width, self.dialog_height)

        # Sprite: metade para fora, centralizado no topo
        sprite_center_x = self.dialog_x + self.dialog_width // 2
        sprite_top_y = self.dialog_y - self.sprite_size // 3
        self.sprite_area = pygame.Rect(
            sprite_center_x - self.sprite_size // 2,
            sprite_top_y,
            self.sprite_size,
            self.sprite_size
        )

        # Nome do falante
        speaker_y = self.dialog_y + self.margin + self.sprite_size // 2 + 10
        self.speaker_area = pygame.Rect(
            self.dialog_x + self.margin,
            speaker_y,
            self.dialog_width - 2 * self.margin,
            30
        )

        # Área do texto
        text_y = self.speaker_area.bottom + 8 if self.speaker else self.dialog_y + self.margin + self.sprite_size // 2 + 15
        text_height = self.dialog_height - text_y - self.margin - self.button_height - 15
        if text_height < 160:
            text_height = 160
        self.text_area = pygame.Rect(
            self.dialog_x + self.margin,
            text_y,
            self.dialog_width - 2 * self.margin,
            text_height
        )

        # Botão
        self.button_rect = pygame.Rect(
            self.dialog_x + (self.dialog_width - self.button_width) // 2,
            self.dialog_y + self.dialog_height - self.margin - self.button_height,
            self.button_width,
            self.button_height
        )

        # Estado da rolagem
        self.scroll_offset = 0
        self.total_lines = 0
        self.visible_lines = 0
        self.scrollbar_rect = None
        self.scrollbar_dragging = False
        self.scrollbar_hovered = False
        self.drag_start_y = 0
        self.drag_start_offset = 0
        self.button_hovered = False

    def _calculate_height(self):
        """Calcula a altura do diálogo - prioriza espaço para o texto."""
        # Altura máxima disponível (usa quase toda a tela)
        max_height = self.viewport.height - 40
        min_height = max(350, self.viewport.height // 2)  # Altura mínima aumentada

        # Calcula linhas necessárias
        inner_width = self.dialog_width - 2 * self.margin - 20
        lines = self._wrap_text(self.text, inner_width)
        line_count = max(1, len(lines))
        self.total_lines = line_count

        # Mostra até 12 linhas visíveis (aumentado)
        max_visible = max(6, min(14, (max_height - 160) // self.line_height))
        visible_lines = min(line_count, max_visible)
        self.visible_lines = visible_lines

        # Altura base (agora com mais espaço para o texto)
        base_height = (self.margin * 2) + (self.sprite_size // 2) + 25
        if self.speaker:
            base_height += 35
        base_height += 10 + (visible_lines * self.line_height) + 25 + self.button_height + self.margin

        return max(min_height, min(base_height, max_height))

    def _wrap_text(self, text, max_width):
        """Quebra o texto em linhas."""
        if not text:
            return []
        words = text.split(' ')
        lines = []
        current_line = []
        for word in words:
            if self.font_text.size(word)[0] > max_width:
                if current_line:
                    lines.append(' '.join(current_line))
                    current_line = []
                for char in word:
                    test_line = ''.join(current_line + [char])
                    if self.font_text.size(test_line)[0] <= max_width:
                        current_line.append(char)
                    else:
                        if current_line:
                            lines.append(''.join(current_line))
                        current_line = [char]
                if current_line:
                    lines.append(''.join(current_line))
                    current_line = []
                continue

            test_line = ' '.join(current_line + [word])
            if self.font_text.size(test_line)[0] <= max_width:
                current_line.append(word)
            else:
                if current_line:
                    lines.append(' '.join(current_line))
                current_line = [word]
        if current_line:
            lines.append(' '.join(current_line))
        return lines

    def _get_lines(self):
        """Retorna a lista de linhas (cache)."""
        if not self._cached_lines:
            inner_width = self.text_area.width - 20
            self._cached_lines = self._wrap_text(self.text, inner_width)
            self.total_lines = len(self._cached_lines)
            self.visible_lines = (self.text_area.height - 10) // self.line_height
        return self._cached_lines

    def _recalculate_layout(self):
        """Recalcula layout quando a viewport muda."""
        sm = self.game_scene.screen_manager
        self.viewport = pygame.Rect(sm.viewport_x, sm.viewport_y,
                                    sm.viewport_width, sm.viewport_height)

        # Recalcula dimensões
        self.sprite_size = min(120, self.viewport.width // 5)
        self.button_height = max(36, min(44, self.viewport.height // 20))
        self.button_width = min(160, self.viewport.width // 5)
        self.dialog_width = min(720, self.viewport.width - 60)

        # Recalcula fontes
        font_size = max(20, min(24, self.viewport.width // 55))
        self.font_speaker = pygame.font.Font(None, font_size)
        self.font_text = pygame.font.Font(None, font_size - 2 if font_size > 20 else font_size)
        self.font_button = pygame.font.Font(None, font_size + 2 if font_size < 24 else font_size)
        self.line_height = max(26, min(32, self.viewport.height // 30))

        # Recalcula altura
        self.dialog_height = self._calculate_height()
        self.dialog_x = self.viewport.x + (self.viewport.width - self.dialog_width) // 2
        self.dialog_y = self.viewport.y + (self.viewport.height - self.dialog_height) // 2
        self.rect = pygame.Rect(self.dialog_x, self.dialog_y,
                                self.dialog_width, self.dialog_height)

        # Sprite
        sprite_center_x = self.dialog_x + self.dialog_width // 2
        sprite_top_y = self.dialog_y - self.sprite_size // 3
        self.sprite_area = pygame.Rect(
            sprite_center_x - self.sprite_size // 2,
            sprite_top_y,
            self.sprite_size,
            self.sprite_size
        )

        # Nome do falante
        speaker_y = self.dialog_y + self.margin + self.sprite_size // 2 + 10
        self.speaker_area = pygame.Rect(
            self.dialog_x + self.margin,
            speaker_y,
            self.dialog_width - 2 * self.margin,
            30
        )

        # Área do texto (MUITO MAIOR)
        text_y = self.speaker_area.bottom + 8 if self.speaker else self.dialog_y + self.margin + self.sprite_size // 2 + 15
        text_height = self.dialog_height - text_y - self.margin - self.button_height - 15
        if text_height < 120:
            text_height = 120
        self.text_area = pygame.Rect(
            self.dialog_x + self.margin,
            text_y,
            self.dialog_width - 2 * self.margin,
            text_height
        )

        # Botão
        self.button_rect = pygame.Rect(
            self.dialog_x + (self.dialog_width - self.button_width) // 2,
            self.dialog_y + self.dialog_height - self.margin - self.button_height,
            self.button_width,
            self.button_height
        )

        # Limpa cache
        self._cached_lines = []
        self.scroll_offset = 0

    def handle_event(self, event):
        if not self.active:
            return False

        # Mouse wheel
        if event.type == pygame.MOUSEWHEEL:
            if self.text_area.collidepoint(pygame.mouse.get_pos()):
                self.scroll_offset -= event.y
                self._clamp_scroll()
                return True

        # Mouse motion
        if event.type == pygame.MOUSEMOTION:
            self.button_hovered = self.button_rect.collidepoint(event.pos)
            if self.scrollbar_rect and self.scrollbar_rect.collidepoint(event.pos):
                self.scrollbar_hovered = True
            else:
                self.scrollbar_hovered = False

            if self.scrollbar_dragging:
                mouse_y = event.pos[1]
                delta_y = mouse_y - self.drag_start_y
                bar_height = self.scrollbar_rect.height
                if bar_height > 0:
                    max_scroll = max(0, self.total_lines - self.visible_lines)
                    if max_scroll > 0:
                        new_offset = self.drag_start_offset + (delta_y / bar_height) * max_scroll
                        self.scroll_offset = int(round(new_offset))
                        self._clamp_scroll()
                return True
            return True

        # Mouse click
        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            if self.button_rect.collidepoint(event.pos):
                if self.action_callback:
                    self.action_callback()
                self.active = False
                return True

            if self.scrollbar_rect and self.scrollbar_rect.collidepoint(event.pos):
                self.scrollbar_dragging = True
                self.drag_start_y = event.pos[1]
                self.drag_start_offset = self.scroll_offset
                return True

        # Mouse release
        if event.type == pygame.MOUSEBUTTONUP and event.button == 1:
            if self.scrollbar_dragging:
                self.scrollbar_dragging = False
                return True

        return False

    def _clamp_scroll(self):
        """Mantém o scroll dentro dos limites."""
        max_scroll = max(0, self.total_lines - self.visible_lines)
        if self.scroll_offset < 0:
            self.scroll_offset = 0
        elif self.scroll_offset > max_scroll:
            self.scroll_offset = max_scroll

    def update(self, dt):
        # Verifica se a viewport mudou (responsividade)
        sm = self.game_scene.screen_manager
        current_viewport = pygame.Rect(sm.viewport_x, sm.viewport_y,
                                       sm.viewport_width, sm.viewport_height)
        if current_viewport != self.viewport:
            self._recalculate_layout()

    def render(self, screen):
        if not self.active:
            return

        # Overlay
        overlay = pygame.Surface((self.viewport.width, self.viewport.height), pygame.SRCALPHA)
        overlay.fill(self.COLORS['overlay_bg'])
        screen.blit(overlay, (self.viewport.x, self.viewport.y))

        # Sombra
        shadow_rect = self.rect.copy()
        shadow_rect.x += 8
        shadow_rect.y += 8
        shadow_surf = pygame.Surface((shadow_rect.width, shadow_rect.height), pygame.SRCALPHA)
        shadow_surf.fill(self.COLORS['shadow'])
        screen.blit(shadow_surf, shadow_rect)

        # Fundo do diálogo
        pygame.draw.rect(screen, self.COLORS['dialog_bg'], self.rect, border_radius=16)
        pygame.draw.rect(screen, self.COLORS['dialog_border'], self.rect, 2, border_radius=16)

        # Sprite (metade fora)
        sprite_bg_rect = self.sprite_area.inflate(12, 12)
        pygame.draw.rect(screen, self.COLORS['speaker_bg'], sprite_bg_rect, border_radius=self.sprite_radius + 4)
        pygame.draw.rect(screen, self.COLORS['speaker_frame'], sprite_bg_rect, 3, border_radius=self.sprite_radius + 4)

        if self.sprite:
            sprite_scaled = self._scale_image_to_fit(self.sprite, self.sprite_size, self.sprite_size)
            mask = pygame.Surface((self.sprite_size, self.sprite_size), pygame.SRCALPHA)
            pygame.draw.rect(mask, (255, 255, 255, 255), (0, 0, self.sprite_size, self.sprite_size),
                             border_radius=self.sprite_radius)
            sprite_final = sprite_scaled.copy()
            sprite_final.blit(mask, (0, 0), special_flags=pygame.BLEND_RGBA_MULT)
            screen.blit(sprite_final, self.sprite_area)
        else:
            placeholder_color = (100, 120, 160)
            pygame.draw.circle(screen, placeholder_color,
                               self.sprite_area.center, self.sprite_size // 2 - 4)
            if self.speaker:
                initial = self.speaker[0].upper()
                font_initial = pygame.font.Font(None, self.sprite_size // 2)
                init_surf = font_initial.render(initial, True, (220, 230, 250))
                init_rect = init_surf.get_rect(center=self.sprite_area.center)
                screen.blit(init_surf, init_rect)

        # Nome do falante
        if self.speaker:
            speaker_surf = self.font_speaker.render(self.speaker, True, self.COLORS['text_speaker'])
            speaker_rect = speaker_surf.get_rect(center=(self.dialog_x + self.dialog_width // 2,
                                                         self.speaker_area.centery))
            screen.blit(speaker_surf, speaker_rect)

        # Painel do texto (prancheta) - com fundo mais escuro para destaque
        panel_rect = self.text_area.inflate(-4, -4)
        pygame.draw.rect(screen, self.COLORS['text_panel_bg'], panel_rect, border_radius=8)
        pygame.draw.rect(screen, self.COLORS['text_panel_border'], panel_rect, 2, border_radius=8)

        # Texto com rolagem
        lines = self._get_lines()
        self.total_lines = len(lines)
        self.visible_lines = (self.text_area.height - 10) // self.line_height
        if self.visible_lines < 1:
            self.visible_lines = 1
        self._clamp_scroll()

        start_line = self.scroll_offset
        end_line = min(start_line + self.visible_lines, self.total_lines)

        for i in range(start_line, end_line):
            line_surf = self.font_text.render(lines[i], True, self.COLORS['text_primary'])
            line_x = self.text_area.x + (self.text_area.width - line_surf.get_width()) // 2
            line_y = self.text_area.y + 10 + (i - start_line) * self.line_height
            if line_y + line_surf.get_height() <= self.text_area.bottom - 10:
                screen.blit(line_surf, (line_x, line_y))

        # Barra de rolagem
        if self.total_lines > self.visible_lines:
            bar_x = self.text_area.right - 16
            bar_y = self.text_area.y + 6
            bar_height = self.text_area.height - 12
            bar_width = 8

            bg_rect = pygame.Rect(bar_x, bar_y, bar_width, bar_height)
            pygame.draw.rect(screen, self.COLORS['scrollbar_bg'], bg_rect, border_radius=4)

            max_scroll = max(1, self.total_lines - self.visible_lines)
            thumb_height = max(20, bar_height * (self.visible_lines / max(1, self.total_lines)))
            thumb_y = bar_y + (self.scroll_offset / max_scroll) * (bar_height - thumb_height)
            thumb_rect = pygame.Rect(bar_x, thumb_y, bar_width, thumb_height)
            thumb_color = self.COLORS['scrollbar_thumb_hover'] if self.scrollbar_hovered else self.COLORS['scrollbar_thumb']
            pygame.draw.rect(screen, thumb_color, thumb_rect, border_radius=4)

            self.scrollbar_rect = bg_rect
        else:
            self.scrollbar_rect = None

        # Botão
        button_color = self.COLORS['button_hover'] if self.button_hovered else self.COLORS['button_bg']
        pygame.draw.rect(screen, button_color, self.button_rect, border_radius=10)
        pygame.draw.rect(screen, self.COLORS['button_border'], self.button_rect, 2, border_radius=10)
        btn_text = self.font_button.render(self.action_label, True, self.COLORS['button_text'])
        btn_rect = btn_text.get_rect(center=self.button_rect.center)
        screen.blit(btn_text, btn_rect)

    def _scale_image_to_fit(self, image, target_w, target_h):
        orig_w, orig_h = image.get_size()
        scale = min(target_w / orig_w, target_h / orig_h)
        new_w = int(orig_w * scale)
        new_h = int(orig_h * scale)
        scaled = pygame.transform.smoothscale(image, (new_w, new_h))
        result = pygame.Surface((target_w, target_h), pygame.SRCALPHA)
        result.blit(scaled, ((target_w - new_w) // 2, (target_h - new_h) // 2))
        return result