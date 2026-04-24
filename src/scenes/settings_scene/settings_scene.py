# src/scenes/settings_scene.py

"""
Cena de configurações do jogo - Usa apenas o save do jogador
"""
import pygame
import os
from src.scenes.base_scene import BaseScene
from src.config.settings import settings
from managers.sounds.sound_manager import sound_manager, SoundEffect


class Slider:
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
        abs_x = viewport_x + int(self.relative_x * viewport_width)
        abs_y = viewport_y + int(self.relative_y * viewport_height)
        abs_width = int(self.relative_width * viewport_width)
        self.rect = pygame.Rect(abs_x, abs_y, abs_width, 20)

    def handle_event(self, event):
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
        ratio = (mouse_x - self.rect.x) / self.rect.width
        ratio = max(0, min(1, ratio))
        self.value = self.min_val + ratio * (self.max_val - self.min_val)

    def render(self, screen, font):
        pygame.draw.rect(screen, (50, 50, 50), self.rect)
        fill_width = int(self.rect.width * ((self.value - self.min_val) / (self.max_val - self.min_val)))
        fill_rect = pygame.Rect(self.rect.x, self.rect.y, fill_width, self.rect.height)
        fill_color = (150, 100, 200) if self.is_music else (100, 150, 200)
        pygame.draw.rect(screen, fill_color, fill_rect)
        pygame.draw.rect(screen, (150, 150, 150), self.rect, 2)
        percent = int((self.value - self.min_val) / (self.max_val - self.min_val) * 100)
        value_text = font.render(f"{percent}%", True, (200, 200, 200))
        value_rect = value_text.get_rect(midleft=(self.rect.right + 10, self.rect.centery))
        screen.blit(value_text, value_rect)


