# src/managers/achievement_manager.py

from typing import Dict, List, Optional, Set
from datetime import datetime
from src.data.achievement_data import Achievement, ACHIEVEMENTS, AchievementRarity
from src.ui.toast_renderer import toast_achievement


class AchievementManager:
    """Gerencia conquistas do jogador"""

    def __init__(self, player):
        self.player = player
        self._unlocked: Set[str] = set()
        self._counters: Dict[str, int] = {}
        self._unlocked_data: Dict[str, Dict] = {}  # Armazena data e fase de cada conquista

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
        """Retorna quantas conquistas foram desbloqueadas"""
        return len(self._unlocked)

    def get_total_count(self) -> int:
        """Retorna total de conquistas disponiveis"""
        return len(ACHIEVEMENTS)

    def is_unlocked(self, achievement_id: str) -> bool:
        """Verifica se uma conquista foi desbloqueada"""
        return achievement_id in self._unlocked

    def get_counter(self, counter_id: str) -> int:
        """Retorna o valor de um contador"""
        return self._counters.get(counter_id, 0)

    def increment_counter(self, counter_id: str, amount: int = 1) -> int:
        """Incrementa um contador e verifica conquistas"""
        new_value = self._counters.get(counter_id, 0) + amount
        self._counters[counter_id] = new_value
        self.save_to_player()
        return new_value

    def set_counter(self, counter_id: str, value: int):
        """Define um contador diretamente"""
        self._counters[counter_id] = value
        self.save_to_player()

    def unlock(self, achievement_id: str, phase_id: Optional[str] = None) -> bool:
        """
        Desbloqueia uma conquista
        """
        if achievement_id in self._unlocked:
            return False

        achievement = ACHIEVEMENTS.get(achievement_id)
        if not achievement:
            return False

        # Registra data/hora e fase
        now = datetime.now()
        unlocked_at = now.strftime("%d/%m/%Y as %H:%M")

        self._unlocked.add(achievement_id)
        self._unlocked_data[achievement_id] = {
            "unlocked_at": unlocked_at,
            "unlocked_phase": phase_id if phase_id else "Desconhecida"
        }

        # ===== SALVA IMEDIATAMENTE =====
        self.save_to_player()

        # Aplica recompensas
        self._apply_rewards(achievement)

        # Mostra toast
        self._show_achievement_toast(achievement)

        print(f"[ACHIEVEMENT] Desbloqueado: {achievement.title} em {unlocked_at} (Fase: {phase_id})")
        return True

    def _apply_rewards(self, achievement: Achievement):
        """Aplica as recompensas da conquista"""
        rewards = achievement.rewards

        if "gold" in rewards:
            self.player.money += rewards["gold"]
            print(f"[ACHIEVEMENT] +{rewards['gold']} ouro")

        if "xp" in rewards:
            for pokemon in self.player.team:
                pokemon.gain_xp(rewards["xp"])
            print(f"[ACHIEVEMENT] +{rewards['xp']} XP para o time")

    def _show_achievement_toast(self, achievement: Achievement):
        """Mostra toast de conquista desbloqueada"""
        rarity_name = achievement.rarity.display_name.upper()

        message = f"CONQUISTA DESBLOQUEADA! {achievement.title} ({rarity_name})"
        toast_achievement(message, duration=4.0)

    def check_and_unlock(self, achievement_id: str, phase_id: Optional[str] = None) -> bool:
        """
        Verifica se uma conquista pode ser desbloqueada e a desbloqueia
        Retorna True se foi desbloqueada
        """
        if self.is_unlocked(achievement_id):
            return False

        # Verifica condicoes especificas
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

        return False

    def check_all_counters(self, phase_id: Optional[str] = None):
        """Verifica todas as conquistas baseadas nos contadores atuais"""
        for ach_id in ACHIEVEMENTS.keys():
            self.check_and_unlock(ach_id, phase_id)

    def get_progress(self, achievement_id: str) -> tuple:
        """
        Retorna o progresso de uma conquista (atual, necessario)
        Retorna (0, 1) para conquistas sem contador
        """
        progress_map = {
            "first_capture": ("capture_count", 1),
            "heal_5": ("heal_count", 5),
            "first_badge": ("badge_count", 1),
            "capture_10": ("capture_count", 10),
            "heal_100": ("heal_count", 100),
            "capture_50": ("capture_count", 50),
            "perfect_phase": ("perfect_phase_count", 1),
            "boss_defeated": ("boss_defeated_count", 1),
        }

        if achievement_id in progress_map:
            counter_id, required = progress_map[achievement_id]
            current = self.get_counter(counter_id)
            return (current, required)

        return (0, 1)