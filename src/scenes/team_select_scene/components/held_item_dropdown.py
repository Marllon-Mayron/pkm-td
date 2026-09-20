# src/scenes/team_select_scene/components/held_item_dropdown.py

import pygame
from typing import List, Dict, Optional, Callable
from src.data.item_bag_catalog import item_bag_catalog


class HeldItemDropdown:
    """
    Dropdown para selecionar itens seguráveis nos detalhes do Pokémon.
    Exibe lista com scroll, sprites e descrições.
    """

    def __init__(self, x: int, y: int, width: int, max_visible: int = 4):
        self.x = x
        self.y = y
        self.width = width
        self.max_visible = max_visible
        self.item_height = 55
        self.padding = 8
        self.visible = False

        # ===== DIRECÃO DO DROPDOWN =====
        self.direction = "down"  # "down" ou "up"
        self.screen_height = 0  # Será definido quando o dropdown for mostrado

        # Scroll
        self.scroll_offset = 0

        # Seleção
        self.selected_index = -1

        # Items a serem exibidos: lista de dicts com id, data, quantity
        self.items: List[Dict] = []

        # Callback quando um item é selecionado
        self.on_select: Optional[Callable] = None
        self.on_close: Optional[Callable] = None

        # ===== ESTADO DA SCROLLBAR (drag) =====
        self._scroll_dragging = False
        self._scrollbar_rect = None       # Área clicável (maior que a visual)
        self._scrollbar_track_rect = None # Visual da track completa
        self._scrollbar_thumb_rect = None # Visual da thumb
        self._scroll_thumb_offset = 0     # Offset do clique dentro da thumb

        # Fontes
        self._ensure_pygame()
        self.font_small = pygame.font.Font(None, 12)
        self.font_medium = pygame.font.Font(None, 15)
        self.font_name = pygame.font.Font(None, 16)

        # Cores
        self.colors = {
            "bg": (35, 38, 48),
            "bg_hover": (55, 60, 80),
            "bg_selected": (70, 70, 120),
            "text": (240, 242, 245),
            "text_dim": (180, 185, 200),
            "text_quantity": (200, 200, 150),
            "border": (80, 85, 110),
            "scroll_bg": (25, 28, 35),
            "scroll_handle": (100, 105, 150),
            "scroll_handle_hover": (140, 145, 190),
            "scroll_handle_active": (170, 175, 220),
            "shadow": (0, 0, 0, 80),
        }

        # Estado do hover
        self.hover_index = -1
        self._scroll_hover = False

        # Cálculo da altura total
        self._calculate_height()

    def _ensure_pygame(self):
        if not pygame.get_init():
            pygame.init()
        if not pygame.font.get_init():
            pygame.font.init()

    def _calculate_height(self):
        self.total_height = min(len(self.items), self.max_visible) * self.item_height + self.padding * 2

    def set_items(self, items: List[Dict]):
        """Define a lista de itens a serem exibidos"""
        self.items = items
        self.selected_index = -1
        self.scroll_offset = 0
        self._calculate_height()

    def set_position(self, x: int, y: int):
        """Define a posição do dropdown"""
        self.x = x
        self.y = y

    def set_screen_height(self, screen_height: int):
        """Define a altura da tela para calcular a direção do dropdown"""
        self.screen_height = screen_height

    def show(self):
        """Mostra o dropdown, calculando a direção automaticamente"""
        self.visible = True
        self.scroll_offset = 0

        # ===== CALCULA A DIREÇÃO BASEADO NO ESPAÇO DISPONÍVEL =====
        if self.screen_height > 0:
            # Verifica espaço abaixo
            space_below = self.screen_height - self.y - 50
            # Verifica espaço acima
            space_above = self.y - 50

            # Se não há espaço embaixo mas há espaço em cima, abre para cima
            if self.total_height > space_below and space_above >= self.total_height:
                self.direction = "up"
                print(f"[DROPDOWN] Abrindo para CIMA (espaço abaixo: {space_below:.0f}px, acima: {space_above:.0f}px)")
            else:
                self.direction = "down"
                print(f"[DROPDOWN] Abrindo para BAIXO (espaço abaixo: {space_below:.0f}px, acima: {space_above:.0f}px)")

    def hide(self):
        """Esconde o dropdown"""
        self.visible = False
        self._scroll_dragging = False

    def toggle(self):
        """Alterna visibilidade"""
        self.visible = not self.visible
        if self.visible:
            self.scroll_offset = 0
            self._calculate_direction()

    def _calculate_direction(self):
        """Calcula a direção do dropdown baseado no espaço disponível"""
        if self.screen_height > 0:
            space_below = self.screen_height - self.y - 50
            space_above = self.y - 50

            if self.total_height > space_below and space_above >= self.total_height:
                self.direction = "up"
            else:
                self.direction = "down"

    def is_visible(self) -> bool:
        return self.visible

    # =================================================================
    # HELPERS DE GEOMETRIA
    # =================================================================
    def _get_dropdown_y(self) -> int:
        """Retorna o Y real do dropdown conforme a direção."""
        if self.direction == "up":
            return self.y - self.total_height
        return self.y

    def _has_scrollbar(self) -> bool:
        return len(self.items) > self.max_visible

    # =================================================================
    # DRAG DA SCROLLBAR
    # =================================================================
    def _begin_scroll_drag(self, mouse_pos):
        """Inicia o drag da scrollbar."""
        if not self._has_scrollbar():
            return

        thumb = self._scrollbar_thumb_rect
        if thumb and thumb.collidepoint(mouse_pos):
            # Clique na thumb: guarda offset
            self._scroll_thumb_offset = mouse_pos[1] - thumb.y
        else:
            # Clique na track: pula para a posição e começa a arrastar
            self._scroll_thumb_offset = max(1, thumb.height // 2 if thumb else 10)
            self._update_scroll_from_mouse(mouse_pos[1])

        self._scroll_dragging = True

    def _update_scroll_from_mouse(self, mouse_y: int):
        """Atualiza o scroll_offset baseado na posição Y do mouse."""
        track = self._scrollbar_track_rect
        thumb = self._scrollbar_thumb_rect
        if not track or not thumb:
            return

        thumb_h = thumb.height
        track_y = track.y
        track_h = track.height
        track_max = max(1, track_h - thumb_h)

        desired_y = mouse_y - self._scroll_thumb_offset
        desired_y = max(track_y, min(track_y + track_max, desired_y))

        ratio = (desired_y - track_y) / track_max
        max_scroll = max(0, len(self.items) - self.max_visible)
        self.scroll_offset = max(0, min(max_scroll, int(round(ratio * max_scroll))))

    # =================================================================
    # EVENTOS
    # =================================================================
    def handle_event(self, event) -> bool:
        """Processa eventos, retorna True se o evento foi consumido"""
        if not self.visible:
            return False

        # ===== DRAG ATIVO (prioridade máxima) =====
        if self._scroll_dragging:
            if event.type == pygame.MOUSEMOTION:
                self._update_scroll_from_mouse(event.pos[1])
                return True
            if event.type == pygame.MOUSEBUTTONUP and event.button == 1:
                self._scroll_dragging = False
                return True
            # Enquanto arrasta, engole tudo o mais do mouse
            if event.type in (pygame.MOUSEBUTTONDOWN,):
                return True

        if event.type == pygame.MOUSEBUTTONDOWN:
            mouse_x, mouse_y = event.pos

            # ===== SCROLLBAR (checa ANTES de tudo) =====
            if (event.button == 1 and self._scrollbar_rect
                    and self._scrollbar_rect.collidepoint(mouse_x, mouse_y)):
                self._begin_scroll_drag(event.pos)
                return True

            # Clique com botão do meio ou direito? Ignora
            if event.button != 1:
                # Scroll pelo botão 4/5 ainda funciona
                if event.button in (4, 5):
                    self._handle_scroll(-1 if event.button == 4 else 1)
                    return True
                return False

            # Verifica se clicou fora
            if not self._is_inside(mouse_x, mouse_y):
                self.hide()
                if self.on_close:
                    self.on_close()
                return True

            # Verifica clique em item
            clicked_index = self._get_item_at_pos(mouse_x, mouse_y)
            if clicked_index is not None and clicked_index < len(self.items):
                self.selected_index = clicked_index
                if self.on_select:
                    self.on_select(self.items[clicked_index])
                self.hide()
                return True

        elif event.type == pygame.MOUSEWHEEL:
            # Só consome se houver itens para rolar
            if self._has_scrollbar():
                self._handle_scroll(-event.y)
                return True
            return False

        elif event.type == pygame.KEYDOWN:
            if event.key == pygame.K_ESCAPE:
                self.hide()
                if self.on_close:
                    self.on_close()
                return True
            elif event.key == pygame.K_UP:
                self._handle_key_navigation(-1)
                return True
            elif event.key == pygame.K_DOWN:
                self._handle_key_navigation(1)
                return True
            elif event.key == pygame.K_RETURN:
                if self.selected_index >= 0 and self.selected_index < len(self.items):
                    if self.on_select:
                        self.on_select(self.items[self.selected_index])
                    self.hide()
                return True

        elif event.type == pygame.MOUSEMOTION:
            mx, my = event.pos
            # Hover da scrollbar
            self._scroll_hover = bool(
                self._scrollbar_rect and self._scrollbar_rect.collidepoint(mx, my)
            )
            # Hover dos itens (ignora se estiver sobre a scrollbar)
            if self._scroll_hover:
                self.hover_index = -1
            else:
                self.hover_index = self._get_item_at_pos(mx, my)

        return False

    def _is_inside(self, x: int, y: int) -> bool:
        """Verifica se o clique foi dentro do dropdown"""
        dropdown_y = self._get_dropdown_y()
        return (self.x <= x <= self.x + self.width and
                dropdown_y <= y <= dropdown_y + self.total_height)

    def _get_item_at_pos(self, x: int, y: int) -> Optional[int]:
        """Retorna o índice do item na posição do mouse"""
        # Ignora cliques na scrollbar (área expandida)
        if self._scrollbar_rect and self._scrollbar_rect.collidepoint(x, y):
            return None

        dropdown_y = self._get_dropdown_y()

        if not (self.x <= x <= self.x + self.width and
                dropdown_y <= y <= dropdown_y + self.total_height):
            return None

        # Ajusta para scroll
        item_y = y - dropdown_y - self.padding
        index = item_y // self.item_height + self.scroll_offset

        if 0 <= index < len(self.items):
            return index
        return None

    def _handle_scroll(self, direction: int):
        """Lida com scroll (1 = para baixo, -1 = para cima)"""
        max_scroll = max(0, len(self.items) - self.max_visible)
        self.scroll_offset += direction

        if self.scroll_offset < 0:
            self.scroll_offset = 0
        elif self.scroll_offset > max_scroll:
            self.scroll_offset = max_scroll

    def _handle_key_navigation(self, direction: int):
        """Navegação por teclado (1 = para baixo, -1 = para cima)"""
        if not self.items:
            return

        self.selected_index += direction
        if self.selected_index < 0:
            self.selected_index = len(self.items) - 1
        elif self.selected_index >= len(self.items):
            self.selected_index = 0

        # Ajusta scroll para mostrar item selecionado
        if self.selected_index < self.scroll_offset:
            self.scroll_offset = self.selected_index
        elif self.selected_index >= self.scroll_offset + self.max_visible:
            self.scroll_offset = self.selected_index - self.max_visible + 1

    # =================================================================
    # RENDER
    # =================================================================
    def render(self, screen: pygame.Surface) -> pygame.Rect:
        """Renderiza o dropdown, retorna o rect da área"""
        if not self.visible or not self.items:
            return pygame.Rect(self.x, self.y, 0, 0)

        # ===== RESETA RECTS DE INTERAÇÃO A CADA FRAME =====
        self._scrollbar_rect = None
        self._scrollbar_track_rect = None
        self._scrollbar_thumb_rect = None

        dropdown_x = self.x
        dropdown_y = self._get_dropdown_y()

        # Sombra
        shadow_surf = pygame.Surface((self.width, self.total_height), pygame.SRCALPHA)
        shadow_surf.fill((0, 0, 0, 120))
        screen.blit(shadow_surf, (dropdown_x + 4, dropdown_y + 4))

        # Fundo
        rect = pygame.Rect(dropdown_x, dropdown_y, self.width, self.total_height)
        pygame.draw.rect(screen, self.colors["bg"], rect, border_radius=8)
        pygame.draw.rect(screen, self.colors["border"], rect, 2, border_radius=8)

        # Clip para scroll
        clip_rect = pygame.Rect(dropdown_x + 2, dropdown_y + 2,
                                self.width - 4, self.total_height - 4)
        old_clip = screen.get_clip()
        screen.set_clip(clip_rect)

        # Desenha itens visíveis
        start_idx = self.scroll_offset
        end_idx = min(start_idx + self.max_visible, len(self.items))

        for i in range(start_idx, end_idx):
            item = self.items[i]
            item_y = dropdown_y + self.padding + (i - start_idx) * self.item_height

            # Fundo do item
            item_rect = pygame.Rect(dropdown_x + 4, item_y,
                                    self.width - 8, self.item_height - 2)

            # Cor do fundo
            if i == self.selected_index:
                color = self.colors["bg_selected"]
            elif i == self.hover_index:
                color = self.colors["bg_hover"]
            else:
                color = self.colors["bg"]

            pygame.draw.rect(screen, color, item_rect, border_radius=4)
            pygame.draw.rect(screen, (50, 55, 70), item_rect, 1, border_radius=4)

            # Sprite do item (36x36)
            sprite = self._get_item_sprite(item["id"])
            if sprite:
                sprite_rect = sprite.get_rect()
                sprite_rect.topleft = (dropdown_x + 10,
                                       item_y + (self.item_height - 36) // 2)
                # Fundo brilhante atrás do sprite
                sprite_bg_rect = pygame.Rect(sprite_rect.x - 4, sprite_rect.y - 4, 44, 44)
                pygame.draw.rect(screen, (50, 55, 70), sprite_bg_rect, border_radius=6)
                screen.blit(sprite, sprite_rect)
                text_x = dropdown_x + 60
            else:
                text_x = dropdown_x + 12

            # Nome do item
            name_text = item["data"]["name"]
            if len(name_text) > 20:
                name_text = name_text[:17] + "..."
            name_surf = self.font_name.render(name_text, True, self.colors["text"])
            screen.blit(name_surf, (text_x, item_y + 4))

            # Quantidade
            qty_text = f"x{item['quantity']}"
            qty_surf = self.font_small.render(qty_text, True, self.colors["text_quantity"])
            qty_x = dropdown_x + self.width - qty_surf.get_width() - 12
            screen.blit(qty_surf, (qty_x, item_y + 6))

            # Descrição (versão curta)
            desc = item["data"].get("description", "")
            if len(desc) > 35:
                desc = desc[:32] + "..."
            desc_surf = self.font_small.render(desc, True, self.colors["text_dim"])
            screen.blit(desc_surf, (text_x, item_y + 26))

            # Efeito do item (type_boost)
            effect_value = item["data"].get("effect_value", {})
            if isinstance(effect_value, dict) and "type_boost" in effect_value:
                boost = effect_value["type_boost"]
                boost_text = f"+{int((boost - 1) * 100)}%"
                boost_surf = self.font_small.render(boost_text, True, (100, 220, 100))
                screen.blit(boost_surf, (text_x + 160, item_y + 26))

        screen.set_clip(old_clip)

        # Scrollbar (se necessário)
        if self._has_scrollbar():
            self._render_scrollbar(screen, dropdown_x, dropdown_y)

        return rect

    def _render_scrollbar(self, screen: pygame.Surface,
                          dropdown_x: int, dropdown_y: int):
        """Renderiza a barra de scroll e armazena rects para hit-testing."""
        scroll_x = dropdown_x + self.width - 8
        scroll_y = dropdown_y + 4
        scroll_height = self.total_height - 8
        scroll_w = 5

        total = len(self.items)
        visible = min(self.max_visible, total)
        max_scroll = max(1, total - visible)

        thumb_h = max(24, int(scroll_height * (visible / total)))
        thumb_y = scroll_y + int((self.scroll_offset / max_scroll) *
                                 (scroll_height - thumb_h))

        # Fundo da track
        pygame.draw.rect(screen, self.colors["scroll_bg"],
                         (scroll_x, scroll_y, scroll_w, scroll_height),
                         border_radius=3)

        # Cor da thumb conforme estado
        if self._scroll_dragging:
            thumb_color = self.colors["scroll_handle_active"]
        elif self._scroll_hover:
            thumb_color = self.colors["scroll_handle_hover"]
        else:
            thumb_color = self.colors["scroll_handle"]

        # Thumb
        pygame.draw.rect(screen, thumb_color,
                         (scroll_x, thumb_y, scroll_w, thumb_h),
                         border_radius=3)

        # ===== GUARDA RECTS PARA HIT-TESTING =====
        self._scrollbar_track_rect = pygame.Rect(
            scroll_x, scroll_y, scroll_w, scroll_height)
        self._scrollbar_thumb_rect = pygame.Rect(
            scroll_x, thumb_y, scroll_w, thumb_h)
        self._scrollbar_rect = pygame.Rect(
            scroll_x - 5, scroll_y, scroll_w + 12, scroll_height)

    def _get_item_sprite(self, item_id: str) -> Optional[pygame.Surface]:
        """Retorna o sprite do item (escalado para 36x36)"""
        sprite = item_bag_catalog.get_sprite(item_id, scaled=True)
        if sprite:
            current_size = sprite.get_size()
            if current_size != (36, 36):
                sprite = pygame.transform.scale(sprite, (36, 36))
        return sprite

    def get_selected_item(self) -> Optional[Dict]:
        """Retorna o item selecionado atualmente"""
        if 0 <= self.selected_index < len(self.items):
            return self.items[self.selected_index]
        return None