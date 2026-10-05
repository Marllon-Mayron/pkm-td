# src/ui/screen_template.py
"""
StandardScreen — classe base para todas as telas.
Agora com:
  - Ações (get_actions()) para amarrar botões a métodos
  - Filtro por abas (.tab nos widgets)
  - Render por z
"""
import pygame

from src.scenes.base_scene import BaseScene
from src.ui.theme import FontBook, Palette
from src.ui.windowskin import dialog_skin
from src.ui.layout import viewport, rel_rect, Anchor, draw_text_centered
from src.ui.widgets import Button


class StandardScreen(BaseScene):
    title             = ""
    title_color       = Palette.TEXT_LIGHT
    title_shadow      = (16, 24, 48)
    show_back_button  = True
    background_image  = None
    background_dim    = 0

    def __init__(self, game):
        super().__init__(game)
        self.widgets = []
        self._widgets_by_id = {}
        self._last_size = (0, 0)
        self.vp = viewport(self.screen_manager)
        self._last_size = (self.screen_manager.window_width,
                           self.screen_manager.window_height)
        self._title_rect = None
        self._back_btn = None
        self.active_tab = None     # None = mostra tudo
        self._rebuild()

    # =================================================================
    # API PARA SUBCLASSES
    # =================================================================
    def build(self):
        """Sobrescreva para montar widgets."""
        pass

    def update(self, dt):
        """Sobrescreva para lógica por-frame."""
        pass

    def draw_content(self, screen):
        """Sobrescreva para desenhar conteúdo extra."""
        pass

    def get_actions(self):
        """
        Sobrescreva para retornar { nome_da_acao: callable }.
        O ScreenLoader amarra o `on_click` (etc.) dos widgets a esses métodos.
        """
        return {}

    def on_back(self):
        self.game.current_scene = self.game.menu_scene

    def set_active_tab(self, tab_name):
        self.active_tab = tab_name

    # =================================================================
    # Helpers
    # =================================================================
    def add(self, widget):
        if not hasattr(widget, "z"):
            widget.z = len(self.widgets)
        self.widgets.append(widget)
        if widget.id:
            self._widgets_by_id[widget.id] = widget
        return widget

    def get(self, wid):
        return self._widgets_by_id.get(wid)

    def clear_widgets(self):
        self.widgets.clear()
        self._widgets_by_id.clear()

    def _is_visible_by_tab(self, w):
        if self.active_tab is None:
            return True
        wtab = getattr(w, "tab", None)
        return wtab is None or wtab == self.active_tab

    # =================================================================
    # Ciclo
    # =================================================================
    def _rebuild(self):
        self.clear_widgets()
        self._create_chrome()
        self.build()

    def _create_chrome(self):
        vp = self.vp
        if self.title:
            size = max(24, int(vp.height * 0.06))
            self._title_rect = pygame.Rect(vp.x, vp.y + int(vp.height * 0.03),
                                           vp.width, size + 10)
        if self.show_back_button:
            bw = int(vp.width * 0.10)
            bh = int(vp.height * 0.065)
            rect = rel_rect(vp, 0.02, 0.03, bw / vp.width, bh / vp.height,
                            Anchor.TOP_LEFT)
            self._back_btn = Button(
                "__back__", rect, "Voltar",
                on_click=lambda b: self._on_back_click(),
                style="danger",
                font_size=max(16, int(rect.height * 0.5)),
                z=99998,
            )
            self.widgets.append(self._back_btn)

    def _on_back_click(self):
        try:
            self.on_back()
        except Exception as e:
            print(f"[UI] erro no on_back: {e}")

    def on_resize(self):
        self._rebuild()

    def _check_resize(self):
        cur = (self.screen_manager.window_width,
               self.screen_manager.window_height)
        if cur != self._last_size:
            self._last_size = cur
            self.vp = viewport(self.screen_manager)
            self._rebuild()

    # =================================================================
    # Eventos / Update / Render
    # =================================================================
    def handle_event(self, event):
        if event.type == pygame.VIDEORESIZE:
            self.on_resize(); return
        if self._back_btn and self._back_btn.handle_event(event):
            return
        ordered = sorted(self.widgets, key=lambda x: getattr(x, "z", 0),
                         reverse=True)
        for w in ordered:
            if w is self._back_btn:
                continue
            if not self._is_visible_by_tab(w):
                continue
            if w.handle_event(event):
                return

    def fixed_update(self, dt):
        self._check_resize()
        for w in self.widgets:
            w.update(dt)
        self.update(dt)

    def render(self, screen):
        self._draw_background(screen)
        self._draw_title(screen)
        for w in sorted(self.widgets, key=lambda x: getattr(x, "z", 0)):
            if not self._is_visible_by_tab(w):
                continue
            w.render(screen)
        self.draw_content(screen)
        if self.paused:
            self._render_pause_overlay(screen)

    # =================================================================
    # Desenho padrão
    # =================================================================
    def _draw_background(self, screen):
        w = self.screen_manager.window_width
        h = self.screen_manager.window_height
        if self.background_image:
            try:
                scaled = pygame.transform.smoothscale(self.background_image, (w, h))
                screen.blit(scaled, (0, 0))
                if self.background_dim > 0:
                    ov = pygame.Surface((w, h), pygame.SRCALPHA)
                    ov.fill((0, 0, 0, self.background_dim))
                    screen.blit(ov, (0, 0))
                return
            except Exception:
                pass
        for i in range(h):
            t = i / h
            r = int(Palette.BG_DEEP[0] + t * (Palette.BG_MID[0] - Palette.BG_DEEP[0]))
            g = int(Palette.BG_DEEP[1] + t * (Palette.BG_MID[1] - Palette.BG_DEEP[1]))
            b = int(Palette.BG_DEEP[2] + t * (Palette.BG_MID[2] - Palette.BG_DEEP[2]))
            pygame.draw.line(screen, (r, g, b), (0, i), (w, i))

    def _draw_title(self, screen):
        if not self._title_rect or not self.title:
            return
        size = max(24, int(self.vp.height * 0.06))
        font = FontBook.get(size, bold=True)
        bar = pygame.Rect(self.vp.x + int(self.vp.width * 0.15),
                          self._title_rect.y,
                          int(self.vp.width * 0.70),
                          self._title_rect.height)
        dialog_skin.render(screen, bar, border_color=Palette.GOLD,
                           fill_override=(72, 88, 128))
        draw_text_centered(screen, self.title, font, self.title_color, bar,
                           shadow_color=self.title_shadow, shadow_offset=(3, 3))

    def _render_pause_overlay(self, screen):
        w = self.screen_manager.window_width
        h = self.screen_manager.window_height
        ov = pygame.Surface((w, h), pygame.SRCALPHA)
        ov.fill((0, 0, 0, 180))
        screen.blit(ov, (0, 0))
        font = FontBook.get(72, bold=True)
        surf = font.render("PAUSADO", True, (240, 240, 240))
        screen.blit(surf, (w // 2 - surf.get_width() // 2,
                           h // 2 - surf.get_height() // 2))