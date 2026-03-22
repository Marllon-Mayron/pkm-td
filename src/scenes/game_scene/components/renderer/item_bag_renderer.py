# src/scenes/game_scene/components/ui/item_bag_renderer.py

import pygame
import math
from src.data.item_bag_catalog import item_bag_catalog

# Cache global para fontes
_FONT_CACHE = {}
# Cache para sprites escalados
_SPRITE_CACHE = {}


class ItemBagRenderer:
    """Renderiza a mochila no canto inferior esquerdo - OTIMIZADO"""

    def __init__(self, game, bag_manager):
        self.game = game
        self.bag = bag_manager
        self.catalog = item_bag_catalog

        # Posicionamento inicial
        self.x = game.screen_manager.window_width - 280
        self.y = game.screen_manager.window_height - 540
        self.width = 250
        self.height = 400

        # ARRASTO DA UI
        self.dragging = False
        self.drag_offset_x = 0
        self.drag_offset_y = 0
        self.drag_start_mouse = (0, 0)

        # Animação
        self.animation_time = 0
        self.hovered_index = -1
        self.pulse_alpha = 0

        # Foco do scroll
        self.mouse_over_ui = False

        # Paginação das categorias
        self.all_categories = [
            ("all", "Todos", (150, 150, 150)),
            ("pokeball", "Pokébolas", (255, 100, 100)),
            ("medicine", "Poções", (100, 255, 100)),
            ("items", "Itens", (255, 215, 0))
        ]
        self.categories_per_page = 3
        self.current_page = 0
        self.total_pages = (len(self.all_categories) + self.categories_per_page - 1) // self.categories_per_page

        # Caches de renderização
        self._cached_background = None
        self._cached_background_size = None
        self._cached_fonts = {}
        self._cached_ui_elements = {}

        # Sincroniza a página inicial
        self._sync_page_with_category()

    def _get_font(self, size, bold=False):
        """Obtém fonte do cache"""
        key = (size, bold)
        if key not in _FONT_CACHE:
            font = pygame.font.Font(None, size)
            if bold:
                font.set_bold(True)
            _FONT_CACHE[key] = font
        return _FONT_CACHE[key]

    def _get_scaled_sprite(self, item_id, size=(32, 32)):
        """Obtém sprite escalado do cache"""
        cache_key = (item_id, size)
        if cache_key not in _SPRITE_CACHE:
            sprite = self.catalog.get_sprite(item_id, scaled=True)
            if sprite:
                _SPRITE_CACHE[cache_key] = pygame.transform.scale(sprite, size)
            else:
                _SPRITE_CACHE[cache_key] = None
        return _SPRITE_CACHE[cache_key]

    def _sync_page_with_category(self):
        """Sincroniza a página atual com a categoria selecionada"""
        current_category = self.bag.selected_category

        for page in range(self.total_pages):
            start_idx = page * self.categories_per_page
            end_idx = min(start_idx + self.categories_per_page, len(self.all_categories))
            page_categories = self.all_categories[start_idx:end_idx]

            for cat_id, _, _ in page_categories:
                if cat_id == current_category:
                    if self.current_page != page:
                        self.current_page = page
                    return

    def update(self, dt):
        """Atualiza animações"""
        self.animation_time += dt
        self.pulse_alpha = 100 + int(55 * math.sin(self.animation_time * 5))

        # Invalida cache de UI quando tamanho da janela muda
        if (self.game.screen_manager.window_width != self._cached_background_size or
                self.game.screen_manager.window_height != self._cached_background_size):
            self._cached_background = None

    def update_hover(self, mouse_pos):
        """Atualiza o índice do item sob o mouse"""
        mouse_x, mouse_y = mouse_pos
        self.mouse_over_ui = self._is_mouse_in_area(mouse_x, mouse_y)

        if self.mouse_over_ui:
            index = self._get_item_index_at(mouse_x, mouse_y)
            if index >= 0:
                self.hovered_index = index
            else:
                self.hovered_index = self.bag.selected_item_index
        else:
            self.hovered_index = -1

    def handle_event(self, event):
        """Processa eventos na UI de itens"""
        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            mouse_x, mouse_y = event.pos

            if self._is_mouse_in_title_area(mouse_x, mouse_y):
                self.dragging = True
                self.drag_offset_x = self.x - mouse_x
                self.drag_offset_y = self.y - mouse_y
                self.drag_start_mouse = (mouse_x, mouse_y)
                pygame.mouse.set_cursor(pygame.SYSTEM_CURSOR_SIZEALL)
                return True

            elif self._is_mouse_in_area(mouse_x, mouse_y):
                index = self._get_item_index_at(mouse_x, mouse_y)
                if index >= 0:
                    self.clicked_item_index = index

            elif self._is_mouse_in_nav_arrows(mouse_x, mouse_y):
                arrow = self._get_clicked_arrow(mouse_x, mouse_y)
                if arrow == "left":
                    self._prev_category_page()
                    return True
                elif arrow == "right":
                    self._next_category_page()
                    return True

            else:
                clicked_category = self._get_clicked_category(mouse_x, mouse_y)
                if clicked_category:
                    self.bag.set_category(clicked_category)
                    self._sync_page_with_category()
                    return True

        elif event.type == pygame.MOUSEMOTION:
            if self.dragging:
                self.x = event.pos[0] + self.drag_offset_x
                self.y = event.pos[1] + self.drag_offset_y
                self.x = max(5, min(self.game.screen_manager.window_width - self.width - 5, self.x))
                self.y = max(5, min(self.game.screen_manager.window_height - self.height - 5, self.y))
                self._cached_background = None  # Invalida cache
                return True

            self.update_hover(event.pos)

        elif event.type == pygame.MOUSEBUTTONUP:
            if event.button == 1 and self.dragging:
                self.dragging = False
                pygame.mouse.set_cursor(pygame.SYSTEM_CURSOR_ARROW)
                return True

        if event.type == pygame.MOUSEWHEEL:
            if self.mouse_over_ui:
                if event.y > 0:
                    self.bag.prev_item()
                else:
                    self.bag.next_item()
                self.hovered_index = self.bag.selected_item_index
                return True

        return False

    def _prev_category_page(self):
        if self.current_page > 0:
            self.current_page -= 1

    def _next_category_page(self):
        if self.current_page < self.total_pages - 1:
            self.current_page += 1

    def _get_current_page_categories(self):
        start_idx = self.current_page * self.categories_per_page
        end_idx = min(start_idx + self.categories_per_page, len(self.all_categories))
        return self.all_categories[start_idx:end_idx]

    def _is_mouse_in_nav_arrows(self, mouse_x, mouse_y):
        nav_y = self.y + 48
        nav_height = 25
        categories_width = self._get_categories_width()
        arrows_x = self.x + 15 + categories_width + 5
        arrows_width = 40
        return (arrows_x <= mouse_x <= arrows_x + arrows_width and
                nav_y <= mouse_y <= nav_y + nav_height)

    def _get_clicked_arrow(self, mouse_x, mouse_y):
        categories_width = self._get_categories_width()
        arrows_x = self.x + 15 + categories_width + 5
        if arrows_x <= mouse_x <= arrows_x + 15:
            return "left"
        elif arrows_x + 25 <= mouse_x <= arrows_x + 40:
            return "right"
        return None

    def _get_clicked_category(self, mouse_x, mouse_y):
        if not (self.y + 45 <= mouse_y <= self.y + 70):
            return None

        start_x = self.x + 15
        current_categories = self._get_current_page_categories()

        for cat_id, cat_name, color in current_categories:
            cat_width = max(65, len(cat_name) * 8 + 10)
            if start_x <= mouse_x <= start_x + cat_width:
                return cat_id
            start_x += cat_width + 5
        return None

    def _get_categories_width(self):
        categories = self._get_current_page_categories()
        total_width = 0
        for cat_id, cat_name, color in categories:
            cat_width = max(65, len(cat_name) * 8 + 10)
            total_width += cat_width + 5
        return total_width - 5

    def _is_mouse_in_area(self, mouse_x, mouse_y):
        return (self.x <= mouse_x <= self.x + self.width and
                self.y <= mouse_y <= self.y + self.height)

    def _is_mouse_in_title_area(self, mouse_x, mouse_y):
        return (self.x <= mouse_x <= self.x + self.width and
                self.y <= mouse_y <= self.y + 40)

    def _get_item_index_at(self, mouse_x, mouse_y):
        start_y = self.y + 70
        relative_y = mouse_y - start_y
        if relative_y < 0:
            return -1
        index = relative_y // 60
        items = self.bag.get_items_for_render()
        if 0 <= index < len(items):
            return index
        return -1

    def render(self, screen):
        """Renderiza a UI da mochila - OTIMIZADO"""
        self._sync_page_with_category()
        self._draw_background(screen)
        self._draw_title(screen)
        self._draw_categories(screen)
        self._draw_items(screen)
        self._draw_instructions(screen)

        if self.dragging:
            self._draw_drag_indicator(screen)

    def _draw_background(self, screen):
        """Desenha fundo com efeito glass - OTIMIZADO"""
        # Usa cache se disponível
        if self._cached_background is not None:
            screen.blit(self._cached_background, (self.x, self.y))
            return

        bg = pygame.Surface((self.width, self.height), pygame.SRCALPHA)

        # Gradiente vertical
        for i in range(self.height):
            progress = i / self.height
            alpha = int(180 + 75 * (1 - progress))
            color = (15, 20, 30, alpha)
            bg.fill(color, (0, i, self.width, 1))

        # Borda
        border_color = (120, 160, 240, 200) if self.mouse_over_ui else (80, 120, 200, 150)
        border_width = 3 if self.mouse_over_ui else 2
        pygame.draw.rect(bg, border_color, bg.get_rect(), border_width, border_radius=10)

        # Brilho na borda superior
        glow = pygame.Surface((self.width, 4), pygame.SRCALPHA)
        for x in range(self.width):
            dist = abs(x - self.width // 2) / (self.width // 2)
            alpha = int(100 * (1 - dist))
            glow.set_at((x, 0), (100, 150, 255, alpha))
        bg.blit(glow, (0, 0))

        self._cached_background = bg
        screen.blit(bg, (self.x, self.y))

    def _draw_title(self, screen):
        """Desenha título da seção"""
        title_font = self._get_font(24)

        if self.mouse_over_ui and self.y <= pygame.mouse.get_pos()[1] <= self.y + 40:
            title_bg = pygame.Surface((self.width, 40), pygame.SRCALPHA)
            title_bg.fill((80, 100, 150, 40))
            screen.blit(title_bg, (self.x, self.y))

        title = title_font.render("MOCHILA", True, (255, 215, 0))
        screen.blit(title, (self.x + 15, self.y + 10))

        for i in range(4):
            dot_x = self.x + self.width - 25 + (i * 5)
            dot_y = self.y + 15
            pygame.draw.circle(screen, (150, 150, 150), (dot_x, dot_y), 2)

        pygame.draw.line(screen, (80, 100, 150),
                         (self.x + 15, self.y + 35),
                         (self.x + self.width - 15, self.y + 35), 1)

    def _draw_categories(self, screen):
        """Desenha seletor de categorias"""
        current_categories = self._get_current_page_categories()
        start_x = self.x + 15
        category_font = self._get_font(16)

        for cat_id, cat_name, color in current_categories:
            cat_width = max(65, len(cat_name) * 8 + 10)
            cat_height = 25

            if self.bag.selected_category == cat_id:
                bg_color = (*color, 80)
                border_color = color
                text_color = (255, 255, 255)
            else:
                bg_color = (30, 35, 45, 100)
                border_color = (60, 70, 90)
                text_color = (180, 180, 200)

            cat_bg = pygame.Surface((cat_width, cat_height), pygame.SRCALPHA)
            cat_bg.fill(bg_color)
            screen.blit(cat_bg, (start_x, self.y + 45))
            pygame.draw.rect(screen, border_color,
                             (start_x, self.y + 45, cat_width, cat_height), 1, border_radius=5)

            text = category_font.render(cat_name, True, text_color)
            text_x = start_x + (cat_width - text.get_width()) // 2
            screen.blit(text, (text_x, self.y + 48))
            start_x += cat_width + 5

        if self.total_pages > 1:
            self._draw_category_navigation(screen)

    def _draw_category_navigation(self, screen):
        """Desenha setas de navegação"""
        categories_width = self._get_categories_width()
        arrows_x = self.x + 15 + categories_width + 5
        nav_y = self.y + 48
        nav_height = 25
        category_font = self._get_font(16)

        left_arrow_color = (150, 150, 150) if self.current_page > 0 else (80, 80, 80)
        left_points = [(arrows_x + 5, nav_y + nav_height // 2),
                       (arrows_x + 12, nav_y + nav_height - 5),
                       (arrows_x + 12, nav_y + 5)]
        pygame.draw.polygon(screen, left_arrow_color, left_points)

        right_arrow_color = (150, 150, 150) if self.current_page < self.total_pages - 1 else (80, 80, 80)
        right_points = [(arrows_x + 35, nav_y + nav_height // 2),
                        (arrows_x + 28, nav_y + nav_height - 5),
                        (arrows_x + 28, nav_y + 5)]
        pygame.draw.polygon(screen, right_arrow_color, right_points)

        page_text = category_font.render(f"{self.current_page + 1}/{self.total_pages}",
                                         True, (180, 180, 200))
        page_x = arrows_x + 15
        page_y = nav_y + (nav_height - page_text.get_height()) // 2
        screen.blit(page_text, (page_x, page_y))

    def _draw_items(self, screen):
        """Desenha a lista de itens - OTIMIZADO"""
        items = self.bag.get_items_for_render()
        item_font = self._get_font(20)
        qty_font = self._get_font(18)

        if not items:
            empty_text = item_font.render("Nenhum item", True, (150, 150, 150))
            text_x = self.x + (self.width - empty_text.get_width()) // 2
            screen.blit(empty_text, (text_x, self.y + 120))
            return

        start_y = self.y + 80
        item_height = 60

        for i, item in enumerate(items):
            item_y = start_y + i * item_height
            if item_y + item_height > self.y + self.height - 10:
                continue

            # Fundo do item
            if i == self.bag.selected_item_index:
                bg = pygame.Surface((self.width - 10, item_height - 5), pygame.SRCALPHA)
                bg.fill((80, 120, 200, 60))
                screen.blit(bg, (self.x + 5, item_y))

                border_color = (100, 200, 255, 200)
                pygame.draw.rect(screen, border_color,
                                 (self.x + 5, item_y, self.width - 10, item_height - 5), 2, border_radius=8)
                pulse_rect = pygame.Rect(self.x + 5, item_y, self.width - 10, item_height - 5)
                self._draw_pulse_effect(screen, pulse_rect)

            elif i == self.hovered_index:
                bg = pygame.Surface((self.width - 10, item_height - 5), pygame.SRCALPHA)
                bg.fill((60, 80, 120, 30))
                screen.blit(bg, (self.x + 5, item_y))

            # Sprite (usando cache)
            sprite = self._get_scaled_sprite(item["id"], (32, 32))
            if sprite:
                screen.blit(sprite, (self.x + 15, item_y + 5))

            # Nome
            name_text = item_font.render(item["data"]["name"], True, (255, 255, 255))
            screen.blit(name_text, (self.x + 70, item_y + 10))

            # Quantidade
            qty_text = qty_font.render(f"{item['quantity']}", True, (255, 255, 0))
            qty_bg_width = max(30, qty_text.get_width() + 10)
            qty_bg = pygame.Surface((qty_bg_width, qty_text.get_height() + 6), pygame.SRCALPHA)
            qty_bg.fill((40, 40, 60, 220))
            pygame.draw.rect(qty_bg, (100, 100, 150, 100), qty_bg.get_rect(), 1, border_radius=10)
            screen.blit(qty_bg, (self.x + self.width - qty_bg_width - 15, item_y + 8))
            screen.blit(qty_text, (self.x + self.width - qty_bg_width - 8, item_y + 12))

            # Descrição
            desc = item["data"]["description"]
            if len(desc) > 25:
                desc = desc[:25] + "..."
            desc_text = qty_font.render(desc, True, (150, 150, 170))
            screen.blit(desc_text, (self.x + 70, item_y + 30))

    def _draw_pulse_effect(self, screen, rect):
        pulse = 0.5 + 0.5 * math.sin(self.animation_time * 3)
        alpha = int(50 + 30 * pulse)
        pulse_surf = pygame.Surface((rect.width, rect.height), pygame.SRCALPHA)
        pygame.draw.rect(pulse_surf, (255, 255, 255, alpha), pulse_surf.get_rect(), 1, border_radius=8)
        screen.blit(pulse_surf, rect)

    def _draw_instructions(self, screen):
        """Desenha instruções de uso"""
        inst_y = self.y + self.height - 55
        qty_font = self._get_font(18)

        inst_bg = pygame.Surface((self.width - 20, 40), pygame.SRCALPHA)
        inst_bg.fill((20, 25, 35, 200))
        screen.blit(inst_bg, (self.x + 10, inst_y))

        instructions = [("Scroll", "Alternar"), ("TAB", "Categoria")]
        x = self.x + 20

        for key, action in instructions:
            key_text = qty_font.render(key, True, (255, 215, 0))
            screen.blit(key_text, (x, inst_y + 8))
            action_text = qty_font.render(action, True, (180, 180, 200))
            screen.blit(action_text, (x + 5 + key_text.get_width(), inst_y + 8))
            x += 85

    def _draw_drag_indicator(self, screen):
        shadow = pygame.Surface((self.width, self.height), pygame.SRCALPHA)
        shadow.fill((255, 255, 255, 30))
        screen.blit(shadow, (self.x + 5, self.y + 5))
        font = self._get_font(20)
        text = font.render("Arraste para posicionar", True, (255, 255, 255))
        text_x = self.x + (self.width - text.get_width()) // 2
        text_y = self.y + self.height // 2
        screen.blit(text, (text_x, text_y))