# src/ui/toast_renderer.py

from src.managers.notification_manager import notification_manager
from src.ui.notification import NotificationType


def toast_info(message: str, duration: float = 3.0, pokemon=None, portrait: str = "normal"):
    notification_manager.notify(message, NotificationType.INFO, duration,
                                pokemon=pokemon, portrait_expression=portrait)


def toast_success(message: str, duration: float = 3.0, pokemon=None, portrait: str = "normal"):
    notification_manager.notify(message, NotificationType.SUCCESS, duration,
                                pokemon=pokemon, portrait_expression=portrait)


def toast_warning(message: str, duration: float = 3.0, pokemon=None, portrait: str = "normal"):
    notification_manager.notify(message, NotificationType.WARNING, duration,
                                pokemon=pokemon, portrait_expression=portrait)


def toast_error(message: str, duration: float = 3.0, pokemon=None, portrait: str = "normal"):
    notification_manager.notify(message, NotificationType.ERROR, duration,
                                pokemon=pokemon, portrait_expression=portrait)


def toast_achievement(message: str, duration: float = 4.0, pokemon=None, portrait: str = "normal"):
    notification_manager.notify(message, NotificationType.ACHIEVEMENT, duration,
                                pokemon=pokemon, portrait_expression=portrait)


def toast_battle(message: str, duration: float = 2.5, pokemon=None, portrait: str = "normal"):
    """
    Exibe notificação de batalha

    Args:
        message: Mensagem a ser exibida
        duration: Duração em segundos
        pokemon: Objeto Pokémon para mostrar o portrait
        portrait: Expressão do portrait ("normal", "happy", "angry", "sad", "shocked", etc)
    """
    notification_manager.notify(message, NotificationType.BATTLE, duration,
                                pokemon=pokemon, portrait_expression=portrait)