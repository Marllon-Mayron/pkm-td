# src/scenes/settings_scene.py
"""
Cena de configurações do jogo
"""
import pygame
from src.scenes.base_scene import BaseScene
from src.config.settings import settings
from src.managers.sound_manager import sound_manager


class Slider:
    """Controle deslizante para ajustar volumes"""

    def __init__(self, x, y, width, value, min_val=0, max_val=1):
        self.rect = pygame.Rect(x, y, width, 20)
        self.value = value
        self.min_val = min_val
        self.max_val = max_val
        self.dragging = False
        self.relative_x = x / 1280  # Para responsividade
        self.relative_y = y / 720

    def update_position(self, viewport_x, viewport_y, viewport_width, viewport_height):
        """Atualiza posição baseada no viewport"""
        self.rect.x = viewport_x + int(self.relative_x * viewport_width)
        self.rect.y = viewport_y + int(self.relative_y * viewport_height)

    def handle_event(self, event):
        """Processa eventos do slider"""
        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            if self.rect.collidepoint(event.pos):
                self.dragging = True
                self._update_value(event.pos[0])
                return True

        elif event.type == pygame.MOUSEBUTTONUP and event.button == 1:
            self.dragging = False

        elif event.type == pygame.MOUSEMOTION and self.dragging:
            self._update_value(event.pos[0])
            return True

        return False

    def _update_value(self, mouse_x):
        """Atualiza o valor baseado na posição do mouse"""
        ratio = (mouse_x - self.rect.x) / self.rect.width
        ratio = max(0, min(1, ratio))
        self.value = self.min_val + ratio * (self.max_val - self.min_val)

    def render(self, screen, font):
        """Renderiza o slider"""
        # Fundo do slider
        pygame.draw.rect(screen, (50, 50, 50), self.rect)

        # Barra de progresso
        fill_width = int(self.rect.width * ((self.value - self.min_val) / (self.max_val - self.min_val)))
        fill_rect = pygame.Rect(self.rect.x, self.rect.y, fill_width, self.rect.height)
        pygame.draw.rect(screen, (100, 150, 200), fill_rect)

        # Contorno
        pygame.draw.rect(screen, (150, 150, 150), self.rect, 2)

        # Valor em percentual
        percent = int((self.value - self.min_val) / (self.max_val - self.min_val) * 100)
        value_text = font.render(f"{percent}%", True, (200, 200, 200))
        value_rect = value_text.get_rect(midleft=(self.rect.right + 10, self.rect.centery))
        screen.blit(value_text, value_rect)


