# src/scenes/game_scene/components/overlays/retry_confirm_overlay.py
"""
Sub-overlay que pergunta ao jogador se ele deseja manter os pokémons
nos spots onde estavam antes de rejogar a fase.

É renderizado POR CIMA do GameOverOverlay ou PhaseCompleteOverlay
(não escurece o fundo de novo — apenas desenha a caixa modal).
"""
import pygame
from .base_overlay import BaseOverlay


class RetryConfirmOverlay(BaseOverlay):
    """Pergunta: 'Deseja manter seus pokémons nos lugares que estavam?'"""

    def __init__(self, game_scene, on_confirm_callback):
        super().__init__(game_scene)
        self.on_confirm_callback = on_confirm_callback

        self.yes_button_rect = None
        self.no_button_rect = None
        self.yes_hovered = False
        self.no_hovered = False

        self.fade_in = 0.0
        self.active = True
        self._resolved = False

    # ============================================================
    # EVENTOS
    # ============================================================
    def handle_event(self, event):
        if self._resolved:
            return True

        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            if self.yes_button_rect and self.yes_button_rect.collidepoint(event.pos):
                self._resolve(True)
                return True
            if self.no_button_rect and self.no_button_rect.collidepoint(event.pos):
                self._resolve(False)
                return True

        elif event.type == pygame.KEYDOWN:
            if event.key == pygame.K_ESCAPE:
                self._resolve(False)
                return True
            if event.key in (pygame.K_RETURN, pygame.K_KP_ENTER, pygame.K_y, pygame.K_s):
                self._resolve(True)
                return True
            if event.key in (pygame.K_n,):
                self._resolve(False)
                return True

        elif event.type == pygame.MOUSEMOTION:
            if self.yes_button_rect:
                self.yes_hovered = self.yes_button_rect.collidepoint(event.pos)
            if self.no_button_rect:
                self.no_hovered = self.no_button_rect.collidepoint(event.pos)

        return False

    def update(self, dt):
        if self.fade_in < 1.0:
            self.fade_in = min(1.0, self.fade_in + dt * 3.0)

    def _resolve(self, keep_placement):
        if self._resolved:
            return
        self._resolved = True
        self.active = False
        if self.on_confirm_callback:
            self.on_confirm_callback(keep_placement)

    # ============================================================
    # RENDER
    # ============================================================
    def render(self, screen):
        sm = self.game_scene.screen_manager
        viewport = pygame.Rect(
            sm.viewport_x, sm.viewport_y,
            sm.viewport_width, sm.viewport_height
        )

        # Leve escurecimento extra por cima do overlay pai
        dim = pygame.Surface((viewport.width, viewport.height), pygame.SRCALPHA)
        dim.fill((0, 0, 0, int(120 * self.fade_in)))
        screen.blit(dim, (viewport.x, viewport.y))

        center_x = viewport.x + viewport.width // 2
        center_y = viewport.y + viewport.height // 2

        font_large = pygame.font.Font(None, 36)
        font_small = pygame.font.Font(None, 26)

        # Caixa modal
        box_w = min(620, int(viewport.width * 0.7))
        box_h = 230
        box_rect = pygame.Rect(0, 0, box_w, box_h)
        box_rect.center = (center_x, center_y)

        # Sombra
        shadow = box_rect.copy()
        shadow.x += 4
        shadow.y += 4
        pygame.draw.rect(screen, (0, 0, 0, 120), shadow, border_radius=15)

        pygame.draw.rect(screen, (20, 25, 40), box_rect, border_radius=15)
        pygame.draw.rect(screen, (80, 120, 200), box_rect, 3, border_radius=15)

        # Texto da pergunta
        title1 = font_large.render("Deseja manter seus pokémons", True, (255, 255, 255))
        title2 = font_large.render("nos lugares que estavam?", True, (255, 255, 255))

        screen.blit(title1, (center_x - title1.get_width() // 2, box_rect.y + 30))
        screen.blit(
            title2,
            (center_x - title2.get_width() // 2,
             box_rect.y + 30 + title1.get_height() + 5)
        )

        # Botões
        btn_w = 150
        btn_h = 55
        spacing = 50

        yes_rect = pygame.Rect(0, 0, btn_w, btn_h)
        yes_rect.center = (center_x - btn_w // 2 - spacing // 2, box_rect.bottom - 55)

        no_rect = pygame.Rect(0, 0, btn_w, btn_h)
        no_rect.center = (center_x + btn_w // 2 + spacing // 2, box_rect.bottom - 55)

        self.yes_button_rect = yes_rect
        self.no_button_rect = no_rect

        self._draw_button(screen, yes_rect, "SIM", font_small, self.yes_hovered,
                          (40, 100, 50), (60, 150, 70))
        self._draw_button(screen, no_rect, "NÃO", font_small, self.no_hovered,
                          (120, 40, 40), (180, 60, 60))

    def _draw_button(self, screen, rect, text, font, hovered, base_color, hover_color):
        color = hover_color if hovered else base_color
        pygame.draw.rect(screen, color, rect, border_radius=10)
        pygame.draw.rect(screen, (220, 220, 220), rect, 2, border_radius=10)

        surf = font.render(text, True, (255, 255, 255))
        screen.blit(surf, surf.get_rect(center=rect.center))