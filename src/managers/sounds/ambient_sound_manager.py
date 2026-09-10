# src/managers/sounds/ambient_sound_manager.py

"""
Gerenciador de sons ambiente (clima, chuva, tempestade, etc)
Herda do BaseSoundManager para sincronizar automaticamente
"""
import pygame
from pathlib import Path
from typing import Dict, Optional
from src.config.paths import RES_PATH
from src.managers.sounds.base_sound_manager import BaseSoundManager


class AmbientSoundManager(BaseSoundManager):
    """Gerencia os sons de ambiente como chuva, tempestade de areia, etc"""

    def __init__(self):
        super().__init__()
        self._ambient_volume: float = 0.5
        self._ambient_enabled: bool = True
        self._current_ambient: Optional[str] = None
        self._ambient_channel: Optional[pygame.mixer.Channel] = None
        self._load_sounds()
        self._sync_with_global_settings()

    def _load_sounds(self):
        """Carrega os sons de ambiente da pasta res/sounds/effects/weather"""
        weather_path = Path(RES_PATH) / "sounds" / "effects" / "weather"

        if not weather_path.exists():
            print(f"[AMBIENT_SOUND] Aviso: Pasta de sons de clima não encontrada: {weather_path}")
            weather_path.mkdir(parents=True, exist_ok=True)
            return

        # Carrega arquivos .mp3, .wav, .ogg da pasta
        sound_files = list(weather_path.glob("*.mp3")) + list(weather_path.glob("*.wav")) + list(
            weather_path.glob("*.ogg"))

        for sound_file in sound_files:
            raw_name = sound_file.stem.lower()
            sound_name = raw_name.replace(" ", "").replace("-", "").replace("'", "")

            try:
                sound = pygame.mixer.Sound(str(sound_file))
                self._sounds[sound_name] = sound
                print(f"[AMBIENT_SOUND] Carregado: {sound_file.name} -> {sound_name}")
            except Exception as e:
                print(f"[AMBIENT_SOUND] Erro ao carregar {sound_file}: {e}")

        # Reserva um canal para sons ambiente (para loop)
        try:
            self._ambient_channel = pygame.mixer.find_channel()
            if not self._ambient_channel:
                self._ambient_channel = pygame.mixer.Channel(8)  # Canal 8 para ambiente
            print(f"[AMBIENT_SOUND] Canal reservado para ambiente: {self._ambient_channel}")
        except Exception as e:
            print(f"[AMBIENT_SOUND] Erro ao reservar canal: {e}")

        print(f"[AMBIENT_SOUND] Total de sons de ambiente carregados: {len(self._sounds)}")

    def _sync_with_global_settings(self):
        """Sincroniza com as configurações globais"""
        from src.config.settings import settings

        self._ambient_enabled = getattr(settings, 'ambient_enabled', True)
        self._ambient_volume = getattr(settings, 'ambient_volume', 0.5) if self._ambient_enabled else 0

        # Aplica o volume a todos os sons
        self._apply_volume_to_all()

        # Se não estiver habilitado, para o som atual
        if not self._ambient_enabled or self._ambient_volume == 0:
            self.stop_ambient()

    def _apply_volume_to_all(self):
        """Aplica o volume atual a todos os sons carregados"""
        for sound in self._sounds.values():
            sound.set_volume(self._ambient_volume)

    def play_ambient(self, sound_key: str, loop: bool = True, fade_ms: int = 1000) -> bool:
        """
        Toca um som ambiente (chuva, tempestade, etc)

        Args:
            sound_key: Nome do som (ex: "rain", "sandstorm")
            loop: Se deve tocar em loop
            fade_ms: Duração do fade in em ms

        Returns:
            True se tocou, False caso contrário
        """
        if not self._ambient_enabled or self._ambient_volume == 0:
            print(
                f"[AMBIENT_SOUND] Ambiente desabilitado (enabled={self._ambient_enabled}, volume={self._ambient_volume})")
            return False

        sound = self._sounds.get(sound_key.lower())
        if not sound:
            print(f"[AMBIENT_SOUND] Som ambiente não encontrado: {sound_key}")
            return False

        # Para o som atual se for diferente
        if self._current_ambient and self._current_ambient != sound_key:
            self.stop_ambient(fade_ms=500)

        # Se já está tocando o mesmo som, não faz nada
        if self._current_ambient == sound_key and self._ambient_channel and self._ambient_channel.get_busy():
            return True

        try:
            # Define volume
            sound.set_volume(self._ambient_volume)

            # Toca no canal reservado
            if self._ambient_channel:
                self._ambient_channel.play(sound, loops=-1 if loop else 0, fade_ms=fade_ms)
            else:
                # Fallback: toca como efeito normal
                sound.play(loops=-1 if loop else 0, fade_ms=fade_ms)

            self._current_ambient = sound_key
            print(f"[AMBIENT_SOUND] Tocado: {sound_key} (loop={loop})")
            return True

        except Exception as e:
            print(f"[AMBIENT_SOUND] Erro ao tocar {sound_key}: {e}")
            return False

    def stop_ambient(self, fade_ms: int = 500):
        """Para o som ambiente atual"""
        if self._ambient_channel and self._ambient_channel.get_busy():
            self._ambient_channel.fadeout(fade_ms)
            self._current_ambient = None
            print(f"[AMBIENT_SOUND] Som ambiente parado (fade={fade_ms}ms)")
            return True
        return False

    def set_ambient_volume(self, volume: float):
        """Define o volume dos sons ambiente"""
        self._ambient_volume = max(0.0, min(1.0, volume))
        if not self._ambient_enabled:
            self._ambient_volume = 0

        # Aplica o volume a todos os sons
        self._apply_volume_to_all()

        # Se o volume for 0, para o som
        if self._ambient_volume == 0:
            self.stop_ambient()

        print(f"[AMBIENT_SOUND] Volume ambiente definido: {self._ambient_volume}")

    def set_ambient_enabled(self, enabled: bool):
        """Habilita/desabilita sons ambiente"""
        self._ambient_enabled = enabled
        if not enabled:
            self.stop_ambient()
            self._ambient_volume = 0
        else:
            from src.config.settings import settings
            self._ambient_volume = getattr(settings, 'ambient_volume', 0.5)
            self._apply_volume_to_all()

    def is_playing(self) -> bool:
        """Verifica se um som ambiente está tocando"""
        return self._ambient_channel and self._ambient_channel.get_busy()

    def get_current_ambient(self) -> Optional[str]:
        """Retorna o nome do som ambiente atual"""
        return self._current_ambient

    def sync_with_main_manager(self):
        """Sincroniza com as configurações globais"""
        self._sync_with_global_settings()


# Instância global
ambient_sound_manager = AmbientSoundManager()