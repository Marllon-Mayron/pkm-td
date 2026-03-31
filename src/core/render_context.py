# src/core/render_context.py

"""
Sistema unificado de renderização - OTIMIZADO E SEM GAPS
"""
import pygame


class RenderContext:
    """Contexto de renderização unificado com cache"""

    _instance = None
    _cache = {}

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialized = False
        return cls._instance

    def __init__(self):
        if self._initialized:
            return
        self._initialized = True
        self._clear_cache()

    def _clear_cache(self):
        """Limpa todos os caches"""
        self._position_cache = {}
        self._sprite_cache = {}
        self._font_cache = {}
        self._last_camera_key = None

    def world_to_screen(self, world_x, world_y, camera, screen_manager):
        """
        Converte coordenadas do mundo para tela - COM PRECISÃO
        """
        if camera:
            zoom = camera.zoom
            cam_x = camera.x
            cam_y = camera.y
        else:
            zoom = 1.0
            cam_x = 0
            cam_y = 0

        # Cálculo com ponto flutuante
        rel_x = world_x - cam_x
        rel_y = world_y - cam_y

        zoomed_x = rel_x * zoom
        zoomed_y = rel_y * zoom

        render_x = zoomed_x + screen_manager.render_width / 2
        render_y = zoomed_y + screen_manager.render_height / 2

        screen_x = render_x * screen_manager.render_scale + screen_manager.viewport_x
        screen_y = render_y * screen_manager.render_scale + screen_manager.viewport_y

        return (screen_x, screen_y)

    def world_to_screen_int(self, world_x, world_y, camera, screen_manager):
        """Versão que retorna inteiros (para cache)"""
        x, y = self.world_to_screen(world_x, world_y, camera, screen_manager)
        return (int(x), int(y))

    def get_scale(self, camera, screen_manager):
        """Retorna a escala atual"""
        if camera:
            return camera.zoom * screen_manager.render_scale
        return screen_manager.render_scale

    def get_font(self, size, bold=False):
        """Obtém fonte com cache"""
        cache_key = (size, bold)
        if cache_key in self._font_cache:
            return self._font_cache[cache_key]

        font = pygame.font.Font(None, size)
        if bold:
            font.set_bold(True)

        self._font_cache[cache_key] = font
        return font

    def invalidate_cache(self):
        """Invalida todo o cache"""
        self._position_cache.clear()
        self._sprite_cache.clear()


# Instância global
render_context = RenderContext()