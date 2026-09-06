# src/editor/event_system.py

"""
Sistema de Eventos para o Jogo e Editor.
Define a estrutura de dados para eventos, gatilhos e ações.
"""

# Tipos de Gatilho
class TriggerType:
    TIME = "time"                   # Gatilho baseado em tempo de jogo
    WAVE = "wave"                   # Gatilho baseado no estado de uma wave (início/fim)
    START_PHASE = "start_phase"     # No início da fase
    BEFORE_BOSS = "before_boss"     # Antes do boss spawnar
    AFTER_BOSS_DEFEAT = "after_boss_defeat"  # Após derrotar o boss
    AFTER_WAVE = "after_wave"       # Após uma wave específica (usando wave_index)
    CUSTOM = "custom"               # Condição customizada (ex: "first_enemy_defeated")

# Estados de onda para o gatilho WAVE
class WaveTriggerState:
    WAVE_START = "wave_start"       # No início de uma wave específica
    WAVE_END = "wave_end"           # Ao final de uma wave específica

# Tipos de Evento
class EventType:
    MESSAGE = "message"             # Mensagem na tela com personagem (com botão de ação)
    CAMERA = "camera"               # Efeitos de câmera (tremor, flash, etc.)
    TUTORIAL = "tutorial"           # Ação de tutorial (abrir bolsa, destacar UI, etc.)
    GAME_STATE = "game_state"       # Mudar estado do jogo (pausar, iniciar wave, etc.)
    SPAWN = "spawn"                 # Spawnar um inimigo ou boss
    CUSTOM_ACTION = "custom_action" # Ação customizada com parâmetros (para extensibilidade)

# Efeitos de Câmera
class CameraEffect:
    SHAKE = "shake"                 # Tremor de tela
    FLASH = "flash"                 # Flash branco
    # Futuro: ZOOM, SHAKE_DIRECTIONAL, etc.

# Ações de Tutorial
class TutorialAction:
    OPEN_BAG = "open_bag"               # Abrir a bolsa e destacar
    PLACEMENT = "placement"             # Ensinar a colocar Pokémon no campo
    CAPTURE = "capture"                 # Ensinar a capturar
    BATTLE = "battle"                   # Ensinar sobre batalha
    TEAM_MANAGEMENT = "team_management" # Ensinar a gerenciar time
    HIGHLIGHT_UI = "highlight_ui"       # Destacar um elemento da UI (passar nome)

# Ações de Estado do Jogo
class GameStateAction:
    PAUSE = "pause"                 # Pausar o jogo
    RESUME = "resume"               # Despausar o jogo
    START_WAVE = "start_wave"       # Iniciar a próxima wave
    COMPLETE_PHASE = "complete_phase" # Completar a fase (vitória)
    SHOW_NOTIFICATION = "show_notification"  # Mostrar notificação

# Ações de Spawn
class SpawnAction:
    BOSS = "boss"                   # Spawnar o boss da fase
    ENEMY = "enemy"                 # Spawnar um inimigo específico
    WAVE = "wave"                   # Forçar o início de uma wave específica


class GameEvent:
    """
    Representa um único evento que será executado.
    """
    def __init__(self):
        # Tipo de evento: "message", "camera", "tutorial", etc.
        self.event_type = EventType.MESSAGE

        # Dados comuns a todos os tipos
        self.delay = 0.0  # Segundos de delay antes de executar o evento

        # ----- Dados específicos para MENSAGEM -----
        self.message_text = ""
        self.speaker_name = ""
        self.speaker_sprite_path = ""  # Caminho para a imagem do personagem
        self.action_label = ""         # Texto do botão (ex: "OK", "Abrir Bolsa")
        self.action_trigger = ""       # Nome da ação a executar ao clicar no botão

        # ----- Dados específicos para CÂMERA -----
        self.camera_effect = CameraEffect.SHAKE
        self.camera_intensity = 5.0
        self.camera_duration = 0.5

        # ----- Dados específicos para TUTORIAL -----
        self.tutorial_action = TutorialAction.OPEN_BAG
        self.tutorial_highlight = ""   # Nome do elemento UI a destacar (opcional)

        # ----- Dados específicos para GAME_STATE -----
        self.state_action = GameStateAction.PAUSE
        self.state_params = {}         # Parâmetros adicionais (ex: {"message": "Olá!"})

        # ----- Dados específicos para SPAWN -----
        self.spawn_type = SpawnAction.BOSS
        self.spawn_params = {}         # ex: {"pokemon_id": 1, "level": 10, "path_index": 0}

        # ----- Dados específicos para CUSTOM_ACTION -----
        self.custom_action_name = ""   # Nome da ação (ex: "set_flag")
        self.custom_action_params = {} # Parâmetros (ex: {"flag": "tutorial_step_2", "value": True})

    def to_dict(self):
        """Converte o evento para um dicionário (para salvar no JSON)."""
        data = {
            "event_type": self.event_type,
            "delay": self.delay,
        }

        if self.event_type == EventType.MESSAGE:
            data.update({
                "message_text": self.message_text,
                "speaker_name": self.speaker_name,
                "speaker_sprite_path": self.speaker_sprite_path,
                "action_label": self.action_label,
                "action_trigger": self.action_trigger,
            })
        elif self.event_type == EventType.CAMERA:
            data.update({
                "camera_effect": self.camera_effect,
                "camera_intensity": self.camera_intensity,
                "camera_duration": self.camera_duration,
            })
        elif self.event_type == EventType.TUTORIAL:
            data.update({
                "tutorial_action": self.tutorial_action,
                "tutorial_highlight": self.tutorial_highlight,
            })
        elif self.event_type == EventType.GAME_STATE:
            data.update({
                "state_action": self.state_action,
                "state_params": self.state_params,
            })
        elif self.event_type == EventType.SPAWN:
            data.update({
                "spawn_type": self.spawn_type,
                "spawn_params": self.spawn_params,
            })
        elif self.event_type == EventType.CUSTOM_ACTION:
            data.update({
                "custom_action_name": self.custom_action_name,
                "custom_action_params": self.custom_action_params,
            })

        return data

    def from_dict(self, data):
        """Carrega os dados do evento a partir de um dicionário."""
        self.event_type = data.get("event_type", EventType.MESSAGE)
        self.delay = data.get("delay", 0.0)

        if self.event_type == EventType.MESSAGE:
            self.message_text = data.get("message_text", "")
            self.speaker_name = data.get("speaker_name", "")
            self.speaker_sprite_path = data.get("speaker_sprite_path", "")
            self.action_label = data.get("action_label", "")
            self.action_trigger = data.get("action_trigger", "")
        elif self.event_type == EventType.CAMERA:
            self.camera_effect = data.get("camera_effect", CameraEffect.SHAKE)
            self.camera_intensity = data.get("camera_intensity", 5.0)
            self.camera_duration = data.get("camera_duration", 0.5)
        elif self.event_type == EventType.TUTORIAL:
            self.tutorial_action = data.get("tutorial_action", TutorialAction.OPEN_BAG)
            self.tutorial_highlight = data.get("tutorial_highlight", "")
        elif self.event_type == EventType.GAME_STATE:
            self.state_action = data.get("state_action", GameStateAction.PAUSE)
            self.state_params = data.get("state_params", {})
        elif self.event_type == EventType.SPAWN:
            self.spawn_type = data.get("spawn_type", SpawnAction.BOSS)
            self.spawn_params = data.get("spawn_params", {})
        elif self.event_type == EventType.CUSTOM_ACTION:
            self.custom_action_name = data.get("custom_action_name", "")
            self.custom_action_params = data.get("custom_action_params", {})

        return self


