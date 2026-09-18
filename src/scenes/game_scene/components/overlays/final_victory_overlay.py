# src/scenes/game_scene/components/overlays/final_victory_overlay.py

import pygame
import random
import math
from .base_overlay import BaseOverlay
from src.data.pokedex import Pokedex


class FinalVictoryOverlay(BaseOverlay):
    """
    Overlay especial de vitoria final (Hall of Fame).

    - 6 pokemons do time em destaque (sprites grandes, com sparkles se shiny)
    - Pokemons da box sobem em ordem de captura, com teto rigido
    - Balao com conquistas do jogador sobe junto (tambem com teto)
    - Botao PULAR no canto -> PhaseSelectScene
    - Responsivo, com brilhos dourados e sparkles animados em shinies

    REGRAS:
      * Overlay cobre a TELA INTEIRA (window_width x window_height).
      * NADA ultrapassa a linha do time (BOX_CEILING_FRACTION).
      * Ao tocar o teto, o item faz fade-out agressivo e some.
      * Todos os pokemons da box sao exibidos.
      * Balao faz fade-out no teto em ~0.4s e o proximo entra logo.
    """

    INTRO_DURATION         = 1.6
    TEAM_APPEAR_INTERVAL   = 0.28

    # --- BOX ---
    BOX_SPAWN_INTERVAL     = 0.55
    BOX_MAX_CONCURRENT     = 8

    # --- BALOES ---
    BALLOON_SPAWN_INTERVAL = 0.55   # proximo balao entra rapido
    BALLOON_MAX_CONCURRENT = 2      # poucos simultaneos = fluxo continuo
    BALLOON_MAX_TOTAL      = 12

    # --- TETO (em fracao da altura da tela) ---
    BOX_CEILING_FRACTION     = 0.55
    BOX_FADE_START_FRACTION  = 0.72

    BALLOON_CEILING_FRACTION    = 0.55
    BALLOON_FADE_START_FRACTION = 0.78

    # Velocidade de fade no teto (multiplicador do fade_speed)
    CEILING_FADE_MULT = 6.0
    # Alpha maximo quando encosta no teto (comeca a sumir)
    CEILING_MAX_ALPHA = 200

    FINAL_HOLD_DURATION    = 3.0

    GOLD        = (255, 215, 0)
    GOLD_BRIGHT = (255, 240, 150)
    TEXT_WHITE  = (245, 245, 255)
    TEXT_DIM    = (170, 180, 200)

    def __init__(self, game_scene):
        super().__init__(game_scene)
        self.player  = game_scene.player
        self.pokedex = Pokedex()

        self.team        = list(self.player.team)[:6]
        self.box_pokemon = self._get_box_sorted()
        self.balloon_data = self._collect_achievement_balloons()

        self.elapsed             = 0.0
        self.music_played        = False
        self.finished            = False
        self.team_reveal_count   = 0.0
        self.rising_sprites      = []
        self.rising_balloons     = []

        self._team_finish_time  = (self.INTRO_DURATION +
                                   self.TEAM_APPEAR_INTERVAL * max(1, len(self.team)) +
                                   0.4)
        self._next_box_spawn     = self._team_finish_time
        self._next_balloon_spawn = self._team_finish_time + 0.6

        self._box_spawned        = 0
        self._balloon_spawned    = 0
        self.final_hold_timer    = 0.0

        self.skip_button_rect = None
        self.skip_hovered     = False

        self._fonts = {}
        self._shared_sprite_size = None

    # =================================================================
    # HELPERS
    # =================================================================
    def _get_font(self, size):
        size = max(10, int(size))
        if size not in self._fonts:
            self._fonts[size] = pygame.font.Font(None, size)
        return self._fonts[size]

    def _get_shared_sprite_size(self):
        vw = self.screen_manager.window_width
        vh = self.screen_manager.window_height
        size = int(min(vw, vh) * 0.185)
        return max(120, min(size, 200))

    def _get_box_sorted(self):
        box = list(self.player.pc_box)
        def key(p):
            if isinstance(p, dict):
                return p.get("capture_date", "") or ""
            return getattr(p, "capture_date", "") or ""
        box.sort(key=key)
        return box

    def _collect_achievement_balloons(self):
        counters = []

        if hasattr(self.player, 'achievement_manager'):
            am  = self.player.achievement_manager
            raw = am._counters if hasattr(am, '_counters') else {}

            labels = {
                "capture_count":              "Pokemon capturados",
                "heal_count":                 "Curas usadas",
                "evolution_count":            "Evolucoes totais",
                "level_evolution_count":      "Evolucoes por nivel",
                "stone_evolution_count":      "Evolucoes por pedra",
                "happiness_evolution_count":  "Evolucoes por felicidade",
                "weather_evolution_count":    "Evolucoes por clima",
                "shiny_capture_count":        "Shinies capturados",
                "boss_defeated_count":        "Chefes derrotados",
                "perfect_phase_count":        "Fases perfeitas",
                "revive_count":               "Revives usados",
                "rare_candy_count":           "Rare Candies usados",
                "escaperope_use_count":       "Escape Ropes usados",
                "move_taught_count":          "Movimentos ensinados",
                "badge_count":                "Insignias conquistadas",
                "friendball_capture_count":   "Friend Ball capturas",
                "weather_change_count":       "Climas alterados",
                "trade_count":                "Trocas realizadas",
                "battle_item_use_count":      "Itens de batalha",
                "berry_consumed_count":       "Berries consumidas",
                "capture_with_item_count":    "Capturas com item",
            }
            for key, value in raw.items():
                if value > 0 and key in labels:
                    counters.append({"label": labels[key], "value": value})

        caught = len(getattr(self.player, 'caught_pokemon', set()))
        if caught > 0:
            counters.insert(0, {"label": "Pokedex capturados", "value": caught})

        money = getattr(self.player, 'money', 0)
        if money > 0:
            counters.insert(0, {"label": "Moedas acumuladas", "value": money})

        score = getattr(self.player, 'score', 0)
        if score > 0:
            counters.insert(0, {"label": "Experiencia total", "value": score})

        counters.sort(key=lambda x: -x["value"])
        return counters[:self.BALLOON_MAX_TOTAL]

    def _screen_size(self):
        """Tamanho da TELA INTEIRA (nao so o viewport)."""
        sm = self.screen_manager
        return sm.window_width, sm.window_height

    # =================================================================
    # EVENTOS
    # =================================================================
    def handle_event(self, event):
        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            if self.skip_button_rect and self.skip_button_rect.collidepoint(event.pos):
                self._finish()
                return True
        elif event.type == pygame.KEYDOWN:
            if event.key in (pygame.K_ESCAPE, pygame.K_RETURN, pygame.K_SPACE):
                self._finish()
                return True
        elif event.type == pygame.MOUSEMOTION:
            if self.skip_button_rect:
                self.skip_hovered = self.skip_button_rect.collidepoint(event.pos)
        return False

    def _finish(self):
        if self.finished:
            return
        self.finished = True

        try:
            from src.managers.sounds.sound_manager import sound_manager
            sound_manager.stop_music(fade_ms=500)
        except Exception:
            pass

        if hasattr(self.game_scene, 'cleanup'):
            try:
                self.game_scene.cleanup()
            except Exception as e:
                print(f"[FINAL_VICTORY] Erro em cleanup: {e}")

        if hasattr(self.game_scene, 'final_victory_overlay'):
            self.game_scene.final_victory_overlay = None

        from src.scenes.phase_selector.phase_select_scene import PhaseSelectScene
        phase_scene = PhaseSelectScene(self.game)
        phase_scene._needs_refresh = True
        self.game.current_scene = phase_scene
        print("[FINAL_VICTORY] Retornando para a PhaseSelectScene.")

    # =================================================================
    # UPDATE
    # =================================================================
    def update(self, dt):
        if not self.music_played:
            self._play_victory_music()
            self.music_played = True

        self.elapsed += dt

        sw, sh = self._screen_size()
        box_ceiling     = sh * self.BOX_CEILING_FRACTION
        balloon_ceiling = sh * self.BALLOON_CEILING_FRACTION

        # ---- Reveal progressivo do time ----
        if self.elapsed >= self.INTRO_DURATION:
            elapsed_since = self.elapsed - self.INTRO_DURATION
            self.team_reveal_count = min(
                len(self.team),
                elapsed_since / self.TEAM_APPEAR_INTERVAL
            )

        # ---- Spawn pokemon da box ----
        if (self.elapsed >= self._next_box_spawn
                and self._box_spawned < len(self.box_pokemon)):
            remaining = len(self.box_pokemon) - self._box_spawned
            burst = 1
            if remaining > 80:   burst = 4
            elif remaining > 50: burst = 3
            elif remaining > 25: burst = 2

            for _ in range(burst):
                if (self._box_spawned < len(self.box_pokemon)
                        and len(self.rising_sprites) < self.BOX_MAX_CONCURRENT):
                    self._spawn_box_pokemon()
                else:
                    break

            self._next_box_spawn = self.elapsed + self.BOX_SPAWN_INTERVAL

        # ---- Spawn baloes ----
        # Spawna assim que ha espaco, sem esperar todos os anteriores morrerem
        if (self.elapsed >= self._next_balloon_spawn
                and self._balloon_spawned < len(self.balloon_data)
                and len(self.rising_balloons) < self.BALLOON_MAX_CONCURRENT):
            self._spawn_balloon()
            self._next_balloon_spawn = self.elapsed + self.BALLOON_SPAWN_INTERVAL

        # ---- Update sprites ----
        for s in self.rising_sprites[:]:
            s['y'] -= s['speed'] * dt

            if s['y'] > s['fade_start_y']:
                s['alpha'] = min(255, s['alpha'] + 220 * dt)
            else:
                s['alpha'] -= s['fade_speed'] * dt

            # Teto: fade-out agressivo
            if s['y'] <= box_ceiling:
                s['y'] = box_ceiling
                if s['alpha'] > self.CEILING_MAX_ALPHA:
                    s['alpha'] = self.CEILING_MAX_ALPHA
                s['alpha'] -= (s['fade_speed'] * self.CEILING_FADE_MULT) * dt

            if s['alpha'] <= 0:
                self.rising_sprites.remove(s)

        # ---- Update baloes ----
        for b in self.rising_balloons[:]:
            b['y'] -= b['speed'] * dt

            if b['alpha'] < 235:
                b['alpha'] = min(235, b['alpha'] + 200 * dt)
            if b['y'] < b['fade_start_y']:
                b['alpha'] -= b['fade_speed'] * dt

            # Teto: fade-out agressivo
            if b['y'] <= balloon_ceiling:
                b['y'] = balloon_ceiling
                if b['alpha'] > self.CEILING_MAX_ALPHA:
                    b['alpha'] = self.CEILING_MAX_ALPHA
                b['alpha'] -= (b['fade_speed'] * self.CEILING_FADE_MULT) * dt

            if b['alpha'] <= 0:
                self.rising_balloons.remove(b)

        # ---- Auto-finalizar ----
        all_spawned = (self._box_spawned >= len(self.box_pokemon) and
                       self._balloon_spawned >= len(self.balloon_data))
        if all_spawned and not self.rising_sprites and not self.rising_balloons:
            self.final_hold_timer += dt
            if self.final_hold_timer >= self.FINAL_HOLD_DURATION:
                self._finish()

    def _play_victory_music(self):
        try:
            from src.managers.sounds.sound_manager import sound_manager
            sound_manager.play_victory_music()
        except Exception as e:
            print(f"[FINAL_VICTORY] Erro musica: {e}")

    # =================================================================
    # SPAWN
    # =================================================================
    def _spawn_box_pokemon(self):
        if self._box_spawned >= len(self.box_pokemon):
            return

        pkmn = self.box_pokemon[self._box_spawned]
        self._box_spawned += 1

        if isinstance(pkmn, dict):
            pokemon_id = pkmn.get("id", 1)
            name       = pkmn.get("name", "???")
            is_shiny   = pkmn.get("is_shiny", False)
        else:
            pokemon_id = pkmn.id
            name       = pkmn.name
            is_shiny   = pkmn.is_shiny

        sprite = self.pokedex.get_sprite(pokemon_id, "front", is_shiny)
        if sprite is None:
            sprite = self.pokedex.get_portrait(pokemon_id, "normal", is_shiny)
        if sprite is None:
            return

        sw, sh = self._screen_size()

        base_size = self._get_shared_sprite_size()
        if random.random() < 0.25:
            base_size = int(base_size * 1.08)

        sprite_scaled = pygame.transform.smoothscale(sprite, (base_size, base_size))

        cols  = 6
        col_i = self._box_spawned % cols
        col_w = sw / (cols + 1)
        x = col_w * (col_i + 1) + random.uniform(-20, 20)

        fade_start_y = sh * self.BOX_FADE_START_FRACTION

        self.rising_sprites.append({
            'sprite_scaled': sprite_scaled,
            'name':          name,
            'shiny':         is_shiny,
            'x':             x,
            'y':             sh + 120,
            'alpha':         0,
            'speed':         random.uniform(75, 105),
            'fade_speed':    random.uniform(55, 80),
            'size':          base_size,
            'fade_start_y':  fade_start_y,
            'wobble_phase':  random.uniform(0, math.pi * 2),
            'wobble_amp':    random.uniform(4, 10),
        })

    def _spawn_balloon(self):
        if self._balloon_spawned >= len(self.balloon_data):
            return

        counter = self.balloon_data[self._balloon_spawned]
        self._balloon_spawned += 1

        sw, sh = self._screen_size()

        x = random.uniform(sw * 0.15, sw * 0.85)
        fade_start_y = sh * self.BALLOON_FADE_START_FRACTION

        self.rising_balloons.append({
            'label':        counter["label"],
            'value':        counter["value"],
            'x':            x,
            'y':            sh + 40,
            'alpha':        0,
            'speed':        random.uniform(95, 130),   # mais rapido
            'fade_speed':   random.uniform(90, 120),   # fade mais rapido
            'fade_start_y': fade_start_y,
            'wobble_phase': random.uniform(0, math.pi * 2),
        })

    # =================================================================
    # RENDER
    # =================================================================
    def render(self, screen):
        sw, sh = self._screen_size()

        # ===== FUNDO COBRINDO A TELA INTEIRA =====
        self._render_background(screen, 0, 0, sw, sh)
        self._render_top_glow(screen, 0, 0, sw, sh)
        self._render_team(screen, 0, 0, sw, sh)
        self._render_rising_sprites(screen)
        self._render_balloons(screen)
        self._render_title(screen, 0, 0, sw, sh)
        self._render_footer_text(screen, 0, 0, sw, sh)
        self._render_skip_button(screen, 0, 0, sw, sh)

    # -----------------------------------------------------------------
    def _render_background(self, screen, vx, vy, vw, vh):
        overlay = pygame.Surface((vw, vh), pygame.SRCALPHA)
        for y in range(vh):
            t = y / vh
            r = int(8  + 22 * (1 - t) ** 2)
            g = int(10 + 20 * (1 - t) ** 2)
            b = int(26 + 42 * (1 - t) ** 2)
            pygame.draw.line(overlay, (r, g, b), (0, y), (vw, y))
        screen.blit(overlay, (vx, vy))

    def _render_top_glow(self, screen, vx, vy, vw, vh):
        glow_h = int(vh * 0.45)
        glow = pygame.Surface((vw, glow_h), pygame.SRCALPHA)
        for y in range(glow_h):
            t = y / glow_h
            a = int(70 * (1 - t) ** 2)
            pygame.draw.line(glow, (255, 215, 0, a), (0, y), (vw, y))
        screen.blit(glow, (vx, vy))

    def _render_title(self, screen, vx, vy, vw, vh):
        intro_t = min(1.0, self.elapsed / self.INTRO_DURATION)
        intro_t = 1 - (1 - intro_t) ** 3

        title_size = int(vh * 0.078)
        title_font = self._get_font(title_size)
        sub_font   = self._get_font(int(vh * 0.022))

        title = "PARABENS!"
        gold_surf  = title_font.render(title, True, self.GOLD_BRIGHT)
        base_surf  = title_font.render(title, True, self.GOLD)

        pulse = 1.0 + 0.02 * math.sin(self.elapsed * 3.0)
        scale = (0.35 + 0.65 * intro_t) * pulse

        w = max(1, int(gold_surf.get_width()  * scale))
        h = max(1, int(gold_surf.get_height() * scale))

        scaled_gold = pygame.transform.smoothscale(gold_surf, (w, h))
        scaled_base = pygame.transform.smoothscale(base_surf, (w, h))

        cx = vx + vw // 2
        cy = vy + int(vh * 0.085)

        for pad in (18, 12, 7):
            glow_surf = pygame.Surface((w + pad*2, h + pad*2), pygame.SRCALPHA)
            pygame.draw.rect(glow_surf, (255, 215, 0, 26),
                             glow_surf.get_rect(), border_radius=22)
            screen.blit(glow_surf, (cx - w//2 - pad, cy - h//2 - pad))

        screen.blit(scaled_gold, scaled_gold.get_rect(center=(cx, cy - 1)))
        screen.blit(scaled_base, scaled_base.get_rect(center=(cx, cy)))

        if self.elapsed > 0.35:
            a = min(255, int((self.elapsed - 0.35) * 220))
            sub = sub_font.render(
                "Voce completou todos os desafios de Kanto!",
                True, self.TEXT_DIM
            )
            sub.set_alpha(a)
            screen.blit(sub, sub.get_rect(center=(cx, vy + int(vh * 0.150))))

    # -----------------------------------------------------------------
    def _render_team(self, screen, vx, vy, vw, vh):
        if not self.team:
            return

        label_y = vy + int(vh * 0.20)
        label_f = self._get_font(int(vh * 0.027))
        label   = label_f.render("SEU TIME CAMPEAO", True, self.GOLD)
        label_r = label.get_rect(center=(vx + vw // 2, label_y))

        line_w = int(vw * 0.30)
        pygame.draw.line(
            screen, self.GOLD,
            (vx + vw//2 - line_w, label_r.bottom + 5),
            (vx + vw//2 + line_w, label_r.bottom + 5), 2
        )
        screen.blit(label, label_r)

        sprite_size = self._get_shared_sprite_size()

        cols = min(6, len(self.team))
        gap  = int(vw * 0.014)
        total_w = cols * sprite_size + (cols - 1) * gap
        start_x = vx + (vw - total_w) // 2

        cy_base = label_r.bottom + int(vh * 0.055) + sprite_size // 2

        for i, pokemon in enumerate(self.team):
            if i >= self.team_reveal_count:
                continue

            appear = min(1.0, max(0.0, self.team_reveal_count - i))
            appear = 1 - (1 - appear) ** 3
            alpha  = int(255 * appear)

            cx = start_x + i * (sprite_size + gap) + sprite_size // 2
            bob = math.sin(self.elapsed * 1.6 + i * 0.8) * 6
            cy = int(cy_base + bob)

            is_shiny   = getattr(pokemon, 'is_shiny', False)
            aura_color = self.GOLD if is_shiny else (120, 160, 220)

            glow_r = int(sprite_size * 0.62)
            glow = pygame.Surface((glow_r * 2, glow_r * 2), pygame.SRCALPHA)
            base_a = 85 if is_shiny else 45
            pygame.draw.circle(
                glow, (*aura_color, int(base_a * appear)),
                (glow_r, glow_r), glow_r
            )
            screen.blit(glow, (cx - glow_r, cy - glow_r))

            sprite = self.pokedex.get_sprite(pokemon.id, "front", is_shiny)
            if sprite:
                scaled = pygame.transform.smoothscale(sprite, (sprite_size, sprite_size))
                scaled.set_alpha(alpha)
                rect = scaled.get_rect(center=(cx, cy))
                screen.blit(scaled, rect)

            if is_shiny and alpha > 40:
                self._draw_shiny_sparkles(screen, cx, cy, sprite_size, alpha)

            name_f  = self._get_font(max(14, int(sprite_size * 0.135)))
            nm      = pokemon.name
            if len(nm) > 10:
                nm = nm[:9] + "."
            nm_surf = name_f.render(nm, True, self.TEXT_WHITE)
            nm_surf.set_alpha(alpha)
            nm_y = cy + sprite_size // 2 + 20
            screen.blit(nm_surf, nm_surf.get_rect(center=(cx, int(nm_y))))

            lvl_f = self._get_font(max(12, int(sprite_size * 0.105)))
            lvl   = getattr(pokemon, 'level', 1)
            lvl_s = lvl_f.render(f"Nv. {lvl}", True, self.GOLD)
            lvl_s.set_alpha(alpha)
            screen.blit(lvl_s, lvl_s.get_rect(center=(cx, int(nm_y + 18))))

    # -----------------------------------------------------------------
    def _draw_shiny_sparkles(self, screen, cx, cy, size, alpha):
        num = 5
        for i in range(num):
            angle = (self.elapsed * 0.9 + i * (math.pi * 2 / num)) % (math.pi * 2)
            radius = size * 0.55
            sx = cx + math.cos(angle) * radius
            sy = cy + math.sin(angle) * radius * 0.75

            twinkle = 0.5 + 0.5 * math.sin(self.elapsed * 3.0 + i * 1.7)
            sparkle_size = max(3, int(size * 0.055 * (0.65 + 0.45 * twinkle)))

            sa = int(alpha * (0.35 + 0.65 * twinkle))
            if sa <= 8:
                continue

            self._draw_sparkle(screen, sx, sy, sparkle_size, sa)

    def _draw_sparkle(self, screen, cx, cy, size, alpha):
        surf = pygame.Surface((size * 2, size * 2), pygame.SRCALPHA)
        pts = [
            (size, 0),
            (size * 1.25, size * 0.75),
            (size * 2, size),
            (size * 1.25, size * 1.25),
            (size, size * 2),
            (size * 0.75, size * 1.25),
            (0, size),
            (size * 0.75, size * 0.75),
        ]
        pygame.draw.polygon(surf, (255, 255, 200, alpha), pts)
        pygame.draw.polygon(surf, (255, 240, 170, alpha), pts, 1)
        pygame.draw.circle(surf, (255, 255, 255, min(255, alpha + 30)),
                           (size, size), max(1, size // 3))
        screen.blit(surf, (cx - size, cy - size))

    def _draw_star(self, screen, cx, cy, size, color):
        pts = []
        for i in range(10):
            ang = math.radians(-90 + i * 36)
            r = size if i % 2 == 0 else size * 0.45
            pts.append((cx + math.cos(ang) * r, cy + math.sin(ang) * r))
        pygame.draw.polygon(screen, color, pts)
        pygame.draw.polygon(screen, (255, 240, 180), pts, 1)

    # -----------------------------------------------------------------
    def _render_rising_sprites(self, screen):
        for s in self.rising_sprites:
            if s['alpha'] <= 0:
                continue

            sprite_scaled = s['sprite_scaled']
            scaled = sprite_scaled.copy()
            scaled.set_alpha(int(s['alpha']))

            wobble = math.sin(self.elapsed * 2.0 + s['wobble_phase']) * s['wobble_amp']
            x = s['x'] + wobble
            y = s['y']
            rect = scaled.get_rect(center=(x, y))

            if s['shiny']:
                size = s['size']
                glow = pygame.Surface((size + 30, size + 30), pygame.SRCALPHA)
                pygame.draw.circle(
                    glow, (255, 215, 0, 65),
                    (size // 2 + 15, size // 2 + 15),
                    size // 2 + 12
                )
                glow.set_alpha(int(s['alpha']))
                screen.blit(glow, (rect.x - 15, rect.y - 15))

            screen.blit(scaled, rect)

            if s['shiny'] and s['alpha'] > 40:
                self._draw_shiny_sparkles(
                    screen, x, y, s['size'], int(s['alpha'])
                )

            if s['alpha'] > 120:
                nf = self._get_font(max(12, int(s['size'] * 0.14)))
                ns = nf.render(s['name'], True, (220, 230, 245))
                ns.set_alpha(int(s['alpha']))
                screen.blit(ns, ns.get_rect(center=(x, rect.bottom + 14)))

    # -----------------------------------------------------------------
    def _render_balloons(self, screen):
        for b in self.rising_balloons:
            if b['alpha'] <= 0:
                continue

            wobble = math.sin(self.elapsed * 1.4 + b['wobble_phase']) * 16
            x = b['x'] + wobble
            y = b['y']

            label_f = self._get_font(18)
            value_f = self._get_font(26)

            label_s = label_f.render(b['label'], True, (250, 250, 250))
            value_s = value_f.render(str(b['value']), True, self.GOLD_BRIGHT)

            pad_x = 20
            pad_y = 12
            text_w = max(label_s.get_width(), value_s.get_width())
            bw = text_w + pad_x * 2
            bh = label_s.get_height() + value_s.get_height() + pad_y * 2 + 8

            balloon = pygame.Surface((bw, bh), pygame.SRCALPHA)
            pygame.draw.rect(balloon, (24, 34, 60, 240),
                             balloon.get_rect(), border_radius=14)
            pygame.draw.rect(balloon, (*self.GOLD, 255),
                             balloon.get_rect(), 2, border_radius=14)
            pygame.draw.line(balloon, (255, 240, 180, 200),
                             (8, 4), (bw - 8, 4), 1)

            balloon.blit(label_s, label_s.get_rect(
                center=(bw // 2, pad_y + label_s.get_height() // 2)))
            balloon.blit(value_s, value_s.get_rect(
                center=(bw // 2,
                        pad_y + label_s.get_height() + 6 + value_s.get_height() // 2)))

            balloon.set_alpha(int(b['alpha']))
            screen.blit(balloon, balloon.get_rect(center=(x, y)))

    def _render_footer_text(self, screen, vx, vy, vw, vh):
        if self.elapsed <= 3.5:
            return
        a = min(255, int((self.elapsed - 3.5) * 110))

        f1 = self._get_font(int(vh * 0.024))
        f2 = self._get_font(int(vh * 0.018))

        s1 = f1.render("Obrigado por jogar!", True, self.GOLD_BRIGHT)
        s2 = f2.render("Sua jornada em Kanto foi lendaria.", True, self.TEXT_DIM)
        s1.set_alpha(a)
        s2.set_alpha(a)

        y1 = vy + vh - int(vh * 0.10)
        screen.blit(s1, s1.get_rect(center=(vx + vw // 2, y1)))
        screen.blit(s2, s2.get_rect(center=(vx + vw // 2, y1 + int(vh * 0.038))))

    def _render_skip_button(self, screen, vx, vy, vw, vh):
        bw = int(vw * 0.12)
        bh = int(vh * 0.048)
        bx = vx + vw - bw - int(vw * 0.02)
        by = vy + int(vh * 0.02)

        self.skip_button_rect = pygame.Rect(bx, by, bw, bh)

        if self.skip_hovered:
            bg     = (62, 82, 132)
            border = self.GOLD_BRIGHT
        else:
            bg     = (34, 44, 68)
            border = self.GOLD

        pygame.draw.rect(screen, bg, self.skip_button_rect, border_radius=8)
        pygame.draw.rect(screen, border, self.skip_button_rect, 2, border_radius=8)

        f = self._get_font(max(14, int(bh * 0.48)))
        t = f.render("PULAR", True, self.TEXT_WHITE)
        screen.blit(t, t.get_rect(center=self.skip_button_rect.center))