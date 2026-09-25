# src/scenes/pvp_scene/pvp_select_scene.py
"""
Seleção do formato PvP + escolha do time.

Formatos:
  1v1 → 1 jogador/time · time de até 6 · 1 em campo
        (mínimo 1 pokémon — o jogador que se prejudique se levar menos)
  2v2 → 2 jogadores/time · time de 3 · 1 em campo por jogador
  3v3 → 3 jogadores/time · time de 2 · 2 em campo por jogador
"""
import math
import pygame

from src.scenes.base_scene import BaseScene
from src.data.pokedex import Pokedex
from src.data.pvp_catalog import (
    get_pvp_format, get_pvp_total_players, get_pvp_team_size,
    get_pvp_spots_per_player, get_pvp_total_on_field,
)
from src.managers.sounds.sound_manager import sound_manager, SoundEffect


COL_BG          = (14, 16, 28)
COL_PANEL       = (24, 27, 44)
COL_PANEL_DARK  = (18, 20, 34)
COL_PANEL_MED   = (30, 34, 52)
COL_BORDER      = (55, 60, 85)
COL_BORDER_HL   = (110, 120, 155)
COL_ACCENT      = (255, 215, 0)
COL_TEXT        = (230, 230, 240)
COL_TEXT_DIM    = (170, 175, 200)
COL_TEXT_MUTED  = (110, 115, 140)
COL_SUCCESS     = (105, 220, 130)
COL_DANGER      = (230, 90, 90)
COL_ITEM        = (30, 34, 52)
COL_ITEM_HOVER  = (44, 50, 74)
COL_ITEM_SEL    = (58, 120, 78)
COL_ITEM_SEL_HV = (70, 145, 95)


PVP_MODES = [
    {"chapter": 1, "label": "1v1", "subtitle": "Duelo Individual",
     "desc": "1 jogador/time · até 6 pokémon · 1 vs 1 em campo"},
    {"chapter": 2, "label": "2v2", "subtitle": "Batalha em Dupla",
     "desc": "2 jogadores/time · 3 pokémon cada · 2 vs 2 em campo"},
    {"chapter": 3, "label": "3v3", "subtitle": "Confronto Completo",
     "desc": "3 jogadores/time · 2 pokémon cada · 6 vs 6 em campo"},
]


