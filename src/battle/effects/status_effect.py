# src/battle/effects/status_effect.py
from enum import Enum
from typing import Optional, Callable
import random


class StatusType(Enum):
    """Tipos de status"""
    NONE = "none"
    POISON = "poison"
    TOXIC_POISON = "toxic_poison"  # Veneno tóxico (dano aumenta com o tempo)
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

        # Para veneno tóxico - contador de ticks
        self._toxic_tick_count = 0
        self._last_tick_time = 0.0
        self._tick_interval = 2.0  # Tick a cada 2 segundos

        # Para paralisia - controle de stun
        self._stun_timer = 0.0
        self._last_stun_check = 0.0

        # Para sono - controle de duração
        self._sleep_timer = 0.0
        self._sleep_check_timer = 0.0

        # Para queimadura e veneno - controle de tick
        self._damage_timer = 0.0

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
            self._damage_timer = 0.0

        elif self.type == StatusType.TOXIC_POISON:
            self.name = "Veneno Tóxico"
            self.display_name = "TOX"
            self.color = (180, 80, 180)
            self.icon = "☠️☠️"
            self.on_tick_callback = self._toxic_poison_tick
            self._toxic_tick_count = 0
            self._damage_timer = 0.0

        elif self.type == StatusType.BURN:
            self.name = "Queimadura"
            self.display_name = "BRN"
            self.color = (240, 128, 48)
            self.icon = "🔥"
            self.on_tick_callback = self._burn_tick
            self._damage_timer = 0.0

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
            self.on_apply_callback = self._sleep_apply

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
        """
        Efeito do veneno a cada tick - dano fixo de 1/8 do HP máximo
        """
        damage = max(1, pokemon.max_hp // 8)
        pokemon.current_hp = max(0, pokemon.current_hp - damage)
        return damage

    def _toxic_poison_tick(self, pokemon, effect_manager):
        """
        Efeito do veneno tóxico - dano aumenta a cada tick
        Primeiro tick: 1/16 do HP
        Segundo tick: 2/16 (1/8)
        Terceiro tick: 3/16
        E assim por diante...
        """
        self._toxic_tick_count += 1
        # Dano = (tick_count / 16) do HP máximo
        damage = max(1, (pokemon.max_hp * self._toxic_tick_count) // 16)
        pokemon.current_hp = max(0, pokemon.current_hp - damage)
        return damage

    def _burn_tick(self, pokemon, effect_manager):
        """Efeito da queimadura a cada tick"""
        damage = max(1, pokemon.max_hp // 8)
        pokemon.current_hp = max(0, pokemon.current_hp - damage)
        effect_manager.add_status_text(pokemon, f"-{damage} HP (Queimadura)")
        return damage

    def _confusion_tick(self, pokemon, effect_manager):
        """Efeito da confusão a cada tick"""
        if random.random() < 0.33:
            damage = max(1, pokemon.max_hp // 8)
            pokemon.current_hp = max(0, pokemon.current_hp - damage)
            effect_manager.add_status_text(pokemon, f"-{damage} HP (Confusão)")
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
        if self._last_stun_check >= 3.0:  # Verifica a cada 3 segundos
            self._last_stun_check = 0
            if random.random() < 0.33:  # 33% de chance de stun
                self._stun_timer = 2.0  # Stun de 2 segundos
                print(f"[PARALYSIS] Stun aplicado por 2 segundos!")
                return True

        return False

    def get_stun_remaining(self) -> float:
        """Retorna o tempo restante de stun (0 se não estiver atordoado)"""
        if self.type == StatusType.PARALYSIS:
            return max(0, self._stun_timer)
        return 0

    def update_sleep(self, dt: float) -> bool:
        """
        Atualiza o estado de sono
        Retorna True se está dormindo, False se acordou
        """
        if self.type != StatusType.SLEEP:
            return False

        # Se o timer é zero ou negativo, pode tentar acordar
        if self._sleep_timer <= 0:
            self._sleep_check_timer += dt

            # Verifica a cada 1 segundo
            if self._sleep_check_timer >= 1.0:
                self._sleep_check_timer = 0
                if random.random() < 0.25:  # 25% de chance de continuar dormindo
                    self._sleep_timer = 2.0  # Dorme mais 2 segundos
                    return True
                else:
                    # Acordou
                    print(f"[SLEEP] {self._pokemon_name} acordou!")
                    return False

        # Ainda tem tempo de sono - decrementa
        old_timer = self._sleep_timer
        self._sleep_timer -= dt

        # Verifica se acabou de zerar
        if self._sleep_timer <= 0 and old_timer > 0:
            print(f"[SLEEP] {self._pokemon_name}: timer zerou! Pronto para acordar.")

        return self._sleep_timer > 0

    def is_asleep(self) -> bool:
        """Verifica se o Pokémon está dormindo"""
        if self.type == StatusType.SLEEP:
            return self._sleep_timer > 0
        return False

    def get_sleep_remaining(self) -> float:
        """Retorna o tempo restante de sono (0 se não está dormindo)"""
        if self.type == StatusType.SLEEP:
            return max(0, self._sleep_timer)
        return 0

    def update(self, pokemon, effect_manager, dt: float):
        """
        Atualiza o efeito de status
        Retorna False se o efeito acabou
        """
        self._pokemon_name = pokemon.name

        # Atualiza paralisia (gerencia stun)
        if self.type == StatusType.PARALYSIS:
            self.update_paralysis(dt)
            return True  # Paralisia não expira naturalmente

        # Atualiza sono
        if self.type == StatusType.SLEEP:
            is_still_asleep = self.update_sleep(dt)
            if not is_still_asleep:
                print(f"[SLEEP] {pokemon.name} acordou! Removendo status.")
                return False
            return True

        # Para outros status com duração
        if self.duration:
            self.time_left -= dt
            if self.time_left <= 0:
                return False

        # ===== TICK DE DANO PARA VENENO, QUEIMADURA, ETC =====
        # Aplica dano a cada 2 segundos
        if self.on_tick_callback:
            self._damage_timer += dt
            if self._damage_timer >= self._tick_interval:
                self._damage_timer = 0
                self.on_tick_callback(pokemon, effect_manager)

        return True

    def is_stunned(self) -> bool:
        """Verifica se o Pokémon está atordoado (paralisia)"""
        if self.type == StatusType.PARALYSIS:
            return self._stun_timer > 0
        return False

    def _sleep_apply(self, pokemon, effect_manager):
        """Aplica o sono - garante 2 segundos iniciais"""
        self._pokemon_name = pokemon.name
        self._sleep_timer = 6.0  # 6 segundos garantidos
        self._sleep_check_timer = 0.0

    def apply(self, pokemon, effect_manager):
        """Aplica o efeito de status"""
        if self.on_apply_callback:
            self.on_apply_callback(pokemon, effect_manager)

    def remove(self, pokemon, effect_manager):
        """Remove o efeito de status"""
        if self.on_remove_callback:
            self.on_remove_callback(pokemon, effect_manager)