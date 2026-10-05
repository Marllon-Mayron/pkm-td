"""
Renderizador de spots de torre no jogo.
Usa o mesmo helper de desenho do editor para garantir consistência visual.
"""
import pygame
from src.editor.tower_spot_editor import (
    TowerSpotManager, draw_typed_rect, get_type_colors,
)
from src.core.render_context import render_context


class PokemonSpotRenderer:
    def __init__(self):
        self.spot_manager = TowerSpotManager()
        self.loaded = False
        self.tile_size = 16

    def load_from_data(self, spot_data: dict):
        if not spot_data:
            return False
        try:
            self.spot_manager.from_dict(spot_data)
            self.loaded = len(self.spot_manager.spots) > 0
            print(f"Spots carregados: {len(self.spot_manager.spots)}")
            return True
        except Exception as e:
            print(f"Erro ao carregar spots: {e}")
            return False

    def update(self, dt):
        pass

    def render(self, screen, camera, screen_manager,
               show_editing=False, highlight_spot=None):
        if not self.loaded:
            return

        scale = render_context.get_scale(camera, screen_manager)
        spot_size = max(10, int(16 * scale))
        half = spot_size // 2

        for spot in self.spot_manager.spots:
            tile_center_x = (spot.x // self.tile_size) * self.tile_size + self.tile_size // 2
            tile_center_y = (spot.y // self.tile_size) * self.tile_size + self.tile_size // 2

            screen_x, screen_y = render_context.world_to_screen(
                tile_center_x, tile_center_y, camera, screen_manager
            )

            colors = get_type_colors(spot.allowed_types)
            is_highlight = (highlight_spot == spot)

            if is_highlight:
                # Slot sob o mouse: mais opaco + borda grossa + outline branco
                draw_typed_rect(
                    screen,
                    screen_x - half, screen_y - half,
                    spot_size, spot_size,
                    colors,
                    fill_alpha=210,
                    border_width=max(4, int(5 * scale)),
                )
                # Outline branco por fora (destaque)
                pygame.draw.rect(
                    screen, (255, 255, 255),
                    (screen_x - half - 2, screen_y - half - 2,
                     spot_size + 4, spot_size + 4), 2,
                )

            elif spot.occupied:
                # Ocupado: fill sólido + borda grossa
                draw_typed_rect(
                    screen,
                    screen_x - half, screen_y - half,
                    spot_size, spot_size,
                    colors,
                    fill_alpha=200,
                    border_width=max(3, int(4 * scale)),
                )

            else:
                # Vazio: fill translúcido + borda grossa
                draw_typed_rect(
                    screen,
                    screen_x - half, screen_y - half,
                    spot_size, spot_size,
                    colors,
                    fill_alpha=95,
                    border_width=max(3, int(3 * scale)),
                )

            # Modo debug do editor (não usado no jogo normal)
            if show_editing:
                font = render_context.get_font(12)
                label = ",".join(spot.allowed_types) if spot.allowed_types else "any"
                text = font.render(label, True, (255, 255, 255))
                screen.blit(text, (screen_x - half, screen_y - half - 14))

    def get_spots(self):
        return self.spot_manager.spots

    def get_spot_at_world_pos(self, world_x, world_y):
        tile_x = int(world_x // self.tile_size)
        tile_y = int(world_y // self.tile_size)
        for spot in self.spot_manager.spots:
            sx = spot.x // self.tile_size
            sy = spot.y // self.tile_size
            if sx == tile_x and sy == tile_y:
                return spot
        return None