# src/scenes/shop_scene/shop_scene.py

"""
Tela da loja - UI profissional com responsividade
"""
import pygame
from src.scenes.base_scene import BaseScene
from src.data.item_bag_catalog import item_bag_catalog
from src.config.progress import progress_manager


class ShopItemCard:
    """Card de item na loja com design clean"""

    def __init__(self, item_data, index):
        self.item_data = item_data
        self.item_id = item_data["id"]
        self.name = item_data["name"]
        self.category = item_data["category"]
        self.description = item_data["description"]
        self.price = item_data.get("price", 100)
        self.index = index
        self.is_locked = False  # Novo: indica se o item está bloqueado
        self.unlock_phase = item_data.get("unlock_phase") or item_data.get("unlock_chapter")  # Fase necessária

        self.rect = pygame.Rect(0, 0, 0, 0)
        self.is_hovered = False
        self.owned_quantity = 0

        # Efeitos visuais
        self.hover_alpha = 0
        self.pulse_time = 0

    def update_position(self, x, y, width, height):
        self.rect = pygame.Rect(x, y, width, height)

    def update_owned(self, bag_items):
        self.owned_quantity = bag_items.get(self.item_id, 0)

    def update_animation(self, dt):
        """Atualiza animações do card"""
        self.pulse_time += dt

        if self.is_hovered and self.hover_alpha < 20:
            self.hover_alpha = min(20, self.hover_alpha + dt * 100)
        elif not self.is_hovered and self.hover_alpha > 0:
            self.hover_alpha = max(0, self.hover_alpha - dt * 100)

    def handle_event(self, event):
        # Se o item está bloqueado, não interage
        if self.is_locked:
            return None

        if event.type == pygame.MOUSEMOTION:
            was_hovered = self.is_hovered
            self.is_hovered = self.rect.collidepoint(event.pos)
            return was_hovered != self.is_hovered

        elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            if self.is_hovered:
                return self

        return None

    def _wrap_text(self, text, font, max_width):
        """Divide o texto em múltiplas linhas baseado na largura máxima"""
        words = text.split(' ')
        lines = []
        current_line = []

        for word in words:
            # Testa se adicionar a palavra atual ultrapassa a largura
            test_line = ' '.join(current_line + [word])
            if font.render(test_line, True, (255, 255, 255)).get_width() <= max_width:
                current_line.append(word)
            else:
                if current_line:  # Salva a linha atual
                    lines.append(' '.join(current_line))
                    current_line = [word]
                else:
                    # Se a palavra sozinha já ultrapassa, força a quebra
                    lines.append(word)
                    current_line = []

        if current_line:
            lines.append(' '.join(current_line))

        return lines

    def render(self, screen, fonts, selected=False):
        # Cores do tema clean
        colors = {
            'bg': (30, 30, 35, 240),
            'bg_hover': (40, 45, 55, 250),
            'bg_locked': (25, 25, 30, 200),  # Fundo mais escuro para itens bloqueados
            'border': (60, 65, 75, 255),
            'border_selected': (80, 160, 255, 255),
            'border_hover': (100, 140, 200, 255),
            'border_locked': (50, 45, 40, 255),  # Borda escura para bloqueados
            'text': (255, 255, 255, 255),
            'text_dim': (180, 190, 210, 255),
            'text_locked': (100, 100, 110, 255),  # Texto escurecido
            'price': (120, 255, 120, 255),
            'price_locked': (80, 100, 80, 255),  # Preço escurecido
            'description': (150, 160, 180, 255),
            'description_locked': (90, 95, 105, 255),  # Descrição escurecida
            'owned_bg': (45, 45, 55, 230),
            'lock_overlay': (0, 0, 0, 180)  # Overlay de bloqueio
        }

        # Determina cores baseadas no estado
        if self.is_locked:
            border_color = colors['border_locked']
            bg_color = colors['bg_locked']
            text_color = colors['text_locked']
            price_color = colors['price_locked']
            desc_color = colors['description_locked']
        elif selected:
            border_color = colors['border_selected']
            bg_color = (45, 55, 75, 250)
            text_color = colors['text'][:3]
            price_color = colors['price'][:3]
            desc_color = colors['description'][:3]
        elif self.is_hovered:
            border_color = colors['border_hover']
            bg_color = colors['bg_hover']
            text_color = colors['text'][:3]
            price_color = colors['price'][:3]
            desc_color = colors['description'][:3]
        else:
            border_color = colors['border']
            bg_color = colors['bg']
            text_color = colors['text'][:3]
            price_color = colors['price'][:3]
            desc_color = colors['description'][:3]

        # Sombra suave
        shadow_rect = self.rect.copy()
        shadow_rect.x += 2
        shadow_rect.y += 2
        pygame.draw.rect(screen, (0, 0, 0, 40), shadow_rect, border_radius=6)

        # Fundo principal
        pygame.draw.rect(screen, bg_color, self.rect, border_radius=6)

        # Borda
        pygame.draw.rect(screen, border_color, self.rect, 1, border_radius=6)

        # Sprite do item (com opacidade reduzida se bloqueado)
        sprite = item_bag_catalog.get_sprite(self.item_id, scaled=True)
        if sprite:
            if self.is_locked:
                # Cria uma versão escurecida do sprite
                locked_sprite = sprite.copy()
                locked_sprite.fill((50, 50, 60, 180), special_flags=pygame.BLEND_RGBA_MULT)
                screen.blit(locked_sprite, (self.rect.x + 6, self.rect.y + 16))
                # Desenha um cadeado sobre o sprite
                lock_font = pygame.font.Font(None, 24)
                lock_text = lock_font.render("🔒", True, (200, 180, 100))
                screen.blit(lock_text, (self.rect.x + 6, self.rect.y + 16))
            else:
                screen.blit(sprite, (self.rect.x + 6, self.rect.y + 16))

        # Nome do item
        name_text = fonts['medium'].render(self.name, True, text_color)
        screen.blit(name_text, (self.rect.x + 60, self.rect.y + 10))

        # Se está bloqueado, mostra a fase necessária
        if self.is_locked and self.unlock_phase:
            lock_text = fonts['small'].render(f"🔒 Desbloqueia na fase {self.unlock_phase}", True, (200, 180, 100))
            screen.blit(lock_text, (self.rect.x + 60, self.rect.y + 52))

        # DESCRIÇÃO
        max_desc_width = self.rect.width - 70
        desc_font = fonts['medium']

        # Quebra o texto em múltiplas linhas
        desc_lines = self._wrap_text(self.description, desc_font, max_desc_width)

        # Renderiza cada linha da descrição
        current_y = self.rect.y + 32
        line_height = desc_font.get_height() + 2

        # Limita a 3 linhas para não ocupar muito espaço
        max_lines = 3
        for i, line in enumerate(desc_lines[:max_lines]):
            desc_text = desc_font.render(line, True, desc_color)
            screen.blit(desc_text, (self.rect.x + 60, current_y))
            current_y += line_height

        # Se houver mais linhas, indica com um pequeno ícone
        if len(desc_lines) > max_lines:
            more_text = desc_font.render("...", True, desc_color)
            screen.blit(more_text, (self.rect.x + 60, current_y))

        # PREÇO (apenas se não estiver bloqueado, ou mostra "???")
        if not self.is_locked:
            price_text = fonts['large'].render(f"${self.price}", True, price_color)
            screen.blit(price_text, (self.rect.x + 60, self.rect.y + 52))

        # Quantidade possuída
        if self.owned_quantity > 0 and not self.is_locked:
            qty_text = fonts['medium'].render(f"possui: x{self.owned_quantity}", True, (180, 180, 200))
            screen.blit(qty_text, (self.rect.right - 80, self.rect.y + 10))

    def render_small(self, screen, fonts, x, y, width, height):
        """Renderiza card em tamanho pequeno (para visualização compacta)"""
        self.rect = pygame.Rect(x, y, width, height)
        self.render(screen, fonts, False)


