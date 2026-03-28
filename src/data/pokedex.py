# src/data/pokedex.py
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

        # NOVO: Usa o gerenciador de sprites APENAS para InMap
        self.sprite_manager = PokemonSpriteManager()

        # Cache de sprites front/back (mantém o sistema antigo)
        self.front_sprites = {}
        self.back_sprites = {}
        self.front_shiny_sprites = {}
        self.back_shiny_sprites = {}

        # Cache para sprites InMap (novo sistema)
        self.inmap_animations_cache = {}  # Cache para animações carregadas

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

        self.load_pokemon_data()
        self.load_sprites()  # Carrega front e back (mantém igual)

    def load_pokemon_data(self):
        """Carrega dados do arquivo JSON"""
        try:
            json_path = Path(__file__).parent.parent.parent / "res" / "json" / "pokemon_data.json"

            with open(json_path, 'r', encoding='utf-8') as file:
                data = json.load(file)

            for pokemon in data:
                pokemon_id = pokemon["id"]
                self.pokemon_data[pokemon_id] = {
                    "id": pokemon_id,
                    "name": pokemon["name"],
                    "is_legendary": pokemon["is_legendary"],
                    "is_mythical": pokemon["is_mythical"],
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
                    "catch_rate": pokemon["rate"],
                    "evolution": pokemon["Evolucao"]
                }

            print(f"Carregados {len(self.pokemon_data)} Pokémon do JSON")

            self._cache_base_speed_limits()

        except Exception as e:
            print(f"Erro ao carregar Pokémon data: {e}")
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

    # ===== MÉTODOS PARA INMAP (NOVO SISTEMA) =====

    def get_inmap_animation(self, pokemon_id: int, shiny: bool = False) -> Dict:
        """
        Retorna animações InMap no formato compatível com 4 direções
        """
        cache_key = f"{pokemon_id}_{shiny}"
        if cache_key in self.inmap_animations_cache:
            return self.inmap_animations_cache[cache_key]

        # Carrega do novo sistema
        animation = self.sprite_manager.get_inmap_animation(pokemon_id, shiny)
        self.inmap_animations_cache[cache_key] = animation
        return animation

    def get_map_sprite_size(self, pokemon_id: int, shiny: bool = False) -> int:
        """Retorna o tamanho do sprite InMap"""
        return self.sprite_manager.get_sprite_size(pokemon_id, shiny)

    def get_raw_inmap_data(self, pokemon_id: int, shiny: bool = False) -> Dict:
        """Retorna dados brutos do InMap (com 8 direções e AnimData)"""
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
        """
        Retorna sprite do Pokémon

        Args:
            pokemon_id: ID do Pokémon
            sprite_type: "front", "back", ou "inmap"
            shiny: True para versão shiny
            direction: para inmap: "down", "left", "right", "up"
            frame: para inmap: índice do frame
        """
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
        """Cria sprite placeholder"""
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
        """Retorna dados de um Pokémon pelo ID"""
        return self.pokemon_data.get(pokemon_id, None)

    def get_name(self, pokemon_id):
        """Retorna nome do Pokémon"""
        pokemon = self.get_pokemon(pokemon_id)
        return pokemon["name"] if pokemon else f"Pokemon {pokemon_id}"

    def get_types(self, pokemon_id):
        """Retorna tipos do Pokémon"""
        pokemon = self.get_pokemon(pokemon_id)
        return pokemon["types"] if pokemon else ["normal"]

    def get_base_stats(self, pokemon_id):
        """Retorna stats base do Pokémon"""
        pokemon = self.get_pokemon(pokemon_id)
        return pokemon["base_stats"] if pokemon else {
            "hp": 50, "attack": 50, "defense": 50,
            "special_attack": 50, "special_defense": 50, "speed": 50
        }

    def _get_placeholder_color(self, pokemon_id):
        """Gera cor baseada no ID para placeholder"""
        colors = [
            (255, 99, 71), (135, 206, 235), (144, 238, 144),
            (255, 215, 0), (221, 160, 221), (255, 182, 193)
        ]
        return colors[pokemon_id % len(colors)]

    def get_type_color(self, type_name):
        """Retorna cor associada ao tipo"""
        return self.type_colors.get(type_name.lower(), (150, 150, 150))

    def calculate_stats(self, pokemon_id, level, ivs=None, evs=None):
        """Calcula stats reais baseado em level, IVs e EVs"""
        base = self.get_base_stats(pokemon_id)

        if ivs is None:
            ivs = {"hp": 15, "attack": 15, "defense": 15,
                   "special_attack": 15, "special_defense": 15, "speed": 15}

        if evs is None:
            evs = {"hp": 0, "attack": 0, "defense": 0,
                   "special_attack": 0, "special_defense": 0, "speed": 0}

        stats = {}

        stats["hp"] = int(((2 * base["hp"] + ivs["hp"] + (evs["hp"] // 4)) * level) / 100) + level + 10

        for stat in ["attack", "defense", "special_attack", "special_defense", "speed"]:
            base_val = base[stat]
            iv_val = ivs[stat]
            ev_val = evs[stat]
            stats[stat] = int(((2 * base_val + iv_val + (ev_val // 4)) * level) / 100) + 5

        return stats

    def search_pokemon(self, query):
        """Busca Pokémon por nome ou ID"""
        results = []
        query = str(query).lower()

        for pid, data in self.pokemon_data.items():
            if query in str(pid) or query in data["name"].lower():
                results.append((pid, data["name"]))

        return results

    def get_all_ids(self):
        """Retorna todos os IDs disponíveis"""
        return sorted(self.pokemon_data.keys())

    def _load_fallback_data(self):
        """Dados de fallback em caso de erro"""
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
                "evolution": None
            }