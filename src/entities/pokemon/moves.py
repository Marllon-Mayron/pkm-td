# src/entities/pokemon/moves.py
from typing import List, Dict, Optional, Set
from src.entities.move import Move


class PokemonMoves:
    """Gerencia moves e aprendizado do Pokémon"""

    def __init__(self, pokemon):
        self.pokemon = pokemon

    def initialize_moves(self):
        """Inicializa os moves do Pokémon baseado no nível atual"""
        all_moves_learned = self.pokemon.move_data.get_moves_at_level(self.pokemon.id, self.pokemon.level)
        initial_moves = all_moves_learned[:4]

        for move_name in initial_moves:
            move_info = self.pokemon.move_data.get_move_info(move_name)
            if move_info:
                self.pokemon.moves.append(Move(move_name, move_info))

        if not self.pokemon.moves:
            fallback_move = {
                "name": "tackle",
                "type": "normal",
                "power": 40,
                "accuracy": 100,
                "pp": 35,
                "category": "physical",
                "description": "Um ataque físico com o corpo."
            }
            self.pokemon.moves.append(Move("tackle", fallback_move))

        print(f"[INIT] {self.pokemon.name} Lv.{self.pokemon.level} aprendeu: {[m.name for m in self.pokemon.moves]}")

    def get_current_move(self) -> Optional[Move]:
        """Retorna o move atual do Pokémon"""
        if self.pokemon.moves and 0 <= self.pokemon.current_move_index < len(self.pokemon.moves):
            return self.pokemon.moves[self.pokemon.current_move_index]
        return None

    def learn_move(self, move_name: str) -> bool:
        """Tenta aprender um novo move"""
        move_info = self.pokemon.move_data.get_move_info(move_name)
        if not move_info:
            return False

        new_move = Move(move_name, move_info)

        if len(self.pokemon.moves) < 4:
            self.pokemon.moves.append(new_move)
            print(f"[MOVES] {self.pokemon.name} aprendeu {move_name}!")
            return True

        if self.pokemon.game_scene:
            self.pokemon.game_scene.open_move_learn_overlay(self.pokemon, move_name)
            return True

        return False

    def forget_move(self, index: int) -> bool:
        """Esquece um move pelo índice (0-3)"""
        if 0 <= index < len(self.pokemon.moves):
            forgotten = self.pokemon.moves.pop(index)
            print(f"[MOVES] {self.pokemon.name} esqueceu {forgotten.name}!")
            return True
        return False

    def replace_move(self, index: int, new_move_name: str) -> bool:
        """Substitui um move existente por um novo"""
        if not 0 <= index < len(self.pokemon.moves):
            return False

        move_info = self.pokemon.move_data.get_move_info(new_move_name)
        if not move_info:
            return False

        old_name = self.pokemon.moves[index].name
        self.pokemon.moves[index] = Move(new_move_name, move_info)
        print(f"[MOVES] {self.pokemon.name} esqueceu {old_name} e aprendeu {new_move_name}!")
        return True

    def get_available_moves(self) -> List[str]:
        """Retorna todos os moves que o Pokémon pode aprender (até o nível atual)"""
        return self.pokemon.move_data.get_moves_at_level(self.pokemon.id, self.pokemon.level)

    def get_new_moves_at_level(self, level: int) -> List[str]:
        """Retorna moves que o Pokémon aprende EXATAMENTE neste nível"""
        learnset = self.pokemon.move_data.get_pokemon_learnset(self.pokemon.id)
        known_moves = set(move.name for move in self.pokemon.moves)

        new_moves = []
        for move_info in learnset:
            if move_info.get("level", 0) == level:
                move_name = move_info.get("move", "")
                if move_name and move_name not in known_moves:
                    new_moves.append(move_name)

        return new_moves

    def check_new_moves_on_level_up(self, old_level: int):
        """Verifica se o Pokémon aprende novos moves ao subir de nível"""
        learnset = self.pokemon.move_data.get_pokemon_learnset(self.pokemon.id)
        current_moves = set(move.name for move in self.pokemon.moves)

        new_moves = []
        for move_info in learnset:
            level = move_info.get("level", 0)
            move_name = move_info.get("move", "")

            if level == self.pokemon.level and move_name not in current_moves:
                new_moves.append(move_name)

        learned_moves = []
        pending_moves = []

        for move_name in new_moves:
            learned = self.learn_move(move_name)
            if learned:
                learned_moves.append(move_name)
            else:
                pending_moves.append(move_name)

        return learned_moves, pending_moves

    def _learn_move_without_replacement(self, move_name: str) -> bool:
        """Aprende um novo move mantendo os existentes"""
        move_info = self.pokemon.move_data.get_move_info(move_name)
        if not move_info:
            return False

        new_move = Move(move_name, move_info)

        if len(self.pokemon.moves) < 4:
            self.pokemon.moves.append(new_move)
            print(f"[MOVES] {self.pokemon.name} aprendeu {move_name}!")
            return True

        print(f"[MOVES] {self.pokemon.name} quer aprender {move_name}, mas já tem 4 moves!")
        return False

    def learn_move_with_selection(self, move_name: str, slot_index: int) -> bool:
        """Aprende um novo move substituindo o move no slot_index"""
        move_info = self.pokemon.move_data.get_move_info(move_name)
        if not move_info:
            return False

        if 0 <= slot_index < len(self.pokemon.moves):
            old_name = self.pokemon.moves[slot_index].name
            self.pokemon.moves[slot_index] = Move(move_name, move_info)
            print(f"[MOVES] {self.pokemon.name} esqueceu {old_name} e aprendeu {move_name}!")
            return True

        return False