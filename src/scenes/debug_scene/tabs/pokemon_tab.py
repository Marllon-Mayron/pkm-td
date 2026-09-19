# src/scenes/debug_scene/tabs/pokemon_tab.py
"""
Aba POKÉMON — criação e edição de Pokémon do save.
Layout maior, com portraits e divisões visuais claras.
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


class PokemonTab:
    MODE_CREATE = "create"
    MODE_EDIT = "edit"
    INPUT_NAMES = {"input_name", "input_search", "edit_input_name"}

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

        try:
            from src.data.held_item_data import (
                HELD_ITEM_TYPE_MAPPING, HELD_ITEM_SPECIAL_EFFECTS,
            )
            ids = list(HELD_ITEM_TYPE_MAPPING.keys()) + list(HELD_ITEM_SPECIAL_EFFECTS.keys())
            self.held_items = [None] + sorted(set(ids))
        except Exception:
            self.held_items = [None]

        # ===== Estado da scrollbar (drag) =====
        self._scroll_dragging = False
        self._scroll_geom = None  # (bar_x, list_y, list_h, total, visible, target)
        self._scrollbar_rect = None
        self._scrollbar_thumb_rect = None
        self._scrollbar_thumb_h = 0
        self._scroll_thumb_offset = 0

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

    # ==================================================================
    # INTERFACE COM O PAI
    # ==================================================================
    def has_focus(self):
        return self.focused_input is not None

    def get_focus(self):
        return self.focused_input

    def clear_focus(self):
        self.focused_input = None

    # ==================================================================
    # DRAG DA SCROLLBAR
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
    # EVENTOS
    # ==================================================================
    def handle_event(self, event):
        # ===== Scrollbar drag (prioridade máxima) =====
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

        # ===== Wheel =====
        if event.type == pygame.MOUSEWHEEL:
            if self.mode == self.MODE_CREATE:
                max_s = max(0, len(self.filtered_ids) - self._visible_create_n)
                self.list_scroll = max(0, min(max_s, self.list_scroll - event.y))
            else:
                max_s = max(0, len(self.edit_targets) - self._visible_edit_n)
                self.edit_scroll = max(0, min(max_s, self.edit_scroll - event.y))
            return

        # ===== Mouse down (clicks) =====
        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            clicked = self.parent.find_click_at(event.pos)
            if clicked not in self.INPUT_NAMES:
                self.focused_input = None
            if clicked:
                self.on_click(clicked)
            return

        # ===== Teclado =====
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

    def on_click(self, name):
        if name == "poke_mode_create":
            self.mode = self.MODE_CREATE
            self.focused_input = None
            return
        if name == "poke_mode_edit":
            self.mode = self.MODE_EDIT
            self.focused_input = None
            self._refresh_edit_targets()
            if self.edit_targets:
                self.edit_selected = min(self.edit_selected, len(self.edit_targets) - 1)
                self._load_edit_form()
            else:
                self.edit_form = None
            return

        if name.startswith("list_item_"):
            try:
                idx = int(name[len("list_item_"):])
            except ValueError:
                return
            if 0 <= idx < len(self.filtered_ids):
                self.list_selected = idx
                self.form["pokemon_id"] = self.filtered_ids[idx]
            return

        if name.startswith("edit_item_"):
            try:
                idx = int(name[len("edit_item_"):])
            except ValueError:
                return
            if 0 <= idx < len(self.edit_targets):
                self.edit_selected = idx
                self._load_edit_form()
            return

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
            self.edit_form = {
                "pokemon_id": p.id, "level": p.level,
                "ivs": dict(p.ivs), "shiny": p.is_shiny,
                "gender": p.gender, "nature": p.nature,
                "custom_name": p.custom_name or "",
                "held_item": p.held_item,
            }
        else:
            d = player.pc_box[target["index"]]
            self.edit_form = {
                "pokemon_id": d.get("id", 1),
                "level": d.get("level", 5),
                "ivs": dict(d.get("ivs", {s: 0 for s in _IV_STATS})),
                "shiny": d.get("is_shiny", False),
                "gender": d.get("gender"),
                "nature": d.get("nature", "Hardy"),
                "custom_name": d.get("custom_name") or "",
                "held_item": d.get("held_item"),
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

        self.parent.save_game()
        self.parent.show_message("Pokémon atualizado!")
        sound_manager.play_effect(SoundEffect.CLICK, volume=0.3)

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

        # ============== IDENTIDADE ==============
        p.draw_section_title(screen, panel.x + pad, y, inner_w, "IDENTIDADE")
        y += SECTION_TITLE_H

        p.render_toggle(screen, panel.x + pad, y, inner_w, FORM_ROW_H,
                        "Shiny", form["shiny"], f"{cb_prefix}shiny_toggle")
        y += FORM_ROW_H + FORM_ROW_GAP

        p.render_gender_row(screen, panel.x + pad, y, inner_w, FORM_ROW_H,
                            "Gênero", form["gender"], f"{cb_prefix}gender")
        y += FORM_ROW_H + SECTION_GAP

        # ============== ATRIBUTOS ==============
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

        # ============== IVs ==============
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

        # ============== PREVIEW ==============
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

    # ---------- FOOTER ----------
    def render_footer(self, screen, footer_rect):
        p = self.parent
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

            hint = hint_f.render("ESC: voltar   ·   Scroll: navegar   ·   Arraste a barra lateral",
                                 True, (140, 140, 160))

        screen.blit(hint, (footer_rect.right - hint.get_width() - 24,
                           footer_rect.y + (footer_rect.height - hint.get_height()) // 2))