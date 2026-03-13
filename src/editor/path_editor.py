"""
Editor de caminho dos inimigos
"""
import pygame
import math


class PathNode:
    def __init__(self, x, y, node_type="waypoint"):
        self.x = x
        self.y = y
        self.node_type = node_type  # "waypoint", "start", "end"
        self.next_nodes = []  # Índices dos próximos nós
        self.prev_nodes = []  # Índices dos nós anteriores

    def get_position(self):
        return (self.x, self.y)


class Path:
    def __init__(self):
        self.nodes = []
        self.selected_node = -1
        self.is_loop = False

    def add_node(self, x, y, node_type="waypoint"):
        node = PathNode(x, y, node_type)
        self.nodes.append(node)
        return len(self.nodes) - 1

    def remove_node(self, index):
        if 0 <= index < len(self.nodes):
            # Remove conexões
            for node in self.nodes:
                if index in node.next_nodes:
                    node.next_nodes.remove(index)
                if index in node.prev_nodes:
                    node.prev_nodes.remove(index)
            del self.nodes[index]
            if self.selected_node >= len(self.nodes):
                self.selected_node = len(self.nodes) - 1

    def connect_nodes(self, from_idx, to_idx):
        if 0 <= from_idx < len(self.nodes) and 0 <= to_idx < len(self.nodes):
            if to_idx not in self.nodes[from_idx].next_nodes:
                self.nodes[from_idx].next_nodes.append(to_idx)
            if from_idx not in self.nodes[to_idx].prev_nodes:
                self.nodes[to_idx].prev_nodes.append(from_idx)

    def disconnect_nodes(self, from_idx, to_idx):
        if 0 <= from_idx < len(self.nodes):
            if to_idx in self.nodes[from_idx].next_nodes:
                self.nodes[from_idx].next_nodes.remove(to_idx)
        if 0 <= to_idx < len(self.nodes):
            if from_idx in self.nodes[to_idx].prev_nodes:
                self.nodes[to_idx].prev_nodes.remove(from_idx)

    def get_path_points(self):
        """Retorna lista de pontos para desenho do caminho"""
        points = []
        visited = set()

        def traverse(node_idx):
            if node_idx in visited:
                return
            visited.add(node_idx)
            node = self.nodes[node_idx]
            points.append((node.x, node.y))

            for next_idx in node.next_nodes:
                traverse(next_idx)

        # Começa pelos nós de start
        for i, node in enumerate(self.nodes):
            if node.node_type == "start":
                traverse(i)
                if self.is_loop and points:
                    points.append(points[0])
                break

        return points

    def render(self, screen, camera, screen_manager):
        """Renderiza o caminho"""
        if len(self.nodes) < 2:
            return

        # Calcula offset da câmera uma única vez para otimização
        cam_offset_x = -camera.x * camera.zoom + screen_manager.render_width / 2
        cam_offset_y = -camera.y * camera.zoom + screen_manager.render_height / 2

        # Desenha linhas do caminho
        points = self.get_path_points()
        if len(points) > 1:
            screen_points = []
            for x, y in points:
                # Calcula render position usando offset
                render_x = x * camera.zoom + cam_offset_x
                render_y = y * camera.zoom + cam_offset_y

                # Converte para tela
                screen_x, screen_y = screen_manager.get_screen_position(render_x, render_y)
                screen_points.append((screen_x, screen_y))

            if len(screen_points) > 1:
                # Ajusta espessura da linha baseada na escala
                line_width = max(1, int(3 * screen_manager.render_scale))
                pygame.draw.lines(screen, (255, 255, 0), self.is_loop, screen_points, line_width)

        # Desenha nós
        for i, node in enumerate(self.nodes):
            # Calcula render position
            render_x = node.x * camera.zoom + cam_offset_x
            render_y = node.y * camera.zoom + cam_offset_y

            # Converte para tela
            screen_x, screen_y = screen_manager.get_screen_position(render_x, render_y)

            # Ajusta tamanho baseado na escala da tela E no zoom
            base_radius = 8 if node.node_type != "waypoint" else 5
            # Multiplica pelo zoom para manter proporção com o mundo
            radius = int(base_radius * camera.zoom * screen_manager.render_scale)

            # Cor baseada no tipo
            if node.node_type == "start":
                color = (0, 255, 0)  # Verde para start
            elif node.node_type == "end":
                color = (255, 0, 0)  # Vermelho para end
            else:
                color = (255, 255, 0)  # Amarelo para waypoint

            # Destaca nó selecionado
            if i == self.selected_node:
                # Círculo externo de destaque
                highlight_radius = radius + int(3 * screen_manager.render_scale)
                highlight_width = max(1, int(2 * screen_manager.render_scale))
                pygame.draw.circle(screen, (255, 255, 255), (screen_x, screen_y),
                                  highlight_radius, highlight_width)

            # Desenha o círculo principal
            pygame.draw.circle(screen, color, (screen_x, screen_y), radius)

            # Desenha a borda branca
            border_width = max(1, int(1 * screen_manager.render_scale))
            pygame.draw.circle(screen, (255, 255, 255), (screen_x, screen_y),
                              radius, border_width)

            # Mostra índice com fonte escalada
            # Fonte base 16, ajustada pela escala da tela
            font_size = max(12, int(16 * screen_manager.render_scale))
            font = pygame.font.Font(None, font_size)
            text = font.render(str(i), True, (255, 255, 255))

            # Posiciona o texto acima do nó
            text_x = screen_x - text.get_width() // 2
            text_y = screen_y - radius - text.get_height() - int(2 * screen_manager.render_scale)

            # Fundo semi-transparente para o texto
            text_bg = pygame.Surface((text.get_width() + 4, text.get_height() + 4))
            text_bg.set_alpha(128)
            text_bg.fill((0, 0, 0))
            screen.blit(text_bg, (text_x - 2, text_y - 2))

            screen.blit(text, (text_x, text_y))

    def get_node_at(self, x, y, threshold=20):
        """Retorna índice do nó na posição (em coordenadas de mundo)"""
        for i, node in enumerate(self.nodes):
            distance = math.sqrt((node.x - x) ** 2 + (node.y - y) ** 2)
            if distance < threshold:
                return i
        return -1

    def to_dict(self):
        """Converte para dicionário"""
        return {
            "is_loop": self.is_loop,
            "nodes": [
                {
                    "x": node.x,
                    "y": node.y,
                    "type": node.node_type,
                    "next": node.next_nodes,
                    "prev": node.prev_nodes
                }
                for node in self.nodes
            ]
        }

    def from_dict(self, data):
        """Carrega do dicionário"""
        self.is_loop = data["is_loop"]
        self.nodes = []
        for node_data in data["nodes"]:
            node = PathNode(node_data["x"], node_data["y"], node_data["type"])
            node.next_nodes = node_data["next"]
            node.prev_nodes = node_data["prev"]
            self.nodes.append(node)