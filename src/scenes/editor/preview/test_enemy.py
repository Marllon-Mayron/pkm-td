import pygame


class TestEnemy:
    def __init__(self, path_nodes):
        self.path_nodes = path_nodes
        self.current_point = 0
        self.progress = 0.0
        self.speed = 0.02  # Mais lento para teste
        self.position = path_nodes[0] if path_nodes else (0, 0)
        self.active = len(path_nodes) > 1
        self.finished = False
        print(f"Inimigo criado com {len(path_nodes)} pontos: {path_nodes}")

    def update(self, dt):
        """Atualiza a posição do inimigo"""
        if not self.active or len(self.path_nodes) < 2 or self.finished:
            return

        self.progress += self.speed * dt * 60
        print(f"Progresso: {self.progress:.2f}")  # Debug

        if self.progress >= 1.0:
            self.current_point += 1
            print(f"Avançou para ponto {self.current_point}")

            if self.current_point >= len(self.path_nodes) - 1:
                self.finished = True
                print("Inimigo completou o caminho!")
                return

            self.progress = 0.0

        start = self.path_nodes[self.current_point]
        end = self.path_nodes[self.current_point + 1]

        self.position = (
            start[0] + (end[0] - start[0]) * self.progress,
            start[1] + (end[1] - start[1]) * self.progress
        )
        print(f"Posição: {self.position}")  # Debug

    def reset(self):
        """Reseta o inimigo"""
        if self.path_nodes and len(self.path_nodes) > 1:
            self.current_point = 0
            self.progress = 0.0
            self.position = self.path_nodes[0]
            self.finished = False
            print("Inimigo resetado!")

    def render(self, screen, camera, screen_manager):
        """Renderiza o inimigo"""
        if not self.active or self.finished:
            return

        render_x = (self.position[0] - camera.x) * camera.zoom + screen_manager.render_width / 2
        render_y = (self.position[1] - camera.y) * camera.zoom + screen_manager.render_height / 2
        screen_x, screen_y = screen_manager.get_screen_position(render_x, render_y)

        size = int(20 * camera.zoom)

        # Corpo do inimigo
        pygame.draw.circle(screen, (255, 0, 0), (int(screen_x), int(screen_y)), size)
        pygame.draw.circle(screen, (255, 255, 255), (int(screen_x), int(screen_y)), size, 2)

        # Olhos
        eye_size = max(2, int(4 * camera.zoom))
        pygame.draw.circle(screen, (255, 255, 255),
                           (int(screen_x - size / 3), int(screen_y - size / 3)), eye_size)
        pygame.draw.circle(screen, (0, 0, 0),
                           (int(screen_x - size / 3), int(screen_y - size / 3)), max(1, eye_size // 2))
        pygame.draw.circle(screen, (255, 255, 255),
                           (int(screen_x + size / 3), int(screen_y - size / 3)), eye_size)
        pygame.draw.circle(screen, (0, 0, 0),
                           (int(screen_x + size / 3), int(screen_y - size / 3)), max(1, eye_size // 2))