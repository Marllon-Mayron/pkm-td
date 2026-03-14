"""
Editor de spots para torres/pokemons
"""
import pygame


class TowerSpot:
    def __init__(self, x, y, size=16):
        self.x = x
        self.y = y
        self.size = size
        self.occupied = False
        self.allowed_types = []  # Tipos de pokemon permitidos

    def get_rect(self):
        return pygame.Rect(self.x, self.y, self.size, self.size)

    def contains_point(self, px, py):
        return (self.x <= px <= self.x + self.size and
                self.y <= py <= self.y + self.size)

    def __eq__(self, other):
        """Compara dois spots pela posição"""
        if isinstance(other, TowerSpot):
            return self.x == other.x and self.y == other.y and self.size == other.size
        return False


class TowerSpotManager:
    def __init__(self):
        self.spots = []
        self.selected_spot = -1
        self.spot_size = 16
        self.snap_to_grid = True
        self.grid_size = 16

    def add_spot(self, x, y):
        """Adiciona um spot se não existir outro na mesma posição"""
        # Ajusta para grid se necessário
        if self.snap_to_grid:
            x = (x // self.grid_size) * self.grid_size
            y = (y // self.grid_size) * self.grid_size

        # Verifica se já existe um spot nesta posição
        for spot in self.spots:
            if spot.x == x and spot.y == y:
                print(f"Spot já existe em ({x}, {y})")
                return -1

        spot = TowerSpot(x, y, self.spot_size)
        self.spots.append(spot)
        print(f"Spot adicionado em ({x}, {y})")
        return len(self.spots) - 1

    def remove_spot(self, spot_to_remove):
        """Remove um spot específico (objeto TowerSpot)"""
        if spot_to_remove in self.spots:
            self.spots.remove(spot_to_remove)
            if self.selected_spot >= len(self.spots):
                self.selected_spot = len(self.spots) - 1
            print("Spot removido")
        else:
            print("Spot não encontrado para remoção")

    def remove_spot_by_index(self, index):
        """Remove um spot pelo índice"""
        if 0 <= index < len(self.spots):
            del self.spots[index]
            if self.selected_spot >= len(self.spots):
                self.selected_spot = len(self.spots) - 1
            print(f"Spot {index} removido")

    def get_spot_at(self, x, y):
        """Retorna o spot na posição (ou None se não existir)"""
        for spot in self.spots:
            if spot.contains_point(x, y):
                return spot
        return None

    def get_spot_index_at(self, x, y):
        """Retorna índice do spot na posição"""
        for i, spot in enumerate(self.spots):
            if spot.contains_point(x, y):
                return i
        return -1

    def render(self, screen, camera, screen_manager):
        """Renderiza os spots"""
        for i, spot in enumerate(self.spots):
            # Calcula render position
            render_x = (spot.x - camera.x) * camera.zoom + screen_manager.render_width / 2
            render_y = (spot.y - camera.y) * camera.zoom + screen_manager.render_height / 2

            # Converte para tela
            screen_x, screen_y = screen_manager.get_screen_position(render_x, render_y)

            # Tamanho na tela (considerando zoom E escala)
            size = int(spot.size * camera.zoom * screen_manager.render_scale)

            # Cor baseada no estado
            if i == self.selected_spot:
                color = (255, 255, 0, 180)
                border_color = (255, 255, 255)
            elif spot.occupied:
                color = (255, 0, 0, 100)
                border_color = (255, 0, 0)
            else:
                color = (0, 255, 0, 50)
                border_color = (0, 255, 0)

            # Desenha spot semi-transparente
            spot_surface = pygame.Surface((size, size), pygame.SRCALPHA)
            spot_surface.fill(color)
            pygame.draw.rect(spot_surface, border_color, spot_surface.get_rect(),
                             max(1, int(2 * screen_manager.render_scale)))
            screen.blit(spot_surface, (screen_x, screen_y))

    def to_dict(self):
        """Converte para dicionário"""
        return {
            "spot_size": self.spot_size,
            "grid_size": self.grid_size,
            "snap_to_grid": self.snap_to_grid,
            "spots": [
                {
                    "x": spot.x,
                    "y": spot.y,
                    "size": spot.size,
                    "allowed_types": spot.allowed_types
                }
                for spot in self.spots
            ]
        }

    def from_dict(self, data):
        """Carrega do dicionário"""
        self.spot_size = data["spot_size"]
        self.grid_size = data["grid_size"]
        self.snap_to_grid = data["snap_to_grid"]
        self.spots = []
        for spot_data in data["spots"]:
            spot = TowerSpot(spot_data["x"], spot_data["y"], spot_data["size"])
            spot.allowed_types = spot_data["allowed_types"]
            self.spots.append(spot)