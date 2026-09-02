# src/managers/achievement_manager.py

from typing import Dict, List, Optional, Set, Any
from datetime import datetime
from src.data.achievement_data import Achievement, ACHIEVEMENTS, AchievementRarity
from src.ui.toast_renderer import toast_achievement
from src.data.item_bag_catalog import item_bag_catalog


class AchievementManager:
    """Gerencia conquistas do jogador"""

    def __init__(self, player):
        self.player = player
        self._unlocked: Set[str] = set()
        self._counters: Dict[str, int] = {}
        self._unlocked_data: Dict[str, Dict] = {}

        # Carrega estado do jogador
        self.load_from_player()

    def load_from_player(self):
        """Carrega estado das conquistas do jogador"""
        if hasattr(self.player, 'achievements'):
            self._unlocked = set(self.player.achievements.get("unlocked", []))
            self._counters = self.player.achievements.get("counters", {}).copy()
            self._unlocked_data = self.player.achievements.get("unlocked_data", {}).copy()
        else:
            self._unlocked = set()
            self._counters = {}
            self._unlocked_data = {}

    def save_to_player(self):
        """Salva estado das conquistas no jogador"""
        if not hasattr(self.player, 'achievements'):
            self.player.achievements = {
                "unlocked": [],
                "counters": {},
                "unlocked_data": {}
            }

        self.player.achievements["unlocked"] = list(self._unlocked)
        self.player.achievements["counters"] = self._counters.copy()
        self.player.achievements["unlocked_data"] = self._unlocked_data.copy()

    def get_all_achievements(self) -> List[Achievement]:
        """Retorna todas as conquistas com estado atualizado"""
        achievements = []
        for ach_id, ach in ACHIEVEMENTS.items():
            unlocked = ach_id in self._unlocked
            unlocked_data = self._unlocked_data.get(ach_id, {})

            ach_copy = Achievement(
                id=ach.id,
                title=ach.title,
                description=ach.description,
                rarity=ach.rarity,
                rewards=ach.rewards.copy(),
                unlocked=unlocked,
                unlocked_at=unlocked_data.get("unlocked_at") if unlocked else None,
                unlocked_phase=unlocked_data.get("unlocked_phase") if unlocked else None
            )
            achievements.append(ach_copy)
        return achievements

    def get_unlocked_count(self) -> int:
        return len(self._unlocked)

    def get_total_count(self) -> int:
        return len(ACHIEVEMENTS)

    def is_unlocked(self, achievement_id: str) -> bool:
        return achievement_id in self._unlocked

    def get_counter(self, counter_id: str) -> int:
        return self._counters.get(counter_id, 0)

    def increment_counter(self, counter_id: str, amount: int = 1) -> int:
        new_value = self._counters.get(counter_id, 0) + amount
        self._counters[counter_id] = new_value
        self.save_to_player()
        return new_value

    def set_counter(self, counter_id: str, value: int):
        self._counters[counter_id] = value
        self.save_to_player()

    def unlock(self, achievement_id: str, phase_id: Optional[str] = None) -> bool:
        """Desbloqueia uma conquista e aplica recompensas"""
        if achievement_id in self._unlocked:
            return False

        achievement = ACHIEVEMENTS.get(achievement_id)
        if not achievement:
            return False

        # Registra data/hora
        now = datetime.now()
        unlocked_at = now.strftime("%d/%m/%Y as %H:%M")

        self._unlocked.add(achievement_id)
        self._unlocked_data[achievement_id] = {
            "unlocked_at": unlocked_at,
            "unlocked_phase": phase_id if phase_id else "Desconhecida"
        }

        self.save_to_player()

        # APLICA RECOMPENSAS
        self._apply_rewards(achievement)

        # Mostra toast
        self._show_achievement_toast(achievement)

        print(f"[ACHIEVEMENT] Desbloqueado: {achievement.title} em {unlocked_at}")
        return True

    def _apply_rewards(self, achievement: Achievement):
        """Aplica recompensas variadas (gold, xp, items, pokemon)"""
        rewards = achievement.rewards

        # ===== OURO =====
        if "gold" in rewards:
            amount = rewards["gold"]
            self.player.money += amount
            print(f"[ACHIEVEMENT] +{amount} ouro")

        # ===== XP =====
        if "xp" in rewards:
            amount = rewards["xp"]
            self.player.score += amount
            print(f"[ACHIEVEMENT] +{amount} XP para o jogador")

        # ===== ITENS =====
        if "items" in rewards:
            items = rewards["items"]
            for item_id, quantity in items.items():
                self.player.bag.add_item(item_id, quantity)
                item_name = item_bag_catalog.get_item(item_id)["name"]
                print(f"[ACHIEVEMENT] +{quantity}x {item_name}")

        # ===== POKÉMON =====
        if "pokemon" in rewards:
            pokemon_id = rewards["pokemon"]
            self._give_pokemon_reward(pokemon_id)

    def _give_pokemon_reward(self, pokemon_id: int):
        """Dá um Pokémon como recompensa (nível 5)"""
        from src.entities.pokemon import Pokemon

        # Cria o Pokémon nível 5
        new_pokemon = Pokemon(0, 0, pokemon_id, level=5, is_wild=False)

        # Tenta adicionar ao time
        if len(self.player.team) < 6:
            self.player.team.append(new_pokemon)
            new_pokemon.is_in_team = True
            location = "time"
        else:
            self.player.pc_box.append(new_pokemon)
            new_pokemon.is_in_team = False
            location = "PC Box"

        self.player.caught_pokemon.add(pokemon_id)

        print(f"[ACHIEVEMENT] Pokémon {new_pokemon.name} adicionado ao {location}!")

        # Mostra mensagem especial no toast
        from src.ui.toast_renderer import toast_battle
        toast_battle(
            f"Você ganhou um {new_pokemon.name} como recompensa!",
            duration=4.0,
            pokemon=new_pokemon,
            portrait="happy"
        )

    def _show_achievement_toast(self, achievement: Achievement):
        """Mostra toast de conquista desbloqueada"""
        rarity_name = achievement.rarity.display_name.upper()

        # Verifica se tem recompensa especial para destacar
        rewards_text = []
        if "pokemon" in achievement.rewards:
            from src.data.pokedex import Pokedex
            pokedex = Pokedex()
            pokemon_name = pokedex.get_name(achievement.rewards["pokemon"])
            rewards_text.append(f"{pokemon_name}")
        if "items" in achievement.rewards:
            items = achievement.rewards["items"]
            for item_id, qty in items.items():
                item_name = item_bag_catalog.get_item(item_id)["name"]
                rewards_text.append(f"{qty}x {item_name}")

        if rewards_text:
            message = f"{achievement.title} ({rarity_name})\n+ {', '.join(rewards_text)}"
        else:
            message = f"{achievement.title} ({rarity_name})"

        toast_achievement(message, duration=4.0)

    def check_and_unlock(self, achievement_id: str, phase_id: Optional[str] = None) -> bool:
        """Verifica se uma conquista pode ser desbloqueada"""
        if self.is_unlocked(achievement_id):
            return False

        # ===== CONQUISTAS EXISTENTES =====
        if achievement_id == "first_capture":
            if self.get_counter("capture_count") >= 1:
                return self.unlock(achievement_id, phase_id)

        elif achievement_id == "heal_5":
            if self.get_counter("heal_count") >= 5:
                return self.unlock(achievement_id, phase_id)

        elif achievement_id == "first_badge":
            if self.get_counter("badge_count") >= 1:
                return self.unlock(achievement_id, phase_id)

        elif achievement_id == "capture_10":
            if self.get_counter("capture_count") >= 10:
                return self.unlock(achievement_id, phase_id)

        elif achievement_id == "heal_100":
            if self.get_counter("heal_count") >= 100:
                return self.unlock(achievement_id, phase_id)

        elif achievement_id == "capture_50":
            if self.get_counter("capture_count") >= 50:
                return self.unlock(achievement_id, phase_id)

        elif achievement_id == "perfect_phase":
            if self.get_counter("perfect_phase_count") >= 1:
                return self.unlock(achievement_id, phase_id)

        elif achievement_id == "boss_defeated":
            if self.get_counter("boss_defeated_count") >= 1:
                return self.unlock(achievement_id, phase_id)

        # ===== CLIMA =====
        elif achievement_id == "first_weather_change":
            if self.get_counter("weather_change_count") >= 1:
                return self.unlock(achievement_id, phase_id)

        elif achievement_id == "weather_change_50":
            if self.get_counter("weather_change_count") >= 50:
                return self.unlock(achievement_id, phase_id)

        elif achievement_id == "weather_change_100":
            if self.get_counter("weather_change_count") >= 100:
                return self.unlock(achievement_id, phase_id)

        elif achievement_id == "first_weather_boosted_attack":
            if self.get_counter("weather_boosted_attack_count") >= 1:
                return self.unlock(achievement_id, phase_id)

        # ===== EVOLUÇÃO GERAL =====
        elif achievement_id == "first_evolution":
            if self.get_counter("evolution_count") >= 1:
                return self.unlock(achievement_id, phase_id)

        elif achievement_id == "evolution_10":
            if self.get_counter("evolution_count") >= 10:
                return self.unlock(achievement_id, phase_id)

        elif achievement_id == "evolution_50":
            if self.get_counter("evolution_count") >= 50:
                return self.unlock(achievement_id, phase_id)

        # ===== EVOLUÇÃO POR NÍVEL =====
        elif achievement_id == "first_level_evolution":
            if self.get_counter("level_evolution_count") >= 1:
                return self.unlock(achievement_id, phase_id)

        elif achievement_id == "level_evolution_50":
            if self.get_counter("level_evolution_count") >= 50:
                return self.unlock(achievement_id, phase_id)

        # ===== EVOLUÇÃO POR PEDRA =====
        elif achievement_id == "first_stone_evolution":
            if self.get_counter("stone_evolution_count") >= 1:
                return self.unlock(achievement_id, phase_id)

        elif achievement_id == "stone_evolution_5":
            if self.get_counter("stone_evolution_count") >= 5:
                return self.unlock(achievement_id, phase_id)

        elif achievement_id == "stone_evolution_20":
            if self.get_counter("stone_evolution_count") >= 20:
                return self.unlock(achievement_id, phase_id)

        # ===== EVOLUÇÃO POR FELICIDADE =====
        elif achievement_id == "max_happiness":
            # Verifica se algum Pokémon do time tem felicidade >= 255
            for pokemon in self.player.team:
                if pokemon.get_happiness() >= 255:
                    return self.unlock(achievement_id, phase_id)
            return False

        elif achievement_id == "full_team_max_happiness":
            # Verifica se TODOS os Pokémon do time têm felicidade máxima (255)
            if not self.player.team:
                return False
            all_max = all(pokemon.get_happiness() >= 255 for pokemon in self.player.team)
            if all_max:
                return self.unlock(achievement_id, phase_id)
            return False

        elif achievement_id == "first_happiness_evolution":
            if self.get_counter("happiness_evolution_count") >= 1:
                return self.unlock(achievement_id, phase_id)

        elif achievement_id == "happiness_evolution_3":
            if self.get_counter("happiness_evolution_count") >= 3:
                return self.unlock(achievement_id, phase_id)

        elif achievement_id == "happiness_evolution_10":
            if self.get_counter("happiness_evolution_count") >= 10:
                return self.unlock(achievement_id, phase_id)

        # ===== EVOLUÇÃO POR CLIMA =====
        elif achievement_id == "first_weather_evolution":
            if self.get_counter("weather_evolution_count") >= 1:
                return self.unlock(achievement_id, phase_id)

        elif achievement_id == "weather_evolution_5":
            if self.get_counter("weather_evolution_count") >= 5:
                return self.unlock(achievement_id, phase_id)

        # ===== BLOQUEIO DE EVOLUÇÃO =====
        elif achievement_id == "first_evolution_blocked":
            if self.get_counter("evolution_blocked_count") >= 1:
                return self.unlock(achievement_id, phase_id)

        elif achievement_id == "evolution_blocked_10":
            if self.get_counter("evolution_blocked_count") >= 10:
                return self.unlock(achievement_id, phase_id)

        # ===== CURA DE STATUS =====
        elif achievement_id == "first_antidote":
            if self.get_counter("antidote_count") >= 1:
                return self.unlock(achievement_id, phase_id)

        elif achievement_id == "antidote_100":
            if self.get_counter("antidote_count") >= 100:
                return self.unlock(achievement_id, phase_id)

        elif achievement_id == "first_awake":
            if self.get_counter("awake_count") >= 1:
                return self.unlock(achievement_id, phase_id)

        elif achievement_id == "awake_100":
            if self.get_counter("awake_count") >= 100:
                return self.unlock(achievement_id, phase_id)

        elif achievement_id == "first_paralyze_heal":
            if self.get_counter("paralyze_heal_count") >= 1:
                return self.unlock(achievement_id, phase_id)

        elif achievement_id == "paralyze_heal_100":
            if self.get_counter("paralyze_heal_count") >= 100:
                return self.unlock(achievement_id, phase_id)

        elif achievement_id == "first_revive":
            if self.get_counter("revive_count") >= 1:
                return self.unlock(achievement_id, phase_id)

        elif achievement_id == "revive_25":
            if self.get_counter("revive_count") >= 25:
                return self.unlock(achievement_id, phase_id)

        # ===== ENSINO DE MOVES =====
        elif achievement_id == "first_move_taught":
            if self.get_counter("move_taught_count") >= 1:
                return self.unlock(achievement_id, phase_id)

        elif achievement_id == "move_taught_10":
            if self.get_counter("move_taught_count") >= 10:
                return self.unlock(achievement_id, phase_id)

        return False

    def check_all_counters(self, phase_id: Optional[str] = None):
        for ach_id in ACHIEVEMENTS.keys():
            self.check_and_unlock(ach_id, phase_id)

    def get_progress(self, achievement_id: str) -> tuple:
        """Retorna o progresso de uma conquista (atual, necessário)"""
        progress_map = {
            # ===== EXISTENTES =====
            "first_capture": ("capture_count", 1),
            "heal_5": ("heal_count", 5),
            "first_badge": ("badge_count", 1),
            "capture_10": ("capture_count", 10),
            "heal_100": ("heal_count", 100),
            "capture_50": ("capture_count", 50),
            "perfect_phase": ("perfect_phase_count", 1),
            "boss_defeated": ("boss_defeated_count", 1),

            # ===== CLIMA =====
            "first_weather_change": ("weather_change_count", 1),
            "weather_change_50": ("weather_change_count", 50),
            "weather_change_100": ("weather_change_count", 100),
            "first_weather_boosted_attack": ("weather_boosted_attack_count", 1),

            # ===== EVOLUÇÃO GERAL =====
            "first_evolution": ("evolution_count", 1),
            "evolution_10": ("evolution_count", 10),
            "evolution_50": ("evolution_count", 50),

            # ===== EVOLUÇÃO POR NÍVEL =====
            "first_level_evolution": ("level_evolution_count", 1),
            "level_evolution_50": ("level_evolution_count", 50),

            # ===== EVOLUÇÃO POR PEDRA =====
            "first_stone_evolution": ("stone_evolution_count", 1),
            "stone_evolution_5": ("stone_evolution_count", 5),
            "stone_evolution_20": ("stone_evolution_count", 20),

            # ===== EVOLUÇÃO POR FELICIDADE =====
            "max_happiness": ("max_happiness_check", 1),  # Especial
            "full_team_max_happiness": ("full_team_max_happiness_check", 1),  # Especial
            "first_happiness_evolution": ("happiness_evolution_count", 1),
            "happiness_evolution_3": ("happiness_evolution_count", 3),
            "happiness_evolution_10": ("happiness_evolution_count", 10),

            # ===== EVOLUÇÃO POR CLIMA =====
            "first_weather_evolution": ("weather_evolution_count", 1),
            "weather_evolution_5": ("weather_evolution_count", 5),

            # ===== BLOQUEIO DE EVOLUÇÃO =====
            "first_evolution_blocked": ("evolution_blocked_count", 1),
            "evolution_blocked_10": ("evolution_blocked_count", 10),

            # ===== CURA DE STATUS =====
            "first_antidote": ("antidote_count", 1),
            "antidote_100": ("antidote_count", 100),
            "first_awake": ("awake_count", 1),
            "awake_100": ("awake_count", 100),
            "first_paralyze_heal": ("paralyze_heal_count", 1),
            "paralyze_heal_100": ("paralyze_heal_count", 100),
            "first_revive": ("revive_count", 1),
            "revive_25": ("revive_count", 25),

            # ===== ENSINO DE MOVES =====
            "first_move_taught": ("move_taught_count", 1),
            "move_taught_10": ("move_taught_count", 10),
        }

        if achievement_id in progress_map:
            counter_id, required = progress_map[achievement_id]
            current = self.get_counter(counter_id)
            return (current, required)

        return (0, 1)