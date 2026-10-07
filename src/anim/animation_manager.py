"""Gerenciador central de animações ativas.

Ponto único de acesso a TODAS as animações do editor — de qualquer cena.

Uso básico:
    from src.anim.animation_manager import animation_manager

    # 1. Por trigger (bindings.json)
    animation_manager.play_by_trigger(
        "item.potion.use_on_ally", anchor_target=pokemon
    )

    # 2. Por caminho direto
    animation_manager.play("effects/shiny_sparkle", anchor_target=pokemon)

    # 3. Em posição de tela fixa
    animation_manager.play_at_screen("ui/hover_pop", 400, 200)

    # 4. Em posição do mundo fixa
    animation_manager.play_at_world("effects/dust", world_x, world_y)

    # 5. Entre dois atores (attacker → target)
    animation_manager.play_between("moves/thunder", attacker, target)

    # 6. Tela cheia (filtro, flash)
    animation_manager.play_screen("ui/damage_flash")

No game loop (chamar SEMPRE, uma vez por cena ativa):
    animation_manager.update(dt)

No render (na ordem que você quiser — world atrás, screen na frente):
    animation_manager.render(screen, camera, screen_manager, space="world")
    # ... renderiza entidades ...
    animation_manager.render(screen, camera, screen_manager, space="screen")
"""
from typing import Optional, List, Iterable

from src.anim.animator import Animator
from src.anim.animation_registry import animation_registry


