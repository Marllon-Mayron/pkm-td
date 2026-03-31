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
    CONFUSION = "confusion"  # Confusão (opcional)


class StatusEffect:
    """
    Representa um efeito de status (veneno, queimadura, etc)
    """

    def __init__(self, status_type: StatusType, duration: Optional[int] = None):
        """
        Args:
            status_type: Tipo de status
            duration: Duração em turnos (None = permanente até cura)
        """
        self.type = status_type
        self.duration = duration
        self.current_duration = duration if duration else 0

        # Callbacks
        self.on_apply_callback = None
        self.on_tick_callback = None
        self.on_remove_callback = None

        self._setup_effects()

    def _setup_effects(self):
        """Configura os efeitos específicos de cada status"""
        if self.type == StatusType.POISON:
            self.name = "Veneno"
            self.color = (160, 64, 160)  # Roxo
            self.icon = "☠️"
            self.on_tick_callback = self._poison_tick

        elif self.type == StatusType.BURN:
            self.name = "Queimadura"
            self.color = (240, 128, 48)  # Laranja
            self.icon = "🔥"
            self.on_tick_callback = self._burn_tick
            self.on_apply_callback = self._burn_apply

        elif self.type == StatusType.PARALYSIS:
            self.name = "Paralisia"
            self.color = (248, 208, 48)  # Amarelo
            self.icon = "⚡"
            self.on_apply_callback = self._paralysis_apply

        elif self.type == StatusType.SLEEP:
            self.name = "Sono"
            self.color = (104, 144, 240)  # Azul
            self.icon = "💤"
            self.on_apply_callback = self._sleep_apply

        elif self.type == StatusType.FREEZE:
            self.name = "Congelado"
            self.color = (152, 216, 216)  # Ciano
            self.icon = "❄️"
            self.on_apply_callback = self._freeze_apply

        elif self.type == StatusType.CONFUSION:
            self.name = "Confusão"
            self.color = (248, 88, 136)  # Rosa
            self.icon = "🌀"
            self.duration = 4  # Duração padrão de confusão
            self.current_duration = 4
            self.on_tick_callback = self._confusion_tick

    def _poison_tick(self, pokemon, effect_manager):
        """Efeito do veneno a cada tick"""
        damage = max(1, pokemon.max_hp // 8)  # 1/8 do HP máximo
        pokemon.current_hp = max(0, pokemon.current_hp - damage)
        effect_manager.add_status_text(pokemon, f"-{damage} HP (Veneno)")
        return damage

    def _burn_tick(self, pokemon, effect_manager):
        """Efeito da queimadura a cada tick"""
        damage = max(1, pokemon.max_hp // 8)
        pokemon.current_hp = max(0, pokemon.current_hp - damage)
        effect_manager.add_status_text(pokemon, f"-{damage} HP (Queimadura)")
        return damage

    def _burn_apply(self, pokemon, effect_manager):
        """Aplica efeito de queimadura (reduz ataque físico)"""
        # A queimadura reduz o ataque físico em 50%
        if not hasattr(pokemon, '_burn_atk_modifier'):
            pokemon._burn_atk_modifier = 0.5

    def _paralysis_apply(self, pokemon, effect_manager):
        """Aplica efeito de paralisia (reduz velocidade e chance de não atacar)"""
        # Reduz velocidade em 50%
        if not hasattr(pokemon, '_paralysis_speed_modifier'):
            pokemon._paralysis_speed_modifier = 0.5

    def _sleep_apply(self, pokemon, effect_manager):
        """Aplica efeito de sono (não pode atacar)"""
        self.duration = random.randint(1, 5)  # Dorme por 1-5 turnos
        self.current_duration = self.duration
        effect_manager.add_status_text(pokemon, f"{pokemon.name} adormeceu!")

    def _freeze_apply(self, pokemon, effect_manager):
        """Aplica efeito de congelamento (não pode atacar)"""
        effect_manager.add_status_text(pokemon, f"{pokemon.name} foi congelado!")

    def _confusion_tick(self, pokemon, effect_manager):
        """Efeito da confusão a cada tick (chance de se machucar)"""
        if random.random() < 0.33:  # 33% de chance
            damage = max(1, pokemon.max_hp // 8)
            pokemon.current_hp = max(0, pokemon.current_hp - damage)
            effect_manager.add_status_text(pokemon, f"{pokemon.name} se machucou na confusão!")
            return damage
        return 0

    def can_attack(self) -> bool:
        """Verifica se o Pokémon pode atacar com esse status"""
        if self.type == StatusType.SLEEP:
            return False
        if self.type == StatusType.FREEZE:
            return False
        if self.type == StatusType.PARALYSIS:
            # 25% de chance de não conseguir atacar
            return random.random() > 0.25
        return True

    def update(self, pokemon, effect_manager):
        """Atualiza o efeito de status"""
        if self.on_tick_callback:
            self.on_tick_callback(pokemon, effect_manager)

        if self.duration:
            self.current_duration -= 1
            if self.current_duration <= 0:
                return False  # Efeito acabou

        return True  # Efeito continua

    def apply(self, pokemon, effect_manager):
        """Aplica o efeito de status"""
        if self.on_apply_callback:
            self.on_apply_callback(pokemon, effect_manager)

    def remove(self, pokemon, effect_manager):
        """Remove o efeito de status"""
        if self.on_remove_callback:
            self.on_remove_callback(pokemon, effect_manager)