# src/scenes/debug_scene/tabs/profile_tab.py
"""
Aba PERFIL — edição dos dados do jogador (nome, gold, XP, tempo de jogo,
progresso de fases, desfossilizadores, conquistas, Pokédex).
"""

import pygame
import uuid as uuid_lib
import json
import os
from datetime import datetime

from src.managers.save_manager import save_manager
from src.managers.sounds.sound_manager import sound_manager, SoundEffect


# =========================================================================
# CONSTANTES
# =========================================================================
SECTION_LIST = [
    ("perfil",       "PERFIL"),
    ("recursos",     "RECURSOS"),
    ("tempo",        "TEMPO DE JOGO"),
    ("progresso",    "PROGRESSO"),
    ("desfos",       "DESFOSSILIZADORES"),
    ("conquistas",   "CONQUISTAS"),
    ("pokedex",      "POKÉDEX"),
]

ROW_H = 34
INPUT_H = 32
SECTION_ROW_H = 42


class ProfileTab:
    """Aba de edição do perfil do jogador."""

    INPUT_NAMES = {
        "profile_name",
        "profile_money",
        "profile_score",
        "profile_play_h",
        "profile_play_m",
        "profile_play_s",
        "ach_new_id",
        "ach_new_counter_id",
        "desfo_pokemon_input",
        "desfo_fossil_input",
    }

    def __init__(self, parent):
        self.parent = parent
        self.current_section = "perfil"
        self.focused_input = None
        self.input_buffers = {}

        # Cache dos campos que precisam de refresh
        self._last_player_money = None
        self._last_player_score = None
        self._last_save_name = None

        # Scroll interno (para listas longas)
        self.scroll = 0
        self._max_scroll = 0
        self._last_content_height = 0

        # Scrollbar drag
        self._dragging_scroll = False
        self._scrollbar_rect = None
        self._scroll_geom = None

        # Selects
        self._desfo_selected = 0
        self._ach_selected = 0

        # Cache do catálogo de fases (evita refresh a cada frame)
        self._phase_cache = None

        self._refresh_buffers()

    # ==================================================================
    # HELPERS
    # ==================================================================
    @property
    def player(self):
        return self.parent.game.player

    @property
    def save(self):
        return save_manager.save_data

    def _meta(self):
        return self.save.setdefault("meta", {})

    def _refresh_buffers(self):
        """Preenche os buffers de texto com os valores atuais do player."""
        p = self.player
        total_sec = max(0, int(p.total_playtime))

        self.input_buffers = {
            "profile_name": self._meta().get("save_name", "Novo Jogo"),
            "profile_money": str(p.money),
            "profile_score": str(p.score),
            "profile_play_h": str(total_sec // 3600),
            "profile_play_m": str((total_sec % 3600) // 60),
            "profile_play_s": str(total_sec % 60),
            "ach_new_id": "",
            "ach_new_counter_id": "",
            "desfo_pokemon_input": "",
            "desfo_fossil_input": "",
        }

        self._last_player_money = p.money
        self._last_player_score = p.score
        self._last_save_name = self._meta().get("save_name", "Novo Jogo")

    def _sync_buffers_if_external_changed(self):
        """Se os valores mudaram por fora, atualiza o buffer."""
        p = self.player
        if p.money != self._last_player_money and self.focused_input != "profile_money":
            self.input_buffers["profile_money"] = str(p.money)
            self._last_player_money = p.money
        if p.score != self._last_player_score and self.focused_input != "profile_score":
            self.input_buffers["profile_score"] = str(p.score)
            self._last_player_score = p.score
        nm = self._meta().get("save_name", "Novo Jogo")
        if nm != self._last_save_name and self.focused_input != "profile_name":
            self.input_buffers["profile_name"] = nm
            self._last_save_name = nm

    def _format_playtime(self, total_sec):
        total_sec = max(0, int(total_sec))
        h = total_sec // 3600
        m = (total_sec % 3600) // 60
        s = total_sec % 60
        return f"{h:02d}h {m:02d}m {s:02d}s"

    def _parse_int(self, text, default=0, min_v=None, max_v=None):
        try:
            v = int(str(text).strip())
        except Exception:
            v = default
        if min_v is not None:
            v = max(min_v, v)
        if max_v is not None:
            v = min(max_v, v)
        return v

    def _commit_focused(self):
        """Aplica o valor do input focado atual."""
        fi = self.focused_input
        if not fi:
            return
        buf = self.input_buffers.get(fi, "").strip()
        p = self.player

        try:
            if fi == "profile_name":
                name = buf if buf else "Novo Jogo"
                if len(name) > 30:
                    name = name[:30]
                self._meta()["save_name"] = name
                self._last_save_name = name
                self.parent.show_message(f"Nome salvo: {name}")

            elif fi == "profile_money":
                p.money = self._parse_int(buf, default=p.money, min_v=0, max_v=9_999_999)
                self._last_player_money = p.money
                self.input_buffers["profile_money"] = str(p.money)

            elif fi == "profile_score":
                p.score = self._parse_int(buf, default=p.score, min_v=0, max_v=9_999_999)
                self._last_player_score = p.score
                self.input_buffers["profile_score"] = str(p.score)

            elif fi in ("profile_play_h", "profile_play_m", "profile_play_s"):
                h = self._parse_int(self.input_buffers["profile_play_h"], default=0, min_v=0, max_v=9999)
                m = self._parse_int(self.input_buffers["profile_play_m"], default=0, min_v=0, max_v=59)
                s = self._parse_int(self.input_buffers["profile_play_s"], default=0, min_v=0, max_v=59)
                p.total_playtime = float(h * 3600 + m * 60 + s)
                self.input_buffers["profile_play_h"] = str(h)
                self.input_buffers["profile_play_m"] = str(m)
                self.input_buffers["profile_play_s"] = str(s)

            elif fi == "ach_new_id":
                if buf:
                    self._add_achievement(buf)
                    self.input_buffers["ach_new_id"] = ""

            elif fi == "ach_new_counter_id":
                if buf:
                    self._add_achievement_counter(buf)
                    self.input_buffers["ach_new_counter_id"] = ""

        except Exception as e:
            self.parent.show_message(f"Erro: {e}")

        self.focused_input = None

    # ==================================================================
    # INTERFACE COM O PAI
    # ==================================================================
    def has_focus(self):
        return self.focused_input is not None

    def get_focus(self):
        return self.focused_input

    def clear_focus(self):
        if self.focused_input:
            self._commit_focused()

    # ==================================================================
    # PROGRESSO — CATÁLOGO E ESTADO
    # ==================================================================
    def _get_all_phase_ids_in_order(self):
        """Lista canônica de todos os phase_id em ordem (cap → número)."""
        try:
            from src.config.phase_catalog import phase_catalog
            phase_catalog.refresh()
            all_phases = phase_catalog.get_all_phases()
        except Exception as e:
            print(f"[PROFILE] Erro ao ler catálogo de fases: {e}")
            return []

        ordered = []
        for chapter in sorted(all_phases.keys()):
            numbers = sorted(p["number"] for p in all_phases[chapter])
            for num in numbers:
                ordered.append(f"{chapter}-{num}")
        return ordered

    def _get_chapters_and_phases(self):
        """Retorna [(chapter, [(phase_id, phase_name, number), ...]), ...] ordenado."""
        try:
            from src.config.phase_catalog import phase_catalog
            phase_catalog.refresh()
            all_phases = phase_catalog.get_all_phases()
        except Exception as e:
            print(f"[PROFILE] Erro ao ler catálogo: {e}")
            return []

        result = []
        for chapter in sorted(all_phases.keys()):
            phases_sorted = sorted(all_phases[chapter], key=lambda ph: ph["number"])
            chapter_phases = []
            for ph in phases_sorted:
                num = ph["number"]
                pid = f"{chapter}-{num}"
                name = ph.get("name", f"Fase {num}")
                chapter_phases.append((pid, name, num))
            result.append((chapter, chapter_phases))
        return result

    def _get_progress_state(self):
        """Retorna (e garante estrutura de) game_state do save."""
        gs = save_manager.save_data.setdefault("game_state", {})
        gs.setdefault("unlocked_phases", ["1-1"])
        gs.setdefault("completed_phases", [])
        gs.setdefault("stars", {})
        gs.setdefault("current_chapter", 1)
        gs.setdefault("current_phase", 1)
        return gs

    def _persist_progress(self, gs):
        """Aplica mudanças no save_data, recarrega o progress_manager e grava JSON."""
        save_manager.save_data["game_state"] = gs

        # Sync com o progress_manager (ele mantém estado em memória)
        try:
            from src.config.progress import progress_manager
            progress_manager.reload_progress()
        except Exception as e:
            print(f"[PROFILE] Aviso: reload_progress falhou: {e}")

        # Persiste no disco
        try:
            slot = save_manager.current_save_file or 1
            fp = os.path.join(save_manager.save_dir, f"save_{slot}.json")
            with open(fp, 'w', encoding='utf-8') as f:
                json.dump(save_manager.save_data, f, indent=2, ensure_ascii=False)
            print(f"[PROFILE] Progresso persistido em {fp}")
        except Exception as e:
            print(f"[PROFILE] Erro ao gravar progresso: {e}")

    # ==================================================================
    # PROGRESSO — AÇÕES
    # ==================================================================
    def _unlock_phase_in_order(self, phase_id):
        """Desbloqueia phase_id E todas as fases ANTERIORES na ordem."""
        ordered = self._get_all_phase_ids_in_order()
        if phase_id not in ordered:
            self.parent.show_message(f"Fase {phase_id} não existe no catálogo.")
            return

        idx = ordered.index(phase_id)
        gs = self._get_progress_state()
        unlocked = set(gs.get("unlocked_phases", []))

        for i in range(idx + 1):
            unlocked.add(ordered[i])

        gs["unlocked_phases"] = sorted(unlocked)
        self._persist_progress(gs)
        self.parent.show_message(f"Fases até {phase_id} desbloqueadas.")
        sound_manager.play_effect(SoundEffect.CLICK, volume=0.3)

    def _complete_phase_in_order(self, phase_id):
        """Marca como COMPLETAS phase_id E todas as ANTERIORES."""
        ordered = self._get_all_phase_ids_in_order()
        if phase_id not in ordered:
            self.parent.show_message(f"Fase {phase_id} não existe.")
            return

        idx = ordered.index(phase_id)
        gs = self._get_progress_state()
        unlocked = set(gs.get("unlocked_phases", []))
        completed = set(gs.get("completed_phases", []))
        stars = dict(gs.get("stars", {}))

        for i in range(idx + 1):
            pid = ordered[i]
            unlocked.add(pid)
            completed.add(pid)
            stars[pid] = 3

        # Desbloqueia a próxima (para o jogador poder continuar)
        if idx + 1 < len(ordered):
            unlocked.add(ordered[idx + 1])

        gs["unlocked_phases"] = sorted(unlocked)
        gs["completed_phases"] = sorted(completed)
        gs["stars"] = stars
        self._persist_progress(gs)
        self.parent.show_message(f"Fases até {phase_id} completadas (3 estrelas).")
        sound_manager.play_effect(SoundEffect.CLICK, volume=0.3)

    def _reset_phase_from(self, phase_id):
        """
        Reseta (desmarca conclusão) de phase_id E TODAS AS SEGUINTES.
        Mantém a fase atual e as anteriores desbloqueadas.
        """
        ordered = self._get_all_phase_ids_in_order()
        if phase_id not in ordered:
            self.parent.show_message(f"Fase {phase_id} não existe.")
            return

        idx = ordered.index(phase_id)
        gs = self._get_progress_state()
        completed = set(gs.get("completed_phases", []))
        stars = dict(gs.get("stars", {}))

        # Remove conclusão de phase_id em diante
        for i in range(idx, len(ordered)):
            pid = ordered[i]
            completed.discard(pid)
            stars.pop(pid, None)

        # Remove desbloqueio de phase_id em diante (a anterior continua liberada)
        unlocked = set(gs.get("unlocked_phases", []))
        for i in range(idx, len(ordered)):
            unlocked.discard(ordered[i])
        # Segurança: 1-1 sempre existe
        unlocked.add("1-1")

        gs["unlocked_phases"] = sorted(unlocked)
        gs["completed_phases"] = sorted(completed)
        gs["stars"] = stars
        self._persist_progress(gs)
        self.parent.show_message(f"Progresso resetado a partir de {phase_id}.")
        sound_manager.play_effect(SoundEffect.CLICK, volume=0.3)

    def _unlock_all_phases(self):
        ordered = self._get_all_phase_ids_in_order()
        gs = self._get_progress_state()
        gs["unlocked_phases"] = sorted(set(ordered))
        self._persist_progress(gs)
        self.parent.show_message(f"{len(ordered)} fases desbloqueadas.")
        sound_manager.play_effect(SoundEffect.CLICK, volume=0.3)

    def _complete_all_phases(self):
        ordered = self._get_all_phase_ids_in_order()
        gs = self._get_progress_state()
        gs["unlocked_phases"] = sorted(set(ordered))
        gs["completed_phases"] = sorted(set(ordered))
        stars = dict(gs.get("stars", {}))
        for pid in ordered:
            stars[pid] = 3
        gs["stars"] = stars
        self._persist_progress(gs)
        self.parent.show_message(f"{len(ordered)} fases completadas (3 estrelas).")
        sound_manager.play_effect(SoundEffect.CLICK, volume=0.3)

    def _reset_all_progress(self):
        gs = self._get_progress_state()
        gs["unlocked_phases"] = ["1-1"]
        gs["completed_phases"] = []
        gs["stars"] = {}
        gs["current_chapter"] = 1
        gs["current_phase"] = 1
        self.player.chapter_page_num = 1
        self._persist_progress(gs)
        self.parent.show_message("Todo o progresso resetado.")
        sound_manager.play_effect(SoundEffect.CLICK, volume=0.3)

    # ==================================================================
    # CONQUISTAS
    # ==================================================================
    def _ensure_achievements_struct(self):
        ach = self.player.achievements
        ach.setdefault("unlocked", [])
        ach.setdefault("counters", {})
        ach.setdefault("unlocked_data", {})
        return ach

    def _add_achievement(self, ach_id):
        ach = self._ensure_achievements_struct()
        ach_id = ach_id.strip()
        if not ach_id:
            return
        if ach_id in ach["unlocked"]:
            self.parent.show_message(f"'{ach_id}' já está desbloqueada.")
            return
        ach["unlocked"].append(ach_id)
        ach["unlocked_data"][ach_id] = {
            "date": datetime.now().isoformat(),
            "phase": "debug",
        }
        self.parent.show_message(f"Conquista desbloqueada: {ach_id}")
        sound_manager.play_effect(SoundEffect.CLICK, volume=0.3)

    def _remove_achievement(self, ach_id):
        ach = self._ensure_achievements_struct()
        if ach_id in ach["unlocked"]:
            ach["unlocked"].remove(ach_id)
            ach["unlocked_data"].pop(ach_id, None)
            self.parent.show_message(f"Conquista removida: {ach_id}")
            sound_manager.play_effect(SoundEffect.CLICK, volume=0.3)

    def _add_achievement_counter(self, counter_id):
        ach = self._ensure_achievements_struct()
        counter_id = counter_id.strip()
        if not counter_id:
            return
        if counter_id not in ach["counters"]:
            ach["counters"][counter_id] = 0
            self.parent.show_message(f"Contador criado: {counter_id} = 0")
        else:
            ach["counters"][counter_id] += 1
            self.parent.show_message(f"Contador {counter_id} = {ach['counters'][counter_id]}")

    def _remove_achievement_counter(self, counter_id):
        ach = self._ensure_achievements_struct()
        ach["counters"].pop(counter_id, None)

    def _clear_all_achievements(self):
        ach = self._ensure_achievements_struct()
        ach["unlocked"].clear()
        ach["unlocked_data"].clear()
        ach["counters"].clear()
        self.parent.show_message("Todas as conquistas foram limpas.")

    # ==================================================================
    # DESFOSSILIZADORES
    # ==================================================================
    def _get_desfos(self):
        return self.player.desfossilizadores

    def _add_desfo(self):
        desfos = self._get_desfos()
        new_id = (max([d.get("id", 0) for d in desfos] or [0]) + 1)
        desfos.append({
            "id": new_id,
            "level": 1,
            "status": "empty",
            "fossil_id": None,
            "pokemon_id": None,
            "start_time": None,
            "duration_minutes": 3600,
            "time_elapsed": 0.0,
        })
        self.parent.show_message(f"Desfossilizador #{new_id} adicionado.")

    def _remove_desfo(self, idx):
        desfos = self._get_desfos()
        if 0 <= idx < len(desfos):
            removed = desfos.pop(idx)
            self.parent.show_message(f"Desfossilizador #{removed.get('id')} removido.")
            if self._desfo_selected >= len(desfos):
                self._desfo_selected = max(0, len(desfos) - 1)

    def _cycle_desfo_level(self, idx, delta=1):
        desfos = self._get_desfos()
        if not (0 <= idx < len(desfos)):
            return
        d = desfos[idx]
        lv = d.get("level", 1) + delta
        if lv < 1: lv = 3
        if lv > 3: lv = 1
        d["level"] = lv
        durations = {1: 3600, 2: 2700, 3: 1200}
        d["duration_minutes"] = durations.get(lv, 3600)

    def _cycle_desfo_status(self, idx):
        desfos = self._get_desfos()
        if not (0 <= idx < len(desfos)):
            return
        d = desfos[idx]
        order = ["empty", "processing", "ready"]
        cur = d.get("status", "empty")
        try:
            i = order.index(cur)
        except ValueError:
            i = 0
        d["status"] = order[(i + 1) % len(order)]
        if d["status"] == "empty":
            d["fossil_id"] = None
            d["pokemon_id"] = None
            d["time_elapsed"] = 0.0
            d["start_time"] = None
        elif d["status"] == "processing":
            d["start_time"] = datetime.now().isoformat()
            if d.get("time_elapsed", 0) >= d.get("duration_minutes", 3600):
                d["time_elapsed"] = 0.0
        elif d["status"] == "ready":
            d["time_elapsed"] = d.get("duration_minutes", 3600)
            d["start_time"] = None

    def _finish_desfo(self, idx):
        desfos = self._get_desfos()
        if not (0 <= idx < len(desfos)):
            return
        d = desfos[idx]
        d["status"] = "ready"
        d["time_elapsed"] = d.get("duration_minutes", 3600)
        d["start_time"] = None

    def _reset_desfo_time(self, idx):
        desfos = self._get_desfos()
        if not (0 <= idx < len(desfos)):
            return
        desfos[idx]["time_elapsed"] = 0.0

    def _clear_all_desfos(self):
        self.player.desfossilizadores.clear()
        self.player._add_initial_desfossilizador()
        self._desfo_selected = 0
        self.parent.show_message("Desfossilizadores resetados.")

    # ==================================================================
    # POKÉDEX
    # ==================================================================
    def _unlock_full_pokedex(self):
        p = self.player
        try:
            all_ids = list(p.pokedex.pokemon_data.keys())
        except Exception:
            all_ids = list(range(1, 152))
        for pid in all_ids:
            p.seen_pokemon.add(pid)
            p.caught_pokemon.add(pid)
        self.parent.show_message(f"Pokédex completa: {len(all_ids)} Pokémon.")

    def _clear_pokedex(self):
        p = self.player
        p.seen_pokemon.clear()
        p.caught_pokemon.clear()
        self.parent.show_message("Pokédex resetada.")

    # ==================================================================
    # EVENTOS
    # ==================================================================
    def handle_event(self, event):
        # ===== Scrollbar drag =====
        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            if self._scrollbar_rect and self._scrollbar_rect.collidepoint(event.pos):
                self._dragging_scroll = True
                self._update_scroll_from_mouse(event.pos[1])
                return
        if event.type == pygame.MOUSEMOTION and self._dragging_scroll:
            self._update_scroll_from_mouse(event.pos[1])
            return
        if event.type == pygame.MOUSEBUTTONUP and event.button == 1:
            if self._dragging_scroll:
                self._dragging_scroll = False
                return

        # ===== Wheel =====
        if event.type == pygame.MOUSEWHEEL:
            if self._max_scroll > 0:
                self.scroll = max(0, min(self._max_scroll, self.scroll - event.y * 30))
            return

        # ===== Mouse down (clicks) =====
        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            clicked = self.parent.find_click_at(event.pos)
            if clicked not in self.INPUT_NAMES:
                if self.focused_input:
                    self._commit_focused()
            if clicked:
                self.on_click(clicked)
            return

        # ===== Teclado =====
        if event.type == pygame.KEYDOWN and self.focused_input:
            fi = self.focused_input

            if event.key == pygame.K_BACKSPACE:
                buf = self.input_buffers.get(fi, "")
                self.input_buffers[fi] = buf[:-1]
                return

            if event.key in (pygame.K_RETURN, pygame.K_TAB):
                self._commit_focused()
                return

            if event.key == pygame.K_ESCAPE:
                self.focused_input = None
                return

            if event.unicode and event.unicode.isprintable():
                buf = self.input_buffers.get(fi, "")
                is_numeric = fi in (
                    "profile_money", "profile_score",
                    "profile_play_h", "profile_play_m", "profile_play_s",
                )
                if is_numeric:
                    if event.unicode.isdigit() and len(buf) < 8:
                        self.input_buffers[fi] = buf + event.unicode
                else:
                    if len(buf) < 40:
                        self.input_buffers[fi] = buf + event.unicode

    def _update_scroll_from_mouse(self, mouse_y):
        if not self._scroll_geom:
            return
        bar_x, list_y, list_h, total_h = self._scroll_geom
        thumb_h = max(24, int(list_h * (list_h / max(1, total_h))))
        desired = mouse_y - list_y - thumb_h // 2
        desired = max(0, min(list_h - thumb_h, desired))
        ratio = desired / max(1, (list_h - thumb_h))
        self.scroll = int(ratio * self._max_scroll)

    # ==================================================================
    # DISPATCHER DE CLIQUE
    # ==================================================================
    def on_click(self, name):
        # ---- Navegação de seções ----
        if name.startswith("section_"):
            key = name[len("section_"):]
            self.current_section = key
            self.scroll = 0
            self.focused_input = None
            return

        # ---- PERFIL ----
        if name == "profile_name":
            self.focused_input = "profile_name"
            return
        if name == "uuid_regen":
            self.player.uuid = str(uuid_lib.uuid4())
            self.parent.show_message("Novo UUID gerado.")
            return

        # ---- RECURSOS ----
        if name == "profile_money":
            self.focused_input = "profile_money"
            return
        if name == "money_plus_1k":
            self.player.money += 1000; self._last_player_money = None; return
        if name == "money_plus_10k":
            self.player.money += 10000; self._last_player_money = None; return
        if name == "money_set_999999":
            self.player.money = 999999; self._last_player_money = None; return
        if name == "money_zero":
            self.player.money = 0; self._last_player_money = None; return

        if name == "profile_score":
            self.focused_input = "profile_score"
            return
        if name == "score_plus_100":
            self.player.score += 100; self._last_player_score = None; return
        if name == "score_plus_1000":
            self.player.score += 1000; self._last_player_score = None; return
        if name == "score_zero":
            self.player.score = 0; self._last_player_score = None; return

        if name == "toggle_starter":
            self.player.has_chosen_starter = not self.player.has_chosen_starter
            return

        if name == "chapter_minus":
            self.player.chapter_page_num = max(1, self.player.chapter_page_num - 1); return
        if name == "chapter_plus":
            self.player.chapter_page_num = min(8, self.player.chapter_page_num + 1); return

        # ---- TEMPO ----
        if name in ("profile_play_h", "profile_play_m", "profile_play_s"):
            self.focused_input = name
            return
        if name == "playtime_zero":
            self.player.total_playtime = 0.0
            self.input_buffers["profile_play_h"] = "0"
            self.input_buffers["profile_play_m"] = "0"
            self.input_buffers["profile_play_s"] = "0"
            return
        if name == "playtime_plus_1h":
            self.player.total_playtime += 3600.0
            self._refresh_buffers()
            return

        # ---- PROGRESSO ----
        if name == "prog_unlock_all":
            self._unlock_all_phases(); return
        if name == "prog_complete_all":
            self._complete_all_phases(); return
        if name == "prog_reset_all":
            self._reset_all_progress(); return

        if name.startswith("prog_unlock_"):
            phase_id = name[len("prog_unlock_"):]
            self._unlock_phase_in_order(phase_id); return

        if name.startswith("prog_complete_"):
            phase_id = name[len("prog_complete_"):]
            self._complete_phase_in_order(phase_id); return

        if name.startswith("prog_reset_"):
            phase_id = name[len("prog_reset_"):]
            self._reset_phase_from(phase_id); return

        # ---- DESFOSSILIZADORES ----
        if name.startswith("desfo_select_"):
            try:
                idx = int(name[len("desfo_select_"):])
            except ValueError:
                return
            self._desfo_selected = idx
            return

        if name == "desfo_add":
            self._add_desfo(); return
        if name == "desfo_clear_all":
            self._clear_all_desfos(); return

        if name.startswith("desfo_remove_"):
            try:
                idx = int(name[len("desfo_remove_"):])
            except ValueError:
                return
            self._remove_desfo(idx); return

        if name.startswith("desfo_lvlup_"):
            try:
                idx = int(name[len("desfo_lvlup_"):])
            except ValueError:
                return
            self._cycle_desfo_level(idx, +1); return

        if name.startswith("desfo_lvldown_"):
            try:
                idx = int(name[len("desfo_lvldown_"):])
            except ValueError:
                return
            self._cycle_desfo_level(idx, -1); return

        if name.startswith("desfo_status_"):
            try:
                idx = int(name[len("desfo_status_"):])
            except ValueError:
                return
            self._cycle_desfo_status(idx); return

        if name.startswith("desfo_finish_"):
            try:
                idx = int(name[len("desfo_finish_"):])
            except ValueError:
                return
            self._finish_desfo(idx); return

        if name.startswith("desfo_resettime_"):
            try:
                idx = int(name[len("desfo_resettime_"):])
            except ValueError:
                return
            self._reset_desfo_time(idx); return

        # ---- CONQUISTAS ----
        if name == "ach_new_id":
            self.focused_input = "ach_new_id"
            return
        if name == "ach_new_counter_id":
            self.focused_input = "ach_new_counter_id"
            return
        if name == "ach_add_common":
            for aid in ("first_capture", "first_evolution", "first_badge",
                        "max_level_reached", "perfect_phase"):
                self._add_achievement(aid)
            return
        if name == "ach_clear_all":
            self._clear_all_achievements(); return

        if name.startswith("ach_remove_"):
            try:
                idx = int(name[len("ach_remove_"):])
            except ValueError:
                return
            ach = self._ensure_achievements_struct()
            if 0 <= idx < len(ach["unlocked"]):
                self._remove_achievement(ach["unlocked"][idx])
            return

        if name.startswith("ctr_remove_"):
            try:
                idx = int(name[len("ctr_remove_"):])
            except ValueError:
                return
            ach = self._ensure_achievements_struct()
            keys = sorted(ach["counters"].keys())
            if 0 <= idx < len(keys):
                self._remove_achievement_counter(keys[idx])
            return

        if name.startswith("ctr_inc_"):
            try:
                idx = int(name[len("ctr_inc_"):])
            except ValueError:
                return
            ach = self._ensure_achievements_struct()
            keys = sorted(ach["counters"].keys())
            if 0 <= idx < len(keys):
                k = keys[idx]
                ach["counters"][k] = ach["counters"].get(k, 0) + 1
            return

        if name.startswith("ctr_dec_"):
            try:
                idx = int(name[len("ctr_dec_"):])
            except ValueError:
                return
            ach = self._ensure_achievements_struct()
            keys = sorted(ach["counters"].keys())
            if 0 <= idx < len(keys):
                k = keys[idx]
                ach["counters"][k] = max(0, ach["counters"].get(k, 0) - 1)
            return

        # ---- POKÉDEX ----
        if name == "pokedex_full":
            self._unlock_full_pokedex(); return
        if name == "pokedex_clear":
            self._clear_pokedex(); return

        # ---- FOOTER ----
        if name == "action_save_profile":
            self.parent.save_game()
            self.parent.show_message("Perfil salvo!")
            sound_manager.play_effect(SoundEffect.CLICK, volume=0.3)
            return

    # ==================================================================
    # UPDATE
    # ==================================================================
    def fixed_update(self, dt):
        self._sync_buffers_if_external_changed()

    # ==================================================================
    # RENDER
    # ==================================================================
    def render(self, screen, left_rect, right_rect):
        p = self.parent

        self._scrollbar_rect = None
        self._scroll_geom = None

        # ---- Coluna esquerda ----
        self._render_section_list(screen, left_rect)

        # ---- Coluna direita (com clip e scroll) ----
        old_clip = screen.get_clip()
        clip = pygame.Rect(right_rect.x + 4, right_rect.y + 4,
                           right_rect.width - 8, right_rect.height - 8)
        screen.set_clip(clip)

        content_top = right_rect.y + 12
        scroll_y = content_top - self.scroll

        if self.current_section == "perfil":
            self._render_section_perfil(screen, right_rect, scroll_y)
        elif self.current_section == "recursos":
            self._render_section_recursos(screen, right_rect, scroll_y)
        elif self.current_section == "tempo":
            self._render_section_tempo(screen, right_rect, scroll_y)
        elif self.current_section == "progresso":
            self._render_section_progresso(screen, right_rect, scroll_y)
        elif self.current_section == "desfos":
            self._render_section_desfos(screen, right_rect, scroll_y)
        elif self.current_section == "conquistas":
            self._render_section_conquistas(screen, right_rect, scroll_y)
        elif self.current_section == "pokedex":
            self._render_section_pokedex(screen, right_rect, scroll_y)

        screen.set_clip(old_clip)

        if self._last_content_height > right_rect.height - 20:
            self._max_scroll = self._last_content_height - (right_rect.height - 20)
            self.scroll = max(0, min(self._max_scroll, self.scroll))
            self._render_scrollbar(screen, right_rect)
        else:
            self._max_scroll = 0
            self.scroll = 0

    # ------------------------------------------------------------------
    # COLUNA ESQUERDA — SEÇÕES + RESUMO
    # ------------------------------------------------------------------
    def _render_section_list(self, screen, left_rect):
        p = self.parent

        header_f = p.get_font(14)
        header = header_f.render("SEÇÕES", True, (180, 190, 215))
        screen.blit(header, (left_rect.x + 14, left_rect.y + 12))

        summary_y = left_rect.y + 40
        summary_h = 110
        summary_rect = pygame.Rect(left_rect.x + 10, summary_y,
                                    left_rect.width - 20, summary_h)
        pygame.draw.rect(screen, (32, 36, 54), summary_rect, border_radius=8)
        pygame.draw.rect(screen, (80, 90, 120), summary_rect, 1, border_radius=8)

        name = self._meta().get("save_name", "Novo Jogo")
        nf = p.get_font(18)
        ns = nf.render(name, True, (255, 220, 120))
        screen.blit(ns, (summary_rect.x + 12, summary_rect.y + 10))

        uid = getattr(self.player, "uuid", "") or "?"
        uid_short = uid[:8] + "..." + uid[-4:] if len(uid) > 12 else uid
        sf = p.get_font(11)
        us = sf.render(f"UUID: {uid_short}", True, (140, 150, 180))
        screen.blit(us, (summary_rect.x + 12, summary_rect.y + 34))

        stat_f = p.get_font(13)
        money_s = stat_f.render(f"Gold: {self.player.money}",
                                 True, (220, 200, 100))
        screen.blit(money_s, (summary_rect.x + 12, summary_rect.y + 56))

        score_s = stat_f.render(f"Score: {self.player.score}",
                                 True, (200, 220, 200))
        screen.blit(score_s, (summary_rect.x + 12, summary_rect.y + 74))

        team_s = stat_f.render(
            f"Time: {len(self.player.team)}/6   Box: {len(self.player.pc_box)}",
            True, (180, 200, 220))
        screen.blit(team_s, (summary_rect.x + 12, summary_rect.y + 92))

        list_y = summary_rect.bottom + 16
        section_row_h = SECTION_ROW_H

        for i, (key, label) in enumerate(SECTION_LIST):
            row = pygame.Rect(left_rect.x + 10, list_y + i * section_row_h,
                              left_rect.width - 20, section_row_h - 4)
            active = (self.current_section == key)
            hovered = row.collidepoint(pygame.mouse.get_pos())

            if active:
                bg, border = (60, 50, 100), (200, 180, 255)
            elif hovered:
                bg, border = (45, 40, 65), (120, 100, 160)
            else:
                bg, border = (30, 32, 48), (55, 55, 75)

            pygame.draw.rect(screen, bg, row, border_radius=6)
            pygame.draw.rect(screen, border, row,
                             2 if active else 1, border_radius=6)
            p.register_click(f"section_{key}", row)

            f = p.get_font(14)
            t = f.render(label, True,
                         (255, 255, 255) if active else (200, 200, 220))
            screen.blit(t, (row.x + 12,
                            row.y + (row.height - t.get_height()) // 2))

            if active:
                pygame.draw.rect(screen, (255, 215, 0),
                                 (row.x + 4, row.y + 4, 3, row.height - 8),
                                 border_radius=2)

    # ------------------------------------------------------------------
    # HELPERS DE RENDER
    # ------------------------------------------------------------------
    def _render_section_header(self, screen, rect, y, title, subtitle=None):
        p = self.parent
        f = p.get_font(22)
        t = f.render(title, True, (255, 220, 120))
        screen.blit(t, (rect.x + 20, y))
        y += t.get_height() + 4

        if subtitle:
            sf = p.get_font(13)
            st = sf.render(subtitle, True, (160, 170, 200))
            screen.blit(st, (rect.x + 20, y))
            y += st.get_height() + 8

        pygame.draw.line(screen, (90, 80, 130),
                         (rect.x + 20, y), (rect.right - 20, y), 1)
        y += 12
        return y

    def _render_field_row(self, screen, rect, y, label, value, width=None):
        p = self.parent
        lf = p.get_font(14)
        label_s = lf.render(label, True, (170, 180, 210))
        screen.blit(label_s, (rect.x + 20, y + 4))

        vf = p.get_font(15)
        value_s = vf.render(str(value), True, (220, 225, 240))
        screen.blit(value_s, (rect.x + 20 + label_s.get_width() + 12, y + 3))

    def _render_text_input_row(self, screen, rect, y, label, click_name,
                                width=260, focus_key=None):
        p = self.parent
        lf = p.get_font(14)
        label_s = lf.render(label, True, (170, 180, 210))
        screen.blit(label_s, (rect.x + 20, y + 6))

        inp_x = rect.x + 20 + label_s.get_width() + 12
        inp_rect = pygame.Rect(inp_x, y, width, INPUT_H)

        p.register_click(click_name, inp_rect)

        focused = (self.focused_input == focus_key) if focus_key else False
        pygame.draw.rect(screen, (15, 15, 25), inp_rect, border_radius=5)
        border_color = (255, 200, 60) if focused else (80, 80, 110)
        pygame.draw.rect(screen, border_color, inp_rect, 2, border_radius=5)

        f = p.get_font(14)
        txt = self.input_buffers.get(click_name, "")
        if focused:
            txt += "_"
        ts = f.render(txt if txt else "(vazio)", True,
                      (230, 230, 240) if txt else (110, 110, 130))
        screen.blit(ts, (inp_rect.x + 8,
                         inp_rect.y + (inp_rect.height - ts.get_height()) // 2))

        return y + INPUT_H + 8

    # ------------------------------------------------------------------
    # SEÇÃO: PERFIL
    # ------------------------------------------------------------------
    def _render_section_perfil(self, screen, rect, y):
        p = self.parent

        y = self._render_section_header(screen, rect, y, "PERFIL",
                                         "Edite informações básicas do jogador")

        y = self._render_text_input_row(screen, rect, y, "Nome do perfil",
                                         "profile_name",
                                         width=rect.width - 260,
                                         focus_key="profile_name")

        uid = getattr(self.player, "uuid", "") or "?"
        self._render_field_row(screen, rect, y, "UUID:", uid)
        y += 30

        btn = pygame.Rect(rect.x + 20, y, 190, 28)
        p.register_click("uuid_regen", btn)
        p.draw_button(screen, btn, "Regerar UUID", font_size=13)
        y += 44

        starter = getattr(self.player, "has_chosen_starter", False)
        p.render_toggle(screen, rect.x + 20, y, rect.width - 60,
                        28, "Já escolheu starter",
                        starter, "toggle_starter")
        y += 40

        p.render_cycle_row(screen, rect.x + 20, y, rect.width - 60, 28,
                           "Capítulo atual",
                           str(self.player.chapter_page_num),
                           "chapter_minus", "chapter_plus")
        y += 44

        info_f = p.get_font(12)
        info = info_f.render(
            "Alterações são salvas ao clicar em SALVAR (rodapé).",
            True, (150, 160, 190))
        screen.blit(info, (rect.x + 20, y))
        y += 30

        self._last_content_height = y - rect.y

    # ------------------------------------------------------------------
    # SEÇÃO: RECURSOS
    # ------------------------------------------------------------------
    def _render_section_recursos(self, screen, rect, y):
        p = self.parent

        y = self._render_section_header(screen, rect, y, "RECURSOS",
                                         "Gold, XP e progressão")

        y = self._render_text_input_row(screen, rect, y, "Gold atual",
                                         "profile_money",
                                         width=180, focus_key="profile_money")

        bw = 90
        bh = 28
        btn_specs = [
            ("money_plus_1k", "+1k"),
            ("money_plus_10k", "+10k"),
            ("money_set_999999", "MAX"),
            ("money_zero", "Zerar"),
        ]
        bx = rect.x + 20
        for cname, label in btn_specs:
            b = pygame.Rect(bx, y, bw, bh)
            p.register_click(cname, b)
            p.draw_button(screen, b, label, font_size=13)
            bx += bw + 8
        y += bh + 16

        y = self._render_text_input_row(screen, rect, y, "Score (XP total)",
                                         "profile_score",
                                         width=180, focus_key="profile_score")

        btn_specs = [
            ("score_plus_100", "+100"),
            ("score_plus_1000", "+1k"),
            ("score_zero", "Zerar"),
        ]
        bx = rect.x + 20
        for cname, label in btn_specs:
            b = pygame.Rect(bx, y, bw, bh)
            p.register_click(cname, b)
            p.draw_button(screen, b, label, font_size=13)
            bx += bw + 8
        y += bh + 20

        info_f = p.get_font(14)
        info = info_f.render(
            f"Time: {len(p.game.player.team)} Pokémon   ·   "
            f"Box: {len(p.game.player.pc_box)} Pokémon",
            True, (200, 210, 230))
        screen.blit(info, (rect.x + 20, y))
        y += 30

        self._last_content_height = y - rect.y

    # ------------------------------------------------------------------
    # SEÇÃO: TEMPO DE JOGO
    # ------------------------------------------------------------------
    def _render_section_tempo(self, screen, rect, y):
        p = self.parent

        y = self._render_section_header(screen, rect, y, "TEMPO DE JOGO",
                                         "Edite o tempo total registrado")

        box = pygame.Rect(rect.x + 20, y, rect.width - 60, 60)
        pygame.draw.rect(screen, (26, 30, 48), box, border_radius=8)
        pygame.draw.rect(screen, (90, 80, 130), box, 1, border_radius=8)

        big_f = p.get_font(28)
        total = self._format_playtime(self.player.total_playtime)
        bt = big_f.render(total, True, (255, 220, 120))
        screen.blit(bt, bt.get_rect(center=box.center))
        y = box.bottom + 16

        lab_f = p.get_font(14)
        sx = rect.x + 20
        for cname, lab, w in [
            ("profile_play_h", "Horas", 90),
            ("profile_play_m", "Minutos", 90),
            ("profile_play_s", "Segundos", 90),
        ]:
            ls = lab_f.render(lab, True, (170, 180, 210))
            screen.blit(ls, (sx, y + 6))
            inp = pygame.Rect(sx, y + 26, w, INPUT_H)
            p.register_click(cname, inp)
            focused = (self.focused_input == cname)
            pygame.draw.rect(screen, (15, 15, 25), inp, border_radius=5)
            bc = (255, 200, 60) if focused else (80, 80, 110)
            pygame.draw.rect(screen, bc, inp, 2, border_radius=5)
            f = p.get_font(15)
            txt = self.input_buffers.get(cname, "0")
            if focused:
                txt += "_"
            ts = f.render(txt, True, (230, 230, 240))
            screen.blit(ts, ts.get_rect(center=inp.center))
            sx += w + 20

        y += INPUT_H + 46

        bw = 130
        bh = 30
        b1 = pygame.Rect(rect.x + 20, y, bw, bh)
        p.register_click("playtime_zero", b1)
        p.draw_button(screen, b1, "Zerar tempo", danger=True, font_size=13)

        b2 = pygame.Rect(b1.right + 10, y, bw, bh)
        p.register_click("playtime_plus_1h", b2)
        p.draw_button(screen, b2, "+1 hora", font_size=13)
        y += bh + 20

        info = p.get_font(12).render(
            "Pressione ENTER em um campo para aplicar.",
            True, (150, 160, 190))
        screen.blit(info, (rect.x + 20, y))
        y += 24

        self._last_content_height = y - rect.y

    # ------------------------------------------------------------------
    # SEÇÃO: PROGRESSO
    # ------------------------------------------------------------------
    # ------------------------------------------------------------------
    # SEÇÃO: PROGRESSO
    # ------------------------------------------------------------------
    def _render_section_progresso(self, screen, rect, y):
        p = self.parent

        y = self._render_section_header(
            screen, rect, y, "PROGRESSO DE FASES",
            "Clique numa fase para marcar o progresso até ela")

        gs = self._get_progress_state()
        unlocked_set = set(gs.get("unlocked_phases", []))
        completed_set = set(gs.get("completed_phases", []))
        stars = gs.get("stars", {})

        chapters = self._get_chapters_and_phases()
        if not chapters:
            f = p.get_font(16)
            t = f.render("Catálogo de fases vazio.", True, (180, 140, 140))
            screen.blit(t, (rect.x + 20, y))
            self._last_content_height = y + 40 - rect.y
            return

        # ---- Contadores no topo ----
        total_phases = sum(len(ph) for _, ph in chapters)
        unlocked_n = len(unlocked_set)
        completed_n = len(completed_set)

        cf = p.get_font(13)
        info = cf.render(
            f"Total: {total_phases} fases    "
            f"Desbloqueadas: {unlocked_n}    "
            f"Completadas: {completed_n}",
            True, (200, 210, 230))
        screen.blit(info, (rect.x + 20, y))
        y += 26

        # ---- Botão resetar tudo (única ação destrutiva) ----
        b_reset = pygame.Rect(rect.x + 20, y, 220, 28)
        p.register_click("prog_reset_all", b_reset)
        p.draw_button(screen, b_reset, "Resetar progresso",
                      danger=True, font_size=13)
        y += 40

        # ---- Legenda de cores ----
        legend_f = p.get_font(12)
        legend_y = y
        legend_items = [
            ((30, 28, 34), (70, 65, 70), "Bloqueada"),
            ((32, 40, 55), (100, 130, 180), "Desbloqueada"),
            ((32, 50, 36), (80, 180, 100), "Completada"),
        ]
        lx = rect.x + 20
        for bg, border, label in legend_items:
            chip = pygame.Rect(lx, legend_y, 16, 16)
            pygame.draw.rect(screen, bg, chip, border_radius=3)
            pygame.draw.rect(screen, border, chip, 1, border_radius=3)
            lf = legend_f.render(label, True, (180, 190, 210))
            screen.blit(lf, (chip.right + 6, chip.y + 1))
            lx += chip.width + 6 + lf.get_width() + 20
        y += 26

        # ---- Grid de chips por capítulo ----
        chip_w = 74
        chip_h = 42
        chip_gap = 8
        chips_per_row = max(1, (rect.width - 60) // (chip_w + chip_gap))

        for chapter, phases in chapters:
            # Header do capítulo
            ch_f = p.get_font(15)
            ch_completed = sum(1 for (pid, _, _) in phases if pid in completed_set)
            ch_total = len(phases)
            ch_label = f"CAP {chapter}"
            ch_s = ch_f.render(ch_label, True, (255, 220, 120))
            screen.blit(ch_s, (rect.x + 20, y))
            ch_info_f = p.get_font(12)
            ch_info = ch_info_f.render(
                f"{ch_completed}/{ch_total}", True, (180, 200, 180))
            screen.blit(ch_info, (rect.x + 20 + ch_s.get_width() + 10,
                                  y + 3))
            y += 22

            # Chips das fases
            col = 0
            row_start_y = y
            for (phase_id, _name, _num) in phases:
                if col >= chips_per_row:
                    col = 0
                    y += chip_h + chip_gap

                cx = rect.x + 20 + col * (chip_w + chip_gap)
                chip = pygame.Rect(cx, y, chip_w, chip_h)

                is_unlocked = phase_id in unlocked_set
                is_completed = phase_id in completed_set

                if is_completed:
                    bg = (32, 50, 36)
                    border = (80, 180, 100)
                    txt_col = (200, 240, 200)
                elif is_unlocked:
                    bg = (32, 40, 55)
                    border = (100, 130, 180)
                    txt_col = (190, 215, 245)
                else:
                    bg = (30, 28, 34)
                    border = (70, 65, 70)
                    txt_col = (140, 130, 140)

                hovered = chip.collidepoint(pygame.mouse.get_pos())
                if hovered:
                    bg = tuple(min(255, c + 18) for c in bg)
                    border = tuple(min(255, c + 30) for c in border)

                pygame.draw.rect(screen, bg, chip, border_radius=6)
                pygame.draw.rect(screen, border, chip, 2, border_radius=6)

                # ID grande no centro
                id_f = p.get_font(18)
                id_s = id_f.render(phase_id, True, txt_col)
                screen.blit(id_s, id_s.get_rect(center=chip.center))

                # Estrela pequena se completa
                if is_completed:
                    star_f = p.get_font(11)
                    st = star_f.render("3/3", True, (255, 220, 120))
                    screen.blit(st, (chip.right - st.get_width() - 4,
                                     chip.bottom - st.get_height() - 2))

                p.register_click(f"prog_complete_{phase_id}", chip)

                col += 1

            y = row_start_y + ((ch_total - 1) // chips_per_row + 1) * (chip_h + chip_gap)
            y += 12

        # ---- Rodapé explicativo ----
        hint_f = p.get_font(12)
        hint = hint_f.render(
            "Clicar numa fase desbloqueia e completa TODAS as anteriores.",
            True, (150, 170, 200))
        screen.blit(hint, (rect.x + 20, y))
        y += 22

        self._last_content_height = y - rect.y

    # ------------------------------------------------------------------
    # SEÇÃO: DESFOSSILIZADORES
    # ------------------------------------------------------------------
    def _render_section_desfos(self, screen, rect, y):
        p = self.parent

        y = self._render_section_header(
            screen, rect, y, "DESFOSSILIZADORES",
            "Gerencie cada fóssil em processamento")

        b1 = pygame.Rect(rect.x + 20, y, 150, 30)
        p.register_click("desfo_add", b1)
        p.draw_button(screen, b1, "+ Adicionar", success=True, font_size=13)

        b2 = pygame.Rect(b1.right + 10, y, 170, 30)
        p.register_click("desfo_clear_all", b2)
        p.draw_button(screen, b2, "Resetar tudo", danger=True, font_size=13)
        y += 42

        desfos = self._get_desfos()

        if not desfos:
            f = p.get_font(16)
            t = f.render("Nenhum desfossilizador", True, (160, 160, 180))
            screen.blit(t, (rect.centerx - t.get_width() // 2, y + 20))
            self._last_content_height = y + 60 - rect.y
            return

        row_h = 130
        for i, d in enumerate(desfos):
            row_rect = pygame.Rect(rect.x + 20, y, rect.width - 60, row_h)

            selected = (i == self._desfo_selected)
            bg = (48, 42, 76) if selected else (30, 34, 50)
            border = (180, 160, 240) if selected else (70, 76, 100)
            pygame.draw.rect(screen, bg, row_rect, border_radius=8)
            pygame.draw.rect(screen, border, row_rect,
                             2 if selected else 1, border_radius=8)

            p.register_click(f"desfo_select_{i}", row_rect)

            header_f = p.get_font(16)
            hs = header_f.render(
                f"Desfossilizador #{d.get('id', i+1)}",
                True, (255, 220, 120))
            screen.blit(hs, (row_rect.x + 14, row_rect.y + 10))

            status = d.get("status", "empty")
            status_colors = {
                "empty": ((90, 90, 110), (200, 200, 220)),
                "processing": ((200, 140, 60), (255, 240, 200)),
                "ready": ((80, 180, 100), (230, 255, 230)),
            }
            sc, tc = status_colors.get(status, ((120, 120, 120), (255, 255, 255)))
            stat_s = p.get_font(12).render(status.upper(), True, tc)
            stat_rect = pygame.Rect(row_rect.right - 130, row_rect.y + 10,
                                     stat_s.get_width() + 16,
                                     stat_s.get_height() + 6)
            pygame.draw.rect(screen, sc, stat_rect, border_radius=4)
            screen.blit(stat_s, (stat_rect.x + 8, stat_rect.y + 3))

            info_f = p.get_font(13)
            info1 = info_f.render(
                f"Nível: {d.get('level', 1)}   ·   "
                f"Fóssil: {d.get('fossil_id') or '—'}   ·   "
                f"Pokémon: {d.get('pokemon_id') or '—'}",
                True, (200, 210, 230))
            screen.blit(info1, (row_rect.x + 14, row_rect.y + 36))

            elapsed = d.get("time_elapsed", 0)
            dur = d.get("duration_minutes", 3600)
            pct = min(1.0, elapsed / max(1, dur))
            time_str = f"Tempo: {int(elapsed)}/{int(dur)} ({int(pct*100)}%)"
            info2 = info_f.render(time_str, True, (180, 190, 210))
            screen.blit(info2, (row_rect.x + 14, row_rect.y + 56))

            bar = pygame.Rect(row_rect.x + 14, row_rect.y + 78,
                              row_rect.width - 28, 10)
            pygame.draw.rect(screen, (40, 44, 60), bar, border_radius=5)
            if pct > 0:
                col = (80, 180, 100) if pct >= 1.0 else (200, 160, 60)
                pygame.draw.rect(screen, col,
                                 (bar.x, bar.y, int(bar.width * pct), bar.height),
                                 border_radius=5)
            pygame.draw.rect(screen, (80, 90, 120), bar, 1, border_radius=5)

            by = row_rect.bottom - 34
            bx = row_rect.x + 14
            bw2 = 80
            bh2 = 24
            specs = [
                (f"desfo_lvldown_{i}", "Lvl-"),
                (f"desfo_lvlup_{i}", "Lvl+"),
                (f"desfo_status_{i}", "Status"),
                (f"desfo_finish_{i}", "Pronto"),
                (f"desfo_resettime_{i}", "Reset"),
                (f"desfo_remove_{i}", "X"),
            ]
            for cname, label in specs:
                b = pygame.Rect(bx, by, bw2, bh2)
                p.register_click(cname, b)
                danger = (cname == f"desfo_remove_{i}")
                success = (cname == f"desfo_finish_{i}")
                p.draw_button(screen, b, label,
                              danger=danger, success=success, font_size=11)
                bx += bw2 + 6

            y += row_h + 12

        self._last_content_height = y - rect.y

    # ------------------------------------------------------------------
    # SEÇÃO: CONQUISTAS
    # ------------------------------------------------------------------
    def _render_section_conquistas(self, screen, rect, y):
        p = self.parent
        ach = self._ensure_achievements_struct()

        y = self._render_section_header(
            screen, rect, y, "CONQUISTAS",
            "Desbloqueie, remova e gerencie conquistas e contadores")

        b1 = pygame.Rect(rect.x + 20, y, 220, 30)
        p.register_click("ach_add_common", b1)
        p.draw_button(screen, b1, "+ Comuns", success=True, font_size=13)

        b2 = pygame.Rect(b1.right + 10, y, 200, 30)
        p.register_click("ach_clear_all", b2)
        p.draw_button(screen, b2, "Limpar tudo", danger=True, font_size=13)
        y += 42

        y = self._render_text_input_row(screen, rect, y,
                                         "Adicionar conquista (ID)",
                                         "ach_new_id",
                                         width=rect.width - 320,
                                         focus_key="ach_new_id")
        y = self._render_text_input_row(screen, rect, y,
                                         "Criar/incrementar contador",
                                         "ach_new_counter_id",
                                         width=rect.width - 320,
                                         focus_key="ach_new_counter_id")
        y += 6

        hdr_f = p.get_font(15)
        hs = hdr_f.render(
            f"Desbloqueadas ({len(ach['unlocked'])})",
            True, (255, 220, 120))
        screen.blit(hs, (rect.x + 20, y))
        y += 26

        if not ach["unlocked"]:
            f = p.get_font(13)
            t = f.render("Nenhuma conquista desbloqueada.",
                         True, (160, 160, 180))
            screen.blit(t, (rect.x + 20, y))
            y += 30
        else:
            for i, aid in enumerate(sorted(ach["unlocked"])):
                row = pygame.Rect(rect.x + 20, y, rect.width - 60, 26)
                pygame.draw.rect(screen, (30, 40, 32), row, border_radius=4)
                pygame.draw.rect(screen, (70, 130, 80), row, 1, border_radius=4)

                f = p.get_font(13)
                t = f.render(aid, True, (200, 240, 200))
                screen.blit(t, (row.x + 10,
                                row.y + (row.height - t.get_height()) // 2))

                xb = pygame.Rect(row.right - 30, row.y + 2, 24, 22)
                p.register_click(f"ach_remove_{i}", xb)
                p.draw_button(screen, xb, "x", danger=True, font_size=11)

                y += 30

        y += 14

        hdr_f = p.get_font(15)
        hs = hdr_f.render(
            f"Contadores ({len(ach['counters'])})",
            True, (255, 220, 120))
        screen.blit(hs, (rect.x + 20, y))
        y += 26

        if not ach["counters"]:
            f = p.get_font(13)
            t = f.render("Nenhum contador.",
                         True, (160, 160, 180))
            screen.blit(t, (rect.x + 20, y))
            y += 30
        else:
            for i, key in enumerate(sorted(ach["counters"].keys())):
                row = pygame.Rect(rect.x + 20, y, rect.width - 60, 26)
                pygame.draw.rect(screen, (30, 34, 48), row, border_radius=4)
                pygame.draw.rect(screen, (70, 80, 110), row, 1, border_radius=4)

                f = p.get_font(13)
                val = ach["counters"][key]
                t = f.render(f"{key}", True, (200, 210, 240))
                screen.blit(t, (row.x + 10,
                                row.y + (row.height - t.get_height()) // 2))

                vf = p.get_font(14)
                v = vf.render(str(val), True, (220, 240, 220))
                screen.blit(v, (row.right - 190, row.y + 5))

                b_dec = pygame.Rect(row.right - 155, row.y + 2, 24, 22)
                b_inc = pygame.Rect(row.right - 125, row.y + 2, 24, 22)
                b_x = pygame.Rect(row.right - 60, row.y + 2, 24, 22)
                p.register_click(f"ctr_dec_{i}", b_dec)
                p.register_click(f"ctr_inc_{i}", b_inc)
                p.register_click(f"ctr_remove_{i}", b_x)
                p.draw_button(screen, b_dec, "-", font_size=13)
                p.draw_button(screen, b_inc, "+", font_size=13)
                p.draw_button(screen, b_x, "x", danger=True, font_size=11)

                y += 30

        y += 14
        self._last_content_height = y - rect.y

    # ------------------------------------------------------------------
    # SEÇÃO: POKÉDEX
    # ------------------------------------------------------------------
    def _render_section_pokedex(self, screen, rect, y):
        p = self.parent

        y = self._render_section_header(
            screen, rect, y, "POKÉDEX",
            "Gerencie os registros vistos/capturados")

        seen = len(self.player.seen_pokemon)
        caught = len(self.player.caught_pokemon)

        cw = (rect.width - 80) // 2
        ch = 90

        card1 = pygame.Rect(rect.x + 20, y, cw, ch)
        pygame.draw.rect(screen, (30, 42, 38), card1, border_radius=8)
        pygame.draw.rect(screen, (80, 160, 100), card1, 2, border_radius=8)
        f = p.get_font(14)
        lbl = f.render("VISTOS", True, (150, 220, 170))
        screen.blit(lbl, (card1.x + 14, card1.y + 12))
        big = p.get_font(32)
        val = big.render(str(seen), True, (200, 240, 200))
        screen.blit(val, (card1.x + 14, card1.y + 34))

        card2 = pygame.Rect(card1.right + 20, y, cw, ch)
        pygame.draw.rect(screen, (42, 36, 32), card2, border_radius=8)
        pygame.draw.rect(screen, (200, 160, 80), card2, 2, border_radius=8)
        lbl = f.render("CAPTURADOS", True, (220, 200, 150))
        screen.blit(lbl, (card2.x + 14, card2.y + 12))
        val = big.render(str(caught), True, (240, 220, 180))
        screen.blit(val, (card2.x + 14, card2.y + 34))

        y = card1.bottom + 20

        b1 = pygame.Rect(rect.x + 20, y, 260, 34)
        p.register_click("pokedex_full", b1)
        p.draw_button(screen, b1, "Desbloquear Pokédex completa",
                      success=True, font_size=14)

        b2 = pygame.Rect(rect.x + 20, b1.bottom + 10, 260, 34)
        p.register_click("pokedex_clear", b2)
        p.draw_button(screen, b2, "Resetar Pokédex",
                      danger=True, font_size=14)

        y = b2.bottom + 20

        info = p.get_font(12).render(
            "Ações afetam apenas a Pokédex — não alteram o time ou a box.",
            True, (150, 160, 190))
        screen.blit(info, (rect.x + 20, y))
        y += 24

        self._last_content_height = y - rect.y

    # ------------------------------------------------------------------
    # SCROLLBAR
    # ------------------------------------------------------------------
    def _render_scrollbar(self, screen, right_rect):
        if self._max_scroll <= 0:
            return
        bar_x = right_rect.right - 10
        bar_y = right_rect.y + 6
        bar_h = right_rect.height - 12

        pygame.draw.rect(screen, (40, 40, 60),
                         (bar_x, bar_y, 5, bar_h), border_radius=3)

        ratio = (right_rect.height - 20) / max(1, self._last_content_height)
        thumb_h = max(24, int(bar_h * ratio))
        max_s = max(1, self._max_scroll)
        thumb_y = bar_y + int((bar_h - thumb_h) * self.scroll / max_s)

        pygame.draw.rect(screen, (140, 110, 180),
                         (bar_x, thumb_y, 5, thumb_h), border_radius=3)

        self._scrollbar_rect = pygame.Rect(bar_x - 3, bar_y, 11, bar_h)
        self._scroll_geom = (bar_x, bar_y, bar_h, self._last_content_height)

    # ------------------------------------------------------------------
    # FOOTER
    # ------------------------------------------------------------------
    def render_footer(self, screen, footer_rect):
        p = self.parent
        btn_h = min(40, footer_rect.height - 14)
        btn_y = footer_rect.y + (footer_rect.height - btn_h) // 2

        save_rect = pygame.Rect(footer_rect.x + 24, btn_y, 240, btn_h)
        p.register_click("action_save_profile", save_rect)
        p.draw_button(screen, save_rect, "SALVAR PERFIL",
                      success=True, font_size=16)

        hint_f = p.get_font(13)
        hint = hint_f.render(
            "ENTER aplica o campo em foco   ·   Scroll navega entre seções",
            True, (140, 140, 160))
        screen.blit(hint, (footer_rect.right - hint.get_width() - 24,
                           footer_rect.y + (footer_rect.height - hint.get_height()) // 2))