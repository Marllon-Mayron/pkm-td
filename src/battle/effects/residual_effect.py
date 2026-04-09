from enum import Enum
from typing import Optional, Callable


class ResidualEffectType(Enum):
    """Tipos de efeitos residuais (por turno)"""
    LEECH_SEED = "leech_seed"
    WRAP = "wrap"
    BIND = "bind"
    FIRE_SPIN = "fire_spin"
    WHIRLPOOL = "whirlpool"
    CLAMP = "clamp"
    SAND_TOMB = "sand_tomb"
    INFESTATION = "infestation"
    MAGMA_STORM = "magma_storm"
    SALT_CURE = "salt_cure"


class ResidualEffect:
    """
    Efeito residual que persiste por múltiplos turnos.
    Ex: Leech Seed, Wrap, Bind, etc.
    """

    def __init__(
            self,
            effect_type: ResidualEffectType,
            source,  # Pokémon que aplicou o efeito
            target,  # Pokémon alvo
            duration: int = 5,  # Duração em turnos
            tick_interval: float = 2.0,  # Intervalo em segundos entre ticks
            on_tick_callback: Optional[Callable] = None,
            on_remove_callback: Optional[Callable] = None,
    ):
        self.effect_type = effect_type
        self.source = source
        self.target = target
        self.duration = duration  # Turnos restantes
        self.max_duration = duration
        self.tick_interval = tick_interval
        self.timer = 0.0
        self.is_active = True

        self.on_tick_callback = on_tick_callback
        self.on_remove_callback = on_remove_callback

        # Para Leech Seed: guarda quem plantou
        if effect_type == ResidualEffectType.LEECH_SEED:
            self.seed_source = source

    def update(self, dt: float) -> bool:
        """
        Atualiza o efeito residual.
        Retorna True se ainda está ativo, False se terminou.
        """
        if not self.is_active:
            return False

        self.timer += dt

        if self.timer >= self.tick_interval:
            self.timer = 0
            self.duration -= 1

            # Executa o tick
            if self.on_tick_callback:
                self.on_tick_callback(self)

            # Se acabou a duração, remove
            if self.duration <= 0:
                self.remove()
                return False

        return True

    def remove(self):
        """Remove o efeito residual"""
        if not self.is_active:
            return

        self.is_active = False
        if self.on_remove_callback:
            self.on_remove_callback(self)

    def get_remaining_turns(self) -> int:
        """Retorna turnos restantes"""
        return max(0, self.duration)

    def get_progress(self) -> float:
        """Retorna progresso (0 a 1)"""
        if self.max_duration == 0:
            return 1.0
        return 1.0 - (self.duration / self.max_duration)


class ResidualEffectManager:
    """Gerencia efeitos residuais em batalha"""

    def __init__(self, battle_system):
        self.battle_system = battle_system
        self.effects: list = []  # Efeitos ativos

    def add_effect(self, effect: ResidualEffect):
        """Adiciona um efeito residual"""
        # Verifica se já existe um efeito do mesmo tipo no alvo
        existing = self.get_effect_on_target(effect.target, effect.effect_type)
        if existing:
            # Substitui o efeito anterior (como nos jogos Pokémon)
            existing.remove()
            self.effects.remove(existing)

        self.effects.append(effect)
        print(f"[RESIDUAL] {effect.effect_type.value} aplicado em {effect.target.name} por {effect.source.name}")

    def remove_effect_on_target(self, target, effect_type: ResidualEffectType = None):
        """Remove efeitos residuais de um alvo"""
        to_remove = []
        for effect in self.effects:
            if effect.target == target:
                if effect_type is None or effect.effect_type == effect_type:
                    to_remove.append(effect)

        for effect in to_remove:
            effect.remove()
            self.effects.remove(effect)

    def get_effect_on_target(self, target, effect_type: ResidualEffectType) -> Optional[ResidualEffect]:
        """Retorna um efeito residual específico no alvo"""
        for effect in self.effects:
            if effect.target == target and effect.effect_type == effect_type:
                return effect
        return None

    def has_effect_on_target(self, target, effect_type: ResidualEffectType) -> bool:
        """Verifica se o alvo tem um efeito residual específico"""
        return self.get_effect_on_target(target, effect_type) is not None

    def update(self, dt: float):
        """Atualiza todos os efeitos residuais"""
        for effect in self.effects[:]:
            still_active = effect.update(dt)
            if not still_active:
                self.effects.remove(effect)

    def clear_all(self):
        """Remove todos os efeitos"""
        for effect in self.effects:
            effect.remove()
        self.effects.clear()