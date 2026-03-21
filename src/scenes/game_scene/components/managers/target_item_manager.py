# src/scenes/game_scene/components/managers/target_item_manager.py

import pygame
import random
import math
from src.entities.target_item import TargetItem
from src.data.item_catalog import item_catalog
from src.scenes.game_scene.components.renderer.target_item_renderer import TargetItemRenderer


class TargetItemManager:
    """Gerencia os itens alvo durante o jogo"""

    def __init__(self, game):
        self.game = game
        self.items = []  # Lista de itens ainda no jogo (não roubados)
        self.catalog = item_catalog
        self.items_stolen = 0
        self.items_protected = 0
        self.total_items = 0  # Total inicial de itens
        self.game_over = False
        self.victory = False
        self.visual_variation_range = 5
        self.renderer = TargetItemRenderer()

    def load_from_data(self, items_data: dict):
        """Carrega os itens a partir dos dados da fase"""
        if not items_data:
            print("Sem dados de itens para carregar")
            self.items = []
            self.items_stolen = 0
            self.items_protected = 0
            self.total_items = 0
            self.game_over = False
            return False

        try:
            self.items = []
            self.items_stolen = 0
            self.items_protected = 0

            if isinstance(items_data, dict) and 'items' in items_data:
                items_list = items_data['items']
            else:
                items_list = items_data if isinstance(items_data, list) else []

            # Agrupa itens por posição para aplicar variação visual diferente
            position_groups = {}

            for item_data in items_list:
                pos_key = (item_data["x"], item_data["y"])
                if pos_key not in position_groups:
                    position_groups[pos_key] = []
                position_groups[pos_key].append(item_data)

            # Cria itens com variação visual baseada no grupo
            for pos_key, group_items in position_groups.items():
                base_x, base_y = pos_key
                variation_range = self.visual_variation_range
                if len(group_items) > 1:
                    variation_range = self.visual_variation_range * 1.5

                for i, item_data in enumerate(group_items):
                    item_id = item_data.get("item_id", 1)

                    if len(group_items) > 1:
                        angle = (i / len(group_items)) * 360
                        extra_offset_x = math.cos(math.radians(angle)) * variation_range * 0.7
                        extra_offset_y = math.sin(math.radians(angle)) * variation_range * 0.7
                    else:
                        extra_offset_x = 0
                        extra_offset_y = 0

                    item = TargetItem(
                        base_x,
                        base_y,
                        item_id,
                        offset_range=variation_range
                    )

                    if len(group_items) > 1:
                        item.visual_offset_x = extra_offset_x
                        item.visual_offset_y = extra_offset_y
                        item.rotation = random.uniform(-45, 45)

                    item.screen_manager = self.game.screen_manager
                    self.items.append(item)

            # IMPORTANTE: Total inicial de itens
            self.total_items = len(self.items)
            self.items_protected = len(self.items)
            self.items_stolen = 0
            self.game_over = False

            print(f"Itens alvo carregados: {self.total_items}")
            return True

        except Exception as e:
            print(f"Erro ao carregar itens: {e}")
            self.items = []
            self.items_stolen = 0
            self.items_protected = 0
            self.total_items = 0
            self.game_over = False
            return False

    def update(self, dt):
        """Atualiza todos os itens e verifica game over"""
        items_to_remove = []

        for item in self.items[:]:  # Itera sobre cópia
            item.update(dt)

            # ===== CRITÉRIO: Item foi roubado =====
            # Um item é considerado roubado se:
            # 1. Foi marcado como is_stolen (pelo wave_manager)
            # 2. OU está sendo carregado por um Pokémon que morreu (carried_by is None mas is_protected False)
            # 3. OU is_protected é False (item foi capturado)

            is_stolen = (not item.is_protected) or item.is_stolen

            # Verificação extra: se está sendo carregado mas o Pokémon morreu
            if item.carried_by and not hasattr(item.carried_by, 'is_alive'):
                is_stolen = True

            if is_stolen and item not in items_to_remove:
                items_to_remove.append(item)

        # Remove itens roubados
        for item in items_to_remove:
            if item in self.items:
                self.items.remove(item)
                self.items_stolen += 1
                self.items_protected = len(self.items)
                print(f"[ITENS] {item.item_name} foi removido! Restam {self.items_protected}/{self.total_items}")

        # ===== VERIFICA GAME OVER =====
        # Game over quando não há mais itens protegidos (todos foram roubados)
        if self.items_protected <= 0 and self.total_items > 0:
            self.game_over = True
            print(f"[GAME OVER] Todos os {self.total_items} itens foram levados!")
            return

        # Se ainda tem itens, mas todos estão sendo carregados ou protegidos, continua
        # Não há game over

    def mark_item_as_stolen(self, item):
        """Marca um item como roubado (chamado pelo wave_manager)"""
        if item in self.items and item.is_protected:
            item.is_protected = False
            item.is_stolen = True
            # Não remove imediatamente, deixa o update fazer a remoção
            print(f"[ITENS] Item {item.item_name} marcado como roubado")

    def check_victory(self):
        """Verifica se todos os itens estão protegidos e waves acabaram"""
        # Vitória: ainda tem itens protegidos E não está em game over
        return self.items_protected > 0 and not self.game_over

    def render_in_ground(self, screen, camera):
        """Renderiza todos os itens no chão usando o renderer"""
        ground_items = [item for item in self.items if item.carried_by is None]
        self.renderer.render(screen, camera, self.game.screen_manager, ground_items)

    def render_in_pokemon(self, screen, camera):
        """Renderiza todos os itens sendo carregados usando o renderer"""
        carried_items = [item for item in self.items if item.carried_by]
        self.renderer.render(screen, camera, self.game.screen_manager, carried_items)

    def get_item_at(self, x, y, tolerance=20):
        """Retorna o item na posição (para debug)"""
        for item in self.items:
            dist = ((item.base_x - x) ** 2 + (item.base_y - y) ** 2) ** 0.5
            if dist < tolerance:
                return item
        return None