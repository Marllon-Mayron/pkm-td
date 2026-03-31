# src/data/move_data.py

import json
import os
from pathlib import Path
from typing import Dict, List, Optional, Any


class MoveData:
    """Gerencia dados dos moves e aprendizado por nível"""

    _instance = None
    _moves_data: Dict[int, Dict] = {}  # Dados detalhados dos moves (por ID)
    _pokemon_learnset: Dict[int, List[Dict]] = {}  # ID -> lista de moves aprendidos por nível
    _pokemon_tm_hm: Dict[int, List[str]] = {}  # ID -> lista de TMs/HMs que o Pokémon pode aprender

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
        self._load_pokemon_learnset()
        self._load_pokemon_tm_hm()  # NOVO

    def _find_data_path(self, filename: str) -> Optional[Path]:
        """Encontra o caminho do arquivo de dados de forma robusta"""
        current_dir = Path(__file__).parent
        base_dir = current_dir.parent.parent  # src/

        possible_paths = [
            base_dir / "res" / "json" / filename,
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
        """Carrega os dados detalhados dos moves do JSON"""
        try:
            moves_path = self._find_data_path("pokemon_moves_gen1.json")
            if moves_path:
                with open(moves_path, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    for move_id, move_info in data.get("moves", {}).items():
                        self._moves_data[int(move_id)] = {
                            "name": move_info["name"],
                            "type": move_info["type"],
                            "power": move_info.get("power"),
                            "accuracy": move_info.get("accuracy"),
                            "pp": move_info["pp"],
                            "category": move_info["damage_class"],
                            "description": move_info["description"],
                            "effect": move_info["effect"],
                            "effect_chance": move_info.get("effect_chance"),
                            "is_status": move_info["is_status"],
                            "sound_name": move_info["name"].lower()
                        }
                print(f"[MoveData] Carregados dados de {len(self._moves_data)} moves")
            else:
                print("[MoveData] AVISO: Arquivo pokemon_moves_gen1.json não encontrado")

        except Exception as e:
            print(f"[MoveData] Erro ao carregar dados de moves: {e}")

    def _load_pokemon_learnset(self):
        """Carrega os learnsets (level-up) dos Pokémon do JSON"""
        try:
            learnset_path = self._find_data_path("pokemon_gen1_learnset.json")
            if learnset_path:
                with open(learnset_path, 'r', encoding='utf-8') as f:
                    data = json.load(f)

                    for pokemon_id_str, pokemon_info in data.get("pokemon", {}).items():
                        pokemon_id = int(pokemon_id_str)
                        self._pokemon_learnset[pokemon_id] = []

                        level_up_moves = pokemon_info.get("moves", {}).get("level_up", [])
                        for move in level_up_moves:
                            self._pokemon_learnset[pokemon_id].append({
                                "level": move["level"],
                                "move": move["name"],
                                "id": move.get("id", 0)
                            })

                        self._pokemon_learnset[pokemon_id].sort(key=lambda x: x["level"])

                print(f"[MoveData] Carregados learnsets para {len(self._pokemon_learnset)} Pokémon")
            else:
                print("[MoveData] AVISO: Arquivo pokemon_gen1_learnset.json não encontrado")

        except Exception as e:
            print(f"[MoveData] Erro ao carregar learnsets: {e}")

    def _load_pokemon_tm_hm(self):
        """Carrega os TMs/HMs que cada Pokémon pode aprender do JSON"""
        try:
            learnset_path = self._find_data_path("pokemon_gen1_learnset.json")
            if learnset_path:
                with open(learnset_path, 'r', encoding='utf-8') as f:
                    data = json.load(f)

                    for pokemon_id_str, pokemon_info in data.get("pokemon", {}).items():
                        pokemon_id = int(pokemon_id_str)
                        self._pokemon_tm_hm[pokemon_id] = []

                        tm_hm_moves = pokemon_info.get("moves", {}).get("tm_hm", [])
                        for move in tm_hm_moves:
                            move_name = move.get("name", "")
                            if move_name:
                                self._pokemon_tm_hm[pokemon_id].append(move_name)

                print(f"[MoveData] Carregados TMs/HMs para {len(self._pokemon_tm_hm)} Pokémon")
            else:
                print("[MoveData] AVISO: Arquivo pokemon_gen1_learnset.json não encontrado")

        except Exception as e:
            print(f"[MoveData] Erro ao carregar TMs/HMs: {e}")

    def get_pokemon_learnset(self, pokemon_id: int) -> List[Dict]:
        """Retorna a lista de moves que o Pokémon aprende por level up"""
        return self._pokemon_learnset.get(pokemon_id, [])

    def get_pokemon_tm_hm_moves(self, pokemon_id: int) -> List[str]:
        """Retorna a lista de TMs/HMs que o Pokémon pode aprender"""
        return self._pokemon_tm_hm.get(pokemon_id, [])

    def can_learn_move(self, pokemon_id: int, move_name: str) -> bool:
        """
        Verifica se um Pokémon pode aprender um move específico
        (via level up OU via TM/HM)

        Args:
            pokemon_id: ID do Pokémon
            move_name: Nome do move a ser verificado

        Returns:
            bool: True se o Pokémon pode aprender o move
        """
        move_name_lower = move_name.lower()

        # Verifica no learnset por level up
        for move_info in self._pokemon_learnset.get(pokemon_id, []):
            if move_info.get("move", "").lower() == move_name_lower:
                return True

        # Verifica nos TMs/HMs
        for tm_move in self._pokemon_tm_hm.get(pokemon_id, []):
            if tm_move.lower() == move_name_lower:
                return True

        return False

    def get_moves_at_level(self, pokemon_id: int, level: int) -> List[str]:
        """
        Retorna lista de nomes dos moves que o Pokémon aprendeu até o nível dado
        """
        learnset = self.get_pokemon_learnset(pokemon_id)
        learned_moves = []
        seen_moves = set()

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
        """
        all_moves = self.get_moves_at_level(pokemon_id, level)
        return all_moves[:4]

    def get_move_info(self, move_name: str) -> Optional[Dict]:
        """Retorna informações detalhadas de um move"""
        move_name_lower = move_name.lower()
        for move_id, move_info in self._moves_data.items():
            if move_info["name"].lower() == move_name_lower:
                return {
                    "name": move_info["name"],
                    "type": move_info["type"],
                    "power": move_info["power"] if move_info["power"] is not None else 0,
                    "accuracy": move_info["accuracy"] if move_info["accuracy"] is not None else 100,
                    "pp": move_info["pp"],
                    "category": move_info["category"],
                    "description": move_info["description"],
                    "effect": move_info["effect"],
                    "effect_chance": move_info.get("effect_chance"),
                    "is_status": move_info["is_status"],
                    "sound_name": move_info.get("sound_name", move_name_lower)
                }

        print(f"[MoveData] AVISO: Move '{move_name}' não encontrado, usando dados padrão")
        return {
            "name": move_name,
            "type": "normal",
            "power": 40,
            "accuracy": 100,
            "pp": 35,
            "category": "physical",
            "description": f"Usa {move_name}.",
            "effect": None,
            "effect_chance": None,
            "is_status": False,
            "sound_name": move_name_lower
        }

    def get_move_info_by_id(self, move_id: int) -> Optional[Dict]:
        """Retorna informações detalhadas de um move por ID"""
        move_info = self._moves_data.get(move_id)
        if move_info:
            return {
                "name": move_info["name"],
                "type": move_info["type"],
                "power": move_info["power"] if move_info["power"] is not None else 0,
                "accuracy": move_info["accuracy"] if move_info["accuracy"] is not None else 100,
                "pp": move_info["pp"],
                "category": move_info["category"],
                "description": move_info["description"],
                "effect": move_info["effect"],
                "effect_chance": move_info.get("effect_chance"),
                "is_status": move_info["is_status"],
                "sound_name": move_info.get("sound_name", move_info["name"].lower())
            }
        return None

    def get_move_name(self, move_id: int) -> str:
        """Retorna o nome do move pelo ID"""
        move_info = self._moves_data.get(move_id)
        return move_info["name"] if move_info else f"move_{move_id}"

    def get_move_sound_name(self, move_name: str) -> str:
        """Retorna o nome do arquivo de som para um move específico"""
        move_info = self.get_move_info(move_name)
        if move_info:
            sound_name = move_info.get("sound_name", move_name.lower())
            sound_name = sound_name.replace(" ", "").replace("-", "").replace("'", "")
            return sound_name
        return move_name.lower().replace(" ", "").replace("-", "").replace("'", "")

    def get_all_move_names(self) -> List[str]:
        """Retorna uma lista com todos os nomes de moves disponíveis"""
        return [move_info["name"] for move_info in self._moves_data.values()]

    def get_all_tm_hm_moves(self) -> List[str]:
        """Retorna uma lista com todos os nomes de moves que são TMs/HMs"""
        all_tm_moves = set()
        for tm_moves in self._pokemon_tm_hm.values():
            for move in tm_moves:
                all_tm_moves.add(move)
        return sorted(list(all_tm_moves))