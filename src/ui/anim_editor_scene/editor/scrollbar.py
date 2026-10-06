"""
Barra de scroll vertical reutilizável.

Melhorias desta versão:
- Scroll FLOAT interno → thumb move suave, sem snapping
- Drag pega EXATAMENTE onde o mouse tocar (offset preservado no thumb)
- Click no track → topo do thumb vai pro mouse, e já inicia drag
- Wheel com passo configurável (`wheel_step`, default 3)
- `wheel_area` — zona onde a roda do mouse ativa o scroll (por padrão = track)
"""
import pygame


class ScrollBar:
    def __init__(self, width=8, pad=2, wheel_step=3):
        self.track = pygame.Rect(0, 0, width, 0)
        self.wheel_area = pygame.Rect(0, 0, width, 0)
        self.width = width
        self.pad = pad
        self.wheel_step = wheel_step
        self._scroll = 0.0           # float interno
        self.max_scroll = 0
        self.total = 1
        self.visible = 1
        self._dragging = False
        self._drag_offset = 0

    # -----------------------------------------------------------------
    # API
    # -----------------------------------------------------------------
    @property
    def scroll(self) -> int:
        return int(round(self._scroll))

    @scroll.setter
    def scroll(self, value):
        self._scroll = float(value)
        self._clamp()

    @property
    def scroll_f(self) -> float:
        """Scroll fracionário (uso interno / debug)."""
        return self._scroll

    @property
    def is_dragging(self) -> bool:
        return self._dragging

    # -----------------------------------------------------------------
    def set(self, track, scroll=None, total=1, visible=1, wheel_area=None):
        self.track = pygame.Rect(track)
        self.total = max(1, int(total))
        self.visible = max(1, int(visible))
        self.max_scroll = max(0, self.total - self.visible)
        # scroll=None → preserva o `_scroll` atual (útil pra re-layout)
        if scroll is not None:
            self._scroll = float(scroll)
        self._clamp()
        self.wheel_area = (pygame.Rect(wheel_area)
                           if wheel_area else self.track.copy())

    def _clamp(self):
        if self.max_scroll <= 0:
            self._scroll = 0.0
        else:
            self._scroll = max(0.0, min(float(self.max_scroll), self._scroll))

    # -----------------------------------------------------------------
    # GEOMETRIA DO THUMB
    # -----------------------------------------------------------------
    def _thumb_h(self) -> int:
        if self.max_scroll <= 0 or self.track.height <= 0:
            return 0
        ratio = self.visible / self.total
        return max(24, min(self.track.height,
                           int(self.track.height * ratio)))

    def thumb_rect(self):
        thumb_h = self._thumb_h()
        if thumb_h <= 0:
            return None
        range_y = self.track.height - thumb_h
        if range_y <= 0:
            return pygame.Rect(self.track.x, self.track.y,
                               self.track.width, thumb_h)
        rel = self._scroll / self.max_scroll
        thumb_y = self.track.y + int(range_y * rel)
        return pygame.Rect(self.track.x, thumb_y,
                           self.track.width, thumb_h)

    # -----------------------------------------------------------------
    # EVENTOS
    # -----------------------------------------------------------------
    def handle_event(self, event) -> bool:
        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            if self.max_scroll <= 0:
                return False
            thumb = self.thumb_rect()
            # Clicou DENTRO do thumb → arrasta preservando offset
            if thumb and thumb.collidepoint(event.pos):
                self._dragging = True
                self._drag_offset = event.pos[1] - thumb.y
                return True
            # Clicou no track → topo do thumb vai pro mouse + inicia drag
            if self.track.collidepoint(event.pos):
                self._dragging = True
                self._drag_offset = 0
                self._apply_drag(event.pos[1])
                return True

        elif event.type == pygame.MOUSEMOTION:
            if self._dragging:
                self._apply_drag(event.pos[1])
                return True

        elif event.type == pygame.MOUSEBUTTONUP and event.button == 1:
            if self._dragging:
                self._dragging = False
                return True
        return False

    def handle_wheel(self, event_y: int, mouse_pos) -> bool:
        """Retorna True se consumiu. Usa `wheel_area` pra decidir hover."""
        if self.max_scroll <= 0:
            return False
        if not self.wheel_area.collidepoint(mouse_pos):
            return False
        self._scroll += -event_y * self.wheel_step
        self._clamp()
        return True

    def _apply_drag(self, mouse_y):
        thumb_h = self._thumb_h()
        if thumb_h <= 0:
            return
        range_y = self.track.height - thumb_h
        if range_y <= 0:
            self._scroll = 0.0
            return
        rel = max(0, min(range_y,
                         mouse_y - self._drag_offset - self.track.y))
        self._scroll = self.max_scroll * (rel / range_y)

    # -----------------------------------------------------------------
    # RENDER
    # -----------------------------------------------------------------
    def render(self, screen,
               base_color=(150, 170, 210),
               hover_color=(190, 200, 230),
               drag_color=(100, 200, 255)):
        if self.max_scroll <= 0:
            return
        pygame.draw.rect(screen, (32, 40, 56), self.track, border_radius=3)
        thumb = self.thumb_rect()
        if not thumb:
            return
        if self._dragging:
            col = drag_color
        elif self.track.inflate(8, 0).collidepoint(pygame.mouse.get_pos()):
            col = hover_color
        else:
            col = base_color
        pygame.draw.rect(screen, col, thumb, border_radius=3)