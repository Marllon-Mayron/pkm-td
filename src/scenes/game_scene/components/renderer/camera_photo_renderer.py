# src/scenes/game_scene/components/camera_photo_renderer.py
"""
UI da câmera fotográfica - acoplada à bolsa (sempre em cima dela).

Recursos:
- Preview da área de captura (moldura)
- Botão de tirar foto (grande, vermelho, estilo obturador)
- Alavanca analógica (estilo PlayStation) para mover a área
- Slider horizontal de zoom na parte de baixo
- Animação Polaroid após captura
- Som sincronizado com volume global (SFX)
- Começa MINIMIZADA por padrão
- Janela pode ser arrastada pelo título
"""
import pygame
import math

_FONT_CACHE = {}


class PolaroidAnimation:
    """Animação de preview estilo Polaroid que desce, pausa e some."""

    # Estados
    STATE_DESCENDING = "descending"
    STATE_HOLDING = "holding"
    STATE_FADING = "fading"
    STATE_DONE = "done"

    def __init__(self, photo_surface: pygame.Surface, start_pos, target_pos):
        """
        Args:
            photo_surface: superfície com a foto capturada
            start_pos: (x, y) de onde começa (atrás da câmera)
            target_pos: (x, y) de destino (onde fica parada)
        """
        self.photo_surface = photo_surface
        self.start_pos = start_pos
        self.target_pos = target_pos

        # Estado
        self.state = self.STATE_DESCENDING
        self.timer = 0.0

        # Tempos (segundos)
        self.DESCEND_DURATION = 0.45
        self.HOLD_DURATION = 2.2
        self.FADE_DURATION = 0.9

        # Progresso
        self.progress = 0.0
        self.alpha = 255

        # Cria versão com moldura Polaroid (moldura branca + espaço embaixo)
        self.polaroid_surface = self._make_polaroid(photo_surface)

        # Efeito de "balanço" ao descer (rotação leve)
        self.rotation = 0.0
        self.ROTATION_MAX = 4.0   # graus

    def _make_polaroid(self, photo: pygame.Surface) -> pygame.Surface:
        """Cria uma superfície com moldura branca estilo Polaroid."""
        # Proporções Polaroid clássicas
        pad_side = 14
        pad_top = 14
        pad_bottom = 40   # espaço embaixo pro "nome"

        w = photo.get_width() + pad_side * 2
        h = photo.get_height() + pad_top + pad_bottom

        surf = pygame.Surface((w, h), pygame.SRCALPHA)

        # Fundo branco (com leve tom creme)
        pygame.draw.rect(surf, (250, 248, 240), (0, 0, w, h), border_radius=4)
        # Borda sutil
        pygame.draw.rect(surf, (210, 205, 195), (0, 0, w, h), 2, border_radius=4)

        # Foto colada
        surf.blit(photo, (pad_side, pad_top))

        # Sombra interna pra dar profundidade (opcional)
        shadow = pygame.Surface((photo.get_width(), 4), pygame.SRCALPHA)
        shadow.fill((0, 0, 0, 40))
        surf.blit(shadow, (pad_side, pad_top))

        return surf

    def update(self, dt):
        if self.state == self.STATE_DONE:
            return

        self.timer += dt

        if self.state == self.STATE_DESCENDING:
            self.progress = min(1.0, self.timer / self.DESCEND_DURATION)
            # Easing: ease-out cubic
            t = 1.0 - (1.0 - self.progress) ** 3

            # Posição interpolada
            self.current_pos = (
                self.start_pos[0] + (self.target_pos[0] - self.start_pos[0]) * t,
                self.start_pos[1] + (self.target_pos[1] - self.start_pos[1]) * t,
            )

            # Balanço sutil (vai e volta)
            self.rotation = math.sin(self.progress * math.pi * 2) * self.ROTATION_MAX * (1.0 - self.progress * 0.5)

            if self.progress >= 1.0:
                self.state = self.STATE_HOLDING
                self.timer = 0.0
                self.rotation = 0.0

        elif self.state == self.STATE_HOLDING:
            self.current_pos = self.target_pos
            if self.timer >= self.HOLD_DURATION:
                self.state = self.STATE_FADING
                self.timer = 0.0

        elif self.state == self.STATE_FADING:
            fade_t = min(1.0, self.timer / self.FADE_DURATION)
            self.alpha = int(255 * (1.0 - fade_t))

            # Desliza levemente pra baixo enquanto some
            offset_y = 30 * fade_t
            self.current_pos = (
                self.target_pos[0],
                self.target_pos[1] + offset_y,
            )

            if fade_t >= 1.0:
                self.state = self.STATE_DONE
                self.alpha = 0

    def render(self, screen):
        if self.state == self.STATE_DONE:
            return

        # Rotaciona se necessário
        if abs(self.rotation) > 0.1:
            rotated = pygame.transform.rotozoom(
                self.polaroid_surface, self.rotation, 1.0
            )
            # Aplica alpha
            rotated.set_alpha(self.alpha)
            rect = rotated.get_rect(center=(
                int(self.current_pos[0] + self.polaroid_surface.get_width() / 2),
                int(self.current_pos[1] + self.polaroid_surface.get_height() / 2),
            ))
            screen.blit(rotated, rect)
        else:
            surf = self.polaroid_surface.copy()
            surf.set_alpha(self.alpha)
            screen.blit(surf, (int(self.current_pos[0]), int(self.current_pos[1])))

    @property
    def is_done(self):
        return self.state == self.STATE_DONE


