# src/scenes/debug_scene/debug_scene.py
"""
Cena de Debug — container com abas.

- Responsável pelo header, abas principais, layout geral e UI primitives
  (botões, sliders, painéis, etc) reutilizadas pelas abas filhas.
- Cada aba concreta vive em `tabs/` e expõe a interface:
    handle_event(event)
    on_click(name)
    render(screen, left_rect, right_rect)
    render_footer(screen, footer_rect)
    fixed_update(dt)
    has_focus() / clear_focus()

Somente acessível com DEBUG_MODE = True.
"""

import pygame

from src.scenes.base_scene import BaseScene
from src.config.global_settings import DEBUG_MODE


class DebugScene(BaseScene):
    TAB_POKEMON = "pokemon"
    TAB_ITEMS = "items"
    TAB_PROFILE = "profile"
    _PARENT_CLICKS = ("close", "tab_pokemon", "tab_items", "tab_profile")

    # ------------------------------------------------------------------
    def __init__(self, game):
        super().__init__(game)
        if not DEBUG_MODE:
            from src.scenes.menu_scene import MenuScene
            self.game.current_scene = MenuScene(self.game)
            return

        self.tab = self.TAB_POKEMON

        # Estado global (immediate-mode UI)
        self._clicks = []
        self._hovered = None
        self._dragging_slider = None
        self._slider_meta = {}  # click_name -> (min_v, max_v, on_change)

        # Toast
        self.message = ""
        self.message_timer = 0.0

        # Fonte cache
        self._fonts = {}

        # Abas filhas
        from .tabs.pokemon_tab import PokemonTab
        from .tabs.items_tab import ItemsTab
        from .tabs.profile_tab import ProfileTab

        self.pokemon_tab = PokemonTab(self)
        self.items_tab = ItemsTab(self)
        self.profile_tab = ProfileTab(self)

        self._tabs = {
            self.TAB_POKEMON: self.pokemon_tab,
            self.TAB_ITEMS: self.items_tab,
            self.TAB_PROFILE: self.profile_tab,
        }

    @property
    def active_tab(self):
        return self._tabs[self.tab]

    # ==================================================================
    # UI PRIMITIVES  (usadas pelas abas)
    # ==================================================================
    def get_font(self, size):
        size = max(10, int(size))
        if size not in self._fonts:
            self._fonts[size] = pygame.font.Font(None, size)
        return self._fonts[size]

    def register_click(self, name, rect):
        self._clicks.append((name, rect))
        if self._hovered is None and rect.collidepoint(pygame.mouse.get_pos()):
            self._hovered = name

    def find_rect(self, name):
        for n, r in self._clicks:
            if n == name:
                return r
        return None

    def find_click_at(self, pos):
        for name, rect in reversed(self._clicks):
            if rect.collidepoint(pos):
                return name
        return None

    def show_message(self, text, duration=2.5):
        self.message = text
        self.message_timer = duration

    def save_game(self):
        try:
            from src.managers.save_manager import save_manager
            slot = save_manager.current_save_file or 1
            self.game.player.save_game(slot=slot)
        except Exception as e:
            print(f"[DEBUG] Save falhou: {e}")

    def wrap_text(self, text, font, max_width):
        words = str(text).split(" ")
        lines, cur = [], ""
        for w in words:
            test = (cur + " " + w).strip()
            if font.size(test)[0] <= max_width:
                cur = test
            else:
                if cur:
                    lines.append(cur)
                cur = w
        if cur:
            lines.append(cur)
        return lines

    # ---------- Botões / painéis ----------
    def draw_button(self, screen, rect, text, *, danger=False, success=False,
                    primary=False, font_size=None):
        hovered = rect.collidepoint(pygame.mouse.get_pos())
        if font_size is None:
            font_size = max(12, rect.height * 0.45)
        if danger:
            base = (140, 45, 45) if hovered else (100, 30, 30); border = (220, 70, 70)
        elif success:
            base = (45, 110, 55) if hovered else (30, 80, 40); border = (90, 210, 110)
        elif primary:
            base = (75, 90, 140) if hovered else (50, 60, 100); border = (130, 170, 240)
        else:
            base = (65, 65, 85) if hovered else (45, 45, 60); border = (110, 110, 140)
        pygame.draw.rect(screen, base, rect, border_radius=6)
        pygame.draw.rect(screen, border, rect, 2, border_radius=6)
        f = self.get_font(font_size)
        t = f.render(text, True, (240, 240, 250))
        screen.blit(t, t.get_rect(center=rect.center))

    def draw_tab(self, screen, rect, label, active):
        hovered = rect.collidepoint(pygame.mouse.get_pos())
        if active:
            base, border = (60, 50, 100), (180, 150, 255)
        elif hovered:
            base, border = (45, 40, 65), (120, 100, 160)
        else:
            base, border = (30, 28, 45), (70, 60, 90)
        pygame.draw.rect(screen, base, rect, border_radius=6)
        pygame.draw.rect(screen, border, rect, 2, border_radius=6)
        if active:
            pygame.draw.rect(screen, (255, 215, 0),
                             (rect.x + 8, rect.bottom - 4, rect.width - 16, 2))
        f = self.get_font(max(14, rect.height * 0.42))
        t = f.render(label, True, (255, 255, 255) if active else (200, 200, 220))
        screen.blit(t, t.get_rect(center=rect.center))

    def draw_subtab(self, screen, rect, label, active):
        hovered = rect.collidepoint(pygame.mouse.get_pos())
        if active:
            base, border = (55, 70, 110), (150, 190, 255)
        elif hovered:
            base, border = (40, 48, 70), (100, 130, 180)
        else:
            base, border = (30, 32, 48), (60, 65, 90)
        pygame.draw.rect(screen, base, rect, border_radius=5)
        pygame.draw.rect(screen, border, rect, 2, border_radius=5)
        f = self.get_font(max(12, rect.height * 0.5))
        t = f.render(label, True, (255, 255, 255) if active else (200, 200, 220))
        screen.blit(t, t.get_rect(center=rect.center))

    def draw_panel(self, screen, rect, bg=(22, 25, 38)):
        pygame.draw.rect(screen, bg, rect, border_radius=8)
        pygame.draw.rect(screen, (60, 60, 90), rect, 2, border_radius=8)

    def draw_section_title(self, screen, x, y, w, text):
        f = self.get_font(13)
        label = f.render(text, True, (170, 180, 210))
        screen.blit(label, (x, y))
        line_y = y + label.get_height() // 2
        line_x = x + label.get_width() + 10
        line_w = w - label.get_width() - 10
        if line_w > 0:
            pygame.draw.line(screen, (60, 60, 90),
                             (line_x, line_y), (line_x + line_w, line_y), 1)

    # ---------- Componentes de form ----------
    def render_slider(self, screen, x, y, w, h, label, value, min_v, max_v,
                      click_name, on_change=None):
        self._slider_meta[click_name] = (min_v, max_v, on_change)

        lf = self.get_font(13)
        label_w = 0
        if label:
            lbl = lf.render(label, True, (200, 200, 220))
            screen.blit(lbl, (x, y + (h - lbl.get_height()) // 2))
            label_w = lbl.get_width() + 8

        bar_x = x + label_w
        value_w = 34
        bar_w = max(20, w - label_w - value_w - 4)
        bar_rect = pygame.Rect(bar_x, y + 3, bar_w, h - 6)
        self.register_click(click_name, bar_rect)

        pygame.draw.rect(screen, (30, 30, 45), bar_rect, border_radius=3)

        ratio = (value - min_v) / max(1, (max_v - min_v))
        fill_w = int(bar_rect.width * ratio)
        if fill_w > 0:
            if ratio < 0.5:
                r, g, b = 200, int(60 + 140 * (ratio / 0.5)), 60
            else:
                r, g, b = int(200 - 100 * ((ratio - 0.5) / 0.5)), 200, 60
            pygame.draw.rect(screen, (r, g, b),
                             (bar_rect.x, bar_rect.y, fill_w, bar_rect.height),
                             border_radius=3)

        border = (255, 200, 60) if self._hovered == click_name else (80, 80, 110)
        pygame.draw.rect(screen, border, bar_rect, 1, border_radius=3)

        vf = self.get_font(13)
        vt = vf.render(str(value), True, (255, 255, 255))
        screen.blit(vt, (bar_rect.right + 6, y + (h - vt.get_height()) // 2))

    def render_toggle(self, screen, x, y, w, h, label, value, click_name):
        lf = self.get_font(14)
        lbl = lf.render(label, True, (200, 200, 220))
        screen.blit(lbl, (x, y + (h - lbl.get_height()) // 2))

        toggle_w = 74
        toggle_rect = pygame.Rect(x + w - toggle_w, y, toggle_w, h)
        self.register_click(click_name, toggle_rect)
        hovered = toggle_rect.collidepoint(pygame.mouse.get_pos())

        if value:
            bg = (80, 160, 90) if hovered else (60, 130, 70)
            border, text = (120, 220, 130), "ATIVO"
        else:
            bg = (80, 80, 95) if hovered else (60, 60, 70)
            border, text = (120, 120, 130), "INATIVO"

        pygame.draw.rect(screen, bg, toggle_rect, border_radius=h // 2)
        pygame.draw.rect(screen, border, toggle_rect, 2, border_radius=h // 2)
        f = self.get_font(12)
        t = f.render(text, True, (255, 255, 255))
        screen.blit(t, t.get_rect(center=toggle_rect.center))

    def render_gender_row(self, screen, x, y, w, h, label, current, prefix):
        lf = self.get_font(14)
        lbl = lf.render(label, True, (200, 200, 220))
        screen.blit(lbl, (x, y + (h - lbl.get_height()) // 2))

        btn_w, gap = 66, 6
        start_x = x + w - (btn_w * 3 + gap * 2)
        options = [
            ("Macho", "male", f"{prefix}_male", (70, 120, 200)),
            ("Fêmea", "female", f"{prefix}_female", (230, 80, 120)),
            ("Sem", None, f"{prefix}_none", (120, 120, 120)),
        ]
        for text, val, cname, color in options:
            btn = pygame.Rect(start_x, y, btn_w, h)
            selected = (current == val)
            hovered = btn.collidepoint(pygame.mouse.get_pos())
            base = color if selected else tuple(max(0, c - 55) for c in color)
            if hovered:
                base = tuple(min(255, c + 25) for c in base)
            pygame.draw.rect(screen, base, btn, border_radius=5)
            pygame.draw.rect(screen,
                             (255, 255, 255) if selected else (80, 80, 100),
                             btn, 2 if selected else 1, border_radius=5)
            bf = self.get_font(12)
            bt = bf.render(text, True, (255, 255, 255))
            screen.blit(bt, bt.get_rect(center=btn.center))
            self.register_click(cname, btn)
            start_x += btn_w + gap

    def render_cycle_row(self, screen, x, y, w, h, label, value_text,
                         click_prev, click_next):
        lf = self.get_font(14)
        lbl = lf.render(label, True, (200, 200, 220))
        screen.blit(lbl, (x, y + (h - lbl.get_height()) // 2))

        btn_w, val_w = h, 200
        right_x = x + w

        next_rect = pygame.Rect(right_x - btn_w, y, btn_w, h)
        self.register_click(click_next, next_rect)
        self.draw_button(screen, next_rect, ">", font_size=15)
        right_x -= btn_w + 4

        val_rect = pygame.Rect(right_x - val_w, y, val_w, h)
        pygame.draw.rect(screen, (30, 30, 45), val_rect, border_radius=4)
        pygame.draw.rect(screen, (80, 80, 110), val_rect, 1, border_radius=4)
        vf = self.get_font(13)
        vt = vf.render(str(value_text), True, (255, 255, 255))
        screen.blit(vt, vt.get_rect(center=val_rect.center))
        right_x -= val_w + 4

        prev_rect = pygame.Rect(right_x - btn_w, y, btn_w, h)
        self.register_click(click_prev, prev_rect)
        self.draw_button(screen, prev_rect, "<", font_size=15)

    def render_text_input(self, screen, x, y, w, h, label, value, click_name,
                          focus_key=None):
        lf = self.get_font(14)
        lbl = lf.render(label, True, (200, 200, 220))
        screen.blit(lbl, (x, y + (h - lbl.get_height()) // 2))

        label_w = lbl.get_width() + 8
        inp_rect = pygame.Rect(x + label_w, y, w - label_w, h)
        self.register_click(click_name, inp_rect)
        pygame.draw.rect(screen, (15, 15, 25), inp_rect, border_radius=4)

        is_focused = focus_key and self.active_tab.get_focus() == focus_key
        border_color = (255, 200, 60) if is_focused else (80, 80, 110)
        pygame.draw.rect(screen, border_color, inp_rect, 2, border_radius=4)

        nf = self.get_font(13)
        display = value if value else "(vazio)"
        color = (230, 230, 240) if value else (110, 110, 130)
        if is_focused:
            display += "_"
        tn = nf.render(display, True, color)
        screen.blit(tn, (inp_rect.x + 8,
                         inp_rect.y + (inp_rect.height - tn.get_height()) // 2))

    # ==================================================================
    # EVENTOS
    # ==================================================================
    def handle_event(self, event):
        # ESC global
        if event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE:
            if self.active_tab.has_focus():
                self.active_tab.clear_focus()
                return
            self._close()
            return

        # Fim de drag
        if event.type == pygame.MOUSEBUTTONUP and event.button == 1:
            self._dragging_slider = None

        # Drag ativo
        if (event.type == pygame.MOUSEMOTION and event.buttons[0]
                and self._dragging_slider):
            self._update_slider_from_mouse(self._dragging_slider, event.pos)

        # Mouse down: checa primeiro os botões do pai
        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            clicked = self.find_click_at(event.pos)
            if clicked in self._PARENT_CLICKS:
                if clicked == "close":
                    self._close()
                    return
                if clicked == "tab_pokemon" and self.tab != self.TAB_POKEMON:
                    self.tab = self.TAB_POKEMON
                    self.active_tab.clear_focus()
                    return
                if clicked == "tab_items" and self.tab != self.TAB_ITEMS:
                    self.tab = self.TAB_ITEMS
                    self.active_tab.clear_focus()
                    return
                if clicked == "tab_profile" and self.tab != self.TAB_PROFILE:
                    self.tab = self.TAB_PROFILE
                    self.active_tab.clear_focus()
                    return
                # se já estava na aba, apenas ignora
                if clicked in ("tab_pokemon", "tab_items", "tab_profile"):
                    return

            if clicked and clicked.endswith("_slider"):
                self._dragging_slider = clicked
                self._update_slider_from_mouse(clicked, event.pos)

        # Repassa para a aba ativa
        self.active_tab.handle_event(event)

    def _update_slider_from_mouse(self, name, pos):
        rect = self.find_rect(name)
        meta = self._slider_meta.get(name)
        if not (rect and meta):
            return
        min_v, max_v, cb = meta
        ratio = (pos[0] - rect.x) / max(1, rect.width)
        ratio = max(0.0, min(1.0, ratio))
        value = int(round(min_v + ratio * (max_v - min_v)))
        if cb:
            cb(value)

    def fixed_update(self, dt):
        if self.message_timer > 0:
            self.message_timer = max(0.0, self.message_timer - dt)
        self.active_tab.fixed_update(dt)

    def _close(self):
        from src.scenes.menu_scene import MenuScene
        self.game.current_scene = MenuScene(self.game)

    # ==================================================================
    # RENDER
    # ==================================================================
    def render(self, screen):
        self._clicks = []
        self._hovered = None
        self._slider_meta = {}

        vx = self.screen_manager.viewport_x
        vy = self.screen_manager.viewport_y
        vw = self.screen_manager.viewport_width
        vh = self.screen_manager.viewport_height

        # Fundo + grid
        screen.fill((12, 14, 22))
        for i in range(0, vw, 40):
            pygame.draw.line(screen, (18, 20, 32), (vx + i, vy), (vx + i, vy + vh), 1)
        for j in range(0, vh, 40):
            pygame.draw.line(screen, (18, 20, 32), (vx, vy + j), (vx + vw, vy + j), 1)

        # Header
        header_h = int(vh * 0.075)
        pygame.draw.rect(screen, (20, 22, 34), (vx, vy, vw, header_h))
        pygame.draw.line(screen, (100, 80, 130),
                         (vx, vy + header_h), (vx + vw, vy + header_h), 2)

        title_font = self.get_font(max(20, vh * 0.030))
        title = title_font.render("DEBUG MODE", True, (255, 220, 120))
        screen.blit(title, (vx + 20, vy + (header_h - title.get_height()) // 2))

        sub_font = self.get_font(max(14, vh * 0.020))
        sub = sub_font.render("· Painel de Desenvolvimento", True, (180, 180, 200))
        screen.blit(sub, (vx + 20 + title.get_width() + 12,
                          vy + (header_h - sub.get_height()) // 2 + 4))

        close_size = int(header_h * 0.6)
        close_rect = pygame.Rect(
            vx + vw - close_size - 15,
            vy + (header_h - close_size) // 2,
            close_size, close_size,
        )
        self.register_click("close", close_rect)
        self.draw_button(screen, close_rect, "X", danger=True,
                         font_size=max(14, close_size * 0.55))

        # Abas principais
        tab_y = vy + header_h + 8
        tab_h = int(vh * 0.05)
        tab_w = int(vw * 0.16)

        poke_tab = pygame.Rect(vx + 20, tab_y, tab_w, tab_h)
        item_tab = pygame.Rect(vx + 20 + (tab_w + 8), tab_y, tab_w, tab_h)
        prof_tab = pygame.Rect(vx + 20 + (tab_w + 8) * 2, tab_y, tab_w, tab_h)

        self.register_click("tab_pokemon", poke_tab)
        self.register_click("tab_items", item_tab)
        self.register_click("tab_profile", prof_tab)

        self.draw_tab(screen, poke_tab, "POKÉMON", self.tab == self.TAB_POKEMON)
        self.draw_tab(screen, item_tab, "ITENS", self.tab == self.TAB_ITEMS)
        self.draw_tab(screen, prof_tab, "PERFIL", self.tab == self.TAB_PROFILE)

        # Área de conteúdo
        content_top = tab_y + tab_h + 10
        footer_h = int(vh * 0.11)
        content_bottom = vy + vh - footer_h - 8

        left_w = int(vw * 0.32)
        left_rect = pygame.Rect(vx + 15, content_top, left_w, content_bottom - content_top)
        self.draw_panel(screen, left_rect)

        right_x = vx + 15 + left_w + 12
        right_w = vw - left_w - 30 - 12
        right_rect = pygame.Rect(right_x, content_top, right_w, content_bottom - content_top)
        self.draw_panel(screen, right_rect)

        # Delega conteúdo para a aba ativa
        self.active_tab.render(screen, left_rect, right_rect)

        # Rodapé
        footer_rect = pygame.Rect(vx + 15, vy + vh - footer_h + 5, vw - 30, footer_h - 10)
        self.draw_panel(screen, footer_rect, bg=(25, 25, 40))
        self.active_tab.render_footer(screen, footer_rect)

        # Toast
        if self.message_timer > 0:
            self._render_message(screen, vx, vy, vw, vh)

    def _render_message(self, screen, vx, vy, vw, vh):
        f = self.get_font(18)
        t = f.render(self.message, True, (255, 240, 180))
        pad = 22
        box_w = t.get_width() + pad * 2
        box_h = t.get_height() + 20
        box_x = vx + (vw - box_w) // 2
        box_y = vy + vh - 130

        bg = pygame.Surface((box_w, box_h), pygame.SRCALPHA)
        bg.fill((20, 20, 30, 240))
        screen.blit(bg, (box_x, box_y))
        pygame.draw.rect(screen, (200, 160, 60),
                         (box_x, box_y, box_w, box_h), 2, border_radius=8)
        screen.blit(t, (box_x + pad, box_y + 10))