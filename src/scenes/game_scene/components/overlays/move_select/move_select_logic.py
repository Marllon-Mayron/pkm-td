# src/scenes/game_scene/components/overlays/move_select_logic.py
"""
Lógica do overlay MoveSelect — estado + ações.
Não desenha nada. A cena lê daqui.
"""
from src.battle.attack_strategy import PriorityType


class MoveSelectLogic:
    # =============================================================
    # Listas fixas
    # =============================================================
    PRIORITY_OPTIONS = [
        PriorityType.FASTEST,
        PriorityType.SLOWEST,
        PriorityType.HOLDING_ITEM,
        PriorityType.LOWEST_HP,
        PriorityType.HIGHEST_HP,
        PriorityType.HIGHEST_LEVEL,
        PriorityType.LOWEST_LEVEL,
        PriorityType.AGGRESSIVE,
        PriorityType.NON_AGGRESSIVE,
        PriorityType.BOSS,
    ]

    PRIORITY_NAMES = {
        PriorityType.FASTEST:         "Mais Rapido",
        PriorityType.SLOWEST:         "Mais Lento",
        PriorityType.HOLDING_ITEM:    "Segurando Item",
        PriorityType.LOWEST_HP:       "Menos Vida",
        PriorityType.HIGHEST_HP:      "Mais Vida",
        PriorityType.HIGHEST_LEVEL:   "Level Alto",
        PriorityType.LOWEST_LEVEL:    "Level Baixo",
        PriorityType.AGGRESSIVE:      "Agressivo",
        PriorityType.NON_AGGRESSIVE:  "Nao Agressivo",
        PriorityType.BOSS:            "Boss",
    }

    PRIORITY_DESCRIPTIONS = {
        PriorityType.FASTEST:         "Ataca primeiro os mais rapidos",
        PriorityType.SLOWEST:         "Ataca primeiro os mais lentos",
        PriorityType.HOLDING_ITEM:    "Foca em quem carrega item",
        PriorityType.LOWEST_HP:       "Foca em quem tem menos vida",
        PriorityType.HIGHEST_HP:      "Foca em quem tem mais vida",
        PriorityType.HIGHEST_LEVEL:   "Foca no de nivel mais alto",
        PriorityType.LOWEST_LEVEL:    "Foca no de nivel mais baixo",
        PriorityType.AGGRESSIVE:      "Foca em agressivos primeiro",
        PriorityType.NON_AGGRESSIVE:  "Foca em passivos primeiro",
        PriorityType.BOSS:            "Foca no Boss sempre",
    }

    TYPE_COLORS = {
        "normal":   "#A8A878", "fire":     "#F08030", "water":    "#6890F0",
        "electric": "#F8D030", "grass":    "#78C850", "ice":      "#98D8D8",
        "fighting": "#C03028", "poison":   "#A040A0", "ground":   "#E0C068",
        "flying":   "#A890F0", "psychic":  "#F85888", "bug":      "#A8B820",
        "rock":     "#B8A038", "ghost":    "#705898", "dragon":   "#7038F8",
        "dark":     "#705848", "steel":    "#B8B8D0", "fairy":    "#EE99AC",
    }

    # =============================================================
    def __init__(self, game, pokemon):
        self.game = game
        self.pokemon = pokemon

        # Índices selecionados
        self.selected_move_index = getattr(pokemon, "current_move_index", 0)
        self.selected_priority_index = self._get_initial_priority_index()

    # -----------------------------------------------------------------
    def _get_initial_priority_index(self):
        if not hasattr(self.pokemon, "attack_priority"):
            return 0
        current = self.pokemon.attack_priority.priority_type
        for i, p in enumerate(self.PRIORITY_OPTIONS):
            if p == current:
                return i
        return 0

    # =============================================================
    # Consultas
    # =============================================================
    def get_moves(self):
        return list(getattr(self.pokemon, "moves", []) or [])

    def get_priority_labels(self):
        return [self.PRIORITY_NAMES[p] for p in self.PRIORITY_OPTIONS]

    def get_move_description(self, move):
        """Tenta pegar descrição do move; fallback genérico."""
        try:
            from src.battle.effects.effect_factory import EffectFactory
            from src.data.move_data import MoveData

            name = getattr(move, "name", "")
            key = name.lower().replace(" ", "-").replace("'", "")

            effect = EffectFactory.create_effect(key)
            if effect and getattr(effect, "description", None):
                return effect.description

            config = EffectFactory.MOVE_EFFECTS.get(key)
            if config and config.get("description"):
                return config["description"]

            info = MoveData().get_move_info(name)
            if info and info.get("description"):
                desc = info["description"]
                if desc and not desc.startswith(f"Usa {name}"):
                    return desc
        except Exception as e:
            print(f"[MoveSelect] descrição: {e}")

        return "Um movimento que causa dano ao oponente."

    # =============================================================
    # Ações
    # =============================================================
    def on_move_selected(self, idx):
        self.selected_move_index = int(idx)

    def on_priority_selected(self, idx):
        self.selected_priority_index = int(idx)

    def move_up(self):
        if self.PRIORITY_OPTIONS:
            n = len(self.PRIORITY_OPTIONS)
            self.selected_priority_index = (self.selected_priority_index - 1) % n

    def move_down(self):
        if self.PRIORITY_OPTIONS:
            n = len(self.PRIORITY_OPTIONS)
            self.selected_priority_index = (self.selected_priority_index + 1) % n

    def move_left(self):
        moves = self.get_moves()
        if moves:
            n = len(moves)
            self.selected_move_index = (self.selected_move_index - 1) % n

    def move_right(self):
        moves = self.get_moves()
        if moves:
            n = len(moves)
            self.selected_move_index = (self.selected_move_index + 1) % n

    # -----------------------------------------------------------------
    def confirm_selection(self):
        """Aplica seleção no pokemon e salva."""
        moves = self.get_moves()
        if moves and 0 <= self.selected_move_index < len(moves):
            self.pokemon.current_move_index = self.selected_move_index
            chosen = moves[self.selected_move_index]
            print(f"[MOVE_SELECT] {self.pokemon.name} usará "
                  f"{getattr(chosen, 'name', '?')}")

        if hasattr(self.pokemon, "attack_priority"):
            if 0 <= self.selected_priority_index < len(self.PRIORITY_OPTIONS):
                p = self.PRIORITY_OPTIONS[self.selected_priority_index]
                self.pokemon.attack_priority.set_priority(p)
                print(f"[PRIORITY_SELECT] {self.pokemon.name} → {p.value}")

        try:
            if hasattr(self.game, "player") and self.game.player:
                self.game.player.auto_save()
        except Exception as e:
            print(f"[MoveSelect] auto_save: {e}")

    def cancel_selection(self):
        print(f"[MOVE_SELECT] {self.pokemon.name}: seleção cancelada")