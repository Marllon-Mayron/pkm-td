# src/scenes/game_scene/components/ui/item_bag_renderer.py

import pygame
import math
from src.data.item_bag_catalog import item_bag_catalog

# Cache global para fontes
_FONT_CACHE = {}
# Cache para sprites escalados
_SPRITE_CACHE = {}


class ItemBagRenderer:
    """Renderiza a mochila com scroll, minimizar e redimensionamento"""

    def __init__(self, game, bag_manager):
        self.game = game
        self.bag = bag_manager
        self.catalog = item_bag_catalog

        # Posicionamento inicial
        self.x = game.screen_manager.window_width - 280
        self.y = game.screen_manager.window_height - 540
        self.full_height = 400
        self.minimized_height = 40
        self.height = self.full_height
        self.width = 250

        # Tamanhos mínimos (respeitam abas e lista)
        self.min_width = 200
        self.min_height = 180

        # ARRASTO DA UI (janela)
        self.dragging = False
        self.drag_offset_x = 0
        self.drag_offset_y = 0
        self.drag_start_mouse = (0, 0)

        # REDIMENSIONAMENTO
        self.resizing = False
        self.resize_start_mouse = (0, 0)
        self.resize_start_size = (self.width, self.height)
        self.resize_handle_size = 16

        # SCROLL VERTICAL
        self.scroll_offset = 0
        self._last_category = self.bag.selected_category

        # MINIMIZAR
        self.minimized = False

        # Animação
        self.animation_time = 0
        self.hovered_index = -1
        self.pulse_alpha = 0

        # Foco do mouse
        self.mouse_over_ui = False

        # Paginação das categorias
        self.all_categories = [
            ("all", "Todos", (150, 150, 150)),
            ("pokeball", "Pokébolas", (255, 100, 100)),
            ("medicine", "Poções", (100, 255, 100)),
            ("battle_item", "Batalha", (255, 200, 100)),
            ("tm", "TMs/HMs", (100, 150, 255)),
            ("items", "Itens", (255, 215, 0))
        ]
        self.categories_per_page = 3
        self.current_page = 0
        self.total_pages = (len(self.all_categories) + self.categories_per_page - 1) // self.categories_per_page

        # Caches de renderização
        self._cached_background = None
        self._cached_background_size = None

        self._sync_page_with_category()

    # ---------- FONTES E SPRITES ----------
    def _get_font(self, size, bold=False):
        key = (size, bold)
        if key not in _FONT_CACHE:
            font = pygame.font.Font(None, size)
            if bold:
                font.set_bold(True)
            _FONT_CACHE[key] = font
        return _FONT_CACHE[key]

    def _get_scaled_sprite(self, item_id, size=(32, 32)):
        cache_key = (item_id, size)
        if cache_key not in _SPRITE_CACHE:
            sprite = self.catalog.get_sprite(item_id, scaled=True)
            if sprite:
                _SPRITE_CACHE[cache_key] = pygame.transform.scale(sprite, size)
            else:
                _SPRITE_CACHE[cache_key] = None
        return _SPRITE_CACHE[cache_key]

    # ---------- SINCRONIZAÇÃO DE CATEGORIA ----------
    def _sync_page_with_category(self):
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

    # ---------- UPDATE ----------
    def update(self, dt):
        self.animation_time += dt
        self.pulse_alpha = 100 + int(55 * math.sin(self.animation_time * 5))

        if self.bag.selected_category != self._last_category:
            self._last_category = self.bag.selected_category
            self.scroll_offset = 0
            self._cached_background = None

        if (self.game.screen_manager.window_width != self._cached_background_size or
                self.game.screen_manager.window_height != self._cached_background_size):
            self._cached_background = None

    def update_hover(self, mouse_pos):
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

    # ---------- EVENTOS ----------
    def handle_event(self, event):
        """Processa eventos da UI (sem lógica de arraste de item)"""
        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            mouse_x, mouse_y = event.pos

            # Botão minimizar (prioridade)
            if self._is_mouse_in_minimize_button(mouse_x, mouse_y):
                self._toggle_minimize()
                return True

            # Handle de redimensionamento (canto inferior direito)
            if self._is_mouse_in_resize_handle(mouse_x, mouse_y):
                self.resizing = True
                self.resize_start_mouse = (mouse_x, mouse_y)
                self.resize_start_size = (self.width, self.height)
                pygame.mouse.set_cursor(pygame.SYSTEM_CURSOR_SIZENWSE)
                return True

            # Arrastar janela pelo título
            if self._is_mouse_in_title_area(mouse_x, mouse_y):
                self.dragging = True
                self.drag_offset_x = self.x - mouse_x
                self.drag_offset_y = self.y - mouse_y
                self.drag_start_mouse = (mouse_x, mouse_y)
                pygame.mouse.set_cursor(pygame.SYSTEM_CURSOR_SIZEALL)
                return True

            # Se minimizado, não processa mais cliques no conteúdo
            if self.minimized:
                return False

            # Navegação de categorias (setas)
            if self._is_mouse_in_nav_arrows(mouse_x, mouse_y):
                arrow = self._get_clicked_arrow(mouse_x, mouse_y)
                if arrow == "left":
                    self._prev_category_page()
                    return True
                elif arrow == "right":
                    self._next_category_page()
                    return True

            # Clique em categoria
            clicked_category = self._get_clicked_category(mouse_x, mouse_y)
            if clicked_category:
                self.bag.set_category(clicked_category)
                self._sync_page_with_category()
                self.scroll_offset = 0
                return True

            # Clique em item: apenas seleciona e deixa o game_scene iniciar o arraste
            if self._is_mouse_in_area(mouse_x, mouse_y):
                index = self._get_item_index_at(mouse_x, mouse_y)
                if index >= 0:
                    self.bag.selected_item_index = index
                    self.hovered_index = index

        elif event.type == pygame.MOUSEMOTION:
            if self.dragging:
                self.x = event.pos[0] + self.drag_offset_x
                self.y = event.pos[1] + self.drag_offset_y
                self._clamp_position()
                self._cached_background = None
                return True

            if self.resizing:
                dx = event.pos[0] - self.resize_start_mouse[0]
                dy = event.pos[1] - self.resize_start_mouse[1]
                new_width = max(self.min_width, self.resize_start_size[0] + dx)
                new_height = max(self.min_height, self.resize_start_size[1] + dy)

                # Ajusta para não ultrapassar a tela
                max_width = self.game.screen_manager.window_width - self.x - 5
                max_height = self.game.screen_manager.window_height - self.y - 5
                self.width = min(new_width, max_width)
                self.height = min(new_height, max_height)

                if self.minimized:
                    self.height = self.minimized_height
                else:
                    if self.height < self.min_height:
                        self.height = self.min_height

                self._cached_background = None
                return True

            self.update_hover(event.pos)

        elif event.type == pygame.MOUSEBUTTONUP:
            if event.button == 1:
                if self.dragging:
                    self.dragging = False
                    pygame.mouse.set_cursor(pygame.SYSTEM_CURSOR_ARROW)
                    return True
                if self.resizing:
                    self.resizing = False
                    pygame.mouse.set_cursor(pygame.SYSTEM_CURSOR_ARROW)
                    return True

        # Roda do mouse: SCROLL vertical (apenas se não minimizado)
        if event.type == pygame.MOUSEWHEEL and not self.minimized:
            if self.mouse_over_ui:
                self._scroll_items(event.y)
                return True

        return False

    def _clamp_position(self):
        screen_width = self.game.screen_manager.window_width
        screen_height = self.game.screen_manager.window_height
        self.x = max(5, min(screen_width - self.width - 5, self.x))
        self.y = max(5, min(screen_height - self.height - 5, self.y))

    # ---------- SCROLL ----------
    def _get_max_visible_items(self):
        available_height = self.height - 90
        return max(0, available_height // 60)

    def _get_max_scroll(self):
        items = self.bag.get_items_for_render()
        max_visible = self._get_max_visible_items()
        return max(0, len(items) - max_visible)

    def _scroll_items(self, direction):
        max_scroll = self._get_max_scroll()
        self.scroll_offset = max(0, min(self.scroll_offset - direction, max_scroll))

    # ---------- MINIMIZAR ----------
    def _toggle_minimize(self):
        self.minimized = not self.minimized
        if self.minimized:
            self.height = self.minimized_height
        else:
            self.height = max(self.min_height, self.full_height)
        self._cached_background = None
        self._clamp_position()

    def _is_mouse_in_minimize_button(self, mouse_x, mouse_y):
        btn_x = self.x + self.width - 30
        btn_y = self.y + 8
        btn_size = 22
        return (btn_x <= mouse_x <= btn_x + btn_size and
                btn_y <= mouse_y <= btn_y + btn_size)

    # ---------- REDIMENSIONAMENTO ----------
    def _is_mouse_in_resize_handle(self, mouse_x, mouse_y):
        if self.minimized:
            return False
        handle_x = self.x + self.width - self.resize_handle_size
        handle_y = self.y + self.height - self.resize_handle_size
        return (handle_x <= mouse_x <= self.x + self.width and
                handle_y <= mouse_y <= self.y + self.height)

    # ---------- NAVEGAÇÃO DE CATEGORIAS ----------
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
        if self.minimized:
            return False
        nav_y = self.y + 48
        nav_height = 25
        # O espaço das setas e página fica à direita das categorias
        # Precisamos saber onde terminam as categorias
        cat_width = self._get_available_category_width()
        arrows_x = self.x + 15 + cat_width + 5
        arrows_width = 40
        return (arrows_x <= mouse_x <= arrows_x + arrows_width and
                nav_y <= mouse_y <= nav_y + nav_height)

    def _get_clicked_arrow(self, mouse_x, mouse_y):
        if self.minimized:
            return None
        cat_width = self._get_available_category_width()
        arrows_x = self.x + 15 + cat_width + 5
        if arrows_x <= mouse_x <= arrows_x + 15:
            return "left"
        elif arrows_x + 25 <= mouse_x <= arrows_x + 40:
            return "right"
        return None

    def _get_clicked_category(self, mouse_x, mouse_y):
        if self.minimized:
            return None
        if not (self.y + 45 <= mouse_y <= self.y + 70):
            return None

        current_categories = self._get_current_page_categories()
        if not current_categories:
            return None

        cat_width = self._get_available_category_width()
        # Se houver mais de uma, distribui igualmente
        total_cats = len(current_categories)
        if total_cats == 0:
            return None
        # Calcula largura de cada categoria (considerando espaços)
        gap = 5
        individual_width = (cat_width - (total_cats - 1) * gap) // total_cats

        start_x = self.x + 15
        for cat_id, cat_name, color in current_categories:
            if start_x <= mouse_x <= start_x + individual_width:
                return cat_id
            start_x += individual_width + gap
        return None

    def _get_available_category_width(self):
        """Largura total disponível para as categorias (descontando margens e setas)"""
        # Margens: 15 da esquerda + 15 da direita + espaço para setas (40) + gap
        # A largura total é self.width
        # Espaço para setas e página: ~40px + um pequeno gap
        arrows_space = 45  # 40 para setas + 5 de gap
        available = self.width - 15 - 15 - arrows_space
        return max(50, available)  # mínimo 50

    # ---------- HIT TESTS ----------
    def _is_mouse_in_area(self, mouse_x, mouse_y):
        return (self.x <= mouse_x <= self.x + self.width and
                self.y <= mouse_y <= self.y + self.height)

    def _is_mouse_in_title_area(self, mouse_x, mouse_y):
        return (self.x <= mouse_x <= self.x + self.width and
                self.y <= mouse_y <= self.y + 40)

    def _get_item_index_at(self, mouse_x, mouse_y):
        if self.minimized:
            return -1
        start_y = self.y + 80
        relative_y = mouse_y - start_y
        if relative_y < 0:
            return -1
        visual_index = relative_y // 60
        max_visible = self._get_max_visible_items()
        if visual_index >= max_visible:
            return -1
        real_index = self.scroll_offset + visual_index
        items = self.bag.get_items_for_render()
        if 0 <= real_index < len(items):
            return real_index
        return -1

    # ---------- RENDER ----------
    def render(self, screen):
        self._sync_page_with_category()
        self._draw_background(screen)
        self._draw_title(screen)

        if not self.minimized:
            self._draw_categories(screen)
            self._draw_items(screen)
            self._draw_instructions(screen)
            self._draw_scrollbar(screen)
            self._draw_resize_handle(screen)

        if self.dragging:
            self._draw_drag_indicator(screen)

    def _draw_background(self, screen):
        key = (self.width, self.height)
        if self._cached_background is not None and self._cached_background_size == key:
            screen.blit(self._cached_background, (self.x, self.y))
            return

        bg = pygame.Surface((self.width, self.height), pygame.SRCALPHA)
        for i in range(self.height):
            progress = i / self.height if self.height > 0 else 0
            alpha = int(180 + 75 * (1 - progress))
            color = (15, 20, 30, alpha)
            bg.fill(color, (0, i, self.width, 1))

        border_color = (120, 160, 240, 200) if self.mouse_over_ui else (80, 120, 200, 150)
        border_width = 3 if self.mouse_over_ui else 2
        pygame.draw.rect(bg, border_color, bg.get_rect(), border_width, border_radius=10)

        glow = pygame.Surface((self.width, 4), pygame.SRCALPHA)
        for x in range(self.width):
            dist = abs(x - self.width // 2) / (self.width // 2)
            alpha = int(100 * (1 - dist))
            glow.set_at((x, 0), (100, 150, 255, alpha))
        bg.blit(glow, (0, 0))

        self._cached_background = bg
        self._cached_background_size = key
        screen.blit(bg, (self.x, self.y))

    def _draw_title(self, screen):
        title_font = self._get_font(24)

        if self.mouse_over_ui and self.y <= pygame.mouse.get_pos()[1] <= self.y + 40:
            title_bg = pygame.Surface((self.width, 40), pygame.SRCALPHA)
            title_bg.fill((80, 100, 150, 40))
            screen.blit(title_bg, (self.x, self.y))

        title = title_font.render("MOCHILA", True, (255, 215, 0))
        screen.blit(title, (self.x + 15, self.y + 10))

        # Botão minimizar
        btn_x = self.x + self.width - 30
        btn_y = self.y + 8
        btn_size = 22
        pygame.draw.rect(screen, (60, 70, 90), (btn_x, btn_y, btn_size, btn_size), border_radius=4)
        pygame.draw.rect(screen, (180, 180, 200), (btn_x, btn_y, btn_size, btn_size), 1, border_radius=4)
        icon = "-" if not self.minimized else "+"
        icon_font = self._get_font(18, bold=True)
        icon_surf = icon_font.render(icon, True, (255, 255, 255))
        icon_rect = icon_surf.get_rect(center=(btn_x + btn_size//2, btn_y + btn_size//2))
        screen.blit(icon_surf, icon_rect)

        for i in range(4):
            dot_x = self.x + self.width - 55 + (i * 5)
            dot_y = self.y + 15
            pygame.draw.circle(screen, (150, 150, 150), (dot_x, dot_y), 2)

        pygame.draw.line(screen, (80, 100, 150),
                         (self.x + 15, self.y + 35),
                         (self.x + self.width - 15, self.y + 35), 1)

    def _draw_resize_handle(self, screen):
        if self.minimized:
            return
        handle_x = self.x + self.width - self.resize_handle_size
        handle_y = self.y + self.height - self.resize_handle_size

        if self.width >= 20 and self.height >= 20:
            pygame.draw.line(screen, (150, 150, 180),
                             (handle_x + 2, handle_y + self.resize_handle_size - 2),
                             (handle_x + self.resize_handle_size - 2, handle_y + 2), 2)
            pygame.draw.line(screen, (150, 150, 180),
                             (handle_x + 6, handle_y + self.resize_handle_size - 6),
                             (handle_x + self.resize_handle_size - 6, handle_y + 6), 2)

    def _draw_categories(self, screen):
        if self.minimized:
            return
        current_categories = self._get_current_page_categories()
        if not current_categories:
            return

        cat_width_total = self._get_available_category_width()
        num_cats = len(current_categories)
        gap = 5
        # Largura individual (arredondada para baixo)
        individual_width = (cat_width_total - (num_cats - 1) * gap) // num_cats
        if individual_width < 40:
            individual_width = 40  # mínimo

        start_x = self.x + 15
        category_font = self._get_font(16)

        for cat_id, cat_name, color in current_categories:
            cat_height = 25

            if self.bag.selected_category == cat_id:
                bg_color = (*color, 80)
                border_color = color
                text_color = (255, 255, 255)
            else:
                bg_color = (30, 35, 45, 100)
                border_color = (60, 70, 90)
                text_color = (180, 180, 200)

            cat_bg = pygame.Surface((individual_width, cat_height), pygame.SRCALPHA)
            cat_bg.fill(bg_color)
            screen.blit(cat_bg, (start_x, self.y + 45))
            pygame.draw.rect(screen, border_color,
                             (start_x, self.y + 45, individual_width, cat_height), 1, border_radius=5)

            # Centraliza o texto
            text = category_font.render(cat_name, True, text_color)
            text_x = start_x + (individual_width - text.get_width()) // 2
            screen.blit(text, (text_x, self.y + 48))

            start_x += individual_width + gap

        # Desenha navegação (setas) se houver mais de uma página
        if self.total_pages > 1:
            self._draw_category_navigation(screen, cat_width_total)

    def _draw_category_navigation(self, screen, cat_width):
        """Desenha setas e indicador de página ao lado das categorias"""
        arrows_x = self.x + 15 + cat_width + 5
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
        if self.minimized:
            return
        items = self.bag.get_items_for_render()
        if not items:
            item_font = self._get_font(20)
            empty_text = item_font.render("Nenhum item", True, (150, 150, 150))
            text_x = self.x + (self.width - empty_text.get_width()) // 2
            screen.blit(empty_text, (text_x, self.y + 120))
            return

        max_visible = self._get_max_visible_items()
        if max_visible <= 0:
            return

        start_idx = self.scroll_offset
        end_idx = min(start_idx + max_visible, len(items))
        start_y = self.y + 80
        item_height = 60

        # Calcula espaço disponível para a descrição (largura)
        # Margem esquerda: 70 (nome) + 10, margem direita: área da quantidade (~50) + 15
        desc_x = self.x + 70
        desc_max_width = self.x + self.width - 15 - (self.x + 70) - 50  # 50 para quantidade e margem
        desc_max_width = max(20, desc_max_width)

        for visual_idx, real_idx in enumerate(range(start_idx, end_idx)):
            item = items[real_idx]
            item_y = start_y + visual_idx * item_height

            if real_idx == self.bag.selected_item_index:
                bg = pygame.Surface((self.width - 10, item_height - 5), pygame.SRCALPHA)
                bg.fill((80, 120, 200, 60))
                screen.blit(bg, (self.x + 5, item_y))

                border_color = (100, 200, 255, 200)
                pygame.draw.rect(screen, border_color,
                                 (self.x + 5, item_y, self.width - 10, item_height - 5), 2, border_radius=8)
                pulse_rect = pygame.Rect(self.x + 5, item_y, self.width - 10, item_height - 5)
                self._draw_pulse_effect(screen, pulse_rect)

            elif real_idx == self.hovered_index:
                bg = pygame.Surface((self.width - 10, item_height - 5), pygame.SRCALPHA)
                bg.fill((60, 80, 120, 30))
                screen.blit(bg, (self.x + 5, item_y))

            sprite = self._get_scaled_sprite(item["id"], (32, 32))
            if sprite:
                screen.blit(sprite, (self.x + 15, item_y + 5))

            item_font = self._get_font(20)
            name_text = item_font.render(item["data"]["name"], True, (255, 255, 255))
            screen.blit(name_text, (self.x + 70, item_y + 10))

            qty_font = self._get_font(18)
            qty_text = qty_font.render(f"{item['quantity']}", True, (255, 255, 0))
            qty_bg_width = max(30, qty_text.get_width() + 10)
            qty_bg = pygame.Surface((qty_bg_width, qty_text.get_height() + 6), pygame.SRCALPHA)
            qty_bg.fill((40, 40, 60, 220))
            pygame.draw.rect(qty_bg, (100, 100, 150, 100), qty_bg.get_rect(), 1, border_radius=10)
            screen.blit(qty_bg, (self.x + self.width - qty_bg_width - 15, item_y + 8))
            screen.blit(qty_text, (self.x + self.width - qty_bg_width - 8, item_y + 12))

            # Descrição: truncar dinamicamente
            desc = item["data"]["description"]
            # Calcula quantos caracteres cabem no espaço disponível
            # Usa a fonte qty_font (18) para medir
            if desc_max_width > 0:
                # Vai truncando até caber
                full_desc = desc
                while full_desc:
                    if qty_font.size(full_desc)[0] <= desc_max_width:
                        break
                    # Remove caracteres do final
                    full_desc = full_desc[:-1]
                # Se ainda assim não couber, coloca "..."
                if qty_font.size(full_desc)[0] > desc_max_width:
                    full_desc = full_desc[:max(1, len(full_desc)-3)] + "..."
                # Garante que não fique vazio
                if not full_desc:
                    full_desc = "..."
                desc = full_desc
            else:
                desc = "..."

            desc_text = qty_font.render(desc, True, (150, 150, 170))
            screen.blit(desc_text, (desc_x, item_y + 30))

    def _draw_scrollbar(self, screen):
        if self.minimized:
            return
        items = self.bag.get_items_for_render()
        if not items:
            return
        max_visible = self._get_max_visible_items()
        if max_visible <= 0 or len(items) <= max_visible:
            return

        bar_x = self.x + self.width - 10
        bar_y = self.y + 80
        bar_height = self.height - 90
        if bar_height <= 0:
            return

        thumb_height = max(20, bar_height * max_visible / len(items))
        max_scroll = self._get_max_scroll()
        if max_scroll == 0:
            return
        scroll_ratio = self.scroll_offset / max_scroll
        thumb_y = bar_y + scroll_ratio * (bar_height - thumb_height)

        pygame.draw.rect(screen, (40, 45, 60), (bar_x, bar_y, 6, bar_height), border_radius=3)
        pygame.draw.rect(screen, (150, 160, 200), (bar_x, thumb_y, 6, thumb_height), border_radius=3)

    def _draw_pulse_effect(self, screen, rect):
        pulse = 0.5 + 0.5 * math.sin(self.animation_time * 3)
        alpha = int(50 + 30 * pulse)
        pulse_surf = pygame.Surface((rect.width, rect.height), pygame.SRCALPHA)
        pygame.draw.rect(pulse_surf, (255, 255, 255, alpha), pulse_surf.get_rect(), 1, border_radius=8)
        screen.blit(pulse_surf, rect)

    def _draw_instructions(self, screen):
        if self.minimized:
            return
        inst_y = self.y + self.height - 55
        qty_font = self._get_font(18)

        inst_bg = pygame.Surface((self.width - 20, 40), pygame.SRCALPHA)
        inst_bg.fill((20, 25, 35, 200))
        screen.blit(inst_bg, (self.x + 10, inst_y))

        instructions = [("Scroll", "Rolar"), ("TAB", "Categoria")]
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