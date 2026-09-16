# src/scenes/raid_scene/raid_victory_overlay.py
"""
Overlay de vitória da RAID.
Mostra o lendário ganho, ouro, XP e itens.
"""
import pygame
import math

# Paleta
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
COL_GOLD        = (255, 215, 0)
COL_XP          = (100, 180, 255)


class RaidVictoryOverlay:
    """Overlay de vitória da raid com preview das recompensas."""

    def __init__(self, game_scene, rewards):
        """
        rewards: {
            "gold": int,
            "xp": int,
            "items": [item_id, ...],
            "legendary": {
                "id": int,
                "name": str,
                "level": int,
                "is_shiny": bool,
                "destination": "team" | "box",
            } or None,
        }
        """
        self.game_scene = game_scene
        self.rewards = rewards or {}
        self.active = True

        # Botão
        self.leave_btn = pygame.Rect(0, 0, 280, 54)
        self._layout()

        # Fontes
        self.font_title = pygame.font.Font(None, 72)
        self.font_sub = pygame.font.Font(None, 30)
        self.font_section = pygame.font.Font(None, 24)
        self.font_info = pygame.font.Font(None, 22)
        self.font_btn = pygame.font.Font(None, 30)
        self.font_small = pygame.font.Font(None, 18)

        # Animação
        self.elapsed = 0.0
        self.alpha = 0

        # Cache de sprites
        self._legendary_portrait = None
        self._item_sprites = {}

        self._load_sprites()

    def _layout(self):
        vx = self.game_scene.screen_manager.viewport_x
        vy = self.game_scene.screen_manager.viewport_y
        vw = self.game_scene.screen_manager.viewport_width
        vh = self.game_scene.screen_manager.viewport_height

        cx = vx + vw // 2
        cy = vy + vh // 2

        self.leave_btn.center = (cx, cy + 210)

    def _load_sprites(self):
        """Carrega o portrait do lendário e os sprites dos itens."""
        # Portrait do lendário
        legendary = self.rewards.get("legendary")
        if legendary:
            try:
                from src.data.pokedex import Pokedex
                pokedex = Pokedex()
                portrait = pokedex.get_portrait(
                    legendary["id"], "happy", legendary.get("is_shiny", False)
                )
                if portrait is None:
                    portrait = pokedex.get_portrait(
                        legendary["id"], "normal", legendary.get("is_shiny", False)
                    )
                if portrait:
                    self._legendary_portrait = pygame.transform.smoothscale(
                        portrait, (110, 110)
                    )
            except Exception as e:
                print(f"[RAID_VICTORY] Erro ao carregar portrait: {e}")

        # Sprites dos itens
        item_ids = self.rewards.get("items", [])
        if item_ids:
            try:
                from src.data.item_bag_catalog import item_bag_catalog
                for iid in set(item_ids):
                    sprite = item_bag_catalog.get_sprite(iid, scaled=True)
                    if sprite:
                        self._item_sprites[iid] = pygame.transform.smoothscale(
                            sprite, (28, 28)
                        )
            except Exception as e:
                print(f"[RAID_VICTORY] Erro ao carregar sprites de itens: {e}")

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
    def update(self, dt):
        if not self.active:
            return
        self.elapsed += dt
        self.alpha = min(255, int((self.elapsed / 0.4) * 255))

    # ------------------------------------------------------------------
    def render(self, screen):
        if not self.active:
            return

        sm = self.game_scene.screen_manager
        vx = sm.viewport_x
        vy = sm.viewport_y
        vw = sm.viewport_width
        vh = sm.viewport_height

        # Fundo escuro
        overlay = pygame.Surface((vw, vh), pygame.SRCALPHA)
        overlay.fill((0, 0, 0, min(215, self.alpha)))
        screen.blit(overlay, (vx, vy))

        # Painel
        panel_w = 720
        panel_h = 500
        panel = pygame.Rect(0, 0, panel_w, panel_h)
        panel.center = (vx + vw // 2, vy + vh // 2 - 30)

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

        # Borda dourada com pulso
        glow_pulse = 0.5 + 0.5 * math.sin(self.elapsed * 3)
        border_alpha = int(200 + 55 * glow_pulse)
        border_surf = pygame.Surface((panel_w + 8, panel_h + 8), pygame.SRCALPHA)
        pygame.draw.rect(border_surf, (*COL_ACCENT, border_alpha),
                         border_surf.get_rect(), 3, border_radius=22)
        screen.blit(border_surf, (panel.x - 4, panel.y - 4))
        pygame.draw.rect(screen, COL_SUCCESS_DIM, panel, 2, border_radius=20)

        cx = panel.centerx

        # Título
        title = self.font_title.render("RAID COMPLETA!", True, COL_ACCENT)
        title_rect = title.get_rect(center=(cx, panel.y + 60))
        shadow_txt = self.font_title.render("RAID COMPLETA!", True, (0, 0, 0))
        screen.blit(shadow_txt, (title_rect.x + 3, title_rect.y + 3))
        screen.blit(title, title_rect)

        # Subtítulo
        sub = self.font_sub.render("Você derrotou o lendário!", True, COL_SUCCESS)
        sub_rect = sub.get_rect(center=(cx, panel.y + 105))
        screen.blit(sub, sub_rect)

        # Linha
        pygame.draw.line(screen, COL_ACCENT,
                         (panel.x + 50, panel.y + 135),
                         (panel.right - 50, panel.y + 135), 2)

        # ===== SEÇÃO: LENDÁRIO =====
        y = panel.y + 160
        section = self.font_section.render("LENDÁRIO CAPTURADO", True, COL_ACCENT)
        screen.blit(section, section.get_rect(center=(cx, y)))
        y += 30

        legendary = self.rewards.get("legendary")
        if legendary:
            # Portrait
            if self._legendary_portrait:
                portrait_rect = self._legendary_portrait.get_rect()
                portrait_rect.center = (cx, y + 55)
                # Moldura
                frame = portrait_rect.inflate(10, 10)
                pygame.draw.rect(screen, COL_PANEL_DARK, frame, border_radius=10)
                border_color = COL_ACCENT if legendary.get("is_shiny") else COL_SUCCESS
                pygame.draw.rect(screen, border_color, frame, 3, border_radius=10)
                screen.blit(self._legendary_portrait, portrait_rect)

            # Nome + nível
            name_color = COL_ACCENT if legendary.get("is_shiny") else COL_TEXT
            name_txt = self.font_sub.render(
                f"{legendary['name']}  Lv.{legendary['level']}",
                True, name_color
            )
            name_rect = name_txt.get_rect(center=(cx, y + 130))
            screen.blit(name_txt, name_rect)

            dest = legendary.get("destination", "box")
            dest_text = "Adicionado ao seu TIME" if dest == "team" else "Enviado à PC Box"
            dest_color = COL_SUCCESS if dest == "team" else COL_TEXT_DIM
            dest_txt = self.font_small.render(dest_text, True, dest_color)
            dest_rect = dest_txt.get_rect(center=(cx, y + 155))
            screen.blit(dest_txt, dest_rect)

            y += 185

        # ===== SEÇÃO: OUTRAS RECOMPENSAS =====
        section2 = self.font_section.render("OUTRAS RECOMPENSAS", True, COL_ACCENT)
        screen.blit(section2, section2.get_rect(center=(cx, y)))
        y += 28

        # Gold e XP lado a lado
        gold = self.rewards.get("gold", 0)
        xp = self.rewards.get("xp", 0)

        gold_txt = self.font_info.render(f"+{gold} Ouro", True, COL_GOLD)
        xp_txt = self.font_info.render(f"+{xp} XP", True, COL_XP)

        left_x = cx - 120
        right_x = cx + 20
        screen.blit(gold_txt, gold_txt.get_rect(midleft=(left_x, y)))
        screen.blit(xp_txt, xp_txt.get_rect(midleft=(right_x, y)))
        y += 30

        # Itens
        items = self.rewards.get("items", [])
        if items:
            items_label = self.font_small.render("Itens:", True, COL_TEXT_DIM)
            screen.blit(items_label, items_label.get_rect(midleft=(left_x, y)))

            item_x = left_x + 60
            item_y = y
            # Agrupa itens por id (contagem)
            from collections import Counter
            counts = Counter(items)
            for iid, count in counts.items():
                sprite = self._item_sprites.get(iid)
                if sprite:
                    screen.blit(sprite, (item_x, item_y - 14))
                    item_x += 32
                    if count > 1:
                        cnt_txt = self.font_small.render(f"x{count}", True, COL_ACCENT)
                        screen.blit(cnt_txt, (item_x, item_y - 8))
                        item_x += cnt_txt.get_width() + 12
                    else:
                        item_x += 8
            y += 30

        # Botão
        mouse = pygame.mouse.get_pos()
        hover = self.leave_btn.collidepoint(mouse)
        btn_color = COL_SUCCESS_H if hover else COL_SUCCESS
        border_color = COL_ACCENT if hover else COL_SUCCESS_DIM

        pygame.draw.rect(screen, btn_color, self.leave_btn, border_radius=14)
        pygame.draw.rect(screen, border_color, self.leave_btn, 3, border_radius=14)

        btn_txt = self.font_btn.render("Voltar ao Lobby", True, (255, 255, 255))
        btn_rect = btn_txt.get_rect(center=self.leave_btn.center)
        screen.blit(btn_txt, btn_rect)

        # Hint
        hint = self.font_small.render(
            "Pressione ENTER ou ESC para voltar", True, COL_TEXT_MUTED
        )
        hint_rect = hint.get_rect(center=(cx, self.leave_btn.bottom + 26))
        screen.blit(hint, hint_rect)