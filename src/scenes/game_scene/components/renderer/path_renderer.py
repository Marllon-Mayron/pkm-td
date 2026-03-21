# src/scenes/game_scene/components/renderer/path_renderer.py

"""
Renderizador de paths - Desenha os caminhos dos inimigos
"""
import pygame
from src.editor.path_editor import Path


class PathRenderer:
    """Renderiza os paths da fase"""

    def __init__(self):
        self.paths = []  # Lista de objetos Path
        self.loaded = False

    def load_from_data(self, paths_data: dict):
        """
        Carrega os paths a partir dos dados

        paths_data: {
            "paths": [path1_dict, path2_dict, ...],
            "current_path_index": 0
        }
        """
        if not paths_data:
            print("Sem dados de paths para carregar")
            return False

        try:
            self.paths = []
            for path_dict in paths_data.get("paths", []):
                path = Path()
                path.from_dict(path_dict)
                self.paths.append(path)

            self.loaded = len(self.paths) > 0
            print(f"Paths carregados: {len(self.paths)}")
            return True

        except Exception as e:
            print(f"Erro ao carregar paths: {e}")
            return False

    def render(self, screen, camera, screen_manager, show_editing=False):
        """Renderiza os paths"""
        if not self.loaded:
            return

        for path in self.paths:
            if show_editing:
                # Modo editor (cores mais visíveis)
                path.render(screen, camera, screen_manager)
            else:
                # Modo jogo (mais discreto)
                self._render_game_path(path, screen, camera, screen_manager)

    def _render_game_path(self, path, screen, camera, screen_manager):
        if len(path.nodes) < 2:
            return

        points_screen = []
        for node in path.nodes:
            screen_x, screen_y = screen_manager.world_to_screen(node[0], node[1], camera)
            points_screen.append((screen_x, screen_y))

        # Desenha diretamente na tela
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

    def get_path_points(self, path_index):
        """Retorna os pontos do path no índice especificado"""
        if 0 <= path_index < len(self.paths):
            return self.paths[path_index].get_path_points()
        return []