"""Helper de bindings (conveniência)."""
from src.anim.animation_registry import animation_registry


def get_animation_for_trigger(trigger: str):
    return animation_registry.resolve_trigger(trigger)


def all_bindings() -> dict:
    return animation_registry.all_bindings()