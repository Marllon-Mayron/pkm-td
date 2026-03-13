import pygame
from src.editor.layer_manager import LayerType


class LayerSelector:
    def __init__(self, x, y, width, height):
        self.rect = pygame.Rect(x, y, width, height)
        self.layers = []
        self.selected_layer = 0
        self.visible = True
        self.focused = False

        # Para redimensionamento
        self.resizing = False
        self.resize_margin = 10
        self.min_width = 120
        self.min_height = 150

        # Para arrastar
        self.dragging = False
        self.drag_start_x = 0
        self.drag_start_y = 0

    def set_layers(self, layers):
        """Define as layers a serem exibidas"""
        self.layers = layers

    def handle_event(self, event):
        """Processa eventos do seletor de layers"""
        if not self.visible:
            return False

        mouse_pos = pygame.mouse.get_pos()
        mouse_x, mouse_y = mouse_pos

        # Verifica foco
        self.focused = self.rect.collidepoint(mouse_x, mouse_y)

        if event.type == pygame.MOUSEBUTTONDOWN:
            if event.button == 1:
                return self._handle_left_click(mouse_x, mouse_y)
        elif event.type == pygame.MOUSEBUTTONUP:
            if event.button == 1:
                self.resizing = False
                self.dragging = False
        elif event.type == pygame.MOUSEMOTION:
            return self._handle_mouse_motion(mouse_x, mouse_y)

        return False

    def _handle_left_click(self, mouse_x, mouse_y):
        """Processa clique esquerdo"""
        # Redimensionamento
        if (self.rect.right - self.resize_margin <= mouse_x <= self.rect.right + self.resize_margin and
            self.rect.bottom - self.resize_margin <= mouse_y <= self.rect.bottom + self.resize_margin):
            self.resizing = True
            return True

        # Arrastar pelo título
        title_rect = pygame.Rect(self.rect.x, self.rect.y, self.rect.width, 25)
        if title_rect.collidepoint(mouse_x, mouse_y):
            self.dragging = True
            self.drag_start_x = mouse_x - self.rect.x
            self.drag_start_y = mouse_y - self.rect.y
            return True

        # Selecionar layer (só com foco)
        if self.focused:
            local_y = mouse_y - self.rect.y - 30
            index = local_y // 28
            if 0 <= index < len(self.layers):
                self.selected_layer = index
                return True
        return False

    def _handle_mouse_motion(self, mouse_x, mouse_y):
        """Processa movimento do mouse"""
        if self.resizing:
            new_width = max(self.min_width, mouse_x - self.rect.x)
            new_height = max(self.min_height, mouse_y - self.rect.y)
            self.rect.width = new_width
            self.rect.height = new_height
            return True
        elif self.dragging:
            self.rect.x = mouse_x - self.drag_start_x
            self.rect.y = mouse_y - self.drag_start_y
            return True
        return False

    def render(self, screen, current_layer_index):
        """Renderiza o seletor de layers"""
        if not self.visible:
            return

        self._render_background(screen)
        self._render_title(screen)
        self._render_layers(screen, current_layer_index)
        self._render_resize_handle(screen)

    def _render_background(self, screen):
        """Renderiza o fundo"""
        # Sombra
        shadow_rect = self.rect.copy()
        shadow_rect.x += 3
        shadow_rect.y += 3
        pygame.draw.rect(screen, (20, 20, 30), shadow_rect, border_radius=8)

        # Fundo
        if self.focused:
            bg_color = (60, 60, 75)
            border_color = (140, 140, 160)
        else:
            bg_color = (45, 45, 55)
            border_color = (90, 90, 100)

        pygame.draw.rect(screen, bg_color, self.rect, border_radius=8)
        pygame.draw.rect(screen, border_color, self.rect, 2, border_radius=8)

    def _render_title(self, screen):
        """Renderiza o título"""
        font = pygame.font.Font(None, 20)
        title = font.render("LAYERS", True, (255, 255, 255))
        screen.blit(title, (self.rect.x + 10, self.rect.y + 5))

    def _render_layers(self, screen, current_layer_index):
        """Renderiza a lista de layers"""
        # Cores para cada tipo
        type_colors = {
            LayerType.GROUND: (80, 80, 90),
            LayerType.DECORATION: (70, 100, 70),
            LayerType.CEILING: (100, 70, 70),
        }

        type_names = {
            LayerType.GROUND: "Chão",
            LayerType.DECORATION: "Decoração",
            LayerType.CEILING: "Teto",
        }

        type_abbr = {
            LayerType.GROUND: "C",
            LayerType.DECORATION: "D",
            LayerType.CEILING: "T",
        }

        # Área de clipping
        clip_rect = pygame.Rect(
            self.rect.x + 5,
            self.rect.y + 30,
            self.rect.width - 10,
            self.rect.height - 35
        )

        old_clip = screen.get_clip()
        screen.set_clip(clip_rect)

        # Lista layers
        y_offset = 0
        for i, layer in enumerate(self.layers):
            layer_rect = pygame.Rect(
                self.rect.x + 5,
                self.rect.y + 30 + y_offset,
                self.rect.width - 10,
                25
            )

            bg_color = type_colors.get(layer.layer_type, (80, 80, 80))

            if i == current_layer_index:
                bg_color = tuple(min(255, c + 40) for c in bg_color)
                border_color = (255, 255, 255)
            else:
                border_color = (80, 80, 90)

            pygame.draw.rect(screen, bg_color, layer_rect)
            pygame.draw.rect(screen, border_color, layer_rect, 1)

            # Nome da layer
            name_font = pygame.font.Font(None, 14)
            name_text = f"{layer.name[:8]}"
            name_surf = name_font.render(name_text, True, (255, 255, 255))
            screen.blit(name_surf, (layer_rect.x + 3, layer_rect.y + 5))

            # Tipo abreviado
            type_surf = name_font.render(type_abbr[layer.layer_type], True, (200, 200, 200))
            screen.blit(type_surf, (layer_rect.x + 40, layer_rect.y + 5))

            # Indicador de visibilidade
            vis_color = (0, 255, 0) if layer.visible else (100, 100, 100)
            pygame.draw.circle(screen, vis_color, (layer_rect.right - 10, layer_rect.centery), 4)

            y_offset += 28

        screen.set_clip(old_clip)

    def _render_resize_handle(self, screen):
        """Renderiza a alça de redimensionamento"""
        resize_handle = pygame.Rect(
            self.rect.right - 15,
            self.rect.bottom - 15,
            10,
            10
        )
        pygame.draw.rect(screen, (150, 150, 150), resize_handle)
        pygame.draw.line(screen, (200, 200, 200),
                        (resize_handle.x + 2, resize_handle.bottom - 2),
                        (resize_handle.right - 2, resize_handle.y + 2), 2)