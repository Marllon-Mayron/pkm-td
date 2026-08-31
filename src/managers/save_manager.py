# src/managers/save_manager.py

import json
import uuid
import os
import pickle
from datetime import datetime
from typing import Dict

SAVE_FORMAT_VERSION = "0.1.4"  # Versão do FORMATO do save (ATUALIZADA)
GAME_VERSION_COMPATIBLE = "0.1.11"  # Versão do jogo que usa este formato


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
        self.current_save_file = None  # Armazena o slot atual
        self.save_data = self._get_default_save_data()

        # Garante que a pasta de saves existe
        self._ensure_save_directory()

    def _ensure_save_directory(self):
        """Garante que a pasta de saves existe"""
        if not os.path.exists(self.save_dir):
            os.makedirs(self.save_dir)
            print(f"[SAVE] Pasta criada: {self.save_dir}")

    def _get_default_save_data(self) -> Dict:
        """Retorna a estrutura padrão de save (versão 0.1.4)"""
        return {
            "meta": {
                "version": SAVE_FORMAT_VERSION,
                "last_save": None,
                "play_time": 0,
                "save_name": "Novo Jogo"
            },
            "player": {
                "money": 100,
                "score": 0,
                "position": {"x": 0, "y": 0},
                "team": [],
                "pc_box": [],
                "bag": {},
                "seen_pokemon": [],
                "caught_pokemon": [],
                "mystery_gift": {
                    "redeemed_codes": {},
                    "history": []
                },
                "achievements": {
                    "unlocked": [],
                    "counters": {},
                    "unlocked_data": {}  # NOVO: {"ach_id": {"unlocked_at": "...", "unlocked_phase": "1-3"}}
                }
            },
            "game_state": {
                "current_chapter": 1,
                "current_phase": 1,
                "unlocked_chapters": [1],
                "unlocked_phases": ["1-1"],
                "completed_phases": [],
                "stars": {}
            },
            "settings": {
                "sfx_volume": 0.7,
                "music_volume": 0.5,
                "music_enabled": True,
                "sfx_enabled": True,
                "fullscreen": False,
                "vsync": True,
                "target_fps": 60
            }
        }

    def _pokemon_to_dict(self, pokemon) -> Dict:
        """
        Converte um objeto Pokémon para dicionário.
        Se o Pokémon for um Ditto transformado, usa os dados ORIGINAIS para salvar.
        """
        from src.data.move_data import MoveData

        move_data = MoveData()

        # ===== VERIFICA SE É DITTO TRANSFORMADO =====
        is_transformed_ditto = (
                pokemon.id == 132 and
                hasattr(pokemon, '_is_transformed') and
                pokemon._is_transformed and
                hasattr(pokemon, '_original_id')
        )

        if is_transformed_ditto:
            # Usa os dados ORIGINAIS para salvar
            print(f"[SAVE] Ditto {pokemon.name} está transformado - salvando estado ORIGINAL")

            # Dados originais
            pokemon_id = pokemon._original_id
            pokemon_name = pokemon._original_name
            pokemon_types = pokemon._original_types
            pokemon_base_stats = pokemon._original_base_stats
            pokemon_moves = pokemon._original_moves

            # Stats atuais (HP, etc) - mantém os valores atuais
            current_hp = pokemon.current_hp
            max_hp = pokemon.max_hp  # Este é o max_hp calculado com stats transformados
            # Mas o HP deve ser baseado no max_hp original, não no transformado
            # Vamos recalcular o max_hp original
            original_max_hp = pokemon._original_max_hp if hasattr(pokemon, '_original_max_hp') else pokemon.max_hp

            # Recalcula o HP proporcionalmente
            if original_max_hp > 0:
                hp_ratio = current_hp / max_hp if max_hp > 0 else 1.0
                save_hp = max(1, int(original_max_hp * hp_ratio))
            else:
                save_hp = current_hp

            # Moves data
            moves_data = []
            for move in pokemon_moves:
                moves_data.append({
                    "name": move.name,
                    "current_pp": move.current_pp,
                    "max_pp": move.max_pp
                })

            pokemon_dict = {
                "unique_id": getattr(pokemon, 'unique_id', str(uuid.uuid4())),
                "id": pokemon_id,
                "name": pokemon_name,
                "level": pokemon.level,
                "is_shiny": pokemon.is_shiny,
                "current_hp": save_hp,
                "max_hp": original_max_hp,
                "xp": pokemon.xp,
                "ivs": pokemon.ivs,
                "evs": pokemon.evs,
                "nature": pokemon.nature,
                "types": pokemon_types,
                "attack": pokemon._original_attack if hasattr(pokemon, '_original_attack') else pokemon.attack,
                "defense": pokemon._original_defense if hasattr(pokemon, '_original_defense') else pokemon.defense,
                "sp_attack": pokemon._original_sp_attack if hasattr(pokemon,
                                                                    '_original_sp_attack') else pokemon.sp_attack,
                "sp_defense": pokemon._original_sp_defense if hasattr(pokemon,
                                                                      '_original_sp_defense') else pokemon.sp_defense,
                "speed": pokemon._original_speed if hasattr(pokemon, '_original_speed') else pokemon.speed_stat,
                "is_in_team": pokemon.is_in_team,
                "is_placed": getattr(pokemon, 'is_placed', False),
                "spot_id": getattr(pokemon, 'spot_id', None),
                "moves": moves_data,
                # NOVOS CAMPOS para Ditto transformado (preservar nome/felicidade do Ditto original)
                "custom_name": getattr(pokemon, 'custom_name', None),
                "happiness": getattr(pokemon, 'happiness', 50),
            }

            return pokemon_dict

        # ===== POKÉMON NORMAL (não transformado) =====
        moves_data = []
        for move in pokemon.moves:
            moves_data.append({
                "name": move.name,
                "current_pp": move.current_pp,
                "max_pp": move.max_pp
            })

        pokemon_dict = {
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
            "spot_id": getattr(pokemon, 'spot_id', None),
            "moves": moves_data,
            "weight_kg": pokemon.weight_kg,
            "height_m": pokemon.height_m,
            "gender": pokemon.gender,
            # NOVOS CAMPOS
            "custom_name": pokemon.custom_name,
            "happiness": pokemon.happiness,
        }

        return pokemon_dict

    def _dict_to_pokemon(self, data: Dict):
        """Converte dicionário para objeto Pokémon, incluindo moves e novos atributos"""
        from src.entities.pokemon import Pokemon

        # Cria o Pokémon básico
        pokemon = Pokemon(
            x=0, y=0,
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
        pokemon.weight_kg = data.get("weight_kg", 10.0)
        pokemon.height_m = data.get("height_m", 1.0)
        pokemon.gender = data.get("gender")

        # ===== NOVOS CAMPOS COM FALLBACK PARA SAVES ANTIGOS =====
        pokemon.custom_name = data.get("custom_name")  # None se não existir
        pokemon.happiness = data.get("happiness", 50)  # 50 se não existir
        pokemon.happiness = max(0, min(100, pokemon.happiness))  # Garante limites

        # Restaura os moves
        moves_data = data.get("moves", [])
        if moves_data:
            pokemon.restore_moves(moves_data)

        return pokemon

    def save_game(self, player, game_state=None, save_name="save", slot=1) -> bool:
        """
        Salva o estado completo do jogo
        """
        import os

        # Define o slot atual
        self.current_save_file = slot

        # ===== SEMPRE TENTA CARREGAR O SAVE EXISTENTE PRIMEIRO =====
        filename = f"save_{slot}.json"
        filepath = os.path.join(self.save_dir, filename)

        existing_data = None

        # Tenta carregar o save existente
        if os.path.exists(filepath):
            try:
                with open(filepath, 'r', encoding='utf-8') as f:
                    existing_data = json.load(f)
                print(f"[SAVE] Save existente carregado de {filepath}")
            except Exception as e:
                print(f"[SAVE] Erro ao carregar save existente: {e}")
                existing_data = None

        # Se não existe save, cria novo
        if not existing_data:
            existing_data = self._get_default_save_data()
            print(f"[SAVE] Criando novo save para slot {slot}")

        # Mantém metadados importantes
        existing_data["meta"]["last_save"] = datetime.now().isoformat()
        existing_data["meta"]["save_name"] = save_name

        # ===== ATUALIZA DADOS DO JOGADOR =====
        existing_data["player"]["money"] = player.money
        existing_data["player"]["score"] = player.score
        existing_data["player"]["position"] = {"x": player.x, "y": player.y}
        existing_data["player"]["bag"] = dict(player.bag.items)
        existing_data["player"]["seen_pokemon"] = list(player.seen_pokemon)
        existing_data["player"]["caught_pokemon"] = list(player.caught_pokemon)

        # ===== PRESERVA MYSTERY GIFT =====
        existing_data["player"]["mystery_gift"] = {
            "redeemed_codes": getattr(player, 'redeemed_codes', {}),
            "history": getattr(player, 'mystery_gift_history', [])
        }

        # ===== SALVA ACHIEVEMENTS =====
        if hasattr(player, 'achievements'):
            existing_data["player"]["achievements"] = {
                "unlocked": list(player.achievements.get("unlocked", [])),
                "counters": dict(player.achievements.get("counters", {})),
                "unlocked_data": dict(player.achievements.get("unlocked_data", {}))
            }
            print(f"[SAVE] Achievements salvos: {len(player.achievements.get('unlocked', []))} desbloqueadas")
        else:
            existing_data["player"]["achievements"] = {
                "unlocked": [],
                "counters": {},
                "unlocked_data": {}
            }

        # ===== SALVA POKÉMONS =====
        box_ids = set()
        unique_box = []

        # Primeiro, adiciona todos os Pokémon da box atual
        for p in player.pc_box:
            if p.unique_id not in box_ids:
                box_ids.add(p.unique_id)
                unique_box.append(p)

        # Depois, adiciona os Pokémon do time que não estão na box
        for p in player.team:
            if p.unique_id not in box_ids:
                box_ids.add(p.unique_id)
                unique_box.append(p)
                print(f"[SAVE] Pokémon {p.name} do time não estava na box, adicionando...")

        # Salva a box completa
        existing_data["player"]["pc_box"] = [
            self._pokemon_to_dict(p) for p in unique_box
        ]

        # Salva o time (apenas as referências)
        existing_data["player"]["team"] = [
            self._pokemon_to_dict(p) for p in player.team
        ]

        # ===== ATUALIZA ESTADO DO JOGO =====
        if game_state:
            for key, value in game_state.items():
                existing_data["game_state"][key] = value

        # ===== SALVA CONFIGURAÇÕES =====
        from src.config.settings import settings
        existing_data["settings"] = {
            "sfx_volume": settings.sfx_volume,
            "music_volume": settings.music_volume,
            "music_enabled": settings.music_enabled,
            "sfx_enabled": settings.sfx_enabled,
            "fullscreen": settings.fullscreen,
            "vsync": settings.vsync,
            "target_fps": settings.target_fps
        }

        # Atualiza o save_data interno
        self.save_data = existing_data

        # Salva em arquivo
        try:
            with open(filepath, 'w', encoding='utf-8') as f:
                json.dump(self.save_data, f, indent=2, ensure_ascii=False)
            print(f"[SAVE] Jogo salvo em {filepath}")
            print(f"[SAVE] Box: {len(unique_box)} Pokemon | Time: {len(player.team)} Pokemon")
            print(f"[SAVE] Itens salvos: {self.save_data['player']['bag']}")
            print(f"[SAVE] Achievements: {len(self.save_data['player']['achievements']['unlocked'])} desbloqueadas")
            return True
        except Exception as e:
            print(f"[ERRO] Falha ao salvar: {e}")
            import traceback
            traceback.print_exc()
            return False

    def save_settings(self, settings_obj) -> bool:
        """Salva as configurações atuais no save atual"""
        if not self.current_save_file:
            print("[SAVE] Nenhum save carregado, não é possível salvar configurações")
            return False

        # Atualiza as configurações no save_data
        self.save_data["settings"] = {
            "sfx_volume": settings_obj.sfx_volume,
            "music_volume": settings_obj.music_volume,
            "music_enabled": settings_obj.music_enabled,
            "sfx_enabled": settings_obj.sfx_enabled,
            "fullscreen": settings_obj.fullscreen,
            "vsync": settings_obj.vsync,
            "target_fps": settings_obj.target_fps
        }

        # Salva o arquivo
        filename = f"save_{self.current_save_file}.json"
        filepath = os.path.join(self.save_dir, filename)

        try:
            with open(filepath, 'w', encoding='utf-8') as f:
                json.dump(self.save_data, f, indent=2, ensure_ascii=False)
            print(f"[SAVE] Configurações salvas: Música={settings_obj.music_volume}, SFX={settings_obj.sfx_volume}")
            return True
        except Exception as e:
            print(f"[ERRO] Falha ao salvar configurações: {e}")
            return False

    def load_game(self, player, slot=1) -> bool:
        """
        Carrega um save e aplica ao jogador
        """
        filename = f"save_{slot}.json"
        filepath = os.path.join(self.save_dir, filename)

        if not os.path.exists(filepath):
            print(f"[SAVE] Arquivo não encontrado: {filepath}")
            return False

        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                raw_data = json.load(f)

            # ===== VERIFICA VERSÃO E MIGRA SE NECESSÁRIO =====
            save_version = raw_data.get("meta", {}).get("version", "0.1.1")
            current_version = SAVE_FORMAT_VERSION

            if save_version != current_version:
                print(f"[SAVE] Save versão {save_version} - será migrado para {current_version}")
                raw_data = self.migrate_save_data(raw_data, save_version)

            self.save_data = raw_data

            # Define o slot atual
            self.current_save_file = slot

            # Aplica dados ao jogador
            player_data = self.save_data["player"]

            # Dados básicos
            player.money = player_data["money"]
            player.score = player_data["score"]
            player.x = player_data["position"]["x"]
            player.y = player_data["position"]["y"]

            # Carrega a bag
            player.bag.items = player_data.get("bag", {})
            if hasattr(player.bag, '_update_filtered_items'):
                player.bag._update_filtered_items()

            # Carrega Pokémons
            player.pc_box = []
            for pokemon_data in player_data["pc_box"]:
                pokemon = self._dict_to_pokemon(pokemon_data)
                player.pc_box.append(pokemon)

            # Carrega o time
            player.team = []
            for pokemon_data in player_data["team"]:
                found = False
                for p in player.pc_box:
                    if p.unique_id == pokemon_data.get("unique_id"):
                        player.team.append(p)
                        p.is_in_team = True
                        found = True
                        break
                if not found:
                    pokemon = self._dict_to_pokemon(pokemon_data)
                    player.team.append(pokemon)
                    pokemon.is_in_team = True
                    player.pc_box.append(pokemon)

            # Carrega Pokédex
            player.seen_pokemon = set(player_data.get("seen_pokemon", []))
            player.caught_pokemon = set(player_data.get("caught_pokemon", []))

            # Carrega Mystery Gift
            mg_data = player_data.get("mystery_gift", {})
            player.redeemed_codes = mg_data.get("redeemed_codes", {})
            player.mystery_gift_history = mg_data.get("history", [])

            # ===== CARREGA E APLICA AS CONFIGURAÇÕES DE ÁUDIO DO SAVE =====
            settings_data = self.save_data.get("settings", {})
            if settings_data:
                from src.config.settings import settings
                from src.managers.sounds.sound_manager import sound_manager

                # Aplica as configurações salvas ao objeto settings
                settings.sfx_volume = settings_data.get("sfx_volume", 0.7)
                settings.music_volume = settings_data.get("music_volume", 0.5)
                settings.music_enabled = settings_data.get("music_enabled", True)
                settings.sfx_enabled = settings_data.get("sfx_enabled", True)
                settings.fullscreen = settings_data.get("fullscreen", False)
                settings.vsync = settings_data.get("vsync", True)
                settings.target_fps = settings_data.get("target_fps", 60)

                # APLICA IMEDIATAMENTE AO SOUND_MANAGER
                if settings.music_enabled:
                    sound_manager.set_music_volume(settings.music_volume)
                else:
                    sound_manager.set_music_volume(0)

                if settings.sfx_enabled:
                    sound_manager.set_sfx_volume(settings.sfx_volume)
                else:
                    sound_manager.set_sfx_volume(0)

                # ===== CARREGA ACHIEVEMENTS =====
                achievements_data = player_data.get("achievements", {})

                # Garante que a estrutura existe no player
                if not hasattr(player, 'achievements'):
                    player.achievements = {
                        "unlocked": [],
                        "counters": {},
                        "unlocked_data": {}
                    }

                # Carrega os dados
                player.achievements["unlocked"] = list(achievements_data.get("unlocked", []))
                player.achievements["counters"] = dict(achievements_data.get("counters", {}))
                player.achievements["unlocked_data"] = dict(achievements_data.get("unlocked_data", {}))

                # ===== RECARREGA O ACHIEVEMENT_MANAGER =====
                if hasattr(player, 'achievement_manager'):
                    player.achievement_manager.load_from_player()
                    print(f"[SAVE] Achievements carregados: {len(player.achievements['unlocked'])} desbloqueadas")

            print(f"[SAVE] Jogo carregado de {filepath}")
            return True

        except Exception as e:
            print(f"[ERRO] Falha ao carregar: {e}")
            import traceback
            traceback.print_exc()
            return False

    def load_settings(self, settings_obj) -> bool:
        """
        Carrega as configurações do save atual
        IMPORTANTE: Deve ser chamado APÓS load_game()
        """
        if not self.current_save_file:
            print("[SAVE] Nenhum save carregado, não é possível carregar configurações")
            return False

        settings_data = self.save_data.get("settings", {})
        if not settings_data:
            print("[SAVE] Nenhuma configuração encontrada no save, usando padrões")
            return False

        # Aplica as configurações
        settings_obj.sfx_volume = settings_data.get("sfx_volume", 0.7)
        settings_obj.music_volume = settings_data.get("music_volume", 0.5)
        settings_obj.music_enabled = settings_data.get("music_enabled", True)
        settings_obj.sfx_enabled = settings_data.get("sfx_enabled", True)
        settings_obj.fullscreen = settings_data.get("fullscreen", False)
        settings_obj.vsync = settings_data.get("vsync", True)
        settings_obj.target_fps = settings_data.get("target_fps", 60)

        print(
            f"[SAVE] Configurações carregadas: Música={settings_obj.music_volume} ({'ON' if settings_obj.music_enabled else 'OFF'}), SFX={settings_obj.sfx_volume} ({'ON' if settings_obj.sfx_enabled else 'OFF'})")
        return True

    def migrate_save_data(self, save_data: Dict, version: str) -> Dict:
        """
        Migra dados de save de versões antigas para o formato atual (0.1.4)
        """
        import copy
        migrated = copy.deepcopy(save_data)

        current_version = SAVE_FORMAT_VERSION

        print(f"[MIGRATE] Migrando save da versão {version} para {current_version}")

        # ===== MIGRAÇÃO DE 0.1.1 (ou sem versão) para 0.1.2 =====
        if version in ["0.1.1", "0.1.0", "0.0.0"]:
            # Adiciona estrutura de Mystery Gift se não existir
            if "mystery_gift" not in migrated.get("player", {}):
                migrated["player"]["mystery_gift"] = {
                    "redeemed_codes": {},
                    "history": []
                }
                print("[MIGRATE] Estrutura Mystery Gift adicionada")

            # Se existia redeemed_codes antigo (string), converte
            if "redeemed_codes" in migrated.get("player", {}):
                old_codes = migrated["player"]["redeemed_codes"]
                if isinstance(old_codes, dict):
                    new_codes = {}
                    for code, value in old_codes.items():
                        if isinstance(value, str):
                            new_codes[code] = {
                                "pokemon_id": 0,
                                "pokemon_name": "Pokemon Antigo",
                                "date": value,
                                "timestamp": 0,
                                "event_name": "Evento Anterior",
                                "is_shiny": False
                            }
                        else:
                            new_codes[code] = value
                    migrated["player"]["mystery_gift"]["redeemed_codes"] = new_codes
                    print(f"[MIGRATE] Convertidos {len(new_codes)} codigos resgatados antigos")

                # Remove o campo antigo
                del migrated["player"]["redeemed_codes"]

            # Garante history existe
            if "history" not in migrated["player"]["mystery_gift"]:
                migrated["player"]["mystery_gift"]["history"] = []

            # Atualiza versão para 0.1.2
            migrated["meta"]["version"] = "0.1.2"
            version = "0.1.2"
            print("[MIGRATE] Migracao para 0.1.2 concluida")

        # ===== MIGRAÇÃO DE 0.1.2 para 0.1.3 =====
        if version in ["0.1.2"]:
            pc_box = migrated.get("player", {}).get("pc_box", [])
            for idx, pokemon_data in enumerate(pc_box):
                if "custom_name" not in pokemon_data:
                    pokemon_data["custom_name"] = None
                if "happiness" not in pokemon_data:
                    pokemon_data["happiness"] = 50

            team = migrated.get("player", {}).get("team", [])
            for idx, pokemon_data in enumerate(team):
                if "custom_name" not in pokemon_data:
                    pokemon_data["custom_name"] = None
                if "happiness" not in pokemon_data:
                    pokemon_data["happiness"] = 50

            migrated["meta"]["version"] = "0.1.3"
            version = "0.1.3"
            print("[MIGRATE] Migracao para 0.1.3 concluida")

        # ===== MIGRAÇÃO DE 0.1.3 para 0.1.4 (ACHIEVEMENTS) =====
        if version in ["0.1.3"]:
            # Adiciona estrutura de conquistas
            if "achievements" not in migrated.get("player", {}):
                migrated["player"]["achievements"] = {
                    "unlocked": [],
                    "counters": {},
                    "unlocked_data": {}  # NOVO: dados de data/hora e fase
                }
                print("[MIGRATE] Estrutura de conquistas adicionada")
            else:
                # Se já existe, garante que tem unlocked_data
                if "unlocked_data" not in migrated["player"]["achievements"]:
                    migrated["player"]["achievements"]["unlocked_data"] = {}
                    print("[MIGRATE] Campo unlocked_data adicionado as conquistas")

            # Atualiza versão
            migrated["meta"]["version"] = current_version
            print("[MIGRATE] Migracao para 0.1.4 concluida: conquistas adicionadas")

        # ===== FUTURAS MIGRAÇÕES =====
        # if version == "0.1.4" and current_version == "0.1.5":
        #     pass

        # ===== VALIDAÇÃO PÓS-MIGRAÇÃO =====
        if "player" not in migrated:
            migrated["player"] = {}

        if "mystery_gift" not in migrated["player"]:
            migrated["player"]["mystery_gift"] = {"redeemed_codes": {}, "history": []}

        if "seen_pokemon" not in migrated["player"]:
            migrated["player"]["seen_pokemon"] = []

        if "caught_pokemon" not in migrated["player"]:
            migrated["player"]["caught_pokemon"] = []

        print(f"[MIGRATE] Migracao concluida! Versao final: {migrated['meta']['version']}")
        return migrated

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
                        "item_count": sum(data["player"]["bag"].values()),
                        "settings": data.get("settings", {})
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