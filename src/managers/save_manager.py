# src/managers/save_manager.py
import pickle
import os
import hashlib
import json
from datetime import datetime
from typing import Optional, Dict, Any, List
from src.entities.pokemon import Pokemon


class SaveManager:
    def __init__(self, save_file="save.data"):
        self.save_file = save_file
        self.version = "1.0"  # Versão do formato de save
        self.magic_bytes = b"PKMSAVE"  # Identificador do arquivo

    def save_pokemon_data(self, player) -> bool:
        """
        Salva os dados dos Pokémon da PC Box e do time
        """
        try:
            # Coleta dados dos Pokémon da box
            box_data = []
            for pokemon in player.pc_box:
                pokemon_data = self._extract_pokemon_data(pokemon)
                box_data.append(pokemon_data)

            # Coleta dados dos Pokémon do time
            team_data = []
            for pokemon in player.team:
                pokemon_data = self._extract_pokemon_data(pokemon)
                team_data.append(pokemon_data)

            # Dados completos para salvar
            save_data = {
                "version": self.version,
                "timestamp": datetime.now().isoformat(),
                "box": box_data,
                "team": team_data,
                "metadata": {
                    "total_pokemon": len(box_data) + len(team_data),
                    "box_count": len(box_data),
                    "team_count": len(team_data)
                }
            }

            # Serializa com pickle
            serialized_data = pickle.dumps(save_data)

            # Adiciona checksum para verificação
            checksum = hashlib.sha256(serialized_data).digest()

            # Estrutura final: [MAGIC_BYTES][VERSION][CHECKSUM][DATA]
            with open(self.save_file, 'wb') as f:
                f.write(self.magic_bytes)
                f.write(len(serialized_data).to_bytes(4, 'big'))
                f.write(checksum)
                f.write(serialized_data)

            print(f"[SAVE] Dados salvos com sucesso! {len(box_data)} Pokémon na box, {len(team_data)} no time")
            return True

        except Exception as e:
            print(f"[ERRO] Falha ao salvar dados: {e}")
            return False

    def load_pokemon_data(self, player) -> bool:
        """
        Carrega os dados dos Pokémon para a PC Box e time do jogador
        """
        if not os.path.exists(self.save_file):
            print("[SAVE] Arquivo de save não encontrado")
            return False

        try:
            with open(self.save_file, 'rb') as f:
                # Verifica magic bytes
                magic = f.read(len(self.magic_bytes))
                if magic != self.magic_bytes:
                    print("[ERRO] Arquivo de save inválido ou corrompido")
                    return False

                # Lê tamanho dos dados
                data_size = int.from_bytes(f.read(4), 'big')

                # Lê e verifica checksum
                saved_checksum = f.read(32)  # SHA256 = 32 bytes
                data = f.read(data_size)

                # Verifica integridade
                current_checksum = hashlib.sha256(data).digest()
                if current_checksum != saved_checksum:
                    print("[ERRO] Checksum inválido - arquivo corrompido ou modificado")
                    return False

                # Carrega dados
                save_data = pickle.loads(data)

                # Verifica versão
                if save_data["version"] != self.version:
                    print(f"[SAVE] Versão diferente: save={save_data['version']}, atual={self.version}")
                    print("[SAVE] Tentando carregar mesmo assim...")

                # Limpa dados atuais
                player.pc_box.clear()
                player.team.clear()

                # Reconstrói Pokémon da box
                for pokemon_dict in save_data["box"]:
                    pokemon = self._reconstruct_pokemon(pokemon_dict)
                    if pokemon:
                        player.pc_box.append(pokemon)

                # Reconstrói Pokémon do time
                for pokemon_dict in save_data["team"]:
                    pokemon = self._reconstruct_pokemon(pokemon_dict)
                    if pokemon:
                        player.team.append(pokemon)
                        pokemon.is_in_team = True

                print(
                    f"[SAVE] Dados carregados com sucesso! {len(player.pc_box)} Pokémon na box, {len(player.team)} no time")
                return True

        except Exception as e:
            print(f"[ERRO] Falha ao carregar dados: {e}")
            import traceback
            traceback.print_exc()
            return False

    def _extract_pokemon_data(self, pokemon) -> Dict[str, Any]:
        """
        Extrai todos os dados relevantes de um Pokémon para salvar
        """
        return {
            "id": pokemon.id,
            "name": pokemon.name,
            "level": pokemon.level,
            "current_hp": pokemon.current_hp,
            "max_hp": pokemon.max_hp,
            "xp": pokemon.xp,
            "xp_to_next": pokemon.xp_to_next,
            "is_shiny": pokemon.is_shiny,
            "nature": pokemon.nature,
            "ivs": pokemon.ivs.copy(),
            "evs": pokemon.evs.copy(),
            "attack": pokemon.attack,
            "defense": pokemon.defense,
            "sp_attack": pokemon.sp_attack,
            "sp_defense": pokemon.sp_defense,
            "speed": pokemon.speed,
            "types": pokemon.types.copy(),
            "is_placed": pokemon.is_placed,
            "spot_id": pokemon.spot_id,
            "is_wild": pokemon.is_wild,
            # Valores calculados que podem ser recalculados se ausentes
            "attack_damage": getattr(pokemon, 'attack_damage', None),
            "defense_value": getattr(pokemon, 'defense_value', None),
            # Metadados extras (para futuras expansões)
            "captured_date": getattr(pokemon, 'captured_date', datetime.now().isoformat()),
            "happiness": getattr(pokemon, 'happiness', 70),  # Valor padrão se não existir
            "ability": getattr(pokemon, 'ability', None),
            "held_item": getattr(pokemon, 'held_item', None),
            "moves": getattr(pokemon, 'moves', []),
        }

    def _reconstruct_pokemon(self, data: Dict[str, Any]) -> Optional[Pokemon]:
        """
        Reconstrói um Pokémon a partir dos dados salvos
        Com tratamento robusto para dados ausentes
        """
        try:
            # Dados obrigatórios com fallbacks
            pokemon_id = data.get("id", 1)  # Fallback para Bulbasaur
            level = data.get("level", 5)
            is_wild = data.get("is_wild", False)
            is_shiny = data.get("is_shiny", False)

            # Cria instância base
            pokemon = Pokemon(0, 0, pokemon_id, level, is_wild, is_shiny)

            # Restaura atributos com verificações seguras
            pokemon.current_hp = data.get("current_hp", pokemon.max_hp)
            pokemon.xp = data.get("xp", 0)
            pokemon.xp_to_next = data.get("xp_to_next", pokemon._calculate_xp_needed())

            # IVs (com fallback para os gerados aleatoriamente)
            saved_ivs = data.get("ivs", {})
            for stat in pokemon.ivs.keys():
                if stat in saved_ivs:
                    pokemon.ivs[stat] = saved_ivs[stat]

            # EVs
            saved_evs = data.get("evs", {})
            for stat in pokemon.evs.keys():
                if stat in saved_evs:
                    pokemon.evs[stat] = saved_evs[stat]

            # Natureza (com fallback)
            pokemon.nature = data.get("nature", pokemon.nature)

            # Recalcula stats baseado nos IVs/EVs carregados
            pokemon._calculate_stats()

            # Restaura HP máximo após recálculo
            if "max_hp" in data:
                pokemon.max_hp = data["max_hp"]

            # Atributos de jogo
            pokemon.is_placed = data.get("is_placed", False)
            pokemon.spot_id = data.get("spot_id", None)

            # Atributos de combate (podem ser recalculados)
            if "attack_damage" in data and data["attack_damage"]:
                pokemon.attack_damage = data["attack_damage"]
            else:
                pokemon.attack_damage = pokemon._calculate_attack_damage()

            if "defense_value" in data and data["defense_value"]:
                pokemon.defense_value = data["defense_value"]
            else:
                pokemon.defense_value = pokemon._calculate_defense()

            # Novos atributos (com valores padrão seguros)
            pokemon.happiness = data.get("happiness", 70)
            pokemon.ability = data.get("ability", None)
            pokemon.held_item = data.get("held_item", None)
            pokemon.moves = data.get("moves", [])
            pokemon.captured_date = data.get("captured_date", datetime.now().isoformat())

            return pokemon

        except Exception as e:
            print(f"[ERRO] Falha ao reconstruir Pokémon: {e}")
            import traceback
            traceback.print_exc()
            return None