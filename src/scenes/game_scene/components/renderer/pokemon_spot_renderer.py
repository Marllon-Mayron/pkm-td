# src/scenes/game_scene/components/renderer/pokemon_spot_renderer.py

"""
Renderizador de spots de torre
"""
import pygame
import math
from src.editor.tower_spot_editor import TowerSpotManager


class PokemonSpotRenderer:
    """Renderiza os spots de torre"""

    def __init__(self):
        self.spot_manager = TowerSpotManager()
        self.loaded = False
        self.animation_time = 0
        self.tile_size = 16  # Tamanho do tile

    def load_from_data(self, spot_data: dict):
        """Carrega os spots a partir dos dados"""
        if not spot_data:
            print("Sem dados de spots para carregar")
            return False

        try:
            self.spot_manager.from_dict(spot_data)
            self.loaded = len(self.spot_manager.spots) > 0

            # DEBUG: Mostra as coordenadas dos spots carregados
            print(f"Spots carregados: {len(self.spot_manager.spots)}")
            for i, spot in enumerate(self.spot_manager.spots[:5]):  # Mostra só os primeiros
                print(f"  Spot {i}: ({spot.x}, {spot.y}) - Tile: ({spot.x // 16}, {spot.y // 16})")

            return True
        except Exception as e:
            print(f"Erro ao carregar spots: {e}")
            return False

    def update(self, dt):
        """Atualiza animações"""
        self.animation_time += dt

    def render(self, screen, camera, screen_manager, show_editing=False, highlight_spot=None):
        """Renderiza os spots sempre visíveis - com DEBUG visual"""
        if not self.loaded:
            return

        for spot in self.spot_manager.spots:
            # Converte coordenadas do mundo para tela

            # Tamanho base
            base_size = max(4, int(self.tile_size * camera.zoom * screen_manager.render_scale))

            screen_x, screen_y = screen_manager.world_to_screen(spot.x, spot.y, camera)
            tile_x = (spot.x // self.tile_size) * self.tile_size
            tile_y = (spot.y // self.tile_size) * self.tile_size
            tile_screen_x, tile_screen_y = screen_manager.world_to_screen(tile_x, tile_y, camera)

            # Desenha o tile inteiro (semi-transparente) para referência
            tile_rect = pygame.Rect(
                tile_screen_x,
                tile_screen_y,
                base_size,
                base_size
            )
            pygame.draw.rect(screen, (50, 50, 255, 30), tile_rect, 1)

            # Determina cor baseada no estado
            if spot.occupied:
                color = (255, 100, 100)
                alpha = 180
                border_color = (255, 50, 50)
            elif highlight_spot == spot:
                color = (100, 255, 100)
                alpha = 220
                border_color = (255, 255, 255)
            else:
                color = (100, 255, 100)
                alpha = 100
                border_color = (150, 255, 150)

            # Desenha o spot NO CENTRO DO TILE
            spot_size = base_size // 2  # Metade do tile para o spot

            # Cria superfície para o spot
            spot_surface = pygame.Surface((spot_size, spot_size), pygame.SRCALPHA)

            # Preenchimento
            fill_color = (*color, alpha)
            spot_surface.fill(fill_color)

            # Borda
            pygame.draw.rect(spot_surface, border_color, spot_surface.get_rect(), 2)

            # Desenha na tela (centralizado no tile)
            screen.blit(spot_surface,
                        (tile_screen_x + (base_size - spot_size) // 2,
                         tile_screen_y + (base_size - spot_size) // 2))

            # DEBUG: Mostra coordenadas
            if show_editing:
                font = pygame.font.Font(None, 14)
                coord_text = font.render(f"{spot.x},{spot.y}", True, (255, 255, 255))
                screen.blit(coord_text, (tile_screen_x, tile_screen_y - 15))

                tile_text = font.render(f"T{spot.x // 16},{spot.y // 16}", True, (200, 200, 0))
                screen.blit(tile_text, (tile_screen_x, tile_screen_y - 30))

    def get_spots(self):
        """Retorna a lista de spots como objetos com atributos"""
        return self.spot_manager.spots

    def get_spot_at_world_pos(self, world_x, world_y):
        """Retorna o spot na posição do mundo - AGORA BASEADO EM TILES"""
        # Converte para coordenadas de tile
        tile_x = world_x // self.tile_size
        tile_y = world_y // self.tile_size

        for spot in self.spot_manager.spots:
            spot_tile_x = spot.x // self.tile_size
            spot_tile_y = spot.y // self.tile_size

            if spot_tile_x == tile_x and spot_tile_y == tile_y:
                return spot
        return None