import pygame


class TestEnemy:
    def __init__(self, path_nodes):
        self.path_nodes = path_nodes
        self.current_node = 0
        self.progress = 0.0
        self.speed = 0.1
        self.position = path_nodes[0] if path_nodes else (0, 0)
        self.active = len(path_nodes) > 1  # Precisa de pelo menos 2 nós para ser ativo
        self.finished = False  # Indica se o inimigo completou o caminho

    def update(self, dt):
        """Atualiza a posição do inimigo"""
        if not self.active or len(self.path_nodes) < 2 or self.finished:
            return

        self.progress += self.speed * dt * 60

        if self.progress >= 1.0:
            self.progress = 1.0
            self.current_node += 1

            # Verifica se chegou ao último nó
            if self.current_node >= len(self.path_nodes) - 1:
                self.finished = True
                print("Inimigo completou o caminho!")  # Debug
                return

            self.progress = 0.0

        start = self.path_nodes[self.current_node]
        end = self.path_nodes[self.current_node + 1]

        self.position = (
            start[0] + (end[0] - start[0]) * self.progress,
            start[1] + (end[1] - start[1]) * self.progress
        )

    def reset(self):
        """Reseta o inimigo para o início do caminho"""
        if self.path_nodes and len(self.path_nodes) > 1:
            self.current_node = 0
            self.progress = 0.0
            self.position = self.path_nodes[0]
            self.finished = False
            print("Inimigo resetado para o início!")  # Debug

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
        pygame.draw.circle(screen, (255, 255, 255),
                           (int(screen_x + size / 3), int(screen_y - size / 3)), eye_size)
        pygame.draw.circle(screen, (0, 0, 0),
                           (int(screen_x - size / 3), int(screen_y - size / 3)), max(1, eye_size // 2))
        pygame.draw.circle(screen, (0, 0, 0),
                           (int(screen_x + size / 3), int(screen_y - size / 3)), max(1, eye_size // 2))

        # Indicador de progresso (opcional)
        if self.finished:
            # Desenha um X se o inimigo terminou (útil para debug)
            pygame.draw.line(screen, (255, 255, 255),
                             (int(screen_x - size / 2), int(screen_y - size / 2)),
                             (int(screen_x + size / 2), int(screen_y + size / 2)), 2)
            pygame.draw.line(screen, (255, 255, 255),
                             (int(screen_x + size / 2), int(screen_y - size / 2)),
                             (int(screen_x - size / 2), int(screen_y + size / 2)), 2)