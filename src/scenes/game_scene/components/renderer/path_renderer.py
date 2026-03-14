"""
Renderizador de path - Desenha o caminho dos inimigos
"""
import pygame
from src.editor.path_editor import Path


class PathRenderer:
    """Renderiza o path da fase"""

    def __init__(self):
        self.path = Path()
        self.loaded = False

    def load_from_data(self, path_data: dict):
        """Carrega o path a partir dos dados"""
        if not path_data:
            print("Sem dados de path para carregar")
            return False

        try:
            self.path.from_dict(path_data)
            self.loaded = len(self.path.nodes) > 0
            print(f"Path carregado: {len(self.path.nodes)} pontos")
            return True
        except Exception as e:
            print(f"Erro ao carregar path: {e}")
            return False

    def render(self, screen, camera, screen_manager, show_editing=False):
        """Renderiza o path"""
        if self.loaded:
            # No jogo, renderizamos de forma mais sutil
            if show_editing:
                # Modo editor (cores mais visíveis)
                self.path.render(screen, camera, screen_manager)
            else:
                # Modo jogo (mais discreto)
                self._render_game_path(screen, camera, screen_manager)

    def _render_game_path(self, screen, camera, screen_manager):
        """Versão de jogo do path (mais discreta)"""
        if len(self.path.nodes) < 2:
            return

        points_screen = []
        for node in self.path.nodes:
            screen_x, screen_y = self._world_to_screen(node[0], node[1], camera, screen_manager)
            points_screen.append((screen_x, screen_y))

        # Linha mais sutil para o jogo
        for i in range(len(points_screen) - 1):
            pygame.draw.line(screen, (100, 100, 150, 100),
                             points_screen[i], points_screen[i + 1], 2)

    def _world_to_screen(self, world_x, world_y, camera, screen_manager):
        """Converte coordenadas do mundo para tela"""
        screen_x = round((world_x - camera.x) * camera.zoom * screen_manager.render_scale +
                         (screen_manager.render_width / 2) * screen_manager.render_scale +
                         screen_manager.viewport_x)
        screen_y = round((world_y - camera.y) * camera.zoom * screen_manager.render_scale +
                         (screen_manager.render_height / 2) * screen_manager.render_scale +
                         screen_manager.viewport_y)
        return (screen_x, screen_y)

    def get_path_points(self):
        """Retorna os pontos do path"""
        return self.path.get_path_points()