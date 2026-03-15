# src/editor/path_manager.py

import pygame
import math
from src.editor.path_editor import Path


class PathManager:
    def __init__(self):
        self.paths = []  # Lista de objetos Path
        self.current_path_index = 0
        self.max_paths = 5  # Limite razoável de paths por fase


        # Cores para diferentes paths (para facilitar identificação)
        self.path_colors = [
            (255, 100, 100),  # Vermelho
            (100, 255, 100),  # Verde
            (100, 100, 255),  # Azul
            (255, 255, 100),  # Amarelo
            (255, 100, 255),  # Rosa
        ]

    def add_path(self):
        """Adiciona um novo path"""
        if len(self.paths) < self.max_paths:
            new_path = Path()
            # Define a cor baseada no índice
            new_path.line_color = self.path_colors[len(self.paths) % len(self.path_colors)]
            self.paths.append(new_path)
            self.current_path_index = len(self.paths) - 1
            print(f"Path {len(self.paths)} adicionado")
            return True
        else:
            print(f"Máximo de {self.max_paths} paths atingido!")
            return False

    def remove_current_path(self):
        """Remove o path atual"""
        if self.paths and 0 <= self.current_path_index < len(self.paths):
            removed = self.paths.pop(self.current_path_index)
            if self.current_path_index >= len(self.paths):
                self.current_path_index = max(0, len(self.paths) - 1)
            print(f"Path removido")
            return True
        return False

    def get_current_path(self):
        """Retorna o path atual"""
        if 0 <= self.current_path_index < len(self.paths):
            return self.paths[self.current_path_index]
        return None

    def get_all_paths(self):
        """Retorna todos os paths"""
        return self.paths

    def get_path_points_for_wave(self, wave_index):
        """Retorna os pontos do path para uma wave específica"""
        # Por enquanto, cada wave usa um path diferente (cíclico)
        if not self.paths:
            return []

        path_index = wave_index % len(self.paths)
        return self.paths[path_index].get_path_points()

    def render(self, screen, camera, screen_manager):
        """Renderiza todos os paths"""
        for i, path in enumerate(self.paths):
            # Salva a cor original do path
            original_color = path.line_color

            # Se não for o path atual, renderiza com transparência
            if i != self.current_path_index:
                # CORRIGIDO: Para o path não selecionado, usamos a linha com transparência
                # mas mantemos a cor original para os pontos
                path.line_color = original_color  # Mantém a cor original para os pontos
                # A linha será renderizada com transparência dentro do próprio path.render
            # else: mantém a cor original

            path.render(screen, camera, screen_manager)

            # Renderiza número do path (para identificação)
            if path.nodes:
                # Pega o primeiro ponto do path para colocar o número
                first_node = path.nodes[0]
                screen_x, screen_y = self._world_to_screen(first_node[0], first_node[1],
                                                           camera, screen_manager)

                # Fundo para o número
                font = pygame.font.Font(None, 16)

                # Define cor do texto baseado no path selecionado
                if i == self.current_path_index:
                    text_color = (255, 255, 0)  # Amarelo para path atual
                else:
                    text_color = (200, 200, 200)  # Cinza para outros paths

                text = font.render(f"P{i + 1}", True, text_color)
                text_bg = pygame.Surface((text.get_width() + 4, text.get_height() + 4))
                text_bg.fill((40, 40, 50))
                text_bg.set_alpha(200)
                screen.blit(text_bg, (screen_x - text_bg.get_width() // 2,
                                      screen_y - 30 - text_bg.get_height() // 2))
                screen.blit(text, (screen_x - text.get_width() // 2,
                                   screen_y - 30 - text.get_height() // 2))

    def _world_to_screen(self, world_x, world_y, camera, screen_manager):
        """Converte coordenadas do mundo para tela"""
        render_x = (world_x - camera.x) * camera.zoom + screen_manager.render_width / 2
        render_y = (world_y - camera.y) * camera.zoom + screen_manager.render_height / 2

        screen_x = render_x * screen_manager.render_scale + screen_manager.viewport_x
        screen_y = render_y * screen_manager.render_scale + screen_manager.viewport_y

        return (screen_x, screen_y)

    def set_wave_manager(self, wave_manager):
        """Associa um gerenciador de waves a este path manager"""
        self.wave_manager = wave_manager

    def get_waves_for_current_path(self):
        """Retorna todas as waves associadas ao path atual"""
        if hasattr(self, 'wave_manager') and self.wave_manager:
            return self.wave_manager.get_waves_for_path(self.current_path_index)
        return []

    def to_dict(self):
        """Converte para dicionário para salvar"""
        return {
            "paths": [path.to_dict() for path in self.paths],
            "current_path_index": self.current_path_index
        }

    def from_dict(self, data):
        """Carrega do dicionário"""
        self.paths = []
        for i, path_data in enumerate(data.get("paths", [])):
            path = Path()
            path.from_dict(path_data)
            # Atribui cor baseada no índice
            path.line_color = self.path_colors[i % len(self.path_colors)]
            self.paths.append(path)

        self.current_path_index = data.get("current_path_index", 0)
        if self.current_path_index >= len(self.paths):
            self.current_path_index = max(0, len(self.paths) - 1)