class AnimationManager:

    def __init__(self):
        self.active: List[Animator] = []
        # Índice reverso: trigger/caminho -> lista de animators ativos
        self._by_key: dict = {}

    # =================================================================
    # API PRINCIPAL
    # =================================================================
    def play_by_trigger(self,
                        trigger: str,
                        anchor_target=None,
                        anchor_attacker=None,
                        anchor_projectile=None,
                        world_pos=None,
                        screen_pos=None,
                        loop_override=None,
                        exclusive: bool = False) -> Optional[Animator]:
        """Toca a animação mapeada para `trigger` em bindings.json.

        Args:
            exclusive: se True e já existe uma animação DESTE trigger
                       rodando, não toca de novo (útil p/ hover, flash).
        """
        defn = animation_registry.resolve_trigger(trigger)
        if defn is None:
            print(f"[ANIM_MGR] trigger não mapeado: {trigger!r}")
            return None
        if exclusive and self._by_key.get(trigger):
            return self._by_key[trigger][0]
        return self._play(
            defn, key=trigger,
            anchor_target=anchor_target,
            anchor_attacker=anchor_attacker,
            anchor_projectile=anchor_projectile,
            world_pos=world_pos,
            screen_pos=screen_pos,
            loop_override=loop_override,
        )

    def play(self, key: str,
             anchor_target=None,
             anchor_attacker=None,
             anchor_projectile=None,
             world_pos=None,
             screen_pos=None,
             loop_override=None,
             exclusive: bool = False) -> Optional[Animator]:
        """Toca uma animação pelo caminho direto (ex: 'items/potion_spray')."""
        defn = animation_registry.get(key)
        if defn is None:
            print(f"[ANIM_MGR] animação não encontrada: {key!r}")
            return None
        if exclusive and self._by_key.get(key):
            return self._by_key[key][0]
        return self._play(
            defn, key=key,
            anchor_target=anchor_target,
            anchor_attacker=anchor_attacker,
            anchor_projectile=anchor_projectile,
            world_pos=world_pos,
            screen_pos=screen_pos,
            loop_override=loop_override,
        )

    # ------- conveniências -------
    def play_at_screen(self, key: str, x: float, y: float,
                       loop_override=None, exclusive=False):
        """Atalho: play() com screen_pos fixo."""
        return self.play(
            key, screen_pos=(x, y),
            loop_override=loop_override, exclusive=exclusive,
        )

    def play_at_world(self, key: str, x: float, y: float,
                      loop_override=None, exclusive=False):
        """Atalho: play() com world_pos fixo (ignora anchor)."""
        return self.play(
            key, world_pos=(x, y),
            loop_override=loop_override, exclusive=exclusive,
        )

    def play_between(self, key: str, attacker, target,
                     loop_override=None, exclusive=False):
        """Atalho para animações ancoradas em dois atores (attacker → target)."""
        return self.play(
            key, anchor_attacker=attacker, anchor_target=target,
            loop_override=loop_override, exclusive=exclusive,
        )

    def play_screen(self, key: str, loop_override=None, exclusive=False):
        """Toca uma animação `space: screen` ocupando a tela inteira."""
        return self.play(
            key, loop_override=loop_override, exclusive=exclusive,
        )

    # =================================================================
    # INTERNO
    # =================================================================
    def _play(self, defn, key, anchor_target=None, anchor_attacker=None,
              anchor_projectile=None, world_pos=None, screen_pos=None,
              loop_override=None) -> Animator:
        anim = Animator(
            defn,
            anchor_target=anchor_target,
            anchor_attacker=anchor_attacker,
            anchor_projectile=anchor_projectile,
            world_pos=world_pos,
            screen_pos=screen_pos,
            loop_override=loop_override,
        )
        self.active.append(anim)
        self._by_key.setdefault(key, []).append(anim)
        return anim

    def play_definition(self, defn,
                        anchor_target=None,
                        anchor_attacker=None,
                        anchor_projectile=None,
                        world_pos=None,
                        screen_pos=None,
                        loop_override=None) -> Animator:
        """Compat: insere um AnimDefinition direto (sem key)."""
        return self._play(
            defn, key=defn.name,
            anchor_target=anchor_target,
            anchor_attacker=anchor_attacker,
            anchor_projectile=anchor_projectile,
            world_pos=world_pos,
            screen_pos=screen_pos,
            loop_override=loop_override,
        )

    # =================================================================
    # STOP / QUERY
    # =================================================================
    def stop(self, key: str):
        """Para todas as animações ativas do trigger/caminho `key`."""
        for anim in self._by_key.get(key, []):
            anim.stop()
        self._by_key.pop(key, None)
        self.active = [a for a in self.active if not a.is_finished()]

    def stop_by_trigger(self, trigger: str):
        """Alias retrocompatível."""
        self.stop(trigger)

    def stop_all(self):
        """Para TODAS as animações (chamar ao trocar de cena)."""
        for anim in self.active:
            anim.stop()
        self.active.clear()
        self._by_key.clear()

    def is_active(self, key: str) -> bool:
        return bool(self._by_key.get(key))

    def count_active(self) -> int:
        return len(self.active)

    def active_keys(self) -> list:
        return [k for k, v in self._by_key.items() if v]

    # =================================================================
    # UPDATE
    # =================================================================
    def update(self, dt: float):
        for anim in self.active:
            anim.update(dt)

        # Limpa finalizados
        self.active = [a for a in self.active if not a.is_finished()]
        for k in list(self._by_key.keys()):
            self._by_key[k] = [a for a in self._by_key[k]
                               if not a.is_finished()]
            if not self._by_key[k]:
                del self._by_key[k]

    # =================================================================
    # RENDER
    # =================================================================
    def render(self, screen, camera=None, screen_manager=None,
               space: Optional[str] = None,
               hidden_actors: Optional[set] = None):
        """Renderiza as animações.

        Args:
            space: "world", "screen" ou None (ambos, world primeiro).
            hidden_actors: set de ids de atores a esconder.
        """
        if space == "world":
            to_draw = [a for a in self.active if a.defn.space == "world"]
        elif space == "screen":
            to_draw = [a for a in self.active if a.defn.space == "screen"]
        else:
            world = [a for a in self.active if a.defn.space == "world"]
            scr = [a for a in self.active if a.defn.space == "screen"]
            to_draw = world + scr

        for anim in to_draw:
            anim.render(screen, camera, screen_manager,
                        hidden_actors=hidden_actors)


# =====================================================================
# SINGLETON
# =====================================================================
animation_manager = AnimationManager()


# =====================================================================
# HELPERS DE INTEGRAÇÃO COM CENAS
# =====================================================================
def attach_to_scene(scene):
    """Registra a cena como 'dona' das animações.

    Quando a cena for trocada, `detach_from_scene` limpa tudo.
    Chame no __init__ ou enter() da cena.
    """
    scene._anim_manager_owner = True


def detach_from_scene(scene=None):
    """Limpa TODAS as animações. Chame ao trocar de cena.

    Se `scene` for passado e ela não for a dona, não faz nada
    (evita que uma cena interrompa as animações de outra).
    """
    if scene is not None and not getattr(scene, '_anim_manager_owner', False):
        return
    animation_manager.stop_all()