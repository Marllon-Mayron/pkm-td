"""
Renderizador de mapa - Desenha o mapa da fase
"""
import pygame
from src.editor.layer_manager import LayerManager


class MapRenderer:
    """Renderiza o mapa da fase"""

    def __init__(self):
        self.layer_manager = LayerManager()
        self.loaded = False

    def load_from_data(self, map_data: dict, base_path: str = ""):
        """Carrega o mapa a partir dos dados"""
        if not map_data:
            print("Sem dados de mapa para carregar")
            return False

        try:
            self.layer_manager.from_dict(map_data, base_path)
            self.loaded = True
            print(f"Mapa carregado: {self.layer_manager.width}x{self.layer_manager.height} tiles")
            return True
        except Exception as e:
            print(f"Erro ao carregar mapa: {e}")
            return False

    def render(self, screen, camera, screen_manager):
        """Renderiza o mapa"""
        if self.loaded:
            self.layer_manager.render_all(screen, camera, screen_manager)

    def get_dimensions(self):
        """Retorna dimensões do mapa em pixels"""
        if not self.loaded:
            return (0, 0)
        return (
            self.layer_manager.width * self.layer_manager.tile_size,
            self.layer_manager.height * self.layer_manager.tile_size
        )