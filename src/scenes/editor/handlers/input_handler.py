# src/scenes/editor/handlers/input_handler.py

import pygame
import time


class EditorInputHandler:
    """Gerencia a entrada do usuário no editor."""

    def __init__(self, editor_scene):
        self.editor = editor_scene
        self.dragging_camera = False
        self.last_mouse_pos = None

        # Pintura contínua
        self.painting = False
        self.erasing = False
        self.eraser_dragging = False

        self.last_paint_pos = None
        self.last_erase_pos = None
        self.last_eraser_pos = None

        self.paint_cooldown = 0.05
        self.last_paint_time = 0
        self.last_erase_time = 0
        self.last_eraser_time = 0

    # ==================================================================
    # ENTRY POINT
    # ==================================================================
    def handle_event(self, event):
        # ===== MOUSEWHEEL — prioridade MÁXIMA no viewport =====
        # Trata antes de qualquer UI para garantir que scroll/zoom funcione
        # mesmo com estrutura carregada, preview ativo, etc.
        if event.type == pygame.MOUSEWHEEL:
            if self._handle_mousewheel(event):
                return True

        if self._handle_ui_events(event):
            return True
        return self._handle_editor_events(event)

    # ==================================================================
    # UI
    # ==================================================================
    def _handle_ui_events(self, event):
        ui_handled = False

        # ===== TILE PALETTE =====
        if self.editor.tile_palette and self.editor.tile_palette.visible:
            if self.editor.tile_palette.handle_event(event):
                ui_handled = True
                if self.editor.tile_palette.selected_tile is not None:
                    self.editor.current_tile = self.editor.tile_palette.selected_tile + 1

            if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                if self._handle_tile_selector_buttons(pygame.mouse.get_pos()):
                    ui_handled = True

        # ===== LAYER SELECTOR =====
        if self.editor.layer_selector and self.editor.layer_selector.handle_event(event):
            ui_handled = True

            pending = self.editor.layer_selector.pending_action
            if pending:
                self.editor.layer_selector.pending_action = None
                action = pending['action']

                if action == 'add':
                    self.editor._add_layer_of_type(pending['type'])
                elif action == 'remove':
                    self.editor._remove_layer_at(pending['index'])
                elif action == 'toggle_visibility':
                    idx = pending['index']
                    if 0 <= idx < len(self.editor.layer_manager.layers):
                        layer = self.editor.layer_manager.layers[idx]
                        layer.visible = not layer.visible
                        state = "visível" if layer.visible else "oculta"
                        print(f"[EDITOR] Camada {idx} ('{layer.name}') {state}")

            self.editor.layer_manager.current_layer = self.editor.layer_selector.selected_layer

            current_layer = self.editor.layer_manager.get_current_layer()
            if current_layer and current_layer.tileset:
                all_tiles, boundaries = current_layer.get_all_tiles_with_boundaries()
                natural_cols = None
                if current_layer.tilesets:
                    natural_cols = current_layer.tilesets[0].get('cols', 6)
                self.editor.tile_palette.set_tileset(all_tiles, boundaries, natural_cols=natural_cols)

        return ui_handled

    # ==================================================================
    # EDITOR
    # ==================================================================
    def _handle_editor_events(self, event):
        if event.type == pygame.KEYDOWN:
            return self._handle_keydown(event)
        elif event.type == pygame.MOUSEBUTTONDOWN:
            return self._handle_mousedown(event)
        elif event.type == pygame.MOUSEBUTTONUP:
            return self._handle_mouseup(event)
        elif event.type == pygame.MOUSEMOTION:
            return self._handle_mousemotion(event)
        return False

    # ==================================================================
    # KEYDOWN
    # ==================================================================
    def _handle_keydown(self, event):
        if event.key == pygame.K_p:
            self.editor.toggle_pause()
        elif event.key == pygame.K_ESCAPE:
            if self.editor.map_handler.shape_active:
                self.editor.map_handler.cancel_shape()
                return True
            if getattr(self.editor, 'loaded_structure', None) is not None:
                self.editor.clear_loaded_structure()
                return True
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
            if not (pygame.key.get_mods() & pygame.KMOD_SHIFT):
                self.editor.undo_manager.undo(self.editor)
                return True
        elif event.key == pygame.K_y and (pygame.key.get_mods() & pygame.KMOD_CTRL):
            self.editor.undo_manager.redo(self.editor)
            return True
        elif event.key == pygame.K_n and (pygame.key.get_mods() & pygame.KMOD_CTRL):
            if self.editor.mode == "path":
                self.editor.path_manager.add_path()
                return True
        elif event.key == pygame.K_d and (pygame.key.get_mods() & pygame.KMOD_CTRL):
            if self.editor.mode == "path":
                self.editor.path_manager.remove_current_path()
                return True
        elif event.key == pygame.K_TAB:
            if self.editor.mode == "path" and self.editor.path_manager.paths:
                current = self.editor.path_manager.current_path_index
                self.editor.path_manager.current_path_index = (current + 1) % len(self.editor.path_manager.paths)
                return True
        elif event.key == pygame.K_l and (pygame.key.get_mods() & pygame.KMOD_CTRL):
            self.editor._open_load_phase_dialog()
        elif event.key == pygame.K_w and (pygame.key.get_mods() & pygame.KMOD_CTRL):
            if self.editor.mode == "path":
                self.editor._open_wave_config_dialog()
                return True
        return True

    # ==================================================================
    # MOUSEDOWN
    # ==================================================================
    def _handle_mousedown(self, event):
        mouse_pos = pygame.mouse.get_pos()

        # Botões de modo
        for rect, text, mode in self.editor.mode_buttons.get_buttons():
            if rect.collidepoint(mouse_pos):
                if mode == "map_config":
                    self.editor._open_map_config_dialog()
                else:
                    self.editor.set_mode(mode)
                return True

        # Botão do meio → arrastar câmera
        if event.button == 2:
            if self.editor.screen_manager.is_mouse_in_viewport(mouse_pos):
                self.dragging_camera = True
                self.last_mouse_pos = mouse_pos
                pygame.mouse.set_cursor(pygame.SYSTEM_CURSOR_SIZEALL)
                return True

        # ===== BOTÃO ESQUERDO =====
        if event.button == 1 and self.editor.screen_manager.is_mouse_in_viewport(mouse_pos):
            brush = self.editor.brush_buttons.get_current_brush()

            # ---- BORRACHA ----
            if brush == self.editor.brush_buttons.BRUSH_ERASER:
                self.eraser_dragging = True
                self.last_eraser_pos = None
                self.last_eraser_time = 0
                world_pos = self.editor.screen_manager.get_mouse_world_position(
                    mouse_pos, self.editor.camera
                )
                if world_pos:
                    self.editor.map_handler.handle_erase(world_pos, continuous=False)
                return True

            # ---- SHAPE TOOLS ----
            if brush in (self.editor.brush_buttons.BRUSH_LINE,
                         self.editor.brush_buttons.BRUSH_CIRCLE):
                world_pos = self.editor.screen_manager.get_mouse_world_position(
                    mouse_pos, self.editor.camera
                )
                if world_pos:
                    tx = int(world_pos[0] // self.editor.grid_size)
                    ty = int(world_pos[1] // self.editor.grid_size)
                    self.editor.map_handler.start_shape(tx, ty)
                return True

            # ---- PINTURA NORMAL ----
            self.painting = True
            self.erasing = False
            self.last_paint_pos = None
            self.last_paint_time = 0

            world_pos = self.editor.screen_manager.get_mouse_world_position(
                mouse_pos, self.editor.camera
            )
            if world_pos:
                self.editor._handle_left_click(world_pos, continuous=False)
            return True

        # ===== BOTÃO DIREITO =====
        if event.button == 3 and self.editor.screen_manager.is_mouse_in_viewport(mouse_pos):
            brush = self.editor.brush_buttons.get_current_brush()

            if brush == self.editor.brush_buttons.BRUSH_ERASER:
                self.eraser_dragging = True
                self.last_eraser_pos = None
                self.last_eraser_time = 0
                world_pos = self.editor.screen_manager.get_mouse_world_position(
                    mouse_pos, self.editor.camera
                )
                if world_pos:
                    self.editor.map_handler.handle_erase(world_pos, continuous=False)
                return True

            self.erasing = True
            self.painting = False
            self.last_erase_pos = None
            self.last_erase_time = 0
            world_pos = self.editor.screen_manager.get_mouse_world_position(
                mouse_pos, self.editor.camera
            )
            if world_pos:
                self.editor._handle_right_click(world_pos)
            return True

        return True

    # ==================================================================
    # MOUSEUP
    # ==================================================================
    def _handle_mouseup(self, event):
        if event.button == 2:
            if self.dragging_camera:
                self.dragging_camera = False
                self.last_mouse_pos = None
                pygame.mouse.set_cursor(pygame.SYSTEM_CURSOR_ARROW)
                return True

        elif event.button == 1:
            if self.editor.map_handler.shape_active:
                self.editor.map_handler.commit_shape()
                return True
            if self.eraser_dragging:
                self.eraser_dragging = False
                self.last_eraser_pos = None
                return True
            if self.painting:
                self.painting = False
                self.last_paint_pos = None
                return True

        elif event.button == 3:
            if self.eraser_dragging:
                self.eraser_dragging = False
                self.last_eraser_pos = None
                return True
            if self.erasing:
                self.erasing = False
                self.last_erase_pos = None
                return True

        return False

    # ==================================================================
    # MOUSEMOTION
    # ==================================================================
    def _handle_mousemotion(self, event):
        if self.editor.map_handler.shape_active:
            mouse_pos = pygame.mouse.get_pos()
            if self.editor.screen_manager.is_mouse_in_viewport(mouse_pos):
                world_pos = self.editor.screen_manager.get_mouse_world_position(
                    mouse_pos, self.editor.camera
                )
                if world_pos:
                    tx = int(world_pos[0] // self.editor.grid_size)
                    ty = int(world_pos[1] // self.editor.grid_size)
                    self.editor.map_handler.update_shape(tx, ty)
            return True

        if self.eraser_dragging and not self.dragging_camera:
            current_time = time.time()
            if current_time - self.last_eraser_time >= self.paint_cooldown:
                mouse_pos = pygame.mouse.get_pos()
                if self.editor.screen_manager.is_mouse_in_viewport(mouse_pos):
                    world_pos = self.editor.screen_manager.get_mouse_world_position(
                        mouse_pos, self.editor.camera
                    )
                    if world_pos:
                        tx = int(world_pos[0] // self.editor.grid_size)
                        ty = int(world_pos[1] // self.editor.grid_size)
                        current_tile_pos = (tx, ty)
                        if current_tile_pos != self.last_eraser_pos:
                            self.editor.map_handler.handle_erase(world_pos, continuous=True)
                            self.last_eraser_pos = current_tile_pos
                            self.last_eraser_time = current_time
                return True

        if self.painting and not self.dragging_camera:
            current_time = time.time()
            if current_time - self.last_paint_time >= self.paint_cooldown:
                mouse_pos = pygame.mouse.get_pos()
                if self.editor.screen_manager.is_mouse_in_viewport(mouse_pos):
                    world_pos = self.editor.screen_manager.get_mouse_world_position(
                        mouse_pos, self.editor.camera
                    )
                    if world_pos:
                        tx = int(world_pos[0] // self.editor.grid_size)
                        ty = int(world_pos[1] // self.editor.grid_size)
                        current_tile_pos = (tx, ty)
                        if current_tile_pos != self.last_paint_pos:
                            self.editor._handle_left_click(world_pos, continuous=True)
                            self.last_paint_pos = current_tile_pos
                            self.last_paint_time = current_time
                return True

        if self.erasing and not self.dragging_camera:
            current_time = time.time()
            if current_time - self.last_erase_time >= self.paint_cooldown:
                mouse_pos = pygame.mouse.get_pos()
                if self.editor.screen_manager.is_mouse_in_viewport(mouse_pos):
                    world_pos = self.editor.screen_manager.get_mouse_world_position(
                        mouse_pos, self.editor.camera
                    )
                    if world_pos:
                        tx = int(world_pos[0] // self.editor.grid_size)
                        ty = int(world_pos[1] // self.editor.grid_size)
                        current_tile_pos = (tx, ty)
                        if current_tile_pos != self.last_erase_pos:
                            self.editor._handle_right_click(world_pos)
                            self.last_erase_pos = current_tile_pos
                            self.last_erase_time = current_time
                return True

        if self.dragging_camera and self.last_mouse_pos:
            dx = event.pos[0] - self.last_mouse_pos[0]
            dy = event.pos[1] - self.last_mouse_pos[1]
            world_dx = dx / self.editor.camera.zoom
            world_dy = dy / self.editor.camera.zoom
            self.editor.camera.x -= world_dx
            self.editor.camera.y -= world_dy
            self.editor.camera._clamp_position()
            self.last_mouse_pos = event.pos
            return True
        return False

    # ==================================================================
    # MOUSEWHEEL (agora no TOPO do handle_event)
    # ==================================================================
    def _handle_mousewheel(self, event):
        """
        Retorna True SEMPRE (consome o evento).
        Faz zoom no viewport de forma robusta (sem depender de is_mouse_in_viewport).
        """
        mouse_pos = pygame.mouse.get_pos()
        mx, my = mouse_pos

        # ===== 1) Ignora se está sobre UIs com scroll próprio =====
        if self.editor.tile_palette and self.editor.tile_palette.visible:
            if self.editor.tile_palette.rect.collidepoint(mouse_pos):
                return False  # deixa a palette processar

        if self.editor.layer_selector and self.editor.layer_selector.visible:
            if self.editor.layer_selector.rect.collidepoint(mouse_pos):
                return False  # deixa o layer selector processar

        if self.editor.brush_buttons and self.editor.brush_buttons.rect.collidepoint(mouse_pos):
            return True  # consome para não dar zoom acidental

        # ===== 2) Verifica viewport de forma inline (robusta) =====
        sm = self.editor.screen_manager
        vx, vy = sm.viewport_x, sm.viewport_y
        vw, vh = sm.viewport_width, sm.viewport_height

        inside = (vx <= mx < vx + vw) and (vy <= my < vy + vh)

        if not inside:
            return True  # consome fora do viewport (menus etc.)

        if self.editor.paused:
            return True

        if self.dragging_camera:
            return True

        # ===== 3) Zoom centrado no cursor =====
        world_pos = sm.get_mouse_world_position(mouse_pos, self.editor.camera)
        if world_pos is None:
            return True

        target_world_x, target_world_y = world_pos

        # Aplica zoom
        self.editor.camera.handle_zoom(event.y > 0)

        # Recalcula posição do mundo sob o mouse após o zoom
        new_world_pos = sm.get_mouse_world_position(
            pygame.mouse.get_pos(), self.editor.camera
        )
        if new_world_pos is not None:
            dx = target_world_x - new_world_pos[0]
            dy = target_world_y - new_world_pos[1]
            self.editor.camera.x += dx
            self.editor.camera.y += dy
            try:
                self.editor.camera._clamp_position()
            except Exception:
                pass

        return True

    # ==================================================================
    # TILE SELECTOR BUTTONS
    # ==================================================================
    def _handle_tile_selector_buttons(self, mouse_pos):
        if self.editor.tile_palette and self.editor.tile_palette.visible:
            if self.editor.tile_palette.handle_current_tile_buttons(mouse_pos):
                self.editor.current_tile = self.editor.tile_palette.selected_tile + 1
                return True
        return False