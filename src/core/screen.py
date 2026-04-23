"""
Gerenciador de tela - Renderização em resolução nativa sem stretching
"""
import pygame
from src.config.settings import settings

class ScreenManager:
    def __init__(self):
        self.settings = settings
        self.screen = None
        self.clock = pygame.time.Clock()
        self.delta_time = 0

        # Tamanho da janela (pode ser alterado)
        self.window_width = settings.screen_width
        self.window_height = settings.screen_height

        # Resolução de renderização (fixa - baseada no design do jogo)
        self.render_width = 1280
        self.render_height = 720

        # Viewport calculations
        self.viewport_x = 0
        self.viewport_y = 0
        self.viewport_width = self.window_width
        self.viewport_height = self.window_height
        self.render_scale = 1.0

        self.initialize_screen()

    def initialize_screen(self):
        """Inicializa a tela com as configurações atuais"""
        flags = pygame.RESIZABLE
        if self.settings.fullscreen:
            flags |= pygame.FULLSCREEN

        self.screen = pygame.display.set_mode(
            (self.window_width, self.window_height),
            flags,
            vsync=self.settings.vsync
        )

        self._calculate_viewport()
        pygame.display.set_caption("Pokemon Tower Defense")

    def _calculate_viewport(self):
        """Calcula o viewport para manter a proporção sem stretching"""
        window_ratio = self.window_width / self.window_height
        render_ratio = self.render_width / self.render_height

        if window_ratio > render_ratio:
            # Janela mais larga - viewport usa altura total
            self.viewport_height = self.window_height
            self.viewport_width = int(self.window_height * render_ratio)
            self.render_scale = self.window_height / self.render_height
        else:
            # Janela mais alta - viewport usa largura total
            self.viewport_width = self.window_width
            self.viewport_height = int(self.window_width / render_ratio)
            self.render_scale = self.window_width / self.render_width

        # Centraliza o viewport
        self.viewport_x = (self.window_width - self.viewport_width) // 2
        self.viewport_y = (self.window_height - self.viewport_height) // 2

    def world_to_screen(self, world_x, world_y, camera=None):
        """Delega para o render_context"""
        from src.core.render_context import render_context
        return render_context.world_to_screen(world_x, world_y, camera, self)

    def world_to_screen_with_scale(self, world_x, world_y, camera=None):
        """
        Versão que retorna TAMBÉM a escala para aplicar no sprite
        Útil para objetos que DEVEM ser afetados pelo zoom (como o mapa)
        """
        if camera:
            screen_x = (world_x - camera.x) * camera.zoom + self.render_width / 2
            screen_y = (world_y - camera.y) * camera.zoom + self.render_height / 2
            scale = camera.zoom * self.render_scale
        else:
            screen_x = world_x
            screen_y = world_y
            scale = self.render_scale

        final_x = screen_x * self.render_scale + self.viewport_x
        final_y = screen_y * self.render_scale + self.viewport_y

        return (final_x, final_y), scale


    def get_render_position(self, world_x, world_y, camera=None):
        """
        Retorna posição para renderização SEM escala
        Útil para sprites que devem manter tamanho original
        """
        if camera:
            screen_x = (world_x - camera.x) * camera.zoom + self.render_width / 2
            screen_y = (world_y - camera.y) * camera.zoom + self.render_height / 2
        else:
            screen_x = world_x
            screen_y = world_y

        return (int(screen_x), int(screen_y))

    def get_screen_position(self, render_x, render_y):
        """Converte posição de renderização para posição na tela"""
        screen_x = render_x * self.render_scale + self.viewport_x
        screen_y = render_y * self.render_scale + self.viewport_y
        return (int(screen_x), int(screen_y))

    def get_mouse_world_position(self, mouse_pos, camera=None):
        """Converte posição do mouse para coordenadas do mundo"""
        mouse_x, mouse_y = mouse_pos

        # Ajusta para viewport
        render_x = (mouse_x - self.viewport_x) / self.render_scale
        render_y = (mouse_y - self.viewport_y) / self.render_scale

        # Verifica se está dentro da área de renderização
        if render_x < 0 or render_x > self.render_width or render_y < 0 or render_y > self.render_height:
            return None

        if camera:
            # Converte para coordenadas do mundo
            world_x = (render_x - self.render_width / 2) / camera.zoom + camera.x
            world_y = (render_y - self.render_height / 2) / camera.zoom + camera.y
            return (world_x, world_y)

        return (render_x, render_y)

    def is_mouse_in_viewport(self, mouse_pos):
        """Verifica se o mouse está dentro da área de jogo"""
        x, y = mouse_pos
        return (self.viewport_x <= x <= self.viewport_x + self.viewport_width and
                self.viewport_y <= y <= self.viewport_y + self.viewport_height)

    def clear(self, color=None):
        """Limpa a tela"""
        if color is None:
            color = self.settings.colors['black']
        self.screen.fill(color)

    def flip(self):
        """Atualiza a tela"""
        pygame.display.flip()
        self.delta_time = self.clock.tick(self.settings.max_fps) / 1000.0

    def get_delta_time(self):
        return self.delta_time

    def get_fps(self):
        return self.clock.get_fps()

    def handle_resize(self, new_width, new_height):
        """Lida com redimensionamento da janela"""
        self.window_width = new_width
        self.window_height = new_height
        self.screen = pygame.display.set_mode(
            (new_width, new_height),
            pygame.RESIZABLE,
            vsync=self.settings.vsync
        )
        self._calculate_viewport()

        # Propaga resize para a cena atual (se existir)
        from src.core.game import Game
        if hasattr(self, '_game') and self._game and self._game.current_scene:
            if hasattr(self._game.current_scene, 'on_resize'):
                self._game.current_scene.on_resize()

    def toggle_fullscreen(self):
        """Alterna entre tela cheia e janela"""
        self.settings.fullscreen = not self.settings.fullscreen
        self.initialize_screen()