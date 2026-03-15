# src/editor/path_editor.py

import pygame
import math


class Path:
    def __init__(self):
        self.nodes = []  # Lista de pontos (x, y)
        self.selected_node = -1
        self.closed = False

        # Cores e estilos (agora todas com 3 valores RGB)
        self.line_color = (255, 100, 100)  # Vermelho para linha
        self.start_color = (0, 255, 0)  # Verde para início
        self.end_color = (255, 0, 0)  # Vermelho para fim
        self.normal_color = (100, 100, 255)  # Azul para nós normais
        self.selected_color = (255, 255, 0)  # Amarelo para selecionado
        self.start_point_color = (0, 255, 255)  # Ciano para primeiro ponto

        self.node_radius = 6
        self.start_node_radius = 8  # Maior para o primeiro ponto
        self.line_width = 3

    def add_node(self, point):
        """Adiciona um nó ao path"""
        self.nodes.append(point)
        self.selected_node = len(self.nodes) - 1

    def remove_node(self, index):
        """Remove um nó do path"""
        if 0 <= index < len(self.nodes):
            del self.nodes[index]
            if self.selected_node >= len(self.nodes):
                self.selected_node = len(self.nodes) - 1

    def get_path_points(self):
        """Retorna a lista de pontos do path"""
        return self.nodes.copy()

    def to_dict(self):
        """Converte para dicionário para salvar"""
        return {
            "nodes": self.nodes,
            "closed": self.closed
        }

    def from_dict(self, data):
        """Carrega do dicionário"""
        self.nodes = data.get("nodes", [])
        self.closed = data.get("closed", False)

    def render(self, screen, camera, screen_manager):
        """Renderiza o path com destaque especial para o primeiro ponto"""
        if not self.nodes:
            return

        # Primeiro, desenha as linhas entre os pontos
        self._render_lines(screen, camera, screen_manager)

        # Depois, desenha os pontos (nós)
        self._render_nodes(screen, camera, screen_manager)

    def _render_lines(self, screen, camera, screen_manager):
        """Renderiza as linhas entre os pontos"""
        if len(self.nodes) < 2:
            return

        points_screen = []
        for node in self.nodes:
            screen_x, screen_y = self._world_to_screen(node[0], node[1], camera, screen_manager)
            points_screen.append((screen_x, screen_y))

        # Desenha linhas entre pontos consecutivos
        for i in range(len(points_screen) - 1):
            start = points_screen[i]
            end = points_screen[i + 1]

            # CORRIGIDO: Usa uma superfície com alpha e aplica a cor corretamente
            line_surface = pygame.Surface((screen.get_width(), screen.get_height()), pygame.SRCALPHA)

            # Cria a cor com alpha - método correto para Pygame
            color_with_alpha = (*self.line_color, 180)  # Isso cria (R, G, B, A)

            pygame.draw.line(line_surface, color_with_alpha, start, end, self.line_width)
            screen.blit(line_surface, (0, 0))

        # Se o path for fechado, desenha linha do último ao primeiro
        if self.closed and len(self.nodes) > 2:
            start = points_screen[-1]
            end = points_screen[0]
            line_surface = pygame.Surface((screen.get_width(), screen.get_height()), pygame.SRCALPHA)
            color_with_alpha = (*self.line_color, 180)
            pygame.draw.line(line_surface, color_with_alpha, start, end, self.line_width)
            screen.blit(line_surface, (0, 0))

    def _render_nodes(self, screen, camera, screen_manager):
        """Renderiza os nós (pontos) com destaque especial para o primeiro"""
        for i, node in enumerate(self.nodes):
            screen_x, screen_y = self._world_to_screen(node[0], node[1], camera, screen_manager)

            # Verifica se o ponto está dentro do viewport (otimização)
            if not (0 <= screen_x <= screen.get_width() and 0 <= screen_y <= screen.get_height()):
                continue

            # Determina a cor e tamanho baseado na posição
            if i == 0:  # PRIMEIRO PONTO
                color = self.start_point_color
                radius = self.start_node_radius
                border_color = (255, 255, 255)  # Borda branca para mais destaque
                border_width = 2

                # Desenha um halo ao redor do primeiro ponto
                halo_surface = pygame.Surface((radius * 4, radius * 4), pygame.SRCALPHA)
                # CORRIGIDO: Cria cor com alpha corretamente
                halo_color = (*self.start_point_color, 100)
                pygame.draw.circle(halo_surface, halo_color,
                                   (radius * 2, radius * 2), radius + 4)
                screen.blit(halo_surface, (screen_x - radius * 2, screen_y - radius * 2))

            elif i == len(self.nodes) - 1:  # Último ponto
                color = self.end_color
                radius = self.node_radius
                border_color = None
            else:  # Pontos intermediários
                color = self.normal_color
                radius = self.node_radius
                border_color = None

            # Ponto selecionado tem destaque especial
            if i == self.selected_node:
                color = self.selected_color
                radius = radius + 2
                border_color = (255, 255, 255)

            # Desenha o ponto principal
            pygame.draw.circle(screen, color, (int(screen_x), int(screen_y)), radius)

            # Desenha borda se necessário
            if border_color:
                pygame.draw.circle(screen, border_color, (int(screen_x), int(screen_y)), radius, border_width)

            # Desenha número do ponto (opcional - útil para debug)
            if i == 0 or i == len(self.nodes) - 1 or i == self.selected_node:
                font = pygame.font.Font(None, 14)
                text = font.render(str(i + 1), True, (255, 255, 255))
                text_rect = text.get_rect(center=(screen_x, screen_y - radius - 10))
                screen.blit(text, text_rect)

    def _world_to_screen(self, world_x, world_y, camera, screen_manager):
        """Converte coordenadas do mundo para tela"""
        render_x = (world_x - camera.x) * camera.zoom + screen_manager.render_width / 2
        render_y = (world_y - camera.y) * camera.zoom + screen_manager.render_height / 2

        screen_x = render_x * screen_manager.render_scale + screen_manager.viewport_x
        screen_y = render_y * screen_manager.render_scale + screen_manager.viewport_y

        return (screen_x, screen_y)