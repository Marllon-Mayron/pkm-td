# src/scenes/minigames/dojo/dojo_select_scene.py
"""
DojoSelectScene — escolha de 1 pokémon para lutar no Dojo.

Regras exibidas: sem bag, sem moves SPECIAL, 5 lutadores, prêmio Tyrogue.
"""
import math
import pygame

from src.scenes.base_scene import BaseScene
from src.data.pokedex import Pokedex


class DojoSelectScene(BaseScene):
    ROW_H = 78

    COL_BG = (14, 16, 28)
    COL_PANEL = (24, 27, 44)
    COL_BORDER = (55, 60, 85)
    COL_ACCENT = (255, 215, 0)
    COL_TEXT = (230, 230, 240)
    COL_DIM = (170, 175, 200)
    COL_MUTED = (110, 115, 140)
    COL_SUCCESS = (105, 220, 130)

    def __init__(self, game, chapter_id: int = 1, phase_number: int = 1,
                 on_exit=None):
        super().__init__(game)
        self.pokedex = Pokedex()
        self.chapter_id = chapter_id
        self.phase_number = phase_number
        self._on_exit = on_exit

        self.player_entries = []
        self._refresh()
        self.selected_uid = None
        self.poke_scroll = 0
        self._anim_time = 0.0

        self.back_btn = pygame.Rect(0, 0, 130, 42)
        self.fight_btn = pygame.Rect(0, 0, 420, 62)
        self._list_rect = None
        self._fonts = {}
        self._last_size = (0, 0)

        self._layout()

    # ------------------------------------------------------------------
    def _font(self, size):
        size = max(10, int(size))
        if size not in self._fonts:
            self._fonts[size] = pygame.font.Font(None, size)
        return self._fonts[size]

    def _refresh(self):
        self.player_entries = []
        seen = set()
        for p in self.game.player.team:
            if p.unique_id in seen:
                continue
            if not p.is_alive():
                continue
            self.player_entries.append({
                "unique_id": p.unique_id,
                "instance": p,
                "id": p.id,
                "name": p.get_display_name(),
                "level": p.level,
                "shiny": p.is_shiny,
                "types": list(p.types) if p.types else [],
            })
            seen.add(p.unique_id)

    def _layout(self):
        sm = self.screen_manager
        vx, vy = sm.viewport_x, sm.viewport_y
        vw, vh = sm.viewport_width, sm.viewport_height

        self.back_btn = pygame.Rect(vx + 20, vy + 20, 130, 42)

        margin = 40
        header_h = 170
        footer_h = 110

        list_w = min(680, vw - margin * 2)
        list_h = vh - header_h - footer_h
        self._list_rect = pygame.Rect(
            vx + (vw - list_w) // 2, vy + header_h,
            list_w, list_h,
        )

        self.fight_btn = pygame.Rect(0, 0, 420, 62)
        self.fight_btn.center = (vx + vw // 2, vy + vh - 55)

        self._last_size = (sm.window_width, sm.window_height)

    def _check_resize(self):
        sm = self.screen_manager
        cur = (sm.window_width, sm.window_height)
        if cur != self._last_size:
            self._layout()
            return True
        return False

    # ------------------------------------------------------------------
    def handle_event(self, event):
        self._check_resize()

        if event.type == pygame.KEYDOWN:
            if event.key == pygame.K_ESCAPE:
                self._go_back()
                return

        if event.type == pygame.MOUSEWHEEL:
            mx, my = pygame.mouse.get_pos()
            if self._list_rect and self._list_rect.collidepoint(mx, my):
                visible = max(1, (self._list_rect.height - 16) // self.ROW_H)
                max_s = max(0, len(self.player_entries) - visible)
                self.poke_scroll = max(0, min(max_s,
                                              self.poke_scroll - event.y))
            return

        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            pos = event.pos
            if self.back_btn.collidepoint(pos):
                self._go_back()
                return
            if self.fight_btn.collidepoint(pos):
                self._start_dojo()
                return
            if self._list_rect and self._list_rect.collidepoint(pos):
                rel_y = pos[1] - self._list_rect.y - 8
                idx = self.poke_scroll + rel_y // self.ROW_H
                if 0 <= idx < len(self.player_entries):
                    self.selected_uid = self.player_entries[idx]["unique_id"]

    def _go_back(self):
        if self._on_exit:
            try:
                self._on_exit()
                return
            except Exception as e:
                print(f"[DOJO] on_exit falhou: {e}")
        try:
            from src.scenes.minigame_select_scene.minigame_select_scene import (
                MinigameSelectScene,
            )
            self.game.current_scene = MinigameSelectScene(self.game)
        except Exception:
            self.game.current_scene = self.game.menu_scene

    def _start_dojo(self):
        if not self.selected_uid:
            return

        entry = next((e for e in self.player_entries
                      if e["unique_id"] == self.selected_uid), None)
        if not entry or not entry["instance"]:
            return

        player_data = entry["instance"].to_dict()

        def on_exit():
            # Volta pra própria tela de seleção (permite tentar de novo)
            self.game.current_scene = DojoSelectScene(
                self.game,
                chapter_id=self.chapter_id,
                phase_number=self.phase_number,
            )

        from src.scenes.minigames.dojo.dojo_minigame_scene import DojoMinigameScene
        self.game.current_scene = DojoMinigameScene(
            self.game,
            player_pokemon_data=player_data,
            chapter_id=self.chapter_id,
            phase_number=self.phase_number,
            on_exit=on_exit,
        )

    # ------------------------------------------------------------------
    def fixed_update(self, dt):
        self._anim_time += dt

    def render(self, screen):
        self._check_resize()
        screen.fill(self.COL_BG)

        sm = self.screen_manager
        vx, vy = sm.viewport_x, sm.viewport_y
        vw, vh = sm.viewport_width, sm.viewport_height

        # ---- Header ----
        title = self._font(52).render("DOJO DE LUTADORES", True, self.COL_ACCENT)
        screen.blit(title, title.get_rect(center=(vx + vw // 2, vy + 44)))

        sub = self._font(18).render(
            "Regras: 1 pokémon · Sem bag · Sem moves ESPECIAIS · "
            "Vença os 5 lutadores!",
            True, self.COL_DIM)
        screen.blit(sub, sub.get_rect(center=(vx + vw // 2, vy + 82)))

        prize = self._font(22).render(
            "PRÊMIO:  Tyrogue (Lv. 10)", True, self.COL_ACCENT)
        screen.blit(prize, prize.get_rect(center=(vx + vw // 2, vy + 118)))

        warn = self._font(14).render(
            "O Tyrogue só é entregue na 1ª vitória. Rejogar não duplica.",
            True, self.COL_MUTED)
        screen.blit(warn, warn.get_rect(center=(vx + vw // 2, vy + 144)))

        # ---- Botão sair ----
        pygame.draw.rect(screen, (60, 30, 35), self.back_btn, border_radius=10)
        pygame.draw.rect(screen, (170, 80, 90), self.back_btn, 2,
                         border_radius=10)
        bt = self._font(24).render("Sair", True, self.COL_TEXT)
        screen.blit(bt, bt.get_rect(center=self.back_btn.center))

        # ---- Lista ----
        pygame.draw.rect(screen, self.COL_PANEL, self._list_rect,
                         border_radius=14)
        pygame.draw.rect(screen, self.COL_BORDER, self._list_rect, 2,
                         border_radius=14)

        if not self.player_entries:
            msg = self._font(20).render(
                "Nenhum pokémon vivo no time ativo.", True, self.COL_DIM)
            screen.blit(msg, msg.get_rect(center=self._list_rect.center))
        else:
            self._render_list(screen)

        # ---- Botão entrar ----
        can_enter = self.selected_uid is not None
        mouse = pygame.mouse.get_pos()
        hover = self.fight_btn.collidepoint(mouse)

        if can_enter:
            pulse = 0.5 + 0.5 * math.sin(self._anim_time * 3.0)
            bg = (90, 190, 110) if hover else (55, 130, 70)
            border = (255, 215, 0)
            ga = int(50 + 60 * pulse)
            glow = pygame.Surface((self.fight_btn.width + 12,
                                   self.fight_btn.height + 12),
                                  pygame.SRCALPHA)
            pygame.draw.rect(glow, (255, 215, 0, ga), glow.get_rect(),
                             border_radius=20)
            screen.blit(glow, (self.fight_btn.x - 6, self.fight_btn.y - 6))
        else:
            bg = (55, 58, 68)
            border = (100, 105, 115)

        pygame.draw.rect(screen, bg, self.fight_btn, border_radius=18)
        pygame.draw.rect(screen, border, self.fight_btn, 3, border_radius=18)

        label = "ENTRAR NO DOJO!" if can_enter else "Escolha um pokémon"
        txt = self._font(30).render(label, True, (255, 255, 255))
        screen.blit(txt, txt.get_rect(center=self.fight_btn.center))

        hint = self._font(14).render(
            "ESC = sair   ·   Clique em um pokémon   ·   Você leva só 1",
            True, self.COL_MUTED)
        screen.blit(hint, hint.get_rect(center=(vx + vw // 2, vy + vh - 16)))

    # ------------------------------------------------------------------
    def _render_list(self, screen):
        rect = self._list_rect
        visible = max(1, (rect.height - 16) // self.ROW_H)
        start = self.poke_scroll
        end = min(len(self.player_entries), start + visible)

        old_clip = screen.get_clip()
        screen.set_clip(rect.inflate(-8, -8))
        mouse = pygame.mouse.get_pos()

        for i in range(start, end):
            idx = i - start
            row = pygame.Rect(
                rect.x + 8,
                rect.y + 8 + idx * self.ROW_H,
                rect.width - 16,
                self.ROW_H - 6,
            )
            entry = self.player_entries[i]
            selected = entry["unique_id"] == self.selected_uid
            hover = row.collidepoint(mouse)

            if selected:
                bg = (58, 120, 78)
                border = self.COL_SUCCESS
            elif hover:
                bg = (44, 50, 74)
                border = (110, 120, 155)
            else:
                bg = (30, 34, 52)
                border = self.COL_BORDER

            pygame.draw.rect(screen, bg, row, border_radius=10)
            pygame.draw.rect(screen, border, row, 2 if selected else 1,
                             border_radius=10)

            # Portrait
            portrait_size = 54
            px = row.x + 10
            py = row.y + (row.height - portrait_size) // 2
            try:
                pt = self.pokedex.get_portrait(entry["id"], "normal",
                                               entry["shiny"])
                if pt:
                    pt = pygame.transform.smoothscale(
                        pt, (portrait_size, portrait_size))
                    screen.blit(pt, (px, py))
            except Exception:
                pass

            # Nome + nível
            tx = px + portrait_size + 16
            name_color = self.COL_ACCENT if entry["shiny"] else self.COL_TEXT
            name_s = self._font(22).render(entry["name"], True, name_color)
            screen.blit(name_s, (tx, row.y + 8))

            lvl_s = self._font(16).render(
                f"Nível {entry['level']}", True, self.COL_DIM)
            screen.blit(lvl_s, (tx, row.y + 36))

            # Check de seleção
            if selected:
                cx = row.right - 26
                cy = row.centery
                pygame.draw.circle(screen, self.COL_SUCCESS, (cx, cy), 13)
                pygame.draw.lines(screen, (20, 30, 20), False,
                                  [(cx - 6, cy), (cx - 2, cy + 5),
                                   (cx + 6, cy - 6)], 3)

        screen.set_clip(old_clip)