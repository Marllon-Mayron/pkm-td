# src/managers/save_manager.py

import json
import uuid
import os
import pickle
from datetime import datetime
from typing import Any, Dict, Optional


class SaveManager:
    """
    Gerenciador de save unificado para todo o jogo
    Usa JSON para ser legível e fácil de modificar
    """

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
        self.save_dir = "saves"  # Pasta de saves
        self.current_save_file = None
        self.save_data = self._get_default_save_data()

        # Garante que a pasta de saves existe
        self._ensure_save_directory()

    def _ensure_save_directory(self):
        """Garante que a pasta de saves existe"""
        if not os.path.exists(self.save_dir):
            os.makedirs(self.save_dir)
            print(f"[SAVE] Pasta criada: {self.save_dir}")

    def _get_default_save_data(self) -> Dict:
        """Retorna a estrutura padrão de save"""
        return {
            "meta": {
                "version": "1.0.0",
                "last_save": None,
                "play_time": 0,
                "save_name": "Novo Jogo"
            },
            "player": {
                "money": 100,
                "score": 0,
                "position": {"x": 0, "y": 0},
                "team": [],  # Pokémons no time
                "pc_box": [],  # Pokémons na box
                "bag": {},  # Itens da mochila {item_id: quantity}
                "seen_pokemon": [],  # IDs vistos
                "caught_pokemon": []  # IDs capturados
            },
            "game_state": {
                "current_chapter": 1,
                "current_phase": 1,
                "unlocked_chapters": [1],
                "unlocked_phases": ["1-1"],
                "completed_phases": [],
                "stars": {}
            }
        }

    def _pokemon_to_dict(self, pokemon) -> Dict:
        """Converte um objeto Pokémon para dicionário"""
        return {
            "unique_id": getattr(pokemon, 'unique_id', str(uuid.uuid4())),
            "id": pokemon.id,
            "name": pokemon.name,
            "level": pokemon.level,
            "is_shiny": pokemon.is_shiny,
            "current_hp": pokemon.current_hp,
            "max_hp": pokemon.max_hp,
            "xp": pokemon.xp,
            "ivs": pokemon.ivs,
            "evs": pokemon.evs,
            "nature": pokemon.nature,
            "types": pokemon.types,
            "attack": pokemon.attack,
            "defense": pokemon.defense,
            "sp_attack": pokemon.sp_attack,
            "sp_defense": pokemon.sp_defense,
            "speed": pokemon.speed_stat,
            "is_in_team": pokemon.is_in_team,
            "is_placed": getattr(pokemon, 'is_placed', False),
            "spot_id": getattr(pokemon, 'spot_id', None)
        }

    def _dict_to_pokemon(self, data: Dict):
        """Converte dicionário para objeto Pokémon"""
        from src.entities.pokemon import Pokemon

        # Cria o Pokémon básico
        pokemon = Pokemon(
            x=0, y=0,  # Posição será definida depois se necessário
            pokemon_id=data["id"],
            level=data["level"],
            shiny=data["is_shiny"]
        )

        pokemon.unique_id = data.get("unique_id", str(uuid.uuid4()))

        # Restaura os atributos
        pokemon.current_hp = data["current_hp"]
        pokemon.max_hp = data["max_hp"]
        pokemon.speed_stat = data["speed"]
        pokemon.xp = data["xp"]
        pokemon.ivs = data["ivs"]
        pokemon.evs = data["evs"]
        pokemon.nature = data["nature"]
        pokemon.is_in_team = data["is_in_team"]
        pokemon.is_placed = False
        pokemon.spot_id = None

        return pokemon

    def save_game(self, player, game_state=None, save_name="save", slot=1):
        """
        Salva o estado completo do jogo
        """
        # Atualiza os dados do jogador
        self.save_data["player"]["money"] = player.money
        self.save_data["player"]["score"] = player.score
        self.save_data["player"]["position"] = {"x": player.x, "y": player.y}

        # IMPORTANTE: Usa unique_id como identificador único
        box_ids = set()
        unique_box = []

        # Primeiro, adiciona todos os Pokémon da box atual
        for p in player.pc_box:
            # Usa unique_id como identificador único
            if p.unique_id not in box_ids:
                box_ids.add(p.unique_id)
                unique_box.append(p)

        # Depois, adiciona os Pokémon do time que não estão na box
        for p in player.team:
            if p.unique_id not in box_ids:
                box_ids.add(p.unique_id)
                unique_box.append(p)
                print(f"[SAVE] Pokémon {p.name} do time não estava na box, adicionando...")

        # Agora salva a box completa (todos os Pokémon)
        self.save_data["player"]["pc_box"] = [
            self._pokemon_to_dict(p) for p in unique_box
        ]

        # Salva o time (apenas as referências)
        self.save_data["player"]["team"] = [
            self._pokemon_to_dict(p) for p in player.team
        ]

        # Salva a bag
        self.save_data["player"]["bag"] = dict(player.bag.items)

        # Salva Pokédex
        self.save_data["player"]["seen_pokemon"] = list(player.seen_pokemon)
        self.save_data["player"]["caught_pokemon"] = list(player.caught_pokemon)

        # Salva estado do jogo
        if game_state:
            self.save_data["game_state"].update(game_state)

        # Atualiza metadados
        self.save_data["meta"]["last_save"] = datetime.now().isoformat()
        self.save_data["meta"]["save_name"] = save_name

        # Define o nome do arquivo
        filename = f"save_{slot}.json"
        filepath = os.path.join(self.save_dir, filename)

        # Salva em JSON
        try:
            with open(filepath, 'w', encoding='utf-8') as f:
                json.dump(self.save_data, f, indent=2, ensure_ascii=False)
            print(f"[SAVE] Jogo salvo em {filepath}")
            print(f"[SAVE] Box: {len(unique_box)} Pokémon | Time: {len(player.team)} Pokémon")
            print(f"[SAVE] Itens salvos: {self.save_data['player']['bag']}")
            return True
        except Exception as e:
            print(f"[ERRO] Falha ao salvar: {e}")
            return False

    def load_game(self, player, slot=1) -> bool:
        """
        Carrega um save e aplica ao jogador

        Args:
            player: Objeto Player para aplicar os dados
            slot: Número do slot (1-3)

        Returns:
            bool: True se carregou com sucesso
        """
        filename = f"save_{slot}.json"
        filepath = os.path.join(self.save_dir, filename)

        if not os.path.exists(filepath):
            print(f"[SAVE] Arquivo não encontrado: {filepath}")
            return False

        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                self.save_data = json.load(f)

            # Aplica dados ao jogador
            player_data = self.save_data["player"]

            # Dados básicos
            player.money = player_data["money"]
            player.score = player_data["score"]
            player.x = player_data["position"]["x"]
            player.y = player_data["position"]["y"]

            # CARREGA A BAG (itens da mochila)
            player.bag.items = player_data.get("bag", {})
            player.bag._update_filtered_items()

            # Carrega Pokémons
            player.pc_box = []
            for pokemon_data in player_data["pc_box"]:
                pokemon = self._dict_to_pokemon(pokemon_data)
                player.pc_box.append(pokemon)

            # Carrega o time - AGORA usando unique_id para match
            player.team = []
            for pokemon_data in player_data["team"]:
                # Encontra o Pokémon na box usando unique_id
                for p in player.pc_box:
                    if p.unique_id == pokemon_data.get("unique_id"):
                        player.team.append(p)
                        p.is_in_team = True
                        break
                else:
                    # Fallback: se não encontrar por unique_id, tenta pelos atributos
                    for p in player.pc_box:
                        if (p.id == pokemon_data["id"] and
                                p.level == pokemon_data["level"] and
                                p.is_shiny == pokemon_data["is_shiny"] and
                                p not in player.team):
                            player.team.append(p)
                            p.is_in_team = True
                            break

            # Carrega Pokédex
            player.seen_pokemon = set(player_data["seen_pokemon"])
            player.caught_pokemon = set(player_data["caught_pokemon"])

            print(f"[SAVE] Jogo carregado de {filepath}")
            print(f"[SAVE] Itens carregados: {player.bag.items}")
            print(f"[SAVE] Pokémons: {len(player.pc_box)} na box, {len(player.team)} no time")
            return True

        except Exception as e:
            print(f"[ERRO] Falha ao carregar: {e}")
            return False

    def delete_save(self, slot=1):
        """Deleta um save específico"""
        filename = f"save_{slot}.json"
        filepath = os.path.join(self.save_dir, filename)

        if os.path.exists(filepath):
            os.remove(filepath)
            print(f"[SAVE] Save {slot} deletado")
            return True
        return False

    def list_saves(self) -> list:
        """Lista todos os saves disponíveis"""
        saves = []
        for i in range(1, 4):  # Slots 1-3
            filename = f"save_{i}.json"
            filepath = os.path.join(self.save_dir, filename)

            if os.path.exists(filepath):
                try:
                    with open(filepath, 'r', encoding='utf-8') as f:
                        data = json.load(f)
                    saves.append({
                        "slot": i,
                        "name": data["meta"]["save_name"],
                        "last_save": data["meta"]["last_save"],
                        "play_time": data["meta"]["play_time"],
                        "chapter": data["game_state"]["current_chapter"],
                        "phase": data["game_state"]["current_phase"],
                        "pokemon_count": len(data["player"]["pc_box"]),
                        "team_size": len(data["player"]["team"]),
                        "item_count": sum(data["player"]["bag"].values())
                    })
                except:
                    saves.append({
                        "slot": i,
                        "name": "Arquivo corrompido",
                        "last_save": None,
                        "error": True
                    })
            else:
                saves.append({
                    "slot": i,
                    "name": "Vazio",
                    "empty": True
                })

        return saves

    def export_to_pickle(self, slot=1):
        """Exporta para pickle (opcional, para dados complexos)"""
        filename = f"save_{slot}.pkl"
        filepath = os.path.join(self.save_dir, filename)

        try:
            with open(filepath, 'wb') as f:
                pickle.dump(self.save_data, f)
            print(f"[SAVE] Exportado para pickle: {filepath}")
            return True
        except Exception as e:
            print(f"[ERRO] Falha ao exportar: {e}")
            return False


# Instância global
save_manager = SaveManager()