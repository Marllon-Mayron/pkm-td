# src/scenes/game_scene/components/renderer/path_renderer.py

"""
Renderizador de paths - SIMPLIFICADO
"""
import pygame
from src.editor.path_editor import Path
from src.core.render_context import render_context


class PathRenderer:
    """Renderiza os paths da fase"""

    def __init__(self):
        self.paths = []
        self.loaded = False

    def load_from_data(self, paths_data: dict):
        """Carrega os paths a partir dos dados"""
        if not paths_data:
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
            points = path.get_path_points()
            if len(points) < 2:
                continue

            # Converte pontos para tela
            screen_points = []
            for x, y in points:
                screen_x, screen_y = render_context.world_to_screen(x, y, camera, screen_manager)
                screen_points.append((screen_x, screen_y))

            if show_editing:
                # Modo editor - cores mais visíveis
                for i in range(len(screen_points) - 1):
                    pygame.draw.line(screen, (255, 100, 100),
                                     screen_points[i], screen_points[i + 1], 3)
                    pygame.draw.circle(screen, (255, 255, 0), screen_points[i], 4)
            else:
                # Modo jogo - mais discreto
                for i in range(len(screen_points) - 1):
                    pygame.draw.line(screen, (100, 100, 150, 100),
                                     screen_points[i], screen_points[i + 1], 2)

    def get_path_points(self, path_index):
        if 0 <= path_index < len(self.paths):
            return self.paths[path_index].get_path_points()
        return []