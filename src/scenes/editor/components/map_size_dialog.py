import pygame


class MapSizeDialog:
    def __init__(self, x, y, width, height, current_width, current_height):
        self.rect = pygame.Rect(x, y, width, height)
        self.visible = True
        self.focused = True
        self.current_width = current_width
        self.current_height = current_height
        self.temp_width = str(current_width)
        self.temp_height = str(current_height)
        self.active_input = "width"  # "width" or "height"

        # Botões
        button_width = 80
        button_height = 30
        self.confirm_rect = pygame.Rect(
            x + (width - button_width * 2 - 10) // 2,
            y + height - 50,
            button_width,
            button_height
        )
        self.cancel_rect = pygame.Rect(
            x + (width - button_width * 2 - 10) // 2 + button_width + 10,
            y + height - 50,
            button_width,
            button_height
        )

        # Input boxes
        self.width_rect = pygame.Rect(x + 50, y + 80, 100, 30)
        self.height_rect = pygame.Rect(x + 50, y + 130, 100, 30)

    def handle_event(self, event):
        """Processa eventos do diálogo"""
        if not self.visible:
            return None

        if event.type == pygame.KEYDOWN:
            return self._handle_keydown(event)
        elif event.type == pygame.MOUSEBUTTONDOWN:
            if event.button == 1:
                return self._handle_mousedown(event)

        return None

    def _handle_keydown(self, event):
        """Processa teclas pressionadas"""
        if event.key == pygame.K_RETURN:
            return self.confirm()
        elif event.key == pygame.K_ESCAPE:
            self.visible = False
            return None
        elif event.key == pygame.K_TAB:
            # Alterna entre width e height
            self.active_input = "height" if self.active_input == "width" else "width"
            return None
        elif event.key == pygame.K_BACKSPACE:
            if self.active_input == "width":
                self.temp_width = self.temp_width[:-1]
            else:
                self.temp_height = self.temp_height[:-1]
            return None
        else:
            # Adiciona números
            if event.unicode.isdigit():
                if self.active_input == "width":
                    self.temp_width += event.unicode
                else:
                    self.temp_height += event.unicode
            return None

    def _handle_mousedown(self, event):
        """Processa clique do mouse"""
        mouse_pos = pygame.mouse.get_pos()

        # Verifica cliques nos inputs
        if self.width_rect.collidepoint(mouse_pos):
            self.active_input = "width"
            return None
        elif self.height_rect.collidepoint(mouse_pos):
            self.active_input = "height"
            return None
        elif self.confirm_rect.collidepoint(mouse_pos):
            return self.confirm()
        elif self.cancel_rect.collidepoint(mouse_pos):
            self.visible = False
            return None
        elif not self.rect.collidepoint(mouse_pos):
            self.visible = False
            return None

        return None

    def confirm(self):
        """Confirma a operação e retorna os novos valores"""
        try:
            new_width = max(10, min(500, int(self.temp_width) if self.temp_width else 10))
            new_height = max(10, min(500, int(self.temp_height) if self.temp_height else 10))
            self.visible = False
            return (new_width, new_height)
        except ValueError:
            return None

    def render(self, screen):
        """Renderiza o diálogo"""
        if not self.visible:
            return

        # Fundo semi-transparente
        overlay = pygame.Surface((screen.get_width(), screen.get_height()))
        overlay.set_alpha(128)
        overlay.fill((0, 0, 0))
        screen.blit(overlay, (0, 0))

        # Caixa de diálogo
        pygame.draw.rect(screen, (60, 60, 70), self.rect, border_radius=10)
        pygame.draw.rect(screen, (255, 215, 0), self.rect, 2, border_radius=10)

        # Título
        font_title = pygame.font.Font(None, 28)
        title = font_title.render("Configurar Tamanho do Mapa", True, (255, 255, 255))
        title_x = self.rect.x + (self.rect.width - title.get_width()) // 2
        screen.blit(title, (title_x, self.rect.y + 20))

        # Labels e inputs
        font = pygame.font.Font(None, 20)

        # Largura
        width_label = font.render("Largura (tiles):", True, (200, 200, 200))
        screen.blit(width_label, (self.rect.x + 20, self.rect.y + 60))

        color = (100, 150, 255) if self.active_input == "width" else (80, 80, 90)
        pygame.draw.rect(screen, color, self.width_rect, 2)
        width_surf = font.render(self.temp_width, True, (255, 255, 255))
        screen.blit(width_surf, (self.width_rect.x + 5, self.width_rect.y + 5))

        # Altura
        height_label = font.render("Altura (tiles):", True, (200, 200, 200))
        screen.blit(height_label, (self.rect.x + 20, self.rect.y + 110))

        color = (100, 150, 255) if self.active_input == "height" else (80, 80, 90)
        pygame.draw.rect(screen, color, self.height_rect, 2)
        height_surf = font.render(self.temp_height, True, (255, 255, 255))
        screen.blit(height_surf, (self.height_rect.x + 5, self.height_rect.y + 5))

        # Informação
        info = font.render("Min: 10, Max: 500 tiles | TAB para alternar", True, (150, 150, 150))
        info_x = self.rect.x + (self.rect.width - info.get_width()) // 2
        screen.blit(info, (info_x, self.rect.y + 170))

        # Botões
        self._render_buttons(screen, font)

    def _render_buttons(self, screen, font):
        """Renderiza os botões"""
        # Confirmar
        pygame.draw.rect(screen, (0, 150, 0), self.confirm_rect, border_radius=5)
        pygame.draw.rect(screen, (255, 255, 255), self.confirm_rect, 1, border_radius=5)
        confirm_text = font.render("Confirmar", True, (255, 255, 255))
        confirm_x = self.confirm_rect.x + (self.confirm_rect.width - confirm_text.get_width()) // 2
        confirm_y = self.confirm_rect.y + (self.confirm_rect.height - confirm_text.get_height()) // 2
        screen.blit(confirm_text, (confirm_x, confirm_y))

        # Cancelar
        pygame.draw.rect(screen, (150, 0, 0), self.cancel_rect, border_radius=5)
        pygame.draw.rect(screen, (255, 255, 255), self.cancel_rect, 1, border_radius=5)
        cancel_text = font.render("Cancelar", True, (255, 255, 255))
        cancel_x = self.cancel_rect.x + (self.cancel_rect.width - cancel_text.get_width()) // 2
        cancel_y = self.cancel_rect.y + (self.cancel_rect.height - cancel_text.get_height()) // 2
        screen.blit(cancel_text, (cancel_x, cancel_y))