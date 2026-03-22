# src/scenes/game_scene/components/renderer/map_renderer.py

"""
Renderizador de mapa - SIMPLIFICADO
"""
from src.scenes.game_scene.components.managers.game_layer_manager import GameLayerManager


class MapRenderer:
    """Renderiza o mapa da fase"""

    def __init__(self):
        self.layer_manager = GameLayerManager()
        self.loaded = False

    def load_from_data(self, map_data: dict, base_path: str = ""):
        """Carrega o mapa a partir dos dados"""
        if not map_data:
            return False

        try:
            self.layer_manager.load_from_dict(map_data, base_path)
            self.loaded = True
            return True
        except Exception as e:
            print(f"Erro ao carregar mapa: {e}")
            return False

    def render(self, screen, camera, screen_manager):
        """Renderiza o mapa - SEM CACHE PARA GARANTIR ALINHAMENTO"""
        if not self.loaded:
            return
        self.layer_manager.render_all(screen, camera, screen_manager)

    def get_dimensions(self):
        if not self.loaded:
            return (0, 0)
        return self.layer_manager.get_dimensions()

    def invalidate_cache(self):
        self.layer_manager.invalidate_cache()