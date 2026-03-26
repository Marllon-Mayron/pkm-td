# src/scenes/game_scene/components/overlay_manager.py

from enum import Enum

from src.scenes.game_scene.components.overlays.game_over_overlay import GameOverOverlay
from src.scenes.game_scene.components.overlays.phase_complete_overlay import PhaseCompleteOverlay
from src.scenes.game_scene.components.overlays.capture_overlay import CaptureOverlay  # NOVO


class OverlayType(Enum):
    NONE = "none"
    GAME_OVER = "game_over"
    PHASE_COMPLETE = "phase_complete"
    CAPTURE = "capture"  # NOVO


class OverlayManager:
    """Gerencia os diferentes overlays do jogo"""

    def __init__(self, game_scene):
        self.game_scene = game_scene
        self.current_overlay = None
        self.current_type = OverlayType.NONE

    def show(self, overlay_type, **kwargs):
        """Ativa um overlay - Cria o overlay no momento da exibição"""
        self.current_type = overlay_type

        # Cria o overlay apenas quando for mostrar
        if overlay_type == OverlayType.GAME_OVER:
            self.current_overlay = GameOverOverlay(self.game_scene)
        elif overlay_type == OverlayType.PHASE_COMPLETE:
            self.current_overlay = PhaseCompleteOverlay(self.game_scene)
            print(f"[OVERLAY] PhaseCompleteOverlay criado com dados: {self.game_scene.phase_complete_data}")
        elif overlay_type == OverlayType.CAPTURE:  # NOVO
            pokemon = kwargs.get('pokemon')
            is_to_team = kwargs.get('is_to_team', True)
            if pokemon:
                self.current_overlay = CaptureOverlay(self.game_scene, pokemon, is_to_team)
            else:
                self.current_overlay = None
                return
        else:
            self.current_overlay = None
            return

        self.current_overlay.active = True

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