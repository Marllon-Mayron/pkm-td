# src/scenes/settings_scene.py

"""
Cena de configurações do jogo - Interface gameficada e responsiva
"""
import pygame
import os
from src.scenes.base_scene import BaseScene
from src.managers.sounds.sound_manager import sound_manager, SoundEffect


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
        self.rect = pygame.Rect(abs_x, abs_y, abs_width, 24)

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
        pygame.draw.rect(screen, (25, 25, 35), self.rect, border_radius=4)

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

        pygame.draw.rect(screen, (80, 80, 100), self.rect, 2, border_radius=4)

        thumb_x = self.rect.x + fill_width - 6
        thumb_rect = pygame.Rect(thumb_x, self.rect.y - 3, 12, self.rect.height + 6)
        thumb_color = (220, 220, 240) if self.dragging else (180, 180, 210)
        pygame.draw.rect(screen, thumb_color, thumb_rect, border_radius=3)
        pygame.draw.rect(screen, (100, 100, 120), thumb_rect, 1, border_radius=3)

        percent = int((self.value - self.min_val) / (self.max_val - self.min_val) * 100)
        value_text = font.render(f"{percent}%", True, (150, 150, 170))
        value_rect = value_text.get_rect(midleft=(self.rect.right + 12, self.rect.centery))
        screen.blit(value_text, value_rect)


