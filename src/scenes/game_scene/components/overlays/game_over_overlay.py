# src/scenes/game_scene/components/overlays/game_over_overlay.py

import pygame
from .base_overlay import BaseOverlay


class GameOverOverlay(BaseOverlay):
    """Overlay de Game Over - suporta diferentes motivos"""

    def __init__(self, game_scene, reason="items_stolen"):
        super().__init__(game_scene)
        self.target_item_manager = game_scene.target_item_manager
        self.music_played = False
        self.reason = reason  # "items_stolen" ou "team_defeated"

        # Botão de voltar
        self.button_rect = None
        self.button_hovered = False

    def handle_event(self, event):
        """Processa eventos do game over"""
        # Só permite ESC ou clique no botão para voltar
        if event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE:
            self._return_to_team_select()
            return True

        elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            if self.button_rect and self.button_rect.collidepoint(event.pos):
                self._return_to_team_select()
                return True

        elif event.type == pygame.MOUSEMOTION:
            if self.button_rect:
                self.button_hovered = self.button_rect.collidepoint(event.pos)

        return False

    def update(self, dt):
        """Atualiza - toca música apenas uma vez"""
        if not self.music_played:
            self._play_defeat_music()
            self.music_played = True

    def _play_defeat_music(self):
        """Toca a música de derrota"""
        from src.managers.sound_manager import sound_manager
        sound_manager.play_defeat_music()

    def _stop_music(self):
        """Para a música de derrota"""
        from src.managers.sound_manager import sound_manager
        sound_manager.stop_music(fade_ms=300)
        print(f"[MUSIC] Música de derrota parada")

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

        y_offset = center_y - 80

        # Texto GAME OVER
        game_over_text = font_large.render("GAME OVER", True, (255, 0, 0))
        game_over_x = center_x - game_over_text.get_width() // 2
        screen.blit(game_over_text, (game_over_x, y_offset))
        y_offset += game_over_text.get_height() + 20

        # Mensagem específica do motivo
        if self.reason == "team_defeated":
            reason_text = font_medium.render(
                "Seu time inteiro foi derrotado!",
                True, (255, 100, 100)
            )
        else:
            reason_text = font_medium.render(
                f"{self.target_item_manager.items_stolen} itens foram levados!",
                True, (255, 100, 100)
            )

        reason_x = center_x - reason_text.get_width() // 2
        screen.blit(reason_text, (reason_x, y_offset))
        y_offset += reason_text.get_height() + 40

        # Botão de voltar
        self.button_rect = self._create_button(
            screen, center_x, y_offset,
            "VOLTAR", font_medium
        )

        y_offset = self.button_rect.bottom + 20

        # Mensagem de ESC
        esc_text = font_small.render(
            "Pressione ESC para voltar",
            True, (150, 150, 150)
        )
        esc_x = center_x - esc_text.get_width() // 2
        screen.blit(esc_text, (esc_x, y_offset))

    def _create_button(self, screen, center_x, y, text, font):
        """Cria e desenha um botão"""
        button_width = 200
        button_height = 50
        button_x = center_x - button_width // 2

        button_rect = pygame.Rect(button_x, y, button_width, button_height)

        if self.button_hovered:
            button_color = (180, 60, 60)
            border_color = (220, 80, 80)
        else:
            button_color = (120, 40, 40)
            border_color = (160, 60, 60)

        pygame.draw.rect(screen, button_color, button_rect, border_radius=8)
        pygame.draw.rect(screen, border_color, button_rect, 3, border_radius=8)

        button_text = font.render(text, True, (255, 255, 255))
        text_x = button_rect.centerx - button_text.get_width() // 2
        text_y = button_rect.centery - button_text.get_height() // 2
        screen.blit(button_text, (text_x, text_y))

        return button_rect

    def _return_to_team_select(self):
        """Volta para a tela de seleção de time"""
        from src.scenes.team_select_scene import TeamSelectScene

        # Para a música antes de sair
        self._stop_music()

        self.game_scene.cleanup()

        team_select = TeamSelectScene(
            self.game,
            self.game_scene.phase_info.get("chapter", 1),
            self.game_scene.phase_number
        )
        self.game.current_scene = team_select