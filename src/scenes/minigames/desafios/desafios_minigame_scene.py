# src/scenes/minigames/desafios/desafios_minigame_scene.py
"""
DesafiosMinigameScene — Boss Snorlax.

Fluxo:
  1) Player coloca seus pokémon nos spots (placement herdado).
  2) Countdown → batalha.
  3) Snorlax spawna NO PATH definido no JSON.
  4) Ciclo: Headbutt → Tackle → Amnesia → Headbutt → REST.
  5) Ao usar Rest, HP cheio, dorme. Só acorda com Poké Flute arrastada
     da bag. Aviso persistente aparece enquanto ele dorme.
  6) Ao derrotar o Snorlax, vitória + prêmio Snorlax Lv.5 na Box.

PRÊMIO:
  Ao vencer, entrega um Snorlax Lv.5 na PC Box (mesmo padrão do Dojo/
  Tyrogue). O overlay mostra o portrait + nome + tipos.

TOASTS:
  O ArenaBattleScene NÃO inicializa notification_manager. Aqui fazemos
  isso manualmente + update/render pra que os toasts de ataque apareçam.
"""
import json
import os
import math

import pygame

from src.scenes.arena_scene.arena_battle_scene import ArenaBattleScene
from src.config.paths import PROJECT_ROOT


# =====================================================================
# CONSTANTES DO PRÊMIO
# =====================================================================
_SNORLAX_REWARD_LEVEL = 5


