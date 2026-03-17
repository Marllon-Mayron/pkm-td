# src/scenes/editor/components/target_item_dialog.py

import pygame


class TargetItemDialog:
    def __init__(self, x, y, width, height, item_manager):
        self.rect = pygame.Rect(x, y, width, height)
        self.visible = True
        self.item_manager = item_manager

        self.dragging = False
        self.drag_offset_x = 0
        self.drag_offset_y = 0

        # Item selecionado para edição
        self.selected_item_index = -1

        # Campos de entrada
        self.active_input = None
        # REMOVIDO: temp_quantity
        self.temp_item_id = "1"

        # Scroll
        self.items_scroll = 0
        self.max_scroll = 0

        # Fontes
        self.font = pygame.font.Font(None, 20)
        self.font_small = pygame.font.Font(None, 16)
        self.font_title = pygame.font.Font(None, 24)

        self._init_buttons()
        self._update_max_scroll()

    def _init_buttons(self):
        x, y, w, h = self.rect

        self.close_button = pygame.Rect(x + w - 30, y + 5, 25, 25)
        self.save_button = pygame.Rect(x + w - 180, y + h - 40, 80, 30)
        self.cancel_button = pygame.Rect(x + w - 90, y + h - 40, 80, 30)

        # Botões de ação
        self.add_button = pygame.Rect(x + 10, y + 70, 100, 30)
        self.remove_button = pygame.Rect(x + 120, y + 70, 100, 30)

        # Inputs para novo item (AGORA SÓ ID)
        self.item_type_input = pygame.Rect(x + 250, y + 70, 80, 30)  # Mais largo

    def handle_event(self, event):
        if not self.visible:
            return False

        mouse_pos = pygame.mouse.get_pos()
        mouse_x, mouse_y = mouse_pos

        if event.type == pygame.MOUSEBUTTONDOWN:
            if event.button == 1:
                return self._handle_left_click(mouse_x, mouse_y)
            elif event.button == 4:  # Scroll up
                self.items_scroll = max(0, self.items_scroll - 30)
                self._update_max_scroll()
                return True
            elif event.button == 5:  # Scroll down
                self.items_scroll = min(self.max_scroll, self.items_scroll + 30)
                self._update_max_scroll()
                return True

        elif event.type == pygame.MOUSEMOTION:
            if self.dragging:
                self.rect.x = mouse_x - self.drag_offset_x
                self.rect.y = mouse_y - self.drag_offset_y
                self._update_button_positions()
                return True

        elif event.type == pygame.MOUSEBUTTONUP:
            if event.button == 1:
                self.dragging = False
                return True

        elif event.type == pygame.KEYDOWN:
            if self.active_input:
                return self._handle_keydown(event)
            elif event.key == pygame.K_ESCAPE:
                self.visible = False
                return True

        return False

    def _handle_left_click(self, mouse_x, mouse_y):
        # Título para arrastar
        title_rect = pygame.Rect(self.rect.x, self.rect.y, self.rect.width, 30)
        if title_rect.collidepoint(mouse_x, mouse_y):
            self.dragging = True
            self.drag_offset_x = mouse_x - self.rect.x
            self.drag_offset_y = mouse_y - self.rect.y
            return True

        # Botão fechar
        if self.close_button.collidepoint(mouse_x, mouse_y):
            self.visible = False
            return True

        # Botões de ação
        if self.save_button.collidepoint(mouse_x, mouse_y):
            self.visible = False
            return "saved"

        if self.cancel_button.collidepoint(mouse_x, mouse_y):
            self.visible = False
            return True

        # Botão adicionar item
        if self.add_button.collidepoint(mouse_x, mouse_y):
            try:
                item_id = int(self.temp_item_id) if self.temp_item_id else 1

                # MODIFICADO: Adiciona SEM quantidade
                index = self.item_manager.add_item(0, 0, item_id)
                if index >= 0:
                    self.selected_item_index = index
                self._update_max_scroll()
                print(f"Item {item_id} criado - posicione no mapa")
            except ValueError:
                print("Erro: ID deve ser número")
            return True

        # Botão remover item
        if self.remove_button.collidepoint(mouse_x, mouse_y):
            if 0 <= self.selected_item_index < len(self.item_manager.items):
                item = self.item_manager.items[self.selected_item_index]
                self.item_manager.remove_item(item)
                self.selected_item_index = -1
                self._update_max_scroll()
                print("Item removido")
            return True

        # Input field (agora só ID)
        if self.item_type_input.collidepoint(mouse_x, mouse_y):
            self.active_input = "item_id"
            return True

        # Lista de itens
        list_x = self.rect.x + 10
        list_y = self.rect.y + 110 - self.items_scroll

        for i, item in enumerate(self.item_manager.items):
            item_rect = pygame.Rect(list_x, list_y + i * 40, self.rect.width - 30, 35)
            if item_rect.collidepoint(mouse_x, mouse_y):
                self.selected_item_index = i
                # Atualiza campo com o ID do item selecionado
                self.temp_item_id = str(item.item_id)
                print(f"Item selecionado: {item.name} (ID:{item.item_id})")
                return True

        return True

    def _handle_keydown(self, event):
        if event.key == pygame.K_RETURN:
            self.active_input = None
            return True
        elif event.key == pygame.K_BACKSPACE:
            if self.active_input == "item_id":
                self.temp_item_id = self.temp_item_id[:-1]
            return True
        elif event.unicode.isdigit():
            if self.active_input == "item_id":
                self.temp_item_id += event.unicode
            return True
        return False

    def _update_button_positions(self):
        x, y, w, h = self.rect
        self.close_button.x = x + w - 30
        self.close_button.y = y + 5
        self.save_button.x = x + w - 180
        self.save_button.y = y + h - 40
        self.cancel_button.x = x + w - 90
        self.cancel_button.y = y + h - 40
        self.add_button.x = x + 10
        self.add_button.y = y + 70
        self.remove_button.x = x + 120
        self.remove_button.y = y + 70
        self.item_type_input.x = x + 250
        self.item_type_input.y = y + 70

    def _update_max_scroll(self):
        total_height = len(self.item_manager.items) * 40
        visible_height = self.rect.height - 200
        self.max_scroll = max(0, total_height - visible_height)
        # Garante que scroll não ultrapasse
        self.items_scroll = min(self.items_scroll, self.max_scroll)

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
        title = self.font_title.render("Itens Alvo", True, (255, 255, 255))
        screen.blit(title, (self.rect.x + 10, self.rect.y + 10))

        # Botão fechar
        pygame.draw.rect(screen, (80, 80, 90), self.close_button)
        pygame.draw.line(screen, (255, 255, 255),
                         (self.close_button.x + 5, self.close_button.y + 5),
                         (self.close_button.right - 5, self.close_button.bottom - 5), 2)
        pygame.draw.line(screen, (255, 255, 255),
                         (self.close_button.right - 5, self.close_button.y + 5),
                         (self.close_button.x + 5, self.close_button.bottom - 5), 2)

        # Área de criação de item
        add_label = self.font_small.render("Adicionar:", True, (200, 200, 200))
        screen.blit(add_label, (self.rect.x + 10, self.rect.y + 50))

        # Botões de ação
        pygame.draw.rect(screen, (0, 100, 0), self.add_button, border_radius=5)
        add_text = self.font_small.render("+ Item", True, (255, 255, 255))
        screen.blit(add_text, (self.add_button.x + 5, self.add_button.y + 7))

        pygame.draw.rect(screen, (100, 0, 0), self.remove_button, border_radius=5)
        remove_text = self.font_small.render("- Remover", True, (255, 255, 255))
        screen.blit(remove_text, (self.remove_button.x + 5, self.remove_button.y + 7))

        # MODIFICADO: Label ID
        id_label = self.font_small.render("ID:", True, (200, 200, 200))
        screen.blit(id_label, (self.item_type_input.x - 20, self.item_type_input.y + 7))

        # Item ID input
        color = (100, 150, 255) if self.active_input == "item_id" else (80, 80, 90)
        pygame.draw.rect(screen, color, self.item_type_input, 2)
        id_surf = self.font_small.render(self.temp_item_id, True, (255, 255, 255))
        screen.blit(id_surf, (self.item_type_input.x + 5, self.item_type_input.y + 5))

        # Lista de itens
        list_title = self.font.render("Itens no mapa:", True, (255, 255, 255))
        screen.blit(list_title, (self.rect.x + 10, self.rect.y + 105))

        # Área de clipping
        clip_rect = pygame.Rect(
            self.rect.x + 5,
            self.rect.y + 125,
            self.rect.width - 10,
            self.rect.height - 170
        )
        old_clip = screen.get_clip()
        screen.set_clip(clip_rect)

        list_x = self.rect.x + 10
        list_y = self.rect.y + 125 - self.items_scroll

        for i, item in enumerate(self.item_manager.items):
            item_rect = pygame.Rect(list_x, list_y + i * 40, self.rect.width - 30, 35)

            if item_rect.bottom < clip_rect.top or item_rect.top > clip_rect.bottom:
                continue

            # Fundo
            if i == self.selected_item_index:
                bg_color = (80, 100, 120)
                border_color = (255, 215, 0)
            else:
                bg_color = (60, 60, 70) if i % 2 == 0 else (55, 55, 65)
                border_color = (80, 80, 90)

            pygame.draw.rect(screen, bg_color, item_rect, border_radius=3)
            pygame.draw.rect(screen, border_color, item_rect, 1, border_radius=3)

            # MODIFICADO: Info do item (SEM quantidade)
            item_text = f"ID:{item.item_id} {item.name}"
            text_surf = self.font_small.render(item_text, True, (255, 255, 255))
            screen.blit(text_surf, (item_rect.x + 5, item_rect.y + 10))

            # Posição
            pos_text = f"({int(item.x)},{int(item.y)})"
            pos_surf = self.font_small.render(pos_text, True, (200, 200, 200))
            screen.blit(pos_surf, (item_rect.right - 70, item_rect.y + 10))

        screen.set_clip(old_clip)

        # Instruções
        if self.selected_item_index >= 0:
            help_text = self.font_small.render(
                "Clique no mapa para posicionar o item selecionado",
                True, (255, 255, 100)
            )
            screen.blit(help_text, (self.rect.x + 10, self.rect.bottom - 70))
        else:
            help_text = self.font_small.render(
                "Selecione um item na lista ou crie um novo (+ Item)",
                True, (200, 200, 200)
            )
            screen.blit(help_text, (self.rect.x + 10, self.rect.bottom - 70))

        # Botões de ação final
        pygame.draw.rect(screen, (0, 150, 0), self.save_button, border_radius=5)
        save_text = self.font.render("Salvar", True, (255, 255, 255))
        save_x = self.save_button.x + (self.save_button.width - save_text.get_width()) // 2
        save_y = self.save_button.y + (self.save_button.height - save_text.get_height()) // 2
        screen.blit(save_text, (save_x, save_y))

        pygame.draw.rect(screen, (150, 0, 0), self.cancel_button, border_radius=5)
        cancel_text = self.font.render("Cancelar", True, (255, 255, 255))
        cancel_x = self.cancel_button.x + (self.cancel_button.width - cancel_text.get_width()) // 2
        cancel_y = self.cancel_button.y + (self.cancel_button.height - cancel_text.get_height()) // 2
        screen.blit(cancel_text, (cancel_x, cancel_y))