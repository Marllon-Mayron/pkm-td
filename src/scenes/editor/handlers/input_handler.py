# src/scenes/editor/handlers/input_handler.py

import pygame


class EditorInputHandler:
    """Gerencia a entrada do usuário no editor"""

    def __init__(self, editor_scene):
        self.editor = editor_scene
        self.dragging_camera = False
        self.last_mouse_pos = None

    def handle_event(self, event):
        """Processa eventos do editor"""
        # Verifica se há um diálogo de configuração ativo
        if self.editor.map_config_dialog and self.editor.map_config_dialog.visible:
            result = self.editor.map_config_dialog.handle_event(event)
            if result:  # Diálogo foi confirmado
                self.editor._handle_map_config_result(result)
            elif not self.editor.map_config_dialog.visible:  # Diálogo foi cancelado
                self.editor.map_config_dialog = None
            return True

        if self._handle_ui_events(event):
            return True

        return self._handle_editor_events(event)

    def _handle_ui_events(self, event):
        """Processa eventos dos painéis UI"""
        ui_handled = False

        if self.editor.mode == "layers":
            if self.editor.tile_palette and self.editor.tile_palette.handle_event(event):
                ui_handled = True
                if self.editor.tile_palette.selected_tile is not None:
                    self.editor.current_tile = self.editor.tile_palette.selected_tile + 1

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
        elif event.key == pygame.K_4:
            self.editor.set_mode("preview")
        elif event.key in (pygame.K_EQUALS, pygame.K_PLUS):
            if not (pygame.key.get_mods() & pygame.KMOD_CTRL):
                self.editor.preview_speed = min(3.0, self.editor.preview_speed + 0.2)
        elif event.key == pygame.K_MINUS:
            if not (pygame.key.get_mods() & pygame.KMOD_CTRL):
                self.editor.preview_speed = max(0.2, self.editor.preview_speed - 0.2)
        elif event.key == pygame.K_DELETE:
            self.editor._delete_selected()
        elif event.key == pygame.K_o and (pygame.key.get_mods() & pygame.KMOD_CTRL):
            self.editor._open_phase_loader()
        elif event.key == pygame.K_l and (pygame.key.get_mods() & pygame.KMOD_CTRL):
            self.editor.list_available_phases()
        elif event.key == pygame.K_m and (pygame.key.get_mods() & pygame.KMOD_CTRL):
            self.editor._open_map_config_dialog()
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
                pygame.mouse.set_cursor(pygame.SYSTEM_CURSOR_SIZEALL)  # Muda cursor para movimento
                return True

        # Se não clicou em botão e está no viewport, processa ações de edição
        if self.editor.mode != "preview" and self.editor.screen_manager.is_mouse_in_viewport(mouse_pos):
            world_pos = self.editor.screen_manager.get_mouse_world_position(mouse_pos, self.editor.camera)
            if world_pos:
                if event.button == 1:  # Clique esquerdo
                    self.editor._handle_left_click(world_pos)
                elif event.button == 3:  # Clique direito
                    self.editor._handle_right_click(world_pos)
        return True

    def _handle_mouseup(self, event):
        """Processa liberação do botão do mouse"""
        if event.button == 2:  # Botão do meio/scroll
            if self.dragging_camera:
                self.dragging_camera = False
                self.last_mouse_pos = None
                pygame.mouse.set_cursor(pygame.SYSTEM_CURSOR_ARROW)  # Volta cursor normal
                return True
        return False

    def _handle_mousemotion(self, event):
        """Processa movimento do mouse"""
        if self.dragging_camera and self.last_mouse_pos:
            # Calcula a diferença do movimento
            dx = event.pos[0] - self.last_mouse_pos[0]
            dy = event.pos[1] - self.last_mouse_pos[1]

            # Converte para movimento no mundo (considerando zoom)
            # Na sua câmera, o movimento é inversamente proporcional ao zoom
            world_dx = dx / self.editor.camera.zoom
            world_dy = dy / self.editor.camera.zoom

            # Move a câmera na direção OPOSTA ao arrasto
            # (arrastar para direita = mundo move para esquerda)
            self.editor.camera.x -= world_dx
            self.editor.camera.y -= world_dy

            # Garante que a câmera respeita os limites (usa o método existente)
            self.editor.camera._clamp_position()

            self.last_mouse_pos = event.pos
            return True
        return False

    def _handle_mousewheel(self, event):
        """Processa scroll do mouse (zoom)"""
        if not self.editor.paused:
            # Só faz zoom se não estiver arrastando a câmera
            if not self.dragging_camera:
                # Verifica se o mouse está sobre o viewport
                mouse_pos = pygame.mouse.get_pos()
                if self.editor.screen_manager.is_mouse_in_viewport(mouse_pos):
                    # Pega posição do mundo antes do zoom
                    world_pos = self.editor.screen_manager.get_mouse_world_position(mouse_pos, self.editor.camera)

                    if world_pos:
                        # Guarda a posição do mundo que queremos manter sob o mouse
                        target_world_x, target_world_y = world_pos

                        # Aplica zoom
                        self.editor.camera.handle_zoom(event.y > 0)

                        # Após o zoom, recalcula onde esse ponto do mundo está na tela
                        # e ajusta a câmera para mantê-lo na mesma posição de tela
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