class CameraPhotoRenderer:
    """UI da câmera, acoplada à bolsa."""

    # Dimensões
    WIDTH = 250
    HEIGHT = 190
    MARGIN_ABOVE_BAG = 8

    # Alavanca analógica
    STICK_BASE_RADIUS = 26
    STICK_KNOB_RADIUS = 12
    STICK_MAX_OFFSET = 18

    # Sensibilidade
    STICK_MOVE_SPEED = 0.25

    # Slider
    SLIDER_WIDTH = 190
    SLIDER_HEIGHT = 8
    SLIDER_KNOB_RADIUS = 9
    SLIDER_MIN = 0.20
    SLIDER_MAX = 1.00
    SLIDER_DEFAULT = 0.50

    def __init__(self, game, bag_renderer, photo_manager):
        self.game = game
        self.bag_renderer = bag_renderer
        self.photo_manager = photo_manager

        # Posição
        self.x = 0
        self.y = 0
        self._user_positioned = False

        # Arrasto da janela
        self.window_dragging = False
        self.window_drag_offset = (0, 0)

        # Estado
        self.visible = True
        self.minimized = True
        self.mouse_over_ui = False

        # Flash
        self.flash_alpha = 0
        self.flash_active = False

        # Animação
        self.animation_time = 0.0
        self.hovered_button = None

        # Alavanca
        self.stick_center = (0, 0)
        self.stick_knob_offset = [0.0, 0.0]
        self.stick_dragging = False
        self.stick_drag_offset = (0, 0)
        self.stick_active = False

        # Slider
        self.slider_rect = None
        self.slider_knob_x = 0.5
        self.slider_dragging = False

        # Botões
        self.btn_capture_rect = None

        # ===== ANIMAÇÃO POLAROID =====
        self.polaroid_animation: PolaroidAnimation | None = None

        self._set_slider_from_area()
        self._sync_with_bag()

    # ------------------------------------------------------------------
    # FONTES
    # ------------------------------------------------------------------
    def _get_font(self, size, bold=False):
        key = (size, bold)
        if key not in _FONT_CACHE:
            font = pygame.font.Font(None, size)
            if bold:
                font.set_bold(True)
            _FONT_CACHE[key] = font
        return _FONT_CACHE[key]

    # ------------------------------------------------------------------
    # SLIDER ↔ ÁREA
    # ------------------------------------------------------------------
    def _set_slider_from_area(self):
        a = self.photo_manager.capture_area
        size = (a["width"] + a["height"]) / 2.0

        if self.SLIDER_MAX == self.SLIDER_MIN:
            self.slider_knob_x = 0.5
            return

        ratio = (size - self.SLIDER_MIN) / (self.SLIDER_MAX - self.SLIDER_MIN)
        self.slider_knob_x = max(0.0, min(1.0, ratio))

    def _apply_slider_to_area(self):
        size = self.SLIDER_MIN + (self.SLIDER_MAX - self.SLIDER_MIN) * self.slider_knob_x

        a = self.photo_manager.capture_area
        center_x = a["x"] + a["width"] / 2
        center_y = a["y"] + a["height"] / 2

        new_w = size
        new_h = size

        new_x = max(0.0, min(1.0 - new_w, center_x - new_w / 2))
        new_y = max(0.0, min(1.0 - new_h, center_y - new_h / 2))

        self.photo_manager.set_capture_area(new_x, new_y, new_w, new_h)

    # ------------------------------------------------------------------
    # SINCRONIZAÇÃO COM A BOLSA
    # ------------------------------------------------------------------
    def _sync_with_bag(self):
        if not self.bag_renderer:
            return

        if not self._user_positioned:
            self.x = self.bag_renderer.x
            self.y = self.bag_renderer.y - self.HEIGHT - self.MARGIN_ABOVE_BAG

            if self.y < 5:
                self.y = self.bag_renderer.y + self.bag_renderer.height + self.MARGIN_ABOVE_BAG

        sw = self.game.screen_manager.window_width
        sh = self.game.screen_manager.window_height
        self.x = max(5, min(sw - self.WIDTH - 5, self.x))
        self.y = max(5, min(sh - 24 - 5, self.y))

    # ------------------------------------------------------------------
    # UPDATE
    # ------------------------------------------------------------------
    def update(self, dt):
        self.animation_time += dt
        self._sync_with_bag()

        if self.flash_active:
            self.flash_alpha -= dt * 800
            if self.flash_alpha <= 0:
                self.flash_alpha = 0
                self.flash_active = False

        self._update_button_rects()

        if not self.minimized and self.stick_active:
            self._apply_stick_movement(dt)

        if not self.minimized and not self.slider_dragging:
            self._set_slider_from_area()

        # ===== ATUALIZA ANIMAÇÃO POLAROID =====
        if self.polaroid_animation is not None:
            self.polaroid_animation.update(dt)
            if self.polaroid_animation.is_done:
                self.polaroid_animation = None

    def _update_button_rects(self):
        if self.minimized:
            self.btn_capture_rect = None
            self.slider_rect = None
            self.stick_center = (0, 0)
            return

        # ===== LAYOUT INFERIOR =====
        slider_zone_height = 34
        content_bottom = self.y + self.HEIGHT - slider_zone_height

        # Alavanca
        stick_zone_center_y = content_bottom - (self.STICK_BASE_RADIUS + 22)
        self.stick_center = (
            self.x + 42,
            stick_zone_center_y
        )

        # Botão de captura
        capture_size = 54
        self.btn_capture_rect = pygame.Rect(
            self.x + self.WIDTH - capture_size - 14,
            stick_zone_center_y - capture_size // 2,
            capture_size, capture_size
        )

        # Slider
        slider_w = self.SLIDER_WIDTH
        slider_h = self.SLIDER_HEIGHT
        slider_x = self.x + (self.WIDTH - slider_w) // 2
        slider_y = self.y + self.HEIGHT - 26
        self.slider_rect = pygame.Rect(slider_x, slider_y, slider_w, slider_h)

    # ------------------------------------------------------------------
    # ALAVANCA
    # ------------------------------------------------------------------
    def _apply_stick_movement(self, dt):
        nx = self.stick_knob_offset[0] / self.STICK_MAX_OFFSET
        ny = self.stick_knob_offset[1] / self.STICK_MAX_OFFSET

        dead_zone = 0.15
        if abs(nx) < dead_zone:
            nx = 0.0
        if abs(ny) < dead_zone:
            ny = 0.0

        if nx == 0.0 and ny == 0.0:
            return

        delta_x = nx * self.STICK_MOVE_SPEED * dt
        delta_y = ny * self.STICK_MOVE_SPEED * dt

        a = self.photo_manager.capture_area
        self.photo_manager.set_capture_area(
            a["x"] + delta_x, a["y"] + delta_y, a["width"], a["height"]
        )

    def _is_mouse_on_stick(self, pos) -> bool:
        knob_x = self.stick_center[0] + self.stick_knob_offset[0]
        knob_y = self.stick_center[1] + self.stick_knob_offset[1]

        dx = pos[0] - knob_x
        dy = pos[1] - knob_y
        if (dx * dx + dy * dy) ** 0.5 <= self.STICK_KNOB_RADIUS + 4:
            return True

        dx = pos[0] - self.stick_center[0]
        dy = pos[1] - self.stick_center[1]
        if (dx * dx + dy * dy) ** 0.5 <= self.STICK_BASE_RADIUS + 6:
            return True

        return False

    def _start_stick_drag(self, pos):
        self.stick_dragging = True
        knob_x = self.stick_center[0] + self.stick_knob_offset[0]
        knob_y = self.stick_center[1] + self.stick_knob_offset[1]
        self.stick_drag_offset = (pos[0] - knob_x, pos[1] - knob_y)

    def _update_stick_drag(self, pos):
        desired_x = pos[0] - self.stick_drag_offset[0]
        desired_y = pos[1] - self.stick_drag_offset[1]

        ox = desired_x - self.stick_center[0]
        oy = desired_y - self.stick_center[1]

        distance = (ox * ox + oy * oy) ** 0.5
        if distance > self.STICK_MAX_OFFSET:
            ratio = self.STICK_MAX_OFFSET / distance
            ox *= ratio
            oy *= ratio

        self.stick_knob_offset[0] = ox
        self.stick_knob_offset[1] = oy
        self.stick_active = (abs(ox) > 2 or abs(oy) > 2)

    def _end_stick_drag(self):
        self.stick_dragging = False
        self.stick_knob_offset[0] = 0.0
        self.stick_knob_offset[1] = 0.0
        self.stick_active = False

    # ------------------------------------------------------------------
    # SLIDER
    # ------------------------------------------------------------------
    def _is_mouse_on_slider(self, pos) -> bool:
        if not self.slider_rect:
            return False
        extended = self.slider_rect.inflate(self.SLIDER_KNOB_RADIUS * 2, 16)
        return extended.collidepoint(pos)

    def _start_slider_drag(self, pos):
        self.slider_dragging = True
        self._update_slider_knob_from_mouse(pos)

    def _update_slider_knob_from_mouse(self, pos):
        if not self.slider_rect:
            return
        rel_x = (pos[0] - self.slider_rect.x) / self.slider_rect.width
        self.slider_knob_x = max(0.0, min(1.0, rel_x))
        self._apply_slider_to_area()

    def _end_slider_drag(self):
        self.slider_dragging = False

    # ------------------------------------------------------------------
    # ARRASTO DA JANELA
    # ------------------------------------------------------------------
    def _start_window_drag(self, pos):
        self.window_dragging = True
        self.window_drag_offset = (pos[0] - self.x, pos[1] - self.y)
        self._user_positioned = True

    def _update_window_drag(self, pos):
        new_x = pos[0] - self.window_drag_offset[0]
        new_y = pos[1] - self.window_drag_offset[1]

        sw = self.game.screen_manager.window_width
        sh = self.game.screen_manager.window_height

        self.x = max(5, min(sw - self.WIDTH - 5, new_x))
        self.y = max(5, min(sh - 24 - 5, new_y))

    def _end_window_drag(self):
        self.window_dragging = False

    # ------------------------------------------------------------------
    # EVENTOS
    # ------------------------------------------------------------------
    def handle_event(self, event) -> bool:
        if not self.visible:
            return False

        if event.type == pygame.MOUSEMOTION:
            self.mouse_over_ui = self._is_mouse_in_area(event.pos)
            self._update_hover(event.pos)

            if self.window_dragging:
                self._update_window_drag(event.pos)
                return True
            if self.stick_dragging:
                self._update_stick_drag(event.pos)
                return True
            if self.slider_dragging:
                self._update_slider_knob_from_mouse(event.pos)
                return True

        elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            if self._handle_click(event.pos):
                return True

        elif event.type == pygame.MOUSEBUTTONUP and event.button == 1:
            consumed = False
            if self.window_dragging:
                self._end_window_drag()
                consumed = True
            if self.stick_dragging:
                self._end_stick_drag()
                consumed = True
            if self.slider_dragging:
                self._end_slider_drag()
                consumed = True
            if consumed:
                return True

        return False

    def _update_hover(self, pos):
        self.hovered_button = None

        title_rect = pygame.Rect(self.x, self.y, self.WIDTH, 24)
        if title_rect.collidepoint(pos):
            self.hovered_button = "title"
            return

        if self.minimized:
            return

        if self._is_mouse_on_stick(pos):
            self.hovered_button = "stick"
            return

        if self._is_mouse_on_slider(pos):
            self.hovered_button = "slider"
            return

        if self.btn_capture_rect and self.btn_capture_rect.collidepoint(pos):
            self.hovered_button = "capture"

    def _handle_click(self, pos) -> bool:
        # Título
        title_rect = pygame.Rect(self.x, self.y, self.WIDTH, 24)
        if title_rect.collidepoint(pos):
            min_btn_rect = pygame.Rect(
                self.x + self.WIDTH - 26, self.y + 2, 22, 20
            )
            if min_btn_rect.collidepoint(pos):
                self.minimized = not self.minimized
                if not self.minimized:
                    self._set_slider_from_area()
                return True

            self._start_window_drag(pos)
            return True

        if self.minimized:
            return False

        if self._is_mouse_on_stick(pos):
            self._start_stick_drag(pos)
            return True

        if self._is_mouse_on_slider(pos):
            self._start_slider_drag(pos)
            return True

        if self.btn_capture_rect and self.btn_capture_rect.collidepoint(pos):
            self._do_capture()
            return True

        if self._is_mouse_in_area(pos):
            return True

        return False

    # ------------------------------------------------------------------
    # CAPTURA
    # ------------------------------------------------------------------
    def _do_capture(self):
        """Tira a foto, toca o som, dispara flash e animação polaroid."""
        path = self.photo_manager.capture()
        if not path:
            return

        # ===== SOM (escala com volume global de SFX) =====
        try:
            from src.managers.sounds.sound_manager import sound_manager, SoundEffect
            sound_manager.play_effect(SoundEffect.CAMERA_CLICK)
        except Exception as e:
            print(f"[CAMERA] Erro ao tocar som de captura: {e}")

        # ===== FLASH =====
        self.flash_alpha = 200
        self.flash_active = True

        # ===== ANIMAÇÃO POLAROID =====
        self._start_polaroid_animation(path)

    def _start_polaroid_animation(self, photo_path: str):
        """Carrega a foto capturada e inicia a animação de preview."""
        try:
            photo_surface = pygame.image.load(photo_path).convert_alpha()
        except Exception as e:
            print(f"[CAMERA] Erro ao carregar foto para preview: {e}")
            return

        # ===== REDIMENSIONA A FOTO PARA UM TAMANHO DE PREVIEW RAZOÁVEL =====
        preview_w = 160
        # Mantém proporção
        aspect = photo_surface.get_height() / photo_surface.get_width()
        preview_h = int(preview_w * aspect)
        photo_surface = pygame.transform.smoothscale(photo_surface, (preview_w, preview_h))

        # ===== POSIÇÕES =====
        # Início: atrás da câmera (escondido atrás do painel)
        start_x = self.x + (self.WIDTH - preview_w) // 2
        start_y = self.y + 24 - preview_h    # logo abaixo do título, "saindo" da câmera

        # Destino: desce um pouco abaixo do painel, centralizado
        target_x = self.x + (self.WIDTH - preview_w) // 2
        target_y = self.y + self.HEIGHT + 10  # logo abaixo do painel

        # Ajusta se sair da tela
        sh = self.game.screen_manager.window_height
        if target_y + preview_h + 60 > sh:
            # Não caberia embaixo: sobe pra cima da câmera
            target_y = self.y - preview_h - 20

        self.polaroid_animation = PolaroidAnimation(
            photo_surface,
            start_pos=(start_x, start_y),
            target_pos=(target_x, target_y),
        )

    def _is_mouse_in_area(self, pos) -> bool:
        h = 24 if self.minimized else self.HEIGHT
        return (self.x <= pos[0] <= self.x + self.WIDTH and
                self.y <= pos[1] <= self.y + h)

    # ------------------------------------------------------------------
    # RENDER
    # ------------------------------------------------------------------
    def render(self, screen):
        if not self.visible:
            return

        if not self.minimized:
            self._render_capture_frame(screen)

        self._render_ui(screen)

        # ===== ANIMAÇÃO POLAROID (por cima de tudo da câmera) =====
        if self.polaroid_animation is not None:
            self.polaroid_animation.render(screen)

        if self.flash_active and self.flash_alpha > 0:
            self._render_flash(screen)

    def _render_capture_frame(self, screen):
        rect = self.photo_manager.get_capture_rect_screen()

        overlay = pygame.Surface(
            (self.game.screen_manager.viewport_width,
             self.game.screen_manager.viewport_height),
            pygame.SRCALPHA
        )
        overlay.fill((0, 0, 0, 60))

        try:
            overlay.fill((0, 0, 0, 0), (
                rect.x - self.game.screen_manager.viewport_x,
                rect.y - self.game.screen_manager.viewport_y,
                rect.width, rect.height
            ))
        except ValueError:
            pass

        screen.blit(overlay, (
            self.game.screen_manager.viewport_x,
            self.game.screen_manager.viewport_y
        ))

        self._render_corner_marks(screen, rect)

        cx = rect.centerx
        cy = rect.centery
        pygame.draw.line(screen, (255, 255, 255, 180), (cx - 8, cy), (cx + 8, cy), 1)
        pygame.draw.line(screen, (255, 255, 255, 180), (cx, cy - 8), (cx, cy + 8), 1)

    def _render_corner_marks(self, screen, rect):
        corner_len = 20
        color = (255, 255, 255)
        thickness = 2

        pygame.draw.line(screen, color, rect.topleft, (rect.left + corner_len, rect.top), thickness)
        pygame.draw.line(screen, color, rect.topleft, (rect.left, rect.top + corner_len), thickness)

        pygame.draw.line(screen, color, (rect.right, rect.top), (rect.right - corner_len, rect.top), thickness)
        pygame.draw.line(screen, color, (rect.right, rect.top), (rect.right, rect.top + corner_len), thickness)

        pygame.draw.line(screen, color, (rect.left, rect.bottom), (rect.left + corner_len, rect.bottom), thickness)
        pygame.draw.line(screen, color, (rect.left, rect.bottom), (rect.left, rect.bottom - corner_len), thickness)

        pygame.draw.line(screen, color, (rect.right, rect.bottom), (rect.right - corner_len, rect.bottom), thickness)
        pygame.draw.line(screen, color, (rect.right, rect.bottom), (rect.right, rect.bottom - corner_len), thickness)

    def _render_ui(self, screen):
        h = 24 if self.minimized else self.HEIGHT

        # Sombra
        shadow = pygame.Surface((self.WIDTH + 6, h + 6), pygame.SRCALPHA)
        shadow.fill((0, 0, 0, 90))
        screen.blit(shadow, (self.x + 3, self.y + 4))

        # Fundo
        bg = pygame.Surface((self.WIDTH, h), pygame.SRCALPHA)
        bg.fill((15, 20, 30, 235))
        screen.blit(bg, (self.x, self.y))

        # Borda
        if self.window_dragging:
            border_color = (255, 215, 0)
        elif self.mouse_over_ui:
            border_color = (120, 160, 240)
        else:
            border_color = (80, 120, 200)
        pygame.draw.rect(screen, border_color,
                         (self.x, self.y, self.WIDTH, h), 2, border_radius=8)

        # Título
        title_font = self._get_font(20, bold=True)
        title = title_font.render("CÂMERA", True, (255, 215, 0))
        screen.blit(title, (self.x + 10, self.y + 4))

        # Botão minimizar
        min_btn_rect = pygame.Rect(self.x + self.WIDTH - 26, self.y + 2, 22, 20)
        hover_min = min_btn_rect.collidepoint(pygame.mouse.get_pos())
        pygame.draw.rect(
            screen,
            (90, 110, 160) if hover_min else (50, 60, 85),
            min_btn_rect, border_radius=4
        )
        pygame.draw.rect(screen, (150, 180, 220), min_btn_rect, 1, border_radius=4)
        min_icon = "−" if not self.minimized else "+"
        min_font = self._get_font(16, bold=True)
        min_surf = min_font.render(min_icon, True, (255, 255, 255))
        screen.blit(min_surf, min_surf.get_rect(center=min_btn_rect.center))

        if self.minimized:
            return

        # Info da área
        a = self.photo_manager.capture_area
        info_font = self._get_font(14)
        info_text = f"Área: {int(a['width']*100)}% x {int(a['height']*100)}%"
        info = info_font.render(info_text, True, (180, 200, 240))
        screen.blit(info, (self.x + 10, self.y + 28))

        # Alavanca
        self._draw_analog_stick(screen)

        # Botão de captura
        self._draw_capture_button(screen)

        # Slider
        self._draw_zoom_slider(screen)

    def _draw_analog_stick(self, screen):
        cx, cy = self.stick_center
        base_r = self.STICK_BASE_RADIUS
        knob_r = self.STICK_KNOB_RADIUS

        knob_x = cx + self.stick_knob_offset[0]
        knob_y = cy + self.stick_knob_offset[1]

        # Sombra
        shadow_surf = pygame.Surface((base_r * 2 + 8, base_r * 2 + 8), pygame.SRCALPHA)
        pygame.draw.circle(
            shadow_surf, (0, 0, 0, 100),
            (base_r + 4, base_r + 6), base_r
        )
        screen.blit(shadow_surf, (cx - base_r - 4, cy - base_r - 4))

        # Base
        pygame.draw.circle(screen, (30, 35, 50), (cx, cy), base_r)
        pygame.draw.circle(screen, (20, 25, 40), (cx, cy), base_r - 2)
        pygame.draw.circle(screen, (60, 70, 90), (cx, cy), base_r, 2)

        # Marcações
        mark_color = (90, 110, 150)
        mark_len = 5
        pygame.draw.line(screen, mark_color, (cx, cy - base_r + 4), (cx, cy - base_r + 4 + mark_len), 1)
        pygame.draw.line(screen, mark_color, (cx, cy + base_r - 4), (cx, cy + base_r - 4 - mark_len), 1)
        pygame.draw.line(screen, mark_color, (cx - base_r + 4, cy), (cx - base_r + 4 + mark_len, cy), 1)
        pygame.draw.line(screen, mark_color, (cx + base_r - 4, cy), (cx + base_r - 4 - mark_len, cy), 1)

        # Haste
        if self.stick_active or self.stick_dragging:
            pygame.draw.line(
                screen, (120, 140, 180),
                (cx, cy), (int(knob_x), int(knob_y)), 3
            )

        # Knob
        shadow_knob = pygame.Surface((knob_r * 2 + 6, knob_r * 2 + 6), pygame.SRCALPHA)
        pygame.draw.circle(
            shadow_knob, (0, 0, 0, 120),
            (knob_r + 3, knob_r + 4), knob_r
        )
        screen.blit(shadow_knob, (knob_x - knob_r - 3, knob_y - knob_r - 3))

        hovered = (self.hovered_button == "stick" or self.stick_dragging)
        if hovered:
            outer_color = (110, 130, 170)
            inner_color = (70, 90, 130)
        else:
            outer_color = (80, 95, 130)
            inner_color = (50, 60, 85)

        pygame.draw.circle(screen, outer_color, (int(knob_x), int(knob_y)), knob_r)
        pygame.draw.circle(screen, inner_color, (int(knob_x), int(knob_y)), knob_r - 3)
        pygame.draw.circle(screen, (150, 170, 210), (int(knob_x), int(knob_y)), knob_r, 2)

        highlight_offset = -knob_r // 3
        pygame.draw.circle(
            screen, (200, 220, 255, 120),
            (int(knob_x) + highlight_offset, int(knob_y) + highlight_offset),
            max(2, knob_r // 4)
        )

    def _draw_zoom_slider(self, screen):
        if not self.slider_rect:
            return

        rect = self.slider_rect
        hovered = (self.hovered_button == "slider" or self.slider_dragging)

        # Label "ZOOM" acima
        label_font = self._get_font(11, bold=True)
        zoom_label = label_font.render("ZOOM", True, (140, 160, 200))
        screen.blit(zoom_label, (
            rect.x,
            rect.y - 12
        ))

        # Porcentagem à direita
        percent = int(self.slider_knob_x * 100)
        percent_text = label_font.render(f"{percent}%", True, (180, 200, 240))
        screen.blit(percent_text, (
            rect.right - percent_text.get_width(),
            rect.y - 12
        ))

        # Trilha
        pygame.draw.rect(
            screen, (25, 30, 45),
            (rect.x - 2, rect.y - 2, rect.width + 4, rect.height + 4),
            border_radius=6
        )
        pygame.draw.rect(
            screen, (50, 60, 85),
            rect, border_radius=4
        )

        # Preenchimento
        center_x = rect.x + rect.width // 2
        knob_x = rect.x + int(rect.width * self.slider_knob_x)
        fill_color = (100, 150, 230) if hovered else (70, 110, 190)

        if knob_x > center_x:
            pygame.draw.rect(
                screen, fill_color,
                (center_x, rect.y, knob_x - center_x, rect.height),
                border_radius=4
            )
        elif knob_x < center_x:
            pygame.draw.rect(
                screen, fill_color,
                (knob_x, rect.y, center_x - knob_x, rect.height),
                border_radius=4
            )

        # Marcador central
        pygame.draw.line(
            screen, (200, 200, 220),
            (center_x, rect.y - 3), (center_x, rect.y + rect.height + 3),
            2
        )

        # Knob
        knob_r = self.SLIDER_KNOB_RADIUS

        shadow_surf = pygame.Surface((knob_r * 2 + 6, knob_r * 2 + 6), pygame.SRCALPHA)
        pygame.draw.circle(
            shadow_surf, (0, 0, 0, 130),
            (knob_r + 3, knob_r + 3), knob_r
        )
        screen.blit(shadow_surf, (knob_x - knob_r - 3, rect.centery - knob_r - 3))

        if hovered:
            knob_color = (200, 220, 255)
            border_color = (255, 255, 255)
        else:
            knob_color = (170, 190, 230)
            border_color = (220, 230, 250)

        pygame.draw.circle(screen, knob_color, (knob_x, rect.centery), knob_r)
        pygame.draw.circle(screen, border_color, (knob_x, rect.centery), knob_r, 2)

        pygame.draw.circle(
            screen, (255, 255, 255),
            (knob_x - knob_r // 3, rect.centery - knob_r // 3),
            max(2, knob_r // 4)
        )

    def _draw_capture_button(self, screen):
        if not self.btn_capture_rect:
            return
        rect = self.btn_capture_rect
        hovered = (self.hovered_button == "capture")

        pulse = 0.5 + 0.5 * math.sin(self.animation_time * 5) if hovered else 0
        radius = rect.width // 2

        if hovered:
            glow = pygame.Surface((rect.width + 20, rect.height + 20), pygame.SRCALPHA)
            glow_alpha = int(80 + 60 * pulse)
            pygame.draw.circle(glow, (255, 215, 0, glow_alpha),
                               (rect.width // 2 + 10, rect.height // 2 + 10),
                               radius + 8)
            screen.blit(glow, (rect.x - 10, rect.y - 10))

        color = (220, 60, 60) if hovered else (180, 40, 40)
        pygame.draw.circle(screen, color, rect.center, radius)
        pygame.draw.circle(screen, (255, 100, 100), rect.center, radius, 2)

        pygame.draw.circle(screen, (80, 20, 20), rect.center, radius - 8)
        pygame.draw.circle(screen, (40, 10, 10), rect.center, radius - 14)

        reflex_rect = pygame.Rect(0, 0, radius // 2, radius // 4)
        reflex_rect.center = (rect.centerx - radius // 3, rect.centery - radius // 3)
        pygame.draw.ellipse(screen, (255, 255, 255, 120), reflex_rect)

    def _render_flash(self, screen):
        flash = pygame.Surface(
            (self.game.screen_manager.window_width,
             self.game.screen_manager.window_height),
            pygame.SRCALPHA
        )
        flash.fill((255, 255, 255, int(self.flash_alpha)))
        screen.blit(flash, (0, 0))