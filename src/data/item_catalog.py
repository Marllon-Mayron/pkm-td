# src/data/item_catalog.py

"""Catálogo de itens disponíveis no jogo"""
import sys
from pathlib import Path

# Importa o caminho centralizado
from src.config.paths import PROJECT_ROOT, ITEMS_PATH


class ItemCatalog:
    """Catálogo central de itens - similar ao Pokedex"""

    def __init__(self):
        # Usa o PROJECT_ROOT centralizado do paths.py
        self.root_dir = PROJECT_ROOT
        self.base_path = ITEMS_PATH

        print(f"[ItemCatalog] Root dir: {self.root_dir}")
        print(f"[ItemCatalog] Base path: {self.base_path}")
        print(f"[ItemCatalog] Base path existe: {self.base_path.exists()}")

        # Constrói o catálogo de itens
        self.items = self._build_catalog()

        # Verifica se os sprites existem (debug)
        self._check_sprites()

    def _build_catalog(self):
        """Constrói o catálogo de itens com caminhos usando Path"""
        items = {}

        # Rare Candy
        medicine_path = self.base_path / "medicine"
        rare_candy_path = medicine_path / "rare-candy.png"

        # Se não encontrar rare-candy.png, tenta variações
        if not rare_candy_path.exists():
            # Tenta outras variações do nome
            alternatives = [
                medicine_path / "Rare Candy.png",
                medicine_path / "RareCandy.png",
                medicine_path / "rare_candy.png",
                self.base_path / "rare-candy.png",
            ]
            for alt in alternatives:
                if alt.exists():
                    rare_candy_path = alt
                    break

        items[1] = {
            "id": 1,
            "name": "Rare Candy",
            "sprite": rare_candy_path,
            "description": "Raro doce que sobe o nível",
            "category": "medicine"
        }

        # Badges
        badge_path = self.base_path / "badge"
        items[2] = {
            "id": 2,
            "name": "Insignia de pedra",
            "sprite": badge_path / "rock-badge.png",
            "description": "Insignia 1",
            "category": "badge"
        }

        items[3] = {
            "id": 3,
            "name": "Insignia de água",
            "sprite": badge_path / "water-badge.png",
            "description": "Insignia 2",
            "category": "badge"
        }

        items[4] = {
            "id": 4,
            "name": "Insignia do trovão",
            "sprite": badge_path / "thunder-badge.png",
            "description": "Insignia 3",
            "category": "badge"
        }
        items[5] = {
            "id": 5,
            "name": "Insignia do arco-iris",
            "sprite": badge_path / "rainbow-badge.png",
            "description": "Insignia 4",
            "category": "badge"
        }
        items[6] = {
            "id": 6,
            "name": "Insignia do veneno",
            "sprite": badge_path / "poison-badge.png",
            "description": "Insignia 5",
            "category": "badge"
        }
        items[7] = {
            "id": 7,
            "name": "Insignia do pantano",
            "sprite": badge_path / "marsh-badge.png",
            "description": "Insignia 6",
            "category": "badge"
        }
        items[8] = {
            "id": 8,
            "name": "Insignia do vulcao",
            "sprite": badge_path / "volcano-badge.png",
            "description": "Insignia 7",
            "category": "badge"
        }
        items[9] = {
            "id": 9,
            "name": "Insignia da terra",
            "sprite": badge_path / "earth-badge.png",
            "description": "Insignia 9",
            "category": "badge"
        }
        items[10] = {
            "id": 10,
            "name": "Isca Safari",
            "sprite": medicine_path / "safari_bait.png",
            "description": "Isca para o safari",
            "category": "medicine"
        }

        return items

    def _check_sprites(self):
        """Verifica se os sprites existem (debug)"""
        print("\n=== VERIFICANDO SPRITES DE ITENS (ItemCatalog) ===")
        for item_id, item in self.items.items():
            sprite_path = item["sprite"]
            sprite_path_str = str(sprite_path)

            if sprite_path and sprite_path.exists():
                print(f"✓ {item['name']}: {sprite_path_str}")
            else:
                print(f"✗ {item['name']}: {sprite_path_str} (NÃO ENCONTRADO!)")

                # Tenta encontrar em locais alternativos
                self._try_find_sprite(item)
        print("================================================\n")

    def _try_find_sprite(self, item):
        """Tenta encontrar o sprite em locais alternativos"""
        item_name = item['name'].lower()

        # Possíveis localizações baseadas no nome
        medicine_path = self.base_path / "medicine"
        badge_path = self.base_path / "badge"

        locations = []

        if item["category"] == "medicine":
            locations = [
                medicine_path / "rare-candy.png",
                medicine_path / "Rare Candy.png",
                medicine_path / "RareCandy.png",
                medicine_path / "rare_candy.png",
                self.base_path / "rare-candy.png",
            ]
        elif item["category"] == "badge":
            locations = [
                badge_path / "rock-badge.png",
                badge_path / "water-badge.png",
                badge_path / "Rock Badge.png",
                badge_path / "Water Badge.png",
            ]

        for loc in locations:
            if loc.exists():
                print(f"  → ENCONTRADO em: {loc}")
                item["sprite"] = loc
                return True

        # Se não encontrou, lista o que tem na pasta
        search_path = medicine_path if item["category"] == "medicine" else badge_path
        if search_path.exists():
            print(f"  Arquivos em {search_path}:")
            try:
                for f in search_path.iterdir():
                    if f.suffix.lower() == '.png':
                        print(f"    - {f.name}")
            except Exception as e:
                print(f"    Erro ao listar: {e}")

        return False

    def get_item(self, item_id):
        """Retorna informações de um item pelo ID"""
        item = self.items.get(item_id)
        if item:
            # Converte Path para string se necessário para compatibilidade
            if isinstance(item.get("sprite"), Path):
                item["sprite_str"] = str(item["sprite"])
            return item

        return {
            "id": item_id,
            "name": f"Item {item_id}",
            "sprite": None,
            "description": "Item desconhecido",
            "category": "unknown"
        }

    def get_all_items(self):
        """Retorna todos os itens"""
        return list(self.items.values())

    def get_items_by_category(self, category):
        """Retorna itens de uma categoria específica"""
        return [item for item in self.items.values() if item["category"] == category]

    def search_items(self, query):
        """Busca itens por nome"""
        query = query.lower()
        return [item for item in self.items.values() if query in item["name"].lower()]


# Instância global
item_catalog = ItemCatalog()