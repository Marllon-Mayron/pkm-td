# src/scenes/npc_hall_scene/relearn_dialog.py
"""
Diálogo do NPC_2 - Reaprender movimentos.

Mostra comparação lado a lado entre o NOVO golpe selecionado e o
golpe ATUAL no slot de destino. Inclui descrição completa de ambos
para o jogador decidir com informação.
"""

import pygame

from src.data.pokedex import Pokedex
from src.data.move_data import MoveData
from src.entities.move import Move
from src.managers.sounds.sound_manager import sound_manager, SoundEffect


# =========================================================================
# HELPERS
# =========================================================================
_PT_TYPE = {
    'normal': 'Normal', 'fire': 'Fogo', 'water': 'Agua',
    'electric': 'Eletrico', 'grass': 'Planta', 'ice': 'Gelo',
    'fighting': 'Lutador', 'poison': 'Venenoso', 'ground': 'Terra',
    'flying': 'Voador', 'psychic': 'Psiquico', 'bug': 'Inseto',
    'rock': 'Pedra', 'ghost': 'Fantasma', 'dragon': 'Dragao',
    'dark': 'Sombrio', 'steel': 'Aco', 'fairy': 'Fada',
}

_CATEGORY_PT = {
    'physical': ('FISICO', (255, 175, 90)),
    'special':  ('ESPECIAL', (110, 180, 250)),
    'status':   ('STATUS', (180, 190, 200)),
}


def _sanitize(text):
    if text is None:
        return ""
    import unicodedata
    nfkd = unicodedata.normalize('NFKD', str(text))
    return nfkd.encode('ASCII', 'ignore').decode('ASCII')


