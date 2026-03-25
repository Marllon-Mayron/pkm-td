# src/scenes/settings_scene.py
"""
Cena de configurações do jogo - Totalmente responsiva
"""
import pygame
from src.scenes.base_scene import BaseScene
from src.config.settings import settings
from src.managers.sound_manager import sound_manager, SoundEffect


class Slider:
    """Controle deslizante para ajustar volumes"""

    def __init__(self, x, y, width, value, min_val=0, max_val=1):
        self.relative_x = x
        self.relative_y = y
        self.relative_width = width
        self.value = value
        self.min_val = min_val
        self.max_val = max_val
        self.dragging = False
        self.rect = pygame.Rect(0, 0, 0, 0)
        self.is_music = False

    def update_rect(self, viewport_x, viewport_y, viewport_width, viewport_height):
        """Atualiza a posição e tamanho baseado no viewport"""
        abs_x = viewport_x + int(self.relative_x * viewport_width)
        abs_y = viewport_y + int(self.relative_y * viewport_height)
        abs_width = int(self.relative_width * viewport_width)

        self.rect = pygame.Rect(abs_x, abs_y, abs_width, 20)

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

        # Cor diferente para música e efeitos
        fill_color = (150, 100, 200) if self.is_music else (100, 150, 200)
        pygame.draw.rect(screen, fill_color, fill_rect)

        # Contorno
        pygame.draw.rect(screen, (150, 150, 150), self.rect, 2)

        # Valor em percentual
        percent = int((self.value - self.min_val) / (self.max_val - self.min_val) * 100)
        value_text = font.render(f"{percent}%", True, (200, 200, 200))
        value_rect = value_text.get_rect(midleft=(self.rect.right + 10, self.rect.centery))
        screen.blit(value_text, value_rect)