class EventTrigger:
    """
    Representa um gatilho que pode disparar uma sequência de eventos.
    """
    def __init__(self):
        # Tipo de gatilho: "time", "wave", "start_phase", etc.
        self.trigger_type = TriggerType.TIME

        # Parâmetros para cada tipo
        # TIME: tempo em segundos
        self.time_value = 0.0

        # WAVE e AFTER_WAVE: número da wave (0-indexed) e o momento (início ou fim)
        self.wave_index = 0
        self.wave_state = WaveTriggerState.WAVE_START

        # CUSTOM: condição personalizada (string)
        self.custom_condition = ""  # ex: "first_enemy_defeated", "tutorial_step_2"

        # Lista de eventos que serão executados por este gatilho
        self.events = []

        # Flag para saber se o gatilho já foi ativado (usado no jogo)
        self.is_triggered = False

    def add_event(self, event: GameEvent):
        """Adiciona um novo evento à lista."""
        self.events.append(event)

    def remove_event(self, index):
        """Remove um evento pelo índice."""
        if 0 <= index < len(self.events):
            del self.events[index]
            return True
        return False

    def to_dict(self):
        """Converte o gatilho para um dicionário (para salvar no JSON)."""
        data = {
            "trigger_type": self.trigger_type,
            "time_value": self.time_value,
            "wave_index": self.wave_index,
            "wave_state": self.wave_state,
            "custom_condition": self.custom_condition,
            "events": [e.to_dict() for e in self.events],
        }
        return data

    def from_dict(self, data):
        """Carrega os dados do gatilho a partir de um dicionário."""
        self.trigger_type = data.get("trigger_type", TriggerType.TIME)
        self.time_value = data.get("time_value", 0.0)
        self.wave_index = data.get("wave_index", 0)
        self.wave_state = data.get("wave_state", WaveTriggerState.WAVE_START)
        self.custom_condition = data.get("custom_condition", "")

        self.events = []
        for e_data in data.get("events", []):
            event = GameEvent()
            event.from_dict(e_data)
            self.events.append(event)

        self.is_triggered = False
        return self


class EventManager:
    """
    Gerencia os gatilhos e eventos de uma fase.
    """
    def __init__(self):
        self.triggers = []  # Lista de EventTrigger
        self.selected_trigger = 0  # Índice do gatilho selecionado para edição

    def add_trigger(self):
        """Adiciona um novo gatilho."""
        new_trigger = EventTrigger()
        self.triggers.append(new_trigger)
        self.selected_trigger = len(self.triggers) - 1
        print(f"[EVENT] Gatilho {len(self.triggers)} adicionado")
        return True

    def remove_trigger(self, index):
        """Remove um gatilho."""
        if 0 <= index < len(self.triggers):
            del self.triggers[index]
            if self.selected_trigger >= len(self.triggers):
                self.selected_trigger = max(0, len(self.triggers) - 1)
            print(f"[EVENT] Gatilho {index} removido")
            return True
        return False

    def get_current_trigger(self):
        """Retorna o gatilho atualmente selecionado."""
        if 0 <= self.selected_trigger < len(self.triggers):
            return self.triggers[self.selected_trigger]
        return None

    def to_dict(self):
        """Converte o gerenciador para dicionário."""
        return {
            "triggers": [t.to_dict() for t in self.triggers],
            "selected_trigger": self.selected_trigger
        }

    def from_dict(self, data):
        """Carrega o gerenciador a partir de um dicionário."""
        self.triggers = []
        for t_data in data.get("triggers", []):
            trigger = EventTrigger()
            trigger.from_dict(t_data)
            self.triggers.append(trigger)
        self.selected_trigger = data.get("selected_trigger", 0)
        if self.selected_trigger >= len(self.triggers):
            self.selected_trigger = max(0, len(self.triggers) - 1)