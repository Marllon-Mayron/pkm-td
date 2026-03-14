# src/data/pokedex.py
import json
import os
import pygame
from pathlib import Path


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

        # Cache de sprites
        self.front_sprites = {}          # 96x96 front
        self.back_sprites = {}           # 96x96 back
        self.front_shiny_sprites = {}    # 96x96 front shiny
        self.back_shiny_sprites = {}     # 96x96 back shiny
        self.inmap_spritesheets = {}     # 256x256 spritesheets (4x4)
        self.inmap_frames = {}           # Frames individuais extraídos

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
        self.load_all_sprites()

    def load_pokemon_data(self):
        """Carrega dados do arquivo JSON"""
        try:
            # Caminho relativo ao arquivo atual
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

        except Exception as e:
            print(f"Erro ao carregar Pokémon data: {e}")
            self._load_fallback_data()

    def _format_filename(self, pokemon_id, shiny=False):
        """Formata nome do arquivo com 3 dígitos"""
        if pokemon_id < 10:
            filename = f"00{pokemon_id}"
        elif pokemon_id < 100:
            filename = f"0{pokemon_id}"
        else:
            filename = str(pokemon_id)

        if shiny:
            filename += "s"

        return filename

    def load_all_sprites(self):
        """Carrega todos os sprites de uma vez"""
        base_path = Path(__file__).parent.parent.parent / "res" / "PokemonSprites"

        # Verifica se o diretório base existe
        if not base_path.exists():
            print(f"Diretório de sprites não encontrado: {base_path}")
            return

        # Carrega sprites para cada Pokémon
        for pokemon_id in range(1, self.max_id + 1):
            # Front sprites
            self._load_front_sprite(pokemon_id, base_path)
            # Back sprites
            self._load_back_sprite(pokemon_id, base_path)
            # InMap spritesheets
            self._load_inmap_spritesheet(pokemon_id, base_path)

        print(f"Sprites carregados: Front({len(self.front_sprites)}), "
              f"Back({len(self.back_sprites)}), InMap({len(self.inmap_spritesheets)})")

    def _load_front_sprite(self, pokemon_id, base_path):
        """Carrega sprite frontal (96x96)"""
        # Normal
        filename = self._format_filename(pokemon_id, shiny=False)
        path = base_path / "front" / f"{filename}.png"

        if path.exists():
            try:
                sprite = pygame.image.load(str(path)).convert_alpha()
                self.front_sprites[pokemon_id] = sprite
            except Exception as e:
                print(f"Erro ao carregar front {pokemon_id}: {e}")

        # Shiny
        filename_shiny = self._format_filename(pokemon_id, shiny=True)
        path_shiny = base_path / "front" / f"{filename_shiny}.png"

        if path_shiny.exists():
            try:
                sprite = pygame.image.load(str(path_shiny)).convert_alpha()
                self.front_shiny_sprites[pokemon_id] = sprite
            except Exception as e:
                print(f"Erro ao carregar front shiny {pokemon_id}: {e}")

    def _load_back_sprite(self, pokemon_id, base_path):
        """Carrega sprite traseiro (96x96)"""
        # Normal
        filename = self._format_filename(pokemon_id, shiny=False)
        path = base_path / "back" / f"{filename}.png"

        if path.exists():
            try:
                sprite = pygame.image.load(str(path)).convert_alpha()
                self.back_sprites[pokemon_id] = sprite
            except Exception as e:
                print(f"Erro ao carregar back {pokemon_id}: {e}")

        # Shiny
        filename_shiny = self._format_filename(pokemon_id, shiny=True)
        path_shiny = base_path / "back" / f"{filename_shiny}.png"

        if path_shiny.exists():
            try:
                sprite = pygame.image.load(str(path_shiny)).convert_alpha()
                self.back_shiny_sprites[pokemon_id] = sprite
            except Exception as e:
                print(f"Erro ao carregar back shiny {pokemon_id}: {e}")

    def _load_inmap_spritesheet(self, pokemon_id, base_path):
        """Carrega spritesheet InMap (256x256, 4x4 grid)"""
        filename = self._format_filename(pokemon_id, shiny=False)
        path = base_path / "InMaps" / f"{filename}.png"

        if path.exists():
            try:
                spritesheet = pygame.image.load(str(path)).convert_alpha()
                self.inmap_spritesheets[pokemon_id] = spritesheet

                # Extrai frames individuais (64x64 cada)
                # Organização: 4 colunas x 4 linhas
                # Linhas: Down, Left, Right, Up
                frames = {
                    "down": [],   # Linha 0
                    "left": [],   # Linha 1
                    "right": [],  # Linha 2
                    "up": []      # Linha 3
                }

                frame_size = 64  # 256/4 = 64

                for row in range(4):
                    direction = ["down", "left", "right", "up"][row]
                    for col in range(4):
                        # Recorta o frame
                        rect = pygame.Rect(col * frame_size, row * frame_size, frame_size, frame_size)
                        frame = spritesheet.subsurface(rect)
                        frames[direction].append(frame)

                self.inmap_frames[pokemon_id] = frames

            except Exception as e:
                print(f"Erro ao carregar InMap {pokemon_id}: {e}")

        # Versão shiny
        filename_shiny = self._format_filename(pokemon_id, shiny=True)
        path_shiny = base_path / "InMaps" / f"{filename_shiny}.png"

        if path_shiny.exists():
            try:
                spritesheet = pygame.image.load(str(path_shiny)).convert_alpha()
                # Podemos armazenar separadamente ou no mesmo dict com chave diferente
                # Por simplicidade, vamos sobrescrever? Melhor não
                # Vamos criar um dict separado para shiny
                if not hasattr(self, 'inmap_shiny_spritesheets'):
                    self.inmap_shiny_spritesheets = {}
                    self.inmap_shiny_frames = {}

                self.inmap_shiny_spritesheets[pokemon_id] = spritesheet

                # Extrai frames
                frames = {"down": [], "left": [], "right": [], "up": []}
                frame_size = 64

                for row in range(4):
                    direction = ["down", "left", "right", "up"][row]
                    for col in range(4):
                        rect = pygame.Rect(col * frame_size, row * frame_size, frame_size, frame_size)
                        frame = spritesheet.subsurface(rect)
                        frames[direction].append(frame)

                self.inmap_shiny_frames[pokemon_id] = frames

            except Exception as e:
                print(f"Erro ao carregar InMap shiny {pokemon_id}: {e}")

    def get_sprite(self, pokemon_id, sprite_type="front", shiny=False, direction="down", frame=0):
        """
        Retorna sprite do Pokémon

        Args:
            pokemon_id: ID do Pokémon
            sprite_type: "front", "back", ou "inmap"
            shiny: True para versão shiny
            direction: para inmap: "down", "left", "right", "up"
            frame: para inmap: 0-3 (frame de animação)
        """
        if sprite_type == "front":
            cache = self.front_shiny_sprites if shiny else self.front_sprites
            return cache.get(pokemon_id, self._create_placeholder(pokemon_id, "front"))

        elif sprite_type == "back":
            cache = self.back_shiny_sprites if shiny else self.back_sprites
            return cache.get(pokemon_id, self._create_placeholder(pokemon_id, "back"))

        elif sprite_type == "inmap":
            if shiny and hasattr(self, 'inmap_shiny_frames'):
                frames_dict = self.inmap_shiny_frames.get(pokemon_id)
            else:
                frames_dict = self.inmap_frames.get(pokemon_id)

            if frames_dict and direction in frames_dict:
                frames_list = frames_dict[direction]
                if 0 <= frame < len(frames_list):
                    return frames_list[frame]

            # Fallback para placeholder
            return self._create_placeholder(pokemon_id, "inmap", 64)

        return self._create_placeholder(pokemon_id, "front")

    def _create_placeholder(self, pokemon_id, sprite_type="front", size=96):
        """Cria sprite placeholder"""
        sprite = pygame.Surface((size, size), pygame.SRCALPHA)
        color = self._get_placeholder_color(pokemon_id)

        # Fundo
        pygame.draw.rect(sprite, color, (0, 0, size, size))
        pygame.draw.rect(sprite, (100, 100, 100), (0, 0, size, size), 2)

        # Texto identificador
        font = pygame.font.Font(None, size // 2)
        text = font.render(f"?", True, (255, 255, 255))
        text_rect = text.get_rect(center=(size // 2, size // 2))
        sprite.blit(text, text_rect)

        # Tipo do sprite
        type_font = pygame.font.Font(None, size // 4)
        type_text = type_font.render(sprite_type[0].upper(), True, (200, 200, 200))
        type_rect = type_text.get_rect(topright=(size - 5, 5))
        sprite.blit(type_text, type_rect)

        return sprite

    def get_inmap_animation(self, pokemon_id, shiny=False):
        """Retorna dicionário com todos os frames de animação InMap"""
        if shiny and hasattr(self, 'inmap_shiny_frames'):
            return self.inmap_shiny_frames.get(pokemon_id, self.inmap_frames.get(pokemon_id))
        return self.inmap_frames.get(pokemon_id)

    # ... (resto dos métodos existentes permanecem iguais)
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
        """
        Calcula stats reais baseado em level, IVs e EVs
        Fórmula simplificada dos jogos principais
        """
        base = self.get_base_stats(pokemon_id)

        if ivs is None:
            ivs = {"hp": 15, "attack": 15, "defense": 15,
                   "special_attack": 15, "special_defense": 15, "speed": 15}

        if evs is None:
            evs = {"hp": 0, "attack": 0, "defense": 0,
                   "special_attack": 0, "special_defense": 0, "speed": 0}

        stats = {}

        # HP tem fórmula diferente
        stats["hp"] = int(((2 * base["hp"] + ivs["hp"] + (evs["hp"] // 4)) * level) / 100) + level + 10

        # Outros stats
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