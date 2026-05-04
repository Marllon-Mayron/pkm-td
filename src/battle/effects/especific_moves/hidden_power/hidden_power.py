# src/battle/effects/specific/hidden_power.py
"""
Hidden Power - Geração 6+
Tipo e poder são determinados pelos IVs do Pokémon.
Agora com suporte a 18 tipos (incluindo Fairy)
"""


class HiddenPowerCalculator:
    """
    Calcula o tipo e poder do Hidden Power baseado nos IVs.

    Fórmula Gen 6+:
    - Tipo: baseado no bit 0 (paridade) dos IVs
    - Agora suporta 18 tipos (0-17)
    - Poder fixo em 60 (a partir de Gen 6)
    """

    # Tabela de tipos para Gen 6+ (18 tipos)
    TYPE_TABLE = [
        "fighting",  # 0 - Lutador
        "flying",  # 1 - Voador
        "poison",  # 2 - Veneno
        "ground",  # 3 - Terra
        "rock",  # 4 - Pedra
        "bug",  # 5 - Inseto
        "ghost",  # 6 - Fantasma
        "steel",  # 7 - Aço
        "fire",  # 8 - Fogo
        "water",  # 9 - Água
        "grass",  # 10 - Planta
        "electric",  # 11 - Elétrico
        "psychic",  # 12 - Psíquico
        "ice",  # 13 - Gelo
        "dragon",  # 14 - Dragão
        "dark",  # 15 - Sombrio
        "fairy",  # 16 - Fada (Gen 6+)
        "normal"  # 17 - Normal (Gen 6+, raro)
    ]

    # Poder fixo a partir de Gen 6 (antes era variável 30-70)
    FIXED_POWER_GEN6 = 60

    @classmethod
    def calculate(cls, pokemon, gen: int = 6) -> tuple:
        """
        Calcula o tipo e poder do Hidden Power para um Pokémon.

        Args:
            pokemon: Pokémon para calcular
            gen: Geração (6+ usa poder fixo, anteriores usam fórmula variável)

        Returns:
            Tuple (tipo, poder)
        """
        ivs = pokemon.ivs

        # ===== CÁLCULO DO TIPO (baseado no BIT 0 - paridade) =====
        # Bit 0 = 1 se o IV é ímpar (IV % 2 == 1)
        hp_bit = ivs.get("hp", 0) & 1
        attack_bit = ivs.get("attack", 0) & 1
        defense_bit = ivs.get("defense", 0) & 1
        speed_bit = ivs.get("speed", 0) & 1
        sp_attack_bit = ivs.get("special_attack", 0) & 1
        sp_defense_bit = ivs.get("special_defense", 0) & 1

        # Fórmula: (bit0 * 1) + (bit1 * 2) + (bit2 * 4) + (bit3 * 8) + (bit4 * 16) + (bit5 * 32)
        type_value = (hp_bit * 1) + (attack_bit * 2) + (defense_bit * 4) + \
                     (speed_bit * 8) + (sp_attack_bit * 16) + (sp_defense_bit * 32)

        # Fórmula para 18 tipos: type = type_value * 17 / 63 (range 0-17)
        type_index = int((type_value * 17) / 63)
        type_index = min(17, max(0, type_index))  # Garante range 0-17

        pokemon_type = cls.TYPE_TABLE[type_index]

        # ===== CÁLCULO DO PODER =====
        if gen >= 6:
            # Gen 6+: poder fixo em 60
            power = cls.FIXED_POWER_GEN6
        else:
            # Gen 2-5: fórmula variável 30-70
            hp_power_bit = 1 if (ivs.get("hp", 0) % 4) >= 2 else 0
            attack_power_bit = 1 if (ivs.get("attack", 0) % 4) >= 2 else 0
            defense_power_bit = 1 if (ivs.get("defense", 0) % 4) >= 2 else 0
            speed_power_bit = 1 if (ivs.get("speed", 0) % 4) >= 2 else 0
            sp_attack_power_bit = 1 if (ivs.get("special_attack", 0) % 4) >= 2 else 0
            sp_defense_power_bit = 1 if (ivs.get("special_defense", 0) % 4) >= 2 else 0

            power_value = (hp_power_bit * 1) + (attack_power_bit * 2) + (defense_power_bit * 4) + \
                          (speed_power_bit * 8) + (sp_attack_power_bit * 16) + (sp_defense_power_bit * 32)

            power = int((power_value * 40) / 63) + 30
            power = max(30, min(70, power))  # Garante range 30-70

        return pokemon_type, power

    @classmethod
    def get_type_name_pt(cls, type_en: str) -> str:
        """Retorna o nome do tipo em português"""
        type_names = {
            "fighting": "Lutador",
            "flying": "Voador",
            "poison": "Veneno",
            "ground": "Terra",
            "rock": "Pedra",
            "bug": "Inseto",
            "ghost": "Fantasma",
            "steel": "Aço",
            "fire": "Fogo",
            "water": "Água",
            "grass": "Planta",
            "electric": "Elétrico",
            "psychic": "Psíquico",
            "ice": "Gelo",
            "dragon": "Dragão",
            "dark": "Sombrio",
            "fairy": "Fada",
            "normal": "Normal"
        }
        return type_names.get(type_en, type_en.capitalize())