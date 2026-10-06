"""Gerenciador de animações ativas."""
from typing import Optional, List

from src.anim.animator import Animator
from src.anim.animation_registry import animation_registry


class AnimationManager:
    def __init__(self):
        self.active: List[Animator] = []
        self._by_trigger: dict = {}

    # =================================================================
    def play_by_trigger(self,
                        trigger: str,
                        anchor_target=None,
                        anchor_attacker=None,
                        anchor_projectile=None,
                        world_pos=None,
                        screen_pos=None,
                        loop_override=None) -> Optional[Animator]:
        defn = animation_registry.resolve_trigger(trigger)
        if defn is None:
            return None
        return self.play_definition(
            defn, anchor_target, anchor_attacker, anchor_projectile,
            world_pos, screen_pos, loop_override,
        )

    def play_definition(self, defn,
                        anchor_target=None,
                        anchor_attacker=None,
                        anchor_projectile=None,
                        world_pos=None,
                        screen_pos=None,
                        loop_override=None) -> Animator:
        anim = Animator(defn, anchor_target, anchor_attacker,
                        anchor_projectile, world_pos, screen_pos, loop_override)
        self.active.append(anim)
        return anim

    def stop_by_trigger(self, trigger: str):
        for anim in self._by_trigger.get(trigger, []):
            anim.stop()
        self._by_trigger.pop(trigger, None)

    def stop_all(self):
        for anim in self.active:
            anim.stop()
        self.active.clear()
        self._by_trigger.clear()

    # =================================================================
    def update(self, dt: float):
        for anim in self.active:
            anim.update(dt)
        self.active = [a for a in self.active if not a.is_finished()]
        for k in list(self._by_trigger.keys()):
            self._by_trigger[k] = [a for a in self._by_trigger[k] if not a.is_finished()]
            if not self._by_trigger[k]:
                del self._by_trigger[k]

    def render(self, screen, camera=None, screen_manager=None):
        world = [a for a in self.active if a.defn.space == "world"]
        scr = [a for a in self.active if a.defn.space == "screen"]
        for anim in world:
            anim.render(screen, camera, screen_manager)
        for anim in scr:
            anim.render(screen, camera, screen_manager)


animation_manager = AnimationManager()