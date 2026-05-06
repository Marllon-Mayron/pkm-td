# src/battle/attack_strategy.py

from enum import Enum
from typing import Optional, List, TYPE_CHECKING

if TYPE_CHECKING:
    from src.entities.pokemon import Pokemon


class PriorityType(Enum):
    """Tipos de prioridade de ataque"""
    FASTEST = "fastest"  # Focar o mais rápido
    SLOWEST = "slowest"  # Focar o mais lento
    HOLDING_ITEM = "holding_item"  # Focar quem está segurando item
    LOWEST_HP = "lowest_hp"  # Focar com menos vida
    HIGHEST_HP = "highest_hp"  # Focar com mais vida
    HIGHEST_LEVEL = "highest_level"  # Focar level altos
    LOWEST_LEVEL = "lowest_level"  # Focar level baixos
    AGGRESSIVE = "aggressive"  # Focar agressivos
    NON_AGGRESSIVE = "non_aggressive"  # Focar não agressivos
    BOSS = "boss"  # Focar boss


class AttackPriority:
    """Gerencia a prioridade de ataque do Pokémon"""

    # Mapeamento de prioridade para função de ordenação
    _priority_handlers = {}

    def __init__(self, pokemon: 'Pokemon'):
        self.pokemon = pokemon
        self.priority_type = PriorityType.FASTEST  # Padrão: focar o mais rápido

    def set_priority(self, priority_type: PriorityType):
        """Define a prioridade de ataque"""
        self.priority_type = priority_type
        print(f"[ATTACK_PRIORITY] {self.pokemon.name} agora foca em: {priority_type.value}")

    def get_priority_name(self) -> str:
        """Retorna o nome da prioridade atual em português"""
        priority_names = {
            PriorityType.FASTEST: "Mais Rápido",
            PriorityType.SLOWEST: "Mais Lento",
            PriorityType.HOLDING_ITEM: "Segurando Item",
            PriorityType.LOWEST_HP: "Menos Vida",
            PriorityType.HIGHEST_HP: "Mais Vida",
            PriorityType.HIGHEST_LEVEL: "Level Alto",
            PriorityType.LOWEST_LEVEL: "Level Baixo",
            PriorityType.AGGRESSIVE: "Agressivo",
            PriorityType.NON_AGGRESSIVE: "Não Agressivo",
            PriorityType.BOSS: "Boss"
        }
        return priority_names.get(self.priority_type, "Mais Rápido")

    def sort_targets(self, targets: List['Pokemon']) -> List['Pokemon']:
        """
        Ordena a lista de alvos baseado na prioridade atual.
        Retorna a lista ordenada (o primeiro é o mais prioritário).
        """
        if not targets:
            return targets

        # Obtém a função de ordenação para a prioridade atual
        handler = self._get_priority_handler(self.priority_type)
        if handler:
            return handler(targets)

        return targets

    def _get_priority_handler(self, priority_type: PriorityType):
        """Retorna a função de ordenação para a prioridade"""
        handlers = {
            PriorityType.FASTEST: self._sort_by_speed_desc,
            PriorityType.SLOWEST: self._sort_by_speed_asc,
            PriorityType.HOLDING_ITEM: self._sort_by_holding_item,
            PriorityType.LOWEST_HP: self._sort_by_hp_asc,
            PriorityType.HIGHEST_HP: self._sort_by_hp_desc,
            PriorityType.HIGHEST_LEVEL: self._sort_by_level_desc,
            PriorityType.LOWEST_LEVEL: self._sort_by_level_asc,
            PriorityType.AGGRESSIVE: self._sort_by_aggressive,
            PriorityType.NON_AGGRESSIVE: self._sort_by_non_aggressive,
            PriorityType.BOSS: self._sort_by_boss,
        }
        return handlers.get(priority_type)

    # ===== MÉTODOS DE ORDENAÇÃO =====

    def _sort_by_speed_desc(self, targets: List['Pokemon']) -> List['Pokemon']:
        """Ordena por velocidade (mais rápido primeiro)"""
        return sorted(targets, key=lambda t: t.speed_stat, reverse=True)

    def _sort_by_speed_asc(self, targets: List['Pokemon']) -> List['Pokemon']:
        """Ordena por velocidade (mais lento primeiro)"""
        return sorted(targets, key=lambda t: t.speed_stat)

    def _sort_by_holding_item(self, targets: List['Pokemon']) -> List['Pokemon']:
        """Ordena por quem está segurando item (prioriza quem tem item)"""
        return sorted(targets, key=lambda t: 0 if t.is_carrying else 1)

    def _sort_by_hp_asc(self, targets: List['Pokemon']) -> List['Pokemon']:
        """Ordena por HP (menos vida primeiro)"""
        return sorted(targets, key=lambda t: t.current_hp / t.max_hp if t.max_hp > 0 else 1.0)

    def _sort_by_hp_desc(self, targets: List['Pokemon']) -> List['Pokemon']:
        """Ordena por HP (mais vida primeiro)"""
        return sorted(targets, key=lambda t: t.current_hp / t.max_hp if t.max_hp > 0 else 0, reverse=True)

    def _sort_by_level_desc(self, targets: List['Pokemon']) -> List['Pokemon']:
        """Ordena por nível (mais alto primeiro)"""
        return sorted(targets, key=lambda t: t.level, reverse=True)

    def _sort_by_level_asc(self, targets: List['Pokemon']) -> List['Pokemon']:
        """Ordena por nível (mais baixo primeiro)"""
        return sorted(targets, key=lambda t: t.level)

    def _sort_by_aggressive(self, targets: List['Pokemon']) -> List['Pokemon']:
        """Ordena por agressividade (mais agressivo primeiro)"""

        def get_aggressiveness(target):
            # Boss são mais agressivos
            if target.is_boss:
                return 3
            # Attack pattern agressivo
            if hasattr(target, 'attack_pattern') and target.attack_pattern:
                from src.battle.attack_pattern import AttackPattern
                if target.attack_pattern == AttackPattern.AGGRESSIVE:
                    return 2
                if target.attack_pattern == AttackPattern.VICIOUS:
                    return 2
                if target.attack_pattern == AttackPattern.VICIOUS_SELECTIVE:
                    return 1
            return 0

        return sorted(targets, key=get_aggressiveness, reverse=True)

    def _sort_by_non_aggressive(self, targets: List['Pokemon']) -> List['Pokemon']:
        """Ordena por não agressividade (menos agressivo primeiro)"""

        def get_non_aggressiveness(target):
            # Passivos primeiro
            if hasattr(target, 'attack_pattern') and target.attack_pattern:
                from src.battle.attack_pattern import AttackPattern
                if target.attack_pattern == AttackPattern.PASSIVE:
                    return 2
                if target.attack_pattern == AttackPattern.RANDOM:
                    return 1
            return 0

        return sorted(targets, key=get_non_aggressiveness, reverse=True)

    def _sort_by_boss(self, targets: List['Pokemon']) -> List['Pokemon']:
        """Ordena por boss (boss primeiro)"""
        return sorted(targets, key=lambda t: 0 if t.is_boss else 1)