# src/battle/effects/specific/weather/rain_particle_system.py

import pygame
import random


class RainDrop:
    """
    Uma gota individual.

    Cai sempre no frame 0 do sprite sheet (posição 0,0 → 16x16).
    A direção é definida pelo sistema (toda a chuva vai pro mesmo lado).

      direction = +1 (direita) → frame 0 original
      direction = -1 (esquerda) → frame 0 invertido horizontalmente
    """

    # ===== Dimensões do sprite sheet =====
    # Total: 80x16, 5 frames lado a lado → cada frame 16x16.
    # Só usamos o frame 0 (posição 0,0).
    FRAME_W = 16
    FRAME_H = 16

    # ===== Inclinação da queda =====
    # 0.5 = ~27° da vertical
    SLOPE_X_FACTOR = 0.5

    def __init__(self, sprite_sheet,
                 x, y, scale, fall_duration, ground_y, min_x, max_x,
                 direction):
        self.sprite_sheet = sprite_sheet
        self.x = float(x)
        self.y = float(y)
        self.scale = scale
        self.ground_y = ground_y
        self.min_x = min_x
        self.max_x = max_x
        self.direction = direction  # -1 = esquerda, +1 = direita

        # Velocidade vertical calculada para durar `fall_duration` segundos
        vertical_distance = max(1.0, ground_y - y)
        if fall_duration > 0:
            self.vy = vertical_distance / fall_duration
        else:
            self.vy = 500.0 * scale

        # Horizontal proporcional à direção
        self.vx = self.vy * RainDrop.SLOPE_X_FACTOR * self.direction

    # ------------------------------------------------------------------ #
    @property
    def alive(self) -> bool:
        return self.y < self.ground_y and self.min_x <= self.x <= self.max_x

    # ------------------------------------------------------------------ #
    def update(self, dt: float):
        self.x += self.vx * dt
        self.y += self.vy * dt

        if self.y >= self.ground_y:
            self.y = self.ground_y

    # ------------------------------------------------------------------ #
    def draw(self, surface: pygame.Surface):
        if not self.alive:
            return

        if not self.sprite_sheet:
            return

        fw = RainDrop.FRAME_W
        fh = RainDrop.FRAME_H

        # ===== PEGA O FRAME 0 (0, 0, 16, 16) =====
        src = pygame.Rect(0, 0, fw, fh)
        try:
            frame_surf = self.sprite_sheet.subsurface(src)
        except ValueError:
            return

        # ===== INVERTE SE FOR PRA ESQUERDA =====
        # O frame 0 original aponta pra direita.
        if self.direction < 0:
            frame_surf = pygame.transform.flip(frame_surf, True, False)

        # ===== ESCALA =====
        w = max(1, int(fw * self.scale))
        h = max(1, int(fh * self.scale))

        if self.scale != 1.0:
            frame_surf = pygame.transform.smoothscale(frame_surf, (w, h))

        rect = frame_surf.get_rect(center=(int(self.x), int(self.y)))
        surface.blit(frame_surf, rect)


class RainParticleSystem:
    """
    Sistema de partículas de chuva.

    A direção (esquerda/direita) é sorteada UMA VEZ no start() e vale
    para toda a chuva até o sistema ser reiniciado.
    """

    # Tempo que cada gota leva para cair (segundos)
    FALL_DURATION = 1.2

    def __init__(self, viewport_rect: pygame.Rect, drop_count: int = 120, scale: float = 1.0):
        self.viewport_rect = pygame.Rect(viewport_rect)
        self.scale = scale
        self.drop_count = max(1, int(drop_count))
        self.drops = []
        self.sprite_sheet = None
        self.active = False

        # ===== DIREÇÃO GLOBAL DA CHUVA =====
        # -1 = esquerda, +1 = direita
        # Sorteada em start(). Toda a chuva usa essa direção.
        self.direction = -1

        self._spawn_accumulator = 0.0
        self._spawn_every = 0.03  # spawn frequente para cobrir a tela

        self._load_sprite()

    # ------------------------------------------------------------------ #
    def _load_sprite(self):
        import os
        try:
            from src.config.paths import PROJECT_ROOT, SPRITES_PATH
        except Exception as e:
            print(f"[RAIN] Não foi possível importar PROJECT_ROOT/SPRITES_PATH: {e}")
            self.sprite_sheet = None
            return

        candidate_paths = [
            os.path.join(str(SPRITES_PATH), "Particle", "Rain.None.png"),
            os.path.join(str(SPRITES_PATH), "Particle", "Rain.png"),
            os.path.join(str(SPRITES_PATH), "Particle", "rain.png"),
            os.path.join(str(PROJECT_ROOT), "res", "weather", "rain_particles.png"),
        ]

        for path in candidate_paths:
            if not os.path.isfile(path):
                continue
            try:
                img = pygame.image.load(path)
                try:
                    img = img.convert_alpha()
                except pygame.error:
                    pass

                self.sprite_sheet = img

                w, h = img.get_width(), img.get_height()
                print(f"[RAIN] Sprite carregado: {path} ({w}x{h})")
                return
            except Exception as e:
                print(f"[RAIN] Falha ao carregar '{path}': {e}")

        print("[RAIN] Sprite NÃO encontrado.")
        self.sprite_sheet = None

    def set_viewport(self, viewport_rect: pygame.Rect):
        self.viewport_rect = pygame.Rect(viewport_rect)

    # ------------------------------------------------------------------ #
    def start(self):
        if self.active:
            return
        self.active = True
        self.drops.clear()

        # ===== SORTEIA A DIREÇÃO UMA VEZ =====
        self.direction = random.choice((-1, 1))
        dir_name = "esquerda" if self.direction < 0 else "direita"
        print(f"[RAIN] Chuva iniciada na direção: {dir_name}")

        for _ in range(self.drop_count):
            self._spawn(initial=True)

    def stop(self):
        self.active = False
        self.drops.clear()
        self._spawn_accumulator = 0.0

    # ------------------------------------------------------------------ #
    def _spawn(self, initial: bool = False):
        vp = self.viewport_rect

        # ===== COBRE TODA A LARGURA =====
        # Spawna em toda a extensão horizontal + folga dos dois lados,
        # para a chuva preencher a tela inteira.
        x = random.uniform(vp.x - 200, vp.right + 200)

        # ===== POSIÇÃO VERTICAL =====
        if initial:
            y = random.uniform(vp.y, vp.bottom - 30)
        else:
            y = vp.y - random.uniform(20, 120)

        # ===== LIMITES DE VIDA =====
        # Amplos para a gota atravessar a tela inteira antes de morrer.
        min_x = vp.x - vp.width * 2
        max_x = vp.right + vp.width * 2

        self.drops.append(RainDrop(
            sprite_sheet=self.sprite_sheet,
            x=x, y=y,
            scale=self.scale,
            fall_duration=RainParticleSystem.FALL_DURATION,
            ground_y=vp.bottom - 2,
            min_x=min_x,
            max_x=max_x,
            direction=self.direction,
        ))

    # ------------------------------------------------------------------ #
    def update(self, dt: float):
        if not self.active:
            return

        for d in self.drops:
            d.update(dt)

        self.drops = [d for d in self.drops if d.alive]

        self._spawn_accumulator += dt
        while self._spawn_accumulator >= self._spawn_every:
            self._spawn_accumulator -= self._spawn_every
            if len(self.drops) < self.drop_count * 4:
                self._spawn(initial=False)

    # ------------------------------------------------------------------ #
    def render(self, surface: pygame.Surface):
        if not self.active or not self.sprite_sheet:
            return
        for d in self.drops:
            d.draw(surface)