# src/data/item_bag_catalog.py

import os
import pygame
import sys
from pathlib import Path


class ItemBagCatalog:
    """Catálogo de itens da mochila - similar ao Pokedex"""

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

        # Cache de sprites (serão carregados sob demanda)
        self.sprites = {}  # Sprites normais 32x32
        self.sprites_scaled = {}  # Sprites escalados para UI
        self._sprites_loaded = False  # Flag para controle

        # Define o caminho base dos sprites
        if getattr(sys, 'frozen', False):
            self.root_dir = os.path.dirname(sys.executable)
        else:
            self.root_dir = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))

        self.base_path = os.path.join(self.root_dir, "res", "PokemonSprites", "items")

        # Catálogo de itens (apenas metadados, sem carregar sprites)
        self.items = {
            # Pokébolas
            "pokeball": {
                "id": "pokeball",
                "name": "POKEBALL",
                "sprite_path": os.path.join(self.base_path, "pokeballs", "POKEBALL.png"),
                "description": "Uma bola para capturar Pokémon selvagens",
                "category": "pokeball",
                "usable_in_battle": True,
                "usable_on_map": True,
                "effect": "capture",
                "effect_value": 1.0,
                "price": 200
            },
            "greatball": {
                "id": "greatball",
                "name": "GREATBALL",
                "sprite_path": os.path.join(self.base_path, "pokeballs", "GREATBALL.png"),
                "description": "Captura Pokémon selvagens com 1,5 vezes a taxa de captura de uma Poké Bola.",
                "category": "pokeball",
                "usable_in_battle": True,
                "usable_on_map": True,
                "effect": "capture",
                "effect_value": 1.5,
                "price": 600
            },
            # Poções
            "potion": {
                "id": "potion",
                "name": "POTION",
                "sprite_path": os.path.join(self.base_path, "medicine", "potion.png"),
                "description": "Recupera 20 HP de um Pokémon",
                "category": "medicine",
                "usable_in_battle": True,
                "usable_on_map": True,
                "effect": "heal",
                "effect_value": 20,
                "price": 200
            },
            # PP Items
            "pp_up": {
                "id": "pp_up",
                "name": "PP UP",
                "sprite_path": os.path.join(self.base_path, "medicine", "PPUP.png"),
                "description": "Aumenta o PP de todos movimento em 20% do máximo.",
                "category": "medicine",
                "usable_in_battle": True,
                "usable_on_map": True,
                "effect": "pp_restore",
                "effect_value": 0.2,  # 20% do max_pp
                "price": 100
            },
            "pp_max": {
                "id": "pp_max",
                "name": "PP MAX",
                "sprite_path": os.path.join(self.base_path, "medicine", "PPMAX.png"),
                "description": "Aumenta o PP de todos movimento ao seu valor máximo.",
                "category": "medicine",
                "usable_in_battle": True,
                "usable_on_map": True,
                "effect": "pp_restore",
                "effect_value": 1.0,  # 100% do max_pp
                "price": 450
            },
            # Pedras de evolição
            "firestone": {
                "id": "firestone",
                "name": "FIRESTONE",
                "sprite_path": os.path.join(self.base_path, "evo-stones", "FIRESTONE.png"),
                "description": "Evolui certas espécies de Pokémon.",
                "category": "items",
                "usable_in_battle": True,
                "usable_on_map": True,
                "effect": "evolution",
                "effect_value": 0,
                "price": 1200
            },"leafstone": {
                "id": "leafstone",
                "name": "LEAFSTONE",
                "sprite_path": os.path.join(self.base_path, "evo-stones", "LEAFSTONE.png"),
                "description": "Evolui certas espécies de Pokémon.",
                "category": "items",
                "usable_in_battle": True,
                "usable_on_map": True,
                "effect": "evolution",
                "effect_value": 0,
                "price": 1200
            },"moonstone": {
                "id": "moonstone",
                "name": "MOONSTONE",
                "sprite_path": os.path.join(self.base_path, "evo-stones", "MOONSTONE.png"),
                "description": "Evolui certas espécies de Pokémon.",
                "category": "items",
                "usable_in_battle": True,
                "usable_on_map": True,
                "effect": "evolution",
                "effect_value": 0,
                "price": 1200
            },"thunderstone": {
                "id": "thunderstone",
                "name": "THUNDERSTONE",
                "sprite_path": os.path.join(self.base_path, "evo-stones", "THUNDERSTONE.png"),
                "description": "Evolui certas espécies de Pokémon.",
                "category": "items",
                "usable_in_battle": True,
                "usable_on_map": True,
                "effect": "evolution",
                "effect_value": 0,
                "price": 1200
            },"waterstone": {
                "id": "waterstone",
                "name": "WATERSTONE",
                "sprite_path": os.path.join(self.base_path, "evo-stones", "WATERSTONE.png"),
                "description": "Evolui certas espécies de Pokémon.",
                "category": "items",
                "usable_in_battle": True,
                "usable_on_map": True,
                "effect": "evolution",
                "effect_value": 0,
                "price": 1200
            },
            # TMs/HMs
            "tm_normal_tackle": {
                "id": "tm_normal_tackle",
                "name": "TM01 - Tackle",
                "sprite_path": os.path.join(self.base_path, "tm-hm", "machine_NORMAL.png"),
                "description": "Ensina Tackle a um Pokémon. Um ataque físico básico.",
                "category": "tm",
                "usable_in_battle": False,
                "usable_on_map": True,
                "effect": "teach_move",
                "effect_value": "tackle",
                "price": 500  # Preço reduzido para TM básica
            },
            "tm_bug_stringshot": {
                "id": "tm_bug_stringshot",
                "name": "TM02 - String Shot",
                "sprite_path": os.path.join(self.base_path, "tm-hm", "machine_BUG.png"),
                "description": "Ensina String Shot a um Pokémon. Reduz a velocidade do oponente.",
                "category": "tm",
                "usable_in_battle": False,
                "usable_on_map": True,
                "effect": "teach_move",
                "effect_value": "string-shot",
                "price": 500
            },
            "tm_mega_punch": {
                "id": "tm_mega_punch",
                "name": "TM03 - Mega Punch",
                "sprite_path": os.path.join(self.base_path, "tm-hm", "machine_NORMAL.png"),
                "description": "A powerful punch thrown very hard.",
                "category": "tm",
                "usable_in_battle": False,
                "usable_on_map": True,
                "effect": "teach_move",
                "effect_value": "mega-punch",
                "price": 1000
            },
        }

        # Placeholders serão criados sob demanda
        self.placeholders = {}

        # Não carrega sprites aqui - será feito sob demanda

    def _ensure_pygame_ready(self):
        """Garante que o pygame está inicializado antes de criar superfícies"""
        if not pygame.get_init():
            pygame.init()
        if not pygame.font.get_init():
            pygame.font.init()

    def _load_sprite(self, item_id):
        """Carrega um sprite específico sob demanda"""
        if item_id in self.sprites:
            return

        self._ensure_pygame_ready()

        item_data = self.items.get(item_id)
        if not item_data:
            return

        sprite_path = item_data["sprite_path"]

        if os.path.exists(sprite_path):
            try:
                # Carrega o sprite
                sprite = pygame.image.load(sprite_path).convert_alpha()
                self.sprites[item_id] = sprite

                # Cria versão escalada
                scaled = pygame.transform.scale(sprite, (48, 48))
                self.sprites_scaled[item_id] = scaled

                print(f"✓ {item_data['name']}: Carregado sob demanda")
            except Exception as e:
                print(f"✗ Erro ao carregar {item_data['name']}: {e}")
                self._create_placeholder(item_id)
        else:
            print(f"✗ {item_data['name']}: Arquivo não encontrado - {sprite_path}")
            self._create_placeholder(item_id)

    def _create_placeholder(self, item_id):
        """Cria um placeholder para o item (agora com pygame inicializado)"""
        self._ensure_pygame_ready()

        size = 32
        sprite = pygame.Surface((size, size), pygame.SRCALPHA)

        # Cor baseada na categoria
        item_data = self.items.get(item_id, {})
        category = item_data.get("category", "")

        if category == "pokeball":
            color = (255, 0, 0)  # Vermelho para pokebolas
        elif category == "medicine":
            color = (0, 255, 0)  # Verde para poções
        else:
            color = (128, 128, 128)  # Cinza para outros

        # Desenha um círculo
        pygame.draw.circle(sprite, color, (size // 2, size // 2), size // 2 - 2)
        pygame.draw.circle(sprite, (255, 255, 255), (size // 2, size // 2), size // 2 - 2, 2)

        # Letra do item
        font = pygame.font.Font(None, 20)
        letter = item_id[0].upper()
        text = font.render(letter, True, (255, 255, 255))
        text_rect = text.get_rect(center=(size // 2, size // 2))
        sprite.blit(text, text_rect)

        self.sprites[item_id] = sprite
        self.sprites_scaled[item_id] = pygame.transform.scale(sprite, (48, 48))
        self.placeholders[item_id] = True

    def get_sprite(self, item_id, scaled=False):
        """Retorna o sprite do item (carrega sob demanda)"""
        if item_id not in self.sprites:
            self._load_sprite(item_id)

        if scaled:
            return self.sprites_scaled.get(item_id, self.sprites_scaled.get("pokeball"))
        return self.sprites.get(item_id, self.sprites.get("pokeball"))

    def get_item(self, item_id):
        """Retorna dados do item"""
        return self.items.get(item_id, self.items.get("pokeball"))

    def get_all_items(self):
        """Retorna todos os itens"""
        return list(self.items.values())

    def get_items_by_category(self, category):
        """Retorna itens de uma categoria"""
        return [item for item in self.items.values() if item["category"] == category]

    def get_pokeballs(self):
        """Retorna apenas pokebolas"""
        return self.get_items_by_category("pokeball")

    def get_medicines(self):
        """Retorna apenas poções/remédios"""
        return self.get_items_by_category("medicine")


# Instância global
item_bag_catalog = ItemBagCatalog()