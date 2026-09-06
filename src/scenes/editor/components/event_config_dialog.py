# src/scenes/editor/components/event_config_dialog.py

import pygame
from src.editor.event_system import TriggerType, WaveTriggerState, EventType, CameraEffect, GameEvent, TutorialAction, GameStateAction, SpawnAction

class EventConfigDialog:
    """Diálogo para configurar gatilhos e eventos de uma fase."""

    COLORS = {
        'bg': (40, 40, 50),
        'bg_light': (50, 50, 60),
        'bg_dark': (30, 30, 40),
        'border': (255, 215, 0),
        'border_light': (80, 80, 90),
        'text': (255, 255, 255),
        'text_dim': (200, 200, 200),
        'text_dark': (150, 150, 150),
        'accent': (80, 100, 120),
        'accent_hover': (100, 120, 140),
        'input_bg': (50, 50, 60),
        'input_border': (80, 80, 90),
        'input_active': (100, 150, 255),
        'success': (0, 120, 0),
        'danger': (120, 0, 0),
        'warning': (120, 120, 0),
    }

    def __init__(self, x, y, width, height, event_manager, wave_manager):
        self.rect = pygame.Rect(x, y, width, height)
        self.visible = True
        self.event_manager = event_manager
        self.wave_manager = wave_manager

        # Estado da UI
        self.dragging = False
        self.drag_offset_x = 0
        self.drag_offset_y = 0
        self.hovered_button = None
        self.active_input = None
        self.input_texts = {}

        self.triggers_scroll = 0
        self.events_scroll = 0
        self.triggers_per_page = 5
        self.trigger_item_height = 40
        self.events_per_page = 4
        self.event_item_height = 60

        self.font_title = pygame.font.Font(None, 24)
        self.font = pygame.font.Font(None, 20)
        self.font_small = pygame.font.Font(None, 16)

        # Armazenará os retângulos dos campos específicos para detecção de clique
        self.specific_fields = {}

        self._init_ui()
        self._update_editor_layout()  # Calcula layout inicial

    def _init_ui(self):
        x, y, w, h = self.rect
        margin = 20
        content_y = y + 45

        triggers_width = int(w * 0.3)
        triggers_area_x = x + margin
        self.triggers_list_area = pygame.Rect(triggers_area_x, content_y + 35, triggers_width - 10,
                                              self.triggers_per_page * self.trigger_item_height + 5)
        self.add_trigger_button = pygame.Rect(triggers_area_x, content_y + 5, 80, 25)
        self.remove_trigger_button = pygame.Rect(triggers_area_x + 90, content_y + 5, 80, 25)

        editor_width = w - triggers_width - (margin * 2)
        editor_area_x = x + triggers_width + margin
        editor_area_y = content_y
        self.editor_area = pygame.Rect(editor_area_x, editor_area_y, editor_width, h - 50)

        button_width = 80
        button_spacing = 15
        buttons_start_x = x + (w - (button_width * 2 + button_spacing)) // 2
        self.save_button = pygame.Rect(buttons_start_x, y + h - 40, button_width, 30)
        self.cancel_button = pygame.Rect(buttons_start_x + button_width + button_spacing, y + h - 40, button_width, 30)

        # Elementos fixos do editor (título, tipo, etc.)
        self._init_fixed_editor_elements(editor_area_x, editor_area_y, editor_width)

    def _init_fixed_editor_elements(self, editor_x, editor_y, editor_width):
        margin = 10
        current_y = editor_y + margin

        self.trigger_title = pygame.Rect(editor_x + margin, current_y, editor_width - margin*2, 25)
        current_y += 35

        # Tipo de gatilho
        self.trigger_type_label = pygame.Rect(editor_x + margin, current_y, 80, 25)
        self.trigger_type_display = pygame.Rect(editor_x + margin + 90, current_y, 120, 25)
        self.trigger_type_prev = pygame.Rect(editor_x + margin + 220, current_y, 25, 25)
        self.trigger_type_next = pygame.Rect(editor_x + margin + 250, current_y, 25, 25)
        current_y += 35

        # Área onde serão desenhados os campos específicos (será preenchida dinamicamente)
        self.specific_area_start_y = current_y
        # A altura será calculada em _update_editor_layout

        # Área da lista de eventos (será posicionada após os campos específicos)
        self.events_label = pygame.Rect(editor_x + margin, 0, 100, 25)   # y será atualizado
        self.add_event_button = pygame.Rect(editor_x + editor_width - 110, 0, 90, 25)  # y atualizado
        self.events_list_area = pygame.Rect(editor_x + margin, 0, editor_width - margin*2,
                                            self.events_per_page * self.event_item_height + 5)

        # Guardamos a largura do editor para recalcular
        self.editor_width = editor_width
        self.editor_x = editor_x
        self.editor_y = editor_y

    def _update_editor_layout(self):
        """Recalcula as posições de todos os elementos do editor com base no tipo atual."""
        trigger = self.event_manager.get_current_trigger()
        if not trigger:
            return

        # Margens
        margin = 10
        x = self.editor_x
        y = self.editor_y

        # Posição inicial após o título e tipo
        current_y = self.trigger_title.y + 35 + 35  # título + tipo (já incluso)

        # O tipo ocupa uma linha, então current_y já está após o tipo
        # Agora vamos posicionar os campos específicos conforme o tipo
        specific_height = 0
        if trigger.trigger_type == TriggerType.TIME:
            # TIME: apenas um campo "Tempo (s)"
            specific_height = 35
            self.time_label = pygame.Rect(x + margin, current_y, 100, 25)
            self.time_input = pygame.Rect(x + margin + 110, current_y, 80, 25)
            # Armazenar referências para detecção de clique
            self.specific_fields = {
                'time_input': self.time_input,
            }
        elif trigger.trigger_type in (TriggerType.WAVE, TriggerType.AFTER_WAVE):
            # WAVE: índice + estado (se for WAVE)
            specific_height = 35
            self.wave_index_label = pygame.Rect(x + margin, current_y, 80, 25)
            self.wave_index_display = pygame.Rect(x + margin + 90, current_y, 60, 25)
            self.wave_index_prev = pygame.Rect(x + margin + 160, current_y, 25, 25)
            self.wave_index_next = pygame.Rect(x + margin + 190, current_y, 25, 25)
            self.specific_fields = {
                'wave_index_prev': self.wave_index_prev,
                'wave_index_next': self.wave_index_next,
            }
            if trigger.trigger_type == TriggerType.WAVE:
                # Estado da wave
                self.wave_state_label = pygame.Rect(x + margin, current_y + 35, 80, 25)
                self.wave_state_display = pygame.Rect(x + margin + 90, current_y + 35, 100, 25)
                self.wave_state_prev = pygame.Rect(x + margin + 200, current_y + 35, 25, 25)
                self.wave_state_next = pygame.Rect(x + margin + 230, current_y + 35, 25, 25)
                self.specific_fields.update({
                    'wave_state_prev': self.wave_state_prev,
                    'wave_state_next': self.wave_state_next,
                })
                specific_height = 70  # duas linhas
            else:
                specific_height = 35
        elif trigger.trigger_type == TriggerType.CUSTOM:
            specific_height = 35
            self.custom_condition_label = pygame.Rect(x + margin, current_y, 80, 25)
            self.custom_condition_input = pygame.Rect(x + margin + 90, current_y, 200, 25)
            self.specific_fields = {
                'custom_condition_input': self.custom_condition_input,
            }
        else:
            # Outros tipos não têm parâmetros
            specific_height = 0
            self.specific_fields = {}

        # Agora posicionamos a lista de eventos logo após os campos específicos
        events_y = current_y + specific_height + 15  # 15px de espaçamento
        self.events_label.y = events_y
        self.add_event_button.y = events_y
        self.events_list_area.y = events_y + 30  # abaixo do label

        # Ajusta a altura total da área de editor (opcional, mas não necessário para colisão)
        # Guardamos a posição inferior para referência
        self.events_bottom = self.events_list_area.bottom

    def _update_button_positions(self):
        # (mesmo código original, mas com a chamada a _update_editor_layout no final)
        x, y, w, h = self.rect
        margin = 20
        content_y = y + 45

        triggers_width = int(w * 0.3)
        triggers_area_x = x + margin
        self.triggers_list_area.x = triggers_area_x
        self.triggers_list_area.y = content_y + 35
        self.add_trigger_button.x = triggers_area_x
        self.add_trigger_button.y = content_y + 5
        self.remove_trigger_button.x = triggers_area_x + 90
        self.remove_trigger_button.y = content_y + 5

        editor_width = w - triggers_width - (margin * 2)
        editor_area_x = x + triggers_width + margin
        editor_area_y = content_y
        self.editor_area.x = editor_area_x
        self.editor_area.y = editor_area_y
        self.editor_area.width = editor_width
        self.editor_x = editor_area_x
        self.editor_y = editor_area_y
        self.editor_width = editor_width
        self._init_fixed_editor_elements(editor_area_x, editor_area_y, editor_width)
        self._update_editor_layout()

        button_width = 80
        button_spacing = 15
        buttons_start_x = x + (w - (button_width * 2 + button_spacing)) // 2
        self.save_button.x = buttons_start_x
        self.save_button.y = y + h - 40
        self.cancel_button.x = buttons_start_x + button_width + button_spacing
        self.cancel_button.y = y + h - 40

    # ===== HANDLE EVENT =====
    def handle_event(self, event):
        if not self.visible:
            return False

        mouse_pos = pygame.mouse.get_pos()
        mouse_x, mouse_y = mouse_pos

        if hasattr(self, 'event_edit_dialog') and self.event_edit_dialog and self.event_edit_dialog.visible:
            result = self.event_edit_dialog.handle_event(event)
            if not self.event_edit_dialog.visible:
                self.event_edit_dialog = None
            return True

        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            if not self.rect.collidepoint(mouse_x, mouse_y):
                return True
            return self._handle_left_click(mouse_x, mouse_y)

        if event.type == pygame.MOUSEBUTTONUP and event.button == 1:
            self.dragging = False
            return True

        if event.type == pygame.MOUSEMOTION:
            if self.dragging:
                self.rect.x = mouse_x - self.drag_offset_x
                self.rect.y = mouse_y - self.drag_offset_y
                self._update_button_positions()
                return True
            self._update_hover(mouse_x, mouse_y)

        if event.type == pygame.MOUSEWHEEL:
            return self._handle_scroll(event.y)

        if event.type == pygame.KEYDOWN and self.active_input:
            return self._handle_keydown(event)

        return True

    def _handle_left_click(self, mouse_x, mouse_y):
        title_rect = pygame.Rect(self.rect.x, self.rect.y, self.rect.width, 30)
        if title_rect.collidepoint(mouse_x, mouse_y):
            self.dragging = True
            self.drag_offset_x = mouse_x - self.rect.x
            self.drag_offset_y = mouse_y - self.rect.y
            return True

        if self.save_button.collidepoint(mouse_x, mouse_y):
            self.visible = False
            return "saved"
        if self.cancel_button.collidepoint(mouse_x, mouse_y):
            self.visible = False
            return True

        if self.add_trigger_button.collidepoint(mouse_x, mouse_y):
            self.event_manager.add_trigger()
            self.triggers_scroll = 0
            self.events_scroll = 0
            self.active_input = None
            self._update_editor_layout()
            return True
        if self.remove_trigger_button.collidepoint(mouse_x, mouse_y):
            self.event_manager.remove_trigger(self.event_manager.selected_trigger)
            self.triggers_scroll = 0
            self._update_editor_layout()
            return True

        if self.triggers_list_area.collidepoint(mouse_x, mouse_y):
            relative_y = mouse_y - self.triggers_list_area.y
            item_index = (relative_y // self.trigger_item_height) + self.triggers_scroll
            if 0 <= item_index < len(self.event_manager.triggers):
                self.event_manager.selected_trigger = item_index
                self.events_scroll = 0
                self._update_editor_layout()
                return True

        trigger = self.event_manager.get_current_trigger()
        if trigger:
            return self._handle_editor_click(mouse_x, mouse_y, trigger)

        return True

    def _handle_editor_click(self, mouse_x, mouse_y, trigger):
        # PRIORIDADE 1: Campos específicos (definidos em specific_fields)
        for field_name, rect in self.specific_fields.items():
            if rect.collidepoint(mouse_x, mouse_y):
                if field_name == "time_input":
                    self.active_input = "time"
                    self.input_texts["time"] = str(trigger.time_value)
                    return True
                elif field_name == "wave_index_prev":
                    self._change_wave_index(trigger, -1)
                    self._update_editor_layout()
                    return True
                elif field_name == "wave_index_next":
                    self._change_wave_index(trigger, 1)
                    self._update_editor_layout()
                    return True
                elif field_name == "wave_state_prev":
                    self._change_wave_state(trigger, -1)
                    self._update_editor_layout()
                    return True
                elif field_name == "wave_state_next":
                    self._change_wave_state(trigger, 1)
                    self._update_editor_layout()
                    return True
                elif field_name == "custom_condition_input":
                    self.active_input = "custom_condition"
                    self.input_texts["custom_condition"] = trigger.custom_condition
                    return True

        # PRIORIDADE 2: Controles de tipo (sempre visíveis)
        if self.trigger_type_prev.collidepoint(mouse_x, mouse_y):
            self._change_trigger_type(trigger, -1)
            self._update_editor_layout()
            return True
        if self.trigger_type_next.collidepoint(mouse_x, mouse_y):
            self._change_trigger_type(trigger, 1)
            self._update_editor_layout()
            return True

        # PRIORIDADE 3: Botão adicionar evento
        if self.add_event_button.collidepoint(mouse_x, mouse_y):
            new_event = GameEvent()
            new_event.event_type = EventType.MESSAGE
            new_event.message_text = "Nova mensagem"
            trigger.add_event(new_event)
            self.events_scroll = max(0, len(trigger.events) - self.events_per_page)
            return True

        # PRIORIDADE 4: Lista de eventos
        if self.events_list_area.collidepoint(mouse_x, mouse_y):
            relative_y = mouse_y - self.events_list_area.y
            item_index = (relative_y // self.event_item_height) + self.events_scroll
            if 0 <= item_index < len(trigger.events):
                # Botão remover
                remove_rect = pygame.Rect(self.events_list_area.right - 30,
                                          self.events_list_area.y + 5 + (item_index - self.events_scroll) * self.event_item_height,
                                          20, 20)
                if remove_rect.collidepoint(mouse_x, mouse_y):
                    trigger.remove_event(item_index)
                    self.events_scroll = min(self.events_scroll, max(0, len(trigger.events) - self.events_per_page))
                    return True
                # Editar
                self._open_event_editor(trigger, item_index)
                return True

        return True

    def _change_trigger_type(self, trigger, direction):
        types = [TriggerType.TIME, TriggerType.WAVE, TriggerType.START_PHASE,
                 TriggerType.BEFORE_BOSS, TriggerType.AFTER_BOSS_DEFEAT,
                 TriggerType.AFTER_WAVE, TriggerType.CUSTOM]
        current_idx = types.index(trigger.trigger_type)
        new_idx = (current_idx + direction) % len(types)
        trigger.trigger_type = types[new_idx]
        # Resetar campos desnecessários
        if trigger.trigger_type != TriggerType.TIME:
            trigger.time_value = 0.0
        if trigger.trigger_type not in [TriggerType.WAVE, TriggerType.AFTER_WAVE]:
            trigger.wave_index = 0
        if trigger.trigger_type != TriggerType.WAVE:
            trigger.wave_state = WaveTriggerState.WAVE_START
        if trigger.trigger_type != TriggerType.CUSTOM:
            trigger.custom_condition = ""

    def _change_wave_index(self, trigger, direction):
        max_wave = max(0, len(self.wave_manager.waves) - 1)
        new_index = trigger.wave_index + direction
        if 0 <= new_index <= max_wave:
            trigger.wave_index = new_index

    def _change_wave_state(self, trigger, direction):
        states = [WaveTriggerState.WAVE_START, WaveTriggerState.WAVE_END]
        current_idx = states.index(trigger.wave_state)
        new_idx = (current_idx + direction) % len(states)
        trigger.wave_state = states[new_idx]

    def _open_event_editor(self, trigger, event_index):
        event = trigger.events[event_index]
        dialog_width = 550
        dialog_height = 480
        dialog_x = self.rect.x + (self.rect.width - dialog_width) // 2
        dialog_y = self.rect.y + (self.rect.height - dialog_height) // 2

        def on_event_saved(updated_event):
            trigger.events[event_index] = updated_event
            print(f"Evento atualizado: {updated_event.event_type}")

        self.event_edit_dialog = EventEditDialog(
            dialog_x, dialog_y, dialog_width, dialog_height,
            event, on_event_saved
        )

    def _update_hover(self, mouse_x, mouse_y):
        # Atualiza o hover para todos os botões (incluindo os específicos)
        buttons = [
            (self.save_button, "save"),
            (self.cancel_button, "cancel"),
            (self.add_trigger_button, "add_trigger"),
            (self.remove_trigger_button, "remove_trigger"),
            (self.add_event_button, "add_event"),
            (self.trigger_type_prev, "trigger_type_prev"),
            (self.trigger_type_next, "trigger_type_next"),
        ]
        # Adiciona os específicos dinamicamente
        for field_name, rect in self.specific_fields.items():
            if field_name in ("time_input", "custom_condition_input"):
                # São inputs, não botões com hover especial
                continue
            buttons.append((rect, field_name))

        for button, name in buttons:
            if button.collidepoint(mouse_x, mouse_y):
                self.hovered_button = name
                return
        self.hovered_button = None

    def _handle_scroll(self, direction):
        if self.triggers_list_area.collidepoint(pygame.mouse.get_pos()):
            max_scroll = max(0, len(self.event_manager.triggers) - self.triggers_per_page)
            self.triggers_scroll = max(0, min(max_scroll, self.triggers_scroll - direction))
            return True
        if self.events_list_area.collidepoint(pygame.mouse.get_pos()):
            trigger = self.event_manager.get_current_trigger()
            if trigger:
                max_scroll = max(0, len(trigger.events) - self.events_per_page)
                self.events_scroll = max(0, min(max_scroll, self.events_scroll - direction))
            return True
        return False

    def _handle_keydown(self, event):
        if event.key == pygame.K_RETURN:
            return self._apply_input()
        elif event.key == pygame.K_ESCAPE:
            self.active_input = None
            return True
        elif event.key == pygame.K_BACKSPACE:
            if self.active_input in self.input_texts:
                self.input_texts[self.active_input] = self.input_texts[self.active_input][:-1]
            return True
        elif event.unicode.isprintable():
            if self.active_input in self.input_texts:
                self.input_texts[self.active_input] += event.unicode
            return True
        return False

    def _apply_input(self):
        if not self.active_input:
            return False
        trigger = self.event_manager.get_current_trigger()
        if not trigger:
            self.active_input = None
            return False

        try:
            if self.active_input == "time":
                value = float(self.input_texts.get("time", "0"))
                trigger.time_value = max(0.0, value)
            elif self.active_input == "custom_condition":
                trigger.custom_condition = self.input_texts.get("custom_condition", "")
        except ValueError:
            pass
        self.active_input = None
        return True

    # ===== RENDER =====
    def render(self, screen):
        if not self.visible:
            return

        overlay = pygame.Surface((screen.get_width(), screen.get_height()))
        overlay.set_alpha(180)
        overlay.fill((0, 0, 0))
        screen.blit(overlay, (0, 0))

        pygame.draw.rect(screen, self.COLORS['bg'], self.rect, border_radius=10)
        pygame.draw.rect(screen, self.COLORS['border'], self.rect, 2, border_radius=10)

        title_bar = pygame.Rect(self.rect.x, self.rect.y, self.rect.width, 30)
        pygame.draw.rect(screen, self.COLORS['bg_light'], title_bar,
                         border_top_left_radius=10, border_top_right_radius=10)
        title = self.font_title.render("Configuração de Eventos", True, self.COLORS['text'])
        screen.blit(title, (self.rect.x + 10, self.rect.y + 8))

        self._render_triggers_list(screen)
        self._render_trigger_editor(screen)
        self._render_buttons(screen)

        if hasattr(self, 'event_edit_dialog') and self.event_edit_dialog and self.event_edit_dialog.visible:
            self.event_edit_dialog.render(screen)

    def _render_triggers_list(self, screen):
        # (mesmo código original, sem alterações)
        pygame.draw.rect(screen, self.COLORS['bg_dark'], self.triggers_list_area, border_radius=5)

        add_color = self.COLORS['success'] if self.hovered_button == "add_trigger" else (0, 80, 0)
        remove_color = self.COLORS['danger'] if self.hovered_button == "remove_trigger" else (80, 0, 0)
        pygame.draw.rect(screen, add_color, self.add_trigger_button, border_radius=5)
        add_text = self.font_small.render("+ Gatilho", True, self.COLORS['text'])
        screen.blit(add_text, (self.add_trigger_button.x + 5, self.add_trigger_button.y + 5))

        pygame.draw.rect(screen, remove_color, self.remove_trigger_button, border_radius=5)
        remove_text = self.font_small.render("- Remover", True, self.COLORS['text'])
        screen.blit(remove_text, (self.remove_trigger_button.x + 5, self.remove_trigger_button.y + 5))

        old_clip = screen.get_clip()
        screen.set_clip(self.triggers_list_area)

        list_x = self.triggers_list_area.x + 5
        list_start_y = self.triggers_list_area.y + 2 - self.triggers_scroll * self.trigger_item_height

        for i, trigger in enumerate(self.event_manager.triggers):
            item_y = list_start_y + i * self.trigger_item_height
            if item_y + self.trigger_item_height < self.triggers_list_area.y or item_y > self.triggers_list_area.bottom:
                continue

            item_rect = pygame.Rect(list_x, item_y, self.triggers_list_area.width - 10, self.trigger_item_height - 4)
            is_selected = (i == self.event_manager.selected_trigger)
            bg_color = self.COLORS['accent'] if is_selected else (self.COLORS['bg_light'] if i % 2 == 0 else self.COLORS['bg'])
            pygame.draw.rect(screen, bg_color, item_rect)
            if is_selected:
                pygame.draw.rect(screen, self.COLORS['border'], item_rect, 1)

            # Descrição do gatilho (mesmo)
            desc = self._get_trigger_description(trigger)
            text = self.font_small.render(desc, True, self.COLORS['text'])
            screen.blit(text, (item_rect.x + 5, item_rect.y + 7))

        screen.set_clip(old_clip)

        if len(self.event_manager.triggers) > self.triggers_per_page:
            scroll_text = self.font_small.render(
                f"{self.triggers_scroll + 1}-{min(self.triggers_scroll + self.triggers_per_page, len(self.event_manager.triggers))} de {len(self.event_manager.triggers)}",
                True, self.COLORS['text_dark'])
            screen.blit(scroll_text, (self.triggers_list_area.x + 5, self.triggers_list_area.bottom + 5))

    def _get_trigger_description(self, trigger):
        if trigger.trigger_type == TriggerType.TIME:
            return f"Tempo: {trigger.time_value}s"
        elif trigger.trigger_type == TriggerType.WAVE:
            state_name = "Início" if trigger.wave_state == WaveTriggerState.WAVE_START else "Fim"
            return f"Wave {trigger.wave_index + 1} ({state_name})"
        elif trigger.trigger_type == TriggerType.START_PHASE:
            return "Início da fase"
        elif trigger.trigger_type == TriggerType.BEFORE_BOSS:
            return "Antes do Boss"
        elif trigger.trigger_type == TriggerType.AFTER_BOSS_DEFEAT:
            return "Após derrotar Boss"
        elif trigger.trigger_type == TriggerType.AFTER_WAVE:
            return f"Após Wave {trigger.wave_index + 1}"
        elif trigger.trigger_type == TriggerType.CUSTOM:
            return f"Custom: {trigger.custom_condition}"
        return "Desconhecido"

    def _render_trigger_editor(self, screen):
        trigger = self.event_manager.get_current_trigger()
        if not trigger:
            msg = self.font.render("Selecione um gatilho à esquerda", True, self.COLORS['text_dim'])
            screen.blit(msg, msg.get_rect(center=self.editor_area.center))
            return

        pygame.draw.rect(screen, self.COLORS['bg_light'], self.editor_area, border_radius=5)
        pygame.draw.rect(screen, self.COLORS['border_light'], self.editor_area, 1, border_radius=5)

        # Título do gatilho
        title_text = self.font.render(f"Gatilho {self.event_manager.selected_trigger + 1}", True, self.COLORS['border'])
        screen.blit(title_text, (self.trigger_title.x, self.trigger_title.y))

        # Tipo de gatilho
        type_label = self.font_small.render("Tipo:", True, self.COLORS['text_dim'])
        screen.blit(type_label, (self.trigger_type_label.x, self.trigger_type_label.y))

        type_name = trigger.trigger_type.capitalize() if trigger.trigger_type in ["time", "wave", "start_phase", "before_boss", "after_boss_defeat", "after_wave", "custom"] else trigger.trigger_type
        pygame.draw.rect(screen, self.COLORS['bg'], self.trigger_type_display)
        pygame.draw.rect(screen, self.COLORS['border_light'], self.trigger_type_display, 1)
        type_text = self.font_small.render(type_name, True, self.COLORS['text'])
        screen.blit(type_text, (self.trigger_type_display.x + 5, self.trigger_type_display.y + 4))

        self._render_nav_buttons(screen, self.trigger_type_prev, self.trigger_type_next)

        # Renderiza campos específicos
        self._render_specific_fields(screen, trigger)

        # Lista de eventos
        self._render_events_list(screen, trigger)

    def _render_specific_fields(self, screen, trigger):
        # Usa os retângulos já calculados em _update_editor_layout
        if trigger.trigger_type == TriggerType.TIME:
            label = self.font_small.render("Tempo (s):", True, self.COLORS['text_dim'])
            screen.blit(label, (self.time_label.x, self.time_label.y))

            input_color = self.COLORS['input_active'] if self.active_input == "time" else self.COLORS['input_border']
            pygame.draw.rect(screen, self.COLORS['input_bg'], self.time_input)
            pygame.draw.rect(screen, input_color, self.time_input, 1)
            time_text = self.input_texts.get("time", f"{trigger.time_value:.1f}") if self.active_input == "time" else f"{trigger.time_value:.1f}"
            text = self.font_small.render(time_text, True, self.COLORS['text'])
            screen.blit(text, (self.time_input.x + 5, self.time_input.y + 4))

        elif trigger.trigger_type in (TriggerType.WAVE, TriggerType.AFTER_WAVE):
            index_label = self.font_small.render("Wave:", True, self.COLORS['text_dim'])
            screen.blit(index_label, (self.wave_index_label.x, self.wave_index_label.y))

            pygame.draw.rect(screen, self.COLORS['bg'], self.wave_index_display)
            pygame.draw.rect(screen, self.COLORS['border_light'], self.wave_index_display, 1)
            index_text = self.font_small.render(str(trigger.wave_index + 1), True, self.COLORS['text'])
            screen.blit(index_text, (self.wave_index_display.x + 5, self.wave_index_display.y + 4))

            self._render_nav_buttons(screen, self.wave_index_prev, self.wave_index_next)

            if trigger.trigger_type == TriggerType.WAVE:
                state_label = self.font_small.render("Momento:", True, self.COLORS['text_dim'])
                screen.blit(state_label, (self.wave_state_label.x, self.wave_state_label.y))

                state_name = "Início" if trigger.wave_state == WaveTriggerState.WAVE_START else "Fim"
                pygame.draw.rect(screen, self.COLORS['bg'], self.wave_state_display)
                pygame.draw.rect(screen, self.COLORS['border_light'], self.wave_state_display, 1)
                state_text = self.font_small.render(state_name, True, self.COLORS['text'])
                screen.blit(state_text, (self.wave_state_display.x + 5, self.wave_state_display.y + 4))

                self._render_nav_buttons(screen, self.wave_state_prev, self.wave_state_next)

        elif trigger.trigger_type == TriggerType.CUSTOM:
            label = self.font_small.render("Condição:", True, self.COLORS['text_dim'])
            screen.blit(label, (self.custom_condition_label.x, self.custom_condition_label.y))

            input_color = self.COLORS['input_active'] if self.active_input == "custom_condition" else self.COLORS['input_border']
            pygame.draw.rect(screen, self.COLORS['input_bg'], self.custom_condition_input)
            pygame.draw.rect(screen, input_color, self.custom_condition_input, 1)
            text = self.input_texts.get("custom_condition", trigger.custom_condition) if self.active_input == "custom_condition" else trigger.custom_condition
            text_surf = self.font_small.render(text, True, self.COLORS['text'])
            screen.blit(text_surf, (self.custom_condition_input.x + 5, self.custom_condition_input.y + 4))

    def _render_events_list(self, screen, trigger):
        title = self.font_small.render("Eventos:", True, self.COLORS['text_dim'])
        screen.blit(title, (self.events_label.x, self.events_label.y))

        add_color = self.COLORS['success'] if self.hovered_button == "add_event" else (0, 80, 0)
        pygame.draw.rect(screen, add_color, self.add_event_button, border_radius=5)
        add_text = self.font_small.render("+ Evento", True, self.COLORS['text'])
        screen.blit(add_text, (self.add_event_button.x + 5, self.add_event_button.y + 5))

        pygame.draw.rect(screen, self.COLORS['bg_dark'], self.events_list_area, border_radius=5)

        old_clip = screen.get_clip()
        screen.set_clip(self.events_list_area)

        list_x = self.events_list_area.x + 5
        list_start_y = self.events_list_area.y + 2 - self.events_scroll * self.event_item_height

        for i, event in enumerate(trigger.events):
            item_y = list_start_y + i * self.event_item_height
            if item_y + self.event_item_height < self.events_list_area.y or item_y > self.events_list_area.bottom:
                continue

            item_rect = pygame.Rect(list_x, item_y, self.events_list_area.width - 10, self.event_item_height - 4)
            bg_color = self.COLORS['bg_light'] if i % 2 == 0 else self.COLORS['bg']
            pygame.draw.rect(screen, bg_color, item_rect)
            pygame.draw.rect(screen, self.COLORS['border_light'], item_rect, 1)

            # Botão remover
            remove_rect = pygame.Rect(item_rect.right - 25, item_rect.y + 5, 20, 20)
            pygame.draw.rect(screen, self.COLORS['danger'], remove_rect)
            pygame.draw.line(screen, self.COLORS['text'], (remove_rect.x + 5, remove_rect.y + 5), (remove_rect.right - 5, remove_rect.bottom - 5), 1)
            pygame.draw.line(screen, self.COLORS['text'], (remove_rect.right - 5, remove_rect.y + 5), (remove_rect.x + 5, remove_rect.bottom - 5), 1)

            # Descrição do evento
            desc = self._get_event_description(event)
            text = self.font_small.render(desc, True, self.COLORS['text'])
            screen.blit(text, (item_rect.x + 5, item_rect.y + 5))

            delay_text = self.font_small.render(f"Delay: {event.delay}s", True, self.COLORS['text_dim'])
            screen.blit(delay_text, (item_rect.x + 5, item_rect.y + 25))

        screen.set_clip(old_clip)

        if len(trigger.events) > self.events_per_page:
            scroll_text = self.font_small.render(
                f"{self.events_scroll + 1}-{min(self.events_scroll + self.events_per_page, len(trigger.events))} de {len(trigger.events)}",
                True, self.COLORS['text_dark'])
            screen.blit(scroll_text, (self.events_list_area.x + 5, self.events_list_area.bottom + 5))

    def _get_event_description(self, event):
        if event.event_type == EventType.MESSAGE:
            desc = f"MENSAGEM: {event.message_text[:30]}"
            if len(event.message_text) > 30:
                desc += "..."
        elif event.event_type == EventType.CAMERA:
            effect_name = "Tremor" if event.camera_effect == CameraEffect.SHAKE else "Flash"
            desc = f"CÂMERA: {effect_name}"
        elif event.event_type == EventType.TUTORIAL:
            desc = f"TUTORIAL: {event.tutorial_action}"
        elif event.event_type == EventType.GAME_STATE:
            desc = f"ESTADO: {event.state_action}"
        elif event.event_type == EventType.SPAWN:
            desc = f"SPAWN: {event.spawn_type}"
        elif event.event_type == EventType.CUSTOM_ACTION:
            desc = f"ACTION: {event.custom_action_name}"
        else:
            desc = "Desconhecido"
        return desc

    def _render_nav_buttons(self, screen, prev_rect, next_rect):
        prev_color = self.COLORS['bg_light'] if self.hovered_button in ["trigger_type_prev", "wave_index_prev", "wave_state_prev"] else (60, 60, 70)
        next_color = self.COLORS['bg_light'] if self.hovered_button in ["trigger_type_next", "wave_index_next", "wave_state_next"] else (60, 60, 70)
        pygame.draw.rect(screen, prev_color, prev_rect)
        pygame.draw.rect(screen, next_color, next_rect)
        pygame.draw.rect(screen, self.COLORS['border_light'], prev_rect, 1)
        pygame.draw.rect(screen, self.COLORS['border_light'], next_rect, 1)

        prev_text = self.font_small.render("<", True, self.COLORS['text'])
        next_text = self.font_small.render(">", True, self.COLORS['text'])
        screen.blit(prev_text, (prev_rect.x + 8, prev_rect.y + 4))
        screen.blit(next_text, (next_rect.x + 8, next_rect.y + 4))

    def _render_buttons(self, screen):
        save_color = self.COLORS['success'] if self.hovered_button == "save" else (0, 100, 0)
        cancel_color = self.COLORS['danger'] if self.hovered_button == "cancel" else (100, 0, 0)
        pygame.draw.rect(screen, save_color, self.save_button, border_radius=5)
        pygame.draw.rect(screen, self.COLORS['text'], self.save_button, 1, border_radius=5)
        save_text = self.font.render("Salvar", True, self.COLORS['text'])
        screen.blit(save_text, (self.save_button.x + 15, self.save_button.y + 5))

        pygame.draw.rect(screen, cancel_color, self.cancel_button, border_radius=5)
        pygame.draw.rect(screen, self.COLORS['text'], self.cancel_button, 1, border_radius=5)
        cancel_text = self.font.render("Cancelar", True, self.COLORS['text'])
        screen.blit(cancel_text, (self.cancel_button.x + 10, self.cancel_button.y + 5))


# ======================================================================
# Classe EventEditDialog (também revisada com layout dinâmico)
# ======================================================================

class EventEditDialog:
    """Sub-diálogo para editar um evento específico."""

    COLORS = EventConfigDialog.COLORS

    def __init__(self, x, y, width, height, event, callback):
        self.rect = pygame.Rect(x, y, width, height)
        self.visible = True
        self.event = event
        self.callback = callback

        self.dragging = False
        self.drag_offset_x = 0
        self.drag_offset_y = 0
        self.active_input = None
        self.input_texts = {}

        self.font_title = pygame.font.Font(None, 24)
        self.font = pygame.font.Font(None, 20)
        self.font_small = pygame.font.Font(None, 16)

        self.save_button = pygame.Rect(x + width - 180, y + height - 45, 80, 30)
        self.cancel_button = pygame.Rect(x + width - 90, y + height - 45, 80, 30)

        # Campos específicos serão armazenados aqui
        self.specific_fields = {}

        self._init_fixed_fields()
        self._update_specific_layout()

    def _init_fixed_fields(self):
        x, y, w, h = self.rect
        margin = 20
        current_y = y + 50

        # Tipo de evento
        self.event_type_label = pygame.Rect(x + margin, current_y, 80, 25)
        self.event_type_display = pygame.Rect(x + margin + 90, current_y, 150, 25)
        self.event_type_prev = pygame.Rect(x + margin + 250, current_y, 25, 25)
        self.event_type_next = pygame.Rect(x + margin + 280, current_y, 25, 25)
        current_y += 35

        # Delay comum
        self.delay_label = pygame.Rect(x + margin, current_y, 80, 25)
        self.delay_input = pygame.Rect(x + margin + 90, current_y, 80, 25)
        current_y += 35

        # Área para campos específicos (começa após o delay)
        self.specific_start_y = current_y

        # Guardamos dimensões
        self.margin = margin
        self.editor_x = x
        self.editor_y = y

    def _update_specific_layout(self):
        """Recalcula posições dos campos específicos com base no tipo de evento."""
        x = self.rect.x
        y = self.rect.y
        margin = self.margin
        current_y = self.specific_start_y

        # Limpa campos anteriores
        self.specific_fields = {}

        if self.event.event_type == EventType.MESSAGE:
            # Speaker
            self.speaker_label = pygame.Rect(x + margin, current_y, 80, 25)
            self.speaker_input = pygame.Rect(x + margin + 100, current_y, 200, 25)
            self.specific_fields['speaker_input'] = self.speaker_input
            current_y += 35

            # Mensagem
            self.message_label = pygame.Rect(x + margin, current_y, 80, 25)
            self.message_input = pygame.Rect(x + margin + 100, current_y, 300, 50)
            self.specific_fields['message_input'] = self.message_input
            current_y += 60

            # Sprite
            self.sprite_label = pygame.Rect(x + margin, current_y, 80, 25)
            self.sprite_input = pygame.Rect(x + margin + 100, current_y, 200, 25)
            self.sprite_button = pygame.Rect(x + margin + 310, current_y, 80, 25)
            self.specific_fields['sprite_input'] = self.sprite_input
            self.specific_fields['sprite_button'] = self.sprite_button
            current_y += 35

            # Action Label
            self.action_label_label = pygame.Rect(x + margin, current_y, 80, 25)
            self.action_label_input = pygame.Rect(x + margin + 100, current_y, 150, 25)
            self.specific_fields['action_label_input'] = self.action_label_input
            current_y += 35

            # Action Trigger
            self.action_trigger_label = pygame.Rect(x + margin, current_y, 120, 25)
            self.action_trigger_input = pygame.Rect(x + margin + 130, current_y, 200, 25)
            self.specific_fields['action_trigger_input'] = self.action_trigger_input

        elif self.event.event_type == EventType.CAMERA:
            # Efeito
            self.effect_label = pygame.Rect(x + margin, current_y, 80, 25)
            self.effect_display = pygame.Rect(x + margin + 100, current_y, 120, 25)
            self.effect_prev = pygame.Rect(x + margin + 230, current_y, 25, 25)
            self.effect_next = pygame.Rect(x + margin + 260, current_y, 25, 25)
            self.specific_fields['effect_prev'] = self.effect_prev
            self.specific_fields['effect_next'] = self.effect_next
            current_y += 35

            # Intensidade
            self.intensity_label = pygame.Rect(x + margin, current_y, 80, 25)
            self.intensity_input = pygame.Rect(x + margin + 100, current_y, 60, 25)
            self.specific_fields['intensity_input'] = self.intensity_input
            current_y += 35

            # Duração
            self.duration_label = pygame.Rect(x + margin, current_y, 100, 25)
            self.duration_input = pygame.Rect(x + margin + 110, current_y, 60, 25)
            self.specific_fields['duration_input'] = self.duration_input

        elif self.event.event_type == EventType.TUTORIAL:
            # Ação
            self.tutorial_action_label = pygame.Rect(x + margin, current_y, 80, 25)
            self.tutorial_action_display = pygame.Rect(x + margin + 100, current_y, 180, 25)
            self.tutorial_action_prev = pygame.Rect(x + margin + 290, current_y, 25, 25)
            self.tutorial_action_next = pygame.Rect(x + margin + 320, current_y, 25, 25)
            self.specific_fields['tutorial_action_prev'] = self.tutorial_action_prev
            self.specific_fields['tutorial_action_next'] = self.tutorial_action_next
            current_y += 35

            # Highlight
            self.highlight_label = pygame.Rect(x + margin, current_y, 80, 25)
            self.highlight_input = pygame.Rect(x + margin + 100, current_y, 200, 25)
            self.specific_fields['highlight_input'] = self.highlight_input

        elif self.event.event_type == EventType.GAME_STATE:
            # Ação
            self.state_action_label = pygame.Rect(x + margin, current_y, 80, 25)
            self.state_action_display = pygame.Rect(x + margin + 100, current_y, 180, 25)
            self.state_action_prev = pygame.Rect(x + margin + 290, current_y, 25, 25)
            self.state_action_next = pygame.Rect(x + margin + 320, current_y, 25, 25)
            self.specific_fields['state_action_prev'] = self.state_action_prev
            self.specific_fields['state_action_next'] = self.state_action_next
            current_y += 35

            # Parâmetros
            self.state_params_label = pygame.Rect(x + margin, current_y, 100, 25)
            self.state_params_input = pygame.Rect(x + margin + 110, current_y, 250, 25)
            self.specific_fields['state_params_input'] = self.state_params_input

        elif self.event.event_type == EventType.SPAWN:
            # Tipo
            self.spawn_type_label = pygame.Rect(x + margin, current_y, 80, 25)
            self.spawn_type_display = pygame.Rect(x + margin + 100, current_y, 180, 25)
            self.spawn_type_prev = pygame.Rect(x + margin + 290, current_y, 25, 25)
            self.spawn_type_next = pygame.Rect(x + margin + 320, current_y, 25, 25)
            self.specific_fields['spawn_type_prev'] = self.spawn_type_prev
            self.specific_fields['spawn_type_next'] = self.spawn_type_next
            current_y += 35

            # Parâmetros
            self.spawn_params_label = pygame.Rect(x + margin, current_y, 100, 25)
            self.spawn_params_input = pygame.Rect(x + margin + 110, current_y, 250, 25)
            self.specific_fields['spawn_params_input'] = self.spawn_params_input

        elif self.event.event_type == EventType.CUSTOM_ACTION:
            # Nome
            self.custom_name_label = pygame.Rect(x + margin, current_y, 80, 25)
            self.custom_name_input = pygame.Rect(x + margin + 100, current_y, 200, 25)
            self.specific_fields['custom_name_input'] = self.custom_name_input
            current_y += 35

            # Parâmetros
            self.custom_params_label = pygame.Rect(x + margin, current_y, 100, 25)
            self.custom_params_input = pygame.Rect(x + margin + 110, current_y, 250, 25)
            self.specific_fields['custom_params_input'] = self.custom_params_input

    def _update_button_positions(self):
        x, y, w, h = self.rect
        self.save_button.x = x + w - 180
        self.save_button.y = y + h - 45
        self.cancel_button.x = x + w - 90
        self.cancel_button.y = y + h - 45
        self._init_fixed_fields()
        self._update_specific_layout()

    # ===== HANDLE EVENT =====
    def handle_event(self, event):
        if not self.visible:
            return False

        mouse_pos = pygame.mouse.get_pos()
        mouse_x, mouse_y = mouse_pos

        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            if not self.rect.collidepoint(mouse_x, mouse_y):
                return False
            return self._handle_left_click(mouse_x, mouse_y)

        if event.type == pygame.MOUSEBUTTONUP and event.button == 1:
            self.dragging = False
            return True

        if event.type == pygame.MOUSEMOTION:
            if self.dragging:
                self.rect.x = mouse_x - self.drag_offset_x
                self.rect.y = mouse_y - self.drag_offset_y
                self._update_button_positions()
                return True

        if event.type == pygame.KEYDOWN and self.active_input:
            return self._handle_keydown(event)

        return True

    def _handle_left_click(self, mouse_x, mouse_y):
        title_rect = pygame.Rect(self.rect.x, self.rect.y, self.rect.width, 30)
        if title_rect.collidepoint(mouse_x, mouse_y):
            self.dragging = True
            self.drag_offset_x = mouse_x - self.rect.x
            self.drag_offset_y = mouse_y - self.rect.y
            return True

        if self.save_button.collidepoint(mouse_x, mouse_y):
            self._save_event()
            self.visible = False
            if self.callback:
                self.callback(self.event)
            return True

        if self.cancel_button.collidepoint(mouse_x, mouse_y):
            self.visible = False
            return True

        # Tipo
        if self.event_type_prev.collidepoint(mouse_x, mouse_y):
            self._change_event_type(-1)
            self._update_specific_layout()
            return True
        if self.event_type_next.collidepoint(mouse_x, mouse_y):
            self._change_event_type(1)
            self._update_specific_layout()
            return True

        # Delay
        if self.delay_input.collidepoint(mouse_x, mouse_y):
            self.active_input = "delay"
            self.input_texts["delay"] = str(self.event.delay)
            return True

        # Campos específicos
        return self._handle_specific_click(mouse_x, mouse_y)

    def _handle_specific_click(self, mouse_x, mouse_y):
        for field_name, rect in self.specific_fields.items():
            if rect.collidepoint(mouse_x, mouse_y):
                if field_name.endswith("_input"):
                    # Campo de texto
                    self.active_input = field_name
                    if field_name not in self.input_texts:
                        self.input_texts[field_name] = self._get_field_value(field_name)
                    return True
                elif field_name == "sprite_button":
                    self._select_sprite()
                    return True
                elif field_name.endswith("_prev") or field_name.endswith("_next"):
                    self._toggle_dropdown(field_name)
                    self._update_specific_layout()
                    return True
        return False

    def _get_field_value(self, field_name):
        mapping = {
            "delay": str(self.event.delay),
            "speaker_input": self.event.speaker_name,
            "message_input": self.event.message_text,
            "sprite_input": self.event.speaker_sprite_path,
            "action_label_input": self.event.action_label,
            "action_trigger_input": self.event.action_trigger,
            "intensity_input": str(self.event.camera_intensity),
            "duration_input": str(self.event.camera_duration),
            "highlight_input": self.event.tutorial_highlight,
            "state_params_input": str(self.event.state_params),
            "spawn_params_input": str(self.event.spawn_params),
            "custom_name_input": self.event.custom_action_name,
            "custom_params_input": str(self.event.custom_action_params),
        }
        return mapping.get(field_name, "")

    def _toggle_dropdown(self, field_name):
        # Para simplificar, usamos os mesmos métodos da versão original
        if field_name == "effect_prev":
            self._change_effect(-1)
        elif field_name == "effect_next":
            self._change_effect(1)
        elif field_name == "tutorial_action_prev":
            self._change_tutorial_action(-1)
        elif field_name == "tutorial_action_next":
            self._change_tutorial_action(1)
        elif field_name == "state_action_prev":
            self._change_state_action(-1)
        elif field_name == "state_action_next":
            self._change_state_action(1)
        elif field_name == "spawn_type_prev":
            self._change_spawn_type(-1)
        elif field_name == "spawn_type_next":
            self._change_spawn_type(1)

    def _change_effect(self, direction):
        options = [CameraEffect.SHAKE, CameraEffect.FLASH]
        current = self.event.camera_effect
        idx = options.index(current) if current in options else 0
        self.event.camera_effect = options[(idx + direction) % len(options)]

    def _change_tutorial_action(self, direction):
        options = [TutorialAction.OPEN_BAG, TutorialAction.PLACEMENT, TutorialAction.CAPTURE,
                   TutorialAction.BATTLE, TutorialAction.TEAM_MANAGEMENT, TutorialAction.HIGHLIGHT_UI]
        current = self.event.tutorial_action
        idx = options.index(current) if current in options else 0
        self.event.tutorial_action = options[(idx + direction) % len(options)]

    def _change_state_action(self, direction):
        options = [GameStateAction.PAUSE, GameStateAction.RESUME, GameStateAction.START_WAVE,
                   GameStateAction.COMPLETE_PHASE, GameStateAction.SHOW_NOTIFICATION]
        current = self.event.state_action
        idx = options.index(current) if current in options else 0
        self.event.state_action = options[(idx + direction) % len(options)]

    def _change_spawn_type(self, direction):
        options = [SpawnAction.BOSS, SpawnAction.ENEMY, SpawnAction.WAVE]
        current = self.event.spawn_type
        idx = options.index(current) if current in options else 0
        self.event.spawn_type = options[(idx + direction) % len(options)]

    def _select_sprite(self):
        from tkinter import filedialog, Tk
        root = Tk()
        root.withdraw()
        file_path = filedialog.askopenfilename(
            title="Selecione o sprite do personagem",
            filetypes=[("Image files", "*.png *.jpg *.jpeg *.bmp *.gif")]
        )
        if file_path:
            self.event.speaker_sprite_path = file_path
            self.input_texts["sprite_input"] = file_path

    def _change_event_type(self, direction):
        types = [EventType.MESSAGE, EventType.CAMERA, EventType.TUTORIAL,
                 EventType.GAME_STATE, EventType.SPAWN, EventType.CUSTOM_ACTION]
        current_idx = types.index(self.event.event_type)
        new_idx = (current_idx + direction) % len(types)
        self.event.event_type = types[new_idx]

    def _save_event(self):
        try:
            self.event.delay = float(self.input_texts.get("delay", "0"))
        except ValueError:
            self.event.delay = 0

        # Salva campos específicos
        if self.event.event_type == EventType.MESSAGE:
            self.event.speaker_name = self.input_texts.get("speaker_input", "")
            self.event.message_text = self.input_texts.get("message_input", "")
            self.event.speaker_sprite_path = self.input_texts.get("sprite_input", "")
            self.event.action_label = self.input_texts.get("action_label_input", "")
            self.event.action_trigger = self.input_texts.get("action_trigger_input", "")
        elif self.event.event_type == EventType.CAMERA:
            try:
                self.event.camera_intensity = float(self.input_texts.get("intensity_input", "5"))
            except ValueError:
                self.event.camera_intensity = 5
            try:
                self.event.camera_duration = float(self.input_texts.get("duration_input", "0.5"))
            except ValueError:
                self.event.camera_duration = 0.5
        elif self.event.event_type == EventType.TUTORIAL:
            self.event.tutorial_highlight = self.input_texts.get("highlight_input", "")
        elif self.event.event_type == EventType.GAME_STATE:
            # state_params pode ser dict, mas tratamos como string
            self.event.state_params = self.input_texts.get("state_params_input", {})
        elif self.event.event_type == EventType.SPAWN:
            self.event.spawn_params = self.input_texts.get("spawn_params_input", {})
        elif self.event.event_type == EventType.CUSTOM_ACTION:
            self.event.custom_action_name = self.input_texts.get("custom_name_input", "")
            self.event.custom_action_params = self.input_texts.get("custom_params_input", {})

    def _handle_keydown(self, event):
        if event.key == pygame.K_RETURN:
            self.active_input = None
            return True
        elif event.key == pygame.K_ESCAPE:
            self.active_input = None
            return True
        elif event.key == pygame.K_BACKSPACE:
            if self.active_input in self.input_texts:
                self.input_texts[self.active_input] = self.input_texts[self.active_input][:-1]
            return True
        elif event.unicode.isprintable():
            if self.active_input in self.input_texts:
                self.input_texts[self.active_input] += event.unicode
            return True
        return False

    # ===== RENDER =====
    def render(self, screen):
        if not self.visible:
            return

        overlay = pygame.Surface((screen.get_width(), screen.get_height()))
        overlay.set_alpha(200)
        overlay.fill((0, 0, 0))
        screen.blit(overlay, (0, 0))

        pygame.draw.rect(screen, self.COLORS['bg'], self.rect, border_radius=10)
        pygame.draw.rect(screen, self.COLORS['border'], self.rect, 2, border_radius=10)

        title_bar = pygame.Rect(self.rect.x, self.rect.y, self.rect.width, 30)
        pygame.draw.rect(screen, self.COLORS['bg_light'], title_bar,
                         border_top_left_radius=10, border_top_right_radius=10)
        title = self.font_title.render("Editar Evento", True, self.COLORS['text'])
        screen.blit(title, (self.rect.x + 10, self.rect.y + 8))

        x, y = self.rect.x, self.rect.y

        # Tipo
        type_label = self.font_small.render("Tipo:", True, self.COLORS['text_dim'])
        screen.blit(type_label, (self.event_type_label.x, self.event_type_label.y))

        type_name = self.event.event_type.capitalize()
        pygame.draw.rect(screen, self.COLORS['bg'], self.event_type_display)
        pygame.draw.rect(screen, self.COLORS['border_light'], self.event_type_display, 1)
        type_text = self.font.render(type_name, True, self.COLORS['text'])
        screen.blit(type_text, (self.event_type_display.x + 10, self.event_type_display.y + 4))

        pygame.draw.rect(screen, self.COLORS['bg_light'], self.event_type_prev)
        pygame.draw.rect(screen, self.COLORS['bg_light'], self.event_type_next)
        prev_text = self.font.render("<", True, self.COLORS['text'])
        next_text = self.font.render(">", True, self.COLORS['text'])
        screen.blit(prev_text, (self.event_type_prev.x + 8, self.event_type_prev.y + 5))
        screen.blit(next_text, (self.event_type_next.x + 8, self.event_type_next.y + 5))

        # Delay
        delay_label = self.font_small.render("Delay (s):", True, self.COLORS['text_dim'])
        screen.blit(delay_label, (self.delay_label.x, self.delay_label.y))

        input_color = self.COLORS['input_active'] if self.active_input == "delay" else self.COLORS['input_border']
        pygame.draw.rect(screen, self.COLORS['input_bg'], self.delay_input)
        pygame.draw.rect(screen, input_color, self.delay_input, 1)
        delay_text = self.font.render(self.input_texts.get("delay", "0"), True, self.COLORS['text'])
        screen.blit(delay_text, (self.delay_input.x + 5, self.delay_input.y + 4))

        # Renderiza campos específicos
        self._render_specific_fields(screen)

        # Botões
        pygame.draw.rect(screen, self.COLORS['success'], self.save_button, border_radius=5)
        save_text = self.font.render("Salvar", True, self.COLORS['text'])
        screen.blit(save_text, (self.save_button.x + 20, self.save_button.y + 7))

        pygame.draw.rect(screen, self.COLORS['danger'], self.cancel_button, border_radius=5)
        cancel_text = self.font.render("Cancelar", True, self.COLORS['text'])
        screen.blit(cancel_text, (self.cancel_button.x + 15, self.cancel_button.y + 7))

    def _render_specific_fields(self, screen):
        """Desenha os campos específicos conforme o tipo atual."""
        if self.event.event_type == EventType.MESSAGE:
            label = self.font_small.render("Falante:", True, self.COLORS['text_dim'])
            screen.blit(label, (self.speaker_label.x, self.speaker_label.y))
            self._render_input(screen, self.speaker_input, "speaker_input", self.event.speaker_name)

            label = self.font_small.render("Mensagem:", True, self.COLORS['text_dim'])
            screen.blit(label, (self.message_label.x, self.message_label.y))
            self._render_multiline_input(screen, self.message_input, "message_input", self.event.message_text)

            label = self.font_small.render("Sprite:", True, self.COLORS['text_dim'])
            screen.blit(label, (self.sprite_label.x, self.sprite_label.y))
            self._render_input(screen, self.sprite_input, "sprite_input", self.event.speaker_sprite_path)
            pygame.draw.rect(screen, self.COLORS['accent'], self.sprite_button)
            btn_text = self.font_small.render("Selecionar", True, self.COLORS['text'])
            screen.blit(btn_text, (self.sprite_button.x + 10, self.sprite_button.y + 5))

            label = self.font_small.render("Botão:", True, self.COLORS['text_dim'])
            screen.blit(label, (self.action_label_label.x, self.action_label_label.y))
            self._render_input(screen, self.action_label_input, "action_label_input", self.event.action_label)

            label = self.font_small.render("Ação ao clicar:", True, self.COLORS['text_dim'])
            screen.blit(label, (self.action_trigger_label.x, self.action_trigger_label.y))
            self._render_input(screen, self.action_trigger_input, "action_trigger_input", self.event.action_trigger)

        elif self.event.event_type == EventType.CAMERA:
            label = self.font_small.render("Efeito:", True, self.COLORS['text_dim'])
            screen.blit(label, (self.effect_label.x, self.effect_label.y))
            effect_name = "Tremor" if self.event.camera_effect == CameraEffect.SHAKE else "Flash"
            pygame.draw.rect(screen, self.COLORS['bg'], self.effect_display)
            pygame.draw.rect(screen, self.COLORS['border_light'], self.effect_display, 1)
            text = self.font.render(effect_name, True, self.COLORS['text'])
            screen.blit(text, (self.effect_display.x + 10, self.effect_display.y + 4))
            self._render_nav_buttons(screen, self.effect_prev, self.effect_next)

            label = self.font_small.render("Intensidade:", True, self.COLORS['text_dim'])
            screen.blit(label, (self.intensity_label.x, self.intensity_label.y))
            self._render_input(screen, self.intensity_input, "intensity_input", str(self.event.camera_intensity))

            label = self.font_small.render("Duração (s):", True, self.COLORS['text_dim'])
            screen.blit(label, (self.duration_label.x, self.duration_label.y))
            self._render_input(screen, self.duration_input, "duration_input", str(self.event.camera_duration))

        elif self.event.event_type == EventType.TUTORIAL:
            label = self.font_small.render("Ação:", True, self.COLORS['text_dim'])
            screen.blit(label, (self.tutorial_action_label.x, self.tutorial_action_label.y))
            pygame.draw.rect(screen, self.COLORS['bg'], self.tutorial_action_display)
            pygame.draw.rect(screen, self.COLORS['border_light'], self.tutorial_action_display, 1)
            text = self.font.render(self.event.tutorial_action, True, self.COLORS['text'])
            screen.blit(text, (self.tutorial_action_display.x + 10, self.tutorial_action_display.y + 4))
            self._render_nav_buttons(screen, self.tutorial_action_prev, self.tutorial_action_next)

            label = self.font_small.render("Destaque:", True, self.COLORS['text_dim'])
            screen.blit(label, (self.highlight_label.x, self.highlight_label.y))
            self._render_input(screen, self.highlight_input, "highlight_input", self.event.tutorial_highlight)

        elif self.event.event_type == EventType.GAME_STATE:
            label = self.font_small.render("Ação:", True, self.COLORS['text_dim'])
            screen.blit(label, (self.state_action_label.x, self.state_action_label.y))
            pygame.draw.rect(screen, self.COLORS['bg'], self.state_action_display)
            pygame.draw.rect(screen, self.COLORS['border_light'], self.state_action_display, 1)
            text = self.font.render(self.event.state_action, True, self.COLORS['text'])
            screen.blit(text, (self.state_action_display.x + 10, self.state_action_display.y + 4))
            self._render_nav_buttons(screen, self.state_action_prev, self.state_action_next)

            label = self.font_small.render("Parâmetros:", True, self.COLORS['text_dim'])
            screen.blit(label, (self.state_params_label.x, self.state_params_label.y))
            self._render_input(screen, self.state_params_input, "state_params_input", str(self.event.state_params))

        elif self.event.event_type == EventType.SPAWN:
            label = self.font_small.render("Tipo:", True, self.COLORS['text_dim'])
            screen.blit(label, (self.spawn_type_label.x, self.spawn_type_label.y))
            pygame.draw.rect(screen, self.COLORS['bg'], self.spawn_type_display)
            pygame.draw.rect(screen, self.COLORS['border_light'], self.spawn_type_display, 1)
            text = self.font.render(self.event.spawn_type, True, self.COLORS['text'])
            screen.blit(text, (self.spawn_type_display.x + 10, self.spawn_type_display.y + 4))
            self._render_nav_buttons(screen, self.spawn_type_prev, self.spawn_type_next)

            label = self.font_small.render("Parâmetros:", True, self.COLORS['text_dim'])
            screen.blit(label, (self.spawn_params_label.x, self.spawn_params_label.y))
            self._render_input(screen, self.spawn_params_input, "spawn_params_input", str(self.event.spawn_params))

        elif self.event.event_type == EventType.CUSTOM_ACTION:
            label = self.font_small.render("Nome:", True, self.COLORS['text_dim'])
            screen.blit(label, (self.custom_name_label.x, self.custom_name_label.y))
            self._render_input(screen, self.custom_name_input, "custom_name_input", self.event.custom_action_name)

            label = self.font_small.render("Parâmetros:", True, self.COLORS['text_dim'])
            screen.blit(label, (self.custom_params_label.x, self.custom_params_label.y))
            self._render_input(screen, self.custom_params_input, "custom_params_input", str(self.event.custom_action_params))

    def _render_input(self, screen, rect, field_name, value):
        input_color = self.COLORS['input_active'] if self.active_input == field_name else self.COLORS['input_border']
        pygame.draw.rect(screen, self.COLORS['input_bg'], rect)
        pygame.draw.rect(screen, input_color, rect, 1)
        display_text = self.input_texts.get(field_name, value) if self.active_input == field_name else value
        text = self.font.render(str(display_text), True, self.COLORS['text'])
        screen.blit(text, (rect.x + 5, rect.y + 4))

    def _render_multiline_input(self, screen, rect, field_name, value):
        input_color = self.COLORS['input_active'] if self.active_input == field_name else self.COLORS['input_border']
        pygame.draw.rect(screen, self.COLORS['input_bg'], rect)
        pygame.draw.rect(screen, input_color, rect, 1)
        display_text = self.input_texts.get(field_name, value) if self.active_input == field_name else value
        lines = [str(display_text)[i:i+30] for i in range(0, len(str(display_text)), 30)]
        for i, line in enumerate(lines[:3]):
            text = self.font_small.render(line, True, self.COLORS['text'])
            screen.blit(text, (rect.x + 5, rect.y + 5 + i*18))

    def _render_nav_buttons(self, screen, prev_rect, next_rect):
        prev_color = self.COLORS['bg_light'] if self.active_input is None else self.COLORS['bg']
        next_color = self.COLORS['bg_light'] if self.active_input is None else self.COLORS['bg']
        pygame.draw.rect(screen, prev_color, prev_rect)
        pygame.draw.rect(screen, next_color, next_rect)
        pygame.draw.rect(screen, self.COLORS['border_light'], prev_rect, 1)
        pygame.draw.rect(screen, self.COLORS['border_light'], next_rect, 1)
        prev_text = self.font.render("<", True, self.COLORS['text'])
        next_text = self.font.render(">", True, self.COLORS['text'])
        screen.blit(prev_text, (prev_rect.x + 8, prev_rect.y + 4))
        screen.blit(next_text, (next_rect.x + 8, next_rect.y + 4))