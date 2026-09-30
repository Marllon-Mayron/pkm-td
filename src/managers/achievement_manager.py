# src/managers/achievement_manager.py

from typing import Dict, List, Optional, Set
from datetime import datetime

from src.data.achievement_data import Achievement, ACHIEVEMENTS
from src.ui.toast_renderer import toast_achievement
from src.data.item_bag_catalog import item_bag_catalog
from src.config.regions import (
    DEFAULT_REGION_ID, parse_phase_id, normalize_phase_id, make_phase_id,
    RegionCatalog,
)


def _key(region_id: int, achievement_id: str) -> str:
    return f"{int(region_id)}:{achievement_id}"


def _ckey(region_id: int, counter_id: str) -> str:
    return f"{int(region_id)}:{counter_id}"


class AchievementManager:
    """
    Conquistas do jogador — UMA POR REGIÃO.

    Cada conquista pode ser desbloqueada independentemente em Kanto, Hoenn, etc.
    A região efetiva é derivada do `phase_id` no momento do unlock ("R:C:P").
    """

    def __init__(self, player):
        self.player = player
        self._current_region: int = DEFAULT_REGION_ID

        self._unlocked: Set[str] = set()           # "R:achievement_id"
        self._counters: Dict[str, int] = {}        # "R:counter_id" -> int
        self._unlocked_data: Dict[str, Dict] = {}  # "R:achievement_id" -> {...}

        self.load_from_player()

    # ==================================================================
    # REGIÃO ATUAL
    # ==================================================================
    def set_current_region(self, region_id) -> None:
        try:
            self._current_region = int(region_id)
        except (TypeError, ValueError):
            self._current_region = DEFAULT_REGION_ID

    def get_current_region(self) -> int:
        return self._current_region

    # ==================================================================
    # PERSISTÊNCIA
    # ==================================================================
    def load_from_player(self):
        """Aceita formato antigo (sem região) e novo (composto "R:id")."""
        if not hasattr(self.player, 'achievements'):
            self.player.achievements = {
                "unlocked": [], "counters": {}, "unlocked_data": {},
            }

        raw = self.player.achievements or {}
        raw_unlocked = raw.get("unlocked", []) or []
        raw_counters = raw.get("counters", {}) or {}
        raw_udata = raw.get("unlocked_data", {}) or {}

        self._unlocked = set()
        self._counters = {}
        self._unlocked_data = {}

        # ---- unlocked ----
        for entry in raw_unlocked:
            s = str(entry)
            parts = s.split(":")
            if len(parts) == 2:
                try:
                    int(parts[0])
                    self._unlocked.add(s)
                    continue
                except (TypeError, ValueError):
                    pass
            # Formato antigo → assume Kanto
            self._unlocked.add(_key(DEFAULT_REGION_ID, s))

        # ---- counters ----
        for key, val in raw_counters.items():
            s = str(key)
            parts = s.split(":")
            if len(parts) == 2:
                try:
                    int(parts[0])
                    self._counters[s] = int(val)
                    continue
                except (TypeError, ValueError):
                    pass
            self._counters[_ckey(DEFAULT_REGION_ID, s)] = int(val)

        # ---- unlocked_data ----
        for key, data in raw_udata.items():
            if not isinstance(data, dict):
                continue
            s = str(key)
            parts = s.split(":")
            if len(parts) == 2:
                try:
                    int(parts[0])
                    self._unlocked_data[s] = dict(data)
                    continue
                except (TypeError, ValueError):
                    pass
            # Antigo — descobre região do phase_id
            raw_phase = data.get("unlocked_phase")
            if raw_phase:
                r, _, _ = parse_phase_id(raw_phase)
            else:
                r = DEFAULT_REGION_ID
            nd = dict(data)
            nd["region_id"] = r
            nd["achievement_id"] = s
            if raw_phase:
                nd["unlocked_phase"] = normalize_phase_id(raw_phase)
            self._unlocked_data[_key(r, s)] = nd

    def save_to_player(self):
        if not hasattr(self.player, 'achievements'):
            self.player.achievements = {}
        self.player.achievements["unlocked"] = sorted(self._unlocked)
        self.player.achievements["counters"] = dict(self._counters)
        self.player.achievements["unlocked_data"] = {
            k: dict(v) for k, v in self._unlocked_data.items()
        }

    # ==================================================================
    # CONSULTAS
    # ==================================================================
    def is_unlocked(self, achievement_id: str,
                    region_id: Optional[int] = None) -> bool:
        """None -> checa em QUALQUER região. X -> só naquela."""
        if region_id is None:
            suffix = f":{achievement_id}"
            return any(k.endswith(suffix) for k in self._unlocked)
        return _key(int(region_id), achievement_id) in self._unlocked

    def get_counter(self, counter_id: str,
                    region_id: Optional[int] = None) -> int:
        rid = int(region_id) if region_id is not None else self._current_region
        return self._counters.get(_ckey(rid, counter_id), 0)

    def increment_counter(self, counter_id: str, amount: int = 1,
                          region_id: Optional[int] = None) -> int:
        rid = int(region_id) if region_id is not None else self._current_region
        k = _ckey(rid, counter_id)
        self._counters[k] = self._counters.get(k, 0) + amount
        self.save_to_player()
        return self._counters[k]

    def set_counter(self, counter_id: str, value: int,
                    region_id: Optional[int] = None):
        rid = int(region_id) if region_id is not None else self._current_region
        self._counters[_ckey(rid, counter_id)] = int(value)
        self.save_to_player()

    def get_unlocked_count(self, region_id: Optional[int] = None) -> int:
        rid = int(region_id) if region_id is not None else self._current_region
        prefix = f"{rid}:"
        return sum(1 for k in self._unlocked if k.startswith(prefix))

    def get_total_count(self) -> int:
        return len(ACHIEVEMENTS)

    def get_all_achievements(self, region_id: Optional[int] = None) -> List[Achievement]:
        rid = int(region_id) if region_id is not None else self._current_region
        out = []
        for ach_id, ach in ACHIEVEMENTS.items():
            k = _key(rid, ach_id)
            unlocked = k in self._unlocked
            udata = self._unlocked_data.get(k, {})
            out.append(Achievement(
                id=ach.id,
                title=ach.title,
                description=ach.description,
                rarity=ach.rarity,
                rewards=ach.rewards.copy(),
                region_id=rid,
                unlocked=unlocked,
                unlocked_at=udata.get("unlocked_at") if unlocked else None,
                unlocked_phase=udata.get("unlocked_phase") if unlocked else None,
            ))
        return out

    # ==================================================================
    # UNLOCK
    # ==================================================================
    def unlock(self, achievement_id: str,
               phase_id: Optional[str] = None) -> bool:
        """Região é extraída do phase_id (fallback: região atual)."""
        if phase_id:
            region_id, _, _ = parse_phase_id(phase_id)
            normalized = normalize_phase_id(phase_id)
        else:
            region_id = self._current_region
            normalized = make_phase_id(region_id, 1, 1)

        k = _key(region_id, achievement_id)
        if k in self._unlocked:
            return False

        ach = ACHIEVEMENTS.get(achievement_id)
        if not ach:
            return False

        unlocked_at = datetime.now().strftime("%d/%m/%Y as %H:%M")
        self._unlocked.add(k)
        self._unlocked_data[k] = {
            "region_id": region_id,
            "achievement_id": achievement_id,
            "unlocked_at": unlocked_at,
            "unlocked_phase": normalized,
        }
        self.save_to_player()
        self._apply_rewards(ach)
        self._show_achievement_toast(ach, region_id)
        print(f"[ACHIEVEMENT] {ach.title} (região {region_id}) em {unlocked_at}")
        return True

    # ==================================================================
    # REWARDS
    # ==================================================================
    def _apply_rewards(self, achievement: Achievement):
        r = achievement.rewards
        if "gold" in r:
            self.player.money += r["gold"]
        if "xp" in r:
            self.player.score += r["xp"]
        if "items" in r:
            for item_id, qty in r["items"].items():
                self.player.bag.add_item(item_id, qty)
        if "pokemon" in r:
            self._give_pokemon_reward(r["pokemon"])

    def _give_pokemon_reward(self, pokemon_id: int):
        from src.entities.pokemon import Pokemon
        new_pokemon = Pokemon(0, 0, pokemon_id, level=5, is_wild=False)
        if len(self.player.team) < 6:
            self.player.team.append(new_pokemon)
            new_pokemon.is_in_team = True
        else:
            self.player.pc_box.append(new_pokemon)
            new_pokemon.is_in_team = False
        self.player.caught_pokemon.add(pokemon_id)
        from src.ui.toast_renderer import toast_battle
        toast_battle(f"Você ganhou um {new_pokemon.name} como recompensa!",
                     duration=4.0, pokemon=new_pokemon, portrait="happy")

    def _show_achievement_toast(self, achievement: Achievement,
                                region_id: int = DEFAULT_REGION_ID):
        from src.data.pokedex import Pokedex
        rarity_name = achievement.rarity.display_name.upper()
        rewards_text = []
        if "pokemon" in achievement.rewards:
            rewards_text.append(Pokedex().get_name(achievement.rewards["pokemon"]))
        if "items" in achievement.rewards:
            for item_id, qty in achievement.rewards["items"].items():
                try:
                    nm = item_bag_catalog.get_item(item_id)["name"]
                    rewards_text.append(f"{qty}x {nm}")
                except Exception:
                    pass

        try:
            rname = RegionCatalog.get_name(region_id)
        except Exception:
            rname = f"Região {region_id}"

        base = f"{achievement.title} ({rarity_name}) — {rname}"
        msg = f"{base}\n+ {', '.join(rewards_text)}" if rewards_text else base
        toast_achievement(msg, duration=4.0)

    # ==================================================================
    # CHECK & UNLOCK
    # ==================================================================
    def check_and_unlock(self, achievement_id: str,
                         phase_id: Optional[str] = None) -> bool:
        if phase_id:
            region_id, _, _ = parse_phase_id(phase_id)
        else:
            region_id = self._current_region

        if self.is_unlocked(achievement_id, region_id=region_id):
            return False

        def c(counter_id: str) -> int:
            return self.get_counter(counter_id, region_id=region_id)

        hit = False
        a = achievement_id

        if a == "first_capture":                     hit = c("capture_count") >= 1
        elif a == "capture_10":                      hit = c("capture_count") >= 10
        elif a == "capture_50":                      hit = c("capture_count") >= 50
        elif a == "first_badge":                     hit = c("badge_count") >= 1
        elif a == "all_badges":                      hit = c("badge_count") >= 8
        elif a == "first_shiny_capture":             hit = c("shiny_capture_count") >= 1

        elif a == "heal_5":                          hit = c("heal_count") >= 5
        elif a == "heal_100":                        hit = c("heal_count") >= 100
        elif a == "first_burn_heal":                 hit = c("burn_heal_count") >= 1
        elif a == "burn_heal_10":                    hit = c("burn_heal_count") >= 10
        elif a == "first_freeze_heal":               hit = c("freeze_heal_count") >= 1
        elif a == "freeze_heal_10":                  hit = c("freeze_heal_count") >= 10

        elif a == "perfect_phase":                   hit = c("perfect_phase_count") >= 1
        elif a == "boss_defeated":                   hit = c("boss_defeated_count") >= 1

        elif a == "first_weather_change":            hit = c("weather_change_count") >= 1
        elif a == "weather_change_50":               hit = c("weather_change_count") >= 50
        elif a == "weather_change_100":              hit = c("weather_change_count") >= 100
        elif a == "first_weather_boosted_attack":    hit = c("weather_boosted_attack_count") >= 1

        elif a == "rare_candy_3":                    hit = c("rare_candy_count") >= 3

        elif a == "first_evolution":                 hit = c("evolution_count") >= 1
        elif a == "evolution_10":                    hit = c("evolution_count") >= 10
        elif a == "evolution_50":                    hit = c("evolution_count") >= 50

        elif a == "first_level_evolution":           hit = c("level_evolution_count") >= 1
        elif a == "level_evolution_50":              hit = c("level_evolution_count") >= 50

        elif a == "max_level_reached":
            for p in self.player.team:
                if getattr(p, 'level', 0) >= 100:
                    hit = True; break
            if not hit:
                for data in self.player.pc_box:
                    if data.get("level", 0) >= 100:
                        hit = True; break

        elif a == "first_stone_evolution":           hit = c("stone_evolution_count") >= 1
        elif a == "stone_evolution_5":               hit = c("stone_evolution_count") >= 5
        elif a == "stone_evolution_20":              hit = c("stone_evolution_count") >= 20

        elif a == "max_happiness":
            for p in self.player.team:
                try:
                    if p.get_happiness() >= 255:
                        hit = True; break
                except Exception:
                    pass

        elif a == "full_team_max_happiness":
            if self.player.team and all(
                getattr(p, 'get_happiness', lambda: 0)() >= 255
                for p in self.player.team
            ):
                hit = True

        elif a == "first_happiness_evolution":       hit = c("happiness_evolution_count") >= 1
        elif a == "happiness_evolution_3":           hit = c("happiness_evolution_count") >= 3
        elif a == "happiness_evolution_10":          hit = c("happiness_evolution_count") >= 10
        elif a == "friendball_capture_5":            hit = c("friendball_capture_count") >= 5

        elif a == "first_weather_evolution":         hit = c("weather_evolution_count") >= 1
        elif a == "weather_evolution_5":             hit = c("weather_evolution_count") >= 5

        elif a == "first_evolution_blocked":         hit = c("evolution_blocked_count") >= 1
        elif a == "evolution_blocked_10":            hit = c("evolution_blocked_count") >= 10

        elif a == "first_antidote":                  hit = c("antidote_count") >= 1
        elif a == "antidote_100":                    hit = c("antidote_count") >= 100
        elif a == "first_awake":                     hit = c("awake_count") >= 1
        elif a == "awake_100":                       hit = c("awake_count") >= 100
        elif a == "first_paralyze_heal":             hit = c("paralyze_heal_count") >= 1
        elif a == "paralyze_heal_100":               hit = c("paralyze_heal_count") >= 100
        elif a == "first_revive":                    hit = c("revive_count") >= 1
        elif a == "revive_25":                       hit = c("revive_count") >= 25

        elif a == "first_move_taught":               hit = c("move_taught_count") >= 1
        elif a == "move_taught_10":                  hit = c("move_taught_count") >= 10

        elif a == "battle_item_use_10":              hit = c("battle_item_use_count") >= 10
        elif a == "battle_item_replace":             hit = c("battle_item_replace_count") >= 1
        elif a == "accuracy_buff_miss":              hit = c("accuracy_buff_miss_count") >= 1
        elif a == "first_escaperope_use":            hit = c("escaperope_use_count") >= 1
        elif a == "escaperope_last_stand":           hit = c("escaperope_last_stand_count") >= 10

        elif a == "first_incubator_revive":          hit = c("incubator_revive_count") >= 1
        elif a == "buy_second_incubator":            hit = c("second_incubator_bought") >= 1
        elif a == "first_incubator_upgrade":         hit = c("incubator_upgrade_count") >= 1

        elif a == "first_trade":                     hit = c("trade_count") >= 1
        elif a == "trade_10":                        hit = c("trade_count") >= 10
        elif a == "first_trade_evolution":           hit = c("trade_evolution_count") >= 1

        elif a == "first_berry_consumed":            hit = c("berry_consumed_count") >= 1
        elif a == "capture_with_item":               hit = c("capture_with_item_count") >= 1

        if hit:
            return self.unlock(achievement_id, phase_id)
        return False

    def check_all_counters(self, phase_id: Optional[str] = None):
        for ach_id in ACHIEVEMENTS.keys():
            self.check_and_unlock(ach_id, phase_id)

    # ==================================================================
    # PROGRESS
    # ==================================================================
    def get_progress(self, achievement_id: str,
                     region_id: Optional[int] = None) -> tuple:
        rid = int(region_id) if region_id is not None else self._current_region

        progress_map = {
            "first_capture": ("capture_count", 1),
            "capture_10": ("capture_count", 10),
            "capture_50": ("capture_count", 50),
            "first_badge": ("badge_count", 1),
            "all_badges": ("badge_count", 8),
            "first_shiny_capture": ("shiny_capture_count", 1),

            "heal_5": ("heal_count", 5),
            "heal_100": ("heal_count", 100),

            "first_burn_heal": ("burn_heal_count", 1),
            "burn_heal_10": ("burn_heal_count", 10),
            "first_freeze_heal": ("freeze_heal_count", 1),
            "freeze_heal_10": ("freeze_heal_count", 10),

            "perfect_phase": ("perfect_phase_count", 1),
            "boss_defeated": ("boss_defeated_count", 1),

            "first_weather_change": ("weather_change_count", 1),
            "weather_change_50": ("weather_change_count", 50),
            "weather_change_100": ("weather_change_count", 100),
            "first_weather_boosted_attack": ("weather_boosted_attack_count", 1),

            "rare_candy_3": ("rare_candy_count", 3),

            "first_evolution": ("evolution_count", 1),
            "evolution_10": ("evolution_count", 10),
            "evolution_50": ("evolution_count", 50),

            "first_level_evolution": ("level_evolution_count", 1),
            "level_evolution_50": ("level_evolution_count", 50),
            "max_level_reached": ("max_level_check", 1),

            "first_stone_evolution": ("stone_evolution_count", 1),
            "stone_evolution_5": ("stone_evolution_count", 5),
            "stone_evolution_20": ("stone_evolution_count", 20),

            "max_happiness": ("max_happiness_check", 1),
            "full_team_max_happiness": ("full_team_max_happiness_check", 1),
            "first_happiness_evolution": ("happiness_evolution_count", 1),
            "happiness_evolution_3": ("happiness_evolution_count", 3),
            "happiness_evolution_10": ("happiness_evolution_count", 10),
            "friendball_capture_5": ("friendball_capture_count", 5),

            "first_weather_evolution": ("weather_evolution_count", 1),
            "weather_evolution_5": ("weather_evolution_count", 5),

            "first_evolution_blocked": ("evolution_blocked_count", 1),
            "evolution_blocked_10": ("evolution_blocked_count", 10),

            "first_antidote": ("antidote_count", 1),
            "antidote_100": ("antidote_count", 100),
            "first_awake": ("awake_count", 1),
            "awake_100": ("awake_count", 100),
            "first_paralyze_heal": ("paralyze_heal_count", 1),
            "paralyze_heal_100": ("paralyze_heal_count", 100),
            "first_revive": ("revive_count", 1),
            "revive_25": ("revive_count", 25),

            "first_move_taught": ("move_taught_count", 1),
            "move_taught_10": ("move_taught_count", 10),

            "battle_item_use_10": ("battle_item_use_count", 10),
            "battle_item_replace": ("battle_item_replace_count", 1),
            "accuracy_buff_miss": ("accuracy_buff_miss_count", 1),
            "first_escaperope_use": ("escaperope_use_count", 1),
            "escaperope_last_stand": ("escaperope_last_stand_count", 10),

            "first_incubator_revive": ("incubator_revive_count", 1),
            "buy_second_incubator": ("second_incubator_bought", 1),
            "first_incubator_upgrade": ("incubator_upgrade_count", 1),

            "first_trade": ("trade_count", 1),
            "trade_10": ("trade_count", 10),
            "first_trade_evolution": ("trade_evolution_count", 1),

            "first_berry_consumed": ("berry_consumed_count", 1),
            "capture_with_item": ("capture_with_item_count", 1),
        }

        if achievement_id in progress_map:
            cid, req = progress_map[achievement_id]
            return (self.get_counter(cid, region_id=rid), req)
        return (0, 1)