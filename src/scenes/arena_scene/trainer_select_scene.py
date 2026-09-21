# src/scenes/arena_scene/trainer_select_scene.py
"""
Seleção de modo de batalha da arena.

O jogador escolhe:
  - FORMATO     (1v1 / 2v2 / 3v3)
  - DIFICULDADE (Fácil / Normal / Difícil) — via dropdown
  - Seu time    (apenas pokémons que estão DE FATO no time ativo)

Um treinador oponente é sorteado aleatoriamente dentro do pool
(capítulo × dificuldade). O time dele permanece OCULTO.
"""
import math
import random
import pygame

from src.scenes.base_scene import BaseScene
from src.data.trainer_catalog import pool_for
from src.data.pokedex import Pokedex
from src.data.arena_catalog import list_arenas, get_arena_format
from src.managers.sounds.sound_manager import sound_manager, SoundEffect


# ---- Paleta ----
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


# ---- Fallback de cores de tipo ----
_TYPE_COLORS_FALLBACK = {
    "normal": (168, 168, 120), "fire": (240, 128, 48),
    "water": (104, 144, 240), "electric": (248, 208, 48),
    "grass": (120, 200, 80), "ice": (152, 216, 216),
    "fighting": (192, 48, 40), "poison": (160, 64, 160),
    "ground": (224, 192, 104), "flying": (168, 144, 240),
    "psychic": (248, 88, 136), "bug": (168, 184, 32),
    "rock": (184, 160, 56), "ghost": (112, 88, 152),
    "dragon": (112, 56, 248), "dark": (112, 88, 72),
    "steel": (184, 184, 208), "fairy": (238, 153, 238),
}

_TYPE_LABELS_PT = {
    "normal": "NORMAL", "fire": "FOGO", "water": "ÁGUA",
    "electric": "ELÉTRICO", "grass": "PLANTA", "ice": "GELO",
    "fighting": "LUTA", "poison": "VENENO", "ground": "TERRA",
    "flying": "VOADOR", "psychic": "PSÍQUICO", "bug": "INSETO",
    "rock": "PEDRA", "ghost": "FANTASMA", "dragon": "DRAGÃO",
    "dark": "SOMBRIO", "steel": "AÇO", "fairy": "FADA",
}


# ---- Formatos ----
MODES = [
    {"chapter": 1, "label": "1v1", "subtitle": "Duelo Individual",
     "desc": "Um contra um. Rápido e direto."},
    {"chapter": 2, "label": "2v2", "subtitle": "Batalha em Dupla",
     "desc": "Dois contra dois. Coordene seu time com cuidado."},
    {"chapter": 3, "label": "3v3", "subtitle": "Confronto Completo",
     "desc": "Três contra três. Estratégia total em campo."},
]

# ---- Dificuldades ----
DIFFICULTIES = [
    {"key": "easy",   "label": "FÁCIL",   "color": COL_SUCCESS,
     "desc": "Oponentes mais fracos, com menos itens e IA mais lenta."},
    {"key": "normal", "label": "NORMAL",  "color": COL_ACCENT,
     "desc": "Desafio balanceado. IA usa itens com frequência média."},
    {"key": "hard",   "label": "DIFÍCIL", "color": COL_DANGER,
     "desc": "IA agressiva, cura-se constantemente e luta até o fim."},
]


