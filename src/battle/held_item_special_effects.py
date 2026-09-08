# src/battle/held_item_special_effects.py

import random
from src.data.held_item_data import get_special_effect


class HeldItemSpecialEffects:
    """Gerencia os efeitos especiais dos itens seguráveis (King's Rock, etc)"""

    @staticmethod
    def get_flinch_chance(attacker) -> float:
        """
        Retorna a chance de flinch do King's Rock se o atacante estiver segurando-o.
        """
        if not attacker or not hasattr(attacker, 'held_item') or not attacker.held_item:
            return 0.0

        special_effect = get_special_effect(attacker.held_item)
        if not special_effect:
            return 0.0

        if special_effect.get("type") == "flinch_chance":
            return special_effect.get("chance", 0.10)

        return 0.0

    @staticmethod
    def should_apply_flinch(attacker, move_category: str) -> bool:
        """
        Verifica se o flinch do King's Rock deve ser aplicado.
        Só funciona em ataques que causam dano (physical ou special).
        """
        # Só funciona em ataques que causam dano
        if move_category == "status":
            return False

        chance = HeldItemSpecialEffects.get_flinch_chance(attacker)
        if chance <= 0:
            return False

        return random.random() < chance

    @staticmethod
    def apply_kings_rock_flinch(attacker, target, move_category: str) -> bool:
        """
        Aplica o efeito do King's Rock no alvo.
        Retorna True se o flinch foi aplicado com sucesso.
        """
        # Verifica se o atacante está segurando King's Rock
        if not attacker or not hasattr(attacker, 'held_item') or attacker.held_item != "kings_rock":
            return False

        # Verifica se o movimento causa dano
        if move_category == "status":
            return False

        # Verifica se o alvo está vivo
        if not target or target.is_defeated or not target.is_alive():
            return False

        # Aplica flinch com 10% de chance
        if random.random() < 0.10:
            # Reseta o cooldown do alvo (faz perder o turno)
            target.attack_cooldown = max(0.5, 1.0 - (target.speed_stat / 500))

            # Mensagem visual
            if hasattr(target, 'effect_manager') and target.effect_manager:
                target.effect_manager.add_status_text(
                    target,
                    f"King's Rock fez {target.name} hesitar!",
                    duration=1.5
                )

            print(f"[KING'S_ROCK] {attacker.name} causou flinch em {target.name} com King's Rock!")
            return True

        return False