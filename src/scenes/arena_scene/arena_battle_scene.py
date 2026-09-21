# src/scenes/arena_scene/arena_battle_scene.py
"""
ArenaBattleScene — cena de batalha PvP/PvE INDEPENDENTE (não herda de GameScene).

Reutiliza:
  - BattleSystem / EffectManager
  - WeatherFilter / DayNightFilter / DayNightWeatherSystem
  - MapRenderer / PokemonSpotRenderer
  - PlacementManager
  - OverlayManager (PauseOverlay)

Adiciona:
  - ItemBagRenderer   (bolsa com itens)
  - GameTeamManager   (HUD inferior do time)
  - MoveQuickSwitchManager (troca de move clicando no slot)
  - ItemDragManager   (arrastar itens)
  - Fase "placing": o jogador posiciona os pokémons antes do countdown.
  - Posicionamento incremental do NPC (arena_ai.ArenaAI controla itens;
    o posicionamento 1:1 fica aqui, na cena).
"""
import json
import math
import os

import pygame

from src.scenes.base_scene import BaseScene
from src.entities.pokemon import Pokemon
from src.battle.effects import StatusType
from src.network.protocol import create_message
from src.data.arena_catalog import (
    get_arena_path, split_spots_for_teams,
)
from src.managers.sounds.sound_manager import sound_manager, SoundEffect

# IA do NPC modularizada — só cuida de itens/curas.
from src.scenes.arena_scene.arena_ai import ArenaAI


# =====================================================================
# WAVE MANAGER SHIM
# =====================================================================
class _ArenaWaveManagerShim:
    """A arena não tem waves — shim pra enganar sistemas que esperam um.

    Inimigos só entram em `active_enemies` depois que forem posicionados
    (placement incremental do NPC — o oponente responde 1:1 ao jogador).
    """
    def __init__(self, scene, enemy_pokemons):
        self.scene = scene
        # Todos os inimigos conhecidos (fonte de verdade do time).
        self._all_enemies = [p for p in enemy_pokemons if p]
        # Só entram aqui quando forem posicionados.
        self.active_enemies = []
        self.paused = False
        self.spawner = self
        self.current_wave_idx = {0: 0}
        self.waves = {0: {"enemies": []}}
        self.wave_active = {0: True}
        self.spawned_count = {0: 0}
        self.waves_ended = []
        self.total_gold_earned = 0
        self.total_enemies_defeated = 0

    def set_paths(self, p): pass
    def set_target_items(self, i): pass
    def initialize_condition(self): pass
    def reset_gold(self): self.total_gold_earned = 0
    def get_total_gold_earned(self): return self.total_gold_earned
    def is_next_wave_boss(self): return False
    def has_more_waves(self): return False
    def has_active_waves(self): return False
    def is_wave_completed(self, i): return self.is_wave_completely_finished()
    def is_boss_defeated(self): return self.is_wave_completely_finished()
    def is_boss_spawned(self): return True
    def set_condition(self, c): pass
    def set_paused(self, p): self.paused = bool(p)
    def get_spawn_countdown(self): return 0.0

    def update(self, dt):
        self.active_enemies = [e for e in self.active_enemies
                                if e.is_alive() and not e.is_defeated]
        return []

    def is_wave_completely_finished(self):
        return not self.active_enemies

    def get_current_wave_info(self):
        alive = len([e for e in self.active_enemies if e.is_alive()])
        return {
            "name": "ARENA", "index": "ARENA", "total": 1,
            "enemies_remaining": alive,
            "enemies_spawned": alive,
            "enemies_total": max(1, alive),
            "progress": 1.0 if alive == 0 else 0.0,
            "active_paths": 0,
        }

    def remove_enemy(self, enemy):
        if enemy in self.active_enemies:
            self.active_enemies.remove(enemy)
            self.total_enemies_defeated += 1