class TrainerSelectScene(BaseScene):
    # ---- Layout ----
    ROW_FORMAT_H        = 96
    ROW_POKE_H          = 78
    POKE_LIST_PAD_TOP   = 8
    DIFF_BTN_H          = 62
    DIFF_OPTION_H       = 60

    def __init__(self, game, chapter_filter=None):
        super().__init__(game)
        self.pokedex = Pokedex()

        # ---- Modo ----
        self.modes = list(MODES)
        self.selected_mode_idx = 0
        if chapter_filter is not None:
            for i, m in enumerate(self.modes):
                if m["chapter"] == chapter_filter:
                    self.selected_mode_idx = i
                    break

        # ---- Dificuldade ----
        self.difficulties = list(DIFFICULTIES)
        self.selected_difficulty_idx = 1  # normal por padrão
        self.difficulty_dropdown_open = False
        self._diff_btn_rect = None
        self._diff_option_rects = []

        # ---- Pokémons do jogador ----
        self.player_entries = []
        self._refresh_player_entries()
        self.selected_poke_ids = set()
        self.poke_scroll = 0

        # ---- Animação ----
        self._anim_time = 0.0

        # ---- Layout ----
        self.back_btn  = pygame.Rect(0, 0, 110, 36)
        self.fight_btn = pygame.Rect(0, 0, 340, 60)
        self._left_rect  = None
        self._right_rect = None
        self._poke_rect  = None
        self._format_row_rects = []
        self._diff_header_y = 0

        self._fonts = {}
        self._last_size = (0, 0)
        self._layout()

    # ==================================================================
    # FONTES / HELPERS
    # ==================================================================
    def _font(self, size):
        size = max(10, int(size))
        if size not in self._fonts:
            self._fonts[size] = pygame.font.Font(None, size)
        return self._fonts[size]

    def _get_type_color(self, type_name):
        try:
            c = self.pokedex.get_type_color(type_name)
            if c:
                return c
        except Exception:
            pass
        return _TYPE_COLORS_FALLBACK.get(type_name.lower(), (150, 150, 150))

    def _type_label(self, type_name):
        return _TYPE_LABELS_PT.get(type_name.lower(),
                                    type_name.upper()[:8])

    def _draw_type_badge(self, screen, x, y, type_name, font_size=14):
        color = self._get_type_color(type_name)
        label = self._type_label(type_name)
        font = self._font(font_size)

        text = font.render(label, True, (255, 255, 255))
        pad_x, pad_y = 9, 3
        w = text.get_width() + pad_x * 2
        h = text.get_height() + pad_y * 2

        rect = pygame.Rect(x, y, w, h)
        pygame.draw.rect(screen, color, rect, border_radius=6)
        pygame.draw.rect(screen, (255, 255, 255, 90), rect, 1, border_radius=6)
        screen.blit(text, (x + pad_x, y + pad_y - 1))
        return w

    # ==================================================================
    # DADOS
    # ==================================================================
    def _refresh_player_entries(self):
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
                "current_hp": p.current_hp,
                "max_hp": p.max_hp,
            })
            seen.add(p.unique_id)

    def _get_selected_mode(self):
        if 0 <= self.selected_mode_idx < len(self.modes):
            return self.modes[self.selected_mode_idx]
        return None

    def _get_selected_difficulty(self):
        if 0 <= self.selected_difficulty_idx < len(self.difficulties):
            return self.difficulties[self.selected_difficulty_idx]
        return None

    def _required_team_size(self):
        mode = self._get_selected_mode()
        if not mode:
            return 1
        size, _ = get_arena_format(mode["chapter"])
        return size

    def _pick_random_trainer(self, chapter, difficulty):
        pool = pool_for(chapter, difficulty)
        if not pool:
            return None
        return random.choice(pool)

    # ==================================================================
    # LAYOUT
    # ==================================================================
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

        self._left_rect  = pygame.Rect(vx + margin, cy, left_w, ch)
        self._right_rect = pygame.Rect(
            self._left_rect.right + gap, cy,
            vw - left_w - margin * 2 - gap, ch,
        )

        # ---- Rows de formato ----
        self._format_row_rects = []
        fmt_y = self._left_rect.y + 12 + 32
        for i in range(len(self.modes)):
            self._format_row_rects.append(pygame.Rect(
                self._left_rect.x + 14,
                fmt_y + i * (self.ROW_FORMAT_H + 8),
                self._left_rect.width - 28,
                self.ROW_FORMAT_H,
            ))

        # ---- Dificuldade (header + botão dropdown) ----
        last_fmt = self._format_row_rects[-1]
        self._diff_header_y = last_fmt.bottom + 20

        diff_btn_y = self._diff_header_y + 34
        self._diff_btn_rect = pygame.Rect(
            self._left_rect.x + 14,
            diff_btn_y,
            self._left_rect.width - 28,
            self.DIFF_BTN_H,
        )

        # ---- Lista de pokémons (posição ajustada no render) ----
        self._poke_rect = pygame.Rect(
            self._right_rect.x + 16,
            self._right_rect.y + 300,
            self._right_rect.width - 32,
            max(60, self._right_rect.height - 316),
        )

        # ---- Botão de batalha ----
        self.fight_btn = pygame.Rect(0, 0, 340, 60)
        self.fight_btn.center = (vx + vw // 2, vy + vh - 48)

        self._last_size = (sm.window_width, sm.window_height)

    def _check_resize(self):
        sm = self.screen_manager
        cur = (sm.window_width, sm.window_height)
        if cur != self._last_size:
            self._layout()
            return True
        return False

    def _visible_poke_rows(self):
        if not self._poke_rect:
            return 5
        avail = self._poke_rect.height - self.POKE_LIST_PAD_TOP * 2
        return max(1, avail // self.ROW_POKE_H)

    # ==================================================================
    # EVENTOS
    # ==================================================================
    def handle_event(self, event):
        self._check_resize()

        if event.type == pygame.VIDEORESIZE:
            self.difficulty_dropdown_open = False
            return

        if event.type == pygame.KEYDOWN:
            if event.key == pygame.K_ESCAPE:
                if self.difficulty_dropdown_open:
                    self.difficulty_dropdown_open = False
                else:
                    self._go_back()
                return

        # ---- Scroll na lista de pokémons ----
        if event.type == pygame.MOUSEWHEEL:
            mx, my = pygame.mouse.get_pos()
            if self._poke_rect and self._poke_rect.collidepoint(mx, my):
                max_s = max(0, len(self.player_entries)
                            - self._visible_poke_rows())
                self.poke_scroll = max(0, min(max_s,
                                              self.poke_scroll - event.y))
            return

        # ---- Cliques ----
        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            pos = event.pos

            # 1) Dropdown aberto tem prioridade ABSOLUTA
            if self.difficulty_dropdown_open:
                for i, r in enumerate(self._diff_option_rects):
                    if r.collidepoint(pos):
                        if i != self.selected_difficulty_idx:
                            self.selected_difficulty_idx = i
                            sound_manager.play_effect(
                                SoundEffect.CLICK, volume=0.2)
                        self.difficulty_dropdown_open = False
                        return

                if self._diff_btn_rect and self._diff_btn_rect.collidepoint(pos):
                    self.difficulty_dropdown_open = False
                    return

                self.difficulty_dropdown_open = False
                return

            # 2) Voltar
            if self.back_btn.collidepoint(pos):
                sound_manager.play_effect(SoundEffect.CLICK)
                self._go_back()
                return

            # 3) Batalhar
            if self.fight_btn.collidepoint(pos):
                self._start_battle()
                return

            # 4) Formato
            for i, r in enumerate(self._format_row_rects):
                if r.collidepoint(pos):
                    if i != self.selected_mode_idx:
                        self.selected_mode_idx = i
                        self.selected_poke_ids.clear()
                        self.poke_scroll = 0
                        sound_manager.play_effect(
                            SoundEffect.CLICK, volume=0.2)
                    return

            # 5) Dificuldade — abre dropdown
            if self._diff_btn_rect and self._diff_btn_rect.collidepoint(pos):
                self.difficulty_dropdown_open = True
                sound_manager.play_effect(SoundEffect.CLICK, volume=0.2)
                return

            # 6) Pokémons
            if self._poke_rect and self._poke_rect.collidepoint(pos):
                rel_y = pos[1] - self._poke_rect.y - self.POKE_LIST_PAD_TOP
                if rel_y >= 0:
                    idx = self.poke_scroll + rel_y // self.ROW_POKE_H
                    if 0 <= idx < len(self.player_entries):
                        self._toggle_poke(self.player_entries[idx])
                return

    def _toggle_poke(self, entry):
        uid = entry["unique_id"]
        max_n = self._required_team_size()

        if uid in self.selected_poke_ids:
            self.selected_poke_ids.discard(uid)
        else:
            if len(self.selected_poke_ids) >= max_n:
                self.selected_poke_ids.pop()
            self.selected_poke_ids.add(uid)

        sound_manager.play_effect(SoundEffect.CLICK, volume=0.2)

    def _go_back(self):
        from src.scenes.npc_hall_scene.npc_hall_scene import NpcHallScene
        self.game.current_scene = NpcHallScene(self.game)

    # ==================================================================
    # INICIAR BATALHA
    # ==================================================================
    def _start_battle(self):
        mode = self._get_selected_mode()
        diff = self._get_selected_difficulty()
        if not mode or not diff:
            return

        required = self._required_team_size()
        if len(self.selected_poke_ids) != required:
            return

        chapter = mode["chapter"]

        trainer = self._pick_random_trainer(chapter, diff["key"])
        if not trainer:
            print(f"[ARENA] Sem treinador para cap={chapter} "
                  f"diff={diff['key']}")
            return

        trainer = dict(trainer)
        trainer["difficulty"] = diff["key"]

        arenas = list_arenas(chapter)
        if not arenas:
            print(f"[ARENA] Nenhuma arena para cap {chapter}")
            return
        arena_chapter, arena_level = arenas[0]

        player_data = []
        for entry in self.player_entries:
            if entry["unique_id"] not in self.selected_poke_ids:
                continue
            inst = entry["instance"]
            if inst:
                player_data.append(inst.to_dict())

        if not player_data:
            print("[ARENA] Sem pokémons selecionados!")
            return

        enemy_data = trainer.get("team", [])

        def on_exit():
            self.game.current_scene = TrainerSelectScene(self.game)

        from src.scenes.arena_scene.arena_battle_scene import ArenaBattleScene
        sound_manager.play_effect(SoundEffect.CLICK)
        self.game.current_scene = ArenaBattleScene(
            self.game,
            player_team_data=player_data,
            enemy_team_data=enemy_data,
            arena_chapter=arena_chapter,
            arena_level=arena_level,
            enemy_is_npc=True,
            trainer_data=trainer,
            on_exit=on_exit,
        )

    # ==================================================================
    # UPDATE
    # ==================================================================
    def fixed_update(self, dt):
        self._anim_time += dt

    # ==================================================================
    # RENDER
    # ==================================================================
    def render(self, screen):
        self._check_resize()
        screen.fill(COL_BG)

        sm = self.screen_manager
        vx, vy = sm.viewport_x, sm.viewport_y
        vw, vh = sm.viewport_width, sm.viewport_height

        # ---- Header ----
        title = self._font(52).render("ARENA DE TREINADORES", True, COL_ACCENT)
        screen.blit(title, title.get_rect(center=(vx + vw // 2, vy + 44)))

        line_w = title.get_width() + 80
        line_y = vy + 74
        pygame.draw.line(screen, (90, 80, 35),
                         (vx + vw // 2 - line_w // 2, line_y),
                         (vx + vw // 2 + line_w // 2, line_y), 2)

        sub = self._font(20).render(
            "Escolha formato, dificuldade e monte seu time",
            True, COL_TEXT_DIM)
        screen.blit(sub, sub.get_rect(center=(vx + vw // 2, vy + 92)))

        # ---- Botão sair ----
        pygame.draw.rect(screen, (60, 30, 35), self.back_btn, border_radius=10)
        pygame.draw.rect(screen, (170, 80, 90), self.back_btn, 2,
                         border_radius=10)
        bt = self._font(24).render("Sair", True, COL_TEXT)
        screen.blit(bt, bt.get_rect(center=self.back_btn.center))

        # ---- Painéis ----
        self._render_left_panel(screen)
        self._render_right_panel(screen)
        self._render_fight_button(screen)

        # ---- Hint inferior ----
        hint = self._font(14).render(
            "ESC = sair   ·   Clique nos pokémons para escolher/remover   ·   "
            "O treinador oponente é sorteado aleatoriamente",
            True, COL_TEXT_MUTED)
        screen.blit(hint, hint.get_rect(
            center=(vx + vw // 2, vy + vh - 14)))

        # ---- Dropdown ABERTO por cima de TUDO (última coisa) ----
        if self.difficulty_dropdown_open:
            self._render_difficulty_dropdown(screen)

    # ------------------------------------------------------------------
    def _render_left_panel(self, screen):
        rect = self._left_rect

        # Sombra
        shadow = rect.move(4, 4)
        ss = pygame.Surface((shadow.width, shadow.height), pygame.SRCALPHA)
        ss.fill((0, 0, 0, 100))
        screen.blit(ss, shadow)

        # Fundo
        pygame.draw.rect(screen, COL_PANEL, rect, border_radius=14)
        pygame.draw.rect(screen, COL_BORDER, rect, 1, border_radius=14)

        mouse = pygame.mouse.get_pos()
        blocked_by_dropdown = self.difficulty_dropdown_open

        # ---- Header FORMATO ----
        hdr = pygame.Rect(rect.x, rect.y, rect.width, 32)
        pygame.draw.rect(screen, (34, 40, 55), hdr,
                         border_top_left_radius=14,
                         border_top_right_radius=14)
        s = self._font(20).render("FORMATO", True, COL_ACCENT)
        screen.blit(s, (hdr.x + 16, hdr.y + 7))

        # ---- Cards de formato ----
        for i, row in enumerate(self._format_row_rects):
            mode = self.modes[i]
            selected = (i == self.selected_mode_idx)
            hover = (not blocked_by_dropdown) and row.collidepoint(mouse)

            if selected:
                bg, border = (62, 52, 100), (200, 180, 255)
            elif hover:
                bg, border = (40, 44, 62), (110, 120, 150)
            else:
                bg, border = (26, 30, 42), (48, 53, 68)

            # Glow pulsante quando selecionado
            if selected:
                pulse = 0.5 + 0.5 * math.sin(self._anim_time * 3.0)
                ga = int(60 + 60 * pulse)
                glow = pygame.Surface((row.width + 8, row.height + 8),
                                      pygame.SRCALPHA)
                pygame.draw.rect(glow, (200, 180, 255, ga),
                                 glow.get_rect(), border_radius=14)
                screen.blit(glow, (row.x - 4, row.y - 4))

            pygame.draw.rect(screen, bg, row, border_radius=12)
            pygame.draw.rect(screen, border, row,
                             2 if selected else 1, border_radius=12)

            # Badge grande (ex: "1v1")
            lbl = self._font(44).render(mode["label"], True, COL_ACCENT)
            lr = lbl.get_rect()
            lr.left = row.x + 20
            lr.centery = row.centery
            screen.blit(lbl, lr)

            # Subtítulo + descrição à direita do badge
            tx = lr.right + 22
            sub = self._font(22).render(mode["subtitle"], True, COL_TEXT)
            screen.blit(sub, (tx, row.y + 16))

            desc = self._font(15).render(mode["desc"], True, COL_TEXT_DIM)
            screen.blit(desc, (tx, row.y + 50))

            # Marcador de seleção à direita
            if selected:
                cx = row.right - 28
                cy = row.centery
                pygame.draw.circle(screen, (200, 180, 255), (cx, cy), 13)
                pygame.draw.lines(screen, (40, 30, 60), False,
                                  [(cx - 6, cy), (cx - 2, cy + 4),
                                   (cx + 6, cy - 6)], 3)

        # ---- Divisor ----
        div_y = self._diff_header_y - 8
        pygame.draw.line(screen, (55, 60, 85),
                         (rect.x + 16, div_y), (rect.right - 16, div_y), 1)

        # ---- Header DIFICULDADE ----
        s2 = self._font(20).render("DIFICULDADE", True, COL_ACCENT)
        screen.blit(s2, (rect.x + 16, self._diff_header_y))

        # ---- Botão do dropdown ----
        if self._diff_btn_rect:
            self._render_difficulty_button(screen, blocked_by_dropdown)

    # ------------------------------------------------------------------
    def _render_difficulty_button(self, screen, blocked_by_dropdown):
        rect = self._diff_btn_rect
        diff = self._get_selected_difficulty()
        if not diff:
            return

        mouse = pygame.mouse.get_pos()
        hover = (not blocked_by_dropdown) and rect.collidepoint(mouse)
        open_ = self.difficulty_dropdown_open

        # Fundo
        if open_ or hover:
            bg = (40, 46, 66)
            border = COL_BORDER_HL
        else:
            bg = (26, 30, 42)
            border = COL_BORDER

        pygame.draw.rect(screen, bg, rect, border_radius=10)
        pygame.draw.rect(screen, border, rect, 2, border_radius=10)

        # Barra lateral colorida (indicador visual limpo, sem barrinhas)
        bar_rect = pygame.Rect(rect.x + 4, rect.y + 8,
                               6, rect.height - 16)
        pygame.draw.rect(screen, diff["color"], bar_rect, border_radius=3)

        # Label grande, colorido pela dificuldade
        lbl = self._font(28).render(diff["label"], True, diff["color"])
        lbl_rect = lbl.get_rect()
        lbl_rect.left = rect.x + 24
        lbl_rect.centery = rect.centery
        screen.blit(lbl, lbl_rect)

        # Descrição curta à direita (truncada se precisar)
        desc_font = self._font(14)
        desc_txt = diff["desc"]
        arrow_w = 32
        max_desc_w = rect.right - lbl_rect.right - arrow_w - 24
        while desc_font.size(desc_txt)[0] > max_desc_w and len(desc_txt) > 6:
            desc_txt = desc_txt[:-1]
        if desc_txt != diff["desc"]:
            desc_txt = desc_txt[:-1].rstrip() + "..."
        desc_s = desc_font.render(desc_txt, True, COL_TEXT_MUTED)
        desc_rect = desc_s.get_rect()
        desc_rect.right = rect.right - arrow_w
        desc_rect.centery = rect.centery
        screen.blit(desc_s, desc_rect)

        # Seta (abre/fecha)
        cx = rect.right - 22
        cy = rect.centery
        if open_:
            pygame.draw.polygon(screen, COL_TEXT, [
                (cx - 8, cy + 3), (cx + 8, cy + 3), (cx, cy - 6),
            ])
        else:
            pygame.draw.polygon(screen, COL_TEXT, [
                (cx - 8, cy - 3), (cx + 8, cy - 3), (cx, cy + 6),
            ])

    # ------------------------------------------------------------------
    def _render_difficulty_dropdown(self, screen):
        """Renderiza o dropdown aberto. Deve ser chamado por último no render()."""
        if not self._diff_btn_rect:
            return

        # Opções desenhadas logo abaixo do botão
        opt_y = self._diff_btn_rect.bottom + 6
        opt_w = self._diff_btn_rect.width
        opt_x = self._diff_btn_rect.x

        self._diff_option_rects = []

        # Container (leve shadow + bg)
        total_h = len(self.difficulties) * self.DIFF_OPTION_H + 8
        container = pygame.Rect(opt_x - 2, opt_y - 2,
                                 opt_w + 4, total_h + 4)

        shadow = container.move(4, 6)
        ss = pygame.Surface((shadow.width, shadow.height), pygame.SRCALPHA)
        ss.fill((0, 0, 0, 130))
        screen.blit(ss, shadow)

        pygame.draw.rect(screen, (20, 24, 36), container, border_radius=12)
        pygame.draw.rect(screen, COL_BORDER_HL, container, 2, border_radius=12)

        mouse = pygame.mouse.get_pos()

        for i, d in enumerate(self.difficulties):
            row = pygame.Rect(
                opt_x + 2,
                opt_y + 2 + i * self.DIFF_OPTION_H,
                opt_w - 4,
                self.DIFF_OPTION_H - 4,
            )
            self._diff_option_rects.append(row)

            selected = (i == self.selected_difficulty_idx)
            hover = row.collidepoint(mouse)

            if selected:
                bg = (48, 42, 56)
            elif hover:
                bg = (44, 50, 72)
            else:
                bg = (30, 34, 46)

            pygame.draw.rect(screen, bg, row, border_radius=8)
            if selected:
                pygame.draw.rect(screen, d["color"], row, 2, border_radius=8)
            elif hover:
                pygame.draw.rect(screen, COL_BORDER_HL, row, 1,
                                 border_radius=8)

            # Barra lateral colorida
            b_rect = pygame.Rect(row.x + 5, row.y + 8, 5, row.height - 16)
            pygame.draw.rect(screen, d["color"], b_rect, border_radius=3)

            # Nome grande
            lbl = self._font(24).render(d["label"], True, d["color"])
            lr = lbl.get_rect()
            lr.left = row.x + 22
            lr.centery = row.centery - 9
            screen.blit(lbl, lr)

            # Descrição embaixo do nome
            desc = self._font(13).render(d["desc"], True, COL_TEXT_DIM)
            dr = desc.get_rect()
            dr.left = row.x + 22
            dr.top = lr.bottom + 3
            # Trunca se estourar
            max_w = row.right - dr.left - 40
            if desc.get_width() > max_w:
                txt = d["desc"]
                while self._font(13).size(txt + "...")[0] > max_w and len(txt) > 4:
                    txt = txt[:-1]
                desc = self._font(13).render(txt + "...", True, COL_TEXT_DIM)
            screen.blit(desc, dr)

            # Check à direita
            if selected:
                cx = row.right - 22
                cy = row.centery
                pygame.draw.circle(screen, d["color"], (cx, cy), 11)
                pygame.draw.lines(screen, (20, 30, 20), False,
                                  [(cx - 5, cy), (cx - 1, cy + 4),
                                   (cx + 5, cy - 5)], 2)

    # ------------------------------------------------------------------
    def _render_right_panel(self, screen):
        rect = self._right_rect

        # Sombra
        shadow = rect.move(4, 4)
        ss = pygame.Surface((shadow.width, shadow.height), pygame.SRCALPHA)
        ss.fill((0, 0, 0, 100))
        screen.blit(ss, shadow)

        # Fundo
        pygame.draw.rect(screen, COL_PANEL, rect, border_radius=14)
        pygame.draw.rect(screen, COL_BORDER, rect, 1, border_radius=14)

        mode = self._get_selected_mode()
        diff = self._get_selected_difficulty()
        if not mode or not diff:
            return

        # ---- Header ----
        y = rect.y + 18
        nm = self._font(30).render(mode["subtitle"], True, COL_ACCENT)
        screen.blit(nm, (rect.x + 22, y))
        y += 38

        tt = self._font(16).render(mode["desc"], True, COL_TEXT_DIM)
        screen.blit(tt, (rect.x + 22, y))
        y += 24

        pygame.draw.line(screen, (55, 60, 85),
                         (rect.x + 22, y), (rect.right - 22, y), 1)
        y += 14

        # ---- Dois chips: Formato · Dificuldade ----
        chip_gap = 10
        chip_h = 36

        # Chip 1: Formato
        cf = self._font(16)
        c1s = cf.render(f"Formato: {mode['label']}", True, COL_TEXT)
        chip1 = pygame.Rect(rect.x + 22, y, c1s.get_width() + 26, chip_h)
        pygame.draw.rect(screen, COL_PANEL_MED, chip1, border_radius=8)
        pygame.draw.rect(screen, COL_BORDER, chip1, 1, border_radius=8)
        screen.blit(c1s, c1s.get_rect(center=chip1.center))

        # Chip 2: Dificuldade (só texto colorido, sem ícone)
        chip2_x = chip1.right + chip_gap
        c2s = self._font(16).render(
            f"Dificuldade: {diff['label']}", True, diff["color"])
        chip2 = pygame.Rect(chip2_x, y, c2s.get_width() + 26, chip_h)
        pygame.draw.rect(screen, COL_PANEL_MED, chip2, border_radius=8)
        pygame.draw.rect(screen, COL_BORDER, chip2, 1, border_radius=8)
        screen.blit(c2s, c2s.get_rect(center=chip2.center))

        y += chip_h + 14

        # ---- Recompensa possível ----
        pool = pool_for(mode["chapter"], diff["key"])
        if pool:
            max_gold = max(t.get("reward_money", 0) for t in pool)
            max_xp = max(t.get("reward_xp", 0) for t in pool)
            rw = self._font(15).render(
                f"Recompensa possível: até {max_gold} de ouro  ·  {max_xp} de XP",
                True, COL_TEXT_MUTED)
            screen.blit(rw, (rect.x + 22, y))
            y += 24

        # ---- Aviso ----
        warn_box = pygame.Rect(rect.x + 22, y, rect.width - 44, 52)
        pygame.draw.rect(screen, (40, 34, 24), warn_box, border_radius=10)
        pygame.draw.rect(screen, (140, 110, 50), warn_box, 1, border_radius=10)
        w1 = self._font(15).render(
            "O treinador oponente é sorteado aleatoriamente.",
            True, (240, 210, 140))
        w2 = self._font(13).render(
            "O time dele fica oculto — prepare-se bem!",
            True, (200, 175, 120))
        screen.blit(w1, (warn_box.x + 14, warn_box.y + 8))
        screen.blit(w2, (warn_box.x + 14, warn_box.y + 28))
        y += 66

        pygame.draw.line(screen, (55, 60, 85),
                         (rect.x + 22, y), (rect.right - 22, y), 1)
        y += 14

        # ---- Título SEU TIME ----
        required = self._required_team_size()
        chosen = len(self.selected_poke_ids)
        color = COL_SUCCESS if chosen == required else COL_TEXT
        title_s = self._font(22).render(
            f"SEU TIME  ({chosen}/{required})", True, color)
        screen.blit(title_s, (rect.x + 22, y))

        # Hint à direita
        if chosen == required:
            hint_txt = "Time pronto!"
            hint_col = COL_SUCCESS
        elif chosen < required:
            hint_txt = f"Faltam {required - chosen} pokémon"
            hint_col = COL_ACCENT
        else:
            hint_txt = "Muitos pokémons"
            hint_col = COL_DANGER
        hint_s = self._font(14).render(hint_txt, True, hint_col)
        hr = hint_s.get_rect()
        hr.right = rect.right - 22
        hr.centery = title_s.get_rect(
            topleft=(rect.x + 22, y)).centery
        screen.blit(hint_s, hr)
        y += 32

        # Aviso se time pequeno
        team_size = len(self.game.player.team)
        if team_size < required:
            warn = self._font(14).render(
                f"Seu time tem apenas {team_size} pokémon(s) — "
                f"o formato {mode['label']} exige {required}.",
                True, COL_DANGER)
            screen.blit(warn, (rect.x + 22, y))
            y += 22

        # Atualiza posição da lista
        self._poke_rect.y = y
        self._poke_rect.height = max(60, rect.bottom - y - 20)

        self._render_player_pokemon_list(screen)

    # ------------------------------------------------------------------
    def _render_player_pokemon_list(self, screen):
        rect = self._poke_rect
        if rect.height < 40:
            return

        pygame.draw.rect(screen, COL_PANEL_DARK, rect, border_radius=10)
        pygame.draw.rect(screen, COL_BORDER, rect, 1, border_radius=10)

        if not self.player_entries:
            msg = self._font(18).render(
                "Nenhum Pokémon no seu time ativo.", True, COL_TEXT_MUTED)
            screen.blit(msg, msg.get_rect(center=rect.center))
            return

        clip = pygame.Rect(rect.x + 4, rect.y + 4,
                           rect.width - 8, rect.height - 8)
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
                rect.y + self.POKE_LIST_PAD_TOP + idx * self.ROW_POKE_H,
                rect.width - 16,
                self.ROW_POKE_H - 6,
            )
            entry = self.player_entries[i]
            selected = entry["unique_id"] in self.selected_poke_ids
            hover = row.collidepoint(mouse)

            # Fundo
            if selected:
                bg, border = ((COL_ITEM_SEL_HV, COL_SUCCESS) if hover
                              else (COL_ITEM_SEL, COL_SUCCESS))
            elif hover:
                bg, border = COL_ITEM_HOVER, COL_BORDER_HL
            else:
                bg, border = COL_ITEM, COL_BORDER

            # Glow pulsante
            if selected:
                pulse = 0.5 + 0.5 * math.sin(self._anim_time * 4.0)
                ga = int(40 + 40 * pulse)
                glow = pygame.Surface((row.width + 8, row.height + 8),
                                      pygame.SRCALPHA)
                pygame.draw.rect(glow, (COL_SUCCESS[0], COL_SUCCESS[1],
                                        COL_SUCCESS[2], ga),
                                 glow.get_rect(), border_radius=12)
                screen.blit(glow, (row.x - 4, row.y - 4))

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
                else:
                    ph = pygame.Rect(px, py, portrait_size, portrait_size)
                    pygame.draw.rect(screen, (50, 55, 75), ph, border_radius=8)
            except Exception:
                pass

            # Moldura
            frame_rect = pygame.Rect(px, py, portrait_size, portrait_size)
            frame_color = COL_ACCENT if entry["shiny"] else COL_BORDER_HL
            pygame.draw.rect(screen, frame_color, frame_rect, 2,
                             border_radius=8)

            # Nome + nível
            tx = px + portrait_size + 16
            name_color = COL_ACCENT if entry["shiny"] else COL_TEXT
            name_s = self._font(22).render(entry["name"], True, name_color)
            screen.blit(name_s, (tx, row.y + 8))

            lvl_s = self._font(16).render(f"Nível {entry['level']}",
                                          True, COL_TEXT_DIM)
            screen.blit(lvl_s, (tx, row.y + 36))

            # Type badges inline após o nível
            types_x = tx + lvl_s.get_width() + 14
            for t in entry["types"][:2]:
                w = self._draw_type_badge(screen, types_x,
                                          row.y + 37, t, font_size=13)
                types_x += w + 6

            # Check à direita
            cx = row.right - 26
            cy = row.centery
            if selected:
                pulse = 0.5 + 0.5 * math.sin(self._anim_time * 4.0)
                rr = 13 + int(2 * pulse)
                ga = int(80 + 80 * pulse)
                ring = pygame.Surface((rr * 2 + 6, rr * 2 + 6),
                                      pygame.SRCALPHA)
                pygame.draw.circle(ring, (COL_SUCCESS[0], COL_SUCCESS[1],
                                          COL_SUCCESS[2], ga),
                                   (rr + 3, rr + 3), rr, 2)
                screen.blit(ring, (cx - rr - 3, cy - rr - 3))

                pygame.draw.circle(screen, COL_SUCCESS, (cx, cy), 13)
                pygame.draw.lines(screen, (20, 30, 20), False,
                                  [(cx - 6, cy), (cx - 2, cy + 5),
                                   (cx + 6, cy - 6)], 3)
            elif hover:
                pygame.draw.circle(screen, (90, 100, 120), (cx, cy), 13, 2)

        screen.set_clip(old_clip)

        # Scrollbar
        if len(self.player_entries) > visible:
            self._draw_scrollbar(screen, rect, self.poke_scroll,
                                 visible, len(self.player_entries), 8)

    def _draw_scrollbar(self, screen, panel_rect, offset, visible, total,
                        header_h):
        bar_x = panel_rect.right - 9
        bar_top = panel_rect.y + header_h
        bar_h = panel_rect.height - header_h - 6
        if bar_h <= 0 or total <= 0:
            return
        thumb_h = max(24, int(bar_h * visible / total))
        max_s = max(1, total - visible)
        thumb_y = bar_top + int((bar_h - thumb_h) * offset / max_s)
        pygame.draw.rect(screen, (35, 38, 55), (bar_x, bar_top, 5, bar_h),
                         border_radius=3)
        pygame.draw.rect(screen, (140, 150, 190),
                         (bar_x, thumb_y, 5, thumb_h), border_radius=3)

    # ------------------------------------------------------------------
    def _render_fight_button(self, screen):
        mode = self._get_selected_mode()
        required = self._required_team_size() if mode else 1
        chosen = len(self.selected_poke_ids)
        can_fight = bool(mode) and chosen == required

        if can_fight:
            bg = (55, 130, 70)
            bg_hover = (90, 190, 110)
            border = COL_ACCENT
        else:
            bg = (55, 58, 68)
            bg_hover = bg
            border = (100, 105, 115)

        mouse = pygame.mouse.get_pos()
        hover = can_fight and self.fight_btn.collidepoint(mouse)
        color = bg_hover if hover else bg

        # Glow pulsante quando ativo
        if can_fight:
            pulse = 0.5 + 0.5 * math.sin(self._anim_time * 3.0)
            ga = int(50 + 60 * pulse)
            glow = pygame.Surface(
                (self.fight_btn.width + 12, self.fight_btn.height + 12),
                pygame.SRCALPHA)
            pygame.draw.rect(glow, (COL_ACCENT[0], COL_ACCENT[1],
                                    COL_ACCENT[2], ga),
                             glow.get_rect(), border_radius=20)
            screen.blit(glow, (self.fight_btn.x - 6, self.fight_btn.y - 6))

        # Sombra
        shadow = self.fight_btn.move(0, 5)
        ss = pygame.Surface((shadow.width, shadow.height), pygame.SRCALPHA)
        ss.fill((0, 0, 0, 120))
        screen.blit(ss, shadow)

        # Fundo
        pygame.draw.rect(screen, color, self.fight_btn, border_radius=18)
        pygame.draw.rect(screen, border, self.fight_btn, 3, border_radius=18)

        # Texto
        if not mode:
            label = "Escolha um formato"
        elif chosen < required:
            label = f"Escolha {required - chosen} pokémon"
        elif chosen > required:
            label = f"Remova {chosen - required} pokémon"
        else:
            label = "BATALHAR!"

        s = self._font(32).render(label, True, (255, 255, 255))
        s_shadow = self._font(32).render(label, True, (0, 0, 0))
        rect = s.get_rect(center=self.fight_btn.center)
        screen.blit(s_shadow, (rect.x + 2, rect.y + 2))
        screen.blit(s, rect)