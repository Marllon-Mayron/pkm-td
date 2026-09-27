# src/scenes/minigames/desafios/desafios_result_overlay.py
"""Overlay de vitória/derrota do minigame Desafios (Snorlax)."""
import math
import pygame


COL_PANEL_DARK  = (20, 22, 38)
COL_PANEL       = (26, 29, 48)
COL_ACCENT      = (255, 215, 0)
COL_TEXT        = (235, 235, 245)
COL_TEXT_DIM    = (170, 175, 200)
COL_TEXT_MUTED  = (95, 100, 130)
COL_SUCCESS     = (105, 220, 130)
COL_SUCCESS_H   = (140, 255, 165)
COL_SUCCESS_DIM = (60, 130, 80)
COL_DANGER      = (230, 90, 90)
COL_DANGER_H    = (255, 120, 120)
COL_DANGER_DIM  = (128, 48, 54)


class DesafiosResultOverlay:
    def __init__(self, scene, result, rewards=None):
        self.scene = scene
        self.result = result
        self.rewards = rewards or {}
        self.active = True

        self.btn = pygame.Rect(0, 0, 300, 56)
        self._layout()

        self.font_title = pygame.font.Font(None, 84)
        self.font_sub = pygame.font.Font(None, 30)
        self.font_section = pygame.font.Font(None, 24)
        self.font_info = pygame.font.Font(None, 22)
        self.font_btn = pygame.font.Font(None, 30)
        self.font_small = pygame.font.Font(None, 18)

        self.elapsed = 0.0
        self.alpha = 0

        # Portrait do Snorlax
        self._portrait = None
        self._load_portrait()

    def _layout(self):
        sm = self.scene.screen_manager
        cx = sm.viewport_x + sm.viewport_width // 2
        cy = sm.viewport_y + sm.viewport_height // 2
        self.btn.center = (cx, cy + 200)

    def _load_portrait(self):
        try:
            from src.data.pokedex import Pokedex
            pdx = Pokedex()
            portrait = pdx.get_portrait(143, "normal", False)
            if portrait:
                self._portrait = pygame.transform.smoothscale(portrait, (120, 120))
        except Exception as e:
            print(f"[DESAFIOS_RESULT] Erro ao carregar portrait: {e}")

    # -----------------------------------------------------------------
    def handle_event(self, event):
        if not self.active:
            return False
        if event.type == pygame.VIDEORESIZE:
            self._layout()
            return False
        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            if self.btn.collidepoint(event.pos):
                self._close()
                return True
        if event.type == pygame.KEYDOWN:
            if event.key in (pygame.K_RETURN, pygame.K_SPACE, pygame.K_ESCAPE):
                self._close()
                return True
        return False

    def _close(self):
        try:
            from src.managers.sounds.sound_manager import sound_manager, SoundEffect
            sound_manager.play_effect(SoundEffect.CLICK)
        except Exception:
            pass
        self.active = False
        self.scene._finish_arena_battle()

    def update(self, dt):
        if not self.active:
            return
        self.elapsed += dt
        self.alpha = min(255, int((self.elapsed / 0.4) * 255))

    # -----------------------------------------------------------------
    def render(self, screen):
        if not self.active:
            return

        sm = self.scene.screen_manager
        vx, vy = sm.viewport_x, sm.viewport_y
        vw, vh = sm.viewport_width, sm.viewport_height

        overlay = pygame.Surface((vw, vh), pygame.SRCALPHA)
        overlay.fill((0, 0, 0, min(220, self.alpha)))
        screen.blit(overlay, (vx, vy))

        win = (self.result == "win")
        accent = COL_ACCENT if win else COL_DANGER
        accent_dim = COL_SUCCESS_DIM if win else COL_DANGER_DIM

        panel_w, panel_h = 720, 500
        panel = pygame.Rect(0, 0, panel_w, panel_h)
        panel.center = (vx + vw // 2, vy + vh // 2 - 20)

        # Sombra
        shadow = pygame.Surface((panel_w + 20, panel_h + 20), pygame.SRCALPHA)
        pygame.draw.rect(shadow, (0, 0, 0, 150), shadow.get_rect(), border_radius=22)
        screen.blit(shadow, (panel.x - 10, panel.y - 6))

        # Fundo gradiente
        bg = pygame.Surface((panel_w, panel_h), pygame.SRCALPHA)
        for i in range(panel_h):
            t = i / panel_h
            r = int(COL_PANEL_DARK[0] * (1 - t) + COL_PANEL[0] * t)
            g = int(COL_PANEL_DARK[1] * (1 - t) + COL_PANEL[1] * t)
            b = int(COL_PANEL_DARK[2] * (1 - t) + COL_PANEL[2] * t)
            bg.fill((r, g, b, 245), (0, i, panel_w, 1))
        screen.blit(bg, panel)

        # Borda com pulso
        pulse = 0.5 + 0.5 * math.sin(self.elapsed * 3)
        border_a = int(200 + 55 * pulse)
        border_surf = pygame.Surface((panel_w + 8, panel_h + 8), pygame.SRCALPHA)
        pygame.draw.rect(border_surf, (*accent, border_a),
                         border_surf.get_rect(), 3, border_radius=22)
        screen.blit(border_surf, (panel.x - 4, panel.y - 4))
        pygame.draw.rect(screen, accent_dim, panel, 2, border_radius=20)

        cx = panel.centerx

        # Título
        title_txt = "SNORLAX DERROTADO!" if win else "DESAFIO FALHOU"
        t = self.font_title.render(title_txt, True, accent)
        t_sh = self.font_title.render(title_txt, True, (0, 0, 0))
        tr = t.get_rect(center=(cx, panel.y + 65))
        screen.blit(t_sh, (tr.x + 3, tr.y + 3))
        screen.blit(t, tr)

        pygame.draw.line(screen, accent_dim,
                         (panel.x + 50, panel.y + 120),
                         (panel.right - 50, panel.y + 120), 2)

        # Subtítulo
        sub_txt = "Você venceu o Snorlax!" if win else "O Snorlax foi mais forte..."
        sub_color = COL_SUCCESS if win else COL_TEXT_DIM
        sub = self.font_sub.render(sub_txt, True, sub_color)
        screen.blit(sub, sub.get_rect(center=(cx, panel.y + 150)))

        # Portrait do Snorlax
        y = panel.y + 200
        if self._portrait:
            pr = self._portrait.get_rect()
            pr.center = (cx, y + 55)
            frame = pr.inflate(10, 10)
            pygame.draw.rect(screen, COL_PANEL_DARK, frame, border_radius=10)
            pygame.draw.rect(screen, accent if win else COL_DANGER_DIM,
                             frame, 3, border_radius=10)
            screen.blit(self._portrait, pr)
            y += 140

        # Recompensas
        if win:
            section = self.font_section.render("RECOMPENSAS", True, COL_ACCENT)
            screen.blit(section, section.get_rect(center=(cx, y)))
            y += 30

            gold = self.rewards.get("money", 0)
            xp = self.rewards.get("xp", 0)

            gold_txt = self.font_info.render(f"+{gold} Ouro", True, COL_ACCENT)
            xp_txt = self.font_info.render(f"+{xp} XP", True, (100, 180, 255))

            left_x = cx - 120
            right_x = cx + 20
            screen.blit(gold_txt, gold_txt.get_rect(midleft=(left_x, y)))
            screen.blit(xp_txt, xp_txt.get_rect(midleft=(right_x, y)))
        else:
            info = self.font_info.render(
                "Você pode tentar novamente quando quiser.",
                True, COL_TEXT_DIM)
            screen.blit(info, info.get_rect(center=(cx, y + 40)))

        # Botão
        mouse = pygame.mouse.get_pos()
        hover = self.btn.collidepoint(mouse)
        btn_color = (COL_SUCCESS_H if hover else COL_SUCCESS) if win \
            else (COL_DANGER_H if hover else COL_DANGER)
        border_color = COL_ACCENT if hover else accent_dim

        pygame.draw.rect(screen, btn_color, self.btn, border_radius=14)
        pygame.draw.rect(screen, border_color, self.btn, 3, border_radius=14)

        label = "Voltar aos Minigames"
        bt = self.font_btn.render(label, True, (255, 255, 255))
        screen.blit(bt, bt.get_rect(center=self.btn.center))

        hint = self.font_small.render(
            "Pressione ENTER ou ESC para voltar",
            True, COL_TEXT_MUTED)
        screen.blit(hint, hint.get_rect(center=(cx, self.btn.bottom + 26)))