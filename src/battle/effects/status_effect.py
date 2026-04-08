# src/battle/effects/status_effect.py
from enum import Enum
from typing import Optional, Callable, List
import random


class StatusType(Enum):
    """Tipos de status"""
    NONE = "none"
    POISON = "poison"
    TOXIC_POISON = "toxic_poison"
    BURN = "burn"
    PARALYSIS = "paralysis"
    SLEEP = "sleep"
    FREEZE = "freeze"
    CONFUSION = "confusion"


class TypeImmunity:
    """Gerencia imunidades de tipos contra status effects"""

    # Imunidades de tipos contra status (baseado nos jogos Pokémon)
    TYPE_IMMUNITIES = {
        # Veneno/Paralisia
        "poison": {
            StatusType.POISON,
            StatusType.TOXIC_POISON,
        },
        "steel": {
            StatusType.POISON,
            StatusType.TOXIC_POISON
        },
        "fire": {
            StatusType.BURN,  # Fogo é imune a queimadura
            StatusType.FREEZE  # Fogo é imune a congelamento
        },
        "ice": {
            StatusType.FREEZE  # Gelo é imune a congelamento
        },
    }

    # Imunidades específicas por espécie (para Pokémon lendários ou especiais)
    POKEMON_IMMUNITIES = {
        # "snorlax": {StatusType.SLEEP},  # Snorlax é difícil de dormir
    }

    @classmethod
    def is_immune_to_status(cls, pokemon, status_type: StatusType) -> bool:
        """
        Verifica se um Pokémon é imune a um tipo específico de status

        Args:
            pokemon: Pokémon a ser verificado
            status_type: Tipo de status a ser aplicado

        Returns:
            True se o Pokémon é imune, False caso contrário
        """
        # Verifica por tipo
        for pokemon_type in pokemon.types:
            pokemon_type_lower = pokemon_type.lower()

            if pokemon_type_lower in cls.TYPE_IMMUNITIES:
                if status_type in cls.TYPE_IMMUNITIES[pokemon_type_lower]:
                    print(f"[IMMUNITY] {pokemon.name} (tipo {pokemon_type}) é imune a {status_type.value}!")
                    return True

        # Verifica por espécie específica
        pokemon_name_lower = pokemon.name.lower()
        if pokemon_name_lower in cls.POKEMON_IMMUNITIES:
            if status_type in cls.POKEMON_IMMUNITIES[pokemon_name_lower]:
                print(f"[IMMUNITY] {pokemon.name} é imune a {status_type.value} por habilidade especial!")
                return True

        return False

    @classmethod
    def get_immunity_message(cls, pokemon, status_type: StatusType) -> str:
        """Retorna uma mensagem apropriada para a imunidade"""
        status_names = {
            StatusType.POISON: "envenenado",
            StatusType.TOXIC_POISON: "gravemente envenenado",
            StatusType.BURN: "queimado",
            StatusType.PARALYSIS: "paralisado",
            StatusType.SLEEP: "adormecido",
            StatusType.FREEZE: "congelado",
            StatusType.CONFUSION: "confuso"
        }

        status_name = status_names.get(status_type, status_type.value)

        # Mensagens específicas por tipo
        for pokemon_type in pokemon.types:
            pokemon_type_lower = pokemon_type.lower()

            if pokemon_type_lower == "poison" and status_type in [StatusType.POISON, StatusType.TOXIC_POISON]:
                return f"{pokemon.name} não pode ser envenenado por ser do tipo Veneno!"
            elif pokemon_type_lower == "steel" and status_type in [StatusType.POISON, StatusType.TOXIC_POISON]:
                return f"{pokemon.name} não pode ser envenenado por ser do tipo Aço!"
            elif pokemon_type_lower == "fire" and status_type == StatusType.BURN:
                return f"{pokemon.name} não pode ser queimado por ser do tipo Fogo!"
            elif pokemon_type_lower == "fire" and status_type == StatusType.FREEZE:
                return f"{pokemon.name} não pode ser congelado por ser do tipo Fogo!"
            elif pokemon_type_lower == "ice" and status_type == StatusType.FREEZE:
                return f"{pokemon.name} não pode ser congelado por ser do tipo Gelo!"
            elif pokemon_type_lower == "electric" and status_type == StatusType.PARALYSIS:
                return f"{pokemon.name} não pode ser paralisado por ser do tipo Elétrico!"
            elif pokemon_type_lower == "ground" and status_type == StatusType.PARALYSIS:
                return f"{pokemon.name} não pode ser paralisado por ser do tipo Terra!"
            elif pokemon_type_lower == "ghost" and status_type == StatusType.PARALYSIS:
                return f"{pokemon.name} não pode ser paralisado por ser do tipo Fantasma!"

        return f"{pokemon.name} é imune a {status_name}!"


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

        # Para congelamento
        self._freeze_timer = 0.0
        self._freeze_check_timer = 0.0
        self._freeze_chance = 0.20

        # Para dano por tick (veneno, queimadura)
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
            self.on_apply_callback = self._burn_apply
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
            self.on_apply_callback = self._freeze_apply

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
        Efeito do veneno a cada tick - dano de 1/8 do HP máximo
        """
        damage = max(1, pokemon.max_hp // 8)
        pokemon.current_hp = max(0, pokemon.current_hp - damage)
        return damage

    def _toxic_poison_tick(self, pokemon, effect_manager):
        """
        Efeito do veneno tóxico - dano aumenta a cada tick
        """
        self._toxic_tick_count += 1
        damage = max(1, (pokemon.max_hp * self._toxic_tick_count) // 16)
        pokemon.current_hp = max(0, pokemon.current_hp - damage)
        effect_manager.add_status_text(pokemon, f"-{damage} HP (Tóxico!)")
        print(f"[TOXIC] {pokemon.name} perdeu {damage} HP por veneno tóxico (tick {self._toxic_tick_count})!")
        return damage

    def _burn_tick(self, pokemon, effect_manager):
        """
        Efeito da queimadura a cada tick - dano de 1/16 do HP máximo
        """
        damage = max(1, pokemon.max_hp // 16)
        pokemon.current_hp = max(0, pokemon.current_hp - damage)
        return damage

    def _burn_apply(self, pokemon, effect_manager):
        """
        Aplica o efeito de queimadura - reduz o ataque físico pela metade
        """
        print(f"[BURN] {pokemon.name} foi queimado! Ataque físico reduzido pela metade!")

    def _confusion_tick(self, pokemon, effect_manager):
        """Efeito da confusão a cada tick"""
        if random.random() < 0.33:
            damage = max(1, pokemon.max_hp // 8)
            pokemon.current_hp = max(0, pokemon.current_hp - damage)
            effect_manager.add_status_text(pokemon, f"-{damage} HP (Confusão)")
            return damage
        return 0

    def get_attack_multiplier(self) -> float:
        """
        Retorna o multiplicador para ataques físicos
        Queimadura reduz o ataque pela metade (0.5x)
        """
        if self.type == StatusType.BURN:
            return 0.5
        return 1.0

    def can_attack(self) -> bool:
        """Verifica se o Pokémon pode atacar neste momento"""
        if self.type == StatusType.SLEEP:
            return False
        if self.type == StatusType.FREEZE:
            return False
        if self.type == StatusType.PARALYSIS:
            return self._stun_timer <= 0
        return True

    def update_paralysis(self, dt: float, pokemon=None) -> bool:
        """
        Atualiza o estado de paralisia
        Retorna True se o Pokémon está atordoado
        """
        if self.type != StatusType.PARALYSIS:
            return False

        old_stun_state = self._stun_timer > 0

        if self._stun_timer > 0:
            self._stun_timer -= dt
            new_stun_state = self._stun_timer > 0

            # Se mudou de atordoado para não atordoado, notifica
            if old_stun_state and not new_stun_state and pokemon:
                print(f"[PARALYSIS] {pokemon.name} não está mais atordoado!")
                self._notify_stun_change(pokemon, False)
            return self._stun_timer > 0

        self._last_stun_check += dt
        if self._last_stun_check >= 3.0:
            self._last_stun_check = 0
            if random.random() < 0.33:
                self._stun_timer = 2.0
                print(f"[PARALYSIS] {getattr(pokemon, 'name', '?')} está atordoado por 2 segundos!")
                # Notifica que entrou em stun
                if pokemon:
                    self._notify_stun_change(pokemon, True)
                return True

        return False

    def _notify_stun_change(self, pokemon, is_stunned: bool):
        """Notifica o Pokémon sobre mudança no estado de stun"""
        print(f"[STUN_NOTIFY] {pokemon.name} is_stunned={is_stunned}")
        if hasattr(pokemon, 'on_stun_state_changed'):
            pokemon.on_stun_state_changed(is_stunned)

    def get_stun_remaining(self) -> float:
        if self.type == StatusType.PARALYSIS:
            return max(0, self._stun_timer)
        return 0

    def update_sleep(self, dt: float) -> bool:
        if self.type != StatusType.SLEEP:
            return False

        if self._sleep_timer <= 0:
            self._sleep_check_timer += dt
            if self._sleep_check_timer >= 1.0:
                self._sleep_check_timer = 0
                if random.random() < 0.25:
                    self._sleep_timer = 2.0
                    return True
                else:
                    print(f"[SLEEP] {self._pokemon_name} acordou!")
                    return False

        old_timer = self._sleep_timer
        self._sleep_timer -= dt

        if self._sleep_timer <= 0 and old_timer > 0:
            print(f"[SLEEP] {self._pokemon_name}: timer zerou!")

        return self._sleep_timer > 0

    def is_asleep(self) -> bool:
        if self.type == StatusType.SLEEP:
            return self._sleep_timer > 0
        return False

    def get_sleep_remaining(self) -> float:
        if self.type == StatusType.SLEEP:
            return max(0, self._sleep_timer)
        return 0

    def update(self, pokemon, effect_manager, dt: float):
        """
        Atualiza o efeito de status
        Retorna False se o efeito acabou
        """
        self._pokemon_name = pokemon.name

        # Atualiza paralisia (passa o pokemon)
        if self.type == StatusType.PARALYSIS:
            self.update_paralysis(dt, pokemon)
            return True

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

        # Tick de dano para veneno e queimadura (a cada 2 segundos)
        if self.on_tick_callback:
            self._damage_timer += dt
            if self._damage_timer >= self._tick_interval:
                self._damage_timer = 0
                self.on_tick_callback(pokemon, effect_manager)

        return True

    def is_stunned(self) -> bool:
        if self.type == StatusType.PARALYSIS:
            return self._stun_timer > 0
        return False

    def _sleep_apply(self, pokemon, effect_manager):
        """Aplica o sono"""
        self._pokemon_name = pokemon.name
        self._sleep_timer = 6.0
        self._sleep_check_timer = 0.0

    def update_freeze(self, dt: float) -> bool:
        """
        Atualiza o estado de congelamento
        Retorna True se o Pokémon ainda está congelado
        """
        if self.type != StatusType.FREEZE:
            return False

        # O congelamento persiste até ser descongelado por:
        # - Ataque de fogo que atinge o Pokémon
        # - Chance aleatória a cada turno
        # - Scald (movimento de água quente)

        self._freeze_check_timer += dt

        # Verifica chance de descongelar a cada ~3 segundos
        if self._freeze_check_timer >= 3.0:
            self._freeze_check_timer = 0
            if random.random() < self._freeze_chance:
                print(f"[FREEZE] {self._pokemon_name} descongelou!")
                return False

        return True

    def _freeze_apply(self, pokemon, effect_manager):
        """Aplica o efeito de congelamento"""
        self._pokemon_name = pokemon.name
        self._freeze_timer = 0.0
        self._freeze_check_timer = 0.0
        self._freeze_chance = 0.20  # 20% de chance de descongelar por turno
        print(f"[FREEZE] {pokemon.name} foi congelado! Não pode se mover!")

    def is_frozen(self) -> bool:
        """Verifica se o Pokémon está congelado"""
        if self.type == StatusType.FREEZE:
            return True
        return False

    def thaw(self):
        """Descongela o Pokémon (usado por ataques de fogo)"""
        if self.type == StatusType.FREEZE:
            self._freeze_timer = 0
            print(f"[FREEZE] {self._pokemon_name} descongelou devido ao calor!")
            return True
        return False

    def apply(self, pokemon, effect_manager):
        """Aplica o efeito de status - com callback de animação"""
        if self.on_apply_callback:
            self.on_apply_callback(pokemon, effect_manager)

        # ===== FORÇA ATUALIZAÇÃO DA ANIMAÇÃO =====
        if hasattr(pokemon, 'update_status_animation'):
            pokemon.update_status_animation()

    def remove(self, pokemon, effect_manager):
        """Remove o efeito de status - com callback de animação"""
        if self.on_remove_callback:
            self.on_remove_callback(pokemon, effect_manager)

        # ===== FORÇA ATUALIZAÇÃO DA ANIMAÇÃO DE VOLTA AO NORMAL =====
        if hasattr(pokemon, 'update_status_animation'):
            pokemon.update_status_animation()