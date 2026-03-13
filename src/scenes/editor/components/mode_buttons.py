import pygame


class ModeButtons:
    def __init__(self, viewport_x, viewport_y):
        self.buttons = []
        self._create_buttons(viewport_x, viewport_y)

    def _create_buttons(self, viewport_x, viewport_y):
        """Cria os botões de modo"""
        modes = [
            ("LAYERS", "layers"),
            ("PATH", "path"),
            ("TOWERS", "towers"),
            ("PREVIEW", "preview"),
        ]

        for i, (text, mode) in enumerate(modes):
            rect = pygame.Rect(
                viewport_x + 10,
                viewport_y + 70 + i * 40,
                90,
                30
            )
            self.buttons.append((rect, text, mode))

        # Botão de tamanho do mapa
        map_config_rect = pygame.Rect(
            viewport_x + 10,
            viewport_y + 70 + len(modes) * 40,
            90,
            30
        )
        self.buttons.append((map_config_rect, "MAP SIZE", "map_size"))

    def get_buttons(self):
        """Retorna a lista de botões"""
        return self.buttons

    def check_click(self, mouse_pos):
        """Verifica se algum botão foi clicado e retorna o modo correspondente"""
        for rect, text, mode in self.buttons:
            if rect.collidepoint(mouse_pos):
                return mode
        return None

    def render(self, screen, current_mode, font_small):
        """Renderiza os botões"""
        for rect, text, mode in self.buttons:
            # Define cores baseado no estado
            if mode == current_mode:
                color = (100, 150, 200)
                border = (255, 255, 255)
            elif mode == "map_size":
                color = (150, 100, 50)
                border = (200, 150, 100)
            else:
                color = (60, 60, 80)
                border = (100, 100, 100)

            # Renderiza botão
            pygame.draw.rect(screen, color, rect)
            pygame.draw.rect(screen, border, rect, 2)
            text_surf = font_small.render(text, True, (255, 255, 255))
            text_rect = text_surf.get_rect(center=rect.center)
            screen.blit(text_surf, text_rect)