class DesafiosMinigameScene(ArenaBattleScene):
    BOSS_LEVEL = 47
    BOSS_ID = 143  # Snorlax

    # -----------------------------------------------------------------
    def __init__(self, game, chapter_id=1, phase_number=1, on_exit=None):
        self._desafio_chapter = int(chapter_id)
        self._desafio_phase = int(phase_number)

        self.day_night_mode = "day"
        self.base_weather = "none"

        self._snorlax = None
        self._sleep_toast_timer = 0.0

        # ===== PRÊMIO =====
        self._snorlax_reward_obj = None

        # Time do jogador
        player_data = []
        try:
            for p in game.player.team:
                if p.is_alive():
                    player_data.append(p.to_dict())
        except Exception as e:
            print(f"[DESAFIOS] Erro ao montar time: {e}")

        trainer_data = {
            "name": "Snorlax",
            "difficulty": "hard",
            "reward_money": 500,
            "reward_xp": 300,
        }

        super().__init__(
            game,
            player_team_data=player_data,
            enemy_team_data=[],
            arena_chapter=self._desafio_chapter,
            arena_level=self._desafio_phase,
            enemy_is_npc=False,
            trainer_data=trainer_data,
            on_exit=on_exit,
        )

        # ===== NOTIFICATION MANAGER (a Arena não inicializa) =====
        # Sem isso, os toasts de ataque do boss não aparecem.
        from src.managers.notification_manager import notification_manager
        self.notification_manager = notification_manager

        for p in self._local_team_objs:
            p._arena_no_return = False
            p.attack_range = self.ALLY_ATTACK_RANGE

        print(f"[DESAFIOS] Iniciado | {len(self._local_team_objs)} pokémon")

    # =================================================================
    # MAPA
    # =================================================================
    def _load_arena_map(self):
        path = os.path.join(
            PROJECT_ROOT, "src", "data", "minigames", "desafios",
            f"level_{self._desafio_chapter:02d}_{self._desafio_phase:02d}.json"
        )

        if not os.path.exists(path):
            print(f"[DESAFIOS] AVISO: JSON não encontrado: {path}")
            return

        try:
            with open(path, "r", encoding="utf-8") as f:
                data = json.load(f)
        except Exception as e:
            print(f"[DESAFIOS] Erro ao ler JSON: {e}")
            return

        self.day_night_mode = data.get("day_night_mode", "day") or "day"
        self.base_weather   = data.get("base_weather",   "none") or "none"
        print(f"[DESAFIOS] Dia/Noite='{self.day_night_mode}' | "
              f"Clima='{self.base_weather}'")

        self.map_renderer.load_from_data(data.get("map", {}), PROJECT_ROOT)
        self.path_renderer.load_from_data(data.get("paths", {}))
        self.spot_renderer.load_from_data(data.get("tower_spots", {}))
        self._phase_data = data

        print(f"[DESAFIOS] Mapa carregado: {self.map_renderer.get_dimensions()} "
              f"| {len(self.spot_renderer.get_spots())} spot(s)")

    # =================================================================
    # TIMES
    # =================================================================
    def _setup_teams(self):
        spots = self.spot_renderer.get_spots()
        self._player_spots = list(spots)
        self._enemy_spots = []
        self.spot_renderer.spot_manager.spots = self._player_spots

        max_players = len(self._player_spots) or 6
        player_data = self._player_team_data[:max_players]

        self._local_team_objs = self._build_team(player_data)
        self._enemy_team_objs = []

        for p in self._local_team_objs:
            p.charge_cooldown_max = self.PVP_COOLDOWN
            p.attack_cooldown_max = self.PVP_COOLDOWN
            p.attack_range = self.ALLY_ATTACK_RANGE

        print(f"[DESAFIOS] {len(self._player_spots)} spot(s) | "
              f"{len(self._local_team_objs)} pokémon")

    def _place_next_enemy_if_needed(self):
        return

    # =================================================================
    # SPAWN no path
    # =================================================================
    def _get_boss_spawn_position(self):
        try:
            paths = getattr(self.path_renderer, 'paths', None) or []
            if paths:
                nodes = getattr(paths[0], 'nodes', None) or []
                if nodes:
                    node = nodes[0]
                    if isinstance(node, (list, tuple)) and len(node) >= 2:
                        return float(node[0]), float(node[1])
                    if isinstance(node, dict):
                        return (float(node.get('x', 180)),
                                float(node.get('y', 12)))
        except Exception as e:
            print(f"[DESAFIOS] Erro ao ler path node: {e}")

        return self.world_width / 2, max(120, self.world_height * 0.15)

    # =================================================================
    # BATALHA
    # =================================================================
    def _start_battle(self):
        self.arena_state = "battle"
        self._battle_elapsed = 0.0

        for p in self.placement_manager.placed_pokemon:
            if p.is_alive():
                p.combat_state = "attacking"

        from src.scenes.minigames.desafios.snorlax_boss import SnorlaxBoss

        bx, by = self._get_boss_spawn_position()
        print(f"[DESAFIOS] Spawnando Snorlax em ({bx:.0f}, {by:.0f}) — path do JSON")

        boss = SnorlaxBoss(
            x=bx, y=by,
            pokemon_id=self.BOSS_ID,
            level=self.BOSS_LEVEL,
            hp_multiplier=14,
            size_multiplier=1.25,
            attack_all=True,
        )

        boss.screen_manager = self.screen_manager
        boss.camera = self.camera
        boss.game_scene = self
        boss.set_battle_system(self.battle_system)
        self.battle_system.set_effect_manager_for_pokemon(boss)

        boss.is_placed = True
        boss.charge_cooldown = 2.5

        self._snorlax = boss
        if boss not in self.wave_manager.active_enemies:
            self.wave_manager.active_enemies.append(boss)

        print(f"[DESAFIOS] BOSS Snorlax Lv.{boss.level} | HP={boss.max_hp}")

        self._toast(
            f"SNORLAX Lv.{boss.level} apareceu! HP: {boss.max_hp}",
            boss, "angry", 4.0,
        )

    # =================================================================
    # UPDATE
    # =================================================================
    def fixed_update(self, dt):
        # Atualiza os toasts (fade, expiração)
        if getattr(self, 'notification_manager', None):
            try:
                self.notification_manager.update(dt)
            except Exception:
                pass

        return super().fixed_update(dt)

    def _update_battle(self, dt):
        self._battle_elapsed += dt

        self.wave_manager.update(dt)
        self.placement_manager.update(dt, self.wave_manager.active_enemies)

        boss = self._snorlax
        if boss and boss.is_alive() and not boss.is_defeated:

            if boss._snorlax_sleeping:
                boss.update(dt)
                self._sleep_toast_timer -= dt
                if self._sleep_toast_timer <= 0:
                    self._sleep_toast_timer = 3.0
                    self._toast(
                        "Snorlax está DORMINDO! Arraste a POKE FLUTE!",
                        boss, "normal", 2.0,
                    )
            else:
                boss.update(dt)
                self._update_snorlax_combat(dt, boss)

        for enemy in self.wave_manager.active_enemies:
            if enemy is boss:
                continue
            if enemy.is_alive() and not enemy.is_defeated:
                enemy.update(dt)
                enemy.update_combat(dt, self.placement_manager.placed_pokemon)

        if self._battle_elapsed > 1.0:
            self._check_desafio_end()

    # -----------------------------------------------------------------
    def _update_snorlax_combat(self, dt, boss):
        if boss.charge_cooldown > 0:
            boss.charge_cooldown -= dt
            return
        if getattr(boss, '_attack_animation_active', False):
            return

        placed = self.placement_manager.placed_pokemon
        targets = []
        for ally in placed:
            if not ally.is_alive() or ally.is_defeated:
                continue
            dx = boss.x - ally.x
            dy = boss.y - ally.y
            if (dx * dx + dy * dy) ** 0.5 <= boss.attack_range:
                targets.append(ally)

        if not targets:
            boss.charge_cooldown = 0.6
            return

        move = boss.get_next_attack_move()
        if move is None:
            boss.charge_cooldown = 1.0
            return

        cx = sum(t.x for t in targets) / len(targets)
        cy = sum(t.y for t in targets) / len(targets)
        try:
            boss.combat._update_direction_to_target(cx - boss.x, cy - boss.y)
        except Exception:
            pass

        # ===== REST =====
        if move.name.lower() == "rest":
            self._trigger_snorlax_rest(boss, move)
            boss.charge_cooldown = 3.0
            return

        # ===== ATAQUE NORMAL =====
        saved_pp = {}
        for m in boss.moves:
            saved_pp[m.name] = m.current_pp
            m.current_pp = m.max_pp if m.name == move.name else 0

        try:
            for t in targets:
                if t and t.is_alive() and not t.is_defeated:
                    try:
                        self.battle_system.attempt_attack(boss, t)
                    except Exception as e:
                        print(f"[DESAFIOS] Erro attack: {e}")
        finally:
            for m in boss.moves:
                m.current_pp = saved_pp.get(m.name, m.max_pp)

        try:
            boss.combat._start_attack_animation(targets[0], move)
            boss._damage_applied = True
            boss._current_multi_targets = None
        except Exception:
            pass

        boss.charge_cooldown = 2.4

        # ===== TOAST DO GOLPE =====
        display = move.name.replace("-", " ").title()
        self._toast(
            f"{boss.name} usou {display}!",
            boss, "angry", 2.0,
        )

        print(f"[DESAFIOS] Snorlax usou {move.name} em {len(targets)} alvo(s) "
              f"(counter={boss._snorlax_attack_counter})")

    # -----------------------------------------------------------------
    def _trigger_snorlax_rest(self, boss, move):
        """Rest: HP cheio + dorme + entrega Poké Flute."""
        boss.current_hp = boss.max_hp
        boss.enter_sleep_state()

        try:
            if self.placement_manager.placed_pokemon:
                boss.combat._start_attack_animation(
                    self.placement_manager.placed_pokemon[0], move)
        except Exception:
            pass

        # Toast destacado (mais longo)
        self._toast(
            "Snorlax usou REST! Está dormindo — use a POKE FLUTE!",
            boss, "normal", 4.0,
        )

        self._give_pokeflute_if_needed()
        print("[DESAFIOS] REST! Snorlax dormiu.")

    # -----------------------------------------------------------------
    def _toast(self, text, pokemon, portrait="normal", duration=2.0):
        """
        Wrapper defensivo do toast_battle.
        Escreve no notification_manager que a cena renderiza.
        """
        try:
            from src.ui.toast_renderer import toast_battle
            toast_battle(text, duration=duration,
                         pokemon=pokemon, portrait=portrait)
        except Exception as e:
            print(f"[DESAFIOS] Falha no toast: {e}")

    def _give_pokeflute_if_needed(self):
        try:
            has_flute = self.player.bag.get_quantity("pokeflute") > 0
            if not has_flute:
                self.player.bag.add_item("pokeflute", 1)
                try:
                    from src.ui.toast_renderer import toast_info
                    toast_info("Poké Flute adicionada à bolsa!", duration=3.0)
                except Exception:
                    pass
                print("[DESAFIOS] Poké Flute adicionada à bag.")
        except Exception as e:
            print(f"[DESAFIOS] Erro ao adicionar Poké Flute: {e}")

    # =================================================================
    # FIM
    # =================================================================
    def _check_desafio_end(self):
        local_alive = any(
            p.is_alive() and not p.is_defeated
            for p in self._local_team_objs
        )
        boss_dead = (
            self._snorlax is not None
            and (self._snorlax.is_defeated or not self._snorlax.is_alive())
        )

        if boss_dead:
            self._end_battle("win")
        elif not local_alive and self.placement_manager.placed_pokemon:
            self._end_battle("lose")

    def _on_item_use(self, target, item_data, target_type):
        """
        Poké Flute é consumida diretamente aqui (remove_item manual).
        Retornamos consume_item=False pra o ItemDragManager NÃO tentar
        remover de novo (o que causaria double-removal se algo mudar).
        """
        item_id = item_data.get("id", "")
        effect = item_data.get("effect", "")

        # ===== POKÉ FLUTE =====
        # Checa por id OU effect — resistente a fallback do catálogo
        if effect == "wake_snorlax" or item_id == "pokeflute":

            # Alvo inválido
            if not (target_type == "enemy"
                    and getattr(target, '_is_snorlax_boss', False)
                    and getattr(target, '_snorlax_sleeping', False)):
                print("[DESAFIOS] Flute usada em alvo inválido — não consome.")
                return {"consume_item": False, "success": False}

            # Tenta acordar
            ok = target.wake_up_from_flute()
            if not ok:
                print("[DESAFIOS] wake_up_from_flute falhou — não consome.")
                return {"consume_item": False, "success": False}

            # ===== CONSOME A FLUTE (manual, garantido) =====
            consumed = False
            try:
                qty_before = self.player.bag.get_quantity("pokeflute")
                self.player.bag.remove_item("pokeflute", 1)
                qty_after = self.player.bag.get_quantity("pokeflute")
                consumed = qty_after < qty_before
                print(f"[DESAFIOS] Poké Flute consumida: "
                      f"{qty_before} → {qty_after}")
            except Exception as e:
                print(f"[DESAFIOS] Erro ao consumir Poké Flute: {e}")

            if not consumed:
                # Fallback: tenta variantes do nome do método
                for method_name in ("consume_item", "use_item", "remove"):
                    try:
                        m = getattr(self.player.bag, method_name, None)
                        if callable(m):
                            m("pokeflute", 1)
                            consumed = True
                            print(f"[DESAFIOS] Consumido via {method_name}().")
                            break
                    except Exception:
                        continue

            # ===== TOAST =====
            self._toast(
                "Snorlax ACORDOU! A batalha continua!",
                target, "angry", 3.0,
            )

            # consume_item=False: nós já removemos manualmente acima.
            return {"consume_item": False, "success": True}

        # ===== Resto delega pro handler da Arena =====
        return super()._on_item_use(target, item_data, target_type)

    # -----------------------------------------------------------------
    # PRÊMIO: SNORLAX Lv.5 NA BOX
    # -----------------------------------------------------------------
    def _give_snorlax_reward(self):
        """Adiciona o Snorlax Lv.5 SEMPRE à PC Box do jogador."""
        try:
            from datetime import datetime
            from src.entities.pokemon import Pokemon

            snorlax = Pokemon(
                0, 0,
                self.BOSS_ID,
                level=_SNORLAX_REWARD_LEVEL,
                is_wild=False,
            )
            snorlax.capture_date = datetime.now().isoformat()
            snorlax.capture_method = "desafios_reward"
            snorlax.is_in_team = False
            snorlax.is_placed = False

            self.player.add_to_box(snorlax)
            print("[DESAFIOS] Snorlax enviado para a PC Box.")

            try:
                self.player.caught_pokemon.add(self.BOSS_ID)
                self.player.register_seen(self.BOSS_ID)
            except Exception:
                pass

            self._snorlax_reward_obj = snorlax
        except Exception as e:
            print(f"[DESAFIOS] Erro ao entregar Snorlax: {e}")
            self._snorlax_reward_obj = None

    def _end_battle(self, result):
        if self.arena_state == "finished":
            return
        self.arena_state = "finished"
        self.arena_result = result

        self._restore_team()

        rewards = {
            "money": 500,
            "xp": 300,
            "trainer_name": "Snorlax",
        }

        if result == "win":
            # ===== PRÊMIO: SNORLAX Lv.5 =====
            self._give_snorlax_reward()

            try:
                self.player.money += rewards["money"]
                self.player.score += rewards["xp"]
                self.player.auto_save()
            except Exception as e:
                print(f"[DESAFIOS] Erro ao aplicar recompensas: {e}")

        else:
            try:
                self.player.money = max(0, self.player.money - rewards["money"])
                self.player.score = max(0, self.player.score - rewards["xp"])
                self.player.auto_save()
            except Exception:
                pass

        print(f"[DESAFIOS] Fim da batalha: {result}")

        from src.scenes.minigames.desafios.desafios_result_overlay import (
            DesafiosResultOverlay,
        )
        self._arena_overlay = DesafiosResultOverlay(
            self, result, rewards, self._snorlax_reward_obj,
        )

    def _finish_arena_battle(self, broadcast=True):
        self._restore_team()
        if self._on_exit_callback:
            try:
                self._on_exit_callback()
                return
            except Exception as e:
                print(f"[DESAFIOS] on_exit falhou: {e}")

        try:
            from src.scenes.minigame_select_scene.minigame_select_scene import (
                MinigameSelectScene,
            )
            self.game.current_scene = MinigameSelectScene(self.game)
        except Exception as e:
            print(f"[DESAFIOS] Erro no fallback: {e}")

    # =================================================================
    # HANDLE EVENT (drag da bag + hover)
    # =================================================================
    def handle_event(self, event):
        if (self.item_bag_renderer
                and event.type in (pygame.MOUSEMOTION, pygame.MOUSEBUTTONDOWN)):
            if hasattr(self.item_bag_renderer, 'update_hover'):
                try:
                    self.item_bag_renderer.update_hover(event.pos)
                except Exception:
                    pass

        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            if (self.item_bag_renderer
                    and getattr(self.item_bag_renderer, 'mouse_over_ui', False)
                    and not self.item_drag_manager.is_dragging):

                hovered_index = getattr(self.item_bag_renderer,
                                        'hovered_index', -1)
                if hovered_index >= 0:
                    try:
                        items = self.player.bag.get_items_for_render()
                    except Exception:
                        items = []

                    if hovered_index < len(items):
                        item = items[hovered_index]
                        self.player.bag.selected_item_index = hovered_index
                        world_pos = self.screen_manager.get_mouse_world_position(
                            event.pos, self.camera)
                        if world_pos:
                            started = self.item_drag_manager.start_drag(
                                item["id"], event.pos, world_pos)
                            if started:
                                return None

        return super().handle_event(event)

    # =================================================================
    # RENDER (inclui toasts + banner do sono)
    # =================================================================
    def render(self, screen):
        super().render(screen)

        # Banner de "Snorlax dormindo"
        if (self._snorlax is not None
                and getattr(self._snorlax, '_snorlax_sleeping', False)
                and self.arena_state not in ("finished",)):
            self._render_sleep_warning(screen)

        # ===== TOASTS (por cima do jogo, abaixo de overlays) =====
        if getattr(self, 'notification_manager', None):
            try:
                viewport_rect = pygame.Rect(
                    self.screen_manager.viewport_x,
                    self.screen_manager.viewport_y,
                    self.screen_manager.viewport_width,
                    self.screen_manager.viewport_height,
                )
                self.notification_manager.render(screen, viewport_rect)
            except Exception as e:
                print(f"[DESAFIOS] Erro ao renderizar toasts: {e}")

    def _render_sleep_warning(self, screen):
        sm = self.screen_manager
        vx, vy = sm.viewport_x, sm.viewport_y
        vw = sm.viewport_width

        t = pygame.time.get_ticks() / 1000.0
        pulse = 0.5 + 0.5 * math.sin(t * 3.5)

        banner_w = 600
        banner_h = 105
        bx = vx + (vw - banner_w) // 2
        by = vy + 110

        bg = pygame.Surface((banner_w, banner_h), pygame.SRCALPHA)
        bg.fill((30, 20, 10, 225))
        screen.blit(bg, (bx, by))

        border_alpha = int(180 + 75 * pulse)
        border = pygame.Surface((banner_w + 6, banner_h + 6), pygame.SRCALPHA)
        pygame.draw.rect(border, (255, 215, 0, border_alpha),
                         border.get_rect(), 4, border_radius=14)
        screen.blit(border, (bx - 3, by - 3))
        pygame.draw.rect(screen, (128, 90, 20),
                         (bx, by, banner_w, banner_h), 1, border_radius=14)

        font_big = pygame.font.Font(None, 38)
        font_small = pygame.font.Font(None, 22)

        txt1 = "SNORLAX ESTÁ DORMINDO!"
        txt2 = "Arraste a POKE FLUTE da bolsa até ele!"

        surf1 = font_big.render(txt1, True, (255, 215, 0))
        surf2 = font_small.render(txt2, True, (255, 255, 255))
        shadow1 = font_big.render(txt1, True, (0, 0, 0))
        shadow2 = font_small.render(txt2, True, (0, 0, 0))

        screen.blit(shadow1, shadow1.get_rect(
            center=(bx + banner_w // 2 + 2, by + 32 + 2)))
        screen.blit(surf1, surf1.get_rect(
            center=(bx + banner_w // 2, by + 32)))

        screen.blit(shadow2, shadow2.get_rect(
            center=(bx + banner_w // 2 + 1, by + 70 + 1)))
        screen.blit(surf2, surf2.get_rect(
            center=(bx + banner_w // 2, by + 70)))

        # Seta apontando pro Snorlax
        try:
            sx, sy = sm.world_to_screen(
                self._snorlax.x, self._snorlax.y, self.camera)
            arrow_y = sy - 70 - int(15 * pulse)

            pts = [
                (sx, arrow_y + 26),
                (sx - 20, arrow_y),
                (sx + 20, arrow_y),
            ]
            pygame.draw.polygon(screen, (255, 215, 0), pts)
            pygame.draw.polygon(screen, (150, 100, 20), pts, 3)

            f = pygame.font.Font(None, 20)
            lbl = f.render("USE A FLUTE AQUI", True, (255, 215, 0))
            lbl_sh = f.render("USE A FLUTE AQUI", True, (0, 0, 0))
            lx = sx - lbl.get_width() // 2
            ly = arrow_y - 26
            screen.blit(lbl_sh, (lx + 1, ly + 1))
            screen.blit(lbl, (lx, ly))
        except Exception:
            pass