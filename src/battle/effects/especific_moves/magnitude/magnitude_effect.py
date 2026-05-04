# src/battle/effects/specific/magnitude_effect.py
"""
Magnitude - Geração 2
Ataque de Ground que causa dano em área com poder aleatório.
O poder é determinado por uma magnitude de 4 a 10.
"""
import random
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from src.entities.pokemon import Pokemon
    from src.battle.battle_system import BattleSystem
    from src.battle.effects.effect_manager import EffectManager


class MagnitudeEffect:
    """
    Efeito do movimento Magnitude.

    Características:
    - Ataque em área (todos inimigos no range)
    - Poder baseado na magnitude sorteada
    - Mostra a magnitude sorteada para feedback visual
    """

    # Tabela de magnitudes: (power, chance)
    MAGNITUDE_TABLE = [
        (4, 10, 5),  # magnitude, power, chance%
        (5, 30, 10),
        (6, 50, 20),
        (7, 70, 30),
        (8, 90, 20),
        (9, 110, 10),
        (10, 150, 5),
    ]

    def __init__(self, move_name: str = "magnitude"):
        self.move_name = move_name

    @classmethod
    def get_random_magnitude(cls) -> tuple:
        """
        Sorteia uma magnitude baseada nas chances.
        Retorna (magnitude, power)
        """
        # Cria lista de opções com pesos
        choices = []
        for mag, power, chance in cls.MAGNITUDE_TABLE:
            choices.extend([(mag, power)] * chance)

        magnitude, power = random.choice(choices)
        return magnitude, power

    @classmethod
    def get_magnitude_info(cls, magnitude: int) -> tuple:
        """Retorna (power, chance) para uma magnitude específica"""
        for mag, power, chance in cls.MAGNITUDE_TABLE:
            if mag == magnitude:
                return power, chance
        return 70, 30  # fallback para magnitude 7

    def execute(self, attacker: 'Pokemon', target: 'Pokemon',
                battle_system: 'BattleSystem', effect_manager: 'EffectManager') -> bool:
        """
        Executa o efeito Magnitude em área.
        """
        from src.battle.damage_calculator import DamageCalculator
        from src.managers.sounds.move_sound_manager import move_sound_manager

        # Previne recursão
        if hasattr(attacker, '_processing_magnitude') and attacker._processing_magnitude:
            return False

        # Sorteia a magnitude
        magnitude, power = self.get_random_magnitude()

        # Mostra mensagem da magnitude
        magnitude_messages = {
            4: "Magnitude 4! Fracamente...",
            5: "Magnitude 5!",
            6: "Magnitude 6!",
            7: "Magnitude 7! Forte!",
            8: "Magnitude 8! Muito forte!",
            9: "Magnitude 9! Devastador!",
            10: "Magnitude 10!!! MÁXIMO!!!"
        }

        message = magnitude_messages.get(magnitude, f"Magnitude {magnitude}!")
        effect_manager.add_status_text(attacker, message, duration=1.2)

        print(f"[MAGNITUDE] {attacker.name} causou Magnitude {magnitude} (Power: {power})!")

        # Obtém o move atual para os parâmetros
        current_move = attacker.get_current_move()
        if not current_move:
            print(f"[MAGNITUDE] {attacker.name} não tem move selecionado!")
            return False

        # Guarda o poder original e substitui temporariamente
        original_power = current_move.power
        current_move.power = power

        # Obtém todos os alvos em range
        targets_in_range = self._get_targets_in_range(attacker, battle_system)

        if not targets_in_range:
            effect_manager.add_status_text(attacker, "Mas não há inimigos no alcance!", duration=1.0)
            # Restaura poder
            current_move.power = original_power
            return False

        # Gasta PP uma vez
        if current_move.current_pp > 0:
            current_move.current_pp -= 1
        else:
            current_move.power = original_power
            return False

        # Toca som do ataque
        move_sound_manager.play_attack_sound(current_move.sound_name)

        # Animação do atacante
        attacker._processing_magnitude = True
        try:
            # Efeito de tremor (se tiver animação específica)
            if hasattr(attacker, 'play_earthquake_animation'):
                attacker.play_earthquake_animation()
            elif hasattr(attacker, 'play_hurt_animation'):
                attacker.play_hurt_animation()

            hit_count = 0
            for target_entity in targets_in_range:
                if not target_entity.is_alive() or target_entity.is_defeated:
                    continue

                # Verifica imunidade de Ground (Flying, Levitate)
                if self._is_immune_to_ground(target_entity):
                    effect_manager.add_status_text(target_entity, f"{target_entity.name} é imune!", duration=0.8)
                    print(f"[MAGNITUDE] {target_entity.name} é imune a Ground!")
                    continue

                # Calcula dano com o poder temporário
                damage_result = DamageCalculator.calculate_damage(attacker, target_entity, current_move)

                if damage_result["hit"]:
                    damage = damage_result["damage"]
                    old_hp = target_entity.current_hp
                    target_entity.take_damage(damage, attacker=attacker)
                    actual_damage = old_hp - target_entity.current_hp

                    # Mostra dano
                    effect_manager.add_status_text(target_entity, f"-{actual_damage} HP", duration=0.6)

                    # Mensagens de eficácia
                    if damage_result["effectiveness"] > 1.0:
                        effect_manager.add_status_text(target_entity, "Super efetivo!", duration=0.6)
                    elif 0 < damage_result["effectiveness"] < 1.0:
                        effect_manager.add_status_text(target_entity, "Não é muito efetivo...", duration=0.6)

                    # Toca som de impacto
                    move_sound_manager.play_hit_sound(current_move.sound_name)

                    # Animação de hurt
                    if hasattr(target_entity, 'play_hurt_animation'):
                        target_entity.play_hurt_animation()

                    hit_count += 1
                    print(
                        f"[MAGNITUDE] {attacker.name} causou {actual_damage} de dano em {target_entity.name} (Mag {magnitude})!")

            # Mensagem final de sucesso
            if hit_count > 0:
                effect_manager.add_status_text(attacker, f"A terra tremeu com magnitude {magnitude}!", duration=1.0)

        finally:
            # Restaura poder original
            current_move.power = original_power
            attacker._processing_magnitude = False

        # Cooldown
        attacker.attack_cooldown = max(0.3, 1.0 - (attacker.speed_stat / 500))
        attacker.combat_state = "idle"

        return hit_count > 0

    def _get_targets_in_range(self, attacker: 'Pokemon', battle_system: 'BattleSystem') -> list:
        """Retorna todos os inimigos no range do atacante"""
        all_targets = []

        if attacker.is_wild:
            # Atacante selvagem: procura aliados do player
            if hasattr(battle_system.game_scene, 'placement_manager'):
                all_targets = battle_system.game_scene.placement_manager.placed_pokemon.copy()
        else:
            # Atacante aliado: procura inimigos selvagens
            if hasattr(battle_system.game_scene, 'wave_manager'):
                all_targets = battle_system.game_scene.wave_manager.active_enemies.copy()

        if not all_targets:
            return []

        return attacker.get_enemies_in_range(all_targets)

    def _is_immune_to_ground(self, pokemon: 'Pokemon') -> bool:
        """
        Verifica se o Pokémon é imune a ataques do tipo Ground.
        Tipos Flying são imunes.
        Pokémon com habilidade Levitate são imunes.
        """
        # 1. Verifica tipo Flying
        if any(t.lower() == "flying" for t in pokemon.types):
            return True

        return False