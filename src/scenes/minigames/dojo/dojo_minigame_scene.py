# src/scenes/minigames/dojo/dojo_minigame_scene.py
"""
DojoMinigameScene — batalha do Dojo.

Regras:
  - 1 pokémon do jogador (sem remover).
  - 5 lutadores Gen 1-2, TODOS nível 40, um por vez.
  - Bag desabilitada.
  - Sem moves SPECIAL (só na cópia da batalha — original fica intacto).
  - Prêmio: Tyrogue Lv. 10 na PC Box (só na 1ª vitória).
  - Respeita day_night_mode e base_weather do JSON.
  - Exibe o diálogo de introdução (events.triggers) do JSON.

PROTEÇÃO CONTRA SAVE CORROMPIDO:
  Enquanto a batalha está em andamento, `player.team` contém CLONES com
  os moves SPECIAL filtrados. Se um auto_save rodar nesse estado, o
  SaveManager serializa os clones e destrói os moves originais pra sempre.
  Por isso:
    1) Interceptamos player.auto_save / player.save_game durante o Dojo.
    2) _end_battle restaura o time ORIGINAL antes de qualquer save.
    3) _finish_arena_battle remove a interceptação e restaura na saída.
"""
import json
import os
import random

import pygame

from src.scenes.arena_scene.arena_battle_scene import ArenaBattleScene
from src.config.paths import PROJECT_ROOT


# =====================================================================
# POOL DE LUTADORES (Gen 1-2)
# =====================================================================
_FIGHTING_POOL = [
    56,   # Mankey
    57,   # Primeape
    66,   # Machop
    67,   # Machoke
    68,   # Machamp
    106,  # Hitmonlee
    107,  # Hitmonchan
    62,   # Poliwrath
    237,  # Hitmontop
    214,  # Heracross
]

_TYROGUE_ID = 236
_TYROGUE_LEVEL = 5
_DOJO_ENEMY_LEVEL = 40


# =====================================================================
# DRAG MANAGER MUDO (bag bloqueada)
# =====================================================================
class _DisabledDragManager:
    is_dragging = False

    def handle_event(self, *a, **k):      return False
    def update(self, *a, **k):            pass
    def render(self, *a, **k):            pass
    def stop_drag(self, *a, **k):         pass
    def cancel_drag(self, *a, **k):       pass
    def start_drag(self, *a, **k):        pass
    def start_drag_placed(self, *a, **k): pass


