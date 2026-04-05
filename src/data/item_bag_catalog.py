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
                "price": 200,
                "unlock_phase": None,  # None = sempre disponível
                "unlock_chapter": None  # compatibilidade com TMs
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
                "price": 600,
                "unlock_phase": None,
                "unlock_chapter": None
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
                "price": 200,
                "unlock_phase": None,
                "unlock_chapter": None
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
                "price": 100,
                "unlock_phase": "1-3",  # Desbloqueia após completar fase 1-3
                "unlock_chapter": None
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
                "price": 450,
                "unlock_phase": "2-1",  # Desbloqueia após completar fase 2-1
                "unlock_chapter": None
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
                "price": 1200,
                "unlock_phase": "1-5",  # Desbloqueia após fase 1-5
                "unlock_chapter": None
            },
            "leafstone": {
                "id": "leafstone",
                "name": "LEAFSTONE",
                "sprite_path": os.path.join(self.base_path, "evo-stones", "LEAFSTONE.png"),
                "description": "Evolui certas espécies de Pokémon.",
                "category": "items",
                "usable_in_battle": True,
                "usable_on_map": True,
                "effect": "evolution",
                "effect_value": 0,
                "price": 1200,
                "unlock_phase": "1-5",
                "unlock_chapter": None
            },
            "moonstone": {
                "id": "moonstone",
                "name": "MOONSTONE",
                "sprite_path": os.path.join(self.base_path, "evo-stones", "MOONSTONE.png"),
                "description": "Evolui certas espécies de Pokémon.",
                "category": "items",
                "usable_in_battle": True,
                "usable_on_map": True,
                "effect": "evolution",
                "effect_value": 0,
                "price": 1200,
                "unlock_phase": "1-5",
                "unlock_chapter": None
            },
            "thunderstone": {
                "id": "thunderstone",
                "name": "THUNDERSTONE",
                "sprite_path": os.path.join(self.base_path, "evo-stones", "THUNDERSTONE.png"),
                "description": "Evolui certas espécies de Pokémon.",
                "category": "items",
                "usable_in_battle": True,
                "usable_on_map": True,
                "effect": "evolution",
                "effect_value": 0,
                "price": 1200,
                "unlock_phase": "1-5",
                "unlock_chapter": None
            },
            "waterstone": {
                "id": "waterstone",
                "name": "WATERSTONE",
                "sprite_path": os.path.join(self.base_path, "evo-stones", "WATERSTONE.png"),
                "description": "Evolui certas espécies de Pokémon.",
                "category": "items",
                "usable_in_battle": True,
                "usable_on_map": True,
                "effect": "evolution",
                "effect_value": 0,
                "price": 1200,
                "unlock_phase": "1-5",
                "unlock_chapter": None
            },
            # TMs/HMs
            "tm_mega_punch": {
                "id": "tm_mega_punch",
                "name": "TM01 - Mega Punch",
                "sprite_path": os.path.join(self.base_path, "tm-hm", "machine_NORMAL.png"),
                "description": "A powerful punch thrown very hard.",
                "category": "tm",
                "usable_in_battle": False,
                "usable_on_map": True,
                "effect": "teach_move",
                "effect_value": "mega-punch",
                "price": 2000,
                "unlock_phase": "1-3",
                "unlock_chapter": None,
            },
            "tm_razor_wind": {
                "id": "tm_razor_wind",
                "name": "TM02 - Razor Wind",
                "sprite_path": os.path.join(self.base_path, "tm-hm", "machine_NORMAL.png"),
                "description": "1st turn: Prepare 2nd turn: Attack",
                "category": "tm",
                "usable_in_battle": False,
                "usable_on_map": True,
                "effect": "teach_move",
                "effect_value": "razor-wind",
                "price": 1500,
                "unlock_phase": "1-4",
                "unlock_chapter": None,
            },
            "tm_swords_dance": {
                "id": "tm_swords_dance",
                "name": "TM03 - Swords Dance",
                "sprite_path": os.path.join(self.base_path, "tm-hm", "machine_NORMAL.png"),
                "description": "A dance that in creases ATTACK.",
                "category": "tm",
                "usable_in_battle": False,
                "usable_on_map": True,
                "effect": "teach_move",
                "effect_value": "swords-dance",
                "price": 1500,
                "unlock_phase": "1-5",
                "unlock_chapter": None,
            },
            "tm_whirlwind": {
                "id": "tm_whirlwind",
                "name": "TM04 - Whirlwind",
                "sprite_path": os.path.join(self.base_path, "tm-hm", "machine_NORMAL.png"),
                "description": "Blows away the foe & ends battle.",
                "category": "tm",
                "usable_in_battle": False,
                "usable_on_map": True,
                "effect": "teach_move",
                "effect_value": "whirlwind",
                "price": 1500,
                "unlock_phase": "1-4",
                "unlock_chapter": None,
            },
            "tm_mega_kick": {
                "id": "tm_mega_kick",
                "name": "TM05 - Mega Kick",
                "sprite_path": os.path.join(self.base_path, "tm-hm", "machine_NORMAL.png"),
                "description": "The target is attacked by a kick launched with muscle-packed power.",
                "category": "tm",
                "usable_in_battle": False,
                "usable_on_map": True,
                "effect": "teach_move",
                "effect_value": "mega-kick",
                "price": 2000,
                "unlock_phase": "2-1",
                "unlock_chapter": None,
            },
            "tm_bubble_beam": {
                "id": "tm_bubble_beam",
                "name": "TM11 - Bubble Beam",
                "sprite_path": os.path.join(self.base_path, "tm-hm", "machine_WATER.png"),
                "description": "An attack that may lower SPEED.",
                "category": "tm",
                "usable_in_battle": False,
                "usable_on_map": True,
                "effect": "teach_move",
                "effect_value": "bubble-beam",
                "price": 2000,
                "unlock_phase": "2-8",
                "unlock_chapter": None,
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

    def get_unlock_phase(self, item_id):
        """Retorna a fase necessária para desbloquear o item"""
        item = self.items.get(item_id, {})
        # Suporta tanto unlock_phase quanto unlock_chapter (para compatibilidade)
        return item.get("unlock_phase") or item.get("unlock_chapter")

    def is_item_unlocked(self, item_id, progress_manager):
        """Verifica se o item está desbloqueado baseado no progresso do jogador"""
        unlock_phase = self.get_unlock_phase(item_id)

        # Se não tem requisito de desbloqueio, sempre disponível
        if unlock_phase is None:
            return True

        # Verifica se a fase foi completada
        return progress_manager.is_phase_completed(unlock_phase)


# Instância global
item_bag_catalog = ItemBagCatalog()