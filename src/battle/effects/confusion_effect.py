# src/battle/effects/confusion_effect.py
import random
from typing import Optional


class ConfusionEffect:
    """
    Efeito de Confusão - status volátil.
    Dura 1-4 turnos de ATAQUE (contado apenas quando o Pokémon tenta atacar).
    Chance de 50% de se acertar (Gen I style).
    """

    def __init__(self, source=None):
        self.source = source  # Pokémon que causou a confusão
        self.remaining_attacks = random.randint(1, 4)  # 1-4 turnos de ATAQUE
        self.initial_attacks = self.remaining_attacks

        # Stats para o jogo
        self.name = "Confusão"
        self.display_name = "CON"
        self.color = (248, 88, 136)  # Rosa
        self.icon = "🌀"

        # Probabilidade de se acertar (50% para Gen I)
        self.self_hit_chance = 0.5

        # Callback quando a confusão acaba
        self.on_end_callback = None

        # Flag para saber se o turno já foi contado
        self._attack_consumed = False

    def before_attack(self, attacker, target, battle_system, effect_manager):
        """
        Verificado ANTES de atacar.
        DECREMENTA o contador apenas quando o Pokémon TENTA atacar.

        Retorna:
            - None: ataque normal
            - "self": ataca a si mesmo
        """
        # Se a confusão acabou, não interfere
        if self.remaining_attacks <= 0:
            return None

        # CONTA este turno de ataque (decrementa)
        self.remaining_attacks -= 1

        # Mostra quantos turnos restam (para debug)
        print(f"[CONFUSION] {attacker.name} ainda confuso por {self.remaining_attacks} ataques")

        # Se acabou após decrementar, não aplica o self-hit
        if self.remaining_attacks <= 0:
            effect_manager.add_status_text(attacker, f"{attacker.name} se recuperou da confusão!", duration=1.5)
            print(f"[CONFUSION] {attacker.name} se recuperou da confusão!")
            return None

        # Chance de se acertar
        if random.random() < self.self_hit_chance:
            print(f"[CONFUSION] {attacker.name} está confuso e se machucou! (restam {self.remaining_attacks} ataques)")
            effect_manager.add_status_text(attacker, f"{attacker.name} se machucou na confusão!", duration=1.5)
            return "self"

        return None

    def calculate_self_damage(self, pokemon) -> int:
        """
        Calcula o dano que o Pokémon causa a si mesmo.
        Power 40, typeless, baseado no Attack físico.
        """
        from src.battle.effects.stat_modifier import StatType

        # Dano base: Power 40
        base_power = 40
        level = pokemon.level

        # Usa Attack físico, independente do que tentaria usar
        attack = pokemon.attack
        defense = pokemon.defense

        # Aplica modificadores de stage (se tiver effect_manager)
        if hasattr(pokemon, 'effect_manager') and pokemon.effect_manager:
            atk_mult = pokemon.effect_manager.get_stat_multiplier(pokemon, StatType.ATTACK)
            def_mult = pokemon.effect_manager.get_stat_multiplier(pokemon, StatType.DEFENSE)
            attack = int(attack * atk_mult)
            defense = int(defense * def_mult)

        # Fórmula de dano padrão Pokémon
        # damage = ((2 * level / 5 + 2) * power * attack / defense) / 50 + 2
        damage = ((2 * level / 5 + 2) * base_power * attack / defense) / 50 + 2
        damage = max(1, int(damage))

        # Variação aleatória de 85-100%
        damage = int(damage * random.uniform(0.85, 1.0))

        return damage

    def apply(self, pokemon, effect_manager):
        """Aplica o efeito de confusão"""
        effect_manager.add_status_text(pokemon, f"{pokemon.name} ficou confuso!", duration=1.5)
        print(f"[CONFUSION] {pokemon.name} ficou confuso por {self.remaining_attacks} ataques!")

        # Força atualização da animação
        if hasattr(pokemon, 'update_status_animation'):
            pokemon.update_status_animation()

    def remove(self, pokemon, effect_manager):
        """Remove o efeito de confusão"""
        if self.on_end_callback:
            self.on_end_callback(pokemon)

        effect_manager.add_status_text(pokemon, f"{pokemon.name} se recuperou da confusão!", duration=1.5)
        print(f"[CONFUSION] Confusão de {pokemon.name} foi removida!")

        # Força atualização da animação
        if hasattr(pokemon, 'update_status_animation'):
            pokemon.update_status_animation()

    def is_active(self) -> bool:
        """Verifica se a confusão ainda está ativa"""
        return self.remaining_attacks > 0

    def get_remaining_attacks(self) -> int:
        """Retorna quantos ataques restam de confusão"""
        return max(0, self.remaining_attacks)

    def get_progress(self) -> float:
        """Retorna progresso da confusão (0 a 1)"""
        if self.initial_attacks == 0:
            return 1.0
        return 1.0 - (self.remaining_attacks / self.initial_attacks)