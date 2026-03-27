# src/editor/event_system.py

"""
Sistema de Eventos para o Jogo e Editor.
Define a estrutura de dados para eventos e gatilhos.
"""

# Tipos de Gatilho
class TriggerType:
    TIME = "time"       # Gatilho baseado em tempo de jogo
    WAVE = "wave"       # Gatilho baseado no estado de uma wave

# Estados de onda para o gatilho WAVE
class WaveTriggerState:
    WAVE_START = "wave_start"   # No início de uma wave específica
    WAVE_END = "wave_end"       # Ao final de uma wave específica
    # Poderíamos adicionar mais no futuro: ON_ENEMY_DEATH, ON_SPAWN, etc.

# Tipos de Evento
class EventType:
    MESSAGE = "message"   # Mensagem na tela com personagem
    CAMERA = "camera"     # Efeitos de câmera (tremor, flash, etc.)
    # Futuro: MUSIC, SPAWN_ENEMY, GIVE_ITEM, CHANGE_MAP, etc.

# Efeitos de Câmera
class CameraEffect:
    SHAKE = "shake"       # Tremor de tela
    FLASH = "flash"       # Flash branco
    # Futuro: ZOOM, SHAKE_DIRECTIONAL, etc.


class GameEvent:
    """
    Representa um único evento que será executado.
    """
    def __init__(self):
        # Tipo de evento: "message", "camera", etc.
        self.event_type = EventType.MESSAGE

        # Dados comuns a todos os tipos
        self.delay = 0.0  # Segundos de delay antes de executar o evento

        # Dados específicos para MENSAGEM
        self.message_text = ""
        self.speaker_name = ""
        self.speaker_sprite_path = ""  # Caminho para a imagem do personagem

        # Dados específicos para CÂMERA
        self.camera_effect = CameraEffect.SHAKE
        self.camera_intensity = 5.0  # Para tremor
        self.camera_duration = 0.5   # Duração do efeito em segundos

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
            })
        elif self.event_type == EventType.CAMERA:
            data.update({
                "camera_effect": self.camera_effect,
                "camera_intensity": self.camera_intensity,
                "camera_duration": self.camera_duration,
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
        elif self.event_type == EventType.CAMERA:
            self.camera_effect = data.get("camera_effect", CameraEffect.SHAKE)
            self.camera_intensity = data.get("camera_intensity", 5.0)
            self.camera_duration = data.get("camera_duration", 0.5)

        return self


class EventTrigger:
    """
    Representa um gatilho que pode disparar uma sequência de eventos.
    """
    def __init__(self):
        # Tipo de gatilho: "time", "wave", etc.
        self.trigger_type = TriggerType.TIME

        # Parâmetros para cada tipo
        # TIME: tempo em segundos
        self.time_value = 0.0

        # WAVE: número da wave (0-indexed) e o momento (início ou fim)
        self.wave_index = 0
        self.wave_state = WaveTriggerState.WAVE_START

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
        return {
            "trigger_type": self.trigger_type,
            "time_value": self.time_value,
            "wave_index": self.wave_index,
            "wave_state": self.wave_state,
            "events": [e.to_dict() for e in self.events],
        }

    def from_dict(self, data):
        """Carrega os dados do gatilho a partir de um dicionário."""
        self.trigger_type = data.get("trigger_type", TriggerType.TIME)
        self.time_value = data.get("time_value", 0.0)
        self.wave_index = data.get("wave_index", 0)
        self.wave_state = data.get("wave_state", WaveTriggerState.WAVE_START)

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