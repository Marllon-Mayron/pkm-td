# src/scenes/game_scene/components/overlay_manager.py

from enum import Enum

from src.scenes.game_scene.components.overlays.game_over_overlay import GameOverOverlay
from src.scenes.game_scene.components.overlays.phase_complete_overlay import PhaseCompleteOverlay


class OverlayType(Enum):
    NONE = "none"
    GAME_OVER = "game_over"
    PHASE_COMPLETE = "phase_complete"


class OverlayManager:
    """Gerencia os diferentes overlays do jogo"""

    def __init__(self, game_scene):
        self.game_scene = game_scene
        self.current_overlay = None
        self.current_type = OverlayType.NONE

        # Cria os overlays
        self.overlays = {
            OverlayType.GAME_OVER: GameOverOverlay(game_scene),
            OverlayType.PHASE_COMPLETE: PhaseCompleteOverlay(game_scene)
        }

    def show(self, overlay_type):
        """Ativa um overlay"""
        if overlay_type in self.overlays:
            self.current_type = overlay_type
            self.current_overlay = self.overlays[overlay_type]
            self.current_overlay.active = True
            self.current_overlay.timer = 0

    def hide(self):
        """Desativa o overlay atual"""
        if self.current_overlay:
            self.current_overlay.active = False
        self.current_overlay = None
        self.current_type = OverlayType.NONE

    def handle_event(self, event):
        """Delega eventos para o overlay atual"""
        if self.current_overlay and self.current_overlay.active:
            return self.current_overlay.handle_event(event)
        return False

    def update(self, dt):
        """Atualiza o overlay atual"""
        if self.current_overlay and self.current_overlay.active:
            self.current_overlay.update(dt)

    def render(self, screen):
        """Renderiza o overlay atual"""
        if self.current_overlay and self.current_overlay.active:
            self.current_overlay.render(screen)

    @property
    def is_active(self):
        """Verifica se há algum overlay ativo"""
        return self.current_overlay is not None and self.current_overlay.active