"""
Cena principal do jogo
"""
import pygame
from src.scenes.base_scene import BaseScene

class GameScene(BaseScene):
    def __init__(self, game, phase_number=1):
        super().__init__(game)

        self.phase_number = phase_number

        # Tamanho do mundo
        self.world_width = 3000
        self.world_height = 3000

        # Inicializa câmera
        self.game.initialize_camera(self.world_width, self.world_height)
        self.camera = self.game.camera

        # Configurações da grid
        self.show_grid = True
        self.grid_size = 16
        self.grid_color = (60, 60, 80)
        self.grid_alpha = 100

        # Debug
        self.show_debug = True

        # Controle de arrasto da câmera
        self.dragging_camera = False
        self.last_mouse_pos = None

        print(f"GameScene iniciada - Fase {phase_number} - Mundo: {self.world_width}x{self.world_height}")
        print(f"Grid ativada por padrão (tecla G para toggle)")
        print(f"Arraste com botão do meio para mover a câmera")

    def handle_event(self, event):
        """Processa eventos do jogo"""
        if event.type == pygame.KEYDOWN:
            if event.key == pygame.K_p:
                self.toggle_pause()
            elif event.key == pygame.K_ESCAPE:
                self.game.current_scene = self.game.menu_scene
            elif event.key == pygame.K_F1:
                self.show_debug = not self.show_debug
            elif event.key == pygame.K_g:
                self.show_grid = not self.show_grid
                print(f"[DEBUG] Grid {'ativada' if self.show_grid else 'desativada'}")
            elif event.key == pygame.K_SPACE:
                mouse_pos = pygame.mouse.get_pos()
                if self.screen_manager.is_mouse_in_viewport(mouse_pos):
                    world_pos = self.screen_manager.get_mouse_world_position(mouse_pos, self.camera)
                    if world_pos:
                        print(f"[DEBUG] Posição do mouse no mundo: ({world_pos[0]:.0f}, {world_pos[1]:.0f})")

        elif event.type == pygame.MOUSEBUTTONDOWN:
            mouse_pos = pygame.mouse.get_pos()

            # Verifica se clicou no viewport
            in_viewport = self.screen_manager.is_mouse_in_viewport(mouse_pos)

            if event.button == 1:  # Clique esquerdo
                if in_viewport:
                    world_pos = self.screen_manager.get_mouse_world_position(mouse_pos, self.camera)
                    if world_pos:
                        print(f"[DEBUG] Clique no mundo: ({world_pos[0]:.0f}, {world_pos[1]:.0f})")

            elif event.button == 2:  # Botão do meio/scroll - ARRASTO DA CÂMERA
                if in_viewport:
                    self.dragging_camera = True
                    self.last_mouse_pos = mouse_pos
                    pygame.mouse.set_cursor(pygame.SYSTEM_CURSOR_SIZEALL)  # Muda cursor para movimento
                    return True

        elif event.type == pygame.MOUSEBUTTONUP:
            if event.button == 2:  # Botão do meio/scroll
                if self.dragging_camera:
                    self.dragging_camera = False
                    self.last_mouse_pos = None
                    pygame.mouse.set_cursor(pygame.SYSTEM_CURSOR_ARROW)  # Volta cursor normal
                    return True

        elif event.type == pygame.MOUSEMOTION:
            if self.dragging_camera and self.last_mouse_pos:
                # Calcula a diferença do movimento
                dx = event.pos[0] - self.last_mouse_pos[0]
                dy = event.pos[1] - self.last_mouse_pos[1]

                # Converte para movimento no mundo (considerando zoom)
                world_dx = dx / self.camera.zoom
                world_dy = dy / self.camera.zoom

                # Move a câmera na direção OPOSTA ao arrasto
                self.camera.x -= world_dx
                self.camera.y -= world_dy

                # Garante que a câmera respeita os limites
                self.camera._clamp_position()

                self.last_mouse_pos = event.pos
                return True

        elif event.type == pygame.MOUSEWHEEL:
            if not self.paused:
                # Só faz zoom se não estiver arrastando a câmera
                if not self.dragging_camera:
                    # Verifica se o mouse está sobre o viewport
                    mouse_pos = pygame.mouse.get_pos()
                    if self.screen_manager.is_mouse_in_viewport(mouse_pos):
                        # Pega posição do mundo antes do zoom
                        world_pos = self.screen_manager.get_mouse_world_position(mouse_pos, self.camera)

                        if world_pos:
                            # Guarda a posição do mundo que queremos manter sob o mouse
                            target_world_x, target_world_y = world_pos

                            # Aplica zoom
                            self.camera.handle_zoom(event.y > 0)

                            # Após o zoom, recalcula onde esse ponto do mundo está na tela
                            # e ajusta a câmera para mantê-lo na mesma posição de tela
                            new_mouse_pos = pygame.mouse.get_pos()
                            new_world_pos = self.screen_manager.get_mouse_world_position(new_mouse_pos, self.camera)

                            if new_world_pos:
                                # Calcula a diferença e ajusta a câmera
                                dx = target_world_x - new_world_pos[0]
                                dy = target_world_y - new_world_pos[1]

                                self.camera.x += dx
                                self.camera.y += dy

                                # Garante que está dentro dos limites
                                self.camera._clamp_position()

    def fixed_update(self, dt):
        """Update da lógica do jogo"""
        if self.paused:
            return

    def render(self, screen):
        """Renderiza o jogo - Grid + Debug"""
        # Limpa a tela (fundo preto simples)
        screen.fill((0, 0, 0))

        # Desenha a grid se ativada
        if self.show_grid:
            self._draw_grid(screen)

        # Desenha borda do viewport
        pygame.draw.rect(screen, (80, 80, 80),
                        (self.screen_manager.viewport_x,
                         self.screen_manager.viewport_y,
                         self.screen_manager.viewport_width,
                         self.screen_manager.viewport_height), 1)

        # Mostra número da fase no centro
        self._draw_phase_info(screen)

        # UI mínima
        self._render_minimal_ui(screen)

        # Overlay de pausa
        if self.paused:
            self._render_pause_overlay(screen)

        # Debug info
        if self.show_debug:
            self._render_debug_info(screen)

    def _draw_phase_info(self, screen):
        """Desenha informação da fase no centro"""
        font_large = pygame.font.Font(None, 72)
        phase_text = font_large.render(f"FASE {self.phase_number}", True, (40, 40, 40))
        text_rect = phase_text.get_rect(center=(
            self.screen_manager.viewport_x + self.screen_manager.viewport_width // 2,
            self.screen_manager.viewport_y + self.screen_manager.viewport_height // 2
        ))
        screen.blit(phase_text, text_rect)

    def _draw_grid(self, screen):
        """Desenha uma grid alinhada com o mundo"""
        visible_rect = self.camera.get_visible_rect()

        start_x = int(visible_rect.left // self.grid_size) * self.grid_size
        start_y = int(visible_rect.top // self.grid_size) * self.grid_size
        end_x = int(visible_rect.right // self.grid_size) * self.grid_size + self.grid_size
        end_y = int(visible_rect.bottom // self.grid_size) * self.grid_size + self.grid_size

        grid_surface = pygame.Surface((self.screen_manager.viewport_width,
                                      self.screen_manager.viewport_height), pygame.SRCALPHA)

        # Linhas verticais
        x = start_x
        while x <= end_x:
            render_x1, render_y1 = self._world_to_render(x, visible_rect.top)
            render_x2, render_y2 = self._world_to_render(x, visible_rect.bottom)

            screen_x1, screen_y1 = self.screen_manager.get_screen_position(render_x1, render_y1)
            screen_x2, screen_y2 = self.screen_manager.get_screen_position(render_x2, render_y2)

            grid_x1 = screen_x1 - self.screen_manager.viewport_x
            grid_y1 = screen_y1 - self.screen_manager.viewport_y
            grid_x2 = screen_x2 - self.screen_manager.viewport_x
            grid_y2 = screen_y2 - self.screen_manager.viewport_y

            pygame.draw.line(grid_surface, self.grid_color + (self.grid_alpha,),
                           (grid_x1, grid_y1), (grid_x2, grid_y2), 1)

            x += self.grid_size

        # Linhas horizontais
        y = start_y
        while y <= end_y:
            render_x1, render_y1 = self._world_to_render(visible_rect.left, y)
            render_x2, render_y2 = self._world_to_render(visible_rect.right, y)

            screen_x1, screen_y1 = self.screen_manager.get_screen_position(render_x1, render_y1)
            screen_x2, screen_y2 = self.screen_manager.get_screen_position(render_x2, render_y2)

            grid_x1 = screen_x1 - self.screen_manager.viewport_x
            grid_y1 = screen_y1 - self.screen_manager.viewport_y
            grid_x2 = screen_x2 - self.screen_manager.viewport_x
            grid_y2 = screen_y2 - self.screen_manager.viewport_y

            pygame.draw.line(grid_surface, self.grid_color + (self.grid_alpha,),
                           (grid_x1, grid_y1), (grid_x2, grid_y2), 1)

            y += self.grid_size

        screen.blit(grid_surface, (self.screen_manager.viewport_x, self.screen_manager.viewport_y))

        # Desenha o centro do mundo
        center_x, center_y = self._world_to_render(self.world_width/2, self.world_height/2)
        screen_center_x, screen_center_y = self.screen_manager.get_screen_position(center_x, center_y)

        if (self.screen_manager.viewport_x <= screen_center_x <= self.screen_manager.viewport_x + self.screen_manager.viewport_width and
            self.screen_manager.viewport_y <= screen_center_y <= self.screen_manager.viewport_y + self.screen_manager.viewport_height):
            size = 10
            pygame.draw.line(screen, (255, 0, 0),
                           (screen_center_x - size, screen_center_y - size),
                           (screen_center_x + size, screen_center_y + size), 2)
            pygame.draw.line(screen, (255, 0, 0),
                           (screen_center_x + size, screen_center_y - size),
                           (screen_center_x - size, screen_center_y + size), 2)

    def _world_to_render(self, world_x, world_y):
        """Converte coordenadas do mundo para coordenadas de renderização"""
        render_x = (world_x - self.camera.x) * self.camera.zoom + self.screen_manager.render_width / 2
        render_y = (world_y - self.camera.y) * self.camera.zoom + self.screen_manager.render_height / 2
        return (render_x, render_y)

    def _render_minimal_ui(self, screen):
        """UI mínima com instruções"""
        font_small = pygame.font.Font(None, 20)

        grid_status = "ON" if self.show_grid else "OFF"
        grid_color = (0, 255, 0) if self.show_grid else (255, 0, 0)

        # Instruções atualizadas para incluir o arrasto
        inst_text = f"F1:Debug | G:Grid [{grid_status}] | P:Pause | ESC:Menu | SPACE:Log | Scroll+Arrasto: Mover"
        inst = font_small.render(inst_text, True, (150, 150, 150))
        inst_x = self.screen_manager.viewport_x + (self.screen_manager.viewport_width - inst.get_width()) // 2
        screen.blit(inst, (inst_x, self.screen_manager.viewport_y + 10))

        # Mostra fase atual
        phase_text = font_small.render(f"Fase {self.phase_number}", True, (200, 200, 0))
        phase_x = self.screen_manager.viewport_x + 10
        phase_y = self.screen_manager.viewport_y + 10
        screen.blit(phase_text, (phase_x, phase_y))

        center_text = f"Centro: ({self.world_width/2:.0f}, {self.world_height/2:.0f})"
        center = font_small.render(center_text, True, (100, 100, 100))
        center_x = self.screen_manager.viewport_x + 10
        center_y = self.screen_manager.viewport_y + self.screen_manager.viewport_height - 20
        screen.blit(center, (center_x, center_y))

    def _render_pause_overlay(self, screen):
        """Overlay de pausa do jogo"""
        overlay = pygame.Surface((self.screen_manager.viewport_width,
                                 self.screen_manager.viewport_height))
        overlay.set_alpha(128)
        overlay.fill((0, 0, 0))
        screen.blit(overlay, (self.screen_manager.viewport_x, self.screen_manager.viewport_y))

        font_large = pygame.font.Font(None, 48)
        pause_text = font_large.render("PAUSADO", True, (255, 255, 255))
        text_x = self.screen_manager.viewport_x + (self.screen_manager.viewport_width - pause_text.get_width()) // 2
        text_y = self.screen_manager.viewport_y + (self.screen_manager.viewport_height - pause_text.get_height()) // 2
        screen.blit(pause_text, (text_x, text_y))

        # Mostra fase atual no pause
        font_small = pygame.font.Font(None, 24)
        phase_text = font_small.render(f"Fase {self.phase_number}", True, (200, 200, 200))
        phase_x = self.screen_manager.viewport_x + (self.screen_manager.viewport_width - phase_text.get_width()) // 2
        phase_y = text_y + pause_text.get_height() + 10
        screen.blit(phase_text, (phase_x, phase_y))

    def _render_debug_info(self, screen):
        """Informações de debug detalhadas"""
        mouse_pos = pygame.mouse.get_pos()
        in_viewport = self.screen_manager.is_mouse_in_viewport(mouse_pos)

        if in_viewport:
            world_pos = self.screen_manager.get_mouse_world_position(mouse_pos, self.camera)
            if world_pos:
                world_text = f"World: ({world_pos[0]:.0f}, {world_pos[1]:.0f})"
                grid_x = int(world_pos[0] // self.grid_size) * self.grid_size
                grid_y = int(world_pos[1] // self.grid_size) * self.grid_size
                grid_cell = f"Grid cell: ({grid_x}, {grid_y})"
            else:
                world_text = "World: invalid position"
                grid_cell = "Grid cell: N/A"
        else:
            world_text = "World: outside viewport"
            grid_cell = "Grid cell: outside"

        debug_lines = [
            "=== DEBUG INFO ===",
            f"FASE: {self.phase_number}",
            f"FPS: {self.screen_manager.get_fps():.1f}",
            f"Delta Time: {self.screen_manager.get_delta_time()*1000:.1f}ms",
            f"Grid: {'ON' if self.show_grid else 'OFF'} (tecla G)",
            f"Camera Drag: {'ACTIVE' if self.dragging_camera else 'inactive'}",
            "",
            "=== CAMERA ===",
            f"Position: ({self.camera.x:.0f}, {self.camera.y:.0f})",
            f"Zoom: {self.camera.zoom:.2f}",
            f"Visible: {self.screen_manager.render_width/self.camera.zoom:.0f} x {self.screen_manager.render_height/self.camera.zoom:.0f}",
            "",
            "=== SCREEN ===",
            f"Window: {self.screen_manager.window_width}x{self.screen_manager.window_height}",
            f"Viewport: {self.screen_manager.viewport_width}x{self.screen_manager.viewport_height}",
            f"Scale: {self.screen_manager.render_scale:.2f}",
            "",
            "=== MOUSE ===",
            f"Screen: ({mouse_pos[0]}, {mouse_pos[1]})",
            f"In Viewport: {in_viewport}",
            world_text,
            grid_cell,
            "",
            "=== WORLD ===",
            f"Size: {self.world_width}x{self.world_height}",
            f"Center: ({self.world_width/2:.0f}, {self.world_height/2:.0f})",
            f"Grid size: {self.grid_size}px"
        ]

        y_offset = self.screen_manager.viewport_y + 40
        x_offset = self.screen_manager.viewport_x + 10
        font_small = pygame.font.Font(None, 18)

        line_height = 16
        bg_height = len(debug_lines) * line_height + 10
        bg_width = 350  # Aumentei um pouco para acomodar a nova linha
        bg_surface = pygame.Surface((bg_width, bg_height))
        bg_surface.set_alpha(180)
        bg_surface.fill((0, 0, 0))
        screen.blit(bg_surface, (x_offset - 5, y_offset - 5))

        for line in debug_lines:
            if line.startswith("==="):
                color = (255, 255, 0)
                font_bold = pygame.font.Font(None, 20)
                text = font_bold.render(line, True, color)
            else:
                color = (0, 255, 0)
                text = font_small.render(line, True, color)

            screen.blit(text, (x_offset, y_offset))
            y_offset += line_height