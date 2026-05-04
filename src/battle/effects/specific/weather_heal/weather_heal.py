# src/battle/effects/specific/weather_heal.py
"""
Movimentos de cura que variam com o clima.
Morning Sun, Synthesis, Moonlight.
"""

from src.battle.effects.specific.weather.weather_state import WeatherType


class WeatherHealMove:
    """
    Classe base para movimentos que curam baseado no clima.

    Morning Sun (Normal)
    Synthesis (Grass)
    Moonlight (Fairy)

    Tabela de cura:
    - Clima normal: 50% do HP máximo
    - Sunny Day: 2/3 (66.6%) do HP máximo
    - Hail/Rain/Sandstorm: 1/4 (25%) do HP máximo
    """

    # Porcentagens de cura por clima
    HEAL_PERCENTAGES = {
        None: 0.5,  # Clima normal
        WeatherType.SUNNY: 2 / 3,  # 66.6%
        WeatherType.RAIN: 0.25,  # 25%
        WeatherType.SANDSTORM: 0.25,  # 25%
        WeatherType.HAIL: 0.25,  # 25% (se implementado)
    }

    def __init__(self, move_name: str):
        self.move_name = move_name.lower()

    @classmethod
    def get_heal_percentage(cls, weather_type) -> float:
        """Retorna a porcentagem de cura baseada no clima atual"""
        return cls.HEAL_PERCENTAGES.get(weather_type, 0.5)

    @classmethod
    def get_heal_message(cls, weather_type) -> str:
        """Retorna a mensagem apropriada baseada no clima"""
        if weather_type == WeatherType.SUNNY:
            return "O sol forte aumentou a cura!"
        elif weather_type in [WeatherType.RAIN, WeatherType.SANDSTORM]:
            return "O clima ruim reduziu a cura..."
        return ""

    def execute(self, attacker, target, battle_system, effect_manager) -> bool:
        """
        Executa a cura baseada no clima.

        Args:
            attacker: Pokémon que está usando o movimento
            target: Alvo (geralmente o próprio atacante)
            battle_system: Sistema de batalha
            effect_manager: Gerenciador de efeitos
        """
        from src.managers.sounds.move_sound_manager import move_sound_manager

        # ===== DETERMINA O ALVO =====
        # Morning Sun, Synthesis, Moonlight sempre curam o usuário
        target_entity = attacker

        # ===== VERIFICA SE O POKÉMON JÁ ESTÁ COM HP CHEIO =====
        if target_entity.current_hp >= target_entity.max_hp:
            effect_manager.add_status_text(
                target_entity,
                f"O HP de {target_entity.name} já está no máximo!",
                duration=1.0
            )
            print(f"[{self.move_name.upper()}] {target_entity.name} já está com HP cheio!")
            return False

        # ===== OBTÉM O CLIMA ATUAL =====
        weather_type = battle_system.get_weather_type()

        # ===== CALCULA A CURA =====
        heal_percentage = self.get_heal_percentage(weather_type)
        heal_amount = int(target_entity.max_hp * heal_percentage)

        # Garante cura mínima de 1 HP
        heal_amount = max(1, heal_amount)

        # ===== APLICA A CURA =====
        old_hp = target_entity.current_hp
        new_hp = min(target_entity.max_hp, target_entity.current_hp + heal_amount)
        actual_heal = new_hp - old_hp

        if actual_heal <= 0:
            effect_manager.add_status_text(
                target_entity,
                f"Mas falhou!",
                duration=0.8
            )
            return False

        target_entity.current_hp = new_hp

        # ===== MOSTRA MENSAGENS =====
        # Mensagem principal do movimento
        move_names_pt = {
            "morning-sun": "Sol Matinal",
            "synthesis": "Síntese",
            "moonlight": "Luar"
        }
        move_name_pt = move_names_pt.get(self.move_name, self.move_name.capitalize())

        effect_manager.add_status_text(
            target_entity,
            f"{target_entity.name} usou {move_name_pt}!",
            duration=1.5
        )

        # Mensagem do clima
        weather_message = self.get_heal_message(weather_type)
        if weather_message:
            effect_manager.add_status_text(
                target_entity,
                weather_message,
                duration=1.0
            )

        # Mensagem da cura
        effect_manager.add_status_text(
            target_entity,
            f"{target_entity.name} recuperou {actual_heal} HP!",
            duration=1.5
        )

        # ===== LOG =====
        weather_name = weather_type.value if weather_type else "normal"
        print(f"[{self.move_name.upper()}] {attacker.name} curou {actual_heal} HP "
              f"(clima: {weather_name}, porcentagem: {heal_percentage * 100:.0f}%)")

        # ===== TOCA SOM =====
        move_sound_manager.play_attack_sound("heal")

        # Gasta PP (o sistema já gasta, mas garantimos)
        current_move = attacker.get_current_move()
        if current_move:
            current_move.current_pp -= 1

        # Cooldown do atacante
        attacker.attack_cooldown = attacker.attack_cooldown_max

        return True


# ===== FACTORIES PARA CADA MOVE =====

class MorningSun(WeatherHealMove):
    """Morning Sun - Sol Matinal"""

    def __init__(self):
        super().__init__("morning-sun")


class Synthesis(WeatherHealMove):
    """Synthesis - Síntese"""

    def __init__(self):
        super().__init__("synthesis")


class Moonlight(WeatherHealMove):
    """Moonlight - Luar"""

    def __init__(self):
        super().__init__("moonlight")