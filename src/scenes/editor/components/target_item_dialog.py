# src/scenes/editor/components/target_item_dialog.py

import pygame, os
from src.data.item_catalog import item_catalog


class TargetItemDialog:
    def __init__(self, x, y, width, height, item_manager):
        self.rect = pygame.Rect(x, y, width, height)
        self.visible = True
        self.item_manager = item_manager

        self.dragging = False
        self.drag_offset_x = 0
        self.drag_offset_y = 0

        # Catálogo de itens
        from src.data.item_catalog import item_catalog
        self.catalog = item_catalog
        self.available_items = self.catalog.get_all_items()

        # Item selecionado para ADICIONAR (quando o diálogo fechar)
        self.selected_item_id = 1  # ID do item selecionado para adicionar
        self.selected_item_name = "Rare Candy"  # Nome para feedback

        # Scroll do catálogo
        self.catalog_scroll = 0
        self.max_catalog_scroll = 0

        # Filtro de categoria
        self.categories = ["todos", "medicine", "ball", "unknown"]
        self.current_category = "todos"
        self.filtered_items = self.available_items

        # Fontes
        self.font = pygame.font.Font(None, 20)
        self.font_small = pygame.font.Font(None, 16)
        self.font_title = pygame.font.Font(None, 24)

        self._init_buttons()
        self._update_max_scroll()

        print(f"TargetItemDialog inicializado - Catálogo com {len(self.available_items)} itens")

    def _init_buttons(self):
        x, y, w, h = self.rect

        self.close_button = pygame.Rect(x + w - 30, y + 5, 25, 25)
        self.select_button = pygame.Rect(x + (w - 160) // 2, y + h - 50, 80, 30)
        self.cancel_button = pygame.Rect(x + (w - 160) // 2 + 90, y + h - 50, 80, 30)

        # Botões de categoria
        self.category_prev = pygame.Rect(x + 200, y + 50, 25, 25)
        self.category_next = pygame.Rect(x + 330, y + 50, 25, 25)
        self.category_display = pygame.Rect(x + 230, y + 50, 95, 25)

    def _update_button_positions(self):
        x, y, w, h = self.rect
        self.close_button.x = x + w - 30
        self.close_button.y = y + 5
        self.select_button.x = x + (w - 160) // 2
        self.select_button.y = y + h - 50
        self.cancel_button.x = x + (w - 160) // 2 + 90
        self.cancel_button.y = y + h - 50
        self.category_prev.x = x + 200
        self.category_prev.y = y + 50
        self.category_next.x = x + 330
        self.category_next.y = y + 50
        self.category_display.x = x + 230
        self.category_display.y = y + 50

    def _update_max_scroll(self):
        """Atualiza limites de scroll do catálogo"""
        visible_items = 6  # Número de itens visíveis
        self.max_catalog_scroll = max(0, len(self.filtered_items) - visible_items)
        self.catalog_scroll = min(self.catalog_scroll, self.max_catalog_scroll)

    def _change_category(self, direction):
        """Muda a categoria atual"""
        current_idx = self.categories.index(self.current_category)
        new_idx = (current_idx + direction) % len(self.categories)
        self.current_category = self.categories[new_idx]

        # Filtra itens
        if self.current_category == "todos":
            self.filtered_items = self.available_items
        else:
            self.filtered_items = self.catalog.get_items_by_category(self.current_category)

        self.catalog_scroll = 0
        self._update_max_scroll()

    def handle_event(self, event):
        if not self.visible:
            return None

        mouse_pos = pygame.mouse.get_pos()
        mouse_x, mouse_y = mouse_pos

        if event.type == pygame.MOUSEBUTTONDOWN:
            if event.button == 1:
                return self._handle_left_click(mouse_x, mouse_y)
            elif event.button == 4:  # Scroll up
                self.catalog_scroll = max(0, self.catalog_scroll - 1)
                return None
            elif event.button == 5:  # Scroll down
                self.catalog_scroll = min(self.max_catalog_scroll, self.catalog_scroll + 1)
                return None

        elif event.type == pygame.MOUSEMOTION:
            if self.dragging:
                self.rect.x = mouse_x - self.drag_offset_x
                self.rect.y = mouse_y - self.drag_offset_y
                self._update_button_positions()
                return None

        elif event.type == pygame.MOUSEBUTTONUP:
            if event.button == 1:
                self.dragging = False
                return None

        elif event.type == pygame.KEYDOWN:
            if event.key == pygame.K_ESCAPE:
                self.visible = False
                return None

        return None

    def _handle_left_click(self, mouse_x, mouse_y):
        # Título para arrastar
        title_rect = pygame.Rect(self.rect.x, self.rect.y, self.rect.width, 30)
        if title_rect.collidepoint(mouse_x, mouse_y):
            self.dragging = True
            self.drag_offset_x = mouse_x - self.rect.x
            self.drag_offset_y = mouse_y - self.rect.y
            return None

        # Botão fechar
        if self.close_button.collidepoint(mouse_x, mouse_y):
            self.visible = False
            return None

        # Botão selecionar
        if self.select_button.collidepoint(mouse_x, mouse_y):
            self.visible = False
            return "selected"

        # Botão cancelar
        if self.cancel_button.collidepoint(mouse_x, mouse_y):
            self.visible = False
            return None

        # Botões de categoria
        if self.category_prev.collidepoint(mouse_x, mouse_y):
            self._change_category(-1)
            return None
        if self.category_next.collidepoint(mouse_x, mouse_y):
            self._change_category(1)
            return None

        # Catálogo de itens - seleciona o item
        catalog_x = self.rect.x + 20
        catalog_y = self.rect.y + 100 - self.catalog_scroll * 25

        for i, item in enumerate(self.filtered_items):
            item_rect = pygame.Rect(catalog_x, catalog_y + i * 25, self.rect.width - 40, 23)
            if item_rect.collidepoint(mouse_x, mouse_y):
                self.selected_item_id = item["id"]
                self.selected_item_name = item["name"]
                print(f"Item selecionado: {item['name']} (ID: {item['id']})")
                return None

        return None

    def render(self, screen):
        if not self.visible:
            return

        # Overlay
        overlay = pygame.Surface((screen.get_width(), screen.get_height()))
        overlay.set_alpha(180)
        overlay.fill((0, 0, 0))
        screen.blit(overlay, (0, 0))

        # Fundo
        pygame.draw.rect(screen, (40, 40, 50), self.rect, border_radius=10)
        pygame.draw.rect(screen, (255, 215, 0), self.rect, 2, border_radius=10)

        # Título
        title = self.font_title.render("Selecionar Item", True, (255, 255, 255))
        screen.blit(title, (self.rect.x + 10, self.rect.y + 10))

        # Botão fechar
        pygame.draw.rect(screen, (80, 80, 90), self.close_button)
        pygame.draw.line(screen, (255, 255, 255),
                         (self.close_button.x + 5, self.close_button.y + 5),
                         (self.close_button.right - 5, self.close_button.bottom - 5), 2)
        pygame.draw.line(screen, (255, 255, 255),
                         (self.close_button.right - 5, self.close_button.y + 5),
                         (self.close_button.x + 5, self.close_button.bottom - 5), 2)

        # Instrução
        inst_text = self.font_small.render("Clique em um item para selecionar:", True, (200, 200, 200))
        screen.blit(inst_text, (self.rect.x + 10, self.rect.y + 40))

        # Controles de categoria
        pygame.draw.rect(screen, (60, 60, 70), self.category_prev, border_radius=3)
        pygame.draw.polygon(screen, (255, 255, 255), [
            (self.category_prev.x + 8, self.category_prev.centery),
            (self.category_prev.x + 18, self.category_prev.y + 5),
            (self.category_prev.x + 18, self.category_prev.y + 20)
        ])

        pygame.draw.rect(screen, (60, 60, 70), self.category_next, border_radius=3)
        pygame.draw.polygon(screen, (255, 255, 255), [
            (self.category_next.x + 17, self.category_next.centery),
            (self.category_next.x + 7, self.category_next.y + 5),
            (self.category_next.x + 7, self.category_next.y + 20)
        ])

        # Display da categoria
        pygame.draw.rect(screen, (50, 50, 60), self.category_display, border_radius=3)
        cat_text = self.font_small.render(self.current_category.upper(), True, (255, 255, 255))
        cat_x = self.category_display.x + (self.category_display.width - cat_text.get_width()) // 2
        screen.blit(cat_text, (cat_x, self.category_display.y + 5))

        # Lista do catálogo
        clip_rect = pygame.Rect(
            self.rect.x + 10,
            self.rect.y + 85,
            self.rect.width - 20,
            170
        )
        old_clip = screen.get_clip()
        screen.set_clip(clip_rect)

        catalog_x = self.rect.x + 15
        catalog_y = self.rect.y + 90 - self.catalog_scroll * 25

        for i, item in enumerate(self.filtered_items):
            item_rect = pygame.Rect(catalog_x, catalog_y + i * 25, self.rect.width - 40, 23)

            if item_rect.bottom < clip_rect.top or item_rect.top > clip_rect.bottom:
                continue

            # Destaca o item selecionado
            if item["id"] == self.selected_item_id:
                bg_color = (80, 100, 120)
                border_color = (255, 215, 0)
                border_width = 2
            else:
                bg_color = (50, 50, 60) if i % 2 == 0 else (45, 45, 55)
                border_color = None
                border_width = 0

            pygame.draw.rect(screen, bg_color, item_rect)
            if border_color:
                pygame.draw.rect(screen, border_color, item_rect, border_width)

            # Preview do sprite (se existir) - AGORA 16x16
            if item["sprite"] and os.path.exists(item["sprite"]):
                try:
                    preview = pygame.image.load(item["sprite"]).convert_alpha()
                    preview = pygame.transform.scale(preview, (16, 16))  # Redimensiona para 16x16
                    screen.blit(preview, (item_rect.x + 2, item_rect.y + 2))
                except:
                    pygame.draw.rect(screen, (100, 100, 100), (item_rect.x + 2, item_rect.y + 2, 16, 16))
            else:
                colors = [(255, 215, 0), (255, 0, 0), (0, 255, 0), (0, 0, 255)]
                color = colors[(item["id"] - 1) % len(colors)]
                pygame.draw.rect(screen, color, (item_rect.x + 2, item_rect.y + 2, 16, 16))

            # Nome do item
            name_text = self.font_small.render(f"{item['name']}", True, (255, 255, 255))
            screen.blit(name_text, (item_rect.x + 22, item_rect.y + 4))  # Ajustado para 16px + 6px de margem

        screen.set_clip(old_clip)

        # Mostra item selecionado atualmente
        selected_text = self.font.render(
            f"Selecionado: {self.selected_item_name} (ID: {self.selected_item_id})",
            True, (255, 215, 0)
        )
        screen.blit(selected_text, (self.rect.x + 10, self.rect.y + 260))

        # Botões
        pygame.draw.rect(screen, (0, 150, 0), self.select_button, border_radius=5)
        select_text = self.font.render("Selecionar", True, (255, 255, 255))
        select_x = self.select_button.x + (self.select_button.width - select_text.get_width()) // 2
        screen.blit(select_text, (select_x, self.select_button.y + 5))

        pygame.draw.rect(screen, (150, 0, 0), self.cancel_button, border_radius=5)
        cancel_text = self.font.render("Cancelar", True, (255, 255, 255))
        cancel_x = self.cancel_button.x + (self.cancel_button.width - cancel_text.get_width()) // 2
        screen.blit(cancel_text, (cancel_x, self.cancel_button.y + 5))