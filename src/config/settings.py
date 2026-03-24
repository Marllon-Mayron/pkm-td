# src/config/settings.py
"""
Configurações do jogo - tudo centralizado aqui
"""
import pygame
import json
from pathlib import Path

class Settings:
    def __init__(self):
        # Configurações de vídeo
        self.screen_width = 1280
        self.screen_height = 720
        self.fullscreen = False
        self.vsync = True

        # Configurações de performance
        self.target_fps = 60  # FPS alvo para renderização
        self.game_tick_rate = 60  # Updates por segundo (lógica do jogo)
        self.max_fps = 240  # FPS máximo (para evitar uso desnecessário de CPU)

        # Configurações de áudio (NOVO)
        self.sfx_volume = 0.7
        self.music_volume = 0.5
        self.music_enabled = True
        self.sfx_enabled = True

        # Cores (útil para ter centralizado)
        self.colors = {
            'black': (0, 0, 0),
            'white': (255, 255, 255),
            'red': (255, 0, 0),
            'green': (0, 255, 0),
            'blue': (0, 0, 255),
            'gray': (128, 128, 128),
            'light_gray': (200, 200, 200)
        }

        # Carregar configurações salvas se existirem
        self.load_settings()

    def load_settings(self):
        """Carrega configurações salvas"""
        config_path = Path('config.json')
        if config_path.exists():
            try:
                with open(config_path, 'r') as f:
                    data = json.load(f)
                    self.screen_width = data.get('screen_width', self.screen_width)
                    self.screen_height = data.get('screen_height', self.screen_height)
                    self.fullscreen = data.get('fullscreen', self.fullscreen)
                    self.target_fps = data.get('target_fps', self.target_fps)
                    self.vsync = data.get('vsync', self.vsync)
                    # NOVAS configurações de áudio
                    self.sfx_volume = data.get('sfx_volume', self.sfx_volume)
                    self.music_volume = data.get('music_volume', self.music_volume)
                    self.music_enabled = data.get('music_enabled', self.music_enabled)
                    self.sfx_enabled = data.get('sfx_enabled', self.sfx_enabled)
            except Exception as e:
                print(f"Erro ao carregar configurações: {e}")

    def save_settings(self):
        """Salva configurações"""
        data = {
            'screen_width': self.screen_width,
            'screen_height': self.screen_height,
            'fullscreen': self.fullscreen,
            'target_fps': self.target_fps,
            'vsync': self.vsync,
            'sfx_volume': self.sfx_volume,
            'music_volume': self.music_volume,
            'music_enabled': self.music_enabled,
            'sfx_enabled': self.sfx_enabled
        }

        try:
            with open('config.json', 'w') as f:
                json.dump(data, f, indent=4)
        except Exception as e:
            print(f"Erro ao salvar configurações: {e}")

    def get_screen_size(self):
        """Retorna tamanho atual da tela"""
        return (self.screen_width, self.screen_height)

    def get_dt_factor(self, dt):
        """Retorna fator de tempo para movimento frame-rate independent"""
        return dt * self.target_fps

# Instância global das configurações
settings = Settings()