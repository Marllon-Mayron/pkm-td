# src/data/item_bag_catalog.py

import os
import sys
import pygame
from pathlib import Path

# Importa os paths centralizados
from src.config.paths import PROJECT_ROOT, ITEMS_PATH

# Importa o EffectFactory para pegar descrições dos moves
from src.battle.effects.effect_factory import EffectFactory

# Importa o MoveData para pegar descrições originais como fallback
from src.data.move_data import MoveData


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
        self.placeholders = {}  # Placeholders criados

        # Usa o PROJECT_ROOT e ITEMS_PATH do paths.py
        self.root_dir = PROJECT_ROOT
        self.base_path = ITEMS_PATH

        # Inicializa MoveData para fallback
        self.move_data = MoveData()

        # Debug dos caminhos
        print(f"[ItemBagCatalog] Root dir: {self.root_dir}")
        print(f"[ItemBagCatalog] Base path: {self.base_path}")
        print(f"[ItemBagCatalog] Base path existe: {self.base_path.exists()}")

        # Constrói o catálogo de itens com os paths corrigidos
        self.items = self._build_item_catalog()

        # Não carrega sprites aqui - será feito sob demanda

    def _get_move_description(self, move_name: str) -> str:
        """
        Obtém a descrição de um movimento.
        Prioridade:
        1. EffectFactory (descrições customizadas para o jogo)
        2. MoveData (descrições originais do JSON)
        3. Mensagem padrão
        """
        if not move_name:
            return "Ensina um movimento ao Pokémon"

        # Tenta 1: Buscar no EffectFactory
        effect = EffectFactory.create_effect(move_name)

        if effect and hasattr(effect, 'description') and effect.description:
            return effect.description

        # Tenta 2: Buscar diretamente na configuração do EffectFactory
        move_key = move_name.lower().replace(" ", "-").replace("'", "")
        config = EffectFactory.MOVE_EFFECTS.get(move_key)

        if config and config.get("description"):
            return config["description"]

        # Tenta 3: Buscar no MoveData (JSON original)
        try:
            move_info = self.move_data.get_move_info(move_name)
            if move_info and move_info.get("description"):
                original_desc = move_info["description"]
                # Limpa a descrição original se necessário
                if original_desc and original_desc != f"Usa {move_name}.":
                    return original_desc
        except Exception as e:
            print(f"[ItemBagCatalog] Erro ao buscar descrição no MoveData: {e}")

        # Fallback: Mensagem padrão
        move_display_name = move_name.replace("-", " ").title()
        return f"Ensina o movimento {move_display_name} ao Pokémon"

    def _build_item_catalog(self):
        """Constrói o catálogo de itens usando Path objects"""
        items = {}

        # Define subpastas
        pokeballs_path = self.base_path / "pokeballs"
        medicine_path = self.base_path / "medicine"
        evo_stones_path = self.base_path / "evo-stones"
        tm_hm_path = self.base_path / "tm-hm"
        battle_items_path = self.base_path / "battle-item"

        # ===== POKÉBOLAS =====
        items["pokeball"] = {
            "id": "pokeball",
            "name": "POKEBALL",
            "sprite_path": pokeballs_path / "POKEBALL.png",
            "description": "Uma bola para capturar Pokémon selvagens",
            "category": "pokeball",
            "usable_in_battle": True,
            "usable_on_map": True,
            "effect": "capture",
            "effect_value": 1.0,
            "price": 200,
            "unlock_phase": None,
            "unlock_chapter": None
        }
        items["greatball"] = {
            "id": "greatball",
            "name": "GREATBALL",
            "sprite_path": pokeballs_path / "GREATBALL.png",
            "description": "Captura Pokémon selvagens com 1,5 vezes a taxa de captura.",
            "category": "pokeball",
            "usable_in_battle": True,
            "usable_on_map": True,
            "effect": "capture",
            "effect_value": 1.5,
            "price": 600,
            "unlock_phase": "1-5",
            "unlock_chapter": None
        }
        items["ultraball"] = {
            "id": "ultraball",
            "name": "ULTRABALL",
            "sprite_path": pokeballs_path / "ULTRABALL.png",
            "description": "Captura Pokémon selvagens com 2 vezes a taxa de captura.",
            "category": "pokeball",
            "usable_in_battle": True,
            "usable_on_map": True,
            "effect": "capture",
            "effect_value": 2,
            "price": 1200,
            "unlock_phase": "3-4",
            "unlock_chapter": None
        }
        items["masterball"] = {
            "id": "masterball",
            "name": "MASTERBALL",
            "sprite_path": pokeballs_path / "MASTERBALL.png",
            "description": "Captura Pokémon selvagens com 100% a taxa de captura.",
            "category": "pokeball",
            "usable_in_battle": True,
            "usable_on_map": True,
            "effect": "capture",
            "effect_value": 2,
            "price": 10000,
            "unlock_phase": "4-5",
            "unlock_chapter": None
        }
        items["safariball"] = {
            "id": "safariball",
            "name": "SAFARIBALL",
            "sprite_path": pokeballs_path / "SAFARIBALL.png",
            "description": "Captura Pokémon selvagens com 1 vezes a taxa de captura.",
            "category": "pokeball",
            "usable_in_battle": True,
            "usable_on_map": True,
            "effect": "capture",
            "effect_value": 1,
            "price": 999999,
            "unlock_phase": "999-999",
            "unlock_chapter": None
        }
        # ===== POÇÕES =====
        items["potion"] = {
            "id": "potion",
            "name": "POTION",
            "sprite_path": medicine_path / "potion.png",
            "description": "Recupera 20 HP de um Pokémon",
            "category": "medicine",
            "usable_in_battle": True,
            "usable_on_map": True,
            "effect": "heal",
            "effect_value": 20,
            "price": 200,
            "unlock_phase": None,
            "unlock_chapter": None
        }
        items["superpotion"] = {
            "id": "superpotion",
            "name": "SUPERPOTION",
            "sprite_path": medicine_path / "superpotion.png",
            "description": "Recupera 50 HP de um Pokémon",
            "category": "medicine",
            "usable_in_battle": True,
            "usable_on_map": True,
            "effect": "heal",
            "effect_value": 50,
            "price": 450,
            "unlock_phase": "1-5",
            "unlock_chapter": None
        }
        items["hyperpotion"] = {
            "id": "hyperpotion",
            "name": "HYPERPOTION",
            "sprite_path": medicine_path / "hyperpotion.png",
            "description": "Recupera 200 HP de um Pokémon",
            "category": "medicine",
            "usable_in_battle": True,
            "usable_on_map": True,
            "effect": "heal",
            "effect_value": 200,
            "price": 1200,
            "unlock_phase": "3-4",
            "unlock_chapter": None
        }
        # ===== ITENS DE CURA DE STATUS =====
        items["antidote"] = {
            "id": "antidote",
            "name": "ANTIDOTE",
            "sprite_path": medicine_path / "antidote.png",
            "description": "Cura veneno.",
            "category": "medicine",
            "usable_in_battle": True,
            "usable_on_map": True,
            "effect": "cure_status",
            "effect_value": "poison",
            "price": 100,
            "unlock_phase": None,
            "unlock_chapter": None
        }
        items["paralyze_heal"] = {
            "id": "paralyze_heal",
            "name": "PARALYZEHEAL",
            "sprite_path": medicine_path / "paralyzeheal.png",
            "description": "Cura paralisia.",
            "category": "medicine",
            "usable_in_battle": True,
            "usable_on_map": True,
            "effect": "cure_status",
            "effect_value": "paralysis",
            "price": 200,
            "unlock_phase": "1-5",
            "unlock_chapter": None
        }
        items["awakening"] = {
            "id": "awakening",
            "name": "AWAKENING",
            "sprite_path": medicine_path / "awakening.png",
            "description": "Cura sono.",
            "category": "medicine",
            "usable_in_battle": True,
            "usable_on_map": True,
            "effect": "cure_status",
            "effect_value": "sleep",
            "price": 250,
            "unlock_phase": "1-5",
            "unlock_chapter": None
        }
        items["burn_heal"] = {
            "id": "burn_heal",
            "name": "BURNHEAL",
            "sprite_path": medicine_path / "burnheal.png",
            "description": "Cura queimadura.",
            "category": "medicine",
            "usable_in_battle": True,
            "usable_on_map": True,
            "effect": "cure_status",
            "effect_value": "burn",
            "price": 250,
            "unlock_phase": "4-5",
            "unlock_chapter": None
        }
        items["ice_heal"] = {
            "id": "ice_heal",
            "name": "ICEHEAL",
            "sprite_path": medicine_path / "iceheal.png",
            "description": "Cura congelamento.",
            "category": "medicine",
            "usable_in_battle": True,
            "usable_on_map": True,
            "effect": "cure_status",
            "effect_value": "freeze",
            "price": 250,
            "unlock_phase": "4-5",
            "unlock_chapter": None
        }
        items["full_heal"] = {
            "id": "full_heal",
            "name": "FULLHEAL",
            "sprite_path": medicine_path / "fullheal.png",
            "description": "Cura todos os problemas de status.",
            "category": "medicine",
            "usable_in_battle": True,
            "usable_on_map": True,
            "effect": "cure_all_status",
            "effect_value": None,
            "price": 600,
            "unlock_phase": "1-5",
            "unlock_chapter": None
        }
        items["rare_candy"] = {
            "id": "rare_candy",
            "name": "RARE CANDY",
            "sprite_path": medicine_path / "rare-candy.png",
            "description": "Doce raro que aumenta o nível em 1.",
            "category": "medicine",
            "usable_in_battle": True,
            "usable_on_map": True,
            "effect": "level_up",
            "effect_value": 1,
            "price": 4800,
            "unlock_phase": None,
            "unlock_chapter": None
        }
        # ===== REVIVES =====
        items["revive"] = {
            "id": "revive",
            "name": "REVIVE",
            "sprite_path": medicine_path / "REVIVE.png",
            "description": "Revive um Pokémon derrotado com metade do HP máximo.",
            "category": "medicine",
            "usable_in_battle": True,
            "usable_on_map": True,
            "effect": "revive",
            "effect_value": 0.5,  # 50% do HP máximo
            "price": 1000,
            "unlock_phase": "1-5",
            "unlock_chapter": None
        }
        items["max_revive"] = {
            "id": "max_revive",
            "name": "MAX REVIVE",
            "sprite_path": medicine_path / "MAXREVIVE.png",
            "description": "Revive um Pokémon derrotado com 100% do HP máximo.",
            "category": "medicine",
            "usable_in_battle": True,
            "usable_on_map": True,
            "effect": "revive",
            "effect_value": 1.0,  # 100% do HP máximo
            "price": 1900,
            "unlock_phase": "2-8",
            "unlock_chapter": None
        }
        # ===== PP ITEMS =====
        items["pp_up"] = {
            "id": "pp_up",
            "name": "PP UP",
            "sprite_path": medicine_path / "PPUP.png",
            "description": "Aumenta o PP de todos movimento em 20% do máximo.",
            "category": "medicine",
            "usable_in_battle": True,
            "usable_on_map": True,
            "effect": "pp_restore",
            "effect_value": 0.2,
            "price": 100,
            "unlock_phase": "1-3",
            "unlock_chapter": None
        }
        items["pp_max"] = {
            "id": "pp_max",
            "name": "PP MAX",
            "sprite_path": medicine_path / "PPMAX.png",
            "description": "Aumenta o PP de todos movimento ao seu valor máximo.",
            "category": "medicine",
            "usable_in_battle": True,
            "usable_on_map": True,
            "effect": "pp_restore",
            "effect_value": 1.0,
            "price": 450,
            "unlock_phase": "2-8",
            "unlock_chapter": None
        }
        # ===== PEDRAS DE EVOLUÇÃO =====
        stones = [
            ("firestone", "FIRESTONE", "2-8"),
            ("thunderstone", "THUNDERSTONE", "2-8"),
            ("waterstone", "WATERSTONE", "2-8"),
            ("leafstone", "LEAFSTONE", "3-4"),
            ("moonstone", "MOONSTONE", "3-4"),
            ("sunstone", "SUNSTONE", "4-5"),
            ("shinystone", "SHINYSTONE", "4-5"),
            ("dawnstone", "DAWNSTONE", "4-5")
        ]
        for stone_id, stone_name, unlock_phase in stones:
            items[stone_id] = {
                "id": stone_id,
                "name": stone_name,
                "sprite_path": evo_stones_path / f"{stone_name}.png",
                "description": "Evolui certas espécies de Pokémon.",
                "category": "items",
                "usable_in_battle": True,
                "usable_on_map": True,
                "effect": "evolution",
                "effect_value": 0,
                "price": 1200,
                "unlock_phase": unlock_phase,
                "unlock_chapter": None
            }
        # ===== ITENS DE BATALHA (X-ITEMS) =====
        battle_items = [
            ("x_accuracy", "X ACCURACY", "XACCURACY.png", "Precisão", "accuracy"),
            ("x_attack", "X ATTACK", "XATTACK.png", "Ataque", "attack"),
            ("x_defense", "X DEFENSE", "XDEFENSE.png", "Defesa", "defense"),
            ("x_spatk", "X SPATK", "XSPATK.png", "Ataque Especial", "sp_attack"),
            ("x_spdef", "X SPDEF", "XSPDEF.png", "Defesa Especial", "sp_defense"),
            ("x_speed", "X SPEED", "XSPEED.png", "Velocidade", "speed"),
        ]
        for item_id, name, filename, stat_display, stat_key in battle_items:
            items[item_id] = {
                "id": item_id,
                "name": name,
                "sprite_path": battle_items_path / filename,
                "description": f"Aumenta {stat_display} do Pokémon por 20 segundos.",
                "category": "battle_item",
                "usable_in_battle": True,
                "usable_on_map": False,
                "effect": "battle_stat_boost",
                "effect_value": {
                    "stat": stat_key,
                    "stages": 1,
                    "duration": 20.0,
                },
                "price": 500,
                "unlock_phase": None,
                "unlock_chapter": None
            }

        # ===== TMs/HMs =====
        # Lista de TMs: (id, nome, sprite_file, move_name, unlock_phase, price)
        tms = [
            ("tm_bide", "TM01 - Bide", "machine_NORMAL.png", "bide", "1-5", 2000),
            ("tm_thunder_wave", "TM45 - Thunder Wave", "machine_ELECTRIC.png", "thunder-wave", "2-2", 1500),
            ("tm_whirlwind", "TM04 - Whirlwind", "machine_NORMAL.png", "whirlwind", "2-3", 2500),
            ("tm_water_gun", "TM12 - Water Gun", "machine_WATER.png", "water-gun", "2-4", 2000),
            ("tm_mega_punch", "TM34 - Mega Punch", "machine_NORMAL.png", "mega-punch", "2-5", 2000),
            ("tm_seismic_toss", "TM19 - Seismic Toss", "machine_FIGHTING.png", "seismic-toss", "2-6", 2000),
            ("tm_dig", "TM28 - Dig", "machine_WATER.png", "dig", "2-7", 2000),
            ("tm_bubble_beam", "TM11 - Bubble Beam", "machine_WATER.png", "bubble-beam", "2-8", 2500),
            ("hm_cut", "HM01 - CUT", "machine_NORMAL.png", "cut", "2-8", 2000),
            ("hm_flash", "HM05 - FLASH", "machine_NORMAL.png", "flash", "2-8", 1000),
            ("hm_body_slam", "TM08 - Body Slam ", "machine_NORMAL.png", "body-slam", "3-1", 2000),
            ("hm_rest", "TM44 - Rest  ", "machine_NORMAL.png", "rest", "3-3", 2000),
            ("tm_thunderbolt", "TM24 - Thunderbolt", "machine_ELECTRIC.png", "thunderbolt", "3-4", 3000),
            ("tm_swift", "TM39  - Swift ", "machine_NORMAL.png", "swift", "3-5", 2500),
            ("tm_pay-_ay", "TM16  - Pay Day ", "machine_NORMAL.png", "pay-day", "3-5", 5000),
            ("tm_double_edge", "TM10  - Double Edge ", "machine_NORMAL.png", "double-edge", "4-1", 3000),
            ("tm_razor_wind", "TM02 - Razor Wind", "machine_NORMAL.png", "razor-wind", "4-1", 1500),
            ("tm_horn_drill", "TM07 - Horn Drill", "machine_NORMAL.png", "horn-drill", "4-1", 4500),
            ("tm_teleport", "TM30 - Teleport", "machine_PSYCHIC.png", "teleport", "4-4", 750),
            ("tm_mega_drain", "TM21 - Mega Drain", "machine_GRASS.png", "mega-drain", "4-5", 3500),
            ("tm_ice_beam", "TM13 - Ice Beam", "machine_ICE.png", "ice-beam", "4-6", 3000),
            ("tm_rock_slide", "TM48 - Rock Slide", "machine_ICE.png", "rock-slide", "4-6", 3000),
            ("tm_tri_attack", "TM49 Tri Attack", "machine_ICE.png", "tri-attack", "4-6", 3333),
            ("hm_surf", "HM03 - Surf", "machine_WATER.png", "surf", "4-6", 4500),

            ("tm_swords_dance", "TM03 - Swords Dance", "machine_NORMAL.png", "swords-dance", "4-6", 1500),
            ("tm_mega_kick", "TM05 - Mega Kick", "machine_NORMAL.png", "mega-kick", "4-6", 2000),
            ("tm_earthquake", "TM26 - Earthquake", "machine_GROUND.png", "earthquake", "4-6", 4000),

        ]

        for tm_id, tm_name, sprite_file, move_name, unlock_phase, price in tms:
            # Busca a descrição do movimento (prioridade: EffectFactory -> MoveData -> padrão)
            move_description = self._get_move_description(move_name)

            items[tm_id] = {
                "id": tm_id,
                "name": tm_name,
                "sprite_path": tm_hm_path / sprite_file,
                "description": move_description,  # Usa a melhor descrição disponível
                "category": "tm",
                "usable_in_battle": False,
                "usable_on_map": True,
                "effect": "teach_move",
                "effect_value": move_name,
                "price": price,
                "unlock_phase": unlock_phase,
                "unlock_chapter": None,
                "move_name": move_name,  # Guarda o nome do movimento para referência
            }

        return items

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
            print(f"[ItemBagCatalog] Item não encontrado: {item_id}")
            return

        sprite_path = item_data["sprite_path"]
        sprite_path_str = str(sprite_path)

        # Verifica se o arquivo existe
        if sprite_path.exists():
            try:
                sprite = pygame.image.load(sprite_path_str).convert_alpha()
                self.sprites[item_id] = sprite
                self.sprites_scaled[item_id] = pygame.transform.scale(sprite, (48, 48))
                print(f"✓ {item_data['name']}: Carregado de {sprite_path_str}")
            except Exception as e:
                print(f"✗ Erro ao carregar {item_data['name']}: {e}")
                self._create_placeholder(item_id)
        else:
            print(f"✗ {item_data['name']}: Arquivo não encontrado - {sprite_path_str}")
            # Tenta encontrar em locais alternativos
            self._try_find_sprite_alternative(item_id, item_data)

    def _try_find_sprite_alternative(self, item_id, item_data):
        """Tenta encontrar o sprite em locais alternativos"""
        sprite_path = item_data["sprite_path"]
        base_name = sprite_path.name
        parent_dir = sprite_path.parent

        # Lista de possíveis nomes alternativos
        alternatives = [
            parent_dir / base_name.lower(),
            parent_dir / base_name.upper(),
            parent_dir / base_name.replace(".png", ".PNG"),
            parent_dir / base_name.replace("-", "_"),
            parent_dir / base_name.replace("_", "-"),
            parent_dir / base_name.replace(" ", ""),
        ]

        # Busca recursiva por arquivos .png na pasta
        if parent_dir.exists():
            for png_file in parent_dir.glob("*.png"):
                if png_file.stem.lower() == sprite_path.stem.lower():
                    alternatives.append(png_file)
                    break

        for alt_path in alternatives:
            if alt_path.exists():
                print(f"  → Encontrado em: {alt_path}")
                item_data["sprite_path"] = alt_path
                self._load_sprite(item_id)  # Tenta carregar novamente
                return

        # Se ainda não encontrou, cria placeholder
        print(f"  → Criando placeholder para {item_data['name']}")
        self._create_placeholder(item_id)

    def _create_placeholder(self, item_id):
        """Cria um placeholder para o item"""
        self._ensure_pygame_ready()

        size = 32
        sprite = pygame.Surface((size, size), pygame.SRCALPHA)

        item_data = self.items.get(item_id, {})
        category = item_data.get("category", "")

        if category == "pokeball":
            color = (255, 0, 0)  # Vermelho para pokebolas
        elif category == "medicine":
            color = (0, 255, 0)  # Verde para poções
        elif category == "tm":
            color = (0, 0, 255)  # Azul para TMs
        else:
            color = (128, 128, 128)  # Cinza para outros

        # Desenha um círculo
        pygame.draw.circle(sprite, color, (size // 2, size // 2), size // 2 - 2)
        pygame.draw.circle(sprite, (255, 255, 255), (size // 2, size // 2), size // 2 - 2, 2)

        # Letra do item
        try:
            font = pygame.font.Font(None, 20)
            letter = item_id[0].upper() if item_id else "?"
            text = font.render(letter, True, (255, 255, 255))
            text_rect = text.get_rect(center=(size // 2, size // 2))
            sprite.blit(text, text_rect)
        except:
            pass

        self.sprites[item_id] = sprite
        self.sprites_scaled[item_id] = pygame.transform.scale(sprite, (48, 48))
        self.placeholders[item_id] = True

    def get_sprite(self, item_id, scaled=False):
        """Retorna o sprite do item (carrega sob demanda)"""
        if item_id not in self.sprites:
            self._load_sprite(item_id)

        if scaled:
            # Tenta retornar o sprite escalado, ou um fallback
            if item_id in self.sprites_scaled:
                return self.sprites_scaled[item_id]
            # Fallback para pokeball
            return self.sprites_scaled.get("pokeball")

        # Sprite normal
        if item_id in self.sprites:
            return self.sprites[item_id]
        return self.sprites.get("pokeball")

    def get_item(self, item_id):
        """Retorna dados do item"""
        item = self.items.get(item_id)
        if item is None:
            # Fallback para pokeball se não encontrar
            print(f"[ItemBagCatalog] Aviso: Item '{item_id}' não encontrado, usando pokeball como fallback")
            return self.items.get("pokeball")
        return item

    def get_all_items(self):
        """Retorna todos os itens"""
        return list(self.items.values())

    def get_items_by_category(self, category):
        """Retorna itens de uma categoria"""
        return [item for item in self.items.values() if item.get("category") == category]

    def get_pokeballs(self):
        """Retorna apenas pokebolas"""
        return self.get_items_by_category("pokeball")

    def get_medicines(self):
        """Retorna apenas poções/remédios"""
        return self.get_items_by_category("medicine")

    def get_tms(self):
        """Retorna apenas TMs"""
        return self.get_items_by_category("tm")

    def get_unlock_phase(self, item_id):
        """Retorna a fase necessária para desbloquear o item"""
        item = self.items.get(item_id, {})
        return item.get("unlock_phase") or item.get("unlock_chapter")

    def is_item_unlocked(self, item_id, progress_manager):
        """Verifica se o item está desbloqueado baseado no progresso do jogador"""
        unlock_phase = self.get_unlock_phase(item_id)

        if unlock_phase is None:
            return True

        return progress_manager.is_phase_completed(unlock_phase)

    def get_move_description(self, item_id):
        """
        Método público para obter a descrição do movimento de um TM.
        Útil se precisar atualizar a descrição dinamicamente.
        """
        item = self.get_item(item_id)
        if item.get("category") == "tm":
            move_name = item.get("move_name") or item.get("effect_value")
            if move_name:
                return self._get_move_description(move_name)
        return item.get("description", "Ensina um movimento ao Pokémon")

    def refresh_tm_description(self, item_id):
        """
        Atualiza a descrição de um TM específico.
        Útil se as descrições dos moves mudarem em runtime.
        """
        item = self.get_item(item_id)
        if item.get("category") == "tm":
            move_name = item.get("move_name") or item.get("effect_value")
            if move_name:
                new_description = self._get_move_description(move_name)
                item["description"] = new_description
                return new_description
        return item.get("description", "Ensina um movimento ao Pokémon")


# Instância global
item_bag_catalog = ItemBagCatalog()