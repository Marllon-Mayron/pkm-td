# src/battle/effects/specific_moves/triple_kick/triple_kick_state.py
"""
Triple Kick - Golpe da Geração 2
Acerta 3 chutes com poder crescente. Se um errar, o ataque para.
"""
import random
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from src.entities.pokemon import Pokemon
    from src.battle.battle_system import BattleSystem
    from src.battle.effects.effect_manager import EffectManager


class TripleKickState:
    """
    Gerencia o estado do ataque Triple Kick em andamento.

    Características:
    - 3 hits consecutivos
    - Poder: 1º hit=10, 2º=20, 3º=30
    - Cada hit tem 90% de acerto (modificável por accuracy/evasion)
    - Se errar, o ataque para completamente
    - Gasta 1 PP por ataque completo
    """

    def __init__(
            self,
            attacker: 'Pokemon',
            target: 'Pokemon',
            move,
            battle_system: 'BattleSystem',
            effect_manager: 'EffectManager'
    ):
        self.attacker = attacker
        self.target = target
        self.move = move
        self.battle_system = battle_system
        self.effect_manager = effect_manager

        # Parâmetros do Triple Kick
        self.total_hits = 3
        self.hits_remaining = 3
        self.current_hit = 1
        self.base_power = 10
        self.power_multiplier = [1, 2, 3]  # 1x, 2x, 3x
        self.accuracy = 90  # 90% de acerto por hit
        self.hit_interval = 0.15  # 0.15 segundos entre hits

        # Estado interno
        self.hit_timer = 0.0
        self.total_damage = 0
        self.was_interrupted = False
        self.hit_results = []

        # Flag para evitar recursão
        self._processing = False

    def update(self, dt: float) -> bool:
        """
        Atualiza o Triple Kick.
        Retorna True se ainda está ativo, False se terminou ou foi interrompido.
        """
        if self._processing:
            return True

        self._processing = True

        try:
            self.hit_timer += dt

            if self.hit_timer >= self.hit_interval and self.hits_remaining > 0 and not self.was_interrupted:
                self.hit_timer = 0
                self._execute_next_hit()

            return self.hits_remaining > 0 and not self.was_interrupted and self.target.is_alive()

        finally:
            self._processing = False

    def _execute_next_hit(self):
        """Executa o próximo hit do Triple Kick"""
        from src.battle.damage_calculator import DamageCalculator
        from src.managers.sounds.move_sound_manager import move_sound_manager

        # Verifica se o alvo ainda está vivo
        if not self.target.is_alive() or self.target.is_defeated:
            self.was_interrupted = True
            print(f"[TRIPLE_KICK] Ataque interrompido: {self.target.name} foi derrotado!")
            return

        # ===== CALCULA O PODER DO HIT ATUAL =====
        current_power = self.base_power * self.power_multiplier[self.current_hit - 1]

        # Guarda o poder original e substitui temporariamente
        original_power = self.move.power
        self.move.power = current_power

        try:
            # ===== TESTE DE ACERTO =====
            hit_chance = self.accuracy / 100

            # Aplica modificadores de accuracy/evasion
            from src.battle.effects.stat_modifier import StatType
            accuracy_mult = self.battle_system.effect_manager.get_stat_multiplier(
                self.attacker, StatType.ACCURACY
            )
            evasion_mult = self.battle_system.effect_manager.get_stat_multiplier(
                self.target, StatType.EVASION
            )

            final_hit_chance = hit_chance * accuracy_mult / evasion_mult
            final_hit_chance = max(0.01, min(1.0, final_hit_chance))

            will_hit = random.random() <= final_hit_chance

            if not will_hit:
                # Errou! O ataque para completamente
                self.was_interrupted = True

                # Mostra mensagem de erro
                hit_ordinal = self._get_ordinal_string(self.current_hit)
                self.effect_manager.add_status_text(
                    self.attacker,
                    f"O {hit_ordinal} chute errou!",
                    duration=1.0
                )

                # Toca som de erro
                move_sound_manager.play_attack_sound("miss")

                print(f"[TRIPLE_KICK] {self.attacker.name} errou o {self.current_hit}º hit! Ataque interrompido.")
                return

            # ===== CALCULA DANO =====
            damage_result = DamageCalculator.calculate_damage(self.attacker, self.target, self.move)

            if damage_result["hit"]:
                damage = damage_result["damage"]
                self.total_damage += damage

                # Aplica dano
                old_hp = self.target.current_hp
                self.target.take_damage(damage, attacker=self.attacker)
                actual_damage = old_hp - self.target.current_hp

                # Guarda resultado
                self.hit_results.append({
                    "hit_number": self.current_hit,
                    "power": current_power,
                    "damage": actual_damage,
                    "critical": damage_result.get("critical", False),
                    "effectiveness": damage_result.get("effectiveness", 1.0)
                })

                # Mostra mensagem do hit
                hit_ordinal = self._get_ordinal_string(self.current_hit)
                self.effect_manager.add_status_text(
                    self.target,
                    f"{hit_ordinal} chute! -{actual_damage} HP",
                    duration=0.8
                )

                # Se foi crítico
                if damage_result.get("critical", False):
                    self.effect_manager.add_status_text(self.attacker, "Acerto Crítico!", duration=0.5)

                # Mostra eficácia
                effectiveness = damage_result.get("effectiveness", 1.0)
                if effectiveness > 1.0:
                    self.effect_manager.add_status_text(self.attacker, "Super efetivo!", duration=0.5)
                elif 0 < effectiveness < 1.0:
                    self.effect_manager.add_status_text(self.attacker, "Não é muito efetivo...", duration=0.5)

                # Toca som de impacto
                move_sound_manager.play_hit_sound(self.move.sound_name)

                # Toca animação de hurt
                if hasattr(self.target, 'play_hurt_animation'):
                    self.target.play_hurt_animation()

                print(f"[TRIPLE_KICK] Hit {self.current_hit}: Power={current_power}, Damage={actual_damage}")

                # Verifica se o alvo morreu
                if self.target.is_defeated or not self.target.is_alive():
                    print(f"[TRIPLE_KICK] {self.target.name} foi derrotado! Ataque interrompido.")
                    self.was_interrupted = True
                    return

        finally:
            # Restaura o poder original do move
            self.move.power = original_power

        # Avança para o próximo hit
        self.current_hit += 1
        self.hits_remaining -= 1

        # Se terminou todos os hits com sucesso
        if self.hits_remaining == 0:
            self._on_complete()

    def _on_complete(self):
        """Callback quando o Triple Kick completa todos os hits com sucesso"""
        self.effect_manager.add_status_text(
            self.attacker,
            f"{self.attacker.name} acertou todos os 3 chutes!",
            duration=1.5
        )

        # Se tiver dano total significativo, mostra
        if self.total_damage > 0:
            self.effect_manager.add_status_text(
                self.target,
                f"Dano total: {self.total_damage}!",
                duration=1.0
            )

        print(f"[TRIPLE_KICK] {self.attacker.name} completou o Triple Kick! "
              f"Dano total: {self.total_damage}, "
              f"Hits acertados: {len(self.hit_results)}/{self.total_hits}")

    def _get_ordinal_string(self, number: int) -> str:
        """Retorna a string ordinal (1º, 2º, 3º)"""
        ordinals = {1: "1º", 2: "2º", 3: "3º"}
        return ordinals.get(number, f"{number}º")

    def is_active(self) -> bool:
        """Retorna se o Triple Kick ainda está ativo"""
        return self.hits_remaining > 0 and not self.was_interrupted and self.target.is_alive()

    def get_progress(self) -> float:
        """Retorna o progresso do ataque (0 a 1)"""
        completed = self.total_hits - self.hits_remaining
        return completed / self.total_hits if self.total_hits > 0 else 0