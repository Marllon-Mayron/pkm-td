# src/scenes/npc_hall_scene/rename_dialog.py
"""
Diálogo do NPC_1 - Renomear Pokémon.
"""

import pygame

from src.data.pokedex import Pokedex
from src.managers.sounds.sound_manager import sound_manager, SoundEffect


class RenameDialog:
    """Diálogo para renomear um Pokémon do jogador."""

    ROW_H = 54

    def __init__(self, game, cost):
        self.game = game
        self.player = game.player
        self.cost = cost
        self.pokedex = Pokedex()

        self.visible = True
        self.success_message = ""

        # Pokemon list
        self.entries = []
        self._refresh_entries()

        self.selected_index = 0
        self.list_scroll = 0
        self.name_input = ""

        # Layout
        self.window = pygame.Rect(0, 0, 0, 0)
        self.list_rect = None
        self.form_rect = None
        self.confirm_btn = None
        self.cancel_btn = None
        self.input_rect = None

        # ===== SCROLLBAR DRAG (lista de pokemon) =====
        self._scrollbar_rect = None
        self._scrollbar_track_rect = None
        self._scrollbar_thumb_rect = None
        self._scroll_dragging = False
        self._scroll_thumb_offset = 0

        self._fonts = {}
        self._last_size = (0, 0)
        self._recalc_layout()

        # Pré-preenche com o apelido atual
        self._load_name_from_selection()

    # ==================================================================
    # FONTES / LAYOUT
    # ==================================================================
    def _get_font(self, size):
        size = max(10, int(size))
        if size not in self._fonts:
            self._fonts[size] = pygame.font.Font(None, size)
        return self._fonts[size]

    def _refresh_entries(self):
        self.entries = []
        for p in self.player.team:
            self.entries.append({
                "source": "team",
                "unique_id": p.unique_id,
                "display": p.get_display_name(),
                "species": p.name,
                "level": p.level,
                "id": p.id,
                "shiny": p.is_shiny,
                "custom_name": p.custom_name,
            })
        for d in self.player.pc_box:
            self.entries.append({
                "source": "box",
                "unique_id": d.get("unique_id"),
                "display": d.get("custom_name") or d.get("name", "?"),
                "species": d.get("name", "?"),
                "level": d.get("level", 1),
                "id": d.get("id", 1),
                "shiny": d.get("is_shiny", False),
                "custom_name": d.get("custom_name"),
            })

    def _recalc_layout(self):
        ww = self.game.screen_manager.window_width
        wh = self.game.screen_manager.window_height

        w = int(ww * 0.82)
        h = int(wh * 0.74)
        x = (ww - w) // 2
        y = (wh - h) // 2
        self.window = pygame.Rect(x, y, w, h)

        pad = 22
        header_h = 68

        # Painel esquerdo
        list_w = int(w * 0.46)
        self.list_rect = pygame.Rect(x + pad, y + header_h,
                                      list_w, h - header_h - pad)

        # Painel direito
        form_x = self.list_rect.right + pad
        form_w = w - (form_x - x) - pad
        self.form_rect = pygame.Rect(form_x, y + header_h,
                                      form_w, h - header_h - pad)

        # Botões
        bw = int(form_w * 0.42)
        bh = 46
        self.confirm_btn = pygame.Rect(
            self.form_rect.right - bw - 16,
            self.form_rect.bottom - bh - 16, bw, bh)
        self.cancel_btn = pygame.Rect(
            self.confirm_btn.x - bw - 12,
            self.confirm_btn.y, bw, bh)

        # Input
        self.input_rect = pygame.Rect(
            self.form_rect.x + 20, self.form_rect.y + 120,
            self.form_rect.width - 40, 52)

        # Fonts
        base = wh * 0.022
        self._fonts = {
            'title': pygame.font.Font(None, int(base * 1.6)),
            'medium': pygame.font.Font(None, int(base * 1.05)),
            'small': pygame.font.Font(None, int(base * 0.9)),
            'tiny': pygame.font.Font(None, int(base * 0.78)),
            'input': pygame.font.Font(None, int(base * 1.4)),
            'button': pygame.font.Font(None, int(base * 1.05)),
        }

    def _check_resize(self):
        cur = (self.game.screen_manager.window_width,
               self.game.screen_manager.window_height)
        if cur != self._last_size:
            self._last_size = cur
            self._recalc_layout()
            return True
        return False

    def _visible_rows(self):
        if not self.list_rect:
            return 8
        return max(1, (self.list_rect.height - 40) // self.ROW_H)

    # ==================================================================
    # SCROLLBAR DRAG
    # ==================================================================
    def _begin_scroll_drag(self, mouse_pos):
        thumb = self._scrollbar_thumb_rect
        if thumb and thumb.collidepoint(mouse_pos):
            self._scroll_thumb_offset = mouse_pos[1] - thumb.y
        else:
            self._scroll_thumb_offset = max(1, thumb.height // 2 if thumb else 10)
            self._update_scroll_from_mouse(mouse_pos[1])
        self._scroll_dragging = True

    def _update_scroll_from_mouse(self, mouse_y):
        track = self._scrollbar_track_rect
        thumb = self._scrollbar_thumb_rect
        if not track or not thumb:
            return
        thumb_h = thumb.height
        track_y = track.y
        track_h = track.height
        track_max = max(1, track_h - thumb_h)

        desired_y = mouse_y - self._scroll_thumb_offset
        desired_y = max(track_y, min(track_y + track_max, desired_y))

        ratio = (desired_y - track_y) / track_max
        max_scroll = max(0, len(self.entries) - self._visible_rows())
        self.list_scroll = max(0, min(max_scroll, int(round(ratio * max_scroll))))

    def _get_selected(self):
        if 0 <= self.selected_index < len(self.entries):
            return self.entries[self.selected_index]
        return None

    def _load_name_from_selection(self):
        entry = self._get_selected()
        if entry:
            self.name_input = entry.get("custom_name") or ""

    # ==================================================================
    # EVENTOS
    # ==================================================================
    def close(self):
        self.visible = False

    def handle_event(self, event):
        self._check_resize()

        # ===== DRAG ATIVO (prioridade maxima) =====
        if self._scroll_dragging:
            if event.type == pygame.MOUSEMOTION:
                self._update_scroll_from_mouse(event.pos[1])
                return None
            if event.type == pygame.MOUSEBUTTONUP and event.button == 1:
                self._scroll_dragging = False
                return None
            if event.type == pygame.MOUSEBUTTONDOWN:
                return None

        # ===== TECLADO =====
        if event.type == pygame.KEYDOWN:
            if event.key == pygame.K_ESCAPE:
                return "close"
            if event.key == pygame.K_RETURN:
                return self._try_confirm()
            if event.key == pygame.K_BACKSPACE:
                self.name_input = self.name_input[:-1]
                return None
            if event.unicode and event.unicode.isprintable():
                if len(self.name_input) < 20:
                    self.name_input += event.unicode
            return None

        # ===== SCROLL WHEEL =====
        if event.type == pygame.MOUSEWHEEL:
            mx, my = pygame.mouse.get_pos()
            if self.list_rect and self.list_rect.collidepoint(mx, my):
                max_s = max(0, len(self.entries) - self._visible_rows())
                self.list_scroll = max(0, min(max_s, self.list_scroll - event.y))
            return None

        # ===== CLICK =====
        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            # Cancelar
            if self.cancel_btn and self.cancel_btn.collidepoint(event.pos):
                return "close"

            # Confirmar
            if self.confirm_btn and self.confirm_btn.collidepoint(event.pos):
                return self._try_confirm()

            # ===== SCROLLBAR DRAG (checa ANTES da lista) =====
            if self._scrollbar_rect and self._scrollbar_rect.collidepoint(event.pos):
                self._begin_scroll_drag(event.pos)
                return None

            # Lista de Pokémon
            if self.list_rect and self.list_rect.collidepoint(event.pos):
                rel_y = event.pos[1] - self.list_rect.y - 40
                if rel_y >= 0:
                    idx = self.list_scroll + rel_y // self.ROW_H
                    if 0 <= idx < len(self.entries):
                        self.selected_index = idx
                        self._load_name_from_selection()
                        sound_manager.play_effect(SoundEffect.CLICK, volume=0.2)
                return None

        return None

    # ==================================================================
    # AÇÃO
    # ==================================================================
    def _try_confirm(self):
        entry = self._get_selected()
        if not entry:
            return None

        new_name = self.name_input.strip()
        if not new_name:
            return None

        if self.player.money < self.cost:
            self.success_message = "Gold insuficiente!"
            return None

        try:
            if entry["source"] == "team":
                # Obter instância real
                p = self.player.get_pokemon_instance(entry["unique_id"])
                if p:
                    p.custom_name = new_name
            else:
                # Atualiza dict da box
                for d in self.player.pc_box:
                    if d.get("unique_id") == entry["unique_id"]:
                        d["custom_name"] = new_name
                        break
                # Atualiza cache se existir
                uid = entry["unique_id"]
                if uid in self.player._pokemon_cache:
                    self.player._pokemon_cache[uid].custom_name = new_name
        except Exception as e:
            print(f"[NPC_HALL] Erro ao renomear: {e}")
            return None

        # Cobra o gold
        self.player.money -= self.cost

        # Salva
        try:
            self.player.auto_save()
        except Exception as e:
            print(f"[NPC_HALL] Erro ao salvar: {e}")

        self.success_message = f"Pokémon renomeado para '{new_name}'!"
        sound_manager.play_effect(SoundEffect.LEVELUP)
        return "success"

    def fixed_update(self, dt):
        pass

    # ==================================================================
    # RENDER
    # ==================================================================
    def render(self, screen):
        self._check_resize()

        # Overlay
        ov = pygame.Surface((self.game.screen_manager.window_width,
                             self.game.screen_manager.window_height))
        ov.set_alpha(210)
        ov.fill((0, 0, 0))
        screen.blit(ov, (0, 0))

        # Janela
        pygame.draw.rect(screen, (20, 24, 34), self.window, border_radius=14)
        pygame.draw.rect(screen, (140, 120, 60), self.window, 3, border_radius=14)
        pygame.draw.rect(screen, (60, 55, 40), self.window.inflate(-8, -8),
                         1, border_radius=12)

        # Header
        title_s = self._fonts['title'].render("RENOMEAR POKÉMON", True,
                                              (255, 220, 120))
        screen.blit(title_s, (self.window.centerx - title_s.get_width() // 2,
                              self.window.y + 20))

        cost_s = self._fonts['small'].render(
            f"Custo: {self.cost} G   ·   Você tem: {self.player.money} G",
            True, (200, 200, 210))
        screen.blit(cost_s, (self.window.centerx - cost_s.get_width() // 2,
                             self.window.y + 20 + title_s.get_height() + 4))

        self._render_list(screen)
        self._render_form(screen)
        self._render_buttons(screen)

    def _render_list(self, screen):
        if not self.list_rect:
            return

        pygame.draw.rect(screen, (16, 20, 28), self.list_rect, border_radius=8)
        pygame.draw.rect(screen, (70, 80, 105), self.list_rect, 2, border_radius=8)

        hdr = pygame.Rect(self.list_rect.x, self.list_rect.y,
                          self.list_rect.width, 36)
        pygame.draw.rect(screen, (34, 40, 55), hdr,
                         border_top_left_radius=8, border_top_right_radius=8)
        hdr_s = self._fonts['small'].render("SEUS POKÉMON", True, (180, 190, 215))
        screen.blit(hdr_s, (hdr.x + 12, hdr.y + 8))

        # ===== Scrollbar geometry (calculada ANTES do loop) =====
        visible = self._visible_rows()
        has_scrollbar = len(self.entries) > visible

        bar_w = 12
        bar_gap_right = 6
        bar_x = self.list_rect.right - bar_w - bar_gap_right
        bar_top = self.list_rect.y + 40
        bar_h = self.list_rect.height - 44

        # Margem reservada à direita (Lv.XX e #ID ficam ANTES da barra)
        right_reserve = (bar_w + bar_gap_right + 8) if has_scrollbar else 12

        old_clip = screen.get_clip()
        clip = pygame.Rect(self.list_rect.x + 4, self.list_rect.y + 36,
                           self.list_rect.width - 8, self.list_rect.height - 40)
        screen.set_clip(clip)

        start = self.list_scroll
        end = min(len(self.entries), start + visible)
        mouse = pygame.mouse.get_pos()

        for i in range(start, end):
            idx = i - start
            row = pygame.Rect(self.list_rect.x + 4,
                              self.list_rect.y + 40 + idx * self.ROW_H,
                              self.list_rect.width - 8, self.ROW_H - 2)

            entry = self.entries[i]
            selected = (i == self.selected_index)
            hovered = row.collidepoint(mouse)

            if selected:
                bg = (62, 52, 100);
                border = (200, 180, 255)
            elif hovered:
                bg = (40, 44, 62);
                border = (100, 110, 140)
            else:
                bg = (26, 30, 42);
                border = (48, 53, 68)

            pygame.draw.rect(screen, bg, row, border_radius=6)
            pygame.draw.rect(screen, border, row, 1, border_radius=6)

            # Sprite
            try:
                sp = self.pokedex.get_portrait(entry["id"], "normal", entry["shiny"])
                if sp:
                    sc = pygame.transform.smoothscale(sp, (40, 40))
                    screen.blit(sc, (row.x + 8, row.y + 7))
            except Exception:
                pass

            # Texto
            src_tag = "[TIME]" if entry["source"] == "team" else "[BOX]"
            f = self._fonts['medium']
            color = (255, 255, 255) if selected else (220, 220, 235)
            s = f.render(f"{src_tag}  {entry['display']}", True, color)
            screen.blit(s, (row.x + 58, row.y + 6))

            sp_js = self._fonts['small'].render(
                f"Espécie: {entry['species']}", True, (160, 170, 195))
            screen.blit(sp_js, (row.x + 58, row.y + 28))

            # Lv e ID deslocados para NÃO invadir a scrollbar
            lv_s = self._fonts['small'].render(f"Lv.{entry['level']}", True,
                                               (255, 220, 120))
            screen.blit(lv_s, (row.right - right_reserve - lv_s.get_width(),
                               row.y + 8))

            id_s = self._fonts['tiny'].render(f"#{entry['id']:04d}", True,
                                              (130, 140, 170))
            screen.blit(id_s, (row.right - right_reserve - id_s.get_width(),
                               row.y + 30))

        screen.set_clip(old_clip)

        # ===== Scrollbar =====
        if has_scrollbar:
            thumb_h = max(40, int(bar_h * visible / len(self.entries)))
            max_s = max(1, len(self.entries) - visible)
            thumb_y = bar_top + int((bar_h - thumb_h) * self.list_scroll / max_s)

            pygame.draw.rect(screen, (35, 38, 55),
                             (bar_x, bar_top, bar_w, bar_h), border_radius=6)
            thumb_color = (180, 190, 230) if self._scroll_dragging else (120, 130, 170)
            pygame.draw.rect(screen, thumb_color,
                             (bar_x, thumb_y, bar_w, thumb_h), border_radius=6)

            self._scrollbar_track_rect = pygame.Rect(bar_x, bar_top, bar_w, bar_h)
            self._scrollbar_thumb_rect = pygame.Rect(bar_x, thumb_y, bar_w, thumb_h)
            self._scrollbar_rect = pygame.Rect(
                bar_x - 10, bar_top, bar_w + 16, bar_h)
        else:
            self._scrollbar_rect = None
            self._scrollbar_track_rect = None
            self._scrollbar_thumb_rect = None

    def _render_form(self, screen):
        if not self.form_rect:
            return

        pygame.draw.rect(screen, (16, 20, 28), self.form_rect, border_radius=8)
        pygame.draw.rect(screen, (70, 80, 105), self.form_rect, 2, border_radius=8)

        entry = self._get_selected()
        if not entry:
            f = self._fonts['medium']
            s = f.render("Selecione um Pokémon", True, (160, 170, 190))
            screen.blit(s, (self.form_rect.centerx - s.get_width() // 2,
                            self.form_rect.centery - s.get_height() // 2))
            return

        y = self.form_rect.y + 20
        pad = 20

        # Nome atual
        lbl = self._fonts['tiny'].render("NOME ATUAL", True, (140, 150, 185))
        screen.blit(lbl, (self.form_rect.x + pad, y))
        y += lbl.get_height() + 4

        cur_name = entry.get("custom_name") or f"(sem apelido — {entry['species']})"
        cur_s = self._fonts['medium'].render(cur_name, True, (255, 200, 120))
        screen.blit(cur_s, (self.form_rect.x + pad, y))
        y += cur_s.get_height() + 16

        # Novo nome
        lbl = self._fonts['tiny'].render("NOVO NOME", True, (140, 150, 185))
        screen.blit(lbl, (self.form_rect.x + pad, y))

        # Ajusta input_rect.y para alinhar
        self.input_rect.y = y + lbl.get_height() + 6

        pygame.draw.rect(screen, (12, 15, 22), self.input_rect, border_radius=6)
        pygame.draw.rect(screen, (200, 170, 90), self.input_rect, 2,
                         border_radius=6)

        display = self.name_input if self.name_input else ""
        display += "_"  # cursor

        isf = self._fonts['input']
        is_ = isf.render(display, True, (240, 240, 250))
        screen.blit(is_, (self.input_rect.x + 12,
                          self.input_rect.centery - is_.get_height() // 2))

        y = self.input_rect.bottom + 8

        # Hint
        hint_s = self._fonts['tiny'].render(
            "Máx. 20 caracteres  ·  O apelido antigo é pré-preenchido",
            True, (130, 140, 170))
        screen.blit(hint_s, (self.form_rect.x + pad, y))
        y += hint_s.get_height() + 16

        # Prévia
        lbl = self._fonts['tiny'].render("PRÉVIA", True, (140, 150, 185))
        screen.blit(lbl, (self.form_rect.x + pad, y))
        y += lbl.get_height() + 6

        prev_rect = pygame.Rect(self.form_rect.x + pad, y,
                                 self.form_rect.width - pad * 2, 92)
        pygame.draw.rect(screen, (22, 27, 38), prev_rect, border_radius=8)
        pygame.draw.rect(screen, (80, 90, 120), prev_rect, 1, border_radius=8)

        try:
            sp = self.pokedex.get_portrait(entry["id"], "normal", entry["shiny"])
            if sp:
                sc = pygame.transform.smoothscale(sp, (64, 64))
                screen.blit(sc, (prev_rect.x + 14, prev_rect.y + 14))
        except Exception:
            pass

        display_name = self.name_input.strip() or entry["species"]
        pf = self._fonts['medium']
        ps = pf.render(display_name, True, (255, 255, 255))
        screen.blit(ps, (prev_rect.x + 92, prev_rect.y + 20))

        sub_s = self._fonts['small'].render(
            f"Lv.{entry['level']}  ·  #{entry['id']:04d}",
            True, (180, 190, 210))
        screen.blit(sub_s, (prev_rect.x + 92, prev_rect.y + 48))

    def _render_buttons(self, screen):
        # Confirm
        can_confirm = (self._get_selected()
                       and self.name_input.strip()
                       and self.player.money >= self.cost)

        if can_confirm:
            bg = (55, 130, 70); border = (120, 220, 140)
        else:
            bg = (55, 58, 68); border = (100, 105, 115)

        pygame.draw.rect(screen, bg, self.confirm_btn, border_radius=8)
        pygame.draw.rect(screen, border, self.confirm_btn, 2, border_radius=8)
        cf = self._fonts['button']
        label = f"CONFIRMAR ({self.cost} G)"
        cs = cf.render(label, True, (255, 255, 255))
        screen.blit(cs, cs.get_rect(center=self.confirm_btn.center))

        # Cancel
        pygame.draw.rect(screen, (120, 55, 55), self.cancel_btn, border_radius=8)
        pygame.draw.rect(screen, (220, 100, 100), self.cancel_btn, 2,
                         border_radius=8)
        cs2 = cf.render("CANCELAR", True, (255, 255, 255))
        screen.blit(cs2, cs2.get_rect(center=self.cancel_btn.center))