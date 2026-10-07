# src/scenes/game_scene/components/overlays/game_over_scene/game_over_scene.py
"""
Overlay Game Over — StandardScreen + JSON.

Uso:
    scene = GameOverScene(game, game_scene, stats={
        "reason": "team_defeated",     # ou "items_stolen"
        "items_stolen": 3,             # só se reason == "items_stolen"
    })
    game.current_scene = scene
"""
import pygame

from src.ui.screen_template import StandardScreen
from src.ui.screen_loader import ScreenLoader
from src.scenes.game_scene.components.overlays.game_over_scene.game_over_logic import (
    GameOverLogic,
)


LAYOUT_PATH = "res/ui_layouts/game_over.json"


class GameOverScene(StandardScreen):
    title = ""
    show_back_button = False

    # =================================================================
    def __init__(self, game, game_scene, stats=None):
        self.game_scene = game_scene
        self.logic = GameOverLogic(game, game_scene, stats)

        # Snapshot do jogo como fundo
        try:
            w = game.screen_manager.window_width
            h = game.screen_manager.window_height
            self.background_image = pygame.Surface((w, h))
            game_scene.render(self.background_image)
            self.background_dim = 0   # o bg_dim do JSON já escurece
        except Exception as e:
            print(f"[GameOverScene] snapshot falhou: {e}")
            self.background_image = None
            self.background_dim = 0

        # Pausa o game_scene
        game_scene.game_paused = True
        game_scene.paused = True
        if hasattr(game_scene, "wave_manager"):
            game_scene.wave_manager.paused = True

        super().__init__(game)

    # =================================================================
    def build(self):
        ScreenLoader.load(self, LAYOUT_PATH)
        self._populate_dynamic()

    def get_actions(self):
        return {
            "retry":        self._on_retry,
            "team":         self._on_team,
            "phase_select": self._on_phase_select,
        }

    # =================================================================
    def _populate_dynamic(self):
        title = self.get("lbl_title")
        if title is not None:
            title.text = self.logic.get_title()

        reason = self.get("lbl_reason")
        if reason is not None:
            reason.text = self.logic.get_reason_text()

        gold = self.get("lbl_gold")
        if gold is not None:
            gold.text = self.logic.get_gold_text()

    # =================================================================
    def _on_retry(self, btn=None):
        self.logic.retry()

    def _on_team(self, btn=None):
        self.logic.go_team_select()

    def _on_phase_select(self, btn=None):
        self.logic.go_phase_select()

    # =================================================================
    def on_back(self):
        self._on_team()

    def _unpause(self):
        try:
            self.game_scene.game_paused = False
            self.game_scene.paused = False
            if hasattr(self.game_scene, "wave_manager"):
                self.game_scene.wave_manager.paused = False
        except Exception as e:
            print(f"[GameOverScene] unpause: {e}")

    def handle_event(self, event):
        if event.type == pygame.KEYDOWN:
            if event.key == pygame.K_ESCAPE:
                self._on_team()
                return
        super().handle_event(event)