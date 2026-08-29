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
    - Rain/Sandstorm: 1/4 (25%) do HP máximo
    """

    # Porcentagens de cura por clima
    HEAL_PERCENTAGES = {
        None: 0.5,  # Clima normal
        WeatherType.SUNNY: 2 / 3,  # 66.6%
        WeatherType.RAIN: 0.25,  # 25%
        WeatherType.SANDSTORM: 0.25,  # 25%
    }

    # ===== NOVO: Efeito do dia/noite =====
    # Morning Sun é afetado pelo dia/noite!
    # Noite: 25% em vez de 50%
    NIGHT_HEAL_MODIFIER = 0.5

    def __init__(self, move_name: str):
        self.move_name = move_name.lower()

    @classmethod
    def get_heal_percentage(cls, weather_type, is_night=False, move_name=None) -> float:
        """
        Retorna a porcentagem de cura baseada no clima e período.

        Args:
            weather_type: Tipo de clima (WeatherType ou None)
            is_night: Se é noite (afeta Morning Sun)
            move_name: Nome do movimento ('morning-sun', 'synthesis', 'moonlight')
        """
        # Percentagem base do clima
        base_percentage = cls.HEAL_PERCENTAGES.get(weather_type, 0.5)

        # ===== MORNING SUN: afetado pelo dia/noite =====
        if move_name and move_name.lower() == "morning-sun":
            if is_night:
                # Morning Sun cura menos à noite
                return base_percentage * cls.NIGHT_HEAL_MODIFIER

        return base_percentage

    @classmethod
    def get_heal_message(cls, weather_type, is_night=False, move_name=None) -> str:
        """Retorna a mensagem apropriada baseada no clima"""
        messages = []

        # Mensagem de clima
        if weather_type == WeatherType.SUNNY:
            messages.append("O sol forte aumentou a cura!")
        elif weather_type in [WeatherType.RAIN, WeatherType.SANDSTORM]:
            messages.append("O clima ruim reduziu a cura...")

        # Mensagem de noite (Morning Sun)
        if move_name and move_name.lower() == "morning-sun" and is_night:
            messages.append("A noite reduziu a luz do sol...")

        return " ".join(messages) if messages else ""

    def execute(self, attacker, target, battle_system, effect_manager) -> bool:
        """
        Executa a cura baseada no clima.
        """
        from src.managers.sounds.move_sound_manager import move_sound_manager

        # ===== DETERMINA O ALVO =====
        target_entity = attacker

        # ===== VERIFICA SE O POKÉMON JÁ ESTÁ COM HP CHEIO =====
        if target_entity.current_hp >= target_entity.max_hp:
            effect_manager.add_status_text(
                target_entity,
                f"O HP de {target_entity.name} já está no máximo!",
                duration=1.0
            )
            return False

        # ===== OBTÉM O CLIMA ATUAL =====
        weather_type = battle_system.get_weather_type()

        # ===== OBTÉM O PERÍODO (DIA/NOITE) =====
        is_night = False
        if hasattr(battle_system, 'game_scene'):
            game_scene = battle_system.game_scene
            if hasattr(game_scene, 'day_night_weather'):
                is_night = game_scene.day_night_weather.is_night()

        # ===== CALCULA A CURA =====
        heal_percentage = self.get_heal_percentage(
            weather_type, is_night, self.move_name
        )
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
        weather_message = self.get_heal_message(
            weather_type, is_night, self.move_name
        )
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
        period_name = "noite" if is_night else "dia"
        print(f"[{self.move_name.upper()}] {attacker.name} curou {actual_heal} HP "
              f"(clima: {weather_name}, período: {period_name}, porcentagem: {heal_percentage * 100:.0f}%)")

        # ===== TOCA SOM =====
        move_sound_manager.play_attack_sound("heal")

        # Gasta PP
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