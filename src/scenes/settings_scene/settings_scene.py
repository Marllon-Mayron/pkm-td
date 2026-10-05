# src/scenes/settings_scene/settings_scene.py
"""
Tela de configurações — casca.
Junta o layout visual (JSON) com a lógica (SettingsLogic).
"""
from src.ui.screen_template import StandardScreen
from src.ui.screen_loader import ScreenLoader
from src.scenes.settings_scene.settings_logic import SettingsLogic


class SettingsScene(StandardScreen):
    title = ""
    show_back_button = False

    def __init__(self, game, on_back_callback=None):
        self.logic = SettingsLogic(game, on_close_callback=on_back_callback)
        super().__init__(game)
        self._sync_widgets_from_logic()

    # =================================================================
    def build(self):
        ScreenLoader.load(self, "res/ui_layouts/settings.json")
        self.set_active_tab("Audio")

    def get_actions(self):
        return {
            "go_back":           self.logic.go_back,
            "apply":             self.logic.apply_settings,
            "set_tab":           self.set_active_tab,       # builtin
            "toggle_music":      self.logic.set_music_enabled,
            "toggle_sfx":        self.logic.set_sfx_enabled,
            "toggle_ambient":    self.logic.set_ambient_enabled,
            "toggle_fullscreen": self.logic.set_fullscreen,
            "toggle_vsync":      self.logic.set_vsync,
            "slider_music":      self.logic.set_music_volume,
        }

    # =================================================================
    def _sync_widgets_from_logic(self):
        """Alinha os widgets do JSON com o estado carregado do save."""
        L = self.logic
        for wid, val in (
            ("cb_music",      L.music_enabled),
            ("cb_sfx",        L.sfx_enabled),
            ("cb_ambient",    L.ambient_enabled),
            ("cb_fullscreen", L.fullscreen_enabled),
            ("cb_vsync",      L.vsync_enabled),
        ):
            w = self.get(wid)
            if w is not None and hasattr(w, "checked"):
                w.checked = bool(val)

        w = self.get("sl_music")
        if w is not None and hasattr(w, "value"):
            w.value = float(L.music_volume)

    # =================================================================
    def on_back(self):
        self.logic.go_back()

    def update(self, dt):
        self.logic.update(dt)