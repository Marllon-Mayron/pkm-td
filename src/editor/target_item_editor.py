# src/editor/target_item_editor.py

import pygame


class TargetItem:
    def __init__(self, x, y, item_id=0, name="Item", sprite_path=None):
        self.x = x
        self.y = y
        self.item_id = item_id
        self.name = name
        self.sprite_path = sprite_path
        self.sprite = None
        # REMOVIDO: quantity
        self.size = 16

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

        # Lista de itens disponíveis (mock)
        self.available_items = [
            {"id": 1, "name": "Rare Candy", "sprite": None},
            {"id": 2, "name": "Master Ball", "sprite": None},
            {"id": 3, "name": "Potion", "sprite": None},
            {"id": 4, "name": "Revive", "sprite": None},
            {"id": 5, "name": "Poké Ball", "sprite": None},
        ]

    def add_item(self, x, y, item_id=1):
        """Adiciona um item alvo - SEM quantidade"""
        # Busca nome do item
        item_name = "Item"
        for avail in self.available_items:
            if avail["id"] == item_id:
                item_name = avail["name"]
                break

        # Cria o item (SEM quantity)
        item = TargetItem(x, y, item_id, item_name)
        self.items.append(item)
        print(f"Item {item_name} adicionado em ({x}, {y})")
        return len(self.items) - 1

    def remove_item(self, item):
        """Remove um item"""
        if item in self.items:
            self.items.remove(item)
            if self.selected_item >= len(self.items):
                self.selected_item = len(self.items) - 1
            print("Item removido")
            return True
        return False

    def get_items_at(self, x, y, tolerance=8):
        """
        Retorna TODOS os itens na posição (com tolerância)
        MODIFICADO: agora retorna lista de itens, não apenas o primeiro
        Args:
            x, y: coordenadas do mundo
            tolerance: tolerância em pixels para considerar como clique no item
        """
        items_found = []
        for item in self.items:
            # Centro do item
            center_x = item.x + item.size // 2
            center_y = item.y + item.size // 2

            # Distância do clique ao centro
            dist = ((center_x - x) ** 2 + (center_y - y) ** 2) ** 0.5

            if dist < tolerance:
                items_found.append(item)

        return items_found  # Retorna lista, pode ser vazia

    def get_item_at(self, x, y, tolerance=8):
        """
        Mantido para compatibilidade, mas modificado para pegar o PRIMEIRO item encontrado
        Útil para UI que espera um único item
        """
        items = self.get_items_at(x, y, tolerance)
        return items[0] if items else None

    def render(self, screen, camera, screen_manager):
        """Renderiza os itens - MODIFICADO para mostrar ID quando sobrepostos"""
        for i, item in enumerate(self.items):
            # Calcula posição na tela
            screen_x = round((item.x - camera.x) * camera.zoom * screen_manager.render_scale +
                             (screen_manager.render_width / 2) * screen_manager.render_scale +
                             screen_manager.viewport_x)
            screen_y = round((item.y - camera.y) * camera.zoom * screen_manager.render_scale +
                             (screen_manager.render_height / 2) * screen_manager.render_scale +
                             screen_manager.viewport_y)

            size = max(1, round(item.size * camera.zoom * screen_manager.render_scale))

            # Placeholder visual - cores baseadas no ID
            colors = [(255, 215, 0), (255, 0, 0), (0, 255, 0), (0, 0, 255), (255, 165, 0)]
            color = colors[(item.item_id - 1) % len(colors)]

            item_surface = pygame.Surface((size, size), pygame.SRCALPHA)

            # Fundo
            pygame.draw.rect(item_surface, (*color, 200),
                             (0, 0, size, size))

            # Borda (se selecionado)
            if i == self.selected_item:
                border_color = (255, 255, 255)
                border_width = 3
            else:
                border_color = (100, 100, 100)
                border_width = 1

            pygame.draw.rect(item_surface, border_color,
                             (0, 0, size, size), border_width)

            # MODIFICADO: Mostra ID do item no centro
            font = pygame.font.Font(None, size // 2)
            text = font.render(f"{item.item_id}", True, (255, 255, 255))
            text_rect = text.get_rect(center=(size // 2, size // 2))
            item_surface.blit(text, text_rect)

            screen.blit(item_surface, (screen_x, screen_y))

    def to_dict(self):
        """Converte para dicionário - REMOVIDO quantity"""
        return {
            "grid_size": self.grid_size,
            "snap_to_grid": self.snap_to_grid,
            "items": [
                {
                    "x": item.x,
                    "y": item.y,
                    "item_id": item.item_id,
                    "name": item.name,
                    "sprite_path": item.sprite_path
                    # REMOVIDO: quantity
                }
                for item in self.items
            ]
        }

    def from_dict(self, data):
        """Carrega do dicionário - compatível com versões antigas"""
        self.grid_size = data.get("grid_size", 16)
        self.snap_to_grid = data.get("snap_to_grid", True)
        self.items = []
        for item_data in data.get("items", []):
            item = TargetItem(
                item_data["x"],
                item_data["y"],
                item_data["item_id"],
                item_data.get("name", "Item"),
                item_data.get("sprite_path")
                # REMOVIDO: quantity - se existir em versões antigas, ignora
            )
            self.items.append(item)