class InventoryItemCard:
    """Card do inventário com design clean"""

    def __init__(self, item_id, item_data, quantity, index):
        self.item_id = item_id
        self.item_data = item_data
        self.name = item_data["name"]
        self.category = item_data["category"]
        self.description = item_data["description"]
        self.quantity = quantity
        self.index = index
        self.sell_price = int(item_data.get("price", 100) * 0.5)

        self.rect = pygame.Rect(0, 0, 0, 0)
        self.is_hovered = False

        # Efeitos visuais
        self.hover_alpha = 0

    def update_position(self, x, y, width, height):
        self.rect = pygame.Rect(x, y, width, height)

    def update_animation(self, dt):
        """Atualiza animações do card"""
        if self.is_hovered and self.hover_alpha < 20:
            self.hover_alpha = min(20, self.hover_alpha + dt * 100)
        elif not self.is_hovered and self.hover_alpha > 0:
            self.hover_alpha = max(0, self.hover_alpha - dt * 100)

    def handle_event(self, event):
        if event.type == pygame.MOUSEMOTION:
            was_hovered = self.is_hovered
            self.is_hovered = self.rect.collidepoint(event.pos)
            return was_hovered != self.is_hovered

        elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            if self.is_hovered:
                return self

        return None

    def render(self, screen, fonts, selected=False):
        # Cores do tema clean para inventário
        colors = {
            'bg': (35, 30, 35, 240),
            'bg_hover': (50, 40, 50, 250),
            'border': (75, 65, 75, 255),
            'border_selected': (255, 180, 120, 255),
            'border_hover': (180, 130, 100, 255),
            'text': (255, 240, 230, 255),
            'text_dim': (200, 180, 170, 255),
            'sell_price': (255, 160, 160, 255),
            'description': (200, 180, 170, 255)
        }

        # Determina cores baseadas no estado
        if selected:
            border_color = colors['border_selected']
            bg_color = (70, 50, 60, 250)
        elif self.is_hovered:
            border_color = colors['border_hover']
            bg_color = colors['bg_hover']
        else:
            border_color = colors['border']
            bg_color = colors['bg']

        # Sombra suave
        shadow_rect = self.rect.copy()
        shadow_rect.x += 2
        shadow_rect.y += 2
        pygame.draw.rect(screen, (0, 0, 0, 40), shadow_rect, border_radius=6)

        # Fundo principal
        pygame.draw.rect(screen, bg_color, self.rect, border_radius=6)

        # Borda
        pygame.draw.rect(screen, border_color, self.rect, 1, border_radius=6)

        # Sprite do item
        sprite = item_bag_catalog.get_sprite(self.item_id, scaled=True)
        if sprite:
            screen.blit(sprite, (self.rect.x + 6, self.rect.y + 16))

        # Nome do item
        name_text = fonts['medium'].render(self.name, True, colors['text'][:3])
        screen.blit(name_text, (self.rect.x + 60, self.rect.y + 10))

        # DESCRIÇÃO
        max_desc_width = self.rect.width - 70
        description = self.description
        if len(description) > 35:
            description = description[:32] + "..."

        desc_text = fonts['small'].render(description, True, colors['description'][:3])
        if desc_text.get_width() > max_desc_width:
            while len(description) > 3 and desc_text.get_width() > max_desc_width:
                description = description[:-1]
                desc_text = fonts['small'].render(description + "...", True, colors['description'][:3])

        screen.blit(desc_text, (self.rect.x + 60, self.rect.y + 32))

        # PREÇO DE VENDA
        sell_text = fonts['medium'].render(f"${self.sell_price}", True, colors['sell_price'][:3])
        screen.blit(sell_text, (self.rect.x + 60, self.rect.y + 52))

        # Quantidade
        qty_text = fonts['small'].render(f"x{self.quantity}", True, (255, 220, 100))
        screen.blit(qty_text, (self.rect.right - 40, self.rect.y + 15))


