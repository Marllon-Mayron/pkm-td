# src/scenes/raid_scene/raid_boss_manager.py
"""
Gerencia o boss de raid.
- Host: simula e é a autoridade. Broadcast do estado.
- Client (passive=True): NÃO simula combate, mas o countdown corre normalmente.
- Delay de spawn e level vêm da fase (template/wave).
- Toast de ataque do boss (local + broadcast).
"""
import math
import random
from typing import List, Optional


class _RaidSpawnerShim:
    def __init__(self):
        self.waves = {}
        self.current_wave_idx = {}
        self.wave_active = {}
        self.spawned_count = {}
        self.waves_ended = []


class RaidBossManager:
    BOSS_LEVEL_DEFAULT = 100
    ALLY_ATTACK_RANGE = 420
    BOSS_ATTACK_COOLDOWN = 2.4
    SPAWN_DELAY_DEFAULT = 10.0

    def __init__(self, game_scene, boss_config, passive=False, spawn_delay=None):
        self.game_scene = game_scene
        self.boss_config = boss_config
        self.passive = passive

        self.boss = None
        self.active_enemies = []
        self.paused = False
        self.target_items = []

        self._boss_defeated = False
        self._spawned = False
        self._death_handled = False

        # ===== DELAY: vem da fase (template/wave) =====
        if spawn_delay is None:
            spawn_delay = self.SPAWN_DELAY_DEFAULT
        self.SPAWN_DELAY = float(spawn_delay)
        self._spawn_delay = self.SPAWN_DELAY
        self._spawn_notified = False

        self._sync_timer = 0.0
        self.SYNC_INTERVAL = 0.2

        self.total_gold_earned = 0
        self.total_enemies_defeated = 0
        self.spawner = _RaidSpawnerShim()

    # ---------- API compatível ----------
    def set_paths(self, p): pass
    def set_target_items(self, i): self.target_items = i
    def initialize_condition(self): pass
    def reset_gold(self): self.total_gold_earned = 0
    def get_total_gold_earned(self): return self.total_gold_earned
    def is_wave_completely_finished(self): return self._boss_defeated and not self.active_enemies
    def is_boss_defeated(self): return self._boss_defeated
    def is_next_wave_boss(self): return False
    def has_more_waves(self): return False
    def has_active_waves(self): return False
    def is_wave_completed(self, i): return self._boss_defeated
    def is_boss_spawned(self): return self._spawned
    def get_spawn_countdown(self): return max(0.0, self._spawn_delay)

    def get_current_wave_info(self):
        if not self._spawned:
            return {
                "name": f"BOSS EM {max(0, int(math.ceil(self._spawn_delay)))}s",
                "index": "BOSS", "total": 1,
                "enemies_remaining": 0, "enemies_spawned": 0,
                "enemies_total": 1, "progress": 0.0, "active_paths": 0,
            }
        total_hp = self.boss.max_hp if self.boss else 1
        current_hp = self.boss.current_hp if self.boss else 0
        return {
            "name": "RAID BOSS", "index": "BOSS", "total": 1,
            "enemies_remaining": 1 if (self.boss and self.boss.is_alive()) else 0,
            "enemies_spawned": 1, "enemies_total": 1,
            "progress": 1.0 - (current_hp / total_hp if total_hp > 0 else 0),
            "active_paths": 1,
        }

    # ---------- SPAWN ----------
    def spawn_boss(self, broadcast=True):
        if self._spawned:
            return
        from src.scenes.raid_scene.raid_boss import RaidBoss

        world_w = self.game_scene.world_width
        world_h = self.game_scene.world_height
        spawn_x = world_w / 2
        spawn_y = max(110, world_h * 0.20)

        cfg = self.boss_config
        boss_level = cfg.get("level", self.BOSS_LEVEL_DEFAULT)

        boss = RaidBoss(
            x=spawn_x, y=spawn_y,
            pokemon_id=cfg["pokemon_id"],
            level=boss_level,
            shiny=cfg.get("shiny", False),
            hp_multiplier=cfg.get("hp_multiplier", None),
            size_multiplier=cfg.get("size_multiplier", None),
            attack_all=cfg.get("attack_all", True),
        )

        if hasattr(self.game_scene, 'screen_manager'):
            boss.screen_manager = self.game_scene.screen_manager
        if hasattr(self.game_scene, 'camera'):
            boss.camera = self.game_scene.camera
        if hasattr(self.game_scene, 'battle_system'):
            boss.set_battle_system(self.game_scene.battle_system)
            self.game_scene.battle_system.set_effect_manager_for_pokemon(boss)

        boss.is_placed = True
        boss.charge_cooldown = self.BOSS_ATTACK_COOLDOWN

        self.boss = boss
        self.active_enemies = [boss]
        self._spawned = True
        self._boost_allies_range()

        if broadcast and not self.passive:
            self._broadcast_boss_spawn()

        try:
            from src.ui.toast_renderer import toast_battle
            toast_battle(f"BOSS {boss.name} apareceu!", duration=4.0,
                         pokemon=boss, portrait="angry")
        except Exception:
            pass

        print(f"[RAID_BOSS_MANAGER] Boss {boss.name} Lv.{boss.level} spawnado em "
              f"({spawn_x:.0f}, {spawn_y:.0f}) | HP={boss.max_hp}")

    def _boost_allies_range(self):
        pm = getattr(self.game_scene, 'placement_manager', None)
        if not pm:
            return
        for ally in pm.placed_pokemon:
            ally.attack_range = self.ALLY_ATTACK_RANGE

    def apply_boss_spawn(self, payload):
        """Chamado no CLIENT quando o host manda RAID_BOSS_SPAWN."""
        from src.scenes.raid_scene.raid_boss import RaidBoss

        if self._spawned:
            return
        boss = RaidBoss(
            x=payload["x"], y=payload["y"],
            pokemon_id=payload["pokemon_id"],
            level=payload.get("level", self.BOSS_LEVEL_DEFAULT),
            shiny=payload.get("shiny", False),
            hp_multiplier=1,
            size_multiplier=payload.get("size_multiplier", None),
            attack_all=True,
        )
        boss.max_hp = payload["max_hp"]
        boss.current_hp = payload["current_hp"]

        if hasattr(self.game_scene, 'screen_manager'):
            boss.screen_manager = self.game_scene.screen_manager
        if hasattr(self.game_scene, 'camera'):
            boss.camera = self.game_scene.camera
        if hasattr(self.game_scene, 'battle_system'):
            boss.set_battle_system(self.game_scene.battle_system)
            self.game_scene.battle_system.set_effect_manager_for_pokemon(boss)

        boss.is_placed = True
        self.boss = boss
        self.active_enemies = [boss]
        self._spawned = True
        self._boost_allies_range()
        print(f"[RAID_BOSS_MANAGER] (client) Boss sincronizado: "
              f"Lv.{boss.level} HP {boss.current_hp}/{boss.max_hp}")

    # ---------- UPDATE ----------
    def update(self, dt: float) -> List['Pokemon']:
        if self.paused:
            return []

        # ===== DELAY DE SPAWN (host e client) =====
        if not self._spawned:
            if self._spawn_delay > 0:
                self._spawn_delay -= dt

            if self.passive:
                return []

            if not self._spawn_notified and self._spawn_delay <= 3.0:
                self._spawn_notified = True
                try:
                    from src.ui.toast_renderer import toast_warning
                    toast_warning("BOSS CHEGANDO EM 3s!", duration=2.5)
                except Exception:
                    pass
            if self._spawn_delay <= 0:
                self.spawn_boss(broadcast=True)
            return []

        # ===== MODO PASSIVO (client): só animação visual =====
        if self.passive:
            for boss in self.active_enemies:
                boss.animation.update(dt)
            return []

        # ===== SIMULAÇÃO DO HOST =====
        # checar morte ANTES de qualquer update, não pular boss morto.
        for boss in self.active_enemies[:]:
            # Se já morreu, chama o handler imediatamente
            if boss.is_defeated or not boss.is_alive():
                self._handle_boss_death(boss)
                continue

            # Update normal
            boss.update(dt)
            self._update_boss_combat(boss, dt)

            # Recheca (boss pode ter morrido durante o update/combate)
            if boss.is_defeated or not boss.is_alive():
                self._handle_boss_death(boss)

        # ===== BROADCAST PERIÓDICO DE HP =====
        self._sync_timer += dt
        if self._sync_timer >= self.SYNC_INTERVAL:
            self._sync_timer = 0.0
            self._broadcast_boss_sync()

        return []

    # ---------- COMBATE DO BOSS ----------
    def _update_boss_combat(self, boss, dt):
        if boss.charge_cooldown > 0:
            boss.charge_cooldown -= dt
            return
        if getattr(boss, '_attack_animation_active', False):
            return

        placed = getattr(self.game_scene.placement_manager, 'placed_pokemon', [])
        targets_in_range = []
        for ally in placed:
            if not ally.is_alive() or ally.is_defeated:
                continue
            dx = boss.x - ally.x
            dy = boss.y - ally.y
            if math.hypot(dx, dy) <= boss.attack_range:
                targets_in_range.append(ally)

        if not targets_in_range:
            boss.charge_cooldown = 0.5
            return

        boss.restore_all_pp()
        move = random.choice(boss.moves) if boss.moves else None
        if move is None:
            boss.charge_cooldown = 1.0
            return

        # Direção para o centro dos alvos
        cx = sum(t.x for t in targets_in_range) / len(targets_in_range)
        cy = sum(t.y for t in targets_in_range) / len(targets_in_range)
        boss.combat._update_direction_to_target(cx - boss.x, cy - boss.y)

        # ============================================================
        # GOLPE FÍSICO: aplica dano DIRETO (boss não anda até o alvo)
        # ============================================================
        if move.category == "physical":
            # Força este move específico a ser escolhido pelo attempt_attack:
            # zera PP dos outros temporariamente
            saved_pp = {}
            for m in boss.moves:
                saved_pp[m.name] = m.current_pp
                m.current_pp = m.max_pp if m.name == move.name else 0

            try:
                for t in targets_in_range:
                    if t and t.is_alive() and not t.is_defeated:
                        try:
                            self.game_scene.battle_system.attempt_attack(boss, t)
                            print(f"[RAID_BOSS] {boss.name} acertou {t.name} "
                                  f"(físico, sem mover)")
                        except Exception as e:
                            print(f"[RAID_BOSS] Erro ataque físico: {e}")
            finally:
                # Restaura PP de todos
                for m in boss.moves:
                    m.current_pp = saved_pp.get(m.name, m.max_pp)

            # Toca animação visual (sem re-aplicar dano pela animação)
            try:
                boss.combat._start_attack_animation(targets_in_range[0], move)
                # Marca como já aplicado para a animação NÃO chamar _execute_attack
                boss._damage_applied = True
                boss._current_multi_targets = None
            except Exception as e:
                print(f"[RAID_BOSS] Erro ao animar físico: {e}")

        # ============================================================
        # GOLPE ESPECIAL / STATUS: fluxo normal (multi-target via _execute_attack)
        # ============================================================
        else:
            boss._current_multi_targets = list(targets_in_range)
            boss._attack_all = True
            try:
                boss.combat._start_attack_animation(targets_in_range[0], move)
            except Exception as e:
                print(f"[RAID_BOSS] Erro ao animar especial: {e}")

        boss.charge_cooldown = self.BOSS_ATTACK_COOLDOWN

        # Toast local + broadcast
        self._show_boss_attack_toast(boss.name, move.name)
        self._broadcast_boss_attack(boss.name, move.name)

        print(f"[RAID_BOSS] {boss.name} usou {move.name} em "
              f"{len(targets_in_range)} alvos ({move.category})")

    # ------------------------------------------------------------------
    # TOAST DE ATAQUE DO BOSS
    # ------------------------------------------------------------------
    def _show_boss_attack_toast(self, boss_name, move_name):
        """Mostra o toast localmente (host)."""
        try:
            from src.ui.toast_renderer import toast_battle
            display = move_name.replace("-", " ").title()
            toast_battle(
                f"{boss_name} usou {display}!",
                duration=2.0,
                pokemon=self.boss,
                portrait="angry",
            )
        except Exception as e:
            print(f"[RAID_BOSS] Erro no toast: {e}")

    def _broadcast_boss_attack(self, boss_name, move_name):
        """Envia o ataque do boss para os clientes."""
        if self.passive:
            return
        net = getattr(self.game_scene, '_raid_network', None)
        if not net:
            return
        try:
            from src.network.protocol import create_message
            net.send_to_all(create_message("RAID_BOSS_ATTACK", {
                "boss_name": boss_name,
                "move_name": move_name,
            }))
        except Exception as e:
            print(f"[RAID_BOSS] Erro ao broadcast ataque: {e}")

    def apply_remote_boss_attack(self, payload):
        """Chamado no CLIENT quando o host avisa que o boss atacou."""
        boss_name = payload.get("boss_name", "BOSS")
        move_name = payload.get("move_name", "?")
        try:
            from src.ui.toast_renderer import toast_battle
            display = move_name.replace("-", " ").title()
            toast_battle(
                f"{boss_name} usou {display}!",
                duration=2.0,
                pokemon=self.boss,
                portrait="angry",
            )
        except Exception as e:
            print(f"[RAID_BOSS] Erro no toast remoto: {e}")

    # ---------- MORTE ----------
    def _handle_boss_death(self, boss):
        if self._death_handled:
            return
        self._death_handled = True
        self._boss_defeated = True

        gold = self.boss_config.get("gold_reward", 500)
        xp = self.boss_config.get("xp_reward", 300)

        placed = getattr(self.game_scene.placement_manager, 'placed_pokemon', [])
        for ally in placed:
            if ally.is_alive():
                ally.gain_xp(xp)
        if hasattr(self.game_scene, 'player'):
            self.game_scene.player.money += gold
            self.total_gold_earned = gold

        self.active_enemies.clear()

        if not self.passive:
            self._broadcast_boss_dead()

        print(f"[RAID_BOSS_MANAGER] Boss derrotado!")

    # ---------- REDE ----------
    def _broadcast_boss_spawn(self):
        net = getattr(self.game_scene, '_raid_network', None)
        if not net:
            return
        from src.network.protocol import create_message
        b = self.boss
        net.send_to_all(create_message("RAID_BOSS_SPAWN", {
            "pokemon_id": b.id,
            "x": b.x, "y": b.y,
            "level": b.level,
            "shiny": b.is_shiny,
            "size_multiplier": b._raid_size_multiplier,
            "current_hp": b.current_hp,
            "max_hp": b.max_hp,
        }))

    def _broadcast_boss_sync(self):
        net = getattr(self.game_scene, '_raid_network', None)
        if not net or not self.boss:
            return
        from src.network.protocol import create_message
        b = self.boss
        net.send_to_all(create_message("RAID_BOSS_SYNC", {
            "current_hp": b.current_hp,
            "max_hp": b.max_hp,
            "x": b.x, "y": b.y,
            "direction": getattr(b, 'current_direction', 'down'),
        }))

    def _broadcast_boss_dead(self):
        net = getattr(self.game_scene, '_raid_network', None)
        if not net:
            return
        from src.network.protocol import create_message
        net.send_to_all(create_message("RAID_BOSS_DEAD", {}))

    def apply_boss_sync(self, payload):
        if not self.boss:
            return
        self.boss.current_hp = payload["current_hp"]
        self.boss.max_hp = payload["max_hp"]
        self.boss.x = payload["x"]
        self.boss.y = payload["y"]
        direction = payload.get("direction")
        if direction:
            self.boss.current_direction = direction
            try:
                self.boss.animation._update_sprite_from_current_animation()
            except Exception:
                pass

    def apply_boss_dead(self):
        self._boss_defeated = True
        self._death_handled = True
        self.active_enemies.clear()

    def set_paused(self, p): self.paused = bool(p)
    def set_condition(self, c): pass