# src/scenes/minigames/survival/components/ui/survival_ui.py
"""
UI especifica do minigame survival - Estilo moderno e responsivo
"""
import pygame
import math


class SurvivalUI:
    """Renderiza a interface do usuario com estilo moderno"""

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

        # Top Bar com gradiente
        top_bar_height = 90
        self._draw_vertical_gradient(
            screen,
            (viewport_x, viewport_y, vp_width, top_bar_height),
            self.COLORS['bg_dark'],
            self.COLORS['bg_light']
        )

        # Linha de brilho na borda inferior
        glow_height = 2
        for i in range(glow_height):
            alpha = 150 - i * 50
            color = (self.COLORS['primary'][0], self.COLORS['primary'][1], self.COLORS['primary'][2], alpha)
            pygame.draw.line(screen, color[:3],
                           (viewport_x, viewport_y + top_bar_height - i),
                           (viewport_x + vp_width, viewport_y + top_bar_height - i))

        # Vidas (esquerda)
        self._render_lives(screen, viewport_x + 20, viewport_y + 15)

        # Energia (abaixo das vidas)
        self._render_energy(screen, viewport_x + 20, viewport_y + 55)

        # Score/Pontos (direita)
        self._render_score(screen, viewport_x + vp_width - 160, viewport_y + 20)

        # Banner da Wave (centro)
        self._render_wave_banner(screen, viewport_x + vp_width // 2, viewport_y + 48)

        # Mensagem central (ao matar boss, etc)
        self._render_center_message(screen, viewport_x, viewport_y, vp_width, vp_height)

        # Game Over / Complete Overlays
        if self.game_scene.game_state == "game_over":
            self._render_game_overlay(screen, viewport_x, viewport_y, vp_width, vp_height, "GAME OVER", self.COLORS['danger'])
        elif self.game_scene.game_state == "completed":
            self._render_game_overlay(screen, viewport_x, viewport_y, vp_width, vp_height, "VITORIA!", self.COLORS['success'])

    def _draw_vertical_gradient(self, screen, rect, color1, color2):
        """Desenha gradiente vertical"""
        x, y, w, h = rect
        for i in range(h):
            t = i / h
            r = int(color1[0] * (1 - t) + color2[0] * t)
            g = int(color1[1] * (1 - t) + color2[1] * t)
            b = int(color1[2] * (1 - t) + color2[2] * t)
            pygame.draw.line(screen, (r, g, b), (x, y + i), (x + w, y + i))

    def _render_lives(self, screen, x: int, y: int):
        """Renderiza o indicador de vidas"""
        heart_size = 24
        spacing = 8
        lives = self.game_scene.lives
        max_lives = self.game_scene.STARTING_LIVES

        # Fundo
        bg_width = max_lives * (heart_size + spacing) + 20
        bg_rect = pygame.Rect(x - 10, y - 5, bg_width, heart_size + 15)
        pygame.draw.rect(screen, self.COLORS['bg_dark'], bg_rect, border_radius=10)
        pygame.draw.rect(screen, self.COLORS['border'], bg_rect, 1, border_radius=10)

        # Título
        title_font = self._get_font(11)
        title = title_font.render("VIDAS", True, self.COLORS['text_dim'])
        screen.blit(title, (x - 5, y - 18))

        # Corações
        for i in range(lives):
            heart_x = x + i * (heart_size + spacing)
            heart_y = y
            self._draw_heart(screen, heart_x, heart_y, heart_size, self.COLORS['danger'])

        # Corações vazios (perdidos)
        for i in range(lives, max_lives):
            heart_x = x + i * (heart_size + spacing)
            heart_y = y
            self._draw_heart_outline(screen, heart_x, heart_y, heart_size, self.COLORS['border'])

    def _draw_heart(self, screen, x, y, size, color):
        """Desenha coração cheio"""
        rect = pygame.Rect(x, y, size, size)
        # Corpo
        pygame.draw.rect(screen, color, rect, border_radius=6)
        # Curvas superiores
        pygame.draw.circle(screen, color, (x + size // 3, y + size // 3), size // 4)
        pygame.draw.circle(screen, color, (x + 2 * size // 3, y + size // 3), size // 4)
        # Brilho
        inner = rect.inflate(-6, -6)
        pygame.draw.rect(screen, (255, 150, 150), inner, border_radius=4)

    def _draw_heart_outline(self, screen, x, y, size, color):
        """Desenha contorno de coração (vida perdida)"""
        rect = pygame.Rect(x, y, size, size)
        pygame.draw.rect(screen, color, rect, 2, border_radius=6)
        pygame.draw.circle(screen, color, (x + size // 3, y + size // 3), size // 4, 2)
        pygame.draw.circle(screen, color, (x + 2 * size // 3, y + size // 3), size // 4, 2)

    def _render_energy(self, screen, x: int, y: int):
        """Renderiza a barra de energia"""
        bar_width = 240
        bar_height = 20

        # Título
        title_font = self._get_font(11)
        title = title_font.render("ENERGIA", True, self.COLORS['text_dim'])
        screen.blit(title, (x, y - 18))

        # Fundo
        bg_rect = pygame.Rect(x, y, bar_width, bar_height)
        pygame.draw.rect(screen, (30, 35, 50), bg_rect, border_radius=10)
        pygame.draw.rect(screen, self.COLORS['border'], bg_rect, 1, border_radius=10)

        # Preenchimento
        energy_percent = self.game_scene.energy / 200.0
        fill_width = int(bar_width * min(1.0, energy_percent))

        if energy_percent > 0.6:
            color = self.COLORS['success']
        elif energy_percent > 0.3:
            color = self.COLORS['accent']
        else:
            color = self.COLORS['danger']

        fill_rect = pygame.Rect(x, y, fill_width, bar_height)
        pygame.draw.rect(screen, color, fill_rect, border_radius=10)

        # Texto do valor
        value_font = self._get_font(14)
        value_text = value_font.render(f"{int(self.game_scene.energy)} / 200", True, self.COLORS['text'])
        value_x = x + bar_width + 12
        screen.blit(value_text, (value_x, y + 2))

    def _render_score(self, screen, x: int, y: int):
        """Renderiza o placar de pontos"""
        score = self.game_scene.score

        # Fundo com brilho
        bg_width = 130
        bg_height = 50
        bg_rect = pygame.Rect(x, y, bg_width, bg_height)
        pygame.draw.rect(screen, self.COLORS['bg_dark'], bg_rect, border_radius=12)
        pygame.draw.rect(screen, self.COLORS['border'], bg_rect, 1, border_radius=12)

        # Símbolo de estrela (sem emoji, desenhado)
        self._draw_star(screen, x + 12, y + 12, 12, self.COLORS['accent'])

        # Título
        title_font = self._get_font(10)
        title = title_font.render("PONTOS", True, self.COLORS['text_dim'])
        screen.blit(title, (x + 32, y + 8))

        # Valor
        value_font = self._get_font(20)
        value_text = value_font.render(str(score), True, self.COLORS['accent'])
        screen.blit(value_text, (x + 32, y + 24))

    def _draw_star(self, screen, x, y, size, color):
        """Desenha uma estrela"""
        points = []
        outer_radius = size
        inner_radius = size // 2
        for i in range(5):
            angle = math.radians(90 + i * 72)
            px = x + outer_radius * math.cos(angle)
            py = y + outer_radius * math.sin(angle)
            points.append((px, py))
            angle = math.radians(90 + i * 72 + 36)
            px = x + inner_radius * math.cos(angle)
            py = y + inner_radius * math.sin(angle)
            points.append((px, py))
        pygame.draw.polygon(screen, color, points)

    def _render_wave_banner(self, screen, center_x: int, y: int):
        """Renderiza o banner da wave atual"""
        wave_num = self.game_scene.wave_number

        has_boss = False
        if hasattr(self.game_scene, 'wave_manager') and self.game_scene.wave_manager:
            config = getattr(self.game_scene.wave_manager, 'current_wave_config', None)
            has_boss = config and config.has_boss if config else False

        # Texto
        if has_boss:
            wave_text = f"Onda {wave_num} - CHEFE"
            base_color = self.COLORS['danger']
            text_color = (255, 220, 220)
        else:
            wave_text = f"Onda {wave_num}"
            base_color = self.COLORS['primary']
            text_color = self.COLORS['text']

        # Efeito pulsante para chefe
        pulse = math.sin(self.wave_pulse) * 0.15 + 0.85 if has_boss else 1.0

        # Banner
        font = self._get_font(22)
        text_surf = font.render(wave_text, True, text_color)
        padding = 30
        banner_width = text_surf.get_width() + padding * 2
        banner_height = 42
        banner_rect = pygame.Rect(center_x - banner_width // 2, y, banner_width, banner_height)

        # Sombra
        shadow_rect = banner_rect.copy()
        shadow_rect.y += 3
        pygame.draw.rect(screen, (0, 0, 0, 120), shadow_rect, border_radius=21)

        # Fundo gradiente
        self._draw_vertical_gradient(screen, banner_rect, base_color,
                                     (base_color[0] + 30, base_color[1] + 30, base_color[2] + 30))

        # Borda (com brilho para chefe)
        if has_boss:
            glow_width = int(4 * pulse)
            for i in range(glow_width):
                alpha = 100 - i * 25
                color = (255, 100, 100, alpha)
                pygame.draw.rect(screen, color[:3], banner_rect.inflate(i*2, i*2), 1, border_radius=21)
        else:
            pygame.draw.rect(screen, self.COLORS['border_glow'], banner_rect, 2, border_radius=21)

        screen.blit(text_surf, (center_x - text_surf.get_width() // 2, y + 10))

    def _render_center_message(self, screen, vp_x, vp_y, vp_w, vp_h):
        """Renderiza mensagem central (wave complete, boss incoming, etc)"""
        if self.message and self.message_timer > 0:
            scale = self.message_animation

            # Escolhe fonte baseada no tamanho da mensagem
            if len(self.message) > 20:
                font = self._get_font(24)
            else:
                font = self._get_font(32)

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
                bg_padding = 40
                bg_rect = pygame.Rect(center_x - scaled_w // 2 - bg_padding,
                                     center_y - scaled_h // 2 - bg_padding // 2,
                                     scaled_w + bg_padding * 2,
                                     scaled_h + bg_padding)

                bg_surf = pygame.Surface((bg_rect.width, bg_rect.height), pygame.SRCALPHA)
                alpha = min(200, int(150 + 100 * scale))
                bg_surf.fill((0, 0, 0, alpha))
                pygame.draw.rect(bg_surf, self.COLORS['border_glow'], bg_surf.get_rect(), 2, border_radius=15)
                screen.blit(bg_surf, bg_rect)

                screen.blit(scaled_shadow, (center_x - scaled_w // 2 + 3, center_y - scaled_h // 2 + 3))
                screen.blit(scaled_text, (center_x - scaled_w // 2, center_y - scaled_h // 2))

    def _render_game_overlay(self, screen, vp_x, vp_y, vp_w, vp_h, title, color):
        """Renderiza overlay de game over ou vitória"""
        # Fundo escurecido
        overlay = pygame.Surface((vp_w, vp_h), pygame.SRCALPHA)
        overlay.fill((0, 0, 0, 200))
        screen.blit(overlay, (vp_x, vp_y))

        # Título
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

        # Instrução
        inst_font = self._get_font(16)
        inst_text = "Pressione ESC para voltar ao menu"
        inst_surf = inst_font.render(inst_text, True, self.COLORS['text_dim'])
        inst_x = vp_x + (vp_w - inst_surf.get_width()) // 2
        inst_y = score_y + 50
        screen.blit(inst_surf, (inst_x, inst_y))