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

    def update(self, dt):
        # Atualiza eventos agendados
        self._update_pending_events(dt)

        # Verifica triggers se não houver diálogo ativo
        if not self.current_dialog:
            self._check_triggers()

    def _check_triggers(self):
        for i, trigger in enumerate(self.triggers):
            if self.triggered[i]:
                continue
            if self._evaluate_trigger(trigger):
                self.triggered[i] = True
                self._schedule_events(trigger.events)

    def _evaluate_trigger(self, trigger):
        if trigger.trigger_type == TriggerType.START_PHASE:
            return True
        elif trigger.trigger_type == TriggerType.BEFORE_BOSS:
            return not self.boss_spawned and self.game_scene.wave_manager.is_next_wave_boss()
        elif trigger.trigger_type == TriggerType.AFTER_BOSS_DEFEAT:
            return not self.boss_defeated and self.game_scene.wave_manager.is_boss_defeated()
        elif trigger.trigger_type == TriggerType.AFTER_WAVE:
            wave_idx = trigger.wave_index
            if wave_idx not in self.waves_ended:
                if self.game_scene.wave_manager.is_wave_completed(wave_idx):
                    self.waves_ended.append(wave_idx)
                    return True
            return False
        elif trigger.trigger_type == TriggerType.CUSTOM:
            return self.custom_flags.get(trigger.custom_condition, False)
        elif trigger.trigger_type == TriggerType.TIME:
            # você precisa implementar a lógica de tempo se quiser
            return False
        elif trigger.trigger_type == TriggerType.WAVE:
            # lógica original (início/fim)
            return False
        return False

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

    def _show_message(self, event):
        # Cria um diálogo com botão de ação
        from src.scenes.game_scene.components.overlays.dialog_overlay import DialogOverlay
        self.current_dialog = DialogOverlay(
            self.game_scene,
            text=event.message_text,
            speaker=event.speaker_name,
            sprite_path=event.speaker_sprite_path,
            action_label=event.action_label,
            action_callback=lambda: self._on_dialog_action(event.action_trigger)
        )

    def _on_dialog_action(self, action_name):
        # Executa ação após clique no botão
        self.current_dialog = None
        self._execute_action_by_name(action_name)

    def _execute_action_by_name(self, action_name):
        if action_name == "open_bag":
            self.game_scene.item_bag_renderer.toggle_visibility()
        elif action_name == "close_bag":
            self.game_scene.item_bag_renderer.visible = False
        elif action_name == "start_wave":
            # Inicia a próxima wave manualmente (se necessário)
            pass
        elif action_name == "complete_tutorial":
            # Pode definir uma flag para finalizar o tutorial
            pass

    def _execute_tutorial(self, event):
        action = event.tutorial_action
        if action == TutorialAction.OPEN_BAG:
            self._show_message_with_action(
                "Abra a bolsa com TAB e arraste uma Pokébola para capturar um Pokémon!",
                "Abrir Bolsa",
                "open_bag"
            )
        elif action == TutorialAction.PLACEMENT:
            self._show_message_with_action(
                "Arraste um Pokémon do time para um dos spots para colocá-lo no campo!",
                "Entendi",
                ""
            )
        # ...

    def _execute_game_state(self, event):
        if event.state_action == GameStateAction.PAUSE:
            self.game_scene.paused = True
        elif event.state_action == GameStateAction.RESUME:
            self.game_scene.paused = False
        elif event.state_action == GameStateAction.START_WAVE:
            self.game_scene.wave_manager.start_next_wave()

    def _execute_spawn(self, event):
        if event.spawn_type == SpawnAction.BOSS:
            self.game_scene.wave_manager.spawn_boss()
            self.boss_spawned = True
        elif event.spawn_type == SpawnAction.ENEMY:
            # spawna inimigo específico
            pass

    def _execute_custom_action(self, event):
        # permite registrar ações customizadas via dicionário
        action_name = event.custom_action_name
        params = event.custom_action_params
        if action_name == "set_flag":
            flag = params.get('flag', '')
            value = params.get('value', True)
            self.custom_flags[flag] = value
        # outros...

    def _execute_camera(self, event):
        # aplica efeito de câmera
        self.game_scene.camera.apply_effect(event.camera_effect, event.camera_intensity, event.camera_duration)