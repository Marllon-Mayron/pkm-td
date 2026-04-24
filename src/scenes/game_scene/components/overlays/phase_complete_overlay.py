# src/scenes/game_scene/components/overlays/phase_complete_overlay.py

import pygame
from .base_overlay import BaseOverlay
from src.config.progress import progress_manager
from src.config.phase_catalog import phase_catalog


class PhaseCompleteOverlay(BaseOverlay):
    """Overlay de conclusão de fase - versão organizada"""

    def __init__(self, game_scene):
        super().__init__(game_scene)
        self.phase_info = game_scene.phase_info
        self.phase_id = game_scene.phase_id
        self.phase_number = game_scene.phase_number
        self.music_played = False

        # Dados da conclusão
        self.complete_data = getattr(game_scene, 'phase_complete_data', {})

        # Botão
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
        """Atualiza - toca música apenas uma vez"""
        if not self.music_played:
            self._play_victory_music()
            self.music_played = True

    def _play_victory_music(self):
        """Toca a música de vitória"""
        from src.managers.sounds.sound_manager import sound_manager
        sound_manager.play_victory_music()

    def _stop_music(self):
        """Para a música de vitória"""
        from src.managers.sounds.sound_manager import sound_manager
        sound_manager.stop_music(fade_ms=300)

    def render(self, screen):
        """Renderiza a tela de conclusão"""
        overlay, viewport = self.create_overlay_surface(220)
        screen.blit(overlay, (viewport.x, viewport.y))

        # Fontes
        font_large = pygame.font.Font(None, 48)
        font_medium = pygame.font.Font(None, 32)
        font_small = pygame.font.Font(None, 24)
        font_tiny = pygame.font.Font(None, 18)

        center_x = viewport.x + viewport.width // 2
        center_y = viewport.y + viewport.height // 2

        y_offset = center_y - 110

        # Título
        complete_text = font_large.render("FASE COMPLETA!", True, (255, 215, 0))
        complete_x = center_x - complete_text.get_width() // 2
        screen.blit(complete_text, (complete_x, y_offset))
        y_offset += complete_text.get_height() + 12

        # Nome da fase
        phase_name = self.phase_info.get("name", f"Fase {self.phase_number}")
        name_text = font_medium.render(phase_name, True, (255, 255, 255))
        name_x = center_x - name_text.get_width() // 2
        screen.blit(name_text, (name_x, y_offset))
        y_offset += name_text.get_height() + 25

        # Linha separadora
        pygame.draw.line(screen, (80, 80, 100),
                        (center_x - 180, y_offset),
                        (center_x + 180, y_offset), 1)
        y_offset += 20

        # Recompensas
        base_reward = self.complete_data.get("base_reward", 0)
        gold_from_defeats = self.complete_data.get("gold_from_defeats", 0)
        bonus_amount = self.complete_data.get("bonus_amount", 0)
        gold_total = self.complete_data.get("gold_total", 0)
        total_xp = self.complete_data.get("total_xp", 0)

        # Ouro - Total
        gold_text = font_medium.render(f" Ouro: +{gold_total}", True, (255, 215, 0))
        gold_x = center_x - gold_text.get_width() // 2
        screen.blit(gold_text, (gold_x, y_offset))
        y_offset += gold_text.get_height() + 5

        # Detalhamento do ouro
        if bonus_amount > 0:
            gold_detail = font_tiny.render(
                f"  ({base_reward} da fase + {gold_from_defeats} de derrotas + {bonus_amount} bônus 30%)",
                True, (150, 150, 150)
            )
        else:
            gold_detail = font_tiny.render(
                f"  ({base_reward} da fase + {gold_from_defeats} de derrotas)",
                True, (150, 150, 150)
            )
        gold_detail_x = center_x - gold_detail.get_width() // 2
        screen.blit(gold_detail, (gold_detail_x, y_offset))
        y_offset += gold_detail.get_height() + 15

        # XP
        xp_text = font_small.render(f"  XP: +{total_xp}", True, (100, 200, 255))
        xp_x = center_x - xp_text.get_width() // 2
        screen.blit(xp_text, (xp_x, y_offset))
        y_offset += xp_text.get_height() + 15

        # Bônus por fase perfeita
        if self.complete_data.get("perfect_run", False):
            bonus_text = font_tiny.render("  PERFEITO! Bônus de 30% no gold aplicado!  ",
                                           True, (100, 255, 100))
            bonus_x = center_x - bonus_text.get_width() // 2
            screen.blit(bonus_text, (bonus_x, y_offset))
            y_offset += bonus_text.get_height() + 20
        else:
            y_offset += 20

        # Linha separadora
        pygame.draw.line(screen, (80, 80, 100),
                        (center_x - 180, y_offset),
                        (center_x + 180, y_offset), 1)
        y_offset += 20

        # Próxima fase
        next_phase = progress_manager.get_next_phase(self.phase_id)
        if next_phase:
            chapter, phase = map(int, next_phase.split("-"))
            next_info = phase_catalog.get_phase_info(chapter, phase)
            if next_info:
                next_text = font_tiny.render(f"Próxima fase: {next_info['name']}", True, (150, 150, 255))
                next_x = center_x - next_text.get_width() // 2
                screen.blit(next_text, (next_x, y_offset))
                y_offset += next_text.get_height() + 20

        # Botão
        self.button_rect = self._create_button(
            screen, center_x, y_offset,
            "CONTINUAR", font_medium
        )

        y_offset = self.button_rect.bottom + 15

        # Mensagem de ESC
        esc_text = font_tiny.render("Pressione ESC para continuar", True, (120, 120, 120))
        esc_x = center_x - esc_text.get_width() // 2
        screen.blit(esc_text, (esc_x, y_offset))

    def _create_button(self, screen, center_x, y, text, font):
        """Cria e desenha um botão"""
        button_width = 200
        button_height = 45
        button_x = center_x - button_width // 2

        button_rect = pygame.Rect(button_x, y, button_width, button_height)

        if self.button_hovered:
            button_color = (90, 120, 220)
            border_color = (120, 150, 250)
        else:
            button_color = (50, 70, 150)
            border_color = (70, 100, 200)

        pygame.draw.rect(screen, button_color, button_rect, border_radius=8)
        pygame.draw.rect(screen, border_color, button_rect, 3, border_radius=8)

        button_text = font.render(text, True, (255, 255, 255))
        text_x = button_rect.centerx - button_text.get_width() // 2
        text_y = button_rect.centery - button_text.get_height() // 2
        screen.blit(button_text, (text_x, text_y))

        return button_rect

    def _return_to_phase_select(self):
        """Volta para a seleção de fases"""
        from src.scenes.phase_selector.phase_select_scene import PhaseSelectScene

        self._stop_music()

        if hasattr(self.game_scene, 'cleanup'):
            self.game_scene.cleanup()

        phase_select = PhaseSelectScene(self.game)
        phase_select.refresh_data()

        self.game.current_scene = phase_select