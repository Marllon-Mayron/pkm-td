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

        # DEBUG: Verificar eventos de teclado
        if event.type == pygame.KEYDOWN:
            print(f"EventHandler recebeu tecla: {event.unicode}, active: {filters.search_active if filters else False}")

        # Processa eventos dos filtros PRIMEIRO (inclui teclado)
        if filters:
            filter_result = filters.handle_event(event)
            if filter_result:
                print(f"Filtro retornou: {filter_result}")  # Debug
                return filter_result

        # Processa outros eventos
        if event.type == pygame.KEYDOWN:
            return self._handle_keyboard(event)

        elif event.type == pygame.VIDEORESIZE:
            return self._handle_resize(event)

        elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            return self._handle_click(event, team_slots, grid_items, filters,
                                      back_button, start_button, prev_button, next_button,
                                      current_page, total_pages)

        elif event.type == pygame.MOUSEMOTION:
            self._handle_hover(event, team_slots, grid_items)

        return None

    def _handle_hover(self, event, team_slots, grid_items):
        """Processa eventos de mouse motion para efeitos de hover"""
        # Slots
        for slot in team_slots:
            slot.handle_event(event)

        # Grid items
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

    def _handle_click(self, event, team_slots, grid_items, filters,
                      back_button, start_button, prev_button, next_button,
                      current_page, total_pages):

        # Processa eventos dos filtros primeiro
        if filters:
            filter_result = filters.handle_event(event)
            if filter_result:
                return filter_result

        # Modal tem prioridade
        if self.modal and self.modal.visible:
            result = self.modal.handle_event(event)
            if result:
                return self._handle_modal_action(result)
            return None

        # Botões de navegação
        if back_button and back_button.collidepoint(event.pos):
            print("Clicou no botão VOLTAR")  # Debug
            return {'type': 'GO_BACK'}

        if start_button and start_button.collidepoint(event.pos):
            if len(self.game.player.team) > 0:
                print("Clicou no botão INICIAR")  # Debug
                return {'type': 'START_GAME'}

        if prev_button and prev_button.collidepoint(event.pos):
            if current_page > 0:
                print("Clicou no botão ANTERIOR")  # Debug
                return {'type': 'PREV_PAGE'}

        if next_button and next_button.collidepoint(event.pos):
            if current_page < total_pages - 1:
                print("Clicou no botão PRÓXIMA")  # Debug
                return {'type': 'NEXT_PAGE'}

        # Slots do time
        for slot in team_slots:
            # Primeiro passa o evento para atualizar hover
            slot.handle_event(event)
            # Depois verifica clique
            result = slot.handle_event(event)
            if result is not None:
                print(f"Clicou no slot {result}")  # Debug
                return {'type': 'SLOT_CLICK', 'slot': slot, 'slot_index': result}

        # Grid items
        for item in grid_items:
            # Primeiro passa o evento para atualizar hover
            item.handle_event(event)
            # Depois verifica clique
            result = item.handle_event(event)
            if result:
                print(f"Clicou no Pokémon: {result.name}")  # Debug
                return {'type': 'GRID_CLICK', 'pokemon': result}

        return None

    def _handle_modal_action(self, result):
        if result == "action":
            return {'type': 'MODAL_ACTION'}
        elif result == "close":
            return {'type': 'CLOSE_MODAL'}
        elif result == "release_confirm":  # NOVO
            return {'type': 'RELEASE_POKEMON'}
        return None

    def set_modal(self, modal):
        self.modal = modal