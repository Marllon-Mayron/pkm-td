# src/scenes/settings_scene.py

"""
Cena de configurações do jogo - Estilo consistente com menu e phase_selector
"""
import pygame
import os
from src.scenes.base_scene import BaseScene
from src.managers.sounds.sound_manager import sound_manager, SoundEffect


class Slider:
    """Slider com posicionamento relativo e responsivo - Estilo consistente"""

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

        # Animações
        self.scale = 1.0
        self.target_scale = 1.0

    def update_rect(self, viewport_x, viewport_y, viewport_width, viewport_height):
        """Atualiza a posição absoluta baseada no viewport"""
        abs_x = viewport_x + int(self.relative_x * viewport_width)
        abs_y = viewport_y + int(self.relative_y * viewport_height)
        abs_width = int(self.relative_width * viewport_width)
        self.rect = pygame.Rect(abs_x, abs_y, abs_width, int(viewport_height * 0.035))

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
        """Renderiza o slider com gradiente e thumb"""
        # Sombra
        shadow_rect = self.rect.copy()
        shadow_rect.y += 3
        pygame.draw.rect(screen, (10, 10, 15), shadow_rect, border_radius=6)

        # Fundo do slider
        pygame.draw.rect(screen, (30, 30, 40), self.rect, border_radius=6)

        # Barra preenchida com gradiente
        fill_width = int(self.rect.width * ((self.value - self.min_val) / (self.max_val - self.min_val)))
        if fill_width > 0:
            fill_rect = pygame.Rect(self.rect.x, self.rect.y, fill_width, self.rect.height)
            if self.is_music:
                fill_color = (80, 180, 80)
                fill_color_end = (50, 150, 50)
            else:
                fill_color = (80, 120, 200)
                fill_color_end = (50, 90, 180)

            for i in range(fill_width):
                t = i / fill_width if fill_width > 0 else 0
                r = fill_color[0] + int((fill_color_end[0] - fill_color[0]) * t)
                g = fill_color[1] + int((fill_color_end[1] - fill_color[1]) * t)
                b = fill_color[2] + int((fill_color_end[2] - fill_color[2]) * t)
                pygame.draw.line(screen, (r, g, b), (fill_rect.x + i, fill_rect.y), (fill_rect.x + i, fill_rect.bottom))

        # Borda do slider
        pygame.draw.rect(screen, (60, 60, 75), self.rect, 2, border_radius=6)

        # Thumb (alça)
        thumb_x = self.rect.x + fill_width - 6
        thumb_rect = pygame.Rect(thumb_x, self.rect.y - 3, 12, self.rect.height + 6)
        thumb_color = (220, 220, 240) if self.dragging else (180, 180, 210)
        pygame.draw.rect(screen, thumb_color, thumb_rect, border_radius=4)
        pygame.draw.rect(screen, (100, 100, 120), thumb_rect, 1, border_radius=4)

        # Texto de porcentagem
        percent = int((self.value - self.min_val) / (self.max_val - self.min_val) * 100)
        value_text = font.render(f"{percent}%", True, (150, 150, 170))
        value_rect = value_text.get_rect(midleft=(self.rect.right + 12, self.rect.centery))
        screen.blit(value_text, value_rect)


