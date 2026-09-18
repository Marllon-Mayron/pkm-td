# src/scenes/raid_scene/raid_battle_scene.py
"""
RaidBattleScene — sync em tempo real host↔cliente (pokémons, boss, clima, ataques).

- Level e delay inicial do boss vêm da fase (template/wave).
- Cada cliente é autoridade sobre SEUS pokémons (movimento, animação, ataque).
- Host é autoridade sobre o boss (HP, ataques).
- Pokémon remotos NÃO simulam combate (só interpolam posição e tocam animação).
- Ataques de qualquer pokémon são broadcastados (RAID_POKEMON_ATTACK).
- Clima sincronizado via hook em WeatherManager.set_weather.
- Nunca dispara Game Over local (raid continua). Só game over global via RAID_ALL_DEFEATED.
"""
import math
import pygame

from src.scenes.game_scene.game_scene import GameScene
from src.scenes.raid_scene.raid_boss_manager import RaidBossManager
from src.entities.pokemon import Pokemon
from src.network.protocol import create_message
from src.scenes.raid_scene.raid_catalog import get_raid_path


class RaidBattleScene(GameScene):
    DEFAULT_BOSS_ID = 146
    DEFAULT_BOSS_LEVEL = 50
    BOSS_GOLD_REWARD = 800
    BOSS_XP_REWARD = 500
    SYNC_INTERVAL = 0.1            # 10 estados/s
    DEFEAT_CHECK_INTERVAL = 1.0    # host checa derrota 1x/s
    DEFAULT_INITIAL_DELAY = 10.0

    def __init__(self, game, is_host, network, raid_players, final_team,
                 boss_id=None, boss_level=None, initial_delay=None,
                 raid_chapter=None, raid_level=None):
        self._raid_is_host = is_host
        self._raid_network = network
        self._raid_players = raid_players
        self._raid_final_team = final_team or []
        self._raid_boss_id = boss_id or self.DEFAULT_BOSS_ID
        self._raid_boss_level = int(boss_level) if boss_level else self.DEFAULT_BOSS_LEVEL
        self._raid_initial_delay = (
            float(initial_delay) if initial_delay is not None else self.DEFAULT_INITIAL_DELAY
        )
        # ===== RAID ESPECÍFICA (pra carregar o JSON correto) =====
        self._raid_chapter = int(raid_chapter) if raid_chapter else 1
        self._raid_level = int(raid_level) if raid_level else 1

        self._raid_my_uuid = self._resolve_my_uuid(game)
        self._remote_pokemon = {}

        # Estado interno
        self._sync_timer = 0.0
        self._defeat_check_timer = 0.0
        self._local_team_dead_shown = False
        self._applying_remote_weather = False
        self.raid_game_over_overlay = None
        self.raid_victory_overlay = None
        self._raid_returning_to_lobby = False

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

        # ===== HOOKS UNIFICADOS (host + client) =====
        self._install_raid_hooks()
        # ===== HOOK DE CLIMA =====
        self._install_weather_sync_hook()

        print(f"[RAID_BATTLE] Iniciada (host={is_host}, uuid={self._raid_my_uuid[:8]})")
        print(f"[RAID_BATTLE] Raid carregada: Cap {self._raid_chapter} "
              f"Level {self._raid_level}")
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
        """Carrega o mapa da RAID ESPECÍFICA sorteada (chapter + level)."""
        import json, os
        from src.config.paths import PROJECT_ROOT
        from src.scenes.game_scene.components.phase_loader import phase_loader

        raid_path = get_raid_path(self._raid_chapter, self._raid_level)

        if not os.path.exists(raid_path):
            print(f"[RAID] AVISO: mapa de raid não encontrado: {raid_path}")
            fallback = get_raid_path(1, 1)
            if os.path.exists(fallback):
                raid_path = fallback
            else:
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
    # HOOKS UNIFICADOS (host + client)
    # ==================================================================
    def _install_raid_hooks(self):
        """
        Hooks unificados (host + client).

        _start_attack_animation: MEU pokemon atacando o boss → broadcast RAID_POKEMON_ATTACK
        _execute_attack:
            - MEU pokemon atacando o boss (HOST): attempt_attack normal
            - MEU pokemon atacando o boss (CLIENT): envia RAID_ATTACK_BOSS + projétil visual
            - Pokémon remoto: handler remoto anima
            - SEMPRE: seta charge_cooldown + retorna ao spot
        take_damage: pokémon remoto tomou dano → envia RAID_POKEMON_DAMAGE pro dono
        """
        from src.entities.pokemon.combat import PokemonCombat

        # ---------- HOOK: _start_attack_animation ----------
        if not getattr(PokemonCombat, '_raid_attack_anim_hook', False):
            original_start = PokemonCombat._start_attack_animation

            def hooked_start(self_c, target, move):
                result = original_start(self_c, target, move)

                pokemon = self_c.pokemon
                bs = getattr(pokemon, 'battle_system', None)
                scene = getattr(bs, 'game_scene', None) if bs else None
                if scene is None or not hasattr(scene, '_raid_my_uuid'):
                    return result

                if getattr(pokemon, '_is_raid_boss', False):
                    return result
                if getattr(pokemon, '_is_remote', False):
                    return result
                if getattr(pokemon, '_raid_owner_uuid', None) != scene._raid_my_uuid:
                    return result
                if not getattr(target, '_is_raid_boss', False):
                    return result

                try:
                    scene._raid_network.send_to_all(create_message(
                        "RAID_POKEMON_ATTACK",
                        {
                            "unique_id": pokemon.unique_id,
                            "owner_uuid": scene._raid_my_uuid,
                            "move_name": move.name,
                        }
                    ))
                except Exception as e:
                    print(f"[RAID] Erro ao broadcast ataque: {e}")

                return result

            PokemonCombat._start_attack_animation = hooked_start
            PokemonCombat._raid_attack_anim_hook = True

        # ---------- HOOK: _execute_attack ----------
        if not getattr(PokemonCombat, '_raid_execute_hook', False):
            original_execute = PokemonCombat._execute_attack

            def hooked_execute(self_c, target, move):
                pokemon = self_c.pokemon
                bs = getattr(pokemon, 'battle_system', None)
                scene = getattr(bs, 'game_scene', None) if bs else None

                if scene is None or not hasattr(scene, '_raid_my_uuid'):
                    return original_execute(self_c, target, move)

                if not getattr(target, '_is_raid_boss', False):
                    return original_execute(self_c, target, move)

                is_my_pokemon = (getattr(pokemon, '_raid_owner_uuid', None)
                                 == scene._raid_my_uuid)

                # Pokémon remoto: só seta cooldown local
                if not is_my_pokemon:
                    try:
                        pokemon.charge_cooldown = pokemon.charge_cooldown_max
                    except Exception:
                        pass
                    return

                # ===== É MEU pokémon atacando o boss =====
                if scene._raid_is_host:
                    try:
                        bs.attempt_attack(pokemon, target)
                    except Exception as e:
                        print(f"[RAID] Erro no attempt_attack (host): {e}")
                else:
                    try:
                        scene._raid_network.send_to_all(create_message(
                            "RAID_ATTACK_BOSS",
                            {
                                "attacker_owner_uuid": scene._raid_my_uuid,
                                "attacker_unique_id": pokemon.unique_id,
                                "attacker_name": pokemon.name,
                                "move_name": move.name,
                            }
                        ))
                    except Exception as e:
                        print(f"[RAID] Erro ao enviar ataque: {e}")

                    try:
                        if move.name.lower() != "struggle" and move.current_pp > 0:
                            move.current_pp -= 1
                    except Exception:
                        pass

                    try:
                        if move.category == "special" and move.power > 0:
                            dmg = {
                                "damage": 0, "effectiveness": 1.0, "hit": True,
                                "message": "", "stab": False, "critical": False,
                            }
                            bs._create_projectile(
                                pokemon, target, move, dmg,
                                will_hit=True, visual_only=True,
                            )
                    except Exception as e:
                        print(f"[RAID] Erro ao criar projétil local: {e}")

                # ⚠️ COOLDOWN (o que evita metralhadora)
                try:
                    pokemon.charge_cooldown = pokemon.charge_cooldown_max
                    pokemon.attack_cooldown = max(0.3, 1.0 - (pokemon.speed_stat / 500))
                except Exception as e:
                    print(f"[RAID] Erro ao setar cooldown: {e}")

                # Pós-ataque: volta ao spot
                if not pokemon.is_wild:
                    pokemon.combat_state = "returning"
                    if (pokemon.current_animation != "walk"
                            and pokemon.has_animation("walk")):
                        pokemon.set_animation("walk")
                else:
                    pokemon.combat_state = "attacking"
                    if hasattr(pokemon, '_path_tracker'):
                        pokemon._path_tracker.set_ignore_path(pokemon, 0)

                if hasattr(pokemon, '_attack_animation_active'):
                    pokemon._attack_animation_active = False

                return

            PokemonCombat._execute_attack = hooked_execute
            PokemonCombat._raid_execute_hook = True

        # ---------- HOOK: take_damage (avisa o dono de pokémons remotos) ----------
        if not getattr(PokemonCombat, '_raid_take_damage_hook', False):
            original_take = PokemonCombat.take_damage

            def hooked_take(self_c, damage, attacker=None):
                pokemon = self_c.pokemon
                old_hp = pokemon.current_hp
                result = original_take(self_c, damage, attacker)
                new_hp = pokemon.current_hp
                actual_damage = old_hp - new_hp

                # ===== Só avisa se for pokémon REMOTO e tomou dano =====
                if actual_damage > 0 and getattr(pokemon, '_is_remote', False):
                    bs = getattr(pokemon, 'battle_system', None)
                    scene = getattr(bs, 'game_scene', None) if bs else None
                    if scene is not None and hasattr(scene, '_raid_my_uuid'):
                        owner_uuid = getattr(pokemon, '_raid_owner_uuid', None)
                        if owner_uuid and owner_uuid != scene._raid_my_uuid:
                            try:
                                scene._raid_network.send_to_all(create_message(
                                    "RAID_POKEMON_DAMAGE",
                                    {
                                        "owner_uuid": owner_uuid,
                                        "unique_id": pokemon.unique_id,
                                        "damage": int(actual_damage),
                                        "attacker_name": attacker.name if attacker else "BOSS",
                                    }
                                ))
                                print(f"[RAID] Avisando dono: {pokemon.name} tomou "
                                      f"{actual_damage} (owner={owner_uuid[:8]})")
                            except Exception as e:
                                print(f"[RAID] Erro ao enviar dano: {e}")
                return result

            PokemonCombat.take_damage = hooked_take
            PokemonCombat._raid_take_damage_hook = True

        print("[RAID] Hooks de raid instalados")

    # Mantidos como no-op pra compatibilidade (caso chamados em outro lugar)
    def _install_host_hooks(self):
        pass

    def _install_client_hooks(self):
        pass

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
        # Rede sempre
        self._process_network_queue()

        # ===== OVERLAY DE VITÓRIA ATIVO =====
        if self.raid_victory_overlay and self.raid_victory_overlay.active:
            self.raid_victory_overlay.update(dt)
            self._interpolate_remote_pokemon(dt)
            return

        # ===== OVERLAY DE DERROTA ATIVO =====
        if self.raid_game_over_overlay and self.raid_game_over_overlay.active:
            self.raid_game_over_overlay.update(dt)
            self._interpolate_remote_pokemon(dt)
            return

        super().fixed_update(dt)

        # ===== INTERPOLAÇÃO DOS REMOTOS =====
        self._interpolate_remote_pokemon(dt)

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

                # Se a cena mudou durante o processamento (ex: RAID_RETURN_LOBBY),
                # parar AGORA, o resto da fila é da nova cena (LobbyScene).
                if self.game.current_scene is not self:
                    print("[RAID] Cena mudou durante processamento — "
                          "deixando o resto pra nova cena")
                    break
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

        if msg_type == "RAID_BOSS_ATTACK":
            if not self._raid_is_host:
                self.wave_manager.apply_remote_boss_attack(payload)
            return

        if msg_type == "RAID_POKEMON_ATTACK":
            self._apply_remote_pokemon_attack(payload)
            return

        if msg_type == "RAID_RETURN_LOBBY":
            who = payload.get("name", "?")
            print(f"[RAID] {who} voltou ao lobby — seguindo junto.")
            self._return_to_lobby_from_raid(broadcast=False)
            return

        if msg_type == "DISCONNECT":
            who = payload.get("name", "?")
            print(f"[RAID] {who} desconectou.")
            # Não faz sentido continuar sozinho — volta pro lobby (sem reenviar).
            self._return_to_lobby_from_raid(broadcast=False)
            return

    # ==================================================================
    # APLICAR ESTADO REMOTO
    # ==================================================================
    def _apply_remote_pokemon_state(self, payload):
        """Aplica estado de pokémons de outro jogador — só guarda a posição ALVO."""
        for state in payload.get("pokemon", []):
            uid = state.get("unique_id")
            pk = self._remote_pokemon.get(uid)
            if not pk:
                continue

            pk._target_x = float(state.get("x", pk.x))
            pk._target_y = float(state.get("y", pk.y))

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

            if not getattr(pk, '_attack_animation_active', False):
                direction = state.get("current_direction")
                if direction:
                    pk.current_direction = direction

                anim = state.get("current_animation")
                if anim and getattr(pk, 'current_animation', None) != anim:
                    if not getattr(pk, '_attack_animation_active', False):
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

            # inicializa alvo de interpolação
            pk._target_x = cx
            pk._target_y = cy

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

    def _apply_remote_pokemon_attack(self, payload):
        """Pokémon remoto começou ataque → toca animação + cria projétil."""
        uid = payload.get("unique_id")
        owner_uuid = payload.get("owner_uuid")
        move_name = payload.get("move_name")

        if owner_uuid == self._raid_my_uuid:
            return

        pk = self._remote_pokemon.get(uid)
        if not pk:
            return

        boss = self.wave_manager.boss
        if not boss:
            return

        # Acha o move
        move = None
        for m in pk.moves:
            if m.name == move_name:
                move = m
                break

        if move is None:
            try:
                from src.entities.move import Move
                move_info = {
                    "type": "normal", "power": 40, "accuracy": 100,
                    "pp": 35, "category": "physical",
                    "description": "",
                }
                move = Move(move_name, move_info)
            except Exception as e:
                print(f"[RAID] Erro ao criar move fake: {e}")
                return

        # Aponta direção para o boss
        try:
            dx = boss.x - pk.x
            dy = boss.y - pk.y
            pk.combat._update_direction_to_target(dx, dy)
        except Exception:
            pass

        # Toca animação
        try:
            pk.combat._start_attack_animation(boss, move)
        except Exception as e:
            print(f"[RAID] Erro ao animar ataque remoto: {e}")

        # Cria projétil visual se for especial
        try:
            if move.category == "special" and move.power > 0 and self.battle_system:
                dmg = {
                    "damage": 0, "effectiveness": 1.0, "hit": True,
                    "message": "", "stab": False, "critical": False,
                }
                self.battle_system._create_projectile(
                    pk, boss, move, dmg,
                    will_hit=True, visual_only=True,
                )
        except Exception as e:
            print(f"[RAID] Erro ao criar projétil remoto: {e}")

    def _interpolate_remote_pokemon(self, dt):
        """Suaviza posição dos pokémons remotos rumo ao alvo."""
        for pk in list(self._remote_pokemon.values()):
            tx = getattr(pk, '_target_x', None)
            ty = getattr(pk, '_target_y', None)
            if tx is None or ty is None:
                continue

            dx = tx - pk.x
            dy = ty - pk.y
            dist_sq = dx * dx + dy * dy

            if dist_sq > 200 * 200:
                pk.x = tx
                pk.y = ty
                pk.rect.x, pk.rect.y = int(pk.x), int(pk.y)
                continue

            lerp_factor = min(1.0, dt * 12.0)
            pk.x += dx * lerp_factor
            pk.y += dy * lerp_factor
            pk.rect.x, pk.rect.y = int(pk.x), int(pk.y)

            if dist_sq > 4:
                try:
                    pk.combat._update_direction_to_target(dx, dy)
                except Exception:
                    pass

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
        """Chamado quando o boss morre. Dá recompensas E o lendário.
        XP vai pro PLAYER (score), não pro time."""
        import random

        try:
            self._stop_all_sounds(fade_ms=1000)
        except Exception:
            pass

        if self.raid_game_over_overlay:
            self.raid_game_over_overlay.active = False

        gold = self.BOSS_GOLD_REWARD
        xp = self.BOSS_XP_REWARD

        # ===== ITENS =====
        earned_items = []
        try:
            from src.data.item_bag_catalog import item_bag_catalog
            for _ in range(random.randint(2, 4)):
                iid = random.choice([
                    "rare_candy", "ultraball", "masterball",
                    "revive", "full_heal"
                ])
                if item_bag_catalog.get_item(iid):
                    self.player.bag.add_item(iid, 1)
                    earned_items.append(iid)
        except Exception as e:
            print(f"[RAID_REWARD] Erro ao dar itens: {e}")

        # ===== GOLD =====
        try:
            self.player.money += gold
        except Exception as e:
            print(f"[RAID_REWARD] Erro ao dar gold: {e}")

        # ===== XP → SCORE DO PLAYER =====
        try:
            self.player.score += xp
            print(f"[RAID_REWARD] +{xp} XP no score do jogador")
        except Exception as e:
            print(f"[RAID_REWARD] Erro ao dar XP: {e}")

        # ===== LENDÁRIO =====
        legendary_reward = self._grant_legendary_reward()

        # ===== FELICIDADE =====
        try:
            for p in self.placement_manager.placed_pokemon:
                if not getattr(p, '_is_remote', False) and p.is_alive():
                    p.add_happiness(5, "Raid completada")
        except Exception:
            pass

        # ===== CELEBRAÇÃO =====
        try:
            self.placement_manager.start_victory_celebration()
        except Exception:
            pass

        try:
            self.player.auto_save()
        except Exception:
            pass

        boss_name = self.wave_manager.boss.name if self.wave_manager.boss else "?"

        self.phase_complete_data = {
            "base_reward": gold,
            "gold_from_defeats": 0,
            "bonus_amount": 0,
            "gold_total": gold,
            "total_xp": xp,
            "perfect_run": True,
            "stars": 3,
            "earned_items": earned_items,
            "is_raid": True,
            "raid_boss_name": boss_name,
            "legendary": legendary_reward,
        }

        self.game_state = "completed"

        from src.scenes.raid_scene.raid_victory_overlay import RaidVictoryOverlay
        self.raid_victory_overlay = RaidVictoryOverlay(self, {
            "gold": gold,
            "xp": xp,
            "items": earned_items,
            "legendary": legendary_reward,
        })
        print(f"[RAID] VITÓRIA! Recompensas exibidas.")

    def _grant_legendary_reward(self):
        """
        Cria o lendário derrotado (level 5, capture_method='event').
        """
        try:
            from src.entities.pokemon import Pokemon
            from datetime import datetime

            legendary_id = self._raid_boss_id
            if not legendary_id:
                print(f"[RAID_REWARD] AVISO: _raid_boss_id inválido")
                return None

            legendary = Pokemon(
                x=0, y=0,
                pokemon_id=legendary_id,
                level=5,
                is_wild=False,
                shiny=False,
                is_boss=False,
            )

            legendary.capture_method = "event"
            legendary.capture_date = datetime.now().isoformat()
            # Garante que não entre no time por engano
            legendary.is_in_team = False
            legendary.is_placed = False

            # ===== SEMPRE PARA A BOX =====
            destination = "box"
            try:
                self.player.add_to_box(legendary)
                print(f"[RAID_REWARD] Lendário {legendary.name} (Lv.5) enviado à BOX")
            except Exception as e:
                print(f"[RAID_REWARD] ERRO ao enviar lendário para box: {e}")
                import traceback
                traceback.print_exc()
                return None

            # ===== POKÉDEX =====
            try:
                self.player.caught_pokemon.add(legendary_id)
                self.player.register_seen(legendary_id)
            except Exception:
                pass

            return {
                "id": legendary_id,
                "name": legendary.name,
                "level": 5,
                "is_shiny": False,
                "destination": destination,
            }

        except Exception as e:
            print(f"[RAID_REWARD] Erro ao dar lendário: {e}")
            import traceback
            traceback.print_exc()
            return None

    def _return_to_lobby_from_raid(self, broadcast=True):
        """
        Volta para o LobbyScene.

        broadcast=True  → envio RAID_RETURN_LOBBY antes de sair (sou quem clicou)
        broadcast=False → fui avisado pelo parceiro, não reenvio (evita loop)
        """
        if self._raid_returning_to_lobby:
            return
        self._raid_returning_to_lobby = True

        if broadcast and self._raid_network:
            try:
                self._raid_network.send_to_all(create_message(
                    "RAID_RETURN_LOBBY",
                    {"name": self._raid_network.my_name},
                ))
                print("[RAID] Avisando parceiro: voltando ao lobby")
            except Exception as e:
                print(f"[RAID] Erro ao avisar retorno: {e}")

        try:
            from src.scenes.lobby_scene.lobby_scene import LobbyScene
            self.game.current_scene = LobbyScene(
                self.game,
                is_host=self._raid_is_host,
                network=self._raid_network,
            )
            print("[RAID] Voltando ao lobby")
        except Exception as e:
            print(f"[RAID] Erro ao voltar ao lobby: {e}")

    def handle_event(self, event):
        if self.raid_victory_overlay and self.raid_victory_overlay.active:
            if self.raid_victory_overlay.handle_event(event):
                return None
            return None

        if self.raid_game_over_overlay and self.raid_game_over_overlay.active:
            if self.raid_game_over_overlay.handle_event(event):
                return None
            return None

        if self.game_state == "game_over":
            return None

        return super().handle_event(event)

    def handle_give_up(self):
        """Desistir na raid = derrota local (sem penalidades)."""
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

        if not self.wave_manager.is_boss_spawned():
            self._render_boss_countdown(screen)

        self._render_spectator_hint(screen)

        if self.raid_victory_overlay and self.raid_victory_overlay.active:
            self.raid_victory_overlay.render(screen)
        elif self.raid_game_over_overlay and self.raid_game_over_overlay.active:
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