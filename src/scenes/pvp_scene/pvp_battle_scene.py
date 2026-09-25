# src/scenes/pvp_scene/pvp_battle_scene.py
"""
PvPBattleScene — batalha PvP entre jogadores com sync de rede.

Regras de substituição:
  - Quando um pokémon morre, o corpo fica no campo por 10s.
  - O spot é LIBERADO imediatamente para que o PERDEDOR possa arrastar
    um novo pokémon do HUD em cima do corpo.
  - Após 10s, se o PERDEDOR não substituiu, o jogo posiciona
    automaticamente o primeiro pokémon disponível do time.
  - VENCEDOR (quem derrotou um pokémon inimigo): recebe SEMPRE um overlay
    com cards (10s) para escolher trocar um dos seus pokémon posicionados
    por outro do HUD, ou "Não trocar".
  - Uma vez colocado, um pokémon NÃO pode ser removido nem trocado por
    drag — apenas substituindo um MORTO (janela de 10s) ou via overlay do
    VENCEDOR.
  - O contador de 10s do placement inicial fica SEMPRE visível durante a
    fase de placement.
  - Bag de itens desabilitada no PvP.
  - Conquistas desabilitadas no PvP (achievements_enabled = False).
"""
import json
import math
import os
import pygame

from src.scenes.base_scene import BaseScene
from src.entities.pokemon import Pokemon
from src.network.protocol import create_message
from src.data.pvp_catalog import (
    get_pvp_path, split_spots_for_teams, split_team_spots_among_players,
    get_pvp_format, get_pvp_total_on_field,
)


# Tempo que o corpo fica no campo antes de ser removido
CORPSE_LIFETIME = 10.0

# Tempo máximo para posicionar pokémon no início da partida
PLACEMENT_TIME = 10.0


# =====================================================================
# HOOK GLOBAL: dano em pokémon remoto → avisa o dono
# =====================================================================
def _install_pvp_damage_hook():
    from src.entities.pokemon.combat import PokemonCombat
    if getattr(PokemonCombat, '_pvp_damage_hook', False):
        return
    original_take = PokemonCombat.take_damage

    def hooked_take(self_c, damage, attacker=None):
        pokemon = self_c.pokemon
        old_hp = pokemon.current_hp
        result = original_take(self_c, damage, attacker)
        new_hp = pokemon.current_hp
        actual = old_hp - new_hp

        if actual > 0 and getattr(pokemon, '_is_remote', False):
            bs = getattr(pokemon, 'battle_system', None)
            scene = getattr(bs, 'game_scene', None) if bs else None
            if scene is not None and hasattr(scene, '_my_uuid'):
                owner_uuid = getattr(pokemon, '_pvp_owner_uuid', None)
                if owner_uuid and owner_uuid != scene._my_uuid:
                    try:
                        scene._network.send_to_all(create_message(
                            "PVP_POKEMON_DAMAGE", {
                                "owner_uuid": owner_uuid,
                                "unique_id": pokemon.unique_id,
                                "damage": int(actual),
                            }))
                    except Exception as e:
                        print(f"[PVP] erro enviar damage: {e}")
        return result

    PokemonCombat.take_damage = hooked_take
    PokemonCombat._pvp_damage_hook = True
    print("[PVP] Hook de dano instalado")


# =====================================================================
# HOOK GLOBAL: status → broadcast
# =====================================================================
def _install_pvp_status_hook():
    """Hook em EffectManager.apply_status/remove_status para propagar
    status aplicados em pokémons remotos de volta ao dono.

    Também protege contra loop: se a aplicação veio da rede
    (_pvp_applying_remote=True), apenas delega sem re-broadcastar.
    """
    from src.battle.effects.effect_manager import EffectManager
    if getattr(EffectManager, '_pvp_status_hook', False):
        return

    original_apply = EffectManager.apply_status
    original_remove = EffectManager.remove_status

    def hooked_apply(self_em, pokemon, status, *args, **kwargs):
        # ★ Guard: aplicação vinda da rede → não re-broadcasta
        if getattr(self_em, '_pvp_applying_remote', False):
            return original_apply(self_em, pokemon, status, *args, **kwargs)

        result = original_apply(self_em, pokemon, status, *args, **kwargs)
        if not result:
            return result
        if not getattr(pokemon, '_is_remote', False):
            return result

        bs = getattr(pokemon, 'battle_system', None)
        scene = getattr(bs, 'game_scene', None) if bs else None
        if scene is None or not hasattr(scene, '_my_uuid'):
            return result
        owner_uuid = getattr(pokemon, '_pvp_owner_uuid', None)
        if not owner_uuid or owner_uuid == scene._my_uuid:
            return result
        try:
            scene._network.send_to_all(create_message(
                "PVP_STATUS_APPLY", {
                    "owner_uuid": owner_uuid,
                    "unique_id": pokemon.unique_id,
                    "status_type": status.type.value,
                }))
            print(f"[PVP] Status broadcast: {pokemon.name} "
                  f"({status.type.value}) → {owner_uuid[:8]}")
        except Exception as e:
            print(f"[PVP] erro enviar status apply: {e}")
        return result

    def hooked_remove(self_em, pokemon):
        # ★ Guard: remoção vinda da rede → não re-broadcasta
        if getattr(self_em, '_pvp_applying_remote', False):
            return original_remove(self_em, pokemon)

        old = self_em.status_effects.get(id(pokemon))
        old_type = old.type.value if old else None

        result = original_remove(self_em, pokemon)

        if result and old_type and getattr(pokemon, '_is_remote', False):
            bs = getattr(pokemon, 'battle_system', None)
            scene = getattr(bs, 'game_scene', None) if bs else None
            if scene is None or not hasattr(scene, '_my_uuid'):
                return result
            owner_uuid = getattr(pokemon, '_pvp_owner_uuid', None)
            if not owner_uuid or owner_uuid == scene._my_uuid:
                return result
            try:
                scene._network.send_to_all(create_message(
                    "PVP_STATUS_REMOVE", {
                        "owner_uuid": owner_uuid,
                        "unique_id": pokemon.unique_id,
                    }))
            except Exception as e:
                print(f"[PVP] erro enviar status remove: {e}")
        return result

    EffectManager.apply_status = hooked_apply
    EffectManager.remove_status = hooked_remove
    EffectManager._pvp_status_hook = True
    print("[PVP] Hook de status instalado")


# =====================================================================
# HOOK GLOBAL: stat mod → broadcast
# =====================================================================
def _install_pvp_stat_hook():
    from src.battle.effects.effect_manager import EffectManager
    if getattr(EffectManager, '_pvp_stat_hook', False):
        return

    original_add = EffectManager.add_stat_modifier

    def hooked_add(self_em, pokemon, stat_type, stages,
                   duration=None, is_battle_item=False):
        # ★ Guard: aplicação vinda da rede → não re-broadcasta
        if getattr(self_em, '_pvp_applying_remote', False):
            return original_add(self_em, pokemon, stat_type, stages,
                                duration, is_battle_item)

        result = original_add(self_em, pokemon, stat_type, stages,
                              duration, is_battle_item)
        if not result:
            return result
        if not getattr(pokemon, '_is_remote', False):
            return result

        bs = getattr(pokemon, 'battle_system', None)
        scene = getattr(bs, 'game_scene', None) if bs else None
        if scene is None or not hasattr(scene, '_my_uuid'):
            return result
        owner_uuid = getattr(pokemon, '_pvp_owner_uuid', None)
        if not owner_uuid or owner_uuid == scene._my_uuid:
            return result

        try:
            scene._network.send_to_all(create_message(
                "PVP_STAT_MOD", {
                    "owner_uuid": owner_uuid,
                    "unique_id": pokemon.unique_id,
                    "stat": stat_type.value,
                    "stages": int(stages),
                    "duration": float(duration) if duration else 0.0,
                }))
            print(f"[PVP] Stat broadcast: {pokemon.name} "
                  f"{stat_type.value} {stages:+d}")
        except Exception as e:
            print(f"[PVP] erro enviar stat_mod: {e}")
        return result

    EffectManager.add_stat_modifier = hooked_add
    EffectManager._pvp_stat_hook = True
    print("[PVP] Hook de stat_mod instalado")


# =====================================================================
# HOOK GLOBAL: clima → broadcast
# =====================================================================
def _install_pvp_weather_hook():
    from src.battle.effects.specific.weather.weather_manager import WeatherManager
    if getattr(WeatherManager, '_pvp_weather_hook', False):
        return

    original_set_weather = WeatherManager.set_weather
    WeatherManager._pvp_active_scene = None

    def hooked_set_weather(self_wm, weather_type, duration, source=None):
        result = original_set_weather(
            self_wm, weather_type, duration, source=source)

        scene = WeatherManager._pvp_active_scene
        if scene is None:
            return result
        if getattr(scene, '_applying_remote_weather', False):
            return result
        if not getattr(scene, '_network', None):
            return result

        try:
            weather_value = (
                weather_type.value if hasattr(weather_type, 'value')
                else str(weather_type)
            )
            scene._network.send_to_all(create_message(
                "PVP_WEATHER_CHANGE", {
                    "weather_value": weather_value,
                    "duration": float(duration),
                }))
            print(f"[PVP] Weather broadcast: {weather_value} ({duration}s)")
        except Exception as e:
            print(f"[PVP] erro weather broadcast: {e}")
        return result

    WeatherManager.set_weather = hooked_set_weather
    WeatherManager._pvp_weather_hook = True
    print("[PVP] Hook de clima instalado")


