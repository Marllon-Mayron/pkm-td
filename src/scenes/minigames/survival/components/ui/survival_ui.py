# src/scenes/minigames/survival/components/ui/survival_ui.py
"""
UI especifica do minigame survival - Estilo simples e limpo
"""

import pygame
import math


class SurvivalUI:
    """Renderiza a interface do usuario com estilo simples"""

    def __init__(self, game_scene):
        self.game_scene = game_scene

        self.message = None
        self.message_timer = 0.0
        self.message_color = (255, 255, 255)
        self.message_animation = 0.0

        self.wave_pulse = 0.0

        # Fontes responsivas
        self._fonts = {}
        self._last_window_width = 0
        self._last_window_height = 0

        # Cores do tema
        self.COLORS = {
            'primary': (70, 130, 220),
            'primary_dark': (50, 100, 180),
            'secondary': (45, 55, 85),
            'accent': (255, 180, 50),
            'success': (80, 200, 80),
            'danger': (220, 70, 70),
            'danger_dark': (180, 50, 50),
            'energy': (255, 200, 50),
            'text': (240, 245, 255),
            'text_dim': (160, 170, 200),
            'bg_dark': (15, 18, 28),
            'bg_light': (25, 30, 45),
            'border': (60, 70, 100),
            'border_glow': (100, 150, 220),
        }

    def _get_font(self, size):
        """Obtém fonte com cache"""
        if size not in self._fonts:
            self._fonts[size] = pygame.font.Font(None, size)
        return self._fonts[size]

    def show_message(self, text: str, color: tuple = (255, 255, 255), duration: float = 2.0):
        self.message = text
        self.message_color = color
        self.message_timer = duration
        self.message_animation = 0.0

    def handle_event(self, event) -> bool:
        return False

    def update(self, dt: float):
        if self.message_timer > 0:
            self.message_timer -= dt
            self.message_animation = math.sin(self.message_timer * 12) * 0.2 + 0.8

        self.wave_pulse += dt * 4
        if self.wave_pulse > math.pi * 2:
            self.wave_pulse -= math.pi * 2

    def render(self, screen):
        viewport = self.game_scene.screen_manager
        viewport_x = viewport.viewport_x
        viewport_y = viewport.viewport_y
        vp_width = viewport.viewport_width
        vp_height = viewport.viewport_height

        # Top bar simples
        top_bar_height = 60
        top_rect = pygame.Rect(viewport_x, viewport_y, vp_width, top_bar_height)
        pygame.draw.rect(screen, self.COLORS['bg_dark'], top_rect)
        pygame.draw.line(screen, self.COLORS['border'],
                         (viewport_x, viewport_y + top_bar_height),
                         (viewport_x + vp_width, viewport_y + top_bar_height), 2)

        # Vidas (quadrados simples)
        self._render_lives(screen, viewport_x + 15, viewport_y + 12)

        # Energia (barra simples abaixo das vidas)
        self._render_energy(screen, viewport_x + 15, viewport_y + 40)

        # Score
        self._render_score(screen, viewport_x + vp_width - 130, viewport_y + 12)

        # Wave banner
        self._render_wave_banner(screen, viewport_x + vp_width // 2, viewport_y + 12)

        # Barra de progresso da wave
        self._render_wave_progress(screen, viewport_x, viewport_y + top_bar_height - 3, vp_width)

        # Mensagem central
        self._render_center_message(screen, viewport_x, viewport_y, vp_width, vp_height)

        # Game over / complete
        if self.game_scene.game_state == "game_over":
            self._render_game_overlay(screen, viewport_x, viewport_y, vp_width, vp_height, "GAME OVER",
                                      self.COLORS['danger'])
        elif self.game_scene.game_state == "completed":
            self._render_game_overlay(screen, viewport_x, viewport_y, vp_width, vp_height, "VITORIA!",
                                      self.COLORS['success'])

    def _render_lives(self, screen, x: int, y: int):
        """Renderiza vidas como quadrados simples"""
        lives = self.game_scene.lives
        max_lives = self.game_scene.STARTING_LIVES

        size = 22
        spacing = 6

        for i in range(max_lives):
            rect = pygame.Rect(x + i * (size + spacing), y, size, size)
            if i < lives:
                pygame.draw.rect(screen, self.COLORS['danger'], rect, border_radius=4)
                pygame.draw.rect(screen, (255, 150, 150), rect, 1, border_radius=4)
            else:
                pygame.draw.rect(screen, (50, 55, 75), rect, border_radius=4)
                pygame.draw.rect(screen, self.COLORS['border'], rect, 1, border_radius=4)

    def _render_energy(self, screen, x: int, y: int):
        """Renderiza barra de energia simples"""
        bar_width = 180
        bar_height = 16
        energy = self.game_scene.energy
        energy_percent = energy / 200.0

        # Fundo
        bg_rect = pygame.Rect(x, y, bar_width, bar_height)
        pygame.draw.rect(screen, (40, 45, 65), bg_rect, border_radius=8)
        pygame.draw.rect(screen, self.COLORS['border'], bg_rect, 1, border_radius=8)

        # Preenchimento
        fill_width = int(bar_width * min(1.0, energy_percent))
        if fill_width > 0:
            if energy_percent > 0.6:
                color = self.COLORS['success']
            elif energy_percent > 0.3:
                color = self.COLORS['accent']
            else:
                color = self.COLORS['danger']

            fill_rect = pygame.Rect(x, y, fill_width, bar_height)
            pygame.draw.rect(screen, color, fill_rect, border_radius=8)

        # Texto
        font = self._get_font(12)
        text = font.render(f"{int(energy)}/200", True, self.COLORS['text'])
        screen.blit(text, (x + bar_width + 8, y + 2))

    def _render_score(self, screen, x: int, y: int):
        """Renderiza placar simples"""
        score = self.game_scene.score

        # Fundo
        bg_width = 110
        bg_height = 36
        bg_rect = pygame.Rect(x, y, bg_width, bg_height)
        pygame.draw.rect(screen, self.COLORS['bg_dark'], bg_rect, border_radius=6)
        pygame.draw.rect(screen, self.COLORS['border'], bg_rect, 1, border_radius=6)

        # Texto
        font = self._get_font(10)
        label = font.render("PONTOS", True, self.COLORS['text_dim'])
        screen.blit(label, (x + 8, y + 4))

        font_big = self._get_font(18)
        value = font_big.render(str(score), True, self.COLORS['accent'])
        screen.blit(value, (x + 8, y + 16))

    def _render_wave_banner(self, screen, center_x: int, y: int):
        """Renderiza banner da wave simples"""
        wave_num = self.game_scene.wave_number

        has_boss = False
        if hasattr(self.game_scene, 'wave_manager') and self.game_scene.wave_manager:
            config = getattr(self.game_scene.wave_manager, 'current_wave_config', None)
            # CORREÇÃO: Verifica se é dicionário e acessa a chave 'has_boss'
            if config:
                if isinstance(config, dict):
                    has_boss = config.get('has_boss', False)
                else:
                    has_boss = getattr(config, 'has_boss', False)

        # Texto
        if has_boss:
            wave_text = f"ONDA {wave_num} - CHEFE"
            base_color = self.COLORS['danger']
            text_color = (255, 255, 255)
        else:
            wave_text = f"ONDA {wave_num}"
            base_color = self.COLORS['primary']
            text_color = self.COLORS['text']

        # Banner
        font = self._get_font(18)
        text_surf = font.render(wave_text, True, text_color)
        padding = 20
        banner_width = text_surf.get_width() + padding * 2
        banner_height = 32
        banner_rect = pygame.Rect(center_x - banner_width // 2, y, banner_width, banner_height)

        pygame.draw.rect(screen, base_color, banner_rect, border_radius=6)
        pygame.draw.rect(screen, self.COLORS['border_glow'], banner_rect, 1, border_radius=6)

        screen.blit(text_surf, (center_x - text_surf.get_width() // 2, y + 7))

    def _render_wave_progress(self, screen, x: int, y: int, width: int):
        """Renderiza barra de progresso da wave"""
        if not hasattr(self.game_scene, 'wave_manager') or not self.game_scene.wave_manager:
            return

        wave_manager = self.game_scene.wave_manager

        # Calcula progresso
        if wave_manager.enemies_to_spawn > 0:
            spawned = wave_manager.enemies_spawned_in_wave
            total = wave_manager.enemies_to_spawn
            remaining = len(wave_manager.active_enemies)
            progress = (spawned - remaining) / total if total > 0 else 0
            progress = max(0, min(1.0, progress))
        else:
            progress = 0

        # Barra
        bar_height = 3
        bar_rect = pygame.Rect(x, y, width, bar_height)
        pygame.draw.rect(screen, (40, 45, 65), bar_rect)

        fill_width = int(width * progress)
        if fill_width > 0:
            has_boss = False
            if wave_manager.current_wave_config:
                config = wave_manager.current_wave_config
                if isinstance(config, dict):
                    has_boss = config.get('has_boss', False)
                else:
                    has_boss = getattr(config, 'has_boss', False)

            color = self.COLORS['danger'] if has_boss else self.COLORS['primary']
            fill_rect = pygame.Rect(x, y, fill_width, bar_height)
            pygame.draw.rect(screen, color, fill_rect)

    def _render_center_message(self, screen, vp_x, vp_y, vp_w, vp_h):
        """Renderiza mensagem central simples"""
        if self.message and self.message_timer > 0:
            scale = self.message_animation

            font = self._get_font(28)
            text_surf = font.render(self.message, True, self.message_color)
            shadow = font.render(self.message, True, (0, 0, 0))

            center_x = vp_x + vp_w // 2
            center_y = vp_y + vp_h // 2 - 80

            scaled_w = int(text_surf.get_width() * scale)
            scaled_h = int(text_surf.get_height() * scale)

            if scaled_w > 0 and scaled_h > 0:
                scaled_text = pygame.transform.scale(text_surf, (scaled_w, scaled_h))
                scaled_shadow = pygame.transform.scale(shadow, (scaled_w, scaled_h))

                # Fundo
                bg_padding = 30
                bg_rect = pygame.Rect(center_x - scaled_w // 2 - bg_padding,
                                      center_y - scaled_h // 2 - bg_padding // 2,
                                      scaled_w + bg_padding * 2,
                                      scaled_h + bg_padding)

                bg_surf = pygame.Surface((bg_rect.width, bg_rect.height), pygame.SRCALPHA)
                bg_surf.fill((0, 0, 0, 180))
                pygame.draw.rect(bg_surf, self.COLORS['border'], bg_surf.get_rect(), 2, border_radius=10)
                screen.blit(bg_surf, bg_rect)

                screen.blit(scaled_shadow, (center_x - scaled_w // 2 + 3, center_y - scaled_h // 2 + 3))
                screen.blit(scaled_text, (center_x - scaled_w // 2, center_y - scaled_h // 2))

    def _render_game_overlay(self, screen, vp_x, vp_y, vp_w, vp_h, title, color):
        """Renderiza overlay de game over ou vitoria"""
        # Fundo escurecido
        overlay = pygame.Surface((vp_w, vp_h), pygame.SRCALPHA)
        overlay.fill((0, 0, 0, 200))
        screen.blit(overlay, (vp_x, vp_y))

        # Titulo
        title_font = self._get_font(48)
        title_surf = title_font.render(title, True, color)
        title_x = vp_x + (vp_w - title_surf.get_width()) // 2
        title_y = vp_y + vp_h // 2 - 80
        screen.blit(title_surf, (title_x, title_y))

        # Score final
        score_font = self._get_font(28)
        score_text = f"PONTOS: {self.game_scene.score}"
        score_surf = score_font.render(score_text, True, self.COLORS['accent'])
        score_x = vp_x + (vp_w - score_surf.get_width()) // 2
        score_y = title_y + 60
        screen.blit(score_surf, (score_x, score_y))

        # Instrucao
        inst_font = self._get_font(16)
        inst_text = "Pressione ESC para voltar ao menu"
        inst_surf = inst_font.render(inst_text, True, self.COLORS['text_dim'])
        inst_x = vp_x + (vp_w - inst_surf.get_width()) // 2
        inst_y = score_y + 50
        screen.blit(inst_surf, (inst_x, inst_y))