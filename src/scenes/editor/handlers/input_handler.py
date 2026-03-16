# src/scenes/editor/handlers/input_handler.py

import pygame
import time


class EditorInputHandler:
    """Gerencia a entrada do usuário no editor"""

    def __init__(self, editor_scene):
        self.editor = editor_scene
        self.dragging_camera = False
        self.last_mouse_pos = None

        # Controle de arrasto para pintura contínua
        self.painting = False  # Se está pintando (botão esquerdo pressionado)
        self.last_paint_pos = None  # Última posição pintada
        self.paint_cooldown = 0.05  # Cooldown entre pinturas (evita pintar no mesmo frame)
        self.last_paint_time = 0

    def handle_event(self, event):
        """Processa eventos do editor"""
        # PRIORIDADE 1: Eventos da UI (incluindo scroll)
        if self._handle_ui_events(event):
            return True

        # PRIORIDADE 2: Eventos do editor (incluindo zoom)
        return self._handle_editor_events(event)

    def _handle_ui_events(self, event):
        """Processa eventos dos painéis UI"""
        ui_handled = False

        # Processa tile palette primeiro (tem prioridade no scroll)
        if self.editor.tile_palette and self.editor.tile_palette.visible:
            if self.editor.tile_palette.handle_event(event):
                ui_handled = True
                if event.type == pygame.MOUSEWHEEL:
                    # Scroll na tile palette - NÃO PROPAGA para o zoom
                    return True
                if self.editor.tile_palette.selected_tile is not None:
                    self.editor.current_tile = self.editor.tile_palette.selected_tile + 1

        # Processa layer selector
        if self.editor.layer_selector and self.editor.layer_selector.handle_event(event):
            ui_handled = True
            self.editor.layer_manager.current_layer = self.editor.layer_selector.selected_layer
            current_layer = self.editor.layer_manager.get_current_layer()
            if current_layer and current_layer.tileset:
                self.editor.tile_palette.set_tileset(current_layer.tileset)

        return ui_handled

    def _handle_editor_events(self, event):
        """Processa eventos do editor"""
        if event.type == pygame.KEYDOWN:
            return self._handle_keydown(event)
        elif event.type == pygame.MOUSEBUTTONDOWN:
            return self._handle_mousedown(event)
        elif event.type == pygame.MOUSEBUTTONUP:
            return self._handle_mouseup(event)
        elif event.type == pygame.MOUSEMOTION:
            return self._handle_mousemotion(event)
        elif event.type == pygame.MOUSEWHEEL:
            return self._handle_mousewheel(event)
        return False

    def _handle_keydown(self, event):
        """Processa teclas pressionadas"""
        if event.key == pygame.K_p:
            self.editor.toggle_pause()
        elif event.key == pygame.K_ESCAPE:
            self.editor.game.current_scene = self.editor.game.menu_scene
        elif event.key == pygame.K_g:
            self.editor.show_grid = not self.editor.show_grid
        elif event.key == pygame.K_s and (pygame.key.get_mods() & pygame.KMOD_CTRL):
            self.editor.save_phase()
        elif event.key == pygame.K_i and (pygame.key.get_mods() & pygame.KMOD_CTRL):
            self.editor._import_tileset()
        elif event.key == pygame.K_1:
            self.editor.set_mode("layers")
        elif event.key == pygame.K_2:
            self.editor.set_mode("path")
        elif event.key == pygame.K_3:
            self.editor.set_mode("towers")
        elif event.key == pygame.K_z and (pygame.key.get_mods() & pygame.KMOD_CTRL):
            # Ctrl+Z = Undo
            if not (pygame.key.get_mods() & pygame.KMOD_SHIFT):  # Não é Ctrl+Shift+Z
                self.editor.undo_manager.undo(self.editor)
                return True
        elif event.key == pygame.K_y and (pygame.key.get_mods() & pygame.KMOD_CTRL):
            # Ctrl+Y = Redo
            self.editor.undo_manager.redo(self.editor)
            return True
        elif event.key == pygame.K_n and (pygame.key.get_mods() & pygame.KMOD_CTRL):
            # Ctrl+N = Novo path
            if self.editor.mode == "path":
                self.editor.path_manager.add_path()
                return True
        elif event.key == pygame.K_d and (pygame.key.get_mods() & pygame.KMOD_CTRL):
            # Ctrl+D = Deletar path atual
            if self.editor.mode == "path":
                self.editor.path_manager.remove_current_path()
                return True
        elif event.key == pygame.K_TAB:
            # TAB = Alternar entre paths (no modo path)
            if self.editor.mode == "path" and self.editor.path_manager.paths:
                current = self.editor.path_manager.current_path_index
                next_path = (current + 1) % len(self.editor.path_manager.paths)
                self.editor.path_manager.current_path_index = next_path
                print(f"Path atual: {next_path + 1}")
                return True

        elif event.key == pygame.K_w and (pygame.key.get_mods() & pygame.KMOD_CTRL):
            # Ctrl+W = Configurar waves (quando no modo path)
            if self.editor.mode == "path":
                self.editor._open_wave_config_dialog()
                return True
        return True

    def _handle_mousedown(self, event):
        """Processa clique do mouse"""
        mouse_pos = pygame.mouse.get_pos()

        # Verifica botões de modo
        for rect, text, mode in self.editor.mode_buttons.get_buttons():
            if rect.collidepoint(mouse_pos):
                if mode == "map_config":
                    self.editor._open_map_config_dialog()
                else:
                    self.editor.set_mode(mode)
                return True

        # Verifica se clicou no viewport com o botão do meio (scroll)
        if event.button == 2:  # Botão do meio/scroll
            if self.editor.screen_manager.is_mouse_in_viewport(mouse_pos):
                self.dragging_camera = True
                self.last_mouse_pos = mouse_pos
                pygame.mouse.set_cursor(pygame.SYSTEM_CURSOR_SIZEALL)
                return True

        # Inicia pintura contínua com botão esquerdo
        if event.button == 1 and self.editor.screen_manager.is_mouse_in_viewport(mouse_pos):
            self.painting = True
            self.last_paint_pos = None  # Força a pintar na primeira posição
            self.last_paint_time = 0

            # Processa o primeiro clique (NUNCA é contínuo)
            world_pos = self.editor.screen_manager.get_mouse_world_position(mouse_pos, self.editor.camera)
            if world_pos:
                self.editor._handle_left_click(world_pos, continuous=False)  # Primeiro clique salva undo
            return True

        # Clique direito no viewport
        if self.editor.screen_manager.is_mouse_in_viewport(mouse_pos):
            world_pos = self.editor.screen_manager.get_mouse_world_position(mouse_pos, self.editor.camera)
            if world_pos:
                # Arredonda para evitar problemas de float
                world_x, world_y = world_pos
                if event.button == 3:  # Clique direito
                    self.editor._handle_right_click((world_x, world_y))
        return True

    def _handle_mouseup(self, event):
        """Processa liberação do botão do mouse"""
        if event.button == 2:  # Botão do meio/scroll
            if self.dragging_camera:
                self.dragging_camera = False
                self.last_mouse_pos = None
                pygame.mouse.set_cursor(pygame.SYSTEM_CURSOR_ARROW)  # Volta cursor normal
                return True

        # Para a pintura contínua quando solta o botão
        elif event.button == 1:  # Botão esquerdo
            if self.painting:
                self.painting = False
                self.last_paint_pos = None
                return True

        return False

    def _handle_mousemotion(self, event):
        """Processa movimento do mouse"""
        # Pintura contínua durante o movimento com botão pressionado
        if self.painting and not self.dragging_camera:
            current_time = time.time()

            # Aplica cooldown para não pintar muito rápido
            if current_time - self.last_paint_time >= self.paint_cooldown:
                mouse_pos = pygame.mouse.get_pos()

                # Verifica se ainda está no viewport
                if self.editor.screen_manager.is_mouse_in_viewport(mouse_pos):
                    world_pos = self.editor.screen_manager.get_mouse_world_position(mouse_pos, self.editor.camera)

                    if world_pos:
                        # Converte para coordenadas de tile
                        tile_x = int(world_pos[0] // self.editor.grid_size)
                        tile_y = int(world_pos[1] // self.editor.grid_size)
                        current_tile_pos = (tile_x, tile_y)

                        # Verifica se mudou de tile desde a última pintura
                        if current_tile_pos != self.last_paint_pos:
                            # Processa o clique esquerdo na posição atual (contínuo)
                            self.editor._handle_left_click(world_pos, continuous=True)
                            self.last_paint_pos = current_tile_pos
                            self.last_paint_time = current_time
                return True

        # Arrasto da câmera (existente)
        if self.dragging_camera and self.last_mouse_pos:
            # Calcula a diferença do movimento
            dx = event.pos[0] - self.last_mouse_pos[0]
            dy = event.pos[1] - self.last_mouse_pos[1]

            # Converte para movimento no mundo (considerando zoom)
            world_dx = dx / self.editor.camera.zoom
            world_dy = dy / self.editor.camera.zoom

            # Move a câmera na direção OPOSTA ao arrasto
            self.editor.camera.x -= world_dx
            self.editor.camera.y -= world_dy

            # Garante que a câmera respeita os limites
            self.editor.camera._clamp_position()

            self.last_mouse_pos = event.pos
            return True
        return False

    def _handle_mousewheel(self, event):
        """Processa scroll do mouse (zoom)"""
        # SÓ FAZ ZOOM SE O MOUSE NÃO ESTIVER SOBRE A TILE PALETTE
        mouse_pos = pygame.mouse.get_pos()

        # Verifica se o mouse está sobre a tile palette
        if self.editor.tile_palette and self.editor.tile_palette.visible:
            if self.editor.tile_palette.rect.collidepoint(mouse_pos):
                # Mouse está na tile palette - NÃO FAZ ZOOM
                return True

        # Verifica se o mouse está sobre o layer selector
        if self.editor.layer_selector and self.editor.layer_selector.visible:
            if self.editor.layer_selector.rect.collidepoint(mouse_pos):
                # Mouse está no layer selector - NÃO FAZ ZOOM
                return True

        if not self.editor.paused and not self.dragging_camera:
            # Verifica se o mouse está sobre o viewport
            if self.editor.screen_manager.is_mouse_in_viewport(mouse_pos):
                # Pega posição do mundo antes do zoom
                world_pos = self.editor.screen_manager.get_mouse_world_position(mouse_pos, self.editor.camera)

                if world_pos:
                    # Guarda a posição do mundo que queremos manter sob o mouse
                    target_world_x, target_world_y = world_pos

                    # Aplica zoom
                    self.editor.camera.handle_zoom(event.y > 0)

                    # Após o zoom, recalcula onde esse ponto do mundo está na tela
                    new_mouse_pos = pygame.mouse.get_pos()
                    new_world_pos = self.editor.screen_manager.get_mouse_world_position(new_mouse_pos,
                                                                                        self.editor.camera)

                    if new_world_pos:
                        # Calcula a diferença e ajusta a câmera
                        dx = target_world_x - new_world_pos[0]
                        dy = target_world_y - new_world_pos[1]

                        self.editor.camera.x += dx
                        self.editor.camera.y += dy

                        # Garante que está dentro dos limites
                        self.editor.camera._clamp_position()
        return True