class SettingsScene(BaseScene):
    """Cena de configurações com estilo consistente"""

    def __init__(self, game, on_back_callback=None):
        super().__init__(game)

        # ===== FONTES =====
        self.title_font = None
        self.label_font = None
        self.value_font = None
        self.hint_font = None
        self.category_font = None
        self.shortcut_font = None
        self.tab_font = None

        # ===== BOTÕES =====
        self.back_button = None
        self.apply_button = None
        self.reset_button = None
        self.tab_audio_button = None
        self.tab_shortcuts_button = None

        # ===== ABA ATUAL =====
        self.current_tab = "audio"

        # ===== RECTS DOS ELEMENTOS =====
        self.panel_rect = None
        self.title_rect = None

        # Colunas (proporções relativas ao viewport)
        self.left_col_x = 0.08
        self.right_col_x = 0.55
        self.col_width = 0.35

        # Rects para cada elemento
        self.music_label_rect = None
        self.music_checkbox_rect = None
        self.music_hint_rect = None
        self.music_slider_rect = None

        self.sfx_label_rect = None
        self.sfx_checkbox_rect = None
        self.sfx_hint_rect = None
        self.sfx_slider_rect = None

        self.fullscreen_label_rect = None
        self.fullscreen_checkbox_rect = None
        self.fullscreen_hint_rect = None

        self.vsync_label_rect = None
        self.vsync_checkbox_rect = None
        self.vsync_hint_rect = None

        self.audio_category_rect = None
        self.video_category_rect = None

        # ===== SLIDERS =====
        self.music_slider = None
        self.sfx_slider = None

        # ===== CALLBACK =====
        self._on_back_callback = on_back_callback

        # ===== ESTADO =====
        self.has_save = self._check_any_save_exists()
        self.state = "normal" if self.has_save else "blocked"

        if self.has_save:
            self._load_settings_from_save()
        else:
            self._load_default_settings()

        # ===== HOVER STATES =====
        self.hover_back = False
        self.hover_apply = False
        self.hover_reset = False
        self.hover_music_check = False
        self.hover_sfx_check = False
        self.hover_fullscreen_check = False
        self.hover_vsync_check = False
        self.hover_tab_audio = False
        self.hover_tab_shortcuts = False

        self.preview_music_timer = 0

        # ===== ANIMAÇÕES =====
        self.panel_animation_progress = 0
        self._animation_timer = 0
        self._scanline_offset = 0

        # ===== LAYOUT =====
        self._create_layout()

    # ======================================================================
    # MÉTODOS DE INICIALIZAÇÃO
    # ======================================================================

    def _check_any_save_exists(self):
        """Verifica se existe algum save disponível"""
        from src.managers.save_manager import save_manager
        import os
        import json

        if save_manager.current_save_file is not None and save_manager.save_data is not None:
            return True

        saves_dir = "saves"
        if os.path.exists(saves_dir):
            for i in range(1, 4):
                save_file = os.path.join(saves_dir, f"save_{i}.json")
                if os.path.exists(save_file):
                    try:
                        with open(save_file, 'r', encoding='utf-8') as f:
                            data = json.load(f)
                            if data.get("player"):
                                save_manager.save_data = data
                                save_manager.current_save_file = i
                                return True
                    except Exception:
                        pass

        if len(self.game.player.team) > 0 or len(self.game.player.pc_box) > 0:
            return True

        return False

    def _load_settings_from_save(self):
        """Carrega configurações do save"""
        from src.config.settings import settings as global_settings
        from src.managers.save_manager import save_manager

        if save_manager.save_data and save_manager.save_data.get("settings"):
            settings_data = save_manager.save_data.get("settings", {})
            self.music_volume = settings_data.get("music_volume", 0.5)
            self.sfx_volume = settings_data.get("sfx_volume", 0.7)
            self.music_enabled = settings_data.get("music_enabled", True)
            self.sfx_enabled = settings_data.get("sfx_enabled", True)
            self.fullscreen_enabled = settings_data.get("fullscreen", False)
            self.vsync_enabled = settings_data.get("vsync", True)
        else:
            self.music_volume = global_settings.music_volume
            self.sfx_volume = global_settings.sfx_volume
            self.music_enabled = global_settings.music_enabled
            self.sfx_enabled = global_settings.sfx_enabled
            self.fullscreen_enabled = global_settings.fullscreen
            self.vsync_enabled = global_settings.vsync

    def _load_default_settings(self):
        """Carrega configurações padrão"""
        from src.config.settings import settings as global_settings
        self.music_volume = global_settings.music_volume
        self.sfx_volume = global_settings.sfx_volume
        self.music_enabled = global_settings.music_enabled
        self.sfx_enabled = global_settings.sfx_enabled
        self.fullscreen_enabled = global_settings.fullscreen
        self.vsync_enabled = global_settings.vsync

    def _get_font_size(self, base_size):
        """Calcula tamanho da fonte baseado no viewport"""
        return max(int(base_size * self.screen_manager.viewport_height / 720), 12)

    # ======================================================================
    # LAYOUT RESPONSIVO
    # ======================================================================

    def _create_layout(self):
        """Cria todo o layout baseado no viewport atual"""
        vx = self.screen_manager.viewport_x
        vy = self.screen_manager.viewport_y
        vw = self.screen_manager.viewport_width
        vh = self.screen_manager.viewport_height

        # ===== FONTES =====
        self.title_font = pygame.font.Font(None, self._get_font_size(52))
        self.label_font = pygame.font.Font(None, self._get_font_size(24))
        self.value_font = pygame.font.Font(None, self._get_font_size(20))
        self.hint_font = pygame.font.Font(None, self._get_font_size(18))
        self.category_font = pygame.font.Font(None, self._get_font_size(22))
        self.shortcut_font = pygame.font.Font(None, self._get_font_size(20))
        self.tab_font = pygame.font.Font(None, self._get_font_size(20))

        # ===== BOTÃO VOLTAR =====
        back_size = int(min(vw * 0.045, vh * 0.065, 40))
        self.back_button = pygame.Rect(vx + 20, vy + 20, back_size, back_size)

        # ===== TÍTULO =====
        title_text = self.title_font.render("CONFIGURACOES", True, (255, 255, 255))
        title_shadow = self.title_font.render("CONFIGURACOES", True, (30, 30, 45))

        title_x = vx + (vw - title_text.get_width()) // 2
        title_y = vy + int(vh * 0.025)
        self.title_rect = pygame.Rect(title_x, title_y, title_text.get_width(), title_text.get_height())

        # ===== ABAS (abaixo do título com espaçamento) =====
        tab_width = int(vw * 0.10)
        tab_height = int(vh * 0.045)
        tab_spacing = int(vw * 0.015)
        tabs_total_width = tab_width * 2 + tab_spacing
        tab_start_x = vx + (vw - tabs_total_width) // 2
        tab_y = title_y + title_text.get_height() + int(vh * 0.04)

        self.tab_audio_button = pygame.Rect(tab_start_x, tab_y, tab_width, tab_height)
        self.tab_shortcuts_button = pygame.Rect(tab_start_x + tab_width + tab_spacing, tab_y, tab_width, tab_height)

        # ===== PAINEL PRINCIPAL =====
        panel_width = int(vw * 0.78)
        panel_height = int(vh * 0.64)
        panel_x = vx + (vw - panel_width) // 2
        panel_y = tab_y + tab_height + int(vh * 0.025)
        self.panel_rect = pygame.Rect(panel_x, panel_y, panel_width, panel_height)

        # ===== CATEGORIAS =====
        cat_y = panel_y + int(panel_height * 0.03)
        self.audio_category_rect = pygame.Rect(panel_x + 20, cat_y, 80, 30)
        self.video_category_rect = pygame.Rect(
            panel_x + panel_width // 2 + 20, cat_y, 80, 30
        )

        # ===== ATUALIZA ELEMENTOS =====
        self._update_element_rects(vx, vy, vw, vh, panel_y, panel_height)

        # ===== SLIDERS =====
        self._init_sliders(vx, vy, vw, vh)

    def _update_element_rects(self, vx, vy, vw, vh, panel_y, panel_height):
        """Atualiza todos os retângulos dos elementos"""
        checkbox_size = int(vh * 0.033)
        label_width = int(vw * 0.12)
        slider_width = vw * 0.28

        start_y = panel_y + panel_height * 0.10
        row_height = panel_height * 0.11

        # ===== COLUNA ESQUERDA - ÁUDIO =====
        left_x = vx + vw * self.left_col_x

        # LINHA 1: MÚSICA
        row_y = start_y

        self.music_label_rect = pygame.Rect(
            left_x, row_y, label_width, int(row_height * 0.35)
        )

        self.music_checkbox_rect = pygame.Rect(
            left_x + label_width + 10,
            row_y + (int(row_height * 0.35) - checkbox_size) // 2,
            checkbox_size, checkbox_size
        )

        hint_y = row_y + int(row_height * 0.38)
        self.music_hint_rect = pygame.Rect(
            left_x, hint_y, int(vw * 0.22), int(row_height * 0.22)
        )

        slider_y = hint_y + int(row_height * 0.28)
        self.music_slider_rect = pygame.Rect(
            left_x, slider_y, int(slider_width), int(row_height * 0.30)
        )

        # LINHA 2: EFEITOS SONOROS
        row_y = start_y + row_height * 1.15

        self.sfx_label_rect = pygame.Rect(
            left_x, row_y, label_width, int(row_height * 0.35)
        )

        self.sfx_checkbox_rect = pygame.Rect(
            left_x + label_width + 10,
            row_y + (int(row_height * 0.35) - checkbox_size) // 2,
            checkbox_size, checkbox_size
        )

        hint_y = row_y + int(row_height * 0.38)
        self.sfx_hint_rect = pygame.Rect(
            left_x, hint_y, int(vw * 0.22), int(row_height * 0.22)
        )

        slider_y = hint_y + int(row_height * 0.28)
        self.sfx_slider_rect = pygame.Rect(
            left_x, slider_y, int(slider_width), int(row_height * 0.30)
        )

        # ===== COLUNA DIREITA - VÍDEO =====
        right_x = vx + vw * self.right_col_x

        # LINHA 1: FULLSCREEN
        row_y = start_y

        self.fullscreen_label_rect = pygame.Rect(
            right_x, row_y, int(label_width * 1.3), int(row_height * 0.35)
        )

        self.fullscreen_checkbox_rect = pygame.Rect(
            right_x + int(label_width * 1.3) + 10,
            row_y + (int(row_height * 0.35) - checkbox_size) // 2,
            checkbox_size, checkbox_size
        )

        hint_y = row_y + int(row_height * 0.38)
        self.fullscreen_hint_rect = pygame.Rect(
            right_x, hint_y, int(vw * 0.22), int(row_height * 0.22)
        )

        # LINHA 2: VSYNC
        row_y = start_y + row_height * 1.15

        self.vsync_label_rect = pygame.Rect(
            right_x, row_y, int(label_width * 1.3), int(row_height * 0.35)
        )

        self.vsync_checkbox_rect = pygame.Rect(
            right_x + int(label_width * 1.3) + 10,
            row_y + (int(row_height * 0.35) - checkbox_size) // 2,
            checkbox_size, checkbox_size
        )

        hint_y = row_y + int(row_height * 0.38)
        self.vsync_hint_rect = pygame.Rect(
            right_x, hint_y, int(vw * 0.22), int(row_height * 0.22)
        )

        # ===== BOTÕES DE AÇÃO =====
        button_width = int(vw * 0.09)
        button_height = int(vh * 0.05)
        button_spacing = int(vw * 0.025)

        total_width = button_width * 2 + button_spacing
        buttons_y = panel_y + panel_height - button_height - int(vh * 0.025)
        buttons_x = vx + (vw - total_width) // 2

        self.apply_button = pygame.Rect(buttons_x, buttons_y, button_width, button_height)
        self.reset_button = pygame.Rect(
            buttons_x + button_width + button_spacing,
            buttons_y, button_width, button_height
        )

    def _init_sliders(self, vx, vy, vw, vh):
        """Inicializa os sliders com posições relativas"""
        if self.music_slider_rect:
            rel_x = (self.music_slider_rect.x - vx) / vw
            rel_y = (self.music_slider_rect.y - vy) / vh
            rel_w = self.music_slider_rect.width / vw

            if not self.music_slider:
                self.music_slider = Slider(rel_x, rel_y, rel_w, self.music_volume)
                self.music_slider.is_music = True
            else:
                self.music_slider.relative_x = rel_x
                self.music_slider.relative_y = rel_y
                self.music_slider.relative_width = rel_w
            self.music_slider.update_rect(vx, vy, vw, vh)

        if self.sfx_slider_rect:
            rel_x = (self.sfx_slider_rect.x - vx) / vw
            rel_y = (self.sfx_slider_rect.y - vy) / vh
            rel_w = self.sfx_slider_rect.width / vw

            if not self.sfx_slider:
                self.sfx_slider = Slider(rel_x, rel_y, rel_w, self.sfx_volume)
                self.sfx_slider.is_music = False
            else:
                self.sfx_slider.relative_x = rel_x
                self.sfx_slider.relative_y = rel_y
                self.sfx_slider.relative_width = rel_w
            self.sfx_slider.update_rect(vx, vy, vw, vh)

    # ======================================================================
    # MÉTODOS DE EVENTOS
    # ======================================================================

    def handle_event(self, event):
        """Processa eventos da cena"""
        if event.type == pygame.VIDEORESIZE:
            self._create_layout()
            return

        if self.state == "blocked":
            if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                if self.back_button and self.back_button.collidepoint(event.pos):
                    sound_manager.play_effect(SoundEffect.CLICK)
                    self._go_back()
            return

        if event.type == pygame.MOUSEMOTION:
            self._update_hover_states(event.pos)

        elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            self._handle_click(event.pos)

        if self.current_tab == "audio":
            if self.music_slider and self.music_slider.handle_event(event):
                self.music_volume = self.music_slider.value
                self._apply_music_preview()

            if self.sfx_slider and self.sfx_slider.handle_event(event):
                self.sfx_volume = self.sfx_slider.value
                self._apply_sfx_preview()

    def _update_hover_states(self, pos):
        """Atualiza estados de hover para todos os elementos"""
        self.hover_back = self.back_button.collidepoint(pos) if self.back_button else False
        self.hover_apply = self.apply_button.collidepoint(pos) if self.apply_button else False
        self.hover_reset = self.reset_button.collidepoint(pos) if self.reset_button else False
        self.hover_tab_audio = self.tab_audio_button.collidepoint(pos) if self.tab_audio_button else False
        self.hover_tab_shortcuts = self.tab_shortcuts_button.collidepoint(pos) if self.tab_shortcuts_button else False

        if self.current_tab == "audio":
            self.hover_music_check = self.music_checkbox_rect.collidepoint(pos) if self.music_checkbox_rect else False
            self.hover_sfx_check = self.sfx_checkbox_rect.collidepoint(pos) if self.sfx_checkbox_rect else False
            self.hover_fullscreen_check = self.fullscreen_checkbox_rect.collidepoint(
                pos) if self.fullscreen_checkbox_rect else False
            self.hover_vsync_check = self.vsync_checkbox_rect.collidepoint(pos) if self.vsync_checkbox_rect else False

    def _handle_click(self, pos):
        """Processa cliques em todos os elementos interativos"""
        if self.back_button and self.back_button.collidepoint(pos):
            sound_manager.play_effect(SoundEffect.CLICK)
            self._go_back()
            return

        if self.tab_audio_button and self.tab_audio_button.collidepoint(pos):
            sound_manager.play_effect(SoundEffect.CLICK)
            self.current_tab = "audio"
            return

        if self.tab_shortcuts_button and self.tab_shortcuts_button.collidepoint(pos):
            sound_manager.play_effect(SoundEffect.CLICK)
            self.current_tab = "shortcuts"
            return

        if self.apply_button and self.apply_button.collidepoint(pos):
            sound_manager.play_effect(SoundEffect.CLICK)
            self._apply_settings()
            return

        if self.reset_button and self.reset_button.collidepoint(pos):
            sound_manager.play_effect(SoundEffect.CLICK)
            self._reset_to_default()
            return

        if self.current_tab == "audio":
            if self.music_checkbox_rect and self.music_checkbox_rect.collidepoint(pos):
                self.music_enabled = not self.music_enabled
                self._apply_music_preview()
                sound_manager.play_effect(SoundEffect.CLICK)

            if self.sfx_checkbox_rect and self.sfx_checkbox_rect.collidepoint(pos):
                self.sfx_enabled = not self.sfx_enabled
                self._apply_sfx_preview()
                sound_manager.play_effect(SoundEffect.CLICK)

            if self.fullscreen_checkbox_rect and self.fullscreen_checkbox_rect.collidepoint(pos):
                self.fullscreen_enabled = not self.fullscreen_enabled
                sound_manager.play_effect(SoundEffect.CLICK)

            if self.vsync_checkbox_rect and self.vsync_checkbox_rect.collidepoint(pos):
                self.vsync_enabled = not self.vsync_enabled
                sound_manager.play_effect(SoundEffect.CLICK)

    # ======================================================================
    # MÉTODOS DE ÁUDIO
    # ======================================================================

    def _apply_music_preview(self):
        """Aplica preview da música"""
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
        """Aplica preview dos efeitos sonoros"""
        if self.sfx_enabled:
            sound_manager.set_sfx_volume(self.sfx_volume)
        else:
            sound_manager.set_sfx_volume(0)

    # ======================================================================
    # MÉTODOS DE AÇÃO
    # ======================================================================

    def _apply_settings(self):
        """Aplica e salva as configurações"""
        from src.config.settings import settings as global_settings
        from src.managers.save_manager import save_manager

        old_fullscreen = global_settings.fullscreen
        old_vsync = global_settings.vsync

        global_settings.music_volume = self.music_volume
        global_settings.sfx_volume = self.sfx_volume
        global_settings.music_enabled = self.music_enabled
        global_settings.sfx_enabled = self.sfx_enabled
        global_settings.fullscreen = self.fullscreen_enabled
        global_settings.vsync = self.vsync_enabled

        sound_manager.sync_all_managers()

        if global_settings.fullscreen != old_fullscreen:
            self.screen_manager.toggle_fullscreen()

        if global_settings.vsync != old_vsync:
            self.screen_manager.initialize_screen()

        if save_manager.current_save_file:
            success = save_manager.save_settings(global_settings)
            if success:
                sound_manager.play_effect(SoundEffect.CLICK)

    def _reset_to_default(self):
        """Reseta para valores padrão"""
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
        """Volta para a cena anterior"""
        sound_manager.stop_music()
        self.preview_music_timer = 0

        if self._on_back_callback is not None:
            callback = self._on_back_callback
            self._on_back_callback = None
            callback()
            return

        self.game.current_scene = self.game.menu_scene

    # ======================================================================
    # UPDATE
    # ======================================================================

    def update(self, dt):
        """Atualiza a cena"""
        self._animation_timer += dt

        if self.preview_music_timer > 0 and self.music_enabled:
            if pygame.time.get_ticks() - self.preview_music_timer > 3000:
                sound_manager.stop_music(fade_ms=500)
                self.preview_music_timer = 0

        self.panel_animation_progress = min(1.0, self.panel_animation_progress + dt * 3)
        self._scanline_offset = (self._scanline_offset + 1) % 4

    def fixed_update(self, dt):
        pass

    # ======================================================================
    # RENDERIZAÇÃO
    # ======================================================================

    def render(self, screen):
        """Renderiza a cena"""
        self._draw_gradient_background(screen)

        vx = self.screen_manager.viewport_x
        vy = self.screen_manager.viewport_y
        vw = self.screen_manager.viewport_width
        vh = self.screen_manager.viewport_height

        # Recalcula layout
        self._create_layout()

        # ===== TÍTULO =====
        self._render_title(screen, vx, vy, vw, vh)

        # ===== ABAS =====
        self._render_tabs(screen)

        # ===== PAINEL PRINCIPAL =====
        self._render_panel(screen)

        # ===== CONTEÚDO DO PAINEL =====
        if self.current_tab == "audio":
            self._render_audio_tab(screen)
        else:
            self._render_shortcuts_tab(screen)

        # ===== BOTÕES =====
        self._render_back_button(screen)
        self._render_button(screen, self.apply_button, "APLICAR", self.hover_apply)
        self._render_button(screen, self.reset_button, "PADRAO", self.hover_reset)

    def _render_title(self, screen, vx, vy, vw, vh):
        """Renderiza o título da cena"""
        title = self.title_font.render("CONFIGURACOES", True, (255, 255, 255))
        title_shadow = self.title_font.render("CONFIGURACOES", True, (30, 30, 45))

        title_x = vx + (vw - title.get_width()) // 2
        title_y = vy + int(vh * 0.025)

        screen.blit(title_shadow, (title_x + 2, title_y + 2))
        screen.blit(title, (title_x, title_y))

        # Linha decorativa
        bar_width = int(vw * 0.12)
        bar_x = vx + (vw - bar_width) // 2
        bar_y = title_y + title.get_height() + 6
        pygame.draw.rect(screen, (100, 85, 55), (bar_x, bar_y, bar_width, 3), border_radius=2)

    def _render_tabs(self, screen):
        """Renderiza as abas de navegação"""
        # Aba Áudio
        is_active = self.current_tab == "audio"
        color = (60, 60, 75) if is_active else (40, 40, 50)
        border = (150, 150, 180) if is_active else (80, 80, 95)
        text_color = (255, 255, 255) if is_active else (180, 180, 190)

        # Sombra
        shadow_rect = self.tab_audio_button.copy()
        shadow_rect.y += 3
        pygame.draw.rect(screen, (10, 10, 15), shadow_rect, border_radius=8)

        pygame.draw.rect(screen, color, self.tab_audio_button, border_radius=8)
        pygame.draw.rect(screen, border, self.tab_audio_button, 2, border_radius=8)

        if is_active:
            # Linha indicadora
            indicator_rect = pygame.Rect(
                self.tab_audio_button.x + 15,
                self.tab_audio_button.bottom - 3,
                self.tab_audio_button.width - 30,
                3
            )
            pygame.draw.rect(screen, (200, 180, 120), indicator_rect, border_radius=2)

        font = pygame.font.Font(None, int(self.tab_audio_button.height * 0.5))
        text = font.render("AUDIO", True, text_color)
        text_rect = text.get_rect(center=self.tab_audio_button.center)
        screen.blit(text, text_rect)

        # Aba Atalhos
        is_active = self.current_tab == "shortcuts"
        color = (60, 60, 75) if is_active else (40, 40, 50)
        border = (150, 150, 180) if is_active else (80, 80, 95)
        text_color = (255, 255, 255) if is_active else (180, 180, 190)

        shadow_rect = self.tab_shortcuts_button.copy()
        shadow_rect.y += 3
        pygame.draw.rect(screen, (10, 10, 15), shadow_rect, border_radius=8)

        pygame.draw.rect(screen, color, self.tab_shortcuts_button, border_radius=8)
        pygame.draw.rect(screen, border, self.tab_shortcuts_button, 2, border_radius=8)

        if is_active:
            indicator_rect = pygame.Rect(
                self.tab_shortcuts_button.x + 15,
                self.tab_shortcuts_button.bottom - 3,
                self.tab_shortcuts_button.width - 30,
                3
            )
            pygame.draw.rect(screen, (200, 180, 120), indicator_rect, border_radius=2)

        font = pygame.font.Font(None, int(self.tab_shortcuts_button.height * 0.5))
        text = font.render("ATALHOS", True, text_color)
        text_rect = text.get_rect(center=self.tab_shortcuts_button.center)
        screen.blit(text, text_rect)

    def _render_audio_tab(self, screen):
        """Renderiza o conteúdo da aba de áudio"""
        self._render_categories(screen)
        self._render_audio_labels(screen)
        self._render_video_labels(screen)

        if self.music_slider:
            self.music_slider.render(screen, self.value_font)
        if self.sfx_slider:
            self.sfx_slider.render(screen, self.value_font)

        self._render_checkbox(screen, self.music_checkbox_rect, self.music_enabled, self.hover_music_check)
        self._render_checkbox(screen, self.sfx_checkbox_rect, self.sfx_enabled, self.hover_sfx_check)
        self._render_checkbox(screen, self.fullscreen_checkbox_rect, self.fullscreen_enabled,
                              self.hover_fullscreen_check)
        self._render_checkbox(screen, self.vsync_checkbox_rect, self.vsync_enabled, self.hover_vsync_check)

        self._render_audio_hints(screen)
        self._render_video_hints(screen)

    def _render_shortcuts_tab(self, screen):
        """Renderiza a aba de atalhos do jogo"""
        vx = self.screen_manager.viewport_x
        vy = self.screen_manager.viewport_y
        vw = self.screen_manager.viewport_width
        vh = self.screen_manager.viewport_height

        panel_x = self.panel_rect.x + 30
        panel_y = self.panel_rect.y + 25
        panel_width = self.panel_rect.width - 60
        panel_height = self.panel_rect.height - 60

        # Título da seção
        title = self.category_font.render("LISTA DE ATALHOS", True, (220, 220, 230))
        title_rect = title.get_rect(center=(self.panel_rect.centerx, panel_y))
        screen.blit(title, title_rect)

        # Linha decorativa
        line_width = int(vw * 0.15)
        line_x = vx + (vw - line_width) // 2
        line_y = title_rect.bottom + 10
        pygame.draw.line(screen, (80, 70, 50), (line_x, line_y), (line_x + line_width, line_y), 2)

        # ===== ATALHOS =====
        shortcuts = [
            ("P", "Pausar / Despausar o jogo"),
            ("H", "Ocultar / Mostrar todas as UIs"),
            ("ESC", "Voltar / Fechar menus"),
            ("TAB", "Alternar categorias da Bolsa"),
            ("F1", "Ativar / Desativar debug"),
            ("U", "Desbloquear proxima fase (debug)"),
            ("A", "Desbloquear todas as fases (debug)"),
            ("CTRL+R", "Resetar progresso (debug)"),
        ]

        # Calcula layout em colunas
        col1_width = int(vw * 0.06)
        col2_width = int(vw * 0.30)
        spacing = int(vh * 0.022)

        start_y = line_y + int(vh * 0.03)
        row_height = int(vh * 0.035)
        rows_per_col = (len(shortcuts) + 1) // 2

        for i, (key, description) in enumerate(shortcuts):
            if i < rows_per_col:
                col = 0
                row = i
            else:
                col = 1
                row = i - rows_per_col

            x = panel_x + 20 + col * (col1_width + col2_width + int(vw * 0.025))
            y = start_y + row * (row_height + spacing)

            # Tecla (em destaque - dourado)
            key_color = (220, 190, 80)
            key_text = self.shortcut_font.render(key, True, key_color)
            screen.blit(key_text, (x, y))

            # Descrição
            desc_color = (200, 200, 210)
            desc_text = self.shortcut_font.render(description, True, desc_color)
            desc_x = x + col1_width + 12
            screen.blit(desc_text, (desc_x, y))

        # ===== RODAPÉ =====
        footer_y = self.panel_rect.y + self.panel_rect.height - 30
        footer_color = (100, 100, 120)
        footer_text = self.hint_font.render("Alguns atalhos funcionam apenas em modo debug", True, footer_color)
        footer_rect = footer_text.get_rect(center=(self.panel_rect.centerx, footer_y))
        screen.blit(footer_text, footer_rect)

    def _render_panel(self, screen):
        """Renderiza o painel principal com animação"""
        panel_scale = min(1.0, self.panel_animation_progress)
        if panel_scale < 1.0:
            scaled_rect = self.panel_rect.inflate(
                -self.panel_rect.width * (1 - panel_scale),
                -self.panel_rect.height * (1 - panel_scale)
            )
            scaled_rect.center = self.panel_rect.center
            render_rect = scaled_rect
        else:
            render_rect = self.panel_rect

        # Fundo do painel
        panel_surface = pygame.Surface((render_rect.width, render_rect.height), pygame.SRCALPHA)
        for i in range(render_rect.height):
            alpha = int(200 - (i / render_rect.height) * 40)
            pygame.draw.line(panel_surface, (20, 20, 35, alpha), (0, i), (render_rect.width, i))

        # Bordas
        pygame.draw.rect(panel_surface, (100, 85, 55), panel_surface.get_rect(), 3, border_radius=10)
        pygame.draw.rect(panel_surface, (160, 140, 100), panel_surface.get_rect().inflate(-3, -3), 1, border_radius=8)

        # Cantos decorativos
        corner_size = 18
        corner_color = (180, 160, 100)
        w, h = render_rect.width, render_rect.height

        corners = [
            (6, 6, corner_size, 6),
            (6, 6, 6, corner_size),
            (w - 6, 6, w - corner_size, 6),
            (w - 6, 6, w - 6, corner_size),
            (6, h - 6, corner_size, h - 6),
            (6, h - 6, 6, h - corner_size),
            (w - 6, h - 6, w - corner_size, h - 6),
            (w - 6, h - 6, w - 6, h - corner_size),
        ]

        for x1, y1, x2, y2 in corners:
            pygame.draw.line(panel_surface, corner_color, (x1, y1), (x2, y2), 2)

        # Linha divisória entre colunas (apenas na aba de áudio)
        if self.current_tab == "audio":
            mid_x = render_rect.width // 2
            pygame.draw.line(panel_surface, (100, 85, 55, 80), (mid_x, 30), (mid_x, h - 30), 1)

        screen.blit(panel_surface, render_rect)
        return render_rect

    def _render_categories(self, screen):
        """Renderiza os títulos das categorias"""
        if self.audio_category_rect:
            audio_text = self.category_font.render("AUDIO", True, (180, 160, 100))
            screen.blit(audio_text, (self.audio_category_rect.x, self.audio_category_rect.y))
            pygame.draw.line(
                screen, (100, 85, 55),
                (self.audio_category_rect.x, self.audio_category_rect.y + 26),
                (self.audio_category_rect.x + 70, self.audio_category_rect.y + 26),
                2
            )

        if self.video_category_rect:
            video_text = self.category_font.render("VIDEO", True, (180, 160, 100))
            screen.blit(video_text, (self.video_category_rect.x, self.video_category_rect.y))
            pygame.draw.line(
                screen, (100, 85, 55),
                (self.video_category_rect.x, self.video_category_rect.y + 26),
                (self.video_category_rect.x + 70, self.video_category_rect.y + 26),
                2
            )

    def _render_audio_labels(self, screen):
        """Renderiza os labels da seção de áudio"""
        if self.music_label_rect:
            music_label = self.label_font.render("MUSICA", True, (220, 220, 230))
            screen.blit(music_label, (self.music_label_rect.x, self.music_label_rect.y))

        if self.sfx_label_rect:
            sfx_label = self.label_font.render("EFEITOS", True, (220, 220, 230))
            screen.blit(sfx_label, (self.sfx_label_rect.x, self.sfx_label_rect.y))

    def _render_video_labels(self, screen):
        """Renderiza os labels da seção de vídeo"""
        if self.fullscreen_label_rect:
            fs_label = self.label_font.render("TELA CHEIA", True, (220, 220, 230))
            screen.blit(fs_label, (self.fullscreen_label_rect.x, self.fullscreen_label_rect.y))

        if self.vsync_label_rect:
            vsync_label = self.label_font.render("VSYNC", True, (220, 220, 230))
            screen.blit(vsync_label, (self.vsync_label_rect.x, self.vsync_label_rect.y))

    def _render_audio_hints(self, screen):
        """Renderiza as dicas da seção de áudio"""
        if self.music_hint_rect:
            music_hint = self.hint_font.render("Volume da musica", True, (110, 110, 130))
            screen.blit(music_hint, (self.music_hint_rect.x, self.music_hint_rect.y))

        if self.sfx_hint_rect:
            sfx_hint = self.hint_font.render("Volume dos efeitos", True, (110, 110, 130))
            screen.blit(sfx_hint, (self.sfx_hint_rect.x, self.sfx_hint_rect.y))

    def _render_video_hints(self, screen):
        """Renderiza as dicas da seção de vídeo"""
        if self.fullscreen_hint_rect:
            fs_hint = self.hint_font.render("Modo tela cheia", True, (110, 110, 130))
            screen.blit(fs_hint, (self.fullscreen_hint_rect.x, self.fullscreen_hint_rect.y))

        if self.vsync_hint_rect:
            vsync_hint = self.hint_font.render("Sincronizacao vertical", True, (110, 110, 130))
            screen.blit(vsync_hint, (self.vsync_hint_rect.x, self.vsync_hint_rect.y))

    def _render_checkbox(self, screen, rect, checked, hover):
        """Renderiza um checkbox estilizado"""
        if not rect:
            return

        check_rect = rect.inflate(4 if hover else 0, 4 if hover else 0)
        check_rect.center = rect.center

        if checked:
            bg_color = (80, 110, 70) if not hover else (100, 140, 85)
        else:
            bg_color = (40, 40, 55) if not hover else (55, 55, 70)

        pygame.draw.rect(screen, bg_color, check_rect, border_radius=4)
        pygame.draw.rect(screen, (100, 85, 55), check_rect, 2, border_radius=4)

        if checked:
            pygame.draw.line(screen, (200, 220, 150),
                             (check_rect.x + 5, check_rect.y + 5),
                             (check_rect.right - 5, check_rect.bottom - 5), 3)
            pygame.draw.line(screen, (200, 220, 150),
                             (check_rect.right - 5, check_rect.y + 5),
                             (check_rect.x + 5, check_rect.bottom - 5), 3)

    def _render_back_button(self, screen):
        """Renderiza o botão de voltar"""
        if not self.back_button:
            return

        # Sombra
        shadow_rect = self.back_button.copy()
        shadow_rect.y += 3
        pygame.draw.rect(screen, (10, 10, 15), shadow_rect, border_radius=8)

        # Fundo
        pygame.draw.rect(screen, (45, 45, 55), self.back_button, border_radius=8)
        pygame.draw.rect(screen, (100, 85, 55) if not self.hover_back else (140, 120, 80),
                         self.back_button, 2, border_radius=8)

        if self.hover_back:
            pygame.draw.rect(screen, (60, 55, 80), self.back_button.inflate(-2, -2), border_radius=6)

        font = pygame.font.Font(None, int(self.back_button.height * 0.6))
        text = font.render("<", True, (200, 200, 210))
        text_rect = text.get_rect(center=self.back_button.center)
        screen.blit(text, text_rect)

    def _render_button(self, screen, rect, text, hover):
        """Renderiza um botão estilizado"""
        if not rect:
            return

        # Sombra
        shadow_rect = rect.copy()
        shadow_rect.y += 3
        pygame.draw.rect(screen, (15, 15, 25), shadow_rect, border_radius=8)

        # Fundo
        if hover:
            bg_color = (80, 70, 55)
            border_color = (160, 140, 100)
            text_color = (255, 255, 255)
        else:
            bg_color = (50, 45, 40)
            border_color = (100, 85, 55)
            text_color = (200, 200, 200)

        pygame.draw.rect(screen, bg_color, rect, border_radius=8)
        pygame.draw.rect(screen, border_color, rect, 2, border_radius=8)

        # Glow no hover
        if hover:
            glow_rect = rect.inflate(4, 4)
            pygame.draw.rect(screen, (120, 100, 70, 50), glow_rect, 1, border_radius=10)

        # Texto
        font_size = int(rect.height * 0.45)
        button_font = pygame.font.Font(None, font_size)
        button_text = button_font.render(text, True, text_color)
        text_rect = button_text.get_rect(center=rect.center)
        screen.blit(button_text, text_rect)

    def _render_blocked_screen(self, screen):
        """Renderiza a tela de acesso bloqueado"""
        vx = self.screen_manager.viewport_x
        vy = self.screen_manager.viewport_y
        vw = self.screen_manager.viewport_width
        vh = self.screen_manager.viewport_height

        container_width = int(vw * 0.4)
        container_height = int(vh * 0.3)
        container_x = vx + (vw - container_width) // 2
        container_y = vy + (vh - container_height) // 2 - 60

        container_rect = pygame.Rect(container_x, container_y, container_width, container_height)

        pygame.draw.rect(screen, (20, 20, 35), container_rect, border_radius=10)
        pygame.draw.rect(screen, (100, 85, 55), container_rect, 3, border_radius=10)
        pygame.draw.rect(screen, (160, 140, 100), container_rect.inflate(-4, -4), 1, border_radius=8)

        title_font = self._get_font(int(vh * 0.04), True)
        title_text = title_font.render("ACESSO NEGADO", True, (220, 180, 80))
        title_x = container_x + (container_width - title_text.get_width()) // 2
        title_y = container_y + int(container_height * 0.15)
        screen.blit(title_text, (title_x, title_y))

        msg_font = self._get_font(int(vh * 0.025))
        lines = ["E necessario iniciar uma partida!", "", "Volte ao menu e selecione:", "NOVO JOGO"]

        line_y = title_y + int(container_height * 0.25)
        line_height = int(vh * 0.04)
        for line in lines:
            if line:
                msg_text = msg_font.render(line, True, (180, 180, 200))
                msg_x = container_x + (container_width - msg_text.get_width()) // 2
                screen.blit(msg_text, (msg_x, line_y))
            line_y += line_height

    def _get_font(self, size, bold=False):
        """Obtém uma fonte do render_context"""
        from src.core.render_context import render_context
        return render_context.get_font(size, bold)

    def _draw_gradient_background(self, screen):
        """Desenha o fundo com gradiente e estrelas (mesmo estilo do menu)"""
        width = self.screen_manager.window_width
        height = self.screen_manager.window_height

        # Gradiente
        for i in range(height):
            t = i / height
            r = int(10 + t * 20)
            g = int(12 + t * 25)
            b = int(25 + t * 35)
            pygame.draw.line(screen, (r, g, b), (0, i), (width, i))

        # Estrelas (mesmo padrão do menu)
        star_positions = [
            (0.03, 0.03), (0.08, 0.08), (0.15, 0.05), (0.22, 0.10), (0.30, 0.04),
            (0.38, 0.12), (0.45, 0.06), (0.52, 0.09), (0.60, 0.04), (0.68, 0.11),
            (0.75, 0.05), (0.82, 0.08), (0.90, 0.07), (0.95, 0.10), (0.05, 0.15),
            (0.12, 0.18), (0.88, 0.17), (0.93, 0.22), (0.02, 0.25), (0.98, 0.28),
        ]

        vx = self.screen_manager.viewport_x
        vy = self.screen_manager.viewport_y
        vw = self.screen_manager.viewport_width
        vh = self.screen_manager.viewport_height

        for i, (rx, ry) in enumerate(star_positions):
            x = vx + int(rx * vw)
            y = vy + int(ry * vh)
            alpha = int(60 + 80 * (0.5 + 0.5 * (self._animation_timer * 0.5 + i * 1.3) % 1))
            size = 1 + int(((i * 5) % 2))

            color = (200 + int(55 * (self._animation_timer * 0.3 + i) % 1),
                     200 + int(55 * (self._animation_timer * 0.4 + i + 1) % 1),
                     255)

            pygame.draw.circle(screen, color, (x, y), size)