# src/scenes/game_scene/components/overlays/move_learn_logic.py
"""
Lógica do overlay MoveLearn — estado + ações.
Não desenha nada. A cena lê daqui.
"""
from src.data.move_data import MoveData
from src.entities.move import Move


class MoveLearnLogic:
    TYPE_COLORS = {
        "normal":   "#A8A878", "fire":     "#F08030", "water":    "#6890F0",
        "electric": "#F8D030", "grass":    "#78C850", "ice":      "#98D8D8",
        "fighting": "#C03028", "poison":   "#A040A0", "ground":   "#E0C068",
        "flying":   "#A890F0", "psychic":  "#F85888", "bug":      "#A8B820",
        "rock":     "#B8A038", "ghost":    "#705898", "dragon":   "#7038F8",
        "dark":     "#705848", "steel":    "#B8B8D0", "fairy":    "#EE99AC",
    }

    # =================================================================
    def __init__(self, game, pokemon, new_move_name):
        self.game = game
        self.pokemon = pokemon
        self.new_move_name = new_move_name
        self.new_move = None
        self.selected_index = -1   # -1 = não aprender; 0..3 = substitui

        self._load_new_move()

    def _load_new_move(self):
        info = MoveData().get_move_info(self.new_move_name)
        if info:
            self.new_move = Move(self.new_move_name, info)
            print(f"[MoveLearn] Novo move: {self.new_move.name} "
                  f"({self.new_move.current_pp}/{self.new_move.max_pp} PP)")

    # =================================================================
    # Consultas
    # =================================================================
    def get_moves(self):
        return list(getattr(self.pokemon, "moves", []) or [])

    def get_move_description(self, move):
        """Descrição do move. Aceita objeto Move OU string."""
        try:
            from src.battle.effects.effect_factory import EffectFactory

            if isinstance(move, str):
                name = move
            else:
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
            print(f"[MoveLearn] descrição: {e}")

        return "Um movimento que causa dano ao oponente."

    # =================================================================
    # Ações
    # =================================================================
    def on_move_selected(self, idx):
        self.selected_index = int(idx)

    def select_cancel(self):
        self.selected_index = -1

    def is_cancel_selected(self):
        return self.selected_index == -1

    def can_confirm(self):
        """Confirmar só faz sentido com um move escolhido."""
        return 0 <= self.selected_index < len(self.get_moves())

    # =================================================================
    def confirm_selection(self):
        if self.can_confirm():
            self.pokemon.replace_move(self.selected_index, self.new_move_name)
            print(f"[MoveLearn] {self.pokemon.name} esqueceu move "
                  f"#{self.selected_index} para aprender {self.new_move_name}")

        try:
            if hasattr(self.game, "player") and self.game.player:
                self.game.player.auto_save()
        except Exception as e:
            print(f"[MoveLearn] auto_save: {e}")

    def cancel_selection(self):
        print(f"[MoveLearn] {self.pokemon.name}: {self.new_move_name} "
              f"não foi aprendido")