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
        self.selected_category = "all"  # "all", "pokeball", "medicine", "items"

        # Lista de itens para navegação
        self.filtered_items = []

        # Ordem das categorias
        self.categories_order = ["all", "pokeball", "medicine", "battle_item", "tm", "held_item", "items"]

        # Garante que o pygame está inicializado
        self._ensure_pygame()

        self._update_filtered_items()

    def _ensure_pygame(self):
        """Garante que o pygame está inicializado"""
        if not pygame.get_init():
            pygame.init()
        if not pygame.font.get_init():
            pygame.font.init()

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

        print(f"[BAG] Categoria: {self.selected_category} -> {len(self.filtered_items)} itens")

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
        if category not in self.categories_order:
            return

        self.selected_category = category
        self._update_filtered_items()
        self.selected_item_index = 0

        # ===== SALVA NO PLAYER =====
        if hasattr(self, 'player') and self.player:
            self.player.update_bag_ui_config(category=category)

        print(f"[BAG] Categoria alterada para: {category}")

    def cycle_category(self):
        """Alterna entre as categorias"""
        try:
            current_index = self.categories_order.index(self.selected_category)
        except ValueError:
            current_index = 0

        next_index = (current_index + 1) % len(self.categories_order)
        new_category = self.categories_order[next_index]
        self.set_category(new_category)
        return self.selected_category

    def get_category_index(self):
        """Retorna o índice da categoria atual na ordem"""
        try:
            return self.categories_order.index(self.selected_category)
        except ValueError:
            return 0

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

    def get_held_items(self):
        """Retorna apenas itens seguráveis (held_item) com quantidade > 0"""
        held_items = []
        for item_id, quantity in self.items.items():
            if quantity <= 0:
                continue
            item_data = self.catalog.get_item(item_id)
            if item_data and item_data.get("category") == "held_item":
                held_items.append({
                    "id": item_id,
                    "data": item_data,
                    "quantity": quantity
                })
        return held_items

    def get_held_item_quantity(self, item_id):
        """Retorna quantidade de um item segurável específico"""
        item_data = self.catalog.get_item(item_id)
        if not item_data or item_data.get("category") != "held_item":
            return 0
        return self.items.get(item_id, 0)

    def equip_held_item(self, pokemon, item_id):
        """
        Equipa um item segurável em um Pokémon.
        Retorna (sucesso, mensagem)
        """
        # Verifica se o item existe e é segurável
        item_data = self.catalog.get_item(item_id)
        if not item_data:
            return False, "Item não encontrado"

        if item_data.get("category") != "held_item":
            return False, f"{item_data['name']} não é um item segurável"

        # Verifica se tem o item na mochila
        if self.get_quantity(item_id) <= 0:
            return False, f"Você não tem {item_data['name']}"

        # Se o Pokémon já tem um item, devolve para a mochila primeiro
        if pokemon.held_item:
            old_item_id = pokemon.held_item
            self.add_item(old_item_id, 1)
            print(f"[BAG] {old_item_id} devolvido à mochila de {pokemon.name}")

        # Remove o item da mochila
        self.remove_item(item_id, 1)

        # Equipa no Pokémon
        pokemon.held_item = item_id
        pokemon.held_item_data = item_data

        # ===== SALVA O JOGO AUTOMATICAMENTE =====
        if hasattr(self, 'player') and self.player:
            self.player.auto_save()
            print(f"[BAG] Jogo salvo automaticamente após equipar {item_data['name']} em {pokemon.name}")

        print(f"[BAG] {pokemon.name} agora segura {item_data['name']}")
        return True, f"{pokemon.name} agora segura {item_data['name']}!"

    def unequip_held_item(self, pokemon):
        """
        Remove o item segurável de um Pokémon e devolve à mochila.
        Retorna (sucesso, mensagem)
        """
        if not pokemon.held_item:
            return False, f"{pokemon.name} não está segurando nada"

        item_id = pokemon.held_item
        item_data = pokemon.held_item_data

        # Devolve para a mochila
        self.add_item(item_id, 1)

        # Remove do Pokémon
        pokemon.held_item = None
        pokemon.held_item_data = None

        # ===== SALVA O JOGO AUTOMATICAMENTE =====
        if hasattr(self, 'player') and self.player:
            self.player.auto_save()
            print(f"[BAG] Jogo salvo automaticamente após remover {item_data['name']} de {pokemon.name}")

        print(f"[BAG] {item_data['name']} removido de {pokemon.name}")
        return True, f"{item_data['name']} removido de {pokemon.name}!"