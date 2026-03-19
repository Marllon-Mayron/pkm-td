# src/scenes/game_scene/components/overlays/phase_complete_overlay.py

import pygame
from .base_overlay import BaseOverlay
from src.config.progress import progress_manager
from src.config.phase_catalog import phase_catalog


class PhaseCompleteOverlay(BaseOverlay):
    """Overlay de conclusão de fase"""

    def __init__(self, game_scene):
        super().__init__(game_scene)
        self.phase_info = game_scene.phase_info
        self.phase_id = game_scene.phase_id
        self.phase_number = game_scene.phase_number
        self.phase_rewards = game_scene.phase_rewards
        self.target_item_manager = game_scene.target_item_manager

        # Botão de voltar
        self.button_rect = None
        self.button_hovered = False

    def handle_event(self, event):
        """Processa eventos da tela de conclusão"""
        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            if self.button_rect and self.button_rect.collidepoint(event.pos):
                self._return_to_phase_select()
                return True

        elif event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE:
            self._return_to_phase_select()
            return True

        elif event.type == pygame.MOUSEMOTION:
            if self.button_rect:
                self.button_hovered = self.button_rect.collidepoint(event.pos)

        return False

    def update(self, dt):
        """Atualiza o timer automático"""
        self.timer += dt
        if self.timer >= self.delay:
            self._return_to_phase_select()

    def render(self, screen):
        """Renderiza a tela de conclusão"""
        overlay, viewport = self.create_overlay_surface(220)
        screen.blit(overlay, (viewport.x, viewport.y))

        # Fontes
        font_large = pygame.font.Font(None, 64)
        font_medium = pygame.font.Font(None, 36)
        font_small = pygame.font.Font(None, 24)

        center_x = viewport.x + viewport.width // 2
        center_y = viewport.y + viewport.height // 2

        y_offset = center_y - 120

        # Título "FASE COMPLETA!"
        complete_text = font_large.render("FASE COMPLETA!", True, (255, 215, 0))
        complete_x = center_x - complete_text.get_width() // 2
        screen.blit(complete_text, (complete_x, y_offset))
        y_offset += complete_text.get_height() + 20

        # Nome da fase
        phase_name = self.phase_info.get("name", f"Fase {self.phase_number}")
        name_text = font_medium.render(phase_name, True, (200, 200, 200))
        name_x = center_x - name_text.get_width() // 2
        screen.blit(name_text, (name_x, y_offset))
        y_offset += name_text.get_height() + 30

        # Recompensas (lado a lado)
        money_text = font_small.render(f"+${self.phase_rewards['money']}", True, (100, 255, 100))
        exp_text = font_small.render(f"+{self.phase_rewards['experience']} XP", True, (100, 100, 255))

        money_x = center_x - 150
        exp_x = center_x + 50
        screen.blit(money_text, (money_x, y_offset))
        screen.blit(exp_text, (exp_x, y_offset))
        y_offset += money_text.get_height() + 30

        # Próxima fase
        next_phase = progress_manager.get_next_phase(self.phase_id)
        if next_phase:
            chapter, phase = map(int, next_phase.split("-"))
            next_info = phase_catalog.get_phase_info(chapter, phase)
            if next_info:
                next_text = font_small.render(f"Próxima fase: {next_info['name']}", True, (150, 150, 255))
                next_x = center_x - next_text.get_width() // 2
                screen.blit(next_text, (next_x, y_offset))
                y_offset += next_text.get_height() + 30

        # Botão de voltar
        self.button_rect = self._create_button(
            screen, center_x, y_offset + 20,
            "VOLTAR", font_medium
        )
        y_offset = self.button_rect.bottom + 20

        # Timer opcional
        remaining = max(0, self.delay - self.timer)
        if remaining > 0:
            timer_text = font_small.render(
                f"Voltando automaticamente em {remaining:.0f}...",
                True, (150, 150, 150)
            )
            timer_x = center_x - timer_text.get_width() // 2
            screen.blit(timer_text, (timer_x, y_offset))

    def _create_button(self, screen, center_x, y, text, font):
        """Cria e desenha um botão"""
        button_width = 200
        button_height = 50
        button_x = center_x - button_width // 2

        button_rect = pygame.Rect(button_x, y, button_width, button_height)

        # Cores baseadas no hover
        if self.button_hovered:
            button_color = (90, 120, 220)
            border_color = (120, 150, 250)
        else:
            button_color = (50, 70, 150)
            border_color = (70, 100, 200)

        # Desenha botão
        pygame.draw.rect(screen, button_color, button_rect, border_radius=8)
        pygame.draw.rect(screen, border_color, button_rect, 3, border_radius=8)

        # Texto do botão
        button_text = font.render(text, True, (255, 255, 255))
        text_x = button_rect.centerx - button_text.get_width() // 2
        text_y = button_rect.centery - button_text.get_height() // 2
        screen.blit(button_text, (text_x, text_y))

        return button_rect

    def _return_to_phase_select(self):
        """Volta para a seleção de fases"""
        from src.scenes.phase_selector.phase_select_scene import PhaseSelectScene

        # Se a game_scene tiver cleanup, chame-o
        if hasattr(self.game_scene, 'cleanup'):
            self.game_scene.cleanup()

        # Cria nova cena de seleção
        phase_select = PhaseSelectScene(self.game)

        # Opcional: força refresh imediato
        phase_select.refresh_data()

        self.game.current_scene = phase_select