# =====================================================================
# CENA PRINCIPAL
# =====================================================================
class ArenaBattleScene(BaseScene):
    COUNTDOWN_TIME = 5.0
    PVP_COOLDOWN = 1.5
    ALLY_ATTACK_RANGE = 420

    def __init__(self, game, player_team_data=None, enemy_team_data=None,
                 arena_chapter=1, arena_level=1,
                 enemy_is_npc=True, trainer_data=None,
                 is_host=True, network=None, on_exit=None):
        super().__init__(game)

        # ----- DADOS DE ENTRADA -----
        self._arena_chapter = int(arena_chapter)
        self._arena_level = int(arena_level)
        self._enemy_is_npc = bool(enemy_is_npc)
        self._trainer_data = trainer_data or {}
        self._is_host = is_host
        self._network = network
        self._on_exit_callback = on_exit

        self._player_team_data = list(player_team_data or [])
        self._enemy_team_data = list(enemy_team_data or [])

        # ----- REFERÊNCIAS BÁSICAS -----
        self.player = game.player
        self.screen_manager = game.screen_manager

        # ----- ESTADO -----
        self.game_state = "in_wave"
        self.arena_state = "placing"  # placing | countdown | battle | finished
        self.arena_result = None
        self.arena_countdown = self.COUNTDOWN_TIME
        self.paused = False
        self.game_paused = False
        self.ui_hidden = False
        self._arena_overlay = None
        self._ai = None
        self._local_team_objs = []
        self._enemy_team_objs = []
        self._player_spots = []
        self._enemy_spots = []
        self._last_dt = 0.0
        self._battle_elapsed = 0.0
        self.move_select_overlay = None
        self.dragging_camera = False
        self.last_mouse_pos = None

        # ----- PLACEMENT INCREMENTAL DO NPC -----
        self._enemy_placed_count = 0
        self._enemy_place_feedback_timer = 0.0

        # ----- IMPORTS LOCAIS -----
        from src.battle.battle_system import BattleSystem
        from src.scenes.game_scene.components.renderer.map_renderer import MapRenderer
        from src.scenes.game_scene.components.renderer.path_renderer import PathRenderer
        from src.scenes.game_scene.components.renderer.pokemon_spot_renderer import PokemonSpotRenderer
        from src.scenes.game_scene.components.managers.placement_manager import PlacementManager
        from src.scenes.game_scene.components.managers.overlay_manager import OverlayManager
        from src.scenes.game_scene.components.managers.team_manager import GameTeamManager
        from src.scenes.game_scene.components.managers.move_quick_switch_manager import MoveQuickSwitchManager
        from src.scenes.game_scene.components.managers.item_drag_manager import ItemDragManager
        from src.scenes.game_scene.components.renderer.item_bag_renderer import ItemBagRenderer
        from src.battle.effects.specific.weather.weather_filter import WeatherFilter
        from src.battle.effects.specific.day_night.day_night_filter import DayNightFilter
        from src.scenes.game_scene.components.day_night_weather_system import DayNightWeatherSystem

        # ----- COMPONENTES -----
        self.map_renderer = MapRenderer()
        self.path_renderer = PathRenderer()
        self.spot_renderer = PokemonSpotRenderer()
        self.weather_filter = WeatherFilter()
        self.day_night_filter = DayNightFilter()

        # ----- MAPA -----
        self._load_arena_map()

        # ----- DIMENSÕES -----
        self._setup_world_dimensions()

        # ----- CÂMERA -----
        self.game.initialize_camera(self.world_width, self.world_height)
        self.camera = self.game.camera
        self.camera.set_limits(-500, self.world_width + 500,
                               -500, self.world_height + 500)
        self.camera.x = self.world_width / 2
        self.camera.y = self.world_height / 2

        # ----- BATTLE SYSTEM -----
        self.battle_system = BattleSystem(self)
        self.effect_manager = self.battle_system.effect_manager

        # ----- CLIMA / DIA-NOITE -----
        self.day_night_weather = DayNightWeatherSystem(self)
        self.day_night_weather.initialize()

        # ----- OVERLAY MANAGER -----
        self.overlay_manager = OverlayManager(self)

        # ----- PLACEMENT MANAGER -----
        self.placement_manager = PlacementManager(self)

        # ----- MONTA OS TIMES -----
        self._setup_teams()

        # ----- SWAP DE TIME (pro HUD mostrar a seleção da arena) -----
        self._original_team = list(game.player.team)
        game.player.team = self._local_team_objs
        for p in self._local_team_objs:
            p.full_restore()
            p.is_in_team = True
        print(f"[ARENA] Time do HUD trocado ({len(self._local_team_objs)} pokémon)")

        # ----- WAVE SHIM -----
        self.wave_manager = _ArenaWaveManagerShim(self, self._enemy_team_objs)

        # ----- HUD: TEAM MANAGER -----
        self.team_manager = GameTeamManager(self.game, self)
        self.move_quick_switch_manager = MoveQuickSwitchManager(self)

        # ----- ITENS: BAG + DRAG -----
        self.item_bag_renderer = ItemBagRenderer(self.game, self.player.bag)
        self.item_drag_manager = ItemDragManager(self.game, self.player.bag)

        # Aplica config da bolsa salva
        try:
            self.player.apply_bag_ui_config(self.item_bag_renderer)
        except Exception:
            pass

        # ----- IA (modularizada em arena_ai.ArenaAI) -----
        if self._enemy_is_npc:
            difficulty = self._trainer_data.get("difficulty", "normal")
            self._ai = ArenaAI(self, self._enemy_team_objs, difficulty)

        # ----- REDE -----
        if self._network:
            self._network.current_scene_callback = self._on_arena_network_message

        # ----- CONFIGURA BATTLE SYSTEM NOS POKÉMONS -----
        # (não posiciona inimigos ainda — eles entram 1:1 com o jogador)
        for p in self._local_team_objs + self._enemy_team_objs:
            p.screen_manager = self.screen_manager
            p.camera = self.camera
            p.game_scene = self
            p.set_battle_system(self.battle_system)
            self.battle_system.set_effect_manager_for_pokemon(p)

            # ===== ARENA: não volta pro spot após atacar =====
            # Faz o pokémon aliado se comportar como selvagem em combate:
            # permanece no local e busca o próximo alvo, em vez de andar
            # até o spot e voltar (o que dava vantagem a atacantes ranged).
            p._arena_no_return = True

        print(f"[ARENA] Iniciada cap={self._arena_chapter} "
              f"lvl={self._arena_level} | player={len(self._local_team_objs)} | "
              f"enemy={len(self._enemy_team_objs)} | npc={self._enemy_is_npc} "
              f"| player_spots={len(self._player_spots)} "
              f"(placement incremental do NPC ativo)")

    # ==================================================================
    # MAPA / DIMENSÕES
    # ==================================================================
    def _load_arena_map(self):
        arena_path = get_arena_path(self._arena_chapter, self._arena_level)
        if not os.path.exists(arena_path):
            print(f"[ARENA] AVISO: mapa não encontrado: {arena_path}")
            return

        print(f"[ARENA] Carregando mapa: {arena_path}")
        try:
            with open(arena_path, "r", encoding="utf-8") as f:
                data = json.load(f)
        except Exception as e:
            print(f"[ARENA] Erro ao ler mapa: {e}")
            return

        from src.config.paths import PROJECT_ROOT
        self.map_renderer.load_from_data(data.get("map", {}), PROJECT_ROOT)
        self.path_renderer.load_from_data(data.get("paths", {}))
        self.spot_renderer.load_from_data(data.get("tower_spots", {}))
        self._phase_data = data

    def _setup_world_dimensions(self):
        w, h = self.map_renderer.get_dimensions()
        self.world_width = w if w > 0 else 2000
        self.world_height = h if h > 0 else 2000

    # ==================================================================
    # TIMES / PLACEMENT
    # ==================================================================
    def _setup_teams(self):
        spots = self.spot_renderer.get_spots()
        spots_raw = [
            {"x": s.x, "y": s.y, "size": getattr(s, "size", 24),
             "allowed_types": getattr(s, "allowed_types", [])}
            for s in spots
        ]
        player_spots_raw, enemy_spots_raw = split_spots_for_teams(spots_raw)

        by_xy = {(s.x, s.y): s for s in spots}
        self._player_spots = [by_xy[(d["x"], d["y"])] for d in player_spots_raw
                              if (d["x"], d["y"]) in by_xy]
        self._enemy_spots = [by_xy[(d["x"], d["y"])] for d in enemy_spots_raw
                             if (d["x"], d["y"]) in by_xy]

        # Renderer só mostra os spots do jogador
        self.spot_renderer.spot_manager.spots = self._player_spots

        # Limita o time ao número de spots
        max_players = len(self._player_spots)
        max_enemies = len(self._enemy_spots)

        player_data = self._player_team_data[:max_players]
        enemy_data = self._enemy_team_data[:max_enemies]

        self._local_team_objs = self._build_team(player_data)
        self._enemy_team_objs = self._build_team(enemy_data)

        for p in self._local_team_objs + self._enemy_team_objs:
            p.charge_cooldown_max = self.PVP_COOLDOWN
            p.attack_cooldown_max = self.PVP_COOLDOWN
            p.attack_range = self.ALLY_ATTACK_RANGE

    def _build_team(self, data_list):
        out = []
        for entry in data_list:
            pk = None

            if isinstance(entry, Pokemon):
                pk = entry
            elif isinstance(entry, dict):
                # Trainer catalog: {"pokemon_id": ..., "level": ..., "moves": [...]}
                if "pokemon_id" in entry and "id" not in entry:
                    pk = self._build_pokemon_from_trainer_entry(entry)
                else:
                    try:
                        pk = Pokemon.from_dict(entry)
                    except Exception as e:
                        print(f"[ARENA] Erro from_dict: {e}")
                        continue

            if pk is None:
                continue

            pk.is_wild = False
            pk.is_in_team = False
            pk.is_placed = False
            pk.game_scene = self
            pk.combat_state = "idle"

            # ===== ARENA: não volta pro spot após atacar =====
            # Setado aqui para cobrir pokémons criados via from_dict
            # (o loop do __init__ reaplica, mas isto garante que qualquer
            #  pokémon criado depois também tenha o flag).
            pk._arena_no_return = True

            out.append(pk)

        print(f"[ARENA] _build_team: {len(out)} pokémon(s) de {len(data_list)} entrada(s)")
        return out

    def _build_pokemon_from_trainer_entry(self, entry):
        """Entrada do trainer_catalog → Pokemon."""
        from src.entities.move import Move
        from src.data.move_data import MoveData

        try:
            pk = Pokemon(
                x=0, y=0,
                pokemon_id=entry["pokemon_id"],
                level=entry.get("level", 5),
                is_wild=False,
                shiny=entry.get("is_shiny", False),
                is_boss=False,
            )
        except Exception as e:
            print(f"[ARENA] Erro ao criar Pokemon({entry.get('pokemon_id')}): {e}")
            return None

        move_names = entry.get("moves", []) or []
        if move_names:
            move_data = MoveData()
            new_moves = []
            for name in move_names:
                info = move_data.get_move_info(name)
                if info:
                    new_moves.append(Move(name, info))
                else:
                    print(f"[ARENA] Move desconhecido em '{entry.get('pokemon_id')}': {name}")
            if new_moves:
                pk.moves = new_moves
                pk.current_move_index = 0

        # ===== ARENA: não volta pro spot após atacar =====
        pk._arena_no_return = True

        return pk

    def _place_next_enemy_if_needed(self):
        """
        Coloca inimigos UM POR VEZ, sempre que o jogador posiciona um.
        Assim o NPC não 'revela' o time antes do jogador decidir onde colocar.
        """
        if self.arena_state != "placing":
            return

        player_count = len(self.placement_manager.placed_pokemon)
        placed_any = False

        while (self._enemy_placed_count < player_count
               and self._enemy_placed_count < len(self._enemy_team_objs)
               and self._enemy_placed_count < len(self._enemy_spots)):
            idx = self._enemy_placed_count
            poke = self._enemy_team_objs[idx]
            spot = self._enemy_spots[idx]

            poke.is_wild = True
            if poke not in self.wave_manager.active_enemies:
                self.wave_manager.active_enemies.append(poke)

            self._place_pokemon_on_spot(poke, spot, is_player=False)
            self._enemy_placed_count += 1
            placed_any = True

        if placed_any:
            self._enemy_place_feedback_timer = 1.8
            try:
                sound_manager.play_effect(SoundEffect.CLICK, volume=0.15)
            except Exception:
                pass

    def _place_pokemon_on_spot(self, poke, spot, is_player):
        """Coloca um pokémon num spot (usado para o inimigo e para o callback do drag)."""
        ts = self.placement_manager.tile_size
        cx = (spot.x // ts) * ts + ts // 2
        cy = (spot.y // ts) * ts + ts // 2

        poke.x, poke.y = cx, cy
        poke.original_spot_x = cx
        poke.original_spot_y = cy
        poke.placed_tile_x = cx // ts
        poke.placed_tile_y = cy // ts
        poke.is_placed = True
        poke.attack_range = self.ALLY_ATTACK_RANGE
        poke.combat_state = "attacking"
        poke.screen_manager = self.screen_manager
        poke.camera = self.camera
        poke.game_scene = self

        if is_player:
            if poke not in self.placement_manager.placed_pokemon:
                self.placement_manager.placed_pokemon.append(poke)
        spot.occupied = True
        tag = "PLAYER" if is_player else "ENEMY"
        print(f"[ARENA] {tag} {poke.name} em ({cx},{cy})")

    # ==================================================================
    # CALLBACKS DE INTERAÇÃO (pro team_manager / drag_manager)
    # ==================================================================
    def _on_pokemon_placed(self, placement_data):
        """Chamado quando o jogador solta um pokémon num spot."""
        if self.arena_state != "placing":
            return

        action = placement_data.get('action', 'place')

        if action == 'place':
            pokemon = placement_data['pokemon']
            spot = placement_data['spot']
            result = self.placement_manager.add_pokemon(spot, pokemon)
            if result:
                # Reafirma o battle system
                pokemon.set_battle_system(self.battle_system)
                self.battle_system.set_effect_manager_for_pokemon(pokemon)
                pokemon.is_wild = False
                pokemon.game_scene = self

                # NPC posiciona em seguida (1:1 com o jogador).
                # Precisa vir ANTES do _check_placing_complete pra que,
                # se o jogador completou o time, o inimigo ainda seja
                # posicionado no mesmo "turno".
                self._place_next_enemy_if_needed()

                # Só agora checa se todos posicionaram (pode virar countdown)
                self._check_placing_complete()

        elif action == 'move':
            pokemon = placement_data['pokemon']
            from_spot = placement_data.get('from_spot')
            to_spot = placement_data['to_spot']
            self._move_pokemon_to_spot(pokemon, from_spot, to_spot)

    def _move_pokemon_to_spot(self, pokemon, from_spot, to_spot):
        if from_spot:
            from_spot.occupied = False

        ts = self.placement_manager.tile_size
        cx = (to_spot.x // ts) * ts + ts // 2
        cy = (to_spot.y // ts) * ts + ts // 2

        pokemon.x = cx
        pokemon.y = cy
        pokemon.original_spot_x = cx
        pokemon.original_spot_y = cy
        pokemon.placed_tile_x = cx // ts
        pokemon.placed_tile_y = cy // ts
        to_spot.occupied = True

    def _on_item_use(self, target, item_data, target_type):
        """Callback do item_drag_manager."""
        effect = item_data.get("effect", "")
        category = item_data.get("category", "")

        if target_type == "ally":
            # Medicina
            if category == "medicine":
                if not target.is_alive():
                    if effect == "revive":
                        pct = item_data.get("effect_value", 0.5)
                        target.revive(heal_percentage=pct)
                        return {"consume_item": True, "success": True}
                    return {"consume_item": False, "success": False}

                heal_amount = item_data.get("effect_value", 0)
                if heal_amount == -1:
                    target.heal()
                    return {"consume_item": True, "success": True}
                elif heal_amount > 0:
                    old_hp = target.current_hp
                    target.current_hp = min(target.max_hp, target.current_hp + heal_amount)
                    if target.current_hp > old_hp:
                        return {"consume_item": True, "success": True}
                    return {"consume_item": False, "success": False}

            # Cura status específico
            elif effect == "cure_status":
                status_to_cure = item_data.get("effect_value")
                status_map = {
                    "paralysis": StatusType.PARALYSIS,
                    "sleep": StatusType.SLEEP,
                    "poison": StatusType.POISON,
                    "burn": StatusType.BURN,
                    "freeze": StatusType.FREEZE,
                }
                status_type = status_map.get(status_to_cure)
                if status_type:
                    current = self.effect_manager.get_status(target)
                    if current and current.type == status_type:
                        self.effect_manager.remove_status(target)
                        return {"consume_item": True, "success": True}
                    return {"consume_item": False, "success": False}

            # Full Heal
            elif effect == "cure_all_status":
                current = self.effect_manager.get_status(target)
                if current and current.type != StatusType.NONE:
                    self.effect_manager.remove_status(target)
                    return {"consume_item": True, "success": True}
                return {"consume_item": False, "success": False}

            # PP restore
            elif effect == "pp_restore":
                if hasattr(target, 'restore_pp'):
                    pct = item_data.get("effect_value", 1.0)
                    restored = target.restore_pp(percentage=pct)
                    if restored > 0:
                        return {"consume_item": True, "success": True}
                return {"consume_item": False, "success": False}

            # Battle item (X-Items)
            elif effect == "battle_stat_boost":
                from src.battle.effects.stat_modifier import StatType
                from src.scenes.game_scene.components.managers.overlay_manager import OverlayType
                effect_value = item_data.get("effect_value", {})
                stat_key = effect_value.get("stat")
                stages = effect_value.get("stages", 1)
                duration = effect_value.get("duration", 15.0)
                stat_map = {
                    "attack": StatType.ATTACK, "defense": StatType.DEFENSE,
                    "sp_attack": StatType.SP_ATTACK, "sp_defense": StatType.SP_DEFENSE,
                    "speed": StatType.SPEED, "accuracy": StatType.ACCURACY,
                    "evasion": StatType.EVASION,
                }
                stat_type = stat_map.get(stat_key)
                if stat_type:
                    self.effect_manager.add_stat_modifier(
                        target, stat_type, stages, duration, is_battle_item=True)
                    self.effect_manager.set_battle_item_buff(target, stat_type, duration)
                    return {"consume_item": True, "success": True}
                return {"consume_item": False, "success": False}

        # Pokébola em inimigo (não faz sentido na arena)
        if target_type == "enemy" and category == "pokeball":
            return {"consume_item": False, "success": False}

        return {"consume_item": False, "success": False}

    # ==================================================================
    # MOVE SELECT OVERLAY (chamado pelo team_manager)
    # ==================================================================
    def open_move_select_overlay(self, pokemon):
        if not pokemon or not pokemon.moves:
            return
        from src.scenes.game_scene.components.overlays.move_select_overlay import MoveSelectOverlay
        self.move_select_overlay = MoveSelectOverlay(self, pokemon)
        self.move_select_overlay.active = True
        self.game_paused = True
        self.paused = True
        if hasattr(self, 'wave_manager'):
            self.wave_manager.paused = True

    def close_move_select_overlay(self):
        if self.move_select_overlay:
            self.move_select_overlay.active = False
            self.move_select_overlay = None
        self.game_paused = False
        self.paused = False
        if hasattr(self, 'wave_manager'):
            self.wave_manager.paused = False

    # Stubs de overlay de evolução (arena não suporta)
    def open_evolution_overlay(self, pokemon, evolution_data):
        print(f"[ARENA] Evolução suprimida na arena: {pokemon.name}")

    # ==================================================================
    # PLACING
    # ==================================================================
    def _check_placing_complete(self):
        if self.arena_state != "placing":
            return
        required = len(self._local_team_objs)
        placed = len(self.placement_manager.placed_pokemon)
        if required > 0 and placed >= required:
            print(f"[ARENA] Todos os {placed} pokémons posicionados! "
                  f"Countdown iniciando...")
            self.arena_state = "countdown"
            self.arena_countdown = self.COUNTDOWN_TIME

    # ==================================================================
    # PAUSA
    # ==================================================================
    def toggle_pause(self):
        from src.scenes.game_scene.components.managers.overlay_manager import OverlayType
        if self.paused:
            self.paused = False
            self.game_paused = False
            if hasattr(self, 'wave_manager'):
                self.wave_manager.paused = False
            self.overlay_manager.hide()
        else:
            self.paused = True
            self.game_paused = True
            if hasattr(self, 'wave_manager'):
                self.wave_manager.paused = True
            self.overlay_manager.show(OverlayType.PAUSE)

    def handle_give_up(self):
        print("[ARENA] Jogador desistiu")
        self.paused = False
        self.game_paused = False
        if hasattr(self, 'wave_manager'):
            self.wave_manager.paused = False
        self._end_battle("lose")

    # ==================================================================
    # EVENTOS
    # ==================================================================
    def handle_event(self, event):
        # --- Overlays prioritários ---
        if self.move_select_overlay and self.move_select_overlay.active:
            self.move_select_overlay.handle_event(event)
            return None

        if self.overlay_manager.is_active:
            if self.overlay_manager.handle_event(event):
                return None
            return None

        if self._arena_overlay and self._arena_overlay.active:
            if self._arena_overlay.handle_event(event):
                return None
            return None

        # --- Resize ---
        if event.type == pygame.VIDEORESIZE:
            return None

        # --- Teclado ---
        if event.type == pygame.KEYDOWN:
            if event.key == pygame.K_h:
                self.ui_hidden = not self.ui_hidden
                return None
            if event.key in (pygame.K_ESCAPE, pygame.K_p):
                self.toggle_pause()
                return None
            if event.key == pygame.K_TAB:
                if hasattr(self.player, 'bag'):
                    self.player.bag.cycle_category()
                return None

        # --- Quick switch de moves (dropdown) ---
        if self.move_quick_switch_manager.handle_event(
                event, self.camera, self.screen_manager):
            return None

        # --- Drag de itens ---
        if self.item_drag_manager.is_dragging:
            if event.type == pygame.MOUSEMOTION:
                world_pos = self.screen_manager.get_mouse_world_position(event.pos, self.camera)
                if world_pos:
                    self.item_drag_manager.update_drag(
                        event.pos, world_pos,
                        self.placement_manager.placed_pokemon,
                        self.wave_manager.active_enemies,
                        self.camera,
                    )
                return None
            elif event.type == pygame.MOUSEBUTTONUP and event.button == 1:
                self.item_drag_manager.stop_drag(self._on_item_use)
                return None
            elif event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE:
                self.item_drag_manager.cancel_drag()
                return None

        # --- Item bag ---
        if self.item_bag_renderer and self.item_bag_renderer.handle_event(event):
            return None

        # --- Team manager (drag de pokémons) ---
        if self.team_manager:
            result = self.team_manager.handle_event(
                event,
                self.spot_renderer.get_spots(),
                self.camera,
                self._on_pokemon_placed,
                None,
                None,
            )
            if result:
                return None

        # --- Clique em pokémon colocado (abre move select) ---
        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            mouse_pos = pygame.mouse.get_pos()
            if not self.item_drag_manager.is_dragging and not self.team_manager.is_dragging():
                if self.screen_manager.is_mouse_in_viewport(mouse_pos):
                    world_pos = self.screen_manager.get_mouse_world_position(mouse_pos, self.camera)
                    if world_pos:
                        clicked = self.placement_manager.get_pokemon_at_world_pos(
                            world_pos[0], world_pos[1], tolerance=30)
                        if clicked and clicked.moves:
                            self.open_move_select_overlay(clicked)
                            return None

        # --- Zoom ---
        if event.type == pygame.MOUSEWHEEL:
            mouse_pos = pygame.mouse.get_pos()
            if self.screen_manager.is_mouse_in_viewport(mouse_pos):
                if self.item_bag_renderer and getattr(self.item_bag_renderer, 'mouse_over_ui', False):
                    return None
                self.camera.handle_zoom(event.y > 0)
                return None

        # --- Botão direito: remover pokémon (só durante placing) ---
        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 3:
            if self.arena_state == "placing":
                mouse_pos = pygame.mouse.get_pos()
                if self.screen_manager.is_mouse_in_viewport(mouse_pos):
                    world_pos = self.screen_manager.get_mouse_world_position(mouse_pos, self.camera)
                    if world_pos:
                        self.placement_manager.remove_pokemon_by_right_click(
                            world_pos[0], world_pos[1])
                        return None

        # --- Câmera (botão do meio) ---
        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 2:
            mouse_pos = pygame.mouse.get_pos()
            if self.screen_manager.is_mouse_in_viewport(mouse_pos):
                self.dragging_camera = True
                self.last_mouse_pos = mouse_pos
                pygame.mouse.set_cursor(pygame.SYSTEM_CURSOR_SIZEALL)
                return None

        if event.type == pygame.MOUSEBUTTONUP and event.button == 2:
            if self.dragging_camera:
                self.dragging_camera = False
                self.last_mouse_pos = None
                pygame.mouse.set_cursor(pygame.SYSTEM_CURSOR_ARROW)
                return None

        if event.type == pygame.MOUSEMOTION and self.dragging_camera:
            if self.last_mouse_pos:
                dx = event.pos[0] - self.last_mouse_pos[0]
                dy = event.pos[1] - self.last_mouse_pos[1]
                self.camera.x -= dx / self.camera.zoom
                self.camera.y -= dy / self.camera.zoom
                self.camera._clamp_position()
                self.last_mouse_pos = event.pos
                return None

        return None

    # ==================================================================
    # UPDATE
    # ==================================================================
    def fixed_update(self, dt):
        self._last_dt = dt
        self._process_network_queue()

        # --- Overlay de move select ---
        if self.move_select_overlay and self.move_select_overlay.active:
            self.move_select_overlay.update(dt)
            return

        # --- Overlay de resultado ---
        if self._arena_overlay and self._arena_overlay.active:
            self._arena_overlay.update(dt)
            return

        # --- Overlay manager ---
        if self.overlay_manager.is_active:
            self.overlay_manager.update(dt)
            return

        # --- Pausa ---
        if self.game_paused or self.paused:
            return

        # --- Battle system + efeitos ---
        if hasattr(self, 'battle_system'):
            self.battle_system.update(dt)

        # --- Clima / dia-noite ---
        if hasattr(self, 'day_night_weather'):
            self.day_night_weather.update(dt)

        # --- HUD ---
        if self.item_bag_renderer:
            self.item_bag_renderer.update(dt)
        if self.team_manager:
            self.team_manager.update(dt)
        if self.move_quick_switch_manager:
            self.move_quick_switch_manager.update(dt)

        # --- Máquina de estados ---
        if self.arena_state == "placing":
            self._update_placing(dt)
        elif self.arena_state == "countdown":
            self._update_countdown(dt)
        elif self.arena_state == "battle":
            self._update_battle(dt)

        # --- EffectManager ---
        if hasattr(self, 'battle_system') and self.battle_system:
            self.battle_system.effect_manager.update(dt)

    def _update_placing(self, dt):
        """Fase de posicionamento — pokémons só animam."""
        if self._enemy_place_feedback_timer > 0:
            self._enemy_place_feedback_timer = max(
                0.0, self._enemy_place_feedback_timer - dt)

        for p in self.placement_manager.placed_pokemon:
            p.update(dt)
        for e in self.wave_manager.active_enemies:
            e.update(dt)

    def _update_countdown(self, dt):
        """Contagem regressiva — pokémons ainda não lutam."""
        if self._enemy_place_feedback_timer > 0:
            self._enemy_place_feedback_timer = max(
                0.0, self._enemy_place_feedback_timer - dt)

        for p in self.placement_manager.placed_pokemon:
            p.update(dt)
        for e in self.wave_manager.active_enemies:
            e.update(dt)

        self.arena_countdown -= dt
        if self.arena_countdown <= 0:
            self.arena_countdown = 0
            self._start_battle()

    def _start_battle(self):
        self.arena_state = "battle"
        self._battle_elapsed = 0.0
        for p in self.placement_manager.placed_pokemon:
            if p.is_alive():
                p.combat_state = "attacking"
        for e in self.wave_manager.active_enemies:
            if e.is_alive():
                e.combat_state = "attacking"
        print("[ARENA] Batalha iniciada!")

    def _update_battle(self, dt):
        self._battle_elapsed += dt

        if self._ai:
            self._ai.update(dt)

        self.wave_manager.update(dt)

        # Aliados
        self.placement_manager.update(dt, self.wave_manager.active_enemies)

        # Inimigos
        for enemy in self.wave_manager.active_enemies:
            if enemy.is_alive() and not enemy.is_defeated:
                enemy.update(dt)
                enemy.update_combat(dt, self.placement_manager.placed_pokemon)

        # Só checa fim depois de 1s de batalha (evita race no primeiro frame)
        if self._battle_elapsed > 1.0:
            self._check_battle_end()

    def _check_battle_end(self):
        local_alive = any(p.is_alive() and not p.is_defeated
                          for p in self.placement_manager.placed_pokemon)

        # Só considera inimigos que foram DE FATO posicionados.
        enemy_alive = any(p.is_alive() and not p.is_defeated
                          for p in self.wave_manager.active_enemies)

        # Vitória: houve pelo menos 1 inimigo posicionado e nenhum sobrou vivo.
        if self._enemy_placed_count > 0 and not enemy_alive:
            self._end_battle("win")
        elif not local_alive and self.placement_manager.placed_pokemon:
            self._end_battle("lose")

    def _end_battle(self, result):
        if self.arena_state == "finished":
            return
        self.arena_state = "finished"
        self.arena_result = result

        # Recompensas SEMPRE calculadas (usadas tanto pra ganhar quanto pra perder).
        rewards = {}
        if self._trainer_data:
            rewards = {
                "money": self._trainer_data.get("reward_money", 0),
                "xp": self._trainer_data.get("reward_xp", 0),
                "trainer_name": self._trainer_data.get("name", "oponente"),
            }

        if result == "win" and rewards:
            # ---- Ganha o que o treinador oferece ----
            try:
                self.player.money += rewards["money"]
                self.player.score += rewards["xp"]
            except Exception:
                pass
            for p in self._local_team_objs:
                if p.is_alive():
                    try:
                        p.gain_xp(rewards["xp"] // 3)
                    except Exception:
                        pass
            try:
                self.player.auto_save()
            except Exception:
                pass

        elif result == "lose" and rewards:
            # ---- Perde EXATAMENTE o que ganharia ----
            loss_money = rewards.get("money", 0)
            loss_xp = rewards.get("xp", 0)

            # Clamp em 0 pra não ficar negativo
            try:
                self.player.money = max(0, self.player.money - loss_money)
            except Exception:
                pass
            try:
                self.player.score = max(0, self.player.score - loss_xp)
            except Exception:
                pass

            try:
                self.player.auto_save()
            except Exception:
                pass

        print(f"[ARENA] Fim da batalha: {result} | rewards={rewards}")

        from src.scenes.arena_scene.arena_result_overlay import ArenaResultOverlay
        self._arena_overlay = ArenaResultOverlay(self, result, rewards)

    # ==================================================================
    # SAÍDA
    # ==================================================================
    def _restore_team(self):
        if getattr(self, '_original_team', None) is not None:
            self.game.player.team = self._original_team
            self._original_team = None
            print("[ARENA] Time original restaurado")

    def _finish_arena_battle(self, broadcast=True):
        self._restore_team()

        if self._network and broadcast:
            try:
                self._network.send_to_all(create_message(
                    "ARENA_LEAVE", {"name": self._network.my_name}))
            except Exception:
                pass

        if self._on_exit_callback:
            try:
                self._on_exit_callback()
                return
            except Exception as e:
                print(f"[ARENA] Callback de saída falhou: {e}")

        try:
            from src.scenes.npc_hall_scene.npc_hall_scene import NpcHallScene
            self.game.current_scene = NpcHallScene(self.game)
        except Exception as e:
            print(f"[ARENA] Erro ao voltar pro hall: {e}")

    # ==================================================================
    # REDE
    # ==================================================================
    def _on_arena_network_message(self, msg, conn=None):
        t = msg.get("type")
        if t in ("ARENA_LEAVE", "DISCONNECT"):
            self._finish_arena_battle(broadcast=False)

    def _process_network_queue(self):
        net = self._network
        if not net or not hasattr(net, 'incoming_queue'):
            return
        try:
            while not net.incoming_queue.empty():
                item = net.incoming_queue.get_nowait()
                if isinstance(item, tuple) and len(item) == 2:
                    msg, _ = item
                else:
                    msg = item
                self._on_arena_network_message(msg, None)
                if self.game.current_scene is not self:
                    break
        except Exception as e:
            print(f"[ARENA] Erro na fila: {e}")

    # ==================================================================
    # RENDER
    # ==================================================================
    def render(self, screen):
        if not self.active:
            return

        sm = self.scene.screen_manager
        vx, vy = sm.viewport_x, sm.viewport_y
        vw, vh = sm.viewport_width, sm.viewport_height

        overlay = pygame.Surface((vw, vh), pygame.SRCALPHA)
        overlay.fill((0, 0, 0, min(210, self.alpha)))
        screen.blit(overlay, (vx, vy))

        win = (self.result == "win")
        accent = (255, 215, 0) if win else (230, 90, 90)
        accent_dim = (128, 90, 20) if win else (128, 48, 54)

        panel_w, panel_h = 640, 360
        panel = pygame.Rect(0, 0, panel_w, panel_h)
        panel.center = (vx + vw // 2, vy + vh // 2 - 20)

        pygame.draw.rect(screen, (26, 29, 48), panel, border_radius=20)
        glow = 0.5 + 0.5 * math.sin(self.elapsed * 3)
        border_alpha = int(180 + 75 * glow)
        border_surf = pygame.Surface((panel_w + 8, panel_h + 8), pygame.SRCALPHA)
        pygame.draw.rect(border_surf, (*accent, border_alpha),
                         border_surf.get_rect(), 3, border_radius=22)
        screen.blit(border_surf, (panel.x - 4, panel.y - 4))
        pygame.draw.rect(screen, accent_dim, panel, 2, border_radius=20)

        cx = panel.centerx
        title = "VITÓRIA!" if win else "DERROTA"
        t = self.font_title.render(title, True, accent)
        t_sh = self.font_title.render(title, True, (0, 0, 0))
        tr = t.get_rect(center=(cx, panel.y + 80))
        screen.blit(t_sh, (tr.x + 3, tr.y + 3))
        screen.blit(t, tr)

        pygame.draw.line(screen, accent_dim,
                         (panel.x + 50, panel.y + 130),
                         (panel.right - 50, panel.y + 130), 2)

        if win:
            sub_txt = f"Você derrotou {self.rewards.get('trainer_name', 'o oponente')}!"
            sub_color = (235, 235, 245)
        else:
            sub_txt = "Sua equipe foi derrotada..."
            sub_color = (200, 200, 210)

        sub = self.font_sub.render(sub_txt, True, sub_color)
        screen.blit(sub, sub.get_rect(center=(cx, panel.y + 165)))

        # Recompensas (vitória) / Penalidade (derrota)
        y = panel.y + 210
        gold = self.rewards.get("money", 0)
        xp = self.rewards.get("xp", 0)

        if win:
            info = self.font_info.render(
                f"+{gold} Ouro    ·    +{xp} XP", True, (255, 215, 0))
            screen.blit(info, info.get_rect(center=(cx, y)))
        else:
            if gold > 0 or xp > 0:
                info = self.font_info.render(
                    f"-{gold} Ouro    ·    -{xp} XP", True, (230, 90, 90))
                screen.blit(info, info.get_rect(center=(cx, y)))

                warn = self.font_info.render(
                    "Você perdeu o equivalente ao que ganharia.",
                    True, (160, 165, 190))
                screen.blit(warn, warn.get_rect(center=(cx, y + 26)))
            else:
                info = self.font_info.render(
                    "Nenhuma penalidade — apenas tente novamente!",
                    True, (170, 175, 200))
                screen.blit(info, info.get_rect(center=(cx, y)))

        # Botão
        mouse = pygame.mouse.get_pos()
        hover = self.btn.collidepoint(mouse)
        btn_color = (80, 180, 100) if win else (180, 80, 90)
        if hover:
            btn_color = (110, 220, 130) if win else (220, 110, 120)

        pygame.draw.rect(screen, btn_color, self.btn, border_radius=14)
        pygame.draw.rect(screen, accent, self.btn, 3, border_radius=14)

        label = "Voltar ao NPC Hall"
        bt = self.font_btn.render(label, True, (255, 255, 255))
        screen.blit(bt, bt.get_rect(center=self.btn.center))

    def _render_placing_hint(self, screen):
        sm = self.screen_manager
        vx, vy = sm.viewport_x, sm.viewport_y
        vw = sm.viewport_width

        required = len(self._local_team_objs)
        placed = len(self.placement_manager.placed_pokemon)

        font = pygame.font.Font(None, 28)
        text = f"Posicione seus Pokémon: {placed}/{required}"
        hint = font.render(text, True, (255, 215, 0))
        shadow = font.render(text, True, (0, 0, 0))

        panel_w = max(hint.get_width() + 40, 520)
        panel_h = 70
        panel = pygame.Rect(vx + (vw - panel_w) // 2, vy + 20, panel_w, panel_h)

        bg = pygame.Surface((panel_w, panel_h), pygame.SRCALPHA)
        bg.fill((0, 0, 0, 190))
        screen.blit(bg, panel)
        pygame.draw.rect(screen, (255, 215, 0), panel, 2, border_radius=10)

        screen.blit(shadow, (panel.centerx - hint.get_width() // 2 + 2,
                             panel.y + 10 + 2))
        screen.blit(hint, (panel.centerx - hint.get_width() // 2, panel.y + 10))

        sub = pygame.font.Font(None, 18).render(
            "Arraste pokémons do HUD inferior até os spots verdes. "
            "O oponente posiciona após cada pokémon seu. "
            "Clique direito remove.",
            True, (190, 200, 220))
        screen.blit(sub, (panel.centerx - sub.get_width() // 2, panel.y + 42))

    def _render_countdown(self, screen):
        sm = self.screen_manager
        vx, vy = sm.viewport_x, sm.viewport_y
        vw, vh = sm.viewport_width, sm.viewport_height

        ov = pygame.Surface((vw, vh), pygame.SRCALPHA)
        ov.fill((0, 0, 0, 110))
        screen.blit(ov, (vx, vy))

        secs = max(1, int(math.ceil(self.arena_countdown)))
        big = pygame.font.Font(None, 110)
        t = big.render(f"{secs}", True, (255, 80, 80))
        sh = big.render(f"{secs}", True, (0, 0, 0))
        r = t.get_rect(center=(vx + vw // 2, vy + vh // 2))
        screen.blit(sh, (r.x + 4, r.y + 4))
        screen.blit(t, r)

        sub = pygame.font.Font(None, 34)
        s = sub.render("Prepare-se para a batalha!", True, (255, 215, 0))
        screen.blit(s, s.get_rect(center=(vx + vw // 2, vy + vh // 2 + 60)))

    def _render_enemy_place_toast(self, screen):
        """Toast temporário avisando que o oponente posicionou um pokémon."""
        if self._enemy_place_feedback_timer <= 0:
            return

        sm = self.screen_manager
        vx, vy = sm.viewport_x, sm.viewport_y
        vw = sm.viewport_width

        # Fade-out nos últimos 0.5s
        alpha = int(255 * min(1.0, self._enemy_place_feedback_timer / 0.5))

        font = pygame.font.Font(None, 26)
        txt = font.render("O oponente posicionou um Pokémon!",
                          True, (255, 190, 100))

        pad_x, pad_y = 18, 9
        box = pygame.Rect(0, 0,
                          txt.get_width() + pad_x * 2,
                          txt.get_height() + pad_y * 2)
        box.center = (vx + vw // 2, vy + 150)

        bg = pygame.Surface((box.width, box.height), pygame.SRCALPHA)
        bg.fill((40, 30, 20, alpha))
        screen.blit(bg, box)

        border = pygame.Surface((box.width + 4, box.height + 4),
                                pygame.SRCALPHA)
        pygame.draw.rect(border, (255, 160, 70, alpha),
                         border.get_rect(), 2, border_radius=10)
        screen.blit(border, (box.x - 2, box.y - 2))

        txt.set_alpha(alpha)
        screen.blit(txt, txt.get_rect(center=box.center))