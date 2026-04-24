# src/scenes/game_scene/components/overlays/evolution_overlay.py

import pygame
import math
from src.scenes.game_scene.components.overlays.base_overlay import BaseOverlay

_FONT_CACHE = {}


class EvolutionOverlay(BaseOverlay):
    """Overlay exibido quando um Pokémon está apto para evoluir"""

    def __init__(self, game_scene, pokemon, evolution_data):
        super().__init__(game_scene)
        self.pokemon = pokemon
        self.evolution_data = evolution_data
        self.evolve_to_id = evolution_data["evolve_to"]
        self.animation_state = "waiting"  # waiting, evolving, complete
        self.animation_timer = 0

        # Guarda os nomes ANTES da evolução
        self.original_name = pokemon.name.upper()

        # Dados do Pokémon evoluído
        from src.data.pokedex import Pokedex
        self.pokedex = Pokedex()
        self.evolved_name = self.pokedex.get_name(self.evolve_to_id).upper()

        # Carrega sprites
        self._load_sprites()

        # Botões
        self.evolve_button_rect = None
        self.cancel_button_rect = None
        self.continue_button_rect = None
        self.evolve_hovered = False
        self.cancel_hovered = False
        self.continue_hovered = False

        # Dimensões do modal
        self.modal_width = 600
        self.modal_height = 500
        self.modal_padding = 30

        # Cores
        self.colors = {
            'primary': (100, 150, 255),
            'accent': (255, 215, 0),
            'success': (100, 200, 100),
            'danger': (255, 100, 100),
            'bg_dark': (20, 25, 45),
            'bg_medium': (30, 35, 55),
            'bg_light': (45, 50, 75),
            'bg_card': (38, 43, 68),
            'text': (255, 255, 255),
            'text_dim': (200, 200, 220),
            'text_muted': (150, 155, 180),
            'border': (80, 100, 140),
        }

        print(f"[EVOLUTION] Overlay criado para {self.original_name} -> {self.evolved_name}")

    def _get_font(self, size, bold=False):
        key = (size, bold)
        if key not in _FONT_CACHE:
            font = pygame.font.Font(None, size)
            if bold:
                font.set_bold(True)
            _FONT_CACHE[key] = font
        return _FONT_CACHE[key]

    def _load_sprites(self):
        """Carrega os sprites"""
        self.current_sprite = self.pokemon.ui_sprite

        # Sprite evoluído
        if self.pokemon.is_shiny:
            self.evolved_sprite = self.pokedex.get_sprite(self.evolve_to_id, "front", shiny=True)
        else:
            self.evolved_sprite = self.pokedex.get_sprite(self.evolve_to_id, "front", shiny=False)

        if not self.evolved_sprite:
            self.evolved_sprite = self.current_sprite

    def handle_event(self, event):
        """Processa eventos"""
        if not self.active:
            return False

        # Estado de evolução completa - botão continuar
        if self.animation_state == "complete":
            if event.type == pygame.KEYDOWN:
                if event.key in (pygame.K_RETURN, pygame.K_SPACE, pygame.K_ESCAPE):
                    self.close()
                    return True
            elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                if self.continue_button_rect and self.continue_button_rect.collidepoint(event.pos):
                    self.close()
                    return True
            return False

        # Estado aguardando confirmação
        if event.type == pygame.KEYDOWN:
            if event.key == pygame.K_ESCAPE:
                self.cancel_evolution()
                return True
            elif event.key in (pygame.K_RETURN, pygame.K_SPACE):
                self.start_evolution()
                return True

        elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            if self.evolve_button_rect and self.evolve_button_rect.collidepoint(event.pos):
                self.start_evolution()
                return True
            if self.cancel_button_rect and self.cancel_button_rect.collidepoint(event.pos):
                self.cancel_evolution()
                return True

        elif event.type == pygame.MOUSEMOTION:
            if self.evolve_button_rect:
                self.evolve_hovered = self.evolve_button_rect.collidepoint(event.pos)
            if self.cancel_button_rect:
                self.cancel_hovered = self.cancel_button_rect.collidepoint(event.pos)

        return False

    def update(self, dt):
        """Atualiza animação"""
        self.animation_timer += dt

        if self.animation_state == "evolving":
            # Animação de 3 segundos
            if self.animation_timer >= 3.0:
                self.complete_evolution()

    def start_evolution(self):
        """Inicia a animação de evolução"""
        self.animation_state = "evolving"
        self.animation_timer = 0
        self._play_evolution_sound()

    def complete_evolution(self):
        """Completa a evolução"""
        # Aplica a evolução
        self.pokemon._perform_evolution(self.evolve_to_id)

        # Atualiza dados do jogador
        if hasattr(self.game_scene, 'player'):
            self.game_scene.player.caught_pokemon.add(self.evolve_to_id)
            self.game_scene.player.register_seen(self.evolve_to_id)
            self.game_scene.player.auto_save()

        self.animation_state = "complete"
        self.animation_timer = 0

    def cancel_evolution(self):
        """Cancela a evolução"""
        self.active = False
        self.game_scene.close_evolution_overlay(cancel=True)

    def close(self):
        """Fecha o overlay"""
        self.active = False
        self.game_scene.close_evolution_overlay(cancel=False)

    def _play_evolution_sound(self):
        try:
            from managers.sounds.sound_manager import sound_manager
            sound_manager.play_evolution_sound()
        except:
            pass

    def render(self, screen):
        if not self.active:
            return

        viewport = self.get_viewport_rect()

        # Fundo escuro
        overlay = pygame.Surface((viewport.width, viewport.height))
        overlay.set_alpha(200)
        overlay.fill((0, 0, 0))
        screen.blit(overlay, (viewport.x, viewport.y))

        # Centraliza modal
        modal_x = viewport.x + (viewport.width - self.modal_width) // 2
        modal_y = viewport.y + (viewport.height - self.modal_height) // 2
        modal_rect = pygame.Rect(modal_x, modal_y, self.modal_width, self.modal_height)

        # Fundo do modal
        bg_rect = modal_rect.inflate(-2, -2)
        pygame.draw.rect(screen, self.colors['bg_dark'], bg_rect, border_radius=20)
        pygame.draw.rect(screen, self.colors['primary'], modal_rect, 3, border_radius=20)

        # Renderiza baseado no estado
        if self.animation_state == "waiting":
            self._render_waiting(screen, modal_rect)
        elif self.animation_state == "evolving":
            self._render_evolving(screen, modal_rect)
        elif self.animation_state == "complete":
            self._render_complete(screen, modal_rect)

    def _render_waiting(self, screen, modal_rect):
        """Tela aguardando confirmação do jogador"""
        content_rect = pygame.Rect(
            modal_rect.x + self.modal_padding,
            modal_rect.y + self.modal_padding,
            modal_rect.width - (self.modal_padding * 2),
            modal_rect.height - (self.modal_padding * 2)
        )

        center_x = content_rect.centerx

        # Título
        font_title = self._get_font(28, True)
        title = font_title.render(f"{self.original_name} ESTÁ EVOLUINDO!", True, self.colors['primary'])
        title_x = center_x - title.get_width() // 2
        screen.blit(title, (title_x, content_rect.y + 10))

        # Sprite atual
        sprite_y = content_rect.y + 100
        sprite_size = 150
        self._render_centered_sprite(screen, self.current_sprite, center_x, sprite_y, sprite_size)

        # Nome do Pokémon
        font_name = self._get_font(24, True)
        name_surf = font_name.render(self.original_name, True, self.colors['text'])
        name_x = center_x - name_surf.get_width() // 2
        screen.blit(name_surf, (name_x, sprite_y + sprite_size + 20))

        # Seta indicando evolução
        font_arrow = self._get_font(40, True)
        arrow = font_arrow.render("|", True, self.colors['accent'])
        arrow_x = center_x - arrow.get_width() // 2
        screen.blit(arrow, (arrow_x, sprite_y + sprite_size + 55))

        # Nome evoluído
        font_evolved = self._get_font(20, True)
        evolved_surf = font_evolved.render(f" {self.evolved_name}", True, self.colors['accent'])
        evolved_x = center_x - evolved_surf.get_width() // 2
        screen.blit(evolved_surf, (evolved_x, sprite_y + sprite_size + 90))

        # Botões
        self._render_waiting_buttons(screen, content_rect)

    def _render_evolving(self, screen, modal_rect):
        """Tela de animação de evolução"""
        content_rect = pygame.Rect(
            modal_rect.x + self.modal_padding,
            modal_rect.y + self.modal_padding,
            modal_rect.width - (self.modal_padding * 2),
            modal_rect.height - (self.modal_padding * 2)
        )

        center_x = content_rect.centerx

        # Título
        font_title = self._get_font(32, True)
        title = font_title.render("EVOLUINDO...", True, self.colors['accent'])
        title_x = center_x - title.get_width() // 2
        screen.blit(title, (title_x, content_rect.y + 10))

        # Animação de transformação
        sprite_y = content_rect.y + 100
        sprite_size = 150

        # 3 segundos de animação, 12 ciclos de piscada (alterna a cada 0.25s)
        total_time = 3.0
        cycles = 12  # Número de trocas de sprite
        cycle_duration = total_time / cycles

        # Calcula em qual ciclo estamos (0 a cycles-1)
        current_cycle = int(self.animation_timer / cycle_duration)

        # Garante que não ultrapasse o número de ciclos
        if current_cycle >= cycles:
            current_cycle = cycles - 1

        # Alterna entre sprite original e evoluído a cada ciclo
        # Ciclos pares = sprite original, ímpares = sprite evoluído
        if current_cycle % 2 == 0:
            sprite_to_show = self.current_sprite
        else:
            sprite_to_show = self.evolved_sprite

        # Efeito de brilho pulsante (quanto mais perto do fim, mais forte)
        glow_intensity = min(1.0, self.animation_timer / total_time)
        pulse = abs(math.sin(self.animation_timer * 15)) * (8 + glow_intensity * 8)

        self._render_centered_sprite(screen, sprite_to_show, center_x, sprite_y, sprite_size,
                                     glowing=True, glow_intensity=glow_intensity)

        # Texto "???" durante a transformação
        font_question = self._get_font(24, True)
        question = font_question.render("???", True, self.colors['accent'])
        question_x = center_x - question.get_width() // 2
        screen.blit(question, (question_x, sprite_y + sprite_size + 30))

        # Barra de progresso da evolução
        bar_width = 300
        bar_height = 8
        bar_x = center_x - bar_width // 2
        bar_y = sprite_y + sprite_size + 80

        # Fundo da barra
        pygame.draw.rect(screen, (60, 60, 70), (bar_x, bar_y, bar_width, bar_height), border_radius=4)

        # Progresso
        progress = min(1.0, self.animation_timer / total_time)
        progress_width = int(bar_width * progress)
        if progress_width > 0:
            pygame.draw.rect(screen, self.colors['accent'], (bar_x, bar_y, progress_width, bar_height), border_radius=4)

        # Texto do progresso
        font_progress = self._get_font(12)
        progress_text = font_progress.render(f"{int(progress * 100)}%", True, self.colors['text_muted'])
        progress_text_x = center_x - progress_text.get_width() // 2
        screen.blit(progress_text, (progress_text_x, bar_y + bar_height + 4))

    def _render_complete(self, screen, modal_rect):
        """Tela de evolução completa"""
        content_rect = pygame.Rect(
            modal_rect.x + self.modal_padding,
            modal_rect.y + self.modal_padding,
            modal_rect.width - (self.modal_padding * 2),
            modal_rect.height - (self.modal_padding * 2)
        )

        center_x = content_rect.centerx

        # Título
        font_title = self._get_font(36, True)
        title = font_title.render("EVOLUIU!", True, self.colors['success'])
        title_x = center_x - title.get_width() // 2
        screen.blit(title, (title_x, content_rect.y + 20))

        # Sprite evoluído
        sprite_y = content_rect.y + 100
        sprite_size = 150
        self._render_centered_sprite(screen, self.evolved_sprite, center_x, sprite_y, sprite_size)

        # Mensagem de parabéns
        font_msg = self._get_font(20)
        msg = f"Parabéns! Seu {self.original_name} evoluiu para {self.evolved_name}!"

        # Quebra de linha
        words = msg.split()
        lines = []
        current_line = []
        for word in words:
            test_line = ' '.join(current_line + [word])
            test_surf = font_msg.render(test_line, True, self.colors['text'])
            if test_surf.get_width() > content_rect.width - 40:
                if current_line:
                    lines.append(' '.join(current_line))
                    current_line = [word]
                else:
                    lines.append(word)
            else:
                current_line.append(word)
        if current_line:
            lines.append(' '.join(current_line))

        msg_y = sprite_y + sprite_size + 30
        for line in lines:
            line_surf = font_msg.render(line, True, self.colors['text'])
            line_x = center_x - line_surf.get_width() // 2
            screen.blit(line_surf, (line_x, msg_y))
            msg_y += 28

        # Botão continuar
        self._render_continue_button(screen, content_rect)

    def _render_centered_sprite(self, screen, sprite, center_x, y, size, glowing=False, glow_intensity=1.0):
        """Renderiza sprite centralizado"""
        if not sprite:
            return

        orig_w, orig_h = sprite.get_width(), sprite.get_height()
        scale = min(size / orig_w, size / orig_h)
        new_w = int(orig_w * scale)
        new_h = int(orig_h * scale)

        scaled = pygame.transform.scale(sprite, (new_w, new_h))

        sprite_x = center_x - new_w // 2
        sprite_y = y + (size - new_h) // 2
        center_y = y + size // 2

        # Efeito de brilho durante evolução
        if glowing:
            pulse = abs(math.sin(self.animation_timer * 12)) * (8 + glow_intensity * 8)
            glow_radius = max(new_w, new_h) // 2 + int(pulse) + 12
            glow_surface = pygame.Surface((glow_radius * 2, glow_radius * 2), pygame.SRCALPHA)
            glow_alpha = int(100 + pulse * 8)
            pygame.draw.circle(glow_surface, (*self.colors['accent'], glow_alpha),
                               (glow_radius, glow_radius), glow_radius)
            screen.blit(glow_surface, (center_x - glow_radius, center_y - glow_radius))

        # Fundo
        circle_radius = max(new_w, new_h) // 2 + 8
        pygame.draw.circle(screen, (*self.colors['bg_light'], 180), (center_x, center_y), circle_radius)
        pygame.draw.circle(screen, self.colors['border'], (center_x, center_y), circle_radius, 2)

        screen.blit(scaled, (sprite_x, sprite_y))

    def _render_waiting_buttons(self, screen, content_rect):
        """Botões de confirmar e cancelar"""
        center_x = content_rect.centerx
        button_width = 180
        button_height = 45
        spacing = 20
        total_width = button_width * 2 + spacing

        evolve_x = center_x - total_width // 2
        cancel_x = evolve_x + button_width + spacing
        button_y = content_rect.bottom - 60

        self.evolve_button_rect = pygame.Rect(evolve_x, button_y, button_width, button_height)
        self.cancel_button_rect = pygame.Rect(cancel_x, button_y, button_width, button_height)

        # Botão EVOLUIR
        color = (70, 150, 70) if self.evolve_hovered else (40, 100, 40)
        pygame.draw.rect(screen, color, self.evolve_button_rect, border_radius=12)
        pygame.draw.rect(screen, (100, 200, 100), self.evolve_button_rect, 2, border_radius=12)

        font = self._get_font(22, True)
        text = font.render("EVOLUIR", True, (255, 255, 255))
        text_x = self.evolve_button_rect.centerx - text.get_width() // 2
        text_y = self.evolve_button_rect.centery - text.get_height() // 2
        screen.blit(text, (text_x, text_y))

        # Botão CANCELAR
        color = (150, 70, 70) if self.cancel_hovered else (100, 40, 40)
        pygame.draw.rect(screen, color, self.cancel_button_rect, border_radius=12)
        pygame.draw.rect(screen, (200, 100, 100), self.cancel_button_rect, 2, border_radius=12)

        text = font.render("CANCELAR", True, (255, 255, 255))
        text_x = self.cancel_button_rect.centerx - text.get_width() // 2
        text_y = self.cancel_button_rect.centery - text.get_height() // 2
        screen.blit(text, (text_x, text_y))

    def _render_continue_button(self, screen, content_rect):
        """Botão continuar após evolução"""
        center_x = content_rect.centerx
        button_width = 200
        button_height = 50
        button_x = center_x - button_width // 2
        button_y = content_rect.bottom - 70

        self.continue_button_rect = pygame.Rect(button_x, button_y, button_width, button_height)

        # Botão CONTINUAR
        color = (70, 100, 150) if self.continue_hovered else (40, 70, 100)
        pygame.draw.rect(screen, color, self.continue_button_rect, border_radius=12)
        pygame.draw.rect(screen, (100, 150, 200), self.continue_button_rect, 2, border_radius=12)

        font = self._get_font(24, True)
        text = font.render("CONTINUAR", True, (255, 255, 255))
        text_x = self.continue_button_rect.centerx - text.get_width() // 2
        text_y = self.continue_button_rect.centery - text.get_height() // 2
        screen.blit(text, (text_x, text_y))

        # Dica
        font_hint = self._get_font(12)
        hint = font_hint.render("Pressione ESPAÇO ou ENTER", True, self.colors['text_muted'])
        hint_x = center_x - hint.get_width() // 2
        screen.blit(hint, (hint_x, button_y + button_height + 8))