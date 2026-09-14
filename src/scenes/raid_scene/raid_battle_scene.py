# src/scenes/raid_scene/raid_battle_scene.py
"""
RaidBattleScene — sync em tempo real host↔cliente (pokémons, boss, clima, ataques).
- Level e delay inicial do boss vêm da fase (template/wave).
- Cada cliente é autoridade sobre SEUS pokémons.
- Host é autoridade sobre o boss.
- Nunca dispara Game Over local (raid continua). Só game over global via RAID_ALL_DEFEATED.
"""
import math
import pygame

from src.scenes.game_scene.game_scene import GameScene
from src.scenes.raid_scene.raid_boss_manager import RaidBossManager
from src.entities.pokemon import Pokemon
from src.network.protocol import create_message


class RaidBattleScene(GameScene):
    DEFAULT_BOSS_ID = 146
    DEFAULT_BOSS_LEVEL = 50
    BOSS_GOLD_REWARD = 800
    BOSS_XP_REWARD = 500
    SYNC_INTERVAL = 0.1            # 10 estados/s
    DEFEAT_CHECK_INTERVAL = 1.0    # host checa derrota 1x/s
    DEFAULT_INITIAL_DELAY = 10.0

    def __init__(self, game, is_host, network, raid_players, final_team,
                 boss_id=None, boss_level=None, initial_delay=None):
        self._raid_is_host = is_host
        self._raid_network = network
        self._raid_players = raid_players
        self._raid_final_team = final_team or []
        self._raid_boss_id = boss_id or self.DEFAULT_BOSS_ID
        self._raid_boss_level = int(boss_level) if boss_level else self.DEFAULT_BOSS_LEVEL
        self._raid_initial_delay = (
            float(initial_delay) if initial_delay is not None else self.DEFAULT_INITIAL_DELAY
        )
        self._raid_my_uuid = self._resolve_my_uuid(game)
        self._remote_pokemon = {}

        # Estado interno
        self._sync_timer = 0.0
        self._defeat_check_timer = 0.0
        self._local_team_dead_shown = False
        self._applying_remote_weather = False
        self.raid_game_over_overlay = None

        super().__init__(game, chapter_id=1, phase_number=1)

        # Callback de rede
        self._raid_network.current_scene_callback = self._on_raid_network_message

        # ===== BOSS MANAGER =====
        boss_cfg = {
            "pokemon_id": self._raid_boss_id,
            "level": self._raid_boss_level,
            "hp_multiplier": 15.0,
            "size_multiplier": 1.0,
            "attack_all": True,
            "gold_reward": self.BOSS_GOLD_REWARD,
            "xp_reward": self.BOSS_XP_REWARD,
        }
        self.wave_manager = RaidBossManager(
            self, boss_cfg,
            passive=not is_host,
            spawn_delay=self._raid_initial_delay,
        )

        self.wave_manager.set_paths(self.path_renderer.paths)
        self.wave_manager.set_target_items(self.target_item_manager.items)

        self.game_state = "in_wave"
        self._raid_boss_spawned = False

        self._setup_raid_team()

        # ===== INSTALA HOOKS =====
        if is_host:
            self._install_host_hooks()
        else:
            self._install_client_hooks()

        # ===== HOOK DE CLIMA (host e client) =====
        self._install_weather_sync_hook()

        print(f"[RAID_BATTLE] Iniciada (host={is_host}, uuid={self._raid_my_uuid[:8]})")
        print(f"[RAID_BATTLE] Boss config: level={self._raid_boss_level}, "
              f"delay={self._raid_initial_delay}s")
        print(f"[RAID_BATTLE] Time local: {[p.name for p in self.player.team]}")

    # ------------------------------------------------------------------
    def _resolve_my_uuid(self, game):
        return (
            getattr(game.player, "uuid", None)
            or getattr(self._raid_network, "my_uuid", None)
            or "unknown"
        )

    # ------------------------------------------------------------------
    # CARREGAMENTO DO MAPA
    # ------------------------------------------------------------------
    def _load_phase_data(self):
        import json, os
        from src.config.paths import PROJECT_ROOT
        from src.scenes.game_scene.components.phase_loader import phase_loader

        raid_path = os.path.join(
            PROJECT_ROOT, "src", "data", "minigames", "raid_maps", "level_01_01.json"
        )
        if not os.path.exists(raid_path):
            print(f"[RAID] AVISO: mapa de raid não encontrado: {raid_path}")
            super()._load_phase_data()
            return

        print(f"[RAID] Carregando mapa de raid: {raid_path}")
        with open(raid_path, 'r', encoding='utf-8') as f:
            data = json.load(f)

        phase_loader.current_phase_data = data
        self._phase_data = data
        base_path = PROJECT_ROOT

        self.map_renderer.load_from_data(data.get("map", {}), base_path)
        self.path_renderer.load_from_data(data.get("paths", {}))
        self.spot_renderer.load_from_data(data.get("tower_spots", {}))

        self.target_item_manager.load_from_data({"items": []})
        self.target_item_manager.items_protected = 1

        self.phase_rewards = {
            "money": self.BOSS_GOLD_REWARD,
            "experience": self.BOSS_XP_REWARD,
            "item_rewards": [], "drop_chance": 0.0,
            "max_items": 0, "template_name": None,
        }

    # ------------------------------------------------------------------
    def _setup_raid_team(self):
        self.player.team.clear()
        if not self._raid_final_team:
            return

        my_pokemons = [
            e for e in self._raid_final_team
            if e.get("owner_uuid") == self._raid_my_uuid
        ]
        if not my_pokemons:
            print(f"[RAID_BATTLE] AVISO: nenhum pokémon meu. Usando todos.")
            my_pokemons = list(self._raid_final_team)

        for entry in my_pokemons:
            pdata = entry.get("pokemon")
            if not pdata:
                continue
            try:
                pk = Pokemon.from_dict(pdata)
            except Exception as e:
                print(f"[RAID_BATTLE] Falha em {pdata.get('name')}: {e}")
                continue
            pk.is_wild = False
            pk.is_in_team = True
            pk._raid_owner_name = entry.get("owner_name", "?")
            pk._raid_owner_uuid = entry.get("owner_uuid", "?")
            pk.attack_range = RaidBossManager.ALLY_ATTACK_RANGE
            pk.reset(self)
            pk.attack_range = RaidBossManager.ALLY_ATTACK_RANGE
            self.player.team.append(pk)

        print(f"[RAID_BATTLE] {len(self.player.team)} pokémon(s) local(is)")

    def _start_game(self):
        try:
            self.day_night_filter.clear()
            self.weather_filter.clear()
        except Exception:
            pass

    # ==================================================================
    # HOOKS
    # ==================================================================
    def _install_client_hooks(self):
        """On CLIENT: nossos pokémons NÃO aplicam dano localmente no boss."""
        scene = self
        from src.entities.pokemon.combat import PokemonCombat

        if getattr(PokemonCombat, '_raid_client_hook', False):
            return

        original_execute = PokemonCombat._execute_attack

        def hooked_execute(self_c, target, move):
            pokemon = self_c.pokemon
            if (getattr(target, '_is_raid_boss', False) and
                    getattr(pokemon, '_raid_owner_uuid', None) == scene._raid_my_uuid):
                try:
                    scene._raid_network.send_to_all(create_message("RAID_ATTACK_BOSS", {
                        "attacker_owner_uuid": scene._raid_my_uuid,
                        "attacker_unique_id": pokemon.unique_id,
                        "attacker_name": pokemon.name,
                        "move_name": move.name,
                    }))
                except Exception as e:
                    print(f"[RAID] Erro ao enviar ataque: {e}")
                return
            return original_execute(self_c, target, move)

        PokemonCombat._execute_attack = hooked_execute
        PokemonCombat._raid_client_hook = True
        print("[RAID] Hooks de CLIENTE instalados")

    def _install_host_hooks(self):
        """On HOST: quando dano é aplicado a pokémon remoto, avisa o dono."""
        scene = self
        from src.entities.pokemon.combat import PokemonCombat

        if getattr(PokemonCombat, '_raid_host_hook', False):
            return

        original_take = PokemonCombat.take_damage

        def hooked_take(self_c, damage, attacker=None):
            pokemon = self_c.pokemon
            old_hp = pokemon.current_hp
            result = original_take(self_c, damage, attacker)
            new_hp = pokemon.current_hp
            actual_damage = old_hp - new_hp

            if (actual_damage > 0 and
                    getattr(pokemon, '_is_remote', False)):
                owner_uuid = getattr(pokemon, '_raid_owner_uuid', None)
                if owner_uuid and owner_uuid != scene._raid_my_uuid:
                    try:
                        scene._raid_network.send_to_all(create_message("RAID_POKEMON_DAMAGE", {
                            "owner_uuid": owner_uuid,
                            "unique_id": pokemon.unique_id,
                            "damage": int(actual_damage),
                            "attacker_name": attacker.name if attacker else "BOSS",
                        }))
                    except Exception as e:
                        print(f"[RAID] Erro ao enviar dano: {e}")
            return result

        PokemonCombat.take_damage = hooked_take
        PokemonCombat._raid_host_hook = True
        print("[RAID] Hooks de HOST instalados")

    def _install_weather_sync_hook(self):
        """Hook global em WeatherManager.set_weather."""
        from src.battle.effects.specific.weather.weather_manager import WeatherManager

        if getattr(WeatherManager, '_raid_weather_hook', False):
            return

        scene = self
        original_set_weather = WeatherManager.set_weather

        def hooked_set_weather(self_wm, weather_type, duration, source=None):
            result = original_set_weather(self_wm, weather_type, duration, source=source)

            if getattr(scene, '_applying_remote_weather', False):
                return result

            try:
                weather_value = (
                    weather_type.value if hasattr(weather_type, 'value')
                    else str(weather_type)
                )
                scene._raid_network.send_to_all(create_message("RAID_WEATHER_CHANGE", {
                    "weather_value": weather_value,
                    "duration": float(duration),
                }))
                print(f"[RAID] Weather broadcast: {weather_value} ({duration}s)")
            except Exception as e:
                print(f"[RAID] Erro ao enviar weather: {e}")

            return result

        WeatherManager.set_weather = hooked_set_weather
        WeatherManager._raid_weather_hook = True
        print("[RAID] Hook de clima instalado")

    # ==================================================================
    # FIXED_UPDATE
    # ==================================================================
    def fixed_update(self, dt):
        self._process_network_queue()

        # Atualiza overlay de derrota (se ativo)
        if self.raid_game_over_overlay and self.raid_game_over_overlay.active:
            self.raid_game_over_overlay.update(dt)
            return  # congela o jogo por baixo

        super().fixed_update(dt)

        # Sync periódico do meu time
        self._sync_timer += dt
        if self._sync_timer >= self.SYNC_INTERVAL:
            self._sync_timer = 0.0
            self._broadcast_my_pokemon_state()

        # Host: checa derrota global + vitória
        if self._raid_is_host:
            self._defeat_check_timer += dt
            if self._defeat_check_timer >= self.DEFEAT_CHECK_INTERVAL:
                self._defeat_check_timer = 0.0
                self._check_raid_defeat()

            if not self._raid_boss_spawned and self.wave_manager.is_boss_spawned():
                self._raid_boss_spawned = True
            if self.wave_manager.is_boss_defeated() and self.game_state != "completed":
                self._trigger_raid_victory()

    def _process_network_queue(self):
        net = self._raid_network
        if not net:
            return
        try:
            while not net.incoming_queue.empty():
                item = net.incoming_queue.get_nowait()
                if isinstance(item, tuple) and len(item) == 2:
                    msg, _ = item
                else:
                    msg = item
                self._on_raid_network_message(msg, None)
        except Exception as e:
            print(f"[RAID] Erro na fila: {e}")

    # ==================================================================
    # BROADCAST
    # ==================================================================
    def _broadcast_my_pokemon_state(self):
        net = self._raid_network
        if not net:
            return
        states = []
        for p in self.player.team:
            states.append({
                "unique_id": p.unique_id,
                "current_hp": int(p.current_hp),
                "max_hp": int(p.max_hp),
                "x": float(p.x),
                "y": float(p.y),
                "current_animation": getattr(p, 'current_animation', 'idle'),
                "current_direction": getattr(p, 'current_direction', 'down'),
                "combat_state": getattr(p, 'combat_state', 'idle'),
                "is_defeated": bool(getattr(p, 'is_defeated', False)),
            })
        try:
            net.send_to_all(create_message("RAID_POKEMON_STATE", {
                "owner_uuid": self._raid_my_uuid,
                "pokemon": states,
            }))
        except Exception as e:
            print(f"[RAID] Erro ao enviar state: {e}")

    # ==================================================================
    # RECEBIMENTO DE REDE
    # ==================================================================
    def _on_raid_network_message(self, msg, conn=None):
        msg_type = msg.get("type")
        payload = msg.get("payload", {})

        if msg_type == "RAID_BOSS_SPAWN":
            if not self._raid_is_host:
                self.wave_manager.apply_boss_spawn(payload)
                try:
                    from src.ui.toast_renderer import toast_battle
                    toast_battle("BOSS apareceu!", duration=3.0)
                except Exception:
                    pass
            return

        if msg_type == "RAID_BOSS_SYNC":
            if not self._raid_is_host:
                self.wave_manager.apply_boss_sync(payload)
            return

        if msg_type == "RAID_BOSS_DEAD":
            if not self._raid_is_host:
                self.wave_manager.apply_boss_dead()
                if self.game_state != "completed":
                    self._trigger_raid_victory()
            return

        if msg_type == "RAID_PLACEMENT":
            self._apply_remote_placement(payload)
            return

        if msg_type == "RAID_POKEMON_STATE":
            if payload.get("owner_uuid") != self._raid_my_uuid:
                self._apply_remote_pokemon_state(payload)
            return

        if msg_type == "RAID_ATTACK_BOSS":
            if self._raid_is_host:
                self._apply_remote_attack_on_host(payload)
            return

        if msg_type == "RAID_POKEMON_DAMAGE":
            if payload.get("owner_uuid") == self._raid_my_uuid:
                self._apply_damage_to_my_pokemon(payload)
            return

        if msg_type == "RAID_ALL_DEFEATED":
            if self.game_state not in ("game_over", "completed"):
                self._show_raid_defeat()
            return

        if msg_type == "RAID_WEATHER_CHANGE":
            self._apply_remote_weather(payload)
            return

        # ===== ATAQUE DO BOSS (só client recebe) =====
        if msg_type == "RAID_BOSS_ATTACK":
            if not self._raid_is_host:
                self.wave_manager.apply_remote_boss_attack(payload)
            return

        if msg_type == "DISCONNECT":
            who = payload.get("name", "?")
            print(f"[RAID] {who} desconectou.")

    # ==================================================================
    # APLICAR ESTADO REMOTO
    # ==================================================================
    def _apply_remote_pokemon_state(self, payload):
        for state in payload.get("pokemon", []):
            uid = state.get("unique_id")
            pk = self._remote_pokemon.get(uid)
            if not pk:
                continue
            pk.x = state.get("x", pk.x)
            pk.y = state.get("y", pk.y)
            pk.current_hp = state.get("current_hp", pk.current_hp)
            pk.max_hp = state.get("max_hp", pk.max_hp)
            if state.get("is_defeated"):
                if not getattr(pk, 'is_defeated', False):
                    try:
                        pk.set_defeated(True)
                    except Exception:
                        pk.is_defeated = True
            else:
                pk.is_defeated = False

            direction = state.get("current_direction")
            if direction:
                pk.current_direction = direction
            anim = state.get("current_animation")
            if anim and getattr(pk, 'current_animation', None) != anim:
                try:
                    pk.set_animation_direct(anim)
                except Exception:
                    pass
            cs = state.get("combat_state")
            if cs:
                pk.combat_state = cs

    # ==================================================================
    # HOST: aplicar ataque remoto no boss
    # ==================================================================
    def _apply_remote_attack_on_host(self, payload):
        uid = payload.get("attacker_unique_id")
        move_name = payload.get("move_name")
        boss = self.wave_manager.boss
        if not boss or not boss.is_alive():
            return

        attacker = None
        for p in self.placement_manager.placed_pokemon:
            if p.unique_id == uid:
                attacker = p
                break
        if not attacker or not attacker.is_alive():
            return

        move = None
        for m in attacker.moves:
            if m.name == move_name:
                move = m
                break
        if not move:
            return

        try:
            result = self.battle_system._calculate_move_damage(attacker, boss, move)
            if result.get("hit") and result.get("damage", 0) > 0:
                self.battle_system._apply_damage(attacker, boss, result, move)
                self.battle_system._apply_move_effect(attacker, boss, move, result["damage"])
                if move.current_pp > 0:
                    move.current_pp -= 1
                print(f"[RAID] Ataque remoto: {attacker.name} → boss "
                      f"({result['damage']} dano)")
        except Exception as e:
            print(f"[RAID] Erro ao aplicar ataque remoto: {e}")

    # ==================================================================
    # CLIENTE: aplicar dano vindo do host
    # ==================================================================
    def _apply_damage_to_my_pokemon(self, payload):
        if payload.get("owner_uuid") != self._raid_my_uuid:
            return
        uid = payload.get("unique_id")
        damage = int(payload.get("damage", 0))
        if damage <= 0:
            return
        for p in self.player.team:
            if p.unique_id == uid:
                old = p.current_hp
                p.current_hp = max(0, p.current_hp - damage)
                actual = old - p.current_hp
                try:
                    if actual > 0 and p.current_hp > 0:
                        p.play_hurt_animation()
                except Exception:
                    pass
                if p.current_hp <= 0:
                    try:
                        p.set_defeated(True)
                    except Exception:
                        p.is_defeated = True
                print(f"[RAID] {p.name} tomou {actual} do BOSS → "
                      f"{p.current_hp}/{p.max_hp}")
                break

    # ==================================================================
    # CLIMA REMOTO
    # ==================================================================
    def _apply_remote_weather(self, payload):
        from src.battle.effects.specific.weather.weather_state import WeatherType

        weather_value = payload.get("weather_value")
        duration = float(payload.get("duration", 30.0))
        if not weather_value:
            return

        try:
            weather_type = WeatherType(weather_value)
        except (ValueError, KeyError):
            print(f"[RAID] Weather desconhecido: {weather_value}")
            return

        self._applying_remote_weather = True
        try:
            if hasattr(self, 'battle_system') and self.battle_system:
                self.battle_system.weather_manager.set_weather(
                    weather_type, duration, source=None
                )
                print(f"[RAID] Weather remoto aplicado: {weather_value} ({duration}s)")
        except Exception as e:
            print(f"[RAID] Erro ao aplicar weather remoto: {e}")
        finally:
            self._applying_remote_weather = False

    # ==================================================================
    # PLACEMENT REMOTO
    # ==================================================================
    def _apply_remote_placement(self, payload):
        owner_uuid = payload.get("owner_uuid")
        if owner_uuid == self._raid_my_uuid:
            return

        action = payload.get("action", "place")
        spot_x = payload.get("spot_x")
        spot_y = payload.get("spot_y")
        unique_id = payload.get("unique_id")
        ts = self.placement_manager.tile_size

        if action == "remove":
            rp = self._remote_pokemon.pop(unique_id, None)
            if rp and rp in self.placement_manager.placed_pokemon:
                self.placement_manager.placed_pokemon.remove(rp)
                for s in self.spot_renderer.get_spots():
                    if s.x // ts == spot_x // ts and s.y // ts == spot_y // ts:
                        s.occupied = False
                        break
            return

        if action in ("place", "move"):
            old = self._remote_pokemon.get(unique_id)
            if old and old in self.placement_manager.placed_pokemon:
                self.placement_manager.placed_pokemon.remove(old)

            pk = None
            if action == "place":
                pdata = payload.get("pokemon_data")
                if not pdata:
                    return
                try:
                    pk = Pokemon.from_dict(pdata)
                except Exception as e:
                    print(f"[RAID] Erro criar remoto: {e}")
                    return
            else:
                pk = old
                if not pk:
                    return

            pk.is_wild = False
            pk.is_in_team = False
            pk.is_placed = True
            pk._is_remote = True
            pk._raid_owner_name = payload.get("owner_name", "?")
            pk._raid_owner_uuid = owner_uuid

            cx = (spot_x // ts) * ts + ts // 2
            cy = (spot_y // ts) * ts + ts // 2
            pk.x, pk.y = cx, cy
            pk.original_spot_x = cx
            pk.original_spot_y = cy
            pk.placed_tile_x = cx // ts
            pk.placed_tile_y = cy // ts

            if hasattr(self, 'screen_manager'):
                pk.screen_manager = self.screen_manager
            if hasattr(self, 'camera'):
                pk.camera = self.camera
            if hasattr(self, 'battle_system'):
                pk.set_battle_system(self.battle_system)
                self.battle_system.set_effect_manager_for_pokemon(pk)
            pk.attack_range = RaidBossManager.ALLY_ATTACK_RANGE

            self._remote_pokemon[unique_id] = pk
            self.placement_manager.placed_pokemon.append(pk)

            for s in self.spot_renderer.get_spots():
                if s.x // ts == spot_x // ts and s.y // ts == spot_y // ts:
                    s.occupied = True
                    break

            print(f"[RAID] Remote {pk.name} de {pk._raid_owner_name} em ({cx},{cy})")

    def _broadcast_my_placement(self, pokemon, spot, action="place"):
        net = self._raid_network
        if not net:
            return
        try:
            pdata = pokemon.to_dict()
        except Exception:
            pdata = None

        payload = {
            "action": action,
            "owner_uuid": self._raid_my_uuid,
            "owner_name": getattr(self.player, "name", "?"),
            "unique_id": pokemon.unique_id,
            "spot_x": spot.x if spot else 0,
            "spot_y": spot.y if spot else 0,
        }
        if action == "place" and pdata:
            payload["pokemon_data"] = pdata
        net.send_to_all(create_message("RAID_PLACEMENT", payload))

    def _on_pokemon_placed(self, placement_data):
        action = placement_data.get('action', 'place')
        super()._on_pokemon_placed(placement_data)

        pokemon = placement_data.get('pokemon')
        spot = placement_data.get('spot') or placement_data.get('to_spot')

        if action == 'place':
            self._broadcast_my_placement(pokemon, spot, "place")
        elif action == 'move':
            self._broadcast_my_placement(pokemon, spot, "move")
        elif action == 'swap':
            spot_a = placement_data.get('spot_a')
            spot_b = placement_data.get('spot_b')
            p_a = placement_data.get('pokemon_a')
            p_b = placement_data.get('pokemon_b')
            if p_a and spot_b:
                self._broadcast_my_placement(p_a, spot_b, "move")
            if p_b and spot_a:
                self._broadcast_my_placement(p_b, spot_a, "move")

    # ==================================================================
    # OVERLAYS SEM PAUSA
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

    def open_move_learn_overlay(self, pokemon, new_move_name):
        from src.scenes.game_scene.components.overlays.move_learn_overlay import MoveLearnOverlay
        self.move_learn_overlay = MoveLearnOverlay(self, pokemon, new_move_name)
        self.move_learn_overlay.active = True

    def close_move_learn_overlay(self, cancel=False):
        if self.move_learn_overlay:
            self.move_learn_overlay.active = False
            self.move_learn_overlay = None
        if not cancel and hasattr(self, 'pending_tm_data') and self.pending_tm_data:
            self.pending_tm_data = None

    # ==================================================================
    # GAME OVER
    # ==================================================================
    def is_team_defeated(self) -> bool:
        """Override: NUNCA dispara game over local."""
        if not self.player.team:
            return False

        local_alive = any(p.is_alive() for p in self.player.team)
        if not local_alive and not self._local_team_dead_shown:
            self._local_team_dead_shown = True
            try:
                from src.ui.toast_renderer import toast_warning
                toast_warning("Sua equipe caiu! Você é espectador.", duration=5.0)
            except Exception:
                pass
            print("[RAID] Equipe local derrotada — modo espectador")

        return False

    def _check_raid_defeat(self):
        if not self._raid_is_host:
            return
        if self.game_state in ("game_over", "completed"):
            return
        if not self._raid_boss_spawned:
            return

        local_alive = any(p.is_alive() for p in self.player.team)

        remote_alive = False
        for p in self.placement_manager.placed_pokemon:
            if getattr(p, '_is_remote', False) and p.is_alive():
                remote_alive = True
                break

        if not local_alive and not remote_alive:
            print("[RAID] DERROTA GLOBAL — todos os pokémons caíram")
            try:
                self._raid_network.send_to_all(create_message("RAID_ALL_DEFEATED", {}))
            except Exception:
                pass
            self._show_raid_defeat()

    def _show_raid_defeat(self):
        """Mostra o overlay de derrota EXCLUSIVO da raid (não usa OverlayManager)."""
        if self.game_state == "game_over":
            return

        self.game_state = "game_over"

        # Para sons sem remover gold nem felicidade
        try:
            self._stop_all_sounds(fade_ms=1000)
        except Exception:
            pass

        from src.scenes.raid_scene.raid_game_over_overlay import RaidGameOverOverlay
        self.raid_game_over_overlay = RaidGameOverOverlay(self)
        print("[RAID] Overlay de derrota da raid ativado (sem penalidades)")

    # ==================================================================
    # VITÓRIA
    # ==================================================================
    def _trigger_raid_victory(self):
        if self.game_state == "completed":
            return
        self.game_state = "completed"
        self._complete_phase()

    def _complete_phase(self):
        from src.scenes.game_scene.components.managers.overlay_manager import OverlayType
        import random

        self._stop_all_sounds(fade_ms=1000)
        gold = self.BOSS_GOLD_REWARD
        xp = self.BOSS_XP_REWARD

        earned_items = []
        try:
            from src.data.item_bag_catalog import item_bag_catalog
            for _ in range(random.randint(2, 4)):
                iid = random.choice(["rare_candy", "ultraball", "masterball",
                                     "revive", "full_heal"])
                if item_bag_catalog.get_item(iid):
                    self.player.bag.add_item(iid, 1)
                    earned_items.append(iid)
        except Exception:
            pass

        self.player.auto_save()
        boss_name = self.wave_manager.boss.name if self.wave_manager.boss else "?"

        self.phase_complete_data = {
            "base_reward": gold, "gold_from_defeats": 0, "bonus_amount": 0,
            "gold_total": gold, "total_xp": xp, "perfect_run": True, "stars": 3,
            "earned_items": earned_items, "is_raid": True, "raid_boss_name": boss_name,
        }
        self.game_state = "completed"
        self.overlay_manager.show(OverlayType.PHASE_COMPLETE)

    def _return_to_lobby_from_raid(self):
        """Volta para o LobbyScene (não para seleção de time)."""
        try:
            from src.scenes.lobby_scene.lobby_scene import LobbyScene
            self.game.current_scene = LobbyScene(
                self.game,
                is_host=self._raid_is_host,
                network=self._raid_network,
            )
            print("[RAID] Voltando ao lobby após derrota")
        except Exception as e:
            print(f"[RAID] Erro ao voltar ao lobby: {e}")

    def handle_event(self, event):
        # Se o overlay de derrota da raid estiver ativo, prioriza ele
        if self.raid_game_over_overlay and self.raid_game_over_overlay.active:
            if self.raid_game_over_overlay.handle_event(event):
                return None
            return None  # bloqueia outros eventos enquanto o overlay está aberto

        # Se o jogo já está em game_over, bloqueia tudo
        if self.game_state == "game_over":
            return None

        return super().handle_event(event)

    def handle_give_up(self):
        """Desistir na raid = derrota local (mas NÃO remove gold nem felicidade)."""
        print("[RAID] Jogador desistiu da raid")
        try:
            self._stop_all_sounds(fade_ms=1000)
        except Exception:
            pass

        self.game_state = "game_over"
        from src.scenes.raid_scene.raid_game_over_overlay import RaidGameOverOverlay
        self.raid_game_over_overlay = RaidGameOverOverlay(self)

    # ==================================================================
    # RENDER
    # ==================================================================
    def render(self, screen):
        super().render(screen)

        # Countdown do boss (antes do spawn)
        if not self.wave_manager.is_boss_spawned():
            self._render_boss_countdown(screen)

        # Hint de espectador
        self._render_spectator_hint(screen)

        # Overlay de derrota da raid (por cima de tudo)
        if self.raid_game_over_overlay and self.raid_game_over_overlay.active:
            self.raid_game_over_overlay.render(screen)

    def _render_spectator_hint(self, screen):
        if not self._local_team_dead_shown:
            return
        vx = self.screen_manager.viewport_x
        vw = self.screen_manager.viewport_width
        vy = self.screen_manager.viewport_y
        font = pygame.font.Font(None, 34)
        txt = font.render("ESPECTADOR — sua equipe caiu", True, (255, 100, 100))
        shadow = font.render("ESPECTADOR — sua equipe caiu", True, (0, 0, 0))
        rect = txt.get_rect(center=(vx + vw // 2, vy + 40))
        screen.blit(shadow, (rect.x + 2, rect.y + 2))
        screen.blit(txt, rect)

    def _render_boss_countdown(self, screen):
        vx = self.screen_manager.viewport_x
        vy = self.screen_manager.viewport_y
        vw = self.screen_manager.viewport_width
        vh = self.screen_manager.viewport_height

        overlay = pygame.Surface((vw, vh), pygame.SRCALPHA)
        overlay.fill((0, 0, 0, 110))
        screen.blit(overlay, (vx, vy))

        remaining = int(math.ceil(self.wave_manager.get_spawn_countdown()))
        font_big = pygame.font.Font(None, 96)
        txt = font_big.render(f"BOSS EM {remaining}s", True, (255, 80, 80))
        rect = txt.get_rect(center=(vx + vw // 2, vy + vh // 2 - 30))
        shadow = font_big.render(f"BOSS EM {remaining}s", True, (0, 0, 0))
        screen.blit(shadow, (rect.x + 4, rect.y + 4))
        screen.blit(txt, rect)

        font_small = pygame.font.Font(None, 34)
        hint = font_small.render("Posicione seus Pokémon nos spots!", True, (255, 215, 0))
        screen.blit(hint, hint.get_rect(center=(vx + vw // 2, vy + vh // 2 + 50)))

        placed_count = len([p for p in self.placement_manager.placed_pokemon
                            if not getattr(p, '_is_remote', False)])
        total_count = len(self.player.team)
        font_info = pygame.font.Font(None, 28)
        info = font_info.render(f"Seus colocados: {placed_count}/{total_count}",
                                True, (200, 200, 230))
        screen.blit(info, info.get_rect(center=(vx + vw // 2, vy + vh // 2 + 95)))