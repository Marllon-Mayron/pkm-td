# src/scenes/editor/components/rewards_config_dialog.py

import pygame
from src.data.item_bag_catalog import item_bag_catalog
from src.managers.reward_template_manager import reward_template_manager


class RewardsConfigDialog:
    def __init__(self, x, y, width, height,
                 current_money=100, current_xp=50,
                 item_rewards=None, drop_chance=0.0, max_items=3,
                 template_name=None):
        # Aumentar um pouco o tamanho padrão se necessário
        if width < 700:
            width = 700
        if height < 550:
            height = 550

        self.rect = pygame.Rect(x, y, width, height)
        self.visible = True

        # Valores atuais
        self.current_money = current_money
        self.current_xp = current_xp
        self.drop_chance = drop_chance
        self.max_items = max_items

        # Dicionário: item_id -> peso (apenas os selecionados)
        self.item_weights = {}
        if item_rewards:
            for entry in item_rewards:
                self.item_weights[entry['item_id']] = entry.get('weight', 100)

        # Templates
        self.templates = reward_template_manager.get_all_templates()
        self.template_names = list(self.templates.keys())
        self.selected_template_name = template_name if template_name in self.templates else None

        # Estado de edição
        self.editing_template_name = False
        self.template_name_input = ""

        # Campos temporários
        self.temp_money = str(current_money)
        self.temp_xp = str(current_xp)
        self.temp_drop_chance = str(int(drop_chance * 100))
        self.temp_max_items = str(max_items)

        # Foco
        self.active_input = "money"  # money, xp, drop_chance, max_items

        # Scroll na lista de itens disponíveis
        self.scroll_offset_available = 0
        self.scroll_offset_selected = 0

        # Lista de itens disponíveis (todos do catálogo)
        self.available_items = sorted(item_bag_catalog.items.keys())
        self.selected_items_list = list(self.item_weights.keys())  # ordem de seleção

        # Pré-visualização dos sprites selecionados
        self.preview_sprites = {}  # item_id -> sprite escalado
        self._update_preview_sprites()

        # Layout calculado
        self._calculate_layout()

    def _calculate_layout(self):
        x, y, w, h = self.rect
        margin = 15
        label_width = 160
        field_width = 100
        field_height = 28

        # Linha 1: Money
        self.money_rect = pygame.Rect(x + margin + label_width, y + 50, field_width, field_height)
        self.money_label = pygame.Rect(x + margin, y + 50, label_width, field_height)

        # Linha 2: XP
        self.xp_rect = pygame.Rect(x + margin + label_width, y + 50 + 40, field_width, field_height)
        self.xp_label = pygame.Rect(x + margin, y + 50 + 40, label_width, field_height)

        # Linha 3: Drop chance
        self.drop_chance_rect = pygame.Rect(x + margin + label_width, y + 50 + 80, field_width, field_height)
        self.drop_chance_label = pygame.Rect(x + margin, y + 50 + 80, label_width, field_height)

        # Linha 4: Max items
        self.max_items_rect = pygame.Rect(x + margin + label_width, y + 50 + 120, field_width, field_height)
        self.max_items_label = pygame.Rect(x + margin, y + 50 + 120, label_width, field_height)

        # Lista de itens disponíveis (esquerda) e selecionados (direita)
        list_y = y + 50 + 170
        list_height = h - 310
        list_width = (w - 3 * margin - 10) // 2
        self.available_list_rect = pygame.Rect(x + margin, list_y, list_width, list_height)
        self.selected_list_rect = pygame.Rect(x + margin + list_width + 10, list_y, list_width, list_height)

        # Área de preview dos sprites selecionados (abaixo da lista selecionada)
        preview_y = self.selected_list_rect.bottom + 10
        preview_height = 80
        self.preview_rect = pygame.Rect(self.selected_list_rect.x, preview_y, list_width, preview_height)

        # Botões de template
        template_y = self.available_list_rect.bottom + 10
        self.save_template_rect = pygame.Rect(x + margin, template_y, 100, 28)
        self.load_template_rect = pygame.Rect(x + margin + 110, template_y, 100, 28)
        self.delete_template_rect = pygame.Rect(x + margin + 220, template_y, 100, 28)
        self.new_template_rect = pygame.Rect(x + margin + 330, template_y, 100, 28)

        # Dropdown de templates
        self.template_dropdown_rect = pygame.Rect(x + margin + 440, template_y, 150, 28)
        # Campo de nome para salvar
        self.template_name_rect = pygame.Rect(x + margin + 440, template_y + 40, 150, 28)

        # Botões Confirmar/Cancelar
        confirm_w = 120
        cancel_w = 120
        total_w = confirm_w + cancel_w + 20
        start_x = x + (w - total_w) // 2
        self.confirm_rect = pygame.Rect(start_x, y + h - 50, confirm_w, 35)
        self.cancel_rect = pygame.Rect(start_x + confirm_w + 20, y + h - 50, cancel_w, 35)

    def _update_preview_sprites(self):
        """Atualiza os sprites para pré-visualização dos itens selecionados."""
        self.preview_sprites = {}
        for item_id in self.selected_items_list:
            sprite = item_bag_catalog.get_sprite(item_id, scaled=True)
            if sprite:
                self.preview_sprites[item_id] = sprite

    def handle_event(self, event):
        if not self.visible:
            return None

        if event.type == pygame.KEYDOWN:
            return self._handle_keydown(event)
        elif event.type == pygame.MOUSEBUTTONDOWN:
            if event.button == 1:
                return self._handle_mousedown(event)
        elif event.type == pygame.MOUSEWHEEL:
            mouse_pos = pygame.mouse.get_pos()
            if self.available_list_rect.collidepoint(mouse_pos):
                max_scroll = max(0, len(self.available_items) - self._visible_items_available())
                self.scroll_offset_available = max(0, min(self.scroll_offset_available - event.y, max_scroll))
            elif self.selected_list_rect.collidepoint(mouse_pos):
                max_scroll = max(0, len(self.selected_items_list) - self._visible_items_selected())
                self.scroll_offset_selected = max(0, min(self.scroll_offset_selected - event.y, max_scroll))
            return None
        return None

    def _visible_items_available(self):
        return self.available_list_rect.height // 22

    def _visible_items_selected(self):
        return self.selected_list_rect.height // 22

    def _handle_keydown(self, event):
        if event.key == pygame.K_RETURN:
            if self.editing_template_name:
                if self.template_name_input.strip():
                    self._save_current_as_template(self.template_name_input.strip())
                self.editing_template_name = False
                return None
            else:
                return self.confirm()
        elif event.key == pygame.K_ESCAPE:
            self.visible = False
            return None
        elif event.key == pygame.K_TAB:
            fields = ["money", "xp", "drop_chance", "max_items"]
            if self.active_input in fields:
                idx = fields.index(self.active_input)
                self.active_input = fields[(idx + 1) % len(fields)]
            else:
                self.active_input = "money"
            return None
        elif event.key == pygame.K_BACKSPACE:
            if self.active_input == "money":
                self.temp_money = self.temp_money[:-1]
            elif self.active_input == "xp":
                self.temp_xp = self.temp_xp[:-1]
            elif self.active_input == "drop_chance":
                self.temp_drop_chance = self.temp_drop_chance[:-1]
            elif self.active_input == "max_items":
                self.temp_max_items = self.temp_max_items[:-1]
            return None
        else:
            if event.unicode.isdigit():
                if self.active_input == "money":
                    self.temp_money += event.unicode
                elif self.active_input == "xp":
                    self.temp_xp += event.unicode
                elif self.active_input == "drop_chance":
                    self.temp_drop_chance += event.unicode
                elif self.active_input == "max_items":
                    self.temp_max_items += event.unicode
                return None
        return None

    def _handle_mousedown(self, event):
        mouse_pos = event.pos

        # Campos de entrada
        if self.money_rect.collidepoint(mouse_pos):
            self.active_input = "money"
            return None
        elif self.xp_rect.collidepoint(mouse_pos):
            self.active_input = "xp"
            return None
        elif self.drop_chance_rect.collidepoint(mouse_pos):
            self.active_input = "drop_chance"
            return None
        elif self.max_items_rect.collidepoint(mouse_pos):
            self.active_input = "max_items"
            return None

        # Lista de itens disponíveis (clique para adicionar)
        if self.available_list_rect.collidepoint(mouse_pos):
            idx = (mouse_pos[1] - self.available_list_rect.y) // 22 + self.scroll_offset_available
            if 0 <= idx < len(self.available_items):
                item_id = self.available_items[idx]
                if item_id not in self.item_weights:
                    self.item_weights[item_id] = 100
                    if item_id not in self.selected_items_list:
                        self.selected_items_list.append(item_id)
                    self._update_preview_sprites()
            return None

        # Lista de itens selecionados (clique para remover ou ajustar peso)
        if self.selected_list_rect.collidepoint(mouse_pos):
            idx = (mouse_pos[1] - self.selected_list_rect.y) // 22 + self.scroll_offset_selected
            if 0 <= idx < len(self.selected_items_list):
                item_id = self.selected_items_list[idx]
                # Verifica se clicou no botão de "+" ou "-" (à direita)
                item_rect = pygame.Rect(self.selected_list_rect.x, self.selected_list_rect.y + idx * 22,
                                        self.selected_list_rect.width, 22)
                # Área do peso: à direita
                if mouse_pos[0] > item_rect.right - 60:
                    # Clique na área de ajuste de peso (vamos usar + e -)
                    # Vamos detectar se está na metade esquerda ou direita da área de ajuste
                    adjust_x = mouse_pos[0] - (item_rect.right - 60)
                    if adjust_x < 20:  # botão "-"
                        new_weight = max(1, self.item_weights.get(item_id, 100) - 10)
                        self.item_weights[item_id] = new_weight
                    elif adjust_x < 40:  # display do peso (clicar não faz nada, mas pode editar depois)
                        pass
                    else:  # botão "+"
                        new_weight = self.item_weights.get(item_id, 100) + 10
                        self.item_weights[item_id] = new_weight
                    return None
                else:
                    # Remove o item
                    if item_id in self.item_weights:
                        del self.item_weights[item_id]
                    if item_id in self.selected_items_list:
                        self.selected_items_list.remove(item_id)
                    self._update_preview_sprites()
                    return None
            return None

        # Template buttons
        if self.save_template_rect.collidepoint(mouse_pos):
            if self.item_weights:
                self.editing_template_name = True
                self.active_input = "template_name"
                self.template_name_input = self.selected_template_name if self.selected_template_name else "Novo Template"
            return None
        if self.load_template_rect.collidepoint(mouse_pos):
            if self.selected_template_name and self.selected_template_name in self.templates:
                template = self.templates[self.selected_template_name]
                items = template.get("items", [])
                self.item_weights = {}
                self.selected_items_list = []
                for entry in items:
                    self.item_weights[entry['item_id']] = entry.get('weight', 100)
                    self.selected_items_list.append(entry['item_id'])
                self._update_preview_sprites()
            return None
        if self.delete_template_rect.collidepoint(mouse_pos):
            if self.selected_template_name and self.selected_template_name in self.templates:
                reward_template_manager.delete_template(self.selected_template_name)
                self.templates = reward_template_manager.get_all_templates()
                self.template_names = list(self.templates.keys())
                self.selected_template_name = None
            return None
        if self.new_template_rect.collidepoint(mouse_pos):
            self.item_weights = {}
            self.selected_items_list = []
            self.selected_template_name = None
            self._update_preview_sprites()
            return None

        # Dropdown de templates
        if self.template_dropdown_rect.collidepoint(mouse_pos):
            # Abrir dropdown com lista de templates
            # Vamos exibir uma lista temporária - não implementamos dropdown complexo, mas faremos simples
            # Para simplificar, usaremos um seletor de clique: cada clique alterna para o próximo template
            if self.template_names:
                if self.selected_template_name in self.templates:
                    idx = self.template_names.index(self.selected_template_name)
                    next_idx = (idx + 1) % len(self.template_names)
                    self.selected_template_name = self.template_names[next_idx]
                else:
                    self.selected_template_name = self.template_names[0] if self.template_names else None
            return None

        # Confirmar/Cancelar
        if self.confirm_rect.collidepoint(mouse_pos):
            return self.confirm()
        if self.cancel_rect.collidepoint(mouse_pos):
            self.visible = False
            return None

        # Clicar fora
        if not self.rect.collidepoint(mouse_pos):
            self.visible = False
            return None

        return None

    def _save_current_as_template(self, name):
        if not self.item_weights:
            return
        item_list = [{"item_id": item_id, "weight": weight} for item_id, weight in self.item_weights.items()]
        reward_template_manager.add_template(name, item_list)
        self.templates = reward_template_manager.get_all_templates()
        self.template_names = list(self.templates.keys())
        self.selected_template_name = name
        self.editing_template_name = False

    def confirm(self):
        try:
            money = max(0, int(self.temp_money) if self.temp_money else 0)
            xp = max(0, int(self.temp_xp) if self.temp_xp else 0)
            drop_chance = max(0, min(100, int(self.temp_drop_chance) if self.temp_drop_chance else 0)) / 100.0
            max_items = max(0, int(self.temp_max_items) if self.temp_max_items else 3)

            item_rewards = [{"item_id": item_id, "weight": weight} for item_id, weight in self.item_weights.items()]

            self.visible = False
            return {
                'money': money,
                'experience': xp,
                'item_rewards': item_rewards,
                'drop_chance': drop_chance,
                'max_items': max_items,
                'template_name': self.selected_template_name
            }
        except ValueError:
            return None

    def render(self, screen, font, font_small):
        if not self.visible:
            return

        # Overlay
        overlay = pygame.Surface((screen.get_width(), screen.get_height()))
        overlay.set_alpha(128)
        overlay.fill((0, 0, 0))
        screen.blit(overlay, (0, 0))

        # Caixa de diálogo
        pygame.draw.rect(screen, (60, 60, 70), self.rect, border_radius=10)
        pygame.draw.rect(screen, (255, 215, 0), self.rect, 2, border_radius=10)

        # Título
        title = pygame.font.Font(None, 28).render("Configuração de Recompensas", True, (255, 255, 255))
        screen.blit(title, (self.rect.x + (self.rect.width - title.get_width()) // 2, self.rect.y + 10))

        x, y = self.rect.x, self.rect.y

        # ===== CAMPOS =====
        # Money
        label = font.render("Gold (Dinheiro):", True, (255, 215, 0))
        screen.blit(label, (self.money_label.x, self.money_label.y + 5))
        pygame.draw.rect(screen, (50, 50, 60), self.money_rect)
        border = (100, 150, 255) if self.active_input == "money" else (80, 80, 90)
        pygame.draw.rect(screen, border, self.money_rect, 2)
        val = font.render(self.temp_money, True, (255, 255, 255))
        screen.blit(val, (self.money_rect.x + 5, self.money_rect.y + 5))

        # XP
        label = font.render("Experience (XP):", True, (100, 200, 255))
        screen.blit(label, (self.xp_label.x, self.xp_label.y + 5))
        pygame.draw.rect(screen, (50, 50, 60), self.xp_rect)
        border = (100, 150, 255) if self.active_input == "xp" else (80, 80, 90)
        pygame.draw.rect(screen, border, self.xp_rect, 2)
        val = font.render(self.temp_xp, True, (255, 255, 255))
        screen.blit(val, (self.xp_rect.x + 5, self.xp_rect.y + 5))

        # Drop chance
        label = font.render("Chance de drop por kill (%):", True, (255, 200, 100))
        screen.blit(label, (self.drop_chance_label.x, self.drop_chance_label.y + 5))
        pygame.draw.rect(screen, (50, 50, 60), self.drop_chance_rect)
        border = (100, 150, 255) if self.active_input == "drop_chance" else (80, 80, 90)
        pygame.draw.rect(screen, border, self.drop_chance_rect, 2)
        val = font.render(self.temp_drop_chance + "%", True, (255, 255, 255))
        screen.blit(val, (self.drop_chance_rect.x + 5, self.drop_chance_rect.y + 5))

        # Max items
        label = font.render("Máximo de itens:", True, (200, 200, 200))
        screen.blit(label, (self.max_items_label.x, self.max_items_label.y + 5))
        pygame.draw.rect(screen, (50, 50, 60), self.max_items_rect)
        border = (100, 150, 255) if self.active_input == "max_items" else (80, 80, 90)
        pygame.draw.rect(screen, border, self.max_items_rect, 2)
        val = font.render(self.temp_max_items, True, (255, 255, 255))
        screen.blit(val, (self.max_items_rect.x + 5, self.max_items_rect.y + 5))

        # ===== LISTA DE ITENS DISPONÍVEIS (ESQUERDA) =====
        list_title = font_small.render("Itens disponíveis (clique para adicionar):", True, (200, 200, 200))
        screen.blit(list_title, (self.available_list_rect.x, self.available_list_rect.y - 20))

        pygame.draw.rect(screen, (40, 40, 50), self.available_list_rect, border_radius=4)
        pygame.draw.rect(screen, (100, 100, 120), self.available_list_rect, 1, border_radius=4)

        visible_avail = self._visible_items_available()
        start_avail = self.scroll_offset_available
        end_avail = min(start_avail + visible_avail, len(self.available_items))

        for i in range(start_avail, end_avail):
            item_id = self.available_items[i]
            item_data = item_bag_catalog.get_item(item_id)
            item_name = item_data['name'] if item_data else item_id
            is_selected = item_id in self.item_weights
            color = (255, 255, 255) if is_selected else (150, 150, 150)
            surf = font_small.render(item_name, True, color)
            y_pos = self.available_list_rect.y + (i - start_avail) * 22 + 2
            screen.blit(surf, (self.available_list_rect.x + 5, y_pos))

            if is_selected:
                # Checkmark
                check_rect = pygame.Rect(self.available_list_rect.right - 20, y_pos + 2, 16, 16)
                pygame.draw.rect(screen, (0, 200, 0), check_rect)
                pygame.draw.line(screen, (0, 0, 0), (check_rect.x + 3, check_rect.centery),
                                 (check_rect.x + 7, check_rect.bottom - 3), 2)
                pygame.draw.line(screen, (0, 0, 0), (check_rect.x + 7, check_rect.bottom - 3),
                                 (check_rect.right - 3, check_rect.y + 3), 2)

        # Scroll indicators
        if len(self.available_items) > visible_avail:
            if end_avail < len(self.available_items):
                pygame.draw.polygon(screen, (150, 150, 150),
                                    [(self.available_list_rect.right - 15, self.available_list_rect.bottom - 15),
                                     (self.available_list_rect.right - 25, self.available_list_rect.bottom - 25),
                                     (self.available_list_rect.right - 5, self.available_list_rect.bottom - 25)])
            if start_avail > 0:
                pygame.draw.polygon(screen, (150, 150, 150),
                                    [(self.available_list_rect.right - 15, self.available_list_rect.top + 15),
                                     (self.available_list_rect.right - 25, self.available_list_rect.top + 25),
                                     (self.available_list_rect.right - 5, self.available_list_rect.top + 25)])

        # ===== LISTA DE ITENS SELECIONADOS (DIREITA) =====
        list_title = font_small.render("Itens selecionados (clique para remover; +/- ajusta peso):", True, (200, 200, 200))
        screen.blit(list_title, (self.selected_list_rect.x, self.selected_list_rect.y - 20))

        pygame.draw.rect(screen, (40, 40, 50), self.selected_list_rect, border_radius=4)
        pygame.draw.rect(screen, (100, 100, 120), self.selected_list_rect, 1, border_radius=4)

        visible_sel = self._visible_items_selected()
        start_sel = self.scroll_offset_selected
        end_sel = min(start_sel + visible_sel, len(self.selected_items_list))

        for i in range(start_sel, end_sel):
            item_id = self.selected_items_list[i]
            item_data = item_bag_catalog.get_item(item_id)
            item_name = item_data['name'] if item_data else item_id
            weight = self.item_weights.get(item_id, 100)

            y_pos = self.selected_list_rect.y + (i - start_sel) * 22 + 2
            # Nome
            name_surf = font_small.render(item_name, True, (255, 255, 255))
            screen.blit(name_surf, (self.selected_list_rect.x + 5, y_pos))

            # Controles de peso (+ e -)
            control_x = self.selected_list_rect.right - 60
            # Botão "-"
            minus_rect = pygame.Rect(control_x, y_pos, 18, 18)
            pygame.draw.rect(screen, (100, 100, 150), minus_rect)
            pygame.draw.rect(screen, (200, 200, 200), minus_rect, 1)
            minus_text = font_small.render("-", True, (255, 255, 255))
            screen.blit(minus_text, (minus_rect.x + 4, minus_rect.y + 2))

            # Peso
            weight_surf = font_small.render(str(weight), True, (255, 215, 0))
            weight_x = control_x + 22
            screen.blit(weight_surf, (weight_x, y_pos + 2))

            # Botão "+"
            plus_rect = pygame.Rect(control_x + 40, y_pos, 18, 18)
            pygame.draw.rect(screen, (100, 100, 150), plus_rect)
            pygame.draw.rect(screen, (200, 200, 200), plus_rect, 1)
            plus_text = font_small.render("+", True, (255, 255, 255))
            screen.blit(plus_text, (plus_rect.x + 4, plus_rect.y + 2))

            # Se não houver espaço, desenha um indicador de scroll
            # (já tratado)

        # Scroll indicators for selected
        if len(self.selected_items_list) > visible_sel:
            if end_sel < len(self.selected_items_list):
                pygame.draw.polygon(screen, (150, 150, 150),
                                    [(self.selected_list_rect.right - 15, self.selected_list_rect.bottom - 15),
                                     (self.selected_list_rect.right - 25, self.selected_list_rect.bottom - 25),
                                     (self.selected_list_rect.right - 5, self.selected_list_rect.bottom - 25)])
            if start_sel > 0:
                pygame.draw.polygon(screen, (150, 150, 150),
                                    [(self.selected_list_rect.right - 15, self.selected_list_rect.top + 15),
                                     (self.selected_list_rect.right - 25, self.selected_list_rect.top + 25),
                                     (self.selected_list_rect.right - 5, self.selected_list_rect.top + 25)])

        # ===== PREVIEW DOS SPRITES =====
        preview_title = font_small.render("Preview dos itens selecionados:", True, (200, 200, 200))
        screen.blit(preview_title, (self.preview_rect.x, self.preview_rect.y - 20))

        pygame.draw.rect(screen, (40, 40, 50), self.preview_rect, border_radius=4)
        pygame.draw.rect(screen, (100, 100, 120), self.preview_rect, 1, border_radius=4)

        if self.preview_sprites:
            # Mostrar sprites lado a lado (até 6)
            sprite_size = 48
            spacing = 10
            total_width = len(self.preview_sprites) * (sprite_size + spacing) - spacing
            start_x = self.preview_rect.centerx - total_width // 2
            y_offset = self.preview_rect.centery - sprite_size // 2
            for idx, (item_id, sprite) in enumerate(self.preview_sprites.items()):
                x_pos = start_x + idx * (sprite_size + spacing)
                scaled = pygame.transform.scale(sprite, (sprite_size, sprite_size))
                screen.blit(scaled, (x_pos, y_offset))
        else:
            no_items = font_small.render("Nenhum item selecionado", True, (150, 150, 150))
            screen.blit(no_items, no_items.get_rect(center=self.preview_rect.center))

        # ===== TEMPLATES =====
        # Botões
        for rect, text, color in [
            (self.save_template_rect, "Salvar", (50, 100, 50)),
            (self.load_template_rect, "Carregar", (50, 50, 150)),
            (self.delete_template_rect, "Deletar", (150, 50, 50)),
            (self.new_template_rect, "Novo", (50, 50, 150))
        ]:
            pygame.draw.rect(screen, color, rect, border_radius=4)
            pygame.draw.rect(screen, (200, 200, 200), rect, 1, border_radius=4)
            btn_text = font_small.render(text, True, (255, 255, 255))
            screen.blit(btn_text, (rect.x + 5, rect.y + 5))

        # Dropdown de templates (simplificado: mostra o nome do template selecionado e alterna com clique)
        selected_display = self.selected_template_name if self.selected_template_name else "Selecione"
        pygame.draw.rect(screen, (50, 50, 80), self.template_dropdown_rect, border_radius=4)
        pygame.draw.rect(screen, (200, 200, 200), self.template_dropdown_rect, 1, border_radius=4)
        display_text = font_small.render(selected_display, True, (255, 255, 255))
        screen.blit(display_text, (self.template_dropdown_rect.x + 5, self.template_dropdown_rect.y + 5))

        # Se estiver editando nome do template
        if self.editing_template_name:
            pygame.draw.rect(screen, (50, 50, 60), self.template_name_rect)
            pygame.draw.rect(screen, (100, 150, 255), self.template_name_rect, 2)
            name_surf = font_small.render(self.template_name_input, True, (255, 255, 255))
            screen.blit(name_surf, (self.template_name_rect.x + 5, self.template_name_rect.y + 5))
            instr = font_small.render("Digite o nome e ENTER", True, (150, 150, 150))
            screen.blit(instr, (self.template_name_rect.right + 10, self.template_name_rect.y + 5))

        # ===== BOTÕES CONFIRMAR / CANCELAR =====
        pygame.draw.rect(screen, (0, 150, 0), self.confirm_rect, border_radius=5)
        pygame.draw.rect(screen, (255, 255, 255), self.confirm_rect, 1, border_radius=5)
        confirm_text = font.render("Confirmar", True, (255, 255, 255))
        screen.blit(confirm_text, (self.confirm_rect.centerx - confirm_text.get_width()//2,
                                   self.confirm_rect.centery - confirm_text.get_height()//2))

        pygame.draw.rect(screen, (150, 0, 0), self.cancel_rect, border_radius=5)
        pygame.draw.rect(screen, (255, 255, 255), self.cancel_rect, 1, border_radius=5)
        cancel_text = font.render("Cancelar", True, (255, 255, 255))
        screen.blit(cancel_text, (self.cancel_rect.centerx - cancel_text.get_width()//2,
                                  self.cancel_rect.centery - cancel_text.get_height()//2))