class CategorySelector:
    """Seletor de categorias clean"""

    def __init__(self, x, y, width):
        self.rect = pygame.Rect(x, y, width, 35)
        self.categories = [
            ("all", "Todos"),
            ("pokeball", "Pokeballs"),
            ("medicine", "Medicina"),
            ("tm", "TMs/HMs"),
            ("items", "Itens"),
        ]
        self.selected = "all"
        self.buttons = []
        self.hovered_button = None

        # Calcula largura dos botões
        btn_width = (width - 20) // len(self.categories)
        for i, (cat_id, cat_name) in enumerate(self.categories):
            btn_x = x + 10 + i * btn_width
            self.buttons.append({
                "id": cat_id,
                "name": cat_name,
                "rect": pygame.Rect(btn_x, y + 5, btn_width - 5, 25)
            })

    def handle_event(self, event):
        if event.type == pygame.MOUSEMOTION:
            self.hovered_button = None
            for btn in self.buttons:
                if btn["rect"].collidepoint(event.pos):
                    self.hovered_button = btn["id"]
                    break
            return None

        elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            for btn in self.buttons:
                if btn["rect"].collidepoint(event.pos):
                    if self.selected != btn["id"]:
                        self.selected = btn["id"]
                        return self.selected
        return None

    def render(self, screen, fonts):
        for btn in self.buttons:
            selected = (btn["id"] == self.selected)
            hovered = (btn["id"] == self.hovered_button)

            # Determina cores - clean
            if selected:
                bg_color = (60, 100, 140, 200)
                text_color = (255, 255, 255)
            elif hovered:
                bg_color = (50, 60, 80, 180)
                text_color = (220, 220, 240)
            else:
                bg_color = (30, 35, 45, 150)
                text_color = (180, 190, 210)

            # Fundo
            pygame.draw.rect(screen, bg_color, btn["rect"], border_radius=4)

            # Borda sutil
            pygame.draw.rect(screen, (80, 90, 110), btn["rect"], 1, border_radius=4)

            # Texto
            text = fonts['small'].render(btn["name"], True, text_color)
            text_x = btn["rect"].x + (btn["rect"].width - text.get_width()) // 2
            text_y = btn["rect"].y + (btn["rect"].height - text.get_height()) // 2
            screen.blit(text, (text_x, text_y))


