# src/scenes/chest_scene/chest_scene.py
"""Tela de Baús — animação cinematográfica."""
import math
import random
import pygame

from src.ui.screen_template import StandardScreen
from src.ui.screen_loader import ScreenLoader
from src.managers.sounds.sound_manager import sound_manager, SoundEffect

from .chest_logic import ChestLogic


MAIN_JSON = "res/ui_layouts/chest.json"

# ===== TIMING (segundos) =====
ANTICIPATE_TIME = 0.75   # tremida antes de abrir
BURST_TIME      = 0.55   # explosão de abertura
REVEAL_STAGGER  = 0.42   # delay entre cada card
REVEAL_POP_TIME = 0.38   # duração da animação de cada card

# ===== CANVAS =====
# painel do modal no design (w=0.72, h=0.88) * 1280x720
PANEL_W = int(1280 * 0.72)  # 921
PANEL_H = int(720  * 0.88)  # 633


class ChestScene(StandardScreen):
    title = ""
    show_back_button = False

    # ============================================================
    def __init__(self, game, return_scene=None):
        self.player = game.player
        self.logic = ChestLogic(game)
        self.return_scene = return_scene or "menu"

        self._open_modal = ""
        self._anim = self._empty_anim()
        self._fx = self._empty_fx()
        self._fx_surface = None
        self._rng = random.Random()

        super().__init__(game)

    # ============================================================
    @staticmethod
    def _empty_anim():
        return {
            "slot_idx": -1,
            "chest_type": None,
            "phase": "idle",     # idle | anticipate | burst | revealing | done
            "phase_time": 0.0,
            "rewards": [],
            "revealed": 0,
            "reveal_timer": 0.0,
            "card_times": [],
            "_burst_fired": False,
        }

    @staticmethod
    def _empty_fx():
        return {
            "particles": [],
            "flash_alpha": 0.0,
            "shake_amp": 0.0,
            "shake_time": 0.0,
            "shake_seed": 0.0,
        }

    # ============================================================
    def build(self):
        ScreenLoader.load(self, MAIN_JSON)
        self._refresh_main()

    def enter(self):
        if hasattr(self.player, "check_chest_status"):
            self.player.check_chest_status()
        self._refresh_main()

        for i, c in enumerate(self.player.chests):
            if c.get("status") == "opened":
                self._open_modal_chest(i, skip_animation=True)
                break

    # ============================================================
    def get_actions(self):
        return {
            "back":        self._on_back,
            "slot_0":      lambda *_: self._on_slot_click(0),
            "slot_1":      lambda *_: self._on_slot_click(1),
            "slot_2":      lambda *_: self._on_slot_click(2),
            "collect":     lambda *_: self._on_collect(),
            "close_modal": lambda *_: self._close_modal(),
        }

    # ============================================================
    # HELPERS
    # ============================================================
    def _set(self, wid, text):
        w = self.get(wid)
        if w is not None and hasattr(w, "text"):
            w.text = text

    def _set_surface(self, wid, surf):
        w = self.get(wid)
        if w is not None and hasattr(w, "surface"):
            w.surface = surf

    def _play_click(self, v=0.3):
        try:
            sound_manager.play_effect(SoundEffect.CLICK, volume=v)
        except Exception:
            pass

    # ============================================================
    # REFRESH MAIN (tela de baús)
    # ============================================================
    def _refresh_main(self):
        from src.data.chest_data import CHEST_TYPES

        self._set("lbl_money", f"$ {int(self.player.money):,}".replace(",", "."))

        for i in range(3):
            slot = self.logic.get_slot(i)
            if slot is None:
                continue
            ct = self.logic.chest_type_of(i)
            cfg = CHEST_TYPES[ct]

            surf = self.logic.chest_sprite(ct, frame=0, size=(160, 160))
            if slot["status"] == "opened":
                surf = self.logic.chest_sprite(ct, frame=3, size=(160, 160))
            self._set_surface(f"slot_{i}_img", surf)

            self._set(f"slot_{i}_name",   cfg["name"])
            self._set(f"slot_{i}_tag",    cfg["tagline"])
            self._set(f"slot_{i}_status", self.logic.status_label(slot))
            self._set(f"slot_{i}_time",   self.logic.time_text(slot))

            status_color = {
                "ready":    "#6ADE82",
                "opened":   "#FFD24A",
                "cooldown": "#8A98C0",
            }.get(slot["status"], "#8A98C0")

            for wid in (f"slot_{i}_status", f"slot_{i}_time"):
                w = self.get(wid)
                if w is not None and hasattr(w, "text_color"):
                    try:
                        w.text_color = status_color
                    except Exception:
                        pass

            prog = self.get(f"slot_{i}_prog")
            if prog is not None:
                prog.value = self.logic.progress_ratio(slot) * 100

            btn = self.get(f"slot_{i}_btn")
            if btn is not None:
                if slot["status"] in ("ready", "opened"):
                    btn.label = "ABRIR"
                    btn.enabled = True
                else:
                    btn.label = "AGUARDE"
                    btn.enabled = False

    # ============================================================
    # CLIQUE NO SLOT
    # ============================================================
    def _on_slot_click(self, idx: int):
        slot = self.logic.get_slot(idx)
        if slot is None:
            return

        if slot["status"] == "opened":
            self._play_click()
            self._open_modal_chest(idx, skip_animation=True)
            return

        if slot["status"] != "ready":
            return

        self._play_click()
        rewards = self.player.open_chest(idx)
        if not rewards:
            return
        self._open_modal_chest(idx, skip_animation=False)
        self._refresh_main()

    # ============================================================
    # MODAL
    # ============================================================
    def _open_modal_chest(self, idx: int, skip_animation: bool = False):
        slot = self.logic.get_slot(idx)
        if slot is None:
            return

        ct = self.logic.chest_type_of(idx)
        rewards = list(slot.get("rewards", []))

        self._open_modal = "open"
        self._set_modal_visible("open", True)

        from src.data.chest_data import CHEST_TYPES
        self._set("m_open_title", CHEST_TYPES[ct]["name"])

        chest_img = self.get("m_open_chest")
        grid      = self.get("m_open_rewards")
        btn       = self.get("m_open_collect")
        fx        = self.get("m_open_fx")

        # ---------- SKIP (reload) ----------
        if skip_animation or not rewards:
            self._anim = self._empty_anim()
            self._anim["phase"] = "done"
            self._anim["slot_idx"] = idx
            self._anim["chest_type"] = ct
            self._anim["rewards"] = rewards
            self._anim["revealed"] = len(rewards)
            self._anim["card_times"] = [1.0] * len(rewards)

            if chest_img is not None:
                chest_img.visible = True
                chest_img.surface = self.logic.chest_sprite(ct, 3, size=(224, 224))
            if grid is not None:
                grid.visible = True
                grid.items = self.logic.reward_items(rewards)
            if btn is not None:
                btn.visible = True
            if fx is not None:
                fx.visible = False
                fx.surface = None
            self._fx = self._empty_fx()
            return

        # ---------- ANIMAÇÃO ----------
        self._anim = self._empty_anim()
        self._anim["slot_idx"] = idx
        self._anim["chest_type"] = ct
        self._anim["phase"] = "anticipate"
        self._anim["phase_time"] = 0.0
        self._anim["rewards"] = rewards
        self._anim["card_times"] = [0.0] * len(rewards)

        if chest_img is not None:
            chest_img.visible = False
        if grid is not None:
            grid.visible = False
            grid.items = []
        if btn is not None:
            btn.visible = False
        if fx is not None:
            fx.visible = True

        self._fx = self._empty_fx()

    # ============================================================
    # FX — partículas / shake / flash
    # ============================================================
    def _spawn_burst(self, cx, cy, color, count=48):
        for _ in range(count):
            ang = self._rng.uniform(0, math.tau)
            spd = self._rng.uniform(140, 460)
            life = self._rng.uniform(0.55, 1.15)
            self._fx["particles"].append({
                "x": cx, "y": cy,
                "vx": math.cos(ang) * spd,
                "vy": math.sin(ang) * spd - 70,
                "life": life, "max_life": life,
                "size": self._rng.uniform(2.5, 6.0),
                "color": color,
                "kind": "spark",
            })
        # Estrelas grandes
        for _ in range(8):
            ang = self._rng.uniform(0, math.tau)
            spd = self._rng.uniform(70, 200)
            life = self._rng.uniform(0.9, 1.5)
            self._fx["particles"].append({
                "x": cx, "y": cy,
                "vx": math.cos(ang) * spd,
                "vy": math.sin(ang) * spd - 50,
                "life": life, "max_life": life,
                "size": self._rng.uniform(8, 14),
                "color": (255, 245, 200),
                "kind": "star",
            })

    def _spawn_sparkle_ring(self, cx, cy, color, count=12, r=26):
        for i in range(count):
            ang = (i / count) * math.tau
            self._fx["particles"].append({
                "x": cx + math.cos(ang) * r,
                "y": cy + math.sin(ang) * r,
                "vx": math.cos(ang) * 55,
                "vy": math.sin(ang) * 55 - 20,
                "life": 0.6, "max_life": 0.6,
                "size": 3.5,
                "color": color,
                "kind": "spark",
            })

    def _trigger_shake(self, amp=12.0, duration=0.35):
        self._fx["shake_amp"] = max(self._fx["shake_amp"], amp)
        self._fx["shake_time"] = max(self._fx["shake_time"], duration)
        self._fx["shake_seed"] = self._rng.uniform(0, 100)

    def _tick_fx(self, dt):
        alive = []
        for p in self._fx["particles"]:
            p["life"] -= dt
            if p["life"] <= 0:
                continue
            p["x"] += p["vx"] * dt
            p["y"] += p["vy"] * dt
            p["vy"] += 520 * dt         # gravidade
            p["vx"] *= (1 - 1.8 * dt)   # drag
            p["vy"] *= (1 - 1.2 * dt)
            alive.append(p)
        self._fx["particles"] = alive

        if self._fx["flash_alpha"] > 0:
            self._fx["flash_alpha"] = max(
                0.0, self._fx["flash_alpha"] - 900 * dt
            )

        if self._fx["shake_time"] > 0:
            self._fx["shake_time"] = max(0.0, self._fx["shake_time"] - dt)
            if self._fx["shake_time"] <= 0:
                self._fx["shake_amp"] = 0.0

    # ============================================================
    # FX — render (canvas principal)
    # ============================================================
    def _render_fx(self):
        fx_widget = self.get("m_open_fx")
        if fx_widget is None:
            return

        if self._fx_surface is None:
            self._fx_surface = pygame.Surface((PANEL_W, PANEL_H), pygame.SRCALPHA)
        else:
            self._fx_surface.fill((0, 0, 0, 0))
        surf = self._fx_surface

        phase   = self._anim["phase"]
        phase_t = self._anim["phase_time"]

        cx = PANEL_W * 0.5
        cy = PANEL_H * 0.30
        chest_size = (224, 224)

        # ---------- Parâmetros de animação ----------
        wig_x, wig_y = 0.0, 0.0
        chest_scale = 1.0
        chest_frame = 0

        if phase == "anticipate":
            k = min(1.0, phase_t / ANTICIPATE_TIME)
            freq = 10 + k * 14
            amp  = 3 + k * 5
            wig_x = math.sin(phase_t * freq) * amp
            wig_y = -abs(math.sin(phase_t * freq)) * (2 + k * 3)
            chest_scale = 1.0 + 0.06 * k

        elif phase == "burst":
            k = min(1.0, phase_t / BURST_TIME)
            chest_frame = min(3, int(k * 4))
            if k > 0.7:
                punch = (k - 0.7) / 0.3
                chest_scale = 1.0 + 0.28 * math.sin(punch * math.pi)
            else:
                chest_scale = 1.0 + 0.12 * k
            wig_x = math.sin(phase_t * 60) * 2.5 * (1 - k)

        elif phase in ("revealing", "done"):
            chest_frame = 3
            chest_scale = 1.0

        # ---------- GLOW por baixo ----------
        glow_r = int(90 * (1.0 + 0.15 * math.sin(pygame.time.get_ticks() * 0.006)))
        glow_color = (255, 220, 130, 70)
        if phase == "burst":
            k = min(1.0, phase_t / BURST_TIME)
            glow_color = (255, 245, 210, int(70 + 140 * k))

        glow_surf = pygame.Surface((glow_r * 2, glow_r * 2), pygame.SRCALPHA)
        for i in range(5, 0, -1):
            r = int(glow_r * (i / 5))
            a = int(glow_color[3] * (1 - i / 6))
            a = max(0, min(255, a))
            pygame.draw.circle(
                glow_surf,
                (glow_color[0], glow_color[1], glow_color[2], a),
                (glow_r, glow_r), r,
            )
        surf.blit(glow_surf,
                  (int(cx - glow_r + wig_x), int(cy - glow_r + wig_y)))

        # ---------- BAÚ ----------
        chest_surf = self.logic.chest_sprite(
            self._anim["chest_type"], frame=chest_frame, size=chest_size
        )
        if chest_surf is not None:
            if chest_scale != 1.0:
                w, h = chest_surf.get_size()
                sw = max(1, int(w * chest_scale))
                sh = max(1, int(h * chest_scale))
                chest_surf = pygame.transform.scale(chest_surf, (sw, sh))

            w, h = chest_surf.get_size()

            # sombra
            shadow = pygame.Surface((w * 3 // 4, h // 5), pygame.SRCALPHA)
            pygame.draw.ellipse(shadow, (0, 0, 0, 100), shadow.get_rect())
            surf.blit(shadow, (int(cx + wig_x - w * 3 // 8),
                               int(cy + wig_y + h * 0.44)))

            surf.blit(chest_surf,
                      (int(cx + wig_x - w / 2),
                       int(cy + wig_y - h / 2)))

        # ---------- PARTÍCULAS ----------
        for p in self._fx["particles"]:
            life_k = max(0.0, min(1.0, p["life"] / p["max_life"]))
            alpha = int(255 * life_k)
            size = p["size"] * (0.45 + 0.55 * life_k)
            col = p["color"] + (alpha,)
            px = p["x"] + cx
            py = p["y"] + cy
            if p["kind"] == "star":
                self._draw_star(surf, px, py, size, col)
            else:
                self._draw_dot(surf, px, py, size, col)

        # ---------- CARDS ----------
        if phase in ("revealing", "done"):
            self._render_reward_cards(surf)

        # ---------- FLASH ----------
        if self._fx["flash_alpha"] > 0:
            fa = int(min(255, self._fx["flash_alpha"]))
            flash = pygame.Surface((PANEL_W, PANEL_H), pygame.SRCALPHA)
            flash.fill((255, 255, 255, fa))
            surf.blit(flash, (0, 0))

        fx_widget.surface = surf

    # ============================================================
    # FX — primitivas
    # ============================================================
    @staticmethod
    def _draw_dot(surf, x, y, r, color):
        try:
            pygame.draw.circle(surf, color, (int(x), int(y)), max(1, int(r)))
        except Exception:
            pass

    @staticmethod
    def _draw_star(surf, x, y, r, color):
        x, y = int(x), int(y)
        r = max(2, int(r))
        pygame.draw.line(surf, color, (x - r, y), (x + r, y), 2)
        pygame.draw.line(surf, color, (x, y - r), (x, y + r), 2)
        pygame.draw.line(surf, color, (x - r + 1, y - r + 1),
                         (x + r - 1, y + r - 1), 1)
        pygame.draw.line(surf, color, (x - r + 1, y + r - 1),
                         (x + r - 1, y - r + 1), 1)

    # ============================================================
    # FX — cards animados
    # ============================================================
    def _card_position(self, idx):
        """Centro do card idx no canvas (coords do PANEL)."""
        gw = PANEL_W * 0.9
        gh = PANEL_H * 0.32
        gx = PANEL_W * 0.5 - gw / 2
        gy = PANEL_H * 0.66 - gh / 2
        cols, rows, gap, pad = 2, 3, 8, 4
        cell_w = (gw - pad * 2 - gap * (cols - 1)) / cols
        cell_h = (gh - pad * 2 - gap * (rows - 1)) / rows
        col = idx % cols
        row = idx // cols
        cx = gx + pad + col * (cell_w + gap) + cell_w / 2
        cy = gy + pad + row * (cell_h + gap) + cell_h / 2
        return cx, cy, cell_w, cell_h

    def _render_reward_cards(self, surf):
        """Desenha os cards com animação pop."""
        raw = self._anim["rewards"]
        if not raw:
            return
        enriched = self.logic.reward_items(raw)
        times = self._anim["card_times"]

        for i, r in enumerate(enriched):
            t = times[i] if i < len(times) else 0.0
            if t <= 0:
                continue

            # Overshoot: 0 → 1.15 → 1.0
            if t < 0.6:
                k = t / 0.6
                scale = 1.15 * (1 - (1 - k) ** 2)
            else:
                k = (t - 0.6) / 0.4
                scale = 1.15 - 0.15 * k

            alpha = int(255 * min(1.0, t / 0.4))

            cx, cy, cw, ch = self._card_position(i)
            w = int(cw * scale)
            h = int(ch * scale)

            is_new = (r.get("is_clothing") and not r.get("is_duplicate"))
            self._draw_reward_card(surf, cx, cy, w, h, alpha, r, is_new)

    def _draw_reward_card(self, surf, cx, cy, w, h, alpha, r, is_new):
        def _hex(c):
            c = c.lstrip("#")
            return (int(c[0:2], 16), int(c[2:4], 16), int(c[4:6], 16))

        bc = _hex(r.get("border_color", "#3A4870"))
        bgc = _hex(r.get("bg_color", "#12172A"))
        a = min(255, alpha)

        # sombra
        shadow = pygame.Surface((w, h), pygame.SRCALPHA)
        pygame.draw.rect(shadow, (0, 0, 0, int(140 * alpha / 255)),
                         (0, 0, w, h), border_radius=8)
        surf.blit(shadow, (int(cx - w / 2) + 3, int(cy - h / 2) + 3))

        # fundo + borda
        bg = pygame.Surface((w, h), pygame.SRCALPHA)
        pygame.draw.rect(bg, bgc + (a,), (0, 0, w, h), border_radius=8)
        pygame.draw.rect(bg, bc + (a,), (0, 0, w, h),
                         width=2, border_radius=8)
        surf.blit(bg, (int(cx - w / 2), int(cy - h / 2)))

        # sprite
        sprite = r.get("sprite")
        if sprite is not None:
            sw, sh = sprite.get_size()
            max_h = int(h * 0.78)
            max_w = int(w * 0.34)
            s = min(max_w / max(1, sw), max_h / max(1, sh))
            if s < 1.0:
                sprite = pygame.transform.scale(
                    sprite, (max(1, int(sw * s)), max(1, int(sh * s)))
                )
            sprite = sprite.copy()
            sprite.set_alpha(a)
            surf.blit(sprite,
                      (int(cx - w / 2 + w * 0.08),
                       int(cy - sprite.get_height() / 2)))

        # nome
        try:
            font = pygame.font.Font(None, 16)
            name = (r.get("name") or "").upper()
            if len(name) > 14:
                name = name[:13] + "…"
            txt = font.render(name, True, (255, 255, 255))
            txt.set_alpha(a)
            surf.blit(txt, (int(cx - w / 2 + w * 0.46),
                            int(cy - h * 0.18)))
        except Exception:
            pass

        # qty / NOVO
        qty_text = r.get("qty_text", "")
        if qty_text:
            try:
                font = pygame.font.Font(None, 18)
                col = (110, 222, 130) if is_new else (255, 210, 74)
                txt = font.render(qty_text, True, col)
                txt.set_alpha(a)
                surf.blit(txt, (int(cx - w / 2 + w * 0.46),
                                int(cy + h * 0.08)))
            except Exception:
                pass

        # halo "NOVO!"
        if is_new:
            pulse = 0.6 + 0.4 * math.sin(pygame.time.get_ticks() * 0.008)
            halo = pygame.Surface((w + 14, h + 14), pygame.SRCALPHA)
            pygame.draw.rect(
                halo,
                (110, 222, 130, int(90 * pulse * alpha / 255)),
                (0, 0, w + 14, h + 14),
                width=4, border_radius=12,
            )
            surf.blit(halo, (int(cx - w / 2) - 7, int(cy - h / 2) - 7))

    # ============================================================
    # STATE MACHINE
    # ============================================================
    def _tick_animation(self, dt):
        a = self._anim
        if a["phase"] == "idle":
            return

        a["phase_time"] += dt

        if a["phase"] == "anticipate":
            if a["phase_time"] >= ANTICIPATE_TIME:
                a["phase"] = "burst"
                a["phase_time"] = 0.0
                a["_burst_fired"] = False

        elif a["phase"] == "burst":
            if not a["_burst_fired"]:
                a["_burst_fired"] = True
                self._trigger_shake(amp=14.0, duration=0.40)
                self._fx["flash_alpha"] = 230.0
                from src.data.chest_data import CHEST_TYPES
                accent = CHEST_TYPES[a["chest_type"]]["accent_color"].lstrip("#")
                ac = (int(accent[0:2], 16),
                      int(accent[2:4], 16),
                      int(accent[4:6], 16))
                self._spawn_burst(PANEL_W * 0.5, PANEL_H * 0.30, ac, count=48)

            if a["phase_time"] >= BURST_TIME:
                a["phase"] = "revealing"
                a["phase_time"] = 0.0
                a["reveal_timer"] = 0.0
                a["revealed"] = 0

        elif a["phase"] == "revealing":
            a["reveal_timer"] += dt

            # Avança pops em andamento
            for i in range(len(a["card_times"])):
                if 0 < a["card_times"][i] < 1.0:
                    a["card_times"][i] = min(
                        1.0, a["card_times"][i] + dt / REVEAL_POP_TIME
                    )

            # Próximo card
            if (a["revealed"] < len(a["rewards"]) and
                    a["reveal_timer"] >= REVEAL_STAGGER):
                a["reveal_timer"] -= REVEAL_STAGGER
                idx = a["revealed"]
                a["card_times"][idx] = 0.01
                a["revealed"] += 1

                self._trigger_shake(amp=4.5, duration=0.15)
                ccx, ccy, _, _ = self._card_position(idx)
                self._spawn_sparkle_ring(ccx, ccy,
                                         (255, 240, 180),
                                         count=12, r=26)

                r = a["rewards"][idx]
                if r.get("is_clothing") and not r.get("is_duplicate"):
                    self._fx["flash_alpha"] = max(self._fx["flash_alpha"], 70.0)

            all_done = (a["revealed"] >= len(a["rewards"]) and
                        all(t >= 1.0 for t in a["card_times"]))
            if all_done:
                a["phase"] = "done"
                self._finish_animation()

    def _finish_animation(self):
        """Troca canvas FX pelos widgets reais."""
        rewards = list(self._anim["rewards"])
        ct = self._anim["chest_type"]

        chest_img = self.get("m_open_chest")
        grid      = self.get("m_open_rewards")
        btn       = self.get("m_open_collect")
        fx        = self.get("m_open_fx")

        if chest_img is not None:
            chest_img.visible = True
            chest_img.surface = self.logic.chest_sprite(ct, 3, size=(224, 224))
        if grid is not None:
            grid.visible = True
            grid.items = self.logic.reward_items(rewards)
        if btn is not None:
            btn.visible = True
        # FX continua visível pra "despejar" as partículas residuais
        # (o fixed_update vai esconder quando acabar)

    # ============================================================
    # COLETA
    # ============================================================
    def _on_collect(self):
        idx = self._anim.get("slot_idx", -1)
        if idx < 0:
            return
        collected = self.player.collect_chest(idx)
        print(f"[CHEST] Coletadas {len(collected)} recompensa(s) do slot {idx}")
        self._play_click()
        self._close_modal()
        self._refresh_main()

    def _close_modal(self):
        if self._open_modal:
            self._set_modal_visible(self._open_modal, False)
        self._open_modal = ""
        self._anim = self._empty_anim()
        self._fx = self._empty_fx()
        self._fx_surface = None

    def _set_modal_visible(self, modal, visible):
        prefix = f"m_{modal}_"
        for w in self.widgets:
            if w.id and w.id.startswith(prefix):
                w.visible = visible

    # ============================================================
    # NAV
    # ============================================================
    def _on_back(self):
        self._play_click()
        try:
            sound_manager.stop_music(fade_ms=300)
        except Exception:
            pass

        if self.return_scene == "phase_select":
            from src.scenes.phase_selector.phase_select_scene import PhaseSelectScene
            self.game.phase_select_scene = PhaseSelectScene(self.game)
            self.game.current_scene = self.game.phase_select_scene
        else:
            from src.scenes.menu_scene import MenuScene
            self.game.current_scene = MenuScene(self.game)

    # ============================================================
    # EVENTOS
    # ============================================================
    def handle_event(self, event):
        if event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE:
            if self._open_modal:
                self._close_modal()
                return
            self._on_back()
            return

        if self._open_modal == "open":
            prefix = "m_open_"
            for w in sorted(self.widgets, key=lambda x: -getattr(x, "z", 0)):
                if w.id and w.id.startswith(prefix):
                    # Bloqueia clique durante a animação
                    if (self._anim["phase"] in ("anticipate", "burst", "revealing")
                            and w.id == "m_open_collect"):
                        continue
                    if w.handle_event(event):
                        return
            return

        super().handle_event(event)

    # ============================================================
    # UPDATE
    # ============================================================
    def fixed_update(self, dt):
        if hasattr(self.player, "check_chest_status"):
            self.player.check_chest_status()

        # FX sempre ativo se tiver coisa rolando
        if (self._fx["particles"] or
                self._fx["flash_alpha"] > 0 or
                self._fx["shake_time"] > 0):
            self._tick_fx(dt)

        if self._open_modal == "open":
            phase = self._anim["phase"]

            if phase in ("anticipate", "burst", "revealing"):
                self._tick_animation(dt)
                self._render_fx()

            elif phase == "done":
                fx_widget = self.get("m_open_fx")
                has_fx = (self._fx["particles"] or
                          self._fx["flash_alpha"] > 0 or
                          self._fx["shake_time"] > 0)
                if fx_widget is not None:
                    if has_fx:
                        fx_widget.visible = True
                        self._render_fx()
                    else:
                        fx_widget.visible = False

        self._refresh_main()
        super().fixed_update(dt)

    def on_back(self):
        self._on_back()