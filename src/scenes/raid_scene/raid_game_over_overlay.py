# src/scenes/raid_scene/raid_game_over_overlay.py
"""
Overlay de Game Over exclusivo da RAID.
- NÃO remove gold / felicidade.
- NÃO volta pra seleção de time.
- Botão único: Voltar ao Lobby.
"""
import pygame
import math


# Paleta igual à do RaidScene (consistência visual)
COL_BG          = (16, 18, 30)
COL_PANEL       = (26, 29, 48)
COL_PANEL_DARK  = (20, 22, 38)
COL_BORDER      = (55, 58, 82)
COL_BORDER_HL   = (110, 115, 150)
COL_ACCENT      = (255, 215, 0)
COL_TEXT        = (235, 235, 245)
COL_TEXT_DIM    = (170, 175, 200)
COL_TEXT_MUTED  = (95, 100, 130)
COL_DANGER      = (230, 90, 90)
COL_DANGER_H    = (255, 120, 120)
COL_DANGER_DIM  = (128, 48, 54)


class RaidGameOverOverlay:
    """Overlay mostrado quando a raid falha (todos os pokémons caíram)."""

    def __init__(self, game_scene):
        self.game_scene = game_scene
        self.active = True

        # Botão principal
        self.leave_btn = pygame.Rect(0, 0, 260, 52)
        self._layout()

        # Fonte
        self.font_title = pygame.font.Font(None, 84)
        self.font_sub = pygame.font.Font(None, 30)
        self.font_info = pygame.font.Font(None, 22)
        self.font_btn = pygame.font.Font(None, 30)

        # Animação de entrada
        self.elapsed = 0.0
        self.alpha = 0

    def _layout(self):
        vx = self.game_scene.screen_manager.viewport_x
        vy = self.game_scene.screen_manager.viewport_y
        vw = self.game_scene.screen_manager.viewport_width
        vh = self.game_scene.screen_manager.viewport_height

        cx = vx + vw // 2
        cy = vy + vh // 2

        # Botão fica embaixo do painel
        self.leave_btn.center = (cx, cy + 150)

    # ------------------------------------------------------------------
    # Eventos
    # ------------------------------------------------------------------
    def handle_event(self, event):
        if not self.active:
            return False

        if event.type == pygame.VIDEORESIZE:
            self._layout()
            return False

        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            if self.leave_btn.collidepoint(event.pos):
                self._on_leave_clicked()
                return True

        if event.type == pygame.KEYDOWN:
            if event.key in (pygame.K_RETURN, pygame.K_SPACE, pygame.K_ESCAPE):
                self._on_leave_clicked()
                return True

        return False

    def _on_leave_clicked(self):
        try:
            from src.managers.sounds.sound_manager import sound_manager, SoundEffect
            sound_manager.play_effect(SoundEffect.CLICK)
        except Exception:
            pass
        self.active = False
        self.game_scene._return_to_lobby_from_raid()

    # ------------------------------------------------------------------
    # Update
    # ------------------------------------------------------------------
    def update(self, dt):
        if not self.active:
            return
        self.elapsed += dt
        # Fade-in rápido (0.4s)
        self.alpha = min(255, int((self.elapsed / 0.4) * 255))

    # ------------------------------------------------------------------
    # Render
    # ------------------------------------------------------------------
    def render(self, screen):
        if not self.active:
            return

        sm = self.game_scene.screen_manager
        vx = sm.viewport_x
        vy = sm.viewport_y
        vw = sm.viewport_width
        vh = sm.viewport_height

        # ===== FUNDO ESCURO =====
        overlay = pygame.Surface((vw, vh), pygame.SRCALPHA)
        overlay.fill((0, 0, 0, min(210, self.alpha)))
        screen.blit(overlay, (vx, vy))

        # ===== PAINEL CENTRAL =====
        panel_w = 620
        panel_h = 340
        panel = pygame.Rect(0, 0, panel_w, panel_h)
        panel.center = (vx + vw // 2, vy + vh // 2 - 20)

        # Sombra
        shadow = pygame.Surface((panel_w + 20, panel_h + 20), pygame.SRCALPHA)
        pygame.draw.rect(shadow, (0, 0, 0, 140),
                         shadow.get_rect(), border_radius=22)
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

        # Borda vermelha brilhante
        glow_pulse = 0.5 + 0.5 * math.sin(self.elapsed * 3)
        border_alpha = int(180 + 75 * glow_pulse)
        border_surf = pygame.Surface((panel_w + 8, panel_h + 8), pygame.SRCALPHA)
        pygame.draw.rect(border_surf, (*COL_DANGER, border_alpha),
                         border_surf.get_rect(), 3, border_radius=22)
        screen.blit(border_surf, (panel.x - 4, panel.y - 4))
        pygame.draw.rect(screen, COL_DANGER_DIM, panel, 2, border_radius=20)

        # ===== TÍTULO =====
        cx = panel.centerx
        title = self.font_title.render("RAID FALHOU", True, COL_DANGER)
        title_rect = title.get_rect(center=(cx, panel.y + 72))
        # sombra
        shadow_txt = self.font_title.render("RAID FALHOU", True, (0, 0, 0))
        screen.blit(shadow_txt, (title_rect.x + 3, title_rect.y + 3))
        screen.blit(title, title_rect)

        # Linha decorativa
        pygame.draw.line(screen, COL_DANGER_DIM,
                         (panel.x + 50, panel.y + 118),
                         (panel.right - 50, panel.y + 118), 2)

        # ===== SUBTÍTULO =====
        sub = self.font_sub.render("Sua equipe foi derrotada...", True, COL_TEXT)
        sub_rect = sub.get_rect(center=(cx, panel.y + 152))
        screen.blit(sub, sub_rect)

        # ===== INFORMAÇÕES =====
        info_lines = [
            ("Todos os seus Pokémon caíram em batalha.", COL_TEXT_DIM),
            ("Nenhum ouro ou item foi perdido.", COL_ACCENT),
            ("Você voltará ao lobby da raid.", COL_TEXT_DIM),
        ]
        y = panel.y + 195
        for line, color in info_lines:
            txt = self.font_info.render(line, True, color)
            r = txt.get_rect(center=(cx, y))
            screen.blit(txt, r)
            y += 26

        # ===== BOTÃO VOLTAR AO LOBBY =====
        mouse = pygame.mouse.get_pos()
        hover = self.leave_btn.collidepoint(mouse)
        btn_color = COL_DANGER_H if hover else COL_DANGER
        border_color = COL_ACCENT if hover else COL_DANGER_DIM

        pygame.draw.rect(screen, btn_color, self.leave_btn, border_radius=14)
        pygame.draw.rect(screen, border_color, self.leave_btn, 3, border_radius=14)

        btn_txt = self.font_btn.render("Voltar ao Lobby", True, (255, 255, 255))
        btn_rect = btn_txt.get_rect(center=self.leave_btn.center)
        screen.blit(btn_txt, btn_rect)

        # ===== DICA DE TECLADO =====
        hint = self.font_info.render(
            "Pressione ENTER ou ESC para voltar", True, COL_TEXT_MUTED
        )
        hint_rect = hint.get_rect(center=(cx, self.leave_btn.bottom + 30))
        screen.blit(hint, hint_rect)