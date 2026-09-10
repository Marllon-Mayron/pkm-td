# src/config/settings.py

"""
Configurações do jogo - Agora usa apenas o save do jogador
"""
import json
from pathlib import Path


class Settings:
    def __init__(self):
        # Configurações de vídeo (valores padrão)
        self.screen_width = 1280
        self.screen_height = 720
        self.fullscreen = False
        self.vsync = True

        # Configurações de performance
        self.target_fps = 60
        self.game_tick_rate = 60
        self.max_fps = 60

        # Configurações de áudio (valores padrão)
        self.sfx_volume = 0.7
        self.music_volume = 0.5
        self.music_enabled = True
        self.sfx_enabled = True

        # ===== Configurações de ambiente (clima) =====
        self.ambient_volume = 0.5
        self.ambient_enabled = True

        # Cores
        self.colors = {
            'black': (0, 0, 0),
            'white': (255, 255, 255),
            'red': (255, 0, 0),
            'green': (0, 255, 0),
            'blue': (0, 0, 255),
            'gray': (128, 128, 128),
            'light_gray': (200, 200, 200)
        }

    def apply_to_sound_manager(self):
        """Aplica as configurações atuais ao SoundManager"""
        try:
            from src.managers.sounds.sound_manager import sound_manager
            sound_manager.set_music_volume(self.music_volume if self.music_enabled else 0)
            sound_manager.set_sfx_volume(self.sfx_volume if self.sfx_enabled else 0)

            # ===== Sincroniza o ambient_sound_manager =====
            from src.managers.sounds.ambient_sound_manager import ambient_sound_manager
            ambient_sound_manager.set_ambient_volume(self.ambient_volume if self.ambient_enabled else 0)

            print(f"[SETTINGS] Aplicado: música={self.music_volume} (enabled={self.music_enabled}), "
                  f"SFX={self.sfx_volume} (enabled={self.sfx_enabled}), "
                  f"Ambiente={self.ambient_volume} (enabled={self.ambient_enabled})")
        except Exception as e:
            print(f"[SETTINGS] Não foi possível aplicar ao SoundManager: {e}")

    def get_screen_size(self):
        return (self.screen_width, self.screen_height)

    def get_dt_factor(self, dt):
        return dt * self.target_fps


# Instância global das configurações
settings = Settings()