class SettingsScene(BaseScene):
    """Cena de configurações - Totalmente responsiva"""

    def __init__(self, game):
        super().__init__(game)

        # Fontes - serão recriadas no resize
        self.title_font = None
        self.label_font = None
        self.value_font = None
        self.hint_font = None

        # Elementos UI
        self.back_button = None
        self.apply_button = None
        self.reset_button = None
        self.music_checkbox_rect = None
        self.sfx_checkbox_rect = None
        self.fullscreen_checkbox_rect = None
        self.vsync_checkbox_rect = None

        self.music_slider = None
        self.sfx_slider = None

        # Estados
        self.music_enabled = settings.music_enabled
        self.sfx_enabled = settings.sfx_enabled
        self.fullscreen_enabled = settings.fullscreen
        self.vsync_enabled = settings.vsync
        self.music_volume = settings.music_volume
        self.sfx_volume = settings.sfx_volume

        # Hover states
        self.hover_back = False
        self.hover_apply = False
        self.hover_reset = False
        self.hover_music_check = False
        self.hover_sfx_check = False
        self.hover_fullscreen_check = False
        self.hover_vsync_check = False

        # Preview timer
        self.preview_music_timer = 0
        self.was_playing_before = False  # Para lembrar se tinha música antes

        # Inicializa layout
        self._create_layout()

    def _get_font_size(self, base_size):
        """Calcula tamanho da fonte baseado na altura do viewport"""
        return max(int(base_size * self.screen_manager.viewport_height / 720), 12)

    def _create_layout(self):
        """Cria o layout dos elementos - TOTALMENTE RESPONSIVO"""
        vx = self.screen_manager.viewport_x
        vy = self.screen_manager.viewport_y
        vw = self.screen_manager.viewport_width
        vh = self.screen_manager.viewport_height

        # Atualiza fontes
        self.title_font = pygame.font.Font(None, self._get_font_size(52))
        self.label_font = pygame.font.Font(None, self._get_font_size(28))
        self.value_font = pygame.font.Font(None, self._get_font_size(24))
        self.hint_font = pygame.font.Font(None, self._get_font_size(20))

        # Botão voltar (canto superior esquerdo)
        back_size = int(min(vw * 0.05, vh * 0.07, 45))
        self.back_button = pygame.Rect(vx + 20, vy + 20, back_size, back_size)

        # Título (centralizado)
        title_text = "CONFIGURAÇÕES"
        title_surface = self.title_font.render(title_text, True, (220, 220, 230))
        title_y = vy + int(vh * 0.05)
        title_x = vx + (vw - title_surface.get_width()) // 2
        self.title_rect = title_surface.get_rect(topleft=(title_x, title_y))

        # Área de conteúdo (usando porcentagens para evitar sobreposição)
        content_start_y = vy + int(vh * 0.15)
        content_height = vh - int(vh * 0.3)  # Espaço para botões inferiores
        row_height = int(content_height / 6)  # 6 linhas de conteúdo

        # Configurações de posicionamento
        label_x = vx + int(vw * 0.1)
        checkbox_x = vx + int(vw * 0.35)
        slider_x = checkbox_x + 40
        slider_width = vw * 0.4

        # Linha 1: Música
        row_y = content_start_y
        self.music_label_rect = self._create_label("MÚSICA", label_x, row_y)
        self.music_checkbox_rect = pygame.Rect(checkbox_x, row_y + 5, 25, 25)

        # Slider de música
        self.music_slider = Slider(
            slider_x / vw, (row_y + 30) / vh,
            slider_width / vw, self.music_volume
        )
        self.music_slider.is_music = True
        self.music_slider.update_rect(vx, vy, vw, vh)

        # Descrição música
        music_hint_y = row_y + 55
        self.music_hint_rect = self._create_hint(
            "Volume da música de fundo", label_x, music_hint_y
        )

        # Linha 2: Efeitos
        row_y += row_height
        self.sfx_label_rect = self._create_label("EFEITOS SONOROS", label_x, row_y)
        self.sfx_checkbox_rect = pygame.Rect(checkbox_x, row_y + 5, 25, 25)

        # Slider de efeitos
        self.sfx_slider = Slider(
            slider_x / vw, (row_y + 30) / vh,
            slider_width / vw, self.sfx_volume
        )
        self.sfx_slider.is_music = False
        self.sfx_slider.update_rect(vx, vy, vw, vh)

        # Descrição efeitos
        sfx_hint_y = row_y + 55
        self.sfx_hint_rect = self._create_hint(
            "Volume dos efeitos (cliques, batalhas, etc)", label_x, sfx_hint_y
        )

        # Linha 3: Tela cheia
        row_y += row_height
        self.fullscreen_label_rect = self._create_label("TELA CHEIA", label_x, row_y)
        self.fullscreen_checkbox_rect = pygame.Rect(checkbox_x, row_y + 5, 25, 25)

        # Descrição tela cheia
        fs_hint_y = row_y + 35
        self.fs_hint_rect = self._create_hint(
            "Alternar entre janela e tela cheia", label_x, fs_hint_y
        )

        # Linha 4: VSync
        row_y += row_height
        self.vsync_label_rect = self._create_label("VSYNC", label_x, row_y)
        self.vsync_checkbox_rect = pygame.Rect(checkbox_x, row_y + 5, 25, 25)

        # Descrição VSync
        vsync_hint_y = row_y + 35
        self.vsync_hint_rect = self._create_hint(
            "Sincronização vertical (reduz tearing)", label_x, vsync_hint_y
        )
        # Botões inferiores
        button_width = int(vw * 0.15)
        button_height = int(vh * 0.07)
        button_spacing = int(vw * 0.03)
        total_width = button_width * 2 + button_spacing
        buttons_y = vy + vh - button_height - int(vh * 0.05)
        buttons_x = vx + (vw - total_width) // 2

        self.apply_button = pygame.Rect(buttons_x, buttons_y, button_width, button_height)
        self.reset_button = pygame.Rect(
            buttons_x + button_width + button_spacing, buttons_y, button_width, button_height
        )

    def _create_label(self, text, x, y):
        """Cria um retângulo para label"""
        surface = self.label_font.render(text, True, (200, 200, 200))
        return surface.get_rect(topleft=(x, y))

    def _create_hint(self, text, x, y):
        """Cria um retângulo para hint"""
        surface = self.hint_font.render(text, True, (120, 120, 130))
        return surface.get_rect(topleft=(x, y))

    def _update_checkbox_hover(self, mouse_pos):
        """Atualiza estados de hover dos checkboxes"""
        self.hover_music_check = self.music_checkbox_rect.collidepoint(mouse_pos) if self.music_checkbox_rect else False
        self.hover_sfx_check = self.sfx_checkbox_rect.collidepoint(mouse_pos) if self.sfx_checkbox_rect else False
        self.hover_fullscreen_check = self.fullscreen_checkbox_rect.collidepoint(
            mouse_pos) if self.fullscreen_checkbox_rect else False
        self.hover_vsync_check = self.vsync_checkbox_rect.collidepoint(mouse_pos) if self.vsync_checkbox_rect else False

    def handle_event(self, event):
        """Processa eventos"""
        if event.type == pygame.VIDEORESIZE:
            # Recria layout quando a janela é redimensionada
            self._create_layout()
            return

        elif event.type == pygame.MOUSEMOTION:
            # Atualiza hover dos botões
            self.hover_back = self.back_button.collidepoint(event.pos) if self.back_button else False
            self.hover_apply = self.apply_button.collidepoint(event.pos) if self.apply_button else False
            self.hover_reset = self.reset_button.collidepoint(event.pos) if self.reset_button else False
            self._update_checkbox_hover(event.pos)

        elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            # Botão voltar
            if self.back_button and self.back_button.collidepoint(event.pos):
                sound_manager.play_effect(SoundEffect.CLICK)
                self._go_back()
                return

            # Botão aplicar
            if self.apply_button and self.apply_button.collidepoint(event.pos):
                sound_manager.play_effect(SoundEffect.CLICK)
                self._apply_settings()
                return

            # Botão reset
            if self.reset_button and self.reset_button.collidepoint(event.pos):
                sound_manager.play_effect(SoundEffect.CLICK)
                self._reset_to_default()
                return

            # Checkboxes
            if self.music_checkbox_rect and self.music_checkbox_rect.collidepoint(event.pos):
                self.music_enabled = not self.music_enabled
                self._apply_music_preview()
                sound_manager.play_effect(SoundEffect.CLICK)

            if self.sfx_checkbox_rect and self.sfx_checkbox_rect.collidepoint(event.pos):
                self.sfx_enabled = not self.sfx_enabled
                self._apply_sfx_preview()
                sound_manager.play_effect(SoundEffect.CLICK)

            if self.fullscreen_checkbox_rect and self.fullscreen_checkbox_rect.collidepoint(event.pos):
                self.fullscreen_enabled = not self.fullscreen_enabled
                sound_manager.play_effect(SoundEffect.CLICK)

            if self.vsync_checkbox_rect and self.vsync_checkbox_rect.collidepoint(event.pos):
                self.vsync_enabled = not self.vsync_enabled
                sound_manager.play_effect(SoundEffect.CLICK)

        # Processa sliders
        if self.music_slider and self.music_slider.handle_event(event):
            self.music_volume = self.music_slider.value
            self._apply_music_preview()
            self.preview_music_timer = 0

        if self.sfx_slider and self.sfx_slider.handle_event(event):
            self.sfx_volume = self.sfx_slider.value
            self._apply_sfx_preview()

    def _apply_music_preview(self):
        """Aplica preview da música"""
        if self.music_enabled:
            sound_manager.set_music_volume(self.music_volume)
            if not pygame.mixer.music.get_busy():
                sound_manager.play_random_battle_music()
                self.preview_music_timer = pygame.time.get_ticks()
        else:
            sound_manager.stop_music()
            self.preview_music_timer = 0

    def _apply_sfx_preview(self):
        """Aplica preview dos efeitos"""
        if self.sfx_enabled:
            sound_manager.set_sfx_volume(self.sfx_volume)
        else:
            sound_manager.set_sfx_volume(0)

    def _apply_settings(self):
        """Aplica as configurações"""
        settings.music_volume = self.music_volume
        settings.sfx_volume = self.sfx_volume
        settings.music_enabled = self.music_enabled
        settings.sfx_enabled = self.sfx_enabled
        settings.fullscreen = self.fullscreen_enabled
        settings.vsync = self.vsync_enabled

        # Aplica volumes
        self._apply_music_preview()
        self._apply_sfx_preview()

        # Aplica tela cheia
        if settings.fullscreen != self.screen_manager.settings.fullscreen:
            self.screen_manager.toggle_fullscreen()

        # Salva as configurações no save manager
        from src.config.progress import progress_manager
        progress_manager._save_settings_to_save()  # Salva no save atual
        progress_manager._sync_with_save_manager()  # Sincroniza tudo

        sound_manager.play_effect(SoundEffect.CLICK)
        print(f"[SETTINGS] Configurações aplicadas! Música={settings.music_volume}, SFX={settings.sfx_volume}")

    def _reset_to_default(self):
        """Reseta para configurações padrão"""
        self.music_volume = 0.5
        self.sfx_volume = 0.7
        self.music_enabled = True
        self.sfx_enabled = True
        self.fullscreen_enabled = False
        self.vsync_enabled = True

        if self.music_slider:
            self.music_slider.value = self.music_volume
        if self.sfx_slider:
            self.sfx_slider.value = self.sfx_volume

        self._apply_music_preview()
        self._apply_sfx_preview()

        sound_manager.play_effect(SoundEffect.CLICK)
        print("[SETTINGS] Resetado para padrão!")

    def _go_back(self):
        """Volta para o menu principal"""
        # PARA A MÚSICA DE PREVIEW AO SAIR
        sound_manager.stop_music()

        # Restaura volumes originais se não aplicou
        if not self._is_applied():
            sound_manager.set_music_volume(settings.music_volume)
            sound_manager.set_sfx_volume(settings.sfx_volume)

        # Se as configurações originais tinham música ativada, volta a tocar a música do menu
        if settings.music_enabled:
            # Pequeno delay para garantir que a música de preview parou
            pygame.time.wait(100)
            sound_manager.set_music_volume(settings.music_volume)
            sound_manager.play_random_battle_music()
            print("[SETTINGS] Música do menu restaurada")

        self.preview_music_timer = 0
        self.game.current_scene = self.game.menu_scene

    def _is_applied(self):
        """Verifica se as configurações atuais são as aplicadas"""
        return (self.music_volume == settings.music_volume and
                self.sfx_volume == settings.sfx_volume and
                self.music_enabled == settings.music_enabled and
                self.sfx_enabled == settings.sfx_enabled)

    def update(self, dt):
        """Atualiza a cena"""
        if self.preview_music_timer > 0:
            current_time = pygame.time.get_ticks()
            if current_time - self.preview_music_timer > 3000:
                if self.music_enabled:
                    sound_manager.stop_music()
                self.preview_music_timer = 0

    def fixed_update(self, dt):
        """Método obrigatório da classe base"""
        pass

    def render(self, screen):
        """Renderiza a tela de configurações"""
        self._draw_gradient_background(screen)

        # Atualiza sliders com posições atuais do viewport
        if self.music_slider:
            self.music_slider.update_rect(
                self.screen_manager.viewport_x,
                self.screen_manager.viewport_y,
                self.screen_manager.viewport_width,
                self.screen_manager.viewport_height
            )
        if self.sfx_slider:
            self.sfx_slider.update_rect(
                self.screen_manager.viewport_x,
                self.screen_manager.viewport_y,
                self.screen_manager.viewport_width,
                self.screen_manager.viewport_height
            )

        # Título
        title = self.title_font.render("CONFIGURAÇÕES", True, (220, 220, 230))
        title_x = self.screen_manager.viewport_x + (self.screen_manager.viewport_width - title.get_width()) // 2
        title_y = self.screen_manager.viewport_y + int(self.screen_manager.viewport_height * 0.05)
        screen.blit(title, (title_x, title_y))

        # Renderiza labels e hints
        self._render_labels(screen)

        # Renderiza checkboxes
        self._render_checkbox(screen, self.music_checkbox_rect, self.music_enabled, self.hover_music_check)
        self._render_checkbox(screen, self.sfx_checkbox_rect, self.sfx_enabled, self.hover_sfx_check)
        self._render_checkbox(screen, self.fullscreen_checkbox_rect, self.fullscreen_enabled,
                              self.hover_fullscreen_check)
        self._render_checkbox(screen, self.vsync_checkbox_rect, self.vsync_enabled, self.hover_vsync_check)

        # Renderiza sliders
        if self.music_slider:
            self.music_slider.render(screen, self.value_font)
        if self.sfx_slider:
            self.sfx_slider.render(screen, self.value_font)

        # Botão voltar
        self._render_back_button(screen)

        # Botões inferiores
        self._render_button(screen, self.apply_button, "APLICAR", self.hover_apply)
        self._render_button(screen, self.reset_button, "PADRÃO", self.hover_reset)


    def _render_labels(self, screen):
        """Renderiza todos os labels e hints"""
        vx = self.screen_manager.viewport_x
        vy = self.screen_manager.viewport_y
        vw = self.screen_manager.viewport_width

        label_x = vx + int(vw * 0.1)

        # Música
        music_label = self.label_font.render("MÚSICA", True, (200, 200, 200))
        screen.blit(music_label, (label_x, self.music_label_rect.y))

        music_hint = self.hint_font.render("Volume da música de fundo", True, (120, 120, 130))
        screen.blit(music_hint, (label_x, self.music_hint_rect.y))

        # Efeitos
        sfx_label = self.label_font.render("EFEITOS SONOROS", True, (200, 200, 200))
        screen.blit(sfx_label, (label_x, self.sfx_label_rect.y))

        sfx_hint = self.hint_font.render("Volume dos efeitos (cliques, batalhas, etc)", True, (120, 120, 130))
        screen.blit(sfx_hint, (label_x, self.sfx_hint_rect.y))

        # Tela cheia
        fs_label = self.label_font.render("TELA CHEIA", True, (200, 200, 200))
        screen.blit(fs_label, (label_x, self.fullscreen_label_rect.y))

        fs_hint = self.hint_font.render("Alternar entre janela e tela cheia", True, (120, 120, 130))
        screen.blit(fs_hint, (label_x, self.fs_hint_rect.y))

        # VSync
        vsync_label = self.label_font.render("VSYNC", True, (200, 200, 200))
        screen.blit(vsync_label, (label_x, self.vsync_label_rect.y))

        vsync_hint = self.hint_font.render("Sincronização vertical (reduz tearing)", True, (120, 120, 130))
        screen.blit(vsync_hint, (label_x, self.vsync_hint_rect.y))

    def _render_checkbox(self, screen, rect, checked, hover):
        """Renderiza um checkbox"""
        if not rect:
            return

        # Cor de fundo
        if hover:
            bg_color = (80, 80, 90)
        else:
            bg_color = (60, 60, 65)

        pygame.draw.rect(screen, bg_color, rect)

        if checked:
            pygame.draw.rect(screen, (100, 150, 200), rect, 2)
            # Desenha checkmark
            pygame.draw.line(screen, (100, 150, 200),
                             (rect.x + 5, rect.centery),
                             (rect.x + 12, rect.bottom - 5), 2)
            pygame.draw.line(screen, (100, 150, 200),
                             (rect.x + 12, rect.bottom - 5),
                             (rect.right - 5, rect.y + 5), 2)
        else:
            pygame.draw.rect(screen, (150, 150, 150), rect, 2)

    def _render_back_button(self, screen):
        """Renderiza o botão voltar"""
        if not self.back_button:
            return

        # Cor baseada no hover
        if self.hover_back:
            color = (70, 70, 80)
            border = (140, 140, 160)
        else:
            color = (50, 50, 55)
            border = (90, 90, 100)

        pygame.draw.rect(screen, color, self.back_button, border_radius=8)
        pygame.draw.rect(screen, border, self.back_button, 2, border_radius=8)

        font = pygame.font.Font(None, int(self.back_button.height * 0.8))
        text = font.render("<", True, (200, 200, 210))
        text_rect = text.get_rect(center=self.back_button.center)
        screen.blit(text, text_rect)

    def _render_button(self, screen, rect, text, hover):
        """Renderiza um botão"""
        if not rect:
            return

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
        font_size = int(rect.height * 0.5)
        button_font = pygame.font.Font(None, font_size)
        button_text = button_font.render(text, True, text_color)
        text_rect = button_text.get_rect(center=rect.center)
        screen.blit(button_text, text_rect)

    def _draw_gradient_background(self, screen):
        """Desenha fundo com gradiente"""
        for i in range(self.screen_manager.window_height):
            value = int(10 + (i / self.screen_manager.window_height) * 20)
            color = (value, value, value + 3)
            pygame.draw.line(screen, color, (0, i), (self.screen_manager.window_width, i))