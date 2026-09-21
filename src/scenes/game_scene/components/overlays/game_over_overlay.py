# src/scenes/game_scene/components/overlays/game_over_overlay.py

import pygame
from .base_overlay import BaseOverlay


class GameOverOverlay(BaseOverlay):
    """Overlay de Game Over - suporta diferentes motivos"""

    def __init__(self, game_scene, reason="items_stolen"):
        super().__init__(game_scene)
        self.target_item_manager = game_scene.target_item_manager
        self.music_played = False
        self.reason = reason

        self.gold_lost = 0
        self._apply_gold_penalty()

        # Botões
        self.button_rect = None          # VOLTAR (team select)
        self.menu_button_rect = None     # SELECIONAR FASE (phase select)
        self.button_hovered = False
        self.menu_button_hovered = False

    def _apply_gold_penalty(self):
        player = self.game_scene.player
        current_gold = player.money

        if current_gold > 0:
            self.gold_lost = max(1, int(current_gold * 0.1))
            player.money -= self.gold_lost
            print(f"[GAME_OVER] Perdeu {self.gold_lost} gold (10% de {current_gold})")
        else:
            self.gold_lost = 0
            print(f"[GAME_OVER] Sem gold para perder")

    def handle_event(self, event):
        if event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE:
            self._return_to_team_select()
            return True

        elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            if self.button_rect and self.button_rect.collidepoint(event.pos):
                self._return_to_team_select()
                return True
            if self.menu_button_rect and self.menu_button_rect.collidepoint(event.pos):
                self._return_to_phase_select()
                return True

        elif event.type == pygame.MOUSEMOTION:
            if self.button_rect:
                self.button_hovered = self.button_rect.collidepoint(event.pos)
            if self.menu_button_rect:
                self.menu_button_hovered = self.menu_button_rect.collidepoint(event.pos)

        return False

    def update(self, dt):
        if not self.music_played:
            self._play_defeat_music()
            self.music_played = True

    def _play_defeat_music(self):
        from src.managers.sounds.sound_manager import sound_manager
        sound_manager.play_defeat_music()

    def _stop_music(self):
        from src.managers.sounds.sound_manager import sound_manager
        sound_manager.stop_music(fade_ms=300)
        print(f"[MUSIC] Música de derrota parada")

    def render(self, screen):
        overlay, viewport = self.create_overlay_surface(200)
        screen.blit(overlay, (viewport.x, viewport.y))

        font_large = pygame.font.Font(None, 48)
        font_medium = pygame.font.Font(None, 36)
        font_small = pygame.font.Font(None, 24)
        font_gold = pygame.font.Font(None, 28)

        center_x = viewport.x + viewport.width // 2
        center_y = viewport.y + viewport.height // 2

        y_offset = center_y - 100

        # ===== TÍTULO =====
        game_over_text = font_large.render("GAME OVER", True, (255, 0, 0))
        game_over_x = center_x - game_over_text.get_width() // 2
        screen.blit(game_over_text, (game_over_x, y_offset))
        y_offset += game_over_text.get_height() + 15

        # ===== MOTIVO =====
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
        y_offset += reason_text.get_height() + 15

        # ===== GOLD PERDIDO =====
        if self.gold_lost > 0:
            gold_text = font_gold.render(
                f"Você perdeu {self.gold_lost} gold! (10%)",
                True, (255, 215, 0)
            )
        else:
            gold_text = font_gold.render(
                "Você não tinha gold para perder!",
                True, (200, 200, 200)
            )
        gold_x = center_x - gold_text.get_width() // 2
        screen.blit(gold_text, (gold_x, y_offset))
        y_offset += gold_text.get_height() + 30

        # ===== BOTÕES (lado a lado) =====
        button_width = 220
        button_height = 50
        spacing = 30

        total_width = button_width * 2 + spacing
        left_x = center_x - total_width // 2

        self.button_rect = self._draw_button(
            screen, left_x, y_offset, button_width, button_height,
            "TIME", font_medium, self.button_hovered,
            base_color=(120, 40, 40), hover_color=(180, 60, 60),
            border_color=(160, 60, 60), hover_border=(220, 80, 80)
        )

        self.menu_button_rect = self._draw_button(
            screen, left_x + button_width + spacing, y_offset,
            button_width, button_height,
            "SELECIONAR FASE", font_small, self.menu_button_hovered,
            base_color=(40, 60, 120), hover_color=(60, 90, 180),
            border_color=(60, 90, 160), hover_border=(80, 120, 220)
        )

        y_offset = self.button_rect.bottom + 20

        esc_text = font_small.render(
            "Pressione ESC para voltar à seleção de time",
            True, (150, 150, 150)
        )
        esc_x = center_x - esc_text.get_width() // 2
        screen.blit(esc_text, (esc_x, y_offset))

    def _draw_button(self, screen, x, y, w, h, text, font, hovered,
                     base_color, hover_color, border_color, hover_border):
        """Desenha um botão genérico com hover"""
        rect = pygame.Rect(x, y, w, h)
        color = hover_color if hovered else base_color
        border = hover_border if hovered else border_color

        pygame.draw.rect(screen, color, rect, border_radius=8)
        pygame.draw.rect(screen, border, rect, 3, border_radius=8)

        text_surf = font.render(text, True, (255, 255, 255))
        screen.blit(
            text_surf,
            (rect.centerx - text_surf.get_width() // 2,
             rect.centery - text_surf.get_height() // 2)
        )
        return rect

    def _return_to_team_select(self):
        """Volta para a tela de seleção de time"""
        from src.scenes.team_select_scene.team_select_scene import TeamSelectScene

        self._stop_music()
        self.game_scene.cleanup()

        team_select = TeamSelectScene(
            self.game,
            self.game_scene.phase_info.get("chapter", 1),
            self.game_scene.phase_number
        )
        self.game.current_scene = team_select

    def _return_to_phase_select(self):
        """Volta para a tela de seleção de fase (mesmo caminho do start_game do menu)"""
        from src.config.progress import progress_manager
        from src.scenes.phase_selector.phase_select_scene import PhaseSelectScene

        self._stop_music()
        self.game_scene.cleanup()

        # Mesmo fluxo do MenuScene.start_game() quando o jogador já tem starter:
        progress_manager._load_settings_from_save()

        phase_select = PhaseSelectScene(self.game)
        phase_select._needs_refresh = True   # força refresh dos dados do time/box

        self.game.current_scene = phase_select

        print("[GAME_OVER] Voltando para PhaseSelectScene")