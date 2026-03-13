import pygame


class EditorInputHandler:
    """Gerencia a entrada do usuário no editor"""

    def __init__(self, editor_scene):
        self.editor = editor_scene

    def handle_event(self, event):
        """Processa eventos do editor"""
        # Primeiro, processa o diálogo de tamanho do mapa se estiver ativo
        if self.editor.map_size_dialog and self.editor.map_size_dialog.visible:
            result = self.editor.map_size_dialog.handle_event(event)
            if result:
                new_width, new_height = result
                self.editor.map_handler.resize_map(new_width, new_height)
            return True

        # Deixa os painéis da UI processarem o evento
        if self._handle_ui_events(event):
            return True

        # Processa outros eventos
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
            self.editor._open_map_size_dialog()
        return True

    def _handle_mousedown(self, event):
        """Processa clique do mouse"""
        mouse_pos = pygame.mouse.get_pos()

        # Verifica botões de modo - CORRIGIDO: usa get_buttons()
        for rect, text, mode in self.editor.mode_buttons.get_buttons():
            if rect.collidepoint(mouse_pos):
                if mode == "map_size":
                    self.editor._open_map_size_dialog()
                else:
                    self.editor.set_mode(mode)
                return True

        # Se não clicou em botão e está no viewport, processa ações de edição
        if self.editor.mode != "preview" and self.editor.screen_manager.is_mouse_in_viewport(mouse_pos):
            world_pos = self.editor.screen_manager.get_mouse_world_position(mouse_pos, self.editor.camera)
            if world_pos:
                if event.button == 1:
                    self.editor._handle_left_click(world_pos)
                elif event.button == 3:
                    self.editor._handle_right_click(world_pos)
        return True

    def _handle_mousewheel(self, event):
        """Processa scroll do mouse"""
        if not self.editor.paused:
            if not (self.editor.tile_palette and self.editor.tile_palette.focused):
                self.editor.camera.handle_zoom(event.y > 0)
        return True