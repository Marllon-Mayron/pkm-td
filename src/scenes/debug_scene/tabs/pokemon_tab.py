# src/scenes/debug_scene/tabs/pokemon_tab.py
"""
Aba POKÉMON — criação e edição de Pokémon do save.
Layout maior, com portraits e divisões visuais claras.

Quando em modo EDIT, o painel direito possui sub-abas:
    - GERAL: stats, identidade, IVs, preview
    - MOVES: editor completo de moves (adicionar/trocar/remover)

O seletor de moves é um MODAL CENTRALIZADO sobre a tela inteira
(com backdrop escuro que bloqueia cliques/scroll por trás), contendo:
    - Busca por nome
    - Filtro de TIPO em dropdown (18 tipos + Todos)
    - Filtro de CATEGORIA em botões (Físico / Especial / Status / Todos)
    - Filtro de ACURÁCIA em botões (Todas / > 50 / ≤ 50)
    - Toggle de ordenação (A-Z ↔ Poder ↓)
    - Lista com scrollbar arrastável

As listas laterais (criar/editar Pokémon) também possuem scrollbar
arrastável com o mouse.
"""

import pygame
import random
from datetime import datetime

from src.data.pokedex import Pokedex
from src.data.item_bag_catalog import item_bag_catalog
from src.managers.sounds.sound_manager import sound_manager, SoundEffect


_IV_STATS = ["hp", "attack", "defense", "special_attack", "special_defense", "speed"]
_IV_LABELS = {
    "hp": "HP", "attack": "ATK", "defense": "DEF",
    "special_attack": "SPA", "special_defense": "SPD", "speed": "SPE",
}
_NATURES_DATA = [
    {"name": "Hardy",   "attack": 1.0, "defense": 1.0, "sp_attack": 1.0, "sp_defense": 1.0, "speed": 1.0},
    {"name": "Lonely",  "attack": 1.1, "defense": 0.9, "sp_attack": 1.0, "sp_defense": 1.0, "speed": 1.0},
    {"name": "Brave",   "attack": 1.1, "defense": 1.0, "sp_attack": 1.0, "sp_defense": 1.0, "speed": 0.9},
    {"name": "Adamant", "attack": 1.1, "defense": 1.0, "sp_attack": 0.9, "sp_defense": 1.0, "speed": 1.0},
    {"name": "Naughty", "attack": 1.1, "defense": 1.0, "sp_attack": 1.0, "sp_defense": 0.9, "speed": 1.0},
    {"name": "Bold",    "attack": 0.9, "defense": 1.1, "sp_attack": 1.0, "sp_defense": 1.0, "speed": 1.0},
    {"name": "Relaxed", "attack": 1.0, "defense": 1.1, "sp_attack": 1.0, "sp_defense": 1.0, "speed": 0.9},
    {"name": "Impish",  "attack": 1.0, "defense": 1.1, "sp_attack": 0.9, "sp_defense": 1.0, "speed": 1.0},
    {"name": "Lax",     "attack": 1.0, "defense": 1.1, "sp_attack": 1.0, "sp_defense": 0.9, "speed": 1.0},
    {"name": "Timid",   "attack": 0.9, "defense": 1.0, "sp_attack": 1.0, "sp_defense": 1.0, "speed": 1.1},
    {"name": "Hasty",   "attack": 1.0, "defense": 0.9, "sp_attack": 1.0, "sp_defense": 1.0, "speed": 1.1},
    {"name": "Jolly",   "attack": 1.0, "defense": 1.0, "sp_attack": 0.9, "sp_defense": 1.0, "speed": 1.1},
    {"name": "Naive",   "attack": 1.0, "defense": 1.0, "sp_attack": 1.0, "sp_defense": 0.9, "speed": 1.1},
    {"name": "Modest",  "attack": 0.9, "defense": 1.0, "sp_attack": 1.1, "sp_defense": 1.0, "speed": 1.0},
    {"name": "Mild",    "attack": 1.0, "defense": 0.9, "sp_attack": 1.1, "sp_defense": 1.0, "speed": 1.0},
    {"name": "Quiet",   "attack": 1.0, "defense": 1.0, "sp_attack": 1.1, "sp_defense": 1.0, "speed": 0.9},
    {"name": "Rash",    "attack": 1.0, "defense": 1.0, "sp_attack": 1.1, "sp_defense": 0.9, "speed": 1.0},
    {"name": "Calm",    "attack": 0.9, "defense": 1.0, "sp_attack": 1.0, "sp_defense": 1.1, "speed": 1.0},
    {"name": "Gentle",  "attack": 1.0, "defense": 0.9, "sp_attack": 1.0, "sp_defense": 1.1, "speed": 1.0},
    {"name": "Sassy",   "attack": 1.0, "defense": 1.0, "sp_attack": 1.0, "sp_defense": 1.1, "speed": 0.9},
    {"name": "Careful", "attack": 1.0, "defense": 1.0, "sp_attack": 0.9, "sp_defense": 1.1, "speed": 1.0},
    {"name": "Quirky",  "attack": 1.0, "defense": 1.0, "sp_attack": 1.0, "sp_defense": 1.0, "speed": 1.0},
]
_NATURE_NAMES = [n["name"] for n in _NATURES_DATA]

ROW_H = 64
PORTRAIT_SIZE = 48
SUB_TAB_H = 40
SEARCH_H = 40
FORM_ROW_H = 32
FORM_ROW_GAP = 6
SECTION_GAP = 14
SECTION_TITLE_H = 22
FORM_HEADER_SIZE = 88

# ===== Constantes para o editor de moves =====
MOVE_ROW_H = 54
MOVE_PICKER_ROW_H = 50
EDIT_SUBTAB_H = 34

# ===== Constantes do modal de moves =====
MODAL_ROW_H = 52
MODAL_PAD = 22

_ALL_TYPES_ORDERED = [
    "normal", "fire", "water", "electric", "grass", "ice",
    "fighting", "poison", "ground", "flying", "psychic", "bug",
    "rock", "ghost", "dragon", "dark", "steel", "fairy",
]


