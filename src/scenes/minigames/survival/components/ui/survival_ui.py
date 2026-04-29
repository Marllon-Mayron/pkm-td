# src/scenes/minigames/survival/components/ui/survival_ui.py
"""
UI especifica do minigame survival - Estilo moderno com wave no topo
"""

import pygame
import math


class SurvivalUI:
    """Renderiza a interface do usuario - wave no topo, stats na parte inferior"""

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
            'primary_glow': (100, 160, 250),
            'secondary': (45, 55, 85),
            'accent': (255, 180, 50),
            'success': (80, 200, 80),
            'danger': (220, 70, 70),
            'danger_dark': (180, 50, 50),
            'energy': (255, 200, 50),
            'energy_glow': (255, 220, 100),
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

        # ===== TOPO: WAVE BANNER =====
        top_bar_height = 100
        top_y = viewport_y
        self._render_top_bar(screen, viewport_x, top_y, vp_width, top_bar_height)

        # ===== WAVE BANNER NO CENTRO SUPERIOR =====
        center_x = viewport_x + vp_width // 2
        self._render_wave_banner(screen, center_x, top_y + 15)

        # ===== BARRA INFERIOR (VIDAS + ENERGIA + SCORE) =====
        bottom_bar_height = 110
        bottom_y = viewport_y + vp_height - bottom_bar_height
        self._render_bottom_bar(screen, viewport_x, bottom_y, vp_width, bottom_bar_height)

        # ===== MENSAGEM CENTRAL (flutuante) =====
        self._render_center_message(screen, viewport_x, viewport_y, vp_width, vp_height)

        # ===== GAME OVER / COMPLETED (overlay central) =====
        if self.game_scene.game_state == "game_over":
            self._render_game_overlay(screen, viewport_x, viewport_y, vp_width, vp_height, "GAME OVER",
                                      self.COLORS['danger'])
        elif self.game_scene.game_state == "completed":
            self._render_game_overlay(screen, viewport_x, viewport_y, vp_width, vp_height, "VITÓRIA!",
                                      self.COLORS['success'])

    def _render_top_bar(self, screen, x: int, y: int, width: int, height: int):
        """Renderiza a barra superior com gradiente"""
        # Fundo da barra superior
        top_rect = pygame.Rect(x, y, width, height)
        pygame.draw.rect(screen, self.COLORS['bg_dark'], top_rect)
        pygame.draw.line(screen, self.COLORS['border_glow'],
                         (x, y + height),
                         (x + width, y + height), 2)

        # Gradiente sutil na parte inferior da barra
        for i in range(6):
            alpha = 35 - i * 6
            grad_rect = pygame.Rect(x, y + height - i - 1, width, 1)
            grad_surf = pygame.Surface((width, 1), pygame.SRCALPHA)
            grad_surf.fill((100, 150, 220, max(0, alpha)))
            screen.blit(grad_surf, (x, y + height - i - 1))

    def _render_wave_banner(self, screen, center_x: int, y: int):
        """Renderiza banner da wave no centro superior com fonte GRANDE"""
        # ===== PEGA A WAVE ATUAL CORRETAMENTE =====
        if self.game_scene.wave_manager:
            current_wave = self.game_scene.wave_manager.current_wave
            total_waves = self.game_scene.total_waves
        else:
            current_wave = self.game_scene.wave_number
            total_waves = self.game_scene.total_waves

        has_boss = False
        if hasattr(self.game_scene, 'wave_manager') and self.game_scene.wave_manager:
            config = getattr(self.game_scene.wave_manager, 'current_wave_config', None)
            if config:
                if isinstance(config, dict):
                    has_boss = config.get('has_boss', False)
                else:
                    has_boss = getattr(config, 'has_boss', False)

        # Pulse animation para waves com chefe
        pulse = abs(math.sin(self.wave_pulse)) if has_boss else 1.0
        pulse_scale = 0.94 + (0.06 * pulse)

        # Texto principal (FONTE MAIOR)
        font_main = self._get_font(42)
        wave_text = f"ONDA {current_wave}"
        text_surf = font_main.render(wave_text, True, self.COLORS['text'])

        # Texto do total (fonte maior também)
        font_total = self._get_font(24)
        total_text = f"/ {total_waves}"
        total_surf = font_total.render(total_text, True, self.COLORS['text_dim'])

        # Banner
        padding = 50
        banner_width = text_surf.get_width() + total_surf.get_width() + padding * 2 + 15
        banner_height = 70

        if has_boss:
            banner_width = max(banner_width, 280)

        banner_rect = pygame.Rect(center_x - int(banner_width * pulse_scale) // 2,
                                  y,
                                  int(banner_width * pulse_scale),
                                  int(banner_height * pulse_scale))

        # Cor baseada em boss
        if has_boss:
            base_color = self.COLORS['danger']
        else:
            base_color = self.COLORS['primary']

        # Fundo com efeito de brilho
        pygame.draw.rect(screen, base_color, banner_rect, border_radius=15)
        pygame.draw.rect(screen, self.COLORS['border_glow'], banner_rect, 3, border_radius=15)

        # Texto da wave
        text_x = banner_rect.centerx - (text_surf.get_width() + total_surf.get_width()) // 2
        text_y = banner_rect.centery - text_surf.get_height() // 2
        screen.blit(text_surf, (text_x, text_y))
        screen.blit(total_surf, (text_x + text_surf.get_width() + 10,
                                 text_y + text_surf.get_height() - total_surf.get_height() - 3))

        # Texto de CHEFE
        if has_boss:
            font_boss = self._get_font(16)
            boss_text = "⚔️ CHEFE ⚔️"
            boss_surf = font_boss.render(boss_text, True, (255, 150, 150))
            boss_x = banner_rect.centerx - boss_surf.get_width() // 2
            boss_y = banner_rect.bottom + 8
            screen.blit(boss_surf, (boss_x, boss_y))

        # Barra de progresso da wave
        progress_y = y + banner_height + 20
        self._render_wave_progress(screen, center_x - 180, progress_y, 360)

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

        # Label com contador (fonte maior)
        font_label = self._get_font(14)
        killed = wave_manager.enemies_killed
        remaining_count = len(wave_manager.active_enemies)
        label_text = f"INIMIGOS: {killed} derrotados  |  Restantes: {remaining_count}"
        label = font_label.render(label_text, True, self.COLORS['text_dim'])

        # Centraliza o label
        label_x = x + (width - label.get_width()) // 2
        screen.blit(label, (label_x, y - 22))

        # Fundo da barra
        bar_height = 10
        bg_rect = pygame.Rect(x, y, width, bar_height)
        pygame.draw.rect(screen, (40, 45, 65), bg_rect, border_radius=5)

        # Preenchimento
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
            pygame.draw.rect(screen, color, fill_rect, border_radius=5)

        # Porcentagem (fonte maior)
        font_percent = self._get_font(14)
        percent_text = font_percent.render(f"{int(progress * 100)}%", True, self.COLORS['text_dim'])
        screen.blit(percent_text, (x + width + 15, y - 4))

    def _render_bottom_bar(self, screen, x: int, y: int, width: int, height: int):
        """Renderiza a barra inferior - Vidas e Energia juntos na esquerda, Score na direita"""
        # Fundo da barra inferior
        bottom_rect = pygame.Rect(x, y, width, height)
        pygame.draw.rect(screen, self.COLORS['bg_dark'], bottom_rect)
        pygame.draw.line(screen, self.COLORS['border_glow'],
                         (x, y),
                         (x + width, y), 3)

        # Gradiente sutil no topo da barra
        for i in range(6):
            alpha = 35 - i * 6
            grad_rect = pygame.Rect(x, y + i, width, 1)
            grad_surf = pygame.Surface((width, 1), pygame.SRCALPHA)
            grad_surf.fill((100, 150, 220, max(0, alpha)))
            screen.blit(grad_surf, (x, y + i))

        # ===== LADO ESQUERDO: VIDAS (em cima) + ENERGIA (embaixo) =====
        left_x = x + 25
        left_y = y + 15

        # Vidas (em cima)
        self._render_lives(screen, left_x, left_y)

        # Energia (embaixo das vidas)
        self._render_energy(screen, left_x, left_y + 55)

        # ===== LADO DIREITO: SCORE =====
        right_x = x + width - 230
        right_y = y + 20
        self._render_score(screen, right_x, right_y)

    def _render_lives(self, screen, x: int, y: int):
        """Renderiza vidas"""
        lives = self.game_scene.lives
        max_lives = self.game_scene.STARTING_LIVES

        # Label
        font_label = self._get_font(13)
        label = font_label.render("VIDAS", True, self.COLORS['text_dim'])
        screen.blit(label, (x, y - 14))

        size = 30
        spacing = 8

        for i in range(max_lives):
            rect = pygame.Rect(x + i * (size + spacing), y, size, size)

            if i < lives:
                pygame.draw.rect(screen, self.COLORS['danger'], rect, border_radius=8)
                pygame.draw.rect(screen, (255, 120, 120), rect, 2, border_radius=8)
                inner_rect = pygame.Rect(rect.x + 4, rect.y + 4, rect.width - 8, rect.height - 8)
                pygame.draw.rect(screen, (255, 100, 100, 100), inner_rect, border_radius=4)
            else:
                pygame.draw.rect(screen, (50, 55, 75), rect, border_radius=8)
                pygame.draw.rect(screen, self.COLORS['border'], rect, 2, border_radius=8)

    def _render_energy(self, screen, x: int, y: int):
        """Renderiza barra de energia"""
        energy = self.game_scene.energy
        max_energy = self.game_scene.MAX_ENERGY
        energy_percent = energy / max_energy

        bar_width = 220
        bar_height = 24

        # Label
        font_label = self._get_font(13)
        label = font_label.render("ENERGIA", True, self.COLORS['text_dim'])
        screen.blit(label, (x, y - 14))

        # Fundo da barra
        bg_rect = pygame.Rect(x, y, bar_width, bar_height)
        pygame.draw.rect(screen, (40, 45, 65), bg_rect, border_radius=12)
        pygame.draw.rect(screen, self.COLORS['border'], bg_rect, 2, border_radius=12)

        # Preenchimento
        fill_width = int(bar_width * energy_percent)
        if fill_width > 0:
            if energy_percent > 0.6:
                color = self.COLORS['success']
            elif energy_percent > 0.3:
                color = self.COLORS['accent']
            else:
                color = self.COLORS['danger']

            fill_rect = pygame.Rect(x, y, fill_width, bar_height)
            pygame.draw.rect(screen, color, fill_rect, border_radius=12)

            # Efeito de brilho
            if fill_width > 6:
                glow_rect = pygame.Rect(x + fill_width - 6, y, 6, bar_height)
                glow_color = (min(255, color[0] + 60), min(255, color[1] + 60), min(255, color[2] + 60))
                pygame.draw.rect(screen, glow_color, glow_rect, border_radius=12)

        # Valor
        font_value = self._get_font(16)
        value_text = font_value.render(f"{int(energy)}/{int(max_energy)}", True, self.COLORS['text'])
        value_x = x + bar_width + 12
        screen.blit(value_text, (value_x, y + 4))

    def _render_score(self, screen, x: int, y: int):
        """Renderiza placar"""
        score = self.game_scene.score

        bg_width = 210
        bg_height = 75
        bg_rect = pygame.Rect(x, y, bg_width, bg_height)

        # Fundo
        pygame.draw.rect(screen, self.COLORS['bg_light'], bg_rect, border_radius=12)
        pygame.draw.rect(screen, self.COLORS['border_glow'], bg_rect, 2, border_radius=12)

        # Label
        font_label = self._get_font(13)
        label = font_label.render("PONTUAÇÃO", True, self.COLORS['text_dim'])
        label_x = x + (bg_width - label.get_width()) // 2
        screen.blit(label, (label_x, y + 8))

        # Valor
        font_value = self._get_font(34)
        formatted_score = f"{score:,}".replace(",", ".")
        value_text = font_value.render(formatted_score, True, self.COLORS['accent'])
        value_x = x + (bg_width - value_text.get_width()) // 2
        screen.blit(value_text, (value_x, y + 32))

        # Efeito de brilho
        if score > 0:
            glow_surf = pygame.Surface((bg_width, bg_height), pygame.SRCALPHA)
            glow_color = (255, 180, 50, 35)
            glow_surf.fill(glow_color)
            screen.blit(glow_surf, (x, y))

    def _render_center_message(self, screen, vp_x, vp_y, vp_w, vp_h):
        """Renderiza mensagem central flutuante"""
        if self.message and self.message_timer > 0:
            scale = self.message_animation

            font = self._get_font(40)
            text_surf = font.render(self.message, True, self.message_color)
            shadow = font.render(self.message, True, (0, 0, 0))

            center_x = vp_x + vp_w // 2
            center_y = vp_y + vp_h // 2

            scaled_w = int(text_surf.get_width() * scale)
            scaled_h = int(text_surf.get_height() * scale)

            if scaled_w > 0 and scaled_h > 0:
                scaled_text = pygame.transform.scale(text_surf, (scaled_w, scaled_h))
                scaled_shadow = pygame.transform.scale(shadow, (scaled_w, scaled_h))

                # Fundo
                bg_padding = 50
                bg_rect = pygame.Rect(center_x - scaled_w // 2 - bg_padding,
                                      center_y - scaled_h // 2 - bg_padding // 2,
                                      scaled_w + bg_padding * 2,
                                      scaled_h + bg_padding)

                bg_surf = pygame.Surface((bg_rect.width, bg_rect.height), pygame.SRCALPHA)
                bg_surf.fill((0, 0, 0, 200))
                pygame.draw.rect(bg_surf, self.COLORS['border_glow'], bg_surf.get_rect(), 3, border_radius=15)
                screen.blit(bg_surf, bg_rect)

                screen.blit(scaled_shadow, (center_x - scaled_w // 2 + 4, center_y - scaled_h // 2 + 4))
                screen.blit(scaled_text, (center_x - scaled_w // 2, center_y - scaled_h // 2))

    def _render_game_overlay(self, screen, vp_x, vp_y, vp_w, vp_h, title, color):
        """Renderiza overlay de game over ou vitoria"""
        # Fundo escurecido
        overlay = pygame.Surface((vp_w, vp_h), pygame.SRCALPHA)
        overlay.fill((0, 0, 0, 220))
        screen.blit(overlay, (vp_x, vp_y))

        # Título
        title_font = self._get_font(60)
        title_surf = title_font.render(title, True, color)
        title_x = vp_x + (vp_w - title_surf.get_width()) // 2
        title_y = vp_y + vp_h // 2 - 120
        screen.blit(title_surf, (title_x, title_y))

        # Score final
        score_font = self._get_font(38)
        formatted_score = f"{self.game_scene.score:,}".replace(",", ".")
        score_text = f"PONTUAÇÃO: {formatted_score}"
        score_surf = score_font.render(score_text, True, self.COLORS['accent'])
        score_x = vp_x + (vp_w - score_surf.get_width()) // 2
        score_y = title_y + 85
        screen.blit(score_surf, (score_x, score_y))

        # Waves completadas
        wave_font = self._get_font(24)
        current_wave = self.game_scene.wave_manager.current_wave if self.game_scene.wave_manager else self.game_scene.wave_number
        wave_text = f"Waves completadas: {current_wave - 1}/{self.game_scene.total_waves}"
        wave_surf = wave_font.render(wave_text, True, self.COLORS['text_dim'])
        wave_x = vp_x + (vp_w - wave_surf.get_width()) // 2
        wave_y = score_y + 60
        screen.blit(wave_surf, (wave_x, wave_y))

        # Instrução
        inst_font = self._get_font(18)
        inst_text = "Pressione ESC para voltar ao menu"
        inst_surf = inst_font.render(inst_text, True, self.COLORS['text_dim'])
        inst_x = vp_x + (vp_w - inst_surf.get_width()) // 2
        inst_y = wave_y + 55
        screen.blit(inst_surf, (inst_x, inst_y))