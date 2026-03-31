# src/battle/effects/status_effect.py
from enum import Enum
from typing import Optional, Callable
import random


class StatusType(Enum):
    """Tipos de status"""
    NONE = "none"
    POISON = "poison"
    BURN = "burn"
    PARALYSIS = "paralysis"
    SLEEP = "sleep"
    FREEZE = "freeze"
    CONFUSION = "confusion"


class StatusEffect:
    """
    Representa um efeito de status (veneno, queimadura, paralisia, etc)
    """

    def __init__(self, status_type: StatusType, duration: Optional[float] = None):
        """
        Args:
            status_type: Tipo de status
            duration: Duração em segundos (None = permanente até cura)
        """
        self.type = status_type
        self.duration = duration
        self.time_left = duration if duration else 0

        # Para paralisia - controle de stun
        self._stun_timer = 0.0  # Tempo restante de stun
        self._last_stun_check = 0.0  # Último tempo de verificação

        # Callbacks
        self.on_apply_callback = None
        self.on_tick_callback = None
        self.on_remove_callback = None

        self._setup_effects()

    def _setup_effects(self):
        """Configura os efeitos específicos de cada status"""
        if self.type == StatusType.POISON:
            self.name = "Veneno"
            self.display_name = "PSN"
            self.color = (160, 64, 160)
            self.icon = "☠️"
            self.on_tick_callback = self._poison_tick

        elif self.type == StatusType.BURN:
            self.name = "Queimadura"
            self.display_name = "BRN"
            self.color = (240, 128, 48)
            self.icon = "🔥"
            self.on_tick_callback = self._burn_tick

        elif self.type == StatusType.PARALYSIS:
            self.name = "Paralisia"
            self.display_name = "PAR"
            self.color = (248, 208, 48)
            self.icon = "⚡"
            # Paralisia não tem tick de dano

        elif self.type == StatusType.SLEEP:
            self.name = "Sono"
            self.display_name = "SLP"
            self.color = (104, 144, 240)
            self.icon = "💤"

        elif self.type == StatusType.FREEZE:
            self.name = "Congelado"
            self.display_name = "FRZ"
            self.color = (152, 216, 216)
            self.icon = "❄️"

        elif self.type == StatusType.CONFUSION:
            self.name = "Confusão"
            self.display_name = "CON"
            self.color = (248, 88, 136)
            self.icon = "🌀"
            self.duration = 4.0
            self.time_left = 4.0
            self.on_tick_callback = self._confusion_tick

    def _poison_tick(self, pokemon, effect_manager):
        """Efeito do veneno a cada tick"""
        damage = max(1, pokemon.max_hp // 8)
        pokemon.current_hp = max(0, pokemon.current_hp - damage)
        # Texto temporário apenas para dano
        effect_manager.add_status_text(pokemon, f"-{damage} HP")
        return damage

    def _burn_tick(self, pokemon, effect_manager):
        """Efeito da queimadura a cada tick"""
        damage = max(1, pokemon.max_hp // 8)
        pokemon.current_hp = max(0, pokemon.current_hp - damage)
        effect_manager.add_status_text(pokemon, f"-{damage} HP")
        return damage

    def _confusion_tick(self, pokemon, effect_manager):
        """Efeito da confusão a cada tick"""
        if random.random() < 0.33:
            damage = max(1, pokemon.max_hp // 8)
            pokemon.current_hp = max(0, pokemon.current_hp - damage)
            effect_manager.add_status_text(pokemon, f"-{damage} HP")
            return damage
        return 0

    def can_attack(self) -> bool:
        """Verifica se o Pokémon pode atacar neste momento"""
        if self.type == StatusType.SLEEP:
            return False
        if self.type == StatusType.FREEZE:
            return False
        if self.type == StatusType.PARALYSIS:
            # Paralisia: retorna False se estiver atordoado (stun)
            return self._stun_timer <= 0
        return True

    def update_paralysis(self, dt: float) -> bool:
        """
        Atualiza o estado de paralisia
        Retorna True se o Pokémon está atordoado neste momento
        """
        if self.type != StatusType.PARALYSIS:
            return False

        # Atualiza o timer de stun
        if self._stun_timer > 0:
            self._stun_timer -= dt
            return True

        # Verifica se deve aplicar um novo stun
        self._last_stun_check += dt
        if self._last_stun_check >= 3.0:  # Verifica a cada 1 segundo
            self._last_stun_check = 0
            if random.random() < 0.33:  # 90% de chance
                self._stun_timer = 2.0  # Stun de 2 segundos
                print(f"[PARALYSIS] {self._stun_timer:.1f}s de stun aplicado!")  # Log para debug
                return True

        return False

    def is_stunned(self) -> bool:
        """Verifica se o Pokémon está atordoado neste momento"""
        if self.type == StatusType.PARALYSIS:
            return self._stun_timer > 0
        return False

    def get_stun_remaining(self) -> float:
        """Retorna o tempo restante de stun (0 se não estiver atordoado)"""
        if self.type == StatusType.PARALYSIS:
            return max(0, self._stun_timer)
        return 0

    def update(self, pokemon, effect_manager, dt: float):
        """
        Atualiza o efeito de status
        Retorna False se o efeito acabou
        """
        # Atualiza paralisia (gerencia stun)
        if self.type == StatusType.PARALYSIS:
            self.update_paralysis(dt)
            return True  # Paralisia não expira naturalmente

        # Para outros status com duração
        if self.duration:
            self.time_left -= dt
            if self.time_left <= 0:
                return False

        # Aplica tick de dano (para veneno, queimadura, confusão)
        if self.on_tick_callback:
            self.on_tick_callback(pokemon, effect_manager)

        return True

    def is_stunned(self) -> bool:
        """Verifica se o Pokémon está atordoado neste momento"""
        if self.type == StatusType.PARALYSIS:
            return self._stun_timer > 0
        return False

    def apply(self, pokemon, effect_manager):
        """Aplica o efeito de status"""
        if self.on_apply_callback:
            self.on_apply_callback(pokemon, effect_manager)

    def remove(self, pokemon, effect_manager):
        """Remove o efeito de status"""
        if self.on_remove_callback:
            self.on_remove_callback(pokemon, effect_manager)