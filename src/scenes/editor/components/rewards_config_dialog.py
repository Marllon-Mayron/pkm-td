# src/scenes/editor/components/rewards_config_dialog.py

import pygame


class RewardsConfigDialog:
    """Diálogo para configurar as recompensas da fase (gold e XP)"""

    def __init__(self, x, y, width, height, current_money=100, current_xp=50):
        self.rect = pygame.Rect(x, y, width, height)
        self.visible = True
        self.focused = True

        # Valores atuais
        self.current_money = current_money
        self.current_xp = current_xp

        # Valores temporários (para edição)
        self.temp_money = str(current_money)
        self.temp_xp = str(current_xp)

        # Campo ativo
        self.active_input = "money"  # "money" ou "xp"

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
        self.money_rect = pygame.Rect(x + 200, y + 100, 150, 35)
        self.xp_rect = pygame.Rect(x + 200, y + 160, 150, 35)

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
            # Alterna entre os inputs
            self.active_input = "xp" if self.active_input == "money" else "money"
            return None
        elif event.key == pygame.K_BACKSPACE:
            if self.active_input == "money":
                self.temp_money = self.temp_money[:-1]
            elif self.active_input == "xp":
                self.temp_xp = self.temp_xp[:-1]
            return None
        else:
            # Adiciona números
            if event.unicode.isdigit():
                if self.active_input == "money":
                    self.temp_money += event.unicode
                elif self.active_input == "xp":
                    self.temp_xp += event.unicode
            return None

    def _handle_mousedown(self, event):
        """Processa clique do mouse"""
        mouse_pos = pygame.mouse.get_pos()

        # Verifica cliques nos inputs
        if self.money_rect.collidepoint(mouse_pos):
            self.active_input = "money"
            return None
        elif self.xp_rect.collidepoint(mouse_pos):
            self.active_input = "xp"
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
        """Confirma e retorna os valores"""
        try:
            # Converte para int, garantindo valores positivos
            new_money = max(0, int(self.temp_money) if self.temp_money else 0)
            new_xp = max(0, int(self.temp_xp) if self.temp_xp else 0)

            self.visible = False
            return {
                'money': new_money,
                'experience': new_xp
            }
        except ValueError:
            return None

    def render(self, screen, font, font_small):
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
        title = font_title.render("Configuração de Recompensas", True, (255, 255, 255))
        title_x = self.rect.x + (self.rect.width - title.get_width()) // 2
        screen.blit(title, (title_x, self.rect.y + 20))

        # Descrição
        desc = font_small.render("Configure quanto o jogador receberá ao completar esta fase:", True, (200, 200, 200))
        desc_x = self.rect.x + (self.rect.width - desc.get_width()) // 2
        screen.blit(desc, (desc_x, self.rect.y + 55))

        # Label Gold/Money
        money_label = font.render("Gold (Dinheiro):", True, (255, 215, 0))
        screen.blit(money_label, (self.rect.x + 50, self.rect.y + 108))

        # Input Money
        color = (100, 150, 255) if self.active_input == "money" else (80, 80, 90)
        pygame.draw.rect(screen, color, self.money_rect, 2)
        pygame.draw.rect(screen, (50, 50, 60), self.money_rect)
        money_surf = font.render(self.temp_money, True, (255, 255, 255))
        screen.blit(money_surf, (self.money_rect.x + 10, self.money_rect.y + 8))

        # Label XP
        xp_label = font.render("Experience (XP):", True, (100, 200, 255))
        screen.blit(xp_label, (self.rect.x + 50, self.rect.y + 168))

        # Input XP
        color = (100, 150, 255) if self.active_input == "xp" else (80, 80, 90)
        pygame.draw.rect(screen, color, self.xp_rect, 2)
        pygame.draw.rect(screen, (50, 50, 60), self.xp_rect)
        xp_surf = font.render(self.temp_xp, True, (255, 255, 255))
        screen.blit(xp_surf, (self.xp_rect.x + 10, self.xp_rect.y + 8))

        # Informação
        info = font_small.render("TAB para alternar entre campos | Apenas números", True, (150, 150, 150))
        info_x = self.rect.x + (self.rect.width - info.get_width()) // 2
        screen.blit(info, (info_x, self.rect.y + 220))

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