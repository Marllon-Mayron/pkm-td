# src/scenes/game_scene/components/capture_shake_animation.py

"""
Animação in-world de captura de pokémon.

Fases (sucesso):
    drop               -> bola cai do alto (pokémon SEMPRE visível)
    impact             -> bola bate no pokémon (pokémon visível)
    ricochet           -> bola sobe em arco e cai — DURANTE este trecho o
                          pokémon encolhe e vira energia vermelha (suck-in)
    shakes             -> N balanços suaves (pivot bottom-center)
    click              -> wiggle final
    success_particles  -> estrelinhas douradas
    (fim → overlay)

Fases (fracasso): mesma coisa até `shakes`; depois:
    open               -> bola abre (frame half), pokémon reaparece pequeno
    escape_jump        -> pokémon cresce até 100%, pula
    escape_fall        -> cai
    escape_bounce      -> quica
    escaped            -> bola vazia (frame open)
"""
import math
import random
import pygame


class CaptureShakeAnimation:

    # ============ TIMING ============
    DROP_DURATION              = 0.28
    IMPACT_DURATION            = 0.10
    RICOCHET_DURATION          = 0.60
    SHAKE_DURATION             = 0.55
    CLICK_DURATION             = 0.38
    SUCCESS_PARTICLES_DURATION = 0.60
    OPEN_DURATION              = 0.18
    ESCAPE_JUMP_DURATION       = 0.42
    ESCAPE_FALL_DURATION       = 0.30
    ESCAPE_BOUNCE_DURATION     = 0.42
    ESCAPED_DURATION           = 0.25

    TILE_SCALE = 16 / 24

    # ============ VISUAL ============
    DROP_HEIGHT          = 40.0
    RICOCHET_HEIGHT      = 42.0
    RICOCHET_SIDE        = 10.0
    BALL_SETTLE_Y_OFFSET = 6.0

    SHAKE_ANGLE    = 12.0
    BALL_BASE_SIZE = 10
    BALL_MIN_SIZE  = 6

    MAX_DURATION = 15.0

    def __init__(self, game_scene, enemy, ball_frames, pokemon_sprite,
                 num_shakes, is_success, pokemon_base_scale=1.0):
        self.game_scene = game_scene
        self.enemy = enemy
        self.ball_frames = ball_frames or {}
        self.pokemon_sprite = pokemon_sprite
        self.num_shakes = max(1, int(num_shakes))
        self.is_success = bool(is_success)
        self.pokemon_base_scale = float(pokemon_base_scale) or 1.0

        # ===== ÂNCORA (posição do pokémon) =====
        self.world_x = float(enemy.x)
        self.world_y = float(enemy.y)

        # Guarda para restaurar no fim (enemy pode andar durante a animação)
        self._enemy_initial_x = float(enemy.x)
        self._enemy_initial_y = float(enemy.y)

        # Posição atual da bola
        self.ball_wx = self.world_x
        self.ball_wy = self.world_y - self.DROP_HEIGHT

        # Direção do ricochete
        self.ball_side = random.choice([-1.0, 1.0])

        # Estado
        self.active = True
        self.state = "drop"
        self.elapsed = 0.0
        self.total_elapsed = 0.0
        self.shakes_done = 0

        # Transform da bola
        self.rotation = 0.0
        self.ball_alpha = 255

        # Pokémon (offsets relativos à âncora)
        self.pokemon_scale = 1.0
        self.pokemon_red = 0.0
        self.pokemon_alpha = 255
        self.pokemon_ox = 0.0
        self.pokemon_oy = 0.0
        self.pokemon_rot = 0.0  # NOVO: rotação sutil durante suck-in

        # Partículas
        self._particles = []

        # Callback
        self.on_complete = None

        print(f"[CAPTURE_ANIM] init | shakes={self.num_shakes} | "
              f"success={self.is_success} | base_scale={self.pokemon_base_scale:.2f}")

    # ================================================================
    # UPDATE
    # ================================================================
    def update(self, dt):
        if not self.active:
            return
        self.total_elapsed += dt
        if self.total_elapsed >= self.MAX_DURATION:
            print(f"[CAPTURE_ANIM] TIMEOUT em {self.state} — forçando fim")
            self._finish(self.is_success)
            return
        self.elapsed += dt

        if   self.state == "drop":              self._update_drop()
        elif self.state == "impact":            self._update_impact()
        elif self.state == "ricochet":          self._update_ricochet()
        elif self.state == "shakes":            self._update_shakes()
        elif self.state == "click":             self._update_click()
        elif self.state == "success_particles": self._update_success_particles(dt)
        elif self.state == "open":              self._update_open()
        elif self.state == "escape_jump":       self._update_escape_jump()
        elif self.state == "escape_fall":       self._update_escape_fall()
        elif self.state == "escape_bounce":     self._update_escape_bounce()
        elif self.state == "escaped":           self._update_escaped()

    # -------- FASES DA BOLA --------
    def _update_drop(self):
        """Bola cai por GRAVIDADE (ease-in: começa devagar, acelera)."""
        p = min(1.0, self.elapsed / self.DROP_DURATION)
        # Gravidade = quadrática. Levemente mais forte que p² para peso visual.
        ease = p ** 2.2

        self.ball_wx = self.world_x
        self.ball_wy = self.world_y - self.DROP_HEIGHT * (1.0 - ease)

        if self.elapsed >= self.DROP_DURATION:
            self.state = "impact"
            self.elapsed = 0.0
            self.ball_wx = self.world_x
            self.ball_wy = self.world_y

    def _update_impact(self):
        # Micro squash do pokémon no impacto (feedback)
        p = min(1.0, self.elapsed / self.IMPACT_DURATION)
        # Compressão momentânea: 1.0 → 0.94 → 1.0
        squash = math.sin(p * math.pi) * 0.06
        self.pokemon_scale = 1.0 - squash

        if self.elapsed >= self.IMPACT_DURATION:
            self.pokemon_scale = 1.0
            self.state = "ricochet"
            self.elapsed = 0.0

    def _update_ricochet(self):
        """
        Bola faz um arco grande pra cima e cai.
        DURANTE ESSE TRECHO, o pokémon é sugado pra dentro da bola.
        """
        p = min(1.0, self.elapsed / self.RICOCHET_DURATION)

        # ===== TRAJETÓRIA DA BOLA =====
        self.ball_wx = self.world_x + self.ball_side * self.RICOCHET_SIDE * p

        # Parábola natural (pico em p=0.5)
        arc = -4.0 * self.RICOCHET_HEIGHT * p * (1.0 - p)
        settle = p * self.BALL_SETTLE_Y_OFFSET
        self.ball_wy = self.world_y + arc + settle

        # ===== SUCK-IN DO POKÉMON =====
        # ease-in forte: fica grande por mais tempo, é sugado rápido no fim
        ease = p ** 2.6

        self.pokemon_scale = max(0.0, 1.0 - ease)
        # Red fica saturado só no finalzinho
        self.pokemon_red = min(1.0, max(0.0, (p - 0.15) * 1.6))
        self.pokemon_alpha = int(255 * (1.0 - ease * 0.95))

        # Wobble: gira levemente conforme encolhe (sensação de sucção)
        self.pokemon_rot = self.ball_side * ease * 25.0

        # Pokémon se move até o ponto FINAL de pouso da bola
        final_ox = self.ball_side * self.RICOCHET_SIDE
        final_oy = self.BALL_SETTLE_Y_OFFSET
        self.pokemon_ox = final_ox * ease
        self.pokemon_oy = final_oy * ease

        if self.elapsed >= self.RICOCHET_DURATION:
            self.ball_wx = self.world_x + self.ball_side * self.RICOCHET_SIDE
            self.ball_wy = self.world_y + self.BALL_SETTLE_Y_OFFSET
            self.pokemon_scale = 0.0
            self.pokemon_alpha = 0
            self.pokemon_rot = 0.0
            self.state = "shakes"
            self.elapsed = 0.0
            self.shakes_done = 0
            self.rotation = 0.0

    # -------- SHAKES SUAVES --------
    def _update_shakes(self):
        p = min(1.0, self.elapsed / self.SHAKE_DURATION)
        # 1 ciclo senoidal com ease-out no final (balanço desacelera)
        decay = 1.0 - 0.15 * p
        self.rotation = math.sin(p * 2.0 * math.pi) * self.SHAKE_ANGLE * decay

        if self.elapsed >= self.SHAKE_DURATION:
            self.shakes_done += 1
            self.elapsed = 0.0
            self.rotation = 0.0
            if self.shakes_done >= self.num_shakes:
                if self.is_success:
                    self.state = "click"
                else:
                    self.state = "open"

    def _update_click(self):
        p = min(1.0, self.elapsed / self.CLICK_DURATION)
        # Damping quadrático: oscila e para suave
        damp = (1.0 - p) ** 2
        self.rotation = math.sin(self.elapsed * 26.0) * 4.0 * damp
        if self.elapsed >= self.CLICK_DURATION:
            self.rotation = 0.0
            self._spawn_success_particles()
            self.state = "success_particles"
            self.elapsed = 0.0

    def _update_success_particles(self, dt):
        self._update_particles(dt)
        if self.elapsed >= self.SUCCESS_PARTICLES_DURATION:
            self._finish(True)

    # -------- FASES DE FUGA --------
    def _update_open(self):
        if self.elapsed >= self.OPEN_DURATION:
            self.state = "escape_jump"
            self.elapsed = 0.0
            # Pokémon começa pequeno e vermelho (saiu da bola agora)
            self.pokemon_scale = 0.22
            self.pokemon_red = 1.0
            self.pokemon_alpha = 255
            self.pokemon_ox = 0.0
            self.pokemon_oy = 0.0
            self.pokemon_rot = 0.0

    def _update_escape_jump(self):
        """Pokémon sai da bola, cresce e sobe num arco natural."""
        p = min(1.0, self.elapsed / self.ESCAPE_JUMP_DURATION)
        # Curva de crescimento: ease-out (rápido no começo, suave no fim)
        grow = 1.0 - (1.0 - p) ** 3

        # NUNCA passa de 1.0
        self.pokemon_scale = 0.22 + grow * 0.78
        self.pokemon_red = max(0.0, 1.0 - grow * 1.4)

        # Subida em arco (parábola): pico em ~p=0.55
        jump_h = 22.0
        arc = -4.0 * jump_h * p * (1.0 - p) / (0.55 * 0.45 * 4.0) * 0.55 * 0.45 * 4.0
        # simplificando: apenas uma parábola normal com pico em p=0.5
        arc = -4.0 * jump_h * p * (1.0 - p)
        self.pokemon_oy = arc
        self.pokemon_ox = 0.0

        if self.elapsed >= self.ESCAPE_JUMP_DURATION:
            self.state = "escape_fall"
            self.elapsed = 0.0
            self.pokemon_scale = 1.0
            self.pokemon_oy = 0.0

    def _update_escape_fall(self):
        p = min(1.0, self.elapsed / self.ESCAPE_FALL_DURATION)
        # Gravidade = ease-in
        ease = p ** 2.0
        self.pokemon_scale = 1.0
        self.pokemon_red = 0.0
        self.pokemon_oy = -22.0 * (1.0 - ease)
        if self.elapsed >= self.ESCAPE_FALL_DURATION:
            self.state = "escape_bounce"
            self.elapsed = 0.0
            self.pokemon_oy = 0.0

    def _update_escape_bounce(self):
        p = min(1.0, self.elapsed / self.ESCAPE_BOUNCE_DURATION)
        # Quica duas vezes com amplitude decrescente
        amplitude = (1.0 - p) * 6.0
        self.pokemon_oy = -abs(math.sin(p * 2.0 * math.pi)) * amplitude
        self.pokemon_scale = 1.0
        if self.elapsed >= self.ESCAPE_BOUNCE_DURATION:
            self.state = "escaped"
            self.elapsed = 0.0
            self.pokemon_scale = 0.0
            self.pokemon_alpha = 0

    def _update_escaped(self):
        if self.elapsed >= self.ESCAPED_DURATION:
            self._finish(False)

    # -------- PARTÍCULAS --------
    def _spawn_success_particles(self):
        self._particles = []
        ox, oy = self.ball_wx, self.ball_wy - 4

        for i in range(14):
            angle = (i / 14.0) * math.tau + random.uniform(-0.25, 0.25)
            speed = random.uniform(28, 55)
            life = random.uniform(0.40, 0.65)
            self._particles.append({
                'x': ox, 'y': oy,
                'vx': math.cos(angle) * speed,
                'vy': math.sin(angle) * speed * 0.75 - 14,
                'life': life, 'max_life': life,
                'size': random.uniform(2.2, 4.0),
                'rot': random.uniform(0, math.pi),
                'color': random.choice([
                    (255, 240, 120), (255, 215, 0), (255, 255, 200),
                ]),
            })

    def _update_particles(self, dt):
        for p in self._particles[:]:
            p['x'] += p['vx'] * dt
            p['y'] += p['vy'] * dt
            p['vy'] += 70 * dt
            p['rot'] += dt * 5.0
            p['life'] -= dt
            if p['life'] <= 0:
                self._particles.remove(p)

    def _finish(self, success):
        self.active = False
        # Restaura posição do inimigo (pode ter andado durante a animação)
        if self.enemy is not None:
            try:
                self.enemy.x = self._enemy_initial_x
                self.enemy.y = self._enemy_initial_y
            except Exception:
                pass
        print(f"[CAPTURE_ANIM] finish | success={success} | "
              f"total={self.total_elapsed:.2f}s")
        if self.on_complete:
            self.on_complete(success)

    # ================================================================
    # RENDER
    # ================================================================
    def render(self, screen, camera, screen_manager):
        if not self.active:
            return

        # Pokémon visível em TODAS as fases "de pokémon"
        # (drop/impact mostram ele normal; ricochet/escape animam)
        if self.state in ("drop", "impact", "ricochet",
                          "escape_jump", "escape_fall", "escape_bounce"):
            self._render_pokemon(screen, camera, screen_manager)

        self._render_ball(screen, camera, screen_manager)

        if self.state == "success_particles":
            self._render_particles(screen, camera, screen_manager)

    # ------------------------------------------------------------------
    def _render_pokemon(self, screen, camera, screen_manager):
        if self.pokemon_sprite is None:
            return
        if self.pokemon_scale <= 0.01 or self.pokemon_alpha <= 0:
            return

        px = self.world_x + self.pokemon_ox
        py = self.world_y + self.pokemon_oy
        sx, sy = screen_manager.world_to_screen(px, py, camera)

        # ===== MESMA ESCALA DO INIMIGO =====
        zoom = camera.zoom * screen_manager.render_scale * self.TILE_SCALE

        bw, bh = self.pokemon_sprite.get_size()
        scale = self.pokemon_scale * self.pokemon_base_scale
        w = max(1, int(bw * zoom * scale))
        h = max(1, int(bh * zoom * scale))

        # ===== NEAREST-NEIGHBOR (igual ao inimigo) =====
        scaled = pygame.transform.scale(self.pokemon_sprite, (w, h))

        if self.pokemon_red > 0.01:
            scaled = self._tint_red(scaled, self.pokemon_red)

        if abs(self.pokemon_rot) > 0.5:
            scaled = pygame.transform.rotozoom(scaled, self.pokemon_rot, 1.0)

        if self.pokemon_alpha < 255:
            scaled = scaled.copy()
            scaled.set_alpha(self.pokemon_alpha)

        # ===== ANCORAGEM CENTER (igual ao inimigo) =====
        rect = scaled.get_rect()
        rect.center = (int(sx), int(sy))
        screen.blit(scaled, rect)

    @staticmethod
    def _tint_red(sprite, intensity):
        if intensity <= 0.01:
            return sprite
        result = sprite.copy()
        factor = int(255 * (1.0 - intensity * 0.75))
        mask = pygame.Surface(sprite.get_size(), pygame.SRCALPHA)
        mask.fill((255, factor, factor, 255))
        result.blit(mask, (0, 0), special_flags=pygame.BLEND_RGBA_MULT)
        boost = pygame.Surface(sprite.get_size(), pygame.SRCALPHA)
        boost.fill((int(90 * intensity), 0, 0, 0))
        result.blit(boost, (0, 0), special_flags=pygame.BLEND_RGBA_ADD)
        return result

    # ------------------------------------------------------------------
    def _current_ball_frame(self):
        f = self.ball_frames
        if self.state in ("drop", "shakes", "click", "success_particles"):
            return f.get("closed")
        if self.state == "impact":
            return f.get("impact") or f.get("closed")
        if self.state == "ricochet":
            return f.get("closed")
        if self.state in ("open", "escape_jump",
                          "escape_fall", "escape_bounce"):
            return f.get("half") or f.get("closed")
        if self.state == "escaped":
            return f.get("open") or f.get("closed")
        return f.get("closed")

    def _render_ball(self, screen, camera, screen_manager):
        sprite = self._current_ball_frame()
        if sprite is None:
            return

        sx, sy = screen_manager.world_to_screen(
            self.ball_wx, self.ball_wy, camera
        )
        # mesma escala do mundo
        zoom = camera.zoom * screen_manager.render_scale * self.TILE_SCALE

        size = max(self.BALL_MIN_SIZE, int(self.BALL_BASE_SIZE * zoom * 1.5))
        # 1.5 é só pra bola não ficar minúscula; ajuste a gosto
        if sprite.get_width() != size:
            sprite = pygame.transform.scale(sprite, (size, size))

        if abs(self.rotation) > 0.1:
            rotated = self._rotate_around_bottom(sprite, self.rotation)
            if self.ball_alpha < 255:
                rotated = rotated.copy()
                rotated.set_alpha(self.ball_alpha)
            rect = rotated.get_rect()
            rect.center = (int(sx), int(sy))
            screen.blit(rotated, rect)
        else:
            if self.ball_alpha < 255:
                sprite = sprite.copy()
                sprite.set_alpha(self.ball_alpha)
            rect = sprite.get_rect()
            rect.midbottom = (int(sx), int(sy))
            screen.blit(sprite, rect)

    @staticmethod
    def _rotate_around_bottom(sprite, angle):
        """
        Rotaciona em torno do pivot bottom-center. Retorna surface quadrada
        com o pivot no centro — quem chamar deve usar `rect.center`.
        """
        w, h = sprite.get_size()
        canvas_size = int(math.hypot(w, h)) + 4
        canvas = pygame.Surface((canvas_size, canvas_size), pygame.SRCALPHA)
        px = w // 2
        py = h
        canvas.blit(sprite,
                    (canvas_size // 2 - px, canvas_size // 2 - py))
        return pygame.transform.rotozoom(canvas, angle, 1.0)

    # ------------------------------------------------------------------
    def _render_particles(self, screen, camera, screen_manager):
        for p in self._particles:
            sx, sy = screen_manager.world_to_screen(p['x'], p['y'], camera)
            alpha = max(0, int(255 * (p['life'] / p['max_life'])))
            size = max(1, int(p['size'] * camera.zoom *
                              screen_manager.render_scale))
            self._draw_star(screen, sx, sy, size, p['color'], alpha, p['rot'])

    @staticmethod
    def _draw_star(screen, cx, cy, size, color, alpha, rot):
        canvas_size = size * 4
        surf = pygame.Surface((canvas_size, canvas_size), pygame.SRCALPHA)
        center = canvas_size // 2
        points = []
        for i in range(8):
            angle = rot + (math.pi / 4) * i
            r = size if i % 2 == 0 else size * 0.35
            points.append((center + math.cos(angle) * r,
                           center + math.sin(angle) * r))
        pygame.draw.polygon(surf, (*color, alpha), points)
        pygame.draw.circle(surf, (255, 255, 255, min(255, alpha + 40)),
                           (center, center), max(1, size // 2))
        screen.blit(surf, (int(cx) - center, int(cy) - center))