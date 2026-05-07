# src/entities/pokemon/stats.py
import random
from typing import Dict


class PokemonStats:
    """Gerencia todos os cálculos de stats do Pokémon"""

    EVS_PER_STAT_POINT = 8  # Quantos EVs para +1 ponto (era 4) → 2x mais difícil
    MAX_TOTAL_EVS = 1020  # Limite total (era 510) → 2x maior
    MAX_EV_PER_STAT = 504  # Limite por stat (1020/2 ≈ 510, 504 é múltiplo de 8)

    def __init__(self, pokemon):
        self.pokemon = pokemon

    def calculate_stats(self):
        """Calcula stats baseado em level, IVs e EVs - SUPORTA TRANSFORM"""

        if hasattr(self.pokemon, '_is_transformed') and self.pokemon._is_transformed:
            base_stats = self.pokemon.base_stats
        else:
            base_stats = self.pokemon.pokedex.get_pokemon(self.pokemon.id)["base_stats"]

        stats = self.pokemon.pokedex.calculate_stats_with_base(
            base_stats,
            self.pokemon.level,
            self.pokemon.ivs,
            self.pokemon.evs
        )

        self.pokemon.max_hp = stats["hp"]
        self.pokemon.attack = stats["attack"]
        self.pokemon.defense = stats["defense"]
        self.pokemon.sp_attack = stats["special_attack"]
        self.pokemon.sp_defense = stats["special_defense"]
        self.pokemon.speed_stat = stats["speed"]

        if hasattr(self.pokemon, 'nature_multipliers'):
            mult = self.pokemon.nature_multipliers
            if mult["attack"] != 1.0:
                self.pokemon.attack = int(self.pokemon.attack * mult["attack"])
            if mult["defense"] != 1.0:
                self.pokemon.defense = int(self.pokemon.defense * mult["defense"])
            if mult["sp_attack"] != 1.0:
                self.pokemon.sp_attack = int(self.pokemon.sp_attack * mult["sp_attack"])
            if mult["sp_defense"] != 1.0:
                self.pokemon.sp_defense = int(self.pokemon.sp_defense * mult["sp_defense"])
            if mult["speed"] != 1.0:
                self.pokemon.speed_stat = int(self.pokemon.speed_stat * mult["speed"])

    def calculate_xp_needed(self) -> int:
        """
        Calcula XP necessário para o próximo nível.

        Fórmula: level² × 2

        Resultado: nível 100 → 20,000 XP (metade do original que era 1,000,000)

        Exemplos:
        - Nível 1 → 2 XP
        - Nível 5 → 50 XP
        - Nível 10 → 200 XP
        - Nível 20 → 800 XP
        - Nível 30 → 1,800 XP
        - Nível 40 → 3,200 XP
        - Nível 50 → 5,000 XP
        - Nível 100 → 20,000 XP
        """
        return (self.pokemon.level ** 2) * 2

    def calculate_attack_damage(self) -> float:
        return (self.pokemon.attack + self.pokemon.sp_attack) / 2

    def calculate_defense(self) -> float:
        return (self.pokemon.defense + self.pokemon.sp_defense) / 2

    def calculate_wild_move_speed(self) -> float:
        MIN_MOVE_SPEED = self.pokemon._MIN_MOVE_SPEED
        MAX_MOVE_SPEED = self.pokemon._MAX_MOVE_SPEED

        min_base = self.pokemon.pokedex.min_base_speed
        max_base = self.pokemon.pokedex.max_base_speed
        base_speed = self.pokemon.base_stats["speed"]

        if max_base > min_base:
            base_norm = (base_speed - min_base) / (max_base - min_base)
            base_norm = max(0.0, min(1.0, base_norm))
        else:
            base_norm = 0.5

        nature_min = 0.9
        nature_max = 1.1

        def calc_speed_stat(iv, ev, nature_mult):
            raw = ((2 * base_speed + iv + (ev // 4)) * self.pokemon.level) / 100 + 5
            return int(raw * nature_mult)

        min_speed_stat = calc_speed_stat(0, 0, nature_min)
        max_speed_stat = calc_speed_stat(31, 252, nature_max)
        actual_speed = self.pokemon.speed_stat

        if max_speed_stat > min_speed_stat:
            stat_norm = (actual_speed - min_speed_stat) / (max_speed_stat - min_speed_stat)
            stat_norm = max(0.0, min(1.0, stat_norm))
        else:
            stat_norm = 0.5

        combined_norm = base_norm * (0.8 + 0.2 * stat_norm)
        level_factor = 1.0 + (self.pokemon.level / 100) * 0.3

        move_speed = MIN_MOVE_SPEED + (MAX_MOVE_SPEED - MIN_MOVE_SPEED) * combined_norm
        move_speed *= level_factor

        speed_mult = 1.0
        if hasattr(self.pokemon, 'effect_manager') and self.pokemon.effect_manager:
            try:
                from src.battle.effects import StatType
                speed_mult = self.pokemon.effect_manager.get_stat_multiplier(self.pokemon, StatType.SPEED)
                move_speed *= speed_mult
            except Exception:
                pass

        if self.pokemon.is_shiny:
            move_speed *= 1.25
        if self.pokemon.is_boss:
            move_speed *= 0.7

        return max(MIN_MOVE_SPEED, min(MAX_MOVE_SPEED, move_speed))

    def get_cached_move_speed(self):
        cache_key = (self.pokemon.id, self.pokemon.level, self.pokemon.speed_stat,
                     self.pokemon.is_shiny, self.pokemon.is_boss)

        if cache_key in self.pokemon._speed_cache:
            return self.pokemon._speed_cache[cache_key]

        speed = self.calculate_wild_move_speed()
        if len(self.pokemon._speed_cache) > 1000:
            self.pokemon._speed_cache.clear()
        self.pokemon._speed_cache[cache_key] = speed
        return speed

    def generate_nature(self):
        natures = [
            {"name": "Hardy", "attack": 1.0, "defense": 1.0, "sp_attack": 1.0, "sp_defense": 1.0, "speed": 1.0},
            {"name": "Lonely", "attack": 1.1, "defense": 0.9, "sp_attack": 1.0, "sp_defense": 1.0, "speed": 1.0},
            {"name": "Brave", "attack": 1.1, "defense": 1.0, "sp_attack": 1.0, "sp_defense": 1.0, "speed": 0.9},
            {"name": "Adamant", "attack": 1.1, "defense": 1.0, "sp_attack": 0.9, "sp_defense": 1.0, "speed": 1.0},
            {"name": "Naughty", "attack": 1.1, "defense": 1.0, "sp_attack": 1.0, "sp_defense": 0.9, "speed": 1.0},
            {"name": "Bold", "attack": 0.9, "defense": 1.1, "sp_attack": 1.0, "sp_defense": 1.0, "speed": 1.0},
            {"name": "Relaxed", "attack": 1.0, "defense": 1.1, "sp_attack": 1.0, "sp_defense": 1.0, "speed": 0.9},
            {"name": "Impish", "attack": 1.0, "defense": 1.1, "sp_attack": 0.9, "sp_defense": 1.0, "speed": 1.0},
            {"name": "Lax", "attack": 1.0, "defense": 1.1, "sp_attack": 1.0, "sp_defense": 0.9, "speed": 1.0},
            {"name": "Timid", "attack": 0.9, "defense": 1.0, "sp_attack": 1.0, "sp_defense": 1.0, "speed": 1.1},
            {"name": "Hasty", "attack": 1.0, "defense": 0.9, "sp_attack": 1.0, "sp_defense": 1.0, "speed": 1.1},
            {"name": "Jolly", "attack": 1.0, "defense": 1.0, "sp_attack": 0.9, "sp_defense": 1.0, "speed": 1.1},
            {"name": "Naive", "attack": 1.0, "defense": 1.0, "sp_attack": 1.0, "sp_defense": 0.9, "speed": 1.1},
            {"name": "Modest", "attack": 0.9, "defense": 1.0, "sp_attack": 1.1, "sp_defense": 1.0, "speed": 1.0},
            {"name": "Mild", "attack": 1.0, "defense": 0.9, "sp_attack": 1.1, "sp_defense": 1.0, "speed": 1.0},
            {"name": "Quiet", "attack": 1.0, "defense": 1.0, "sp_attack": 1.1, "sp_defense": 1.0, "speed": 0.9},
            {"name": "Rash", "attack": 1.0, "defense": 1.0, "sp_attack": 1.1, "sp_defense": 0.9, "speed": 1.0},
            {"name": "Calm", "attack": 0.9, "defense": 1.0, "sp_attack": 1.0, "sp_defense": 1.1, "speed": 1.0},
            {"name": "Gentle", "attack": 1.0, "defense": 0.9, "sp_attack": 1.0, "sp_defense": 1.1, "speed": 1.0},
            {"name": "Sassy", "attack": 1.0, "defense": 1.0, "sp_attack": 1.0, "sp_defense": 1.1, "speed": 0.9},
            {"name": "Careful", "attack": 1.0, "defense": 1.0, "sp_attack": 0.9, "sp_defense": 1.1, "speed": 1.0},
            {"name": "Quirky", "attack": 1.0, "defense": 1.0, "sp_attack": 1.0, "sp_defense": 1.0, "speed": 1.0},
        ]
        return random.choice(natures)

    def gain_evs(self, ev_yield: dict, multiplier: float = 1.0):
        total_evs_before = sum(self.pokemon.evs.values())
        evs_gained = {}

        for stat, value in ev_yield.items():
            if value <= 0:
                continue

            actual_gain = int(value * multiplier)
            if actual_gain <= 0:
                continue

            current = self.pokemon.evs.get(stat, 0)
            new_value = min(self.MAX_EV_PER_STAT, current + actual_gain)
            actual_gain = new_value - current

            if actual_gain > 0:
                self.pokemon.evs[stat] = new_value
                evs_gained[stat] = actual_gain

        total_evs_after = sum(self.pokemon.evs.values())

        if total_evs_after > self.MAX_TOTAL_EVS:
            excess = total_evs_after - self.MAX_TOTAL_EVS
            self._reduce_excess_evs(excess, evs_gained)
            total_evs_after = self.MAX_TOTAL_EVS

        total_gained = total_evs_after - total_evs_before

        if total_gained > 0:
            print(f"[EVS] {self.pokemon.name} ganhou {total_gained} EVs totais!")
            for stat, gain in evs_gained.items():
                print(f"  └─ +{gain} {stat.upper()} (agora: {self.pokemon.evs[stat]}/{self.MAX_EV_PER_STAT})")

            old_max_hp = self.pokemon.max_hp
            self.calculate_stats()

            if self.pokemon.current_hp > 0:
                hp_increase = self.pokemon.max_hp - old_max_hp
                if hp_increase > 0:
                    self.pokemon.current_hp += hp_increase

        return evs_gained

    def _reduce_excess_evs(self, excess: int, last_gained: dict):
        total_evs = sum(self.pokemon.evs.values())
        if total_evs <= self.MAX_TOTAL_EVS:
            return

        total_gained = sum(last_gained.values())
        if total_gained == 0:
            return

        for stat, gained in last_gained.items():
            if gained > 0:
                reduction = int(gained * (excess / total_gained))
                if reduction > 0:
                    self.pokemon.evs[stat] = max(0, self.pokemon.evs[stat] - reduction)

    def get_ev_total(self) -> int:
        return sum(self.pokemon.evs.values())

    def get_ev_percentage(self) -> float:
        return min(1.0, self.get_ev_total() / self.MAX_TOTAL_EVS)

    def get_ev_bonus(self, stat: str) -> int:
        ev_value = self.pokemon.evs.get(stat, 0)
        return ev_value // self.EVS_PER_STAT_POINT

    def reset_evs(self):
        for stat in self.pokemon.evs:
            self.pokemon.evs[stat] = 0
        self.calculate_stats()

    def can_gain_evs(self, ev_yield: dict) -> bool:
        total_after = self.get_ev_total() + sum(ev_yield.values())
        if total_after > self.MAX_TOTAL_EVS:
            return False

        for stat, value in ev_yield.items():
            if value <= 0:
                continue
            if self.pokemon.evs.get(stat, 0) + value > self.MAX_EV_PER_STAT:
                return False
        return True