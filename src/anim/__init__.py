"""
Runtime de animações do jogo.

Este pacote é LEVE — só depende de pygame e json.
O editor visual (src/ui/anim_editor_scene/) usa este pacote para preview.
O jogo usa este pacote para reproduzir animações em runtime.

Uso básico:
    from src.anim.animation_manager import animation_manager
    animation_manager.play_by_trigger(
        "item.antidote.use_on_ally", anchor_target=pokemon
    )
"""
from src.anim.animation import AnimDefinition
from src.anim.layer import (
    Keyframe, LayerDef, SpriteLayerDef, EmitterLayerDef, FilterLayerDef,
)
from src.anim.animator import Animator
from src.anim.animation_manager import AnimationManager, animation_manager
from src.anim.animation_registry import AnimationRegistry, animation_registry

__all__ = [
    "AnimDefinition",
    "Keyframe", "LayerDef", "SpriteLayerDef", "EmitterLayerDef", "FilterLayerDef",
    "Animator",
    "AnimationManager", "animation_manager",
    "AnimationRegistry", "animation_registry",
]