class QuantitySelector:
    """Seletor de quantidade clean"""

    def __init__(self, x, y, width, height):
        self.rect = pygame.Rect(x, y, width, height)
        self.quantity = 1
        self.max_quantity = 99
        self.min_quantity = 1
        self.visible = False
        self.mode = "buy"
        self.item = None
        self.total_price = 0

        # Botões
        btn_size = 40
        self.btn_decrease = pygame.Rect(x + 30, y + 70, btn_size, btn_size)
        self.btn_increase = pygame.Rect(x + width - 70, y + 70, btn_size, btn_size)
        self.btn_confirm = pygame.Rect(x + 30, y + 140, width - 60, 40)
        self.btn_cancel = pygame.Rect(x + 30, y + 190, width - 60, 35)

        self.hovered_btn = None

    def show(self, mode, item, player_money, max_from_inventory=None):
        self.mode = mode
        self.item = item
        self.visible = True
        self.quantity = 1

        if mode == "buy":
            item_price = item.get("price", 100)
            self.max_quantity = min(99, player_money // item_price) if player_money >= item_price else 0
        else:
            self.max_quantity = item.quantity
            self.quantity = min(1, self.max_quantity)

        self.update_total()

    def hide(self):
        self.visible = False
        self.item = None

    def update_total(self):
        if not self.item:
            return

        if self.mode == "buy":
            price = self.item.get("price", 100)
            self.total_price = self.quantity * price
        else:
            self.total_price = self.quantity * self.item.sell_price

    def handle_event(self, event):
        if not self.visible:
            return None

        if event.type == pygame.MOUSEMOTION:
            self.hovered_btn = None
            if self.btn_decrease.collidepoint(event.pos):
                self.hovered_btn = "decrease"
            elif self.btn_increase.collidepoint(event.pos):
                self.hovered_btn = "increase"
            elif self.btn_confirm.collidepoint(event.pos):
                self.hovered_btn = "confirm"
            elif self.btn_cancel.collidepoint(event.pos):
                self.hovered_btn = "cancel"
            return None

        elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            if self.btn_decrease.collidepoint(event.pos):
                self.quantity = max(self.min_quantity, self.quantity - 1)
                self.update_total()
                return "update"

            elif self.btn_increase.collidepoint(event.pos):
                self.quantity = min(self.max_quantity, self.quantity + 1)
                self.update_total()
                return "update"

            elif self.btn_confirm.collidepoint(event.pos):
                return "confirm"

            elif self.btn_cancel.collidepoint(event.pos):
                self.hide()
                return "cancel"

        return None

    def render(self, screen, fonts):
        if not self.visible:
            return

        # Overlay escuro que BLOQUEIA cliques no fundo
        overlay = pygame.Surface((screen.get_width(), screen.get_height()))
        overlay.set_alpha(200)
        overlay.fill((0, 0, 0))
        screen.blit(overlay, (0, 0))

        # Janela principal
        pygame.draw.rect(screen, (35, 40, 50), self.rect, border_radius=10)
        pygame.draw.rect(screen, (80, 120, 180), self.rect, 2, border_radius=10)

        # Título
        mode_text = "COMPRAR" if self.mode == "buy" else "VENDER"
        item_name = self.item['name'] if isinstance(self.item, dict) else self.item.name
        title = fonts['medium'].render(f"{mode_text} {item_name}", True, (255, 215, 0))
        title_rect = title.get_rect(center=(self.rect.centerx, self.rect.y + 25))
        screen.blit(title, title_rect)

        # Quantidade
        qty_text = fonts['large'].render(str(self.quantity), True, (255, 255, 255))
        qty_rect = qty_text.get_rect(center=(self.rect.centerx, self.rect.y + 90))
        screen.blit(qty_text, qty_rect)

        # Botões +/-
        for btn, symbol in [(self.btn_decrease, "-"), (self.btn_increase, "+")]:
            hovered = (self.hovered_btn == ("decrease" if symbol == "-" else "increase"))
            can_use = (symbol == "-" and self.quantity > 1) or (symbol == "+" and self.quantity < self.max_quantity)

            if hovered and can_use:
                btn_color = (70, 90, 120)
            elif can_use:
                btn_color = (50, 70, 100)
            else:
                btn_color = (40, 45, 60)

            pygame.draw.rect(screen, btn_color, btn, border_radius=20)
            pygame.draw.rect(screen, (150, 150, 150), btn, 1, border_radius=20)

            btn_text = fonts['large'].render(symbol, True, (255, 255, 255))
            btn_rect = btn_text.get_rect(center=btn.center)
            screen.blit(btn_text, btn_rect)

        # Total
        total_text = fonts['small'].render(f"Total: ${self.total_price}", True, (150, 255, 150))
        total_rect = total_text.get_rect(center=(self.rect.centerx, self.rect.y + 120))
        screen.blit(total_text, total_rect)

        # Botão confirmar
        hovered = (self.hovered_btn == "confirm")
        confirm_color = (70, 140, 70) if hovered and self.quantity > 0 else (50, 100, 50)
        pygame.draw.rect(screen, confirm_color, self.btn_confirm, border_radius=5)
        confirm_text = fonts['small'].render("CONFIRMAR", True, (255, 255, 255))
        confirm_rect = confirm_text.get_rect(center=self.btn_confirm.center)
        screen.blit(confirm_text, confirm_rect)

        # Botão cancelar
        hovered = (self.hovered_btn == "cancel")
        cancel_color = (120, 70, 70) if hovered else (90, 60, 60)
        pygame.draw.rect(screen, cancel_color, self.btn_cancel, border_radius=5)
        cancel_text = fonts['small'].render("Cancelar", True, (255, 200, 200))
        cancel_rect = cancel_text.get_rect(center=self.btn_cancel.center)
        screen.blit(cancel_text, cancel_rect)


class ShopScene(BaseScene):
    def __init__(self, game):
        super().__init__(game)

        self.player = game.player
        self.catalog = item_bag_catalog
        self.progress = progress_manager  # Referência ao progresso
        self.on_close_callback = None
        # Dados da loja
        self.shop_items = []
        self._load_shop_items()

        # Estado
        self.selected_shop_index = 0
        self.selected_inventory_index = 0
        self.sell_multiplier = 0.5

        # Categorias
        self.shop_category = "all"
        self.inventory_category = "all"
        self.filtered_shop_items = []
        self.filtered_inventory_items = []

        # Scroll
        self.shop_scroll_y = 0
        self.shop_scroll_target = 0
        self.inventory_scroll_y = 0
        self.inventory_scroll_target = 0
        self.max_shop_scroll = 0
        self.max_inventory_scroll = 0

        # Elementos UI
        self.shop_cards = []
        self.inventory_cards = []
        self.shop_category_selector = None
        self.inventory_category_selector = None
        self.quantity_selector = None

        # Layout
        self.layout_initialized = False
        self.shop_panel_rect = None
        self.inventory_panel_rect = None

        # Fontes
        self.fonts = self._create_responsive_fonts()

        # Feedback
        self.feedback_message = ""
        self.feedback_timer = 0
        self.feedback_alpha = 0

        # Botões
        self.back_button = None
        self.money_rect = None

        # Offset para descer tudo abaixo do título
        self.category_offset = 30  # Ajuste este valor (20-40 pixels)

        # Já carrega os itens no início
        self.filter_shop()
        self.refresh_inventory()
        self.filter_inventory()

    def _create_responsive_fonts(self):
        """Cria fontes com tamanhos baseados na resolução"""
        base_size = max(16, self.screen_manager.window_height // 45)

        return {
            'title': pygame.font.Font(None, base_size * 2),
            'large': pygame.font.Font(None, base_size),
            'medium': pygame.font.Font(None, base_size - 2),
            'small': pygame.font.Font(None, base_size - 4)
        }

    def _load_shop_items(self):
        """Carrega todos os itens do catálogo"""
        all_items = self.catalog.get_all_items()
        self.shop_items = [item for item in all_items if "price" in item]
        self.shop_items.sort(key=lambda x: (x["category"], x["price"]))

    def _is_item_available(self, item_data):
        """Verifica se um item está disponível para compra baseado no progresso"""
        # Verifica se tem requisito de desbloqueio
        unlock_phase = item_data.get("unlock_phase") or item_data.get("unlock_chapter")

        # Se não tem requisito, sempre disponível
        if unlock_phase is None:
            return True

        # Verifica se a fase foi completada
        return self.progress.is_phase_completed(unlock_phase)

    def refresh_inventory(self):
        self.inventory_cards = []
        items = self.player.bag.get_items_for_render()

        for i, item in enumerate(items):
            card = InventoryItemCard(
                item["id"],
                item["data"],
                item["quantity"],
                i
            )
            self.inventory_cards.append(card)

        for card in self.shop_cards:
            card.update_owned(self.player.bag.items)

    def filter_shop(self):
        """Filtra itens da loja por categoria e disponibilidade"""
        # Primeiro filtra por categoria
        if self.shop_category == "all":
            category_filtered = self.shop_items
        else:
            category_filtered = [
                item for item in self.shop_items
                if item["category"] == self.shop_category
            ]

        # Depois filtra por disponibilidade (baseado no progresso)
        self.filtered_shop_items = [
            item for item in category_filtered
            if self._is_item_available(item)
        ]

        # Atualiza o flag de bloqueio nos cards
        for card in self.shop_cards:
            if hasattr(card, 'is_locked'):
                card.is_locked = not self._is_item_available(card.item_data)

    def filter_inventory(self):
        if self.inventory_category == "all":
            self.filtered_inventory_items = self.inventory_cards
        else:
            self.filtered_inventory_items = [
                card for card in self.inventory_cards
                if card.category == self.inventory_category
            ]

    def _create_layout(self):
        """Cria layout responsivo"""
        vp_x = self.screen_manager.viewport_x
        vp_y = self.screen_manager.viewport_y
        vp_w = self.screen_manager.viewport_width
        vp_h = self.screen_manager.viewport_height

        # Margens
        margin = max(20, vp_w // 40)

        # Botão voltar
        btn_size = max(46, vp_h // 20)
        self.back_button = pygame.Rect(vp_x + margin, vp_y + margin, btn_size, btn_size)

        # Área de dinheiro
        money_width = max(150, vp_w // 8)
        money_height = max(36, vp_h // 20)
        self.money_rect = pygame.Rect(
            vp_x + vp_w - money_width - margin,
            vp_y + margin,
            money_width,
            money_height
        )

        # Painéis lado a lado
        panel_width = (vp_w - margin * 3) // 2
        panel_height = vp_h - margin * 3 - 40
        panel_y = vp_y + margin + 50

        # Painel esquerdo (loja)
        self.shop_panel_rect = pygame.Rect(vp_x + margin, panel_y, panel_width, panel_height)

        # Painel direito (inventário)
        self.inventory_panel_rect = pygame.Rect(
            vp_x + vp_w - panel_width - margin,
            panel_y,
            panel_width,
            panel_height
        )

        # Seletores de categoria
        self.shop_category_selector = CategorySelector(
            self.shop_panel_rect.x + 10,
            self.shop_panel_rect.y + 5,
            self.shop_panel_rect.width - 20
        )

        self.inventory_category_selector = CategorySelector(
            self.inventory_panel_rect.x + 10,
            self.inventory_panel_rect.y + 5,
            self.inventory_panel_rect.width - 20
        )

        # Seletor de quantidade
        selector_width = min(320, vp_w // 3)
        selector_height = min(260, vp_h // 3)
        self.quantity_selector = QuantitySelector(
            vp_x + (vp_w - selector_width) // 2,
            vp_y + (vp_h - selector_height) // 2,
            selector_width,
            selector_height
        )

        # Atualiza fontes
        self.fonts = self._create_responsive_fonts()

        # Cria os cards
        self._create_shop_cards()
        self._create_inventory_cards()

        self.layout_initialized = True

    def _create_shop_cards(self):
        self.shop_cards = []

        card_height = 80
        card_margin = 8
        start_y = self.shop_panel_rect.y + 50 + self.category_offset
        visible_height = self.shop_panel_rect.height - 60 - self.category_offset

        self.max_shop_scroll = max(0, len(self.filtered_shop_items) * (card_height + card_margin) - visible_height)

        for i, item_data in enumerate(self.filtered_shop_items):
            card_y = start_y + i * (card_height + card_margin) - self.shop_scroll_y

            card = ShopItemCard(item_data, i)

            # Verifica se o item está desbloqueado
            card.is_locked = not self._is_item_available(item_data)

            card.update_position(
                self.shop_panel_rect.x + 10,
                card_y,
                self.shop_panel_rect.width - 25,
                card_height
            )
            card.update_owned(self.player.bag.items)
            self.shop_cards.append(card)

    def _create_inventory_cards(self):
        if not hasattr(self, 'inventory_panel_rect') or self.inventory_panel_rect is None:
            return

        card_height = 80
        card_margin = 8
        start_y = self.inventory_panel_rect.y + 50 + self.category_offset
        visible_height = self.inventory_panel_rect.height - 60 - self.category_offset

        self.max_inventory_scroll = max(0, len(self.filtered_inventory_items) * (
                card_height + card_margin) - visible_height)

        for i, card in enumerate(self.filtered_inventory_items):
            card_y = start_y + i * (card_height + card_margin) - self.inventory_scroll_y
            card.update_position(
                self.inventory_panel_rect.x + 10,
                card_y,
                self.inventory_panel_rect.width - 25,
                card_height
            )

    def handle_event(self, event):
        # Se o seletor de quantidade estiver visível, ele recebe todos os eventos primeiro
        if self.quantity_selector and self.quantity_selector.visible:
            result = self.quantity_selector.handle_event(event)
            if result == "confirm":
                self._execute_transaction()
            return

        if event.type == pygame.KEYDOWN:
            if event.key == pygame.K_p:
                self.toggle_pause()
            elif event.key == pygame.K_ESCAPE:
                # Chama callback se existir
                if self.on_close_callback:
                    self.on_close_callback()

                from src.scenes.phase_selector.phase_select_scene import PhaseSelectScene
                self.game.current_scene = PhaseSelectScene(self.game)

        elif event.type == pygame.VIDEORESIZE:
            self.layout_initialized = False

        elif event.type == pygame.MOUSEWHEEL:
            mouse_pos = pygame.mouse.get_pos()

            if self.shop_panel_rect and self.shop_panel_rect.collidepoint(mouse_pos):
                self.shop_scroll_target += event.y * -20
                self.shop_scroll_target = max(0, min(self.max_shop_scroll, self.shop_scroll_target))

            elif self.inventory_panel_rect and self.inventory_panel_rect.collidepoint(mouse_pos):
                self.inventory_scroll_target += event.y * -20
                self.inventory_scroll_target = max(0, min(self.max_inventory_scroll, self.inventory_scroll_target))

        elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            if self.back_button and self.back_button.collidepoint(event.pos):
                if self.on_close_callback:
                    self.on_close_callback()
                from src.scenes.phase_selector.phase_select_scene import PhaseSelectScene
                self.game.current_scene = PhaseSelectScene(self.game)
                return

            if self.shop_category_selector:
                new_category = self.shop_category_selector.handle_event(event)
                if new_category:
                    self.shop_category = new_category
                    self.filter_shop()
                    self._create_shop_cards()
                    self.shop_scroll_target = 0
                    self.selected_shop_index = 0
                    return

            if self.inventory_category_selector:
                new_category = self.inventory_category_selector.handle_event(event)
                if new_category:
                    self.inventory_category = new_category
                    self.filter_inventory()
                    self._create_inventory_cards()
                    self.inventory_scroll_target = 0
                    self.selected_inventory_index = 0
                    return

            if self.shop_panel_rect and self.shop_panel_rect.collidepoint(event.pos):
                for card in self.shop_cards:
                    # Só permite interagir se não estiver bloqueado
                    if not card.is_locked:
                        result = card.handle_event(event)
                        if result:
                            self.selected_shop_index = card.index
                            self._open_quantity_selector_for_card(card)
                            return

            if self.inventory_panel_rect and self.inventory_panel_rect.collidepoint(event.pos):
                for card in self.filtered_inventory_items:
                    result = card.handle_event(event)
                    if result:
                        self.selected_inventory_index = card.index
                        self._open_quantity_selector_for_inventory(card)
                        return

        # Passa eventos para os cards para hover
        for card in self.shop_cards:
            card.handle_event(event)
        for card in self.inventory_cards:
            card.handle_event(event)

    def _open_quantity_selector_for_card(self, card):
        # Verifica novamente se o item está disponível antes de abrir o seletor
        if self._is_item_available(card.item_data):
            self.quantity_selector.show("buy", card.item_data, self.player.money)
        else:
            self.feedback_message = f"Item bloqueado! Complete a fase {card.unlock_phase} primeiro."
            self.feedback_timer = 2.0

    def _open_quantity_selector_for_inventory(self, card):
        self.quantity_selector.show("sell", card, self.player.money)

    def _execute_transaction(self):
        selector = self.quantity_selector
        if not selector or not selector.item:
            return

        quantity = selector.quantity
        total = selector.total_price

        if selector.mode == "buy":
            item_data = selector.item
            item_id = item_data["id"]
            item_name = item_data["name"]

            # Verifica novamente se o item está disponível antes de comprar
            if not self._is_item_available(item_data):
                self.feedback_message = f"Item bloqueado! Complete a fase necessária primeiro."
                self.feedback_timer = 2.0
                selector.hide()
                return

            if self.player.money >= total:
                self.player.money -= total
                self.player.bag.add_item(item_id, quantity)
                self.feedback_message = f"Comprou {quantity}x {item_name}"
                self.feedback_timer = 2.0
            else:
                self.feedback_message = "Dinheiro insuficiente!"
                self.feedback_timer = 1.5
                selector.hide()
                return

        else:  # modo "sell"
            item_card = selector.item
            item_id = item_card.item_id
            item_name = item_card.name

            # Verifica se tem quantidade suficiente
            current_qty = self.player.bag.get_quantity(item_id)
            if current_qty >= quantity:
                self.player.money += total
                self.player.bag.remove_item(item_id, quantity)
                self.feedback_message = f"Vendeu {quantity}x {item_name}"
                self.feedback_timer = 2.0
            else:
                self.feedback_message = f"Você só tem {current_qty}x {item_name}!"
                self.feedback_timer = 1.5
                selector.hide()
                return

        # ========== FORÇA ATUALIZAÇÃO COMPLETA DA UI ==========
        # 1. Atualiza os cards do inventário com os dados mais recentes
        self.refresh_inventory()

        # 2. Reaplica os filtros no inventário
        self.filter_inventory()

        # 3. Recria os cards visuais do inventário
        self._create_inventory_cards()

        # 4. Atualiza a quantidade nos cards da loja
        for card in self.shop_cards:
            card.update_owned(self.player.bag.items)

        # 5. Recria os cards da loja
        self._create_shop_cards()

        # 6. Atualiza os filtros da loja (caso necessário)
        self.filter_shop()

        # 7. Ajusta o scroll para valores válidos
        self.inventory_scroll_target = min(self.inventory_scroll_target, self.max_inventory_scroll)
        self.shop_scroll_target = min(self.shop_scroll_target, self.max_shop_scroll)

        # 8. Garante que a seleção ainda é válida
        if self.selected_inventory_index >= len(self.filtered_inventory_items):
            self.selected_inventory_index = max(0, len(self.filtered_inventory_items) - 1)
        if self.selected_shop_index >= len(self.filtered_shop_items):
            self.selected_shop_index = max(0, len(self.filtered_shop_items) - 1)
        # ===================================================

        self.game.player.auto_save()

        selector.hide()

    def fixed_update(self, dt):
        if not self.layout_initialized:
            self._create_layout()
            return

        # Atualiza animações
        for card in self.shop_cards + self.inventory_cards:
            if hasattr(card, 'update_animation'):
                card.update_animation(dt)

        # Scroll suave
        if abs(self.shop_scroll_y - self.shop_scroll_target) > 0.1:
            self.shop_scroll_y += (self.shop_scroll_target - self.shop_scroll_y) * min(1, dt * 10)
            self._create_shop_cards()

        if abs(self.inventory_scroll_y - self.inventory_scroll_target) > 0.1:
            self.inventory_scroll_y += (self.inventory_scroll_target - self.inventory_scroll_y) * min(1, dt * 10)
            self._create_inventory_cards()

        # Feedback
        if self.feedback_timer > 0:
            self.feedback_timer -= dt
            self.feedback_alpha = min(255, int(255 * self.feedback_timer))
        else:
            self.feedback_alpha = 0

    def render(self, screen):
        self._draw_gradient_background(screen)

        if not self.layout_initialized:
            self._create_layout()

        # Título
        title = self.fonts['title'].render("LOJA", True, (255, 215, 0))
        title_x = self.screen_manager.viewport_x + (self.screen_manager.viewport_width - title.get_width()) // 2
        screen.blit(title, (title_x, self.screen_manager.viewport_y + 25))

        # Botão voltar
        if self.back_button:
            pygame.draw.rect(screen, (40, 40, 45), self.back_button, border_radius=6)
            pygame.draw.rect(screen, (80, 80, 90), self.back_button, 1, border_radius=6)
            back_text = self.fonts['large'].render("Voltar", True, (200, 200, 210))
            back_rect = back_text.get_rect(center=self.back_button.center)
            screen.blit(back_text, back_rect)

        # Dinheiro
        self._render_money(screen)

        # Painéis
        self._render_panels(screen)

        # Seletor de quantidade (renderiza por cima de tudo)
        if self.quantity_selector and self.quantity_selector.visible:
            self.quantity_selector.render(screen, self.fonts)

        # Feedback
        if self.feedback_alpha > 0:
            self._render_feedback(screen)

        if self.paused:
            self._render_pause_overlay(screen)

    def _render_money(self, screen):
        pygame.draw.rect(screen, (30, 35, 45), self.money_rect, border_radius=6)
        pygame.draw.rect(screen, (80, 120, 180), self.money_rect, 1, border_radius=6)

        coin = self.fonts['title'].render("$", True, (255, 215, 0))
        screen.blit(coin, (self.money_rect.x + 10, self.money_rect.y + 10))

        money_text = self.fonts['title'].render(str(self.player.money), True, (150, 255, 150))
        screen.blit(money_text, (self.money_rect.x + 30, self.money_rect.y + 10))

    def _render_panels(self, screen):
        # Painel da loja
        self._render_panel(
            screen,
            self.shop_panel_rect,
            "COMPRAR",
            self.shop_category_selector,
            self.shop_cards,
            (80, 140, 220)
        )

        # Painel do inventário
        self._render_panel(
            screen,
            self.inventory_panel_rect,
            "VENDER",
            self.inventory_category_selector,
            self.filtered_inventory_items,
            (220, 140, 80)
        )

    def _render_panel(self, screen, rect, title, category_selector, cards, color):
        # Fundo
        pygame.draw.rect(screen, (25, 28, 32, 240), rect, border_radius=8)
        pygame.draw.rect(screen, color, rect, 1, border_radius=8)

        # Título do painel
        title_text = self.fonts['large'].render(title, True, color)
        screen.blit(title_text, (category_selector.rect.x + (category_selector.rect.width / 2 - 16), rect.y + 12))

        # Categorias
        if category_selector:
            # Move o seletor inteiro para baixo
            category_selector.rect.y = rect.y + 8 + self.category_offset

            # Atualiza a posição de cada botão dentro do seletor
            for btn in category_selector.buttons:
                btn["rect"].y = category_selector.rect.y + 5

            category_selector.render(screen, self.fonts)

        # Área de clipping (cards começam depois das categorias)
        old_clip = screen.get_clip()
        clip_rect = pygame.Rect(
            rect.x,
            rect.y + 40 + self.category_offset,
            rect.width,
            rect.height - 50 - self.category_offset
        )
        screen.set_clip(clip_rect)

        # Cards
        for i, card in enumerate(cards):
            if hasattr(card, 'rect') and card.rect.bottom > clip_rect.top and card.rect.top < clip_rect.bottom:
                selected = False
                if isinstance(card, ShopItemCard):
                    selected = (i == self.selected_shop_index and card in self.shop_cards)
                else:
                    selected = (i == self.selected_inventory_index and card in self.filtered_inventory_items)

                card.render(screen, self.fonts, selected)

        screen.set_clip(old_clip)

        # Barra de scroll
        max_scroll = self.max_shop_scroll if title == "COMPRAR" else self.max_inventory_scroll
        scroll_y = self.shop_scroll_y if title == "COMPRAR" else self.inventory_scroll_y

        if max_scroll > 0:
            self._render_scroll_bar(screen, rect, scroll_y, max_scroll, color)

    def _render_scroll_bar(self, screen, panel_rect, scroll_y, max_scroll, color):
        bar_x = panel_rect.right - 8
        bar_y = panel_rect.y + 45 + self.category_offset
        bar_height = panel_rect.height - 50 - self.category_offset

        if max_scroll <= 0:
            return

        scroll_height = max(30, bar_height * (bar_height / (bar_height + max_scroll)))
        scroll_pos = bar_y + (scroll_y / max_scroll) * (bar_height - scroll_height)

        # Fundo
        pygame.draw.rect(screen, (40, 40, 45), (bar_x, bar_y, 3, bar_height))

        # Barra
        scroll_rect = pygame.Rect(bar_x, scroll_pos, 3, scroll_height)
        pygame.draw.rect(screen, color, scroll_rect)

    def _render_feedback(self, screen):
        text = self.fonts['small'].render(self.feedback_message, True, (255, 255, 255))
        text.set_alpha(self.feedback_alpha)

        bg = pygame.Surface((text.get_width() + 30, text.get_height() + 12))
        bg.set_alpha(min(180, self.feedback_alpha))
        bg.fill((30, 30, 35))

        x = self.screen_manager.viewport_x + (self.screen_manager.viewport_width - bg.get_width()) // 2
        y = self.screen_manager.viewport_y + self.screen_manager.viewport_height - 60

        screen.blit(bg, (x, y))
        screen.blit(text, (x + 15, y + 6))

    def _draw_gradient_background(self, screen):
        for i in range(self.screen_manager.window_height):
            value = int(15 + (i / self.screen_manager.window_height) * 20)
            color = (value, value, value + 5)
            pygame.draw.line(screen, color, (0, i), (self.screen_manager.window_width, i))

    def _render_pause_overlay(self, screen):
        overlay = pygame.Surface((self.screen_manager.window_width, self.screen_manager.window_height))
        overlay.set_alpha(180)
        overlay.fill((10, 10, 10))
        screen.blit(overlay, (0, 0))

        pause_text = self.fonts['title'].render("PAUSADO", True, (200, 200, 200))
        text_x = (self.screen_manager.window_width - pause_text.get_width()) // 2
        text_y = (self.screen_manager.window_height - pause_text.get_height()) // 2
        screen.blit(pause_text, (text_x, text_y))