# src/utils/pet_sprite.py
"""
Pet do jogador — sprite InMap com 3 estados: SLEEP, IDLE, HOP.

Os frames vêm do PokemonSpriteManager (mesmo loader usado na Pokédex).
Esta classe só orquestra a máquina de estados e o offset vertical do hop.
"""
import math
import random
import pygame
from typing import Optional


class PetState:
    SLEEP = "sleep"
    IDLE  = "idle"
    HOP   = "hop"


class PetAnimator:
    # ===== Velocidade de troca de frames de cada animação =====
    FRAME_TIME_SLEEP = 0.55
    FRAME_TIME_IDLE  = 0.22
    FRAME_TIME_HOP   = 0.12

    # ===== Duração de cada estado (segundos) =====
    # O pet passa a maior parte do tempo ACORDADO. Dorme por bem mais
    # tempo quando finalmente vai dormir, pra não ficar num ciclo
    # curto de "dorme-acorda-dorme-acorda".
    DUR_SLEEP = (9.0, 16.0)
    DUR_IDLE  = (4.0, 7.0)
    DUR_HOP   = (1.0, 2.0)

    HOP_HEIGHT = 6
    HOP_PERIOD = 0.35

    def __init__(self, direction: str = "down"):
        self.direction = direction
        self.state = PetState.SLEEP
        self.state_timer = 0.0
        self.state_duration = random.uniform(*self.DUR_SLEEP)

        self.frame_idx = 0
        self.frame_timer = 0.0

        self._frames: dict = {}
        self._pid: Optional[int] = None
        self._shiny: bool = False

    # -----------------------------------------------------------------
    def set_frames(self, frames_by_anim: dict, pid: Optional[int],
                   shiny: bool = False, reset_state: bool = True):
        self._frames = frames_by_anim or {}
        self._pid = pid
        self._shiny = shiny
        if reset_state:
            self._reset()

    def _reset(self):
        self.state = PetState.SLEEP
        self.state_timer = 0.0
        self.state_duration = random.uniform(*self.DUR_SLEEP)
        self.frame_idx = 0
        self.frame_timer = 0.0

    # -----------------------------------------------------------------
    def _pick(self, anim_name: str) -> list:
        f = self._frames.get(anim_name, [])
        if f:
            return f
        for v in self._frames.values():
            if v:
                return v
        return []

    def _transition(self):
        if self.state == PetState.SLEEP:
            # Dormindo → acorda e fica idle
            self.state = PetState.IDLE
            self.state_duration = random.uniform(*self.DUR_IDLE)

        elif self.state == PetState.IDLE:
            # Idle → 25% volta a dormir, 75% pula
            if random.random() < 0.25:
                self.state = PetState.SLEEP
                self.state_duration = random.uniform(*self.DUR_SLEEP)
            else:
                self.state = PetState.HOP
                self.state_duration = random.uniform(*self.DUR_HOP)

        elif self.state == PetState.HOP:
            # Pular → volta a ficar idle
            self.state = PetState.IDLE
            self.state_duration = random.uniform(*self.DUR_IDLE)

        self.state_timer = 0.0
        self.frame_idx = 0
        self.frame_timer = 0.0

    # -----------------------------------------------------------------
    def update(self, dt: float):
        if self._pid is None:
            return

        self.state_timer += dt
        if self.state_timer >= self.state_duration:
            self._transition()

        if self.state == PetState.SLEEP:
            ft = self.FRAME_TIME_SLEEP
        elif self.state == PetState.IDLE:
            ft = self.FRAME_TIME_IDLE
        else:
            ft = self.FRAME_TIME_HOP

        self.frame_timer += dt
        if self.frame_timer >= ft:
            self.frame_timer -= ft
            self.frame_idx += 1

    # -----------------------------------------------------------------
    def get_frame(self) -> Optional[pygame.Surface]:
        if self._pid is None:
            return None

        if self.state == PetState.SLEEP:
            frames = self._pick("sleep") or self._pick("idle")
            if not frames:
                return None
            # Cicla mesmo em SLEEP, pra não ficar "congelado" se
            # o Sleep-Anim tiver mais de 1 frame.
            return frames[self.frame_idx % len(frames)]

        if self.state == PetState.IDLE:
            frames = self._pick("idle") or self._pick("walk")
            if not frames:
                return None
            return frames[self.frame_idx % len(frames)]

        # HOP
        frames = self._pick("walk") or self._pick("idle")
        if not frames:
            return None
        return frames[self.frame_idx % len(frames)]

    def get_offset_y(self) -> int:
        """Deslocamento vertical (só durante o hop). Negativo = pra cima."""
        if self.state != PetState.HOP:
            return 0
        phase = self.state_timer / self.HOP_PERIOD
        return int(-abs(math.sin(phase * math.pi)) * self.HOP_HEIGHT)

    def is_sleeping(self) -> bool:
        return self.state == PetState.SLEEP