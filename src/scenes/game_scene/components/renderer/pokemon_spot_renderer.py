# src/scenes/game_scene/components/renderer/pokemon_spot_renderer.py

"""
Renderizador de spots de torre - SEM GRID
"""
import pygame
from src.editor.tower_spot_editor import TowerSpotManager
from src.core.render_context import render_context


class PokemonSpotRenderer:
    """Renderiza os spots de torre - APENAS O SPOT, SEM GRID"""

    def __init__(self):
        self.spot_manager = TowerSpotManager()
        self.loaded = False
        self.tile_size = 16
        self._cached_spots = {}  # Cache de superfícies

    def load_from_data(self, spot_data: dict):
        """Carrega os spots a partir dos dados"""
        if not spot_data:
            return False

        try:
            self.spot_manager.from_dict(spot_data)
            self.loaded = len(self.spot_manager.spots) > 0
            self._cached_spots.clear()
            print(f"Spots carregados: {len(self.spot_manager.spots)}")
            return True
        except Exception as e:
            print(f"Erro ao carregar spots: {e}")
            return False

    def update(self, dt):
        pass

    def _get_spot_surface(self, spot, is_occupied, is_highlight, size):
        """Obtém superfície do spot com cache"""
        cache_key = (spot.x, spot.y, is_occupied, is_highlight, size)

        if cache_key not in self._cached_spots:
            if is_occupied:
                color = (255, 80, 80)
                alpha = 200
                border_color = (255, 50, 50)
                inner_color = (255, 100, 100)
            elif is_highlight:
                color = (100, 255, 100)
                alpha = 220
                border_color = (255, 255, 255)
                inner_color = (150, 255, 150)
            else:
                color = (100, 200, 100)
                alpha = 150
                border_color = (150, 200, 150)
                inner_color = (120, 220, 120)

            surf = pygame.Surface((size, size), pygame.SRCALPHA)
            half = size // 2

            # Efeito de brilho (se highlight)
            if is_highlight:
                glow_size = size + 8
                glow = pygame.Surface((glow_size, glow_size), pygame.SRCALPHA)
                pygame.draw.circle(glow, (255, 255, 255, 80), (glow_size // 2, glow_size // 2), glow_size // 2)
                self._cached_spots[f"glow_{cache_key}"] = glow

            # Círculo principal
            pygame.draw.circle(surf, (*color, alpha), (half, half), half - 1)
            pygame.draw.circle(surf, border_color, (half, half), half - 1, 2)

            # Círculo interno (efeito de profundidade)
            inner_radius = max(2, half - 4)
            pygame.draw.circle(surf, (*inner_color, alpha + 30), (half, half), inner_radius)

            self._cached_spots[cache_key] = surf

        return self._cached_spots[cache_key]

    def render(self, screen, camera, screen_manager, show_editing=False, highlight_spot=None):
        """Renderiza os spots - APENAS O SPOT, SEM GRID"""
        if not self.loaded:
            return

        scale = render_context.get_scale(camera, screen_manager)
        spot_size = max(12, int(24 * scale))  # Tamanho fixo, não depende do tile
        half_spot = spot_size // 2

        for spot in self.spot_manager.spots:
            # Pega o centro do tile onde o spot está
            tile_center_x = (spot.x // self.tile_size) * self.tile_size + self.tile_size // 2
            tile_center_y = (spot.y // self.tile_size) * self.tile_size + self.tile_size // 2

            screen_x, screen_y = render_context.world_to_screen(
                tile_center_x, tile_center_y, camera, screen_manager
            )

            is_occupied = spot.occupied
            is_highlight = highlight_spot == spot

            # Obtém superfície do spot
            spot_surface = self._get_spot_surface(spot, is_occupied, is_highlight, spot_size)

            # Desenha o spot
            screen.blit(spot_surface, (screen_x - half_spot, screen_y - half_spot))

            # Efeito de brilho para highlight
            if is_highlight:
                glow_key = f"glow_{(spot.x, spot.y, is_occupied, is_highlight, spot_size)}"
                if glow_key in self._cached_spots:
                    glow = self._cached_spots[glow_key]
                    screen.blit(glow, (screen_x - glow.get_width() // 2, screen_y - glow.get_height() // 2))

            # Debug (opcional, apenas se show_editing)
            if show_editing:
                font = render_context.get_font(12)
                coord_text = font.render(f"{spot.x},{spot.y}", True, (255, 255, 255))
                screen.blit(coord_text, (screen_x - 20, screen_y - half_spot - 15))

    def get_spots(self):
        return self.spot_manager.spots

    def get_spot_at_world_pos(self, world_x, world_y):
        tile_x = int(world_x // self.tile_size)
        tile_y = int(world_y // self.tile_size)

        for spot in self.spot_manager.spots:
            spot_tile_x = spot.x // self.tile_size
            spot_tile_y = spot.y // self.tile_size
            if spot_tile_x == tile_x and spot_tile_y == tile_y:
                return spot
        return None