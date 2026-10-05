# src/scenes/settings_scene/settings_logic.py
"""
Lógica da tela de configurações.
Só estado + métodos. Nenhum desenho, nenhum widget.
A casca (SettingsScene) amarra estes métodos às ações dos widgets.
"""
import pygame

from src.managers.sounds.sound_manager import sound_manager, SoundEffect
from src.managers.sounds.ambient_sound_manager import ambient_sound_manager


class SettingsLogic:
    def __init__(self, game, on_close_callback=None):
        self.game = game
        self.on_close_callback = on_close_callback

        # Estado inicial
        self.music_volume       = 0.5
        self.sfx_volume         = 0.7
        self.ambient_volume     = 0.5
        self.music_enabled      = True
        self.sfx_enabled        = True
        self.ambient_enabled    = True
        self.fullscreen_enabled = False
        self.vsync_enabled      = True

        self.preview_music_timer = 0
        self._load()

    # =================================================================
    # CARGA / PERSISTÊNCIA
    # =================================================================
    def _load(self):
        from src.config.settings import settings as gs
        from src.managers.save_manager import save_manager
        data = (save_manager.save_data or {}).get("settings", {}) or {}

        self.music_volume       = data.get("music_volume",   gs.music_volume)
        self.sfx_volume         = data.get("sfx_volume",     gs.sfx_volume)
        self.ambient_volume     = data.get("ambient_volume", getattr(gs, "ambient_volume", 0.5))
        self.music_enabled      = data.get("music_enabled",  gs.music_enabled)
        self.sfx_enabled        = data.get("sfx_enabled",    gs.sfx_enabled)
        self.ambient_enabled    = data.get("ambient_enabled", getattr(gs, "ambient_enabled", True))
        self.fullscreen_enabled = data.get("fullscreen",     gs.fullscreen)
        self.vsync_enabled      = data.get("vsync",          gs.vsync)

    # =================================================================
    # AÇÕES
    # =================================================================
    def apply_settings(self, *args):
        from src.config.settings import settings as gs
        from src.managers.save_manager import save_manager

        old_fs = gs.fullscreen
        old_vs = gs.vsync

        gs.music_volume       = self.music_volume
        gs.sfx_volume         = self.sfx_volume
        gs.ambient_volume     = self.ambient_volume
        gs.music_enabled      = self.music_enabled
        gs.sfx_enabled        = self.sfx_enabled
        gs.ambient_enabled    = self.ambient_enabled
        gs.fullscreen         = self.fullscreen_enabled
        gs.vsync              = self.vsync_enabled

        sound_manager.sync_all_managers()
        ambient_sound_manager.set_ambient_enabled(self.ambient_enabled)
        ambient_sound_manager.set_ambient_volume(
            self.ambient_volume if self.ambient_enabled else 0)

        if gs.fullscreen != old_fs:
            self.game.screen_manager.toggle_fullscreen()
        if gs.vsync != old_vs:
            self.game.screen_manager.initialize_screen()

        if save_manager.current_save_file:
            save_manager.save_settings(gs)

        sound_manager.play_effect(SoundEffect.CLICK)
        print("[SETTINGS] Aplicado e salvo.")

    def go_back(self, *args):
        sound_manager.stop_music()
        ambient_sound_manager.stop_ambient()
        self.preview_music_timer = 0
        if self.on_close_callback:
            cb = self.on_close_callback
            self.on_close_callback = None
            cb()
            return
        self.game.current_scene = self.game.menu_scene

    # =================================================================
    # CALLBACKS DOS WIDGETS
    # =================================================================
    def set_music_enabled(self, checked):
        self.music_enabled = bool(checked)
        self._apply_music_preview()
        sound_manager.play_effect(SoundEffect.CLICK)

    def set_sfx_enabled(self, checked):
        self.sfx_enabled = bool(checked)
        self._apply_sfx_preview()
        sound_manager.play_effect(SoundEffect.CLICK)

    def set_ambient_enabled(self, checked):
        self.ambient_enabled = bool(checked)
        self._apply_ambient_preview()
        sound_manager.play_effect(SoundEffect.CLICK)

    def set_fullscreen(self, checked):
        self.fullscreen_enabled = bool(checked)
        sound_manager.play_effect(SoundEffect.CLICK)

    def set_vsync(self, checked):
        self.vsync_enabled = bool(checked)
        sound_manager.play_effect(SoundEffect.CLICK)

    def set_music_volume(self, value):
        self.music_volume = float(value)
        self._apply_music_preview()

    def set_sfx_volume(self, value):
        self.sfx_volume = float(value)
        self._apply_sfx_preview()

    def set_ambient_volume(self, value):
        self.ambient_volume = float(value)
        self._apply_ambient_preview()

    # =================================================================
    # PREVIEW DE ÁUDIO
    # =================================================================
    def _apply_music_preview(self):
        if self.music_enabled:
            sound_manager.set_music_volume(self.music_volume)
            if not pygame.mixer.music.get_busy():
                try:
                    sound_manager.play_random_battle_music()
                    self.preview_music_timer = pygame.time.get_ticks()
                except Exception:
                    pass
        else:
            sound_manager.stop_music(fade_ms=200)
            self.preview_music_timer = 0

    def _apply_sfx_preview(self):
        sound_manager.set_sfx_volume(self.sfx_volume if self.sfx_enabled else 0)

    def _apply_ambient_preview(self):
        if self.ambient_enabled and self.ambient_volume > 0:
            ambient_sound_manager.set_ambient_volume(self.ambient_volume)
        else:
            ambient_sound_manager.stop_ambient()

    # =================================================================
    def update(self, dt):
        if self.preview_music_timer > 0 and self.music_enabled:
            if pygame.time.get_ticks() - self.preview_music_timer > 3000:
                sound_manager.stop_music(fade_ms=500)
                self.preview_music_timer = 0