# =====================================================================
# WAVE SHIM
# =====================================================================
class _PvPWaveManagerShim:
    def __init__(self, scene):
        self.scene = scene
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
    def reset_gold(self): pass
    def get_total_gold_earned(self): return 0
    def is_next_wave_boss(self): return False
    def has_more_waves(self): return False
    def has_active_waves(self): return False
    def is_wave_completed(self, i): return False
    def is_boss_defeated(self): return False
    def is_boss_spawned(self): return False
    def set_condition(self, c): pass
    def set_paused(self, p): self.paused = bool(p)
    def get_spawn_countdown(self): return 0.0

    def update(self, dt):
        self.active_enemies = [
            e for e in self.active_enemies
            if e.is_alive() and not e.is_defeated
        ]
        return []

    def is_wave_completely_finished(self):
        return not any(e.is_alive() and not e.is_defeated
                       for e in self.active_enemies)

    def get_current_wave_info(self):
        return {
            "name": "PVP", "index": "PVP", "total": 1,
            "enemies_remaining": 0, "enemies_spawned": 0,
            "enemies_total": 1, "progress": 0.0, "active_paths": 0,
        }

    def remove_enemy(self, enemy):
        if enemy in self.active_enemies:
            self.active_enemies.remove(enemy)


# =====================================================================
# CENA
# =====================================================================
class PvPBattleScene(BaseScene):
    COUNTDOWN_TIME = 5.0
    PVP_COOLDOWN = 1.5
    ALLY_ATTACK_RANGE = 420
    SYNC_INTERVAL = 0.1

    def __init__(self, game, network, all_teams,
                 format_chapter, arena_chapter, arena_level,
                 my_team_side="a", on_exit=None):
        super().__init__(game)

        _install_pvp_damage_hook()
        _install_pvp_status_hook()
        _install_pvp_stat_hook()
        _install_pvp_weather_hook()

        try:
            from src.battle.effects.specific.weather.weather_manager import WeatherManager
            WeatherManager._pvp_active_scene = self
        except Exception:
            pass

        self._network = network
        self._all_teams = all_teams or {}
        self._format_chapter = int(format_chapter)
        self._arena_chapter = int(arena_chapter)
        self._arena_level = int(arena_level)
        self._my_team_side = my_team_side
        self._on_exit_callback = on_exit

        # ★ Conquistas são exclusivas do modo campanha.
        #   Código de achievement checa esta flag antes de rodar.
        self.achievements_enabled = False

        (self.players_per_team,
         self.pokemon_per_player,
         self.spots_per_player,
         self.format_name) = get_pvp_format(self._format_chapter)

        self._total_players = len(self._all_teams)
        self._total_on_field_per_team = get_pvp_total_on_field(self._format_chapter)

        self.player = game.player
        self.screen_manager = game.screen_manager
        self._my_uuid = (
            getattr(game.player, "uuid", None)
            or getattr(network, "my_uuid", None)
            or "unknown"
        )

        # Pokedex para os retratos do overlay de troca
        from src.data.pokedex import Pokedex
        self.pokedex = Pokedex()

        self.pvp_state = "placing"
        self.pvp_result = None
        self.pvp_countdown = self.COUNTDOWN_TIME
        self.paused = False
        self.game_paused = False
        self.ui_hidden = False
        self._pvp_overlay = None
        self._swap_overlay = None
        self._battle_elapsed = 0.0
        self._last_dt = 0.0
        self.move_select_overlay = None
        self.dragging_camera = False
        self.last_mouse_pos = None

        self._local_placement_ready = False
        self._remote_placement_done = set()
        # Timer do placement inicial (10s) — SEMPRE decrementa na fase de
        # placement, mesmo depois de o jogador local estar pronto.
        self._placement_timer = PLACEMENT_TIME

        self._sync_timer = 0.0
        self._remote_pokemon = {}
        self._local_team_objs = []
        self._ally_team_objs = []
        self._enemy_team_objs = []
        self._local_team_dead = False
        self._original_team = None
        self._applying_remote_weather = False
        self._applying_remote_day_night = False

        # Timers de remoção de corpos MEUS (id(pokemon) -> segundos restantes)
        self._death_timers = {}

        # Dados do mapa (dia/noite/clima-base) — preenchidos em _load_map
        self._map_day_night = "day"
        self._map_base_weather = "none"

        self.day_night_mode = "day"
        self.base_weather = "none"

        self._uuid_to_side = {}
        for u, info in self._all_teams.items():
            self._uuid_to_side[u] = info.get("team_side", "a")

        from src.battle.battle_system import BattleSystem
        from src.scenes.game_scene.components.renderer.map_renderer import MapRenderer
        from src.scenes.game_scene.components.renderer.path_renderer import PathRenderer
        from src.scenes.game_scene.components.renderer.pokemon_spot_renderer import PokemonSpotRenderer
        from src.scenes.game_scene.components.managers.placement_manager import PlacementManager
        from src.scenes.game_scene.components.managers.overlay_manager import OverlayManager
        from src.scenes.game_scene.components.managers.team_manager import GameTeamManager
        from src.scenes.game_scene.components.managers.move_quick_switch_manager import MoveQuickSwitchManager
        from src.battle.effects.specific.weather.weather_filter import WeatherFilter
        from src.battle.effects.specific.day_night.day_night_filter import DayNightFilter
        from src.scenes.game_scene.components.day_night_weather_system import DayNightWeatherSystem

        self.map_renderer = MapRenderer()
        self.path_renderer = PathRenderer()
        self.spot_renderer = PokemonSpotRenderer()
        self.weather_filter = WeatherFilter()
        self.day_night_filter = DayNightFilter()

        self._load_map()
        w, h = self.map_renderer.get_dimensions()
        self.world_width = w if w > 0 else 2000
        self.world_height = h if h > 0 else 2000

        self.game.initialize_camera(self.world_width, self.world_height)
        self.camera = self.game.camera
        self.camera.set_limits(-500, self.world_width + 500,
                               -500, self.world_height + 500)
        self.camera.x = self.world_width / 2
        self.camera.y = self.world_height / 2

        self.battle_system = BattleSystem(self)
        self.effect_manager = self.battle_system.effect_manager

        self.day_night_weather = DayNightWeatherSystem(self)
        self.day_night_weather.initialize()

        self.overlay_manager = OverlayManager(self)
        self.placement_manager = PlacementManager(self)

        self._setup_teams()

        self._original_team = list(game.player.team)
        game.player.team = self._local_team_objs
        for p in self._local_team_objs:
            try:
                p.full_restore()
            except Exception:
                pass
            p.is_in_team = True
        print(f"[PVP] Time do HUD trocado ({len(self._local_team_objs)})")

        self.wave_manager = _PvPWaveManagerShim(self)

        self.team_manager = GameTeamManager(self.game, self)
        self.move_quick_switch_manager = MoveQuickSwitchManager(self)

        all_p = (self._local_team_objs + self._ally_team_objs
                 + self._enemy_team_objs)
        for p in all_p:
            p.screen_manager = self.screen_manager
            p.camera = self.camera
            p.game_scene = self
            p.set_battle_system(self.battle_system)
            self.battle_system.set_effect_manager_for_pokemon(p)
            p._arena_no_return = True
            p._pvp_no_return = True

        if self._network and self._network.is_host:
            self._broadcast_day_night()

        print(f"[PVP] Iniciado {self.format_name} | "
              f"lado={self._my_team_side} | "
              f"time={len(self._local_team_objs)} | "
              f"spots_meus={len(self._my_spots)} | "
              f"aliados={len(self._ally_team_objs)} | "
              f"inimigos={len(self._enemy_team_objs)} | "
              f"total_players={self._total_players} | "
              f"dia={self._map_day_night} | "
              f"clima_base={self._map_base_weather}")

    # ==================================================================
    def _load_map(self):
        path = get_pvp_path(self._arena_chapter, self._arena_level)
        if not os.path.exists(path):
            print(f"[PVP] AVISO: mapa não encontrado: {path}")
            return
        print(f"[PVP] Carregando mapa: {path}")
        try:
            with open(path, "r", encoding="utf-8") as f:
                data = json.load(f)
        except Exception as e:
            print(f"[PVP] Erro lendo mapa: {e}")
            return
        from src.config.paths import PROJECT_ROOT
        self.map_renderer.load_from_data(data.get("map", {}), PROJECT_ROOT)
        self.path_renderer.load_from_data(data.get("paths", {}))
        self.spot_renderer.load_from_data(data.get("tower_spots", {}))
        self._phase_data = data

        self._map_day_night = str(data.get("day_night_mode", "day") or "day")
        self._map_base_weather = str(data.get("base_weather", "none") or "none")

        self.day_night_mode = self._map_day_night
        self.base_weather = self._map_base_weather
        print(f"[PVP] Mapa define dia/noite='{self.day_night_mode}' "
              f"clima='{self.base_weather}'")

    # ==================================================================
    # DAY/NIGHT
    # ==================================================================
    def _apply_map_day_night(self):
        mode = self._map_day_night
        if not mode:
            return

        new_weather = self._map_base_weather or "none"

        already_correct = (
            getattr(self, 'day_night_mode', None) == mode
            and getattr(self, 'base_weather', None) == new_weather
            and getattr(self.day_night_weather, '_initialized', False)
        )
        if already_correct:
            return

        self.day_night_mode = mode
        self.base_weather = new_weather

        try:
            self.day_night_weather._initialized = False
            self.day_night_weather.initialize()
            print(f"[PVP] Day/night aplicado: {mode} | "
                  f"clima base: {new_weather}")
        except Exception as e:
            print(f"[PVP] erro aplicar day/night: {e}")

    def _broadcast_day_night(self):
        if not self._network:
            return
        mode = self._map_day_night
        if not mode:
            return
        try:
            self._network.send_to_all(create_message("PVP_DAY_NIGHT", {
                "mode": mode,
                "base_weather": self._map_base_weather,
            }))
            print(f"[PVP] Day/night broadcast: {mode} | "
                  f"clima={self._map_base_weather}")
        except Exception as e:
            print(f"[PVP] erro broadcast day/night: {e}")

    def _apply_remote_day_night(self, payload):
        mode = payload.get("mode")
        if not mode:
            return
        if self._applying_remote_day_night:
            return
        self._applying_remote_day_night = True
        try:
            self._map_day_night = mode
            self._map_base_weather = payload.get(
                "base_weather", self._map_base_weather)
            self._apply_map_day_night()
        finally:
            self._applying_remote_day_night = False

    # ==================================================================
    def _setup_teams(self):
        spots = self.spot_renderer.get_spots()
        spots_raw = [
            {"x": s.x, "y": s.y, "size": getattr(s, "size", 24),
             "allowed_types": getattr(s, "allowed_types", [])}
            for s in spots
        ]
        team_a_raw, team_b_raw = split_spots_for_teams(spots_raw)
        team_a_split = split_team_spots_among_players(
            team_a_raw, self.players_per_team)
        team_b_split = split_team_spots_among_players(
            team_b_raw, self.players_per_team)

        by_xy = {(s.x, s.y): s for s in spots}

        def resolve(lst):
            return [by_xy[(d["x"], d["y"])]
                    for d in lst if (d["x"], d["y"]) in by_xy]

        team_a_spots = [resolve(g) for g in team_a_split]
        team_b_spots = [resolve(g) for g in team_b_split]

        side_a = [u for u, s in self._uuid_to_side.items() if s == "a"]
        side_b = [u for u, s in self._uuid_to_side.items() if s == "b"]

        self._my_spots = []
        self._enemy_spots = []

        for i, u in enumerate(side_a):
            if i >= len(team_a_spots):
                break
            if u == self._my_uuid and self._my_team_side == "a":
                self._my_spots = team_a_spots[i]
            else:
                self._enemy_spots.extend(team_a_spots[i])

        for i, u in enumerate(side_b):
            if i >= len(team_b_spots):
                break
            if u == self._my_uuid and self._my_team_side == "b":
                self._my_spots = team_b_spots[i]
            else:
                self._enemy_spots.extend(team_b_spots[i])

        self.spot_renderer.spot_manager.spots = self._my_spots

        my_info = self._all_teams.get(self._my_uuid, {})
        self._local_team_objs = self._build_pokemon_list(
            my_info.get("pokemon", []), is_local=True)

        for u, info in self._all_teams.items():
            if u == self._my_uuid:
                continue
            is_ally = (info.get("team_side") == self._my_team_side)
            for entry in info.get("pokemon", []):
                pk = self._build_single_pokemon(entry, is_local=False)
                if pk is None:
                    continue
                pk._pvp_owner_uuid = u
                pk._pvp_owner_name = info.get("name", "?")
                pk._is_remote = True
                pk._is_ally_remote = is_ally
                pk.is_wild = (not is_ally)
                pk.is_placed = False
                if is_ally:
                    self._ally_team_objs.append(pk)
                else:
                    self._enemy_team_objs.append(pk)
                self._remote_pokemon[pk.unique_id] = pk

        all_p = (self._local_team_objs + self._ally_team_objs
                 + self._enemy_team_objs)
        for p in all_p:
            p.charge_cooldown_max = self.PVP_COOLDOWN
            p.attack_cooldown_max = self.PVP_COOLDOWN
            p.attack_range = self.ALLY_ATTACK_RANGE

        print(f"[PVP] Spots meus={len(self._my_spots)} | "
              f"time={len(self._local_team_objs)} | "
              f"aliados={len(self._ally_team_objs)} | "
              f"inimigos={len(self._enemy_team_objs)}")

    def _build_pokemon_list(self, data_list, is_local):
        out = []
        for entry in data_list:
            pk = self._build_single_pokemon(entry, is_local)
            if pk is not None:
                out.append(pk)
        return out

    def _build_single_pokemon(self, entry, is_local):
        try:
            pk = Pokemon.from_dict(entry)
        except Exception as e:
            print(f"[PVP] Erro from_dict: {e}")
            return None
        pk.is_wild = False
        pk.is_in_team = is_local
        pk.is_placed = False
        pk.game_scene = self
        pk.combat_state = "idle"
        pk._arena_no_return = True
        pk._pvp_no_return = True
        if is_local:
            pk._pvp_owner_uuid = self._my_uuid
        return pk

    # ==================================================================
    # PLACEMENT
    # ==================================================================
    def _broadcast_placement(self, pokemon, spot=None, is_reserve=False):
        if not self._network:
            return
        try:
            pdata = pokemon.to_dict()
        except Exception as e:
            print(f"[PVP] erro serializar {pokemon.name}: {e}")
            return

        payload = {
            "uuid": self._my_uuid,
            "action": "place",
            "unique_id": pokemon.unique_id,
            "pokemon_data": pdata,
            "is_reserve": is_reserve,
        }

        if spot is not None:
            payload["spot_x"] = spot.x
            payload["spot_y"] = spot.y
        else:
            payload["spot_x"] = pokemon.original_spot_x
            payload["spot_y"] = pokemon.original_spot_y

        try:
            self._network.send_to_all(create_message("PVP_PLACEMENT", payload))
        except Exception as e:
            print(f"[PVP] erro enviar placement: {e}")

    def _apply_remote_placement(self, payload):
        uid = payload.get("unique_id")
        if not uid:
            return

        pk = self._remote_pokemon.get(uid)
        if not pk:
            data = payload.get("pokemon_data")
            if not data:
                return
            try:
                pk = Pokemon.from_dict(data)
            except Exception as e:
                print(f"[PVP] erro criar remoto: {e}")
                return
            pk.is_wild = True
            pk.is_in_team = False
            pk.is_placed = False
            pk._is_remote = True
            pk._arena_no_return = True
            pk._pvp_no_return = True
            pk.game_scene = self
            pk.screen_manager = self.screen_manager
            pk.camera = self.camera
            pk.set_battle_system(self.battle_system)
            self.battle_system.set_effect_manager_for_pokemon(pk)
            pk.charge_cooldown_max = self.PVP_COOLDOWN
            pk.attack_cooldown_max = self.PVP_COOLDOWN
            pk.attack_range = self.ALLY_ATTACK_RANGE
            self._remote_pokemon[uid] = pk
            self._enemy_team_objs.append(pk)

        if pk in self.placement_manager.placed_pokemon:
            self.placement_manager.placed_pokemon.remove(pk)

        ts = self.placement_manager.tile_size
        sx = payload.get("spot_x", 0)
        sy = payload.get("spot_y", 0)
        cx = (sx // ts) * ts + ts // 2
        cy = (sy // ts) * ts + ts // 2

        pk.x, pk.y = cx, cy
        pk.original_spot_x = cx
        pk.original_spot_y = cy
        pk.placed_tile_x = cx // ts
        pk.placed_tile_y = cy // ts
        pk.is_placed = True
        pk.combat_state = "attacking"
        pk.is_defeated = False
        if pk.current_hp <= 0:
            pk.current_hp = pk.max_hp

        self.placement_manager.placed_pokemon.append(pk)

        if pk not in self.wave_manager.active_enemies:
            self.wave_manager.active_enemies.append(pk)

        tag = "RESERVA" if payload.get("is_reserve") else "REMOTO"
        print(f"[PVP] {tag} {pk.name} de "
              f"{getattr(pk, '_pvp_owner_name', '?')} em ({cx},{cy})")

    def _on_pokemon_placed(self, placement_data):
        """Permite drop durante 'placing' E 'battle'."""
        if self.pvp_state not in ("placing", "battle"):
            return
        action = placement_data.get('action', 'place')
        is_replacement = placement_data.get('is_replacement', False)

        if action == 'place':
            pokemon = placement_data['pokemon']
            spot = placement_data['spot']

            if self.pvp_state == "battle" and not is_replacement:
                dead_body = self._find_own_dead_at_spot(spot)
                if dead_body is not None:
                    self._replace_own_pokemon(dead_body, pokemon, spot)
                    return
                print(f"[PVP] Drop em spot sem corpo morto — ignorado")
                return

            if spot.occupied:
                if (self.pvp_state == "battle"
                        and self._try_replace_own_on_spot(pokemon, spot)):
                    return
                return

            if self.pvp_state == "placing":
                my_placed = [
                    p for p in self.placement_manager.placed_pokemon
                    if getattr(p, '_pvp_owner_uuid', None) == self._my_uuid
                ]
                if len(my_placed) >= self.spots_per_player:
                    print(f"[PVP] Você já tem {len(my_placed)} em campo "
                          f"(max {self.spots_per_player})")
                    return

            result = self.placement_manager.add_pokemon(spot, pokemon)
            if result:
                pokemon.set_battle_system(self.battle_system)
                self.battle_system.set_effect_manager_for_pokemon(pokemon)
                pokemon.is_wild = False
                pokemon.is_placed = True
                pokemon.game_scene = self
                pokemon._arena_no_return = True
                pokemon._pvp_no_return = True
                if getattr(pokemon, '_pvp_owner_uuid', None) is None:
                    pokemon._pvp_owner_uuid = self._my_uuid

                if self.pvp_state == "battle":
                    pokemon.combat_state = "attacking"

                self._broadcast_placement(pokemon, spot, is_reserve=False)

                if self.pvp_state == "placing":
                    self._check_placing_complete()
                else:
                    print(f"[PVP] {pokemon.name} entrou em campo "
                          f"(durante batalha)")

        elif action == 'move':
            pokemon = placement_data['pokemon']
            to_spot = placement_data['to_spot']
            from_spot = placement_data.get('from_spot')
            if from_spot:
                from_spot.occupied = False
            ts = self.placement_manager.tile_size
            cx = (to_spot.x // ts) * ts + ts // 2
            cy = (to_spot.y // ts) * ts + ts // 2
            pokemon.x, pokemon.y = cx, cy
            pokemon.original_spot_x = cx
            pokemon.original_spot_y = cy
            to_spot.occupied = True
            self._broadcast_placement(pokemon, to_spot, is_reserve=False)

    # ------------------------------------------------------------------
    # SUBSTITUIÇÃO POR DRAG (PERDEDOR) E POR OVERLAY (VENCEDOR)
    # ------------------------------------------------------------------
    def _find_own_dead_at_spot(self, spot):
        ts = self.placement_manager.tile_size
        stx = spot.x // ts
        sty = spot.y // ts

        for p in self.placement_manager.placed_pokemon:
            if getattr(p, '_pvp_owner_uuid', None) != self._my_uuid:
                continue
            if p.is_alive() and not getattr(p, 'is_defeated', False):
                continue
            if (getattr(p, 'placed_tile_x', None) == stx
                    and getattr(p, 'placed_tile_y', None) == sty):
                return p

        for p in self.placement_manager.placed_pokemon:
            if getattr(p, '_pvp_owner_uuid', None) != self._my_uuid:
                continue
            if p.is_alive() and not getattr(p, 'is_defeated', False):
                continue
            cx = (spot.x // ts) * ts + ts // 2
            cy = (spot.y // ts) * ts + ts // 2
            if abs(p.x - cx) < 5 and abs(p.y - cy) < 5:
                return p
        return None

    def _try_replace_own_on_spot(self, new_pk, spot):
        existing = self._find_own_dead_at_spot(spot)
        if existing is None or existing is new_pk:
            return False
        self._replace_own_pokemon(existing, new_pk, spot)
        return True

    def _replace_own_pokemon(self, old_pk, new_pk, spot):
        self._death_timers.pop(id(old_pk), None)

        if old_pk in self.placement_manager.placed_pokemon:
            self.placement_manager.placed_pokemon.remove(old_pk)
        old_pk.is_placed = False
        old_pk.combat_state = "idle"
        old_pk.placed_tile_x = None
        old_pk.placed_tile_y = None

        spot.occupied = False

        if self._network:
            try:
                self._network.send_to_all(create_message(
                    "PVP_POKEMON_REMOVE", {
                        "uuid": self._my_uuid,
                        "unique_id": old_pk.unique_id,
                    }))
            except Exception as e:
                print(f"[PVP] erro replace remove: {e}")

        self._on_pokemon_placed({
            'action': 'place',
            'pokemon': new_pk,
            'spot': spot,
            'is_replacement': True,
        })
        print(f"[PVP] Substituição: {old_pk.name} → {new_pk.name}")

    def _check_placing_complete(self):
        if self.pvp_state != "placing" or self._local_placement_ready:
            return

        placed = len([
            p for p in self.placement_manager.placed_pokemon
            if getattr(p, '_pvp_owner_uuid', None) == self._my_uuid
        ])
        required = self.spots_per_player

        if required > 0 and placed >= required:
            self._local_placement_ready = True
            print(f"[PVP] Local pronto ({placed}/{required})")
            if self._network:
                try:
                    self._network.send_to_all(create_message("PVP_PLACEMENT", {
                        "uuid": self._my_uuid,
                        "action": "done",
                    }))
                except Exception as e:
                    print(f"[PVP] erro enviar done: {e}")
            if self._network and self._network.is_host:
                self._check_all_ready()

    def _check_all_ready(self):
        if not self._network or not self._network.is_host:
            return
        if self.pvp_state != "placing":
            return
        if not self._local_placement_ready:
            return
        if len(self._remote_placement_done) < self._total_players - 1:
            return
        print(f"[PVP] TODOS prontos! Iniciando countdown...")
        try:
            self._network.send_to_all(create_message("PVP_START", {}))
        except Exception:
            pass
        self._on_all_ready()

    def _on_all_ready(self):
        if self.pvp_state == "placing":
            self.pvp_state = "countdown"
            self.pvp_countdown = self.COUNTDOWN_TIME
            print("[PVP] → countdown")

    # ==================================================================
    # AUTO-PLACEMENT (timeout de 10s no início)
    # ==================================================================
    def _auto_place_pokemon(self):
        if self._local_placement_ready:
            return

        print(f"[PVP] Auto-placement: {self._placement_timer:.1f}s "
              f"esgotado, posicionando automaticamente...")

        placed_ids = {
            p.unique_id for p in self.placement_manager.placed_pokemon
            if getattr(p, '_pvp_owner_uuid', None) == self._my_uuid
        }
        available = [
            p for p in self._local_team_objs if p.unique_id not in placed_ids
        ]

        for spot in self._my_spots:
            if self._local_placement_ready:
                break
            if spot.occupied or not available:
                continue
            pk = available.pop(0)
            self._on_pokemon_placed({
                'action': 'place',
                'pokemon': pk,
                'spot': spot,
            })

        if not self._local_placement_ready:
            self._local_placement_ready = True
            if self._network:
                try:
                    self._network.send_to_all(create_message("PVP_PLACEMENT", {
                        "uuid": self._my_uuid,
                        "action": "done",
                    }))
                except Exception as e:
                    print(f"[PVP] erro auto-done: {e}")
            if self._network and self._network.is_host:
                self._check_all_ready()

    # ==================================================================
    # AUTO-PLACEMENT DO PERDEDOR (após expirar a janela de 10s)
    # ==================================================================
    def _auto_place_for_loser(self, corpse_pk):
        ts = self.placement_manager.tile_size
        ptx = getattr(corpse_pk, 'placed_tile_x', None)
        pty = getattr(corpse_pk, 'placed_tile_y', None)

        target_spot = None
        for spot in self._my_spots:
            stx = spot.x // ts
            sty = spot.y // ts
            if stx == ptx and sty == pty:
                target_spot = spot
                break

        if target_spot is None:
            for spot in self._my_spots:
                cx = (spot.x // ts) * ts + ts // 2
                cy = (spot.y // ts) * ts + ts // 2
                if abs(corpse_pk.x - cx) < 5 and abs(corpse_pk.y - cy) < 5:
                    target_spot = spot
                    break

        placed_ids = {
            p.unique_id for p in self.placement_manager.placed_pokemon
            if getattr(p, '_pvp_owner_uuid', None) == self._my_uuid
        }
        available = [
            p for p in self._local_team_objs
            if p.unique_id not in placed_ids
            and p.is_alive()
            and not getattr(p, 'is_defeated', False)
        ]

        if target_spot is not None and available:
            new_pk = available[0]
            self._replace_own_pokemon(corpse_pk, new_pk, target_spot)
            new_pk.combat_state = "attacking"
            print(f"[PVP] Auto-place do perdedor: {corpse_pk.name} → "
                  f"{new_pk.name}")
        else:
            self._remove_pokemon_from_field(corpse_pk)
            print(f"[PVP] Auto-place do perdedor sem substituto "
                  f"({corpse_pk.name} removido)")

    # ==================================================================
    # OVERLAY DO VENCEDOR
    # ==================================================================
    def _check_enemy_kills(self):
        """Varre inimigos remotos e dispara overlay do vencedor para
        qualquer um que morreu e ainda não foi oferecido.

        Cobre casos onde a transição was_alive→now_dead não é vista
        no sync (ex: simulação local já matou o remoto antes do pacote
        de state chegar). Idempotente via `_winner_swap_offered`.
        """
        if self.pvp_state != "battle":
            return

        for enemy in self._enemy_team_objs:
            if getattr(enemy, '_is_ally_remote', False):
                continue
            if not getattr(enemy, 'is_defeated', False):
                continue
            if getattr(enemy, '_winner_swap_offered', False):
                continue
            # _on_enemy_killed revalida pré-condições e só marca
            # `_winner_swap_offered` quando de fato oferece o overlay.
            self._on_enemy_killed(enemy)

    def _on_enemy_killed(self, enemy_pk):
        """Chamado quando um pokémon INIMIGO morre na minha tela.

        Sou o VENCEDOR dessa troca. Abro SEMPRE o overlay para eu poder
        trocar um dos meus pokémon posicionados por um do HUD.

        Se já houver um overlay ativo, ele é substituído pelo novo — o
        vencedor sempre tem a chance de escolher para a morte mais recente.
        """
        # Idempotência: um overlay por inimigo
        if getattr(enemy_pk, '_winner_swap_offered', False):
            return
        if self.pvp_state != "battle":
            return

        # Preciso ter pokémon vivo posicionado
        my_placed = [
            p for p in self.placement_manager.placed_pokemon
            if getattr(p, '_pvp_owner_uuid', None) == self._my_uuid
            and p.is_alive()
            and not getattr(p, 'is_defeated', False)
        ]
        if not my_placed:
            return

        # Preciso ter pokémon vivo no banco (fora do campo)
        my_benched = [
            p for p in self._local_team_objs
            if not getattr(p, 'is_placed', False)
            and p.is_alive()
            and not getattr(p, 'is_defeated', False)
        ]
        if not my_benched:
            return

        enemy_pk._winner_swap_offered = True

        # Substitui overlay ativo silenciosamente (sem chamar callback do antigo)
        if self._swap_overlay and self._swap_overlay.active:
            self._swap_overlay.active = False

        my_placed.sort(
            key=lambda p: (p.x - enemy_pk.x) ** 2 + (p.y - enemy_pk.y) ** 2
        )
        placed_to_swap = my_placed[0]

        from src.scenes.pvp_scene.pvp_swap_overlay import SwapSelectionOverlay
        self._swap_overlay = SwapSelectionOverlay(
            self, placed_to_swap, my_benched,
            on_choice=lambda chosen: self._on_winner_swap_choice(
                placed_to_swap, chosen),
            subtitle=(f"Você derrotou {enemy_pk.name}! "
                      f"Trocar {placed_to_swap.name}?"),
        )
        print(f"[PVP] Overlay do vencedor: pode trocar "
              f"{placed_to_swap.name} ({len(my_benched)} no banco) — 10s")

    def _on_winner_swap_choice(self, placed_pk, chosen):
        """Callback do overlay do vencedor."""
        self._swap_overlay = None

        if chosen is None:
            print(f"[PVP] Vencedor optou por não trocar {placed_pk.name}")
            return

        ts = self.placement_manager.tile_size
        ptx = getattr(placed_pk, 'placed_tile_x', None)
        pty = getattr(placed_pk, 'placed_tile_y', None)

        target_spot = None
        for spot in self._my_spots:
            stx = spot.x // ts
            sty = spot.y // ts
            if stx == ptx and sty == pty:
                target_spot = spot
                break

        if target_spot is None:
            for spot in self._my_spots:
                cx = (spot.x // ts) * ts + ts // 2
                cy = (spot.y // ts) * ts + ts // 2
                if abs(placed_pk.x - cx) < 5 and abs(placed_pk.y - cy) < 5:
                    target_spot = spot
                    break

        if target_spot is None:
            print(f"[PVP] Spot não encontrado para {placed_pk.name}")
            return

        self._replace_own_pokemon(placed_pk, chosen, target_spot)
        chosen.combat_state = "attacking"
        print(f"[PVP] Vencedor trocou: {placed_pk.name} → {chosen.name}")

    # ==================================================================
    # UPDATE
    # ==================================================================
    def fixed_update(self, dt):
        self._last_dt = dt
        self._process_network_queue()

        if self._pvp_overlay and self._pvp_overlay.active:
            self._pvp_overlay.update(dt)
            return
        if self.move_select_overlay and self.move_select_overlay.active:
            self.move_select_overlay.update(dt)
        if self._swap_overlay and self._swap_overlay.active:
            self._swap_overlay.update(dt)

        if self.overlay_manager.is_active:
            self.overlay_manager.update(dt)
            return
        if self.game_paused or self.paused:
            return

        if hasattr(self, 'battle_system'):
            self.battle_system.update(dt)
        if hasattr(self, 'day_night_weather'):
            self.day_night_weather.update(dt)

        if self.team_manager:
            self.team_manager.update(dt)
        if self.move_quick_switch_manager:
            self.move_quick_switch_manager.update(dt)

        if self.pvp_state == "placing":
            self._update_placing(dt)
        elif self.pvp_state == "countdown":
            self._update_countdown(dt)
        elif self.pvp_state == "battle":
            self._update_battle(dt)

        if hasattr(self, 'battle_system') and self.battle_system:
            self.battle_system.effect_manager.update(dt)

        self._interpolate_remote_pokemon(dt)

        self._sync_timer += dt
        if self._sync_timer >= self.SYNC_INTERVAL:
            self._sync_timer = 0.0
            self._broadcast_my_pokemon_state()

    def _update_placing(self, dt):
        for p in self.placement_manager.placed_pokemon:
            p.update(dt)
        for e in self.wave_manager.active_enemies:
            e.update(dt)

        if self._placement_timer > 0:
            self._placement_timer -= dt
            if self._placement_timer <= 0:
                self._placement_timer = 0.0
                self._auto_place_pokemon()

    def _update_countdown(self, dt):
        for p in self.placement_manager.placed_pokemon:
            p.update(dt)
        for e in self.wave_manager.active_enemies:
            e.update(dt)
        self.pvp_countdown -= dt
        if self.pvp_countdown <= 0:
            self.pvp_countdown = 0
            self._start_battle()

    def _start_battle(self):
        self.pvp_state = "battle"
        self._battle_elapsed = 0.0
        for p in self.placement_manager.placed_pokemon:
            if p.is_alive():
                p.combat_state = "attacking"
        print("[PVP] Batalha iniciada!")

        if self._network and self._network.is_host:
            self._broadcast_day_night()

    def _update_battle(self, dt):
        self._battle_elapsed += dt
        self.wave_manager.update(dt)
        self.placement_manager.update(dt, self.wave_manager.active_enemies)

        # Gerencia corpos MEUS (dead bodies → 10s → remove/auto-place)
        self._check_dead_pokemon()
        self._update_death_timers(dt)

        # ★ Varre inimigos mortos e dispara overlay do vencedor
        self._check_enemy_kills()

        if self._battle_elapsed > 1.0:
            self._check_battle_end()

    # ==================================================================
    # CORPOS (DEAD BODIES) — janela de 10s do PERDEDOR
    # ==================================================================
    def _check_dead_pokemon(self):
        ts = self.placement_manager.tile_size
        for p in self.placement_manager.placed_pokemon:
            if getattr(p, '_pvp_owner_uuid', None) != self._my_uuid:
                continue
            if p.is_alive() and not p.is_defeated:
                continue
            if id(p) in self._death_timers:
                continue

            self._death_timers[id(p)] = CORPSE_LIFETIME
            print(f"[PVP] {p.name} morreu — janela de {CORPSE_LIFETIME}s "
                  f"para substituir")

            ptx = getattr(p, 'placed_tile_x', None)
            pty = getattr(p, 'placed_tile_y', None)
            freed = False
            for spot in self._my_spots:
                stx = spot.x // ts
                sty = spot.y // ts
                if stx == ptx and sty == pty:
                    spot.occupied = False
                    freed = True
                    break
            if not freed:
                for spot in self._my_spots:
                    cx = (spot.x // ts) * ts + ts // 2
                    cy = (spot.y // ts) * ts + ts // 2
                    if abs(p.x - cx) < 5 and abs(p.y - cy) < 5:
                        spot.occupied = False
                        break

            try:
                if p.has_animation("faint"):
                    p.set_animation_direct("faint")
            except Exception:
                pass

    def _update_death_timers(self, dt):
        to_expire = []
        for pid, timer in list(self._death_timers.items()):
            new_timer = timer - dt
            if new_timer <= 0:
                to_expire.append(pid)
            else:
                self._death_timers[pid] = new_timer

        for pid in to_expire:
            del self._death_timers[pid]

            pk = None
            for p in self.placement_manager.placed_pokemon:
                if id(p) == pid:
                    pk = p
                    break

            if pk is not None:
                self._auto_place_for_loser(pk)

    def _remove_pokemon_from_field(self, pokemon):
        ts = self.placement_manager.tile_size

        ptx = getattr(pokemon, 'placed_tile_x', None)
        pty = getattr(pokemon, 'placed_tile_y', None)
        freed_spot = None

        for spot in self._my_spots:
            stx = spot.x // ts
            sty = spot.y // ts
            if stx == ptx and sty == pty:
                spot.occupied = False
                freed_spot = spot
                break

        if freed_spot is None:
            for spot in self._my_spots:
                cx = (spot.x // ts) * ts + ts // 2
                cy = (spot.y // ts) * ts + ts // 2
                if abs(pokemon.x - cx) < 5 and abs(pokemon.y - cy) < 5:
                    spot.occupied = False
                    freed_spot = spot
                    break

        if pokemon in self.placement_manager.placed_pokemon:
            self.placement_manager.placed_pokemon.remove(pokemon)

        pokemon.is_placed = False

        if self._network:
            try:
                self._network.send_to_all(create_message("PVP_POKEMON_REMOVE", {
                    "uuid": self._my_uuid,
                    "unique_id": pokemon.unique_id,
                }))
            except Exception as e:
                print(f"[PVP] erro enviar remove: {e}")

        spot_info = ""
        if freed_spot:
            spot_info = f" | spot liberado ({freed_spot.x},{freed_spot.y})"
        print(f"[PVP] {pokemon.name} removido do campo{spot_info}")

    def _apply_remote_remove(self, payload):
        if payload.get("uuid") == self._my_uuid:
            return

        uid = payload.get("unique_id")
        pk = self._remote_pokemon.get(uid)
        if not pk:
            return

        ts = self.placement_manager.tile_size
        ptx = getattr(pk, 'placed_tile_x', None)
        pty = getattr(pk, 'placed_tile_y', None)

        for spot in self._enemy_spots:
            stx = spot.x // ts
            sty = spot.y // ts
            if stx == ptx and sty == pty:
                spot.occupied = False
                break

        if pk in self.placement_manager.placed_pokemon:
            self.placement_manager.placed_pokemon.remove(pk)
        if pk in self.wave_manager.active_enemies:
            self.wave_manager.active_enemies.remove(pk)

        pk.is_placed = False
        print(f"[PVP] Remoto {pk.name} removido do campo")

    # ==================================================================
    def _check_battle_end(self):
        my_alive = any(p.is_alive() and not p.is_defeated
                       for p in self._local_team_objs)
        ally_alive = any(
            p.is_alive() and not p.is_defeated
            for p in self._ally_team_objs
        )
        enemy_alive = any(
            p.is_alive() and not p.is_defeated
            for p in self._enemy_team_objs
        )

        if not my_alive and not ally_alive and not self._local_team_dead:
            self._local_team_dead = True
            print("[PVP] Meu time caiu (todos os pokémon derrotados)")

        if not self._network or not self._network.is_host:
            return

        my_side = self._my_team_side

        if my_side == "a":
            side_a_alive = (my_alive or ally_alive)
            side_b_alive = enemy_alive
        else:
            side_a_alive = enemy_alive
            side_b_alive = (my_alive or ally_alive)

        if not side_a_alive and not side_b_alive:
            self._end_battle("lose")
        elif not side_a_alive and side_b_alive:
            self._broadcast_end("b")
        elif not side_b_alive and side_a_alive:
            self._broadcast_end("a")

    def _broadcast_end(self, winner_side):
        if self.pvp_state == "finished":
            return
        self.pvp_state = "finished"
        my_side = self._my_team_side
        result = "win" if winner_side == my_side else "lose"
        self._show_result(result)

        if self._network:
            try:
                self._network.send_to_all(create_message("PVP_END", {
                    "winner_side": winner_side,
                }))
            except Exception:
                pass

    def _end_battle(self, result):
        if self.pvp_state == "finished":
            return
        self.pvp_state = "finished"
        self._show_result(result)
        if self._network:
            my_side = self._my_team_side
            other = "b" if my_side == "a" else "a"
            winner_side = my_side if result == "win" else other
            try:
                self._network.send_to_all(create_message("PVP_END", {
                    "winner_side": winner_side,
                }))
            except Exception:
                pass

    def _show_result(self, result):
        print(f"[PVP] Resultado local: {result}")
        from src.scenes.pvp_scene.pvp_result_overlay import PvPResultOverlay
        self._pvp_overlay = PvPResultOverlay(self, result, {
            "money": 300, "xp": 200,
        })

    # ==================================================================
    # SYNC
    # ==================================================================
    def _broadcast_my_pokemon_state(self):
        if not self._network:
            return
        from src.battle.effects import StatType
        em = self.battle_system.effect_manager

        states = []
        for p in self._local_team_objs:
            status = em.get_status(p)
            status_name = status.type.value if status else None

            stages_payload = {}
            pid = id(p)
            if pid in em.stat_stages:
                for st in StatType:
                    s = em.stat_stages[pid].get_stage(st)
                    if s != 0:
                        stages_payload[st.value] = s

            states.append({
                "unique_id": p.unique_id,
                "current_hp": int(p.current_hp),
                "max_hp": int(p.max_hp),
                "x": float(p.x),
                "y": float(p.y),
                "is_placed": bool(getattr(p, 'is_placed', False)),
                "current_animation": getattr(p, 'current_animation', 'idle'),
                "current_direction": getattr(p, 'current_direction', 'down'),
                "combat_state": getattr(p, 'combat_state', 'idle'),
                "is_defeated": bool(getattr(p, 'is_defeated', False)),
                "status": status_name,
                "stat_stages": stages_payload,
            })
        try:
            self._network.send_to_all(create_message("PVP_POKEMON_STATE", {
                "uuid": self._my_uuid,
                "pokemon": states,
            }))
        except Exception as e:
            print(f"[PVP] erro broadcast state: {e}")

    def _apply_remote_pokemon_state(self, payload):
        if payload.get("uuid") == self._my_uuid:
            return
        for state in payload.get("pokemon", []):
            uid = state.get("unique_id")
            pk = self._remote_pokemon.get(uid)
            if not pk:
                continue

            old_hp = pk.current_hp
            was_alive = old_hp > 0 and not getattr(pk, 'is_defeated', False)

            pk._target_x = float(state.get("x", pk.x))
            pk._target_y = float(state.get("y", pk.y))
            pk.current_hp = state.get("current_hp", pk.current_hp)
            pk.max_hp = state.get("max_hp", pk.max_hp)

            now_dead = (pk.current_hp <= 0
                        or state.get("is_defeated", False))

            if state.get("is_defeated"):
                if not getattr(pk, 'is_defeated', False):
                    try:
                        pk.set_defeated(True)
                    except Exception:
                        pk.is_defeated = True
            else:
                pk.is_defeated = False

            # ★ Sync periódico de status e stat stages.
            # O guard `_pvp_applying_remote` evita re-broadcast.
            self._sync_remote_status(pk, state.get("status"))
            self._sync_remote_stat_stages(pk, state.get("stat_stages", {}))

            # ★ Overlay do VENCEDOR quando um inimigo morre.
            # Não depende mais de `was_alive` — se a simulação local
            # já tiver matado o remoto, esta chamada ainda dispara
            # (idempotente via `_winner_swap_offered`).
            if (now_dead
                    and not getattr(pk, '_is_ally_remote', False)
                    and not getattr(pk, '_winner_swap_offered', False)):
                self._on_enemy_killed(pk)

            if not getattr(pk, '_attack_animation_active', False):
                anim = state.get("current_animation")
                if anim and getattr(pk, 'current_animation', None) != anim:
                    try:
                        pk.set_animation_direct(anim)
                    except Exception:
                        pass
                direction = state.get("current_direction")
                if direction:
                    pk.current_direction = direction
                    try:
                        pk.animation._update_sprite_from_current_animation()
                    except Exception:
                        pass

            cs = state.get("combat_state")
            if cs:
                pk.combat_state = cs

    def _sync_remote_status(self, pk, status_name):
        """Espelha o status do dono no nosso lado. Cobre expiração
        (sono, congelamento) e auto-correção caso um PVP_STATUS_* tenha
        sido perdido."""
        from src.battle.effects import StatusType, StatusEffect
        em = self.battle_system.effect_manager

        current = em.get_status(pk)
        current_type = current.type.value if current else None

        if status_name == current_type:
            return  # já consistente

        em._pvp_applying_remote = True
        try:
            if current:
                em.remove_status(pk)
            if status_name:
                try:
                    st = StatusType(status_name)
                except ValueError:
                    return
                new_status = StatusEffect(st, duration=None)
                em.apply_status(pk, new_status, source=None, silent=True)
        finally:
            em._pvp_applying_remote = False

    def _sync_remote_stat_stages(self, pk, stages_dict):
        """Espelha os stages do dono no nosso lado. Cobre expiração e
        auto-correção caso um PVP_STAT_MOD tenha sido perdido."""
        from src.battle.effects import StatType
        from src.battle.effects.stat_modifier import StatStage
        em = self.battle_system.effect_manager
        pid = id(pk)

        has_any = bool(stages_dict) or pid in em.stat_stages
        if not has_any:
            return

        if pid not in em.stat_stages:
            em.stat_stages[pid] = StatStage()

        changed = False
        for st in StatType:
            target = int(stages_dict.get(st.value, 0))
            current = em.stat_stages[pid].get_stage(st)
            diff = target - current
            if diff != 0:
                em.stat_stages[pid].modify(st, diff)
                changed = True

        if changed and hasattr(pk, 'update_move_speed_from_effects'):
            pk.update_move_speed_from_effects()

    def _interpolate_remote_pokemon(self, dt):
        for pk in self._remote_pokemon.values():
            tx = getattr(pk, '_target_x', None)
            ty = getattr(pk, '_target_y', None)
            if tx is None or ty is None:
                continue
            dx = tx - pk.x
            dy = ty - pk.y
            dist_sq = dx * dx + dy * dy
            if dist_sq > 200 * 200:
                pk.x, pk.y = tx, ty
                pk.rect.x, pk.rect.y = int(pk.x), int(pk.y)
                continue
            lf = min(1.0, dt * 12.0)
            pk.x += dx * lf
            pk.y += dy * lf
            pk.rect.x, pk.rect.y = int(pk.x), int(pk.y)

    # ==================================================================
    # REDE
    # ==================================================================
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
                self._on_pvp_network_message(msg)
                if self.game.current_scene is not self:
                    break
        except Exception as e:
            print(f"[PVP] erro fila: {e}")

    def _on_pvp_network_message(self, msg):
        t = msg.get("type")
        p = msg.get("payload", {})

        if t == "PVP_PLACEMENT":
            uid = p.get("uuid")
            if uid == self._my_uuid:
                return
            action = p.get("action", "place")
            if action == "done":
                if uid and uid not in self._remote_placement_done:
                    self._remote_placement_done.add(uid)
                    total = len(self._remote_placement_done) + 1
                    print(f"[PVP] {uid[:8]} pronto ({total}/{self._total_players})")
                    if self._network and self._network.is_host:
                        self._check_all_ready()
            else:
                self._apply_remote_placement(p)

        elif t == "PVP_POKEMON_REMOVE":
            self._apply_remote_remove(p)

        elif t == "PVP_START":
            self._on_all_ready()

        elif t == "PVP_WEATHER_CHANGE":
            self._apply_remote_weather(p)

        elif t == "PVP_DAY_NIGHT":
            self._apply_remote_day_night(p)

        elif t == "PVP_POKEMON_STATE":
            self._apply_remote_pokemon_state(p)

        elif t == "PVP_POKEMON_ATTACK":
            self._apply_remote_pokemon_attack(p)

        elif t == "PVP_POKEMON_DAMAGE":
            self._apply_damage_to_my_pokemon(p)

        elif t == "PVP_STATUS_APPLY":
            self._apply_status_to_my_pokemon(p)

        elif t == "PVP_STATUS_REMOVE":
            self._remove_status_from_my_pokemon(p)

        elif t == "PVP_STAT_MOD":
            self._apply_stat_mod_to_my_pokemon(p)

        elif t == "PVP_END":
            winner_side = p.get("winner_side")
            my_side = self._my_team_side
            if winner_side:
                result = "win" if winner_side == my_side else "lose"
            else:
                result = p.get("result", "lose")
            if self.pvp_state != "finished":
                self.pvp_state = "finished"
                self._show_result(result)

        elif t == "PVP_LEAVE":
            pass

        elif t == "DISCONNECT":
            print("[PVP] oponente desconectou")
            if self.pvp_state != "finished":
                self.pvp_state = "finished"
                self._show_result("win")

    def _apply_remote_weather(self, payload):
        from src.battle.effects.specific.weather.weather_state import WeatherType
        weather_value = payload.get("weather_value")
        duration = float(payload.get("duration", 30.0))
        if not weather_value:
            return
        try:
            weather_type = WeatherType(weather_value)
        except (ValueError, KeyError):
            print(f"[PVP] Weather desconhecido: {weather_value}")
            return

        self._applying_remote_weather = True
        try:
            if hasattr(self, 'battle_system') and self.battle_system:
                self.battle_system.weather_manager.set_weather(
                    weather_type, duration, source=None)
                print(f"[PVP] Weather remoto: {weather_value} ({duration}s)")
        except Exception as e:
            print(f"[PVP] erro aplicar weather: {e}")
        finally:
            self._applying_remote_weather = False

    def _apply_remote_pokemon_attack(self, payload):
        uid = payload.get("unique_id")
        owner = payload.get("uuid")
        if owner == self._my_uuid:
            return
        pk = self._remote_pokemon.get(uid)
        if not pk:
            return
        move_name = payload.get("move_name", "tackle")
        try:
            from src.entities.move import Move
            move_info = {
                "type": "normal", "power": 40, "accuracy": 100,
                "pp": 35, "category": "physical", "description": "",
            }
            move = Move(move_name, move_info)
            target = None
            best = float('inf')
            for mine in self._local_team_objs:
                if not mine.is_alive():
                    continue
                d = (mine.x - pk.x) ** 2 + (mine.y - pk.y) ** 2
                if d < best:
                    best = d
                    target = mine
            if target:
                pk.combat._start_attack_animation(target, move)
        except Exception as e:
            print(f"[PVP] erro anim remota: {e}")

    def _apply_damage_to_my_pokemon(self, payload):
        if payload.get("owner_uuid") != self._my_uuid:
            return
        uid = payload.get("unique_id")
        damage = int(payload.get("damage", 0))
        if damage <= 0:
            return
        for p in self._local_team_objs:
            if p.unique_id == uid:
                old = p.current_hp
                p.current_hp = max(0, p.current_hp - damage)
                if p.current_hp > 0:
                    try:
                        p.play_hurt_animation()
                    except Exception:
                        pass
                if p.current_hp <= 0:
                    try:
                        p.set_defeated(True)
                    except Exception:
                        p.is_defeated = True
                print(f"[PVP] {p.name} tomou {damage} → "
                      f"{p.current_hp}/{p.max_hp}")
                break

    def _apply_status_to_my_pokemon(self, payload):
        """O oponente aplicou um status no MEU pokémon — aplica localmente
        para que os ticks (veneno/queimadura) e a paralisia funcionem."""
        if payload.get("owner_uuid") != self._my_uuid:
            return
        uid = payload.get("unique_id")
        status_type_str = payload.get("status_type")
        if not uid or not status_type_str:
            return

        from src.battle.effects import StatusType, StatusEffect

        for p in self._local_team_objs:
            if p.unique_id != uid:
                continue
            try:
                status_type = StatusType(status_type_str)
            except ValueError:
                print(f"[PVP] Status desconhecido: {status_type_str}")
                return

            em = self.battle_system.effect_manager

            if em.get_status(p):
                em.remove_status(p)

            status = StatusEffect(status_type, duration=None)
            em.apply_status(p, status, source=None)
            print(f"[PVP] Status remoto aplicado: {p.name} = {status_type_str}")
            break

    def _apply_stat_mod_to_my_pokemon(self, payload):
        """O oponente reduziu/aumentou um stat do MEU pokémon.
        Aplicamos localmente COM duração para que o modificador
        expire no lado do dono e o próximo sync propague o valor 0."""
        if payload.get("owner_uuid") != self._my_uuid:
            return
        uid = payload.get("unique_id")
        stat_name = payload.get("stat")
        stages = int(payload.get("stages", 0))
        duration = float(payload.get("duration", 0.0)) or None
        if not uid or not stat_name or stages == 0:
            return

        from src.battle.effects import StatType
        stat_map = {
            "attack": StatType.ATTACK,
            "defense": StatType.DEFENSE,
            "sp_attack": StatType.SP_ATTACK,
            "sp_defense": StatType.SP_DEFENSE,
            "speed": StatType.SPEED,
            "accuracy": StatType.ACCURACY,
            "evasion": StatType.EVASION,
        }
        st = stat_map.get(stat_name)
        if st is None:
            return

        for p in self._local_team_objs:
            if p.unique_id != uid:
                continue
            em = self.battle_system.effect_manager
            em._pvp_applying_remote = True
            try:
                # ★ Usa add_stat_modifier COM duração → expira sozinho
                em.add_stat_modifier(p, st, stages, duration)
            finally:
                em._pvp_applying_remote = False
            print(f"[PVP] Stat remoto: {p.name} {stat_name} {stages:+d} "
                  f"(dur={duration})")
            break

    def _remove_status_from_my_pokemon(self, payload):
        if payload.get("owner_uuid") != self._my_uuid:
            return
        uid = payload.get("unique_id")
        for p in self._local_team_objs:
            if p.unique_id == uid:
                em = self.battle_system.effect_manager
                if em.get_status(p):
                    em.remove_status(p)
                    print(f"[PVP] Status remoto removido: {p.name}")
                break

    # ==================================================================
    # EVENTOS
    # ==================================================================
    def handle_event(self, event):
        if self._pvp_overlay and self._pvp_overlay.active:
            if self._pvp_overlay.handle_event(event):
                return None
            return None

        if self._swap_overlay and self._swap_overlay.active:
            if self._swap_overlay.handle_event(event):
                return None
            return None

        if self.move_select_overlay and self.move_select_overlay.active:
            self.move_select_overlay.handle_event(event)
            return None

        if self.overlay_manager.is_active:
            self.overlay_manager.handle_event(event)
            return None
        if event.type == pygame.VIDEORESIZE:
            return None

        if event.type == pygame.KEYDOWN:
            if event.key == pygame.K_h:
                self.ui_hidden = not self.ui_hidden
                return None
            if event.key in (pygame.K_ESCAPE, pygame.K_p):
                self.toggle_pause()
                return None

        if self.move_quick_switch_manager.handle_event(
                event, self.camera, self.screen_manager):
            return None

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

        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            mp = pygame.mouse.get_pos()
            if not self.team_manager.is_dragging():
                if self.screen_manager.is_mouse_in_viewport(mp):
                    wp = self.screen_manager.get_mouse_world_position(
                        mp, self.camera)
                    if wp:
                        clicked = self.placement_manager.get_pokemon_at_world_pos(
                            wp[0], wp[1], tolerance=30)
                        if clicked and clicked.moves:
                            if (getattr(clicked, '_pvp_owner_uuid', None) == self._my_uuid
                                    and clicked.is_alive()
                                    and not clicked.is_defeated):
                                self.open_move_select_overlay(clicked)
                                return None

        if event.type == pygame.MOUSEWHEEL:
            mp = pygame.mouse.get_pos()
            if self.screen_manager.is_mouse_in_viewport(mp):
                self.camera.handle_zoom(event.y > 0)
                return None

        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 2:
            mp = pygame.mouse.get_pos()
            if self.screen_manager.is_mouse_in_viewport(mp):
                self.dragging_camera = True
                self.last_mouse_pos = mp
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

    def toggle_pause(self):
        from src.scenes.game_scene.components.managers.overlay_manager import OverlayType
        if self.paused:
            self.paused = False
            self.game_paused = False
            self.overlay_manager.hide()
        else:
            self.paused = True
            self.game_paused = True
            self.overlay_manager.show(OverlayType.PAUSE)

    def handle_give_up(self):
        self.paused = False
        self.game_paused = False
        self._end_battle("lose")

    def _finish_pvp_battle(self):
        try:
            from src.battle.effects.specific.weather.weather_manager import WeatherManager
            if getattr(WeatherManager, '_pvp_active_scene', None) is self:
                WeatherManager._pvp_active_scene = None
        except Exception:
            pass

        self._restore_team()
        if self._on_exit_callback:
            try:
                self._on_exit_callback()
                return
            except Exception as e:
                print(f"[PVP] callback falhou: {e}")
        try:
            from src.scenes.lobby_scene.lobby_scene import LobbyScene
            self.game.current_scene = LobbyScene(
                self.game, is_host=self._network.is_host,
                network=self._network)
        except Exception as e:
            print(f"[PVP] erro sair: {e}")

    def _restore_team(self):
        if self._original_team is not None:
            self.game.player.team = self._original_team
            self._original_team = None
            print("[PVP] Time original restaurado")

    # ==================================================================
    # OVERLAYS
    # ==================================================================
    def open_move_select_overlay(self, pokemon):
        if not pokemon or not pokemon.moves:
            return
        from src.scenes.game_scene.components.overlays.move_select_overlay import MoveSelectOverlay
        self.move_select_overlay = MoveSelectOverlay(self, pokemon)
        self.move_select_overlay.active = True

    def close_move_select_overlay(self):
        if self.move_select_overlay:
            self.move_select_overlay.active = False
            self.move_select_overlay = None

    def open_evolution_overlay(self, pokemon, evolution_data):
        print(f"[PVP] Evolução suprimida: {pokemon.name}")

    # ==================================================================
    # RENDER
    # ==================================================================
    def render(self, screen):
        screen.fill((0, 0, 0))

        self.map_renderer.render(screen, self.camera, self.screen_manager)
        if self.spot_renderer:
            self.spot_renderer.render(
                screen, self.camera, self.screen_manager,
                show_editing=False, highlight_spot=None)

        for ally in self._ally_team_objs:
            if (getattr(ally, 'is_placed', False)
                    and ally.is_alive() and not ally.is_defeated):
                ally.render(screen, self.camera, show_hp=False)
        for enemy in self._enemy_team_objs:
            if (getattr(enemy, 'is_placed', False)
                    and enemy.is_alive() and not enemy.is_defeated):
                enemy.render(screen, self.camera, show_hp=False)

        if self.placement_manager:
            self.placement_manager.render(
                screen, self.camera, self.screen_manager)

        if hasattr(self, 'battle_system'):
            self.battle_system.render_projectiles(
                screen, self.camera, self.screen_manager)

        for ally in self._ally_team_objs:
            if (getattr(ally, 'is_placed', False)
                    and ally.is_alive() and not ally.is_defeated):
                ally.render_hp_enemy(screen, self.camera)
        for enemy in self._enemy_team_objs:
            if (getattr(enemy, 'is_placed', False)
                    and enemy.is_alive() and not enemy.is_defeated):
                enemy.render_hp_enemy(screen, self.camera)

        if self.placement_manager:
            self.placement_manager.render_hp(screen, self.camera)

        viewport_rect = pygame.Rect(
            self.screen_manager.viewport_x, self.screen_manager.viewport_y,
            self.screen_manager.viewport_width,
            self.screen_manager.viewport_height)
        if hasattr(self, 'battle_system') and self.battle_system:
            weather = self.battle_system.weather_manager.current_weather
            if weather and weather.active:
                self.weather_filter.render(
                    screen, weather, viewport_rect,
                    dt=getattr(self, '_last_dt', 0.0))
            else:
                self.weather_filter.render(
                    screen, None, viewport_rect,
                    dt=getattr(self, '_last_dt', 0.0))
        if hasattr(self, 'day_night_weather'):
            dn = self.day_night_weather.day_night_state
            if dn and dn.active:
                self.day_night_filter.render(screen, dn, viewport_rect)

        if not self.ui_hidden:
            if self.team_manager:
                self.team_manager.render(
                    screen, self.camera, self.spot_renderer.get_spots())
            if self.move_quick_switch_manager:
                self.move_quick_switch_manager.render(
                    screen, self.camera, self.screen_manager)

        if self.pvp_state == "placing":
            self._render_placing_hint(screen)
        elif self.pvp_state == "countdown":
            self._render_countdown(screen)

        if self.pvp_state == "battle":
            if not (self._swap_overlay and self._swap_overlay.active):
                self._render_death_hint(screen)

        if self.overlay_manager.is_active:
            self.overlay_manager.render(screen)
        if self.move_select_overlay and self.move_select_overlay.active:
            self.move_select_overlay.render(screen)
        if self._swap_overlay and self._swap_overlay.active:
            self._swap_overlay.render(screen)
        if self._pvp_overlay and self._pvp_overlay.active:
            self._pvp_overlay.render(screen)

    def _render_placing_hint(self, screen):
        sm = self.screen_manager
        vx, vy = sm.viewport_x, sm.viewport_y
        vw = sm.viewport_width
        placed = len([
            p for p in self.placement_manager.placed_pokemon
            if getattr(p, '_pvp_owner_uuid', None) == self._my_uuid
        ])
        required = self.spots_per_player

        font = pygame.font.Font(None, 28)
        timer_left = max(0, int(math.ceil(self._placement_timer)))

        if self._local_placement_ready:
            text = f"Você está pronto!  ·  {timer_left}s"
            text_color = (105, 220, 130)
        elif timer_left <= 3:
            text = (f"Posicione seus Pokémon: {placed}/{required}  ·  "
                    f"{timer_left}s")
            text_color = (255, 90, 90)
        else:
            text = (f"Posicione seus Pokémon: {placed}/{required}  ·  "
                    f"{timer_left}s")
            text_color = (255, 215, 0)

        hint = font.render(text, True, text_color)
        shadow = font.render(text, True, (0, 0, 0))
        panel_w = max(hint.get_width() + 40, 520)
        panel = pygame.Rect(vx + (vw - panel_w) // 2, vy + 20, panel_w, 70)
        bg = pygame.Surface((panel_w, 70), pygame.SRCALPHA)
        bg.fill((0, 0, 0, 190))
        screen.blit(bg, panel)
        pygame.draw.rect(screen, text_color, panel, 2, border_radius=10)
        screen.blit(shadow, (panel.centerx - hint.get_width() // 2 + 2,
                             panel.y + 12))
        screen.blit(hint, (panel.centerx - hint.get_width() // 2, panel.y + 10))

        total_ready = len(self._remote_placement_done) + (
            1 if self._local_placement_ready else 0)
        status = pygame.font.Font(None, 18).render(
            f"Prontos: {total_ready}/{self._total_players}",
            True, (190, 200, 220))
        screen.blit(status, (panel.centerx - status.get_width() // 2,
                             panel.y + 42))

    def _render_death_hint(self, screen):
        """Avisa o PERDEDOR (eu) que posso arrastar um pokémon novo do HUD
        para o spot do pokémon morto durante a janela de 10s."""
        if not self._death_timers:
            return

        min_timer = min(self._death_timers.values())

        sm = self.screen_manager
        vx, vy = sm.viewport_x, sm.viewport_y
        vw = sm.viewport_width

        font = pygame.font.Font(None, 26)
        text = (f"Seu pokémon caiu! Arraste um novo do HUD para o "
                f"corpo ({min_timer:.1f}s)")
        hint = font.render(text, True, (255, 100, 100))
        shadow = font.render(text, True, (0, 0, 0))

        panel_w = max(hint.get_width() + 40, 680)
        panel = pygame.Rect(vx + (vw - panel_w) // 2, vy + 20, panel_w, 42)
        bg = pygame.Surface((panel_w, 42), pygame.SRCALPHA)
        bg.fill((40, 0, 0, 200))
        screen.blit(bg, panel)
        pygame.draw.rect(screen, (200, 60, 60), panel, 2, border_radius=10)
        screen.blit(shadow, (panel.centerx - hint.get_width() // 2 + 2,
                             panel.y + 10 + 2))
        screen.blit(hint, (panel.centerx - hint.get_width() // 2, panel.y + 10))

    def _render_countdown(self, screen):
        sm = self.screen_manager
        vx, vy = sm.viewport_x, sm.viewport_y
        vw, vh = sm.viewport_width, sm.viewport_height
        ov = pygame.Surface((vw, vh), pygame.SRCALPHA)
        ov.fill((0, 0, 0, 110))
        screen.blit(ov, (vx, vy))
        secs = max(1, int(math.ceil(self.pvp_countdown)))
        big = pygame.font.Font(None, 110)
        t = big.render(f"{secs}", True, (255, 80, 80))
        sh = big.render(f"{secs}", True, (0, 0, 0))
        r = t.get_rect(center=(vx + vw // 2, vy + vh // 2))
        screen.blit(sh, (r.x + 4, r.y + 4))
        screen.blit(t, r)
        sub = pygame.font.Font(None, 34)
        s = sub.render("Prepare-se para a batalha!", True, (255, 215, 0))
        screen.blit(s, s.get_rect(center=(vx + vw // 2, vy + vh // 2 + 60)))