class SettingsScene(BaseScene):
    def __init__(self, game, on_back_callback=None):
        super().__init__(game)

        self.title_font = None
        self.label_font = None
        self.value_font = None
        self.hint_font = None
        self.category_font = None

        self.back_button = None
        self.apply_button = None
        self.reset_button = None

        self.left_col_x = 0.12
        self.right_col_x = 0.62

        self.row_height = 0.12
        self.label_y_offset = 0.05
        self.checkbox_y_offset = 0.055
        self.slider_y_offset = 0.09
        self.hint_y_offset = 0.115

        self.music_label_rect = None
        self.music_checkbox_rect = None
        self.music_hint_rect = None

        self.sfx_label_rect = None
        self.sfx_checkbox_rect = None
        self.sfx_hint_rect = None

        self.fullscreen_label_rect = None
        self.fullscreen_checkbox_rect = None
        self.fullscreen_hint_rect = None

        self.vsync_label_rect = None
        self.vsync_checkbox_rect = None
        self.vsync_hint_rect = None

        self.audio_category_rect = None
        self.video_category_rect = None

        self.music_slider = None
        self.sfx_slider = None

        # ===== CALLBACK =====
        self._on_back_callback = on_back_callback

        self.has_save = self._check_any_save_exists()
        self.state = "normal" if self.has_save else "blocked"

        print(f"[SETTINGS] Tem save? {self.has_save} - Estado: {self.state}")

        if self.has_save:
            self._load_settings_from_save()
        else:
            self._load_default_settings()

        self.hover_back = False
        self.hover_apply = False
        self.hover_reset = False
        self.hover_music_check = False
        self.hover_sfx_check = False
        self.hover_fullscreen_check = False
        self.hover_vsync_check = False

        self.preview_music_timer = 0
        self._create_layout()

        self.panel_animation_progress = 0
        self._scanline_offset = 0

    def _check_any_save_exists(self):
        from src.managers.save_manager import save_manager

        if save_manager.current_save_file is not None and save_manager.save_data is not None:
            return True

        saves_dir = "saves"
        if os.path.exists(saves_dir):
            for i in range(1, 4):
                save_file = os.path.join(saves_dir, f"save_{i}.json")
                if os.path.exists(save_file):
                    try:
                        import json
                        with open(save_file, 'r', encoding='utf-8') as f:
                            data = json.load(f)
                            if data.get("settings"):
                                save_manager.save_data = data
                                save_manager.current_save_file = i
                                return True
                    except Exception as e:
                        print(f"[SETTINGS] Erro ao ler save {i}: {e}")

        if len(self.game.player.team) > 0 or len(self.game.player.pc_box) > 0:
            return True

        return False

    def _load_settings_from_save(self):
        from src.managers.save_manager import save_manager

        if save_manager.save_data and save_manager.save_data.get("settings"):
            settings_data = save_manager.save_data.get("settings", {})
        else:
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
                                save_manager.save_data = data
                                save_manager.current_save_file = i
                                break
                    except:
                        pass

        self.music_volume = settings_data.get("music_volume", 0.5)
        self.sfx_volume = settings_data.get("sfx_volume", 0.7)
        self.music_enabled = settings_data.get("music_enabled", True)
        self.sfx_enabled = settings_data.get("sfx_enabled", True)
        self.fullscreen_enabled = settings_data.get("fullscreen", False)
        self.vsync_enabled = settings_data.get("vsync", True)

    def _load_default_settings(self):
        self.music_volume = 0.5
        self.sfx_volume = 0.7
        self.music_enabled = True
        self.sfx_enabled = True
        self.fullscreen_enabled = False
        self.vsync_enabled = True

    def _get_font_size(self, base_size):
        return max(int(base_size * self.screen_manager.viewport_height / 720), 12)

    def _create_layout(self):
        vx = self.screen_manager.viewport_x
        vy = self.screen_manager.viewport_y
        vw = self.screen_manager.viewport_width
        vh = self.screen_manager.viewport_height

        self.title_font = pygame.font.Font(None, self._get_font_size(52))
        self.label_font = pygame.font.Font(None, self._get_font_size(24))
        self.value_font = pygame.font.Font(None, self._get_font_size(20))
        self.hint_font = pygame.font.Font(None, self._get_font_size(18))
        self.category_font = pygame.font.Font(None, self._get_font_size(22))

        back_size = int(min(vw * 0.045, vh * 0.065, 40))
        self.back_button = pygame.Rect(vx + 20, vy + 20, back_size, back_size)

        panel_width = int(vw * 0.75)
        panel_height = int(vh * 0.7)
        panel_x = vx + (vw - panel_width) // 2
        panel_y = vy + int(vh * 0.12)
        self.panel_rect = pygame.Rect(panel_x, panel_y, panel_width, panel_height)

        category_y = panel_y + int(panel_height * 0.03)
        self.audio_category_rect = pygame.Rect(panel_x + 20, category_y, 100, 30)
        self.video_category_rect = pygame.Rect(panel_x + panel_width // 2 + 20, category_y, 100, 30)

        self._update_rects(vx, vy, vw, vh, panel_y, panel_height)

    def _update_rects(self, vx, vy, vw, vh, panel_y, panel_height):
        item_height = panel_height * 0.12
        start_y = panel_y + panel_height * 0.12

        left_x = vx + vw * self.left_col_x
        right_x = vx + vw * self.right_col_x

        label_width = int(vw * 0.1)
        checkbox_size = int(vh * 0.033)
        hint_width = int(vw * 0.2)
        slider_width = vw * 0.3

        row_y = start_y

        self.music_label_rect = pygame.Rect(left_x, row_y, label_width, int(item_height * 0.3))
        self.music_checkbox_rect = pygame.Rect(
            left_x + label_width + 10,
            row_y + (int(item_height * 0.3) - checkbox_size) // 2,
            checkbox_size, checkbox_size
        )

        hint_y = row_y + int(item_height * 0.35)
        self.music_hint_rect = pygame.Rect(left_x, hint_y, hint_width, int(item_height * 0.2))

        slider_y = hint_y + int(item_height * 0.25)
        if not self.music_slider:
            self.music_slider = Slider(left_x / vw, slider_y / vh, slider_width / vw, self.music_volume)
            self.music_slider.is_music = True
        else:
            self.music_slider.relative_x = left_x / vw
            self.music_slider.relative_y = slider_y / vh
            self.music_slider.relative_width = slider_width / vw
        self.music_slider.update_rect(vx, vy, vw, vh)

        row_y = start_y + int(item_height * 1.2)

        self.sfx_label_rect = pygame.Rect(left_x, row_y, label_width, int(item_height * 0.3))
        self.sfx_checkbox_rect = pygame.Rect(
            left_x + label_width + 10,
            row_y + (int(item_height * 0.3) - checkbox_size) // 2,
            checkbox_size, checkbox_size
        )

        hint_y = row_y + int(item_height * 0.35)
        self.sfx_hint_rect = pygame.Rect(left_x, hint_y, hint_width, int(item_height * 0.2))

        slider_y = hint_y + int(item_height * 0.25)
        if not self.sfx_slider:
            self.sfx_slider = Slider(left_x / vw, slider_y / vh, slider_width / vw, self.sfx_volume)
            self.sfx_slider.is_music = False
        else:
            self.sfx_slider.relative_x = left_x / vw
            self.sfx_slider.relative_y = slider_y / vh
            self.sfx_slider.relative_width = slider_width / vw
        self.sfx_slider.update_rect(vx, vy, vw, vh)

        row_y = start_y

        self.fullscreen_label_rect = pygame.Rect(right_x, row_y, int(label_width * 1.2), int(item_height * 0.3))
        self.fullscreen_checkbox_rect = pygame.Rect(
            right_x + int(label_width * 1.2) + 10,
            row_y + (int(item_height * 0.3) - checkbox_size) // 2,
            checkbox_size, checkbox_size
        )

        hint_y = row_y + int(item_height * 0.35)
        self.fullscreen_hint_rect = pygame.Rect(right_x, hint_y, hint_width, int(item_height * 0.2))

        row_y = start_y + int(item_height * 1.2)

        self.vsync_label_rect = pygame.Rect(right_x, row_y, label_width, int(item_height * 0.3))
        self.vsync_checkbox_rect = pygame.Rect(
            right_x + label_width + 10,
            row_y + (int(item_height * 0.3) - checkbox_size) // 2,
            checkbox_size, checkbox_size
        )

        hint_y = row_y + int(item_height * 0.35)
        self.vsync_hint_rect = pygame.Rect(right_x, hint_y, hint_width, int(item_height * 0.2))

        button_width = int(vw * 0.1)
        button_height = int(vh * 0.055)
        button_spacing = int(vw * 0.02)
        total_width = button_width * 2 + button_spacing
        buttons_y = panel_y + panel_height - button_height - int(vh * 0.02)
        buttons_x = vx + (vw - total_width) // 2
        self.apply_button = pygame.Rect(buttons_x, buttons_y, button_width, button_height)
        self.reset_button = pygame.Rect(buttons_x + button_width + button_spacing, buttons_y, button_width, button_height)

    def handle_event(self, event):
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
            self.hover_back = self.back_button.collidepoint(event.pos) if self.back_button else False
            self.hover_apply = self.apply_button.collidepoint(event.pos) if self.apply_button else False
            self.hover_reset = self.reset_button.collidepoint(event.pos) if self.reset_button else False
            self.hover_music_check = self.music_checkbox_rect.collidepoint(event.pos) if self.music_checkbox_rect else False
            self.hover_sfx_check = self.sfx_checkbox_rect.collidepoint(event.pos) if self.sfx_checkbox_rect else False
            self.hover_fullscreen_check = self.fullscreen_checkbox_rect.collidepoint(event.pos) if self.fullscreen_checkbox_rect else False
            self.hover_vsync_check = self.vsync_checkbox_rect.collidepoint(event.pos) if self.vsync_checkbox_rect else False

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

        if not save_manager.current_save_file:
            print("[SETTINGS] Não é possível salvar - nenhum save carregado!")
            sound_manager.play_effect(SoundEffect.CLICK)
            return

        settings.music_volume = self.music_volume
        settings.sfx_volume = self.sfx_volume
        settings.music_enabled = self.music_enabled
        settings.sfx_enabled = self.sfx_enabled
        settings.fullscreen = self.fullscreen_enabled
        settings.vsync = self.vsync_enabled

        sound_manager.sync_all_managers()

        if save_manager.save_data:
            old_fullscreen = save_manager.save_data["settings"].get("fullscreen", False)
            if self.fullscreen_enabled != old_fullscreen:
                self.screen_manager.toggle_fullscreen()

        save_manager.save_settings(settings)
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

        if save_manager.current_save_file and save_manager.save_data:
            settings_data = save_manager.save_data.get("settings", {})
            music_vol = settings_data.get("music_volume", 0.5)
            music_en = settings_data.get("music_enabled", True)
            if music_en and music_vol > 0:
                pygame.time.wait(100)
                sound_manager.set_music_volume(music_vol)
                sound_manager.stop_music()

        self.preview_music_timer = 0

        if self._on_back_callback is not None:
            print("[SETTINGS] Voltando via callback")
            callback = self._on_back_callback
            self._on_back_callback = None
            callback()
            return  # <--- ESSA LINHA É CRUCIAL!

        print("[SETTINGS] Voltando para o menu")
        self.game.current_scene = self.game.menu_scene

    def update(self, dt):
        if self.preview_music_timer > 0 and self.music_enabled:
            if pygame.time.get_ticks() - self.preview_music_timer > 3000:
                sound_manager.stop_music(fade_ms=500)
                self.preview_music_timer = 0

        self.panel_animation_progress = min(1.0, self.panel_animation_progress + dt * 3)
        self._scanline_offset = (self._scanline_offset + 1) % 4

    def fixed_update(self, dt):
        pass

    def render(self, screen):
        self._draw_gradient_background(screen)

        vx = self.screen_manager.viewport_x
        vy = self.screen_manager.viewport_y
        vw = self.screen_manager.viewport_width
        vh = self.screen_manager.viewport_height

        panel_width = int(vw * 0.75)
        panel_height = int(vh * 0.7)
        panel_x = vx + (vw - panel_width) // 2
        panel_y = vy + int(vh * 0.12)

        self._update_rects(vx, vy, vw, vh, panel_y, panel_height)

        title = self.title_font.render("CONFIGURATIONS", True, (255, 255, 255))
        title_shadow = self.title_font.render("CONFIGURATIONS", True, (30, 30, 45))
        title_x = vx + (vw - title.get_width()) // 2
        title_y = vy + int(vh * 0.03)
        screen.blit(title_shadow, (title_x + 2, title_y + 2))
        screen.blit(title, (title_x, title_y))

        bar_width = int(vw * 0.12)
        bar_x = vx + (vw - bar_width) // 2
        bar_y = title_y + title.get_height() + 6
        pygame.draw.rect(screen, (100, 85, 55), (bar_x, bar_y, bar_width, 3), border_radius=2)

        if self.state == "blocked":
            self._render_blocked_screen(screen)
            self._render_back_button(screen)
            return

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

        panel_surface = pygame.Surface((render_rect.width, render_rect.height), pygame.SRCALPHA)
        for i in range(render_rect.height):
            alpha = int(200 - (i / render_rect.height) * 40)
            pygame.draw.line(panel_surface, (20, 20, 35, alpha), (0, i), (render_rect.width, i))

        pygame.draw.rect(panel_surface, (100, 85, 55), panel_surface.get_rect(), 3, border_radius=8)
        pygame.draw.rect(panel_surface, (160, 140, 100), panel_surface.get_rect().inflate(-2, -2), 1, border_radius=6)

        corner_size = 20
        corner_color = (180, 160, 100)
        w, h = render_rect.width, render_rect.height
        pygame.draw.line(panel_surface, corner_color, (6, 6), (corner_size, 6), 2)
        pygame.draw.line(panel_surface, corner_color, (6, 6), (6, corner_size), 2)
        pygame.draw.line(panel_surface, corner_color, (w - 6, 6), (w - corner_size, 6), 2)
        pygame.draw.line(panel_surface, corner_color, (w - 6, 6), (w - 6, corner_size), 2)
        pygame.draw.line(panel_surface, corner_color, (6, h - 6), (corner_size, h - 6), 2)
        pygame.draw.line(panel_surface, corner_color, (6, h - 6), (6, h - corner_size), 2)
        pygame.draw.line(panel_surface, corner_color, (w - 6, h - 6), (w - corner_size, h - 6), 2)
        pygame.draw.line(panel_surface, corner_color, (w - 6, h - 6), (w - 6, h - corner_size), 2)

        mid_x = render_rect.width // 2
        pygame.draw.line(panel_surface, (100, 85, 55, 100), (mid_x, 30), (mid_x, h - 30), 1)

        screen.blit(panel_surface, render_rect)

        self._render_categories(screen)
        self._render_audio_labels(screen)
        self._render_video_labels(screen)

        if self.music_slider:
            self.music_slider.render(screen, self.value_font)
        if self.sfx_slider:
            self.sfx_slider.render(screen, self.value_font)

        self._render_checkbox(screen, self.music_checkbox_rect, self.music_enabled, self.hover_music_check)
        self._render_checkbox(screen, self.sfx_checkbox_rect, self.sfx_enabled, self.hover_sfx_check)
        self._render_checkbox(screen, self.fullscreen_checkbox_rect, self.fullscreen_enabled, self.hover_fullscreen_check)
        self._render_checkbox(screen, self.vsync_checkbox_rect, self.vsync_enabled, self.hover_vsync_check)

        self._render_audio_hints(screen)
        self._render_video_hints(screen)

        self._render_back_button(screen)
        self._render_button(screen, self.apply_button, "APLICAR", self.hover_apply)
        self._render_button(screen, self.reset_button, "PADRAO", self.hover_reset)

    def _render_categories(self, screen):
        if self.audio_category_rect:
            audio_text = self.category_font.render("AUDIO", True, (180, 160, 100))
            screen.blit(audio_text, (self.audio_category_rect.x, self.audio_category_rect.y))
            pygame.draw.line(screen, (100, 85, 55),
                             (self.audio_category_rect.x, self.audio_category_rect.y + 25),
                             (self.audio_category_rect.x + 80, self.audio_category_rect.y + 25), 2)

        if self.video_category_rect:
            video_text = self.category_font.render("VIDEO", True, (180, 160, 100))
            screen.blit(video_text, (self.video_category_rect.x, self.video_category_rect.y))
            pygame.draw.line(screen, (100, 85, 55),
                             (self.video_category_rect.x, self.video_category_rect.y + 25),
                             (self.video_category_rect.x + 80, self.video_category_rect.y + 25), 2)

    def _render_audio_labels(self, screen):
        if self.music_label_rect:
            music_label = self.label_font.render("MUSIC", True, (220, 220, 230))
            screen.blit(music_label, (self.music_label_rect.x, self.music_label_rect.y))

        if self.sfx_label_rect:
            sfx_label = self.label_font.render("SOUND FX", True, (220, 220, 230))
            screen.blit(sfx_label, (self.sfx_label_rect.x, self.sfx_label_rect.y))

    def _render_video_labels(self, screen):
        if self.fullscreen_label_rect:
            fs_label = self.label_font.render("FULLSCREEN", True, (220, 220, 230))
            screen.blit(fs_label, (self.fullscreen_label_rect.x, self.fullscreen_label_rect.y))

        if self.vsync_label_rect:
            vsync_label = self.label_font.render("VSYNC", True, (220, 220, 230))
            screen.blit(vsync_label, (self.vsync_label_rect.x, self.vsync_label_rect.y))

    def _render_audio_hints(self, screen):
        if self.music_hint_rect:
            music_hint = self.hint_font.render("Volume das Musicas", True, (110, 110, 130))
            screen.blit(music_hint, (self.music_hint_rect.x, self.music_hint_rect.y))

        if self.sfx_hint_rect:
            sfx_hint = self.hint_font.render("Volume dos Efeitos", True, (110, 110, 130))
            screen.blit(sfx_hint, (self.sfx_hint_rect.x, self.sfx_hint_rect.y))

    def _render_video_hints(self, screen):
        if self.fullscreen_hint_rect:
            fs_hint = self.hint_font.render("Tela Cheia", True, (110, 110, 130))
            screen.blit(fs_hint, (self.fullscreen_hint_rect.x, self.fullscreen_hint_rect.y))

        if self.vsync_hint_rect:
            vsync_hint = self.hint_font.render("Sincronizacao Vertical", True, (110, 110, 130))
            screen.blit(vsync_hint, (self.vsync_hint_rect.x, self.vsync_hint_rect.y))

    def _render_checkbox(self, screen, rect, checked, hover):
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
                             (check_rect.x + 6, check_rect.y + 6),
                             (check_rect.right - 6, check_rect.bottom - 6), 3)
            pygame.draw.line(screen, (200, 220, 150),
                             (check_rect.right - 6, check_rect.y + 6),
                             (check_rect.x + 6, check_rect.bottom - 6), 3)

    def _render_back_button(self, screen):
        if not self.back_button:
            return

        pygame.draw.rect(screen, (30, 30, 45), self.back_button, border_radius=6)
        pygame.draw.rect(screen, (100, 85, 55) if not self.hover_back else (140, 120, 80),
                         self.back_button, 2, border_radius=6)

        if self.hover_back:
            pygame.draw.rect(screen, (60, 55, 80), self.back_button.inflate(-2, -2), border_radius=4)

        font = pygame.font.Font(None, int(self.back_button.height * 0.6))
        text = font.render("<", True, (200, 200, 210))
        text_rect = text.get_rect(center=self.back_button.center)
        screen.blit(text, text_rect)

    def _render_button(self, screen, rect, text, hover):
        if not rect:
            return

        shadow_rect = rect.copy()
        shadow_rect.y += 3
        pygame.draw.rect(screen, (15, 15, 25), shadow_rect, border_radius=6)

        if hover:
            bg_color = (80, 70, 55)
            border_color = (160, 140, 100)
            text_color = (255, 255, 255)
        else:
            bg_color = (50, 45, 40)
            border_color = (100, 85, 55)
            text_color = (200, 200, 200)

        pygame.draw.rect(screen, bg_color, rect, border_radius=6)
        pygame.draw.rect(screen, border_color, rect, 2, border_radius=6)

        if hover:
            glow_rect = rect.inflate(4, 4)
            pygame.draw.rect(screen, (120, 100, 70, 50), glow_rect, 1, border_radius=8)

        font_size = int(rect.height * 0.45)
        button_font = pygame.font.Font(None, font_size)
        button_text = button_font.render(text, True, text_color)
        text_rect = button_text.get_rect(center=rect.center)
        screen.blit(button_text, text_rect)

    def _render_blocked_screen(self, screen):
        vx = self.screen_manager.viewport_x
        vy = self.screen_manager.viewport_y
        vw = self.screen_manager.viewport_width
        vh = self.screen_manager.viewport_height

        container_width = int(vw * 0.4)
        container_height = int(vh * 0.3)
        container_x = vx + (vw - container_width) // 2
        container_y = vy + (vh - container_height) // 2 - 60

        container_rect = pygame.Rect(container_x, container_y, container_width, container_height)

        pygame.draw.rect(screen, (20, 20, 35), container_rect, border_radius=8)
        pygame.draw.rect(screen, (100, 85, 55), container_rect, 3, border_radius=8)
        pygame.draw.rect(screen, (160, 140, 100), container_rect.inflate(-4, -4), 1, border_radius=6)

        title_font = self._get_font(int(vh * 0.04), True)
        title_text = title_font.render("ACCESS DENIED", True, (220, 180, 80))
        title_x = container_x + (container_width - title_text.get_width()) // 2
        title_y = container_y + int(container_height * 0.15)
        screen.blit(title_text, (title_x, title_y))

        msg_font = self._get_font(int(vh * 0.025))
        lines = ["You need to start a game first!", "", "Return to main menu and select:", "NEW GAME"]

        line_y = title_y + int(container_height * 0.25)
        line_height = int(vh * 0.04)
        for line in lines:
            if line:
                msg_text = msg_font.render(line, True, (180, 180, 200))
                msg_x = container_x + (container_width - msg_text.get_width()) // 2
                screen.blit(msg_text, (msg_x, line_y))
            line_y += line_height

    def _get_font(self, size, bold=False):
        from src.core.render_context import render_context
        return render_context.get_font(size, bold)

    def _draw_gradient_background(self, screen):
        width = self.screen_manager.window_width
        height = self.screen_manager.window_height

        for i in range(height):
            t = i / height
            r = int(15 + t * 10)
            g = int(18 + t * 12)
            b = int(25 + t * 15)
            pygame.draw.line(screen, (r, g, b), (0, i), (width, i))

        for i in range(self._scanline_offset, height, 4):
            pygame.draw.line(screen, (5, 5, 10, 30), (0, i), (width, i), 1)