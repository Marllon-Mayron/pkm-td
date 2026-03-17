# src/scenes/game_scene/components/managers/target_item_manager.py

import pygame
from src.entities.target_item import TargetItem
from src.data.pokedex import Pokedex


class TargetItemManager:
    """Gerencia os itens alvo durante o jogo"""

    def __init__(self, game):
        self.game = game
        self.items = []  # Lista de TargetItem
        self.pokedex = Pokedex()
        self.items_stolen = 0
        self.items_protected = 0
        self.game_over = False
        self.victory = False

        # Efeitos visuais
        self.stolen_flash_timer = 0
        self.stolen_flash_duration = 1.0

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
                sprite = self._get_item_sprite(item_data["item_id"])

                item = TargetItem(
                    item_data["x"],
                    item_data["y"],
                    item_data["item_id"],
                    item_data.get("name", "Item"),
                    sprite,
                    item_data.get("quantity", 1)
                )

                # PASSA O SCREEN_MANAGER para o item
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

    def _get_item_sprite(self, item_id):
        """Retorna um sprite para o item (placeholder por enquanto)"""
        # Placeholder - criar sprites coloridos diferentes por ID
        sprite = pygame.Surface((16, 16), pygame.SRCALPHA)

        colors = {
            1: (255, 215, 0),  # Ouro - Rare Candy
            2: (255, 0, 0),    # Vermelho - Master Ball
            3: (0, 255, 0),    # Verde - Potion
            4: (0, 0, 255),    # Azul - Revive
            5: (255, 165, 0),  # Laranja - Poké Ball
        }

        color = colors.get(item_id, (200, 200, 200))

        # Desenha um ícone simples
        pygame.draw.rect(sprite, color, (0, 0, 16, 16))
        pygame.draw.rect(sprite, (255, 255, 255), (0, 0, 16, 16), 2)

        # Adiciona um brilho
        pygame.draw.line(sprite, (255, 255, 255, 100), (2, 2), (14, 2), 2)

        return sprite

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
                #self.stolen_flash_timer = self.stolen_flash_duration

                print(f"[ITENS] {item.item_name} foi levado! Restam {self.items_protected}")

        # Remove itens levados
        for item in items_to_remove:
            self.items.remove(item)

        # Atualiza timer do flash
        if self.stolen_flash_timer > 0:
            self.stolen_flash_timer -= dt

        # Verifica condições de game over/vitória
        if self.items_protected <= 0:
            self.game_over = True
            print("[GAME OVER] Todos os itens foram levados!")

    def check_victory(self):
        """Verifica se todos os itens estão protegidos e waves acabaram"""
        # Vitória quando todas as waves acabaram e ainda há itens
        return self.items_protected > 0 and not self.game_over

    def render(self, screen, camera):
        """Renderiza todos os itens"""
        for item in self.items:
            item.render(screen, camera)

        # Efeito de flash quando item é levado
        if self.stolen_flash_timer > 0:
            alpha = int(255 * (self.stolen_flash_timer / self.stolen_flash_duration))
            flash_surf = pygame.Surface((screen.get_width(), screen.get_height()))
            flash_surf.set_alpha(alpha)
            flash_surf.fill((255, 0, 0))
            screen.blit(flash_surf, (0, 0))

    def get_item_at(self, x, y, tolerance=20):
        """Retorna o item na posição (para debug)"""
        for item in self.items:
            dist = ((item.x - x) ** 2 + (item.y - y) ** 2) ** 0.5
            if dist < tolerance:
                return item
        return None