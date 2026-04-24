# src/managers/sounds/base_sound_manager.py

"""
Classe base para todos os gerenciadores de som do jogo
Garante que todos os sons sejam sincronizados com as configurações globais
"""
import pygame
from abc import ABC, abstractmethod
from typing import Dict, Optional, Any


class BaseSoundManager(ABC):
    """Classe base para todos os gerenciadores de som"""

    _instances: Dict[str, Any] = {}  # Armazena instâncias por classe

    def __new__(cls, *args, **kwargs):
        """Singleton pattern por classe"""
        if cls.__name__ not in cls._instances:
            instance = super().__new__(cls)
            cls._instances[cls.__name__] = instance
            instance._initialized = False
        return cls._instances[cls.__name__]

    def __init__(self):
        if self._initialized:
            return
        self._initialized = True
        self._volume: float = 0.7
        self._sounds: Dict[str, pygame.mixer.Sound] = {}
        self._enabled: bool = True

    @abstractmethod
    def _load_sounds(self):
        """Método abstrato para carregar sons específicos - deve ser implementado pelas subclasses"""
        pass

    def _sync_with_global_settings(self, sound_type: str):
        """
        Sincroniza o volume com as configurações globais

        Args:
            sound_type: "music" ou "sfx" - qual tipo de som sincronizar
        """
        from src.config.settings import settings

        if sound_type == "music":
            self._enabled = settings.music_enabled
            self._volume = settings.music_volume if settings.music_enabled else 0
        elif sound_type == "sfx":
            self._enabled = settings.sfx_enabled
            self._volume = settings.sfx_volume if settings.sfx_enabled else 0
        else:
            # Fallback: usa sfx
            self._enabled = settings.sfx_enabled
            self._volume = settings.sfx_volume if settings.sfx_enabled else 0

        # Aplica o volume a todos os sons
        self._apply_volume_to_all()

    def _apply_volume_to_all(self):
        """Aplica o volume atual a todos os sons carregados"""
        for sound in self._sounds.values():
            sound.set_volume(self._volume)

    def play_sound(self, sound_key: str, volume: Optional[float] = None) -> bool:
        """
        Toca um som específico

        Args:
            sound_key: Chave do som a ser tocado
            volume: Volume específico (opcional)

        Returns:
            True se tocou, False caso contrário
        """
        if not self._enabled or self._volume == 0:
            return False

        sound = self._sounds.get(sound_key)
        if sound:
            target_volume = volume if volume is not None else self._volume
            sound.set_volume(target_volume)
            try:
                sound.play()
                return True
            except Exception as e:
                print(f"[{self.__class__.__name__}] Erro ao tocar {sound_key}: {e}")
        return False

    def set_global_volume(self, volume: float):
        """Define o volume global (usado pela classe base quando sincroniza)"""
        self._volume = max(0.0, min(1.0, volume))
        self._apply_volume_to_all()

    def get_volume(self) -> float:
        """Retorna o volume atual"""
        return self._volume

    def get_enabled(self) -> bool:
        """Retorna se está habilitado"""
        return self._enabled

    @classmethod
    def sync_all_managers(cls):
        """Sincroniza todos os gerenciadores de som com as configurações globais"""
        for instance in cls._instances.values():
            if hasattr(instance, '_sync_with_global_settings'):
                # Tenta sincronizar como SFX primeiro
                instance._sync_with_global_settings("sfx")