# src/scenes/npc_hall_scene/npc_hall_scene.py
"""
NPC HALL - Hub de NPCs do jogo.

Cada NPC oferece um serviço ao jogador mediante pagamento em gold:
  - NPC_1: Renomear Pokémon
  - NPC_2: Reaprender movimentos (apenas golpes já aprendidos)

Layout em CARROSSEL: apenas um NPC fica centralizado por vez.
Navegação:
  - Setas laterais (botões na tela)
  - Teclado ← / →
  - Arrastar (swipe) com o mouse
  - Clique num NPC lateral traz ele para o centro

Somente acessível pela tela de seleção de fases.
"""

import pygame

from src.scenes.base_scene import BaseScene
from src.config.paths import SPRITES_PATH
from src.managers.sounds.sound_manager import sound_manager, SoundEffect
from .rename_dialog import RenameDialog
from .relearn_dialog import RelearnDialog


# =========================================================================
# CONFIGURAÇÃO
# =========================================================================
RENAME_COST = 350
RELEARN_COST = 1500

SWIPE_THRESHOLD = 60          # px de arrasto para trocar de NPC
CAROUSEL_LERP = 12.0          # velocidade da animação (maior = mais rápido)
CARD_PAD = 16                 # padding interno p/ superfície temporária


# =========================================================================
# NPC CARD
# =========================================================================
class NpcCard:
    """Card visual de um NPC no hub (com efeito de profundidade do carrossel)."""

    def __init__(self, key, name, title, description, sprite_filename):
        self.key = key
        self.name = name
        self.title = title
        self.description = description

        self.rect = pygame.Rect(0, 0, 0, 0)
        self.is_hovered = False
        self.is_center = False
        self.center_distance = 0.0   # 0 = centro, 1 = um passo afastado
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

    def handle_event(self, event):  # <-- ADICIONA AQUI
        if event.type == pygame.MOUSEMOTION:
            was = self.is_hovered
            self.is_hovered = self.rect.collidepoint(event.pos)
            if self.is_hovered and not was:
                self.target_scale = 1.03
                sound_manager.play_effect(SoundEffect.CLICK, volume=0.2)
            elif not self.is_hovered and was:
                self.target_scale = 1.0
        return None

    def update_position(self, x, y, w, h):
        self.rect = pygame.Rect(x, y, w, h)

    def update(self, dt):
        self.scale += (self.target_scale - self.scale) * 0.15
        if self.is_hovered:
            self._hover_glow = min(1.0, self._hover_glow + dt * 4)
        else:
            self._hover_glow = max(0.0, self._hover_glow - dt * 4)

    # -------- render --------
    def render(self, screen, fonts):
        distance = min(1.0, max(0.0, self.center_distance))

        # Escala combinada: hover * profundidade (cards laterais menores)
        depth_scale = 1.0 - distance * 0.16
        total_scale = self.scale * depth_scale

        final_rect = self.rect.copy()
        if total_scale != 1.0:
            dw = int(self.rect.width * (total_scale - 1))
            dh = int(self.rect.height * (total_scale - 1))
            final_rect = self.rect.inflate(dw, dh)
            final_rect.center = self.rect.center

        # Alpha decrescente conforme se afasta do centro
        alpha = int(255 * (1.0 - distance * 0.6))
        alpha = max(0, min(255, alpha))

        # Superfície temporária para aplicar alpha global
        PAD = CARD_PAD
        temp_w = final_rect.width + PAD * 2
        temp_h = final_rect.height + PAD * 2
        if temp_w <= 0 or temp_h <= 0:
            return

        temp = pygame.Surface((temp_w, temp_h), pygame.SRCALPHA)
        local = pygame.Rect(PAD, PAD, final_rect.width, final_rect.height)

        self._draw_card(temp, local, fonts, distance)

        temp.set_alpha(alpha)
        screen.blit(temp, (final_rect.x - PAD, final_rect.y - PAD))

    def _draw_card(self, surf, rect, fonts, distance):
        # Sombra
        shadow = rect.copy()
        shadow.y += 5
        pygame.draw.rect(surf, (8, 8, 14), shadow, border_radius=14)

        # Fundo / borda
        hovered = self.is_hovered and distance < 0.05
        if hovered:
            bg = (48, 55, 78)
            border = (180, 200, 255)
        else:
            bg = (30, 34, 48)
            border = (75, 85, 115)

        pygame.draw.rect(surf, bg, rect, border_radius=14)
        pygame.draw.rect(surf, border, rect, 3, border_radius=14)

        # Glow de hover
        if self._hover_glow > 0 and distance < 0.05:
            glow = pygame.Surface((rect.width, rect.height), pygame.SRCALPHA)
            pygame.draw.rect(
                glow,
                (140, 180, 255, int(60 * self._hover_glow)),
                glow.get_rect(), border_radius=14, width=5,
            )
            surf.blit(glow, rect)

        pad = 20

        # Sprite
        sprite_area_h = int(rect.height * 0.48)
        sprite_size = min(rect.width - pad * 2, sprite_area_h)
        sprite_size = max(16, sprite_size)
        sprite_y = rect.y + 16

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
            sx = rect.centerx - sprite_size // 2
            circle = pygame.Rect(sx, sprite_y, sprite_size, sprite_size)
            pygame.draw.ellipse(surf, (18, 22, 32), circle)
            pygame.draw.ellipse(surf, (60, 70, 95), circle, 2)
            surf.blit(sprite_scaled, (sx, sprite_y))
        else:
            ph = pygame.Rect(rect.centerx - sprite_size // 2, sprite_y,
                             sprite_size, sprite_size)
            pygame.draw.rect(surf, (60, 60, 80), ph, border_radius=10)
            pygame.draw.rect(surf, (120, 120, 140), ph, 2, border_radius=10)
            f = fonts['placeholder']
            t = f.render("?", True, (200, 200, 220))
            surf.blit(t, t.get_rect(center=ph.center))

        # Nome
        name_y = sprite_y + sprite_size + 12
        name_s = fonts['name'].render(self.name, True, (255, 220, 120))
        surf.blit(name_s, (rect.centerx - name_s.get_width() // 2, name_y))

        # Título / função
        title_y = name_y + name_s.get_height() + 4
        title_s = fonts['title'].render(self.title, True, (200, 210, 235))
        surf.blit(title_s, (rect.centerx - title_s.get_width() // 2, title_y))

        # Divisor
        div_y = title_y + title_s.get_height() + 8
        div_w = int(rect.width * 0.6)
        pygame.draw.line(surf, (75, 85, 115),
                         (rect.centerx - div_w // 2, div_y),
                         (rect.centerx + div_w // 2, div_y), 1)

        # Descrição
        desc_y = div_y + 10
        max_w = rect.width - pad * 2
        lines = self._wrap_text(self.description, fonts['desc'], max_w)
        for line in lines:
            s = fonts['desc'].render(line, True, (170, 180, 205))
            surf.blit(s, (rect.centerx - s.get_width() // 2, desc_y))
            desc_y += s.get_height() + 2

        # Hint
        hint_s = fonts['hint'].render("Clique para interagir", True,
                                      (140, 155, 190))
        hint_y = rect.bottom - hint_s.get_height() - 14
        surf.blit(hint_s, (rect.centerx - hint_s.get_width() // 2, hint_y))

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
    """Hub de NPCs do jogo com navegação em carrossel."""

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
            NpcCard(
                key="trainer_battle",
                name="Mestre de Batalhas",
                title="Arena de Treinadores",
                description=("Desafie treinadores em batalhas de arena! "
                             "1v1, 2v2 e 3v3 disponíveis."),
                sprite_filename="NPC_3.png",
            ),
        ]

        # ---- Estado do carrossel ----
        self.current_index = 0
        self.carousel_pos = 0.0        # posição animada (float)
        self.drag_start_x = None
        self.drag_offset_x = 0

        # Layout (definido em _create_layout)
        self.viewport = (0, 0, 0, 0)
        self.card_w = 0
        self.card_h = 0
        self.card_y = 0
        self.card_spacing = 0

        # Estado
        self.active_dialog = None
        self.layout_initialized = False
        self.last_size = (0, 0)

        # Fonts
        self._fonts = {}

        # Botões
        self.back_button = None
        self.back_hover = False
        self.left_arrow = None
        self.right_arrow = None
        self.left_arrow_hover = False
        self.right_arrow_hover = False

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

        self.viewport = (vx, vy, vw, vh)

        # ---- Botão voltar ----
        back_size = int(min(vw * 0.05, vh * 0.07, 48))
        self.back_button = pygame.Rect(vx + 20, vy + 20, back_size, back_size)

        # ---- Tamanho dos cards (responsivo) ----
        # Largura limitada por largura da tela E por altura (mantém proporção)
        self.card_w = int(min(vw * 0.30, vh * 0.52))
        self.card_h = int(vh * 0.66)
        self.card_y = vy + int(vh * 0.19)
        self.card_spacing = int(self.card_w * 1.15)

        # ---- Setas laterais ----
        arrow_size = int(min(vw * 0.045, vh * 0.06, 52))
        arrow_y = self.card_y + self.card_h // 2 - arrow_size // 2
        self.left_arrow = pygame.Rect(vx + 16, arrow_y, arrow_size, arrow_size)
        self.right_arrow = pygame.Rect(vx + vw - arrow_size - 16, arrow_y,
                                       arrow_size, arrow_size)

        # ---- Fontes responsivas ----
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
            'arrow': pygame.font.Font(None, int(arrow_size * 0.7)),
        }

        self.layout_initialized = True
        self._update_npc_positions()

    def _check_resize(self):
        cur = (self.screen_manager.window_width,
               self.screen_manager.window_height)
        if cur != self.last_size:
            self.last_size = cur
            self.layout_initialized = False
            return True
        return False

    def _update_npc_positions(self):
        """Recalcula posições dos cards conforme carousel_pos (a cada frame)."""
        vx, vy, vw, vh = self.viewport
        center_x = vx + vw // 2

        # Feedback visual do arrasto
        drag_offset = self.drag_offset_x if self.drag_start_x is not None else 0

        for i, npc in enumerate(self.npcs):
            offset = (i - self.carousel_pos) * self.card_spacing + drag_offset
            x = center_x + offset - self.card_w // 2
            npc.update_position(x, self.card_y, self.card_w, self.card_h)

            distance = abs(offset) / max(1, self.card_spacing)
            npc.center_distance = distance
            npc.is_center = (i == self.current_index)

    # ==================================================================
    # NAVEGAÇÃO
    # ==================================================================
    def _navigate(self, direction):
        new_index = self.current_index + direction
        new_index = max(0, min(len(self.npcs) - 1, new_index))
        if new_index != self.current_index:
            self.current_index = new_index
            sound_manager.play_effect(SoundEffect.CLICK, volume=0.2)

    def _go_to(self, index):
        if 0 <= index < len(self.npcs) and index != self.current_index:
            self.current_index = index
            sound_manager.play_effect(SoundEffect.CLICK, volume=0.2)

    # ==================================================================
    # EVENTOS
    # ==================================================================
    def handle_event(self, event):
        self._check_resize()

        # ---- ESC ----
        if event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE:
            if self.active_dialog:
                self.active_dialog.close()
                self.active_dialog = None
                return
            self._go_back()
            return

        # ---- Teclado: setas ----
        if event.type == pygame.KEYDOWN and not self.active_dialog:
            if event.key in (pygame.K_LEFT, pygame.K_a):
                self._navigate(-1)
                return
            if event.key in (pygame.K_RIGHT, pygame.K_d):
                self._navigate(1)
                return

        # ---- Dialog ativo: encaminha tudo ----
        if self.active_dialog:
            result = self.active_dialog.handle_event(event)
            if result == "close":
                self.active_dialog = None
            elif result == "success":
                self.feedback_message = self.active_dialog.success_message
                self.feedback_timer = 2.5
                self.active_dialog = None
            return

        # ---- Hover ----
        if event.type == pygame.MOUSEMOTION:
            if self.back_button:
                self.back_hover = self.back_button.collidepoint(event.pos)
            if self.left_arrow:
                self.left_arrow_hover = self.left_arrow.collidepoint(event.pos)
            if self.right_arrow:
                self.right_arrow_hover = self.right_arrow.collidepoint(event.pos)

            # Hover só no card central
            for i, npc in enumerate(self.npcs):
                if i == self.current_index and self.drag_start_x is None:
                    npc.handle_event(event)
                elif npc.is_hovered:
                    npc.is_hovered = False
                    npc.target_scale = 1.0

            # Arrasto em andamento → feedback visual
            if self.drag_start_x is not None:
                self.drag_offset_x = event.pos[0] - self.drag_start_x
            return

        # ---- Mouse down ----
        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            if self.back_button and self.back_button.collidepoint(event.pos):
                self._go_back()
                return
            if self.left_arrow and self.left_arrow.collidepoint(event.pos):
                self._navigate(-1)
                return
            if self.right_arrow and self.right_arrow.collidepoint(event.pos):
                self._navigate(1)
                return
            # Inicia potencial arrasto
            self.drag_start_x = event.pos[0]
            self.drag_offset_x = 0
            return

        # ---- Mouse up ----
        if event.type == pygame.MOUSEBUTTONUP and event.button == 1:
            if self.drag_start_x is None:
                return
            dx = event.pos[0] - self.drag_start_x
            self.drag_start_x = None
            self.drag_offset_x = 0

            # Swipe?
            if abs(dx) >= SWIPE_THRESHOLD:
                self._navigate(1 if dx < 0 else -1)
                return

            # Clique: identifica o card clicado
            for i, npc in enumerate(self.npcs):
                if npc.rect.collidepoint(event.pos):
                    if i == self.current_index:
                        self._open_dialog(npc.key)
                    else:
                        self._go_to(i)
                    return

    def _open_dialog(self, action):
        sound_manager.play_effect(SoundEffect.CLICK, volume=0.3)
        if action == "rename":
            self.active_dialog = RenameDialog(self.game, RENAME_COST)
        elif action == "relearn":
            self.active_dialog = RelearnDialog(self.game, RELEARN_COST)
        elif action == "trainer_battle":
            from src.scenes.arena_scene.trainer_select_scene import TrainerSelectScene
            self.game.current_scene = TrainerSelectScene(self.game)

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

        # Animação suave do carrossel
        target = float(self.current_index)
        diff = target - self.carousel_pos
        if abs(diff) < 0.001:
            self.carousel_pos = target
        else:
            self.carousel_pos += diff * min(1.0, dt * CAROUSEL_LERP)

        # Reposiciona cards a cada frame (carrossel animado)
        self._update_npc_positions()

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

        vx, vy, vw, vh = self.viewport

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

        # ===== NPCs (do mais distante ao mais central, para sobrepor bem) =====
        ordered = sorted(self.npcs, key=lambda n: -n.center_distance)
        for npc in ordered:
            npc.render(screen, self._fonts)

        # ===== SETAS DE NAVEGAÇÃO =====
        self._render_arrows(screen)

        # ===== BOTÃO VOLTAR =====
        self._render_back_button(screen)

        # ===== GOLD =====
        self._render_gold(screen, vx, vy, vw)

        # ===== INDICADORES (bolinhas) =====
        self._render_indicators(screen, vx, vw, vy, vh)

        # ===== INSTRUÇÕES =====
        inst_s = self._fonts['inst'].render(
            "< > ou arraste para navegar   ·   Clique para interagir   ·   ESC para voltar",
            True, (110, 120, 140))
        screen.blit(inst_s,
                    (vx + (vw - inst_s.get_width()) // 2, vy + vh - 28))

        # ===== FEEDBACK =====
        if self.feedback_timer > 0:
            self._render_feedback(screen, vx, vy, vw, vh)

        # ===== DIALOG =====
        if self.active_dialog:
            self.active_dialog.render(screen)

    # ------------------------------------------------------------------
    def _render_arrows(self, screen):
        if not self.left_arrow or not self.right_arrow:
            return

        at_start = (self.current_index <= 0)
        at_end = (self.current_index >= len(self.npcs) - 1)

        self._draw_arrow(screen, self.left_arrow, self.left_arrow_hover,
                         "<", disabled=at_start)
        self._draw_arrow(screen, self.right_arrow, self.right_arrow_hover,
                         ">", disabled=at_end)

    def _draw_arrow(self, screen, rect, hovered, glyph, disabled=False):
        if disabled:
            bg = (28, 30, 40)
            border = (60, 65, 80)
            txt_col = (90, 95, 115)
        elif hovered:
            bg = (60, 75, 110)
            border = (180, 200, 255)
            txt_col = (255, 255, 255)
        else:
            bg = (38, 44, 62)
            border = (90, 100, 130)
            txt_col = (200, 210, 235)

        pygame.draw.rect(screen, bg, rect, border_radius=10)
        pygame.draw.rect(screen, border, rect, 2, border_radius=10)

        f = self._fonts['arrow']
        t = f.render(glyph, True, txt_col)
        screen.blit(t, t.get_rect(center=rect.center))

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
        screen.blit(s, (box.x + 14, box.y + 6))

    def _render_indicators(self, screen, vx, vw, vy, vh):
        n = len(self.npcs)
        if n <= 1:
            return

        dot_r = 6
        gap = 22
        total_w = n * dot_r * 2 + (n - 1) * gap
        start_x = vx + (vw - total_w) // 2
        y = vy + vh - 60

        for i in range(n):
            cx = start_x + i * (dot_r * 2 + gap) + dot_r
            is_active = (i == self.current_index)
            r = dot_r if is_active else int(dot_r * 0.6)
            color = (255, 220, 120) if is_active else (90, 100, 130)
            pygame.draw.circle(screen, color, (cx, y), r)
            if is_active:
                pygame.draw.circle(screen, (255, 240, 180), (cx, y), r, 1)

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

        for i in range(8):
            rx = (i * 0.13 + 0.05) % 1.0
            ry = (i * 0.21 + 0.08) % 0.5
            x = int(rx * w)
            y = int(ry * h)
            pygame.draw.circle(screen, (110, 130, 180), (x, y), 1 + (i % 2))