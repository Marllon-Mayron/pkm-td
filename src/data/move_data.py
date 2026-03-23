# src/data/move_data.py
import json
import os
from pathlib import Path
from typing import Dict, List, Optional, Any


class MoveData:
    """Gerencia dados dos moves e aprendizado por nível"""

    _instance = None
    _moves_data: Dict[int, Dict] = {}
    _pokemon_moves: Dict[int, List[Dict]] = {}  # ID -> lista de moves aprendidos por nível

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialized = False
        return cls._instance

    def __init__(self):
        if self._initialized:
            return
        self._initialized = True
        self._load_moves_data()

    def _find_data_path(self, filename: str) -> Optional[Path]:
        """Encontra o caminho do arquivo de dados de forma robusta"""
        # Caminho relativo ao arquivo atual
        current_dir = Path(__file__).parent
        base_dir = current_dir.parent.parent  # src/

        # Possíveis caminhos
        possible_paths = [
            base_dir / "data" / "scripts" / filename,
            current_dir / "scripts" / filename,
            Path(__file__).parent.parent.parent / "res" / "json" / filename,
            Path.cwd() / "src" / "data" / "scripts" / filename,
            Path.cwd() / "res" / "json" / filename,
        ]

        for path in possible_paths:
            if path.exists():
                return path

        return None

    def _load_moves_data(self):
        """Carrega os dados dos moves dos JSONs"""
        try:
            # Carrega dados dos moves da Gen 1
            moves_path = self._find_data_path("pokemon_moves_gen1_compact.json")
            if moves_path:
                with open(moves_path, 'r', encoding='utf-8') as f:
                    self._pokemon_moves = json.load(f)
                print(f"[MoveData] Carregados dados de moves para {len(self._pokemon_moves)} Pokémon")
            else:
                print("[MoveData] AVISO: Arquivo pokemon_moves_gen1_compact.json não encontrado")

            # TODO: Carregar dados detalhados dos moves quando disponível
            # Por enquanto, usamos apenas os dados do JSON compacto

        except Exception as e:
            print(f"[MoveData] Erro ao carregar dados de moves: {e}")
            self._pokemon_moves = {}

    def get_pokemon_learnset(self, pokemon_id: int) -> List[Dict]:
        """
        Retorna a lista de moves que o Pokémon aprende por level up

        Returns:
            Lista de dicionários com 'level' e 'move'
        """
        pokemon_id_str = str(pokemon_id)
        if pokemon_id_str in self._pokemon_moves:
            pokemon_data = self._pokemon_moves[pokemon_id_str]
            return pokemon_data.get("level_up_moves", [])
        return []

    def get_moves_at_level(self, pokemon_id: int, level: int) -> List[str]:
        """
        Retorna lista de nomes dos moves que o Pokémon aprendeu até o nível dado
        """
        learnset = self.get_pokemon_learnset(pokemon_id)
        learned_moves = []
        seen_moves = set()  # Evita duplicatas (alguns JSONs têm moves duplicados)

        for move_info in learnset:
            if move_info.get("level", 0) <= level:
                move_name = move_info.get("move", "")
                if move_name and move_name not in seen_moves:
                    seen_moves.add(move_name)
                    learned_moves.append(move_name)

        return learned_moves

    def get_initial_moves(self, pokemon_id: int, level: int) -> List[str]:
        """
        Retorna os 4 primeiros moves disponíveis para o Pokémon no nível atual
        (ou menos se não houver 4)
        """
        all_moves = self.get_moves_at_level(pokemon_id, level)
        # Pega os 4 primeiros moves (ou todos se tiver menos)
        return all_moves[:4]

    def get_move_name(self, move_id: int) -> str:
        """Retorna o nome do move pelo ID (placeholder até ter dados completos)"""
        # TODO: Implementar quando tivermos o arquivo completo de moves
        return f"move_{move_id}"

    def get_move_info(self, move_name: str) -> Optional[Dict]:
        """Retorna informações detalhadas de um move (placeholder)"""
        # TODO: Implementar quando tivermos dados detalhados dos moves
        return {
            "name": move_name,
            "type": "normal",  # Placeholder
            "power": 40,  # Placeholder
            "accuracy": 100,  # Placeholder
            "pp": 35,  # Placeholder
            "category": "physical",  # Placeholder
            "description": f"Usa {move_name}."
        }