class SettingsScene(BaseScene):
    def __init__(self, game):
        super().__init__(game)

        self.title_font = None
        self.label_font = None
        self.value_font = None
        self.hint_font = None

        self.back_button = None
        self.apply_button = None
        self.reset_button = None
        self.music_checkbox_rect = None
        self.sfx_checkbox_rect = None
        self.fullscreen_checkbox_rect = None
        self.vsync_checkbox_rect = None

        self.music_slider = None
        self.sfx_slider = None

        # ===== VERIFICA SE HÁ SAVE (qualquer save, mesmo sem estar "carregado") =====
        self.has_save = self._check_any_save_exists()
        self.state = "normal" if self.has_save else "blocked"

        print(f"[SETTINGS] Tem save? {self.has_save} - Estado: {self.state}")

        # Carrega configurações do save ou usa padrão
        if self.has_save:
            self._load_settings_from_save()
        else:
            self._load_default_settings()

        # Hover states
        self.hover_back = False
        self.hover_apply = False
        self.hover_reset = False
        self.hover_music_check = False
        self.hover_sfx_check = False
        self.hover_fullscreen_check = False
        self.hover_vsync_check = False

        self.preview_music_timer = 0
        self._create_layout()

    def _check_any_save_exists(self):
        """Verifica se existe pelo menos um arquivo de save"""
        from src.managers.save_manager import save_manager

        # Verifica se o save_manager já tem um save carregado
        if save_manager.current_save_file is not None and save_manager.save_data is not None:
            print("[SETTINGS] Save carregado no manager")
            return True

        # Verifica se existe arquivo de save na pasta
        saves_dir = "saves"
        if os.path.exists(saves_dir):
            for i in range(1, 4):  # Slots 1-3
                save_file = os.path.join(saves_dir, f"save_{i}.json")
                if os.path.exists(save_file):
                    print(f"[SETTINGS] Arquivo de save encontrado: save_{i}.json")
                    # Tenta carregar as configurações deste save
                    try:
                        import json
                        with open(save_file, 'r', encoding='utf-8') as f:
                            data = json.load(f)
                            if data.get("settings"):
                                # Salva no save_manager para uso posterior
                                save_manager.save_data = data
                                save_manager.current_save_file = i
                                print(f"[SETTINGS] Save {i} carregado automaticamente")
                                return True
                    except Exception as e:
                        print(f"[SETTINGS] Erro ao ler save {i}: {e}")

        # Verifica se o jogador tem Pokémon (indicando que está em jogo)
        if len(self.game.player.team) > 0 or len(self.game.player.pc_box) > 0:
            print("[SETTINGS] Jogador tem Pokémon - considerando como tendo save")
            return True

        print("[SETTINGS] Nenhum save encontrado")
        return False

    def _load_settings_from_save(self):
        from src.managers.save_manager import save_manager

        # Se save_manager já tem dados, usa eles
        if save_manager.save_data and save_manager.save_data.get("settings"):
            settings_data = save_manager.save_data.get("settings", {})
        else:
            # Procura o primeiro save disponível
            saves_dir = "saves"
            import json
            settings_data = {}
            for i in range(1, 4):
                save_file = os.path.join(saves_dir, f"save_{i}.json")
                if os.path.exists(save_file):
                    try:
                        with open(save_file, 'r', encoding='utf-8') as f:
                            data = json.load(f)
                            if data.get("settings"):
                                settings_data = data.get("settings", {})
                                # Atualiza o save_manager
                                save_manager.save_data = data
                                save_manager.current_save_file = i
                                print(f"[SETTINGS] Carregado save {i}")
                                break
                    except:
                        pass

        self.music_volume = settings_data.get("music_volume", 0.5)
        self.sfx_volume = settings_data.get("sfx_volume", 0.7)
        self.music_enabled = settings_data.get("music_enabled", True)
        self.sfx_enabled = settings_data.get("sfx_enabled", True)
        self.fullscreen_enabled = settings_data.get("fullscreen", False)
        self.vsync_enabled = settings_data.get("vsync", True)

        print(f"[SETTINGS] Carregadas do save: música={self.music_volume}, SFX={self.sfx_volume}")

    def _load_default_settings(self):
        self.music_volume = 0.5
        self.sfx_volume = 0.7
        self.music_enabled = True
        self.sfx_enabled = True
        self.fullscreen_enabled = False
        self.vsync_enabled = True
        print("[SETTINGS] Usando configurações padrão (sem save)")

    def _get_font_size(self, base_size):
        return max(int(base_size * self.screen_manager.viewport_height / 720), 12)

    def _create_layout(self):
        vx = self.screen_manager.viewport_x
        vy = self.screen_manager.viewport_y
        vw = self.screen_manager.viewport_width
        vh = self.screen_manager.viewport_height

        self.title_font = pygame.font.Font(None, self._get_font_size(52))
        self.label_font = pygame.font.Font(None, self._get_font_size(28))
        self.value_font = pygame.font.Font(None, self._get_font_size(24))
        self.hint_font = pygame.font.Font(None, self._get_font_size(20))

        back_size = int(min(vw * 0.05, vh * 0.07, 45))
        self.back_button = pygame.Rect(vx + 20, vy + 20, back_size, back_size)

        content_start_y = vy + int(vh * 0.15)
        content_height = vh - int(vh * 0.3)
        row_height = int(content_height / 6)

        label_x = vx + int(vw * 0.1)
        checkbox_x = vx + int(vw * 0.35)
        slider_x = checkbox_x + 40
        slider_width = vw * 0.4

        # Música
        row_y = content_start_y
        self.music_label_rect = self._create_label("MÚSICA", label_x, row_y)
        self.music_checkbox_rect = pygame.Rect(checkbox_x, row_y + 5, 25, 25)
        self.music_slider = Slider(slider_x / vw, (row_y + 30) / vh, slider_width / vw, self.music_volume)
        self.music_slider.is_music = True
        self.music_slider.update_rect(vx, vy, vw, vh)
        self.music_hint_rect = self._create_hint("Volume da música de fundo", label_x, row_y + 55)

        # Efeitos
        row_y += row_height
        self.sfx_label_rect = self._create_label("EFEITOS SONOROS", label_x, row_y)
        self.sfx_checkbox_rect = pygame.Rect(checkbox_x, row_y + 5, 25, 25)
        self.sfx_slider = Slider(slider_x / vw, (row_y + 30) / vh, slider_width / vw, self.sfx_volume)
        self.sfx_slider.is_music = False
        self.sfx_slider.update_rect(vx, vy, vw, vh)
        self.sfx_hint_rect = self._create_hint("Volume dos efeitos (cliques, batalhas, etc)", label_x, row_y + 55)

        # Tela cheia
        row_y += row_height
        self.fullscreen_label_rect = self._create_label("TELA CHEIA", label_x, row_y)
        self.fullscreen_checkbox_rect = pygame.Rect(checkbox_x, row_y + 5, 25, 25)
        self.fs_hint_rect = self._create_hint("Alternar entre janela e tela cheia", label_x, row_y + 35)

        # VSync
        row_y += row_height
        self.vsync_label_rect = self._create_label("VSYNC", label_x, row_y)
        self.vsync_checkbox_rect = pygame.Rect(checkbox_x, row_y + 5, 25, 25)
        self.vsync_hint_rect = self._create_hint("Sincronização vertical (reduz tearing)", label_x, row_y + 35)

        # Botões
        button_width = int(vw * 0.15)
        button_height = int(vh * 0.07)
        button_spacing = int(vw * 0.03)
        total_width = button_width * 2 + button_spacing
        buttons_y = vy + vh - button_height - int(vh * 0.05)
        buttons_x = vx + (vw - total_width) // 2
        self.apply_button = pygame.Rect(buttons_x, buttons_y, button_width, button_height)
        self.reset_button = pygame.Rect(buttons_x + button_width + button_spacing, buttons_y, button_width,
                                        button_height)

    def _create_label(self, text, x, y):
        surface = self.label_font.render(text, True, (200, 200, 200))
        return surface.get_rect(topleft=(x, y))

    def _create_hint(self, text, x, y):
        surface = self.hint_font.render(text, True, (120, 120, 130))
        return surface.get_rect(topleft=(x, y))

    def handle_event(self, event):
        if event.type == pygame.VIDEORESIZE:
            self._create_layout()
            return

        # Se está bloqueado, só permite voltar
        if self.state == "blocked":
            if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                if self.back_button and self.back_button.collidepoint(event.pos):
                    sound_manager.play_effect(SoundEffect.CLICK)
                    self._go_back()
            return

        if event.type == pygame.MOUSEMOTION:
            self.hover_back = self.back_button.collidepoint(event.pos) if self.back_button else False
            self.hover_apply = self.apply_button.collidepoint(event.pos) if self.apply_button else False
            self.hover_reset = self.reset_button.collidepoint(event.pos) if self.reset_button else False
            self.hover_music_check = self.music_checkbox_rect.collidepoint(
                event.pos) if self.music_checkbox_rect else False
            self.hover_sfx_check = self.sfx_checkbox_rect.collidepoint(event.pos) if self.sfx_checkbox_rect else False
            self.hover_fullscreen_check = self.fullscreen_checkbox_rect.collidepoint(
                event.pos) if self.fullscreen_checkbox_rect else False
            self.hover_vsync_check = self.vsync_checkbox_rect.collidepoint(
                event.pos) if self.vsync_checkbox_rect else False

        elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            if self.back_button and self.back_button.collidepoint(event.pos):
                sound_manager.play_effect(SoundEffect.CLICK)
                self._go_back()
                return

            if self.apply_button and self.apply_button.collidepoint(event.pos):
                sound_manager.play_effect(SoundEffect.CLICK)
                self._apply_settings()
                return

            if self.reset_button and self.reset_button.collidepoint(event.pos):
                sound_manager.play_effect(SoundEffect.CLICK)
                self._reset_to_default()
                return

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

        if self.music_slider and self.music_slider.handle_event(event):
            self.music_volume = self.music_slider.value
            self._apply_music_preview()

        if self.sfx_slider and self.sfx_slider.handle_event(event):
            self.sfx_volume = self.sfx_slider.value
            self._apply_sfx_preview()

    def _apply_music_preview(self):
        if self.music_enabled:
            sound_manager.set_music_volume(self.music_volume)
            if not pygame.mixer.music.get_busy():
                if self.preview_music_timer > 0:
                    sound_manager.stop_music()
                sound_manager.play_random_battle_music()
                self.preview_music_timer = pygame.time.get_ticks()
        else:
            sound_manager.stop_music(fade_ms=200)
            self.preview_music_timer = 0

    def _apply_sfx_preview(self):
        if self.sfx_enabled:
            sound_manager.set_sfx_volume(self.sfx_volume)
        else:
            sound_manager.set_sfx_volume(0)

    def _apply_settings(self):
        from src.config.settings import settings
        from src.managers.save_manager import save_manager

        # Verifica se tem save para salvar
        if not save_manager.current_save_file:
            print("[SETTINGS] Não é possível salvar - nenhum save carregado!")
            sound_manager.play_effect(SoundEffect.CLICK)
            return

        # Atualiza settings
        settings.music_volume = self.music_volume
        settings.sfx_volume = self.sfx_volume
        settings.music_enabled = self.music_enabled
        settings.sfx_enabled = self.sfx_enabled
        settings.fullscreen = self.fullscreen_enabled
        settings.vsync = self.vsync_enabled

        # Aplica ao SoundManager
        sound_manager.sync_all_managers()

        # Aplica tela cheia
        if save_manager.save_data:
            old_fullscreen = save_manager.save_data["settings"].get("fullscreen", False)
            if self.fullscreen_enabled != old_fullscreen:
                self.screen_manager.toggle_fullscreen()

        # SALVA NO SAVE
        save_manager.save_settings(settings)
        print(f"[SETTINGS] Configurações salvas no save {save_manager.current_save_file}!")
        sound_manager.play_effect(SoundEffect.CLICK)

    def _reset_to_default(self):
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

    def _go_back(self):
        from src.managers.save_manager import save_manager

        sound_manager.stop_music()

        # Restaura configurações do save
        if save_manager.current_save_file and save_manager.save_data:
            settings_data = save_manager.save_data.get("settings", {})
            music_vol = settings_data.get("music_volume", 0.5)
            music_en = settings_data.get("music_enabled", True)
            if music_en and music_vol > 0:
                pygame.time.wait(100)
                sound_manager.set_music_volume(music_vol)
                sound_manager.stop_music()

        self.preview_music_timer = 0
        self.game.current_scene = self.game.menu_scene

    def update(self, dt):
        if self.preview_music_timer > 0 and self.music_enabled:
            if pygame.time.get_ticks() - self.preview_music_timer > 3000:
                sound_manager.stop_music(fade_ms=500)
                self.preview_music_timer = 0

    def fixed_update(self, dt):
        pass

    def render(self, screen):
        self._draw_gradient_background(screen)

        if self.music_slider:
            self.music_slider.update_rect(
                self.screen_manager.viewport_x, self.screen_manager.viewport_y,
                self.screen_manager.viewport_width, self.screen_manager.viewport_height
            )
        if self.sfx_slider:
            self.sfx_slider.update_rect(
                self.screen_manager.viewport_x, self.screen_manager.viewport_y,
                self.screen_manager.viewport_width, self.screen_manager.viewport_height
            )

        # Título
        title = self.title_font.render("CONFIGURAÇÕES", True, (220, 220, 230))
        title_x = self.screen_manager.viewport_x + (self.screen_manager.viewport_width - title.get_width()) // 2
        title_y = self.screen_manager.viewport_y + int(self.screen_manager.viewport_height * 0.05)
        screen.blit(title, (title_x, title_y))

        # Se está bloqueado, mostra mensagem
        if self.state == "blocked":
            self._render_blocked_screen(screen)
            self._render_back_button(screen)
            return

        self._render_labels(screen)
        self._render_checkbox(screen, self.music_checkbox_rect, self.music_enabled, self.hover_music_check)
        self._render_checkbox(screen, self.sfx_checkbox_rect, self.sfx_enabled, self.hover_sfx_check)
        self._render_checkbox(screen, self.fullscreen_checkbox_rect, self.fullscreen_enabled,
                              self.hover_fullscreen_check)
        self._render_checkbox(screen, self.vsync_checkbox_rect, self.vsync_enabled, self.hover_vsync_check)

        if self.music_slider:
            self.music_slider.render(screen, self.value_font)
        if self.sfx_slider:
            self.sfx_slider.render(screen, self.value_font)

        self._render_back_button(screen)
        self._render_button(screen, self.apply_button, "APLICAR", self.hover_apply)
        self._render_button(screen, self.reset_button, "PADRÃO", self.hover_reset)

    def _render_blocked_screen(self, screen):
        viewport_x = self.screen_manager.viewport_x
        viewport_y = self.screen_manager.viewport_y
        viewport_w = self.screen_manager.viewport_width
        viewport_h = self.screen_manager.viewport_height

        container_width = 500
        container_height = 280
        container_x = viewport_x + (viewport_w - container_width) // 2
        container_y = viewport_y + (viewport_h - container_height) // 2 - 50

        container_rect = pygame.Rect(container_x, container_y, container_width, container_height)
        pygame.draw.rect(screen, (40, 40, 60), container_rect)
        pygame.draw.rect(screen, (255, 200, 0), container_rect, 3, border_radius=15)

        title_font = self._get_font(28, True)
        title_text = title_font.render("ACESSO BLOQUEADO", True, (255, 200, 100))
        title_x = container_x + (container_width - title_text.get_width()) // 2
        title_y = container_y + 20
        screen.blit(title_text, (title_x, title_y))

        msg_font = self._get_font(20)
        lines = ["Você precisa iniciar um jogo primeiro!", "", "Volte ao menu principal e selecione:", "INICIAR JOGO"]

        line_y = title_y + 50
        for line in lines:
            if line:
                msg_text = msg_font.render(line, True, (200, 200, 220))
            else:
                msg_text = msg_font.render("", True, (200, 200, 220))
            msg_x = container_x + (container_width - msg_text.get_width()) // 2
            screen.blit(msg_text, (msg_x, line_y))
            line_y += 35

    def _get_font(self, size, bold=False):
        from src.core.render_context import render_context
        return render_context.get_font(size, bold)

    def _render_labels(self, screen):
        vx = self.screen_manager.viewport_x
        vw = self.screen_manager.viewport_width
        label_x = vx + int(vw * 0.1)

        music_label = self.label_font.render("MÚSICA", True, (200, 200, 200))
        screen.blit(music_label, (label_x, self.music_label_rect.y))
        music_hint = self.hint_font.render("Volume da música de fundo", True, (120, 120, 130))
        screen.blit(music_hint, (label_x, self.music_hint_rect.y))

        sfx_label = self.label_font.render("EFEITOS SONOROS", True, (200, 200, 200))
        screen.blit(sfx_label, (label_x, self.sfx_label_rect.y))
        sfx_hint = self.hint_font.render("Volume dos efeitos (cliques, batalhas, etc)", True, (120, 120, 130))
        screen.blit(sfx_hint, (label_x, self.sfx_hint_rect.y))

        fs_label = self.label_font.render("TELA CHEIA", True, (200, 200, 200))
        screen.blit(fs_label, (label_x, self.fullscreen_label_rect.y))
        fs_hint = self.hint_font.render("Alternar entre janela e tela cheia", True, (120, 120, 130))
        screen.blit(fs_hint, (label_x, self.fs_hint_rect.y))

        vsync_label = self.label_font.render("VSYNC", True, (200, 200, 200))
        screen.blit(vsync_label, (label_x, self.vsync_label_rect.y))
        vsync_hint = self.hint_font.render("Sincronização vertical (reduz tearing)", True, (120, 120, 130))
        screen.blit(vsync_hint, (label_x, self.vsync_hint_rect.y))

    def _render_checkbox(self, screen, rect, checked, hover):
        if not rect:
            return
        bg_color = (80, 80, 90) if hover else (60, 60, 65)
        pygame.draw.rect(screen, bg_color, rect)
        if checked:
            pygame.draw.rect(screen, (100, 150, 200), rect, 2)
            pygame.draw.line(screen, (100, 150, 200), (rect.x + 5, rect.centery), (rect.x + 12, rect.bottom - 5), 2)
            pygame.draw.line(screen, (100, 150, 200), (rect.x + 12, rect.bottom - 5), (rect.right - 5, rect.y + 5), 2)
        else:
            pygame.draw.rect(screen, (150, 150, 150), rect, 2)

    def _render_back_button(self, screen):
        if not self.back_button:
            return
        color = (70, 70, 80) if self.hover_back else (50, 50, 55)
        border = (140, 140, 160) if self.hover_back else (90, 90, 100)
        pygame.draw.rect(screen, color, self.back_button, border_radius=8)
        pygame.draw.rect(screen, border, self.back_button, 2, border_radius=8)
        font = pygame.font.Font(None, int(self.back_button.height * 0.8))
        text = font.render("<", True, (200, 200, 210))
        text_rect = text.get_rect(center=self.back_button.center)
        screen.blit(text, text_rect)

    def _render_button(self, screen, rect, text, hover):
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
        shadow_rect = rect.copy()
        shadow_rect.x += 4
        shadow_rect.y += 4
        pygame.draw.rect(screen, (15, 15, 15), shadow_rect, border_radius=8)
        pygame.draw.rect(screen, color, rect, border_radius=8)
        pygame.draw.rect(screen, border, rect, 2, border_radius=8)
        font_size = int(rect.height * 0.5)
        button_font = pygame.font.Font(None, font_size)
        button_text = button_font.render(text, True, text_color)
        text_rect = button_text.get_rect(center=rect.center)
        screen.blit(button_text, text_rect)

    def _draw_gradient_background(self, screen):
        for i in range(self.screen_manager.window_height):
            value = int(10 + (i / self.screen_manager.window_height) * 20)
            color = (value, value, value + 3)
            pygame.draw.line(screen, color, (0, i), (self.screen_manager.window_width, i))