# src/managers/evolution_manager.py

import json
import os
import sys
from pathlib import Path


class EvolutionManager:
    """Gerencia as evoluções dos Pokémon"""

    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialized = False
        return cls._instance

    def __init__(self):
        if self._initialized:
            return

        self._initialized = True
        self.evolutions = {}
        self._load_evolution_data()

    def _get_json_path(self):
        """Obtém o caminho correto para o arquivo JSON independente de onde o jogo é executado"""
        if getattr(sys, 'frozen', False):
            # Se for executado como executável
            root_dir = os.path.dirname(sys.executable)
        else:
            # Se for executado como script Python
            # Vai do diretório atual até a raiz do projeto
            current_file = Path(__file__).resolve()
            # src/managers/evolution_manager.py -> sobe 3 níveis até a raiz
            root_dir = current_file.parent.parent.parent

        json_path = root_dir / "src" / "data" / "scripts" / "pokemon_evolutions_gen1.json"
        return json_path

    def _load_evolution_data(self):
        """Carrega os dados de evolução do arquivo JSON"""
        try:
            json_path = self._get_json_path()

            if not json_path.exists():
                print(f"⚠️ Arquivo de evoluções não encontrado: {json_path}")
                print(f"   Diretório atual: {os.getcwd()}")
                print(f"   Caminho tentado: {json_path}")
                self._create_fallback_data()
                return

            with open(json_path, 'r', encoding='utf-8') as file:
                self.evolutions = json.load(file)

            print(f"✓ Carregados dados de evolução para {len(self.evolutions)} Pokémon")

        except Exception as e:
            print(f"✗ Erro ao carregar dados de evolução: {e}")
            self._create_fallback_data()

    def _create_fallback_data(self):
        """Cria dados de evolução básicos para fallback"""
        # Fallback para os starters pelo menos
        self.evolutions = {
            "1": {"lvlMin": 16, "EvolveTo": 2, "method": "level_up"},
            "2": {"lvlMin": 32, "EvolveTo": 3, "method": "level_up"},
            "3": {"lvlMin": "none", "EvolveTo": "none", "method": "none"},
            "4": {"lvlMin": 16, "EvolveTo": 5, "method": "level_up"},
            "5": {"lvlMin": 36, "EvolveTo": 6, "method": "level_up"},
            "6": {"lvlMin": "none", "EvolveTo": "none", "method": "none"},
            "7": {"lvlMin": 16, "EvolveTo": 8, "method": "level_up"},
            "8": {"lvlMin": 36, "EvolveTo": 9, "method": "level_up"},
            "9": {"lvlMin": "none", "EvolveTo": "none", "method": "none"},
        }
        print("⚠️ Usando dados de evolução de fallback (apenas starters)")

    def can_evolve_by_level(self, pokemon_id, current_level):
        """Verifica se o Pokémon pode evoluir por nível"""
        evo_data = self.evolutions.get(str(pokemon_id))

        if not evo_data:
            return None

        lvl_min = evo_data.get("lvlMin")
        method = evo_data.get("method", "none")

        # Verifica se é evolução por nível (lvlMin é um número)
        if method == "level_up" and isinstance(lvl_min, (int, float)):
            if current_level >= lvl_min:
                return {
                    "evolve_to": evo_data.get("EvolveTo"),
                    "method": "level",
                    "requirement": lvl_min
                }

        return None

    def can_evolve_by_stone(self, pokemon_id, stone_name):
        """Verifica se o Pokémon pode evoluir com uma pedra específica"""
        evo_data = self.evolutions.get(str(pokemon_id))

        if not evo_data:
            return None

        lvl_min = evo_data.get("lvlMin")
        method = evo_data.get("method", "none")

        # Verifica se é evolução por pedra
        # Normaliza os nomes das pedras (remove hífens e espaços)
        stone_name_normalized = stone_name.lower().replace("-", "").replace(" ", "")
        method_normalized = method.lower().replace("-", "").replace(" ", "")

        # Lista de pedras de evolução válidas
        evolution_stones = [
            "firestone", "waterstone", "thunderstone", "leafstone",
            "moonstone", "sunstone", "icystone", "dawnstone",
            "duskstone", "shinystone"
        ]

        # Verifica se o método contém o nome da pedra
        if method_normalized in evolution_stones and method_normalized == stone_name_normalized:
            return {
                "evolve_to": evo_data.get("EvolveTo"),
                "method": "stone",
                "requirement": stone_name
            }

        # Verificação alternativa: lvlMin pode conter o nome da pedra
        if isinstance(lvl_min, str):
            lvl_min_normalized = lvl_min.lower().replace("-", "").replace(" ", "")
            if lvl_min_normalized in evolution_stones and lvl_min_normalized == stone_name_normalized:
                return {
                    "evolve_to": evo_data.get("EvolveTo"),
                    "method": "stone",
                    "requirement": stone_name
                }

        return None

    def can_evolve_by_trade(self, pokemon_id):
        """Verifica se o Pokémon pode evoluir por troca"""
        evo_data = self.evolutions.get(str(pokemon_id))

        if not evo_data:
            return False

        method = evo_data.get("method", "none")

        # Verifica se é evolução por troca
        if method == "trade":
            return {
                "evolve_to": evo_data.get("EvolveTo"),
                "method": "trade",
                "requirement": "trade"
            }

        return False

    def check_evolution(self, pokemon_id, current_level=None, stone_name=None, is_trade=False):
        """
        Verifica todas as possibilidades de evolução

        Args:
            pokemon_id: ID do Pokémon
            current_level: Nível atual (para evolução por nível)
            stone_name: Nome da pedra (para evolução por pedra)
            is_trade: Se é uma troca (para evolução por troca)

        Returns:
            dict ou None: Informações da evolução se possível, None caso contrário
        """
        # Primeiro verifica evolução por nível
        if current_level is not None:
            level_evo = self.can_evolve_by_level(pokemon_id, current_level)
            if level_evo:
                return level_evo

        # Depois verifica evolução por pedra
        if stone_name is not None:
            stone_evo = self.can_evolve_by_stone(pokemon_id, stone_name)
            if stone_evo:
                return stone_evo

        # Por último verifica evolução por troca
        if is_trade:
            trade_evo = self.can_evolve_by_trade(pokemon_id)
            if trade_evo:
                return trade_evo

        return None

    def get_evolution_info(self, pokemon_id):
        """Retorna informações de evolução do Pokémon"""
        return self.evolutions.get(str(pokemon_id), {
            "lvlMin": "none",
            "EvolveTo": "none",
            "method": "none"
        })

    def get_next_evolution(self, pokemon_id):
        """Retorna o próximo estágio de evolução"""
        evo_data = self.get_evolution_info(pokemon_id)
        next_id = evo_data.get("EvolveTo")

        if next_id != "none" and next_id is not None:
            return int(next_id)
        return None

    def get_evolution_chain(self, pokemon_id, max_depth=3):
        """
        Retorna toda a cadeia de evolução

        Returns:
            list: Lista com os IDs da cadeia de evolução [atual, proximo, ...]
        """
        chain = [pokemon_id]
        current_id = pokemon_id

        for _ in range(max_depth):
            next_id = self.get_next_evolution(current_id)
            if next_id is None:
                break
            chain.append(next_id)
            current_id = next_id

        return chain

    def is_final_form(self, pokemon_id):
        """Verifica se o Pokémon é a forma final"""
        next_id = self.get_next_evolution(pokemon_id)
        return next_id is None

    def get_evolution_method_string(self, pokemon_id):
        """Retorna uma string legível do método de evolução"""
        evo_data = self.get_evolution_info(pokemon_id)
        method = evo_data.get("method", "none")
        lvl_min = evo_data.get("lvlMin")

        if method == "level_up" and isinstance(lvl_min, (int, float)):
            return f"Evolui no nível {lvl_min}"
        elif method == "trade":
            return "Evolui por troca"
        elif method in ["firestone", "waterstone", "thunderstone", "leafstone", "moonstone", "sunstone"]:
            stone_name = method.replace("stone", " Stone").capitalize()
            return f"Evolui com {stone_name}"
        elif isinstance(lvl_min, str) and "stone" in lvl_min:
            stone_name = lvl_min.replace("-", " ").capitalize()
            return f"Evolui com {stone_name}"
        else:
            return "Não evolui"


# Instância global para uso no jogo
evolution_manager = EvolutionManager()