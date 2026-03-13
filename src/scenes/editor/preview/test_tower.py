import pygame


class TestTower:
    def __init__(self, x, y):
        self.x = x
        self.y = y
        self.rotation = 0

    def update(self, dt):
        """Atualiza a torre de teste"""
        self.rotation += dt * 50

    def render(self, screen, camera, screen_manager):
        """Renderiza a torre de teste"""
        render_x = (self.x - camera.x) * camera.zoom + screen_manager.render_width / 2
        render_y = (self.y - camera.y) * camera.zoom + screen_manager.render_height / 2
        screen_x, screen_y = screen_manager.get_screen_position(render_x, render_y)

        size = int(25 * camera.zoom)

        # Base da torre
        pygame.draw.rect(screen, (0, 100, 200),
                        (screen_x - size//2, screen_y - size//2, size, size))

        # Canhão
        cannon_length = size
        end_x = screen_x + cannon_length * 0.8 * pygame.math.Vector2(1, 0).rotate(self.rotation).x
        end_y = screen_y + cannon_length * 0.8 * pygame.math.Vector2(1, 0).rotate(self.rotation).y

        pygame.draw.line(screen, (200, 200, 100),
                        (screen_x, screen_y), (end_x, end_y), max(2, int(5 * camera.zoom)))

        # Centro
        pygame.draw.circle(screen, (255, 255, 0), (int(screen_x), int(screen_y)), max(3, int(8 * camera.zoom)))