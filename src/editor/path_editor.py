"""
Editor de caminho dos inimigos - Versão Simplificada
"""
import pygame
import math


class Path:
    def __init__(self):
        self.nodes = []  # Lista simples de tuplas (x, y)
        self.selected_node = -1
        self.is_loop = False
        print("Path inicializado com lista simples")

    def add_node(self, x, y):
        """Adiciona um nó ao caminho"""
        print(f"add_node: adicionando ({x}, {y})")
        self.nodes.append((x, y))
        print(f"  Agora com {len(self.nodes)} nós: {self.nodes}")

    def remove_node(self, index):
        """Remove um nó do caminho"""
        if 0 <= index < len(self.nodes):
            print(f"Removendo nó {index}")
            del self.nodes[index]
            if self.selected_node >= len(self.nodes):
                self.selected_node = len(self.nodes) - 1

    def get_path_points(self):
        """Retorna a lista de pontos"""
        print(f"get_path_points: retornando {len(self.nodes)} nós: {self.nodes}")
        return self.nodes.copy()

    def render(self, screen, camera, screen_manager):
        """Renderiza o caminho"""
        if len(self.nodes) < 2:
            return

        # Calcula offset da câmera
        cam_offset_x = -camera.x * camera.zoom + screen_manager.render_width / 2
        cam_offset_y = -camera.y * camera.zoom + screen_manager.render_height / 2

        # Desenha linhas do caminho
        if len(self.nodes) > 1:
            screen_points = []
            for x, y in self.nodes:
                render_x = x * camera.zoom + cam_offset_x
                render_y = y * camera.zoom + cam_offset_y
                screen_x, screen_y = screen_manager.get_screen_position(render_x, render_y)
                screen_points.append((screen_x, screen_y))

            line_width = max(1, int(3 * screen_manager.render_scale))
            pygame.draw.lines(screen, (255, 255, 0), self.is_loop, screen_points, line_width)

        # Desenha nós
        for i, (x, y) in enumerate(self.nodes):
            render_x = x * camera.zoom + cam_offset_x
            render_y = y * camera.zoom + cam_offset_y
            screen_x, screen_y = screen_manager.get_screen_position(render_x, render_y)

            radius = int(8 * camera.zoom * screen_manager.render_scale)

            # Destaca nó selecionado
            if i == self.selected_node:
                highlight_radius = radius + int(3 * screen_manager.render_scale)
                pygame.draw.circle(screen, (255, 255, 255), (screen_x, screen_y), highlight_radius, 2)

            # Desenha o círculo
            pygame.draw.circle(screen, (255, 255, 0), (screen_x, screen_y), radius)
            pygame.draw.circle(screen, (255, 255, 255), (screen_x, screen_y), radius, 1)

            # Mostra índice
            font = pygame.font.Font(None, 16)
            text = font.render(str(i), True, (255, 255, 255))
            screen.blit(text, (screen_x - text.get_width()//2, screen_y - radius - 20))

    def get_node_at(self, x, y, threshold=20):
        """Retorna índice do nó na posição"""
        for i, (nx, ny) in enumerate(self.nodes):
            distance = math.sqrt((nx - x) ** 2 + (ny - y) ** 2)
            if distance < threshold:
                return i
        return -1

    def to_dict(self):
        """Converte para dicionário"""
        return {
            "nodes": self.nodes,
            "is_loop": self.is_loop
        }

    def from_dict(self, data):
        """Carrega do dicionário"""
        self.nodes = data.get("nodes", [])
        self.is_loop = data.get("is_loop", False)
        print(f"Path carregado: {len(self.nodes)} nós")