# src/scenes/game_scene/components/overlays/game_over_overlay.py

import pygame
from .base_overlay import BaseOverlay


class GameOverOverlay(BaseOverlay):
    """Overlay de Game Over"""

    def __init__(self, game_scene):
        super().__init__(game_scene)
        self.target_item_manager = game_scene.target_item_manager

    def handle_event(self, event):
        """Processa eventos do game over"""
        # Só permite ESC para voltar imediatamente
        if event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE:
            self._return_to_team_select()
            return True
        return False

    def update(self, dt):
        """Atualiza o timer de game over"""
        self.timer += dt
        if self.timer >= self.delay:
            self._return_to_team_select()

    def render(self, screen):
        """Renderiza a tela de game over"""
        overlay, viewport = self.create_overlay_surface(200)
        screen.blit(overlay, (viewport.x, viewport.y))

        # Fontes
        font_large = pygame.font.Font(None, 48)
        font_medium = pygame.font.Font(None, 36)
        font_small = pygame.font.Font(None, 24)

        center_x = viewport.x + viewport.width // 2
        center_y = viewport.y + viewport.height // 2

        # Texto GAME OVER
        game_over_text = font_large.render("GAME OVER", True, (255, 0, 0))
        game_over_x = center_x - game_over_text.get_width() // 2
        game_over_y = center_y - 60
        screen.blit(game_over_text, (game_over_x, game_over_y))

        # Texto de itens levados
        items_lost_text = font_medium.render(
            f"{self.target_item_manager.items_stolen} itens foram levados!",
            True, (255, 100, 100)
        )
        items_lost_x = center_x - items_lost_text.get_width() // 2
        items_lost_y = game_over_y + game_over_text.get_height() + 20
        screen.blit(items_lost_text, (items_lost_x, items_lost_y))

        # Timer para voltar
        remaining = max(0, self.delay - self.timer)
        timer_text = font_medium.render(
            f"Voltando em {remaining:.0f}...",
            True, (200, 200, 200)
        )
        timer_x = center_x - timer_text.get_width() // 2
        timer_y = items_lost_y + items_lost_text.get_height() + 20
        screen.blit(timer_text, (timer_x, timer_y))

        # Mensagem de ESC
        esc_text = font_small.render(
            "Pressione ESC para voltar agora",
            True, (150, 150, 150)
        )
        esc_x = center_x - esc_text.get_width() // 2
        esc_y = timer_y + timer_text.get_height() + 30
        screen.blit(esc_text, (esc_x, esc_y))

    def _return_to_team_select(self):
        """Volta para a tela de seleção de time"""
        from src.scenes.team_select_scene import TeamSelectScene

        team_select = TeamSelectScene(
            self.game,
            self.game_scene.phase_info.get("chapter", 1),
            self.game_scene.phase_number
        )
        self.game.current_scene = team_select