class SettingsScene(BaseScene):
    """Cena de configurações"""

    def __init__(self, game):
        super().__init__(game)

        # Título
        self.title_font = pygame.font.Font(None, 52)
        self.label_font = pygame.font.Font(None, 28)
        self.value_font = pygame.font.Font(None, 24)

        # Botões
        self.back_button = None
        self.apply_button = None
        self.reset_button = None

        # Checkboxes
        self.music_checkbox = None
        self.sfx_checkbox = None
        self.fullscreen_checkbox = None
        self.vsync_checkbox = None

        # Sliders
        self.music_slider = None
        self.sfx_slider = None

        # Layout
        self.layout_initialized = False
        self.last_window_size = (self.screen_manager.window_width, self.screen_manager.window_height)

        # Estado temporário das configurações
        self.temp_settings = {
            'sfx_volume': settings.sfx_volume,
            'music_volume': settings.music_volume,
            'music_enabled': settings.music_enabled,
            'sfx_enabled': settings.sfx_enabled,
            'fullscreen': settings.fullscreen,
            'vsync': settings.vsync,
            'screen_width': settings.screen_width,
            'screen_height': settings.screen_height
        }

        self.hover_apply = False
        self.hover_reset = False

    def _check_resize(self):
        """Verifica se a tela foi redimensionada"""
        current_size = (self.screen_manager.window_width, self.screen_manager.window_height)
        if current_size != self.last_window_size:
            self.last_window_size = current_size
            self.layout_initialized = False
            return True
        return False

    def _create_layout(self):
        """Cria o layout dos elementos"""
        viewport_x = self.screen_manager.viewport_x
        viewport_y = self.screen_manager.viewport_y
        viewport_width = self.screen_manager.viewport_width
        viewport_height = self.screen_manager.viewport_height

        # Botão voltar
        back_size = 45
        self.back_button = pygame.Rect(
            viewport_x + 30,
            viewport_y + 25,
            back_size,
            back_size
        )

        # Botões de ação
        button_width = 180
        button_height = 50
        button_spacing = 20

        total_buttons_width = button_width * 2 + button_spacing
        start_x = viewport_x + (viewport_width - total_buttons_width) // 2

        self.apply_button = pygame.Rect(
            start_x,
            viewport_y + viewport_height - 100,
            button_width,
            button_height
        )

        self.reset_button = pygame.Rect(
            start_x + button_width + button_spacing,
            viewport_y + viewport_height - 100,
            button_width,
            button_height
        )

        # Posições dos elementos
        start_y = viewport_y + 120
        row_height = 80

        # Checkbox de música
        self.music_checkbox = {
            'rect': pygame.Rect(viewport_x + 150, start_y, 25, 25),
            'checked': self.temp_settings['music_enabled']
        }

        # Slider de música
        slider_width = 400
        self.music_slider = Slider(
            viewport_x + 150 + 40, start_y + 30, slider_width,
            self.temp_settings['music_volume']
        )
        self.music_slider.relative_x = (viewport_x + 150 + 40) / viewport_width
        self.music_slider.relative_y = (start_y + 30) / viewport_height

        # Checkbox de efeitos
        start_y += row_height
        self.sfx_checkbox = {
            'rect': pygame.Rect(viewport_x + 150, start_y, 25, 25),
            'checked': self.temp_settings['sfx_enabled']
        }

        # Slider de efeitos
        self.sfx_slider = Slider(
            viewport_x + 150 + 40, start_y + 30, slider_width,
            self.temp_settings['sfx_volume']
        )
        self.sfx_slider.relative_x = (viewport_x + 150 + 40) / viewport_width
        self.sfx_slider.relative_y = (start_y + 30) / viewport_height

        # Checkbox de tela cheia
        start_y += row_height
        self.fullscreen_checkbox = {
            'rect': pygame.Rect(viewport_x + 150, start_y, 25, 25),
            'checked': self.temp_settings['fullscreen']
        }

        # Checkbox de VSync
        start_y += row_height
        self.vsync_checkbox = {
            'rect': pygame.Rect(viewport_x + 150, start_y, 25, 25),
            'checked': self.temp_settings['vsync']
        }

        self.layout_initialized = True

    def handle_event(self, event):
        """Processa eventos"""
        if event.type == pygame.KEYDOWN:
            if event.key == pygame.K_ESCAPE:
                self._go_back()

        elif event.type == pygame.VIDEORESIZE:
            self.layout_initialized = False

        elif event.type == pygame.MOUSEMOTION:
            # Atualiza hover dos botões
            if self.apply_button:
                self.hover_apply = self.apply_button.collidepoint(event.pos)
            if self.reset_button:
                self.hover_reset = self.reset_button.collidepoint(event.pos)

        elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            # Botão voltar
            if self.back_button and self.back_button.collidepoint(event.pos):
                sound_manager.play_sound("click")
                self._go_back()
                return

            # Botão aplicar
            if self.apply_button and self.apply_button.collidepoint(event.pos):
                sound_manager.play_sound("click")
                self._apply_settings()
                return

            # Botão reset
            if self.reset_button and self.reset_button.collidepoint(event.pos):
                sound_manager.play_sound("click")
                self._reset_to_default()
                return

            # Checkboxes
            if self.music_checkbox and self.music_checkbox['rect'].collidepoint(event.pos):
                self.music_checkbox['checked'] = not self.music_checkbox['checked']
                self.temp_settings['music_enabled'] = self.music_checkbox['checked']
                if not self.music_checkbox['checked']:
                    sound_manager.stop_music()
                else:
                    sound_manager.set_music_volume(self.music_slider.value)
                sound_manager.play_sound("click")

            if self.sfx_checkbox and self.sfx_checkbox['rect'].collidepoint(event.pos):
                self.sfx_checkbox['checked'] = not self.sfx_checkbox['checked']
                self.temp_settings['sfx_enabled'] = self.sfx_checkbox['checked']
                if self.sfx_checkbox['checked']:
                    sound_manager.play_sound("click")

            if self.fullscreen_checkbox and self.fullscreen_checkbox['rect'].collidepoint(event.pos):
                self.fullscreen_checkbox['checked'] = not self.fullscreen_checkbox['checked']
                self.temp_settings['fullscreen'] = self.fullscreen_checkbox['checked']
                sound_manager.play_sound("click")

            if self.vsync_checkbox and self.vsync_checkbox['rect'].collidepoint(event.pos):
                self.vsync_checkbox['checked'] = not self.vsync_checkbox['checked']
                self.temp_settings['vsync'] = self.vsync_checkbox['checked']
                sound_manager.play_sound("click")

        # Processa sliders
        if self.music_slider and self.music_slider.handle_event(event):
            self.temp_settings['music_volume'] = self.music_slider.value
            if self.temp_settings['music_enabled']:
                sound_manager.set_music_volume(self.music_slider.value)

        if self.sfx_slider and self.sfx_slider.handle_event(event):
            self.temp_settings['sfx_volume'] = self.sfx_slider.value
            if self.temp_settings['sfx_enabled']:
                sound_manager.set_sfx_volume(self.sfx_slider.value)

    def _apply_settings(self):
        """Aplica as configurações"""
        # Salva no settings global
        settings.sfx_volume = self.temp_settings['sfx_volume']
        settings.music_volume = self.temp_settings['music_volume']
        settings.music_enabled = self.temp_settings['music_enabled']
        settings.sfx_enabled = self.temp_settings['sfx_enabled']
        settings.fullscreen = self.temp_settings['fullscreen']
        settings.vsync = self.temp_settings['vsync']

        # Aplica volumes no sound manager
        if settings.sfx_enabled:
            sound_manager.set_sfx_volume(settings.sfx_volume)
        else:
            sound_manager.set_sfx_volume(0)

        if settings.music_enabled:
            sound_manager.set_music_volume(settings.music_volume)
        else:
            sound_manager.set_music_volume(0)

        # Aplica tela cheia
        if settings.fullscreen != self.screen_manager.settings.fullscreen:
            self.screen_manager.toggle_fullscreen()

        # Salva as configurações no save atual
        from src.config.progress import progress_manager
        progress_manager._sync_with_save_manager()  # Isso já salva as settings no save

        # Salva no arquivo config.json como fallback
        settings.save_settings()

        # Feedback
        sound_manager.play_sound("confirm")
        print("[SETTINGS] Configurações aplicadas e salvas no save!")

    def _reset_to_default(self):
        """Reseta para as configurações padrão"""
        self.temp_settings = {
            'sfx_volume': 0.7,
            'music_volume': 0.5,
            'music_enabled': True,
            'sfx_enabled': True,
            'fullscreen': False,
            'vsync': True,
            'screen_width': 1280,
            'screen_height': 720
        }

        # Atualiza elementos UI
        if self.music_checkbox:
            self.music_checkbox['checked'] = self.temp_settings['music_enabled']
        if self.sfx_checkbox:
            self.sfx_checkbox['checked'] = self.temp_settings['sfx_enabled']
        if self.fullscreen_checkbox:
            self.fullscreen_checkbox['checked'] = self.temp_settings['fullscreen']
        if self.vsync_checkbox:
            self.vsync_checkbox['checked'] = self.temp_settings['vsync']
        if self.music_slider:
            self.music_slider.value = self.temp_settings['music_volume']
        if self.sfx_slider:
            self.sfx_slider.value = self.temp_settings['sfx_volume']

        sound_manager.play_sound("click")
        print("[SETTINGS] Configurações resetadas para padrão")

    def _go_back(self):
        """Volta para o menu principal"""
        # Restaura os volumes originais se não aplicou
        if not self._is_applied():
            sound_manager.set_sfx_volume(settings.sfx_volume)
            sound_manager.set_music_volume(settings.music_volume)

        self.game.current_scene = self.game.menu_scene

    def _is_applied(self):
        """Verifica se as configurações atuais são as aplicadas"""
        return (self.temp_settings['sfx_volume'] == settings.sfx_volume and
                self.temp_settings['music_volume'] == settings.music_volume and
                self.temp_settings['music_enabled'] == settings.music_enabled and
                self.temp_settings['sfx_enabled'] == settings.sfx_enabled)
    def fixed_update(self, dt):
        pass

    def render(self, screen):
        """Renderiza a tela de configurações"""
        self._check_resize()
        self._draw_gradient_background(screen)

        if not self.layout_initialized:
            self._create_layout()

        # Atualiza posições dos sliders
        if self.music_slider:
            self.music_slider.update_position(
                self.screen_manager.viewport_x,
                self.screen_manager.viewport_y,
                self.screen_manager.viewport_width,
                self.screen_manager.viewport_height
            )
        if self.sfx_slider:
            self.sfx_slider.update_position(
                self.screen_manager.viewport_x,
                self.screen_manager.viewport_y,
                self.screen_manager.viewport_width,
                self.screen_manager.viewport_height
            )

        # Título
        title = self.title_font.render("CONFIGURAÇÕES", True, (220, 220, 230))
        title_x = self.screen_manager.viewport_x + (self.screen_manager.viewport_width - title.get_width()) // 2
        screen.blit(title, (title_x, self.screen_manager.viewport_y + 25))

        # Botão voltar
        if self.back_button:
            pygame.draw.rect(screen, (50, 50, 55), self.back_button, border_radius=8)
            pygame.draw.rect(screen, (90, 90, 100), self.back_button, 2, border_radius=8)
            font = pygame.font.Font(None, 40)
            text = font.render("<", True, (200, 200, 210))
            text_rect = text.get_rect(center=self.back_button.center)
            screen.blit(text, text_rect)

        # Renderiza opções
        self._render_options(screen)

        # Botões de ação
        if self.apply_button:
            self._render_button(screen, self.apply_button, "APLICAR", self.hover_apply)
        if self.reset_button:
            self._render_button(screen, self.reset_button, "PADRÃO", self.hover_reset)

    def _render_options(self, screen):
        """Renderiza as opções de configuração"""
        viewport_x = self.screen_manager.viewport_x
        viewport_y = self.screen_manager.viewport_y
        viewport_width = self.screen_manager.viewport_width

        start_y = viewport_y + 120
        row_height = 80

        # Música
        label = self.label_font.render("MÚSICA", True, (200, 200, 200))
        screen.blit(label, (viewport_x + 50, start_y + 5))

        if self.music_checkbox:
            # Checkbox
            pygame.draw.rect(screen, (60, 60, 65), self.music_checkbox['rect'])
            if self.music_checkbox['checked']:
                pygame.draw.rect(screen, (100, 150, 200), self.music_checkbox['rect'], 2)
                pygame.draw.line(screen, (100, 150, 200),
                                 (self.music_checkbox['rect'].x + 5, self.music_checkbox['rect'].centery),
                                 (self.music_checkbox['rect'].x + 12, self.music_checkbox['rect'].bottom - 5), 2)
                pygame.draw.line(screen, (100, 150, 200),
                                 (self.music_checkbox['rect'].x + 12, self.music_checkbox['rect'].bottom - 5),
                                 (self.music_checkbox['rect'].right - 5, self.music_checkbox['rect'].y + 5), 2)
            else:
                pygame.draw.rect(screen, (150, 150, 150), self.music_checkbox['rect'], 2)

        if self.music_slider:
            self.music_slider.render(screen, self.value_font)

        # Efeitos sonoros
        start_y += row_height
        label = self.label_font.render("EFEITOS", True, (200, 200, 200))
        screen.blit(label, (viewport_x + 50, start_y + 5))

        if self.sfx_checkbox:
            pygame.draw.rect(screen, (60, 60, 65), self.sfx_checkbox['rect'])
            if self.sfx_checkbox['checked']:
                pygame.draw.rect(screen, (100, 150, 200), self.sfx_checkbox['rect'], 2)
                pygame.draw.line(screen, (100, 150, 200),
                                 (self.sfx_checkbox['rect'].x + 5, self.sfx_checkbox['rect'].centery),
                                 (self.sfx_checkbox['rect'].x + 12, self.sfx_checkbox['rect'].bottom - 5), 2)
                pygame.draw.line(screen, (100, 150, 200),
                                 (self.sfx_checkbox['rect'].x + 12, self.sfx_checkbox['rect'].bottom - 5),
                                 (self.sfx_checkbox['rect'].right - 5, self.sfx_checkbox['rect'].y + 5), 2)
            else:
                pygame.draw.rect(screen, (150, 150, 150), self.sfx_checkbox['rect'], 2)

        if self.sfx_slider:
            self.sfx_slider.render(screen, self.value_font)

        # Tela cheia
        start_y += row_height
        label = self.label_font.render("TELA CHEIA", True, (200, 200, 200))
        screen.blit(label, (viewport_x + 50, start_y + 5))

        if self.fullscreen_checkbox:
            pygame.draw.rect(screen, (60, 60, 65), self.fullscreen_checkbox['rect'])
            if self.fullscreen_checkbox['checked']:
                pygame.draw.rect(screen, (100, 150, 200), self.fullscreen_checkbox['rect'], 2)
                pygame.draw.line(screen, (100, 150, 200),
                                 (self.fullscreen_checkbox['rect'].x + 5, self.fullscreen_checkbox['rect'].centery),
                                 (self.fullscreen_checkbox['rect'].x + 12, self.fullscreen_checkbox['rect'].bottom - 5),
                                 2)
                pygame.draw.line(screen, (100, 150, 200),
                                 (self.fullscreen_checkbox['rect'].x + 12, self.fullscreen_checkbox['rect'].bottom - 5),
                                 (self.fullscreen_checkbox['rect'].right - 5, self.fullscreen_checkbox['rect'].y + 5),
                                 2)
            else:
                pygame.draw.rect(screen, (150, 150, 150), self.fullscreen_checkbox['rect'], 2)

        # VSync
        start_y += row_height
        label = self.label_font.render("VSYNC", True, (200, 200, 200))
        screen.blit(label, (viewport_x + 50, start_y + 5))

        if self.vsync_checkbox:
            pygame.draw.rect(screen, (60, 60, 65), self.vsync_checkbox['rect'])
            if self.vsync_checkbox['checked']:
                pygame.draw.rect(screen, (100, 150, 200), self.vsync_checkbox['rect'], 2)
                pygame.draw.line(screen, (100, 150, 200),
                                 (self.vsync_checkbox['rect'].x + 5, self.vsync_checkbox['rect'].centery),
                                 (self.vsync_checkbox['rect'].x + 12, self.vsync_checkbox['rect'].bottom - 5), 2)
                pygame.draw.line(screen, (100, 150, 200),
                                 (self.vsync_checkbox['rect'].x + 12, self.vsync_checkbox['rect'].bottom - 5),
                                 (self.vsync_checkbox['rect'].right - 5, self.vsync_checkbox['rect'].y + 5), 2)
            else:
                pygame.draw.rect(screen, (150, 150, 150), self.vsync_checkbox['rect'], 2)

    def _render_button(self, screen, rect, text, hover):
        """Renderiza um botão"""
        if hover:
            color = (70, 70, 80)
            border = (140, 140, 160)
            text_color = (255, 255, 255)
        else:
            color = (50, 50, 55)
            border = (90, 90, 100)
            text_color = (200, 200, 200)

        # Sombra
        shadow_rect = rect.copy()
        shadow_rect.x += 4
        shadow_rect.y += 4
        pygame.draw.rect(screen, (15, 15, 15), shadow_rect, border_radius=8)

        # Botão
        pygame.draw.rect(screen, color, rect, border_radius=8)
        pygame.draw.rect(screen, border, rect, 2, border_radius=8)

        # Texto
        button_text = self.label_font.render(text, True, text_color)
        text_rect = button_text.get_rect(center=rect.center)
        screen.blit(button_text, text_rect)

    def _draw_gradient_background(self, screen):
        """Desenha fundo com gradiente"""
        for i in range(self.screen_manager.window_height):
            value = int(10 + (i / self.screen_manager.window_height) * 20)
            color = (value, value, value + 3)
            pygame.draw.line(screen, color, (0, i), (self.screen_manager.window_width, i))