# =====================================================================
# CENA
# =====================================================================
class DojoMinigameScene(ArenaBattleScene):
    DOJO_TOTAL_ENEMIES = 5

    # -----------------------------------------------------------------
    def __init__(self, game, player_pokemon_data, chapter_id=1,
                 phase_number=1, on_exit=None):
        # ---- Estado do dojo (antes do super) ----
        self._dojo_chapter = int(chapter_id)
        self._dojo_phase = int(phase_number)
        self._current_enemy_index = 0
        self._tyrogue_rewarded = False
        self._tyrogue_obj = None

        # ===== DEFAULTS DE DIA/NOITE E CLIMA =====
        self.day_night_mode = "day"
        self.base_weather = "none"

        # ---- Estado do diálogo de introdução ----
        self.current_dialog = None
        self._intro_event = None

        # ---- Gera inimigos ----
        enemy_data = self._generate_dojo_enemies()

        trainer_data = {
            "name": "Mestre do Dojo",
            "difficulty": "hard",
            "reward_money": 300,
            "reward_xp": 150,
        }

        # ---- ArenaBattleScene cuida do resto ----
        super().__init__(
            game,
            player_team_data=[player_pokemon_data],
            enemy_team_data=enemy_data,
            arena_chapter=self._dojo_chapter,
            arena_level=self._dojo_phase,
            enemy_is_npc=False,
            trainer_data=trainer_data,
            on_exit=on_exit,
        )

        # ---- Bag bloqueada ----
        self.item_bag_renderer = None
        self.item_drag_manager = _DisabledDragManager()

        # ===== PROTEÇÃO CONTRA SAVE CORROMPIDO =====
        self._install_save_guard()

        # ===== EVENTO DE INTRODUÇÃO DO JSON =====
        # Se houver um trigger de tipo "time" com time_value 0.0 contendo
        # um evento "message", exibe o diálogo e bloqueia o placing até
        # o jogador fechar.
        self._intro_event = self._load_intro_event()
        if self._intro_event:
            self._show_intro_dialog()

        print(f"[DOJO] Iniciado. Jogador com "
              f"{len(self._local_team_objs)} pokémon, "
              f"{len(self._enemy_team_objs)} lutadores Lv.{_DOJO_ENEMY_LEVEL}. "
              f"intro_event={'sim' if self._intro_event else 'não'}")

    # =================================================================
    # CARREGAMENTO / EXIBIÇÃO DO EVENTO DE INTRODUÇÃO
    # =================================================================
    def _load_intro_event(self):
        """
        Lê `_phase_data["events"]["triggers"]` e retorna o primeiro
        evento do tipo "message" cujo trigger dispare no início da fase:
          - trigger_type == "start_phase"
          - trigger_type == "time" com time_value <= 0.01
        Retorna o dict do evento ou None.
        """
        if not getattr(self, '_phase_data', None):
            return None

        events_block = self._phase_data.get("events", {}) or {}
        triggers = events_block.get("triggers", []) or []

        for trigger in triggers:
            t_type = (trigger.get("trigger_type") or "").lower()
            time_value = float(trigger.get("time_value", 0.0) or 0.0)

            # Só considera triggers que disparam no início
            if t_type == "time" and time_value > 0.01:
                continue
            if t_type not in ("time", "start_phase"):
                continue

            for ev in (trigger.get("events") or []):
                e_type = (ev.get("event_type") or "").lower()
                if e_type == "message":
                    print(f"[DOJO] Evento de introdução encontrado: "
                          f"speaker='{ev.get('speaker_name', '')}'")
                    return ev

        return None

    def _show_intro_dialog(self):
        """Cria o DialogOverlay de introdução e bloqueia o jogo."""
        from src.scenes.game_scene.components.overlays.dialog_overlay import (
            DialogOverlay,
        )

        ev = self._intro_event

        def on_action():
            # Fechou o diálogo → libera o placing
            self.current_dialog = None
            self.arena_state = "placing"
            # Garante que nenhuma pausa residual continue
            self.paused = False
            self.game_paused = False
            if hasattr(self, 'wave_manager'):
                self.wave_manager.paused = False
            print("[DOJO] Diálogo fechado — iniciando placing.")

        self.current_dialog = DialogOverlay(
            self,
            text=ev.get("message_text", ""),
            speaker=ev.get("speaker_name", ""),
            sprite_path=ev.get("speaker_sprite_path", ""),
            action_label=(ev.get("action_label") or "OK"),
            action_callback=on_action,
        )
        self.current_dialog.active = True

        # Bloqueia o fluxo: intro precede placing/countdown/battle
        self.arena_state = "intro"
        print("[DOJO] Diálogo de introdução exibido.")

    # =================================================================
    # SAVE GUARD
    # =================================================================
    def _install_save_guard(self):
        try:
            self._original_player_auto_save = self.player.auto_save
            self._original_player_save_game = self.player.save_game
            self.player.auto_save = self._dojo_safe_auto_save
            self.player.save_game = self._dojo_safe_save_game
            print("[DOJO] Save guard instalado.")
        except Exception as e:
            print(f"[DOJO] Falha ao instalar save guard: {e}")
            self._original_player_auto_save = None
            self._original_player_save_game = None

    def _uninstall_save_guard(self):
        if getattr(self, '_original_player_auto_save', None) is not None:
            try:
                self.player.auto_save = self._original_player_auto_save
            except Exception:
                pass
            self._original_player_auto_save = None

        if getattr(self, '_original_player_save_game', None) is not None:
            try:
                self.player.save_game = self._original_player_save_game
            except Exception:
                pass
            self._original_player_save_game = None

        print("[DOJO] Save guard removido.")

    def _dojo_safe_auto_save(self, *args, **kwargs):
        if self.arena_state != "finished":
            print("[DOJO] auto_save bloqueado (batalha em andamento).")
            return
        return self._original_player_auto_save(*args, **kwargs)

    def _dojo_safe_save_game(self, *args, **kwargs):
        if self.arena_state != "finished":
            print("[DOJO] save_game bloqueado (batalha em andamento).")
            return False
        return self._original_player_save_game(*args, **kwargs)

    # =================================================================
    # GERAÇÃO DE INIMIGOS — TODOS NÍVEL 40
    # =================================================================
    @staticmethod
    def _generate_dojo_enemies():
        pool = list(_FIGHTING_POOL)
        random.shuffle(pool)
        chosen = pool[:5]

        return [
            {
                "pokemon_id": pid,
                "level": _DOJO_ENEMY_LEVEL,
                "moves": [],
            }
            for pid in chosen
        ]

    # =================================================================
    # MAPA: lê do JSON + spots + dia/noite + clima
    # =================================================================
    def _load_arena_map(self):
        path = os.path.join(
            PROJECT_ROOT, "src", "data", "minigames", "Dojo",
            f"level_{self._dojo_chapter:02d}_{self._dojo_phase:02d}.json"
        )

        if not os.path.exists(path):
            print(f"[DOJO] AVISO: arquivo do dojo não encontrado: {path}")
            return

        try:
            with open(path, "r", encoding="utf-8") as f:
                data = json.load(f)
        except Exception as e:
            print(f"[DOJO] Erro ao ler o JSON: {e}")
            return

        # ===== DIA/NOITE E CLIMA =====
        self.day_night_mode = data.get("day_night_mode", "random") or "random"
        self.base_weather   = data.get("base_weather",   "random") or "random"
        print(f"[DOJO] Dia/Noite='{self.day_night_mode}' | "
              f"Clima='{self.base_weather}'")

        # ---- Coleta spots ----
        tower = data.get("tower_spots", {}) or {}
        spots = list(tower.get("spots", []) or [])

        map_data = data.get("map", {})
        ts = int(map_data.get("tile_size", 24))
        w = int(map_data.get("width", 15)) * ts
        h = int(map_data.get("height", 15)) * ts

        def snap(v):
            return (int(v) // ts) * ts + ts // 2

        if not spots:
            px, py = snap(w * 0.30), snap(h * 0.50)
            ex, ey = snap(w * 0.70), snap(h * 0.50)
            spots = [
                {"x": px, "y": py, "size": ts, "allowed_types": []},
                {"x": ex, "y": ey, "size": ts, "allowed_types": []},
            ]
            print(f"[DOJO] Nenhum spot — auto-gerados P=({px},{py}) "
                  f"E=({ex},{ey})")

        elif len(spots) == 1:
            s = spots[0]
            px = int(s.get("x", snap(w * 0.30)))
            py = int(s.get("y", snap(h * 0.50)))
            ex = snap(w - px - ts)
            ey = snap(py)
            spots.append({"x": ex, "y": ey, "size": ts,
                          "allowed_types": []})
            print(f"[DOJO] Spot JSON: ({px},{py}) | "
                  f"inimigo espelhado: ({ex},{ey})")

        else:
            spots = spots[:2]
            print(f"[DOJO] Usando spots do JSON: {spots}")

        data["tower_spots"] = {
            "spot_size": ts,
            "grid_size": ts,
            "snap_to_grid": True,
            "spots": spots,
        }

        self.map_renderer.load_from_data(data.get("map", {}), PROJECT_ROOT)
        self.path_renderer.load_from_data(data.get("paths", {}))
        self.spot_renderer.load_from_data(data.get("tower_spots", {}))
        self._phase_data = data

        print(f"[DOJO] Mapa carregado: "
              f"{self.map_renderer.get_dimensions()} | "
              f"{len(spots)} spot(s)")

    # =================================================================
    # TIMES
    # =================================================================
    def _setup_teams(self):
        spots = self.spot_renderer.get_spots()
        if not spots:
            print("[DOJO] ERRO: nenhum spot disponível.")
            return

        sorted_spots = sorted(spots, key=lambda s: s.x)
        if len(sorted_spots) >= 2:
            self._player_spots = [sorted_spots[0]]
            self._enemy_spots = [sorted_spots[-1]]
        else:
            self._player_spots = [sorted_spots[0]]
            self._enemy_spots = [sorted_spots[0]]

        self.spot_renderer.spot_manager.spots = self._player_spots

        player_data = self._player_team_data[:1]
        self._local_team_objs = self._build_team(player_data)
        self._enemy_team_objs = self._build_team(self._enemy_team_data)

        for p in self._local_team_objs + self._enemy_team_objs:
            p.charge_cooldown_max = self.PVP_COOLDOWN
            p.attack_cooldown_max = self.PVP_COOLDOWN
            p.attack_range = self.ALLY_ATTACK_RANGE
            self._strip_special_moves(p)

        print(f"[DOJO] Times montados | "
              f"P=({self._player_spots[0].x},{self._player_spots[0].y}) "
              f"E=({self._enemy_spots[0].x},{self._enemy_spots[0].y})")

    @staticmethod
    def _strip_special_moves(poke):
        filtered = [
            m for m in poke.moves
            if getattr(m, 'category', 'physical').lower() != 'special'
        ]

        if not filtered:
            try:
                from src.entities.move import Move
                from src.data.move_data import MoveData
                info = MoveData().get_move_info("tackle")
                if info:
                    filtered = [Move("tackle", info)]
                    print(f"[DOJO] {poke.name} só tinha SPECIAL — "
                          f"recebeu 'tackle'.")
            except Exception as e:
                print(f"[DOJO] Falha ao dar tackle pra {poke.name}: {e}")

        poke.moves = filtered
        if poke.current_move_index >= len(poke.moves):
            poke.current_move_index = 0

    # =================================================================
    # PLACING
    # =================================================================
    def _place_next_enemy_if_needed(self):
        return

    def _on_pokemon_placed(self, placement_data):
        if self.arena_state != "placing":
            return

        action = placement_data.get('action', 'place')
        if action != 'place':
            return

        pokemon = placement_data['pokemon']
        spot = placement_data['spot']
        result = self.placement_manager.add_pokemon(spot, pokemon)
        if result:
            pokemon.set_battle_system(self.battle_system)
            self.battle_system.set_effect_manager_for_pokemon(pokemon)
            pokemon.is_wild = False
            pokemon.game_scene = self
            self._check_placing_complete()

    # =================================================================
    # BATALHA
    # =================================================================
    def _start_battle(self):
        self.arena_state = "battle"
        self._battle_elapsed = 0.0

        for p in self.placement_manager.placed_pokemon:
            if p.is_alive():
                p.combat_state = "attacking"

        self._spawn_next_enemy()
        print("[DOJO] Batalha iniciada!")

    def _spawn_next_enemy(self):
        if self._current_enemy_index >= len(self._enemy_team_objs):
            return
        if not self._enemy_spots:
            print("[DOJO] ERRO: sem enemy spot!")
            return

        poke = self._enemy_team_objs[self._current_enemy_index]
        spot = self._enemy_spots[0]

        poke.full_restore()
        poke.is_defeated = False
        poke.current_hp = poke.max_hp
        poke.is_wild = True

        if poke not in self.wave_manager.active_enemies:
            self.wave_manager.active_enemies.append(poke)

        self._place_pokemon_on_spot(poke, spot, is_player=False)
        poke.combat_state = "attacking"

        self._current_enemy_index += 1
        print(f"[DOJO] Inimigo {self._current_enemy_index}/"
              f"{self.DOJO_TOTAL_ENEMIES}: {poke.name} Lv.{poke.level}")

        try:
            from src.ui.toast_renderer import toast_battle
            toast_battle(
                f"Oponente {self._current_enemy_index}/"
                f"{self.DOJO_TOTAL_ENEMIES}: {poke.name} (Lv.{poke.level})",
                duration=3.5, pokemon=poke, portrait="angry",
            )
        except Exception:
            pass

    def _update_battle(self, dt):
        self._battle_elapsed += dt

        self.wave_manager.update(dt)
        self.placement_manager.update(dt, self.wave_manager.active_enemies)

        for enemy in self.wave_manager.active_enemies:
            if enemy.is_alive() and not enemy.is_defeated:
                enemy.update(dt)
                enemy.update_combat(dt, self.placement_manager.placed_pokemon)

        if self._battle_elapsed > 1.0:
            self._check_spawn_next()
            self._check_dojo_end()

    def _check_spawn_next(self):
        any_alive = any(e.is_alive() and not e.is_defeated
                        for e in self.wave_manager.active_enemies)
        if any_alive:
            return
        if self._current_enemy_index < len(self._enemy_team_objs):
            self._spawn_next_enemy()

    def _check_dojo_end(self):
        local_alive = any(
            p.is_alive() and not p.is_defeated
            for p in self._local_team_objs
        )
        enemy_alive = any(
            e.is_alive() and not e.is_defeated
            for e in self.wave_manager.active_enemies
        )

        all_done = (
            self._current_enemy_index >= len(self._enemy_team_objs)
            and not enemy_alive
        )

        if all_done:
            self._end_battle("win")
        elif not local_alive and self.placement_manager.placed_pokemon:
            self._end_battle("lose")

    # =================================================================
    # ITENS BLOQUEADOS
    # =================================================================
    def _on_item_use(self, target, item_data, target_type):
        return {"consume_item": False, "success": False}

    # =================================================================
    # FIM
    # =================================================================
    def _end_battle(self, result):
        if self.arena_state == "finished":
            return
        self.arena_state = "finished"
        self.arena_result = result

        # Restaura o time original ANTES de salvar
        self._restore_team()

        rewards = {
            "money": 300,
            "xp": 150,
            "trainer_name": "Mestre do Dojo",
        }

        if result == "win":
            self._tyrogue_rewarded = True
            self._give_tyrogue()
            try:
                self.player.money += rewards["money"]
                self.player.score += rewards["xp"]
                self.player.auto_save()
            except Exception as e:
                print(f"[DOJO] Erro ao aplicar recompensas: {e}")

        elif result == "lose":
            try:
                self.player.money = max(0, self.player.money - rewards["money"])
                self.player.score = max(0, self.player.score - rewards["xp"])
                self.player.auto_save()
            except Exception as e:
                print(f"[DOJO] Erro ao aplicar penalidades: {e}")

        print(f"[DOJO] Fim da batalha: {result}")

        from src.scenes.minigames.dojo.dojo_result_overlay import (
            DojoResultOverlay,
        )
        self._arena_overlay = DojoResultOverlay(
            self, result, rewards, self._tyrogue_obj,
        )

    def _give_tyrogue(self):
        """Adiciona o Tyrogue SEMPRE à PC Box do jogador."""
        try:
            from datetime import datetime
            from src.entities.pokemon import Pokemon

            tyrogue = Pokemon(0, 0, _TYROGUE_ID,
                              level=_TYROGUE_LEVEL, is_wild=False)
            tyrogue.capture_date = datetime.now().isoformat()
            tyrogue.capture_method = "dojo_reward"
            tyrogue.is_in_team = False
            tyrogue.is_placed = False

            self.player.add_to_box(tyrogue)
            print("[DOJO] Tyrogue enviado para a PC Box.")

            self.player.caught_pokemon.add(_TYROGUE_ID)
            self.player.register_seen(_TYROGUE_ID)

            self._tyrogue_obj = tyrogue
        except Exception as e:
            print(f"[DOJO] Erro ao entregar Tyrogue: {e}")
            self._tyrogue_obj = None

    # =================================================================
    # SAÍDA
    # =================================================================
    def _finish_arena_battle(self, broadcast=True):
        self._restore_team()
        self._uninstall_save_guard()

        if self._on_exit_callback:
            try:
                self._on_exit_callback()
                return
            except Exception as e:
                print(f"[DOJO] on_exit falhou: {e}")

        try:
            from src.scenes.minigame_select_scene.minigame_select_scene import (
                MinigameSelectScene,
            )
            self.game.current_scene = MinigameSelectScene(self.game)
        except Exception as e:
            print(f"[DOJO] Erro no fallback: {e}")

    # =================================================================
    # HANDLE_EVENT (diálogo de intro tem PRIORIDADE ABSOLUTA)
    # =================================================================
    def handle_event(self, event):
        # Enquanto o diálogo de introdução estiver ativo, ele consome
        # TODOS os eventos (inclusive ESC, pra não abrir pausa).
        if self.current_dialog and self.current_dialog.active:
            self.current_dialog.handle_event(event)
            return None

        # Se um diálogo acabou de ser fechado (active=False mas referência
        # ainda existe), limpa pra liberar o fluxo normal.
        if self.current_dialog and not self.current_dialog.active:
            self.current_dialog = None

        return super().handle_event(event)

    # =================================================================
    # FIXED_UPDATE (bloqueia tudo durante o intro)
    # =================================================================
    def fixed_update(self, dt):
        # 1) Diálogo de introdução ativo → só atualiza ele
        if self.current_dialog and self.current_dialog.active:
            self.current_dialog.update(dt)
            return

        # 2) Intro ainda rolando (sem diálogo, transição)
        if self.arena_state == "intro":
            return

        # 3) Fluxo normal
        return super().fixed_update(dt)

    # =================================================================
    # RENDER (desenha o diálogo por cima de tudo)
    # =================================================================
    def render(self, screen):
        super().render(screen)

        if self.current_dialog and self.current_dialog.active:
            self.current_dialog.render(screen)