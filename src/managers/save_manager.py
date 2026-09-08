# src/managers/save_manager.py

import json
import uuid
import os
import pickle
from datetime import datetime
from typing import Dict

SAVE_FORMAT_VERSION = "0.1.6"  # Versão do FORMATO do save (ATUALIZADA)
GAME_VERSION_COMPATIBLE = "0.1.14"  # Versão do jogo que usa este formato


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
        """Retorna a estrutura padrão de save (versão 0.1.6)"""
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
                    "unlocked_data": {}
                },
                "desfossilizadores": [],
                "total_playtime": 0,
                "has_chosen_starter": False  # NOVO
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
                "custom_name": getattr(pokemon, 'custom_name', None),
                "happiness": getattr(pokemon, 'happiness', 0),
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
        pokemon.custom_name = data.get("custom_name")
        pokemon.happiness = data.get("happiness", 0)
        pokemon.happiness = max(0, min(255, pokemon.happiness))

        # Restaura os moves
        moves_data = data.get("moves", [])
        if moves_data:
            pokemon.restore_moves(moves_data)

        return pokemon

    def save_game(self, player, game_state=None, save_name="save", slot=1) -> bool:
        """
        Salva o estado completo do jogo.
        player.pc_box: lista de dicionários (dados leves)
        player.team: lista de objetos Pokemon (instâncias completas)
        """
        import os
        from src.managers.save_manager import SAVE_FORMAT_VERSION

        # Define o slot atual
        self.current_save_file = slot

        filename = f"save_{slot}.json"
        filepath = os.path.join(self.save_dir, filename)

        # Carrega save existente se houver
        existing_data = None
        if os.path.exists(filepath):
            try:
                with open(filepath, 'r', encoding='utf-8') as f:
                    existing_data = json.load(f)
                print(f"[SAVE] Save existente carregado de {filepath}")
            except Exception as e:
                print(f"[SAVE] Erro ao carregar save existente: {e}")
                existing_data = None

        if not existing_data:
            existing_data = self._get_default_save_data()
            print(f"[SAVE] Criando novo save para slot {slot}")

        # Atualiza metadados
        existing_data["meta"]["last_save"] = datetime.now().isoformat()
        existing_data["meta"]["save_name"] = save_name
        existing_data["meta"]["version"] = SAVE_FORMAT_VERSION

        # ===== DADOS DO JOGADOR =====
        player_data = existing_data["player"]
        player_data["money"] = player.money
        player_data["score"] = player.score
        player_data["position"] = {"x": player.x, "y": player.y}
        player_data["bag"] = dict(player.bag.items) if hasattr(player.bag, 'items') else {}
        player_data["seen_pokemon"] = list(player.seen_pokemon)
        player_data["caught_pokemon"] = list(player.caught_pokemon)
        player_data["desfossilizadores"] = player.desfossilizadores
        player_data["total_playtime"] = player.total_playtime
        player_data["has_chosen_starter"] = getattr(player, 'has_chosen_starter', False)

        # ===== MYSTERY GIFT =====
        player_data["mystery_gift"] = {
            "redeemed_codes": getattr(player, 'redeemed_codes', {}),
            "history": getattr(player, 'mystery_gift_history', [])
        }

        # ===== ACHIEVEMENTS =====
        if hasattr(player, 'achievements'):
            player_data["achievements"] = {
                "unlocked": list(player.achievements.get("unlocked", [])),
                "counters": dict(player.achievements.get("counters", {})),
                "unlocked_data": dict(player.achievements.get("unlocked_data", {}))
            }
        else:
            player_data["achievements"] = {"unlocked": [], "counters": {}, "unlocked_data": {}}

        # ===== PC BOX - já é uma lista de dicionários =====
        # Garante que todos os dicionários tenham unique_id
        for data in player.pc_box:
            if "unique_id" not in data:
                data["unique_id"] = str(uuid.uuid4())

        # ===== TIME - converte objetos para dicionários =====
        team_dicts = []
        for pokemon in player.team:
            # Converte o objeto Pokemon para dict
            p_dict = self._pokemon_to_dict(pokemon)
            # Garante que o unique_id existe
            if "unique_id" not in p_dict:
                p_dict["unique_id"] = str(uuid.uuid4())
            team_dicts.append(p_dict)

        # ===== CONSOLIDA: time + pc_box sem duplicatas =====
        # Cria um dicionário para deduplicar por unique_id
        all_pokemon_dicts = {}
        # Adiciona os da pc_box primeiro
        for data in player.pc_box:
            uid = data.get("unique_id")
            if uid:
                all_pokemon_dicts[uid] = data
        # Adiciona os do time (sobrescreve se houver duplicata, garantindo que o time prevalece)
        for p_dict in team_dicts:
            uid = p_dict.get("unique_id")
            if uid:
                all_pokemon_dicts[uid] = p_dict

        # Agora, all_pokemon_dicts contém todos os Pokémon únicos
        # Precisamos separar: os que estão no time devem ter is_in_team=True
        # Atualiza is_in_team baseado no time real
        team_ids = {p.unique_id for p in player.team}
        for uid, data in all_pokemon_dicts.items():
            data["is_in_team"] = uid in team_ids

        # Converte para lista de dicts (a ordem não importa)
        box_list = list(all_pokemon_dicts.values())

        # ===== SALVA =====
        player_data["pc_box"] = box_list
        # O time é salvo como uma lista de dicts também (referências)
        # Mas o time deve ser salvo como uma lista de dicts na ordem do time
        # Para preservar a ordem, salvamos o time como lista de unique_ids? Ou como dicts completos?
        # Vamos salvar o time como lista de dicts completos (na ordem do time)
        team_order = []
        for pokemon in player.team:
            # Busca o dict correspondente
            uid = pokemon.unique_id
            if uid in all_pokemon_dicts:
                team_order.append(all_pokemon_dicts[uid])
            else:
                # Fallback: converte novamente
                team_order.append(self._pokemon_to_dict(pokemon))

        player_data["team"] = team_order

        # ===== ESTADO DO JOGO =====
        if game_state:
            for key, value in game_state.items():
                existing_data["game_state"][key] = value

        # ===== CONFIGURAÇÕES =====
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

        self.save_data = existing_data

        try:
            with open(filepath, 'w', encoding='utf-8') as f:
                json.dump(self.save_data, f, indent=2, ensure_ascii=False)
            print(f"[SAVE] Jogo salvo em {filepath}")
            print(f"[SAVE] Box: {len(box_list)} Pokemon | Time: {len(player.team)} Pokemon")
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
        Carrega um save e aplica ao jogador.
        Agora: pc_box será preenchida com dicionários, team com objetos Pokemon.
        """
        filename = f"save_{slot}.json"
        filepath = os.path.join(self.save_dir, filename)

        if not os.path.exists(filepath):
            print(f"[SAVE] Arquivo não encontrado: {filepath}")
            return False

        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                raw_data = json.load(f)

            save_version = raw_data.get("meta", {}).get("version", "0.1.1")
            current_version = SAVE_FORMAT_VERSION

            if save_version != current_version:
                print(f"[SAVE] Save versão {save_version} - será migrado para {current_version}")
                raw_data = self.migrate_save_data(raw_data, save_version)

            self.save_data = raw_data
            self.current_save_file = slot

            player_data = self.save_data["player"]

            # Dados básicos
            player.money = player_data["money"]
            player.score = player_data["score"]
            player.x = player_data["position"]["x"]
            player.y = player_data["position"]["y"]
            player.has_chosen_starter = player_data.get("has_chosen_starter", False)

            # Bag
            player.bag.items = player_data.get("bag", {})
            if hasattr(player.bag, '_update_filtered_items'):
                player.bag._update_filtered_items()

            # ===== CARREGA PC BOX COMO DICIONÁRIOS =====
            box_data = player_data.get("pc_box", [])
            player.pc_box = box_data  # já são dicts

            # ===== CARREGA TIME COMO OBJETOS POKEMON =====
            team_data = player_data.get("team", [])
            player.team = []
            for p_dict in team_data:
                # Converte dict para objeto Pokemon
                pokemon = self._dict_to_pokemon(p_dict)
                # Garante que unique_id está presente
                if not hasattr(pokemon, 'unique_id') or not pokemon.unique_id:
                    pokemon.unique_id = p_dict.get("unique_id", str(uuid.uuid4()))
                # Marca como no time
                pokemon.is_in_team = True
                player.team.append(pokemon)

            # ===== ATUALIZA STATUS DE is_in_team NA BOX =====
            team_ids = {p.unique_id for p in player.team}
            for data in player.pc_box:
                data["is_in_team"] = data.get("unique_id") in team_ids

            # ===== POKEDEX =====
            player.seen_pokemon = set(player_data.get("seen_pokemon", []))
            player.caught_pokemon = set(player_data.get("caught_pokemon", []))

            # ===== DESFOSSILIZADORES =====
            player.desfossilizadores = player_data.get("desfossilizadores", [])
            if not player.desfossilizadores:
                if hasattr(player, '_add_initial_desfossilizador'):
                    player._add_initial_desfossilizador()
                else:
                    player.desfossilizadores = [{
                        "id": 1,
                        "level": 1,
                        "status": "empty",
                        "fossil_id": None,
                        "pokemon_id": None,
                        "start_time": None,
                        "duration_minutes": 60,
                        "time_elapsed": 0.0
                    }]

            # Garante campos nos desfossilizadores
            for desfossilizador in player.desfossilizadores:
                if "time_elapsed" not in desfossilizador:
                    desfossilizador["time_elapsed"] = 0.0
                if "start_time" not in desfossilizador:
                    desfossilizador["start_time"] = None
                if "duration_minutes" not in desfossilizador:
                    desfossilizador["duration_minutes"] = 60
                if "status" not in desfossilizador:
                    desfossilizador["status"] = "empty"

            # Verifica se algum desfossilizador já está pronto
            for desfossilizador in player.desfossilizadores:
                if desfossilizador["status"] == "processing":
                    if desfossilizador["time_elapsed"] >= desfossilizador["duration_minutes"]:
                        desfossilizador["status"] = "ready"
                        desfossilizador["start_time"] = None
                        desfossilizador["time_elapsed"] = desfossilizador["duration_minutes"]

            # ===== TEMPO DE JOGO =====
            player.total_playtime = player_data.get("total_playtime", 0.0)

            # ===== MYSTERY GIFT =====
            mg_data = player_data.get("mystery_gift", {})
            player.redeemed_codes = mg_data.get("redeemed_codes", {})
            player.mystery_gift_history = mg_data.get("history", [])

            # ===== CONFIGURAÇÕES =====
            settings_data = self.save_data.get("settings", {})
            if settings_data:
                from src.config.settings import settings
                from src.managers.sounds.sound_manager import sound_manager
                settings.sfx_volume = settings_data.get("sfx_volume", 0.7)
                settings.music_volume = settings_data.get("music_volume", 0.5)
                settings.music_enabled = settings_data.get("music_enabled", True)
                settings.sfx_enabled = settings_data.get("sfx_enabled", True)
                settings.fullscreen = settings_data.get("fullscreen", False)
                settings.vsync = settings_data.get("vsync", True)
                settings.target_fps = settings_data.get("target_fps", 60)

                if settings.music_enabled:
                    sound_manager.set_music_volume(settings.music_volume)
                else:
                    sound_manager.set_music_volume(0)

                if settings.sfx_enabled:
                    sound_manager.set_sfx_volume(settings.sfx_volume)
                else:
                    sound_manager.set_sfx_volume(0)

            # ===== ACHIEVEMENTS =====
            achievements_data = player_data.get("achievements", {})
            if not hasattr(player, 'achievements'):
                player.achievements = {"unlocked": [], "counters": {}, "unlocked_data": {}}
            player.achievements["unlocked"] = list(achievements_data.get("unlocked", []))
            player.achievements["counters"] = dict(achievements_data.get("counters", {}))
            player.achievements["unlocked_data"] = dict(achievements_data.get("unlocked_data", {}))

            if hasattr(player, 'achievement_manager'):
                player.achievement_manager.load_from_player()

            print(f"[SAVE] Jogo carregado de {filepath}")
            print(f"[SAVE] Box: {len(player.pc_box)} Pokemon | Time: {len(player.team)} Pokemon")
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
        Migra dados de save de versões antigas para o formato atual (0.1.6)
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
                    pokemon_data["happiness"] = 0

            team = migrated.get("player", {}).get("team", [])
            for idx, pokemon_data in enumerate(team):
                if "custom_name" not in pokemon_data:
                    pokemon_data["custom_name"] = None
                if "happiness" not in pokemon_data:
                    pokemon_data["happiness"] = 0

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
                    "unlocked_data": {}
                }
                print("[MIGRATE] Estrutura de conquistas adicionada")
            else:
                # Se já existe, garante que tem unlocked_data
                if "unlocked_data" not in migrated["player"]["achievements"]:
                    migrated["player"]["achievements"]["unlocked_data"] = {}
                    print("[MIGRATE] Campo unlocked_data adicionado as conquistas")

            # Atualiza versão
            migrated["meta"]["version"] = "0.1.4"
            version = "0.1.4"
            print("[MIGRATE] Migracao para 0.1.4 concluida: conquistas adicionadas")

        # ===== MIGRAÇÃO DE 0.1.4 para 0.1.5 (INCUBADORA/DESFOSSILIZADOR) =====
        if version == "0.1.4":
            # Adiciona desfossilizadores se não existir
            if "desfossilizadores" not in migrated.get("player", {}):
                migrated["player"]["desfossilizadores"] = []
                print("[MIGRATE] Campo desfossilizadores criado")

            # Se não tiver desfossilizadores, adiciona um inicial
            if not migrated["player"]["desfossilizadores"]:
                desfossilizador = {
                    "id": 1,
                    "level": 1,
                    "status": "empty",
                    "fossil_id": None,
                    "pokemon_id": None,
                    "start_time": None,
                    "duration_minutes": 3600,  # 1 hora para jogadores existentes
                    "time_elapsed": 0.0
                }
                migrated["player"]["desfossilizadores"].append(desfossilizador)
                print("[MIGRATE] Desfossilizador inicial adicionado ao save!")

            # Garante que cada desfossilizador existente tem os campos corretos
            durations = {1: 3600, 2: 2700, 3: 1200}
            for desfossilizador in migrated["player"]["desfossilizadores"]:
                if "time_elapsed" not in desfossilizador:
                    desfossilizador["time_elapsed"] = 0.0
                if "start_time" not in desfossilizador:
                    desfossilizador["start_time"] = None
                if "duration_minutes" not in desfossilizador or desfossilizador["duration_minutes"] == 0:
                    level = desfossilizador.get("level", 1)
                    desfossilizador["duration_minutes"] = durations.get(level, 3600)
                if "status" not in desfossilizador:
                    desfossilizador["status"] = "empty"
                if "fossil_id" not in desfossilizador:
                    desfossilizador["fossil_id"] = None
                if "pokemon_id" not in desfossilizador:
                    desfossilizador["pokemon_id"] = None

            # Adiciona total_playtime se não existir
            if "total_playtime" not in migrated.get("player", {}):
                migrated["player"]["total_playtime"] = 0.0
                print("[MIGRATE] Campo total_playtime adicionado")

            # Atualiza versão
            migrated["meta"]["version"] = "0.1.5"
            version = "0.1.5"
            print("[MIGRATE] Migracao para 0.1.5 concluida: desfossilizadores e tempo de jogo")

        # ===== NOVA MIGRAÇÃO: 0.1.5 para 0.1.6 (HAS_CHOSEN_STARTER) =====
        if version == "0.1.5":
            # Adiciona has_chosen_starter se não existir
            if "has_chosen_starter" not in migrated.get("player", {}):
                # ===== VERIFICA SE O JOGADOR TEM POKÉMON NO TIME OU NA BOX =====
                has_team = len(migrated.get("player", {}).get("team", [])) > 0
                has_box = len(migrated.get("player", {}).get("pc_box", [])) > 0

                # Se tem Pokémon no time ou na box, assume que já escolheu o inicial
                if has_team or has_box:
                    migrated["player"]["has_chosen_starter"] = True
                    print(
                        f"[MIGRATE] has_chosen_starter definido como True (time: {len(migrated['player']['team'])}, box: {len(migrated['player']['pc_box'])})")
                else:
                    migrated["player"]["has_chosen_starter"] = False
                    print("[MIGRATE] has_chosen_starter definido como False (sem Pokémon)")
            else:
                # Se já existe, mantém o valor
                print(f"[MIGRATE] has_chosen_starter já existia: {migrated['player']['has_chosen_starter']}")

            # Atualiza versão
            migrated["meta"]["version"] = current_version
            print("[MIGRATE] Migracao para 0.1.6 concluida: has_chosen_starter adicionado")

        # ===== FUTURAS MIGRAÇÕES =====
        # if version == "0.1.6" and current_version == "0.1.7":
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

        if "desfossilizadores" not in migrated["player"]:
            migrated["player"]["desfossilizadores"] = []
            desfossilizador = {
                "id": 1,
                "level": 1,
                "status": "empty",
                "fossil_id": None,
                "pokemon_id": None,
                "start_time": None,
                "duration_minutes": 3600,
                "time_elapsed": 0.0
            }
            migrated["player"]["desfossilizadores"].append(desfossilizador)
            print("[MIGRATE] desfossilizador inicial adicionado (fallback)")

        if "total_playtime" not in migrated["player"]:
            migrated["player"]["total_playtime"] = 0.0

        # Garante que has_chosen_starter existe (fallback)
        if "has_chosen_starter" not in migrated["player"]:
            has_team = len(migrated["player"].get("team", [])) > 0
            has_box = len(migrated["player"].get("pc_box", [])) > 0
            migrated["player"]["has_chosen_starter"] = has_team or has_box
            print(f"[MIGRATE] has_chosen_starter definido como {migrated['player']['has_chosen_starter']} (fallback)")

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