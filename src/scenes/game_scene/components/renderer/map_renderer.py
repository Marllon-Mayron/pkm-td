# src/scenes/game_scene/components/renderer/map_renderer.py

"""
Renderizador de mapa - com suporte a render split (ground/decoration/ceiling).
"""
from src.scenes.game_scene.components.managers.game_layer_manager import GameLayerManager


class MapRenderer:
    def __init__(self):
        self.layer_manager = GameLayerManager()
        self.loaded = False
        self.tile_size = 16

    def load_from_data(self, map_data: dict, base_path: str = ""):
        if not map_data:
            return False
        try:
            self.tile_size = map_data.get("tile_size", 16)
            self.layer_manager.tile_size = self.tile_size
            self.layer_manager.load_from_dict(map_data, base_path)
            self.loaded = True
            print(f"[MapRenderer] Mapa carregado com tile_size={self.tile_size}, "
                  f"{len(self.layer_manager.layers)} camadas")
            return True
        except Exception as e:
            print(f"Erro ao carregar mapa: {e}")
            import traceback
            traceback.print_exc()
            return False

    # ===== RENDER SPLIT =====
    def render_ground(self, screen, camera, screen_manager):
        if not self.loaded:
            return
        self.layer_manager.render_ground_layers(screen, camera, screen_manager)

    def render_decoration(self, screen, camera, screen_manager):
        if not self.loaded:
            return
        self.layer_manager.render_decoration_layers(screen, camera, screen_manager)

    def render_ceiling(self, screen, camera, screen_manager):
        if not self.loaded:
            return
        self.layer_manager.render_ceiling_layers(screen, camera, screen_manager)

    # ===== RENDER COMPLETO (compat) =====
    def render(self, screen, camera, screen_manager):
        if not self.loaded:
            return
        self.layer_manager.render_all(screen, camera, screen_manager)

    def get_dimensions(self):
        if not self.loaded:
            return (0, 0)
        return self.layer_manager.get_dimensions()

    def invalidate_cache(self):
        self.layer_manager.invalidate_cache()