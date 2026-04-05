# src/data/item_catalog.py

"""Catálogo de itens disponíveis no jogo"""
import os
import sys


class ItemCatalog:
    """Catálogo central de itens - similar ao Pokedex"""

    def __init__(self):
        # Obtém o diretório raiz do projeto (onde o main.py está)
        if getattr(sys, 'frozen', False):
            # Se for executável
            self.root_dir = os.path.dirname(sys.executable)
        else:
            # Em desenvolvimento, sobe um nível de src/
            self.root_dir = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))

        # Constrói o caminho base absoluto
        self.base_path = os.path.join(self.root_dir, "res", "PokemonSprites", "items")

        print(f"Root dir: {self.root_dir}")
        print(f"Base path: {self.base_path}")

        self.items = {
            1: {
                "id": 1,
                "name": "Rare Candy",
                "sprite": os.path.join(self.base_path, "medicine", "rare-candy.png"),
                "description": "Raro doce que sobe o nível",
                "category": "medicine"
            },
            2: {
                "id": 2,
                "name": "Insignia de pedra",
                "sprite": os.path.join(self.base_path, "badge", "rock-badge.png"),
                "description": "Insignia 1",
                "category": "badge"
            },
            3: {
                "id": 3,
                "name": "Insignia de água",
                "sprite": os.path.join(self.base_path, "badge", "water-badge.png"),
                "description": "Insignia 2",
                "category": "badge"
            }
        }

        # Verifica se os sprites existem
        self._check_sprites()

    def _check_sprites(self):
        """Verifica se os sprites existem (debug)"""
        print("\n=== VERIFICANDO SPRITES DE ITENS ===")
        for item_id, item in self.items.items():
            if item["sprite"]:
                # Normaliza o caminho
                normalized_path = os.path.normpath(item["sprite"])
                exists = os.path.exists(normalized_path)
                if exists:
                    print(f"✓ {item['name']}: {normalized_path}")
                else:
                    print(f"✗ {item['name']}: {normalized_path} (NÃO ENCONTRADO!)")

                    # Tenta encontrar em locais alternativos
                    self._try_find_sprite(item)
        print("=====================================\n")

    def _try_find_sprite(self, item):
        """Tenta encontrar o sprite em locais alternativos"""
        nome_arquivo = item['name'].lower().replace(' ', '-')

        # Possíveis localizações
        locations = [
            os.path.join(self.base_path, "medicine", f"{nome_arquivo}.png"),
            os.path.join(self.base_path, "medicine", f"{nome_arquivo}.PNG"),
            os.path.join(self.base_path, "medicine", f"{item['name']}.png"),
            os.path.join(self.base_path, "medicine", "rare-candy.png"),  # Força rare-candy.png
            os.path.join(self.base_path, "rare-candy.png"),
            os.path.join(self.base_path, "medicine", "Rare Candy.png"),
        ]

        for loc in locations:
            if os.path.exists(loc):
                print(f"  → ENCONTRADO em: {loc}")
                item["sprite"] = loc
                return True

        # Se não encontrou, lista o que tem na pasta medicine
        medicine_path = os.path.join(self.base_path, "medicine")
        if os.path.exists(medicine_path):
            print(f"  Arquivos em {medicine_path}:")
            try:
                for f in os.listdir(medicine_path):
                    print(f"    - {f}")
            except:
                pass

        return False

    def get_item(self, item_id):
        """Retorna informações de um item pelo ID"""
        return self.items.get(item_id, {
            "id": item_id,
            "name": f"Item {item_id}",
            "sprite": None,
            "description": "Item desconhecido",
            "category": "unknown"
        })

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