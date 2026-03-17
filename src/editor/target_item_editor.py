# src/editor/target_item_editor.py

import pygame
import os
from src.data.item_catalog import item_catalog


class TargetItem:
    def __init__(self, x, y, item_id=1):
        self.x = x
        self.y = y
        self.item_id = item_id
        self.size = 16  # Tamanho 16x16 (grid)

        # Carrega informações do catálogo
        item_info = item_catalog.get_item(item_id)
        self.name = item_info["name"]
        self.sprite_path = item_info["sprite"]

        # Carrega sprite
        self.sprite = None
        self.load_sprite()

    def load_sprite(self):
        """Carrega o sprite do item e redimensiona para 16x16"""
        if self.sprite_path:
            # Normaliza o caminho
            normalized_path = os.path.normpath(self.sprite_path)
            if os.path.exists(normalized_path):
                try:
                    original_sprite = pygame.image.load(normalized_path).convert_alpha()
                    # Redimensiona para 16x16
                    self.sprite = pygame.transform.scale(original_sprite, (self.size, self.size))
                    print(f"✓ Sprite carregado: {self.name} redimensionado para 16x16 de {normalized_path}")
                except Exception as e:
                    print(f"✗ Erro ao carregar sprite {normalized_path}: {e}")
                    self.sprite = None
            else:
                print(f"✗ Sprite não encontrado: {normalized_path}")
                self.sprite = None
        else:
            self.sprite = None

    def get_rect(self):
        return pygame.Rect(self.x, self.y, self.size, self.size)

    def contains_point(self, px, py):
        return (self.x <= px <= self.x + self.size and
                self.y <= py <= self.y + self.size)


class TargetItemManager:
    def __init__(self):
        self.items = []
        self.selected_item = -1
        self.snap_to_grid = True
        self.grid_size = 16

        # Catálogo de itens
        self.catalog = item_catalog

    def add_item(self, x, y, item_id=1):
        """Adiciona um item alvo"""
        print(f"TargetItemManager.add_item({x}, {y}, {item_id})")
        item = TargetItem(x, y, item_id)
        self.items.append(item)

        item_info = self.catalog.get_item(item_id)
        print(f"Item {item_info['name']} (ID:{item_id}) adicionado em ({x}, {y})")
        return len(self.items) - 1

    def remove_item(self, item_or_index):
        """Remove um item - pode receber o objeto ou o índice"""
        if isinstance(item_or_index, int):
            # Remove por índice
            if 0 <= item_or_index < len(self.items):
                removed = self.items.pop(item_or_index)
                if self.selected_item >= len(self.items):
                    self.selected_item = len(self.items) - 1
                print(f"Item {removed.name} removido")
                return True
        else:
            # Remove por objeto
            if item_or_index in self.items:
                self.items.remove(item_or_index)
                if self.selected_item >= len(self.items):
                    self.selected_item = len(self.items) - 1
                print(f"Item {item_or_index.name} removido")
                return True
        return False

    def get_items_at(self, x, y, tolerance=16):
        """Retorna TODOS os itens na posição"""
        items_found = []
        for item in self.items:
            center_x = item.x + item.size // 2
            center_y = item.y + item.size // 2
            dist = ((center_x - x) ** 2 + (center_y - y) ** 2) ** 0.5
            if dist < tolerance:
                items_found.append(item)
        return items_found

    def get_item_at(self, x, y, tolerance=16):
        """Retorna o primeiro item encontrado na posição"""
        items = self.get_items_at(x, y, tolerance)
        return items[0] if items else None

    def render(self, screen, camera, screen_manager):
        """Renderiza os itens com sprites"""
        for i, item in enumerate(self.items):
            # Calcula posição na tela
            screen_x = round((item.x - camera.x) * camera.zoom * screen_manager.render_scale +
                             (screen_manager.render_width / 2) * screen_manager.render_scale +
                             screen_manager.viewport_x)
            screen_y = round((item.y - camera.y) * camera.zoom * screen_manager.render_scale +
                             (screen_manager.render_height / 2) * screen_manager.render_scale +
                             screen_manager.viewport_y)

            size = max(1, round(item.size * camera.zoom * screen_manager.render_scale))

            # Se tem sprite, usa ele
            if item.sprite:
                # Redimensiona sprite se necessário (zoom)
                if item.sprite.get_width() != size:
                    sprite_to_draw = pygame.transform.scale(item.sprite, (size, size))
                else:
                    sprite_to_draw = item.sprite

                screen.blit(sprite_to_draw, (screen_x, screen_y))

                # Se selecionado, desenha borda amarela
                if i == self.selected_item:
                    pygame.draw.rect(screen, (255, 215, 0),
                                     (screen_x - 2, screen_y - 2, size + 4, size + 4), 3)
            else:
                # Fallback: desenha um retângulo colorido com ID
                colors = [(255, 215, 0), (255, 0, 0), (0, 255, 0), (0, 0, 255), (255, 165, 0)]
                color = colors[(item.item_id - 1) % len(colors)]

                # Fundo
                pygame.draw.rect(screen, color, (screen_x, screen_y, size, size))

                # Borda (amarela se selecionado)
                border_color = (255, 215, 0) if i == self.selected_item else (100, 100, 100)
                border_width = 3 if i == self.selected_item else 1
                pygame.draw.rect(screen, border_color, (screen_x, screen_y, size, size), border_width)

                # Mostra ID no centro
                font = pygame.font.Font(None, size // 2)
                text = font.render(str(item.item_id), True, (255, 255, 255))
                text_rect = text.get_rect(center=(screen_x + size // 2, screen_y + size // 2))
                screen.blit(text, text_rect)

    def to_dict(self):
        """Converte para dicionário - só salva ID e posição"""
        return {
            "grid_size": self.grid_size,
            "snap_to_grid": self.snap_to_grid,
            "items": [
                {
                    "x": item.x,
                    "y": item.y,
                    "item_id": item.item_id
                }
                for item in self.items
            ]
        }

    def from_dict(self, data):
        """Carrega do dicionário"""
        self.grid_size = data.get("grid_size", 16)
        self.snap_to_grid = data.get("snap_to_grid", True)
        self.items = []
        for item_data in data.get("items", []):
            item_id = item_data.get("item_id", 1)
            item = TargetItem(item_data["x"], item_data["y"], item_id)
            self.items.append(item)