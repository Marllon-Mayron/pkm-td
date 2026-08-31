# src/data/pokedex.py - ATUALIZADO PARA CONSUMIR O NOVO JSON UNIFICADO
import json
import os
import pygame
from pathlib import Path
from typing import Dict, List, Optional, Any
from src.data.sprite_loader import PokemonSpriteManager


class Pokedex:
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
        self.pokemon_data = {}
        self.max_id = 151

        # Usa o gerenciador de sprites APENAS para InMap
        self.sprite_manager = PokemonSpriteManager()

        # Cache de sprites front/back (mantém o sistema antigo)
        self.front_sprites = {}
        self.back_sprites = {}
        self.front_shiny_sprites = {}
        self.back_shiny_sprites = {}

        # Cache para sprites InMap (novo sistema)
        self.inmap_animations_cache = {}
        self.pokemon_animations_info = {}

        # Tipos
        self.type_colors = {
            "normal": (168, 168, 120),
            "fire": (240, 128, 48),
            "water": (104, 144, 240),
            "electric": (248, 208, 48),
            "grass": (120, 200, 80),
            "ice": (152, 216, 216),
            "fighting": (192, 48, 40),
            "poison": (160, 64, 160),
            "ground": (224, 192, 104),
            "flying": (168, 144, 240),
            "psychic": (248, 88, 136),
            "bug": (168, 184, 32),
            "rock": (184, 160, 56),
            "ghost": (112, 88, 152),
            "dragon": (112, 56, 248),
            "dark": (112, 88, 72),
            "steel": (184, 184, 208),
            "fairy": (238, 153, 238)
        }

        # Inicializa limites de speed
        self.min_base_speed = 0
        self.max_base_speed = 1

        self.load_pokemon_data()
        self.load_sprites()

    def load_pokemon_data(self):
        """Carrega dados do arquivo JSON unificado (pokemon_completo.json)"""
        try:
            # PRIORIDADE 1: src/data/scripts/pokemon_completo.json
            json_path = Path(__file__).parent.parent.parent / "src" / "data" / "scripts" / "pokemon_completo.json"

            if not json_path.exists():
                # PRIORIDADE 2: res/json/pokemon_completo.json
                json_path = Path(__file__).parent.parent.parent / "res" / "json" / "pokemon_completo.json"

            if not json_path.exists():
                print(f"⚠️ Arquivo JSON não encontrado: {json_path}")
                self._load_fallback_data()
                return

            with open(json_path, 'r', encoding='utf-8') as file:
                data = json.load(file)

            # Carrega os Pokémon do novo formato unificado
            for pokemon in data:
                pokemon_id = pokemon["id"]

                # Extrai informações de evolução
                next_evolution_id = None
                evolution_method = "none"
                evolution_level = None

                evo_data = pokemon.get("evolution", {})
                family_members = evo_data.get("family_members", [])

                # Encontra o próximo estágio na cadeia
                for i, member in enumerate(family_members):
                    if member.get("id") == pokemon_id and i + 1 < len(family_members):
                        next_evolution_id = family_members[i + 1].get("id")
                        break

                # Pega o método e nível dos evolution_details
                evolution_details = evo_data.get("evolution_details", [])
                if evolution_details:
                    detail = evolution_details[0]
                    evolution_method = detail.get("method", "none")
                    if evolution_method == "level_up":
                        evolution_level = detail.get("min_level")
                    elif evolution_method == "use_item":
                        evolution_method = detail.get("item", "none")

                self.pokemon_data[pokemon_id] = {
                    "id": pokemon_id,
                    "name": pokemon["name"],
                    "is_legendary": pokemon.get("is_legendary", False),
                    "is_mythical": pokemon.get("is_mythical", False),
                    "types": pokemon["type"],
                    "base_stats": {
                        "hp": pokemon["base"]["hp"],
                        "attack": pokemon["base"]["attack"],
                        "defense": pokemon["base"]["defense"],
                        "special_attack": pokemon["base"]["special-attack"],
                        "special_defense": pokemon["base"]["special-defense"],
                        "speed": pokemon["base"]["speed"]
                    },
                    "ev_yield": {
                        "hp": pokemon["ev"]["hp"],
                        "attack": pokemon["ev"]["attack"],
                        "defense": pokemon["ev"]["defense"],
                        "special_attack": pokemon["ev"]["special-attack"],
                        "special_defense": pokemon["ev"]["special-defense"],
                        "speed": pokemon["ev"]["speed"]
                    },
                    "catch_rate": pokemon.get("rate", pokemon.get("capture_rate", 120)),
                    "evolution": {
                        "EvolveTo": next_evolution_id,
                        "lvlMin": evolution_level if evolution_level is not None else "none",
                        "method": evolution_method
                    },
                    "weight_kg": pokemon.get("weight_kg", 10.0),
                    "height_m": pokemon.get("height_m", 1.0),
                    "gender_ratio": pokemon.get("gender_ratio", 0.5),
                }

                if pokemon_id > self.max_id:
                    self.max_id = pokemon_id

            print(f"✓ Carregados {len(self.pokemon_data)} Pokémon do JSON")
            self._cache_base_speed_limits()

        except Exception as e:
            print(f"✗ Erro ao carregar Pokémon data: {e}")
            self._load_fallback_data()

    def load_sprites(self):
        """Carrega os sprites front e back (mantém o sistema original)"""
        base_path = Path(__file__).parent.parent.parent / "res" / "PokemonSprites"

        if not base_path.exists():
            print(f"Diretório de sprites não encontrado: {base_path}")
            return

        for pokemon_id in range(1, self.max_id + 1):
            self._load_front_sprite(pokemon_id, base_path)
            self._load_back_sprite(pokemon_id, base_path)

        print(f"Sprites carregados: Front({len(self.front_sprites)}), Back({len(self.back_sprites)})")

    def _load_front_sprite(self, pokemon_id, base_path):
        """Carrega sprite frontal (96x96) - MANTIDO ORIGINAL"""
        # Normal
        filename = self._format_filename_front_back(pokemon_id, shiny=False)
        path = base_path / "front" / f"{filename}.png"

        if path.exists():
            try:
                sprite = pygame.image.load(str(path)).convert_alpha()
                self.front_sprites[pokemon_id] = sprite
            except Exception as e:
                print(f"Erro ao carregar front {pokemon_id}: {e}")

        # Shiny
        filename_shiny = self._format_filename_front_back(pokemon_id, shiny=True)
        path_shiny = base_path / "front" / f"{filename_shiny}.png"

        if path_shiny.exists():
            try:
                sprite = pygame.image.load(str(path_shiny)).convert_alpha()
                self.front_shiny_sprites[pokemon_id] = sprite
            except Exception as e:
                print(f"Erro ao carregar front shiny {pokemon_id}: {e}")

    def _load_back_sprite(self, pokemon_id, base_path):
        """Carrega sprite traseiro (96x96) - MANTIDO ORIGINAL"""
        # Normal
        filename = self._format_filename_front_back(pokemon_id, shiny=False)
        path = base_path / "back" / f"{filename}.png"

        if path.exists():
            try:
                sprite = pygame.image.load(str(path)).convert_alpha()
                self.back_sprites[pokemon_id] = sprite
            except Exception as e:
                print(f"Erro ao carregar back {pokemon_id}: {e}")

        # Shiny
        filename_shiny = self._format_filename_front_back(pokemon_id, shiny=True)
        path_shiny = base_path / "back" / f"{filename_shiny}.png"

        if path_shiny.exists():
            try:
                sprite = pygame.image.load(str(path_shiny)).convert_alpha()
                self.back_shiny_sprites[pokemon_id] = sprite
            except Exception as e:
                print(f"Erro ao carregar back shiny {pokemon_id}: {e}")

    def _format_filename_front_back(self, pokemon_id, shiny=False):
        """Formata nome do arquivo para front/back (mantém original)"""
        filename = str(pokemon_id)
        if shiny:
            filename += "s"
        return filename

    # ===== MÉTODOS PARA INMAP =====

    def get_inmap_animation(self, pokemon_id: int, shiny: bool = False) -> Dict:
        """
        Retorna animações COMPLETAS com 8 direções.
        Usa os dados já carregados pelo SpriteLoader.
        """
        cache_key = f"{pokemon_id}_{shiny}"
        if cache_key in self.inmap_animations_cache:
            return self.inmap_animations_cache[cache_key]

        # Carrega os dados completos do SpriteLoader (já tem 8 direções)
        sprites_data = self.sprite_manager.loader.load_pokemon_sprites(pokemon_id, shiny)

        # Pega a animação Walk (ou a primeira disponível)
        animations = sprites_data.get("animations", {})
        walk_frames = animations.get("walk", {})

        # Se não tem Walk, tenta a primeira animação disponível
        if not walk_frames and animations:
            walk_frames = next(iter(animations.values()))

        # Remove o metadado se existir
        if '_metadata' in walk_frames:
            del walk_frames['_metadata']

        # AGORA RETORNA AS 8 DIREÇÕES DIRETAMENTE
        # Garante que todas as 8 direções estão presentes (mesmo que vazias)
        all_directions = [
            "down", "down-right", "right", "up-right",
            "up", "up-left", "left", "down-left"
        ]

        result = {}
        for direction in all_directions:
            result[direction] = walk_frames.get(direction, [])

        # SE SÓ TEM UMA DIREÇÃO, REPLICA PARA TODAS
        # Isso acontece quando o spritesheet tem apenas 1 linha (direção única)
        non_empty = [d for d, frames in result.items() if frames]

        if len(non_empty) == 1:
            # Só tem uma direção com frames - replica para todas
            source_frames = result[non_empty[0]]
            for direction in all_directions:
                if direction != non_empty[0]:
                    result[direction] = source_frames.copy()
            print(f"[POKEDEX] {pokemon_id}: animação de direção única replicada para 8 direções")
        elif len(non_empty) == 4 and set(non_empty) == {"down", "right", "up", "left"}:
            # Tem 4 direções principais - replica para diagonais
            diagonal_map = {
                "down-right": "right",
                "up-right": "right",
                "up-left": "left",
                "down-left": "left"
            }
            for diag, src in diagonal_map.items():
                if src in result and result[src]:
                    result[diag] = result[src].copy()
            print(f"[POKEDEX] {pokemon_id}: 4 direções replicadas para diagonais")

        self.inmap_animations_cache[cache_key] = result

        print(f"[POKEDEX] get_inmap_animation: {pokemon_id} - "
              f"direções com frames: {[d for d in all_directions if result[d]]}")
        return result
    def get_pokemon_animations_info(self, pokemon_id: int, shiny: bool = False) -> Dict:
        cache_key = f"{pokemon_id}_{shiny}_info"
        if cache_key in self.pokemon_animations_info:
            return self.pokemon_animations_info[cache_key]

        raw_data = self.sprite_manager.loader.load_pokemon_sprites(pokemon_id, shiny)

        animation_details = {}
        for anim_name, anim_frames in raw_data.get("animations", {}).items():
            directions_info = {}
            total_frames = 0

            for direction, frames in anim_frames.items():
                directions_info[direction] = len(frames)
                total_frames += len(frames)

            xml_info = raw_data.get("anim_data", {}).get(anim_name.capitalize(), {})

            animation_details[anim_name] = {
                "directions": directions_info,
                "total_frames": total_frames,
                "num_directions": len(anim_frames),
                "frame_width": xml_info.get("frame_width", 32),
                "frame_height": xml_info.get("frame_height", 32),
                "durations": xml_info.get("durations", []),
                "has_animation": total_frames > 0
            }

        result = {
            "available_animations": raw_data.get("available_animations", []),
            "animation_details": animation_details,
            "raw_data": raw_data,
            "has_animations": len(animation_details) > 0
        }

        self.pokemon_animations_info[cache_key] = result
        return result

    def get_all_animations(self, pokemon_id: int, shiny: bool = False) -> List[str]:
        info = self.get_pokemon_animations_info(pokemon_id, shiny)
        return info.get("available_animations", [])

    def has_animation(self, pokemon_id: int, animation_name: str, shiny: bool = False) -> bool:
        animations = self.get_all_animations(pokemon_id, shiny)
        return animation_name.lower() in [a.lower() for a in animations]

    def get_animation_frames(self, pokemon_id: int, animation_name: str,
                             direction: str = "down", shiny: bool = False) -> List[pygame.Surface]:
        return self.sprite_manager.get_animation_frames(pokemon_id, shiny, animation_name, direction)

    def get_animation_durations(self, pokemon_id: int, animation_name: str, shiny: bool = False) -> List[int]:
        info = self.get_pokemon_animations_info(pokemon_id, shiny)
        anim_details = info.get("animation_details", {}).get(animation_name.lower(), {})
        return anim_details.get("durations", [])

    def get_map_sprite_size(self, pokemon_id: int, shiny: bool = False) -> int:
        return self.sprite_manager.get_sprite_size(pokemon_id, shiny)

    def get_raw_inmap_data(self, pokemon_id: int, shiny: bool = False) -> Dict:
        return self.sprite_manager.loader.load_pokemon_sprites(pokemon_id, shiny)

    # ===== MÉTODOS EXISTENTES (MANTIDOS) =====

    def _cache_base_speed_limits(self):
        """Calcula e armazena os valores mínimo e máximo de base speed"""
        if not self.pokemon_data:
            self.min_base_speed = 0
            self.max_base_speed = 1
            return

        base_speeds = [data["base_stats"]["speed"] for data in self.pokemon_data.values()]
        self.min_base_speed = min(base_speeds)
        self.max_base_speed = max(base_speeds)

    def get_sprite(self, pokemon_id, sprite_type="front", shiny=False, direction="down", frame=0):
        if sprite_type == "front":
            cache = self.front_shiny_sprites if shiny else self.front_sprites
            return cache.get(pokemon_id, self._create_placeholder(pokemon_id, "front", 96))

        elif sprite_type == "back":
            cache = self.back_shiny_sprites if shiny else self.back_sprites
            return cache.get(pokemon_id, self._create_placeholder(pokemon_id, "back", 96))

        elif sprite_type == "inmap":
            anim = self.get_inmap_animation(pokemon_id, shiny)
            if direction in anim and anim[direction]:
                frames = anim[direction]
                if 0 <= frame < len(frames):
                    return frames[frame]
            return self._create_placeholder(pokemon_id, "inmap", 32)

        return self._create_placeholder(pokemon_id, "front", 96)

    def _create_placeholder(self, pokemon_id, sprite_type="front", size=96):
        sprite = pygame.Surface((size, size), pygame.SRCALPHA)
        color = self._get_placeholder_color(pokemon_id)

        pygame.draw.rect(sprite, color, (0, 0, size, size))
        pygame.draw.rect(sprite, (100, 100, 100), (0, 0, size, size), 2)

        font = pygame.font.Font(None, size // 2)
        text = font.render(f"?", True, (255, 255, 255))
        text_rect = text.get_rect(center=(size // 2, size // 2))
        sprite.blit(text, text_rect)

        type_font = pygame.font.Font(None, size // 4)
        type_text = type_font.render(sprite_type[0].upper(), True, (200, 200, 200))
        type_rect = type_text.get_rect(topright=(size - 5, 5))
        sprite.blit(type_text, type_rect)

        return sprite

    def get_pokemon(self, pokemon_id):
        return self.pokemon_data.get(pokemon_id, None)

    def get_name(self, pokemon_id):
        pokemon = self.get_pokemon(pokemon_id)
        return pokemon["name"] if pokemon else f"Pokemon {pokemon_id}"

    def get_types(self, pokemon_id):
        pokemon = self.get_pokemon(pokemon_id)
        return pokemon["types"] if pokemon else ["normal"]

    def get_base_stats(self, pokemon_id):
        pokemon = self.get_pokemon(pokemon_id)
        return pokemon["base_stats"] if pokemon else {
            "hp": 50, "attack": 50, "defense": 50,
            "special_attack": 50, "special_defense": 50, "speed": 50
        }

    def get_ev_yield(self, pokemon_id: int) -> Dict[str, int]:
        pokemon = self.get_pokemon(pokemon_id)
        if pokemon and "ev_yield" in pokemon:
            return pokemon["ev_yield"]
        return {"hp": 1, "attack": 0, "defense": 0,
                "special_attack": 0, "special_defense": 0, "speed": 0}

    def _get_placeholder_color(self, pokemon_id):
        colors = [
            (255, 99, 71), (135, 206, 235), (144, 238, 144),
            (255, 215, 0), (221, 160, 221), (255, 182, 193)
        ]
        return colors[pokemon_id % len(colors)]

    def get_type_color(self, type_name):
        return self.type_colors.get(type_name.lower(), (150, 150, 150))

    def calculate_stats(self, pokemon_id, level, ivs=None, evs=None):
        base = self.get_base_stats(pokemon_id)

        if ivs is None:
            ivs = {"hp": 0, "attack": 0, "defense": 0,
                   "special_attack": 0, "special_defense": 0, "speed": 0}
        if evs is None:
            evs = {"hp": 0, "attack": 0, "defense": 0,
                   "special_attack": 0, "special_defense": 0, "speed": 0}

        return self.calculate_stats_with_base(base, level, ivs, evs)

    def calculate_stats_with_base(self, base_stats: dict, level: int, ivs: dict, evs: dict) -> dict:
        EV_DIVISOR = 8

        stats = {}
        stats["hp"] = int(((2 * base_stats["hp"] + ivs["hp"] + (evs["hp"] // EV_DIVISOR)) * level) / 100) + level + 10

        for stat in ["attack", "defense", "special_attack", "special_defense", "speed"]:
            stats[stat] = int(((2 * base_stats[stat] + ivs[stat] + (evs[stat] // EV_DIVISOR)) * level) / 100) + 5

        return stats

    def search_pokemon(self, query):
        results = []
        query = str(query).lower()

        for pid, data in self.pokemon_data.items():
            if query in str(pid) or query in data["name"].lower():
                results.append((pid, data["name"]))

        return results

    def get_all_ids(self):
        return sorted(self.pokemon_data.keys())

    def _load_fallback_data(self):
        print("Carregando dados de fallback...")
        for i in range(1, self.max_id + 1):
            self.pokemon_data[i] = {
                "id": i,
                "name": f"Pokemon{i}",
                "is_legendary": False,
                "is_mythical": False,
                "types": ["normal"],
                "base_stats": {
                    "hp": 50, "attack": 50, "defense": 50,
                    "special_attack": 50, "special_defense": 50, "speed": 50
                },
                "ev_yield": {"hp": 0, "attack": 0, "defense": 0,
                             "special_attack": 0, "special_defense": 0, "speed": 0},
                "catch_rate": 120,
                "evolution": {"EvolveTo": "none", "lvlMin": "none", "method": "none"}
            }
        self._cache_base_speed_limits()

    # ===== MÉTODOS PARA RETRATOS (PORTRAITS) =====

    def get_portrait(self, pokemon_id: int, expression: str = "normal", shiny: bool = False) -> Optional[
        pygame.Surface]:
        if not hasattr(self, '_portrait_cache'):
            self._portrait_cache = {}

        cache_key = f"{pokemon_id}_{expression}_{shiny}"
        if cache_key in self._portrait_cache:
            return self._portrait_cache[cache_key]

        base_path = Path(__file__).parent.parent.parent / "res" / "PokemonSprites" / "Portrait"
        pokemon_dir = f"{pokemon_id:04d}"

        if shiny:
            portrait_path = base_path / pokemon_dir / "0000" / "0001" / f"{expression}.png"
        else:
            portrait_path = base_path / pokemon_dir / f"{expression}.png"

        portrait = None
        if portrait_path.exists():
            try:
                portrait = pygame.image.load(str(portrait_path)).convert_alpha()
                if portrait.get_width() != 40 or portrait.get_height() != 40:
                    portrait = pygame.transform.scale(portrait, (40, 40))
            except Exception as e:
                print(f"Erro ao carregar portrait {portrait_path}: {e}")

        if portrait is None and expression != "normal":
            portrait = self.get_portrait(pokemon_id, "normal", shiny)

        if portrait is None:
            portrait = self._create_portrait_placeholder(pokemon_id, expression)

        self._portrait_cache[cache_key] = portrait
        return portrait

    def _create_portrait_placeholder(self, pokemon_id: int, expression: str) -> pygame.Surface:
        portrait = pygame.Surface((40, 40), pygame.SRCALPHA)
        color = self._get_placeholder_color(pokemon_id)
        pygame.draw.rect(portrait, color, (0, 0, 40, 40))
        pygame.draw.rect(portrait, (100, 100, 100), (0, 0, 40, 40), 2)

        font = pygame.font.Font(None, 16)
        expr_text = expression[0].upper() if expression else "?"
        text = font.render(expr_text, True, (255, 255, 255))
        text_rect = text.get_rect(center=(20, 20))
        portrait.blit(text, text_rect)

        return portrait

    def get_portraits_info(self, pokemon_id: int, shiny: bool = False) -> Dict[str, bool]:
        result = {}
        expressions = ["normal", "happy", "angry"]

        base_path = Path(__file__).parent.parent.parent / "res" / "PokemonSprites" / "Portrait"
        pokemon_dir = f"{pokemon_id:04d}"

        for expr in expressions:
            if shiny:
                path = base_path / pokemon_dir / "0000" / "0001" / f"{expr}.png"
            else:
                path = base_path / pokemon_dir / f"{expr}.png"
            result[expr] = path.exists()

        return result

    def get_animation_directions(self, pokemon_id: int, animation_name: str, shiny: bool = False) -> List[str]:
        raw_data = self.get_raw_inmap_data(pokemon_id, shiny)
        animations = raw_data.get("animations", {})
        anim_frames = animations.get(animation_name.lower(), {})
        return list(anim_frames.keys()) if anim_frames else []

    def is_single_direction_animation(self, pokemon_id: int, animation_name: str, shiny: bool = False) -> bool:
        directions = self.get_animation_directions(pokemon_id, animation_name, shiny)
        return len(directions) == 1