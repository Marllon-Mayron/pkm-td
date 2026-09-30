# src/scenes/game_scene/components/managers/in_game_debug_manager.py
"""
In-Game Debug Manager v4 — painel flutuante, arrastável, redimensionável (F2).

Mudanças v4:
  - BUGFIX: dropdowns nao abriam (self._dropdown_trigger_rect nunca era setado)
  - BUGFIX: pause nao sincronizava corretamente ao fechar/minimizar
  - Day/Night e Weather viraram DROPDOWNS (menos poluicao visual)
  - Painel ARRASTAVEL pelo header
  - Painel REDIMENSIONAVEL pelo canto inferior direito (min 40% do viewport)
  - Minimizar nao mexe no estado de pausa
"""
import pygame
import random
from typing import Optional, List, Dict, Any, Tuple

from src.data.pokedex import Pokedex
from src.data.move_data import MoveData
from src.data.item_bag_catalog import item_bag_catalog
from src.battle.attack_pattern import AttackPattern
from src.battle.effects.specific.weather.weather_state import WeatherType
from src.battle.effects.specific.day_night.day_night_state import DayNightType, DayNightState
from src.entities.move import Move


# =============================================================
# FONTES
# =============================================================
_FONT_CACHE: Dict[int, pygame.font.Font] = {}


def _get_font(size: int) -> pygame.font.Font:
    size = max(10, int(size))
    if size not in _FONT_CACHE:
        _FONT_CACHE[size] = pygame.font.Font(None, size)
    return _FONT_CACHE[size]


# Layout base (px)
FONT_TITLE = 22
FONT_SECTION = 15
FONT_BASE = 16
FONT_BUTTON = 16
FONT_SMALL = 14
FONT_BIG = 26

BTN_H = 32
BTN_H_LG = 40
SLIDER_H = 24
INPUT_H = 34
HEADER_H = 42
TAB_H = 34
PANEL_PAD = 22

# =============================================================
# TABELAS
# =============================================================
_TABS = [
    ("ambiente", "AMBIENTE"),
    ("waves", "WAVES"),
    ("spawn", "SPAWN"),
    ("editar", "EDITAR"),
    ("god", "GOD"),
]

from src.battle.effects.specific.weather.weather_state import (
    WeatherType, get_weather_ui_options, weather_from_string,
)
from src.battle.effects.specific.day_night.day_night_state import (
    DayNightType, get_day_night_ui_options, day_night_from_string,
)

_DAY_NIGHT_OPTIONS = get_day_night_ui_options()
_WEATHER_OPTIONS = get_weather_ui_options()

_ALL_ATTACK_PATTERNS = [
    (AttackPattern.RANDOM, "Aleatorio"),
    (AttackPattern.AGGRESSIVE, "Agressivo"),
    (AttackPattern.VICIOUS, "Vicioso"),
    (AttackPattern.VICIOUS_SELECTIVE, "Vicioso Seletivo"),
    (AttackPattern.PASSIVE, "Passivo"),
]


