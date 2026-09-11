# src/scenes/team_select_scene/handlers/event_handler.py

import pygame


class EventHandler:
    def __init__(self, game, pokemon_manager, layout_manager):
        self.game = game
        self.pokemon_manager = pokemon_manager
        self.layout_manager = layout_manager
        self.modal = None

    def handle_event(self, event, team_slots, grid_items, filters,
                     back_button, start_button, prev_button, next_button,
                     current_page, total_pages):

        # =================================================================
        # MODAL ABERTO -> PRIORIDADE ABSOLUTA
        # =================================================================
        if self.modal and self.modal.visible:
            forwarded_types = (
                pygame.MOUSEMOTION,
                pygame.MOUSEWHEEL,
                pygame.MOUSEBUTTONDOWN,
                pygame.MOUSEBUTTONUP,
                pygame.KEYDOWN,
                pygame.KEYUP,
            )
            if event.type in forwarded_types:
                result = self.modal.handle_event(event)
                if result:
                    return self._handle_modal_action(result)
                # Consome o evento para não vazar para grid/filtros
                return None
            # Outros eventos (VIDEORESIZE) seguem normalmente
            if event.type == pygame.VIDEORESIZE:
                return self._handle_resize(event)
            return None

        # =================================================================
        # SEM MODAL -> FLUXO NORMAL
        # =================================================================
        if filters:
            filter_result = filters.handle_event(event)
            if filter_result:
                return filter_result

        if event.type == pygame.KEYDOWN:
            return self._handle_keyboard(event)
        elif event.type == pygame.VIDEORESIZE:
            return self._handle_resize(event)
        elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            return self._handle_click(event, team_slots, grid_items,
                                      back_button, start_button,
                                      prev_button, next_button,
                                      current_page, total_pages)
        elif event.type == pygame.MOUSEMOTION:
            self._handle_hover(event, team_slots, grid_items)

        return None

    def _handle_hover(self, event, team_slots, grid_items):
        for slot in team_slots:
            slot.handle_event(event)
        for item in grid_items:
            item.handle_event(event)

    def _handle_keyboard(self, event):
        if event.key == pygame.K_ESCAPE:
            if self.modal:
                self.modal.visible = False
                self.modal = None
                return {'type': 'CLOSE_MODAL'}
            else:
                return {'type': 'GO_BACK'}
        return None

    def _handle_resize(self, event):
        if self.modal:
            self.layout_manager.update_modal_position(self.modal)
        return {'type': 'RESIZE'}

    def _handle_click(self, event, team_slots, grid_items,
                      back_button, start_button, prev_button, next_button,
                      current_page, total_pages):
        # Modal já foi tratado em handle_event; aqui só chega com modal fechado
        if self.modal and self.modal.visible:
            return None

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

        for slot in team_slots:
            result = slot.handle_event(event)
            if result is not None:
                return {'type': 'SLOT_CLICK', 'slot': slot, 'slot_index': result}

        for item in grid_items:
            result = item.handle_event(event)
            if result:
                return {'type': 'GRID_CLICK', 'pokemon': result}

        return None

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