class PokemonTab:
    MODE_CREATE = "create"
    MODE_EDIT = "edit"
    INPUT_NAMES = {"input_name", "input_search", "edit_input_name", "move_search_input"}

    SUBTAB_GENERAL = "general"
    SUBTAB_MOVES = "moves"

    # ------------------------------------------------------------------
    def __init__(self, parent):
        self.parent = parent
        self.pokedex = Pokedex()

        self.mode = self.MODE_CREATE
        self.focused_input = None

        self.all_ids = self.pokedex.get_all_ids()
        self.filtered_ids = list(self.all_ids)
        self.search_text = ""
        self.list_scroll = 0
        self.list_selected = 0

        self.form = self._default_form()

        self.edit_targets = []
        self.edit_selected = 0
        self.edit_scroll = 0
        self.edit_form = None
        self._refresh_edit_targets()

        # ===== Sub-aba atual no modo edição =====
        self.edit_subtab = self.SUBTAB_GENERAL

        # ===== Move picker (modal) state =====
        self.move_picker_open = False
        self.move_picker_slot = 0
        self.move_picker_scroll = 0
        self.move_search_text = ""
        self._visible_move_picker_n = 8

        # Filtros / ordenação
        self.move_filter_category = None      # None | "physical" | "special" | "status"
        self.move_filter_type = None          # None | "fire" | "water" | ...
        self.move_filter_accuracy = "all"     # "all" | "gt50" | "le50"
        self.move_sort_mode = "az"            # "az" | "power"

        # Dropdown ativo (None | "type")
        self.active_dropdown = None

        # Cache de info de moves por nome (lower) para performance
        self._move_info_cache = {}

        # ===== Dados de moves =====
        self.move_data = None
        self._all_move_names = []
        self.filtered_move_names = []
        try:
            from src.data.move_data import MoveData
            self.move_data = MoveData()
            self._all_move_names = sorted(self.move_data.get_all_move_names())
            self.filtered_move_names = list(self._all_move_names)

            # Cache name(lower) -> info
            for name in self._all_move_names:
                info = self.move_data.get_move_info(name)
                if info:
                    self._move_info_cache[name.lower()] = info
        except Exception as e:
            print(f"[POKEMON_TAB] Erro ao carregar MoveData: {e}")
            self._all_move_names = []
            self.filtered_move_names = []

        # ===== Itens segurados =====
        try:
            from src.data.held_item_data import (
                HELD_ITEM_TYPE_MAPPING, HELD_ITEM_SPECIAL_EFFECTS,
            )
            ids = list(HELD_ITEM_TYPE_MAPPING.keys()) + list(HELD_ITEM_SPECIAL_EFFECTS.keys())
            self.held_items = [None] + sorted(set(ids))
        except Exception:
            self.held_items = [None]

        # ===== Estado da scrollbar (drag) — listas laterais =====
        self._scroll_dragging = False
        self._scroll_geom = None  # (bar_x, list_y, list_h, total, visible, target)
        self._scrollbar_rect = None
        self._scrollbar_thumb_rect = None
        self._scrollbar_thumb_h = 0
        self._scroll_thumb_offset = 0

        # ===== Estado da scrollbar (drag) — modal de moves =====
        self._mp_scroll_dragging = False
        self._mp_scroll_geom = None
        self._mp_scrollbar_rect = None
        self._mp_scrollbar_thumb_rect = None
        self._mp_scroll_thumb_offset = 0

        # Geometria do modal (última renderizada) — usada por handle_event
        self._modal_rect = None
        self._modal_backdrop_rect = None

        # Visibilidade (definida no render)
        self._visible_create_n = 8
        self._visible_edit_n = 8

    # ==================================================================
    # HELPERS
    # ==================================================================
    def _default_form(self):
        return {
            "pokemon_id": 1,
            "level": 50,
            "ivs": {s: 31 for s in _IV_STATS},
            "shiny": False,
            "gender": "male",
            "nature": "Hardy",
            "custom_name": "",
            "held_item": None,
        }

    def _refresh_edit_targets(self):
        self.edit_targets = []
        player = self.parent.game.player
        for i, _ in enumerate(player.team):
            self.edit_targets.append({"source": "team", "index": i})
        for i, _ in enumerate(player.pc_box):
            self.edit_targets.append({"source": "box", "index": i})

    def _apply_search(self):
        q = self.search_text.strip().lower()
        if not q:
            self.filtered_ids = list(self.all_ids)
        else:
            self.filtered_ids = [
                pid for pid in self.all_ids
                if q in self.pokedex.get_name(pid).lower() or q in str(pid)
            ]
        self.list_scroll = 0
        self.list_selected = 0

    def _apply_move_search(self):
        """Compat: apenas delega para o filtro unificado."""
        self._apply_move_filters()

    def _apply_move_filters(self):
        """Aplica busca + categoria + tipo + acurácia + ordenação."""
        q = self.move_search_text.strip().lower()
        cat_filter = self.move_filter_category
        type_filter = self.move_filter_type
        acc_filter = self.move_filter_accuracy

        results = []
        for name in self._all_move_names:
            if q and q not in name.lower():
                continue
            info = self._move_info_cache.get(name.lower())
            if info:
                if cat_filter and info.get("category") != cat_filter:
                    continue
                if type_filter and info.get("type") != type_filter:
                    continue

                acc = info.get("accuracy", 100)
                if acc is None:
                    acc = 100
                if acc_filter == "gt50" and acc <= 50:
                    continue
                if acc_filter == "le50" and acc > 50:
                    continue
            elif cat_filter or type_filter or acc_filter != "all":
                continue
            results.append(name)

        if self.move_sort_mode == "power":
            def _pwr(n):
                info = self._move_info_cache.get(n.lower())
                return info.get("power", 0) if info else 0
            results.sort(key=lambda n: (-_pwr(n), n.lower()))
        else:
            results.sort(key=lambda n: n.lower())

        self.filtered_move_names = results
        self.move_picker_scroll = 0

    def _cycle_move_sort(self):
        self.move_sort_mode = "power" if self.move_sort_mode == "az" else "az"
        self._apply_move_filters()

    def _close_move_picker(self):
        """Fecha o modal e limpa TODO o estado associado."""
        self.move_picker_open = False
        self.focused_input = None
        self.move_search_text = ""
        self.move_filter_category = None
        self.move_filter_type = None
        self.move_filter_accuracy = "all"
        self.move_sort_mode = "az"
        self.move_picker_scroll = 0
        self.active_dropdown = None
        self._mp_scroll_dragging = False
        self._apply_move_filters()

    def _get_portrait(self, pid, shiny=False):
        try:
            p = self.pokedex.get_portrait(pid, "normal", shiny)
            if p is None:
                p = self.pokedex.get_sprite(pid, "front", shiny)
            return p
        except Exception:
            try:
                return self.pokedex.get_sprite(pid, "front", shiny)
            except Exception:
                return None

    @staticmethod
    def _text_color_for_bg(bg):
        """Retorna preto ou branco conforme a luminância do fundo."""
        r, g, b = bg[0], bg[1], bg[2]
        lum = 0.299 * r + 0.587 * g + 0.114 * b
        return (10, 10, 20) if lum > 165 else (255, 255, 255)

    # ==================================================================
    # INTERFACE COM O PAI
    # ==================================================================
    def has_focus(self):
        # Modal aberto conta como "foco" para o ESC fechar o modal
        return self.focused_input is not None or self.move_picker_open

    def get_focus(self):
        return self.focused_input

    def clear_focus(self):
        # Se o modal está aberto, ESC fecha o modal primeiro
        if self.move_picker_open:
            self._close_move_picker()
        self.focused_input = None

    # ==================================================================
    # DRAG DA SCROLLBAR (listas laterais: create/edit)
    # ==================================================================
    def _begin_scroll_drag(self, mouse_pos):
        if not self._scroll_geom:
            return
        _, list_y, list_h, total, visible, _ = self._scroll_geom
        if total <= visible:
            return
        thumb_h = max(24, int(list_h * visible / total))
        if self._scrollbar_thumb_rect and self._scrollbar_thumb_rect.collidepoint(mouse_pos):
            self._scroll_thumb_offset = mouse_pos[1] - self._scrollbar_thumb_rect.y
        else:
            self._scroll_thumb_offset = thumb_h // 2
            self._update_scroll_from_mouse(mouse_pos[1])
        self._scroll_dragging = True

    def _update_scroll_from_mouse(self, mouse_y):
        if not self._scroll_geom:
            return
        _, list_y, list_h, total, visible, target = self._scroll_geom
        if total <= visible:
            return
        thumb_h = max(24, int(list_h * visible / total))
        desired_y = mouse_y - self._scroll_thumb_offset
        desired_y = max(list_y, min(list_y + list_h - thumb_h, desired_y))
        track_h = max(1, list_h - thumb_h)
        ratio = (desired_y - list_y) / track_h
        max_s = total - visible
        new_scroll = max(0, min(max_s, int(round(ratio * max_s))))
        if target == "create":
            self.list_scroll = new_scroll
        elif target == "edit":
            self.edit_scroll = new_scroll

    # ==================================================================
    # DRAG DA SCROLLBAR DO MODAL DE MOVES
    # ==================================================================
    def _begin_mp_scroll_drag(self, mouse_pos):
        if not self._mp_scroll_geom:
            return
        _, list_y, list_h, total, visible = self._mp_scroll_geom
        if total <= visible:
            return
        thumb_h = max(24, int(list_h * visible / total))
        if self._mp_scrollbar_thumb_rect and self._mp_scrollbar_thumb_rect.collidepoint(mouse_pos):
            self._mp_scroll_thumb_offset = mouse_pos[1] - self._mp_scrollbar_thumb_rect.y
        else:
            self._mp_scroll_thumb_offset = thumb_h // 2
            self._update_mp_scroll_from_mouse(mouse_pos[1])
        self._mp_scroll_dragging = True

    def _update_mp_scroll_from_mouse(self, mouse_y):
        if not self._mp_scroll_geom:
            return
        _, list_y, list_h, total, visible = self._mp_scroll_geom
        if total <= visible:
            return
        thumb_h = max(24, int(list_h * visible / total))
        desired_y = mouse_y - self._mp_scroll_thumb_offset
        desired_y = max(list_y, min(list_y + list_h - thumb_h, desired_y))
        track_h = max(1, list_h - thumb_h)
        ratio = (desired_y - list_y) / track_h
        max_s = total - visible
        self.move_picker_scroll = max(0, min(max_s, int(round(ratio * max_s))))

    # ==================================================================
    # EVENTOS
    # ==================================================================
    def handle_event(self, event):
        # ==============================================================
        # ================= MODO MODAL DE MOVES ========================
        # ==============================================================
        if self.move_picker_open:
            # ---- Scrollbar drag (prioridade máxima) ----
            if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                if self._mp_scrollbar_rect and self._mp_scrollbar_rect.collidepoint(event.pos):
                    self._begin_mp_scroll_drag(event.pos)
                    return
            if event.type == pygame.MOUSEMOTION and self._mp_scroll_dragging:
                self._update_mp_scroll_from_mouse(event.pos[1])
                return
            if event.type == pygame.MOUSEBUTTONUP and event.button == 1:
                if self._mp_scroll_dragging:
                    self._mp_scroll_dragging = False
                    return

            # ---- Wheel ----
            if event.type == pygame.MOUSEWHEEL:
                # Se o dropdown está aberto, o wheel não rola a lista
                if self.active_dropdown:
                    return
                max_s = max(0, len(self.filtered_move_names) - self._visible_move_picker_n)
                self.move_picker_scroll = max(
                    0, min(max_s, self.move_picker_scroll - event.y)
                )
                return

            # ---- Cliques ----
            if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                # Busca o que foi clicado via fila de rects registrados no último render
                clicked = self.parent.find_click_at(event.pos)

                # ---------- 1) DROPDOWN ABERTO ----------
                if self.active_dropdown == "type":
                    # Clique numa opção do dropdown?
                    if clicked and clicked.startswith("move_dd_type_opt_"):
                        val = clicked[len("move_dd_type_opt_"):]
                        self.move_filter_type = None if val == "all" else val
                        self.active_dropdown = None
                        self._apply_move_filters()
                        return
                    # Clique no botão do dropdown → fecha (toggle)
                    if clicked == "move_filter_type_btn":
                        self.active_dropdown = None
                        return
                    # Qualquer outro clique: fecha o dropdown e NÃO processa
                    self.active_dropdown = None
                    return

                # ---------- 2) DROPDOWN FECHADO ----------
                # Backdrop (fora do modal) → fecha o modal
                if clicked == "move_modal_backdrop":
                    self._close_move_picker()
                    return

                # Painel do modal (dentro, mas fora de qualquer botão) → absorve
                if clicked == "move_modal_panel":
                    return

                # Botões/inputs do modal
                if clicked:
                    if clicked == "move_modal_close":
                        self._close_move_picker()
                        return
                    if clicked == "move_search_input":
                        self.focused_input = "move_search"
                        return
                    if clicked == "move_search_clear":
                        self.move_search_text = ""
                        self._apply_move_filters()
                        self.focused_input = "move_search"
                        return
                    if clicked == "move_sort_toggle":
                        self._cycle_move_sort()
                        return
                    if clicked == "move_filter_type_btn":
                        self.active_dropdown = "type"
                        self.focused_input = None
                        return
                    if clicked.startswith("move_filter_cat_"):
                        val = clicked[len("move_filter_cat_"):]
                        self.move_filter_category = None if val == "all" else val
                        self._apply_move_filters()
                        return
                    if clicked.startswith("move_filter_acc_"):
                        val = clicked[len("move_filter_acc_"):]
                        self.move_filter_accuracy = val if val in ("all", "gt50", "le50") else "all"
                        self._apply_move_filters()
                        return
                    if clicked.startswith("move_pick_idx_"):
                        try:
                            idx = int(clicked[len("move_pick_idx_"):])
                        except ValueError:
                            return
                        if 0 <= idx < len(self.filtered_move_names):
                            self._pick_move(self.filtered_move_names[idx])
                        return

                # Fallback: nada reconhecido dentro do modal → consome
                return

            # ---- Teclado ----
            if event.type == pygame.KEYDOWN:
                # ESC: primeiro fecha dropdown, depois o modal
                if event.key == pygame.K_ESCAPE:
                    if self.active_dropdown:
                        self.active_dropdown = None
                    else:
                        self._close_move_picker()
                    return

                if self.focused_input == "move_search":
                    if event.key == pygame.K_BACKSPACE:
                        self.move_search_text = self.move_search_text[:-1]
                        self._apply_move_filters()
                    elif event.key in (pygame.K_RETURN, pygame.K_TAB):
                        self.focused_input = None
                    elif event.unicode and event.unicode.isprintable():
                        if len(self.move_search_text) < 30:
                            self.move_search_text += event.unicode
                            self._apply_move_filters()
                return

            # Qualquer outro evento: consome
            return

        # ==============================================================
        # ==================== MODO NORMAL ==============================
        # ==============================================================
        # ---- Scrollbar drag (prioridade máxima) ----
        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            if self._scrollbar_rect and self._scrollbar_rect.collidepoint(event.pos):
                self._begin_scroll_drag(event.pos)
                return
        if event.type == pygame.MOUSEMOTION and self._scroll_dragging:
            self._update_scroll_from_mouse(event.pos[1])
            return
        if event.type == pygame.MOUSEBUTTONUP and event.button == 1:
            if self._scroll_dragging:
                self._scroll_dragging = False
                return

        # ---- Wheel ----
        if event.type == pygame.MOUSEWHEEL:
            if self.mode == self.MODE_CREATE:
                max_s = max(0, len(self.filtered_ids) - self._visible_create_n)
                self.list_scroll = max(0, min(max_s, self.list_scroll - event.y))
            else:
                max_s = max(0, len(self.edit_targets) - self._visible_edit_n)
                self.edit_scroll = max(0, min(max_s, self.edit_scroll - event.y))
            return

        # ---- Mouse down (clicks) ----
        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            clicked = self.parent.find_click_at(event.pos)
            if clicked not in self.INPUT_NAMES:
                self.focused_input = None
            if clicked:
                self.on_click(clicked)
            return

        # ---- Teclado ----
        if event.type == pygame.KEYDOWN and self.focused_input:
            fi = self.focused_input
            is_name = fi in ("name", "edit_name")
            target = (
                self.form if fi == "name"
                else self.edit_form if fi == "edit_name"
                else None
            )
            if event.key == pygame.K_BACKSPACE:
                if is_name and target is not None:
                    target["custom_name"] = target["custom_name"][:-1]
                elif fi == "search":
                    self.search_text = self.search_text[:-1]
                    self._apply_search()
            elif event.key in (pygame.K_RETURN, pygame.K_TAB):
                self.focused_input = None
            elif event.unicode and event.unicode.isprintable():
                if is_name and target is not None:
                    if len(target["custom_name"]) < 20:
                        target["custom_name"] += event.unicode
                elif fi == "search":
                    if len(self.search_text) < 20:
                        self.search_text += event.unicode
                        self._apply_search()

    # ==================================================================
    # ON_CLICK (chamado pelo pai em modo normal)
    # ==================================================================
    def on_click(self, name):
        # ---- Sub-abas do modo edição ----
        if name == "edit_subtab_general":
            self.edit_subtab = self.SUBTAB_GENERAL
            self.focused_input = None
            return
        if name == "edit_subtab_moves":
            self.edit_subtab = self.SUBTAB_MOVES
            self.focused_input = None
            return

        # ---- Botões dentro do editor de moves (abre o modal) ----
        if name.startswith("move_edit_slot_"):
            try:
                slot = int(name[len("move_edit_slot_"):])
            except ValueError:
                return
            self.move_picker_open = True
            self.move_picker_slot = slot
            self.move_search_text = ""
            self.move_filter_category = None
            self.move_filter_type = None
            self.move_filter_accuracy = "all"
            self.move_sort_mode = "az"
            self.active_dropdown = None
            self._apply_move_filters()
            self.focused_input = "move_search"
            return
        if name.startswith("move_remove_slot_"):
            try:
                slot = int(name[len("move_remove_slot_"):])
            except ValueError:
                return
            self._remove_move_at(slot)
            return

        # ---- Modo ----
        if name == "poke_mode_create":
            self.mode = self.MODE_CREATE
            self.focused_input = None
            self.edit_subtab = self.SUBTAB_GENERAL
            return
        if name == "poke_mode_edit":
            self.mode = self.MODE_EDIT
            self.focused_input = None
            self.edit_subtab = self.SUBTAB_GENERAL
            self._refresh_edit_targets()
            if self.edit_targets:
                self.edit_selected = min(self.edit_selected, len(self.edit_targets) - 1)
                self._load_edit_form()
            else:
                self.edit_form = None
            return

        # ---- Selecionar pokémon (criar) ----
        if name.startswith("list_item_"):
            try:
                idx = int(name[len("list_item_"):])
            except ValueError:
                return
            if 0 <= idx < len(self.filtered_ids):
                self.list_selected = idx
                self.form["pokemon_id"] = self.filtered_ids[idx]
            return

        # ---- Selecionar pokémon (editar) ----
        if name.startswith("edit_item_"):
            try:
                idx = int(name[len("edit_item_"):])
            except ValueError:
                return
            if 0 <= idx < len(self.edit_targets):
                self.edit_selected = idx
                self.edit_subtab = self.SUBTAB_GENERAL
                self._load_edit_form()
            return

        # ---- Inputs ----
        if name == "input_name":
            self.focused_input = "name"; return
        if name == "input_search":
            self.focused_input = "search"; return
        if name == "edit_input_name":
            self.focused_input = "edit_name"; return
        if name == "search_clear":
            self.search_text = ""
            self._apply_search()
            return

        # ---- Ações ----
        if name == "action_random":
            self.form["pokemon_id"] = random.choice(self.all_ids)
            if self.form["pokemon_id"] in self.filtered_ids:
                self.list_selected = self.filtered_ids.index(self.form["pokemon_id"])
            sound_manager.play_effect(SoundEffect.CLICK, volume=0.3)
            return

        if name in ("level_minus10", "level_minus", "level_plus", "level_plus10"):
            self._nudge_level("form", name); return
        if name in ("edit_level_minus10", "edit_level_minus",
                    "edit_level_plus", "edit_level_plus10"):
            self._nudge_level("edit_form", name); return

        if name == "iv_all31":
            for s in _IV_STATS: self.form["ivs"][s] = 31
            return
        if name == "iv_all0":
            for s in _IV_STATS: self.form["ivs"][s] = 0
            return
        if name == "iv_random":
            for s in _IV_STATS: self.form["ivs"][s] = random.randint(0, 31)
            return
        if name == "edit_iv_all31" and self.edit_form:
            for s in _IV_STATS: self.edit_form["ivs"][s] = 31
            return
        if name == "edit_iv_all0" and self.edit_form:
            for s in _IV_STATS: self.edit_form["ivs"][s] = 0
            return

        if name == "shiny_toggle":
            self.form["shiny"] = not self.form["shiny"]; return
        if name == "edit_shiny_toggle" and self.edit_form:
            self.edit_form["shiny"] = not self.edit_form["shiny"]; return

        if name == "gender_male":
            self.form["gender"] = "male"; return
        if name == "gender_female":
            self.form["gender"] = "female"; return
        if name == "gender_none":
            self.form["gender"] = None; return
        if name == "edit_gender_male" and self.edit_form:
            self.edit_form["gender"] = "male"; return
        if name == "edit_gender_female" and self.edit_form:
            self.edit_form["gender"] = "female"; return
        if name == "edit_gender_none" and self.edit_form:
            self.edit_form["gender"] = None; return

        if name in ("nature_prev", "nature_next"):
            self._cycle("form", "nature", _NATURE_NAMES, name)
            return
        if name in ("edit_nature_prev", "edit_nature_next") and self.edit_form:
            self._cycle("edit_form", "nature", _NATURE_NAMES, name)
            return

        if name in ("item_prev", "item_next"):
            self._cycle("form", "held_item", self.held_items, name)
            return
        if name in ("edit_item_prev", "edit_item_next") and self.edit_form:
            self._cycle("edit_form", "held_item", self.held_items, name)
            return

        if name == "action_add_box":
            self._action_create(add_to_team=False); return
        if name == "action_add_team":
            self._action_create(add_to_team=True); return
        if name == "action_save_edit":
            self._action_save_edit(); return
        if name == "action_delete":
            self._action_delete(); return

    # ------------------------------------------------------------------
    # Moves: helpers
    # ------------------------------------------------------------------
    def _pick_move(self, move_name):
        if not self.edit_form:
            return
        moves = self.edit_form.setdefault("moves", [])
        slot = self.move_picker_slot

        info = self._move_info_cache.get(move_name.lower())
        if info:
            new_move = {
                "name": info["name"],
                "current_pp": info["pp"],
                "max_pp": info["pp"],
            }
        else:
            new_move = {"name": move_name, "current_pp": 35, "max_pp": 35}

        if 0 <= slot < len(moves):
            moves[slot] = new_move
        else:
            moves.append(new_move)

        self._close_move_picker()
        sound_manager.play_effect(SoundEffect.CLICK, volume=0.3)

    def _remove_move_at(self, slot):
        if not self.edit_form:
            return
        moves = self.edit_form.get("moves", [])
        if 0 <= slot < len(moves):
            moves.pop(slot)
            sound_manager.play_effect(SoundEffect.CLICK, volume=0.3)

    def _nudge_level(self, target_attr, name):
        target = self.form if target_attr == "form" else self.edit_form
        if target is None:
            return
        if name.endswith("minus10"):
            target["level"] = max(1, target["level"] - 10)
        elif name.endswith("minus"):
            target["level"] = max(1, target["level"] - 1)
        elif name.endswith("plus10"):
            target["level"] = min(100, target["level"] + 10)
        else:
            target["level"] = min(100, target["level"] + 1)

    def _cycle(self, target_attr, key, options, name):
        target = self.form if target_attr == "form" else self.edit_form
        if target is None:
            return
        cur = target[key]
        try:
            i = options.index(cur)
        except ValueError:
            i = 0
        delta = -1 if name.endswith("prev") else 1
        target[key] = options[(i + delta) % len(options)]

    # ==================================================================
    # AÇÕES
    # ==================================================================
    def _action_create(self, add_to_team=False):
        from src.entities.pokemon import Pokemon
        form = self.form
        try:
            pkmn = Pokemon(0, 0, form["pokemon_id"], level=form["level"], shiny=form["shiny"])
        except Exception as e:
            self.parent.show_message(f"Erro ao criar: {e}")
            return

        pkmn.ivs = dict(form["ivs"])
        pkmn.gender = form["gender"]

        for nature in _NATURES_DATA:
            if nature["name"] == form["nature"]:
                pkmn.nature_multipliers = dict(nature)
                pkmn.nature = nature["name"]
                break

        pkmn.stats.calculate_stats()
        pkmn.current_hp = pkmn.max_hp
        pkmn.xp = 0
        try:
            pkmn.xp_to_next = pkmn.stats.calculate_xp_needed()
        except Exception:
            pass

        if form["custom_name"].strip():
            pkmn.custom_name = form["custom_name"].strip()
        if form["held_item"]:
            pkmn.held_item = form["held_item"]
            try:
                pkmn.held_item_data = item_bag_catalog.get_item(form["held_item"])
            except Exception:
                pkmn.held_item_data = None

        pkmn.capture_date = datetime.now().isoformat()
        pkmn.capture_method = "migration"

        player = self.parent.game.player
        if add_to_team:
            if len(player.team) >= 6:
                self.parent.show_message("Time cheio! Adicionado à BOX.")
                player.add_to_box(pkmn)
            else:
                pkmn.is_in_team = True
                player.team.append(pkmn)
                self.parent.show_message(f"{pkmn.get_display_name()} adicionado ao TIME!")
        else:
            player.add_to_box(pkmn)
            self.parent.show_message(f"{pkmn.get_display_name()} adicionado à BOX!")

        # ===== REGISTRA NA POKÉDEX (visto + capturado) =====
        # add_to_box já faz caught_pokemon.add, mas o branch do TEAM não.
        # register_seen NUNCA é feito por nenhum dos dois.
        # Set é idempotente, então chamar sempre é seguro.
        try:
            player.register_seen(pkmn.id)
            player.caught_pokemon.add(pkmn.id)
            print(f"[DEBUG] {pkmn.name} (ID: {pkmn.id}) registrado na Pokédex "
                  f"(visto + capturado)")
        except Exception as e:
            print(f"[DEBUG] Erro ao registrar na Pokédex: {e}")

        self.parent.save_game()
        self._refresh_edit_targets()
        sound_manager.play_effect(SoundEffect.CLICK, volume=0.3)

    def _load_edit_form(self):
        if not self.edit_targets:
            self.edit_form = None
            return
        target = self.edit_targets[self.edit_selected]
        player = self.parent.game.player

        if target["source"] == "team":
            p = player.team[target["index"]]
            moves = [
                {
                    "name": m.name,
                    "current_pp": m.current_pp,
                    "max_pp": m.max_pp,
                }
                for m in p.moves
            ]
            self.edit_form = {
                "pokemon_id": p.id, "level": p.level,
                "ivs": dict(p.ivs), "shiny": p.is_shiny,
                "gender": p.gender, "nature": p.nature,
                "custom_name": p.custom_name or "",
                "held_item": p.held_item,
                "moves": moves,
            }
        else:
            d = player.pc_box[target["index"]]
            moves = []
            for m in d.get("moves", []):
                moves.append({
                    "name": m.get("name", ""),
                    "current_pp": m.get("current_pp", m.get("max_pp", 0)),
                    "max_pp": m.get("max_pp", 0),
                })
            self.edit_form = {
                "pokemon_id": d.get("id", 1),
                "level": d.get("level", 5),
                "ivs": dict(d.get("ivs", {s: 0 for s in _IV_STATS})),
                "shiny": d.get("is_shiny", False),
                "gender": d.get("gender"),
                "nature": d.get("nature", "Hardy"),
                "custom_name": d.get("custom_name") or "",
                "held_item": d.get("held_item"),
                "moves": moves,
            }

    def _action_save_edit(self):
        if not self.edit_targets or not self.edit_form:
            self.parent.show_message("Nada para salvar.")
            return
        target = self.edit_targets[self.edit_selected]
        player = self.parent.game.player
        form = self.edit_form

        try:
            if target["source"] == "team":
                p = player.team[target["index"]]
                p.level = form["level"]
                p.ivs = dict(form["ivs"])
                p.is_shiny = form["shiny"]
                p.gender = form["gender"]
                for nature in _NATURES_DATA:
                    if nature["name"] == form["nature"]:
                        p.nature_multipliers = dict(nature)
                        p.nature = nature["name"]
                        break
                p.custom_name = form["custom_name"].strip() or None
                p.held_item = form["held_item"]
                if form["held_item"]:
                    try:
                        p.held_item_data = item_bag_catalog.get_item(form["held_item"])
                    except Exception:
                        p.held_item_data = None
                else:
                    p.held_item_data = None

                # ===== APLICA MOVES =====
                self._apply_moves_to_team_pokemon(p, form.get("moves", []))

                p.stats.calculate_stats()
                if p.current_hp > p.max_hp:
                    p.current_hp = p.max_hp
            else:
                d = player.pc_box[target["index"]]
                d["level"] = form["level"]
                d["ivs"] = dict(form["ivs"])
                d["is_shiny"] = form["shiny"]
                d["gender"] = form["gender"]
                d["nature"] = form["nature"]
                d["custom_name"] = form["custom_name"].strip() or None
                d["held_item"] = form["held_item"]

                # ===== APLICA MOVES =====
                d["moves"] = self._serialize_moves_for_dict(form.get("moves", []))

                base = self.pokedex.get_base_stats(d["id"])
                evs = d.get("evs", {s: 0 for s in _IV_STATS})
                stats = self.pokedex.calculate_stats_with_base(base, d["level"], d["ivs"], evs)

                for nature in _NATURES_DATA:
                    if nature["name"] == form["nature"]:
                        if nature["attack"] != 1.0:
                            stats["attack"] = int(stats["attack"] * nature["attack"])
                        if nature["defense"] != 1.0:
                            stats["defense"] = int(stats["defense"] * nature["defense"])
                        if nature["sp_attack"] != 1.0:
                            stats["special_attack"] = int(stats["special_attack"] * nature["sp_attack"])
                        if nature["sp_defense"] != 1.0:
                            stats["special_defense"] = int(stats["special_defense"] * nature["sp_defense"])
                        if nature["speed"] != 1.0:
                            stats["speed"] = int(stats["speed"] * nature["speed"])
                        break

                d["max_hp"] = stats["hp"]
                d["attack"] = stats["attack"]
                d["defense"] = stats["defense"]
                d["sp_attack"] = stats["special_attack"]
                d["sp_defense"] = stats["special_defense"]
                d["speed"] = stats["speed"]
                if d.get("current_hp", 0) > d["max_hp"]:
                    d["current_hp"] = d["max_hp"]
        except Exception as e:
            self.parent.show_message(f"Erro: {e}")
            return

        # ===== REGISTRA NA POKÉDEX (por segurança) =====
        # Se o Pokémon foi editado mas ainda não estava registrado como
        # visto/capturado (ex: bug anterior), garante que agora esteja.
        try:
            pid = form["pokemon_id"]
            player.register_seen(pid)
            player.caught_pokemon.add(pid)
        except Exception as e:
            print(f"[DEBUG] Erro ao registrar na Pokédex (edit): {e}")

        self.parent.save_game()
        self.parent.show_message("Pokémon atualizado!")
        sound_manager.play_effect(SoundEffect.CLICK, volume=0.3)

    def _apply_moves_to_team_pokemon(self, pokemon, moves_list):
        """Reconstrói a lista de moves do Pokémon a partir dos dicts."""
        from src.entities.move import Move

        if not self.move_data:
            return
        pokemon.moves = []
        for m_dict in moves_list:
            name = m_dict.get("name", "").strip()
            if not name:
                continue
            info = self.move_data.get_move_info(name)
            if not info:
                continue
            mv = Move(name, info)
            mv.max_pp = m_dict.get("max_pp", mv.max_pp)
            mv.current_pp = m_dict.get("current_pp", mv.max_pp)
            mv.current_pp = min(mv.current_pp, mv.max_pp)
            pokemon.moves.append(mv)

        # Se ficou sem moves, garante pelo menos Tackle (fallback do sistema)
        if not pokemon.moves:
            try:
                fallback = self.move_data.get_move_info("tackle")
                if fallback:
                    pokemon.moves.append(Move("tackle", fallback))
            except Exception:
                pass

    def _serialize_moves_for_dict(self, moves_list):
        """Converte a lista de moves do form em dicts prontos para o pc_box."""
        result = []
        for m_dict in moves_list:
            name = m_dict.get("name", "").strip()
            if not name:
                continue
            info = self.move_data.get_move_info(name) if self.move_data else None
            if info:
                result.append({
                    "name": info["name"],
                    "current_pp": m_dict.get("current_pp", info["pp"]),
                    "max_pp": m_dict.get("max_pp", info["pp"]),
                    "type": info["type"],
                    "power": info["power"],
                    "accuracy": info["accuracy"],
                    "category": info["category"],
                })
        return result

    def _action_delete(self):
        if not self.edit_targets:
            self.parent.show_message("Nada para deletar.")
            return
        target = self.edit_targets[self.edit_selected]
        player = self.parent.game.player
        try:
            if target["source"] == "team":
                player.team.pop(target["index"])
            else:
                player.pc_box.pop(target["index"])
        except Exception as e:
            self.parent.show_message(f"Erro: {e}")
            return

        self.parent.save_game()
        self._refresh_edit_targets()
        if self.edit_targets:
            self.edit_selected = min(self.edit_selected, len(self.edit_targets) - 1)
            self._load_edit_form()
        else:
            self.edit_form = None
        self.parent.show_message("Pokémon removido.")
        sound_manager.play_effect(SoundEffect.CLICK, volume=0.3)

    def fixed_update(self, dt):
        pass

    # ==================================================================
    # RENDER
    # ==================================================================
    def render(self, screen, left_rect, right_rect):
        # Limpa rects da scrollbar antes de qualquer render
        self._scrollbar_rect = None
        self._scrollbar_thumb_rect = None
        self._scroll_geom = None

        p = self.parent

        # ---- Sub-abas ----
        sub_y = left_rect.y + 10
        sub_h = SUB_TAB_H
        sub_w = (left_rect.width - 30) // 2
        create_rect = pygame.Rect(left_rect.x + 10, sub_y, sub_w, sub_h)
        edit_rect = pygame.Rect(left_rect.x + 20 + sub_w, sub_y, sub_w, sub_h)
        p.register_click("poke_mode_create", create_rect)
        p.register_click("poke_mode_edit", edit_rect)
        p.draw_subtab(screen, create_rect, "CRIAR NOVO", self.mode == self.MODE_CREATE)
        p.draw_subtab(screen, edit_rect, "EDITAR EXISTENTE", self.mode == self.MODE_EDIT)

        # ---- Search ----
        search_rect = pygame.Rect(left_rect.x + 10, sub_y + sub_h + 8,
                                  left_rect.width - 20, SEARCH_H)
        p.register_click("input_search", search_rect)
        pygame.draw.rect(screen, (15, 15, 25), search_rect, border_radius=6)
        border = (255, 200, 60) if self.focused_input == "search" else (80, 80, 110)
        pygame.draw.rect(screen, border, search_rect, 2, border_radius=6)

        f = p.get_font(16)
        display = self.search_text if self.search_text else "Buscar por nome ou ID..."
        color = (220, 220, 230) if self.search_text else (110, 110, 130)
        if self.focused_input == "search":
            display += "_"
        t = f.render(display, True, color)
        screen.blit(t, (search_rect.x + 12,
                        search_rect.y + (search_rect.height - t.get_height()) // 2))

        if self.search_text:
            clr = pygame.Rect(search_rect.right - 32, search_rect.y + 6, 28, 28)
            p.register_click("search_clear", clr)
            p.draw_button(screen, clr, "x", font_size=15)

        # ---- Lista ----
        list_y = search_rect.bottom + 10
        if self.mode == self.MODE_CREATE:
            self._render_create_list(screen, left_rect, list_y)
            self._render_form(screen, right_rect, self.form, "form")
        else:
            self._render_edit_list(screen, left_rect, list_y)
            if self.edit_form:
                self._render_form(screen, right_rect, self.edit_form, "edit")
            else:
                f = p.get_font(17)
                t = f.render("Selecione um Pokémon para editar", True, (160, 160, 180))
                screen.blit(t, (right_rect.centerx - t.get_width() // 2,
                                right_rect.centery - t.get_height() // 2))

    # ---------- LISTAS ----------
    def _render_create_list(self, screen, left_rect, list_y):
        p = self.parent
        row_h = ROW_H
        list_h = left_rect.bottom - list_y - 10
        visible = max(1, list_h // row_h)
        self._visible_create_n = visible

        start = self.list_scroll
        end = min(len(self.filtered_ids), start + visible)

        summary_f = p.get_font(13)
        summary = summary_f.render(f"{len(self.filtered_ids)} Pokémon",
                                   True, (150, 160, 190))
        screen.blit(summary, (left_rect.x + 12, list_y - 14))

        for i in range(start, end):
            idx = i - start
            row = pygame.Rect(left_rect.x + 10, list_y + idx * row_h,
                              left_rect.width - 20, row_h - 4)
            self._render_list_row(
                screen, row,
                click_name=f"list_item_{i}",
                pid=self.filtered_ids[i],
                selected=(i == self.list_selected),
            )

        self._render_scrollbar(screen, left_rect, list_y, list_h,
                               visible, len(self.filtered_ids),
                               self.list_scroll, target="create")

    def _render_edit_list(self, screen, left_rect, list_y):
        p = self.parent
        row_h = ROW_H
        list_h = left_rect.bottom - list_y - 10
        visible = max(1, list_h // row_h)
        self._visible_edit_n = visible

        total = len(self.edit_targets)
        team_count = sum(1 for t in self.edit_targets if t["source"] == "team")
        header_f = p.get_font(13)
        header = header_f.render(
            f"TIME: {team_count}   ·   BOX: {total - team_count}   ·   TOTAL: {total}",
            True, (170, 180, 210))
        screen.blit(header, (left_rect.x + 12, list_y - 14))

        if not self.edit_targets:
            f = p.get_font(15)
            t = f.render("Nenhum Pokémon no save", True, (160, 160, 180))
            screen.blit(t, (left_rect.centerx - t.get_width() // 2,
                            left_rect.centery - t.get_height() // 2))
            return

        start = self.edit_scroll
        end = min(len(self.edit_targets), start + visible)
        player = p.game.player

        for i in range(start, end):
            idx = i - start
            row = pygame.Rect(left_rect.x + 10, list_y + idx * row_h,
                              left_rect.width - 20, row_h - 4)
            target = self.edit_targets[i]

            try:
                if target["source"] == "team":
                    pk = player.team[target["index"]]
                    pid = pk.id
                    name = pk.custom_name or pk.name
                    level = pk.level
                    shiny = pk.is_shiny
                    badge = ("TIME", (70, 120, 200))
                else:
                    d = player.pc_box[target["index"]]
                    pid = d.get("id", 1)
                    name = d.get("custom_name") or d.get("name", "?")
                    level = d.get("level", 1)
                    shiny = d.get("is_shiny", False)
                    badge = ("BOX", (200, 140, 60))
            except Exception:
                pid, name, level, shiny = 1, "?", 1, False
                badge = ("?", (80, 80, 80))

            self._render_list_row(
                screen, row,
                click_name=f"edit_item_{i}",
                pid=pid, name=name, level=level, shiny=shiny,
                selected=(i == self.edit_selected),
                badge=badge,
            )

        self._render_scrollbar(screen, left_rect, list_y, list_h,
                               visible, len(self.edit_targets),
                               self.edit_scroll, target="edit")

    def _render_list_row(self, screen, row, click_name, pid,
                         name=None, level=None, shiny=False,
                         selected=False, badge=None):
        p = self.parent
        hovered = row.collidepoint(pygame.mouse.get_pos())

        if selected:
            bg, border = (60, 50, 100), (200, 180, 255)
        elif hovered:
            bg, border = (45, 40, 65), (120, 100, 160)
        else:
            bg, border = (30, 32, 48), (55, 55, 75)

        pygame.draw.rect(screen, bg, row, border_radius=6)
        pygame.draw.rect(screen, border, row, 2 if selected else 1, border_radius=6)
        p.register_click(click_name, row)

        # Portrait
        portrait = self._get_portrait(pid, shiny)
        if portrait:
            ps = PORTRAIT_SIZE
            try:
                sc = pygame.transform.smoothscale(portrait, (ps, ps))
            except Exception:
                sc = pygame.transform.scale(portrait, (ps, ps))
            box = pygame.Rect(row.x + 6, row.y + (row.height - ps) // 2, ps, ps)
            pygame.draw.rect(screen, (18, 20, 32), box, border_radius=6)
            pygame.draw.rect(screen, (70, 75, 100), box, 1, border_radius=6)
            screen.blit(sc, (box.x + (ps - sc.get_width()) // 2,
                             box.y + (ps - sc.get_height()) // 2))

        tx = row.x + PORTRAIT_SIZE + 20

        if name is None:
            name_f = p.get_font(18)
            clr = (255, 255, 255) if selected else (215, 220, 235)
            text = f"#{pid:04d}   {self.pokedex.get_name(pid)}"
            text_s = name_f.render(text, True, clr)
            ty = row.y + (row.height - text_s.get_height()) // 2
            screen.blit(text_s, (tx, ty))
        else:
            if badge:
                label, color = badge
                bf = p.get_font(12)
                bt = bf.render(label, True, (255, 255, 255))
                badge_rect = pygame.Rect(tx, row.y + 10,
                                         bt.get_width() + 12, 20)
                pygame.draw.rect(screen, color, badge_rect, border_radius=3)
                pygame.draw.rect(screen, (0, 0, 0), badge_rect, 1, border_radius=3)
                screen.blit(bt, (badge_rect.x + 6, badge_rect.y + 2))
                tx += badge_rect.width + 8

            name_f = p.get_font(17)
            clr = (255, 255, 255) if selected else (215, 220, 235)
            name_s = name_f.render(name, True, clr)
            ty = row.y + (row.height - name_s.get_height()) // 2
            screen.blit(name_s, (tx, ty))

            lv_f = p.get_font(15)
            lv_s = lv_f.render(f"Lv.{level}", True, (255, 220, 120))
            screen.blit(lv_s, (row.right - lv_s.get_width() - 16, ty))

    def _render_scrollbar(self, screen, left_rect, list_y, list_h,
                          visible, total, scroll, target):
        bar_x = left_rect.right - 8
        # Guarda geometria sempre (mesmo quando não há scroll)
        self._scroll_geom = (bar_x, list_y, list_h, total, visible, target)

        if total <= visible:
            return

        thumb_h = max(24, int(list_h * visible / total))
        max_s = max(1, total - visible)
        thumb_y = list_y + int((list_h - thumb_h) * scroll / max_s)

        # Visual
        pygame.draw.rect(screen, (40, 40, 60),
                         (bar_x, list_y, 5, list_h), border_radius=3)
        pygame.draw.rect(screen, (140, 110, 180),
                         (bar_x, thumb_y, 5, thumb_h), border_radius=3)

        # Área clicável (um pouco mais larga para facilitar)
        self._scrollbar_rect = pygame.Rect(bar_x - 3, list_y, 11, list_h)
        self._scrollbar_thumb_rect = pygame.Rect(bar_x, thumb_y, 5, thumb_h)
        self._scrollbar_thumb_h = thumb_h

    # ---------- FORMULÁRIO ----------
    def _render_form(self, screen, panel, form, prefix):
        p = self.parent
        pid = form["pokemon_id"]
        name = self.pokedex.get_name(pid)
        is_edit = (prefix == "edit")
        cb_prefix = "edit_" if is_edit else ""

        pad = 20
        y = panel.y + pad
        inner_w = panel.width - pad * 2

        # ============== CABEÇALHO ==============
        header_h = FORM_HEADER_SIZE + 24
        header_rect = pygame.Rect(panel.x + pad, y, inner_w, header_h)
        pygame.draw.rect(screen, (26, 30, 48), header_rect, border_radius=10)
        pygame.draw.rect(screen, (90, 80, 130), header_rect, 2, border_radius=10)

        portrait = self._get_portrait(pid, form["shiny"])
        ps = FORM_HEADER_SIZE
        if portrait:
            try:
                sc = pygame.transform.smoothscale(portrait, (ps, ps))
            except Exception:
                sc = pygame.transform.scale(portrait, (ps, ps))
            pb = pygame.Rect(header_rect.x + 12,
                             header_rect.y + (header_h - ps) // 2, ps, ps)
            pygame.draw.rect(screen, (18, 20, 32), pb, border_radius=8)
            pygame.draw.rect(screen, (90, 80, 130), pb, 2, border_radius=8)
            screen.blit(sc, (pb.x + (ps - sc.get_width()) // 2,
                             pb.y + (ps - sc.get_height()) // 2))

        name_f = p.get_font(28)
        name_s = name_f.render(name, True, (255, 255, 255))
        id_f = p.get_font(15)
        id_s = id_f.render(f"#{pid:04d}", True, (170, 180, 210))

        tx = header_rect.x + ps + 28
        ty = header_rect.y + 14
        screen.blit(name_s, (tx, ty))
        screen.blit(id_s, (tx, ty + name_s.get_height() + 2))

        types = self.pokedex.get_types(pid)
        type_y = ty + name_s.get_height() + id_s.get_height() + 12
        ttx = tx
        for tp in types:
            color = self.pokedex.get_type_color(tp)
            tf = p.get_font(13)
            tt = tf.render(tp.upper(), True, (255, 255, 255))
            badge = pygame.Rect(ttx, type_y, tt.get_width() + 16, tt.get_height() + 8)
            pygame.draw.rect(screen, color, badge, border_radius=4)
            pygame.draw.rect(screen, (0, 0, 0), badge, 1, border_radius=4)
            screen.blit(tt, (badge.x + 8, badge.y + 4))
            ttx += badge.width + 8

        if not is_edit:
            rand_rect = pygame.Rect(header_rect.right - 130,
                                    header_rect.bottom - 34, 118, 26)
            p.register_click("action_random", rand_rect)
            p.draw_button(screen, rand_rect, "Aleatório", font_size=13)

        y = header_rect.bottom + SECTION_GAP

        # ============== SUB-ABAS (apenas em modo edição) ==============
        if is_edit:
            sub_w = (inner_w - 8) // 2
            gen_rect = pygame.Rect(panel.x + pad, y, sub_w, EDIT_SUBTAB_H)
            mov_rect = pygame.Rect(gen_rect.right + 8, y, sub_w, EDIT_SUBTAB_H)
            p.register_click("edit_subtab_general", gen_rect)
            p.register_click("edit_subtab_moves", mov_rect)
            p.draw_subtab(screen, gen_rect, "GERAL",
                          self.edit_subtab == self.SUBTAB_GENERAL)
            p.draw_subtab(screen, mov_rect, "MOVES",
                          self.edit_subtab == self.SUBTAB_MOVES)
            y += EDIT_SUBTAB_H + 12

            # --------- Se for MOVES, delega para o editor ---------
            if self.edit_subtab == self.SUBTAB_MOVES:
                self._render_moves_editor(screen, panel, pad, inner_w, y, form)
                return

        # ============== FORM GERAL (continua) ==============
        # IDENTIDADE
        p.draw_section_title(screen, panel.x + pad, y, inner_w, "IDENTIDADE")
        y += SECTION_TITLE_H

        p.render_toggle(screen, panel.x + pad, y, inner_w, FORM_ROW_H,
                        "Shiny", form["shiny"], f"{cb_prefix}shiny_toggle")
        y += FORM_ROW_H + FORM_ROW_GAP

        p.render_gender_row(screen, panel.x + pad, y, inner_w, FORM_ROW_H,
                            "Gênero", form["gender"], f"{cb_prefix}gender")
        y += FORM_ROW_H + SECTION_GAP

        # ATRIBUTOS
        p.draw_section_title(screen, panel.x + pad, y, inner_w, "ATRIBUTOS")
        y += SECTION_TITLE_H

        p.render_slider(screen, panel.x + pad, y, inner_w, FORM_ROW_H,
                        "Nível", form["level"], 1, 100,
                        f"{cb_prefix}level_slider",
                        on_change=lambda v, tgt=form: tgt.__setitem__("level", v))
        y += FORM_ROW_H + FORM_ROW_GAP

        p.render_cycle_row(screen, panel.x + pad, y, inner_w, FORM_ROW_H,
                           "Natureza", form["nature"],
                           f"{cb_prefix}nature_prev", f"{cb_prefix}nature_next")
        y += FORM_ROW_H + FORM_ROW_GAP

        item_display = form["held_item"] if form["held_item"] else "Nenhum"
        p.render_cycle_row(screen, panel.x + pad, y, inner_w, FORM_ROW_H,
                           "Item segurado", item_display,
                           f"{cb_prefix}item_prev", f"{cb_prefix}item_next")
        y += FORM_ROW_H + FORM_ROW_GAP

        input_name = "edit_input_name" if is_edit else "input_name"
        focus_key = "edit_name" if is_edit else "name"
        p.render_text_input(screen, panel.x + pad, y, inner_w, FORM_ROW_H,
                            "Apelido", form["custom_name"], input_name,
                            focus_key=focus_key)
        y += FORM_ROW_H + SECTION_GAP

        # IVs
        p.draw_section_title(screen, panel.x + pad, y, inner_w, "IVs (0-31)")
        y += SECTION_TITLE_H

        preset_h = 26
        preset_w = 90
        px = panel.x + pad
        presets = [("Tudo 31", f"{cb_prefix}iv_all31"),
                   ("Tudo 0", f"{cb_prefix}iv_all0")]
        if not is_edit:
            presets.append(("Random", "iv_random"))
        for label, cname in presets:
            btn = pygame.Rect(px, y, preset_w, preset_h)
            p.register_click(cname, btn)
            p.draw_button(screen, btn, label, font_size=13)
            px += preset_w + 8

        y += preset_h + 10

        col_gap = 14
        col_w = (inner_w - col_gap) // 2
        col1_x = panel.x + pad
        col2_x = col1_x + col_w + col_gap

        for i, stat in enumerate(_IV_STATS):
            col = i % 2
            row = i // 2
            rx = col1_x if col == 0 else col2_x
            ry = y + row * (FORM_ROW_H + 2)
            p.render_slider(screen, rx, ry, col_w, FORM_ROW_H,
                            _IV_LABELS[stat], form["ivs"][stat], 0, 31,
                            f"{cb_prefix}iv_{stat}_slider",
                            on_change=lambda v, tgt=form, s=stat: tgt["ivs"].__setitem__(s, v))

        y += 3 * (FORM_ROW_H + 2) + SECTION_GAP

        # PREVIEW
        if y + 90 < panel.bottom - 6:
            p.draw_section_title(screen, panel.x + pad, y, inner_w, "STATS PREVISTOS")
            y += SECTION_TITLE_H

            stats_box = pygame.Rect(panel.x + pad, y, inner_w, 74)
            pygame.draw.rect(screen, (26, 30, 48), stats_box, border_radius=8)
            pygame.draw.rect(screen, (90, 80, 130), stats_box, 1, border_radius=8)

            base = self.pokedex.get_base_stats(pid)
            evs = {s: 0 for s in _IV_STATS}
            stats = self.pokedex.calculate_stats_with_base(
                base, form["level"], form["ivs"], evs)

            for nature in _NATURES_DATA:
                if nature["name"] == form["nature"]:
                    for key_json, key_mult in [
                        ("attack", "attack"), ("defense", "defense"),
                        ("special_attack", "sp_attack"),
                        ("special_defense", "sp_defense"),
                        ("speed", "speed"),
                    ]:
                        mult = nature.get(key_mult, 1.0)
                        if mult != 1.0:
                            stats[key_json] = int(stats[key_json] * mult)
                    break

            items = [("HP", stats["hp"], (100, 200, 100)),
                     ("ATK", stats["attack"], (220, 120, 120)),
                     ("DEF", stats["defense"], (200, 180, 100)),
                     ("SPA", stats["special_attack"], (180, 130, 220)),
                     ("SPD", stats["special_defense"], (130, 180, 220)),
                     ("SPE", stats["speed"], (150, 220, 180))]

            cell_w = inner_w // 6
            for i, (lbl, val, color) in enumerate(items):
                cx = stats_box.x + i * cell_w + cell_w // 2
                lf = p.get_font(13)
                ls = lf.render(lbl, True, (150, 160, 190))
                screen.blit(ls, ls.get_rect(center=(cx, stats_box.y + 22)))
                vf = p.get_font(22)
                vs = vf.render(str(val), True, color)
                screen.blit(vs, vs.get_rect(center=(cx, stats_box.y + 50)))

    # ==================================================================
    # EDITOR DE MOVES (dentro do painel direito)
    # ==================================================================
    def _render_moves_editor(self, screen, panel, pad, inner_w, start_y, form):
        p = self.parent
        y = start_y

        moves = form.setdefault("moves", [])

        # ---- Título da seção ----
        p.draw_section_title(screen, panel.x + pad, y, inner_w,
                             f"MOVES  ·  {len(moves)}/4")
        y += SECTION_TITLE_H

        # ---- Info de ajuda ----
        hint_f = p.get_font(12)
        hint = hint_f.render(
            "Clique em Trocar/Adicionar para abrir o seletor.",
            True, (150, 155, 180))
        screen.blit(hint, (panel.x + pad, y))
        y += 18

        # ---- 4 slots ----
        for slot in range(4):
            row_y = y + slot * (MOVE_ROW_H + 6)
            row_rect = pygame.Rect(panel.x + pad, row_y, inner_w, MOVE_ROW_H)

            filled = slot < len(moves) and moves[slot]

            if filled:
                pygame.draw.rect(screen, (30, 34, 52), row_rect, border_radius=8)
                pygame.draw.rect(screen, (90, 80, 130), row_rect, 1, border_radius=8)
            else:
                pygame.draw.rect(screen, (22, 24, 36), row_rect, border_radius=8)
                pygame.draw.rect(screen, (55, 55, 75), row_rect, 1, border_radius=8)

            # Slot number box
            num_rect = pygame.Rect(row_rect.x + 8, row_rect.y + 8, 34, MOVE_ROW_H - 16)
            num_bg = (60, 50, 100) if filled else (35, 35, 50)
            pygame.draw.rect(screen, num_bg, num_rect, border_radius=6)
            num_border = (170, 150, 220) if filled else (70, 70, 95)
            pygame.draw.rect(screen, num_border, num_rect, 1, border_radius=6)
            nf = p.get_font(18)
            ns = nf.render(str(slot + 1), True,
                           (230, 220, 255) if filled else (140, 140, 160))
            screen.blit(ns, ns.get_rect(center=num_rect.center))

            tx = num_rect.right + 12

            if filled:
                move = moves[slot]
                mname = move.get("name", "?")
                info = self._move_info_cache.get(mname.lower())
                mtype = info["type"] if info else "normal"
                cat = info["category"] if info else "physical"
                cur_pp = move.get("current_pp", info["pp"] if info else 0)
                max_pp = move.get("max_pp", info["pp"] if info else 0)

                # Nome
                name_f = p.get_font(17)
                name_s = name_f.render(mname, True, (255, 255, 255))
                screen.blit(name_s, (tx, row_rect.y + 8))

                # Tipo
                type_color = self.pokedex.get_type_color(mtype)
                tf = p.get_font(11)
                tt = tf.render(mtype.upper(), True, self._text_color_for_bg(type_color))
                tbadge = pygame.Rect(tx, row_rect.y + 30,
                                     tt.get_width() + 12, tt.get_height() + 4)
                pygame.draw.rect(screen, type_color, tbadge, border_radius=3)
                pygame.draw.rect(screen, (0, 0, 0), tbadge, 1, border_radius=3)
                screen.blit(tt, (tbadge.x + 6, tbadge.y + 2))

                # Categoria / PP
                info_f = p.get_font(12)
                info_s = info_f.render(
                    f"{cat.capitalize()}  ·  PP {cur_pp}/{max_pp}",
                    True, (180, 185, 210))
                screen.blit(info_s,
                            (tbadge.right + 10,
                             row_rect.y + 30 + (tbadge.height - info_s.get_height()) // 2))

                # Botões: [Trocar] [X]
                x_btn = pygame.Rect(row_rect.right - 40, row_rect.y + 11, 28, 32)
                ch_btn = pygame.Rect(x_btn.left - 80, row_rect.y + 11, 74, 32)
                p.register_click(f"move_remove_slot_{slot}", x_btn)
                p.register_click(f"move_edit_slot_{slot}", ch_btn)
                p.draw_button(screen, ch_btn, "Trocar", font_size=12)
                p.draw_button(screen, x_btn, "X", danger=True, font_size=14)
            else:
                # Slot vazio
                empty_f = p.get_font(14)
                es = empty_f.render("(vazio)", True, (110, 110, 130))
                screen.blit(es, (tx, row_rect.y + (MOVE_ROW_H - es.get_height()) // 2))

                add_btn = pygame.Rect(row_rect.right - 140, row_rect.y + 11, 130, 32)
                p.register_click(f"move_edit_slot_{slot}", add_btn)
                p.draw_button(screen, add_btn, "+ Adicionar", success=True, font_size=13)

    # ==================================================================
    # MODAL CENTRALIZADO — SELETOR DE MOVES
    # ==================================================================
    def _render_move_picker_modal(self, screen):
        """Renderiza o seletor de moves como um modal centralizado na tela.

        IMPORTANTE: este método é chamado por render_footer(), que roda APÓS
        o render() normal do debug_scene. Isso garante que:
          1. O backdrop (que cobre a tela inteira) é desenhado POR CIMA do
             rodapé e de qualquer outro elemento;
          2. Os cliques do modal são registrados DEPOIS de todos os cliques
             de outras partes da cena — assim o modal sempre ganha a
             prioridade em `find_click_at` e nada "vaza" para as páginas
             atrás.
        """
        p = self.parent

        # ---- Viewport (para centralizar de forma responsiva) ----
        sm = getattr(self.parent, 'screen_manager', None)
        if sm is not None:
            vx = sm.viewport_x
            vy = sm.viewport_y
            vw = sm.viewport_width
            vh = sm.viewport_height
        else:
            vx, vy = 0, 0
            vw, vh = screen.get_size()

        # ---- BACKDROP ----
        # Escurece toda a área do viewport e absorve cliques por completo.
        backdrop = pygame.Surface((vw, vh), pygame.SRCALPHA)
        backdrop.fill((0, 0, 0, 190))
        screen.blit(backdrop, (vx, vy))

        self._modal_backdrop_rect = pygame.Rect(vx, vy, vw, vh)
        p.register_click("move_modal_backdrop", self._modal_backdrop_rect)

        # ---- Dimensões do MODAL ----
        modal_w = min(880, int(vw * 0.78))
        modal_h = min(700, int(vh * 0.90))
        modal_x = vx + (vw - modal_w) // 2
        modal_y = vy + (vh - modal_h) // 2
        modal_rect = pygame.Rect(modal_x, modal_y, modal_w, modal_h)
        self._modal_rect = modal_rect

        # Sombra externa
        shadow = pygame.Surface((modal_w + 24, modal_h + 24), pygame.SRCALPHA)
        pygame.draw.rect(shadow, (0, 0, 0, 140),
                         (0, 0, shadow.get_width(), shadow.get_height()),
                         border_radius=16)
        screen.blit(shadow, (modal_x - 12, modal_y - 12))

        # Fundo do modal
        pygame.draw.rect(screen, (26, 30, 48), modal_rect, border_radius=12)
        pygame.draw.rect(screen, (140, 120, 200), modal_rect, 2, border_radius=12)

        # Painel do modal - absorve cliques que não atingem nenhum botão
        p.register_click("move_modal_panel", modal_rect)

        # --------------------- CABEÇALHO ---------------------
        header_rect = pygame.Rect(modal_x, modal_y, modal_w, 68)
        pygame.draw.rect(screen, (36, 32, 60), header_rect,
                         border_top_left_radius=12, border_top_right_radius=12)
        pygame.draw.line(screen, (140, 120, 200),
                         (header_rect.left, header_rect.bottom),
                         (header_rect.right, header_rect.bottom), 2)

        # Botão X (fechar) - canto superior direito
        close_size = 34
        close_rect = pygame.Rect(
            header_rect.right - close_size - 14,
            header_rect.y + (header_rect.height - close_size) // 2,
            close_size, close_size
        )
        p.register_click("move_modal_close", close_rect)
        p.draw_button(screen, close_rect, "X", danger=True, font_size=16)

        # Título
        title_f = p.get_font(22)
        title_s = title_f.render("Escolher Move", True, (255, 255, 255))
        screen.blit(title_s, (header_rect.x + MODAL_PAD, header_rect.y + 10))

        # Subtítulo com o slot atual
        slot_num = self.move_picker_slot + 1
        moves = self.edit_form.get("moves", []) if self.edit_form else []
        replacing = None
        if 0 <= self.move_picker_slot < len(moves):
            replacing = moves[self.move_picker_slot].get("name")
        sub_f = p.get_font(13)
        if replacing:
            sub_str = f"Slot {slot_num}  ·  Substituindo: {replacing}"
            sub_clr = (245, 180, 180)
        else:
            sub_str = f"Slot {slot_num}  ·  Adicionando novo move"
            sub_clr = (170, 225, 170)
        sub_s = sub_f.render(sub_str, True, sub_clr)
        screen.blit(sub_s, (header_rect.x + MODAL_PAD, header_rect.y + 38))

        # --------------------- BUSCA ---------------------
        y = header_rect.bottom + 14
        search_rect = pygame.Rect(
            modal_x + MODAL_PAD, y,
            modal_w - MODAL_PAD * 2, 38
        )
        p.register_click("move_search_input", search_rect)
        pygame.draw.rect(screen, (15, 15, 25), search_rect, border_radius=6)
        border = (255, 200, 60) if self.focused_input == "move_search" else (80, 80, 110)
        pygame.draw.rect(screen, border, search_rect, 2, border_radius=6)

        f = p.get_font(15)
        display = self.move_search_text if self.move_search_text else "Buscar move por nome..."
        color = (220, 220, 230) if self.move_search_text else (110, 110, 130)
        if self.focused_input == "move_search":
            display += "_"
        ts = f.render(display, True, color)
        screen.blit(ts, (search_rect.x + 12,
                         search_rect.y + (search_rect.height - ts.get_height()) // 2))

        if self.move_search_text:
            clr_rect = pygame.Rect(search_rect.right - 32, search_rect.y + 5, 28, 28)
            p.register_click("move_search_clear", clr_rect)
            p.draw_button(screen, clr_rect, "x", font_size=14)

        y = search_rect.bottom + 12

        # --------------------- LINHA DE FILTROS ---------------------
        # Coluna 1: Tipo (dropdown)
        lbl_f = p.get_font(13)
        lbl_color = (180, 190, 220)

        # ----- TIPO (dropdown) -----
        type_lbl = lbl_f.render("Tipo", True, lbl_color)
        screen.blit(type_lbl, (modal_x + MODAL_PAD, y + 4))

        type_btn_x = modal_x + MODAL_PAD + type_lbl.get_width() + 8
        type_btn_w = 160
        type_btn_h = 30
        type_btn_rect = pygame.Rect(type_btn_x, y, type_btn_w, type_btn_h)
        p.register_click("move_filter_type_btn", type_btn_rect)

        type_hovered = type_btn_rect.collidepoint(pygame.mouse.get_pos())
        type_open = (self.active_dropdown == "type")

        # Cor do botão (usa a cor do tipo selecionado, se houver)
        if self.move_filter_type:
            type_bg = self.pokedex.get_type_color(self.move_filter_type)
            type_bg = tuple(max(0, c - 30) for c in type_bg)
            type_text = self.move_filter_type.capitalize()
        else:
            type_bg = (60, 60, 85)
            type_text = "Todos"

        if type_open:
            type_bg = tuple(min(255, c + 30) for c in type_bg)
        elif type_hovered:
            type_bg = tuple(min(255, c + 15) for c in type_bg)

        pygame.draw.rect(screen, type_bg, type_btn_rect, border_radius=5)
        pygame.draw.rect(screen,
                         (255, 255, 255) if type_open else (110, 110, 140),
                         type_btn_rect, 2, border_radius=5)
        tbf = p.get_font(13)
        tb_txt = tbf.render(type_text, True, self._text_color_for_bg(type_bg))
        screen.blit(tb_txt, (type_btn_rect.x + 10,
                             type_btn_rect.y + (type_btn_h - tb_txt.get_height()) // 2))

        # Seta ▾
        arrow = "▲" if type_open else "▼"
        arw_f = p.get_font(12)
        arw_s = arw_f.render(arrow, True, self._text_color_for_bg(type_bg))
        screen.blit(arw_s, (type_btn_rect.right - arw_s.get_width() - 8,
                            type_btn_rect.y + (type_btn_h - arw_s.get_height()) // 2))

        # ----- CATEGORIA (botões) -----
        cat_lbl = lbl_f.render("Tipo do Ataque", True, lbl_color)
        cat_lbl_x = type_btn_rect.right + 20
        screen.blit(cat_lbl, (cat_lbl_x, y + 4))

        cat_btn_x = cat_lbl_x + cat_lbl.get_width() + 8
        cat_options = [
            ("Todos",    None,       (90, 90, 110)),
            ("Físico",   "physical", (200, 80, 80)),
            ("Especial", "special",  (130, 100, 220)),
            ("Status",   "status",   (150, 150, 150)),
        ]
        cat_btn_w = 70
        cat_btn_h = 30
        cat_gap = 5
        cx = cat_btn_x
        for label, val, base_color in cat_options:
            btn = pygame.Rect(cx, y, cat_btn_w, cat_btn_h)
            selected = (self.move_filter_category == val)
            hovered = btn.collidepoint(pygame.mouse.get_pos())
            bg = base_color if selected else tuple(max(0, c - 60) for c in base_color)
            if hovered and not selected:
                bg = tuple(min(255, c + 20) for c in bg)
            pygame.draw.rect(screen, bg, btn, border_radius=5)
            pygame.draw.rect(screen,
                             (255, 255, 255) if selected else (60, 60, 80),
                             btn, 2 if selected else 1, border_radius=5)
            bf = p.get_font(12)
            bt = bf.render(label, True, self._text_color_for_bg(bg))
            screen.blit(bt, bt.get_rect(center=btn.center))
            p.register_click(f"move_filter_cat_{val or 'all'}", btn)
            cx += cat_btn_w + cat_gap

        y += type_btn_h + 10

        # --------------------- LINHA 2: ACURÁCIA + SORT ---------------------
        # ----- ACURÁCIA (botões) -----
        acc_lbl = lbl_f.render("Acurácia", True, lbl_color)
        screen.blit(acc_lbl, (modal_x + MODAL_PAD, y + 4))

        acc_btn_x = modal_x + MODAL_PAD + acc_lbl.get_width() + 8
        acc_options = [
            ("Todas", "all",  (90, 90, 110)),
            ("> 50",  "gt50", (100, 180, 100)),
            ("≤ 50",  "le50", (200, 140, 70)),
        ]
        acc_btn_w = 72
        acc_btn_h = 30
        acc_gap = 5
        ax = acc_btn_x
        for label, val, base_color in acc_options:
            btn = pygame.Rect(ax, y, acc_btn_w, acc_btn_h)
            selected = (self.move_filter_accuracy == val)
            hovered = btn.collidepoint(pygame.mouse.get_pos())
            bg = base_color if selected else tuple(max(0, c - 60) for c in base_color)
            if hovered and not selected:
                bg = tuple(min(255, c + 20) for c in bg)
            pygame.draw.rect(screen, bg, btn, border_radius=5)
            pygame.draw.rect(screen,
                             (255, 255, 255) if selected else (60, 60, 80),
                             btn, 2 if selected else 1, border_radius=5)
            bf = p.get_font(12)
            bt = bf.render(label, True, self._text_color_for_bg(bg))
            screen.blit(bt, bt.get_rect(center=btn.center))
            p.register_click(f"move_filter_acc_{val}", btn)
            ax += acc_btn_w + acc_gap

        # ----- SORT (à direita) -----
        sort_w = 150
        sort_h = 30
        sort_rect = pygame.Rect(modal_rect.right - MODAL_PAD - sort_w, y,
                                sort_w, sort_h)
        sort_label = "Ordenar: Poder ↓" if self.move_sort_mode == "power" else "Ordenar: A-Z"
        p.register_click("move_sort_toggle", sort_rect)
        p.draw_button(screen, sort_rect, sort_label, font_size=12)

        y += acc_btn_h + 12

        # --------------------- CONTAGEM / SEPARADOR ---------------------
        sep_y = y
        pygame.draw.line(screen, (60, 60, 90),
                         (modal_x + MODAL_PAD, sep_y),
                         (modal_rect.right - MODAL_PAD, sep_y), 1)
        y += 8

        cnt_f = p.get_font(12)
        cnt_s = cnt_f.render(
            f"{len(self.filtered_move_names)} move(s) encontrados",
            True, (150, 160, 190))
        screen.blit(cnt_s, (modal_x + MODAL_PAD, y))
        y += cnt_s.get_height() + 6

        # --------------------- LISTA DE MOVES ---------------------
        list_top = y
        list_bottom = modal_rect.bottom - 14
        list_h = list_bottom - list_top
        row_h = MODAL_ROW_H
        visible = max(1, list_h // row_h)
        self._visible_move_picker_n = visible

        total = len(self.filtered_move_names)
        max_s = max(0, total - visible)
        self.move_picker_scroll = max(0, min(max_s, self.move_picker_scroll))

        start = self.move_picker_scroll
        end = min(total, start + visible)

        show_scroll = total > visible
        list_left = modal_x + MODAL_PAD
        list_width = modal_w - MODAL_PAD * 2 - (14 if show_scroll else 0)

        # ---- Slot list frame ----
        frame_rect = pygame.Rect(list_left - 4, list_top - 4,
                                 list_width + 8, list_h + 8)
        pygame.draw.rect(screen, (20, 22, 34), frame_rect, border_radius=8)
        pygame.draw.rect(screen, (60, 60, 90), frame_rect, 1, border_radius=8)

        # ---- Pré-calcula moves já equipados ----
        equipped_slots = {}
        if self.edit_form:
            for si, m_dict in enumerate(self.edit_form.get("moves", [])):
                nm = (m_dict.get("name") or "").lower()
                if nm:
                    equipped_slots.setdefault(nm, []).append(si + 1)

        # ---- Estado vazio ----
        if total == 0:
            ef = p.get_font(15)
            es = ef.render("Nenhum move encontrado com esses filtros.",
                           True, (160, 160, 180))
            screen.blit(es, es.get_rect(center=(modal_rect.centerx,
                                                 list_top + list_h // 2)))
        else:
            # ---- Renderiza linhas ----
            for i in range(start, end):
                idx = i - start
                move_name = self.filtered_move_names[i]
                row = pygame.Rect(list_left, list_top + idx * row_h,
                                  list_width, row_h - 4)
                hovered = row.collidepoint(pygame.mouse.get_pos())

                if hovered:
                    bg = (48, 42, 70)
                    border = (140, 120, 200)
                else:
                    bg = (30, 32, 48)
                    border = (60, 60, 85)

                pygame.draw.rect(screen, bg, row, border_radius=6)
                pygame.draw.rect(screen, border, row,
                                 2 if hovered else 1, border_radius=6)
                p.register_click(f"move_pick_idx_{i}", row)

                info = self._move_info_cache.get(move_name.lower())
                mtype = info["type"] if info else "normal"
                cat = info["category"] if info else "physical"
                power = info.get("power", 0) if info else 0
                acc = info.get("accuracy", 100) if info else 100
                pp = info.get("pp", 0) if info else 0
                desc = info.get("description", "") if info else ""

                # ---- Type badge (à direita) ----
                type_color = self.pokedex.get_type_color(mtype)
                tf = p.get_font(11)
                tt = tf.render(mtype.upper(), True, self._text_color_for_bg(type_color))
                tbadge_w = tt.get_width() + 14
                tbadge = pygame.Rect(row.right - 10 - tbadge_w, row.y + 8,
                                     tbadge_w, 18)
                pygame.draw.rect(screen, type_color, tbadge, border_radius=3)
                pygame.draw.rect(screen, (0, 0, 0), tbadge, 1, border_radius=3)
                screen.blit(tt, tt.get_rect(center=tbadge.center))

                # ---- Stats (à esquerda do badge) ----
                sf = p.get_font(12)
                cat_pt = {"physical": "Físico",
                          "special": "Especial",
                          "status": "Status"}.get(cat, cat.capitalize())
                pwr_str = f"{power}" if power and power > 0 else "—"
                acc_str = f"{acc}" if acc and acc > 0 else "—"
                stats_str = f"{cat_pt}  ·  PWR {pwr_str}  ·  ACC {acc_str}  ·  PP {pp}"
                stats_s = sf.render(stats_str, True, (180, 185, 210))
                stats_x = tbadge.left - 12 - stats_s.get_width()
                stats_y = row.y + 8 + (18 - stats_s.get_height()) // 2
                screen.blit(stats_s, (stats_x, stats_y))

                # ---- Nome (esquerda, truncado) ----
                nf = p.get_font(16)
                name_max_w = stats_x - (row.x + 12) - 8
                disp_name = move_name
                while nf.size(disp_name)[0] > name_max_w and len(disp_name) > 4:
                    disp_name = disp_name[:-2] + "…"
                name_color = (255, 255, 255) if hovered else (235, 235, 245)
                ns = nf.render(disp_name, True, name_color)
                screen.blit(ns, (row.x + 12, row.y + 6))

                # ---- Indicador "Slot N" (já equipado) ----
                key = move_name.lower()
                tag_right_edge = None
                if key in equipped_slots:
                    slots_txt = "Slot " + ",".join(str(s) for s in equipped_slots[key])
                    ef2 = p.get_font(10)
                    es2 = ef2.render(slots_txt, True, (255, 220, 120))
                    tag_rect = pygame.Rect(row.x + 12, row.y + 26,
                                           es2.get_width() + 10, 15)
                    pygame.draw.rect(screen, (60, 50, 20), tag_rect, border_radius=3)
                    pygame.draw.rect(screen, (170, 140, 60), tag_rect, 1, border_radius=3)
                    screen.blit(es2, (tag_rect.x + 5, tag_rect.y + 1))
                    tag_right_edge = tag_rect.right

                # ---- Descrição (linha de baixo) ----
                if desc:
                    df = p.get_font(11)
                    desc_x = row.x + 12
                    if tag_right_edge:
                        desc_x = tag_right_edge + 8
                    max_desc_w = (row.right - 12) - desc_x - 120
                    if max_desc_w < 40:
                        max_desc_w = 40
                    d_txt = desc
                    while df.size(d_txt)[0] > max_desc_w and len(d_txt) > 3:
                        d_txt = d_txt[:-2] + "…"
                    ds = df.render(d_txt, True, (140, 145, 170))
                    screen.blit(ds, (desc_x, row.y + 28))

            # ---- Scrollbar (arrastável) ----
            if show_scroll:
                bar_x = modal_rect.right - 14
                self._mp_scroll_geom = (bar_x, list_top, list_h, total, visible)
                thumb_h = max(24, int(list_h * visible / total))
                thumb_y = list_top + int((list_h - thumb_h) * self.move_picker_scroll / max_s)

                pygame.draw.rect(screen, (40, 40, 60),
                                 (bar_x, list_top, 6, list_h), border_radius=3)
                pygame.draw.rect(screen, (160, 130, 210),
                                 (bar_x, thumb_y, 6, thumb_h), border_radius=3)

                # Área clicável mais larga para facilitar o arrasto
                self._mp_scrollbar_rect = pygame.Rect(bar_x - 5, list_top, 16, list_h)
                self._mp_scrollbar_thumb_rect = pygame.Rect(bar_x, thumb_y, 6, thumb_h)
            else:
                self._mp_scrollbar_rect = None
                self._mp_scrollbar_thumb_rect = None

        # --------------------- DROPDOWN DE TIPO (por cima) ---------------------
        # Renderizado POR ÚLTIMO para ficar visualmente sobre a lista
        # e ter prioridade de clique (find_click_at percorre reversed).
        if self.active_dropdown == "type":
            self._render_type_dropdown(screen, type_btn_rect)

    def _render_type_dropdown(self, screen, anchor_rect):
        """Renderiza o dropdown de tipos abaixo do botão de tipo.

        Layout: grade de 3 colunas por N linhas, com botões coloridos
        por tipo. `Todos` é a primeira opção (cinza).
        """
        p = self.parent

        # Opções: ("Todos", None) + 18 tipos
        options = [("Todos", None)] + [(t.capitalize(), t) for t in _ALL_TYPES_ORDERED]

        cols = 3
        btn_w = 92
        btn_h = 26
        pad = 8
        gap_x = 6
        gap_y = 6

        rows = (len(options) + cols - 1) // cols
        dd_w = cols * btn_w + (cols - 1) * gap_x + pad * 2
        dd_h = rows * btn_h + (rows - 1) * gap_y + pad * 2

        # Posição: abaixo do anchor, alinhado à esquerda
        dd_x = anchor_rect.x
        dd_y = anchor_rect.bottom + 4

        # Ajuste se sair do modal pela direita/baixo
        modal = self._modal_rect
        if modal:
            if dd_x + dd_w > modal.right - 6:
                dd_x = modal.right - 6 - dd_w
            if dd_y + dd_h > modal.bottom - 6:
                dd_y = anchor_rect.y - dd_h - 4

        dd_rect = pygame.Rect(dd_x, dd_y, dd_w, dd_h)

        # Sombra
        shadow = pygame.Surface((dd_w + 12, dd_h + 12), pygame.SRCALPHA)
        pygame.draw.rect(shadow, (0, 0, 0, 150),
                         (0, 0, shadow.get_width(), shadow.get_height()),
                         border_radius=10)
        screen.blit(shadow, (dd_x - 6, dd_y - 6))

        # Fundo do dropdown
        pygame.draw.rect(screen, (34, 30, 54), dd_rect, border_radius=8)
        pygame.draw.rect(screen, (140, 120, 200), dd_rect, 2, border_radius=8)

        # Importante: registrar o painel do dropdown para absorver cliques
        # (assim clicar em área vazia do dropdown NÃO fecha o modal)
        p.register_click("move_dd_type_panel", dd_rect)

        # Renderiza as opções em grade
        for i, (label, val) in enumerate(options):
            col = i % cols
            row = i // cols
            bx = dd_rect.x + pad + col * (btn_w + gap_x)
            by = dd_rect.y + pad + row * (btn_h + gap_y)
            btn = pygame.Rect(bx, by, btn_w, btn_h)

            selected = (self.move_filter_type == val)
            hovered = btn.collidepoint(pygame.mouse.get_pos())

            if val is None:
                base = (90, 90, 110)
            else:
                base = self.pokedex.get_type_color(val)

            if selected:
                bg = base
            else:
                bg = tuple(max(0, c - 65) for c in base)
                if hovered:
                    bg = tuple(min(255, c + 25) for c in bg)

            pygame.draw.rect(screen, bg, btn, border_radius=4)
            pygame.draw.rect(screen,
                             (255, 255, 255) if selected else (60, 60, 80),
                             btn, 2 if selected else 1, border_radius=4)

            bf = p.get_font(12)
            bt = bf.render(label, True, self._text_color_for_bg(bg))
            screen.blit(bt, bt.get_rect(center=btn.center))

            # Nome de registro com o valor (para saber qual aplicar)
            key = val if val else "all"
            p.register_click(f"move_dd_type_opt_{key}", btn)

    # ==================================================================
    # FOOTER
    # ==================================================================
    def render_footer(self, screen, footer_rect):
        p = self.parent

        # ==============================================================
        # MODAL DE MOVES ABERTO: renderiza modal por cima de TUDO
        # e ignora o rodapé normal (sem botões, sem cliques).
        # ==============================================================
        if self.move_picker_open:
            # Limpa as rects da scrollbar do modal — serão registradas
            # durante o render do modal.
            self._mp_scrollbar_rect = None
            self._mp_scrollbar_thumb_rect = None
            self._mp_scroll_geom = None

            # Desenha o modal (backdrop + painel + lista + dropdown).
            # Isso registra os cliques do modal DEPOIS dos cliques do
            # resto da cena (rodapé inclusive), garantindo prioridade.
            self._render_move_picker_modal(screen)
            return

        # ==============================================================
        # RODAPÉ NORMAL
        # ==============================================================
        btn_h = min(44, footer_rect.height - 14)
        btn_y = footer_rect.y + (footer_rect.height - btn_h) // 2
        hint_f = p.get_font(14)

        if self.mode == self.MODE_CREATE:
            box_rect = pygame.Rect(footer_rect.x + 24, btn_y, 240, btn_h)
            p.register_click("action_add_box", box_rect)
            p.draw_button(screen, box_rect, "Adicionar à BOX",
                          primary=True, font_size=17)

            team_rect = pygame.Rect(box_rect.right + 16, btn_y, 240, btn_h)
            p.register_click("action_add_team", team_rect)
            p.draw_button(screen, team_rect, "Adicionar ao TIME",
                          success=True, font_size=17)

            hint = hint_f.render(
                "ESC: voltar   ·   Scroll: navegar   ·   Arraste a barra lateral",
                True, (140, 140, 160))
        else:
            save_rect = pygame.Rect(footer_rect.x + 24, btn_y, 260, btn_h)
            p.register_click("action_save_edit", save_rect)
            p.draw_button(screen, save_rect, "SALVAR ALTERAÇÕES",
                          success=True, font_size=17)

            del_rect = pygame.Rect(save_rect.right + 16, btn_y, 170, btn_h)
            p.register_click("action_delete", del_rect)
            p.draw_button(screen, del_rect, "REMOVER", danger=True, font_size=17)

            if self.edit_subtab == self.SUBTAB_MOVES:
                hint_text = "Trocar/Adicionar move   ·   X para remover   ·   Salvar para aplicar"
            else:
                hint_text = "ESC: voltar   ·   Scroll: navegar   ·   Arraste a barra lateral"

            hint = hint_f.render(hint_text, True, (140, 140, 160))

        screen.blit(hint, (footer_rect.right - hint.get_width() - 24,
                           footer_rect.y + (footer_rect.height - hint.get_height()) // 2))