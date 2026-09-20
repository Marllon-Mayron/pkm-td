# src/scenes/npc_hall_scene/npc_hall_scene.py
"""
NPC HALL - Hub de NPCs do jogo.

Cada NPC oferece um serviço ao jogador mediante pagamento em gold:
  - NPC_1: Renomear Pokémon
  - NPC_2: Reaprender movimentos (apenas golpes já aprendidos)

Somente acessível pela tela de seleção de fases.
"""

import pygame

from src.scenes.base_scene import BaseScene
from src.config.paths import SPRITES_PATH
from src.managers.sounds.sound_manager import sound_manager, SoundEffect
from .rename_dialog import RenameDialog
from .relearn_dialog import RelearnDialog


# =========================================================================
# CONFIGURAÇÃO DOS NPCs
# =========================================================================
RENAME_COST = 350     # Custo em gold para renomear
RELEARN_COST = 1500    # Custo em gold para reaprender um move


# =========================================================================
# NPC CARD
# =========================================================================
class NpcCard:
    """Card visual de um NPC no hub."""

    def __init__(self, key, name, title, description, sprite_filename):
        self.key = key
        self.name = name
        self.title = title
        self.description = description

        self.rect = pygame.Rect(0, 0, 0, 0)
        self.is_hovered = False
        self.scale = 1.0
        self.target_scale = 1.0
        self._hover_glow = 0.0

        self._sprite = self._load_sprite(sprite_filename)
        self._sprite_cache = {}

    def _load_sprite(self, filename):
        try:
            path = SPRITES_PATH / "characters" / filename
            if path.exists():
                surf = pygame.image.load(str(path)).convert_alpha()
                print(f"[NPC_HALL] Sprite carregado: {path.name} ({surf.get_size()})")
                return surf
            else:
                print(f"[NPC_HALL] Sprite não encontrado: {path}")
        except Exception as e:
            print(f"[NPC_HALL] Erro ao carregar sprite {filename}: {e}")
        return None

    def update_position(self, x, y, w, h):
        self.rect = pygame.Rect(x, y, w, h)

    def update(self, dt):
        self.scale += (self.target_scale - self.scale) * 0.15
        if self.is_hovered:
            self._hover_glow = min(1.0, self._hover_glow + dt * 4)
        else:
            self._hover_glow = max(0.0, self._hover_glow - dt * 4)

    def handle_event(self, event):
        if event.type == pygame.MOUSEMOTION:
            was = self.is_hovered
            self.is_hovered = self.rect.collidepoint(event.pos)
            if self.is_hovered and not was:
                self.target_scale = 1.03
                sound_manager.play_effect(SoundEffect.CLICK, volume=0.2)
            elif not self.is_hovered and was:
                self.target_scale = 1.0
        elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            if self.is_hovered:
                return self.key
        return None

    def render(self, screen, fonts):
        # Escala
        scaled_rect = self.rect.copy()
        if self.scale != 1.0:
            wo = int(self.rect.width * (self.scale - 1)) // 2
            ho = int(self.rect.height * (self.scale - 1)) // 2
            scaled_rect = self.rect.inflate(wo * 2, ho * 2)
            scaled_rect.center = self.rect.center

        # Sombra
        shadow = scaled_rect.copy()
        shadow.y += 5
        pygame.draw.rect(screen, (8, 8, 14), shadow, border_radius=14)

        # Fundo
        if self.is_hovered:
            bg = (48, 55, 78)
            border = (180, 200, 255)
        else:
            bg = (30, 34, 48)
            border = (75, 85, 115)

        pygame.draw.rect(screen, bg, scaled_rect, border_radius=14)
        pygame.draw.rect(screen, border, scaled_rect, 3, border_radius=14)

        # Glow
        if self._hover_glow > 0:
            glow = pygame.Surface((scaled_rect.width, scaled_rect.height),
                                   pygame.SRCALPHA)
            pygame.draw.rect(glow,
                             (140, 180, 255, int(60 * self._hover_glow)),
                             glow.get_rect(), border_radius=14, width=5)
            screen.blit(glow, scaled_rect)

        pad = 20

        # Sprite
        sprite_area_h = int(scaled_rect.height * 0.48)
        sprite_size = min(scaled_rect.width - pad * 2, sprite_area_h)
        sprite_y = scaled_rect.y + 16

        if self._sprite:
            key = sprite_size
            if key not in self._sprite_cache:
                try:
                    self._sprite_cache[key] = pygame.transform.smoothscale(
                        self._sprite, (sprite_size, sprite_size))
                except Exception:
                    self._sprite_cache[key] = pygame.transform.scale(
                        self._sprite, (sprite_size, sprite_size))
            sprite_scaled = self._sprite_cache[key]
            sx = scaled_rect.centerx - sprite_size // 2
            # Círculo de fundo
            circle = pygame.Rect(sx, sprite_y, sprite_size, sprite_size)
            pygame.draw.ellipse(screen, (18, 22, 32), circle)
            pygame.draw.ellipse(screen, (60, 70, 95), circle, 2)
            screen.blit(sprite_scaled, (sx, sprite_y))
        else:
            ph = pygame.Rect(scaled_rect.centerx - sprite_size // 2,
                             sprite_y, sprite_size, sprite_size)
            pygame.draw.rect(screen, (60, 60, 80), ph, border_radius=10)
            pygame.draw.rect(screen, (120, 120, 140), ph, 2, border_radius=10)
            f = fonts['placeholder']
            t = f.render("?", True, (200, 200, 220))
            screen.blit(t, t.get_rect(center=ph.center))

        # Nome
        name_y = sprite_y + sprite_size + 12
        name_s = fonts['name'].render(self.name, True, (255, 220, 120))
        screen.blit(name_s, (scaled_rect.centerx - name_s.get_width() // 2, name_y))

        # Título / função
        title_y = name_y + name_s.get_height() + 4
        title_s = fonts['title'].render(self.title, True, (200, 210, 235))
        screen.blit(title_s, (scaled_rect.centerx - title_s.get_width() // 2, title_y))

        # Divisor
        div_y = title_y + title_s.get_height() + 8
        div_w = int(scaled_rect.width * 0.6)
        pygame.draw.line(screen, (75, 85, 115),
                         (scaled_rect.centerx - div_w // 2, div_y),
                         (scaled_rect.centerx + div_w // 2, div_y), 1)

        # Descrição
        desc_y = div_y + 10
        max_w = scaled_rect.width - pad * 2
        lines = self._wrap_text(self.description, fonts['desc'], max_w)
        for line in lines:
            s = fonts['desc'].render(line, True, (170, 180, 205))
            screen.blit(s, (scaled_rect.centerx - s.get_width() // 2, desc_y))
            desc_y += s.get_height() + 2

        # Hint
        hint_s = fonts['hint'].render("Clique para interagir", True,
                                       (140, 155, 190))
        hint_y = scaled_rect.bottom - hint_s.get_height() - 14
        screen.blit(hint_s, (scaled_rect.centerx - hint_s.get_width() // 2,
                              hint_y))

    def _wrap_text(self, text, font, max_w):
        words = text.split(' ')
        lines, cur = [], ""
        for w in words:
            test = (cur + " " + w).strip()
            if font.size(test)[0] <= max_w:
                cur = test
            else:
                if cur:
                    lines.append(cur)
                cur = w
        if cur:
            lines.append(cur)
        return lines


# =========================================================================
# CENA PRINCIPAL
# =========================================================================
class NpcHallScene(BaseScene):
    """Hub de NPCs do jogo."""

    def __init__(self, game):
        super().__init__(game)
        self.player = game.player

        # NPCs
        self.npcs = [
            NpcCard(
                key="rename",
                name="Mestre Onomástico",
                title="Renomeador de Pokémon",
                description=(f"Posso dar um novo apelido ao seu Pokémon. "
                             f"O serviço custa {RENAME_COST} moedas de ouro."),
                sprite_filename="NPC_1.png",
            ),
            NpcCard(
                key="relearn",
                name="Sábio dos Golpes",
                title="Mestre de Movimentos",
                description=(f"Ensino novamente golpes que seu Pokémon já "
                             f"aprendeu. Custa {RELEARN_COST} moedas de ouro."),
                sprite_filename="NPC_2.png",
            ),
        ]

        # Estado
        self.active_dialog = None
        self.layout_initialized = False
        self.last_size = (0, 0)

        # Fonts
        self._fonts = {}

        # Botão voltar
        self.back_button = None
        self.back_hover = False

        # Feedback
        self.feedback_message = ""
        self.feedback_timer = 0.0

    # ==================================================================
    # LAYOUT / FONTES
    # ==================================================================
    def _get_font(self, size):
        size = max(10, int(size))
        if size not in self._fonts:
            self._fonts[size] = pygame.font.Font(None, size)
        return self._fonts[size]

    def _create_layout(self):
        vx = self.screen_manager.viewport_x
        vy = self.screen_manager.viewport_y
        vw = self.screen_manager.viewport_width
        vh = self.screen_manager.viewport_height

        # Back button
        back_size = int(min(vw * 0.05, vh * 0.07, 48))
        self.back_button = pygame.Rect(vx + 20, vy + 20, back_size, back_size)

        # NPC cards
        card_w = int(vw * 0.28)
        card_h = int(vh * 0.66)
        gap = int(vw * 0.04)
        total_w = card_w * 2 + gap
        start_x = vx + (vw - total_w) // 2
        card_y = vy + int(vh * 0.19)

        for i, npc in enumerate(self.npcs):
            x = start_x + i * (card_w + gap)
            npc.update_position(x, card_y, card_w, card_h)

        # Fontes responsivas
        base = vh * 0.024
        self._fonts = {
            'title': pygame.font.Font(None, int(base * 2.2)),
            'subtitle': pygame.font.Font(None, int(base * 1.0)),
            'name': pygame.font.Font(None, int(base * 1.25)),
            'placeholder': pygame.font.Font(None, int(base * 3.0)),
            'desc': pygame.font.Font(None, int(base * 0.85)),
            'hint': pygame.font.Font(None, int(base * 0.75)),
            'gold': pygame.font.Font(None, int(base * 1.1)),
            'feedback': pygame.font.Font(None, int(base * 1.0)),
            'inst': pygame.font.Font(None, int(base * 0.75)),
        }

        self.layout_initialized = True

    def _check_resize(self):
        cur = (self.screen_manager.window_width,
               self.screen_manager.window_height)
        if cur != self.last_size:
            self.last_size = cur
            self.layout_initialized = False
            return True
        return False

    # ==================================================================
    # EVENTOS
    # ==================================================================
    def handle_event(self, event):
        self._check_resize()

        # ESC
        if event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE:
            if self.active_dialog:
                self.active_dialog.close()
                self.active_dialog = None
                return
            self._go_back()
            return

        # Dialog ativo → encaminha tudo
        if self.active_dialog:
            result = self.active_dialog.handle_event(event)
            if result == "close":
                self.active_dialog = None
            elif result == "success":
                self.feedback_message = self.active_dialog.success_message
                self.feedback_timer = 2.5
                self.active_dialog = None
            return

        # Hover
        if event.type == pygame.MOUSEMOTION:
            if self.back_button:
                self.back_hover = self.back_button.collidepoint(event.pos)
            for npc in self.npcs:
                npc.handle_event(event)

        # Click
        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            if self.back_button and self.back_button.collidepoint(event.pos):
                self._go_back()
                return

            for npc in self.npcs:
                action = npc.handle_event(event)
                if action:
                    self._open_dialog(action)
                    return

    def _open_dialog(self, action):
        sound_manager.play_effect(SoundEffect.CLICK, volume=0.3)
        if action == "rename":
            self.active_dialog = RenameDialog(self.game, RENAME_COST)
        elif action == "relearn":
            self.active_dialog = RelearnDialog(self.game, RELEARN_COST)

    def _go_back(self):
        sound_manager.play_effect(SoundEffect.CLICK, volume=0.3)
        from src.scenes.phase_selector.phase_select_scene import PhaseSelectScene
        self.game.current_scene = PhaseSelectScene(self.game)

    # ==================================================================
    # UPDATE
    # ==================================================================
    def fixed_update(self, dt):
        if not self.layout_initialized:
            self._create_layout()

        for npc in self.npcs:
            npc.update(dt)

        if self.feedback_timer > 0:
            self.feedback_timer = max(0.0, self.feedback_timer - dt)

        if self.active_dialog:
            self.active_dialog.fixed_update(dt)

    # ==================================================================
    # RENDER
    # ==================================================================
    def render(self, screen):
        self._draw_background(screen)

        if not self.layout_initialized:
            self._create_layout()

        vx = self.screen_manager.viewport_x
        vy = self.screen_manager.viewport_y
        vw = self.screen_manager.viewport_width
        vh = self.screen_manager.viewport_height

        # ===== TÍTULO =====
        title_s = self._fonts['title'].render("NPC HALL", True, (255, 220, 120))
        screen.blit(title_s, (vx + (vw - title_s.get_width()) // 2, vy + 20))

        subtitle_s = self._fonts['subtitle'].render(
            "Bem-vindo ao Salão dos Mestres — escolha com quem deseja falar",
            True, (180, 190, 210))
        screen.blit(subtitle_s,
                    (vx + (vw - subtitle_s.get_width()) // 2,
                     vy + 20 + title_s.get_height() + 4))

        # Linha decorativa
        line_w = int(vw * 0.4)
        line_y = vy + 20 + title_s.get_height() + subtitle_s.get_height() + 16
        pygame.draw.line(screen, (100, 85, 55),
                         (vx + (vw - line_w) // 2, line_y),
                         (vx + (vw + line_w) // 2, line_y), 2)

        # ===== NPCs =====
        for npc in self.npcs:
            npc.render(screen, self._fonts)

        # ===== BOTÃO VOLTAR =====
        self._render_back_button(screen)

        # ===== GOLD =====
        self._render_gold(screen, vx, vy, vw)

        # ===== INSTRUÇÕES =====
        inst_s = self._fonts['inst'].render(
            "Clique em um NPC para interagir   ·   ESC para voltar",
            True, (110, 120, 140))
        screen.blit(inst_s,
                    (vx + (vw - inst_s.get_width()) // 2, vy + vh - 28))

        # ===== FEEDBACK =====
        if self.feedback_timer > 0:
            self._render_feedback(screen, vx, vy, vw, vh)

        # ===== DIALOG =====
        if self.active_dialog:
            self.active_dialog.render(screen)

    def _render_back_button(self, screen):
        if not self.back_button:
            return
        bg = (70, 70, 90) if self.back_hover else (45, 45, 60)
        border = (170, 170, 200) if self.back_hover else (90, 90, 110)
        pygame.draw.rect(screen, bg, self.back_button, border_radius=8)
        pygame.draw.rect(screen, border, self.back_button, 2, border_radius=8)
        f = self._get_font(int(self.back_button.height * 0.6))
        t = f.render("<", True, (240, 240, 250))
        screen.blit(t, t.get_rect(center=self.back_button.center))

    def _render_gold(self, screen, vx, vy, vw):
        money = getattr(self.player, 'money', 0)
        text = f"{money} G"
        s = self._fonts['gold'].render(text, True, (255, 220, 120))
        box = pygame.Rect(vx + vw - s.get_width() - 60, vy + 20,
                          s.get_width() + 40, s.get_height() + 14)
        pygame.draw.rect(screen, (40, 35, 25), box, border_radius=8)
        pygame.draw.rect(screen, (180, 150, 80), box, 2, border_radius=8)

        coin_f = self._fonts['gold']
        coin = coin_f.render("G", True, (255, 215, 0))
        screen.blit(s, (box.x + 14, box.y + 6))

    def _render_feedback(self, screen, vx, vy, vw, vh):
        f = self._fonts['feedback']
        s = f.render(self.feedback_message, True, (255, 255, 255))
        box = pygame.Rect(vx + (vw - s.get_width() - 48) // 2,
                          vy + vh - 110,
                          s.get_width() + 48, s.get_height() + 22)
        pygame.draw.rect(screen, (28, 60, 34), box, border_radius=10)
        pygame.draw.rect(screen, (90, 200, 90), box, 2, border_radius=10)
        screen.blit(s, (box.x + 24, box.y + 11))

    def _draw_background(self, screen):
        w = self.screen_manager.window_width
        h = self.screen_manager.window_height
        for i in range(h):
            t = i / h
            r = int(15 + t * 20)
            g = int(18 + t * 22)
            b = int(30 + t * 32)
            pygame.draw.line(screen, (r, g, b), (0, i), (w, i))

        # Estrelas
        for i in range(8):
            rx = (i * 0.13 + 0.05) % 1.0
            ry = (i * 0.21 + 0.08) % 0.5
            x = int(rx * w)
            y = int(ry * h)
            pygame.draw.circle(screen, (110, 130, 180), (x, y), 1 + (i % 2))