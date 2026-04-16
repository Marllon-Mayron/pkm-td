# src/managers/evolution_manager.py

import json
import os
import sys
from pathlib import Path
from typing import Dict, List, Optional, Any


class EvolutionManager:
    """Gerencia as evoluções dos Pokémon - SUPORTA MÚLTIPLAS VARIANTES"""

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
        self.evolutions = {}  # Formato: {pokemon_id: {"lvlMin": x, "EvolveTo": y, "method": z}}
        self.evolution_variants = {}  # Formato: {pokemon_id: [{"evolves_to": x, "method": y, ...}]}
        self._load_evolution_data()

    def _get_json_path(self):
        """Obtém o caminho correto para o arquivo JSON unificado"""
        if getattr(sys, 'frozen', False):
            root_dir = os.path.dirname(sys.executable)
        else:
            current_file = Path(__file__).resolve()
            root_dir = current_file.parent.parent.parent

        # PRIORIDADE 1: src/data/scripts/pokemon_completo.json
        json_path = root_dir / "src" / "data" / "scripts" / "pokemon_completo.json"

        if json_path.exists():
            return json_path

        # PRIORIDADE 2: res/json/pokemon_completo.json
        json_path = root_dir / "res" / "json" / "pokemon_completo.json"

        if json_path.exists():
            return json_path

        # FALLBACK
        json_path = root_dir / "src" / "data" / "scripts" / "pokemon_evolutions_gen1.json"

        return json_path

    def _load_evolution_data(self):
        """Carrega os dados de evolução do arquivo JSON unificado"""
        try:
            json_path = self._get_json_path()

            if not json_path.exists():
                print(f"⚠️ Arquivo de evoluções não encontrado: {json_path}")
                self._create_fallback_data()
                return

            with open(json_path, 'r', encoding='utf-8') as file:
                data = json.load(file)

            # Verifica se é o novo formato (lista com campo "evolution")
            if isinstance(data, list) and len(data) > 0 and "evolution" in data[0]:
                for pokemon in data:
                    pokemon_id = str(pokemon["id"])
                    evo_data = pokemon.get("evolution", {})

                    # Coleta TODAS as variantes de evolução
                    all_variants = []

                    # 1. Pega do campo "evolution_details"
                    evolution_details = evo_data.get("evolution_details", [])
                    for detail in evolution_details:
                        variant = {
                            "evolves_to_id": detail.get("evolves_to_id"),
                            "evolves_to_name": detail.get("evolves_to_name"),
                            "method": detail.get("method", "unknown"),
                            "min_level": detail.get("min_level"),
                            "item": detail.get("item"),
                            "min_happiness": detail.get("min_happiness"),
                            "time_of_day": detail.get("time_of_day"),
                            "location": detail.get("location"),
                            "gender": detail.get("gender"),
                            "known_move": detail.get("known_move"),
                            "trade_species": detail.get("trade_species")
                        }
                        # Remove None values
                        variant = {k: v for k, v in variant.items() if v is not None}
                        all_variants.append(variant)

                    # 2. Pega do campo "variants" (se existir)
                    variants = evo_data.get("variants", [])
                    for variant in variants:
                        # Normaliza o formato
                        norm_variant = {
                            "evolves_to_id": variant.get("evolves_to_id"),
                            "evolves_to_name": variant.get("evolves_to_name"),
                            "method": variant.get("method", "unknown"),
                            "min_level": variant.get("min_level"),
                            "item": variant.get("item"),
                            "min_happiness": variant.get("min_happiness"),
                            "time_of_day": variant.get("time_of_day"),
                            "location": variant.get("location"),
                            "gender": variant.get("gender"),
                            "known_move": variant.get("known_move")
                        }
                        norm_variant = {k: v for k, v in norm_variant.items() if v is not None}
                        if norm_variant not in all_variants:
                            all_variants.append(norm_variant)

                    # Armazena as variantes
                    if all_variants:
                        self.evolution_variants[pokemon_id] = all_variants

                    # Para compatibilidade com código antigo, pega a PRIMEIRA evolução
                    # como a evolução "padrão"
                    if all_variants:
                        first_variant = all_variants[0]
                        evolve_to = first_variant.get("evolves_to_id")
                        method = first_variant.get("method", "none")

                        if method == "level_up":
                            lvl_min = first_variant.get("min_level", "none")
                        elif method == "use_item":
                            lvl_min = first_variant.get("item", "none")
                        else:
                            lvl_min = "none"

                        if evolve_to:
                            self.evolutions[pokemon_id] = {
                                "lvlMin": lvl_min if lvl_min is not None else "none",
                                "EvolveTo": evolve_to,
                                "method": method
                            }
                        else:
                            self.evolutions[pokemon_id] = {
                                "lvlMin": "none",
                                "EvolveTo": "none",
                                "method": "none"
                            }
                    else:
                        self.evolutions[pokemon_id] = {
                            "lvlMin": "none",
                            "EvolveTo": "none",
                            "method": "none"
                        }
            else:
                # Formato antigo
                self.evolutions = data

            print(f"✓ Carregados dados de evolução para {len(self.evolutions)} Pokémon")
            print(f"✓ Pokémon com múltiplas variantes: {len(self.evolution_variants)}")

        except Exception as e:
            print(f"✗ Erro ao carregar dados de evolução: {e}")
            self._create_fallback_data()

    def _create_fallback_data(self):
        """Cria dados de evolução básicos para fallback"""
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

    def get_evolution_variants(self, pokemon_id) -> List[Dict]:
        """
        Retorna todas as variantes de evolução possíveis para um Pokémon.
        Ex: Eevee retorna [Vaporeon, Jolteon, Flareon, Espeon, Umbreon, Leafeon, Glaceon, Sylveon]
        """
        return self.evolution_variants.get(str(pokemon_id), [])

    def has_multiple_evolutions(self, pokemon_id) -> bool:
        """Verifica se o Pokémon tem múltiplas opções de evolução"""
        variants = self.get_evolution_variants(pokemon_id)
        return len(variants) > 1

    def can_evolve_by_level(self, pokemon_id, current_level):
        """Verifica se o Pokémon pode evoluir por nível (pega a PRIMEIRA evolução por nível)"""
        variants = self.get_evolution_variants(pokemon_id)

        for variant in variants:
            method = variant.get("method", "")
            if method == "level_up":
                min_level = variant.get("min_level")
                if isinstance(min_level, (int, float)) and current_level >= min_level:
                    return {
                        "evolve_to": variant.get("evolves_to_id"),
                        "method": "level",
                        "requirement": min_level,
                        "variant_name": variant.get("evolves_to_name")
                    }
        return None

    def can_evolve_by_stone(self, pokemon_id, stone_name):
        """Verifica se o Pokémon pode evoluir com uma pedra específica"""
        variants = self.get_evolution_variants(pokemon_id)

        stone_name_normalized = stone_name.lower().replace("-", "").replace(" ", "")

        for variant in variants:
            method = variant.get("method", "")
            item = variant.get("item", "")

            item_normalized = item.lower().replace("-", "").replace(" ", "") if item else ""
            method_normalized = method.lower().replace("-", "").replace(" ", "")

            evolution_stones = [
                "firestone", "waterstone", "thunderstone", "leafstone",
                "moonstone", "sunstone", "icystone", "dawnstone",
                "duskstone", "shinystone"
            ]

            if method_normalized in evolution_stones and method_normalized == stone_name_normalized:
                return {
                    "evolve_to": variant.get("evolves_to_id"),
                    "method": "stone",
                    "requirement": stone_name,
                    "variant_name": variant.get("evolves_to_name")
                }

            if item_normalized in evolution_stones and item_normalized == stone_name_normalized:
                return {
                    "evolve_to": variant.get("evolves_to_id"),
                    "method": "stone",
                    "requirement": stone_name,
                    "variant_name": variant.get("evolves_to_name")
                }

        return None

    def can_evolve_by_trade(self, pokemon_id):
        """Verifica se o Pokémon pode evoluir por troca"""
        variants = self.get_evolution_variants(pokemon_id)

        for variant in variants:
            method = variant.get("method", "")
            if method == "trade":
                return {
                    "evolve_to": variant.get("evolves_to_id"),
                    "method": "trade",
                    "requirement": "trade",
                    "variant_name": variant.get("evolves_to_name")
                }

        return False

    def can_evolve_by_happiness(self, pokemon_id, current_happiness, time_of_day=None):
        """Verifica se o Pokémon pode evoluir por felicidade (Eevee -> Espeon/Umbreon)"""
        variants = self.get_evolution_variants(pokemon_id)

        for variant in variants:
            method = variant.get("method", "")
            if method == "happiness":
                min_happiness = variant.get("min_happiness", 160)
                if current_happiness >= min_happiness:
                    # Verifica horário se necessário
                    req_time = variant.get("time_of_day")
                    if req_time and time_of_day:
                        if req_time.lower() == time_of_day.lower():
                            return {
                                "evolve_to": variant.get("evolves_to_id"),
                                "method": "happiness",
                                "requirement": min_happiness,
                                "variant_name": variant.get("evolves_to_name"),
                                "time_of_day": req_time
                            }
                    elif not req_time:
                        return {
                            "evolve_to": variant.get("evolves_to_id"),
                            "method": "happiness",
                            "requirement": min_happiness,
                            "variant_name": variant.get("evolves_to_name")
                        }
        return None

    def can_evolve_by_location(self, pokemon_id, location_name):
        """Verifica se o Pokémon pode evoluir por local específico (Eevee -> Leafeon/Glaceon)"""
        variants = self.get_evolution_variants(pokemon_id)
        location_normalized = location_name.lower().replace("-", "").replace(" ", "")

        for variant in variants:
            method = variant.get("method", "")
            req_location = variant.get("location", "")

            if method == "location" and req_location:
                req_normalized = req_location.lower().replace("-", "").replace(" ", "")
                if req_normalized == location_normalized:
                    return {
                        "evolve_to": variant.get("evolves_to_id"),
                        "method": "location",
                        "requirement": req_location,
                        "variant_name": variant.get("evolves_to_name")
                    }
        return None

    def check_evolution(self, pokemon_id, current_level=None, stone_name=None,
                        is_trade=False, current_happiness=None, time_of_day=None,
                        location_name=None):
        """
        Verifica todas as possibilidades de evolução
        Retorna a PRIMEIRA evolução encontrada (para compatibilidade)
        """
        # 1. Evolução por nível
        if current_level is not None:
            level_evo = self.can_evolve_by_level(pokemon_id, current_level)
            if level_evo:
                return level_evo

        # 2. Evolução por pedra
        if stone_name is not None:
            stone_evo = self.can_evolve_by_stone(pokemon_id, stone_name)
            if stone_evo:
                return stone_evo

        # 3. Evolução por felicidade
        if current_happiness is not None:
            happiness_evo = self.can_evolve_by_happiness(pokemon_id, current_happiness, time_of_day)
            if happiness_evo:
                return happiness_evo

        # 4. Evolução por local
        if location_name is not None:
            location_evo = self.can_evolve_by_location(pokemon_id, location_name)
            if location_evo:
                return location_evo

        # 5. Evolução por troca
        if is_trade:
            trade_evo = self.can_evolve_by_trade(pokemon_id)
            if trade_evo:
                return trade_evo

        return None

    def get_all_evolution_options(self, pokemon_id) -> List[Dict]:
        """Retorna TODAS as opções de evolução disponíveis para um Pokémon"""
        return self.get_evolution_variants(pokemon_id)

    def get_evolution_info(self, pokemon_id):
        """Retorna informações de evolução do Pokémon (formato antigo para compatibilidade)"""
        return self.evolutions.get(str(pokemon_id), {
            "lvlMin": "none",
            "EvolveTo": "none",
            "method": "none"
        })

    def get_next_evolution(self, pokemon_id):
        """Retorna o próximo estágio de evolução (primeiro da lista)"""
        evo_data = self.get_evolution_info(pokemon_id)
        next_id = evo_data.get("EvolveTo")

        if next_id != "none" and next_id is not None:
            return int(next_id)
        return None

    def get_evolution_chain(self, pokemon_id, max_depth=3):
        """Retorna toda a cadeia de evolução (ignora ramificações)"""
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
        variants = self.get_evolution_variants(pokemon_id)
        return len(variants) == 0

    def get_evolution_method_string(self, pokemon_id):
        """Retorna uma string legível do método de evolução (primeiro método)"""
        variants = self.get_evolution_variants(pokemon_id)

        if not variants:
            return "Não evolui"

        if self.has_multiple_evolutions(pokemon_id):
            methods = []
            for v in variants:
                method = v.get("method", "")
                if method == "level_up":
                    level = v.get("min_level", "?")
                    methods.append(f"Nível {level}")
                elif method == "use_item":
                    item = v.get("item", "item")
                    methods.append(f"Usar {item}")
                elif method == "happiness":
                    methods.append("Felicidade")
                elif method == "trade":
                    methods.append("Troca")
                elif method == "location":
                    methods.append(f"Local especial")
            return f"Múltiplas: {', '.join(methods)}"

        # Forma antiga para compatibilidade
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