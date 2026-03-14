import pygame
from src.scenes.team_select_scene.utils.constants import COLORS


class NavigationButtons:
    def __init__(self, back_rect, start_rect, prev_rect, next_rect):
        self.back_button = back_rect
        self.start_button = start_rect
        self.prev_page_button = prev_rect
        self.next_page_button = next_rect

    def render(self, screen, font, team_size, current_page, total_pages):
        self._draw_back_button(screen, font)
        self._draw_start_button(screen, font, team_size)

        if total_pages > 1:
            self._draw_page_buttons(screen, font, current_page, total_pages)

    def _draw_back_button(self, screen, font):
        pygame.draw.rect(screen, COLORS['BUTTON']['DEFAULT'], self.back_button, border_radius=8)
        pygame.draw.rect(screen, COLORS['BUTTON']['BORDER'], self.back_button, 2, border_radius=8)

        back_text = font.render("VOLTAR", True, COLORS['TEXT']['GRAY'])
        back_rect = back_text.get_rect(center=self.back_button.center)
        screen.blit(back_text, back_rect)

    def _draw_start_button(self, screen, font, team_size):
        if team_size > 0:
            button_color = COLORS['BUTTON']['START_ACTIVE']
        else:
            button_color = COLORS['BUTTON']['START_INACTIVE']

        pygame.draw.rect(screen, button_color, self.start_button, border_radius=8)
        pygame.draw.rect(screen, (150, 150, 150), self.start_button, 2, border_radius=8)

        start_text = font.render("INICIAR", True, COLORS['TEXT']['WHITE'])
        start_rect = start_text.get_rect(center=self.start_button.center)
        screen.blit(start_text, start_rect)

    def _draw_page_buttons(self, screen, font, current_page, total_pages):
        # Botão anterior
        if current_page > 0:
            prev_color = COLORS['BUTTON']['ACTIVE']
        else:
            prev_color = COLORS['BUTTON']['INACTIVE']

        pygame.draw.rect(screen, prev_color, self.prev_page_button, border_radius=8)
        pygame.draw.rect(screen, (100, 100, 110), self.prev_page_button, 2, border_radius=8)

        prev_text = font.render("ANTERIOR", True, COLORS['TEXT']['GRAY'])
        prev_rect = prev_text.get_rect(center=self.prev_page_button.center)
        screen.blit(prev_text, prev_rect)

        # Botão próximo
        if current_page < total_pages - 1:
            next_color = COLORS['BUTTON']['ACTIVE']
        else:
            next_color = COLORS['BUTTON']['INACTIVE']

        pygame.draw.rect(screen, next_color, self.next_page_button, border_radius=8)
        pygame.draw.rect(screen, (100, 100, 110), self.next_page_button, 2, border_radius=8)

        next_text = font.render("PRÓXIMA", True, COLORS['TEXT']['GRAY'])
        next_rect = next_text.get_rect(center=self.next_page_button.center)
        screen.blit(next_text, next_rect)