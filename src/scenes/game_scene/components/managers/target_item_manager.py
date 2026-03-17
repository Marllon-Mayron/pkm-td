# src/scenes/game_scene/components/managers/target_item_manager.py

import pygame
from src.entities.target_item import TargetItem
from src.data.item_catalog import item_catalog


class TargetItemManager:
    """Gerencia os itens alvo durante o jogo"""

    def __init__(self, game):
        self.game = game
        self.items = []
        self.catalog = item_catalog
        self.items_stolen = 0
        self.items_protected = 0
        self.game_over = False
        self.victory = False

    def load_from_data(self, items_data: dict):
        """Carrega os itens a partir dos dados da fase"""
        if not items_data:
            print("Sem dados de itens para carregar")
            self.items = []
            self.items_stolen = 0
            self.items_protected = 0
            self.game_over = False
            return False

        try:
            self.items = []

            if isinstance(items_data, dict) and 'items' in items_data:
                items_list = items_data['items']
            else:
                items_list = items_data if isinstance(items_data, list) else []

            for item_data in items_list:
                # Pega o ID do item
                item_id = item_data.get("item_id", 1)

                # Cria o item (o construtor já carrega sprite do catálogo)
                item = TargetItem(
                    item_data["x"],
                    item_data["y"],
                    item_id
                )

                # Passa o screen_manager
                item.screen_manager = self.game.screen_manager
                self.items.append(item)

            print(f"Itens alvo carregados: {len(self.items)}")
            self.items_stolen = 0
            self.items_protected = len(self.items)
            self.game_over = False
            return True

        except Exception as e:
            print(f"Erro ao carregar itens: {e}")
            self.items = []
            self.items_stolen = 0
            self.items_protected = 0
            self.game_over = False
            return False

    def update(self, dt):
        """Atualiza todos os itens"""
        items_to_remove = []

        for item in self.items:
            item.update(dt)

            # Verifica se o item foi levado
            if not item.is_protected and item not in items_to_remove:
                items_to_remove.append(item)
                self.items_stolen += 1
                self.items_protected -= 1

                print(f"[ITENS] {item.item_name} foi levado! Restam {self.items_protected}")

        # Remove itens levados
        for item in items_to_remove:
            self.items.remove(item)

        # Verifica condições de game over/vitória
        if self.items_protected <= 0:
            self.game_over = True
            print("[GAME OVER] Todos os itens foram levados!")

    def check_victory(self):
        """Verifica se todos os itens estão protegidos e waves acabaram"""
        return self.items_protected > 0 and not self.game_over

    def render(self, screen, camera):
        """Renderiza todos os itens"""
        for item in self.items:
            item.render(screen, camera)

    def get_item_at(self, x, y, tolerance=20):
        """Retorna o item na posição (para debug)"""
        for item in self.items:
            dist = ((item.x - x) ** 2 + (item.y - y) ** 2) ** 0.5
            if dist < tolerance:
                return item
        return None