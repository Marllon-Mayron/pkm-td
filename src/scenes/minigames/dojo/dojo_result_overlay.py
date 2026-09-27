# src/scenes/minigames/dojo/dojo_result_overlay.py
"""
Overlay de vitória/derrota do Dojo.

Vitória: mostra o Tyrogue premiado (portrait via Pokedex, mesmo estilo
do RaidVictoryOverlay), ouro, XP e aviso "foi para a Box".
Derrota: mensagem simples.
"""
import math
import pygame


# ---- Paleta (espelha RaidVictoryOverlay) ----
COL_PANEL_DARK  = (20, 22, 38)
COL_PANEL       = (26, 29, 48)
COL_BORDER      = (55, 58, 82)
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


class DojoResultOverlay:
    """Overlay de resultado do Dojo."""

    def __init__(self, scene, result, rewards=None, tyrogue=None):
        self.scene = scene
        self.result = result
        self.rewards = rewards or {}
        self.tyrogue = tyrogue
        self.active = True

        # Botão
        self.btn = pygame.Rect(0, 0, 300, 56)
        self._layout()

        # Fontes
        self.font_title = pygame.font.Font(None, 84)
        self.font_sub = pygame.font.Font(None, 30)
        self.font_section = pygame.font.Font(None, 24)
        self.font_info = pygame.font.Font(None, 22)
        self.font_btn = pygame.font.Font(None, 30)
        self.font_small = pygame.font.Font(None, 18)

        # Animação
        self.elapsed = 0.0
        self.alpha = 0

        # Portrait
        self._portrait = None
        self._load_portrait()

    # -----------------------------------------------------------------
    def _layout(self):
        sm = self.scene.screen_manager
        cx = sm.viewport_x + sm.viewport_width // 2
        cy = sm.viewport_y + sm.viewport_height // 2
        self.btn.center = (cx, cy + 230)

    def _load_portrait(self):
        """Carrega o portrait do Tyrogue — igual ao RaidVictoryOverlay."""
        if self.tyrogue is None:
            return
        try:
            from src.data.pokedex import Pokedex
            pokedex = Pokedex()

            # Tenta 'happy', cai pra 'normal'
            portrait = pokedex.get_portrait(
                self.tyrogue.id, "happy", self.tyrogue.is_shiny
            )
            if portrait is None:
                portrait = pokedex.get_portrait(
                    self.tyrogue.id, "normal", self.tyrogue.is_shiny
                )

            if portrait:
                self._portrait = pygame.transform.smoothscale(
                    portrait, (130, 130)
                )
                print("[DOJO_RESULT] Portrait do Tyrogue carregado.")
            else:
                print("[DOJO_RESULT] Portrait não encontrado, "
                      "usando fallback.")
        except Exception as e:
            print(f"[DOJO_RESULT] Erro ao carregar portrait: {e}")

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

    # -----------------------------------------------------------------
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

        # Fundo
        overlay = pygame.Surface((vw, vh), pygame.SRCALPHA)
        overlay.fill((0, 0, 0, min(220, self.alpha)))
        screen.blit(overlay, (vx, vy))

        win = (self.result == "win")
        accent = COL_ACCENT if win else COL_DANGER
        accent_dim = COL_SUCCESS_DIM if win else COL_DANGER_DIM
        accent_hover = COL_SUCCESS_H if win else COL_DANGER_H

        # ---- Painel ----
        panel_w = 720
        panel_h = 540
        panel = pygame.Rect(0, 0, panel_w, panel_h)
        panel.center = (vx + vw // 2, vy + vh // 2 - 20)

        # Sombra
        shadow = pygame.Surface((panel_w + 20, panel_h + 20),
                                pygame.SRCALPHA)
        pygame.draw.rect(shadow, (0, 0, 0, 150), shadow.get_rect(),
                         border_radius=22)
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
        glow_pulse = 0.5 + 0.5 * math.sin(self.elapsed * 3)
        border_alpha = int(200 + 55 * glow_pulse)
        border_surf = pygame.Surface((panel_w + 8, panel_h + 8),
                                     pygame.SRCALPHA)
        pygame.draw.rect(border_surf, (*accent, border_alpha),
                         border_surf.get_rect(), 3, border_radius=22)
        screen.blit(border_surf, (panel.x - 4, panel.y - 4))
        pygame.draw.rect(screen, accent_dim, panel, 2, border_radius=20)

        cx = panel.centerx

        # ---- Título ----
        title_txt = "VITÓRIA NO DOJO!" if win else "DERROTA"
        title = self.font_title.render(title_txt, True, accent)
        title_rect = title.get_rect(center=(cx, panel.y + 60))
        title_sh = self.font_title.render(title_txt, True, (0, 0, 0))
        screen.blit(title_sh, (title_rect.x + 3, title_rect.y + 3))
        screen.blit(title, title_rect)

        # ---- Subtítulo ----
        if win:
            sub_txt = "Você venceu os 5 lutadores do Mestre!"
            sub_color = COL_SUCCESS
        else:
            sub_txt = "Os lutadores do Dojo foram mais fortes..."
            sub_color = COL_TEXT_DIM

        sub = self.font_sub.render(sub_txt, True, sub_color)
        screen.blit(sub, sub.get_rect(center=(cx, panel.y + 105)))

        # Linha
        pygame.draw.line(screen, accent,
                         (panel.x + 50, panel.y + 135),
                         (panel.right - 50, panel.y + 135), 2)

        # =============================================================
        # SEÇÃO: PRÊMIO (só vitória)
        # =============================================================
        y = panel.y + 160

        if win and self.tyrogue is not None:
            section = self.font_section.render(
                "PRÊMIO — TYROGUE", True, COL_ACCENT)
            screen.blit(section, section.get_rect(center=(cx, y)))
            y += 30

            # ---- Portrait com moldura ----
            if self._portrait:
                p_rect = self._portrait.get_rect()
                p_rect.center = (cx, y + 65)

                # Aura dourada pulsante
                aura_size = 160
                aura = pygame.Surface((aura_size, aura_size),
                                      pygame.SRCALPHA)
                pulse = 0.5 + 0.5 * math.sin(self.elapsed * 4)
                a = int(90 + 90 * pulse)
                pygame.draw.circle(
                    aura, (255, 215, 0, a),
                    (aura_size // 2, aura_size // 2),
                    aura_size // 2 - 6)
                screen.blit(
                    aura,
                    (p_rect.centerx - aura_size // 2,
                     p_rect.centery - aura_size // 2))

                # Moldura
                frame = p_rect.inflate(10, 10)
                pygame.draw.rect(screen, COL_PANEL_DARK, frame,
                                 border_radius=10)
                border_c = COL_ACCENT if self.tyrogue.is_shiny \
                    else COL_SUCCESS
                pygame.draw.rect(screen, border_c, frame, 3,
                                 border_radius=10)

                screen.blit(self._portrait, p_rect)
                y += 145
            else:
                y += 100

            # ---- Nome + nível ----
            name_color = COL_ACCENT if self.tyrogue.is_shiny else COL_TEXT
            name_txt = self.font_sub.render(
                f"{self.tyrogue.name}  Lv.{self.tyrogue.level}",
                True, name_color)
            screen.blit(name_txt, name_txt.get_rect(center=(cx, y)))
            y += 26

            # ---- Tipos ----
            try:
                types_txt = " · ".join(t.upper()
                                       for t in self.tyrogue.types)
                types_s = self.font_small.render(
                    types_txt, True, COL_TEXT_DIM)
                screen.blit(types_s, types_s.get_rect(center=(cx, y)))
                y += 24
            except Exception:
                y += 6

            # ---- Destino (sempre box) ----
            dest_txt = self.font_small.render(
                "Enviado para a PC Box", True, COL_TEXT_DIM)
            screen.blit(dest_txt, dest_txt.get_rect(center=(cx, y)))
            y += 24

        elif win:
            # Vitória mas sem tyrogue (não deve acontecer)
            section = self.font_section.render(
                "PRÊMIO", True, COL_ACCENT)
            screen.blit(section, section.get_rect(center=(cx, y)))
            y += 30

        else:
            # Derrota
            info = self.font_info.render(
                "Você pode tentar novamente quando quiser.",
                True, COL_TEXT_DIM)
            screen.blit(info, info.get_rect(center=(cx, y + 60)))

        # =============================================================
        # SEÇÃO: OUTRAS RECOMPENSAS (só vitória)
        # =============================================================
        if win:
            section2 = self.font_section.render(
                "RECOMPENSAS", True, COL_ACCENT)
            screen.blit(section2, section2.get_rect(center=(cx, y)))
            y += 30

            gold = self.rewards.get("money", 0)
            xp = self.rewards.get("xp", 0)

            gold_txt = self.font_info.render(
                f"+{gold} Ouro", True, COL_ACCENT)
            xp_txt = self.font_info.render(
                f"+{xp} XP", True, (100, 180, 255))

            left_x = cx - 120
            right_x = cx + 20
            screen.blit(gold_txt,
                        gold_txt.get_rect(midleft=(left_x, y)))
            screen.blit(xp_txt,
                        xp_txt.get_rect(midleft=(right_x, y)))

        # =============================================================
        # BOTÃO
        # =============================================================
        mouse = pygame.mouse.get_pos()
        hover = self.btn.collidepoint(mouse)

        btn_color = accent_hover if hover else (
            COL_SUCCESS if win else COL_DANGER)
        border_color = COL_ACCENT if hover else accent_dim

        pygame.draw.rect(screen, btn_color, self.btn, border_radius=14)
        pygame.draw.rect(screen, border_color, self.btn, 3,
                         border_radius=14)

        label = "Voltar aos Minigames"
        bt = self.font_btn.render(label, True, (255, 255, 255))
        screen.blit(bt, bt.get_rect(center=self.btn.center))

        # Hint
        hint = self.font_small.render(
            "Pressione ENTER ou ESC para voltar",
            True, COL_TEXT_MUTED)
        screen.blit(hint, hint.get_rect(
            center=(cx, self.btn.bottom + 26)))