# src/scenes/editor/components/event_config_dialog.py

import pygame
from src.editor.event_system import TriggerType, WaveTriggerState, EventType, CameraEffect, GameEvent

class EventConfigDialog:
    """Diálogo para configurar gatilhos e eventos de uma fase."""

    # Cores padronizadas (use as mesmas do wave_config_dialog)
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
        self.wave_manager = wave_manager  # Para obter o número de waves

        # Estado da UI
        self.dragging = False
        self.drag_offset_x = 0
        self.drag_offset_y = 0
        self.hovered_button = None
        self.active_input = None
        self.input_texts = {}

        # Scroll
        self.triggers_scroll = 0
        self.events_scroll = 0

        # Items por página
        self.triggers_per_page = 5
        self.trigger_item_height = 40
        self.events_per_page = 4
        self.event_item_height = 60

        # Fontes
        self.font_title = pygame.font.Font(None, 24)
        self.font = pygame.font.Font(None, 20)
        self.font_small = pygame.font.Font(None, 16)

        # Inicializa UI
        self._init_ui()

    def _init_ui(self):
        """Inicializa os elementos da UI."""
        x, y, w, h = self.rect
        margin = 20
        content_x = x + margin
        content_y = y + 45  # Espaço para título

        # Área esquerda: Lista de Gatilhos (30% da largura)
        triggers_width = int(w * 0.3)
        triggers_area_x = x + margin
        self.triggers_list_area = pygame.Rect(triggers_area_x, content_y + 35, triggers_width - 10,
                                              self.triggers_per_page * self.trigger_item_height + 5)
        self.add_trigger_button = pygame.Rect(triggers_area_x, content_y + 5, 80, 25)
        self.remove_trigger_button = pygame.Rect(triggers_area_x + 90, content_y + 5, 80, 25)

        # Área direita: Editor de Gatilho (70% da largura)
        editor_width = w - triggers_width - (margin * 2)
        editor_area_x = x + triggers_width + margin
        editor_area_y = content_y  # CORREÇÃO: define o Y como content_y
        self.editor_area = pygame.Rect(editor_area_x, editor_area_y, editor_width, h - 50)

        # Botões de ação (Salvar/Cancelar) - centralizados
        button_width = 80
        button_spacing = 15
        buttons_total_width = (button_width * 2) + button_spacing
        buttons_start_x = x + (w - buttons_total_width) // 2

        self.save_button = pygame.Rect(buttons_start_x, y + h - 40, button_width, 30)
        self.cancel_button = pygame.Rect(buttons_start_x + button_width + button_spacing, y + h - 40, button_width, 30)

        # Elementos do editor (posições relativas ao editor_area)
        self._init_editor_ui(editor_area_x, editor_area_y, editor_width)

    def _init_editor_ui(self, editor_x, editor_y, editor_width):
        """Inicializa os campos do editor de gatilho."""
        margin = 10
        current_y = editor_y + margin

        # Título do gatilho
        self.trigger_title = pygame.Rect(editor_x + margin, current_y, editor_width - (margin * 2), 25)

        # Tipo de gatilho
        current_y += 35
        self.trigger_type_label = pygame.Rect(editor_x + margin, current_y, 80, 25)
        self.trigger_type_display = pygame.Rect(editor_x + margin + 90, current_y, 120, 25)
        self.trigger_type_prev = pygame.Rect(editor_x + margin + 220, current_y, 25, 25)
        self.trigger_type_next = pygame.Rect(editor_x + margin + 250, current_y, 25, 25)

        # Parâmetros (TIME e WAVE)
        current_y += 35

        # TIME: input de segundos
        self.time_label = pygame.Rect(editor_x + margin, current_y, 100, 25)
        self.time_input = pygame.Rect(editor_x + margin + 110, current_y, 100, 25)

        # WAVE: índice e estado - REPOSICIONADOS
        # Primeira linha: índice da wave
        self.wave_index_label = pygame.Rect(editor_x + margin, current_y, 80, 25)
        self.wave_index_display = pygame.Rect(editor_x + margin + 90, current_y, 60, 25)
        self.wave_index_prev = pygame.Rect(editor_x + margin + 160, current_y, 25, 25)
        self.wave_index_next = pygame.Rect(editor_x + margin + 190, current_y, 25, 25)

        # Segunda linha: momento da wave (início/fim)
        current_y += 35
        self.wave_state_label = pygame.Rect(editor_x + margin, current_y, 80, 25)
        self.wave_state_display = pygame.Rect(editor_x + margin + 90, current_y, 100, 25)
        self.wave_state_prev = pygame.Rect(editor_x + margin + 200, current_y, 25, 25)
        self.wave_state_next = pygame.Rect(editor_x + margin + 230, current_y, 25, 25)

        # Área de eventos (lista e botões)
        current_y += 45
        self.events_label = pygame.Rect(editor_x + margin, current_y, 100, 25)
        self.add_event_button = pygame.Rect(editor_x + editor_width - 110, current_y, 90, 25)

        current_y += 30
        # Ajusta altura da lista de eventos
        events_list_height = min(200, self.events_per_page * self.event_item_height + 5)
        self.events_list_area = pygame.Rect(editor_x + margin, current_y, editor_width - (margin * 2),
                                            events_list_height)

    def _update_button_positions(self):
        """Atualiza posições dos botões após arrastar."""
        x, y, w, h = self.rect
        margin = 20

        # Área esquerda
        triggers_width = int(w * 0.3)
        triggers_area_x = x + margin
        content_y = y + 45

        self.triggers_list_area.x = triggers_area_x
        self.triggers_list_area.y = content_y + 35
        self.add_trigger_button.x = triggers_area_x
        self.add_trigger_button.y = content_y + 5
        self.remove_trigger_button.x = triggers_area_x + 90
        self.remove_trigger_button.y = content_y + 5

        # Área direita
        editor_width = w - triggers_width - (margin * 2)
        editor_area_x = x + triggers_width + margin
        editor_area_y = content_y
        self.editor_area.x = editor_area_x
        self.editor_area.y = editor_area_y
        self.editor_area.width = editor_width

        # Re-inicializa os elementos do editor com as novas posições
        self._init_editor_ui(editor_area_x, editor_area_y, editor_width)

        # Botões de ação
        button_width = 80
        button_spacing = 15
        buttons_total_width = (button_width * 2) + button_spacing
        buttons_start_x = x + (w - buttons_total_width) // 2
        self.save_button.x = buttons_start_x
        self.save_button.y = y + h - 40
        self.cancel_button.x = buttons_start_x + button_width + button_spacing
        self.cancel_button.y = y + h - 40

    def handle_event(self, event):
        """Processa eventos do diálogo."""
        if not self.visible:
            return False

        mouse_pos = pygame.mouse.get_pos()
        mouse_x, mouse_y = mouse_pos

        if hasattr(self, 'event_edit_dialog') and self.event_edit_dialog and self.event_edit_dialog.visible:
            result = self.event_edit_dialog.handle_event(event)
            if not self.event_edit_dialog.visible:
                self.event_edit_dialog = None
            return True

        self.hovered_button = None

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
        """Processa clique esquerdo."""
        # Título para arrastar
        title_rect = pygame.Rect(self.rect.x, self.rect.y, self.rect.width, 30)
        if title_rect.collidepoint(mouse_x, mouse_y):
            self.dragging = True
            self.drag_offset_x = mouse_x - self.rect.x
            self.drag_offset_y = mouse_y - self.rect.y
            return True

        # Botões Salvar/Cancelar
        if self.save_button.collidepoint(mouse_x, mouse_y):
            self.visible = False
            return "saved"
        if self.cancel_button.collidepoint(mouse_x, mouse_y):
            self.visible = False
            return True

        # Botões da lista de gatilhos
        if self.add_trigger_button.collidepoint(mouse_x, mouse_y):
            self.event_manager.add_trigger()
            self.triggers_scroll = 0
            self.events_scroll = 0
            self.active_input = None
            return True
        if self.remove_trigger_button.collidepoint(mouse_x, mouse_y):
            self.event_manager.remove_trigger(self.event_manager.selected_trigger)
            self.triggers_scroll = 0
            return True
        if self.triggers_list_area.collidepoint(mouse_x, mouse_y):
            relative_y = mouse_y - self.triggers_list_area.y
            item_index = (relative_y // self.trigger_item_height) + self.triggers_scroll
            if 0 <= item_index < len(self.event_manager.triggers):
                self.event_manager.selected_trigger = item_index
                self.events_scroll = 0
                return True

        # Botões do editor (se houver gatilho selecionado)
        trigger = self.event_manager.get_current_trigger()
        if trigger:
            return self._handle_editor_click(mouse_x, mouse_y, trigger)

        return True

    def _handle_editor_click(self, mouse_x, mouse_y, trigger):
        """Processa cliques no editor do gatilho."""
        # Botões de navegação do tipo de gatilho
        if self.trigger_type_prev.collidepoint(mouse_x, mouse_y):
            self._change_trigger_type(trigger, -1)
            return True
        if self.trigger_type_next.collidepoint(mouse_x, mouse_y):
            self._change_trigger_type(trigger, 1)
            return True

        # Botões de wave index
        if self.wave_index_prev.collidepoint(mouse_x, mouse_y):
            self._change_wave_index(trigger, -1)
            return True
        if self.wave_index_next.collidepoint(mouse_x, mouse_y):
            self._change_wave_index(trigger, 1)
            return True

        # Botões de wave state
        if self.wave_state_prev.collidepoint(mouse_x, mouse_y):
            self._change_wave_state(trigger, -1)
            return True
        if self.wave_state_next.collidepoint(mouse_x, mouse_y):
            self._change_wave_state(trigger, 1)
            return True

        # Input de tempo
        if self.time_input.collidepoint(mouse_x, mouse_y):
            self.active_input = "time"
            self.input_texts["time"] = str(trigger.time_value)
            return True

        # Botão de adicionar evento
        if self.add_event_button.collidepoint(mouse_x, mouse_y):
            # Adiciona um evento de mensagem padrão
            new_event = GameEvent()
            new_event.event_type = EventType.MESSAGE
            new_event.message_text = "Nova mensagem"
            trigger.add_event(new_event)
            return True

        # Lista de eventos (seleção e botões de remover)
        if self.events_list_area.collidepoint(mouse_x, mouse_y):
            relative_y = mouse_y - self.events_list_area.y
            item_index = (relative_y // self.event_item_height) + self.events_scroll
            if 0 <= item_index < len(trigger.events):
                # Verifica se clicou no botão de remover
                event_x = self.events_list_area.x + self.events_list_area.width - 30
                event_y = self.events_list_area.y + 5 + (item_index - self.events_scroll) * self.event_item_height
                remove_rect = pygame.Rect(event_x, event_y, 20, 20)
                if remove_rect.collidepoint(mouse_x, mouse_y):
                    trigger.remove_event(item_index)
                    return True
                # Caso contrário, seleciona o evento para editar (abrirá um sub-diálogo)
                self._open_event_editor(trigger, item_index)
                return True

        return True

    def _change_trigger_type(self, trigger, direction):
        """Muda o tipo do gatilho."""
        types = [TriggerType.TIME, TriggerType.WAVE]
        current_idx = types.index(trigger.trigger_type)
        new_idx = (current_idx + direction) % len(types)
        trigger.trigger_type = types[new_idx]

    def _change_wave_index(self, trigger, direction):
        """Muda o índice da wave."""
        max_wave = max(0, len(self.wave_manager.waves) - 1)
        new_index = trigger.wave_index + direction
        if 0 <= new_index <= max_wave:
            trigger.wave_index = new_index

    def _change_wave_state(self, trigger, direction):
        """Muda o estado da wave (início/fim)."""
        states = [WaveTriggerState.WAVE_START, WaveTriggerState.WAVE_END]
        current_idx = states.index(trigger.wave_state)
        new_idx = (current_idx + direction) % len(states)
        trigger.wave_state = states[new_idx]

    def _open_event_editor(self, trigger, event_index):
        """Abre um sub-diálogo para editar um evento específico."""
        event = trigger.events[event_index]

        # Centraliza o sub-diálogo
        dialog_width = 500
        dialog_height = 400
        dialog_x = self.rect.x + (self.rect.width - dialog_width) // 2
        dialog_y = self.rect.y + (self.rect.height - dialog_height) // 2

        def on_event_saved(updated_event):
            """Callback chamado quando o evento é salvo."""
            # Atualiza o evento no trigger
            trigger.events[event_index] = updated_event
            print(f"Evento atualizado: {updated_event.event_type}")

        self.event_edit_dialog = EventEditDialog(
            dialog_x, dialog_y, dialog_width, dialog_height,
            event, on_event_saved
        )

    def _popup_input(self, prompt, current_text):
        """Popup simples para input de texto (apenas para demonstração)."""
        # Por simplicidade, apenas retorna o texto atual + "editado"
        # Isso pode ser expandido com um diálogo real no futuro.
        return f"{current_text} (editado)"

    def _update_hover(self, mouse_x, mouse_y):
        """Atualiza estado de hover dos botões."""
        buttons = [
            (self.save_button, "save"),
            (self.cancel_button, "cancel"),
            (self.add_trigger_button, "add_trigger"),
            (self.remove_trigger_button, "remove_trigger"),
            (self.add_event_button, "add_event"),
            (self.trigger_type_prev, "trigger_type_prev"),
            (self.trigger_type_next, "trigger_type_next"),
            (self.wave_index_prev, "wave_index_prev"),
            (self.wave_index_next, "wave_index_next"),
            (self.wave_state_prev, "wave_state_prev"),
            (self.wave_state_next, "wave_state_next"),
        ]
        for button, name in buttons:
            if button.collidepoint(mouse_x, mouse_y):
                self.hovered_button = name
                return

    def _handle_scroll(self, direction):
        """Processa scroll do mouse."""
        mouse_pos = pygame.mouse.get_pos()
        if self.triggers_list_area.collidepoint(mouse_pos):
            max_scroll = max(0, len(self.event_manager.triggers) - self.triggers_per_page)
            self.triggers_scroll = max(0, min(max_scroll, self.triggers_scroll - direction))
            return True
        if self.events_list_area.collidepoint(mouse_pos):
            trigger = self.event_manager.get_current_trigger()
            if trigger:
                max_scroll = max(0, len(trigger.events) - self.events_per_page)
                self.events_scroll = max(0, min(max_scroll, self.events_scroll - direction))
            return True
        return False

    def _handle_keydown(self, event):
        """Processa teclas pressionadas em inputs."""
        if event.key == pygame.K_RETURN:
            return self._apply_input()
        elif event.key == pygame.K_ESCAPE:
            self.active_input = None
            return True
        elif event.key == pygame.K_BACKSPACE:
            if self.active_input in self.input_texts:
                self.input_texts[self.active_input] = self.input_texts[self.active_input][:-1]
            return True
        elif event.unicode.isdigit() or event.unicode == '.':
            if self.active_input in self.input_texts:
                self.input_texts[self.active_input] += event.unicode
            return True
        return False

    def _apply_input(self):
        """Aplica o valor do input atual."""
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
        except ValueError:
            pass

        self.active_input = None
        return True

    def render(self, screen):
        """Renderiza o diálogo."""
        if not self.visible:
            return

        # Overlay
        overlay = pygame.Surface((screen.get_width(), screen.get_height()))
        overlay.set_alpha(180)
        overlay.fill((0, 0, 0))
        screen.blit(overlay, (0, 0))

        # Fundo da janela
        pygame.draw.rect(screen, self.COLORS['bg'], self.rect, border_radius=10)
        pygame.draw.rect(screen, self.COLORS['border'], self.rect, 2, border_radius=10)

        # Barra de título (arrastável)
        title_bar = pygame.Rect(self.rect.x, self.rect.y, self.rect.width, 30)
        pygame.draw.rect(screen, self.COLORS['bg_light'], title_bar, border_top_left_radius=10, border_top_right_radius=10)

        title = self.font_title.render("Configuração de Eventos", True, self.COLORS['text'])
        screen.blit(title, (self.rect.x + 10, self.rect.y + 8))

        # Lista de gatilhos (esquerda)
        self._render_triggers_list(screen)

        # Editor do gatilho (direita)
        self._render_trigger_editor(screen)

        # Botões Salvar/Cancelar
        self._render_buttons(screen)

        if hasattr(self, 'event_edit_dialog') and self.event_edit_dialog and self.event_edit_dialog.visible:
            self.event_edit_dialog.render(screen)

    def _render_triggers_list(self, screen):
        """Renderiza a lista de gatilhos."""
        pygame.draw.rect(screen, self.COLORS['bg_dark'], self.triggers_list_area, border_radius=5)

        # Botões
        add_color = self.COLORS['success'] if self.hovered_button == "add_trigger" else (0, 80, 0)
        remove_color = self.COLORS['danger'] if self.hovered_button == "remove_trigger" else (80, 0, 0)

        pygame.draw.rect(screen, add_color, self.add_trigger_button, border_radius=5)
        add_text = self.font_small.render("+ Gatilho", True, self.COLORS['text'])
        add_text_x = self.add_trigger_button.x + (self.add_trigger_button.width - add_text.get_width()) // 2
        add_text_y = self.add_trigger_button.y + (self.add_trigger_button.height - add_text.get_height()) // 2
        screen.blit(add_text, (add_text_x, add_text_y))

        pygame.draw.rect(screen, remove_color, self.remove_trigger_button, border_radius=5)
        remove_text = self.font_small.render("- Remover", True, self.COLORS['text'])
        remove_text_x = self.remove_trigger_button.x + (self.remove_trigger_button.width - remove_text.get_width()) // 2
        remove_text_y = self.remove_trigger_button.y + (self.remove_trigger_button.height - remove_text.get_height()) // 2
        screen.blit(remove_text, (remove_text_x, remove_text_y))

        # Clipping para a lista
        old_clip = screen.get_clip()
        screen.set_clip(self.triggers_list_area)

        list_x = self.triggers_list_area.x + 5
        list_start_y = self.triggers_list_area.y + 2 - self.triggers_scroll * self.trigger_item_height

        for i, trigger in enumerate(self.event_manager.triggers):
            item_y = list_start_y + i * self.trigger_item_height
            if item_y + self.trigger_item_height < self.triggers_list_area.y or item_y > self.triggers_list_area.y + self.triggers_list_area.height:
                continue

            item_rect = pygame.Rect(list_x, item_y, self.triggers_list_area.width - 10, self.trigger_item_height - 4)

            is_selected = (i == self.event_manager.selected_trigger)
            bg_color = self.COLORS['accent'] if is_selected else (self.COLORS['bg_light'] if i % 2 == 0 else self.COLORS['bg'])
            pygame.draw.rect(screen, bg_color, item_rect)

            if is_selected:
                pygame.draw.rect(screen, self.COLORS['border'], item_rect, 1)

            # Descrição do gatilho
            if trigger.trigger_type == TriggerType.TIME:
                desc = f"Tempo: {trigger.time_value}s"
            else:
                state_name = "Início" if trigger.wave_state == WaveTriggerState.WAVE_START else "Fim"
                desc = f"Wave {trigger.wave_index + 1} ({state_name})"

            text = self.font_small.render(desc, True, self.COLORS['text'])
            screen.blit(text, (item_rect.x + 5, item_rect.y + 7))

        screen.set_clip(old_clip)

        # Indicador de scroll
        if len(self.event_manager.triggers) > self.triggers_per_page:
            scroll_text = self.font_small.render(
                f"{self.triggers_scroll + 1}-{min(self.triggers_scroll + self.triggers_per_page, len(self.event_manager.triggers))} de {len(self.event_manager.triggers)}",
                True, self.COLORS['text_dark']
            )
            screen.blit(scroll_text, (self.triggers_list_area.x + 5, self.triggers_list_area.bottom + 5))

    def _render_trigger_editor(self, screen):
        """Renderiza o editor do gatilho selecionado."""
        trigger = self.event_manager.get_current_trigger()
        if not trigger:
            # Mostrar mensagem "Nenhum gatilho selecionado"
            msg = self.font.render("Selecione um gatilho à esquerda", True, self.COLORS['text_dim'])
            msg_rect = msg.get_rect(center=self.editor_area.center)
            screen.blit(msg, msg_rect)
            return

        pygame.draw.rect(screen, self.COLORS['bg_light'], self.editor_area, border_radius=5)
        pygame.draw.rect(screen, self.COLORS['border_light'], self.editor_area, 1, border_radius=5)

        # Título do gatilho
        title_text = self.font.render(f"Gatilho {self.event_manager.selected_trigger + 1}", True, self.COLORS['border'])
        screen.blit(title_text, (self.trigger_title.x, self.trigger_title.y))

        # Tipo de gatilho
        type_label = self.font_small.render("Tipo:", True, self.COLORS['text_dim'])
        screen.blit(type_label, (self.trigger_type_label.x, self.trigger_type_label.y))

        type_name = "Tempo" if trigger.trigger_type == TriggerType.TIME else "Wave"
        type_color = self.COLORS['accent'] if self.hovered_button in ["trigger_type_prev", "trigger_type_next"] else self.COLORS['bg']
        pygame.draw.rect(screen, type_color, self.trigger_type_display)
        pygame.draw.rect(screen, self.COLORS['border_light'], self.trigger_type_display, 1)
        type_text = self.font_small.render(type_name, True, self.COLORS['text'])
        type_text_x = self.trigger_type_display.x + (self.trigger_type_display.width - type_text.get_width()) // 2
        type_text_y = self.trigger_type_display.y + (self.trigger_type_display.height - type_text.get_height()) // 2
        screen.blit(type_text, (type_text_x, type_text_y))

        # Botões de navegação do tipo
        self._render_nav_buttons(screen, self.trigger_type_prev, self.trigger_type_next)

        # Parâmetros específicos
        if trigger.trigger_type == TriggerType.TIME:
            self._render_time_editor(screen, trigger)
        else:
            self._render_wave_editor(screen, trigger)

        # Área de eventos
        self._render_events_list(screen, trigger)

    def _render_time_editor(self, screen, trigger):
        """Renderiza os campos para gatilho de tempo."""
        label = self.font_small.render("Tempo (s):", True, self.COLORS['text_dim'])
        screen.blit(label, (self.time_label.x, self.time_label.y))

        input_color = self.COLORS['input_active'] if self.active_input == "time" else self.COLORS['input_border']
        pygame.draw.rect(screen, self.COLORS['input_bg'], self.time_input)
        pygame.draw.rect(screen, input_color, self.time_input, 1)

        time_text = self.input_texts.get("time", f"{trigger.time_value:.1f}") if self.active_input == "time" else f"{trigger.time_value:.1f}"
        text = self.font_small.render(time_text, True, self.COLORS['text'])
        screen.blit(text, (self.time_input.x + 5, self.time_input.y + 4))

    def _render_wave_editor(self, screen, trigger):
        """Renderiza os campos para gatilho de wave."""
        # Índice da wave
        index_label = self.font_small.render("Wave:", True, self.COLORS['text_dim'])
        screen.blit(index_label, (self.wave_index_label.x, self.wave_index_label.y))

        index_color = self.COLORS['bg'] if self.hovered_button in ["wave_index_prev", "wave_index_next"] else self.COLORS['bg']
        pygame.draw.rect(screen, index_color, self.wave_index_display)
        pygame.draw.rect(screen, self.COLORS['border_light'], self.wave_index_display, 1)

        index_text = self.font_small.render(str(trigger.wave_index + 1), True, self.COLORS['text'])
        index_text_x = self.wave_index_display.x + (self.wave_index_display.width - index_text.get_width()) // 2
        index_text_y = self.wave_index_display.y + (self.wave_index_display.height - index_text.get_height()) // 2
        screen.blit(index_text, (index_text_x, index_text_y))

        # Botões de navegação do índice
        self._render_nav_buttons(screen, self.wave_index_prev, self.wave_index_next)

        # Estado da wave
        state_label = self.font_small.render("Momento:", True, self.COLORS['text_dim'])
        screen.blit(state_label, (self.wave_state_label.x, self.wave_state_label.y))

        state_name = "Início" if trigger.wave_state == WaveTriggerState.WAVE_START else "Fim"
        state_color = self.COLORS['bg'] if self.hovered_button in ["wave_state_prev", "wave_state_next"] else self.COLORS['bg']
        pygame.draw.rect(screen, state_color, self.wave_state_display)
        pygame.draw.rect(screen, self.COLORS['border_light'], self.wave_state_display, 1)

        state_text = self.font_small.render(state_name, True, self.COLORS['text'])
        state_text_x = self.wave_state_display.x + (self.wave_state_display.width - state_text.get_width()) // 2
        state_text_y = self.wave_state_display.y + (self.wave_state_display.height - state_text.get_height()) // 2
        screen.blit(state_text, (state_text_x, state_text_y))

        # Botões de navegação do estado
        self._render_nav_buttons(screen, self.wave_state_prev, self.wave_state_next)

    def _render_events_list(self, screen, trigger):
        """Renderiza a lista de eventos do gatilho."""
        # Título e botão adicionar
        title = self.font_small.render("Eventos:", True, self.COLORS['text_dim'])
        screen.blit(title, (self.events_label.x, self.events_label.y))

        add_color = self.COLORS['success'] if self.hovered_button == "add_event" else (0, 80, 0)
        pygame.draw.rect(screen, add_color, self.add_event_button, border_radius=5)
        add_text = self.font_small.render("+ Evento", True, self.COLORS['text'])
        add_text_x = self.add_event_button.x + (self.add_event_button.width - add_text.get_width()) // 2
        add_text_y = self.add_event_button.y + (self.add_event_button.height - add_text.get_height()) // 2
        screen.blit(add_text, (add_text_x, add_text_y))

        # Área da lista
        pygame.draw.rect(screen, self.COLORS['bg_dark'], self.events_list_area, border_radius=5)

        # Clipping
        old_clip = screen.get_clip()
        screen.set_clip(self.events_list_area)

        list_x = self.events_list_area.x + 5
        list_start_y = self.events_list_area.y + 2 - self.events_scroll * self.event_item_height

        for i, event in enumerate(trigger.events):
            item_y = list_start_y + i * self.event_item_height
            if item_y + self.event_item_height < self.events_list_area.y or item_y > self.events_list_area.y + self.events_list_area.height:
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
            if event.event_type == EventType.MESSAGE:
                desc = f"MENSAGEM: {event.message_text[:30]}"
                if len(event.message_text) > 30:
                    desc += "..."
            else:
                effect_name = "Tremor" if event.camera_effect == CameraEffect.SHAKE else "Flash"
                desc = f"CÂMERA: {effect_name} (intensidade {event.camera_intensity}, duração {event.camera_duration}s)"

            text = self.font_small.render(desc, True, self.COLORS['text'])
            screen.blit(text, (item_rect.x + 5, item_rect.y + 5))

            # Delay
            delay_text = self.font_small.render(f"Delay: {event.delay}s", True, self.COLORS['text_dim'])
            screen.blit(delay_text, (item_rect.x + 5, item_rect.y + 25))

        screen.set_clip(old_clip)

        # Indicador de scroll
        if len(trigger.events) > self.events_per_page:
            scroll_text = self.font_small.render(
                f"{self.events_scroll + 1}-{min(self.events_scroll + self.events_per_page, len(trigger.events))} de {len(trigger.events)}",
                True, self.COLORS['text_dark']
            )
            screen.blit(scroll_text, (self.events_list_area.x + 5, self.events_list_area.bottom + 5))

    def _render_nav_buttons(self, screen, prev_rect, next_rect):
        """Renderiza botões de navegação < e >."""
        prev_color = self.COLORS['bg_light'] if self.hovered_button == "trigger_type_prev" else (60, 60, 70)
        next_color = self.COLORS['bg_light'] if self.hovered_button == "trigger_type_next" else (60, 60, 70)

        pygame.draw.rect(screen, prev_color, prev_rect)
        pygame.draw.rect(screen, next_color, next_rect)
        pygame.draw.rect(screen, self.COLORS['border_light'], prev_rect, 1)
        pygame.draw.rect(screen, self.COLORS['border_light'], next_rect, 1)

        prev_text = self.font_small.render("<", True, self.COLORS['text'])
        next_text = self.font_small.render(">", True, self.COLORS['text'])
        prev_text_x = prev_rect.x + (prev_rect.width - prev_text.get_width()) // 2
        prev_text_y = prev_rect.y + (prev_rect.height - prev_text.get_height()) // 2
        next_text_x = next_rect.x + (next_rect.width - next_text.get_width()) // 2
        next_text_y = next_rect.y + (next_rect.height - next_text.get_height()) // 2
        screen.blit(prev_text, (prev_text_x, prev_text_y))
        screen.blit(next_text, (next_text_x, next_text_y))

    def _render_buttons(self, screen):
        """Renderiza os botões Salvar e Cancelar."""
        save_color = self.COLORS['success'] if self.hovered_button == "save" else (0, 100, 0)
        cancel_color = self.COLORS['danger'] if self.hovered_button == "cancel" else (100, 0, 0)

        pygame.draw.rect(screen, save_color, self.save_button, border_radius=5)
        pygame.draw.rect(screen, self.COLORS['text'], self.save_button, 1, border_radius=5)
        save_text = self.font.render("Salvar", True, self.COLORS['text'])
        save_x = self.save_button.x + (self.save_button.width - save_text.get_width()) // 2
        save_y = self.save_button.y + (self.save_button.height - save_text.get_height()) // 2
        screen.blit(save_text, (save_x, save_y))

        pygame.draw.rect(screen, cancel_color, self.cancel_button, border_radius=5)
        pygame.draw.rect(screen, self.COLORS['text'], self.cancel_button, 1, border_radius=5)
        cancel_text = self.font.render("Cancelar", True, self.COLORS['text'])
        cancel_x = self.cancel_button.x + (self.cancel_button.width - cancel_text.get_width()) // 2
        cancel_y = self.cancel_button.y + (self.cancel_button.height - cancel_text.get_height()) // 2
        screen.blit(cancel_text, (cancel_x, cancel_y))

class EventEditDialog:
    """Sub-diálogo para editar um evento específico."""

    COLORS = EventConfigDialog.COLORS  # Reusa as mesmas cores

    def __init__(self, x, y, width, height, event, callback):
        self.rect = pygame.Rect(x, y, width, height)
        self.visible = True
        self.event = event
        self.callback = callback  # Função chamada ao salvar

        self.dragging = False
        self.drag_offset_x = 0
        self.drag_offset_y = 0
        self.active_input = None
        self.input_texts = {}

        # Fontes
        self.font_title = pygame.font.Font(None, 24)
        self.font = pygame.font.Font(None, 20)
        self.font_small = pygame.font.Font(None, 16)

        # Botões
        self.save_button = pygame.Rect(x + width - 180, y + height - 45, 80, 30)
        self.cancel_button = pygame.Rect(x + width - 90, y + height - 45, 80, 30)

        # Campos do formulário
        self._init_fields()

    def _init_fields(self):
        x, y, w, h = self.rect
        margin = 20
        current_y = y + 50

        # Tipo de evento
        self.event_type_label = pygame.Rect(x + margin, current_y, 100, 25)
        self.event_type_display = pygame.Rect(x + margin + 110, current_y, 150, 25)
        self.event_type_prev = pygame.Rect(x + margin + 270, current_y, 25, 25)
        self.event_type_next = pygame.Rect(x + margin + 300, current_y, 25, 25)

        current_y += 40

        # Delay
        self.delay_label = pygame.Rect(x + margin, current_y, 100, 25)
        self.delay_input = pygame.Rect(x + margin + 110, current_y, 100, 25)

        current_y += 40

        # Campos específicos por tipo
        # MENSAGEM
        self.speaker_label = pygame.Rect(x + margin, current_y, 100, 25)
        self.speaker_input = pygame.Rect(x + margin + 110, current_y, 250, 25)

        current_y += 40
        self.message_label = pygame.Rect(x + margin, current_y, 100, 25)
        self.message_input = pygame.Rect(x + margin + 110, current_y, 250, 60)

        current_y += 70
        self.sprite_label = pygame.Rect(x + margin, current_y, 100, 25)
        self.sprite_display = pygame.Rect(x + margin + 110, current_y, 200, 25)
        self.sprite_button = pygame.Rect(x + margin + 320, current_y, 80, 25)

        # CÂMERA
        self.effect_label = pygame.Rect(x + margin, current_y, 100, 25)
        self.effect_display = pygame.Rect(x + margin + 110, current_y, 120, 25)
        self.effect_prev = pygame.Rect(x + margin + 240, current_y, 25, 25)
        self.effect_next = pygame.Rect(x + margin + 270, current_y, 25, 25)

        current_y += 40
        self.intensity_label = pygame.Rect(x + margin, current_y, 100, 25)
        self.intensity_input = pygame.Rect(x + margin + 110, current_y, 80, 25)

        current_y += 40
        self.duration_label = pygame.Rect(x + margin, current_y, 100, 25)
        self.duration_input = pygame.Rect(x + margin + 110, current_y, 80, 25)

        # Inicializa valores
        self._load_event_values()

    def _load_event_values(self):
        """Carrega os valores do evento nos inputs."""
        self.input_texts["delay"] = str(self.event.delay)

        if self.event.event_type == EventType.MESSAGE:
            self.input_texts["speaker"] = self.event.speaker_name
            self.input_texts["message"] = self.event.message_text
            self.input_texts["sprite"] = self.event.speaker_sprite_path
        else:
            self.input_texts["intensity"] = str(self.event.camera_intensity)
            self.input_texts["duration"] = str(self.event.camera_duration)

    def handle_event(self, event):
        """Processa eventos do sub-diálogo."""
        if not self.visible:
            return False

        mouse_pos = pygame.mouse.get_pos()
        mouse_x, mouse_y = mouse_pos

        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            if not self.rect.collidepoint(mouse_x, mouse_y):
                return False  # Não fecha ao clicar fora
            return self._handle_left_click(mouse_x, mouse_y)

        elif event.type == pygame.MOUSEBUTTONUP and event.button == 1:
            self.dragging = False
            return True

        elif event.type == pygame.MOUSEMOTION:
            if self.dragging:
                self.rect.x = mouse_x - self.drag_offset_x
                self.rect.y = mouse_y - self.drag_offset_y
                self._update_button_positions()
                return True

        elif event.type == pygame.KEYDOWN and self.active_input:
            return self._handle_keydown(event)

        return True

    def _handle_left_click(self, mouse_x, mouse_y):
        """Processa clique esquerdo."""
        # Arrastar
        title_rect = pygame.Rect(self.rect.x, self.rect.y, self.rect.width, 30)
        if title_rect.collidepoint(mouse_x, mouse_y):
            self.dragging = True
            self.drag_offset_x = mouse_x - self.rect.x
            self.drag_offset_y = mouse_y - self.rect.y
            return True

        # Botões
        if self.save_button.collidepoint(mouse_x, mouse_y):
            self._save_event()
            self.visible = False
            if self.callback:
                self.callback(self.event)
            return True

        if self.cancel_button.collidepoint(mouse_x, mouse_y):
            self.visible = False
            return True

        # Tipo de evento
        if self.event_type_prev.collidepoint(mouse_x, mouse_y):
            self._change_event_type(-1)
            return True
        if self.event_type_next.collidepoint(mouse_x, mouse_y):
            self._change_event_type(1)
            return True

        # Campos
        if self.delay_input.collidepoint(mouse_x, mouse_y):
            self.active_input = "delay"
            return True

        if self.event.event_type == EventType.MESSAGE:
            if self.speaker_input.collidepoint(mouse_x, mouse_y):
                self.active_input = "speaker"
                return True
            if self.message_input.collidepoint(mouse_x, mouse_y):
                self.active_input = "message"
                return True
            if self.sprite_button.collidepoint(mouse_x, mouse_y):
                self._select_sprite()
                return True
        else:
            if self.effect_prev.collidepoint(mouse_x, mouse_y):
                self._change_effect(-1)
                return True
            if self.effect_next.collidepoint(mouse_x, mouse_y):
                self._change_effect(1)
                return True
            if self.intensity_input.collidepoint(mouse_x, mouse_y):
                self.active_input = "intensity"
                return True
            if self.duration_input.collidepoint(mouse_x, mouse_y):
                self.active_input = "duration"
                return True

        return True

    def _change_event_type(self, direction):
        """Muda o tipo do evento."""
        types = [EventType.MESSAGE, EventType.CAMERA]
        current_idx = types.index(self.event.event_type)
        new_idx = (current_idx + direction) % len(types)
        self.event.event_type = types[new_idx]

    def _change_effect(self, direction):
        """Muda o efeito de câmera."""
        effects = [CameraEffect.SHAKE, CameraEffect.FLASH]
        current_idx = effects.index(self.event.camera_effect)
        new_idx = (current_idx + direction) % len(effects)
        self.event.camera_effect = effects[new_idx]

    def _select_sprite(self):
        """Abre seletor de sprite."""
        from tkinter import filedialog, Tk
        root = Tk()
        root.withdraw()

        file_path = filedialog.askopenfilename(
            title="Selecione o sprite do personagem",
            filetypes=[("Image files", "*.png *.jpg *.jpeg *.bmp *.gif")]
        )

        if file_path:
            self.event.speaker_sprite_path = file_path
            self.input_texts["sprite"] = file_path

    def _save_event(self):
        """Salva os valores do evento."""
        try:
            self.event.delay = float(self.input_texts.get("delay", "0"))
        except ValueError:
            self.event.delay = 0

        if self.event.event_type == EventType.MESSAGE:
            self.event.speaker_name = self.input_texts.get("speaker", "")
            self.event.message_text = self.input_texts.get("message", "")
            self.event.speaker_sprite_path = self.input_texts.get("sprite", "")
        else:
            try:
                self.event.camera_intensity = float(self.input_texts.get("intensity", "5"))
            except ValueError:
                self.event.camera_intensity = 5
            try:
                self.event.camera_duration = float(self.input_texts.get("duration", "0.5"))
            except ValueError:
                self.event.camera_duration = 0.5

    def _handle_keydown(self, event):
        """Processa teclas."""
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

    def _update_button_positions(self):
        """Atualiza posições dos botões."""
        x, y, w, h = self.rect
        self.save_button.x = x + w - 180
        self.save_button.y = y + h - 45
        self.cancel_button.x = x + w - 90
        self.cancel_button.y = y + h - 45

    def render(self, screen):
        """Renderiza o sub-diálogo."""
        if not self.visible:
            return

        # Overlay mais escuro para destacar
        overlay = pygame.Surface((screen.get_width(), screen.get_height()))
        overlay.set_alpha(200)
        overlay.fill((0, 0, 0))
        screen.blit(overlay, (0, 0))

        # Fundo
        pygame.draw.rect(screen, self.COLORS['bg'], self.rect, border_radius=10)
        pygame.draw.rect(screen, self.COLORS['border'], self.rect, 2, border_radius=10)

        # Título
        title_bar = pygame.Rect(self.rect.x, self.rect.y, self.rect.width, 30)
        pygame.draw.rect(screen, self.COLORS['bg_light'], title_bar,
                         border_top_left_radius=10, border_top_right_radius=10)
        title = self.font_title.render("Editar Evento", True, self.COLORS['text'])
        screen.blit(title, (self.rect.x + 10, self.rect.y + 8))

        x, y = self.rect.x, self.rect.y
        margin = 20
        current_y = y + 50

        # Tipo de evento
        type_label = self.font_small.render("Tipo:", True, self.COLORS['text_dim'])
        screen.blit(type_label, (self.event_type_label.x, self.event_type_label.y))

        type_name = "Mensagem" if self.event.event_type == EventType.MESSAGE else "Câmera"
        pygame.draw.rect(screen, self.COLORS['bg'], self.event_type_display)
        pygame.draw.rect(screen, self.COLORS['border_light'], self.event_type_display, 1)
        type_text = self.font.render(type_name, True, self.COLORS['text'])
        type_text_x = self.event_type_display.x + (self.event_type_display.width - type_text.get_width()) // 2
        screen.blit(type_text, (type_text_x, self.event_type_display.y + 4))

        # Botões tipo
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

        # Campos específicos
        if self.event.event_type == EventType.MESSAGE:
            # Speaker
            speaker_label = self.font_small.render("Falante:", True, self.COLORS['text_dim'])
            screen.blit(speaker_label, (self.speaker_label.x, self.speaker_label.y))

            input_color = self.COLORS['input_active'] if self.active_input == "speaker" else self.COLORS['input_border']
            pygame.draw.rect(screen, self.COLORS['input_bg'], self.speaker_input)
            pygame.draw.rect(screen, input_color, self.speaker_input, 1)
            speaker_text = self.font.render(self.input_texts.get("speaker", ""), True, self.COLORS['text'])
            screen.blit(speaker_text, (self.speaker_input.x + 5, self.speaker_input.y + 4))

            # Mensagem
            message_label = self.font_small.render("Mensagem:", True, self.COLORS['text_dim'])
            screen.blit(message_label, (self.message_label.x, self.message_label.y))

            input_color = self.COLORS['input_active'] if self.active_input == "message" else self.COLORS['input_border']
            pygame.draw.rect(screen, self.COLORS['input_bg'], self.message_input)
            pygame.draw.rect(screen, input_color, self.message_input, 1)

            # Quebra de linha manual para mensagens longas
            message = self.input_texts.get("message", "")
            lines = [message[i:i + 30] for i in range(0, len(message), 30)]
            for i, line in enumerate(lines[:2]):  # Mostra até 2 linhas
                msg_text = self.font_small.render(line, True, self.COLORS['text'])
                screen.blit(msg_text, (self.message_input.x + 5, self.message_input.y + 5 + i * 18))

            # Sprite
            sprite_label = self.font_small.render("Sprite:", True, self.COLORS['text_dim'])
            screen.blit(sprite_label, (self.sprite_label.x, self.sprite_label.y))

            pygame.draw.rect(screen, self.COLORS['input_bg'], self.sprite_display)
            pygame.draw.rect(screen, self.COLORS['border_light'], self.sprite_display, 1)
            sprite_path = self.input_texts.get("sprite", "")
            sprite_short = sprite_path.split("/")[-1] if sprite_path else "Nenhum"
            sprite_text = self.font_small.render(sprite_short[:25], True, self.COLORS['text'])
            screen.blit(sprite_text, (self.sprite_display.x + 5, self.sprite_display.y + 4))

            pygame.draw.rect(screen, self.COLORS['accent'], self.sprite_button)
            button_text = self.font_small.render("Selecionar", True, self.COLORS['text'])
            screen.blit(button_text, (self.sprite_button.x + 12, self.sprite_button.y + 5))

        else:  # CÂMERA
            # Efeito
            effect_label = self.font_small.render("Efeito:", True, self.COLORS['text_dim'])
            screen.blit(effect_label, (self.effect_label.x, self.effect_label.y))

            effect_name = "Tremor" if self.event.camera_effect == CameraEffect.SHAKE else "Flash"
            pygame.draw.rect(screen, self.COLORS['bg'], self.effect_display)
            pygame.draw.rect(screen, self.COLORS['border_light'], self.effect_display, 1)
            effect_text = self.font.render(effect_name, True, self.COLORS['text'])
            screen.blit(effect_text, (self.effect_display.x + 20, self.effect_display.y + 4))

            pygame.draw.rect(screen, self.COLORS['bg_light'], self.effect_prev)
            pygame.draw.rect(screen, self.COLORS['bg_light'], self.effect_next)
            screen.blit(prev_text, (self.effect_prev.x + 8, self.effect_prev.y + 5))
            screen.blit(next_text, (self.effect_next.x + 8, self.effect_next.y + 5))

            # Intensidade
            intensity_label = self.font_small.render("Intensidade:", True, self.COLORS['text_dim'])
            screen.blit(intensity_label, (self.intensity_label.x, self.intensity_label.y))

            input_color = self.COLORS['input_active'] if self.active_input == "intensity" else self.COLORS[
                'input_border']
            pygame.draw.rect(screen, self.COLORS['input_bg'], self.intensity_input)
            pygame.draw.rect(screen, input_color, self.intensity_input, 1)
            intensity_text = self.font.render(self.input_texts.get("intensity", "5"), True, self.COLORS['text'])
            screen.blit(intensity_text, (self.intensity_input.x + 5, self.intensity_input.y + 4))

            # Duração
            duration_label = self.font_small.render("Duração (s):", True, self.COLORS['text_dim'])
            screen.blit(duration_label, (self.duration_label.x, self.duration_label.y))

            input_color = self.COLORS['input_active'] if self.active_input == "duration" else self.COLORS[
                'input_border']
            pygame.draw.rect(screen, self.COLORS['input_bg'], self.duration_input)
            pygame.draw.rect(screen, input_color, self.duration_input, 1)
            duration_text = self.font.render(self.input_texts.get("duration", "0.5"), True, self.COLORS['text'])
            screen.blit(duration_text, (self.duration_input.x + 5, self.duration_input.y + 4))

        # Botões
        pygame.draw.rect(screen, self.COLORS['success'], self.save_button, border_radius=5)
        save_text = self.font.render("Salvar", True, self.COLORS['text'])
        screen.blit(save_text, (self.save_button.x + 20, self.save_button.y + 7))

        pygame.draw.rect(screen, self.COLORS['danger'], self.cancel_button, border_radius=5)
        cancel_text = self.font.render("Cancelar", True, self.COLORS['text'])
        screen.blit(cancel_text, (self.cancel_button.x + 15, self.cancel_button.y + 7))