# =============================================================
# MANAGER
# =============================================================
class InGameDebugManager:
    _active_manager = None

    # ---------------------------------------------------------
    # INIT
    # ---------------------------------------------------------
    def __init__(self, game_scene):
        InGameDebugManager._active_manager = self
        self.gs = game_scene

        # Estado geral
        self.visible = False
        self.minimized = False
        self.pause_on_edit = False
        self.active_tab = "ambiente"

        # Dados
        self.pokedex = Pokedex()
        self.move_data = MoveData()
        self.item_catalog = item_bag_catalog

        # UI
        self._clicks: List[Tuple[str, pygame.Rect]] = []
        self._sliders: Dict[str, Tuple[float, float, Any]] = {}
        self.panel_rect: Optional[pygame.Rect] = None

        # Layout
        self._panel_x = 0
        self._panel_y = 0
        self._panel_w = 0
        self._panel_h = 0

        # Drag painel
        self._panel_dragging = False
        self._panel_drag_offset = (0, 0)

        # Resize
        self._resizing = False
        self._resize_start_mouse = (0, 0)
        self._resize_start_size = (0, 0)
        self._resize_handle_size = 20

        # Scroll
        self.scroll_y = 0
        self._scroll_max = 0
        self._scroll_content_h = 0
        self._scroll_dragging = False
        self._scroll_thumb_offset = 0
        self._scrollbar_rect: Optional[pygame.Rect] = None
        self._scrollbar_thumb_rect: Optional[pygame.Rect] = None

        # Slider drag
        self._dragging_slider: Optional[str] = None

        # Dropdown
        self.active_dropdown: Optional[Tuple[str, Any]] = None
        self.dropdown_search = ""
        self.dropdown_scroll = 0
        self._search_focused = False
        self._all_dropdown_entries: List[Tuple[Any, str, Any]] = []
        self._dropdown_entries: List[Tuple[Any, str, Any]] = []
        self._dropdown_rect: Optional[pygame.Rect] = None
        self._dropdown_trigger_rect: Optional[pygame.Rect] = None

        # SPAWN
        self.spawn_form = {
            "pokemon_id": 1,
            "level": 10,
            "shiny": False,
            "boss": False,
            "moves": ["", "", "", ""],
            "held_item": None,
            "pattern": AttackPattern.RANDOM,
            "path_index": 0,
        }

        # EDIT
        self.edit_selected = 0
        self.edit_scroll = 0

        # God
        self.god = {
            "team_invincible": False,
            "one_hit_kill": False,
            "enemies_1hp": False,
            "infinite_money": False,
            "no_cooldown": False,
            "no_pp": False,
            "disable_spawn": False,
            "damage_x10": False,
            "show_hitboxes": False,
        }
        self.fast_forward_mult = 1
        self._ff_options = [1, 2, 3, 4]
        self._seen_enemy_ids = set()

        # Pausa
        self._debug_pause_active = False
        self._saved_pause = {
            "paused": False,
            "game_paused": False,
            "wave_paused": False,
        }

        # Ambiente
        self._weather_duration = 30

        # Hooks
        self._install_hooks()

    # =========================================================
    # HOOKS (God Mode)
    # =========================================================
    def _install_hooks(self):
        from src.entities.pokemon import Pokemon
        if hasattr(Pokemon, "_orig_take_damage_for_debug"):
            return

        Pokemon._orig_take_damage_for_debug = Pokemon.take_damage

        def _patched_take_damage(self, damage, attacker=None):
            mgr = InGameDebugManager._active_manager
            if mgr is not None:
                if mgr.god["team_invincible"] and not self.is_wild:
                    return False
                if mgr.god["one_hit_kill"] and self.is_wild:
                    damage = 999999
                if mgr.god["damage_x10"]:
                    if attacker is not None and not attacker.is_wild and self.is_wild:
                        damage = int(damage * 10)
            return Pokemon._orig_take_damage_for_debug(self, damage, attacker)

        Pokemon.take_damage = _patched_take_damage
        print("[DEBUG_MANAGER] Hook instalado em Pokemon.take_damage")

    # =========================================================
    # API PUBLICA
    # =========================================================
    def get_time_multiplier(self) -> float:
        return float(self.fast_forward_mult)

    def is_visible(self) -> bool:
        return self.visible

    def toggle(self):
        """Abre/fecha o painel. Aplica o estado de pausa IMEDIATAMENTE."""
        self.visible = not self.visible

        if not self.visible:
            self._close_dropdown()
            self._panel_dragging = False
            self._scroll_dragging = False
            self._dragging_slider = None
            self._resizing = False
            try:
                pygame.mouse.set_cursor(pygame.SYSTEM_CURSOR_ARROW)
            except Exception:
                pass

        # Aplica pausa/restaura IMEDIATAMENTE
        self._apply_pause_state()

    # =========================================================
    # PAUSA
    # =========================================================
    def _apply_pause_state(self):
        """
        Aplica o estado de pausa baseado em:
            should_pause = self.visible AND self.pause_on_edit

        Se should_pause=True e ainda nao pausamos: salva + pausa.
        Se should_pause=False e estavamos pausando: restaura.

        Chamado IMEDIATAMENTE por toggle() e pelo checkbox.
        """
        should_pause = self.visible and self.pause_on_edit

        if should_pause and not self._debug_pause_active:
            self._saved_pause["paused"] = bool(getattr(self.gs, "paused", False))
            self._saved_pause["game_paused"] = bool(getattr(self.gs, "game_paused", False))
            wm = getattr(self.gs, "wave_manager", None)
            self._saved_pause["wave_paused"] = bool(getattr(wm, "paused", False)) if wm else False

            self.gs.paused = True
            self.gs.game_paused = True
            if wm:
                wm.paused = True

            self._debug_pause_active = True
            print("[DEBUG_MANAGER] Jogo PAUSADO pelo painel de debug")

        elif not should_pause and self._debug_pause_active:
            self.gs.paused = self._saved_pause["paused"]
            self.gs.game_paused = self._saved_pause["game_paused"]
            wm = getattr(self.gs, "wave_manager", None)
            if wm:
                wm.paused = self._saved_pause["wave_paused"]

            self._debug_pause_active = False
            print("[DEBUG_MANAGER] Jogo RESTAURADO pelo painel de debug")

    # =========================================================
    # HANDLE EVENT
    # =========================================================
    def handle_event(self, event) -> bool:
        if event.type == pygame.KEYDOWN and event.key == pygame.K_F2:
            self.toggle()
            return True

        if not self.visible:
            return False

        if event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE:
            if self.active_dropdown:
                self._close_dropdown()
            else:
                self.toggle()
            return True

        # Motion
        if event.type == pygame.MOUSEMOTION:
            if self._dragging_slider:
                self._update_slider_from_mouse(self._dragging_slider, event.pos)
                return True
            if self._resizing:
                self._update_resize_from_mouse(event.pos)
                return True
            if self._panel_dragging:
                mx, my = event.pos
                self._panel_x = mx - self._panel_drag_offset[0]
                self._panel_y = my - self._panel_drag_offset[1]
                self._clamp_panel_position()
                return True
            if self._scroll_dragging:
                self._update_scroll_from_mouse(event.pos[1])
                return True

        if event.type == pygame.MOUSEBUTTONUP and event.button == 1:
            if self._dragging_slider:
                self._dragging_slider = None
                return True
            if self._resizing:
                self._resizing = False
                pygame.mouse.set_cursor(pygame.SYSTEM_CURSOR_ARROW)
                return True
            if self._panel_dragging:
                self._panel_dragging = False
                return True
            if self._scroll_dragging:
                self._scroll_dragging = False
                return True

        # Dropdown tem prioridade
        if self.active_dropdown is not None:
            return self._handle_dropdown_event(event)

        # Wheel pra scroll
        if event.type == pygame.MOUSEWHEEL:
            if self.panel_rect and self.panel_rect.collidepoint(pygame.mouse.get_pos()):
                if self._scroll_max > 0:
                    self.scroll_y = max(0, min(self._scroll_max,
                                                self.scroll_y - event.y * 32))
                return True
            return False

        # Clique
        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            # Resize handle
            resize_rect = self._get_resize_handle_rect()
            if resize_rect and resize_rect.collidepoint(event.pos):
                self._resizing = True
                self._resize_start_mouse = event.pos
                self._resize_start_size = (self._panel_w, self._panel_h)
                try:
                    pygame.mouse.set_cursor(pygame.SYSTEM_CURSOR_SIZENWSE)
                except Exception:
                    pass
                return True

            clicked = self._find_click_at(event.pos)

            if clicked and clicked in self._sliders:
                self._dragging_slider = clicked
                self._update_slider_from_mouse(clicked, event.pos)
                return True

            if clicked:
                self._on_click(clicked)
                return True

            # Header = drag
            if self.panel_rect:
                header_rect = pygame.Rect(self._panel_x, self._panel_y,
                                          self._panel_w, HEADER_H)
                if header_rect.collidepoint(event.pos):
                    self._panel_dragging = True
                    self._panel_drag_offset = (
                        event.pos[0] - self._panel_x,
                        event.pos[1] - self._panel_y,
                    )
                    return True

            # Clique fora → fecha
            if self.panel_rect and not self.panel_rect.collidepoint(event.pos):
                self.toggle()
                return True

            return True

        if event.type == pygame.KEYDOWN and self._search_focused:
            return True

        return True

    # =========================================================
    # DROPDOWN
    # =========================================================
    def _open_dropdown(self, key, entries):
        self.active_dropdown = key
        self.dropdown_search = ""
        self.dropdown_scroll = 0
        self._search_focused = True
        self._all_dropdown_entries = list(entries)
        self._refresh_dropdown_entries()

    def _refresh_dropdown_entries(self):
        q = self.dropdown_search.strip().lower()
        if not q:
            self._dropdown_entries = list(self._all_dropdown_entries)
        else:
            self._dropdown_entries = [
                e for e in self._all_dropdown_entries
                if q in str(e[0]).lower() or q in e[1].lower()
            ]

    def _close_dropdown(self):
        self.active_dropdown = None
        self.dropdown_search = ""
        self.dropdown_scroll = 0
        self._search_focused = False
        self._dropdown_rect = None
        self._dropdown_trigger_rect = None

    def _handle_dropdown_event(self, event) -> bool:
        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            clicked = self._find_click_at(event.pos)

            if clicked and clicked.startswith("dd_pick_"):
                try:
                    idx = int(clicked[len("dd_pick_"):])
                    if 0 <= idx < len(self._dropdown_entries):
                        _, _, value = self._dropdown_entries[idx]
                        self._apply_dropdown_selection(self.active_dropdown, value)
                except Exception as e:
                    print(f"[DEBUG] dropdown pick erro: {e}")
                self._close_dropdown()
                return True

            if clicked == "dd_search":
                self._search_focused = True
                return True
            if clicked == "dd_panel":
                self._search_focused = False
                return True

            kind, sub = self.active_dropdown
            trigger_name = f"dd_open_{kind}_{sub}"
            if clicked == trigger_name:
                self._close_dropdown()
                return True

            if clicked and clicked.startswith("dd_open_"):
                self._close_dropdown()
                self._on_click(clicked)
                return True

            if self.panel_rect and not self.panel_rect.collidepoint(event.pos):
                self._close_dropdown()
                self.toggle()
                return True

            self._close_dropdown()
            return True

        if event.type == pygame.MOUSEWHEEL:
            if self._dropdown_rect and \
                    self._dropdown_rect.collidepoint(pygame.mouse.get_pos()):
                self.dropdown_scroll = max(0, self.dropdown_scroll - event.y)
            return True

        if event.type == pygame.KEYDOWN and self._search_focused:
            if event.key == pygame.K_BACKSPACE:
                self.dropdown_search = self.dropdown_search[:-1]
                self._refresh_dropdown_entries()
                self.dropdown_scroll = 0
                return True
            if event.key in (pygame.K_RETURN, pygame.K_TAB):
                self._search_focused = False
                return True
            if event.key == pygame.K_ESCAPE:
                self._close_dropdown()
                return True
            if event.unicode and event.unicode.isprintable():
                if len(self.dropdown_search) < 30:
                    self.dropdown_search += event.unicode
                    self._refresh_dropdown_entries()
                    self.dropdown_scroll = 0
                return True
            return True

        return True

    def _apply_dropdown_selection(self, key, value):
        kind, sub = key
        if kind == "spawn_pokemon":
            self.spawn_form["pokemon_id"] = value
        elif kind == "spawn_move":
            self.spawn_form["moves"][sub] = value or ""
        elif kind == "spawn_held":
            self.spawn_form["held_item"] = value
        elif kind == "spawn_pattern":
            self.spawn_form["pattern"] = value
        elif kind == "spawn_path":
            self.spawn_form["path_index"] = value
        elif kind == "edit_move":
            enemy = self._get_selected_enemy()
            if enemy:
                self._set_enemy_move(enemy, sub, value)
        elif kind == "edit_held":
            enemy = self._get_selected_enemy()
            if enemy:
                self._set_enemy_held(enemy, value)
        elif kind == "edit_pattern":
            enemy = self._get_selected_enemy()
            if enemy:
                self._set_enemy_pattern(enemy, value)
        elif kind == "dn_select":
            self._set_day_night_type(value)
        elif kind == "weather_select":
            self._set_weather_type(value)

    # =========================================================
    # ENTRY LISTS
    # =========================================================
    def _get_pokemon_entries(self):
        return [(pid, f"#{pid:04d}  {self.pokedex.get_name(pid)}", pid)
                for pid in self.pokedex.get_all_ids()]

    def _get_move_entries(self):
        res: List[Tuple[Any, str, Any]] = [(None, "(vazio)", "")]
        for n in sorted(self.move_data.get_all_move_names(), key=str.lower):
            info = self.move_data.get_move_info(n)
            cat = info.get("category", "?") if info else "?"
            mtype = info.get("type", "?") if info else "?"
            res.append((n, f"{n}  [{mtype} / {cat}]", n))
        return res

    def _get_held_item_entries(self):
        res: List[Tuple[Any, str, Any]] = [(None, "(nenhum)", None)]
        try:
            items = self.item_catalog.get_items_by_category("held_item")
        except Exception:
            items = []
        for it in items:
            res.append((it["id"], it.get("name", it["id"]), it["id"]))
        return res

    def _get_pattern_entries(self):
        return [(p, label, p) for p, label in _ALL_ATTACK_PATTERNS]

    def _get_path_entries(self):
        res = []
        wm = getattr(self.gs, "wave_manager", None)
        if wm and hasattr(wm, "spawner"):
            for i in sorted(wm.spawner.waves.keys()):
                res.append((i, f"Path {i + 1}", i))
        if not res:
            res = [(0, "Path 1", 0)]
        return res

    def _get_day_night_entries(self):
        return [(v, label, v) for v, label in _DAY_NIGHT_OPTIONS]

    def _get_weather_entries(self):
        return [(v, label, v) for v, label in _WEATHER_OPTIONS]

    # =========================================================
    # ON_CLICK
    # =========================================================
    def _on_click(self, name: str):
        # Topo
        if name == "close_panel":
            self.toggle()
            return
        if name == "toggle_minimize":
            self.minimized = not self.minimized
            return
        if name == "toggle_pause_edit":
            self.pause_on_edit = not self.pause_on_edit
            self._apply_pause_state()
            return

        # Tabs
        for tid, _ in _TABS:
            if name == f"tab_{tid}":
                self.active_tab = tid
                self.scroll_y = 0
                self._close_dropdown()
                return

        # AMBIENTE
        if name == "weather_apply":
            self._apply_weather(); return
        if name == "dn_flash":
            self._activate_cave_flash(); return

        # WAVES
        if name == "waves_start_all":
            wm = getattr(self.gs, "wave_manager", None)
            if wm:
                wm.start_all_waves()
            return
        if name == "waves_kill_all":
            self._kill_all_enemies(); return
        if name == "waves_instant_win":
            self._kill_all_enemies()
            wm = getattr(self.gs, "wave_manager", None)
            if wm and hasattr(wm, "spawner"):
                sp = wm.spawner
                for pidx in list(sp.waves.keys()):
                    sp.current_wave_idx[pidx] = len(sp.waves[pidx])
                    sp.wave_active[pidx] = False
            return
        if name == "waves_toggle_spawner":
            sp = getattr(getattr(self.gs, "wave_manager", None), "spawner", None)
            if sp:
                sp.paused = not sp.paused
            return
        if name.startswith("waves_start_path_"):
            idx = int(name[len("waves_start_path_"):])
            sp = getattr(getattr(self.gs, "wave_manager", None), "spawner", None)
            if sp:
                sp._start_wave_for_path(idx)
            return
        if name.startswith("waves_next_path_"):
            idx = int(name[len("waves_next_path_"):])
            sp = getattr(getattr(self.gs, "wave_manager", None), "spawner", None)
            if sp:
                sp._advance_to_next_wave(idx)
            return
        if name.startswith("waves_skip_path_"):
            idx = int(name[len("waves_skip_path_"):])
            sp = getattr(getattr(self.gs, "wave_manager", None), "spawner", None)
            if sp:
                waves = sp.waves.get(idx, [])
                cur = sp.current_wave_idx.get(idx, 0)
                if cur < len(waves):
                    sp.spawned_count[idx] = waves[cur].wave_size
            return

        # SPAWN
        if name == "spawn_toggle_shiny":
            self.spawn_form["shiny"] = not self.spawn_form["shiny"]; return
        if name == "spawn_toggle_boss":
            self.spawn_form["boss"] = not self.spawn_form["boss"]; return
        if name == "spawn_do":
            self._do_spawn(); return

        # EDIT
        if name.startswith("edit_select_"):
            try:
                self.edit_selected = int(name[len("edit_select_"):])
            except ValueError:
                pass
            return
        if name.startswith("edit_toggle_shiny_"):
            idx = int(name[len("edit_toggle_shiny_"):])
            enemies = self._get_enemies()
            if 0 <= idx < len(enemies):
                enemies[idx].is_shiny = not enemies[idx].is_shiny
            return
        if name.startswith("edit_toggle_boss_"):
            idx = int(name[len("edit_toggle_boss_"):])
            enemies = self._get_enemies()
            if 0 <= idx < len(enemies):
                enemies[idx].is_boss = not enemies[idx].is_boss
            return
        if name.startswith("edit_kill_"):
            idx = int(name[len("edit_kill_"):])
            enemies = self._get_enemies()
            if 0 <= idx < len(enemies):
                e = enemies[idx]
                e.current_hp = 0
                e.set_defeated(True)
            return
        if name.startswith("edit_heal_"):
            idx = int(name[len("edit_heal_"):])
            enemies = self._get_enemies()
            if 0 <= idx < len(enemies):
                e = enemies[idx]
                e.current_hp = e.max_hp
                e.is_defeated = False
            return

        # DROPDOWN TRIGGERS
        if name.startswith("dd_open_"):
            rest = name[len("dd_open_"):]
            if rest.startswith("spawn_pokemon_"):
                self._open_dropdown(("spawn_pokemon", None), self._get_pokemon_entries())
            elif rest.startswith("spawn_move_"):
                sub = int(rest[len("spawn_move_"):])
                self._open_dropdown(("spawn_move", sub), self._get_move_entries())
            elif rest.startswith("spawn_held_"):
                self._open_dropdown(("spawn_held", None), self._get_held_item_entries())
            elif rest.startswith("spawn_pattern_"):
                self._open_dropdown(("spawn_pattern", None), self._get_pattern_entries())
            elif rest.startswith("spawn_path_"):
                self._open_dropdown(("spawn_path", None), self._get_path_entries())
            elif rest.startswith("edit_move_"):
                sub = int(rest[len("edit_move_"):])
                self._open_dropdown(("edit_move", sub), self._get_move_entries())
            elif rest.startswith("edit_held_"):
                self._open_dropdown(("edit_held", None), self._get_held_item_entries())
            elif rest.startswith("edit_pattern_"):
                self._open_dropdown(("edit_pattern", None), self._get_pattern_entries())
            elif rest.startswith("dn_select_"):
                self._open_dropdown(("dn_select", None), self._get_day_night_entries())
            elif rest.startswith("weather_select_"):
                self._open_dropdown(("weather_select", None), self._get_weather_entries())
            return

        # GOD
        if name.startswith("god_ff_"):
            try:
                self.fast_forward_mult = int(name[len("god_ff_"):])
            except ValueError:
                pass
            return
        if name == "god_reset_all":
            for k in self.god:
                self.god[k] = False
            self.fast_forward_mult = 1
            return
        if name == "god_kill_all":
            self._kill_all_enemies(); return
        if name.startswith("god_"):
            key = name[len("god_"):]
            if key in self.god:
                self.god[key] = not self.god[key]
                print(f"[DEBUG] God mode {key} = {self.god[key]}")
                if key == "enemies_1hp" and self.god[key]:
                    self._seen_enemy_ids.clear()
                    for e in self._get_enemies():
                        self._seen_enemy_ids.add(id(e))
            return

    # =========================================================
    # ACOES
    # =========================================================
    def _set_weather_type(self, type_val: str):
        if not hasattr(self.gs, "battle_system"):
            return
        wm = self.gs.battle_system.weather_manager

        if type_val == "none":
            wm.clear_weather()
            if getattr(wm, "base_weather", None):
                wm.base_weather.active = False
                wm.base_weather = None
            wm.current_weather = None
            return

        wtype = weather_from_string(type_val)
        if wtype == WeatherType.NONE:
            return

        wm.set_weather(wtype, duration=999999.0, source=None)
        print(f"[DEBUG] Weather -> {type_val}")

    def _set_day_night_type(self, type_val: str):
        if not hasattr(self.gs, "day_night_weather"):
            return
        dns = self.gs.day_night_weather

        new_type = day_night_from_string(type_val)
        duration = dns.day_night_state.duration if dns.day_night_state else 60

        if new_type in (DayNightType.CAVE, DayNightType.DEEP):
            duration = 999999.0

        dns.day_night_state = DayNightState(new_type, duration)
        dns.day_night_state.active = True
        print(f"[DEBUG] Day/Night -> {new_type.value}")

    def _apply_weather(self):
        if not hasattr(self.gs, "battle_system"):
            return
        wm = self.gs.battle_system.weather_manager
        if wm.current_weather and wm.current_weather.type != WeatherType.NONE:
            wm.set_weather(wm.current_weather.type, duration=999999.0, source=None)

    def _activate_cave_flash(self):
        if not hasattr(self.gs, "day_night_weather"):
            return
        dns = self.gs.day_night_weather
        if dns.day_night_state and hasattr(dns.day_night_state, "activate_flash"):
            dns.day_night_state.activate_flash()

    def _kill_all_enemies(self):
        for e in list(self._get_enemies()):
            e.current_hp = 0
            try:
                e.set_defeated(True)
            except Exception:
                pass

    def _get_enemies(self):
        wm = getattr(self.gs, "wave_manager", None)
        return wm.active_enemies if wm else []

    def _get_selected_enemy(self):
        enemies = self._get_enemies()
        if 0 <= self.edit_selected < len(enemies):
            return enemies[self.edit_selected]
        return None

    def _set_enemy_move(self, enemy, slot: int, move_name: str):
        if not move_name:
            if slot < len(enemy.moves):
                enemy.moves.pop(slot)
            return
        info = self.move_data.get_move_info(move_name)
        if not info:
            return
        new_move = Move(move_name, info)
        if slot < len(enemy.moves):
            enemy.moves[slot] = new_move
        else:
            enemy.moves.append(new_move)

    def _set_enemy_held(self, enemy, item_id):
        enemy.held_item = item_id
        if item_id:
            enemy.held_item_data = self.item_catalog.get_item(item_id)
        else:
            enemy.held_item_data = None

    def _set_enemy_pattern(self, enemy, pattern):
        enemy.attack_pattern = pattern
        try:
            enemy._setup_attack_pattern()
        except Exception:
            pass

    def _do_spawn(self):
        wm = getattr(self.gs, "wave_manager", None)
        if not wm:
            return
        path_idx = self.spawn_form["path_index"]
        path = wm.path_tracker.get_path_by_index(path_idx)
        if not path or not path.start_point:
            return

        from src.entities.pokemon import Pokemon
        form = self.spawn_form
        pokemon = Pokemon(
            path.start_point[0], path.start_point[1],
            form["pokemon_id"],
            level=form["level"],
            is_wild=True,
            shiny=form["shiny"],
            is_boss=form["boss"],
        )

        chosen = [m for m in form["moves"] if m]
        if chosen:
            pokemon.moves = []
            for n in chosen:
                info = self.move_data.get_move_info(n)
                if info:
                    pokemon.moves.append(Move(n, info))
            if not pokemon.moves:
                fb = self.move_data.get_move_info("tackle")
                if fb:
                    pokemon.moves.append(Move("tackle", fb))

        if form["held_item"]:
            pokemon.held_item = form["held_item"]
            pokemon.held_item_data = self.item_catalog.get_item(form["held_item"])

        pokemon.attack_pattern = form["pattern"]
        try:
            pokemon._setup_attack_pattern()
        except Exception:
            pass

        if hasattr(self.gs, "screen_manager"):
            pokemon.screen_manager = self.gs.screen_manager
        if hasattr(self.gs, "camera"):
            pokemon.camera = self.gs.camera

        if not wm.path_tracker.assign_path(pokemon, path_idx, start_at_begin=True):
            return

        pokemon._just_spawned = True
        pokemon._spawn_timer = 0.3
        pokemon._path_tracker = wm.path_tracker

        if hasattr(self.gs, "battle_system"):
            pokemon.set_battle_system(self.gs.battle_system)
            try:
                self.gs.battle_system.set_effect_manager_for_pokemon(pokemon)
            except Exception:
                pass

        wm.active_enemies.append(pokemon)

        try:
            player = getattr(self.gs, "player", None)
            if player:
                player.register_seen(pokemon.id)
        except Exception:
            pass

        print(f"[DEBUG] Spawn: {pokemon.name} Lv.{pokemon.level} "
              f"(boss={pokemon.is_boss}, shiny={pokemon.is_shiny}) path {path_idx}")

    # =========================================================
    # UPDATE
    # =========================================================
    def update(self, dt: float):
        # Safety net — re-sincroniza se algo externo mexeu
        self._apply_pause_state()
        # God mode continuo
        self._apply_god_effects()

    def _apply_god_effects(self):
        gs = self.gs
        if not gs:
            return

        if self.god["infinite_money"]:
            player = getattr(gs, "player", None)
            if player:
                player.money = 999999

        if self.god["no_cooldown"] or self.god["no_pp"]:
            placed = []
            if hasattr(gs, "placement_manager"):
                placed = gs.placement_manager.placed_pokemon
            for p in placed:
                if not p.is_alive():
                    continue
                if self.god["no_cooldown"]:
                    p.charge_cooldown = 0
                    p.attack_cooldown = 0
                    p.can_attack = True
                if self.god["no_pp"]:
                    for m in p.moves:
                        m.current_pp = m.max_pp

        if self.god["disable_spawn"]:
            wm = getattr(gs, "wave_manager", None)
            if wm and hasattr(wm, "spawner"):
                wm.spawner.paused = True

        if self.god["enemies_1hp"]:
            for e in self._get_enemies():
                eid = id(e)
                if eid not in self._seen_enemy_ids:
                    self._seen_enemy_ids.add(eid)
                    e.current_hp = 1

    # =========================================================
    # UI HELPERS
    # =========================================================
    def _register_click(self, name, rect):
        self._clicks.append((name, rect))

    def _find_click_at(self, pos) -> Optional[str]:
        for n, r in reversed(self._clicks):
            if r.collidepoint(pos):
                return n
        return None

    def _update_slider_from_mouse(self, name, pos):
        rect = None
        for n, r in self._clicks:
            if n == name:
                rect = r
                break
        meta = self._sliders.get(name)
        if not (rect and meta):
            return
        min_v, max_v, cb = meta
        ratio = (pos[0] - rect.x) / max(1, rect.width)
        ratio = max(0.0, min(1.0, ratio))
        value = int(round(min_v + ratio * (max_v - min_v)))
        if cb:
            cb(value)

    # ---------------------------------------------------------
    # Layout
    # ---------------------------------------------------------
    def _recalc_layout(self, screen):
        sm = self.gs.screen_manager
        vw = sm.viewport_width
        vh = sm.viewport_height

        min_w = int(vw * 0.4)
        min_h = int(vh * 0.4)

        if self._panel_w == 0 or self._panel_h == 0:
            self._panel_w = max(min_w, min(1200, vw - 80))
            self._panel_h = max(min_h, min(800, vh - 80))
            vx = sm.viewport_x
            vy = sm.viewport_y
            self._panel_x = vx + (vw - self._panel_w) // 2
            self._panel_y = vy + (vh - self._panel_h) // 2

        max_w = vw - 20
        max_h = vh - 20
        self._panel_w = max(min_w, min(max_w, self._panel_w))
        self._panel_h = max(min_h, min(max_h, self._panel_h))

        self._clamp_panel_position()

    def _clamp_panel_position(self):
        sm = self.gs.screen_manager
        vx = sm.viewport_x
        vy = sm.viewport_y
        vw = sm.viewport_width
        vh = sm.viewport_height

        min_x = vx - self._panel_w + 120
        max_x = vx + vw - 120
        min_y = vy
        max_y = vy + vh - HEADER_H

        self._panel_x = max(min_x, min(max_x, self._panel_x))
        self._panel_y = max(min_y, min(max_y, self._panel_y))

    def _get_resize_handle_rect(self) -> Optional[pygame.Rect]:
        if self.minimized or self.panel_rect is None:
            return None
        hs = self._resize_handle_size
        return pygame.Rect(
            self._panel_x + self._panel_w - hs,
            self._panel_y + self._panel_h - hs,
            hs, hs,
        )

    def _update_resize_from_mouse(self, pos):
        sm = self.gs.screen_manager
        vw = sm.viewport_width
        vh = sm.viewport_height

        min_w = int(vw * 0.4)
        min_h = int(vh * 0.4)
        max_w = vw - 20
        max_h = vh - 20

        dx = pos[0] - self._resize_start_mouse[0]
        dy = pos[1] - self._resize_start_mouse[1]

        new_w = self._resize_start_size[0] + dx
        new_h = self._resize_start_size[1] + dy
        new_w = max(min_w, min(max_w, new_w))
        new_h = max(min_h, min(max_h, new_h))

        self._panel_w = new_w
        self._panel_h = new_h
        self._clamp_panel_position()

    # ---------------------------------------------------------
    # Desenho de componentes
    # ---------------------------------------------------------
    def _draw_button(self, screen, rect, text, *,
                     danger=False, success=False, primary=False,
                     font_size=None, click_name=None, disabled=False):
        if click_name and not disabled:
            self._register_click(click_name, rect)
        hovered = rect.collidepoint(pygame.mouse.get_pos()) and not disabled

        if font_size is None:
            font_size = FONT_BUTTON

        if disabled:
            base, border, text_c = (40, 40, 50), (70, 70, 85), (130, 130, 140)
        elif danger:
            base = (140, 45, 45) if hovered else (100, 30, 30)
            border, text_c = (220, 70, 70), (255, 235, 235)
        elif success:
            base = (45, 110, 55) if hovered else (30, 80, 40)
            border, text_c = (90, 210, 110), (235, 255, 235)
        elif primary:
            base = (75, 90, 140) if hovered else (50, 60, 100)
            border, text_c = (130, 170, 240), (235, 240, 255)
        else:
            base = (65, 65, 85) if hovered else (45, 45, 60)
            border, text_c = (110, 110, 140), (240, 240, 250)

        pygame.draw.rect(screen, base, rect, border_radius=6)
        pygame.draw.rect(screen, border, rect, 2, border_radius=6)

        f = _get_font(font_size)
        t = f.render(text, True, text_c)
        max_w = rect.width - 16
        if t.get_width() > max_w:
            disp = text
            while f.size(disp)[0] > max_w and len(disp) > 4:
                disp = disp[:-2]
            disp = disp[:-2] + "..." if len(disp) > 3 else disp
            t = f.render(disp, True, text_c)
        screen.blit(t, t.get_rect(center=rect.center))

    def _draw_tab(self, screen, rect, label, active, click_name):
        self._register_click(click_name, rect)
        hovered = rect.collidepoint(pygame.mouse.get_pos())
        if active:
            base, border = (75, 60, 130), (200, 170, 255)
        elif hovered:
            base, border = (50, 45, 80), (140, 120, 200)
        else:
            base, border = (30, 30, 45), (70, 70, 100)
        pygame.draw.rect(screen, base, rect, border_radius=6)
        pygame.draw.rect(screen, border, rect, 2, border_radius=6)
        if active:
            pygame.draw.rect(screen, (255, 200, 100),
                             (rect.x + 6, rect.bottom - 3, rect.width - 12, 3))
        f = _get_font(15)
        t = f.render(label, True, (255, 255, 255) if active else (200, 200, 220))
        screen.blit(t, t.get_rect(center=rect.center))

    def _draw_toggle(self, screen, rect, label, value, click_name):
        self._register_click(click_name, rect)
        hovered = rect.collidepoint(pygame.mouse.get_pos())
        if value:
            bg = (60, 140, 70) if hovered else (40, 100, 55)
            border = (120, 220, 130)
            status = "LIGADO"
        else:
            bg = (80, 80, 95) if hovered else (55, 55, 70)
            border = (120, 120, 130)
            status = "DESLIG."
        pygame.draw.rect(screen, bg, rect, border_radius=6)
        pygame.draw.rect(screen, border, rect, 2, border_radius=6)

        sf = _get_font(13)
        st = sf.render(status, True, (255, 255, 255))
        st_x = rect.right - st.get_width() - 10

        f = _get_font(FONT_BASE)
        max_w = rect.width - 100
        disp = label
        while f.size(disp)[0] > max_w and len(disp) > 4:
            disp = disp[:-2]
        if disp != label:
            disp = disp[:-2] + "..." if len(disp) > 3 else disp
        t = f.render(disp, True, (240, 240, 250))
        screen.blit(t, (rect.x + 10, rect.centery - t.get_height() // 2))
        screen.blit(st, (st_x, rect.centery - st.get_height() // 2))

    def _draw_checkbox(self, screen, rect, label, value, click_name):
        self._register_click(click_name, rect)
        box_size = 20
        box = pygame.Rect(rect.x, rect.centery - box_size // 2, box_size, box_size)
        pygame.draw.rect(screen, (30, 30, 45), box, border_radius=4)
        bc = (200, 180, 255) if value else (90, 90, 120)
        pygame.draw.rect(screen, bc, box, 2, border_radius=4)
        if value:
            pygame.draw.line(screen, (120, 220, 130),
                             (box.x + 3, box.centery), (box.centerx, box.bottom - 4), 3)
            pygame.draw.line(screen, (120, 220, 130),
                             (box.centerx, box.bottom - 4), (box.right - 3, box.y + 3), 3)

        f = _get_font(FONT_BASE)
        t = f.render(label, True, (220, 220, 240))
        screen.blit(t, (box.right + 10, rect.centery - t.get_height() // 2))

    def _draw_slider(self, screen, rect, label, value, min_v, max_v,
                     click_name, on_change):
        self._register_click(click_name, rect)
        self._sliders[click_name] = (min_v, max_v, on_change)

        label_w = 0
        if label:
            f = _get_font(FONT_SMALL)
            t = f.render(label, True, (220, 220, 240))
            screen.blit(t, (rect.x, rect.centery - t.get_height() // 2))
            label_w = t.get_width() + 12

        val_w = 70
        bar_rect = pygame.Rect(rect.x + label_w, rect.centery - 7,
                               rect.width - label_w - val_w - 8, 14)
        pygame.draw.rect(screen, (28, 28, 42), bar_rect, border_radius=6)

        ratio = (value - min_v) / max(1, max_v - min_v)
        fill_w = int(bar_rect.width * ratio)
        if fill_w > 0:
            pygame.draw.rect(screen, (100, 180, 240),
                             (bar_rect.x, bar_rect.y, fill_w, bar_rect.height),
                             border_radius=6)

        bc = (200, 180, 255) if click_name == self._dragging_slider else (90, 90, 130)
        pygame.draw.rect(screen, bc, bar_rect, 2, border_radius=6)

        val_rect = pygame.Rect(bar_rect.right + 8, rect.centery - 13, val_w, 26)
        pygame.draw.rect(screen, (25, 25, 40), val_rect, border_radius=6)
        pygame.draw.rect(screen, (80, 80, 110), val_rect, 1, border_radius=6)
        vf = _get_font(15)
        vt = vf.render(str(value), True, (255, 220, 120))
        screen.blit(vt, vt.get_rect(center=val_rect.center))

    def _draw_dropdown_trigger(self, screen, rect, label, value_text, dropdown_key):
        kind, sub = dropdown_key
        click_name = f"dd_open_{kind}_{sub}"
        self._register_click(click_name, rect)

        hovered = rect.collidepoint(pygame.mouse.get_pos())
        is_open = (self.active_dropdown == dropdown_key)

        # ====== FIX DO BUG: salva o rect do trigger quando o dropdown esta aberto ======
        if is_open:
            self._dropdown_trigger_rect = rect
        # ==============================================================================

        bg = (75, 70, 110) if is_open else ((55, 50, 85) if hovered else (38, 38, 55))
        border = (200, 170, 255) if is_open else (120, 110, 170)
        pygame.draw.rect(screen, bg, rect, border_radius=6)
        pygame.draw.rect(screen, border, rect, 2, border_radius=6)

        tx = rect.x + 10
        if label:
            lf = _get_font(FONT_SMALL)
            lt = lf.render(label, True, (180, 180, 210))
            screen.blit(lt, (rect.x + 10, rect.centery - lt.get_height() // 2))
            tx = rect.x + 10 + lt.get_width() + 12

        vf = _get_font(FONT_BASE)
        max_val_w = rect.right - tx - 26
        disp = value_text
        while vf.size(disp)[0] > max_val_w and len(disp) > 4:
            disp = disp[:-2]
        if disp != value_text:
            disp = disp[:-2] + "..." if len(disp) > 3 else disp
        vt = vf.render(disp, True, (255, 240, 200))
        screen.blit(vt, (tx, rect.centery - vt.get_height() // 2))

        ax = rect.right - 16
        ay = rect.centery
        if is_open:
            pygame.draw.polygon(screen, (240, 240, 255),
                                [(ax - 7, ay + 2), (ax + 7, ay + 2), (ax, ay - 5)])
        else:
            pygame.draw.polygon(screen, (240, 240, 255),
                                [(ax - 7, ay - 2), (ax + 7, ay - 2), (ax, ay + 5)])

    def _draw_section_title(self, screen, x, y, w, text):
        f = _get_font(FONT_SECTION)
        label = f.render(text, True, (170, 180, 210))
        screen.blit(label, (x, y))
        line_y = y + label.get_height() // 2
        line_x = x + label.get_width() + 12
        line_w = w - label.get_width() - 12
        if line_w > 0:
            pygame.draw.line(screen, (60, 60, 90),
                             (line_x, line_y), (line_x + line_w, line_y), 1)

    def _draw_scrollbar(self, screen, content_rect):
        if self._scroll_max <= 0:
            return
        bar_x = content_rect.right - 8
        bar_y = content_rect.y
        bar_h = content_rect.height

        pygame.draw.rect(screen, (40, 40, 60),
                         (bar_x, bar_y, 6, bar_h), border_radius=3)

        ratio = content_rect.height / max(1, self._scroll_content_h)
        thumb_h = max(30, int(bar_h * ratio))
        max_s = max(1, self._scroll_max)
        thumb_y = bar_y + int((bar_h - thumb_h) * self.scroll_y / max_s)

        pygame.draw.rect(screen, (160, 130, 220),
                         (bar_x, thumb_y, 6, thumb_h), border_radius=3)

        self._scrollbar_rect = pygame.Rect(bar_x - 5, bar_y, 16, bar_h)
        self._scrollbar_thumb_rect = pygame.Rect(bar_x, thumb_y, 6, thumb_h)

    def _update_scroll_from_mouse(self, mouse_y):
        cr = self._get_content_rect()
        if not cr or self._scroll_max <= 0:
            return
        thumb_h = max(30, int(cr.height * cr.height / max(1, self._scroll_content_h)))
        desired = mouse_y - cr.y - self._scroll_thumb_offset
        desired = max(0, min(cr.height - thumb_h, desired))
        track_h = max(1, cr.height - thumb_h)
        ratio = desired / track_h
        self.scroll_y = int(ratio * self._scroll_max)

    def _get_content_rect(self) -> Optional[pygame.Rect]:
        if self.panel_rect is None:
            return None
        return pygame.Rect(
            self.panel_rect.x + PANEL_PAD,
            self.panel_rect.y + HEADER_H + TAB_H + 12,
            self.panel_rect.width - PANEL_PAD * 2,
            self.panel_rect.height - HEADER_H - TAB_H - 24,
        )

    # =========================================================
    # RENDER
    # =========================================================
    def render(self, screen):
        if self.god["show_hitboxes"]:
            self._render_hitboxes(screen)

        # Limpa registros por frame
        self._clicks = []
        self._sliders = {}
        self._scrollbar_rect = None
        self._scrollbar_thumb_rect = None
        self._dropdown_trigger_rect = None

        if not self.visible:
            return

        self._recalc_layout(screen)
        self._draw_panel(screen)

        content_rect = self._get_content_rect()

        if self.minimized:
            self._scroll_content_h = 0
            self._scroll_max = 0
            self.scroll_y = 0
        elif content_rect:
            prev_clip = screen.get_clip()
            screen.set_clip(content_rect)
            try:
                if self.active_tab == "ambiente":
                    h = self._render_ambiente(screen, content_rect)
                elif self.active_tab == "waves":
                    h = self._render_waves(screen, content_rect)
                elif self.active_tab == "spawn":
                    h = self._render_spawn(screen, content_rect)
                elif self.active_tab == "editar":
                    h = self._render_editar(screen, content_rect)
                elif self.active_tab == "god":
                    h = self._render_god(screen, content_rect)
                else:
                    h = 0
                self._scroll_content_h = h
            except Exception as e:
                import traceback
                print(f"[DEBUG_MANAGER] Erro render aba {self.active_tab}: {e}")
                traceback.print_exc()
                self._scroll_content_h = 0
            screen.set_clip(prev_clip)

            self._scroll_max = max(0, self._scroll_content_h - content_rect.height)
            if self.scroll_y > self._scroll_max:
                self.scroll_y = self._scroll_max

            self._draw_scrollbar(screen, content_rect)

        # Dropdown por ultimo (prioridade maxima)
        if self.active_dropdown is not None and not self.minimized:
            self._render_dropdown(screen)

    def _draw_panel(self, screen):
        sm = self.gs.screen_manager

        pw = self._panel_w
        ph = HEADER_H + (TAB_H + 12) if self.minimized else self._panel_h
        px = self._panel_x
        py = self._panel_y

        if self._debug_pause_active:
            vx = sm.viewport_x
            vy = sm.viewport_y
            vw = sm.viewport_width
            vh = sm.viewport_height
            backdrop = pygame.Surface((vw, vh), pygame.SRCALPHA)
            backdrop.fill((0, 0, 0, 130))
            screen.blit(backdrop, (vx, vy))

        self.panel_rect = pygame.Rect(px, py, pw, ph)

        shadow = pygame.Surface((pw + 16, ph + 16), pygame.SRCALPHA)
        pygame.draw.rect(shadow, (0, 0, 0, 170), shadow.get_rect(), border_radius=16)
        screen.blit(shadow, (px - 8, py - 8))

        pygame.draw.rect(screen, (18, 22, 34), self.panel_rect, border_radius=12)
        pygame.draw.rect(screen, (140, 110, 220), self.panel_rect, 2, border_radius=12)

        header = pygame.Rect(px, py, pw, HEADER_H)
        pygame.draw.rect(screen, (40, 35, 65), header,
                         border_top_left_radius=12, border_top_right_radius=12)
        pygame.draw.line(screen, (140, 110, 220),
                         (px, py + HEADER_H), (px + pw, py + HEADER_H), 2)

        title = _get_font(FONT_TITLE).render(
            "DEBUG  -  ARRASTE AQUI", True, (255, 220, 120))
        screen.blit(title, (px + 18, py + 10))

        min_rect = pygame.Rect(px + pw - 36 - 100, py + 8, 92, HEADER_H - 16)
        self._draw_button(screen, min_rect,
                          "Expandir" if self.minimized else "Minimizar",
                          font_size=13, click_name="toggle_minimize")

        close_rect = pygame.Rect(px + pw - 36, py + 8, 28, HEADER_H - 16)
        self._draw_button(screen, close_rect, "X", danger=True,
                          font_size=16, click_name="close_panel")

        pause_rect = pygame.Rect(close_rect.left - 280 - 12, py + 10,
                                 280, HEADER_H - 20)
        self._draw_checkbox(screen, pause_rect,
                            "Pausar jogo enquanto edita",
                            self.pause_on_edit, "toggle_pause_edit")

        # Resize handle
        if not self.minimized:
            handle_rect = self._get_resize_handle_rect()
            if handle_rect:
                hovered = handle_rect.collidepoint(pygame.mouse.get_pos())
                col = (200, 180, 255) if (hovered or self._resizing) else (130, 110, 180)
                for offset in (2, 7, 12):
                    pygame.draw.line(
                        screen, col,
                        (handle_rect.x + offset, handle_rect.bottom - 2),
                        (handle_rect.right - 2, handle_rect.y + offset),
                        2,
                    )

        if self.minimized:
            return

        tab_y = py + HEADER_H + 6
        tab_w = (pw - 2 * PANEL_PAD) // len(_TABS)
        for i, (tid, label) in enumerate(_TABS):
            tx = px + PANEL_PAD + i * tab_w
            rect = pygame.Rect(tx, tab_y, tab_w - 4, TAB_H)
            self._draw_tab(screen, rect, label,
                           self.active_tab == tid, f"tab_{tid}")

    # ---------------------------------------------------------
    # ABA AMBIENTE
    # ---------------------------------------------------------
    def _render_ambiente(self, screen, cr) -> int:
        x = cr.x
        y = cr.y - self.scroll_y
        w = cr.width
        y_start = y

        dn = None
        if hasattr(self.gs, "day_night_weather"):
            dn = self.gs.day_night_weather.day_night_state

        # -------- PERIODO DO DIA --------
        self._draw_section_title(screen, x, y, w, "PERIODO DO DIA / AMBIENTE")
        y += 28

        # Dropdown do tipo
        cur_dn = dn.type.value if dn else "day"
        dn_disp = next((l for v, l in _DAY_NIGHT_OPTIONS if v == cur_dn),
                       "Desconhecido")
        dn_rect = pygame.Rect(x, y, (w - 20) // 2, INPUT_H)
        self._draw_dropdown_trigger(screen, dn_rect, "Tipo",
                                    dn_disp, ("dn_select", None))
        y += INPUT_H + 14

        # Slider de duracao
        cur_dur = int(dn.duration) if dn else 60
        if cur_dur > 300:
            cur_dur = 300
        sr = pygame.Rect(x, y, w // 2, SLIDER_H)
        self._draw_slider(screen, sr, "Duracao (s)",
                          cur_dur, 5, 300, "dn_duration",
                          on_change=lambda v: self._set_day_night_duration(v))
        y += SLIDER_H + 18

        flash_r = pygame.Rect(x, y, 240, BTN_H)
        self._draw_button(screen, flash_r, "Ativar Flash (caverna)",
                          font_size=14, click_name="dn_flash")
        y += BTN_H + 26

        # -------- CLIMA --------
        self._draw_section_title(screen, x, y, w, "CLIMA")
        y += 28

        weather = None
        if hasattr(self.gs, "battle_system") and self.gs.battle_system.weather_manager:
            weather = self.gs.battle_system.weather_manager.current_weather
        cur_w = weather.type.value if weather else "none"
        w_disp = next((l for v, l in _WEATHER_OPTIONS if v == cur_w), "Desconhecido")
        w_rect = pygame.Rect(x, y, (w - 20) // 2, INPUT_H)
        self._draw_dropdown_trigger(screen, w_rect, "Tipo",
                                    w_disp, ("weather_select", None))
        y += INPUT_H + 14

        sr = pygame.Rect(x, y, w // 2, SLIDER_H)
        self._draw_slider(screen, sr, "Duracao (s)",
                          self._weather_duration, 5, 300,
                          "weather_duration",
                          on_change=lambda v: setattr(self, "_weather_duration", v))
        y += SLIDER_H + 18

        apply_r = pygame.Rect(x, y, 240, BTN_H)
        self._draw_button(screen, apply_r, "Reaplicar Clima Atual",
                          primary=True, font_size=14, click_name="weather_apply")
        y += BTN_H + 26

        # Dicas
        self._draw_section_title(screen, x, y, w, "DICAS")
        y += 26
        hint_f = _get_font(FONT_SMALL)
        for h in [
            "Noite ativa variants 'night' nas waves com use_variants.",
            "Caverna e Fundo do Mar sao permanentes.",
            "Chuva buffa Agua, enfraquece Fogo.",
            "Tempestade de Areia: 1/16 do HP max a cada 2s.",
        ]:
            ht = hint_f.render(h, True, (150, 160, 190))
            screen.blit(ht, (x, y))
            y += 20

        return y - y_start

    def _set_day_night_duration(self, v):
        if not hasattr(self.gs, "day_night_weather"):
            return
        dns = self.gs.day_night_weather
        if dns.day_night_state:
            dns.day_night_state.duration = float(v)
            dns.day_night_state.max_duration = float(v)

    # ---------------------------------------------------------
    # ABA WAVES
    # ---------------------------------------------------------
    def _render_waves(self, screen, cr) -> int:
        x = cr.x
        y = cr.y - self.scroll_y
        w = cr.width
        y_start = y

        wm = getattr(self.gs, "wave_manager", None)
        sp = getattr(wm, "spawner", None) if wm else None

        if not sp:
            f = _get_font(FONT_BASE)
            t = f.render("Wave manager indisponivel", True, (255, 150, 150))
            screen.blit(t, (x, y))
            return y - y_start + 30

        self._draw_section_title(screen, x, y, w, "CONTROLES GLOBAIS")
        y += 28

        bw = 200
        bh = BTN_H
        gap = 12

        r1 = pygame.Rect(x, y, bw, bh)
        self._draw_button(screen, r1, "Iniciar Todas Waves", success=True,
                          font_size=14, click_name="waves_start_all")
        r2 = pygame.Rect(x + bw + gap, y, bw, bh)
        self._draw_button(screen, r2, "Matar Todos", danger=True,
                          font_size=14, click_name="waves_kill_all")
        r3 = pygame.Rect(x + 2 * (bw + gap), y, bw, bh)
        self._draw_button(screen, r3, "Instant Win", primary=True,
                          font_size=14, click_name="waves_instant_win")
        y += bh + 14

        paused = getattr(sp, "paused", False)
        r = pygame.Rect(x, y, bw, bh)
        self._draw_button(screen, r,
                          "Retomar Spawner" if paused else "Pausar Spawner",
                          font_size=14, click_name="waves_toggle_spawner")
        y += bh + 26

        self._draw_section_title(screen, x, y, w, "STATUS POR PATH")
        y += 28

        paths = sorted(sp.waves.keys())
        if not paths:
            f = _get_font(FONT_BASE)
            t = f.render("Nenhum path configurado", True, (180, 180, 200))
            screen.blit(t, (x, y))
            return y - y_start + 30

        for pidx in paths:
            waves = sp.waves.get(pidx, [])
            widx = sp.current_wave_idx.get(pidx, 0)
            active = sp.wave_active.get(pidx, False)
            spawned = sp.spawned_count.get(pidx, 0)

            if widx < len(waves):
                wave = waves[widx]
                wsize = wave.wave_size
                wlabel = f"Wave {widx + 1}/{len(waves)}"
            else:
                wsize = 0
                wlabel = f"Wave {widx}/{len(waves)} (fim)"

            alive = 0
            if wm:
                for e in wm.active_enemies:
                    if getattr(e, "path_index_origin", 0) == pidx:
                        alive += 1

            card_h = 78
            card = pygame.Rect(x, y, w, card_h)
            pygame.draw.rect(screen, (26, 30, 44), card, border_radius=8)
            pygame.draw.rect(screen, (80, 90, 120), card, 1, border_radius=8)

            tf = _get_font(17)
            t = tf.render(f"Path {pidx + 1}", True, (255, 220, 120))
            screen.blit(t, (card.x + 14, card.y + 10))

            sf = _get_font(14)
            scol = (100, 220, 100) if active else (180, 180, 180)
            st = sf.render(
                f"{wlabel}   Spawnados: {spawned}/{wsize}   Vivos: {alive}",
                True, scol)
            screen.blit(st, (card.x + 14, card.y + 36))

            bw2 = 110
            bh2 = 28
            by = card.y + 22
            r1 = pygame.Rect(card.right - 3 * (bw2 + 8) - 14, by, bw2, bh2)
            r2 = pygame.Rect(r1.right + 8, by, bw2, bh2)
            r3 = pygame.Rect(r2.right + 8, by, bw2, bh2)
            self._draw_button(screen, r1, "Iniciar", success=True, font_size=12,
                              click_name=f"waves_start_path_{pidx}")
            self._draw_button(screen, r2, "Proxima", font_size=12,
                              click_name=f"waves_next_path_{pidx}")
            self._draw_button(screen, r3, "Pular", font_size=12,
                              click_name=f"waves_skip_path_{pidx}")

            y += card_h + 10

        return y - y_start

    # ---------------------------------------------------------
    # ABA SPAWN
    # ---------------------------------------------------------
    def _render_spawn(self, screen, cr) -> int:
        x = cr.x
        y = cr.y - self.scroll_y
        w = cr.width
        y_start = y
        form = self.spawn_form

        # POKEMON
        self._draw_section_title(screen, x, y, w, "POKEMON")
        y += 28
        name = self.pokedex.get_name(form["pokemon_id"])
        r = pygame.Rect(x, y, w - 60, INPUT_H)
        self._draw_dropdown_trigger(screen, r, "ID",
                                    f"#{form['pokemon_id']:04d}   {name}",
                                    ("spawn_pokemon", None))
        y += INPUT_H + 14

        # NIVEL
        self._draw_section_title(screen, x, y, w, "NIVEL")
        y += 28
        r = pygame.Rect(x, y, w - 60, SLIDER_H)
        self._draw_slider(screen, r, "", form["level"], 1, 100, "spawn_level",
                          on_change=lambda v: form.__setitem__("level", v))
        y += SLIDER_H + 20

        # Flags
        col_w = (w - 12) // 2
        r1 = pygame.Rect(x, y, col_w, BTN_H)
        r2 = pygame.Rect(r1.right + 12, y, col_w, BTN_H)
        self._draw_toggle(screen, r1, "Shiny", form["shiny"], "spawn_toggle_shiny")
        self._draw_toggle(screen, r2, "Boss", form["boss"], "spawn_toggle_boss")
        y += BTN_H + 22

        # MOVES
        self._draw_section_title(screen, x, y, w,
                                 "MOVES (vazio = usa learnset padrao)")
        y += 28
        move_w = (w - 3 * 8) // 4
        for i in range(4):
            mv = form["moves"][i]
            mr = pygame.Rect(x + i * (move_w + 8), y, move_w, INPUT_H)
            disp = mv if mv else "(vazio)"
            self._draw_dropdown_trigger(screen, mr, "", disp, ("spawn_move", i))
        y += INPUT_H + 22

        # ITEM SEGURADO
        self._draw_section_title(screen, x, y, w, "ITEM SEGURADO")
        y += 28
        held_id = form["held_item"]
        held_disp = "(nenhum)"
        if held_id:
            it = self.item_catalog.get_item(held_id)
            held_disp = it.get("name", held_id)
        r = pygame.Rect(x, y, (w - 20) // 2, INPUT_H)
        self._draw_dropdown_trigger(screen, r, "", held_disp,
                                    ("spawn_held", None))
        y += INPUT_H + 22

        # PATTERN
        self._draw_section_title(screen, x, y, w, "PADRAO DE ATAQUE")
        y += 28
        pat = form["pattern"]
        pat_disp = next((l for p_, l in _ALL_ATTACK_PATTERNS if p_ == pat), "?")
        r = pygame.Rect(x, y, (w - 20) // 2, INPUT_H)
        self._draw_dropdown_trigger(screen, r, "", pat_disp,
                                    ("spawn_pattern", None))
        y += INPUT_H + 22

        # PATH
        self._draw_section_title(screen, x, y, w, "PATH")
        y += 28
        r = pygame.Rect(x, y, (w - 20) // 2, INPUT_H)
        self._draw_dropdown_trigger(screen, r, "",
                                    f"Path {form['path_index'] + 1}",
                                    ("spawn_path", None))
        y += INPUT_H + 30

        # BOTAO
        spawn_r = pygame.Rect(x, y, w, BTN_H_LG)
        self._draw_button(screen, spawn_r, "SPAWNAR AGORA",
                          success=True, font_size=18, click_name="spawn_do")
        y += BTN_H_LG + 20

        hint_f = _get_font(FONT_SMALL)
        for h in [
            "Moves vazios: usa apenas o learnset padrao do nivel.",
            "O Pokemon entra no wave_manager normalmente (dropa, da XP, etc).",
        ]:
            ht = hint_f.render(h, True, (150, 160, 190))
            screen.blit(ht, (x, y))
            y += 20

        return y - y_start

    # ---------------------------------------------------------
    # ABA EDITAR
    # ---------------------------------------------------------
    def _render_editar(self, screen, cr) -> int:
        x = cr.x
        y = cr.y
        w = cr.width
        h = cr.height

        enemies = self._get_enemies()
        if not enemies:
            f = _get_font(FONT_BASE)
            t = f.render("Nenhum inimigo ativo para editar", True, (180, 180, 200))
            screen.blit(t, (x, y))
            return 30

        self.edit_selected = max(0, min(self.edit_selected, len(enemies) - 1))

        list_w = int(w * 0.36)
        list_rect = pygame.Rect(x, y, list_w, h)
        pygame.draw.rect(screen, (20, 22, 34), list_rect, border_radius=8)
        pygame.draw.rect(screen, (60, 60, 90), list_rect, 1, border_radius=8)

        lf = _get_font(14)
        lt = lf.render(f"INIMIGOS ({len(enemies)})", True, (180, 190, 220))
        screen.blit(lt, (list_rect.x + 10, list_rect.y + 8))

        row_h = 46
        list_y = list_rect.y + 32
        max_visible = max(1, (list_rect.height - 40) // row_h)

        if self.edit_selected < self.edit_scroll:
            self.edit_scroll = self.edit_selected
        elif self.edit_selected >= self.edit_scroll + max_visible:
            self.edit_scroll = self.edit_selected - max_visible + 1

        for i in range(max_visible):
            idx = self.edit_scroll + i
            if idx >= len(enemies):
                break
            e = enemies[idx]
            ry = list_y + i * row_h
            rr = pygame.Rect(list_rect.x + 6, ry, list_rect.width - 12, row_h - 4)

            selected = (idx == self.edit_selected)
            hovered = rr.collidepoint(pygame.mouse.get_pos())

            if selected:
                bg, border = (60, 50, 95), (200, 170, 255)
            elif hovered:
                bg, border = (40, 40, 60), (110, 100, 150)
            else:
                bg, border = (30, 32, 48), (60, 60, 85)

            pygame.draw.rect(screen, bg, rr, border_radius=6)
            pygame.draw.rect(screen, border, rr, 1, border_radius=6)
            self._register_click(f"edit_select_{idx}", rr)

            badge = ""
            if e.is_boss: badge += "B"
            if e.is_shiny: badge += "S"
            txt = e.name + (f"  [{badge}]" if badge else "")
            ef = _get_font(15)
            t = ef.render(txt, True, (240, 240, 250))
            screen.blit(t, (rr.x + 10, rr.y + 6))

            lvf = _get_font(12)
            hp_pct = int((e.current_hp / max(1, e.max_hp)) * 100)
            lvt = lvf.render(
                f"Lv.{e.level}  HP: {e.current_hp}/{e.max_hp} ({hp_pct}%)",
                True, (180, 190, 210))
            screen.blit(lvt, (rr.x + 10, rr.y + 26))

        # Editor
        edit_x = list_rect.right + 14
        edit_w = x + w - edit_x
        edit_rect = pygame.Rect(edit_x, y, edit_w, h)
        pygame.draw.rect(screen, (22, 24, 38), edit_rect, border_radius=8)
        pygame.draw.rect(screen, (70, 70, 100), edit_rect, 1, border_radius=8)

        enemy = enemies[self.edit_selected]

        ef = _get_font(20)
        et = ef.render(f"{enemy.name}   Lv.{enemy.level}", True, (255, 220, 120))
        screen.blit(et, (edit_rect.x + 14, edit_rect.y + 12))

        ey = edit_rect.y + 48
        ex = edit_rect.x + 14
        ew = edit_rect.width - 28

        hpf = _get_font(14)
        screen.blit(hpf.render("HP atual", True, (220, 220, 240)), (ex, ey))
        ey += 18

        def set_hp(v):
            enemy.current_hp = max(0, min(enemy.max_hp, v))
            if enemy.current_hp <= 0 and not enemy.is_defeated:
                try:
                    enemy.set_defeated(True)
                except Exception:
                    pass

        self._draw_slider(screen, pygame.Rect(ex, ey, ew, SLIDER_H),
                          "", enemy.current_hp, 0, max(1, enemy.max_hp),
                          f"edit_hp_{self.edit_selected}",
                          on_change=set_hp)
        ey += SLIDER_H + 14

        screen.blit(hpf.render("Nivel", True, (220, 220, 240)), (ex, ey))
        ey += 18

        def set_level(v):
            enemy.level = v
            try:
                enemy.stats.calculate_stats()
            except Exception:
                pass
            if enemy.current_hp > enemy.max_hp:
                enemy.current_hp = enemy.max_hp

        self._draw_slider(screen, pygame.Rect(ex, ey, ew, SLIDER_H),
                          "", enemy.level, 1, 100,
                          f"edit_level_{self.edit_selected}",
                          on_change=set_level)
        ey += SLIDER_H + 16

        col_w = (ew - 10) // 2
        r1 = pygame.Rect(ex, ey, col_w, BTN_H)
        r2 = pygame.Rect(r1.right + 10, ey, col_w, BTN_H)
        self._draw_toggle(screen, r1, "Shiny", enemy.is_shiny,
                          f"edit_toggle_shiny_{self.edit_selected}")
        self._draw_toggle(screen, r2, "Boss", enemy.is_boss,
                          f"edit_toggle_boss_{self.edit_selected}")
        ey += BTN_H + 18

        mf = _get_font(14)
        screen.blit(mf.render("MOVES", True, (180, 190, 220)), (ex, ey))
        ey += 20
        for i in range(4):
            mr = pygame.Rect(ex, ey, ew, INPUT_H)
            if i < len(enemy.moves):
                mv = enemy.moves[i]
                disp = f"{mv.name}   ({mv.current_pp}/{mv.max_pp})"
            else:
                disp = "(vazio)"
            self._draw_dropdown_trigger(screen, mr, "", disp, ("edit_move", i))
            ey += INPUT_H + 6

        ey += 8

        screen.blit(mf.render("ITEM SEGURADO", True, (180, 190, 220)), (ex, ey))
        ey += 20
        held_id = enemy.held_item
        held_disp = "(nenhum)"
        if held_id:
            it = self.item_catalog.get_item(held_id)
            held_disp = it.get("name", held_id)
        self._draw_dropdown_trigger(screen, pygame.Rect(ex, ey, ew, INPUT_H),
                                    "", held_disp, ("edit_held", None))
        ey += INPUT_H + 16

        screen.blit(mf.render("PADRAO DE ATAQUE", True, (180, 190, 220)), (ex, ey))
        ey += 20
        pat = getattr(enemy, "attack_pattern", AttackPattern.RANDOM)
        pat_disp = next((l for p_, l in _ALL_ATTACK_PATTERNS if p_ == pat), "?")
        self._draw_dropdown_trigger(screen, pygame.Rect(ex, ey, ew, INPUT_H),
                                    "", pat_disp, ("edit_pattern", None))
        ey += INPUT_H + 20

        by = edit_rect.bottom - BTN_H - 12
        kb = pygame.Rect(ex, by, 160, BTN_H)
        self._draw_button(screen, kb, "Matar", danger=True, font_size=14,
                          click_name=f"edit_kill_{self.edit_selected}")
        hb = pygame.Rect(kb.right + 10, by, 160, BTN_H)
        self._draw_button(screen, hb, "Curar 100%", success=True, font_size=14,
                          click_name=f"edit_heal_{self.edit_selected}")

        return h

    # ---------------------------------------------------------
    # ABA GOD
    # ---------------------------------------------------------
    def _render_god(self, screen, cr) -> int:
        x = cr.x
        y = cr.y - self.scroll_y
        w = cr.width
        y_start = y

        self._draw_section_title(screen, x, y, w, "GOD MODE - TOGGLES")
        y += 28

        toggles = [
            ("team_invincible", "Time Invencivel (aliados)"),
            ("one_hit_kill", "One-Hit Kill (aliados)"),
            ("enemies_1hp", "Inimigos nascem com 1 HP"),
            ("infinite_money", "Dinheiro Infinito"),
            ("no_cooldown", "Sem Cooldown (aliados)"),
            ("no_pp", "PP Infinito (aliados)"),
            ("disable_spawn", "Parar Spawner"),
            ("damage_x10", "Dano x10 (aliados)"),
            ("show_hitboxes", "Mostrar Hitboxes"),
        ]

        col_w = (w - 12) // 2
        row_h = BTN_H + 6
        for i, (key, label) in enumerate(toggles):
            col = i % 2
            row = i // 2
            rx = x + col * (col_w + 12)
            ry = y + row * row_h
            r = pygame.Rect(rx, ry, col_w, BTN_H)
            self._draw_toggle(screen, r, label, self.god[key], f"god_{key}")

        y += ((len(toggles) + 1) // 2) * row_h + 14

        self._draw_section_title(screen, x, y, w, "VELOCIDADE DO JOGO")
        y += 28

        f = _get_font(FONT_BASE)
        t = f.render(f"Multiplicador atual: x{self.fast_forward_mult}",
                     True, (220, 220, 240))
        screen.blit(t, (x, y + 6))

        bx = x + 320
        for mult in self._ff_options:
            br = pygame.Rect(bx, y, 66, BTN_H)
            is_active = self.fast_forward_mult == mult
            self._draw_button(screen, br, f"x{mult}",
                              primary=is_active, font_size=15,
                              click_name=f"god_ff_{mult}")
            bx += 72
        y += BTN_H + 22

        self._draw_section_title(screen, x, y, w, "ACOES PERIGOSAS")
        y += 28

        r = pygame.Rect(x, y, 240, BTN_H)
        self._draw_button(screen, r, "Resetar God Mode",
                          danger=True, font_size=14, click_name="god_reset_all")
        r2 = pygame.Rect(r.right + 14, y, 240, BTN_H)
        self._draw_button(screen, r2, "Matar Todos Inimigos",
                          danger=True, font_size=14, click_name="god_kill_all")
        y += BTN_H + 26

        hint_f = _get_font(FONT_SMALL)
        for h in [
            "God Mode fica ATIVO mesmo com o painel fechado.",
            "Use 'Resetar God Mode' antes de sair da fase.",
            "Fast-Forward multiplica o dt do update (tudo acelera).",
            "Hitboxes desenham o raio de ataque de todos os Pokemon.",
        ]:
            ht = hint_f.render(h, True, (255, 200, 120))
            screen.blit(ht, (x, y))
            y += 20

        return y - y_start

    # ---------------------------------------------------------
    # HITBOXES
    # ---------------------------------------------------------
    def _render_hitboxes(self, screen):
        gs = self.gs
        if not hasattr(gs, "screen_manager") or not hasattr(gs, "camera"):
            return
        cam = gs.camera
        sm = gs.screen_manager
        zoom = cam.zoom * sm.render_scale

        all_pokemon = []
        if hasattr(gs, "placement_manager"):
            all_pokemon.extend(gs.placement_manager.placed_pokemon)
        if hasattr(gs, "wave_manager"):
            all_pokemon.extend(gs.wave_manager.active_enemies)

        for p in all_pokemon:
            try:
                sx, sy = sm.world_to_screen(p.x, p.y, cam)
            except Exception:
                continue
            color = (100, 255, 100, 90) if not p.is_wild else (255, 100, 100, 90)
            radius = max(4, int(p.attack_range * zoom))
            surf = pygame.Surface((radius * 2 + 4, radius * 2 + 4), pygame.SRCALPHA)
            pygame.draw.circle(surf, color, (radius + 2, radius + 2), radius, 2)
            screen.blit(surf, (sx - radius - 2, sy - radius - 2))
            pygame.draw.circle(screen, color[:3], (int(sx), int(sy)), 3, 1)

    # ---------------------------------------------------------
    # DROPDOWN RENDER
    # ---------------------------------------------------------
    def _render_dropdown(self, screen):
        trigger = self._dropdown_trigger_rect
        if trigger is None:
            # Nao achou o trigger deste frame -> fecha pra evitar estado preso
            self._close_dropdown()
            return

        panel = self.panel_rect
        if panel is None:
            return

        w = max(trigger.width + 80, 420)
        h = 400
        x = trigger.x
        y = trigger.bottom + 4
        if x + w > panel.right - 8:
            x = panel.right - w - 8
        if x < panel.x + 8:
            x = panel.x + 8
        if y + h > panel.bottom - 8:
            y = trigger.y - h - 4
            if y < panel.y + HEADER_H + 8:
                y = panel.y + HEADER_H + 8

        actual = pygame.Rect(x, y, w, h)
        self._dropdown_rect = actual

        shadow = pygame.Surface((w + 12, h + 12), pygame.SRCALPHA)
        pygame.draw.rect(shadow, (0, 0, 0, 180), shadow.get_rect(), border_radius=10)
        screen.blit(shadow, (x - 6, y - 6))

        pygame.draw.rect(screen, (28, 26, 44), actual, border_radius=10)
        pygame.draw.rect(screen, (160, 130, 220), actual, 2, border_radius=10)

        self._register_click("dd_panel", actual)

        # Search
        sh = 38
        search_rect = pygame.Rect(x + 8, y + 8, w - 16, sh)
        self._register_click("dd_search", search_rect)
        pygame.draw.rect(screen, (15, 15, 25), search_rect, border_radius=6)
        bc = (255, 200, 60) if self._search_focused else (80, 80, 110)
        pygame.draw.rect(screen, bc, search_rect, 2, border_radius=6)
        sf = _get_font(FONT_BASE)
        txt = self.dropdown_search if self.dropdown_search else "Buscar..."
        tc = (220, 220, 230) if self.dropdown_search else (110, 110, 130)
        if self._search_focused:
            txt += "_"
        st = sf.render(txt, True, tc)
        screen.blit(st, (search_rect.x + 12,
                         search_rect.centery - st.get_height() // 2))

        # Lista
        list_y = search_rect.bottom + 6
        list_h = actual.bottom - list_y - 8
        row_h = 30
        max_visible = max(1, list_h // row_h)

        total = len(self._dropdown_entries)
        max_scroll = max(0, total - max_visible)
        if self.dropdown_scroll > max_scroll:
            self.dropdown_scroll = max_scroll
        start = self.dropdown_scroll
        end = min(total, start + max_visible)

        if total == 0:
            ef = _get_font(FONT_BASE)
            et = ef.render("Nada encontrado", True, (160, 160, 180))
            screen.blit(et, (x + (w - et.get_width()) // 2,
                             list_y + list_h // 2 - et.get_height() // 2))
        else:
            for i in range(start, end):
                _, display, _ = self._dropdown_entries[i]
                ry = list_y + (i - start) * row_h
                rr = pygame.Rect(x + 8, ry, w - 16, row_h - 2)
                hovered = rr.collidepoint(pygame.mouse.get_pos())
                bg = (60, 50, 95) if hovered else (34, 32, 50)
                pygame.draw.rect(screen, bg, rr, border_radius=4)
                self._register_click(f"dd_pick_{i}", rr)
                f = _get_font(FONT_BASE)
                max_w = rr.width - 20
                disp = display
                while f.size(disp)[0] > max_w and len(disp) > 4:
                    disp = disp[:-2]
                if disp != display:
                    disp = disp[:-2] + "..." if len(disp) > 3 else disp
                t = f.render(disp, True, (240, 240, 250))
                screen.blit(t, (rr.x + 10, rr.centery - t.get_height() // 2))

            if total > max_visible:
                bar_x = x + w - 8
                pygame.draw.rect(screen, (40, 40, 60),
                                 (bar_x, list_y, 5, list_h), border_radius=2)
                thumb_h = max(24, int(list_h * max_visible / total))
                thumb_y = list_y + int((list_h - thumb_h) *
                                       self.dropdown_scroll / max(1, max_scroll))
                pygame.draw.rect(screen, (160, 130, 220),
                                 (bar_x, thumb_y, 5, thumb_h), border_radius=2)