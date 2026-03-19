# src/scenes/game_scene/components/ui/item_bag_renderer.py

import pygame
import math
from src.data.item_bag_catalog import item_bag_catalog


class ItemBagRenderer:
    """Renderiza a mochila no canto inferior esquerdo - AGORA ARRASTÁVEL"""

    def __init__(self, game, bag_manager):
        self.game = game
        self.bag = bag_manager
        self.catalog = item_bag_catalog

        # Posicionamento inicial (canto inferior esquerdo)
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

        # Foco do scroll (só rola se mouse estiver sobre a UI)
        self.mouse_over_ui = False

        # Fontes
        self._create_fonts()

    def _create_fonts(self):
        """Cria fontes"""
        self.title_font = pygame.font.Font(None, 24)
        self.item_font = pygame.font.Font(None, 20)
        self.quantity_font = pygame.font.Font(None, 18)
        self.category_font = pygame.font.Font(None, 16)

    def update(self, dt):
        """Atualiza animações"""
        self.animation_time += dt
        self.pulse_alpha = 100 + int(55 * math.sin(self.animation_time * 5))

    def update_hover(self, mouse_pos):
        """Atualiza o índice do item sob o mouse"""
        mouse_x, mouse_y = mouse_pos
        self.mouse_over_ui = self._is_mouse_in_area(mouse_x, mouse_y)

        if self.mouse_over_ui:
            # Verifica se está sobre um item específico
            index = self._get_item_index_at(mouse_x, mouse_y)
            if index >= 0:
                self.hovered_index = index
            else:
                # Se não está sobre nenhum item, mostra o item selecionado
                self.hovered_index = self.bag.selected_item_index
        else:
            self.hovered_index = -1

    def handle_event(self, event):
        """Processa eventos na UI de itens"""

        # PRIMEIRO: Verifica se é clique em um item para arrastar
        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            mouse_x, mouse_y = event.pos

            # Verifica se clicou na área do título (para arrastar a UI)
            if self._is_mouse_in_title_area(mouse_x, mouse_y):
                self.dragging = True
                self.drag_offset_x = self.x - mouse_x
                self.drag_offset_y = self.y - mouse_y
                self.drag_start_mouse = (mouse_x, mouse_y)
                pygame.mouse.set_cursor(pygame.SYSTEM_CURSOR_SIZEALL)
                return True  # Evento consumido - arrastando UI

            # Verifica se clicou em um item (NÃO consome o evento, apenas marca)
            elif self._is_mouse_in_area(mouse_x, mouse_y):
                index = self._get_item_index_at(mouse_x, mouse_y)
                if index >= 0:
                    # Só marca qual item foi clicado, não consome o evento
                    # Isso permite que o GameScene também receba o evento
                    self.clicked_item_index = index
                    # NÃO retorna True - deixa o evento passar!
                    # O GameScene vai capturar e iniciar o arrasto

        # ARRASTO DA UI (já iniciado)
        elif event.type == pygame.MOUSEMOTION:
            if self.dragging:
                # Move a UI
                self.x = event.pos[0] + self.drag_offset_x
                self.y = event.pos[1] + self.drag_offset_y

                # Limites para não sair da tela
                self.x = max(5, min(self.game.screen_manager.window_width - self.width - 5, self.x))
                self.y = max(5, min(self.game.screen_manager.window_height - self.height - 5, self.y))
                return True  # Evento consumido - arrastando UI

            # Atualiza hover (sempre)
            self.update_hover(event.pos)

        # FINALIZA ARRASTO DA UI
        elif event.type == pygame.MOUSEBUTTONUP:
            if event.button == 1 and self.dragging:
                self.dragging = False
                pygame.mouse.set_cursor(pygame.SYSTEM_CURSOR_ARROW)
                return True  # Evento consumido - finalizou arrasto UI

        # SCROLL (mantém como estava)
        if event.type == pygame.MOUSEWHEEL:
            if self.mouse_over_ui:
                self.hovered_index = self.bag.selected_item_index
                return True  # Indica que processamos o evento

        return False

    def _is_mouse_in_area(self, mouse_x, mouse_y):
        """Verifica se mouse está na área dos itens"""
        return (self.x <= mouse_x <= self.x + self.width and
                self.y <= mouse_y <= self.y + self.height)

    def _is_mouse_in_title_area(self, mouse_x, mouse_y):
        """Verifica se mouse está na área do título (para arrastar)"""
        return (self.x <= mouse_x <= self.x + self.width and
                self.y <= mouse_y <= self.y + 40)  # Só a parte superior

    def _get_item_index_at(self, mouse_x, mouse_y):
        """Retorna índice do item sob o mouse"""
        start_y = self.y + 70  # Abaixo do título e categorias

        relative_y = mouse_y - start_y
        if relative_y < 0:
            return -1

        index = relative_y // 60  # 60px por item
        items = self.bag.get_items_for_render()

        if 0 <= index < len(items):
            return index
        return -1

    def render(self, screen):
        """Renderiza a UI da mochila"""

        # Fundo com efeito glass
        self._draw_background(screen)

        # Título (com indicador de arrasto)
        self._draw_title(screen)

        # Categorias
        self._draw_categories(screen)

        # Itens
        self._draw_items(screen)

        # Instruções
        self._draw_instructions(screen)

        # Indicador de arrasto (se estiver arrastando)
        if self.dragging:
            self._draw_drag_indicator(screen)

    def _draw_background(self, screen):
        """Desenha fundo com efeito glass"""
        # Fundo semi-transparente
        bg = pygame.Surface((self.width, self.height), pygame.SRCALPHA)

        # Gradiente vertical
        for i in range(self.height):
            progress = i / self.height
            alpha = int(180 + 75 * (1 - progress))
            color = (15, 20, 30, alpha)
            bg.fill(color, (0, i, self.width, 1))

        screen.blit(bg, (self.x, self.y))

        # Borda com brilho (mais forte se mouse over)
        if self.mouse_over_ui:
            border_color = (120, 160, 240, 200)
            border_width = 3
        else:
            border_color = (80, 120, 200, 150)
            border_width = 2

        pygame.draw.rect(screen, border_color,
                         (self.x, self.y, self.width, self.height),
                         border_width, border_radius=10)

        # Brilho na borda superior
        glow = pygame.Surface((self.width, 4), pygame.SRCALPHA)
        for x in range(self.width):
            dist = abs(x - self.width // 2) / (self.width // 2)
            alpha = int(100 * (1 - dist))
            glow.set_at((x, 0), (100, 150, 255, alpha))
        screen.blit(glow, (self.x, self.y))

    def _draw_title(self, screen):
        """Desenha título da seção (arrastável)"""
        # Fundo do título (para indicar que é arrastável)
        title_bg = pygame.Surface((self.width, 40), pygame.SRCALPHA)
        if self.mouse_over_ui and self.y <= pygame.mouse.get_pos()[1] <= self.y + 40:
            title_bg.fill((80, 100, 150, 40))  # Highlight quando mouse sobre o título
        screen.blit(title_bg, (self.x, self.y))

        title = self.title_font.render("MOCHILA", True, (255, 215, 0))
        screen.blit(title, (self.x + 15, self.y + 10))

        # Ícone de arrasto (4 pontinhos)
        for i in range(4):
            dot_x = self.x + self.width - 25 + (i * 5)
            dot_y = self.y + 15
            pygame.draw.circle(screen, (150, 150, 150), (dot_x, dot_y), 2)

        # Linha decorativa
        pygame.draw.line(screen, (80, 100, 150),
                         (self.x + 15, self.y + 35),
                         (self.x + self.width - 15, self.y + 35), 1)

    def _draw_categories(self, screen):
        """Desenha seletor de categorias"""
        categories = [
            ("all", "Todos", (150, 150, 150)),
            ("pokeball", "Pokébolas", (255, 100, 100)),
            ("medicine", "Poções", (100, 255, 100))
        ]

        start_x = self.x + 15
        for cat_id, cat_name, color in categories:
            # Fundo da categoria
            cat_width = 70
            cat_height = 25

            # Destaca categoria selecionada
            if self.bag.selected_category == cat_id:
                bg_color = (*color, 80)
                border_color = color
                text_color = (255, 255, 255)
            else:
                bg_color = (30, 35, 45, 100)
                border_color = (60, 70, 90)
                text_color = (180, 180, 200)

            # Fundo
            cat_bg = pygame.Surface((cat_width, cat_height), pygame.SRCALPHA)
            cat_bg.fill(bg_color)
            screen.blit(cat_bg, (start_x, self.y + 45))

            # Borda
            pygame.draw.rect(screen, border_color,
                             (start_x, self.y + 45, cat_width, cat_height), 1, border_radius=5)

            # Texto
            text = self.category_font.render(cat_name, True, text_color)
            text_x = start_x + (cat_width - text.get_width()) // 2
            screen.blit(text, (text_x, self.y + 48))

            start_x += cat_width + 5

    def _draw_items(self, screen):
        """Desenha a lista de itens"""
        items = self.bag.get_items_for_render()

        if not items:
            # Mensagem de vazio
            empty_text = self.item_font.render("Nenhum item", True, (150, 150, 150))
            text_x = self.x + (self.width - empty_text.get_width()) // 2
            screen.blit(empty_text, (text_x, self.y + 120))
            return

        start_y = self.y + 80
        item_height = 60

        for i, item in enumerate(items):
            item_y = start_y + i * item_height

            # Fundo do item (se hover ou selecionado)
            if i == self.bag.selected_item_index:
                # Item selecionado - fundo mais forte
                bg = pygame.Surface((self.width - 10, item_height - 5), pygame.SRCALPHA)
                bg.fill((80, 120, 200, 60))
                screen.blit(bg, (self.x + 5, item_y))

                # Borda brilhante
                border_color = (100, 200, 255, 200)
                pygame.draw.rect(screen, border_color,
                                 (self.x + 5, item_y, self.width - 10, item_height - 5), 2, border_radius=8)

                # Efeito de pulso
                pulse_rect = pygame.Rect(self.x + 5, item_y, self.width - 10, item_height - 5)
                self._draw_pulse_effect(screen, pulse_rect)

            elif i == self.hovered_index:
                # Hover - fundo sutil
                bg = pygame.Surface((self.width - 10, item_height - 5), pygame.SRCALPHA)
                bg.fill((60, 80, 120, 30))
                screen.blit(bg, (self.x + 5, item_y))

            # Sprite do item
            sprite = self.catalog.get_sprite(item["id"], scaled=True)
            if sprite:
                screen.blit(sprite, (self.x + 15, item_y + 5))

            # Nome do item
            name_text = self.item_font.render(item["data"]["name"], True, (255, 255, 255))
            screen.blit(name_text, (self.x + 70, item_y + 10))

            # QUANTIDADE COM FUNDO DESTACADO
            qty_text = self.quantity_font.render(f"{item['quantity']}", True, (255, 255, 0))

            # Fundo para quantidade (formato de bolha)
            qty_bg_width = max(30, qty_text.get_width() + 10)
            qty_bg = pygame.Surface((qty_bg_width, qty_text.get_height() + 6), pygame.SRCALPHA)
            qty_bg.fill((40, 40, 60, 220))

            # Borda arredondada
            pygame.draw.rect(qty_bg, (100, 100, 150, 100),
                             qty_bg.get_rect(), 1, border_radius=10)

            screen.blit(qty_bg, (self.x + self.width - qty_bg_width - 15, item_y + 8))
            screen.blit(qty_text, (self.x + self.width - qty_bg_width - 8, item_y + 12))

            # Descrição
            desc_text = self.quantity_font.render(item["data"]["description"][:25] + "...",
                                                  True, (150, 150, 170))
            screen.blit(desc_text, (self.x + 70, item_y + 30))

    def _draw_pulse_effect(self, screen, rect):
        """Desenha efeito de pulso no item selecionado"""
        pulse = 0.5 + 0.5 * math.sin(self.animation_time * 3)
        alpha = int(50 + 30 * pulse)

        pulse_surf = pygame.Surface((rect.width, rect.height), pygame.SRCALPHA)
        pygame.draw.rect(pulse_surf, (255, 255, 255, alpha), pulse_surf.get_rect(), 1, border_radius=8)
        screen.blit(pulse_surf, rect)

    def _draw_instructions(self, screen):
        """Desenha instruções de uso"""
        inst_y = self.y + self.height - 55

        # Fundo das instruções
        inst_bg = pygame.Surface((self.width - 20, 40), pygame.SRCALPHA)
        inst_bg.fill((20, 25, 35, 200))
        screen.blit(inst_bg, (self.x + 10, inst_y))

        # Instruções
        instructions = [
            ("Scroll", "Alternar"),
            ("TAB", "Categoria"),
        ]

        x = self.x + 20
        for key, action in instructions:
            # Tecla em destaque
            key_text = self.quantity_font.render(key, True, (255, 215, 0))
            screen.blit(key_text, (x, inst_y + 8))

            # Ação
            action_text = self.quantity_font.render(action, True, (180, 180, 200))
            screen.blit(action_text, (x + 5 + key_text.get_width(), inst_y + 8))

            x += 100

    def _draw_drag_indicator(self, screen):
        """Desenha indicador de que está arrastando"""
        shadow = pygame.Surface((self.width, self.height), pygame.SRCALPHA)
        shadow.fill((255, 255, 255, 30))
        screen.blit(shadow, (self.x + 5, self.y + 5))

        font = pygame.font.Font(None, 20)
        text = font.render("Arraste para posicionar", True, (255, 255, 255))
        text_x = self.x + (self.width - text.get_width()) // 2
        text_y = self.y + self.height // 2
        screen.blit(text, (text_x, text_y))