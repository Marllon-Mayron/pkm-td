# src/scenes/arena_scene/arena_result_overlay.py
"""Overlay de vitória/derrota da arena."""
import pygame
import math


class ArenaResultOverlay:
    def __init__(self, scene, result, rewards=None):
        """
        result: "win" | "lose"
        rewards: {"money": int, "xp": int, "trainer_name": str}
        """
        self.scene = scene
        self.result = result
        self.rewards = rewards or {}
        self.active = True

        self.btn = pygame.Rect(0, 0, 260, 52)
        self._layout()

        self.font_title = pygame.font.Font(None, 84)
        self.font_sub = pygame.font.Font(None, 30)
        self.font_info = pygame.font.Font(None, 22)
        self.font_btn = pygame.font.Font(None, 30)

        self.elapsed = 0.0
        self.alpha = 0

    def _layout(self):
        sm = self.scene.screen_manager
        cx = sm.viewport_x + sm.viewport_width // 2
        cy = sm.viewport_y + sm.viewport_height // 2
        self.btn.center = (cx, cy + 140)

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
        self.active = False
        self.scene._finish_arena_battle()

    def update(self, dt):
        if not self.active:
            return
        self.elapsed += dt
        self.alpha = min(255, int((self.elapsed / 0.4) * 255))

    def render(self, screen):
        if not self.active:
            return

        sm = self.scene.screen_manager
        vx, vy = sm.viewport_x, sm.viewport_y
        vw, vh = sm.viewport_width, sm.viewport_height

        overlay = pygame.Surface((vw, vh), pygame.SRCALPHA)
        overlay.fill((0, 0, 0, min(210, self.alpha)))
        screen.blit(overlay, (vx, vy))

        win = (self.result == "win")
        accent = (255, 215, 0) if win else (230, 90, 90)
        accent_dim = (128, 90, 20) if win else (128, 48, 54)

        panel_w, panel_h = 640, 360
        panel = pygame.Rect(0, 0, panel_w, panel_h)
        panel.center = (vx + vw // 2, vy + vh // 2 - 20)

        pygame.draw.rect(screen, (26, 29, 48), panel, border_radius=20)
        glow = 0.5 + 0.5 * math.sin(self.elapsed * 3)
        border_alpha = int(180 + 75 * glow)
        border_surf = pygame.Surface((panel_w + 8, panel_h + 8), pygame.SRCALPHA)
        pygame.draw.rect(border_surf, (*accent, border_alpha),
                         border_surf.get_rect(), 3, border_radius=22)
        screen.blit(border_surf, (panel.x - 4, panel.y - 4))
        pygame.draw.rect(screen, accent_dim, panel, 2, border_radius=20)

        cx = panel.centerx
        title = "VITÓRIA!" if win else "DERROTA"
        t = self.font_title.render(title, True, accent)
        t_sh = self.font_title.render(title, True, (0, 0, 0))
        tr = t.get_rect(center=(cx, panel.y + 80))
        screen.blit(t_sh, (tr.x + 3, tr.y + 3))
        screen.blit(t, tr)

        pygame.draw.line(screen, accent_dim,
                         (panel.x + 50, panel.y + 130),
                         (panel.right - 50, panel.y + 130), 2)

        if win:
            sub_txt = f"Você derrotou {self.rewards.get('trainer_name', 'o oponente')}!"
            sub_color = (235, 235, 245)
        else:
            sub_txt = "Sua equipe foi derrotada..."
            sub_color = (200, 200, 210)

        sub = self.font_sub.render(sub_txt, True, sub_color)
        screen.blit(sub, sub.get_rect(center=(cx, panel.y + 165)))

        # Recompensas (vitória) / Penalidade (derrota)
        y = panel.y + 210
        gold = self.rewards.get("money", 0)
        xp = self.rewards.get("xp", 0)

        if win:
            info = self.font_info.render(
                f"+{gold} Ouro    ·    +{xp} XP", True, (255, 215, 0))
            screen.blit(info, info.get_rect(center=(cx, y)))
        else:
            if gold > 0 or xp > 0:
                info = self.font_info.render(
                    f"-{gold} Ouro    ·    -{xp} XP", True, (230, 90, 90))
                screen.blit(info, info.get_rect(center=(cx, y)))

                warn = self.font_info.render(
                    "Você perdeu o equivalente ao que ganharia.",
                    True, (160, 165, 190))
                screen.blit(warn, warn.get_rect(center=(cx, y + 26)))
            else:
                info = self.font_info.render(
                    "Nenhuma penalidade — apenas tente novamente!",
                    True, (170, 175, 200))
                screen.blit(info, info.get_rect(center=(cx, y)))

        # Botão
        mouse = pygame.mouse.get_pos()
        hover = self.btn.collidepoint(mouse)
        btn_color = (80, 180, 100) if win else (180, 80, 90)
        if hover:
            btn_color = (110, 220, 130) if win else (220, 110, 120)

        pygame.draw.rect(screen, btn_color, self.btn, border_radius=14)
        pygame.draw.rect(screen, accent, self.btn, 3, border_radius=14)

        label = "Voltar ao NPC Hall"
        bt = self.font_btn.render(label, True, (255, 255, 255))
        screen.blit(bt, bt.get_rect(center=self.btn.center))