# src/scenes/game_scene/components/overlays/pause_overlay.py

import pygame
from src.scenes.game_scene.components.overlays.base_overlay import BaseOverlay

_FONT_CACHE = {}


class PauseOverlay(BaseOverlay):
    """Overlay de pausa – centralizado, título e 3 botões com hover amarelo"""

    def __init__(self, game_scene):
        super().__init__(game_scene)

        self.active = True
        self.selected_index = 0
        self.button_rects = []

        self.colors = {
            'accent': (255, 215, 0),
            'bg_dark': (10, 12, 25),
            'bg_medium': (25, 30, 50),
            'panel_border': (255, 215, 0),
            'panel_border_inner': (220, 200, 120),
            'button_bg': (50, 60, 110),
            'button_bg_hover': (255, 215, 0),
            'button_text_hover': (255, 255, 40),
            'button_text': (255, 255, 255),
        }

        self.buttons = []
        self.animation_progress = 0
        self.scanline_offset = 0

        self._setup_buttons()

    def _setup_buttons(self):
        self.buttons = [
            {"text": "VOLTAR AO JOGO", "callback": self._resume_game},
            {"text": "CONFIGURAÇÕES", "callback": self._open_settings},
            {"text": "VOLTAR AO MENU", "callback": self._return_to_menu},
        ]

    def _get_font(self, size, bold=False):
        key = (size, bold)
        if key not in _FONT_CACHE:
            font = pygame.font.Font(None, size)
            if bold:
                font.set_bold(True)
            _FONT_CACHE[key] = font
        return _FONT_CACHE[key]

    def _resume_game(self):
        self.game_scene.paused = False
        self.game_scene.game_paused = False
        if hasattr(self.game_scene, 'wave_manager'):
            self.game_scene.wave_manager.paused = False
        self.active = False
        self.game_scene.overlay_manager.hide()

    def _open_settings(self):
        from src.scenes.settings_scene.settings_scene import SettingsScene
        from src.managers.sounds.sound_manager import sound_manager

        sound_manager.stop_music(fade_ms=200)
        self.active = False
        self.game_scene.overlay_manager.hide()

        settings_scene = SettingsScene(
            self.game_scene.game,
            on_back_callback=self._on_return_from_settings
        )
        self.game_scene.game.current_scene = settings_scene

    def _on_return_from_settings(self):
        self.game_scene.paused = True
        self.game_scene.game_paused = True
        if hasattr(self.game_scene, 'wave_manager'):
            self.game_scene.wave_manager.paused = True

        self.active = True
        from src.scenes.game_scene.components.managers.overlay_manager import OverlayType
        self.game_scene.overlay_manager.current_overlay = self
        self.game_scene.overlay_manager.current_type = OverlayType.PAUSE

        self.game_scene.game.current_scene = self.game_scene

        from src.managers.sounds.sound_manager import sound_manager
        sound_manager.play_random_battle_music()

    def _return_to_menu(self):
        self.game_scene.cleanup()
        self.active = False
        self.game_scene.overlay_manager.hide()
        self.game_scene.game.current_scene = self.game_scene.game.menu_scene

    def handle_event(self, event):
        if not self.active:
            return False

        # Hover (só atualiza o índice, não consome)
        if event.type == pygame.MOUSEMOTION:
            for i, rect in enumerate(self.button_rects):
                if rect and rect.collidepoint(event.pos):
                    self.selected_index = i
                    break
            return False

        # Clique do mouse
        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            for i, rect in enumerate(self.button_rects):
                if rect and rect.collidepoint(event.pos):
                    if i < len(self.buttons):
                        self.buttons[i]["callback"]()
                        return True
            return False

        # Teclado
        if event.type == pygame.KEYDOWN:
            if event.key in (pygame.K_ESCAPE, pygame.K_p):
                self._resume_game()
                return True
            elif event.key in (pygame.K_DOWN, pygame.K_s):
                self.selected_index = (self.selected_index + 1) % len(self.buttons)
                return True
            elif event.key in (pygame.K_UP, pygame.K_w):
                self.selected_index = (self.selected_index - 1) % len(self.buttons)
                return True
            elif event.key in (pygame.K_RETURN, pygame.K_SPACE):
                if 0 <= self.selected_index < len(self.buttons):
                    self.buttons[self.selected_index]["callback"]()
                    return True

        return False

    def update(self, dt):
        if not self.active:
            return
        self.animation_progress = min(1.0, self.animation_progress + dt * 2.5)
        self.scanline_offset = (self.scanline_offset + 1) % 4

    def render(self, screen):
        if not self.active:
            return

        viewport = self.get_viewport_rect()
        vx, vy = viewport.x, viewport.y
        vw, vh = viewport.width, viewport.height

        # Fundo escuro
        overlay_surface, _ = self.create_overlay_surface(alpha=200)
        screen.blit(overlay_surface, (vx, vy))

        # Painel – mais para cima (8% do topo)
        panel_w = min(int(vw * 0.55), 560)
        panel_h = min(int(vh * 0.50), 400)

        scale = min(1.0, self.animation_progress)
        if scale < 1.0:
            panel_w = int(panel_w * scale)
            panel_h = int(panel_h * scale)

        panel_x = vx + (vw - panel_w) // 2
        panel_y = vy + int(vh * 0.08)

        # Superfície do painel
        panel_surf = pygame.Surface((panel_w, panel_h), pygame.SRCALPHA)

        # Gradiente de fundo (mais escuro)
        for i in range(panel_h):
            t = i / panel_h
            r = int(8 + t * 18)
            g = int(12 + t * 22)
            b = int(25 + t * 40)
            alpha = int(245 - t * 15)
            pygame.draw.line(panel_surf, (r, g, b, alpha), (0, i), (panel_w, i))

        # Bordas douradas grossas
        pygame.draw.rect(panel_surf, self.colors['panel_border'],
                         panel_surf.get_rect(), 4, border_radius=18)
        pygame.draw.rect(panel_surf, self.colors['panel_border_inner'],
                         panel_surf.get_rect().inflate(-12, -12), 2, border_radius=14)

        # Cantos decorativos
        for cx, cy in [(24, 24), (panel_w - 24, 24), (24, panel_h - 24), (panel_w - 24, panel_h - 24)]:
            pygame.draw.circle(panel_surf, (255, 215, 0), (cx, cy), 14, 3)
            pygame.draw.circle(panel_surf, (255, 215, 0), (cx, cy), 6)
            pygame.draw.circle(panel_surf, (255, 255, 255), (cx, cy), 3)

        screen.blit(panel_surf, (panel_x, panel_y))

        # Título
        title_size = max(42, int(vh * 0.07))
        title_font = self._get_font(title_size, True)
        title_text = "JOGO PAUSADO"
        title_surf = title_font.render(title_text, True, self.colors['accent'])
        title_shadow = title_font.render(title_text, True, (0, 0, 0))

        tx = panel_x + (panel_w - title_surf.get_width()) // 2
        ty = panel_y + int(panel_h * 0.10)
        screen.blit(title_shadow, (tx + 4, ty + 4))
        screen.blit(title_surf, (tx, ty))

        # Linha decorativa
        line_y = ty + title_surf.get_height() + 18
        line_w = int(panel_w * 0.4)
        line_x = panel_x + (panel_w - line_w) // 2
        for i in range(line_w):
            brightness = 180 + int(75 * (0.5 + 0.5 * pygame.math.Vector2(1, 0).rotate(i * 2).x))
            brightness = max(100, min(255, brightness))
            pygame.draw.line(screen, (255, brightness, 0), (line_x + i, line_y), (line_x + i, line_y + 4))

        # Botões
        button_size = max(30, int(vh * 0.05))
        button_font = self._get_font(button_size, True)

        num_buttons = len(self.buttons)
        btn_w = int(panel_w * 0.72)
        btn_h = int(panel_h * 0.16)   # mais altos

        available_height = panel_h - (line_y + 30 - panel_y) - int(panel_h * 0.06)
        total_height = num_buttons * btn_h
        spacing = max(28, (available_height - total_height) // (num_buttons + 1))
        if spacing < 32:
            spacing = 32

        start_y = line_y + 30 + spacing
        self.button_rects = []

        for i, btn_data in enumerate(self.buttons):
            is_hovered = (i == self.selected_index)

            bx = panel_x + (panel_w - btn_w) // 2
            by = start_y + i * (btn_h + spacing)

            rect = pygame.Rect(bx, by, btn_w, btn_h)
            self.button_rects.append(rect)

            # Sombra
            shadow_rect = rect.copy()
            shadow_rect.y += 5
            pygame.draw.rect(screen, (0, 0, 0, 120), shadow_rect, border_radius=12)

            # Fundo – hover amarelo
            if is_hovered:
                bg_color = self.colors['button_bg_hover']  # amarelo
                border_color = (255, 255, 255)
                text_color = self.colors['button_text_hover']  # preto
            else:
                bg_color = self.colors['button_bg']
                border_color = (140, 150, 200)
                text_color = self.colors['button_text']

            # Gradiente
            for j in range(btn_h):
                t = j / btn_h
                if is_hovered:
                    r = min(255, bg_color[0] + int(20 * t))
                    g = min(255, bg_color[1] + int(20 * t))
                    b = min(255, bg_color[2] + int(10 * t))
                else:
                    r = min(255, bg_color[0] + int(30 * t))
                    g = min(255, bg_color[1] + int(30 * t))
                    b = min(255, bg_color[2] + int(30 * t))
                pygame.draw.line(screen, (r, g, b), (bx, by + j), (bx + btn_w, by + j))

            pygame.draw.rect(screen, border_color, rect, 3, border_radius=12)

            # Texto
            text_surf = button_font.render(btn_data["text"], True, text_color)
            text_x = bx + (btn_w - text_surf.get_width()) // 2
            text_y = by + (btn_h - text_surf.get_height()) // 2
            screen.blit(text_surf, (text_x, text_y))

        # Scanline sutil
        for i in range(self.scanline_offset, int(panel_h), 4):
            pygame.draw.line(panel_surf, (10, 10, 20, 20), (0, i), (panel_w, i), 1)

        screen.blit(panel_surf, (panel_x, panel_y))