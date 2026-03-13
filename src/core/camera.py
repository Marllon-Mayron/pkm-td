"""
Sistema de câmera otimizado para renderização nativa
"""
import pygame

class Camera:
    def __init__(self, world_width, world_height, screen_manager):
        self.world_width = world_width
        self.world_height = world_height
        self.screen_manager = screen_manager

        # Posição da câmera (centro do mundo) - AGORA PODE SER NEGATIVO
        self.x = 0  # Começa em 0,0 ao invés do centro
        self.y = 0

        # Zoom
        self.zoom = 1.0
        self.min_zoom = 0.5
        self.max_zoom = 2.0
        self.zoom_speed = 0.1

        # Velocidade de movimento
        self.pan_speed = 500

        # Área morta para movimento (percentual)
        self.dead_zone = 0.1

        # Suavização
        self.smooth_factor = 5.0

        # Limites expandidos (agora permitem valores negativos)
        self.min_x = -1000  # Limite mínimo negativo
        self.max_x = world_width + 1000  # Limite máximo positivo
        self.min_y = -1000
        self.max_y = world_height + 1000

    def update(self, dt, mouse_render_pos):
        """Atualiza câmera baseado na posição do mouse em coordenadas de renderização"""
        if not mouse_render_pos:
            return

        mouse_x, mouse_y = mouse_render_pos

        # Calcula direção baseado na posição do mouse
        move_x = 0
        move_y = 0

        # Zona morta horizontal
        dead_zone_x = self.screen_manager.render_width * self.dead_zone

        if mouse_x < dead_zone_x:
            move_x = -1 * (1 - mouse_x / dead_zone_x)
        elif mouse_x > self.screen_manager.render_width - dead_zone_x:
            move_x = 1 * ((mouse_x - (self.screen_manager.render_width - dead_zone_x)) / dead_zone_x)

        # Zona morta vertical
        dead_zone_y = self.screen_manager.render_height * self.dead_zone

        if mouse_y < dead_zone_y:
            move_y = -1 * (1 - mouse_y / dead_zone_y)
        elif mouse_y > self.screen_manager.render_height - dead_zone_y:
            move_y = 1 * ((mouse_y - (self.screen_manager.render_height - dead_zone_y)) / dead_zone_y)

        # Aplica movimento suavizado
        if move_x != 0 or move_y != 0:
            target_x = self.x + move_x * self.pan_speed * dt / self.zoom
            target_y = self.y + move_y * self.pan_speed * dt / self.zoom

            self.x += (target_x - self.x) * min(1, dt * self.smooth_factor)
            self.y += (target_y - self.y) * min(1, dt * self.smooth_factor)

        self._clamp_position()

    def handle_zoom(self, zoom_in):
        """Aplica zoom"""
        if zoom_in:
            self.zoom = min(self.max_zoom, self.zoom + self.zoom_speed)
        else:
            self.zoom = max(self.min_zoom, self.zoom - self.zoom_speed)
        self._clamp_position()

    def get_visible_rect(self):
        """Retorna o retângulo visível do mundo (agora pode ser negativo)"""
        half_width = self.screen_manager.render_width / (2 * self.zoom)
        half_height = self.screen_manager.render_height / (2 * self.zoom)

        return pygame.Rect(
            self.x - half_width,
            self.y - half_height,
            half_width * 2,
            half_height * 2
        )

    def _clamp_position(self):
        """Mantém câmera dentro dos limites expandidos"""
        half_width = self.screen_manager.render_width / (2 * self.zoom)
        half_height = self.screen_manager.render_height / (2 * self.zoom)

        # Limites considerando a borda da tela
        min_x = self.min_x + half_width
        max_x = self.max_x - half_width
        min_y = self.min_y + half_height
        max_y = self.max_y - half_height

        # Garante que min < max
        if min_x > max_x:
            min_x = max_x = (min_x + max_x) / 2
        if min_y > max_y:
            min_y = max_y = (min_y + max_y) / 2

        self.x = max(min_x, min(self.x, max_x))
        self.y = max(min_y, min(self.y, max_y))

    def set_limits(self, min_x, max_x, min_y, max_y):
        """Define novos limites para a câmera"""
        self.min_x = min_x
        self.max_x = max_x
        self.min_y = min_y
        self.max_y = max_y
        self._clamp_position()