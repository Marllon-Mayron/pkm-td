# src/scenes/game_scene/components/managers/event_processor.py

import pygame
from src.editor.event_system import TriggerType, EventType, TutorialAction, GameStateAction, SpawnAction


class EventProcessor:
    def __init__(self, game_scene):
        self.game_scene = game_scene
        self.event_manager = game_scene.event_manager  # vindo da fase
        self.triggers = self.event_manager.triggers if self.event_manager else []
        self.triggered = [False] * len(self.triggers)  # controle de ativação única

        # estado interno para condições
        self.boss_spawned = False
        self.boss_defeated = False
        self.wave_completed = False
        self.waves_ended = []
        self.custom_flags = {}   # para condições customizadas

        self.pending_events = []  # eventos agendados com delay
        self.current_dialog = None  # para mensagem com botão

        # Controle de pausa
        self.paused = False
        self._pause_until_event_complete = False
        self._waiting_for_resume = False
        self._pending_resume_timer = 0.0

    def start_wave(self):
        """Inicia a wave manualmente (chamado quando o tutorial permite)."""
        if not self.game_scene.wave_manager.has_more_waves():
            return

        # Verifica se todos os triggers customizados já foram processados
        # ou se não há mais triggers pendentes
        all_custom_triggered = True
        for trigger in self.triggers:
            if trigger.trigger_type == TriggerType.CUSTOM:
                # Pula triggers que já foram ativados
                idx = self.triggers.index(trigger)
                if not self.triggered[idx]:
                    all_custom_triggered = False
                    break

        # Se ainda há triggers CUSTOM pendentes, não inicia a wave
        if not all_custom_triggered:
            print(f"[EVENT] Ainda há triggers CUSTOM pendentes. Wave não iniciada.")
            return

        self.game_scene.game_state = "in_wave"
        self.game_scene.wave_manager.start_all_waves()
        print("[EVENT] Wave iniciada após tutorial!")

    def update(self, dt):
        # Verifica se está esperando para despausar (após efeito de câmera, etc.)
        if getattr(self, '_waiting_for_resume', False):
            self._pending_resume_timer -= dt
            if self._pending_resume_timer <= 0:
                self._resume_after_event()
                self._waiting_for_resume = False

        # Se está pausado por um evento, não processa novos eventos
        if getattr(self, '_pause_until_event_complete', False):
            if self.current_dialog:
                self.current_dialog.update(dt)
            return

        # Atualiza eventos agendados
        self._update_pending_events(dt)

        # Verifica triggers se não houver diálogo ativo
        if not self.current_dialog:
            self._check_triggers()

    def _check_triggers(self):
        """Verifica todos os triggers, ativando aqueles cujas condições são satisfeitas e respeitando a ordem dos CUSTOM."""
        # Loop até que nenhum novo trigger seja ativado
        activated = True
        while activated:
            activated = False
            for i, trigger in enumerate(self.triggers):
                if self.triggered[i]:
                    continue
                if self._evaluate_trigger(trigger, i):
                    self.triggered[i] = True
                    self._schedule_events(trigger.events)
                    activated = True
                    # Se ativou um trigger, pode ter desbloqueado outros, então reinicia o loop
                    break  # Sai do for e recomeça o while

    def _evaluate_trigger(self, trigger, index):
        """
        Avalia se um trigger deve ser ativado.
        Retorna True se a condição for satisfeita e a ordem permitir.
        """
        # ===== START_PHASE =====
        if trigger.trigger_type == TriggerType.START_PHASE:
            # Executado logo no início da fase
            return True

        # ===== BEFORE_BOSS =====
        elif trigger.trigger_type == TriggerType.BEFORE_BOSS:
            # Verifica se o boss ainda não foi spawnado e a próxima wave é a do boss
            return not self.boss_spawned and self.game_scene.wave_manager.is_next_wave_boss()

        # ===== AFTER_BOSS_DEFEAT =====
        elif trigger.trigger_type == TriggerType.AFTER_BOSS_DEFEAT:
            is_boss_defeated = self.game_scene.wave_manager.is_boss_defeated()
            is_phase_completed = self.game_scene.game_state == "completed"
            if is_boss_defeated and not is_phase_completed:
                print(f"[EVENT] Trigger AFTER_BOSS_DEFEAT ativado! Boss derrotado, fase não completada.")
                return True
            return False

        # ===== AFTER_WAVE =====
        elif trigger.trigger_type == TriggerType.AFTER_WAVE:
            wave_idx = trigger.wave_index
            if wave_idx not in self.waves_ended:
                if self.game_scene.wave_manager.is_wave_completed(wave_idx):
                    self.waves_ended.append(wave_idx)
                    print(f"[EVENT] Trigger AFTER_WAVE {wave_idx} ativado!")
                    return True
            return False

        # ===== CUSTOM =====
        elif trigger.trigger_type == TriggerType.CUSTOM:
            # Verifica se a flag customizada existe e é True
            result = self.custom_flags.get(trigger.custom_condition, False)
            if result:
                # Verifica se todos os CUSTOM anteriores já foram ativados
                if self._can_activate_custom(index):
                    print(f"[EVENT] Trigger CUSTOM '{trigger.custom_condition}' ativado em ordem!")
                    return True
                else:
                    print(f"[EVENT] Trigger CUSTOM '{trigger.custom_condition}' ignorado (ordem não respeitada)")
                    return False
            return False

        # ===== TIME =====
        elif trigger.trigger_type == TriggerType.TIME:
            # TODO: Implementar lógica de tempo se necessário
            return False

        # ===== WAVE =====
        elif trigger.trigger_type == TriggerType.WAVE:
            # TODO: Implementar lógica de início/fim de wave se necessário
            return False

        return False

    def _can_activate_custom(self, current_index):
        """
        Verifica se todos os gatilhos CUSTOM com índice menor que current_index
        já foram ativados (self.triggered[i] == True).
        """
        for i in range(current_index):
            trigger = self.triggers[i]
            if trigger.trigger_type == TriggerType.CUSTOM and not self.triggered[i]:
                return False
        return True

    def get_next_custom_flag(self):
        """
        Retorna o custom_condition do próximo trigger CUSTOM não ativado,
        ou None se todos já foram ativados ou não houver mais.
        """
        for i, trigger in enumerate(self.triggers):
            if trigger.trigger_type == TriggerType.CUSTOM and not self.triggered[i]:
                # Verifica se todos os anteriores já foram ativados
                if self._can_activate_custom(i):
                    return trigger.custom_condition
                else:
                    # Se algum anterior não foi ativado, o próximo válido é o primeiro pendente
                    # Vamos retornar o custom_condition do primeiro que está bloqueado
                    for j in range(i):
                        if self.triggers[j].trigger_type == TriggerType.CUSTOM and not self.triggered[j]:
                            return self.triggers[j].custom_condition
                    return trigger.custom_condition
        return None

    def _schedule_events(self, events):
        for event in events:
            self.pending_events.append({
                'event': event,
                'timer': event.delay,
                'executed': False
            })

    def _update_pending_events(self, dt):
        to_remove = []
        for i, entry in enumerate(self.pending_events):
            if entry['executed']:
                continue
            entry['timer'] -= dt
            if entry['timer'] <= 0:
                self._execute_event(entry['event'])
                entry['executed'] = True
                to_remove.append(i)
        for i in reversed(to_remove):
            self.pending_events.pop(i)

    def _execute_event(self, event):
        """
        Executa um evento individual.
        Se o evento tiver pause_game=True, pausa o processamento da wave/jogo.
        """
        # ===== VERIFICA PAUSA =====
        if hasattr(event, 'pause_game') and event.pause_game:
            # Pausa o wave_manager e o jogo
            self.game_scene.wave_manager.paused = True
            self.game_scene.paused = True
            self.paused = True
            self._pause_until_event_complete = True
            print(f"[EVENT] Evento pausou o jogo: {event.event_type}")

        # ===== EXECUTA O EVENTO =====
        if event.event_type == EventType.MESSAGE:
            self._show_message(event)
        elif event.event_type == EventType.TUTORIAL:
            self._execute_tutorial(event)
        elif event.event_type == EventType.GAME_STATE:
            self._execute_game_state(event)
        elif event.event_type == EventType.SPAWN:
            self._execute_spawn(event)
        elif event.event_type == EventType.CUSTOM_ACTION:
            self._execute_custom_action(event)
        elif event.event_type == EventType.CAMERA:
            self._execute_camera(event)
        else:
            print(f"[EVENT] Tipo de evento desconhecido: {event.event_type}")
            # Se for desconhecido e pausou, despausa
            if hasattr(event, 'pause_game') and event.pause_game:
                self._resume_after_event()

    def _resume_after_event(self):
        """Despausa o jogo após um evento com pause_game ser concluído."""
        if getattr(self, '_pause_until_event_complete', False):
            self.game_scene.wave_manager.paused = False
            self.game_scene.paused = False
            self.paused = False
            self._pause_until_event_complete = False
            print(f"[EVENT] Jogo despausado após evento")

    def _show_message(self, event):
        """Cria um diálogo com botão de ação."""
        from src.scenes.game_scene.components.overlays.dialog_overlay import DialogOverlay

        # Callback que será executado quando o botão for clicado
        def on_action():
            self._on_dialog_action(event.action_trigger)

        self.current_dialog = DialogOverlay(
            self.game_scene,
            text=event.message_text,
            speaker=event.speaker_name,
            sprite_path=event.speaker_sprite_path,
            action_label=event.action_label or "OK",
            action_callback=on_action
        )

    def _on_dialog_action(self, action_name):
        """Executa ação após clique no botão do diálogo."""
        self.current_dialog = None
        self._execute_action_by_name(action_name)

        # Se estava pausado por este evento, despausa
        self._resume_after_event()

        # ===== VERIFICA SE DEVE INICIAR A WAVE =====
        # Só inicia a wave se:
        # 1. O jogo está em estado "waiting"
        # 2. Não há mais triggers CUSTOM pendentes
        # 3. O trigger START_PHASE já foi processado
        if (self.game_scene.game_state == "waiting" and
                self.triggered[0]):  # START_PHASE foi processado

            # Verifica se ainda há triggers CUSTOM pendentes
            has_custom_pending = False
            for i, trigger in enumerate(self.triggers):
                if trigger.trigger_type == TriggerType.CUSTOM and not self.triggered[i]:
                    has_custom_pending = True
                    break

            if not has_custom_pending:
                # Se não há mais triggers CUSTOM, inicia a wave
                self.start_wave()
            else:
                print(f"[EVENT] Aguardando triggers CUSTOM pendentes antes de iniciar wave")

    def _execute_action_by_name(self, action_name):
        """Executa uma ação pelo nome (definido no action_trigger do evento)."""
        if action_name == "open_bag":
            self.game_scene.item_bag_renderer.toggle_visibility()
        elif action_name == "close_bag":
            self.game_scene.item_bag_renderer.visible = False
        elif action_name == "placement_tutorial":
            # destaca spots e ensina a arrastar (pode ser implementado depois)
            pass
        elif action_name == "start_wave":
            self.game_scene.wave_manager.start_next_wave()
        elif action_name == "complete_tutorial":
            # Pode definir uma flag para finalizar o tutorial
            pass
        elif action_name == "set_flag":
            # Permite setar flags customizadas via ação
            # Formato: "set_flag:nome_da_flag"
            if ":" in action_name:
                flag_name = action_name.split(":", 1)[1]
                self.custom_flags[flag_name] = True
                print(f"[EVENT] Flag customizada setada: {flag_name}")
        # Adicione outras ações conforme necessário

    def _execute_tutorial(self, event):
        """Executa uma ação de tutorial."""
        action = event.tutorial_action
        if action == TutorialAction.OPEN_BAG:
            self.game_scene.item_bag_renderer.toggle_visibility()
        elif action == TutorialAction.PLACEMENT:
            # Destaca spots para colocação
            pass
        elif action == TutorialAction.CAPTURE:
            # Mostra como capturar
            pass
        elif action == TutorialAction.BATTLE:
            # Mostra sobre batalha
            pass
        elif action == TutorialAction.TEAM_MANAGEMENT:
            # Mostra gerenciamento de time
            pass
        elif action == TutorialAction.HIGHLIGHT_UI:
            # Destaca elemento da UI (se implementado)
            pass

        # Se o tutorial não tem interação direta, despausa
        if hasattr(event, 'pause_game') and event.pause_game:
            self._resume_after_event()

    def _execute_game_state(self, event):
        """Executa uma ação de estado do jogo."""
        if event.state_action == GameStateAction.PAUSE:
            self.game_scene.paused = True
            self.game_scene.wave_manager.paused = True
        elif event.state_action == GameStateAction.RESUME:
            self.game_scene.paused = False
            self.game_scene.wave_manager.paused = False
        elif event.state_action == GameStateAction.START_WAVE:
            self.game_scene.wave_manager.start_next_wave()
        elif event.state_action == GameStateAction.COMPLETE_PHASE:
            self.game_scene._complete_phase()
        elif event.state_action == GameStateAction.SHOW_NOTIFICATION:
            from src.ui.toast_renderer import toast_info
            message = event.state_params.get("message", "Notificação")
            toast_info(message, duration=3.0)

        # Se pausou, mas a ação já foi executada, despausa
        if hasattr(event, 'pause_game') and event.pause_game:
            self._resume_after_event()

    def _execute_spawn(self, event):
        """Executa uma ação de spawn."""
        if event.spawn_type == SpawnAction.BOSS:
            self.game_scene.wave_manager.spawn_boss()
            self.boss_spawned = True
        elif event.spawn_type == SpawnAction.ENEMY:
            # spawna inimigo específico
            pass
        elif event.spawn_type == SpawnAction.WAVE:
            # força início de wave específica
            pass

        if hasattr(event, 'pause_game') and event.pause_game:
            self._resume_after_event()

    def _execute_custom_action(self, event):
        """Executa uma ação customizada."""
        action_name = event.custom_action_name
        params = event.custom_action_params

        if action_name == "set_flag":
            flag = params.get('flag', '')
            value = params.get('value', True)
            if flag:
                self.custom_flags[flag] = value
                print(f"[EVENT] Flag customizada setada via CUSTOM_ACTION: {flag} = {value}")
        elif action_name == "delay":
            # Adiciona um delay manual (se necessário)
            pass
        # Adicione outras ações customizadas aqui

        if hasattr(event, 'pause_game') and event.pause_game:
            self._resume_after_event()

    def _execute_camera(self, event):
        """Aplica efeito de câmera."""
        # Aplica o efeito
        self.game_scene.camera.apply_effect(
            event.camera_effect,
            event.camera_intensity,
            event.camera_duration
        )

        # Se pausou, agenda o despause após a duração do efeito + pequeno delay
        if hasattr(event, 'pause_game') and event.pause_game:
            self._waiting_for_resume = True
            self._pending_resume_timer = event.camera_duration + 0.2
            print(f"[EVENT] Câmera pausou, despausando em {self._pending_resume_timer:.1f}s")