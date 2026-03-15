# src/scenes/game_scene/components/renderer/pokemon_spot_renderer.py

"""
Renderizador de spots de torre
"""
import pygame
from src.editor.tower_spot_editor import TowerSpotManager


class PokemonSpotRenderer:
    """Renderiza os spots de torre"""

    def __init__(self):
        self.spot_manager = TowerSpotManager()
        self.loaded = False

    def load_from_data(self, spot_data: dict):
        """Carrega os spots a partir dos dados"""
        if not spot_data:
            print("Sem dados de spots para carregar")
            return False

        try:
            self.spot_manager.from_dict(spot_data)
            self.loaded = len(self.spot_manager.spots) > 0
            print(f"Spots carregados: {len(self.spot_manager.spots)}")
            return True
        except Exception as e:
            print(f"Erro ao carregar spots: {e}")
            return False

    def render(self, screen, camera, screen_manager, show_editing=False):
        """Renderiza os spots"""
        if self.loaded and show_editing:
            self.spot_manager.render(screen, camera, screen_manager)

    def get_spots(self):
        """Retorna a lista de spots como objetos com atributos"""
        return self.spot_manager.spots  # Já retorna objetos TowerSpot

    def get_spots_as_dicts(self):
        """Retorna spots como dicionários (para compatibilidade)"""
        return [{'x': spot.x, 'y': spot.y, 'id': i}
                for i, spot in enumerate(self.spot_manager.spots)]