# =========================================================================
# DIALOG
# =========================================================================
class RelearnDialog:
    """Diálogo para fazer um Pokémon reaprender um golpe."""

    POKE_ROW_H_BASE = 62
    MOVE_ROW_H_BASE = 58

    def __init__(self, game, cost):
        self.game = game
        self.player = game.player
        self.cost = cost
        self.pokedex = Pokedex()
        self.move_data = MoveData()

        self.visible = True
        self.success_message = ""

        # Lista de Pokémon
        self.entries = []
        self._refresh_entries()

        self.selected_poke_idx = 0
        self.pokemon_scroll = 0

        # Golpes reaprendíveis
        self.learnable_moves = []
        self.selected_move_idx = -1
        self.move_scroll = 0

        # Slot de destino
        self.target_slot = -1

        # Layout
        self.window = pygame.Rect(0, 0, 0, 0)
        self.poke_rect = None
        self.moves_rect = None
        self.detail_rect = None
        self.detail_left = None
        self.detail_right = None
        self.slots_rect = None
        self.confirm_btn = None
        self.cancel_btn = None
        self.slot_buttons = []

        # ===== SCROLLBAR DRAG (lista de pokemon) =====
        self._poke_scrollbar_rect = None
        self._poke_scrollbar_track_rect = None
        self._poke_scrollbar_thumb_rect = None
        self._poke_scroll_dragging = False
        self._poke_scroll_thumb_offset = 0

        # ===== SCROLLBAR DRAG (lista de moves) =====
        self._move_scrollbar_rect = None
        self._move_scrollbar_track_rect = None
        self._move_scrollbar_thumb_rect = None
        self._move_scroll_dragging = False
        self._move_scroll_thumb_offset = 0

        self._fonts = {}
        self._last_size = (0, 0)

        # Cache de descrição
        self._desc_cache = {}

        self._recalc_layout()
        self._refresh_learnable_moves()

    # ==================================================================
    # FONTES / LAYOUT
    # ==================================================================
    def _get_font(self, size):
        size = max(10, int(size))
        if size not in self._fonts:
            self._fonts[size] = pygame.font.Font(None, size)
        return self._fonts[size]

    def _refresh_entries(self):
        """
        Popula a lista de Pokémon do time + box, SEM duplicatas.

        O save manager salva o time dentro da pc_box também (mesmos
        unique_ids). Filtramos os que já estão no time para não duplicar
        a exibição.
        """
        self.entries = []

        # ===== TIME =====
        team_ids = set()
        for p in self.player.team:
            team_ids.add(p.unique_id)
            self.entries.append({
                "source": "team",
                "unique_id": p.unique_id,
                "display": p.get_display_name(),
                "species": p.name,
                "level": p.level,
                "id": p.id,
                "shiny": p.is_shiny,
                # RenameDialog também usa:
                "custom_name": getattr(p, "custom_name", None),
            })

        # ===== BOX (filtra quem já está no time) =====
        for d in self.player.pc_box:
            uid = d.get("unique_id")
            if not uid:
                continue
            if uid in team_ids:
                continue
            self.entries.append({
                "source": "box",
                "unique_id": uid,
                "display": d.get("custom_name") or d.get("name", "?"),
                "species": d.get("name", "?"),
                "level": d.get("level", 1),
                "id": d.get("id", 1),
                "shiny": d.get("is_shiny", False),
                # RenameDialog também usa:
                "custom_name": d.get("custom_name"),
            })

    def _recalc_layout(self):
        ww = self.game.screen_manager.window_width
        wh = self.game.screen_manager.window_height

        w = int(ww * 0.94)
        h = int(wh * 0.90)
        x = (ww - w) // 2
        y = (wh - h) // 2
        self.window = pygame.Rect(x, y, w, h)

        pad = 22
        header_h = 82

        # ===== Painel esquerdo: lista de Pokémon =====
        left_w = int(w * 0.26)
        self.poke_rect = pygame.Rect(
            x + pad, y + header_h, left_w, h - header_h - pad)

        # ===== Coluna direita =====
        right_x = self.poke_rect.right + pad
        right_w = w - (right_x - x) - pad
        right_h = h - header_h - pad
        right_y = y + header_h

        # Proporções verticais:
        # 34% golpes · 42% comparação · 24% slots
        gap_v = 12
        moves_h = int((right_h - gap_v * 2) * 0.34)
        detail_h = int((right_h - gap_v * 2) * 0.42)
        slots_h = right_h - moves_h - detail_h - gap_v * 2

        self.moves_rect = pygame.Rect(right_x, right_y, right_w, moves_h)
        self.detail_rect = pygame.Rect(
            right_x, self.moves_rect.bottom + gap_v, right_w, detail_h)
        self.slots_rect = pygame.Rect(
            right_x, self.detail_rect.bottom + gap_v, right_w, slots_h)

        # ===== Sub-painéis do detail =====
        d_pad = 14
        d_gap = 14
        half_w = (self.detail_rect.width - d_pad * 2 - d_gap) // 2
        inner_y = self.detail_rect.y + 44
        inner_h = self.detail_rect.height - 44 - d_pad

        self.detail_left = pygame.Rect(
            self.detail_rect.x + d_pad, inner_y, half_w, inner_h)
        self.detail_right = pygame.Rect(
            self.detail_left.right + d_gap, inner_y, half_w, inner_h)

        # ===== Slots =====
        num_slots = 4
        slot_gap = 12
        slot_pad = 16
        slot_top = 42
        slot_h = max(56, self.slots_rect.height - slot_top - 74)
        slot_w = (self.slots_rect.width - slot_pad * 2
                  - slot_gap * (num_slots - 1)) // num_slots

        self.slot_buttons = []
        for i in range(num_slots):
            sx = self.slots_rect.x + slot_pad + i * (slot_w + slot_gap)
            self.slot_buttons.append(pygame.Rect(
                sx, self.slots_rect.y + slot_top, slot_w, slot_h))

        # ===== Botões =====
        bw = int(self.slots_rect.width * 0.22)
        bh = 46
        self.confirm_btn = pygame.Rect(
            self.slots_rect.right - bw - 16,
            self.slots_rect.bottom - bh - 14, bw, bh)
        self.cancel_btn = pygame.Rect(
            self.confirm_btn.x - bw - 12,
            self.confirm_btn.y, bw, bh)

        # ===== Fonts responsivas =====
        base = wh * 0.022
        self._fonts = {
            'title':      pygame.font.Font(None, int(base * 1.7)),
            'subtitle':   pygame.font.Font(None, int(base * 0.95)),
            'section':    pygame.font.Font(None, int(base * 1.05)),
            'medium':     pygame.font.Font(None, int(base * 1.05)),
            'small':      pygame.font.Font(None, int(base * 0.92)),
            'tiny':       pygame.font.Font(None, int(base * 0.80)),
            'desc':       pygame.font.Font(None, int(base * 0.94)),
            'button':     pygame.font.Font(None, int(base * 1.08)),
            'move_name':  pygame.font.Font(None, int(base * 1.15)),
            'detail_name': pygame.font.Font(None, int(base * 1.30)),
            'detail_val': pygame.font.Font(None, int(base * 1.10)),
        }

    def _check_resize(self):
        cur = (self.game.screen_manager.window_width,
               self.game.screen_manager.window_height)
        if cur != self._last_size:
            self._last_size = cur
            self._recalc_layout()
            return True
        return False

    # ==================================================================
    # HELPERS
    # ==================================================================
    def _get_selected_pokemon_entry(self):
        if 0 <= self.selected_poke_idx < len(self.entries):
            return self.entries[self.selected_poke_idx]
        return None

    def _get_pokemon_instance(self):
        entry = self._get_selected_pokemon_entry()
        if not entry:
            return None
        return self.player.get_pokemon_instance(entry["unique_id"])

    def _visible_poke_rows(self):
        if not self.poke_rect:
            return 8
        return max(1, (self.poke_rect.height - 44) // self.POKE_ROW_H_BASE)

    def _visible_move_rows(self):
        if not self.moves_rect:
            return 6
        return max(1, (self.moves_rect.height - 44) // self.MOVE_ROW_H_BASE)

    def _get_selected_move(self):
        if 0 <= self.selected_move_idx < len(self.learnable_moves):
            return self.learnable_moves[self.selected_move_idx]
        return None

    def _get_target_slot_move(self):
        """Retorna o Move atualmente equipado no slot alvo (ou None)."""
        if self.target_slot < 0:
            return None
        pokemon = self._get_pokemon_instance()
        if not pokemon:
            return None
        if self.target_slot < len(pokemon.moves):
            return pokemon.moves[self.target_slot]
        return None

    def _refresh_learnable_moves(self):
        """Popula a lista de golpes reaprendíveis considerando pré-evoluções."""
        self.learnable_moves = []
        self.selected_move_idx = -1
        self.move_scroll = 0
        self.target_slot = -1

        pokemon = self._get_pokemon_instance()
        if not pokemon:
            return

        # ===== NOVO: pega golpes de TODA a família (pré-evoluções + atual) =====
        all_moves = self._get_family_moves_at_level(pokemon.id, pokemon.level)

        current_lower = {m.name.lower() for m in pokemon.moves}

        for name in all_moves:
            if name.lower() in current_lower:
                continue
            info = self.move_data.get_move_info(name)
            if info:
                self.learnable_moves.append({"name": name, "info": info})

    # ==================================================================
    # FAMÍLIA EVOLUTIVA
    # ==================================================================
    def _get_family_moves_at_level(self, pokemon_id, level):
        """
        Retorna todos os golpes que o Pokémon pode ter aprendido por level-up
        considerando sua cadeia de pré-evoluções.

        Funciona como o Move Reminder real: um Pokémon evoluído ainda pode
        reaprender qualquer golpe que suas pré-evoluções aprendiam até o
        nível atual.

        Ex.: Butterfree Lv.20 pode reaprender Tackle e String Shot do
        Caterpie, mesmo sendo uma espécie diferente.
        """
        chain = self._get_species_pre_evolution_chain(pokemon_id)
        seen = set()
        result = []

        for species_id in chain:
            try:
                moves = self.move_data.get_moves_at_level(species_id, level)
            except Exception as e:
                print(f"[RELEARN] Erro ao pegar moves de #{species_id}: {e}")
                moves = []

            for move_name in moves:
                key = move_name.lower()
                if key in seen:
                    continue
                seen.add(key)
                result.append(move_name)

        return result

    def _get_species_pre_evolution_chain(self, pokemon_id):
        """
        Retorna a lista de IDs da cadeia evolutiva até (e incluindo) o
        Pokémon alvo, ordenada da forma mais básica até a mais evoluída.

        Prioridade:
          1) Usa `family_members` do pokedex (dados exatos do JSON)
          2) Fallback: caminha pelo `evolves_from` (subindo a corrente)
          3) Fallback final: retorna apenas o próprio pokemon_id
        """
        try:
            data = self.pokedex.get_pokemon(pokemon_id)
        except Exception:
            data = None

        if not data:
            return [pokemon_id]

        evo = data.get("evolution") or {}

        # ----- Tentativa 1: family_members (ordenado do mais básico ao final) -----
        fam = evo.get("family_members") or []
        family_ids = [
            m.get("id") for m in fam
            if isinstance(m, dict) and m.get("id")
        ]
        if family_ids and pokemon_id in family_ids:
            idx = family_ids.index(pokemon_id)
            return family_ids[:idx + 1]

        # ----- Tentativa 2: sobe pelo evolves_from -----
        chain = [pokemon_id]
        current_id = pokemon_id
        visited = {pokemon_id}

        for _ in range(10):  # sanity limit (cadeias gen 1-5 nunca passam de 3)
            try:
                cur_data = self.pokedex.get_pokemon(current_id)
            except Exception:
                break
            if not cur_data:
                break

            prev = (cur_data.get("evolution") or {}).get("evolves_from")
            if not prev or not isinstance(prev, dict) or not prev.get("id"):
                break

            prev_id = prev["id"]
            if prev_id in visited:
                break

            visited.add(prev_id)
            chain.insert(0, prev_id)
            current_id = prev_id

        return chain

    def _get_move_description(self, move_name, move_info=None):
        if move_name in self._desc_cache:
            return self._desc_cache[move_name]

        desc = None
        try:
            from src.battle.effects.effect_factory import EffectFactory
            key = move_name.lower().replace(" ", "-").replace("'", "")
            ef = EffectFactory.create_effect(key)
            if ef and getattr(ef, 'description', None):
                desc = ef.description
            if not desc:
                cfg = EffectFactory.MOVE_EFFECTS.get(key)
                if cfg and cfg.get("description"):
                    desc = cfg["description"]
        except Exception:
            pass

        if not desc and move_info:
            d = move_info.get("description")
            if d and not d.startswith(f"Usa {move_name}"):
                desc = d

        if not desc:
            desc = "Um movimento que causa dano ao oponente."

        desc = _sanitize(desc)
        self._desc_cache[move_name] = desc
        return desc

    def _wrap_text(self, text, font, max_w):
        words = text.split()
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
        return lines or [""]

    # ==================================================================
    # SCROLLBAR DRAG (pokemon list)
    # ==================================================================
    def _begin_poke_scroll_drag(self, mouse_pos):
        thumb = self._poke_scrollbar_thumb_rect
        if thumb and thumb.collidepoint(mouse_pos):
            self._poke_scroll_thumb_offset = mouse_pos[1] - thumb.y
        else:
            self._poke_scroll_thumb_offset = max(1, thumb.height // 2 if thumb else 10)
            self._update_poke_scroll_from_mouse(mouse_pos[1])
        self._poke_scroll_dragging = True

    def _update_poke_scroll_from_mouse(self, mouse_y):
        track = self._poke_scrollbar_track_rect
        thumb = self._poke_scrollbar_thumb_rect
        if not track or not thumb:
            return
        thumb_h = thumb.height
        track_y = track.y
        track_h = track.height
        track_max = max(1, track_h - thumb_h)

        desired_y = mouse_y - self._poke_scroll_thumb_offset
        desired_y = max(track_y, min(track_y + track_max, desired_y))

        ratio = (desired_y - track_y) / track_max
        max_scroll = max(0, len(self.entries) - self._visible_poke_rows())
        self.pokemon_scroll = max(0, min(max_scroll, int(round(ratio * max_scroll))))

    # ==================================================================
    # SCROLLBAR DRAG (moves list)
    # ==================================================================
    def _begin_move_scroll_drag(self, mouse_pos):
        thumb = self._move_scrollbar_thumb_rect
        if thumb and thumb.collidepoint(mouse_pos):
            self._move_scroll_thumb_offset = mouse_pos[1] - thumb.y
        else:
            self._move_scroll_thumb_offset = max(1, thumb.height // 2 if thumb else 10)
            self._update_move_scroll_from_mouse(mouse_pos[1])
        self._move_scroll_dragging = True

    def _update_move_scroll_from_mouse(self, mouse_y):
        track = self._move_scrollbar_track_rect
        thumb = self._move_scrollbar_thumb_rect
        if not track or not thumb:
            return
        thumb_h = thumb.height
        track_y = track.y
        track_h = track.height
        track_max = max(1, track_h - thumb_h)

        desired_y = mouse_y - self._move_scroll_thumb_offset
        desired_y = max(track_y, min(track_y + track_max, desired_y))

        ratio = (desired_y - track_y) / track_max
        max_scroll = max(0, len(self.learnable_moves) - self._visible_move_rows())
        self.move_scroll = max(0, min(max_scroll, int(round(ratio * max_scroll))))

    # ==================================================================
    # EVENTOS
    # ==================================================================
    def close(self):
        self.visible = False

    def handle_event(self, event):
        self._check_resize()

        # ===== DRAG ATIVO (prioridade maxima) =====
        if self._poke_scroll_dragging:
            if event.type == pygame.MOUSEMOTION:
                self._update_poke_scroll_from_mouse(event.pos[1])
                return None
            if event.type == pygame.MOUSEBUTTONUP and event.button == 1:
                self._poke_scroll_dragging = False
                return None
            if event.type == pygame.MOUSEBUTTONDOWN:
                return None

        if self._move_scroll_dragging:
            if event.type == pygame.MOUSEMOTION:
                self._update_move_scroll_from_mouse(event.pos[1])
                return None
            if event.type == pygame.MOUSEBUTTONUP and event.button == 1:
                self._move_scroll_dragging = False
                return None
            if event.type == pygame.MOUSEBUTTONDOWN:
                return None

        if event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE:
            return "close"

        # ===== SCROLL WHEEL =====
        if event.type == pygame.MOUSEWHEEL:
            mx, my = pygame.mouse.get_pos()
            if self.poke_rect and self.poke_rect.collidepoint(mx, my):
                max_s = max(0, len(self.entries) - self._visible_poke_rows())
                self.pokemon_scroll = max(0, min(max_s,
                                                  self.pokemon_scroll - event.y))
            elif self.moves_rect and self.moves_rect.collidepoint(mx, my):
                max_s = max(0, len(self.learnable_moves) - self._visible_move_rows())
                self.move_scroll = max(0, min(max_s,
                                              self.move_scroll - event.y))
            return None

        # ===== CLICK =====
        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            if self.cancel_btn and self.cancel_btn.collidepoint(event.pos):
                return "close"
            if self.confirm_btn and self.confirm_btn.collidepoint(event.pos):
                return self._try_confirm()

            # ===== SCROLLBAR DRAG (checa ANTES das listas) =====
            if self._poke_scrollbar_rect and self._poke_scrollbar_rect.collidepoint(event.pos):
                self._begin_poke_scroll_drag(event.pos)
                return None
            if self._move_scrollbar_rect and self._move_scrollbar_rect.collidepoint(event.pos):
                self._begin_move_scroll_drag(event.pos)
                return None

            # Lista de Pokémon
            if self.poke_rect and self.poke_rect.collidepoint(event.pos):
                rel_y = event.pos[1] - self.poke_rect.y - 44
                if rel_y >= 0:
                    idx = self.pokemon_scroll + rel_y // self.POKE_ROW_H_BASE
                    if 0 <= idx < len(self.entries):
                        self.selected_poke_idx = idx
                        self._refresh_learnable_moves()
                        sound_manager.play_effect(SoundEffect.CLICK, volume=0.2)
                return None

            # Lista de golpes
            if self.moves_rect and self.moves_rect.collidepoint(event.pos):
                rel_y = event.pos[1] - self.moves_rect.y - 44
                if rel_y >= 0:
                    idx = self.move_scroll + rel_y // self.MOVE_ROW_H_BASE
                    if 0 <= idx < len(self.learnable_moves):
                        self.selected_move_idx = idx
                        sound_manager.play_effect(SoundEffect.CLICK, volume=0.2)
                return None

            # Slots
            for i, rect in enumerate(self.slot_buttons):
                if rect.collidepoint(event.pos):
                    self.target_slot = i
                    sound_manager.play_effect(SoundEffect.CLICK, volume=0.2)
                    return None

        return None

    # ==================================================================
    # AÇÃO
    # ==================================================================
    def _try_confirm(self):
        pokemon = self._get_pokemon_instance()
        if not pokemon:
            return None

        if self.selected_move_idx < 0 or self.selected_move_idx >= len(self.learnable_moves):
            self.success_message = "Selecione um golpe para aprender."
            return None

        if self.target_slot < 0:
            self.success_message = "Selecione um slot de destino."
            return None

        if self.player.money < self.cost:
            self.success_message = "Gold insuficiente!"
            return None

        chosen = self.learnable_moves[self.selected_move_idx]
        move_info = chosen["info"]
        new_move = Move(chosen["name"], move_info)

        try:
            slot = self.target_slot
            if slot < len(pokemon.moves):
                pokemon.moves[slot] = new_move
            elif slot == len(pokemon.moves) and slot < 4:
                pokemon.moves.append(new_move)
            else:
                self.success_message = "Slot inválido."
                return None
        except Exception as e:
            print(f"[NPC_HALL] Erro ao reaprender: {e}")
            return None

        if not pokemon.is_in_team:
            for d in self.player.pc_box:
                if d.get("unique_id") == pokemon.unique_id:
                    d["moves"] = [
                        {
                            "name": m.name,
                            "current_pp": m.current_pp,
                            "max_pp": m.max_pp,
                            "type": m.type,
                            "power": m.power,
                            "accuracy": m.accuracy,
                            "category": m.category,
                        }
                        for m in pokemon.moves
                    ]
                    break

        self.player.money -= self.cost
        try:
            self.player.auto_save()
        except Exception as e:
            print(f"[NPC_HALL] Erro ao salvar: {e}")

        self.success_message = f"Seu Pokémon reaprendeu '{chosen['name']}'!"
        sound_manager.play_effect(SoundEffect.LEVELUP)
        return "success"

    def fixed_update(self, dt):
        pass

    # ==================================================================
    # RENDER
    # ==================================================================
    def render(self, screen):
        self._check_resize()

        ov = pygame.Surface((self.game.screen_manager.window_width,
                             self.game.screen_manager.window_height))
        ov.set_alpha(215)
        ov.fill((0, 0, 0))
        screen.blit(ov, (0, 0))

        pygame.draw.rect(screen, (20, 24, 34), self.window, border_radius=14)
        pygame.draw.rect(screen, (140, 120, 60), self.window, 3, border_radius=14)
        pygame.draw.rect(screen, (60, 55, 40), self.window.inflate(-8, -8),
                         1, border_radius=12)

        self._render_header(screen)
        self._render_pokemon_list(screen)
        self._render_moves_list(screen)
        self._render_comparison(screen)
        self._render_slots(screen)
        self._render_buttons(screen)

    # ------------------------------------------------------------------
    # HEADER
    # ------------------------------------------------------------------
    def _render_header(self, screen):
        title_s = self._fonts['title'].render(
            "REAPRENDER MOVIMENTO", True, (255, 220, 120))
        screen.blit(title_s,
                    (self.window.centerx - title_s.get_width() // 2,
                     self.window.y + 16))

        parts = [
            (f"Custo: {self.cost} G", (255, 220, 120)),
            ("   ·   ", (140, 150, 180)),
            (f"Você tem: {self.player.money} G",
             (150, 220, 150) if self.player.money >= self.cost
             else (240, 130, 130)),
            ("   ·   ", (140, 150, 180)),
            ("Apenas golpes que o Pokémon já poderia aprender até o nível atual",
             (180, 190, 210)),
        ]
        total_w = sum(self._fonts['subtitle'].size(t)[0] for t, _ in parts)
        start_x = self.window.centerx - total_w // 2
        cy = self.window.y + 16 + title_s.get_height() + 8
        for text, color in parts:
            s = self._fonts['subtitle'].render(text, True, color)
            screen.blit(s, (start_x, cy))
            start_x += s.get_width()

    # ------------------------------------------------------------------
    # LISTA DE POKÉMON
    # ------------------------------------------------------------------
    def _render_pokemon_list(self, screen):
        if not self.poke_rect:
            return

        pygame.draw.rect(screen, (16, 20, 28), self.poke_rect, border_radius=8)
        pygame.draw.rect(screen, (70, 80, 105), self.poke_rect, 2, border_radius=8)

        hdr = pygame.Rect(self.poke_rect.x, self.poke_rect.y,
                          self.poke_rect.width, 40)
        pygame.draw.rect(screen, (34, 40, 55), hdr,
                         border_top_left_radius=8, border_top_right_radius=8)
        pygame.draw.line(screen, (70, 80, 105),
                         (hdr.x + 8, hdr.bottom - 1),
                         (hdr.right - 8, hdr.bottom - 1), 1)

        hdr_s = self._fonts['section'].render("SEUS POKÉMON", True, (200, 210, 235))
        screen.blit(hdr_s, (hdr.x + 14,
                             hdr.y + (hdr.height - hdr_s.get_height()) // 2))

        cnt_s = self._fonts['tiny'].render(f"{len(self.entries)}",
                                            True, (150, 160, 190))
        screen.blit(cnt_s, (hdr.right - cnt_s.get_width() - 14,
                            hdr.y + (hdr.height - cnt_s.get_height()) // 2))

        if not self.entries:
            f = self._fonts['medium']
            s = f.render("Nenhum Pokémon", True, (160, 170, 190))
            screen.blit(s, (self.poke_rect.centerx - s.get_width() // 2,
                            self.poke_rect.centery - s.get_height() // 2))
            return

        # ===== Scrollbar geometry (calculada ANTES do loop) =====
        visible = self._visible_poke_rows()
        has_scrollbar = len(self.entries) > visible

        bar_w = 16
        bar_gap_right = 6
        bar_x = self.poke_rect.right - bar_w - bar_gap_right
        bar_top = self.poke_rect.y + 44
        bar_h = self.poke_rect.height - 48

        # Lv.XX e #ID ficam antes da barra
        right_reserve = (bar_w + bar_gap_right + 8) if has_scrollbar else 10

        old_clip = screen.get_clip()
        clip = pygame.Rect(self.poke_rect.x + 4, self.poke_rect.y + 44,
                           self.poke_rect.width - 8, self.poke_rect.height - 48)
        screen.set_clip(clip)

        start = self.pokemon_scroll
        end = min(len(self.entries), start + visible)
        mouse = pygame.mouse.get_pos()

        for i in range(start, end):
            idx = i - start
            row = pygame.Rect(self.poke_rect.x + 6,
                              self.poke_rect.y + 48 + idx * self.POKE_ROW_H_BASE,
                              self.poke_rect.width - 12,
                              self.POKE_ROW_H_BASE - 4)

            entry = self.entries[i]
            selected = (i == self.selected_poke_idx)
            hovered = row.collidepoint(mouse)

            if selected:
                bg, border = (62, 52, 100), (200, 180, 255)
            elif hovered:
                bg, border = (40, 44, 62), (110, 120, 150)
            else:
                bg, border = (26, 30, 42), (48, 53, 68)

            pygame.draw.rect(screen, bg, row, border_radius=6)
            pygame.draw.rect(screen, border, row, 2 if selected else 1,
                             border_radius=6)

            try:
                sp = self.pokedex.get_portrait(entry["id"], "normal", entry["shiny"])
                if sp:
                    sz = 44
                    sc = pygame.transform.smoothscale(sp, (sz, sz))
                    screen.blit(sc, (row.x + 8, row.y + (row.height - sz) // 2))
            except Exception:
                pass

            src_tag = "TIME" if entry["source"] == "team" else "BOX"
            src_color = (90, 160, 230) if entry["source"] == "team" else (230, 160, 90)
            tag_s = self._fonts['tiny'].render(src_tag, True, (255, 255, 255))
            tag_bg = pygame.Rect(row.x + 58, row.y + 8,
                                 tag_s.get_width() + 12, tag_s.get_height() + 4)
            pygame.draw.rect(screen, src_color, tag_bg, border_radius=3)
            screen.blit(tag_s, (tag_bg.x + 6, tag_bg.y + 2))

            name_s = self._fonts['medium'].render(
                entry["display"], True,
                (255, 255, 255) if selected else (220, 220, 235))
            screen.blit(name_s, (tag_bg.right + 8,
                                  row.y + (row.height - name_s.get_height()) // 2 - 8))

            sp_s = self._fonts['tiny'].render(
                f"Espécie: {entry['species']}", True, (160, 170, 195))
            screen.blit(sp_s, (tag_bg.right + 8,
                                row.y + row.height - sp_s.get_height() - 8))

            lv_s = self._fonts['small'].render(
                f"Lv.{entry['level']}", True, (255, 220, 120))
            screen.blit(lv_s, (row.right - right_reserve - lv_s.get_width(),
                                row.y + 10))

            id_s = self._fonts['tiny'].render(
                f"#{entry['id']:04d}", True, (130, 140, 170))
            screen.blit(id_s, (row.right - right_reserve - id_s.get_width(),
                                row.bottom - id_s.get_height() - 8))

        screen.set_clip(old_clip)

        # ===== Scrollbar (16px visual, 50px hitbox) =====
        if has_scrollbar:
            thumb_h = max(48, int(bar_h * visible / len(self.entries)))
            max_s = max(1, len(self.entries) - visible)
            thumb_y = bar_top + int((bar_h - thumb_h) * self.pokemon_scroll / max_s)

            pygame.draw.rect(screen, (35, 38, 55),
                             (bar_x, bar_top, bar_w, bar_h), border_radius=8)
            thumb_color = (180, 190, 230) if self._poke_scroll_dragging else (120, 130, 170)
            pygame.draw.rect(screen, thumb_color,
                             (bar_x, thumb_y, bar_w, thumb_h), border_radius=8)

            self._poke_scrollbar_track_rect = pygame.Rect(bar_x, bar_top, bar_w, bar_h)
            self._poke_scrollbar_thumb_rect = pygame.Rect(bar_x, thumb_y, bar_w, thumb_h)
            self._poke_scrollbar_rect = pygame.Rect(
                bar_x - 30, bar_top, bar_w + 34, bar_h)
        else:
            self._poke_scrollbar_rect = None
            self._poke_scrollbar_track_rect = None
            self._poke_scrollbar_thumb_rect = None

    # ------------------------------------------------------------------
    # LISTA DE GOLPES
    # ------------------------------------------------------------------
    def _render_moves_list(self, screen):
        if not self.moves_rect:
            return

        pygame.draw.rect(screen, (16, 20, 28), self.moves_rect, border_radius=8)
        pygame.draw.rect(screen, (70, 80, 105), self.moves_rect, 2, border_radius=8)

        hdr = pygame.Rect(self.moves_rect.x, self.moves_rect.y,
                          self.moves_rect.width, 40)
        pygame.draw.rect(screen, (34, 40, 55), hdr,
                         border_top_left_radius=8, border_top_right_radius=8)
        pygame.draw.line(screen, (70, 80, 105),
                         (hdr.x + 8, hdr.bottom - 1),
                         (hdr.right - 8, hdr.bottom - 1), 1)

        hdr_s = self._fonts['section'].render(
            "GOLPES REAPRENDÍVEIS", True, (200, 210, 235))
        screen.blit(hdr_s, (hdr.x + 14,
                             hdr.y + (hdr.height - hdr_s.get_height()) // 2))

        cnt_s = self._fonts['tiny'].render(
            f"{len(self.learnable_moves)} disponíveis", True, (150, 160, 190))
        screen.blit(cnt_s, (hdr.right - cnt_s.get_width() - 14,
                            hdr.y + (hdr.height - cnt_s.get_height()) // 2))

        if not self.learnable_moves:
            f = self._fonts['medium']
            s = f.render("Nenhum golpe disponível para reaprender",
                         True, (160, 170, 190))
            screen.blit(s, (self.moves_rect.centerx - s.get_width() // 2,
                            self.moves_rect.centery - s.get_height() // 2))
            return

        # ===== Scrollbar geometry =====
        visible = self._visible_move_rows()
        has_scrollbar = len(self.learnable_moves) > visible

        bar_w = 16
        bar_gap_right = 6
        bar_x = self.moves_rect.right - bar_w - bar_gap_right
        bar_top = self.moves_rect.y + 44
        bar_h = self.moves_rect.height - 48

        right_reserve = (bar_w + bar_gap_right + 10) if has_scrollbar else 12

        old_clip = screen.get_clip()
        clip = pygame.Rect(self.moves_rect.x + 4, self.moves_rect.y + 44,
                           self.moves_rect.width - 8, self.moves_rect.height - 48)
        screen.set_clip(clip)

        start = self.move_scroll
        end = min(len(self.learnable_moves), start + visible)
        mouse = pygame.mouse.get_pos()

        for i in range(start, end):
            idx = i - start
            row = pygame.Rect(self.moves_rect.x + 6,
                              self.moves_rect.y + 48 + idx * self.MOVE_ROW_H_BASE,
                              self.moves_rect.width - 12,
                              self.MOVE_ROW_H_BASE - 4)

            mv = self.learnable_moves[i]
            info = mv["info"]
            selected = (i == self.selected_move_idx)
            hovered = row.collidepoint(mouse)

            if selected:
                bg, border = (55, 75, 105), (150, 190, 255)
            elif hovered:
                bg, border = (36, 42, 58), (95, 105, 135)
            else:
                bg, border = (24, 28, 40), (46, 51, 66)

            pygame.draw.rect(screen, bg, row, border_radius=6)
            pygame.draw.rect(screen, border, row, 2 if selected else 1,
                             border_radius=6)

            mv_type = info.get("type", "normal")
            type_color = self.pokedex.get_type_color(mv_type)
            pygame.draw.rect(screen, type_color,
                             (row.x + 4, row.y + 6, 5, row.height - 12),
                             border_radius=3)

            nm_s = self._fonts['move_name'].render(
                mv["name"].capitalize(), True,
                (255, 255, 255) if selected else (225, 230, 245))
            screen.blit(nm_s, (row.x + 18, row.y + 8))

            badge_y = row.y + row.height - 24
            type_s = self._fonts['tiny'].render(
                _sanitize(_PT_TYPE.get(mv_type, mv_type.upper())).upper(),
                True, (255, 255, 255))
            type_badge = pygame.Rect(row.x + 18, badge_y,
                                     type_s.get_width() + 14,
                                     type_s.get_height() + 4)
            pygame.draw.rect(screen, type_color, type_badge, border_radius=3)
            pygame.draw.rect(screen, (0, 0, 0), type_badge, 1, border_radius=3)
            screen.blit(type_s, (type_badge.x + 7, type_badge.y + 2))

            cat = info.get("category", "physical")
            cat_lbl, cat_color = _CATEGORY_PT.get(cat, ("---", (150, 150, 150)))
            cat_s = self._fonts['tiny'].render(cat_lbl, True, (255, 255, 255))
            cat_badge = pygame.Rect(type_badge.right + 8, badge_y,
                                     cat_s.get_width() + 14,
                                     cat_s.get_height() + 4)
            pygame.draw.rect(screen, cat_color, cat_badge, border_radius=3)
            pygame.draw.rect(screen, (0, 0, 0), cat_badge, 1, border_radius=3)
            screen.blit(cat_s, (cat_badge.x + 7, cat_badge.y + 2))

            pwr = info.get("power", 0)
            pwr_txt = f"{pwr}" if pwr else "--"
            acc = info.get("accuracy", 0)
            acc_txt = f"{acc}%" if acc else "--"
            pp = info.get("pp", 0)

            stats = [
                ("PWR", pwr_txt, (255, 175, 90)),
                ("ACC", acc_txt, (170, 210, 255)),
                ("PP",  f"{pp}", (170, 220, 170)),
            ]
            stat_x = row.right - right_reserve
            for label, value, color in reversed(stats):
                vs = self._fonts['small'].render(value, True, color)
                ls = self._fonts['tiny'].render(label, True, (140, 150, 180))
                block_w = max(vs.get_width(), ls.get_width())
                vx = stat_x - block_w
                screen.blit(vs, (vx + (block_w - vs.get_width()) // 2,
                                  row.y + 8))
                screen.blit(ls, (vx + (block_w - ls.get_width()) // 2,
                                  row.y + row.height - ls.get_height() - 10))
                stat_x = vx - 16

        screen.set_clip(old_clip)

        # ===== Scrollbar (16px visual, 50px hitbox) =====
        if has_scrollbar:
            thumb_h = max(48, int(bar_h * visible / len(self.learnable_moves)))
            max_s = max(1, len(self.learnable_moves) - visible)
            thumb_y = bar_top + int((bar_h - thumb_h) * self.move_scroll / max_s)

            pygame.draw.rect(screen, (35, 38, 55),
                             (bar_x, bar_top, bar_w, bar_h), border_radius=8)
            thumb_color = (180, 190, 230) if self._move_scroll_dragging else (120, 130, 170)
            pygame.draw.rect(screen, thumb_color,
                             (bar_x, thumb_y, bar_w, thumb_h), border_radius=8)

            self._move_scrollbar_track_rect = pygame.Rect(bar_x, bar_top, bar_w, bar_h)
            self._move_scrollbar_thumb_rect = pygame.Rect(bar_x, thumb_y, bar_w, thumb_h)
            self._move_scrollbar_rect = pygame.Rect(
                bar_x - 30, bar_top, bar_w + 34, bar_h)
        else:
            self._move_scrollbar_rect = None
            self._move_scrollbar_track_rect = None
            self._move_scrollbar_thumb_rect = None

    # ------------------------------------------------------------------
    # COMPARAÇÃO (NOVO vs ATUAL)
    # ------------------------------------------------------------------
    def _render_comparison(self, screen):
        if not self.detail_rect:
            return

        pygame.draw.rect(screen, (16, 20, 28), self.detail_rect, border_radius=8)
        pygame.draw.rect(screen, (70, 80, 105), self.detail_rect, 2, border_radius=8)

        hdr = pygame.Rect(self.detail_rect.x, self.detail_rect.y,
                          self.detail_rect.width, 40)
        pygame.draw.rect(screen, (34, 40, 55), hdr,
                         border_top_left_radius=8, border_top_right_radius=8)
        pygame.draw.line(screen, (70, 80, 105),
                         (hdr.x + 8, hdr.bottom - 1),
                         (hdr.right - 8, hdr.bottom - 1), 1)

        hdr_s = self._fonts['section'].render(
            "COMPARAÇÃO DE GOLPES", True, (200, 210, 235))
        screen.blit(hdr_s, (hdr.x + 14,
                             hdr.y + (hdr.height - hdr_s.get_height()) // 2))

        hint_s = self._fonts['tiny'].render(
            "Escolha um golpe e um slot para comparar",
            True, (150, 160, 190))
        screen.blit(hint_s, (hdr.right - hint_s.get_width() - 14,
                              hdr.y + (hdr.height - hint_s.get_height()) // 2))

        # ===== Coluna ESQUERDA: NOVO GOLPE =====
        new_mv = self._get_selected_move()
        if new_mv:
            self._render_move_column(
                screen,
                self.detail_left,
                title="NOVO GOLPE",
                title_color=(150, 220, 150),
                border_accent=(90, 200, 100),
                move_name=new_mv["name"],
                move_info=new_mv["info"],
            )
        else:
            self._render_empty_column(
                screen, self.detail_left,
                title="NOVO GOLPE",
                title_color=(150, 220, 150),
                border_accent=(90, 200, 100),
                msg="Selecione um golpe na lista\nacima para ver os detalhes",
            )

        # ===== Coluna DIREITA: GOLPE ATUAL DO SLOT =====
        if self.target_slot < 0:
            self._render_empty_column(
                screen, self.detail_right,
                title="GOLPE ATUAL NO SLOT",
                title_color=(255, 200, 150),
                border_accent=(220, 160, 90),
                msg="Clique em um slot abaixo\npara comparar com o golpe atual",
            )
        else:
            cur_mv = self._get_target_slot_move()
            title = f"GOLPE ATUAL NO SLOT {self.target_slot + 1}"

            if cur_mv is None:
                self._render_empty_column(
                    screen, self.detail_right,
                    title=title,
                    title_color=(255, 200, 150),
                    border_accent=(220, 160, 90),
                    msg="SLOT VAZIO\n\nO novo golpe será adicionado\nsem substituir nada",
                )
            else:
                cur_info = {
                    "type": getattr(cur_mv, 'type', 'normal'),
                    "category": getattr(cur_mv, 'category', 'physical'),
                    "power": getattr(cur_mv, 'power', 0),
                    "accuracy": getattr(cur_mv, 'accuracy', 0),
                    "pp": getattr(cur_mv, 'max_pp', 0),
                    "effect": None,
                    "effect_chance": None,
                }
                self._render_move_column(
                    screen,
                    self.detail_right,
                    title=title,
                    title_color=(255, 200, 150),
                    border_accent=(220, 160, 90),
                    move_name=cur_mv.name,
                    move_info=cur_info,
                )

    def _render_move_column(self, screen, rect, title, title_color,
                            border_accent, move_name, move_info):
        """Renderiza uma coluna de detalhes de um golpe."""
        pygame.draw.rect(screen, (22, 26, 38), rect, border_radius=8)
        pygame.draw.rect(screen, border_accent, rect, 2, border_radius=8)

        pad = 12
        inner = pygame.Rect(rect.x + pad, rect.y + pad,
                            rect.width - pad * 2, rect.height - pad * 2)

        title_s = self._fonts['tiny'].render(title, True, title_color)
        screen.blit(title_s, (inner.x, inner.y))
        y = inner.y + title_s.get_height() + 6

        # ===== Nome do golpe =====
        name_s = self._fonts['detail_name'].render(
            move_name.capitalize(), True, (255, 245, 210))
        screen.blit(name_s, (inner.x, y))
        y += name_s.get_height() + 6

        # ===== Badges: tipo + categoria =====
        mv_type = move_info.get("type", "normal")
        type_color = self.pokedex.get_type_color(mv_type)
        type_s = self._fonts['tiny'].render(
            _sanitize(_PT_TYPE.get(mv_type, mv_type.upper())).upper(),
            True, (255, 255, 255))
        type_badge = pygame.Rect(inner.x, y,
                                  type_s.get_width() + 14,
                                  type_s.get_height() + 4)
        pygame.draw.rect(screen, type_color, type_badge, border_radius=3)
        pygame.draw.rect(screen, (0, 0, 0), type_badge, 1, border_radius=3)
        screen.blit(type_s, (type_badge.x + 7, type_badge.y + 2))

        cat = move_info.get("category", "physical")
        cat_lbl, cat_color = _CATEGORY_PT.get(cat, ("---", (150, 150, 150)))
        cat_s = self._fonts['tiny'].render(cat_lbl, True, (255, 255, 255))
        cat_badge = pygame.Rect(type_badge.right + 6, y,
                                 cat_s.get_width() + 14,
                                 cat_s.get_height() + 4)
        pygame.draw.rect(screen, cat_color, cat_badge, border_radius=3)
        pygame.draw.rect(screen, (0, 0, 0), cat_badge, 1, border_radius=3)
        screen.blit(cat_s, (cat_badge.x + 7, cat_badge.y + 2))

        y = type_badge.bottom + 8

        # ===== Stats inline (PWR · ACC · PP) =====
        pwr = move_info.get("power") or 0
        acc = move_info.get("accuracy") or 0
        pp = move_info.get("pp") or 0

        stat_font = self._fonts['small']
        sep_color = (100, 110, 140)

        stats_line = [
            ("PWR", f"{pwr}" if pwr else "--", (255, 175, 90)),
            ("|", "", sep_color),
            ("ACC", f"{acc}%" if acc else "--", (170, 210, 255)),
            ("|", "", sep_color),
            ("PP", f"{pp}", (170, 220, 170)),
        ]
        sx = inner.x
        for label, value, color in stats_line:
            if label == "|":
                ss = stat_font.render(" | ", True, sep_color)
                screen.blit(ss, (sx, y))
                sx += ss.get_width()
            else:
                ls = self._fonts['tiny'].render(label + ":", True, (150, 160, 190))
                screen.blit(ls, (sx, y + 2))
                sx += ls.get_width() + 3
                vs = stat_font.render(value, True, color)
                screen.blit(vs, (sx, y))
                sx += vs.get_width() + 6

        y += stat_font.get_height() + 8

        # ===== Divisor =====
        pygame.draw.line(screen, (55, 65, 90),
                         (inner.x, y), (inner.right, y), 1)
        y += 8

        # ===== Label DESCRIÇÃO =====
        lbl = self._fonts['tiny'].render("DESCRIÇÃO", True, (150, 160, 190))
        screen.blit(lbl, (inner.x, y))
        y += lbl.get_height() + 4

        # ===== Descrição com wrap =====
        desc = self._get_move_description(move_name, move_info)
        desc_font = self._fonts['desc']
        lines = self._wrap_text(desc, desc_font, inner.width)
        line_h = desc_font.get_height() + 1
        max_lines = max(1, (inner.bottom - y) // line_h)

        for i, line in enumerate(lines[:max_lines]):
            if i == max_lines - 1 and len(lines) > max_lines:
                while line and desc_font.size(line + "...")[0] > inner.width:
                    line = line[:-1]
                line = line + "..."
            s = desc_font.render(line, True, (215, 220, 235))
            screen.blit(s, (inner.x, y))
            y += line_h

    def _render_empty_column(self, screen, rect, title, title_color,
                              border_accent, msg):
        """Renderiza uma coluna vazia com mensagem centralizada."""
        pygame.draw.rect(screen, (20, 23, 32), rect, border_radius=8)
        pygame.draw.rect(screen, (60, 68, 90), rect, 1, border_radius=8)

        pad = 12
        inner = pygame.Rect(rect.x + pad, rect.y + pad,
                            rect.width - pad * 2, rect.height - pad * 2)

        title_s = self._fonts['tiny'].render(title, True, title_color)
        screen.blit(title_s, (inner.x, inner.y))

        lines = msg.split('\n')
        total_h = sum(self._fonts['small'].get_height() + 2 for _ in lines)
        cy = inner.centery - total_h // 2

        for line in lines:
            if not line:
                cy += self._fonts['small'].get_height() + 2
                continue
            s = self._fonts['small'].render(line, True, (150, 160, 185))
            sx = inner.centerx - s.get_width() // 2
            screen.blit(s, (sx, cy))
            cy += s.get_height() + 2

    # ------------------------------------------------------------------
    # SLOTS
    # ------------------------------------------------------------------
    def _render_slots(self, screen):
        if not self.slots_rect:
            return

        pygame.draw.rect(screen, (16, 20, 28), self.slots_rect, border_radius=8)
        pygame.draw.rect(screen, (70, 80, 105), self.slots_rect, 2, border_radius=8)

        hdr_s = self._fonts['section'].render(
            "SLOTS ATUAIS DO POKÉMON", True, (200, 210, 235))
        screen.blit(hdr_s, (self.slots_rect.x + 16,
                             self.slots_rect.y + (42 - hdr_s.get_height()) // 2))

        hint_s = self._fonts['tiny'].render(
            "Clique em um slot para escolher onde encaixar o novo golpe",
            True, (150, 160, 190))
        screen.blit(hint_s, (self.slots_rect.right - hint_s.get_width() - 16,
                              self.slots_rect.y + (42 - hint_s.get_height()) // 2))

        pokemon = self._get_pokemon_instance()
        mouse = pygame.mouse.get_pos()

        if not pokemon:
            return

        for i, rect in enumerate(self.slot_buttons):
            has_move = i < len(pokemon.moves)
            selected = (i == self.target_slot)
            hovered = rect.collidepoint(mouse)

            if selected:
                bg, border = (55, 75, 105), (150, 190, 255)
            elif hovered:
                bg, border = (36, 42, 58), (110, 120, 150)
            else:
                bg, border = (24, 28, 40), (46, 51, 66)

            pygame.draw.rect(screen, bg, rect, border_radius=8)
            pygame.draw.rect(screen, border, rect, 2 if selected else 1,
                             border_radius=8)

            idx_s = self._fonts['tiny'].render(
                f"SLOT {i + 1}", True, (150, 160, 190))
            screen.blit(idx_s, (rect.x + 10, rect.y + 6))

            if has_move:
                mv = pokemon.moves[i]
                mv_type = getattr(mv, 'type', 'normal')
                type_color = self.pokedex.get_type_color(mv_type)

                pygame.draw.rect(screen, type_color,
                                 (rect.x + 4, rect.y + 22, 4, rect.height - 26),
                                 border_radius=3)

                nm_s = self._fonts['medium'].render(
                    mv.name.capitalize(), True, (240, 245, 255))
                screen.blit(nm_s, (rect.x + 16, rect.y + 26))

                pp_txt = f"PP {mv.current_pp}/{mv.max_pp}"
                pp_pct = mv.current_pp / max(1, mv.max_pp)
                if pp_pct > 0.4:
                    pp_color = (170, 220, 170)
                elif pp_pct > 0.2:
                    pp_color = (255, 220, 120)
                else:
                    pp_color = (240, 130, 130)
                pp_s = self._fonts['small'].render(pp_txt, True, pp_color)
                screen.blit(pp_s, (rect.right - pp_s.get_width() - 10,
                                    rect.bottom - pp_s.get_height() - 8))
            else:
                empty_s = self._fonts['medium'].render("VAZIO", True,
                                                        (120, 130, 150))
                screen.blit(empty_s,
                            (rect.centerx - empty_s.get_width() // 2,
                             rect.centery - empty_s.get_height() // 2 + 8))

    # ------------------------------------------------------------------
    # BOTÕES
    # ------------------------------------------------------------------
    def _render_buttons(self, screen):
        mv = self._get_selected_move()
        ready = (mv is not None
                 and self.target_slot >= 0
                 and self.player.money >= self.cost)

        if ready:
            bg, border = (55, 130, 70), (120, 220, 140)
        else:
            bg, border = (55, 58, 68), (100, 105, 115)

        pygame.draw.rect(screen, bg, self.confirm_btn, border_radius=8)
        pygame.draw.rect(screen, border, self.confirm_btn, 2, border_radius=8)
        cf = self._fonts['button']
        label = f"CONFIRMAR ({self.cost} G)"
        cs = cf.render(label, True, (255, 255, 255))
        screen.blit(cs, cs.get_rect(center=self.confirm_btn.center))

        pygame.draw.rect(screen, (120, 55, 55), self.cancel_btn, border_radius=8)
        pygame.draw.rect(screen, (220, 100, 100), self.cancel_btn, 2,
                         border_radius=8)
        cs2 = cf.render("CANCELAR", True, (255, 255, 255))
        screen.blit(cs2, cs2.get_rect(center=self.cancel_btn.center))