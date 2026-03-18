# src/managers/bag_manager.py

import pygame
from src.data.item_bag_catalog import item_bag_catalog


class BagManager:
    """Gerencia a mochila do jogador com itens - AGORA COM STACK INFINITO"""

    def __init__(self, player):
        self.player = player
        self.catalog = item_bag_catalog

        # Inventário: dict com item_id -> quantidade (até 9999)
        self.items = {}

        # Item selecionado atual
        self.selected_item_index = 0
        self.selected_category = "all"  # "all", "pokeball", "medicine"

        # Lista de itens para navegação
        self.filtered_items = []

        # Garante que o pygame está inicializado
        self._ensure_pygame()

        # Itens iniciais (6 pokebolas e 2 poções)
        self._add_initial_items()
        self._update_filtered_items()

    def _ensure_pygame(self):
        """Garante que o pygame está inicializado"""
        if not pygame.get_init():
            pygame.init()
        if not pygame.font.get_init():
            pygame.font.init()

    def _add_initial_items(self):
        """Adiciona itens iniciais para o jogador"""
        # 6 Pokebolas
        self.add_item("pokeball", 6)

        # 2 Poções
        self.add_item("potion", 2)


    def add_item(self, item_id, quantity=1):
        """Adiciona item à mochila (stack até 9999)"""
        if item_id not in self.catalog.items:
            print(f"[BAG] Item {item_id} não existe no catálogo!")
            return False

        current = self.items.get(item_id, 0)
        new_total = current + quantity

        # Limite de 9999 por stack
        if new_total > 9999:
            new_total = 9999
            print(f"[BAG] Aviso: {item_id} atingiu limite máximo de 9999!")

        self.items[item_id] = new_total

        self._update_filtered_items()
        print(f"[BAG] +{quantity} {item_id} | Total: {self.items[item_id]}")
        return True

    def remove_item(self, item_id, quantity=1):
        """Remove item da mochila"""
        if item_id not in self.items:
            return False

        self.items[item_id] -= quantity

        if self.items[item_id] <= 0:
            del self.items[item_id]
            self._update_filtered_items()

            # Ajusta seleção se necessário
            if self.selected_item_index >= len(self.filtered_items):
                self.selected_item_index = max(0, len(self.filtered_items) - 1)
        else:
            self._update_filtered_items()

        return True

    def get_quantity(self, item_id):
        """Retorna quantidade de um item"""
        return self.items.get(item_id, 0)

    def get_selected_item(self):
        """Retorna o item selecionado atualmente"""
        if not self.filtered_items:
            return None

        if self.selected_item_index < len(self.filtered_items):
            item_id = self.filtered_items[self.selected_item_index]
            return self.catalog.get_item(item_id)
        return None

    def _update_filtered_items(self):
        """Atualiza a lista de itens filtrada por categoria"""
        all_items = list(self.items.keys())

        if self.selected_category == "all":
            self.filtered_items = all_items
        else:
            self.filtered_items = [
                item_id for item_id in all_items
                if self.catalog.get_item(item_id)["category"] == self.selected_category
            ]

    def next_item(self):
        """Seleciona próximo item (rolagem para baixo)"""
        if self.filtered_items:
            self.selected_item_index = (self.selected_item_index + 1) % len(self.filtered_items)
            return self.get_selected_item()
        return None

    def prev_item(self):
        """Seleciona item anterior (rolagem para cima)"""
        if self.filtered_items:
            self.selected_item_index = (self.selected_item_index - 1) % len(self.filtered_items)
            return self.get_selected_item()
        return None

    def set_category(self, category):
        """Muda a categoria de filtro"""
        self.selected_category = category
        self._update_filtered_items()
        self.selected_item_index = 0

    def cycle_category(self):
        """Alterna entre as categorias"""
        categories = ["all", "pokeball", "medicine"]
        current_index = categories.index(self.selected_category)
        next_index = (current_index + 1) % len(categories)
        self.set_category(categories[next_index])
        return self.selected_category

    def use_selected_item(self, target=None):
        """Usa o item selecionado em um alvo"""
        selected = self.get_selected_item()
        if not selected:
            return False, "Nenhum item selecionado"

        # Verifica se tem quantidade
        if self.get_quantity(selected["id"]) <= 0:
            return False, f"Sem {selected['name']}"

        # TODO: Implementar lógica de uso real
        # Por enquanto, só remove o item
        self.remove_item(selected["id"], 1)
        return True, f"Usou {selected['name']}"

    def has_item(self, item_id):
        """Verifica se tem pelo menos 1 do item"""
        return self.items.get(item_id, 0) > 0

    def has_items(self):
        """Verifica se tem itens na categoria atual"""
        return len(self.filtered_items) > 0

    def get_items_for_render(self):
        """Retorna lista de itens para renderização"""
        items_for_render = []

        for i, item_id in enumerate(self.filtered_items):
            item_data = self.catalog.get_item(item_id)
            quantity = self.items[item_id]
            is_selected = (i == self.selected_item_index)

            items_for_render.append({
                "id": item_id,
                "data": item_data,
                "quantity": quantity,
                "selected": is_selected,
                "index": i
            })

        return items_for_render

    def get_item_count(self):
        """Retorna total de itens (contando quantidades)"""
        return sum(self.items.values())

    def get_unique_item_count(self):
        """Retorna número de tipos diferentes de itens"""
        return len(self.items)