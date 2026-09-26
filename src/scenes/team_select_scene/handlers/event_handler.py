# src/scenes/team_select_scene/handlers/event_handler.py

import pygame
from src.scenes.team_select_scene.managers.drag_drop_manager import DragDropManager


class EventHandler:
    def __init__(self, game, pokemon_manager, layout_manager):
        self.game = game
        self.pokemon_manager = pokemon_manager
        self.layout_manager = layout_manager
        self.modal = None
        self.drag_drop = DragDropManager(game, pokemon_manager)

        # Estado de clique pendente (down registra, up decide)
        self._pending_click_hit = None

    def handle_event(self, event, team_slots, grid_items, filters,
                     back_button, start_button, prev_button, next_button,
                     current_page, total_pages):

        # =================================================================
        # MODAL ABERTO -> prioridade absoluta
        # =================================================================
        if self.modal and self.modal.visible:
            forwarded_types = (
                pygame.MOUSEMOTION, pygame.MOUSEWHEEL,
                pygame.MOUSEBUTTONDOWN, pygame.MOUSEBUTTONUP,
                pygame.KEYDOWN, pygame.KEYUP,
            )
            if event.type in forwarded_types:
                result = self.modal.handle_event(event)
                if result:
                    return self._handle_modal_action(result)
                return None
            if event.type == pygame.VIDEORESIZE:
                return self._handle_resize(event)
            return None

        # =================================================================
        # SEM MODAL
        # =================================================================
        # Filtros primeiro (dropdowns podem consumir cliques)
        if filters:
            filter_result = filters.handle_event(event)
            if filter_result:
                return filter_result

        # ===== DRAG & DROP: sempre atualiza targets antes =====
        self.drag_drop.set_targets(team_slots, grid_items)

        # ---------------------------------------------------------------
        # 1) JÁ ESTÁ ARRASTANDO -> drag tem prioridade total
        # ---------------------------------------------------------------
        if self.drag_drop.is_dragging:
            if event.type == pygame.MOUSEMOTION:
                self.drag_drop.handle_event(event)
                return None
            if event.type == pygame.MOUSEBUTTONUP and event.button == 1:
                self.drag_drop.handle_event(event)
                self._pending_click_hit = None
                return None
            # Ignora outros eventos enquanto arrasta
            return None

        # ---------------------------------------------------------------
        # 2) DOWN -> registra pending no drag_drop E no event_handler
        # ---------------------------------------------------------------
        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            # Botões primeiro
            if back_button and back_button.collidepoint(event.pos):
                return {'type': 'GO_BACK'}
            if start_button and start_button.collidepoint(event.pos):
                if len(self.game.player.team) > 0:
                    return {'type': 'START_GAME'}
            if prev_button and prev_button.collidepoint(event.pos):
                if current_page > 0:
                    return {'type': 'PREV_PAGE'}
            if next_button and next_button.collidepoint(event.pos):
                if current_page < total_pages - 1:
                    return {'type': 'NEXT_PAGE'}

            # Drag drop registra intenção
            consumed = self.drag_drop.handle_event(event)

            # Registra o hit para decidir no UP
            hit = self.drag_drop._hit_test(event.pos)
            if hit:
                self._pending_click_hit = hit
            return None

        # ---------------------------------------------------------------
        # 3) MOTION -> atualiza hover; se pending_drag, avalia threshold
        # ---------------------------------------------------------------
        if event.type == pygame.MOUSEMOTION:
            # Se pending_drag, deixa o drag_drop avaliar se vira drag
            if self.drag_drop._pending_drag:
                self.drag_drop.handle_event(event)
                # Virou drag? Consome e sai
                if self.drag_drop.is_dragging:
                    return None

            # Hover normal
            for slot in team_slots:
                slot.handle_event(event)
            for item in grid_items:
                item.handle_event(event)
            return None

        # ---------------------------------------------------------------
        # 4) UP -> se não virou drag, é clique simples (abre modal)
        # ---------------------------------------------------------------
        if event.type == pygame.MOUSEBUTTONUP and event.button == 1:
            # Sem drag ativo: checa clique simples
            if self._pending_click_hit is not None:
                hit = self._pending_click_hit
                self._pending_click_hit = None
                self.drag_drop._reset()

                kind, index, data = hit
                if kind == 'team':
                    slot = team_slots[index]
                    return {'type': 'SLOT_CLICK', 'slot': slot,
                            'slot_index': slot.slot_index}
                elif kind == 'box':
                    return {'type': 'GRID_CLICK', 'pokemon': data}

            # Se não houve hit, limpa o drag_drop e retorna
            self.drag_drop._reset()
            return None

        # ---------------------------------------------------------------
        # 5) TECLADO / RESIZE
        # ---------------------------------------------------------------
        if event.type == pygame.KEYDOWN:
            return self._handle_keyboard(event)
        if event.type == pygame.VIDEORESIZE:
            return self._handle_resize(event)

        return None

    def _handle_keyboard(self, event):
        if event.key == pygame.K_ESCAPE:
            if self.modal:
                self.modal.visible = False
                self.modal = None
                return {'type': 'CLOSE_MODAL'}
            return {'type': 'GO_BACK'}
        return None

    def _handle_resize(self, event):
        if self.modal:
            self.layout_manager.update_modal_position(self.modal)
        return {'type': 'RESIZE'}

    def _handle_modal_action(self, result):
        if result == "action":
            return {'type': 'MODAL_ACTION'}
        elif result == "close":
            return {'type': 'CLOSE_MODAL'}
        elif result == "release_confirm":
            return {'type': 'RELEASE_POKEMON'}
        return None

    def set_modal(self, modal):
        self.modal = modal