class PvPSelectScene(BaseScene):
    ROW_FORMAT_H = 90
    ROW_POKE_H   = 74
    POKE_PAD     = 8

    def __init__(self, game, network, on_back=None):
        super().__init__(game)
        self.pokedex = Pokedex()
        self.network = network
        self._on_back = on_back

        self.modes = list(PVP_MODES)
        self.selected_mode_idx = 0

        self.player_entries = []
        self._refresh_entries()
        self.selected_ids = set()
        self.poke_scroll = 0

        self._anim_time = 0.0
        self._fonts = {}
        self._last_size = (0, 0)

        self.back_btn = pygame.Rect(0, 0, 130, 42)
        self.ready_btn = pygame.Rect(0, 0, 340, 60)
        self._left_rect = None
        self._right_rect = None
        self._poke_rect = None
        self._format_rects = []

        self._layout()

    # ------------------------------------------------------------------
    def _font(self, size):
        size = max(10, int(size))
        if size not in self._fonts:
            self._fonts[size] = pygame.font.Font(None, size)
        return self._fonts[size]

    def _refresh_entries(self):
        self.player_entries = []
        seen = set()
        for p in self.game.player.team:
            if p.unique_id in seen or not p.is_alive():
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

    def _selected_chapter(self):
        return self.modes[self.selected_mode_idx]["chapter"]

    # ------------------------------------------------------------------
    # Regras de seleção
    # ------------------------------------------------------------------
    def _required_pokemon(self):
        """Quantidade 'nominal' de pokémon do formato (team_size).
        Usado no display e na validação de modos rígidos."""
        return get_pvp_team_size(self._selected_chapter())

    def _min_pokemon(self):
        """Mínimo que o jogador PRECISA escolher.
        - 1v1: 1 (o jogador pode ir com menos que o máximo e se virar)
        - 2v2 / 3v3: exatamente o team_size (rígido)"""
        chapter = self._selected_chapter()
        if chapter == 1:
            return 1
        return get_pvp_team_size(chapter)

    def _max_pokemon(self):
        """Máximo que o jogador PODE escolher (também é o teto físico)."""
        return get_pvp_team_size(self._selected_chapter())

    def _is_selection_valid(self):
        chosen = len(self.selected_ids)
        return self._min_pokemon() <= chosen <= self._max_pokemon()

    def _required_players(self):
        return get_pvp_total_players(self._selected_chapter())

    # ------------------------------------------------------------------
    def _layout(self):
        sm = self.screen_manager
        vx, vy = sm.viewport_x, sm.viewport_y
        vw, vh = sm.viewport_width, sm.viewport_height

        self.back_btn = pygame.Rect(vx + 20, vy + 20, 130, 42)

        margin = 24
        header_h = 108
        footer_h = 96
        cy = vy + header_h
        ch = vh - header_h - footer_h

        left_w = int(vw * 0.38)
        gap = 20

        self._left_rect = pygame.Rect(vx + margin, cy, left_w, ch)
        self._right_rect = pygame.Rect(
            self._left_rect.right + gap, cy,
            vw - left_w - margin * 2 - gap, ch,
        )

        self._format_rects = []
        fmt_y = self._left_rect.y + 12 + 32
        for i in range(len(self.modes)):
            self._format_rects.append(pygame.Rect(
                self._left_rect.x + 14,
                fmt_y + i * (self.ROW_FORMAT_H + 8),
                self._left_rect.width - 28,
                self.ROW_FORMAT_H,
            ))

        self._poke_rect = pygame.Rect(
            self._right_rect.x + 16,
            self._right_rect.y + 260,
            self._right_rect.width - 32,
            max(60, self._right_rect.height - 276),
        )

        self.ready_btn = pygame.Rect(0, 0, 340, 60)
        self.ready_btn.center = (vx + vw // 2, vy + vh - 48)

        self._last_size = (sm.window_width, sm.window_height)

    def _check_resize(self):
        sm = self.screen_manager
        if (sm.window_width, sm.window_height) != self._last_size:
            self._layout()
            return True
        return False

    def _visible_poke_rows(self):
        avail = self._poke_rect.height - self.POKE_PAD * 2
        return max(1, avail // self.ROW_POKE_H)

    # ------------------------------------------------------------------
    def handle_event(self, event):
        self._check_resize()

        if event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE:
            self._go_back()
            return

        if event.type == pygame.MOUSEWHEEL:
            mx, my = pygame.mouse.get_pos()
            if self._poke_rect and self._poke_rect.collidepoint(mx, my):
                max_s = max(0, len(self.player_entries) - self._visible_poke_rows())
                self.poke_scroll = max(0, min(max_s, self.poke_scroll - event.y))
            return

        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            pos = event.pos

            if self.back_btn.collidepoint(pos):
                sound_manager.play_effect(SoundEffect.CLICK)
                self._go_back()
                return

            if self.ready_btn.collidepoint(pos):
                self._start_matchmaking()
                return

            for i, r in enumerate(self._format_rects):
                if r.collidepoint(pos):
                    if i != self.selected_mode_idx:
                        self.selected_mode_idx = i
                        # ★ Ao trocar de formato, o time selecionado pode
                        # ficar inválido. Não limpamos agressivamente para
                        # não irritar o jogador — só garantimos que a
                        # seleção não ultrapasse o novo máximo.
                        self._clamp_selection_to_max()
                        self.poke_scroll = 0
                        sound_manager.play_effect(SoundEffect.CLICK, volume=0.2)
                    return

            if self._poke_rect and self._poke_rect.collidepoint(pos):
                rel_y = pos[1] - self._poke_rect.y - self.POKE_PAD
                if rel_y >= 0:
                    idx = self.poke_scroll + rel_y // self.ROW_POKE_H
                    if 0 <= idx < len(self.player_entries):
                        self._toggle_poke(self.player_entries[idx])
                return

    def _clamp_selection_to_max(self):
        """Remove seleção excedente ao trocar de formato."""
        max_p = self._max_pokemon()
        while len(self.selected_ids) > max_p:
            self.selected_ids.pop()

    def _toggle_poke(self, entry):
        uid = entry["unique_id"]
        max_p = self._max_pokemon()

        if uid in self.selected_ids:
            self.selected_ids.discard(uid)
        else:
            # ★ Só bloqueia se ultrapassar o MÁXIMO (não o "required").
            # No 1v1 isso permite selecionar de 1 a 6 livremente.
            if len(self.selected_ids) >= max_p:
                self.selected_ids.pop()
            self.selected_ids.add(uid)
        sound_manager.play_effect(SoundEffect.CLICK, volume=0.2)

    def _go_back(self):
        if self._on_back:
            self._on_back()
            return
        from src.scenes.lobby_scene.lobby_scene import LobbyScene
        self.game.current_scene = LobbyScene(
            self.game, is_host=self.network.is_host, network=self.network
        )

    def _start_matchmaking(self):
        # ★ Validação: usa min/max em vez de exigir exatamente o team_size
        if not self._is_selection_valid():
            return

        team_data = []
        for entry in self.player_entries:
            if entry["unique_id"] in self.selected_ids:
                inst = entry["instance"]
                if inst:
                    team_data.append(inst.to_dict())

        if not team_data:
            return

        from src.scenes.pvp_scene.pvp_matchmaking_scene import PvPMatchmakingScene
        sound_manager.play_effect(SoundEffect.CLICK)

        def on_ready(all_teams, my_team_side):
            from src.scenes.pvp_scene.pvp_battle_scene import PvPBattleScene
            from src.data.pvp_catalog import list_pvps
            chapter = self._selected_chapter()
            arenas = list_pvps(chapter)
            if not arenas:
                print(f"[PVP] Sem mapas para cap {chapter}")
                self._go_back()
                return
            arena_ch, arena_lv = arenas[0]
            self.game.current_scene = PvPBattleScene(
                self.game,
                network=self.network,
                all_teams=all_teams,
                format_chapter=chapter,
                arena_chapter=arena_ch,
                arena_level=arena_lv,
                my_team_side=my_team_side,
            )

        self.game.current_scene = PvPMatchmakingScene(
            self.game, self.network,
            format_chapter=self._selected_chapter(),
            my_team_data=team_data,
            on_back=self._go_back,
            on_ready=on_ready,
        )

    # ------------------------------------------------------------------
    def fixed_update(self, dt):
        self._anim_time += dt

    # ------------------------------------------------------------------
    def render(self, screen):
        self._check_resize()
        screen.fill(COL_BG)

        sm = self.screen_manager
        vx, vy = sm.viewport_x, sm.viewport_y
        vw, vh = sm.viewport_width, sm.viewport_height

        title = self._font(50).render("ARENA PVP", True, COL_ACCENT)
        screen.blit(title, title.get_rect(center=(vx + vw // 2, vy + 44)))

        line_w = title.get_width() + 80
        pygame.draw.line(screen, (90, 80, 35),
                         (vx + vw // 2 - line_w // 2, vy + 76),
                         (vx + vw // 2 + line_w // 2, vy + 76), 2)

        sub = self._font(20).render(
            "Escolha o formato e monte seu time", True, COL_TEXT_DIM)
        screen.blit(sub, sub.get_rect(center=(vx + vw // 2, vy + 94)))

        pygame.draw.rect(screen, (60, 30, 35), self.back_btn, border_radius=10)
        pygame.draw.rect(screen, (170, 80, 90), self.back_btn, 2, border_radius=10)
        bt = self._font(24).render("Sair", True, COL_TEXT)
        screen.blit(bt, bt.get_rect(center=self.back_btn.center))

        self._render_left(screen)
        self._render_right(screen)
        self._render_ready_btn(screen)

        hint = self._font(14).render(
            "Clique nos pokémon para escolher  ·  O time é enviado ao matchmaking",
            True, COL_TEXT_MUTED)
        screen.blit(hint, hint.get_rect(center=(vx + vw // 2, vy + vh - 14)))

    # ------------------------------------------------------------------
    def _render_left(self, screen):
        rect = self._left_rect

        pygame.draw.rect(screen, COL_PANEL, rect, border_radius=14)
        pygame.draw.rect(screen, COL_BORDER, rect, 1, border_radius=14)

        hdr = pygame.Rect(rect.x, rect.y, rect.width, 32)
        pygame.draw.rect(screen, (34, 40, 55), hdr,
                         border_top_left_radius=14, border_top_right_radius=14)
        s = self._font(20).render("FORMATO", True, COL_ACCENT)
        screen.blit(s, (hdr.x + 16, hdr.y + 7))

        mouse = pygame.mouse.get_pos()
        for i, row in enumerate(self._format_rects):
            mode = self.modes[i]
            selected = (i == self.selected_mode_idx)
            hover = row.collidepoint(mouse)

            if selected:
                bg, border = (62, 52, 100), (200, 180, 255)
            elif hover:
                bg, border = (40, 44, 62), (110, 120, 150)
            else:
                bg, border = (26, 30, 42), (48, 53, 68)

            if selected:
                pulse = 0.5 + 0.5 * math.sin(self._anim_time * 3.0)
                ga = int(60 + 60 * pulse)
                glow = pygame.Surface((row.width + 8, row.height + 8), pygame.SRCALPHA)
                pygame.draw.rect(glow, (200, 180, 255, ga),
                                 glow.get_rect(), border_radius=14)
                screen.blit(glow, (row.x - 4, row.y - 4))

            pygame.draw.rect(screen, bg, row, border_radius=12)
            pygame.draw.rect(screen, border, row, 2 if selected else 1, border_radius=12)

            lbl = self._font(40).render(mode["label"], True, COL_ACCENT)
            lr = lbl.get_rect()
            lr.left = row.x + 20
            lr.centery = row.centery
            screen.blit(lbl, lr)

            tx = lr.right + 22
            sub = self._font(22).render(mode["subtitle"], True, COL_TEXT)
            screen.blit(sub, (tx, row.y + 12))

            desc = self._font(15).render(mode["desc"], True, COL_TEXT_DIM)
            screen.blit(desc, (tx, row.y + 46))

    def _render_right(self, screen):
        rect = self._right_rect
        pygame.draw.rect(screen, COL_PANEL, rect, border_radius=14)
        pygame.draw.rect(screen, COL_BORDER, rect, 1, border_radius=14)

        chapter = self._selected_chapter()
        players, team_size, spots_pp, label = get_pvp_format(chapter)
        total_players = get_pvp_total_players(chapter)
        on_field = get_pvp_total_on_field(chapter)

        y = rect.y + 18
        nm = self._font(30).render(self.modes[self.selected_mode_idx]["subtitle"],
                                    True, COL_ACCENT)
        screen.blit(nm, (rect.x + 22, y))
        y += 40

        info = self._font(18).render(
            f"{players} jogador(es)/time  ·  time de até {team_size}  ·  "
            f"{spots_pp} em campo/jogador",
            True, COL_TEXT_DIM)
        screen.blit(info, (rect.x + 22, y))
        y += 26

        info_field = self._font(16).render(
            f"Em campo: {on_field} vs {on_field}",
            True, COL_SUCCESS)
        screen.blit(info_field, (rect.x + 22, y))
        y += 24

        info2 = self._font(15).render(
            f"Total de jogadores: {total_players}",
            True, COL_TEXT_MUTED)
        screen.blit(info2, (rect.x + 22, y))
        y += 28

        pygame.draw.line(screen, (55, 60, 85),
                         (rect.x + 22, y), (rect.right - 22, y), 1)
        y += 14

        # ★ Usa min/max em vez de exigir exatamente team_size
        min_p = self._min_pokemon()
        max_p = self._max_pokemon()
        chosen = len(self.selected_ids)
        is_valid = self._is_selection_valid()

        if min_p == max_p:
            label_range = f"{max_p}"
        else:
            label_range = f"{min_p}-{max_p}"

        color = COL_SUCCESS if is_valid else COL_TEXT
        title_s = self._font(22).render(
            f"SEU TIME  ({chosen}/{label_range})", True, color)
        screen.blit(title_s, (rect.x + 22, y))

        if is_valid:
            hint_txt = "Pronto!"
            hint_col = COL_SUCCESS
        elif chosen < min_p:
            faltam = min_p - chosen
            hint_txt = f"Faltam {faltam}"
            hint_col = COL_ACCENT
        else:
            hint_txt = "Muitos"
            hint_col = COL_DANGER
        hs = self._font(14).render(hint_txt, True, hint_col)
        hr = hs.get_rect()
        hr.right = rect.right - 22
        hr.centery = title_s.get_rect(topleft=(rect.x + 22, y)).centery
        screen.blit(hs, hr)
        y += 32

        self._poke_rect.y = y
        self._poke_rect.height = max(60, rect.bottom - y - 20)
        self._render_pokemon_list(screen)

    def _render_pokemon_list(self, screen):
        rect = self._poke_rect
        if rect.height < 40:
            return

        pygame.draw.rect(screen, COL_PANEL_DARK, rect, border_radius=10)
        pygame.draw.rect(screen, COL_BORDER, rect, 1, border_radius=10)

        if not self.player_entries:
            msg = self._font(18).render(
                "Nenhum Pokémon no seu time.", True, COL_TEXT_MUTED)
            screen.blit(msg, msg.get_rect(center=rect.center))
            return

        clip = pygame.Rect(rect.x + 4, rect.y + 4, rect.width - 8, rect.height - 8)
        old_clip = screen.get_clip()
        screen.set_clip(clip)

        visible = self._visible_poke_rows()
        start = self.poke_scroll
        end = min(len(self.player_entries), start + visible)
        mouse = pygame.mouse.get_pos()

        for i in range(start, end):
            idx = i - start
            row = pygame.Rect(
                rect.x + 8,
                rect.y + self.POKE_PAD + idx * self.ROW_POKE_H,
                rect.width - 16,
                self.ROW_POKE_H - 6,
            )
            entry = self.player_entries[i]
            selected = entry["unique_id"] in self.selected_ids
            hover = row.collidepoint(mouse)

            if selected:
                bg, border = ((COL_ITEM_SEL_HV, COL_SUCCESS) if hover
                              else (COL_ITEM_SEL, COL_SUCCESS))
            elif hover:
                bg, border = COL_ITEM_HOVER, COL_BORDER_HL
            else:
                bg, border = COL_ITEM, COL_BORDER

            if selected:
                pulse = 0.5 + 0.5 * math.sin(self._anim_time * 4.0)
                ga = int(40 + 40 * pulse)
                glow = pygame.Surface((row.width + 8, row.height + 8), pygame.SRCALPHA)
                pygame.draw.rect(glow, (*COL_SUCCESS, ga),
                                 glow.get_rect(), border_radius=12)
                screen.blit(glow, (row.x - 4, row.y - 4))

            pygame.draw.rect(screen, bg, row, border_radius=10)
            pygame.draw.rect(screen, border, row, 2 if selected else 1, border_radius=10)

            psize = 50
            px = row.x + 10
            py = row.y + (row.height - psize) // 2
            try:
                pt = self.pokedex.get_portrait(entry["id"], "normal", entry["shiny"])
                if pt:
                    pt = pygame.transform.smoothscale(pt, (psize, psize))
                    screen.blit(pt, (px, py))
            except Exception:
                pass

            frame = pygame.Rect(px, py, psize, psize)
            frame_color = COL_ACCENT if entry["shiny"] else COL_BORDER_HL
            pygame.draw.rect(screen, frame_color, frame, 2, border_radius=8)

            tx = px + psize + 14
            name_color = COL_ACCENT if entry["shiny"] else COL_TEXT
            ns = self._font(20).render(entry["name"], True, name_color)
            screen.blit(ns, (tx, row.y + 8))
            ls = self._font(15).render(f"Nv. {entry['level']}", True, COL_TEXT_DIM)
            screen.blit(ls, (tx, row.y + 34))

        screen.set_clip(old_clip)

    def _render_ready_btn(self, screen):
        # ★ Validação por min/max — em 1v1, qualquer valor entre 1 e 6 vale
        is_valid = self._is_selection_valid()
        chosen = len(self.selected_ids)
        min_p = self._min_pokemon()
        max_p = self._max_pokemon()

        if is_valid:
            bg = (55, 130, 70)
            bg_hover = (90, 190, 110)
            border = COL_ACCENT
        else:
            bg = bg_hover = (55, 58, 68)
            border = (100, 105, 115)

        mouse = pygame.mouse.get_pos()
        hover = is_valid and self.ready_btn.collidepoint(mouse)
        color = bg_hover if hover else bg

        if is_valid:
            pulse = 0.5 + 0.5 * math.sin(self._anim_time * 3.0)
            ga = int(50 + 60 * pulse)
            glow = pygame.Surface(
                (self.ready_btn.width + 12, self.ready_btn.height + 12),
                pygame.SRCALPHA)
            pygame.draw.rect(glow, (*COL_ACCENT, ga),
                             glow.get_rect(), border_radius=20)
            screen.blit(glow, (self.ready_btn.x - 6, self.ready_btn.y - 6))

        pygame.draw.rect(screen, color, self.ready_btn, border_radius=18)
        pygame.draw.rect(screen, border, self.ready_btn, 3, border_radius=18)

        if not is_valid:
            if chosen < min_p:
                faltam = min_p - chosen
                label = f"Escolha {faltam} pokémon" if faltam > 1 else "Escolha 1 pokémon"
            else:
                # Ultrapassou o máximo (não deveria acontecer, mas defensivo)
                remova = chosen - max_p
                label = f"Remova {remova} pokémon"
        else:
            label = "BUSCAR PARTIDA!"

        s = self._font(32).render(label, True, (255, 255, 255))
        sh = self._font(32).render(label, True, (0, 0, 0))
        r = s.get_rect(center=self.ready_btn.center)
        screen.blit(sh, (r.x + 2, r.y + 2))
        screen.blit(s, r)